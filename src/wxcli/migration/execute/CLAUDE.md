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

**Tier 7 dual use:** Cycle-break fixups use `batch="fixups"`; device finalization ops use location-derived batches. They don't conflict because they land in separate batch groups.

---

## Handler Pattern

Every handler in `handlers.py` is a pure function with this signature:

```python
HandlerResult = list[tuple[str, str, dict | None]]  # [(method, url, body), ...]

def handle_foo_bar(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    ...
```

- `data` — canonical object dict from the store (object's full JSON)
- `deps` — `{canonical_id: webex_id}` for all completed dependency operations
- `ctx` — session context: `{"orgId": "...", "CALLING_LICENSE_ID": "...", ...}`
- Returns a list of `(method, url, body)` tuples executed sequentially by the engine
- **Return `[]`** = no-op. The engine marks the operation completed without making any API call. Use this for guard clauses (missing deps, nothing to configure).
- `_url(path, ctx)` — always use this instead of building URLs manually. It injects `?orgId=...` automatically when ctx has orgId.

### Resolving dependencies

Handlers resolve Webex IDs from `deps` by canonical_id:

```python
# Direct lookup
person_wid = deps.get(data.get("user_canonical_id", ""))

# Prefix search (when the canonical_id isn't in data)
loc_wid = next((wid for cid, wid in deps.items() if cid.startswith("location:")), None)

# Silently omit unresolved members (partial resolution is valid)
members = [{"id": deps[cid]} for cid in member_cids if cid in deps]
```

---

## Handler Inventory

All 41 handlers in `HANDLER_REGISTRY`:

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
| `(workspace, configure_settings)` | PUT `/workspaces/{id}/features/{feature}` | Uses /workspaces/ not /telephony/config/ |
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

### Tier 0 — Hoteling location (voice portal sign-in)
| Key | URL | Notes |
|-----|-----|-------|
| `(hoteling_location, enable_hotdesking)` | PUT `/telephony/config/locations/{id}/features/hotDesking` | Enables voice portal hot desk sign-in at locations with EM phones |

### Tier 6 — Shared/Virtual Lines + Monitoring
| Key | URL | Notes |
|-----|-----|-------|
| `(shared_line, configure)` | PUT `/telephony/config/people/{id}/applications/members` × N owners | Configures person-level app shared call appearance for each owner |
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

**Skip logic (two kinds):**
1. **Generic skip** — any object with a `_SKIP_DECISION_TYPES` decision resolved as "skip" is suppressed entirely. Types: `DEVICE_INCOMPATIBLE`, `DEVICE_FIRMWARE_CONVERTIBLE`, `EXTENSION_CONFLICT`, `LOCATION_AMBIGUOUS`, `MISSING_DATA`, `WORKSPACE_LICENSE_TIER`, `DUPLICATE_USER`, `VOICEMAIL_INCOMPATIBLE`.
2. **Per-expander skip** — individual expanders have their own skip logic (e.g., `_expand_call_forwarding` returns `[]` if all forwarding types disabled; `_expand_line_key_template` returns `[]` if `phones_using == 0`; `_expand_softkey_config` returns `[]` if `is_psk_target=False`).

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
2. **Cross-object** — from `_CROSS_OBJECT_RULES` (20+ rules) queried against store cross_refs. Examples: device:create requires its owner user:create; monitoring_list:configure requires each monitored target's create (SOFT).

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

---

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
- **`device:create_activation_code` vs `device:create`** — firmware-convertible phones (7800/8800-series eligible for E2M conversion) take the activation-code path instead of MAC-based creation. The planner picks between the two based on `compatibility_tier == "convertible"` + the `DEVICE_FIRMWARE_CONVERTIBLE` decision produced by `DeviceCompatibilityAnalyzer`: `"convert"` → activation code op; `"skip"` → no op (caught by the generic skip path upstream); unresolved / anything else → no op. The activation code string lands in `plan_operations.webex_id` because the engine falls back to `resp_body.get("code")` when no `id` is present. Model strings arriving as `"Cisco IP Phone 8851"` are collapsed to `"DMS Cisco 8851"` in the handler (the verbose form is recognized by the convertibility classifier but rejected by the Webex activation code API). Expiry is not persisted (no `result_body` column); regenerating expired codes is future work.

---

## Bulk Job Operations (Phase: bulk-operations)

At 100+ devices, the planner's post-expansion `_optimize_for_bulk()` pass
replaces per-device ops with Webex bulk job submissions:

| Per-device op | Replaced by | Tier |
|---|---|---|
| `device:configure_settings` | `bulk_device_settings:submit` | 5 |
| `device_layout:configure` | `bulk_line_key_template:submit` | 7 |
| `softkey_config:configure` | `bulk_dynamic_settings:submit` | 7 |
| (post-all) | `bulk_rebuild_phones:submit` | 8 |

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
