# Platform Constraints: Migration Knowledge Base

<!-- Last verified: 2026-03-28 -->

> **Audience:** Migration advisor agent (Opus) and cold-context Claude sessions looking up dissent triggers, decision context, and Webex constraints for platform hard limits, feature gaps, and scope requirements.
> **Reading mode:** Reference. Grep by `DT-LIMITS-NNN` ID for dissent triggers, OR read `## Decision Framework` end-to-end when the migration-advisor agent loads this doc during analysis.
> **See also:** [Operator Runbook](../../runbooks/cucm-migration/operator-runbook.md) · [Decision Guide](../../runbooks/cucm-migration/decision-guide.md) · [Tuning Reference](../../runbooks/cucm-migration/tuning-reference.md)

This document is loaded for EVERY migration. It contains hard limits, feature gaps,
scope requirements, and license implications that the advisor must consider regardless
of which specific decision types are present.

## Decision Framework

Platform constraints should override a static recommendation when:

- **A recommendation would exceed a hard limit.** For example, recommending a Call Queue
  with Simultaneous routing when the source hunt list has 51+ agents. The CQ Simultaneous
  routing type caps at 50 agents -- the recommendation must account for the routing type.
- **A recommendation depends on a feature that does not exist in Webex.** For example,
  recommending partition-ordered CSS routing when Webex uses longest-match only.
- **A recommendation requires a license tier the customer may not have.** For example,
  recommending Customer Assist queue features when the customer lacks CX Essentials licenses.
- **A recommendation would push cumulative resource usage past an org-level limit.** For
  example, creating virtual extensions across multiple decisions that collectively exceed
  the org's virtual line capacity.

## Hard Limits

### Call Features

| Resource | Limit | Routing Type | Source |
|----------|-------|-------------|--------|
| Call Queue agents | 50 | SIMULTANEOUS | call-features-major.md comparison table (line 1282) |
| Call Queue agents | 100 | WEIGHTED | call-features-major.md comparison table (line 1283) |
| Call Queue agents | 1,000 | CIRCULAR / REGULAR / UNIFORM | call-features-major.md comparison table (line 1284) |
| Hunt Group agents | 50 | SIMULTANEOUS | call-features-major.md comparison table (line 1282) |
| Hunt Group agents | 100 | WEIGHTED | call-features-major.md comparison table (line 1283) |
| Hunt Group agents | 1,000 | CIRCULAR / REGULAR / UNIFORM | call-features-major.md comparison table (line 1284) |
| Auto Attendant alternate numbers | 10 | per AA | call-features-major.md (line 63) |
| Call Queue alternate numbers | 10 | per CQ | call-features-major.md (line 1180, 1195 — HGandCQ base class) |
| Hunt Group alternate numbers | 10 | per HG | call-features-major.md (line 797) |
| Paging Group targets | 75 | per group | call-features-additional.md (line 73, 222) |
| Call Pickup group membership | 1 group per user | user can only belong to one pickup group | call-features-additional.md (line 933) |
| Monitoring elements | 50 | per person/workspace (persons, places, virtual lines, call park extensions combined) | person-call-settings-media.md (line 1481, 1890) |
| Shared line appearances | 35 | per line | recommendation_rules.py (line 312); CLAUDE.md known issue -- not explicitly stated in reference docs as a hard limit, sourced from implementation/Cisco documentation |
| Auto Attendant per-location limit | Not documented in reference docs | Checked: call-features-major.md has no per-location AA cap | -- |
| Call Park Extensions per-location limit | Not documented in reference docs | Checked: call-features-additional.md has no per-location CPE cap | -- |
| Voicemail Group member limit | Not documented in reference docs | Checked: call-features-additional.md has no explicit member cap | -- |

### Routing

| Resource | Limit | Scope | Source |
|----------|-------|-------|--------|
| Dial Plans | Org-wide (not per-location) | Global routing namespace | call-routing.md (line 55) |
| Route Groups | Up to 10 trunks per group | Cross-location failover | call-routing.md (line 58, 820) |
| Translation Patterns | Org-level or location-level | Can be scoped either way | call-routing.md (line 60, 1325) |
| Trunk type change | Cannot change after creation | Must delete and recreate | call-routing.md (line 584) |
| Trunk location change | Cannot change after creation | Must delete and recreate | call-routing.md (line 584) |

