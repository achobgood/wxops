"""Part B: Command renderer tests — Endpoint → valid Python CLI code."""

import ast
import json
import pytest
from pathlib import Path

from tools.postman_parser import Endpoint, EndpointField
from tools.command_renderer import (
    render_command_file,
    folder_name_to_module,
    _render_list_command,
    _render_show_command,
    _render_create_command,
    _render_update_command,
    _render_delete_command,
    _render_action_command,
    _render_error_handler,
    _render_url_expr,
    _safe_func_name,
    _safe_param_name,
    _escape_help,
    PYTHON_KEYWORDS,
)
from tools.openapi_parser import parse_tag


FIXTURES = Path(__file__).parent / "fixtures"


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_endpoint(**kwargs) -> Endpoint:
    """Build an Endpoint with sensible defaults."""
    defaults = dict(
        name="Test Command",
        method="GET",
        url_path="things",
        path_vars=[],
        query_params=[],
        body_fields=[],
        command_type="list",
        command_name="list",
        raw_path=["things"],
        response_list_key="items",
        response_id_key=None,
        deprecated=False,
        json_body_example=None,
    )
    defaults.update(kwargs)
    return Endpoint(**defaults)


def _make_field(**kwargs) -> EndpointField:
    """Build an EndpointField with sensible defaults."""
    defaults = dict(
        name="fieldName",
        python_name="field-name",
        field_type="string",
        description="A field",
        required=False,
        default=None,
        enum_values=None,
    )
    defaults.update(kwargs)
    return EndpointField(**defaults)


# ── list command rendering ───────────────────────────────────────────────────


class TestListCommand:
    def test_has_pagination_params(self):
        ep = _make_endpoint(command_type="list")
        code = _render_list_command(ep, {})
        assert '"--limit"' in code
        assert '"--offset"' in code

    def test_has_table_output(self):
        ep = _make_endpoint(command_type="list")
        code = _render_list_command(ep, {})
        assert "print_table" in code
        assert '"--output"' in code

    def test_custom_table_columns(self):
        ep = _make_endpoint(command_type="list")
        overrides = {"list": {"table_columns": [["Phone", "phoneNumber"], ["State", "state"]]}}
        code = _render_list_command(ep, overrides)
        assert "phoneNumber" in code
        assert "Phone" in code

    def test_default_columns(self):
        ep = _make_endpoint(command_type="list")
        code = _render_list_command(ep, {})
        assert '"ID"' in code
        assert '"id"' in code
        assert '"Name"' in code
        assert '"name"' in code

    def test_path_vars_as_arguments(self):
        ep = _make_endpoint(
            command_type="list",
            url_path="things/{thingId}/items",
            path_vars=["thingId"],
        )
        code = _render_list_command(ep, {})
        assert "thing_id: str = typer.Argument" in code

    def test_query_params_rendered(self):
        ep = _make_endpoint(
            command_type="list",
            query_params=[
                _make_field(name="status", python_name="status", field_type="string"),
            ],
        )
        code = _render_list_command(ep, {})
        assert '"--status"' in code

    def test_response_list_key_used(self):
        ep = _make_endpoint(command_type="list", response_list_key="records")
        code = _render_list_command(ep, {})
        assert '"records"' in code

    def test_skips_duplicate_limit_param(self):
        """If query params already have 'limit', don't add another."""
        ep = _make_endpoint(
            command_type="list",
            query_params=[_make_field(name="limit", python_name="limit", field_type="number")],
        )
        code = _render_list_command(ep, {})
        # Should only have the query param version, not a second --limit
        assert code.count('"--limit"') == 1


# ── show command rendering ───────────────────────────────────────────────────


