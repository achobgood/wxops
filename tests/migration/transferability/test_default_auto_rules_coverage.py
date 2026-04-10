"""Verify every entry in DEFAULT_AUTO_RULES has an explanation anchor in
docs/runbooks/cucm-migration/tuning-reference.md §Auto-Rules."""

from __future__ import annotations

from wxcli.commands.cucm_config import DEFAULT_AUTO_RULES
from .conftest import extract_anchors, slugify


def _rule_anchor(rule: dict) -> str:
    """Build a stable slug from a rule's type + match keys."""
    parts = ["default-rule", rule["type"].lower().replace("_", "-")]
    if "match" in rule:
        # Disambiguate rules that share a type by adding match-key suffixes
        for k, v in sorted(rule["match"].items()):
            parts.append(f"{k.replace('_', '-')}-{v}")
    return slugify(" ".join(parts))


def test_every_default_auto_rule_has_an_anchor(tuning_reference_path):
    expected = {_rule_anchor(r) for r in DEFAULT_AUTO_RULES}
    actual = extract_anchors(tuning_reference_path)
    missing = expected - actual
    assert not missing, (
        f"tuning-reference.md is missing anchors for default auto-rules: {sorted(missing)}. "
        f"Each entry in DEFAULT_AUTO_RULES needs a `### default-rule-<type>...` heading."
    )
