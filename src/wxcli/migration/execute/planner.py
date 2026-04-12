"""Execution planner — expand canonical objects into migration operations.

Each canonical object type has a deterministic expansion pattern that produces
one or more MigrationOp nodes for the dependency DAG. The planner only expands
objects at status 'analyzed' (all decisions resolved). Objects at
'needs_decision' are skipped.

(from 05-dependency-graph.md — expand_to_operations lines 38-75)
"""

from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.execute import (
    API_CALL_ESTIMATES,
    MigrationOp,
    ORG_WIDE_TYPES,
    TIER_ASSIGNMENTS,
)
from wxcli.migration.store import MigrationStore

logger = logging.getLogger(__name__)

# Decision types where chosen_option="skip" means "don't expand this object".
# (from phase-07-planning.md lines 26-27)
_SKIP_DECISION_TYPES = {
    "DEVICE_INCOMPATIBLE",
    "DEVICE_FIRMWARE_CONVERTIBLE",
    "EXTENSION_CONFLICT",
    "LOCATION_AMBIGUOUS",
    "MISSING_DATA",
    "WORKSPACE_LICENSE_TIER",
    "DUPLICATE_USER",
    "VOICEMAIL_INCOMPATIBLE",
}


# ---------------------------------------------------------------------------
# Decision-aware helpers
# ---------------------------------------------------------------------------

def _build_decisions_index(store: MigrationStore) -> dict[str, list[dict[str, Any]]]:
    """Build a canonical_id → decisions index from all non-stale decisions.

    Called once per expand_to_operations() run to avoid O(objects * decisions)
    repeated queries.
    """
    all_decisions = store.get_all_decisions()
    index: dict[str, list[dict[str, Any]]] = {}
    for d in all_decisions:
        if d.get("chosen_option") == "__stale__":
            continue
        context = d.get("context", {})
        for cid in context.get("_affected_objects", []):
            index.setdefault(cid, []).append(d)
    return index


def _any_skip_decision(decisions: list[dict[str, Any]]) -> bool:
    """Check if any decision in _SKIP_DECISION_TYPES is resolved as 'skip'."""
    for d in decisions:
        if d.get("type") in _SKIP_DECISION_TYPES and d.get("chosen_option") == "skip":
            return True
    return False


def _decision_chosen(decisions: list[dict[str, Any]], decision_type: str) -> str | None:
    """Get the chosen option for a specific decision type, if resolved."""
    for d in decisions:
        if d.get("type") == decision_type and d.get("chosen_option") is not None:
            return d["chosen_option"]
    return None


# ---------------------------------------------------------------------------
# Operation builder helpers
# ---------------------------------------------------------------------------

def _op(
    canonical_id: str,
    op_type: str,
    resource_type: str,
    description: str,
    depends_on: list[str] | None = None,
    batch: str | None = None,
) -> MigrationOp:
    """Build a MigrationOp with tier and api_calls looked up from constants."""
    tier = TIER_ASSIGNMENTS.get((resource_type, op_type), 0)
    api_key = f"{resource_type}:{op_type}"
    api_calls = API_CALL_ESTIMATES.get(api_key, 1)
    if batch is None and resource_type in ORG_WIDE_TYPES:
        batch = "org-wide"
    return MigrationOp(
        canonical_id=canonical_id,
        op_type=op_type,
        resource_type=resource_type,
        tier=tier,
        batch=batch,
        api_calls=api_calls,
        description=description,
        depends_on=depends_on or [],
    )


def _node_id(canonical_id: str, op_type: str) -> str:
    """Consistent node ID format: 'canonical_id:op_type'.

    To parse back: use rsplit(":", 1) — canonical_id may contain colons.
    """
    return f"{canonical_id}:{op_type}"


# ---------------------------------------------------------------------------
# Per-type expansion patterns
# (from 05-dependency-graph.md lines 41-74 — user and location examples)
# Other types follow the same deterministic pattern.
# ---------------------------------------------------------------------------

def _expand_location(obj: dict[str, Any]) -> list[MigrationOp]:
    """Location → 2 ops: create + enable_calling (tier 0).

    Fix 13: Creating a location does NOT enable Webex Calling on it.
    A separate POST /v1/telephony/config/locations is required.
    (from 05-dependency-graph.md lines 68-70, updated by Phase 12a Fix 13)
    """
    cid = obj["canonical_id"]
    name = obj.get("name", cid)
    return [
        _op(cid, "create", "location", f"Create location {name}"),
        _op(cid, "enable_calling", "location", f"Enable Webex Calling on {name}",
            depends_on=[_node_id(cid, "create")]),
    ]


