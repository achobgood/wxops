"""Inverse coverage check: for every recommend_* function in
recommendation_rules.py, the corresponding ### <decision-type> entry in
decision-guide.md must contain a **Recommendation:** field.

The existing test_decision_type_coverage.py checks that every DecisionType
has an anchor. This file checks that the anchor is populated with the
recommendation output — not just that it exists.

Spec: transferability-phase-3.md §3.6.
"""

from __future__ import annotations

import re

from wxcli.migration.advisory.recommendation_rules import RECOMMENDATION_DISPATCH

from .conftest import slugify


def _find_recommendation_field_near_anchor(
    text: str, anchor_slug: str, window: int = 20
) -> bool:
    """Return True if **Recommendation:** appears within `window` lines after
    the heading whose slug matches `anchor_slug`."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^#{2,4}\s+(.+?)\s*$", line)
        if m and slugify(m.group(1)) == anchor_slug:
            chunk = "\n".join(lines[i + 1 : i + 1 + window])
            if "**Recommendation:**" in chunk:
                return True
    return False


def test_every_recommend_function_has_recommendation_field_in_guide(decision_guide_path):
    """Every DecisionType key in RECOMMENDATION_DISPATCH must have a
    **Recommendation:** field in its decision-guide.md entry."""
    text = decision_guide_path.read_text(encoding="utf-8")
    failures: list[str] = []

    for dt_str in RECOMMENDATION_DISPATCH:
        # Convert "CSS_ROUTING_MISMATCH" → slug "css-routing-mismatch"
        anchor = slugify(dt_str.replace("_", " "))
        if not _find_recommendation_field_near_anchor(text, anchor):
            failures.append(
                f"decision-guide.md ### {dt_str.lower().replace('_', '-')!r}: "
                f"missing **Recommendation:** field within 20 lines. "
                f"Add the recommendation summary so Claude Code can look it up without "
                f"reading recommendation_rules.py."
            )

    assert not failures, (
        f"{len(failures)} decision-guide entries missing **Recommendation:** field:\n  "
        + "\n  ".join(failures)
    )
