"""Verify phone extractor requests device-settings-related AXL fields."""
from wxcli.migration.cucm.extractors.devices import PHONE_GET_RETURNED_TAGS

def test_phone_get_tags_include_common_phone_config_name():
    assert "commonPhoneConfigName" in PHONE_GET_RETURNED_TAGS

def test_phone_get_tags_include_product_specific_config():
    assert "productSpecificConfiguration" in PHONE_GET_RETURNED_TAGS

def test_phone_get_tags_include_user_locale():
    assert "userLocale" in PHONE_GET_RETURNED_TAGS

def test_phone_get_tags_include_network_locale():
    assert "networkLocale" in PHONE_GET_RETURNED_TAGS

def test_phone_get_tags_include_dnd_option():
    assert "dndOption" in PHONE_GET_RETURNED_TAGS

def test_phone_get_tags_include_dnd_status():
    assert "dndStatus" in PHONE_GET_RETURNED_TAGS

def test_phone_get_tags_include_extension_mobility():
    assert "enableExtensionMobility" in PHONE_GET_RETURNED_TAGS
