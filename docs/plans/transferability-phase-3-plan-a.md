# Layer 3 Plan A: CI Gate + Pytest Extensions

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a path-filtered GitHub Actions CI gate and three new pytest files that prevent silent drift between `score.py`, `recommendation_rules.py`, `migration-advisor.md`, and the three operator runbooks — plus five small doc fixes identified in the Layer 3 spec's §9 findings.

**Architecture:** All 9 deliverables are pure text-parsing tests and YAML/markdown edits. No new source modules, no new fixtures beyond what conftest.py already provides. The three new test files sit alongside the existing 7 in `tests/migration/transferability/` and import only from `wxcli.migration.report.score`, `wxcli.migration.advisory.recommendation_rules`, and the runbook `.md` files. The CI workflow is a standalone `transferability.yml` that path-filters on 8 drift-sensitive file patterns and blocks merge on failure.

**Tech Stack:** Python 3.11, pytest, GitHub Actions (actions/checkout@v4, actions/setup-python@v5), pathlib (stdlib), re (stdlib)

---

## File Map

**New files:**
- Create: `tests/migration/transferability/test_score_factor_display_names.py`
- Create: `tests/migration/transferability/test_runbook_parsability.py`
- Create: `tests/migration/transferability/test_recommendation_output_coverage.py`
- Create: `.github/workflows/transferability.yml`

**Modified files:**
- Modify: `src/wxcli/migration/advisory/CLAUDE.md` — fix "20" → "26" in file map table line 42
- Modify: `docs/runbooks/cucm-migration/self-review-findings.md` — update Finding 5 disposition from "Deferred" to "Fixed"
- Modify: `docs/runbooks/cucm-migration/operator-runbook.md` — two edits: AXL credential clarification in §Assumed environment + slash-command marker on Step 11
- Modify: `tests/migration/transferability/test_advisor_routing_coverage.py` — add one assertion for "Always load" marker

**Unchanged:**
- `tests/migration/transferability/conftest.py` — already provides `operator_runbook_path`, `decision_guide_path`, `tuning_reference_path`, `advisor_agent_path`. Do not touch.

---

## Task 1: test_score_factor_display_names.py

**Files:**
- Create: `tests/migration/transferability/test_score_factor_display_names.py`

The test imports `WEIGHTS` and `DISPLAY_NAMES` directly from `wxcli.migration.report.score` (which already resolves correctly given the `pip install -e .` project setup) and reads `operator-runbook.md` via the `operator_runbook_path` fixture from `conftest.py`. Three assertions: key parity between dicts, internal names in runbook, display names in runbook.

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run it to verify it fails**

```bash
cd /Users/ahobgood/Documents/webexCalling
pytest tests/migration/transferability/test_score_factor_display_names.py -v --tb=short
```

Expected: The first test (`test_weights_and_display_names_keys_match`) likely passes immediately since the dicts are already in sync. The second and third tests may pass or fail depending on whether the operator-runbook §The 8 Score Factors table already contains all 8 internal names and 8 display names. If all three pass, note it in the commit message — the test is a regression guard even if the current state is clean.

- [ ] **Step 3: Commit**

```bash
git add tests/migration/transferability/test_score_factor_display_names.py
git commit -m "test(transferability): score factor display-name parity regression guard"
```

---

## Task 2: test_runbook_parsability.py

**Files:**
- Create: `tests/migration/transferability/test_runbook_parsability.py`

This file runs structural probes on the three runbooks and SKILL.md. Five probes (spec §3.4 and §3.5):
1. Table completeness in all three runbooks
2. DT entry field completeness (`**Condition:**` and `**Recommendation:**`) in all 8 KB docs
3. Anchor density in `decision-guide.md` (each `### X` entry must have at least one of `**Recommendation:**`, `**Options:**`, `**Auto-rule match:**` within 20 lines)
4. Recipe entry-point structure in `tuning-reference.md` (each recipe heading must have `**Symptom:**` or `**When to use:**` within 5 lines)
5. BLOCKING GATE visibility in SKILL.md (each `**[MANDATORY, NOT SKIPPABLE]**` or `**Do NOT proceed**` marker must not be buried inside a fenced code block)

