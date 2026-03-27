# Phase 5: End-to-End Pipeline Integration Tests

## Context

The CUCM migration pipeline has 1507 unit tests but no end-to-end integration test that runs the full pipeline: `normalize → map → analyze → plan → export`. Each phase has its own tests, but cross-phase assumptions (data shapes, cross-ref availability, decision propagation) are only validated by running everything together.

**Why this matters:** Unit tests mock dependencies. Integration tests catch bugs like:
- Normalizer output shape doesn't match what the mapper expects
- Cross-ref builder misses a relationship that a mapper depends on
- Analyzer produces decisions that the planner doesn't know how to expand
- Planner produces operations that have no handler

**Read these files first:**
- `src/wxcli/migration/transform/pipeline.py` — `normalize_discovery()` entry point
- `src/wxcli/migration/transform/engine.py` — `TransformEngine` with `MAPPER_ORDER`
- `src/wxcli/migration/transform/analysis_pipeline.py` — `AnalysisPipeline.run()`
- `src/wxcli/migration/execute/planner.py` — `expand_to_operations()`
- `src/wxcli/migration/execute/dependency.py` — `build_dependency_graph()`
- `src/wxcli/migration/execute/batch.py` — `partition_into_batches()`
- `src/wxcli/migration/export/deployment_plan.py` — `generate_deployment_plan()`
- `tests/migration/transform/test_integration.py` — existing partial integration test (messy_store fixture)
- `tests/migration/test_cucm_cli.py` — existing CLI integration tests (Typer CliRunner)
- `src/wxcli/migration/store.py` — `MigrationStore` API

## What to Build

A single test file `tests/migration/test_pipeline_e2e.py` with synthetic CUCM data that exercises the full pipeline from raw extraction output through deployment plan generation.

### Synthetic Data Set

Create a fixture that produces a realistic `raw_data` dict simulating a small CUCM environment:

**2 locations:**
- "Main Office" (device pool "DP-Main", datetime group "DT-Eastern", CUCM location "LOC-Main")
- "Branch Office" (device pool "DP-Branch", datetime group "DT-Pacific", CUCM location "LOC-Branch")

**4 users:**
- `jsmith` — Main Office, extension 1001, 1 phone (Cisco 8845, compatible), voicemail enabled
- `mchen` — Main Office, extension 1002, 1 phone (Cisco 9861, native MPP), no voicemail
- `bwilson` — Branch Office, extension 2001, 1 phone (Cisco 7962, incompatible), voicemail enabled
- `alee` — Branch Office, extension 2002, no phone (phoneless user), no voicemail

**3 phones:**
- SEP001122334455 (8845) — owned by jsmith, 2 line appearances (1001 primary, 1002 shared)
- SEP556677889900 (9861) — owned by mchen, 1 line appearance (1002 primary)
- SEPAABBCCDDEEFF (7962) — owned by bwilson, 1 line appearance (2001 primary)

**1 shared line:**
- DN 1002 appears on both SEP001122334455 (line 2) and SEP556677889900 (line 1) — triggers `SHARED_LINE_COMPLEX` decision

**Call features:**
- 1 hunt group: "Sales HG" in Main Office, members [jsmith, mchen]
- 1 auto attendant (CTI RP): "Main AA" in Main Office, with business schedule "Business Hours"
- 1 call park: extension 7001 in Main Office

**Routing:**
- 1 SIP trunk: "PSTN-Trunk"
- 1 route group: "RG-PSTN" referencing PSTN-Trunk
- 1 CSS: "CSS-Internal" with 2 partitions: "PT-Internal", "PT-PSTN"
- 2 translation patterns: "+1!" → prefix strip, "9.!" → PSTN breakout

**Schedules:**
- 1 time schedule "Business Hours" with 1 time period (Mon-Fri 8am-5pm)

**Voicemail:**
- 1 VM pilot: "VM-Pilot-1"
- 1 VM profile assigned to jsmith

**Button template:**
- "Standard 8845" — 10 buttons (line 1, line 2, 3x BLF, 5x speed dial)

