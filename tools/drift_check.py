#!/usr/bin/env python3
"""Drift gate — mechanical coherence checks between specs, CLI, skills, and docs.

Report-only by default (always exits 0); --enforce exits 1 on any failure.
Checks (docs/arch/target-architecture.md §A6):
  1. Spec <-> CLI parity: every non-skipped tracked-spec op has >=1 registered
     command; every registered command URL maps to a live spec op or a
     keep_endpoints entry in tools/field_overrides.yaml.
  2. Reference existence: every `wxcli <group> [<command>]` token in code spans
     of .claude/{skills,agents,rules}/**, docs/reference/**, CLAUDE.md,
     README.md resolves against the built CLI. docs/reference/** is in scope
     because CLAUDE.md's Mandatory Grounding Rule requires the agent to read
     those docs before answering — they are the most load-bearing prose here.
  3. Published counts: "N command groups" / "N OpenAPI specs" claims in
     CLAUDE.md / README.md match measured fresh-clone values. Groups are
     counted as distinct command sets (aliases excluded — see
     distinct_command_sets).
  4. Unreferenced groups: every registered group is referenced by the skills
     layer or declared on CLAUDE.md's out-of-skill-scope list.
  5. Stale overlays: no specs/overlays/** path has been published upstream. An
     overlay claims "live API serves this, published spec omits it"; once
     upstream ships the path that claim is obsolete and the entry must go.

Fresh-clone semantics: only git-tracked specs and command modules count
(dev-only fs_* modules and specs/webex-flow-store.json are untracked).
"""
import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

try:  # runnable as `python tools/drift_check.py` and as an imported module
    from tools.spec_overlay import load_overlay, merge_overlay, superseded_paths
except ImportError:  # pragma: no cover
    from spec_overlay import load_overlay, merge_overlay, superseded_paths

REPO = Path(__file__).resolve().parent.parent
SPECS_DIR = REPO / "specs"
COMMANDS_DIR = REPO / "src" / "wxcli" / "commands"
MAIN_PY = REPO / "src" / "wxcli" / "main.py"
OVERRIDES = REPO / "tools" / "field_overrides.yaml"
ALLOWLIST = REPO / "tools" / "drift_check_allowlist.txt"

HTTP_METHODS = {"get", "put", "post", "patch", "delete"}
URL_BASES = (
    "https://webexapis.com",       # SCIM paths hang off the bare domain (no /v1)
    "https://analytics-calling.webexapis.com",
    "{cc_base_url}",
    "{fs_base_url}",
)  # normalize_path() strips a leading /v1 from whatever remains


def tracked_files(*patterns: str) -> set[str]:
    out = subprocess.run(["git", "ls-files", "--", *patterns],
                         capture_output=True, text=True, cwd=REPO, check=True)
    return {line for line in out.stdout.splitlines() if line}


def tracked_specs() -> set[str]:
    """Tracked OpenAPI specs — files directly under specs/, not specs/overlays/.

    git's pathspec `specs/*.json` matches across directories, so overlay
    fragments (specs/overlays/*.overlay.json) would otherwise be counted as
    specs and parsed as if they were one.
    """
    return {f for f in tracked_files("specs/*.json")
            if Path(f).parent.name == "specs"}


def normalize_path(path: str) -> str:
    """Normalize an API path for matching: params -> {}, strip /v1 prefix."""
    path = re.sub(r"\{[^}]*\}", "{}", path)
    if path.startswith("/v1/"):
        path = path[3:]
    return path.rstrip("/") or "/"


# ---------------------------------------------------------------- spec side

