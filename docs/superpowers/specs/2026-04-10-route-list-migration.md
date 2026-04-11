# Route List Migration

**Date:** 2026-04-10
**Priority:** HIGH
**Source:** API audit — calling gaps
**Status:** Spec

---

## Problem Statement

CUCM route lists are extracted via AXL discovery and normalized into `MigrationObject` records
(`canonical_id=route_list:{name}`), but the `RoutingMapper` skips them entirely during the
transform phase. When the mapper encounters a route pattern whose target is a route list, it
resolves past the route list and points the resulting `CanonicalDialPlan` directly at a
`route_group:` target (lines 516-523 of `routing_mapper.py`):

```python
# Route list -> route group mapping
# Webex doesn't have route lists; we point to the route group
rl_id = rl_refs[0]
rl_name = rl_id.split(":", 1)[-1] if ":" in rl_id else rl_id
target_id = f"route_group:{rl_name}"
route_type = "ROUTE_GROUP"
```

This comment ("Webex doesn't have route lists") is factually wrong. Webex has full route list
CRUD at `/telephony/config/premisePstn/routeLists` plus a separate numbers sub-resource at
`.../routeLists/{routeListId}/numbers`. The `call-routing.md` reference doc already documents
7 SDK methods and 7 CLI commands for route lists. The wxcli CLI has generated commands for
all route list endpoints.

### Why This Matters

Route lists wrap route groups with an ordered set of phone numbers, providing cloud PSTN
connectivity to Webex Calling Dedicated Instance. In multi-site CUCM deployments, route lists
are the mechanism for PSTN failover across geographic regions:

```
CUCM                                    Webex Calling
----                                    -------------
Route Pattern (+1408!)                  Dial Plan (pattern: +1408!)
  -> Route List (US-West-RL)              -> Route List (US-West-RL)     <-- MISSING
       -> Route Group (US-West-RG)              -> Route Group (US-West-RG)
            -> Gateway (SJ-GW)                       -> Trunk (SJ-GW)
            -> Gateway (LA-GW)                       -> Trunk (LA-GW)
       -> Route Group (US-East-RG)              [numbers: +14085551000...]
            -> Gateway (NY-GW)
```

Without route list creation, the migration:
1. Loses the number-to-route-group binding that defines which DIDs are reachable via which trunks
2. Breaks Dedicated Instance topologies that require route lists for cloud PSTN connectivity
3. Silently flattens the route list layer, making the migration appear successful while
   leaving PSTN failover unconfigured

---

## CUCM Source Data

### Already Extracted

The AXL extractor (`cucm/extractors.py`) already pulls route lists. The normalizer
(`normalizers.py`, line 1028) produces `MigrationObject` records:

```python
def normalize_route_list(raw: dict, cluster: str = "default") -> MigrationObject:
    # canonical_id = f"route_list:{name}"
    # pre_migration_state:
    #   route_list_name: str
    #   description: str | None
    #   route_groups: list[str]  (ordered route group names)
```

### Already Cross-Referenced

