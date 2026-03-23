"""Part A: OpenAPI parser tests — spec → Endpoint conversion."""

import json
import pytest
from pathlib import Path

from tools.openapi_parser import (
    resolve_ref,
    parse_parameters,
    parse_request_body,
    detect_command_type,
    extract_response_list_key,
    extract_response_id_key,
    parse_operation,
    parse_tag,
    _get_response_schema,
    _openapi_type_to_field_type,
    _path_to_raw_path,
    _path_to_url_path,
    generate_body_example,
)


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def spec():
    with open(FIXTURES / "mini-openapi.json") as f:
        return json.load(f)


# ── resolve_ref ──────────────────────────────────────────────────────────────


class TestResolveRef:
    def test_resolve_schema_ref(self, spec):
        result = resolve_ref(spec, "#/components/schemas/Thing")
        assert result["type"] == "object"
        assert "id" in result["properties"]
        assert "name" in result["properties"]

    def test_resolve_parameter_ref(self, spec):
        result = resolve_ref(spec, "#/components/parameters/OrgIdParam")
        assert result["name"] == "orgId"
        assert result["in"] == "query"

    def test_resolve_nested_ref(self, spec):
        result = resolve_ref(spec, "#/components/schemas/ThingConfig")
        assert "timeout" in result["properties"]
        assert "retries" in result["properties"]


# ── parse_parameters ─────────────────────────────────────────────────────────


class TestParseParameters:
    def test_path_param_extracted(self, spec):
        params = [{"name": "thingId", "in": "path", "required": True, "schema": {"type": "string"}}]
        path_vars, query_params, auto_inject = parse_parameters(params, spec)
        assert path_vars == ["thingId"]
        assert query_params == []
        assert auto_inject == []

    def test_query_params_extracted(self, spec):
        params = spec["paths"]["/v1/things"]["get"]["parameters"]
        path_vars, query_params, auto_inject = parse_parameters(params, spec, omit_query_params=["orgId"])
        assert path_vars == []
        assert len(query_params) == 2  # max, status (orgId omitted)
        names = [qp.name for qp in query_params]
        assert "max" in names
        assert "status" in names
        assert "orgId" not in names
        assert auto_inject == []

    def test_query_param_types(self, spec):
        params = spec["paths"]["/v1/things"]["get"]["parameters"]
        _, query_params, _ = parse_parameters(params, spec, omit_query_params=["orgId"])
        max_param = next(qp for qp in query_params if qp.name == "max")
        assert max_param.field_type == "number"
        status_param = next(qp for qp in query_params if qp.name == "status")
        assert status_param.field_type == "string"
        assert status_param.enum_values == ["active", "inactive"]

    def test_ref_param_resolved(self, spec):
        params = spec["paths"]["/v1/ref-param"]["get"]["parameters"]
        path_vars, query_params, auto_inject = parse_parameters(params, spec)
        assert len(query_params) == 1
        assert query_params[0].name == "orgId"
        assert auto_inject == []

    def test_omit_query_params(self, spec):
        params = spec["paths"]["/v1/things"]["get"]["parameters"]
        _, query_params, _ = parse_parameters(params, spec, omit_query_params=["orgId", "max"])
        names = [qp.name for qp in query_params]
        assert "orgId" not in names
        assert "max" not in names
        assert "status" in names


# ── parse_request_body ───────────────────────────────────────────────────────


class TestParseRequestBody:
    def test_post_with_body(self, spec):
        op = spec["paths"]["/v1/things"]["post"]
        fields = parse_request_body(op, spec)
        names = [f.name for f in fields]
        assert "name" in names
        assert "description" in names
        assert "enabled" in names
        assert "thingType" in names

    def test_required_fields_marked(self, spec):
        op = spec["paths"]["/v1/things"]["post"]
        fields = parse_request_body(op, spec)
        name_field = next(f for f in fields if f.name == "name")
        desc_field = next(f for f in fields if f.name == "description")
        assert name_field.required is True
        assert desc_field.required is False

    def test_enum_values_preserved(self, spec):
        op = spec["paths"]["/v1/things"]["post"]
        fields = parse_request_body(op, spec)
        type_field = next(f for f in fields if f.name == "thingType")
        assert type_field.enum_values == ["A", "B", "C"]

    def test_nested_ref_becomes_object(self, spec):
        op = spec["paths"]["/v1/nested-body"]["post"]
        fields = parse_request_body(op, spec)
        config_field = next(f for f in fields if f.name == "config")
        assert config_field.field_type == "object"

    def test_array_field_type(self, spec):
        op = spec["paths"]["/v1/nested-body"]["post"]
        fields = parse_request_body(op, spec)
        tags_field = next(f for f in fields if f.name == "tags")
        assert tags_field.field_type == "array"

    def test_no_request_body(self, spec):
        op = spec["paths"]["/v1/things/{thingId}"]["get"]
        fields = parse_request_body(op, spec)
        assert fields == []

    def test_python_name_is_kebab(self, spec):
        op = spec["paths"]["/v1/things"]["post"]
        fields = parse_request_body(op, spec)
        type_field = next(f for f in fields if f.name == "thingType")
        assert type_field.python_name == "thing-type"


