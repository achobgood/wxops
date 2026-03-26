"""Workspace license tier analyzer for CUCM-to-Webex migration.

Determines whether each workspace needs a Workspace or Professional Workspace
Webex Calling license based on its configured features.

WORKSPACE_LICENSE_TIER is a mapper-owned decision type — the
workspace_mapper may already produce these during transform.
This analyzer catches workspaces the mapper didn't cover and
workspaces whose feature profile suggests a tier mismatch.

(from 03-conflict-detection-engine.md, linter pattern)
(from phase-06-analyzers.md, Decision Ownership Table — WORKSPACE_LICENSE_TIER is mapper-owned)
"""

from __future__ import annotations

from typing import Any

from wxcli.migration.models import DecisionOption, DecisionType
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.analyzers import Analyzer, Decision


# ---------------------------------------------------------------------------
# Feature indicators that suggest Professional Workspace license is needed
# ---------------------------------------------------------------------------
# Each entry: (field_name, check_fn, feature_label)
# check_fn receives the field value and returns True if the feature IS present.

def _has_value(val: Any) -> bool:
    """True if the value is not None and not empty/falsy."""
    if val is None:
        return False
    if isinstance(val, (str, list, dict)) and not val:
        return False
    return True


def _is_hotdesking_on(val: Any) -> bool:
    return isinstance(val, str) and val.lower() == "on"


_PROFESSIONAL_INDICATORS: list[tuple[str, Any, str]] = [
    ("hotdesking_status", _is_hotdesking_on, "hot-desking enabled"),
    ("phone_number", _has_value, "DID phone number assigned"),
]

# Features detected via cross-references (relationship, label)
_XREF_INDICATORS: list[tuple[str, str]] = [
    ("workspace_has_voicemail", "voicemail configured"),
    ("workspace_has_call_forwarding", "call forwarding configured"),
    ("workspace_has_shared_line", "shared line appearance"),
]


class WorkspaceLicenseAnalyzer(Analyzer):
    """Determines Workspace vs Professional Workspace license for workspaces.

    Webex Calling workspaces can be provisioned with Workspace or
    Professional Workspace licenses. Several features require Professional Workspace:
    - Hot-desking
    - DID phone numbers
    - Voicemail
    - Call forwarding
    - Shared line appearances
    - Most /telephony/config/workspaces/ settings

    The workspace_mapper sets ``license_tier`` during transform when the
    answer is obvious.  This analyzer catches workspaces where:
    1. The mapper didn't set a tier (license_tier is None)
    2. The workspace has feature indicators that create ambiguity

    (from docs/reference/devices-workspaces.md, Workspace vs Professional Workspace)
    """

    name = "workspace_license"
    decision_types = [DecisionType.WORKSPACE_LICENSE_TIER]

    def analyze(self, store: MigrationStore) -> list[Decision]:
        """Sweep workspaces for undecided or ambiguous license tiers."""
        # Existing mapper-produced decisions indexed by canonical_id
        existing = self._get_existing_decisions_for_type(
            store, DecisionType.WORKSPACE_LICENSE_TIER
        )

        decisions: list[Decision] = []
        workspaces = store.get_objects("workspace")

        for ws in workspaces:
            canonical_id = ws.get("canonical_id", "")

            # Skip workspaces the mapper already produced a decision for
            if canonical_id in existing:
                continue

            license_tier = ws.get("license_tier")
            features_detected = self._detect_features(ws, store, canonical_id)

            # Case 1: mapper already set a definite tier and no conflicting features
            if license_tier is not None and not features_detected:
                continue

            # Case 2: tier is set but features suggest it might be wrong
            # (e.g., mapper said Workspace but workspace has voicemail)
            if license_tier == "Workspace" and features_detected:
                summary = (
                    f"Workspace '{ws.get('display_name', canonical_id)}' set to Workspace "
                    f"but has Professional Workspace features: {', '.join(features_detected)}"
                )
            # Case 3: no tier set at all
            elif license_tier is None:
                if features_detected:
                    summary = (
                        f"Workspace '{ws.get('display_name', canonical_id)}' needs license "
                        f"tier — detected features: {', '.join(features_detected)}"
                    )
                else:
                    summary = (
                        f"Workspace '{ws.get('display_name', canonical_id)}' needs license "
                        f"tier assignment (no feature indicators detected)"
                    )
            else:
                # Professional Workspace tier set, features present — consistent, no decision needed
                continue

            context = {
                "canonical_id": canonical_id,
                "display_name": ws.get("display_name"),
                "license_tier": license_tier,
                "features_detected": features_detected,
            }

            options = [
                DecisionOption(
                    id="workspace",
                    label="Workspace",
                    impact="Workspace license; limited to basic calling features",
                ),
                DecisionOption(
                    id="professional",
                    label="Professional Workspace",
                    impact="Professional Workspace license; full calling features including voicemail, forwarding, hot-desking",
                ),
                DecisionOption(
                    id="skip",
                    label="Skip this workspace",
                    impact="1 workspace excluded from migration",
                ),
            ]

            decision = self._create_decision(
                store=store,
                decision_type=DecisionType.WORKSPACE_LICENSE_TIER,
                severity="MEDIUM",
                summary=summary,
                context=context,
                options=options,
                affected_objects=[canonical_id],
            )
            decisions.append(decision)

        return decisions

    def fingerprint(self, decision_type: DecisionType, context: dict[str, Any]) -> str:
        """Deterministic fingerprint from canonical_id + license tier + detected features.

        Includes features_detected so that discovering new Professional Workspace-tier
        features invalidates a previous "Workspace" resolution.
        (from 07-idempotency-resumability.md: include data whose change would
        invalidate a previous resolution)
        """
        return self._hash_fingerprint({
            "type": decision_type.value,
            "canonical_id": context.get("canonical_id", ""),
            "license_tier": context.get("license_tier"),
            "features_detected": sorted(context.get("features_detected", [])),
        })

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_features(
        ws: dict[str, Any],
        store: MigrationStore,
        canonical_id: str,
    ) -> list[str]:
        """Detect features that suggest Professional Workspace license is needed.

        Checks both workspace data fields and cross-references to
        related objects (voicemail profiles, call forwarding, shared lines).
        """
        features: list[str] = []

        # Check data fields
        for field_name, check_fn, label in _PROFESSIONAL_INDICATORS:
            if check_fn(ws.get(field_name)):
                features.append(label)

        # Check multiple line appearances (>1 line suggests shared/complex config)
        line_refs = store.find_cross_refs(canonical_id, "workspace_has_line")
        if len(line_refs) > 1:
            features.append(f"multiple lines ({len(line_refs)})")

        # Check cross-reference indicators
        for relationship, label in _XREF_INDICATORS:
            refs = store.find_cross_refs(canonical_id, relationship)
            if refs:
                features.append(label)

        return features
