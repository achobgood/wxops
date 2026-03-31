"""Base class for all transform mappers.

Provides the Mapper ABC with map() abstract method, decision creation helpers,
fingerprint generation, and standard decision option builders.

(from 03b-transform-mappers.md, shared patterns section §13)
"""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from wxcli.migration.models import (
    CanonicalUser,
    Decision,
    DecisionOption,
    DecisionType,
    MapperResult,
    Provenance,
)
from wxcli.migration.store import MigrationStore


class Mapper(ABC):
    """Base class for all transform mappers.

    Each mapper reads CUCM canonical objects from the store, produces
    Webex canonical objects, and returns decisions for anything it
    can't cleanly map.

    (from 03b-transform-mappers.md, shared patterns — Mapper base class)
    """

    name: str = ""
    depends_on: list[str] = []

    @abstractmethod
    def map(self, store: MigrationStore) -> MapperResult:
        """Read CUCM canonical objects, produce Webex canonical objects + decisions."""
        ...

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
        """Helper to create a well-formed Decision with auto-generated ID and fingerprint.

        (from 03b-transform-mappers.md, shared patterns — _create_decision helper)
        """
        return Decision(
            decision_id=store.next_decision_id(),
            type=decision_type,
            severity=severity,
            summary=summary,
            context=context,
            options=options,
            affected_objects=affected_objects,
            fingerprint=self._fingerprint(decision_type, context),
            run_id=store.current_run_id,
        )

    def _fingerprint(self, decision_type: DecisionType, context: dict[str, Any]) -> str:
        """Deterministic fingerprint for idempotent decision identity.

        (from 03b-transform-mappers.md, shared patterns — _fingerprint helper)
        """
        key_data = json.dumps({"type": decision_type.value, **context}, sort_keys=True)
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Decision option builder helpers
# (from 03b-transform-mappers.md, shared patterns — Decision Option Builder)
# ---------------------------------------------------------------------------


def skip_option(impact: str = "Object not migrated") -> DecisionOption:
    """Create a 'Skip' decision option."""
    return DecisionOption(id="skip", label="Skip", impact=impact)


def manual_option(impact: str = "Requires manual configuration post-migration") -> DecisionOption:
    """Create a 'Manual' decision option."""
    return DecisionOption(id="manual", label="Manual", impact=impact)


def accept_option(impact: str) -> DecisionOption:
    """Create an 'Accept fidelity loss' decision option."""
    return DecisionOption(id="accept", label="Accept fidelity loss", impact=impact)


# ---------------------------------------------------------------------------
# Store serialization helper
# ---------------------------------------------------------------------------


def decision_to_store_dict(decision: Decision) -> dict[str, Any]:
    """Convert a Decision Pydantic model to the dict format store.save_decision() expects.

    The store expects:
    - type as string value (e.g., "LOCATION_AMBIGUOUS"), not the enum member
    - options as list of dicts (not DecisionOption models)
    - context as dict (not JSON string — the store handles serialization)

    affected_objects is embedded in context (as _affected_objects) since the
    decisions table has no dedicated column. merge_decisions() in Phase 10
    can read it from context when needed.
    """
    ctx = dict(decision.context)
    if decision.affected_objects:
        ctx["_affected_objects"] = decision.affected_objects
    return {
        "decision_id": decision.decision_id,
        "type": decision.type.value,
        "severity": decision.severity,
        "summary": decision.summary,
        "context": ctx,
        "options": [opt.model_dump() for opt in decision.options],
        "chosen_option": decision.chosen_option,
        "resolved_at": decision.resolved_at,
        "resolved_by": decision.resolved_by,
        "fingerprint": decision.fingerprint,
        "run_id": decision.run_id,
        "recommendation": decision.recommendation,
        "recommendation_reasoning": decision.recommendation_reasoning,
    }


# ---------------------------------------------------------------------------
# Shared mapper utilities (DRY — used by all 9 mappers)
# ---------------------------------------------------------------------------


def extract_provenance(data: dict[str, Any]) -> Provenance:
    """Extract Provenance from a stored object dict.

    Handles both Pydantic-serialized dicts (from store.get_objects) and
    raw dicts. Gracefully handles missing or malformed extracted_at.
    """
    prov = data.get("provenance", {})
    extracted_at = prov.get("extracted_at")
    if isinstance(extracted_at, str):
        try:
            extracted_at = datetime.fromisoformat(extracted_at)
        except (ValueError, TypeError):
            extracted_at = datetime.now(timezone.utc)
    elif extracted_at is None:
        extracted_at = datetime.now(timezone.utc)

    return Provenance(
        source_system=prov.get("source_system", "cucm"),
        source_id=prov.get("source_id", ""),
        source_name=prov.get("source_name", ""),
        cluster=prov.get("cluster"),
        extracted_at=extracted_at,
        cucm_version=prov.get("cucm_version"),
    )


def enrich_user(store: MigrationStore, user_id: str, **fields: Any) -> None:
    """Update fields on a CanonicalUser in the store.

    Re-reads the user dict, merges the provided fields, reconstructs
    a CanonicalUser (filtering to known model fields), and upserts.
    Used by enrichment mappers (VoicemailMapper, CallSettingsMapper).
    """
    user_data = store.get_object(user_id)
    if not user_data:
        return
    user_data.update(fields)
    enriched = CanonicalUser(**{
        k: v for k, v in user_data.items()
        if k in CanonicalUser.model_fields
    })
    store.upsert_object(enriched)


def hash_id(value: str) -> str:
    """Generate a deterministic short hash for canonical IDs."""
    return hashlib.sha256(value.encode()).hexdigest()[:12]
