from __future__ import annotations

from collections import Counter
from typing import Any, Callable

from wxcli.org_health.models import Finding

CheckFn = Callable[[dict[str, Any]], list[Finding]]
ALL_CHECKS: list[CheckFn] = []


def check(category: str):
    def decorator(fn: CheckFn) -> CheckFn:
        fn._check_category = category  # type: ignore[attr-defined]
        ALL_CHECKS.append(fn)
        return fn
    return decorator


def run_all_checks(data: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    for check_fn in ALL_CHECKS:
        findings.extend(check_fn(data))
    return findings


# ---------------------------------------------------------------------------
# Feature Utilization checks
# ---------------------------------------------------------------------------

@check("feature_utilization")
def check_disabled_auto_attendants(data: dict[str, Any]) -> list[Finding]:
    disabled = [aa for aa in data.get("auto_attendants", []) if not aa.get("enabled", True)]
    if not disabled:
        return []
    return [Finding(
        check_name="disabled_auto_attendants",
        category="feature_utilization",
        severity="MEDIUM",
        title=f"{len(disabled)} Auto Attendant{'s are' if len(disabled) != 1 else ' is'} disabled",
        detail="Disabled auto attendants consume configuration space without serving callers. They may be leftovers from testing or seasonal changes.",
        affected_items=[{"id": aa.get("id"), "name": aa.get("name"), "location": aa.get("locationName")} for aa in disabled],
        recommendation="Enable or delete these auto attendants.",
    )]


@check("feature_utilization")
def check_understaffed_call_queues(data: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    zero_agent = []
    one_agent = []
    for cq in data.get("call_queues", []):
        agents = cq.get("agents", [])
        if len(agents) == 0:
            zero_agent.append(cq)
        elif len(agents) == 1:
            one_agent.append(cq)
    if zero_agent:
        findings.append(Finding(
            check_name="understaffed_call_queues",
            category="feature_utilization",
            severity="HIGH",
            title=f"{len(zero_agent)} Call Queue{'s have' if len(zero_agent) != 1 else ' has'} zero agents",
            detail="Call queues with no agents will send all callers to overflow or voicemail immediately. This is usually a configuration error.",
            affected_items=[{"id": cq.get("id"), "name": cq.get("name"), "location": cq.get("locationName")} for cq in zero_agent],
            recommendation="Assign agents to these queues or delete them if no longer needed.",
        ))
    if one_agent:
        findings.append(Finding(
            check_name="understaffed_call_queues",
            category="feature_utilization",
            severity="MEDIUM",
            title=f"{len(one_agent)} Call Queue{'s have' if len(one_agent) != 1 else ' has'} only one agent",
            detail="Single-agent queues offer no redundancy. If the agent is unavailable, all calls go to overflow.",
            affected_items=[{"id": cq.get("id"), "name": cq.get("name"), "location": cq.get("locationName")} for cq in one_agent],
            recommendation="Add backup agents or convert to a direct line if redundancy is not needed.",
        ))
    return findings


@check("feature_utilization")
def check_single_member_hunt_groups(data: dict[str, Any]) -> list[Finding]:
    single = [hg for hg in data.get("hunt_groups", []) if len(hg.get("agents", [])) == 1]
    if not single:
        return []
    return [Finding(
        check_name="single_member_hunt_groups",
        category="feature_utilization",
        severity="MEDIUM",
        title=f"{len(single)} Hunt Group{'s have' if len(single) != 1 else ' has'} only one member",
        detail="A hunt group with a single member provides no hunt functionality. Calls will ring one person.",
        affected_items=[{"id": hg.get("id"), "name": hg.get("name"), "location": hg.get("locationName")} for hg in single],
        recommendation="Add members for redundancy or replace with a direct line.",
    )]


@check("feature_utilization")
def check_empty_voicemail_groups(data: dict[str, Any]) -> list[Finding]:
    empty = [vg for vg in data.get("voicemail_groups", []) if len(vg.get("members", [])) == 0]
    if not empty:
        return []
    return [Finding(
        check_name="empty_voicemail_groups",
        category="feature_utilization",
        severity="LOW",
        title=f"{len(empty)} Voicemail Group{'s have' if len(empty) != 1 else ' has'} no members",
        detail="Voicemail groups with no members will not deliver messages to anyone.",
        affected_items=[{"id": vg.get("id"), "name": vg.get("name"), "location": vg.get("locationName")} for vg in empty],
        recommendation="Add members or delete unused voicemail groups.",
    )]


@check("feature_utilization")
def check_empty_paging_groups(data: dict[str, Any]) -> list[Finding]:
    empty = [pg for pg in data.get("paging_groups", []) if len(pg.get("targets", [])) == 0]
    if not empty:
        return []
    return [Finding(
        check_name="empty_paging_groups",
        category="feature_utilization",
        severity="LOW",
        title=f"{len(empty)} Paging Group{'s have' if len(empty) != 1 else ' has'} no targets",
        detail="Paging groups with no targets will not page anyone.",
        affected_items=[{"id": pg.get("id"), "name": pg.get("name"), "location": pg.get("locationName")} for pg in empty],
        recommendation="Add targets or delete unused paging groups.",
    )]


@check("feature_utilization")
def check_empty_call_parks(data: dict[str, Any]) -> list[Finding]:
    empty = [cp for cp in data.get("call_parks", []) if len(cp.get("callParkExtensions", [])) == 0]
    if not empty:
        return []
    return [Finding(
        check_name="empty_call_parks",
        category="feature_utilization",
        severity="LOW",
        title=f"{len(empty)} Call Park{'s have' if len(empty) != 1 else ' has'} no extensions",
        detail="Call park groups with no extensions cannot park calls.",
        affected_items=[{"id": cp.get("id"), "name": cp.get("name"), "location": cp.get("locationName")} for cp in empty],
        recommendation="Add park extensions or delete unused call park groups.",
    )]


# ---------------------------------------------------------------------------
# Device Health checks
# ---------------------------------------------------------------------------

_ONLINE_STATUSES = {"connected", "connected_with_issues", "online", "registered"}


@check("device_health")
def check_offline_devices(data: dict[str, Any]) -> list[Finding]:
    offline = [
        d for d in data.get("devices", [])
        if d.get("connectionStatus", "").lower() not in _ONLINE_STATUSES
    ]
    if not offline:
        return []
    return [Finding(
        check_name="offline_devices",
        category="device_health",
        severity="HIGH",
        title=f"{len(offline)} device{'s are' if len(offline) != 1 else ' is'} offline",
        detail="Offline devices cannot make or receive calls. This may indicate network issues, power failures, or decommissioned hardware.",
        affected_items=[
            {"id": d.get("id"), "name": d.get("displayName"), "product": d.get("product"),
             "status": d.get("connectionStatus")}
            for d in offline
        ],
        recommendation="Investigate connectivity for offline devices. Decommission any that are no longer in use.",
    )]


@check("device_health")
def check_device_limit_users(data: dict[str, Any]) -> list[Finding]:
    device_counts = Counter(
        d.get("personId") for d in data.get("devices", []) if d.get("personId")
    )
    user_map = {u["id"]: u for u in data.get("users", [])}
    at_limit = [
        (pid, count) for pid, count in device_counts.items() if count >= 5
    ]
    if not at_limit:
        return []
    return [Finding(
        check_name="device_limit_users",
        category="device_health",
        severity="MEDIUM",
        title=f"{len(at_limit)} user{'s are' if len(at_limit) != 1 else ' is'} at or near the 5-device limit",
        detail="Webex enforces a hard limit of 5 devices per user. Users at this limit cannot add new devices without removing existing ones.",
        affected_items=[
            {"id": pid, "name": user_map.get(pid, {}).get("displayName", "Unknown"),
             "device_count": count}
            for pid, count in at_limit
        ],
        recommendation="Review device assignments and remove unused devices for affected users.",
    )]


@check("device_health")
def check_unassigned_devices(data: dict[str, Any]) -> list[Finding]:
    unassigned = [
        d for d in data.get("devices", [])
        if not d.get("personId") and not d.get("workspaceId")
    ]
    if not unassigned:
        return []
    return [Finding(
        check_name="unassigned_devices",
        category="device_health",
        severity="MEDIUM",
        title=f"{len(unassigned)} device{'s are' if len(unassigned) != 1 else ' is'} unassigned",
        detail="Devices without an owner (person or workspace) cannot be used for calling. They may have been orphaned during a user deletion.",
        affected_items=[
            {"id": d.get("id"), "name": d.get("displayName"), "product": d.get("product")}
            for d in unassigned
        ],
        recommendation="Assign these devices to users or workspaces, or delete them.",
    )]


@check("device_health")
def check_deviceless_workspaces(data: dict[str, Any]) -> list[Finding]:
    workspace_ids_with_devices = {
        d.get("workspaceId") for d in data.get("devices", []) if d.get("workspaceId")
    }
    calling_workspaces = [
        ws for ws in data.get("workspaces", [])
        if ws.get("calling", {}).get("type") == "webexCalling"
        and ws.get("id") not in workspace_ids_with_devices
    ]
    if not calling_workspaces:
        return []
    return [Finding(
        check_name="deviceless_workspaces",
        category="device_health",
        severity="LOW",
        title=f"{len(calling_workspaces)} workspace{'s have' if len(calling_workspaces) != 1 else ' has'} calling enabled but no device",
        detail="Workspaces with Webex Calling enabled but no device assigned cannot make or receive calls.",
        affected_items=[
            {"id": ws.get("id"), "name": ws.get("displayName")}
            for ws in calling_workspaces
        ],
        recommendation="Assign a device to these workspaces or disable calling if not needed.",
    )]


@check("device_health")
def check_stale_activation_codes(data: dict[str, Any]) -> list[Finding]:
    stale = [
        d for d in data.get("devices", [])
        if d.get("activationState", "").lower() == "activating"
    ]
    if not stale:
        return []
    return [Finding(
        check_name="stale_activation_codes",
        category="device_health",
        severity="LOW",
        title=f"{len(stale)} device{'s have' if len(stale) != 1 else ' has'} pending activation codes",
        detail="Devices in 'activating' state have an activation code that hasn't been used. The code may have expired or been forgotten.",
        affected_items=[
            {"id": d.get("id"), "name": d.get("displayName"), "product": d.get("product")}
            for d in stale
        ],
        recommendation="Complete device activation or regenerate expired codes.",
    )]


# ---------------------------------------------------------------------------
# Security Posture checks
# ---------------------------------------------------------------------------

@check("security")
def check_aa_external_transfer(data: dict[str, Any]) -> list[Finding]:
    transfer_enabled = [
        aa for aa in data.get("auto_attendants", [])
        if aa.get("transferEnabled", False)
    ]
    if not transfer_enabled:
        return []
    return [Finding(
        check_name="aa_external_transfer",
        category="security",
        severity="MEDIUM",
        title=f"{len(transfer_enabled)} Auto Attendant{'s allow' if len(transfer_enabled) != 1 else ' allows'} external transfers",
        detail="Auto attendants with transfer enabled can be used by external callers to place outbound calls through your system (toll fraud vector).",
        affected_items=[
            {"id": aa.get("id"), "name": aa.get("name"), "location": aa.get("locationName")}
            for aa in transfer_enabled
        ],
        recommendation="Disable external transfer unless explicitly required. Restrict transfer destinations to internal extensions.",
    )]


@check("security")
def check_queues_without_recording(data: dict[str, Any]) -> list[Finding]:
    no_recording = []
    for cq in data.get("call_queues", []):
        detail = data.get("call_queue_details", {}).get(cq.get("id", ""), {})
        recording = detail.get("callRecording", {})
        if not detail or not recording.get("enabled", False):
            no_recording.append(cq)
    if not no_recording:
        return []
    return [Finding(
        check_name="queues_without_recording",
        category="security",
        severity="MEDIUM",
        title=f"{len(no_recording)} Call Queue{'s do' if len(no_recording) != 1 else ' does'} not have recording enabled",
        detail="Call queues without recording have no audit trail for customer interactions. This may violate compliance requirements.",
        affected_items=[
            {"id": cq.get("id"), "name": cq.get("name"), "location": cq.get("locationName")}
            for cq in no_recording
        ],
        recommendation="Enable call recording for queues that handle customer interactions.",
    )]


_PREMIUM_CALL_TYPES = {"INTERNATIONAL", "PREMIUM_SERVICES_I", "PREMIUM_SERVICES_II"}


@check("security")
def check_unrestricted_international(data: dict[str, Any]) -> list[Finding]:
    unrestricted_users = []
    for user_id, perm_data in data.get("outgoing_permissions", {}).items():
        permissions = perm_data.get("callingPermissions", [])
        for p in permissions:
            if p.get("callType") in _PREMIUM_CALL_TYPES and p.get("action") == "ALLOW":
                unrestricted_users.append(user_id)
                break
    if not unrestricted_users:
        return []
    sample_size = data.get("manifest", {}).get("sampled_users_for_permissions", len(unrestricted_users))
    return [Finding(
        check_name="unrestricted_international",
        category="security",
        severity="HIGH",
        title=f"{len(unrestricted_users)} of {sample_size} sampled users have unrestricted international/premium dialing",
        detail="Users with unrestricted international or premium service dialing can incur significant toll charges. This is a common toll fraud vector if credentials are compromised.",
        affected_items=[{"id": uid} for uid in unrestricted_users],
        recommendation="Restrict international and premium dialing to users who require it. Use authorization codes for occasional international callers.",
    )]


@check("security")
def check_no_outgoing_restrictions(data: dict[str, Any]) -> list[Finding]:
    no_rules = []
    for user_id, perm_data in data.get("outgoing_permissions", {}).items():
        permissions = perm_data.get("callingPermissions", [])
        if not permissions:
            no_rules.append(user_id)
    if not no_rules:
        return []
    sample_size = data.get("manifest", {}).get("sampled_users_for_permissions", len(no_rules))
    return [Finding(
        check_name="no_outgoing_restrictions",
        category="security",
        severity="MEDIUM",
        title=f"{len(no_rules)} of {sample_size} sampled users have no outgoing permission rules",
        detail="Users without any outgoing permission rules inherit the default org/location policy. Verify the default policy is appropriate.",
        affected_items=[{"id": uid} for uid in no_rules],
        recommendation="Configure explicit outgoing permissions or verify the default policy is restrictive enough.",
    )]


# ---------------------------------------------------------------------------
# Routing Hygiene checks
# ---------------------------------------------------------------------------

@check("routing")
def check_empty_dial_plans(data: dict[str, Any]) -> list[Finding]:
    empty = [
        dp for dp in data.get("dial_plans", [])
        if not dp.get("routeChoices")
    ]
    if not empty:
        return []
    return [Finding(
        check_name="empty_dial_plans",
        category="routing",
        severity="HIGH",
        title=f"{len(empty)} Dial Plan{'s have' if len(empty) != 1 else ' has'} no route choices",
        detail="Dial plans without route choices will not route any calls. Calls matching these patterns will fail.",
        affected_items=[
            {"id": dp.get("id"), "name": dp.get("name")}
            for dp in empty
        ],
        recommendation="Add route choices to these dial plans or delete them if obsolete.",
    )]


@check("routing")
def check_orphan_route_components(data: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    empty_rgs = [
        rg for rg in data.get("route_groups", [])
        if not rg.get("localGateways")
    ]
    if empty_rgs:
        findings.append(Finding(
            check_name="orphan_route_components",
            category="routing",
            severity="MEDIUM",
            title=f"{len(empty_rgs)} Route Group{'s have' if len(empty_rgs) != 1 else ' has'} no trunks",
            detail="Route groups without trunks cannot route calls. They may reference decommissioned gateways.",
            affected_items=[
                {"id": rg.get("id"), "name": rg.get("name")}
                for rg in empty_rgs
            ],
            recommendation="Add trunks to these route groups or delete them.",
        ))
    empty_rls = [
        rl for rl in data.get("route_lists", [])
        if not rl.get("routeGroups")
    ]
    if empty_rls:
        findings.append(Finding(
            check_name="orphan_route_components",
            category="routing",
            severity="MEDIUM",
            title=f"{len(empty_rls)} Route List{'s have' if len(empty_rls) != 1 else ' has'} no Route Groups",
            detail="Route lists without route groups cannot route calls to any gateway.",
            affected_items=[
                {"id": rl.get("id"), "name": rl.get("name")}
                for rl in empty_rls
            ],
            recommendation="Add route groups to these route lists or delete them.",
        ))
    return findings


_HEALTHY_TRUNK_STATUSES = {"registered", "online", "connected"}


@check("routing")
def check_trunk_errors(data: dict[str, Any]) -> list[Finding]:
    error_trunks = [
        t for t in data.get("trunks", [])
        if t.get("registrationStatus", "").lower() not in _HEALTHY_TRUNK_STATUSES
        and t.get("registrationStatus")  # skip empty/missing status
    ]
    if not error_trunks:
        return []
    return [Finding(
        check_name="trunk_errors",
        category="routing",
        severity="HIGH",
        title=f"{len(error_trunks)} trunk{'s are' if len(error_trunks) != 1 else ' is'} not registered",
        detail="Trunks in error or unregistered state cannot route PSTN calls. This likely indicates a gateway connectivity issue.",
        affected_items=[
            {"id": t.get("id"), "name": t.get("name"), "type": t.get("trunkType"),
             "status": t.get("registrationStatus")}
            for t in error_trunks
        ],
        recommendation="Investigate gateway connectivity and registration for affected trunks.",
    )]