def load_overrides() -> dict:
    """Minimal YAML subset parser for the keys drift_check needs.

    field_overrides.yaml uses plain nested maps/lists for skip_tags and
    keep_endpoints; avoiding a PyYAML dependency keeps this runnable in CI.
    """
    skip_tags: dict[str, list[str]] = {}
    skip_reasons: dict[tuple[str, str], str] = {}   # (spec, pattern) -> comment
    keep_endpoints: list[str] = []
    section = None      # "skip_tags" | "keep_endpoints" | None
    subkey = None
    for raw in OVERRIDES.read_text().splitlines():
        comment = raw.split("#", 1)[1].strip() if "#" in raw else ""
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if indent == 0:
            section = stripped.rstrip(":") if stripped.endswith(":") else None
            subkey = None
            continue
        if section == "skip_tags":
            if stripped.endswith(":") and indent == 2:
                subkey = stripped.rstrip(":")
                skip_tags.setdefault(subkey, [])
            elif stripped.startswith("- ") and subkey:
                pattern = stripped[2:].strip().strip('"').strip("'")
                skip_tags[subkey].append(pattern)
                skip_reasons[(subkey, pattern)] = comment
        elif section == "keep_endpoints":
            if stripped.startswith("- "):
                keep_endpoints.append(stripped[2:].strip().strip('"').strip("'"))
    return {"skip_tags": skip_tags, "skip_reasons": skip_reasons,
            "keep_endpoints": keep_endpoints}


def tag_is_skipped(tag: str, spec_name: str, skip_tags: dict) -> bool:
    patterns = skip_tags.get("_global", []) + skip_tags.get(spec_name, [])
    return any(fnmatch.fnmatch(tag, pat) for pat in patterns)


def load_spec_ops(skip_tags: dict) -> tuple[dict, dict]:
    """Return ({(method, norm_path): (spec, tag)} non-skipped, same for skipped).

    Multipart/form-data operations count as deliberately skipped — the
    generator cannot render file uploads (parse_tag returns them as
    skipped_uploads); they are a known limitation, not drift.
    """
    ops, skipped = {}, {}
    for rel in sorted(tracked_specs()):
        spec_name = Path(rel).name
        spec = json.loads((REPO / rel).read_text())
        # Overlays supply endpoints upstream omits but the live API serves, so
        # the CLI built from them is parity-correct rather than "ahead of spec".
        spec = merge_overlay(spec, load_overlay(REPO / rel))
        for path, methods in spec.get("paths", {}).items():
            for method, op in methods.items():
                if method.lower() not in HTTP_METHODS or not isinstance(op, dict):
                    continue
                tag = (op.get("tags") or ["(untagged)"])[0]
                key = (method.upper(), normalize_path(path))
                content = op.get("requestBody", {}).get("content", {})
                if "multipart/form-data" in content:
                    skipped.setdefault(key, (spec_name, f"{tag} [multipart upload]"))
                elif tag == "(untagged)":
                    # generator iterates tags; untagged ops are structurally
                    # ungeneratable (upstream spec bug) — deliberate gap
                    skipped.setdefault(key, (spec_name, "(untagged) [ungeneratable]"))
                elif tag_is_skipped(tag, spec_name, skip_tags):
                    skipped.setdefault(key, (spec_name, tag))
                else:
                    ops.setdefault(key, (spec_name, tag))
    return ops, skipped


# ----------------------------------------------------------------- CLI side

def parse_registrations() -> dict[str, str]:
    """Registered group name -> module name (manifest + explicit main.py)."""
    groups = {}
    registry = COMMANDS_DIR / "_registry.py"
    if registry.exists():
        for mod, grp in re.findall(r'\("(\w+)", "([\w-]+)"\)', registry.read_text()):
            groups[grp] = mod
    src = MAIN_PY.read_text()
    var_to_module = {var: mod for mod, var in re.findall(
        r"from wxcli\.commands\.(\w+) import app as (\w+)", src)}
    for var, name in re.findall(r"app\.add_typer\((\w+),\s*name=\"([^\"]+)\"", src):
        if var in var_to_module:
            groups[name] = var_to_module[var]
    # aliases mount a manifest group's app under a second name
    for base, alias in re.findall(
            r"app\.add_typer\(_generated_apps\[\"([\w-]+)\"\],\s*name=\"([\w-]+)\"", src):
        if base in groups:
            groups[alias] = groups[base]
    return groups


