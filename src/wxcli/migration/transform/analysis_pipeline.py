"""Analysis pipeline — runs all 12 analyzers, then auto-rules, then merge.

Orchestrates the conflict detection engine. Each analyzer sweeps the
mapped inventory independently and produces Decision objects. After all
analyzers run, auto-resolution rules are applied, then the fingerprint-based
merge integrates new decisions with existing ones.

(from 03-conflict-detection-engine.md — AnalysisPipeline)
(from 07-idempotency-resumability.md — merge after analysis)
"""

from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.models import DecisionType
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.analyzers import (
    Analyzer,
    AnalysisResult,
    Decision,
)
from wxcli.migration.transform.analyzers.css_permission import CSSPermissionAnalyzer
from wxcli.migration.transform.analyzers.css_routing import CSSRoutingAnalyzer
from wxcli.migration.transform.analyzers.device_compatibility import DeviceCompatibilityAnalyzer
from wxcli.migration.transform.analyzers.dn_ambiguity import DNAmbiguityAnalyzer
from wxcli.migration.transform.analyzers.duplicate_user import DuplicateUserAnalyzer
from wxcli.migration.transform.analyzers.extension_conflict import ExtensionConflictAnalyzer
from wxcli.migration.transform.analyzers.feature_approximation import FeatureApproximationAnalyzer
from wxcli.migration.transform.analyzers.location_ambiguity import LocationAmbiguityAnalyzer
from wxcli.migration.transform.analyzers.missing_data import MissingDataAnalyzer
from wxcli.migration.transform.analyzers.shared_line import SharedLineAnalyzer
from wxcli.migration.transform.analyzers.voicemail_compatibility import VoicemailCompatibilityAnalyzer
from wxcli.migration.transform.analyzers.workspace_license import WorkspaceLicenseAnalyzer
from wxcli.migration.transform.mappers.base import decision_to_store_dict
from wxcli.migration.transform.rules import apply_auto_rules

logger = logging.getLogger(__name__)

# All 12 analyzers in default execution order.
# No inter-analyzer dependencies exist in the current set (from 03-conflict-detection-engine.md).
ALL_ANALYZERS: list[type[Analyzer]] = [
    ExtensionConflictAnalyzer,
    DNAmbiguityAnalyzer,
    DeviceCompatibilityAnalyzer,
    SharedLineAnalyzer,
    CSSRoutingAnalyzer,
    CSSPermissionAnalyzer,
    LocationAmbiguityAnalyzer,
    DuplicateUserAnalyzer,
    VoicemailCompatibilityAnalyzer,
    WorkspaceLicenseAnalyzer,
    FeatureApproximationAnalyzer,
    MissingDataAnalyzer,
]


