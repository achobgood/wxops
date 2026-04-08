<!-- Last verified: 2026-04-08 against branch claude/identify-missing-questions-8Xe2R -->

# Transferability Phase 3 — Validation Framework Spec

---

## 1. Problem Statement

Layers 1 and 2 built the knowledge artifacts and verified their internal
consistency. Layer 1 codified judgment as executable code: 26 advisory
patterns, 19 recommendation rules, 8 default auto-rules, and the
`SCORE_CALIBRATED` flag with a defined path to `True`. Layer 2 produced
three operator-facing runbooks, wired them into the `cucm-migrate` skill
and `migration-advisor` agent, and proved internal consistency via 22
pytest tests: every `DecisionType` has a decision-guide anchor, every
advisory pattern has a decision-guide anchor, every `DEFAULT_CONFIG` key
has a tuning-reference anchor, every markdown link resolves, every
`file:line` citation points to a real line.

What neither layer addresses is whether these artifacts actually help the
agent that reads them. **The primary reader of the Layer 2 runbooks is
Claude Code**, running inside the `cucm-migrate` skill or the
`migration-advisor` agent. A Cisco SE or customer is running Claude Code
in a session — they could read the runbooks directly but almost never
will. The runbooks are a lookup table for Claude Code, not a training
document for a human.

This inverts the validation model a human-audience framing would suggest.
Layer 3 is not a cold-read usability study with an SE. It is a measurement
of whether Claude Code, reading these artifacts during a live migration
session, encounters fewer stuck points and makes fewer wrong calls than
Claude Code reading nothing — or reading only the pre-Layer-2 state of
the skill. The Layer 2 tests prove the artifacts are internally consistent.
Layer 3 proves they are agent-readable and efficiency-improving.

The two explicit hand-offs from `self-review-findings.md` are both in
scope: (1) CI wiring — the 22 transferability tests exist and pass but
no GitHub Actions job triggers them specifically on the PRs that can
silently drift them; and (2) factor display-name regression — the G7
drift (internal score-factor names vs customer-facing display names)
was fixed inline with no test to prevent recurrence.

---

## 2. Success Criteria

Layer 3 is done when all of the following are met:

- **CI gate exists.** A path-filtered GitHub Actions job runs
  `pytest tests/migration/transferability/` on every PR touching any
  of the eight drift-sensitive files. The job blocks merge on failure.

- **Display-name regression test exists and passes.** A new test in
  `tests/migration/transferability/` asserts that every key in
  `score.py:WEIGHTS` has a corresponding entry in `score.py:DISPLAY_NAMES`
  and that the operator-runbook contains both the internal name and its
  display-name counterpart for each score factor.

- **Efficiency benchmark harness exists.** A standalone Python script
  (not a pytest test) can run a scripted decision-review session against
  a fixture migration project, capture tool-use metadata (Read/Grep/Bash
  call counts and targets, input token counts, decision outcomes), and
  produce a structured JSON report. The harness does not require a live
  CUCM cluster or a live Webex org.

- **Baseline run is committed.** At least one baseline run of the
  benchmark harness against the existing skill + runbooks is committed
  to the repo as a reference artifact (`docs/reports/layer3-baseline-*.json`).
  Future runs diff against this baseline.

- **All six failure modes have a detection mechanism.** Each mode defined
  in §3 has either (a) an automated test that catches it, or (b) a
  named metric in the benchmark harness that surfaces it. No failure mode
  is "in scope" without a concrete detection path.

- **Calibration feedback loop is documented.** The `SCORE_CALIBRATED`
  path is updated in `tuning-reference.md §What SCORE_CALIBRATED = False
  Means` to reference the harness's output format and the handoff
  procedure when Layer 3 data meets the threshold for setting it to `True`.

- **Layer 2 findings from §9 are triaged.** Each finding in §9 of this
  spec is reviewed by the user and either (a) scheduled for a follow-up
  commit with a `docs(transferability): ...` message, or (b) explicitly
  marked "accepted — no fix."

---

## 3. Failure Modes in Scope

Layer 3 must be able to detect and measure all six of the following
failure categories. For each: the signal that detects it, the cost to
instrument, and the cadence at which it is checked.

### 3.1 Loops

**Definition:** Claude Code re-runs the same pipeline stage, re-reads
the same file three or more times in a single decision review session,
or re-derives a value from source code that the runbook already provides.

**Signal:** The benchmark harness records every `Read` and `Grep` tool
call with its `file_path` argument. After the session, a post-processor
counts duplicate `file_path` values within each pipeline stage. Any file
read more than twice in a stage is flagged as a loop candidate. A
separate check counts how many times `wxcli cucm analyze` or
`wxcli cucm decisions` appears in Bash calls within the decision-review
phase — more than once in a phase (absent an explicit error-recovery
path) is a loop.

**Cost:** Low — tool-call recording is a side effect of the harness
intercepting tool responses. No LLM budget beyond the benchmark run itself.

**Cadence:** Per benchmark run. Baseline run on merge; re-run when the
skill, runbooks, or advisor agent change materially (judged by the CI
path filter).

**Current state (pre-Layer 3):** No detection. The existing tests verify
artifact consistency but do not observe Claude Code's behavior.

---

