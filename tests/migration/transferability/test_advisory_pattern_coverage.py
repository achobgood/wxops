"""Verify every function in ALL_ADVISORY_PATTERNS has an entry in
docs/runbooks/cucm-migration/decision-guide.md §Advisory Patterns."""

from __future__ import annotations

from wxcli.migration.advisory.advisory_patterns import ALL_ADVISORY_PATTERNS
from .conftest import extract_anchors, slugify


def _pattern_name(func) -> str:
    """detect_restriction_css_consolidation -> restriction-css-consolidation"""
    name = func.__name__
    assert name.startswith("detect_"), f"Unexpected pattern function name: {name}"
    return slugify(name[len("detect_"):].replace("_", " "))


def test_every_advisory_pattern_has_an_anchor(decision_guide_path):
    expected = {_pattern_name(f) for f in ALL_ADVISORY_PATTERNS}
    actual = extract_anchors(decision_guide_path)
    missing = expected - actual
    assert not missing, (
        f"decision-guide.md is missing anchors for {len(missing)} advisory pattern(s): "
        f"{sorted(missing)}. Add a `#### <slug>` heading for each."
    )
