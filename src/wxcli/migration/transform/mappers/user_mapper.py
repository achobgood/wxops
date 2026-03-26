"""User mapper: CUCM End Users -> Webex Calling People.

Maps CUCM end users to CanonicalUser objects with resolved email, location,
and primary extension. Email resolution uses mailid with userid as fallback.
Location resolution follows the cross-ref chain:
    user -> user_has_device -> device -> device_in_pool -> device_pool
    -> device_pool_to_location -> location

(from 03b-transform-mappers.md §2, user_mapper)

Cross-ref reads:
    user_has_device        (User -> Device)
    user_has_primary_dn    (User -> DN)
    device_in_pool         (Device -> DevicePool)
    device_pool_to_location (DevicePool -> Location)

Does NOT produce: DUPLICATE_USER, EXTENSION_CONFLICT (analyzer-owned)
"""

from __future__ import annotations

import logging
import re
from typing import Any

from wxcli.migration.models import (
    CanonicalUser,
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

# Simple email validation pattern
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UserMapper(Mapper):
    """Maps CUCM End Users to Webex Calling People.

    (from 03b-transform-mappers.md §2)
    """

    name = "user_mapper"
    depends_on = ["location_mapper"]

    def __init__(
        self,
        create_method: str = "people_api",
        include_phoneless_users: bool = False,
    ) -> None:
        """
        Args:
            create_method: "scim" or "people_api" — execution strategy
                (from 03b-transform-mappers.md §2: execution strategy note)
            include_phoneless_users: If True, map users without phones.
                (from 03b-transform-mappers.md §2: edge case — users with no phone)
        """
        self.create_method = create_method
        self.include_phoneless_users = include_phoneless_users

    def map(self, store: MigrationStore) -> MapperResult:
        """Read normalized CUCM users and produce CanonicalUser objects."""
        result = MapperResult()

        for user_data in store.get_objects("user"):
            user_id = user_data["canonical_id"]
            state = user_data.get("pre_migration_state") or {}

            # --- Email resolution ---
            # (from 03b-transform-mappers.md §2: mailid primary, userid fallback)
            emails = user_data.get("emails", [])
            cucm_mailid = user_data.get("cucm_mailid")
            cucm_userid = user_data.get("cucm_userid", "")

            if not emails:
                if cucm_mailid and _EMAIL_RE.match(cucm_mailid):
                    emails = [cucm_mailid.lower()]
                elif cucm_userid and _EMAIL_RE.match(cucm_userid):
                    emails = [cucm_userid.lower()]

            if not emails:
                # No email available
                # (from 03b-transform-mappers.md §2: MISSING_DATA if no mailid and userid not email)
                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.MISSING_DATA,
                    severity="HIGH",
                    summary=f"User '{cucm_userid}' has no email address (mailid empty, userid not email format)",
                    context={
                        "user_id": user_id,
                        "cucm_userid": cucm_userid,
                        "cucm_mailid": cucm_mailid,
                    },
                    options=[
                        manual_option("Admin provides email address"),
                        skip_option("User not migrated to Webex Calling"),
                    ],
                    affected_objects=[user_id],
                )
                store.save_decision(decision_to_store_dict(decision))
                result.decisions.append(decision)
                continue

            # --- Device and location resolution ---
            # Chain: user -> user_has_device -> device -> device_in_pool -> pool -> device_pool_to_location -> location
            device_refs = store.find_cross_refs(user_id, "user_has_device")
            location_id = None

            if device_refs:
                # Try each device until we find one with a location chain
                for dev_id in device_refs:
                    loc_id = store.resolve_chain(
                        dev_id, "device_in_pool", "device_pool_to_location"
                    )
                    if loc_id:
                        location_id = loc_id
                        break

            if not location_id and not self.include_phoneless_users:
                # No device -> no location
                # (from 03b-transform-mappers.md §2: MISSING_DATA if no device/location)
                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.MISSING_DATA,
                    severity="MEDIUM",
                    summary=f"User '{cucm_userid}' has no associated phone — cannot resolve Webex location",
                    context={
                        "user_id": user_id,
                        "cucm_userid": cucm_userid,
                        "reason": "no_device_no_location",
                    },
                    options=[
                        manual_option("Admin assigns user to a location manually"),
                        skip_option("User not migrated to Webex Calling"),
                    ],
                    affected_objects=[user_id],
                )
                store.save_decision(decision_to_store_dict(decision))
                result.decisions.append(decision)
                continue

            # --- Extension resolution ---
            # (from 03b-transform-mappers.md §2: primary DN, bare extension without routing prefix)
            extension = user_data.get("extension")
            primary_dn_refs = store.find_cross_refs(user_id, "user_has_primary_dn")
            if primary_dn_refs:
                dn_id = primary_dn_refs[0]
                # DN IDs are formatted as "dn:pattern:partition"
                parts = dn_id.split(":", 2)
                if len(parts) >= 2:
                    extension = parts[1]

            # --- Build display name ---
            first_name = user_data.get("first_name")
            last_name = user_data.get("last_name")
            display_name = user_data.get("display_name")
            if not display_name:
                name_parts = [p for p in [first_name, last_name] if p]
                display_name = " ".join(name_parts) or None

            # --- SQL-extracted user detection ---
            # Users extracted via SQL fallback have limited fields.
            # (from Phase 04 corrections: pre_migration_state.extracted_via_sql = true)
            sql_extracted = state.get("extracted_via_sql", False)
            if sql_extracted:
                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.MISSING_DATA,
                    severity="LOW",
                    summary=f"User '{cucm_userid}' was extracted via SQL fallback — limited field data available",
                    context={
                        "user_id": user_id,
                        "cucm_userid": cucm_userid,
                        "reason": "sql_extracted",
                        "missing_fields": ["cucm_css", "cucm_voicemail_profile", "selfService", "userLocale"],
                    },
                    options=[
                        manual_option("Admin verifies and supplements user data"),
                        accept_option("Proceed with limited data — CSS and voicemail settings will not be migrated"),
                    ],
                    affected_objects=[user_id],
                )
                store.save_decision(decision_to_store_dict(decision))
                result.decisions.append(decision)

            # --- Build CanonicalUser ---
            user_obj = CanonicalUser(
                canonical_id=user_id,
                provenance=extract_provenance(user_data),
                status=MigrationStatus.ANALYZED,
                emails=emails,
                first_name=first_name,
                last_name=last_name,
                display_name=display_name,
                location_id=location_id,
                extension=extension,
                department=user_data.get("department"),
                title=user_data.get("title"),
                create_method=self.create_method,
                calling_data=True,
                cucm_manager_user_id=user_data.get("cucm_manager_user_id"),
                cucm_userid=cucm_userid,
                cucm_mailid=cucm_mailid,
            )

            store.upsert_object(user_obj)
            result.objects_updated += 1

            # Fix 8: Write user_in_location cross-ref for dependency graph
            if location_id:
                store.add_cross_ref(user_id, location_id, "user_in_location")

        return result


