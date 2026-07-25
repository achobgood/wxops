"""Tests for the cross-site dependency analyzer.

Covers every detector class in docs/prompts/cross-site-dependency-detection.md §6:
Class A (membership), Class B (relationships), Class C (destinations), and
Class D (line identity). Uses a real :memory: SQLite store — no mocks.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from wxcli.migration.models import (
    CanonicalDevice,
    CanonicalExecutiveAssistant,
    CanonicalHuntGroup,
    CanonicalLine,
    CanonicalLocation,
    CanonicalMonitoringList,
    CanonicalPagingGroup,
    CanonicalPickupGroup,
    CanonicalUser,
    DecisionType,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.analyzers.cross_site import (
    CROSS_SITE_RULES,
    CrossSiteAnalyzer,
    _resolve_collector,
    resolve_entity_location,
)

LOC_A = "location:site-a"
LOC_B = "location:site-b"
LOC_C = "location:site-c"


def _prov(name: str = "test") -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id=name,
        source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def store() -> MigrationStore:
    s = MigrationStore(":memory:")
    for cid, name in ((LOC_A, "Site A"), (LOC_B, "Site B"), (LOC_C, "Site C")):
        s.upsert_object(
            CanonicalLocation(
                canonical_id=cid,
                provenance=_prov(cid),
                status=MigrationStatus.ANALYZED,
                name=name,
            )
        )
    return s


def _user(store: MigrationStore, uid: str, location: str, extension: str | None = None):
    store.upsert_object(
        CanonicalUser(
            canonical_id=uid,
            provenance=_prov(uid),
            status=MigrationStatus.ANALYZED,
            display_name=uid.split(":", 1)[-1],
            location_id=location,
            extension=extension,
        )
    )


def _analyze(store: MigrationStore):
    return CrossSiteAnalyzer().analyze(store)


# ---------------------------------------------------------------------------
# Rule table integrity
# ---------------------------------------------------------------------------


def test_every_rule_has_a_collector():
    missing = [r for r in CROSS_SITE_RULES if _resolve_collector(r.member_ref) is None]
    assert missing == []


def test_rule_table_covers_all_detector_classes():
    relations = {r.relation for r in CROSS_SITE_RULES}
    assert relations == {
        "membership",
        "monitoring",
        "delegation",
        "destination",
        "device_placement",
        "line_appearance",
    }


# ---------------------------------------------------------------------------
# Class A — membership
# ---------------------------------------------------------------------------


def test_hunt_group_with_remote_agent_is_flagged(store):
    _user(store, "user:alice", LOC_A)
    _user(store, "user:bob", LOC_A)
    _user(store, "user:carol", LOC_B)
    store.upsert_object(
        CanonicalHuntGroup(
            canonical_id="hunt_group:sales",
            provenance=_prov("sales"),
            status=MigrationStatus.ANALYZED,
            name="Sales",
            location_id=LOC_A,
            agents=["user:alice", "user:bob", "user:carol"],
        )
    )

    decisions = _analyze(store)

    assert len(decisions) == 1
    dec = decisions[0]
    assert dec.type == DecisionType.CROSS_SITE_DEPENDENCY
    assert dec.context["relation"] == "membership"
    assert dec.context["home_location"] == LOC_A
    assert [m["canonical_id"] for m in dec.context["remote_members"]] == ["user:carol"]
    assert dec.context["remote_locations"][0]["location_name"] == "Site B"
    # Home holds the strict majority (2 local vs 1 remote) → MEDIUM
    assert dec.severity == "MEDIUM"


def test_hunt_group_entirely_in_one_location_is_not_flagged(store):
    _user(store, "user:alice", LOC_A)
    _user(store, "user:bob", LOC_A)
    store.upsert_object(
        CanonicalHuntGroup(
            canonical_id="hunt_group:local",
            provenance=_prov("local"),
            status=MigrationStatus.ANALYZED,
            name="Local",
            location_id=LOC_A,
            agents=["user:alice", "user:bob"],
        )
    )

    assert _analyze(store) == []


def test_pickup_group_with_remote_member_is_flagged(store):
    _user(store, "user:alice", LOC_A)
    _user(store, "user:carol", LOC_B)
    store.upsert_object(
        CanonicalPickupGroup(
            canonical_id="pickup_group:front",
            provenance=_prov("front"),
            status=MigrationStatus.ANALYZED,
            name="Front Desk",
            location_id=LOC_A,
            agents=["user:alice", "user:carol"],
        )
    )

    decisions = _analyze(store)

    assert len(decisions) == 1
    assert decisions[0].context["object_type"] == "pickup_group"
    # 1 local vs 1 remote — home does not hold a strict majority
    assert decisions[0].severity == "HIGH"
    assert "pickup group" in decisions[0].context["webex_constraint"].lower()


def test_paging_group_home_comes_from_member_vote(store):
    _user(store, "user:alice", LOC_A)
    _user(store, "user:bob", LOC_A)
    _user(store, "user:carol", LOC_B)
    store.upsert_object(
        CanonicalPagingGroup(
            canonical_id="paging_group:all",
            provenance=_prov("all"),
            status=MigrationStatus.ANALYZED,
            name="All Page",
            targets=["user:alice", "user:bob"],
            originators=["user:carol"],
        )
    )

    decisions = _analyze(store)

    assert len(decisions) == 1
    # CanonicalPagingGroup has no location field — the majority wins.
    assert decisions[0].context["home_location"] == LOC_A
    assert decisions[0].context["location_vote"] == {LOC_A: 2, LOC_B: 1}


def test_three_locations_is_high_severity(store):
    _user(store, "user:alice", LOC_A)
    _user(store, "user:carol", LOC_B)
    _user(store, "user:dave", LOC_C)
    store.upsert_object(
        CanonicalHuntGroup(
            canonical_id="hunt_group:wide",
            provenance=_prov("wide"),
            status=MigrationStatus.ANALYZED,
            name="Wide",
            location_id=LOC_A,
            agents=["user:alice", "user:carol", "user:dave"],
        )
    )

    decisions = _analyze(store)

    assert len(decisions) == 1
    assert decisions[0].severity == "HIGH"
    assert len(decisions[0].context["remote_locations"]) == 2


# ---------------------------------------------------------------------------
# Class B — relationships (home inherited from the owner)
# ---------------------------------------------------------------------------


def test_monitoring_list_watching_remote_line_is_flagged(store):
    _user(store, "user:reception", LOC_A)
    _user(store, "user:remote", LOC_B)
    store.upsert_object(
        CanonicalMonitoringList(
            canonical_id="monitoring_list:reception",
            provenance=_prov("reception"),
            status=MigrationStatus.ANALYZED,
            user_canonical_id="user:reception",
            monitored_members=[
                {"target_canonical_id": "user:remote", "display_label": "Remote"},
                {"target_canonical_id": None, "display_label": "Unresolved"},
            ],
        )
    )

    decisions = _analyze(store)

    assert len(decisions) == 1
    assert decisions[0].context["relation"] == "monitoring"
    assert decisions[0].context["home_location"] == LOC_A
    assert [m["canonical_id"] for m in decisions[0].context["remote_members"]] == ["user:remote"]


def test_executive_assistant_across_sites_is_flagged(store):
    _user(store, "user:exec", LOC_A)
    _user(store, "user:assistant", LOC_B)
    store.upsert_object(
        CanonicalExecutiveAssistant(
            canonical_id="executive_assistant:exec",
            provenance=_prov("exec"),
            status=MigrationStatus.ANALYZED,
            executive_canonical_id="user:exec",
            assistant_canonical_ids=["user:assistant"],
        )
    )

    decisions = _analyze(store)

    assert len(decisions) == 1
    assert decisions[0].context["relation"] == "delegation"
    assert decisions[0].context["home_location"] == LOC_A


def test_device_at_different_site_than_owner_is_flagged(store):
    """One person, a phone at each of two sites — the case that raised this work."""
    _user(store, "user:roamer", LOC_A)
    store.upsert_object(
        CanonicalDevice(
            canonical_id="device:SEP0001",
            provenance=_prov("SEP0001"),
            status=MigrationStatus.ANALYZED,
            display_name="Branch Phone",
            owner_canonical_id="user:roamer",
            location_canonical_id=LOC_B,
        )
    )

    decisions = _analyze(store)

    assert len(decisions) == 1
    assert decisions[0].context["relation"] == "device_placement"
    assert decisions[0].context["home_location"] == LOC_B
    assert [m["canonical_id"] for m in decisions[0].context["remote_members"]] == ["user:roamer"]


def test_device_at_owner_site_is_not_flagged(store):
    _user(store, "user:local", LOC_A)
    store.upsert_object(
        CanonicalDevice(
            canonical_id="device:SEP0002",
            provenance=_prov("SEP0002"),
            status=MigrationStatus.ANALYZED,
            owner_canonical_id="user:local",
            location_canonical_id=LOC_A,
        )
    )

    assert _analyze(store) == []


# ---------------------------------------------------------------------------
# Class C — destinations
# ---------------------------------------------------------------------------


def test_forwarding_to_remote_extension_is_flagged(store):
    _user(store, "user:alice", LOC_A, extension="1001")
    _user(store, "user:carol", LOC_B, extension="2002")
    store.upsert_object(
        CanonicalHuntGroup(
            canonical_id="hunt_group:support",
            provenance=_prov("support"),
            status=MigrationStatus.ANALYZED,
            name="Support",
            location_id=LOC_A,
            agents=["user:alice"],
            forward_no_answer_enabled=True,
            forward_no_answer_destination="2002",
        )
    )

    decisions = _analyze(store)

    assert len(decisions) == 1
    assert decisions[0].context["relation"] == "destination"
    assert [m["canonical_id"] for m in decisions[0].context["remote_members"]] == ["user:carol"]


def test_forwarding_to_external_number_is_not_flagged(store):
    _user(store, "user:alice", LOC_A, extension="1001")
    store.upsert_object(
        CanonicalHuntGroup(
            canonical_id="hunt_group:support",
            provenance=_prov("support"),
            status=MigrationStatus.ANALYZED,
            name="Support",
            location_id=LOC_A,
            agents=["user:alice"],
            forward_busy_enabled=True,
            forward_busy_destination="+15551234567",
        )
    )

    assert _analyze(store) == []


# ---------------------------------------------------------------------------
# Class D — line identity
# ---------------------------------------------------------------------------


def test_shared_dn_on_devices_at_two_sites_is_flagged(store):
    """One owner, two phones, two sites, one shared DID.

    SharedLineAnalyzer skips this (it needs 2+ distinct owners); the cross-site
    detector must catch it because the appearances are in different locations.
    """
    _user(store, "user:exec", LOC_A)
    store.upsert_object(
        CanonicalLine(
            canonical_id="dn:5000",
            provenance=_prov("5000"),
            status=MigrationStatus.ANALYZED,
            extension="5000",
        )
    )
    for cid, loc in (("device:SEP-A", LOC_A), ("device:SEP-B", LOC_B)):
        store.upsert_object(
            CanonicalDevice(
                canonical_id=cid,
                provenance=_prov(cid),
                status=MigrationStatus.ANALYZED,
                display_name=cid.split(":", 1)[-1],
                owner_canonical_id="user:exec",
                location_canonical_id=loc,
            )
        )
    store.add_cross_ref("device:SEP-A", "dn:5000", "device_has_dn")
    store.add_cross_ref("device:SEP-B", "dn:5000", "device_has_dn")

    decisions = _analyze(store)

    line_decisions = [d for d in decisions if d.context["relation"] == "line_appearance"]
    assert len(line_decisions) == 1
    assert line_decisions[0].severity == "HIGH"
    assert line_decisions[0].context["dn_canonical_id"] == "dn:5000"


def test_shared_dn_on_devices_at_one_site_is_not_flagged(store):
    _user(store, "user:exec", LOC_A)
    store.upsert_object(
        CanonicalLine(
            canonical_id="dn:5000",
            provenance=_prov("5000"),
            status=MigrationStatus.ANALYZED,
            extension="5000",
        )
    )
    for cid in ("device:SEP-A", "device:SEP-B"):
        store.upsert_object(
            CanonicalDevice(
                canonical_id=cid,
                provenance=_prov(cid),
                status=MigrationStatus.ANALYZED,
                owner_canonical_id="user:exec",
                location_canonical_id=LOC_A,
            )
        )
        store.add_cross_ref(cid, "dn:5000", "device_has_dn")

    assert _analyze(store) == []


# ---------------------------------------------------------------------------
# Data gaps, idempotency, location resolution
# ---------------------------------------------------------------------------


def test_unresolvable_member_location_is_not_flagged(store):
    """A member with no resolvable location is a data gap, never a false positive."""
    _user(store, "user:alice", LOC_A)
    store.upsert_object(
        CanonicalUser(
            canonical_id="user:nowhere",
            provenance=_prov("nowhere"),
            status=MigrationStatus.ANALYZED,
            display_name="Nowhere",
            location_id=None,
        )
    )
    store.upsert_object(
        CanonicalHuntGroup(
            canonical_id="hunt_group:gap",
            provenance=_prov("gap"),
            status=MigrationStatus.ANALYZED,
            name="Gap",
            location_id=LOC_A,
            agents=["user:alice", "user:nowhere"],
        )
    )

    assert _analyze(store) == []


def test_fingerprint_is_stable_across_runs(store):
    _user(store, "user:alice", LOC_A)
    _user(store, "user:carol", LOC_B)
    store.upsert_object(
        CanonicalHuntGroup(
            canonical_id="hunt_group:sales",
            provenance=_prov("sales"),
            status=MigrationStatus.ANALYZED,
            name="Sales",
            location_id=LOC_A,
            agents=["user:alice", "user:carol"],
        )
    )

    first = _analyze(store)
    second = _analyze(store)

    assert len(first) == len(second) == 1
    assert first[0].fingerprint == second[0].fingerprint


def test_fingerprint_changes_when_membership_changes(store):
    _user(store, "user:alice", LOC_A)
    _user(store, "user:carol", LOC_B)
    _user(store, "user:dave", LOC_B)
    hg = CanonicalHuntGroup(
        canonical_id="hunt_group:sales",
        provenance=_prov("sales"),
        status=MigrationStatus.ANALYZED,
        name="Sales",
        location_id=LOC_A,
        agents=["user:alice", "user:carol"],
    )
    store.upsert_object(hg)
    before = _analyze(store)[0].fingerprint

    hg.agents = ["user:alice", "user:carol", "user:dave"]
    store.upsert_object(hg)
    after = _analyze(store)[0].fingerprint

    assert before != after


def test_resolve_entity_location_inherits_from_owner(store):
    _user(store, "user:alice", LOC_A)
    store.upsert_object(
        CanonicalMonitoringList(
            canonical_id="monitoring_list:alice",
            provenance=_prov("alice"),
            status=MigrationStatus.ANALYZED,
            user_canonical_id="user:alice",
            monitored_members=[],
        )
    )

    assert resolve_entity_location(store, "monitoring_list:alice", {}) == LOC_A
    assert resolve_entity_location(store, "user:missing", {}) is None


# ---------------------------------------------------------------------------
# Planner gate + auto-rule refusal
# ---------------------------------------------------------------------------


def _sales_hunt_group(store: MigrationStore) -> None:
    _user(store, "user:alice", LOC_A)
    _user(store, "user:carol", LOC_B)
    store.upsert_object(
        CanonicalHuntGroup(
            canonical_id="hunt_group:sales",
            provenance=_prov("sales"),
            status=MigrationStatus.ANALYZED,
            name="Sales",
            extension="4000",
            location_id=LOC_A,
            agents=["user:alice", "user:carol"],
        )
    )


def _persist_decisions(store: MigrationStore) -> list:
    from wxcli.migration.transform.mappers.base import decision_to_store_dict

    decisions = _analyze(store)
    for dec in decisions:
        store.save_decision(decision_to_store_dict(dec))
    return decisions


def test_pending_cross_site_decision_blocks_the_construct(store):
    from wxcli.migration.execute.planner import PlannerSkipReport, expand_to_operations

    _sales_hunt_group(store)
    _persist_decisions(store)

    report = PlannerSkipReport()
    ops = expand_to_operations(store, report=report, fail_on_unresolved=False)

    assert [o for o in ops if o.canonical_id == "hunt_group:sales"] == []
    assert "cross_site_unreviewed" in {e.reason for e in report.entries}
    assert report.has_unresolved_skips is True
    assert len([e for e in report.entries if e.canonical_id == 'hunt_group:sales']) == 1


def test_gate_does_not_block_the_remote_member_user(store):
    """Members are listed on the decision for reporting — they must still be created."""
    from wxcli.migration.execute.planner import expand_to_operations

    _sales_hunt_group(store)
    _persist_decisions(store)

    ops = expand_to_operations(store, fail_on_unresolved=False)

    assert [o for o in ops if o.canonical_id == "user:carol"], "remote member was blocked"


def test_resolved_cross_site_decision_releases_the_construct(store):
    from wxcli.migration.execute.planner import expand_to_operations

    _sales_hunt_group(store)
    decisions = _persist_decisions(store)
    store.resolve_decision(
        decision_id=decisions[0].decision_id,
        chosen_option="migrate_together",
        resolved_by="test",
    )

    ops = expand_to_operations(store, fail_on_unresolved=False)

    assert [o for o in ops if o.canonical_id == "hunt_group:sales"]


def test_skip_choice_suppresses_only_the_construct(store):
    from wxcli.migration.execute.planner import expand_to_operations

    _sales_hunt_group(store)
    decisions = _persist_decisions(store)
    store.resolve_decision(
        decision_id=decisions[0].decision_id, chosen_option="skip", resolved_by="test"
    )

    ops = expand_to_operations(store, fail_on_unresolved=False)

    assert [o for o in ops if o.canonical_id == "hunt_group:sales"] == []
    assert [o for o in ops if o.canonical_id == "user:carol"]


def test_auto_rules_refuse_to_resolve_cross_site(store):
    from wxcli.migration.transform.rules import apply_auto_rules

    _sales_hunt_group(store)
    _persist_decisions(store)

    resolved = apply_auto_rules(
        store,
        {"auto_rules": [{"type": "CROSS_SITE_DEPENDENCY", "choice": "proceed_partial"}]},
    )

    assert resolved == 0
    pending = [
        d for d in store.get_all_decisions()
        if d["type"] == "CROSS_SITE_DEPENDENCY" and not d.get("chosen_option")
    ]
    assert len(pending) == 1


# ---------------------------------------------------------------------------
# Reassignment — resolving with a location canonical id moves the construct
# (docs/prompts/cross-site-phase-2.md §5)
# ---------------------------------------------------------------------------


def _resolve_sales(store: MigrationStore, choice: str) -> None:
    decisions = _persist_decisions(store)
    cross_site = [
        d for d in decisions
        if d.type == DecisionType.CROSS_SITE_DEPENDENCY
        and d.context.get("construct_id") == "hunt_group:sales"
    ]
    assert len(cross_site) == 1
    store.resolve_decision(
        decision_id=cross_site[0].decision_id, chosen_option=choice, resolved_by="test"
    )


def test_location_choice_moves_the_construct_and_its_batch(store):
    """LOC_A → LOC_C: an existing location is overridden, and the batch follows."""
    from wxcli.migration.execute.planner import expand_to_operations

    _sales_hunt_group(store)
    _resolve_sales(store, LOC_C)

    ops = expand_to_operations(store, fail_on_unresolved=False)

    hg_ops = [o for o in ops if o.canonical_id == "hunt_group:sales"]
    assert hg_ops, "construct was not expanded"
    assert {o.batch for o in hg_ops} == {LOC_C}
    assert store.get_object("hunt_group:sales")["location_id"] == LOC_C


def test_location_choice_is_logged_old_to_new(store, caplog):
    import logging

    from wxcli.migration.execute.planner import expand_to_operations

    _sales_hunt_group(store)
    _resolve_sales(store, LOC_C)

    with caplog.at_level(logging.INFO, logger="wxcli.migration.execute.planner"):
        expand_to_operations(store, fail_on_unresolved=False)

    moved = [r.getMessage() for r in caplog.records if "Cross-site reassignment" in r.getMessage()]
    assert len(moved) == 1
    assert LOC_A in moved[0] and LOC_C in moved[0]


def test_non_location_choice_does_not_move_the_construct(store):
    """'proceed_partial' is not a location canonical id — the location stands."""
    from wxcli.migration.execute.planner import expand_to_operations

    _sales_hunt_group(store)
    _resolve_sales(store, "proceed_partial")

    ops = expand_to_operations(store, fail_on_unresolved=False)

    hg_ops = [o for o in ops if o.canonical_id == "hunt_group:sales"]
    assert hg_ops
    assert {o.batch for o in hg_ops} == {LOC_A}
    assert store.get_object("hunt_group:sales")["location_id"] == LOC_A


def test_unknown_location_string_does_not_move_the_construct(store):
    """A location id that is not in the store is not a resolution."""
    from wxcli.migration.execute.planner import expand_to_operations

    _sales_hunt_group(store)
    _resolve_sales(store, "location:does-not-exist")

    ops = expand_to_operations(store, fail_on_unresolved=False)

    assert {o.batch for o in ops if o.canonical_id == "hunt_group:sales"} == {LOC_A}
    assert store.get_object("hunt_group:sales")["location_id"] == LOC_A


def test_reassignment_does_not_move_the_remote_member(store):
    """The patch is scoped to context['construct_id'] — members stay where they are."""
    from wxcli.migration.execute.planner import expand_to_operations

    _sales_hunt_group(store)
    _resolve_sales(store, LOC_C)

    ops = expand_to_operations(store, fail_on_unresolved=False)

    assert {o.batch for o in ops if o.canonical_id == "user:carol"} == {LOC_B}
    assert store.get_object("user:carol")["location_id"] == LOC_B


def test_reassignment_uses_location_canonical_id_field_when_that_is_the_name(store):
    """CanonicalDevice carries ``location_canonical_id``, not ``location_id``."""
    from wxcli.migration.execute.planner import expand_to_operations

    _user(store, "user:roamer", LOC_A)
    store.upsert_object(
        CanonicalDevice(
            canonical_id="device:SEP0001",
            provenance=_prov("SEP0001"),
            status=MigrationStatus.ANALYZED,
            display_name="Branch Phone",
            mac="AABBCCDDEEFF",
            owner_canonical_id="user:roamer",
            location_canonical_id=LOC_B,
        )
    )
    decisions = _persist_decisions(store)
    store.resolve_decision(
        decision_id=decisions[0].decision_id, chosen_option=LOC_A, resolved_by="test"
    )

    ops = expand_to_operations(store, fail_on_unresolved=False)

    assert {o.batch for o in ops if o.canonical_id == "device:SEP0001"} == {LOC_A}
    device = store.get_object("device:SEP0001")
    assert device["location_canonical_id"] == LOC_A
    assert "location_id" not in device


def test_reassign_home_option_tells_the_operator_to_name_a_location(store):
    _sales_hunt_group(store)
    decisions = _analyze(store)

    option = next(
        opt
        for dec in decisions
        for opt in dec.options
        if opt.id == "reassign_home"
    )
    assert "location canonical id" in option.impact
    assert LOC_B in option.impact
    assert "wxcli cucm inventory --type location" in option.impact


# ---------------------------------------------------------------------------
# Report surfacing
# ---------------------------------------------------------------------------


def test_appendix_renders_cross_site_section_grouped_by_site_pair(store):
    from wxcli.migration.report.appendix import _cross_site_group

    _sales_hunt_group(store)
    _persist_decisions(store)

    html_out = _cross_site_group(store)

    assert "AF. Cross-Site Dependencies" in html_out
    assert "Site A" in html_out and "Site B" in html_out
    assert "Unreviewed" in html_out
    assert "canonical_id" not in html_out
    assert "hunt_group:" not in html_out


def test_appendix_section_is_empty_without_cross_site_decisions(store):
    from wxcli.migration.report.appendix import _cross_site_group

    assert _cross_site_group(store) == ""


def test_explainer_has_plain_english_template():
    from wxcli.migration.report.explainer import (
        DECISION_TYPE_DISPLAY_NAMES,
        explain_decision,
    )

    assert DECISION_TYPE_DISPLAY_NAMES["CROSS_SITE_DEPENDENCY"] == "Cross-Site Dependency"
    result = explain_decision(
        decision_type="CROSS_SITE_DEPENDENCY",
        severity="HIGH",
        summary="",
        context={
            "relation": "membership",
            "object_name": "Sales",
            "home_location_name": "Site A",
            "remote_locations": [{"location_name": "Site B", "member_count": 1}],
            "remote_members": [{"canonical_id": "user:carol", "display_name": "carol"}],
        },
    )
    assert "Sales" in result["title"]
    assert "Site B" in result["explanation"]
    for jargon in ("canonical", "cross_refs", "CROSS_SITE"):
        assert jargon not in result["explanation"]


# ---------------------------------------------------------------------------
# The two scenarios that prompted this work — end to end
# ---------------------------------------------------------------------------


def test_scenario_one_user_two_sites_shared_did(store):
    """"A user with a phone in site 1 and another phone in site 2, sharing a
    second line (a DID)." Must be detected, gated, and reported.
    """
    from wxcli.migration.execute.planner import PlannerSkipReport, expand_to_operations
    from wxcli.migration.report.appendix import _cross_site_group

    _user(store, "user:exec", LOC_A)
    store.upsert_object(
        CanonicalLine(
            canonical_id="dn:5551000",
            provenance=_prov("5551000"),
            status=MigrationStatus.ANALYZED,
            extension="1000",
            e164="+15555551000",
        )
    )
    for cid, loc in (("device:SEP-HQ", LOC_A), ("device:SEP-BRANCH", LOC_B)):
        store.upsert_object(
            CanonicalDevice(
                canonical_id=cid,
                provenance=_prov(cid),
                status=MigrationStatus.ANALYZED,
                display_name=cid.split(":", 1)[-1],
                owner_canonical_id="user:exec",
                location_canonical_id=loc,
            )
        )
        store.add_cross_ref(cid, "dn:5551000", "device_has_dn")

    decisions = _persist_decisions(store)
    by_relation = {d.context["relation"] for d in decisions}

    # The shared DID across sites, and the phone sitting away from its owner.
    assert "line_appearance" in by_relation
    assert "device_placement" in by_relation
    line_dec = next(d for d in decisions if d.context["relation"] == "line_appearance")
    assert line_dec.severity == "HIGH"

    # Gated: the branch phone is not planned until reviewed; the person still is.
    report = PlannerSkipReport()
    ops = expand_to_operations(store, report=report, fail_on_unresolved=False)
    assert [o for o in ops if o.canonical_id == "device:SEP-BRANCH"] == []
    assert [o for o in ops if o.canonical_id == "user:exec"]
    assert report.has_unresolved_skips is True

    # Reported.
    html_out = _cross_site_group(store)
    assert "Site A" in html_out and "Site B" in html_out
    assert "Shared line" in html_out


def test_scenario_two_cross_site_hunt_group_and_pickup_group(store):
    """"A user in site 2 that is part of the call pickup group or the hunt group
    from site 1." Must be detected, gated, and reported.
    """
    from wxcli.migration.execute.planner import expand_to_operations
    from wxcli.migration.report.appendix import _cross_site_group

    _user(store, "user:hq1", LOC_A)
    _user(store, "user:hq2", LOC_A)
    _user(store, "user:branch", LOC_B)
    store.upsert_object(
        CanonicalHuntGroup(
            canonical_id="hunt_group:sales",
            provenance=_prov("sales"),
            status=MigrationStatus.ANALYZED,
            name="Sales",
            location_id=LOC_A,
            agents=["user:hq1", "user:hq2", "user:branch"],
        )
    )
    store.upsert_object(
        CanonicalPickupGroup(
            canonical_id="pickup_group:front",
            provenance=_prov("front"),
            status=MigrationStatus.ANALYZED,
            name="Front Desk",
            location_id=LOC_A,
            agents=["user:hq1", "user:branch"],
        )
    )

    decisions = _persist_decisions(store)
    constructs = {d.context["construct_id"] for d in decisions}
    assert constructs == {"hunt_group:sales", "pickup_group:front"}

    ops = expand_to_operations(store, fail_on_unresolved=False)
    assert [o for o in ops if o.canonical_id == "hunt_group:sales"] == []
    assert [o for o in ops if o.canonical_id == "pickup_group:front"] == []
    # The site-2 person is still provisioned — only the groups are held.
    assert [o for o in ops if o.canonical_id == "user:branch"]

    html_out = _cross_site_group(store)
    assert "Sales" in html_out and "Front Desk" in html_out
    assert "branch" in html_out  # the remote member is named
    assert "2 of 2 still need a decision" in html_out


def test_auto_attendant_menu_key_to_remote_extension_is_flagged(store):
    from wxcli.migration.models import CanonicalAutoAttendant

    _user(store, "user:carol", LOC_B, extension="2002")
    store.upsert_object(
        CanonicalAutoAttendant(
            canonical_id="auto_attendant:main",
            provenance=_prov("main"),
            status=MigrationStatus.ANALYZED,
            name="Main AA",
            location_id=LOC_A,
            business_hours_menu={
                "greeting": "DEFAULT",
                "keyConfigurations": [
                    {"key": "0", "action": "TRANSFER_TO_OPERATOR", "value": "0"},
                    {"key": "2", "action": "TRANSFER_WITHOUT_PROMPT", "value": "2002"},
                ],
            },
            after_hours_menu={"greeting": "DEFAULT", "keyConfigurations": []},
        )
    )

    decisions = _analyze(store)

    assert len(decisions) == 1
    assert decisions[0].context["relation"] == "destination"
    assert [m["canonical_id"] for m in decisions[0].context["remote_members"]] == ["user:carol"]


def test_auto_attendant_default_operator_key_is_not_flagged(store):
    from wxcli.migration.models import CanonicalAutoAttendant

    _user(store, "user:alice", LOC_A, extension="1001")
    store.upsert_object(
        CanonicalAutoAttendant(
            canonical_id="auto_attendant:main",
            provenance=_prov("main"),
            status=MigrationStatus.ANALYZED,
            name="Main AA",
            location_id=LOC_A,
            business_hours_menu={
                "keyConfigurations": [
                    {"key": "0", "action": "TRANSFER_TO_OPERATOR", "value": "0"}
                ]
            },
            after_hours_menu={"keyConfigurations": []},
        )
    )

    assert _analyze(store) == []
