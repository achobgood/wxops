"""Tests for the command renderer."""
import pytest

from tools.postman_parser import Endpoint, EndpointField
from tools.command_renderer import (
    _render_list_command,
    _render_create_command,
    _render_show_command,
    _render_create_id_extraction,
    _enum_help,
    render_command_file,
)


# ---------------------------------------------------------------------------
# Helpers to build test fixtures
# ---------------------------------------------------------------------------

def _make_ep(**kwargs) -> Endpoint:
    """Build an Endpoint with sensible defaults, overriding with kwargs."""
    defaults = dict(
        name="Test Endpoint",
        method="GET",
        url_path="telephony/config/widgets",
        path_vars=[],
        query_params=[],
        body_fields=[],
        command_type="list",
        command_name="list",
        raw_path=["telephony", "config", "widgets"],
        response_list_key="widgets",
        response_id_key=None,
        deprecated=False,
    )
    defaults.update(kwargs)
    return Endpoint(**defaults)


def _make_field(**kwargs) -> EndpointField:
    """Build an EndpointField with sensible defaults."""
    defaults = dict(
        name="testField",
        python_name="test-field",
        field_type="string",
        description="A test field",
        required=False,
        default=None,
        enum_values=None,
    )
    defaults.update(kwargs)
    return EndpointField(**defaults)


# ---------------------------------------------------------------------------
# test_render_list_with_response_key
# ---------------------------------------------------------------------------

class TestRenderListWithResponseKey:
    def test_uses_response_list_key(self):
        ep = _make_ep(response_list_key="autoAttendants")
        code = _render_list_command(ep, {})
        assert '"autoAttendants"' in code
        assert 'result.get("autoAttendants"' in code

    def test_falls_back_to_items(self):
        ep = _make_ep(response_list_key=None)
        code = _render_list_command(ep, {})
        assert 'result.get("items"' in code


# ---------------------------------------------------------------------------
# test_render_create_with_custom_id_key
# ---------------------------------------------------------------------------

class TestRenderCreateWithCustomIdKey:
    def test_uses_response_id_key_from_endpoint(self):
        ep = _make_ep(
            method="POST",
            command_type="create",
            command_name="create",
            response_id_key="dectNetworkId",
            body_fields=[
                _make_field(name="name", python_name="name", required=True),
            ],
        )
        code = _render_create_command(ep, {})
        assert '"dectNetworkId"' in code
        assert 'result[\'dectNetworkId\']' in code

    def test_falls_back_to_folder_override_id_key(self):
        ep = _make_ep(
            method="POST",
            command_type="create",
            command_name="create",
            response_id_key=None,
            body_fields=[],
        )
        overrides = {"create": {"id_key": "huntGroupId"}}
        code = _render_create_command(ep, overrides)
        assert '"huntGroupId"' in code

    def test_falls_back_to_default_id(self):
        ep = _make_ep(
            method="POST",
            command_type="create",
            command_name="create",
            response_id_key=None,
            body_fields=[],
        )
        code = _render_create_command(ep, {})
        assert 'result[\'id\']' in code
        # Should NOT have a custom key check
        assert "dectNetworkId" not in code

    def test_schema_id_key_takes_precedence_over_override(self):
        ep = _make_ep(
            method="POST",
            command_type="create",
            command_name="create",
            response_id_key="widgetId",
            body_fields=[],
        )
        overrides = {"create": {"id_key": "huntGroupId"}}
        code = _render_create_command(ep, overrides)
        # Schema key should win
        assert '"widgetId"' in code
        assert "huntGroupId" not in code


# ---------------------------------------------------------------------------
# test_render_option_with_enum_choices
# ---------------------------------------------------------------------------

class TestRenderOptionWithEnumChoices:
    def test_short_enum_shows_choices(self):
        field = _make_field(
            name="color",
            python_name="color",
            enum_values=["red", "blue", "green"],
            description="Color of widget",
        )
        help_text = _enum_help(field)
        assert "Choices: red, blue, green" in help_text

    def test_long_enum_shows_help_hint(self):
        many = [f"VAL_{i}" for i in range(12)]
        field = _make_field(
            name="region",
            python_name="region",
            enum_values=many,
            description="Region code",
        )
        help_text = _enum_help(field)
        assert "use --help for choices" in help_text
        assert "Region code" in help_text

    def test_no_enum_shows_description(self):
        field = _make_field(
            name="name",
            python_name="name",
            enum_values=None,
            description="Widget name",
        )
        help_text = _enum_help(field)
        assert help_text == "Widget name"

    def test_enum_in_create_command(self):
        ep = _make_ep(
            method="POST",
            command_type="create",
            command_name="create",
            body_fields=[
                _make_field(
                    name="color",
                    python_name="color",
                    enum_values=["red", "blue", "green"],
                    required=True,
                ),
            ],
        )
        code = _render_create_command(ep, {})
        assert "Choices: red, blue, green" in code

    def test_enum_in_list_query_param(self):
        ep = _make_ep(
            query_params=[
                _make_field(
                    name="status",
                    python_name="status",
                    enum_values=["active", "inactive"],
                    description="Filter by status",
                ),
            ],
        )
        code = _render_list_command(ep, {})
        assert "Choices: active, inactive" in code


