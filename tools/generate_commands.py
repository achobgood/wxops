"""Generate wxcli command files from OpenAPI spec JSON."""
import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path

from tools.openapi_parser import load_spec, get_tags, parse_tag, _path_to_url_path
from tools.postman_parser import (
    DESTRUCTIVE_SEMANTICS,
    load_overrides,
    apply_endpoint_overrides,
)
from tools.command_renderer import (
    render_command_file, folder_name_to_module, BASE_URL_CC, BASE_URL_FS, OffsetIgnoredError,
)


DEFAULT_SPEC = Path(__file__).parent.parent / "specs" / "webex-cloud-calling.json"
DEFAULT_OVERRIDES = Path(__file__).parent / "field_overrides.yaml"
DEFAULT_OUTPUT = Path(__file__).parent.parent / "src" / "wxcli" / "commands"

# Top-level keys in field_overrides.yaml that are global settings rather than
# tag blocks. Anything else at the top level is treated as a tag block, so a new
# global key must be listed here or its subkeys get validated as tag keys.
# Single source of truth: tests/test_field_overrides.py imports this.
KNOWN_GLOBAL_KEYS = {
    "omit_query_params", "skip_tags", "tag_merge", "cli_name_overrides",
    "auto_inject_from_config", "tag_overrides", "tag_op_excludes",
    "verb_semantics_ack", "_resolved_cli_name_overrides",
    # Consumed by tools/drift_check.py (check 9), not by the generator — but it
    # must still be declared here. An unregistered top-level key falls through
    # to the backwards-compat branch below and is treated as a TAG override
    # block, so "spec_authority" would silently become a tag named
    # "spec_authority". test_field_overrides.py::test_all_keys_recognized is
    # what catches that, and it is why this set exists.
    "spec_authority",
    # Consumed by tools/drift_check.py (check 12) via tools/verb_naming.py:
    # the acknowledged numeric-suffix and resource-mismatch command names.
    "naming_ack",
    # Consumed by tools/drift_check.py (check 15): tags whose config cannot
    # resolve against any spec on disk and is kept deliberately anyway.
    "inert_tag_ack",
    # Consumed by tools/drift_check.py (check 16): operations whose list command
    # carries a `--all` that cannot walk, because the spec declares no paging
    # parameter and no Link header on an endpoint whose 200 declares a total.
    "undeclared_paging_ack",
    # Per-spec, per-OPERATION overrides (skip / blocked / warn, and the keys
    # Task 10 renders). See resolve_operation_overrides.
    "operation_overrides",
}

# Override families inside a tag block whose keys are COMMAND names. Used to
# refuse a key that names no command the tag renders — see the stale-key check
# in generate_tag(). `list` is deliberately absent: it is the old-style
# folder-level `list: {table_columns: [...]}` marker, not a command key.
COMMAND_KEYED_OVERRIDES = (
    "table_columns", "add_query_params", "command_type_overrides",
    "url_overrides", "response_list_keys", "make_optional", "make_required", "body_defaults",
    "command_help_notes", "command_confirms", "param_name_overrides",
    # ADR-18: list commands whose endpoint ignores the `start` the CLI sends
    # for --offset, measured live. {command: evidence}. The renderer refuses
    # --offset on them (exit 2) and their truncation note never names it.
    "offset_ignored",
    # Plan 2 Task 14. {command: false} keeps a list out of the argument-help
    # producer index (command_renderer.build_producer_index); {command:
    # {page: page, size: pageSize|size}} puts a list whose render spec
    # declares no paging onto the page walker (postman_parser).
    "producer", "paging",
    # Plan 2 Task 15c. {command: {query param: evidence}}: a spec query
    # parameter the server ignores, measured live; the parser drops it.
    "drop_query_params",
)

# Where a rename's old name may have SHIPPED (Plan 2 Task 14, Adam's decision
# 4): the name lock records every visible name, and the shipped module carries
# the hidden aliases (the lock deliberately does not). Module attributes so a
# test can point them at fixtures.
NAME_LOCK_PATH = Path(__file__).parent / "command_name_lock.json"
SHIPPED_COMMANDS_DIR = DEFAULT_OUTPUT
_HIDDEN_ALIAS_RE = re.compile(r'^@app\.command\("([^"]+)", hidden=True', re.M)