def parse_module_commands(module: str) -> dict[str, list[tuple[str, str]]]:
    """Parse a command module: command name -> [(METHOD, norm_path), ...]."""
    path = COMMANDS_DIR / f"{module}.py"
    if not path.exists():
        return {}
    src = path.read_text()
    commands: dict[str, list[tuple[str, str]]] = {}
    blocks = re.split(r"(@\w+\.command\((?:\"[^\"]*\")?\)?)", src)
    for i in range(1, len(blocks), 2):
        deco, body = blocks[i], blocks[i + 1]
        named = re.search(r"\.command\(\"([^\"]+)\"", deco)
        if named:
            name = named.group(1)
        else:
            func = re.search(r"def\s+(\w+)\s*\(", body)
            if not func:
                continue
            name = func.group(1).replace("_", "-")
        urls, current = [], None
        for m in re.finditer(
                r"url = f?\"([^\"]+)\""
                r"|rest_(get|put|post|patch|delete)\("
                r"|follow_pagination\(", body):
            if m.group(1):
                current = m.group(1)
                for base in URL_BASES:
                    if current.startswith(base):
                        current = current[len(base):]
                        break
            elif current is not None:
                method = (m.group(2) or "get").upper()
                urls.append((method, normalize_path(current)))
        commands.setdefault(name, []).extend(dict.fromkeys(urls))
    # nested sub-typers (e.g. cucm.py mounts cucm_config as `config`) are
    # commands from the reference checker's point of view
    for sub in re.findall(r"app\.add_typer\(\w+,\s*name=\"([^\"]+)\"", src):
        commands.setdefault(sub, [])
    return commands


def build_cli_surface() -> tuple[dict, set[str]]:
    """Return ({group: {command: [(METHOD, path)]}} for tracked modules,
    top-level command names from main.py)."""
    tracked_modules = {Path(f).stem for f in tracked_files("src/wxcli/commands/*.py")}
    surface = {}
    for group, module in parse_registrations().items():
        if module not in tracked_modules:
            continue  # dev-only (fs_*) — absent on a fresh clone
        surface[group] = parse_module_commands(module)
    # converged_recordings_export mounts download/export onto the generated
    # group at import time (main.py register() pattern)
    if "converged-recordings" in surface:
        surface["converged-recordings"].update(
            parse_module_commands("converged_recordings_export"))
    top_level = set()
    main_src = MAIN_PY.read_text()
    for m in re.finditer(r"@app\.command\((?:\"([^\"]+)\")?\)\s*\ndef\s+(\w+)",
                         main_src):
        top_level.add(m.group(1) or m.group(2).replace("_", "-"))
    # call-form registration — app.command(name="init")(init_command). Not a
    # decorator, so the pattern above cannot see it; `init` is a real command.
    for m in re.finditer(r"app\.command\(name=\"([^\"]+)\"\)\(", main_src):
        top_level.add(m.group(1))
    return surface, top_level


def distinct_command_sets() -> int:
    """Distinct tracked command modules behind the registered groups.

    Aliases (cx-essentials, users, licenses-api) mount an existing module under
    a second name — the same commands, not a separate command set. Published
    "N command groups" claims count command sets, so aliases are excluded.
    """
    tracked = {Path(f).stem for f in tracked_files("src/wxcli/commands/*.py")}
    return len({m for m in parse_registrations().values() if m in tracked})


# ------------------------------------------------------------------ check 1

