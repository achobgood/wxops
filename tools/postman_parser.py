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
class ResponseField:
    """One property of a list response's item schema.

    Deliberately not an EndpointField: a response field never becomes a CLI
    flag, so it has no python_name. It exists to let the renderer pick default
    table columns the endpoint actually returns.
    """
    name: str
    field_type: str
    required: bool = False


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
    auto_inject_params: list[str] = field(default_factory=list)
    auto_inject_path_params: list[str] = field(default_factory=list)
    content_type: str | None = None
    paginates: bool = False
    real_semantics: str | None = None
    # {extraction key -> item-schema fields}, list endpoints only. Keyed by the
    # key the generated code extracts with, so a response_list_keys override
    # applied after parse still resolves (see apply_endpoint_overrides).
    response_item_fields: dict[str, list[ResponseField]] = field(default_factory=dict)
    # {path var name -> {"example", "enum", "format"}}. Path vars are a bare
    # list of names, so everything the spec says about the VALUE was being
    # discarded — the renderer could only echo the name back as the argument's
    # own help. Kept as a side table rather than turning path_vars into objects
    # so ordering, URL substitution, and every existing path_vars consumer are
    # untouched. Absent for a var backfilled by _infer_missing_path_vars.
    path_var_meta: dict[str, dict] = field(default_factory=dict)


# Known issue #20: command_type comes from the HTTP method, but Cisco models
# some deletes as PUT/POST with a delete-body — the verb says update, the
# operation deletes. Maps the operation's real verb to its success message.
DESTRUCTIVE_SEMANTICS = {
    "delete": "Deleted.",
    "remove": "Removed.",
    "purge": "Purged.",
    "clear": "Cleared.",
    "revoke": "Revoked.",
    "unassign": "Unassigned.",
    "cancel": "Cancelled.",
}

# A body field that can only take things away. Deliberately narrow: `numbers`
# on a PUT that also accepts additions is an update, not a delete.
_DELETE_SHAPED_FIELD = re.compile(r"^(delete|remove|purge|revoke|unassign)", re.I)


def summary_leading_verb(summary: str) -> str | None:
    """The first word of an operation summary, lowercased, if it is a word."""
    m = re.match(r"\s*([A-Za-z]+)", summary or "")
    return m.group(1).lower() if m else None


def classify_real_semantics(name: str, body_fields: list) -> str | None:
    """Return an operation's real destructive verb, or None if it isn't one.

    Two independent signals, because either alone misses real cases:

    1. The summary leads with a destructive verb. Catches the ops whose summary
       is honest even though the verb isn't ("Delete Outgoing Permission Access
       Code Location" on a PUT).
    2. Every body field is delete-shaped, so the operation *cannot* do anything
       but delete. Catches the ops whose summary is itself misleading — the
       person/virtual-line/workspace accessCodes PUTs say "Modify Access Codes"
       and accept only `deleteCodes`. Summary-scanning alone never sees these.

    Signal 2 requires *all* fields to be delete-shaped on purpose: `Modify Dial
    Patterns` takes `dialPatterns` (add or delete) plus `deleteAllDialPatterns`,
    which is a genuine update and must not be flagged.
    """
    verb = summary_leading_verb(name)
    if verb in DESTRUCTIVE_SEMANTICS:
        return verb
    names = [f.name for f in body_fields]
    if names and all(_DELETE_SHAPED_FIELD.search(n) for n in names):
        return "delete"
    return None


def camel_to_kebab(name: str) -> str:
    name = name.lstrip("$")
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
        return {"skip_folders": [], "omit_query_params": [], "auto_inject_from_config": ["orgId"]}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def apply_endpoint_overrides(ep: 'Endpoint', folder_overrides: dict) -> None:
    """Apply folder-level overrides to an endpoint (e.g. command_type, response_list_key, url)."""
    if not folder_overrides:
        return
    # Command name overrides (e.g. rename auto-generated names to human-friendly ones)
    name_overrides = folder_overrides.get("command_name_overrides", {})
    old_name = ep.command_name
    if old_name in name_overrides:
        ep.command_name = name_overrides[old_name]
        # Remembered so the renderer can emit the pre-rename name as a hidden
        # alias. A rename is user-facing: anything already scripted against the
        # old name must keep working, which is the condition the 26 CRITICAL
        # renames were approved under (tools/CLAUDE.md, 2026-07-27).
        ep.original_command_name = old_name
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
    # Make-optional overrides (spec says required but API allows alternatives)
    make_opt = folder_overrides.get("make_optional", {})
    if ep.command_name in make_opt:
        opt_names = set(make_opt[ep.command_name])
        for qp in ep.query_params:
            if qp.name in opt_names:
                qp.required = False
    # Response list key overrides
    if ep.command_type == "list":
        keys_map = folder_overrides.get("response_list_keys", {})
        if ep.command_name in keys_map:
            ep.response_list_key = keys_map[ep.command_name]