def _expand_trunk(obj: dict[str, Any]) -> list[MigrationOp]:
    """Trunk → 1 op: create (tier 1)."""
    cid = obj["canonical_id"]
    name = obj.get("name", cid)
    return [_op(cid, "create", "trunk", f"Create trunk {name}")]


def _expand_route_group(obj: dict[str, Any]) -> list[MigrationOp]:
    """Route group → 1 op: create (tier 1). Depends on its trunks."""
    cid = obj["canonical_id"]
    name = obj.get("name", cid)
    deps = []
    for gw in obj.get("local_gateways", []):
        trunk_cid = gw.get("trunk_canonical_id")
        if trunk_cid:
            deps.append(_node_id(trunk_cid, "create"))
    return [_op(cid, "create", "route_group", f"Create route group {name}", depends_on=deps)]


def _expand_route_list(obj: dict[str, Any]) -> list[MigrationOp]:
    """Route list → 1-2 ops: create (tier 1) + optional configure_numbers.
    Depends on its route group.
    """
    cid = obj["canonical_id"]
    name = obj.get("name", cid)
    deps = []
    rg_cid = obj.get("route_group_id")
    if rg_cid:
        deps.append(_node_id(rg_cid, "create"))
    ops = [_op(cid, "create", "route_list", f"Create route list {name}", depends_on=deps)]
    numbers = obj.get("numbers", [])
    if numbers:
        ops.append(_op(
            cid, "configure_numbers", "route_list",
            f"Assign {len(numbers)} numbers to route list {name}",
            depends_on=[_node_id(cid, "create")],
        ))
    return ops


def _expand_operating_mode(obj: dict[str, Any]) -> list[MigrationOp]:
    """Operating mode (schedule) → 1 op: create (tier 1)."""
    cid = obj["canonical_id"]
    name = obj.get("name", cid)
    return [_op(cid, "create", "operating_mode", f"Create operating mode {name}")]


def _expand_schedule(obj: dict[str, Any]) -> list[MigrationOp]:
    """Location schedule → 1 op: create (tier 1)."""
    cid = obj["canonical_id"]
    name = obj.get("name", cid)
    loc_id = obj.get("location_id")
    return [_op(cid, "create", "schedule", f"Create location schedule {name}",
                batch=loc_id)]


def _expand_user(obj: dict[str, Any]) -> list[MigrationOp]:
    """User → 1-3 ops: create (always), configure_settings (if custom), configure_voicemail (if custom).

    Fix 12: extension and license are included at creation time — the Webex
    People API requires extension when callingData=true, and wxcli users create
    has --license (not available on update).
    Only generates configure_settings/configure_voicemail ops if the user has
    non-default settings data to apply.
    (from 05-dependency-graph.md lines 46-66, updated by Phase 12a Fix 12)
    """
    cid = obj["canonical_id"]
    email = (obj.get("emails") or ["unknown"])[0]
    loc_id = obj.get("location_id")
    batch = loc_id if loc_id else None

    ops = [_op(cid, "create", "user", f"Create person {email}", batch=batch)]

    # Only generate settings op if user has custom call settings
    settings = obj.get("call_settings") or obj.get("forwarding") or obj.get("call_forwarding")
    if settings:
        ops.append(_op(cid, "configure_settings", "user",
                       f"Configure call settings for {email}",
                       depends_on=[_node_id(cid, "create")], batch=batch))

    # Only generate voicemail op if user has custom voicemail config
    vm = obj.get("voicemail") or obj.get("voicemail_settings") or obj.get("voicemail_profile_id")
    if vm:
        ops.append(_op(cid, "configure_voicemail", "user",
                       f"Configure voicemail for {email}",
                       depends_on=[_node_id(cid, "create")], batch=batch))

    return ops


def _expand_workspace(obj: dict[str, Any]) -> list[MigrationOp]:
    """Workspace → 3 ops: create, assign_number, configure_settings."""
    cid = obj["canonical_id"]
    name = obj.get("display_name", cid)
    loc_id = obj.get("location_id")
    batch = loc_id if loc_id else None

    return [
        _op(cid, "create", "workspace", f"Create workspace {name}", batch=batch),
        _op(cid, "assign_number", "workspace",
            f"Assign number to workspace {name}",
            depends_on=[_node_id(cid, "create")], batch=batch),
        _op(cid, "configure_settings", "workspace",
            f"Configure settings for workspace {name}",
            depends_on=[_node_id(cid, "assign_number")], batch=batch),
    ]


