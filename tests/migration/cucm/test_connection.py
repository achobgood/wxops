"""Tests for AXL connection module.

Mocks zeep Client, Transport, and Session so no live CUCM is required.
"""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import pytest

from wxcli.migration.cucm.connection import AXLConnection, AXLConnectionError


# ------------------------------------------------------------------
# Helpers — build a mock AXLConnection without hitting __init__
# ------------------------------------------------------------------

def _make_conn(**overrides) -> AXLConnection:
    """Construct an AXLConnection with zeep fully mocked out."""
    with patch("wxcli.migration.cucm.connection.Client") as mock_client_cls, \
         patch("wxcli.migration.cucm.connection.Transport") as mock_transport_cls, \
         patch("wxcli.migration.cucm.connection.Session") as mock_session_cls, \
         patch("wxcli.migration.cucm.connection.Settings"):

        mock_session = mock_session_cls.return_value
        mock_client = mock_client_cls.return_value
        mock_service = mock_client.create_service.return_value

        conn = AXLConnection(
            host=overrides.get("host", "cucm.example.com"),
            username=overrides.get("username", "admin"),
            password=overrides.get("password", "secret"),
            version=overrides.get("version", "14.0"),
            verify_ssl=overrides.get("verify_ssl", False),
            timeout=overrides.get("timeout", 30),
        )

    # Stash mocks on the connection so tests can configure them.
    conn._mock_client_cls = mock_client_cls
    conn._mock_transport_cls = mock_transport_cls
    conn._mock_session = mock_session
    conn._mock_service = mock_service
    return conn


# ------------------------------------------------------------------
# 1. test_connection_init
# ------------------------------------------------------------------

class TestConnectionInit:
    """Verify AXLConnection constructs the WSDL URL and sets up auth."""

    def test_wsdl_url_format(self):
        conn = _make_conn(host="10.0.0.1")
        assert conn.wsdl_url == "https://10.0.0.1:8443/axl/AXLAPIService?wsdl"

    def test_wsdl_url_with_hostname(self):
        conn = _make_conn(host="cucm-pub.corp.local")
        assert conn.wsdl_url == "https://cucm-pub.corp.local:8443/axl/AXLAPIService?wsdl"

    def test_session_auth_configured(self):
        with patch("wxcli.migration.cucm.connection.Client"), \
             patch("wxcli.migration.cucm.connection.Transport"), \
             patch("wxcli.migration.cucm.connection.Session") as mock_session_cls, \
             patch("wxcli.migration.cucm.connection.Settings"):

            mock_session = mock_session_cls.return_value
            AXLConnection("host", "myuser", "mypass", verify_ssl=True)

            # Session should have basic auth and verify set
            assert mock_session.auth is not None
            assert mock_session.verify is True

    def test_session_verify_false_by_default(self):
        with patch("wxcli.migration.cucm.connection.Client"), \
             patch("wxcli.migration.cucm.connection.Transport"), \
             patch("wxcli.migration.cucm.connection.Session") as mock_session_cls, \
             patch("wxcli.migration.cucm.connection.Settings"):

            mock_session = mock_session_cls.return_value
            AXLConnection("host", "user", "pass")
            assert mock_session.verify is False

    def test_transport_receives_session_and_timeout(self):
        with patch("wxcli.migration.cucm.connection.Client"), \
             patch("wxcli.migration.cucm.connection.Transport") as mock_transport_cls, \
             patch("wxcli.migration.cucm.connection.Session") as mock_session_cls, \
             patch("wxcli.migration.cucm.connection.Settings"):

            mock_session = mock_session_cls.return_value
            AXLConnection("host", "user", "pass", timeout=60)
            mock_transport_cls.assert_called_once_with(
                session=mock_session, timeout=60
            )

    def test_client_receives_wsdl_and_transport(self):
        with patch("wxcli.migration.cucm.connection.Client") as mock_client_cls, \
             patch("wxcli.migration.cucm.connection.Transport") as mock_transport_cls, \
             patch("wxcli.migration.cucm.connection.Session"), \
             patch("wxcli.migration.cucm.connection.Settings") as mock_settings_cls:

            mock_transport = mock_transport_cls.return_value
            mock_settings = mock_settings_cls.return_value
            AXLConnection("myhost", "user", "pass")
            mock_client_cls.assert_called_once_with(
                "https://myhost:8443/axl/AXLAPIService?wsdl",
                transport=mock_transport,
                settings=mock_settings,
            )

    def test_service_attribute_set(self):
        conn = _make_conn()
        # service is now from client.create_service(), not client.service
        assert conn.service is conn._mock_service

    def test_version_stored(self):
        conn = _make_conn(version="12.5")
        assert conn.version == "12.5"

    def test_connection_error_on_client_failure(self):
        with patch("wxcli.migration.cucm.connection.Client") as mock_client_cls, \
             patch("wxcli.migration.cucm.connection.Transport"), \
             patch("wxcli.migration.cucm.connection.Session"), \
             patch("wxcli.migration.cucm.connection.Settings"):

            mock_client_cls.side_effect = Exception("Connection refused")
            with pytest.raises(AXLConnectionError, match="Failed to load WSDL"):
                AXLConnection("badhost", "user", "pass")


