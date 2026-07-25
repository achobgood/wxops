"""Tests for the membership-reconcile operation.

``proceed_partial`` lets a cross-site group be created in wave 1 with whoever
exists locally. ``reconcile_members`` is what finishes the job on the wave that
provisions the last remote member — without it, ``proceed_partial`` is a promise
the tool cannot keep.

The single most important behaviour here: these endpoints replace the WHOLE
member array, so a short list would delete members rather than add them. The op
must refuse to write at all when any member is unresolved.

(from docs/prompts/cross-site-phase-2.md §7)
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from wxcli.migration.execute.handlers import (
    RECONCILE_RULES,
    SkippedResult,
    handle_reconcile_members,
)
from wxcli.migration.models import (
    CanonicalHuntGroup,
    CanonicalLocation,
    CanonicalPagingGroup,
    CanonicalPickupGroup,
    CanonicalUser,
    DecisionType,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore

LOC_A = "location:site-a"
LOC_B = "location:site-b"


def _prov(name: str = "test") -> Provenance:
    return Provenance(
        source_system="cucm", source_id=name, source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def store() -> MigrationStore:
    s = MigrationStore(":memory:")
    for cid, name in ((LOC_A, "Site A"), (LOC_B, "Site B")):
        s.upsert_object(CanonicalLocation(
            canonical_id=cid, provenance=_prov(cid),
            status=MigrationStatus.ANALYZED, name=name,
        ))
    return s


def _user(store: MigrationStore, uid: str, location: str) -> None:
    store.upsert_object(CanonicalUser(
        canonical_id=uid, provenance=_prov(uid), status=MigrationStatus.ANALYZED,
        display_name=uid.split(":", 1)[-1], location_id=location,
    ))


def _straddling_hunt_group(store: MigrationStore) -> None:
    """Sales rings alice at Site A and carol at Site B."""
    _user(store, "user:alice", LOC_A)
    _user(store, "user:carol", LOC_B)
    store.upsert_object(CanonicalHuntGroup(
        canonical_id="hunt_group:sales", provenance=_prov("sales"),
        status=MigrationStatus.ANALYZED, name="Sales", extension="4000",
        location_id=LOC_A, agents=["user:alice", "user:carol"],
    ))
    # FeatureMapper writes these (Fix 8) — they carry the member edges in the
    # dependency graph, so a store without them does not exercise the real path.
    for agent in ("user:alice", "user:carol"):
        store.add_cross_ref("hunt_group:sales", agent, "feature_has_agent")


def _resolve_cross_site(store: MigrationStore, choice: str) -> None:
    from wxcli.migration.transform.analyzers.cross_site import CrossSiteAnalyzer
    from wxcli.migration.transform.mappers.base import decision_to_store_dict

    decisions = CrossSiteAnalyzer().analyze(store)
    for dec in decisions:
        store.save_decision(decision_to_store_dict(dec))
    target = [
        d for d in decisions
        if d.type == DecisionType.CROSS_SITE_DEPENDENCY
        and d.context.get("construct_id") == "hunt_group:sales"
    ]
    assert len(target) == 1
    store.resolve_decision(
        decision_id=target[0].decision_id, chosen_option=choice, resolved_by="test",
    )


def _plan(store: MigrationStore):
    from wxcli.migration.execute.planner import expand_to_operations

    return expand_to_operations(store, fail_on_unresolved=False)


# ---------------------------------------------------------------------------
# Emission — only on proceed_partial
# ---------------------------------------------------------------------------


def test_reconcile_op_emitted_for_proceed_partial(store):
    _straddling_hunt_group(store)
    _resolve_cross_site(store, "proceed_partial")

    ops = _plan(store)

    reconcile = [o for o in ops if o.op_type == "reconcile_members"]
    assert len(reconcile) == 1
    assert reconcile[0].canonical_id == "hunt_group:sales"
    assert reconcile[0].resource_type == "hunt_group"
    assert reconcile[0].tier == 9
    assert reconcile[0].batch == LOC_A


@pytest.mark.parametrize("choice", ["migrate_together", "skip", LOC_B])
def test_reconcile_op_not_emitted_for_other_choices(store, choice):
    """migrate_together needs none; skip and reassign_home do not apply."""
    _straddling_hunt_group(store)
    _resolve_cross_site(store, choice)

    ops = _plan(store)

    assert [o for o in ops if o.op_type == "reconcile_members"] == []


def test_reconcile_op_not_emitted_without_a_cross_site_decision(store):
    """A group entirely at one site never gets a reconcile op."""
    _user(store, "user:alice", LOC_A)
    _user(store, "user:bob", LOC_A)
    store.upsert_object(CanonicalHuntGroup(
        canonical_id="hunt_group:local", provenance=_prov("local"),
        status=MigrationStatus.ANALYZED, name="Local", extension="4001",
        location_id=LOC_A, agents=["user:alice", "user:bob"],
    ))

    ops = _plan(store)

    assert [o for o in ops if o.op_type == "reconcile_members"] == []


def test_create_op_keeps_its_soft_member_edges(store):
    """The group must still be built in wave 1 — only reconcile gets REQUIRES."""
    from wxcli.migration.execute.dependency import DependencyType, build_dependency_graph

    _straddling_hunt_group(store)
    _resolve_cross_site(store, "proceed_partial")
    ops = _plan(store)
    graph = build_dependency_graph(ops, store)

    create = "hunt_group:sales:create"
    reconcile = "hunt_group:sales:reconcile_members"

    member_edges_on_create = [
        graph.edges[u, create]["type"]
        for u in graph.predecessors(create)
        if u.startswith("user:")
    ]
    assert member_edges_on_create, "create lost its member edges"
    assert set(member_edges_on_create) == {DependencyType.SOFT}

    member_edges_on_reconcile = {
        u: graph.edges[u, reconcile]["type"]
        for u in graph.predecessors(reconcile)
        if u.startswith("user:")
    }
    assert member_edges_on_reconcile == {
        "user:alice:create": DependencyType.REQUIRES,
        "user:carol:create": DependencyType.REQUIRES,
    }


# ---------------------------------------------------------------------------
# The refusal to write a partial list
# ---------------------------------------------------------------------------


def _hunt_group_data() -> dict:
    return {
        "canonical_id": "hunt_group:sales",
        "name": "Sales",
        "location_id": LOC_A,
        "agents": ["user:alice", "user:carol"],
    }


def test_skipped_when_any_member_is_unresolved():
    """A short list would DELETE carol, not add her. Refuse outright."""
    deps = {"hunt_group:sales": "wx-hg", LOC_A: "wx-loc", "user:alice": "wx-alice"}

    result = handle_reconcile_members(_hunt_group_data(), deps, {})

    assert isinstance(result, SkippedResult)
    assert "user:carol" in result.reason
    assert "membership left unchanged" in result.reason


def test_skipped_result_issues_no_api_call():
    """Guard the actual danger: nothing is written when a member is missing."""
    deps = {"hunt_group:sales": "wx-hg", LOC_A: "wx-loc", "user:alice": "wx-alice"}

    result = handle_reconcile_members(_hunt_group_data(), deps, {})

    assert not isinstance(result, list), "a partial membership PUT was emitted"


def test_writes_full_list_once_every_member_resolves():
    deps = {
        "hunt_group:sales": "wx-hg", LOC_A: "wx-loc",
        "user:alice": "wx-alice", "user:carol": "wx-carol",
    }

    result = handle_reconcile_members(_hunt_group_data(), deps, {})

    assert len(result) == 1
    method, url, body = result[0]
    assert method == "PUT"
    assert "/locations/wx-loc/huntGroups/wx-hg" in url
    assert body == {"agents": [{"id": "wx-alice"}, {"id": "wx-carol"}]}


def test_body_carries_only_members_not_the_full_object():
    """Sending a full object back fails on queues with Missing
    callingLineIdPhoneNumber (call-features-major.md:518)."""
    data = {**_hunt_group_data(), "extension": "4000", "phone_number": "+15551234000"}
    deps = {
        "hunt_group:sales": "wx-hg", LOC_A: "wx-loc",
        "user:alice": "wx-alice", "user:carol": "wx-carol",
    }

    _method, _url, body = handle_reconcile_members(data, deps, {})[0]

    assert set(body) == {"agents"}


# ---------------------------------------------------------------------------
# Payload shape per resource type — object vs flat string is a 400
# ---------------------------------------------------------------------------


def test_pickup_group_uses_flat_id_strings():
    data = {
        "canonical_id": "pickup_group:front", "name": "Front Desk",
        "location_id": LOC_A, "agents": ["user:alice", "user:carol"],
    }
    deps = {
        "pickup_group:front": "wx-pg", LOC_A: "wx-loc",
        "user:alice": "wx-alice", "user:carol": "wx-carol",
    }

    _method, url, body = handle_reconcile_members(data, deps, {})[0]

    assert "/callPickups/wx-pg" in url
    assert body == {"agents": ["wx-alice", "wx-carol"]}


def test_paging_group_reconciles_targets_and_originators():
    data = {
        "canonical_id": "paging_group:all", "name": "All Page",
        "location_id": LOC_A,
        "targets": ["user:alice", "user:carol"], "originators": ["user:alice"],
    }
    deps = {
        "paging_group:all": "wx-pag", LOC_A: "wx-loc",
        "user:alice": "wx-alice", "user:carol": "wx-carol",
    }

    _method, url, body = handle_reconcile_members(data, deps, {})[0]

    assert "/paging/wx-pag" in url
    assert body == {
        "targets": ["wx-alice", "wx-carol"],
        "originators": ["wx-alice"],
    }


def test_paging_group_skips_when_an_originator_is_unresolved():
    """Every member field is covered by the no-partial-write rule."""
    data = {
        "canonical_id": "paging_group:all", "name": "All Page",
        "location_id": LOC_A,
        "targets": ["user:alice"], "originators": ["user:carol"],
    }
    deps = {"paging_group:all": "wx-pag", LOC_A: "wx-loc", "user:alice": "wx-alice"}

    result = handle_reconcile_members(data, deps, {})

    assert isinstance(result, SkippedResult)
    assert "originators" in result.reason


def test_call_queue_uses_object_ids():
    data = {
        "canonical_id": "call_queue:support", "name": "Support",
        "location_id": LOC_A, "agents": ["user:alice"],
    }
    deps = {"call_queue:support": "wx-cq", LOC_A: "wx-loc", "user:alice": "wx-alice"}

    _method, url, body = handle_reconcile_members(data, deps, {})[0]

    assert "/queues/wx-cq" in url
    assert body == {"agents": [{"id": "wx-alice"}]}


def test_every_rule_is_registered_as_a_handler():
    from wxcli.migration.execute import API_CALL_ESTIMATES, TIER_ASSIGNMENTS
    from wxcli.migration.execute.handlers import HANDLER_REGISTRY

    for resource_type in RECONCILE_RULES:
        assert (resource_type, "reconcile_members") in HANDLER_REGISTRY
        assert (resource_type, "reconcile_members") in TIER_ASSIGNMENTS
        assert f"{resource_type}:reconcile_members" in API_CALL_ESTIMATES


# ---------------------------------------------------------------------------
# Retry semantics — §7.5
# ---------------------------------------------------------------------------


def test_skipped_when_the_feature_has_no_webex_id():
    """Never a blind create — if the group's id cannot be resolved, skip."""
    deps = {LOC_A: "wx-loc", "user:alice": "wx-alice", "user:carol": "wx-carol"}

    result = handle_reconcile_members(_hunt_group_data(), deps, {})

    assert isinstance(result, SkippedResult)
    assert "no Webex id" in result.reason


