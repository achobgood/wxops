"""Workspace mapper: CUCM Common-area Phones -> Webex Workspaces.

Maps CUCM common-area phones (conference rooms, lobby phones, break rooms) to
CanonicalWorkspace objects with associated device references.

(from 03b-transform-mappers.md §5, workspace_mapper)

Cross-ref reads:
    common_area_device_in_pool (Common-area device -> DevicePool)
    device_pool_to_location    (DevicePool -> Location)
    device_has_dn              (Device -> DN)

Decisions generated:
    WORKSPACE_LICENSE_TIER     — Workspace vs Professional Workspace license determination
    WORKSPACE_TYPE_UNCERTAIN   — ambiguous workspace classification
    HOTDESK_DN_CONFLICT        — device has both DN and hoteling enabled
"""

from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.models import (
    CanonicalWorkspace,
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

# Keywords that hint at workspace type classification
# (from 03b-transform-mappers.md §5: heuristic for type inference)
_MEETING_ROOM_HINTS = {"conf", "conference", "meeting", "room", "boardroom", "huddle"}
_DESK_HINTS = {"desk", "hotdesk", "hot-desk", "shared", "hoteling"}


class WorkspaceMapper(Mapper):
    """Maps CUCM common-area phones to Webex Workspaces.

    Only processes phones/devices flagged as is_common_area=True by the normalizer.

    (from 03b-transform-mappers.md §5)
    """

    name = "workspace_mapper"
    depends_on = ["location_mapper"]

    def map(self, store: MigrationStore) -> MapperResult:
        """Read common-area phone objects and produce CanonicalWorkspace objects."""
        result = MapperResult()

        for phone_data in store.get_objects("phone"):
            phone_id = phone_data["canonical_id"]
            state = phone_data.get("pre_migration_state") or {}

            # Only process common-area phones
            # (from 03b-transform-mappers.md §5: "only processes phones flagged as is_common_area=true")
            if not state.get("is_common_area", False):
                continue

            device_name = state.get("name", phone_id.replace("phone:", ""))
            model = state.get("model")

            # --- Location resolution ---
            # Chain: common-area device -> common_area_device_in_pool -> device_pool_to_location
            # (from 03b-transform-mappers.md §5: cross-ref dependencies)
            location_id = store.resolve_chain(
                phone_id, "common_area_device_in_pool", "device_pool_to_location"
            )

            # --- Extension / phone number resolution ---
            # Primary line (line 1) from device_has_dn cross-ref
            # (from 03b-transform-mappers.md §5: "DN from device line 1")
            extension = None
            phone_number = None
            dn_refs = store.find_cross_refs(phone_id, "device_has_dn")
            if dn_refs:
                # Use the first DN (primary line)
                dn_id = dn_refs[0]
                # DN IDs are formatted as "dn:pattern:partition"
                parts = dn_id.split(":", 2)
                if len(parts) >= 2:
                    dn_pattern = parts[1]
                    # If it looks like E.164 (starts with +), it's a phone_number
                    if dn_pattern.startswith("+"):
                        phone_number = dn_pattern
                    else:
                        extension = dn_pattern

                    # Check if there's e164 enrichment data in the store
                    dn_data = store.get_object(dn_id)
                    if dn_data:
                        dn_state = dn_data.get("pre_migration_state") or {}
                        e164_result = dn_state.get("e164_result")
                        if e164_result:
                            if e164_result.get("e164"):
                                phone_number = e164_result["e164"]
                            if e164_result.get("extension"):
                                extension = e164_result["extension"]

            # --- Display name ---
            # (from 03b-transform-mappers.md §5: "description, fallback to device name")
            display_name = state.get("description") or device_name

            # --- Supported devices ---
            # (from 03b-transform-mappers.md §5: "phones for MPP, collaborationDevices for Room/Board/Desk")
            supported_devices = _infer_supported_devices(model)

            # --- Hotdesking status ---
            # enableExtensionMobility is the CUCM field (not 'hotelingEnabled')
            # (from 02b-cucm-extraction.md §2.5: enableExtensionMobility on Phone)
            em_val = state.get("enableExtensionMobility", False)
            hotdesking_status = "on" if em_val in (True, "true", "True") else "off"

            # --- Workspace type inference ---
            # (from 03b-transform-mappers.md §5: heuristic from device pool name/description)
            dp_name = state.get("cucm_device_pool", "")
            workspace_type = _infer_workspace_type(display_name, dp_name)

            # --- License tier inference ---
            # (from 03b-transform-mappers.md §5: Workspace vs Professional Workspace)
            # Default to Workspace; Professional Workspace if advanced settings are needed
            license_tier = _infer_license_tier(state)

            # --- Hotdesk + DN conflict check ---
            # (from 03b-transform-mappers.md §5: "Webex hot desk workspaces cannot have extension")
            has_dn = extension is not None or phone_number is not None
            is_hotdesk = hotdesking_status == "on"

            if has_dn and is_hotdesk:
                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.HOTDESK_DN_CONFLICT,
                    severity="MEDIUM",
                    summary=(
                        f"Common-area device '{device_name}' has both a DN and "
                        f"hoteling enabled — Webex hot desk workspaces cannot have "
                        f"extension or phoneNumber"
                    ),
                    context={
                        "device_name": device_name,
                        "extension": extension,
                        "phone_number": phone_number,
                        "hotdesking_status": hotdesking_status,
                    },
                    options=[
                        accept_option("Preserve extension — disable hot desking"),
                        accept_option("Preserve hot desking — drop the DN"),
                        manual_option("Admin decides how to resolve this conflict"),
                    ],
                    affected_objects=[phone_id],
                )
                store.save_decision(decision_to_store_dict(decision))
                result.decisions.append(decision)

            # --- Workspace type uncertain ---
            if workspace_type is None:
                workspace_type = "other"  # default fallback
                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.WORKSPACE_TYPE_UNCERTAIN,
                    severity="LOW",
                    summary=(
                        f"Common-area device '{device_name}' has ambiguous workspace "
                        f"classification — device pool '{dp_name}' does not clearly "
                        f"indicate room type"
                    ),
                    context={
                        "device_name": device_name,
                        "device_pool": dp_name,
                        "display_name": display_name,
                    },
                    options=[
                        accept_option("Use 'meetingRoom' — conference room equipment"),
                        accept_option("Use 'desk' — shared desk / hot desk"),
                        accept_option("Use 'other' — lobby phone, break room, etc."),
                    ],
                    affected_objects=[phone_id],
                )
                store.save_decision(decision_to_store_dict(decision))
                result.decisions.append(decision)

            # --- License tier decision ---
            # Always produce this decision so admin can confirm
            # (from 03b-transform-mappers.md §5: WORKSPACE_LICENSE_TIER)
            decision = self._create_decision(
                store=store,
                decision_type=DecisionType.WORKSPACE_LICENSE_TIER,
                severity="LOW",
                summary=(
                    f"Workspace '{display_name}' inferred as {license_tier} license tier"
                ),
                context={
                    "device_name": device_name,
                    "display_name": display_name,
                    "inferred_tier": license_tier,
                    "model": model,
                },
                options=[
                    accept_option(
                        f"Workspace — most /telephony/config/workspaces/ settings return 405, "
                        f"only musicOnHold and doNotDisturb work"
                    ),
                    accept_option(
                        "Professional Workspace — full settings access, higher license cost"
                    ),
                ],
                affected_objects=[phone_id],
            )
            store.save_decision(decision_to_store_dict(decision))
            result.decisions.append(decision)

            # --- Call settings extraction ---
            call_settings = _extract_workspace_call_settings(state, license_tier)

            # --- Build CanonicalWorkspace ---
            workspace = CanonicalWorkspace(
                canonical_id=f"workspace:{device_name}",
                provenance=extract_provenance(phone_data),
                status=MigrationStatus.ANALYZED,
                display_name=display_name,
                location_id=location_id,
                supported_devices=supported_devices,
                extension=extension,
                phone_number=phone_number,
                calling_type="webexCalling",
                workspace_type=workspace_type,
                hotdesking_status=hotdesking_status,
                is_common_area=True,
                license_tier=license_tier,
                call_settings=call_settings,
            )

            store.upsert_object(workspace)
            result.objects_created += 1

        return result