# ------------------------------------------------------------------
# 2. test_get_version
# ------------------------------------------------------------------

class TestGetVersion:
    """Mock service.getCCMVersion() and verify version string extraction."""

    def test_extracts_version_from_nested_dict(self):
        conn = _make_conn()
        conn.service.getCCMVersion.return_value = {
            "return": {
                "componentVersion": {
                    "version": "14.0.1.12900-161"
                }
            }
        }
        assert conn.get_version() == "14.0.1.12900-161"

    def test_extracts_version_from_string_component(self):
        conn = _make_conn()
        conn.service.getCCMVersion.return_value = {
            "return": {
                "componentVersion": "12.5.1.10000-1"
            }
        }
        assert conn.get_version() == "12.5.1.10000-1"

    def test_falls_back_when_component_is_empty(self):
        conn = _make_conn(version="14.0")
        conn.service.getCCMVersion.return_value = {
            "return": {
                "componentVersion": {}
            }
        }
        # Empty dict → isinstance(comp, dict) is True → .get("version", self.version) → "14.0"
        assert conn.get_version() == "14.0"

    def test_falls_back_when_component_is_none(self):
        conn = _make_conn(version="12.5")
        conn.service.getCCMVersion.return_value = {
            "return": {
                "componentVersion": None
            }
        }
        assert conn.get_version() == "12.5"

    def test_falls_back_when_return_is_not_dict(self):
        conn = _make_conn(version="11.5")
        conn.service.getCCMVersion.return_value = {
            "return": "unexpected"
        }
        assert conn.get_version() == "11.5"

    def test_falls_back_when_return_is_empty_dict(self):
        conn = _make_conn(version="14.0")
        conn.service.getCCMVersion.return_value = {
            "return": {}
        }
        # Empty dict → isinstance True → loop finds no componentVersion → falls through
        # Actually: isinstance(version_info, dict) is True, comp = {}.get("componentVersion", {}) → {}
        # isinstance(comp, dict) True → {}.get("version", self.version) → "14.0"
        assert conn.get_version() == "14.0"


# ------------------------------------------------------------------
# 3. test_paginated_list_single_page
# ------------------------------------------------------------------

class TestPaginatedListSinglePage:
    """Mock a list response with fewer items than page_size."""

    def test_single_page_returns_all_items(self):
        conn = _make_conn()
        rows = [{"name": "phone1"}, {"name": "phone2"}]
        # AXL response: {'return': {'phone': [rows...]}}
        conn.service.listPhone.return_value = {"return": {"phone": rows}}

        result = conn.paginated_list(
            method_name="listPhone",
            search_criteria={"name": "%"},
            returned_tags={"name": ""},
            page_size=200,
        )
        assert result == rows
        # Should only call once because len(batch) < page_size
        conn.service.listPhone.assert_called_once()

    def test_single_page_called_with_correct_args(self):
        conn = _make_conn()
        conn.service.listPhone.return_value = {"return": {"phone": [{"name": "a"}]}}

        conn.paginated_list(
            method_name="listPhone",
            search_criteria={"name": "%"},
            returned_tags={"name": "", "description": ""},
            page_size=100,
        )
        conn.service.listPhone.assert_called_once_with(
            searchCriteria={"name": "%"},
            returnedTags={"name": "", "description": ""},
            first="100",
            skip="0",
        )


# ------------------------------------------------------------------
# 4. test_paginated_list_multi_page
# ------------------------------------------------------------------

