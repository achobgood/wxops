"""Tests for store.merge_decisions() — fingerprint-based decision merge algorithm.

The merge algorithm (from 07-idempotency-resumability.md):
- Matches existing decisions against new decisions by fingerprint
- Same fingerprint + resolved -> KEPT (preserve resolution)
- Same fingerprint + pending  -> UPDATED (update context)
- New fingerprint only         -> NEW (insert)
- Old fingerprint only + pending  -> STALE (mark stale)
- Old fingerprint only + resolved -> INVALIDATED (mark stale)

Stale decisions are marked with chosen_option='__stale__' and resolved_by='stale'.

Uses real :memory: SQLite store, no mocks.
"""

from __future__ import annotations

from typing import Any

import pytest

from wxcli.migration.store import MigrationStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_store() -> MigrationStore:
    return MigrationStore(":memory:")


def _make_decision(
    decision_id: str,
    dtype: str = "MISSING_DATA",
    fingerprint: str | None = None,
    chosen_option: str | None = None,
    resolved_by: str | None = None,
    context: dict[str, Any] | None = None,
    summary: str | None = None,
    severity: str = "MEDIUM",
    run_id: str = "test-run-1",
) -> dict[str, Any]:
    fp = fingerprint or f"fp_{decision_id}"
    return {
        "decision_id": decision_id,
        "type": dtype,
        "severity": severity,
        "summary": summary or f"Test decision {decision_id}",
        "context": context or {"test": True},
        "options": [{"id": "skip", "label": "Skip", "impact": "Skip it"}],
        "chosen_option": chosen_option,
        "resolved_at": None,
        "resolved_by": resolved_by,
        "fingerprint": fp,
        "run_id": run_id,
    }


def _seed_decisions(
    store: MigrationStore,
    count: int,
    prefix: str = "D",
    start: int = 1,
    dtype: str = "MISSING_DATA",
    run_id: str = "test-run-1",
) -> list[dict[str, Any]]:
    """Insert `count` pending decisions into the store and return their dicts."""
    decisions = []
    for i in range(start, start + count):
        d = _make_decision(
            decision_id=f"{prefix}{i:04d}",
            dtype=dtype,
            run_id=run_id,
        )
        store.save_decision(d)
        decisions.append(d)
    return decisions


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMergeNewDecisions:
    """test_merge_new_decisions: Empty store. Merge 5 new decisions.
    All should be 'new'. Verify counts."""

    def test_merge_all_new(self) -> None:
        store = _make_store()

        new_decisions = [
            _make_decision(f"D{i:04d}") for i in range(1, 6)
        ]

        result = store.merge_decisions(new_decisions)

        assert result["new"] == 5
        assert result["kept"] == 0
        assert result["updated"] == 0
        assert result["stale"] == 0
        assert result["invalidated"] == 0

        # All 5 should be in the store
        all_decs = store.get_all_decisions()
        assert len(all_decs) == 5

    def test_merge_new_preserves_content(self) -> None:
        """New decisions should retain all their fields."""
        store = _make_store()

        d = _make_decision(
            "D0001",
            dtype="DEVICE_INCOMPATIBLE",
            severity="HIGH",
            summary="Test device",
            context={"model": "7941G"},
        )
        store.merge_decisions([d])

        stored = store.get_all_decisions()
        assert len(stored) == 1
        assert stored[0]["type"] == "DEVICE_INCOMPATIBLE"
        assert stored[0]["severity"] == "HIGH"
        assert stored[0]["summary"] == "Test device"
        assert stored[0]["context"]["model"] == "7941G"


