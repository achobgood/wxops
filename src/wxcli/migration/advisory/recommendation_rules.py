"""Per-decision recommendation rules.

Each function signature: (context: dict, options: list) -> tuple[str, str] | None
Returns (option_id, reasoning) or None if no recommendation can be made.

Reference: migration-advisory-design.md §5 (spec section 5).
"""
from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Implemented rules — 6 simple types
# ---------------------------------------------------------------------------

_PROFESSIONAL_FEATURES = {
    "callForwarding", "callerId", "monitoring", "intercept",
    "callWaiting", "callRecording", "bargeIn", "pushToTalk",
}

_BASIC_FEATURES = {"musicOnHold", "doNotDisturb"}


def recommend_device_firmware_convertible(
    context: dict[str, Any], options: list
) -> tuple[str, str] | None:
    """Spec §5.3: Convertible device — always recommend convert."""
    model = context.get("cucm_model", "unknown")
    reasoning = f"Device model {model} supports Webex firmware conversion. Convert to native MPP."
    if context.get("has_srst"):
        reasoning += (
            " Note: Survivable Gateway (SRST) is configured. "
            "Verify fallback behavior after conversion — Webex devices use Webex Edge for survivability."
        )
    return ("convert", reasoning)


def recommend_missing_data(
    context: dict[str, Any], options: list
) -> tuple[str, str] | None:
    """Spec §5.15: Missing data decisions.

    CRITICAL: Do not recommend "skip" for objects that have downstream dependents.
    Skipping a location/trunk/user cascades to block all their devices/routes/features.
    Return None (no recommendation) to force the LLM to ask the user.
    """
    dependent_count = context.get("dependent_count", 0)
    missing_fields = context.get("missing_fields", [])
    fields_str = ", ".join(missing_fields) if isinstance(missing_fields, list) else ""
    object_type = context.get("object_type", "")

    # Objects with dependents should NOT be auto-skipped — force human review
    if dependent_count > 0:
        return None

    # Locations and trunks are infrastructure — always force review, never auto-skip
    if object_type in ("location", "trunk", "route_group"):
        return None

    # Executive/assistant broken pair — force review unless permanently excluded
    if context.get("missing_reason") == "executive_assistant_broken_pair":
        if context.get("permanently_excluded"):
            missing_side = context.get("missing_side", "user")
            return (
                "skip",
                f"The missing {missing_side} is permanently excluded from migration. "
                f"Executive/assistant pairing will need manual Webex configuration.",
            )
        return None  # Force human review — missing user might be added later

    # Leaf objects with no dependents can be safely skipped
    if fields_str:
        return (
            "skip",
            f"Missing required data: {fields_str}. Cannot migrate without this data.",
        )
    return (
        "skip",
        "Missing required data. Cannot migrate without the required information.",
    )


def recommend_number_conflict(
    context: dict[str, Any], options: list
) -> tuple[str, str] | None:
    """Spec §5.16: Number already assigned in Webex."""
    if context.get("same_owner"):
        return ("auto_resolve", "Same user owns this number in both systems. No conflict.")
    existing_owner = context.get("existing_owner", "unknown")
    cucm_owner = context.get("cucm_owner", "unknown")
    return (
        "keep_existing",
        f"Number is already assigned to {existing_owner} in Webex. "
        f"The CUCM owner ({cucm_owner}) will need a different number or "
        "the existing assignment must be removed first.",
    )


def recommend_duplicate_user(
    context: dict[str, Any], options: list
) -> tuple[str, str] | None:
    """Spec §5.10: Duplicate user entries."""
    if context.get("email_match"):
        email = context.get("email", "unknown")
        return ("merge", f"Both entries share email {email}. Merge into one Webex user.")
    if context.get("userid_match"):
        return (
            "merge",
            "Same CUCM userid. Merge; use the entry with the email address.",
        )
    return ("keep_both", "Same name but different emails. Likely different people.")


