"""DN ambiguity analyzer — finds lines with AMBIGUOUS E.164 classification.

The line_mapper's E.164 normalization algorithm classifies each DN as
EXTENSION, NATIONAL, E164, or AMBIGUOUS.  This analyzer surfaces the
AMBIGUOUS cases so a human can make the call.

Decision ownership: MAPPER-OWNED (line_mapper produces DN_AMBIGUOUS decisions).
This analyzer checks for existing mapper decisions before creating new ones.

(from 03-conflict-detection-engine.md, DN ambiguity detection)
(from 03b-transform-mappers.md, line_mapper E.164 algorithm lines 208-211)
(from 07-idempotency-resumability.md, fingerprint-based identity)
"""

from __future__ import annotations

from typing import Any

from wxcli.migration.models import DecisionOption, DecisionType
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.analyzers import Analyzer, Decision


class DNAmbiguityAnalyzer(Analyzer):
    """Finds DNs where E.164 classification is AMBIGUOUS.

    The line_mapper may already have produced DN_AMBIGUOUS decisions for some
    lines.  This analyzer only creates decisions for ambiguous lines that
    don't already have one, acting as a safety net for anything the mapper
    missed.
    """

    name = "dn_ambiguity"
    decision_types = [DecisionType.DN_AMBIGUOUS]

    def analyze(self, store: MigrationStore) -> list[Decision]:
        """Sweep all lines, find AMBIGUOUS classification, skip already-decided."""
        decisions: list[Decision] = []

        # Step 1: Get existing mapper-produced DN_AMBIGUOUS decisions
        existing = self._get_existing_decisions_for_type(store, DecisionType.DN_AMBIGUOUS)

        # Step 2: Load all lines and filter for AMBIGUOUS classification
        lines = store.get_objects("line")
        if not lines:
            return decisions

        for line in lines:
            classification = line.get("classification")
            if classification != "AMBIGUOUS":
                continue

            canonical_id = line.get("canonical_id", "")
            if not canonical_id:
                continue

            # Skip if mapper already produced a decision for this line
            if canonical_id in existing:
                continue

            dn_pattern = line.get("cucm_pattern", "")
            partition = line.get("route_partition_name", "")
            # Count fixed (non-wildcard) digits after stripping + prefix
            # e.g., "+1555XXXX" -> "1555XXXX" -> count chars that aren't X/x/. -> 4
            stripped = dn_pattern.lstrip("+")
            dn_length = sum(1 for c in stripped if c not in "Xx.![]")

            severity = "LOW" if dn_length <= 4 else "MEDIUM"

            context = {
                "dn": dn_pattern,
                "partition": partition,
                "dn_length": dn_length,
                "canonical_id": canonical_id,
            }

            options = [
                DecisionOption(
                    id="extension_only",
                    label="Treat as Extension",
                    impact=f"Map '{dn_pattern}' as internal extension only — no DID",
                ),
                DecisionOption(
                    id="national",
                    label="Treat as National Number",
                    impact=f"Map '{dn_pattern}' as national-format DID",
                ),
                DecisionOption(
                    id="e164",
                    label="Treat as E.164",
                    impact=f"Map '{dn_pattern}' as full E.164 DID with + prefix",
                ),
                DecisionOption(
                    id="skip",
                    label="Skip",
                    impact="Leave DN unmapped — manual intervention required",
                ),
            ]

            decision = self._create_decision(
                store=store,
                decision_type=DecisionType.DN_AMBIGUOUS,
                severity=severity,
                summary=(
                    f"DN '{dn_pattern}' in partition '{partition}' has ambiguous "
                    f"E.164 classification ({dn_length} digits)"
                ),
                context=context,
                options=options,
                affected_objects=[canonical_id],
            )
            decisions.append(decision)

        return decisions

    def fingerprint(self, decision_type: DecisionType, context: dict[str, Any]) -> str:
        """Deterministic fingerprint from DN pattern, partition, and line ID.

        Includes:
        - dn (the pattern that's ambiguous)
        - partition (routing scope — different partitions are different decisions)
        - canonical_id (the specific line object)

        (from 07-idempotency-resumability.md lines 30-43)
        """
        return self._hash_fingerprint({
            "type": decision_type.value,
            "dn": context.get("dn"),
            "partition": context.get("partition"),
            "canonical_id": context.get("canonical_id"),
        })
