"""Voicemail compatibility analyzer for CUCM-to-Webex migration.

Finds voicemail profiles with Unity Connection features that lack
Webex Calling equivalents (fax-to-voicemail, non-standard message
storage, complex transfer routing).

VOICEMAIL_INCOMPATIBLE is a mapper-owned decision type — the
voicemail_mapper already produces these during transform.  This
analyzer backfills any profiles the mapper missed or that were
added after initial mapping.

(from 03-conflict-detection-engine.md, linter pattern)
(from phase-06-analyzers.md, Decision Ownership Table — VOICEMAIL_INCOMPATIBLE is mapper-owned)
"""

from __future__ import annotations

from typing import Any

from wxcli.migration.models import DecisionOption, DecisionType
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.analyzers import Analyzer, Decision


# ---------------------------------------------------------------------------
# Incompatibility detection helpers
# ---------------------------------------------------------------------------

def _has_fax_message(profile: dict[str, Any]) -> str | None:
    """Return issue string if fax-to-voicemail is configured."""
    fax = profile.get("fax_message")
    if fax:
        return "fax_message: Webex has no fax-to-voicemail"
    return None


def _has_nonstandard_storage(profile: dict[str, Any]) -> str | None:
    """Return issue string if message_storage uses non-standard settings."""
    storage = profile.get("message_storage")
    if storage is None:
        return None
    if isinstance(storage, str):
        normalized = storage.strip().lower()
        if normalized in ("", "standard", "default", "mailbox"):
            return None
        return f"message_storage '{storage}': non-standard storage not supported in Webex"
    if isinstance(storage, dict):
        # Dict-form storage — check for MWI-only or external indicators
        storage_type = storage.get("type", "").lower()
        if storage_type in ("mwi_only", "mwi-only", "external"):
            return f"message_storage type '{storage_type}': not supported in Webex"
        # Non-empty dict with unexpected keys suggests custom config
        if storage and storage_type not in ("", "standard", "default", "mailbox"):
            return f"message_storage type '{storage_type}': non-standard storage not supported in Webex"
    return None


def _has_complex_transfer(profile: dict[str, Any]) -> str | None:
    """Return issue string if transfer_to_number has complex routing."""
    transfer = profile.get("transfer_to_number")
    if transfer is None:
        return None
    if isinstance(transfer, str) and transfer.strip():
        # Simple transfer number — this maps to Webex forwarding, minor gap
        return None
    if isinstance(transfer, dict):
        # Dict-form transfer implies complex routing rules
        rules = transfer.get("rules") or transfer.get("conditions")
        if rules:
            return "transfer_to_number: complex routing rules cannot map to Webex"
        # Has a transfer config dict but no complex rules — check for non-empty
        transfer_type = transfer.get("type", "")
        if transfer_type and transfer_type.lower() not in ("", "simple", "direct"):
            return f"transfer_to_number type '{transfer_type}': complex transfer not supported in Webex"
    return None


def _check_warnings(profile: dict[str, Any]) -> list[str]:
    """Extract voicemail-related warnings from the object's warnings list."""
    warnings = profile.get("warnings") or []
    issues: list[str] = []
    for w in warnings:
        if not isinstance(w, str):
            continue
        w_lower = w.lower()
        if any(kw in w_lower for kw in (
            "voicemail", "unity", "fax", "message storage",
            "not supported", "incompatible", "mwi",
        )):
            issues.append(f"warning: {w}")
    return issues


# Severity assignment: fax and complex transfer are MEDIUM;
# non-standard storage and warning-only issues are MEDIUM;
# simple warnings are LOW.
_HIGH_KEYWORDS = frozenset()  # nothing is HIGH for voicemail incompatibilities
_MEDIUM_KEYWORDS = frozenset((
    "fax_message", "message_storage", "transfer_to_number",
))