class TestPaginatedListMultiPage:
    """Mock two pages: first full, second partial. Verify pagination."""

    def test_two_pages_combined(self):
        conn = _make_conn()
        page1 = [{"name": f"user{i}"} for i in range(5)]
        page2 = [{"name": "user5"}, {"name": "user6"}]

        conn.service.listEndUser.side_effect = [
            {"return": {"endUser": page1}},
            {"return": {"endUser": page2}},
        ]

        result = conn.paginated_list(
            method_name="listEndUser",
            search_criteria={"firstName": "%"},
            returned_tags={"firstName": "", "lastName": ""},
            page_size=5,
        )
        assert len(result) == 7
        assert result == page1 + page2

    def test_pagination_calls_with_correct_skip(self):
        conn = _make_conn()
        page1 = [{"name": f"p{i}"} for i in range(3)]
        page2 = [{"name": "p3"}]

        conn.service.listLine.side_effect = [
            {"return": {"line": page1}},
            {"return": {"line": page2}},
        ]

        conn.paginated_list(
            method_name="listLine",
            search_criteria={"pattern": "%"},
            returned_tags={"pattern": ""},
            page_size=3,
        )

        calls = conn.service.listLine.call_args_list
        assert len(calls) == 2
        # First call: skip=0
        assert calls[0].kwargs["skip"] == "0"
        # Second call: skip=3
        assert calls[1].kwargs["skip"] == "3"

    def test_stops_when_second_page_is_empty(self):
        conn = _make_conn()
        page1 = [{"name": f"x{i}"} for i in range(5)]

        conn.service.listPhone.side_effect = [
            {"return": {"phone": page1}},
            {"return": None},  # empty page
        ]

        result = conn.paginated_list(
            method_name="listPhone",
            search_criteria={"name": "%"},
            returned_tags={"name": ""},
            page_size=5,
        )
        assert len(result) == 5
        assert conn.service.listPhone.call_count == 2

    def test_three_pages(self):
        conn = _make_conn()
        page1 = [{"name": f"a{i}"} for i in range(10)]
        page2 = [{"name": f"b{i}"} for i in range(10)]
        page3 = [{"name": "c0"}, {"name": "c1"}]

        conn.service.listCss.side_effect = [
            {"return": {"css": page1}},
            {"return": {"css": page2}},
            {"return": {"css": page3}},
        ]

        result = conn.paginated_list(
            method_name="listCss",
            search_criteria={"name": "%"},
            returned_tags={"name": ""},
            page_size=10,
        )
        assert len(result) == 22
        assert conn.service.listCss.call_count == 3


# ------------------------------------------------------------------
# 5. test_paginated_list_empty
# ------------------------------------------------------------------

class TestPaginatedListEmpty:
    """Mock empty response, verify empty list returned."""

    def test_none_response(self):
        conn = _make_conn()
        conn.service.listPhone.return_value = None
        result = conn.paginated_list(
            method_name="listPhone",
            search_criteria={"name": "%"},
            returned_tags={"name": ""},
        )
        assert result == []

    def test_empty_return_dict(self):
        conn = _make_conn()
        conn.service.listPhone.return_value = {"return": None}
        result = conn.paginated_list(
            method_name="listPhone",
            search_criteria={"name": "%"},
            returned_tags={"name": ""},
        )
        assert result == []

    def test_empty_return_empty_dict(self):
        conn = _make_conn()
        conn.service.listPhone.return_value = {"return": {}}
        result = conn.paginated_list(
            method_name="listPhone",
            search_criteria={"name": "%"},
            returned_tags={"name": ""},
        )
        assert result == []

    def test_single_call_on_empty(self):
        conn = _make_conn()
        conn.service.listPhone.return_value = {"return": None}
        conn.paginated_list(
            method_name="listPhone",
            search_criteria={"name": "%"},
            returned_tags={"name": ""},
        )
        conn.service.listPhone.assert_called_once()


# ------------------------------------------------------------------
# 6. test_get_detail_success
# ------------------------------------------------------------------

