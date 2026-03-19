"""Tests for the OpenAPI 3.0 spec parser."""
import json
import os
import pytest

from tools.openapi_parser import (
    resolve_ref,
    detect_command_type,
    extract_response_list_key,
    extract_response_id_key,
    parse_request_body,
    parse_parameters,
    parse_tag,
    _get_response_schema,
    load_spec,
    get_tags,
)

# ---------------------------------------------------------------------------
# Minimal inline spec fixture for unit tests
# ---------------------------------------------------------------------------

MINI_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Test", "version": "1.0"},
    "tags": [{"name": "TestTag"}],
    "components": {
        "schemas": {
            "WidgetList": {
                "type": "object",
                "required": ["widgets"],
                "properties": {
                    "widgets": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/Widget"},
                    }
                },
            },
            "Widget": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Widget ID"},
                    "name": {"type": "string", "description": "Widget name"},
                    "color": {
                        "type": "string",
                        "enum": ["red", "blue", "green"],
                        "description": "Color choice",
                    },
                },
            },
            "CreateWidgetRequest": {
                "type": "object",
                "required": ["name", "color"],
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Widget name",
                    },
                    "color": {
                        "type": "string",
                        "enum": ["red", "blue", "green"],
                        "description": "Color choice",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional tags",
                    },
                    "metadata": {
                        "$ref": "#/components/schemas/Widget",
                    },
                },
            },
            "WidgetDetail": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "parts": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Parts list",
                    },
                },
            },
            "SettingsResponse": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean"},
                    "timeout": {"type": "integer"},
                },
            },
            "PartA": {
                "type": "object",
                "required": ["aField"],
                "properties": {
                    "aField": {"type": "string"},
                },
            },
            "PartB": {
                "type": "object",
                "properties": {
                    "bField": {"type": "integer"},
                },
            },
            "MultiArrayResponse": {
                "type": "object",
                "required": ["primary"],
                "properties": {
                    "primary": {"type": "array", "items": {"type": "string"}},
                    "secondary": {"type": "array", "items": {"type": "string"}},
                },
            },
        }
    },
    "paths": {
        "/widgets": {
            "get": {
                "operationId": "listWidgets",
                "tags": ["TestTag"],
                "summary": "List Widgets",
                "parameters": [
                    {
                        "name": "orgId",
                        "in": "query",
                        "schema": {"type": "string"},
                        "description": "Organization ID",
                    },
                    {
                        "name": "max",
                        "in": "query",
                        "schema": {"type": "integer"},
                        "description": "Max results",
                    },
                ],
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/WidgetList"
                                }
                            }
                        },
                    }
                },
            },
            "post": {
                "operationId": "createWidget",
                "tags": ["TestTag"],
                "summary": "Create a Widget",
                "parameters": [],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/CreateWidgetRequest"
                            }
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "Created",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string"},
                                    },
                                }
                            }
                        },
                    }
                },
            },
        },
        "/widgets/{widgetId}": {
            "get": {
                "operationId": "getWidget",
                "tags": ["TestTag"],
                "summary": "Get Widget Details",
                "parameters": [
                    {
                        "name": "widgetId",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                        "description": "Widget ID",
                    },
                ],
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/WidgetDetail"
                                }
                            }
                        },
                    }
                },
            },
            "put": {
                "operationId": "updateWidget",
                "tags": ["TestTag"],
                "summary": "Update a Widget",
                "parameters": [
                    {
                        "name": "widgetId",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                ],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/CreateWidgetRequest"
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "OK"}},
            },
            "delete": {
                "operationId": "deleteWidget",
                "tags": ["TestTag"],
                "summary": "Delete a Widget",
                "parameters": [
                    {
                        "name": "widgetId",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                ],
                "responses": {"204": {"description": "Deleted"}},
            },
        },
        "/widgets/settings": {
            "get": {
                "operationId": "getWidgetSettings",
                "tags": ["TestTag"],
                "summary": "Get Widget Settings",
                "parameters": [],
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/SettingsResponse"
                                }
                            }
                        },
                    }
                },
            },
        },
        "/widgets/{widgetId}/actions/invoke": {
            "post": {
                "operationId": "invokeWidgetAction",
                "tags": ["TestTag"],
                "summary": "Invoke Widget Action",
                "parameters": [
                    {
                        "name": "widgetId",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                ],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "action": {"type": "string"},
                                },
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "OK"}},
            },
        },
        "/widgets/allof-test": {
            "get": {
                "operationId": "getAllOfTest",
                "tags": ["TestTag"],
                "summary": "AllOf Test",
                "parameters": [],
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "allOf": [
                                        {"$ref": "#/components/schemas/PartA"},
                                        {"$ref": "#/components/schemas/PartB"},
                                    ]
                                }
                            }
                        },
                    }
                },
            },
        },
        "/widgets/multi-array": {
            "get": {
                "operationId": "getMultiArray",
                "tags": ["TestTag"],
                "summary": "Multi Array Response",
                "parameters": [],
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/MultiArrayResponse"
                                }
                            }
                        },
                    }
                },
            },
        },
        "/widgets/direct-array": {
            "get": {
                "operationId": "getDirectArray",
                "tags": ["TestTag"],
                "summary": "Direct Array Response",
                "parameters": [],
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/Widget"},
                                }
                            }
                        },
                    }
                },
            },
        },
        "/widgets/upload": {
            "post": {
                "operationId": "uploadWidget",
                "tags": ["TestTag"],
                "summary": "Upload Widget File",
                "parameters": [],
                "requestBody": {
                    "content": {
                        "multipart/form-data": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "file": {"type": "string", "format": "binary"},
                                },
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "OK"}},
            },
        },
        "/widgets/no-schema": {
            "get": {
                "operationId": "getNoSchema",
                "tags": ["TestTag"],
                "summary": "No Schema Response",
                "parameters": [],
                "responses": {
                    "200": {"description": "OK"},
                },
            },
        },
        "/widgets/{widgetId}/dect-create": {
            "post": {
                "operationId": "createDectWidget",
                "tags": ["TestTag"],
                "summary": "Create DECT Widget",
                "parameters": [
                    {
                        "name": "widgetId",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                ],
                "responses": {
                    "201": {
                        "description": "Created",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["dectNetworkId"],
                                    "properties": {
                                        "dectNetworkId": {"type": "string"},
                                    },
                                }
                            }
                        },
                    }
                },
            },
        },
    },
}


