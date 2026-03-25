# CUCM Assessment Report — Phase A: Foundation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the data foundation: test fixtures, collector file ingestion, and the complexity score algorithm. Everything in Phases B and C depends on this.

**Architecture:** Two new modules in `src/wxcli/migration/report/`: `ingest.py` (reads collector files into the existing pipeline's raw_data format) and `score.py` (reads from SQLite store, returns a 0-100 complexity score with factor breakdown). One modification to `src/wxcli/commands/cucm.py` adds `--from-file` to the discover command.

**Tech Stack:** Python 3.11, existing MigrationStore (SQLite), gzip for compressed files.

**Spec:** `docs/superpowers/specs/2026-03-24-cucm-assess-design.md`
**Master plan:** `docs/superpowers/plans/2026-03-24-cucm-assess-report.md`
**Next phase:** `docs/superpowers/plans/2026-03-24-cucm-assess-phase-b.md` (SVG charts, explainer, CSS)

---

## File Map

| File | Purpose |
|------|---------|
| **Create:** `src/wxcli/migration/report/__init__.py` | Package init, exports `ingest_collector_file` |
| **Create:** `src/wxcli/migration/report/ingest.py` | Collector file reader + AXL→raw_data key mapping |
| **Create:** `src/wxcli/migration/report/score.py` | Complexity score algorithm (7 weighted factors → 0-100) |
| **Modify:** `src/wxcli/commands/cucm.py:374-451` | Add `--from-file` flag to discover command |
| **Create:** `tests/migration/report/__init__.py` | Test package init |
| **Create:** `tests/migration/report/conftest.py` | Shared fixtures (populated MigrationStore, sample collector file) |
| **Create:** `tests/migration/report/test_from_file.py` | File ingestion tests |
| **Create:** `tests/migration/report/test_score.py` | Score algorithm tests |

---

### Task 1: Test Fixtures + `--from-file` Ingestion

**Files:**
- Create: `tests/migration/report/__init__.py`
- Create: `tests/migration/report/conftest.py`
- Create: `src/wxcli/migration/report/__init__.py`
- Create: `src/wxcli/migration/report/ingest.py`
- Create: `tests/migration/report/test_from_file.py`
- Modify: `src/wxcli/commands/cucm.py:374-451` (add `--from-file` to discover)

This task creates the shared test fixtures all subsequent tasks use, plus the file ingestion path that lets SEs load collector output files.

- [ ] **Step 1: Create test + report packages**

Create empty `tests/migration/report/__init__.py` and `src/wxcli/migration/report/__init__.py`.

- [ ] **Step 2: Write conftest.py with populated store fixture**

Create `tests/migration/report/conftest.py` with a `populated_store` fixture. This builds a realistic MigrationStore simulating a post-analyze state with:
- 3 locations (Dallas HQ, Austin Branch, London Office)
- 50 users across locations (25/15/10)
- 45 devices (40 native MPP CP-8845, 3 convertible CP-7841, 2 incompatible CP-7962G)
- 6 features (2 hunt groups, 1 AA, 1 call queue, 1 call park, 1 pickup group)
- Routing (2 trunks, 1 route group, 1 dial plan)
- 3 CSSes with 5 partitions, cross-refs wired
- 5 decisions (2 FEATURE_APPROXIMATION, 1 CSS_ROUTING_MISMATCH, 1 DEVICE_INCOMPATIBLE auto-resolved, 1 SHARED_LINE_COMPLEX)
- All stages marked complete through `analyze`

Also add a `sample_collector_file` fixture that writes a minimal gzipped JSON collector file to tmp_path.

Verify the store fixture methods match the actual `MigrationStore` API — read `src/wxcli/migration/store.py` for exact method signatures before writing. If `upsert_raw()` doesn't exist, construct `MigrationObject` instances and use `upsert_object()`. Note: MigrationObject subclasses require a `Provenance` field (with `source_system`, `source_id`, `source_name`, `extracted_at`) — read `src/wxcli/migration/models.py` for the exact class and include it in all fixture objects.

- [ ] **Step 3: Write failing tests for file ingestion**

Create `tests/migration/report/test_from_file.py` with tests:
- `test_ingest_collector_file_reads_gzip` — loads .json.gz, returns dict with expected keys
- `test_ingest_collector_file_reads_plain_json` — loads .json (uncompressed)
- `test_ingest_collector_file_rejects_invalid` — missing `collector_version` raises ValueError
- `test_collector_to_raw_data_mapping` — verifies key mappings match discovery.py raw_data contract

- [ ] **Step 4: Run tests to verify they fail**

Run: `pytest tests/migration/report/test_from_file.py -v`
Expected: FAIL — `ingest` module doesn't exist.

- [ ] **Step 5: Implement ingest.py**

Create `src/wxcli/migration/report/ingest.py` with:
- `COLLECTOR_TO_RAW_DATA_MAP` — dict mapping AXL names to `(extractor_group, sub_key)` tuples. Source for correct mappings: `src/wxcli/migration/cucm/discovery.py` lines 51-71 (DiscoveryResult.raw_data contract).
- `ingest_collector_file(file_path) -> dict` — reads .json.gz or .json, validates required keys (`collector_version`, `cucm_version`, `cluster_name`, `collected_at`, `objects`), maps collector keys to raw_data format, returns dict matching DiscoveryResult.raw_data structure.

Export both from `__init__.py`.

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/migration/report/test_from_file.py -v`
Expected: All PASS.

- [ ] **Step 7: Add `--from-file` to discover CLI command**

Modify `src/wxcli/commands/cucm.py` discover function:
1. Add `from_file: Optional[str] = typer.Option(None, "--from-file", help="Path to collector file (.json.gz or .json)")` parameter
2. Make `--host`, `--username`, `--password` optional (default None) so they aren't required with `--from-file`
3. Add validation: if neither `--from-file` nor `--host` provided, print error and exit
4. When `--from-file` is set: call `ingest_collector_file()`, write result to `project_dir / "raw_data.json"`, record journal entry, mark discover stage complete, print summary of loaded objects, return early (skip AXL connection)

Read the existing discover function carefully before modifying — preserve all existing behavior for the live-AXL path.

- [ ] **Step 8: Commit**

```bash
git add src/wxcli/migration/report/ tests/migration/report/ src/wxcli/commands/cucm.py
git commit -m "feat(cucm): add --from-file ingestion + report package scaffold"
```

---

### Task 2: Complexity Score Algorithm

**Files:**
- Create: `src/wxcli/migration/report/score.py`
- Create: `tests/migration/report/test_score.py`

Pure computation — no HTML, no SVG. Takes a MigrationStore, queries it, returns a score and factor breakdown.

- [ ] **Step 1: Write failing tests for score algorithm**

Create `tests/migration/report/test_score.py`:

```python
"""Tests for migration complexity score algorithm."""
import pytest


class TestComplexityScore:
    """Score should be 0-100 with 7 weighted factors."""

    def test_score_returns_int_in_range(self, populated_store):
        from wxcli.migration.report.score import compute_complexity_score
        result = compute_complexity_score(populated_store)
        assert 0 <= result.score <= 100

    def test_score_has_seven_factors(self, populated_store):
        from wxcli.migration.report.score import compute_complexity_score
        result = compute_complexity_score(populated_store)
        assert len(result.factors) == 7

    def test_score_factors_have_required_fields(self, populated_store):
        from wxcli.migration.report.score import compute_complexity_score
        result = compute_complexity_score(populated_store)
        for factor in result.factors:
            assert "name" in factor
            assert "weight" in factor
            assert "raw_score" in factor  # 0-100 before weighting
            assert "weighted_score" in factor  # raw * weight
            assert "detail" in factor  # human-readable explanation

    def test_factor_weights_sum_to_100(self, populated_store):
        from wxcli.migration.report.score import compute_complexity_score
        result = compute_complexity_score(populated_store)
        total_weight = sum(f["weight"] for f in result.factors)
        assert total_weight == 100

    def test_score_label_straightforward(self, populated_store):
        """Fixture has moderate data — should score green or low amber."""
        from wxcli.migration.report.score import compute_complexity_score
        result = compute_complexity_score(populated_store)
        assert result.label in ("Straightforward", "Moderate")
        assert result.color in ("#2E7D32", "#F57C00")

    def test_empty_store_scores_zero(self, tmp_path):
        from wxcli.migration.store import MigrationStore
        from wxcli.migration.report.score import compute_complexity_score
        store = MigrationStore(tmp_path / "empty.db")
        result = compute_complexity_score(store)
        assert result.score == 0
        assert result.label == "Straightforward"

    def test_device_factor_all_native(self, populated_store):
        """With 40/45 native MPP, device factor should be low."""
        from wxcli.migration.report.score import compute_complexity_score
        result = compute_complexity_score(populated_store)
        device_factor = next(f for f in result.factors if f["name"] == "Device Compatibility")
        assert device_factor["raw_score"] < 30  # mostly native

    def test_decision_factor_scales_with_count(self, populated_store):
        """5 decisions / 50+ objects = low density."""
        from wxcli.migration.report.score import compute_complexity_score
        result = compute_complexity_score(populated_store)
        decision_factor = next(f for f in result.factors if f["name"] == "Decision Density")
        assert decision_factor["raw_score"] < 40
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/migration/report/test_score.py -v`
Expected: FAIL — `score` module doesn't exist.

- [ ] **Step 3: Implement score.py**

Create `src/wxcli/migration/report/score.py`:

Key design:
- `ScoreResult` dataclass with `score: int`, `label: str`, `color: str`, `factors: list[dict]`
- `compute_complexity_score(store: MigrationStore) -> ScoreResult` — main entry point
- 7 private factor functions, each returning `(raw_score: int, detail: str)`:
  1. `_css_complexity(store)` — count CSSes, avg partitions per CSS via `css_contains_partition` cross-refs, check for CSS_ROUTING_MISMATCH and CALLING_PERMISSION_MISMATCH decisions
  2. `_feature_parity(store)` — count FEATURE_APPROXIMATION decisions relative to total features
  3. `_device_compatibility(store)` — query all device objects, count by `compatibility_tier` field in data JSON
  4. `_decision_density(store)` — total unresolved decisions / total objects * 100, log-scaled
  5. `_scale_factor(store)` — `math.log10(max(user_count, 1)) * 10`, capped at 100
  6. `_shared_line_complexity(store)` — count SHARED_LINE_COMPLEX decisions, shared line objects
  7. `_routing_complexity(store)` — count trunks, route groups, translation patterns

Weights: `[25, 20, 15, 15, 10, 10, 5]`

Label thresholds: 0-30 = "Straightforward" (#2E7D32), 31-55 = "Moderate" (#F57C00), 56-100 = "Complex" (#C62828)

Read from store using `store.count_by_type()`, `store.get_all_decisions()`, `store.get_cross_refs()`, and `store.get_objects()`. Device compatibility_tier is available directly as `obj["compatibility_tier"]` — `get_objects()` returns already-parsed dicts, no need for `json.loads()`.

Note: `store.get_objects(type)` returns `list[dict]` with the data already deserialized. `store.query_by_type(type)` returns `list[MigrationObject]` (Pydantic models). Use `get_objects()` for dict access.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/migration/report/test_score.py -v`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add src/wxcli/migration/report/score.py tests/migration/report/test_score.py
git commit -m "feat(report): add migration complexity score algorithm"
```

---

## Phase A Verification

After both tasks complete:

```bash
pytest tests/migration/report/ -v
```

Expected: All ingestion + score tests pass. The `report/` package exists with `ingest.py` and `score.py`. The `--from-file` flag works on `wxcli cucm discover`.

**Next:** Run Phase B (`docs/superpowers/plans/2026-03-24-cucm-assess-phase-b.md`) — SVG charts, decision explainer, CSS template. Tasks 3-5 can run in parallel.
