"""Duplicate user analyzer — finds users with matching email or name across CUCM inventory.

Detects users that would collide in Webex because they share the same email
address, or users without emails who share the same (first_name, last_name)
pair.  Duplicate users block migration because Webex requires unique email
identities.

Decision ownership: ANALYZER-OWNED (no mapper produces DUPLICATE_USER).

(from 03-conflict-detection-engine.md, duplicate user detection)
(from 07-idempotency-resumability.md, fingerprint-based identity)
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from wxcli.migration.models import DecisionOption, DecisionType
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.analyzers import Analyzer, Decision


class DuplicateUserAnalyzer(Analyzer):
    """Finds users with matching email or name across CUCM inventory.

    Webex requires each person to have a unique email address.  This analyzer
    detects two collision patterns:

    1. **Email collisions**: 2+ users share the same email (case-insensitive).
    2. **Name collisions (no email)**: 2+ users with empty emails share the
       same (first_name, last_name) pair — likely the same person entered
       multiple times in CUCM.

    Both patterns produce DUPLICATE_USER decisions with HIGH severity since
    they block migration.
    """

    name = "duplicate_user"
    decision_types = [DecisionType.DUPLICATE_USER]

    def analyze(self, store: MigrationStore) -> list[Decision]:
        """Sweep all users, group by email and name, flag duplicates."""
        decisions: list[Decision] = []

        users = store.get_objects("user")
        if not users:
            return decisions

        # Step 1: Group users by lowercase email
        email_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        # Track users with no email for name-based duplicate check
        no_email_users: list[dict[str, Any]] = []

        for user in users:
            emails = user.get("emails", [])
            if emails:
                for email in emails:
                    email_lower = email.strip().lower()
                    if email_lower:
                        email_groups[email_lower].append(user)
            else:
                no_email_users.append(user)

        # Step 2: Produce decisions for email-based duplicates (2+ users per email)
        seen_ids: set[str] = set()  # track which users already have a decision

        for email, group_users in sorted(email_groups.items()):
            if len(group_users) < 2:
                continue

            # Deduplicate by canonical_id within the group (a user with multiple
            # emails could appear twice in the same group)
            unique_users: dict[str, dict[str, Any]] = {}
            for u in group_users:
                cid = u.get("canonical_id", "")
                if cid:
                    unique_users[cid] = u

            if len(unique_users) < 2:
                continue

            user_ids = sorted(unique_users.keys())
            user_names = [
                unique_users[uid].get("display_name")
                or f"{unique_users[uid].get('first_name', '')} {unique_users[uid].get('last_name', '')}".strip()
                or uid
                for uid in user_ids
            ]

            context = {
                "email": email,
                "user_ids": user_ids,
                "user_names": user_names,
            }

            options = [
                DecisionOption(
                    id="merge",
                    label="Merge",
                    impact=f"Merge {len(user_ids)} users into single Webex person",
                ),
                DecisionOption(
                    id="keep_primary",
                    label="Keep Primary",
                    impact=f"Keep first user, skip {len(user_ids) - 1} others",
                ),
                DecisionOption(
                    id="skip_all",
                    label="Skip All",
                    impact=f"Skip all {len(user_ids)} duplicate users",
                ),
                DecisionOption(
                    id="manual",
                    label="Manual Resolution",
                    impact="Flag for manual review and resolution",
                ),
            ]

            decision = self._create_decision(
                store=store,
                decision_type=DecisionType.DUPLICATE_USER,
                severity="HIGH",
                summary=f"Email {email} shared by {len(user_ids)} users",
                context=context,
                options=options,
                affected_objects=user_ids,
            )
            decisions.append(decision)
            seen_ids.update(user_ids)

        # Step 3: Check no-email users for (first_name, last_name) collisions
        name_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

        for user in no_email_users:
            cid = user.get("canonical_id", "")
            if cid in seen_ids:
                continue  # already covered by an email-based decision

            first = (user.get("first_name") or "").strip().lower()
            last = (user.get("last_name") or "").strip().lower()
            if first or last:
                name_groups[(first, last)].append(user)

        for (first, last), group_users in sorted(name_groups.items()):
            if len(group_users) < 2:
                continue

            user_ids = sorted(u.get("canonical_id", "") for u in group_users if u.get("canonical_id"))
            if len(user_ids) < 2:
                continue

            display_name = f"{first} {last}".strip()
            user_names = [
                u.get("display_name") or display_name or u.get("canonical_id", "")
                for u in group_users
                if u.get("canonical_id")
            ]

            # Use a synthetic email key for context — no real email exists
            name_key = f"<no-email>:{first}:{last}"

            context = {
                "email": name_key,
                "user_ids": user_ids,
                "user_names": sorted(user_names),
            }

            options = [
                DecisionOption(
                    id="merge",
                    label="Merge",
                    impact=f"Merge {len(user_ids)} users into single Webex person",
                ),
                DecisionOption(
                    id="keep_primary",
                    label="Keep Primary",
                    impact=f"Keep first user, skip {len(user_ids) - 1} others",
                ),
                DecisionOption(
                    id="skip_all",
                    label="Skip All",
                    impact=f"Skip all {len(user_ids)} duplicate users",
                ),
                DecisionOption(
                    id="manual",
                    label="Manual Resolution",
                    impact="Flag for manual review and resolution",
                ),
            ]

            decision = self._create_decision(
                store=store,
                decision_type=DecisionType.DUPLICATE_USER,
                severity="HIGH",
                summary=(
                    f"Name '{display_name}' shared by {len(user_ids)} users "
                    f"(no email set)"
                ),
                context=context,
                options=options,
                affected_objects=user_ids,
            )
            decisions.append(decision)

        return decisions

    def fingerprint(self, decision_type: DecisionType, context: dict[str, Any]) -> str:
        """Deterministic fingerprint from shared email and affected user IDs.

        Includes:
        - email (the shared email, or synthetic name key for no-email dupes)
        - sorted user canonical_ids (all users in the duplicate group)

        (from 07-idempotency-resumability.md lines 30-43)
        """
        return self._hash_fingerprint({
            "type": decision_type.value,
            "email": context.get("email"),
            "user_ids": sorted(context.get("user_ids", [])),
        })
