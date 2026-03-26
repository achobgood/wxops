"""Voicemail mapper: CUCM Unity Connection VM profiles -> Webex per-person voicemail.

Maps Unity Connection voicemail profiles (shared config) plus per-user VM settings
to Webex Calling per-person voicemail settings (CanonicalVoicemailProfile).

(from 03b-transform-mappers.md §9, voicemail_mapper)

Cross-ref reads:
    user_has_voicemail_profile  (#26) — EndUser -> VoicemailProfile
    voicemail_profile_settings  (#27) — VoicemailProfile -> settings

Per-user VM settings:
    store.get_object(f"unity_vm:{userid}") — per-user Unity Connection settings
    (from Phase 04 corrections: unity_vm objects for notifications, greetings, etc.)

Decisions generated:
    VOICEMAIL_INCOMPATIBLE — UC features without Webex equivalent (13-row gap table §11)
    MISSING_DATA           — custom greeting audio files can't be extracted
"""

from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.models import (
    CanonicalVoicemailProfile,
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
    hash_id,
    manual_option,
    skip_option,
)

logger = logging.getLogger(__name__)

# Read-only fields that must be stripped from Webex voicemail PUT
# (from 03b-transform-mappers.md §9: "Read-only fields must be stripped")
# (from docs/reference/person-call-settings-media.md: voiceMessageForwardingEnabled,
#  greetingUploaded, systemMaxNumberOfRings)
_READ_ONLY_FIELDS = frozenset([
    "voiceMessageForwardingEnabled",
    "voice_message_forwarding_enabled",
    "greetingUploaded",
    "greeting_uploaded",
    "systemMaxNumberOfRings",
    "system_max_number_of_rings",
])

# Default number of rings if CFNA timeout can't be parsed
_DEFAULT_NUMBER_OF_RINGS = 3

# Max ring count (system max is typically 20)
# (from 03b-transform-mappers.md §9: "clamp to [1, systemMaxNumberOfRings]")
_MAX_NUMBER_OF_RINGS = 20

# Voicemail gap analysis: Unity Connection features to check
# (from 03b-transform-mappers.md §11: 13-row gap table)
# Each tuple: (check_key, description, condition_fn)
# condition_fn takes (profile_settings, unity_vm_settings) and returns True if gap detected
_VM_GAP_CHECKS: list[tuple[str, str, Any]] = [
    (
        "multiple_greetings",
        "Multiple greetings per time-of-day (UC supports 6+; Webex has 2)",
        lambda p, u: (
            (p.get("alternateGreeting") is not None)
            or (p.get("offHoursGreeting") is not None)
            or (p.get("internalGreeting") is not None)
            or (p.get("holidayGreeting") is not None)
            or (u.get("alternateGreeting") is not None)
            or (u.get("offHoursGreeting") is not None)
            or (u.get("internalGreeting") is not None)
            or (u.get("holidayGreeting") is not None)
        ),
    ),
    (
        "caller_input_rules",
        "Caller input rules (press digits during greeting for routing)",
        lambda p, u: bool(
            p.get("callerInputRules") or u.get("callerInputRules")
        ),
    ),
    (
        "alternate_extensions",
        "Alternate extensions (additional pilot numbers)",
        lambda p, u: bool(
            p.get("alternateExtensions") or u.get("alternateExtensions")
        ),
    ),
    (
        "message_expiry",
        "Message expiry/retention policies",
        lambda p, u: bool(
            p.get("messageExpiry") or p.get("retentionPolicy")
            or u.get("messageExpiry") or u.get("retentionPolicy")
        ),
    ),
    (
        "vpim_networking",
        "VPIM networking (inter-system VM messaging)",
        lambda p, u: bool(
            p.get("vpimEnabled") or u.get("vpimEnabled")
        ),
    ),
    (
        "dispatch_messaging",
        "Dispatch messaging (round-robin VM to group)",
        lambda p, u: bool(
            p.get("dispatchMessaging") or u.get("dispatchMessaging")
        ),
    ),
    (
        "secure_private_messages",
        "Secure/private messages (encryption flag)",
        lambda p, u: bool(
            p.get("secureMessaging") or p.get("privateMessages")
            or u.get("secureMessaging") or u.get("privateMessages")
        ),
    ),
    (
        "live_record",
        "Live Record (record active call to voicemail inbox)",
        lambda p, u: bool(
            p.get("liveRecord") or u.get("liveRecord")
        ),
    ),
    (
        "pager_sms_notification",
        "Pager/SMS notification (no Webex equivalent)",
        lambda p, u: bool(
            p.get("pagerNotification") or p.get("smsNotification")
            or u.get("pagerNotification") or u.get("smsNotification")
        ),
    ),
    (
        "fax_internal_storage",
        "Fax with internal storage (fax requires external storage in Webex)",
        lambda p, u: (
            (p.get("faxEnabled") or u.get("faxEnabled"))
            and (p.get("storageType") or u.get("storageType", "INTERNAL")) != "EXTERNAL"
        ),
    ),
]