def shipped_command_names(module_name: str) -> set[str] | None:
    """Every name `module_name` has shipped under, or None when unknowable.

    A module absent from tools/command_name_lock.json has never shipped, so it
    has no names: a brand-new group gets no hidden alias for a derived name
    nobody ever ran (`cc-flow-store list` -> /health). For a shipped module:
    its locked visible names plus the hidden aliases its shipped source
    already carries (renames older than the lock, 2026-09-08, are recorded
    only there). No lock file at all -> None: keep every alias, as before.
    The lock is read before spec_sync refreshes it, so a regen sees the
    names that shipped, not the ones it is about to add.
    """
    if not NAME_LOCK_PATH.exists():
        return None
    locked = json.loads(NAME_LOCK_PATH.read_text()).get("modules") or {}
    if module_name not in locked:
        return set()
    names = set(locked[module_name])
    src = SHIPPED_COMMANDS_DIR / f"{module_name}.py"
    if src.exists():
        names |= set(_HIDDEN_ALIAS_RE.findall(src.read_text()))
    return names


def merge_tags(spec: dict, merge_map: dict) -> None:
    """Rewrite operation tags in-place so merged tags appear under a single name."""
    for merged_name, source_tags in merge_map.items():
        for path, methods in spec.get("paths", {}).items():
            for method, op in methods.items():
                if not isinstance(op, dict):
                    continue
                tags = op.get("tags", [])
                for i, tag in enumerate(tags):
                    if tag in source_tags:
                        tags[i] = merged_name


def should_skip_tag(tag: str, skip_patterns: list[str]) -> bool:
    """Check if a tag matches any skip pattern (glob-style)."""
    for pattern in skip_patterns:
        if fnmatch.fnmatch(tag, pattern):
            return True
    return False


def resolve_skip_patterns(raw: list | dict | None, spec_filename: str) -> list[str]:
    """Merge global skip patterns with per-spec skip patterns for the current spec.

    ``skip_tags`` in field_overrides.yaml supports two shapes:

    1. A flat list (legacy) — patterns apply to every spec.
    2. A mapping with optional ``_global`` key + per-spec-filename keys
       (e.g. ``webex-admin.json``) — each spec only skips the union of
       ``_global`` patterns and its own list. Tags canonical to a given
       spec should NOT appear in that spec's list but SHOULD appear in
       every other spec's list that also exposes them.

    ``spec_filename`` is matched by basename (``Path(spec).name``).
    """
    if raw is None:
        return []
    if isinstance(raw, list):
        return list(raw)
    if isinstance(raw, dict):
        patterns: list[str] = list(raw.get("_global", []) or [])
        per_spec = raw.get(spec_filename) or []
        patterns.extend(per_spec)
        return patterns
    raise TypeError(f"skip_tags must be list or dict, got {type(raw).__name__}")


def resolve_cli_name_overrides(raw: dict | list | None, spec_filename: str) -> dict:
    """Merge global CLI name overrides with per-spec overrides.

    Supports two shapes:
    1. Flat dict (legacy) — all overrides apply to every spec.
    2. Dict with optional ``_global`` + per-spec-filename keys — per-spec
       overrides take precedence over _global for the same tag name.
    """
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise TypeError(f"cli_name_overrides must be dict, got {type(raw).__name__}")
    if "_global" not in raw and not any(k.endswith(".json") for k in raw):
        return dict(raw)
    result = dict(raw.get("_global", {}) or {})
    per_spec = raw.get(spec_filename) or {}
    result.update(per_spec)
    return result


def resolve_tag_merge(raw: dict | None, spec_filename: str) -> dict:
    """Merge global tag_merge rules with per-spec rules.

    Same shape as resolve_cli_name_overrides: flat dict (legacy) or
    dict with _global + per-spec keys.
    """
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise TypeError(f"tag_merge must be dict, got {type(raw).__name__}")
    if "_global" not in raw and not any(k.endswith(".json") for k in raw):
        return dict(raw)
    result = dict(raw.get("_global", {}) or {})
    per_spec = raw.get(spec_filename) or {}
    result.update(per_spec)
    return result


def resolve_tag_op_excludes(raw: dict | None, spec_filename: str) -> dict:
    """Merge global tag_op_excludes rules with per-spec rules.

    ``tag_op_excludes`` drops spurious tag/operation pairings that exist in the
    upstream spec — a tag that a set of operations carries but does not belong
    to. Shape mirrors resolve_tag_merge: flat dict (legacy) or dict with
    ``_global`` + per-spec-filename keys. Each value maps a tag name to a list
    of path globs to exclude from that tag.

    Keys are matched against the tag name as generated, i.e. *after* tag_merge
    rewrites it — use the merged name ("User Call Settings"), not a source tag
    ("User Call Settings (3/3)").
    """
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise TypeError(f"tag_op_excludes must be dict, got {type(raw).__name__}")
    if "_global" not in raw and not any(k.endswith(".json") for k in raw):
        return dict(raw)
    result = dict(raw.get("_global", {}) or {})
    per_spec = raw.get(spec_filename) or {}
    result.update(per_spec)
    return result


