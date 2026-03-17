# Emergency Services & E911

## Overview

Webex Calling E911 compliance requires three interlocking configurations:

| Layer | What It Configures | SDK API |
|-------|--------------------|---------|
| **Emergency Call Notifications** | Org-level email alerts when any emergency call is placed | `OrgEmergencyServicesApi` |
| **Emergency Addresses** | Physical civic addresses associated with locations and phone numbers | `EmergencyAddressApi` |
| **Emergency Callback Number (ECBN)** | Per-person/workspace/virtual-line callback number for return calls from PSAP | `ECBNApi` |

All three are needed for full E911 compliance in the United States. Emergency call notifications satisfy **Kari's Law** (U.S. Public Law 115-127), which requires that any emergency call from within an organization generates a notification. Emergency addresses and ECBN satisfy **RAY BAUM's Act** requirements for dispatchable location information.

---

## 1. Emergency Call Notifications (Org-Level)

### What It Does

When enabled, sends an email to a specified address every time someone in the organization dials emergency services (911 in the U.S.). This is the org-wide kill switch for Kari's Law compliance.

### SDK Access

```python
api = wxc_api.telephony.emergency_services  # OrgEmergencyServicesApi instance
```

Base path: `telephony/config/emergencyCallNotification`

Required scopes:
- **Read**: `spark-admin:telephony_config_read`
- **Write**: `spark-admin:telephony_config_write`

### Read Notification Settings

```python
OrgEmergencyServicesApi.read_emergency_call_notification(
    org_id: str = None,
) -> OrgEmergencyCallNotification
```

### Update Notification Settings

```python
OrgEmergencyServicesApi.update_emergency_call_notification(
    setting: OrgEmergencyCallNotification,
    org_id: str = None,
) -> None
```

**Example -- enable emergency call notifications:**
```python
from wxc_sdk.telephony.emergency_services import OrgEmergencyCallNotification

setting = OrgEmergencyCallNotification(
    emergency_call_notification_enabled=True,
    allow_email_notification_all_location_enabled=True,
    email_address="security@company.com"
)
api.telephony.emergency_services.update_emergency_call_notification(setting=setting)
```

### Data Model

```python
class OrgEmergencyCallNotification(ApiModel):
    # When True, sends email on any emergency call
    emergency_call_notification_enabled: Optional[bool]
    # When True, sends notifications for ALL locations (not just specific ones)
    allow_email_notification_all_location_enabled: Optional[bool]
    # Email address that receives the notification
    email_address: Optional[str]
```

---

## 2. Emergency Addresses

### What They Are

Emergency addresses are the physical civic addresses associated with phone numbers and locations. When someone dials 911, this address is transmitted to the PSAP (Public Safety Answering Point) so first responders know where to go.

Emergency addresses can be set at two levels:
- **Location level** -- default address for all numbers at that location
- **Phone number level** -- per-number override (e.g., for users on different floors or in different buildings at the same location)

### SDK Access

```python
api = wxc_api.telephony.emergency_address  # EmergencyAddressApi instance
```

Base path: `telephony/pstn`

Required scopes:
- **Read/Lookup**: `spark-admin:telephony_pstn_read`
- **Write**: `spark-admin:telephony_pstn_write`

### Operations

#### Add Emergency Address to a Location

```python
EmergencyAddressApi.add_to_location(
    location_id: str,                     # Required
    address: Union[EmergencyAddress, SuggestedEmergencyAddress],  # Required
    org_id: str = None,
) -> str  # Returns the new emergency address ID
```

**Example:**
```python
from wxc_sdk.telephony.emergency_address import EmergencyAddress

addr = EmergencyAddress(
    address1="100 Main Street",
    address2="Suite 400",
    city="San Jose",
    state="CA",
    postal_code="95110",
    country="US"
)
addr_id = api.telephony.emergency_address.add_to_location(
    location_id="loc_id_123",
    address=addr
)
```

#### Lookup / Validate an Address

```python
EmergencyAddressApi.lookup_for_location(
    location_id: str,                     # Required
    address: Union[EmergencyAddress, SuggestedEmergencyAddress],  # Required
    org_id: str = None,
) -> list[SuggestedEmergencyAddress]
```

Returns a list of suggested addresses. If the input address is valid and unchanged, no errors are returned. If corrections were needed, the response includes the corrected address along with error details in each `SuggestedEmergencyAddress.errors` list.