### Identity & Numbers

| Resource | Limit | Notes | Source |
|----------|-------|-------|--------|
| Virtual lines per org | Not explicitly documented as a hard limit | API paginates at max=1000; LIMIT_EXCEEDED validation status exists in the VirtualExtensionValidationStatus enum, indicating an org-level cap exists but its value is not published in reference docs | virtual-lines.md (line 846) |
| Virtual extension range patterns | 100 per request | Bulk operations capped per API call | virtual-lines.md (line 726, 753) |
| Location name length (calling-enabled) | 80 characters | General API allows 256, but calling features enforce 80 | provisioning.md (line 627, 807) |
| Extension length | 2-6 digits (unknown extension routing) | Internal dialing routes unknown extensions of this length to premises PBX | location-call-settings-core.md (line 260) |

### Devices

| Resource | Limit | Notes | Source |
|----------|-------|-------|--------|
| Lines per device | Model-specific (`max_line_count` from API) | Returned by `supported_devices()` catalog and `members()` response | devices-core.md (line 448, 524) |
| Line key types | PRIMARY_LINE, SHARED_LINE, MONITOR, CALL_PARK_EXTENSION, SPEED_DIAL, OPEN, CLOSED, MODE_MANAGEMENT | Configurable via line key templates | devices-core.md (line 550) |

**Note on device line counts:** The exact `max_line_count` varies by phone model and is returned dynamically by the `supported_devices()` API or the device `members()` response. Common Cisco MPP models: 6821 (2 lines), 6841 (4 lines), 6851 (6 lines + KEM), 6861 (4 lines), 7811 (1 line), 7821 (2 lines), 7841 (4 lines), 7861 (16 lines), 8811 (1 line), 8841 (10 lines), 8851 (10 lines + KEM), 8861 (10 lines + KEM), 8865 (10 lines + KEM), 9841 (4 lines), 9851 (6 lines + KEM), 9861 (10 lines + KEM), 9871 (touch, configurable). These are approximate -- use the live API catalog for authoritative values.
- **Background image limit:** 100 images per org. Custom backgrounds require multipart upload before referencing in device settings.
- **Dynamic settings job:** Only 1 concurrent dynamic device settings job per org. Cannot run in parallel with other device jobs (settings push, rebuild phones).

### DECT Networks

| Resource | Limit | Scope | Notes | Source |
|----------|-------|-------|-------|--------|
| DECT networks | Not documented as a hard limit | Per location | No explicit cap found in reference docs; practical limit is base station and handset counts | devices-dect.md |
| Base stations per DBS-110 network | 1 | Per network | DBS-110 is a single-base model — one base station, up to 30 registered lines | devices-dect.md §3 |
| Base stations per DBS-210 network | Up to 250 | Per network | DBS-210 supports multi-cell roaming up to 250 base stations | devices-dect.md §3 |
| Handsets per DBS-110 network | 30 | Per network | Max 30 lines on DBS-110 | devices-dect.md §3 |
| Handsets per DBS-210 network | 1000 | Per network | Max 1000 lines on DBS-210 | devices-dect.md §3 |
| Handsets per bulk assign request | 50 | Per API call | `/dectNetworks/{id}/handsets/bulk` accepts max 50 per call; handler batches automatically | devices-dect.md |
| FedRAMP support | Not supported | Org-level | DECT networks cannot be provisioned on FedRAMP tenants | devices-dect.md |

**Migration note:** The pipeline auto-selects `DBS-110` for coverage zones with ≤30 handsets and `DBS-210` for >30. If a zone exceeds 1000 handsets (unusual), it must be split into multiple DECT networks — the pipeline does not split automatically and will raise a `DECT_NETWORK_DESIGN` decision.

### Users and Provisioning

| Resource | Limit | Notes | Source |
|----------|-------|-------|--------|
| Users per page with calling_data | 10 | SDK enforces MAX_USERS_WITH_CALLING_DATA = 10 for performance | provisioning.md (line 321-322) |

## Feature Gaps vs CUCM

