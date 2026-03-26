# Tier2-Phase3 Design Spec: Execution Handlers for Phone Config, Call Forwarding, and Monitoring

**Date:** 2026-03-25
**Status:** Approved
**Predecessor:** Tier2-Phase2 (assessment mappers for button templates, device layouts, softkeys)

## Overview

The CUCM-to-Webex migration pipeline has an assessment side (extract → normalize → map → analyze → report) and an execution side (plan → execute via Webex APIs). Tier2-Phase2 built the assessment mappers for phone configuration (button templates, device layouts, softkeys). Tier2-Phase3 builds the **execution handlers** that take those mapped canonical objects and push them to Webex.

Additionally, call forwarding and monitoring/BLF mappers exist from Tier 2 Wave 1 but have no execution handlers. This phase fills those gaps.

**Five new handlers total:**
1. `line_key_template:create` — Webex Line Key Template from CUCM Phone Button Template
2. `call_forwarding:configure` — Per-person call forwarding from CUCM per-line CFA/CFB/CFNA
3. `monitoring_list:configure` — Per-person monitoring/BLF from CUCM BLF Speed Dials
4. `device_layout:configure` — Per-device line key + KEM layout (most complex handler)
5. `softkey_config:configure` — Programmable Soft Keys on 9800/8875 via Device Configurations API

## Design Decisions

These were resolved during brainstorming:

1. **PSK included in this phase.** The full PSK schema is documented in `webex-device.json` under `SoftKeyLayoutObject` (`softKeyLayout.psk.psk1`-`psk16` + `softKeyLayout.softKeyMenu.*KeyList`). No verification blocker.

2. **Single multi-call handler for device layout.** `device_layout:configure` returns 2-3 sequential API call tuples. The engine already executes multi-call handlers sequentially (same pattern as `user:configure_settings` and `shared_line:configure`).

3. **Device ID surface stored at map time.** `CanonicalDevice` and `CanonicalDeviceLayout` get a `device_id_surface` field (`"telephony"` for classic MPP using `callingDeviceId`, `"cloud"` for 9800/8875/PhoneOS using `deviceId`). The mapper sets this based on model family. Handlers read it — no runtime branching or planner changes.

4. **New tier 7 for device finalization.** `device_layout:configure` and `softkey_config:configure` run at tier 7, after monitoring lists (tier 6) are configured. This ensures MONITOR-type line keys reference users already in the owner's monitoring list.

5. **Templates created for organizational purposes; per-device layout set directly.** No bulk template-apply via the async jobs API. The jobs API returns a job ID requiring polling, which doesn't fit the engine's synchronous-per-call model. Templates exist in Webex for post-migration management; during migration, each device is configured individually.

## Handler Specifications

All handlers follow the existing pure-function pattern:
- Input: `(data: dict, resolved_deps: dict, ctx: dict)`
- Output: `list[tuple[str, str, dict | None]]` — `[(HTTP_method, URL, body), ...]`
- No IO, no side effects, fully testable

### 1. `handle_line_key_template_create`

**API:** `POST /telephony/config/devices/lineKeyTemplates?orgId=...`

**Body:**
```json
{
  "templateName": "<name>",
  "deviceModel": "<device_model>",
  "lineKeys": [
    {"lineKeyIndex": 1, "lineKeyType": "PRIMARY_LINE"},
    {"lineKeyIndex": 2, "lineKeyType": "MONITOR", "lineKeyLabel": "John", "lineKeyValue": "1001"},
    {"lineKeyIndex": 3, "lineKeyType": "SPEED_DIAL", "lineKeyLabel": "Front Desk", "lineKeyValue": "1000"}
  ],
  "kemModuleType": "<kem_module_type if present>",
  "kemKeys": [...]
}
```

