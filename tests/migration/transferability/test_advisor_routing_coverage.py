"""Verify every advisory pattern_name in ALL_ADVISORY_PATTERNS appears in the
'By advisory pattern_name' table in .claude/agents/migration-advisor.md."""

from __future__ import annotations

from wxcli.migration.advisory.advisory_patterns import ALL_ADVISORY_PATTERNS


def test_advisor_routing_table_lists_all_patterns(advisor_agent_path):
    text = advisor_agent_path.read_text(encoding="utf-8")

    # Locate the routing table — search between the section header and the next H2/H3
    marker = "By advisory pattern_name"
    assert marker in text, "migration-advisor.md missing 'By advisory pattern_name' section"

    section_start = text.index(marker)
    # Routing table ends at the next blank-line + non-table line. Easier: just
    # check that every pattern_name appears somewhere AFTER the marker.
    after = text[section_start:]

    missing = []
    for func in ALL_ADVISORY_PATTERNS:
        name = func.__name__[len("detect_"):]  # restriction_css_consolidation
        if name not in after:
            missing.append(name)

    assert not missing, (
        f"migration-advisor.md routing table is missing entries for: {missing}. "
        f"Add a row to the 'By advisory pattern_name' table for each."
    )
