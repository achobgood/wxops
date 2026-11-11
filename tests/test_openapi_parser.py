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
    extract_response_item_fields,
    parse_operation,
    parse_tag,
    _get_response_schema,
    _openapi_type_to_field_type,
    _path_to_raw_path,
    _path_to_url_path,
    generate_body_example,
    _MAX_EXAMPLE_DEPTH,
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
        path_vars, query_params, auto_inject, auto_inject_path, _ = parse_parameters(params, spec)
        assert path_vars == ["thingId"]
        assert query_params == []
        assert auto_inject == []
        assert auto_inject_path == []

    def test_query_params_extracted(self, spec):
        params = spec["paths"]["/v1/things"]["get"]["parameters"]
        path_vars, query_params, auto_inject, auto_inject_path, _ = parse_parameters(
            params, spec, omit_query_params=["orgId"]
        )
        assert path_vars == []
        assert len(query_params) == 2  # max, status (orgId omitted)
        names = [qp.name for qp in query_params]
        assert "max" in names
        assert "status" in names
        assert "orgId" not in names
        assert auto_inject == []
        assert auto_inject_path == []

    def test_query_param_types(self, spec):
        params = spec["paths"]["/v1/things"]["get"]["parameters"]
        _, query_params, _, _, _ = parse_parameters(params, spec, omit_query_params=["orgId"])
        max_param = next(qp for qp in query_params if qp.name == "max")
        assert max_param.field_type == "number"
        status_param = next(qp for qp in query_params if qp.name == "status")
        assert status_param.field_type == "string"
        assert status_param.enum_values == ["active", "inactive"]

    def test_ref_param_resolved(self, spec):
        params = spec["paths"]["/v1/ref-param"]["get"]["parameters"]
        path_vars, query_params, auto_inject, auto_inject_path, _ = parse_parameters(params, spec)
        assert len(query_params) == 1
        assert query_params[0].name == "orgId"
        assert auto_inject == []
        assert auto_inject_path == []

    def test_omit_query_params(self, spec):
        params = spec["paths"]["/v1/things"]["get"]["parameters"]
        _, query_params, _, _, _ = parse_parameters(params, spec, omit_query_params=["orgId", "max"])
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


# ── extract_response_item_fields ─────────────────────────────────────────────


class TestExtractResponseItemFields:
    """Item-schema fields feed the renderer's default table columns, so they
    are keyed by the key the generated code extracts with — not by a guess."""

    def test_resolves_a_reffed_item_schema(self, spec):
        op = spec["paths"]["/v1/things"]["get"]
        fields = extract_response_item_fields(op, spec)
        assert [f.name for f in fields["items"]] == ["id", "name", "enabled"]
        assert fields["items"][2].field_type == "boolean"

    def test_direct_array_is_keyed_items_like_the_renderer_reads_it(self, spec):
        op = spec["paths"]["/v1/tags"]["get"]
        assert [f.name for f in extract_response_item_fields(op, spec)["items"]] == ["name"]

    def test_every_array_property_is_kept_for_list_key_overrides(self, spec):
        """response_list_keys can repoint extraction after parse; both keys
        must already be resolved or the override renders blank columns."""
        op = spec["paths"]["/v1/multi-array"]["get"]
        fields = extract_response_item_fields(op, spec)
        assert set(fields) <= {"primary", "secondary"}

    def test_no_response_schema_returns_empty(self, spec):
        op = spec["paths"]["/v1/things/{thingId}"]["delete"]
        assert extract_response_item_fields(op, spec) == {}

    def test_parse_operation_attaches_them_to_list_endpoints(self, spec):
        ep = parse_operation("get", "/v1/things", spec["paths"]["/v1/things"]["get"], spec)
        assert ep.command_type == "list"
        assert [f.name for f in ep.response_item_fields["items"]] == ["id", "name", "enabled"]

    def test_parse_operation_skips_them_for_non_list_endpoints(self, spec):
        op = spec["paths"]["/v1/things/{thingId}"]["get"]
        assert parse_operation("get", "/v1/things/{thingId}", op, spec).response_item_fields == {}


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

    def test_json_body_example_for_flat_too(self, spec):
        op = spec["paths"]["/v1/things/{thingId}"]["put"]
        ep = parse_operation("put", "/v1/things/{thingId}", op, spec)
        assert ep.json_body_example is not None
        json.loads(ep.json_body_example)


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


# ── colon-action paths ───────────────────────────────────────────────────────


