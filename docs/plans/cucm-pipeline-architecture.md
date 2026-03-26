# CUCM→Webex Migration Pipeline Architecture

Design decisions for the normalize → analyze → plan pipeline.
Companion to [`docs/plans/cucm-wxc-migration.md`](cucm-wxc-migration.md) (the full migration design).

## How to use this document

Start here to understand the overall architecture. Each section below summarizes one design decision and links to its detailed spec. When implementing a stage, read the relevant detail doc — don't try to load all 7 at once.

---

## Architecture Summary

The pipeline transforms raw CUCM data into an executable Webex Calling migration plan through three stages:

```
Discovery (raw CUCM dicts)
    │
    ▼
Normalize ──► Pass 1: stateless CUCM→canonical (per-object)
    │         Pass 2: cross-reference resolution (full inventory)
    │
    ▼
Analyze ───► 12 independent analyzers sweep inventory
    │         produce decisions (conflicts, ambiguities, choices)
    │         auto-rules resolve obvious cases
    │
    ▼
Plan ──────► Expand objects into operations
             Build dependency DAG (NetworkX)
             Topological sort into tiers
             Partition into site-based batches
```

### Cross-cutting concerns

- **Storage**: SQLite database (`migration.db`) — single source of truth for all stages
- **Decisions**: Fingerprint-based identity, three-way merge on re-analyze, cascading re-evaluation
- **Idempotency**: Every stage is re-runnable. Resolved decisions survive re-analysis.

---

## 1. Data Representation

**Decision:** SQLite as primary store, JSON export for human inspection.

Why: ACID transactions for crash safety, SQL JOINs for cross-referencing (the analyze stage needs these heavily), indexes for O(1) lookups on 50K+ objects. JSON files are derived views via `wxcli cucm export`, not source of truth.

Key tables: `objects`, `cross_refs`, `decisions`, `journal`

**Detail:** [`cucm-pipeline/01-data-representation.md`](cucm-pipeline/01-data-representation.md)

---

## 2. Normalization Architecture

**Decision:** Two-pass ELT. Pass 1 is stateless (one CUCM dict in → one canonical Pydantic model out). Pass 2 builds cross-reference indexes and enriches using SQL.

Why: Stateless normalizers are testable in isolation, order-independent, and parallel-safe. Cross-referencing (shared line detection, CSS graph building, device pool→location resolution) needs the full inventory in SQLite.

Key classes: normalizer functions (pass 1), `CrossReferenceBuilder` (pass 2)
Key library: `phonenumbers` for E.164 normalization

**Detail:** [`cucm-pipeline/02-normalization-architecture.md`](cucm-pipeline/02-normalization-architecture.md)

---

## 3. Conflict Detection Engine — BUILT (Phase 06)

**Decision:** Pipeline of 12 independent analyzer classes (linter pattern). Not a rule engine, not a constraint solver.

Why: Each analyzer is a self-contained sweep — no rule interaction. Independent = testable, pluggable, parallelizable. Auto-resolution rules handle obvious cases (incompatible devices → skip).

Key boundary: Analyzers operate on CUCM data only (offline). Webex-side conflict checks (number collisions, cross-system duplicate users) are deferred to preflight (online).

Key classes: `Analyzer` base class (`transform/analyzers/__init__.py`), `AnalysisPipeline` (`transform/analysis_pipeline.py`), 12 concrete analyzers (`transform/analyzers/*.py`)

Decision ownership: 3 analyzer-owned types (EXTENSION_CONFLICT, SHARED_LINE_COMPLEX, DUPLICATE_USER) — analyzers are sole producers. 9 mapper-owned types — analyzers check for existing mapper decisions before creating duplicates.

Pipeline sequence: sort by depends_on → run each analyzer → merge_decisions() (fingerprint-based) → apply_auto_rules(). Also provides `resolve_and_cascade()` for cascading re-evaluation on decision resolution.

**Detail:** [`cucm-pipeline/03-conflict-detection-engine.md`](cucm-pipeline/03-conflict-detection-engine.md)

---

