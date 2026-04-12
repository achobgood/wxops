"""Voicemail group mapper: Unity Connection shared mailboxes -> Webex Voicemail Groups.

Reads normalized `voicemail_group` objects (produced by normalize_voicemail_group
from Unity Connection CUPI data) and produces CanonicalVoicemailGroup objects
ready for execution via handle_voicemail_group_create.

(from docs/superpowers/specs/2026-04-10-voicemail-groups.md)

Decisions generated:
    MISSING_DATA         — UC passcodes are never extractable; a default
                            placeholder is assigned and the admin must rotate
                            post-migration.
    AUDIO_ASSET_MANUAL   — custom greetings can't be extracted from UC.
    EXTENSION_CONFLICT   — voicemail group extension clashes with a user's
                            extension in the same location.
    LOCATION_AMBIGUOUS   — no location could be resolved for the mailbox.
"""

from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.models import (
    CanonicalVoicemailGroup,
    DecisionType,
    MapperResult,
    MigrationStatus,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.base import (
    Mapper,
    accept_option,
    decision_to_store_dict,
    extract_provenance,
    manual_option,
    skip_option,
)

logger = logging.getLogger(__name__)

# Default placeholder passcode — admins must rotate post-migration.
# (CUCM Unity Connection PINs are one-way hashed and not retrievable.)
_DEFAULT_PASSCODE = "0000"


class VoicemailGroupMapper(Mapper):
    """Map Unity Connection shared mailboxes to Webex Voicemail Groups.

    Runs after FeatureMapper (so hunt groups / call queues are in the store)
    and depends on LocationMapper so canonical locations exist.
    """

    name = "voicemail_group_mapper"
    depends_on = ["location_mapper", "feature_mapper"]

    def map(self, store: MigrationStore) -> MapperResult:
        result = MapperResult()

        # Precompute lookups used during resolution.
        locations = list(store.get_objects("location"))
        location_ids = [loc["canonical_id"] for loc in locations]
        users_by_extension = self._index_users_by_extension(store)

        for raw in store.get_objects("voicemail_group"):
            raw_id = raw["canonical_id"]
            state = raw.get("pre_migration_state") or {}
            # Skip if we've already replaced it with a CanonicalVoicemailGroup
            # (protects against idempotent re-runs).
            if raw.get("name") and raw.get("passcode"):
                continue

            name = state.get("name") or raw_id.split(":", 1)[-1]
            extension = state.get("extension")

            location_id, location_decision = self._resolve_location(
                store, extension, users_by_extension, location_ids, raw_id, name
            )
            if location_decision is not None:
                store.save_decision(decision_to_store_dict(location_decision))
                result.decisions.append(location_decision)

            # Build notifications block
            notification_dest = state.get("notification_destination")
            notifications: dict[str, Any] = {"enabled": bool(notification_dest)}
            if notification_dest:
                notifications["destination"] = notification_dest

            vg = CanonicalVoicemailGroup(
                canonical_id=raw_id,  # Same ID — we're enriching in place.
                provenance=extract_provenance(raw),
                status=MigrationStatus.ANALYZED,
                name=name,
                extension=extension,
                location_id=location_id,
                language_code=state.get("language_code") or "en_us",
                enabled=True,
                passcode=_DEFAULT_PASSCODE,
                greeting_type=state.get("greeting_type", "DEFAULT"),
                notifications=notifications,
                cucm_object_id=state.get("cucm_object_id"),
                cucm_display_name=name,
            )
            store.upsert_object(vg)
            result.objects_created += 1

            # --- Decision: passcode placeholder (always) ---
            passcode_decision = self._create_decision(
                store=store,
                decision_type=DecisionType.MISSING_DATA,
                severity="LOW",
                summary=(
                    f"Voicemail group '{name}' will be created with a "
                    f"placeholder passcode (CUCM PINs cannot be extracted) — "
                    f"admin must set the final passcode after migration"
                ),
                context={
                    "voicemail_group_id": raw_id,
                    "reason": "voicemail_group_passcode",
                    "placeholder_passcode": _DEFAULT_PASSCODE,
                },
                options=[
                    accept_option(
                        f"Create with passcode {_DEFAULT_PASSCODE}; rotate manually"
                    ),
                    manual_option(
                        "Admin assigns a passcode in Control Hub post-migration"
                    ),
                ],
                affected_objects=[raw_id],
            )
            store.save_decision(decision_to_store_dict(passcode_decision))
            result.decisions.append(passcode_decision)

            # --- Decision: custom greeting (if present) ---
            if state.get("greeting_type") == "CUSTOM":
                greeting_decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.AUDIO_ASSET_MANUAL,
                    severity="MEDIUM",
                    summary=(
                        f"Voicemail group '{name}' has a custom Unity Connection "
                        f"greeting — audio cannot be migrated programmatically"
                    ),
                    context={
                        "voicemail_group_id": raw_id,
                        "asset_type": "voicemail_group_greeting",
                        "reason": "custom_greeting_not_extractable",
                    },
                    options=[
                        accept_option(
                            "Use DEFAULT greeting at creation; upload manually"
                        ),
                        manual_option(
                            "Upload custom greeting WAV post-migration via Control Hub"
                        ),
                    ],
                    affected_objects=[raw_id],
                )
                store.save_decision(decision_to_store_dict(greeting_decision))
                result.decisions.append(greeting_decision)

            # --- Decision: extension conflict (if user has same extension) ---
            if extension and location_id:
                conflicting_user = self._find_conflicting_user(
                    users_by_extension, extension, location_id
                )
                if conflicting_user is not None:
                    conflict_decision = self._create_decision(
                        store=store,
                        decision_type=DecisionType.EXTENSION_CONFLICT,
                        severity="HIGH",
                        summary=(
                            f"Voicemail group '{name}' extension {extension} "
                            f"conflicts with user {conflicting_user} in "
                            f"{location_id}"
                        ),
                        context={
                            "voicemail_group_id": raw_id,
                            "extension": extension,
                            "conflicting_user_id": conflicting_user,
                            "location_id": location_id,
                            "reason": "voicemail_group_extension_taken",
                        },
                        options=[
                            manual_option(
                                "Assign a new extension to the voicemail group"
                            ),
                            skip_option("Voicemail group not migrated"),
                        ],
                        affected_objects=[raw_id, conflicting_user],
                    )
                    store.save_decision(decision_to_store_dict(conflict_decision))
                    result.decisions.append(conflict_decision)

        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _index_users_by_extension(
        self, store: MigrationStore
    ) -> dict[str, list[tuple[str, str | None]]]:
        """Return {extension: [(user_canonical_id, location_id), ...]}."""
        idx: dict[str, list[tuple[str, str | None]]] = {}
        for u in store.get_objects("user"):
            ext = u.get("extension")
            if not ext:
                continue
            idx.setdefault(str(ext), []).append(
                (u["canonical_id"], u.get("location_id"))
            )
        return idx

    def _resolve_location(
        self,
        store: MigrationStore,
        extension: str | None,
        users_by_extension: dict[str, list[tuple[str, str | None]]],
        location_ids: list[str],
        raw_id: str,
        name: str,
    ) -> tuple[str | None, Any | None]:
        """Resolve a location for a voicemail group.

        Returns (location_id, decision). decision is None when a location
        was found; otherwise it's a LOCATION_AMBIGUOUS decision.
        """
        # Tier 1: user with matching extension
        if extension and extension in users_by_extension:
            for _user_cid, loc_id in users_by_extension[extension]:
                if loc_id:
                    return loc_id, None

        # Tier 2: single-location deployment
        if len(location_ids) == 1:
            return location_ids[0], None

        # Tier 3: ambiguous — emit decision, leave location_id unset
        decision = self._create_decision(
            store=store,
            decision_type=DecisionType.LOCATION_AMBIGUOUS,
            severity="MEDIUM",
            summary=(
                f"Voicemail group '{name}' has no resolvable location "
                f"(no user with extension {extension}; {len(location_ids)} "
                f"candidate locations)"
            ),
            context={
                "voicemail_group_id": raw_id,
                "extension": extension,
                "candidate_locations": location_ids,
                "reason": "voicemail_group_location_unknown",
            },
            options=[
                *[
                    accept_option(f"Create in {lid}") for lid in location_ids
                ],
                skip_option("Voicemail group not migrated"),
            ],
            affected_objects=[raw_id],
        )
        return None, decision

    def _find_conflicting_user(
        self,
        users_by_extension: dict[str, list[tuple[str, str | None]]],
        extension: str,
        location_id: str,
    ) -> str | None:
        for user_cid, user_loc in users_by_extension.get(extension, []):
            if user_loc == location_id:
                return user_cid
        return None
