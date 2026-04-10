# Hoteling / Hot Desking Migration (Extension Mobility)

**Date:** 2026-04-10
**Status:** Spec
**Scope:** CUCM-to-Webex migration pipeline gap -- Extension Mobility profiles to Webex hot desking configuration

---

## 1. Problem Statement

CUCM Extension Mobility (EM) allows users to log into any EM-enabled phone and load their personal profile -- line appearances, speed dials, services, and ring settings. This is a critical feature for enterprises with shared workspaces, hot desking environments, shift workers, and remote office/branch office (ROBO) deployments.

Webex Calling has hot desking capabilities but they are architecturally different from CUCM EM. The pipeline currently:

- **Detects EM profiles** via advisory pattern 20 (`detect_extension_mobility_usage`) -- produces an informational `ARCHITECTURE_ADVISORY` finding with `severity=LOW` and `category=rebuild`
- **Has a DeviceProfileMapper** that reads `device_profile` objects and produces `FEATURE_APPROXIMATION` decisions when profiles have features that Webex hot desking cannot replicate (multi-line, speed dials, BLF entries)
- **Does NOT** configure any Webex hot desking settings during execution
- **Does NOT** map EM service subscriptions to identify which users have EM enabled
- **Does NOT** create or configure workspaces for hot desking hosts
- **Does NOT** enable the person-level hoteling guest flag
- **Does NOT** enable location-level hot desking sign-in settings

### What Extension Mobility does in CUCM

Extension Mobility is a login/logout service on CUCM phones:

1. **Device Profiles** define what a user gets when they log in: line appearances (DNs), speed dials, BLF entries, services, ring settings, softkey assignments. Each user has a "default device profile" that loads when they log into any EM-enabled phone.

2. **EM Service Subscription** -- users must be subscribed to the "Extension Mobility" UC service to use it. The subscription is at the user level, typically through a Service Profile.

3. **EM-Enabled Phones** -- phones must have the "Allow Extension Mobility" checkbox enabled (in Phone Configuration > Device Information). When EM is enabled, the phone presents a login screen on idle, and any EM-subscribed user can log in.

4. **Login behavior** -- when a user logs in, their device profile replaces the phone's default configuration. All line appearances, speed dials, BLF entries, and services from the profile are loaded. The phone's own default DN may be overridden or supplemented.

5. **Logout behavior** -- when the user logs out (manually or via auto-logout timer), the phone reverts to its default configuration. The auto-logout timer is configurable per user or globally.

### What Webex hot desking does

Webex Calling has three related but distinct features:

1. **Person-level Hoteling** (`/people/{personId}/features/hoteling`):
   - Simple boolean toggle: `{"enabled": true}`
   - Enables a person as a hoteling *guest* -- their phone profile can be temporarily loaded onto a shared (host) phone
   - Scope: `spark-admin:people_write`
   - This is the closest equivalent to "user is EM-subscribed"

2. **Device-level Hoteling** (`/telephony/config/people/{personId}/devices/settings/hoteling`):
   - Configures the person's *primary device* as a hoteling host
   - Settings: `enabled`, `limitGuestUse`, `guestHoursLimit`
   - This is the closest equivalent to "phone has Allow Extension Mobility enabled"
   - Available via Get Person Devices response under the `hoteling` field

3. **Hot Desking** (per-person guest and per-location):
   - Person-level: `GET/PUT /telephony/config/people/{personId}/features/hotDesking/guest`
     - `voicePortalHotDeskSignInEnabled` -- enables hot desking sign-in via voice portal
   - Location-level: `GET/PUT /telephony/config/locations/{locationId}/features/hotDesking`
     - `voicePortalHotDeskSignInEnabled` -- location-level toggle
   - These control Voice Portal-based hot desking sign-in (dial into voice portal, authenticate, get profile loaded)

4. **Workspace Hot Desking** (via Workspaces API):
   - `hotdeskingStatus` field on workspace objects: `"on"`, `"off"`, or `"default"`
   - Controls whether a workspace (common-area device) supports hot desking
   - Workspace must be type `desk` and have `supportedDevices: "collaborationDevices"` or `"phones"`

5. **Hot Desk Sessions** (`/hotdesk/sessions`):
   - List and delete active hot desk sessions
   - Query by `personId`, `workspaceId`, or both
   - Returns: `sessionId`, `workspaceId`, `personId`, `bookingStartTime`, `bookingEndTime`
   - Admin management of active sessions