def recommend_workspace_license_tier(
    context: dict[str, Any], options: list
) -> tuple[str, str] | None:
    """Spec §5.12: Workspace license tier recommendation."""
    features_detected = context.get("features_detected", [])
    professional_found = [f for f in features_detected if f in _PROFESSIONAL_FEATURES]
    if professional_found:
        features_str = ", ".join(professional_found)
        return (
            "professional",
            f"Features detected: {features_str}. These require Professional workspace license.",
        )
    return (
        "basic",
        "Only basic features detected. Webex Calling Basic license is sufficient.",
    )


def recommend_hotdesk_dn_conflict(
    context: dict[str, Any], options: list
) -> tuple[str, str] | None:
    """Spec §5.14: Hotdesk DN conflict — always keep primary."""
    return (
        "keep_primary",
        "Keep the primary DN and configure hoteling for the secondary. "
        "Webex hoteling allows any user to log into the device temporarily.",
    )


# ---------------------------------------------------------------------------
# Implemented rules — complex types
# ---------------------------------------------------------------------------

def recommend_feature_approximation(
    context: dict[str, Any], options: list
) -> tuple[str, str] | None:
    """Spec §5.1: Feature approximation — CTI RP or Line Group → CQ/HG.

    Also handles selective call handling decisions tagged with
    `selective_call_handling_pattern` in context (spec
    docs/superpowers/specs/2026-04-10-selective-call-forwarding.md §4c).
    """
    # Selective call handling — recommend accept with feature-specific reasoning.
    sch_pattern = context.get("selective_call_handling_pattern")
    if sch_pattern:
        feature = context.get("recommended_webex_feature", "selective call handling")
        confidence = (context.get("confidence") or "").upper()
        if sch_pattern == "naming_convention" or confidence == "LOW":
            note = (
                " Note: this is a weak signal based on partition naming only — "
                "verify the CUCM behaviour before configuring. Priority Alert "
                "specifically requires user-only OAuth and cannot be configured "
                "via admin token."
                if feature.lower() == "priority alert"
                else " Note: this is a weak signal based on partition naming "
                "only — verify the CUCM behaviour before configuring."
            )
            return (
                "accept",
                f"CUCM CSS/partition pattern suggests caller-specific routing. "
                f"Configure Webex {feature} post-migration to preserve this "
                f"behaviour.{note}",
            )
        return (
            "accept",
            f"CUCM CSS/partition pattern suggests caller-specific routing. "
            f"Configure Webex {feature} post-migration to preserve this "
            f"behaviour. The pipeline cannot auto-create the rule because the "
            f"phone-number criteria require operator review.",
        )

    # EM profile → hot desking: always recommend accept (no alternative exists)
    if context.get("classification") == "EXTENSION_MOBILITY":
        line_count = context.get("line_count", 0)
        sd_count = context.get("speed_dial_count", 0)
        blf_count = context.get("blf_count", 0)
        has_feature_loss = line_count > 1 or sd_count > 0 or blf_count > 0
        if has_feature_loss:
            return (
                "accept",
                f"EM profile has {line_count} line(s) but Webex hot desking uses "
                f"primary line only. Speed dials and BLF entries will not carry to "
                f"hot desk sessions. Accept — no alternative to hot desking exists.",
            )
        return (
            "accept",
            "Simple EM profile — maps cleanly to Webex hot desking with primary line.",
        )

    classification = context.get("classification")
    if classification == "AUTO_ATTENDANT":
        if context.get("complex_script"):
            return None
        return (
            "accept",
            "Standard CTI Route Point with no complex scripting. "
            "Maps directly to Webex Auto Attendant.",
        )

    has_queue = context.get("has_queue_features", False)
    agent_count = context.get("agent_count", 0)
    algorithm = context.get("algorithm")  # legacy; still read below for small-group check
    policy = context.get("policy")        # preferred; Webex form from mapper

    # Agent limit check — routing-type-aware (kb-webex-limits.md DT-LIMITS-001).
    # SIMULTANEOUS caps at 50; REGULAR/CIRCULAR/UNIFORM/WEIGHTED cap at 1000.
    # Prefer `policy` (Webex form set by FeatureMapper) over CUCM `algorithm` —
    # the mapping is already done.
    target_routing = context.get("target_routing_type")  # explicit override (future scaffold)
    if target_routing is not None:
        is_simultaneous = target_routing.upper() == "SIMULTANEOUS"
    elif policy is not None:
        is_simultaneous = policy == "SIMULTANEOUS"
    else:
        # Fallback: legacy contexts without `policy`. Only "Broadcast" maps to
        # simultaneous; "Top Down" was incorrectly treated as simultaneous in the
        # pre-fix code (it actually maps to REGULAR).
        is_simultaneous = algorithm in ("Broadcast", None)

    # Cap from context if mapper provided it (post-fix); otherwise fall back
    # to defaults for legacy/hand-constructed contexts. The mapper writes
    # `agent_limit` with the policy-correct value from `_AGENT_LIMITS` —
    # SIMULTANEOUS=50, WEIGHTED=100, REGULAR/CIRCULAR/UNIFORM=1000. Reading the
    # context value avoids the prior bug where WEIGHTED hunt pilots exceeded
    # their 100-cap but the recommender's hard-coded 1000 missed them.
    context_limit = context.get("agent_limit")
    simultaneous_cap = 50      # legacy default
    priority_cap = 1000        # legacy default
    if context_limit is not None:
        if is_simultaneous:
            simultaneous_cap = context_limit
        else:
            priority_cap = context_limit

    if is_simultaneous and agent_count > simultaneous_cap:
        routing_note = ""
        # Only mark as "assumed" when we actually fell through the legacy
        # algorithm fallback — i.e., neither `target_routing_type` nor `policy`
        # was set. With `policy` populated by FeatureMapper, the SIMULTANEOUS
        # detection is explicit, not assumed.
        if (
            target_routing is None
            and policy is None
            and algorithm in ("undefined", None)
        ):
            routing_note = " (assumed simultaneous — no algorithm detected in CUCM data)"
        return (
            "split",
            f"Agent count ({agent_count}) exceeds Simultaneous routing cap of "
            f"{simultaneous_cap}{routing_note}. Split into multiple queues with "
            f"overflow chain, or switch to priority-based routing (REGULAR/"
            f"CIRCULAR/UNIFORM support up to 1000).",
        )
    if not is_simultaneous and agent_count > priority_cap:
        policy_label = policy or "priority-based"
        return (
            "split",
            f"Agent count ({agent_count}) exceeds Call Queue limit of "
            f"{priority_cap} for {policy_label} routing. Split into multiple "
            f"queues with overflow chain.",
        )

    if has_queue:
        return (
            "call_queue",
            f"Queue indicators detected. Call Queue preserves queuing, "
            f"overflow routing, agent-level reporting, and wait-time management. "
            f"Hunt Group loses all of these.",
        )

    if agent_count > 8:
        return (
            "call_queue",
            f"Large agent group ({agent_count} agents). Even without explicit "
            f"queue features, Call Queue provides reporting, overflow management, "
            f"and wait-time handling at this scale.",
        )

    if agent_count <= 4 and algorithm in ("Top Down", "undefined", None):
        return (
            "hunt_group",
            f"Small group ({agent_count} agents), no queue features, "
            f"top-down ring order. This is a ring-group pattern — "
            f"Hunt Group maps directly.",
        )

    # 5-8 agents, no queue, non-top-down → genuinely ambiguous
    return None