# ── detect_command_type ──────────────────────────────────────────────────────


class TestDetectCommandType:
    def test_list_endpoint(self, spec):
        op = spec["paths"]["/v1/things"]["get"]
        assert detect_command_type("GET", "/v1/things", op, spec) == "list"

    def test_show_endpoint(self, spec):
        op = spec["paths"]["/v1/things/{thingId}"]["get"]
        assert detect_command_type("GET", "/v1/things/{thingId}", op, spec) == "show"

    def test_post_creates(self, spec):
        op = spec["paths"]["/v1/things"]["post"]
        assert detect_command_type("POST", "/v1/things", op, spec) == "create"

    def test_put_updates(self, spec):
        op = spec["paths"]["/v1/things/{thingId}"]["put"]
        assert detect_command_type("PUT", "/v1/things/{thingId}", op, spec) == "update"

    def test_delete(self, spec):
        op = spec["paths"]["/v1/things/{thingId}"]["delete"]
        assert detect_command_type("DELETE", "/v1/things/{thingId}", op, spec) == "delete"

    def test_settings_get_flat_object(self, spec):
        """Flat object response (no arrays) → settings-get."""
        op = spec["paths"]["/v1/things/{thingId}/settings"]["get"]
        assert detect_command_type("GET", "/v1/things/{thingId}/settings", op, spec) == "settings-get"

    def test_direct_array_response(self, spec):
        """Response that is a bare array (no wrapper) → list."""
        op = spec["paths"]["/v1/tags"]["get"]
        assert detect_command_type("GET", "/v1/tags", op, spec) == "list"

    def test_action_post_with_invoke(self, spec):
        op = spec["paths"]["/v1/things/{thingId}/actions/invoke"]["post"]
        assert detect_command_type("POST", "/v1/things/{thingId}/actions/invoke", op, spec) == "action"

    def test_me_endpoint_is_show(self, spec):
        """Path ending in /me → show."""
        op = spec["paths"]["/v1/things/me"]["get"]
        assert detect_command_type("GET", "/v1/things/me", op, spec) == "show"

    def test_allof_with_array_is_list(self, spec):
        """allOf response with array property → list."""
        op = spec["paths"]["/v1/combined"]["get"]
        assert detect_command_type("GET", "/v1/combined", op, spec) == "list"


# ── extract_response_list_key ────────────────────────────────────────────────


class TestExtractResponseListKey:
    def test_standard_items_key(self, spec):
        op = spec["paths"]["/v1/things"]["get"]
        assert extract_response_list_key(op, spec) == "items"

    def test_direct_array_returns_none(self, spec):
        """Direct array response → None (renderer handles raw list)."""
        op = spec["paths"]["/v1/tags"]["get"]
        assert extract_response_list_key(op, spec) is None

    def test_allof_merged_key(self, spec):
        op = spec["paths"]["/v1/combined"]["get"]
        assert extract_response_list_key(op, spec) == "records"

    def test_multi_array_prefers_required(self, spec):
        """Multiple arrays: required one wins."""
        op = spec["paths"]["/v1/multi-array"]["get"]
        assert extract_response_list_key(op, spec) == "primary"

    def test_no_response_returns_none(self, spec):
        op = spec["paths"]["/v1/things/{thingId}"]["delete"]
        assert extract_response_list_key(op, spec) is None


# ── extract_response_id_key ──────────────────────────────────────────────────


class TestExtractResponseIdKey:
    def test_standard_id(self, spec):
        op = spec["paths"]["/v1/things"]["post"]
        assert extract_response_id_key(op, spec) == "id"

    def test_custom_id_key(self, spec):
        op = spec["paths"]["/v1/nested-body"]["post"]
        assert extract_response_id_key(op, spec) == "customId"

    def test_no_201_response(self, spec):
        op = spec["paths"]["/v1/things/{thingId}"]["get"]
        assert extract_response_id_key(op, spec) is None


