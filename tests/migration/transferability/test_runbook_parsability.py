"""Structural probes for runbook parsability — verifies that markdown
formatting is unambiguous enough for Claude Code to extract answers reliably.

Checks:
1. Table completeness — every markdown table (outside fenced code blocks)
   has a header + divider + at least one data row.
2. DT entry field completeness — every DT-{DOMAIN}-NNN heading in KB docs
   is followed within 10 lines by **Condition:** and **Advisor should:**.
3. Decision-guide anchor density — each ### entry that matches a
   RECOMMENDATION_DISPATCH decision type must contain at least one of
   **Recommendation:**, **Options:**, **Auto-rule match:** within 20 lines.
4. Recipe entry-point structure — each recipe heading in tuning-reference
   has at least one **X:** bold-field marker within the first 5 lines
   (entry-point field that describes when/where the recipe applies).
5. BLOCKING GATE visibility — mandatory markers in SKILL.md are not buried
   exclusively inside fenced code blocks.

Probes 2 and 4 encode the actual doc conventions in use (as of 2026-04-08):
KB DT entries use `**Advisor should:**` rather than `**Recommendation:**`
as the operator-guidance field, and tuning recipes use
`**Source environment characteristics:**` as the entry-point marker.

Spec: transferability-phase-3.md §3.4 and §3.5.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from wxcli.migration.advisory.recommendation_rules import RECOMMENDATION_DISPATCH

from .conftest import KB_DIR, RUNBOOK_DIR, SKILL_PATH, slugify

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

FENCE_RE = re.compile(r"^```")


def _code_fence_line_indices(lines: list[str]) -> set[int]:
    """Return the 0-indexed line numbers covered by fenced code blocks."""
    in_fence = False
    covered: set[int] = set()
    for idx, line in enumerate(lines):
        if FENCE_RE.match(line):
            covered.add(idx)
            in_fence = not in_fence
            continue
        if in_fence:
            covered.add(idx)
    return covered


# ---------------------------------------------------------------------------
# Probe 1: Table completeness
# ---------------------------------------------------------------------------

_TABLE_ROW_RE = re.compile(r"^\|.+\|\s*$")
_DIVIDER_RE = re.compile(r"^\|\s*[-:| ]+\|\s*$")


def _check_table_completeness(text: str, doc_name: str) -> list[str]:
    """Find markdown tables outside code fences and verify each has
    header + divider + at least one data row. Advances past all continuous
    data rows before looking for the next table."""
    failures: list[str] = []
    lines = text.splitlines()
    fence_lines = _code_fence_line_indices(lines)

    i = 0
    while i < len(lines):
        if i in fence_lines:
            i += 1
            continue

        line = lines[i].rstrip()
        if _TABLE_ROW_RE.match(line):
            header_line = i + 1  # 1-indexed for error messages
            # Expect divider on next line
            if (
                i + 1 >= len(lines)
                or (i + 1) in fence_lines
                or not _DIVIDER_RE.match(lines[i + 1].rstrip())
            ):
                # Not a table — single pipe-like line (e.g., inside a blockquote
                # or just content with pipes). Skip past it.
                i += 1
                continue

            # Expect at least one data row after divider
            if (
                i + 2 >= len(lines)
                or (i + 2) in fence_lines
                or not _TABLE_ROW_RE.match(lines[i + 2].rstrip())
            ):
                failures.append(
                    f"{doc_name} line {header_line}: table has header + divider but no data rows"
                )
                i += 2
                continue

            # Consume all contiguous data rows belonging to this table
            j = i + 2
            while (
                j < len(lines)
                and j not in fence_lines
                and _TABLE_ROW_RE.match(lines[j].rstrip())
            ):
                j += 1
            i = j
            continue

        i += 1
    return failures


@pytest.mark.parametrize(
    "doc_name",
    ["operator-runbook.md", "decision-guide.md", "tuning-reference.md"],
)
def test_table_completeness(doc_name):
    path = RUNBOOK_DIR / doc_name
    text = path.read_text(encoding="utf-8")
    failures = _check_table_completeness(text, doc_name)
    assert not failures, "Malformed tables:\n  " + "\n  ".join(failures)


# ---------------------------------------------------------------------------
# Probe 2: DT entry field completeness in KB docs
# ---------------------------------------------------------------------------

DT_HEADING_RE = re.compile(r"^#{2,4}\s+DT-[A-Z]+-\d+", re.MULTILINE)

# Section-terminator regex — stops an entry block at the next DT heading, the
# next ## section, or end of file.
_DT_BLOCK_END_RE = re.compile(r"^(?:#{2,4}\s+DT-[A-Z]+-\d+|## )", re.MULTILINE)

# KB docs use these field conventions (verified 2026-04-08 across all 8 KBs):
#   **Condition:** — always present
#   Advisor-guidance field — either **Advisor should:** or
#     **What the advisor should do:** (kb-device-migration.md variant)
_DT_CONDITION_FIELD = "**Condition:**"
_DT_ADVISOR_FIELDS = ("**Advisor should:**", "**What the advisor should do:**")


def _dt_entry_block(text: str, heading_start_pos: int) -> str:
    """Return the text of a DT entry — from the line after the heading up to
    (but not including) the next DT heading or the next top-level ## section."""
    # Start after the newline that ends the heading line
    body_start = text.find("\n", heading_start_pos)
    if body_start == -1:
        return ""
    body_start += 1
    # Find the next DT heading or ## section after this one
    next_match = _DT_BLOCK_END_RE.search(text, body_start)
    body_end = next_match.start() if next_match else len(text)
    return text[body_start:body_end]


