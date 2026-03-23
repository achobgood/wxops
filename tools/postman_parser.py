"""Shared dataclasses and utilities for wxcli command generation.

Originally parsed Postman collections; now used by the OpenAPI parser pipeline.
Dead Postman-specific code removed 2026-03-18.
"""
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
    enum_values: list[str] | None = None


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
    response_id_key: str | None = None
    deprecated: bool = False
    json_body_example: str | None = None


def camel_to_kebab(name: str) -> str:
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1-\2", name)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", s)
    return s.lower().lstrip("-")


def camel_to_snake(name: str) -> str:
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    return s.lower().lstrip("_")


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


def load_overrides(path: str | Path) -> dict:
    path = Path(path)
    if not path.exists():
        return {"skip_folders": [], "omit_query_params": ["orgId"]}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def apply_endpoint_overrides(ep: 'Endpoint', folder_overrides: dict) -> None:
    """Apply folder-level overrides to an endpoint (e.g. command_type, response_list_key, url)."""
    if not folder_overrides:
        return
    # URL overrides (e.g. fix incorrect paths)
    url_overrides = folder_overrides.get("url_overrides", {})
    if ep.command_name in url_overrides:
        ep.url_path = url_overrides[ep.command_name]
    # Command type overrides (e.g. reclassify list -> settings-get for singletons)
    type_overrides = folder_overrides.get("command_type_overrides", {})
    if ep.command_name in type_overrides:
        new_type = type_overrides[ep.command_name]
        ep.command_type = new_type
        if new_type in ("settings-get", "show"):
            ep.response_list_key = None
    # Add query params override (inject params the spec is missing)
    add_qp = folder_overrides.get("add_query_params", {})
    if ep.command_name in add_qp:
        for param_def in add_qp[ep.command_name]:
            ep.query_params.append(EndpointField(
                name=param_def["name"],
                python_name=camel_to_kebab(param_def["name"]),
                field_type=param_def.get("type", "str"),
                description=param_def.get("description", ""),
            ))
    # Response list key overrides
    if ep.command_type == "list":
        keys_map = folder_overrides.get("response_list_keys", {})
        if ep.command_name in keys_map:
            ep.response_list_key = keys_map[ep.command_name]