class TestShowCommand:
    def test_uses_path_params(self):
        ep = _make_endpoint(
            command_type="show",
            command_name="show",
            url_path="things/{thingId}",
            path_vars=["thingId"],
        )
        code = _render_show_command(ep)
        assert "thing_id: str = typer.Argument" in code

    def test_default_json_output(self):
        ep = _make_endpoint(command_type="show", command_name="show")
        code = _render_show_command(ep)
        assert '"json"' in code  # default output format
        assert "print_json" in code

    def test_table_output_support(self):
        ep = _make_endpoint(command_type="show", command_name="show")
        code = _render_show_command(ep)
        assert "print_table" in code

    def test_with_query_params(self):
        """Show command with query params includes params dict."""
        ep = _make_endpoint(
            command_type="show",
            command_name="show",
            query_params=[_make_field(name="orgId", python_name="org-id")],
        )
        code = _render_show_command(ep)
        assert '"--org-id"' in code
        assert "params=params" in code


# ── create command rendering ─────────────────────────────────────────────────


class TestCreateCommand:
    def test_builds_json_body(self):
        ep = _make_endpoint(
            command_type="create",
            command_name="create",
            method="POST",
            body_fields=[
                _make_field(name="name", python_name="name", required=True),
                _make_field(name="enabled", python_name="enabled", field_type="bool"),
            ],
        )
        code = _render_create_command(ep)
        assert "body" in code
        assert '"name"' in code
        assert "json.loads(json_body)" in code

    def test_json_body_option_present(self):
        ep = _make_endpoint(command_type="create", command_name="create", method="POST")
        code = _render_create_command(ep)
        assert '"--json-body"' in code

    def test_required_fields_use_ellipsis(self):
        ep = _make_endpoint(
            command_type="create",
            command_name="create",
            method="POST",
            body_fields=[_make_field(name="name", python_name="name", required=True)],
        )
        code = _render_create_command(ep)
        assert "typer.Option(...," in code

    def test_optional_fields_use_none(self):
        ep = _make_endpoint(
            command_type="create",
            command_name="create",
            method="POST",
            body_fields=[_make_field(name="desc", python_name="desc", required=False)],
        )
        code = _render_create_command(ep)
        assert "typer.Option(None," in code

    def test_bool_field_has_no_prefix(self):
        ep = _make_endpoint(
            command_type="create",
            command_name="create",
            method="POST",
            body_fields=[_make_field(name="enabled", python_name="enabled", field_type="bool")],
        )
        code = _render_create_command(ep)
        assert "--enabled/--no-enabled" in code

    def test_object_fields_skipped(self):
        ep = _make_endpoint(
            command_type="create",
            command_name="create",
            method="POST",
            body_fields=[
                _make_field(name="name", python_name="name"),
                _make_field(name="config", python_name="config", field_type="object"),
            ],
        )
        code = _render_create_command(ep)
        # 'config' shouldn't appear as a CLI option (only via --json-body)
        assert '"--config"' not in code

    def test_id_extraction(self):
        ep = _make_endpoint(
            command_type="create",
            command_name="create",
            method="POST",
            response_id_key="id",
        )
        code = _render_create_command(ep)
        assert "Created:" in code

    def test_custom_id_extraction(self):
        ep = _make_endpoint(
            command_type="create",
            command_name="create",
            method="POST",
            response_id_key="customId",
        )
        code = _render_create_command(ep)
        assert "customId" in code

    def test_with_query_params(self):
        """Create command with query params passes params to rest_post."""
        ep = _make_endpoint(
            command_type="create",
            command_name="create",
            method="POST",
            query_params=[_make_field(name="orgId", python_name="org-id")],
        )
        code = _render_create_command(ep)
        assert "params=params" in code


# ── update command rendering ─────────────────────────────────────────────────