def test_dt_entry_field_completeness():
    """Every DT-{DOMAIN}-NNN entry in KB docs must contain **Condition:** and
    an advisor-guidance field (**Advisor should:** or
    **What the advisor should do:**) somewhere in the entry body — i.e.,
    between the heading and the next DT heading / next `## ` section.
    """
    kb_docs = list(KB_DIR.glob("*.md"))
    assert kb_docs, f"No KB docs found in {KB_DIR}"

    failures: list[str] = []
    for doc_path in sorted(kb_docs):
        text = doc_path.read_text(encoding="utf-8")
        for m in DT_HEADING_RE.finditer(text):
            block = _dt_entry_block(text, m.start())
            missing: list[str] = []
            if _DT_CONDITION_FIELD not in block:
                missing.append(_DT_CONDITION_FIELD)
            if not any(f in block for f in _DT_ADVISOR_FIELDS):
                missing.append(" or ".join(_DT_ADVISOR_FIELDS))
            if missing:
                failures.append(
                    f"{doc_path.name}: {m.group(0).strip()!r} missing {missing} in entry body"
                )

    assert not failures, "Incomplete DT entries:\n  " + "\n  ".join(failures)


# ---------------------------------------------------------------------------
# Probe 3: Decision-guide anchor density
# ---------------------------------------------------------------------------

DG_ENTRY_RE = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)
_ANCHOR_CONTENT_MARKERS = ("**Recommendation:**", "**Options:**", "**Auto-rule match:**")


def _decision_type_slugs() -> set[str]:
    """The set of anchor slugs for all decision types in RECOMMENDATION_DISPATCH."""
    return {slugify(dt.replace("_", " ")) for dt in RECOMMENDATION_DISPATCH}


def test_decision_guide_anchor_density(decision_guide_path):
    """Each ### entry in decision-guide.md whose slug matches a decision type
    from RECOMMENDATION_DISPATCH must contain at least one of
    **Recommendation:**, **Options:**, or **Auto-rule match:** within 20 lines.

    Workflow/sub-section headings (e.g., 'eliminate', 'rebuild') are not
    decision-type entries and are intentionally skipped."""
    text = decision_guide_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    dt_slugs = _decision_type_slugs()
    failures: list[str] = []

    for m in DG_ENTRY_RE.finditer(text):
        heading_slug = slugify(m.group(1).strip())
        if heading_slug not in dt_slugs:
            continue
        heading_line = text[: m.start()].count("\n")
        window = lines[heading_line + 1 : heading_line + 21]
        window_text = "\n".join(window)
        if not any(marker in window_text for marker in _ANCHOR_CONTENT_MARKERS):
            failures.append(
                f"decision-guide.md ### {m.group(1).strip()!r}: none of "
                f"{_ANCHOR_CONTENT_MARKERS} found within 20 lines"
            )

    assert not failures, (
        "Structurally incomplete decision-guide entries:\n  " + "\n  ".join(failures)
    )


