# mappers/ — CUCM-to-Webex Transform Mappers (Phase 05)

20 mapper classes that read normalized CUCM objects from the store, resolve cross-references, and produce Webex-ready canonical objects. Each mapper extends `Mapper` (base.py) and implements `map(store) -> MapperResult`.

## Mapper Contract

```python
class Mapper(ABC):
    name: str = ""                 # unique name used in depends_on lists
    depends_on: list[str] = []    # other mapper names that must run first

    def map(self, store: MigrationStore) -> MapperResult:
        """Read CUCM objects, produce Webex canonical objects + decisions."""
```

Mappers are run by `transform/engine.py` in topological order. Each mapper:
1. Reads objects from the store (`store.get_objects(object_type)`)
2. Resolves cross-refs (`store.find_cross_refs(canonical_id, relationship)`)
3. Calls `store.upsert_object(canonical_obj)` for each output object
4. Calls `store.save_decision(decision_to_store_dict(d))` for unresolvable cases
5. Returns `MapperResult(objects_created=N, decisions_created=M, ...)`

**base.py utilities:**
- `extract_provenance(data)` — reconstructs `Provenance` from a stored object dict
- `hash_id(value)` — deterministic 12-char hex ID from SHA256
- `decision_to_store_dict(decision)` — converts `Decision` model to store-ready dict (embeds `affected_objects` into `context._affected_objects`)
- `skip_option()`, `manual_option()`, `accept_option()` — standard decision option builders

## Mapper Inventory

Execution order determined by `depends_on` (topological sort):

### Tier 1 — No dependencies

| Mapper | `name` | Produces | Source objects |
|--------|--------|---------|----------------|
| `LocationMapper` | `location_mapper` | `CanonicalLocation`, `CanonicalSchedule` (operating hours) | `device_pool`, `datetime_group`, `cucm_location` |
| `RoutingMapper` | `routing_mapper` | `CanonicalTrunk`, `CanonicalRouteGroup`, `CanonicalTranslationPattern`, `CanonicalOperatingMode` | `gateway`, `sip_trunk`, `route_group`, `route_pattern`, `time_schedule`, `time_period` |

### Tier 2 — Depends on location/routing

| Mapper | `name` | Depends on | Produces | Source objects |
|--------|--------|-----------|---------|----------------|
| `LineMapper` | `line_mapper` | `location_mapper` | `CanonicalLine` (data-only, consumed by user:create / workspace:assign_number) | `dn` (directory number) |
| `UserMapper` | `user_mapper` | `location_mapper` | `CanonicalUser` | `user` |
| `DeviceMapper` | `device_mapper` | `location_mapper` | `CanonicalDevice` (3-tier: NATIVE_MPP / CONVERTIBLE / INCOMPATIBLE) | `phone` (raw) |

### Tier 3 — Depends on users/lines/devices

| Mapper | `name` | Depends on | Produces | Source objects |
|--------|--------|-----------|---------|----------------|
| `FeatureMapper` | `feature_mapper` | `location_mapper`, `line_mapper`, `user_mapper` | `CanonicalHuntGroup`, `CanonicalCallQueue`, `CanonicalAutoAttendant`, `CanonicalCallPark`, `CanonicalPickupGroup`, `CanonicalPagingGroup`, `CanonicalLocationSchedule`, `CanonicalOperatingMode` | `hunt_pilot`, `hunt_list`, `line_group`, `call_park`, `pickup_group`, `time_schedule`, `time_period` |
| `WorkspaceMapper` | `workspace_mapper` | `location_mapper` | `CanonicalWorkspace` (common-area phones) | `phone` (raw, `ownerUserName=None`) |
| `MonitoringMapper` | `monitoring_mapper` | `user_mapper`, `line_mapper` | `CanonicalMonitoringList` | `phone` (raw, `busyLampFields`) |
| `CallForwardingMapper` | `call_forwarding_mapper` | `user_mapper`, `line_mapper` | `CanonicalCallForwarding` | `phone` (raw, per-line forwarding) |
| `CSSMapper` | `css_mapper` | `routing_mapper`, `user_mapper`, `line_mapper`, `device_mapper` | `CanonicalCallingPermission`, `CanonicalDialPlan` | `css`, `partition`, `route_pattern` |
| `ButtonTemplateMapper` | `button_template_mapper` | `device_mapper` | `CanonicalLineKeyTemplate` | `button_template` (raw) |

### Tier 4 — Phase 3 mappers (depend on button templates + device layout inputs)

| Mapper | `name` | Depends on | Produces | Source objects |
|--------|--------|-----------|---------|----------------|
| `DeviceLayoutMapper` | `device_layout_mapper` | `button_template_mapper`, `monitoring_mapper`, `line_mapper`, `device_mapper` | `CanonicalDeviceLayout` | `phone` (raw) + `CanonicalLineKeyTemplate` |
| `SoftkeyMapper` | `softkey_mapper` | `device_mapper` | `CanonicalSoftkeyConfig` (2 per template: 1 template-level + N per-device) | `button_template` (raw softkey data), `phone` (raw) |
| `VoicemailMapper` | `voicemail_mapper` | `user_mapper` | (voicemail config enrichment) | `voicemail_profile`, `user` |