class OperationOverrideError(ValueError):
    """An `operation_overrides` entry that cannot apply: an unknown or
    ambiguous operation, or an unknown or malformed inner key.

    Same contract as `verb_semantics_ack` and `param_name_overrides`: the YAML
    is re-validated against the spec on every generation, so an entry cannot
    rot into a silent no-op when upstream renames or drops the operation.
    """


# The `_all` block applies to every operation of the spec. It is returned under
# this key and attached to each Endpoint as op_overrides["_all"].
ALL_OPERATIONS_KEY = ("*", "*")
_OP_KEY_RE = re.compile(r"^(GET|POST|PUT|PATCH|DELETE) (/\S*)$")
_STR_KEYS = ("skip", "blocked", "warn")
# Checked against the rendered command, and rendered, by command_renderer
# (_apply_render_overrides and the render paths; Plan 2 Task 10).
_TASK10_KEYS = ("multipart", "param_help", "body_transform", "exit_code_from")
_OP_INNER_KEYS = set(_STR_KEYS) | set(_TASK10_KEYS)
_ALL_INNER_KEYS = {"param_help"}


def _check_inner(spec_filename: str, key: str, inner, allowed: set) -> None:
    def fail(why: str):
        raise OperationOverrideError(
            f"operation_overrides -> {spec_filename} -> {key!r}: {why}")

    if not isinstance(inner, dict) or not inner:
        fail(f"must be a non-empty mapping, got {inner!r}")
    unknown = sorted(set(inner) - allowed)
    if unknown:
        fail(f"unknown key(s) {', '.join(unknown)}; allowed: {', '.join(sorted(allowed))}")
    for k in _STR_KEYS:
        if k in inner and (not isinstance(inner[k], str) or not inner[k].strip()):
            fail(f"{k} must be a non-empty message string")
    # skip and blocked replace the whole command, so any other key beside
    # them would be inert configuration that parses and does nothing.
    for k in ("skip", "blocked"):
        if k in inner and len(inner) > 1:
            fail(f"{k} replaces the command; drop {', '.join(sorted(set(inner) - {k}))}")
    ph = inner.get("param_help")
    if ph is not None and not (isinstance(ph, dict) and ph and all(
            isinstance(n, str) and isinstance(t, str) and t.strip() for n, t in ph.items())):
        fail("param_help must map wire parameter names to help text")
    mp = inner.get("multipart")
    if mp is not None and mp is not True and not (
            isinstance(mp, dict) and set(mp) == {"field"} and isinstance(mp["field"], str)):
        fail("multipart must be true or {field: <part name>}")
    if "body_transform" in inner and inner["body_transform"] != "json-string":
        fail("body_transform supports only 'json-string'")
    ecf = inner.get("exit_code_from")
    if ecf is not None and not (
            isinstance(ecf, dict) and isinstance(ecf.get("json_key"), str)
            and set(ecf) <= {"json_key", "invert"}
            and isinstance(ecf.get("invert", False), bool)):
        fail("exit_code_from must be {json_key: <key>, invert: <bool>}")


def resolve_operation_overrides(raw: dict | None, spec: dict,
                                spec_filename: str) -> dict[tuple[str, str], dict]:
    """Resolve `operation_overrides` for one spec, keyed (METHOD, spec path).

    Shape: ``{<spec file>: {<key>: {<inner key>: value}}}``. A key is an
    operationId that is unique in that spec, or ``"METHOD /path"`` with the
    path exactly as the spec writes it. The CC spec reuses operationIds across
    paths (tools/CLAUDE.md known issue 16), so a repeated opId is refused
    rather than applied to whichever operation comes first. ``_all`` holds
    settings for every operation and is returned under ALL_OPERATIONS_KEY.
    """
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise OperationOverrideError(
            f"operation_overrides must be a mapping of spec file -> operations, "
            f"got {type(raw).__name__}")
    block = raw.get(spec_filename) or {}
    if not isinstance(block, dict):
        raise OperationOverrideError(
            f"operation_overrides -> {spec_filename} must be a mapping, got "
            f"{type(block).__name__}")
    by_op_id: dict[str, list[tuple[str, str]]] = {}
    for path, path_obj in spec.get("paths", {}).items():
        for method, op in (path_obj or {}).items():
            if isinstance(op, dict) and op.get("operationId"):
                by_op_id.setdefault(op["operationId"], []).append((method.upper(), path))

    resolved: dict[tuple[str, str], dict] = {}
    named_by: dict[tuple[str, str], str] = {}
    for key, inner in block.items():
        if key == "_all":
            _check_inner(spec_filename, key, inner, _ALL_INNER_KEYS)
            resolved[ALL_OPERATIONS_KEY] = dict(inner)
            continue
        _check_inner(spec_filename, key, inner, _OP_INNER_KEYS)
        m = _OP_KEY_RE.match(str(key))
        if m:
            method, path = m.groups()
            if not isinstance((spec.get("paths", {}).get(path) or {}).get(method.lower()), dict):
                raise OperationOverrideError(
                    f"operation_overrides -> {spec_filename} -> {key!r}: no such "
                    f"operation in the spec")
            target = (method, path)
        else:
            matches = by_op_id.get(key, [])
            if not matches:
                raise OperationOverrideError(
                    f"operation_overrides -> {spec_filename} -> {key!r}: no "
                    f"operation has this operationId (and it is not a "
                    f"'METHOD /path' key)")
            if len(matches) > 1:
                raise OperationOverrideError(
                    f"operation_overrides -> {spec_filename} -> {key!r}: "
                    f"operationId is ambiguous, used by "
                    f"{', '.join(f'{m_} {p}' for m_, p in matches)}. Key the "
                    f"entry as 'METHOD /path' instead.")
            target = matches[0]
        if target in resolved:
            raise OperationOverrideError(
                f"operation_overrides -> {spec_filename}: {key!r} and "
                f"{named_by[target]!r} both name {target[0]} {target[1]}; merge them")
        resolved[target] = dict(inner)
        named_by[target] = key
    return resolved