# ── singleton vs list classification ─────────────────────────────────────────


class TestSingletonVsListClassification:
    def test_flat_object_is_singleton(self, spec):
        """Response with only scalar properties → settings-get, not list."""
        op = spec["paths"]["/v1/things/{thingId}/settings"]["get"]
        ct = detect_command_type("GET", "/v1/things/{thingId}/settings", op, spec)
        assert ct == "settings-get"

    def test_object_with_array_is_list(self, spec):
        """Response with an array property → list."""
        op = spec["paths"]["/v1/things"]["get"]
        ct = detect_command_type("GET", "/v1/things", op, spec)
        assert ct == "list"


# ── parse_operation ──────────────────────────────────────────────────────────


class TestParseOperation:
    def test_list_operation(self, spec):
        op = spec["paths"]["/v1/things"]["get"]
        ep = parse_operation("get", "/v1/things", op, spec, omit_query_params=["orgId"])
        assert ep.command_type == "list"
        assert ep.method == "GET"
        assert ep.url_path == "things"
        assert ep.response_list_key == "items"
        assert len(ep.query_params) == 2  # max, status

    def test_show_operation(self, spec):
        op = spec["paths"]["/v1/things/{thingId}"]["get"]
        ep = parse_operation("get", "/v1/things/{thingId}", op, spec)
        assert ep.command_type == "show"
        assert ep.path_vars == ["thingId"]

    def test_create_operation(self, spec):
        op = spec["paths"]["/v1/things"]["post"]
        ep = parse_operation("post", "/v1/things", op, spec)
        assert ep.command_type == "create"
        assert ep.response_id_key == "id"
        assert len(ep.body_fields) == 4

    def test_delete_operation(self, spec):
        op = spec["paths"]["/v1/things/{thingId}"]["delete"]
        ep = parse_operation("delete", "/v1/things/{thingId}", op, spec)
        assert ep.command_type == "delete"
        assert ep.path_vars == ["thingId"]

    def test_url_path_strips_v1(self, spec):
        op = spec["paths"]["/v1/things"]["get"]
        ep = parse_operation("get", "/v1/things", op, spec)
        assert ep.url_path == "things"
        assert not ep.url_path.startswith("v1/")

    def test_deprecated_flag(self, spec):
        op = spec["paths"]["/v1/deprecated-thing"]["get"]
        ep = parse_operation("get", "/v1/deprecated-thing", op, spec)
        assert ep.deprecated is True

    def test_json_body_example_for_nested(self, spec):
        op = spec["paths"]["/v1/nested-body"]["post"]
        ep = parse_operation("post", "/v1/nested-body", op, spec)
        assert ep.json_body_example is not None
        parsed = json.loads(ep.json_body_example)
        assert "name" in parsed
        assert "config" in parsed

    def test_no_json_body_example_for_flat(self, spec):
        op = spec["paths"]["/v1/things/{thingId}"]["put"]
        ep = parse_operation("put", "/v1/things/{thingId}", op, spec)
        assert ep.json_body_example is None


# ── parse_tag ────────────────────────────────────────────────────────────────


class TestParseTag:
    def test_parse_things_tag(self, spec):
        endpoints, skipped = parse_tag("Things", spec, omit_query_params=["orgId"])
        # list, create, show, update, delete, settings-get, tags(list), me(show), action
        # minus upload (skipped)
        types = [ep.command_type for ep in endpoints]
        assert "list" in types
        assert "create" in types
        assert "show" in types
        assert "update" in types
        assert "delete" in types

    def test_upload_skipped(self, spec):
        _, skipped = parse_tag("Things", spec)
        assert len(skipped) == 1
        assert "Upload" in skipped[0] or "upload" in skipped[0].lower()

    def test_command_names_assigned(self, spec):
        endpoints, _ = parse_tag("Things", spec)
        for ep in endpoints:
            assert ep.command_name != "", f"Missing command_name for {ep.name}"

    def test_no_duplicate_command_names(self, spec):
        endpoints, _ = parse_tag("Things", spec)
        names = [ep.command_name for ep in endpoints]
        assert len(names) == len(set(names)), f"Duplicate command names: {names}"

    def test_dedup_across_tags(self, spec):
        """Operations processed by one tag don't appear again in another."""
        seen = set()
        ep1, _ = parse_tag("Things", spec, seen_operation_ids=seen)
        ep2, _ = parse_tag("Things", spec, seen_operation_ids=seen)
        # Second parse should return nothing (all ops already seen)
        assert len(ep2) == 0


