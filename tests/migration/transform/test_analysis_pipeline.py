"""Tests for AnalysisPipeline at analysis_pipeline.py.

Verifies the pipeline:
1. Instantiates and runs all analyzers in dependency order
2. Collects decisions and stats per analyzer
3. Merges decisions into the store via fingerprint-based merge
4. Applies auto-resolution rules from config
5. Returns AnalysisResult with decisions, stats, run_id

Uses real :memory: SQLite store, no mocks except for injected test analyzers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from wxcli.migration.models import (
    CanonicalDevice,
    CanonicalLine,
    CanonicalUser,
    DecisionOption,
    DecisionType,
    DeviceCompatibilityTier,
    LineClassification,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.analysis_pipeline import (
    ALL_ANALYZERS,
    AnalysisPipeline,
)
from wxcli.migration.transform.analyzers import (
    Analyzer,
    AnalysisResult,
    Decision,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_store() -> MigrationStore:
    return MigrationStore(":memory:")


def _make_provenance(name: str = "test") -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id=name,
        source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def _seed_incompatible_device(store: MigrationStore, idx: int = 1) -> CanonicalDevice:
    """Insert an incompatible device into the store so DeviceCompatibilityAnalyzer fires."""
    device = CanonicalDevice(
        canonical_id=f"device:incompat-{idx}",
        provenance=_make_provenance(f"device-{idx}"),
        model="Cisco 7941G",
        mac=f"AABB00110{idx:03d}",
        compatibility_tier=DeviceCompatibilityTier.INCOMPATIBLE,
        cucm_device_name=f"SEP00110{idx:03d}",
    )
    store.upsert_object(device)
    return device


def _seed_user_missing_email(store: MigrationStore, idx: int = 1) -> CanonicalUser:
    """Insert a user with no email so MissingDataAnalyzer fires."""
    user = CanonicalUser(
        canonical_id=f"user:noemail-{idx}",
        provenance=_make_provenance(f"user-{idx}"),
        emails=[],
        first_name="No",
        last_name="Email",
    )
    store.upsert_object(user)
    return user


# ---------------------------------------------------------------------------
# Mock analyzers for dependency and failure tests
# ---------------------------------------------------------------------------


class MockAnalyzerA(Analyzer):
    """Mock analyzer that produces no decisions. Used for dependency ordering."""

    name = "mock_analyzer_a"
    decision_types = [DecisionType.MISSING_DATA]
    depends_on: list[str] = []
    run_order: list[str] = []  # class-level list to track execution order

    def analyze(self, store: MigrationStore) -> list[Decision]:
        MockAnalyzerA.run_order.append(self.name)
        return []

    def fingerprint(self, dt: DecisionType, ctx: dict[str, Any]) -> str:
        return self._hash_fingerprint(ctx)


class MockAnalyzerB(Analyzer):
    """Mock analyzer that depends on MockAnalyzerA."""

    name = "mock_analyzer_b"
    decision_types = [DecisionType.MISSING_DATA]
    depends_on = ["mock_analyzer_a"]
    run_order: list[str] = []

    def analyze(self, store: MigrationStore) -> list[Decision]:
        MockAnalyzerB.run_order.append(self.name)
        return []

    def fingerprint(self, dt: DecisionType, ctx: dict[str, Any]) -> str:
        return self._hash_fingerprint(ctx)


class FailingAnalyzer(Analyzer):
    """Mock analyzer that raises an exception."""

    name = "failing_analyzer"
    decision_types: list[DecisionType] = []
    depends_on: list[str] = []

    def analyze(self, store: MigrationStore) -> list[Decision]:
        raise ValueError("intentional test failure")

    def fingerprint(self, dt: DecisionType, ctx: dict[str, Any]) -> str:
        return ""


class ProducingMockAnalyzer(Analyzer):
    """Mock analyzer that produces a fixed decision."""

    name = "producing_mock"
    decision_types = [DecisionType.MISSING_DATA]
    depends_on: list[str] = []

    def analyze(self, store: MigrationStore) -> list[Decision]:
        return [
            self._create_decision(
                store=store,
                decision_type=DecisionType.MISSING_DATA,
                severity="LOW",
                summary="Mock missing data",
                context={"canonical_id": "mock:1", "missing_fields": ["name"]},
                options=[
                    DecisionOption(id="skip", label="Skip", impact="Skip it"),
                    DecisionOption(id="manual", label="Manual", impact="Fix later"),
                ],
                affected_objects=["mock:1"],
            )
        ]

    def fingerprint(self, dt: DecisionType, ctx: dict[str, Any]) -> str:
        return self._hash_fingerprint({
            "type": dt.value,
            "canonical_id": ctx.get("canonical_id", ""),
            "missing_fields": sorted(ctx.get("missing_fields", [])),
        })


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPipelineRunsAllAnalyzers:
    """test_pipeline_runs_all_analyzers: Create a store with objects that trigger
    decisions. Run pipeline. Verify stats dict has entries for multiple analyzer
    names and decisions are produced."""

    def test_pipeline_runs_all_analyzers(self) -> None:
        store = _make_store()

        # Seed objects that will trigger at least 2 analyzers:
        # - DeviceCompatibilityAnalyzer (incompatible device)
        # - MissingDataAnalyzer (user with no email)
        _seed_incompatible_device(store, 1)
        _seed_incompatible_device(store, 2)
        _seed_user_missing_email(store, 1)

        pipeline = AnalysisPipeline()
        result = pipeline.run(store)

        # Should have stats entries for all 12 analyzers + architecture_advisor
        assert len(result.stats) == len(ALL_ANALYZERS) + 1
        assert "architecture_advisor" in result.stats

        # At least device_compatibility and missing_data should have produced decisions
        assert result.stats.get("device_compatibility", 0) >= 2
        assert result.stats.get("missing_data", 0) >= 1

        # Total decisions should be non-zero
        assert len(result.decisions) > 0

        # run_id should be set
        assert result.run_id != ""


class TestPipelineEmptyStore:
    """test_pipeline_empty_store: Run on empty store. Should produce no decisions,
    all stats = 0."""

    def test_pipeline_empty_store(self) -> None:
        store = _make_store()
        pipeline = AnalysisPipeline()
        result = pipeline.run(store)

        assert len(result.decisions) == 0

        # All analyzer stats should be 0 (no data to analyze)
        # architecture_advisor may be non-zero (Pattern 16 E911 always fires)
        for analyzer_name, count in result.stats.items():
            if analyzer_name == "architecture_advisor":
                continue
            assert count == 0, f"Analyzer {analyzer_name} should produce 0 decisions on empty store"


class TestPipelineAutoRulesApplied:
    """test_pipeline_auto_rules_applied: Create store with an incompatible device.
    Configure auto_rules to skip DEVICE_INCOMPATIBLE. Run pipeline. Verify the
    decision gets auto-resolved (chosen_option='skip', resolved_by='auto_rule')."""

    def test_pipeline_auto_rules_applied(self) -> None:
        store = _make_store()
        _seed_incompatible_device(store, 1)

        config = {
            "auto_rules": [
                {"type": "DEVICE_INCOMPATIBLE", "choice": "skip"},
            ]
        }
        pipeline = AnalysisPipeline(config=config)
        result = pipeline.run(store)

        # The pipeline should have produced at least 1 DEVICE_INCOMPATIBLE decision
        assert result.stats.get("device_compatibility", 0) >= 1

        # After pipeline run, the auto-rule should have resolved the decision in the store
        all_decisions = store.get_all_decisions()
        device_decisions = [
            d for d in all_decisions
            if d["type"] == "DEVICE_INCOMPATIBLE"
            and d.get("chosen_option") != "__stale__"
        ]
        assert len(device_decisions) >= 1

        for dec in device_decisions:
            assert dec["chosen_option"] == "skip"
            assert dec["resolved_by"] == "auto_rule"
            assert dec["resolved_at"] is not None


class TestPipelineHandlesAnalyzerFailure:
    """test_pipeline_handles_analyzer_failure: Inject a failing analyzer. Verify
    the pipeline continues (doesn't crash) and stats show -1 for the failed analyzer."""

    def test_pipeline_handles_analyzer_failure(self) -> None:
        store = _make_store()
        _seed_incompatible_device(store, 1)

        # Use a small set: a producing mock + a failing analyzer
        pipeline = AnalysisPipeline(
            analyzers=[ProducingMockAnalyzer, FailingAnalyzer]
        )
        result = pipeline.run(store)

        # Failing analyzer should show -1
        assert result.stats["failing_analyzer"] == -1

        # Producing analyzer should still have run successfully
        assert result.stats["producing_mock"] == 1
        assert len(result.decisions) == 1

    def test_pipeline_continues_after_failure(self) -> None:
        """Failure of one analyzer must not prevent subsequent analyzers from running."""
        store = _make_store()

        # Put FailingAnalyzer first, ProducingMock second
        pipeline = AnalysisPipeline(
            analyzers=[FailingAnalyzer, ProducingMockAnalyzer]
        )
        result = pipeline.run(store)

        assert result.stats["failing_analyzer"] == -1
        assert result.stats["producing_mock"] == 1
        assert len(result.decisions) == 1


class TestPipelineDependencySort:
    """test_pipeline_dependency_sort: Create 2 mock analyzers, one depends_on the
    other. Verify they run in the correct order."""

    def setup_method(self) -> None:
        # Reset class-level run order trackers before each test
        MockAnalyzerA.run_order = []
        MockAnalyzerB.run_order = []

    def test_dependency_sort_b_depends_on_a(self) -> None:
        store = _make_store()

        # Pass B before A in the list — pipeline should sort A first
        pipeline = AnalysisPipeline(analyzers=[MockAnalyzerB, MockAnalyzerA])
        pipeline.run(store)

        # Both should share the same class-level run_order list via MockAnalyzerA
        # (since they append to their own class's list, check ordering)
        assert "mock_analyzer_a" in MockAnalyzerA.run_order
        assert "mock_analyzer_b" in MockAnalyzerB.run_order

        # A must have run before B. Use a combined order tracker:
        combined_order: list[str] = []

        class TrackingA(MockAnalyzerA):
            name = "mock_analyzer_a"
            depends_on: list[str] = []

            def analyze(self, store: MigrationStore) -> list[Decision]:
                combined_order.append(self.name)
                return []

        class TrackingB(MockAnalyzerB):
            name = "mock_analyzer_b"
            depends_on = ["mock_analyzer_a"]

            def analyze(self, store: MigrationStore) -> list[Decision]:
                combined_order.append(self.name)
                return []

        pipeline2 = AnalysisPipeline(analyzers=[TrackingB, TrackingA])
        pipeline2.run(store)

        assert combined_order == ["mock_analyzer_a", "mock_analyzer_b"]

    def test_no_dependencies_preserves_order(self) -> None:
        """With no dependencies, original list order is preserved."""
        store = _make_store()
        combined_order: list[str] = []

        class OrderA(Analyzer):
            name = "order_a"
            decision_types: list[DecisionType] = []
            depends_on: list[str] = []

            def analyze(self, store_: MigrationStore) -> list[Decision]:
                combined_order.append(self.name)
                return []

            def fingerprint(self, dt: DecisionType, ctx: dict[str, Any]) -> str:
                return ""

        class OrderB(Analyzer):
            name = "order_b"
            decision_types: list[DecisionType] = []
            depends_on: list[str] = []

            def analyze(self, store_: MigrationStore) -> list[Decision]:
                combined_order.append(self.name)
                return []

            def fingerprint(self, dt: DecisionType, ctx: dict[str, Any]) -> str:
                return ""

        pipeline = AnalysisPipeline(analyzers=[OrderA, OrderB])
        pipeline.run(store)

        assert combined_order == ["order_a", "order_b"]


class TestPipelineMergeOnRerun:
    """test_pipeline_merge_on_rerun: Run pipeline once (produces decisions).
    Run pipeline again (same data). Verify merge_decisions was called and
    existing decisions are preserved.

    Note: The real analyzers (DeviceCompatibilityAnalyzer, MissingDataAnalyzer)
    use _get_existing_decisions_for_type() to skip objects that already have
    decisions. This means a second pipeline run with the same data produces
    zero new analyzer decisions, and the merge correctly marks all existing
    pending decisions as stale. To test the merge-on-rerun path, we use
    ProducingMockAnalyzer which always produces decisions regardless of
    existing ones.
    """

    def test_merge_preserves_decisions_on_rerun(self) -> None:
        """Using a mock analyzer that always produces the same decision,
        verify that the second run merges instead of duplicating."""
        store = _make_store()

        pipeline = AnalysisPipeline(analyzers=[ProducingMockAnalyzer])

        # First run — produces 1 decision (+ advisory decisions from ArchitectureAdvisor)
        result1 = pipeline.run(store)
        decisions_after_first = store.get_all_decisions()
        # Filter to mock analyzer decisions only (exclude advisory)
        non_stale_first = [
            d for d in decisions_after_first
            if d.get("chosen_option") != "__stale__"
            and d.get("type") != "ARCHITECTURE_ADVISORY"
        ]
        assert len(non_stale_first) == 1
        first_id = non_stale_first[0]["decision_id"]

        # Second run — same decision (same fingerprint) produced again
        result2 = pipeline.run(store)
        decisions_after_second = store.get_all_decisions()
        non_stale_second = [
            d for d in decisions_after_second
            if d.get("chosen_option") != "__stale__"
            and d.get("type") != "ARCHITECTURE_ADVISORY"
        ]

        # Same number of non-stale decisions (merge updated, not duplicated)
        assert len(non_stale_second) == len(non_stale_first)

        # Decision ID preserved from first run (merge keeps original ID)
        assert non_stale_second[0]["decision_id"] == first_id

    def test_resolved_decisions_kept_on_rerun(self) -> None:
        """Resolved decisions survive a re-analysis run when the same
        fingerprint is produced again."""
        store = _make_store()

        pipeline = AnalysisPipeline(analyzers=[ProducingMockAnalyzer])

        # First run
        pipeline.run(store)

        # Resolve the decision
        decisions = store.get_all_decisions()
        assert len(decisions) >= 1
        resolved_id = decisions[0]["decision_id"]
        store.resolve_decision(resolved_id, "skip", "user")

        # Second run — same fingerprint produced again
        pipeline.run(store)

        # The resolved decision should still be resolved (kept, not overwritten)
        dec = store.get_decision(resolved_id)
        assert dec is not None
        assert dec["chosen_option"] == "skip"
        assert dec["resolved_by"] == "user"

    def test_real_analyzers_mark_stale_on_rerun(self) -> None:
        """With real analyzers, the second run produces no new decisions
        (analyzers skip objects with existing decisions), so the merge
        correctly marks all existing pending decisions as stale."""
        store = _make_store()
        _seed_incompatible_device(store, 1)

        pipeline = AnalysisPipeline()

        # First run — produces decisions
        result1 = pipeline.run(store)
        decisions_after_first = [
            d for d in store.get_all_decisions()
            if d.get("chosen_option") != "__stale__"
        ]
        assert len(decisions_after_first) > 0

        # Second run — analyzers see existing decisions and skip,
        # producing zero new decisions. Merge marks existing as stale.
        # Advisory decisions (from ArchitectureAdvisor) survive because
        # Phase 1 merge is scoped to Phase 1 decision types only.
        result2 = pipeline.run(store)
        decisions_after_second = store.get_all_decisions()
        non_stale_second = [
            d for d in decisions_after_second
            if d.get("chosen_option") != "__stale__"
            and d.get("type") != "ARCHITECTURE_ADVISORY"
        ]
        stale_second = [
            d for d in decisions_after_second
            if d.get("chosen_option") == "__stale__"
        ]

        # All previous Phase 1 decisions should now be stale (analyzers produced 0 new)
        phase1_first = [
            d for d in decisions_after_first
            if d.get("type") != "ARCHITECTURE_ADVISORY"
        ]
        assert len(non_stale_second) == 0
        assert len(stale_second) == len(phase1_first)


class TestResolveAndCascade:
    """Investigation 1: Cascade re-evaluation on resolve.

    Verifies that resolving a CSS_ROUTING_MISMATCH decision with
    cascades_to=[CALLING_PERMISSION_MISMATCH] triggers re-evaluation
    of CSSPermissionAnalyzer only.

    (from 06-decision-workflow.md lines 142-184)
    """

    def test_cascade_reruns_affected_analyzer(self) -> None:
        """Resolving a decision with cascades_to triggers re-run of the affected analyzer."""
        store = _make_store()

        # Seed a CSS_ROUTING_MISMATCH decision with cascades_to in context.
        # Use next_decision_id() so the counter stays in sync with the store.
        cascade_id = store.next_decision_id()
        store.save_decision({
            "decision_id": cascade_id,
            "type": "CSS_ROUTING_MISMATCH",
            "severity": "HIGH",
            "summary": "Test routing mismatch",
            "context": {
                "cascades_to": ["CALLING_PERMISSION_MISMATCH"],
                "dial_plan_ids": ["dp:1"],
                "conflicting_pattern": "9.!",
            },
            "options": [
                {"id": "use_union", "label": "Union", "impact": "Merge all"},
                {"id": "skip", "label": "Skip", "impact": "Skip"},
            ],
            "chosen_option": None,
            "resolved_at": None,
            "resolved_by": None,
            "fingerprint": "fp_cascade_test_1",
            "run_id": store.current_run_id,
        })

        # Seed a calling_permission object that CSSPermissionAnalyzer will flag
        # (empty calling_permissions list triggers "No calling permissions mapped")
        from wxcli.migration.models import CanonicalCallingPermission
        perm = CanonicalCallingPermission(
            canonical_id="calling_permission:css-restricted",
            provenance=_make_provenance("css-restricted"),
            calling_permissions=[],  # empty → triggers analyzer
        )
        store.upsert_object(perm)

        pipeline = AnalysisPipeline()

        # Resolve the routing mismatch with cascade
        warnings = pipeline.resolve_and_cascade(
            store=store,
            decision_id=cascade_id,
            chosen_option="use_union",
            resolved_by="user",
        )

        # Verify the original decision is resolved
        dec = store.get_decision(cascade_id)
        assert dec is not None
        assert dec["chosen_option"] == "use_union"
        assert dec["resolved_by"] == "user"

        # CSSPermissionAnalyzer should have been re-run and produced
        # a CALLING_PERMISSION_MISMATCH for the empty permission object
        all_decs = store.get_all_decisions()
        perm_decs = [
            d for d in all_decs
            if d["type"] == "CALLING_PERMISSION_MISMATCH"
            and d.get("chosen_option") != "__stale__"
        ]
        assert len(perm_decs) >= 1, (
            "CSSPermissionAnalyzer should have produced a decision for the "
            "empty calling_permission object"
        )

    def test_cascade_no_cascades_to_returns_empty(self) -> None:
        """Decision without cascades_to in context returns no warnings."""
        store = _make_store()

        dec_id = store.next_decision_id()
        store.save_decision({
            "decision_id": dec_id,
            "type": "DEVICE_INCOMPATIBLE",
            "severity": "MEDIUM",
            "summary": "Test no cascade",
            "context": {"canonical_id": "device:1"},
            "options": [{"id": "skip", "label": "Skip", "impact": "Skip"}],
            "chosen_option": None,
            "resolved_at": None,
            "resolved_by": None,
            "fingerprint": "fp_no_cascade_test",
            "run_id": store.current_run_id,
        })

        pipeline = AnalysisPipeline()
        warnings = pipeline.resolve_and_cascade(
            store=store,
            decision_id=dec_id,
            chosen_option="skip",
        )

        # No cascades_to → empty warnings, but decision is still resolved
        assert warnings == []
        dec = store.get_decision(dec_id)
        assert dec["chosen_option"] == "skip"

    def test_cascade_only_runs_affected_analyzers(self) -> None:
        """Cascade with cascades_to=[CALLING_PERMISSION_MISMATCH] must NOT
        re-run all 12 analyzers — only CSSPermissionAnalyzer."""
        store = _make_store()

        # Track which analyzers actually run
        run_tracker: list[str] = []

        class TrackingCSSPerm(Analyzer):
            name = "css_permission"
            decision_types = [DecisionType.CALLING_PERMISSION_MISMATCH]
            depends_on: list[str] = []

            def analyze(self, store_: MigrationStore) -> list[Decision]:
                run_tracker.append(self.name)
                return []

            def fingerprint(self, dt: DecisionType, ctx: dict[str, Any]) -> str:
                return self._hash_fingerprint(ctx)

        class TrackingDevice(Analyzer):
            name = "device_compatibility"
            decision_types = [DecisionType.DEVICE_INCOMPATIBLE]
            depends_on: list[str] = []

            def analyze(self, store_: MigrationStore) -> list[Decision]:
                run_tracker.append(self.name)
                return []

            def fingerprint(self, dt: DecisionType, ctx: dict[str, Any]) -> str:
                return self._hash_fingerprint(ctx)

        dec_id = store.next_decision_id()
        store.save_decision({
            "decision_id": dec_id,
            "type": "CSS_ROUTING_MISMATCH",
            "severity": "HIGH",
            "summary": "Cascade selectivity test",
            "context": {"cascades_to": ["CALLING_PERMISSION_MISMATCH"]},
            "options": [{"id": "use_union", "label": "Union", "impact": "Merge"}],
            "chosen_option": None,
            "resolved_at": None,
            "resolved_by": None,
            "fingerprint": "fp_selectivity_test",
            "run_id": store.current_run_id,
        })

        pipeline = AnalysisPipeline(analyzers=[TrackingCSSPerm, TrackingDevice])
        pipeline.resolve_and_cascade(
            store=store,
            decision_id=dec_id,
            chosen_option="use_union",
        )

        # Only css_permission should have run, NOT device_compatibility
        assert "css_permission" in run_tracker
        assert "device_compatibility" not in run_tracker

    def test_cascade_merge_result_in_warnings(self) -> None:
        """When cascade produces new decisions, warnings report the count."""
        store = _make_store()

        dec_id = store.next_decision_id()
        store.save_decision({
            "decision_id": dec_id,
            "type": "CSS_ROUTING_MISMATCH",
            "severity": "HIGH",
            "summary": "Cascade warning test",
            "context": {"cascades_to": ["MISSING_DATA"]},
            "options": [{"id": "use_union", "label": "Union", "impact": "Merge"}],
            "chosen_option": None,
            "resolved_at": None,
            "resolved_by": None,
            "fingerprint": "fp_warning_test",
            "run_id": store.current_run_id,
        })

        # Seed a user with no email → MissingDataAnalyzer produces MISSING_DATA
        _seed_user_missing_email(store, 99)

        pipeline = AnalysisPipeline()
        warnings = pipeline.resolve_and_cascade(
            store=store,
            decision_id=dec_id,
            chosen_option="use_union",
        )

        # Should have at least one "new decision(s) generated" warning
        assert any("new decision" in w for w in warnings)


class TestMultiAnalyzerSameObject:
    """Investigation 2: Multi-analyzer decisions on same object.

    Verifies that two analyzers can produce independent decisions for the
    same canonical_id (e.g., a device that is both DEVICE_INCOMPATIBLE and
    MISSING_DATA). Each decision has a unique fingerprint, so they coexist
    in the store and can be resolved independently.
    """

    def test_same_object_gets_two_decisions(self) -> None:
        """A device that is incompatible AND missing MAC triggers both
        DeviceCompatibilityAnalyzer and MissingDataAnalyzer."""
        store = _make_store()

        # Seed a device that is incompatible AND has no MAC
        device = CanonicalDevice(
            canonical_id="device:dual-issue",
            provenance=_make_provenance("dual-issue"),
            model="Cisco 7941G",
            mac=None,  # Missing MAC → MISSING_DATA
            compatibility_tier=DeviceCompatibilityTier.INCOMPATIBLE,  # → DEVICE_INCOMPATIBLE
            cucm_device_name="SEP_DUAL_ISSUE",
        )
        store.upsert_object(device)

        pipeline = AnalysisPipeline()
        result = pipeline.run(store)

        # Both analyzers should have produced decisions
        assert result.stats.get("device_compatibility", 0) >= 1
        assert result.stats.get("missing_data", 0) >= 1

        # Verify both decisions exist in the store for the same canonical_id
        all_decs = store.get_all_decisions()
        non_stale = [
            d for d in all_decs if d.get("chosen_option") != "__stale__"
        ]

        device_decs = [
            d for d in non_stale
            if "device:dual-issue" in d.get("context", {}).get("_affected_objects", [])
        ]
        assert len(device_decs) >= 2, (
            f"Expected at least 2 decisions for device:dual-issue, got {len(device_decs)}"
        )

        # Verify they have different fingerprints
        fingerprints = [d["fingerprint"] for d in device_decs]
        assert len(set(fingerprints)) == len(fingerprints), (
            "Each decision must have a unique fingerprint"
        )

        # Verify the decision types are what we expect
        types = sorted(d["type"] for d in device_decs)
        assert "DEVICE_INCOMPATIBLE" in types
        assert "MISSING_DATA" in types

    def test_same_object_decisions_resolved_independently(self) -> None:
        """Two decisions on the same object can be resolved independently."""
        store = _make_store()

        device = CanonicalDevice(
            canonical_id="device:dual-resolve",
            provenance=_make_provenance("dual-resolve"),
            model="Cisco 7941G",
            mac=None,
            compatibility_tier=DeviceCompatibilityTier.INCOMPATIBLE,
            cucm_device_name="SEP_DUAL_RESOLVE",
        )
        store.upsert_object(device)

        pipeline = AnalysisPipeline()
        pipeline.run(store)

        all_decs = store.get_all_decisions()
        non_stale = [
            d for d in all_decs if d.get("chosen_option") != "__stale__"
        ]
        device_decs = [
            d for d in non_stale
            if "device:dual-resolve" in d.get("context", {}).get("_affected_objects", [])
        ]
        assert len(device_decs) >= 2

        # Resolve just the DEVICE_INCOMPATIBLE one
        incompat = next(d for d in device_decs if d["type"] == "DEVICE_INCOMPATIBLE")
        missing = next(d for d in device_decs if d["type"] == "MISSING_DATA")

        store.resolve_decision(incompat["decision_id"], "skip", "user")

        # Verify only the incompatible decision is resolved
        incompat_after = store.get_decision(incompat["decision_id"])
        assert incompat_after["chosen_option"] == "skip"
        assert incompat_after["resolved_by"] == "user"

        # MISSING_DATA should still be pending
        missing_after = store.get_decision(missing["decision_id"])
        assert missing_after["chosen_option"] is None

        # Now resolve MISSING_DATA independently
        store.resolve_decision(missing["decision_id"], "provide_data", "user")
        missing_final = store.get_decision(missing["decision_id"])
        assert missing_final["chosen_option"] == "provide_data"
