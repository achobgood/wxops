"""Tests for ExecutiveAssistantMapper — CUCM exec/assistant pairings to Webex config."""

from __future__ import annotations

from datetime import datetime, timezone

from wxcli.migration.models import (
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.executive_assistant_mapper import ExecutiveAssistantMapper


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _prov(name: str = "test") -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id=f"uuid-{name}",
        source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def _user(userid: str) -> MigrationObject:
    return MigrationObject(
        canonical_id=f"user:{userid}",
        provenance=_prov(userid),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"userid": userid},
    )


def _exec_asst_pair(exec_userid: str, asst_userid: str) -> MigrationObject:
    return MigrationObject(
        canonical_id=f"exec_asst_pair:{exec_userid}:{asst_userid}",
        provenance=_prov(f"pair-{exec_userid}-{asst_userid}"),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "executive_userid": exec_userid,
            "assistant_userid": asst_userid,
        },
    )


def _exec_setting(
    userid: str,
    alerting_mode: str = "SIMULTANEOUS",
    filter_enabled: bool = False,
    filter_type: str = "ALL_CALLS",
    screening_enabled: bool = False,
) -> MigrationObject:
    return MigrationObject(
        canonical_id=f"exec_setting:{userid}",
        provenance=_prov(f"setting-{userid}"),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "userid": userid,
            "alerting_mode": alerting_mode,
            "filter_enabled": filter_enabled,
            "filter_type": filter_type,
            "screening_enabled": screening_enabled,
        },
    )


def _setup(objects: list[MigrationObject]) -> MigrationStore:
    store = MigrationStore(":memory:")
    for obj in objects:
        store.upsert_object(obj)
    return store


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMapBasicPair:
    def test_map_basic_pair(self):
        """1 exec + 1 asst, both in store -> 1 CanonicalExecutiveAssistant, 0 decisions."""
        store = _setup([
            _user("exec1"),
            _user("asst1"),
            _exec_asst_pair("exec1", "asst1"),
        ])

        mapper = ExecutiveAssistantMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        assert len(result.decisions) == 0

        ea = store.get_object("executive_assistant:exec1")
        assert ea is not None
        assert ea["executive_canonical_id"] == "user:exec1"
        assert ea["assistant_canonical_ids"] == ["user:asst1"]


class TestMapMultiAssistant:
    def test_map_multi_assistant(self):
        """1 exec + 3 assts -> 1 object with 3 assistant_canonical_ids."""
        store = _setup([
            _user("exec1"),
            _user("asst1"),
            _user("asst2"),
            _user("asst3"),
            _exec_asst_pair("exec1", "asst1"),
            _exec_asst_pair("exec1", "asst2"),
            _exec_asst_pair("exec1", "asst3"),
        ])

        mapper = ExecutiveAssistantMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        assert len(result.decisions) == 0

        ea = store.get_object("executive_assistant:exec1")
        assert ea is not None
        assert sorted(ea["assistant_canonical_ids"]) == [
            "user:asst1",
            "user:asst2",
            "user:asst3",
        ]


class TestBrokenPairMissingAssistant:
    def test_map_broken_pair_missing_assistant(self):
        """exec present, asst NOT in store -> MISSING_DATA decision."""
        store = _setup([
            _user("exec1"),
            _exec_asst_pair("exec1", "ghost_asst"),
        ])

        mapper = ExecutiveAssistantMapper()
        result = mapper.map(store)

        assert result.objects_created == 0
        assert len(result.decisions) == 1

        d = result.decisions[0]
        assert d.type.value == "MISSING_DATA"
        assert d.context["missing_reason"] == "executive_assistant_broken_pair"
        assert d.context["missing_side"] == "assistant"
        assert d.context["assistant_userid"] == "ghost_asst"


class TestBrokenPairMissingExecutive:
    def test_map_broken_pair_missing_executive(self):
        """exec NOT in store, asst present -> MISSING_DATA decision."""
        store = _setup([
            _user("asst1"),
            _exec_asst_pair("ghost_exec", "asst1"),
        ])

        mapper = ExecutiveAssistantMapper()
        result = mapper.map(store)

        assert result.objects_created == 0
        assert len(result.decisions) == 1

        d = result.decisions[0]
        assert d.type.value == "MISSING_DATA"
        assert d.context["missing_reason"] == "executive_assistant_broken_pair"
        assert d.context["missing_side"] == "executive"
        assert d.context["executive_userid"] == "ghost_exec"


class TestSettingsSimultaneous:
    def test_map_settings_simultaneous(self):
        """Default alerting_mode is SIMULTANEOUS when no exec_setting present."""
        store = _setup([
            _user("exec1"),
            _user("asst1"),
            _exec_asst_pair("exec1", "asst1"),
        ])

        mapper = ExecutiveAssistantMapper()
        result = mapper.map(store)

        ea = store.get_object("executive_assistant:exec1")
        assert ea is not None
        assert ea["alerting_mode"] == "SIMULTANEOUS"
        assert ea["filter_enabled"] is False
        assert ea["filter_type"] == "ALL_CALLS"
        assert ea["screening_enabled"] is False

    def test_map_settings_from_exec_setting(self):
        """Settings from exec_setting object are applied."""
        store = _setup([
            _user("exec1"),
            _user("asst1"),
            _exec_asst_pair("exec1", "asst1"),
            _exec_setting(
                "exec1",
                alerting_mode="SEQUENTIAL",
                filter_enabled=True,
                filter_type="ALL_EXTERNAL_CALLS",
                screening_enabled=True,
            ),
        ])

        mapper = ExecutiveAssistantMapper()
        result = mapper.map(store)

        ea = store.get_object("executive_assistant:exec1")
        assert ea is not None
        assert ea["alerting_mode"] == "SEQUENTIAL"
        assert ea["filter_enabled"] is True
        assert ea["filter_type"] == "ALL_EXTERNAL_CALLS"
        assert ea["screening_enabled"] is True


class TestNoPairs:
    def test_map_no_pairs(self):
        """Empty store -> 0 objects, 0 decisions."""
        store = _setup([])

        mapper = ExecutiveAssistantMapper()
        result = mapper.map(store)

        assert result.objects_created == 0
        assert len(result.decisions) == 0