def _saved_plan(store: MigrationStore):
    from wxcli.migration.execute.batch import save_plan_to_store
    from wxcli.migration.execute.dependency import build_dependency_graph

    ops = _plan(store)
    graph = build_dependency_graph(ops, store)
    save_plan_to_store(graph, store)
    return ops


def test_reconcile_waits_until_the_last_member_exists(store):
    """The whole point of the hard edges — assert via the real runtime path.

    Wave 1 completes the local member and the group; the reconcile op must NOT
    be handed out while the remote member is still pending.
    """
    from wxcli.migration.execute.runtime import get_next_batch, update_op_status

    _straddling_hunt_group(store)
    _resolve_cross_site(store, "proceed_partial")
    _saved_plan(store)

    for node, wid in (
        (f"{LOC_A}:create", "wx-loc-a"),
        (f"{LOC_B}:create", "wx-loc-b"),
        ("user:alice:create", "wx-alice"),
        ("hunt_group:sales:create", "wx-hg"),
    ):
        update_op_status(store, node, "completed", webex_id=wid)

    # Drain every batch that becomes ready while carol is still pending. A
    # single get_next_batch call would prove nothing — it returns only the
    # lowest (batch, tier) group, so a tier-9 op is absent either way.
    offered: set[str] = set()
    for _ in range(20):
        batch = get_next_batch(store)
        if not batch:
            break
        for op in batch:
            offered.add(op["node_id"])
            if op["node_id"] == "user:carol:create":
                continue  # the member we are deliberately withholding
            update_op_status(store, op["node_id"], "completed", webex_id="wx-x")
    assert "hunt_group:sales:reconcile_members" not in offered, (
        "reconcile became ready while user:carol was still pending"
    )
    assert "user:carol:create" in offered, "test never reached the withheld member"

    # Wave 2 provisions the remote member.
    update_op_status(store, "user:carol:create", "completed", webex_id="wx-carol")

    ready_ops = []
    for _ in range(12):
        batch = get_next_batch(store)
        if not batch:
            break
        ready_ops.extend(batch)
        for op in batch:
            if op["node_id"] == "hunt_group:sales:reconcile_members":
                break
            update_op_status(store, op["node_id"], "completed", webex_id="wx-x")
        if any(o["node_id"] == "hunt_group:sales:reconcile_members" for o in batch):
            break

    reconcile = next(
        o for o in ready_ops if o["node_id"] == "hunt_group:sales:reconcile_members"
    )

    # The real deps the engine would hand the handler — not a hand-built dict.
    deps = reconcile["resolved_deps"]
    assert deps.get("hunt_group:sales") == "wx-hg", (
        "the create op's webex_id did not reach the reconcile op's deps"
    )
    assert deps.get("user:alice") == "wx-alice"
    assert deps.get("user:carol") == "wx-carol"

    result = handle_reconcile_members(reconcile["data"], deps, {})
    assert not isinstance(result, SkippedResult), getattr(result, "reason", "")
    _method, url, body = result[0]
    assert "wx-hg" in url
    assert body == {"agents": [{"id": "wx-alice"}, {"id": "wx-carol"}]}