# ── path conversion helpers ──────────────────────────────────────────────────


class TestPathHelpers:
    def test_path_to_raw_path(self):
        assert _path_to_raw_path("/v1/things/{thingId}/settings") == [
            "v1", "things", ":thingId", "settings"
        ]

    def test_path_to_url_path_strips_v1(self):
        assert _path_to_url_path("/v1/things/{thingId}") == "things/{thingId}"

    def test_path_to_url_path_preserves_non_v1(self):
        assert _path_to_url_path("/identity/v1/scim") == "identity/v1/scim"


# ── type conversion ──────────────────────────────────────────────────────────


class TestTypeConversion:
    def test_integer_to_number(self):
        assert _openapi_type_to_field_type({"type": "integer"}) == "number"

    def test_number_to_number(self):
        assert _openapi_type_to_field_type({"type": "number"}) == "number"

    def test_boolean_to_bool(self):
        assert _openapi_type_to_field_type({"type": "boolean"}) == "bool"

    def test_array_to_array(self):
        assert _openapi_type_to_field_type({"type": "array"}) == "array"

    def test_object_to_object(self):
        assert _openapi_type_to_field_type({"type": "object"}) == "object"

    def test_string_default(self):
        assert _openapi_type_to_field_type({"type": "string"}) == "string"

    def test_missing_type_defaults_to_string(self):
        assert _openapi_type_to_field_type({}) == "string"


# ── generate_body_example ────────────────────────────────────────────────────


class TestGenerateBodyExample:
    def test_nested_fields_generate_example(self, spec):
        op = spec["paths"]["/v1/nested-body"]["post"]
        example = generate_body_example(op, spec)
        assert example is not None
        parsed = json.loads(example)
        assert "name" in parsed
        assert "config" in parsed

    def test_flat_body_returns_none(self, spec):
        op = spec["paths"]["/v1/things/{thingId}"]["put"]
        example = generate_body_example(op, spec)
        assert example is None

    def test_no_body_returns_none(self, spec):
        op = spec["paths"]["/v1/things"]["get"]
        example = generate_body_example(op, spec)
        assert example is None


# ── _get_response_schema ─────────────────────────────────────────────────────


class TestGetResponseSchema:
    def test_standard_200(self, spec):
        op = spec["paths"]["/v1/things"]["get"]
        schema = _get_response_schema(op, spec, "200")
        assert schema is not None
        assert "items" in schema["properties"]

    def test_ref_response_resolved(self, spec):
        op = spec["paths"]["/v1/things/{thingId}"]["get"]
        schema = _get_response_schema(op, spec, "200")
        assert schema is not None
        assert "id" in schema["properties"]

    def test_allof_merged(self, spec):
        op = spec["paths"]["/v1/combined"]["get"]
        schema = _get_response_schema(op, spec, "200")
        assert schema is not None
        assert "totalCount" in schema["properties"]
        assert "records" in schema["properties"]

    def test_missing_status_returns_none(self, spec):
        op = spec["paths"]["/v1/things"]["get"]
        schema = _get_response_schema(op, spec, "404")
        assert schema is None

    def test_no_content_returns_none(self, spec):
        op = spec["paths"]["/v1/things/{thingId}"]["delete"]
        schema = _get_response_schema(op, spec, "204")
        assert schema is None


# ── parse_parameters auto_inject ─────────────────────────────────────────────


def test_parse_parameters_auto_inject():
    """orgId in auto_inject_params is separated from query_params."""
    params = [
        {"name": "orgId", "in": "query", "schema": {"type": "string"}},
        {"name": "locationId", "in": "query", "schema": {"type": "string"}},
        {"name": "id", "in": "path", "schema": {"type": "string"}},
    ]
    path_vars, query_params, auto_inject = parse_parameters(
        params, {}, omit_query_params=[], auto_inject_params={"orgId"}
    )
    assert path_vars == ["id"]
    assert [qp.name for qp in query_params] == ["locationId"]
    assert auto_inject == ["orgId"]


def test_parse_parameters_no_auto_inject():
    """Without auto_inject, orgId appears in query_params normally."""
    params = [
        {"name": "orgId", "in": "query", "schema": {"type": "string"}},
    ]
    path_vars, query_params, auto_inject = parse_parameters(params, {})
    assert [qp.name for qp in query_params] == ["orgId"]
    assert auto_inject == []
