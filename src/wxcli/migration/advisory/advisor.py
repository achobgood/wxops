"""ArchitectureAdvisor — cross-cutting migration advisory analyzer.

Runs after the 12 standard analyzers in a two-phase pipeline.
Reads the full canonical model + merged decisions from the store.
Produces ARCHITECTURE_ADVISORY decisions.

(from migration-advisory-design.md §4.4)
"""

from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.models import DecisionOption, DecisionType
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.analyzers import Analyzer, Decision
from wxcli.migration.advisory.advisory_patterns import (
    ALL_ADVISORY_PATTERNS,
    AdvisoryFinding,
)

logger = logging.getLogger(__name__)


class ArchitectureAdvisor(Analyzer):
    """Cross-cutting advisory analyzer producing ARCHITECTURE_ADVISORY decisions.

    Not registered in ALL_ANALYZERS — runs separately in Phase 2 of the
    analysis pipeline, after the first 12 analyzers have merged their
    decisions into the store.
    """

    name = "architecture_advisor"
    decision_types = [DecisionType.ARCHITECTURE_ADVISORY]
    depends_on: list[str] = []

    def analyze(self, store: MigrationStore) -> list[Decision]:
        """Run all advisory patterns and convert findings to Decisions."""
        findings: list[AdvisoryFinding] = []
        for pattern_fn in ALL_ADVISORY_PATTERNS:
            try:
                findings.extend(pattern_fn(store))
            except Exception as exc:
                logger.warning(
                    "Advisory pattern %s failed: %s",
                    getattr(pattern_fn, "__name__", "?"),
                    exc,
                )
        return [self._finding_to_decision(store, f) for f in findings]

    def _finding_to_decision(
        self, store: MigrationStore, finding: AdvisoryFinding
    ) -> Decision:
        """Convert an AdvisoryFinding to a Decision.

        The context dict includes affected_ids (sorted) which the fingerprint
        method reads. _create_decision injects _affected_objects AFTER
        fingerprint() is called, so we use affected_ids in context for
        deterministic fingerprinting.
        """
        context = {
            "pattern_name": finding.pattern_name,
            "detail": finding.detail,
            "category": finding.category,
            "affected_ids": sorted(finding.affected_objects),
        }
        decision = self._create_decision(
            store=store,
            decision_type=DecisionType.ARCHITECTURE_ADVISORY,
            severity=finding.severity,
            summary=finding.summary,
            context=context,
            options=[
                DecisionOption(
                    id="accept",
                    label="Apply recommendation",
                    impact=finding.detail,
                ),
                DecisionOption(
                    id="ignore",
                    label="Migrate as planned",
                    impact="No change to migration plan",
                ),
            ],
            affected_objects=finding.affected_objects,
        )
        # Advisory decisions ARE recommendations — set immediately
        decision.recommendation = finding.recommendation
        decision.recommendation_reasoning = finding.recommendation_reasoning
        return decision

    def fingerprint(
        self, decision_type: DecisionType, context: dict[str, Any]
    ) -> str:
        """Fingerprint uses pattern_name + affected_ids.

        The _affected_objects key is injected by _create_decision() AFTER
        fingerprint() is called. So we use affected_ids which is set in
        the context dict before _create_decision() is called.
        """
        return self._hash_fingerprint(
            {
                "pattern": context.get("pattern_name"),
                "affected": context.get("affected_ids", []),
            }
        )