def _spec_without_skipped(spec: dict, op_overrides: dict) -> dict:
    """A view of `spec` without the operations `operation_overrides` skips.

    Dropped BEFORE parse_tag so a skipped operation never takes part in the
    command-name race: it must not hold a bare name (`delete`) that pushes a
    surviving operation onto a suffixed one. The spec itself is not mutated;
    components stay shared, so $refs still resolve.
    """
    skipped = {k for k, v in op_overrides.items() if "skip" in v}
    if not skipped:
        return spec
    paths = {}
    for path, path_obj in spec.get("paths", {}).items():
        if isinstance(path_obj, dict):
            path_obj = {m: o for m, o in path_obj.items()
                        if (m.upper(), path) not in skipped}
        paths[path] = path_obj
    return {**spec, "paths": paths}


def _attach_op_overrides(endpoints: list, op_overrides: dict) -> None:
    """Fill Endpoint.op_overrides from the resolved (METHOD, spec path) map.

    An Endpoint keeps only url_path (leading "/" and "v1/" stripped), so the
    match is on that form. Must run before apply_endpoint_overrides, whose
    url_overrides can rewrite url_path.
    """
    by_url: dict[tuple[str, str], dict] = {}
    for (method, path), inner in op_overrides.items():
        if (method, path) == ALL_OPERATIONS_KEY:
            continue
        key = (method, _path_to_url_path(path))
        if key in by_url:
            raise OperationOverrideError(
                f"operation_overrides: two entries resolve to {method} "
                f"/{key[1]} once the 'v1/' prefix is stripped")
        by_url[key] = inner
    all_block = op_overrides.get(ALL_OPERATIONS_KEY)
    for ep in endpoints:
        merged = dict(by_url.get((ep.method, ep.url_path), {}))
        if all_block:
            merged["_all"] = dict(all_block)
        ep.op_overrides = merged


MANIFEST_HEADER = '''"""Registration manifest for generated command groups.

Emitted by tools/generate_commands.py — do NOT edit by hand.
main.py imports GENERATED_GROUPS and mounts each (module, group) pair;
hand-written seams and aliases stay explicit
in main.py. A stale entry whose module is missing fails import loudly.
"""

GENERATED_GROUPS = [
'''


def update_manifest(generated: list[tuple[str, str]], output_dir: Path) -> None:
    """Upsert (module, cli_name) pairs into _registry.py, sorted by module.

    Upsert (not rewrite): the generator runs per-spec, so a single run only
    knows its own tags. Entries whose tag was renamed/removed upstream must
    be deleted in the regen diff review — a stale entry fails import loudly.
    """
    manifest_path = output_dir / "_registry.py"
    entries: dict[str, str] = {}
    if manifest_path.exists():
        entries = dict(re.findall(r'\("(\w+)", "([\w-]+)"\)', manifest_path.read_text()))
    entries.update(generated)
    lines = [MANIFEST_HEADER]
    lines += [f'    ("{m}", "{g}"),\n' for m, g in sorted(entries.items())]
    lines += ["]\n"]
    manifest_path.write_text("".join(lines))
    print(f"Manifest: {manifest_path.name} updated ({len(entries)} groups)")


