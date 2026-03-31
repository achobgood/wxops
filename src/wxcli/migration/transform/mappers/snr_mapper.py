"""SNRMapper — CUCM Remote Destinations → Webex Single Number Reach.

Reads remote_destination objects from the store, groups by user,
resolves user ownership, normalizes phone numbers to E.164, and
produces CanonicalSingleNumberReach objects.

Timer controls (answerTooSoon, answerTooLate) have no Webex equivalent
and produce SNR_LOSSY decisions.

(from tier2-enterprise-expansion.md §4)
"""

from __future__ import annotations

import logging
import re
from typing import Any

from wxcli.migration.models import (
    CanonicalSingleNumberReach,
    DecisionType,
    MigrationStatus,
    MapperResult,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.base import (
    Mapper,
    accept_option,
    extract_provenance,
    manual_option,
    skip_option,
)

logger = logging.getLogger(__name__)

# CUCM default timer values (milliseconds) — non-default triggers SNR_LOSSY
CUCM_DEFAULT_ANSWER_TOO_SOON = 1500
CUCM_DEFAULT_ANSWER_TOO_LATE = 19000

# Basic E.164 check: starts with + and has 8-15 digits
_E164_RE = re.compile(r"^\+\d{8,15}$")


def _is_e164(number: str) -> bool:
    """Check if a number looks like E.164 format."""
    return bool(_E164_RE.match(number))


def _safe_int(val: Any, default: int | None = None) -> int | None:
    """Safely coerce a value to int."""
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


class SNRMapper(Mapper):
    """Map CUCM Remote Destinations to Webex Single Number Reach.

    Tier 2 expansion: produces CanonicalSingleNumberReach objects and
    SNR_LOSSY decisions for CUCM-only timer controls.
    """

    name = "snr_mapper"
    depends_on = ["user_mapper"]

    def map(self, store: MigrationStore) -> MapperResult:
        result = MapperResult()

        # Group remote destinations by owner user ID
        user_dests: dict[str, list[dict[str, Any]]] = {}
        rd_count = 0
        for rd in store.get_objects("remote_destination"):
            rd_count += 1
            state = rd.get("pre_migration_state") or {}
            owner = state.get("ownerUserId") or ""
            if not owner:
                continue
            user_dests.setdefault(owner, []).append(rd)

        logger.info(
            "SNR mapping: %d remote_destination objects, %d unique owners",
            rd_count, len(user_dests),
        )

        for owner_userid, rd_list in user_dests.items():
            user_cid = f"user:{owner_userid}"
            if not store.get_object(user_cid):
                continue

            # Build numbers list
            numbers = []
            lossy_timers = []
            invalid_numbers = []
            any_enabled = False

            for rd in rd_list:
                state = rd.get("pre_migration_state") or {}
                dest = state.get("destination") or ""
                name = state.get("name") or ""
                is_mobile = str(state.get("isMobilePhone") or "").lower() in ("true", "t", "1")
                mobile_connect = str(state.get("enableMobileConnect") or "").lower() in ("true", "t", "1")

                if mobile_connect:
                    any_enabled = True

                # Timer values
                too_soon = _safe_int(state.get("answerTooSoonTimer"), CUCM_DEFAULT_ANSWER_TOO_SOON)
                too_late = _safe_int(state.get("answerTooLateTimer"), CUCM_DEFAULT_ANSWER_TOO_LATE)

                # Check for non-default timers
                if too_soon != CUCM_DEFAULT_ANSWER_TOO_SOON or too_late != CUCM_DEFAULT_ANSWER_TOO_LATE:
                    lossy_timers.append({
                        "destination": dest,
                        "answer_too_soon": too_soon,
                        "answer_too_late": too_late,
                    })

                # Validate number format
                if dest and not _is_e164(dest):
                    if len(dest) >= 10 and dest.isdigit():
                        # Could be national format — flag for admin validation
                        invalid_numbers.append(dest)

                label = "Mobile" if is_mobile else name
                numbers.append({
                    "phone_number": dest,
                    "enabled": mobile_connect,
                    "name": label,
                    "answer_confirmation": False,
                    "cucm_answer_too_soon": too_soon,
                    "cucm_answer_too_late": too_late,
                })

            if not numbers:
                continue

            # Build canonical SNR object
            prov = extract_provenance(rd_list[0])
            snr = CanonicalSingleNumberReach(
                canonical_id=f"single_number_reach:{owner_userid}",
                provenance=prov,
                status=MigrationStatus.ANALYZED,
                user_canonical_id=user_cid,
                enabled=any_enabled,
                numbers=numbers,
            )
            store.upsert_object(snr)
            result.objects_created += 1

            # Write cross-ref
            store.add_cross_ref(user_cid, snr.canonical_id, "user_has_snr")

            # Decision: lossy timers
            if lossy_timers:
                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.SNR_LOSSY,
                    severity="LOW",
                    summary=(
                        f"User '{owner_userid}' has {len(lossy_timers)} Remote Destination(s) "
                        f"with custom timer values that Webex SNR does not support"
                    ),
                    context={
                        "user_id": user_cid,
                        "lossy_timers": lossy_timers,
                    },
                    options=[
                        accept_option("Accept loss — migrate numbers without timer control"),
                        skip_option("Skip SNR migration for this user"),
                        manual_option("Admin configures custom behavior in Webex"),
                    ],
                    affected_objects=[user_cid, snr.canonical_id],
                )
                result.decisions.append(decision)

            # Decision: invalid numbers
            if invalid_numbers:
                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.MISSING_DATA,
                    severity="MEDIUM",
                    summary=(
                        f"User '{owner_userid}' has {len(invalid_numbers)} Remote Destination(s) "
                        f"with non-E.164 numbers"
                    ),
                    context={
                        "user_id": user_cid,
                        "invalid_numbers": invalid_numbers,
                    },
                    options=[
                        manual_option("Admin provides valid E.164 numbers"),
                        skip_option("Skip these entries"),
                    ],
                    affected_objects=[user_cid, snr.canonical_id],
                )
                result.decisions.append(decision)

        return result
