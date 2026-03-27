<!-- Verified via CLI Batches 1-4, 2026-03-19 through 2026-03-21 -->
# Location Call Settings — Core Settings & Voicemail

## Sources
- wxc_sdk v1.30.0
- OpenAPI spec: specs/webex-cloud-calling.json
- developer.webex.com Location Call Settings APIs

Reference document covering the SDK APIs for location-level call settings, voicemail policies (location and org), voicemail rules, voice messaging, and voice portal configuration.

**SDK source module:** `wxc_sdk.telephony.location` (and related telephony modules)

---

## Table of Contents

1. [Location-Level Call Settings](#1-location-level-call-settings)
   - [TelephonyLocationApi — Main API Class](#telephonylocationapi--main-api-class)
   - [Data Models](#location-data-models)
   - [Enable / List / Get / Update Locations](#enable--list--get--update-locations)
   - [Caller ID](#caller-id)
   - [Internal Dialing](#internal-dialing)
   - [Call Intercept](#call-intercept)
   - [Music on Hold](#music-on-hold)
   - [Location Numbers](#location-numbers)
   - [Emergency Callback Number (ECBN)](#emergency-callback-number-ecbn)
   - [Announcement Language](#announcement-language)
   - [Call Captions](#call-captions)
   - [Device Settings](#device-settings)
   - [Safe Delete Check](#safe-delete-check)
   - [Extension Validation & Password Generation](#extension-validation--password-generation)
2. [Voicemail Policies](#2-voicemail-policies)
   - [Location Voicemail Settings](#location-voicemail-settings)
   - [Organisation Voicemail Settings](#organisation-voicemail-settings)
3. [Voicemail Rules (Org-Level Passcode Policy)](#3-voicemail-rules-org-level-passcode-policy)
4. [Voice Messaging (User-Level)](#4-voice-messaging-user-level)
5. [Voice Portal](#5-voice-portal)

---

## 1. Location-Level Call Settings

### TelephonyLocationApi -- Main API Class

The main entry point is `TelephonyLocationApi`, accessible at `api.telephony.location`. It aggregates several child APIs as attributes:

```
base = 'telephony/config/locations'
```

| Attribute | Type | Purpose |
|-----------|------|---------|
| `emergency_services` | `LocationEmergencyServicesApi` | Emergency services config |
| `intercept` | `LocationInterceptApi` | Call intercept settings |
| `internal_dialing` | `InternalDialingApi` | Internal dialing / unknown extension routing |
| `moh` | `LocationMoHApi` | Music on hold settings |
| `number` | `LocationNumbersApi` | Phone number management (add/remove/activate) |
| `permissions_out` | `OutgoingPermissionsApi` | Outgoing call permissions |
| `voicemail` | `LocationVoicemailSettingsApi` | Location VM settings (transcription toggle) |
| `receptionist_contacts_directory` | `ReceptionistContactsDirectoryApi` | Receptionist contact directories |

---

### Location Data Models

#### `TelephonyLocation`

The core model representing a Webex Calling-enabled location.

| Field | Type | Description |
|-------|------|-------------|
| `location_id` | `str` | Unique identifier (aliased from `id`) |
| `name` | `str` | Location name |
| `announcement_language` | `str` | Phone announcement language |
| `calling_line_id` | `CallingLineId` | Caller ID name + phone number |
| `connection` | `PSTNConnection` | PSTN connection (TRUNK or ROUTE_GROUP) |
| `subscription_id` | `str` | PSTN subscription ID |
| `external_caller_id_name` | `str` | External caller ID name (Unicode) |
| `user_limit` | `int` | Max people at location (read-only) |
| `p_access_network_info` | `str` | Emergency SIP P-Access-Network-Info header |
| `outside_dial_digit` | `str` | Digit to dial for outside line (e.g. `'9'`) |
| `enforce_outside_dial_digit` | `bool` | Enforce outside dial digit for PSTN calls |
| `routing_prefix` | `str` | Prefix for inter-location calls with same extension |
| `default_domain` | `str` | IP/hostname/domain (read-only) |
| `charge_number` | `str` | P-Charge-Info header number for PSTN calls |
| `use_charge_number_for_pcharge_info` | `bool` | Enable charge number in SIP INVITE |
| `e911_setup_required` | `bool` | Whether E911 setup is needed (read-only) |

**Read-only fields** (excluded from updates): `location_id`, `name`, `subscription_id`, `user_limit`, `default_domain`, `e911_setup_required`.

#### `CallingLineId`

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Group calling line ID name (defaults to org name). When updating, include phone_number too. |
| `phone_number` | `str` | Main number in E.164 format |

#### `PSTNConnection`

| Field | Type | Description |
|-------|------|-------------|
| `type` | `RouteType` | `TRUNK` or `ROUTE_GROUP` |
| `id` | `str` | Unique identifier of the route |

---

### Enable / List / Get / Update Locations

#### `enable_for_calling`

Enable a location for Webex Calling. Adds calling support to a location created via the locations API.

```python
def enable_for_calling(
    self,
    location: Location,
    org_id: str = None
) -> str
```

**Returns:** The new location ID.

**Scope:** `spark-admin:telephony_config_write`

---

#### `list`

List all Webex Calling locations with telephony details.

```python
def list(
    self,
    name: str = None,
    order: str = None,
    org_id: str = None
) -> Generator[TelephonyLocation, None, None]
```

| Parameter | Description |
|-----------|-------------|
| `name` | Filter — locations whose name contains this string |
| `order` | Sort by name: `'asc'` or `'desc'` |

**Scope:** `spark-admin:telephony_config_read`

---

#### `details`

Get Webex Calling details for a single location.

```python
def details(
    self,
    location_id: str,
    org_id: str = None
) -> TelephonyLocation
```

**Scope:** `spark-admin:telephony_config_read`

---

#### `update`

Update Webex Calling details for a location. Only non-read-only fields in `TelephonyLocation` are sent.

```python
def update(
    self,
    location_id: str,
    settings: TelephonyLocation,
    org_id: str = None
) -> Optional[str]
```

**Returns:** `batchJobId` if an async update job is created, otherwise `None`.

**Example:**
```python
api.telephony.location.update(
    location_id=location_id,
    settings=TelephonyLocation(
        calling_line_id=CallingLineId(phone_number=tn),
        routing_prefix=routing_prefix,
        outside_dial_digit='9'
    )
)
```

**Scope:** `spark-admin:telephony_config_write`

**Note:** Modifying `connection` is only supported for local PSTN types `TRUNK` and `ROUTE_GROUP`.

#### CLI Examples

```bash
# List all locations with Webex Calling details
wxcli location-settings list-1

# List locations filtered by name
wxcli location-settings list-1 --name "San Jose"

# Get calling details for a specific location
wxcli location-settings show Y2lzY29zcGFyazovL...

# Enable a location for Webex Calling
wxcli location-settings create \
  --id Y2lzY29zcGFyazovL... \
  --name "San Jose HQ" \
  --time-zone "America/Los_Angeles" \
  --preferred-language "en_us" \
  --announcement-language "en_us"

# Update location calling details (outside dial digit, routing prefix)
wxcli location-settings update Y2lzY29zcGFyazovL... \
  --outside-dial-digit "9" \
  --enforce-outside-dial-digit \
  --routing-prefix "8001" \
  --external-caller-id-name "Acme Corp"

# Update location with JSON body for complex settings
wxcli location-settings update Y2lzY29zcGFyazovL... \
  --json-body '{"announcementLanguage": "en_us", "chargeNumber": "+14085551234"}'
```

---

### Caller ID

Caller ID is configured through the `CallingLineId` object embedded in `TelephonyLocation`. There is also a dedicated API to list phone numbers available for external caller ID.

#### `phone_numbers_available_for_external_caller_id`

List phone numbers available for external caller ID usage by a Webex Calling entity within a location.

```python
def phone_numbers_available_for_external_caller_id(
    self,
    location_id: str,
    phone_number: List[str] = None,
    owner_name: str = None,
    person_id: str = None,
    org_id: str = None,
    **params
) -> Generator[AvailableNumber, None, None]
```

Numbers from the specified location and cross-location numbers (same country, PSTN provider, zone) are returned. When `person_id` is specified for a Cisco PSTN location user with a mobile primary DN and no billing plan, only that mobile number is returned.

**Scope:** `spark-admin:telephony_config_read`

---

### Internal Dialing

**API path:** `api.telephony.location.internal_dialing`

Controls routing of calls to unknown extensions (2-6 digits) to a premises PBX via a trunk or route group.

#### `InternalDialing` Model

| Field | Type | Description |
|-------|------|-------------|
| `enable_unknown_extension_route_policy` | `bool` | Route unknown extensions to premises |
| `unknown_extension_route_identity` | `RouteIdentity` | Destination trunk/route group for unknown extensions |

#### `read`

```python
def read(
    self,
    location_id: str,
    org_id: str = None
) -> InternalDialing
```

**Scope:** `spark-admin:telephony_config_read`

#### `update`

```python
def update(
    self,
    location_id: str,
    update: InternalDialing,
    org_id: str = None
)
```

**Scope:** `spark-admin:telephony_config_write`

#### CLI Examples

```bash
# Read internal dialing configuration for a location
wxcli location-call-handling show Y2lzY29zcGFyazovL...

# Enable routing of unknown extensions to a trunk
wxcli location-call-handling update Y2lzY29zcGFyazovL... \
  --enable-unknown-extension-route-policy \
  --json-body '{"unknownExtensionRouteIdentity": {"id": "TRUNK_ID", "type": "TRUNK"}}'

# Disable unknown extension routing
wxcli location-call-handling update Y2lzY29zcGFyazovL... \
  --no-enable-unknown-extension-route-policy
```

---

### Call Intercept

**API path:** `api.telephony.location.intercept`

Intercept incoming or outgoing calls for all persons at a location. Intercepted calls are routed to a designated number or to voicemail.

Uses the shared `InterceptSetting` model from `wxc_sdk.person_settings.call_intercept`.

#### `read`

```python
def read(
    self,
    location_id: str,
    org_id: str = None
) -> InterceptSetting
```

**Scope:** `spark-admin:telephony_config_read`

#### `configure`

```python
def configure(
    self,
    location_id: str,
    settings: InterceptSetting,
    org_id: str = None
)
```

**Scope:** `spark-admin:telephony_config_write`

#### `call_intercept_available_phone_numbers`

(On `TelephonyLocationApi` directly.) List service and standard numbers available to be assigned as the location's call intercept number.

```python
def call_intercept_available_phone_numbers(
    self,
    location_id: str,
    phone_number: List[str] = None,
    owner_name: str = None,
    org_id: str = None,
    **params
) -> Generator[AvailableNumber, None, None]
```

**Scope:** `spark-admin:telephony_config_read`

#### CLI Examples

```bash
# Read call intercept settings for a location
wxcli location-call-handling show-intercept Y2lzY29zcGFyazovL...

# Enable call intercept for all users at a location
wxcli location-call-handling update-intercept Y2lzY29zcGFyazovL... --enabled

# Enable intercept with voicemail routing via JSON body
wxcli location-call-handling update-intercept Y2lzY29zcGFyazovL... \
  --json-body '{"enabled": true, "incoming": {"type": "INTERCEPT_ALL", "voicemailEnabled": true}}'

# Disable call intercept
wxcli location-call-handling update-intercept Y2lzY29zcGFyazovL... --no-enabled

# List available phone numbers for call intercept
wxcli location-settings list-available-numbers-call-intercept Y2lzY29zcGFyazovL...
```

---

### Music on Hold

**API path:** `api.telephony.location.moh`

Controls music played when a call is on hold or parked at the location.

#### `LocationMoHGreetingType` Enum

| Value | Description |
|-------|-------------|
| `SYSTEM` | Default system music |
| `CUSTOM` | Custom uploaded audio file or playlist |

#### `LocationMoHSetting` Model

| Field | Type | Description |
|-------|------|-------------|
| `call_hold_enabled` | `bool` | Play music on hold |
| `call_park_enabled` | `bool` | Play music on park |
| `greeting` | `LocationMoHGreetingType` | `SYSTEM` or `CUSTOM` |
| `audio_file` | `AnnAudioFile` | Audio file details (when `CUSTOM`) |
| `playlist` | `IdAndName` | Playlist details (when `CUSTOM`) |

#### `read`

```python
def read(
    self,
    location_id: str,
    org_id: str = None
) -> LocationMoHSetting
```

**Scope:** `spark-admin:telephony_config_read`

#### `update`

```python
def update(
    self,
    location_id: str,
    settings: LocationMoHSetting,
    org_id: str = None
)
```

**Scope:** `spark-admin:telephony_config_write`

#### CLI Examples

```bash
# Read music on hold settings for a location
wxcli location-settings show-music-on-hold Y2lzY29zcGFyazovL...

# Enable music on hold with system greeting
wxcli location-settings update-music-on-hold Y2lzY29zcGFyazovL... \
  --moh-enabled --greeting DEFAULT

# Switch to custom greeting
wxcli location-settings update-music-on-hold Y2lzY29zcGFyazovL... \
  --moh-enabled --greeting CUSTOM
```

---

### Location Numbers

**API path:** `api.telephony.location.number`

Manage phone numbers assigned to a location (add, remove, activate, deactivate).

#### Key Models

| Model | Description |
|-------|-------------|
| `TelephoneNumberType` | Enum: `TOLLFREE`, `DID`, `MOBILE` |
| `NumberUsageType` | Enum: `NONE` (standard), `SERVICE` (high-volume, e.g. Contact Center) |
| `NumbersRequestAction` | Enum: `ACTIVATE`, `DEACTIVATE` |

#### `add`

```python
def add(
    self,
    location_id: str,
    phone_numbers: list[str],
    number_type: TelephoneNumberType = None,
    number_usage_type: NumberUsageType = None,
    state: NumberState = NumberState.inactive,
    subscription_id: str = None,
    carrier_id: str = None,
    org_id: str = None
) -> NumberAddResponse
```

Only supported for non-integrated PSTN (LGW, Non-integrated CPP). Max 20 mobile numbers per request. Numbers already at the location are silently ignored.

#### `remove`

```python
def remove(
    self,
    location_id: str,
    phone_numbers: list[str],
    org_id: str = None
)
```

A location's main number cannot be removed. Only non-integrated PSTN.

#### `activate`

```python
def activate(
    self,
    location_id: str,
    phone_numbers: list[str],
    org_id: str = None
)
```

Does not activate mobile numbers (those activate on user assignment).

#### `manage_number_state`

```python
def manage_number_state(
    self,
    location_id: str,
    phone_numbers: list[str],
    action: NumbersRequestAction = None,
    org_id: str = None
)
```

Unified activate/deactivate. Deactivate limitations: max 500 numbers, must be unassigned, not ECBN, not mobile, non-integrated PSTN only.

---

### Emergency Callback Number (ECBN)

#### `read_ecbn`

```python
def read_ecbn(
    self,
    location_id: str,
    org_id: str = None
) -> LocationECBN
```

**Scope:** `spark-admin:telephony_config_read`

#### `update_ecbn`

```python
def update_ecbn(
    self,
    location_id: str,
    selected: CallBackSelected,
    location_member_id: str = None,
    org_id: str = None
)
```

| `CallBackSelected` Value | Description |
|--------------------------|-------------|
| `LOCATION_NUMBER` | Use the location's TN |
| `LOCATION_MEMBER_NUMBER` | Use a member's number (requires `location_member_id`) |

**Scope:** `spark-admin:telephony_config_write`

#### `ecbn_available_phone_numbers`

```python
def ecbn_available_phone_numbers(
    self,
    location_id: str,
    phone_number: List[str] = None,
    owner_name: str = None,
    org_id: str = None,
    **params
) -> Generator[AvailableNumber, None, None]
```

#### `LocationECBN` Model

| Field | Type | Description |
|-------|------|-------------|
| `location_info` | `LocationECBNLocation` | Location-level ECBN data (phone_number, name, effective_level, effective_value, quality) |
| `location_member_info` | `LocationECBNLocationMember` | Member-level ECBN data (phone_number, first/last name, member_id, member_type, effective_level, effective_value, quality) |
| `selected` | `CallBackSelected` | Which number type is selected |

#### CLI Examples

```bash
# Read ECBN settings for a location
wxcli location-settings show-emergency-callback-number Y2lzY29zcGFyazovL...

# Update ECBN to use the location's main number
wxcli location-settings update-emergency-callback-number Y2lzY29zcGFyazovL... \
  --json-body '{"selected": "LOCATION_NUMBER"}'

# Update ECBN to use a specific member's number
wxcli location-settings update-emergency-callback-number Y2lzY29zcGFyazovL... \
  --location-member-id MEMBER_ID \
  --json-body '{"selected": "LOCATION_MEMBER_NUMBER", "locationMemberId": "MEMBER_ID"}'

# List available ECBN phone numbers
wxcli location-settings list-available-numbers-emergency-callback-number Y2lzY29zcGFyazovL...
```

---

### Announcement Language

#### `change_announcement_language`

Change the announcement language for existing people/workspaces and/or feature configurations at a location. Does **not** change the default language for new entities.

```python
def change_announcement_language(
    self,
    location_id: str,
    language_code: str,
    agent_enabled: bool = None,
    service_enabled: bool = None,
    org_id: str = None
)
```

| Parameter | Description |
|-----------|-------------|
| `language_code` | Language code to set |
| `agent_enabled` | `True` to change language for existing people/workspaces |
| `service_enabled` | `True` to change language for existing feature configurations |

**Scope:** `spark-admin:telephony_config_write`

#### CLI Examples

```bash
# Change announcement language for existing people and features at a location
wxcli location-settings change-announcement-language Y2lzY29zcGFyazovL... \
  --announcement-language-code "en_us" \
  --agent-enabled true \
  --service-enabled true
```

---

### Call Captions

#### `LocationCallCaptions` Model

| Field | Type | Description |
|-------|------|-------------|
| `location_closed_captions_enabled` | `bool` | Location-level closed captions on/off |
| `location_transcripts_enabled` | `bool` | Location-level transcripts on/off |
| `org_closed_captions_enabled` | `bool` | Org-level closed captions (read-only) |
| `org_transcripts_enabled` | `bool` | Org-level transcripts (read-only) |
| `use_org_settings_enabled` | `bool` | `True` = org settings override location settings |

**Note:** Not supported for locations in India. <!-- Verified via wxc_sdk source (location/__init__.py docstring) 2026-03-19 -->

#### `get_call_captions_settings`

```python
def get_call_captions_settings(
    self,
    location_id: str,
    org_id: str = None
) -> LocationCallCaptions
```

#### `update_call_captions_settings`

```python
def update_call_captions_settings(
    self,
    location_id: str,
    settings: LocationCallCaptions,
    org_id: str = None
)
```

Only location-level fields and `use_org_settings_enabled` are sent on update; org-level fields are excluded.

#### CLI Examples

```bash
# Read call captions settings for a location
wxcli location-settings show-call-captions Y2lzY29zcGFyazovL...

# Enable location-level closed captions and transcripts
wxcli location-settings update-call-captions Y2lzY29zcGFyazovL... \
  --location-closed-captions-enabled \
  --location-transcripts-enabled \
  --no-use-org-settings-enabled

# Use org-level settings instead of location overrides
wxcli location-settings update-call-captions Y2lzY29zcGFyazovL... \
  --use-org-settings-enabled
```

---

### Device Settings

#### `device_settings`

Get device override settings for a location.

```python
def device_settings(
    self,
    location_id: str,
    org_id: str = None
) -> DeviceCustomization
```

**Scope:** `spark-admin:telephony_config_read`

---

### Safe Delete Check

#### `safe_delete_check_before_disabling_calling_location`

Check whether a calling location can be safely disabled. Returns blockers and warnings.

```python
def safe_delete_check_before_disabling_calling_location(
    self,
    location_id: str,
    org_id: str = None
) -> SafeDeleteCheckResponse
```

#### `SafeDeleteCheckResponse` Model

| Field | Type | Description |
|-------|------|-------------|
| `location_delete_status` | `LocationDeleteStatus` | `BLOCKED`, `UNBLOCKED`, or `FORCE_REQUIRED` |
| `blocking` | `BlockingDisableCalling` | Hard blockers: last_location, trunks_in_use_count, users_in_use_count, workspaces_in_use_count, virtual_line_in_use_count, numbers_order_pending |
| `non_blocking` | `NonBlockingDisableCalling` | Warnings: numbers_present |
| `blocking_unless_forced` | `BlockingUnlessForced` | Soft blockers: non_user_entities_in_use, trunks_count |

**Scope:** `spark-admin:telephony_config_read`

#### CLI Examples

```bash
# Check if a location can be safely disabled for calling
wxcli location-settings safe-delete-check Y2lzY29zcGFyazovL...
```

---

### Extension Validation & Password Generation

#### `validate_extensions`

```python
def validate_extensions(
    self,
    location_id: str,
    extensions: list[str],
    org_id: str = None
) -> ValidateExtensionsResponse
```

**Scope:** `spark-admin:telephony_config_write`

#### `generate_password`

Generate an example SIP password using the location's effective password settings. Used during trunk creation.

```python
def generate_password(
    self,
    location_id: str,
    generate: list[str] = None,
    org_id: str = None
) -> str
```

**Returns:** The generated example SIP password string.

**Scope:** `spark-admin:telephony_config_write`

#### CLI Examples

```bash
# Validate extensions at a location
wxcli location-settings validate-extensions Y2lzY29zcGFyazovL... \
  --json-body '{"extensions": ["1000", "1001", "1002"]}'

# Generate an example SIP password for a location
wxcli location-call-handling generate-example-password Y2lzY29zcGFyazovL...
```

---

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()  # auth via WEBEX_ACCESS_TOKEN env var
BASE = "https://webexapis.com/v1"
```

All location-level call settings use raw HTTP via `api.session.rest_*()` methods. Full URLs are required. No auto-pagination -- pass `max=1000` for list endpoints. Responses are JSON dicts. Errors raise `RestError`.

#### Location Calling Config (List / Get / Enable / Update)

**List locations with calling details:**
```python
params = {"max": 1000}
result = api.session.rest_get(f"{BASE}/telephony/config/locations", params=params)
locations = result.get("locations", [])
# Each item: {"id", "name", "announcementLanguage", "callingLineId", "connection", ...}
```

**Get a single location's calling details:**
```python
loc = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}")
```

**Enable a location for calling:**
```python
body = {
    "id": location_id,          # existing location ID from Locations API
    "name": "San Jose HQ",
    "timeZone": "America/Los_Angeles",
    "preferredLanguage": "en_us",
    "announcementLanguage": "en_us"
}
result = api.session.rest_post(f"{BASE}/telephony/config/locations", json=body)
```

**Update location calling details:**
```python
body = {
    "announcementLanguage": "en_us",
    "outsideDialDigit": "9",
    "enforceOutsideDialDigit": True,
    "routingPrefix": "8001",
    "externalCallerIdName": "Acme Corp"
}
api.session.rest_put(f"{BASE}/telephony/config/locations/{loc_id}", json=body)
# Returns batchJobId if async update, otherwise None
```

#### Internal Dialing

**Read internal dialing settings:**
```python
result = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/internalDialing")
# {"enableUnknownExtensionRoutePolicy": bool, "unknownExtensionRouteIdentity": {...}}
```

**Update internal dialing:**
```python
body = {
    "enableUnknownExtensionRoutePolicy": True,
    "unknownExtensionRouteIdentity": {"id": trunk_id, "type": "TRUNK"}
}
api.session.rest_put(f"{BASE}/telephony/config/locations/{loc_id}/internalDialing", json=body)
```

#### Call Intercept

**Read call intercept:**
```python
result = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/intercept")
```

**Update call intercept:**
```python
body = {"enabled": True, "incoming": {"type": "INTERCEPT_ALL", "voicemailEnabled": True}}
api.session.rest_put(f"{BASE}/telephony/config/locations/{loc_id}/intercept", json=body)
```

**Available intercept phone numbers:**
```python
result = api.session.rest_get(
    f"{BASE}/telephony/config/locations/{loc_id}/callIntercept/availableNumbers",
    params={"max": 1000}
)
numbers = result.get("availableNumbers", [])
```

#### Music on Hold

**Read MoH settings:**
```python
result = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/musicOnHold")
# {"mohEnabled": bool, "greeting": "SYSTEM"|"CUSTOM", "audioFile": {...}, "playlist": {...}}
```

**Update MoH:**
```python
body = {"mohEnabled": True, "greeting": "SYSTEM"}
api.session.rest_put(f"{BASE}/telephony/config/locations/{loc_id}/musicOnHold", json=body)
```

#### Emergency Callback Number (ECBN)

**Read ECBN:**
```python
result = api.session.rest_get(
    f"{BASE}/telephony/config/locations/{loc_id}/features/emergencyCallbackNumber"
)
```

**Update ECBN:**
```python
body = {"selected": "LOCATION_NUMBER"}
# Or: {"selected": "LOCATION_MEMBER_NUMBER", "locationMemberId": member_id}
api.session.rest_put(
    f"{BASE}/telephony/config/locations/{loc_id}/features/emergencyCallbackNumber", json=body
)
```

**ECBN available phone numbers:**
```python
result = api.session.rest_get(
    f"{BASE}/telephony/config/locations/{loc_id}/emergencyCallbackNumber/availableNumbers",
    params={"max": 1000}
)
```

#### Announcement Language

**Change announcement language for existing entities at a location:**
```python
body = {
    "announcementLanguageCode": "en_us",
    "agentEnabled": True,       # change for people/workspaces
    "serviceEnabled": True      # change for features (AA, CQ, etc.)
}
api.session.rest_post(
    f"{BASE}/telephony/config/locations/{loc_id}/actions/modifyAnnouncementLanguage/invoke",
    json=body
)
```

> **Gotcha:** Use lowercase language codes (`en_us`, not `en_US`). The API rejects uppercase variants. Also, `announcementLanguage` may return `None` even when set -- this is a known API quirk.

#### Call Captions

**Read call captions settings:**
```python
result = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/callCaptions")
# {"locationClosedCaptionsEnabled", "locationTranscriptsEnabled",
#  "orgClosedCaptionsEnabled", "orgTranscriptsEnabled", "useOrgSettingsEnabled"}
```

**Update call captions:**
```python
body = {
    "locationClosedCaptionsEnabled": True,
    "locationTranscriptsEnabled": True,
    "useOrgSettingsEnabled": False
}
api.session.rest_put(f"{BASE}/telephony/config/locations/{loc_id}/callCaptions", json=body)
```

#### Device Settings

**Read location device overrides:**
```python
result = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/devices/settings")
```

#### Safe Delete Check

**Check if location can be safely disabled:**
```python
result = api.session.rest_post(
    f"{BASE}/telephony/config/locations/{loc_id}/actions/precheckForDeletion/invoke", json={}
)
# {"locationDeleteStatus": "BLOCKED"|"UNBLOCKED"|"FORCE_REQUIRED", "blocking": {...}, ...}
```

**Disable a calling location (async job):**
```python
body = {"locationId": loc_id, "locationName": "San Jose HQ", "forceDelete": False}
result = api.session.rest_post(
    f"{BASE}/telephony/config/jobs/locations/deleteCallingLocation", json=body
)
job_id = result.get("id")
```

**Job management:**
```python
# List jobs
api.session.rest_get(f"{BASE}/telephony/config/jobs/locations/deleteCallingLocation")
# Get job status
api.session.rest_get(f"{BASE}/telephony/config/jobs/locations/deleteCallingLocation/{job_id}")
# Get job errors
api.session.rest_get(f"{BASE}/telephony/config/jobs/locations/deleteCallingLocation/{job_id}/errors")
# Pause job
api.session.rest_post(f"{BASE}/telephony/config/jobs/locations/deleteCallingLocation/{job_id}/actions/pause/invoke", json={})
# Resume job
api.session.rest_post(f"{BASE}/telephony/config/jobs/locations/deleteCallingLocation/{job_id}/actions/resume/invoke", json={})
```

#### CLI Examples — Disable Calling Location Jobs

```bash
# Safe delete check before disabling a location
wxcli location-settings safe-delete-check Y2lzY29zcGFyazovL...

# Disable a calling location
wxcli location-settings create-delete-calling-location \
  --location-id Y2lzY29zcGFyazovL... \
  --location-name "San Jose HQ"

# Force-disable a calling location (when features like trunks exist)
wxcli location-settings create-delete-calling-location \
  --location-id Y2lzY29zcGFyazovL... \
  --location-name "San Jose HQ" \
  --force-delete

# List disable calling location jobs
wxcli location-settings list-delete-calling-location

# Get disable calling location job status
wxcli location-settings show-delete-calling-location JOB_ID

# Get job errors
wxcli location-settings list-errors JOB_ID

# Pause a job
wxcli location-settings pause-a-disable JOB_ID

# Resume a paused job
wxcli location-settings resume-a-paused JOB_ID
```

#### Extension Validation

**Validate extensions at a location:**
```python
body = {"extensions": ["1000", "1001", "1002"]}
result = api.session.rest_post(
    f"{BASE}/telephony/config/locations/{loc_id}/actions/validateExtensions/invoke", json=body
)
```

**Validate extensions org-wide:**
```python
body = {"extensions": ["1000", "1001"]}
result = api.session.rest_post(
    f"{BASE}/telephony/config/actions/validateExtensions/invoke", json=body
)
```

#### Private Network Connect

**Read PNC settings:**
```python
result = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/privateNetworkConnect")
```

**Update PNC settings:**
```python
body = {"networkConnectionType": "PRIVATE_NETWORK"}
api.session.rest_put(f"{BASE}/telephony/config/locations/{loc_id}/privateNetworkConnect", json=body)
```

#### CLI Examples — Private Network Connect

```bash
# Read private network connect settings
wxcli location-settings show-private-network-connect Y2lzY29zcGFyazovL...

# Update private network connect
wxcli location-settings update-private-network-connect Y2lzY29zcGFyazovL... \
  --json-body '{"networkConnectionType": "PRIVATE_NETWORK"}'
```

#### Routing Prefix Jobs

**List update routing prefix jobs:**
```python
result = api.session.rest_get(f"{BASE}/telephony/config/jobs/updateRoutingPrefix")
```

**Get job status / errors:**
```python
api.session.rest_get(f"{BASE}/telephony/config/jobs/updateRoutingPrefix/{job_id}")
api.session.rest_get(f"{BASE}/telephony/config/jobs/updateRoutingPrefix/{job_id}/errors")
```

#### Available Phone Numbers

Several endpoints return available phone numbers for different purposes. All follow the same pattern:

| Purpose | URL path |
|---------|----------|
| External Caller ID | `telephony/config/locations/{locId}/externalCallerId/availableNumbers` |
| Location main number | `telephony/config/locations/{locId}/availableNumbers` |
| Webex Go | `telephony/config/locations/{locId}/webexGo/availableNumbers` |
| ECBN | `telephony/config/locations/{locId}/emergencyCallbackNumber/availableNumbers` |
| Call Intercept | `telephony/config/locations/{locId}/callIntercept/availableNumbers` |
| Charge Number | `telephony/config/locations/{locId}/chargeNumber/availableNumbers` |
| Route Choices | `telephony/config/routeChoices` |

All accept `max`, `start`, `phoneNumber`, `ownerName` query params (availability varies by endpoint).

#### CLI Examples — Available Phone Numbers

```bash
# List phone numbers available for external caller ID
wxcli location-settings list-available-numbers-external-caller-id Y2lzY29zcGFyazovL...

# List available phone numbers for a location's main number
wxcli location-settings list-available-numbers-locations Y2lzY29zcGFyazovL...

# List Webex Go available phone numbers
wxcli location-settings list-available-numbers-webex-go Y2lzY29zcGFyazovL...

# List available charge numbers
wxcli location-settings list-available-numbers-charge-number Y2lzY29zcGFyazovL...

# List route choices
wxcli location-settings list-route-choices
```

#### Receptionist Contact Directories

**Create directory:**
```python
body = {"name": "Front Desk Contacts", "contacts": [{"id": person_id}]}
result = api.session.rest_post(
    f"{BASE}/telephony/config/locations/{loc_id}/receptionistContacts/directories", json=body
)
new_id = result.get("id")
```

**List directories:**
```python
result = api.session.rest_get(
    f"{BASE}/telephony/config/locations/{loc_id}/receptionistContacts/directories"
)
dirs = result.get("directories", [])
```

**Get directory details:**
```python
result = api.session.rest_get(
    f"{BASE}/telephony/config/locations/{loc_id}/receptionistContacts/directories/{dir_id}"
)
```

**Update directory (full replacement):**
```python
body = {"name": "Updated Name", "contacts": [{"id": person_id_1}, {"id": person_id_2}]}
api.session.rest_put(
    f"{BASE}/telephony/config/locations/{loc_id}/receptionistContacts/directories/{dir_id}",
    json=body
)
```

**Delete directory:**
```python
api.session.rest_delete(
    f"{BASE}/telephony/config/locations/{loc_id}/receptionistContacts/directories/{dir_id}"
)
```

#### CLI Examples — Receptionist Contact Directories

```bash
# List receptionist contact directories for a location
wxcli location-settings list-directories Y2lzY29zcGFyazovL...

# Get details for a specific directory
wxcli location-settings show-directories Y2lzY29zcGFyazovL... --json-body '...'

# Create a new receptionist contact directory
wxcli location-settings create-directories Y2lzY29zcGFyazovL... \
  --json-body '{"name": "Front Desk Contacts", "contacts": [{"id": "PERSON_ID"}]}'

# Update a directory (full replacement of contacts)
wxcli location-settings update-directories Y2lzY29zcGFyazovL... \
  --json-body '{"name": "Updated Name", "contacts": [{"id": "PERSON_ID_1"}, {"id": "PERSON_ID_2"}]}'

# Delete a receptionist contact directory
wxcli location-settings delete Y2lzY29zcGFyazovL...
```

---

### Additional Location-Level APIs on TelephonyLocationApi

#### `phone_numbers`

List service and standard PSTN numbers available to be assigned as the location's main number.

```python
def phone_numbers(
    self,
    location_id: str,
    phone_number: List[str] = None,
    owner_name: str = None,
    org_id: str = None,
    **params
) -> Generator[AvailableNumber, None, None]
```

#### `webex_go_available_phone_numbers`

List standard numbers available for Webex Go assignment at a location.

```python
def webex_go_available_phone_numbers(
    self,
    location_id: str,
    phone_number: List[str] = None,
    org_id: str = None,
    **params
) -> Generator[AvailableNumber, None, None]
```

#### `charge_number_available_phone_numbers`

List non-toll-free, non-mobile numbers available as the location's charge number.

```python
def charge_number_available_phone_numbers(
    self,
    location_id: str,
    phone_number: List[str] = None,
    owner_name: str = None,
    org_id: str = None,
    **params
) -> Generator[AvailableNumber, None, None]
```

#### Receptionist Contact Directories

These methods manage named directories of users and location features (Auto Attendant, Call Queue, Hunt Group, Single Number Reach, Paging Group):

```python
def create_receptionist_contact_directory(location_id, name, contacts, org_id=None) -> str
def list_receptionist_contact_directories(location_id, org_id=None) -> List[IdAndName]
def receptionist_contact_directory_details(location_id, directory_id, ...) -> List[ContactDetails]
def delete_receptionist_contact_directory(location_id, directory_id, org_id=None)
def modify_receptionist_contact_directory(location_id, directory_id, name, contacts, org_id=None) -> str
```

Note: `modify` performs a **full replacement** of the contacts list (not incremental). The details API is supported for orgs with fewer than 2000 users or location-based calling features; orgs exceeding this threshold get error 25395. <!-- Verified via wxc_sdk source (location/__init__.py docstring) 2026-03-19 -->

---

## 2. Voicemail Policies

### Location Voicemail Settings

**API path:** `api.telephony.location.voicemail`

**Source:** `wxc_sdk.telephony.location.vm`

Currently limited to enabling/disabling voicemail transcription at the location level.

#### `LocationVoiceMailSettings` Model

| Field | Type | Description |
|-------|------|-------------|
| `voicemail_transcription_enabled` | `bool` | Enable/disable voicemail transcription for the location |

#### `read`

```python
def read(
    self,
    location_id: str,
    org_id: str = None
) -> LocationVoiceMailSettings
```

**Scope:** `spark-admin:telephony_config_read`

#### `update`

```python
def update(
    self,
    location_id: str,
    settings: LocationVoiceMailSettings,
    org_id: str = None
)
```

**Scope:** `spark-admin:telephony_config_write`

#### CLI Examples

```bash
# Read location voicemail settings
wxcli location-voicemail show Y2lzY29zcGFyazovL...

# Enable voicemail transcription for a location
wxcli location-voicemail update Y2lzY29zcGFyazovL... --voicemail-transcription-enabled

# Disable voicemail transcription
wxcli location-voicemail update Y2lzY29zcGFyazovL... --no-voicemail-transcription-enabled
```

---

### Raw HTTP — Location Voicemail
<!-- Updated by playbook session 2026-03-18 -->

**Read location voicemail settings:**
```python
result = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/voicemail")
# {"voicemailTranscriptionEnabled": bool}
```

**Update location voicemail:**
```python
body = {"voicemailTranscriptionEnabled": True}
api.session.rest_put(f"{BASE}/telephony/config/locations/{loc_id}/voicemail", json=body)
```

---

### Organisation Voicemail Settings

**API path:** `api.telephony.organisation_voicemail` <!-- Verified via wxc_sdk telephony/__init__.py 2026-03-19 -->

**Source:** `wxc_sdk.telephony.organisation_vm`

**Base endpoint:** `telephony/config/voicemail/settings`

Controls org-wide voicemail message expiry and forwarding policies.

#### `OrganisationVoicemailSettings` Model

| Field | Type | Description |
|-------|------|-------------|
| `message_expiry_enabled` | `bool` | Enable deletion conditions for expired messages |
| `number_of_days_for_message_expiry` | `int` | Days after which messages expire |
| `strict_deletion_enabled` | `bool` | When enabled, both read and unread messages are deleted based on expiry. When disabled, unread messages are kept. |
| `voice_message_forwarding_enabled` | `bool` | Allow people to configure email forwarding of voicemails |

**Defaults** (from `OrganisationVoicemailSettings.default()`):
```python
message_expiry_enabled = False
number_of_days_for_message_expiry = 15
strict_deletion_enabled = False
voice_message_forwarding_enabled = False
```

#### `read`

```python
def read(
    self,
    org_id: str = None
) -> OrganisationVoicemailSettings
```

**Scope:** `spark-admin:telephony_config_read`

#### `update`

```python
def update(
    self,
    settings: OrganisationVoicemailSettings,
    org_id: str = None
)
```

**Scope:** `spark-admin:telephony_config_write`

---

### Raw HTTP — Organisation Voicemail
<!-- Updated by playbook session 2026-03-18 -->

**Read org voicemail settings:**
```python
result = api.session.rest_get(f"{BASE}/telephony/config/voicemail/settings")
# {"messageExpiryEnabled", "numberOfDaysForMessageExpiry", "strictDeletionEnabled",
#  "voiceMessageForwardingEnabled"}
```

**Update org voicemail settings:**
```python
body = {
    "messageExpiryEnabled": True,
    "numberOfDaysForMessageExpiry": 30,
    "strictDeletionEnabled": False,
    "voiceMessageForwardingEnabled": True
}
api.session.rest_put(f"{BASE}/telephony/config/voicemail/settings", json=body)
```

---

## 3. Voicemail Rules (Org-Level Passcode Policy)

**API path:** `api.telephony.voicemail_rules` <!-- Verified via wxc_sdk telephony/__init__.py 2026-03-19 -->

**Source:** `wxc_sdk.telephony.vm_rules`

**Base endpoint:** `telephony/config/voicemail/rules`

Defines org-wide default voicemail passcode requirements.

### `VoiceMailRules` Model

| Field | Type | Description |
|-------|------|-------------|
| `default_voicemail_pin_rules` | `DefaultVoicemailPinRules` | Read-only rules (excluded from update payload) |
| `default_voicemail_pin_enabled` | `bool` | Enable setting a default pin for new users (update only) |
| `default_voicemail_pin` | `str` | The default pin value (update only) |
| `expire_passcode` | `EnabledAndNumberOfDays` | Passcode expiry settings |
| `change_passcode` | `EnabledAndNumberOfDays` | Minimum days before passcode can be changed |
| `block_previous_passcodes` | `BlockPreviousPasscodes` | Block reuse of N previous passcodes |

### `DefaultVoicemailPinRules` Model (read-only)

| Field | Type | Description |
|-------|------|-------------|
| `block_repeated_patterns_enabled` | `bool` | Block repeated patterns |
| `block_repeated_digits` | `BlockRepeatedDigits` | Block repeated digit groups (enabled, max) |
| `block_contiguous_sequences` | `BlockContiguousSequences` | Block ascending/descending sequences (enabled, ascending count, descending count) |
| `length` | `PinLength` | Min/max passcode length |
| `default_voicemail_pin_enabled` | `bool` | Whether default pin is enabled |

### Supporting Models

#### `BlockRepeatedDigits`

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `enabled` | `bool` | | Block repeated digits |
| `max` | `int` | 1-6 | Max repeated digits allowed |

#### `BlockContiguousSequences`

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `enabled` | `bool` | | Block sequential digits |
| `number_of_ascending_digits` | `int` | 2-5 | Ascending sequence length to block |
| `number_of_descending_digits` | `int` | 2-5 | Descending sequence length to block |

#### `PinLength`

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `min` | `int` | 2-15 | Minimum passcode length |
| `max` | `int` | 3-30 | Maximum passcode length |

#### `BlockPreviousPasscodes`

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `enabled` | `bool` | | Block reuse of previous passcodes |
| `number_of_passcodes` | `int` | 1-10 | How many previous passcodes to block |

#### `EnabledAndNumberOfDays`

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | `bool` | Feature on/off |
| `number_of_days` | `int` | Number of days for expiry/change window |

### Defaults (from `VoiceMailRules.default()`)

```python
expire_passcode:        enabled=True,  number_of_days=180
change_passcode:        enabled=False, number_of_days=1
block_previous_passcodes: enabled=True,  number_of_passcodes=10
# Pin rules defaults:
block_repeated_patterns: True
block_repeated_digits:   max=3
block_contiguous_sequences: ascending=3, descending=3
pin_length:             min=6, max=30
default_voicemail_pin:  disabled
```

### Methods

#### `read`

```python
def read(
    self,
    org_id: str = None
) -> VoiceMailRules
```

**Scope:** `spark-admin:telephony_config_read`

#### `update`

```python
def update(
    self,
    settings: VoiceMailRules,
    org_id: str = None
)
```

**Important:** The `default_voicemail_pin_rules` field is **excluded** from the update payload. To set a default pin, use `default_voicemail_pin_enabled` and `default_voicemail_pin` on the `VoiceMailRules` object directly. If you enable a default pin, communicate it to your users -- they must reset it before accessing voicemail.

**Scope:** `spark-admin:telephony_config_write`

---

### Raw HTTP — Voicemail Rules
<!-- Updated by playbook session 2026-03-18 -->

**Read org voicemail passcode rules:**
```python
result = api.session.rest_get(f"{BASE}/telephony/config/voicemail/rules")
# {"defaultVoicemailPinRules": {...}, "expirePasscode": {...},
#  "changePasscode": {...}, "blockPreviousPasscodes": {...}}
```

**Update org voicemail rules:**
```python
body = {
    "defaultVoicemailPinEnabled": True,
    "defaultVoicemailPin": "654321",
    "expirePasscode": {"enabled": True, "numberOfDays": 90},
    "changePasscode": {"enabled": False, "numberOfDays": 1},
    "blockPreviousPasscodes": {"enabled": True, "numberOfPasscodes": 5}
}
api.session.rest_put(f"{BASE}/telephony/config/voicemail/rules", json=body)
```

> **Gotcha:** The `defaultVoicemailPinRules` field is **read-only** and excluded from update payloads. Set default PINs via the top-level `defaultVoicemailPinEnabled` and `defaultVoicemailPin` fields instead.

---

## 4. Voice Messaging (User-Level)

**API path:** `api.telephony.voice_messaging` <!-- Verified via wxc_sdk telephony/__init__.py 2026-03-19 -->

**Source:** `wxc_sdk.telephony.voice_messaging`

**Base endpoint:** `telephony/voiceMessages`

User-scoped API (not admin). Handles voicemail message retrieval, deletion, and read/unread status. All GET operations require `spark:calls_read`; write operations require `spark:calls_write`.

### Models

#### `MessageSummary`

| Field | Type | Description |
|-------|------|-------------|
| `new_messages` | `int` | Count of unread voicemail messages |
| `old_messages` | `int` | Count of read voicemail messages |
| `new_urgent_messages` | `int` | Count of unread urgent messages |
| `old_urgent_messages` | `int` | Count of read urgent messages |

#### `VoiceMessageDetails`

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Message identifier |
| `duration` | `int` | Duration in seconds (not present for FAX) |
| `calling_party` | `VoiceMailPartyInformation` | Who left the message |
| `urgent` | `bool` | Urgent flag |
| `confidential` | `bool` | Confidential flag |
| `read` | `bool` | Whether the message has been read |
| `fax_page_count` | `int` | Page count (FAX only) |
| `created` | `str` | Timestamp of message creation |

#### `VoiceMailPartyInformation`

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Caller name (absent if privacy enabled) |
| `number` | `str` | Caller number — digits, URI, or E.164 (absent if privacy enabled) |
| `person_id` | `str` | Person ID (absent if privacy enabled) |
| `place_id` | `str` | Place ID (absent if privacy enabled) |
| `privacy_enabled` | `bool` | Whether privacy is on |

### Methods

#### `summary`

```python
def summary(self) -> MessageSummary
```

Get voicemail message counts. **Scope:** `spark:calls_read`

#### `list`

```python
def list(
    self,
    line_owner_id: str = None,
    **params
) -> Generator[VoiceMessageDetails, None, None]
```

List all voicemail messages. `line_owner_id` supports secondary lines on shared devices.

**Scope:** `spark:calls_read`

#### `delete`

```python
def delete(self, message_id: str)
```

Delete a specific voicemail message. **Scope:** `spark:calls_write`

#### `mark_as_read`

```python
def mark_as_read(
    self,
    message_id: str,
    line_owner_id: str = None
)
```

Mark a specific message (or all messages if `message_id` semantics allow) as read. **Scope:** `spark:calls_write`

#### `mark_as_unread`

```python
def mark_as_unread(
    self,
    message_id: str,
    line_owner_id: str = None
)
```

Mark a specific message (or all messages) as unread. **Scope:** `spark:calls_write`

---

### Raw HTTP — Voice Messaging
<!-- Updated by playbook session 2026-03-18 -->

Voice messaging is user-scoped (not admin). Uses `spark:calls_read` and `spark:calls_write` scopes.

**Get voicemail summary:**
```python
result = api.session.rest_get(f"{BASE}/telephony/voiceMessages/summary")
# {"newMessages", "oldMessages", "newUrgentMessages", "oldUrgentMessages"}
```

**List voicemail messages:**
```python
result = api.session.rest_get(f"{BASE}/telephony/voiceMessages", params={"max": 100})
messages = result.get("items", [])
```

**Delete a voicemail message:**
```python
api.session.rest_delete(f"{BASE}/telephony/voiceMessages/{message_id}")
```

**Mark as read / unread:**
```python
api.session.rest_put(f"{BASE}/telephony/voiceMessages/{message_id}/markAsRead")
api.session.rest_put(f"{BASE}/telephony/voiceMessages/{message_id}/markAsUnread")
```

---

## 5. Voice Portal

**API path:** `api.telephony.voiceportal` <!-- Verified via wxc_sdk telephony/__init__.py 2026-03-19 -->

**Source:** `wxc_sdk.telephony.voiceportal`

**Base endpoint:** `telephony/config/locations/{locationId}/voicePortal`

Voice portals provide an interactive voice response (IVR) system so administrators can manage auto attendant announcements. Each location has one voice portal.

### `VoicePortalSettings` Model

| Field | Type | Description |
|-------|------|-------------|
| `portal_id` | `str` | Voice Portal ID (aliased from `id`) |
| `name` | `str` | Voice Portal name |
| `language` | `str` | Language for audio announcements (excluded from updates) |
| `language_code` | `str` | Language code for voicemail group audio announcement |
| `extension` | `str` | Extension of incoming call |
| `phone_number` | `str` | Phone number of incoming call |
| `first_name` | `str` | **Deprecated.** Use `direct_line_caller_id_name` and `dial_by_name` instead. |
| `last_name` | `str` | **Deprecated.** Use `direct_line_caller_id_name` and `dial_by_name` instead. |
| `direct_line_caller_id_name` | `DirectLineCallerIdName` | Caller ID name shown for this voice portal |
| `dial_by_name` | `str` | Name used for dial-by-name functions |

### `PasscodeRules` Model

Voice portal passcode rules (separate from the org-level voicemail rules).

| Field | Type | Description |
|-------|------|-------------|
| `expire_passcode` | `ExpirePasscode` | Passcode expiry (enabled, days) |
| `failed_attempts` | `FailedAttempts` | Lock after N failed attempts (enabled, attempts) |
| `block_previous_passcodes` | `BlockPreviousPasscodes` | Block reuse of previous passcodes |
| `block_repeated_digits` | `BlockRepeatedDigits` | Block repeated digit groups |
| `block_contiguous_sequences` | `BlockContiguousSequences` | Block sequential digits |
| `length` | `PinLength` | Min/max passcode length |
| `block_reversed_user_number_enabled` | `bool` | Block reversed phone number/extension as passcode |
| `block_user_number_enabled` | `bool` | Block user phone number/extension as passcode |
| `block_repeated_patterns_enabled` | `bool` | Block repeated patterns |
| `block_reversed_old_passcode_enabled` | `bool` | Block reversed old passcode |

### Methods

#### `read`

```python
def read(
    self,
    location_id: str,
    org_id: str = None
) -> VoicePortalSettings
```

**Scope:** `spark-admin:telephony_config_read`

#### `update`

```python
def update(
    self,
    location_id: str,
    settings: VoicePortalSettings,
    passcode: str = None,
    org_id: str = None
)
```

Update voice portal settings. Pass `passcode` to change the portal passcode (SDK sends both `newPasscode` and `confirmPasscode` automatically). The `portal_id` and `language` fields are excluded from the update payload.

**Scope:** `spark-admin:telephony_config_write`

#### `available_phone_numbers`

```python
def available_phone_numbers(
    self,
    location_id: str,
    phone_number: list[str] = None,
    org_id: str = None,
    **params
) -> Generator[AvailableNumber, None, None]
```

List numbers available to be assigned as the voice portal's phone number.

**Scope:** `spark-admin:telephony_config_read`

#### `passcode_rules`

```python
def passcode_rules(
    self,
    location_id: str,
    org_id: str = None
) -> PasscodeRules
```

Retrieve the voice portal passcode rules for a location.

**Scope:** `spark-admin:telephony_config_read`

#### CLI Examples

```bash
# Read voice portal settings for a location
wxcli location-voicemail show-voice-portal Y2lzY29zcGFyazovL...

# Update voice portal settings
wxcli location-voicemail update-voice-portal Y2lzY29zcGFyazovL... \
  --name "Voice Portal" \
  --extension "9999" \
  --language-code "en_us" \
  --dial-by-name "Voice Portal"

# Read voice portal passcode rules
wxcli location-voicemail show-passcode-rules Y2lzY29zcGFyazovL...

# List available phone numbers for voice portal
wxcli location-voicemail list-available-numbers-voice-portal Y2lzY29zcGFyazovL...
```

---

### Raw HTTP — Voice Portal
<!-- Updated by playbook session 2026-03-18 -->

**Read voice portal settings:**
```python
result = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}/voicePortal")
# {"id", "name", "languageCode", "extension", "phoneNumber", "firstName", "lastName",
#  "directLineCallerIdName", "dialByName"}
```

**Update voice portal:**
```python
body = {
    "name": "Voice Portal",
    "extension": "9999",
    "languageCode": "en_us",
    "dialByName": "Voice Portal"
}
api.session.rest_put(f"{BASE}/telephony/config/locations/{loc_id}/voicePortal", json=body)
```

> **Gotcha:** To change the portal passcode via raw HTTP, include `newPasscode` and `confirmPasscode` in the body (the SDK wraps this for you, but raw HTTP requires both fields).

**Read voice portal passcode rules:**
```python
result = api.session.rest_get(
    f"{BASE}/telephony/config/locations/{loc_id}/voicePortal/passcodeRules"
)
```

**Available phone numbers for voice portal:**
```python
result = api.session.rest_get(
    f"{BASE}/telephony/config/locations/{loc_id}/voicePortal/availableNumbers",
    params={"max": 1000}
)
numbers = result.get("availableNumbers", [])
```

### Raw HTTP — Voicemail Groups
<!-- Updated by playbook session 2026-03-18 -->

Voicemail groups are location-scoped features for shared voicemail boxes.

**List voicemail groups:**
```python
params = {"locationId": loc_id, "max": 1000}
result = api.session.rest_get(f"{BASE}/telephony/config/voicemailGroups", params=params)
groups = result.get("voicemailGroups", [])
```

**Get voicemail group details:**
```python
result = api.session.rest_get(
    f"{BASE}/telephony/config/locations/{loc_id}/voicemailGroups/{vmg_id}"
)
```

**Create voicemail group:**
```python
body = {
    "name": "Sales VM Group",
    "extension": "2000",
    "passcode": "123456",
    "languageCode": "en_us"
}
result = api.session.rest_post(
    f"{BASE}/telephony/config/locations/{loc_id}/voicemailGroups", json=body
)
new_id = result.get("id")
```

**Update voicemail group:**
```python
body = {"name": "Updated Sales VM", "enabled": True, "greeting": "CUSTOM"}
api.session.rest_put(
    f"{BASE}/telephony/config/locations/{loc_id}/voicemailGroups/{vmg_id}", json=body
)
```

**Delete voicemail group:**
```python
api.session.rest_delete(
    f"{BASE}/telephony/config/locations/{loc_id}/voicemailGroups/{vmg_id}"
)
```

**Available phone numbers for voicemail groups:**
```python
# Regular available numbers
api.session.rest_get(
    f"{BASE}/telephony/config/locations/{loc_id}/voicemailGroups/availableNumbers",
    params={"max": 1000}
)
# Fax message available numbers
api.session.rest_get(
    f"{BASE}/telephony/config/locations/{loc_id}/voicemailGroups/faxMessage/availableNumbers",
    params={"max": 1000}
)
```

#### CLI Examples — Voicemail Groups

```bash
# List voicemail groups for a location
wxcli location-voicemail list --location-id Y2lzY29zcGFyazovL...

# Get voicemail group details
wxcli location-voicemail show-voicemail-groups Y2lzY29zcGFyazovL...

# Create a voicemail group
wxcli location-voicemail create Y2lzY29zcGFyazovL... \
  --name "Sales VM Group" \
  --extension "2000" \
  --passcode "123456" \
  --language-code "en_us"

# Update a voicemail group
wxcli location-voicemail update-voicemail-groups Y2lzY29zcGFyazovL... \
  --json-body '{"name": "Updated Sales VM", "enabled": true}'

# Delete a voicemail group
wxcli location-voicemail delete Y2lzY29zcGFyazovL...

# List available phone numbers for voicemail groups
wxcli location-voicemail list-available-numbers-voicemail-groups Y2lzY29zcGFyazovL...

# List fax message available phone numbers
wxcli location-voicemail list-available-numbers-fax-message Y2lzY29zcGFyazovL...
```

---

## API Access Path Summary

| Setting | SDK Access Path | Scope |
|---------|----------------|-------|
| Location telephony details | `api.telephony.location.details()` | read |
| Location list | `api.telephony.location.list()` | read |
| Enable calling | `api.telephony.location.enable_for_calling()` | write |
| Update location | `api.telephony.location.update()` | write |
| Internal dialing | `api.telephony.location.internal_dialing.read/update()` | read/write |
| Call intercept | `api.telephony.location.intercept.read/configure()` | read/write |
| Music on hold | `api.telephony.location.moh.read/update()` | read/write |
| Location numbers | `api.telephony.location.number.add/remove/activate/manage_number_state()` | write |
| Location voicemail | `api.telephony.location.voicemail.read/update()` | read/write |
| ECBN | `api.telephony.location.read_ecbn/update_ecbn()` | read/write |
| Call captions | `api.telephony.location.get_call_captions_settings/update_call_captions_settings()` | read/write |
| Announcement language | `api.telephony.location.change_announcement_language()` | write |
| Device settings | `api.telephony.location.device_settings()` | read |
| Safe delete check | `api.telephony.location.safe_delete_check_before_disabling_calling_location()` | read |
| Org voicemail settings | `api.telephony.organisation_voicemail.read/update()` | read/write |
| Voicemail rules | `api.telephony.voicemail_rules.read/update()` | read/write |
| Voice messaging (user) | `api.telephony.voice_messaging.summary/list/delete/mark_as_read/mark_as_unread()` | calls_read/write |
| Voice portal | `api.telephony.voiceportal.read/update/passcode_rules/available_phone_numbers()` | read/write |

<!-- Verified: all attribute names confirmed against wxc_sdk telephony/__init__.py 2026-03-19: organisation_voicemail, voicemail_rules, voice_messaging, voiceportal -->

---

## Raw HTTP URL Pattern Summary
<!-- Updated by playbook session 2026-03-18 -->

| Area | URL Pattern | Methods |
|------|-------------|---------|
| Location calling config | `telephony/config/locations` | GET (list), POST (enable) |
| Location details | `telephony/config/locations/{locId}` | GET, PUT |
| Internal dialing | `telephony/config/locations/{locId}/internalDialing` | GET, PUT |
| Call intercept | `telephony/config/locations/{locId}/intercept` | GET, PUT |
| Music on hold | `telephony/config/locations/{locId}/musicOnHold` | GET, PUT |
| ECBN | `telephony/config/locations/{locId}/features/emergencyCallbackNumber` | GET, PUT |
| Call captions | `telephony/config/locations/{locId}/callCaptions` | GET, PUT |
| Announcement language | `telephony/config/locations/{locId}/actions/modifyAnnouncementLanguage/invoke` | POST |
| Private network connect | `telephony/config/locations/{locId}/privateNetworkConnect` | GET, PUT |
| Safe delete precheck | `telephony/config/locations/{locId}/actions/precheckForDeletion/invoke` | POST |
| Validate extensions | `telephony/config/locations/{locId}/actions/validateExtensions/invoke` | POST |
| Validate extensions (org) | `telephony/config/actions/validateExtensions/invoke` | POST |
| Location voicemail | `telephony/config/locations/{locId}/voicemail` | GET, PUT |
| Voice portal | `telephony/config/locations/{locId}/voicePortal` | GET, PUT |
| Voice portal passcode rules | `telephony/config/locations/{locId}/voicePortal/passcodeRules` | GET |
| Org voicemail settings | `telephony/config/voicemail/settings` | GET, PUT |
| Org voicemail rules | `telephony/config/voicemail/rules` | GET, PUT |
| Voicemail groups (list) | `telephony/config/voicemailGroups` | GET |
| Voicemail groups (CRUD) | `telephony/config/locations/{locId}/voicemailGroups/{vmgId}` | GET, PUT, DELETE |
| Voicemail groups (create) | `telephony/config/locations/{locId}/voicemailGroups` | POST |
| Receptionist directories | `telephony/config/locations/{locId}/receptionistContacts/directories` | GET, POST |
| Receptionist directory | `telephony/config/locations/{locId}/receptionistContacts/directories/{dirId}` | GET, PUT, DELETE |
| Delete calling location job | `telephony/config/jobs/locations/deleteCallingLocation` | GET, POST |
| Routing prefix jobs | `telephony/config/jobs/updateRoutingPrefix` | GET |

## Raw HTTP Gotchas
<!-- Updated by playbook session 2026-03-18 -->

1. **Lowercase language codes** -- The API rejects `en_US`; use `en_us` instead. Applies to both `announcementLanguage` on location updates and `announcementLanguageCode` on the language change action.
2. **`announcementLanguage` returns None** -- Even when a language is set, the GET response may return `null` for this field. This is a known API quirk.
3. **Voice portal passcode requires two fields** -- When changing passcode via raw HTTP, you must send both `newPasscode` and `confirmPasscode`. The SDK handles this automatically but raw HTTP does not.
4. **Receptionist directory modify is full replacement** -- PUT on a directory replaces the entire contacts list. Always include the full desired contacts array.
5. **No auto-pagination** -- All list endpoints require manual `max` and `start` params. Set `max=1000` for maximum page size.
6. **Action endpoints use POST** -- `validateExtensions`, `modifyAnnouncementLanguage`, `precheckForDeletion`, job pause/resume all use POST, not GET or PUT.

## CLI: `calling-service` (Org-Level Calling Service Settings)

The `calling-service` CLI group covers org-level voicemail settings, voicemail rules, music on hold configuration, large organization status, and call captions. These are org-wide settings, not per-location.

| Command | Description |
|---------|-------------|
| `calling-service list` | List announcement languages |
| `calling-service show` | Get org voicemail settings |
| `calling-service update` | Update org voicemail settings |
| `calling-service show-rules` | Get org voicemail rules (passcode policy) |
| `calling-service update-rules` | Update org voicemail rules |
| `calling-service show-settings` | Get org music on hold configuration |
| `calling-service update-settings` | Update org music on hold configuration |
| `calling-service show-large-org-status` | Get large organization status |
| `calling-service show-call-captions` | Get org call captions settings |
| `calling-service update-call-captions` | Update org call captions settings |

```bash
# List available announcement languages
wxcli calling-service list

# Get org-level voicemail settings
wxcli calling-service show

# Enable voicemail message expiry after 30 days
wxcli calling-service update --message-expiry-enabled --number-of-days-for-message-expiry 30

# Get org music on hold configuration
wxcli calling-service show-settings

# Check if this org qualifies as a large organization
wxcli calling-service show-large-org-status

# Get org call captions settings
wxcli calling-service show-call-captions

# Enable org-level closed captions and transcripts
wxcli calling-service update-call-captions --org-closed-captions-enabled --org-transcripts-enabled
```

## CLI Files

| CLI Group | File |
|-----------|------|
| `location-call-settings` | `src/wxcli/commands/location_call_settings.py` |
| `location-call-settings-voicemail` | `src/wxcli/commands/location_call_settings_voicemail.py` |
| `calling-service` | `src/wxcli/commands/calling_service.py` |

---

## See Also

- **[Person Call Settings — Handling](person-call-settings-handling.md)** — Per-user call forwarding overrides and call intercept settings that override location-level defaults
- **[Person Call Settings — Media](person-call-settings-media.md)** — Per-user voicemail settings, music on hold overrides, and call intercept at the person level
- **[Person Call Settings — Behavior](person-call-settings-behavior.md)** — Per-user ECBN settings that override the location ECBN default
