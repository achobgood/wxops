"""DeviceLayoutMapper: per-device resolved line key + KEM layout.

Merges CanonicalLineKeyTemplate structure with per-phone line appearances,
speed dials, and BLF entries. Resolves DNs to canonical user IDs and
detects shared lines via CanonicalSharedLine objects.

(from tier2-phase2-phone-config-design.md §4.2)

Cross-ref reads:
    phone_uses_button_template  (Phone → ButtonTemplate)  — template lookup
    device_owned_by_user        (Phone → User)             — owner
    line_assigned_to_user       (Line → User)              — DN resolution
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


class DeviceLayoutMapper(Mapper):
    """Per-device layout: merges button template with actual phone data."""

    name = "device_layout_mapper"
    depends_on = ["button_template_mapper", "monitoring_mapper", "line_mapper", "device_mapper"]

    def map(self, store: MigrationStore) -> MapperResult:
        result = MapperResult()

        # Pre-load shared line DNs for fast lookup
        shared_dns = self._build_shared_dn_set(store)

        for phone_data in store.get_objects("phone"):
            phone_id = phone_data["canonical_id"]
            state = phone_data.get("pre_migration_state") or {}

            # Skip common-area phones
            if state.get("is_common_area", False):
                continue

            phone_name = state.get("name", phone_id.split(":", 1)[-1])

            # Resolve owner
            owner_refs = store.find_cross_refs(phone_id, "device_owned_by_user")
            owner_id = owner_refs[0] if owner_refs else None

            # Resolve button template
            tmpl_refs = store.find_cross_refs(phone_id, "phone_uses_button_template")
            tmpl_id = None
            tmpl_line_keys: list[dict] = []
            tmpl_kem_keys: list[dict] = []
            if tmpl_refs:
                lkt_id = tmpl_refs[0].replace("button_template:", "line_key_template:")
                lkt = store.get_object(lkt_id)
                if lkt:
                    tmpl_id = lkt_id
                    tmpl_line_keys = lkt.get("line_keys", [])
                    tmpl_kem_keys = lkt.get("kem_keys", [])

            # Phone-specific data
            line_appearances = state.get("line_appearances", [])
            speed_dials_raw = _extract_speed_dials(state)
            blf_entries_raw = _extract_blf_entries(state)

            # Index speed dials and BLF by position
            sd_by_index: dict[str, dict] = {}
            for sd in speed_dials_raw:
                idx = sd.get("speedDialIndex") or sd.get("index")
                if idx:
                    sd_by_index[str(idx)] = sd

            blf_by_index: dict[str, dict] = {}
            for i, blf in enumerate(blf_entries_raw):
                blf_by_index[str(i + 1)] = blf

            # Build line_members from line appearances
            line_members: list[dict[str, Any]] = []
            la_by_index = {
                la.get("line_index", i + 1): la
                for i, la in enumerate(line_appearances)
            }

            for la_idx, la in sorted(la_by_index.items()):
                dn = la.get("dn", "")
                partition = la.get("partition")
                label = la.get("line_label")

                # Resolve DN to user
                member_id = self._resolve_dn_to_user(store, dn)

                # Check shared
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
            for idx, sd in sd_by_index.items():
                speed_dials.append({
                    "index": int(idx),
                    "label": sd.get("label", ""),
                    "number": sd.get("speedDialNumber", sd.get("dirn", "")),
                })

            layout = CanonicalDeviceLayout(
                canonical_id=f"device_layout:{phone_name}",
                provenance=extract_provenance(phone_data),
                status=MigrationStatus.ANALYZED,
                device_canonical_id=f"device:{phone_name}",
                template_canonical_id=tmpl_id,
                owner_canonical_id=owner_id,
                line_members=line_members,
                resolved_line_keys=resolved_line_keys,
                resolved_kem_keys=resolved_kem_keys,
                speed_dials=speed_dials,
            )
            store.upsert_object(layout)

            # Link phone → layout (phone always exists in the store)
            store.add_cross_ref(
                phone_id, layout.canonical_id, "phone_has_layout",
            )
            # Also link device → layout if the device object exists
            device_id = f"device:{phone_name}"
            if store.get_object(device_id) is not None:
                store.add_cross_ref(
                    device_id, layout.canonical_id, "device_has_layout",
                )
            result.objects_created += 1

        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_keys(
        self,
        template_keys: list[dict],
        la_by_index: dict,
        sd_by_index: dict,
        blf_by_index: dict,
        store: MigrationStore,
    ) -> list[dict[str, Any]]:
        """Resolve template key slots with phone-specific values."""
        resolved = []
        blf_counter = 0
        for key in template_keys:
            idx = key.get("index", 0)
            key_type = key.get("key_type", "OPEN")
            entry: dict[str, Any] = {"index": idx, "key_type": key_type}

            if key_type in ("PRIMARY_LINE", "SHARED_LINE", "LINE"):
                la = la_by_index.get(idx)
                if la:
                    entry["label"] = la.get("line_label")
                    dn = la.get("dn", "")
                    member_id = self._resolve_dn_to_user(store, dn)
                    entry["target_canonical_id"] = member_id

            elif key_type == "SPEED_DIAL":
                sd = sd_by_index.get(str(idx))
                if sd:
                    entry["label"] = sd.get("label", "")
                    entry["value"] = sd.get(
                        "speedDialNumber", sd.get("dirn", ""),
                    )

            elif key_type == "MONITOR":
                blf_counter += 1
                blf = blf_by_index.get(str(blf_counter))
                if blf:
                    target_dn = (
                        blf.get("blfDest") or blf.get("blfDirn") or ""
                    )
                    entry["label"] = blf.get("label", target_dn)
                    entry["target_canonical_id"] = self._resolve_dn_to_user(
                        store, target_dn,
                    )

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
                # Extract DN pattern from canonical_id like "line:1001"
                parts = dn_id.split(":", 1)
                if len(parts) > 1:
                    shared.add(parts[1])
                shared.add(dn_id)
        return shared
