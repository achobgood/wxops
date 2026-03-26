"""Conflict detection analyzers for CUCM-to-Webex migration.

Linter-pattern analyzers that sweep the mapped inventory and produce
Decision objects for conflicts, ambiguities, and incompatibilities.

(from 03-conflict-detection-engine.md — linter pattern)
(from 07-idempotency-resumability.md — fingerprint-based identity)
"""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from wxcli.migration.models import (
    Decision,
    DecisionOption,
    DecisionType,
)
from wxcli.migration.store import MigrationStore


class Analyzer(ABC):
    """Base class for all conflict/decision analyzers.

    Each analyzer sweeps the full inventory via MigrationStore and produces
    Decision objects for patterns it detects.  Analyzers are independent —
    they don't call each other.

    (from 03-conflict-detection-engine.md, Analyzer ABC)
    (from 07-idempotency-resumability.md, fingerprint method requirement)
    """

    name: str = ""
    decision_types: list[DecisionType]
    depends_on: list[str]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # Default mutable class attrs to empty lists if not overridden
        if "decision_types" not in cls.__dict__:
            cls.decision_types = []
        if "depends_on" not in cls.__dict__:
            cls.depends_on = []

    @abstractmethod
    def analyze(self, store: MigrationStore) -> list[Decision]:
        """Sweep the inventory, return decisions found."""
        ...

    @abstractmethod
    def fingerprint(self, decision_type: DecisionType, context: dict[str, Any]) -> str:
        """Compute deterministic fingerprint from causal data.

        MUST include:
        - The triggering condition (e.g., which DN is shared)
        - The identity of all affected objects (e.g., which owners/devices)
        - Any data whose change would invalidate a previous resolution

        MUST NOT include:
        - Display-only fields (labels, descriptions)
        - Timestamps, run IDs, or sequential counters
        - Derived fields that could change without the condition changing

        (from 07-idempotency-resumability.md lines 30-43)
        """
        ...

    def _hash_fingerprint(self, data: dict[str, Any]) -> str:
        """Hash a dict into a 16-char hex fingerprint."""
        canonical = json.dumps(data, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]

    def _create_decision(
        self,
        store: MigrationStore,
        decision_type: DecisionType,
        severity: str,
        summary: str,
        context: dict[str, Any],
        options: list[DecisionOption],
        affected_objects: list[str],
    ) -> Decision:
        """Helper to create a well-formed Decision with auto-generated ID and fingerprint."""
        ctx = dict(context)
        if affected_objects:
            ctx["_affected_objects"] = affected_objects
        return Decision(
            decision_id=store.next_decision_id(),
            type=decision_type,
            severity=severity,
            summary=summary,
            context=ctx,
            options=options,
            affected_objects=affected_objects,
            fingerprint=self.fingerprint(decision_type, context),
            run_id=store.current_run_id,
        )

    def _get_existing_decisions_for_type(
        self, store: MigrationStore, decision_type: DecisionType
    ) -> dict[str, dict[str, Any]]:
        """Get existing mapper-produced decisions indexed by affected object canonical_id.

        Returns {canonical_id: decision_dict} for all decisions of the given type.
        Used by analyzers to skip objects that already have mapper-produced decisions.

        (from phase-06-analyzers.md, Decision Ownership Table)
        """
        all_decisions = store.get_all_decisions()
        result: dict[str, dict[str, Any]] = {}
        for dec in all_decisions:
            if dec.get("type") == decision_type.value:
                affected = dec.get("context", {}).get("_affected_objects", [])
                for obj_id in affected:
                    result[obj_id] = dec
        return result


@dataclass
class AnalysisResult:
    """Aggregate result from running all analyzers.

    (from 03-conflict-detection-engine.md, AnalysisPipeline.run return type)
    """

    decisions: list[Decision] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)
    run_id: str = ""


# Re-export common types for analyzer implementations
__all__ = [
    "Analyzer",
    "AnalysisResult",
    "Decision",
    "DecisionOption",
    "DecisionType",
]
