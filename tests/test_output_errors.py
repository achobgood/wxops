"""Part D: Output formatting and error handling edge case tests."""

import json
import pytest
from io import StringIO
from unittest.mock import patch

from wxcli.output import (
    print_table,
    print_json,
    format_as_json,
    _resolve_accessor,
    auto_columns,
)
from tools.command_renderer import _render_error_handler
from wxcli.errors import WebexError, handle_rest_error


# ── print_table edge cases ───────────────────────────────────────────────────


class TestPrintTableEdgeCases:
    def test_empty_list(self, capsys):
        """Empty list → prints table with no rows (no traceback)."""
        print_table([], columns=[("ID", "id"), ("Name", "name")])
        captured = capsys.readouterr()
        # Should have header but no data rows; importantly, no traceback
        assert "ID" in captured.out
        assert "Name" in captured.out

    def test_null_fields_display_as_empty(self, capsys):
        """Items with None values → display as empty string, not 'None'."""
        data = [{"id": "1", "name": None, "status": "active"}]
        print_table(data, columns=[("ID", "id"), ("Name", "name"), ("Status", "status")])
        captured = capsys.readouterr()
        assert "None" not in captured.out
        assert "1" in captured.out
        assert "active" in captured.out

    def test_nested_dot_notation(self, capsys):
        """Column spec 'location.name' → extracts nested field."""
        data = [{"id": "1", "location": {"name": "HQ", "city": "NYC"}}]
        print_table(data, columns=[("ID", "id"), ("Location", "location.name")])
        captured = capsys.readouterr()
        assert "HQ" in captured.out

    def test_auto_detect_columns(self):
        """No explicit columns resolving → auto-detect from item's keys."""
        item = {"firstName": "Alice", "lastName": "Bob", "age": 30}
        cols = auto_columns(item)
        headers = [h for h, _ in cols]
        accessors = [a for _, a in cols]
        assert "firstName" in accessors
        assert "lastName" in accessors
        assert "age" in accessors
        # Headers should be title-cased with space insertion
        assert "First Name" in headers
        assert "Last Name" in headers

    def test_auto_detect_skips_nested(self):
        """Auto-detect columns skips dict/list values."""
        item = {"name": "Alice", "address": {"city": "NYC"}, "emails": ["a@b.com"]}
        cols = auto_columns(item)
        accessors = [a for _, a in cols]
        assert "name" in accessors
        assert "address" not in accessors
        assert "emails" not in accessors

    def test_auto_detect_fallback_on_empty_columns(self, capsys):
        """If configured columns all resolve to empty, auto-detect kicks in."""
        data = [{"firstName": "Alice", "email": "a@b.com"}]
        # These columns don't match the data
        print_table(data, columns=[("ID", "id"), ("Name", "name")])
        captured = capsys.readouterr()
        # Should have auto-detected and shown actual data
        assert "Alice" in captured.out

    def test_limit_parameter(self, capsys):
        """Limit parameter truncates output."""
        data = [{"id": str(i), "name": f"Item {i}"} for i in range(10)]
        print_table(data, columns=[("ID", "id"), ("Name", "name")], limit=3)
        captured = capsys.readouterr()
        assert "7 more" in captured.out

    def test_zero_limit_shows_all(self, capsys):
        """limit=0 shows all items."""
        data = [{"id": str(i), "name": f"Item {i}"} for i in range(5)]
        print_table(data, columns=[("ID", "id"), ("Name", "name")], limit=0)
        captured = capsys.readouterr()
        assert "more" not in captured.out
        for i in range(5):
            assert f"Item {i}" in captured.out


# ── print_json ───────────────────────────────────────────────────────────────


class TestPrintJson:
    def test_formats_correctly(self, capsys):
        """JSON output is indented, valid JSON."""
        data = {"id": "1", "name": "Test", "nested": {"key": "value"}}
        print_json(data)
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed == data

    def test_list_output(self, capsys):
        data = [{"id": "1"}, {"id": "2"}]
        print_json(data)
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert len(parsed) == 2

    def test_format_as_json_indented(self):
        data = {"key": "value"}
        result = format_as_json(data)
        assert "\n" in result  # indented
        assert json.loads(result) == data

    def test_format_as_json_model_dump(self):
        """Objects with model_dump (pydantic) are handled."""
        class FakeModel:
            def model_dump(self, by_alias=False):
                return {"id": "1", "name": "Test"}
        result = format_as_json(FakeModel())
        parsed = json.loads(result)
        assert parsed == {"id": "1", "name": "Test"}

    def test_format_as_json_list_of_models(self):
        class FakeModel:
            def model_dump(self, by_alias=False):
                return {"id": "1"}
        result = format_as_json([FakeModel(), {"id": "2"}, "raw"])
        parsed = json.loads(result)
        assert len(parsed) == 3
        assert parsed[0] == {"id": "1"}
        assert parsed[1] == {"id": "2"}
        assert parsed[2] == "raw"


