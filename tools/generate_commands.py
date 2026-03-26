"""Generate wxcli command files from OpenAPI spec JSON."""
import argparse
import fnmatch
import json
import sys
from pathlib import Path

from tools.openapi_parser import load_spec, get_tags, parse_tag
from tools.postman_parser import load_overrides, apply_endpoint_overrides
from tools.command_renderer import render_command_file, folder_name_to_module


DEFAULT_SPEC = Path(__file__).parent.parent / "specs" / "webex-cloud-calling.json"
DEFAULT_OVERRIDES = Path(__file__).parent / "field_overrides.yaml"
DEFAULT_OUTPUT = Path(__file__).parent.parent / "src" / "wxcli" / "commands"


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


def generate_tag(
    tag_name: str,
    spec: dict,
    overrides: dict,
    output_dir: Path,
    dry_run: bool,
    seen_op_ids: set,
) -> tuple[str, str, int]:
    """Generate commands for one tag. Returns (module_name, cli_name, command_count)."""
    omit_qp = list(overrides.get("omit_query_params", []))
    auto_inject_qp = set(overrides.get("auto_inject_from_config", ["orgId"]))
    folder_ovr = overrides.get(tag_name, {})
    endpoints, skipped_uploads = parse_tag(
        tag_name, spec, omit_query_params=omit_qp,
        auto_inject_params=auto_inject_qp, seen_operation_ids=seen_op_ids
    )

    # Apply endpoint-level overrides (table_columns, url_overrides)
    for ep in endpoints:
        apply_endpoint_overrides(ep, folder_ovr)

    # Determine module and cli names
    cli_name_overrides = overrides.get("cli_name_overrides", {})
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
        code = render_command_file(tag_name, endpoints, folder_ovr)
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

    # Apply tag merging
    tag_merge = overrides.get("tag_merge", {})
    if tag_merge:
        merge_tags(spec, tag_merge)

    # Get unique tags (after merging)
    all_tags = get_tags(spec)
    skip_patterns = overrides.get("skip_tags", [])

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

    seen_op_ids: set[str] = set()
    total_cmds = 0
    generated_modules: list[tuple[str, str]] = []

    for t in targets:
        module_name, cli_name, cmd_count = generate_tag(
            t, spec, overrides, output_dir, args.dry_run, seen_op_ids
        )
        total_cmds += cmd_count
        generated_modules.append((module_name, cli_name))

    if not args.dry_run and generated_modules:
        print(f"\nTotal: {len(targets)} tags, {total_cmds} commands")
        print(f"\n{'='*60}")
        print("  Registration block for main.py:")
        print(f"{'='*60}")
        for module_name, cli_name in generated_modules:
            var = f"{module_name}_app"
            print(f"from wxcli.commands.{module_name} import app as {var}")
            print(f'app.add_typer({var}, name="{cli_name}")')


if __name__ == "__main__":
    main()