**Mapping from canonical:**
- `data["name"]` → `templateName`
- `data["device_model"]` → `deviceModel`
- `data["line_keys"]` → `lineKeys`, filtering out entries where `key_type == "UNMAPPED"` (report-only from mapper)
- Each line key: `k["index"]` → `lineKeyIndex`, `k["key_type"]` → `lineKeyType`, `k.get("label")` → `lineKeyLabel`, `k.get("value")` → `lineKeyValue`
- `data["kem_module_type"]` → `kemModuleType` (only if present)
- `data["kem_keys"]` → `kemKeys` (same field mapping as line keys, with `kemKeyIndex` and `kemModuleIndex`)

**Dependencies:** None. Org-scoped.
**Returns:** 1 API call.

### 2. `handle_call_forwarding_configure`

**API:** `PUT /people/{personId}/features/callForwarding?orgId=...`

**Body:**
```json
{
  "callForwarding": {
    "always": {
      "enabled": true,
      "destination": "+12223334444",
      "ringReminderEnabled": false,
      "destinationVoicemailEnabled": false
    },
    "busy": {
      "enabled": true,
      "destination": "+15556667777",
      "destinationVoicemailEnabled": false
    },
    "noAnswer": {
      "enabled": true,
      "destination": "+18889990000",
      "numberOfRings": 5,
      "destinationVoicemailEnabled": false
    }
  },
  "businessContinuity": {"enabled": false}
}
```

**Mapping from canonical:**
- `data["user_canonical_id"]` → resolve person Webex ID from `resolved_deps`
- `data["always_enabled"]` → `callForwarding.always.enabled`
- `data["always_destination"]` → `callForwarding.always.destination`
- `data["always_to_voicemail"]` → `callForwarding.always.destinationVoicemailEnabled`
- Same pattern for `busy_*` and `no_answer_*` fields
- `data["no_answer_ring_count"]` → `callForwarding.noAnswer.numberOfRings`

**Dropped CUCM fields (no Webex equivalent):**
- `busy_internal_*`, `no_answer_internal_*` — CUCM internal-only forwarding variants
- `no_coverage_*`, `on_failure_*`, `not_registered_*` — CUCM failure-mode variants
- These are already flagged as advisory decisions by the mapper

**Dependencies:** `user:create` (needs person Webex ID).
**Returns:** 1 API call. Returns `[]` if no forwarding is enabled (all `*_enabled == False`).

### 3. `handle_monitoring_list_configure`

**API:** `PUT /people/{personId}/features/monitoring?orgId=...`

**Body:**
```json
{
  "enableCallParkNotification": true,
  "monitoredMembers": [
    {"id": "<webex-person-id>"},
    {"id": "<webex-person-id-2>"}
  ]
}
```

**Mapping from canonical:**
- `data["user_canonical_id"]` → resolve person Webex ID from `resolved_deps`
- `data["call_park_notification_enabled"]` → `enableCallParkNotification`
- `data["monitored_members"]` → `monitoredMembers`, resolving each `m["target_canonical_id"]` to a Webex ID via `resolved_deps`. Note: the monitoring mapper stores `target_canonical_id` (not `canonical_id`) for each member entry.

**Partial resolution:** Monitored members that fail to resolve (missing from `resolved_deps`) or have `target_canonical_id == None` (unresolved BLF targets from the mapper) are silently omitted. Partial monitoring is better than handler failure. The handler logs a warning for each dropped member.

**Dependencies:** Owner `user:create` + all monitored members' `create` ops.
**Returns:** 1 API call. Returns `[]` if `monitored_members` is empty.

### 4. `handle_device_layout_configure`

The most complex handler. Returns 2-3 sequential API calls.

**Device ID resolution:** The handler reads `data["device_id_surface"]` to determine which ID to use:
- `"cloud"` (9800/8875/PhoneOS): uses `deviceId` directly — this is the cloud device ID returned by `POST /devices` and stored in `resolved_deps` by the engine.
- `"telephony"` (classic MPP): uses `callingDeviceId` which may differ from the cloud `deviceId`.

