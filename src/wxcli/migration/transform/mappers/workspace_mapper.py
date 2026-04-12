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
from wxcli.migration.cucm.extractors.helpers import ref_value
from wxcli.migration.transform.mappers.call_forwarding_mapper import _duration_to_rings

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
            # pre_migration_state here is the raw AXL getPhone dict (preserved by pipeline.py
            # alongside the CanonicalDevice). Field names use original CUCM casing, not the
            # normalized CanonicalDevice field names.
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
        enabled = dnd_status in ("true", True, "1")
        ring_splash = enabled and state.get("dndOption") == "Ringer Off"
        settings["doNotDisturb"] = {
            "enabled": enabled,
            "ringSplashEnabled": ring_splash,
        }

    # --- voicemail (Professional-only; license gate drops it for Workspace tier) ---
    # voiceMailProfileName is extracted per-line via getLine enrichment. Live AXL
    # returns it as a zeep reference dict: {"_value_1": "name", "uuid": "..."},
    # so unwrap with ref_value().
    first_line = _get_first_line(state)
    vm_profile = ref_value(first_line.get("voiceMailProfileName")) if first_line else None
    has_vm_profile = bool(vm_profile) and vm_profile.lower() not in ("none", "")
    if has_vm_profile:
        vm_body: dict[str, Any] = {"enabled": True}
        # Pull CFNA ring timing + VM flag from line 1
        if first_line:
            cfna = first_line.get("callForwardNoAnswer") or {}
            if cfna.get("forwardToVoiceMail") in ("true", True):
                duration = cfna.get("duration")
                rings = _duration_to_rings(duration) or 3
                vm_body["sendUnansweredCalls"] = {
                    "enabled": True,
                    "numberOfRings": rings,
                }
            cfb = first_line.get("callForwardBusy") or {}
            if cfb.get("forwardToVoiceMail") in ("true", True):
                vm_body["sendBusyCalls"] = {"enabled": True}
        settings["voicemail"] = vm_body
    else:
        # Webex defaults VM to enabled; common-area phones almost always want it OFF
        settings["voicemail"] = {"enabled": False}

    # --- callForwarding (Professional-only) ---
    line1 = _get_first_line(state)
    if line1:
        # Only emit callForwarding if there's an explicit destination. When CUCM
        # has forwardToVoiceMail=true with destination=None (forward to the phone's
        # voicemail), we intentionally skip callForwarding — the voicemail block
        # above already captures the user intent. Webex /telephony/config/.../callForwarding
        # doesn't accept a "forward to voicemail" sentinel; that requires the voicemail endpoint.
        cfa = (line1.get("callForwardAll") or {}).get("destination")
        cfb = (line1.get("callForwardBusy") or {}).get("destination")
        cfna_raw = line1.get("callForwardNoAnswer") or {}
        cfna_dest = cfna_raw.get("destination")
        if cfa or cfb or cfna_dest:
            cf_body: dict[str, Any] = {
                "always": {"enabled": bool(cfa)},
                "busy": {"enabled": bool(cfb)},
                "noAnswer": {"enabled": bool(cfna_dest)},
            }
            if cfa:
                cf_body["always"]["destination"] = cfa
            if cfb:
                cf_body["busy"]["destination"] = cfb
            if cfna_dest:
                cf_body["noAnswer"]["destination"] = cfna_dest
                duration = cfna_raw.get("duration")
                cf_body["noAnswer"]["numberOfRings"] = _duration_to_rings(duration) or 3
            settings["callForwarding"] = cf_body

    # --- privacy (Professional-only) ---
    # Real CUCM AXL field name is callInfoPrivacyStatus. Values observed on live
    # CUCM 14.0 dCloud: "On" (privacy enabled), "Default" (inherits from common
    # phone profile), or None (no owner — unowned phones don't get this field).
    privacy = state.get("callInfoPrivacyStatus")
    if privacy == "On":
        settings["privacy"] = {"enabled": True}

    # License tier gating: Workspace-tier only supports DND + MOH at /telephony/config/
    # (from docs/reference/devices-workspaces.md license tier access matrix)
    if license_tier == "Workspace":
        allowed = {"doNotDisturb", "musicOnHold"}
        settings = {k: v for k, v in settings.items() if k in allowed}

    return settings or None


def _get_first_line(state: dict[str, Any]) -> dict | None:
    """Return the first line entry from a raw phone state, or None if missing."""
    lines = state.get("lines") or []
    if isinstance(lines, dict):
        return lines.get(1) or lines.get("1")
    if isinstance(lines, list) and lines and isinstance(lines[0], dict):
        return lines[0]
    return None


