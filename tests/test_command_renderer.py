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

    def test_cc_v1_spec_path_keeps_v1(self, monkeypatch):
        """The CC base URL has no /v1, so a /v1/ spec path must keep it.
        Regression: cc-callbacks rendered {cc_base_url}/callbacks/... -> 404."""
        import tools.command_renderer as cr
        monkeypatch.setattr(cr, "_active_base_url_override", cr.BASE_URL_CC)
        url = _render_url_expr(
            "callbacks/organization/{orgId}/scheduled-callback", ["orgId"],
            spec_v1=True)
        assert url == "{cc_base_url}/v1/callbacks/organization/{org_id}/scheduled-callback"

    def test_cc_unversioned_config_path_unchanged(self, monkeypatch):
        import tools.command_renderer as cr
        monkeypatch.setattr(cr, "_active_base_url_override", cr.BASE_URL_CC)
        url = _render_url_expr("organization/{orgid}/queue", ["orgid"])
        assert url == "{cc_base_url}/organization/{orgid}/queue"

    def test_calling_v1_spec_path_not_doubled(self):
        url = _render_url_expr("things", [], spec_v1=True)
        assert url == "https://webexapis.com/v1/things"


class TestCcV1PathsEndToEnd:
    """Every /v1/ operation in the real CC spec renders a URL containing /v1/."""

    def test_cc_callbacks_urls_include_v1(self):
        spec = json.loads((Path(__file__).parent.parent / "specs"
                           / "webex-contact-center.json").read_text())
        endpoints, _ = parse_tag("Callbacks", spec)
        assert endpoints, "Callbacks tag produced no endpoints"
        code = render_command_file("Callbacks", endpoints, {},
                                   base_url_override="{cc_base_url}")
        urls = [ln.strip() for ln in code.splitlines() if ln.strip().startswith("url = ")]
        assert len(urls) == 5
        for u in urls:
            assert u.startswith('url = f"{cc_base_url}/v1/callbacks/organization/'), u

    def test_shipped_cc_modules_have_no_stripped_v1(self):
        spec = json.loads((Path(__file__).parent.parent / "specs"
                           / "webex-contact-center.json").read_text())
        first = {p.split("/")[2] for p in spec["paths"] if p.startswith("/v1/")}
        first -= {"{orgId}", "organization"}  # also used by unversioned config paths
        cmd_dir = Path(__file__).parent.parent / "src" / "wxcli" / "commands"
        bad = []
        for f in sorted(cmd_dir.glob("cc_*.py")):
            for ln in f.read_text().splitlines():
                s = ln.strip()
                if s.startswith('url = f"{cc_base_url}/'):
                    seg = s[len('url = f"{cc_base_url}/'):].split("/")[0].rstrip('"')
                    if seg in first:
                        bad.append(f"{f.name}: {s}")
        assert not bad, "CC /v1 paths rendered without /v1:\n" + "\n".join(bad)


# ── Contact Center fixes, 2026-10-13 (all three reproduced live first) ───────

_CC_SPEC = Path(__file__).parent.parent / "specs" / "webex-contact-center.json"


def _cc_render(tag: str) -> tuple[list, str]:
    spec = json.loads(_CC_SPEC.read_text())
    # auto_inject_params as generate_commands passes it by default.
    endpoints, _ = parse_tag(tag, spec, auto_inject_params={"orgId"})
    assert endpoints, f"{tag} produced no endpoints"
    return endpoints, render_command_file(tag, endpoints, {},
                                          base_url_override="{cc_base_url}")


def _function_body(code: str, func: str) -> str:
    start = code.index(f"\ndef {func}(")
    nxt = code.find("\n@app.command", start)
    return code[start: nxt if nxt != -1 else len(code)]


class TestCcOrgIdQueryParam:
    """Bug 1: the CC host rejected the base64 Webex org id in `?orgId=` with
    401 'Token does not have access to OrgId:Y2lz...' — every CC runtime and
    analytics command that sends it (cc-queue-stats, cc-agents, ...) failed."""

    def test_cc_query_orgid_is_the_decoded_uuid(self):
        _, code = _cc_render("Queues")
        assert 'params["orgId"] = get_cc_org_id(api.session)' in code
        assert 'params["orgId"] = org_id' not in code
        # Still only when an org is saved: no saved org -> param omitted and the
        # org is inferred from the token, as the spec documents.
        assert "    if org_id is not None:\n" in code
        compile(code, "<cc_queue_stats>", "exec")

    def test_non_cc_query_orgid_is_unchanged(self):
        """Control: the Calling/admin hosts DO take the base64 id."""
        ep = _make_endpoint(auto_inject_params=["orgId"])
        code = render_command_file("Things", [ep], {})
        assert 'params["orgId"] = org_id' in code
        assert "get_cc_org_id" not in code

    def test_no_shipped_cc_module_sends_the_base64_org_id(self):
        cmd_dir = Path(__file__).parent.parent / "src" / "wxcli" / "commands"
        bad = [f.name for f in sorted(cmd_dir.glob("cc_*.py"))
               if 'params["orgId"] = org_id' in f.read_text()]
        assert not bad, f"CC modules still send the base64 org id: {bad}"