class TestColonActionPaths:
    def test_raw_path_splits_colon_action(self):
        """Path param with colon-action suffix splits into two segments."""
        result = _path_to_raw_path("/{orgId}/flows/{flowId}:publish")
        assert result == [":orgId", "flows", ":flowId", "publish"]

    def test_raw_path_plain_colon_action(self):
        """Non-param segment with colon-action splits correctly."""
        result = _path_to_raw_path("/{orgId}/flows:import")
        assert result == [":orgId", "flows", "import"]

    def test_raw_path_no_colon_unchanged(self):
        """Normal paths without colons are unchanged."""
        result = _path_to_raw_path("/v1/things/{thingId}")
        assert result == ["v1", "things", ":thingId"]

    def test_url_path_preserves_colon(self):
        """URL path keeps the colon intact for the HTTP request."""
        result = _path_to_url_path("/{orgId}/flows/{flowId}:publish")
        assert result == "{orgId}/flows/{flowId}:publish"

    def test_url_path_preserves_plain_colon(self):
        result = _path_to_url_path("/{orgId}/flows:import")
        assert result == "{orgId}/flows:import"


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

    def test_flat_body_returns_example_too(self, spec):
        op = spec["paths"]["/v1/things/{thingId}"]["put"]
        example = generate_body_example(op, spec)
        assert example is not None

    def test_no_body_returns_none(self, spec):
        op = spec["paths"]["/v1/things"]["get"]
        example = generate_body_example(op, spec)
        assert example is None


# ── skeleton truncation ──────────────────────────────────────────────────────
#
# The skeleton is the documented escape hatch for every body field the
# generator cannot render as a flag, so a field it drops is unreachable by ANY
# route. These pin the two guarantees that replaced the old `depth > 2` and
# `ordered[:8]` cutoffs: nothing is dropped, and where expansion genuinely
# cannot continue it SAYS so.


def _body_op(schema):
    return {"requestBody": {"content": {"application/json": {"schema": schema}}}}


class TestSkeletonNeverTruncatesSilently:
    def test_no_property_cap(self):
        """`ordered[:8]` dropped everything past the eighth property."""
        props = {f"f{i}": {"type": "string"} for i in range(30)}
        op = _body_op({"type": "object", "properties": props,
                       "required": list(props)})
        parsed = json.loads(generate_body_example(op, {}))
        assert len(parsed) == 30

    def test_nested_object_is_not_a_scalar(self):
        """`depth > 2` rendered a nested object as the string "..."."""
        leaf = {"type": "object", "required": ["deep"],
                "properties": {"deep": {"type": "string"}}}
        op = _body_op({
            "type": "object", "required": ["a"],
            "properties": {"a": {"type": "object", "required": ["b"], "properties": {
                "b": {"type": "object", "required": ["c"], "properties": {
                    "c": leaf}}}}}})
        parsed = json.loads(generate_body_example(op, {}))
        assert parsed["a"]["b"]["c"] == {"deep": "..."}

    def test_all_of_body_is_composed(self):
        """A body declared purely as allOf used to parse as having no fields."""
        spec = {"components": {"schemas": {"Base": {
            "type": "object", "required": ["name"],
            "properties": {"name": {"type": "string"}}}}}}
        op = _body_op({"allOf": [
            {"type": "object", "required": ["id"],
             "properties": {"id": {"type": "string"}}},
            {"$ref": "#/components/schemas/Base"}]})
        parsed = json.loads(generate_body_example(op, spec))
        assert set(parsed) == {"id", "name"}

    def test_recursive_schema_stops_and_says_so(self):
        spec = {"components": {"schemas": {"Node": {
            "type": "object", "required": ["label", "child"],
            "properties": {"label": {"type": "string"},
                           "child": {"$ref": "#/components/schemas/Node"}}}}}}
        op = _body_op({"type": "object", "required": ["root"],
                       "properties": {"root": {"$ref": "#/components/schemas/Node"}}})
        notes = []
        parsed = json.loads(generate_body_example(op, spec, notes=notes))
        # Type-correct where it stops: `{}`, never the scalar "...".
        assert parsed["root"]["child"] == {}
        assert notes and "recurses" in notes[0]

    def test_depth_backstop_stops_and_says_so(self):
        schema = {"type": "string"}
        for _ in range(_MAX_EXAMPLE_DEPTH + 3):
            schema = {"type": "object", "required": ["n"],
                      "properties": {"n": schema}}
        notes = []
        generate_body_example(_body_op(schema), {}, notes=notes)
        assert notes and "deeper than" in notes[0]

    def test_complete_skeleton_reports_no_note(self):
        """A note must mean something — silence is the normal case."""
        notes = []
        generate_body_example(
            _body_op({"type": "object", "required": ["a"],
                      "properties": {"a": {"type": "string"}}}), {}, notes=notes)
        assert notes == []


