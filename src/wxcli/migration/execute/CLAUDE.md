# execute/ — CUCM Migration Execution Layer

Translates canonical objects from the SQLite store into API operations and executes them. The module has two execution paths: **bulk async** (engine.py calls Webex APIs directly) and **skill-delegated** (cucm-migrate skill reads the plan and delegates to domain skills). Both paths use the same plan tables and handler functions.

## File Map

| File | Purpose |
|------|---------|
| `__init__.py` | Constants: `TIER_ASSIGNMENTS`, `API_CALL_ESTIMATES`, `ORG_WIDE_TYPES`. Models: `MigrationOp`, `Batch`, `BrokenCycle`, `DependencyType` |
| `handlers.py` | Pure-function handlers: `(data, deps, ctx) → HandlerResult`. `HANDLER_REGISTRY` maps `(resource_type, op_type)` to handler. |
| `planner.py` | `expand_to_operations(store)` — turns analyzed canonical objects into `MigrationOp` nodes |
| `dependency.py` | `build_dependency_graph(ops, store)` — NetworkX DAG with intra-object and cross-object edges, cycle detection/breaking |
| `batch.py` | `partition_into_batches(G)` — org-wide → per-site → fixups, split by tier. SQLite persistence: `save_plan_to_store`, `load_plan_from_store` |
| `runtime.py` | `get_next_batch(store)`, `update_op_status()`, `dry_run_all_batches()`, `get_execution_progress()`. Used by the cucm-migrate skill. |
| `engine.py` | `execute_all_batches()` — async aiohttp bulk executor with semaphore rate-limiting, 429 retry, 409 auto-recovery |

---

## Tier System

Operations run in tier order. Within a tier, all operations in the same (batch, tier) group execute concurrently.

| Tier | What runs | Key types |
|------|-----------|-----------|
| 0 | Infrastructure | location:create, location:enable_calling |
| 1 | Routing backbone + org-wide | trunk, route_group, operating_mode, schedule, line_key_template |
| 2 | People + org-wide routing | user:create, workspace:create, dial_plan, translation_pattern |
| 3 | Numbers + devices | workspace:assign_number, device:create |
| 4 | Call features | hunt_group, call_queue, auto_attendant, call_park, pickup_group, paging_group |
| 5 | Settings | user:configure_settings, user:configure_voicemail, device:configure_settings, workspace:configure_settings, calling_permission:assign, call_forwarding:configure |
| 6 | Shared/virtual lines + monitoring | shared_line:configure, virtual_line:create/configure, monitoring_list:configure |
| 7 | Device finalization + cycle fixups | device_layout:configure, softkey_config:configure, fixup ops from cycle breaking |
| 8 | Bulk phone rebuild | bulk_rebuild_phones:submit |
| 9 | Membership reconcile | hunt_group/call_queue/pickup_group/paging_group:reconcile_members |

**Tier 7 dual use:** Cycle-break fixups use `batch="fixups"`; device finalization ops use location-derived batches. They don't conflict because they land in separate batch groups.

---

## Membership Reconcile (tier 9)

`reconcile_members` is what makes the `proceed_partial` answer to a
`CROSS_SITE_DEPENDENCY` honest. The group is still created in wave 1 with whichever
members exist; this op rewrites the **full** membership on the wave that provisions the
last remote member.

One handler, `handle_reconcile_members`, serves all four group types. Behaviour comes
from `RECONCILE_RULES` in `handlers.py` — endpoint path, which canonical fields hold
members, and whether the API wants `{"id": ...}` objects or bare id strings. Adding
voicemail groups or DECT handsets later is a new row, not a new handler.

| Resource | Endpoint | Members |
|----------|----------|---------|
| `hunt_group` | PUT `.../locations/{loc}/huntGroups/{id}` | `agents: [{"id": ...}]` |
| `call_queue` | PUT `.../locations/{loc}/queues/{id}` | `agents: [{"id": ...}]` |
| `pickup_group` | PUT `.../locations/{loc}/callPickups/{id}` | `agents: ["id", ...]` |
| `paging_group` | PUT `.../locations/{loc}/paging/{id}` | `targets` / `originators`, flat strings |

**It never writes a partial list.** These endpoints replace the whole array, so a short
list would *delete* members rather than add them — including any an operator added by
hand. If a single member is unresolved the handler returns `skipped(reason)` and the
existing membership is left untouched. This is the single most important behaviour of
the op; `test_skipped_result_issues_no_api_call` guards it directly.

**Why tier 9 and not a second batch inside tier 8.** It has to be the last thing that
touches a group, and tier 8 is already occupied by `bulk_rebuild_phones`. Sharing tier 8
would make the ordering depend on how batch groups happen to be constructed rather than
on the tier number, which is the mechanism everything else in the plan relies on.

