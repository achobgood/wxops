"""Translate DecisionType + context into plain-English explanations.

Each decision type has a template that produces:
- title: Short heading for the report (e.g., "Dallas office international dialing restriction")
- explanation: What we found and how Webex handles it differently
- reassurance: Why this is manageable, not a blocker

Tone: direct, jargon-free, never alarming. Frame problems as decisions, not blockers.
"""
from __future__ import annotations

from typing import Any


def _with_summary(summary: str, continuation: str) -> str:
    """Prefix with summary sentence if non-empty."""
    return f"{summary}. {continuation}" if summary else continuation


def _reassurance_for_severity(severity: str) -> str:
    """Return reassurance text appropriate for the severity level."""
    sev = severity.upper()
    if sev == "CRITICAL":
        return "This must be resolved before migration but the options are clear."
    if sev == "HIGH":
        return "This requires planning but has well-defined resolution options."
    if sev in ("LOW", "MEDIUM"):
        return "This is a configuration choice, not a limitation."
    raise ValueError(f"Unknown severity: {severity!r}")


def _explain_extension_conflict(
    summary: str, context: dict[str, Any], severity: str
) -> dict[str, str]:
    dn = context.get("dn") or context.get("extension", "")
    count = context.get("count", "")
    title = f"Extension conflict for {dn}" if dn else "Extension conflict detected"
    if dn and count:
        explanation = (
            f"Extension {dn} is assigned to {count} different users or devices. "
            "Webex Calling requires each extension to be unique within a location. "
            "During planning, you'll choose which user keeps the extension and what "
            "alternatives the others receive."
        )
    else:
        explanation = _with_summary(
            summary,
            "Webex Calling requires each extension to be unique within "
            "a location. During planning, you'll assign unique extensions where needed.",
        )
    return {"title": title, "explanation": explanation, "reassurance": _reassurance_for_severity(severity)}


def _explain_dn_ambiguous(
    summary: str, context: dict[str, Any], severity: str
) -> dict[str, str]:
    dn = context.get("dn", "")
    title = f"Ambiguous directory number {dn}" if dn else "Ambiguous directory number"
    if dn:
        explanation = (
            f"Directory number {dn} appears in multiple partitions with different "
            "routing behavior. In Webex Calling, numbers are scoped to locations rather "
            "than partitions. You'll choose how to consolidate during planning."
        )
    else:
        explanation = _with_summary(
            summary,
            "In Webex Calling, numbers are scoped to locations rather than "
            "partitions. You'll choose how to consolidate during planning.",
        )
    return {"title": title, "explanation": explanation, "reassurance": _reassurance_for_severity(severity)}


def _explain_device_incompatible(
    summary: str, context: dict[str, Any], severity: str
) -> dict[str, str]:
    model = context.get("model", "")
    count = context.get("count", "")
    recommended = context.get("recommended_model", "a supported Webex Calling model")
    title = f"Incompatible phone model: {model}" if model else "Incompatible phone model"
    if model and count:
        explanation = (
            f"You have {count} {model} phones that aren't compatible with Webex Calling. "
            f"These will need to be replaced with {recommended}."
        )
    elif model:
        explanation = (
            f"The {model} phone model is not compatible with Webex Calling. "
            f"These devices will need to be replaced with {recommended}."
        )
    else:
        explanation = _with_summary(
            summary,
            f"Incompatible phones will need to be replaced with "
            f"{recommended}.",
        )
    return {"title": title, "explanation": explanation, "reassurance": _reassurance_for_severity(severity)}


def _explain_device_firmware_convertible(
    summary: str, context: dict[str, Any], severity: str
) -> dict[str, str]:
    model = context.get("model", "")
    count = context.get("count", "")
    title = f"Firmware-convertible phone: {model}" if model else "Firmware-convertible phones detected"
    if model and count:
        explanation = (
            f"You have {count} {model} phones that can be converted to Webex Calling "
            "with a firmware upgrade. No hardware replacement is needed — these phones "
            "just need their firmware updated during the migration."
        )
    elif model:
        explanation = (
            f"The {model} phone can be converted to Webex Calling with a firmware "
            "upgrade. No hardware replacement is needed."
        )
    else:
        explanation = _with_summary(
            summary,
            "These phones can be converted with a firmware upgrade — "
            "no hardware replacement is needed.",
        )
    return {"title": title, "explanation": explanation, "reassurance": _reassurance_for_severity(severity)}


