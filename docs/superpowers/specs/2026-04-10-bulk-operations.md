# Bulk Operations for Scale

**Date:** 2026-04-10
**Status:** Spec
**Scope:** CUCM migration pipeline — bulk job APIs for device settings at 1000+ phone scale

---

## 1. Problem Statement

The current migration execution engine (`src/wxcli/migration/execute/engine.py`) processes every
device operation as an individual API call. For each device in the migration:

- `device:create` = 1 API call (POST /devices)
- `device:configure_settings` = 1 API call (PUT /telephony/config/devices/{id}/settings)
- `device_layout:configure` = 2-3 API calls (PUT members + PUT layout + POST applyChanges)
- `softkey_config:configure` = 2 API calls (PUT dynamicSettings + POST applyChanges)

At 1000 phones, this totals **5000-7000 API calls** just for device-related operations, not
counting user creation, feature configuration, and settings. With Webex API rate limits
(~100 req/min sustained) and the engine's semaphore-bounded concurrency (default 20), the
device layer alone takes **50-70 minutes**.

At 5000 phones (a realistic enterprise migration), device operations alone consume
**25,000-35,000 API calls = 4-6 hours** of wall-clock time. This is the single largest time
sink in the migration execution phase.

### Current Approach (Per-Device)

From `API_CALL_ESTIMATES` in `src/wxcli/migration/execute/__init__.py` (line 126):

```python
"device:create": 1,               # POST /devices by MAC
"device:configure_settings": 1,   # PUT /telephony/config/devices/{id}/settings
"device_layout:configure": 3,     # PUT members + PUT layout + POST applyChanges
"softkey_config:configure": 2,    # PUT dynamicSettings + POST applyChanges
```

The batch partitioning logic (`batch.py`) groups operations by tier and site, but within each
group, every operation is a standalone API call dispatched by `execute_single_op()`. There is
no aggregation across devices.

### What Webex Offers

Webex provides three bulk job APIs specifically for device operations that can replace hundreds
of individual calls with a single job submission + polling:

1. **Apply Line Key Template** — `POST /telephony/config/jobs/devices/applyLineKeyTemplate`
2. **Change Device Settings** — `POST /telephony/config/jobs/devices/callDeviceSettings`
3. **Rebuild Phones** — `POST /telephony/config/jobs/devices/rebuildPhones`

Additionally, a fourth bulk API handles dynamic device settings (PSK, softkeys):

4. **Update Dynamic Device Settings** — `POST /telephony/config/jobs/devices/dynamicDeviceSettings`

These jobs run server-side, process devices in parallel internally, and return within seconds
to minutes regardless of device count. A 5000-phone line key template application that would
take 4+ hours per-device completes in under 5 minutes as a bulk job.

---

## 2. Webex Bulk Job APIs

### 2a. Apply Line Key Template (Bulk)

**Endpoint:** `POST /v1/telephony/config/jobs/devices/applyLineKeyTemplate`
**OpenAPI location:** `specs/webex-cloud-calling.json` line 32064
**Scope:** `spark-admin:telephony_config_write`