class TestMergePreservesResolved:
    """test_merge_preserves_resolved: Insert 3 decisions, resolve 1.
    Re-merge with same fingerprints. Verify resolved decision is kept
    (chosen_option preserved)."""

    def test_resolved_kept_on_remerge(self) -> None:
        store = _make_store()

        # Insert 3 decisions
        originals = _seed_decisions(store, 3)

        # Resolve the first one
        store.resolve_decision("D0001", "skip", "user")

        # Verify resolution stuck
        resolved = store.get_decision("D0001")
        assert resolved["chosen_option"] == "skip"
        assert resolved["resolved_by"] == "user"

        # Re-merge with the same fingerprints (simulating re-analysis)
        new_run = [
            _make_decision(f"NEW{i:04d}", fingerprint=f"fp_D{i:04d}", run_id="run-2")
            for i in range(1, 4)
        ]
        result = store.merge_decisions(new_run)

        assert result["kept"] == 1      # D0001 was resolved
        assert result["updated"] == 2   # D0002, D0003 were pending
        assert result["new"] == 0
        assert result["stale"] == 0
        assert result["invalidated"] == 0

        # Verify D0001 still resolved
        dec = store.get_decision("D0001")
        assert dec["chosen_option"] == "skip"
        assert dec["resolved_by"] == "user"

    def test_resolved_context_updated_on_kept(self) -> None:
        """Even when kept, the context should be refreshed from the new run."""
        store = _make_store()

        d = _make_decision("D0001", context={"version": 1})
        store.save_decision(d)
        store.resolve_decision("D0001", "skip", "user")

        new = _make_decision(
            "D_NEW",
            fingerprint="fp_D0001",
            context={"version": 2, "extra": "data"},
            run_id="run-2",
        )
        result = store.merge_decisions([new])

        assert result["kept"] == 1

        dec = store.get_decision("D0001")
        # Resolution preserved
        assert dec["chosen_option"] == "skip"
        # Context updated to new version
        assert dec["context"]["version"] == 2
        assert dec["context"]["extra"] == "data"


class TestMergeUpdatesPending:
    """test_merge_updates_pending: Insert 3 pending decisions. Re-merge with
    same fingerprints but updated context. Verify context is updated but
    decision_id preserved."""

    def test_pending_context_updated(self) -> None:
        store = _make_store()

        originals = _seed_decisions(store, 3)

        # Re-merge with same fingerprints but different context
        updated = [
            _make_decision(
                f"NEW{i:04d}",
                fingerprint=f"fp_D{i:04d}",
                context={"updated": True, "iteration": 2},
                summary=f"Updated summary {i}",
                run_id="run-2",
            )
            for i in range(1, 4)
        ]
        result = store.merge_decisions(updated)

        assert result["updated"] == 3
        assert result["kept"] == 0
        assert result["new"] == 0
        assert result["stale"] == 0

        # Verify original decision_ids preserved
        for i in range(1, 4):
            dec = store.get_decision(f"D{i:04d}")
            assert dec is not None, f"D{i:04d} should still exist"
            assert dec["context"]["updated"] is True
            assert dec["context"]["iteration"] == 2
            assert dec["summary"] == f"Updated summary {i}"

    def test_pending_decision_id_not_replaced(self) -> None:
        """The decision_id from the original insert should persist, not the new one."""
        store = _make_store()
        store.save_decision(_make_decision("D0001"))

        new = _make_decision("D_DIFFERENT_ID", fingerprint="fp_D0001", run_id="run-2")
        store.merge_decisions([new])

        # Original ID preserved
        assert store.get_decision("D0001") is not None
        # New ID should NOT exist as a separate entry
        assert store.get_decision("D_DIFFERENT_ID") is None


class TestMergeMarksStale:
    """test_merge_marks_stale: Insert 3 decisions. Re-merge with only 2 of
    the fingerprints. Verify the missing one is marked stale."""

    def test_missing_fingerprint_marked_stale(self) -> None:
        store = _make_store()

        _seed_decisions(store, 3)

        # Re-merge with only 2 fingerprints (D0001 and D0002, but not D0003)
        new = [
            _make_decision(f"NEW{i:04d}", fingerprint=f"fp_D{i:04d}", run_id="run-2")
            for i in range(1, 3)  # 1, 2 only
        ]
        result = store.merge_decisions(new)

        assert result["updated"] == 2  # D0001, D0002 were pending and matched
        assert result["stale"] == 1    # D0003 pending, fingerprint gone
        assert result["new"] == 0
        assert result["invalidated"] == 0

        # Verify D0003 is stale
        dec = store.get_decision("D0003")
        assert dec["chosen_option"] == "__stale__"
        assert dec["resolved_by"] == "stale"

    def test_stale_decisions_excluded_from_subsequent_merge(self) -> None:
        """Once marked stale, a decision should not participate in future merges."""
        store = _make_store()

        _seed_decisions(store, 2)

        # First merge: remove D0002
        result1 = store.merge_decisions([
            _make_decision("N1", fingerprint="fp_D0001", run_id="run-2")
        ])
        assert result1["stale"] == 1  # D0002 marked stale

        # Second merge: only D0001 again. D0002 should NOT show as stale again.
        result2 = store.merge_decisions([
            _make_decision("N2", fingerprint="fp_D0001", run_id="run-3")
        ])
        assert result2["updated"] == 1
        assert result2["stale"] == 0  # D0002 already stale, not recounted