Features that exist in CUCM but have no direct Webex Calling equivalent:

| CUCM Feature | Webex Status | Migration Approach | Source |
|-------------|-------------|-------------------|--------|
| Partition ordering (CSS) | No equivalent -- Webex uses longest-match routing | Manual review required; partition-dependent overlapping patterns may route differently | advisory_patterns.py Pattern 11 (detect_partition_ordering_loss) |
| Multi-level precedence (MLPP) | No equivalent | Out of scope for cloud migration | -- |
| Intercom | No native intercom feature | Workaround: speed dial, virtual line, or paging group (one-way only) | -- |
| Media Resource Group Lists (MRGL) | Cloud-managed | All media resources (conference bridges, transcoders, MTPs, MOH servers) managed by cloud automatically; no provisioning needed | advisory_patterns.py Pattern 15 (detect_media_resource_scope_removal) |
| Conference bridges | Cloud-managed | Webex provides cloud conferencing; no on-premises bridge provisioning | advisory_patterns.py Pattern 15 |
| Transcoders | Cloud-managed | Cloud handles media transcoding | advisory_patterns.py Pattern 15 |
| Time-of-day routing via partitions | No partition-based ToD routing | Use AA business/after-hours schedules or operating modes instead | advisory_patterns.py Pattern 7 (detect_partition_time_routing) |
| Complex CPN transformation chains | Flat caller ID model | CUCM chains transformations across 5 levels (line, RP, trunk, TG, SIP profile); Webex has per-user/per-location caller ID only | advisory_patterns.py Pattern 12 (detect_cpn_transformation_chain) |
| CTI Route Points with scripting | Partial -- AA covers simple cases | Complex IVR logic requires Webex Contact Center | -- |
| Service URL buttons | No equivalent | Use Webex App integrations or web clips on RoomOS devices | -- |
| Bulk phone service subscriptions | No equivalent | Managed by Webex cloud platform | -- |
| Extension Mobility (device profiles) | Hot desking | Webex hot desking is simpler -- no profile-level settings migration | advisory_patterns.py Pattern 20 (detect_extension_mobility_usage) |
| Single Number Reach (remote destinations) | SNR exists but differs | Webex SNR uses different config model; manual setup required | advisory_patterns.py Pattern 18 (detect_snr_configured_users) |
| Translation patterns for digit normalization | Often unnecessary | Webex handles E.164 normalization natively at the location level; many CUCM translation patterns are workarounds for localized dialing | advisory_patterns.py Pattern 2 (detect_translation_pattern_elimination) |

## Scope Requirements

Features requiring specific OAuth scopes and token types:

| Feature Area | Required Scope | Token Type | Error if Wrong | Source |
|-------------|---------------|------------|----------------|--------|
| Telephony config (read) | `spark-admin:telephony_config_read` | Admin or Service App | 403 | authentication.md (line 410) |
| Telephony config (write) | `spark-admin:telephony_config_write` | Admin or Service App | 403 | authentication.md (line 411) |
| Call control (user) | `spark:calls_read` / `spark:calls_write` | User-level OAuth | 400 "Target user not authorized" | call-control.md (line 38, 195); CLAUDE.md known issue #1 |
| Call control (admin) | `spark-admin:calls_read` / `spark-admin:calls_write` | Service App | -- | call-control.md (line 39-40) |
| /people/me/ settings | User-level OAuth (any `spark:` scope) | User-level only | 404 on admin tokens | self-service-call-settings.md (line 18); CLAUDE.md known issue #4 |
| CDR / reporting | `spark-admin:calling_cdr_read` | Admin or Service App | 403 | authentication.md (line 414) |
| People CRUD | `spark-admin:people_read` / `spark-admin:people_write` | Admin or Service App | 403 | authentication.md (line 415-416) |
| Customer Assist (read) | `spark-admin:telephony_config_read` + `spark-admin:people_read` | Admin or Service App | 403 | call-features-additional.md (line 60, 62) |
| Customer Assist (write) | `spark-admin:telephony_config_write` + `spark-admin:people_write` | Admin or Service App | 403 | call-features-additional.md (line 61, 63) |
| Contact Center APIs | `cjp:config_read` / `cjp:config_write` | CC-scoped OAuth | 403 | CLAUDE.md known issue #13 |
| Device configurations | `spark-admin:devices_write` (implied by admin token) | Admin or Service App | 403 | devices-core.md (device config operations) |

