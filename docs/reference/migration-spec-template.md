# Migration Pipeline Spec Template

All migration pipeline spec documents must follow this template. This applies whether
the spec is written interactively via brainstorming, by an agent swarm, or manually.
All 9 sections are required. Sections can be brief for simple specs but cannot be omitted.

**Quality gate:** Can someone implement this in a separate session without asking
clarifying questions? If the answer is no, the spec is not ready. Every file path must
be real. Every function name must match the codebase convention. Every endpoint must
include the method, path, scope, and body shape.

---

## Required Reading Before Writing a Spec

The spec author MUST read the following architecture docs before writing. These define
the pipeline's structure, conventions, and extension points:

| Doc | What it tells you |
|-----|-------------------|
| `src/wxcli/migration/CLAUDE.md` | Pipeline file map, CLI commands, known issues |
| `src/wxcli/migration/transform/CLAUDE.md` | Normalizer/mapper/analyzer architecture, pass ordering, key gotchas |
| `src/wxcli/migration/transform/mappers/CLAUDE.md` | Mapper inventory, tier system, `depends_on` conventions |
| `src/wxcli/migration/execute/CLAUDE.md` | Planner/handler/engine architecture, tier system, handler pattern, adding new handlers |
| `src/wxcli/migration/advisory/CLAUDE.md` | Advisory system: recommendation rules + cross-cutting patterns |
| `src/wxcli/migration/report/CLAUDE.md` | Report generator: score, charts, explainer, appendix sections |
| `src/wxcli/migration/cucm/CLAUDE.md` | AXL extractors, discovery pipeline, raw_data structure |

The spec author MUST also check:

- **OpenAPI specs** in `specs/` — verify endpoint paths, methods, body shapes, and scopes
  against the actual spec before documenting them in the spec
- **Existing mappers** in `src/wxcli/migration/transform/mappers/` — check if a similar
  mapper already exists or if the new work should extend an existing one
- **Existing handlers** in `src/wxcli/migration/execute/handlers.py` — check
  `HANDLER_REGISTRY` for related handlers
- **Existing normalizers** in `src/wxcli/migration/transform/normalizers.py` — check
  `RAW_DATA_MAPPING` for existing data paths
- **Reference docs** in `docs/reference/` — the Webex API surface for the feature area

---

## Frontmatter

Every spec begins with:

```markdown
# {Feature Name}

**Date:** YYYY-MM-DD
**Status:** Spec
**Scope:** CUCM-to-Webex migration pipeline — {one-line scope description}

---
```

---

## Section 1: Problem Statement

**Purpose:** Define what's broken, why it matters, and the current pipeline state.

**Must include:**

- **What the feature does** — describe the CUCM feature and its Webex equivalent in
  concrete terms (not abstract). Include both the user-facing behavior and the admin
  configuration model.
- **Current pipeline state** — for each pipeline stage (discovery, normalization,
  mapping, analysis, advisory, report, execution), state whether it handles this
  feature and how. Use this checklist:
  - Discovery: Does the extractor pull this data? Which extractor? What raw_data key?
  - Normalization: Does a normalizer handle it? Which function in `normalizers.py`?
  - Mapping: Does a mapper produce canonical objects? Which mapper?
  - Analysis: Does an analyzer detect related issues? Which analyzer?
  - Advisory: Does an advisory pattern flag this? Which pattern?
  - Report: Does the assessment report mention it? Which section?
  - Execution: Does a handler configure it in Webex? Which handler?
- **Impact of not migrating** — concrete user-visible consequences on migration day.
  Who notices? What breaks? How visible is the failure?

**When brief is OK:** If the feature is a small enhancement to an existing pipeline
component (e.g., adding a report section), the "current pipeline state" checklist can
be shortened to cover only the affected stages.

---

## Section 2: CUCM Source Data

**Purpose:** Define exactly what data needs to be extracted from CUCM and how.

**Must include:**

- **AXL discovery** — which AXL operations or SQL queries extract the data. Include
  the actual query or method name, not just "query the database."
- **Raw data shape** — Python dict showing the exact structure of `raw_data["group"]["key"]`
  that the extractor will produce. Use real field names from AXL.
- **Extraction implementation** — which extractor class, which method, where in
  `src/wxcli/migration/cucm/extractors/`. If extending an existing extractor, name it
  and describe what to add. If creating a new extractor, justify why.