**Always validate before adding.** The PSAP database requires standardized addresses. This lookup normalizes the input and flags issues.

**Example:**
```python
suggestions = api.telephony.emergency_address.lookup_for_location(
    location_id="loc_id_123",
    address=EmergencyAddress(
        address1="100 Main St",
        city="San Jose",
        state="CA",
        postal_code="95110",
        country="US"
    )
)
if suggestions and not suggestions[0].errors:
    # Address is valid, use the suggested (normalized) version
    validated_addr = suggestions[0]
    addr_id = api.telephony.emergency_address.add_to_location(
        location_id="loc_id_123",
        address=validated_addr
    )
```

#### Update Emergency Address for a Location

```python
EmergencyAddressApi.update_for_location(
    location_id: str,                     # Required
    address_id: str,                      # Required -- ID of existing address to update
    address: Union[EmergencyAddress, SuggestedEmergencyAddress],  # Required
    org_id: str = None,
) -> None
```

#### Update Emergency Address for a Phone Number

```python
EmergencyAddressApi.update_for_phone_number(
    phone_number: str,                    # Required -- the E.164 phone number
    emergency_address: Union[EmergencyAddress, SuggestedEmergencyAddress] = None,
    org_id: str = None,
) -> None
```

Use this to set a per-number emergency address that overrides the location default. **Passing an empty/None address deletes the custom address** and reverts the number to the location's default emergency address.

### Data Models

#### EmergencyAddress

```python
class EmergencyAddress(ApiModel):
    address1: Optional[str]              # Primary street (e.g., "100 Main Street")
    address2: Optional[str]              # Secondary (e.g., "Suite 400", "Floor 3")
    city: Optional[str]
    state: Optional[str]                 # State / Province / Region
    postal_code: Optional[str]
    country: Optional[str]               # Country code (e.g., "US")
```

#### SuggestedEmergencyAddress

Extends `EmergencyAddress` with validation metadata:

```python
class SuggestedEmergencyAddress(EmergencyAddress):
    meta: Optional[dict]                 # Additional metadata
    errors: Optional[list[AddressLookupError]]  # Validation errors (present when input was corrected)
```

#### AddressLookupError

```python
class AddressLookupError(ApiModel):
    code: Optional[str]                  # Error code
    title: Optional[str]                 # Error title
    detail: Optional[str]                # Detailed error message
```

---

## 3. Emergency Callback Number (ECBN)

### What It Is

The Emergency Callback Number (ECBN) is the phone number that the PSAP (Public Safety Answering Point) uses to call back if an emergency call is disconnected. This is critical for extension-only users who don't have a direct DID -- without an ECBN, the PSAP has no number to call back.

ECBN applies to:
- **People** (users)
- **Workspaces**
- **Virtual lines**

### SDK Access

```python
# For person ECBN:
api = wxc_api.person_settings.ecbn  # ECBNApi instance

# For virtual line ECBN:
api = wxc_api.telephony.virtual_lines.ecbn  # ECBNApi instance (virtual line selector)
```

The `ECBNApi` is a `PersonSettingsApiChild` that works across entity types via the `ApiSelector`:
- `ApiSelector.person` -- URL: `telephony/config/people/{id}/emergencyCallbackNumber`
- `ApiSelector.workspace` -- URL: `telephony/config/workspaces/{id}/emergencyCallbackNumber`
- `ApiSelector.virtual_line` -- URL: `telephony/config/virtualLines/{id}/emergencyCallbackNumber`

Required scopes:
- **Read**: `spark-admin:telephony_config_read`
- **Write**: `spark-admin:telephony_config_write`

### ECBN Selection Options

There are multiple sources for where the ECBN comes from, in order of specificity:

| Selection | Enum Value | When To Use |
|-----------|-----------|-------------|
| **Direct Line** | `DIRECT_LINE` | User has their own DID -- PSAP calls back that number directly |
| **Location ECBN** | `LOCATION_ECBN` | Location has a dedicated ECBN different from the main number -- used for extension-only users |
| **Location Member Number** | `LOCATION_MEMBER_NUMBER` | Another user/workspace/virtual line's number at the same location -- used for multi-floor/multi-building locations to get a more accurate ESA |
| **None** | `NONE` | No selection (falls back to system default) |

### Operations

#### Read ECBN Settings