def _explain_shared_line_complex(
    summary: str, context: dict[str, Any], severity: str
) -> dict[str, str]:
    dn = context.get("dn", "")
    devices = context.get("devices", "")
    owners = context.get("owners", "")
    title = f"Complex shared line: {dn}" if dn else "Complex shared line arrangement"
    if dn and devices and owners:
        explanation = (
            f"Extension {dn} appears on {devices} devices with {owners} different "
            "owners. Webex handles this through Virtual Lines or Shared Lines — "
            "you'll choose the best approach during planning."
        )
    else:
        explanation = _with_summary(
            summary,
            "Webex handles shared lines through Virtual Lines or "
            "Shared Line Appearance — you'll choose the best approach during planning.",
        )
    return {"title": title, "explanation": explanation, "reassurance": _reassurance_for_severity(severity)}


def _explain_css_routing_mismatch(
    summary: str, context: dict[str, Any], severity: str
) -> dict[str, str]:
    css_name = context.get("css_name", "")
    partitions = context.get("partitions", [])
    title = f"Routing scope change: {css_name}" if css_name else "Routing scope change detected"
    if css_name:
        partition_detail = ""
        if partitions:
            partition_detail = f" It currently uses partitions {', '.join(partitions)}."
        explanation = (
            f"Your {css_name} calling search space restricts which numbers users "
            f"can dial.{partition_detail} Webex Calling uses flat org-wide routing "
            "instead. During planning, you'll choose how to map these restrictions."
        )
    else:
        explanation = _with_summary(
            summary,
            "Webex Calling uses flat org-wide routing instead of "
            "partition-based calling search spaces. During planning, you'll choose "
            "how to map these restrictions.",
        )
    return {"title": title, "explanation": explanation, "reassurance": _reassurance_for_severity(severity)}


def _explain_calling_permission_mismatch(
    summary: str, context: dict[str, Any], severity: str
) -> dict[str, str]:
    css_name = context.get("css_name", "")
    permission = context.get("permission", "")
    title = f"Calling permission change: {css_name}" if css_name else "Calling permission change"
    if css_name and permission:
        explanation = (
            f"The calling search space {css_name} enforces a {permission} restriction "
            "that maps to Webex Calling's outgoing calling permissions. The permission "
            "model differs, so you'll choose the closest match during planning."
        )
    else:
        explanation = _with_summary(
            summary,
            "Webex Calling uses a different permission model for outgoing "
            "calls. You'll choose the closest match during planning.",
        )
    return {"title": title, "explanation": explanation, "reassurance": _reassurance_for_severity(severity)}


def _explain_location_ambiguous(
    summary: str, context: dict[str, Any], severity: str
) -> dict[str, str]:
    device_pool = context.get("device_pool", "")
    candidates = context.get("candidates", [])
    title = f"Location mapping unclear: {device_pool}" if device_pool else "Location mapping unclear"
    if device_pool and candidates:
        explanation = (
            f"Device pool {device_pool} could map to multiple Webex locations: "
            f"{', '.join(candidates)}. You'll confirm the correct mapping during planning."
        )
    else:
        explanation = _with_summary(
            summary,
            "The system couldn't automatically determine which Webex "
            "location to assign. You'll confirm the correct mapping during planning.",
        )
    return {"title": title, "explanation": explanation, "reassurance": _reassurance_for_severity(severity)}


def _explain_duplicate_user(
    summary: str, context: dict[str, Any], severity: str
) -> dict[str, str]:
    user = context.get("user", "")
    count = context.get("count", "")
    title = f"Duplicate user record: {user}" if user else "Duplicate user record"
    if user and count:
        explanation = (
            f"User {user} has {count} records in CUCM. Webex Calling requires a "
            "single identity per person. During planning, you'll choose which record "
            "to keep and how to merge the settings."
        )
    else:
        explanation = _with_summary(
            summary,
            "Webex Calling requires a single identity per person. "
            "You'll choose how to consolidate during planning.",
        )
    return {"title": title, "explanation": explanation, "reassurance": _reassurance_for_severity(severity)}