### Key architectural differences

| Aspect | CUCM Extension Mobility | Webex Hot Desking |
|--------|------------------------|-------------------|
| Profile richness | Full profile: multiple lines, speed dials, BLF, services, softkeys, ring settings | Primary line only -- no profile-level speed dials, BLF, or services |
| Login mechanism | Phone login screen (username + PIN) | Webex app login, voice portal, or device pairing |
| Device scope | Any EM-enabled phone in the cluster | Workspace devices with hot desking enabled |
| Multi-line | Profile can define 2-34 line appearances | Guest gets their primary line only |
| Speed dials | Profile carries speed dials | No profile-based speed dials |
| Auto-logout | Configurable timer per user or globally | Session-based with booking time window |
| BLF entries | Profile carries BLF entries | No profile-based BLF |

### Current pipeline state

| Component | Status | What exists |
|-----------|--------|-------------|
| AXL extraction | Done | `device_profiles` extractor in `FeatureExtractor` |
| Normalizer | Done | `normalize_device_profile()` creates `device_profile:{name}` objects; `normalize_info_device_profile()` creates `info_device_profile:{name}` for report |
| Mapper | Done | `DeviceProfileMapper` resolves user ownership, produces `CanonicalDeviceProfile`, creates `FEATURE_APPROXIMATION` decisions |
| Analyzer | None | No dedicated analyzer for EM configurations |
| Advisory | Done | Pattern 20 (`detect_extension_mobility_usage`) flags EM profiles as `rebuild` |
| Report | Done | Tier 4 appendix section V shows EM profiles |
| Execution | None | No handler configures hoteling/hot desking in Webex |

### Impact of not migrating (execution gap)

The detection and decision infrastructure exists, but the execution layer does nothing. When the migration runs:

1. Users who were EM-subscribed do not have hoteling enabled as guests.
2. Phones that were EM-enabled hosts are not configured as hoteling hosts.
3. Workspaces for shared desks are not configured for hot desking.
4. Location-level hot desking voice portal sign-in is not enabled.
5. Users accustomed to logging into any shared phone and getting their profile lose that capability entirely.

For shift-based environments (contact centers, retail, healthcare), this is a **day-1 workflow disruption** that affects every hot-desking user.

---

## 2. CUCM Source Data

### 2a. Already Extracted

The following data is already in the migration store from existing extractors:

**Device Profiles** (from `FeatureExtractor._extract_device_profiles`):

```python
raw_data["device_profiles"]["device_profiles"] = [
    {
        "name": "UDP-jsmith",
        "description": "John Smith's EM Profile",
        "product": "Cisco 8845",
        "protocol": "SIP",
        "phoneTemplateName": "Standard 8845 SIP",
        "lines": [
            {
                "dirn": {"pattern": "1001", "routePartitionName": "Internal_PT"},
                "label": "John Smith",
                "display": "John Smith",
                "displayAscii": "John Smith",
                "maxNumCalls": "2",
                "busyTrigger": "1",
                "index": "1"
            }
        ],
        "speeddials": [...],
        "busyLampFields": [...],
        "defaultProfileName": "...",
    },
    ...
]
```

**Normalized to:** `device_profile:{name}` objects with `pre_migration_state` containing profile details.

**Also:** `info_device_profile:{name}` objects for Tier 4 informational reporting.

### 2b. Not Yet Extracted

**EM Service Subscriptions** -- which users are subscribed to Extension Mobility:

```sql
SELECT eu.userid, s.name as service_name
FROM enduser eu
JOIN endusersubscribedservice euss ON euss.fkenduser = eu.pkid
JOIN subscribedservice s ON s.pkid = euss.fksubscribedservice
WHERE s.name = 'Extension Mobility'
```

**EM-Enabled Phones** -- which phones allow EM login:

The `allowExtensionMobility` flag is on the phone record. This field may or may not be in the current AXL `getPhone` response -- needs verification. If present, it's in the raw phone data already. If not, it needs to be added to the phone extraction.

**Auto-Logout Timer** -- configurable per user or via enterprise parameter:

```
Enterprise Parameter: "Extension Mobility Timer" (in minutes, 0=disabled)
Per-user: stored in device profile or service parameter
```

### 2c. Proposed New Extraction

Add to `FeatureExtractor` or create a new method on `UserExtractor`:

```python
raw_data["users"]["em_subscriptions"] = [
    {
        "userid": "jsmith",
        "service_name": "Extension Mobility",
        "subscribed": True,
    },
    ...
]
```

This extraction is optional -- the device profile ownership resolution in `DeviceProfileMapper._find_profile_owner()` already establishes user-to-profile mapping. The subscription data adds confirmation but is not strictly required.

---

## 3. Webex Target APIs

### 3a. Person-Level Hoteling (Guest Enable)

**Read:** `GET /people/{personId}/features/hoteling`

```json
{"enabled": true}
```

**Update:** `PUT /people/{personId}/features/hoteling`

```json
{"enabled": true}
```

**Scope:** `spark-admin:people_write` / `spark-admin:people_read`

**Mapping:** Every user who has a device profile (i.e., is EM-subscribed) should have hoteling enabled as a guest.

### 3b. Device-Level Hoteling (Host Configuration)

**Read:** Included in `GET /telephony/config/people/{personId}/devices` response under `hoteling` field.

```json
{
  "devices": [{
    "model": "Cisco 8845",
    "primaryOwner": true,
    "type": "PRIMARY",
    "hoteling": {
      "enabled": true,
      "limitGuestUse": true,
      "guestHoursLimit": 12
    }
  }]
}
```

**Update:** `PUT /telephony/config/people/{personId}/devices/settings/hoteling`

```json
{
  "hoteling": {
    "enabled": true,
    "limitGuestUse": true,
    "guestHoursLimit": 12
  }
}
```

**Scope:** `spark-admin:telephony_config_write`

**Mapping:** Phones that had `allowExtensionMobility=True` in CUCM should have their hoteling host settings enabled. The `guestHoursLimit` maps from CUCM's EM auto-logout timer.

### 3c. Hot Desking Voice Portal Sign-In

**Person-level:** `GET/PUT /telephony/config/people/{personId}/features/hotDesking/guest`

```json
{"voicePortalHotDeskSignInEnabled": true}
```

**Location-level:** `GET/PUT /telephony/config/locations/{locationId}/features/hotDesking`

```json
{"voicePortalHotDeskSignInEnabled": true}
```

**Scope:** `spark-admin:telephony_config_write` / `spark-admin:telephony_config_read`

**Mapping:** Locations with EM-enabled phones should have voice portal hot desking sign-in enabled at the location level. Individual users with EM profiles should have it enabled at the person level.

### 3d. Workspace Hot Desking

**Create/Update Workspace:** `POST/PUT /workspaces`

```json
{
  "displayName": "Shared Desk - Floor 3",
  "type": "desk",
  "hotdeskingStatus": "on",
  "supportedDevices": "phones",
  "calling": {
    "type": "webexCalling",
    "webexCalling": {"locationId": "Y2lzY29..."}
  }
}
```

**Mapping:** CUCM phones that were purely EM hosts (no personal user, just shared) map to workspaces with `hotdeskingStatus: "on"`. The `WorkspaceMapper` already creates workspaces for common-area phones -- this adds the hot desking enablement flag.

### 3e. Hot Desk Session Management

**List sessions:** `GET /hotdesk/sessions?personId={}&workspaceId={}`

**Delete session:** `DELETE /hotdesk/sessions/{sessionId}`

These are operational APIs -- not needed during migration, but useful for post-migration verification.

---

## 4. Migration Path

### 4a. What Maps Automatically

| CUCM Source | Webex Target | Mechanism |
|-------------|-------------|-----------|
| User has device profile | Person hoteling enabled (`/people/{id}/features/hoteling`) | New execution handler |
| Phone `allowExtensionMobility=True` | Device hoteling host enabled | New execution handler |
| EM auto-logout timer | `guestHoursLimit` on device hoteling | New execution handler (if timer data extracted) |
| Common-area EM-enabled phone | Workspace `hotdeskingStatus: "on"` | Enhanced WorkspaceMapper or new handler |
| Location with EM phones | Location hot desking voice portal enabled | New execution handler |

### 4b. What Requires Manual Setup or Is Lost