```python
ECBNApi.read(
    entity_id: str,                       # Person ID, workspace ID, or virtual line ID
    org_id: str = None,
) -> PersonECBN
```

Returns the current ECBN configuration including the selected source, direct line info, location ECBN info, location member info, and the default fallback info.

**Example:**
```python
ecbn = api.person_settings.ecbn.read(entity_id="person_id_123")
print(f"Selected: {ecbn.selected}")
print(f"Effective value: {ecbn.direct_line_info.effective_value}")
```

#### Configure ECBN

```python
ECBNApi.configure(
    entity_id: str,                       # Required
    selected: SelectedECBN,               # Required -- DIRECT_LINE, LOCATION_ECBN, or LOCATION_MEMBER_NUMBER
    location_member_id: str = None,       # Required when selected=LOCATION_MEMBER_NUMBER
    org_id: str = None,
) -> None
```

**Example -- set a user to use their direct line as ECBN:**
```python
from wxc_sdk.person_settings.ecbn import SelectedECBN

api.person_settings.ecbn.configure(
    entity_id="person_id_123",
    selected=SelectedECBN.direct_line
)
```

**Example -- set an extension-only user to use the location ECBN:**
```python
api.person_settings.ecbn.configure(
    entity_id="person_id_456",
    selected=SelectedECBN.location_ecbn
)
```

**Example -- set ECBN to another member's number (multi-floor scenario):**
```python
api.person_settings.ecbn.configure(
    entity_id="person_id_789",
    selected=SelectedECBN.location_member_number,
    location_member_id="other_person_id_on_same_floor"
)
```

#### Read ECBN Dependencies

```python
ECBNApi.dependencies(
    entity_id: str,                       # Person ID, workspace ID, or virtual line ID
    org_id: str = None,
) -> ECBNDependencies
```

Check what depends on this entity's ECBN before making changes. Returns:
- Whether this entity is the location's default ECBN
- Whether this entity uses itself as ECBN
- How many other members use this entity as their ECBN

**Example:**
```python
deps = api.person_settings.ecbn.dependencies(entity_id="person_id_123")
if deps.dependent_member_count and deps.dependent_member_count > 0:
    print(f"WARNING: {deps.dependent_member_count} other members use this person's number as ECBN")
```

### ECBN Fallback Logic

The system applies fallback rules when the configured ECBN source is unavailable:

1. If `DIRECT_LINE` is selected but the user has no valid DID, falls back to location ECBN
2. If `LOCATION_ECBN` is selected but no location ECBN is configured, falls back to the location's main number
3. If `LOCATION_MEMBER_NUMBER` is selected but the member's number is invalid, falls back to location ECBN or location main number

The `effective_level` and `effective_value` fields on the response models show which ECBN will actually be used after fallback resolution.

### Data Models

#### PersonECBN (Main Response)

```python
class PersonECBN(ApiModel):
    # The selected ECBN source
    selected: Optional[ECBNSelection]                    # DIRECT_LINE, LOCATION_ECBN, LOCATION_MEMBER_NUMBER, NONE
    # Info for the direct line option
    direct_line_info: Optional[PersonECBNDirectLine]
    # Info for the location ECBN option
    location_ecbn_info: Optional[PersonECBNDirectLine]   # Note: aliased from 'locationECBNInfo'
    # Info for the location member option
    location_member_info: Optional[ECBNLocationMember]
    # Default fallback info when nothing else is configured
    default_info: Optional[ECBNDefault]
```

#### PersonECBNDirectLine

```python
class PersonECBNDirectLine(ApiModel):
    phone_number: Optional[str]                          # The callback phone number
    first_name: Optional[str]
    last_name: Optional[str]
    effective_level: Optional[ECBNEffectiveLevel]         # What actually gets used after fallback
    effective_value: Optional[str]                        # The actual ECBN number after fallback
    quality: Optional[ECBNQuality]                       # RECOMMENDED, NOT_RECOMMENDED, or INVALID
```

#### ECBNLocationMember

```python
class ECBNLocationMember(ApiModel):
    phone_number: Optional[str]                          # Member's callback number
    first_name: Optional[str]
    last_name: Optional[str]
    member_id: Optional[str]                             # User/workspace/virtual line ID
    member_type: Optional[UserType]                      # Type of the member
    effective_level: Optional[ECBNLocationEffectiveLevel]
    effective_value: Optional[str]
    quality: Optional[ECBNQuality]
```