# ---------------------------------------------------------------------------
# test_render_option_with_description
# ---------------------------------------------------------------------------

class TestRenderOptionWithDescription:
    def test_description_in_create_option(self):
        ep = _make_ep(
            method="POST",
            command_type="create",
            command_name="create",
            body_fields=[
                _make_field(
                    name="name",
                    python_name="name",
                    description="The widget display name",
                    required=False,
                ),
            ],
        )
        code = _render_create_command(ep, {})
        assert "The widget display name" in code

    def test_description_in_list_query(self):
        ep = _make_ep(
            query_params=[
                _make_field(
                    name="max",
                    python_name="max",
                    field_type="number",
                    description="Maximum results to return",
                ),
            ],
        )
        code = _render_list_command(ep, {})
        assert "Maximum results to return" in code


# ---------------------------------------------------------------------------
# test_render_required_option
# ---------------------------------------------------------------------------

class TestRenderRequiredOption:
    def test_required_string_uses_ellipsis(self):
        ep = _make_ep(
            method="POST",
            command_type="create",
            command_name="create",
            body_fields=[
                _make_field(
                    name="name",
                    python_name="name",
                    required=True,
                    description="Widget name",
                ),
            ],
        )
        code = _render_create_command(ep, {})
        assert 'typer.Option(..., "--name"' in code

    def test_optional_string_uses_none(self):
        ep = _make_ep(
            method="POST",
            command_type="create",
            command_name="create",
            body_fields=[
                _make_field(
                    name="label",
                    python_name="label",
                    required=False,
                    description="Optional label",
                ),
            ],
        )
        code = _render_create_command(ep, {})
        assert 'typer.Option(None, "--label"' in code

    def test_required_bool_uses_ellipsis(self):
        ep = _make_ep(
            method="POST",
            command_type="create",
            command_name="create",
            body_fields=[
                _make_field(
                    name="enabled",
                    python_name="enabled",
                    field_type="bool",
                    required=True,
                    description="Enable widget",
                ),
            ],
        )
        code = _render_create_command(ep, {})
        assert 'typer.Option(..., "--enabled"' in code


# ---------------------------------------------------------------------------
# test_render_settings_get
# ---------------------------------------------------------------------------

class TestRenderSettingsGet:
    def test_settings_get_renders_like_show(self):
        ep = _make_ep(
            command_type="settings-get",
            command_name="show",
            url_path="telephony/config/locations/{locationId}/voicemail",
            path_vars=["locationId"],
        )
        code = _render_show_command(ep)
        assert '@app.command("show")' in code
        assert "rest_get" in code
        assert "print_json(result)" in code

    def test_settings_get_via_render_command_file(self):
        ep = _make_ep(
            command_type="settings-get",
            command_name="show",
            url_path="telephony/config/locations/{locationId}/voicemail",
            path_vars=["locationId"],
        )
        code = render_command_file("Test Settings", [ep], {})
        assert '@app.command("show")' in code
        assert "rest_get" in code


# ---------------------------------------------------------------------------
# test_render_command_file dispatch
# ---------------------------------------------------------------------------

class TestRenderCommandFileDispatch:
    def test_all_command_types_dispatch(self):
        """All known command types should render without error."""
        endpoints = [
            _make_ep(command_type="list", command_name="list"),
            _make_ep(command_type="show", command_name="show", path_vars=["widgetId"]),
            _make_ep(
                command_type="create", command_name="create", method="POST",
                body_fields=[_make_field(name="n", python_name="n", required=True)],
            ),
            _make_ep(
                command_type="update", command_name="update", method="PUT",
                path_vars=["widgetId"],
            ),
            _make_ep(
                command_type="delete", command_name="delete", method="DELETE",
                path_vars=["widgetId"],
            ),
            _make_ep(command_type="settings-get", command_name="show-settings"),
            _make_ep(
                command_type="settings-update", command_name="update-settings",
                method="PUT",
            ),
            _make_ep(
                command_type="action", command_name="invoke-action", method="POST",
            ),
        ]
        code = render_command_file("Widgets", endpoints, {})
        assert "SKIPPED" not in code
        # Each endpoint should have produced an @app.command
        for ep in endpoints:
            assert f'@app.command("{ep.command_name}")' in code

    def test_unknown_type_skipped(self):
        ep = _make_ep(command_type="unknown-type", command_name="mystery")
        code = render_command_file("Widgets", [ep], {})
        assert "SKIPPED" in code
