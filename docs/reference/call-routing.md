<!-- Updated by playbook session 2026-03-18 -->
# Call Routing & PSTN Reference

## Sources
- OpenAPI spec: specs/webex-cloud-calling.json
- developer.webex.com Call Routing APIs

Comprehensive reference for Webex Calling dial plans, trunks, route groups, route lists, translation patterns, PSTN configuration, and call routing validation using the `wxcli` CLI and raw HTTP via `api.session`.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [API Base Paths](#api-base-paths)
3. [Required Scopes](#required-scopes)
4. [Dial Plans](#dial-plans)
5. [Trunks](#trunks)
6. [Route Groups](#route-groups)
7. [Route Lists](#route-lists)
8. [Translation Patterns](#translation-patterns)
9. [PSTN Configuration](#pstn-configuration)
10. [Private Network Connect (PNC)](#private-network-connect-pnc)
11. [Route Choices](#route-choices)
12. [Call Routing Test](#call-routing-test)
13. [Phone Number Management](#phone-number-management)
14. [Data Models Quick Reference](#data-models-quick-reference)
15. [Common Gotchas](#common-gotchas)
16. [See Also](#see-also)

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

## API Base Paths

| Resource | REST Base Path |
|----------|---------------|
| Dial Plans | `telephony/config/premisePstn/dialPlans` |
| Trunks | `telephony/config/premisePstn/trunks` |
| Route Groups | `telephony/config/premisePstn/routeGroups` |
| Route Lists | `telephony/config/premisePstn/routeLists` |
| Translation Patterns | `telephony/config/callRouting/translationPatterns` |
| PSTN | `telephony/pstn/locations` |
| Private Network Connect | `telephony/config/locations` |
| Premise PSTN (parent) | `telephony/config/premisePstn` |

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

### Dial Pattern Rules

- A dial pattern is a sequence of digits (1-9), followed by optional wildcard characters.
- `!` matches any sequence of digits. Can only occur once at the end. Only valid in E.164 patterns.
- `X` matches a single digit (0-9).
- Example E.164 pattern: `+1408!` matches any number starting with +1408.
- Example short pattern: `9XXX` matches any 4-digit string starting with 9.

### API Methods

#### Update Dial Plan

All three fields (`name`, `routeId`, `routeType`) must be set when updating a dial plan.

#### Modify Dial Patterns (Add/Delete)

Patterns not present in the request are not modified.

### CLI Examples

```bash
# List all dial plans
wxcli call-routing list-dial-plans

# Filter dial plans by name
wxcli call-routing list-dial-plans --dial-plan-name "US-Outbound"

# Filter by trunk name
wxcli call-routing list-dial-plans --trunk-name "HQ-LGW-01"

# Filter by route group name
wxcli call-routing list-dial-plans --route-group-name "US-East-RG"

# Get dial plan details
wxcli call-routing show-dial-plans Y2lzY29zcGFyazovL_DIAL_PLAN_ID

# Create a dial plan (patterns require --json-body since dialPatterns is an array)
wxcli call-routing create --name "US-Outbound" --route-id Y2lzY29zcGFyazovL_TRUNK_ID

# Create with dial patterns via --json-body
wxcli call-routing create --json-body '{
  "name": "US-Outbound",
  "routeId": "Y2lzY29zcGFyazovL_TRUNK_ID",
  "routeType": "TRUNK",
  "dialPatterns": ["+1!", "+44!"]
}'

# Update a dial plan name or route assignment
wxcli call-routing update-dial-plans Y2lzY29zcGFyazovL_DIAL_PLAN_ID \
  --name "US-Outbound-v2" --route-id Y2lzY29zcGFyazovL_NEW_TRUNK_ID

# Modify dial patterns (add/delete patterns on an existing dial plan)
wxcli call-routing update Y2lzY29zcGFyazovL_DIAL_PLAN_ID --json-body '{
  "dialPatterns": [
    {"dialPattern": "+44!", "action": "ADD"},
    {"dialPattern": "+1!", "action": "DELETE"}
  ]
}'

# Delete all dial patterns from a dial plan
wxcli call-routing update Y2lzY29zcGFyazovL_DIAL_PLAN_ID --delete-all-dial-patterns

# Validate dial patterns before creating a dial plan
wxcli call-routing validate-a-dial --json-body '{"dialPatterns": ["+1408!", "+44!", "9XXX"]}'

# Delete a dial plan
wxcli call-routing delete Y2lzY29zcGFyazovL_DIAL_PLAN_ID --force
```

### Raw HTTP
<!-- Updated by playbook session 2026-03-18 -->

All dial plan endpoints live under the `/premisePstn/` prefix -- NOT `/dialPlans` at the top level.

```python
from wxcli.auth import get_api
api = get_api()
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

#### Update Trunk

`name` and `password` are always required for updates.

**Limitation**: You cannot change `trunkType`, `locationId`, or `deviceType` after creation. To change these properties, you must delete and recreate the trunk.

### CLI Examples

```bash
# List all trunks
wxcli call-routing list-trunks

# Filter trunks by name
wxcli call-routing list-trunks --name "HQ-LGW"

# Filter by location
wxcli call-routing list-trunks --location-name "Raleigh"

# Filter by trunk type
wxcli call-routing list-trunks --trunk-type REGISTERING

# Get trunk details
wxcli call-routing show-trunks Y2lzY29zcGFyazovL_TRUNK_ID

# List available trunk types and their device types
wxcli call-routing list-trunk-types

# Create a registering trunk (Cisco CUBE Local Gateway)
wxcli call-routing create-trunks --name "HQ-LGW-01" \
  --location-id Y2lzY29zcGFyazovL_LOC_ID \
  --password "SecurePass123!"

# Create a certificate-based trunk with FQDN
wxcli call-routing create-trunks --name "HQ-SBC-01" \
  --location-id Y2lzY29zcGFyazovL_LOC_ID \
  --password "SecurePass123!" \
  --address "sbc.example.com" \
  --domain "example.com" \
  --port 5061 \
  --max-concurrent-calls 100

# Create with full JSON body (includes device type and dual identity)
wxcli call-routing create-trunks --json-body '{
  "name": "HQ-LGW-02",
  "locationId": "Y2lzY29zcGFyazovL_LOC_ID",
  "password": "SecurePass123!",
  "trunkType": "REGISTERING",
  "dualIdentitySupportEnabled": true,
  "deviceType": "Cisco Unified Border Element"
}'

# Update a trunk (rename and change password)
wxcli call-routing update-trunks Y2lzY29zcGFyazovL_TRUNK_ID \
  --name "HQ-LGW-01-v2" --password "NewPass456!"

# Validate FQDN and domain before creating a certificate-based trunk
wxcli call-routing validate-local-gateway \
  --address "sbc.example.com" --domain "example.com" --port 5061

# Get trunk usage count (how many dial plans, route groups, etc. use it)
wxcli call-routing show Y2lzY29zcGFyazovL_TRUNK_ID

# List dial plans using this trunk
wxcli call-routing list Y2lzY29zcGFyazovL_TRUNK_ID

# List route groups using this trunk
wxcli call-routing list-usage-route-group Y2lzY29zcGFyazovL_TRUNK_ID

# List locations using this trunk as PSTN connection
wxcli call-routing list-usage-pstn-connection-trunks Y2lzY29zcGFyazovL_TRUNK_ID

# List call-to-extension locations for this trunk
wxcli call-routing list-usage-call-to-extension-trunks Y2lzY29zcGFyazovL_TRUNK_ID

# Delete a trunk
wxcli call-routing delete-trunks Y2lzY29zcGFyazovL_TRUNK_ID --force
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

### API Methods

#### Create Route Group

The route group must have `name` and `localGateways` set. Each entry in `localGateways` must have `trunkId` and `priority` set.

### CLI Examples

```bash
# List all route groups
wxcli call-routing list-route-groups

# Filter by name
wxcli call-routing list-route-groups --name "US-East"

# Get route group details (includes trunk assignments)
wxcli call-routing show-route-groups Y2lzY29zcGFyazovL_RG_ID

# Create a route group with trunk assignments (requires --json-body for localGateways array)
wxcli call-routing create-route-groups --json-body '{
  "name": "US-East-RG",
  "localGateways": [
    {"id": "Y2lzY29zcGFyazovL_PRIMARY_TRUNK_ID", "priority": "1"},
    {"id": "Y2lzY29zcGFyazovL_BACKUP_TRUNK_ID", "priority": "2"}
  ]
}'

# Create with just a name (trunks can be added later via update)
wxcli call-routing create-route-groups --name "US-East-RG"

# Update a route group (rename or change trunk assignments)
wxcli call-routing update-route-groups Y2lzY29zcGFyazovL_RG_ID \
  --name "US-East-RG-v2"

# Update trunk assignments via --json-body
wxcli call-routing update-route-groups Y2lzY29zcGFyazovL_RG_ID --json-body '{
  "name": "US-East-RG-v2",
  "localGateways": [
    {"id": "Y2lzY29zcGFyazovL_PRIMARY_TRUNK_ID", "priority": "1"}
  ]
}'

# Get route group usage count
wxcli call-routing show-usage Y2lzY29zcGFyazovL_RG_ID

# List dial plan locations using this route group
wxcli call-routing list-usage-dial-plan Y2lzY29zcGFyazovL_RG_ID

# List PSTN connection locations using this route group
wxcli call-routing list-usage-pstn-connection-route-groups Y2lzY29zcGFyazovL_RG_ID

# List route lists using this route group
wxcli call-routing list-usage-route-list Y2lzY29zcGFyazovL_RG_ID

# List call-to-extension locations using this route group
wxcli call-routing list-usage-call-to-extension-route-groups Y2lzY29zcGFyazovL_RG_ID

# Delete a route group
wxcli call-routing delete-route-groups Y2lzY29zcGFyazovL_RG_ID --force
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

### API Methods

#### Modify Numbers on a Route List (Add/Delete)

If `deleteAllNumbers` is set, the `numbers` array is ignored and all numbers are removed.

### CLI Examples

```bash
# List all route lists
wxcli call-routing list-route-lists

# Filter by name
wxcli call-routing list-route-lists --name "US-East-Numbers"

# Filter by location
wxcli call-routing list-route-lists --location-id Y2lzY29zcGFyazovL_LOC_ID

# Get route list details
wxcli call-routing show-route-lists Y2lzY29zcGFyazovL_RL_ID

# Create a route list
wxcli call-routing create-route-lists \
  --name "US-East-Numbers" \
  --location-id Y2lzY29zcGFyazovL_LOC_ID \
  --route-group-id Y2lzY29zcGFyazovL_RG_ID

# Update a route list (rename or change route group)
wxcli call-routing update-route-lists Y2lzY29zcGFyazovL_RL_ID \
  --name "US-East-Numbers-v2"

# List numbers assigned to a route list
wxcli call-routing list-numbers Y2lzY29zcGFyazovL_RL_ID

# Add/delete numbers on a route list (requires --json-body for numbers array)
wxcli call-routing update-numbers Y2lzY29zcGFyazovL_RL_ID --json-body '{
  "numbers": [
    {"number": "+19195551234", "action": "ADD"},
    {"number": "+19195555678", "action": "ADD"}
  ]
}'

# Delete all numbers from a route list
wxcli call-routing update-numbers Y2lzY29zcGFyazovL_RL_ID --delete-all-numbers

# Delete a route list
wxcli call-routing delete-route-lists Y2lzY29zcGFyazovL_RL_ID --force
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

### API Methods

#### Create Translation Pattern

The pattern must have `name`, `matchingPattern`, and `replacementPattern` set. The `id`, `level`, and `location` fields are excluded from the create payload.

### Endpoint Routing

- **Org-level**: `telephony/config/callRouting/translationPatterns`
- **Location-level**: `telephony/config/locations/{location_id}/callRouting/translationPatterns`

### CLI Examples

```bash
# List all translation patterns (org-level and location-level)
wxcli call-routing list-translation-patterns

# Filter to org-level patterns only
wxcli call-routing list-translation-patterns --limit-to-org-level-enabled true

# Filter to patterns at a specific location
wxcli call-routing list-translation-patterns \
  --limit-to-location-id Y2lzY29zcGFyazovL_LOC_ID

# Filter by name or matching pattern
wxcli call-routing list-translation-patterns --name "Strip-9-Prefix"
wxcli call-routing list-translation-patterns --matching-pattern "9XXX"

# Get org-level translation pattern details
wxcli call-routing show-translation-patterns-call-routing Y2lzY29zcGFyazovL_TP_ID

# Get location-level translation pattern details (location_id then translation_id)
wxcli call-routing show-translation-patterns-call-routing-1 \
  Y2lzY29zcGFyazovL_LOC_ID Y2lzY29zcGFyazovL_TP_ID

# Create an org-level translation pattern (strip leading 9)
wxcli call-routing create-translation-patterns-call-routing \
  --name "Strip-9-Prefix" \
  --matching-pattern "9XXX" \
  --replacement-pattern "XXX"

# Create a location-level translation pattern
wxcli call-routing create-translation-patterns-call-routing-1 Y2lzY29zcGFyazovL_LOC_ID \
  --name "Local-Rewrite" \
  --matching-pattern "+1919555XXXX" \
  --replacement-pattern "555XXXX"

# Update an org-level translation pattern
wxcli call-routing update-translation-patterns-call-routing Y2lzY29zcGFyazovL_TP_ID \
  --name "Strip-9-Prefix-v2" \
  --matching-pattern "9XXX" \
  --replacement-pattern "XXX"

# Update a location-level translation pattern (location_id then translation_id)
wxcli call-routing update-translation-patterns-call-routing-1 \
  Y2lzY29zcGFyazovL_LOC_ID Y2lzY29zcGFyazovL_TP_ID \
  --name "Local-Rewrite-v2"

# Delete an org-level translation pattern
wxcli call-routing delete-translation-patterns-call-routing Y2lzY29zcGFyazovL_TP_ID --force

# Delete a location-level translation pattern (location_id then translation_id)
wxcli call-routing delete-translation-patterns-call-routing-1 \
  Y2lzY29zcGFyazovL_LOC_ID Y2lzY29zcGFyazovL_TP_ID --force
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

### API Methods

#### Configure PSTN Connection for a Location

**Important**: Only `LOCAL_GATEWAY` and `NON_INTEGRATED_CCP` types can be configured via the API. `INTEGRATED_CCP` and `CISCO_PSTN` must be configured through the Control Hub UI.

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

## Private Network Connect (PNC)

Private Network Connect determines whether a location uses the public internet or a private network for its connection to Webex Calling.

### Endpoint

Both the read and update operations use: `telephony/config/locations/{location_id}/privateNetworkConnect`

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

Route Choices lists all available routing targets (trunks and route groups) for the organization. This is useful when building dial plans or configuring PSTN connections and you need to enumerate what routes are available.

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

Call Routing Test validates that an incoming call can be routed. It simulates the routing logic and returns the destination type and details.

### Data Models

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

### CLI Examples

```bash
# Test call routing from a user to an external number
wxcli call-routing test-call-routing \
  --originator-id Y2lzY29zcGFyazovL_PERSON_ID \
  --destination "+19195551234"

# Test with applied services (shows translation patterns, intercept, permissions)
wxcli call-routing test-call-routing \
  --originator-id Y2lzY29zcGFyazovL_PERSON_ID \
  --destination "+19195551234" \
  --include-applied-services true

# Test routing from a trunk (inbound from PSTN)
wxcli call-routing test-call-routing \
  --originator-id Y2lzY29zcGFyazovL_TRUNK_ID \
  --originator-number "+14085559999" \
  --destination "+19195551234"

# Test using full JSON body (originatorType defaults to PEOPLE per OpenAPI spec)
wxcli call-routing test-call-routing --json-body '{
  "originatorId": "Y2lzY29zcGFyazovL_PERSON_ID",
  "originatorType": "PEOPLE",
  "destination": "+19195551234",
  "includeAppliedServices": true
}'

# Test inbound from trunk via JSON body
wxcli call-routing test-call-routing --json-body '{
  "originatorId": "Y2lzY29zcGFyazovL_TRUNK_ID",
  "originatorType": "TRUNK",
  "destination": "+19195551234",
  "originatorNumber": "+14085559999"
}'
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

**Note:** The live API accepts **both** `"PEOPLE"` and `"USER"` as valid values for `originatorType` and returns identical results. The OpenAPI spec defines `OriginatorType` as `["PEOPLE", "TRUNK"]`; `"USER"` is also accepted for compatibility with older integrations. Use `"PEOPLE"` for new code.

| Operation | Method | URL |
|-----------|--------|-----|
| Test call routing | POST | `{BASE}/telephony/config/actions/testCallRouting/invoke` |

---

## Phone Number Management

### List Phone Numbers

Numbers can be standard, service, or mobile. Both standard and service numbers are PSTN numbers. Service numbers are high-utilization numbers assignable to features (auto-attendants, call queues, hunt groups).

### Validate Phone Numbers

Phone numbers must follow **E.164 format** for all countries, except for the United States which can also use National format.

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
7. **Validate** -- use Call Routing Test to verify the configuration

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
Step 7: Call Routing Test to validate
```

---

## Common Gotchas

### 0. Raw HTTP URLs require the `/premisePstn/` prefix for routing resources
<!-- Updated by playbook session 2026-03-18 -->

Dial plans, trunks, route groups, and route lists all live under `telephony/config/premisePstn/` -- NOT under `telephony/config/dialPlans` or similar. Translation patterns use a different prefix: `telephony/config/callRouting/translationPatterns`. PSTN connection uses yet another: `telephony/pstn/locations/`. Test call routing uses `telephony/config/actions/testCallRouting/invoke`. Getting any of these prefixes wrong returns 404.

### 1. Translation pattern replacement must use fully specified digits

Translation pattern replacement strings cannot contain `X` wildcards in any format. For example, `+1919666XXXX` is rejected, and so is `XXX` (non-E.164). Use fully specified literal digits: `+19196660000`. The matching pattern accepts `X` wildcards normally (`9XXXXXXX`, `+1512555XXXX`), but the replacement must be all literal digits. Confirmed via live API testing 2026-04-18 — error 28043 "Invalid Translation Replacement Pattern" for any replacement containing `X`.

### 2. Dial plans require an existing trunk or route group

You cannot create a standalone dial plan without a route choice. The dial plan must reference an existing trunk or route group as its route choice at creation time.

### 3. Test Call Routing requires a calling-enabled user's originatorId

The `test_call_routing` API requires the `originatorId` to be a valid calling-enabled user. Passing a non-calling user's ID returns `404 "Originator not found"`. Always verify the user has a Webex Calling license and location assigned before using them as an originator.

### 4. Trunk passwords reject `?` and `!` characters

When creating a REGISTERING trunk, the password field rejects `?` and `!` — error 25015 "Invalid characters ? or ! in password." Use alphanumeric + other special characters (e.g., `@`, `#`, `$`). Confirmed via live API testing 2026-04-18.

### 5. Number porting and ordering are Control Hub only

The API manages PSTN connections, trunks, and routing for numbers that already exist in the org. To port in new numbers or order from Cisco Calling Plan, use Control Hub or contact Cisco PTS.

---

## See Also

- [Major Call Features](call-features-major.md) -- Auto Attendants, Call Queues, and Hunt Groups (the `HOSTED_FEATURE` destination type in call routing test results covers these features)
- [Provisioning Reference](provisioning.md) -- creating locations and users (trunks, route lists, and PSTN connections are all location-scoped)
- [Devices Reference](devices-core.md) -- device types and device management (relevant to trunk device type selection)
