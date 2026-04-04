# Migration Advisory System

Practitioner-level architectural advisory for CUCM-to-Webex Calling migrations. Two layers that add judgment to the pipeline's mechanical decision-making.

## Architecture

```
analysis_pipeline.py run()
    │
    ├── Phase 1: 12 existing analyzers → merge decisions into store
    │
    ├── Phase 2: ArchitectureAdvisor → reads merged decisions + full inventory
    │            → produces ARCHITECTURE_ADVISORY decisions → merge (separate stage)
    │
    └── Phase 3: populate_recommendations() → enriches ALL decisions with recommendations
                 │
                 ▼
         advisory/
            ├── recommendation_rules.py  (Layer 1: per-decision)
            ├── advisory_patterns.py     (Layer 2: cross-cutting)
            └── advisor.py               (ArchitectureAdvisor class)
```

**Layer 1 — Per-Decision Recommendations.** Every decision the pipeline produces (from mappers and analyzers) gets an optional `recommendation` field: which option the system advises, and `recommendation_reasoning`: why. Populated by `populate_recommendations()` which calls into `recommendation_rules.py`. One function per DecisionType (16 total). Returns `(option_id, reasoning)` or `None` for genuinely ambiguous cases.

**Layer 2 — Cross-Cutting Advisor.** The `ArchitectureAdvisor` runs after all 12 analyzers have merged their decisions. It reads the full canonical model plus all prior decisions and produces `ARCHITECTURE_ADVISORY` decisions for patterns spanning multiple objects — things like "6 of your 14 CSSes are restriction-only and should be calling permissions, not dial plans" or "your trunk topology indicates Local Gateway, not Cloud Connected PSTN."

## Why Two Phases

The ArchitectureAdvisor needs to read decisions from the first 12 analyzers (e.g., Pattern 4 groups DEVICE_INCOMPATIBLE decisions by model for bulk upgrade planning). In a single-phase design, analyzer decisions aren't in the store until after ALL analyzers run — so the ArchitectureAdvisor would see nothing. The two-phase approach merges Phase 1 decisions first, then runs Phase 2 against the populated store.

Advisory decisions are merged separately using `decision_types=[ARCHITECTURE_ADVISORY]` and `stage="advisory"` so they don't stale-mark the Phase 1 decisions.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Exports `populate_recommendations()` and `ArchitectureAdvisor` |
| `recommendation_rules.py` | 19 recommendation functions (one per DecisionType) + `RECOMMENDATION_DISPATCH` dict |
| `advisory_patterns.py` | 20 cross-cutting pattern detectors + `AdvisoryFinding` dataclass + `ALL_ADVISORY_PATTERNS` list |
| `advisor.py` | `ArchitectureAdvisor` class (extends Analyzer ABC) |

## Decision Model Fields

Two fields added to `Decision` in `models.py`:
- `recommendation: str | None` — the `id` of the recommended option (e.g., `"call_queue"`, `"convert"`)
- `recommendation_reasoning: str | None` — 1-3 sentences explaining why

Both are display-only — NOT part of the fingerprint. They can change across runs without invalidating resolved decisions. Stored in the `decisions` table as nullable TEXT columns.

One enum value added: `DecisionType.ARCHITECTURE_ADVISORY`

## Per-Decision Recommendations (Layer 1)

`recommendation_rules.py` has one function per DecisionType:

```python
def recommend_{type_name}(context: dict, options: list[dict]) -> tuple[str, str] | None:
```

The `RECOMMENDATION_DISPATCH` dict maps type strings to functions. `populate_recommendations()` iterates all decisions in the store, calls the dispatch function, and writes results via `store.update_recommendation()`.

**Key rules by type:**
- `FEATURE_APPROXIMATION`: Queue features enabled → Call Queue. >8 agents → Call Queue. ≤4 agents top-down → Hunt Group. 5-8 ambiguous → None.
- `DEVICE_INCOMPATIBLE`: Model-to-replacement lookup (7811→9841, 7832→room device, ATA 190→ATA 192). Includes firmware type (MPP vs RoomOS) in reasoning.
- `CSS_ROUTING_MISMATCH`: Partition ordering dependency → "manual" with explanation. Scope difference → "use_union" unless it creates conflicts.
- `MISSING_DATA`: Almost always "skip" with remediation guidance. Trunk password → "generate".

Ambiguous cases return `None`. Honest uncertainty is a feature.

## Cross-Cutting Advisory Patterns (Layer 2)

`advisory_patterns.py` has 26 pattern detector functions. Each takes a `MigrationStore` and returns `list[AdvisoryFinding]`.

**Critical patterns (highest migration impact):**
1. **Partition Ordering Loss** — CSSes that depend on partition ordering to resolve overlapping patterns. Webex uses longest-match routing — no ordering equivalent. Calls may route differently after migration.
2. **CPN Transformation Chain** — Route patterns and trunks with calling/called party transformations. CUCM chains transformations across 5 levels. Webex has flat caller ID per user/location.
3. **PSTN Connection Type** — Classifies trunk topology into Local Gateway, Cloud Connected PSTN, or Premises-based PSTN. Drives the entire Webex routing architecture.

**Eliminate patterns (CUCM workarounds to remove):**
4. Restriction CSS Consolidation — CSSes with only blocking patterns → calling permission policies
5. Translation Pattern Elimination — Digit normalization handled natively by Webex location settings
6. Partition-Based Time Routing — Time schedule→partition→CSS chain → AA business hours schedule
7. Over-Engineered Dial Plan — Patterns matching Webex's built-in extension routing
8. Voicemail Pilot Simplification — Multiple pilots to same VM system → Webex location-level voicemail

