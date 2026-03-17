"""Generate wxcli command files from Postman collection JSON."""
import argparse
import fnmatch
import json
import sys
from pathlib import Path

from tools.postman_parser import parse_folder, load_overrides, apply_overrides
from tools.command_renderer import render_command_file, folder_name_to_module, V2_MODULES


DEFAULT_COLLECTION = Path(__file__).parent.parent.parent / "postman-webex-collections" / "webex_cloud_calling.json"
DEFAULT_OVERRIDES = Path(__file__).parent / "field_overrides.yaml"
DEFAULT_OUTPUT = Path(__file__).parent.parent / "src" / "wxcli" / "commands"


def should_skip(folder_name: str, skip_patterns: list[str]) -> bool:
    for pattern in skip_patterns:
        if fnmatch.fnmatch(folder_name, pattern):
            return True
    return False


def generate_folder(folder: dict, overrides: dict, output_dir: Path, dry_run: bool) -> None:
    folder_name = folder["name"]
    module_name, cli_name = folder_name_to_module(folder_name)
    omit_qp = overrides.get("omit_query_params", ["orgId"])

    endpoints, skipped_uploads = parse_folder(folder, omit_query_params=omit_qp)

    folder_ovr = overrides.get(folder_name, {})
    for ep in endpoints:
        ep.body_fields = apply_overrides(ep.body_fields, ep.command_type, folder_ovr)

    required_count = sum(1 for ep in endpoints for f in ep.body_fields if f.required)
    default_count = sum(1 for ep in endpoints for f in ep.body_fields if f.default is not None)

    if module_name in V2_MODULES:
        module_name = f"{module_name}_generated"
        cli_name = f"{cli_name}-generated"

    if dry_run:
        print(f"\n{'='*60}")
        print(f"  {folder_name} -> {module_name}.py ({cli_name})")
        print(f"  {len(endpoints)} commands, {required_count} required fields, {default_count} defaults, {len(skipped_uploads)} skipped uploads")
        print(f"{'='*60}")
        for ep in endpoints:
            req_fields = [f.name for f in ep.body_fields if f.required]
            print(f"  {ep.command_name:30s} {ep.method:6s} {ep.command_type:15s} required={req_fields}")
        if skipped_uploads:
            for name in skipped_uploads:
                print(f"  {'SKIP':30s} {'':6s} {'upload':15s} {name}")
    else:
        code = render_command_file(folder_name, endpoints, folder_ovr)
        out_path = output_dir / f"{module_name}.py"
        out_path.write_text(code)
        print(f"Generated: {out_path.name} ({len(endpoints)} commands, {required_count} required, {default_count} defaults, {len(skipped_uploads)} skipped)")
        print(f"  from wxcli.commands.{module_name} import app as {module_name}_app")
        print(f'  app.add_typer({module_name}_app, name="{cli_name}")')


def main():
    parser = argparse.ArgumentParser(description="Generate wxcli commands from Postman collection")
    parser.add_argument("--folder", help="Generate for a specific folder name")
    parser.add_argument("--all", action="store_true", help="Generate for all non-skipped folders")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be generated")
    parser.add_argument("--list-folders", action="store_true", help="List all folders")
    parser.add_argument("--collection", default=str(DEFAULT_COLLECTION))
    parser.add_argument("--overrides", default=str(DEFAULT_OVERRIDES))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    if not Path(args.collection).exists():
        print(f"Collection not found: {args.collection}", file=sys.stderr)
        print("Download from Postman or set --collection path", file=sys.stderr)
        sys.exit(1)

    with open(args.collection) as f:
        data = json.load(f)
    folders = data["collection"]["item"]
    overrides = load_overrides(args.overrides)
    skip_patterns = overrides.get("skip_folders", [])

    if args.list_folders:
        for i, folder in enumerate(folders):
            name = folder["name"]
            count = len(folder.get("item", []))
            skip = " [SKIP]" if should_skip(name, skip_patterns) else ""
            v2 = " [V2]" if folder_name_to_module(name)[0] in V2_MODULES else ""
            print(f"{i:2d}. {name} ({count} endpoints){skip}{v2}")
        return

    targets = []
    if args.folder:
        targets = [f for f in folders if f["name"] == args.folder]
        if not targets:
            close = [f["name"] for f in folders if args.folder.lower() in f["name"].lower()]
            print(f"Folder not found: {args.folder}", file=sys.stderr)
            if close:
                print(f"Did you mean: {', '.join(close[:5])}", file=sys.stderr)
            sys.exit(1)
    elif args.all:
        targets = [f for f in folders if not should_skip(f["name"], skip_patterns)]
    else:
        parser.print_help()
        return

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    total_cmds = 0
    for folder in targets:
        endpoints, _ = parse_folder(folder, omit_query_params=overrides.get("omit_query_params", ["orgId"]))
        total_cmds += len(endpoints)
        generate_folder(folder, overrides, output_dir, args.dry_run)

    if not args.dry_run:
        print(f"\nTotal: {len(targets)} folders, {total_cmds} commands")


if __name__ == "__main__":
    main()