_NON_WEBEX_DEVICE_MODELS = {
    "Cisco Unified Client Services Framework",
    "Analog Phone",
    "Cisco ATA 191",
}


def _expand_device(
    obj: dict[str, Any], decisions: list[dict[str, Any]],
) -> list[MigrationOp]:
    """Device → 1 op (CONVERTIBLE, convert) or 2 ops (NATIVE_MPP).

    - NATIVE_MPP / default: create (MAC-based POST /devices) + configure_settings
    - CONVERTIBLE + decision 'convert': single create_activation_code op,
      no configure_settings (the phone auto-configures after registering)
    - CONVERTIBLE + decision 'skip': caught by the generic skip path upstream
    - CONVERTIBLE + unresolved / other: no ops (decision forces a no-op)
    - webex_app / infrastructure / dect / non-Webex models: no ops

    Skip decisions handled generically in expand_to_operations.
    (from 05-dependency-graph.md — device:create at tier 3, api_calls=2)
    """
    cid = obj["canonical_id"]
    # Skip devices with non-Webex models (CSF soft phones, analog, ATA)
    if obj.get("compatibility_tier") in ("webex_app", "infrastructure", "dect") or obj.get("model") in _NON_WEBEX_DEVICE_MODELS:
        return []
    name = obj.get("display_name") or obj.get("mac") or cid
    owner_cid = obj.get("owner_canonical_id")
    loc_cid = obj.get("location_canonical_id")
    batch = loc_cid if loc_cid else None

    deps_create: list[str] = []
    if owner_cid:
        deps_create.append(_node_id(owner_cid, "create"))

    if obj.get("compatibility_tier") == "convertible":
        choice = _decision_chosen(decisions, "DEVICE_FIRMWARE_CONVERTIBLE")
        if choice != "convert":
            # Only 'convert' resolves to an activation code op.
            # 'skip' is caught by the generic skip path upstream; any
            # other value (None / unresolved) produces no op.
            return []
        return [
            _op(cid, "create_activation_code", "device",
                f"Generate activation code for {name}",
                depends_on=deps_create, batch=batch),
        ]

    return [
        _op(cid, "create", "device", f"Create device {name}",
            depends_on=deps_create, batch=batch),
        _op(cid, "configure_settings", "device", f"Configure device {name}",
            depends_on=[_node_id(cid, "create")], batch=batch),
    ]


def _expand_dial_plan(obj: dict[str, Any]) -> list[MigrationOp]:
    """Dial plan → 1 op: create (tier 2, org-wide)."""
    cid = obj["canonical_id"]
    name = obj.get("name", cid)
    deps = []
    route_id = obj.get("route_id")
    if route_id:
        deps.append(_node_id(route_id, "create"))
    return [_op(cid, "create", "dial_plan", f"Create dial plan {name}", depends_on=deps)]


def _expand_translation_pattern(obj: dict[str, Any]) -> list[MigrationOp]:
    """Translation pattern → 1 op: create (tier 2, org-wide)."""
    cid = obj["canonical_id"]
    name = obj.get("name") or obj.get("matching_pattern") or cid
    return [_op(cid, "create", "translation_pattern", f"Create translation pattern {name}")]


def _expand_calling_permission(obj: dict[str, Any]) -> list[MigrationOp]:
    """Calling permission → 0-1 ops: assign op per assigned user (tier 5).

    No standalone create op — Webex permissions are per-user, not standalone
    resources. Only generates an assign op if there are users to apply to.
    """
    cid = obj["canonical_id"]
    assigned_users = obj.get("assigned_users", [])
    if not assigned_users:
        return []

    api_calls = len(assigned_users)
    return [MigrationOp(
        canonical_id=cid,
        op_type="assign",
        resource_type="calling_permission",
        tier=TIER_ASSIGNMENTS[("calling_permission", "assign")],
        batch="org-wide",
        api_calls=api_calls,
        description=f"Assign calling permissions to {api_calls} users",
        depends_on=[_node_id(uid, "create") for uid in assigned_users],
    )]