class AnalysisPipeline:
    """Runs all analyzers in dependency order, collects decisions.

    Multiple analyzers CAN produce decisions for the same object. Each
    decision has a unique fingerprint (derived from its type + context),
    so they coexist in the store and can be resolved independently. For
    example, a device may be both DEVICE_INCOMPATIBLE (from
    DeviceCompatibilityAnalyzer) and MISSING_DATA (from MissingDataAnalyzer).

    (from 03-conflict-detection-engine.md, AnalysisPipeline)
    """

    def __init__(
        self,
        analyzers: list[type[Analyzer]] | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        self.analyzer_classes = analyzers or ALL_ANALYZERS
        self.config = config or {}

    def run(self, store: MigrationStore) -> AnalysisResult:
        """Run all analyzers, apply auto-rules, merge decisions.

        Steps:
        1. Sort analyzers by depends_on (topological)
        2. Run each analyzer, collect decisions
        3. Apply auto-resolution rules from config
        4. Merge new decisions with existing (fingerprint-based)

        Returns AnalysisResult with all decisions and per-analyzer stats.
        """
        # Instantiate and sort by dependencies
        instances = [cls() for cls in self.analyzer_classes]
        sorted_analyzers = self._sort_by_dependencies(instances)

        all_decisions: list[Decision] = []
        stats: dict[str, int] = {}

        # Step 1: Run each analyzer
        for analyzer in sorted_analyzers:
            analyzer_name = analyzer.name or type(analyzer).__name__
            logger.info("Running analyzer: %s", analyzer_name)
            try:
                decisions = analyzer.analyze(store)
                all_decisions.extend(decisions)
                stats[analyzer_name] = len(decisions)
                logger.info(
                    "Analyzer %s complete: %d decisions",
                    analyzer_name,
                    len(decisions),
                )
            except Exception as exc:
                logger.error(
                    "Analyzer %s failed with %s: %s",
                    analyzer_name,
                    type(exc).__name__,
                    exc,
                )
                stats[analyzer_name] = -1  # -1 signals failure

        # Step 2: Convert to store dicts for merge
        new_decision_dicts = [decision_to_store_dict(d) for d in all_decisions]

        # Step 3: Merge with existing decisions (fingerprint-based)
        # Scope to Phase 1 decision types only — advisory decisions are managed
        # by the Phase 2 merge (Step 5) and must not be stale-marked here.
        phase1_types = list({
            dt.value for cls in self.analyzer_classes for dt in cls.decision_types
        })
        merge_result = store.merge_decisions(
            new_decision_dicts, decision_types=phase1_types
        )
        logger.info(
            "Decision merge: kept=%d, updated=%d, new=%d, stale=%d, invalidated=%d",
            merge_result["kept"],
            merge_result["updated"],
            merge_result["new"],
            merge_result["stale"],
            merge_result["invalidated"],
        )

        # Step 4: Apply auto-resolution rules
        auto_resolved = apply_auto_rules(store, self.config)
        if auto_resolved:
            logger.info("Auto-rules resolved %d decisions", auto_resolved)

        # Step 5: Phase 2 — Run ArchitectureAdvisor (reads merged decisions from store)
        from wxcli.migration.advisory.advisor import ArchitectureAdvisor
        advisor = ArchitectureAdvisor()
        logger.info("Running advisor: architecture_advisor")
        try:
            advisory_decisions = advisor.analyze(store)
            if advisory_decisions:
                advisory_dicts = [decision_to_store_dict(d) for d in advisory_decisions]
                advisory_merge = store.merge_decisions(
                    advisory_dicts,
                    decision_types=[DecisionType.ARCHITECTURE_ADVISORY.value],
                    stage="advisory",
                )
                logger.info(
                    "Advisory merge: kept=%d, updated=%d, new=%d, stale=%d",
                    advisory_merge.get("kept", 0),
                    advisory_merge.get("updated", 0),
                    advisory_merge.get("new", 0),
                    advisory_merge.get("stale", 0),
                )
                stats["architecture_advisor"] = len(advisory_decisions)
            else:
                stats["architecture_advisor"] = 0
        except Exception as exc:
            logger.error(
                "ArchitectureAdvisor failed: %s: %s", type(exc).__name__, exc
            )
            stats["architecture_advisor"] = -1

        # Step 6: Populate recommendations on ALL decisions (Phase 1 + Phase 2)
        from wxcli.migration.advisory import populate_recommendations
        rec_count = populate_recommendations(store)
        if rec_count:
            logger.info("Advisory: %d recommendations populated", rec_count)

        return AnalysisResult(
            decisions=all_decisions,
            stats=stats,
            run_id=store.current_run_id,
        )

    def resolve_and_cascade(
        self,
        store: MigrationStore,
        decision_id: str,
        chosen_option: str,
        resolved_by: str = "user",
    ) -> list[str]:
        """Resolve a decision and trigger cascading re-evaluation.

        Steps:
        1. Resolve the decision via store.resolve_decision()
        2. Read cascades_to from the decision's context
        3. Re-run only analyzers whose decision_types intersect cascades_to
        4. Merge the new decisions via store.merge_decisions()
        5. Return warnings about new/changed decisions

        (from 06-decision-workflow.md lines 142-184, resolve_decision workflow)

        Scope: Only re-runs affected analyzers, not all 12.
        Does NOT modify the Decision model or the main run() method.
        """
        # Step 1: Resolve the decision
        store.resolve_decision(
            decision_id=decision_id,
            chosen_option=chosen_option,
            resolved_by=resolved_by,
        )

        # Step 2: Read cascades_to from the resolved decision's context
        decision = store.get_decision(decision_id)
        if decision is None:
            return []

        context = decision.get("context", {})
        cascades_to = context.get("cascades_to", [])
        if not cascades_to:
            return []

        # Step 3: Re-run only affected analyzers
        # (from 06-decision-workflow.md: "Re-run only the affected analyzers")
        cascade_types = set(cascades_to)
        affected_classes = [
            cls for cls in self.analyzer_classes
            if any(dt.value in cascade_types for dt in cls.decision_types)
        ]

        if not affected_classes:
            logger.info(
                "No analyzers match cascades_to=%s for decision %s",
                cascades_to,
                decision_id,
            )
            return []

        affected_names = [cls.name if hasattr(cls, 'name') else cls.__name__ for cls in affected_classes]
        logger.info(
            "Cascade from %s: re-running analyzers %s",
            decision_id,
            affected_names,
        )

        instances = [cls() for cls in affected_classes]
        all_decisions: list[Decision] = []
        for analyzer in instances:
            try:
                decisions = analyzer.analyze(store)
                all_decisions.extend(decisions)
            except Exception as exc:
                logger.error(
                    "Cascade analyzer %s failed: %s",
                    analyzer.name,
                    exc,
                )

        # Step 4: Save cascade-produced decisions individually.
        # DELIBERATE DEVIATION from 06-decision-workflow.md pseudocode (lines
        # 172-174) which calls merge_decisions().  We use save_decision()
        # (fingerprint-based upsert) instead because cascade only re-runs a
        # subset of analyzers.  merge_decisions() does a full three-way merge
        # that marks decisions as stale if their fingerprint is absent from
        # the "new" set — since non-cascaded analyzers didn't run, their
        # decisions would be incorrectly staled.  save_decision() avoids this
        # by only inserting/updating the cascade-produced decisions.
        # Consequence: stale detection is not available in the cascade path.
        # Full stale detection happens on the next complete pipeline.run().
        new_dicts = [decision_to_store_dict(d) for d in all_decisions]

        # Track what's new vs existing for warnings
        existing_fps = {
            d["fingerprint"]
            for d in store.get_all_decisions()
            if d.get("chosen_option") != "__stale__"
        }

        new_count = 0
        updated_count = 0
        for d in new_dicts:
            fp = d.get("fingerprint", "")
            if fp in existing_fps:
                updated_count += 1
            else:
                new_count += 1
            store.save_decision(d)

        # Step 5: Build warnings
        # (from 06-decision-workflow.md lines 173-183)
        warnings: list[str] = []
        if new_count > 0:
            warnings.append(
                f"{new_count} new decision(s) generated "
                f"as a result of resolving {decision_id}"
            )

        logger.info(
            "Cascade for %s: %d new, %d updated decisions",
            decision_id,
            new_count,
            updated_count,
        )

        return warnings

    @staticmethod
    def _sort_by_dependencies(analyzers: list[Analyzer]) -> list[Analyzer]:
        """Topological sort of analyzers by depends_on field.

        If no dependencies, original order is preserved.

        (from 03-conflict-detection-engine.md: depends_on field retained for
        future extensibility, no current analyzers use it)
        """
        by_name = {a.name: a for a in analyzers}
        visited: set[str] = set()
        result: list[Analyzer] = []

        def visit(analyzer: Analyzer) -> None:
            name = analyzer.name
            if name in visited:
                return
            visited.add(name)
            for dep_name in analyzer.depends_on:
                dep = by_name.get(dep_name)
                if dep is not None:
                    visit(dep)
            result.append(analyzer)

        for a in analyzers:
            visit(a)

        return result
