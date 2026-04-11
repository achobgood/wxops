"""ReceptionistMapper — detect CUCM receptionist users from phone layout signals.

Scores each phone owner for receptionist likelihood using 4 signals:
  1. BLF count (10+ = 2pts, 20+ = 3pts)
  2. KEM presence (2pts)
  3. Template name keywords (2pts)
  4. Main number assignment (1pt)

Users scoring >= 3 produce a CanonicalReceptionistConfig object. The mapper
reads the existing MonitoringMapper output to populate monitored_members and
DeviceLayoutMapper output to detect KEM presence.
"""

from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.models import (
    CanonicalReceptionistConfig,
    MapperResult,
    MigrationStatus,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.base import (
    Mapper,
    extract_provenance,
)

logger = logging.getLogger(__name__)

RECEPTIONIST_THRESHOLD = 3

_TEMPLATE_KEYWORDS = ("attendant", "reception", "lobby", "operator", "front desk")


def _extract_blf_entries(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract BLF entries from phone pre_migration_state."""
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


class ReceptionistMapper(Mapper):
    """Detect CUCM receptionist users and produce CanonicalReceptionistConfig."""

    name = "receptionist_mapper"
    depends_on = [
        "monitoring_mapper",
        "device_layout_mapper",
        "location_mapper",
        "line_mapper",
        "user_mapper",
    ]

    def map(self, store: MigrationStore) -> MapperResult:
        result = MapperResult()
        seen_users: set[str] = set()

        for phone_data in store.get_objects("phone"):
            phone_id = phone_data["canonical_id"]
            state = phone_data.get("pre_migration_state") or {}

            # Resolve owner
            user_refs = store.find_cross_refs(phone_id, "device_owned_by_user")
            if not user_refs:
                continue
            user_id = user_refs[0]
            user_name = user_id.split(":", 1)[-1]

            # Skip duplicate (multi-device)
            if user_name in seen_users:
                continue
            seen_users.add(user_name)

            # Score receptionist likelihood
            score, reasons = self._score(store, user_id, phone_id, state)
            if score < RECEPTIONIST_THRESHOLD:
                continue

            blf_entries = _extract_blf_entries(state)
            blf_count = len(blf_entries)

            # Get KEM info from device layout
            phone_name = phone_id.split(":", 1)[-1]
            layout = store.get_object(f"device_layout:{phone_name}")
            layout_data = layout or {}
            kem_keys = (
                layout_data.get("resolved_kem_keys")
                or (layout_data.get("pre_migration_state") or {}).get("resolved_kem_keys")
                or []
            )

            # Get monitored members from existing monitoring list
            monitored_members = self._get_monitored_members(store, user_name)

            # Check main number
            is_main = self._is_main_number_holder(store, user_id)

            # Get location
            user_obj = store.get_object(user_id)
            user_data = user_obj or {}
            location_cid = (
                user_data.get("location_id")
                or (user_data.get("pre_migration_state") or {}).get("location_id")
                or ""
            )

            template_name = state.get("phoneTemplateName") or ""

            prov = extract_provenance(phone_data)
            config = CanonicalReceptionistConfig(
                canonical_id=f"receptionist_config:{user_name}",
                provenance=prov,
                status=MigrationStatus.ANALYZED,
                user_canonical_id=user_id,
                location_canonical_id=location_cid,
                blf_count=blf_count,
                has_kem=bool(kem_keys),
                kem_key_count=len(kem_keys),
                template_name=template_name,
                detection_score=score,
                detection_reasons=reasons,
                monitored_members=monitored_members,
                is_main_number_holder=is_main,
            )
            store.upsert_object(config)
            result.objects_created += 1

            # Cross-refs
            store.add_cross_ref(user_id, config.canonical_id, "user_has_receptionist_config")

        return result

    def _score(
        self,
        store: MigrationStore,
        user_id: str,
        phone_id: str,
        state: dict[str, Any],
    ) -> tuple[int, list[str]]:
        """Score a phone owner for receptionist likelihood."""
        score = 0
        reasons: list[str] = []

        # Signal 1: BLF count
        blf_entries = _extract_blf_entries(state)
        blf_count = len(blf_entries)
        if blf_count >= 20:
            score += 3
            reasons.append(f"{blf_count} BLF entries (20+)")
        elif blf_count >= 10:
            score += 2
            reasons.append(f"{blf_count} BLF entries (10+)")

        # Signal 2: KEM presence (via device layout)
        phone_name = phone_id.split(":", 1)[-1]
        layout = store.get_object(f"device_layout:{phone_name}")
        if layout:
            kem_keys = (
                layout.get("resolved_kem_keys")
                or (layout.get("pre_migration_state") or {}).get("resolved_kem_keys")
                or []
            )
            if kem_keys:
                score += 2
                reasons.append(f"KEM with {len(kem_keys)} keys")

        # Signal 3: Template name keywords
        # AXL returns reference fields as dicts with _value_1 + uuid keys
        raw_template = state.get("phoneTemplateName")
        if isinstance(raw_template, dict):
            raw_template = raw_template.get("_value_1", "")
        template_name = (raw_template or "").lower()
        for keyword in _TEMPLATE_KEYWORDS:
            if keyword in template_name:
                score += 2
                reasons.append(f"Template name contains '{keyword}'")
                break

        # Signal 4: Main number assignment
        if self._is_main_number_holder(store, user_id):
            score += 1
            reasons.append("Holds location main number")

        return score, reasons

    def _is_main_number_holder(self, store: MigrationStore, user_id: str) -> bool:
        """Check if the user holds a line matching their location's main number."""
        loc_refs = store.find_cross_refs(user_id, "user_in_location")
        if not loc_refs:
            return False
        loc_id = loc_refs[0]
        loc_obj = store.get_object(loc_id)
        if not loc_obj:
            return False
        main_number = (
            loc_obj.get("main_number")
            or (loc_obj.get("pre_migration_state") or {}).get("main_number")
            or ""
        )
        if not main_number:
            return False
        # Check via user's own extension first
        user_obj = store.get_object(user_id)
        if user_obj:
            user_state = user_obj.get("pre_migration_state") or {}
            user_ext = user_state.get("extension") or ""
            if user_ext == main_number:
                return True
        # Fallback: check via line cross-refs
        for line_data in store.get_objects("line"):
            line_state = line_data.get("pre_migration_state") or {}
            line_ext = line_state.get("extension") or line_state.get("pattern") or ""
            if line_ext == main_number:
                line_id = line_data["canonical_id"]
                user_refs = store.find_cross_refs(line_id, "line_assigned_to_user")
                if user_id in user_refs:
                    return True
        return False

    def _get_monitored_members(self, store: MigrationStore, user_name: str) -> list[str]:
        """Get resolved monitored member canonical IDs from the monitoring list."""
        ml = store.get_object(f"monitoring_list:{user_name}")
        if not ml:
            return []
        members = (
            ml.get("monitored_members")
            or (ml.get("pre_migration_state") or {}).get("monitored_members")
            or []
        )
        return [
            m["target_canonical_id"]
            for m in members
            if isinstance(m, dict) and m.get("target_canonical_id")
        ]