class TestMergeInvalidatesResolvedGone:
    """test_merge_invalidates_resolved_gone: Insert 3 decisions, resolve 1.
    Re-merge without that decision's fingerprint. Verify the resolved one
    is 'invalidated' (marked stale)."""

    def test_resolved_gone_is_invalidated(self) -> None:
        store = _make_store()

        _seed_decisions(store, 3)
        store.resolve_decision("D0001", "skip", "user")

        # Re-merge without D0001's fingerprint
        new = [
            _make_decision(f"NEW{i:04d}", fingerprint=f"fp_D{i:04d}", run_id="run-2")
            for i in range(2, 4)  # 2, 3 only
        ]
        result = store.merge_decisions(new)

        assert result["invalidated"] == 1  # D0001 was resolved, now gone
        assert result["updated"] == 2      # D0002, D0003 pending, still present
        assert result["stale"] == 0
        assert result["new"] == 0
        assert result["kept"] == 0

        # Verify D0001 is invalidated (stale markers applied)
        dec = store.get_decision("D0001")
        assert dec["chosen_option"] == "__stale__"
        assert dec["resolved_by"] == "stale"


class TestMergeFullScenario:
    """test_merge_full_scenario: Per acceptance criteria from 07-idempotency.

    Given 20 decisions with 5 resolved, re-running analysis with modified data
    preserves the 5 resolved (matching fingerprints), produces new decisions
    for changed data, marks stale decisions.

    Setup:
    - 20 initial decisions (D0001..D0020)
    - Resolve 5 (D0001..D0005)
    - Re-merge with 18 matching fingerprints + 3 new fingerprints
      (fp_D0019 and fp_D0020 removed)

    Expected:
    - 5 kept (D0001..D0005 resolved, fingerprints still present)
    - 13 updated (D0006..D0018 pending, fingerprints still present)
    - 3 new (brand new fingerprints)
    - 1 stale (D0019 pending, fingerprint gone)
    - 1 invalidated (D0020 was pending — wait, let's make D0005 resolved
      and one resolved one gone too)

    Revised setup for invalidated:
    - 20 initial decisions
    - Resolve D0001..D0005
    - Re-merge with 18 fingerprints: fp_D0001..D0018 present
      + 3 new fingerprints fp_N1, fp_N2, fp_N3
    - fp_D0019 gone (pending -> stale)
    - fp_D0020 gone AND D0020 resolved -> actually let's resolve D0020 too

    Final setup:
    - 20 decisions: D0001..D0020
    - Resolve 6: D0001..D0005 and D0020
    - Re-merge: fp_D0001..D0018 + fp_N1..N3 (21 new decisions)
    - fp_D0019 gone (pending) -> stale
    - fp_D0020 gone (resolved) -> invalidated
    - D0001..D0005 matched (resolved) -> kept = 5
    - D0006..D0018 matched (pending) -> updated = 13
    - fp_N1..N3 new -> new = 3
    """

    def test_full_merge_scenario(self) -> None:
        store = _make_store()

        # Insert 20 decisions
        _seed_decisions(store, 20)

        # Resolve D0001..D0005 and D0020
        for i in range(1, 6):
            store.resolve_decision(f"D{i:04d}", "skip", "user")
        store.resolve_decision("D0020", "manual", "user")

        # Build new decision set:
        # - D0001..D0018 fingerprints present (18 matching)
        # - D0019, D0020 fingerprints absent (2 removed)
        # - 3 brand new fingerprints
        new_decisions = []

        # 18 matching fingerprints
        for i in range(1, 19):
            new_decisions.append(
                _make_decision(
                    f"NEW{i:04d}",
                    fingerprint=f"fp_D{i:04d}",
                    context={"iteration": 2},
                    run_id="run-2",
                )
            )

        # 3 brand new decisions
        for j in range(1, 4):
            new_decisions.append(
                _make_decision(
                    f"BRAND{j:04d}",
                    fingerprint=f"fp_BRAND_{j}",
                    context={"brand_new": True},
                    run_id="run-2",
                )
            )

        result = store.merge_decisions(new_decisions)

        # D0001..D0005: resolved, fingerprint present -> kept
        assert result["kept"] == 5

        # D0006..D0018: pending, fingerprint present -> updated
        assert result["updated"] == 13

        # fp_BRAND_1..3: new fingerprints -> new
        assert result["new"] == 3

        # D0019: pending, fingerprint gone -> stale
        assert result["stale"] == 1

        # D0020: resolved, fingerprint gone -> invalidated
        assert result["invalidated"] == 1

        # Verify stale D0019
        d19 = store.get_decision("D0019")
        assert d19["chosen_option"] == "__stale__"
        assert d19["resolved_by"] == "stale"

        # Verify invalidated D0020
        d20 = store.get_decision("D0020")
        assert d20["chosen_option"] == "__stale__"
        assert d20["resolved_by"] == "stale"

        # Verify resolved D0001..D0005 still resolved
        for i in range(1, 6):
            dec = store.get_decision(f"D{i:04d}")
            assert dec["chosen_option"] == "skip", f"D{i:04d} should still be resolved"
            assert dec["resolved_by"] == "user"

        # Verify brand new decisions exist in store
        all_decs = store.get_all_decisions()
        all_fps = {d["fingerprint"] for d in all_decs}
        for j in range(1, 4):
            assert f"fp_BRAND_{j}" in all_fps

        # Total non-stale decisions: 5 kept + 13 updated + 3 new = 21
        active = [d for d in all_decs if d.get("chosen_option") != "__stale__"]
        assert len(active) == 21


