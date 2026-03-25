"""Tests for MonitoringMapper — CUCM BLF → Webex per-person monitoring list."""

from __future__ import annotations
from datetime import datetime, timezone

import pytest

from wxcli.migration.models import (
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.monitoring_mapper import (
    MonitoringMapper,
    _extract_blf_entries,
    _extract_speed_dials,
    WEBEX_MONITORING_MAX,
)


def _provenance(source_id: str = "test-id", name: str = "test") -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id=source_id,
        source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def _make_phone(
    name: str = "SEP001122334455",
    blf_entries: list | None = None,
    speed_dials: list | None = None,
) -> MigrationObject:
    state = {"name": name, "owner_user": "jdoe", "lines": [{"index": "1", "dirn": {"pattern": "1001"}}]}
    if blf_entries is not None:
        state["busyLampFields"] = {"busyLampField": blf_entries}
    if speed_dials is not None:
        state["speeddials"] = {"speeddial": speed_dials}
    return MigrationObject(
        canonical_id=f"phone:{name}",
        provenance=_provenance(source_id=f"uuid-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=state,
    )


def _make_user(userid: str = "jdoe") -> MigrationObject:
    return MigrationObject(
        canonical_id=f"user:{userid}",
        provenance=_provenance(source_id=f"uuid-user-{userid}", name=userid),
        status=MigrationStatus.NORMALIZED,
    )


def _make_line(pattern: str = "1002", owner_user: str | None = None) -> MigrationObject:
    return MigrationObject(
        canonical_id=f"line:{pattern}",
        provenance=_provenance(source_id=f"uuid-line-{pattern}", name=pattern),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"extension": pattern, "pattern": pattern},
    )


def _setup_store(phone, user, lines=None):
    store = MigrationStore(":memory:")
    store.upsert_object(phone)
    store.upsert_object(user)
    store.add_cross_ref(phone.canonical_id, user.canonical_id, "device_owned_by_user")
    if lines:
        for line, owner_id in lines:
            store.upsert_object(line)
            if owner_id:
                store.add_cross_ref(line.canonical_id, owner_id, "line_assigned_to_user")
    return store


class TestExtractBlfEntries:
    def test_nested_dict_format(self):
        state = {"busyLampFields": {"busyLampField": [{"blfDest": "1002"}]}}
        assert len(_extract_blf_entries(state)) == 1

    def test_list_format(self):
        state = {"busyLampFields": [{"blfDest": "1002"}]}
        assert len(_extract_blf_entries(state)) == 1

    def test_none(self):
        assert _extract_blf_entries({}) == []

    def test_single_entry_dict(self):
        state = {"busyLampFields": {"busyLampField": {"blfDest": "1002"}}}
        assert len(_extract_blf_entries(state)) == 1


class TestExtractSpeedDials:
    def test_nested_dict_format(self):
        state = {"speeddials": {"speeddial": [{"dirn": "5551234"}]}}
        assert len(_extract_speed_dials(state)) == 1

    def test_none(self):
        assert _extract_speed_dials({}) == []


class TestMonitoringMapperResolved:
    def test_resolved_blf_creates_monitoring_list(self):
        phone = _make_phone(blf_entries=[{"blfDest": "1002", "label": "Jane"}])
        user = _make_user()
        target_line = _make_line("1002")
        target_user = _make_user("jane")

        # Must upsert target_user before adding cross-ref that references it
        store = MigrationStore(":memory:")
        store.upsert_object(phone)
        store.upsert_object(user)
        store.upsert_object(target_user)
        store.upsert_object(target_line)
        store.add_cross_ref(phone.canonical_id, user.canonical_id, "device_owned_by_user")
        store.add_cross_ref(target_line.canonical_id, target_user.canonical_id, "line_assigned_to_user")

        mapper = MonitoringMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        assert len(result.decisions) == 0

        ml = store.get_object("monitoring_list:jdoe")
        assert ml is not None


class TestMonitoringMapperUnresolvable:
    def test_unresolvable_blf_still_creates_list(self):
        phone = _make_phone(blf_entries=[{"blfDest": "9999", "label": "Unknown"}])
        user = _make_user()
        store = _setup_store(phone, user)

        mapper = MonitoringMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        ml = store.get_object("monitoring_list:jdoe")
        assert ml is not None


class TestMonitoringMapperOverflow:
    def test_over_50_entries_truncation(self):
        entries = [{"blfDest": f"100{i:02d}", "label": f"User{i}"} for i in range(55)]
        phone = _make_phone(blf_entries=entries)
        user = _make_user()
        store = _setup_store(phone, user)

        mapper = MonitoringMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        assert len(result.decisions) == 1
        assert result.decisions[0].type.value == "FEATURE_APPROXIMATION"


class TestMonitoringMapperNoBlf:
    def test_phone_without_blf_skipped(self):
        phone = _make_phone(blf_entries=None)
        user = _make_user()
        store = _setup_store(phone, user)

        mapper = MonitoringMapper()
        result = mapper.map(store)

        assert result.objects_created == 0

    def test_speed_dials_only_not_mapped(self):
        """Speed dials stay as metadata — no monitoring list created."""
        phone = _make_phone(
            blf_entries=None,
            speed_dials=[{"dirn": "5551234", "label": "Bob"}],
        )
        user = _make_user()
        store = _setup_store(phone, user)

        mapper = MonitoringMapper()
        result = mapper.map(store)

        assert result.objects_created == 0


class TestMonitoringMapperNoOwner:
    def test_phone_without_owner_skipped(self):
        phone = _make_phone(blf_entries=[{"blfDest": "1002", "label": "Jane"}])
        store = MigrationStore(":memory:")
        store.upsert_object(phone)

        mapper = MonitoringMapper()
        result = mapper.map(store)

        assert result.objects_created == 0
