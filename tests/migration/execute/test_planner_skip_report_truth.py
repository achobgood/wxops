"""The planner's skip report must be true in both directions (F08 + F09).

Two halves of one question, from the round-3 audit:

**F09 — it reported skips that did not happen.** ``expand_to_operations`` calls
``_warn_skip`` for every stale decision attached to an object and then falls
through to expansion — no ``continue``, unlike the genuine skip paths. Measured
on director-demo-2026-04-15: of 1129 ``Planner skip:`` lines, **766** are these
fall-throughs (405 DEVICE_INCOMPATIBLE + 361 MISSING_DATA), and the entities are
all in ``plan_operations``. ``PlannerUnresolvedError`` says "entities skipped due
to unresolved decisions" — of entities that were planned.

**F08 — it missed the skips that did.** 23 of 300 users sit at
``objects.status='normalized'`` while 277 advance to ``'analyzed'``.
``expand_to_operations`` queries ``'analyzed'`` only, so it never sees them, and
``_count_needs_decision_by_type`` counts ``'needs_decision'`` only, so the
held-back roll-up misses them too. They appear in none of the 1370 lines.

Both groups carry stale MISSING_DATA decisions — measured, all 300 of them — so a
stale decision is *not* what distinguishes planned from stranded. ``status`` is.
A warning that fires on 277 of 277 planned users carries no information.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from wxcli.migration.execute.planner import (
    PlannerSkipReport,
    PlannerUnresolvedError,
    expand_to_operations,
)
from wxcli.migration.models import (
    CanonicalDevice,
    CanonicalUser,
    DeviceCompatibilityTier,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore


def _prov() -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id="pk",
        source_name="n",
        extracted_at=datetime(2026, 7, 29, tzinfo=timezone.utc),
    )


@pytest.fixture()
def store(tmp_path):
    s = MigrationStore(tmp_path / "t.db")
    yield s
    s.close()


def _stale_decision(store, did, dtype, cid, fp):
    store.save_decision({
        "decision_id": did,
        "type": dtype,
        "severity": "HIGH",
        "summary": "invalidated by re-analysis",
        "context": {"_affected_objects": [cid]},
        "options": [{"id": "skip", "label": "Skip", "impact": "none"}],
        "chosen_option": "__stale__",
        "resolved_at": "2026-01-01T00:00:00Z",
        "resolved_by": "stale",
        "fingerprint": fp,
        "run_id": "r",
    })


# ---------------------------------------------------------------------------
# F09 — warned-but-expanded is not a skip
# ---------------------------------------------------------------------------

class TestExpandedEntitiesAreNotReportedAsSkipped:
    def test_stale_decision_on_expanded_object_is_an_anomaly_not_a_skip(self, store):
        """The entity got operations, so it was not skipped."""
        dev = CanonicalDevice(
            canonical_id="device:d1",
            provenance=_prov(),
            mac="AABBCCDDEEFF",
            compatibility_tier=DeviceCompatibilityTier.NATIVE_MPP,
        )
        dev.status = MigrationStatus.ANALYZED
        store.upsert_object(dev)
        _stale_decision(store, "D1", "DEVICE_INCOMPATIBLE", "device:d1", "fp1")

        report = PlannerSkipReport()
        ops = expand_to_operations(store, report=report)

        assert [o for o in ops if o.canonical_id == "device:d1"], "must still be planned"
        assert not any(e.canonical_id == "device:d1" for e in report.entries), (
            "an entity that was planned must not appear in the skip report"
        )
        assert any(a.canonical_id == "device:d1" for a in report.anomalies), (
            "but the stale decision must still be surfaced, as an anomaly"
        )

    def test_anomaly_keeps_the_decision_context(self, store):
        """Reclassifying must not lose the diagnostic detail."""
        dev = CanonicalDevice(
            canonical_id="device:d2",
            provenance=_prov(),
            mac="AABBCCDDEE00",
            compatibility_tier=DeviceCompatibilityTier.NATIVE_MPP,
        )
        dev.status = MigrationStatus.ANALYZED
        store.upsert_object(dev)
        _stale_decision(store, "D2", "DEVICE_INCOMPATIBLE", "device:d2", "fp2")

        report = PlannerSkipReport()
        expand_to_operations(store, report=report)

        anomaly = next(a for a in report.anomalies if a.canonical_id == "device:d2")
        assert anomaly.decision_type == "DEVICE_INCOMPATIBLE"
        assert anomaly.decision_state == "stale"
        assert anomaly.entity_type == "device"

    def test_anomalies_do_not_trip_fail_on_unresolved(self, store):
        """The gate says "entities skipped" — it must not fire on planned ones.

        This reverses a 2026-04-15 expectation deliberately. That guard was
        written for the DEVICE_FIRMWARE_CONVERTIBLE bug, where 611 phones were
        silently *dropped*. These are not dropped, and on director-demo the gate
        would abort a correct plan citing 766 entities that are all in it.
        """
        dev = CanonicalDevice(
            canonical_id="device:d3",
            provenance=_prov(),
            mac="AABBCCDDEE11",
            compatibility_tier=DeviceCompatibilityTier.NATIVE_MPP,
        )
        dev.status = MigrationStatus.ANALYZED
        store.upsert_object(dev)
        _stale_decision(store, "D3", "DEVICE_INCOMPATIBLE", "device:d3", "fp3")

        report = PlannerSkipReport()
        ops = expand_to_operations(store, report=report, fail_on_unresolved=True)
        assert [o for o in ops if o.canonical_id == "device:d3"]
        assert not report.has_unresolved_skips

    def test_genuine_skips_still_recorded_and_still_trip_the_gate(self, store):
        """A resolved 'skip' really does suppress the entity — unchanged."""
        dev = CanonicalDevice(
            canonical_id="device:d4",
            provenance=_prov(),
            mac="AABBCCDDEE22",
            compatibility_tier=DeviceCompatibilityTier.NATIVE_MPP,
        )
        dev.status = MigrationStatus.ANALYZED
        store.upsert_object(dev)
        store.save_decision({
            "decision_id": "D4",
            "type": "DEVICE_INCOMPATIBLE",
            "severity": "HIGH",
            "summary": "operator chose skip",
            "context": {"_affected_objects": ["device:d4"]},
            "options": [{"id": "skip", "label": "Skip", "impact": "none"}],
            "chosen_option": "skip",
            "resolved_at": "2026-01-01T00:00:00Z",
            "resolved_by": "user",
            "fingerprint": "fp4",
            "run_id": "r",
        })

        report = PlannerSkipReport()
        ops = expand_to_operations(store, report=report)
        assert not [o for o in ops if o.canonical_id == "device:d4"]
        assert any(e.canonical_id == "device:d4" for e in report.entries)


# ---------------------------------------------------------------------------
# F08 — objects stranded before the planner
# ---------------------------------------------------------------------------

class TestStrandedObjectsAreReported:
    def test_object_below_analyzed_is_counted(self, store):
        """23 of 300 users were dropped with no operator-visible signal."""
        for i in range(3):
            u = CanonicalUser(
                canonical_id=f"user:planned{i}",
                provenance=_prov(),
                emails=[f"p{i}@x.com"],
            )
            u.status = MigrationStatus.ANALYZED
            store.upsert_object(u)
        for i in range(2):
            u = CanonicalUser(
                canonical_id=f"user:stranded{i}",
                provenance=_prov(),
                emails=[f"s{i}@x.com"],
            )
            u.status = MigrationStatus.NORMALIZED
            store.upsert_object(u)
            _stale_decision(store, f"DS{i}", "MISSING_DATA", f"user:stranded{i}", f"fps{i}")

        report = PlannerSkipReport()
        expand_to_operations(store, report=report)

        assert report.stranded_counts.get("user") == 2, (
            "objects that never reached 'analyzed' must be counted"
        )

    def test_stranded_objects_are_not_double_counted_as_skips(self, store):
        """They never reached expansion, so they are not skip entries."""
        u = CanonicalUser(
            canonical_id="user:s1", provenance=_prov(), emails=["s1@x.com"]
        )
        u.status = MigrationStatus.NORMALIZED
        store.upsert_object(u)

        report = PlannerSkipReport()
        expand_to_operations(store, report=report)
        assert not any(e.canonical_id == "user:s1" for e in report.entries)
        assert report.stranded_counts.get("user") == 1

    def test_stranded_objects_trip_fail_on_unresolved(self, store):
        """These are genuinely absent from the plan — the gate's real purpose.

        The gate was blind to them: it keyed on skip entries, and a stranded
        object produces none.
        """
        u = CanonicalUser(
            canonical_id="user:s2", provenance=_prov(), emails=["s2@x.com"]
        )
        u.status = MigrationStatus.NORMALIZED
        store.upsert_object(u)

        with pytest.raises(PlannerUnresolvedError) as exc:
            expand_to_operations(store, fail_on_unresolved=True)
        assert "user" in str(exc.value)

    def test_no_stranded_report_when_everything_advanced(self, store):
        u = CanonicalUser(
            canonical_id="user:ok", provenance=_prov(), emails=["ok@x.com"]
        )
        u.status = MigrationStatus.ANALYZED
        store.upsert_object(u)

        report = PlannerSkipReport()
        expand_to_operations(store, report=report)
        assert report.stranded_counts == {}
        assert not report.has_unresolved_skips

    def test_cucm_source_types_are_not_counted_as_stranded(self, store):
        """The correction this fix needed on its first attempt.

        A first cut counted every `normalized` object and reported **2005**
        entities "ABSENT from this plan" on director-demo — `phone: 1100`,
        `button_template: 242`, `info_phone_button_template: 232` and so on. Those
        are CUCM-side source and intermediate types with no expander: `phone`
        normalizes into `device`, `hunt_pilot` into `hunt_group`. Only 67 of the
        2005 were real. Same by-design-vs-genuine error as the F03 fix.
        """
        store.conn.execute(
            "INSERT INTO objects (canonical_id, object_type, status, data, "
            "created_at, updated_at) VALUES (?,?,?,?,?,?)",
            ("phone:SEP001", "phone", "normalized", "{}", "t", "t"),
        )
        store.conn.execute(
            "INSERT INTO objects (canonical_id, object_type, status, data, "
            "created_at, updated_at) VALUES (?,?,?,?,?,?)",
            ("button_template:bt1", "button_template", "normalized", "{}", "t", "t"),
        )
        store.conn.commit()

        report = PlannerSkipReport()
        expand_to_operations(store, report=report)

        assert "phone" not in report.stranded_counts
        assert "button_template" not in report.stranded_counts
        assert report.stranded_counts == {}

    def test_data_only_types_are_not_counted_as_stranded(self, store):
        """`line` and `voicemail_profile` produce no operations by design."""
        store.conn.execute(
            "INSERT INTO objects (canonical_id, object_type, status, data, "
            "created_at, updated_at) VALUES (?,?,?,?,?,?)",
            ("voicemail_profile:vp1", "voicemail_profile", "normalized", "{}", "t", "t"),
        )
        store.conn.commit()

        report = PlannerSkipReport()
        expand_to_operations(store, report=report)
        assert report.stranded_counts == {}

    def test_discovered_only_objects_are_not_counted_as_stranded(self, store):
        """Pre-normalize objects are not the planner's business.

        An object at 'discovered' has not been through normalize yet, so it was
        never a candidate for this plan. Only objects that got as far as
        normalization and then stopped are a signal.
        """
        u = CanonicalUser(
            canonical_id="user:raw", provenance=_prov(), emails=["raw@x.com"]
        )
        u.status = MigrationStatus.DISCOVERED
        store.upsert_object(u)

        report = PlannerSkipReport()
        expand_to_operations(store, report=report)
        assert report.stranded_counts == {}
