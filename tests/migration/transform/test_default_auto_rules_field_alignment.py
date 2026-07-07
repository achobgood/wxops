"""Parametrized test: every DEFAULT_AUTO_RULES match key must exist in
the producing analyzer's (or enrichment's) decision context.

This is a CI-time guard against the class of bugs where a rule references
a context field that no producer writes — the CALLING_PERMISSION_MISMATCH
silent-skip bug (Bug F) was exactly this shape.

New default rules with a `match` field get covered automatically as soon
as they're added to DEFAULT_AUTO_RULES. If a rule matches on a field no
producer knows about, this test fails at collection time (if the analyzer
cannot be identified) or at assert time (if the synthetic producer output
doesn't contain the key).

KNOWN LIMITATION: this test uses a hand-maintained `_SYNTHETIC_PRODUCERS`
registry that mirrors what each analyzer writes. It catches RULE-side
typos (rule references a field the producer never wrote) but NOT
ANALYZER-side renames (analyzer renames its output field; registry is
out of date; Bug F can recur). A more robust version would import each
real analyzer and run `.analyze()` against a minimal synthetic store,
but that's a non-trivial integration-test surface. Tracked as follow-up
work; do not rely on this test alone to catch field-name drift during
analyzer refactors.
"""

from __future__ import annotations

from typing import Any

import pytest

from wxcli.commands.cucm_config import DEFAULT_AUTO_RULES


def _strip_operator_suffix(key: str) -> str:
    """Strip _lte / _gte / _contains suffixes for field-name alignment."""
    for suffix in ("_lte", "_gte", "_contains"):
        if key.endswith(suffix):
            return key[: -len(suffix)]
    return key


# ---------------------------------------------------------------------------
# Synthetic producers: one factory per (decision_type, key) pair.
#
# Each factory returns a dict that represents what the analyzer / enrichment
# would write into a decision's context. The test asserts every stripped
# match key is present in this dict.
#
# When a new default rule lands with a new (type, key), add a factory here.
# ---------------------------------------------------------------------------


def _css_permission_synthetic_context() -> dict[str, Any]:
    """Mirror what CSSPermissionAnalyzer writes at css_permission.py:128."""
    return {
        "profile_name": "test-profile",
        "assigned_users_count": 0,  # key the default rule matches on
        "assigned_users": [],
    }


def _missing_data_enriched_synthetic_context() -> dict[str, Any]:
    """Mirror what enrich_cross_decision_context() writes into MISSING_DATA
    decisions after analysis_pipeline step 3.5."""
    return {
        "object_type": "device",
        "canonical_id": "phone:001",
        "missing_fields": ["mac"],
        "is_on_incompatible_device": True,  # key the default rule matches on
    }


# Registry: decision_type → synthetic context factory.
# Multiple rules for the same type share one factory.
_SYNTHETIC_PRODUCERS: dict[str, Any] = {
    "CALLING_PERMISSION_MISMATCH": _css_permission_synthetic_context,
    "MISSING_DATA": _missing_data_enriched_synthetic_context,
}


# Rules with a `match` field — parametrize over every one.
_RULES_WITH_MATCH = [
    r for r in DEFAULT_AUTO_RULES if r.get("match")
]


@pytest.mark.parametrize(
    "rule",
    _RULES_WITH_MATCH,
    ids=[f"{r['type']}:{','.join(r.get('match', {}))}" for r in _RULES_WITH_MATCH],
)
def test_default_rule_match_fields_are_produced(rule: dict[str, Any]) -> None:
    """Every match key in a default rule must be writable by a known producer.

    Regression guard for analyzer-rule field-name drift.
    """
    dec_type = rule["type"]
    match = rule.get("match", {})
    assert match, f"Rule for {dec_type} has empty match field"

    producer = _SYNTHETIC_PRODUCERS.get(dec_type)
    assert producer is not None, (
        f"No synthetic producer registered for decision type {dec_type!r}. "
        f"Add one to _SYNTHETIC_PRODUCERS in "
        f"test_default_auto_rules_field_alignment.py that mirrors whatever "
        f"analyzer / enrichment writes the context for this decision type."
    )

    ctx = producer()
    missing_keys = []
    for raw_key in match:
        base_key = _strip_operator_suffix(raw_key)
        if base_key not in ctx:
            missing_keys.append(base_key)

    assert not missing_keys, (
        f"Default auto-rule for {dec_type} matches on context fields "
        f"that the synthetic producer does not write: {missing_keys}. "
        f"Either (a) the rule's match field is wrong, or (b) the producer "
        f"actually writes a different key name, or (c) the synthetic "
        f"producer is out of date with the real producer's code."
    )


def test_every_producer_has_at_least_one_rule() -> None:
    """Sanity: every synthetic producer maps to at least one rule. This
    keeps the registry tight — if a producer is removed, the test that
    needs it will fail loudly instead of silently drifting."""
    rule_types = {r["type"] for r in _RULES_WITH_MATCH}
    orphans = [t for t in _SYNTHETIC_PRODUCERS if t not in rule_types]
    assert not orphans, (
        f"_SYNTHETIC_PRODUCERS has factories for decision types with no "
        f"corresponding default rules: {orphans}. Either add a rule or "
        f"remove the producer."
    )
