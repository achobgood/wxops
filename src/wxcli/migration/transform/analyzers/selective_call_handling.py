"""Selective call handling analyzer for CUCM-to-Webex migration.

Detects CUCM CSS/partition patterns that imply per-caller routing differences
and produces FEATURE_APPROXIMATION advisory decisions recommending Webex
selective call handling features (Selective Forward / Accept / Reject /
Priority Alert).

Three heuristics:
1. Multi-partition DN — same DN in 2+ partitions reachable via different
   user CSSes (internal vs external routing split).
2. Low-membership partition — partition with few DNs that appears in only
   a subset of CSSes (VIP/priority bypass pattern).
3. Naming convention — partition name contains VIP/executive/priority
   keywords (weak signal, only LOW severity unless paired with structural
   signal).

This analyzer reuses DecisionType.FEATURE_APPROXIMATION with a distinguishing
context key `selective_call_handling_pattern`. The recommendation rule and
report renderer key off this context key.

Spec: docs/superpowers/specs/2026-04-10-selective-call-forwarding.md
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from wxcli.migration.models import DecisionOption, DecisionType
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.analyzers import Analyzer, Decision


_VIP_KEYWORDS = (
    "vip",
    "executive",
    "exec",
    "priority",
    "direct",
    "bypass",
    "afterhours",
    "after_hours",
    "after-hours",
    "emergency",
)


class SelectiveCallHandlingAnalyzer(Analyzer):
    """Detects CSS/partition patterns suggesting selective call handling.

    See module docstring for the three heuristics. Produces
    FEATURE_APPROXIMATION decisions with context key
    `selective_call_handling_pattern` set to one of:
        - "multi_partition_dn"
        - "low_membership_partition"
        - "naming_convention"
    """

    name = "selective_call_handling"
    decision_types = [DecisionType.FEATURE_APPROXIMATION]
    # Run after css_routing so CSS decomposition decisions are merged first.
    depends_on = ["css_routing"]

    def analyze(self, store: MigrationStore) -> list[Decision]:
        decisions: list[Decision] = []
        decisions.extend(self._heuristic_multi_partition_dn(store))
        decisions.extend(self._heuristic_low_membership_partition(store))
        decisions.extend(self._heuristic_naming_convention(store, decisions))
        return decisions

    def fingerprint(
        self, decision_type: DecisionType, context: dict[str, Any]
    ) -> str:
        """Deterministic fingerprint from pattern type + natural keys."""
        return self._hash_fingerprint({
            "type": decision_type.value,
            "pattern": context.get("selective_call_handling_pattern", ""),
            "primary_key": context.get("primary_key", ""),
            "partitions": sorted(context.get("partitions", [])),
            "user": context.get("user_canonical_id", ""),
        })

    # ------------------------------------------------------------------
    # Heuristics — implemented in later tasks
    # ------------------------------------------------------------------

    def _heuristic_multi_partition_dn(
        self, store: MigrationStore
    ) -> list[Decision]:
        """Find DNs in 2+ partitions reachable via different user CSSes."""
        # Build {dn_number: {partition_name: dn_canonical_id}} from cross_refs.
        # The dn_canonical_id form is "dn:{number}:{partition}".
        rows = store.conn.execute(
            "SELECT from_id, to_id FROM cross_refs WHERE relationship = 'dn_in_partition'"
        ).fetchall()
        dn_to_partitions: dict[str, dict[str, str]] = defaultdict(dict)
        for row in rows:
            dn_canonical_id = row["from_id"]
            partition_canonical_id = row["to_id"]
            # Extract the dn number from "dn:{number}:{partition}"
            parts = dn_canonical_id.split(":", 2)
            if len(parts) < 3:
                continue
            dn_number = parts[1]
            partition_name = (
                partition_canonical_id.split(":", 1)[1]
                if ":" in partition_canonical_id
                else partition_canonical_id
            )
            dn_to_partitions[dn_number][partition_name] = dn_canonical_id

        # Map user_id → set of CSS canonical_ids and CSS → set of partition_ids
        user_csses = self._build_user_css_index(store)
        css_partitions = self._build_css_partition_index(store)
        # Map dn canonical_id → owner user canonical_id (from user_has_primary_dn)
        owner_rows = store.conn.execute(
            "SELECT from_id, to_id FROM cross_refs WHERE relationship = 'user_has_primary_dn'"
        ).fetchall()
        dn_owner: dict[str, str] = {row["to_id"]: row["from_id"] for row in owner_rows}

        decisions: list[Decision] = []
        for dn_number, partition_map in sorted(dn_to_partitions.items()):
            if len(partition_map) < 2:
                continue

            # Multi-site filter (mitigation 8a):
            # Get owners across all partition variants for this DN number.
            owner_ids: set[str] = set()
            for dn_cid in partition_map.values():
                owner = dn_owner.get(dn_cid)
                if owner:
                    owner_ids.add(owner)
            owner_locations = self._owner_locations(store, owner_ids)
            if len(owner_locations) > 1:
                # Multi-site routing pattern, not selective call handling.
                continue

            # Determine severity: MEDIUM if owning user's CSSes have
            # different scopes (different partition sets).
            primary_owner = next(iter(owner_ids), "")
            scopes = self._user_css_scopes(primary_owner, user_csses, css_partitions)
            severity = "MEDIUM" if self._scopes_differ(scopes) else "LOW"

            partitions_sorted = sorted(partition_map.keys())
            context = {
                "selective_call_handling_pattern": "multi_partition_dn",
                "primary_key": dn_number,
                "dn_number": dn_number,
                "partitions": partitions_sorted,
                "user_canonical_id": primary_owner,
                "recommended_webex_feature": "Selective Forward",
                "confidence": "HIGH" if severity == "MEDIUM" else "LOW",
            }
            options = self._build_options("Selective Forward")
            summary = (
                f"DN {dn_number} appears in {len(partitions_sorted)} partitions "
                f"({', '.join(partitions_sorted)}); CUCM caller-specific routing "
                f"pattern detected"
            )
            decisions.append(
                self._create_decision(
                    store=store,
                    decision_type=DecisionType.FEATURE_APPROXIMATION,
                    severity=severity,
                    summary=summary,
                    context=context,
                    options=options,
                    affected_objects=[primary_owner] if primary_owner else [],
                )
            )
        return decisions

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _build_user_css_index(
        self, store: MigrationStore
    ) -> dict[str, set[str]]:
        rows = store.conn.execute(
            "SELECT from_id, to_id FROM cross_refs WHERE relationship = 'user_has_css'"
        ).fetchall()
        index: dict[str, set[str]] = defaultdict(set)
        for row in rows:
            index[row["from_id"]].add(row["to_id"])
        return index

    def _build_css_partition_index(
        self, store: MigrationStore
    ) -> dict[str, set[str]]:
        rows = store.conn.execute(
            "SELECT from_id, to_id FROM cross_refs WHERE relationship = 'css_contains_partition'"
        ).fetchall()
        index: dict[str, set[str]] = defaultdict(set)
        for row in rows:
            index[row["from_id"]].add(row["to_id"])
        return index

    def _owner_locations(
        self, store: MigrationStore, owner_ids: set[str]
    ) -> set[str]:
        locations: set[str] = set()
        for owner_id in owner_ids:
            obj = store.get_object(owner_id)
            if obj is None:
                continue
            loc = obj.get("location_id")
            if loc:
                locations.add(loc)
        return locations

    def _user_css_scopes(
        self,
        user_id: str,
        user_csses: dict[str, set[str]],
        css_partitions: dict[str, set[str]],
    ) -> list[set[str]]:
        return [
            css_partitions.get(css_id, set())
            for css_id in user_csses.get(user_id, set())
        ]

    @staticmethod
    def _scopes_differ(scopes: list[set[str]]) -> bool:
        if len(scopes) < 2:
            return False
        # Any pair with non-empty symmetric difference → scopes differ.
        for i in range(len(scopes)):
            for j in range(i + 1, len(scopes)):
                if scopes[i] ^ scopes[j]:
                    return True
        return False

    @staticmethod
    def _build_options(recommended_feature: str) -> list[DecisionOption]:
        return [
            DecisionOption(
                id="accept",
                label=f"Configure {recommended_feature} post-migration",
                impact=(
                    f"Operator manually configures Webex {recommended_feature} "
                    f"to preserve CUCM caller-specific routing behavior"
                ),
            ),
            DecisionOption(
                id="skip",
                label="Skip — accept loss of caller-specific routing",
                impact=(
                    "Per-caller routing differences are not preserved; "
                    "callers reach the user via standard Webex routing"
                ),
            ),
        ]

    def _heuristic_low_membership_partition(
        self, store: MigrationStore
    ) -> list[Decision]:
        return []

    def _heuristic_naming_convention(
        self,
        store: MigrationStore,
        existing_decisions: list[Decision],
    ) -> list[Decision]:
        return []
