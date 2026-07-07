"""Tests for MigrationStore (SQLite-backed migration persistence).

Acceptance criteria:
- Create a migration.db, insert 100 objects across 5 types
- Query by type and status, add cross_refs, query cross_refs by relationship
- Verify WAL mode and foreign keys are active
- Upsert same canonical_id twice -> updates not duplicates
"""

import json
import pytest
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from wxcli.migration.models import (
    CanonicalDevice,
    CanonicalLine,
    CanonicalLocation,
    CanonicalUser,
    CanonicalWorkspace,
    DeviceCompatibilityTier,
    LocationAddress,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test_migration.db"


@pytest.fixture
def store(db_path):
    s = MigrationStore(db_path)
    yield s
    s.close()


def _prov():
    return Provenance(
        source_system="cucm",
        source_id="pk-test",
        source_name="test",
        extracted_at=datetime.now(timezone.utc),
    )


def _make_location(i: int) -> CanonicalLocation:
    return CanonicalLocation(
        canonical_id=f"location:{i:04d}",
        provenance=_prov(),
        name=f"Location-{i}",
    )


def _make_user(i: int) -> CanonicalUser:
    return CanonicalUser(
        canonical_id=f"user:{i:04d}",
        provenance=_prov(),
        first_name=f"User{i}",
        emails=[f"user{i}@example.com"],
    )


def _make_device(i: int) -> CanonicalDevice:
    return CanonicalDevice(
        canonical_id=f"device:{i:04d}",
        provenance=_prov(),
        mac=f"{i:012X}",
        compatibility_tier=DeviceCompatibilityTier.NATIVE_MPP,
    )


def _make_line(i: int) -> CanonicalLine:
    return CanonicalLine(
        canonical_id=f"line:{i:04d}",
        provenance=_prov(),
        extension=str(1000 + i),
    )


def _make_workspace(i: int) -> CanonicalWorkspace:
    return CanonicalWorkspace(
        canonical_id=f"workspace:{i:04d}",
        provenance=_prov(),
        display_name=f"Workspace-{i}",
    )


class TestWALAndForeignKeys:
    def test_wal_mode(self, store):
        row = store.conn.execute("PRAGMA journal_mode").fetchone()
        assert row[0] == "wal"

    def test_foreign_keys_on(self, store):
        row = store.conn.execute("PRAGMA foreign_keys").fetchone()
        assert row[0] == 1


class TestUpsertObject:
    def test_insert_and_query(self, store):
        loc = _make_location(1)
        store.upsert_object(loc)
        results = store.query_by_type("location")
        assert len(results) == 1
        assert results[0].canonical_id == "location:0001"
        assert results[0].name == "Location-1"

    def test_upsert_updates_not_duplicates(self, store):
        loc = _make_location(1)
        store.upsert_object(loc)
        # Update name
        loc.name = "Location-1-Updated"
        loc.status = MigrationStatus.ANALYZED
        store.upsert_object(loc)
        results = store.query_by_type("location")
        assert len(results) == 1
        assert results[0].name == "Location-1-Updated"
        assert results[0].status == MigrationStatus.ANALYZED


class TestBulkInsertAndQuery:
    def test_100_objects_across_5_types(self, store):
        """Insert 100 objects across 5 types, query by type and status."""
        for i in range(20):
            store.upsert_object(_make_location(i))
            store.upsert_object(_make_user(i))
            store.upsert_object(_make_device(i))
            store.upsert_object(_make_line(i))
            store.upsert_object(_make_workspace(i))

        assert store.count_by_type("location") == 20
        assert store.count_by_type("user") == 20
        assert store.count_by_type("device") == 20
        assert store.count_by_type("line") == 20
        assert store.count_by_type("workspace") == 20

        # All are DISCOVERED by default
        discovered = store.query_by_status("discovered")
        assert len(discovered) == 100

        # Update some to analyzed
        for i in range(5):
            u = _make_user(i)
            u.status = MigrationStatus.ANALYZED
            store.upsert_object(u)

        analyzed = store.query_by_type("user", status="analyzed")
        assert len(analyzed) == 5

    def test_get_object_single(self, store):
        loc = _make_location(42)
        store.upsert_object(loc)
        data = store.get_object("location:0042")
        assert data is not None
        assert data["name"] == "Location-42"

    def test_get_object_typed(self, store):
        loc = _make_location(42)
        store.upsert_object(loc)
        obj = store.get_object_typed("location:0042")
        assert isinstance(obj, CanonicalLocation)
        assert obj.name == "Location-42"

    def test_get_object_missing(self, store):
        assert store.get_object("nonexistent:001") is None


class TestCrossRefs:
    def test_add_and_find(self, store):
        store.upsert_object(_make_user(1))
        store.upsert_object(_make_device(1))
        store.add_cross_ref("user:0001", "device:0001", "user_has_device")
        targets = store.find_cross_refs("user:0001", "user_has_device")
        assert targets == ["device:0001"]

    def test_multiple_refs(self, store):
        store.upsert_object(_make_user(1))
        store.upsert_object(_make_device(1))
        store.upsert_object(_make_device(2))
        store.add_cross_ref("user:0001", "device:0001", "user_has_device")
        store.add_cross_ref("user:0001", "device:0002", "user_has_device")
        targets = store.find_cross_refs("user:0001", "user_has_device")
        assert set(targets) == {"device:0001", "device:0002"}

    def test_ordinal(self, store):
        store.upsert_object(_make_location(1))
        store.upsert_object(_make_location(2))
        store.upsert_object(_make_location(3))
        # css_contains_partition with ordinal (priority)
        store.add_cross_ref("location:0001", "location:0002", "css_contains_partition", ordinal=1)
        store.add_cross_ref("location:0001", "location:0003", "css_contains_partition", ordinal=2)
        refs = store.get_cross_refs(from_id="location:0001", relationship="css_contains_partition")
        assert len(refs) == 2
        ordinals = sorted(r["ordinal"] for r in refs)
        assert ordinals == [1, 2]

    def test_get_cross_ref_targets(self, store):
        store.upsert_object(_make_device(1))
        store.upsert_object(_make_line(1))
        store.add_cross_ref("device:0001", "line:0001", "device_has_dn")
        targets = store.get_cross_ref_targets("device:0001", "device_has_dn")
        assert targets == ["line:0001"]

    def test_resolve_chain(self, store):
        store.upsert_object(_make_device(1))
        store.upsert_object(_make_location(1))
        store.upsert_object(_make_location(2))
        store.add_cross_ref("device:0001", "location:0001", "device_in_pool")
        store.add_cross_ref("location:0001", "location:0002", "device_pool_to_location")
        result = store.resolve_chain("device:0001", "device_in_pool", "device_pool_to_location")
        assert result == "location:0002"

    def test_resolve_chain_broken(self, store):
        store.upsert_object(_make_device(1))
        result = store.resolve_chain("device:0001", "device_in_pool", "device_pool_to_location")
        assert result is None

    def test_clear_cross_refs(self, store):
        store.upsert_object(_make_user(1))
        store.upsert_object(_make_device(1))
        store.add_cross_ref("user:0001", "device:0001", "user_has_device")
        assert len(store.find_cross_refs("user:0001", "user_has_device")) == 1
        store.clear_cross_refs()
        assert len(store.find_cross_refs("user:0001", "user_has_device")) == 0


class TestDecisions:
    def _sample_decision(self, decision_id="D0001"):
        return {
            "decision_id": decision_id,
            "type": "DEVICE_INCOMPATIBLE",
            "severity": "HIGH",
            "summary": "Phone model 7945 is incompatible",
            "context": {"model": "7945", "device_id": "device:0001"},
            "options": [
                {"id": "skip", "label": "Skip", "impact": "User migrated without device"},
                {"id": "replace", "label": "Replace", "impact": "Suggest MPP replacement"},
            ],
            "fingerprint": "abc123def456",
            "run_id": "run-001",
        }

    def test_save_and_get(self, store):
        store.save_decision(self._sample_decision())
        d = store.get_decision("D0001")
        assert d is not None
        assert d["type"] == "DEVICE_INCOMPATIBLE"
        assert d["severity"] == "HIGH"
        assert d["context"]["model"] == "7945"
        assert len(d["options"]) == 2

    def test_get_all_decisions(self, store):
        store.save_decision(self._sample_decision("D0001"))
        d2 = self._sample_decision("D0002")
        d2["fingerprint"] = "xyz789"
        store.save_decision(d2)
        all_d = store.get_all_decisions()
        assert len(all_d) == 2

    def test_upsert_by_fingerprint(self, store):
        store.save_decision(self._sample_decision())
        # Same fingerprint, different ID — should update
        updated = self._sample_decision("D9999")
        updated["summary"] = "Updated summary"
        store.save_decision(updated)
        all_d = store.get_all_decisions()
        assert len(all_d) == 1  # no duplicate

    def test_resolve_decision(self, store):
        store.save_decision(self._sample_decision())
        store.resolve_decision("D0001", "skip", "user")
        d = store.get_decision("D0001")
        assert d["chosen_option"] == "skip"
        assert d["resolved_by"] == "user"
        assert d["resolved_at"] is not None


class TestJournal:
    def test_add_entry(self, store):
        store.upsert_object(_make_user(1))
        store.add_journal_entry(
            entry_type="CREATE",
            canonical_id="user:0001",
            resource_type="user",
            request={"method": "POST", "url": "/v1/people", "payload": {}},
            response={"status": 200, "body": {"id": "webex-123"}},
        )
        rows = store.conn.execute("SELECT * FROM journal").fetchall()
        assert len(rows) == 1
        assert json.loads(rows[0]["request"])["method"] == "POST"


class TestMergeLog:
    def test_add_entry(self, store):
        store.add_merge_log(
            stage="analyze",
            action="kept",
            target_type="decision",
            target_id="D0001",
            details={"reason": "fingerprint unchanged"},
        )
        rows = store.conn.execute("SELECT * FROM merge_log").fetchall()
        assert len(rows) == 1
        assert rows[0]["action"] == "kept"


class TestRunIdAndDecisionId:
    def test_run_id_stable(self, store):
        rid = store.current_run_id
        assert rid == store.current_run_id  # same within session

    def test_set_run_id(self, store):
        store.set_run_id("custom-run-001")
        assert store.current_run_id == "custom-run-001"

    def test_decision_id_increments(self, store):
        d1 = store.next_decision_id()
        d2 = store.next_decision_id()
        assert d1 == "D0001"
        assert d2 == "D0002"

    def test_decision_counter_persists_across_sessions(self, db_path):
        """Re-opening the DB continues numbering from the highest existing ID."""
        store1 = MigrationStore(db_path)
        store1.save_decision({
            "decision_id": "D0005",
            "type": "TEST",
            "severity": "LOW",
            "summary": "test",
            "context": {},
            "options": [],
            "fingerprint": "fp-persist-test",
            "run_id": "run-1",
        })
        store1.close()

        store2 = MigrationStore(db_path)
        next_id = store2.next_decision_id()
        assert next_id == "D0006"
        store2.close()


class TestContextManager:
    def test_with_statement(self, db_path):
        with MigrationStore(db_path) as store:
            store.upsert_object(_make_location(1))
            assert store.count_by_type("location") == 1
        # Connection should be closed after exiting
        import sqlite3
        try:
            store.conn.execute("SELECT 1")
            closed = False
        except Exception:
            closed = True
        assert closed


class TestUpdateDecisionContext:
    """Targeted context-column update for cross-decision enrichment."""

    def _seed(self, store: MigrationStore) -> None:
        store.save_decision({
            "decision_id": "D0001",
            "type": "MISSING_DATA",
            "severity": "MEDIUM",
            "summary": "phone:abc missing mac",
            "context": {
                "object_type": "device",
                "canonical_id": "phone:abc",
                "missing_fields": ["mac"],
            },
            "options": [
                {"id": "skip", "label": "Skip", "impact": "Excluded"},
                {"id": "provide_data", "label": "Provide", "impact": "Supply"},
            ],
            "chosen_option": None,
            "resolved_at": None,
            "resolved_by": None,
            "fingerprint": "fp_d0001",
            "run_id": store.current_run_id,
        })

    def test_patches_context_in_place(self) -> None:
        store = MigrationStore(":memory:")
        self._seed(store)

        new_ctx = {
            "object_type": "device",
            "canonical_id": "phone:abc",
            "missing_fields": ["mac"],
            "is_on_incompatible_device": True,
        }
        store.update_decision_context("D0001", new_ctx)

        dec = store.get_decision("D0001")
        assert dec is not None
        assert dec["context"]["is_on_incompatible_device"] is True
        # Untouched columns must stay put.
        assert dec["type"] == "MISSING_DATA"
        assert dec["severity"] == "MEDIUM"
        assert dec["summary"] == "phone:abc missing mac"
        assert dec["fingerprint"] == "fp_d0001"
        assert dec["chosen_option"] is None

    def test_raises_on_unknown_decision_id(self) -> None:
        store = MigrationStore(":memory:")
        with pytest.raises(KeyError):
            store.update_decision_context("D_DOES_NOT_EXIST", {"x": 1})

    def test_idempotent(self) -> None:
        store = MigrationStore(":memory:")
        self._seed(store)
        ctx = {
            "object_type": "device",
            "canonical_id": "phone:abc",
            "missing_fields": ["mac"],
            "is_on_incompatible_device": False,
        }
        store.update_decision_context("D0001", ctx)
        store.update_decision_context("D0001", ctx)
        dec = store.get_decision("D0001")
        assert dec["context"]["is_on_incompatible_device"] is False