_DEVICE_REPLACEMENT_MAP: dict[str, tuple[str, str]] = {
    "7811": ("9841", "Same desk form factor, single-screen. 9841 is Webex-native (RoomOS). Note: RoomOS uses device configuration templates, not telephony device settings — different day-2 config model than MPP."),
    "7821": ("9841", "2-line phone → 9841 supports more lines. Same price tier. 9841 uses RoomOS firmware (device configuration templates for day-2 config)."),
    "7832": ("conference room device", "Conference phone. Consider Webex Room device (RoomOS) for both calling and meeting capability."),
    "7905": ("8845 or 9851", "Legacy SCCP/SIP phone with no Webex firmware path. 8845 uses MPP firmware; 9851 uses RoomOS (larger screen). Different day-2 config models."),
    "7906": ("8845 or 9851", "Legacy SCCP/SIP phone with no Webex firmware path. 8845 uses MPP firmware; 9851 uses RoomOS (larger screen). Different day-2 config models."),
    "7911": ("8845 or 9851", "Legacy SCCP/SIP phone with no Webex firmware path. 8845 uses MPP firmware; 9851 uses RoomOS (larger screen). Different day-2 config models."),
    "7912": ("8845 or 9851", "Legacy SCCP/SIP phone with no Webex firmware path. 8845 uses MPP firmware; 9851 uses RoomOS (larger screen). Different day-2 config models."),
    "7940": ("8845 or 9851", "Legacy SCCP/SIP phone with no Webex firmware path. 8845 uses MPP firmware; 9851 uses RoomOS (larger screen). Different day-2 config models."),
    "7941": ("8845 or 9851", "Legacy SCCP/SIP phone with no Webex firmware path. 8845 uses MPP firmware; 9851 uses RoomOS (larger screen). Different day-2 config models."),
    "7942": ("8845 or 9851", "Legacy SCCP/SIP phone with no Webex firmware path. 8845 uses MPP firmware; 9851 uses RoomOS (larger screen). Different day-2 config models."),
    "7945": ("8845 or 9851", "Legacy SCCP/SIP phone with no Webex firmware path. 8845 uses MPP firmware; 9851 uses RoomOS (larger screen). Different day-2 config models."),
    "7960": ("8845 or 9851", "Legacy SCCP/SIP phone with no Webex firmware path. 8845 uses MPP firmware; 9851 uses RoomOS (larger screen). Different day-2 config models."),
    "7961": ("8845 or 9851", "Legacy SCCP/SIP phone with no Webex firmware path. 8845 uses MPP firmware; 9851 uses RoomOS (larger screen). Different day-2 config models."),
    "7962": ("8845 or 9851", "Legacy SCCP/SIP phone with no Webex firmware path. 8845 uses MPP firmware; 9851 uses RoomOS (larger screen). Different day-2 config models."),
    "7965": ("8845 or 9851", "Legacy SCCP/SIP phone with no Webex firmware path. 8845 uses MPP firmware; 9851 uses RoomOS (larger screen). Different day-2 config models."),
    "7970": ("8845 or 9851", "Legacy SCCP/SIP phone with no Webex firmware path. 8845 uses MPP firmware; 9851 uses RoomOS (larger screen). Different day-2 config models."),
    "7971": ("8845 or 9851", "Legacy SCCP/SIP phone with no Webex firmware path. 8845 uses MPP firmware; 9851 uses RoomOS (larger screen). Different day-2 config models."),
    "7975": ("8845 or 9851", "Legacy SCCP/SIP phone with no Webex firmware path. 8845 uses MPP firmware; 9851 uses RoomOS (larger screen). Different day-2 config models."),
    "6901": ("8841 or 9841", "Cisco 69xx series. No Webex firmware. 8841 uses MPP firmware (same line count); 9841 uses RoomOS."),
    "6911": ("8841 or 9841", "Cisco 69xx series. No Webex firmware. 8841 uses MPP firmware (same line count); 9841 uses RoomOS."),
    "6921": ("8841 or 9841", "Cisco 69xx series. No Webex firmware. 8841 uses MPP firmware (same line count); 9841 uses RoomOS."),
    "6941": ("8841 or 9841", "Cisco 69xx series. No Webex firmware. 8841 uses MPP firmware (same line count); 9841 uses RoomOS."),
    "6945": ("8841 or 9841", "Cisco 69xx series. No Webex firmware. 8841 uses MPP firmware (same line count); 9841 uses RoomOS."),
    "6961": ("8841 or 9841", "Cisco 69xx series. No Webex firmware. 8841 uses MPP firmware (same line count); 9841 uses RoomOS."),
    "ATA 190": ("ATA 192", "Analog adapter. ATA 192 supports Webex Calling."),
    "ATA 191": ("ATA 192", "Analog adapter. ATA 192 supports Webex Calling."),
    "ATA190": ("ATA 192", "Analog adapter. ATA 192 supports Webex Calling."),
    "ATA191": ("ATA 192", "Analog adapter. ATA 192 supports Webex Calling."),
}