class TestMergeEdgeCases:
    """Additional edge cases for merge robustness."""

    def test_merge_empty_new_list(self) -> None:
        """Merging an empty list should mark all existing pending as stale."""
        store = _make_store()
        _seed_decisions(store, 3)

        result = store.merge_decisions([])

        assert result["stale"] == 3
        assert result["new"] == 0
        assert result["kept"] == 0

    def test_merge_empty_store_empty_new(self) -> None:
        """Empty store + empty new list = all zeros."""
        store = _make_store()
        result = store.merge_decisions([])

        assert result == {"kept": 0, "updated": 0, "new": 0, "stale": 0, "invalidated": 0}

    def test_merge_duplicate_fingerprints_in_new(self) -> None:
        """If new list has duplicate fingerprints, last one wins (dict behavior)."""
        store = _make_store()

        new = [
            _make_decision("D0001", fingerprint="fp_dup", context={"version": 1}),
            _make_decision("D0002", fingerprint="fp_dup", context={"version": 2}),
        ]
        result = store.merge_decisions(new)

        # Only 1 new (deduped by fingerprint via dict key)
        assert result["new"] == 1

        all_decs = store.get_all_decisions()
        assert len(all_decs) == 1
        assert all_decs[0]["context"]["version"] == 2

    def test_merge_log_entries_created(self) -> None:
        """Each merge action should produce a merge_log entry."""
        store = _make_store()

        _seed_decisions(store, 2)
        store.resolve_decision("D0001", "skip", "user")

        # Merge with D0001 fp (kept), no D0002 fp (stale), + 1 new
        new = [
            _make_decision("N1", fingerprint="fp_D0001", run_id="run-2"),
            _make_decision("N2", fingerprint="fp_BRAND", run_id="run-2"),
        ]
        result = store.merge_decisions(new)

        assert result["kept"] == 1
        assert result["stale"] == 1
        assert result["new"] == 1

        # Verify merge_log has entries
        rows = store.conn.execute("SELECT * FROM merge_log").fetchall()
        actions = [dict(r)["action"] for r in rows]
        assert "kept" in actions
        assert "stale" in actions
        assert "new" in actions