---

## Phase 3 Mappers in Detail

### ButtonTemplateMapper

Reads `button_template` raw objects, resolves model-specific line key counts, produces `CanonicalLineKeyTemplate`. Filters UNMAPPED keys before writing. Only produces templates where `phones_using > 0` (dead templates are skipped by the planner).

Key fields on output: `name`, `device_model`, `line_keys` (list of `{index, key_type, label?, value?}`), `kem_keys`, `kem_module_type`, `phones_using`.

### DeviceLayoutMapper

Merges `CanonicalLineKeyTemplate` key structure with per-phone line appearances from raw phone objects. Detects shared lines via `CanonicalSharedLine` objects.

Reads raw phone via `store.get_objects("phone")`, looks up the phone's button template via cross-ref, resolves line members from `busyLampFields` and `lines`.

Key fields on `CanonicalDeviceLayout`: `device_canonical_id`, `device_id_surface` (`"cloud"` or `"telephony"`), `template_canonical_id`, `owner_canonical_id`, `line_members` (list of `{port, member_canonical_id, line_type}`), `resolved_line_keys`, `resolved_kem_keys`.

**`member_canonical_id`** on `line_members` is what `handle_device_layout_configure` uses to resolve Webex IDs from `deps`. It's the canonical_id of the user or workspace assigned to that port.

### SoftkeyMapper

Reads softkey template data (via SQL — not AXL) and PSK-capable phone references. Produces **two kinds** of `CanonicalSoftkeyConfig`:

1. **Template-level** (`is_psk_target=False`) — `canonical_id=f"softkey_config:{template_name}"`. Report-only. The planner's `_expand_softkey_config` returns `[]` for these — no execution ops produced.
2. **Per-device** (`is_psk_target=True`) — `canonical_id=f"softkey_config:device:{device_name}"`. One per PSK-capable phone referencing the template. These drive `handle_softkey_config_configure`.

Key fields: `is_psk_target`, `device_canonical_id` (set only for per-device objects), `psk_mappings` (list of `{psk_slot, keyword}`), `state_key_lists` (`{webex_state: [keywords]}`), `cucm_template_name`, `phones_using`.

**PSK-capable models:** 9861 (with 120 KEM buttons), 8875. The mapper checks `_is_psk_capable_model(model)` before creating per-device objects.

---

## Key Gotchas

- **Raw phones vs CanonicalDevice.** Mappers that need `speeddials`, `busyLampFields`, or per-line forwarding call `store.get_objects("phone")` to get raw phone dicts (object_type="phone", canonical_id="phone:{name}"). Do NOT call `store.get_objects("device")` for this — that returns `CanonicalDevice` objects which have already lost the raw AXL fields.
- **`device_id_surface` field.** Added to `CanonicalDevice` and `CanonicalDeviceLayout` in Phase 3. Values: `"cloud"` (9800-series + 8875 PhoneOS phones using cloud `deviceId`) or `"telephony"` (classic MPP phones using `callingDeviceId`). The execute handler uses this to decide which API surface to call.
- **`device_canonical_id` field on `CanonicalSoftkeyConfig`.** Only set on per-device objects (`is_psk_target=True`). The planner checks `device_canonical_id` presence before adding dependency edges.
- **PSK slot lowercasing.** The mapper stores `psk_slot` as uppercase (e.g., `"PSK1"`). The execute handler lowercases it when building `softKeyLayout.psk.psk1` keys. The state key list state names in `state_key_lists` are already in Webex format (e.g., `"idle"`, `"progressing"` — NOT CUCM names).
- **`ringOut` → `progressing`.** `CUCM_STATE_TO_PSK_STATE` maps CUCM's `ringOut` to Webex's `progressing`, producing key `softKeyLayout.softKeyMenu.progressingKeyList`. The incorrect value `"processing"` was fixed — see comment in `softkey_mapper.py`.
- **CSSMapper produces both permissions AND dial plans.** It reads the full CSS→partition→route-pattern graph to classify calling permissions (international/national/local) and generate `CanonicalDialPlan` objects from blocking/non-blocking route patterns.
- **FeatureMapper converts CUCM hunt pilots → hunt groups.** CUCM's hunt pilot → hunt list → line group chain collapses into a single `CanonicalHuntGroup`. Agent resolution goes via DN → user cross-refs.
- **LocationMapper writes `device_pool_to_location` cross-refs.** This is the only cross-ref NOT written by `CrossReferenceBuilder` — it requires a decision when device pool → location mapping is ambiguous.