def test_webex_id_survives_completion_in_plan_operations(store):
    """§7.5 — the id is read from plan_operations, so it outlives the run that set it.

    Scope note: this holds across repeated `execute` runs against ONE saved plan.
    Re-running `wxcli cucm plan` calls save_plan_to_store, which clears
    plan_operations and resets every op to pending with no webex_id — that is a
    pre-existing property of plan persistence, not specific to this op.
    """
    from wxcli.migration.execute.runtime import update_op_status

    _straddling_hunt_group(store)
    _resolve_cross_site(store, "proceed_partial")
    _saved_plan(store)

    update_op_status(
        store, "hunt_group:sales:create", "completed", webex_id="wx-hg-from-run-1",
    )

    row = store.conn.execute(
        "SELECT webex_id, status FROM plan_operations WHERE node_id = ?",
        ("hunt_group:sales:create",),
    ).fetchone()
    assert row["status"] == "completed"
    assert row["webex_id"] == "wx-hg-from-run-1"

    # And the reconcile op is still pending, waiting on its members.
    reconcile_row = store.conn.execute(
        "SELECT status FROM plan_operations WHERE node_id = ?",
        ("hunt_group:sales:reconcile_members",),
    ).fetchone()
    assert reconcile_row["status"] == "pending"


def test_reconcile_is_idempotent_across_replans(store):
    """Re-planning must not duplicate the op."""
    _straddling_hunt_group(store)
    _resolve_cross_site(store, "proceed_partial")

    first = [o for o in _plan(store) if o.op_type == "reconcile_members"]
    second = [o for o in _plan(store) if o.op_type == "reconcile_members"]

    assert len(first) == len(second) == 1
    assert first[0].model_dump() == second[0].model_dump()


