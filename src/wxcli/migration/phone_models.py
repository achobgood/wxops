"""Shared phone model constants for the CUCM migration pipeline.

Single source of truth for phone model classifications used across transform
mappers, analyzers, and execution handlers. This module has NO dependencies on
other migration code to avoid circular imports — it exports only plain data
(a set and two dicts).

Consumers:
    - ``transform/mappers/device_mapper.py`` — cloud vs telephony surface
    - ``transform/mappers/softkey_mapper.py`` — PSK capability
    - ``transform/mappers/button_template_mapper.py`` — line key counts
    - ``transform/analyzers/layout_overflow.py`` — line key overflow detection
    - ``execute/handlers.py`` — PhoneOS model normalization + KEM overflow split
"""
from __future__ import annotations

# PhoneOS phones (9800-series + 8875) are distinct from classic MPP in three ways:
#   1. They use cloud deviceId (not callingDeviceId) — device_id_surface="cloud".
#   2. Their model strings in the Webex API drop the "DMS " prefix
#      ("Cisco 9841" not "DMS Cisco 9841").
#   3. They support Programmable Softkeys (PSK).
PHONEOS_MODEL_NUMBERS: set[str] = {
    "9811", "9821", "9841", "9851", "9861", "9871", "8875",
}

# Max physical line-key count per phone model. Buttons beyond this count are
# KEM (Key Expansion Module) keys on KEM-capable models. Superset of the
# PhoneOS-only counts used by handlers.py — classic MPP models (7800/8800/6800)
# appear here for the mappers/analyzers that classify button templates.
MODEL_LINE_KEY_COUNTS: dict[str, int] = {
    # 7800-series
    "7821": 2, "7841": 4, "7861": 16,
    # 8800-series (classic MPP)
    "8811": 10, "8832": 0, "8841": 10, "8845": 10,
    "8851": 10, "8861": 10, "8865": 10,
    # 8875 (PhoneOS)
    "8875": 10,
    # 9800-series (PhoneOS)
    "9811": 2, "9821": 2, "9841": 4,
    "9851": 10, "9861": 16, "9871": 32,
    # 6800-series
    "6821": 2, "6841": 4, "6851": 12, "6861": 16, "6871": 10,
}

# PhoneOS-only subset of the above, used by handlers.py to split KEM overflow
# from line_keys during line-key-template execution. Derived from the superset
# so there is exactly one place where counts are authored.
PHONEOS_LINE_KEY_COUNTS: dict[str, int] = {
    model: MODEL_LINE_KEY_COUNTS[model] for model in PHONEOS_MODEL_NUMBERS
}