class TestRequiredOnlyExample:
    def test_prunes_optional_fields(self):
        op = _body_op({"type": "object", "required": ["name"], "properties": {
            "name": {"type": "string"}, "id": {"type": "string"},
            "createdTime": {"type": "integer"}}})
        assert json.loads(generate_body_example(op, {}, required_only=True)) \
            == {"name": "..."}

    def test_keeps_required_nested_objects_whole(self):
        """An inner object declaring no `required` has nothing to prune by."""
        op = _body_op({"type": "object", "required": ["address"], "properties": {
            "address": {"type": "object", "properties": {
                "city": {"type": "string"}, "country": {"type": "string"}}},
            "note": {"type": "string"}}})
        parsed = json.loads(generate_body_example(op, {}, required_only=True))
        assert parsed == {"address": {"city": "...", "country": "..."}}


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
    path_vars, query_params, auto_inject, auto_inject_path, _ = parse_parameters(
        params, {}, omit_query_params=[], auto_inject_params={"orgId"}
    )
    assert path_vars == ["id"]
    assert [qp.name for qp in query_params] == ["locationId"]
    assert auto_inject == ["orgId"]
    assert auto_inject_path == []


def test_parse_parameters_no_auto_inject():
    """Without auto_inject, orgId appears in query_params normally."""
    params = [
        {"name": "orgId", "in": "query", "schema": {"type": "string"}},
    ]
    path_vars, query_params, auto_inject, auto_inject_path, _ = parse_parameters(params, {})
    assert [qp.name for qp in query_params] == ["orgId"]
    assert auto_inject == []
    assert auto_inject_path == []


def test_parse_parameters_auto_inject_path():
    """Path params in auto_inject are tracked in auto_inject_path_names but remain in path_vars."""
    params = [
        {"name": "orgId", "in": "path", "schema": {"type": "string"}, "required": True},
        {"name": "id", "in": "path", "schema": {"type": "string"}, "required": True},
    ]
    path_vars, query_params, auto_inject, auto_inject_path, _ = parse_parameters(
        params, {}, auto_inject_params={"orgId"}
    )
    # Path var still present so URL substitution works
    assert path_vars == ["orgId", "id"]
    # But orgId is flagged for auto-injection (no CLI arg generated)
    assert auto_inject_path == ["orgId"]
    assert auto_inject == []


def test_body_example_generated_for_flat_schemas_too():
    op = {"requestBody": {"content": {"application/json": {"schema": {
        "type": "object",
        "required": ["name"],
        "properties": {"name": {"type": "string"}, "enabled": {"type": "boolean"}},
    }}}}}
    assert json.loads(generate_body_example(op, {})) == {"name": "...", "enabled": True}


def test_nested_only_true_preserves_old_behaviour():
    op = {"requestBody": {"content": {"application/json": {"schema": {
        "type": "object", "properties": {"name": {"type": "string"}},
    }}}}}
    assert generate_body_example(op, {}, nested_only=True) is None


def test_no_request_body_yields_none():
    assert generate_body_example({}, {}) is None