**How it waits.** Hard `REQUIRES` edges to every member's `user:create`, from four rows
in `_CROSS_OBJECT_RULES` keyed on the `feature_has_agent` cross-ref. The op simply never
becomes ready until the last member exists — across separate wave runs it stays pending
and executes on the final one. There is no wave-tracking state. `REQUIRES` rather than
`CONFIGURES` because cycle-breaking prefers to break weaker edge types, and this edge
must not be broken.

The `create` op keeps its **SOFT** member edges, untouched. Making those hard would
reintroduce "no hunt group at all", which is worse than partial membership.

Paging groups previously had no `feature_has_agent` cross-ref at all — `FeatureMapper`
now writes one for targets and originators (`_link_paging_members`). No SOFT rule was
paired with it, so `paging_group:create` behaviour is unchanged.

**Retry.** The group's Webex id comes from `deps`, which the runtime builds from
`plan_operations.webex_id` — so it resolves even when the `create` op ran in an earlier
run and this plan contains only the reconcile op. If it cannot be resolved, the op skips
rather than blindly creating a duplicate group. Renaming is deliberately unsupported: a
Call Pickup group's id changes when its name changes, which would invalidate `webex_id`.

---

## Handler Pattern

Every handler in `handlers.py` is a pure function with this signature:

```python
HandlerResult = list[tuple[str, str, dict | None]] | SkippedResult

def handle_foo_bar(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    ...
```