### 3.2 Wrong Calls

**Definition:** Claude Code picks a non-recommended option on a decision
where the recommendation field is set and the decision-guide entry gives
a clear preference; or Claude Code accepts a dissent-flagged decision
without invoking the dissent protocol (presenting both the static
recommendation and the advisor alternative with KB citation).

**Signal:** The benchmark harness runs decision review against a fixture
project whose decisions have known `recommendation` values. The harness
extracts the option chosen for each resolved decision from the session
transcript (by grepping for `wxcli cucm decide <ID>` calls in Bash
tool content). Decision accuracy is computed as:

```
accuracy = decisions_matching_recommendation / decisions_with_recommendation
```

For dissent-flagged decisions (fixture decisions that correspond to a
`DT-{DOMAIN}-NNN` entry marked HIGH confidence in the relevant KB doc),
the harness checks whether the advisor's alternative option and its KB
citation appeared in the transcript before the `wxcli cucm decide` call.

**Cost:** Medium — requires constructing fixture decisions with known
`recommendation` values and known dissent triggers. Fixture construction
is a one-time cost.

**Cadence:** Per benchmark run.

**Current state (pre-Layer 3):** No detection. The existing tests verify
that recommendation functions exist but not that they produce the right
decision during an interactive session.

---

### 3.3 Token Waste

**Definition:** Claude Code reads a large source file to answer a
question the runbook already answers, consuming more input tokens than
a direct runbook lookup would have. A concrete threshold: reading
`advisory_patterns.py` (≈250 lines), `recommendation_rules.py` (≈350
lines), or `analysis_pipeline.py` (≈200 lines) during the decision-review
phase when no failure has been diagnosed is token waste. The runbook
exists precisely to make these reads unnecessary.

**Signal (primary):** The harness records every Read call and checks
whether the target path is under `src/wxcli/migration/`. Any such read
during the decision-review phase (Steps 1c/1c-fallback) that is not
preceded by an explicit error or an "I need to diagnose a failure"
assistant message is flagged as token waste.

**Signal (secondary):** The harness records the total input token count
for the decision-review phase (from the Anthropic API `usage.input_tokens`
field on each response). This is compared against the baseline. A
regression is defined as >20% increase in tokens-per-decision-resolved
without a corresponding increase in decision accuracy.

**Signal (tertiary, structural):** The `test_runbook_cites.py` suite
already verifies that runbook prose cites source at specific lines. A
separate structural probe (see §7 for the display-name variant of this
pattern) checks whether tuning-reference.md and decision-guide.md
contain inline answers for the top-10 most commonly re-derived values
(config key defaults, option IDs, DecisionType semantics). This is a
static analysis test, not a harness run.

**Cost:** Medium for the harness signal; low for the structural probe.

**Cadence:** Per benchmark run for harness; per PR for structural probe.

**Current state (pre-Layer 3):** No detection.

---

### 3.4 Unparseable Tables and Prose

**Definition:** Claude Code cannot resolve a runbook reference because
the formatting is ambiguous or the prose is too verbose to extract an
answer cleanly in-context. Examples: a decision-guide table where the
`Option` column spans multiple lines and a naive reader would merge two
option descriptions; a tuning-reference recipe where the "prerequisite"
and "steps" sections are not visually distinguished; a KB doc Dissent
Trigger whose `Condition` field is a paragraph instead of a scannable
predicate.

**Signal (automated — CI):** A new pytest module,
`test_runbook_parsability.py`, runs structural probes on each of the
three runbook files:

1. **Table completeness:** Every markdown table has a header row, a
   divider row (`|---|---|`), and at least one data row. Tables with
   merged cells (a `|` appearing inside a cell value followed by no
   closing `|` on the same line) are flagged.

2. **Dissent Trigger structure:** Every `DT-{DOMAIN}-NNN` heading in
   all 8 KB docs is followed within 5 lines by a `**Condition:**` line
   and a `**Recommendation:**` line. Entries that are missing either
   field are flagged.

3. **Anchor density:** Each `### DecisionType` entry in decision-guide.md
   contains at least one of: `**Recommendation:**`, `**Options:**`, or
   `**Auto-rule match:**` within 20 lines of the heading. Entries with
   none of these are flagged as structurally incomplete.

4. **Recipe step structure:** Each recipe in tuning-reference.md
   §Tuning Recipes begins with a `**Symptom:**` or `**When to use:**`
   line within 5 lines of the recipe heading. Recipes missing this
   entry-point field are flagged.

**Signal (harness — periodic):** After a benchmark run, the session
transcript is scanned for phrases that indicate confusion about artifact
structure: "I don't see a recommendation for this decision type", "the
table appears to be cut off", "I'll check the source code to understand
the options". These are flagged as parsability candidates for manual review.

**Cost:** Low for the CI structural probes (pure text parsing); medium
for the harness scan (requires a benchmark run).

**Cadence:** Per PR for CI probes; per benchmark run for harness scan.

**Current state (pre-Layer 3):** The `test_runbook_links.py` verifies
links resolve but does not probe internal table structure. No dissent
trigger field completeness check exists. No recipe structure check exists.

---

### 3.5 Missed Gotchas