Both ID surfaces use the same `/telephony/config/devices/` path family for the layout and members endpoints.

**Known risk — `callingDeviceId` for classic MPP:** The engine stores only the cloud `deviceId` from the `device:create` response (`resp_body.get("id")`). For 9800/PhoneOS devices, this IS the correct ID. For classic MPP devices, the telephony config endpoints need `callingDeviceId`, which may differ. The existing `device:configure_settings` handler uses the same cloud ID and has not been validated against live MPP devices.

**Mitigation:** If MPP devices fail layout configuration due to ID mismatch, the `device_layout:configure` handler will prepend a GET call (`GET /telephony/config/devices/{cloudDeviceId}`) to resolve the `callingDeviceId` from the response, then use it for subsequent calls. This GET-then-configure pattern can be added as a follow-up without changing the handler signature or engine.

**Call 1 (conditional — only if `line_members` present):**
```
PUT /telephony/config/devices/{deviceWid}/members?orgId=...
{
  "members": [
    {"id": "<webex-person-id>", "port": 1},
    {"id": "<webex-person-id-2>", "port": 2}
  ]
}
```
- Each `m["canonical_id"]` in `data["line_members"]` resolved via `resolved_deps`
- `m.get("port", 1)` → `port`
- Members that fail to resolve are omitted (same partial-resolution pattern as monitoring)

**Call 2:**
```
PUT /telephony/config/devices/{deviceWid}/layout?orgId=...
{
  "layoutMode": "CUSTOM",
  "lineKeys": [
    {"lineKeyIndex": 1, "lineKeyType": "PRIMARY_LINE"},
    {"lineKeyIndex": 2, "lineKeyType": "SPEED_DIAL", "lineKeyLabel": "Lobby", "lineKeyValue": "2000"}
  ],
  "kemModuleType": "KEM_14_KEYS",
  "kemKeys": [
    {"kemModuleIndex": 1, "kemKeyIndex": 1, "kemKeyType": "MONITOR"}
  ]
}
```
- `data["resolved_line_keys"]` → `lineKeys`
- `data["resolved_kem_keys"]` → `kemKeys`
- `data.get("kem_module_type")` → `kemModuleType`
- If `template_canonical_id` is set and no custom key overrides exist, use `"layoutMode": "DEFAULT"` to inherit from the line key template

**Call 3:**
```
POST /telephony/config/devices/{deviceWid}/actions/applyChanges/invoke?orgId=...
(empty body)
```
Pushes the configuration to the physical device. For 9800-series devices, the device must be online and registered for this to succeed. If offline, the API returns an error — the engine logs it as failed, re-runnable on next batch execution.

**Dependencies:** `device:create`, `line_key_template:create` (if template referenced), owner `user:create`, all line member `create` ops.
**Returns:** 2-3 API calls.

### 5. `handle_softkey_config_configure`

**Prerequisite:** Only reaches this handler for **per-device** PSK configs (`is_psk_target == True`). Classic MPP softkey configs (`is_psk_target == False`) are report-only — the expander skips them. See "Softkey per-device fan-out" below for how template-level configs become per-device ops.

**API:** `PUT /telephony/config/devices/{deviceId}/dynamicSettings?orgId=...`

Uses the per-device Dynamic Settings API (telephony config path family), not the `/deviceConfigurations/` JSON Patch surface. Plain JSON body, no special content-type handling needed.

**Call 1:**
```
PUT /telephony/config/devices/{deviceId}/dynamicSettings?orgId=...
{
  "settings": [
    {"key": "softKeyLayout.psk.psk1", "value": "fnc=sd;ext=1000@$PROXY;nme=Front Desk"},
    {"key": "softKeyLayout.psk.psk2", "value": "fnc=sd;ext=*11;nme=Call Pull"},
    {"key": "softKeyLayout.softKeyMenu.idleKeyList", "value": "redial|1;newcall|2;cfwd|3;psk1|4;psk2|5;dnd;gpickup;dir"},
    {"key": "softKeyLayout.softKeyMenu.connectedKeyList", "value": "hold;endcall;xfer;conf;park"}
  ]
}
```

