"""Tests for enrich_cross_decision_context().

This helper writes `is_on_incompatible_device: bool` into every non-stale
MISSING_DATA decision's context, based on the set of non-stale
DEVICE_INCOMPATIBLE decisions in the store. The new default auto-rule
`{type: MISSING_DATA, match: {is_on_incompatible_device: true}, choice: skip}`
consumes this field.
"""

from __future__ import annotations

import hashlib

import pytest

from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.analysis_pipeline import (
    enrich_cross_decision_context,
)


def _fp(did: str, dtype: str) -> str:
    return hashlib.sha256(f"{dtype}:{did}".encode()).hexdigest()[:16]


def _save(
    store: MigrationStore,
    did: str,
    dtype: str,
    context: dict,
    *,
    chosen_option: str | None = None,
) -> None:
    store.save_decision({
        "decision_id": did,
        "type": dtype,
        "severity": "MEDIUM",
        "summary": f"{dtype} {did}",
        "context": context,
        "options": [
            {"id": "skip", "label": "Skip", "impact": "Excluded"},
            {"id": "provide_data", "label": "Provide", "impact": "Supply"},
        ],
        "chosen_option": chosen_option,
        "resolved_at": None,
        "resolved_by": None,
        "fingerprint": _fp(did, dtype),
        "run_id": store.current_run_id,
    })


def test_enrich_no_decisions() -> None:
    store = MigrationStore(":memory:")
    count = enrich_cross_decision_context(store)
    assert count == 0


def test_enrich_no_incompatible_devices() -> None:
    """MISSING_DATA exists but no DEVICE_INCOMPATIBLE → field is False."""
    store = MigrationStore(":memory:")
    _save(store, "D0001", "MISSING_DATA", {
        "object_type": "device",
        "canonical_id": "phone:001",
        "missing_fields": ["mac"],
    })
    count = enrich_cross_decision_context(store)
    assert count == 1
    dec = store.get_decision("D0001")
    assert dec["context"]["is_on_incompatible_device"] is False


def test_enrich_one_incompatible_one_missing_match() -> None:
    """DI on phone:001 + MD on phone:001 → True."""
    store = MigrationStore(":memory:")
    _save(store, "D0001", "DEVICE_INCOMPATIBLE", {
        "device_id": "phone:001",
        "_affected_objects": ["phone:001"],
    })
    _save(store, "D0002", "MISSING_DATA", {
        "object_type": "device",
        "canonical_id": "phone:001",
        "missing_fields": ["mac"],
    })
    count = enrich_cross_decision_context(store)
    # Only MISSING_DATA is enriched (DEVICE_INCOMPATIBLE is not touched).
    assert count == 1
    assert store.get_decision("D0002")["context"]["is_on_incompatible_device"] is True
    # DEVICE_INCOMPATIBLE context is untouched.
    assert "is_on_incompatible_device" not in store.get_decision("D0001")["context"]


def test_enrich_via_affected_objects() -> None:
    """MD context without canonical_id but _affected_objects hit → True."""
    store = MigrationStore(":memory:")
    _save(store, "D0001", "DEVICE_INCOMPATIBLE", {
        "_affected_objects": ["phone:xyz"],
    })
    _save(store, "D0002", "MISSING_DATA", {
        # No canonical_id — only _affected_objects identifies the device.
        "missing_fields": ["mac"],
        "_affected_objects": ["phone:xyz"],
    })
    count = enrich_cross_decision_context(store)
    assert count == 1
    assert store.get_decision("D0002")["context"]["is_on_incompatible_device"] is True


def test_enrich_idempotent() -> None:
    """Running twice produces the same field values and safe count."""
    store = MigrationStore(":memory:")
    _save(store, "D0001", "DEVICE_INCOMPATIBLE", {
        "_affected_objects": ["phone:001"],
    })
    _save(store, "D0002", "MISSING_DATA", {
        "object_type": "device",
        "canonical_id": "phone:001",
        "missing_fields": ["mac"],
    })
    enrich_cross_decision_context(store)
    # Re-run: field value is stable, no crash.
    enrich_cross_decision_context(store)
    assert store.get_decision("D0002")["context"]["is_on_incompatible_device"] is True


def test_enrich_skips_stale_decisions() -> None:
    """__stale__ decisions are not enriched."""
    store = MigrationStore(":memory:")
    _save(store, "D0001", "DEVICE_INCOMPATIBLE", {
        "_affected_objects": ["phone:001"],
    })
    _save(
        store,
        "D0002",
        "MISSING_DATA",
        {
            "object_type": "device",
            "canonical_id": "phone:001",
            "missing_fields": ["mac"],
        },
        chosen_option="__stale__",
    )
    count = enrich_cross_decision_context(store)
    # Stale MD is skipped entirely.
    assert count == 0
    dec = store.get_decision("D0002")
    assert "is_on_incompatible_device" not in dec["context"]


def test_md_fingerprint_stable_before_and_after_enrichment() -> None:
    """Fingerprint-safety guard: MissingDataAnalyzer.fingerprint() only
    hashes type + canonical_id + sorted(missing_fields). Enriching the
    context with is_on_incompatible_device must NOT change what a future
    merge_decisions() call would compute as the fingerprint for the same
    decision. This is load-bearing for the enrichment-before-rules design.
    """
    from wxcli.migration.models import DecisionType
    from wxcli.migration.transform.analyzers.missing_data import MissingDataAnalyzer

    analyzer = MissingDataAnalyzer()
    ctx_before = {
        "object_type": "device",
        "canonical_id": "phone:001",
        "missing_fields": ["mac", "owner_canonical_id"],
    }
    ctx_after = dict(ctx_before)
    ctx_after["is_on_incompatible_device"] = True

    fp_before = analyzer.fingerprint(DecisionType.MISSING_DATA, ctx_before)
    fp_after = analyzer.fingerprint(DecisionType.MISSING_DATA, ctx_after)
    assert fp_before == fp_after