The conftest.py `RUNBOOK_DIR` and `SKILL_PATH` constants are used directly — no new fixtures needed.

- [ ] **Step 1: Write the failing test**

```python
"""Structural probes for runbook parsability — verifies that markdown
formatting is unambiguous enough for Claude Code to extract answers reliably.

Checks:
1. Table completeness — header + divider + at least one data row, no
   merged cells (a `|` inside a cell value without a closing `|`).
2. DT entry field completeness — every DT-{DOMAIN}-NNN heading in KB docs
   is followed by **Condition:** and **Recommendation:** within 5 lines.
3. Decision-guide anchor density — each ### entry has at least one of
   **Recommendation:**, **Options:**, **Auto-rule match:** within 20 lines.
4. Recipe entry-point structure — each recipe heading in tuning-reference
   has **Symptom:** or **When to use:** within 5 lines.
5. BLOCKING GATE visibility — mandatory markers in SKILL.md are not inside
   fenced code blocks.

Spec: transferability-phase-3.md §3.4 and §3.5.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from .conftest import KB_DIR, RUNBOOK_DIR, SKILL_PATH

# ---------------------------------------------------------------------------
# Probe 1: Table completeness
# ---------------------------------------------------------------------------

TABLE_HEADER_RE = re.compile(r"^\|.+\|$", re.MULTILINE)
DIVIDER_RE = re.compile(r"^\|\s*[-:]+[-| :]*\|$", re.MULTILINE)


def _check_table_completeness(text: str, doc_name: str) -> list[str]:
    """Return a list of failure messages for malformed markdown tables."""
    failures: list[str] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        # Detect a table header row (starts and ends with |)
        if re.match(r"^\|.+\|$", line.strip()):
            header_line = i + 1  # 1-indexed for error messages
            # Expect a divider on the next line
            if i + 1 >= len(lines) or not re.match(r"^\|\s*[-:| ]+\|$", lines[i + 1].strip()):
                failures.append(
                    f"{doc_name} line {header_line}: table header not followed by divider row"
                )
                i += 1
                continue
            # Expect at least one data row
            if i + 2 >= len(lines) or not re.match(r"^\|.+\|$", lines[i + 2].strip()):
                failures.append(
                    f"{doc_name} line {header_line}: table has header + divider but no data rows"
                )
            i += 3
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


def test_dt_entry_field_completeness():
    """Every DT-{DOMAIN}-NNN heading in KB docs must be followed within 5 lines
    by **Condition:** and **Recommendation:**."""
    kb_docs = list(KB_DIR.glob("*.md"))
    assert kb_docs, f"No KB docs found in {KB_DIR}"

    failures: list[str] = []
    for doc_path in sorted(kb_docs):
        text = doc_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        for m in DT_HEADING_RE.finditer(text):
            # Find the line number of the heading
            heading_start = text[: m.start()].count("\n")
            window = lines[heading_start + 1 : heading_start + 6]
            window_text = "\n".join(window)
            has_condition = "**Condition:**" in window_text
            has_recommendation = "**Recommendation:**" in window_text
            if not has_condition or not has_recommendation:
                missing = []
                if not has_condition:
                    missing.append("**Condition:**")
                if not has_recommendation:
                    missing.append("**Recommendation:**")
                failures.append(
                    f"{doc_path.name}: {m.group(0).strip()!r} missing {missing} within 5 lines"
                )

    assert not failures, "Incomplete DT entries:\n  " + "\n  ".join(failures)


# ---------------------------------------------------------------------------
# Probe 3: Decision-guide anchor density
# ---------------------------------------------------------------------------

DG_ENTRY_RE = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)
_ANCHOR_CONTENT_MARKERS = ("**Recommendation:**", "**Options:**", "**Auto-rule match:**")


def test_decision_guide_anchor_density(decision_guide_path):
    """Each ### entry in decision-guide.md must contain at least one of
    **Recommendation:**, **Options:**, or **Auto-rule match:** within 20 lines."""
    text = decision_guide_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    failures: list[str] = []

    for m in DG_ENTRY_RE.finditer(text):
        heading_line = text[: m.start()].count("\n")
        window = lines[heading_line + 1 : heading_line + 21]
        window_text = "\n".join(window)
        if not any(marker in window_text for marker in _ANCHOR_CONTENT_MARKERS):
            failures.append(
                f"decision-guide.md ### {m.group(1).strip()!r}: none of "
                f"{_ANCHOR_CONTENT_MARKERS} found within 20 lines"
            )

    assert not failures, "Structurally incomplete decision-guide entries:\n  " + "\n  ".join(failures)


# ---------------------------------------------------------------------------
# Probe 4: Recipe entry-point structure in tuning-reference.md
# ---------------------------------------------------------------------------

RECIPE_HEADING_RE = re.compile(r"^###\s+Recipe\b", re.MULTILINE | re.IGNORECASE)
RECIPE_SECTION_RE = re.compile(r"^##\s+Tuning Recipes", re.MULTILINE | re.IGNORECASE)
_RECIPE_ENTRY_MARKERS = ("**Symptom:**", "**When to use:**")


def test_recipe_entry_point_structure(tuning_reference_path):
    """Each recipe heading in tuning-reference.md §Tuning Recipes must have
    **Symptom:** or **When to use:** within 5 lines."""
    text = tuning_reference_path.read_text(encoding="utf-8")

    # Find the Tuning Recipes section
    section_match = RECIPE_SECTION_RE.search(text)
    if not section_match:
        pytest.skip("No '## Tuning Recipes' section found in tuning-reference.md")

    recipes_text = text[section_match.start():]
    lines = text.splitlines()
    failures: list[str] = []

    for m in RECIPE_HEADING_RE.finditer(recipes_text):
        # Absolute position in full text
        abs_start = section_match.start() + m.start()
        heading_line = text[:abs_start].count("\n")
        window = lines[heading_line + 1 : heading_line + 6]
        window_text = "\n".join(window)
        if not any(marker in window_text for marker in _RECIPE_ENTRY_MARKERS):
            failures.append(
                f"tuning-reference.md {m.group(0).strip()!r} at line {heading_line + 1}: "
                f"missing {_RECIPE_ENTRY_MARKERS} within 5 lines"
            )

    assert not failures, "Recipe entries missing entry-point field:\n  " + "\n  ".join(failures)


# ---------------------------------------------------------------------------
# Probe 5: BLOCKING GATE visibility in SKILL.md
# ---------------------------------------------------------------------------

_GATE_MARKERS = ("**[MANDATORY, NOT SKIPPABLE]**", "**Do NOT proceed**", "BLOCKING GATE")
FENCED_BLOCK_RE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)


def test_blocking_gate_has_visible_instance():
    """BLOCKING GATE / MANDATORY markers in SKILL.md must appear at least once
    OUTSIDE a fenced code block. Markers may also appear inside code blocks as
    documentation of expected admin output — that is fine, as long as at least
    one prose-level instance exists so a prose reader cannot miss the gate."""
    text = SKILL_PATH.read_text(encoding="utf-8")

    # Collect line ranges covered by fenced code blocks
    code_block_line_ranges: set[int] = set()
    for m in FENCED_BLOCK_RE.finditer(text):
        start_line = text[: m.start()].count("\n")
        end_line = text[: m.end()].count("\n")
        code_block_line_ranges.update(range(start_line, end_line + 1))

    lines = text.splitlines()
    # For each marker, count how many instances appear OUTSIDE code blocks.
    missing: list[str] = []
    for marker in _GATE_MARKERS:
        visible_count = sum(
            1 for line_idx, line in enumerate(lines)
            if marker in line and line_idx not in code_block_line_ranges
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
```