class TestUpdateCommand:
    def test_builds_body(self):
        ep = _make_endpoint(
            command_type="update",
            command_name="update",
            method="PUT",
            path_vars=["thingId"],
            body_fields=[_make_field(name="name", python_name="name")],
        )
        code = _render_update_command(ep)
        assert "body" in code
        assert '"name"' in code
        assert "Updated." in code

    def test_patch_method(self):
        ep = _make_endpoint(
            command_type="update",
            command_name="update",
            method="PATCH",
            path_vars=["thingId"],
        )
        code = _render_update_command(ep)
        assert "rest_patch" in code

    def test_put_method(self):
        ep = _make_endpoint(
            command_type="update",
            command_name="update",
            method="PUT",
            path_vars=["thingId"],
        )
        code = _render_update_command(ep)
        assert "rest_put" in code

    def test_with_query_params(self):
        ep = _make_endpoint(
            command_type="update",
            command_name="update",
            method="PUT",
            query_params=[_make_field(name="orgId", python_name="org-id")],
        )
        code = _render_update_command(ep)
        assert "params=params" in code


# ── action command rendering ─────────────────────────────────────────────────


class TestActionCommand:
    def test_action_renders(self):
        ep = _make_endpoint(
            command_type="action",
            command_name="invoke-thing",
            method="POST",
            path_vars=["thingId"],
            body_fields=[_make_field(name="command", python_name="command")],
        )
        code = _render_action_command(ep)
        assert "rest_post" in code
        assert "print_json" in code
        assert '"--command"' in code

    def test_with_query_params(self):
        ep = _make_endpoint(
            command_type="action",
            command_name="invoke-thing",
            method="POST",
            query_params=[_make_field(name="orgId", python_name="org-id")],
        )
        code = _render_action_command(ep)
        assert "params=params" in code


# ── delete command rendering ─────────────────────────────────────────────────


class TestDeleteCommand:
    def test_has_path_params_only(self):
        ep = _make_endpoint(
            command_type="delete",
            command_name="delete",
            method="DELETE",
            url_path="things/{thingId}",
            path_vars=["thingId"],
        )
        code = _render_delete_command(ep)
        assert "thing_id: str = typer.Argument" in code
        assert '"--json-body"' not in code  # no body for delete

    def test_has_confirmation(self):
        ep = _make_endpoint(
            command_type="delete",
            command_name="delete",
            method="DELETE",
            path_vars=["thingId"],
        )
        code = _render_delete_command(ep)
        assert "typer.confirm" in code
        assert '"--force"' in code

    def test_no_path_vars_confirmation(self):
        ep = _make_endpoint(
            command_type="delete",
            command_name="delete",
            method="DELETE",
        )
        code = _render_delete_command(ep)
        assert "Delete this resource?" in code

    def test_with_query_params(self):
        ep = _make_endpoint(
            command_type="delete",
            command_name="delete",
            method="DELETE",
            path_vars=["thingId"],
            query_params=[_make_field(name="hasCxEssentials", python_name="has-cx-essentials")],
        )
        code = _render_delete_command(ep)
        assert "params=params" in code
        assert '"--has-cx-essentials"' in code


# ── _render_query_params ─────────────────────────────────────────────────────


class TestRenderQueryParams:
    def test_required_query_param(self):
        from tools.command_renderer import _render_query_params
        ep = _make_endpoint(
            query_params=[_make_field(name="orgId", python_name="org-id", required=True)],
        )
        defs, build = _render_query_params(ep)
        assert len(defs) == 1
        assert "typer.Option(...," in defs[0]
        assert len(build) > 1  # params = {} + at least one if

    def test_optional_query_param(self):
        from tools.command_renderer import _render_query_params
        ep = _make_endpoint(
            query_params=[_make_field(name="status", python_name="status", required=False)],
        )
        defs, build = _render_query_params(ep)
        assert "typer.Option(None," in defs[0]

    def test_empty_query_params(self):
        from tools.command_renderer import _render_query_params
        ep = _make_endpoint(query_params=[])
        defs, build = _render_query_params(ep)
        assert defs == []
        assert build == []


# ── error handler ────────────────────────────────────────────────────────────