**Mapping from canonical:**
- `data["psk_mappings"]` → settings entries for `softKeyLayout.psk.psk<N>`: each `{"psk_slot": "PSK1", "keyword": "park"}` becomes `{"key": "softKeyLayout.psk.psk1", "value": "<psk_value>"}`. Speed dials use `fnc=sd;ext=<value>@$PROXY;nme=<label>`. Other types map to their keyword directly.
- `data["state_key_lists"]` → settings entries for `softKeyLayout.softKeyMenu.<stateKeyList>`: each state name (e.g., `"idle"`) maps to the key `softKeyLayout.softKeyMenu.idleKeyList`, with the value being the semicolon-separated keyword string with PSK references injected.

**PSK value syntax (from OpenAPI spec):**
- Speed Dial: `fnc=sd;ext=<extension>@$PROXY;vid=<n>;nme=<label>`
- DTMF: `fnc=dtmf;ext=<digits>;nme=<label>;vid=<n>`
- XML Service: `fnc=xml;url=<url>;nme=<label>`

**State key list properties (14 total):**
`idleKeyList`, `offHookKeyList`, `dialingInputKeyList`, `progressingKeyList`, `connectedKeyList`, `connectedVideoKeyList`, `startTransferKeyList`, `startConferenceKeyList`, `conferencingKeyList`, `releasingKeyList`, `holdKeyList`, `ringingKeyList`, `sharedActiveKeyList`, `sharedHeldKeyList`

**Read-back verification (optional):** Before writing, the handler can optionally read current settings via `POST /telephony/config/lists/devices/{deviceId}/dynamicSettings/actions/getSettings/invoke` with `{"keys": ["softKeyLayout.psk.*", "softKeyLayout.softKeyMenu.*"]}`. Not included in the primary handler (adds latency), but documented for debugging.

**Call 2:**
```
POST /telephony/config/devices/{deviceId}/actions/applyChanges/invoke?orgId=...
(empty body)
```
Returns 204. Pushes pending config to the device. Same 9800-online caveat as device_layout — device must be online and registered. Without this call, settings are stored in Webex but don't reach the phone.

**Dependencies:** `device:create`.
**Returns:** 2 API calls. Uses `deviceId` (cloud surface) since PSK is only for 9800/8875.

### Softkey per-device fan-out

The softkey mapper currently creates **one `CanonicalSoftkeyConfig` per CUCM softkey template** (e.g., `softkey_config:Standard User`), not per device. But `PUT .../devices/{deviceId}/dynamicSettings` targets a single device. The resolution:

**Mapper change:** For PSK-eligible templates (`is_psk_target == True`), the softkey mapper creates **per-device** config objects in addition to the template-level object. For each phone that uses the template and is a 9800/8875 model, the mapper creates `softkey_config:device:<SEP...>` with:
- `device_canonical_id` set to the phone's device canonical ID
- PSK mappings and key lists copied from the template-level config
- `is_psk_target = True`

The template-level `softkey_config:Standard User` object remains with `is_psk_target = False` (report-only, counts `phones_using`). The per-device objects are what the expander creates ops for.

This is analogous to how `calling_permission:assign` fans out to per-user API calls — the difference is that softkey fan-out happens at map time (creating per-device objects) rather than at handler time (iterating over users), because each device needs a separate entry in the dependency graph.

## Tier Assignments