def _expand_hunt_group(obj: dict[str, Any]) -> list[MigrationOp]:
    """Hunt group → 1 op: create (tier 4)."""
    cid = obj["canonical_id"]
    name = obj.get("name", cid)
    loc_id = _location_from_provenance(obj)
    deps = [_node_id(uid, "create") for uid in obj.get("agents", [])]
    return [_op(cid, "create", "hunt_group", f"Create hunt group {name}",
                depends_on=deps, batch=loc_id)]


def _expand_call_queue(obj: dict[str, Any]) -> list[MigrationOp]:
    """Call queue → 1 op: create (tier 4)."""
    cid = obj["canonical_id"]
    name = obj.get("name", cid)
    loc_id = _location_from_provenance(obj)
    deps = [_node_id(uid, "create") for uid in obj.get("agents", [])]
    return [_op(cid, "create", "call_queue", f"Create call queue {name}",
                depends_on=deps, batch=loc_id)]


def _expand_auto_attendant(obj: dict[str, Any]) -> list[MigrationOp]:
    """Auto attendant → 1 op: create (tier 4, api_calls=2)."""
    cid = obj["canonical_id"]
    name = obj.get("name", cid)
    loc_id = _location_from_provenance(obj)
    return [_op(cid, "create", "auto_attendant", f"Create auto attendant {name}",
                batch=loc_id)]


def _expand_call_park(obj: dict[str, Any]) -> list[MigrationOp]:
    """Call park → 1 op: create (tier 4)."""
    cid = obj["canonical_id"]
    name = obj.get("name") or obj.get("extension") or cid
    loc_id = obj.get("location_id")
    return [_op(cid, "create", "call_park", f"Create call park {name}",
                batch=loc_id)]


def _expand_pickup_group(obj: dict[str, Any]) -> list[MigrationOp]:
    """Pickup group → 1 op: create (tier 4)."""
    cid = obj["canonical_id"]
    name = obj.get("name", cid)
    loc_id = _location_from_provenance(obj)
    deps = [_node_id(uid, "create") for uid in obj.get("agents", [])]
    return [_op(cid, "create", "pickup_group", f"Create pickup group {name}",
                depends_on=deps, batch=loc_id)]


def _expand_paging_group(obj: dict[str, Any]) -> list[MigrationOp]:
    """Paging group → 1 op: create (tier 4)."""
    cid = obj["canonical_id"]
    name = obj.get("name", cid)
    loc_id = _location_from_provenance(obj)
    deps = [_node_id(uid, "create") for uid in obj.get("targets", [])]
    return [_op(cid, "create", "paging_group", f"Create paging group {name}",
                depends_on=deps, batch=loc_id)]


def _expand_shared_line(obj: dict[str, Any], decisions: list[dict[str, Any]]) -> list[MigrationOp]:
    """Shared line → 1 op: configure (tier 6).
    Decision SHARED_LINE_COMPLEX can change expansion:
      - 'virtual_line' → creates a virtual line instead (handled via virtual_line object)
      - 'skip' → no operations
    """
    choice = _decision_chosen(decisions, "SHARED_LINE_COMPLEX")
    if choice == "skip":
        return []
    if choice == "virtual_line":
        # Virtual line creation handled by the CanonicalVirtualLine object
        # that was created during analysis. No shared_line ops needed.
        return []

    cid = obj["canonical_id"]
    owner_ids = obj.get("owner_canonical_ids", [])
    deps = [_node_id(uid, "create") for uid in owner_ids]
    # Batch assignment deferred — shared lines span users which may be in
    # different sites. The batch partitioner handles unassigned ops as org-wide.
    return [_op(cid, "configure", "shared_line",
                f"Configure shared line appearances for {cid}",
                depends_on=deps)]


def _expand_virtual_line(obj: dict[str, Any]) -> list[MigrationOp]:
    """Virtual line → 2 ops: create (tier 6), configure (tier 6)."""
    cid = obj["canonical_id"]
    name = obj.get("display_name") or obj.get("extension") or cid
    loc_id = obj.get("location_id")
    return [
        _op(cid, "create", "virtual_line", f"Create virtual line {name}",
            batch=loc_id),
        _op(cid, "configure", "virtual_line", f"Configure virtual line {name}",
            depends_on=[_node_id(cid, "create")], batch=loc_id),
    ]