- [ ] **Step 2: Run it to verify it fails (or passes cleanly)**

```bash
cd /Users/ahobgood/Documents/webexCalling
pytest tests/migration/transferability/test_runbook_parsability.py -v --tb=short
```

Expected: Most probes will pass on the current state of the runbooks. If any fail, the failure message will name the specific heading or table. Do not fix failures here — they are Layer 2 findings to fix in Task 5. Note any failures in the commit message.

- [ ] **Step 3: Commit**

```bash
git add tests/migration/transferability/test_runbook_parsability.py
git commit -m "test(transferability): structural parsability probes for runbooks and SKILL.md"
```

---

## Task 3: test_recommendation_output_coverage.py

**Files:**
- Create: `tests/migration/transferability/test_recommendation_output_coverage.py`

For every `recommend_*` function in `recommendation_rules.py`, the corresponding `### <decision-type>` entry in `decision-guide.md` must contain a `**Recommendation:**` field. The 20 functions in `RECOMMENDATION_DISPATCH` map to 20 DecisionType string keys. The test converts each key to its expected decision-guide slug (`CSS_ROUTING_MISMATCH` → `css-routing-mismatch`) and checks for `**Recommendation:**` within 20 lines of that anchor.

The `conftest.slugify` function handles the slug conversion (it lowercases, replaces spaces with hyphens, drops non-alphanum). DecisionType values use underscores, so the test replaces `_` with ` ` before passing to `slugify`, matching the pattern in `test_decision_type_coverage.py`.