def _explain_voicemail_incompatible(
    summary: str, context: dict[str, Any], severity: str
) -> dict[str, str]:
    feature = context.get("feature", "")
    title = f"Voicemail feature gap: {feature}" if feature else "Voicemail configuration change"
    if feature:
        explanation = (
            f"Your Unity Connection voicemail uses {feature}, which is not directly "
            "available in Webex Calling's built-in voicemail. You'll choose between "
            "Webex's built-in voicemail or a third-party voicemail system during planning."
        )
    else:
        explanation = _with_summary(
            summary,
            "Some Unity Connection voicemail features are not available "
            "in Webex Calling's built-in voicemail. You'll choose the best voicemail "
            "approach during planning.",
        )
    return {"title": title, "explanation": explanation, "reassurance": _reassurance_for_severity(severity)}


def _explain_workspace_license_tier(
    summary: str, context: dict[str, Any], severity: str
) -> dict[str, str]:
    workspace = context.get("workspace", "")
    tier = context.get("tier", "")
    title = f"Workspace license tier: {workspace}" if workspace else "Workspace license tier decision"
    if workspace and tier:
        explanation = (
            f"Workspace {workspace} has been mapped to the {tier} license tier. "
            "Webex Calling workspaces come in Basic (free, limited features) and "
            "Professional (full calling features) tiers. You'll confirm the right "
            "tier during planning."
        )
    else:
        explanation = _with_summary(
            summary,
            "Webex Calling workspaces come in Basic and Professional "
            "tiers with different feature sets. You'll confirm the right tier "
            "during planning.",
        )
    return {"title": title, "explanation": explanation, "reassurance": _reassurance_for_severity(severity)}


def _explain_workspace_type_uncertain(
    summary: str, context: dict[str, Any], severity: str
) -> dict[str, str]:
    device = context.get("device", "")
    title = f"Workspace type uncertain: {device}" if device else "Workspace type uncertain"
    if device:
        explanation = (
            f"Device {device} could be set up as a personal device or a shared "
            "workspace in Webex Calling. The system couldn't determine the intended "
            "use automatically. You'll confirm during planning."
        )
    else:
        explanation = _with_summary(
            summary,
            "The system couldn't determine whether this should be a "
            "personal device or a shared workspace. You'll confirm during planning.",
        )
    return {"title": title, "explanation": explanation, "reassurance": _reassurance_for_severity(severity)}


def _explain_hotdesk_dn_conflict(
    summary: str, context: dict[str, Any], severity: str
) -> dict[str, str]:
    dn = context.get("dn", "")
    title = f"Hot-desk extension conflict: {dn}" if dn else "Hot-desk extension conflict"
    if dn:
        explanation = (
            f"Extension {dn} is used for hot-desking but conflicts with another "
            "assignment. Webex Calling hot-desking uses a different model — "
            "you'll choose how to resolve the overlap during planning."
        )
    else:
        explanation = _with_summary(
            summary,
            "Webex Calling handles hot-desking differently from CUCM's "
            "Extension Mobility. You'll choose how to resolve any overlaps during planning.",
        )
    return {"title": title, "explanation": explanation, "reassurance": _reassurance_for_severity(severity)}


def _explain_feature_approximation(
    summary: str, context: dict[str, Any], severity: str
) -> dict[str, str]:
    cucm_feature = context.get("cucm_feature", "")
    webex_feature = context.get("webex_feature", "")
    title = f"Feature mapping: {cucm_feature}" if cucm_feature else "Feature mapping required"
    if cucm_feature and webex_feature:
        explanation = (
            f"{cucm_feature} doesn't have a direct Webex equivalent. The closest "
            f"match is {webex_feature}, which handles most of the same use cases."
        )
    else:
        explanation = _with_summary(
            summary,
            "The CUCM feature doesn't have a direct Webex equivalent, "
            "but a close match is available that handles most of the same use cases.",
        )
    return {"title": title, "explanation": explanation, "reassurance": _reassurance_for_severity(severity)}