| CUCM Feature | Webex Equivalent | Why Manual / Lost |
|-------------|-----------------|-------------------|
| Multi-line device profile (2+ DNs) | Primary line only | Webex hot desking loads primary line only -- no multi-line profile concept |
| Profile-based speed dials | None | Webex hot desking does not carry speed dials from user profile to host device |
| Profile-based BLF entries | None | Webex hot desking does not carry BLF from user profile to host device |
| Profile-based services (XML) | None | CUCM IP phone services are not supported in Webex |
| Profile-based softkey layout | None | Webex hot desking does not carry softkey config from profile |
| Per-phone EM login screen customization | None | Webex login is via app pairing or voice portal, not phone screen |
| EM Cross-Cluster Extension Mobility (EMCC) | Not applicable | Webex is single-cluster; EMCC has no equivalent |
| Device profile to phone model binding | Not applicable | Webex hot desking is model-agnostic for the user |

### 4c. Feature Loss Severity by Use Case

| Use Case | Severity | Notes |
|----------|----------|-------|
| Simple hot desking (one line, no extras) | LOW | Maps cleanly -- user gets primary line on any workspace device |
| Shift worker with personal speed dials | MEDIUM | Speed dials lost during hot desk session; must use Webex app for personal contacts |
| Receptionist with multi-line EM profile | HIGH | Only primary line loads; receptionist loses all secondary lines during hot desk |
| EMCC cross-cluster roaming | N/A | Webex is single-cluster; feature not applicable |

---

## 5. Pipeline Integration

### 5a. Enhance DeviceProfileMapper

The existing `DeviceProfileMapper` produces decisions but no execution-ready data. Enhance it to:

1. **Set a `webex_hoteling_guest` flag** on the `CanonicalDeviceProfile` or associated `CanonicalUser` indicating this user needs hoteling enabled.

2. **Capture the EM auto-logout timer** if available in the device profile data, for mapping to `guestHoursLimit`.

3. **Cross-ref enhancement:** Add `device_profile_for_host_device` cross-ref linking the device profile to the phone(s) where it was used as default. This requires checking which phones reference this profile as their default.

### 5b. Enhance WorkspaceMapper

The `WorkspaceMapper` creates `CanonicalWorkspace` objects for common-area phones. Enhance it to:

1. **Check EM enablement** on the source phone. If the phone had `allowExtensionMobility=True` and is being migrated as a workspace, set `hotdesking_status="on"` on the `CanonicalWorkspace`.

2. **Add this to the workspace's `pre_migration_state`** so the execution handler knows to set `hotdeskingStatus: "on"` during workspace creation.

### 5c. New: HotelingMapper (or enhance DeviceProfileMapper)

A focused mapper that reads device profiles and EM signals, and produces execution-ready configuration:

**Option A: New HotelingMapper class**
- Dependencies: `device_profile_mapper`, `workspace_mapper`, `user_mapper`, `location_mapper`
- Reads: `CanonicalDeviceProfile` objects, `CanonicalWorkspace` objects, phone raw data
- Produces: `CanonicalHotelingConfig` objects with all Webex configuration parameters

**Option B: Enhance existing DeviceProfileMapper**
- Add hoteling configuration fields to `CanonicalDeviceProfile`
- Add execution-ready data (guest enable, host enable, hour limits) to the canonical object

Recommendation: **Option B** -- the `DeviceProfileMapper` already owns this domain and has the user ownership resolution logic. Adding hoteling config fields avoids a new mapper class and keeps the domain cohesive.

### 5d. Enhance Advisory Pattern 20

The existing `detect_extension_mobility_usage` pattern fires at `severity=LOW`. Enhance it to:

1. **Increase severity to MEDIUM** when profiles have multi-line or BLF entries (features that will be lost).
2. **Add execution gap context** -- note specifically that hoteling guest/host configuration, workspace hot desking, and location-level voice portal sign-in must be configured.
3. **Quantify feature loss** -- count profiles with multi-line, speed dials, BLF entries to surface the scope of feature gaps.

Updated pattern output:

```python
detail = (
    f"{len(profiles)} Extension Mobility device profile(s) found. "
    f"{multi_line_count} have multiple lines (will lose secondary lines). "
    f"{sd_count} have speed dials (will lose speed dials during hot desk). "
    f"{blf_count} have BLF entries (will lose BLF during hot desk). "
    f"Migration will enable Webex hoteling for these users and configure "
    f"workspace hot desking on their host devices. Users with multi-line "
    f"profiles will only get their primary line during hot desk sessions."
)
```

### 5e. New Recommendation Rule

Add a recommendation rule for `FEATURE_APPROXIMATION` decisions from the `DeviceProfileMapper`:

```python
def recommend_em_hotdesking(context, options):
    """EM profile → hot desking recommendation."""
    has_multi_line = context.get("line_count", 0) > 1
    has_features = context.get("speed_dial_count", 0) > 0 or context.get("blf_count", 0) > 0
    
    if not has_multi_line and not has_features:
        return ("accept", "Simple EM profile — maps cleanly to Webex hot desking with primary line.")
    
    if has_multi_line:
        return (
            "accept",
            f"EM profile has {context['line_count']} lines but Webex hot desking uses primary line only. "
            f"Accept the feature gap — secondary lines are not available during hot desk sessions."
        )
    
    return ("accept", "EM profile has speed dials/BLF that won't carry to hot desk sessions. Accept.")
```

This rule recommends "accept" for all EM profiles since there is no alternative to hot desking -- the feature gap is inherent to the Webex architecture.

### 5f. Report Enhancement

The Tier 4 appendix section V already shows EM profiles. Enhance it to:

1. **Feature loss summary table**: For each profile, show line count, speed dial count, BLF count, and a "feature loss" severity indicator.
2. **Execution plan preview**: Show what will be configured (hoteling guest enable, host enable, workspace hot desking).
3. **Training recommendation**: Note that users with complex EM profiles need training on Webex hot desking limitations.

### 5g. Execution Handlers

Three new handlers (or one composite handler):

**Handler 1: `handle_hoteling_guest_enable`**

```python
# For each user with a device profile:
PUT /people/{personId}/features/hoteling
Body: {"enabled": true}
```

**Handler 2: `handle_hoteling_host_configure`**

```python
# For each phone that was EM-enabled:
PUT /telephony/config/people/{personId}/devices/settings/hoteling
Body: {
    "hoteling": {
        "enabled": true,
        "limitGuestUse": True if auto_logout_timer else False,
        "guestHoursLimit": auto_logout_timer_hours or 12
    }
}
```

**Handler 3: `handle_location_hotdesking_enable`**

```python
# For each location with EM-enabled phones:
PUT /telephony/config/locations/{locationId}/features/hotDesking
Body: {"voicePortalHotDeskSignInEnabled": true}
```

**Workspace hot desking** is handled by the existing workspace creation handler by adding `hotdeskingStatus: "on"` to the workspace creation payload.

**Planner dependencies:**
- Handler 1 depends on: user creation
- Handler 2 depends on: user creation, device activation
- Handler 3 depends on: location creation
- Workspace hot desking depends on: workspace creation

---

## 6. Data Model Changes

### 6a. Enhance CanonicalDeviceProfile

Add fields to `CanonicalDeviceProfile` in `models.py`:

```python
@dataclass
class CanonicalDeviceProfile(MigrationObject):
    # Existing fields:
    profile_name: str = ""
    user_canonical_id: str = ""
    model: str = ""
    protocol: str = ""
    lines: list = field(default_factory=list)
    device_pool_name: str = ""
    speed_dial_count: int = 0
    blf_count: int = 0
    
    # New fields for execution:
    hoteling_guest_enabled: bool = False       # user should have hoteling enabled
    host_device_canonical_ids: list[str] = field(default_factory=list)  # phones where this was default profile
    auto_logout_minutes: int = 0              # CUCM EM timer, maps to guestHoursLimit
    location_canonical_id: str = ""           # resolved location for this profile's device pool
```

### 6b. Enhance CanonicalWorkspace

Add field to `CanonicalWorkspace`:

```python
hotdesking_enabled: bool = False  # set True when source phone had allowExtensionMobility
```

### 6c. No New DecisionType

Uses existing `FEATURE_APPROXIMATION` for feature loss decisions (already produced by `DeviceProfileMapper`).

### 6d. New Cross-Reference Types

- `device_profile_hosts_on_device` -- device profile → phone where it's used as EM default (inverse of existing `user_has_device_profile`)

---

## 7. Documentation Updates Required

### 7a. Reference Docs

- `docs/reference/person-call-settings-behavior.md` section 6 (Hoteling): Add migration context -- how CUCM EM maps to Webex hoteling, the person-level API is guest-only (single boolean), device-level API is host configuration.
- `docs/reference/devices-workspaces.md`: Add hot desking migration context for `hotdeskingStatus` field on workspaces.

### 7b. Knowledge Base

- `docs/knowledge-base/migration/kb-user-settings.md`: Add Extension Mobility to hot desking mapping details, feature loss table.
- `docs/knowledge-base/migration/kb-device-migration.md`: Add EM-enabled phone to hoteling host mapping.