def check_parity(surface: dict, spec_ops: dict, skipped_ops: dict,
                 keep_endpoints: list[str]) -> dict:
    covered = {}
    for group, commands in surface.items():
        for command, ops in commands.items():
            for op in ops:
                covered.setdefault(op, []).append(f"{group} {command}")
    missing = [
        {"method": m, "path": p, "spec": spec, "tag": tag}
        for (m, p), (spec, tag) in sorted(spec_ops.items())
        if (m, p) not in covered
    ]
    kept = {normalize_path(k.split(" ", 1)[1]) if " " in k else normalize_path(k)
            for k in keep_endpoints}
    ahead = [
        {"method": m, "path": p, "commands": cmds}
        for (m, p), cmds in sorted(covered.items())
        if (m, p) not in spec_ops and (m, p) not in skipped_ops and p not in kept
        # hand-written modules with variable bases (converged export) are
        # chartered exceptions — their URLs can't be resolved statically
        and not p.startswith("{}")
    ]
    return {"missing_from_cli": missing, "cli_ahead_of_spec": ahead}


# ------------------------------------------------------------------ check 2

SCAN_PATTERNS = (".claude/skills/**", ".claude/agents/**", ".claude/rules/**",
                 "docs/reference/**", "CLAUDE.md", "README.md")
TOKEN = re.compile(r"wxcli\s+([a-z0-9][a-z0-9_-]*)(?:\s+([a-z0-9][a-z0-9_-]*))?")
PLACEHOLDER = re.compile(r"[<>\[\]{}$|]")


def code_spans(text: str):
    """Yield (line_number, span_text) for fenced blocks and inline code."""
    fence_open = None
    for lineno, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            fence_open = None if fence_open else lineno
            continue
        if fence_open:
            if not line.lstrip().startswith("#"):  # shell comments are prose
                yield lineno, line
        else:
            for span in re.findall(r"`([^`]+)`", line):
                yield lineno, span


def load_allowlist() -> set[str]:
    if not ALLOWLIST.exists():
        return set()
    return {line.strip() for line in ALLOWLIST.read_text().splitlines()
            if line.strip() and not line.startswith("#")}


def check_references(surface: dict, top_level: set[str]) -> tuple[list, dict]:
    """Validate wxcli tokens in code spans; also collect group reference counts."""
    dead, group_refs = [], {g: 0 for g in surface}
    allow = load_allowlist()
    for rel in sorted(f for pat in SCAN_PATTERNS for f in tracked_files(pat)
                      if f.endswith(".md")):
        text = (REPO / rel).read_text()
        if rel.startswith(".claude/"):
            # check 4 asks "does the skills layer claim this group" — root
            # CLAUDE.md/README mentions (known-issue rows) don't count
            for g in surface:
                if f"`{g}`" in text or f"wxcli {g}" in text:
                    group_refs[g] += 1
        for lineno, span in code_spans(text):
            for m in TOKEN.finditer(span):
                group, command = m.group(1), m.group(2)
                if PLACEHOLDER.search(m.group(0)):
                    continue
                if group[-1] in "-_" or (command and command[-1] in "-_"):
                    continue  # truncated placeholder like `wxcli cc-<group>`
                entry = f"{group} {command}" if command else group
                if entry in allow or group in allow:
                    continue
                if group in top_level:
                    continue
                if group not in surface:
                    dead.append({"file": rel, "line": lineno,
                                 "ref": f"wxcli {group}", "kind": "group"})
                elif command and command not in surface[group]:
                    dead.append({"file": rel, "line": lineno,
                                 "ref": f"wxcli {group} {command}", "kind": "command"})
    return dead, group_refs


# ------------------------------------------------------------------ check 3

def check_counts(surface: dict) -> list:
    measured_groups = distinct_command_sets()
    measured_specs = len(tracked_specs())
    mismatches = []
    for rel in ("CLAUDE.md", "README.md"):
        text = (REPO / rel).read_text()
        for n in {int(x) for x in re.findall(r"(\d+)\s+command groups", text)}:
            if n != measured_groups:
                mismatches.append({"file": rel, "claim": f"{n} command groups",
                                   "measured": measured_groups})
        for n in {int(x) for x in re.findall(r"(\d+)\s+OpenAPI(?:\s+3\.0)?\s+specs?", text)}:
            if n != measured_specs:
                mismatches.append({"file": rel, "claim": f"{n} OpenAPI specs",
                                   "measured": measured_specs})
    # NOTE: bare "N commands" phrases are deliberately not checked — they are
    # ambiguous (per-group and per-spec counts use the same wording). The
    # measured total is printed in the report header instead.
    return mismatches


