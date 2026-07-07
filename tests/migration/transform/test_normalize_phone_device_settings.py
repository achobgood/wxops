"""Verify normalize_phone preserves device-settings fields in pre_migration_state."""
from wxcli.migration.transform.normalizers import normalize_phone

PHONE_WITH_DEVICE_SETTINGS = {
    "name": "SEP001122AABBCC", "model": "Cisco 9861", "description": "Test Phone",
    "protocol": "SIP",
    "ownerUserName": {"_value_1": "jdoe", "uuid": "{U1}"},
    "devicePoolName": {"_value_1": "HQ-Phones", "uuid": "{DP1}"},
    "callingSearchSpaceName": {"_value_1": "Std-CSS", "uuid": "{CSS1}"},
    "phoneTemplateName": {"_value_1": "Standard 9861", "uuid": "{PT1}"},
    "softkeyTemplateName": None, "product": "Cisco 9861", "class": "Phone", "lines": None,
    "commonPhoneConfigName": {"_value_1": "Standard Common Phone", "uuid": "{CPC1}"},
    "productSpecificConfiguration": {
        "BluetoothMode": "1", "WifiEnable": "1", "WifiSSID": "Corp-WiFi", "screenBrightness": "12",
    },
    "userLocale": "English_United_States", "networkLocale": "United_States",
    "dndOption": "Ringer Off", "dndStatus": "true", "enableExtensionMobility": "false",
}

def test_common_phone_config_name_preserved():
    result = normalize_phone(PHONE_WITH_DEVICE_SETTINGS)
    assert result.pre_migration_state["cucm_common_phone_config"] == "Standard Common Phone"

def test_product_specific_config_preserved():
    result = normalize_phone(PHONE_WITH_DEVICE_SETTINGS)
    psc = result.pre_migration_state["product_specific_config"]
    assert psc["BluetoothMode"] == "1"
    assert psc["WifiEnable"] == "1"
    assert psc["WifiSSID"] == "Corp-WiFi"

def test_user_locale_preserved():
    result = normalize_phone(PHONE_WITH_DEVICE_SETTINGS)
    assert result.pre_migration_state["cucm_user_locale"] == "English_United_States"

def test_network_locale_preserved():
    result = normalize_phone(PHONE_WITH_DEVICE_SETTINGS)
    assert result.pre_migration_state["cucm_network_locale"] == "United_States"

def test_dnd_fields_preserved():
    result = normalize_phone(PHONE_WITH_DEVICE_SETTINGS)
    assert result.pre_migration_state["cucm_dnd_option"] == "Ringer Off"
    assert result.pre_migration_state["cucm_dnd_status"] == "true"

def test_extension_mobility_preserved():
    result = normalize_phone(PHONE_WITH_DEVICE_SETTINGS)
    assert result.pre_migration_state["cucm_extension_mobility"] == "false"

def test_missing_fields_default_to_none():
    minimal = {"name": "SEP000000000000", "model": "Cisco 6841", "protocol": "SIP", "lines": None}
    result = normalize_phone(minimal)
    state = result.pre_migration_state
    assert state.get("cucm_common_phone_config") is None
    assert state.get("product_specific_config") is None
    assert state.get("cucm_user_locale") is None
    assert state.get("cucm_dnd_option") is None
    assert state.get("cucm_extension_mobility") is None
