"""Device mapper: CUCM Phones -> Webex Calling Devices.

Maps CUCM phone (SEP) devices to CanonicalDevice objects with three-tier
model compatibility classification. Skips common-area phones (those go to
workspace_mapper).

(from 03b-transform-mappers.md §4, device_mapper)

Cross-ref reads:
    device_in_pool          (Device -> DevicePool)         — resolve pool
    device_pool_to_location (DevicePool -> Location)       — resolve location
    device_has_dn           (Device -> DN)                 — line appearances
    device_owned_by_user    (Device -> EndUser)            — owner

Decisions generated:
    DEVICE_INCOMPATIBLE          — phone model in Incompatible tier
    DEVICE_FIRMWARE_CONVERTIBLE  — phone model in Firmware Convertible tier
"""

from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.models import (
    CanonicalDevice,
    DecisionType,
    DeviceCompatibilityTier,
    MapperResult,
    MigrationStatus,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.cross_reference import classify_phone_model
from wxcli.migration.transform.mappers.base import (
    Mapper,
    accept_option,
    decision_to_store_dict,
    extract_provenance,
    manual_option,
    skip_option,
)

logger = logging.getLogger(__name__)

# PhoneOS phones: 9800-series + 8875 use cloud deviceId ("cloud" surface).
# Classic MPP (6800-series, 7800-series, 8800-series) use callingDeviceId ("telephony").
_CLOUD_SURFACE_SUBSTRINGS = {"9811", "9821", "9841", "9851", "9861", "9871", "8875"}


class DeviceMapper(Mapper):
    """Maps CUCM Phones to Webex Calling Devices.

    Skips common-area phones (is_common_area=True in pre_migration_state) —
    those are handled by workspace_mapper.

    (from 03b-transform-mappers.md §4)
    """

    name = "device_mapper"
    depends_on = ["location_mapper"]

    def map(self, store: MigrationStore) -> MapperResult:
        """Read normalized phone objects and produce CanonicalDevice objects."""
        result = MapperResult()

        for phone_data in store.get_objects("phone"):
            phone_id = phone_data["canonical_id"]
            state = phone_data.get("pre_migration_state") or {}

            # Skip common-area phones — workspace_mapper handles those
            # (from 03b-transform-mappers.md §4: "does NOT process common-area phones")
            if state.get("is_common_area", False):
                continue

            # --- Model classification ---
            # Uses classify_phone_model() from cross_reference.py
            # (from 03b-transform-mappers.md §4: phone model compatibility table)
            model = state.get("model")
            protocol = state.get("protocol", "SIP")

            # SCCP-only phones are classified as Incompatible regardless of model
            # (from 03b-transform-mappers.md §4: "SCCP-only phones classified as Incompatible")
            if protocol and protocol.upper() == "SCCP":
                compatibility_tier = DeviceCompatibilityTier.INCOMPATIBLE
            else:
                compatibility_tier = classify_phone_model(model)

            # --- MAC extraction ---
            # Strip "SEP" prefix from device name to get 12 hex digits
            # (from 03b-transform-mappers.md §4: "Extract 12 hex digits after SEP prefix")
            device_name = state.get("name", phone_id.replace("phone:", ""))
            mac = None
            if device_name.upper().startswith("SEP"):
                mac = device_name[3:].upper()
            elif len(device_name) == 12 and all(c in "0123456789ABCDEFabcdef" for c in device_name):
                mac = device_name.upper()

            # --- Location resolution ---
            # Chain: device -> device_in_pool -> device_pool_to_location
            # (from 03b-transform-mappers.md §4: cross-ref dependencies)
            location_canonical_id = store.resolve_chain(
                phone_id, "device_in_pool", "device_pool_to_location"
            )

            # --- Owner resolution ---
            # (from 03b-transform-mappers.md §4: "device_owned_by_user")
            owner_refs = store.find_cross_refs(phone_id, "device_owned_by_user")
            owner_canonical_id = owner_refs[0] if owner_refs else None

            # --- Line appearances ---
            # (from 03b-transform-mappers.md §4: "line appearances stored for post-creation config")
            dn_refs = store.find_cross_refs(phone_id, "device_has_dn")
            line_appearances = state.get("line_appearances", [])

            # --- Display name ---
            display_name = state.get("description") or device_name

            # --- Device ID surface ---
            # PhoneOS phones (9800-series, 8875) use cloud deviceId; all others use callingDeviceId.
            device_id_surface = "cloud" if any(s in (model or "") for s in _CLOUD_SURFACE_SUBSTRINGS) else "telephony"

            # --- Build CanonicalDevice ---
            device = CanonicalDevice(
                canonical_id=f"device:{device_name}",
                provenance=extract_provenance(phone_data),
                status=MigrationStatus.ANALYZED,
                mac=mac,
                model=model,
                compatibility_tier=compatibility_tier,
                display_name=display_name,
                owner_canonical_id=owner_canonical_id,
                location_canonical_id=location_canonical_id,
                line_appearances=line_appearances,
                cucm_protocol=protocol,
                cucm_device_name=device_name,
                device_id_surface=device_id_surface,
            )

            store.upsert_object(device)
            result.objects_created += 1

            # --- Generate decisions for non-native devices ---
            if compatibility_tier == DeviceCompatibilityTier.INCOMPATIBLE:
                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.DEVICE_INCOMPATIBLE,
                    severity="HIGH",
                    summary=(
                        f"Device '{device_name}' (model: {model or 'unknown'}, "
                        f"protocol: {protocol}) is incompatible with Webex Calling"
                    ),
                    context={
                        "device_id": device.canonical_id,
                        "device_name": device_name,
                        "model": model,
                        "protocol": protocol,
                        "compatibility_tier": compatibility_tier.value,
                    },
                    options=[
                        skip_option("Migrate user without device — user must use Webex app or get new phone"),
                        manual_option("Replace with compatible MPP phone (68xx series recommended)"),
                    ],
                    affected_objects=[device.canonical_id],
                )
                store.save_decision(decision_to_store_dict(decision))
                result.decisions.append(decision)

            elif compatibility_tier == DeviceCompatibilityTier.CONVERTIBLE:
                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.DEVICE_FIRMWARE_CONVERTIBLE,
                    severity="MEDIUM",
                    summary=(
                        f"Device '{device_name}' (model: {model}) requires firmware "
                        f"conversion from Enterprise to MPP"
                    ),
                    context={
                        "device_id": device.canonical_id,
                        "device_name": device_name,
                        "model": model,
                        "protocol": protocol,
                        "compatibility_tier": compatibility_tier.value,
                    },
                    options=[
                        accept_option(
                            "Convert firmware — factory reset, load MPP firmware via TFTP/EDOS, "
                            "then register to Webex via activation code"
                        ),
                        manual_option("Replace with native MPP phone (68xx series)"),
                        skip_option("Migrate user without device"),
                    ],
                    affected_objects=[device.canonical_id],
                )
                store.save_decision(decision_to_store_dict(decision))
                result.decisions.append(decision)

        return result