class TestCcFlowsPaging:
    """Bug 2: `cc-flow list --all` returned 10 of 56. The walker sent
    `pageSize`, the Flows endpoints take `size`; the server ignored the unknown
    name, answered with its default page of 10, and the short-page stop ended
    the walk. With no `includePagination`, the bare array carried no total, so
    the truncation note could not fire either."""

    def test_flows_page_size_param_is_size(self):
        endpoints, _ = _cc_render("Flows")
        by_path = {ep.url_path: ep for ep in endpoints if ep.method == "GET"}
        assert by_path["{orgId}/project/{projectId}/flows"].page_size_param == "size"
        assert by_path["{orgId}/project/{projectId}/flows:search"].page_size_param == "size"

    def test_flows_walkers_page_with_size(self):
        _, code = _cc_render("Flows")
        # 2 commands x (the --all walker + the --offset window), both in `size`.
        import re
        assert len(re.findall(r'follow_page_param\([^)]*size_param="size"\)', code)) == 2
        assert len(re.findall(r'fetch_from_offset\([^)]*size_param="size"\)', code)) == 2

    def test_include_pagination_defaults_on(self):
        _, code = _cc_render("Flows")
        assert 'typer.Option("true", "--include-pagination"' in code

    def test_pagesize_endpoints_render_unchanged(self):
        """Control: the ~109 `pageSize` commands must not grow a size_param."""
        endpoints, code = _cc_render("Team")
        assert any(ep.pagination_style == "page" for ep in endpoints)
        assert all(ep.page_size_param == "pageSize" for ep in endpoints
                   if ep.pagination_style == "page")
        assert "size_param=" not in code


class TestPageNumberedLimitOffset:
    """Issue 1 (2026-10-13): on the page-numbered (`page`/`pageSize`) list
    commands, --limit was sent as `max` and --offset as `start`. CC reads
    neither, so both were inert on the wire and exit 0 (live: `cc-queue list
    --limit 2` -> `?max=2` -> 17 records). Both flags stay — uniform on every
    list command, ADR-12 — and are translated instead."""

    def _list_body(self, tag, func="cmd_list"):
        _, code = _cc_render(tag)
        return _function_body(code, func)

    def test_page_numbered_list_never_sends_max_or_start(self):
        body = self._list_body("Team")
        assert 'params["max"]' not in body and 'params["start"]' not in body
        assert ('if limit > 0 and not all_pages and params.get("pageSize") is None:\n'
                '        params["pageSize"] = limit') in body
        assert ('elif offset > 0:\n            result = api.session.fetch_from_offset('
                'url=url, params=params, offset=offset, count=limit, item_key=') in body

    def test_offset_help_says_what_it_does(self):
        body = self._list_body("Team")
        assert 'help="Skip this many records (translated to the page number; record-exact)."' in body
        assert "sent as the page size (pageSize)" in body

    def test_flows_translate_into_size(self):
        _, code = _cc_render("Flows")
        assert 'params.get("size") is None:\n        params["size"] = limit' in code

    def test_tasks_page_size_only_endpoint_is_translated_too(self):
        """/v1/tasks declares `pageSize` but no `page`; it has no --page flag,
        so --offset is its ONLY way to the next page (it honours `page` live:
        Link rel=next `page=1&pageSize=100`, 2026-10-13)."""
        body = self._list_body("Tasks")
        assert "fetch_from_offset" in body and '"--page"' not in body

    def test_link_style_commands_keep_max_and_start(self):
        """Control: `max`/`start` endpoints are untouched."""
        ep = _make_endpoint(command_type="list", method="GET",
                            query_params=[_make_field(name="max", python_name="max", field_type="number"),
                                          _make_field(name="start", python_name="start", field_type="number")])
        ep.pagination_style = "link"
        code = render_command_file("Things", [ep], {})
        assert 'params["max"] = limit' in code and 'params["start"] = offset' in code
        assert "fetch_from_offset" not in code

    def test_scim_list_sends_count_and_one_based_start_index(self):
        """SCIM (`startIndex`/`count`) reads neither `max` nor `start` either —
        drift check 23 found it on 5 commands (`scim-users list`, …)."""
        ep = _make_endpoint(command_type="list", method="GET",
                            query_params=[_make_field(name="startIndex", python_name="start-index"),
                                          _make_field(name="count", python_name="count")])
        ep.pagination_style = "scim"
        code = render_command_file("Things", [ep], {})
        assert 'params["max"]' not in code and 'params["start"]' not in code
        assert ('if limit > 0 and not all_pages and params.get("count") is None:\n'
                '        params["count"] = limit') in code
        assert ('if offset > 0 and params.get("startIndex") is None:\n'
                '        params["startIndex"] = offset + 1') in code
        assert "sent as the 1-based startIndex = offset + 1" in code

    def test_count_only_scim_style_op_is_not_translated(self):
        """`scim` style is set by either name alone. A count-only op must not
        get --offset sent as a `startIndex` it does not declare."""
        ep = _make_endpoint(command_type="list", method="GET",
                            query_params=[_make_field(name="count", python_name="count")])
        ep.pagination_style = "scim"
        code = render_command_file("Things", [ep], {})
        assert 'params["startIndex"]' not in code
        assert "1-based startIndex" not in code


