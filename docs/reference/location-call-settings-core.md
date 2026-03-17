# Location Call Settings — Core Settings & Voicemail

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

**Note:** Not supported for locations in India. <!-- NEEDS VERIFICATION: exact country restrictions -->

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

Note: `modify` performs a **full replacement** of the contacts list (not incremental). The details API has a limit of 2000 users/features per location. <!-- NEEDS VERIFICATION: exact error code 25395 threshold -->

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

---

### Organisation Voicemail Settings

**API path:** `api.telephony.organisation_voicemail` <!-- NEEDS VERIFICATION: exact attribute name on the telephony API -->

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

## 3. Voicemail Rules (Org-Level Passcode Policy)

**API path:** `api.telephony.voicemail_rules` <!-- NEEDS VERIFICATION: exact attribute name on the telephony API -->

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

## 4. Voice Messaging (User-Level)

**API path:** `api.telephony.voice_messaging` <!-- NEEDS VERIFICATION: exact attribute name -->

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

## 5. Voice Portal

**API path:** `api.telephony.voiceportal` <!-- NEEDS VERIFICATION: exact attribute name -->

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

<!-- NEEDS VERIFICATION: The exact attribute names on the top-level telephony API object (e.g., api.telephony.organisation_voicemail vs api.telephony.org_voicemail) should be confirmed against the TelephonyApi class definition in wxc_sdk/telephony/__init__.py -->