def test_rewriting_identical_membership_is_a_stable_no_change(store):
    """Re-running against unchanged membership produces the same body."""
    deps = {
        "hunt_group:sales": "wx-hg", LOC_A: "wx-loc",
        "user:alice": "wx-alice", "user:carol": "wx-carol",
    }

    first = handle_reconcile_members(_hunt_group_data(), deps, {})
    second = handle_reconcile_members(_hunt_group_data(), deps, {})

    assert first == second


# ---------------------------------------------------------------------------
# §6.3 — virtual_line ops emitted from the shared-line object itself
# ---------------------------------------------------------------------------


def _shared_line_resolved_as_virtual_line(store: MigrationStore) -> None:
    from wxcli.migration.models import CanonicalSharedLine

    _user(store, "user:alice", LOC_A)
    _user(store, "user:carol", LOC_A)
    store.upsert_object(CanonicalSharedLine(
        canonical_id="shared_line:2000:PT-Internal", provenance=_prov("sl"),
        status=MigrationStatus.ANALYZED,
        dn_canonical_id="dn:2000:PT-Internal",
        owner_canonical_ids=["user:alice", "user:carol"],
        device_canonical_ids=["device:SEPAAAA", "device:SEPBBBB"],
    ))
    store.save_decision({
        "decision_id": "D9001",
        "type": "SHARED_LINE_COMPLEX",
        "severity": "MEDIUM",
        "summary": "Shared line on two devices",
        "context": {"_affected_objects": ["shared_line:2000:PT-Internal"]},
        "options": [{"id": "virtual_line", "label": "Virtual Line", "impact": "1 VL"}],
        "chosen_option": "virtual_line",
        "resolved_at": "2026-07-24T00:00:00Z",
        "resolved_by": "user",
        "fingerprint": "fp-sl-2000",
        "run_id": "test-run",
    })


