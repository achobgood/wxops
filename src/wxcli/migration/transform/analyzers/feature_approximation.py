"""Feature approximation analyzer for CUCM-to-Webex migration.

Finds CTI route points mapped to auto attendants with complex/unmappable
scripts, hunt pilots with non-standard algorithms, and call queues with
agent limit warnings that require approximation in Webex.

FEATURE_APPROXIMATION is a mapper-owned decision type — the feature_mapper
and routing_mapper already produce these during transform.  This analyzer
backfills any objects the mappers missed or that acquired warnings after
initial mapping.

(from 03-conflict-detection-engine.md, linter pattern)
(from phase-06-analyzers.md, Decision Ownership Table — FEATURE_APPROXIMATION is mapper-owned)
"""

from __future__ import annotations

from typing import Any

from wxcli.migration.models import DecisionOption, DecisionType
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.analyzers import Analyzer, Decision


# ---------------------------------------------------------------------------
# Approximation detection keywords
# ---------------------------------------------------------------------------
# These appear in warnings/errors emitted by feature_mapper and routing_mapper
# when a CUCM construct cannot be directly mapped to Webex.

_APPROXIMATION_KEYWORDS = (
    "approximat",
    "complex script",
    "fidelity",
    "not supported",
    "agent limit",
)


def _extract_approximation_issues(
    warnings: list[Any], errors: list[Any]
) -> list[str]:
    """Extract warning/error strings that indicate approximation was needed."""
    issues: list[str] = []
    for source in (warnings, errors):
        for item in source:
            if not isinstance(item, str):
                continue
            item_lower = item.lower()
            if any(kw in item_lower for kw in _APPROXIMATION_KEYWORDS):
                issues.append(item)
    return issues


class FeatureApproximationAnalyzer(Analyzer):
    """Detects mapped features that required approximation from CUCM to Webex.

    Sweeps three object types for approximation indicators:

    - **auto_attendant** — CTI route points mapped to AA; checks for
      unmappable scripts (business_hours_menu or after_hours_menu is None)
      and warning strings about script approximation.

    - **hunt_group** — Hunt pilots with non-standard algorithms; checks
      for warning strings about algorithm approximation.

    - **call_queue** — Queues that exceeded Webex agent limits or had
      unsupported features; checks for agent limit warnings.

    Skips objects that already have a mapper-produced FEATURE_APPROXIMATION
    decision.

    (from 03-conflict-detection-engine.md, feature approximation linter)
    """

    name = "feature_approximation"
    decision_types = [DecisionType.FEATURE_APPROXIMATION]
    depends_on: list[str] = []

    # Object types to sweep, with type-specific checks
    _FEATURE_TYPES = ("auto_attendant", "hunt_group", "call_queue")

    def analyze(self, store: MigrationStore) -> list[Decision]:
        """Sweep AA, HG, and CQ objects for approximation indicators."""
        # Existing mapper-produced decisions indexed by canonical_id
        existing = self._get_existing_decisions_for_type(
            store, DecisionType.FEATURE_APPROXIMATION
        )

        decisions: list[Decision] = []

        for feature_type in self._FEATURE_TYPES:
            objects = store.get_objects(feature_type)
            for obj in objects:
                canonical_id = obj.get("canonical_id", "")

                # Skip if mapper already produced a decision for this object
                if canonical_id in existing:
                    continue

                issues = self._detect_approximation_issues(feature_type, obj)
                if not issues:
                    continue

                severity = self._determine_severity(feature_type, obj, issues)
                name = obj.get("name") or obj.get("display_name") or canonical_id

                summary = (
                    f"{feature_type} '{name}' requires approximation: "
                    f"{'; '.join(issues[:3])}"
                )
                if len(issues) > 3:
                    summary += f" (+{len(issues) - 3} more)"

                context = {
                    "feature_type": feature_type,
                    "canonical_id": canonical_id,
                    "name": name,
                    "approximation_issues": issues,
                }

                options = [
                    DecisionOption(
                        id="accept",
                        label="Accept approximation",
                        impact=(
                            f"{feature_type} '{name}' migrated with best-effort "
                            f"approximation ({len(issues)} issue(s))"
                        ),
                    ),
                    DecisionOption(
                        id="manual",
                        label="Configure manually post-migration",
                        impact=(
                            f"{feature_type} '{name}' flagged for manual "
                            f"post-migration configuration"
                        ),
                    ),
                    DecisionOption(
                        id="skip",
                        label="Skip this feature",
                        impact=f"{feature_type} '{name}' excluded from migration",
                    ),
                ]

                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.FEATURE_APPROXIMATION,
                    severity=severity,
                    summary=summary,
                    context=context,
                    options=options,
                    affected_objects=[canonical_id],
                )
                decisions.append(decision)

        return decisions

    def fingerprint(self, decision_type: DecisionType, context: dict[str, Any]) -> str:
        """Deterministic fingerprint from canonical_id + sorted approximation issues."""
        return self._hash_fingerprint({
            "type": decision_type.value,
            "canonical_id": context.get("canonical_id", ""),
            "approximation_issues": sorted(context.get("approximation_issues", [])),
        })

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_approximation_issues(
        feature_type: str, obj: dict[str, Any]
    ) -> list[str]:
        """Detect all approximation issues for a given feature object.

        Checks warnings/errors lists for approximation keywords, plus
        type-specific structural checks (e.g., None menus on auto_attendants).
        """
        warnings = obj.get("warnings") or []
        errors = obj.get("errors") or []
        issues = _extract_approximation_issues(warnings, errors)

        # Type-specific structural checks
        if feature_type == "auto_attendant":
            # None menus indicate an unmappable CTI route point script
            if obj.get("business_hours_menu") is None:
                issue = "business_hours_menu is None (unmappable CTI route point script)"
                if issue not in issues:
                    issues.append(issue)
            if obj.get("after_hours_menu") is None:
                issue = "after_hours_menu is None (unmappable CTI route point script)"
                if issue not in issues:
                    issues.append(issue)

        return issues

    @staticmethod
    def _determine_severity(
        feature_type: str,
        obj: dict[str, Any],
        issues: list[str],
    ) -> str:
        """Determine decision severity based on feature type and issues.

        HIGH:   auto_attendant with None menus (completely unmappable)
        MEDIUM: call_queue agent limit issues, hunt_group algorithm issues
        LOW:    minor approximations (warning-only, no structural problems)
        """
        if feature_type == "auto_attendant":
            # Unmappable menus are HIGH severity
            if obj.get("business_hours_menu") is None or obj.get("after_hours_menu") is None:
                return "HIGH"

        # Agent limit issues are MEDIUM
        for issue in issues:
            if "agent limit" in issue.lower():
                return "MEDIUM"

        # Check for strong approximation keywords -> MEDIUM
        for issue in issues:
            issue_lower = issue.lower()
            if any(kw in issue_lower for kw in ("complex script", "not supported")):
                return "MEDIUM"

        # Minor approximations
        return "LOW"