class TestWildcardResponseListKey:
    """Issue 5 (2026-10-13): `cc-global-vars list` printed 0 rows and a "server
    has more pages" note while the org has 6 variables. The CC spec declares
    121 GET 200s as `*/*`, which the list-key extractor never read, so the 7
    bulk-export lists extracted `items`/`data` from a body whose records are
    under `resources`."""

    BULK = ["Global Variables", "Auxiliary Code", "Contact Number", "Dial Number",
            "Entry Point", "Multimedia Profile", "Site"]

    @pytest.mark.parametrize("tag", BULK)
    def test_bulk_export_extracts_resources(self, tag):
        endpoints, code = _cc_render(tag)
        bulk = [ep for ep in endpoints if ep.url_path.endswith("/bulk-export")]
        assert len(bulk) == 1, tag
        assert bulk[0].response_list_key == "resources"
        assert 'result.get("resources", result.get("data"' in code

    def test_only_the_key_is_widened_not_the_command_type(self):
        """reportable-count is a `*/*` flat object: widening type detection too
        would turn it into settings-get and rename it. It must stay a list."""
        endpoints, _ = _cc_render("Global Variables")
        rc = [ep for ep in endpoints if ep.url_path.endswith("/reportable-count")]
        assert rc and rc[0].command_type == "list"


def _probes(by_group: dict) -> dict:
    return {g: v for g, v in by_group.items() if g.startswith("zz-")}