- [ ] **Step 1: Write the failing test**

```python
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

from .conftest import extract_anchors, slugify

# Heading pattern that matches any level 2-4 heading
HEADING_RE = re.compile(r"^#{2,4}\s+(.+?)\s*$", re.MULTILINE)


def _find_recommendation_field_near_anchor(
    text: str, anchor_slug: str, window: int = 20
) -> bool:
    """Return True if **Recommendation:** appears within `window` lines after
    the heading whose slug matches `anchor_slug`."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        # Check if this line is a heading whose slug matches
        m = re.match(r"^#{2,4}\s+(.+?)\s*$", line)
        if m and slugify(m.group(1)) == anchor_slug:
            # Scan the next `window` lines for **Recommendation:**
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
```

- [ ] **Step 2: Run it to verify it fails**

```bash
cd /Users/ahobgood/Documents/webexCalling
pytest tests/migration/transferability/test_recommendation_output_coverage.py -v --tb=short
```

Expected: This test may fail for several DecisionType entries that lack `**Recommendation:**` in their decision-guide entry. That is expected — it surfaces the Layer 2 finding described in spec §9 Finding L3-5. Do not fix the decision-guide entries in this task — note which entries fail in the commit message so they can be fixed in a follow-up.

If the test passes cleanly, the decision-guide is already fully populated. Note that in the commit message.

- [ ] **Step 3: Commit**

```bash
git add tests/migration/transferability/test_recommendation_output_coverage.py
git commit -m "test(transferability): recommendation output coverage — every recommend_* function must populate decision-guide entry"
```

---

## Task 4: .github/workflows/transferability.yml

**Files:**
- Create: `.github/workflows/transferability.yml`

This is a standalone path-filtered workflow that triggers only on PRs to `main` that touch any of the 8 drift-sensitive file patterns. It does not fire on push to main (the existing `ci.yml` already covers that). Uses Python 3.11 only — no matrix.

- [ ] **Step 1: Write the workflow file**

```yaml
name: Transferability Gate

on:
  pull_request:
    branches: [main]
    paths:
      - 'src/wxcli/migration/advisory/advisory_patterns.py'
      - 'src/wxcli/migration/advisory/recommendation_rules.py'
      - 'src/wxcli/commands/cucm_config.py'
      - 'src/wxcli/migration/report/score.py'
      - 'src/wxcli/migration/models.py'
      - 'docs/runbooks/cucm-migration/**'
      - '.claude/skills/cucm-migrate/SKILL.md'
      - '.claude/agents/migration-advisor.md'

jobs:
  transferability:
    name: Transferability coverage gate
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e .
          pip install pytest

      - name: Run transferability tests
        run: |
          pytest tests/migration/transferability/ -v --tb=short
        # Failure message: "This PR touches drift-sensitive files.
        # tests/migration/transferability/ gates the runbook <-> code
        # invariants. Fix the broken test before merging."
```