class VoicemailCompatibilityAnalyzer(Analyzer):
    """Detects voicemail profiles with Unity Connection features that
    lack Webex Calling equivalents.

    Checks each voicemail_profile object for:
    - fax_message configured (Webex has no fax-to-voicemail)
    - message_storage with MWI-only or external storage
    - transfer_to_number with complex routing rules
    - Warnings on the object indicating incompatibility

    Skips profiles already covered by voicemail_mapper decisions.

    (from 03-conflict-detection-engine.md, voicemail compatibility linter)
    """

    name = "voicemail_compatibility"
    decision_types = [DecisionType.VOICEMAIL_INCOMPATIBLE]
    depends_on: list[str] = []

    def analyze(self, store: MigrationStore) -> list[Decision]:
        """Sweep voicemail profiles for incompatible features."""
        # Existing mapper-produced decisions indexed by canonical_id
        existing = self._get_existing_decisions_for_type(
            store, DecisionType.VOICEMAIL_INCOMPATIBLE
        )

        decisions: list[Decision] = []
        profiles = store.get_objects("voicemail_profile")

        for profile in profiles:
            canonical_id = profile.get("canonical_id", "")

            # Skip if mapper already produced a decision for this profile
            if canonical_id in existing:
                continue

            incompatible_features = self._detect_incompatibilities(profile)
            if not incompatible_features:
                continue

            severity = self._determine_severity(incompatible_features)
            profile_name = (
                profile.get("cucm_voicemail_profile_name")
                or profile.get("name")
                or canonical_id
            )
            user_canonical_id = profile.get("user_canonical_id", "")

            summary = (
                f"Voicemail profile '{profile_name}' has {len(incompatible_features)} "
                f"feature(s) incompatible with Webex: "
                f"{', '.join(self._feature_names(incompatible_features))}"
            )

            context = {
                "canonical_id": canonical_id,
                "profile_name": profile_name,
                "user_canonical_id": user_canonical_id,
                "incompatible_features": incompatible_features,
            }

            options = [
                DecisionOption(
                    id="accept",
                    label="Accept fidelity loss",
                    impact=(
                        f"Voicemail profile '{profile_name}' migrated without "
                        f"{', '.join(self._feature_names(incompatible_features))}"
                    ),
                ),
                DecisionOption(
                    id="manual",
                    label="Configure manually post-migration",
                    impact=(
                        f"Voicemail profile '{profile_name}' flagged for manual "
                        f"post-migration configuration"
                    ),
                ),
                DecisionOption(
                    id="skip",
                    label="Skip this profile",
                    impact=f"Voicemail profile '{profile_name}' excluded from migration",
                ),
            ]

            affected = [canonical_id]
            if user_canonical_id:
                affected.append(user_canonical_id)

            decision = self._create_decision(
                store=store,
                decision_type=DecisionType.VOICEMAIL_INCOMPATIBLE,
                severity=severity,
                summary=summary,
                context=context,
                options=options,
                affected_objects=affected,
            )
            decisions.append(decision)

        return decisions

    def fingerprint(self, decision_type: DecisionType, context: dict[str, Any]) -> str:
        """Deterministic fingerprint from canonical_id + sorted incompatible feature names."""
        features = context.get("incompatible_features", [])
        return self._hash_fingerprint({
            "type": decision_type.value,
            "canonical_id": context.get("canonical_id", ""),
            "incompatible_features": sorted(self._feature_names(features)),
        })

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_incompatibilities(profile: dict[str, Any]) -> list[str]:
        """Return list of issue description strings for all detected incompatibilities."""
        issues: list[str] = []

        fax_issue = _has_fax_message(profile)
        if fax_issue:
            issues.append(fax_issue)

        storage_issue = _has_nonstandard_storage(profile)
        if storage_issue:
            issues.append(storage_issue)

        transfer_issue = _has_complex_transfer(profile)
        if transfer_issue:
            issues.append(transfer_issue)

        warning_issues = _check_warnings(profile)
        issues.extend(warning_issues)

        return issues

    @staticmethod
    def _feature_names(issues: list[str]) -> list[str]:
        """Extract short feature names from issue description strings.

        E.g., "fax_message: Webex has no fax-to-voicemail" -> "fax_message"
        """
        names: list[str] = []
        for issue in issues:
            if ":" in issue:
                name = issue.split(":")[0].strip()
            else:
                name = issue[:40]
            names.append(name)
        return names

    @staticmethod
    def _determine_severity(issues: list[str]) -> str:
        """Determine decision severity based on the incompatible features found.

        MEDIUM for feature-level incompatibilities (fax, storage, transfer).
        LOW for warning-only issues.
        """
        for issue in issues:
            prefix = issue.split(":")[0].strip() if ":" in issue else ""
            if prefix in _MEDIUM_KEYWORDS:
                return "MEDIUM"
        # All issues are warning-based
        return "LOW"