def recommend_device_incompatible(
    context: dict[str, Any], options: list
) -> tuple[str, str] | None:
    """Spec §5.2: Incompatible device — look up replacement recommendation."""
    model = context.get("cucm_model", "")
    entry = _DEVICE_REPLACEMENT_MAP.get(model)
    if entry is None:
        return None
    replacement, base_reason = entry
    reasoning = f"Device model {model} is not supported in Webex Calling. {base_reason}"
    if context.get("button_count") or context.get("has_sidecar"):
        reasoning += (
            " Note: This device has expanded line key capacity. "
            "Verify the replacement model supports equivalent line keys or sidecar."
        )
    return ("replace", f"Replace with {replacement}. {reasoning}")


def recommend_dn_ambiguous(
    context: dict[str, Any], options: list
) -> tuple[str, str] | None:
    """Spec §5.4: Ambiguous DN ownership."""
    owner_count = context.get("owner_count", 0)
    if owner_count == 1:
        owner_name = context.get("owner_name", "unknown")
        return ("assign", f"DN has one clear owner ({owner_name}). Assign to this user.")
    primary_owner = context.get("primary_owner")
    if primary_owner:
        return (
            "assign",
            f"DN is shared but {primary_owner} has it as line 1. "
            "Assign to primary owner; other appearances become shared line or virtual extension.",
        )
    return None


