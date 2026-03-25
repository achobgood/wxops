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
# Stub rules — 10 remaining types (return None until implemented)
# ---------------------------------------------------------------------------

def recommend_feature_approximation(
    context: dict[str, Any], options: list
) -> tuple[str, str] | None:
    return None


def recommend_device_incompatible(
    context: dict[str, Any], options: list
) -> tuple[str, str] | None:
    return None


def recommend_dn_ambiguous(
    context: dict[str, Any], options: list
) -> tuple[str, str] | None:
    return None


def recommend_extension_conflict(
    context: dict[str, Any], options: list
) -> tuple[str, str] | None:
    return None


def recommend_shared_line_complex(
    context: dict[str, Any], options: list
) -> tuple[str, str] | None:
    return None


def recommend_css_routing_mismatch(
    context: dict[str, Any], options: list
) -> tuple[str, str] | None:
    return None


def recommend_calling_permission_mismatch(
    context: dict[str, Any], options: list
) -> tuple[str, str] | None:
    return None


def recommend_location_ambiguous(
    context: dict[str, Any], options: list
) -> tuple[str, str] | None:
    return None


def recommend_voicemail_incompatible(
    context: dict[str, Any], options: list
) -> tuple[str, str] | None:
    return None


def recommend_workspace_type_uncertain(
    context: dict[str, Any], options: list
) -> tuple[str, str] | None:
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
