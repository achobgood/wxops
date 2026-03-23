"""Parse OpenAPI 3.0 spec JSON into normalized Endpoint dataclasses."""
import json
import re
from pathlib import Path
from typing import Any

from tools.postman_parser import (
    Endpoint,
    EndpointField,
    camel_to_kebab,
    camel_to_snake,
    _derive_command_name,
    _dedup_command_names,
)


def load_spec(path: str | Path) -> dict:
    """Load an OpenAPI 3.0 JSON spec file."""
    with open(path) as f:
        return json.load(f)


def resolve_ref(spec: dict, ref: str) -> dict:
    """Resolve a $ref like '#/components/schemas/Foo' within the spec."""
    parts = ref.lstrip("#/").split("/")
    result = spec
    for part in parts:
        result = result[part]
    return result


def _get_response_schema(
    op: dict, spec: dict, status_code: str = "200"
) -> dict | None:
    """Get the resolved response schema for a given status code.

    Handles $ref resolution, allOf merging, and both application/json
    and application/json;charset=UTF-8 content types.
    """
    resp = op.get("responses", {}).get(status_code, {})
    content = resp.get("content", {})
    json_content = (
        content.get("application/json")
        or content.get("application/json;charset=UTF-8", {})
    )
    schema = json_content.get("schema", {})
    if not schema:
        return None
    if "$ref" in schema:
        schema = resolve_ref(spec, schema["$ref"])
    if "allOf" in schema:
        merged_props: dict = {}
        merged_required: list = []
        for item in schema["allOf"]:
            if "$ref" in item:
                resolved = resolve_ref(spec, item["$ref"])
                merged_props.update(resolved.get("properties", {}))
                merged_required.extend(resolved.get("required", []))
            else:
                merged_props.update(item.get("properties", {}))
                merged_required.extend(item.get("required", []))
        schema = {
            "type": "object",
            "properties": merged_props,
            "required": merged_required,
        }
    return schema


def get_tags(spec: dict) -> list[str]:
    """Return sorted list of unique tags across all operations."""
    tags: set[str] = set()
    for path_obj in spec.get("paths", {}).values():
        for method in ("get", "post", "put", "patch", "delete"):
            op = path_obj.get(method)
            if op:
                for tag in op.get("tags", []):
                    tags.add(tag)
    return sorted(tags)


def parse_parameters(
    params: list[dict], spec: dict, omit_query_params: list[str] | None = None,
    auto_inject_params: set[str] | None = None,
) -> tuple[list[str], list[EndpointField], list[str]]:
    """Parse OpenAPI parameters into (path_vars, query_params, auto_inject_names).

    Path params become path_vars list of variable names.
    Query params become EndpointField list with type, description, required, enum.
    Params in omit_query_params are skipped entirely.
    Params in auto_inject_params are separated into auto_inject_names and not
    added to query_params (they will be injected from config at runtime).
    """
    omit = set(omit_query_params or [])
    auto_inject = auto_inject_params or set()
    auto_inject_names: list[str] = []
    path_vars: list[str] = []
    query_params: list[EndpointField] = []

    for param in params:
        # Resolve param-level $ref
        if "$ref" in param:
            param = resolve_ref(spec, param["$ref"])

        name = param.get("name", "")
        location = param.get("in", "")
        schema = param.get("schema", {})

        if location == "path":
            path_vars.append(name)
        elif location == "query":
            if name in omit:
                continue
            if name in auto_inject:
                auto_inject_names.append(name)
                continue
            field_type = _openapi_type_to_field_type(schema)
            enum_values = schema.get("enum")
            desc = param.get("description", "")[:120]
            required = param.get("required", False)
            query_params.append(
                EndpointField(
                    name=name,
                    python_name=camel_to_kebab(name),
                    field_type=field_type,
                    description=desc,
                    required=required,
                    enum_values=enum_values,
                )
            )

    return path_vars, query_params, auto_inject_names


def _openapi_type_to_field_type(schema: dict) -> str:
    """Convert OpenAPI schema type to our field_type string."""
    t = schema.get("type", "string")
    if t == "integer":
        return "number"
    if t == "number":
        return "number"
    if t == "boolean":
        return "bool"
    if t == "array":
        return "array"
    if t == "object":
        return "object"
    return "string"


def _schema_to_example(schema: dict, spec: dict, depth: int = 0) -> Any:
    """Generate a compact example value from an OpenAPI schema, max 2 levels deep."""
    if depth > 2:
        return "..."
    if "$ref" in schema:
        schema = resolve_ref(spec, schema["$ref"])
    t = schema.get("type", "object")
    if t == "string":
        enum = schema.get("enum")
        return enum[0] if enum else "..."
    if t == "integer" or t == "number":
        return 0
    if t == "boolean":
        return True
    if t == "array":
        items = schema.get("items", {})
        return [_schema_to_example(items, spec, depth + 1)]
    if t == "object" or "properties" in schema:
        props = schema.get("properties", {})
        result = {}
        for name, prop in list(props.items())[:6]:  # cap at 6 keys
            if "$ref" in prop:
                prop = resolve_ref(spec, prop["$ref"])
            result[name] = _schema_to_example(prop, spec, depth + 1)
        return result
    return "..."