```python
TIER_ASSIGNMENTS additions:
    ("line_key_template", "create"): 1,      # Org-wide infrastructure, no deps
    ("call_forwarding", "configure"): 5,     # Same as other user settings
    ("monitoring_list", "configure"): 6,     # After all users/workspaces/features
    ("device_layout", "configure"): 7,       # NEW TIER — after templates, monitoring, shared lines
    ("softkey_config", "configure"): 7,      # Same finalization tier

API_CALL_ESTIMATES additions:
    "line_key_template:create": 1,
    "call_forwarding:configure": 1,
    "monitoring_list:configure": 1,
    "device_layout:configure": 3,            # members + layout + applyChanges
    "softkey_config:configure": 2,           # PUT dynamicSettings + POST applyChanges

ORG_WIDE_TYPES addition:
    "line_key_template"
```

**Tier 7 rationale:** Device layout BLF keys (type MONITOR) may reference users that need to be in the owner's monitoring list first. Putting device_layout at tier 7 guarantees monitoring_list (tier 6) has run. Also cleanly separates "device finalization" from "shared line / virtual line" work at tier 6.

**Note:** Tier 7 was previously used only by the cycle-breaker for fixup operations (created by `detect_and_break_cycles` in `dependency.py`). With this change, tier 7 is shared between device finalization ops and fixup ops. Both coexist safely in the batch system — fixups use `batch="fixups"` while device ops use location-derived batches.

## Planner Expansions

Five new `_expand_*` functions added to `planner.py` and registered in `_EXPANDERS`.

### `_expand_line_key_template(obj)`
- 1 op: `("line_key_template", "create")` at tier 1
- Batch: `"org-wide"`
- Skip condition: `phones_using == 0` (dead template)
- No `depends_on`

### `_expand_call_forwarding(obj)`
- 1 op: `("call_forwarding", "configure")` at tier 5
- Batch: derived from user's location (via `user_canonical_id` → user object → `location_id`)
- Skip condition: all forwarding disabled (`always_enabled`, `busy_enabled`, `no_answer_enabled` all False)
- `depends_on`: `[user_canonical_id:create]`

### `_expand_monitoring_list(obj)`
- 1 op: `("monitoring_list", "configure")` at tier 6
- Batch: derived from user's location
- Skip condition: `monitored_members` is empty
- `depends_on`: `[user_canonical_id:create]` + `[m["target_canonical_id"]:create for m in monitored_members if m.get("target_canonical_id")]`

### `_expand_device_layout(obj)`
- 1 op: `("device_layout", "configure")` at tier 7
- Batch: derived from device's location
- Skip condition: `resolved_line_keys` is empty AND `template_canonical_id` is None
- `depends_on`:
  - `device_canonical_id:create`
  - `template_canonical_id:create` (if set)
  - `owner_canonical_id:create` (if set)
  - `m["canonical_id"]:create` for each line member

### `_expand_softkey_config(obj)`
- If `is_psk_target == False`: no ops (added to `_DATA_ONLY_TYPES` conceptually — the expander returns `[]`)
- If `is_psk_target == True`: 1 op: `("softkey_config", "configure")` at tier 7
- Batch: derived from device's location
- `depends_on`: `[device_canonical_id:create]`

## Dependency Graph Rules

New `_CROSS_OBJECT_RULES` entries in `dependency.py`:

```python
# Call forwarding depends on owner user being created
{
    "source_type": "call_forwarding",
    "source_op": "configure",
    "relationship": "user_has_call_forwarding",
    "target_op": "create",
    "dep_type": DependencyType.REQUIRES,
},

# Monitoring list depends on owner user being created
{
    "source_type": "monitoring_list",
    "source_op": "configure",
    "relationship": "user_has_monitoring_list",
    "target_op": "create",
    "dep_type": DependencyType.REQUIRES,
},

# Monitoring list depends on each monitored target existing (SOFT — partial OK)
{
    "source_type": "monitoring_list",
    "source_op": "configure",
    "relationship": "monitoring_watches",
    "target_op": "create",
    "dep_type": DependencyType.SOFT,
},

# Device layout depends on its device being created
{
    "source_type": "device_layout",
    "source_op": "configure",
    "relationship": "device_has_layout",
    "target_op": "create",
    "dep_type": DependencyType.REQUIRES,
},

# Device layout depends on referenced line key template existing
{
    "source_type": "device_layout",
    "source_op": "configure",
    "relationship": "layout_uses_template",
    "target_op": "create",
    "dep_type": DependencyType.REQUIRES,
},
```

