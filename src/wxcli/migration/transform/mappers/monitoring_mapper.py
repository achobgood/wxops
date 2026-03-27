"""MonitoringMapper — CUCM BLF → Webex per-person monitoring list.

Reads phone objects from the store (which contain busyLampFields from getPhone),
resolves user ownership via device_owned_by_user cross-ref, resolves BLF
targets to user canonical IDs via line cross-refs, and produces
CanonicalMonitoringList objects.

Speed dials are NOT mapped — they stay in phone metadata for reporting.
Webex monitoring list max is 50 entries; overflow produces FEATURE_APPROXIMATION.
"""

from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.models import (
    CanonicalMonitoringList,
    DecisionType,
    MigrationStatus,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.models import MapperResult
from wxcli.migration.transform.mappers.base import (
    Mapper,
    accept_option,
    extract_provenance,
    skip_option,
)

logger = logging.getLogger(__name__)

WEBEX_MONITORING_MAX = 50


def _extract_blf_entries(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract BLF entries from phone pre_migration_state.

    Handles both raw AXL format (nested dict) and pre-normalized list.
    """
    blf = state.get("busyLampFields")
    if blf is None:
        return []
    if isinstance(blf, list):
        return blf
    if isinstance(blf, dict):
        entries = blf.get("busyLampField", [])
        if isinstance(entries, list):
            return entries
        if isinstance(entries, dict):
            return [entries]
    return []


def _extract_speed_dials(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract speed dial entries from phone pre_migration_state."""
    sd = state.get("speeddials")
    if sd is None:
        return []
    if isinstance(sd, list):
        return sd
    if isinstance(sd, dict):
        entries = sd.get("speeddial", [])
        if isinstance(entries, list):
            return entries
        if isinstance(entries, dict):
            return [entries]
    return []


class MonitoringMapper(Mapper):
    """Map CUCM BLF entries to Webex per-person monitoring lists.

    Tier 2 expansion: produces CanonicalMonitoringList objects and
    FEATURE_APPROXIMATION decisions for overflow (>50 entries).
    """

    name = "monitoring_mapper"
    depends_on = ["user_mapper", "line_mapper"]

    def map(self, store: MigrationStore) -> MapperResult:
        result = MapperResult()

        for phone_data in store.get_objects("phone"):
            phone_id = phone_data["canonical_id"]
            state = phone_data.get("pre_migration_state") or {}

            blf_entries = _extract_blf_entries(state)
            if not blf_entries:
                continue

            # Resolve owner user
            user_refs = store.find_cross_refs(phone_id, "device_owned_by_user")
            if not user_refs:
                continue
            user_id = user_refs[0]
            user_name = user_id.split(":", 1)[-1]

            # Skip if already created for this user (multi-device)
            existing = store.get_object(f"monitoring_list:{user_name}")
            if existing:
                continue

            # Resolve BLF targets
            monitored_members = []
            for entry in blf_entries:
                if not isinstance(entry, dict):
                    continue
                blf_dest = entry.get("blfDest") or entry.get("blfDirn") or ""
                label = entry.get("label") or blf_dest

                # Try to resolve BLF destination to a user
                target_id = self._resolve_blf_target(store, blf_dest)
                if target_id:
                    monitored_members.append({
                        "target_canonical_id": target_id,
                        "display_label": label,
                    })
                else:
                    # Still add with unresolved marker
                    monitored_members.append({
                        "target_canonical_id": None,
                        "display_label": label,
                        "unresolved_dn": blf_dest,
                    })

            # Check overflow
            truncated = False
            total_count = len(monitored_members)
            if total_count > WEBEX_MONITORING_MAX:
                truncated = True
                monitored_members = monitored_members[:WEBEX_MONITORING_MAX]

            # Build canonical monitoring list
            prov = extract_provenance(phone_data)
            ml = CanonicalMonitoringList(
                canonical_id=f"monitoring_list:{user_name}",
                provenance=prov,
                status=MigrationStatus.ANALYZED,
                user_canonical_id=user_id,
                monitored_members=monitored_members,
            )
            store.upsert_object(ml)
            result.objects_created += 1

            # Write cross-refs
            store.add_cross_ref(user_id, ml.canonical_id, "user_has_monitoring_list")
            for member in monitored_members:
                target = member.get("target_canonical_id")
                if target:
                    store.add_cross_ref(ml.canonical_id, target, "monitoring_watches")

            # Decision: unresolved BLF targets
            unresolved = [m for m in monitored_members if m.get("target_canonical_id") is None]
            if unresolved:
                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.MISSING_DATA,
                    severity="LOW",
                    summary=(
                        f"User '{user_name}' has {len(unresolved)} BLF "
                        f"target(s) that cannot be resolved to a Webex user"
                    ),
                    context={
                        "user_id": user_id,
                        "unresolved_dns": [m.get("unresolved_dn", "") for m in unresolved],
                        "total_blf_entries": total_count,
                    },
                    options=[
                        accept_option("Skip unresolved entries — exclude from monitoring list"),
                        skip_option("Skip entire monitoring list migration for this user"),
                    ],
                    affected_objects=[user_id, ml.canonical_id],
                )
                result.decisions.append(decision)

            # Decision: overflow
            if truncated:
                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.FEATURE_APPROXIMATION,
                    severity="MEDIUM",
                    summary=(
                        f"User '{user_name}' has {total_count} BLF entries, "
                        f"exceeding Webex monitoring list max of {WEBEX_MONITORING_MAX}"
                    ),
                    context={
                        "user_id": user_id,
                        "total_blf_entries": total_count,
                        "max_allowed": WEBEX_MONITORING_MAX,
                        "truncated_count": total_count - WEBEX_MONITORING_MAX,
                    },
                    options=[
                        accept_option(f"Truncate to first {WEBEX_MONITORING_MAX} entries"),
                        skip_option("Skip monitoring list migration for this user"),
                    ],
                    affected_objects=[user_id, ml.canonical_id],
                )
                result.decisions.append(decision)

        return result

    def _resolve_blf_target(self, store: MigrationStore, dn: str) -> str | None:
        """Try to resolve a BLF DN to a user canonical_id via line cross-refs."""
        if not dn:
            return None
        # Look for a line object matching this DN
        for line_data in store.get_objects("line"):
            line_state = line_data.get("pre_migration_state") or {}
            line_ext = (
                line_data.get("extension")
                or line_state.get("extension")
                or line_state.get("pattern")
            )
            if line_ext == dn:
                # Found the line — now find its owner via cross-ref
                line_id = line_data["canonical_id"]
                user_refs = store.find_cross_refs(line_id, "line_assigned_to_user")
                if user_refs:
                    return user_refs[0]
        return None