def generate_body_example(op: dict, spec: dict) -> str | None:
    """Generate a compact JSON example for the request body, or None if no nested fields."""
    rb = op.get("requestBody", {})
    content = rb.get("content", {})
    json_content = (
        content.get("application/json")
        or content.get("application/json;charset=UTF-8")
        or content.get("application/json-patch+json", {})
    )
    if not json_content:
        return None

    schema = json_content.get("schema", {})
    if "$ref" in schema:
        schema = resolve_ref(spec, schema["$ref"])

    # Only generate example if there are nested object/array fields
    props = schema.get("properties", {})
    has_nested = any(
        p.get("type") in ("object", "array") or "$ref" in p
        for p in props.values()
    )
    if not has_nested:
        return None

    example = _schema_to_example(schema, spec)
    return json.dumps(example, separators=(",", ":"))


def parse_request_body(
    op: dict, spec: dict
) -> list[EndpointField]:
    """Parse request body into flat EndpointField list.

    Resolves $ref, marks required fields, extracts enums and descriptions.
    Nested $ref objects get field_type='object'.
    """
    rb = op.get("requestBody", {})
    content = rb.get("content", {})
    json_content = (
        content.get("application/json")
        or content.get("application/json;charset=UTF-8")
        or content.get("application/json-patch+json", {})
    )
    if not json_content:
        return []

    schema = json_content.get("schema", {})
    if "$ref" in schema:
        schema = resolve_ref(spec, schema["$ref"])

    properties = schema.get("properties", {})
    required_fields = set(schema.get("required", []))
    fields: list[EndpointField] = []

    for name, prop in properties.items():
        # Resolve property-level $ref
        if "$ref" in prop:
            # Nested object reference
            fields.append(
                EndpointField(
                    name=name,
                    python_name=camel_to_kebab(name),
                    field_type="object",
                    description=prop.get("description", "")[:120],
                    required=name in required_fields,
                )
            )
            continue

        field_type = _openapi_type_to_field_type(prop)
        enum_values = prop.get("enum")
        desc = prop.get("description", "")[:120]

        fields.append(
            EndpointField(
                name=name,
                python_name=camel_to_kebab(name),
                field_type=field_type,
                description=desc,
                required=name in required_fields,
                enum_values=enum_values,
            )
        )

    return fields


def detect_command_type(
    method: str, path: str, op: dict, spec: dict
) -> str:
    """Detect command type from HTTP method, path, and response schema.

    CRITICAL: For GET, check path ending FIRST, schema SECOND.
    This ensures endpoints like 'GET /foo/{id}' that happen to have
    array properties in their response are correctly classified as 'show'.
    """
    method = method.upper()
    path_segments = path.rstrip("/").split("/")
    last_seg = path_segments[-1] if path_segments else ""

    # POST with actions/invoke → action
    if method == "POST" and ("actions" in path_segments or "invoke" in path_segments):
        return "action"
    if method == "POST":
        return "create"
    if method in ("PUT", "PATCH"):
        return "update"
    if method == "DELETE":
        return "delete"

    # GET — check path ending FIRST
    if method == "GET":
        # Path ends with {param} or /me → always "show"
        if last_seg.startswith("{") and last_seg.endswith("}"):
            return "show"
        if last_seg == "me":
            return "show"

        # Check response schema for array properties
        schema = _get_response_schema(op, spec, "200")
        if schema:
            # Direct array response → list
            if schema.get("type") == "array":
                return "list"
            props = schema.get("properties", {})
            has_array = any(
                p.get("type") == "array" for p in props.values()
            )
            if has_array:
                return "list"
            # Flat object response → settings-get
            return "settings-get"

        # No schema → default to list
        return "list"

    return "action"


def extract_response_list_key(op: dict, spec: dict) -> str | None:
    """For list commands, find the array property in the 200 response schema.

    Returns None for direct array responses (renderer handles raw list).
    For multiple array properties, prefers required ones, then first.
    """
    schema = _get_response_schema(op, spec, "200")
    if not schema:
        return None

    # Direct array response
    if schema.get("type") == "array":
        return None

    props = schema.get("properties", {})
    required = set(schema.get("required", []))

    array_props = [
        name for name, prop in props.items() if prop.get("type") == "array"
    ]

    if not array_props:
        return None
    if len(array_props) == 1:
        return array_props[0]

    # Multiple arrays: prefer required ones
    required_arrays = [p for p in array_props if p in required]
    if required_arrays:
        return required_arrays[0]
    return array_props[0]