**Note:** Device layout → line member dependencies use `depends_on` in the expander (intra-object edges), not cross-object rules. The member list is directly in the canonical object data.

Softkey config dependencies are handled entirely via `depends_on` in the expander (`device_canonical_id:create`). No cross-object rules needed.

## Model Changes

### `CanonicalDevice` (models.py)
Add field:
```python
device_id_surface: str = "telephony"  # "telephony" (MPP) or "cloud" (9800/8875)
```
Set by the device mapper at map time based on model family. 9800-series and 8875 → `"cloud"`. Everything else → `"telephony"`.

### `CanonicalDeviceLayout` (models.py)
Add field:
```python
device_id_surface: str = "telephony"  # Copied from associated device at map time
```

### `CanonicalSoftkeyConfig` (models.py)
Add field:
```python
device_canonical_id: str | None = None  # Links to the device this config applies to
```
Set by the softkey mapper. Enables the expander to wire `depends_on` without a cross-ref lookup.

### New cross-ref: `layout_uses_template`
The `device_layout_mapper.py` stores a new cross-ref linking `device_layout:<X>` → `line_key_template:<Y>` when a layout references a template. This enables the `device_layout:configure` → `line_key_template:create` dependency edge via the cross-object rules.

## Handler Registry & Engine

### HANDLER_REGISTRY (handlers.py)
Five new entries:
```python
("line_key_template", "create"): handle_line_key_template_create,
("call_forwarding", "configure"): handle_call_forwarding_configure,
("monitoring_list", "configure"): handle_monitoring_list_configure,
("device_layout", "configure"): handle_device_layout_configure,
("softkey_config", "configure"): handle_softkey_config_configure,
```

### Engine (engine.py)
**No changes.** The softkey handler now uses `PUT /telephony/config/devices/{deviceId}/dynamicSettings` with plain JSON — no special content-type handling needed. Multi-call handlers are already supported by the sequential sub-call loop in `execute_single_op`. The `webex_id` from the first call's response is propagated — for configure ops this will be `None`, which is correct since no new resource is created.

### 409 Recovery (engine.py)
**No new `_try_find_existing` entries.** All new handlers are PUT/PATCH (configure, not create), so 409 conflicts don't apply. `line_key_template:create` is a POST, but template names aren't unique-constrained — duplicates are allowed. Search-by-name recovery can be added later if needed.

## Test Plan

All tests in `tests/migration/execute/`. Follows existing patterns.

### Handler Tests (test_handlers.py) — ~15 tests

**`test_handle_line_key_template_create`:**
- Basic: name + model + 3 line keys → correct POST body
- With KEM: includes `kemModuleType` and `kemKeys`
- Unmapped filtered: buttons with `key_type == "UNMAPPED"` excluded from body

**`test_handle_call_forwarding_configure`:**
- All enabled: always + busy + noAnswer all populated
- Partial: only noAnswer enabled, others omitted
- All disabled: returns `[]` (no-op)
- Voicemail destinations: `*_to_voicemail` flags → `destinationVoicemailEnabled`
- User resolution: person Webex ID resolved from `user_canonical_id` in deps

**`test_handle_monitoring_list_configure`:**
- Basic: 2 monitored members, both resolve → correct body
- Partial resolution: 1 of 2 members missing from deps → body has 1 member
- Empty members: returns `[]` (no-op)
- Call park notification: flag mapped correctly

**`test_handle_device_layout_configure`:**
- Full 3-call sequence: members + layout + applyChanges
- No line members: skips call 1, returns 2 calls
- Template mode: `layoutMode: "DEFAULT"` when template set and no custom keys
- Cloud device surface: uses `deviceId` instead of `callingDeviceId`
- Telephony device surface: uses `callingDeviceId` (default)

