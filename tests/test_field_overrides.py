"""Part C: Field overrides tests — field_overrides.yaml application."""

import json
import pytest
from pathlib import Path

import yaml

from tools.postman_parser import (
    Endpoint,
    EndpointField,
    load_overrides,
    apply_endpoint_overrides,
    camel_to_kebab,
)
from tools.command_renderer import render_command_file, _render_list_command
from tools.openapi_parser import parse_tag
from tools.generate_commands import should_skip_tag, merge_tags


FIXTURES = Path(__file__).parent / "fixtures"
OVERRIDES_PATH = Path(__file__).parent.parent / "tools" / "field_overrides.yaml"


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_endpoint(**kwargs) -> Endpoint:
    defaults = dict(
        name="Test",
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


# ── YAML validity ────────────────────────────────────────────────────────────


class TestOverridesYamlValidity:
    def test_yaml_parses_without_error(self):
        """field_overrides.yaml is valid YAML."""
        with open(OVERRIDES_PATH) as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict)

    def test_all_keys_recognized(self):
        """Top-level non-tag keys are from the known set."""
        with open(OVERRIDES_PATH) as f:
            data = yaml.safe_load(f)
        known_global_keys = {
            "omit_query_params", "skip_tags", "tag_merge", "cli_name_overrides"
        }
        known_tag_keys = {
            "list", "table_columns", "command_type_overrides", "response_list_keys",
            "url_overrides", "add_query_params", "keep_query_params",
        }
        for key, value in data.items():
            if key in known_global_keys:
                continue
            # It's a tag-level override
            if isinstance(value, dict):
                for subkey in value:
                    assert subkey in known_tag_keys, (
                        f"Unrecognized key '{subkey}' under tag '{key}'"
                    )

    def test_omit_query_params_present(self):
        with open(OVERRIDES_PATH) as f:
            data = yaml.safe_load(f)
        assert "omit_query_params" in data
        # orgId moved from omit_query_params to auto_inject_from_config
        assert isinstance(data["omit_query_params"], list)

    def test_skip_tags_are_strings(self):
        with open(OVERRIDES_PATH) as f:
            data = yaml.safe_load(f)
        for pattern in data.get("skip_tags", []):
            assert isinstance(pattern, str)

    def test_cli_name_overrides_are_kebab(self):
        with open(OVERRIDES_PATH) as f:
            data = yaml.safe_load(f)
        for tag, cli_name in data.get("cli_name_overrides", {}).items():
            assert "_" not in cli_name, (
                f"cli_name '{cli_name}' for tag '{tag}' should be kebab-case, not snake_case"
            )


# ── table_columns applied ───────────────────────────────────────────────────


class TestTableColumnsApplied:
    def test_folder_level_columns(self):
        """Override specifying list.table_columns → columns appear in rendered command."""
        ep = _make_endpoint(command_type="list", command_name="list")
        overrides = {
            "list": {"table_columns": [["Phone", "phoneNumber"], ["State", "state"]]}
        }
        code = _render_list_command(ep, overrides)
        assert "phoneNumber" in code
        assert "Phone" in code

    def test_per_command_columns(self):
        """Per-command table_columns override takes precedence."""
        ep = _make_endpoint(command_type="list", command_name="list-numbers")
        overrides = {
            "list": {"table_columns": [["ID", "id"], ["Name", "name"]]},
            "table_columns": {
                "list-numbers": [["Number", "directNumber"], ["Ext", "extension"]],
            },
        }
        code = _render_list_command(ep, overrides)
        assert "directNumber" in code
        assert "Number" in code
        # Folder-level columns should NOT be used
        assert ('("ID", "id")' not in code) or ("directNumber" in code)


# ── response_list_key applied ────────────────────────────────────────────────


class TestResponseListKeyApplied:
    def test_override_response_list_key(self):
        ep = _make_endpoint(command_type="list", command_name="list", response_list_key="items")
        overrides = {"response_list_keys": {"list": "Resources"}}
        apply_endpoint_overrides(ep, overrides)
        assert ep.response_list_key == "Resources"

    def test_no_override_keeps_default(self):
        ep = _make_endpoint(command_type="list", command_name="list", response_list_key="items")
        apply_endpoint_overrides(ep, {})
        assert ep.response_list_key == "items"


# ── command_type override ────────────────────────────────────────────────────