**Definition:** Claude Code proceeds past a "if you see X, do Y" warning
in the runbook without applying Y. Examples: not running `wxcli cucm
analyze` after importing location addresses (SKILL.md Step 1a instruction
at line 98–103); not blocking on location addresses before proceeding to
decision review (the BLOCKING GATE instruction at SKILL.md line 94);
accepting a dissent-flagged decision at HIGH confidence without explicitly
surfacing the dissent protocol.

**Signal (harness):** The benchmark harness fixture includes a project
state that triggers specific gotcha paths. For each path, the harness
checks that the corresponding guard action appeared in the session
transcript:

| Gotcha path | Expected guard action |
|---|---|
| Locations with null addresses | `wxcli cucm import-locations` called before `wxcli cucm decisions` |
| Token expiry < 2h | "Your token expires in" warning emitted before execution |
| HIGH-confidence dissent flag | Advisor alternative presented with KB citation before `wxcli cucm decide` |
| Preflight failure | Execution blocked; fix instructions provided |

A "missed gotcha" is recorded when a fixture activates a gotcha path but
the guard action does not appear in the transcript.

**Signal (CI — structural):** A new probe in `test_runbook_parsability.py`
verifies that every BLOCKING GATE marker in SKILL.md (`**[MANDATORY, NOT
SKIPPABLE]**`, `**Do NOT proceed**`) appears at a heading level (##, ###)
and is not buried inside a code block where it would be invisible to a
casual reader. This is a formatting check, not a behavior check.

**Cost:** Medium for harness (fixture construction); low for CI probe.

**Cadence:** Per benchmark run for harness; per PR for CI probe.

**Current state (pre-Layer 3):** No detection of missed gotcha behavior.

---

### 3.6 Redundant Re-derivation

**Definition:** Claude Code computes something the runbook already
provides — for example, deriving the semantic meaning of
`CSS_ROUTING_MISMATCH` by reading `analysis_pipeline.py` and
`analyzers/css_routing.py` instead of looking it up in decision-guide.md;
or re-reading `score.py` to determine factor weights instead of using
the tuning-reference table at §The 8 Score Factors.

**Signal (harness):** Same as §3.3 Token Waste — source-file reads
during decision-review are a proxy for re-derivation. The harness
additionally records whether the `recommendation_rules.py` or
`advisory_patterns.py` source was read. If so, it logs the preceding
assistant message to help identify what question triggered the source
read. This gives the Layer 3 maintainer a targeted signal for which
runbook section is failing to answer the question.

**Signal (CI — coverage):** The existing `test_runbook_cites.py`
verifies that `recommend_*` and `detect_*` functions cited in the
runbooks exist. Layer 3 adds an inverse check: for every
`recommend_{type}` function in `recommendation_rules.py`, the
decision-guide.md must have a `Recommendation:` field in the
corresponding `### <decision-type>` entry. This ensures the runbook
contains the function's output (the recommendation) not just a citation
to the function's existence.

**Cost:** Low for the CI inverse-coverage check; marginal for the harness
(same session recording as §3.3).

**Cadence:** Per PR for CI check; per benchmark run for harness signal.

**Current state (pre-Layer 3):** The existing tests verify function
existence but not that the runbook reproduces the function's output.

---

## 4. Measurement Architecture

### 4.1 Why Not Instrument the Skill Inline

The obvious approach is to add structured log emissions to SKILL.md and
the migration-advisor agent — `> [SKILL_LOG: ...]` markers that Claude
Code is instructed to emit, which can then be parsed from session output.
This was considered and rejected for three reasons:

1. **Unreliable emission.** Claude Code's compliance with "emit a log
   line at this step" instructions degrades when the session is long or
   the agent is focused on a complex decision. A missed emission produces
   a false negative (no loop detected) rather than a clear test failure.

2. **Spec pollution.** Adding observability markers to an operator-facing
   skill changes the artifact under test. The goal is to measure the
   runbooks as they are, not as they would be with instrumentation added.

3. **Context budget.** Log emission instructions consume token budget in
   every response, increasing the very metric (tokens per decision) that
   Layer 3 is trying to measure.

### 4.2 Chosen Architecture: Two-Tier

Layer 3 uses two independent measurement tiers that complement each other:

**Tier 1 — Automated CI tests (runs on every PR):** Extends the existing
`tests/migration/transferability/` pytest suite with structural probes
that detect formatting problems, coverage regressions, and display-name
drift without running any LLM. These are cheap, deterministic, and
block-merge.

**Tier 2 — Periodic benchmark harness (runs on demand or scheduled):**
A standalone Python script that exercises the `cucm-migrate` skill
against a fixture migration project via the Anthropic API, records all
tool-use events, and produces a structured JSON efficiency report.
This tier measures Claude Code's actual behavior — loop rate, token
consumption, decision accuracy, gotcha coverage. It is expensive (API
calls, fixture maintenance) and non-deterministic (model behavior varies),
so it runs periodically, not on every PR.

### 4.3 Tier 1 — CI Structural Tests

**What it adds to the existing suite:**

| New test file | What it checks |
|---|---|
| `test_runbook_parsability.py` | Table completeness, DT structure, anchor density, recipe entry-points, BLOCKING GATE visibility |
| `test_score_factor_display_names.py` | `WEIGHTS` ↔ `DISPLAY_NAMES` parity; both names in operator-runbook |
| `test_recommendation_output_coverage.py` | Every `recommend_*` function's recommended option ID appears in decision-guide.md for that DecisionType |

These sit alongside the existing 7 test files. All 3 new files import only
from the Python source and the runbook markdown — no Anthropic API, no
subprocess execution beyond what the CLI command tests already do.

**What it does NOT add:** The CI tier cannot detect loops, wrong calls,
token waste, or missed gotchas. Those require a live session. The CI tier
is a necessary but not sufficient condition for Layer 3 completion.

### 4.4 Tier 2 — Benchmark Harness

**Location:** `tools/layer3_benchmark.py`

This script is not a pytest test. It is a standalone executable that
uses the `anthropic` Python SDK directly.

**Fixture project:** A pre-built SQLite store at
`tests/fixtures/benchmark-migration/` containing:

- 12 decisions spanning all 3 review groups (auto-apply, recommended,
  needs-input)
- 4 decisions with `recommendation` values derived from known
  recommendation_rules logic
- 2 decisions corresponding to HIGH-confidence Dissent Trigger conditions
  (one CSS routing dissent, one feature approximation dissent)
- 3 gotcha-path triggers: one location with null address, one token
  expiry marker in `wxcli whoami` mock output, one preflight check failure
- Fixture tool responses: the harness intercepts every tool call and
  returns pre-recorded responses from the fixture directory, so no live
  Webex org or CUCM cluster is needed

**Session design:** The harness constructs an API session that:

1. Sets the system prompt to the full contents of
   `.claude/skills/cucm-migrate/SKILL.md`
2. Opens with a user message: `"Run the CUCM migration for project
   benchmark-migration"`
3. Runs the tool-use loop: on each model response, the harness processes
   tool_use blocks by looking up responses in the fixture directory,
   then sends tool_result blocks back
4. Continues until the model returns a response with no tool_use blocks
   or a stop signal

**What gets recorded per session:**

```json
{
  "session_id": "...",
  "timestamp": "...",
  "skill_sha": "...",
  "runbook_sha": "...",
  "phases": {
    "assessment": {
      "turns": 3,
      "input_tokens": 4200,
      "tool_calls": [
        {"tool": "Bash", "summary": "wxcli cucm status"},
        {"tool": "Bash", "summary": "wxcli cucm report ..."}
      ],
      "source_file_reads": []
    },
    "decision_review": {
      "turns": 8,
      "input_tokens": 18400,
      "tool_calls": [...],
      "source_file_reads": ["src/wxcli/migration/advisory/advisory_patterns.py"],
      "decisions_resolved": 12,
      "decision_accuracy": 0.92,
      "gotcha_coverage": {
        "location_address_gate": true,
        "token_expiry_gate": true,
        "dissent_protocol": false
      },
      "duplicate_reads": []
    }
  },
  "summary": {
    "total_input_tokens": 22600,
    "tokens_per_decision": 1883,
    "source_file_reads_in_review": 1,
    "decision_accuracy": 0.92,
    "gotcha_coverage_rate": 0.67,
    "loops_detected": 0
  }
}
```

**Baseline commit:** On Layer 3 implementation completion, one baseline
run is committed to `docs/reports/layer3-baseline-YYYY-MM-DD.json`. The
harness's `--compare` flag diffs a new run against the committed baseline
and prints a regression report. A >20% regression on
`tokens_per_decision` or a drop in `decision_accuracy` below the
baseline value is reported as a warning.

### 4.5 How the Loop Closes Back to Layer 1 and Layer 2

**Back to Layer 1 (`SCORE_CALIBRATED`):** When the benchmark harness
produces a run against a real (non-fixture) migration project and the
admin provides ground-truth data on the migration outcome, the session
JSON is the input to the calibration protocol already specified in
`tuning-reference.md §What SCORE_CALIBRATED = False Means`. The harness
report includes a `calibration_data` section (format TBD in the
tuning-reference update — see §8 Deliverable 6) that matches the
Calibration Data Capture schema. Once 3+ real runs with ground truth
are accumulated, `SCORE_CALIBRATED` can be set to `True` and the
disclaimer removed from reports.

**Back to Layer 2 (runbook revisions):** When the harness detects a
source-file read during decision review, the session log includes the
preceding assistant message (the question that triggered the read). This
pinpoints which runbook section is failing to answer the question. The
Layer 3 maintainer reviews these findings quarterly and files targeted
`docs(transferability): ...` commits to the relevant runbook section.
The Layer 2 findings in §9 of this spec are the first such backlog.

---

## 5. Efficiency Metrics

Layer 3 tracks the following concrete numeric signals. Units and
comparison methods are defined so future runs can be compared without
ambiguity.

### 5.1 Tokens per Decision Resolved

**Unit:** Input tokens consumed during the decision-review phase
(Steps 1a–1c of SKILL.md) divided by the number of decisions resolved
in that phase.

**Baseline comparison:** Absolute value against committed baseline.
Regression threshold: >20% increase without a corresponding
>5% increase in `decision_accuracy`.

**Why this matters:** If the skill eats 180K tokens reviewing 50
decisions on a test fixture, it will exhaust the context window on a
real 500-DN migration before execution even starts.

**Where it lives:** `summary.tokens_per_decision` in the harness JSON.

---

### 5.2 Source-File Read Rate During Decision Review

**Unit:** Count of unique file paths under `src/wxcli/migration/` that
appear in `Read` tool calls during the decision-review phase.

**Target:** 0 in the absence of an error-recovery path. Any value >0
is reported as a token-waste signal (see §3.3).

**Baseline comparison:** Binary — did it read source during review?
The baseline should be 0 after Layer 2's runbooks are operative. Any
regression from 0 is reported.

**Where it lives:** `phases.decision_review.source_file_reads` in the
harness JSON.

---

### 5.3 Duplicate Read Count

**Unit:** Count of `(file_path, phase)` pairs where the same file is
read more than twice in the same pipeline phase.

**Target:** 0. One read at entry (to orient) and one re-read on error
recovery are acceptable; three or more indicates a loop.

**Baseline comparison:** Against committed baseline. Any increase is
reported.

**Where it lives:** `phases.<phase>.duplicate_reads` in the harness JSON.

---

### 5.4 Decision Accuracy Rate

**Unit:** `decisions_matching_recommendation / decisions_with_recommendation`
across all fixture decisions that have a `recommendation` field set.

**Target:** ≥0.90 (9 of 10 recommended decisions accepted without
override) on the baseline run.

**Baseline comparison:** Against committed baseline. A drop of >0.10
absolute is a regression.

**Why this matters:** The recommendation rules are the Layer 1 codified
judgment. If Claude Code overrides them without a dissent flag, either
the runbook's decision-guide entry is inadequately explaining the
recommendation or the model is ignoring it.

**Where it lives:** `phases.decision_review.decision_accuracy` in the
harness JSON.

---

### 5.5 Gotcha Coverage Rate

**Unit:** Count of fixture-triggered gotcha paths where the expected
guard action appeared in the transcript, divided by the total count of
fixture-triggered gotcha paths.

**Target:** 1.00 (all gotchas covered) on the baseline run.

**Baseline comparison:** Against committed baseline. Any drop is a
regression.

**Where it lives:** `phases.decision_review.gotcha_coverage` dict in the
harness JSON, plus `summary.gotcha_coverage_rate`.

---

### 5.6 Turns per Resolution

**Unit:** Total assistant turns in the decision-review phase divided by
decisions resolved.

**Target:** Not defined as a hard threshold (this varies with model
verbosity). Tracked for trend analysis across versions.

**Baseline comparison:** Informational; not a hard regression trigger.
A >2x increase from baseline warrants investigation.

**Where it lives:** Computed from `phases.decision_review.turns /
phases.decision_review.decisions_resolved`.

---

### 5.7 Runbook Lookup Rate (Qualitative)

**Unit:** Fraction of decision-review turns that contain a reference to a
runbook section (by heading name or anchor) vs. turns that reference
source code or produce ungrounded text.

**Target:** >0.50 of turns in the decision-review phase contain at least
one reference to a runbook heading or anchor.

**How measured:** Regex scan of assistant text in the harness session log.
Patterns: `decision-guide.md#`, `tuning-reference.md#`, operator-runbook
section headings.

**Why this matters:** High runbook lookup rate indicates the artifacts are
being used as the primary reference. Low rate indicates the model is
reasoning from training data instead, which means the runbooks aren't
pulling their weight.

**Where it lives:** Computed post-hoc from the session transcript; added
to the summary section of the harness JSON.

---

## 6. CI Wiring

### 6.1 Workflow File

**File:** `.github/workflows/transferability.yml`

This is a new workflow file separate from `.github/workflows/ci.yml`.
The existing `ci.yml` runs `pytest tests/ -m "not live"` on push to
main and PRs to main — it already covers the transferability tests as
a side effect. The new workflow adds an explicit, path-filtered job
whose failure message names the specific drift category.

### 6.2 Trigger Paths

The job triggers on `pull_request` to `main` when any of the following
paths change:

```yaml
paths:
  - 'src/wxcli/migration/advisory/advisory_patterns.py'
  - 'src/wxcli/migration/advisory/recommendation_rules.py'
  - 'src/wxcli/commands/cucm_config.py'
  - 'src/wxcli/migration/report/score.py'
  - 'src/wxcli/migration/models.py'
  - 'docs/runbooks/cucm-migration/**'
  - '.claude/skills/cucm-migrate/SKILL.md'
  - '.claude/agents/migration-advisor.md'
```

These are exactly the 8 files named in `self-review-findings.md §Drift
Outside Phase 2 Scope` plus the runbook directory. Changes to any of
these files can silently break the transferability invariants.

### 6.3 Job Definition

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
        # tests/migration/transferability/ gates the runbook ↔ code
        # invariants. Fix the broken test before merging."
```

### 6.4 Failure Behavior

On failure, the job output includes the pytest short-traceback, which
names the specific broken invariant (e.g., "decision-guide.md is missing
anchors for 2 DecisionType(s): ['css-routing-mismatch-new']"). This is
actionable without reading the test file.

The existing `ci.yml` job continues to run `pytest tests/` on all PRs;
it catches transferability failures as a secondary gate. The new
`transferability.yml` is the primary, targeted gate with the explicit
failure message.

### 6.5 Python Version

The workflow uses Python 3.11 only (matching the project's primary
version). The existing `ci.yml` matrix-tests 3.11 and 3.12; the
transferability gate does not need the matrix because all tests are
pure-Python text parsing with no version-sensitive behavior.

---

## 7. Factor Display-Name Regression Test

### 7.1 Background

The G7 self-walkthrough finding (recorded in `self-review-findings.md
§Assessment Report Drift`) discovered that `score.py` uses two
parallel name sets for its 8 complexity factors:

- `WEIGHTS` dict (line 17): internal names like `"CSS Complexity"`,
  `"Feature Parity"`, `"Decision Density"`
- `DISPLAY_NAMES` dict (line 28): customer-facing names like
  `"Calling Restrictions"`, `"Feature Compatibility"`,
  `"Outstanding Decisions"`

The operator-runbook was updated inline (commit `5e891a8`) to show both
names in a 4-column table. No regression test was added. A future rename
of a factor in `DISPLAY_NAMES` or `WEIGHTS` would silently break the
runbook's dual-name table.

### 7.2 Test Location

**File:** `tests/migration/transferability/test_score_factor_display_names.py`

This file joins the existing 7 test files in
`tests/migration/transferability/`. It imports from `score.py` directly
and reads `operator-runbook.md` as text — no special fixtures needed.

### 7.3 What the Test Asserts

**Assertion 1 — WEIGHTS ↔ DISPLAY_NAMES parity:**

Every key in `score.py:WEIGHTS` must appear as a key in
`score.py:DISPLAY_NAMES`, and vice versa. This catches a rename in
either dict that leaves the two out of sync.

```python
def test_weights_and_display_names_keys_match():
    assert set(WEIGHTS.keys()) == set(DISPLAY_NAMES.keys()), (
        f"WEIGHTS and DISPLAY_NAMES have different keys. "
        f"In WEIGHTS only: {set(WEIGHTS.keys()) - set(DISPLAY_NAMES.keys())}. "
        f"In DISPLAY_NAMES only: {set(DISPLAY_NAMES.keys()) - set(WEIGHTS.keys())}."
    )
```

**Assertion 2 — Internal names in operator-runbook:**

Every key in `WEIGHTS` must appear as a literal string in
`operator-runbook.md`. This catches a score factor rename that the
runbook's dual-name table has not been updated to reflect.

```python
def test_internal_factor_names_in_runbook(operator_runbook_path):
    text = operator_runbook_path.read_text(encoding="utf-8")
    missing = [k for k in WEIGHTS if k not in text]
    assert not missing, (
        f"operator-runbook.md is missing these internal factor names: {missing}. "
        f"Update the §The 8 Score Factors table to include both the internal name "
        f"and the display name for each factor."
    )
```

**Assertion 3 — Display names in operator-runbook:**

Every value in `DISPLAY_NAMES` must appear as a literal string in
`operator-runbook.md`. This catches a rename of the customer-facing
name that the runbook hasn't tracked.

```python
def test_display_factor_names_in_runbook(operator_runbook_path):
    text = operator_runbook_path.read_text(encoding="utf-8")
    missing = [v for v in DISPLAY_NAMES.values() if v not in text]
    assert not missing, (
        f"operator-runbook.md is missing these display factor names: {missing}. "
        f"Update the §The 8 Score Factors table to include the display name "
        f"(shown to customers in the report) alongside the internal name."
    )
```

### 7.4 Fixture Data

No fixture data needed. The test reads from:
- `src/wxcli/migration/report/score.py` — imported directly as
  `from wxcli.migration.report.score import WEIGHTS, DISPLAY_NAMES`
- `docs/runbooks/cucm-migration/operator-runbook.md` — via the existing
  `operator_runbook_path` fixture in `conftest.py`

### 7.5 Edge Cases

**Factor with identical internal and display name:** `"Scale"` maps to
`"Scale"` in the current `DISPLAY_NAMES`. Assertions 2 and 3 both pass
for this factor with a single occurrence. This is intentional — no
special handling needed.

**New factor added to WEIGHTS without DISPLAY_NAMES entry:** Assertion 1
catches this immediately. The test message names the missing key.

**Factor renamed in DISPLAY_NAMES but not in runbook:** Assertion 3
catches this. The test message names the missing display value.

---

## 8. Deliverable Inventory

Ordered by dependency. Human-owned items are work the user or a
teammate must do. Claude Code-owned items are implementation tasks for
a future execution session.

| # | Artifact | Owner | Depends on |
|---|---|---|---|
| 1 | `.github/workflows/transferability.yml` | Claude Code | Nothing — standalone YAML |
| 2 | `tests/migration/transferability/test_score_factor_display_names.py` | Claude Code | Nothing — reads existing score.py and runbook |
| 3 | `tests/migration/transferability/test_runbook_parsability.py` | Claude Code | Nothing — pure text parsing |
| 4 | `tests/migration/transferability/test_recommendation_output_coverage.py` | Claude Code | Depends on understanding all 19 recommendation_rules functions and their return values |
| 5 | `tools/layer3_benchmark.py` — harness script skeleton | Claude Code | Depends on fixture design (#6) |
| 6 | `tests/fixtures/benchmark-migration/` — fixture store + tool response mocks | Human (design) + Claude Code (build) | Requires deciding which 12 decisions to include and what gotcha-path triggers to activate |
| 7 | `tools/layer3_benchmark.py` — full implementation with fixture integration | Claude Code | Depends on #5 and #6 |
| 8 | `docs/reports/layer3-baseline-YYYY-MM-DD.json` — first baseline run | Human (runs the harness) | Depends on #7 |
| 9 | `tuning-reference.md §What SCORE_CALIBRATED = False Means` update | Claude Code | Depends on #8 (to know the harness output format) |
| 10 | Layer 2 findings triage and follow-up commits | Human (triage) + Claude Code (fix) | Depends on user review of §9 |

**Dependency notes:**

- Items 1–4 are independent of each other and of items 5–9. They can
  be implemented in a single parallel wave.
- Items 5–7 must be sequenced: skeleton (#5) → fixture design (#6) →
  full implementation (#7).
- Item 8 (baseline run) requires a working Anthropic API key and
  produces output that informs item 9.
- Item 10 is a rolling backlog, not a blocking dependency for any
  of items 1–9.

**What is not a deliverable:**
- No new runbook file
- No changes to Layer 1 source code
- No changes to the three existing runbooks (unless fixing a §9 finding
  after user triage)

---

## 9. Layer 2 Findings

Issues discovered in Layer 2 artifacts during spec work. These are not
Layer 3 implementation tasks — they are a backlog for the user to triage.
Each entry: file + anchor + finding + proposed fix.

**Finding L3-1:** `src/wxcli/migration/advisory/CLAUDE.md` — file map
table (line 42)
> Quoted: `advisory_patterns.py | 20 cross-cutting pattern detectors`
> Finding: The file map table says 20 patterns but the prose section
> §Cross-Cutting Advisory Patterns (Layer 2) on line 73 of the same file
> says 26. The actual count is 26 (Layer 1 added 6 new patterns in advisory
> patterns 21–26). The file map table is stale by 6.
> Proposed fix: Update line 42 to read "26 cross-cutting pattern detectors"
> to match the body text and the actual `ALL_ADVISORY_PATTERNS` list.

**Finding L3-2:** `docs/runbooks/cucm-migration/self-review-findings.md`
— §Author Self-Walkthrough §Finding 5
> Quoted: "Deferred — drift outside Phase 2 scope. Phase 2 self-walkthrough
> caught the drift manually; the test enhancement is a Layer 3 improvement."
> Finding: Finding 5 describes extending `FILE_LINE_RE` to match `.md`
> citations as a deferred Layer 3 task. However, §Code Review Pass
> §Observation 3 (later in the same file) documents that this fix was
> applied in the post-G8 cleanup pass. The Finding 5 disposition text
> is now stale — it says "deferred" for something that was completed.
> Proposed fix: Update Finding 5 disposition from "Deferred" to "Fixed
> in post-G8 cleanup commit" with a reference to Observation 3's fix
> description, so the document is self-consistent.

**Finding L3-3:** `docs/runbooks/cucm-migration/operator-runbook.md`
— §Quick Start (accepted minor, Finding 6 from self-review)
> Quoted: "Note: AXL credentials are separate from the Webex OAuth token"
> Finding: The proposed fix from self-review Finding 6 was not applied —
> the "accepted minor" disposition deferred it. However, the dual-credential
> model is exactly the kind of setup confusion that would cause Claude Code
> to issue a confusing or incorrect `wxcli configure` instruction to an admin
> on first run. This is a Claude-Code-readability issue, not just a human
> readability issue.
> Proposed fix: Apply the one-line clarification from Finding 6 to the Quick
> Start §Assumed environment block. Effort: < 5 minutes.

**Finding L3-4:** `docs/runbooks/cucm-migration/operator-runbook.md`
— §Quick Start (accepted minor, Finding 7 from self-review)
> Quoted: `/cucm-migrate <project>`
> Finding: The slash-command syntax for Step 11 in the Quick Start is not
> marked as a Claude Code session command (vs. bash). For a Claude Code
> agent reading this runbook for the first time, the unmarked syntax creates
> ambiguity: should it call `Bash(["/cucm-migrate", ...])` (which fails) or
> invoke the skill through its own skill mechanism? The inline disambiguation
> proposed in Finding 7 was not applied.
> Proposed fix: Apply the inline marker from Finding 7: add "(Claude Code
> slash command — invoke in the session, not in bash)" after the `/cucm-migrate`
> command in the Quick Start.

**Finding L3-5:** `docs/runbooks/cucm-migration/decision-guide.md` —
routing table completeness
> Finding: The decision-guide.md has 20 `### <decision-type>` entries
> (one per non-advisory DecisionType, excluding `ARCHITECTURE_ADVISORY`).
> Each entry is verified to exist by `test_decision_type_coverage.py`. However,
> the test only checks for anchor existence — not that each entry contains a
> `**Recommendation:**` field. The Layer 1 recommendation_rules have 19
> functions (one per non-advisory, non-ambiguous DecisionType); at least one
> DecisionType (`MISSING_DATA`) may not have its recommendation reproduced
> in plain English in the decision-guide. The `test_recommendation_output_coverage.py`
> test proposed in §3.6 will verify this. If it fails on initial run, that
> failure is a Layer 2 finding to fix.
> Proposed fix: Run deliverable #4 from §8 and fix any entries it flags.

**Finding L3-6:** `docs/knowledge-base/migration/kb-webex-limits.md` —
always-loaded status
> Finding: The migration-advisor.md routing table includes "**Always load:**
> `kb-webex-limits.md`" as the final entry after the advisory pattern table.
> The `test_advisor_routing_coverage.py` test verifies only that advisory
> pattern names appear in the routing table — it does not verify that the
> "always load" instruction is present. If the instruction were accidentally
> deleted, the test would still pass.
> Proposed fix: Add a dedicated assertion to `test_advisor_routing_coverage.py`
> (or a new test) that verifies the "Always load: `kb-webex-limits.md`"
> marker appears in `migration-advisor.md`.

---

## 10. Open Questions

**OQ-1: Fixture project size.**
The spec proposes 12 decisions in the benchmark fixture. Is 12 large
enough to produce stable efficiency metrics, or does it need to be
closer to a realistic 50-DN sample (which would have 30–60 decisions)?
Larger fixtures improve signal quality but increase harness maintenance
cost. The 12-decision proposal is a starting point — the implementer
should validate it against the token-per-decision baseline to confirm
it exercises a meaningful portion of the decision-review flow.

**OQ-2: Harness run cadence.**
The spec calls the benchmark harness "periodic" without specifying a
period. Weekly would produce good trend data but costs API budget on
every run. Monthly is cheaper but slow to detect regressions. A
reasonable default is: run on every merge to main that touches the
8 drift-sensitive files (same trigger as the CI gate), with a scheduled
monthly run as a backstop. This is not spec'd here because it depends
on the project's API budget and GitHub Actions minute allocation.

**OQ-3: What counts as a "regression" for decision accuracy.**
The spec proposes a 0.10 absolute drop as the regression threshold. But
if the fixture has only 4 decisions with recommendations, a 0.10 drop
equals missing one decision — which could be noise (model non-determinism)
rather than a real regression. The threshold should be validated against
multiple baseline runs to understand natural variance before being treated
as a hard gate.

**OQ-4: Harness model version.**
The benchmark harness should be pinned to a specific model version to
avoid baseline drift caused by model upgrades. The current project model
is `claude-sonnet-4-6`. When the model is upgraded, the baseline should
be re-run and re-committed so comparisons are against the new model's
behavior, not the old one's.

**OQ-5: Fixture maintenance ownership.**
The fixture store in `tests/fixtures/benchmark-migration/` will drift
as the pipeline schema evolves (new DecisionTypes, new store columns,
new option IDs). Who owns keeping the fixture in sync? This should be
documented in the fixture directory's README alongside the fixture's
design intent.

**OQ-6: Harness availability in CI.**
The benchmark harness requires an `ANTHROPIC_API_KEY` to run. If the
CI-on-merge variant of the harness trigger (OQ-2) is implemented, the
API key must be available as a GitHub Actions secret. This is a
straightforward secrets configuration, but it means the harness is not
runnable in fork PRs (which don't get org secrets). The harness should
detect missing `ANTHROPIC_API_KEY` and exit with a clear message rather
than failing cryptically.

---

## 11. Out of Scope

The following are explicitly out of scope for Layer 3, restating the
non-goals from the task spec and adding two identified during spec work:

**G6 external reviewer pass.** The user is handling this independently.
If G6 findings arrive, they land as `docs(transferability): G6 external
reviewer fix — ...` commits, not as Layer 3 tasks.

**Rewriting Layer 2 artifacts.** The operator-runbook, decision-guide,
and tuning-reference are not modified by Layer 3 implementation work,
except to fix a §9 finding after explicit user triage approval.

**Layer 1 redesign.** The `SCORE_CALIBRATED` flag, `DEFAULT_AUTO_RULES`,
and the 26 advisory patterns are fixed. Layer 3 proposes a feedback path
into Layer 1 (the calibration loop in §4.5) but does not change the
Layer 1 artifacts.

**New runbook.** If Layer 3 needs to document "how to read a validation
report," that section belongs in `tuning-reference.md §What
SCORE_CALIBRATED = False Means` (as a subsection), not as a fourth
runbook.

**Live integration testing.** The benchmark harness uses fixture data
(mocked tool responses). Running the harness against a live CUCM cluster
and a live Webex org is a future milestone (relevant when feeding real
data into the calibration loop), not a Layer 3 requirement.

**Comprehensive LLM evaluation.** Layer 3 is a targeted efficiency and
accuracy measurement, not a full LLM evaluation suite. It measures the
6 failure modes specific to the migration workflow. General instruction-
following quality, hallucination rate, or cross-task performance are out
of scope.

**Decision-guide or tuning-reference content changes.** Adding new
entries, improving recommendations, or expanding the worked recipes in
tuning-reference.md based on real-world feedback is ongoing maintenance
work (Layer 2 territory). Layer 3 may trigger that work by surfacing
findings, but performing it is not a Layer 3 deliverable.
