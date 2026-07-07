"""Tests for classify_decisions(store, config).

classify_decisions is a thin wrapper over preview_auto_rules — its
job is to split pending decisions into (auto_apply, needs_input)
groups based on the project's config["auto_rules"].
"""

from __future__ import annotations

import hashlib

import pytest

from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.decisions import (
    classify_decisions,
    generate_decision_review,
)


def _fp(did: str, dtype: str) -> str:
    return hashlib.sha256(f"{dtype}:{did}".encode()).hexdigest()[:16]


def _save(
    store: MigrationStore,
    did: str,
    dtype: str,
    context: dict,
    *,
    options: list | None = None,
    chosen_option: str | None = None,
) -> None:
    opts = options or [
        {"id": "skip", "label": "Skip", "impact": "Excluded"},
        {"id": "manual", "label": "Manual", "impact": "Manual"},
    ]
    store.save_decision({
        "decision_id": did,
        "type": dtype,
        "severity": "MEDIUM",
        "summary": f"{dtype} {did}",
        "context": context,
        "options": opts,
        "chosen_option": chosen_option,
        "resolved_at": None,
        "resolved_by": None,
        "fingerprint": _fp(did, dtype),
        "run_id": store.current_run_id,
    })


@pytest.fixture
def store() -> MigrationStore:
    return MigrationStore(":memory:")


def test_classify_returns_auto_apply_from_preview(store: MigrationStore) -> None:
    _save(store, "D0001", "DEVICE_INCOMPATIBLE", {})
    _save(store, "D0002", "WORKSPACE_LICENSE_TIER", {"workspace_name": "Lobby"})

    config = {
        "auto_rules": [{"type": "DEVICE_INCOMPATIBLE", "choice": "skip"}]
    }
    auto, needs = classify_decisions(store, config)

    auto_ids = {d["decision_id"] for d in auto}
    needs_ids = {d["decision_id"] for d in needs}
    assert "D0001" in auto_ids
    assert "D0002" in needs_ids

    # Auto_apply entries must carry auto_choice + auto_reason (from preview).
    d1 = next(d for d in auto if d["decision_id"] == "D0001")
    assert d1["auto_choice"] == "skip"
    assert d1["auto_reason"]


def test_classify_needs_input_excludes_auto_apply_decisions(
    store: MigrationStore,
) -> None:
    _save(store, "D0001", "DEVICE_INCOMPATIBLE", {})
    _save(store, "D0002", "DEVICE_INCOMPATIBLE", {})

    config = {
        "auto_rules": [{"type": "DEVICE_INCOMPATIBLE", "choice": "skip"}]
    }
    auto, needs = classify_decisions(store, config)

    assert len(auto) == 2
    # Every decision the config resolves must NOT reappear in needs_input.
    assert needs == []


def test_classify_with_custom_config_rule(store: MigrationStore) -> None:
    """A custom rule in config.json should resolve matching decisions."""
    _save(store, "D0001", "DN_AMBIGUOUS", {"dn_length": 3, "dn": "101"},
          options=[
              {"id": "extension_only", "label": "Extension", "impact": "Internal"},
              {"id": "skip", "label": "Skip", "impact": "Excluded"},
          ])

    config = {
        "auto_rules": [
            {
                "type": "DN_AMBIGUOUS",
                "match": {"dn_length_lte": 4},
                "choice": "extension_only",
                "reason": "3-digit extension matches internal plan",
            }
        ]
    }
    auto, needs = classify_decisions(store, config)

    assert len(auto) == 1
    assert auto[0]["auto_choice"] == "extension_only"
    assert auto[0]["auto_reason"] == "3-digit extension matches internal plan"
    assert needs == []


def test_classify_with_empty_auto_rules(store: MigrationStore) -> None:
    """Empty auto_rules → every pending decision is needs_input."""
    _save(store, "D0001", "DEVICE_INCOMPATIBLE", {})
    _save(store, "D0002", "WORKSPACE_LICENSE_TIER", {"workspace_name": "Lobby"})

    config = {"auto_rules": []}
    auto, needs = classify_decisions(store, config)
    assert auto == []
    assert {d["decision_id"] for d in needs} == {"D0001", "D0002"}


def test_classify_excludes_resolved_decisions(store: MigrationStore) -> None:
    """Already-resolved decisions must not appear in either group."""
    _save(store, "D0001", "DEVICE_INCOMPATIBLE", {}, chosen_option="manual")
    _save(store, "D0002", "DEVICE_INCOMPATIBLE", {})

    config = {
        "auto_rules": [{"type": "DEVICE_INCOMPATIBLE", "choice": "skip"}]
    }
    auto, needs = classify_decisions(store, config)
    assert {d["decision_id"] for d in auto} == {"D0002"}
    assert needs == []


def test_generate_decision_review_threads_config(store: MigrationStore) -> None:
    """generate_decision_review takes config and passes it to classify_decisions."""
    _save(store, "D0001", "DEVICE_INCOMPATIBLE", {})

    config = {
        "auto_rules": [
            {"type": "DEVICE_INCOMPATIBLE", "choice": "skip",
             "reason": "Custom reason from test"},
        ]
    }
    md = generate_decision_review(store, "test-project", config)
    assert "## Auto-Apply (1 decisions)" in md
    assert "Custom reason from test" in md