- [ ] **Step 2: Verify the file is syntactically valid YAML**

```bash
cd /Users/ahobgood/Documents/webexCalling
python3.11 -c "import yaml; yaml.safe_load(open('.github/workflows/transferability.yml'))" && echo "YAML valid"
```

Expected: `YAML valid`

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/transferability.yml
git commit -m "ci(transferability): path-filtered gate for runbook/code drift on PRs"
```

---

## Task 5: Doc fixes (5 sub-steps)

All five fixes are trivial edits. Each sub-step shows the exact old text to replace and the exact new text. Commit after all five are applied.

**Files:**
- Modify: `src/wxcli/migration/advisory/CLAUDE.md`
- Modify: `docs/runbooks/cucm-migration/self-review-findings.md`
- Modify: `docs/runbooks/cucm-migration/operator-runbook.md` (two edits)
- Modify: `tests/migration/transferability/test_advisor_routing_coverage.py`

### 5a: Fix advisory/CLAUDE.md pattern count

Read the file first, then apply the edit.

- [ ] **Step 1: Read the target file**

```bash
cd /Users/ahobgood/Documents/webexCalling
grep -n "20 cross-cutting pattern detectors" src/wxcli/migration/advisory/CLAUDE.md
```

Expected output: `42: | advisory_patterns.py | 20 cross-cutting pattern detectors ...`

- [ ] **Step 2: Apply the edit**

In `src/wxcli/migration/advisory/CLAUDE.md`, find the file map table row (line ~42):

Old text:
```
| `advisory_patterns.py` | 20 cross-cutting pattern detectors + `AdvisoryFinding` dataclass + `ALL_ADVISORY_PATTERNS` list |
```

New text:
```
| `advisory_patterns.py` | 26 cross-cutting pattern detectors + `AdvisoryFinding` dataclass + `ALL_ADVISORY_PATTERNS` list |
```

Use the Edit tool to apply this change.

- [ ] **Step 3: Verify**

```bash
grep "cross-cutting pattern detectors" /Users/ahobgood/Documents/webexCalling/src/wxcli/migration/advisory/CLAUDE.md
```

Expected: line contains "26 cross-cutting pattern detectors"

---

### 5b: Fix self-review-findings.md Finding 5 disposition

- [ ] **Step 1: Read the target section**

```bash
grep -n "Deferred" /Users/ahobgood/Documents/webexCalling/docs/runbooks/cucm-migration/self-review-findings.md | head -10
```

Identify the line where Finding 5's disposition says "Deferred".

- [ ] **Step 2: Apply the edit**

In `docs/runbooks/cucm-migration/self-review-findings.md`, locate the Finding 5 disposition block. It will contain text like:

Old text (the exact disposition line — may be phrased as):
```
**Disposition:** Deferred — drift outside Phase 2 scope. Phase 2 self-walkthrough caught the drift manually; the test enhancement is a Layer 3 improvement.
```

New text:
```
**Disposition:** Fixed in post-G8 cleanup commit — see §Code Review Pass §Observation 3. The `FILE_LINE_RE` pattern was extended to match `.md` citations in the cleanup pass. No further action needed.
```

Use the Edit tool to apply this change.

- [ ] **Step 3: Verify**

```bash
grep -n "Finding 5" /Users/ahobgood/Documents/webexCalling/docs/runbooks/cucm-migration/self-review-findings.md
```

Confirm the Finding 5 section no longer says "Deferred".

---

### 5c: Add AXL credential clarification to operator-runbook.md §Assumed environment

- [ ] **Step 1: Capture the exact anchor text**

```bash
grep -n "Assumed environment\|AXL\|wxcli configure" /Users/ahobgood/Documents/webexCalling/docs/runbooks/cucm-migration/operator-runbook.md | head -20
```

Then use the Read tool to read the 6 lines immediately following the §Assumed environment heading. Copy the last full paragraph or bullet in that block — this is the `old_string` anchor for the Edit call. Record it verbatim before proceeding.

- [ ] **Step 2: Apply the edit**

Use the Edit tool with:
- `old_string` = the exact last paragraph/bullet you recorded in Step 1 (unchanged)
- `new_string` = the same text followed by a blank line and the new Note blockquote:

```
<<<the exact last paragraph or bullet from Step 1, unchanged>>>