**Request body:**
```json
{
  "action": "APPLY_TEMPLATE",
  "templateId": "Y2lz...",
  "locationIds": ["Y2lz...", "Y2lz..."],
  "excludeDevicesWithCustomLayout": true,
  "includeDeviceTags": ["migrated-batch-1"],
  "excludeDeviceTags": ["do-not-touch"],
  "advisoryTypes": {
    "moreSharedAppearancesEnabled": true,
    "fewSharedAppearancesEnabled": true,
    "moreMonitorAppearancesEnabled": true,
    "moreCPEAppearancesEnabled": true,
    "moreModeManagementAppearancesEnabled": true
  }
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `action` | string | Yes | `"APPLY_TEMPLATE"` or `"APPLY_DEFAULT_LAYOUT"` (factory reset) |
| `templateId` | string | Yes (for APPLY_TEMPLATE) | ID of line key template to apply |
| `locationIds` | string[] | No | Limit to specific locations; omit for org-wide |
| `excludeDevicesWithCustomLayout` | bool | No | Skip devices with custom layouts |
| `includeDeviceTags` | string[] | No | Only apply to devices with these tags |
| `excludeDeviceTags` | string[] | No | Skip devices with these tags |
| `advisoryTypes` | object | No | Control advisory generation for layout conflicts |

**Response (202 Accepted):**
```json
{
  "name": "applyphonelinekeytemplates",
  "id": "Y2lz...",
  "latestExecutionStatus": "STARTED",
  "percentageComplete": 10,
  "updatedCount": 0,
  "advisoryCount": 0
}
```

**Key fields in response:**
- `id` — Job ID for polling
- `latestExecutionStatus` — `STARTING`, `STARTED`, `COMPLETED`, `FAILED`
- `latestExecutionExitCode` — `UNKNOWN`, `COMPLETED`, `FAILED`
- `percentageComplete` — 0-100
- `updatedCount` — Devices successfully updated
- `advisoryCount` — Devices with advisory warnings

**Replaces:** Per-device `device_layout:configure` operations (tier 7). Instead of 3 API calls
per device (PUT members, PUT layout, POST applyChanges), one bulk job handles all devices in
the target locations.

### 2b. Change Device Settings (Bulk)

**Endpoint:** `POST /v1/telephony/config/jobs/devices/callDeviceSettings`
**OpenAPI location:** `specs/webex-cloud-calling.json` line 32878
**Scope:** `spark-admin:telephony_config_write`

**Request body:**
```json
{
  "locationId": "Y2lz...",
  "locationCustomizationsEnabled": true,
  "customizations": {
    "mpp": {
      "audioCodecPriority": {
        "primary": "OPUS",
        "secondary": "G722",
        "tertiary": "G711u",
        "selection": "CUSTOM"
      },
      "displayNameFormat": "PERSON_FIRST_THEN_LAST_NAME",
      "lineKeyLabelFormat": "PERSON_FIRST_THEN_LAST_NAME",
      "dndServicesEnabled": true,
      "cdpEnabled": false,
      "lldpEnabled": false
    },
    "ata": { ... },
    "dect": { ... }
  }
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `locationId` | string | No | Scope to location; omit for org-wide |
| `locationCustomizationsEnabled` | bool | No | Enable location-level overrides |
| `customizations` | object | Yes | Device family settings: `mpp`, `ata`, `dect` |

**Constraint:** Only one job per customer per organization can run at a time. A 409 is returned
if another job is already running.

**Replaces:** Per-device `device:configure_settings` operations (tier 5). Instead of one PUT
per device, a single bulk job applies settings to all devices in a location or org.

### 2c. Rebuild Phones (Bulk)

**Endpoint:** `POST /v1/telephony/config/jobs/devices/rebuildPhones`
**OpenAPI location:** `specs/webex-cloud-calling.json` line 33748
**Scope:** `spark-admin:telephony_config_write`

**Request body:**
```json
{
  "locationId": "Y2lz..."
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `locationId` | string | Yes | Location to rebuild phones for |

**Use case in migration:** After applying line key templates and device settings in bulk, a
rebuild ensures all phones pick up the new configuration. This is the bulk equivalent of the
per-device `POST /telephony/config/devices/{id}/actions/applyChanges/invoke` call.

**Not for FedRAMP:** The API explicitly states it is not supported for Webex for Government.

### 2d. Update Dynamic Device Settings (Bulk)

**Endpoint:** `POST /v1/telephony/config/jobs/devices/dynamicDeviceSettings`
**OpenAPI location:** `specs/webex-cloud-calling.json` line 35998
**Scope:** `spark-admin:telephony_config_write`

**Request body:**
```json
{
  "locationId": "",
  "tags": [
    {
      "familyOrModelDisplayName": "Cisco 9861",
      "tag": "%SOFTKEY_LAYOUT_PSK1%",
      "action": "SET",
      "value": "fnc=sd;ext=1234"
    }
  ]
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `locationId` | string | No | Scope to location; empty string for org-wide |
| `tags` | array | Yes | List of device tag settings to apply |
| `tags[].familyOrModelDisplayName` | string | Yes | Device family or model name |
| `tags[].tag` | string | Yes | Setting tag name |
| `tags[].action` | string | Yes | `"SET"` or `"CLEAR"` |
| `tags[].value` | string | No | Value when action is SET |

**Replaces:** Per-device `softkey_config:configure` operations (tier 7). Instead of 2 API calls
per PSK-capable device (PUT dynamicSettings + POST applyChanges), one bulk job applies PSK
mappings to all devices of a given model in a location.

**Constraint:** Cannot run in parallel with callDeviceSettings or rebuildPhones jobs for the
same org.

### 2e. Job Polling APIs

All four bulk jobs share the same polling pattern:

**Get job status:**
```
GET /v1/telephony/config/jobs/devices/{jobType}/{jobId}
```

**Get job errors:**
```
GET /v1/telephony/config/jobs/devices/{jobType}/{jobId}/errors
```

**List all jobs:**
```
GET /v1/telephony/config/jobs/devices/{jobType}
```

Where `{jobType}` is one of:
- `applyLineKeyTemplate`
- `callDeviceSettings`
- `rebuildPhones`
- `dynamicDeviceSettings`

**Job status lifecycle:**
```
STARTING -> STARTED -> COMPLETED (exitCode: COMPLETED)
                    -> FAILED    (exitCode: FAILED)
```

**Polling fields:**
| Field | Type | Notes |
|-------|------|-------|
| `latestExecutionStatus` | string | Current state |
| `latestExecutionExitCode` | string | `UNKNOWN` while running, `COMPLETED` or `FAILED` at end |
| `percentageComplete` | int | 0-100 progress |
| `updatedCount` | int | Devices successfully processed |
| `advisoryCount` | int | Devices with warnings (applyLineKeyTemplate only) |
| `deviceCount` | int | Total devices targeted (rebuildPhones only) |

---

## 3. Pipeline Integration

### 3a. Threshold-Based Strategy Selection

The planner should select between per-device and bulk execution based on device count:

```python
BULK_DEVICE_THRESHOLD = 100  # Use bulk jobs above this count
```

**Decision logic in the planner:**

```
device_count = count of device:create operations in the plan
if device_count >= BULK_DEVICE_THRESHOLD:
    → Replace device_layout:configure ops with bulk_apply_line_key_template ops
    → Replace device:configure_settings ops with bulk_change_device_settings ops
    → Replace softkey_config:configure ops with bulk_update_dynamic_settings ops
    → Add bulk_rebuild_phones op at the end
else:
    → Keep per-device operations (current behavior)
```

**Why 100?** Below 100 devices, per-device operations complete in under 10 minutes with
20 concurrent workers. The overhead of bulk job submission + polling + error handling for
partial failures doesn't save meaningful time. Above 100, the time savings are substantial:
300 API calls (per-device) vs 3-4 API calls + polling (bulk).

### 3b. Planner Changes (`planner.py`)

Add a post-expansion optimization pass that aggregates per-device ops into bulk ops:

```python
def _optimize_for_bulk(ops: list[MigrationOp], store: MigrationStore) -> list[MigrationOp]:
    """Replace per-device operations with bulk job operations when device count
    exceeds the threshold.

    Per-device ops:                    Bulk replacements:
    device:configure_settings (N)  ->  bulk_device_settings:submit (per location)
    device_layout:configure (N)    ->  bulk_line_key_template:submit (per template+location)
    softkey_config:configure (N)   ->  bulk_dynamic_settings:submit (per location)
    (all per-device)               ->  bulk_rebuild_phones:submit (per location, at end)
    """
```

The function:
1. Counts device operations
2. If below threshold, returns ops unchanged
3. If above threshold:
   - Groups `device:configure_settings` ops by location
   - Groups `device_layout:configure` ops by (template_id, location)
   - Groups `softkey_config:configure` ops by location
   - Removes the per-device ops
   - Adds one bulk op per group
   - Adds `bulk_rebuild_phones:submit` ops per location at the end

### 3c. New Operation Types

| Resource Type | Op Type | Tier | Replaces |
|--------------|---------|------|----------|
| `bulk_device_settings` | `submit` | 5 | N x `device:configure_settings` |
| `bulk_line_key_template` | `submit` | 7 | N x `device_layout:configure` |
| `bulk_dynamic_settings` | `submit` | 7 | N x `softkey_config:configure` |
| `bulk_rebuild_phones` | `submit` | 8 (new) | N x applyChanges sub-calls |

**Note:** Tier 8 is new — it runs after all tier 7 operations (both per-device and bulk).
The rebuild step must happen last because it forces phones to reload their full configuration.

### 3d. Handler Implementations (`handlers.py`)

Each bulk handler follows the same pattern: submit the job, return the job ID.

```python
def handle_bulk_device_settings_submit(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    """Submit bulk device settings job for a location."""
    location_wid = deps.get(data.get("location_canonical_id", ""))
    body = {
        "locationId": location_wid,
        "locationCustomizationsEnabled": True,
        "customizations": data.get("customizations", {}),
    }
    return [("POST", _url("/telephony/config/jobs/devices/callDeviceSettings", ctx), body)]


def handle_bulk_line_key_template_submit(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    """Submit bulk apply line key template job."""
    template_wid = deps.get(data.get("template_canonical_id", ""))
    location_wids = [
        deps[cid] for cid in data.get("location_canonical_ids", []) if cid in deps
    ]
    body = {
        "action": "APPLY_TEMPLATE",
        "templateId": template_wid,
    }
    if location_wids:
        body["locationIds"] = location_wids
    return [("POST", _url("/telephony/config/jobs/devices/applyLineKeyTemplate", ctx), body)]


def handle_bulk_dynamic_settings_submit(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    """Submit bulk dynamic device settings job."""
    location_wid = deps.get(data.get("location_canonical_id", ""))
    body = {
        "locationId": location_wid or "",
        "tags": data.get("tags", []),
    }
    return [("POST", _url("/telephony/config/jobs/devices/dynamicDeviceSettings", ctx), body)]


def handle_bulk_rebuild_phones_submit(data: dict, deps: dict, ctx: dict) -> HandlerResult:
    """Submit rebuild phones job for a location."""
    location_wid = deps.get(data.get("location_canonical_id", ""))
    body = {"locationId": location_wid}
    return [("POST", _url("/telephony/config/jobs/devices/rebuildPhones", ctx), body)]
```

### 3e. Registration in `__init__.py`

```python
# TIER_ASSIGNMENTS additions
("bulk_device_settings", "submit"): 5,
("bulk_line_key_template", "submit"): 7,
("bulk_dynamic_settings", "submit"): 7,
("bulk_rebuild_phones", "submit"): 8,

# API_CALL_ESTIMATES additions (submit = 1 call, but polling adds ~5-10 calls)
"bulk_device_settings:submit": 10,
"bulk_line_key_template:submit": 10,
"bulk_dynamic_settings:submit": 10,
"bulk_rebuild_phones:submit": 10,
```

---

## 4. Job Monitoring and Error Handling

### 4a. Job Polling Engine

Bulk operations are asynchronous — the POST returns immediately with a job ID, but the actual
work happens server-side. The engine needs a polling loop:

```python
async def poll_job_until_complete(
    session: aiohttp.ClientSession,
    job_type: str,
    job_id: str,
    poll_interval: int = 5,
    max_poll_time: int = 600,
    ctx: dict = None,
) -> dict:
    """Poll a bulk job until completion or timeout.

    Returns the final job status dict.
    Raises TimeoutError if max_poll_time exceeded.
    """
    url = _url(f"/telephony/config/jobs/devices/{job_type}/{job_id}", ctx)
    elapsed = 0
    while elapsed < max_poll_time:
        async with session.get(url) as resp:
            status = await resp.json()

        exit_code = status.get("latestExecutionExitCode", "UNKNOWN")
        if exit_code in ("COMPLETED", "FAILED"):
            return status

        pct = status.get("percentageComplete", 0)
        logger.info("Job %s: %d%% complete", job_id[:20], pct)
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

    raise TimeoutError(f"Job {job_id} did not complete within {max_poll_time}s")
```

The engine's `execute_single_op` needs modification: when the handler's URL path contains
`/jobs/devices/`, treat the response as a job submission. Capture the job ID from the response,
then enter the polling loop. The operation is marked `completed` only when the job reaches
`exitCode: COMPLETED`.

### 4b. Partial Failure Handling

Bulk jobs can partially succeed — some devices update successfully while others fail. The job
errors endpoint provides per-device failure details:

```
GET /v1/telephony/config/jobs/devices/{jobType}/{jobId}/errors
```

Response:
```json
{
  "items": [
    {
      "itemId": "device-id-1",
      "trackingId": "...",
      "error": { "key": "...", "message": ["..."] }
    }
  ]
}
```

**Recovery strategy for partial failures:**

1. After a bulk job completes, check if `updatedCount < expectedCount`
2. Fetch the errors endpoint to identify failed devices
3. For each failed device, fall back to per-device operations:
   - Re-expand the failed device into individual ops
   - Add these to a "bulk-fallback" batch at tier 8
   - Execute per-device with full error reporting

This gives the best of both worlds: bulk speed for the majority, per-device granularity for
the failures.

### 4c. One-Job-at-a-Time Constraint

The callDeviceSettings, dynamicDeviceSettings, and rebuildPhones APIs enforce a one-job-per-org
constraint (409 if another is running). The engine must serialize these:

```
bulk_device_settings:submit (location A) -> poll -> complete
bulk_device_settings:submit (location B) -> poll -> complete
bulk_dynamic_settings:submit (location A) -> poll -> complete
bulk_rebuild_phones:submit (location A) -> poll -> complete
```

This serialization is handled naturally by the tier system: all bulk_device_settings are tier 5,
all bulk_line_key_template and bulk_dynamic_settings are tier 7, and bulk_rebuild_phones are
tier 8. Within a tier, operations of the same type for different locations should be serialized,
not parallelized.

**Implementation:** Add a `serialize_within_tier` flag to bulk operation types. The engine's
batch execution loop checks this flag and runs flagged operations sequentially rather than via
`asyncio.gather()`.

---

## 5. Threshold Logic and Tradeoffs

### 5a. When to Use Bulk vs Per-Device

| Dimension | Per-Device | Bulk |
|-----------|-----------|------|
| **Device count** | < 100 | >= 100 |
| **Error granularity** | Per-device, immediate | Per-job, then per-device fallback |
| **Progress visibility** | Real-time per-operation | Percentage-based polling |
| **Partial retry** | Retry individual failed ops | Retry individual devices from error list |
| **Rate limit impact** | Consumes API quota heavily | Minimal quota (job submission + polling) |
| **Wall-clock time (1000 devices)** | ~60 min | ~5 min + polling |
| **Complexity** | Simple — existing engine | Polling loop, fallback, serialization |
| **FedRAMP support** | Full | rebuildPhones not supported |

### 5b. Configurable Threshold

The threshold should be configurable via the migration store's config system:

```python
# In wxcli cucm config
wxcli cucm config set bulk_device_threshold 200
```

Default: 100. Set to 0 to force bulk for all migrations. Set to 999999 to disable bulk.

### 5c. Hybrid Mode

For migrations with mixed device types (some native MPP, some convertible), the bulk optimization
should only apply to the per-device settings/layout operations, not to the device creation
operations. Device creation must remain per-device because:

- MAC-based creation is per-device by nature
- Activation code generation is per-device by nature
- There is no bulk device creation API

The bulk path only covers the **post-creation configuration** phase:

```
Per-device (always):
  device:create / device:create_activation_code

Bulk (above threshold):
  device:configure_settings     -> bulk_device_settings:submit
  device_layout:configure       -> bulk_line_key_template:submit
  softkey_config:configure      -> bulk_dynamic_settings:submit
  (post-all)                    -> bulk_rebuild_phones:submit
```

### 5d. Time Savings Estimate

For a 1000-phone migration:

| Phase | Per-Device | Bulk | Savings |
|-------|-----------|------|---------|
| Device creation | 1000 calls / ~10 min | 1000 calls / ~10 min | None (no bulk API) |
| Device settings | 1000 calls / ~10 min | 3-5 calls / ~2 min | 8 min |
| Line key templates | 3000 calls / ~30 min | 3-5 calls / ~3 min | 27 min |
| Softkey config | 2000 calls / ~20 min | 3-5 calls / ~2 min | 18 min |
| Rebuild phones | 1000 calls / ~10 min | 3-5 calls / ~2 min | 8 min |
| **Total device phase** | **~80 min** | **~19 min** | **~61 min (76%)** |

At 5000 phones, the savings are proportionally larger: ~5 hours vs ~25 minutes.

---

## 6. Documentation Updates Required

| Document | Change |
|----------|--------|
| `src/wxcli/migration/execute/CLAUDE.md` | Add bulk handler descriptions, tier 8, serialization constraint, polling engine |
| `src/wxcli/migration/execute/__init__.py` | Add 4 bulk operation types to TIER_ASSIGNMENTS and API_CALL_ESTIMATES |
| `src/wxcli/migration/execute/handlers.py` | Add 4 bulk handlers + HANDLER_REGISTRY entries |
| `src/wxcli/migration/execute/engine.py` | Add job polling loop, serialization support |
| `src/wxcli/migration/execute/planner.py` | Add `_optimize_for_bulk()` post-expansion pass |
| `src/wxcli/migration/execute/batch.py` | Add serialization flag handling |
| `docs/reference/devices-core.md` | Add bulk job API documentation (currently only per-device is documented) |
| `docs/runbooks/cucm-migration/operator-runbook.md` | Add section on bulk execution behavior, monitoring job progress |
| `docs/runbooks/cucm-migration/tuning-reference.md` | Add `bulk_device_threshold` config key documentation |

---

## 7. Test Strategy

### 7a. Unit Tests

| Test | What it validates |
|------|-------------------|
| `test_handle_bulk_device_settings_submit` | Handler produces correct POST body with locationId and customizations |
| `test_handle_bulk_line_key_template_submit` | Handler produces correct POST body with templateId and locationIds |
| `test_handle_bulk_dynamic_settings_submit` | Handler produces correct POST body with tags |
| `test_handle_bulk_rebuild_phones_submit` | Handler produces correct POST body with locationId |
| `test_optimize_for_bulk_above_threshold` | Planner replaces per-device ops with bulk ops when count >= threshold |
| `test_optimize_for_bulk_below_threshold` | Planner keeps per-device ops when count < threshold |
| `test_optimize_for_bulk_groups_by_location` | Bulk ops grouped correctly by location |
| `test_optimize_for_bulk_groups_by_template` | Line key template bulk ops grouped by template + location |
| `test_optimize_for_bulk_preserves_device_create` | Device creation ops never converted to bulk |
| `test_optimize_for_bulk_configurable_threshold` | Threshold reads from store config |

### 7b. Job Polling Tests

| Test | What it validates |
|------|-------------------|
| `test_poll_job_until_complete_success` | Polling loop returns on COMPLETED |
| `test_poll_job_until_complete_failure` | Polling loop returns on FAILED |
| `test_poll_job_timeout` | Polling loop raises TimeoutError |
| `test_poll_job_progress_logging` | Progress percentage is logged |

### 7c. Partial Failure Tests

| Test | What it validates |
|------|-------------------|
| `test_bulk_partial_failure_fallback` | Failed devices from bulk job get per-device retry ops |
| `test_bulk_partial_failure_error_fetch` | Error endpoint is called to identify failed devices |
| `test_bulk_all_success_no_fallback` | No fallback ops when all devices succeed |

### 7d. Serialization Tests

| Test | What it validates |
|------|-------------------|
| `test_bulk_jobs_serialized_within_tier` | Bulk ops for different locations run sequentially |
| `test_bulk_jobs_different_types_serialized` | callDeviceSettings and dynamicDeviceSettings don't overlap |

### 7e. Integration Tests

| Test | What it validates |
|------|-------------------|
| `test_end_to_end_bulk_1000_devices` | Full plan with 1000 devices produces bulk ops |
| `test_end_to_end_small_migration_no_bulk` | Plan with 50 devices produces per-device ops |
| `test_tier_ordering_with_bulk` | Tier 5 bulk settings run before tier 7 bulk templates before tier 8 rebuild |

---

## 8. Open Questions

1. **Exact one-job-at-a-time scope** — The docs say "one job per customer can be running at any
   given time within the same organization." Does this mean one job of each type, or one job
   total across all types? The dynamicDeviceSettings docs say it "cannot run in parallel with
   other device jobs such as callDeviceSettings and rebuildPhones." If the constraint is global
   across all four job types, the entire bulk phase must be fully serialized, which affects
   the time savings estimate. Needs empirical verification.

2. **Device tag strategy** — The `applyLineKeyTemplate` API supports `includeDeviceTags` and
   `excludeDeviceTags` for targeting specific devices. Should the migration tool tag devices
   during creation (via `POST /devices` → tags) to enable precise bulk targeting? This would
   add 1 API call per device for tagging but enable surgical bulk operations.

3. **Location-scoped vs org-wide** — For single-location migrations, location-scoped bulk jobs
   are preferred (no risk of affecting other locations). For multi-location migrations, should
   the tool submit one org-wide job or one job per location? Per-location is safer but requires
   serialization. Org-wide is faster but riskier (affects all devices in the org, including
   non-migration devices).

4. **Rollback on bulk failure** — Per-device operations have individual rollback (delete the
   created resource). Bulk operations don't have an undo API. If a bulk line key template
   application fails partway, some devices have the new layout and some don't. The only
   recovery is to re-run the bulk job or fall back to per-device. Is this acceptable?

5. **advisoryTypes in line key template jobs** — The API accepts advisory type flags that
   control what gets flagged vs silently applied (e.g., when a template has more shared
   appearances than the device's current layout). What should the default advisory settings
   be for migration? Enabling all advisories is safest but may generate noise.

---

## 9. Estimated Effort

| Component | Effort |
|-----------|--------|
| 4 bulk handlers | 2 hours |
| Job polling engine (poll_job_until_complete) | 3 hours |
| Planner _optimize_for_bulk() | 4 hours |
| Partial failure fallback logic | 3 hours |
| Serialization support in engine/batch | 2 hours |
| __init__.py registrations + tier 8 | 30 min |
| Unit tests (10 tests) | 3 hours |
| Job polling tests (4 tests) | 2 hours |
| Partial failure tests (3 tests) | 2 hours |
| Serialization tests (2 tests) | 1 hour |
| Integration tests (3 tests) | 3 hours |
| Documentation updates (9 docs) | 3 hours |
| **Total** | **~28 hours** |