class TestErrorHandler:
    def test_error_handler_present_in_all_types(self):
        """All command types include RestError catch block."""
        for cmd_type, renderer in [
            ("list", _render_list_command),
            ("show", _render_show_command),
            ("create", _render_create_command),
            ("update", _render_update_command),
            ("delete", _render_delete_command),
            ("action", _render_action_command),
        ]:
            ep = _make_endpoint(
                command_type=cmd_type,
                command_name=cmd_type,
                method={"list": "GET", "show": "GET", "create": "POST",
                        "update": "PUT", "delete": "DELETE", "action": "POST"}[cmd_type],
            )
            code = renderer(ep, {})
            assert "RestError" in code, f"No RestError handler in {cmd_type} command"
            assert "typer.Exit(1)" in code, f"No Exit(1) in {cmd_type} command"

    def test_error_handler_known_codes(self):
        handler = _render_error_handler()
        assert "25008" in handler
        assert "4003" in handler
        assert "4008" in handler
        assert "25409" in handler

    def test_error_handler_tips(self):
        handler = _render_error_handler()
        assert "user-level OAuth" in handler
        assert "Webex Calling license" in handler
        assert "Professional license" in handler
        assert "--json-body" in handler


# ── generated code validity ──────────────────────────────────────────────────


class TestGeneratedCodeValidity:
    def test_generated_code_is_valid_python(self):
        """Render a full command file, compile with ast.parse()."""
        with open(FIXTURES / "mini-openapi.json") as f:
            spec = json.load(f)
        endpoints, _ = parse_tag("Things", spec, omit_query_params=["orgId"])
        code = render_command_file("Things", endpoints, {})
        # Should not raise SyntaxError
        ast.parse(code)

    def test_multiple_tags_valid_python(self):
        """Each tag in the fixture produces valid Python."""
        with open(FIXTURES / "mini-openapi.json") as f:
            spec = json.load(f)
        for tag in ["Things", "Combined", "Nested", "Keywords", "Quoted"]:
            endpoints, _ = parse_tag(tag, spec, omit_query_params=["orgId"])
            if endpoints:
                code = render_command_file(tag, endpoints, {})
                try:
                    ast.parse(code)
                except SyntaxError as e:
                    pytest.fail(f"Tag '{tag}' generated invalid Python: {e}")


# ── help text escaping ───────────────────────────────────────────────────────


class TestHelpTextEscaping:
    def test_quotes_escaped(self):
        assert '\\"' in _escape_help('He said "hello"')

    def test_newlines_replaced(self):
        result = _escape_help("line1\nline2")
        assert "\n" not in result
        assert "line1 line2" == result

    def test_backslashes_escaped(self):
        result = _escape_help("path\\to\\thing")
        assert "\\\\" in result

    def test_quoted_things_tag_valid(self):
        """Descriptions with quotes/newlines don't break generated code."""
        with open(FIXTURES / "mini-openapi.json") as f:
            spec = json.load(f)
        endpoints, _ = parse_tag("Quoted", spec)
        if endpoints:
            code = render_command_file("Quoted", endpoints, {})
            ast.parse(code)


# ── kebab-case flags ─────────────────────────────────────────────────────────


class TestKebabCaseFlags:
    def test_camel_to_kebab_flags(self):
        ep = _make_endpoint(
            command_type="create",
            command_name="create",
            method="POST",
            body_fields=[
                _make_field(name="firstName", python_name="first-name"),
                _make_field(name="lastName", python_name="last-name"),
            ],
        )
        code = _render_create_command(ep)
        assert '"--first-name"' in code
        assert '"--last-name"' in code


# ── Python keyword collision ─────────────────────────────────────────────────