**When brief is OK:** If the data is already extracted by an existing extractor and
just needs to be consumed differently downstream, state "Already extracted by
`{ExtractorName}` as `raw_data['{group}']['{key}']`" and skip the AXL/SQL details.

---

## Section 3: Webex Target APIs

**Purpose:** Define every Webex API endpoint involved in configuring this feature.

**Must include for each endpoint:**

- HTTP method and path (e.g., `PUT /telephony/config/people/{personId}/executive/alert`)
- Required scope (e.g., `spark-admin:telephony_config_write`)
- Request body shape as JSON with real field names and example values
- Response shape if it's consumed by a later step
- Any ordering constraints (e.g., "Step 3 must complete before steps 4-7")

**Specificity requirement:** Do not write "use the Webex API to configure X." Write
the actual endpoint path, the actual body structure, and the actual scope. The
implementer should not need to look up the API docs.

**When brief is OK:** Never. This section must always be detailed. Even for a no-op
handler (Phase A placeholder), document the future API endpoints so the Phase B
implementer has them.

---

## Section 4: Pipeline Integration

**Purpose:** Define exactly how the feature threads through each pipeline stage.

**Must include (as applicable):**

### 4a. Normalization (Phase 04)
- New normalizer function name(s) in `normalizers.py`
- Registration in `RAW_DATA_MAPPING`: `(extractor_key, sub_key, normalizer_key)` tuple
- Object type name(s) in the store

### 4b. Cross-References (Phase 04)
- New relationships for `CrossReferenceBuilder`
- Relationship name, source type, target type

### 4c. Mapping (Phase 05)
- New or modified mapper: file path, class name, `depends_on` list
- What the mapper reads from the store (input object types)
- What it produces (output canonical type, canonical_id format)
- Decisions it creates (DecisionType, conditions, option IDs)

### 4d. Analysis (Phase 06)
- New or modified analyzer, or "no changes needed" with rationale
- If new: decision types produced, severity levels, cascade behavior

### 4e. Execution (Phase 07)
- Planner: new `_expand_{type}()` function or addition to `_DATA_ONLY_TYPES`
- Handler: function name, `HANDLER_REGISTRY` entry, `HandlerResult` structure
- Tier assignment in `__init__.py`
- API call estimate in `__init__.py`
- Dependencies: cross-object rules in `dependency.py` with `DependencyType`

**When brief is OK:** Subsections for stages that require no changes can be a single
line: "No changes needed — {reason}." Do not omit the subsection header.

---

## Section 5: Report Changes

**Purpose:** Define what changes to the assessment report (executive summary and
technical appendix).

**Must include:**

- **Executive summary changes** — new metrics, callout boxes, or stat cards. Which
  page (1-4) and where on the page.
- **Appendix changes** — new sections or additions to existing sections. Include the
  section letter (A-V currently) and describe the content: tables, counts, lists.
- **Score impact** — does this feature add a new score factor to `score.py`? If so,
  define the factor name, weight, and scoring thresholds.
- **Implementation** — which files to modify (`executive.py`, `appendix.py`,
  `score.py`, `explainer.py`) and what to add to each.

**When brief is OK:** If the feature has no report impact (rare), state "No report
changes — {reason}." More commonly, even small features need at least a count added
to an existing appendix section.

---

## Section 6: Advisory System

**Purpose:** Define new advisory patterns and/or recommendation rules.

**Must include:**

- **New advisory patterns** — for `advisory_patterns.py`:
  - Function name: `detect_{pattern_name}(store)`
  - Category: `migrate_as_is` | `rebuild` | `eliminate` | `out_of_scope`
  - Severity logic (what triggers LOW/MEDIUM/HIGH/CRITICAL)
  - Detail template text (the actual text the operator sees)
  - Position in `ALL_ADVISORY_PATTERNS` (next available number)

- **New recommendation rules** — for `recommendation_rules.py`:
  - Which DecisionType(s) are enhanced
  - Logic: when to recommend which option
  - Reasoning text template

**When brief is OK:** If the feature produces no new decisions and no new advisory
patterns, state "No advisory changes — {reason}." If it only adds to an existing
pattern, describe the delta.

---

## Section 7: Documentation Updates Required

**Purpose:** Exhaustive list of every file that needs updating after implementation.
This is the COMPLETENESS CHECK — if a file is missing from this list, it won't get
updated.

**Required format:** Tables with columns: `File`, `Section`, `What to Add`.

