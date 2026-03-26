"""Report helper utilities for customer-facing text formatting."""
from __future__ import annotations

# Canonical ID prefixes used in the migration store.
# dn: has a special format — dn:NUMBER:PARTITION
_KNOWN_PREFIXES = (
    "css:", "device:", "location:", "partition:", "trunk:",
    "route_group:", "dial_plan:", "voicemail_profile:",
    "hunt_group:", "auto_attendant:", "call_queue:", "call_park:",
    "pickup_group:", "paging_group:", "workspace:", "schedule:",
    "operating_mode:", "shared_line:", "virtual_line:", "line:",
    "calling_permission:", "translation_pattern:", "user:",
)


def strip_canonical_id(canonical_id: str) -> str:
    """Strip internal canonical ID prefixes for customer-facing display.

    Examples:
        "css:Standard-Employee-CSS" → "Standard-Employee-CSS"
        "dn:1001:Internal-PT" → "1001 (Internal-PT)"
        "voicemail_profile:Default" → "Default"
        "plain-string" → "plain-string"
    """
    if not canonical_id:
        return ""

    # Special case: dn:NUMBER:PARTITION
    if canonical_id.startswith("dn:"):
        parts = canonical_id[3:].split(":", 1)
        if len(parts) == 2:
            return f"{parts[0]} ({parts[1]})"
        return parts[0]

    # Known prefixes
    for prefix in _KNOWN_PREFIXES:
        if canonical_id.startswith(prefix):
            return canonical_id[len(prefix):]

    # Unknown prefix — if there's a colon, strip up to first colon
    if ":" in canonical_id:
        return canonical_id.split(":", 1)[1]

    return canonical_id


# Suffixes to strip from device pool names for friendly display.
_SITE_SUFFIXES = ("-Phones", "-Softphones", "-CommonArea")


def friendly_site_name(device_pool_name: str) -> str:
    """Convert a CUCM device pool name to a customer-friendly site name.

    Examples:
        "DP-HQ-Phones" → "HQ"
        "DP-Branch" → "Branch"
        "MainOffice" → "MainOffice"
    """
    if not device_pool_name:
        return ""

    name = device_pool_name

    # Strip DP- prefix
    if name.startswith("DP-"):
        name = name[3:]

    # Strip known suffixes
    for suffix in _SITE_SUFFIXES:
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break

    return name