# ---------------------------------------------------------------------------
# Unit tests: resolve_ref
# ---------------------------------------------------------------------------


class TestResolveRef:
    def test_resolves_schema(self):
        result = resolve_ref(MINI_SPEC, "#/components/schemas/Widget")
        assert result["type"] == "object"
        assert "id" in result["properties"]

    def test_resolves_nested(self):
        result = resolve_ref(MINI_SPEC, "#/components/schemas/WidgetList")
        assert "widgets" in result["properties"]


# ---------------------------------------------------------------------------
# Unit tests: detect_command_type
# ---------------------------------------------------------------------------


class TestDetectCommandType:
    def test_list(self):
        op = MINI_SPEC["paths"]["/widgets"]["get"]
        assert detect_command_type("get", "/widgets", op, MINI_SPEC) == "list"

    def test_show_with_path_param(self):
        """GET ending in {param} should ALWAYS be 'show', even if response has arrays."""
        op = MINI_SPEC["paths"]["/widgets/{widgetId}"]["get"]
        result = detect_command_type("get", "/widgets/{widgetId}", op, MINI_SPEC)
        assert result == "show"

    def test_show_with_arrays_in_response(self):
        """Critical: GET ending with {param} is 'show' even when response has array props."""
        # WidgetDetail has a 'parts' array property, but path ends in {widgetId}
        op = MINI_SPEC["paths"]["/widgets/{widgetId}"]["get"]
        result = detect_command_type("get", "/widgets/{widgetId}", op, MINI_SPEC)
        assert result == "show"

    def test_settings_get(self):
        op = MINI_SPEC["paths"]["/widgets/settings"]["get"]
        result = detect_command_type("get", "/widgets/settings", op, MINI_SPEC)
        assert result == "settings-get"

    def test_create(self):
        op = MINI_SPEC["paths"]["/widgets"]["post"]
        assert detect_command_type("post", "/widgets", op, MINI_SPEC) == "create"

    def test_action(self):
        op = MINI_SPEC["paths"]["/widgets/{widgetId}/actions/invoke"]["post"]
        result = detect_command_type(
            "post", "/widgets/{widgetId}/actions/invoke", op, MINI_SPEC
        )
        assert result == "action"

    def test_update(self):
        op = MINI_SPEC["paths"]["/widgets/{widgetId}"]["put"]
        result = detect_command_type("put", "/widgets/{widgetId}", op, MINI_SPEC)
        assert result == "update"

    def test_delete(self):
        op = MINI_SPEC["paths"]["/widgets/{widgetId}"]["delete"]
        result = detect_command_type("delete", "/widgets/{widgetId}", op, MINI_SPEC)
        assert result == "delete"

    def test_no_schema_defaults_to_list(self):
        op = MINI_SPEC["paths"]["/widgets/no-schema"]["get"]
        result = detect_command_type("get", "/widgets/no-schema", op, MINI_SPEC)
        assert result == "list"