### 7c. Runbooks

- `docs/runbooks/cucm-migration/decision-guide.md`: Add entry for EM-related `FEATURE_APPROXIMATION` decisions (multi-line loss, speed dial loss, BLF loss).
- `docs/runbooks/cucm-migration/tuning-reference.md`: Add hot desking configuration tuning (auto-logout timer mapping, location-level voice portal toggle).

### 7d. Migration CLAUDE.md

Update `src/wxcli/migration/CLAUDE.md`:
- Note that `DeviceProfileMapper` now produces execution-ready hoteling configuration
- Add execution handlers to the file map
- Update advisory pattern 20 description

---

## 8. Open Questions

1. **Is `allowExtensionMobility` in the current AXL `getPhone` response?** The phone extraction may or may not include this field. If it's present in the raw phone data, no new extraction is needed for host detection. If not, the `PhoneExtractor` needs a field addition. Needs verification against test bed data.

2. **EM auto-logout timer source.** The timer can be set at the enterprise parameter level, the service parameter level, or per-user. Which source(s) should the pipeline read? Recommendation: start with enterprise parameter (global default), enhance to per-user later.

3. **Workspace vs. person-owned phone distinction for host enable.** A phone assigned to a user (personal phone) that also has EM enabled is a different case than a common-area phone with EM. The user's phone uses device-level hoteling host settings; the common-area phone uses workspace hot desking. The pipeline needs to distinguish these two cases.

4. **Voice Portal hot desking sign-in.** Should this be enabled globally (all locations) or only at locations where EM phones were detected? Recommendation: only locations with EM phones, to avoid changing behavior at locations that never used EM.

5. **Interaction with device layout migration.** When a user hot desks onto a Webex device, they get their primary line only. But the `DeviceLayoutMapper` may have configured line key templates on the host device. How do these interact? Webex applies the host device's line key template to the guest's primary line. This is informational -- no pipeline change needed, but should be documented.

6. **Simple EM profiles (1 line, no extras) -- should they generate a decision?** Currently, the `DeviceProfileMapper` only creates `FEATURE_APPROXIMATION` decisions for profiles with multi-line or BLF/speed dial features. Simple profiles (1 line, 0 extras) do not generate decisions -- they map cleanly. Should we still flag them for operator awareness? Recommendation: no decision needed for simple profiles, but include them in the report count.

---

## 9. Implementation Estimate

| Component | Effort | Notes |
|-----------|--------|-------|
| Enhance DeviceProfileMapper (hoteling fields, host detection) | Medium | Adds fields + cross-refs + host device resolution |
| Enhance WorkspaceMapper (hotdesking_enabled flag) | Small | One field addition + conditional logic |
| Enhance advisory pattern 20 (severity, feature loss counts) | Small | Read additional fields from store |
| Add recommendation rule for EM decisions | Small | Always recommends "accept" with reasoning |
| Report enhancement (feature loss table) | Small | Extend existing Tier 4 section V |
| Execution handler: hoteling guest enable | Small | Single PUT per user |
| Execution handler: hoteling host configure | Medium | Device-level API, needs device ID resolution |
| Execution handler: location hot desking enable | Small | Single PUT per location |
| Workspace hot desking in creation payload | Small | Add field to existing workspace creation |
| Planner dependency wiring | Small | Add nodes + edges for 3 new handlers |
| Tests | Medium | Mapper enhancement, advisory, handlers, planner |
| Documentation updates | Small | 4 docs need sections |
| **Total** | **~3-4 days** | Can share mapper test fixtures with receptionist spec |

---

## 10. Relationship to Other Specs

- **Receptionist/Attendant Console Migration** (`2026-04-10-receptionist-attendant-migration.md`): Receptionists who use EM profiles to log into shared reception phones are at the intersection of both specs. The receptionist spec handles monitored member lists and contact directories; this spec handles the hoteling login mechanism. Both should reference each other.

- **Executive/Assistant Migration** (`2026-04-10-executive-assistant-migration.md`): Executives with EM profiles may hot desk into offices at different locations. Their executive/assistant pairing should persist regardless of which device they're logged into. Webex handles this at the user level (not device level), so no conflict -- but worth documenting.

- **Device Layout Migration** (existing `DeviceLayoutMapper`): Line key templates on host devices interact with hot desking guest sessions. The host device's template applies to the guest's primary line. No code change needed, but the report should note this interaction.