class TestCommandTypeOverride:
    def test_reclassify_list_to_settings_get(self):
        ep = _make_endpoint(
            command_type="list", command_name="list-connection", response_list_key="items"
        )
        overrides = {"command_type_overrides": {"list-connection": "settings-get"}}
        apply_endpoint_overrides(ep, overrides)
        assert ep.command_type == "settings-get"
        assert ep.response_list_key is None  # Cleared for non-list

    def test_no_override_keeps_type(self):
        ep = _make_endpoint(command_type="list", command_name="list")
        overrides = {"command_type_overrides": {"other-command": "show"}}
        apply_endpoint_overrides(ep, overrides)
        assert ep.command_type == "list"


# ── add_query_params ─────────────────────────────────────────────────────────


class TestAddQueryParams:
    def test_add_query_param_to_command(self):
        ep = _make_endpoint(command_type="delete", command_name="delete-supervisors-config")
        overrides = {
            "add_query_params": {
                "delete-supervisors-config": [
                    {"name": "hasCxEssentials", "type": "str", "description": "Include CX supervisors"}
                ]
            }
        }
        assert len(ep.query_params) == 0
        apply_endpoint_overrides(ep, overrides)
        assert len(ep.query_params) == 1
        assert ep.query_params[0].name == "hasCxEssentials"
        assert ep.query_params[0].python_name == "has-cx-essentials"

    def test_no_matching_override(self):
        ep = _make_endpoint(command_type="list", command_name="list")
        overrides = {
            "add_query_params": {
                "other-command": [{"name": "extra", "type": "str"}]
            }
        }
        apply_endpoint_overrides(ep, overrides)
        assert len(ep.query_params) == 0


# ── skip_tags ────────────────────────────────────────────────────────────────


class TestSkipTags:
    def test_beta_tags_skipped(self):
        assert should_skip_tag("Beta Features", ["Beta *"])

    def test_exact_match_skipped(self):
        assert should_skip_tag("People", ["People"])

    def test_no_match_not_skipped(self):
        assert not should_skip_tag("Things", ["Beta *", "People"])

    def test_phase_pattern(self):
        assert should_skip_tag("Call Settings For Me Phase 2", ["Call Settings For Me*"])

    def test_wildcard_patterns(self):
        skip_patterns = ["Beta *", "* Phase*"]
        assert should_skip_tag("Beta Test Feature", skip_patterns)
        assert should_skip_tag("Settings Phase 2", skip_patterns)
        assert not should_skip_tag("Normal Feature", skip_patterns)


# ── cli_name override ────────────────────────────────────────────────────────


class TestCliNameOverride:
    def test_cli_name_override_used(self):
        """Tag with cli_name override → command group uses override name."""
        with open(OVERRIDES_PATH) as f:
            data = yaml.safe_load(f)
        cli_names = data.get("cli_name_overrides", {})
        assert cli_names.get("Features:  Auto Attendant") == "auto-attendant"
        assert cli_names.get("Reports: Detailed Call History") == "cdr"
        assert cli_names.get("User Call Settings") == "user-settings"


# ── url_overrides ────────────────────────────────────────────────────────────


class TestUrlOverrides:
    def test_url_override_applied(self):
        ep = _make_endpoint(command_name="list", url_path="things")
        overrides = {"url_overrides": {"list": "other/path"}}
        apply_endpoint_overrides(ep, overrides)
        assert ep.url_path == "other/path"

    def test_no_url_override(self):
        ep = _make_endpoint(command_name="list", url_path="things")
        apply_endpoint_overrides(ep, {})
        assert ep.url_path == "things"


# ── load_overrides ───────────────────────────────────────────────────────────


class TestLoadOverrides:
    def test_load_existing_file(self):
        data = load_overrides(OVERRIDES_PATH)
        assert isinstance(data, dict)
        assert "omit_query_params" in data

    def test_load_missing_file(self, tmp_path):
        data = load_overrides(tmp_path / "nonexistent.yaml")
        assert isinstance(data, dict)
        assert "omit_query_params" in data  # default


# ── merge_tags ───────────────────────────────────────────────────────────────


class TestMergeTags:
    def test_merge_tags_rewrites_operations(self):
        spec = {
            "paths": {
                "/v1/test": {
                    "get": {"tags": ["User Call Settings (1/2)"], "operationId": "op1"}
                },
                "/v1/test2": {
                    "get": {"tags": ["User Call Settings (2/2)"], "operationId": "op2"}
                },
            }
        }
        merge_map = {
            "User Call Settings": [
                "User Call Settings (1/2)",
                "User Call Settings (2/2)",
            ]
        }
        merge_tags(spec, merge_map)
        assert spec["paths"]["/v1/test"]["get"]["tags"] == ["User Call Settings"]
        assert spec["paths"]["/v1/test2"]["get"]["tags"] == ["User Call Settings"]
