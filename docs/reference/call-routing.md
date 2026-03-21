<!-- Updated by playbook session 2026-03-18 -->
# Call Routing & PSTN Reference

## Sources
- wxc_sdk v1.30.0
- OpenAPI spec: webex-cloud-calling.json
- developer.webex.com Call Routing APIs

Comprehensive reference for Webex Calling dial plans, trunks, route groups, route lists, translation patterns, PSTN configuration, and call routing validation using the `wxc_sdk` and raw HTTP via `api.session`.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [SDK Access Paths](#sdk-access-paths)
3. [Required Scopes](#required-scopes)
4. [Dial Plans](#dial-plans)
5. [Trunks](#trunks)
6. [Route Groups](#route-groups)
7. [Route Lists](#route-lists)
8. [Translation Patterns](#translation-patterns)
9. [PSTN Configuration](#pstn-configuration)
10. [Premises PSTN](#premises-pstn)
11. [Private Network Connect (PNC)](#private-network-connect-pnc)
12. [Route Choices](#route-choices)
13. [Call Routing Test](#call-routing-test)
14. [Phone Number Management](#phone-number-management)
15. [Data Models Quick Reference](#data-models-quick-reference)
16. [Common Gotchas](#common-gotchas)

---

## Architecture Overview

Webex Calling routes outbound calls from cloud-hosted users to on-premises or PSTN destinations through a layered chain:

```
Dial Plan (pattern match)
    |
    v
Route Choice (trunk or route group)
    |
    +---> Trunk (direct) -----> Local Gateway / SBC -----> PSTN / PBX
    |
    +---> Route Group ---------> Trunk(s) with priority/failover
              |
              v
          Route List (number patterns for cloud PSTN / Dedicated Instance)
```

### How the chain works

1. **Dial Plans** are configured globally (org-wide, not per-location). Each dial plan contains one or more **dial patterns** (e.g., `+1919!`, `9XXX`) and is associated with a single **routing choice** -- either a trunk or a route group.
2. When a user dials a number, the platform matches it against all dial plan patterns. The matching dial plan's routing choice determines where the call goes.
3. A **Trunk** is a direct SIP connection between Webex Calling and an on-premises local gateway or SBC.
4. A **Route Group** bundles up to 10 trunks (from different locations) with priority-based failover.
5. A **Route List** is a list of phone numbers reachable via a route group. Route lists provide cloud PSTN connectivity to Webex Calling Dedicated Instance.
6. **Translation Patterns** manipulate dialed digits before routing (outbound calls only). They can be applied at the organization level or location level.
7. **PSTN Connection** settings at the location level determine which PSTN provider (Cisco PSTN, Cloud-Connected PSTN, or Local Gateway) handles calls for that location.

---

## SDK Access Paths

All call routing APIs are accessed through the `TelephonyApi` instance on the SDK:

```python
from wxc_sdk import WebexSimpleApi

api = WebexSimpleApi(tokens='...')

# Premises PSTN sub-APIs
api.telephony.prem_pstn.dial_plan      # DialPlanApi
api.telephony.prem_pstn.trunk          # TrunkApi
api.telephony.prem_pstn.route_group    # RouteGroupApi
api.telephony.prem_pstn.route_list     # RouteListApi

# Call routing sub-APIs
api.telephony.call_routing.tp          # TranslationPatternsApi

# PSTN location connection
api.telephony.pstn                     # PSTNApi

# Private Network Connect
api.telephony.pnc                      # PrivateNetworkConnectApi

# Top-level telephony methods
api.telephony.route_choices(...)
api.telephony.test_call_routing(...)
api.telephony.validate_phone_numbers(...)
api.telephony.phone_numbers(...)
```

### API base paths

| API Class | REST Base Path |
|-----------|---------------|
| `DialPlanApi` | `telephony/config/premisePstn/dialPlans` |
| `TrunkApi` | `telephony/config/premisePstn/trunks` |
| `RouteGroupApi` | `telephony/config/premisePstn/routeGroups` |
| `RouteListApi` | `telephony/config/premisePstn/routeLists` |
| `TranslationPatternsApi` | `telephony/config/callRouting/translationPatterns` |
| `PSTNApi` | `telephony/pstn/locations` |
| `PrivateNetworkConnectApi` | `telephony/config/locations` |
| `PremisePstnApi` (parent) | `telephony/config/premisePstn` |

---

## Required Scopes

| Operation | Scope |
|-----------|-------|
| Read dial plans, trunks, route groups, route lists, translation patterns | `spark-admin:telephony_config_read` |
| Create/update/delete dial plans, trunks, route groups, route lists, translation patterns | `spark-admin:telephony_config_write` |
| Test call routing | `spark-admin:telephony_config_write` |
| Validate phone numbers | `spark-admin:telephony_config_write` |
| Read phone numbers | `spark-admin:telephony_config_read` |
| Read PSTN location connection | `spark-admin:telephony_pstn_read` |
| Configure PSTN location connection | `spark-admin:telephony_pstn_write` |
| Read/update Private Network Connect | `spark-admin:telephony_config_read` / `spark-admin:telephony_config_write` |

---

## Dial Plans

Dial plans route calls to on-premises destinations by use of trunks or route groups. They are configured **globally for an enterprise** and apply to all users, regardless of location.

### Data Models

```python
class DialPlan(ApiModel):
    dial_plan_id: Optional[str]     # alias 'id'
    name: Optional[str]
    route_id: str                   # ID of trunk or route group
    route_name: Optional[str]
    route_type: RouteType           # 'ROUTE_GROUP' | 'TRUNK'
    customer: Optional[Customer]

class RouteType(str, Enum):
    route_group = 'ROUTE_GROUP'
    trunk = 'TRUNK'
    cisco_pstn = 'CISCO_PSTN'
    cloud_connected_pstn = 'CLOUD_CONNECTED_PSTN'

class CreateResponse(ApiModel):
    dial_plan_id: str               # alias 'id'
    dial_pattern_errors: list[DialPatternValidate]
    # .ok property: True if no errors

class PatternAndAction(ApiModel):
    dial_pattern: str
    action: PatternAction           # 'ADD' | 'DELETE'
    # helper statics: PatternAndAction.add(pattern), PatternAndAction.delete(pattern)
```

### Dial Pattern Rules

- A dial pattern is a sequence of digits (1-9), followed by optional wildcard characters.
- `!` matches any sequence of digits. Can only occur once at the end. Only valid in E.164 patterns.
- `X` matches a single digit (0-9).
- Example E.164 pattern: `+1408!` matches any number starting with +1408.
- Example short pattern: `9XXX` matches any 4-digit string starting with 9.

### API Methods

#### List Dial Plans

```python
DialPlanApi.list(
    dial_plan_name: str = None,
    route_group_name: str = None,
    trunk_name: str = None,
    order: str = None,              # sort fields: name, routeName, routeType
    org_id: str = None
) -> Generator[DialPlan, None, None]
```

#### Create Dial Plan

```python
DialPlanApi.create(
    name: str,
    route_id: str,
    route_type: RouteType,
    dial_patterns: List[str] = None,
    org_id: str = None
) -> CreateResponse
```

Returns a `CreateResponse` with the new dial plan ID and any pattern validation errors. Check `response.ok` to confirm no errors.

#### Get Dial Plan Details

```python
DialPlanApi.details(
    dial_plan_id: str,
    org_id: str = None
) -> DialPlan
```

#### Update Dial Plan

```python
DialPlanApi.update(
    update: DialPlan,               # name, route_id, route_type required
    org_id: str = None
) -> None
```

All three fields (`name`, `route_id`, `route_type`) must be set on the `update` object.

#### Delete Dial Plan

```python
DialPlanApi.delete_dial_plan(
    dial_plan_id: str,
    org_id: str = None
) -> None
```

#### List Dial Patterns

```python
DialPlanApi.patterns(
    dial_plan_id: str,
    org_id: str = None,
    dial_pattern: str = None
) -> Generator[str, None, None]
```

Returns the raw pattern strings.

#### Modify Dial Patterns (Add/Delete)

```python
DialPlanApi.modify_patterns(
    dial_plan_id: str,
    dial_patterns: List[PatternAndAction],
    org_id: str = None
) -> None
```

Patterns not present in the request are not modified. Use `PatternAndAction.add(pattern)` and `PatternAndAction.delete(pattern)` helper methods.

#### Delete All Dial Patterns

```python
DialPlanApi.delete_all_patterns(
    dial_plan_id: str,
    org_id: str = None
) -> None
```

### Validate Dial Patterns

This method is on the parent `PremisePstnApi`:

```python
PremisePstnApi.validate_pattern(
    dial_patterns: Union[str, List[str]],
    org_id: str = None
) -> DialPatternValidationResult
```

```python
class DialPatternValidationResult(ApiModel):
    status: ValidationStatus            # 'OK' | 'ERRORS'
    dial_pattern_status: list[DialPatternValidate]
    # .ok property: True if status == 'OK'

class DialPatternValidate(ApiModel):
    dial_pattern: str
    pattern_status: DialPatternStatus   # 'INVALID' | 'DUPLICATE' | 'DUPLICATE_IN_LIST'
    message: str
```

### Usage Example

```python
from wxc_sdk.common import RouteType

# Create a dial plan pointing to a trunk
response = api.telephony.prem_pstn.dial_plan.create(
    name='US-Outbound',
    route_id=trunk_id,
    route_type=RouteType.trunk,
    dial_patterns=['+1!']
)
if not response.ok:
    print(f"Pattern errors: {response.dial_pattern_errors}")

# Add patterns later
from wxc_sdk.telephony.prem_pstn.dial_plan import PatternAndAction

api.telephony.prem_pstn.dial_plan.modify_patterns(
    dial_plan_id=response.dial_plan_id,
    dial_patterns=[
        PatternAndAction.add('+44!'),
        PatternAndAction.delete('+1!')
    ]
)
```

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

All dial plan endpoints live under the `/premisePstn/` prefix -- NOT `/dialPlans` at the top level.

```python
from wxc_sdk import WebexSimpleApi
api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"

# List dial plans
plans = api.session.rest_get(f"{BASE}/telephony/config/premisePstn/dialPlans",
                             params={"max": 1000})
# plans["dialPlans"] -> list of dicts

# Create dial plan
result = api.session.rest_post(f"{BASE}/telephony/config/premisePstn/dialPlans", json={
    "name": "US-Outbound",
    "routeId": trunk_id,
    "routeType": "TRUNK",
    "dialPatterns": ["+1!"]
})
# result["id"] -> new dial plan ID

# Get dial plan details
dp = api.session.rest_get(f"{BASE}/telephony/config/premisePstn/dialPlans/{dial_plan_id}")

# Update dial plan
api.session.rest_put(f"{BASE}/telephony/config/premisePstn/dialPlans/{dial_plan_id}", json={
    "name": "US-Outbound-v2",
    "routeId": trunk_id,
    "routeType": "TRUNK"
})

# Delete dial plan
api.session.rest_delete(f"{BASE}/telephony/config/premisePstn/dialPlans/{dial_plan_id}")

# List dial patterns for a dial plan
patterns = api.session.rest_get(
    f"{BASE}/telephony/config/premisePstn/dialPlans/{dial_plan_id}/dialPatterns",
    params={"max": 1000})

# Modify dial patterns (add/delete)
api.session.rest_put(
    f"{BASE}/telephony/config/premisePstn/dialPlans/{dial_plan_id}/dialPatterns", json={
        "dialPatterns": [
            {"dialPattern": "+44!", "action": "ADD"},
            {"dialPattern": "+1!", "action": "DELETE"}
        ]
    })

# Delete all dial patterns
api.session.rest_put(
    f"{BASE}/telephony/config/premisePstn/dialPlans/{dial_plan_id}/dialPatterns", json={
        "deleteAllDialPatterns": True
    })

# Validate dial patterns
result = api.session.rest_post(
    f"{BASE}/telephony/config/premisePstn/actions/validateDialPatterns/invoke", json={
        "dialPatterns": ["+1408!", "+44!", "9XXX"]
    })
# result["status"] -> "OK" or "ERRORS"
```

**URL summary:**

| Operation | Method | URL |
|-----------|--------|-----|
| List | GET | `{BASE}/telephony/config/premisePstn/dialPlans` |
| Create | POST | `{BASE}/telephony/config/premisePstn/dialPlans` |
| Get | GET | `{BASE}/telephony/config/premisePstn/dialPlans/{id}` |
| Update | PUT | `{BASE}/telephony/config/premisePstn/dialPlans/{id}` |
| Delete | DELETE | `{BASE}/telephony/config/premisePstn/dialPlans/{id}` |
| List patterns | GET | `{BASE}/telephony/config/premisePstn/dialPlans/{id}/dialPatterns` |
| Modify patterns | PUT | `{BASE}/telephony/config/premisePstn/dialPlans/{id}/dialPatterns` |
| Validate patterns | POST | `{BASE}/telephony/config/premisePstn/actions/validateDialPatterns/invoke` |

---

## Trunks

A Trunk is a SIP connection between Webex Calling and on-premises infrastructure (local gateway or SBC). Trunks can be assigned to route groups for failover/load distribution.

### Data Models

```python
class TrunkType(str, Enum):
    registering = 'REGISTERING'         # Cisco CUBE Local Gateway
    certificate_base = 'CERTIFICATE_BASED'  # Cisco UBE, Oracle ACME SBC,
                                            # AudioCodes SBC, Ribbon SBC

class Trunk(ApiModel):
    trunk_id: str                       # alias 'id'
    name: str
    location: IdAndName
    in_use: bool
    trunk_type: TrunkType
    is_restricted_to_dedicated_instance: bool

class TrunkDetail(ApiModel):
    trunk_id: str                       # alias 'id'
    name: str
    organization: Customer
    location: IdAndName
    otg_dtg_id: str                     # outgoing/destination trunk group ID
    line_port: str                      # device endpoint / SIP URI
    locations_using_trunk: list[IdAndName]
    pilot_user_id: str
    outbound_proxy: Any
    sip_authentication_user_name: str
    status: DeviceStatus                # 'online' | 'offline' | 'unknown'
    error_codes: list[str]
    response_status: list[ResponseStatus]
    dual_identity_support_enabled: bool
    trunk_type: TrunkType
    device_type: str
    address: Optional[str]              # FQDN/SRV -- certificate-based only
    domain: Optional[str]               # certificate-based only
    port: Optional[int]                 # certificate-based only
    max_concurrent_calls: int
    is_restricted_to_dedicated_instance: Optional[bool]
    p_charge_info_support_policy: Optional[PChargeInfoSupportPolicy]

class TrunkDeviceType(ApiModel):
    device_type: str
    min_concurrent_calls: int
    max_concurrent_calls: int

class TrunkTypeWithDeviceType(ApiModel):
    trunk_type: TrunkType
    device_types: list[TrunkDeviceType]

class DeviceStatus(str, Enum):
    online = 'online'
    offline = 'offline'
    unknown = 'unknown'

class PChargeInfoSupportPolicy(str, Enum):
    disabled = 'DISABLED'
    asserted_identity = 'ASSERTED_IDENTITY'
    configurable_charge_number = 'CONFIGURABLE_CHARGE_NUMBER'

class TrunkUsage(ApiModel):
    pstn_connection_count: int
    call_to_extension_count: int
    dial_plan_count: int
    route_group_count: int
```

### Trunk Types

| Type | Value | Use Case |
|------|-------|----------|
| Registering | `REGISTERING` | Cisco CUBE Local Gateway. Registers with Webex Calling cloud. Requires password. |
| Certificate-based | `CERTIFICATE_BASED` | Cisco UBE, Oracle ACME SBC, AudioCodes SBC, Ribbon SBC. Uses mutual TLS. Requires FQDN/SRV address, domain, port, and max concurrent calls. |

### Dual Identity Support

The `dual_identity_support_enabled` setting controls the From and P-Asserted-Identity (PAI) headers on outbound SIP INVITEs sent to the trunk. When enabled, the From header may differ from the PAI, allowing the called party to see the user's identity while the trunk authenticates with a different identity.

### P-Charge-Info Support Policy

Controls the P-Charge-Info header on outbound PSTN calls:

- **DISABLED**: No P-Charge-Info header sent.
- **ASSERTED_IDENTITY**: Always uses the Webex Calling primary number or the location's main number.
- **CONFIGURABLE_CHARGE_NUMBER**: Uses the originating entity's location charge number if set, else the entity's primary number (non-toll-free), else the location main number (non-toll-free), else falls back to ASSERTED_IDENTITY behavior.

### API Methods

#### List Trunks

```python
TrunkApi.list(
    name: str = None,
    location_name: str = None,
    trunk_type: str = None,
    order: str = None,              # sort fields: name, locationName
    org_id: str = None
) -> Generator[Trunk, None, None]
```

#### Create Trunk

```python
TrunkApi.create(
    name: str,
    location_id: str,
    password: str,
    trunk_type: TrunkType = TrunkType.registering,
    dual_identity_support_enabled: bool = None,
    device_type: TrunkDeviceType = None,
    address: str = None,            # FQDN/SRV -- required for certificate-based
    domain: str = None,             # required for certificate-based
    port: int = None,               # required for certificate-based
    max_concurrent_calls: int = None,  # required for certificate-based
    p_charge_info_support_policy: PChargeInfoSupportPolicy = None,
    org_id: str = None
) -> str                            # returns new trunk ID
```

#### Get Trunk Details

```python
TrunkApi.details(
    trunk_id: str,
    org_id: str = None
) -> TrunkDetail
```

#### Update Trunk

```python
TrunkApi.update(
    trunk_id: str,
    name: str,
    password: str,
    dual_identity_support_enabled: bool = None,
    max_concurrent_calls: int = None,
    p_charge_info_support_policy: PChargeInfoSupportPolicy = None,
    org_id: str = None
) -> None
```

Note: `name` and `password` are always required for updates.

**Limitation**: You cannot change `trunk_type`, `location_id`, or `device_type` after creation. To change these properties, you must delete and recreate the trunk.

#### Delete Trunk

```python
TrunkApi.delete_trunk(
    trunk_id: str,
    org_id: str = None
) -> None
```

#### List Trunk Types with Device Types

```python
TrunkApi.trunk_types(
    org_id: str = None
) -> List[TrunkTypeWithDeviceType]
```

Returns the available trunk types and their supported device types (with min/max concurrent call limits).

#### Validate FQDN and Domain

```python
TrunkApi.validate_fqdn_and_domain(
    address: str,
    domain: str,
    port: int = None,
    org_id: str = None
) -> None
```

Validates the FQDN/SRV address and domain before creating a certificate-based trunk. Raises an exception on validation failure.

#### Get Trunk Usage

```python
TrunkApi.usage(
    trunk_id: str,
    org_id: str = None
) -> TrunkUsage
```

Returns counts of PSTN connections, call-to-extension locations, dial plans, and route groups using this trunk.

#### Trunk Usage Detail Methods

```python
TrunkApi.usage_call_to_extension(trunk_id, order=None, name=None, org_id=None) -> Generator[IdAndName]
TrunkApi.usage_dial_plan(trunk_id, order=None, name=None, org_id=None) -> Generator[IdAndName]
TrunkApi.usage_location_pstn(trunk_id, org_id=None) -> Generator[IdAndName]
TrunkApi.usage_route_group(trunk_id, org_id=None) -> Generator[IdAndName]
```

### Usage Example

```python
from wxc_sdk.telephony.prem_pstn.trunk import TrunkType

# Create a registering trunk
trunk_id = api.telephony.prem_pstn.trunk.create(
    name='HQ-LGW-01',
    location_id=location_id,
    password='SecurePass123!',
    trunk_type=TrunkType.registering
)

# Check trunk status
detail = api.telephony.prem_pstn.trunk.details(trunk_id=trunk_id)
print(f"Status: {detail.status}")           # online / offline / unknown
print(f"SIP User: {detail.sip_authentication_user_name}")
print(f"Line/Port: {detail.line_port}")
print(f"OTG/DTG: {detail.otg_dtg_id}")
```

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

All trunk endpoints live under the `/premisePstn/trunks` prefix.

```python
BASE = "https://webexapis.com/v1"

# List trunks
trunks = api.session.rest_get(f"{BASE}/telephony/config/premisePstn/trunks",
                              params={"max": 1000})
# trunks["trunks"] -> list of dicts

# Create trunk (registering type)
result = api.session.rest_post(f"{BASE}/telephony/config/premisePstn/trunks", json={
    "name": "HQ-LGW-01",
    "locationId": location_id,
    "password": "SecurePass123!",
    "trunkType": "REGISTERING"
})
# result["id"] -> new trunk ID

# Create trunk (certificate-based)
result = api.session.rest_post(f"{BASE}/telephony/config/premisePstn/trunks", json={
    "name": "HQ-SBC-01",
    "locationId": location_id,
    "password": "SecurePass123!",
    "trunkType": "CERTIFICATE_BASED",
    "address": "sbc.example.com",
    "domain": "example.com",
    "port": 5061,
    "maxConcurrentCalls": 100
})

# Get trunk details
detail = api.session.rest_get(f"{BASE}/telephony/config/premisePstn/trunks/{trunk_id}")

# Update trunk (name + password always required)
api.session.rest_put(f"{BASE}/telephony/config/premisePstn/trunks/{trunk_id}", json={
    "name": "HQ-LGW-01-v2",
    "password": "NewPass456!"
})

# Delete trunk
api.session.rest_delete(f"{BASE}/telephony/config/premisePstn/trunks/{trunk_id}")

# List trunk types with device types
types = api.session.rest_get(f"{BASE}/telephony/config/premisePstn/trunks/trunkTypes")
# types["trunkTypes"] -> list of dicts

# Validate FQDN and domain (certificate-based)
api.session.rest_post(
    f"{BASE}/telephony/config/premisePstn/trunks/actions/fqdnValidation/invoke", json={
        "address": "sbc.example.com",
        "domain": "example.com",
        "port": 5061
    })

# Trunk usage count
usage = api.session.rest_get(f"{BASE}/telephony/config/premisePstn/trunks/{trunk_id}/usage")

# Trunk usage details
api.session.rest_get(f"{BASE}/telephony/config/premisePstn/trunks/{trunk_id}/usageDialPlan")
api.session.rest_get(f"{BASE}/telephony/config/premisePstn/trunks/{trunk_id}/usagePstnConnection")
api.session.rest_get(f"{BASE}/telephony/config/premisePstn/trunks/{trunk_id}/usageRouteGroup")
api.session.rest_get(f"{BASE}/telephony/config/premisePstn/trunks/{trunk_id}/usageCallToExtension")
```

**URL summary:**

| Operation | Method | URL |
|-----------|--------|-----|
| List | GET | `{BASE}/telephony/config/premisePstn/trunks` |
| Create | POST | `{BASE}/telephony/config/premisePstn/trunks` |
| Get | GET | `{BASE}/telephony/config/premisePstn/trunks/{id}` |
| Update | PUT | `{BASE}/telephony/config/premisePstn/trunks/{id}` |
| Delete | DELETE | `{BASE}/telephony/config/premisePstn/trunks/{id}` |
| List types | GET | `{BASE}/telephony/config/premisePstn/trunks/trunkTypes` |
| Validate FQDN | POST | `{BASE}/telephony/config/premisePstn/trunks/actions/fqdnValidation/invoke` |
| Usage count | GET | `{BASE}/telephony/config/premisePstn/trunks/{id}/usage` |
| Usage dial plan | GET | `{BASE}/telephony/config/premisePstn/trunks/{id}/usageDialPlan` |
| Usage PSTN | GET | `{BASE}/telephony/config/premisePstn/trunks/{id}/usagePstnConnection` |
| Usage route group | GET | `{BASE}/telephony/config/premisePstn/trunks/{id}/usageRouteGroup` |
| Usage call-to-ext | GET | `{BASE}/telephony/config/premisePstn/trunks/{id}/usageCallToExtension` |

---

## Route Groups

A Route Group is a collection of trunks (up to 10, from different locations) that enables failover and load distribution for on-premises call routing.

### Data Models

```python
class RGTrunk(ApiModel):
    trunk_id: str                       # alias 'id'
    name: Optional[str]
    location_id: Optional[str]
    priority: int

class RouteGroup(ApiModel):
    rg_id: Optional[str]               # alias 'id' -- only in list(), not detail()
    name: str
    in_use: Optional[bool]             # only in list()
    organization: Optional[Customer]   # only in detail()
    local_gateways: Optional[list[RGTrunk]]  # only in detail()

class RouteGroupUsage(ApiModel):
    pstn_connection_count: int
    call_to_extension_count: int
    dial_plan_count: int
    route_list_count: int

class UsageRouteLists(ApiModel):
    rl_id: str                          # alias 'id'
    rl_name: str                        # alias 'name'
    location_id: str
    location_name: str
```

### API Methods

#### List Route Groups

```python
RouteGroupApi.list(
    name: str = None,
    order: str = None,              # sort orders: asc, desc
    org_id: str = None
) -> Generator[RouteGroup, None, None]
```

#### Create Route Group

```python
RouteGroupApi.create(
    route_group: RouteGroup,
    org_id: str = None
) -> str                            # returns new route group ID
```

The `RouteGroup` object must have `name` and `local_gateways` set. Each `RGTrunk` in `local_gateways` must have `trunk_id` and `priority` set.

#### Get Route Group Details

```python
RouteGroupApi.details(
    rg_id: str,
    org_id: str = None
) -> RouteGroup
```

Returns the route group with `organization` and `local_gateways` populated.

#### Update Route Group

```python
RouteGroupApi.update(
    rg_id: str,
    update: RouteGroup,
    org_id: str = None
) -> None
```

#### Delete Route Group

```python
RouteGroupApi.delete_route_group(
    rg_id: str,
    org_id: str = None
) -> None
```

#### Get Route Group Usage

```python
RouteGroupApi.usage(
    rg_id: str,
    org_id: str = None
) -> RouteGroupUsage
```

#### Route Group Usage Detail Methods

```python
RouteGroupApi.usage_call_to_extension(rg_id, location_name=None, order=None, org_id=None) -> Generator[IdAndName]
RouteGroupApi.usage_dial_plan(rg_id, location_name=None, order=None, org_id=None) -> Generator[IdAndName]
RouteGroupApi.usage_location_pstn(rg_id, location_name=None, order=None, org_id=None) -> Generator[IdAndName]
RouteGroupApi.usage_route_lists(rg_id, name=None, order=None, org_id=None) -> Generator[UsageRouteLists]
```

### Usage Example

```python
from wxc_sdk.telephony.prem_pstn.route_group import RouteGroup, RGTrunk

# Create a route group with two trunks (priority-based failover)
rg = RouteGroup(
    name='US-East-RG',
    local_gateways=[
        RGTrunk(trunk_id=primary_trunk_id, priority=1),
        RGTrunk(trunk_id=backup_trunk_id, priority=2)
    ]
)
rg_id = api.telephony.prem_pstn.route_group.create(route_group=rg)

# Check what's using this route group
usage = api.telephony.prem_pstn.route_group.usage(rg_id=rg_id)
print(f"Dial plans: {usage.dial_plan_count}, Route lists: {usage.route_list_count}")
```

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

All route group endpoints live under the `/premisePstn/routeGroups` prefix.

```python
BASE = "https://webexapis.com/v1"

# List route groups
groups = api.session.rest_get(f"{BASE}/telephony/config/premisePstn/routeGroups",
                              params={"max": 1000})
# groups["routeGroups"] -> list of dicts

# Create route group
result = api.session.rest_post(f"{BASE}/telephony/config/premisePstn/routeGroups", json={
    "name": "US-East-RG",
    "localGateways": [
        {"trunkId": primary_trunk_id, "priority": 1},
        {"trunkId": backup_trunk_id, "priority": 2}
    ]
})
# result["id"] -> new route group ID

# Get route group details
rg = api.session.rest_get(f"{BASE}/telephony/config/premisePstn/routeGroups/{rg_id}")

# Update route group
api.session.rest_put(f"{BASE}/telephony/config/premisePstn/routeGroups/{rg_id}", json={
    "name": "US-East-RG-v2",
    "localGateways": [
        {"trunkId": primary_trunk_id, "priority": 1}
    ]
})

# Delete route group
api.session.rest_delete(f"{BASE}/telephony/config/premisePstn/routeGroups/{rg_id}")

# Route group usage count
usage = api.session.rest_get(
    f"{BASE}/telephony/config/premisePstn/routeGroups/{rg_id}/usage")

# Route group usage details
api.session.rest_get(f"{BASE}/telephony/config/premisePstn/routeGroups/{rg_id}/usageCallToExtension")
api.session.rest_get(f"{BASE}/telephony/config/premisePstn/routeGroups/{rg_id}/usageDialPlan")
api.session.rest_get(f"{BASE}/telephony/config/premisePstn/routeGroups/{rg_id}/usagePstnConnection")
api.session.rest_get(f"{BASE}/telephony/config/premisePstn/routeGroups/{rg_id}/usageRouteList")
```

**URL summary:**

| Operation | Method | URL |
|-----------|--------|-----|
| List | GET | `{BASE}/telephony/config/premisePstn/routeGroups` |
| Create | POST | `{BASE}/telephony/config/premisePstn/routeGroups` |
| Get | GET | `{BASE}/telephony/config/premisePstn/routeGroups/{id}` |
| Update | PUT | `{BASE}/telephony/config/premisePstn/routeGroups/{id}` |
| Delete | DELETE | `{BASE}/telephony/config/premisePstn/routeGroups/{id}` |
| Usage count | GET | `{BASE}/telephony/config/premisePstn/routeGroups/{id}/usage` |
| Usage call-to-ext | GET | `{BASE}/telephony/config/premisePstn/routeGroups/{id}/usageCallToExtension` |
| Usage dial plan | GET | `{BASE}/telephony/config/premisePstn/routeGroups/{id}/usageDialPlan` |
| Usage PSTN | GET | `{BASE}/telephony/config/premisePstn/routeGroups/{id}/usagePstnConnection` |
| Usage route list | GET | `{BASE}/telephony/config/premisePstn/routeGroups/{id}/usageRouteList` |

---

## Route Lists

A Route List is a list of phone numbers that can be reached via a Route Group. Route lists are used to provide cloud PSTN connectivity to Webex Calling Dedicated Instance.

### Data Models

```python
class RouteListDetail(ApiModel):
    rl_id: str                          # alias 'id'
    name: str
    location: IdAndName
    route_group: IdAndName

class RouteList(ApiModel):
    rl_id: str                          # alias 'id'
    name: str
    location_id: str
    location_name: str
    rg_id: str                          # alias 'routeGroupId'
    rg_name: str                        # alias 'routeGroupName'
    peak_active_route_list_calls_org: Optional[int]
    current_active_route_list_calls_org: Optional[int]
    route_list_calls_volume_org: Optional[int]
    peak_active_route_list_calls: Optional[int]
    current_active_route_list_calls: Optional[int]

class NumberAndAction(ApiModel):
    number: str
    action: PatternAction               # 'ADD' | 'DELETE'
    # helper statics: NumberAndAction.add(number), NumberAndAction.delete(number)

class UpdateNumbersResponse(ApiModel):
    number: str
    number_status: str
    message: str
```

### API Methods

#### List Route Lists

```python
RouteListApi.list(
    name: list[str] = None,
    location_id: list[str] = None,
    order: str = None,              # sort fields: name, locationId
    org_id: str = None
) -> Generator[RouteList, None, None]
```

Note: `name` and `location_id` accept lists for multi-value filtering.

#### Create Route List

```python
RouteListApi.create(
    name: str,
    location_id: str,
    rg_id: str,                     # route group ID
    org_id: str = None
) -> str                            # returns new route list ID
```

#### Get Route List Details

```python
RouteListApi.details(
    rl_id: str,
    org_id: str = None
) -> RouteListDetail
```

#### Update Route List

```python
RouteListApi.update(
    rl_id: str,
    name: str = None,
    rg_id: str = None,
    org_id: str = None
) -> None
```

#### Delete Route List

```python
RouteListApi.delete_route_list(
    rl_id: str,
    org_id: str = None
) -> None
```

#### List Numbers on a Route List

```python
RouteListApi.numbers(
    rl_id: str,
    order: str = None,
    number: str = None,
    org_id: str = None
) -> Generator[str, None, None]
```

#### Modify Numbers on a Route List (Add/Delete)

```python
RouteListApi.update_numbers(
    rl_id: str,
    numbers: List[NumberAndAction] = None,
    delete_all_numbers: bool = None,
    org_id: str = None
) -> List[UpdateNumbersResponse]
```

If `delete_all_numbers` is set, the `numbers` array is ignored and all numbers are removed.

#### Delete All Numbers from a Route List

```python
RouteListApi.delete_all_numbers(
    rl_id: str,
    org_id: str = None
) -> None
```

### Usage Example

```python
from wxc_sdk.telephony.prem_pstn.route_list import NumberAndAction

# Create route list
rl_id = api.telephony.prem_pstn.route_list.create(
    name='US-East-Numbers',
    location_id=location_id,
    rg_id=rg_id
)

# Add numbers
result = api.telephony.prem_pstn.route_list.update_numbers(
    rl_id=rl_id,
    numbers=[
        NumberAndAction.add('+19195551234'),
        NumberAndAction.add('+19195555678')
    ]
)
for r in result:
    print(f"{r.number}: {r.number_status} - {r.message}")
```

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

All route list endpoints live under the `/premisePstn/routeLists` prefix.

```python
BASE = "https://webexapis.com/v1"

# List route lists
lists = api.session.rest_get(f"{BASE}/telephony/config/premisePstn/routeLists",
                             params={"max": 1000})
# lists["routeLists"] -> list of dicts

# Create route list
result = api.session.rest_post(f"{BASE}/telephony/config/premisePstn/routeLists", json={
    "name": "US-East-Numbers",
    "locationId": location_id,
    "routeGroupId": rg_id
})
# result["id"] -> new route list ID

# Get route list details
rl = api.session.rest_get(f"{BASE}/telephony/config/premisePstn/routeLists/{rl_id}")

# Update route list
api.session.rest_put(f"{BASE}/telephony/config/premisePstn/routeLists/{rl_id}", json={
    "name": "US-East-Numbers-v2",
    "routeGroupId": new_rg_id
})

# Delete route list
api.session.rest_delete(f"{BASE}/telephony/config/premisePstn/routeLists/{rl_id}")

# List numbers on route list
nums = api.session.rest_get(
    f"{BASE}/telephony/config/premisePstn/routeLists/{rl_id}/numbers",
    params={"max": 1000})
# nums["numbers"] -> list of dicts

# Modify numbers on route list (add/delete)
api.session.rest_put(
    f"{BASE}/telephony/config/premisePstn/routeLists/{rl_id}/numbers", json={
        "numbers": [
            {"number": "+19195551234", "action": "ADD"},
            {"number": "+19195555678", "action": "ADD"}
        ]
    })

# Delete all numbers from route list
api.session.rest_put(
    f"{BASE}/telephony/config/premisePstn/routeLists/{rl_id}/numbers", json={
        "deleteAllNumbers": True
    })
```

**URL summary:**

| Operation | Method | URL |
|-----------|--------|-----|
| List | GET | `{BASE}/telephony/config/premisePstn/routeLists` |
| Create | POST | `{BASE}/telephony/config/premisePstn/routeLists` |
| Get | GET | `{BASE}/telephony/config/premisePstn/routeLists/{id}` |
| Update | PUT | `{BASE}/telephony/config/premisePstn/routeLists/{id}` |
| Delete | DELETE | `{BASE}/telephony/config/premisePstn/routeLists/{id}` |
| List numbers | GET | `{BASE}/telephony/config/premisePstn/routeLists/{id}/numbers` |
| Modify numbers | PUT | `{BASE}/telephony/config/premisePstn/routeLists/{id}/numbers` |

---

## Translation Patterns

Translation patterns manipulate dialed digits before routing a call. They apply to **outbound calls only**. Patterns can be configured at the **organization level** or the **location level**.

### Data Models

```python
class TranslationPatternLevel(str, Enum):
    location = 'Location'
    organization = 'Organization'

class TranslationPattern(ApiModel):
    id: Optional[str]
    name: Optional[str]
    matching_pattern: Optional[str]
    replacement_pattern: Optional[str]
    level: Optional[TranslationPatternLevel]
    location: Optional[IdAndName]
```

### API Methods

#### List Translation Patterns

```python
TranslationPatternsApi.list(
    limit_to_location_id: str = None,       # filter to specific location
    limit_to_org_level_enabled: bool = None, # filter to org-level only
    order: str = None,
    name: str = None,
    matching_pattern: str = None,
    org_id: str = None
) -> Generator[TranslationPattern, None, None]
```

#### Create Translation Pattern

```python
TranslationPatternsApi.create(
    pattern: TranslationPattern,
    location_id: str = None,        # omit for org-level, set for location-level
    org_id: str = None
) -> str                            # returns new pattern ID
```

The `TranslationPattern` must have `name`, `matching_pattern`, and `replacement_pattern` set. The `id`, `level`, and `location` fields are excluded from the create payload.

#### Get Translation Pattern Details

```python
TranslationPatternsApi.details(
    translation_id: str,
    location_id: str = None,
    org_id: str = None
) -> TranslationPattern
```

#### Update Translation Pattern

```python
TranslationPatternsApi.update(
    pattern: TranslationPattern,    # must have .id set
    location_id: str = None,
    org_id: str = None
) -> None
```

#### Delete Translation Pattern

```python
TranslationPatternsApi.delete(
    translation_id: str,
    location_id: str = None,
    org_id: str = None
) -> None
```

### Endpoint Routing

- **Org-level**: `telephony/config/callRouting/translationPatterns`
- **Location-level**: `telephony/config/locations/{location_id}/callRouting/translationPatterns`

### Usage Example

```python
from wxc_sdk.telephony.call_routing.translation_pattern import TranslationPattern

# Create an org-level translation pattern
# Strips leading '9' from 4-digit extensions before routing
pattern = TranslationPattern(
    name='Strip-9-Prefix',
    matching_pattern='9XXX',
    replacement_pattern='XXX'
)
tp_id = api.telephony.call_routing.tp.create(pattern=pattern)

# Create a location-level translation pattern
pattern_loc = TranslationPattern(
    name='Local-Rewrite',
    matching_pattern='+1919555XXXX',
    replacement_pattern='555XXXX'
)
tp_id_loc = api.telephony.call_routing.tp.create(
    pattern=pattern_loc,
    location_id=location_id
)
```

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

Translation patterns use the `/callRouting/` prefix (NOT `/premisePstn/`). Org-level and location-level have different URL paths.

```python
BASE = "https://webexapis.com/v1"

# --- Org-level translation patterns ---

# List org-level translation patterns
tps = api.session.rest_get(
    f"{BASE}/telephony/config/callRouting/translationPatterns",
    params={"max": 1000})
# tps["translationPatterns"] -> list of dicts

# Create org-level translation pattern
result = api.session.rest_post(
    f"{BASE}/telephony/config/callRouting/translationPatterns", json={
        "name": "Strip-9-Prefix",
        "matchingPattern": "9XXX",
        "replacementPattern": "XXX"
    })
# result["id"] -> new pattern ID

# Get org-level translation pattern
tp = api.session.rest_get(
    f"{BASE}/telephony/config/callRouting/translationPatterns/{translation_id}")

# Update org-level translation pattern
api.session.rest_put(
    f"{BASE}/telephony/config/callRouting/translationPatterns/{translation_id}", json={
        "name": "Strip-9-Prefix-v2",
        "matchingPattern": "9XXX",
        "replacementPattern": "XXX"
    })

# Delete org-level translation pattern
api.session.rest_delete(
    f"{BASE}/telephony/config/callRouting/translationPatterns/{translation_id}")

# --- Location-level translation patterns ---

# Create location-level translation pattern
result = api.session.rest_post(
    f"{BASE}/telephony/config/locations/{location_id}/callRouting/translationPatterns", json={
        "name": "Local-Rewrite",
        "matchingPattern": "+1919555XXXX",
        "replacementPattern": "+19196660000"
    })

# Get/update/delete location-level: same pattern with /locations/{location_id}/ prefix
api.session.rest_get(
    f"{BASE}/telephony/config/locations/{location_id}/callRouting/translationPatterns/{translation_id}")
api.session.rest_put(
    f"{BASE}/telephony/config/locations/{location_id}/callRouting/translationPatterns/{translation_id}",
    json={...})
api.session.rest_delete(
    f"{BASE}/telephony/config/locations/{location_id}/callRouting/translationPatterns/{translation_id}")
```

**URL summary:**

| Operation | Method | URL |
|-----------|--------|-----|
| List (org) | GET | `{BASE}/telephony/config/callRouting/translationPatterns` |
| Create (org) | POST | `{BASE}/telephony/config/callRouting/translationPatterns` |
| Get (org) | GET | `{BASE}/telephony/config/callRouting/translationPatterns/{id}` |
| Update (org) | PUT | `{BASE}/telephony/config/callRouting/translationPatterns/{id}` |
| Delete (org) | DELETE | `{BASE}/telephony/config/callRouting/translationPatterns/{id}` |
| List (location) | GET | `{BASE}/telephony/config/locations/{locId}/callRouting/translationPatterns` |
| Create (location) | POST | `{BASE}/telephony/config/locations/{locId}/callRouting/translationPatterns` |
| Get (location) | GET | `{BASE}/telephony/config/locations/{locId}/callRouting/translationPatterns/{id}` |
| Update (location) | PUT | `{BASE}/telephony/config/locations/{locId}/callRouting/translationPatterns/{id}` |
| Delete (location) | DELETE | `{BASE}/telephony/config/locations/{locId}/callRouting/translationPatterns/{id}` |

---

## PSTN Configuration

The PSTN API manages the PSTN connection settings for a location -- which provider handles calls and how it connects.

### Data Models

```python
class PSTNType(str, Enum):
    local_gateway = 'LOCAL_GATEWAY'             # Premises-based PSTN
    non_integrated_ccp = 'NON_INTEGRATED_CCP'   # Non-Integrated Cloud Connected PSTN
    integrated_ccp = 'INTEGRATED_CCP'           # Integrated CCP (not API-configurable)
    cisco_pstn = 'CISCO_PSTN'                   # Cisco PSTN (not API-configurable)

class PSTNServiceType(str, Enum):
    geographic_numbers = 'GEOGRAPHIC_NUMBERS'
    tollfree_numbers = 'TOLLFREE_NUMBERS'
    business_texting = 'BUSINESS_TEXTING'
    contact_center = 'CONTACT_CENTER'
    service_numbers = 'SERVICE_NUMBERS'
    non_geographic_numbers = 'NON_GEOGRAPHIC_NUMBERS'
    mobile_numbers = 'MOBILE_NUMBERS'

class PSTNConnectionOption(ApiModel):
    id: Optional[str]
    display_name: Optional[str]
    pstn_services: Optional[list[PSTNServiceType]]
    pstn_connection_type: Optional[PSTNType]
    route_type: Optional[RouteType]         # required if LOCAL_GATEWAY
    route_id: Optional[str]                 # trunk ID or route group ID
```

### API Methods

#### List PSTN Connection Options for a Location

```python
PSTNApi.list(
    location_id: str,
    service_types: list[PSTNServiceType] = None,
    org_id: str = None
) -> list[PSTNConnectionOption]
```

Returns all available PSTN connection options for the given location.

#### Configure PSTN Connection for a Location

```python
PSTNApi.configure(
    location_id: str,
    id: str = None,                     # connection ID -- required for non-integrated CCP
    premise_route_type: str = None,     # 'TRUNK' or 'ROUTE_GROUP' -- required for local gateway
    premise_route_id: str = None,       # trunk or route group ID -- required for local gateway
    org_id: str = None
) -> None
```

**Important**: Only `LOCAL_GATEWAY` and `NON_INTEGRATED_CCP` types can be configured via the API. `INTEGRATED_CCP` and `CISCO_PSTN` must be configured through the Control Hub UI.

#### Read Current PSTN Connection for a Location

```python
PSTNApi.read(
    location_id: str,
    org_id: str = None
) -> PSTNConnectionOption
```

### Usage Example

```python
# Set a location to use a local gateway trunk for PSTN
api.telephony.pstn.configure(
    location_id=location_id,
    premise_route_type='TRUNK',
    premise_route_id=trunk_id
)

# Or use a route group
api.telephony.pstn.configure(
    location_id=location_id,
    premise_route_type='ROUTE_GROUP',
    premise_route_id=rg_id
)

# Read current configuration
current = api.telephony.pstn.read(location_id=location_id)
print(f"Connection: {current.pstn_connection_type}")
print(f"Route: {current.route_type} -> {current.route_id}")
```

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

PSTN endpoints use the `/telephony/pstn/` prefix (NOT `/premisePstn/` and NOT `/telephony/config/`).

```python
BASE = "https://webexapis.com/v1"

# List PSTN connection options for a location
options = api.session.rest_get(
    f"{BASE}/telephony/pstn/locations/{location_id}/connectionOptions",
    params={"max": 1000})
# options["connectionOptions"] -> list of dicts

# Read current PSTN connection for a location
conn = api.session.rest_get(
    f"{BASE}/telephony/pstn/locations/{location_id}/connection")

# Setup/update PSTN connection for a location (local gateway)
api.session.rest_put(
    f"{BASE}/telephony/pstn/locations/{location_id}/connection", json={
        "premiseRouteType": "TRUNK",
        "premiseRouteId": trunk_id
    })

# Setup/update PSTN connection (non-integrated CCP)
api.session.rest_put(
    f"{BASE}/telephony/pstn/locations/{location_id}/connection", json={
        "id": ccp_provider_id
    })

# Emergency address lookup
result = api.session.rest_post(
    f"{BASE}/telephony/pstn/locations/{location_id}/emergencyAddress/lookup", json={
        "address1": "123 Main St",
        "city": "Raleigh",
        "state": "NC",
        "postalCode": "27601",
        "country": "US"
    })

# Add emergency address to location
api.session.rest_post(
    f"{BASE}/telephony/pstn/locations/{location_id}/emergencyAddress", json={
        "address1": "123 Main St",
        "city": "Raleigh",
        "state": "NC",
        "postalCode": "27601",
        "country": "US"
    })

# Update emergency address for a phone number
api.session.rest_put(
    f"{BASE}/telephony/pstn/numbers/{phone_number}/emergencyAddress", json={...})
```

**URL summary:**

| Operation | Method | URL |
|-----------|--------|-----|
| List connection options | GET | `{BASE}/telephony/pstn/locations/{locId}/connectionOptions` |
| Read connection | GET | `{BASE}/telephony/pstn/locations/{locId}/connection` |
| Setup connection | PUT | `{BASE}/telephony/pstn/locations/{locId}/connection` |
| Emergency lookup | POST | `{BASE}/telephony/pstn/locations/{locId}/emergencyAddress/lookup` |
| Add emergency addr | POST | `{BASE}/telephony/pstn/locations/{locId}/emergencyAddress` |
| Update emergency addr (location) | PUT | `{BASE}/telephony/pstn/locations/{locId}/emergencyAddresses/{addrId}` |
| Update emergency addr (number) | PUT | `{BASE}/telephony/pstn/numbers/{phoneNumber}/emergencyAddress` |

---

## Premises PSTN

The `PremisePstnApi` is the parent API that groups all premises-based PSTN sub-APIs and provides the `validate_pattern()` method.

### SDK Access

```python
api.telephony.prem_pstn                 # PremisePstnApi
api.telephony.prem_pstn.dial_plan       # DialPlanApi
api.telephony.prem_pstn.trunk           # TrunkApi
api.telephony.prem_pstn.route_group     # RouteGroupApi
api.telephony.prem_pstn.route_list      # RouteListApi
```

### Validate Dial Pattern

```python
PremisePstnApi.validate_pattern(
    dial_patterns: Union[str, List[str]],
    org_id: str = None
) -> DialPatternValidationResult
```

Accepts a single pattern string or a list. Returns validation status and per-pattern details.

```python
result = api.telephony.prem_pstn.validate_pattern(['+1408!', '+44!', '9XXX'])
if result.ok:
    print("All patterns valid")
else:
    for p in result.dial_pattern_status:
        print(f"{p.dial_pattern}: {p.pattern_status} - {p.message}")
```

---

## Private Network Connect (PNC)

Private Network Connect determines whether a location uses the public internet or a private network for its connection to Webex Calling.

### Data Models

```python
class NetworkConnectionType(str, Enum):
    public_internet = 'PUBLIC_INTERNET'
    private_network = 'PRIVATE_NETWORK'
```

### API Methods

#### Read PNC Setting

```python
PrivateNetworkConnectApi.read(
    location_id: str,
    org_id: str = None
) -> NetworkConnectionType
```

#### Update PNC Setting

```python
PrivateNetworkConnectApi.update(
    location_id: str,
    connection_type: NetworkConnectionType,
    org_id: str = None
) -> None
```

### Endpoint

Both methods use: `telephony/config/locations/{location_id}/privateNetworkConnect`

### Usage Example

```python
from wxc_sdk.telephony.pnc import NetworkConnectionType

# Read current setting
pnc = api.telephony.pnc.read(location_id=location_id)
print(f"Connection type: {pnc}")

# Switch to private network
api.telephony.pnc.update(
    location_id=location_id,
    connection_type=NetworkConnectionType.private_network
)
```

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

```python
BASE = "https://webexapis.com/v1"

# Read PNC setting for a location
pnc = api.session.rest_get(
    f"{BASE}/telephony/config/locations/{location_id}/privateNetworkConnect")
# pnc["networkConnectionType"] -> "PUBLIC_INTERNET" or "PRIVATE_NETWORK"

# Update PNC setting
api.session.rest_put(
    f"{BASE}/telephony/config/locations/{location_id}/privateNetworkConnect", json={
        "networkConnectionType": "PRIVATE_NETWORK"
    })
```

| Operation | Method | URL |
|-----------|--------|-----|
| Read PNC | GET | `{BASE}/telephony/config/locations/{locId}/privateNetworkConnect` |
| Update PNC | PUT | `{BASE}/telephony/config/locations/{locId}/privateNetworkConnect` |

---

## Route Choices

The `route_choices()` method lists all available routing targets (trunks and route groups) for the organization. This is useful when building dial plans or configuring PSTN connections and you need to enumerate what routes are available.

### Data Model

```python
class RouteIdentity(ApiModel):
    route_id: str                       # alias 'id'
    name: Optional[str]
    route_type: RouteType               # alias 'type' -- 'ROUTE_GROUP' | 'TRUNK'
```

### API Method

```python
TelephonyApi.route_choices(
    route_group_name: str = None,
    trunk_name: str = None,
    order: str = None,              # sort fields: routeName, routeType
    org_id: str = None
) -> Generator[RouteIdentity, None, None]
```

### Usage Example

```python
# List all available route choices
for route in api.telephony.route_choices():
    print(f"{route.name} ({route.route_type}): {route.route_id}")

# Filter to trunks only
for route in api.telephony.route_choices(trunk_name='HQ'):
    print(f"Trunk: {route.name}")
```

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

```python
BASE = "https://webexapis.com/v1"

# List all available route choices (trunks + route groups)
choices = api.session.rest_get(f"{BASE}/telephony/config/premisePstn/routeChoices",
                               params={"max": 1000})
# choices["routeIdentities"] -> list of dicts with id, name, type
```

| Operation | Method | URL |
|-----------|--------|-----|
| List route choices | GET | `{BASE}/telephony/config/premisePstn/routeChoices` |

---

## Call Routing Test

The `test_call_routing()` method validates that an incoming call can be routed. It simulates the routing logic and returns the destination type and details.

### Data Models

```python
class OriginatorType(str, Enum):
    user = 'USER'                       # originator is a person
    trunk = 'TRUNK'                     # originator is a trunk

class DestinationType(str, Enum):
    hosted_agent = 'HOSTED_AGENT'       # person or workspace
    hosted_feature = 'HOSTED_FEATURE'   # auto-attendant, hunt group, call queue, etc.
    pbx_user = 'PBX_USER'              # on-premises PBX user
    pstn_number = 'PSTN_NUMBER'         # PSTN phone number
    virtual_extension = 'VIRTUAL_EXTENSION'
    virtual_extension_range = 'VIRTUAL_EXTENSION_RANGE'
    route_list = 'ROUTE_LIST'
    fac = 'FAC'                         # feature access code
    emergency = 'EMERGENCY'
    repair = 'REPAIR'                   # route in repair state
    unknown_extension = 'UNKNOWN_EXTENSION'
    unknown_number = 'UNKNOWN_NUMBER'

class CallSourceType(str, Enum):
    route_list = 'ROUTE_LIST'
    dial_pattern = 'DIAL_PATTERN'
    unknown_extension = 'UNKNOWN_EXTENSION'
    unknown_number = 'UNKNOWN_NUMBER'

class TestCallRoutingResult(ApiModel):
    language: Optional[str]
    time_zone: Optional[str]
    call_source_info: Optional[CallSourceInfo]
    destination_type: DestinationType
    routing_address: str                # FAC code or routing address
    outside_access_code: Optional[str]
    is_rejected: bool
    hosted_user: Optional[HostedUserDestination]       # alias 'hostedAgent'
    hosted_feature: Optional[HostedFeatureDestination]
    pbx_user: Optional[PbxUserDestination]
    pstn_number: Optional[PstnNumberDestination]
    virtual_extension: Optional[VirtualExtensionDestination]
    virtual_extension_range: Optional[VirtualExtensionRange]
    route_list: Optional[RouteListDestination]
    feature_access_code: Optional[FeatureAccessCodeDestination]
    emergency: Optional[EmergencyDestination]
    repair: Optional[TrunkDestination]
    unknown_extension: Optional[TrunkDestination]
    unknown_number: Optional[TrunkDestination]
    applied_services: Optional[list[AppliedService]]
```

#### `CallSourceInfo`

| Field | Type | Notes |
|-------|------|-------|
| `call_source_type` | `CallSourceType` | `ROUTE_LIST`, `DIAL_PATTERN`, `UNKNOWN_EXTENSION`, or `UNKNOWN_NUMBER` |
| `route_list_name` | `str` | Name of the matched route list (when type is ROUTE_LIST) |
| `route_list_id` | `str` | ID of the matched route list |
| `dial_plan_name` | `str` | Name of the matched dial plan (when type is DIAL_PATTERN) |
| `dial_plan_id` | `str` | ID of the matched dial plan |
| `dial_pattern` | `str` | The specific pattern that matched |

#### `AppliedService`

| Field | Type | Notes |
|-------|------|-------|
| `translation_pattern` | `object` | Translation pattern details if applied (see below) |

Translation pattern sub-object fields:
- `matching_pattern`: The pattern that matched the dialed number
- `replacement_pattern`: The replacement pattern applied
- `matched_number`: The original number that was matched
- `translated_number`: The resulting number after translation

#### Destination-Specific Models

These models populate the corresponding field on `TestCallRoutingResult` based on the `destination_type`:

| Model | Key Fields | Notes |
|-------|------------|-------|
| `HostedUserDestination` | `hosted_user_id`, `last_name`, `first_name`, `extension`, `phone_number`, `location_name` | Person or workspace destination |
| `HostedFeatureDestination` | `hosted_feature_id`, `name`, `feature_type`, `extension`, `phone_number`, `location_name` | AA, CQ, HG, or other hosted feature |
| `PbxUserDestination` | `dial_plan_name`, `dial_pattern`, `trunk_name`, `route_group_name` | On-premises PBX user routed via trunk |
| `PstnNumberDestination` | `trunk_name`, `route_group_name`, `trunk_id`, `route_group_id`, `outside_access_code` | PSTN number routed via trunk/route group |
| `VirtualExtensionDestination` | `extension`, `first_name`, `last_name`, `phone_number` | Virtual extension destination |
| `VirtualExtensionRange` | `extension`, `prefix`, `range_name` | Virtual extension range destination |
| `RouteListDestination` | `route_list_id`, `route_list_name`, `route_group_name`, `trunk_name` | Route list destination |
| `FeatureAccessCodeDestination` | `code`, `name` | Feature access code destination |
| `EmergencyDestination` | `is_emergency_callback_number` | Emergency services destination |
| `TrunkDestination` | `trunk_name`, `trunk_id`, `route_group_name`, `route_group_id` | Used for repair, unknown_extension, unknown_number |

The `applied_services` field returns details about any translation patterns, call intercept rules, or outgoing calling plan permissions that were applied during routing.

### API Method

```python
TelephonyApi.test_call_routing(
    originator_id: str,                 # person ID or trunk ID
    originator_type: OriginatorType,    # USER or TRUNK
    destination: str,                   # any dialable string (E.164, extension, URL, FAC)
    originator_number: str = None,      # phone number/URI -- only when originator_type is TRUNK
    include_applied_services: bool = None,  # include translation patterns, intercept, permissions
    org_id: str = None
) -> TestCallRoutingResult
```

### Usage Example

```python
from wxc_sdk.telephony import OriginatorType

# Test routing from a user to an external number
result = api.telephony.test_call_routing(
    originator_id=person_id,
    originator_type=OriginatorType.user,
    destination='+19195551234',
    include_applied_services=True
)

print(f"Destination type: {result.destination_type}")
print(f"Routing address: {result.routing_address}")
print(f"Rejected: {result.is_rejected}")

if result.destination_type == DestinationType.pstn_number:
    print(f"Trunk: {result.pstn_number.trunk_name}")
    print(f"Route Group: {result.pstn_number.route_group_name}")

if result.applied_services:
    for svc in result.applied_services:
        if svc.translation_pattern:
            tp = svc.translation_pattern
            print(f"Translation: {tp.matching_pattern} -> {tp.replacement_pattern}")
            print(f"  {tp.matched_number} -> {tp.translated_number}")

# Test routing from a trunk (inbound from PSTN)
result = api.telephony.test_call_routing(
    originator_id=trunk_id,
    originator_type=OriginatorType.trunk,
    destination='+19195551234',
    originator_number='+14085559999'
)

if result.call_source_info:
    csi = result.call_source_info
    print(f"Call source type: {csi.call_source_type}")
    if csi.route_list_name:
        print(f"Route list: {csi.route_list_name}")
    if csi.dial_plan_name:
        print(f"Dial plan: {csi.dial_plan_name}, Pattern: {csi.dial_pattern}")
```

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

Test call routing uses an action endpoint under `/telephony/config/` (NOT `/premisePstn/`).

```python
BASE = "https://webexapis.com/v1"

# Test call routing (POST, not GET)
result = api.session.rest_post(
    f"{BASE}/telephony/config/actions/testCallRouting/invoke", json={
        "originatorId": person_id,
        "originatorType": "USER",
        "destination": "+19195551234",
        "includeAppliedServices": True
    })
# result["destinationType"] -> "HOSTED_AGENT", "PSTN_NUMBER", etc.
# result["routingAddress"] -> the resolved routing address
# result["isRejected"] -> boolean

# Test from trunk (inbound from PSTN)
result = api.session.rest_post(
    f"{BASE}/telephony/config/actions/testCallRouting/invoke", json={
        "originatorId": trunk_id,
        "originatorType": "TRUNK",
        "destination": "+19195551234",
        "originatorNumber": "+14085559999"
    })
```

**Note:** The `originatorType` value differs between sources. The OpenAPI spec defines `OriginatorType` as `["PEOPLE", "TRUNK"]`, while wxc_sdk uses `"USER"` and `"TRUNK"`. The live API accepts **both** `"PEOPLE"` and `"USER"` as valid values for `originatorType` and returns identical results. Use `"PEOPLE"` for new code (matches OpenAPI spec), but `"USER"` (wxc_sdk convention) also works. <!-- Verified via live API 2026-03-19: tested testCallRouting/invoke with both PEOPLE and USER, both succeed -->

| Operation | Method | URL |
|-----------|--------|-----|
| Test call routing | POST | `{BASE}/telephony/config/actions/testCallRouting/invoke` |

---

## Phone Number Management

### List Phone Numbers

```python
TelephonyApi.phone_numbers(
    location_id: str = None,
    phone_number: str = None,
    available: bool = None,
    order: str = None,                  # sort: lastName, dn, extension
    owner_name: str = None,
    owner_id: str = None,
    owner_type: OwnerType = None,
    extension: str = None,
    number_type: NumberType = None,     # EXTENSION | NUMBER
    phone_number_type: NumberListPhoneNumberType = None,  # PRIMARY | ALTERNATE | FAX | DNIS
    state: NumberState = None,          # ACTIVE | INACTIVE
    details: bool = None,
    toll_free_numbers: bool = None,
    restricted_non_geo_numbers: bool = None,
    included_telephony_type: TelephonyType = None,  # PSTN_NUMBER | MOBILE_NUMBER
    service_number: bool = None,
    org_id: str = None
) -> Generator[NumberListPhoneNumber, None, None]
```

Numbers can be standard, service, or mobile. Both standard and service numbers are PSTN numbers. Service numbers are high-utilization numbers assignable to features (auto-attendants, call queues, hunt groups).

### Validate Phone Numbers

```python
TelephonyApi.validate_phone_numbers(
    phone_numbers: list[str],
    org_id: str = None
) -> ValidatePhoneNumbersResponse
```

```python
class ValidatePhoneNumbersResponse(ApiModel):
    status: ValidationStatus            # 'OK' | 'ERRORS'
    phone_numbers: Optional[list[ValidatePhoneNumberStatus]]
    # .ok property: True if status == 'OK'

class ValidatePhoneNumberStatus(ApiModel):
    phone_number: str
    state: ValidatePhoneNumberStatusState  # Available | Duplicate | Duplicate In List | Invalid | Unavailable
    toll_free_number: bool
    detail: list[str]
    # .ok property: True if state == Available
```

Phone numbers must follow **E.164 format** for all countries, except for the United States which can also use National format.

### Usage Example

```python
# Validate numbers before provisioning
result = api.telephony.validate_phone_numbers(
    phone_numbers=['+19195551234', '+19195555678']
)
if result.ok:
    print("All numbers available")
else:
    for pn in result.phone_numbers:
        if not pn.ok:
            print(f"{pn.phone_number}: {pn.state} - {pn.detail}")

# List all assigned numbers at a location
for num in api.telephony.phone_numbers(location_id=location_id, available=False):
    owner_name = num.owner.last_name if num.owner else 'Unassigned'
    print(f"{num.phone_number} ext:{num.extension} -> {owner_name}")
```

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

```python
BASE = "https://webexapis.com/v1"

# List phone numbers (no auto-pagination -- use max=1000)
numbers = api.session.rest_get(f"{BASE}/telephony/config/numbers",
                               params={"max": 1000, "locationId": location_id})
# numbers["phoneNumbers"] -> list of dicts

# Validate phone numbers
result = api.session.rest_post(f"{BASE}/telephony/config/actions/validateNumbers/invoke",
                               json={"phoneNumbers": ["+19195551234", "+19195555678"]})
# result["status"] -> "OK" or "ERRORS"
# result["phoneNumbers"] -> list of validation status dicts
```

| Operation | Method | URL |
|-----------|--------|-----|
| List numbers | GET | `{BASE}/telephony/config/numbers` |
| Validate numbers | POST | `{BASE}/telephony/config/actions/validateNumbers/invoke` |

---

## Data Models Quick Reference

### Enums

| Enum | Values | Used In |
|------|--------|---------|
| `RouteType` | `ROUTE_GROUP`, `TRUNK`, `CISCO_PSTN`, `CLOUD_CONNECTED_PSTN` | Dial plans, PSTN config |
| `TrunkType` | `REGISTERING`, `CERTIFICATE_BASED` | Trunk creation |
| `PatternAction` | `ADD`, `DELETE` | Dial pattern and route list number modifications |
| `ValidationStatus` | `OK`, `ERRORS` | Pattern and number validation results |
| `DialPatternStatus` | `INVALID`, `DUPLICATE`, `DUPLICATE_IN_LIST` | Pattern validation errors |
| `DeviceStatus` | `online`, `offline`, `unknown` | Trunk detail status |
| `PSTNType` | `LOCAL_GATEWAY`, `NON_INTEGRATED_CCP`, `INTEGRATED_CCP`, `CISCO_PSTN` | PSTN connection config |
| `NetworkConnectionType` | `PUBLIC_INTERNET`, `PRIVATE_NETWORK` | PNC settings |
| `OriginatorType` | `USER`, `TRUNK` | Call routing test |
| `DestinationType` | `HOSTED_AGENT`, `HOSTED_FEATURE`, `PBX_USER`, `PSTN_NUMBER`, `VIRTUAL_EXTENSION`, `VIRTUAL_EXTENSION_RANGE`, `ROUTE_LIST`, `FAC`, `EMERGENCY`, `REPAIR`, `UNKNOWN_EXTENSION`, `UNKNOWN_NUMBER` | Call routing test result |
| `TranslationPatternLevel` | `Location`, `Organization` | Translation patterns |
| `NumberState` | `ACTIVE`, `INACTIVE` | Phone number listing |
| `PChargeInfoSupportPolicy` | `DISABLED`, `ASSERTED_IDENTITY`, `CONFIGURABLE_CHARGE_NUMBER` | Trunk config |

### Complete End-to-End Setup Flow

The typical order for setting up premises-based PSTN routing:

1. **Create Trunk(s)** -- establish SIP connections to on-premises gateways
2. **Create Route Group** (optional) -- bundle trunks for failover
3. **Create Dial Plan** -- define patterns and associate with trunk or route group
4. **Create Translation Patterns** (optional) -- digit manipulation before routing
5. **Configure PSTN Connection** -- point location to trunk or route group
6. **Create Route List** (optional) -- for Dedicated Instance cloud PSTN
7. **Validate** -- use `test_call_routing()` to verify the configuration

```
Step 1: Trunk (SBC/LGW)
         |
Step 2: Route Group (optional, for failover)
         |
Step 3: Dial Plan (pattern matching → route choice)
         |
Step 4: Translation Pattern (optional, digit rewrite)
         |
Step 5: PSTN Connection (location → trunk/route group)
         |
Step 6: Route List (optional, Dedicated Instance)
         |
Step 7: test_call_routing() to validate
```

---

## Common Gotchas

### 0. Raw HTTP URLs require the `/premisePstn/` prefix for routing resources
<!-- Updated by playbook session 2026-03-18 -->

Dial plans, trunks, route groups, and route lists all live under `telephony/config/premisePstn/` -- NOT under `telephony/config/dialPlans` or similar. Translation patterns use a different prefix: `telephony/config/callRouting/translationPatterns`. PSTN connection uses yet another: `telephony/pstn/locations/`. Test call routing uses `telephony/config/actions/testCallRouting/invoke`. Getting any of these prefixes wrong returns 404.

### 1. Translation pattern replacement must use fully specified digits
<!-- Verified via CLI implementation 2026-03-18 -->

E.164-formatted translation pattern replacement strings cannot contain `X` wildcards. For example, `+1919666XXXX` is rejected — use `+19196660000` instead. Note: `X` wildcards ARE valid in non-E.164 replacement patterns for digit manipulation (e.g., replacing `9XXX` with `XXX` to strip a prefix).

### 2. Dial plans require an existing trunk or route group
<!-- Verified via CLI implementation 2026-03-18 -->

You cannot create a standalone dial plan without a route choice. The dial plan must reference an existing trunk or route group as its route choice at creation time.

### 3. Test Call Routing requires a calling-enabled user's originatorId
<!-- Verified via CLI implementation 2026-03-18 -->

The `test_call_routing` API requires the `originatorId` to be a valid calling-enabled user. Passing a non-calling user's ID returns `404 "Originator not found"`. Always verify the user has a Webex Calling license and location assigned before using them as an originator.

### 4. Number porting and ordering are Control Hub only

The API manages PSTN connections, trunks, and routing for numbers that already exist in the org. To port in new numbers or order from Cisco Calling Plan, use Control Hub or contact Cisco PTS.

---

## See Also

- [Major Call Features](call-features-major.md) -- Auto Attendants, Call Queues, and Hunt Groups (the `HOSTED_FEATURE` destination type in call routing test results covers these features)
- [Provisioning Reference](provisioning.md) -- creating locations and users (trunks, route lists, and PSTN connections are all location-scoped)
- [Devices Reference](devices-core.md) -- device types and device management (relevant to trunk device type selection)