def check_verb_semantics(endpoints: list, spec_filename: str, acked: dict) -> list[str]:
    """Return command names whose verb-derived name contradicts what they do.

    Known issue #20. The command name comes from the HTTP method, but Cisco
    models some deletes as PUT/POST with a delete-body, so a destructive
    operation gets named `update-*`/`create-*`. The generator can see both the
    method and the semantics, so it refuses to render the mismatch silently.

    Only names that give the operator *no* signal are an error. A name that
    carries the destructive verb already (`create-purge-inactive-entities`)
    reads oddly but does not mislead, and the success message now follows the
    real semantics regardless — see _success_message in command_renderer.
    """
    problems = []
    for ep in endpoints:
        if not ep.real_semantics or ep.command_type not in ("create", "update"):
            continue
        if any(verb in ep.command_name for verb in DESTRUCTIVE_SEMANTICS):
            continue
        key = f"{ep.method} /{ep.url_path.lstrip('/')}"
        if key in acked:
            declared = acked[key]
            if declared != ep.real_semantics:
                problems.append(
                    f"{ep.command_name!r} is acked as {declared!r} but now classifies as "
                    f"{ep.real_semantics!r} — re-check the spec and update the ack.\n"
                    f"      {key}"
                )
            continue
        problems.append(
            f"{ep.command_name!r} ({ep.method}) really {ep.real_semantics}s: "
            f"{ep.name!r}\n"
            f"      {key}\n"
            f"      Nothing in the name says {ep.real_semantics!r}, so an operator "
            f"reading it cannot tell this is destructive.\n"
            f"      Fix the name via tag_overrides -> command_name_overrides, or if the "
            f"name must stay, ack it in field_overrides.yaml:\n"
            f"        verb_semantics_ack:\n"
            f"          {spec_filename}:\n"
            f"            {key!r}: {ep.real_semantics!r}"
        )
    return problems


