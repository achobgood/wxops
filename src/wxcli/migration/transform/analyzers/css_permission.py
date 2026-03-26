"""CSS permission analyzer — finds unclassifiable calling permission patterns.

The css_mapper produces CanonicalCallingPermission objects and
CALLING_PERMISSION_MISMATCH decisions when block patterns can't be cleanly
classified into Webex call types (INTERNAL, NATIONAL, INTERNATIONAL, etc.).
This analyzer performs a cross-object sweep to find calling_permission objects
with incomplete or contradictory entries that the mapper didn't flag.

Decision ownership: MAPPER-OWNED (css_mapper produces CALLING_PERMISSION_MISMATCH).
This analyzer checks for existing mapper decisions before creating new ones.

(from 03-conflict-detection-engine.md, CSS permission conflict detection)
(from 03b-transform-mappers.md, css_mapper calling permissions)
(from 07-idempotency-resumability.md, fingerprint-based identity)
"""

from __future__ import annotations

from typing import Any

from wxcli.migration.models import DecisionOption, DecisionType
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.analyzers import Analyzer, Decision


class CSSPermissionAnalyzer(Analyzer):
    """Finds calling_permission objects with incomplete or contradictory entries.

    The css_mapper creates CanonicalCallingPermission objects with a
    calling_permissions list of CallingPermissionEntry dicts (call_type,
    action, transfer_enabled).  This analyzer detects:

    - Empty calling_permissions list (no permissions mapped)
    - Permissions that block INTERNAL_CALL (unusual, likely misconfigured)
    - Permission objects that exist but have no assigned users

    The css_mapper may already have produced CALLING_PERMISSION_MISMATCH
    decisions.  This analyzer only creates decisions for issues the mapper
    missed.
    """

    name = "css_permission"
    decision_types = [DecisionType.CALLING_PERMISSION_MISMATCH]

    def analyze(self, store: MigrationStore) -> list[Decision]:
        """Sweep all calling_permission objects, flag incomplete or contradictory entries."""
        decisions: list[Decision] = []

        # Step 1: Get existing mapper-produced CALLING_PERMISSION_MISMATCH decisions
        existing = self._get_existing_decisions_for_type(
            store, DecisionType.CALLING_PERMISSION_MISMATCH
        )

        # Step 2: Load all calling_permission objects
        permissions = store.get_objects("calling_permission")
        if not permissions:
            return decisions

        # Step 3: Load user_has_calling_permission cross-refs to find assigned users
        perm_rows = store.conn.execute(
            "SELECT from_id, to_id FROM cross_refs "
            "WHERE relationship = 'user_has_calling_permission'"
        ).fetchall()

        perm_to_users: dict[str, list[str]] = {}
        for row in perm_rows:
            perm_id = row["to_id"]
            if perm_id not in perm_to_users:
                perm_to_users[perm_id] = []
            perm_to_users[perm_id].append(row["from_id"])

        # Step 4: Analyze each calling_permission object for issues
        for perm in permissions:
            canonical_id = perm.get("canonical_id", "")
            if not canonical_id:
                continue

            # Skip if mapper already produced a decision for this object
            if canonical_id in existing:
                continue

            calling_perms = perm.get("calling_permissions", [])
            assigned_users = perm_to_users.get(canonical_id, [])
            issues: list[str] = []

            # Issue 1: Empty calling_permissions list
            if not calling_perms:
                issues.append(
                    "No calling permissions mapped — all call types will use defaults"
                )

            # Issue 2: INTERNAL_CALL is blocked
            for entry in calling_perms:
                call_type = entry.get("call_type", "")
                action = entry.get("action", "")
                if call_type == "INTERNAL_CALL" and action.upper() == "BLOCK":
                    issues.append(
                        "INTERNAL_CALL is blocked — users cannot make internal calls, "
                        "likely a misconfiguration"
                    )
                    break

            # Note: orphaned permission objects (0 users assigned) are silently
            # dropped by the CSS mapper and never reach the analyzer.

            if not issues:
                continue

            # Determine severity
            has_internal_block = any(
                "INTERNAL_CALL is blocked" in issue for issue in issues
            )
            severity = "HIGH" if has_internal_block else "MEDIUM"

            # Build calling_permissions summary for context
            perms_summary = []
            for entry in calling_perms:
                perms_summary.append({
                    "call_type": entry.get("call_type", ""),
                    "action": entry.get("action", ""),
                    "transfer_enabled": entry.get("transfer_enabled", False),
                })

            context = {
                "permission_canonical_id": canonical_id,
                "issues": sorted(issues),
                "calling_permissions": perms_summary,
                "assigned_users_count": len(assigned_users),
            }

            perm_name = perm.get("name", canonical_id)

            options = [
                DecisionOption(
                    id="accept",
                    label="Accept Current Mapping",
                    impact=(
                        f"Keep calling permissions for '{perm_name}' as mapped — "
                        f"{len(calling_perms)} entries, {len(assigned_users)} users"
                    ),
                ),
                DecisionOption(
                    id="manual",
                    label="Manual Configuration",
                    impact=(
                        f"Manually configure calling permissions for '{perm_name}' "
                        f"in Webex Calling"
                    ),
                ),
                DecisionOption(
                    id="skip",
                    label="Skip",
                    impact=(
                        f"Leave calling permissions for '{perm_name}' unresolved — "
                        f"manual intervention required"
                    ),
                ),
            ]

            issue_summary = "; ".join(issues)
            decision = self._create_decision(
                store=store,
                decision_type=DecisionType.CALLING_PERMISSION_MISMATCH,
                severity=severity,
                summary=(
                    f"Calling permission '{perm_name}' has issues: {issue_summary}"
                ),
                context=context,
                options=options,
                affected_objects=[canonical_id],
            )
            decisions.append(decision)

        return decisions

    def fingerprint(self, decision_type: DecisionType, context: dict[str, Any]) -> str:
        """Deterministic fingerprint from canonical_id and sorted issues.

        Includes:
        - permission_canonical_id (the object with the problem)
        - sorted list of issues (the triggering conditions)

        (from 07-idempotency-resumability.md lines 30-43)
        """
        return self._hash_fingerprint({
            "type": decision_type.value,
            "permission_canonical_id": context.get("permission_canonical_id"),
            "issues": sorted(context.get("issues", [])),
        })