def _explain_missing_data(
    summary: str, context: dict[str, Any], severity: str
) -> dict[str, str]:
    field = context.get("field", "")
    source = context.get("source", "")
    title = f"Missing data: {field}" if field else "Missing configuration data"
    if field and source:
        explanation = (
            f"The {field} value from {source} was not found in the CUCM export. "
            "This data is needed to complete the migration mapping. You may need to "
            "provide it manually or re-run the discovery."
        )
    else:
        explanation = _with_summary(
            summary,
            "Some configuration data was not found in the CUCM export. "
            "You may need to provide it manually or re-run the discovery.",
        )
    return {"title": title, "explanation": explanation, "reassurance": _reassurance_for_severity(severity)}


def _explain_number_conflict(
    summary: str, context: dict[str, Any], severity: str
) -> dict[str, str]:
    number = context.get("number", "")
    title = f"Phone number conflict: {number}" if number else "Phone number conflict"
    if number:
        explanation = (
            f"Phone number {number} is already in use in your Webex Calling "
            "organization. You'll need to resolve the conflict before migration — "
            "either by releasing the existing assignment or choosing a different number."
        )
    else:
        explanation = _with_summary(
            summary,
            "A phone number is already assigned in Webex Calling. "
            "You'll resolve the conflict before migration by releasing the existing "
            "assignment or choosing a different number.",
        )
    return {"title": title, "explanation": explanation, "reassurance": _reassurance_for_severity(severity)}


def _explain_architecture_advisory(
    summary: str, context: dict[str, Any], severity: str
) -> dict[str, str]:
    topic = context.get("topic", "")
    recommendation = context.get("recommendation", "")
    title = f"Architecture note: {topic}" if topic else "Architecture advisory"
    if topic and recommendation:
        explanation = (
            f"Regarding {topic}: {recommendation}. This is an architectural "
            "observation about your deployment that may influence your migration approach."
        )
    else:
        explanation = _with_summary(
            summary,
            "This is an architectural observation about your deployment "
            "that may influence your migration approach.",
        )
    return {"title": title, "explanation": explanation, "reassurance": _reassurance_for_severity(severity)}


# Template dispatch table
_TEMPLATES: dict[str, Any] = {
    "EXTENSION_CONFLICT": _explain_extension_conflict,
    "DN_AMBIGUOUS": _explain_dn_ambiguous,
    "DEVICE_INCOMPATIBLE": _explain_device_incompatible,
    "DEVICE_FIRMWARE_CONVERTIBLE": _explain_device_firmware_convertible,
    "SHARED_LINE_COMPLEX": _explain_shared_line_complex,
    "CSS_ROUTING_MISMATCH": _explain_css_routing_mismatch,
    "CALLING_PERMISSION_MISMATCH": _explain_calling_permission_mismatch,
    "LOCATION_AMBIGUOUS": _explain_location_ambiguous,
    "DUPLICATE_USER": _explain_duplicate_user,
    "VOICEMAIL_INCOMPATIBLE": _explain_voicemail_incompatible,
    "WORKSPACE_LICENSE_TIER": _explain_workspace_license_tier,
    "WORKSPACE_TYPE_UNCERTAIN": _explain_workspace_type_uncertain,
    "HOTDESK_DN_CONFLICT": _explain_hotdesk_dn_conflict,
    "FEATURE_APPROXIMATION": _explain_feature_approximation,
    "MISSING_DATA": _explain_missing_data,
    "NUMBER_CONFLICT": _explain_number_conflict,
    "ARCHITECTURE_ADVISORY": _explain_architecture_advisory,
}


def explain_decision(
    decision_type: str,
    severity: str,
    summary: str,
    context: dict[str, Any],
) -> dict[str, str]:
    """Translate a machine-readable decision into a plain-English explanation.

    Args:
        decision_type: A DecisionType value string (e.g., "CSS_ROUTING_MISMATCH").
        severity: One of "LOW", "MEDIUM", "HIGH", "CRITICAL".
        summary: Free-text summary from the decision record.
        context: Dict of context-specific fields for template interpolation.

    Returns:
        Dict with keys "title", "explanation", "reassurance".
    """
    summary = summary or ""  # ensure string
    template_fn = _TEMPLATES.get(decision_type)
    if template_fn is None:
        # Fallback for unknown decision types
        return {
            "title": decision_type.replace("_", " ").title(),
            "explanation": summary or "A migration decision requires your input.",
            "reassurance": _reassurance_for_severity(severity),
        }
    return template_fn(summary, context or {}, severity)
