# CUCM Migration Extraction Scope Expansion

Deferred from Phase 03 (2026-03-23). These are object types not covered by the
current 20 canonical types in `models.py` but needed for complete enterprise
migration fidelity.

## AXL Surface Area Context

CUCM 15.0 AXL exposes **251 object types** with **2,136 operations** across 16
functional domains. The current extractors cover ~20 types — the core needed for
a "get everyone onto Webex Calling" migration. This document specifies the next
tier: configuration detail that enterprise customers (10K+ users) expect to be
migrated or documented.

Source: AXL WSDL analysis against `/Users/ahobgood/Downloads/axlsqltoolkit/schema/15.0/AXLAPI.wsdl`

---

## Tier 2 — Needed for Complete Enterprise Migration

These require new canonical types in `models.py`, new mapper specs in `03b`, and
new or expanded extractors.

### 2.1 Per-User Call Forwarding Settings

**Current state:** Call forwarding data (CFA, CFB, CFNA) is now extracted via
`getLine` and merged into phone line entries by `DeviceExtractor`. The raw data
is available. What's missing is a canonical type to represent it and a mapper to
translate CUCM forwarding rules → Webex call forwarding settings.

**CUCM source:** `getLine` response fields:
- `callForwardAll` → `{forwardToVoiceMail, destination, callingSearchSpaceName}`
- `callForwardBusy` → same structure
- `callForwardBusyInt` → internal-only busy forwarding
- `callForwardNoAnswer` → `{forwardToVoiceMail, destination, callingSearchSpaceName, duration}`
- `callForwardNoAnswerInt` → internal-only no-answer
- `callForwardNoCoverage`, `callForwardOnFailure`, `callForwardNotRegistered`

Verified against live CUCM 15.0 (2026-03-23): all 10 forwarding fields present
on `getLine` response.

**Webex target:** Per-person call forwarding settings via
`/people/{personId}/features/callForwarding`:
- `always` → CFA
- `busy` → CFB
- `noAnswer` → CFNA with `numberOfRings`
- `callsFromSelection` → filter by caller type

**Canonical type needed:**
```python
class CanonicalCallForwarding(MigrationObject):
    user_canonical_id: str | None = None
    always_enabled: bool = False
    always_destination: str | None = None
    always_to_voicemail: bool = False
    busy_enabled: bool = False
    busy_destination: str | None = None
    busy_to_voicemail: bool = False
    no_answer_enabled: bool = False
    no_answer_destination: str | None = None
    no_answer_to_voicemail: bool = False
    no_answer_rings: int | None = None
```

**Extraction:** Already done — data is in `DeviceExtractor` line entries via
`_enrich_line_with_forwarding()`. No new extractor needed.

**Effort:** New canonical type + mapper only. Small.

---

### 2.2 Extension Mobility / Device Profiles

**Current state:** Not extracted. `CanonicalWorkspace.hotdesking_status` is
always `None`.

**CUCM source:** Extension Mobility (EM) uses Device Profiles — virtual phone
configurations that users log into. When a user logs into a physical phone, the
device profile's lines/settings replace the phone's default config.

AXL methods:
- `listDeviceProfile` / `getDeviceProfile` — same structure as Phone but
  `class=Device Profile`
- `listDefaultDeviceProfile` — per-user default profile
- Phone field `enableExtensionMobility` — whether the phone supports EM login

**Webex target:** Hot desking (`/workspaces/{id}/features/hotDesking`):
- `hotDeskingStatus`: "on" or "off"
- Webex hot desking is simpler than CUCM EM — no profile concept, just
  login/logout with the user's primary line

**Canonical type needed:**
```python
class CanonicalDeviceProfile(MigrationObject):
    """CUCM Device Profile → informs Webex hot desking decisions."""
    profile_name: str | None = None
    user_canonical_id: str | None = None
    lines: list[dict[str, Any]] = Field(default_factory=list)
    device_pool_name: str | None = None
    # Decision: if user has EM profile, their workspace should enable hot desking
```

**Extraction:** New extractor `device_profiles.py`:
- `listDeviceProfile` → `getDeviceProfile` (same pattern as phones)
- Also update `DeviceExtractor` to capture `enableExtensionMobility` field
  (already in getPhone response, just not in returnedTags)

**Effort:** New extractor + canonical type + mapper. Medium.

---

### 2.3 Music On Hold (MOH) Sources

**Current state:** Not extracted. MOH audio source IDs appear in device pool
and phone configurations but the actual audio files are not captured.

**CUCM source:**
- `listMohAudioSource` / `getMohAudioSource` — audio file references
- `listMohServer` — MOH server configuration
- Device pool field `userHoldMohAudioSourceId` — per-location MOH
- Phone field `userHoldMohAudioSourceId` — per-device MOH override

**Webex target:** Per-location MOH upload via
`/telephony/config/locations/{locationId}/musicOnHold`:
- `callHoldEnabled`, `callParkEnabled`
- `greeting`: "DEFAULT", "CUSTOM"
- Audio file uploaded separately