def extract_response_id_key(op: dict, spec: dict) -> str | None:
    """For create commands, find the ID field in the 201 response schema.

    Usually 'id', sometimes 'dectNetworkId' or similar.
    """
    schema = _get_response_schema(op, spec, "201")
    if not schema:
        return None

    props = schema.get("properties", {})
    if not props:
        return None

    # Look for exact 'id' field first
    if "id" in props:
        return "id"

    # Look for fields ending in 'Id'
    for name in props:
        if name.endswith("Id") or name == "id":
            return name

    # Return first property if it's the only one
    if len(props) == 1:
        return list(props.keys())[0]

    return None


def _path_to_raw_path(path: str) -> list[str]:
    """Convert OpenAPI path '/foo/{bar}/baz' to raw_path ['foo', ':bar', 'baz'].

    raw_path uses ':param' format for compatibility with _derive_command_name.
    """
    segments = path.strip("/").split("/")
    result = []
    for seg in segments:
        if seg.startswith("{") and seg.endswith("}"):
            result.append(":" + seg[1:-1])
        else:
            result.append(seg)
    return result


def _path_to_url_path(path: str) -> str:
    """Convert OpenAPI path '/foo/{bar}/baz' to url_path 'foo/{bar}/baz'.

    Strips leading slash and redundant 'v1/' prefix (renderer's BASE_URL
    already includes /v1). Keeps {param} format as-is.
    """
    result = path.lstrip("/")
    if result.startswith("v1/"):
        result = result[3:]
    return result


def parse_operation(
    method: str,
    path: str,
    op: dict,
    spec: dict,
    omit_query_params: list[str] | None = None,
    auto_inject_params: set[str] | None = None,
) -> Endpoint:
    """Convert one OpenAPI operation to an Endpoint dataclass."""
    params = op.get("parameters", [])
    path_vars, query_params, auto_inject_names = parse_parameters(
        params, spec, omit_query_params, auto_inject_params
    )
    body_fields = parse_request_body(op, spec)

    command_type = detect_command_type(method, path, op, spec)

    response_list_key = None
    if command_type == "list":
        response_list_key = extract_response_list_key(op, spec)

    response_id_key = None
    if command_type == "create":
        response_id_key = extract_response_id_key(op, spec)

    raw_path = _path_to_raw_path(path)
    url_path = _path_to_url_path(path)
    name = op.get("summary") or op.get("operationId", "")
    deprecated = op.get("deprecated", False)

    json_body_example = None
    if command_type in ("create", "update", "action"):
        json_body_example = generate_body_example(op, spec)

    return Endpoint(
        name=name,
        method=method.upper(),
        url_path=url_path,
        path_vars=path_vars,
        query_params=query_params,
        body_fields=body_fields,
        command_type=command_type,
        command_name="",  # Set later by _derive_command_name
        raw_path=raw_path,
        response_list_key=response_list_key,
        response_id_key=response_id_key,
        deprecated=deprecated,
        json_body_example=json_body_example,
        auto_inject_params=auto_inject_names,
    )


def parse_tag(
    tag: str,
    spec: dict,
    omit_query_params: list[str] | None = None,
    auto_inject_params: set[str] | None = None,
    seen_operation_ids: set[str] | None = None,
) -> tuple[list[Endpoint], list[str]]:
    """Parse all operations for a given tag into Endpoint list.

    Skips operations already in seen_operation_ids (handles multi-tagged ops).
    Skips formdata/multipart upload operations.
    Returns (endpoints, skipped_uploads).
    """
    if seen_operation_ids is None:
        seen_operation_ids = set()

    endpoints: list[Endpoint] = []
    skipped_uploads: list[str] = []
    seen_types: dict[str, int] = {}

    for path, path_obj in spec.get("paths", {}).items():
        for method in ("get", "post", "put", "patch", "delete"):
            op = path_obj.get(method)
            if not op:
                continue

            # Check if this operation belongs to the requested tag
            op_tags = op.get("tags", [])
            if tag not in op_tags:
                continue

            # Skip already-processed operations (multi-tag dedup)
            op_id = op.get("operationId", "")
            if op_id and op_id in seen_operation_ids:
                continue
            if op_id:
                seen_operation_ids.add(op_id)

            # Skip multipart/formdata uploads
            rb = op.get("requestBody", {})
            rb_content = rb.get("content", {})
            if "multipart/form-data" in rb_content:
                skipped_uploads.append(
                    op.get("summary") or op_id or f"{method.upper()} {path}"
                )
                continue

            ep = parse_operation(method, path, op, spec, omit_query_params, auto_inject_params)
            ep.command_name = _derive_command_name(
                ep.command_type, ep.raw_path, ep.name, seen_types
            )
            endpoints.append(ep)

    _dedup_command_names(endpoints)
    return endpoints, skipped_uploads
