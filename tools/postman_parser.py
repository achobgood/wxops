"""Parse Postman collection JSON into normalized Endpoint dataclasses."""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class EndpointField:
    name: str
    python_name: str
    field_type: str
    description: str
    required: bool = False
    default: Any = None
    enum_example: str | None = None


@dataclass
class Endpoint:
    name: str
    method: str
    url_path: str
    path_vars: list[str]
    query_params: list[EndpointField]
    body_fields: list[EndpointField]
    command_type: str
    command_name: str
    raw_path: list[str] = field(default_factory=list)
    response_list_key: str | None = None


def camel_to_kebab(name: str) -> str:
    s = re.sub(r"([A-Z])", r"-\1", name).lower().lstrip("-")
    return s


def camel_to_snake(name: str) -> str:
    s = re.sub(r"([A-Z])", r"_\1", name).lower().lstrip("_")
    return s


def _infer_type(value: Any) -> tuple[str, str | None]:
    if isinstance(value, str):
        if value == "<string>":
            return "string", None
        if value == "<boolean>":
            return "bool", None
        if value == "<number>":
            return "number", None
        if re.match(r"^[A-Z][A-Z0-9_]{2,}$", value):
            return "string", value
        return "string", None
    if isinstance(value, bool):
        return "bool", None
    if isinstance(value, (int, float)):
        return "number", None
    if isinstance(value, dict):
        return "object", None
    if isinstance(value, list):
        return "array", None
    return "string", None


def parse_body_fields(raw_body: str | None) -> list[EndpointField]:
    if not raw_body:
        return []
    try:
        parsed = json.loads(raw_body)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(parsed, dict):
        return []
    fields = []
    for key, value in parsed.items():
        field_type, enum_example = _infer_type(value)
        fields.append(
            EndpointField(
                name=key,
                python_name=camel_to_kebab(key),
                field_type=field_type,
                description="",
                enum_example=enum_example,
            )
        )
    return fields


SETTINGS_KEYWORDS = {
    "settings", "service", "forwarding", "musiconhold", "nightservice",
    "holidayservice", "forcedforward", "strandedcalls", "musicOnHold",
}

SETTINGS_NAME_KEYWORDS = [
    "settings", "service", "forwarding", "music on hold", "night service",
    "holiday service", "forced forward", "stranded calls",
]


def derive_command_type(method: str, path: list[str], name: str) -> str:
    last_seg = path[-1] if path else ""
    is_path_var = last_seg.startswith(":")
    name_lower = name.lower()

    if method == "POST" and ("actions" in path or "invoke" in path):
        return "action"
    if method == "POST" and ("selective" in name_lower or "rule" in name_lower):
        return "create"

    is_settings = last_seg.lstrip(":").lower() in {kw.lower() for kw in SETTINGS_KEYWORDS}
    if not is_settings:
        is_settings = any(kw in name_lower for kw in SETTINGS_NAME_KEYWORDS)

    if is_settings:
        if method == "GET":
            return "settings-get"
        if method == "PUT":
            return "settings-update"

    if method == "GET":
        return "show" if is_path_var else "list"
    if method == "POST":
        return "create"
    if method in ("PUT", "PATCH"):
        return "update"
    if method == "DELETE":
        return "delete"
    return "action"


def derive_response_list_key(path: list[str]) -> str | None:
    for seg in reversed(path):
        if not seg.startswith(":"):
            return seg
    return None


def _derive_command_name(
    command_type: str, raw_path: list[str], postman_name: str, seen_types: dict
) -> str:
    base = command_type.replace("settings-get", "show").replace("settings-update", "update")
    if base == "action":
        words = re.sub(r"[^a-zA-Z0-9 ]", " ", postman_name).lower().split()
        slug = "-".join(words[:3])
        return slug

    count = seen_types.get(base, 0)
    seen_types[base] = count + 1
    if count == 0:
        return base

    for seg in reversed(raw_path):
        if not seg.startswith(":") and seg.lower() not in (
            "config", "telephony", "locations", "v1", "features",
        ):
            suffix = camel_to_kebab(seg).strip("-")
            if suffix:
                return f"{base}-{suffix}"
    return f"{base}-{count}"


