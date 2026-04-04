"""Migration complexity score algorithm.

Queries a MigrationStore and produces a 0-100 complexity score with
8 weighted factors and a human-readable breakdown.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from wxcli.migration.store import MigrationStore


# Factor weights (must sum to 100)
WEIGHTS = {
    "CSS Complexity": 20,
    "Feature Parity": 17,
    "Device Compatibility": 15,
    "Decision Density": 15,
    "Scale": 10,
    "Shared Line Complexity": 10,
    "Routing Complexity": 5,
    "Phone Config Complexity": 8,
}

# Customer-friendly display names for score factors
DISPLAY_NAMES = {
    "CSS Complexity": "Calling Restrictions",
    "Feature Parity": "Feature Compatibility",
    "Device Compatibility": "Device Readiness",
    "Decision Density": "Outstanding Decisions",
    "Scale": "Scale",
    "Shared Line Complexity": "Shared Lines",
    "Routing Complexity": "Routing",
    "Phone Config Complexity": "Phone Configuration",
}

# Label thresholds
LABEL_THRESHOLDS = [
    (30, "Straightforward", "#2E7D32"),
    (55, "Moderate", "#F57C00"),
    (100, "Complex", "#C62828"),
]


# Score calibration status — set to True once validated against real environments.
# When False, reports include an UNCALIBRATED disclaimer.
SCORE_CALIBRATED: bool = False


@dataclass
class ScoreResult:
    """Result of complexity score computation."""
    score: int = 0
    label: str = "Straightforward"
    color: str = "#2E7D32"
    factors: list[dict[str, Any]] = field(default_factory=list)
    calibrated: bool = SCORE_CALIBRATED


def compute_complexity_score(store: MigrationStore) -> ScoreResult:
    """Compute migration complexity score from store data.

    Args:
        store: Populated MigrationStore (post-analyze state).

    Returns:
        ScoreResult with score (0-100), label, color, and 8 factor dicts.
    """
    factor_funcs = [
        ("CSS Complexity", _css_complexity),
        ("Feature Parity", _feature_parity),
        ("Device Compatibility", _device_compatibility),
        ("Decision Density", _decision_density),
        ("Scale", _scale_factor),
        ("Shared Line Complexity", _shared_line_complexity),
        ("Routing Complexity", _routing_complexity),
        ("Phone Config Complexity", _phone_config_complexity),
    ]

    factors = []
    weighted_total = 0.0

    for name, func in factor_funcs:
        raw_score, detail = func(store)
        raw_score = max(0, min(100, raw_score))  # clamp to 0-100
        weight = WEIGHTS[name]
        weighted_score = raw_score * weight / 100.0
        weighted_total += weighted_score
        factors.append({
            "name": name,
            "display_name": DISPLAY_NAMES.get(name, name),
            "weight": weight,
            "raw_score": raw_score,
            "weighted_score": round(weighted_score, 1),
            "detail": detail,
        })

    score = round(weighted_total)
    score = max(0, min(100, score))

    label = "Straightforward"
    color = "#2E7D32"
    for threshold, lbl, clr in LABEL_THRESHOLDS:
        if score <= threshold:
            label = lbl
            color = clr
            break

    return ScoreResult(score=score, label=label, color=color, factors=factors)


# ---------------------------------------------------------------------------
# Factor functions — each returns (raw_score: int, detail: str)
# ---------------------------------------------------------------------------

def _css_complexity(store: MigrationStore) -> tuple[int, str]:
    """Score based on CSS count and partition depth.

    Checks for CSS_ROUTING_MISMATCH and CALLING_PERMISSION_MISMATCH decisions.
    """
    css_count = store.count_by_type("css")
    if css_count == 0:
        return 0, "No CSSes found"

    # Count avg partitions per CSS via cross-refs
    css_refs = store.get_cross_refs(relationship="css_contains_partition")
    if css_refs:
        avg_partitions = len(css_refs) / css_count
    else:
        avg_partitions = 0

    # Check for routing mismatch decisions
    decisions = store.get_all_decisions()
    css_decisions = [
        d for d in decisions
        if d["type"] in ("CSS_ROUTING_MISMATCH", "CALLING_PERMISSION_MISMATCH")
    ]

    # Score: base from CSS count + depth + mismatch decisions
    base = min(css_count * 5, 40)  # 0-40 from count
    depth = min(avg_partitions * 8, 30)  # 0-30 from depth
    mismatch = min(len(css_decisions) * 15, 30)  # 0-30 from decisions

    raw = int(base + depth + mismatch)
    detail = f"{css_count} CSSes, avg {avg_partitions:.1f} partitions/CSS, {len(css_decisions)} routing decisions"
    return raw, detail


def _feature_parity(store: MigrationStore) -> tuple[int, str]:
    """Score based on FEATURE_APPROXIMATION decisions relative to total features."""
    feature_types = ["hunt_group", "call_queue", "auto_attendant",
                     "call_park", "pickup_group", "paging_group"]
    total_features = sum(store.count_by_type(t) for t in feature_types)

    if total_features == 0:
        return 0, "No features found"

    decisions = store.get_all_decisions()
    approx_decisions = [d for d in decisions if d["type"] == "FEATURE_APPROXIMATION"]
    approx_count = len(approx_decisions)

    # Percentage of features that need approximation
    ratio = approx_count / total_features
    raw = int(ratio * 100)
    detail = f"{approx_count}/{total_features} features need approximation"
    return raw, detail


def _device_compatibility(store: MigrationStore) -> tuple[int, str]:
    """Score based on device compatibility tiers."""
    devices = store.get_objects("device")
    if not devices:
        return 0, "No devices found"

    total = len(devices)
    convertible = sum(1 for d in devices if d.get("compatibility_tier") == "convertible")
    incompatible = sum(1 for d in devices if d.get("compatibility_tier") == "incompatible")

    # Incompatible devices weigh heavily, convertible less so
    raw = int((incompatible * 100 + convertible * 30) / total)
    detail = f"{total} devices: {total - convertible - incompatible} native, {convertible} convertible, {incompatible} incompatible"
    return raw, detail


def _decision_density(store: MigrationStore) -> tuple[int, str]:
    """Score based on unresolved decisions relative to total objects."""
    decisions = store.get_all_decisions()
    unresolved = [d for d in decisions if d.get("chosen_option") is None]
    unresolved_count = len(unresolved)

    # Count total objects across known types
    _REPORT_OBJECT_TYPES = [
        "user", "device", "location", "hunt_group", "call_queue",
        "auto_attendant", "call_park", "pickup_group", "paging_group",
        "trunk", "route_group", "dial_plan", "translation_pattern",
        "css", "partition", "shared_line", "workspace", "virtual_line",
        "operating_mode", "schedule", "voicemail_profile", "calling_permission",
    ]
    total_objects = sum(store.count_by_type(t) for t in _REPORT_OBJECT_TYPES)

    if total_objects == 0:
        return 0, "No objects in store"

    # Log-scaled density: raw_ratio * log multiplier
    ratio = unresolved_count / total_objects
    raw = int(min(ratio * 100 * math.log2(max(unresolved_count, 1) + 1), 100))
    detail = f"{unresolved_count} unresolved decisions across {total_objects} objects"
    return raw, detail


def _scale_factor(store: MigrationStore) -> tuple[int, str]:
    """Score based on user count (log-scaled).

    Uses logarithmic scaling: log10(users) * 10, capped at 100.
    Ensures size alone doesn't dominate the score (10% weight).
    - 1-10 users: 0-10 raw points
    - 50 users: ~17 raw points
    - 500 users: ~27 raw points
    - 5000 users: ~37 raw points

    Note: Spec examples (50≈2, 500≈5, 5000≈8) were illustrative targets
    for the weighted contribution, not raw score values.
    """
    user_count = store.count_by_type("user")
    if user_count == 0:
        return 0, "No users found"

    raw = int(min(math.log10(max(user_count, 1)) * 10, 100))
    detail = f"{user_count} users"
    return raw, detail


def _shared_line_complexity(store: MigrationStore) -> tuple[int, str]:
    """Score based on shared line decisions and objects."""
    decisions = store.get_all_decisions()
    shared_decisions = [d for d in decisions if d["type"] == "SHARED_LINE_COMPLEX"]
    shared_objects = store.count_by_type("shared_line")

    count = len(shared_decisions) + shared_objects
    if count == 0:
        return 0, "No shared lines"

    # Each shared line adds 15 points, capped at 100
    raw = min(count * 15, 100)
    detail = f"{shared_objects} shared lines, {len(shared_decisions)} complex decisions"
    return raw, detail


def _routing_complexity(store: MigrationStore) -> tuple[int, str]:
    """Score based on trunk, route group, and translation pattern counts."""
    trunks = store.count_by_type("trunk")
    route_groups = store.count_by_type("route_group")
    trans_patterns = store.count_by_type("translation_pattern")

    total = trunks + route_groups + trans_patterns
    if total == 0:
        return 0, "No routing objects"

    # Each routing object adds 10 points, capped at 100
    raw = min(total * 10, 100)
    detail = f"{trunks} trunks, {route_groups} route groups, {trans_patterns} translation patterns"
    return raw, detail


def _phone_config_complexity(store: MigrationStore) -> tuple[int, str]:
    """Score based on phone button template and softkey customization.

    Checks for custom button templates, KEM modules, and PSK softkey migration.
    """
    templates = store.get_objects("line_key_template")
    layouts = store.get_objects("device_layout")
    softkeys = store.get_objects("softkey_config")

    if not templates and not layouts and not softkeys:
        return 0, "No phone config data"

    template_count = len(templates) if templates else 0
    layout_count = len(layouts) if layouts else 0
    softkey_count = len(softkeys) if softkeys else 0

    # Count phones with KEM modules
    kem_count = 0
    if layouts:
        kem_count = sum(1 for l in layouts if l.get("resolved_kem_keys"))

    # Count unmapped button types across all templates
    unmapped_count = 0
    if templates:
        unmapped_count = sum(len(t.get("unmapped_buttons", [])) for t in templates)

    # Score: templates + KEM + unmapped buttons + softkeys
    raw = 0
    raw += min(template_count * 8, 30)   # 0-30 from template count
    raw += min(kem_count * 10, 25)        # 0-25 from KEM modules
    raw += min(unmapped_count * 5, 20)    # 0-20 from unmapped buttons
    raw += min(softkey_count * 8, 25)     # 0-25 from softkey templates

    parts = []
    if template_count:
        parts.append(f"{template_count} button templates")
    if kem_count:
        parts.append(f"{kem_count} KEM phones")
    if unmapped_count:
        parts.append(f"{unmapped_count} unmapped buttons")
    if softkey_count:
        parts.append(f"{softkey_count} softkey templates")

    detail = ", ".join(parts) if parts else "No phone config data"
    return raw, detail