def _infer_supported_devices(model: str | None) -> str:
    """Infer supportedDevices value from phone model.

    (from 03b-transform-mappers.md §5: "phones for MPP, collaborationDevices for Room/Board/Desk")
    """
    if not model:
        return "phones"

    model_upper = model.upper()
    # Room, Board, Desk series are collaboration devices
    for keyword in ("ROOM", "BOARD", "DESK", "WEBEX BOARD", "WEBEX ROOM", "WEBEX DESK"):
        if keyword in model_upper:
            return "collaborationDevices"

    return "phones"


def _infer_workspace_type(display_name: str, device_pool_name: str) -> str | None:
    """Infer workspace type from display name and device pool name.

    Returns 'meetingRoom', 'desk', or None if ambiguous.
    (from 03b-transform-mappers.md §5: heuristic)
    """
    combined = f"{display_name} {device_pool_name}".lower()

    for hint in _MEETING_ROOM_HINTS:
        if hint in combined:
            return "meetingRoom"

    for hint in _DESK_HINTS:
        if hint in combined:
            return "desk"

    return None


def _infer_license_tier(state: dict[str, Any]) -> str:
    """Infer Workspace vs Professional Workspace license tier from CUCM settings.

    Professional Workspace is needed if the device has:
    - Call recording enabled
    - Voicemail with custom greetings
    - Outgoing call permissions
    Otherwise Workspace license suffices.

    (from 03b-transform-mappers.md §5: WORKSPACE_LICENSE_TIER decision)
    """
    if state.get("call_recording_enabled"):
        return "Professional Workspace"
    if state.get("voicemail_enabled") and state.get("custom_greetings"):
        return "Professional Workspace"
    if state.get("outgoing_call_permissions"):
        return "Professional Workspace"
    return "Workspace"


def _extract_workspace_call_settings(
    state: dict[str, Any],
    license_tier: str,
) -> dict[str, Any] | None:
    """Translate common-area phone state into a Webex workspace call_settings dict.

    Returns a dict keyed by /telephony/config/workspaces/{id}/{key} path suffix.
    Keys emitted depend on ``license_tier``:
      - Workspace (basic): only ``doNotDisturb`` (Webex returns 405 on others for Basic).
      - Professional Workspace: all detected settings.
    Returns None if nothing worth writing.
    """
    settings: dict[str, Any] = {}

    # --- doNotDisturb (both tiers) ---
    dnd_status = state.get("dndStatus")
    if dnd_status is not None:
        enabled = dnd_status in ("true", True, "1", 1)
        ring_splash = enabled and state.get("dndOption") == "Ringer Off"
        settings["doNotDisturb"] = {
            "enabled": enabled,
            "ringSplashEnabled": ring_splash,
        }

    # License tier gating: Workspace-tier only supports DND + MOH at /telephony/config/
    # (from docs/reference/devices-workspaces.md license tier access matrix)
    if license_tier == "Workspace":
        allowed = {"doNotDisturb", "musicOnHold"}
        settings = {k: v for k, v in settings.items() if k in allowed}

    return settings or None