# ── error handler known codes ────────────────────────────────────────────────


class TestErrorHandlerKnownCodes:
    """Each known error code → correct tip message from handle_rest_error."""

    def test_render_uses_handle_rest_error(self):
        handler = _render_error_handler()
        assert "WebexError" in handler
        assert "handle_rest_error" in handler

    def test_25008_missing_field(self, capsys):
        with pytest.raises(RuntimeError):
            handle_rest_error(WebexError('{"message":"error","errors":[{"errorCode":25008}]}'))
        captured = capsys.readouterr()
        assert "--json-body" in captured.err

    def test_4003_user_level_oauth(self, capsys):
        with pytest.raises(RuntimeError):
            handle_rest_error(WebexError('{"message":"Target user not authorized","errors":[{"errorCode":4003}]}'))
        captured = capsys.readouterr()
        assert "user-level OAuth" in captured.err

    def test_4003_user_not_found_no_false_tip(self, capsys):
        with pytest.raises(RuntimeError):
            handle_rest_error(WebexError('{"message":"User Not Found","errors":[{"errorCode":4003}]}'))
        captured = capsys.readouterr()
        assert "user-level OAuth" not in captured.err

    def test_4008_calling_license(self, capsys):
        with pytest.raises(RuntimeError):
            handle_rest_error(WebexError('{"message":"err","errors":[{"errorCode":4008}]}'))
        captured = capsys.readouterr()
        assert "Webex Calling license" in captured.err

    def test_25409_professional_license(self, capsys):
        with pytest.raises(RuntimeError):
            handle_rest_error(WebexError('{"message":"err","errors":[{"errorCode":25409}]}'))
        captured = capsys.readouterr()
        assert "Professional license" in captured.err

    def test_unknown_code_prints_error(self, capsys):
        with pytest.raises(RuntimeError):
            handle_rest_error(WebexError("some unknown error"))
        captured = capsys.readouterr()
        assert "some unknown error" in captured.err


# ── _resolve_accessor edge cases ─────────────────────────────────────────────


class TestResolveAccessorEdgeCases:
    def test_none_object(self):
        assert _resolve_accessor(None, "name") is None

    def test_empty_accessor(self):
        """Empty string accessor returns the object itself."""
        data = {"name": "test"}
        result = _resolve_accessor(data, "")
        # Splitting "" gives [""], which tries to .get("") on the dict
        # This is an edge case — the function returns None for missing keys
        assert result is None or result == data

    def test_deeply_nested(self):
        data = {"a": {"b": {"c": "deep"}}}
        assert _resolve_accessor(data, "a.b.c") == "deep"

    def test_list_returns_full_list(self):
        """No silent reduction — the full list is returned unresolved."""
        data = {"items": [1, 2, 3]}
        assert _resolve_accessor(data, "items") == [1, 2, 3]

    def test_empty_list(self):
        data = {"items": []}
        assert _resolve_accessor(data, "items") == []

    def test_mixed_dict_and_object(self):
        class Inner:
            city = "NYC"
        data = {"location": Inner()}
        assert _resolve_accessor(data, "location.city") == "NYC"


# ── null result guard ────────────────────────────────────────────────────────


class TestNullResultGuard:
    def test_format_json_none(self):
        """None value → valid JSON 'null'."""
        result = format_as_json(None)
        assert json.loads(result) is None

    def test_format_json_empty_dict(self):
        result = format_as_json({})
        assert json.loads(result) == {}

    def test_format_json_empty_list(self):
        result = format_as_json([])
        assert json.loads(result) == []

    def test_print_table_with_none_item_values(self, capsys):
        """Table with all-None row doesn't crash."""
        data = [{"id": None, "name": None}]
        print_table(data, columns=[("ID", "id"), ("Name", "name")])
        captured = capsys.readouterr()
        # Auto-detect may kick in since all values are None, using raw keys as headers
        assert "Id" in captured.out or "ID" in captured.out  # Header rendered


# ── transport-level network errors ───────────────────────────────────────────

import httpx
import pytest
import typer
from wxcli.errors import handle_network_error


def test_read_timeout_names_the_flag_that_fixes_it(capsys):
    with pytest.raises(typer.Exit) as exc:
        handle_network_error(httpx.ReadTimeout("timed out"))
    assert exc.value.exit_code == 1
    err = capsys.readouterr().err
    assert "ReadTimeout" in err
    assert "WXCLI_READ_TIMEOUT" in err


def test_connect_error_gets_a_connectivity_tip(capsys):
    with pytest.raises(typer.Exit):
        handle_network_error(httpx.ConnectError("no route to host"))
    err = capsys.readouterr().err
    assert "ConnectError" in err
    assert "Tip:" in err


def test_unknown_transport_error_still_exits_cleanly(capsys):
    class Weird(httpx.HTTPError):
        pass

    with pytest.raises(typer.Exit) as exc:
        handle_network_error(Weird("odd"))
    assert exc.value.exit_code == 1
    assert "Error:" in capsys.readouterr().err