def resolve_verb_semantics_ack(raw: dict | None, spec_filename: str) -> dict:
    """Merge global + per-spec verb_semantics_ack. Shape mirrors tag_op_excludes."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise TypeError(f"verb_semantics_ack must be dict, got {type(raw).__name__}")
    result = dict(raw.get("_global", {}) or {})
    result.update(raw.get(spec_filename) or {})
    return result


def generate_tag(
    tag_name: str,
    spec: dict,
    overrides: dict,
    output_dir: Path,
    dry_run: bool,
    seen_op_ids: set,
    base_url_override: str | None = None,
) -> tuple[str, str, int]:
    """Generate commands for one tag. Returns (module_name, cli_name, command_count)."""
    omit_qp = list(overrides.get("omit_query_params", []))
    auto_inject_qp = set(overrides.get("auto_inject_from_config", ["orgId"]))
    folder_ovr = overrides.get(f"_tag_ovr:{tag_name}", {})
    exclude_paths = overrides.get("_resolved_tag_op_excludes", {}).get(tag_name)
    op_overrides = overrides.get("_resolved_operation_overrides") or {}
    endpoints, skipped_uploads = parse_tag(
        tag_name, _spec_without_skipped(spec, op_overrides), omit_query_params=omit_qp,
        auto_inject_params=auto_inject_qp, seen_operation_ids=seen_op_ids,
        exclude_paths=exclude_paths,
        multipart_ops={k for k, v in op_overrides.items() if v.get("multipart")},
    )
    _attach_op_overrides(endpoints, op_overrides)

    # Apply endpoint-level overrides (table_columns, url_overrides)
    for ep in endpoints:
        apply_endpoint_overrides(ep, folder_ovr)

    # A rename keeps its old name as a hidden alias — but ONLY if nothing else
    # in this tag now answers to that name. `command_name_overrides` is
    # sometimes a SWAP, not a rename: `Features:  Call Queue` moves
    # show -> show-org-settings AND show-queues -> show, deliberately handing
    # the bare name to the per-queue command (2026-06 pinning). Aliasing the
    # old `show` there would re-register a second `show` on the same Typer app
    # and shadow the command the swap exists to protect — caught live when
    # check 6 started failing on `call-queue show --has-cx-essentials`.
    claimed = {ep.command_name for ep in endpoints}
    # Read before any alias is dropped: the stale-key guard below needs every
    # rename that applied, aliased or not.
    renamed = {getattr(ep, "original_command_name", None) for ep in endpoints}
    # And only for a name that SHIPPED (Plan 2 Task 14, Adam's decision 4): a
    # rename on a brand-new group, or of a derived name first rendered in this
    # regen, has nothing scripted against it to keep working.
    cli_name_overrides = overrides.get("_resolved_cli_name_overrides", {})
    if tag_name in cli_name_overrides:
        cli_name = cli_name_overrides[tag_name]
        module_name = cli_name.replace("-", "_")
    else:
        module_name, cli_name = folder_name_to_module(tag_name)
    shipped = shipped_command_names(module_name)
    for ep in endpoints:
        original = getattr(ep, "original_command_name", None)
        if original and (original in claimed
                         or (shipped is not None and original not in shipped)):
            ep.original_command_name = None

    # A command_name_overrides key that matches no command is INERT, and inert
    # is indistinguishable from applied unless something says so. Three of the
    # 26 Wave 3 renames were keyed on a pre-merge tag name ("Journey - Customer
    # Identification API" is folded into "CC Journey" by tag_merge before
    # overrides resolve) and were silently ignored — regen succeeded, the gate
    # passed, and the commands simply kept their old names. Fail loudly instead.
    stale = [k for k in (folder_ovr or {}).get("command_name_overrides", {})
             if k not in renamed and k not in claimed]
    if stale:
        print(
            f"\nERROR: command_name_overrides in tag {tag_name!r} names "
            f"{len(stale)} command(s) that do not exist here: "
            f"{', '.join(sorted(stale))}.\n"
            f"       Rendered commands: {', '.join(sorted(claimed))}\n"
            f"       If this tag is merged by tag_merge, key the override on "
            f"the MERGED name.", file=sys.stderr)
        sys.exit(1)

    # The same defect in every OTHER command-keyed family, which went unguarded
    # until 2026-07-29 and had three live instances: table_columns keyed
    # `list-calls` (Call Controls renders list-calls-members / list-calls-me),
    # `list-supported-devices-config` (no such command) and `list-regions` (the
    # regions endpoint renders as the bare `list`). All three parsed, and all
    # three did nothing. Validated against the POST-rename names, because that is
    # what apply_endpoint_overrides and the renderer key on — an override on a
    # pre-rename name is inert even though the hidden alias still answers to it.
    for family in COMMAND_KEYED_OVERRIDES:
        entry = (folder_ovr or {}).get(family)
        if not isinstance(entry, dict):
            continue
        stale = sorted(k for k in entry if k not in claimed)
        if stale:
            print(
                f"\nERROR: {family} in tag {tag_name!r} names {len(stale)} "
                f"command(s) that do not exist here: {', '.join(stale)}.\n"
                f"       Rendered commands: {', '.join(sorted(claimed))}\n"
                f"       Key it on the name the command SHIPS under (after any "
                f"command_name_overrides rename), and on the MERGED tag name if "
                f"tag_merge folds this tag.", file=sys.stderr)
            sys.exit(1)

    # A table override on a command that renders no table is inert the same
    # way: `_render_show_command` emits the whole object and reads no columns.
    # Drift check 31 (2026-10-13) re-rendered 107 list-classified GETs whose
    # 200 is one object as single-object reads, which silently retired the
    # table_columns of 13 of them; this keeps the next one from rotting.
    # `producer` takes only `false`: anything else would parse and do nothing.
    not_false = sorted(k for k, v in ((folder_ovr or {}).get("producer") or {}).items()
                       if v is not False)
    if not_false:
        print(
            f"\nERROR: producer in tag {tag_name!r} must map each command to "
            f"false (keep it out of the argument-help producer index); not "
            f"false for: {', '.join(not_false)}.", file=sys.stderr)
        sys.exit(1)

    types = {ep.command_name: ep.command_type for ep in endpoints}
    for family in ("table_columns", "response_list_keys", "paging"):
        entry = (folder_ovr or {}).get(family)
        if not isinstance(entry, dict):
            continue
        tableless = sorted(k for k in entry
                           if k in types and types[k] != "list")
        if tableless:
            print(
                f"\nERROR: {family} in tag {tag_name!r} names {len(tableless)} "
                f"command(s) that render no list: "
                f"{', '.join(f'{k} ({types[k]})' for k in tableless)}.\n"
                f"       A single-object read emits the whole response and "
                f"reads no columns or list key. Delete the entry. If the "
                f"response really is a collection, the parser's rule is wrong "
                f"for this shape: fix openapi_parser._drops_object_fields and "
                f"regen. Do NOT pin it with command_type_overrides: list -- "
                f"drift check 31 reads the rendered command and fails a list "
                f"that drops part of an object.", file=sys.stderr)
            sys.exit(1)

    # `offset_ignored` describes a list's --offset; on a command that renders
    # no list there is no --offset to refuse, so the entry would be inert.
    ignored = (folder_ovr or {}).get("offset_ignored")
    if isinstance(ignored, dict):
        not_lists = sorted(k for k in ignored if k in types and types[k] != "list")
        if not_lists:
            print(
                f"\nERROR: offset_ignored in tag {tag_name!r} names "
                f"{len(not_lists)} command(s) that render no list: "
                f"{', '.join(f'{k} ({types[k]})' for k in not_lists)}.\n"
                f"       Only a list command sends --offset. Delete the entry.",
                file=sys.stderr)
            sys.exit(1)

    # Known issue #20: refuse to render a destructive op behind a name that
    # gives no hint it destroys. Runs after command_name_overrides, so a name
    # pinned to the truth clears the gate without an ack.
    problems = check_verb_semantics(
        endpoints, overrides.get("_spec_filename", "<spec>"),
        overrides.get("_resolved_verb_semantics_ack", {}),
    )
    if problems:
        print(
            f"\nERROR: verb-vs-semantics mismatch in tag {tag_name!r} "
            f"({len(problems)} command(s)):",
            file=sys.stderr,
        )
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        sys.exit(1)

    if dry_run:
        print(f"\n{'='*60}")
        print(f"  {tag_name} -> {module_name}.py ({cli_name})")
        print(f"  {len(endpoints)} commands, {len(skipped_uploads)} skipped uploads")
        print(f"{'='*60}")
        for ep in endpoints:
            req_fields = [f.name for f in ep.body_fields if f.required]
            print(
                f"  {ep.command_name:30s} {ep.method:6s} {ep.command_type:15s} required={req_fields}"
            )
        if skipped_uploads:
            for name in skipped_uploads:
                print(f"  {'SKIP':30s} {'':6s} {'upload':15s} {name}")
    else:
        try:
            code = render_command_file(cli_name, endpoints, folder_ovr, base_url_override=base_url_override,
                                       spec_filename=overrides.get("_spec_filename"))
        except OffsetIgnoredError as e:
            # A human fix (ADR-18, spec-sync contract §6): never auto-repaired.
            print(f"\nERROR: {e} (tag {tag_name!r})", file=sys.stderr)
            sys.exit(1)
        out_path = output_dir / f"{module_name}.py"
        out_path.write_text(code)
        print(
            f"Generated: {out_path.name} ({len(endpoints)} commands, {len(skipped_uploads)} skipped)"
        )

    return module_name, cli_name, len(endpoints)


def main():
    parser = argparse.ArgumentParser(
        description="Generate wxcli commands from OpenAPI spec"
    )
    parser.add_argument("--tag", help="Generate for a specific tag name")
    parser.add_argument(
        "--folder", help="Alias for --tag (backward compat)", dest="tag_alias"
    )
    parser.add_argument(
        "--all", action="store_true", help="Generate for all non-skipped tags"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be generated"
    )
    parser.add_argument("--list-tags", action="store_true", help="List all tags")
    parser.add_argument(
        "--list-folders",
        action="store_true",
        help="Alias for --list-tags (backward compat)",
    )
    parser.add_argument("--spec", default=str(DEFAULT_SPEC))
    parser.add_argument("--overrides", default=str(DEFAULT_OVERRIDES))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    # Handle backward-compat aliases
    tag = args.tag or args.tag_alias
    list_tags = args.list_tags or args.list_folders

    if not Path(args.spec).exists():
        print(f"Spec not found: {args.spec}", file=sys.stderr)
        print("Set --spec path to your OpenAPI JSON file", file=sys.stderr)
        sys.exit(1)

    spec = load_spec(args.spec)
    overrides = load_overrides(args.overrides)

    # Detect spec-specific base URL override
    spec_name = Path(args.spec).stem
    if "contact-center" in spec_name:
        base_url_override = BASE_URL_CC
    elif "flow-store" in spec_name:
        base_url_override = BASE_URL_FS
    else:
        base_url_override = None

    # Per-operation overrides, validated against this spec before anything renders.
    try:
        overrides["_resolved_operation_overrides"] = resolve_operation_overrides(
            overrides.get("operation_overrides"), spec, Path(args.spec).name)
    except OperationOverrideError as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Resolve per-spec cli_name_overrides
    overrides["_resolved_cli_name_overrides"] = resolve_cli_name_overrides(
        overrides.get("cli_name_overrides"), Path(args.spec).name
    )

    # Resolve per-spec tag-level overrides (command_name_overrides, body_defaults, etc.)
    raw_tag_ovr = overrides.get("tag_overrides", {})
    spec_tag_ovr = {}
    if isinstance(raw_tag_ovr, dict):
        global_tag_ovr = raw_tag_ovr.get("_global", {})
        per_spec_tag_ovr = raw_tag_ovr.get(Path(args.spec).name, {})
        for tag_name in set(list(global_tag_ovr.keys()) + list(per_spec_tag_ovr.keys())):
            merged = dict(global_tag_ovr.get(tag_name, {}))
            merged.update(per_spec_tag_ovr.get(tag_name, {}))
            spec_tag_ovr[tag_name] = merged
    for tag_name, tag_ovr in spec_tag_ovr.items():
        overrides[f"_tag_ovr:{tag_name}"] = tag_ovr
    # A tag can be configured in two places: a top-level block keyed on the tag
    # name, and an entry under `tag_overrides:`. They MERGE, key by key, with
    # tag_overrides winning — so a top-level block that also has a tag_overrides
    # entry still applies.
    #
    # It did not always. Until 2026-07-29 the top-level block was promoted only
    # when tag_overrides did not name the tag, so when both existed the whole
    # top-level block was discarded silently: it parsed, the tests passed, and it
    # did nothing. Six blocks were inert that way — table_columns on 4 tags,
    # add_query_params on `Features:  Call Queue`, and two old-style `list:`
    # blocks. Merging alone would have taken check 9 from 0 to 15, because
    # `Features:  Call Queue`'s folder-level `list:` block applies its four
    # columns to every list-shaped command in the tag (root cause #2 in
    # tools/CLAUDE.md's table-columns entry) — the shadowing had been
    # accidentally shielding the tree from it. So the blocks were fixed FIRST
    # (migrated to per-command form, or deleted after re-verification against
    # their response schemas), and the merge landed after. Both halves are in
    # tools/CLAUDE.md.
    #
    # The merge is SHALLOW: a key present in both is taken from tag_overrides
    # whole, which would silently discard the top-level copy — the same defect
    # one level down. Nothing does that today, and the loop below refuses to let
    # it start.
    for key, val in list(overrides.items()):
        if key in KNOWN_GLOBAL_KEYS or key.startswith("_"):
            continue
        if not isinstance(val, dict):
            continue
        tag_ovr = overrides.get(f"_tag_ovr:{key}") or {}
        clash = sorted(set(val) & set(tag_ovr))
        if clash:
            print(
                f"\nERROR: tag {key!r} declares {', '.join(clash)} both in its "
                f"top-level block and under tag_overrides.\n"
                f"       The merge is shallow, so the tag_overrides copy would "
                f"win and the top-level one would be silently dropped.\n"
                f"       Merge them by hand into one of the two places.",
                file=sys.stderr)
            sys.exit(1)
        merged = dict(val)
        merged.update(tag_ovr)
        overrides[f"_tag_ovr:{key}"] = merged

    # Resolve per-spec spurious tag/operation pairings
    overrides["_resolved_tag_op_excludes"] = resolve_tag_op_excludes(
        overrides.get("tag_op_excludes"), Path(args.spec).name
    )

    # Known issue #20: acknowledged verb-vs-semantics mismatches
    overrides["_spec_filename"] = Path(args.spec).name
    overrides["_resolved_verb_semantics_ack"] = resolve_verb_semantics_ack(
        overrides.get("verb_semantics_ack"), Path(args.spec).name
    )

    # Apply tag merging
    tag_merge = resolve_tag_merge(overrides.get("tag_merge"), Path(args.spec).name)
    if tag_merge:
        merge_tags(spec, tag_merge)

    # Get unique tags (after merging)
    all_tags = get_tags(spec)
    skip_patterns = resolve_skip_patterns(
        overrides.get("skip_tags"), Path(args.spec).name
    )

    if list_tags:
        for i, t in enumerate(all_tags):
            skip = " [SKIP]" if should_skip_tag(t, skip_patterns) else ""
            print(f"{i:2d}. {t}{skip}")
        return

    targets = []
    if tag:
        if tag in all_tags:
            targets = [tag]
        else:
            close = [t for t in all_tags if tag.lower() in t.lower()]
            print(f"Tag not found: {tag}", file=sys.stderr)
            if close:
                print(f"Did you mean: {', '.join(close[:5])}", file=sys.stderr)
            sys.exit(1)
    elif args.all:
        targets = [t for t in all_tags if not should_skip_tag(t, skip_patterns)]
    else:
        parser.print_help()
        return

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    total_cmds = 0
    generated_modules: list[tuple[str, str]] = []

    for t in targets:
        # Dedup per-tag, not globally: an operation that legitimately carries
        # several tags belongs in each of those groups (e.g. the hotDesking
        # members endpoints are both "Features: Hot Desking Members" and
        # "User Call Settings"). A global set gave the op to whichever tag was
        # generated first, silently dropping it from the others.
        #
        # This is only safe because spurious tag pairings are filtered by
        # tag_op_excludes and secondary-tag ops cannot claim a bare command
        # name (see parse_tag). Without both, a foreign op floods the group and
        # wins the name race — read known issue #22 in tools/CLAUDE.md before
        # touching this; it has shipped a broken CLI once already.
        seen_op_ids: set[str] = set()
        module_name, cli_name, cmd_count = generate_tag(
            t, spec, overrides, output_dir, args.dry_run, seen_op_ids,
            base_url_override=base_url_override,
        )
        total_cmds += cmd_count
        generated_modules.append((module_name, cli_name))

    if not args.dry_run and generated_modules:
        print(f"\nTotal: {len(targets)} tags, {total_cmds} commands")
        update_manifest(generated_modules, output_dir)


if __name__ == "__main__":
    main()
