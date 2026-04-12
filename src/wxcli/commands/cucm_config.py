"""Configuration management for CUCM migration projects.

Manages config.json in the project directory. Keys control pipeline behavior
(country code, language, auto-rules, etc.).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# Default auto-resolution rules for clear-cut, low-risk decisions.
#
# These reduce manual review burden without risking incorrect choices.
# Override per-project by writing "auto_rules" to config.json.
#
# IMPORTANT: Defaults are seeded into a project's `config.json` ONCE by
# `wxcli cucm init`. They are NOT applied at runtime — `load_config()`
# reads the saved file literally. Operators who edit `config.json` to
# remove a default can restore it via `wxcli cucm config reset auto_rules`
# (which clobbers any custom rules in `auto_rules` — preserve them by
# hand-editing instead).
#
# To add a new default rule WITHOUT regressing existing in-flight projects:
# 1. Append the rule here.
# 2. Document the upgrade procedure in the relevant runbook.
# 3. Operators on existing projects must either (a) hand-edit their
#    config.json to append the new rule, or (b) run
#    `wxcli cucm config reset auto_rules` (destructive to custom rules).
DEFAULT_AUTO_RULES: list[dict[str, Any]] = [
    # Incompatible devices have no migration path — always skip
    {"type": "DEVICE_INCOMPATIBLE", "choice": "skip",
     "reason": "No MPP migration path exists for this device"},
    # Convertible devices can always be firmware-flashed
    {"type": "DEVICE_FIRMWARE_CONVERTIBLE", "choice": "convert",
     "reason": "Device model can be firmware-converted to MPP"},
    # Hotdesk DN conflicts — primary DN always wins
    {"type": "HOTDESK_DN_CONFLICT", "choice": "keep_primary",
     "reason": "Primary DN takes precedence over hotdesk conflict"},
    # CUCM-only forwarding variants — accept the loss (rarely configured)
    {"type": "FORWARDING_LOSSY", "choice": "accept_loss",
     "reason": "CUCM-specific forwarding variant has no Webex equivalent"},
    # SNR timer controls — accept Webex simplification
    {"type": "SNR_LOSSY", "choice": "accept_loss",
     "reason": "SNR timer controls are simplified in Webex"},
    # Unmappable CUCM button types — no Webex equivalent exists
    {"type": "BUTTON_UNMAPPABLE", "choice": "accept_loss",
     "reason": "CUCM button type has no Webex equivalent"},
    # Calling permissions with 0 affected users — orphaned profile
    # Analyzer writes "assigned_users_count" in context (css_permission.py line 128)
    {"type": "CALLING_PERMISSION_MISMATCH",
     "match": {"assigned_users_count": 0}, "choice": "skip",
     "reason": "Orphaned permission profile — 0 users affected"},
    # Missing data on devices that are already incompatible — skip
    # (fixing missing data on a device we're not migrating is pointless)
    # `is_on_incompatible_device` is written by
    # enrich_cross_decision_context() during analysis_pipeline step 3.5.
    {"type": "MISSING_DATA",
     "match": {"is_on_incompatible_device": True}, "choice": "skip",
     "reason": "Missing data on incompatible device — skipping device anyway"},
]

DEFAULT_CONFIG: dict[str, Any] = {
    "country_code": "+1",
    "default_language": "en_us",
    "default_country": "US",
    "outside_dial_digit": "9",
    "create_method": "people_api",
    "include_phoneless_users": False,
    "auto_rules": DEFAULT_AUTO_RULES,
    "recording_vendor": "Webex",
    "site_prefix_rules": [],
    "category_rules": None,
    "e911": {
        "auto_configure_ecbn": True,
        "notification_email": None,
        "redsky_enabled": False,
        "primary_did_strategy": "first_line",
    },
}


def load_config(project_dir: Path) -> dict[str, Any]:
    """Load config.json from the project directory, with defaults."""
    config_path = project_dir / "config.json"
    config = dict(DEFAULT_CONFIG)
    if config_path.exists():
        with open(config_path) as f:
            saved = json.load(f)
        config.update(saved)
    return config


def save_config(project_dir: Path, config: dict[str, Any]) -> None:
    """Write config.json to the project directory."""
    config_path = project_dir / "config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


def coerce_value(value: str) -> Any:
    """Coerce a string CLI value to the appropriate Python type."""
    if value.lower() in ("true", "yes"):
        return True
    if value.lower() in ("false", "no"):
        return False
    try:
        n = int(value)
        # Only coerce if round-trip matches (preserves "+44" as string)
        if str(n) == value:
            return n
    except ValueError:
        pass
    try:
        return json.loads(value)
    except (json.JSONDecodeError, ValueError):
        pass
    return value