def test_virtual_line_ops_land_in_the_owners_site_batch(store):
    """The batch must follow the resolved location, not default to org-wide."""
    _shared_line_resolved_as_virtual_line(store)

    ops = [o for o in _plan(store) if o.resource_type == "virtual_line"]

    assert {o.op_type for o in ops} == {"create", "configure"}
    assert {o.batch for o in ops} == {LOC_A}
    create = next(o for o in ops if o.op_type == "create")
    assert create.payload["location_id"] == LOC_A
    assert create.payload["extension"] == "2000"
    assert create.payload["display_name"] == "Shared 2000"


def test_virtual_line_create_depends_on_owners_and_location(store):
    _shared_line_resolved_as_virtual_line(store)

    create = next(
        o for o in _plan(store)
        if o.resource_type == "virtual_line" and o.op_type == "create"
    )

    assert set(create.depends_on) == {
        "user:alice:create", "user:carol:create", f"{LOC_A}:create",
    }


def test_virtual_line_not_emitted_without_a_resolvable_dn(store):
    """No DN means no extension — skip loudly rather than POST a broken body."""
    from wxcli.migration.execute.planner import PlannerSkipReport, expand_to_operations
    from wxcli.migration.models import CanonicalSharedLine

    _user(store, "user:alice", LOC_A)
    store.upsert_object(CanonicalSharedLine(
        canonical_id="shared_line:orphan", provenance=_prov("orphan"),
        status=MigrationStatus.ANALYZED,
        dn_canonical_id=None, owner_canonical_ids=["user:alice"],
    ))
    store.save_decision({
        "decision_id": "D9002", "type": "SHARED_LINE_COMPLEX", "severity": "MEDIUM",
        "summary": "Shared line", "context": {"_affected_objects": ["shared_line:orphan"]},
        "options": [{"id": "virtual_line", "label": "VL", "impact": "1 VL"}],
        "chosen_option": "virtual_line", "resolved_at": "2026-07-24T00:00:00Z",
        "resolved_by": "user", "fingerprint": "fp-orphan", "run_id": "test-run",
    })

    report = PlannerSkipReport()
    ops = expand_to_operations(store, report=report, fail_on_unresolved=False)

    assert [o for o in ops if o.resource_type == "virtual_line"] == []
    assert "virtual_line_no_extension" in {e.reason for e in report.entries}


def test_shared_line_configure_still_emitted_when_choice_is_not_virtual_line(store):
    """The default path is untouched — only the virtual_line branch changed."""
    from wxcli.migration.models import CanonicalSharedLine

    _user(store, "user:alice", LOC_A)
    store.upsert_object(CanonicalSharedLine(
        canonical_id="shared_line:plain", provenance=_prov("plain"),
        status=MigrationStatus.ANALYZED,
        dn_canonical_id="dn:2001:PT-Internal", owner_canonical_ids=["user:alice"],
    ))

    ops = _plan(store)

    assert [o for o in ops if o.resource_type == "virtual_line"] == []
    assert [
        o for o in ops
        if o.resource_type == "shared_line" and o.op_type == "configure"
    ]