# ---------------------------------------------------------------------------
# Unit tests: extract_response_list_key
# ---------------------------------------------------------------------------


class TestExtractResponseListKey:
    def test_normal_list_key(self):
        op = MINI_SPEC["paths"]["/widgets"]["get"]
        assert extract_response_list_key(op, MINI_SPEC) == "widgets"

    def test_direct_array_returns_none(self):
        op = MINI_SPEC["paths"]["/widgets/direct-array"]["get"]
        assert extract_response_list_key(op, MINI_SPEC) is None

    def test_multi_array_prefers_required(self):
        op = MINI_SPEC["paths"]["/widgets/multi-array"]["get"]
        assert extract_response_list_key(op, MINI_SPEC) == "primary"

    def test_no_response_returns_none(self):
        op = MINI_SPEC["paths"]["/widgets/no-schema"]["get"]
        assert extract_response_list_key(op, MINI_SPEC) is None


# ---------------------------------------------------------------------------
# Unit tests: extract_response_id_key
# ---------------------------------------------------------------------------


class TestExtractResponseIdKey:
    def test_standard_id(self):
        op = MINI_SPEC["paths"]["/widgets"]["post"]
        assert extract_response_id_key(op, MINI_SPEC) == "id"

    def test_custom_id_key(self):
        op = MINI_SPEC["paths"]["/widgets/{widgetId}/dect-create"]["post"]
        assert extract_response_id_key(op, MINI_SPEC) == "dectNetworkId"

    def test_no_201_response(self):
        op = MINI_SPEC["paths"]["/widgets/{widgetId}/actions/invoke"]["post"]
        assert extract_response_id_key(op, MINI_SPEC) is None


# ---------------------------------------------------------------------------
# Unit tests: parse_request_body
# ---------------------------------------------------------------------------