#### ECBNDependencies

```python
class ECBNDependencies(ApiModel):
    is_location_ecbn_default: Optional[bool]             # Is this the location's default ECBN?
    is_self_ecbn_default: Optional[bool]                 # Does this entity use itself as ECBN?
    dependent_member_count: Optional[int]                # How many others reference this entity's number
```

#### ECBNDefault

```python
class ECBNDefault(ApiModel):
    effective_value: Optional[str]                       # The fallback ECBN number
    quality: Optional[ECBNQuality]                       # RECOMMENDED, NOT_RECOMMENDED, or INVALID
```

#### Enums

```python
class ECBNSelection(str, Enum):
    direct_line = 'DIRECT_LINE'
    location_ecbn = 'LOCATION_ECBN'
    location_member_number = 'LOCATION_MEMBER_NUMBER'
    none_ = 'NONE'

class SelectedECBN(str, Enum):
    """Used in configure() -- does not include NONE"""
    direct_line = 'DIRECT_LINE'
    location_ecbn = 'LOCATION_ECBN'
    location_member_number = 'LOCATION_MEMBER_NUMBER'

class ECBNEffectiveLevel(str, Enum):
    direct_line = 'DIRECT_LINE'
    location_ecbn = 'LOCATION_ECBN'
    location_number = 'LOCATION_NUMBER'
    location_member_number = 'LOCATION_MEMBER_NUMBER'
    none_ = 'NONE'

class ECBNQuality(str, Enum):
    recommended = 'RECOMMENDED'           # Activated number on a user/workspace
    not_recommended = 'NOT_RECOMMENDED'   # Activated number on AA/HG/etc.
    invalid = 'INVALID'                   # Inactive or non-existent number
```

---

## 4. E911 Compliance Checklist

To be fully compliant with Kari's Law and RAY BAUM's Act, an organization should:

### Kari's Law (Emergency Call Notifications)

- [ ] Enable `emergency_call_notification_enabled` at the org level
- [ ] Set `allow_email_notification_all_location_enabled` to `True` (covers all locations)
- [ ] Configure `email_address` to a monitored mailbox (e.g., security, facilities)
<!-- NEEDS VERIFICATION: Whether location-level notification settings exist separately from org-level -->

### RAY BAUM's Act (Dispatchable Location)

- [ ] Every location has a validated emergency address (use `lookup_for_location` before `add_to_location`)
- [ ] Multi-building/multi-floor locations have per-number emergency addresses (use `update_for_phone_number`)
- [ ] All users with DIDs have `DIRECT_LINE` ECBN (default for users with phone numbers)
- [ ] Extension-only users have `LOCATION_ECBN` or `LOCATION_MEMBER_NUMBER` configured
- [ ] Virtual lines that can place calls have ECBN configured
- [ ] Location ECBN quality is `RECOMMENDED` (not `NOT_RECOMMENDED` or `INVALID`)
- [ ] Run `ECBNApi.dependencies()` before changing any ECBN to avoid breaking other users' callbacks

### Ongoing Maintenance

- When adding new locations: validate and add emergency address, configure location ECBN
- When adding new users: verify ECBN is correctly set (especially extension-only users)
- When moving users between locations: update both emergency address and ECBN
- When deactivating numbers: check ECBN dependencies first -- other users may reference that number

---

## Source

- SDK source: `wxc_sdk/telephony/emergency_services/__init__.py`
- SDK source: `wxc_sdk/telephony/emergency_address/__init__.py`
- SDK source: `wxc_sdk/person_settings/ecbn.py`
- SDK source: `wxc_sdk/person_settings/common.py` (ApiSelector, URL routing for ECBN)
- U.S. Public Law 115-127 (Kari's Law) -- multi-line telephone system notification requirements
- RAY BAUM's Act Section 506 -- dispatchable location requirements for 911

---

## See Also

- **[person-call-settings-behavior.md](person-call-settings-behavior.md)** — The ECBNApi is shared between person, workspace, and virtual line settings. That doc covers the same ECBN sub-API from the person-settings perspective, including how ECBN integrates with other call behavior settings.
- **[virtual-lines.md](virtual-lines.md)** — Virtual lines that can place calls need ECBN configured. The `.ecbn` sub-API is listed in the virtual line call settings table there.