## License Implications

### Workspace Licenses

| Path Family | Basic License | Professional License | Source |
|------------|--------------|---------------------|--------|
| `/workspaces/{id}/features/callForwarding` | 200 OK | 200 OK | devices-workspaces.md (line 1356-1365) |
| `/workspaces/{id}/features/callWaiting` | 200 OK | 200 OK | devices-workspaces.md |
| `/workspaces/{id}/features/callerId` | 200 OK | 200 OK | devices-workspaces.md |
| `/workspaces/{id}/features/intercept` | 200 OK | 200 OK | devices-workspaces.md |
| `/workspaces/{id}/features/monitoring` | 200 OK | 200 OK | devices-workspaces.md |
| `/telephony/config/workspaces/{id}/musicOnHold` | 200 OK | 200 OK | devices-workspaces.md (line 1366) |
| `/telephony/config/workspaces/{id}/doNotDisturb` | 200 OK | 200 OK | devices-workspaces.md (line 1367) |
| `/telephony/config/workspaces/{id}/voicemail` | 405 "Invalid Professional Place" | 200 OK | devices-workspaces.md (line 1389) |
| `/telephony/config/workspaces/{id}/callRecording` | 405 | 200 OK | devices-workspaces.md (line 1374) |
| `/telephony/config/workspaces/{id}/callForwarding` | 405 | 200 OK | devices-workspaces.md (line 1372) |
| All other `/telephony/config/workspaces/{id}/` paths | 405 | 200 OK | devices-workspaces.md (line 1352, 1368-1389) |

**Rule of thumb:** Under `/telephony/config/workspaces/{id}/`, only `musicOnHold` and `doNotDisturb` work on Basic. Everything else returns 405. For Basic workspaces, use the `/workspaces/{id}/features/` path family (5 endpoints).

### User Licenses

| License | Purpose | Key Constraints | Source |
|---------|---------|----------------|--------|
| Webex Calling - Professional | Full calling features | Extension, DID, voicemail, forwarding, device support | admin-licensing.md (line 35) |
| Webex Calling - Standard | Basic calling | Limited features (no voicemail, restricted forwarding) | admin-licensing.md (line 36) |
| Webex Calling - Common Area | Shared devices | Lobby phones, break rooms | admin-licensing.md (line 37) |
| Customer Assist (CX Essentials) | Contact center agent add-on | Required for screen pop, wrap-up, queue recording, supervisors; requires Calling Professional as base | admin-licensing.md (line 38); call-features-additional.md (line 1346-1357) |
| Webex Attendant Console | Receptionist console | Requires Calling Professional as prerequisite | admin-licensing.md (line 39) |

### User-Only Settings (No Admin Path)

Six person call settings exist **only** at `/telephony/config/people/me/settings/{feature}`. There is no admin-path equivalent. Admin tokens get 404. A user-level OAuth token from the calling-licensed user is required.

| Setting | Scopes Required | Source |
|---------|----------------|--------|
| `simultaneousRing` | `spark:people_read` / `spark:people_write` | self-service-call-settings.md (line 26, 59) |
| `sequentialRing` | `spark:people_read` / `spark:people_write` | self-service-call-settings.md (line 26, 60) |
| `priorityAlert` | `spark:people_read` / `spark:people_write` | self-service-call-settings.md (line 26, 61) |
| `callNotify` | `spark:people_read` / `spark:people_write` | self-service-call-settings.md (line 26, 62) |
| `anonymousCallReject` | `spark:people_read` / `spark:people_write` | self-service-call-settings.md (line 26, 63) |
| `callPolicies` | `spark:people_read` / `spark:people_write` | self-service-call-settings.md (line 26, 64) |

**Migration impact:** If the CUCM deployment uses simultaneous ring, sequential ring, or priority alert extensively, these settings cannot be bulk-configured via admin token during migration. They require per-user OAuth flows or manual user self-service configuration.

### Recording