def _dedup_command_names(endpoints: list) -> None:
    """Post-process to fix duplicate command names by appending context from path."""
    from collections import Counter
    # Pass 1: try to disambiguate with a path segment
    name_counts = Counter(ep.command_name for ep in endpoints)
    dupes = {name for name, cnt in name_counts.items() if cnt > 1}
    if not dupes:
        return
    for ep in endpoints:
        if ep.command_name not in dupes:
            continue
        for seg in reversed(ep.raw_path):
            if seg.startswith(":"):
                continue
            candidate = camel_to_kebab(seg).strip("-")
            if candidate and candidate not in ep.command_name:
                ep.command_name = f"{ep.command_name}-{candidate}"
                break
    # Pass 2: if still duplicated, append numeric suffix
    name_counts = Counter(ep.command_name for ep in endpoints)
    dupes = {name for name, cnt in name_counts.items() if cnt > 1}
    if not dupes:
        return
    seen: dict[str, int] = {}
    for ep in endpoints:
        if ep.command_name in dupes:
            n = seen.get(ep.command_name, 0)
            seen[ep.command_name] = n + 1
            if n > 0:
                ep.command_name = f"{ep.command_name}-{n}"


def _build_url_path(path: list[str]) -> str:
    parts = []
    for seg in path:
        if seg.startswith(":"):
            var = seg[1:]
            parts.append("{" + var + "}")
        else:
            parts.append(seg)
    return "/".join(parts)


def parse_request(
    request_data: dict, omit_query_params: list[str] | None = None
) -> Endpoint:
    omit = set(omit_query_params or [])
    r = request_data["request"]
    method = r["method"]
    url = r["url"]
    path = url.get("path", [])
    name = request_data.get("name", "")

    path_vars = [v["key"] for v in url.get("variable", [])]

    query_params = []
    seen_qp: set[str] = set()
    for q in url.get("query", []):
        key = q["key"]
        if key in omit or key in seen_qp:
            continue
        seen_qp.add(key)
        desc = q.get("description", "")
        if isinstance(desc, dict):
            desc = desc.get("content", "")
        ft = "number" if q.get("value") == "<number>" else "string"
        query_params.append(
            EndpointField(
                name=key,
                python_name=camel_to_kebab(key),
                field_type=ft,
                description=str(desc)[:120],
            )
        )

    body_fields: list[EndpointField] = []
    body = r.get("body") or {}
    if body.get("mode") == "raw":
        body_fields = parse_body_fields(body.get("raw", ""))

    url_path = _build_url_path(path)
    command_type = derive_command_type(method, path, name)
    response_list_key = derive_response_list_key(path) if command_type == "list" else None

    return Endpoint(
        name=name,
        method=method,
        url_path=url_path,
        path_vars=path_vars,
        query_params=query_params,
        body_fields=body_fields,
        command_type=command_type,
        command_name="",
        raw_path=path,
        response_list_key=response_list_key,
    )


def load_overrides(path: str | Path) -> dict:
    path = Path(path)
    if not path.exists():
        return {"skip_folders": [], "omit_query_params": ["orgId"]}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def apply_overrides(
    fields: list[EndpointField], command_type: str, folder_overrides: dict
) -> list[EndpointField]:
    cmd_overrides = folder_overrides.get(command_type, {})
    required = set(cmd_overrides.get("required_fields", []))
    defaults = cmd_overrides.get("defaults", {})
    for f in fields:
        if f.name in required:
            f.required = True
        if f.name in defaults:
            f.default = defaults[f.name]
    return fields


def apply_endpoint_overrides(ep: 'Endpoint', folder_overrides: dict) -> None:
    """Apply folder-level overrides to an endpoint (e.g. response_list_key)."""
    if ep.command_type == "list":
        keys_map = folder_overrides.get("response_list_keys", {})
        if ep.command_name in keys_map:
            ep.response_list_key = keys_map[ep.command_name]


def parse_folder(
    folder: dict, omit_query_params: list[str] | None = None
) -> list[Endpoint]:
    endpoints = []
    seen_types: dict[str, int] = {}
    skipped_uploads = []
    for req in folder.get("item", []):
        body_mode = (req.get("request") or {}).get("body", {})
        if isinstance(body_mode, dict) and body_mode.get("mode") == "formdata":
            skipped_uploads.append(req.get("name", "unknown"))
            continue
        ep = parse_request(req, omit_query_params=omit_query_params)
        ep.command_name = _derive_command_name(
            ep.command_type, ep.raw_path, ep.name, seen_types
        )
        endpoints.append(ep)
    _dedup_command_names(endpoints)
    return endpoints, skipped_uploads
