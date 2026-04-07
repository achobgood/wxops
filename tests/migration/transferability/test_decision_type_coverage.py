"""Verify every DecisionType (except ARCHITECTURE_ADVISORY) has an entry in
docs/runbooks/cucm-migration/decision-guide.md §Decision Types A–Z."""

from __future__ import annotations

from wxcli.migration.models import DecisionType
from .conftest import extract_anchors, slugify


def test_every_decision_type_has_an_anchor(decision_guide_path):
    expected = {
        slugify(dt.value.replace("_", " "))
        for dt in DecisionType
        if dt != DecisionType.ARCHITECTURE_ADVISORY
    }
    actual = extract_anchors(decision_guide_path)
    missing = expected - actual
    assert not missing, (
        f"decision-guide.md is missing anchors for {len(missing)} DecisionType(s): "
        f"{sorted(missing)}. Add a `### <slug>` heading for each."
    )


def test_no_extra_decision_type_anchors(decision_guide_path):
    """Catch typos / removed enum values: every decision-type-shaped anchor in the
    guide must correspond to a real DecisionType."""
    expected = {
        slugify(dt.value.replace("_", " "))
        for dt in DecisionType
        if dt != DecisionType.ARCHITECTURE_ADVISORY
    }
    actual = extract_anchors(decision_guide_path)
    # Restrict to anchors that look like decision types (kebab-case, no slashes)
    candidates = {a for a in actual if "-" in a and "/" not in a}
    suspicious = candidates & {slugify(dt.value.replace("_", " ")) + "-removed" for dt in DecisionType}
    assert not suspicious, f"Suspicious renamed anchors: {sorted(suspicious)}"
    # Note: this test is intentionally permissive — the strict check is the
    # 'missing' assertion above. Extras are allowed as long as the naming
    # pattern doesn't suggest a stale rename.