class TestGetDetailSuccess:
    """Mock a get response, verify the inner object is returned."""

    def test_returns_inner_object(self):
        conn = _make_conn()
        phone_data = {
            "name": "SEP001122334455",
            "model": "Cisco 8845",
            "description": "Lobby phone",
        }
        conn.service.getPhone.return_value = {
            "return": {"phone": phone_data}
        }

        result = conn.get_detail("getPhone", name="SEP001122334455")
        assert result == phone_data

    def test_passes_kwargs_to_service(self):
        conn = _make_conn()
        conn.service.getLine.return_value = {
            "return": {"line": {"pattern": "1001"}}
        }

        conn.get_detail(
            "getLine",
            pattern="1001",
            routePartitionName="Internal_PT",
        )
        conn.service.getLine.assert_called_once_with(
            pattern="1001",
            routePartitionName="Internal_PT",
        )

    def test_skips_value_1_key(self):
        conn = _make_conn()
        conn.service.getUser.return_value = {
            "return": {"_value_1": None, "user": {"userid": "jsmith"}}
        }
        result = conn.get_detail("getUser", userid="jsmith")
        assert result == {"userid": "jsmith"}

    def test_returns_ret_when_no_inner_key(self):
        conn = _make_conn()
        # Edge case: return value has only _value_1 or all None values
        conn.service.getThing.return_value = {
            "return": {"_value_1": None}
        }
        # Loop skips _value_1, no other key found → falls through to return ret
        result = conn.get_detail("getThing")
        assert result == {"_value_1": None}


# ------------------------------------------------------------------
# 7. test_get_detail_error
# ------------------------------------------------------------------

class TestGetDetailError:
    """Mock an exception from the service method, verify None returned."""

    def test_returns_none_on_exception(self):
        conn = _make_conn()
        conn.service.getPhone.side_effect = Exception("Item not found")
        result = conn.get_detail("getPhone", name="NONEXISTENT")
        assert result is None

    def test_returns_none_on_fault(self):
        conn = _make_conn()
        conn.service.getLine.side_effect = Exception(
            "Item not valid: The specified Line was not found"
        )
        result = conn.get_detail("getLine", pattern="9999")
        assert result is None

    def test_logs_warning_on_error(self, caplog):
        conn = _make_conn()
        conn.service.getPhone.side_effect = Exception("Not found")
        with caplog.at_level("WARNING"):
            conn.get_detail("getPhone", name="BAD")
        assert "getPhone" in caplog.text
        assert "Not found" in caplog.text


# ------------------------------------------------------------------
# 8. test_extract_rows_various_formats
# ------------------------------------------------------------------

class TestExtractRowsVariousFormats:
    """Test the static _extract_rows with various zeep response formats."""

    def test_none_response(self):
        assert AXLConnection._extract_rows(None) == []

    def test_dict_with_list_value(self):
        """Standard AXL response: {'return': {'phone': [rows...]}}"""
        rows = [{"name": "SEP111"}, {"name": "SEP222"}]
        response = {"return": {"phone": rows}}
        assert AXLConnection._extract_rows(response) == rows

    def test_dict_with_single_item(self):
        """Single result: {'return': {'phone': {single_row}}}"""
        single = {"name": "SEP111"}
        response = {"return": {"phone": single}}
        result = AXLConnection._extract_rows(response)
        assert result == [single]

    def test_dict_with_empty_return(self):
        response = {"return": {}}
        assert AXLConnection._extract_rows(response) == []

    def test_dict_with_none_return(self):
        response = {"return": None}
        assert AXLConnection._extract_rows(response) == []

    def test_skips_value_1_key(self):
        """Zeep sometimes adds _value_1 key; should be skipped."""
        rows = [{"name": "a"}]
        response = {"return": {"_value_1": None, "row": rows}}
        assert AXLConnection._extract_rows(response) == rows

    def test_all_none_values_in_return(self):
        """All values are None — should return empty list."""
        response = {"return": {"phone": None, "_value_1": None}}
        assert AXLConnection._extract_rows(response) == []

    def test_zeep_object_with_getitem(self):
        """Zeep objects support __getitem__ but aren't plain dicts."""
        mock_response = MagicMock()
        # Remove .get so the code falls through to __getitem__
        del mock_response.get
        mock_response.__getitem__ = Mock(
            side_effect=lambda k: {"row": [{"col": "val"}]} if k == "return" else None
        )
        # The result from __getitem__ is a dict with one key
        result = AXLConnection._extract_rows(mock_response)
        assert result == [{"col": "val"}]

    def test_zeep_object_with_getitem_key_error(self):
        """Zeep object where __getitem__ raises KeyError."""
        mock_response = MagicMock()
        del mock_response.get
        mock_response.__getitem__ = Mock(side_effect=KeyError("return"))
        result = AXLConnection._extract_rows(mock_response)
        assert result == []
