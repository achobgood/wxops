<!-- Updated by playbook session 2026-03-18 -->
# Location Recording, Supervisor, Guest Calling, Conference & Misc

**CLI group:** `wxcli call-recording` (org-level recording vendor, compliance, per-location vendor assignment)
**NOT:** `wxcli location-call-settings` (that group handles dial patterns for premise PSTN — completely different domain)

## Sources

- wxc_sdk v1.30.0
- OpenAPI spec: specs/webex-cloud-calling.json
- developer.webex.com Location Call Settings APIs

Reference for advanced location-level and org-level call settings managed through the wxc_sdk. Covers call recording vendors and compliance, caller reputation (spam scoring), conference controls, supervisor/agent management, guest calling (click-to-call), operating modes, hot desking via voice portal, and shared forwarding patterns used across features.

---

## Table of Contents

1. [Call Recording](#1-call-recording)
2. [Caller Reputation](#2-caller-reputation)
3. [Conference Controls](#3-conference-controls)
4. [Supervisors](#4-supervisors)
5. [Guest Calling (Click-to-Call)](#5-guest-calling-click-to-call)
6. [Operating Modes](#6-operating-modes)
7. [Hot Desking Sign-in via Voice Portal](#7-hot-desking-sign-in-via-voice-portal)
8. [Forwarding (Shared Patterns)](#8-forwarding-shared-patterns)

---

## 1. Call Recording

**SDK module:** `wxc_sdk.telephony.call_recording`
**API class:** `CallRecordingSettingsApi` (base: `telephony/config`)
**Not supported** for Webex for Government (FedRAMP). See [authentication.md → FedRAMP](authentication.md#webex-for-government-fedramp) for all FedRAMP restrictions.

Call recording supports multiple third-party vendors. The org has an overall default vendor, but individual locations can override to a different vendor.

### 1.1 Scopes

| Operation | Scope |
|-----------|-------|
| Read | `spark-admin:telephony_config_read` |
| Write | `spark-admin:telephony_config_write` |

### 1.2 Data Models

#### `CallRecordingInfo`
Top-level org recording status.

| Field | Type | Notes |
|-------|------|-------|
| `organization` | `IdAndName` | Org id and name |
| `enabled` | `bool` | Whether call recording is enabled |
| `vendor_id` | `str` | Current vendor ID |
| `vendor_name` | `str` | Current vendor name |
| `terms_of_service_url` | `str` | Empty for Webex Recording Platform |

#### `CallRecordingTermsOfService`

| Field | Type | Notes |
|-------|------|-------|
| `vendor_id` | `str` | |
| `vendor_name` | `str` | |
| `terms_of_service_enabled` | `bool` | |
| `terms_of_service_url` | `str` | Empty for Webex Recording Platform |

#### `OrgComplianceAnnouncement`
Controls whether the recording START/STOP announcement plays on PSTN calls.

| Field | Type | Notes |
|-------|------|-------|
| `inbound_pstncalls_enabled` | `bool` | Alias: `inboundPSTNCallsEnabled` |
| `outbound_pstncalls_enabled` | `bool` | Alias: `outboundPSTNCallsEnabled` |
| `outbound_pstncalls_delay_enabled` | `bool` | Alias: `outboundPSTNCallsDelayEnabled` |
| `delay_in_seconds` | `int` | Seconds before announcement plays |

**Interaction note:** When the compliance announcement plays to the PSTN party and that party is connected to someone with call recording enabled, the start/stop announcement is inhibited.

#### `LocationComplianceAnnouncement` (extends `OrgComplianceAnnouncement`)

| Additional Field | Type | Notes |
|------------------|------|-------|
| `use_org_settings_enabled` | `bool` | Use org-level defaults |

#### `FailureBehavior` (Enum)
What happens when recording fails:

| Value | Behavior |
|-------|----------|
| `PROCEED_WITH_CALL_NO_ANNOUNCEMENT` | Call continues, no announcement |
| `PROCEED_CALL_WITH_ANNOUNCEMENT` | Call continues, announcement plays |
| `END_CALL_WITH_ANNOUNCEMENT` | Call ends with announcement |

#### `RecordingVendor`

| Field | Type |
|-------|------|
| `id` | `str` |
| `name` | `str` |
| `description` | `str` |
| `migrate_user_creation_enabled` | `bool` |
| `login_url` | `str` |
| `terms_of_service_url` | `str` |

#### `CallRecordingVendors` (org-level)

| Field | Type | Notes |
|-------|------|-------|
| `vendor_id` | `str` | Current vendor |
| `vendor_name` | `str` | |
| `vendors` | `list[RecordingVendor]` | All available vendors |
| `storage_region` | `str` | Only for Webex vendor |
| `failure_behavior` | `FailureBehavior` | |

#### `CallRecordingLocationVendors`

| Field | Type | Notes |
|-------|------|-------|
| `org_default_enabled` | `bool` | |
| `org_default_vendor_id` | `str` | |
| `org_default_vendor_name` | `str` | |
| `default_vendor_id` | `str` | Location-level vendor |
| `default_vendor_name` | `str` | |
| `vendors` | `list[RecordingVendor]` | |
| `org_storage_region_enabled` | `bool` | |
| `org_storage_region` | `str` | |
| `storage_region` | `str` | Location-level region |
| `org_failure_behavior_enabled` | `bool` | |
| `org_failure_behavior` | `FailureBehavior` | |
| `failure_behavior` | `FailureBehavior` | Location-level |

#### `CallRecordingRegion`

| Field | Type |
|-------|------|
| `code` | `str` — two-character region code |
| `name` | `str` |
| `default_enabled` | `bool` |

#### `RecordingUser`

| Field | Type |
|-------|------|
| `id` | `str` |
| `first_name` | `str` |
| `last_name` | `str` |
| `type` | `UserType` |
| `license_type` | `UserLicenseType` |

### 1.3 API Methods

```python
class CallRecordingSettingsApi:

    # --- Org-level recording on/off ---
    def read(self, org_id: str = None) -> CallRecordingInfo
    def update(self, enabled: bool, org_id: str = None)  # Cisco partners only

    # --- Terms of service ---
    def read_terms_of_service(self, vendor_id: str, org_id: str = None) -> CallRecordingTermsOfService
    def update_terms_of_service(self, vendor_id: str, enabled: bool, org_id: str = None)

    # --- Compliance announcement (org) ---
    def read_org_compliance_announcement(self, org_id: str = None) -> OrgComplianceAnnouncement
    def update_org_compliance_announcement(self, settings: OrgComplianceAnnouncement, org_id: str = None)

    # --- Compliance announcement (location) ---
    def read_location_compliance_announcement(self, location_id: str, org_id: str = None) -> LocationComplianceAnnouncement
    def update_location_compliance_announcement(self, location_id: str, settings: LocationComplianceAnnouncement, org_id: str = None)

    # --- Regions ---
    def get_call_recording_regions(self, org_id: str = None) -> list[CallRecordingRegion]

    # --- Vendor users (org) ---
    def list_org_users(self, standard_user_only: bool = None, org_id: str = None, **params) -> Generator[RecordingUser]

    # --- Vendor management (org) ---
    def get_org_vendors(self, org_id: str = None) -> CallRecordingVendors
    def set_org_vendor(self, vendor_id: str, storage_region: str = None,
                       failure_behavior: FailureBehavior = None, org_id: str = None) -> str  # returns jobId

    # --- Vendor management (location) ---
    def get_location_vendors(self, location_id: str, org_id: str = None) -> CallRecordingLocationVendors
    def set_location_vendor(self, location_id: str, id: str = None,
                            org_default_enabled: bool = None, storage_region: str = None,
                            org_storage_region_enabled: bool = None,
                            failure_behavior: FailureBehavior = None,
                            org_failure_behavior_enabled: bool = None,
                            org_id: str = None) -> str  # returns jobId

    # --- Vendor users (location) ---
    def list_location_users(self, location_id: str, standard_user_only: bool = None,
                            org_id: str = None, **params) -> Generator[RecordingUser]
```

### 1.4 Raw HTTP — Call Recording

```python
BASE = "https://webexapis.com/v1"

# --- Org-level recording on/off ---
# GET — Get call recording settings
result = api.session.rest_get(f"{BASE}/telephony/config/callRecording")
# Response: {"organization": {"id": "...", "name": "..."}, "enabled": true,
#            "vendorId": "...", "vendorName": "...", "termsOfServiceUrl": ""}

# PUT — Enable/disable call recording (Cisco partners only)
body = {"enabled": True}
api.session.rest_put(f"{BASE}/telephony/config/callRecording", json=body)

# --- Terms of service ---
# GET
result = api.session.rest_get(f"{BASE}/telephony/config/callRecording/vendors/{vendor_id}/termsOfService")
# PUT
body = {"termsOfServiceEnabled": True}
api.session.rest_put(f"{BASE}/telephony/config/callRecording/vendors/{vendor_id}/termsOfService", json=body)

# --- Compliance announcement (org) ---
# GET
result = api.session.rest_get(f"{BASE}/telephony/config/callRecording/complianceAnnouncement")
# Response: {"inboundPSTNCallsEnabled": false, "outboundPSTNCallsEnabled": false,
#            "outboundPSTNCallsDelayEnabled": false, "delayInSeconds": 3}

# PUT
body = {
    "inboundPSTNCallsEnabled": True,
    "outboundPSTNCallsEnabled": True,
    "outboundPSTNCallsDelayEnabled": True,
    "delayInSeconds": 5
}
api.session.rest_put(f"{BASE}/telephony/config/callRecording/complianceAnnouncement", json=body)

# --- Compliance announcement (location) ---
# GET
result = api.session.rest_get(
    f"{BASE}/telephony/config/locations/{loc_id}/callRecording/complianceAnnouncement"
)
# Response includes useOrgSettingsEnabled

# PUT
body = {
    "useOrgSettingsEnabled": False,
    "inboundPSTNCallsEnabled": True,
    "outboundPSTNCallsEnabled": True,
    "outboundPSTNCallsDelayEnabled": True,
    "delayInSeconds": 3
}
api.session.rest_put(
    f"{BASE}/telephony/config/locations/{loc_id}/callRecording/complianceAnnouncement",
    json=body
)

# --- Regions ---
# GET
result = api.session.rest_get(f"{BASE}/telephony/config/callRecording/regions")
# Response: {"regions": [{"code": "US", "name": "United States", "defaultEnabled": true}]}

# --- Vendor users (org) ---
# GET (paginated)
result = api.session.rest_get(f"{BASE}/telephony/config/callRecording/vendorUsers",
    params={"max": 1000, "standardUserOnly": True})
# Response: {"vendorUsers": [...]}

# --- Vendor management (org) ---
# GET — Get org vendors
result = api.session.rest_get(f"{BASE}/telephony/config/callRecording/vendors")

# PUT — Set org vendor (returns jobId)
body = {"vendorId": "<vendor_id>", "storageRegion": "US", "failureBehavior": "PROCEED_WITH_CALL_NO_ANNOUNCEMENT"}
result = api.session.rest_put(f"{BASE}/telephony/config/callRecording/vendor", json=body)
# Response 200: {"jobId": "..."} or 204 for immediate

# --- Vendor management (location) ---
# GET — Get location vendors
result = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/callRecording/vendors")

# PUT — Set location vendor (returns jobId)
body = {
    "id": "<vendor_id>",
    "orgDefaultEnabled": False,
    "storageRegion": "US",
    "orgStorageRegionEnabled": False,
    "failureBehavior": "PROCEED_WITH_CALL_NO_ANNOUNCEMENT",
    "orgFailureBehaviorEnabled": False
}
result = api.session.rest_put(f"{BASE}/telephony/config/locations/{loc_id}/callRecording/vendor", json=body)

# --- Vendor users (location) ---
# GET (paginated)
result = api.session.rest_get(
    f"{BASE}/telephony/config/locations/{loc_id}/callRecording/vendorUsers",
    params={"max": 1000, "standardUserOnly": True}
)

# --- Call Recording Jobs ---
# GET — List jobs
result = api.session.rest_get(f"{BASE}/telephony/config/jobs/callRecording", params={"max": 100})

# GET — Job status
result = api.session.rest_get(f"{BASE}/telephony/config/jobs/callRecording/{job_id}")

# GET — Job errors
result = api.session.rest_get(f"{BASE}/telephony/config/jobs/callRecording/{job_id}/errors")
```

### 1.5 CLI Examples

```bash
# Get org-level call recording settings
wxcli call-recording show

# Get org-level compliance announcement settings
wxcli call-recording show-compliance-announcement-call-recording

# Enable compliance announcement for inbound PSTN calls with 5-second delay
wxcli call-recording update-compliance-announcement-call-recording \
  --inbound-pstn-calls-enabled --outbound-pstn-calls-enabled \
  --outbound-pstn-calls-delay-enabled --delay-in-seconds 5

# Get location-level compliance announcement settings
wxcli call-recording show-compliance-announcement-call-recording-1 <location_id>

# Get org-level recording vendors
wxcli call-recording show-vendors

# Get location-level recording vendors
wxcli call-recording list-vendors <location_id>

# Set recording vendor for a location
wxcli call-recording update-vendor-call-recording <location_id> \
  --id <vendor_id> --no-org-default-enabled \
  --storage-region US --no-org-storage-region-enabled

# List call recording regions
wxcli call-recording list

# List vendor users at org level (paginated)
wxcli call-recording list-vendor-users-call-recording

# List vendor users at location level
wxcli call-recording list-vendor-users-call-recording-1 <location_id>

# List call recording jobs
wxcli call-recording list-call-recording

# Get status of a specific recording job
wxcli call-recording show-call-recording <job_id>

# Get errors for a recording job
wxcli call-recording list-errors <job_id>
```

### 1.6 Key Behaviors

- `set_org_vendor()` and `set_location_vendor()` return a **job ID** (string). Use the jobs API to check status if the change cannot be applied immediately (HTTP 200 with jobId vs. 204 for immediate).
- `update()` (enable/disable recording) is **Cisco partners only**.
- Storage region is **only applicable when vendor is Webex**; ignored for third-party vendors.
- `standard_user_only` parameter filters to Webex Calling standard license users only.

---

## 2. Caller Reputation

**SDK module:** `wxc_sdk.telephony.caller_reputation`
**API class:** `CallerReputationProviderApi` (base: `telephony/config/serviceSettings/callerReputationProvider`)

Integrates with external calling reputation providers for spam/fraud call scoring.

### 2.1 Data Models

#### `ReputationProviderSettings`

| Field | Type | Notes |
|-------|------|-------|
| `name` | `str` | Provider name |
| `id` | `str` | Provider ID |
| `client_id` | `str` | OAuth client ID for integration |
| `client_secret` | `str` | Write-only; not returned on read |
| `enabled` | `bool` | Service enabled/disabled |
| `call_block_score_threshold` | `str` | Score at which calls are blocked |
| `call_allow_score_threshold` | `str` | Score at which calls are allowed |

#### `ReputationProviderState` (Enum)

| Value | Meaning |
|-------|---------|
| `NOT_CONNECTED` | Not connected |
| `CONNECTING` | Connection in progress |
| `CONNECTED` | Connected |
| `ACTIVE` | Active and operational |
| `EXPIRED` | Session/token expired |
| `AUTH_FAILED` | Authentication failed |
| `PROVIDER_DISABLED` | Provider disabled |

#### `ReputationProviderStatus`

| Field | Type |
|-------|------|
| `id` | `str` |
| `status` | `ReputationProviderState` |

#### `ReputationProviderRegion`

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | |
| `name` | `str` | |
| `type` | `str` | e.g., primary, secondary |
| `visible` | `bool` | |
| `environment_type` | `str` | e.g., production, staging |

#### `CallerReputationProviderProvider`

| Field | Type |
|-------|------|
| `id` | `str` |
| `enabled` | `bool` |
| `name` | `str` |
| `regions` | `list[ReputationProviderRegion]` |

### 2.2 API Methods

```python
class CallerReputationProviderApi:

    def get(self, organization_id: str = None) -> ReputationProviderSettings
    def update(self, settings: ReputationProviderSettings, organization_id: str = None)
    def unlock(self, rep_id: str, organization_id: str = None)
    def providers(self, organization_id: str = None) -> list[CallerReputationProviderProvider]
    def status(self, organization_id: str = None) -> ReputationProviderStatus
```

### 2.3 Raw HTTP — Caller Reputation

```python
BASE = "https://webexapis.com/v1"

# GET — Get caller reputation provider settings
result = api.session.rest_get(
    f"{BASE}/telephony/config/serviceSettings/callerReputationProvider")
# Response: {"name": "...", "id": "...", "clientId": "...", "enabled": true,
#            "callBlockScoreThreshold": "80", "callAllowScoreThreshold": "20"}
# Note: clientSecret is NEVER returned by GET

# PUT — Update caller reputation provider settings
body = {
    "enabled": True,
    "id": "<provider_id>",
    "name": "Provider Name",
    "clientId": "<oauth_client_id>",
    "clientSecret": "<oauth_client_secret>",
    "callBlockScoreThreshold": "80",
    "callAllowScoreThreshold": "20"
}
api.session.rest_put(
    f"{BASE}/telephony/config/serviceSettings/callerReputationProvider", json=body)

# GET — Get provider status
result = api.session.rest_get(
    f"{BASE}/telephony/config/serviceSettings/callerReputationProvider/status")
# Response: {"id": "...", "status": "CONNECTED"}

# GET — List available providers
result = api.session.rest_get(
    f"{BASE}/telephony/config/serviceSettings/callerReputationProvider/providers")
# Response: {"providers": [{"id": "...", "enabled": true, "name": "...",
#            "regions": [{"id": "...", "name": "...", "type": "primary", "visible": true}]}]}

# POST — Unlock a locked provider
body = {"id": "<provider_id>"}
api.session.rest_post(
    f"{BASE}/telephony/config/serviceSettings/callerReputationProvider/actions/unlock/invoke",
    json=body)
```

**Gotcha:** This API uses `organizationId` as the query parameter (not `orgId` like most other telephony APIs).

**Gotcha:** Score thresholds are strings, not integers.
<!-- Updated by playbook session 2026-03-18 -->

### 2.4 CLI Examples

```bash
# Get caller reputation provider settings
wxcli caller-reputation show

# Get caller reputation provider status
wxcli caller-reputation show-status

# List available caller reputation providers
wxcli caller-reputation list

# Update caller reputation provider settings
wxcli caller-reputation update \
  --enabled --id <provider_id> --name "Provider Name" \
  --client-id <oauth_client_id> --client-secret <oauth_client_secret> \
  --call-block-score-threshold "80" --call-allow-score-threshold "20"

# Unlock a locked caller reputation provider
wxcli caller-reputation unlock-caller-reputation

# Query for a specific org (partner scenario)
wxcli caller-reputation show --organization-id <org_id>
```

### 2.5 Key Behaviors

- **`client_secret` is write-only** -- it is never returned by `get()`. Only usable in `update()`.
- The `unlock()` method invokes `actions/unlock/invoke` -- use this when the provider is in a locked state (e.g., after auth failure). <!-- UNVERIFIABLE: exact conditions that trigger a locked state are not documented in SDK or OpenAPI spec; would need live API testing -->
- Note the parameter is `organization_id` (not `org_id`) in this API, differing from most other telephony APIs.
- Score thresholds are strings, not integers. The OpenAPI spec examples show decimal numeric strings (e.g., `"0.7"`, `"0.3"`), not integer strings.

---

## 3. Conference Controls

**SDK module:** `wxc_sdk.telephony.conference`
**API class:** `ConferenceControlsApi` (base: `telephony/conference`)

Runtime conference call management (not configuration). This is a **call-control** API, not an admin config API.

### 3.1 Scopes

| Operation | Scope |
|-----------|-------|
| GET | `spark:calls_read` |
| All others | `spark:calls_write` |

### 3.2 Data Models

#### `ConferenceState` (Enum)

| Value | Meaning |
|-------|---------|
| `connected` | Host is active participant |
| `held` | Host has held the conference |
| `disconnected` | Conference released |

#### `ConferenceTypeEnum` (Enum)

| Value | Usage |
|-------|-------|
| `bargeIn` | Barge-in conference |
| `silentMonitoring` | Silent monitoring |
| `coaching` | Coaching session |

#### `ConferenceParticipant`

| Field | Type | Notes |
|-------|------|-------|
| `call_id` | `str` | Call identifier for this participant |
| `muted` | `bool` | |
| `deafened` | `bool` | Media not transmitted to participant |

#### `ConferenceDetails`

| Field | Type | Notes |
|-------|------|-------|
| `state` | `ConferenceState` | |
| `appearance` | `int` | Appearance index (if assigned) |
| `created` | `datetime` | ISO 8601 start time |
| `muted` | `bool` | Host muted |
| `type` | `ConferenceTypeEnum` | Only for non-standard conferences |
| `participants` | `list[ConferenceParticipant]` | |

### 3.3 API Methods

```python
class ConferenceControlsApi:

    def start_conference(self, call_ids: list[str], line_owner_id: str = None)
    def get_conference_details(self, line_owner_id: str = None) -> ConferenceDetails
    def release_conference(self, line_owner_id: str = None)
    def add_participant(self, call_id: str, line_owner_id: str = None)
    def hold(self, line_owner_id: str = None)
    def resume(self, line_owner_id: str = None)
    def mute(self, call_id: str = None)       # host if call_id omitted
    def unmute(self, call_id: str = None)      # host if call_id omitted
    def deafen_participant(self, call_id: str)
    def undeafen_participant(self, call_id: str)
```

### 3.4 CLI Examples

```bash
# Get current conference details (requires user-level OAuth token)
wxcli conference list

# Get conference details for a specific line owner
wxcli conference list --line-owner-id <user_id>

# Start a conference by merging two active calls
wxcli conference create --json-body '{"callIds": ["call_id_1", "call_id_2"]}'

# Add a participant to an active conference
wxcli conference create-add-participant --json-body '{"callId": "call_id_3"}'

# Hold / resume the conference
wxcli conference create-hold
wxcli conference create-resume

# Mute the host
wxcli conference create-mute

# Mute a specific participant
wxcli conference create-mute --json-body '{"callId": "participant_call_id"}'

# Unmute
wxcli conference create-unmute

# Deafen / undeafen a participant
wxcli conference create-deafen --json-body '{"callId": "participant_call_id"}'
wxcli conference create-undeafen --json-body '{"callId": "participant_call_id"}'

# Release (end) the conference
wxcli conference delete
```

> **Note:** Conference controls require a **user-level OAuth token** (`spark:calls_write` scope). Admin tokens will not work. See Known Issues in CLAUDE.md.

### 3.5 Key Behaviors

- **`start_conference()`** requires a minimum of **two call IDs**. Each must identify an existing call between the invoking user and a participant.
- **`get_conference_details()`** returns an **empty JSON object** if no conference exists.
- **Mute vs. Deafen**: Muting stops a participant's audio from being transmitted to the conference. Deafening stops the conference audio from being transmitted to the participant. They are independent.
- **`mute()` / `unmute()`** operate on the host when `call_id` is omitted, or on a specific participant when provided.
- **`line_owner_id`** is used when invoking the API on behalf of a secondary line owner (user, workspace, or virtual line).
- For three-way calls (3WC), the Transfer API can be used instead of `release_conference()` to keep participants connected while the host drops.

---

## 4. Supervisors

> For the full Customer Assist setup workflow including supervisors, use the **customer-assist** skill.

**SDK module:** `wxc_sdk.telephony.supervisor`
**API class:** `SupervisorApi` (base: `telephony/config/supervisors`)

Supervisors manage call queue agents. They can silently monitor, coach, barge in, or take over calls their agents are handling.

### 4.1 Scopes

| Operation | Scope |
|-----------|-------|
| Read | `spark-admin:telephony_config_read` |
| Write | `spark-admin:telephony_config_write` |

### 4.2 Data Models

#### `AgentOrSupervisor`
Used for both supervisor and agent listings.

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | |
| `first_name` | `str` | |
| `last_name` | `str` | |
| `display_name` | `str` | |
| `phone_number` | `str` | |
| `extension` | `str` | |
| `routing_prefix` | `str` | Location routing prefix |
| `esn` | `str` | Routing prefix + extension |
| `type` | `UserType` | Person, workspace, or virtual line |
| `has_cx_essentials` | `bool` | Has Customer Assist (formerly CX Essentials) license |
| `agent_count` | `int` | Agents managed (supervisors only) |

#### `IdAndAction`

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | Person, workspace, or virtual line ID |
| `action` | `PatternAction` | `ADD` or `DELETE` |

#### `SupervisorAgentStatus`

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | |
| `status` | `str` | Status result |
| `message` | `str` | Detail message |
| `type` | `UserType` | SDK-only field; absent from OpenAPI spec `ListSupervisorAgentStatusObject`. SDK marks as `# TODO: undocumented, issue 202`  |

### 4.3 API Methods

```python
class SupervisorApi:

    # --- List / search ---
    def list(self, name: str = None, phone_number: str = None, order: str = None,
             has_cx_essentials: bool = None, org_id: str = None,
             **params) -> Generator[AgentOrSupervisor]

    def available_supervisors(self, name: str = None, phone_number: str = None, order: str = None,
                              has_cx_essentials: bool = None, org_id: str = None,
                              **params) -> Generator[AgentOrSupervisor]

    def available_agents(self, name: str = None, phone_number: str = None, order: str = None,
                         has_cx_essentials: bool = None, org_id: str = None,
                         **params) -> Generator[AgentOrSupervisor]

    # --- CRUD ---
    def create(self, id: str, agents: list[str], has_cx_essentials: bool = None, org_id: str = None)
    def delete(self, supervisor_id: str, org_id: str = None)
    def delete_bulk(self, supervisors_ids: list[str], delete_all: bool = None, org_id: str = None)

    # --- Details and agent assignment ---
    def details(self, supervisor_id: str, name: str = None, phone_number: str = None,
                order: str = None, has_cx_essentials: bool = None,
                org_id: str = None, **additional_params) -> Generator[AgentOrSupervisor]

    def assign_unassign_agents(self, supervisor_id: str, agents: list[IdAndAction],
                               has_cx_essentials: bool = None,
                               org_id: str = None) -> Optional[list[SupervisorAgentStatus]]
```

### 4.4 CLI Examples

Supervisor commands are under the `wxcli call-queue` group. **For Customer Assist supervisors, always include `--has-cx-essentials true`.**

```bash
# List all Customer Assist supervisors
wxcli call-queue list-supervisors --has-cx-essentials true

# List available supervisors (not yet assigned)
wxcli call-queue list-available-supervisors --has-cx-essentials true

# List available agents for supervisor assignment
wxcli call-queue list-available-agents-supervisors --has-cx-essentials true

# Create a supervisor with agents
wxcli call-queue create-supervisors --has-cx-essentials true \
  --id SUPERVISOR_PERSON_ID --json-body '{"agents": [{"id": "AGENT_ID"}]}'

# Show supervisor's assigned agents
wxcli call-queue show-supervisors SUPERVISOR_ID --has-cx-essentials true -o json

# Update supervisor's agents (incremental add/remove)
wxcli call-queue update-supervisors SUPERVISOR_ID --has-cx-essentials true \
  --json-body '{"agents": [{"id": "AGENT_ID", "action": "ADD"}]}'

# Delete a specific supervisor
wxcli call-queue delete-supervisors-config-1 SUPERVISOR_ID --has-cx-essentials true --force

# Delete supervisors in bulk
wxcli call-queue delete-supervisors-config --has-cx-essentials true --force

# RECOMMENDED: Remove supervisor by removing all agents (more reliable)
wxcli call-queue update-supervisors SUPERVISOR_ID --has-cx-essentials true \
  --json-body '{"agents": [{"id": "AGENT_ID", "action": "DELETE"}]}'
# When last agent is removed, supervisor is auto-deleted
```

> **WARNING:** `delete-supervisors-config --force` without specifying IDs may remove **all supervisors in the org**. Always confirm scope before executing.

> **GOTCHA:** `delete-supervisors-config-1` returns 204 but the Customer Assist supervisor may persist. The reliable method is to remove all agents via `update-supervisors` with `action: DELETE` — when the last agent is removed, the supervisor is automatically deleted.

### 4.5 Key Behaviors

- **A supervisor must have at least one agent** when created via `create()`.
- **`create()` takes agent IDs as a flat `list[str]`**, not `IdAndAction` objects. The SDK wraps them as `[{'id': agent_id}]` internally.
- **`assign_unassign_agents()`** uses `IdAndAction` with `PatternAction.ADD` or `PatternAction.DELETE` to add/remove agents in a single call. Returns `None` if all succeed, or a list of `SupervisorAgentStatus` with per-agent error details.
- **`delete_bulk()`** has a `delete_all` parameter. When set to `True`, the `supervisors_ids` array is ignored and **all supervisors in the org are removed**. Use with extreme caution.
- **Customer Assist vs. CX Basic**: The `has_cx_essentials` parameter gates which license tier you are querying/modifying. When `True`, returns/operates on Customer Assist supervisors only. When omitted or `False`, operates on CX Basic.
- **`details()`** returns a generator of the supervisor's assigned **agents** (not the supervisor's own details). The item key is `agents`.

---

## 5. Guest Calling (Click-to-Call)

**SDK module:** `wxc_sdk.telephony.guest_calling`
**API class:** `GuestCallingApi` (base: `telephony/config/guestCalling`)

Click-to-call allows external (guest) callers to reach internal destinations. Org-level setting.

### 5.1 Scopes

| Operation | Scope |
|-----------|-------|
| Read | `spark-admin:telephony_config_read` |
| Write | `spark-admin:telephony_config_write` |

### 5.2 Data Models

#### `GuestCallingSettings`

| Field | Type | Notes |
|-------|------|-------|
| `enabled` | `bool` | Click-to-call enabled |
| `privacy_enabled` | `bool` | Privacy mode |
| `video_enabled` | `bool` | SDK-only field with no docstring; absent from all OpenAPI specs. May be undocumented or deprecated  |

#### `DestinationMember`

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | |
| `first_name` | `str` | |
| `last_name` | `str` | |
| `phone_number` | `str` | |
| `extension` | `str` | |
| `routing_prefix` | `str` | |
| `esn` | `str` | |
| `type` | `OwnerType` | |
| `location` | `IdAndName` | |

### 5.3 API Methods

```python
class GuestCallingApi:

    def read(self, org_id: str = None) -> GuestCallingSettings
    def update(self, enabled: bool, privacy_enabled: bool,
               destination_members: list[str], org_id: str = None)
    def members(self, member_name: str = None, phone_number: str = None,
                extension: str = None, org_id: str = None,
                **params) -> Generator[DestinationMember]
    def available_members(self, member_name: str = None, phone_number: str = None,
                          extension: str = None, org_id: str = None,
                          **params) -> Generator[DestinationMember]
```

### 5.4 CLI Examples

There is no dedicated `wxcli` guest-calling (click-to-call) command group. Use the SDK methods or Raw HTTP calls. The `guest-management` group covers a different feature (guest user creation), not click-to-call destinations.

### 5.5 Key Behaviors

- **Supported destination types**: Auto Attendant, Call Queue, Hunt Group, and Virtual Line. Not individual users.
- **`update()` takes destination member IDs** as a flat `list[str]`, not full `DestinationMember` objects.
- **`members()`** returns currently assigned click-to-call destinations.
- **`available_members()`** returns destinations that can be added but are not yet assigned.
- All search parameters (`member_name`, `phone_number`, `extension`) use **contains** matching.

---

## 6. Operating Modes

**SDK module:** `wxc_sdk.telephony.operating_modes`
**API class:** `OperatingModesApi` (base: `telephony/config`)

Operating modes define time-based call routing rules (business hours, after hours, holidays, etc.) used by Auto Attendants, Call Queues, and Hunt Groups via mode-based forwarding.

### 6.1 Scopes

| Operation | Scope |
|-----------|-------|
| Read | `spark-admin:telephony_config_read` |
| Write | `spark-admin:telephony_config_write` |

### 6.2 Data Models

#### `OperatingModeSchedule` (Enum)

| Value | Meaning |
|-------|---------|
| `SAME_HOURS_DAILY` | Same schedule Mon-Fri and Sat-Sun |
| `DIFFERENT_HOURS_DAILY` | Per-day schedule |
| `HOLIDAY` | Holiday-based with recurrence |
| `NONE` | No schedule defined |

#### `DaySchedule`

| Field | Type | Notes |
|-------|------|-------|
| `enabled` | `bool` | Schedule active for this day/group |
| `all_day_enabled` | `bool` | Active entire day |
| `start_time` | `time` | HH:MM format |
| `end_time` | `time` | HH:MM format |

#### `SameHoursDaily`

| Field | Type |
|-------|------|
| `monday_to_friday` | `DaySchedule` |
| `saturday_to_sunday` | `DaySchedule` |

#### `DifferentHoursDaily`
Individual `DaySchedule` fields for: `sunday`, `monday`, `tuesday`, `wednesday`, `thursday`, `friday`, `saturday`.

#### `OperatingModeHoliday`

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | |
| `name` | `str` | |
| `all_day_enabled` | `bool` | |
| `start_date` | `date` | YYYY-MM-DD format |
| `end_date` | `date` | |
| `start_time` | `time` | Required if `all_day_enabled` is false |
| `end_time` | `time` | Required if `all_day_enabled` is false |
| `recurrence` | `OperatingModeRecurrence` | |

#### `OperatingModeRecurrence`

| Field | Type |
|-------|------|
| `recur_yearly_by_date` | `OperatingModeRecurYearlyByDate` |
| `recur_yearly_by_day` | `OperatingModeRecurYearlyByDay` |

Two recurrence patterns: by date (day of month + month) or by day (day + week + month, e.g., "first Monday of September").

#### `OperatingMode`

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | |
| `name` | `str` | |
| `type` | `OperatingModeSchedule` | |
| `level` | `ScheduleLevel` | Org or location |
| `location` | `IdAndName` | Required if level is LOCATION |
| `same_hours_daily` | `SameHoursDaily` | Present if type is `SAME_HOURS_DAILY` |
| `different_hours_daily` | `DifferentHoursDaily` | Present if type is `DIFFERENT_HOURS_DAILY` |
| `holidays` | `list[OperatingModeHoliday]` | Present if type is `HOLIDAY` |
| `call_forwarding` | `CallForwardingCommon` | Forwarding settings for this mode |

### 6.3 API Methods

```python
class OperatingModesApi:

    # --- CRUD ---
    def list(self, limit_to_location_id: str = None, name: str = None,
             limit_to_org_level_enabled: bool = None, order: str = None,
             org_id: str = None, **params) -> Generator[OperatingMode]

    def details(self, mode_id: str, org_id: str = None) -> OperatingMode
    def create(self, settings: OperatingMode, org_id: str = None) -> str  # returns mode ID
    def update(self, mode_id: str, settings: OperatingMode, org_id: str = None)
    def delete(self, mode_id: str, org_id: str = None)

    # --- Holiday management ---
    def holiday_details(self, mode_id: str, holiday_id: str, org_id: str = None) -> OperatingModeHoliday
    def holiday_create(self, mode_id: str, settings: OperatingModeHoliday, org_id: str = None) -> str  # returns holiday ID
    # Verified via CLI implementation 2026-03-17: holiday_create requires start_date and end_date (not just date), plus all_day_enabled. Only HOLIDAY type operating modes accept holiday events.
    def holiday_update(self, mode_id: str, holiday_id: str, settings: OperatingModeHoliday, org_id: str = None)
    def holiday_delete(self, mode_id: str, holiday_id: str = None, org_id: str = None)

    # --- Availability queries ---
    def available_operating_modes(self, location_id: str, org_id: str = None) -> list[IdAndName]
    def call_forward_available_phone_numbers(self, location_id: str, phone_number: list[str] = None,
                                             owner_name: str = None, extension: str = None,
                                             org_id: str = None, **params) -> Generator[AvailableNumber]
```

### 6.4 Raw HTTP — Operating Modes

```python
BASE = "https://webexapis.com/v1"

# --- Operating Mode CRUD ---

# GET — List operating modes (paginated)
result = api.session.rest_get(f"{BASE}/telephony/config/operatingModes",
    params={"max": 1000, "limitToLocationId": loc_id})
# Response: {"operatingModes": [{"id": "...", "name": "...", "type": "SAME_HOURS_DAILY",
#            "level": "ORGANIZATION"}]}
# Optional params: name, limitToOrgLevelEnabled, order (asc/desc by name)

# GET — Get operating mode details
result = api.session.rest_get(f"{BASE}/telephony/config/operatingModes/{mode_id}")
# Response includes full schedule data (sameHoursDaily, differentHoursDaily, or holidays)
# plus callForwarding settings

# POST — Create an operating mode
body = {
    "name": "Business Hours",
    "type": "SAME_HOURS_DAILY",
    "level": "ORGANIZATION",
    "sameHoursDaily": {
        "mondayToFriday": {
            "enabled": True,
            "allDayEnabled": False,
            "startTime": "09:00",
            "endTime": "17:00"
        },
        "saturdayToSunday": {
            "enabled": False
        }
    }
}
result = api.session.rest_post(f"{BASE}/telephony/config/operatingModes/", json=body)
# Returns: {"id": "<mode_id>"}

# For location-scoped:
body = {
    "name": "Branch Office Hours",
    "type": "DIFFERENT_HOURS_DAILY",
    "level": "LOCATION",
    "locationId": "<loc_id>",
    "differentHoursDaily": {
        "monday": {"enabled": True, "startTime": "08:00", "endTime": "18:00"},
        "tuesday": {"enabled": True, "startTime": "08:00", "endTime": "18:00"},
        "wednesday": {"enabled": True, "startTime": "08:00", "endTime": "18:00"},
        "thursday": {"enabled": True, "startTime": "08:00", "endTime": "18:00"},
        "friday": {"enabled": True, "startTime": "08:00", "endTime": "16:00"},
        "saturday": {"enabled": False},
        "sunday": {"enabled": False}
    }
}
result = api.session.rest_post(f"{BASE}/telephony/config/operatingModes/", json=body)

# PUT — Update an operating mode
body = {"name": "Updated Business Hours"}
api.session.rest_put(f"{BASE}/telephony/config/operatingModes/{mode_id}", json=body)

# DELETE — Delete an operating mode
api.session.rest_delete(f"{BASE}/telephony/config/operatingModes/{mode_id}")

# --- Holiday management (only for HOLIDAY type operating modes) ---

# GET — Get holiday details
result = api.session.rest_get(
    f"{BASE}/telephony/config/operatingModes/{mode_id}/holidays/{holiday_id}")

# POST — Create a holiday
body = {
    "name": "Independence Day",
    "allDayEnabled": True,
    "startDate": "2026-07-04",
    "endDate": "2026-07-04"
}
result = api.session.rest_post(
    f"{BASE}/telephony/config/operatingModes/{mode_id}/holidays", json=body)
# Returns: {"id": "<holiday_id>"}

# POST — Create holiday with yearly recurrence
body = {
    "name": "Christmas",
    "allDayEnabled": True,
    "startDate": "2026-12-25",
    "endDate": "2026-12-25",
    "recurrence": {
        "recurYearlyByDate": {"dayOfMonth": 25, "month": "DECEMBER"}
    }
}
result = api.session.rest_post(
    f"{BASE}/telephony/config/operatingModes/{mode_id}/holidays", json=body)

# PUT — Update a holiday
body = {"name": "Christmas Day", "allDayEnabled": True,
        "startDate": "2026-12-25", "endDate": "2026-12-25"}
api.session.rest_put(
    f"{BASE}/telephony/config/operatingModes/{mode_id}/holidays/{holiday_id}", json=body)

# DELETE — Delete a holiday
api.session.rest_delete(
    f"{BASE}/telephony/config/operatingModes/{mode_id}/holidays/{holiday_id}")

# --- Availability queries ---

# GET — Available operating modes for a location (up to 200: location + org combined)
result = api.session.rest_get(
    f"{BASE}/telephony/config/locations/{loc_id}/operatingModes/availableOperatingModes")
# Response: {"availableOperatingModes": [{"id": "...", "name": "..."}]}

# GET — Available phone numbers for call forwarding in operating modes
result = api.session.rest_get(
    f"{BASE}/telephony/config/locations/{loc_id}/operatingModes/callForwarding/availableNumbers",
    params={"max": 1000})
# Response: {"availableNumbers": [{"phoneNumber": "+1...", "ownerName": "...", "extension": "..."}]}
```

**Gotcha:** Create requires `level` set to `ORGANIZATION` or `LOCATION`. For `LOCATION`, you must also include `locationId` in the body. The `type` field must use the enum value directly (e.g., `SAME_HOURS_DAILY`, `DIFFERENT_HOURS_DAILY`, `HOLIDAY`).

**Gotcha:** For `SAME_HOURS_DAILY` type, you must provide actual schedule data in `sameHoursDaily` -- the API rejects a create with no schedule data.

**Gotcha:** Holidays can only be added to operating modes with `type: HOLIDAY`. The `holiday_create` endpoint requires `startDate`, `endDate`, and `allDayEnabled` at minimum.

### 6.5 CLI Examples

```bash
# List all operating modes
wxcli operating-modes list

# List operating modes for a specific location
wxcli operating-modes list --limit-to-location-id <location_id>

# List org-level operating modes only
wxcli operating-modes list --limit-to-org-level-enabled true

# Search operating modes by name
wxcli operating-modes list --name "Business Hours"

# Get details for an operating mode
wxcli operating-modes show <mode_id>

# Create an operating mode (requires --json-body for schedule data)
wxcli operating-modes create --name "Business Hours" --json-body '{
  "type": "SAME_HOURS_DAILY",
  "level": "ORGANIZATION",
  "sameHoursDaily": {
    "mondayToFriday": {"enabled": true, "startTime": "09:00", "endTime": "17:00"},
    "saturdayToSunday": {"enabled": false}
  }
}'

# Create a location-scoped operating mode
wxcli operating-modes create --name "Branch Hours" \
  --location-id <location_id> --json-body '{
  "type": "DIFFERENT_HOURS_DAILY",
  "level": "LOCATION",
  "differentHoursDaily": {
    "monday": {"enabled": true, "startTime": "08:00", "endTime": "18:00"},
    "tuesday": {"enabled": true, "startTime": "08:00", "endTime": "18:00"},
    "wednesday": {"enabled": true, "startTime": "08:00", "endTime": "18:00"},
    "thursday": {"enabled": true, "startTime": "08:00", "endTime": "18:00"},
    "friday": {"enabled": true, "startTime": "08:00", "endTime": "16:00"},
    "saturday": {"enabled": false},
    "sunday": {"enabled": false}
  }
}'

# Update an operating mode
wxcli operating-modes update <mode_id> --json-body '{"name": "Updated Business Hours"}'

# Delete an operating mode
wxcli operating-modes delete <mode_id>

# Create a holiday on a HOLIDAY-type operating mode
wxcli operating-modes create-holidays <mode_id> \
  --name "Independence Day" --all-day-enabled \
  --start-date "2026-07-04" --end-date "2026-07-04"

# Get holiday details
wxcli operating-modes show-holidays <mode_id> <holiday_id>

# Delete a holiday
wxcli operating-modes delete-holidays <mode_id> <holiday_id>

# List available operating modes for a location
wxcli operating-modes list-available-operating-modes <location_id>

# List available phone numbers for call forwarding in operating modes
wxcli operating-modes list-available-numbers <location_id>
```

### 6.6 Key Behaviors

- **Max 100 operating modes per location** and 100 per org. `available_operating_modes()` returns up to 200 (location + org combined).
- **Max 150 holidays per operating mode.**
- The `create()` method requires at least `name`, `type`, and `level` on the `OperatingMode` object. If `level` is LOCATION, `location.id` must be set.
- On `create()`, the SDK internally converts `location` to `locationId` and strips `id` from holidays. On `update()`, it additionally strips `type` and `level` (immutable after creation).
- `call_forward_available_phone_numbers()` lists PSTN numbers available as forwarding destinations for operating modes at a given location.
- The `list()` result is sorted ascending by operating mode name.

---

## 7. Hot Desking Sign-in via Voice Portal

**SDK module:** `wxc_sdk.telephony.hotdesking_voiceportal`
**API class:** `HotDeskingSigninViaVoicePortalApi` (base: `telephony/config`)

Hot desking allows users to sign in to a shared phone via the voice portal and make calls using their own phone number.

### 7.1 Scopes

| Operation | Scope |
|-----------|-------|
| Read | `spark-admin:telephony_config_read` |
| Write | `spark-admin:telephony_config_write` |

### 7.2 Data Models

#### `HotDeskingVoicePortalSetting`

| Field | Type | Notes |
|-------|------|-------|
| `enabled` | `bool` | JSON alias: `voicePortalHotDeskSignInEnabled` |

Single boolean -- enables or disables hot desking sign-in via voice portal.

### 7.3 API Methods

```python
class HotDeskingSigninViaVoicePortalApi:

    # --- Location level ---
    def location_get(self, location_id: str, org_id: str = None) -> HotDeskingVoicePortalSetting
    def location_update(self, location_id: str, setting: HotDeskingVoicePortalSetting, org_id: str = None)

    # --- User level ---
    def user_get(self, person_id: str, org_id: str = None) -> HotDeskingVoicePortalSetting
    def user_update(self, person_id: str, setting: HotDeskingVoicePortalSetting, org_id: str = None)
```

### 7.4 CLI: `hot-desking-portal`

| Command | Description |
|---------|-------------|
| `hot-desking-portal show <location_id>` | Get voice portal hot desking settings for a location |
| `hot-desking-portal update <location_id>` | Update voice portal hot desking settings for a location |
| `hot-desking-portal show-guest <person_id>` | Get voice portal hot desking settings for a user |
| `hot-desking-portal update-guest <person_id>` | Update voice portal hot desking settings for a user |

```bash
# Get hot desking voice portal settings for a location
wxcli hot-desking-portal show <location_id>

# Enable hot desking sign-in via voice portal for a location
wxcli hot-desking-portal update <location_id> --voice-portal-hot-desk-sign-in-enabled

# Disable hot desking sign-in via voice portal for a location
wxcli hot-desking-portal update <location_id> --no-voice-portal-hot-desk-sign-in-enabled

# Get hot desking guest settings for a specific user
wxcli hot-desking-portal show-guest <person_id>

# Enable a user as a hot desking guest
wxcli hot-desking-portal update-guest <person_id> --voice-portal-hot-desk-sign-in-enabled

# Disable a user as a hot desking guest
wxcli hot-desking-portal update-guest <person_id> --no-voice-portal-hot-desk-sign-in-enabled
```

### 7.5 Key Behaviors

- Location endpoint: `locations/{location_id}/features/hotDesking`
- User endpoint: `people/{person_id}/features/hotDesking/guest`
- This is a simple enable/disable toggle at both location and per-user levels.
- The user-level setting controls whether a specific user can act as a hot desking guest.

---

## 8. Forwarding (Shared Patterns)

**SDK module:** `wxc_sdk.telephony.forwarding`
**API class:** `ForwardingApi` (base: dynamic per feature)

Shared forwarding settings and selective rules used by **Call Queues**, **Hunt Groups**, and **Auto Attendants**. The `ForwardingApi` is instantiated with a `FeatureSelector` that determines which feature type it operates on.

### 8.1 Feature Selectors

```python
class FeatureSelector(str, Enum):
    queues = 'queues'
    huntgroups = 'huntGroups'
    auto_attendants = 'autoAttendants'
```

The API endpoint is constructed as:
```
telephony/config/locations/{location_id}/{feature}/​{feature_id}/callForwarding[/{path}]
```

### 8.2 Data Models

#### `CallForwarding`
Top-level forwarding configuration for a feature.

| Field | Type | Notes |
|-------|------|-------|
| `always` | `ForwardingSetting` | Forward all calls |
| `selective` | `ForwardingSetting` | Forward based on rules |
| `rules` | `list[ForwardingRule]` | Selective forwarding rules |
| `operating_modes` | `ForwardOperatingModes` | Mode-based forwarding |

#### `ForwardingSetting`

| Field | Type | Notes |
|-------|------|-------|
| `enabled` | `bool` | |
| `destination` | `str` | Forwarding destination number |
| `ring_reminder_enabled` | `bool` | Brief tone on forwarded call |
| `destination_voice_mail_enabled` | `bool` | Forward to destination's voicemail |
| `send_to_voicemail_enabled` | `bool` | Send to voicemail |

#### `ForwardingRule`
Summary of a selective forwarding rule (returned in the rules list).

| Field | Type |
|-------|------|
| `id` | `str` |
| `name` | `str` |
| `calls_from` | `str` |
| `forward_to` | `str` |
| `calls_to` | `str` |
| `enabled` | `bool` |

#### `ForwardingRuleDetails`
Full details of a selective forwarding rule.

| Field | Type | Notes |
|-------|------|-------|
| `name` | `str` | |
| `id` | `str` | |
| `enabled` | `bool` | |
| `holiday_schedule` | `str` | Schedule name for when rule applies |
| `business_schedule` | `str` | Schedule name for when rule applies |
| `forward_to` | `ForwardTo` | |
| `calls_to` | `ForwardCallsTo` | List of numbers/extensions |
| `calls_from` | `CallsFrom` | |

#### `ForwardTo`

| Field | Type | Default |
|-------|------|---------|
| `selection` | `ForwardToSelection` | `FORWARD_TO_DEFAULT_NUMBER` |
| `phone_number` | `str` | |

#### `ForwardToSelection` (Enum)

| Value | Meaning |
|-------|---------|
| `FORWARD_TO_DEFAULT_NUMBER` | Use default forwarding number |
| `FORWARD_TO_SPECIFIED_NUMBER` | Use number in `phone_number` field |
| `DO_NOT_FORWARD` | Do not forward |

#### `ForwardFromSelection` (Enum)

| Value | Meaning |
|-------|---------|
| `ANY` | Match any caller |
| `CUSTOM` | Match specific callers only |

#### `CallsFrom`

| Field | Type | Default |
|-------|------|---------|
| `selection` | `ForwardFromSelection` | `ANY` |
| `custom_numbers` | `CustomNumbers` | |

#### `CustomNumbers`

| Field | Type | Default |
|-------|------|---------|
| `private_number_enabled` | `bool` | `False` |
| `unavailable_number_enabled` | `bool` | `False` |
| `numbers` | `list[str]` | |

#### `ForwardOperatingModes`

| Field | Type | Notes |
|-------|------|-------|
| `enabled` | `bool` | Operating modes enabled |
| `current_operating_mode_id` | `str` | Currently active mode |
| `exception_type` | `ExceptionType` | |
| `modes` | `list[ModeForward]` | Configured modes |

#### `ModeForward`

| Field | Type |
|-------|------|
| `normal_operation_enabled` | `bool` |
| `id` | `str` |
| `name` | `str` |
| `type` | `OperatingModeSchedule` |
| `level` | `ScheduleLevel` |
| `forward_to` | `ModeForwardTo` |

#### `ModeForwardTo`

| Field | Type | Notes |
|-------|------|-------|
| `selection` | `ForwardToSelection` | |
| `destination` | `str` | Required when selection is `FORWARD_TO_SPECIFIED_NUMBER` |
| `destination_voicemail_enabled` | `bool` | |
| `default_destination` | `str` | Operating mode's own destination |
| `default_destination_voicemail_enabled` | `bool` | |
| `default_forward_to_selection` | `ModeDefaultForwardToSelection` | |

### 8.3 API Methods

```python
class ForwardingApi:

    def __init__(self, session: RestSession, feature_selector: FeatureSelector)

    # --- Get/Update forwarding settings ---
    def settings(self, location_id: str, feature_id: str, org_id: str = None) -> CallForwarding
    def update(self, location_id: str, feature_id: str,
               forwarding: CallForwarding, org_id: str = None)

    # --- Selective forwarding rules ---
    def create_call_forwarding_rule(self, location_id: str, feature_id: str,
                                    forwarding_rule: ForwardingRuleDetails,
                                    org_id: str = None) -> str  # returns rule ID

    def call_forwarding_rule(self, location_id: str, feature_id: str,
                             rule_id: str, org_id: str = None) -> ForwardingRuleDetails

    def update_call_forwarding_rule(self, location_id: str, feature_id: str,
                                    rule_id: str, forwarding_rule: ForwardingRuleDetails,
                                    org_id: str = None) -> str  # returns new rule ID

    def delete_call_forwarding_rule(self, location_id: str, feature_id: str,
                                    rule_id: str, org_id: str = None)

    # --- Operating mode switch ---
    def switch_mode_for_call_forwarding(self, location_id: str, feature_id: str,
                                        org_id: str = None)
```

### 8.4 CLI Examples

Forwarding commands are accessed through the feature-specific command groups (`auto-attendant`, `call-queue`, `hunt-group`), not a standalone forwarding group. The commands follow the same pattern across all three features:

```bash
# --- Call Queue forwarding ---

# Get call forwarding settings for a call queue
wxcli call-queue show-call-forwarding <location_id> <queue_id>

# Update call forwarding settings (use --json-body for complex forwarding rules)
wxcli call-queue update-call-forwarding <location_id> <queue_id> --json-body '{
  "callForwarding": {
    "always": {"enabled": true, "destination": "+14155551234"}
  }
}'

# Create a selective call forwarding rule
wxcli call-queue create-selective-rules <location_id> <queue_id> \
  --name "After Hours Forward" --enabled \
  --business-schedule "After Hours Schedule"

# Get a selective call forwarding rule
wxcli call-queue show-selective-rules <location_id> <queue_id> <rule_id>

# Delete a selective call forwarding rule
wxcli call-queue delete-selective-rules <location_id> <queue_id> <rule_id>

# Get available phone numbers for call forwarding
wxcli call-queue list-available-numbers-call-forwarding <location_id> <queue_id>

# Switch operating mode back to normal operations
wxcli call-queue switch-mode-for <location_id> <queue_id>

# --- Auto Attendant forwarding (same pattern) ---
wxcli auto-attendant show-call-forwarding <location_id> <aa_id>
wxcli auto-attendant create-selective-rules <location_id> <aa_id> --name "Holiday Forward"
wxcli auto-attendant switch-mode-for <location_id> <aa_id>

# --- Hunt Group forwarding (same pattern) ---
wxcli hunt-group show-call-forwarding <location_id> <hg_id>
wxcli hunt-group create-selective-rules <location_id> <hg_id> --name "Overflow Forward"
wxcli hunt-group switch-mode-for <location_id> <hg_id>
```

### 8.5 Key Behaviors

- **Rule ID changes on rename**: The Call Forwarding Rule ID will change when the rule name is modified via `update_call_forwarding_rule()`. The new ID is returned.
- **NANP number normalization**: The SDK automatically handles +1 prefix transformations. Numbers returned from the platform without a `+` prefix get `+1-` prepended. When serializing for API calls, `+1-` is stripped back off. Non-NANP numbers (those starting with `+`) are left as-is.
- **`switch_mode_for_call_forwarding()`** switches the feature's current operating mode back to normal operations.
- The `update()` method serializes with `exclude_unset=True`, so only fields you explicitly set are sent to the API. It also strips read-only fields (`calls_from`, `forward_to`, `calls_to`, `name`) from rule summaries in the rules list.
- **`CallForwarding.default()`** provides a safe starting point: always-forward disabled, selective disabled, empty rules list.
- Three forwarding modes are available simultaneously: always forward, selective rules, and operating mode-based. The API returns all three as part of the `CallForwarding` object.

---

## Cross-Reference: Scope Summary

| API | Read Scope | Write Scope |
|-----|-----------|-------------|
| Call Recording | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |
| Caller Reputation | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |
| Conference Controls | `spark:calls_read` | `spark:calls_write` |
| Supervisors | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |
| Guest Calling | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |
| Operating Modes | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |
| Hot Desking Voice Portal | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |
| Forwarding | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |

Note that Conference Controls uses **user-level** scopes (`spark:calls_*`), not admin scopes, because it is a runtime call-control API.

---

## Gotchas (Cross-Cutting)

- **Conference Controls require user-level OAuth.** Unlike all other APIs in this doc, Conference Controls uses `spark:calls_read` / `spark:calls_write` scopes (not admin scopes). Admin or service-app tokens will fail. This matches the `call-controls` known issue documented in CLAUDE.md.
- **Caller Reputation uses `organizationId`, not `orgId`.** Most telephony APIs use `orgId` as the query parameter, but the caller reputation endpoints use `organizationId`. The wxcli maps this as `--organization-id`.
- **Call Recording vendor changes are async.** `set_org_vendor()` and `set_location_vendor()` may return a job ID (HTTP 200) instead of completing immediately (HTTP 204). Always check job status via `wxcli call-recording show-call-recording <job_id>` after vendor changes.
- **Operating mode type and level are immutable after creation.** You cannot change `type` (SAME_HOURS_DAILY, DIFFERENT_HOURS_DAILY, HOLIDAY) or `level` (ORGANIZATION, LOCATION) after creating an operating mode. Delete and recreate if you need to change these.
- **Forwarding rule IDs change on rename.** When you rename a selective forwarding rule via `update_call_forwarding_rule()`, the rule ID changes. The new ID is returned from the update call. Store it if you need to reference the rule again.
- **Score thresholds are strings.** The caller reputation `callBlockScoreThreshold` and `callAllowScoreThreshold` fields are string-typed, not integers. Pass them as quoted values in both CLI and raw HTTP.
- **`delete_bulk` supervisors has a nuke option.** Setting `delete_all: true` on `delete_bulk()` ignores the provided ID list and removes ALL supervisors in the org. Double-check before using.
- **Hot desking has two levels.** The location setting enables the feature globally for the location; the user-level setting controls whether a specific user can act as a hot desking guest. Both must be enabled for a user to hot-desk at that location.
- **TimePeriod AXL field constraints.** The `monthOfYear` field uses 3-letter abbreviations only (`Dec`, `Jan`, `Feb`, etc., not full names like `December`). The `startTime`/`endTime` fields only accept on-the-hour values per the `TypeTimeOfDay` enum — values like `23:59` or `17:30` are rejected. For date-specific (holiday) time periods, use `monthOfYear` + `dayOfMonth` with valid time range (e.g., `08:00`–`17:00`).

---

## See Also

- **[Person Call Settings — Media](person-call-settings-media.md)** — Per-user call recording settings (record mode, notifications, access permissions) that work within the vendor/compliance framework configured here