**Required subsections:**

### 7a. CLAUDE.md Files
Every module-level CLAUDE.md that references the changed components. Always check:
- `src/wxcli/migration/CLAUDE.md` (file map, normalizer/mapper/analyzer counts)
- `src/wxcli/migration/transform/CLAUDE.md` (normalizer list, cross-ref table)
- `src/wxcli/migration/transform/mappers/CLAUDE.md` (mapper inventory)
- `src/wxcli/migration/execute/CLAUDE.md` (handler inventory, tier system)
- `src/wxcli/migration/advisory/CLAUDE.md` (pattern list, pattern count)
- `src/wxcli/migration/report/CLAUDE.md` (report sections, appendix letters)
- `src/wxcli/migration/cucm/CLAUDE.md` (extractor details, raw_data structure)
- `/CLAUDE.md` (project root — file map, known issues)

### 7b. Reference Docs
Relevant docs in `docs/reference/` that cover the API surface being used.

### 7c. Runbooks
- `docs/runbooks/cucm-migration/operator-runbook.md`
- `docs/runbooks/cucm-migration/decision-guide.md`
- `docs/runbooks/cucm-migration/tuning-reference.md`

### 7d. Knowledge Base
Relevant docs in `docs/knowledge-base/migration/`.

### 7e. Skills
Any `.claude/skills/` files that reference the changed pipeline components.

### 7f. Models
Changes to `src/wxcli/migration/models.py` (new canonical types, DecisionType values).

**When brief is OK:** Never. Every spec must have this section fully populated. If a
subsection has no changes, include it with "No changes needed." An incomplete doc
update list means drift accumulates silently.

---

## Section 8: Test Strategy

**Purpose:** Define the test plan with enough specificity that the implementer can
write tests without re-analyzing the feature.

**Must include:**

- **Unit tests per component** — grouped by file. For each test:
  - Test function name (following `test_{component}_{scenario}` convention)
  - One-line description of what it verifies
- **Integration tests** — end-to-end scenarios that verify the feature works across
  pipeline stages.
- **Estimated test count** — a number range (e.g., "18-22 tests").

**Organize by component:**

| Component | Test file | Tests |
|-----------|-----------|-------|
| Normalizer | `tests/migration/transform/test_normalizers_{feature}.py` | ... |
| Mapper | `tests/migration/transform/mappers/test_{feature}_mapper.py` | ... |
| Analyzer | `tests/migration/transform/analyzers/test_{feature}_analyzer.py` | ... |
| Advisory | `tests/migration/advisory/test_advisory_{feature}.py` | ... |
| Handler | `tests/migration/execute/test_handlers.py` | ... |
| Planner | `tests/migration/execute/test_planner.py` | ... |
| Report | `tests/migration/report/test_{feature}.py` | ... |

**When brief is OK:** Small specs (e.g., adding one advisory pattern) can have a
shorter test section, but must still name every test function.

---

## Section 9: Risks, Open Questions, and Effort

**Purpose:** Surface implementation risks, unresolved design decisions, and effort
estimate.

**Must include:**

- **Risks** — things that could go wrong during implementation, with mitigations.
  Focus on technical risks (API behavior, data shape variability, version compatibility)
  not project risks.
- **Open questions** — design decisions that need resolution during implementation.
  Number them for easy reference. Include the author's recommendation where possible.
- **Implementation order** — numbered list of implementation steps in dependency order.
  The implementer follows this order.
- **Effort estimate** — table with component, estimated lines of code, and effort
  level (Small/Medium/Large). Include a total.

**When brief is OK:** Simple specs can have 1-2 risks and 0-1 open questions. The
implementation order and effort estimate are always required.

---

## Section Checklist

Before submitting a spec for review, verify:

- [ ] All file paths are real (check with `ls` or `glob`)
- [ ] All function names follow codebase conventions (`normalize_*`, `handle_*_*`, `detect_*`)
- [ ] All API endpoints include method, path, scope, and body shape
- [ ] All canonical_id formats follow existing conventions (`type:name` or `type:hash`)
- [ ] All DecisionType values are either existing or clearly marked as new
- [ ] All CLAUDE.md files that reference changed components are in Section 7
- [ ] All three runbook files are checked in Section 7c
- [ ] Section 8 names every test function
- [ ] Section 9 has an implementation order
- [ ] The spec passes the quality gate: implementable without clarifying questions