This data set should trigger at least these decision types:
- `DEVICE_INCOMPATIBLE` (7962)
- `SHARED_LINE_COMPLEX` (DN 1002)
- `LOCATION_AMBIGUOUS` (if device pool names don't clearly map — make one ambiguous)
- `EXTENSION_CONFLICT` (if desired — add duplicate extension across locations)

### raw_data Structure

The fixture should produce the exact dict structure that `normalize_discovery()` expects:

```python
raw_data = {
    "locations": {
        "device_pools": [...],      # listDevicePool results
        "datetime_groups": [...],   # listDateTimeGroup results
        "cucm_locations": [...],    # listCmcLocation results
    },
    "users": {
        "users": [...],             # listEndUser + getEndUser results
        "dns": [...],               # listLine + getLine results
    },
    "devices": {
        "phones": [...],            # listPhone + getPhone results (full line arrays)
    },
    "routing": {
        "gateways": [],
        "sip_trunks": [...],
        "route_groups": [...],
        "route_lists": [],
        "route_patterns": [...],
        "css": [...],
        "partitions": [...],
        "time_schedules": [...],
        "time_periods": [...],
    },
    "features": {
        "hunt_pilots": [...],
        "hunt_lists": [...],
        "line_groups": [...],
        "call_parks": [...],
        "pickup_groups": [],
        "cti_route_points": [...],
    },
    "voicemail": {
        "pilots": [...],
        "profiles": [...],
    },
    "templates": {
        "button_templates": [...],
        "softkey_templates": [],
    },
}
```

**Critical:** Get the raw data shapes right. Look at `src/wxcli/migration/cucm/extractors/*.py` to see what fields each extractor returns, and match those shapes exactly. The normalizers expect specific field names (e.g., `ownerUserName`, `devicePoolName`, `callingSearchSpaceName`). Zeep returns nested dicts with `_value_1` for reference fields — replicate this.

### Test Structure

```python
"""End-to-end pipeline integration tests.

Runs the full pipeline: normalize → map → analyze → plan → export
on a synthetic CUCM data set and verifies outputs at each stage.
"""

import pytest
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.pipeline import normalize_discovery
from wxcli.migration.transform.engine import TransformEngine
from wxcli.migration.transform.analysis_pipeline import AnalysisPipeline
from wxcli.migration.execute.planner import expand_to_operations
from wxcli.migration.execute.dependency import build_dependency_graph
from wxcli.migration.execute.batch import partition_into_batches, save_plan_to_store
from wxcli.migration.export.deployment_plan import generate_deployment_plan


@pytest.fixture
def store(tmp_path):
    s = MigrationStore(tmp_path / "e2e.db")
    yield s
    s.close()


@pytest.fixture
def raw_data():
    """Synthetic CUCM environment — 2 locations, 4 users, 3 phones, features."""
    return { ... }  # Full synthetic data set


class TestNormalizationPhase:
    def test_normalize_produces_expected_object_counts(self, store, raw_data):
        result = normalize_discovery(raw_data, store)
        # Verify object counts
        assert store.count_by_type("user") == 4
        assert store.count_by_type("device") >= 3
        assert store.count_by_type("dn") >= 4  # 1001, 1002, 2001, 2002
        assert store.count_by_type("device_pool") == 2
        assert store.count_by_type("hunt_pilot") >= 1
        assert store.count_by_type("sip_trunk") >= 1

    def test_cross_refs_built(self, store, raw_data):
        normalize_discovery(raw_data, store)
        # Verify key cross-refs exist
        user_refs = store.find_cross_refs("user:jsmith", "user_has_line")
        assert len(user_refs) >= 1
        device_refs = store.find_cross_refs("device:SEP001122334455", "device_has_dn")
        assert len(device_refs) >= 2  # Two line appearances

    def test_shared_line_detected(self, store, raw_data):
        normalize_discovery(raw_data, store)
        shared_lines = store.get_objects("shared_line")
        assert len(shared_lines) >= 1  # DN 1002 is shared


class TestMappingPhase:
    def test_mappers_produce_canonical_objects(self, store, raw_data):
        normalize_discovery(raw_data, store)
        engine = TransformEngine()
        result = engine.run(store)
        # Verify mapped objects
        assert store.count_by_type("location") >= 2
        assert store.count_by_type("trunk") >= 1
        assert store.count_by_type("hunt_group") >= 1
        assert store.count_by_type("auto_attendant") >= 1

    def test_no_mapper_errors(self, store, raw_data):
        normalize_discovery(raw_data, store)
        engine = TransformEngine()
        result = engine.run(store)
        assert len(result.errors) == 0, f"Mapper errors: {result.errors}"


class TestAnalysisPhase:
    def test_analyzers_produce_decisions(self, store, raw_data):
        normalize_discovery(raw_data, store)
        TransformEngine().run(store)
        pipeline = AnalysisPipeline()
        result = pipeline.run(store)
        decisions = store.get_all_decisions()
        # Should have at least DEVICE_INCOMPATIBLE (7962) and SHARED_LINE_COMPLEX (DN 1002)
        decision_types = {d["type"] for d in decisions}
        assert "DEVICE_INCOMPATIBLE" in decision_types
        assert "SHARED_LINE_COMPLEX" in decision_types

    def test_all_analyzers_run_without_error(self, store, raw_data):
        normalize_discovery(raw_data, store)
        TransformEngine().run(store)
        pipeline = AnalysisPipeline()
        result = pipeline.run(store)
        # No analyzer should crash — verify all 13 ran
        assert len(result.stats) >= 10  # At least 10 analyzers ran


class TestPlanningPhase:
    def _run_through_analysis(self, store, raw_data):
        normalize_discovery(raw_data, store)
        TransformEngine().run(store)
        AnalysisPipeline().run(store)
        # Resolve decisions so objects reach 'analyzed' status
        for d in store.get_all_decisions():
            if d.get("chosen_option") is None and d.get("options"):
                store.save_decision({
                    **d,
                    "chosen_option": d["options"][0]["value"],
                })

    def test_planner_produces_operations(self, store, raw_data):
        self._run_through_analysis(store, raw_data)
        ops = expand_to_operations(store)
        assert len(ops) > 0
        # Should have location:create, user:create, device:create at minimum
        op_keys = {(op.resource_type, op.op_type) for op in ops}
        assert ("location", "create") in op_keys
        assert ("user", "create") in op_keys

    def test_dependency_graph_is_acyclic(self, store, raw_data):
        self._run_through_analysis(store, raw_data)
        ops = expand_to_operations(store)
        G = build_dependency_graph(ops, store)
        import networkx as nx
        assert nx.is_directed_acyclic_graph(G), "Dependency graph has cycles!"

    def test_batches_partition_correctly(self, store, raw_data):
        self._run_through_analysis(store, raw_data)
        ops = expand_to_operations(store)
        G = build_dependency_graph(ops, store)
        batches = partition_into_batches(G)
        assert len(batches) > 0
        # Tier 0 (locations) should be in earliest batch
        tier_0_ops = [b for b in batches if b.tier == 0]
        assert len(tier_0_ops) > 0


class TestExportPhase:
    def _run_through_planning(self, store, raw_data):
        normalize_discovery(raw_data, store)
        TransformEngine().run(store)
        AnalysisPipeline().run(store)
        for d in store.get_all_decisions():
            if d.get("chosen_option") is None and d.get("options"):
                store.save_decision({**d, "chosen_option": d["options"][0]["value"]})
        ops = expand_to_operations(store)
        G = build_dependency_graph(ops, store)
        save_plan_to_store(G, store)

    def test_deployment_plan_generates(self, store, raw_data):
        self._run_through_planning(store, raw_data)
        plan = generate_deployment_plan(store)
        assert isinstance(plan, str)
        assert len(plan) > 100
        assert "## " in plan  # Has markdown sections

    def test_deployment_plan_references_locations(self, store, raw_data):
        self._run_through_planning(store, raw_data)
        plan = generate_deployment_plan(store)
        assert "Main Office" in plan or "main" in plan.lower()


class TestFullPipelineSmoke:
    """Single test that runs everything and verifies the pipeline doesn't crash."""

    def test_full_pipeline_no_crash(self, store, raw_data):
        # Normalize
        norm_result = normalize_discovery(raw_data, store)
        assert norm_result["pass1"]["total"] > 0

        # Map
        map_result = TransformEngine().run(store)
        assert map_result.objects_created > 0

        # Analyze
        analysis_result = AnalysisPipeline().run(store)

        # Resolve all decisions (auto-pick first option)
        for d in store.get_all_decisions():
            if d.get("chosen_option") is None and d.get("options"):
                store.save_decision({**d, "chosen_option": d["options"][0]["value"]})

        # Plan
        ops = expand_to_operations(store)
        assert len(ops) > 0
        G = build_dependency_graph(ops, store)
        save_plan_to_store(G, store)

        # Export
        plan = generate_deployment_plan(store)
        assert len(plan) > 0
```

### The Hard Part: Getting raw_data Shapes Right

The synthetic data must match exactly what the extractors produce. Key gotchas:

1. **Zeep reference fields** return `{"_value_1": "name", "uuid": "{UUID}"}` not plain strings. The normalizers use `ref_value()` helper from `extractors/helpers.py` to unwrap these. Your synthetic data should use plain strings for fields the normalizers expect unwrapped, and the `_value_1` format for fields where extractors pass raw zeep output.

2. **Phone lines array:** `lines` may be `{"line": [...]}` (list) or `{"line": {...}}` (single dict). Normalizers handle both. Use the list format.

3. **Empty fields:** Use `None` not empty string for absent fields. Zeep returns `None` for unset fields.

4. **DN patterns:** Use realistic E.164-convertible patterns like `"1001"`, `"1002"`, `"+12125551001"`.

5. **Model names:** Use exact Cisco model strings: `"Cisco 8845"`, `"Cisco 9861"`, `"Cisco 7962"`. The device compatibility analyzer matches on these.

**Tip:** Look at existing test fixtures in `tests/migration/transform/test_integration.py` (the `messy_store` fixture) and `tests/migration/transform/test_normalizers.py` for examples of raw data shapes that the pipeline accepts.

## Verification

```bash
python3.11 -m pytest tests/migration/test_pipeline_e2e.py -v  # All e2e tests pass
python3.11 -m pytest tests/migration/ -x -q  # No regressions
```

## What NOT to Do

- Don't mock pipeline internals — the whole point is testing real interactions
- Don't test individual normalizers/mappers — that's what unit tests do
- Don't make the synthetic data too large — 4 users, 3 phones is enough to trigger key decisions
- Don't test preflight (it requires live wxcli subprocess calls) — stop at export
- Don't test the report generator (it has its own test suite) — stop at deployment plan