**Canonical type needed:**
```python
class CanonicalMusicOnHold(MigrationObject):
    location_canonical_id: str | None = None
    source_name: str | None = None
    audio_file_name: str | None = None
    is_default: bool = False
    # Note: actual audio file must be downloaded from CUCM MOH server
    # separately — not available via AXL
```

**Extraction:** New extractor or expand `locations.py` to pull MOH sources.

**Effort:** New canonical type + extractor. Audio file transfer is a separate
problem (SFTP from CUCM MOH server, not AXL). Medium.

---

### 2.4 Announcements (Custom Audio)

**Current state:** Not extracted. Auto Attendant and Call Queue greetings in
Webex require uploaded audio files. The CTI Route Point extractor captures the
AA structure but not the audio.

**CUCM source:** Announcements in CUCM are primarily in:
- Unity Connection (CUPI) — call handler greetings, accessed via
  `UnityConnectionClient` (already built, but greeting audio download not implemented)
- CUCM Announcement objects — `listAnnouncement` / `getAnnouncement`
  (used for MOH, queue announcements)

**Webex target:** Announcement upload via
`/telephony/config/locations/{locationId}/announcements`:
- Per-location announcement repository
- Referenced by Auto Attendants and Call Queues

**Canonical type needed:**
```python
class CanonicalAnnouncement(MigrationObject):
    name: str | None = None
    location_canonical_id: str | None = None
    file_name: str | None = None
    media_type: str | None = None  # WAV, WMA
    usage: str | None = None  # AA_GREETING, QUEUE_COMFORT, MOH
    # Audio file content must be downloaded separately
```

**Extraction:** New extractor `announcements.py` + expand Unity Connection
client for greeting audio download.

**Effort:** Medium-large. Audio file handling adds complexity.

---

### 2.5 Speed Dials and BLF (Busy Lamp Field)

**Current state:** Speed dials are present in the `getPhone` response
(within the `lines` structure and `speeddials` element) but not explicitly
extracted. BLF configurations are in `busyLampFields` on the phone object.

**CUCM source:**
- Phone field `speeddials` → `{speeddial: [{dirn, label, index}]}`
- Phone field `busyLampFields` → `{busyLampField: [{blfDest, label, index}]}`
- Both are per-phone configurations

**Webex target:**
- Speed dials: per-device speed dial configuration
- BLF: Monitoring list via `/people/{personId}/features/monitoring`

**Canonical type needed:**
```python
class CanonicalSpeedDial(BaseModel):  # Not MigrationObject — per-device config
    device_canonical_id: str
    index: int
    destination: str
    label: str | None = None

class CanonicalMonitoringList(MigrationObject):
    user_canonical_id: str | None = None
    monitored_members: list[str] = Field(default_factory=list)  # person IDs
```

**Extraction:** Expand `DeviceExtractor` to also extract `speeddials` and
`busyLampFields` from the getPhone response.

**Effort:** Small — data is already in the getPhone response.

---

### 2.6 E911 / ELIN Configuration

**Current state:** Not extracted. The existing `emergency-services.md` reference
doc covers the Webex E911 API surface but the CUCM side isn't extracted.

**CUCM source:**
- `listElinGroup` / `getElinGroup` — ELIN groups for E911 routing
- Route patterns in E911 partition (already extracted — pattern 911)
- `listGeoLocation` / `getGeoLocation` — geographic locations for E911
- CER (Cisco Emergency Responder) has its own database — not AXL-accessible

**Webex target:** ECBN (Emergency Callback Number) per location, RedSky E911
integration via `/telephony/config/locations/{locationId}/emergencyCallbackNumber`

**Canonical type needed:**
```python
class CanonicalE911Config(MigrationObject):
    location_canonical_id: str | None = None
    elin: str | None = None  # Emergency Location ID Number
    callback_number: str | None = None
    geo_location: str | None = None
```

**Extraction:** New extractor `e911.py` for ELIN groups + geo locations.

**Effort:** Small-medium. CER integration is out of scope.

---

### 2.7 Remote Destinations / Single Number Reach (SNR)

**Current state:** Not extracted. CUCM Remote Destinations define mobile numbers
that ring when a user's desk phone rings.

**CUCM source:**
- `listRemoteDestination` / `getRemoteDestination` — mobile numbers per user
- `listRemoteDestinationProfile` / `getRemoteDestinationProfile` — SNR profiles
- `listMobilityProfile` — enterprise mobility configuration

**Webex target:** Simultaneous ring / SNR via
`/people/{personId}/features/simultaneousRing`:
- `enabled`, `doNotRingIfOnCall`
- `phoneNumbers[]` with `ringOrder`

**Canonical type needed:**
```python
class CanonicalRemoteDestination(MigrationObject):
    user_canonical_id: str | None = None
    destination: str | None = None  # mobile number
    is_mobile: bool = True
    answer_too_soon_timer: int | None = None
    answer_too_late_timer: int | None = None
    enabled: bool = True
```

**Extraction:** New extractor `remote_destinations.py`.

**Effort:** Small.

---

### 2.8 SIP Profiles and Security Profiles

