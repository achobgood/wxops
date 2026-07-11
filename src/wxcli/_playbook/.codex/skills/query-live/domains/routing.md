# Routing Domain

**Covers:** Trunks, route groups, route lists, dial plans, translation patterns, PSTN connections.

**Important:** All routing commands are under the `call-routing` group. There are NO separate `trunk`, `route-group`, `route-list`, or `dial-plan` command groups.

## Question Patterns

| Pattern | Example |
|---------|---------|
| Inventory | "What trunks are configured?", "Show me all dial plans" |
| Detail | "Show me the Main trunk details", "What's in the US dial plan?" |
| Topology | "Show the full routing path", "Which route group does the Main trunk belong to?" |
| Translation | "What translation patterns are in place?" |
| PSTN | "How is PSTN connected at Austin?" |

## Command Recipes

### Trunks
```bash
wxcli call-routing list-trunks -o json
wxcli call-routing list-trunks --name "Main" -o json
wxcli call-routing show-trunks TRUNK_ID -o json
```
Show response includes: `name`, `location`, `trunkType` (REGISTERING, CERTIFICATE_BASED), `inboundCalls`, `outboundCalls`, `routeGroup`.

### Route Groups
```bash
wxcli call-routing list-route-groups -o json
wxcli call-routing show-route-groups ROUTE_GROUP_ID -o json
```
Show response includes: `name`, `localGateways` (list of trunks in the group with priority/weight).

### Route Lists
```bash
wxcli call-routing list-route-lists -o json
wxcli call-routing show-route-lists ROUTE_LIST_ID -o json
```
Show response includes: `name`, `routeGroup` references, `locationId`.

### Dial Plans
```bash
wxcli call-routing list-dial-plans -o json
wxcli call-routing list-dial-plans --dial-plan-name "International" -o json
wxcli call-routing show-dial-plans DIAL_PLAN_ID -o json
```
Show response includes: `name`, `routeType` (ROUTE_LIST or ROUTE_GROUP), `routeId`, `dialPatterns`.

### Translation Patterns
```bash
wxcli call-routing list-translation-patterns -o json
wxcli call-routing list-translation-patterns --name "Emergency" -o json
wxcli call-routing list-translation-patterns --matching-pattern "+1911" -o json
wxcli call-routing show-translation-patterns-call-routing TRANSLATION_ID -o json
```

### PSTN Connection
```bash
wxcli pstn list LOCATION_ID -o json
```

### Test Call Routing
```bash
wxcli call-routing test-call-routing --originator-id PERSON_ID --originator-type PEOPLE --destination "+15125551234" -o json
```
Tests how a dialed number would be routed. Useful for "what happens if I dial...?" questions. `--originator-type` accepts `PEOPLE` or `TRUNK`. This is a POST but does not modify state — it's a read-only simulation.

## Join Patterns

**Topology query** ("Show the full routing path"):
Build the tree bottom-up:
1. `wxcli call-routing list-trunks -o json` → all trunks
2. `wxcli call-routing list-route-groups -o json` → all route groups (each references its trunks)
3. `wxcli call-routing list-route-lists -o json` → all route lists (each references its route groups)
4. `wxcli call-routing list-dial-plans -o json` → all dial plans (each references a route list or route group)

Present as a tree:
```
Dial Plan: US Domestic
  └─ Route List: US Routes
       └─ Route Group: Primary RG
            ├─ Trunk: Austin SBC (priority 1)
            └─ Trunk: Denver SBC (priority 2)

Dial Plan: International
  └─ Route Group: International RG
       └─ Trunk: Cloud PSTN
```

**Trunk membership query** ("Which route group does Main trunk belong to?"):
1. `wxcli call-routing list-route-groups -o json`
2. For each route group, check its `localGateways` list for the trunk name/ID
3. Report all route groups that contain the trunk

## Response Guidance

**Inventory query** ("What trunks are configured?"):
```
3 trunks configured:
  - Austin SBC (Registering, Austin location)
  - Denver SBC (Registering, Denver location)
  - Cloud PSTN (Certificate-based, no location)
```

**Detail query** ("Show me the US dial plan"):
```
US Domestic Dial Plan:
  Route type: Route List
  Route list: US Routes
  Dial patterns:
    - +1[2-9]XXXXXXXXX (US/Canada)
    - 1[2-9]XXXXXXXXX
    - [2-9]XXXXXXXXX (10-digit)
```

**Topology query** (full tree): See Join Patterns above for the tree format.

## Gotchas

1. **All commands are under `call-routing`.** Do NOT use `wxcli trunk`, `wxcli route-group`, etc. — those groups don't exist. Use `wxcli call-routing list-trunks`, `wxcli call-routing show-trunks`, etc.
2. **Dial plan show includes patterns inline.** No separate "list patterns" command needed — they're in the show response.
3. **Route groups reference trunks by ID.** To show trunk names in a route group view, you need to cross-reference with the trunk list.
4. **Translation patterns support `--name` and `--matching-pattern` server-side filters.** For other criteria, filter client-side. The show command has a generator-artifact suffix: `show-translation-patterns-call-routing` (not `show-translation-patterns`).
5. **PSTN list is location-scoped.** Must pass a location ID. For org-wide PSTN view, enumerate all locations.