class VoicemailMapper(Mapper):
    """Maps CUCM Unity Connection voicemail profiles to Webex per-person VM settings.

    Joins two data sources per user:
    1. voicemail_profile (shared config via cross-ref #26, #27)
    2. unity_vm:{userid} (per-user settings from Unity Connection)

    (from 03b-transform-mappers.md §9)
    """

    name = "voicemail_mapper"
    depends_on = ["user_mapper"]

    def map(self, store: MigrationStore) -> MapperResult:
        """Read CUCM users with voicemail profiles and produce VM settings."""
        result = MapperResult()

        for user_data in store.get_objects("user"):
            user_id = user_data["canonical_id"]

            # --- Resolve voicemail profile via cross-ref (#26) ---
            vm_profile_refs = store.find_cross_refs(
                user_id, "user_has_voicemail_profile"
            )
            if not vm_profile_refs:
                # User has no voicemail profile — skip
                continue

            # --- Load shared profile settings via cross-ref (#27) ---
            profile_id = vm_profile_refs[0]
            profile_data = store.get_object(profile_id)
            profile_state = (profile_data or {}).get("pre_migration_state") or {}

            # Resolve detailed settings via voicemail_profile_settings cross-ref
            settings_refs = store.find_cross_refs(
                profile_id, "voicemail_profile_settings"
            )
            profile_settings: dict[str, Any] = {}
            if settings_refs:
                settings_data = store.get_object(settings_refs[0])
                if settings_data:
                    profile_settings = (
                        settings_data.get("pre_migration_state") or {}
                    )

            # Merge profile_state into profile_settings (profile_state overrides)
            merged_profile = {**profile_settings, **profile_state}

            # --- Load per-user Unity VM settings ---
            # (from Phase 04 corrections: unity_vm:{userid} objects)
            # Try top-level cucm_userid first (CanonicalUser after UserMapper),
            # fall back to pre_migration_state (raw MigrationObject before UserMapper)
            user_cucm_id = user_data.get("cucm_userid") or (
                user_data.get("pre_migration_state") or {}
            ).get("cucm_userid")
            unity_vm_state: dict[str, Any] = {}
            if user_cucm_id:
                unity_vm_data = store.get_object(f"unity_vm:{user_cucm_id}")
                if unity_vm_data:
                    unity_vm_state = (
                        unity_vm_data.get("pre_migration_state") or {}
                    )

            # Also try the canonical_id-based key
            if not unity_vm_state:
                user_name = user_id.split(":", 1)[-1] if ":" in user_id else user_id
                unity_vm_data = store.get_object(f"unity_vm:{user_name}")
                if unity_vm_data:
                    unity_vm_state = (
                        unity_vm_data.get("pre_migration_state") or {}
                    )

            # --- Build Webex voicemail settings ---
            vm_profile = self._build_voicemail_profile(
                store, user_id, user_data, merged_profile, unity_vm_state
            )
            store.upsert_object(vm_profile)
            result.objects_created += 1

            # --- Gap analysis: check all 13 rows ---
            # (from 03b-transform-mappers.md §11: Voicemail Gap Analysis)
            gaps = self._detect_gaps(merged_profile, unity_vm_state)
            if gaps:
                gap_descriptions = [desc for _, desc in gaps]
                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.VOICEMAIL_INCOMPATIBLE,
                    severity="MEDIUM",
                    summary=(
                        f"User '{user_id.split(':', 1)[-1]}' uses "
                        f"{len(gaps)} Unity Connection feature(s) without "
                        f"Webex equivalent: {', '.join(k for k, _ in gaps)}"
                    ),
                    context={
                        "user_id": user_id,
                        "gaps": [
                            {"feature": key, "description": desc}
                            for key, desc in gaps
                        ],
                        "gap_count": len(gaps),
                    },
                    options=[
                        accept_option(
                            f"Accept loss of {len(gaps)} feature(s) — "
                            f"document what's lost"
                        ),
                        skip_option(
                            "Skip voicemail migration — configure manually"
                        ),
                        manual_option(
                            "Flag for post-migration manual configuration"
                        ),
                    ],
                    affected_objects=[user_id],
                )
                store.save_decision(decision_to_store_dict(decision))
                result.decisions.append(decision)

            # --- MISSING_DATA for custom greetings ---
            has_custom_greeting = (
                merged_profile.get("customBusyGreeting")
                or merged_profile.get("customNoAnswerGreeting")
                or unity_vm_state.get("customBusyGreeting")
                or unity_vm_state.get("customNoAnswerGreeting")
            )
            if has_custom_greeting:
                decision = self._create_decision(
                    store=store,
                    decision_type=DecisionType.MISSING_DATA,
                    severity="MEDIUM",
                    summary=(
                        f"Custom greeting audio for user "
                        f"'{user_id.split(':', 1)[-1]}' can't be extracted "
                        f"from Unity Connection"
                    ),
                    context={
                        "user_id": user_id,
                        "reason": "custom_greeting_not_extractable",
                    },
                    options=[
                        accept_option("Use DEFAULT greetings"),
                        manual_option(
                            "Admin provides audio files manually post-migration"
                        ),
                    ],
                    affected_objects=[user_id],
                )
                store.save_decision(decision_to_store_dict(decision))
                result.decisions.append(decision)

        return result

    def _build_voicemail_profile(
        self,
        store: MigrationStore,
        user_id: str,
        user_data: dict[str, Any],
        profile_settings: dict[str, Any],
        unity_vm_state: dict[str, Any],
    ) -> CanonicalVoicemailProfile:
        """Build a CanonicalVoicemailProfile from profile + per-user settings.

        (from 03b-transform-mappers.md §9: field mapping table)
        """
        # --- send_all_calls ---
        # Check device line appearances for call_forward_all to VM
        # (from Phase 04 corrections: call forwarding on line appearances)
        send_all_enabled = bool(
            profile_settings.get("callForwardAll")
            or unity_vm_state.get("callForwardAll")
        )
        send_all_calls = {"enabled": send_all_enabled}

        # --- send_busy_calls ---
        send_busy_enabled = bool(
            profile_settings.get("callForwardBusy")
            or unity_vm_state.get("callForwardBusy")
        )
        busy_greeting = (
            "CUSTOM"
            if (
                profile_settings.get("customBusyGreeting")
                or unity_vm_state.get("customBusyGreeting")
            )
            else "DEFAULT"
        )
        send_busy_calls = {
            "enabled": send_busy_enabled,
            "greeting": busy_greeting,
        }

        # --- send_unanswered_calls ---
        # Preserve explicit opt-out from CUCM; default to True (Webex default)
        cfna_setting = (
            profile_settings.get("callForwardNoAnswer")
            or unity_vm_state.get("callForwardNoAnswer")
        )
        send_unanswered_enabled = cfna_setting if cfna_setting is not None else True
        unanswered_greeting = (
            "CUSTOM"
            if (
                profile_settings.get("customNoAnswerGreeting")
                or unity_vm_state.get("customNoAnswerGreeting")
            )
            else "DEFAULT"
        )

        # --- CFNA timeout -> numberOfRings ---
        # (from 03b-transform-mappers.md §9: "CUCM timeout in seconds ÷ 6")
        cfna_timeout = (
            unity_vm_state.get("cfnaTimeout")
            or profile_settings.get("cfnaTimeout")
        )
        number_of_rings = _DEFAULT_NUMBER_OF_RINGS
        if cfna_timeout is not None:
            try:
                computed_rings = max(1, int(cfna_timeout) // 6)
                number_of_rings = min(computed_rings, _MAX_NUMBER_OF_RINGS)
            except (ValueError, TypeError):
                number_of_rings = _DEFAULT_NUMBER_OF_RINGS

        send_unanswered_calls = {
            "enabled": send_unanswered_enabled,
            "greeting": unanswered_greeting,
            "numberOfRings": number_of_rings,
        }

        # --- notifications ---
        notification_enabled = bool(
            profile_settings.get("notificationEnabled")
            or unity_vm_state.get("notificationEnabled")
        )
        notification_dest = (
            unity_vm_state.get("notificationEmail")
            or profile_settings.get("notificationEmail")
        )
        notifications = {
            "enabled": notification_enabled,
        }
        if notification_dest:
            notifications["destination"] = notification_dest

        # --- email_copy_of_message ---
        email_copy_enabled = bool(
            profile_settings.get("emailCopyEnabled")
            or unity_vm_state.get("emailCopyEnabled")
        )
        email_copy_address = (
            unity_vm_state.get("emailCopyAddress")
            or profile_settings.get("emailCopyAddress")
        )
        email_copy = {"enabled": email_copy_enabled}
        if email_copy_address:
            email_copy["emailId"] = email_copy_address

        # --- message_storage ---
        storage_type = (
            unity_vm_state.get("storageType")
            or profile_settings.get("storageType")
            or "INTERNAL"
        )
        mwi_enabled = unity_vm_state.get(
            "mwiEnabled", profile_settings.get("mwiEnabled", True)
        )
        message_storage: dict[str, Any] = {
            "storageType": storage_type,
            "mwiEnabled": mwi_enabled,
        }
        if storage_type == "EXTERNAL":
            external_email = (
                unity_vm_state.get("externalEmail")
                or profile_settings.get("externalEmail")
            )
            if external_email:
                message_storage["externalEmail"] = external_email
            else:
                # Fall back to INTERNAL if no external email
                # (from 03b-transform-mappers.md §9: edge case)
                message_storage["storageType"] = "INTERNAL"

        # --- fax_message ---
        fax_enabled = bool(
            profile_settings.get("faxEnabled")
            or unity_vm_state.get("faxEnabled")
        )
        fax_message: dict[str, Any] = {"enabled": fax_enabled}
        if fax_enabled:
            fax_phone = (
                unity_vm_state.get("faxPhoneNumber")
                or profile_settings.get("faxPhoneNumber")
            )
            if fax_phone:
                fax_message["phoneNumber"] = fax_phone
            fax_ext = (
                unity_vm_state.get("faxExtension")
                or profile_settings.get("faxExtension")
            )
            if fax_ext:
                fax_message["extension"] = fax_ext

        # --- transfer_to_number ---
        transfer_enabled = bool(
            profile_settings.get("transferToZero")
            or unity_vm_state.get("transferToZero")
        )
        transfer_dest = (
            unity_vm_state.get("transferToZeroDestination")
            or profile_settings.get("transferToZeroDestination")
        )
        transfer_to_number: dict[str, Any] = {"enabled": transfer_enabled}
        if transfer_dest:
            transfer_to_number["destination"] = transfer_dest

        # --- Profile name ---
        cucm_profile_name = profile_settings.get("voicemail_profile_name")

        return CanonicalVoicemailProfile(
            canonical_id=f"voicemail_profile:{hash_id(user_id)}",
            provenance=extract_provenance(user_data),
            status=MigrationStatus.ANALYZED,
            enabled=True,
            send_all_calls=send_all_calls,
            send_busy_calls=send_busy_calls,
            send_unanswered_calls=send_unanswered_calls,
            notifications=notifications,
            email_copy_of_message=email_copy,
            message_storage=message_storage,
            fax_message=fax_message,
            transfer_to_number=transfer_to_number,
            cucm_voicemail_profile_name=cucm_profile_name,
            user_canonical_id=user_id,
        )

    def _detect_gaps(
        self,
        profile_settings: dict[str, Any],
        unity_vm_state: dict[str, Any],
    ) -> list[tuple[str, str]]:
        """Scan for Unity Connection features without Webex equivalents.

        Returns list of (gap_key, description) for each detected gap.

        (from 03b-transform-mappers.md §11: Voicemail Gap Analysis table)
        """
        gaps: list[tuple[str, str]] = []
        for key, description, check_fn in _VM_GAP_CHECKS:
            try:
                if check_fn(profile_settings, unity_vm_state):
                    gaps.append((key, description))
            except (KeyError, TypeError, AttributeError):
                # Gracefully handle missing keys in check functions
                continue
        return gaps