## 4. CSS Decomposition Algorithm

**Decision:** Classify partitions (DIRECTORY/ROUTING/BLOCKING/MIXED) → compute routing scope per CSS → compute restriction profile per CSS → detect ordering conflicts via pattern overlap analysis.

Why: CUCM's CSS is a single ordered mechanism controlling both routing and restrictions. Webex separates these into org-wide dial plans (flat) and per-user permissions (category-based). Decomposition requires partition classification, set intersection for safe routing baseline, and firewall-rule-style shadowing detection.

Key module: `transform/cucm_pattern.py` — dedicated CUCM digit pattern matching (not a helper function, needs its own test suite)
Key insight: Use intersection (not union) of routing scopes as the org-wide baseline to avoid silently granting access.

**Detail:** [`cucm-pipeline/04-css-decomposition.md`](cucm-pipeline/04-css-decomposition.md)

---

## 5. Dependency Graph Construction

**Decision:** NetworkX DiGraph. Static tiers for inter-type ordering, DAG for intra-tier ordering and validation. Batch by org-wide first, then site-by-site.

Why: Static tiers (0-6) give deterministic coarse scheduling. The DAG catches intra-tier dependencies (AA B references HG A → A before B). Cycle detection with safety rails: all-REQUIRES cycles error to the user, SOFT/CONFIGURES cycles break to a tier 7 fixup pass.

Key function: `expand_to_operations()` — bridges analyzed inventory to executable plan
Key tables: `plan_operations`, `plan_edges`

**Detail:** [`cucm-pipeline/05-dependency-graph.md`](cucm-pipeline/05-dependency-graph.md)

---

## 6. Decision Workflow

**Decision:** Rich CLI tables for browsing, interactive prompts (questionary) for resolving, CSV import/export for stakeholder review workflows. Not a TUI, not a web UI.

Why: User is already in a CLI workflow. Bulk resolve shows full summary before confirmation. Cascading re-evaluation: resolving one decision can trigger re-analysis of dependent decision types.

Key model: `Decision` with `cascades_to`, `fingerprint`, `affected_objects`
Key feature: Reverse lookup — `wxcli cucm inventory -o detail` shows which decisions affect each object

**Detail:** [`cucm-pipeline/06-decision-workflow.md`](cucm-pipeline/06-decision-workflow.md)

---

## 7. Idempotency and Resumability — BUILT (Phase 01 + 06)

**Decision:** Fingerprint-based decision identity with three-way merge on re-analyze. Four-state object progression (discovered → normalized → analyzed → planned).

Why: Users will re-discover and re-analyze as they fix CUCM issues. Resolved decisions must survive re-analysis if the underlying data hasn't changed. Fingerprints are computed by the analyzer that created the decision (required abstract method — can't forget).

Key algorithm: `store.merge_decisions()` — three-way merge using fingerprint as key (five-way classification: kept/updated/new/stale/invalidated)
Key table: `merge_log` — full audit trail of what changed between runs
Stale sentinel: `chosen_option = '__stale__'` marks decisions whose condition no longer exists

**Detail:** [`cucm-pipeline/07-idempotency-resumability.md`](cucm-pipeline/07-idempotency-resumability.md)

---

## Dependencies introduced

| Library | Purpose | Existing? |
|---------|---------|-----------|
| `sqlite3` (stdlib) | Primary data store | Yes |
| `networkx` | Dependency DAG | New |
| `phonenumbers` | E.164 normalization | New |
| `questionary` or `InquirerPy` | Interactive decision prompts | New |
| `rich` | CLI tables and formatting | Already available via typer[all] |

## On-disk layout

```
~/.wxcli/migrations/<project_id>/
  migration.db              # SQLite — all objects, cross_refs, decisions, journal, plan
  state.json                # State machine position (tiny, always JSON)
  config.json               # Migration config (country code, coexistence strategy, auto-rules)
  exports/                  # JSON/CSV views generated by 'wxcli cucm export'
  snapshots/                # Webex pre-migration state (for rollback)
  reports/                  # Generated markdown reports
```
