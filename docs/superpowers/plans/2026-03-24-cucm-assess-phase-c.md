# CUCM Assessment Report — Phase C: Report Assembly

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Assemble the final report: executive summary HTML, technical appendix HTML, report assembler, CLI command, and end-to-end tests. This is the deliverable — the PDF that Sales Engineers hand to customers.

**Architecture:** Two HTML generators (`executive.py`, `appendix.py`) consume Phase A modules (score) and Phase B modules (charts, explainer, styles). The assembler (`assembler.py`) wraps them in a complete HTML document. The CLI command (`wxcli cucm report`) wires everything to the terminal.

**Tech Stack:** Python 3.11, existing MigrationStore (SQLite), modules from Phase A (score) and Phase B (charts, explainer, styles). Optional headless Chromium for `--pdf`.

**Spec:** `docs/superpowers/specs/2026-03-24-cucm-assess-design.md`
**Master plan:** `docs/superpowers/plans/2026-03-24-cucm-assess-report.md`
**Prerequisites:** Phase A complete (ingest, score, conftest fixtures), Phase B complete (charts, explainer, styles)

## Notes from Phase A (read before implementing)

1. **`ScoreResult` is a dataclass**, not a dict — import from `wxcli.migration.report.score`. Fields: `.score`, `.label`, `.color`, `.factors` (list of dicts with keys `name`, `weight`, `raw_score`, `weighted_score`, `detail`).
2. **Device `compatibility_tier` is a lowercase string** in store dicts, not the enum — values are `"native_mpp"`, `"convertible"`, `"incompatible"`. The `get_objects()` method returns deserialized dicts, not Pydantic models.
3. **CSS and partition are intermediate object types** — they use the `canonical_id` prefix convention for type detection: `css:CSS-Internal`, `partition:PT-Internal`. Query with `store.count_by_type("css")` / `store.get_objects("css")`.
4. **The `populated_store` fixture** is in `tests/migration/report/conftest.py` and is automatically available to all Phase C tests in the same directory — no import needed.

---

## File Map

| File | Purpose |
|------|---------|
| **Create:** `src/wxcli/migration/report/executive.py` | Executive summary HTML (pages 1-4) |
| **Create:** `src/wxcli/migration/report/appendix.py` | Technical appendix HTML (9 conditional sections) |
| **Create:** `src/wxcli/migration/report/assembler.py` | Combines CSS + executive + appendix into single HTML file |
| **Modify:** `src/wxcli/commands/cucm.py` | Add `report` command |
| **Create:** `tests/migration/report/test_executive.py` | Executive summary section tests |
| **Create:** `tests/migration/report/test_appendix.py` | Appendix section tests |
| **Create:** `tests/migration/report/test_assembler.py` | Full report assembly tests |
| **Create:** `tests/migration/report/test_e2e.py` | End-to-end pipeline tests |

---

### Task 6: Executive Summary HTML Generator

**Files:**
- Create: `src/wxcli/migration/report/executive.py`
- Create: `tests/migration/report/test_executive.py`

Generates the 2-4 page executive summary HTML. Depends on Phase A (score) and Phase B (charts, explainer).

- [ ] **Step 1: Write failing tests**

Create `tests/migration/report/test_executive.py`:

```python
"""Tests for executive summary HTML generation."""
import pytest


class TestExecutiveSummary:
    def test_returns_html_string(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "<section" in html
        assert "</section>" in html

    def test_contains_complexity_score(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "<svg" in html  # gauge chart
        assert "Straightforward" in html or "Moderate" in html

    def test_contains_brand_name(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "Acme Corp" in html

    def test_contains_environment_snapshot(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "50" in html  # user count
        assert "45" in html  # device count

    def test_contains_phone_compatibility_chart(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "Native MPP" in html
        assert "Convertible" in html
        assert "Incompatible" in html

    def test_contains_site_breakdown(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "Dallas" in html or "loc_dallas" in html

    def test_contains_decision_summary(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "Auto-resolved" in html or "auto-resolved" in html
        assert "Decision" in html or "decision" in html

    def test_contains_feature_mapping_table(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "Hunt Group" in html
        assert "Auto Attendant" in html

    def test_contains_plain_english_decisions(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        # Should use explainer, not raw decision type names
        assert "CSS_ROUTING_MISMATCH" not in html
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/migration/report/test_executive.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement executive.py**

Create `src/wxcli/migration/report/executive.py`:

One public function: `generate_executive_summary(store: MigrationStore, brand: str, prepared_by: str, cluster_name: str = "", cucm_version: str = "") -> str`

Returns an HTML string containing `<section>` elements for each page:

**Page 1 — The Headline:**
- Calls `compute_complexity_score(store)` → score, label, color, factors
- Calls `gauge_chart(score, color, label)` → SVG
- Builds one-paragraph summary by querying store for counts
- Environment snapshot table (CUCM version, cluster, total objects, sites, date)

**Page 2 — What You Have:**
- Queries `store.get_objects()` for each type, builds inventory data
- Calls `horizontal_bar_chart()` for object inventory
- Queries device objects, groups by `compatibility_tier`, calls `donut_chart()` for phone compatibility
- Builds per-site breakdown table by grouping objects by `location_id`
- Per-site complexity: use simplified counts (user count, device count, decision count for that site) rather than calling `compute_complexity_score()` per site — the scoring function operates on the full store, not filtered subsets. Map the simplified counts to labels: 0 decisions = "Straightforward", 1-2 = "Moderate", 3+ = "Complex".

**Page 3 — What Needs Attention:**
- Queries `store.get_all_decisions()`, groups by resolution status
- Calls `traffic_light_boxes()` for decision summary
- Gets top 5 unresolved decisions (highest severity first)
- Calls `explain_decision()` for each → plain-English blocks
- Builds feature mapping table from feature-type objects + FEATURE_APPROXIMATION decisions

**Page 4 — Next Steps (conditional):**
- Only generated if > 100 objects or > 3 sites
- Prerequisites checklist (license count, number count, decision count)
- Call to action with `prepared_by` name

All HTML uses semantic elements (`<section>`, `<table>`, `<h2>`, `<p>`) with CSS classes matching `styles.py`. No inline styles except on SVG elements.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/migration/report/test_executive.py -v`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add src/wxcli/migration/report/executive.py tests/migration/report/test_executive.py
git commit -m "feat(report): add executive summary HTML generator"
```

---

### Task 7: Technical Appendix HTML Generator

**Files:**
- Create: `src/wxcli/migration/report/appendix.py`
- Create: `tests/migration/report/test_appendix.py`

Generates the variable-length technical appendix. Each section is wrapped in `<details>/<summary>` for collapsibility. Sections are only generated if relevant data exists.

- [ ] **Step 1: Write failing tests**

Create `tests/migration/report/test_appendix.py`:

```python
"""Tests for technical appendix HTML generation."""
import pytest