def _expand_line_key_template(obj: dict[str, Any]) -> list[MigrationOp]:
    """Line key template → 1 op: create (tier 1, org-wide).
    Skip if phones_using == 0 (dead template — nothing will reference it).
    """
    if obj.get("phones_using", 0) == 0:
        return []
    cid = obj["canonical_id"]
    name = obj.get("name") or cid
    return [_op(cid, "create", "line_key_template", f"Create line key template {name}")]


def _expand_call_forwarding(obj: dict[str, Any]) -> list[MigrationOp]:
    """Call forwarding → 0-1 ops: configure (tier 5).
    Skip if all forwarding types are disabled.
    batch=None — the batch partitioner assigns unassigned ops as org-wide.
    """
    if not any([
        obj.get("always_enabled"),
        obj.get("busy_enabled"),
        obj.get("no_answer_enabled"),
    ]):
        return []
    cid = obj["canonical_id"]
    user_cid = obj.get("user_canonical_id")
    deps = [_node_id(user_cid, "create")] if user_cid else []
    return [_op(cid, "configure", "call_forwarding",
                f"Configure call forwarding for {cid}",
                depends_on=deps)]


def _expand_single_number_reach(obj: dict[str, Any]) -> list[MigrationOp]:
    """Single Number Reach → 0-1 ops: configure (tier 5).
    Skip if no numbers.
    """
    if not obj.get("numbers"):
        return []
    cid = obj["canonical_id"]
    user_cid = obj.get("user_canonical_id")
    deps = [_node_id(user_cid, "create")] if user_cid else []
    return [_op(cid, "configure", "single_number_reach",
                f"Configure SNR for {cid}",
                depends_on=deps)]


def _expand_monitoring_list(obj: dict[str, Any]) -> list[MigrationOp]:
    """Monitoring list → 0-1 ops: configure (tier 6).
    Skip if no monitored_members.
    batch=None — the batch partitioner assigns unassigned ops as org-wide.
    """
    if not obj.get("monitored_members"):
        return []
    cid = obj["canonical_id"]
    user_cid = obj.get("user_canonical_id")
    deps = [_node_id(user_cid, "create")] if user_cid else []
    for m in obj.get("monitored_members", []):
        target_cid = m.get("target_canonical_id")
        if target_cid:
            deps.append(_node_id(target_cid, "create"))
    return [_op(cid, "configure", "monitoring_list",
                f"Configure monitoring list for {cid}",
                depends_on=deps)]


def _expand_device_layout(obj: dict[str, Any]) -> list[MigrationOp]:
    """Device layout → 0-1 ops: configure (tier 7).
    Skip if no resolved_line_keys and no template referenced.
    batch=None — the batch partitioner assigns unassigned ops as org-wide.
    """
    resolved_keys = obj.get("resolved_line_keys", [])
    template_cid = obj.get("template_canonical_id")
    if not resolved_keys and not template_cid:
        return []
    cid = obj["canonical_id"]
    deps = []
    device_cid = obj.get("device_canonical_id")
    if device_cid:
        deps.append(_node_id(device_cid, "create"))
    if template_cid:
        deps.append(_node_id(template_cid, "create"))
    owner_cid = obj.get("owner_canonical_id")
    if owner_cid:
        deps.append(_node_id(owner_cid, "create"))
    for m in obj.get("line_members", []):
        member_cid = m.get("member_canonical_id")
        if member_cid:
            deps.append(_node_id(member_cid, "create"))
    return [_op(cid, "configure", "device_layout",
                f"Configure layout for {cid}",
                depends_on=deps)]


def _expand_softkey_config(obj: dict[str, Any]) -> list[MigrationOp]:
    """Softkey config → 0-1 ops: configure (tier 7).
    Only per-device objects (is_psk_target=True) produce ops.
    Template-level objects (is_psk_target=False) are report-only.
    batch=None — the batch partitioner assigns unassigned ops as org-wide.
    """
    if not obj.get("is_psk_target"):
        return []
    device_cid = obj.get("device_canonical_id")
    if not device_cid:
        return []
    cid = obj["canonical_id"]
    return [_op(cid, "configure", "softkey_config",
                f"Configure PSK softkeys for {cid}",
                depends_on=[_node_id(device_cid, "create")])]