`CrossReferenceBuilder._build_routing_refs()` (line 593) writes:
- `route_pattern_uses_route_list` (#12) — route pattern -> route list relationship
- `route_group_to_route_list` — route group -> route list membership

### Data Shape

A CUCM route list contains:
- `name` — unique name
- `description` — optional
- `members` — ordered list of `{routeGroupName: str}` entries
- `callManagerGroupName` — redundancy group (not mapped to Webex)
- `routeListEnabled` — whether the route list is active

---

## Webex Target API

### Endpoints

All endpoints at `/telephony/config/premisePstn/routeLists`. Scope:
`spark-admin:telephony_config_read` (GET) / `spark-admin:telephony_config_write` (POST/PUT/DELETE).

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/routeLists` | List all route lists (filterable by name, locationId) |
| POST | `/routeLists` | Create route list |
| GET | `/routeLists/{routeListId}` | Get route list details |
| PUT | `/routeLists/{routeListId}` | Update route list (name, routeGroupId) |
| DELETE | `/routeLists/{routeListId}` | Delete route list |
| GET | `/routeLists/{routeListId}/numbers` | List numbers on route list |
| PUT | `/routeLists/{routeListId}/numbers` | Add/delete numbers (NumberAndAction array) |

### Create Request Body (RouteListPost)

```json
{
  "name": "US-West-Numbers",        // required
  "locationId": "Y2lzY29...",       // required — location association
  "routeGroupId": "Y2lzY29..."      // required — single route group binding
}
```

Response: `{"id": "NjA1MDA2YzMt..."}` (201 Created)

### Numbers Sub-Resource

After creation, assign numbers via PUT `.../numbers`:

```json
{
  "numbers": [
    {"number": "+14085551000", "action": "ADD"},
    {"number": "+14085551001", "action": "ADD"}
  ]
}
```

Or `{"deleteAllNumbers": true}` to clear.

### Key Constraint

A Webex route list binds to exactly ONE route group (unlike CUCM which allows multiple
route group members). CUCM route lists with multiple route groups require one of:
1. Split into N Webex route lists (one per route group member)
2. Flatten to a single route group (loses failover ordering)

This is a migration decision that the mapper must surface.

---

## Pipeline Integration

### 1. Add CanonicalRouteList Model

File: `src/wxcli/migration/models.py`

```python
class CanonicalRouteList(MigrationObject):
    """Webex route list — wraps a route group with phone number assignments."""
    name: str = ""
    location_id: str | None = None
    route_group_id: str | None = None          # canonical_id of the route group
    numbers: list[str] = Field(default_factory=list)  # E.164 numbers to assign
    cucm_route_list_name: str = ""
    cucm_route_groups: list[str] = Field(default_factory=list)  # original ordered members
```

### 2. Enhance RoutingMapper

File: `src/wxcli/migration/transform/mappers/routing_mapper.py`

Add `_map_route_lists()` method to the mapper, called after `_map_route_groups()`:

```python
def map(self, store: MigrationStore) -> MapperResult:
    result = MapperResult()
    self._map_trunks(store, result)
    self._map_route_groups(store, result)
    self._map_route_lists(store, result)       # <-- NEW
    self._map_dial_plans(store, result)
    self._map_translation_patterns(store, result)
    return result
```

**`_map_route_lists()` logic:**

For each `route_list` object in the store:
1. Read `pre_migration_state.route_groups` (ordered list of route group names)
2. If exactly 1 route group: create `CanonicalRouteList` mapping directly
3. If multiple route groups: create FEATURE_APPROXIMATION decision — options:
   - "Split into N route lists (one per route group)" — creates N objects
   - "Use first route group only (loses failover)" — creates 1 object
   - "Skip" — no route list created
4. Resolve `location_id` from the route group's trunks (via cross-ref chain:
   `route_group_has_trunk` -> `trunk_at_location` -> `device_pool_to_location`)
5. Numbers: read from `route_pattern_uses_route_list` cross-refs — collect the
   patterns that pointed at this route list and extract their associated phone
   numbers. Alternatively, store a `numbers` list on the normalized route list if
   the CUCM extractor provides route list number membership.

### 3. Fix Dial Plan Target Resolution

Current code (lines 516-523) maps route list targets to `route_group:`. Change to
map to `route_list:` when route lists are present:

```python
# BEFORE (wrong):
target_id = f"route_group:{rl_name}"
route_type = "ROUTE_GROUP"

# AFTER (correct):
target_id = f"route_list:{rl_name}"
route_type = "ROUTE_LIST"  # if Webex dial plans support route list as choice
```

**Important caveat:** Verify whether Webex dial plans accept route lists as routing
choices directly. The `RouteType` enum in the spec only has `ROUTE_GROUP` and `TRUNK`.
If dial plans cannot point to route lists, then the current behavior of pointing to the
route group is correct for the dial plan, and route lists are a standalone parallel
resource (not referenced by dial plans). In that case, the route list creation is still
needed for Dedicated Instance number assignment, but dial plans continue pointing to
route groups.

### 4. Add Planner Expander

File: `src/wxcli/migration/execute/planner.py`

```python
def _expand_route_list(obj: dict[str, Any]) -> list[MigrationOp]:
    cid = obj["canonical_id"]
    name = obj.get("name", cid)
    ops = [_op(cid, "create", "route_list", f"Create route list {name}")]
    # If numbers list is non-empty, add a configure_numbers op
    numbers = obj.get("numbers", [])
    if numbers:
        ops.append(_op(cid, "configure_numbers", "route_list",
                       f"Assign {len(numbers)} numbers to route list {name}",
                       depends_on=[f"{cid}:create"]))
    return ops
```

Register in `_EXPANDERS`:
```python
"route_list": lambda obj, _: _expand_route_list(obj),
```

### 5. Add Tier Assignment

File: `src/wxcli/migration/execute/__init__.py`

Route lists depend on route groups (tier 1) and must exist before dial plans (tier 2).
Assign to **tier 1** alongside route groups, or create a new **tier 1.5** by placing
them at tier 1 with a dependency edge to route_group:create.

```python
TIER_ASSIGNMENTS = {
    ...
    ("route_list", "create"): 1,
    ("route_list", "configure_numbers"): 1,
    ...
}

API_CALL_ESTIMATES = {
    ...
    "route_list:create": 1,
    "route_list:configure_numbers": 1,
    ...
}

ORG_WIDE_TYPES += ["route_list"]  # not location-scoped for batching
```

### 6. Add Handlers

File: `src/wxcli/migration/execute/handlers.py`

```python
def handle_route_list_create(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    # Resolve location and route group Webex IDs from deps
    loc_wid = None
    rg_wid = None
    rg_cid = data.get("route_group_id", "")
    for cid, wid in deps.items():
        if cid.startswith("location:") and wid:
            loc_wid = loc_wid or wid
        if cid == rg_cid and wid:
            rg_wid = wid
    if not loc_wid or not rg_wid:
        return []  # Missing deps — no-op
    body = {
        "name": data.get("name"),
        "locationId": loc_wid,
        "routeGroupId": rg_wid,
    }
    return [("POST", _url("/telephony/config/premisePstn/routeLists", ctx), body)]


def handle_route_list_configure_numbers(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    rl_wid = deps.get(data.get("canonical_id", ""))
    if not rl_wid:
        return []
    numbers = data.get("numbers", [])
    if not numbers:
        return []
    body = {
        "numbers": [{"number": n, "action": "ADD"} for n in numbers]
    }
    return [("PUT", _url(f"/telephony/config/premisePstn/routeLists/{rl_wid}/numbers", ctx), body)]
```

Register in `HANDLER_REGISTRY`:
```python
("route_list", "create"): handle_route_list_create,
("route_list", "configure_numbers"): handle_route_list_configure_numbers,
```

### 7. Add Dependency Rules

File: `src/wxcli/migration/execute/dependency.py`

Add cross-object dependency rules:

```python
# route_list:create REQUIRES route_group:create (the bound route group)
# route_list:create REQUIRES location:create (the associated location)
# dial_plan:create REQUIRES route_list:create (if dial plan points to route list)
```

### Dependency Chain

```
location:create          (tier 0)
    |
trunk:create             (tier 1)
    |
route_group:create       (tier 1)
    |
route_list:create        (tier 1, after route_group via dependency edge)
    |
route_list:configure_numbers  (tier 1, after create via intra-object edge)
    |
dial_plan:create         (tier 2, may reference route_list or route_group)
```

---

## Cleanup Integration

File: `src/wxcli/commands/cleanup.py`

Route lists must be deleted before route groups (reverse of creation order). Add
route list deletion as a layer in the cleanup command, between dial plans and route groups:

```
Current: dial_plans -> route_lists(MISSING) -> route_groups -> trunks
New:     dial_plans -> route_lists -> route_groups -> trunks
```

---

## Documentation Updates Required

| File | Change |
|------|--------|
| `src/wxcli/migration/models.py` | Add `CanonicalRouteList` model |
| `src/wxcli/migration/transform/mappers/routing_mapper.py` | Add `_map_route_lists()`, fix dial plan target resolution |
| `src/wxcli/migration/transform/mappers/CLAUDE.md` | Document route_list in RoutingMapper Produces list |
| `src/wxcli/migration/execute/__init__.py` | Add TIER_ASSIGNMENTS, API_CALL_ESTIMATES, ORG_WIDE_TYPES entries |
| `src/wxcli/migration/execute/planner.py` | Add `_expand_route_list`, register in `_EXPANDERS` |
| `src/wxcli/migration/execute/handlers.py` | Add `handle_route_list_create`, `handle_route_list_configure_numbers` |
| `src/wxcli/migration/execute/dependency.py` | Add cross-object rules for route_list |
| `src/wxcli/migration/execute/CLAUDE.md` | Add route_list to handler inventory (tier 1) |
| `src/wxcli/migration/transform/CLAUDE.md` | Update routing refs section |
| `src/wxcli/migration/CLAUDE.md` | Update mapper count (20 -> still 20, but RoutingMapper produces new type) |
| `src/wxcli/commands/cleanup.py` | Add route list deletion layer |
| `docs/reference/call-routing.md` | Already documented (no change needed) |
| `docs/knowledge-base/migration/kb-trunk-pstn.md` | Add route list migration guidance |
| `docs/runbooks/cucm-migration/decision-guide.md` | Add FEATURE_APPROXIMATION entry for multi-RG route lists |
| `docs/runbooks/cucm-migration/tuning-reference.md` | Add route_list config keys if any |

---

## Test Strategy

### Unit Tests

1. **Normalizer test** — verify `normalize_route_list()` produces correct canonical_id, pre_migration_state
   (already exists but verify coverage)
2. **Mapper test — single route group** — route list with 1 RG member -> 1 CanonicalRouteList, no decision
3. **Mapper test — multiple route groups** — route list with 3 RG members -> FEATURE_APPROXIMATION decision
   with split/flatten/skip options
4. **Mapper test — location resolution** — route list location derived from route group trunk chain
5. **Dial plan target test** — route pattern pointing at route list -> correct target resolution
6. **Planner test** — route_list:create and route_list:configure_numbers ops produced
7. **Handler test — create** — correct POST body with resolved locationId and routeGroupId
8. **Handler test — configure_numbers** — correct PUT body with NumberAndAction array
9. **Handler test — no deps** — returns [] when location or route group not yet created
10. **Dependency test** — route_list:create depends on route_group:create; dial_plan:create depends on route_list:create

### Integration Tests

11. **Full pipeline test** — discover -> normalize -> map -> analyze -> plan with route list data,
    verify route_list ops appear in plan with correct tier/batch ordering
12. **Cleanup test** — verify route list deletion layer runs between dial plans and route groups

### Acceptance Criteria

- Route lists with single route group members produce CanonicalRouteList objects and create/configure_numbers ops
- Route lists with multiple route group members produce a FEATURE_APPROXIMATION decision
- Dial plans that targeted route lists in CUCM correctly reference the Webex route list (or route group, per API constraint)
- End-to-end: route list appears in plan output with tier 1 assignment, dependency on route_group:create
- Cleanup deletes route lists before route groups

---

## Open Questions

1. **Can Webex dial plans reference route lists as routing choices?** The `RouteType` enum only
   shows `ROUTE_GROUP` and `TRUNK`. If not, dial plans continue pointing to route groups and
   route lists are a parallel resource for Dedicated Instance number assignment. This changes the
   dependency chain (dial_plan no longer depends on route_list).

2. **Does the AXL extractor pull route list number membership?** If CUCM stores which phone
   numbers are assigned to a route list, we need those for `configure_numbers`. If not, the
   numbers list may need to be derived from route patterns or left for manual configuration.

3. **Route list call volume tracking.** The Webex route list GET response includes
   `peakActiveRouteListCalls`, `currentActiveRouteListCalls`, `routeListCallsVolume`. These are
   read-only metrics. No migration action needed, but the assessment report could surface them
   as capacity planning data.
