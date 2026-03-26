"""DeviceLayoutMapper: per-device resolved line key + KEM layout.

Merges CanonicalLineKeyTemplate structure with per-phone line appearances,
speed dials, and BLF entries. Resolves DNs to canonical user IDs and
detects shared lines via CanonicalSharedLine objects.

Reads raw phone objects (object_type="phone") which contain the full AXL
getPhone response in pre_migration_state. Key fields:
  - lines: list of line dicts with {index, label, dirn: {pattern, routePartitionName}}
  - speeddials: {speeddial: [{dirn, label, index}, ...]}
  - busyLampFields: {busyLampField: [{blfDest, label, index}, ...]}
  - ownerUserName: zeep ref dict {"_value_1": "userid", "uuid": "..."}

(from tier2-phase2-phone-config-design.md §4.2)
"""
from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.models import (
    CanonicalDeviceLayout,
    MapperResult,
    MigrationStatus,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.base import (
    Mapper,
    extract_provenance,
)
from wxcli.migration.transform.mappers.monitoring_mapper import (
    _extract_blf_entries,
    _extract_speed_dials,
)

logger = logging.getLogger(__name__)


def _ref_value(field: Any) -> str | None:
    """Extract display value from a zeep ref dict or plain string."""
    if field is None:
        return None
    if isinstance(field, str):
        return field or None
    if isinstance(field, dict):
        val = field.get("_value_1")
        return val if val else None
    return None


class DeviceLayoutMapper(Mapper):
    """Per-device layout: merges button template with actual phone data."""

    name = "device_layout_mapper"
    depends_on = ["button_template_mapper", "monitoring_mapper", "line_mapper", "device_mapper"]

    def map(self, store: MigrationStore) -> MapperResult:
        result = MapperResult()

        shared_dns = self._build_shared_dn_set(store)

        for phone_data in store.get_objects("phone"):
            phone_id = phone_data["canonical_id"]
            state = phone_data.get("pre_migration_state") or {}

            # Skip common-area phones (no ownerUserName)
            owner_raw = _ref_value(state.get("ownerUserName"))
            if not owner_raw and state.get("class") == "Phone":
                continue

            phone_name = state.get("name", phone_id.split(":", 1)[-1])
            device_id = f"device:{phone_name}"

            # Resolve owner via device cross-ref (device_owned_by_user links device:, not phone:)
            owner_id = None
            owner_refs = store.find_cross_refs(device_id, "device_owned_by_user")
            if owner_refs:
                owner_id = owner_refs[0]

            # Resolve button template via phone cross-ref
            tmpl_refs = store.find_cross_refs(phone_id, "phone_uses_button_template")
            tmpl_id = None
            tmpl_line_keys: list[dict] = []
            tmpl_kem_keys: list[dict] = []
            if tmpl_refs:
                lkt_id = tmpl_refs[0].replace("button_template:", "line_key_template:")
                lkt = store.get_object(lkt_id)
                if lkt:
                    tmpl_id = lkt_id
                    lkt_data = lkt if isinstance(lkt, dict) else lkt.model_dump()
                    tmpl_line_keys = lkt_data.get("line_keys", [])
                    tmpl_kem_keys = lkt_data.get("kem_keys", [])

            # Raw phone data: lines are a flat list from the extractor
            raw_lines = state.get("lines", [])
            if isinstance(raw_lines, dict):
                raw_lines = raw_lines.get("line", [])
                if isinstance(raw_lines, dict):
                    raw_lines = [raw_lines]

            # Index line appearances by position
            la_by_index: dict[int, dict] = {}
            for la in raw_lines:
                if not isinstance(la, dict):
                    continue
                dirn = la.get("dirn")
                if not dirn or not isinstance(dirn, dict):
                    continue
                idx = la.get("index")
                if idx is not None:
                    la_by_index[int(idx)] = la

            # Speed dials and BLF indexed by button position
            speed_dials_raw = _extract_speed_dials(state)
            blf_entries_raw = _extract_blf_entries(state)

            sd_by_index: dict[int, dict] = {}
            for sd in speed_dials_raw:
                idx = sd.get("index") or sd.get("speedDialIndex")
                if idx is not None:
                    sd_by_index[int(idx)] = sd

            blf_by_index: dict[int, dict] = {}
            for blf in blf_entries_raw:
                idx = blf.get("index")
                if idx is not None:
                    blf_by_index[int(idx)] = blf

            # Build line_members from line appearances
            line_members: list[dict[str, Any]] = []
            for la_idx in sorted(la_by_index.keys()):
                la = la_by_index[la_idx]
                dirn = la.get("dirn", {})
                dn = dirn.get("pattern", "")
                partition = _ref_value(dirn.get("routePartitionName"))
                label = la.get("label")

                member_id = self._resolve_dn_to_user(store, dn)

                dn_key = f"{dn}:{partition}" if partition else dn
                line_type = (
                    "SHARED_LINE"
                    if dn_key in shared_dns or dn in shared_dns
                    else "PRIMARY"
                )

                line_members.append({
                    "port": la_idx,
                    "member_canonical_id": member_id,
                    "line_type": line_type,
                    "line_label": label,
                })

            # Merge template keys with phone data
            resolved_line_keys = self._resolve_keys(
                tmpl_line_keys, la_by_index, sd_by_index, blf_by_index, store,
            )
            resolved_kem_keys = self._resolve_keys(
                tmpl_kem_keys, la_by_index, sd_by_index, blf_by_index, store,
            )

            # Collect speed dials
            speed_dials = []
            for idx in sorted(sd_by_index.keys()):
                sd = sd_by_index[idx]
                speed_dials.append({
                    "index": idx,
                    "label": sd.get("label", ""),
                    "number": sd.get("dirn") or sd.get("speedDialNumber", ""),
                })

            # Copy device_id_surface from the associated CanonicalDevice
            device_obj = store.get_object(device_id)
            device_id_surface = device_obj.get("device_id_surface", "telephony") if device_obj else "telephony"

            layout = CanonicalDeviceLayout(
                canonical_id=f"device_layout:{phone_name}",
                provenance=extract_provenance(phone_data),
                status=MigrationStatus.ANALYZED,
                device_canonical_id=device_id,
                template_canonical_id=tmpl_id,
                owner_canonical_id=owner_id,
                line_members=line_members,
                resolved_line_keys=resolved_line_keys,
                resolved_kem_keys=resolved_kem_keys,
                speed_dials=speed_dials,
                device_id_surface=device_id_surface,
            )
            store.upsert_object(layout)

            store.add_cross_ref(phone_id, layout.canonical_id, "phone_has_layout")
            if device_obj is not None:
                store.add_cross_ref(device_id, layout.canonical_id, "device_has_layout")
            if layout.template_canonical_id:
                store.add_cross_ref(
                    layout.canonical_id,
                    layout.template_canonical_id,
                    "layout_uses_template",
                )
            result.objects_created += 1

        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_keys(
        self,
        template_keys: list[dict],
        la_by_index: dict[int, dict],
        sd_by_index: dict[int, dict],
        blf_by_index: dict[int, dict],
        store: MigrationStore,
    ) -> list[dict[str, Any]]:
        """Resolve template key slots with phone-specific values."""
        resolved = []
        for key in template_keys:
            idx = key.get("index", 0)
            key_type = key.get("key_type", "OPEN")
            entry: dict[str, Any] = {"index": idx, "key_type": key_type}

            if key_type in ("PRIMARY_LINE", "SHARED_LINE", "LINE"):
                la = la_by_index.get(idx)
                if la:
                    dirn = la.get("dirn", {})
                    dn = dirn.get("pattern", "") if isinstance(dirn, dict) else ""
                    entry["label"] = la.get("label")
                    entry["target_canonical_id"] = self._resolve_dn_to_user(store, dn)

            elif key_type == "SPEED_DIAL":
                sd = sd_by_index.get(idx)
                if sd:
                    entry["label"] = sd.get("label", "")
                    entry["value"] = sd.get("dirn") or sd.get("speedDialNumber", "")

            elif key_type == "MONITOR":
                blf = blf_by_index.get(idx)
                if blf:
                    target_dn = blf.get("blfDest") or ""
                    entry["label"] = blf.get("label", target_dn)
                    entry["target_canonical_id"] = self._resolve_dn_to_user(
                        store, target_dn,
                    )

            elif key_type == "CALL_PARK_EXTENSION":
                entry["label"] = "Call Park"

            resolved.append(entry)
        return resolved

    def _resolve_dn_to_user(
        self, store: MigrationStore, dn: str,
    ) -> str | None:
        """Resolve a DN to a user canonical_id via line cross-refs."""
        if not dn:
            return None
        for line_data in store.get_objects("line"):
            line_state = line_data.get("pre_migration_state") or {}
            line_ext = (
                line_data.get("extension")
                or line_state.get("extension")
                or line_state.get("pattern")
            )
            if line_ext == dn:
                line_id = line_data["canonical_id"]
                user_refs = store.find_cross_refs(line_id, "line_assigned_to_user")
                if user_refs:
                    return user_refs[0]
        return None

    def _build_shared_dn_set(self, store: MigrationStore) -> set[str]:
        """Build a set of DN keys that are shared lines."""
        shared: set[str] = set()
        for sl in store.get_objects("shared_line"):
            dn_id = sl.get("dn_canonical_id", "")
            if dn_id:
                parts = dn_id.split(":", 1)
                if len(parts) > 1:
                    shared.add(parts[1])
                shared.add(dn_id)
        return shared