> **Note:** AXL credentials are separate from the Webex OAuth token — they are passed inline to `wxcli cucm discover` (or via the `WXCLI_CUCM_*` env vars). `wxcli configure` only handles the Webex OAuth flow.
```

This anchors the append to a known unique location. If the anchor text is not unique in the file (Edit rejects ambiguous matches), extend the anchor backwards by one more paragraph until it becomes unique.

- [ ] **Step 3: Verify**

```bash
grep -n "AXL credentials are separate" /Users/ahobgood/Documents/webexCalling/docs/runbooks/cucm-migration/operator-runbook.md
```

Expected: line found

---

### 5d: Add slash-command marker to operator-runbook.md §Quick Start Step 11

- [ ] **Step 1: Capture the exact anchor — the /cucm-migrate reference is NOT unique**

`grep -n "cucm-migrate" docs/runbooks/cucm-migration/operator-runbook.md` will return multiple hits. Only the §Quick Start Step 11 hit should be edited. Use the Read tool to read 6 lines of context around each hit. The Quick Start Step 11 hit is the one inside a numbered list in §Quick Start (typically near the top of the file) — not inside §Execution & Recovery or §Pipeline Walkthrough.

Capture the 3 lines of context (line above, the `/cucm-migrate` line itself, line below) as your Edit `old_string`. This makes the anchor unique in the file.

- [ ] **Step 2: Apply the edit**

Use the Edit tool with:
- `old_string` = the exact 3-line context block from Step 1 (numbered list item with `/cucm-migrate <project>`)
- `new_string` = the same 3-line block with the marker appended inline after the command, e.g.:

```
11. Execute via the cucm-migrate skill — `/cucm-migrate <project>` _(Claude Code skill invocation — invoke in the session, not in bash)_
```

Preserve the lines above and below the edit line exactly. If Edit rejects the match as ambiguous, extend the context by one more line until the anchor is unique.

- [ ] **Step 3: Verify**

```bash
grep -n "Claude Code skill invocation" /Users/ahobgood/Documents/webexCalling/docs/runbooks/cucm-migration/operator-runbook.md
```

Expected: line found

---

### 5e: Add "Always load" assertion to test_advisor_routing_coverage.py

- [ ] **Step 1: Read the existing file**

Read `tests/migration/transferability/test_advisor_routing_coverage.py` in full. (Already done above — the file has one test function `test_advisor_routing_table_lists_all_patterns`.)

- [ ] **Step 2: Apply the edit**

Append a second test function to `tests/migration/transferability/test_advisor_routing_coverage.py`. Add it after the last line of the existing test function:

```python


def test_advisor_always_load_kb_webex_limits(advisor_agent_path):
    """migration-advisor.md must contain the 'Always load: kb-webex-limits.md'
    instruction. This file is loaded on every advisory run regardless of pattern
    matches. If it were deleted, the routing coverage test would still pass
    (since it only checks the pattern table), but the always-load guarantee
    would be silently lost.

    Spec: transferability-phase-3.md §9 Finding L3-6.
    """
    text = advisor_agent_path.read_text(encoding="utf-8")
    assert "Always load" in text and "kb-webex-limits.md" in text, (
        "migration-advisor.md is missing the 'Always load: kb-webex-limits.md' "
        "instruction. This instruction ensures the platform limits KB doc is loaded "
        "on every advisory run. Re-add it after the advisory pattern routing table."
    )
