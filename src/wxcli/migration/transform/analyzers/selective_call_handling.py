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
        return []

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