def _expand_device_settings_template(obj: dict[str, Any], decisions: list) -> list[MigrationOp]:
    """device_settings_template → location settings + per-device overrides."""
    cid = obj["canonical_id"]
    settings = obj.get("settings") or {}
    phones_using = obj.get("phones_using", 0)
    if not settings or phones_using == 0:
        return []

    family = obj.get("model_family", "unknown")
    loc_id = obj.get("location_canonical_id", "unknown")
    ops = [
        _op(cid, "apply_location_settings", "device_settings_template",
            f"Apply {family} device settings at {loc_id}"),
    ]

    for override in obj.get("per_device_overrides", []):
        dev_cid = override.get("device_canonical_id", "")
        ops.append(_op(
            cid, "apply_device_override", "device_settings_template",
            f"Override device settings for {dev_cid}",
            depends_on=[_node_id(cid, "apply_location_settings")],
        ))

    return ops


def _expand_device_profile(obj: dict[str, Any]) -> list[MigrationOp]:
    """Device profile → 1-2 ops: enable_hoteling_guest (tier 5), enable_hoteling_host (tier 5).
    Guest op requires user_canonical_id. Host op requires host_device_canonical_ids.
    """
    cid = obj["canonical_id"]
    name = obj.get("profile_name") or cid
    user_cid = obj.get("user_canonical_id")
    ops: list[MigrationOp] = []

    if obj.get("hoteling_guest_enabled") and user_cid:
        ops.append(_op(cid, "enable_hoteling_guest", "device_profile",
                        f"Enable hoteling guest for {name}",
                        depends_on=[_node_id(user_cid, "create")]))

    host_cids = obj.get("host_device_canonical_ids") or []
    if host_cids and user_cid:
        deps = [_node_id(user_cid, "create")]
        for hcid in host_cids:
            deps.append(_node_id(hcid, "create"))
        ops.append(_op(cid, "enable_hoteling_host", "device_profile",
                        f"Configure hoteling host for {name}",
                        depends_on=deps))

    return ops


def _expand_hoteling_location(obj: dict[str, Any]) -> list[MigrationOp]:
    """Hoteling location → 1 op: enable_hotdesking (tier 0).
    Enables voice portal hot desk sign-in at a location with EM phones.
    """
    cid = obj["canonical_id"]
    state = obj.get("pre_migration_state") or {}
    loc_cid = state.get("location_canonical_id", "")
    deps = [_node_id(loc_cid, "enable_calling")] if loc_cid else []
    return [_op(cid, "enable_hotdesking", "hoteling_location",
                f"Enable hot desking at {loc_cid}",
                depends_on=deps)]


# ---------------------------------------------------------------------------
# Types that don't produce standalone operations
# ---------------------------------------------------------------------------

_DATA_ONLY_TYPES = {
    "line": "Data consumed by user:create (extension) / workspace:assign_number",
    "voicemail_profile": "Data consumed by user:configure_voicemail",
}


# ---------------------------------------------------------------------------
# Location helper
# ---------------------------------------------------------------------------

def _location_from_provenance(obj: dict[str, Any]) -> str | None:
    """Extract location_id from object data. Features may store it differently."""
    return obj.get("location_id")


# ---------------------------------------------------------------------------
# Expansion dispatch
# All expanders take (obj_data, decisions) for uniformity.
# ---------------------------------------------------------------------------



def _expand_receptionist_config(obj: dict) -> list:
    """Receptionist config -> 0-1 ops: configure (tier 6)."""
    cid = obj["canonical_id"]
    user_cid = obj.get("user_canonical_id")
    deps = [_node_id(user_cid, "create")] if user_cid else []
    for member_cid in obj.get("monitored_members", []):
        if member_cid:
            deps.append(_node_id(member_cid, "create"))
    loc_cid = obj.get("location_canonical_id")
    if loc_cid:
        deps.append(_node_id(loc_cid, "create"))
    return [_op(cid, "configure", "receptionist_config",
                f"Configure receptionist client for {cid}",
                depends_on=deps)]

