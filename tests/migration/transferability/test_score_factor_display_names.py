"""Regression guard: WEIGHTS ↔ DISPLAY_NAMES parity and both name sets
present in operator-runbook.md.

Background: score.py maintains two parallel name sets for its 8 complexity
factors. WEIGHTS uses internal names (e.g. "CSS Complexity"); DISPLAY_NAMES
maps those to customer-facing names (e.g. "Calling Restrictions"). The
operator-runbook §The 8 Score Factors table shows both. A rename in either
dict without updating the runbook silently breaks the table. This file
prevents that regression.

Spec: transferability-phase-3.md §7.
"""

from __future__ import annotations

from wxcli.migration.report.score import DISPLAY_NAMES, WEIGHTS


def test_weights_and_display_names_keys_match():
    """Every WEIGHTS key must appear in DISPLAY_NAMES and vice versa."""
    w_keys = set(WEIGHTS.keys())
    d_keys = set(DISPLAY_NAMES.keys())
    assert w_keys == d_keys, (
        f"WEIGHTS and DISPLAY_NAMES have different keys. "
        f"In WEIGHTS only: {sorted(w_keys - d_keys)}. "
        f"In DISPLAY_NAMES only: {sorted(d_keys - w_keys)}."
    )


def test_internal_factor_names_in_runbook(operator_runbook_path):
    """Every WEIGHTS key must appear as a literal string in operator-runbook.md."""
    text = operator_runbook_path.read_text(encoding="utf-8")
    missing = [k for k in WEIGHTS if k not in text]
    assert not missing, (
        f"operator-runbook.md is missing these internal factor names: {missing}. "
        f"Update the \u00a7The 8 Score Factors table to include both the internal name "
        f"and the display name for each factor."
    )


def test_display_factor_names_in_runbook(operator_runbook_path):
    """Every DISPLAY_NAMES value must appear as a literal string in operator-runbook.md."""
    text = operator_runbook_path.read_text(encoding="utf-8")
    missing = [v for v in DISPLAY_NAMES.values() if v not in text]
    assert not missing, (
        f"operator-runbook.md is missing these display factor names: {missing}. "
        f"Update the \u00a7The 8 Score Factors table to include the display name "
        f"(shown to customers in the report) alongside the internal name."
    )
