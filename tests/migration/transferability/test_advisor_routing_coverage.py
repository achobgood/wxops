"""Verify every advisory pattern_name in ALL_ADVISORY_PATTERNS appears in the
'By advisory pattern_name' table in .claude/agents/migration-advisor.md."""

from __future__ import annotations

import re

from wxcli.migration.advisory.advisory_patterns import ALL_ADVISORY_PATTERNS


def _extract_routing_table_pattern_names(text: str) -> set[str]:
    """Parse the 'By advisory pattern_name' markdown table and return the set
    of pattern names listed in its rows.

    The table looks like:

        **By advisory pattern_name:**
        | Pattern Name | KB Doc |
        |---|---|
        | foo_pattern, bar_pattern | kb-foo.md |
        | baz_pattern              | kb-bar.md |

        **Always load:** `kb-webex-limits.md`

    The first cell of each row holds a comma-separated list of pattern names.
    Returns the union of all pattern names across all rows.
    """
    marker = "By advisory pattern_name"
    if marker not in text:
        return set()

    section_start = text.index(marker)
    after = text[section_start:]

    # Walk lines after the marker. The table starts at the first `|` line and
    # ends at the first non-table line (blank or non-`|`).
    table_row_re = re.compile(r"^\s*\|(.+?)\|(.+?)\|\s*$")
    in_table = False
    pattern_names: set[str] = set()
    for line in after.splitlines():
        m = table_row_re.match(line)
        if m:
            in_table = True
            first_cell = m.group(1).strip()
            # Skip the header row and divider row
            if first_cell.lower().startswith("pattern name"):
                continue
            if set(first_cell) <= set("-: "):
                continue
            # Split comma-separated pattern names in the first cell
            for raw in first_cell.split(","):
                name = raw.strip().strip("`")
                if name:
                    pattern_names.add(name)
        elif in_table:
            # First non-table line after the table — stop scanning
            break

    return pattern_names


def test_advisor_routing_table_lists_all_patterns(advisor_agent_path):
    text = advisor_agent_path.read_text(encoding="utf-8")

    marker = "By advisory pattern_name"
    assert marker in text, "migration-advisor.md missing 'By advisory pattern_name' section"

    table_patterns = _extract_routing_table_pattern_names(text)
    assert table_patterns, (
        "Could not parse any pattern names from the 'By advisory pattern_name' "
        "table in migration-advisor.md. The table format may have changed — "
        "verify it still uses the `| names | kb-doc.md |` row layout."
    )

    expected = {func.__name__[len("detect_"):] for func in ALL_ADVISORY_PATTERNS}
    missing = expected - table_patterns

    assert not missing, (
        f"migration-advisor.md routing table is missing entries for: {sorted(missing)}. "
        f"Add a row to the 'By advisory pattern_name' table for each."
    )
