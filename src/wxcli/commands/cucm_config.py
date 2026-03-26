"""Configuration management for CUCM migration projects.

Manages config.json in the project directory. Keys control pipeline behavior
(country code, language, auto-rules, etc.).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "country_code": "+1",
    "default_language": "en_us",
    "default_country": "US",
    "outside_dial_digit": "9",
    "create_method": "people_api",
    "include_phoneless_users": False,
    "auto_rules": [],
    "site_prefix_rules": [],
    "category_rules": None,
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
