"""Tests for feature_mapper: CUCM call features -> Webex Calling features.

Uses real :memory: SQLite store, no mocks.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from wxcli.migration.models import (
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.feature_mapper import FeatureMapper


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _provenance(source_id: str = "test-id", name: str = "test") -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id=source_id,
        source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def _hunt_pilot(
    name: str = "HP-Sales",
    pattern: str = "5001",
    queue_calls_enabled: bool = False,
    max_callers: int = 0,
    moh_source_id: str | None = None,
    overflow_dest: str | None = None,
    rna_timeout: int | None = None,
    enabled: bool = True,
    is_cti_rp: bool = False,
) -> MigrationObject:
    state: dict = {
        "name": name,
        "pattern": pattern,
        "extension": pattern,
        "enabled": enabled,
    }
    # All queue fields are nested inside queueCalls (XCallsQueue complex type)
    # (from 02b-cucm-extraction.md §6)
    queue_calls: dict = {}
    if queue_calls_enabled:
        queue_calls["enabled"] = True
    if max_callers > 0:
        queue_calls["maxCallersInQueue"] = max_callers
    if moh_source_id:
        queue_calls["networkHoldMohAudioSourceID"] = moh_source_id
    if overflow_dest:
        queue_calls["queueFullDestination"] = overflow_dest
    if queue_calls:
        state["queueCalls"] = queue_calls
    if rna_timeout is not None:
        # rnaReversionTimeOut is on LineGroup, not HuntPilot — but allow
        # test fixture to set it here for backward compat if needed
        state["rnaReversionTimeOut"] = rna_timeout
    if is_cti_rp:
        state["isCtiRp"] = True

    return MigrationObject(
        canonical_id=f"hunt_pilot:{name}",
        provenance=_provenance(source_id=f"uuid-hp-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=state,
    )


def _hunt_list(
    name: str = "HL-Sales",
    voice_mail_usage: str = "NONE",
) -> MigrationObject:
    state: dict = {
        "name": name,
        "voiceMailUsage": voice_mail_usage,
    }
    return MigrationObject(
        canonical_id=f"hunt_list:{name}",
        provenance=_provenance(source_id=f"uuid-hl-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=state,
    )


def _line_group(
    name: str = "LG-Sales",
    algorithm: str = "Top Down",
    rna_timeout: int | None = None,
) -> MigrationObject:
    # distributionAlgorithm is on LineGroup, not HuntList
    # (from 02b-cucm-extraction.md §2.5)
    state: dict = {"name": name, "distributionAlgorithm": algorithm}
    if rna_timeout is not None:
        state["rnaReversionTimeOut"] = rna_timeout

    return MigrationObject(
        canonical_id=f"line_group:{name}",
        provenance=_provenance(source_id=f"uuid-lg-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=state,
    )


def _member_dn(pattern: str = "1001") -> MigrationObject:
    return MigrationObject(
        canonical_id=f"dn:{pattern}",
        provenance=_provenance(source_id=f"uuid-dn-{pattern}", name=pattern),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"pattern": pattern},
    )


def _cti_route_point(
    name: str = "CTI-MainMenu",
    pattern: str = "4000",
) -> MigrationObject:
    state: dict = {
        "name": name,
        "pattern": pattern,
        "extension": pattern,
    }
    return MigrationObject(
        canonical_id=f"cti_rp:{name}",
        provenance=_provenance(source_id=f"uuid-cti-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=state,
    )


def _call_park(
    name: str = "CP-Lobby",
    pattern: str = "7001",
    location_id: str | None = None,
) -> MigrationObject:
    state: dict = {
        "name": name,
        "pattern": pattern,
        "extension": pattern,
    }
    if location_id:
        state["location_id"] = location_id
    return MigrationObject(
        canonical_id=f"call_park:{name}",
        provenance=_provenance(source_id=f"uuid-cp-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=state,
    )


def _pickup_group(
    name: str = "PG-Front",
    members: list[str] | None = None,
) -> MigrationObject:
    state: dict = {
        "name": name,
        "members": members or [],
    }
    return MigrationObject(
        canonical_id=f"pickup_group:{name}",
        provenance=_provenance(source_id=f"uuid-pg-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=state,
    )


def _paging_group(
    name: str = "PAG-Warehouse",
    extension: str = "8001",
    targets: list[str] | None = None,
    originators: list[str] | None = None,
) -> MigrationObject:
    state: dict = {
        "name": name,
        "extension": extension,
        "targets": targets or [],
        "originators": originators or [],
    }
    return MigrationObject(
        canonical_id=f"paging_group:{name}",
        provenance=_provenance(source_id=f"uuid-pag-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=state,
    )


def _time_schedule(
    name: str = "BusinessHours",
) -> MigrationObject:
    state: dict = {"name": name}
    return MigrationObject(
        canonical_id=f"time_schedule:{name}",
        provenance=_provenance(source_id=f"uuid-ts-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=state,
    )


def _time_period(
    name: str = "MondayAM",
    start_time: str = "08:00",
    end_time: str = "17:00",
    day_of_week: str | None = None,
    date: str | None = None,
) -> MigrationObject:
    state: dict = {
        "name": name,
        "start_time": start_time,
        "end_time": end_time,
    }
    if day_of_week:
        state["day_of_week"] = day_of_week
    if date:
        state["date"] = date
    return MigrationObject(
        canonical_id=f"time_period:{name}",
        provenance=_provenance(source_id=f"uuid-tp-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=state,
    )


def _make_store() -> MigrationStore:
    return MigrationStore(":memory:")


def _seed_hunt_chain(
    store: MigrationStore,
    hp_name: str = "HP-Sales",
    hp_pattern: str = "5001",
    algorithm: str = "Top Down",
    member_patterns: list[str] | None = None,
    queue_calls_enabled: bool = False,
    max_callers: int = 0,
    moh_source_id: str | None = None,
    overflow_dest: str | None = None,
    voice_mail_usage: str = "NONE",
    rna_timeout: int | None = None,
) -> str:
    """Seed the full hunt_pilot -> hunt_list -> line_group -> members chain.

    Returns the hunt_pilot canonical_id.
    """
    hp = _hunt_pilot(
        name=hp_name,
        pattern=hp_pattern,
        queue_calls_enabled=queue_calls_enabled,
        max_callers=max_callers,
        moh_source_id=moh_source_id,
        overflow_dest=overflow_dest,
    )
    store.upsert_object(hp)

    hl = _hunt_list(name=f"HL-{hp_name}", voice_mail_usage=voice_mail_usage)
    store.upsert_object(hl)
    store.add_cross_ref(hp.canonical_id, hl.canonical_id, "hunt_pilot_has_hunt_list")

    # rna_timeout goes on LineGroup (rnaReversionTimeOut), not HuntPilot
    lg = _line_group(name=f"LG-{hp_name}", algorithm=algorithm, rna_timeout=rna_timeout)
    store.upsert_object(lg)
    store.add_cross_ref(hl.canonical_id, lg.canonical_id, "hunt_list_has_line_group")

    members = member_patterns or ["1001", "1002", "1003"]
    for pattern in members:
        dn = _member_dn(pattern)
        store.upsert_object(dn)
        store.add_cross_ref(lg.canonical_id, dn.canonical_id, "line_group_has_members")

    return hp.canonical_id


# ---------------------------------------------------------------------------
# Tests — Hunt Pilot Classification (Algorithm Mapping Table)
# ---------------------------------------------------------------------------


class TestFeatureMapperHuntPilotClassification:
    """Tests for classify_hunt_pilot: 3-step algorithm from §10."""

    def test_top_down_no_queue_features_produces_hunt_group_regular(self):
        """Top Down + no queue features -> HUNT_GROUP, policy=REGULAR."""
        store = _make_store()
        _seed_hunt_chain(store, "HP-TopDown", "5001", algorithm="Top Down")

        mapper = FeatureMapper()
        result = mapper.map(store)

        hgs = store.get_objects("hunt_group")
        assert len(hgs) == 1
        assert hgs[0]["policy"] == "REGULAR"
        assert hgs[0]["name"] == "HP-TopDown"
        assert len(hgs[0]["agents"]) == 3

    def test_circular_no_queue_features_produces_hunt_group_circular(self):
        """Circular + no queue features -> HUNT_GROUP, policy=CIRCULAR."""
        store = _make_store()
        _seed_hunt_chain(store, "HP-Circular", "5002", algorithm="Circular")

        mapper = FeatureMapper()
        mapper.map(store)

        hgs = store.get_objects("hunt_group")
        assert len(hgs) == 1
        assert hgs[0]["policy"] == "CIRCULAR"

    def test_longest_idle_no_queue_features_produces_hunt_group_uniform(self):
        """Longest Idle Time + no queue features -> HUNT_GROUP, policy=UNIFORM."""
        store = _make_store()
        _seed_hunt_chain(store, "HP-LongestIdle", "5003", algorithm="Longest Idle Time")

        mapper = FeatureMapper()
        mapper.map(store)

        hgs = store.get_objects("hunt_group")
        assert len(hgs) == 1
        assert hgs[0]["policy"] == "UNIFORM"

    def test_broadcast_no_queue_features_produces_hunt_group_simultaneous(self):
        """Broadcast + no queue features -> HUNT_GROUP, policy=SIMULTANEOUS."""
        store = _make_store()
        _seed_hunt_chain(store, "HP-Broadcast", "5004", algorithm="Broadcast")

        mapper = FeatureMapper()
        mapper.map(store)

        hgs = store.get_objects("hunt_group")
        assert len(hgs) == 1
        assert hgs[0]["policy"] == "SIMULTANEOUS"

    def test_circular_with_queue_calls_produces_call_queue(self):
        """Circular + queueCalls.enabled=True -> CALL_QUEUE, policy=CIRCULAR."""
        store = _make_store()
        _seed_hunt_chain(
            store, "HP-CQ-Circular", "5010",
            algorithm="Circular", queue_calls_enabled=True,
        )

        mapper = FeatureMapper()
        mapper.map(store)

        cqs = store.get_objects("call_queue")
        assert len(cqs) == 1
        assert cqs[0]["policy"] == "CIRCULAR"
        assert cqs[0]["routing_type"] == "PRIORITY_BASED"

    def test_top_down_with_max_callers_produces_call_queue(self):
        """Top Down + maxCallersInQueue > 0 -> CALL_QUEUE, policy=REGULAR."""
        store = _make_store()
        _seed_hunt_chain(
            store, "HP-CQ-MaxCallers", "5011",
            algorithm="Top Down", max_callers=10,
        )

        mapper = FeatureMapper()
        mapper.map(store)

        cqs = store.get_objects("call_queue")
        assert len(cqs) == 1
        assert cqs[0]["policy"] == "REGULAR"
        assert cqs[0]["queue_size"] == 10

    def test_with_moh_source_produces_call_queue(self):
        """Any algorithm + mohSourceId set -> CALL_QUEUE."""
        store = _make_store()
        _seed_hunt_chain(
            store, "HP-CQ-MoH", "5012",
            algorithm="Circular", moh_source_id="moh-jazz",
        )

        mapper = FeatureMapper()
        mapper.map(store)

        cqs = store.get_objects("call_queue")
        assert len(cqs) == 1

    def test_with_overflow_destination_produces_call_queue(self):
        """Any algorithm + overflowDestination set -> CALL_QUEUE."""
        store = _make_store()
        _seed_hunt_chain(
            store, "HP-CQ-Overflow", "5013",
            algorithm="Circular", overflow_dest="6000",
        )

        mapper = FeatureMapper()
        mapper.map(store)

        cqs = store.get_objects("call_queue")
        assert len(cqs) == 1

    def test_with_voicemail_usage_produces_call_queue(self):
        """Hunt list voiceMailUsage != NONE -> CALL_QUEUE."""
        store = _make_store()
        _seed_hunt_chain(
            store, "HP-CQ-VM", "5014",
            algorithm="Circular", voice_mail_usage="USE_PROFILE",
        )

        mapper = FeatureMapper()
        mapper.map(store)

        cqs = store.get_objects("call_queue")
        assert len(cqs) == 1


class TestFeatureMapperHuntPilotEdgeCases:
    """Edge cases for hunt pilot classification."""

    def test_broadcast_60_members_produces_agent_limit_decision(self):
        """Broadcast + 60 members -> FEATURE_APPROXIMATION (50-agent limit)."""
        store = _make_store()
        members = [str(1000 + i) for i in range(60)]
        _seed_hunt_chain(
            store, "HP-BigBroadcast", "5020",
            algorithm="Broadcast", member_patterns=members,
        )

        mapper = FeatureMapper()
        result = mapper.map(store)

        limit_decisions = [
            d for d in result.decisions
            if d.type.value == "FEATURE_APPROXIMATION"
            and d.context.get("reason") == "agent_limit_exceeded"
        ]
        assert len(limit_decisions) == 1
        assert limit_decisions[0].context["agent_count"] == 60
        assert limit_decisions[0].context["agent_limit"] == 50

    def test_traverses_full_cross_ref_chain(self):
        """Verifies the mapper traverses hunt_pilot -> hunt_list -> line_group -> members."""
        store = _make_store()
        hp_id = _seed_hunt_chain(
            store, "HP-Chain", "5030",
            algorithm="Top Down", member_patterns=["2001", "2002"],
        )

        mapper = FeatureMapper()
        mapper.map(store)

        hgs = store.get_objects("hunt_group")
        assert len(hgs) == 1
        # Members should be the DN canonical_ids
        assert "dn:2001" in hgs[0]["agents"]
        assert "dn:2002" in hgs[0]["agents"]

    def test_missing_extension_produces_missing_data_decision(self):
        """Hunt pilot with no pattern -> MISSING_DATA decision."""
        store = _make_store()

        hp = MigrationObject(
            canonical_id="hunt_pilot:HP-NoExt",
            provenance=_provenance(name="HP-NoExt"),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={"name": "HP-NoExt"},
        )
        store.upsert_object(hp)

        hl = _hunt_list(name="HL-NoExt")
        store.upsert_object(hl)
        store.add_cross_ref(hp.canonical_id, hl.canonical_id, "hunt_pilot_has_hunt_list")

        lg = _line_group(name="LG-NoExt", algorithm="Top Down")
        store.upsert_object(lg)
        store.add_cross_ref(hl.canonical_id, lg.canonical_id, "hunt_list_has_line_group")

        mapper = FeatureMapper()
        result = mapper.map(store)

        missing = [
            d for d in result.decisions
            if d.type.value == "MISSING_DATA"
            and d.context.get("reason") == "no_extension"
        ]
        assert len(missing) == 1

    def test_default_queue_size_25(self):
        """Call queue with no maxCallersInQueue uses default 25."""
        store = _make_store()
        _seed_hunt_chain(
            store, "HP-CQ-Default", "5040",
            algorithm="Circular", queue_calls_enabled=True,
        )

        mapper = FeatureMapper()
        mapper.map(store)

        cqs = store.get_objects("call_queue")
        assert cqs[0]["queue_size"] == 25

    def test_rna_timeout_from_line_group(self):
        """rnaReversionTimeOut on LineGroup should set no_answer_rings on HG.

        (from 02b-cucm-extraction.md §2.5: rnaReversionTimeOut is on LineGroup)
        18 seconds ÷ 6 = 3 rings.
        """
        store = _make_store()
        _seed_hunt_chain(
            store, "HP-RNA", "5050",
            algorithm="Top Down",
            rna_timeout=18,
        )

        mapper = FeatureMapper()
        mapper.map(store)

        hgs = store.get_objects("hunt_group")
        assert len(hgs) == 1
        assert hgs[0]["no_answer_rings"] == 3, (
            "18s rnaReversionTimeOut on LineGroup should produce 3 rings (18÷6)"
        )


# ---------------------------------------------------------------------------
# Tests — CTI Route Point -> Auto Attendant
# ---------------------------------------------------------------------------


class TestFeatureMapperCTIRoutePoint:
    """CTI Route Point -> CanonicalAutoAttendant."""

    def test_cti_rp_produces_auto_attendant_and_decision(self):
        """CTI RP -> AA with FEATURE_APPROXIMATION decision."""
        store = _make_store()
        cti = _cti_route_point("CTI-MainMenu", "4000")
        store.upsert_object(cti)

        mapper = FeatureMapper()
        result = mapper.map(store)

        aas = store.get_objects("auto_attendant")
        assert len(aas) == 1
        assert aas[0]["name"] == "CTI-MainMenu"
        assert aas[0]["extension"] == "4000"

        # Both menus must be present
        assert aas[0]["business_hours_menu"] is not None
        assert aas[0]["after_hours_menu"] is not None
        assert aas[0]["business_hours_menu"]["greeting"] == "DEFAULT"
        assert aas[0]["business_hours_menu"]["extensionEnabled"] is True
        assert len(aas[0]["business_hours_menu"]["keyConfigurations"]) >= 1

        # FEATURE_APPROXIMATION decision
        fa_decisions = [
            d for d in result.decisions
            if d.type.value == "FEATURE_APPROXIMATION"
            and d.context.get("reason") == "cti_rp_to_auto_attendant"
        ]
        assert len(fa_decisions) == 1

    def test_cti_rp_with_script_reference(self):
        """CTI RP with cti_rp_has_script cross-ref notes script in decision."""
        store = _make_store()
        cti = _cti_route_point("CTI-IVR", "4001")
        store.upsert_object(cti)

        script = MigrationObject(
            canonical_id="script:MainMenu",
            provenance=_provenance(name="MainMenu"),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={"name": "MainMenu"},
        )
        store.upsert_object(script)
        store.add_cross_ref(cti.canonical_id, script.canonical_id, "cti_rp_has_script")

        mapper = FeatureMapper()
        result = mapper.map(store)

        fa_decisions = [
            d for d in result.decisions
            if d.type.value == "FEATURE_APPROXIMATION"
        ]
        assert len(fa_decisions) == 1
        assert fa_decisions[0].context["has_script"] is True

    def test_cti_rp_decision_context_sets_classification(self):
        """Regression guard: FeatureMapper must set classification and complex_script
        in the FEATURE_APPROXIMATION decision context for CTI Route Points.

        Without these keys, recommend_feature_approximation()'s AUTO_ATTENDANT
        branch never fires and every CTI RP gets a wrong recommendation.
        """
        store = _make_store()
        cti = _cti_route_point("CTI-Reception", "4002")
        store.upsert_object(cti)

        mapper = FeatureMapper()
        result = mapper.map(store)

        fa_decisions = [
            d for d in result.decisions
            if d.type.value == "FEATURE_APPROXIMATION"
            and d.context.get("reason") == "cti_rp_to_auto_attendant"
        ]
        assert len(fa_decisions) == 1, (
            f"Expected 1 FEATURE_APPROXIMATION decision, got {len(fa_decisions)}"
        )
        ctx = fa_decisions[0].context
        assert ctx.get("classification") == "AUTO_ATTENDANT", (
            f"Expected classification='AUTO_ATTENDANT', got {ctx.get('classification')!r}"
        )
        assert ctx.get("complex_script") is False, (
            f"Expected complex_script=False for simple CTI RP, got {ctx.get('complex_script')!r}"
        )


# ---------------------------------------------------------------------------
# Tests — Simple Features
# ---------------------------------------------------------------------------


class TestFeatureMapperCallPark:
    """Call Park Number -> CanonicalCallPark."""

    def test_call_park_created_with_extension(self):
        store = _make_store()
        cp = _call_park("CP-Lobby", "7001", location_id="location:HQ")
        store.upsert_object(cp)

        mapper = FeatureMapper()
        result = mapper.map(store)

        cps = store.get_objects("call_park")
        mapped_cps = [c for c in cps if c["status"] == "analyzed"]
        assert len(mapped_cps) == 1
        assert mapped_cps[0]["extension"] == "7001"
        assert mapped_cps[0]["location_id"] == "location:HQ"


class TestFeatureMapperPickupGroup:
    """Pickup Group -> CanonicalPickupGroup."""

    def test_pickup_group_created_with_members(self):
        store = _make_store()
        pg = _pickup_group("PG-Front", members=["user:alice", "user:bob"])
        store.upsert_object(pg)

        mapper = FeatureMapper()
        result = mapper.map(store)

        pgs = store.get_objects("pickup_group")
        mapped_pgs = [p for p in pgs if p["status"] == "analyzed"]
        assert len(mapped_pgs) == 1
        assert mapped_pgs[0]["name"] == "PG-Front"
        assert "user:alice" in mapped_pgs[0]["agents"]
        assert "user:bob" in mapped_pgs[0]["agents"]

    def test_pickup_group_extracts_uuids_from_member_dicts(self):
        """Members coming as CUCM AXL dicts should have UUIDs extracted."""
        store = _make_store()
        # Simulate raw CUCM member dicts that weren't cleaned by normalizer
        raw_members = [
            {"priority": 1, "pickupGroupLineMember": {"_value_1": "SEP001", "uuid": "{A1B2C3D4-E5F6-7890-1234-567890ABCDEF}"}},
            {"priority": 2, "pickupGroupLineMember": {"_value_1": "SEP002", "uuid": "{F1E2D3C4-B5A6-0987-6543-210FEDCBA987}"}},
        ]
        pg = _pickup_group("PG-Dict-Members", members=raw_members)
        store.upsert_object(pg)

        mapper = FeatureMapper()
        result = mapper.map(store)

        pgs = store.get_objects("pickup_group")
        mapped_pgs = [p for p in pgs if p["status"] == "analyzed"]
        assert len(mapped_pgs) == 1
        assert mapped_pgs[0]["name"] == "PG-Dict-Members"
        # Should extract UUID strings, not pass raw dicts
        agents = mapped_pgs[0]["agents"]
        assert len(agents) == 2
        assert all(isinstance(a, str) for a in agents)
        assert "{A1B2C3D4-E5F6-7890-1234-567890ABCDEF}" in agents
        assert "{F1E2D3C4-B5A6-0987-6543-210FEDCBA987}" in agents


class TestFeatureMapperSchedule:
    """Time Schedule + Time Period -> CanonicalOperatingMode."""

    def test_schedule_produces_operating_mode_with_org_level(self):
        """Time schedule -> OperatingMode with level=ORGANIZATION."""
        store = _make_store()
        sched = _time_schedule("BusinessHours")
        store.upsert_object(sched)

        tp1 = _time_period("Weekday", "08:00", "17:00")
        store.upsert_object(tp1)
        store.add_cross_ref(sched.canonical_id, tp1.canonical_id, "schedule_has_time_period")

        mapper = FeatureMapper()
        result = mapper.map(store)

        oms = store.get_objects("operating_mode")
        assert len(oms) == 1
        assert oms[0]["level"] == "ORGANIZATION"
        assert oms[0]["name"] == "BusinessHours"

    def test_multiple_periods_different_hours(self):
        """Multiple time periods with different times -> DIFFERENT_HOURS_DAILY."""
        store = _make_store()
        sched = _time_schedule("SplitHours")
        store.upsert_object(sched)

        tp1 = _time_period("MondayAM", "08:00", "12:00", day_of_week="Monday")
        tp2 = _time_period("TuesdayPM", "13:00", "17:00", day_of_week="Tuesday")
        store.upsert_object(tp1)
        store.upsert_object(tp2)
        store.add_cross_ref(sched.canonical_id, tp1.canonical_id, "schedule_has_time_period")
        store.add_cross_ref(sched.canonical_id, tp2.canonical_id, "schedule_has_time_period")

        mapper = FeatureMapper()
        mapper.map(store)

        oms = store.get_objects("operating_mode")
        assert len(oms) == 1
        assert oms[0]["schedule_type"] == "DIFFERENT_HOURS_DAILY"

    def test_holiday_schedule(self):
        """Time period with date -> HOLIDAY schedule type."""
        store = _make_store()
        sched = _time_schedule("Holidays2026")
        store.upsert_object(sched)

        tp = _time_period("NewYear", "00:00", "23:59", date="2026-01-01")
        store.upsert_object(tp)
        store.add_cross_ref(sched.canonical_id, tp.canonical_id, "schedule_has_time_period")

        mapper = FeatureMapper()
        mapper.map(store)

        oms = store.get_objects("operating_mode")
        assert len(oms) == 1
        assert oms[0]["schedule_type"] == "HOLIDAY"
        assert len(oms[0]["holidays"]) == 1


class TestFeatureMapperPagingGroup:
    """Paging Group -> CanonicalPagingGroup."""

    def test_paging_group_created(self):
        store = _make_store()
        pag = _paging_group("PAG-Warehouse", "8001", targets=["user:1", "user:2"])
        store.upsert_object(pag)

        mapper = FeatureMapper()
        result = mapper.map(store)

        pags = store.get_objects("paging_group")
        mapped = [p for p in pags if p["status"] == "analyzed"]
        assert len(mapped) == 1
        assert mapped[0]["name"] == "PAG-Warehouse"
        assert mapped[0]["extension"] == "8001"
        assert len(mapped[0]["targets"]) == 2

    def test_paging_group_split_over_75_targets(self):
        """Paging group with 80 targets -> split into 2 groups (75 + 5)."""
        store = _make_store()
        targets = [f"user:{i}" for i in range(80)]
        pag = _paging_group("PAG-Large", "8002", targets=targets)
        store.upsert_object(pag)

        mapper = FeatureMapper()
        result = mapper.map(store)

        pags = store.get_objects("paging_group")
        mapped = [p for p in pags if p["status"] == "analyzed"]
        assert len(mapped) == 2

        # First group should have 75 targets
        first = [p for p in mapped if p["name"] == "PAG-Large-1"]
        assert len(first) == 1
        assert len(first[0]["targets"]) == 75

        # Second group should have 5 targets
        second = [p for p in mapped if p["name"] == "PAG-Large-2"]
        assert len(second) == 1
        assert len(second[0]["targets"]) == 5


# ---------------------------------------------------------------------------
# Tests — Location Schedule (Fix: schedule-mapping-and-skill-gaps)
# ---------------------------------------------------------------------------


def _seed_aa_with_schedule(
    store: MigrationStore,
    aa_name: str = "AA-Main",
    schedule_name: str = "BusinessHours",
    location_id: str = "location:HQ",
) -> str:
    """Seed a pre-analyzed AA and a time schedule for location schedule creation.

    The AA is seeded directly (not via CTI RP chain) with business_schedule
    and location_id set. The time schedule gets mapped to an operating_mode
    by _map_schedules(), then _map_location_schedules() creates the location schedule.

    Returns the schedule canonical_id.
    """
    from wxcli.migration.models import CanonicalAutoAttendant

    # Create the time schedule + period (gets turned into operating_mode by mapper)
    sched = _time_schedule(schedule_name)
    store.upsert_object(sched)
    tp = _time_period("Weekday", "08:00", "17:00")
    store.upsert_object(tp)
    store.add_cross_ref(sched.canonical_id, tp.canonical_id, "schedule_has_time_period")

    # Pre-seed an analyzed AA with business_schedule and location_id
    aa = CanonicalAutoAttendant(
        canonical_id=f"auto_attendant:{aa_name}",
        provenance=_provenance(source_id=f"uuid-aa-{aa_name}", name=aa_name),
        status=MigrationStatus.ANALYZED,
        name=aa_name,
        extension="4000",
        business_schedule=schedule_name,
        location_id=location_id,
        business_hours_menu={"greeting": "DEFAULT"},
        after_hours_menu={"greeting": "DEFAULT"},
    )
    store.upsert_object(aa)

    return sched.canonical_id


class TestFeatureMapperLocationSchedule:
    """Location Schedule: schedules referenced by AAs create CanonicalLocationSchedule."""

    def test_aa_with_schedule_creates_location_schedule(self):
        """AA referencing a business_schedule -> CanonicalLocationSchedule created."""
        store = _make_store()
        _seed_aa_with_schedule(store)

        mapper = FeatureMapper()
        mapper.map(store)

        schedules = store.get_objects("schedule")
        assert len(schedules) == 1
        assert schedules[0]["name"] == "BusinessHours"
        assert schedules[0]["schedule_type"] == "businessHours"
        assert schedules[0]["status"] == "analyzed"

    def test_aa_without_schedule_no_location_schedule(self):
        """AA without business_schedule -> no location schedule."""
        store = _make_store()
        cti = _cti_route_point("AA-NoSched", "4001")
        store.upsert_object(cti)

        mapper = FeatureMapper()
        mapper.map(store)

        schedules = store.get_objects("schedule")
        assert len(schedules) == 0

    def test_multiple_aas_same_schedule_one_location_schedule(self):
        """Two AAs referencing same schedule -> one location schedule."""
        from wxcli.migration.models import CanonicalAutoAttendant

        store = _make_store()
        sched = _time_schedule("SharedHours")
        store.upsert_object(sched)
        tp = _time_period("Weekday", "09:00", "18:00")
        store.upsert_object(tp)
        store.add_cross_ref(sched.canonical_id, tp.canonical_id, "schedule_has_time_period")

        # Pre-seed two analyzed AAs referencing the same schedule
        for name in ["AA-One", "AA-Two"]:
            aa = CanonicalAutoAttendant(
                canonical_id=f"auto_attendant:{name}",
                provenance=_provenance(source_id=f"uuid-aa-{name}", name=name),
                status=MigrationStatus.ANALYZED,
                name=name,
                business_schedule="SharedHours",
                location_id="location:HQ",
                business_hours_menu={"greeting": "DEFAULT"},
                after_hours_menu={"greeting": "DEFAULT"},
            )
            store.upsert_object(aa)

        mapper = FeatureMapper()
        mapper.map(store)

        schedules = store.get_objects("schedule")
        assert len(schedules) == 1

        # Both AAs should have cross-refs to the schedule
        for name in ["AA-One", "AA-Two"]:
            aas = [a for a in store.get_objects("auto_attendant") if a["name"] == name]
            assert len(aas) == 1
            refs = store.find_cross_refs(aas[0]["canonical_id"], "aa_has_schedule")
            assert len(refs) >= 1

    def test_operating_mode_without_aa_no_location_schedule(self):
        """Operating mode not referenced by any AA -> no location schedule."""
        store = _make_store()
        sched = _time_schedule("UnusedSchedule")
        store.upsert_object(sched)
        tp = _time_period("Weekday", "08:00", "17:00")
        store.upsert_object(tp)
        store.add_cross_ref(sched.canonical_id, tp.canonical_id, "schedule_has_time_period")

        mapper = FeatureMapper()
        mapper.map(store)

        # Operating mode is created, but no location schedule
        oms = store.get_objects("operating_mode")
        assert len(oms) == 1
        schedules = store.get_objects("schedule")
        assert len(schedules) == 0

    def test_holiday_schedule_type_mapping(self):
        """HOLIDAY operating mode -> holidays schedule_type."""
        from wxcli.migration.models import CanonicalAutoAttendant

        store = _make_store()
        sched = _time_schedule("Holidays2026")
        store.upsert_object(sched)
        tp = _time_period("NewYear", "00:00", "23:59", date="2026-01-01")
        store.upsert_object(tp)
        store.add_cross_ref(sched.canonical_id, tp.canonical_id, "schedule_has_time_period")

        # Pre-seed an analyzed AA referencing the holiday schedule
        aa = CanonicalAutoAttendant(
            canonical_id="auto_attendant:AA-Holiday",
            provenance=_provenance(source_id="uuid-aa-holiday", name="AA-Holiday"),
            status=MigrationStatus.ANALYZED,
            name="AA-Holiday",
            business_schedule="Holidays2026",
            location_id="location:HQ",
            business_hours_menu={"greeting": "DEFAULT"},
            after_hours_menu={"greeting": "DEFAULT"},
        )
        store.upsert_object(aa)

        mapper = FeatureMapper()
        mapper.map(store)

        schedules = store.get_objects("schedule")
        assert len(schedules) == 1
        assert schedules[0]["schedule_type"] == "holidays"

    def test_schedule_events_use_recur_weekly(self):
        """Location schedule events use recurWeekly, not recurForEver."""
        store = _make_store()
        _seed_aa_with_schedule(store)

        mapper = FeatureMapper()
        mapper.map(store)

        schedules = store.get_objects("schedule")
        assert len(schedules) == 1
        events = schedules[0]["events"]
        assert len(events) >= 1
        # Verify recurWeekly is used
        for event in events:
            rec = event.get("recurrence", {})
            if rec:
                assert "recurWeekly" in rec
                assert "recurForEver" not in rec

    def test_aa_has_schedule_cross_ref_written(self):
        """AA -> schedule cross-ref is written for matching AAs."""
        store = _make_store()
        _seed_aa_with_schedule(store)

        mapper = FeatureMapper()
        mapper.map(store)

        aas = store.get_objects("auto_attendant")
        assert len(aas) >= 1
        aa_cid = aas[0]["canonical_id"]
        refs = store.find_cross_refs(aa_cid, "aa_has_schedule")
        assert len(refs) >= 1