# ------------------------------------------------------------------ check 4

OUT_OF_SCOPE_HEADING = re.compile(r"out.of.skill.scope", re.IGNORECASE)


def declared_out_of_scope() -> set[str]:
    """Backticked group names under CLAUDE.md's out-of-skill-scope heading."""
    text = (REPO / "CLAUDE.md").read_text()
    groups, in_section = set(), False
    for line in text.splitlines():
        if line.startswith("#"):
            in_section = bool(OUT_OF_SCOPE_HEADING.search(line))
            continue
        if in_section:
            groups.update(re.findall(r"`([a-z0-9*_-]+)`", line))
    return groups


def check_unreferenced(group_refs: dict) -> list:
    declared = declared_out_of_scope()
    return sorted(
        g for g, count in group_refs.items()
        if count == 0 and not any(fnmatch.fnmatch(g, d) for d in declared)
    )


# ------------------------------------------------------------------ check 5

def check_overlays() -> list:
    """Overlay paths upstream now publishes — the overlay entry must be deleted.

    An overlay asserts "the live API serves this but the published spec omits
    it". Once upstream publishes the path, that claim is obsolete and the
    overlay would silently shadow Cisco's own definition. Failing here is what
    stops an overlay outliving its purpose. See tools/spec_overlay.py rule 1.
    """
    stale = []
    for rel in sorted(tracked_specs()):
        raw = json.loads((REPO / rel).read_text())
        for p in superseded_paths(raw, load_overlay(REPO / rel)):
            stale.append({"spec": Path(rel).name, "path": p})
    return stale


# ---------------------------------------------------------- deliberate gaps

GAPS_DOC = REPO / "docs" / "arch" / "deliberate-gaps.md"


def write_gaps_doc(skipped_ops: dict, overrides: dict) -> None:
    """Emit docs/arch/deliberate-gaps.md so 'no CLI' is classifiable as
    deliberate vs drift without re-running the coherence audit."""
    by_spec_tag: dict[tuple[str, str], list[str]] = {}
    for (method, path), (spec, tag) in sorted(skipped_ops.items()):
        by_spec_tag.setdefault((spec, tag), []).append(f"`{method} {path}`")
    skip_tags, reasons = overrides["skip_tags"], overrides["skip_reasons"]

    def reason_for(spec: str, tag: str) -> str:
        if tag.endswith("[multipart upload]"):
            return "multipart file upload — the generator cannot render these (parse_tag skipped_uploads)"
        if tag.endswith("[ungeneratable]"):
            return "untagged operation — the generator iterates tags, so this op cannot generate (upstream spec bug)"
        for scope in (spec, "_global"):
            for pat in skip_tags.get(scope, []):
                if fnmatch.fnmatch(tag, pat):
                    return reasons.get((scope, pat)) or "see tools/field_overrides.yaml"
        return "see tools/field_overrides.yaml"

    lines = [
        "# Deliberate CLI Gaps (generated)",
        "",
        "Emitted by `tools/drift_check.py --write-gaps` — do NOT edit by hand.",
        "Spec operations with no CLI command **on purpose**, per `skip_tags` in",
        "`tools/field_overrides.yaml`. Anything missing from the CLI and not",
        "listed here is drift (drift-gate check 1).",
        "",
    ]
    total = 0
    for (spec, tag), ops in sorted(by_spec_tag.items()):
        total += len(ops)
        lines.append(f"## {spec} — {tag} ({len(ops)} ops)")
        lines.append(f"Reason: {reason_for(spec, tag)}")
        lines.extend(f"- {op}" for op in ops)
        lines.append("")
    if overrides["keep_endpoints"]:
        lines.append("## CLI-ahead endpoints kept deliberately (`keep_endpoints`)")
        lines.extend(f"- `{k}`" for k in overrides["keep_endpoints"])
        lines.append("")
    lines.insert(7, f"**{total} skipped operations across {len(by_spec_tag)} spec/tag pairs.**")
    lines.insert(8, "")
    GAPS_DOC.write_text("\n".join(lines))
    print(f"wrote {GAPS_DOC.relative_to(REPO)} ({total} ops)")