**Current state:** Profile names are extracted on SIP trunks (references) but
the profile detail (SIP messaging customization, TLS settings) is not pulled.

**CUCM source:**
- `listSipProfile` / `getSipProfile` — SIP messaging config (early offer,
  codec negotiation, normalization scripts)
- `listSipTrunkSecurityProfile` / `getSipTrunkSecurityProfile` — TLS/SRTP
  settings, digest authentication

**Webex target:** Trunk configuration includes SIP profile settings implicitly.
Webex trunks have limited SIP customization compared to CUCM. Most profile
settings are informational for the migration report.

**Canonical type needed:** Likely informational only — embedded in
`CanonicalTrunk` rather than a separate type. Expand trunk with:
```python
# Add to CanonicalTrunk:
    sip_profile_early_offer: bool | None = None
    security_profile_tls_mode: str | None = None  # NON_SECURE, TLS, etc.
```

**Extraction:** Expand `RoutingExtractor` to pull profile detail when processing
SIP trunks.

**Effort:** Small.

---

## Tier 3 — Informational Only (Migration Report)

These have no Webex equivalent. Extracted for the migration report so the
customer knows what CUCM functionality they're losing or what needs manual
reconfiguration.

| Object Type | AXL Method | Why it matters | Webex equivalent |
|---|---|---|---|
| Regions | `listRegion` | Codec preferences between locations | Cloud-managed |
| SRST References | `listSrst` | Survivable telephony during WAN outage | Webex Local Gateway survivability (different) |
| Media Resource Groups/Lists | `listMediaResourceGroup` | Transcoder/MTP assignments | Cloud-managed |
| Common Phone Profiles | `listCommonPhoneConfig` | Shared phone settings (DND, privacy) | Per-device settings in Webex |
| Phone Button Templates | `listPhoneButtonTemplate` | Button layout (line keys, speed dials) | Webex line key templates |
| Softkey Templates | `listSoftkeyTemplate` | Softkey customization | Not migratable |
| IP Phone Services | `listIpPhoneService` | XML services on phones | Not migratable |
| Feature Control Policies | `listFeatureControlPolicy` | Per-device feature restrictions | Webex feature access codes |
| Credential Policies | `listCredentialPolicy` | PIN/password rules | Webex managed separately |
| Intercom | `listIntercom` | Intercom lines between phones | No Webex equivalent |
| AAR Groups | `listAarGroup` | Automated Alternate Routing | Cloud-managed |
| Device Mobility Groups | `listDeviceMobilityGroup` | Site-aware settings | Cloud-managed |
| Recording Profiles | `listRecordingProfile` | Call recording config | Webex recording (different arch) |
| Enterprise Parameters | `getEnterprise` | Global CUCM settings | Migration planning input |
| Service Parameters | `listServiceParameter` | Per-service tuning | Migration planning input |
| LDAP Directory | `listLdapDirectory` | User sync config | Webex SCIM / directory sync |
| Application Users | `listAppUser` | JTAPI/TAPI apps controlling CTI RPs | Service app migration |
| Conference Bridges | `listConferenceBridge` | Hardware conference resources | Webex cloud conferencing |
| H.323 Gateway detail | `getH323Gateway` | Port-level analog/PRI config | ATA/gateway migration |

**Extraction approach for Tier 3:** A single `informational.py` extractor that
pulls all Tier 3 objects with minimal returnedTags (just names and counts) for
the migration report. No canonical types needed — data goes directly into the
report generator.

---

## Priority Order for Expansion

If expanding, build in this order (highest customer impact first):

1. **Call Forwarding** (§2.1) — data already extracted, just needs canonical type + mapper
2. **Speed Dials + BLF** (§2.5) — data already in getPhone response, just needs extraction
3. **Remote Destinations / SNR** (§2.7) — common enterprise feature, small effort
4. **Extension Mobility** (§2.2) — affects hoteling migration, medium effort
5. **E911 / ELIN** (§2.6) — compliance requirement, medium effort
6. **SIP/Security Profiles** (§2.8) — trunk detail, small effort
7. **MOH Sources** (§2.3) — quality of experience, medium effort
8. **Announcements** (§2.4) — AA/queue greetings, largest effort (audio files)

Total Tier 2 effort: ~4-6 sessions of design + build.

---

## Verified AXL Method Names

From live CUCM 15.0 validation (2026-03-23) and WSDL analysis:

| Method | Verified | Notes |
|---|---|---|
| `listDeviceProfile` | WSDL | Not tested live |
| `listMohAudioSource` | WSDL | Not tested live |
| `listAnnouncement` | WSDL | Not tested live |
| `listElinGroup` | WSDL | Not tested live |
| `listRemoteDestination` | WSDL | Not tested live |
| `listRemoteDestinationProfile` | WSDL | Not tested live |
| `listSipProfile` | WSDL | Not tested live |
| `listSipTrunkSecurityProfile` | WSDL | Not tested live |
| `listEndUser` | **BLOCKED** | EPR error + not in WSDL binding on this cluster. SQL fallback built. |
