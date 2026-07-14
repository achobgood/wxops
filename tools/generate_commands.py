"""Generate wxcli command files from OpenAPI spec JSON."""
import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path

from tools.openapi_parser import load_spec, get_tags, parse_tag
from tools.postman_parser import (
    DESTRUCTIVE_SEMANTICS,
    load_overrides,
    apply_endpoint_overrides,
)
from tools.command_renderer import render_command_file, folder_name_to_module, BASE_URL_CC, BASE_URL_FS


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
}


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


MANIFEST_HEADER = '''"""Registration manifest for generated command groups.

Emitted by tools/generate_commands.py — do NOT edit by hand.
main.py imports GENERATED_GROUPS and mounts each (module, group) pair;
hand-written seams, aliases, and the dev-only fs_* block stay explicit
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
    if base_url_override == BASE_URL_FS:
        auto_inject_qp.add("projectId")
    folder_ovr = overrides.get(f"_tag_ovr:{tag_name}", {})
    exclude_paths = overrides.get("_resolved_tag_op_excludes", {}).get(tag_name)
    endpoints, skipped_uploads = parse_tag(
        tag_name, spec, omit_query_params=omit_qp,
        auto_inject_params=auto_inject_qp, seen_operation_ids=seen_op_ids,
        exclude_paths=exclude_paths,
    )

    # Apply endpoint-level overrides (table_columns, url_overrides)
    for ep in endpoints:
        apply_endpoint_overrides(ep, folder_ovr)

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

    # Determine module and cli names
    cli_name_overrides = overrides.get("_resolved_cli_name_overrides", {})
    if tag_name in cli_name_overrides:
        cli_name = cli_name_overrides[tag_name]
        module_name = cli_name.replace("-", "_")
    else:
        module_name, cli_name = folder_name_to_module(tag_name)

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
        code = render_command_file(cli_name, endpoints, folder_ovr, base_url_override=base_url_override)
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
    parser.add_argument(
        "--dev-only", action="store_true",
        help="Skip the registration manifest (dev-only specs keep the guarded "
             "manual block in main.py so fresh clones don't break)",
    )
    args = parser.parse_args()

    # Flow-store is dev-only/untracked — never let a local regen write its
    # groups into the tracked manifest
    if "flow-store" in Path(args.spec).name:
        args.dev_only = True

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
    # Backwards compat: top-level tag blocks that aren't in tag_overrides
    for key, val in list(overrides.items()):
        if key in KNOWN_GLOBAL_KEYS or key.startswith("_"):
            continue
        if isinstance(val, dict) and f"_tag_ovr:{key}" not in overrides:
            overrides[f"_tag_ovr:{key}"] = val

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
        if args.dev_only:
            print(f"\n{'='*60}")
            print("  Dev-only spec — manifest NOT updated. Guarded block for main.py:")
            print(f"{'='*60}")
            for module_name, cli_name in generated_modules:
                var = f"{module_name}_app"
                print(f"from wxcli.commands.{module_name} import app as {var}")
                print(f'app.add_typer({var}, name="{cli_name}")')
        else:
            update_manifest(generated_modules, output_dir)


if __name__ == "__main__":
    main()