**Rebuild patterns (use Webex-native approach):**
9. Hunt Pilot Behavioral Reclassification — HGs with queue-like behavior → Call Queues
10. Location Consolidation — Multiple device pools same tz+region → fewer Webex locations
11. Shared Line Simplification — Monitoring-only appearances → virtual extensions
12. Trunk Destination Consolidation — Multiple trunks same destination → single Webex trunk

**Informational / out-of-scope:**
13. Device Bulk Upgrade Planning — Groups incompatible devices by model with replacement options
14. Globalized vs. Localized Dial Plan — Detects dial plan style to guide migration approach
15. Media Resource Scope Removal — MRGLs, conference bridges, transcoders → cloud-managed, skip
16. E911/CER Migration Flag — Emergency services require separate workstream

**Tier 4 feature gap patterns:**
17. Recording Enabled Users — phones with recordingFlag enabled → configure Webex recording
18. SNR Configured Users — remote destination profiles → manual Webex SNR setup
19. Transformation Patterns — calling/called party transformations → manual caller ID review
20. Extension Mobility Usage — device profiles → Webex hot desking configuration

## AdvisoryFinding Dataclass

```python
@dataclass
class AdvisoryFinding:
    pattern_name: str           # "restriction_css_consolidation"
    severity: str               # "CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"
    summary: str                # One-liner for decision summary
    detail: str                 # 2-5 sentences of reasoning
    affected_objects: list[str] # canonical_ids
    recommendation: str         # Always "accept" for advisories
    recommendation_reasoning: str
    category: str               # "migrate_as_is" | "rebuild" | "eliminate" | "out_of_scope"
```

The `category` field classifies advisories into the migration decision framework: migrate as-is, rebuild using Webex-native patterns, eliminate (CUCM workaround), or out-of-scope (separate workstream).

## Implementation Notes

**Pattern 1 uses `blockEnable`, not `classify_block_pattern()`.** The spec says to use `classify_block_pattern()` from `cucm_pattern.py`, but that function requires a `category_rules` list from the migration config. Using `pre_migration_state.blockEnable` is more direct and robust — it detects blocking patterns without config dependency. Code review approved this deviation.

**Pattern 9 groups by voicemail system before firing.** Uses the first 3 digits of pilot number + CSS name as a grouping key. Only fires when all pilots share the same key (i.e., point to the same VM system). Prevents false positives on deployments with genuinely independent voicemail systems.

**Pattern 11 `affected_objects` includes CSS + partition + route pattern IDs.** Not just CSS IDs — the partitions and route patterns involved in ordering conflicts are also tracked for traceability.

**Pattern 16 (E911) always fires**, even on empty stores. When no E911 signals are detected, it produces a warning that CER data may not be visible via AXL. This is by design per the spec's "if detection data is sparse" guidance.

**Test count:** 81 tests (35 pattern + 7 advisor + 39 new-pattern/rule tests). The prompt estimated ~50; the actual count is lower because some patterns share positive/negative cases and the simpler patterns need fewer test scenarios.

## Pipeline Integration (Phase 13d — COMPLETE)

In `analysis_pipeline.py`, the `run()` method has steps 5-6 after the original 4:
1. Run 12 existing analyzers (unchanged)
2. Convert to store dicts and merge (unchanged)
3. Apply auto-rules (unchanged)
4. Apply auto-resolution rules (unchanged)
5. Run ArchitectureAdvisor → merge advisory decisions separately (`decision_types=[ARCHITECTURE_ADVISORY]`, `stage="advisory"`)
6. `populate_recommendations()` → enrich all decisions

Advisory decisions do NOT trigger cascades. Resolving an advisory does not re-run any analyzer. Stats dict includes `architecture_advisor` key.

## CLI Integration (Phase 13d — COMPLETE)

- `wxcli cucm decisions` shows `[REC: option]` tag on decisions with recommendations (in a Recommendations section below the table)
- `wxcli cucm decisions --type advisory` filters to ARCHITECTURE_ADVISORY only (shorthand mapping)
- JSON export includes `recommendation` and `recommendation_reasoning` fields

## Skill Integration (Phase 13d — COMPLETE)

The `cucm-migrate` skill's decision review has two phases:
- **Phase A:** Present advisories grouped by category (eliminate, rebuild, out_of_scope, migrate_as_is) with bulk accept
- **Phase B:** Present per-decision items as auto_apply, recommended (with bulk accept and reasoning), or needs_input

## Adding New Patterns

To add a new advisory pattern:
1. Write a function `detect_{name}(store: MigrationStore) -> list[AdvisoryFinding]` in `advisory_patterns.py`
2. Register it in `ALL_ADVISORY_PATTERNS`
3. Add tests in `tests/migration/advisory/test_advisory_patterns.py`

To add a new recommendation rule:
1. Add logic to the existing function for that DecisionType in `recommendation_rules.py`
2. Add tests in `tests/migration/advisory/test_recommendation_rules.py`

No framework changes needed for either. The knowledge base grows by adding functions.

## Design Spec

Full design: `docs/superpowers/specs/2026-03-24-migration-advisory-design.md`

Build prompts: `docs/prompts/phase-13a` through `phase-13d`