class TestAppendix:
    def test_returns_html_string(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert "<section" in html

    def test_contains_object_inventory(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert "Object Inventory" in html
        assert "<table" in html

    def test_contains_decision_detail(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert "Decision Detail" in html
        assert "FEATURE_APPROXIMATION" in html or "Feature Approximation" in html

    def test_contains_device_inventory(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert "Device Inventory" in html
        assert "CP-8845" in html

    def test_uses_details_summary_elements(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert "<details" in html
        assert "<summary>" in html

    def test_skips_empty_sections(self, tmp_path):
        """Appendix for empty store should have minimal content."""
        from wxcli.migration.store import MigrationStore
        from wxcli.migration.report.appendix import generate_appendix
        store = MigrationStore(tmp_path / "empty.db")
        html = generate_appendix(store)
        # Should not have device inventory if no devices
        assert "Device Inventory" not in html or "No devices" in html

    def test_css_partition_analysis(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert "CSS" in html and "Partition" in html

    def test_routing_topology(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert "Routing" in html
        assert "PSTN Trunk" in html or "trunk" in html.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/migration/report/test_appendix.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement appendix.py**

Create `src/wxcli/migration/report/appendix.py`:

One public function: `generate_appendix(store: MigrationStore) -> str`

9 private section generators, each returning `str` (HTML fragment) or empty string if no data:

1. `_object_inventory(store)` — tables grouped by type and by location. Uses `store.get_objects(type)` for each type, groups by location_id.
2. `_decision_detail(store)` — every decision with context, options, severity. Groups by DecisionType. Uses `store.get_all_decisions()`.
3. `_css_partition_analysis(store)` — text-based topology (CSS → partitions → patterns via cross-refs). Uses `store.get_cross_refs(relationship="css_contains_partition")` and `partition_has_pattern`.
4. `_device_inventory(store)` — full phone model list with compatibility tier. Groups by tier. Shows firmware conversion steps for convertible, replacements for incompatible.
5. `_dn_analysis(store)` — E.164 classification breakdown. Queries line objects for classification data.
6. `_user_device_line_map(store)` — cross-ref chains. Uses `user_has_device`, `device_has_dn`, `dn_in_partition` cross-refs to build chains.
7. `_routing_topology(store)` — trunk, route group, dial plan inventory tables.
8. `_voicemail_analysis(store)` — voicemail profile mapping. Queries voicemail_profile objects + VOICEMAIL_INCOMPATIBLE decisions.
9. `_data_coverage(store)` — reads journal for collection errors. If no journal data, notes "collected via live AXL extraction".

Each section is wrapped in:
```html
<details open>
  <summary>Section Title</summary>
  ... content ...
</details>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/migration/report/test_appendix.py -v`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add src/wxcli/migration/report/appendix.py tests/migration/report/test_appendix.py
git commit -m "feat(report): add technical appendix HTML generator"
```

---

### Task 8: Report Assembler + CLI Command

**Files:**
- Create: `src/wxcli/migration/report/assembler.py`
- Create: `tests/migration/report/test_assembler.py`
- Modify: `src/wxcli/commands/cucm.py` (add `report` command)

Combines everything into a single self-contained HTML file and wires the CLI.

- [ ] **Step 1: Write failing tests**

Create `tests/migration/report/test_assembler.py`:

```python
"""Tests for full report assembly."""
import pytest


class TestAssembler:
    def test_assemble_returns_complete_html(self, populated_store):
        from wxcli.migration.report.assembler import assemble_report
        html = assemble_report(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html
        assert "<style>" in html  # embedded CSS
        assert "Acme Corp" in html

    def test_html_is_self_contained(self, populated_store):
        from wxcli.migration.report.assembler import assemble_report
        html = assemble_report(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        # No external references
        assert 'href="http' not in html or 'fonts.googleapis' in html  # font CDN is OK
        assert '<script src="' not in html  # no external JS
        assert '<link rel="stylesheet" href="http' not in html

    def test_contains_executive_and_appendix(self, populated_store):
        from wxcli.migration.report.assembler import assemble_report
        html = assemble_report(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "Migration Complexity Score" in html or "Complexity" in html  # executive
        assert "Object Inventory" in html  # appendix

    def test_executive_only_flag(self, populated_store):
        from wxcli.migration.report.assembler import assemble_report
        html = assemble_report(populated_store,
            brand="Acme Corp", prepared_by="Test SE",
            executive_only=True)
        assert "Object Inventory" not in html  # no appendix
        assert "Acme Corp" in html  # executive still there

    def test_print_styles_present(self, populated_store):
        from wxcli.migration.report.assembler import assemble_report
        html = assemble_report(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "@media print" in html
        assert "@page" in html

    def test_write_report_to_file(self, populated_store, tmp_path):
        from wxcli.migration.report.assembler import assemble_report
        html = assemble_report(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        out_path = tmp_path / "report.html"
        out_path.write_text(html)
        assert out_path.exists()
        assert out_path.stat().st_size > 1000  # not trivially small
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/migration/report/test_assembler.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement assembler.py**

Create `src/wxcli/migration/report/assembler.py`:

One public function:
```python
def assemble_report(
    store: MigrationStore,
    brand: str,
    prepared_by: str,
    cluster_name: str = "",
    cucm_version: str = "",
    executive_only: bool = False,
) -> str:
```

Assembly:
1. Generate executive summary HTML via `generate_executive_summary()`
2. If not `executive_only`, generate appendix HTML via `generate_appendix()`
3. Combine into full HTML document:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CUCM Migration Assessment — {brand}</title>
  <style>{REPORT_CSS}</style>
</head>
<body>
  <header class="report-header">
    <h1>CUCM Migration Assessment</h1>
    <p class="brand">{brand}</p>
    <p class="meta">Prepared by {prepared_by} | {date}</p>
  </header>
  <main>
    {executive_html}
    {appendix_html if not executive_only}
  </main>
  <footer class="report-footer">
    <p>Generated by cucm-assess</p>
  </footer>
</body>
</html>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/migration/report/test_assembler.py -v`
Expected: All PASS.

- [ ] **Step 5: Add `report` CLI command to cucm.py**

Add to `src/wxcli/commands/cucm.py`:

```python
@app.command()
def report(
    brand: str = typer.Option(..., "--brand", help="Customer name for report header"),
    prepared_by: str = typer.Option(..., "--prepared-by", help="SE/partner name"),
    output: str = typer.Option("assessment-report", "--output", "-o",
        help="Output filename (without extension)"),
    pdf: bool = typer.Option(False, "--pdf", help="Also generate PDF via headless Chrome"),
    executive_only: bool = typer.Option(False, "--executive-only",
        help="Generate executive summary only, skip technical appendix"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
):
    """Generate a migration assessment report (HTML + optional PDF)."""
```

Implementation:
1. Resolve project dir, check that `analyze` stage is complete. Note: `report` is not in `PIPELINE_STAGES` or `STAGE_PREREQUISITES` — add it, or do a manual check by reading the stages file. The `report` command's prerequisite is `analyze` (not `plan` or `preflight` — those are for execution, not assessment).
2. Open store, read config for cluster_name/cucm_version
3. Call `assemble_report()`
4. Write to `{output}.html`
5. If `--pdf`: run `shutil.which("chromium") or shutil.which("google-chrome") or shutil.which("chrome")` — if found, run `subprocess.run([browser, "--headless", "--disable-gpu", "--print-to-pdf={output}.pdf", f"file://{output_path.absolute()}"])`. If no Chrome found, print warning with manual instructions.
6. Print success message with file path(s)

- [ ] **Step 6: Run all report tests**

Run: `pytest tests/migration/report/ -v`
Expected: All PASS.

- [ ] **Step 7: Commit**

```bash
git add src/wxcli/migration/report/assembler.py tests/migration/report/test_assembler.py \
  src/wxcli/commands/cucm.py
git commit -m "feat(cucm): add report assembler + wxcli cucm report command"
```

---

### Task 9: End-to-End Test + Polish

**Files:**
- Create: `tests/migration/report/test_e2e.py`
- Modify: `src/wxcli/migration/report/__init__.py` (public API)

Final integration test: collector file → discover --from-file → normalize → map → analyze → report.

- [ ] **Step 1: Write end-to-end test**

Create `tests/migration/report/test_e2e.py`:

```python
"""End-to-end test: collector file → pipeline → report."""
import json
import gzip
import pytest
from pathlib import Path


class TestEndToEnd:
    def test_full_pipeline_from_collector_file(self, tmp_path, sample_collector_file):
        """Ingest → normalize → map → analyze → report should produce valid HTML."""
        from wxcli.migration.report.ingest import ingest_collector_file
        from wxcli.migration.store import MigrationStore
        from wxcli.migration.transform.pipeline import normalize_discovery
        from wxcli.migration.transform.engine import TransformEngine
        from wxcli.migration.transform.analysis_pipeline import AnalysisPipeline
        from wxcli.migration.report.assembler import assemble_report

        # 1. Ingest collector file
        raw_data = ingest_collector_file(sample_collector_file)

        # 2. Store + normalize (pass 1 + pass 2)
        store = MigrationStore(tmp_path / "e2e.db")
        normalize_discovery(raw_data, store)

        # 3. Map (creates canonical objects with compatibility_tier, etc.)
        TransformEngine().run(store)

        # 4. Analyze
        AnalysisPipeline().run(store)

        # 5. Generate report

        html = assemble_report(store,
            brand="E2E Test Corp", prepared_by="Test SE")

        assert "<!DOCTYPE html>" in html
        assert "E2E Test Corp" in html
        assert "Complexity" in html.lower() or "straightforward" in html.lower()

        # Write and verify file
        out = tmp_path / "e2e-report.html"
        out.write_text(html)
        assert out.stat().st_size > 2000

    def test_report_from_populated_fixture(self, populated_store, tmp_path):
        """Report from test fixture should have all expected sections."""
        from wxcli.migration.report.assembler import assemble_report

        html = assemble_report(populated_store,
            brand="Fixture Corp", prepared_by="Fixture SE")

        out = tmp_path / "fixture-report.html"
        out.write_text(html)

        # Executive sections
        assert "Migration Complexity" in html or "Complexity Score" in html
        assert "<svg" in html  # charts present
        assert "Fixture Corp" in html

        # Appendix sections
        assert "Object Inventory" in html
        assert "Decision Detail" in html
        assert "Device Inventory" in html
```

- [ ] **Step 2: Run end-to-end test**

Run: `pytest tests/migration/report/test_e2e.py -v`
Expected: All PASS. If normalize_discovery, TransformEngine, or AnalysisPipeline have import issues or require additional setup, fix and re-run.

Note: The e2e test that uses `sample_collector_file` may need the normalize/analyze functions to handle minimal data gracefully (1 user, 1 phone). If they crash on sparse data, that's a bug worth fixing — real collector files may have sparse data too.

- [ ] **Step 3: Run full test suite**

Run: `pytest tests/ -v --tb=short`
Expected: All existing tests still pass + all new report tests pass. No regressions.

- [ ] **Step 4: Generate a sample report from the CUCM test bed**

If you have access to the test bed at 10.201.123.107, run:
```bash
wxcli cucm init sample-report
wxcli cucm discover --host 10.201.123.107 --username axl_admin --password ***
wxcli cucm normalize
wxcli cucm analyze
wxcli cucm report --brand "Sample Customer" --prepared-by "Adam Hobgood"
```

Open the resulting HTML in a browser and verify:
- [ ] Complexity score gauge renders correctly
- [ ] Phone compatibility donut chart has correct proportions
- [ ] Object inventory bar chart is sorted and labeled
- [ ] Decision explanations are in plain English (no raw type names)
- [ ] Tables have zebra striping and correct alignment
- [ ] Print preview (Cmd+P) shows clean page breaks
- [ ] All SVGs render at high resolution

If no CUCM access, generate from the fixture:
```bash
pytest tests/migration/report/test_e2e.py::TestEndToEnd::test_report_from_populated_fixture -v
```
Then open the written HTML file from the tmp_path output.

- [ ] **Step 5: Commit**

```bash
git add tests/migration/report/test_e2e.py src/wxcli/migration/report/__init__.py
git commit -m "test(report): add end-to-end assessment report tests"
```

---

## Phase C Verification

After all tasks complete:

```bash
pytest tests/migration/report/ -v
pytest tests/ -v --tb=short  # full regression check
```

Expected: All report tests pass. No regressions in existing migration tests.

**Task Parallelism:** Tasks 6 and 7 can run in parallel (executive and appendix are independent). Task 8 depends on both. Task 9 depends on Task 8.

**After Phase C:** The assessment report tool is complete. Run `wxcli cucm report --brand "..." --prepared-by "..."` to generate a report from any analyzed migration project.
