"""DeviceSettingsMapper — CUCM device settings → Webex device settings templates.

Groups phones by (model_family, location) and generates location-level device
settings templates with per-device overrides for phones that differ from the
group majority.

Spec: docs/superpowers/specs/2026-04-10-device-settings-templates.md
"""
from __future__ import annotations

import json
import logging
from collections import Counter
from typing import Any

from wxcli.migration.models import (
    CanonicalDeviceSettingsTemplate,
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
    manual_option,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model family classification
# ---------------------------------------------------------------------------

_MODEL_FAMILY_PATTERNS: dict[str, str] = {
    "9811": "9800", "9821": "9800", "9841": "9800",
    "9851": "9800", "9861": "9800", "9871": "9800",
    "8875": "8875",
    "7811": "78xx", "7821": "78xx", "7832": "78xx",
    "7841": "78xx", "7861": "78xx",
    "6821": "68xx", "6841": "68xx", "6851": "68xx", "6861": "68xx",
}


def classify_model_family(model: str | None) -> str | None:
    """Classify a phone model into a device settings family.

    Returns "9800", "8875", "78xx", "68xx", or None.
    """
    if not model:
        return None
    for pattern, family in _MODEL_FAMILY_PATTERNS.items():
        if pattern in model:
            return family
    return None


# ---------------------------------------------------------------------------
# CUCM → Webex field mapping helpers
# ---------------------------------------------------------------------------

def map_bluetooth(mode: str | None) -> dict | None:
    """Map CUCM BluetoothMode (0-3) to Webex bluetooth settings."""
    if mode is None:
        return None
    mode_map = {
        "0": {"enabled": False},
        "1": {"enabled": True, "mode": "HANDSFREE"},
        "2": {"enabled": True, "mode": "PHONE"},
        "3": {"enabled": True, "mode": "BOTH"},
    }
    return mode_map.get(str(mode))


def map_wifi_security(mode: str | None) -> str | None:
    """Map CUCM WifiSecurityMode to Webex authenticationMethod."""
    if mode is None:
        return None
    security_map = {"WPA2-PSK": "PSK", "WPA2-Enterprise": "EAP"}
    return security_map.get(mode, mode)


def map_backlight_timeout(seconds: str | None) -> str | None:
    """Map CUCM backlightTimeout (seconds) to Webex backlightTimer enum."""
    if seconds is None:
        return None
    try:
        val = int(seconds)
    except (ValueError, TypeError):
        return None
    if val == 0:
        return "ALWAYS_ON"
    if val <= 30:
        return "THIRTY_SEC"
    if val <= 60:
        return "ONE_MIN"
    if val <= 300:
        return "FIVE_MIN"
    if val <= 1800:
        return "THIRTY_MIN"
    return "ALWAYS_ON"


def map_locale_to_language(locale: str | None) -> str | None:
    """Map CUCM locale (e.g. English_United_States) to Webex phoneLanguage enum."""
    if not locale:
        return None
    return locale.upper().replace(" ", "_")


def map_dnd(status: str | None) -> bool | None:
    """Map CUCM dndStatus to Webex bool."""
    if status is None:
        return None
    return str(status).lower() == "true"


def map_usb_port(value: str | None) -> bool | None:
    """Map CUCM usbPort (Enabled/Disabled) to Webex bool."""
    if value is None:
        return None
    return str(value).lower() == "enabled"


# ---------------------------------------------------------------------------
# Settings builder: extract + map all CUCM settings for one phone
# ---------------------------------------------------------------------------

def _build_phone_settings(phone_state: dict) -> dict[str, Any]:
    """Extract and map all device settings from a single phone's pre_migration_state.

    Returns a flat dict of Webex setting keys → values.
    Only includes settings that have non-None values.
    """
    psc = phone_state.get("product_specific_config") or {}
    settings: dict[str, Any] = {}

    # Bluetooth
    bt = map_bluetooth(psc.get("BluetoothMode"))
    if bt is not None:
        settings["bluetooth"] = bt

    # WiFi
    wifi_enabled = psc.get("WifiEnable")
    wifi_ssid = psc.get("WifiSSID")
    wifi_security = psc.get("WifiSecurityMode")
    if wifi_enabled is not None:
        wifi_settings: dict[str, Any] = {"enabled": str(wifi_enabled) == "1"}
        if wifi_ssid:
            wifi_settings["ssidName"] = wifi_ssid
        if wifi_security:
            auth = map_wifi_security(wifi_security)
            if auth:
                wifi_settings["authenticationMethod"] = auth
        settings["wifiNetwork"] = wifi_settings

    # Backlight timer
    timeout = psc.get("backlightTimeout")
    if timeout is not None:
        timer = map_backlight_timeout(timeout)
        if timer:
            settings["backlightTimer"] = timer

    # USB ports
    usb = map_usb_port(psc.get("usbPort"))
    if usb is not None:
        settings["usbPorts"] = {"enabled": usb, "sideUsbEnabled": usb, "rearUsbEnabled": usb}

    # Network: CDP, LLDP (from device pool defaults, if present)
    cdp = psc.get("cdpSwPort")
    if cdp is not None:
        settings["cdpEnabled"] = str(cdp).lower() in ("true", "1", "enabled")

    lldp = psc.get("lldpSwPort")
    if lldp is not None:
        settings["lldpEnabled"] = str(lldp).lower() in ("true", "1", "enabled")

    # Language
    locale = phone_state.get("cucm_user_locale")
    lang = map_locale_to_language(locale)
    if lang:
        settings["phoneLanguage"] = lang

    # DND
    dnd = map_dnd(phone_state.get("cucm_dnd_status"))
    if dnd is not None:
        settings["dndServicesEnabled"] = dnd

    # Volume (from PSC if present)
    for vol_key, webex_key in [
        ("ringerVolume", "ringerVolume"),
        ("speakerVolume", "speakerVolume"),
        ("handsetVolume", "handsetVolume"),
        ("headsetVolume", "headsetVolume"),
    ]:
        val = psc.get(vol_key)
        if val is not None:
            try:
                vol = int(val)
                settings.setdefault("volumeSettings", {})[webex_key] = vol
            except (ValueError, TypeError):
                pass

    # Screen brightness → screen timeout (lossy mapping)
    brightness = psc.get("screenBrightness")
    if brightness is not None:
        settings["screenTimeout"] = {"enabled": True, "value": 400}

    # Noise cancellation
    nc = psc.get("noiseCancellation")
    if nc is not None:
        settings["noiseCancellation"] = {
            "enabled": str(nc).lower() in ("true", "1", "enabled"),
            "allowEndUserOverrideEnabled": False,
        }

    return settings


def _majority_vote(values: list) -> Any:
    """Return the most common value from a list. Ties broken by first occurrence."""
    if not values:
        return None
    counter = Counter(str(v) for v in values)
    winner_str = counter.most_common(1)[0][0]
    # Return the original value (not stringified)
    for v in values:
        if str(v) == winner_str:
            return v
    return values[0]


def _merge_settings_majority(all_settings: list[dict]) -> dict:
    """Compute majority-vote settings across a list of per-phone settings dicts.

    For each setting key, collect all values and pick the most common one.
    Handles nested dicts by serializing to JSON string for comparison.
    """
    if not all_settings:
        return {}

    # Collect all keys across all phones
    all_keys: set[str] = set()
    for s in all_settings:
        all_keys.update(s.keys())

    result: dict[str, Any] = {}
    for key in sorted(all_keys):
        values = [s[key] for s in all_settings if key in s]
        if not values:
            continue

        # For dict values, serialize to JSON for comparison
        if isinstance(values[0], dict):
            json_values = [json.dumps(v, sort_keys=True) for v in values]
            winner_json = Counter(json_values).most_common(1)[0][0]
            result[key] = json.loads(winner_json)
        else:
            result[key] = _majority_vote(values)

    return result


# ---------------------------------------------------------------------------
# Unmappable settings detection
# ---------------------------------------------------------------------------

_UNMAPPABLE_PSC_FIELDS = {
    "idleUrl", "idleTimeout", "gratuitousArp", "dot1xAuth",
    "spanToPCPort", "alwaysUsePrimeLine", "alwaysUsePrimeLineForVoiceMessage",
}


def _detect_unmappable(phone_state: dict) -> list[str]:
    """Return list of CUCM PSC field names that have no Webex mapping."""
    psc = phone_state.get("product_specific_config") or {}
    found = []
    for field in _UNMAPPABLE_PSC_FIELDS:
        if psc.get(field) is not None:
            found.append(field)
    if phone_state.get("cucm_extension_mobility") in ("true", "True", True):
        found.append("enableExtensionMobility")
    return found


# ---------------------------------------------------------------------------
# DeviceSettingsMapper
# ---------------------------------------------------------------------------

class DeviceSettingsMapper(Mapper):
    """Map CUCM device settings to Webex device settings templates.

    Groups phones by (model_family, location), computes majority-vote
    settings per group, and stores device_settings_template objects.
    """

    name = "device_settings_mapper"
    depends_on = ["device_mapper", "location_mapper"]

    def map(self, store: MigrationStore) -> MapperResult:
        result = MapperResult()

        # Collect all devices with their locations and compatibility tiers
        devices_by_name: dict[str, dict] = {}
        for device_data in store.get_objects("device"):
            cid = device_data.get("canonical_id", "")
            tier = device_data.get("compatibility_tier", "")
            if tier not in ("native_mpp", "convertible"):
                continue
            name = device_data.get("cucm_device_name") or cid.split(":", 1)[-1]
            loc_id = device_data.get("location_canonical_id")
            model = device_data.get("model")
            family = classify_model_family(model)
            if not family or not loc_id:
                continue
            devices_by_name[name] = {
                "device_canonical_id": cid,
                "model": model,
                "model_family": family,
                "location_canonical_id": loc_id,
            }

        if not devices_by_name:
            return result

        # Build phone settings keyed by device name
        phone_settings: dict[str, dict] = {}
        phone_unmappable: dict[str, list[str]] = {}
        for phone_data in store.get_objects("phone"):
            phone_cid = phone_data.get("canonical_id", "")
            name = phone_cid.split(":", 1)[-1] if ":" in phone_cid else phone_cid
            if name not in devices_by_name:
                continue
            state = phone_data.get("pre_migration_state") or {}
            settings = _build_phone_settings(state)
            if settings:
                phone_settings[name] = settings
            unmappable = _detect_unmappable(state)
            if unmappable:
                phone_unmappable[name] = unmappable

        # Group by (model_family, location)
        groups: dict[tuple[str, str], list[str]] = {}
        for name, info in devices_by_name.items():
            key = (info["model_family"], info["location_canonical_id"])
            groups.setdefault(key, []).append(name)

        # Generate templates
        for (family, loc_id), names in groups.items():
            group_settings = [phone_settings[n] for n in names if n in phone_settings]
            if not group_settings:
                continue

            majority = _merge_settings_majority(group_settings)
            if not majority:
                continue

            # Detect per-device overrides
            majority_json = json.dumps(majority, sort_keys=True)
            overrides = []
            for name in names:
                if name not in phone_settings:
                    continue
                phone_json = json.dumps(phone_settings[name], sort_keys=True)
                if phone_json != majority_json:
                    overrides.append({
                        "device_canonical_id": devices_by_name[name]["device_canonical_id"],
                        "settings": phone_settings[name],
                    })

            # Collect unmappable settings across group
            all_unmappable: set[str] = set()
            for name in names:
                all_unmappable.update(phone_unmappable.get(name, []))

            # Detect lossy mappings and custom backgrounds
            lossy_fields = self._detect_lossy_mappings(group_settings)
            has_custom_bg = any(
                (phone_settings.get(n) or {}).get("background", {}).get("image") == "CUSTOM"
                for n in names
            )

            template_id = f"device_settings_template:{family}:{loc_id}"

            # Get a provenance from the first phone object for this group
            first_phone_data = next(
                (d for d in store.get_objects("phone")
                 if (d.get("canonical_id", "").split(":", 1)[-1] if ":" in d.get("canonical_id", "") else d.get("canonical_id", "")) in [n for n in names if n in phone_settings]),
                {}
            )

            template = CanonicalDeviceSettingsTemplate(
                canonical_id=template_id,
                provenance=extract_provenance(first_phone_data),
                status=MigrationStatus.ANALYZED,
                model_family=family,
                location_canonical_id=loc_id,
                settings=majority,
                per_device_overrides=overrides,
                unmappable_settings=sorted(all_unmappable),
                phones_using=len(names),
                custom_backgrounds=[],
            )
            store.upsert_object(template)
            result.objects_created += 1

            # Generate decisions for lossy mappings
            if lossy_fields or has_custom_bg:
                self._generate_lossy_decision(
                    store, result, template_id, family, loc_id,
                    lossy_fields, has_custom_bg, len(names),
                )

        return result

    def _detect_lossy_mappings(self, group_settings: list[dict]) -> list[str]:
        """Detect settings that map with value loss."""
        lossy = set()
        for s in group_settings:
            if "screenTimeout" in s:
                lossy.add("screenBrightness→screenTimeout (brightness level lost)")
            if "dndServicesEnabled" in s:
                lossy.add("dndOption (ringer off vs reject distinction lost)")
        return sorted(lossy)

    def _generate_lossy_decision(
        self,
        store: MigrationStore,
        result: MapperResult,
        template_id: str,
        family: str,
        loc_id: str,
        lossy_fields: list[str],
        has_custom_bg: bool,
        phone_count: int,
    ) -> None:
        """Generate DEVICE_SETTINGS_LOSSY decision."""
        details = []
        if lossy_fields:
            details.extend(lossy_fields)
        if has_custom_bg:
            details.append("Custom wallpaper detected (TFTP extraction not configured)")

        decision = self._create_decision(
            store=store,
            decision_type=DecisionType.DEVICE_SETTINGS_LOSSY,
            severity="MEDIUM",
            summary=f"Device settings for {family} at {loc_id}: {len(details)} lossy mapping(s)",
            context={
                "model_family": family,
                "location_canonical_id": loc_id,
                "lossy_details": details,
                "phone_count": phone_count,
            },
            options=[
                accept_option("Settings applied with noted fidelity loss"),
                manual_option("Manually configure affected settings post-migration"),
            ],
            affected_objects=[template_id],
        )
        store.save_decision(decision_to_store_dict(decision))
        result.decisions.append(decision)