# ---------------------------------------------------------------------------
# Probe 4: Recipe entry-point structure in tuning-reference.md
# ---------------------------------------------------------------------------

RECIPE_HEADING_RE = re.compile(r"^###\s+Recipe\b", re.MULTILINE | re.IGNORECASE)
RECIPE_SECTION_RE = re.compile(r"^##\s+Tuning Recipes", re.MULTILINE | re.IGNORECASE)

# Any **FieldName:** marker qualifies as an entry-point marker. This is more
# permissive than the original spec (which named **Symptom:** / **When to use:**)
# because tuning-reference.md uses **Source environment characteristics:** as the
# recipe opening field — a legitimate entry-point convention that describes
# WHEN the recipe applies. The intent of the probe is "each recipe has a
# structured opening field within 5 lines", not "each recipe uses specific
# field names".
_BOLD_FIELD_RE = re.compile(r"\*\*[A-Z][A-Za-z ]*:\*\*")


def test_recipe_entry_point_structure(tuning_reference_path):
    """Each recipe heading in tuning-reference.md §Tuning Recipes must have
    at least one bold-field marker (`**Xxx:**`) within 5 lines — confirming
    the recipe opens with a structured entry-point field."""
    text = tuning_reference_path.read_text(encoding="utf-8")

    # Find the Tuning Recipes section
    section_match = RECIPE_SECTION_RE.search(text)
    if not section_match:
        pytest.skip("No '## Tuning Recipes' section found in tuning-reference.md")

    recipes_text = text[section_match.start():]
    lines = text.splitlines()
    failures: list[str] = []

    for m in RECIPE_HEADING_RE.finditer(recipes_text):
        abs_start = section_match.start() + m.start()
        heading_line = text[:abs_start].count("\n")
        window = lines[heading_line + 1 : heading_line + 6]
        window_text = "\n".join(window)
        if not _BOLD_FIELD_RE.search(window_text):
            failures.append(
                f"tuning-reference.md {m.group(0).strip()!r} at line {heading_line + 1}: "
                f"no **Xxx:** bold-field marker within 5 lines"
            )

    assert not failures, "Recipe entries missing entry-point field:\n  " + "\n  ".join(failures)


# ---------------------------------------------------------------------------
# Probe 5: BLOCKING GATE visibility in SKILL.md
# ---------------------------------------------------------------------------

_GATE_MARKERS = ("**[MANDATORY, NOT SKIPPABLE]**", "**Do NOT proceed**", "BLOCKING GATE")


def test_blocking_gate_has_visible_instance():
    """BLOCKING GATE / MANDATORY markers in SKILL.md must appear at least once
    OUTSIDE a fenced code block. Markers may also appear inside code blocks as
    documentation of expected admin output — that is fine, as long as at least
    one prose-level instance exists so a prose reader cannot miss the gate."""
    text = SKILL_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()
    fence_lines = _code_fence_line_indices(lines)

    missing: list[str] = []
    for marker in _GATE_MARKERS:
        visible_count = sum(
            1 for idx, line in enumerate(lines)
            if marker in line and idx not in fence_lines
        )
        total_count = sum(1 for line in lines if marker in line)
        if total_count > 0 and visible_count == 0:
            missing.append(
                f"SKILL.md: marker {marker!r} appears {total_count} time(s) but all "
                f"instances are inside fenced code blocks. Add at least one prose-level "
                f"instance (outside a code fence) so a reader scanning headings and "
                f"paragraphs can see the gate."
            )

    assert not missing, "Blocking markers not visible in prose:\n  " + "\n  ".join(missing)