```

Use the Edit tool to append this function.

- [ ] **Step 3: Run all five tests that changed to verify they pass**

```bash
cd /Users/ahobgood/Documents/webexCalling
pytest tests/migration/transferability/test_advisor_routing_coverage.py -v --tb=short
```

Expected: Both tests pass (`test_advisor_routing_table_lists_all_patterns` and `test_advisor_always_load_kb_webex_limits`).

- [ ] **Step 4: Commit all five doc fixes together**

```bash
git add \
  src/wxcli/migration/advisory/CLAUDE.md \
  docs/runbooks/cucm-migration/self-review-findings.md \
  docs/runbooks/cucm-migration/operator-runbook.md \
  tests/migration/transferability/test_advisor_routing_coverage.py
git commit -m "docs(transferability): fix Layer 3 spec §9 findings (L3-1 through L3-6)"
```

---

## Task 6: Full suite smoke test

Before declaring Plan A complete, run the entire transferability suite to confirm all new and existing tests pass together.

- [ ] **Step 1: Run the full transferability suite**

```bash
cd /Users/ahobgood/Documents/webexCalling
pytest tests/migration/transferability/ -v --tb=short
```

Expected: All tests pass. If any test introduced in Tasks 1–5 fails due to a legitimate doc gap (e.g., `test_recommendation_output_coverage` flagging missing `**Recommendation:**` fields in the decision-guide), that is a Layer 2 finding — record it but do not count it as a Plan A failure. Plan A's job is to make the test exist, not to guarantee all current docs are already compliant.

- [ ] **Step 2: Run the full test suite to check for regressions**

```bash
cd /Users/ahobgood/Documents/webexCalling
pytest tests/ -m "not live" --tb=short -q
```

Expected: 1642+ tests passing, 0 failures.

---

## Self-Review

### Spec coverage check

| Spec requirement | Task |
|---|---|
| CI gate — path-filtered GitHub Actions job | Task 4 |
| `test_score_factor_display_names.py` — 3 assertions | Task 1 |
| `test_runbook_parsability.py` — table completeness, DT structure, anchor density, recipe entry-points, BLOCKING GATE visibility | Task 2 |
| `test_recommendation_output_coverage.py` — every `recommend_*` function has `**Recommendation:**` in decision-guide | Task 3 |
| `advisory/CLAUDE.md` "20" → "26" fix (Finding L3-1) | Task 5a |
| `self-review-findings.md` Finding 5 disposition update (Finding L3-2) | Task 5b |
| `operator-runbook.md` AXL credential clarification (Finding L3-3) | Task 5c |
| `operator-runbook.md` Step 11 slash-command marker (Finding L3-4) | Task 5d |
| `test_advisor_routing_coverage.py` "Always load" assertion (Finding L3-6) | Task 5e |

All 9 deliverables are covered.

### Placeholder scan

No placeholder phrases present. Every test function shows complete code. Every doc edit shows the exact old and new text pattern to locate.

### Type/name consistency check

- `WEIGHTS`, `DISPLAY_NAMES` — imported from `wxcli.migration.report.score` consistently across Task 1 and spec §7.
- `RECOMMENDATION_DISPATCH` — imported from `wxcli.migration.advisory.recommendation_rules` in Task 3. The dict has 20 keys matching the 20 `recommend_*` functions listed in the grep output above.
- `operator_runbook_path`, `decision_guide_path`, `tuning_reference_path`, `advisor_agent_path` — all provided by `conftest.py`; used consistently.
- `slugify`, `extract_anchors` — imported from `.conftest` in Task 3, matching the pattern in `test_decision_type_coverage.py`.
- `RUNBOOK_DIR`, `KB_DIR`, `SKILL_PATH` — imported from `.conftest` in Task 2, consistent with `conftest.py` definitions.
- `_find_recommendation_field_near_anchor` — defined and used only in Task 3; no cross-task reference.
