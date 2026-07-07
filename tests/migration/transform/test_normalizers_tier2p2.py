"""Tests for Tier2-Phase2 normalizers — button template, softkey template, phone update."""
from wxcli.migration.transform.normalizers import (
    normalize_button_template,
    normalize_softkey_template,
    normalize_phone,
)


class TestNormalizeButtonTemplate:
    def test_basic_template(self):
        raw = {
            "name": "Standard 8845",
            "basePhoneTemplateName": {"_value_1": "Universal Phone Template", "uuid": "{abc}"},
            "buttons": {
                "button": [
                    {"feature": "Line", "index": "1"},
                    {"feature": "Speed Dial", "index": "2"},
                    {"feature": "Busy Lamp Field", "index": "3"},
                ],
            },
        }
        obj = normalize_button_template(raw, cluster="lab")
        assert obj.canonical_id == "button_template:Standard 8845"
        state = obj.pre_migration_state
        assert state["name"] == "Standard 8845"
        assert state["base_template"] == "Universal Phone Template"
        assert len(state["buttons"]) == 3
        assert state["buttons"][0] == {"index": 1, "feature": "Line"}
        assert state["buttons"][1] == {"index": 2, "feature": "Speed Dial"}

    def test_buttons_sorted_by_index(self):
        raw = {
            "name": "Custom",
            "basePhoneTemplateName": None,
            "buttons": {
                "button": [
                    {"feature": "Speed Dial", "index": "3"},
                    {"feature": "Line", "index": "1"},
                ],
            },
        }
        obj = normalize_button_template(raw)
        assert obj.pre_migration_state["buttons"][0]["index"] == 1
        assert obj.pre_migration_state["buttons"][1]["index"] == 3

    def test_empty_buttons(self):
        raw = {"name": "Empty", "basePhoneTemplateName": None, "buttons": None}
        obj = normalize_button_template(raw)
        assert obj.pre_migration_state["buttons"] == []

    def test_single_button_not_list(self):
        raw = {
            "name": "Single",
            "basePhoneTemplateName": None,
            "buttons": {"button": {"feature": "Line", "index": "1"}},
        }
        obj = normalize_button_template(raw)
        assert len(obj.pre_migration_state["buttons"]) == 1


class TestNormalizeSoftkeyTemplate:
    def test_basic_template(self):
        raw = {
            "name": "Standard User",
            "description": "Default softkeys",
            "defaultSoftkeyTemplateName": {"_value_1": "Factory Default", "uuid": "{x}"},
        }
        obj = normalize_softkey_template(raw, cluster="lab")
        assert obj.canonical_id == "softkey_template:Standard User"
        state = obj.pre_migration_state
        assert state["name"] == "Standard User"
        assert state["description"] == "Default softkeys"
        assert state["default_template"] == "Factory Default"
        assert isinstance(state["call_states"], dict)

    def test_none_name_returns_none(self):
        raw = {"name": None}
        assert normalize_softkey_template(raw) is None


class TestPhoneNormalizerCapturesSoftkeyTemplate:
    def test_softkey_template_in_pre_migration_state(self):
        raw = {
            "name": "SEP001122334455",
            "model": "Cisco 8845",
            "protocol": "SIP",
            "description": "Test phone",
            "ownerUserName": {"_value_1": "jdoe", "uuid": "{u}"},
            "devicePoolName": {"_value_1": "DP-HQ", "uuid": "{d}"},
            "callingSearchSpaceName": None,
            "phoneTemplateName": {"_value_1": "Standard 8845", "uuid": "{p}"},
            "softkeyTemplateName": {"_value_1": "Standard User", "uuid": "{s}"},
            "product": "Cisco 8845",
            "class": "Phone",
            "lines": None,
        }
        obj = normalize_phone(raw, cluster="lab")
        assert obj.pre_migration_state["cucm_softkey_template"] == "Standard User"

    def test_missing_softkey_template(self):
        raw = {
            "name": "SEP001122334455",
            "model": "Cisco 8845",
            "protocol": "SIP",
            "description": "",
            "ownerUserName": None,
            "devicePoolName": None,
            "callingSearchSpaceName": None,
            "phoneTemplateName": None,
            "softkeyTemplateName": None,
            "product": "Cisco 8845",
            "class": "Phone",
            "lines": None,
        }
        obj = normalize_phone(raw)
        assert obj.pre_migration_state["cucm_softkey_template"] is None