**`test_handle_softkey_config_configure`:**
- PSK mappings: psk1-psk3 as dynamicSettings key/value pairs
- Key list injection: idleKeyList setting with PSK references
- Body structure: `{"settings": [...]}` with correct keys
- Non-PSK: `is_psk_target == False` → returns `[]`
- Includes applyChanges as call 2

### Planner Tests (test_planner.py) — ~10 tests

- `test_expand_line_key_template`: 1 op, tier 1, org-wide batch
- `test_expand_line_key_template_dead`: `phones_using == 0` → no ops
- `test_expand_call_forwarding`: 1 op, tier 5, correct depends_on
- `test_expand_call_forwarding_all_disabled`: no forwarding enabled → no ops
- `test_expand_monitoring_list`: 1 op, tier 6, depends_on includes all members
- `test_expand_monitoring_list_empty`: no members → no ops
- `test_expand_device_layout`: 1 op, tier 7, depends_on includes device + template + owner + members
- `test_expand_device_layout_nothing_to_configure`: empty keys + no template → no ops
- `test_expand_softkey_config_psk`: `is_psk_target == True` → 1 op, tier 7
- `test_expand_softkey_config_non_psk`: `is_psk_target == False` → no ops

### Dependency Graph Tests (test_dependency.py or test_planner.py) — ~5 tests

- `test_call_forwarding_depends_on_user_create`: REQUIRES edge via `user_has_call_forwarding`
- `test_monitoring_depends_on_user_create`: REQUIRES edge via `user_has_monitoring_list`
- `test_monitoring_watches_are_soft`: SOFT edges via `monitoring_watches` (breakable in cycles)
- `test_device_layout_depends_on_device_create`: REQUIRES edge via `device_has_layout`
- `test_device_layout_depends_on_template`: REQUIRES edge via `layout_uses_template`

### Estimated Total: ~30 new tests

## Files Modified

| File | Changes |
|------|---------|
| `src/wxcli/migration/execute/__init__.py` | 5 TIER_ASSIGNMENTS, 5 API_CALL_ESTIMATES, 1 ORG_WIDE_TYPES |
| `src/wxcli/migration/execute/handlers.py` | 5 handler functions, 5 HANDLER_REGISTRY entries |
| `src/wxcli/migration/execute/planner.py` | 5 `_expand_*` functions, 5 `_EXPANDERS` entries |
| `src/wxcli/migration/execute/dependency.py` | 5 `_CROSS_OBJECT_RULES` entries |
| `src/wxcli/migration/models.py` | `device_id_surface` on CanonicalDevice + CanonicalDeviceLayout, `device_canonical_id` on CanonicalSoftkeyConfig |
| `src/wxcli/migration/transform/mappers/device_layout_mapper.py` | Add `layout_uses_template` cross-ref |
| `src/wxcli/migration/transform/mappers/softkey_mapper.py` | Per-device fan-out for PSK-eligible phones, populate `device_canonical_id` |
| `src/wxcli/migration/transform/mappers/device_mapper.py` | Set `device_id_surface` based on model |
| `tests/migration/execute/test_handlers.py` | ~15 new handler tests |
| `tests/migration/execute/test_planner.py` | ~10 new expander tests |
| `tests/migration/execute/test_dependency.py` | ~5 new dependency graph tests |

## Support APIs Reference

These APIs are called by the Phase 3 handlers as part of multi-step operations. All exist in `webex-cloud-calling.json` and `webex-device.json`.

### Apply Changes (used by handlers 4 and 5)
```
POST /telephony/config/devices/{deviceId}/actions/applyChanges/invoke
```
Returns 204. Pushes pending config to the device. **Required after:** updating device members, modifying device layout, or updating dynamic settings. Without this call, changes sit in Webex but don't reach the phone.