class TestGroupHelpProduct:
    """Item 7 (2026-10-13): the group-help label was guessed from the CLI-name
    prefix, so `asset` and `channel` (Contact Center host) and every admin,
    device and messaging group read "Manage Webex Calling <group>." It now
    reads SPEC_PRODUCT for the spec the group is rendered from."""

    @pytest.mark.parametrize("spec,label", [
        ("webex-contact-center.json", "Webex Contact Center"),
        ("webex-messaging.json", "Webex Messaging"),
        ("webex-admin.json", "Webex Admin"),
        ("webex-cloud-calling.json", "Webex Calling"),
    ])
    def test_label_follows_the_spec(self, spec, label, monkeypatch):
        # An empty index: no spec owns "asset", so each keeps its own product
        # whatever the live specs say (group_label_spec's non-owner branch).
        from tools import command_renderer as cr
        monkeypatch.setattr(cr, "_producer_index", {
            "by_path": {}, "by_tail": {}, "scoping": set(), "summary_groups": {},
            "group_product": {}, "group_specs": {}})
        code = render_command_file("asset", [_make_endpoint()], {}, spec_filename=spec)
        assert f'app = typer.Typer(help="Manage {label}: asset.")' in code

    def test_shipped_unprefixed_cc_groups_say_contact_center(self):
        cmd_dir = Path(__file__).parent.parent / "src" / "wxcli" / "commands"
        for mod in ("asset", "channel"):
            src = (cmd_dir / f"{mod}.py").read_text()
            assert "get_cc_base_url" in src
            assert f'help="Manage Webex Contact Center: {mod}."' in src

    def test_every_cc_host_module_is_labelled_contact_center(self):
        cmd_dir = Path(__file__).parent.parent / "src" / "wxcli" / "commands"
        wrong = [f.name for f in sorted(cmd_dir.glob("*.py"))
                 if "cc_base_url = get_cc_base_url()" in f.read_text()
                 # prefix without the colon: cc_ai_assistant.py is a kept
                 # CLI-ahead module no regen writes, labelled before 2026-10-13
                 and 'typer.Typer(help="Manage Webex Contact Center' not in f.read_text()]
        assert not wrong, wrong

    # Seven groups are written by two specs (last writer wins), and five of
    # their labels flipped with render order: a full spec_sync regen and a
    # one-spec regen disagreed. The rule tests below run on a FIXTURE index
    # built from tiny specs, so an upstream tag change cannot fail them (the
    # weekly routine runs this suite and may not edit tests); only the live
    # self-consistency test reads the real index, and it names no group.

    @staticmethod
    def _probe_spec(*tags):
        paths = {}
        for i, tag in enumerate(tags):
            slug = tag.lower().replace(" ", "")
            paths[f"/{slug}/{{probeId}}"] = {"get": {
                "tags": [tag], "operationId": f"get{slug}{i}",
                "summary": f"Get {tag}",
                "parameters": [{"name": "probeId", "in": "path",
                                "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "ok"}}}}
        return {"openapi": "3.0.0", "info": {"title": "probe", "version": "1"},
                "paths": paths}

    @pytest.fixture
    def probe_index(self, tmp_path, monkeypatch):
        """Umbrella pair (admin + meetings; admin walks first), a walk-order
        tie (cloud-calling + device), and a single-owner group."""
        from tools import command_renderer as cr
        specs = {
            "webex-admin.json": ["Zz Umbrella Probe"],
            "webex-meetings.json": ["Zz Umbrella Probe"],
            "webex-device.json": ["Zz Order Probe"],
            "webex-cloud-calling.json": ["Zz Order Probe"],
            "webex-messaging.json": ["Zz Single Probe"],
        }
        for name, tags in specs.items():
            (tmp_path / name).write_text(json.dumps(self._probe_spec(*tags)))
        index = cr.build_producer_index(specs_dir=tmp_path)
        monkeypatch.setattr(cr, "_producer_index", index)
        return index

    def test_fixture_index_records_every_owner_in_walk_order(self, probe_index):
        # Filtered to the probes: the real field_overrides.yaml still applies
        # (tag_merge can synthesize a group of its own on a cloud-calling spec).
        assert _probes(probe_index["group_specs"]) == {
            "zz-umbrella-probe": ["webex-admin.json", "webex-meetings.json"],
            "zz-order-probe": ["webex-cloud-calling.json", "webex-device.json"],
            "zz-single-probe": ["webex-messaging.json"],
        }

    def test_umbrella_spec_ranks_last(self, probe_index):
        from tools.command_renderer import group_label_spec
        for spec in ("webex-admin.json", "webex-meetings.json"):
            assert group_label_spec("zz-umbrella-probe", spec) == "webex-meetings.json"

    def test_walk_order_breaks_a_tie(self, probe_index):
        from tools.command_renderer import group_label_spec
        for spec in ("webex-device.json", "webex-cloud-calling.json"):
            assert group_label_spec("zz-order-probe", spec) == "webex-cloud-calling.json"

    def test_non_owner_keeps_its_own_spec(self, probe_index):
        from tools.command_renderer import group_label_spec
        assert group_label_spec("zz-single-probe", "webex-admin.json") == "webex-admin.json"
        assert group_label_spec("zz-unknown", "webex-device.json") == "webex-device.json"

    @pytest.mark.parametrize("group,owners,product", [
        ("zz-umbrella-probe", ["webex-admin.json", "webex-meetings.json"], "Meetings"),
        ("zz-order-probe", ["webex-device.json", "webex-cloud-calling.json"], "Calling"),
    ])
    def test_label_ignores_render_order(self, probe_index, group, owners, product):
        want = f'app = typer.Typer(help="Manage Webex {product}: {group}.")'
        for spec in owners:
            code = render_command_file(group, [_make_endpoint()], {}, spec_filename=spec)
            assert want in code, spec

    def test_qualifier_product_follows_the_label_rule(self, probe_index):
        assert _probes(probe_index["group_product"]) == {
            "zz-umbrella-probe": "Meetings",
            "zz-order-probe": "Calling",
            "zz-single-probe": "Messaging",
        }

    def test_shipped_labels_match_the_live_index(self):
        """Self-consistency, no group named: every shipped module of a group the
        live index knows carries the label the rule derives. A full regen must
        reproduce this byte-for-byte."""
        from tools.command_renderer import (
            SPEC_PRODUCT, _label_rank, build_producer_index)
        cmd_dir = Path(__file__).parent.parent / "src" / "wxcli" / "commands"
        checked, wrong = 0, []
        for group, owners in build_producer_index()["group_specs"].items():
            module = cmd_dir / f"{group.replace('-', '_')}.py"
            if not owners or not module.exists():
                continue
            product = SPEC_PRODUCT[min(owners, key=_label_rank(owners))]
            want = f'app = typer.Typer(help="Manage Webex {product}: {group}.")'
            checked += 1
            if want not in module.read_text():
                wrong.append(want)
        assert checked >= 1, "the live index is empty -- it is not being built"
        assert not wrong, wrong


class TestSingleResourceActionGet:
    """Bug 3: `cc-flow export` printed only result["nodes"] — the list-style
    extractor — so the export could not be re-imported; `list-validate` printed
    `results` and dropped `valid: false`. A GET on `{id}:<action>` acts on ONE
    resource and must emit the whole response."""

    @pytest.mark.parametrize("method,path,expected", [
        ("GET", "/{orgId}/project/{projectId}/v2/flows/{flowId}:export", True),
        ("GET", "/{orgId}/project/{projectId}/v2/flows/{flowId}:validate", True),
        ("GET", "/flow-store/{orgId}/project/{p}/flows/{flowId}:export", True),
        ("GET", "/{orgId}/project/{projectId}/flows:search", False),   # a real list
        ("GET", "/{orgId}/project/{projectId}/v2/flows/{flowId}", False),
        ("POST", "/{orgId}/project/{projectId}/flows/{flowId}:publish", False),
    ])
    def test_classifier(self, method, path, expected):
        from tools.openapi_parser import _is_single_resource_action_get
        assert _is_single_resource_action_get(method, path) is expected

    def test_export_and_validate_render_the_full_response(self):
        endpoints, code = _cc_render("Flows")
        names = {ep.url_path.rsplit(":", 1)[-1]: ep for ep in endpoints
                 if ep.method == "GET" and ":" in ep.url_path.rsplit("/", 1)[-1]}
        for action in ("export", "validate"):
            ep = names[action]
            assert ep.command_type == "show"
            # Names are derived BEFORE the reclassification, so nothing moves.
            assert ep.command_name == f"list-{action}"
            body = _function_body(code, _safe_func_name(ep.command_name))
            assert "emit(result, output=output, fields=fields)" in body
            assert 'result.get("nodes"' not in body and 'result.get("results"' not in body

    def test_flows_list_is_still_a_list(self):
        """Control: the reclassification must not touch real list commands."""
        endpoints, _ = _cc_render("Flows")
        lists = {ep.url_path for ep in endpoints if ep.command_type == "list"}
        assert "{orgId}/project/{projectId}/flows" in lists
        assert "{orgId}/project/{projectId}/flows:search" in lists


def _single_object_spec(response_200: dict, extra: dict | None = None) -> dict:
    # The real list comes first and takes the bare `list`, as in user-settings.
    spec = {"paths": {
        "/people/{personId}/numbers": {"get": {
            "tags": ["Probe"], "operationId": "getNumbers",
            "summary": "List Numbers",
            "parameters": [{"name": "personId", "in": "path",
                            "required": True, "schema": {"type": "string"}}],
            "responses": {"200": {"description": "ok", "content": {
                "application/json": {"schema": {"type": "object", "properties": {
                    "numbers": {"type": "array", "items": {"type": "object"}}}}}}}}}},
        "/people/{personId}/outboundBillingPlan": {"get": {
            "tags": ["Probe"], "operationId": "getPlan",
            "summary": "Retrieve a Person's Outbound Billing Plan",
            "parameters": [{"name": "personId", "in": "path",
                            "required": True, "schema": {"type": "string"}}],
            "responses": {"200": response_200}}},
    }}
    spec.update(extra or {})
    return spec


_PLAN_SCHEMA = {"type": "object", "properties": {"enabled": {"type": "boolean"}}}


class TestSingleObjectResponseGet:
    """`user-settings list-outbound-billing-plan` printed `[]` for
    `{"enabled": true}` (live, 2026-10-13). Its 200 is a response-level `$ref`
    `_get_response_schema` never resolved, so `detect_command_type` saw no
    schema and defaulted to list. `guest-management list` (`/guests/count`,
    an object under `text/plain` only) had the same shape. A list-classified
    GET whose response is one flat object renders as `show`, after naming."""

    @pytest.mark.parametrize("response,expected", [
        ({"$ref": "#/components/responses/Plan"}, True),
        ({"content": {"text/plain": {"schema": _PLAN_SCHEMA}}}, True),
        ({"content": {"*/*": {"schema": _PLAN_SCHEMA}}}, True),
        # Any doubt keeps the list rendering:
        ({"content": {"application/json": {"schema": {
            "type": "array", "items": {}}}}}, False),
        ({"content": {"application/json": {"schema": {"type": "object",
            "properties": {"rows": {"$ref": "#/components/schemas/Rows"}}}}}},
         False),
        ({"content": {"application/json": {"schema": {"type": "object",
            "properties": {"rows": {"$ref": "#/components/schemas/Gone"}}}}}},
         False),
        ({"content": {"application/json": {"schema": {"type": "object"}}}},
         False),
        ({"description": "no content"}, False),
        ({"$ref": "#/components/responses/Gone"}, False),
    ])
    def test_classifier(self, response, expected):
        from tools.openapi_parser import _declares_single_object
        spec = {"components": {
            "responses": {"Plan": {"description": "ok", "content": {
                "application/json": {"schema": {
                    "$ref": "#/components/schemas/Plan"}}}}},
            "schemas": {"Plan": _PLAN_SCHEMA,
                        "Rows": {"type": "array", "items": {}}}}}
        assert _declares_single_object(
            {"responses": {"200": response}}, spec) is expected

    def test_response_ref_object_renders_full_response_name_kept(self):
        spec = _single_object_spec(
            {"$ref": "#/components/responses/Plan"},
            {"components": {"responses": {"Plan": {
                "description": "ok", "content": {"application/json": {
                    "schema": _PLAN_SCHEMA}}}}}})
        endpoints, _ = parse_tag("Probe", spec)
        by_path = {ep.url_path: ep for ep in endpoints}
        plan = by_path["people/{personId}/outboundBillingPlan"]
        assert plan.command_type == "show"
        assert plan.response_list_key is None
        # Named BEFORE the reclassification, so the shipped name is kept.
        assert plan.command_name == "list-outbound-billing-plan"
        code = render_command_file("Probe", endpoints, {})
        body = _function_body(code, _safe_func_name(plan.command_name))
        assert "emit(result, output=output, fields=fields)" in body
        assert 'result.get("items"' not in body
        # Control: the sibling array response is still a list.
        assert by_path["people/{personId}/numbers"].command_type == "list"


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
    """--fields must not disturb the flags cc-search/CC already own."""
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


class TestMakeRequired:
    """Item 6 (2026-10-13): `cc-dial-number create` — the spec marks `location`
    and `regionId` optional; live the API answered 400 "location: should not
    be null or blank", then 400 "Telephony regionId should be provided.".
    `make_required` pins them so the CLI refuses before the request."""

    def test_marks_named_body_fields_required(self):
        from tools.postman_parser import apply_endpoint_overrides
        ep = _make_endpoint(command_type="create", method="POST", command_name="create",
                            body_fields=[_make_field(name="location", python_name="location"),
                                         _make_field(name="other", python_name="other")])
        apply_endpoint_overrides(ep, {"make_required": {"create": ["location"]}})
        assert {bf.name: bf.required for bf in ep.body_fields} == {"location": True, "other": False}

    def test_unknown_field_name_raises(self):
        from tools.postman_parser import apply_endpoint_overrides
        ep = _make_endpoint(command_type="create", method="POST", command_name="create",
                            body_fields=[_make_field(name="location", python_name="location")])
        with pytest.raises(ValueError, match="regionIdd"):
            apply_endpoint_overrides(ep, {"make_required": {"create": ["regionIdd"]}})

    def test_shipped_dial_number_create_requires_location_and_region(self):
        src = (Path(__file__).parent.parent / "src" / "wxcli" / "commands"
               / "cc_dial_number.py").read_text()
        assert ("_missing = [f for f in ['entryPointId', 'entryPointName', 'location', "
                "'regionId'] if f not in body") in src
        assert 'help="(required) The ID of the location' in src
        assert 'help="(required) Specify the telephony region id' in src
