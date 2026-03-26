"""Tests for TemplateExtractor — button templates (AXL) + softkey templates (SQL)."""
from unittest.mock import MagicMock

import pytest

from wxcli.migration.cucm.extractors.templates import TemplateExtractor


def _mock_connection(button_templates=None, softkey_sql_rows=None, typesoftkey_rows=None):
    """Build a mock AXLConnection that returns canned data.

    button_templates: list of dicts for AXL listPhoneButtonTemplate/getPhoneButtonTemplate
    softkey_sql_rows: list of dicts for executeSQLQuery (softkeytemplate table)
    typesoftkey_rows: list of dicts for executeSQLQuery (typesoftkey table)
    """
    conn = MagicMock()

    button_list = button_templates or []
    sk_rows = softkey_sql_rows or []
    type_rows = typesoftkey_rows or [
        {"enum": "0", "name": "Undefined"},
        {"enum": "1", "name": "Redial"},
        {"enum": "2", "name": "NewCall"},
        {"enum": "3", "name": "Hold"},
        {"enum": "9", "name": "End Call"},
    ]

    def paginated_list(method_name, search_criteria, returned_tags, page_size):
        if method_name == "listPhoneButtonTemplate":
            return button_list
        return []

    conn.paginated_list = MagicMock(side_effect=paginated_list)

    def get_detail(method_name, **kwargs):
        name = kwargs.get("name")
        if method_name == "getPhoneButtonTemplate":
            for t in button_list:
                tname = t.get("name") or ""
                if isinstance(tname, dict):
                    tname = tname.get("_value_1", "")
                if tname == name:
                    return {
                        "name": name,
                        "basePhoneTemplateName": t.get("basePhoneTemplateName", ""),
                        "buttons": t.get("_detail_buttons", {"button": []}),
                    }
        return None

    conn.get_detail = MagicMock(side_effect=get_detail)

    def execute_sql(query):
        if "typesoftkey" in query:
            return type_rows
        if "softkeytemplate" in query:
            return sk_rows
        return []

    conn.execute_sql = MagicMock(side_effect=execute_sql)
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
        conn = _mock_connection(softkey_sql_rows=[
            {
                "name": "Standard User",
                "description": "Default softkey template",
                "softkeyclause": "1:2:3:9",
                "softkeysetclause": "1:2;3:9;9;2;1:9;0:9;9;0:9;0:9;1:9;0;0:9",
                "iksoftkeytemplate_base": "abc-123",
            },
        ])
        ext = TemplateExtractor(conn)
        result = ext.extract()
        assert "softkey_templates" in ext.results
        assert len(ext.results["softkey_templates"]) == 1
        tmpl = ext.results["softkey_templates"][0]
        assert tmpl["name"] == "Standard User"
        assert tmpl["description"] == "Default softkey template"
        assert "call_states" in tmpl
        assert "On Hook" in tmpl["call_states"]
        # On Hook state has softkey IDs 1,2 → Redial, NewCall
        assert tmpl["call_states"]["On Hook"] == ["Redial", "NewCall"]
        assert tmpl["call_states"]["Connected"] == ["Hold", "End Call"]

    def test_handles_empty_cluster(self):
        conn = _mock_connection()
        ext = TemplateExtractor(conn)
        result = ext.extract()
        assert result.total == 0
        assert ext.results.get("button_templates", []) == []
        assert ext.results.get("softkey_templates", []) == []

    def test_softkey_sql_failure_graceful(self):
        """Softkey SQL failure should not crash, just return empty."""
        conn = _mock_connection()
        conn.execute_sql = MagicMock(side_effect=Exception("SQL error"))
        ext = TemplateExtractor(conn)
        result = ext.extract()
        assert ext.results.get("softkey_templates", []) == []
        assert len(result.errors) > 0
