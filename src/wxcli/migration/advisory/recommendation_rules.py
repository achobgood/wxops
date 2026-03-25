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
    """Spec §5.15: Missing data decisions."""
    if context.get("subtype") == "trunk_password":
        return (
            "generate",
            "Trunk authentication password not extractable from CUCM. "
            "A new password will be generated. Update the SBC/carrier configuration to match.",
        )
    missing_fields = context.get("missing_fields")
    if isinstance(missing_fields, list) and missing_fields:
        fields_str = ", ".join(missing_fields)
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
    """Spec §5.1: Feature approximation — CTI RP or Line Group → CQ/HG."""
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

    # Agent limit exceeded — recommend split
    if agent_count > 50:
        return (
            "split",
            f"Agent count ({agent_count}) exceeds Call Queue limit of 50 for "
            f"simultaneous distribution. Split into multiple queues with "
            f"overflow chain.",
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

    algorithm = context.get("algorithm")
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
    """Spec §5.9: Ambiguous location — consolidate if tz + region + site_code all match."""
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


# ---------------------------------------------------------------------------
# Dispatch table — ALL 16 DecisionType string values
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
}
