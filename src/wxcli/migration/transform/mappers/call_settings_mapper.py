"""CallSettingsMapper — extract per-user call settings from CUCM phone data.

Reads phone objects, resolves user ownership, and populates call_settings
on CanonicalUser objects. Settings extracted: DND, call waiting, caller ID,
privacy, barge-in, recording.

Multi-device users: first phone encountered wins (store insertion order).
This is acceptable because most CUCM users have one primary phone with
non-default settings. If a user has conflicting settings across phones,
the first phone's settings are used.

Runs AFTER CallForwardingMapper and MonitoringMapper (depends on user_mapper,
uses device_owned_by_user cross-ref from phone:{name}).
"""
from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.models import MapperResult
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.base import Mapper, enrich_user

logger = logging.getLogger(__name__)


class CallSettingsMapper(Mapper):
    """Extract per-user call settings from CUCM phone data."""

    name = "call_settings_mapper"
    depends_on = ["user_mapper"]

    def map(self, store: MigrationStore) -> MapperResult:
        result = MapperResult()

        for phone_data in store.get_objects("phone"):
            phone_id = phone_data["canonical_id"]
            state = phone_data.get("pre_migration_state") or {}

            # Skip common-area phones
            if state.get("is_common_area"):
                continue

            # Resolve owner user
            user_refs = store.find_cross_refs(phone_id, "device_owned_by_user")
            if not user_refs:
                continue
            user_id = user_refs[0]

            # Skip if already enriched (multi-device user — only first phone wins)
            user_data = store.get_object(user_id)
            if not user_data:
                continue
            if user_data.get("call_settings"):
                continue

            # Extract non-default settings
            settings = self._extract_settings(state)
            if not settings:
                continue

            # Enrich user object
            enrich_user(store, user_id, call_settings=settings)
            result.objects_updated += 1
            logger.debug(
                "Enriched user %s with call_settings from phone %s: %s",
                user_id, phone_id, list(settings.keys()),
            )


        # --- Pass 2: Intercept candidate detection ---
        for user_data in store.get_objects("user"):
            user_id = user_data["canonical_id"]
            intercept_refs = store.find_cross_refs(user_id, "user_has_intercept_signal")
            if not intercept_refs:
                continue
            candidate = store.get_object(intercept_refs[0])
            if not candidate:
                continue
            pre = candidate.get("pre_migration_state") or {}
            intercept_settings = {
                "detected": True,
                "signal_type": pre.get("signal_type", "unknown"),
                "forward_destination": pre.get("forward_destination"),
                "voicemail_enabled": pre.get("voicemail_enabled", False),
            }
            existing_settings = user_data.get("call_settings") or {}
            existing_settings["intercept"] = intercept_settings
            enrich_user(store, user_id, call_settings=existing_settings)
            result.objects_updated += 1

        return result

    def _extract_settings(self, state: dict[str, Any]) -> dict[str, Any] | None:
        """Extract non-default call settings from phone pre_migration_state."""
        settings: dict[str, Any] = {}

        # DND
        dnd_status = state.get("dndStatus")
        if dnd_status in ("true", True, "1"):
            dnd_option = state.get("dndOption", "Call Reject")
            settings["doNotDisturb"] = {
                "enabled": True,
                "ringSplashEnabled": dnd_option == "Ringer Off",
            }

        # Call waiting
        # CUCM: callWaiting on line appearance (first line)
        # lines may be a list or a dict (integer-keyed) depending on AXL normalization
        lines = state.get("lines") or []
        first_line: dict | None = None
        if isinstance(lines, dict):
            first_line = lines.get(1) or lines.get("1")
        elif isinstance(lines, list) and lines:
            candidate = lines[0]
            if isinstance(candidate, dict):
                first_line = candidate
        if first_line is not None:
            cw = first_line.get("callWaiting")
            if cw in ("false", False, "0"):
                settings["callWaiting"] = {"enabled": False}

        # Caller ID (external caller ID restriction)
        caller_id_block = state.get("callerIdBlock")
        if caller_id_block in ("true", True):
            settings["callerId"] = {
                "externalCallerIdNamePolicy": "DIRECT_LINE",
                "blockInForwardCallsEnabled": True,
            }

        # Privacy
        privacy = state.get("enablePrivacy")
        if privacy in ("true", True):
            settings["privacy"] = {"enablePhoneStatusPrivacyIndicator": True}

        # Recording
        recording = state.get("builtInBridgeStatus")
        if recording in ("On", "true", True):
            settings["callRecording"] = {
                "enabled": True,
                "record": "Always",
            }

        return settings if settings else None