# --------------------------------------------------------------------- main

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enforce", action="store_true",
                        help="exit 1 on any failing check (default: report only)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--write-gaps", action="store_true",
                        help="emit docs/arch/deliberate-gaps.md from skip_tags")
    args = parser.parse_args()

    overrides = load_overrides()
    spec_ops, skipped_ops = load_spec_ops(overrides["skip_tags"])
    surface, top_level = build_cli_surface()

    if args.write_gaps:
        write_gaps_doc(skipped_ops, overrides)

    parity = check_parity(surface, spec_ops, skipped_ops, overrides["keep_endpoints"])
    dead_refs, group_refs = check_references(surface, top_level)
    count_mismatches = check_counts(surface)
    unreferenced = check_unreferenced(group_refs)
    stale_overlays = check_overlays()

    results = {
        "1_spec_cli_parity": parity,
        "2_dead_references": dead_refs,
        "3_count_mismatches": count_mismatches,
        "4_undeclared_unreferenced_groups": unreferenced,
        "5_stale_overlays": stale_overlays,
    }
    failed = bool(parity["missing_from_cli"] or parity["cli_ahead_of_spec"]
                  or dead_refs or count_mismatches or unreferenced
                  or stale_overlays)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"drift-check: {distinct_command_sets()} command sets "
              f"({len(surface)} registered names incl. aliases), "
              f"{sum(len(c) for c in surface.values())} commands, "
              f"{len(spec_ops)} non-skipped spec ops "
              f"({len(skipped_ops)} deliberately skipped)\n")
        print(f"[1] spec->CLI missing: {len(parity['missing_from_cli'])}   "
              f"CLI-ahead-of-spec: {len(parity['cli_ahead_of_spec'])}")
        for op in parity["missing_from_cli"][:15]:
            print(f"      MISSING {op['method']:6} {op['path']}  ({op['spec']}: {op['tag']})")
        if len(parity["missing_from_cli"]) > 15:
            print(f"      ... and {len(parity['missing_from_cli']) - 15} more (--json for all)")
        for op in parity["cli_ahead_of_spec"][:15]:
            print(f"      AHEAD   {op['method']:6} {op['path']}  ({', '.join(op['commands'])})")
        if len(parity["cli_ahead_of_spec"]) > 15:
            print(f"      ... and {len(parity['cli_ahead_of_spec']) - 15} more (--json for all)")
        print(f"[2] dead wxcli references: {len(dead_refs)}")
        for ref in dead_refs[:20]:
            print(f"      {ref['file']}:{ref['line']}  {ref['ref']}  (dead {ref['kind']})")
        if len(dead_refs) > 20:
            print(f"      ... and {len(dead_refs) - 20} more (--json for all)")
        print(f"[3] published-count mismatches: {len(count_mismatches)}")
        for cm in count_mismatches:
            print(f"      {cm['file']}: says \"{cm['claim']}\", measured {cm['measured']}")
        print(f"[4] unreferenced groups not on the out-of-scope list: {len(unreferenced)}")
        if unreferenced:
            print(f"      {', '.join(unreferenced)}")
        print(f"[5] stale overlays (upstream now publishes the path): {len(stale_overlays)}")
        for s in stale_overlays:
            print(f"      {s['spec']}: {s['path']} — delete this overlay entry")
        print(f"\nresult: {'FAIL' if failed else 'PASS'}"
              f"{' (advisory — not enforcing)' if failed and not args.enforce else ''}")

    return 1 if (failed and args.enforce) else 0


if __name__ == "__main__":
    sys.exit(main())