def recommend_extension_conflict(
    context: dict[str, Any], options: list
) -> tuple[str, str] | None:
    """Spec §5.5: Extension conflict between two owners."""
    a_count = context.get("ext_a_appearances", 0)
    b_count = context.get("ext_b_appearances", 0)
    if a_count > b_count:
        ext_a = context.get("ext_a", "unknown")
        owner_a = context.get("owner_a", "unknown")
        return (
            "keep_a",
            f"Extension {ext_a} is used on {a_count} devices for {owner_a}. "
            "Reassign the conflicting extension.",
        )
    if b_count > a_count:
        ext_b = context.get("ext_b", "unknown")
        owner_b = context.get("owner_b", "unknown")
        return (
            "keep_b",
            f"Extension {ext_b} is used on {b_count} devices for {owner_b}. "
            "Reassign the conflicting extension.",
        )
    return None


_MONITORING_KEYWORDS = {"BLF", "Monitor", "Busy Lamp", "Speed", "DSS"}


def recommend_shared_line_complex(
    context: dict[str, Any], options: list
) -> tuple[str, str] | None:
    """Spec §5.6: Shared line with complex appearance patterns."""
    appearance_count = context.get("appearance_count", 0)
    secondary_labels = context.get("secondary_labels", [])

    # Check if ALL secondary labels contain a monitoring keyword
    if secondary_labels:
        all_monitoring = all(
            any(kw.lower() in label.lower() for kw in _MONITORING_KEYWORDS)
            for label in secondary_labels
        )
        if all_monitoring:
            return (
                "virtual_extension",
                f"All {len(secondary_labels)} secondary appearances use monitoring "
                f"labels ({', '.join(secondary_labels)}). Virtual extension with BLF "
                f"monitoring is the correct Webex equivalent.",
            )

    # Low count without all-monitoring labels → shared line
    if appearance_count <= 10:
        return (
            "shared_line",
            f"Webex shared line supports up to 35 appearances. "
            f"{appearance_count} appearances fits within limits.",
        )

    # High count with mixed usage → ambiguous
    return None