_EXPANDERS: dict[str, Any] = {
    "location": lambda obj, _: _expand_location(obj),
    "trunk": lambda obj, _: _expand_trunk(obj),
    "route_group": lambda obj, _: _expand_route_group(obj),
    "route_list": lambda obj, _: _expand_route_list(obj),
    "operating_mode": lambda obj, _: _expand_operating_mode(obj),
    "schedule": lambda obj, _: _expand_schedule(obj),
    "user": lambda obj, _: _expand_user(obj),
    "workspace": lambda obj, _: _expand_workspace(obj),
    "device": lambda obj, decs: _expand_device(obj, decs),
    "dial_plan": lambda obj, _: _expand_dial_plan(obj),
    "translation_pattern": lambda obj, _: _expand_translation_pattern(obj),
    "calling_permission": lambda obj, _: _expand_calling_permission(obj),
    "hunt_group": lambda obj, _: _expand_hunt_group(obj),
    "call_queue": lambda obj, _: _expand_call_queue(obj),
    "auto_attendant": lambda obj, _: _expand_auto_attendant(obj),
    "call_park": lambda obj, _: _expand_call_park(obj),
    "pickup_group": lambda obj, _: _expand_pickup_group(obj),
    "paging_group": lambda obj, _: _expand_paging_group(obj),
    "shared_line": lambda obj, decs: _expand_shared_line(obj, decs),
    "virtual_line": lambda obj, _: _expand_virtual_line(obj),
    "line_key_template": lambda obj, _: _expand_line_key_template(obj),
    "call_forwarding": lambda obj, _: _expand_call_forwarding(obj),
    "single_number_reach": lambda obj, _: _expand_single_number_reach(obj),
    "monitoring_list": lambda obj, _: _expand_monitoring_list(obj),
    "receptionist_config": lambda obj, _: _expand_receptionist_config(obj),
    "device_layout": lambda obj, _: _expand_device_layout(obj),
    "softkey_config": lambda obj, _: _expand_softkey_config(obj),
    "device_settings_template": lambda obj, d: _expand_device_settings_template(obj, d),
    "device_profile": lambda obj, _: _expand_device_profile(obj),
    "hoteling_location": lambda obj, _: _expand_hoteling_location(obj),
}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def expand_to_operations(store: MigrationStore) -> list[MigrationOp]:
    """Expand each analyzed canonical object into its constituent API operations.

    Only objects at status 'analyzed' are expanded. Objects at 'needs_decision'
    are skipped — they have pending decisions that must be resolved first.

    Generic skip: any object with a resolved "skip" decision of type
    DEVICE_INCOMPATIBLE, DEVICE_FIRMWARE_CONVERTIBLE, EXTENSION_CONFLICT,
    or LOCATION_AMBIGUOUS is suppressed entirely (no ops produced).

    Special handling: SHARED_LINE_COMPLEX decisions are checked inside
    the shared_line expander (supports "virtual_line" option in addition
    to "skip").

    (from 05-dependency-graph.md lines 38-75,
     phase-07-planning.md lines 26-27)
    """
    analyzed_objects = store.query_by_status("analyzed")
    all_ops: list[MigrationOp] = []
    skipped_data_only = 0
    skipped_by_decision = 0

    # Build decisions index once (avoids O(objects * decisions) repeated queries)
    decisions_index = _build_decisions_index(store)

    for obj in analyzed_objects:
        obj_data = obj.model_dump()
        cid = obj_data["canonical_id"]
        # Derive object_type from canonical_id prefix (e.g., "user:0001" → "user")
        obj_type = cid.split(":")[0] if ":" in cid else "unknown"

        # Data-only types don't produce operations
        if obj_type in _DATA_ONLY_TYPES:
            skipped_data_only += 1
            continue

        expander = _EXPANDERS.get(obj_type)
        if expander is None:
            logger.warning("No expansion pattern for object type '%s' (id=%s)", obj_type, cid)
            continue

        decisions = decisions_index.get(cid, [])

        # Generic skip: any _SKIP_DECISION_TYPES resolved as "skip" → suppress object
        if _any_skip_decision(decisions):
            skipped_by_decision += 1
            continue

        # Patch location_id from resolved LOCATION_AMBIGUOUS decision
        # (e.g., trunk with no device pool where user picked a location)
        loc_choice = _decision_chosen(decisions, "LOCATION_AMBIGUOUS")
        if loc_choice and loc_choice != "skip" and not obj_data.get("location_id"):
            obj_data["location_id"] = loc_choice
            # Persist the patched location_id back to the store object
            if hasattr(obj, "location_id"):
                obj.location_id = loc_choice
                store.upsert_object(obj)

        ops = expander(obj_data, decisions)
        all_ops.extend(ops)

    logger.info(
        "Expanded %d analyzed objects into %d operations "
        "(%d data-only skipped, %d skipped by decision)",
        len(analyzed_objects) - skipped_data_only - skipped_by_decision,
        len(all_ops),
        skipped_data_only,
        skipped_by_decision,
    )
    return all_ops