### Per-Device Dynamic Settings (used by handler 5)
```
PUT /telephony/config/devices/{deviceId}/dynamicSettings
Body: {"settings": [{"key": "softKeyLayout.psk.psk1", "value": "fnc=sd;ext=1000@$PROXY;nme=Front Desk"}, ...]}

POST /telephony/config/lists/devices/{deviceId}/dynamicSettings/actions/getSettings/invoke
Body: {"keys": ["softKeyLayout.psk.*"]}
Returns: current dynamic settings for the device (read-back for debugging)
```

### Async Job APIs (out of scope — scale optimization)

These bulk/async APIs exist but are **not used by the per-device handlers**. They're documented here as future optimization options for the cucm-migrate skill to invoke post-batch for large migrations (500+ devices per location).

**Line Key Template Bulk Apply:**
```
POST /telephony/config/devices/actions/previewApplyLineKeyTemplate/invoke
Body: {"action": "APPLY_TEMPLATE", "templateId": "...", "locationIds": [...], "excludeDevicesWithCustomLayout": true}
Returns: {"deviceCount": N}

POST /telephony/config/jobs/devices/applyLineKeyTemplate
Body: same as preview
Returns: {"id": "jobId", ...}

GET /telephony/config/jobs/devices/applyLineKeyTemplate/{jobId}
GET /telephony/config/jobs/devices/applyLineKeyTemplate/{jobId}/errors
```

**Bulk Dynamic Settings (PSK at scale):**
```
POST /telephony/config/jobs/devices/dynamicDeviceSettings
Body: location/org scoped dynamic settings changes

GET /telephony/config/jobs/devices/dynamicDeviceSettings/{jobId}
GET /telephony/config/jobs/devices/dynamicDeviceSettings/{jobId}/errors
```

**Rebuild Phones Configuration (recovery):**
```
POST /telephony/config/jobs/devices/rebuildPhones
Body: location or org scoped

GET /telephony/config/jobs/devices/rebuildPhones/{jobId}
GET /telephony/config/jobs/devices/rebuildPhones/{jobId}/errors
```
Nuclear option — forces full config rebuild and push. Useful as a recovery step if individual applyChanges calls fail at scale.

**Why these are out of scope:** The current engine executes synchronous request/response pairs. Async jobs require submit → poll → check-errors, which is a different execution model. Per-device handlers work for typical migration sizes. If bulk jobs are needed, they run outside the engine — the cucm-migrate skill can invoke them post-batch with manual polling. This keeps the engine simple and the handlers testable.

## Out of Scope

- **Async job APIs** — Bulk template apply, bulk dynamic settings, rebuild phones. Documented above as future optimization, invocable by the cucm-migrate skill post-batch. Engine stays synchronous.
- **Preview endpoint** (`lineKeyTemplates/preview`) — Useful for dry-run mode, not needed for execution.
- **Template update/delete** — Only creation. Templates are immutable during migration.
- **Offline device retry orchestration** — 9800 devices that are offline fail `applyChanges`. Re-run handles this. No special retry loop.
- **Classic MPP softkey execution** — 78xx/88xx/68xx softkey templates are report-only (`is_psk_target == False`). Only 9800/8875 PSK configs get execution handlers.
- **`cfExpandedSoftKey` and `acd.displayCallqueueAgentSoftkeys`** — Additional softkey-adjacent device config properties. Out of scope for this phase; can be added to device_configure_settings if needed.
- **Connected Meeting Key List and Device Key List** — Mentioned in Control Hub docs but not in the OpenAPI spec. Out of scope until API support is confirmed.
- **`/deviceConfigurations/` JSON Patch surface** — The Device Configurations API (`PATCH /deviceConfigurations/{deviceId}`) uses JSON Patch format which would require engine content-type changes. Using the Dynamic Settings API (`PUT .../dynamicSettings`) instead — same config keys, plain JSON, no engine changes.
