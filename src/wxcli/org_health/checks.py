from __future__ import annotations

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