def test_empty_properties_yields_none():
    op = {"requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}}}
    assert generate_body_example(op, {}) is None


# ── Audit F7 / F6 (2026-11-10): query enums through $ref/items; readOnly ─────

class TestQueryEnumResolution:
    """`parse_parameters` read `enum`/`type` off the raw schema, so a query
    parameter whose enum sat behind a `$ref` or under `items` lost its
    choices (audit F7)."""

    def _spec(self):
        return {"components": {"schemas": {"Action": {
            "type": "string",
            "enum": ["modifyElin", "modifyStandard", "modifyService"]}}}}

    def test_query_enum_through_ref(self):
        spec = self._spec()
        params = [{"name": "action", "in": "query", "required": True,
                   "schema": {"$ref": "#/components/schemas/Action"}}]
        _, qps, _, _, _ = parse_parameters(params, spec)
        assert qps[0].enum_values == ["modifyElin", "modifyStandard",
                                      "modifyService"]
        assert qps[0].is_array is False

    def test_query_enum_through_items(self):
        params = [{"name": "channelTypes", "in": "query",
                   "schema": {"type": "array",
                              "items": {"enum": ["email", "chat"]}}}]
        _, qps, _, _, _ = parse_parameters(params, {})
        assert qps[0].enum_values == ["email", "chat"]
        assert qps[0].is_array is True

    def test_query_enum_through_items_ref(self):
        spec = self._spec()
        params = [{"name": "actions", "in": "query",
                   "schema": {"type": "array",
                              "items": {"$ref": "#/components/schemas/Action"}}}]
        _, qps, _, _, _ = parse_parameters(params, spec)
        assert qps[0].enum_values == ["modifyElin", "modifyStandard",
                                      "modifyService"]
        assert qps[0].is_array is True

    def test_plain_array_without_enum_is_still_array(self):
        params = [{"name": "ids", "in": "query",
                   "schema": {"type": "array", "items": {"type": "string"}}}]
        _, qps, _, _, _ = parse_parameters(params, {})
        assert qps[0].enum_values is None
        assert qps[0].is_array is True

    def test_inline_enum_unchanged(self):
        params = [{"name": "status", "in": "query",
                   "schema": {"type": "string", "enum": ["a", "b"]}}]
        _, qps, _, _, _ = parse_parameters(params, {})
        assert qps[0].enum_values == ["a", "b"]
        assert qps[0].is_array is False

    def test_resolve_param_schema_contract(self):
        from tools.openapi_parser import _resolve_param_schema
        spec = self._spec()
        ref = _resolve_param_schema(spec, {"$ref": "#/components/schemas/Action"})
        assert ref["enum"][0] == "modifyElin" and "_array" not in ref
        arr = _resolve_param_schema(
            spec, {"type": "array", "items": {"enum": ["x"]}})
        assert arr["enum"] == ["x"] and arr["_array"] is True
        # the spec itself is never mutated
        assert "_array" not in spec["components"]["schemas"]["Action"]
        assert _resolve_param_schema(spec, {}) == {}


class TestReadOnlyBodyProperties:
    """A top-level `readOnly: true` request property is server-assigned: it is
    neither a flag nor a skeleton key (audit F6). Top level only."""

    def _op(self):
        return _body_op({"type": "object", "properties": {
            "name": {"type": "string"},
            "createdTime": {"type": "integer", "readOnly": True},
            "viaRef": {"$ref": "#/components/schemas/Stamp"},
            "nested": {"type": "object", "properties": {
                "inner": {"type": "string", "readOnly": True}}},
        }})

    def _spec(self):
        return {"components": {"schemas": {"Stamp": {
            "type": "integer", "readOnly": True}}}}

    def test_readonly_body_property_dropped(self):
        op = {"requestBody": {"content": {"application/json": {"schema": {
            "type": "object", "properties": {
                "name": {"type": "string"},
                "createdTime": {"type": "integer", "readOnly": True}}}}}}}
        fields = parse_request_body(op, {})
        assert [f.name for f in fields] == ["name"]
        assert "createdTime" not in json.loads(generate_body_example(op, {}))

    def test_readonly_through_ref_dropped(self):
        spec = self._spec()
        op = self._op()
        assert "viaRef" not in [f.name for f in parse_request_body(op, spec)]
        assert "viaRef" not in json.loads(generate_body_example(op, spec))

    def test_nested_readonly_is_kept(self):
        spec = self._spec()
        skeleton = json.loads(generate_body_example(self._op(), spec))
        assert skeleton["nested"] == {"inner": "..."}
        assert set(skeleton) == {"name", "nested"}

    def test_readonly_false_is_kept(self):
        op = _body_op({"type": "object", "properties": {
            "a": {"type": "string", "readOnly": False}}})
        assert [f.name for f in parse_request_body(op, {})] == ["a"]

    def test_spec_is_not_mutated(self):
        spec = self._spec()
        op = self._op()
        parse_request_body(op, spec)
        assert "createdTime" in op["requestBody"]["content"][
            "application/json"]["schema"]["properties"]


# ── Audit F2 / F3 (2026-11-10): composed properties; oneOf request bodies ────

SPECS = Path(__file__).parent.parent / "specs"


class TestComposedBodyProperties:
    """A body property declared only by composition (`allOf: [{$ref}]`) was
    typed "string" (no `type` key), so an object became a text flag (audit F2).
    """

    def _spec(self):
        return {"components": {"schemas": {
            "CreateDefaultAction": {"type": "object", "properties": {
                "actionType": {"type": "string"}}},
            "FailureBehavior": {"type": "string", "enum": ["A", "B"],
                                "description": "long enum prose"},
        }}}

    def test_allof_object_property_is_object_field(self):
        spec = self._spec()
        op = _body_op({"type": "object", "required": ["defaultAction"],
                       "properties": {"defaultAction": {
                           "description": "Default action configuration",
                           "allOf": [{"$ref": "#/components/schemas/CreateDefaultAction"}]}}})
        fields = parse_request_body(op, spec)
        assert len(fields) == 1
        f = fields[0]
        assert (f.name, f.field_type, f.required) == ("defaultAction", "object", True)
        assert f.description == "Default action configuration"
        # What a direct $ref to the same object already produces.
        direct = _body_op({"type": "object", "required": ["defaultAction"],
                           "properties": {"defaultAction": {
                               "$ref": "#/components/schemas/CreateDefaultAction"}}})
        assert parse_request_body(direct, spec)[0].field_type == "object"

    def test_allof_object_makes_the_example_use_json_body(self):
        """`_flagless_required_body_fields` then switches the Example: to
        `--json-body '<minimal skeleton>'` carrying the key."""
        from tools.command_renderer import _example_json_body
        spec = self._spec()
        op = _body_op({"type": "object", "required": ["defaultAction"],
                       "properties": {"defaultAction": {
                           "allOf": [{"$ref": "#/components/schemas/CreateDefaultAction"}]}}})
        ep = parse_operation("POST", "/things", op, spec)
        body = _example_json_body(ep)
        assert body is not None and "defaultAction" in json.loads(body)

    def test_allof_enum_property_keeps_choices(self):
        spec = json.loads((SPECS / "webex-cloud-calling.json").read_text())
        schema = spec["components"]["schemas"]["CallRecordingVendorPatch"]
        want = spec["components"]["schemas"]["FailureBehavior"]["enum"]
        op = _body_op({"$ref": "#/components/schemas/CallRecordingVendorPatch"})
        fields = {f.name: f for f in parse_request_body(op, spec)}
        assert "failureBehavior" in schema["properties"]
        assert fields["failureBehavior"].field_type == "string"
        assert fields["failureBehavior"].enum_values == want
        assert fields["failureBehavior"].description == "Call recording failure behavior."

    def test_allof_scalar_with_own_description_keeps_it(self):
        spec = self._spec()
        op = _body_op({"type": "object", "properties": {"mode": {
            "description": "own text",
            "allOf": [{"$ref": "#/components/schemas/FailureBehavior"}]}}})
        f = parse_request_body(op, spec)[0]
        assert (f.field_type, f.enum_values, f.description) == (
            "string", ["A", "B"], "own text")

    def test_resolve_property_schema_contract(self):
        from tools.openapi_parser import _resolve_property_schema
        spec = self._spec()
        ref = {"$ref": "#/components/schemas/FailureBehavior"}
        assert _resolve_property_schema(spec, ref)["enum"] == ["A", "B"]
        assert _resolve_property_schema(spec, {"allOf": [ref]})["enum"] == ["A", "B"]
        # a plain inline schema comes back as it is; the spec is not mutated
        inline = {"type": "string"}
        assert _resolve_property_schema(spec, inline) == inline
        assert _resolve_property_schema(spec, {}) == {}
        assert "allOf" not in spec["components"]["schemas"]["FailureBehavior"]


class TestOneOfRequestBodies:
    """A top-level `oneOf` body is a choice between shapes: the flags may demand
    only what EVERY branch requires, and enums are the union (audit F3)."""

    @staticmethod
    def _search_spec():
        def branch(extra, st):
            return {"type": "object",
                    "required": ["orgId", *extra, "searchType"],
                    "properties": {
                        "orgId": {"type": "string"},
                        **{e: {"type": "string"} for e in extra},
                        "searchType": {"type": "string", "enum": [st],
                                       "description": "The type of search."}}}
        return {"components": {"schemas": {
            "Org": branch([], "ORGANIZATION"),
            "Inter": branch(["interactionId"], "INTERACTION"),
            "Agent": branch(["agentCiUserId"], "AGENT"),
            "Req": {"oneOf": [{"$ref": "#/components/schemas/Org"},
                              {"$ref": "#/components/schemas/Inter"},
                              {"$ref": "#/components/schemas/Agent"}]}}}}

    def _search_op(self):
        return _body_op({"$ref": "#/components/schemas/Req"})

    def test_oneof_required_is_intersection(self):
        fields = parse_request_body(self._search_op(), self._search_spec())
        assert {f.name for f in fields if f.required} == {"orgId", "searchType"}
        assert {f.name for f in fields} == {
            "orgId", "interactionId", "agentCiUserId", "searchType"}

    def test_oneof_enum_is_union(self):
        fields = {f.name: f for f in parse_request_body(
            self._search_op(), self._search_spec())}
        assert fields["searchType"].enum_values == [
            "ORGANIZATION", "INTERACTION", "AGENT"]
        assert fields["searchType"].description == "The type of search."

    def test_oneof_free_branch_means_no_enum(self):
        """One branch with no enum accepts any string: the union has no limit."""
        spec = {"components": {"schemas": {
            "A": {"type": "object", "properties": {
                "kind": {"type": "string", "enum": ["x"]}}},
            "B": {"type": "object", "properties": {"kind": {"type": "string"}}}}}}
        op = _body_op({"oneOf": [{"$ref": "#/components/schemas/A"},
                                 {"$ref": "#/components/schemas/B"}]})
        f = parse_request_body(op, spec)[0]
        assert f.enum_values is None

    def test_oneof_type_conflict_drops_flag(self):
        """Fixture only: no tracked spec has it. A property whose type differs
        between branches cannot be one text flag, so it is flagless
        (`--json-body`), and still required only if every branch requires it."""
        spec = {"components": {"schemas": {
            "A": {"type": "object", "required": ["v", "n"], "properties": {
                "v": {"type": "string"}, "n": {"type": "string"}}},
            "B": {"type": "object", "required": ["v", "n"], "properties": {
                "v": {"type": "integer"}, "n": {"type": "string"}}}}}}
        op = _body_op({"oneOf": [{"$ref": "#/components/schemas/A"},
                                 {"$ref": "#/components/schemas/B"}]})
        fields = {f.name: f for f in parse_request_body(op, spec)}
        assert fields["v"].field_type == "object" and fields["v"].required is True
        assert fields["n"].field_type == "string"

    def test_oneof_differing_descriptions_are_joined_and_not_required(self):
        """`cc-tasks create-tasks --channel`: "required for workItem" in one
        branch, "not applicable" in another. Not in the intersection, so not
        required; the help says every branch's rule, not only the first."""
        def branch(channel_desc, required):
            return {"type": "object", "required": ["kind", *required],
                    "properties": {
                        "kind": {"type": "string"},
                        "channel": {"type": "string", "description": channel_desc}}}
        spec = {"components": {"schemas": {
            "A": branch("Required for A.", ["channel"]),
            "B": branch("Not applicable for B.", [])}}}
        op = _body_op({"oneOf": [{"$ref": "#/components/schemas/A"},
                                 {"$ref": "#/components/schemas/B"}]})
        fields = {f.name: f for f in parse_request_body(op, spec)}
        assert fields["channel"].required is False
        assert fields["channel"].description == "Required for A. | Not applicable for B."
        assert fields["kind"].required is True

    def test_anyof_is_read_like_oneof(self):
        spec = self._search_spec()
        spec["components"]["schemas"]["Req"] = {
            "anyOf": spec["components"]["schemas"]["Req"]["oneOf"]}
        fields = parse_request_body(self._search_op(), spec)
        assert {f.name for f in fields if f.required} == {"orgId", "searchType"}

    def test_oneof_examples_come_from_first_branch(self):
        from tools.openapi_parser import _schema_to_example
        spec = {"components": {"schemas": {
            "A": {"type": "object", "required": ["kind", "channelParams"], "properties": {
                "kind": {"type": "string", "enum": ["a"]},
                "channelParams": {"type": "object", "required": ["onlyA"],
                                  "properties": {"onlyA": {"type": "string"}}}}},
            "B": {"type": "object", "required": ["kind", "channelParams"], "properties": {
                "kind": {"type": "string", "enum": ["b"]},
                "channelParams": {"type": "object", "required": ["onlyB"],
                                  "properties": {"onlyB": {"type": "string"}}}}}}}}
        op = {**_body_op({"oneOf": [{"$ref": "#/components/schemas/A"},
                                    {"$ref": "#/components/schemas/B"}]})}
        first = spec["components"]["schemas"]["A"]
        ep = parse_operation("POST", "/things", op, spec)
        assert json.loads(ep.json_body_example) == _schema_to_example(first, spec)
        assert json.loads(ep.json_body_minimal_example) == _schema_to_example(
            first, spec, required_only=True)
        assert json.loads(ep.json_body_example)["channelParams"] == {"onlyA": "..."}

    def test_for_example_returns_first_branch_default_returns_merge(self):
        from tools.openapi_parser import _request_body_schema
        spec, op = self._search_spec(), self._search_op()
        first = _request_body_schema(op, spec, for_example=True)
        assert set(first["properties"]) == {"orgId", "searchType"}
        assert first["properties"]["searchType"]["enum"] == ["ORGANIZATION"]
        merged = _request_body_schema(op, spec)
        assert set(merged["properties"]) == {
            "orgId", "interactionId", "agentCiUserId", "searchType"}

    def test_merge_alternatives_contract(self):
        from tools.openapi_parser import _merge_alternatives
        spec = self._search_spec()
        schema = spec["components"]["schemas"]["Req"]
        merged, first = _merge_alternatives(spec, schema)
        assert merged["required"] == ["orgId", "searchType"]
        assert first["required"] == ["orgId", "searchType"]
        # the spec is never mutated
        assert spec["components"]["schemas"]["Inter"]["properties"][
            "searchType"]["enum"] == ["INTERACTION"]

    def test_allof_body_still_merges_everything(self):
        """`cc-callbacks update` is `allOf`: the merge exists so a composed body
        is not read as empty, and it is untouched by the oneOf handling."""
        spec = {"components": {"schemas": {
            "A": {"type": "object", "required": ["a"], "properties": {"a": {"type": "string"}}},
            "B": {"type": "object", "required": ["b"], "properties": {"b": {"type": "string"}}}}}}
        op = _body_op({"allOf": [{"$ref": "#/components/schemas/A"},
                                 {"$ref": "#/components/schemas/B"}]})
        fields = parse_request_body(op, spec)
        assert {f.name for f in fields if f.required} == {"a", "b"}


# The `_item_fields` output of four list operations, captured BEFORE the F2/F3
# change (venv/bin/python, 2026-11-10). A list response's item schema is read by
# `_resolve_schema_node`, which F3 must not touch: it merges the branches of a
# composed ITEM, where a request body is a choice between shapes.
_ITEM_BASELINE = {
    ("webex-meetings.json", "/slido/compliance/events"): {"items": [
        ["createdAtMs", "number", True], ["sessionId", "string", True],
        ["sessionOrgId", "string", True], ["userId", "string", True],
        ["data", "object", True]]},
    ("webex-meetings.json", "/videoMesh/eventThresholds"): {"eventThresholds": [
        ["eventName", "string", False], ["eventThresholdId", "string", False],
        ["eventScope", "string", False], ["entityId", "string", False],
        ["thresholdConfig", "object", False]]},
    ("webex-meetings.json", "/videoMesh/testStatus"): {"nodes": [
        ["nodeId", "string", False], ["status", "string", False]]},
    ("webex-contact-center.json",
     "/v3/campaign-management/campaign-groups/{campaignGroupName}/campaigns"): {
        "campaigns": [[n, t, False] for n, t in [
            ("campaignId", "string"), ("campaignName", "string"),
            ("campaignGroupName", "string"), ("channel", "string"),
            ("campaignType", "string"), ("campaignDialingMode", "string"),
            ("status", "string"), ("createdTime", "string"),
            ("lastUpdatedTime", "string"), ("startDate", "string"),
            ("endDate", "string"), ("sourceCampaigns", "array"),
            ("fieldMapping", "string"), ("timezone", "string"),
            ("scheduleType", "string"), ("scheduleInfo", "array"),
            ("safeCallingWindow", "array"), ("contactAttemptsStrategy", "object"),
            ("contactFlowPriority", "object"), ("campaignCreatedBy", "string"),
            ("controlHubChannelEntryPointID", "string"), ("outdialANI", "string"),
            ("dncLists", "array"), ("purposeTags", "array"), ("pAndLTag", "string"),
            ("cpaEnabled", "string"), ("numberOfSFTPContactLists", "integer"),
            ("numberOfAPIContactLists", "integer"),
            ("numberOfManualFileContactLists", "integer")]]},
}


@pytest.mark.parametrize("key", sorted(_ITEM_BASELINE))
def test_response_item_schemas_unchanged(key):
    spec_file, path = key
    spec = json.loads((SPECS / spec_file).read_text())
    got = extract_response_item_fields(spec["paths"][path]["get"], spec)
    assert {k: [[f.name, f.field_type, f.required] for f in v]
            for k, v in got.items()} == _ITEM_BASELINE[key]


# ── request body shape (audit F1) ────────────────────────────────────────────

_PATCH_CT = "application/json-patch+json"


def _shape_ep(schema, method="PATCH", content_type=_PATCH_CT, spec=None):
    spec = spec or {"components": {"schemas": {}}}
    op = {"operationId": "probe", "responses": {"200": {"description": "ok"}},
          "parameters": [{"name": "thingId", "in": "path", "required": True,
                         "schema": {"type": "string"}}],
          "requestBody": {"content": {content_type: {"schema": schema}}}}
    return parse_operation(method, "/things/{thingId}", op, spec)


_PATCH_DOC = {"type": "object", "required": ["op", "path"], "properties": {
    "op": {"type": "string", "enum": ["add", "remove", "replace"]},
    "path": {"type": "string"},
    "value": {"type": "string"},
}}


class TestBodyShape:
    def test_no_body_is_none(self):
        ep = parse_operation("PATCH", "/things",
                             {"operationId": "p", "responses": {"200": {"description": "ok"}}},
                             {})
        assert ep.body_shape is None

    def test_single_patch_op_is_op(self):
        assert _shape_ep(_PATCH_DOC).body_shape == "op"
        assert _shape_ep({"type": "object", "properties": {
            "op": {"type": "string"}, "path": {"type": "string"}}}).body_shape == "op"

    def test_array_of_patch_ops_is_op_array(self):
        assert _shape_ep({"type": "array", "items": _PATCH_DOC}).body_shape == "op_array"

    def test_array_of_patch_ops_behind_refs_is_op_array(self):
        spec = {"components": {"schemas": {
            "PatchDocument": _PATCH_DOC,
            "Body": {"type": "array", "items": {"$ref": "#/components/schemas/PatchDocument"}}}}}
        ep = _shape_ep({"$ref": "#/components/schemas/Body"}, spec=spec)
        assert ep.body_shape == "op_array"

    def test_other_object_is_object_whatever_the_content_type(self):
        obj = {"type": "object", "properties": {"title": {"type": "string"}}}
        assert _shape_ep(obj).body_shape == "object"
        assert _shape_ep(obj, method="POST", content_type="application/json").body_shape == "object"

    def test_object_with_op_among_other_properties_is_object(self):
        obj = {"type": "object", "properties": {
            "op": {"type": "string"}, "path": {"type": "string"}, "title": {"type": "string"}}}
        assert _shape_ep(obj).body_shape == "object"

    def test_other_array_is_array(self):
        assert _shape_ep({"type": "array", "items": {"type": "string"}}).body_shape == "array"

    def test_scala_seq_placeholder_is_array(self):
        spec = {"components": {"schemas": {"SeqFlowPreference": {
            "type": "object", "properties": {
                "empty": {"type": "boolean"}, "traversableAgain": {"type": "boolean"}}}}}}
        ep = _shape_ep({"$ref": "#/components/schemas/SeqFlowPreference"},
                       method="PUT", content_type="application/json", spec=spec)
        assert ep.body_shape == "array"

    def test_string_and_untyped(self):
        assert _shape_ep({"type": "string"}, method="POST",
                         content_type="application/json").body_shape == "string"
        assert _shape_ep({}).body_shape == "untyped"

    def test_op_array_flags_come_from_the_items(self):
        op = {"requestBody": {"content": {_PATCH_CT: {"schema": {
            "type": "array", "items": _PATCH_DOC}}}}}
        fields = parse_request_body(op, {})
        assert [(f.name, f.required) for f in fields] == [
            ("op", True), ("path", True), ("value", False)]

    def test_other_array_has_no_flags(self):
        op = {"requestBody": {"content": {_PATCH_CT: {"schema": {
            "type": "array", "items": {"type": "string"}}}}}}
        assert parse_request_body(op, {}) == []

    def test_array_skeletons(self):
        strings = {"requestBody": {"content": {_PATCH_CT: {"schema": {
            "type": "array", "items": {"type": "string"}}}}}}
        assert json.loads(generate_body_example(strings, {})) == ["..."]
        ops = {"requestBody": {"content": {_PATCH_CT: {"schema": {
            "type": "array", "items": _PATCH_DOC}}}}}
        assert json.loads(generate_body_example(ops, {})) == [
            {"op": "add", "path": "...", "value": "..."}]
        assert json.loads(generate_body_example(ops, {}, required_only=True)) == [
            {"op": "add", "path": "..."}]

    def test_shape_of_the_live_specs(self):
        """The 8 PATCH operations of the audit, read from the real specs."""
        want = {
            ("webex-meetings.json", "/meetings/{meetingId}"): "object",
            ("webex-meetings.json", "/group/meetings/{meetingId}"): "object",
            ("webex-device.json", "/devices/{deviceId}"): "op",
            ("webex-device.json", "/deviceConfigurations"): "op",
            ("webex-cloud-calling.json", "/devices/{deviceId}"): "op",
            ("webex-contact-center.json",
             "/admin/v1/api/person/workspace-id/{workspaceId}/person-id/{personId}"): "op_array",
            ("webex-contact-center.json",
             "/admin/v1/api/person/add-identities/workspace-id/{workspaceId}/person-id/{personId}"): "object",
            ("webex-contact-center.json",
             "/admin/v1/api/person/remove-identities/workspace-id/{workspaceId}/person-id/{personId}"): "array",
        }
        for (spec_file, path), shape in want.items():
            spec = json.loads((SPECS / spec_file).read_text())
            ep = parse_operation("PATCH", path, spec["paths"][path]["patch"], spec)
            assert ep.body_shape == shape, (spec_file, path)
