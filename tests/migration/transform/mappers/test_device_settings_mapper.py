"""Tests for DeviceSettingsMapper — CUCM device settings → Webex templates."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from wxcli.migration.models import (
    CanonicalDevice,
    DecisionType,
    DeviceCompatibilityTier,
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.device_settings_mapper import (
    DeviceSettingsMapper,
    classify_model_family,
    map_backlight_timeout,
    map_bluetooth,
    map_dnd,
    map_locale_to_language,
    map_usb_port,
    map_wifi_security,
)


# ===== FIELD MAPPING TESTS =====

class TestMapBluetooth:
    def test_mode_0_disabled(self):
        assert map_bluetooth("0") == {"enabled": False}

    def test_mode_1_handsfree(self):
        assert map_bluetooth("1") == {"enabled": True, "mode": "HANDSFREE"}

    def test_mode_2_phone(self):
        assert map_bluetooth("2") == {"enabled": True, "mode": "PHONE"}

    def test_mode_3_both(self):
        assert map_bluetooth("3") == {"enabled": True, "mode": "BOTH"}

    def test_none_returns_none(self):
        assert map_bluetooth(None) is None


class TestMapWifiSecurity:
    def test_wpa2_psk(self):
        assert map_wifi_security("WPA2-PSK") == "PSK"

    def test_wpa2_enterprise(self):
        assert map_wifi_security("WPA2-Enterprise") == "EAP"

    def test_unknown_passthrough(self):
        assert map_wifi_security("WPA3") == "WPA3"

    def test_none(self):
        assert map_wifi_security(None) is None


class TestMapBacklightTimeout:
    def test_30_seconds(self):
        assert map_backlight_timeout("30") == "THIRTY_SEC"

    def test_60_seconds(self):
        assert map_backlight_timeout("60") == "ONE_MIN"

    def test_300_seconds(self):
        assert map_backlight_timeout("300") == "FIVE_MIN"

    def test_1800_seconds(self):
        assert map_backlight_timeout("1800") == "THIRTY_MIN"

    def test_zero_always_on(self):
        assert map_backlight_timeout("0") == "ALWAYS_ON"

    def test_none(self):
        assert map_backlight_timeout(None) is None


class TestMapLocale:
    def test_english_us(self):
        assert map_locale_to_language("English_United_States") == "ENGLISH_UNITED_STATES"

    def test_french_france(self):
        assert map_locale_to_language("French_France") == "FRENCH_FRANCE"

    def test_none(self):
        assert map_locale_to_language(None) is None


class TestMapDnd:
    def test_enabled(self):
        assert map_dnd("true") is True

    def test_disabled(self):
        assert map_dnd("false") is False

    def test_none(self):
        assert map_dnd(None) is None


class TestMapUsbPort:
    def test_enabled(self):
        assert map_usb_port("Enabled") is True

    def test_disabled(self):
        assert map_usb_port("Disabled") is False

    def test_none(self):
        assert map_usb_port(None) is None


class TestClassifyModelFamily:
    def test_9861(self):
        assert classify_model_family("Cisco 9861") == "9800"

    def test_9811(self):
        assert classify_model_family("Cisco 9811") == "9800"

    def test_8875(self):
        assert classify_model_family("Cisco 8875") == "8875"

    def test_7841(self):
        assert classify_model_family("Cisco 7841") == "78xx"

    def test_6841(self):
        assert classify_model_family("Cisco 6841") == "68xx"

    def test_unknown_returns_none(self):
        assert classify_model_family("Cisco IP Communicator") is None

    def test_none_returns_none(self):
        assert classify_model_family(None) is None


# ===== FIXTURE HELPERS =====

def _prov(name="test"):
    return Provenance(
        source_system="cucm", source_id=f"uuid-{name}", source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def _make_phone(
    name: str,
    model: str = "Cisco 9861",
    location_id: str = "location:HQ",
    psc: dict | None = None,
    cpc_name: str | None = None,
) -> MigrationObject:
    state = {
        "name": name,
        "model": model,
        "is_common_area": False,
        "cucm_device_pool": "HQ-Phones",
        "cucm_common_phone_config": cpc_name,
        "product_specific_config": psc,
        "cucm_user_locale": None,
        "cucm_dnd_option": None,
        "cucm_dnd_status": None,
        "cucm_extension_mobility": None,
    }
    return MigrationObject(
        canonical_id=f"phone:{name}",
        provenance=_prov(name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=state,
    )


def _make_device(
    name: str,
    model: str = "Cisco 9861",
    compatibility_tier: str = "native_mpp",
    location_id: str = "location:HQ",
) -> CanonicalDevice:
    return CanonicalDevice(
        canonical_id=f"device:{name}",
        provenance=_prov(name),
        status=MigrationStatus.ANALYZED,
        model=model,
        compatibility_tier=DeviceCompatibilityTier(compatibility_tier),
        location_canonical_id=location_id,
        cucm_device_name=name,
        pre_migration_state={
            "cucm_device_name": name,
            "model": model,
            "compatibility_tier": compatibility_tier,
            "location_canonical_id": location_id,
        },
    )


def _seed_store(phones, devices, location_id="location:HQ"):
    """Create store with phones, devices, and cross-refs."""
    store = MigrationStore(":memory:")

    # Insert location
    loc = MigrationObject(
        canonical_id=location_id,
        provenance=_prov("HQ"),
        status=MigrationStatus.ANALYZED,
        pre_migration_state={"name": "HQ"},
    )
    store.upsert_object(loc)

    for phone in phones:
        store.upsert_object(phone)
    for device in devices:
        store.upsert_object(device)

    # Cross-refs: phone → device pool → location (simplified for tests)
    for device in devices:
        cid = device.canonical_id
        store.add_cross_ref(cid, location_id, "device_in_location")

    return store


# ===== TEMPLATE GENERATION TESTS =====

class TestEmptyEnvironment:
    def test_no_phones_no_templates(self):
        """No phones → mapper produces no templates."""
        store = MigrationStore(":memory:")
        result = DeviceSettingsMapper().map(store)
        assert result.objects_created == 0
        assert result.decisions == []


class TestSingleModelSingleLocation:
    def test_ten_identical_phones_one_template(self):
        """10 phones with identical settings → 1 template, 0 overrides."""
        psc = {"BluetoothMode": "1", "WifiEnable": "0"}
        phones = [_make_phone(f"SEP00112233AA{i:02d}", psc=psc) for i in range(10)]
        devices = [_make_device(f"SEP00112233AA{i:02d}") for i in range(10)]
        store = _seed_store(phones, devices)

        result = DeviceSettingsMapper().map(store)

        assert result.objects_created == 1
        templates = store.get_objects("device_settings_template")
        assert len(templates) == 1
        tmpl = templates[0]
        assert tmpl["model_family"] == "9800"
        assert tmpl["location_canonical_id"] == "location:HQ"
        assert tmpl["phones_using"] == 10
        settings = tmpl["settings"]
        assert settings["bluetooth"]["enabled"] is True
        assert settings["bluetooth"]["mode"] == "HANDSFREE"
        assert len(tmpl.get("per_device_overrides", [])) == 0


class TestMultipleLocations:
    def test_same_model_three_locations_three_templates(self):
        """Same model across 3 locations → 3 templates."""
        phones = []
        devices = []
        for loc_idx, loc_name in enumerate(["HQ", "Branch-A", "Branch-B"]):
            loc_id = f"location:{loc_name}"
            for i in range(3):
                name = f"SEP{loc_idx:02d}{i:04d}000000"
                phones.append(_make_phone(name, location_id=loc_id, psc={"BluetoothMode": "1"}))
                devices.append(_make_device(name, location_id=loc_id))

        store = MigrationStore(":memory:")
        for loc_name in ["HQ", "Branch-A", "Branch-B"]:
            store.upsert_object(MigrationObject(
                canonical_id=f"location:{loc_name}",
                provenance=_prov(loc_name),
                status=MigrationStatus.ANALYZED,
                pre_migration_state={"name": loc_name},
            ))
        for phone in phones:
            store.upsert_object(phone)
        for device in devices:
            store.upsert_object(device)
            store.add_cross_ref(
                device.canonical_id,
                device.location_canonical_id,
                "device_in_location",
            )

        result = DeviceSettingsMapper().map(store)
        templates = store.get_objects("device_settings_template")
        assert len(templates) == 3


class TestMultipleModels:
    def test_9861_and_8875_two_templates(self):
        """9861 + 8875 at one location → 2 templates (different families)."""
        phones = [
            _make_phone("SEPAAA000000001", model="Cisco 9861", psc={"BluetoothMode": "1"}),
            _make_phone("SEPBBB000000001", model="Cisco 8875", psc={"BluetoothMode": "0"}),
        ]
        devices = [
            _make_device("SEPAAA000000001", model="Cisco 9861"),
            _make_device("SEPBBB000000001", model="Cisco 8875"),
        ]
        store = _seed_store(phones, devices)

        result = DeviceSettingsMapper().map(store)
        templates = store.get_objects("device_settings_template")
        families = {t["model_family"] for t in templates}
        assert families == {"9800", "8875"}


class TestMajorityVote:
    def test_majority_bluetooth_on(self):
        """6 phones BT on, 4 phones BT off → template has bluetooth.enabled=True."""
        phones = (
            [_make_phone(f"SEPON{i:010d}", psc={"BluetoothMode": "1"}) for i in range(6)]
            + [_make_phone(f"SEPOFF{i:09d}", psc={"BluetoothMode": "0"}) for i in range(4)]
        )
        devices = (
            [_make_device(f"SEPON{i:010d}") for i in range(6)]
            + [_make_device(f"SEPOFF{i:09d}") for i in range(4)]
        )
        store = _seed_store(phones, devices)

        DeviceSettingsMapper().map(store)
        templates = store.get_objects("device_settings_template")
        assert len(templates) == 1
        assert templates[0]["settings"]["bluetooth"]["enabled"] is True


# ===== OVERRIDE AND EXCLUSION TESTS =====

class TestPerDeviceOverrides:
    def test_two_phones_differ_from_majority(self):
        """10 phones, 2 with different Bluetooth → 1 template + 2 overrides."""
        psc_majority = {"BluetoothMode": "1"}
        psc_minority = {"BluetoothMode": "0"}
        phones = (
            [_make_phone(f"SEPMAJ{i:09d}", psc=psc_majority) for i in range(8)]
            + [_make_phone(f"SEPMIN{i:09d}", psc=psc_minority) for i in range(2)]
        )
        devices = (
            [_make_device(f"SEPMAJ{i:09d}") for i in range(8)]
            + [_make_device(f"SEPMIN{i:09d}") for i in range(2)]
        )
        store = _seed_store(phones, devices)

        DeviceSettingsMapper().map(store)
        templates = store.get_objects("device_settings_template")
        assert len(templates) == 1
        overrides = templates[0].get("per_device_overrides", [])
        assert len(overrides) == 2
        # Override devices should be the minority ones
        override_cids = {o["device_canonical_id"] for o in overrides}
        assert "device:SEPMIN000000000" in override_cids
        assert "device:SEPMIN000000001" in override_cids


class TestMissingPSC:
    def test_phone_without_psc_no_error(self):
        """Phone without productSpecificConfiguration → no settings mapped, no error."""
        phones = [_make_phone("SEP000000000000", psc=None)]
        devices = [_make_device("SEP000000000000")]
        store = _seed_store(phones, devices)

        result = DeviceSettingsMapper().map(store)
        # No settings to map → no template created
        assert result.objects_created == 0


class TestIncompatibleExcluded:
    def test_incompatible_phones_excluded(self):
        """INCOMPATIBLE phones do not contribute to any template."""
        phones = [
            _make_phone("SEPGOOD00000000", model="Cisco 9861", psc={"BluetoothMode": "1"}),
            _make_phone("SEPBAD000000000", model="Cisco 7911", psc={"BluetoothMode": "0"}),
        ]
        devices = [
            _make_device("SEPGOOD00000000", model="Cisco 9861", compatibility_tier="native_mpp"),
            _make_device("SEPBAD000000000", model="Cisco 7911", compatibility_tier="incompatible"),
        ]
        store = _seed_store(phones, devices)

        DeviceSettingsMapper().map(store)
        templates = store.get_objects("device_settings_template")
        assert len(templates) == 1
        assert templates[0]["phones_using"] == 1  # Only the good phone


class TestWebexAppExcluded:
    def test_software_phones_excluded(self):
        """WEBEX_APP devices do not contribute to any template."""
        phones = [
            _make_phone("SEPREAL00000000", model="Cisco 9861", psc={"BluetoothMode": "1"}),
            _make_phone("CSFJDOE", model="Cisco IP Communicator", psc=None),
        ]
        devices = [
            _make_device("SEPREAL00000000", model="Cisco 9861", compatibility_tier="native_mpp"),
            _make_device("CSFJDOE", model="Cisco IP Communicator", compatibility_tier="webex_app"),
        ]
        store = _seed_store(phones, devices)

        DeviceSettingsMapper().map(store)
        templates = store.get_objects("device_settings_template")
        assert len(templates) == 1
        assert templates[0]["phones_using"] == 1


class TestUnknownPSCFields:
    def test_unknown_xml_elements_ignored(self):
        """PSC with unknown XML elements → ignored gracefully, known fields still mapped."""
        psc = {
            "BluetoothMode": "1",
            "UnknownCucmField": "some_value",
            "AnotherWeirdField": "42",
            "FutureFeature": "enabled",
        }
        phones = [_make_phone("SEP000000000099", psc=psc)]
        devices = [_make_device("SEP000000000099")]
        store = _seed_store(phones, devices)

        result = DeviceSettingsMapper().map(store)
        templates = store.get_objects("device_settings_template")
        assert len(templates) == 1
        # Known field mapped correctly
        assert templates[0]["settings"]["bluetooth"]["enabled"] is True
        # Unknown fields not in output (no error)
        assert "UnknownCucmField" not in str(templates[0]["settings"])


class TestLossyDecision:
    def test_custom_wallpaper_generates_decision(self):
        """Phone with screen brightness → DEVICE_SETTINGS_LOSSY decision."""
        psc = {"BluetoothMode": "1", "screenBrightness": "12"}
        phones = [_make_phone("SEP000000000001", psc=psc)]
        devices = [_make_device("SEP000000000001")]
        store = _seed_store(phones, devices)

        result = DeviceSettingsMapper().map(store)
        assert len(result.decisions) == 1
        assert result.decisions[0].type == DecisionType.DEVICE_SETTINGS_LOSSY