- `data` — canonical object dict from the store (object's full JSON)
- `deps` — `{canonical_id: webex_id}` for all completed dependency operations
- `ctx` — session context: `{"orgId": "...", "CALLING_LICENSE_ID": "...", ...}`
- Returns one of:
  - **`list[tuple[str, str, dict | None]]`** — API calls to execute sequentially by the engine
  - **`[]`** — legitimate no-op (feature disabled by design, no config needed). Engine marks op `completed` with no API call.
  - **`skipped(reason)`** — required upstream dependency not resolved. Engine marks op `skipped` with `error_message=reason` and cascades to dependents. Use when a webex_id from `deps` is missing where one was expected.
- `_url(path, ctx)` — always use this instead of building URLs manually. It injects `?orgId=...` automatically when ctx has orgId.

### When to return `[]` vs `skipped(reason)`

| Scenario | Return |
|---|---|
| `if not feature.enabled: ...` | `[]` |
| `if not settings: ...` (empty optional config) | `[]` |
| `if not deps.get(upstream_cid): ...` | `skipped(f"{upstream_cid} not resolved")` |
| `if not _resolve_location(data, deps): ...` | `skipped(f"location not resolved for {name}")` |
| MOH / announcement placeholders (Phase A) | `[]` with explicit comment — do not convert |

The runtime (`runtime.py`) and engine both intercept `SkippedResult`:
- `engine.py::run_batch_ops` calls `update_op_status(..., 'skipped', error_message=reason)` and cascades skip to dependents (see Fix #10).
- `engine.py::_run_per_device_fallback` treats a handler returning `SkippedResult` during bulk fallback as a per-device failure, recording the reason without iterating the sentinel (see Finding #8).

### Resolving dependencies

Handlers resolve Webex IDs from `deps` by canonical_id:

```python
# Direct lookup
person_wid = deps.get(data.get("user_canonical_id", ""))

# Prefix search (when the canonical_id isn't in data)
loc_wid = next((wid for cid, wid in deps.items() if cid.startswith("location:")), None)

# Silently omit unresolved members (partial resolution is valid, but log a warning):
resolved_members = [{"id": deps[cid]} for cid in member_cids if cid in deps]
unresolved = [cid for cid in member_cids if cid not in deps]
if unresolved:
    logger.warning(
        "Handler X: %d of %d members unresolved: %s",
        len(unresolved), len(member_cids), unresolved,
    )
# If ALL members unresolved AND members are required, return skipped(...) instead.
```

---

## Handler Inventory

All 67 handler functions, across 70 `HANDLER_REGISTRY` entries (the four
`reconcile_members` keys share one function — see Membership Reconcile above):

### Tier 0 — Infrastructure
| Key | URL | Notes |
|-----|-----|-------|
| `(location, create)` | POST `/locations` | |
| `(location, enable_calling)` | POST `/telephony/config/locations` | Separate from create — Fix 13 |

### Tier 1 — Routing + Org-Wide
| Key | URL | Notes |
|-----|-----|-------|
| `(trunk, create)` | POST `/telephony/config/premisePstn/trunks` | |
| `(route_group, create)` | POST `/telephony/config/premisePstn/routeGroups` | Resolves trunk deps |
| `(route_list, create)` | POST `/telephony/config/premisePstn/routeLists` | Resolves route group + location deps |
| `(route_list, configure_numbers)` | PUT `/telephony/config/premisePstn/routeLists/{id}/numbers` | NumberAndAction array |
| `(operating_mode, create)` | POST `/telephony/config/operatingModes` | |
| `(schedule, create)` | POST `/telephony/config/locations/{loc}/schedules` | |
| `(line_key_template, create)` | POST `/telephony/config/devices/lineKeyTemplates` | Filters UNMAPPED keys |
| `(device_settings_template, apply_location_settings)` | PUT `/telephony/config/locations/{id}/devices/settings` | Apply device settings at location level |

### Tier 2-3 — People + Devices
| Key | URL | Notes |
|-----|-----|-------|
| `(user, create)` | POST `/people?callingData=true` | Injects CALLING_LICENSE_ID from ctx |
| `(workspace, create)` | POST `/workspaces` | Injects WORKSPACE_LICENSE_ID from ctx |
| `(workspace, assign_number)` | PUT `/workspaces/{id}` | Returns `[]` if no DID needed |
| `(device, create)` | POST `/devices` | Sets personId or workspaceId from owner_canonical_id prefix |
| `(device, create_activation_code)` | POST `/devices/activationCode` | For CONVERTIBLE phones only; drops MAC, normalizes model to `DMS <name>` format, sets personId/workspaceId from owner prefix |
| `(dial_plan, create)` | POST `/telephony/config/premisePstn/dialPlans` | |
| `(translation_pattern, create)` | POST `/telephony/config/callRouting/translationPatterns` | |

### Tier 2-3 — DECT Networks
| Key | URL | Notes |
|-----|-----|-------|
| `(dect_network, create)` | POST `/telephony/config/locations/{loc}/dectNetworks` | Returns `dectNetworkId` in response. Requires base station MAC inventory for full fidelity. |
| `(dect_network, create_base_stations)` | POST `/telephony/config/locations/{loc}/dectNetworks/{id}/baseStations` | Registers MAC addresses from base station inventory. Returns `[]` (no-op) if no base stations in data. |
| `(dect_network, assign_handsets)` | POST `/telephony/config/locations/{loc}/dectNetworks/{id}/handsets/bulk` | Batches handset assignments (max 50 per request). Returns `[]` if no handsets. |

### Tier 4 — Call Features
| Key | URL | Notes |
|-----|-----|-------|
| `(hunt_group, create)` | POST `/telephony/config/locations/{loc}/huntGroups` | |
| `(call_queue, create)` | POST `/telephony/config/locations/{loc}/queues` | |
| `(auto_attendant, create)` | POST `/telephony/config/locations/{loc}/autoAttendants` | |
| `(call_park, create)` | POST `/telephony/config/locations/{loc}/callParks` | |
| `(pickup_group, create)` | POST `/telephony/config/locations/{loc}/callPickups` | Agents as plain string array, not `{"id": ...}` |
| `(paging_group, create)` | POST `/telephony/config/locations/{loc}/paging` | No location_id field — resolves from deps prefix |

### Tier 5 — Settings
| Key | URL | Notes |
|-----|-----|-------|
| `(user, configure_settings)` | PUT `/people/{id}/features/{feature}` | One call per feature in call_settings dict |
| `(user, configure_voicemail)` | PUT `/telephony/config/people/{id}/voicemail` | |
| `(device, configure_settings)` | PUT `/telephony/config/devices/{id}/settings` | Returns `[]` if no settings |
| `(workspace, configure_settings)` | PUT `/telephony/config/workspaces/{id}/{feature}` | One call per feature in call_settings dict (DND + MOH work on both tiers; others require Professional Workspace) |
| `(calling_permission, assign)` | PUT `/people/{id}/features/outgoingPermission` | One call per user in assigned_users |
| `(call_forwarding, configure)` | PUT `/people/{id}/features/callForwarding` | Returns `[]` if all forwarding types disabled |
| `(hunt_group, configure_forwarding)` | PUT `/telephony/config/locations/{loc}/huntGroups/{id}/callForwarding` | Returns `[]` if no forwarding fields set or feature/location not yet created |
| `(call_queue, configure_forwarding)` | PUT `/telephony/config/locations/{loc}/queues/{id}/callForwarding` | Maps queue_full_destination → callForwarding.always |
| `(call_queue, configure_holiday_service)` | PUT `/telephony/config/locations/{loc}/queues/{id}/holidayService` | References schedule by name + level |
| `(call_queue, configure_night_service)` | PUT `/telephony/config/locations/{loc}/queues/{id}/nightService` | References business hours by name + level |
| `(call_queue, configure_stranded_calls)` | PUT `/telephony/config/locations/{loc}/queues/{id}/strandedCalls` | TRANSFER action, transferPhoneNumber from no_agent_destination |
| `(auto_attendant, configure_forwarding)` | PUT `/telephony/config/locations/{loc}/autoAttendants/{id}/callForwarding` | Always-forward only |
| `(device_settings_template, apply_device_override)` | PUT `/telephony/config/devices/{id}/settings` | Apply per-device settings override |
| `(device_profile, enable_hoteling_guest)` | PUT `/people/{id}/features/hoteling` | Enables EM-subscribed user as hoteling guest |
| `(device_profile, enable_hoteling_host)` | PUT `/telephony/config/people/{id}/devices/settings/hoteling` | Configures EM-enabled device as hoteling host (no-op when host data unavailable) |
| `(ecbn_config, configure)` | PUT `/telephony/config/{people|workspaces|virtualLines}/{id}/emergencyCallbackNumber` | Configures per-entity ECBN selection |

### Tier 0 — Hoteling location (voice portal sign-in)
| Key | URL | Notes |
|-----|-----|-------|
| `(hoteling_location, enable_hotdesking)` | PUT `/telephony/config/locations/{id}/features/hotDesking` | Enables voice portal hot desk sign-in at locations with EM phones |

### Advisory-to-execution bridge (Phase A: no-op placeholders)

These handlers exist so the planner no longer logs `No expansion pattern` warnings
for types that the transform/mappers layer emits. They are deliberate no-ops that
return `[]` — the engine marks the op completed without making any API call.
Phase B will add real per-location MOH configuration and multipart announcement
upload once `execute/engine.py` gains `aiohttp.FormData` support.

| Key | URL | Notes |
|-----|-----|-------|
| `(music_on_hold, configure)` | — | Returns `[]`. Phase A visibility placeholder — MOHMapper's `AUDIO_ASSET_MANUAL` decisions still gate custom audio. |
| `(announcement, upload)` | — | Returns `[]`. Phase A visibility placeholder — AnnouncementMapper creates `AUDIO_ASSET_MANUAL` decisions for all announcements. |

`e911_config` is NOT in this list — it is in `_DATA_ONLY_TYPES` in `planner.py`
because ECBN per-user configuration belongs in `user:configure_settings` and
RedSky civic addresses are a separate workstream. The `E911Mapper`'s
`ARCHITECTURE_ADVISORY` decisions are the operator-facing surface for E911.

`location_schedule` is NOT in this list — `CanonicalLocationSchedule` uses the
canonical_id prefix `schedule:` (from `feature_mapper._map_location_schedules`),
so `cid.split(":")[0]` resolves to `"schedule"` and the existing
`_expand_schedule` + `handle_schedule_create` handle it with no new code.

`device_profile` is NOT in this list — it was fully wired by the hoteling
migration work (see "Tier 5 — Settings" above for `enable_hoteling_guest` and
`enable_hoteling_host`, plus "Tier 0 — Hoteling location").

### Tier 6 — Shared/Virtual Lines + Monitoring
| Key | URL | Notes |
|-----|-----|-------|
| `(shared_line, configure)` | PUT `/telephony/config/people/{id}/applications/members` × N owners | Configures person-level app shared call appearance for each owner. When `SHARED_LINE_COMPLEX` is resolved `virtual_line`, the planner emits `virtual_line:create` + `configure` instead — see below |
| `(virtual_line, create)` | POST `/telephony/config/virtualLines` | |
| `(virtual_line, configure)` | PUT `/telephony/config/virtualLines/{id}` | Returns `[]` if no settings |
| `(monitoring_list, configure)` | PUT `/people/{id}/features/monitoring` | Returns `[]` if no resolved members; silently omits unresolved |

### Tier 7 — Device Finalization
| Key | Calls | Notes |
|-----|-------|-------|
| `(device_layout, configure)` | 2-3 calls | Call 1 (conditional): PUT `/telephony/config/devices/{id}/members`; Call 2: PUT `.../layout`; Call 3: POST `.../actions/applyChanges/invoke` with body=None |
| `(softkey_config, configure)` | 2 calls | Returns `[]` if `is_psk_target=False`. Call 1: PUT `.../dynamicSettings`; Call 2: POST `.../actions/applyChanges/invoke` |

---

## Planner — expand_to_operations()

`planner.py:expand_to_operations(store)` reads all `status='analyzed'` objects and calls the matching `_EXPANDERS[obj_type](obj_data, decisions)` function. Returns `list[MigrationOp]`.

**Cross-site gate (the only pending-decision block).** An unresolved
`CROSS_SITE_DEPENDENCY` decision suppresses expansion of its construct and records
`reason="cross_site_unreviewed"` (`decision_state="pending"`) in the skip report, which
trips `plan --fail-on-unresolved`. Every other decision type only gates on a *resolved*
`skip`. The gate is scoped by `context["construct_id"] == canonical_id`: a cross-site
decision also lists its remote members in `affected_objects` so the report can link them,
and gating those would block provisioning real users. `CROSS_SITE_DEPENDENCY` is
deliberately NOT in `_SKIP_DECISION_TYPES` for the same reason — its `skip` choice is
handled inside the construct-scoped gate.

**Cross-site location reassignment (`reassign_home`).** `wxcli cucm decide` stores whatever
the operator typed, so a `CROSS_SITE_DEPENDENCY` resolved with a *location canonical_id*
means "build the construct there instead". `_cross_site_location_choice()` recognises this
(the choice must be in `_location_canonical_ids(store)` — the four literal option ids are
not), and the expansion loop patches the object's location field before calling the expander,
so the construct lands in that location's batch. Two things distinguish it from the
`LOCATION_AMBIGUOUS` patch immediately above it in the loop:

1. It **overrides** an existing location; the `LOCATION_AMBIGUOUS` patch only fills a gap
   (`and not obj_data.get("location_id")`).
2. The field name is resolved through `_LOCATION_FIELDS` (imported from
   `transform/analyzers/cross_site.py`) rather than hardcoded — it is `location_id` on some
   canonical types and `location_canonical_id` on others. Types with neither field are
   patched in memory only under `location_id`: that still moves `paging_group` (its expander
   reads `location_id`) but is inert for the relationship constructs whose expanders emit
   `batch=None` by design — `monitoring_list`, `executive_assistant`, `call_forwarding`,
   `device_layout`. Those inherit their owner's location, so "build it at location X" has
   nothing to move; the operator's remedy there is `migrate_together` or `skip`.

Scoped to `context["construct_id"] == canonical_id`, so resolving a construct's decision
never relocates the remote members it also lists in `affected_objects`. The move is logged at
INFO with old → new because it changes which wave the construct executes in.

**Skip logic (two kinds):**
1. **Generic skip** — any object with a `_SKIP_DECISION_TYPES` decision resolved as "skip" is suppressed entirely. Types: `DEVICE_INCOMPATIBLE`, `EXTENSION_CONFLICT`, `LOCATION_AMBIGUOUS`, `MISSING_DATA`, `WORKSPACE_LICENSE_TIER`, `DUPLICATE_USER`, `VOICEMAIL_INCOMPATIBLE`. (`DEVICE_FIRMWARE_CONVERTIBLE` was removed 2026-04-15 — convertible devices auto-convert and always emit a `create_activation_code` op.)
2. **Per-expander skip** — individual expanders have their own skip logic (e.g., `_expand_call_forwarding` returns `[]` if all forwarding types disabled; `_expand_line_key_template` returns `[]` if `phones_using == 0`; `_expand_softkey_config` returns `[]` if `is_psk_target=False`).

**`virtual_line` from a shared line.** No `CanonicalVirtualLine` object is ever produced
by the pipeline, so `_expand_shared_line` used to return `[]` when the operator chose
`virtual_line` — the choice silently built nothing. It now emits `virtual_line:create` +
`configure` directly from the shared-line object. Building the canonical objects in a new
pipeline stage would be wrong: `SHARED_LINE_COMPLEX` is resolved *after* analyze, so the
planner is the only place that knows the answer.

`CanonicalSharedLine` has no extension, location, or display name, so the ops carry a
`payload` (extension parsed from `dn_canonical_id`, location resolved from the owners via
`resolve_entity_location`). `runtime.get_next_batch` prefers an inline payload over the
store lookup, so the handler receives virtual-line shaped data even though the op's
`canonical_id` points at a shared line. A shared line with no resolvable DN records
`virtual_line_no_extension` in the skip report rather than POSTing a body with no
extension. `_expand_shared_line` is one of two expanders that receive the store (the other
is `_expand_device`, which takes `config`).

**Data-only types** (no operations produced): `line` (consumed by user:create), `voicemail_profile` (consumed by user:configure_voicemail).

**Node IDs**: format is `"canonical_id:op_type"` — parse back with `rsplit(":", 1)` (canonical_id can contain colons).

---

## Dependency Graph

`dependency.py:build_dependency_graph(ops, store)` builds a NetworkX DiGraph.

**Edge types** (`DependencyType` enum):
- `REQUIRES` — hard: predecessor must be completed before successor can start. Failure cascades skip.
- `CONFIGURES` — hard: same blocking behavior, used for intra-object sequencing.
- `SOFT` — non-blocking: successor proceeds even if predecessor failed/skipped. Used for agent memberships in hunt groups/queues (circular dependency safety valve).

**Two edge sources:**
1. **Intra-object** — from `depends_on` field set by expanders (e.g., `configure_settings` depends on `create` for the same object).
2. **Cross-object** — from `_CROSS_OBJECT_RULES` (30 rules) queried against store cross_refs. Examples: device:create requires its owner user:create; monitoring_list:configure requires each monitored target's create (SOFT); hunt_group/call_queue:configure_forwarding requires voicemail_group:create when forwarding to a VM group extension (cross-ref `feature_forwards_to_voicemail_group` written by FeatureMapper).

**Cycle breaking:**
- All-REQUIRES cycle → hard error (unbreakable — needs human decision).
- Mixed/SOFT cycle → break weakest edge (prefer SOFT, then CONFIGURES) → create tier 7 fixup node in `batch="fixups"`.

---

## Runtime — get_next_batch()

`runtime.py:get_next_batch(store)` returns ops whose hard deps are all `completed` or `skipped`. Returns the lowest (tier, batch) group. Used by both the cucm-migrate skill and the engine.

**Cascade skip on failure:** When an op fails, all ops that depend on it via hard edges are recursively set to `skipped`. This prevents orphaned operations from waiting forever.

**Undo cascade on retry:** If a previously-failed op succeeds on retry, its cascade-skipped dependents are reset to `pending` so they execute in the next batch.

**dry_run_all_batches()** — uses a SQLite SAVEPOINT to simulate full execution without state changes. Useful for previewing the execution plan.

---

## Engine — execute_all_batches()

`engine.py:execute_all_batches(store, token, concurrency=20, ctx, on_progress)` is the async bulk executor.

- Each batch: all ops run concurrently via `asyncio.gather()`, bounded by a semaphore (`concurrency=20` by default).
- **429 handling** — backs off by `Retry-After` header value, retries up to `MAX_RETRIES=5` times.
- **409 handling** — auto-recovery: searches for the existing resource by name/email and uses its ID. Supported for: user, location, translation_pattern, trunk, dial_plan, operating_mode, schedule. Other types cascade-fail.
- **Multi-call ops** — sequential: the engine iterates `calls` in order. First call's response `id` becomes the `webex_id`. Any sub-call failure fails the whole op.
- Handler returning `[]` → op marked `completed` with no API call.
- No handler in registry → op marked `failed` immediately.

### `wxcli cucm execute` exits 0 even with `Failed: N` — decided, not overlooked (2026-07-29)

`execute()` in `commands/cucm.py` prints `Completed: N` / `Failed: N`, prints a tip
pointing at `execution-status`, and returns normally. **Partial failure is not an
error exit here, and that is the decision** — recorded because the same audit round
fixed the opposite call on `cucm preflight`, and the difference is not obvious from
either command's code.

**Nothing reads this exit code.** Measured over both callers, not assumed:

- `.claude/skills/cucm-migrate/SKILL.md` step 4 runs `wxcli cucm execution-status
  -o json` and branches on its **content** — "IF all completed → deliverables",
  "IF failures exist → triage per operation". No `$?`, no `&&`, no `set -e`.
- `docs/runbooks/cucm-migration/operator-runbook.md` says it outright: Claude
  "re-enters only when the skill checks `execution-status` and finds failures".

**Why non-zero would be wrong, not merely unnecessary.** The documented recovery
loop is `retry-failed` → `execute` → "repeat until execution-status shows 0 failed,
0 pending". A partially-failed run is the *expected* mid-migration state, and the
prescribed next step is to run the same command again. Exiting non-zero on it would
make the first `execute` of a normal multi-pass migration kill any future `set -e`
wrapper around the loop the runbook tells operators to run. "Exit non-zero only when
zero operations succeeded" has the same hazard, just rarer: a retry pass where every
retried op fails again for a new reason is still a legitimate iteration.

**Why `preflight` is genuinely different.** It is a pre-execution gate whose entire
output is a verdict, and the skill calls it MANDATORY, NOT SKIPPABLE with "if ANY
check fails, do NOT proceed to execution". A gate that prints `Overall: ✗ FAIL` and
exits 0 is a broken gate. `execute` is not a gate; it is a resumable worker whose
verdict lives in the store, where `execution-status` reads it.

**Correction to a round-3 note.** `PHASE-3-RESULTS.md` records that "`plan` and
`analyze` share the shape". Checked against source: **`analyze` does** (a per-analyzer
`count == -1` prints `FAILED` in red and the command still exits 0), but **`plan` does
not** — it already carries `--fail-on-unresolved` plus a
`WXCLI_PLAN_FAIL_ON_UNRESOLVED=1` env var that exits **2** when entities are dropped
for unresolved decisions, i.e. the "should partial failure be fatal?" question was
already answered there with a declared opt-in. `plan` retains the shape only for
`cycle_errors` and tier violations, which print red and continue. So the in-group
precedent is *opt-in*, never default-throw.

**Rejected: adding `execute --fail-on-failures`** for symmetry with `plan`. `plan`'s
flag exists because a real caller wanted it; no caller gates on `execute` at all, and
a CLI flag with no consumer is surface added on speculation. Add it the day something
scripts around `execute` — the store already has the data it would read.

## Adding a New Handler

1. Add the pure function to `handlers.py` in the appropriate tier section.
2. Add the entry to `HANDLER_REGISTRY`: `("resource_type", "op_type"): handle_fn`.
3. Add to `TIER_ASSIGNMENTS` in `__init__.py`: `("resource_type", "op_type"): tier`.
4. Add to `API_CALL_ESTIMATES` in `__init__.py`: `"resource_type:op_type": N`.
5. Add expansion logic to `planner.py`: `_expand_*()` function + `_EXPANDERS` entry.
6. If the new type has cross-object dependencies, add rules to `_CROSS_OBJECT_RULES` in `dependency.py`.
7. Write TDD tests in `tests/migration/execute/test_handlers.py`.

---

## Key Gotchas

- **`SkippedResult` sentinel + `skipped(reason)` helper** — `handlers.py` exports both. `SkippedResult(reason=...)` is a frozen dataclass returned in place of a `[(method, url, body)]` list when a required upstream dep is missing. `skipped(reason)` is the one-liner factory. The engine detects the sentinel via `isinstance(calls, SkippedResult)` and routes the op to `update_op_status(..., 'skipped', error_message=reason)` so the operator can see cascades separately from genuine FAILED ops. Never return `SkippedResult` from a no-op — return `[]` instead (legitimate no-ops don't block dependents from running).
- **`_url()` always handles orgId** — never build query strings manually in handlers.
- **Picking owner from deps**: `owner_canonical_id` prefix determines `personId` vs `workspaceId` in device:create. Use `cid.startswith("user:")` / `"workspace:"`.
- **Pickup group + paging group agents** — these APIs take plain string arrays, not `[{"id": ...}]`. Hunt group and call queue take the object format.
- **Paging group has no `location_id`** — use `_resolve_location_from_deps()` fallback.
- **`calling_permission:create` has 0 API calls** — `TestHandlerRegistry` skips it. No handler needed. The `assign` op does the actual work.
- **`device_layout:configure` returns 2 or 3 tuples** depending on whether `line_members` resolves to anything. Engine handles both — it just iterates `calls`.
- **`softkey_config:configure` for template-level objects** — `is_psk_target=False` objects return `[]` → auto-completed. Only per-device objects (`is_psk_target=True`) produce API calls.
- **PSK slot lowercasing** — `"PSK1"` → `"psk1"` for the `softKeyLayout.psk.psk1` key.
- **`ringOut` → `progressing`** — CUCM state "ringOut" maps to Webex state "progressing", producing key `softKeyLayout.softKeyMenu.progressingKeyList`. Not "processing".
- **Tier 7 dual use** — cycle-break fixups (`batch="fixups"`) and device finalization ops (location-derived batch) both use tier 7. No conflict — different batch values → different batch groups in the executor.
- **location:create ≠ enabling Webex Calling** — creating a location via POST /locations does NOT enable calling on it. A separate POST /telephony/config/locations is required (Fix 13). Both are tier 0.
- **`line_key_template` — SPEED_DIAL without value → Error 27650** — The lineKeyTemplates API rejects `SPEED_DIAL` keys with no `lineKeyValue` (Error 27650). The handler converts valueless `SPEED_DIAL` keys to `OPEN` (template-level placeholder). Only include `SPEED_DIAL` in a template when you have a real number/extension to assign.
- **`line_key_template` — PhoneOS model names** — The ButtonTemplateMapper stores `"DMS Cisco {model}"` for all phones, but PhoneOS phones (9811/9821/9841/9851/9861/9871/8875) require `"Cisco {model}"` in the lineKeyTemplates API. The handler remaps these at execution time.
- **`line_key_template` — 9861 KEM overflow in line_keys** — The ButtonTemplateMapper places all button indices (1-130 for a 9861) into `line_keys`. But the 9861 only has 10 physical line keys; indices 11+ belong to the KEM. The handler splits `line_keys` at `phoneos_max` (10 for 9861) and re-indexes the overflow as `kemKeys` starting at 1.
- **`line_key_template` — no model → skip** — Templates for CUCM-only devices (Standard Analog, ATA 191, Client Services Framework) have `device_model=None` because no Webex equivalent exists. The handler returns `[]` (no-op) for these — they auto-complete without making an API call.
- **`operating_mode` — field is `type` not `scheduleType`** — The POST body must use `"type"` not `"scheduleType"` for the schedule type field. The GET response also uses `"type"`.
- **`operating_mode` — `sameHoursDaily` format** — Canonical stores `{startTime, endTime}`, but the API requires `{mondayToFriday: {enabled, allDayEnabled, startTime?, endTime?}, saturdayToSunday: ...}`. The handler converts automatically.
- **`operating_mode` — `differentHoursDaily` format** — Canonical stores `{day_0: {startTime, endTime}, ...}` (numeric keys). API uses `{monday: {enabled, allDayEnabled, startTime?, endTime?}, ...}` (day names). The handler maps `day_N` → day name.
- **`operating_mode` — 409 auto-recovery** — If an operating mode with the same name already exists, the engine searches by name and uses the existing ID.
- **`device:create_activation_code` vs `device:create`** — firmware-convertible phones (7800/8800-series eligible for E2M conversion) take the activation-code path instead of MAC-based creation. As of 2026-04-15, the planner picks between the two purely on `compatibility_tier == "convertible"` — convertible devices unconditionally emit a `create_activation_code` op with no decision gating, no option, and no skip path (if a device is convertible, it converts). The `DEVICE_FIRMWARE_CONVERTIBLE` decision type is retained in the enum for backward compatibility with pre-2026-04-15 project stores, but no code path emits it for new runs. The activation code string lands in `plan_operations.webex_id` because the engine falls back to `resp_body.get("code")` when no `id` is present. Model strings arriving as `"Cisco IP Phone 8851"` are collapsed to `"DMS Cisco 8851"` in the handler (the verbose form is recognized by the convertibility classifier but rejected by the Webex activation code API). Expiry is not persisted (no `result_body` column); regenerating expired codes is future work.

---

## Bulk Job Operations (Phase: bulk-operations)

At 100+ devices, the planner's post-expansion `_optimize_for_bulk()` pass
replaces per-device ops with Webex bulk job submissions:

| Per-device op | Replaced by | Tier |
|---|---|---|
| `device:configure_settings` | `bulk_device_settings:submit` | 5 |
| `device_layout:configure` | `bulk_line_key_template:submit` **+ per-device `device_layout:configure_members`** | 7 |
| `softkey_config:configure` | `bulk_dynamic_settings:submit` | 7 |
| (post-all) | `bulk_rebuild_phones:submit` | 8 |

**`device_layout:configure` is only half-replaceable.** The bulk job applies a line key
*template* — its body is `{action, templateId, locationIds}` and carries no device members.
There is no bulk API for members, so `_optimize_for_bulk` emits a per-device
`device_layout:configure_members` op (members PUT + applyChanges) for every layout that has
`line_members`, alongside the bulk template job. Without it, every shared line silently
stopped being configured at 100+ devices — which is where real migrations live, so the
shared-line work would have been inert in practice. `_resolve_device_members()` is shared by
both handlers so the five-mandatory-field contract lives in one place.

`device:create` is never replaced — there is no bulk create API.

**Threshold:** `bulk_device_threshold` in project `config.json`. Default 100.
Set to 0 to force bulk always; set to 999999 to disable.

**Engine polling:** `execute_bulk_op()` POSTs the submit URL, captures the
job id, calls `poll_job_until_complete()`, and returns an `OpResult` only
when the job reaches COMPLETED or FAILED. If a bulk job fails or times
out, the op is marked `failed` and cascade-skip applies to its dependents.
On the next `execute_all_batches` run, the failed op can be retried.

**Partial-failure fallback (not yet wired):** `execute_bulk_op` accepts a
`fallback_context` parameter with `_run_per_device_fallback` logic for
re-running per-device handlers on failed items. The primitives exist and
are unit-tested, but `run_batch_ops` does not yet populate `fallback_context`
from the plan. Until this is wired, partial bulk job failures are treated as
full failures. Follow-up task needed.

**Serialization:** All four bulk resource types are in
`SERIALIZED_RESOURCE_TYPES` — the batch loop runs them sequentially via
`run_batch_ops` (never via `asyncio.gather`) to satisfy Webex's
one-job-per-org constraint.

**FedRAMP gotcha:** `rebuildPhones` is not supported for Webex for
Government. If you're migrating a FedRAMP tenant, set
`bulk_device_threshold` to 999999 or delete the `bulk_rebuild_phones`
ops manually from the plan before execution.

---

## History — Wave 1 primitive locations (archaeology note)

The silent-failure-hardening Wave 1 primitives — the `SkippedResult`
sentinel + `skipped()` helper in `handlers.py`, the engine bulk-job
critical fixes (#4, #6, #19), and the `JobErrorFetchFailed` exception —
were landed in commit **`85c2f12`** ("feat(planner): thread-safe skip
report + needs_decision visibility"), **not** in the commit whose
message advertises them (`50f5724`, "feat(execute): add SKIPPED op
status + sentinel + bulk-job critical fixes (#4, #6, #19)"). The
`50f5724` commit in fact contains only the Wave 1 test file —
`tests/migration/execute/test_silent_failure_wave1.py`. The diff
reality and the commit message drifted during concurrent planner work.

If you're bisecting / blame-walking Wave 1 primitives, look at
**`85c2f12`** for the actual source changes. This note exists so the
history is retrievable without a forensic pass — the `50f5724` commit
message cannot be rewritten without an interactive rebase of 8
subsequent commits, which was judged too risky on an active research
branch. See Finding #9 in
`docs/superpowers/specs/2026-04-16-silent-failure-hardening-design.md`
for the full rationale.