- Location-level recording vendor configuration must be set before per-user recording works (location-call-settings-advanced.md, line 33-50)
- Per-user recording has modes: Always, Never, On Demand with User Initiated Start (person-call-settings-media.md, line 998-999)
- Recording compliance announcement is location-level (location-call-settings-advanced.md, line 74)
- Queue call recording is a separate Customer Assist feature requiring CX Essentials license (call-features-additional.md, line 60-61)

## Dissent Triggers

### DT-LIMITS-001: CQ agent count exceeds simultaneous limit

**Condition:** FEATURE_APPROXIMATION decision recommends Call Queue AND context shows
agent_count > 50 AND the CUCM hunt list algorithm maps to Simultaneous routing
(e.g., Broadcast)

**Why static rule fails:** The recommendation_rules.py FEATURE_APPROXIMATION rule
recommends CQ at >8 agents without checking the 50-agent simultaneous routing cap.
Migrations with 51-100 agents work only with WEIGHTED routing. Migrations with
51-1,000 agents work with CIRCULAR, REGULAR, or UNIFORM routing.

**Advisor should:** Flag the routing type constraint. If the CUCM hunt list uses
Broadcast (maps to SIMULTANEOUS in Webex), the CQ must either:
1. Switch to a non-simultaneous routing type (CIRCULAR, REGULAR, UNIFORM support up to 1,000 agents; WEIGHTED supports up to 100)
2. Split into two queues with <=50 agents each using Simultaneous routing

**Confidence:** HIGH

### DT-LIMITS-002: Shared line appearances exceed 35 limit

**Condition:** SHARED_LINE_COMPLEX decision AND context shows appearance_count > 35

**Why static rule fails:** The recommendation_rules.py SHARED_LINE_COMPLEX rule
recommends "shared_line" for <=10 appearances but doesn't have a hard cap check.
Migrations with 36+ appearances on a single DN cannot use shared lines at all.

**Advisor should:** Recommend virtual extension for monitoring-only appearances +
shared line for active-use appearances, keeping the total shared line count under 35.
For lines with >35 appearances where all are active-use (not monitoring), the migration
requires splitting the DN across multiple numbers or restructuring the call flow.

**Confidence:** HIGH

### DT-LIMITS-003: Cumulative virtual line/extension consumption approaching org limit

**Condition:** Multiple DN_AMBIGUOUS or SHARED_LINE_COMPLEX decisions recommend
virtual_extension AND total virtual extension recommendations is high (approaching
org capacity)

**Why static rule fails:** Individual decisions don't track cumulative virtual line
consumption across the migration. Each decision independently recommends virtual
extensions without awareness of the aggregate count.

**Advisor should:** Flag cumulative count in cross-decision analysis. Suggest
prioritizing virtual extensions for true monitoring use cases (BLF/busy lamp field
only); use shared lines where the appearance count is <=35 and appearances involve
active call handling rather than just monitoring.

**Confidence:** MEDIUM (org limit value not published in reference docs; the
LIMIT_EXCEEDED validation status confirms a cap exists but does not specify the number)

### DT-LIMITS-004: Monitoring list exceeds 50 elements

**Condition:** Decision recommends monitoring configuration (BLF, shared line
monitoring) AND context shows total monitored elements > 50 for a single user

**Why static rule fails:** Monitoring element recommendations don't check the
per-user 50-element cap. A CUCM user with 60+ BLF speed dials cannot replicate
all of them as Webex monitored elements.

**Advisor should:** Recommend prioritizing the most critical monitored elements
(direct reports, key extensions) and using speed dials (non-monitoring) for the
remainder. Speed dials don't count against the 50-element monitoring limit.

**Confidence:** HIGH

### DT-LIMITS-005: Paging group target count exceeds 75

**Condition:** Migration includes paging groups AND source paging group has > 75
targets (members who receive pages)

**Why static rule fails:** Paging group migration may not check the 75-target cap.
CUCM paging groups (via InformaCast or native) may have larger membership.

**Advisor should:** Recommend splitting into multiple paging groups with <=75 targets
each. If the source uses IP multicast-based paging (InformaCast), note that Webex
paging is SIP-based unicast and may have different behavior at scale.

**Confidence:** HIGH
