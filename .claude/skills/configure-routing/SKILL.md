---
name: configure-routing
description: |
  Configure Webex Calling routing infrastructure using wxcli CLI commands: Trunks, Route Groups,
  Route Lists, Dial Plans, Translation Patterns, and PSTN Connection settings.
  Guides the user from prerequisites through the full dependency chain and verification.
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [routing-component]
---

<!-- Created 2026-03-19 -->

# Configure Call Routing Workflow

## When to Use This Skill

- Setting up PSTN connectivity for a location (local gateway, cloud-connected PSTN)
- Creating or modifying dial plans and dial patterns
- Configuring trunks to on-premises SBCs or local gateways
- Building route groups for trunk failover/load distribution
- Creating route lists for Dedicated Instance cloud PSTN
- Adding translation patterns for digit manipulation
- Validating or testing call routing end-to-end

## Step 1: Load references

1. Read `docs/reference/call-routing.md` for full API detail, data models, and gotchas
2. Read `docs/reference/authentication.md` for auth token conventions

## Step 2: Verify auth token

Before any API calls, confirm the user has a working auth token:

```bash
wxcli whoami
```

If this fails, stop and resolve authentication first (`wxcli configure`). Required scopes for routing:

- **Read**: `spark-admin:telephony_config_read`
- **Write**: `spark-admin:telephony_config_write`
- **PSTN Read**: `spark-admin:telephony_pstn_read`
- **PSTN Write**: `spark-admin:telephony_pstn_write`

## Step 3: Interview -- what routing does the user need?

Ask the user what they want to accomplish. Present this decision matrix if they are unsure:

| Need | Component(s) |
|------|-------------|
| Connect a location to PSTN via on-premises SBC/gateway | **Trunk** + **PSTN Connection** |
| Failover between multiple SBCs across locations | **Trunk(s)** + **Route Group** + **Dial Plan** |
| Route outbound calls by dialed pattern (e.g., +1! to US trunk) | **Dial Plan** (requires existing trunk or route group) |
| Rewrite/manipulate digits before routing (strip prefix, add prefix) | **Translation Pattern** (org-level or location-level) |
| Provide cloud PSTN numbers to Dedicated Instance | **Route List** (requires route group) |
| Verify that a number routes correctly end-to-end | **Test Call Routing** |
| Set up full premises-based PSTN from scratch | All: Trunk -> Route Group -> Dial Plan -> PSTN Connection |

## Step 4: Prerequisites

### 4a. Location exists

Trunks, route lists, and PSTN connections are location-scoped. Confirm the target location:

```bash
wxcli locations list --output json
```

Capture the `location_id` for the target location.

### 4b. PSTN provider / SBC credentials ready

For premises-based PSTN (local gateway trunks), the user needs:

| Trunk Type | Requirements |
|-----------|-------------|
| **Registering** (`REGISTERING`) | Cisco CUBE Local Gateway. Needs a password for SIP registration. |
| **Certificate-based** (`CERTIFICATE_BASED`) | Cisco UBE, Oracle ACME, AudioCodes, or Ribbon SBC. Needs FQDN/SRV address, domain, port, and max concurrent calls. |

For cloud-connected PSTN (CCP), the provider must already be set up in Control Hub.

### 4c. Existing routing components (if building on top of them)

Check what already exists:

```bash
# List existing trunks
wxcli call-routing list-trunks --output json

# List existing route groups
wxcli call-routing list-route-groups --output json

# List existing dial plans
wxcli call-routing list-dial-plans --output json

# List existing translation patterns
wxcli call-routing list-translation-patterns --output json

# List existing route lists
wxcli call-routing list-route-lists --output json

# Check current PSTN connection for a location
wxcli pstn list-connection LOCATION_ID --output json
```

### 4d. Dependency chain -- `[STRICT ORDER]`

Routing components have hard dependencies. You **must** create them in this order:

```
1: Trunk (SIP connection to SBC/LGW)
   |
2: Route Group (optional -- bundles trunks for failover)
   |
3: Dial Plan (pattern matching -> trunk or route group)
   |
4: Translation Pattern (optional -- digit rewrite before routing)
   |
5: PSTN Connection (points a location to trunk or route group)
   |
6: Route List (optional -- for Dedicated Instance cloud PSTN)
   |
7: Test Call Routing (validate the configuration)
```

**Why this order matters:**
- A Dial Plan requires an existing trunk or route group as its route choice -- you cannot create a dial plan without one.
- A Route Group requires existing trunk(s) -- you cannot create a route group without trunks.
- A Route List requires an existing route group.
- PSTN Connection points to either a trunk or route group -- they must exist first.

**Deletion order (reverse):**

When tearing down routing, delete in reverse: PSTN Connection → Route Lists → Dial Plans → Route Groups → Trunks. A trunk cannot be deleted if it's referenced by a route group; a route group cannot be deleted if it's referenced by a dial plan or route list. The API returns error 27350 when you try to delete a component that's still referenced.

### 4e. Component CLI reference -- Trunks

A trunk is a SIP connection between Webex Calling and an on-premises local gateway or SBC.

**List available trunk types:**

```bash
wxcli call-routing list-trunk-types --output json
```

**Create a registering trunk (Cisco CUBE):**

```bash
wxcli call-routing create-trunks \
  --name "HQ-LGW-01" \
  --location-id LOCATION_ID \
  --password "SecurePass123!" \
  --trunk-type REGISTERING
```

**Create a certificate-based trunk (third-party SBC):**

```bash
wxcli call-routing create-trunks \
  --name "HQ-SBC-01" \
  --location-id LOCATION_ID \
  --password "SecurePass123!" \
  --trunk-type CERTIFICATE_BASED \
  --address "sbc.example.com" \
  --domain "example.com" \
  --port 5061 \
  --max-concurrent-calls 100
```

**View trunk details and status:**

```bash
wxcli call-routing show-trunks TRUNK_ID --output json
```

The response includes `status` (online/offline/unknown), `sipAuthenticationUserName`, `linePort`, and `otgDtgId` -- all needed for SBC configuration.