def recommend_css_routing_mismatch(
    context: dict[str, Any], options: list
) -> tuple[str, str] | None:
    """Spec §5.7: CSS routing mismatch — partition ordering, scope, or conflict."""
    mismatch_type = context.get("mismatch_type")
    if mismatch_type == "partition_ordering":
        pattern = context.get("pattern", "unknown")
        return (
            "manual",
            f"This CSS depends on partition ordering to resolve pattern '{pattern}'. "
            f"Webex uses longest-match routing — partition ordering has no equivalent. "
            f"Review manually.",
        )
    if mismatch_type == "scope_difference":
        return (
            "use_union",
            "Union preserves all routing for all users at this location.",
        )
    if mismatch_type == "pattern_conflict":
        pattern = context.get("pattern", "unknown")
        route_a = context.get("route_a", "unknown")
        route_b = context.get("route_b", "unknown")
        dp_a = context.get("dp_a", "unknown")
        dp_b = context.get("dp_b", "unknown")
        return (
            "manual",
            f"Pattern '{pattern}' routes to {route_a} in {dp_a} and "
            f"{route_b} in {dp_b}. The correct route depends on business intent.",
        )
    return None


_INTERNATIONAL_PREFIXES = ("011", "00", "+2", "+3", "+4", "+5", "+6", "+7", "+8", "+9")
_PREMIUM_PREFIXES = ("1900", "900", "976")


def recommend_calling_permission_mismatch(
    context: dict[str, Any], options: list
) -> tuple[str, str] | None:
    """Spec §5.8: Calling permission mismatch — map block pattern to Webex call type."""
    block_pattern = context.get("block_pattern", "")

    for prefix in _INTERNATIONAL_PREFIXES:
        if block_pattern.startswith(prefix):
            return (
                "INTERNATIONAL_CALL",
                f"Block pattern '{block_pattern}' matches international dialing prefix "
                f"'{prefix}'. Map to Webex outgoing call permission: INTERNATIONAL_CALL.",
            )

    for prefix in _PREMIUM_PREFIXES:
        if block_pattern.startswith(prefix):
            return (
                "PREMIUM_SERVICES_NUMBER_ONE",
                f"Block pattern '{block_pattern}' matches premium/toll prefix "
                f"'{prefix}'. Map to Webex outgoing call permission: PREMIUM_SERVICES_NUMBER_ONE.",
            )

    return None


def recommend_location_ambiguous(
    context: dict[str, Any], options: list
) -> tuple[str, str] | None:
    """Spec §5.9: Ambiguous location — consolidate if tz + region + site_code all match.

    CRITICAL: If the location has no address and devices depend on it,
    always recommend provide_address. Never recommend skip when devices
    would be blocked — skip is not even offered as an option in that case.
    """
    dependent_count = context.get("dependent_device_count", 0)
    has_address = context.get("has_address", False)

    # If no address and devices depend on this location, always recommend provide_address
    if not has_address and dependent_count > 0:
        return (
            "provide_address",
            f"Location has {dependent_count} devices in its pools but no street address. "
            f"Webex requires an address to create a location. Provide address1, city, state, "
            f"postal_code, and country to proceed. Without an address, all {dependent_count} "
            f"devices will be blocked from migration.",
        )

    timezone = context.get("timezone")
    region = context.get("region")
    site_code = context.get("site_code")
    same_timezone = context.get("same_timezone")
    same_region = context.get("same_region")

    # Explicit same_timezone=True but same_region=False → can't consolidate
    if same_timezone is True and same_region is False:
        return None

    if timezone and region and site_code:
        return (
            "consolidate",
            f"All partitions share timezone ({timezone}), region ({region}), and site code ({site_code}). "
            "Consolidate into a single Webex location.",
        )
    if timezone and region:
        return (
            "consolidate",
            f"Partitions share timezone ({timezone}) and region ({region}). "
            "Consolidate into a single Webex location.",
        )

    # No address info and no devices → genuinely ambiguous
    return None


def recommend_voicemail_incompatible(
    context: dict[str, Any], options: list
) -> tuple[str, str] | None:
    """Spec §5.11: Voicemail incompatible — map Unity settings to Webex voicemail."""
    cfna_timeout = context.get("cfna_timeout")
    unity_features = context.get("unity_features")

    if cfna_timeout is not None:
        rings = cfna_timeout // 6
        return (
            "webex_voicemail",
            f"CUCM CFNA timeout {cfna_timeout}s maps to {rings} rings in Webex voicemail.",
        )

    if unity_features:
        features_str = ", ".join(unity_features)
        return (
            "webex_voicemail",
            f"Unity VM settings include {features_str}. "
            f"Webex voicemail provides equivalent functionality.",
        )

    return (
        "webex_voicemail",
        "No Unity Connection data available. Recommend Webex voicemail with default settings (3 rings).",
    )