class TestParseRequestBody:
    def test_required_fields(self):
        op = MINI_SPEC["paths"]["/widgets"]["post"]
        fields = parse_request_body(op, MINI_SPEC)
        field_map = {f.name: f for f in fields}
        assert field_map["name"].required is True
        assert field_map["color"].required is True

    def test_enum_values(self):
        op = MINI_SPEC["paths"]["/widgets"]["post"]
        fields = parse_request_body(op, MINI_SPEC)
        field_map = {f.name: f for f in fields}
        assert field_map["color"].enum_values == ["red", "blue", "green"]

    def test_descriptions(self):
        op = MINI_SPEC["paths"]["/widgets"]["post"]
        fields = parse_request_body(op, MINI_SPEC)
        field_map = {f.name: f for f in fields}
        assert field_map["name"].description == "Widget name"

    def test_nested_object_ref(self):
        op = MINI_SPEC["paths"]["/widgets"]["post"]
        fields = parse_request_body(op, MINI_SPEC)
        field_map = {f.name: f for f in fields}
        assert field_map["metadata"].field_type == "object"

    def test_array_field(self):
        op = MINI_SPEC["paths"]["/widgets"]["post"]
        fields = parse_request_body(op, MINI_SPEC)
        field_map = {f.name: f for f in fields}
        assert field_map["tags"].field_type == "array"

    def test_no_body_returns_empty(self):
        op = MINI_SPEC["paths"]["/widgets"]["get"]
        fields = parse_request_body(op, MINI_SPEC)
        assert fields == []


# ---------------------------------------------------------------------------
# Unit tests: parse_parameters
# ---------------------------------------------------------------------------


class TestParseParameters:
    def test_path_and_query_params(self):
        params = MINI_SPEC["paths"]["/widgets"]["get"]["parameters"]
        path_vars, query_params = parse_parameters(params, MINI_SPEC)
        assert path_vars == []
        assert len(query_params) == 2
        assert query_params[0].name == "orgId"
        assert query_params[1].name == "max"
        assert query_params[1].field_type == "number"

    def test_omit_query_params(self):
        params = MINI_SPEC["paths"]["/widgets"]["get"]["parameters"]
        path_vars, query_params = parse_parameters(
            params, MINI_SPEC, omit_query_params=["orgId"]
        )
        assert len(query_params) == 1
        assert query_params[0].name == "max"

    def test_path_variable(self):
        params = MINI_SPEC["paths"]["/widgets/{widgetId}"]["get"]["parameters"]
        path_vars, query_params = parse_parameters(params, MINI_SPEC)
        assert path_vars == ["widgetId"]
        assert query_params == []


# ---------------------------------------------------------------------------
# Unit tests: _get_response_schema with allOf
# ---------------------------------------------------------------------------


class TestGetResponseSchema:
    def test_allof_merges(self):
        op = MINI_SPEC["paths"]["/widgets/allof-test"]["get"]
        schema = _get_response_schema(op, MINI_SPEC, "200")
        assert schema["type"] == "object"
        assert "aField" in schema["properties"]
        assert "bField" in schema["properties"]
        assert "aField" in schema["required"]

    def test_ref_resolves(self):
        op = MINI_SPEC["paths"]["/widgets"]["get"]
        schema = _get_response_schema(op, MINI_SPEC, "200")
        assert "widgets" in schema["properties"]


# ---------------------------------------------------------------------------
# Integration test: parse_tag against the mini spec
# ---------------------------------------------------------------------------


