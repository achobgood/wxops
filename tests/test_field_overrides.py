"""Part C: Field overrides tests — field_overrides.yaml application."""

import json
import pytest
from pathlib import Path

import yaml

from tools.postman_parser import (
    DESTRUCTIVE_SEMANTICS,
    Endpoint,
    EndpointField,
    classify_real_semantics,
    load_overrides,
    apply_endpoint_overrides,
    camel_to_kebab,
)
from tools.command_renderer import (
    render_command_file,
    _render_list_command,
    ParamNameOverrideError,
    ReservedParamCollisionError,
)
from tools.openapi_parser import load_spec, parse_operation, parse_tag
from tools.generate_commands import KNOWN_GLOBAL_KEYS, should_skip_tag, merge_tags


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
        # Imported, not re-listed: the generator decides what a global key is,
        # and a second copy here silently drifts out of date (it did, for
        # tag_op_excludes). Contents of each global key are checked separately.
        known_global_keys = KNOWN_GLOBAL_KEYS
        known_tag_keys = {
            "list", "table_columns", "command_type_overrides", "response_list_keys",
            "url_overrides", "add_query_params", "keep_query_params",
            "command_name_overrides", "make_optional", "body_defaults",
            "param_name_overrides",
        }
        for key, value in data.items():
            if key in known_global_keys or key.startswith("_"):
                continue
            # It's a tag-level override
            if isinstance(value, dict):
                for subkey in value:
                    assert subkey in known_tag_keys, (
                        f"Unrecognized key '{subkey}' under tag '{key}'"
                    )

    def test_tag_op_excludes_shape(self):
        """tag_op_excludes: {spec.json|_global: {tag: [path globs]}}."""
        with open(OVERRIDES_PATH) as f:
            data = yaml.safe_load(f)
        raw = data.get("tag_op_excludes")
        if raw is None:
            return
        assert isinstance(raw, dict), "tag_op_excludes must be a dict"
        for scope, tags in raw.items():
            assert scope == "_global" or scope.endswith(".json"), (
                f"tag_op_excludes scope '{scope}' must be '_global' or a spec filename"
            )
            assert isinstance(tags, dict), f"tag_op_excludes['{scope}'] must be a dict"
            for tag, globs in tags.items():
                assert isinstance(globs, list), (
                    f"tag_op_excludes['{scope}']['{tag}'] must be a list of path globs"
                )
                for g in globs:
                    assert isinstance(g, str) and g.startswith("/"), (
                        f"tag_op_excludes['{scope}']['{tag}'] glob {g!r} must be a "
                        f"path string starting with '/'"
                    )

    def test_classify_flags_destructive_summary(self):
        """Signal 1: the summary leads with a destructive verb (issue #20)."""
        assert classify_real_semantics(
            "Delete Outgoing Permission Access Code Location", []
        ) == "delete"
        assert classify_real_semantics("Purge inactive Teams", []) == "purge"
        assert classify_real_semantics("Remove Preview Task", []) == "remove"

    def test_classify_flags_delete_only_body(self):
        """Signal 2: summary lies, but every body field can only take away.

        The person/virtual-line/workspace accessCodes PUTs say "Modify Access
        Codes" and accept only deleteCodes. Summary-scanning never sees these.
        """
        body = [EndpointField("deleteCodes", "delete-codes", "array", "Access Codes to delete.")]
        assert classify_real_semantics("Modify Access Codes for a Person", body) == "delete"

    def test_classify_ignores_genuine_update_with_a_delete_flag(self):
        """A body that can BOTH add and delete is an update, not a delete.

        "Modify Dial Patterns" takes dialPatterns (add or delete) alongside
        deleteAllDialPatterns. Flagging it would mislabel a real update, so
        signal 2 requires *every* field to be delete-shaped.
        """
        body = [
            EndpointField("dialPatterns", "dial-patterns", "array", "Add or delete."),
            EndpointField("deleteAllDialPatterns", "delete-all-dial-patterns", "boolean", "Delete all."),
        ]
        assert classify_real_semantics("Modify Dial Patterns", body) is None

    def test_classify_leaves_ordinary_updates_alone(self):
        assert classify_real_semantics("Update Voicemail Rules", []) is None
        assert classify_real_semantics("Create Access Codes for a Person", []) is None

    def test_verb_semantics_ack_shape(self):
        """verb_semantics_ack: {spec.json|_global: {"METHOD /path": verb}}."""
        with open(OVERRIDES_PATH) as f:
            data = yaml.safe_load(f)
        raw = data.get("verb_semantics_ack")
        if raw is None:
            return
        assert isinstance(raw, dict), "verb_semantics_ack must be a dict"
        for scope, entries in raw.items():
            assert scope == "_global" or scope.endswith(".json"), (
                f"verb_semantics_ack scope '{scope}' must be '_global' or a spec filename"
            )
            assert isinstance(entries, dict)
            for key, verb in entries.items():
                method, _, path = key.partition(" ")
                assert method in ("PUT", "POST", "PATCH"), (
                    f"verb_semantics_ack key {key!r} must start with PUT/POST/PATCH — "
                    f"a real DELETE needs no ack"
                )
                assert path.startswith("/"), (
                    f"verb_semantics_ack key {key!r} path must start with '/'"
                )
                assert verb in DESTRUCTIVE_SEMANTICS, (
                    f"verb_semantics_ack {key!r} declares {verb!r}, which is not a "
                    f"known destructive verb {sorted(DESTRUCTIVE_SEMANTICS)}"
                )

    def test_verb_semantics_acks_still_match_the_spec(self):
        """An ack must keep describing a real, still-destructive operation.

        Guards ack rot in both directions: upstream fixing the verb (the op is
        no longer a mismatch, so the ack is dead weight) and upstream changing
        the semantics under a stale ack. Known issue #20.
        """
        with open(OVERRIDES_PATH) as f:
            data = yaml.safe_load(f)
        raw = data.get("verb_semantics_ack") or {}
        specs_dir = OVERRIDES_PATH.parent.parent / "specs"
        for scope, entries in raw.items():
            if scope == "_global":
                continue
            spec = load_spec(str(specs_dir / scope))
            for key, declared in entries.items():
                method, _, path = key.partition(" ")
                assert path in spec["paths"], (
                    f"verb_semantics_ack {key!r} names a path that is no longer in "
                    f"{scope} — upstream moved or removed it; drop or update the ack"
                )
                op = spec["paths"][path].get(method.lower())
                assert op is not None, (
                    f"verb_semantics_ack {key!r}: {scope} no longer defines {method} "
                    f"on that path"
                )
                body_fields = parse_operation(
                    method.lower(), path, op, spec, [], set()
                ).body_fields
                actual = classify_real_semantics(op.get("summary", ""), body_fields)
                assert actual == declared, (
                    f"verb_semantics_ack {key!r} is acked as {declared!r} but the spec "
                    f"now classifies it as {actual!r} — re-read the operation and "
                    f"update or remove the ack"
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
        raw = data.get("skip_tags", {})
        if isinstance(raw, dict):
            all_patterns = []
            for key, val in raw.items():
                if isinstance(val, list):
                    all_patterns.extend(val)
        else:
            all_patterns = list(raw)
        for pattern in all_patterns:
            assert isinstance(pattern, str), f"skip_tags pattern must be str, got {type(pattern).__name__}: {pattern}"

    def test_cli_name_overrides_are_kebab(self):
        with open(OVERRIDES_PATH) as f:
            data = yaml.safe_load(f)
        raw = data.get("cli_name_overrides", {})
        if "_global" in raw or any(k.endswith(".json") for k in raw):
            all_overrides = {}
            for key, val in raw.items():
                if isinstance(val, dict):
                    all_overrides.update(val)
        else:
            all_overrides = raw
        for tag, cli_name in all_overrides.items():
            assert "_" not in cli_name, (
                f"cli_name '{cli_name}' for tag '{tag}' should be kebab-case"
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


# ── param_name_overrides ─────────────────────────────────────────────────────


def _fields_collision_endpoint(command_name="update-contacts"):
    """An endpoint whose spec query param is literally named 'fields'.

    Real case: upstream's PATCH .../campaigns/{campaignId}/contacts/{contactId}
    (tag 'Contact List Management'), added in the 2026-07 spec refresh.
    """
    return _make_endpoint(
        method="PATCH",
        command_type="update",
        command_name=command_name,
        url_path="v3/campaign-management/campaigns/{campaignId}/contacts/{contactId}",
        path_vars=["campaignId", "contactId"],
        query_params=[EndpointField(
            name="fields", python_name="fields", field_type="string",
            description="Contact field names to include in the response.",
        )],
    )


class TestParamNameOverrides:
    def test_unrenamed_fields_param_still_fails_loudly(self):
        """Without an override the reserved-name guard must still fire.

        This is the control: if it ever stops raising, the tests below would
        pass for the wrong reason.
        """
        ep = _fields_collision_endpoint()
        with pytest.raises(ReservedParamCollisionError):
            render_command_file("cc-contact-list", [ep], {})

    def test_rename_changes_flag_but_not_wire_name(self):
        """--contact-fields on the CLI; still params["fields"] on the wire.

        The two are different operations — a spec 'fields' param is server-side
        field selection, --fields is a client-side JMESPath post-filter — so
        both must coexist rather than one replacing the other.
        """
        ep = _fields_collision_endpoint()
        overrides = {"param_name_overrides": {"update-contacts": {"fields": "contact-fields"}}}
        code = render_command_file("cc-contact-list", [ep], overrides)
        assert '"--contact-fields"' in code
        assert 'params["fields"] = contact_fields' in code
        # the renderer's own universal --fields survives alongside it
        assert '"--fields"' in code
        # exactly one parameter is named exactly `fields` (the injected one).
        # Match on the line start so `contact_fields:` is not counted as a
        # substring hit — the whole point is that they are two distinct params.
        assert code.count("\n    fields: str = typer.Option") == 1
        assert code.count("\n    contact_fields: str = typer.Option") == 1

    def test_stale_command_name_raises(self):
        """An entry naming a command the tag no longer renders must fail."""
        ep = _fields_collision_endpoint()
        overrides = {"param_name_overrides": {"no-such-command": {"fields": "contact-fields"}}}
        with pytest.raises(ParamNameOverrideError, match="no-such-command"):
            render_command_file("cc-contact-list", [ep], overrides)

    def test_stale_param_name_raises(self):
        """Upstream renaming/dropping the param must fail, not sit inert."""
        ep = _fields_collision_endpoint()
        overrides = {"param_name_overrides": {"update-contacts": {"gone": "contact-fields"}}}
        with pytest.raises(ParamNameOverrideError, match="gone"):
            render_command_file("cc-contact-list", [ep], overrides)

    def test_rename_onto_another_reserved_name_raises(self):
        """Renaming 'fields' to 'output' just moves the collision."""
        ep = _fields_collision_endpoint()
        overrides = {"param_name_overrides": {"update-contacts": {"fields": "output"}}}
        with pytest.raises(ParamNameOverrideError, match="output"):
            render_command_file("cc-contact-list", [ep], overrides)

    def test_live_override_matches_the_shipped_spec(self):
        """The shipped override must still describe a real endpoint.

        Guards the same rot the renderer does, but against the real spec, so a
        future refresh that drops the param fails here too.
        """
        with open(OVERRIDES_PATH) as f:
            data = yaml.safe_load(f)
        block = data.get("Contact List Management", {}).get("param_name_overrides", {})
        assert block.get("update-contacts", {}).get("fields") == "contact-fields", (
            "the Contact List Management rename is missing — regeneration will "
            "fail with ReservedParamCollisionError"
        )


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
        from tools.generate_commands import resolve_cli_name_overrides
        with open(OVERRIDES_PATH) as f:
            data = yaml.safe_load(f)
        cli_names = resolve_cli_name_overrides(data.get("cli_name_overrides"), "webex-cloud-calling.json")
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