_CONFERENCE_MODELS = {
    "7832", "8832", "CP-7832", "CP-8832",
    "7832-CE", "8832-CE",
}

_DESK_PHONE_MODELS = {
    "6901", "6911", "6921", "6941", "6945", "6961",
    "7811", "7821", "7832",
    "7905", "7906", "7911", "7912", "7940", "7941", "7942", "7945",
    "7960", "7961", "7962", "7965", "7970", "7971", "7975",
    "8811", "8841", "8845", "8851", "8861", "8865",
    "9811", "9821", "9841", "9851", "9861", "9871",
}


def recommend_workspace_type_uncertain(
    context: dict[str, Any], options: list
) -> tuple[str, str] | None:
    """Spec §5.13: Uncertain workspace type — infer from device model and ownership."""
    model = context.get("cucm_model", "")
    if model in _CONFERENCE_MODELS:
        return (
            "conference_room",
            f"Conference phone model ({model}) suggests conference room workspace.",
        )
    has_owner = context.get("has_owner")
    if model in _DESK_PHONE_MODELS and has_owner is False:
        return (
            "common_area",
            f"Desk phone ({model}) with no assigned user. Common area workspace.",
        )
    return None


def recommend_forwarding_lossy(
    context: dict[str, Any], options: list,
) -> tuple[str, str] | None:
    """CUCM-only forwarding variants are rarely configured. Accept the loss."""
    return ("accept", "The 7 CUCM-only variants (busyInt, noAnswerInt, noCoverage, "
            "noCoverageInt, onFailure, notRegistered, notRegisteredInt) are rarely "
            "configured; CFA/CFB/CFNA covers >95% of real forwarding behavior.")


def recommend_snr_lossy(
    context: dict[str, Any], options: list,
) -> tuple[str, str] | None:
    """Timer controls rarely customized from defaults."""
    return ("accept", "Timer controls (answerTooSoon/answerTooLate) are rarely "
            "customized from defaults. Webex answerConfirmationEnabled provides "
            "equivalent 'don't connect too soon' behavior.")


def recommend_audio_asset_manual(
    context: dict[str, Any], options: list,
) -> tuple[str, str] | None:
    """Custom audio was intentional — always recommend manual migration."""
    source_name = (
        context.get("moh_source_name")
        or context.get("source_name")
        or context.get("name", "unknown")
    )

    if context.get("moh_source_name") or context.get("source_type") == "moh":
        return (
            "accept",
            f"Custom MoH source '{source_name}' should be downloaded from CUCM TFTP "
            "(/usr/local/cm/tftp/) and uploaded to Webex announcement repository. "
            "Set location MoH to CUSTOM after upload.",
        )

    usage = context.get("usage", "")
    if usage:
        return (
            "accept",
            f"Customer-facing {usage} audio '{source_name}' should be downloaded from "
            "CUCM and uploaded to Webex. Webex accepts WAV files up to 8 MB.",
        )

    return (
        "accept",
        f"Custom audio '{source_name}' should be downloaded from CUCM and uploaded "
        "to Webex announcement repository for brand consistency.",
    )


def recommend_button_unmappable(
    context: dict[str, Any], options: list,
) -> tuple[str, str] | None:
    """Spec §6.1: CUCM-specific button types have no Webex line key equivalent."""
    unmapped = context.get("unmapped_features", [])
    if unmapped:
        features_str = ", ".join(unmapped)
        return (
            "accept_loss",
            f"CUCM button types ({features_str}) have no Webex equivalent. "
            "These are CUCM-specific features (Service URL, Intercom, Privacy, etc.) "
            "that don't exist in Webex Calling. No action is possible.",
        )
    return (
        "accept_loss",
        "CUCM-specific phone button types have no Webex line key equivalent. "
        "These buttons will not be migrated. No action is possible.",
    )


