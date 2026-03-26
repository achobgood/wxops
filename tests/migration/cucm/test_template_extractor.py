"""Tests for TemplateExtractor — button + softkey templates."""
from unittest.mock import MagicMock

import pytest

from wxcli.migration.cucm.extractors.templates import TemplateExtractor


def _mock_connection(button_templates=None, softkey_templates=None):
    """Build a mock AXLConnection that returns canned data."""
    conn = MagicMock()

    button_list = button_templates or []
    softkey_list = softkey_templates or []

    def paginated_list(method_name, search_criteria, returned_tags, page_size):
        if method_name == "listPhoneButtonTemplate":
            return button_list
        if method_name == "listSoftkeyTemplate":
            return softkey_list
        return []

    conn.paginated_list = MagicMock(side_effect=paginated_list)

    def get_detail(method_name, **kwargs):
        name = kwargs.get("name")
        if method_name == "getPhoneButtonTemplate":
            for t in button_list:
                tname = t.get("name") or (t.get("name", {}).get("_value_1") if isinstance(t.get("name"), dict) else None)
                if tname == name or t.get("name") == name:
                    return {
                        "name": name,
                        "basePhoneTemplateName": t.get("basePhoneTemplateName", ""),
                        "buttons": t.get("_detail_buttons", {"button": []}),
                    }
        if method_name == "getSoftkeyTemplate":
            for t in softkey_list:
                tname = t.get("name") or ""
                if tname == name:
                    return {
                        "name": name,
                        "description": t.get("description", ""),
                        "defaultSoftkeyTemplateName": t.get("defaultSoftkeyTemplateName", ""),
                        **t.get("_detail_states", {}),
                    }
        return None

    conn.get_detail = MagicMock(side_effect=get_detail)
    return conn


class TestTemplateExtractorButtonTemplates:
    def test_discovers_button_templates(self):
        conn = _mock_connection(button_templates=[
            {
                "name": "Standard 8845",
                "basePhoneTemplateName": "Universal Phone Template",
                "_detail_buttons": {
                    "button": [
                        {"feature": "Line", "index": "1"},
                        {"feature": "Speed Dial", "index": "2"},
                    ],
                },
            },
        ])
        ext = TemplateExtractor(conn)
        result = ext.extract()
        assert result.total >= 1
        assert "button_templates" in ext.results
        assert len(ext.results["button_templates"]) == 1
        detail = ext.results["button_templates"][0]
        assert detail["name"] == "Standard 8845"
        buttons = detail.get("buttons", {})
        btn_list = buttons.get("button", []) if isinstance(buttons, dict) else buttons
        assert len(btn_list) == 2

    def test_discovers_softkey_templates(self):
        conn = _mock_connection(softkey_templates=[
            {
                "name": "Standard User",
                "description": "Default softkey template",
                "defaultSoftkeyTemplateName": "",
                "_detail_states": {},
            },
        ])
        ext = TemplateExtractor(conn)
        result = ext.extract()
        assert "softkey_templates" in ext.results
        assert len(ext.results["softkey_templates"]) == 1
        assert ext.results["softkey_templates"][0]["name"] == "Standard User"

    def test_handles_empty_cluster(self):
        conn = _mock_connection()
        ext = TemplateExtractor(conn)
        result = ext.extract()
        assert result.total == 0
        assert ext.results.get("button_templates", []) == []
        assert ext.results.get("softkey_templates", []) == []