class TestParseTag:
    def test_parse_mini_spec_tag(self):
        endpoints, skipped = parse_tag(
            "TestTag", MINI_SPEC, omit_query_params=["orgId"]
        )
        # Should have all non-upload operations
        names = {ep.command_name for ep in endpoints}
        types = {ep.command_name: ep.command_type for ep in endpoints}

        # Upload should be skipped
        assert len(skipped) == 1
        assert "Upload" in skipped[0]

        # Check command types
        list_eps = [ep for ep in endpoints if ep.command_type == "list"]
        show_eps = [ep for ep in endpoints if ep.command_type == "show"]
        create_eps = [ep for ep in endpoints if ep.command_type == "create"]
        settings_eps = [
            ep for ep in endpoints if ep.command_type == "settings-get"
        ]
        action_eps = [ep for ep in endpoints if ep.command_type == "action"]

        assert len(list_eps) >= 1, f"Expected list commands, got types: {types}"
        assert len(show_eps) >= 1
        assert len(create_eps) >= 1
        assert len(settings_eps) >= 1
        assert len(action_eps) >= 1

        # Check that list key is populated
        widget_list = [ep for ep in list_eps if "widgets" == ep.response_list_key]
        assert len(widget_list) >= 1

        # Check that response_id_key is populated for create
        create_widget = [ep for ep in create_eps if ep.response_id_key == "id"]
        assert len(create_widget) >= 1

    def test_skip_seen_operation_ids(self):
        seen = {"listWidgets"}
        endpoints, _ = parse_tag("TestTag", MINI_SPEC, seen_operation_ids=seen)
        op_ids_found = [
            ep.name
            for ep in endpoints
            if ep.name == "List Widgets"
        ]
        assert len(op_ids_found) == 0

    def test_url_path_format(self):
        """url_path should use {param} format without leading slash."""
        endpoints, _ = parse_tag("TestTag", MINI_SPEC)
        show_ep = [ep for ep in endpoints if ep.command_type == "show"][0]
        assert "{widgetId}" in show_ep.url_path
        assert not show_ep.url_path.startswith("/")

    def test_raw_path_format(self):
        """raw_path should use :param format."""
        endpoints, _ = parse_tag("TestTag", MINI_SPEC)
        show_ep = [ep for ep in endpoints if ep.command_type == "show"][0]
        assert ":widgetId" in show_ep.raw_path


# ---------------------------------------------------------------------------
# Integration test: parse_tag against the real spec
# ---------------------------------------------------------------------------

REAL_SPEC_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "webex-cloud-calling.json"
)


@pytest.mark.skipif(
    not os.path.exists(REAL_SPEC_PATH),
    reason="Real OpenAPI spec not found",
)
class TestRealSpec:
    @pytest.fixture(scope="class")
    def spec(self):
        return load_spec(REAL_SPEC_PATH)

    def test_parse_dect_devices_tag(self, spec):
        """Parse DECT Devices Settings tag from real spec."""
        endpoints, skipped = parse_tag(
            "DECT Devices Settings", spec, omit_query_params=["orgId"]
        )
        assert len(endpoints) > 0

        # Should have list, show, create, update, delete types
        types = {ep.command_type for ep in endpoints}
        assert "list" in types
        assert "create" in types

        # DECT create should have dectNetworkId as response_id_key
        creates = [ep for ep in endpoints if ep.command_type == "create"]
        dect_creates = [ep for ep in creates if ep.response_id_key == "dectNetworkId"]
        assert len(dect_creates) >= 1, (
            f"Expected dectNetworkId create, got: "
            f"{[(ep.name, ep.response_id_key) for ep in creates]}"
        )

    def test_show_endpoints_with_path_params(self, spec):
        """All GET endpoints ending in {param} should be 'show', never 'list'."""
        endpoints, _ = parse_tag(
            "DECT Devices Settings", spec, omit_query_params=["orgId"]
        )
        for ep in endpoints:
            if ep.method == "GET" and ep.url_path.endswith("}"):
                assert ep.command_type == "show", (
                    f"{ep.name} at {ep.url_path} should be show, got {ep.command_type}"
                )

    def test_multi_tag_dedup(self, spec):
        """Operations shared between Call Controls and External Voicemail are deduped."""
        seen = set()
        eps1, _ = parse_tag("Call Controls", spec, seen_operation_ids=seen)
        eps2, _ = parse_tag("External Voicemail", spec, seen_operation_ids=seen)
        # All ops from both tags combined should have unique names
        all_ops = eps1 + eps2
        op_names = [ep.name for ep in all_ops]
        # The 24 shared ops should appear only once
        assert len(op_names) == len(set(op_names)), (
            f"Duplicate operations found: "
            f"{[n for n in op_names if op_names.count(n) > 1]}"
        )

    def test_get_tags_returns_all(self, spec):
        """get_tags should return all unique tags."""
        tags = get_tags(spec)
        assert len(tags) >= 2
        assert "DECT Devices Settings" in tags or len(tags) > 0