def recommend_e911_ecbn_ambiguous(
    context: dict[str, Any], options: list
) -> tuple[str, str] | None:
    """Recommend the primary line's DID as ECBN when user has multiple DIDs.

    (from 2026-04-10-e911-ecbn-execution.md §6.4)
    """
    primary_did = context.get("primary_did")
    if not primary_did:
        return None
    option_id = f"did_{primary_did}"
    option_ids = {o.get("id") for o in options}
    if option_id not in option_ids:
        return None
    return (
        option_id,
        f"Primary line DID {primary_did} is the most common ECBN choice. "
        f"The PSAP will call back this number if the emergency call is disconnected.",
    )


def recommend_e911_location_mismatch(
    context: dict[str, Any], options: list
) -> tuple[str, str] | None:
    """Recommend the user's assigned location for ECBN on mismatch."""
    user_loc = context.get("user_location")
    if not user_loc:
        return None
    option_ids = {o.get("id") for o in options}
    if "use_user_location" not in option_ids:
        return None
    return (
        "use_user_location",
        f"The user's assigned location ({user_loc}) should determine PSAP routing "
        "when user and device locations differ. If the user's phone is consistently "
        "at a different physical site, update the user's assigned location first.",
    )


def recommend_workspace_settings_professional_required(
    context: dict[str, Any], options: list
) -> tuple[str, str] | None:
    """Workspace has settings that require Professional license but is on basic tier."""
    dropped = context.get("dropped_settings", [])
    if not dropped:
        return None
    settings_str = ", ".join(dropped)
    return (
        "accept_loss",
        f"Settings requiring Professional Workspace license ({settings_str}) will be "
        "lost with basic Workspace license. Most common-area phones don't need these — "
        "upgrade only if the phone actively uses call forwarding or voicemail.",
    )


# ---------------------------------------------------------------------------
# Dispatch table — ALL 19 DecisionType string values
# ---------------------------------------------------------------------------

RECOMMENDATION_DISPATCH: dict[str, Any] = {
    "EXTENSION_CONFLICT": recommend_extension_conflict,
    "DN_AMBIGUOUS": recommend_dn_ambiguous,
    "DEVICE_INCOMPATIBLE": recommend_device_incompatible,
    "DEVICE_FIRMWARE_CONVERTIBLE": recommend_device_firmware_convertible,
    "SHARED_LINE_COMPLEX": recommend_shared_line_complex,
    "CSS_ROUTING_MISMATCH": recommend_css_routing_mismatch,
    "CALLING_PERMISSION_MISMATCH": recommend_calling_permission_mismatch,
    "LOCATION_AMBIGUOUS": recommend_location_ambiguous,
    "DUPLICATE_USER": recommend_duplicate_user,
    "VOICEMAIL_INCOMPATIBLE": recommend_voicemail_incompatible,
    "WORKSPACE_LICENSE_TIER": recommend_workspace_license_tier,
    "WORKSPACE_TYPE_UNCERTAIN": recommend_workspace_type_uncertain,
    "HOTDESK_DN_CONFLICT": recommend_hotdesk_dn_conflict,
    "FEATURE_APPROXIMATION": recommend_feature_approximation,
    "MISSING_DATA": recommend_missing_data,
    "NUMBER_CONFLICT": recommend_number_conflict,
    "FORWARDING_LOSSY": recommend_forwarding_lossy,
    "SNR_LOSSY": recommend_snr_lossy,
    "AUDIO_ASSET_MANUAL": recommend_audio_asset_manual,
    "BUTTON_UNMAPPABLE": recommend_button_unmappable,
    "E911_ECBN_AMBIGUOUS": recommend_e911_ecbn_ambiguous,
    "E911_LOCATION_MISMATCH": recommend_e911_location_mismatch,
    "WORKSPACE_SETTINGS_PROFESSIONAL_REQUIRED": recommend_workspace_settings_professional_required,
}