**Check trunk usage (what's connected to it):**

```bash
wxcli call-routing show TRUNK_ID --output json
```

**Delete a trunk:**

```bash
wxcli call-routing delete-trunks TRUNK_ID
```

**Trunk limitations:**
- You cannot change `trunkType`, `locationId`, or `deviceType` after creation. Delete and recreate instead.
- `name` and `password` are always required on updates.

### 4f. Component CLI reference -- Route Groups

A route group bundles up to 10 trunks (from different locations) with priority-based failover.

**Create a route group:**

```bash
wxcli call-routing create-route-groups \
  --name "US-East-RG" \
  --json-body '{"localGateways": [{"trunkId": "TRUNK_ID_1", "priority": 1}, {"trunkId": "TRUNK_ID_2", "priority": 2}]}'
```

> **NOTE:** The `localGateways` array with trunk IDs and priorities requires `--json-body` because it's a nested object the CLI cannot express as flat options.

**View route group details:**

```bash
wxcli call-routing show-route-groups ROUTE_GROUP_ID --output json
```

**Check route group usage:**

```bash
wxcli call-routing show-usage ROUTE_GROUP_ID --output json
```

**Delete a route group:**

```bash
wxcli call-routing delete-route-groups ROUTE_GROUP_ID
```

### 4g. Component CLI reference -- Dial Plans

Dial plans route outbound calls by matching dialed patterns to a trunk or route group. They are **org-wide** (not per-location).

**Dial pattern rules:**
- `!` matches any sequence of digits. Can only appear once at the end. Only valid in E.164 patterns.
- `X` matches a single digit (0-9).
- Example E.164: `+1408!` matches any number starting with +1408.
- Example short: `9XXX` matches any 4-digit string starting with 9.

**Create a dial plan:**

```bash
wxcli call-routing create \
  --name "US-Outbound" \
  --route-id TRUNK_OR_ROUTE_GROUP_ID \
  --route-type TRUNK
```

`--route-type` is either `TRUNK` or `ROUTE_GROUP`.

**Add dial patterns to a dial plan:**

```bash
wxcli call-routing update DIAL_PLAN_ID \
  --json-body '{"dialPatterns": [{"dialPattern": "+1!", "action": "ADD"}, {"dialPattern": "+44!", "action": "ADD"}]}'
```

**Validate dial patterns before adding:**

```bash
wxcli call-routing validate-a-dial --json-body '{"dialPatterns": ["+1408!", "+44!", "9XXX"]}'
```

**View a dial plan:**

```bash
wxcli call-routing show-dial-plans DIAL_PLAN_ID --output json
```

**List dial patterns on a dial plan:**

```bash
wxcli call-routing list TRUNK_ID --output json
```

**Delete a dial plan:**

```bash
wxcli call-routing delete DIAL_PLAN_ID
```

### 4h. Component CLI reference -- Route Lists

Route lists are lists of phone numbers reachable via a route group. Used for Dedicated Instance cloud PSTN connectivity.

**Create a route list:**

```bash
wxcli call-routing create-route-lists \
  --name "US-East-Numbers" \
  --location-id LOCATION_ID \
  --route-group-id ROUTE_GROUP_ID
```

**Add numbers to a route list:**

```bash
wxcli call-routing update-numbers ROUTE_LIST_ID \
  --json-body '{"numbers": [{"number": "+19195551234", "action": "ADD"}, {"number": "+19195555678", "action": "ADD"}]}'
```

**List numbers on a route list:**

```bash
wxcli call-routing list-numbers ROUTE_LIST_ID --output json
```

**View route list details:**

```bash
wxcli call-routing show-route-lists ROUTE_LIST_ID --output json
```

**Delete a route list:**

```bash
wxcli call-routing delete-route-lists ROUTE_LIST_ID
```

### 4i. Component CLI reference -- Translation Patterns

Translation patterns rewrite dialed digits **before routing** (outbound calls only). They can be org-level or location-level.

**Common use cases:**

| Pattern | Matching | Replacement | Purpose |
|---------|----------|-------------|---------|
| Strip access code | `9XXX` | `XXX` | Remove leading '9' prefix for external dialing |
| Add country code | `XXXXXXXXXX` | `+1XXXXXXXXXX` | Prepend +1 to 10-digit national numbers |
| Site-specific rewrite | `+1919555XXXX` | `+19196660000` | Redirect a number range to a specific destination |
| Short code to E.164 | `411` | `+18005551212` | Map short codes to full numbers |

**Create org-level translation pattern:**

```bash
wxcli call-routing create-translation-patterns-call-routing \
  --name "Strip-9-Prefix" \
  --matching-pattern "9XXX" \
  --replacement-pattern "XXX"
```

**Create location-level translation pattern:**

```bash
wxcli call-routing create-translation-patterns-call-routing-1 \
  --name "Local-Rewrite" \
  --matching-pattern "+1919555XXXX" \
  --replacement-pattern "+19196660000" \
  --location-id LOCATION_ID
```

**View translation patterns:**

```bash
# List all translation patterns (org and location)
wxcli call-routing list-translation-patterns --output json

# Show a specific org-level pattern
wxcli call-routing show-translation-patterns-call-routing PATTERN_ID --output json

# Show a specific location-level pattern
wxcli call-routing show-translation-patterns-call-routing-1 PATTERN_ID --location-id LOCATION_ID --output json
```

**Delete translation patterns:**

```bash
# Org-level
wxcli call-routing delete-translation-patterns-call-routing PATTERN_ID

# Location-level
wxcli call-routing delete-translation-patterns-call-routing-1 PATTERN_ID --location-id LOCATION_ID
```

### 4j. Component CLI reference -- PSTN Connection (per-location)

The PSTN connection setting determines which provider handles calls for a specific location.

**PSTN connection types:**

| Type | Value | API Configurable? | Notes |
|------|-------|:-----------------:|-------|
| Local Gateway | `LOCAL_GATEWAY` | Yes | Points to a trunk or route group |
| Non-Integrated CCP | `NON_INTEGRATED_CCP` | Yes | Points to a CCP provider ID |
| Integrated CCP | `INTEGRATED_CCP` | No | Must be configured via Control Hub |
| Cisco PSTN | `CISCO_PSTN` | No | Must be configured via Control Hub |

**Check available PSTN options for a location:**

```bash
wxcli pstn list LOCATION_ID --output json
```

**Read current PSTN connection:**

```bash
wxcli pstn list-connection LOCATION_ID --output json
```

**Set PSTN connection to a trunk:**

```bash
wxcli pstn update LOCATION_ID \
  --json-body '{"premiseRouteType": "TRUNK", "premiseRouteId": "TRUNK_ID"}'
```

**Set PSTN connection to a route group:**

```bash
wxcli pstn update LOCATION_ID \
  --json-body '{"premiseRouteType": "ROUTE_GROUP", "premiseRouteId": "ROUTE_GROUP_ID"}'
```

## Step 5: Build and present deployment plan -- [SHOW BEFORE EXECUTING]

Before executing any commands, present the full plan to the user:

```
ROUTING DEPLOYMENT PLAN
=======================
Objective: [what the user wants to accomplish]
Location: [name] ([location_id])

Components to create (in dependency order):

  1. Trunk: [name]
     Type: [REGISTERING / CERTIFICATE_BASED]
     Location: [location_name]
     [FQDN/Port if certificate-based]

  2. Route Group: [name] (if applicable)
     Trunks: [trunk_1 (priority 1), trunk_2 (priority 2)]

  3. Dial Plan: [name]
     Route Choice: [trunk or route group name] ([type])
     Patterns: [+1!, +44!, etc.]

  4. Translation Patterns: (if applicable)
     [matching_pattern] -> [replacement_pattern] ([org/location level])

  5. PSTN Connection:
     Location: [location_name]
     Route Type: [TRUNK / ROUTE_GROUP]
     Route Target: [trunk or route group name]

Prerequisites verified:
  [check] Location exists
  [check] SBC/gateway credentials available
  [check] No conflicting dial patterns

Commands to execute:
  wxcli call-routing create-trunks ...
  wxcli call-routing create-route-groups ...
  wxcli call-routing create ...
  wxcli pstn update ...

Proceed? (yes/no)
```

**Wait for user confirmation before executing.**

> **WARNING:** Routing changes can affect live calls. Modifying dial plans, trunks, or PSTN connections on a production organization can immediately disrupt call routing for all users. Always confirm with the user and prefer off-hours changes for production environments.

## Step 6: Execute via wxcli

### 6a. Run commands in dependency order

Execute commands in strict dependency order (Step 4d): Trunk -> Route Group -> Dial Plan -> Translation Pattern -> PSTN Connection -> Route List.

Capture the ID returned by each create command -- subsequent commands need it as input.

### 6b. Handle errors

- **401/403**: Token expired or insufficient scopes -- run `wxcli configure`
- **400**: Validation error -- read the error message, common causes:
  - Invalid dial pattern syntax
  - Trunk name already exists
  - Route group references a non-existent trunk
- **404**: Referenced resource doesn't exist -- verify IDs
- **409**: Name conflict -- ask user for alternate name

## Step 7: Verify the configuration

### Verify each component was created

```bash
# Verify trunk (check status: online/offline)
wxcli call-routing show-trunks TRUNK_ID --output json

# Verify route group (check localGateways populated)
wxcli call-routing show-route-groups ROUTE_GROUP_ID --output json

# Verify dial plan (check routeId and routeType)
wxcli call-routing show-dial-plans DIAL_PLAN_ID --output json

# Verify PSTN connection
wxcli pstn list-connection LOCATION_ID --output json
```

### Test call routing end-to-end

The test call routing command simulates routing without placing an actual call:

```bash
wxcli call-routing test-call-routing \
  --originator-id PERSON_ID \
  --destination "+19195551234" \
  --json-body '{"originatorType": "USER"}'
```

> **Note:** `--originator-type` is not a CLI flag. Pass `originatorType` via `--json-body`. Both `USER` and `PEOPLE` are accepted; `PEOPLE` is preferred per OpenAPI spec.

Check the response for:
- `destinationType` -- should be `PSTN_NUMBER` for external calls
- `isRejected` -- should be `false`
- `routingAddress` -- the resolved address
- `callSourceInfo.dialPlanName` -- confirms which dial plan matched

To include translation pattern details in the test:

```bash
wxcli call-routing test-call-routing \
  --originator-id PERSON_ID \
  --destination "+19195551234" \
  --include-applied-services true \
  --json-body '{"originatorType": "USER"}'
```

## Step 8: Report results

Present the creation results:

```
ROUTING CONFIGURED
==================
Location: [location_name]

Components created:
  Trunk: [name] (ID: [trunk_id], Status: [online/offline])
  Route Group: [name] (ID: [rg_id], Trunks: [count])
  Dial Plan: [name] (ID: [dp_id], Patterns: [count])
  PSTN Connection: [type] -> [target_name]

Test Routing Result:
  +19195551234 -> PSTN_NUMBER via [trunk_name]
  Rejected: false

Next steps:
  - Monitor trunk status (should show "online" once SBC registers)
  - Add additional dial patterns as needed
  - Configure translation patterns for digit manipulation
  - Set up additional locations with PSTN connections
```

---

## Critical Rules

1. **Strict dependency order.** Create Trunk -> Route Group -> Dial Plan -> PSTN Connection. Reversing the order will fail because each component references the one before it.
2. **Always show the deployment plan** (Step 5) and wait for user confirmation before executing. Routing changes can affect live calls immediately.
3. **Dial plans require an existing trunk or route group.** You cannot create a standalone dial plan without a route choice.
4. **Trunk type, location, and device type are immutable after creation.** To change any of these, delete and recreate the trunk.
5. **Trunk updates always require name + password.** Even if you're only changing one field, both must be sent.
6. **Route groups are limited to 10 trunks** from different locations.
7. **Translation pattern E.164 replacements must use fully specified digits.** `+1919666XXXX` is rejected as a replacement pattern -- use `+19196660000` instead. `X` wildcards ARE valid in non-E.164 replacements (e.g., `9XXX` -> `XXX`).
8. **Only LOCAL_GATEWAY and NON_INTEGRATED_CCP are API-configurable** for PSTN connections. INTEGRATED_CCP and CISCO_PSTN must be configured via Control Hub.
9. **Test call routing requires a calling-enabled user as originator.** Passing a non-calling user's ID returns 404.
10. **Dial plans are org-wide, not per-location.** A dial plan applies to all users across all locations in the organization.
11. **Route group `--json-body` is required** for specifying trunks with priorities. The CLI cannot express the nested `localGateways` array as flat options.
12. **Translation patterns are outbound only.** They manipulate digits before outbound routing. They do not affect inbound call routing.
13. **Raw HTTP URL prefixes differ by component.** Dial plans/trunks/route groups/route lists use `/premisePstn/`. Translation patterns use `/callRouting/`. PSTN connections use `/telephony/pstn/`. Getting the prefix wrong returns 404. See `docs/reference/call-routing.md` for full URL tables.
14. **Production routing changes should be done off-hours.** Modifying dial plans, trunks, or PSTN connections can immediately disrupt live call routing.

---

## Scope Quick Reference

| Operation | Scope |
|-----------|-------|
| Read trunks, route groups, dial plans, route lists, translation patterns | `spark-admin:telephony_config_read` |
| Create/update/delete trunks, route groups, dial plans, route lists, translation patterns | `spark-admin:telephony_config_write` |
| Test call routing | `spark-admin:telephony_config_write` |
| Validate phone numbers | `spark-admin:telephony_config_write` |
| Read PSTN connection settings | `spark-admin:telephony_pstn_read` |
| Configure PSTN connection settings | `spark-admin:telephony_pstn_write` |

---

## Context Compaction Recovery

If context compacts mid-execution, recover by:
1. Read the deployment plan from `docs/plans/` to recover what was planned
2. Check what's already been created: run the relevant `list` commands for each component
3. Resume from the first incomplete step in the dependency chain