class TestPythonKeywordCollision:
    def test_safe_func_name_keyword(self):
        assert _safe_func_name("list") == "cmd_list"
        assert _safe_func_name("type") == "cmd_type"
        assert _safe_func_name("import") == "cmd_import"

    def test_safe_func_name_normal(self):
        assert _safe_func_name("show") == "show"
        assert _safe_func_name("create-thing") == "create_thing"

    def test_safe_param_name_keyword(self):
        assert _safe_param_name("list") == "list_param"
        assert _safe_param_name("type") == "type_param"

    def test_safe_param_name_normal(self):
        assert _safe_param_name("name") == "name"
        assert _safe_param_name("first-name") == "first_name"

    def test_keyword_fields_in_generated_code(self):
        """Fields named 'list' or 'type' produce valid Python code."""
        with open(FIXTURES / "mini-openapi.json") as f:
            spec = json.load(f)
        endpoints, _ = parse_tag("Keywords", spec)
        if endpoints:
            code = render_command_file("Keywords", endpoints, {})
            ast.parse(code)  # Would fail if keywords not escaped


# ── json_body_example in help ────────────────────────────────────────────────


class TestJsonBodyExampleInHelp:
    def test_json_body_example_in_docstring(self):
        ep = _make_endpoint(
            command_type="create",
            command_name="create",
            method="POST",
            json_body_example='{"name":"...","config":{"timeout":0}}',
        )
        code = _render_create_command(ep)
        assert "--json-body" in code
        assert "config" in code


# ── URL rendering ────────────────────────────────────────────────────────────


class TestUrlRendering:
    def test_standard_url(self):
        url = _render_url_expr("things/{thingId}", ["thingId"])
        assert "webexapis.com/v1/things/{thing_id}" in url

    def test_scim_url_no_v1(self):
        url = _render_url_expr("identity/v1/scim", [])
        assert "webexapis.com/identity/v1/scim" in url
        assert "/v1/v1/" not in url  # shouldn't double v1

    def test_analytics_url(self):
        url = _render_url_expr("cdr_feed/records", [])
        assert "analytics-calling.webexapis.com" in url


# ── folder_name_to_module ───────────────────────────────────────────────────


class TestFolderNameToModule:
    def test_simple_name(self):
        module, cli = folder_name_to_module("Things")
        assert module == "things"
        assert cli == "things"

    def test_features_prefix_stripped(self):
        module, cli = folder_name_to_module("Features:  Auto Attendant")
        assert module == "auto_attendant"
        assert cli == "auto-attendant"

    def test_pagination_suffix_stripped(self):
        module, cli = folder_name_to_module("User Call Settings (1/2)")
        assert module == "user_call_settings"
        assert cli == "user-call-settings"


# ── orgId auto-inject ────────────────────────────────────────────────────────


def test_render_show_command_orgid_only_param():
    """When orgId is the only query param, params dict is still created."""
    ep = Endpoint(
        name="Get Widget",
        method="GET",
        url_path="widgets/{widgetId}",
        path_vars=["widgetId"],
        query_params=[],
        body_fields=[],
        command_type="show",
        command_name="show",
        auto_inject_params=["orgId"],
    )
    code = render_command_file("Test Widgets", [ep], {})
    assert "get_org_id" in code
    assert "params = {}" in code
    assert 'params["orgId"]' in code
    assert "params=params" in code


def test_render_show_command_no_orgid():
    """When no auto_inject_params, no params dict for paramless show."""
    ep = Endpoint(
        name="Get Widget",
        method="GET",
        url_path="widgets/{widgetId}",
        path_vars=["widgetId"],
        query_params=[],
        body_fields=[],
        command_type="show",
        command_name="show",
        auto_inject_params=[],
    )
    code = render_command_file("Test Widgets", [ep], {})
    assert "get_org_id" not in code
    assert "rest_get(url)" in code


def test_render_delete_command_orgid_injection():
    """Delete command with orgId auto-inject creates params dict."""
    ep = Endpoint(
        name="Delete Widget",
        method="DELETE",
        url_path="widgets/{widgetId}",
        path_vars=["widgetId"],
        query_params=[],
        body_fields=[],
        command_type="delete",
        command_name="delete",
        auto_inject_params=["orgId"],
    )
    code = render_command_file("Test Widgets", [ep], {})
    assert "get_org_id" in code
    assert 'params["orgId"]' in code
    assert "params=params" in code
