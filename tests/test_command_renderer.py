"""Part B: Command renderer tests — Endpoint → valid Python CLI code."""

import ast
import json
import pytest
from pathlib import Path

from tools.postman_parser import Endpoint, EndpointField, ResponseField
from tools.command_renderer import (
    render_command_file,
    folder_name_to_module,
    _column_header,
    _derive_default_columns,
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
    ReservedParamCollisionError,
    UnboundUrlPlaceholderError,
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
        assert "emit(items" in code  # routes through the shared output pipeline
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


# ── schema-derived default columns ───────────────────────────────────────────


def _rf(name, field_type="string", required=False) -> ResponseField:
    return ResponseField(name=name, field_type=field_type, required=required)


class TestSchemaDerivedColumns:
    """The ID/Name fallback is wrong for most Webex list endpoints — they return
    phoneNumber/clusterId/displayName and no id or name at all, so the table
    rendered blank while -o json was correct. Default columns now come from the
    endpoint's own 200 item schema."""

    def test_derives_columns_when_schema_has_no_id_or_name(self):
        ep = _make_endpoint(response_item_fields={"phoneNumbers": [
            _rf("phoneNumber"), _rf("extension"), _rf("state"),
        ]}, response_list_key="phoneNumbers")
        assert _derive_default_columns(ep) == [
            ("Phone Number", "phoneNumber"),
            ("Extension", "extension"),
            ("State", "state"),
        ]

    def test_prefers_id_and_a_human_readable_label(self):
        ep = _make_endpoint(response_item_fields={"items": [
            _rf("created"), _rf("displayName"), _rf("id"), _rf("email"),
        ]})
        cols = _derive_default_columns(ep)
        assert cols[0] == ("ID", "id")
        assert cols[1] == ("Display Name", "displayName")

    def test_falls_back_to_an_id_suffixed_field(self):
        ep = _make_endpoint(response_item_fields={"items": [
            _rf("clusterId"), _rf("clusterName"), _rf("status"),
        ]})
        cols = _derive_default_columns(ep)
        assert cols[0] == ("Cluster ID", "clusterId")
        assert cols[1] == ("Cluster Name", "clusterName")

    def test_skips_nested_objects_and_arrays(self):
        """A dict or list renders as a Python repr in a table cell — useless."""
        ep = _make_endpoint(response_item_fields={"items": [
            _rf("id"), _rf("numbers", "array"), _rf("owner", "object"),
            _rf("type"),
        ]})
        assert [a for _, a in _derive_default_columns(ep)] == ["id", "type"]

    def test_caps_the_column_count(self):
        ep = _make_endpoint(response_item_fields={"items": [
            _rf(f"field{i}") for i in range(12)
        ]})
        assert len(_derive_default_columns(ep)) <= 5

    def test_drops_org_id_which_is_identical_on_every_row(self):
        ep = _make_endpoint(response_item_fields={"items": [
            _rf("orgId"), _rf("id"), _rf("name"), _rf("status"),
        ]})
        assert "orgId" not in [a for _, a in _derive_default_columns(ep)]

    def test_keeps_org_id_when_it_is_all_there_is(self):
        ep = _make_endpoint(response_item_fields={"items": [
            _rf("orgId"), _rf("clusters", "array"),
        ]})
        assert [a for _, a in _derive_default_columns(ep)] == ["orgId"]

    def test_returns_none_without_a_resolvable_schema(self):
        assert _derive_default_columns(_make_endpoint()) is None

    def test_returns_none_when_the_item_has_no_scalars(self):
        ep = _make_endpoint(response_item_fields={"items": [
            _rf("clusters", "array"), _rf("meta", "object"),
        ]})
        assert _derive_default_columns(ep) is None

    def test_keys_off_the_effective_list_key(self):
        """response_list_keys overrides run after parse; the columns must
        follow the key the generated code actually extracts."""
        ep = _make_endpoint(
            response_list_key="records",
            response_item_fields={
                "items": [_rf("wrong")],
                "records": [_rf("callId"), _rf("duration")],
            },
        )
        assert [a for _, a in _derive_default_columns(ep)] == ["callId", "duration"]

    def test_rendered_command_uses_the_derived_columns(self):
        ep = _make_endpoint(response_item_fields={"items": [
            _rf("phoneNumber"), _rf("state"),
        ]})
        code = _render_list_command(ep, {})
        assert "'phoneNumber'" in code
        assert "('ID', 'id')" not in code

    def test_explicit_overrides_still_win(self):
        ep = _make_endpoint(response_item_fields={"items": [_rf("phoneNumber")]})
        per_cmd = {"table_columns": {"list": [["State", "state"]]}}
        assert "'state'" in _render_list_command(ep, per_cmd)
        old_style = {"list": {"table_columns": [["State", "state"]]}}
        assert "'state'" in _render_list_command(ep, old_style)

    def test_falls_back_to_id_name_when_no_schema_resolves(self):
        code = _render_list_command(_make_endpoint(), {})
        assert '("ID", "id")' in code and '("Name", "name")' in code


class TestColumnHeader:
    @pytest.mark.parametrize("field,header", [
        ("id", "ID"),
        ("name", "Name"),
        ("phoneNumber", "Phone Number"),
        ("personId", "Person ID"),
        ("isMainNumber", "Is Main Number"),
        ("esn", "ESN"),
        ("routeGroupId", "Route Group ID"),
        ("siteUrl", "Site URL"),
    ])
    def test_headers(self, field, header):
        assert _column_header(field) == header


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
        assert "emit(result" in code

    def test_table_output_support(self):
        """Table rendering is handled inside emit() (Task 1's dict branch)."""
        ep = _make_endpoint(command_type="show", command_name="show")
        code = _render_show_command(ep)
        assert "table|json|text" in code  # --output advertises table as a choice

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
        assert "load_json_body(json_body)" in code

    def test_json_body_option_present(self):
        ep = _make_endpoint(command_type="create", command_name="create", method="POST")
        code = _render_create_command(ep)
        assert '"--json-body"' in code

    def test_required_fields_use_ellipsis(self):
        """Required body fields use Option(None, ...) with runtime validation (was Option(...)).

        The generator switched from typer's built-in required handling (Option(..., ...)) to
        runtime validation via `_missing` check so that --json-body can supply the field
        without requiring the CLI flag. The help text is prefixed "(required)" and a
        post-body `_missing` block raises Exit(1) if the field is absent.
        """
        ep = _make_endpoint(
            command_type="create",
            command_name="create",
            method="POST",
            body_fields=[_make_field(name="name", python_name="name", required=True)],
        )
        code = _render_create_command(ep)
        # Required marker is in the help text
        assert '"--name"' in code
        assert "(required)" in code
        # Runtime validation of required fields is present
        assert "_missing" in code
        assert "'name'" in code or '"name"' in code

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
        assert "emit(result" in code
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
            assert "WebexError" in code, f"No WebexError handler in {cmd_type} command"
            assert "handle_rest_error" in code, f"No handle_rest_error in {cmd_type} command"

    def test_error_handler_delegates_to_handle_rest_error(self):
        handler = _render_error_handler()
        assert "WebexError" in handler
        assert "handle_rest_error" in handler


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


# ── --output / --fields uniformity (Task 3) ─────────────────────────────────

import re
import pytest
from tools.command_renderer import _render_output_options, render_command_file


def test_output_options_include_fields():
    assert "--fields" in "\n".join(_render_output_options("json"))


def test_output_options_respect_the_default():
    assert '"json", "--output"' in "\n".join(_render_output_options("json"))
    assert '"table", "--output"' in "\n".join(_render_output_options("table"))
    assert '"id", "--output"' in "\n".join(_render_output_options("id"))


def test_create_default_stays_id_but_offers_table():
    assert "id|table|json|text" in "\n".join(_render_output_options("id"))


def test_list_and_show_offer_the_same_set():
    assert "table|json|text" in "\n".join(_render_output_options("table"))
    assert "table|json|text" in "\n".join(_render_output_options("json"))


@pytest.mark.parametrize("ctype,cname,method", [
    ("list", "list", "GET"),
    ("show", "show", "GET"),
    ("create", "create", "POST"),
    ("update", "update", "PUT"),
    ("delete", "delete", "DELETE"),
    ("action", "do-thing", "POST"),
])
def test_every_command_type_declares_output_and_fields(ctype, cname, method):
    """The core defect: update/delete/action had no --output at all."""
    ep = _make_endpoint(command_type=ctype, command_name=cname, method=method)
    code = render_command_file("demo", [ep], {})
    assert '"--output"' in code, f"{ctype} has no --output"
    assert '"--fields"' in code, f"{ctype} has no --fields"
    compile(code, "<generated>", "exec")


def test_rendered_list_command_routes_through_emit():
    ep = _make_endpoint(command_type="list", command_name="list", paginates=True)
    code = render_command_file("demo", [ep], {})
    assert "emit(items, output=output, fields=fields" in code
    assert "from wxcli.common import emit" in code


def test_rendered_update_command_routes_through_emit():
    ep = _make_endpoint(command_type="update", command_name="update", method="PUT")
    code = render_command_file("demo", [ep], {})
    assert "emit(result, output=output, fields=fields)" in code
    assert "Updated." in code  # issue #20's success message survives (see Step 4's Decision)


def test_rendered_delete_command_assigns_result_and_emits():
    """Pins the revision-3 fix: delete_call never assigned `result`, so the
    rev-2 tail was a NameError on every successful delete — invisible to
    compile(), which only catches syntax."""
    ep = _make_endpoint(command_type="delete", command_name="delete",
                        method="DELETE", path_vars=["thingId"])
    code = render_command_file("demo", [ep], {})
    assert "result = api.session.rest_delete(" in code
    assert "emit(result, output=output, fields=fields)" in code
    assert "Deleted:" in code  # the no-body case keeps its message


def test_create_still_prints_a_bare_id_by_default():
    ep = _make_endpoint(command_type="create", command_name="create", method="POST")
    code = render_command_file("demo", [ep], {})
    assert '"id", "--output"' in code


def test_no_duplicate_option_declarations():
    """Guards against colliding with a spec-derived flag such as --page-size."""
    ep = _make_endpoint(command_type="list", command_name="list", paginates=True)
    code = render_command_file("demo", [ep], {})
    flags = re.findall(r'"(--[a-z0-9-]+)"', code)
    dupes = sorted({f for f in flags if flags.count(f) > 1})
    assert dupes == [], f"duplicate flag declarations: {dupes}"


def test_spec_query_and_filter_params_are_untouched():
    """--fields must not disturb the flags cc-search/fs-flows/CC already own."""
    for taken in ("query", "filter"):
        ep = _make_endpoint(
            command_type="show", command_name="show",
            query_params=[_make_field(name=taken, python_name=taken, required=True)],
        )
        code = render_command_file("demo", [ep], {})
        assert code.count(f'"--{taken}"') == 1
        assert '"--fields"' in code
        compile(code, "<generated>", "exec")


# ── reserved --fields/--output collision guard ──────────────────────────────
#
# Unlike "query"/"filter" above (different flag *text*, no collision), a spec
# parameter whose python name is literally "fields" or "output" collides with
# the option _render_output_options() adds to every command under that exact
# name. One such param exists today: CC Functions GET /v1/{orgId}/functions
# declares a "fields" query param, inert only because the Functions tag is
# skip-listed. These tests prove that if that tag is ever un-skipped (or any
# future spec adds "output"), the generator fails loudly at generation time
# instead of emitting a function with a duplicate argument.


class TestReservedParamCollision:
    def test_spec_query_param_named_fields_raises(self):
        ep = _make_endpoint(
            command_type="list", command_name="list",
            query_params=[_make_field(name="fields", python_name="fields")],
        )
        with pytest.raises(ReservedParamCollisionError, match="fields"):
            _render_list_command(ep, {})

    def test_spec_query_param_named_output_raises(self):
        ep = _make_endpoint(
            command_type="show", command_name="show",
            query_params=[_make_field(name="output", python_name="output")],
        )
        with pytest.raises(ReservedParamCollisionError, match="output"):
            _render_show_command(ep)

    def test_message_names_the_offending_endpoint(self):
        """The exception must be actionable: method, path, command name, and
        the colliding spec parameter name — not a bare traceback."""
        ep = _make_endpoint(
            command_type="list", command_name="list-functions", method="GET",
            url_path="{orgId}/functions",
            query_params=[_make_field(name="fields", python_name="fields")],
        )
        with pytest.raises(ReservedParamCollisionError) as exc_info:
            _render_list_command(ep, {})
        message = str(exc_info.value)
        assert "GET" in message
        assert "{orgId}/functions" in message
        assert "list-functions" in message
        assert "fields" in message

    def test_body_field_named_fields_raises(self):
        ep = _make_endpoint(
            command_type="create", command_name="create", method="POST",
            body_fields=[_make_field(name="fields", python_name="fields")],
        )
        with pytest.raises(ReservedParamCollisionError, match="fields"):
            _render_create_command(ep)

    def test_object_typed_body_field_named_fields_does_not_raise(self):
        """Object/array-typed body fields are never rendered as CLI flags —
        only settable via --json-body — so they can't actually collide with
        --fields and must not trip the guard."""
        ep = _make_endpoint(
            command_type="create", command_name="create", method="POST",
            body_fields=[_make_field(name="fields", python_name="fields", field_type="object")],
        )
        code = _render_create_command(ep)  # must not raise
        assert '"--fields"' in code

    def test_ordinary_query_param_does_not_raise(self):
        ep = _make_endpoint(
            command_type="list", command_name="list",
            query_params=[_make_field(name="status", python_name="status")],
        )
        code = _render_list_command(ep, {})  # must not raise
        assert '"--status"' in code

    def test_paging_names_are_exempt(self):
        """limit/max/start/offset are already folded into the renderer's own
        --limit/--offset flags with equivalent semantics
        (_SUPPRESS_SPEC_PAGING_NAMES). The new guard must not re-flag them —
        doing so would turn test_skips_duplicate_limit_param's handled case
        into a hard failure."""
        ep = _make_endpoint(
            command_type="list", command_name="list",
            query_params=[_make_field(name="limit", python_name="limit", field_type="number")],
        )
        code = _render_list_command(ep, {})  # must not raise
        assert code.count('"--limit"') == 1


def _generated_module_paths():
    """Scan scope = the _registry.py manifest: generated modules only.

    NOT a bare glob of src/wxcli/commands/*.py — that sweeps in (a) hand-
    written cucm.py, whose preflight/decisions/assess flags legitimately say
    "Output format: table or json" / "html or csv" (cucm.py:1448, 1566, 2933)
    and whose named map/mark-complete/mark-failed commands (cucm.py:1235,
    2391, 2426) have no --output by design, and (b) gitignored dev-only fs_*
    modules that Task 7's regen never touches. With the glob, both tests
    below fail forever once their xfail markers come off.
    """
    reg = open("src/wxcli/commands/_registry.py").read()
    return [f"src/wxcli/commands/{m}.py" for m in re.findall(r'\("([a-z0-9_]+)",', reg)]


def test_no_generated_command_offers_a_narrow_output_set():
    allowed = {"table|json|text", "id|table|json|text"}
    bad = []
    for path in _generated_module_paths():
        for m in re.finditer(r'help="Output format: ([^"]+)"', open(path).read()):
            if m.group(1) not in allowed:
                bad.append(f"{path}: {m.group(1)}")
    assert bad == [], f"narrow --output sets remain: {bad[:10]}"


def test_no_generated_command_lacks_output():
    """update/delete/action must stop being the exception."""
    bad = []
    for path in _generated_module_paths():
        src = open(path).read()
        for m in re.finditer(r'@app\.command\("([^"]+)"\)\ndef [a-z_0-9]+\((.*?)\n\):', src, re.S):
            if '"--output"' not in m.group(2):
                bad.append(f"{path}:{m.group(1)}")
    assert bad == [], f"commands with no --output: {len(bad)} e.g. {bad[:5]}"


# ── --generate-json-body / widened --json-body (Task 4) ────────────────────


def _create_ep():
    return _make_endpoint(
        command_type="create", command_name="create", method="POST",
        json_body_example='{"name":"...","enabled":true}',
    )


def test_create_command_declares_generate_json_body():
    assert "--generate-json-body" in render_command_file("demo", [_create_ep()], {})


def test_generate_json_body_exits_before_get_api():
    code = render_command_file("demo", [_create_ep()], {})
    assert code.index("if generate_json_body:") < code.index("api = get_api(")


def test_skeleton_is_pretty_printed():
    code = render_command_file("demo", [_create_ep()], {})
    assert "indent=2" in code
    assert "_BODY_SKELETON" in code


def test_command_without_a_body_has_no_flag():
    ep = _make_endpoint(command_type="show", command_name="show")
    assert "--generate-json-body" not in render_command_file("demo", [ep], {})


def test_json_body_routes_through_load_json_body():
    """--generate-json-body's output must be feedable via file://."""
    code = render_command_file("demo", [_create_ep()], {})
    assert "body = load_json_body(json_body)" in code
    assert "body = json.loads(json_body)" not in code


def test_json_body_help_mentions_file_input():
    assert "file://" in render_command_file("demo", [_create_ep()], {})


# ── Fix round 1: delete gets --generate-json-body too ───────────────────────


def test_delete_with_body_declares_generate_json_body():
    """Finding 1: openapi_parser now includes 'delete' in the json_body_example
    gate (tools/openapi_parser.py), so a delete endpoint with a body gets
    --generate-json-body just like create/update/action, and it still
    short-circuits before get_api."""
    ep = _make_endpoint(
        command_type="delete", command_name="delete", method="DELETE",
        path_vars=["thingId"],
        body_fields=[_make_field(name="supervisorIds", python_name="supervisor-ids", field_type="array")],
        json_body_example='{"supervisorIds":["..."]}',
    )
    code = render_command_file("demo", [ep], {})
    assert "--generate-json-body" in code
    assert code.index("if generate_json_body:") < code.index("api = get_api(")


def test_delete_generate_flag_and_check_share_one_gate():
    """Finding 2: the --generate-json-body PARAM and the early-exit CHECK in
    _render_delete_command must never disagree. A delete endpoint built with
    json_body_example set but no body_fields (has_body=False) previously
    rendered the early-exit `if generate_json_body:` block without declaring
    the parameter — a NameError at runtime, latent only because Finding 1's
    bug made delete's json_body_example always None in practice."""
    ep = _make_endpoint(
        command_type="delete", command_name="delete", method="DELETE",
        path_vars=["thingId"],
        body_fields=[],
        json_body_example='{"foo":"bar"}',
    )
    code = render_command_file("demo", [ep], {})
    declares_param = "generate_json_body: bool" in code
    declares_check = "if generate_json_body:" in code
    assert declares_param == declares_check, "param and early-exit check disagree — NameError risk"


# ── transport-error clause (Task 5) ─────────────────────────────────────────


def test_generated_commands_catch_transport_errors():
    ep = _make_endpoint(command_type="list", command_name="list")
    code = render_command_file("demo", [ep], {})
    assert "except httpx.HTTPError as e:" in code
    assert "handle_network_error(e)" in code
    assert "import httpx" in code
    compile(code, "<generated>", "exec")


def test_webex_error_is_still_caught_first():
    """WebexError must be handled before the broader transport clause."""
    ep = _make_endpoint(command_type="list", command_name="list")
    code = render_command_file("demo", [ep], {})
    assert code.index("except WebexError as e:") < code.index("except httpx.HTTPError as e:")
    compile(code, "<generated>", "exec")


# ── Finding 9: structured no-body result on update/delete ──────────────────
#
# --output defaults to "json" on update/delete, but Webex PUT/DELETE mostly
# return 204 with no body — the common case — so the no-body branch used to
# always print the issue #20 prose line even under -o json, and piping to
# jq broke. table/id keep the exact prose message; json/text/--fields now
# get a small {"status": ..., "id": ...} object instead, routed through
# emit() so --fields still applies to it.


class TestNoBodyStructuredResult:
    def test_update_default_output_gets_structured_result(self):
        ep = _make_endpoint(
            command_type="update", command_name="update", method="PUT",
            path_vars=["thingId"],
        )
        code = render_command_file("demo", [ep], {})
        assert 'elif output in ("table", "id") and not fields:' in code
        assert 'typer.echo(f"Updated.")' in code  # table/id prose survives
        assert 'emit({"status": "updated", "id": thing_id}, output=output, fields=fields)' in code
        compile(code, "<generated>", "exec")

    def test_delete_default_output_gets_structured_result(self):
        ep = _make_endpoint(
            command_type="delete", command_name="delete", method="DELETE",
            path_vars=["thingId"],
        )
        code = render_command_file("demo", [ep], {})
        assert 'elif output in ("table", "id") and not fields:' in code
        assert 'typer.echo(f"Deleted: {thing_id}")' in code  # table/id prose survives
        assert 'emit({"status": "deleted", "id": thing_id}, output=output, fields=fields)' in code
        compile(code, "<generated>", "exec")

    def test_update_structured_status_follows_delete_shaped_semantics(self):
        """Issue #20: a delete-shaped PUT (real_semantics='delete') must
        report status='deleted' in the structured result, not 'updated' —
        the SAME semantics the kept prose line already uses. Reuses
        _success_message rather than hardcoding the verb."""
        ep = _make_endpoint(
            command_type="update", command_name="update-access-codes", method="PUT",
            path_vars=["personId"], real_semantics="delete",
        )
        code = render_command_file("demo", [ep], {})
        assert 'typer.echo(f"Deleted.")' in code
        assert '{"status": "deleted", "id": person_id}' in code
        assert '"status": "updated"' not in code
        compile(code, "<generated>", "exec")

    def test_create_destructive_variant_message_unaffected(self):
        """Scope guard: the create renderer's destructive-POST message
        ('Purged.') is untouched by this change — only update/delete grew
        the machine-format branch."""
        ep = _make_endpoint(
            command_type="create", command_name="create-purge-inactive-entities",
            method="POST", real_semantics="purge",
        )
        code = _render_create_command(ep)
        assert 'typer.echo("Purged.")' in code
        assert '"status": "purged"' not in code

    def test_update_no_path_vars_structured_result_omits_id(self):
        ep = _make_endpoint(command_type="update", command_name="update", method="PUT")
        code = render_command_file("demo", [ep], {})
        assert 'emit({"status": "updated"}, output=output, fields=fields)' in code

    def test_delete_no_path_vars_structured_result_omits_id(self):
        ep = _make_endpoint(command_type="delete", command_name="delete", method="DELETE")
        code = render_command_file("demo", [ep], {})
        assert 'emit({"status": "deleted"}, output=output, fields=fields)' in code

    def test_no_body_branches_ordered_result_then_prose_then_structured(self):
        ep = _make_endpoint(
            command_type="update", command_name="update", method="PUT",
            path_vars=["thingId"],
        )
        code = render_command_file("demo", [ep], {})
        i_if = code.index("if result:")
        i_elif = code.index('elif output in ("table", "id")')
        i_else = code.index("else:", i_elif)
        assert i_if < i_elif < i_else

    def test_protected_update_test_string_still_present(self):
        """Guards the exact scenario TestUpdateCommand::test_builds_body
        checks — 'Updated.' must remain literally in the code even though
        it now lives in an elif branch, not a bare else."""
        ep = _make_endpoint(
            command_type="update", command_name="update", method="PUT",
            path_vars=["thingId"],
            body_fields=[_make_field(name="name", python_name="name")],
        )
        code = _render_update_command(ep)
        assert "Updated." in code


# ── Finding 11: unbound URL placeholder guard ───────────────────────────────
#
# Live bug: webex-meetings.json's PUT
# /admin/meeting/config/trackingCodes/{trackingCodeId} declares an empty
# `parameters` array, so ep.path_vars was [] while the URL template still
# carried {trackingCodeId} — every call raised a bare NameError at runtime,
# invisible to compile(). render_command_file now infers the missing var
# from a sibling operation on the identical path (GET/DELETE both declare
# it); _render_url_expr's guard is the backstop when no sibling has it either.


class TestUnboundUrlPlaceholderGuard:
    def test_unbound_placeholder_raises_with_clear_message(self):
        """Calling the renderer directly bypasses render_command_file's
        sibling inference, so the raw spec defect (path_vars empty, URL
        template still carrying the placeholder) must raise loudly."""
        ep = _make_endpoint(
            command_type="update", command_name="update", method="PUT",
            url_path="things/{thingId}", path_vars=[],
        )
        with pytest.raises(UnboundUrlPlaceholderError) as exc_info:
            _render_update_command(ep)
        message = str(exc_info.value)
        assert "PUT" in message
        assert "things/{thingId}" in message
        assert "thingId" in message

    def test_normal_endpoint_still_renders_and_compiles(self):
        ep = _make_endpoint(
            command_type="update", command_name="update", method="PUT",
            url_path="things/{thingId}", path_vars=["thingId"],
        )
        code = _render_update_command(ep)
        assert "thing_id" in code
        compile(code, "<generated>", "exec")

    def test_sibling_inference_heals_missing_parameters_declaration(self):
        """The live fix: a sibling GET on the identical url_path declares
        the path var that the PUT's own (buggy) parameters list omits.
        render_command_file must borrow it so the PUT renders correctly
        instead of tripping the guard."""
        show_ep = _make_endpoint(
            command_type="show", command_name="show", method="GET",
            url_path="things/{thingId}", path_vars=["thingId"],
        )
        update_ep = _make_endpoint(
            command_type="update", command_name="update", method="PUT",
            url_path="things/{thingId}", path_vars=[],  # spec bug: empty parameters
        )
        code = render_command_file("demo", [show_ep, update_ep], {})  # must not raise
        assert "thing_id: str = typer.Argument" in code
        assert 'url = f"https://webexapis.com/v1/things/{thing_id}"' in code
        compile(code, "<generated>", "exec")

    def test_no_sibling_to_borrow_from_still_raises(self):
        """If no sibling on the same url_path declares the var either,
        inference can't heal it — the guard is the backstop, not a
        silent pass-through."""
        ep = _make_endpoint(
            command_type="update", command_name="update", method="PUT",
            url_path="things/{thingId}", path_vars=[],
        )
        with pytest.raises(UnboundUrlPlaceholderError):
            render_command_file("demo", [ep], {})

    def test_render_url_expr_accepts_optional_method_for_back_compat(self):
        """Direct callers (e.g. TestUrlRendering) don't pass method= — the
        guard must still work with a generic label rather than requiring
        every existing call site to change."""
        url = _render_url_expr("things/{thingId}", ["thingId"])
        assert "webexapis.com/v1/things/{thing_id}" in url


# ── Example line: --json-body when no flag can carry a required field ────────
#
# Regression guard for the class the g-badexamples audit found: 99 commands
# printed an `Example:` naming only the flags they HAVE, on operations whose
# spec requires an object/array field the generator never renders as a flag.
# Copy-pasting one produced a guaranteed 400 (live-confirmed on
# `location-settings create`, which omitted `address`).

import tools.command_renderer as _cr
from tools.command_renderer import _render_example, _render_docstring


def _example_ep(**kw) -> Endpoint:
    defaults = dict(
        name="Create Thing", method="POST", url_path="things",
        command_type="create", command_name="create", raw_path=["things"],
        response_list_key=None,
    )
    defaults.update(kw)
    return _make_endpoint(**defaults)


class TestExampleCarriesJsonBody:
    SKELETON = '{"name":"...","address":{"city":"..."},"note":"..."}'
    MINIMAL = '{"name":"...","address":{"city":"..."}}'

    @pytest.fixture(autouse=True)
    def _pinned_group(self):
        """The example head reads the renderer's module-global group name,
        which render_command_file sets as a side effect — pin it so these
        assertions do not depend on which test ran last."""
        prev = _cr._active_cli_name
        _cr._active_cli_name = "things"
        yield
        _cr._active_cli_name = prev

    def _ep(self, **kw):
        return _example_ep(
            body_fields=[
                _make_field(name="name", python_name="name",
                            field_type="string", required=True),
                _make_field(name="address", python_name="address",
                            field_type="object", required=True),
            ],
            json_body_example=self.SKELETON,
            json_body_minimal_example=self.MINIMAL,
            **kw,
        )

    def test_example_uses_json_body_and_drops_the_flags(self):
        """The flags are not merely redundant — the generated code is
        `if json_body: body = load_json_body(...) else: <flags>`, so showing
        both would teach that they still apply."""
        example = _render_example(self._ep())
        assert f"--json-body '{self.MINIMAL}'" in example
        assert "--name" not in example

    def test_positionals_are_kept(self):
        ep = self._ep(url_path="locations/{locationId}/things",
                      path_vars=["locationId"], raw_path=["locations", "things"])
        assert _render_example(ep).startswith(
            "wxcli things create LOCATION_ID --json-body ")

    def test_example_shows_the_minimal_body_not_the_full_skeleton(self):
        """A create whose example hands back `id`/`createdTime` is not an
        example of creating anything."""
        assert self.SKELETON not in _render_example(self._ep())

    def test_full_skeleton_still_listed_separately(self):
        doc = _render_docstring(self._ep())
        assert f"Example --json-body: '{self.SKELETON}'" in doc

    def test_scalar_only_body_keeps_plain_flags(self):
        """Negative control: every required field has a flag, so nothing
        changes — this is the 1,300-odd commands that were always fine."""
        ep = _example_ep(
            body_fields=[_make_field(name="name", python_name="name",
                                     field_type="string", required=True)],
            json_body_example='{"name":"..."}',
            json_body_minimal_example='{"name":"..."}',
        )
        assert _render_example(ep) == "wxcli things create --name NAME"

    def test_optional_object_field_does_not_trigger_json_body(self):
        """Only a REQUIRED flagless field makes the flag list unusable."""
        ep = _example_ep(
            body_fields=[
                _make_field(name="name", python_name="name",
                            field_type="string", required=True),
                _make_field(name="address", python_name="address",
                            field_type="object", required=False),
            ],
            json_body_example=self.SKELETON,
            json_body_minimal_example='{"name":"..."}',
        )
        assert _render_example(ep) == "wxcli things create --name NAME"

    def test_truncation_note_reaches_the_docstring(self):
        ep = self._ep(json_body_truncations=["a.b not expanded (schema recurses)"])
        assert "NOTE: skeleton incomplete" in _render_docstring(ep)
