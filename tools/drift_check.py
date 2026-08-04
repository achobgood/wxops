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
     CLAUDE.md / README.md match measured fresh-clone values, AND the two
     files do not contradict each other. Groups are counted as distinct
     command sets (aliases excluded — see distinct_command_sets). Three
     phrasings are harvested, not one: `N command groups`, `N CLI command
     groups`, and the bare `N groups` (CLI context required, see
     harvest_count_claims). The original single pattern could see only the
     first, so README shipped 178 and 176 at once while this check read 0.
     The contradiction oracle is deliberately independent of the measurement:
     two published values disagreeing is a defect whichever one is right.
  4. Unreferenced groups: every registered group is referenced by the skills
     layer or declared on CLAUDE.md's out-of-skill-scope list.
  5. Stale overlays: no specs/overlays/** path has been published upstream. An
     overlay claims "live API serves this, published spec omits it"; once
     upstream ships the path that claim is obsolete and the entry must go.
  6. Flag existence: every `--flag` cited after a resolvable `wxcli <group>
     <command>` in those same code spans is accepted by that command. Check 2
     proves the command name resolves; it never looks at flags, so docs could
     (and did) tell an operator to type options the generator had made
     positional arguments.
  7. Prose flags: every backticked `--flag` anywhere in those same files —
     not just ones trailing a resolvable `wxcli <group> <command>` — exists
     on at least one command somewhere in the CLI. This is the command-free
     complement to check 6: weaker, because with no command in front of the
     flag it can only prove the flag exists *somewhere*, never that it is the
     right flag for the command actually named nearby (`--media-type` on
     `cc-ewt show` is real only on `cc-tasks create`, and passes this check
     regardless). Flags documented on purpose as non-existent — to warn an
     operator away from reaching for one — are allowlisted per file/flag
     rather than flagged as drift.

  8. Untracked modules: a src/wxcli/commands/*.py module that is present and
     not gitignored, but not staged. Separate from check 1 — the command
     exists, only the `git add` is missing.

  9. Table columns: every accessor in a generated list command's `columns=`
     exists on the item schema of the 200 response, resolved through the key
     that command actually extracts with. Unlike checks 6/7 — which prove a
     documented flag exists — this one catches a defect an operator cannot
     see: the command exits 0 and prints a table whose columns are blank,
     because the API returns phoneNumber/clusterId and the table asked for
     id/name. -o json was always correct; only the table lied.

  10. Positional arguments: every documented `wxcli <group> <command> ...`
      example in those same code spans supplies the number of positional
      (typer.Argument) values the command actually declares — not too many,
      not too few, and none at all on a command that takes zero. Checks 6/7
      prove a documented FLAG exists; nothing checks positionals, so docs
      could (and did) pass a resource ID positionally to a command whose real
      positional is something else, or none at all — the copy-pasted example
      aborts immediately. A bare `wxcli <group> <command>` with no arguments,
      cited outside a fenced block, is a reference-table mention rather than
      a runnable example and is reported separately, never failed.

  11a. Required flags: a documented example supplies every option the command
      declares `typer.Option(...)`. Check 10 counts positionals only, so an
      example can have the right argument count and still abort. Read off the
      RENDERED command, never the spec — auto_inject_from_config makes 12
      spec-required parameters legitimately absent from --help. Fenced
      examples fail; inline mentions are counted separately.

  11b. Argument kinds: a doc placeholder (CLUSTER_ID, TEMPLATE_ID) names the
      resource the positional actually takes. Two tiers — a specific declared
      kind that disagrees is mechanical and gated; a bare `UUID` argument can
      only be judged by its producer command, which is a heuristic and is
      reported, never failed. Arguments whose declared kind contradicts their
      own parameter name (79 of 1049) are excluded and reported separately:
      there the CLI's help is wrong, not the doc.

  12. Command naming: no shipping command name whose obvious reading is wrong
      is unacknowledged — a `-N` suffix the generator minted for a collision,
      or a bare verb whose URL targets something other than the group's
      headline resource. CRITICAL+HIGH fails, MEDIUM is reported. Existing
      debt is acknowledged per operation in field_overrides.yaml's
      `naming_ack`, which is re-validated every run so it cannot rot.
      Classification lives in tools/verb_naming.py.

  13. Runnable generated examples: the auto-generated `Example:` line in a
      generated command's docstring — the one `--help` prints — names every
      flag the command HAS, so when the declaring spec marks a body field or
      query parameter REQUIRED and the generator emitted no flag for it, the
      example looks complete and still cannot succeed. Live anchor:
      `location-settings create` omitted `address` and 400'd with
      {location.address.null}; 99 of 1,410 commands printing an example were
      in that state. Check 11a cannot cover this — it scans hand-written
      markdown against the rendered CLI, while the broken string lives in a
      generated module's docstring 11a never reads, and its requiredness comes
      off the rendered Typer signature, where a flagless field has no node to
      find. Disjoint corpora, disjoint oracles. Only spec-REQUIRED fields are
      considered, so a flagless OPTIONAL field cannot fire it.

  14. Skeleton completeness: the `--generate-json-body` skeleton a generated
      module ships never renders a nested object/array as the scalar "..."
      and never omits a field the spec marks required. Both were live
      truncations in openapi_parser (a depth cutoff, 147 cases; `ordered[:8]`,
      which dropped a REQUIRED field on 5 commands) — so the documented escape
      hatch for exactly the bodies check 13 flags was itself emitting a body
      the API rejects. The bounds that remain there return a type-correct
      empty container rather than dropping a property, so this check stays
      satisfiable on a pathological schema.

  15. Inert overrides: no entry in tools/field_overrides.yaml is configuration
      that cannot apply — a tag block, tag_overrides entry or
      cli_name_overrides entry keyed on a tag no spec on disk generates, a
      per-command key naming a command its tag does not render, or one family
      declared in BOTH a top-level block and a tag_overrides entry (where the
      shallow merge drops the top-level copy). This is the quietest defect in
      the file: it parses, every existing test passes, and it does nothing.
      Six blocks were inert that way for months — the shadowed-block class was
      also, by accident, the only thing holding check 9 at 0 on call-queue.
      Deliberate exceptions are declared in `inert_tag_ack` and re-validated,
      so an ack whose tag returns fails instead of lingering.

  16. Inert `--all`: no list command carries a `--all` that cannot walk
      anything on an endpoint whose own 200 schema declares a paging total.
      `--all` is uniform on all 507 list commands and reaches a pager on 264;
      the other 243 are inert BY DESIGN, because the spec says the endpoint
      does not page. Nothing verified that. Where a spec under-declares — no
      paging parameter, no Link header — the command renders inert and returns
      page one, while `rest_get`'s runtime warning still fires off the body
      total, so the CLI reports truncation and offers no flag that fixes it.
      The oracle is the RENDERED module (a fetch block with no all_pages
      branch), so fixing the generator retires findings rather than rotting
      them. `/count` paths are excluded — measured: 5 of 7 raw hits are
      `availableMembers/count`, where the total is the answer. Acked per
      operation in `undeclared_paging_ack`, re-validated every run.

  18. Reference-doc shape: every docs/reference/*.md satisfies the structural
      rules in that directory's own CLAUDE.md — in-document `](#anchor)` links
      land on a real heading, the file ends with exactly one newline, and a
      `## See Also` section exists. This is the only check that reads a doc as
      a DOCUMENT rather than as a carrier of wxcli commands, and it catches a
      rot the others structurally cannot: devices-core.md's contents list
      pointed at `#5-raw-http` / `#6-gotchas` long after those headings became
      `## 6.` / `## 7.`, so four links landed nowhere while checks 2/6/7/10/11
      all read that file and reported it clean. Hand-repaired once (a016cea)
      and drifted straight back, which is the argument for a machine reading
      it. Conventions with legitimate exceptions on disk — no Sources, no
      Gotchas, no contents list, See Also not last — are ADVISORY and never
      fail: a gate that fails on a judgement call is a gate someone switches
      off.

Note: checks 13 and 14 share one pass (check_generated_help) over the same
join of shipped source to declaring spec, and both index specs PER FILE. They
skip an operation whose declaring specs disagree rather than unioning them —
unioning is how check 9's predecessor reported a confident 0 over a live-broken
command. Both also assert the dev-only fs_* exclusion rather than assuming it.

Note: checks 2, 10, 11a and 11b share `command_heads`, which reads BOTH
`wxcli <group> <command>` and the prefixless `<group> <command>` form that
skill quick-reference tables use. Keying only on the literal `wxcli` hid 14
dead references and 10 broken examples while every check reported 0.

Fresh-clone semantics: only git-tracked specs count
(specs/webex-flow-store.json is untracked). Command modules count unless a
gitignore rule excludes them (dev-only fs_*), so a newly generated module is
counted — and reported by check 8 — rather than silently treated as absent.
"""
import argparse
import ast
import fnmatch
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

try:  # runnable as `python tools/drift_check.py` and as an imported module
    from tools.spec_overlay import load_overlay, merge_overlay, superseded_paths
    from tools import verb_naming
except ImportError:  # pragma: no cover
    from spec_overlay import load_overlay, merge_overlay, superseded_paths
    import verb_naming

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


_IGNORE_CACHE: dict[tuple[str, ...], set[str]] = {}


def ignored_files(paths) -> set[str]:
    """Subset of `paths` that a gitignore rule excludes — one batched git call.

    git check-ignore consults the index, so a tracked path is never reported
    even when a pattern matches it; this can only ever flag files a fresh clone
    would not have. Exit 1 means "no path matched", a normal answer here.
    """
    key = tuple(sorted(paths))
    if key not in _IGNORE_CACHE:
        if not key:
            return _IGNORE_CACHE.setdefault(key, set())
        out = subprocess.run(["git", "check-ignore", "--stdin"],
                             input="\n".join(key), capture_output=True,
                             text=True, cwd=REPO)
        if out.returncode not in (0, 1):
            raise RuntimeError(f"git check-ignore failed: {out.stderr.strip()}")
        _IGNORE_CACHE[key] = {line for line in out.stdout.splitlines() if line}
    return _IGNORE_CACHE[key]


_MODULE_STATE: dict[str, set[str]] | None = None


def module_state() -> dict[str, set[str]]:
    """Classify src/wxcli/commands/*.py module stems: countable vs untracked.

    "countable" is what the published counts and checks 1/3/6 are built from. A
    module counts unless a gitignore rule excludes it — the dev-only fs_*
    modules (.gitignore:111) exist only on a developer's machine and counting
    them would make the published "N command groups" claim unreproducible.

    Index membership is deliberately NOT the test. A freshly generated module
    is legitimately required but untracked until `git add`; treating it as
    absent made check 1 report phantom "spec->CLI missing" entries for commands
    that existed and were correct, and froze the command-set count. That third
    state — present, not ignored, not staged — is "untracked", reported on its
    own by check 8. Tracked stems stay countable even if the file is missing
    locally, since a fresh clone would still have it.
    """
    global _MODULE_STATE
    if _MODULE_STATE is None:
        tracked = {Path(f).stem for f in tracked_files("src/wxcli/commands/*.py")}
        on_disk = {f"src/wxcli/commands/{p.name}" for p in COMMANDS_DIR.glob("*.py")}
        ignored = {Path(p).stem for p in ignored_files(on_disk)}
        present = {Path(p).stem for p in on_disk}
        _MODULE_STATE = {"countable": (tracked | present) - ignored,
                         "untracked": present - ignored - tracked}
    return _MODULE_STATE


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
    spec_authority: dict[str, dict[str, str]] = {}
    naming_ack: dict[str, dict[str, str]] = {}
    section = None      # skip_tags|keep_endpoints|spec_authority|naming_ack|None
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
        elif section == "spec_authority":
            if stripped.endswith(":") and indent == 2:
                subkey = stripped.rstrip(":").strip().strip('"').strip("'")
                spec_authority.setdefault(subkey, {})
            elif indent >= 4 and ":" in stripped and subkey:
                k, _, v = stripped.partition(":")
                spec_authority[subkey][k.strip()] = v.strip().strip('"').strip("'")
        elif section == "naming_ack":
            # same two-level shape as spec_authority: a quoted
            # "<kind> <METHOD> <path>" key, then command/severity beneath it.
            if stripped.endswith(":") and indent == 2:
                subkey = stripped.rstrip(":").strip().strip('"').strip("'")
                naming_ack.setdefault(subkey, {})
            elif indent >= 4 and ":" in stripped and subkey:
                k, _, v = stripped.partition(":")
                naming_ack[subkey][k.strip()] = v.strip().strip('"').strip("'")
    return {"skip_tags": skip_tags, "skip_reasons": skip_reasons,
            "keep_endpoints": keep_endpoints, "spec_authority": spec_authority,
            "naming_ack": naming_ack}


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
    """Registered group name -> module name (manifest + hand-written + aliases).

    The hand-written seams and the aliases used to be scraped out of main.py by
    matching literal `app.add_typer(...)` calls. Lazy-loading (2026-07-27) moved
    every one of those calls into commands/_lazy.py, where they are now declared
    as DATA — `HAND_WRITTEN_GROUPS` / `ALIASES` — and mounted on demand.

    Reading the declarations instead of the call sites is both the fix and the
    better parse: a list of tuples cannot drift from the mounting order the way
    a regex over call syntax can. Scraping call sites is what made this break —
    the gate went blind to 5 groups and 3 aliases and invented 274 dead
    references, while `wxcli configure` worked perfectly the whole time.
    """
    groups = {}
    registry = COMMANDS_DIR / "_registry.py"
    if registry.exists():
        for mod, grp in re.findall(r'\("(\w+)", "([\w-]+)"\)', registry.read_text()):
            groups[grp] = mod
    lazy = COMMANDS_DIR / "_lazy.py"
    src = lazy.read_text() if lazy.exists() else MAIN_PY.read_text()

    def _pairs(block: str) -> list[tuple[str, str]]:
        m = re.search(rf"^{block}\s*=\s*\[(.*?)^\]", src, re.S | re.M)
        return re.findall(r'\("([\w-]+)",\s*"([\w-]+)"\)', m.group(1)) if m else []

    for module, group in _pairs("HAND_WRITTEN_GROUPS"):
        groups[group] = module
    # An alias is a second top-level name for an already-registered group,
    # sharing the same Typer app — so it resolves to the same module.
    for base, alias in _pairs("ALIASES"):
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


def _command_name(node: ast.FunctionDef) -> str | None:
    """Command name from an @app.command(...) decorator, or None if undecorated."""
    for deco in node.decorator_list:
        call = deco if isinstance(deco, ast.Call) else None
        func = call.func if call else deco
        if not (isinstance(func, ast.Attribute) and func.attr == "command"):
            continue
        if call and call.args and isinstance(call.args[0], ast.Constant):
            return call.args[0].value
        for kw in (call.keywords if call else []):
            if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                return kw.value.value
        return node.name.replace("_", "-")
    return None


def parse_module_flags(module: str) -> dict[str, set[str]]:
    """Parse a command module with ast: command name -> accepted flags.

    ast rather than the regex used by parse_module_commands: flag decls sit in
    help-string company (escaped quotes, "):" inside prose) that desyncs naive
    quote matching, and only the parse tree distinguishes typer.Option (a flag)
    from typer.Argument (positional — citing it as --flag is the bug this check
    exists to catch).
    """
    path = COMMANDS_DIR / f"{module}.py"
    if not path.exists():
        return {}
    out: dict[str, set[str]] = {}
    for node in ast.walk(ast.parse(path.read_text())):
        if not isinstance(node, ast.FunctionDef):
            continue
        name = _command_name(node)
        if name is None:
            continue
        flags = {"--help"}  # typer adds it to every command
        for default in node.args.defaults + list(node.args.kw_defaults):
            if not (isinstance(default, ast.Call)
                    and isinstance(default.func, ast.Attribute)
                    and default.func.attr == "Option"):
                continue
            # typer.Option(default, "--flag", "-f", ...) — args[0] is the
            # default value; every later positional string is a param decl.
            for arg in default.args[1:]:
                if not (isinstance(arg, ast.Constant) and isinstance(arg.value, str)):
                    continue
                # boolean pairs declare both names at once: "--x/--no-x"
                flags.update(p for p in arg.value.split("/") if p.startswith("-"))
        out.setdefault(name, set()).update(flags)
    return out


def build_flag_surface() -> dict[str, dict[str, set[str]]]:
    """{group: {command: {flags}}} for countable modules — mirrors build_cli_surface."""
    countable = module_state()["countable"]
    surface = {}
    for group, module in parse_registrations().items():
        if module not in countable:
            continue
        surface[group] = parse_module_flags(module)
    if "converged-recordings" in surface:
        surface["converged-recordings"].update(
            parse_module_flags("converged_recordings_export"))
    return surface


def build_cli_surface() -> tuple[dict, set[str]]:
    """Return ({group: {command: [(METHOD, path)]}} for countable modules,
    top-level command names from main.py)."""
    countable = module_state()["countable"]
    surface = {}
    for group, module in parse_registrations().items():
        if module not in countable:
            continue  # gitignored dev-only (fs_*) — absent on a fresh clone
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
    """Distinct countable command modules behind the registered groups.

    Aliases (cx-essentials, users, licenses-api) mount an existing module under
    a second name — the same commands, not a separate command set. Published
    "N command groups" claims count command sets, so aliases are excluded.
    """
    countable = module_state()["countable"]
    return len({m for m in parse_registrations().values() if m in countable})


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

# A citation that omits the literal `wxcli`. Skill quick-reference tables drop
# the prefix routinely (`| Get cluster details | `video-mesh show CLUSTER_ID` |`),
# and every check keyed on TOKEN/FLAG_CMD was blind to all of them: measured on
# this repo, 639 such spans head a registered group, 14 named a command that
# does not exist, and check 2 reported 0.
#
# Two restrictions keep this out of English prose, and both are load-bearing:
#   * anchored at the START of the span — `people list` mid-sentence is not a
#     citation, and 1232 spans match the shape while only 639 head a group;
#   * the second token must end on a word boundary, so the slash-notation
#     `emergency-services show/create/update` is prose, not a 1-argument
#     invocation of `show` (that exact span was this rule's only false
#     positive across the whole doc set).
# The caller adds the third: the first token must be a REGISTERED GROUP.
PREFIXLESS_HEAD = re.compile(
    r"^([a-z0-9][a-z0-9_-]*)[ \t]+([a-z0-9][a-z0-9_-]*)(?=[ \t]|$)")


def command_heads(span: str):
    """Yield (group, command|None, rest_text, prefixless) for each command head.

    One reader for every check that parses a documented invocation, so a
    citation is either visible to all of them or to none. Callers get the
    remaining argument text directly rather than an offset, because the
    prefixless match runs against a left-stripped copy and the two offset
    spaces would not line up.
    """
    for m in TOKEN.finditer(span):
        yield m.group(1), m.group(2), span[m.end():], False
    s = span.lstrip()
    if s.startswith("wxcli"):
        return  # already yielded above, in its canonical form
    m = PREFIXLESS_HEAD.match(s)
    if m:
        yield m.group(1), m.group(2), s[m.end():], True


def _quote_open(s: str) -> str | None:
    """Scan `s` from a clean start and return the quote char still open at the
    end, or None if every '/" is balanced. Ported from d1-positionals/
    detector.py's slice_invocation: a `"` inside an open `'...'` (and vice
    versa) does not count, and a backslash inside a double-quoted string
    escapes the next char rather than ending it."""
    quote = None
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if quote:
            if c == quote:
                quote = None
            elif c == "\\" and quote == '"' and i + 1 < n:
                i += 1
        elif c in "'\"":
            quote = c
        i += 1
    return quote


def code_spans(text: str, join_continuations: bool = False,
               join_quotes: bool = False, with_kind: bool = False):
    """Yield (line_number, span_text) for fenced blocks and inline code, or
    (line_number, span_text, in_fenced_block) when with_kind=True.

    join_continuations merges shell line-continuations into one span, reported
    at the first line. Check 6 needs it (a flag wrapped onto a `\\` line still
    belongs to the command above it); check 2 leaves it off, since the
    `wxcli <group> <command>` head it reads is always on the first line.

    join_quotes is check 10's addition: it also keeps buffering across a
    newline that falls INSIDE an open quote, e.g. a multi-line `--json-body
    '{ ... }'` block. Without it, a line-at-a-time reader ends the span at the
    unterminated `'{` and the invocation becomes untokenizable — measured on
    this repo's docs, 14 of check 10's 85 real findings sit inside exactly
    this shape and were silently dropped before this was added. check 6/7
    leave it off (default False) to keep their existing, already-tuned
    behaviour unchanged.

    with_kind is check 10's other addition: a bare `wxcli grp cmd` with zero
    arguments means something different depending on where it sits — a fenced
    block reads as a runnable example missing a required arg (actionable), an
    inline backtick reads as a reference-table mention (not actionable) — and
    no earlier caller needed that distinction, so it defaults off and leaves
    checks 2/6's 2-tuple unpacking untouched.
    """
    def _yield(lineno, span, fenced):
        return (lineno, span, fenced) if with_kind else (lineno, span)

    fence_open = None
    pending, pending_line = None, None
    for lineno, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            fence_open = None if fence_open else lineno
            if pending is not None:  # unterminated continuation at fence close
                yield _yield(pending_line, pending, True)
                pending, pending_line = None, None
            continue
        if fence_open:
            if line.lstrip().startswith("#"):  # shell comments are prose
                continue
            if not join_continuations:
                yield _yield(lineno, line, True)
                continue
            if pending is None:
                pending, pending_line = line.rstrip(), lineno
            else:
                pending += " " + line.strip()
            # `cmd --flag x \    # what this does` is a real continuation whose
            # `\` is not the last character. Recognising only a literal trailing
            # `\` ends the span here and hides every flag on the wrapped lines:
            # measured, README.md's `wxcli cucm report --brand ... \  # comment`
            # supplies --prepared-by on the NEXT line, and check 11a reported it
            # as missing. Only a comment introduced AFTER whitespace following
            # the backslash is stripped, so a `#` inside a quoted value is
            # untouched.
            pending = re.sub(r"\\[ \t]+#.*$", "\\\\", pending)
            if pending.endswith("\\"):
                pending = pending[:-1]
                continue
            # "wxcli" in pending: an apostrophe in unrelated PROSE sharing the
            # fence (e.g. "the user's inputs") opens a quote that never
            # closes and would otherwise swallow every following line up to
            # fence-close. Anchoring on "wxcli" restricts continuation to
            # buffers that already are a command line, matching the
            # detector's approach of re-starting quote-tracking at each
            # invocation rather than at the start of the fenced block.
            if (join_quotes and "wxcli" in pending
                    and _quote_open(pending) is not None):
                continue  # still inside an open quote — keep buffering
            yield _yield(pending_line, pending, True)
            pending, pending_line = None, None
        else:
            for span in re.findall(r"`([^`]+)`", line):
                yield _yield(lineno, span, False)
    if pending is not None:
        yield _yield(pending_line, pending, True)


def load_allowlist() -> set[str]:
    if not ALLOWLIST.exists():
        return set()
    return {line.strip() for line in ALLOWLIST.read_text().splitlines()
            if line.strip() and not line.startswith("#")}


def check_references(surface: dict, top_level: set[str]) -> tuple[list, dict, int]:
    """Validate wxcli tokens in code spans; also collect group reference counts.

    Returns (dead, group_refs, prefixless_subtotal). A dead command name is dead
    whether or not the doc wrote `wxcli` in front of it, so prefixless hits join
    the same failing list — but they are counted separately and printed on the
    check-2 line, so the widening stays visible instead of silently changing
    what a passing gate means.
    """
    dead, group_refs = [], {g: 0 for g in surface}
    prefixless = 0
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
            for group, command, _rest, no_prefix in command_heads(span):
                entry = f"{group} {command}" if command else group
                if no_prefix:
                    # the anti-prose guard: only a REGISTERED group may head a
                    # prefixless citation. Without it, 639 candidate spans
                    # become 1232 and ordinary English joins the findings.
                    if group not in surface:
                        continue
                elif PLACEHOLDER.search(f"wxcli {entry}"):
                    continue
                if group[-1] in "-_" or (command and command[-1] in "-_"):
                    continue  # truncated placeholder like `wxcli cc-<group>`
                # Bare "<group>"/"<group> <command>" exempt everywhere (a real
                # English-prose false positive, e.g. "wxcli commands", reads
                # the same way in any file). "ref <file> <group|entry>" scopes
                # an exemption to the ONE file that has a documented reason for
                # it — needed because a bare group entry silences that group
                # in every file, including ones where the same name is a real,
                # unrelated dead reference (found live: `user-call-settings`
                # exempted here for a deliberate negative example in
                # manage-devices/SKILL.md also hid 6 real dead refs in
                # person-call-settings-behavior.md).
                if (entry in allow or group in allow
                        or f"ref {rel} {group}" in allow
                        or f"ref {rel} {entry}" in allow):
                    continue
                if group in top_level:
                    continue
                if group not in surface:
                    kind = "group"
                elif command and command not in surface[group]:
                    kind = "command"
                else:
                    continue
                # A dead GROUP is reported as the group alone — the command name
                # is noise when the group it lives in does not exist. `ref`
                # otherwise shows the citation AS WRITTEN: printing a `wxcli`
                # the doc never had sends the reader grepping for a string that
                # is not there.
                cited = group if kind == "group" else entry
                dead.append({"file": rel, "line": lineno, "kind": kind,
                             "prefixless": no_prefix,
                             "ref": cited if no_prefix else f"wxcli {cited}"})
                prefixless += no_prefix
    return dead, group_refs, prefixless


# ------------------------------------------------------------------ check 3

# Three claim shapes, spelled out rather than collapsed into one loose regex.
# The original harvester was `(\d+)\s+command groups`, which can match only the
# first of them: "176 CLI command groups" has a word between the number and
# `command`, and "176 groups" has no `command` at all. README shipped 178 and
# 176 simultaneously and check 3 reported a confident 0 over both.
#
#   "178 command groups"      GROUP_CLAIM
#   "178 CLI command groups"  GROUP_CLAIM, one qualifier word
#   "178 groups"              BARE_GROUP_CLAIM, CLI context required
GROUP_CLAIM = re.compile(r"(\d+)\s+(?:[A-Za-z][A-Za-z-]*\s+)?command\s+groups\b")
BARE_GROUP_CLAIM = re.compile(r"(\d+)\s+groups\b")
SPEC_CLAIM = re.compile(r"(\d+)\s+OpenAPI(?:\s+3\.0)?\s+specs?\b")

# The bare form is the one that can pick up ordinary prose ("3 groups of
# users"), so it counts only on a line that already names the thing being
# counted. Both live citations qualify: "| **CLI** (178 groups) |" and "Run
# `wxcli --help` to see all 178 groups". The rule is LINE-scoped rather than a
# character window on purpose — a window is a magic number nobody can
# re-derive, a line is the unit the sentence is written in.
#
# The residual false positive is real and was measured, not assumed: a line
# reading "The CLI is used by 3 groups of users" DOES fire, while the same
# sentence without `CLI` does not. Neither published file contains such a line
# today, and the trade is deliberate — the alternative is the blind spot that
# let README ship two different numbers. If one is ever written, rephrase the
# prose or say "command groups"; do not loosen this rule.
CLI_CONTEXT = re.compile(r"\bwxcli\b|\bCLI\b")


def harvest_count_claims() -> list[dict]:
    """Every published count claim in CLAUDE.md + README.md, with its line.

    Scoped to those two files ONLY — they are what a reader outside the repo
    sees, and narrow scope is what makes the bare `N groups` form affordable.
    Every claim is kept individually (not deduplicated to a set of values) so
    both oracles in check_counts can name the file and line of each side.
    """
    claims = []
    for rel in ("CLAUDE.md", "README.md"):
        for lineno, line in enumerate((REPO / rel).read_text().splitlines(), 1):
            found = [(m, "command groups") for m in GROUP_CLAIM.finditer(line)]
            if CLI_CONTEXT.search(line):
                found += [(m, "command groups")
                          for m in BARE_GROUP_CLAIM.finditer(line)]
            found += [(m, "OpenAPI specs") for m in SPEC_CLAIM.finditer(line)]
            for m, kind in found:
                claims.append({"kind": kind, "file": rel, "line": lineno,
                               "value": int(m.group(1)), "text": m.group(0)})
    return claims


def check_counts(surface: dict) -> list:
    measured = {"command groups": distinct_command_sets(),
                "OpenAPI specs": len(tracked_specs())}
    claims = harvest_count_claims()
    mismatches = [
        {"file": c["file"], "line": c["line"], "claim": c["text"],
         "measured": measured[c["kind"]]}
        for c in claims if c["value"] != measured[c["kind"]]
    ]
    # Second, INDEPENDENT oracle: the published files disagreeing with each
    # OTHER is a defect whichever side is right. It does not consult `measured`
    # at all, so it still fires when the measurement itself is wrong — and a
    # self-contradiction is the shape a partially-blind harvester produces, so
    # this is the oracle that would have caught the 178/176 split even if the
    # widened patterns above had missed a fourth phrasing.
    for kind in ("command groups", "OpenAPI specs"):
        values = sorted({c["value"] for c in claims if c["kind"] == kind})
        if len(values) > 1:
            mismatches.append({
                "file": "CLAUDE.md + README.md", "line": 0,
                "claim": f"{kind} claimed as "
                         + " and ".join(str(v) for v in values),
                "measured": measured[kind],
                "contradiction": "; ".join(
                    f"{v} at " + ", ".join(f"{c['file']}:{c['line']}"
                                           for c in claims
                                           if c["kind"] == kind
                                           and c["value"] == v)
                    for v in values),
            })
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


# ------------------------------------------------------------------ check 6

# two literal words: a truncated head (`wxcli cc-<group> list`) cannot match,
# which is how check 6 stays out of check 2's territory without PLACEHOLDER.
FLAG_CMD = re.compile(r"wxcli\s+([a-z0-9][a-z0-9_-]*)\s+([a-z0-9][a-z0-9_-]*)")
FLAG_CITE = re.compile(r"(?<![\w=/-])(--[a-z0-9][a-z0-9-]*|-[a-zA-Z])(?![\w-])")


def arg_region(rest: str, strip_comment: bool = False) -> str:
    """The argument text belonging to this command — stop at a shell pipe,
    redirect, or chain, so flags past a `|` are not blamed on this command.

    `>` only ends the region OUTSIDE an angle-bracket placeholder: examples are
    written `--location-id <loc_id> --paging-id <pg_id>`, so treating the `>` of
    `<loc_id>` as a redirect would truncate the line and silently skip every
    flag after the first placeholder — which is most of them.

    strip_comment additionally stops at a `# trailing shell comment` (a `#`
    preceded by whitespace). Check 6 never needed this — its FLAG_CITE regex
    only matches `--flag`-shaped tokens, which a prose comment never is — but
    check 10 tokenizes and counts EVERY remaining word, so `wxcli locations
    list  # Get location IDs` without this became 4 phantom positionals on a
    zero-arg command. Off by default so check 6's tuned behaviour is
    untouched; check 10 passes strip_comment=True.
    """
    depth, quote = 0, None
    for i, ch in enumerate(rest):
        if quote:
            if ch == quote:
                quote = None
            continue
        if ch in "'\"":
            quote = ch
        elif ch == "<":
            depth += 1
        elif ch == ">":
            if depth:
                depth -= 1
            else:
                # Drop a file-descriptor digit immediately before the redirect:
                # `2>&1` would otherwise leave a bare `2`, which shlex reads as
                # its own word and check 10 counts as a phantom positional. It
                # hit EVERY line ending `2>&1` regardless of the real arguments
                # — 15 of teardown/SKILL.md's 16 findings were this artifact and
                # nothing else, on lines whose documented arguments were already
                # correct. Only a lone digit is stripped, so a real trailing
                # argument ending in a digit (`... SITE2 > out`) is untouched.
                end = i
                if end and rest[end - 1].isdigit() and (
                        end == 1 or not rest[end - 2].strip()):
                    end -= 1
                return rest[:end]
        elif ch in "|;" or rest.startswith("&&", i) or rest.startswith("$(", i):
            return rest[:i]
        elif strip_comment and ch == "#" and i > 0 and rest[i - 1].isspace():
            return rest[:i]
    return rest


def check_flags(surface: dict, flag_surface: dict) -> list:
    """Flags cited against a command that does not accept them.

    Deliberately does NOT skip PLACEHOLDER spans the way check 2 does:
    `--location-id <loc_id>` is the shape a copy-pasteable example takes, so
    skipping placeholders would blind this check to exactly the citations most
    likely to be typed.
    """
    dead = []
    allow = load_allowlist()
    for rel in sorted(f for pat in SCAN_PATTERNS for f in tracked_files(pat)
                      if f.endswith(".md")):
        text = (REPO / rel).read_text()
        for lineno, span in code_spans(text, join_continuations=True):
            for m in FLAG_CMD.finditer(span):
                group, command = m.group(1), m.group(2)
                if group in allow or f"{group} {command}" in allow:
                    continue
                if group not in surface or command not in surface[group]:
                    continue  # check 2 owns names that don't resolve
                real = flag_surface.get(group, {}).get(command)
                if real is None:
                    continue  # a mounted sub-typer, not a leaf command
                rest = arg_region(span[m.end():])
                nxt = rest.find("wxcli")
                if nxt != -1:
                    rest = rest[:nxt]
                for fm in FLAG_CITE.finditer(rest):
                    flag = fm.group(1)
                    if flag in real or f"{group} {command} {flag}" in allow:
                        continue
                    dead.append({"file": rel, "line": lineno,
                                 "ref": f"wxcli {group} {command}", "flag": flag})
    return dead


# ------------------------------------------------------------------ check 7

# The backticks must wrap the flag AND NOTHING ELSE. That is what keeps this
# check out of check 6's territory: `wxcli people create --license` is a command
# span and belongs to check 6, while `--license` alone is a prose citation and
# belongs here. It also drops `curl --header`-style spans, where the flag is a
# different tool's and the backticks wrap the whole invocation.
PROSE_FLAG = re.compile(r"`(--[a-z0-9][a-z0-9-]+)`")


def check_prose_flags(flag_surface: dict) -> list:
    """Backticked flags that exist on NO wxcli command anywhere.

    Check 6 can only judge a flag that trails a resolvable `wxcli <group>
    <command>` in a code span. A flag named in a sentence or a table cell has no
    command in front of it, so check 6 is blind to it by design. This check is
    the command-free complement, and it is deliberately weaker: with no command
    to check against, it can only say "no such flag anywhere", never "real flag,
    wrong command". A citation like `--media-type` on `cc-ewt show` (real on
    cc-tasks create, fiction there) passes this check and always will.

    It also cannot tell "use `--x`" from "there is NO `--x`". The repo documents
    several non-existent flags on purpose, to stop an agent reaching for one;
    those lines are some of the best docs here and a check that pressured
    someone into deleting them would make the playbook worse. They are
    allowlisted per file as `prose-flag <path> <flag>`.
    """
    real = {f for cmds in flag_surface.values() for fl in cmds.values() for f in fl}
    allow = load_allowlist()
    dead = []
    for rel in sorted(f for pat in SCAN_PATTERNS for f in tracked_files(pat)
                      if f.endswith(".md")):
        for lineno, line in enumerate((REPO / rel).read_text().splitlines(), 1):
            for m in PROSE_FLAG.finditer(line):
                flag = m.group(1)
                if flag in real or f"prose-flag {rel} {flag}" in allow:
                    continue
                dead.append({"file": rel, "line": lineno, "flag": flag})
    return dead


# ------------------------------------------------------------------ check 8

def check_untracked_modules() -> list:
    """Command modules on disk and not gitignored, but never `git add`ed.

    Its own check, not part of check 1: the generator did its job, so reporting
    these as "spec->CLI missing" blames the wrong thing and invites someone to
    skip-list an endpoint whose command already exists. A fresh clone still
    would not have the file, and main.py imports every _registry.py manifest
    entry unguarded, so a committed manifest entry with an uncommitted module
    breaks the CLI at import for everyone else.
    """
    registered = set(parse_registrations().values())
    return [{"module": m, "registered": m in registered}
            for m in sorted(module_state()["untracked"])]


# ------------------------------------------------------------------ check 9

# A dict or list never renders as a useful table cell (output.py's auto_columns
# skips them for the same reason), so only these can be a column.
SCALAR_TYPES = {"string", "integer", "number", "boolean"}


def _resolve_schema(spec: dict, schema, depth: int = 0) -> dict:
    """Resolve $ref / allOf / oneOf / anyOf into one schema dict."""
    if not isinstance(schema, dict) or depth > 8:
        return {}
    if "$ref" in schema:
        node = spec
        for part in schema["$ref"].lstrip("#/").split("/"):
            node = node.get(part, {}) if isinstance(node, dict) else {}
        return _resolve_schema(spec, node, depth + 1)
    for key in ("allOf", "oneOf", "anyOf"):
        if key not in schema:
            continue
        merged: dict = {}
        for sub in schema[key]:
            merged.update(_resolve_schema(spec, sub, depth + 1).get("properties", {}))
        out = {k: v for k, v in schema.items() if k != key}
        merged.update(out.get("properties", {}))
        out["properties"] = merged
        out.setdefault("type", "object")
        return out
    return schema


def spec_item_fields() -> dict:
    """{(METHOD, norm_path): {extraction key: {spec: {field: type}}}} — per spec.

    Provenance is kept rather than unioned. 60 operations declare a list-item
    schema in more than one tracked spec, and for 7 of them the specs disagree
    about the fields. Unioning made a column only one spec declared look valid
    no matter which spec the command was rendered from, which is how a live-
    broken `locations list` sat behind a passing gate: webex-device.json claims
    /locations returns displayName/locationId/countryCode, the live endpoint
    returns none of them, and the union let all three through.

    Collapsing happens later in `resolve_item_fields`, which consults the
    `spec_authority` overrides so the choice is declared instead of implicit.
    """
    out: dict[tuple[str, str], dict[str, dict[str, dict[str, str]]]] = {}
    for rel in sorted(tracked_specs()):
        spec = json.loads((REPO / rel).read_text())
        spec = merge_overlay(spec, load_overlay(REPO / rel))
        for path, methods in spec.get("paths", {}).items():
            for method, op in methods.items():
                if method.lower() not in HTTP_METHODS or not isinstance(op, dict):
                    continue
                content = op.get("responses", {}).get("200", {}).get("content", {})
                js = (content.get("application/json")
                      or content.get("application/json;charset=UTF-8") or {})
                schema = _resolve_schema(spec, js.get("schema"))
                if not schema:
                    continue
                by_key = out.setdefault((method.upper(), normalize_path(path)), {})
                arrays = ([("items", schema)] if schema.get("type") == "array"
                          else [(n, _resolve_schema(spec, p))
                                for n, p in schema.get("properties", {}).items()])
                for name, prop in arrays:
                    if prop.get("type") != "array" and "items" not in prop:
                        continue
                    item = _resolve_schema(spec, prop.get("items", {}))
                    fields = {f: _resolve_schema(spec, s).get("type", "string")
                              for f, s in item.get("properties", {}).items()}
                    if fields:
                        by_key.setdefault(name, {})[Path(rel).name] = fields
    return out


def resolve_item_fields(by_spec: dict, op_key: str,
                        authority: dict) -> tuple[dict, str | None]:
    """Collapse per-spec item fields into the one schema check 9 validates against.

    Returns (fields, unpinned_reason). A non-None reason means the specs
    disagree and no `spec_authority` entry decides between them — that is a
    gate failure in its own right, because any answer given would be a guess.

    `live_fields` on the entry are folded in afterwards: a spec can under-declare
    a real response, and a column proven live must not be failed for it.
    """
    pin = authority.get(op_key) or {}
    extra = _parse_live_fields(pin.get("live_fields", ""))
    if len(by_spec) == 1:
        return {**next(iter(by_spec.values())), **extra}, None
    sets = [set(f) for f in by_spec.values()]
    if set().union(*sets) == set.intersection(*sets):
        return {**next(iter(by_spec.values())), **extra}, None  # agree; nothing to decide
    if not pin:
        return {}, (f"{len(by_spec)} specs disagree "
                    f"({', '.join(sorted(by_spec))}) and no spec_authority entry "
                    f"decides between them")
    chosen = pin.get("spec", "union")
    if chosen == "union":
        merged: dict = {}
        for f in by_spec.values():
            merged.update(f)
        return {**merged, **extra}, None
    if chosen not in by_spec:
        return {}, (f"spec_authority names {chosen}, which declares no item "
                    f"schema for this operation (have: {', '.join(sorted(by_spec))})")
    return {**by_spec[chosen], **extra}, None


def _parse_live_fields(raw: str) -> dict[str, str]:
    """"orgId:string, address:object" -> {"orgId": "string", "address": "object"}."""
    out = {}
    for part in raw.split(","):
        name, _, typ = part.strip().partition(":")
        if name.strip():
            out[name.strip()] = (typ.strip() or "string")
    return out


def parse_module_columns(module: str, commands_dir: Path) -> list:
    """[(command, [(header, accessor)], extraction key, METHOD, norm_path)].

    Reads the generated file, not the generator: what an operator sees is what
    this module renders, and check 9 exists to prove those two agree.
    """
    path = commands_dir / f"{module}.py"
    if not path.exists():
        return []
    src = path.read_text()
    lines = src.splitlines()
    out = []
    for node in ast.walk(ast.parse(src)):
        if not isinstance(node, ast.FunctionDef):
            continue
        name = _command_name(node)
        if name is None:
            continue
        columns = None
        for sub in ast.walk(node):
            if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name)
                    and sub.func.id == "emit"):
                for kw in sub.keywords:
                    if kw.arg != "columns":
                        continue
                    try:
                        columns = ast.literal_eval(kw.value)
                    except ValueError:
                        columns = None
        if not columns:
            continue
        body = "\n".join(lines[node.lineno - 1:node.end_lineno])
        key = re.search(r'item_key="([^"]*)"', body) or re.search(
            r'items = result\.get\("([^"]*)"', body)
        url = re.search(r'url = f?"([^"]+)"', body)
        raw_url = url.group(1) if url else ""
        for base in URL_BASES:
            if raw_url.startswith(base):
                raw_url = raw_url[len(base):]
                break
        verb = re.search(r"rest_(get|put|post|patch|delete)\(|follow_pagination\(", body)
        method = verb.group(1).upper() if verb and verb.group(1) else "GET"
        out.append((name, columns, key.group(1) if key else "items",
                    method, normalize_path(raw_url)))
    return out


def check_table_columns(commands_dir: Path = COMMANDS_DIR,
                        authority: dict | None = None) -> tuple[list, list, list]:
    """Table columns naming a field the endpoint's 200 item schema has no room for.

    The failure is silent by design of the CLI: the command exits 0 and prints
    a table that looks fine but has blank columns, while -o json was always
    correct. 224 of 513 list commands were in this state before the renderer
    started deriving defaults from the response schema.

    Two classes are deliberately not failures, and are returned separately:
      - dotted accessors ("owner.type"), which output.py:_resolve_accessor
        legitimately supports and this check cannot follow;
      - responses whose extracted item carries no scalar field at all — the
        payload nests one level deeper than the extractor reaches (`items[]
        .items`, Video Mesh). No column list can fix those, so flagging them
        would be permanent noise; nested extraction was cut deliberately.

    A third list IS a failure: operations whose specs disagree about the item
    schema with no `spec_authority` entry to settle it. Validating against a
    guess is what this check used to do implicitly, by unioning.
    """
    fields_by_op = spec_item_fields()
    authority = authority or {}
    countable = module_state()["countable"]
    findings, wrapper_only, unpinned = [], [], []
    for group, module in sorted(parse_registrations().items()):
        seen = set()
        for cmd, columns, key, method, path in parse_module_columns(module, commands_dir):
            if module not in countable or (group, cmd) in seen:
                continue
            seen.add((group, cmd))
            by_spec = (fields_by_op.get((method, path)) or {}).get(key)
            if not by_spec:
                continue  # hand-written command, or a schema declaring nothing
            item, reason = resolve_item_fields(by_spec, f"{method} {path}", authority)
            if reason:
                unpinned.append({"group": group, "command": cmd,
                                 "op": f"{method} {path}", "reason": reason})
                continue
            if not any(t in SCALAR_TYPES for t in item.values()):
                wrapper_only.append({"group": group, "command": cmd, "path": path})
                continue
            missing = [a for _, a in columns
                       if a and "." not in a and a not in item]
            if missing:
                findings.append({
                    "group": group, "command": cmd, "path": path,
                    "missing": missing,
                    "available": sorted(f for f, t in item.items()
                                        if t in SCALAR_TYPES),
                })
    return findings, wrapper_only, unpinned


# ----------------------------------------------------------------- check 10

# Prototyped as the standalone d1-positionals detector
# (docs/superpowers/quality-loop/artifacts/detectors/d1-positionals/detector.py)
# before being promoted here. The CLI-side signature parsing below
# (_typer_call / _is_bool_annotation / parse_module_signatures) is ported
# from it near-verbatim: parse_module_flags (above) records flag NAMES only,
# and nothing in this file records typer.Argument declarations at all, but
# telling a real positional from an option's value needs both — a flag's
# take-a-value-or-not, and the ordered, required-or-not positional list.
# The doc-side scan deliberately does NOT port the detector's own
# find_invocations/slice_invocation file walker: this file's own SCAN_PATTERNS
# + tracked_files + code_spans + FLAG_CMD + arg_region (all used already by
# checks 2/6/7) cover the same ground, so check 10 reuses them instead of
# scanning a second, slightly different way.


def _typer_call(default, attr: str):
    """Return the ast.Call if `default` is typer.<attr>(...), else None."""
    if (isinstance(default, ast.Call)
            and isinstance(default.func, ast.Attribute)
            and default.func.attr == attr):
        return default
    return None


def _is_bool_annotation(ann) -> bool:
    return isinstance(ann, ast.Name) and ann.id == "bool"


def parse_module_signatures(module: str,
                            commands_dir: Path = COMMANDS_DIR) -> dict[str, dict]:
    """command -> {"args": [(name, required)], "flags": {flag: takes_value}}.

    args is the ORDERED list of typer.Argument(...) params (required unless
    declared typer.Argument(None) / default=...). flags covers every
    typer.Option(...), each marked whether it consumes a following token —
    parse_module_flags (above) already answers "does this flag exist" for
    check 6; this answers "does citing it eat the next positional".

    commands_dir defaults to the real tree; tests override it the same way
    parse_module_columns (check 9) does, to probe a throwaway module without
    writing into src/wxcli/commands/.
    """
    path = commands_dir / f"{module}.py"
    if not path.exists():
        return {}
    out: dict[str, dict] = {}
    for node in ast.walk(ast.parse(path.read_text())):
        if not isinstance(node, ast.FunctionDef):
            continue
        name = _command_name(node)
        if name is None:
            continue
        params = node.args.args + node.args.kwonlyargs
        defaults = ([None] * (len(node.args.args) - len(node.args.defaults))
                    + list(node.args.defaults) + list(node.args.kw_defaults))
        args: list[tuple[str, bool]] = []
        flags: dict[str, bool] = {"--help": False}
        for param, default in zip(params, defaults):
            arg_call = _typer_call(default, "Argument")
            if arg_call is not None:
                # typer.Argument(...)  -> required (Ellipsis or no default)
                # typer.Argument(None) -> optional
                required = True
                if arg_call.args and isinstance(arg_call.args[0], ast.Constant):
                    if arg_call.args[0].value is None:
                        required = False
                for kw in arg_call.keywords:
                    if kw.arg == "default" and isinstance(kw.value, ast.Constant):
                        required = kw.value.value is ...
                args.append((param.arg, required))
                continue
            opt_call = _typer_call(default, "Option")
            if opt_call is None:
                continue
            takes_value = not _is_bool_annotation(param.annotation)
            names = [p for a in opt_call.args[1:]
                     if isinstance(a, ast.Constant) and isinstance(a.value, str)
                     for p in a.value.split("/") if p.startswith("-")]
            if not names:  # typer derives --param-name when none declared
                names = ["--" + param.arg.replace("_", "-")]
            for f in names:
                flags[f] = takes_value
        rec = out.setdefault(name, {"args": args, "flags": {}})
        if not rec["args"] and args:
            rec["args"] = args
        rec["flags"].update(flags)
    return out


def build_positional_surface() -> dict[str, dict[str, dict]]:
    """{group: {command: {"args": ..., "flags": ...}}} for countable modules —
    mirrors build_flag_surface, adding the positional side."""
    countable = module_state()["countable"]
    surface = {}
    for group, module in parse_registrations().items():
        if module not in countable:
            continue
        surface[group] = parse_module_signatures(module)
    if "converged-recordings" in surface:
        surface["converged-recordings"].update(
            parse_module_signatures("converged_recordings_export"))
    return surface


def global_bool_flags(positional_surface: dict) -> set[str]:
    """Flags declared bool ANYWHERE. Used only when a documented flag is not
    declared on the command being cited, so an unknown --force/--debug does
    not eat the following positional and get mistaken for consuming it."""
    bools: set[str] = set()
    for cmds in positional_surface.values():
        for rec in cmds.values():
            for f, takes in rec.get("flags", {}).items():
                if not takes:
                    bools.add(f)
    return bools


def split_doc_positionals(tokens: list[str], flags: dict[str, bool],
                          global_bools: set[str]) -> tuple[list[str], bool, bool]:
    """Return (positional tokens, saw_ellipsis, unbalanced_brackets).

    `[OPTIONS]` / `[--include-audio]` / `[-d OUTPUT_DIR]` are usage-synopsis
    notation, not supplied arguments — dropped rather than treated as
    positionals. An opening bracket with no closer (a synopsis truncated at a
    `|`, e.g. `[--format jsonl|json-per-file]`) means the whole example is
    notation, not a runnable invocation — the caller skips it entirely.
    """
    positionals: list[str] = []
    ellipsis = unbalanced = False
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in ("...", "…"):
            ellipsis = True
            i += 1
            continue
        if t.startswith("[") or t.endswith("]"):
            if t.startswith("[") and not t.endswith("]"):
                unbalanced = True
            i += 1
            continue
        if t.startswith("--") or (len(t) > 1 and t.startswith("-")
                                  and not t[1:].replace(".", "").isdigit()):
            name = t.split("=", 1)[0]
            has_inline = "=" in t
            if name in flags:
                takes = flags[name]
            elif name in global_bools:
                takes = False
            else:
                takes = True  # convention: an unknown long flag takes a value
            if takes and not has_inline:
                if i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
                    i += 2
                    continue
            i += 1
            continue
        positionals.append(t)
        i += 1
    return positionals, ellipsis, unbalanced


# ---------------------------------------------------------------- check 11a

def parse_module_required_options(
        module: str, commands_dir: Path = COMMANDS_DIR) -> dict[str, list[set]]:
    """command -> [{every spelling of a REQUIRED option}].

    Required means `typer.Option(...)` — Ellipsis as the default. Click enforces
    these at PARSE time, so an example omitting one aborts before the command
    runs, exactly like a missing positional.

    Read the RENDERED command, never the spec. `auto_inject_from_config`
    (tools/field_overrides.yaml) supplies orgId from saved config, so a
    parameter the spec marks required is legitimately absent from --help; a
    spec-driven version of this check would report every one of those as a
    missing flag. Measured on this tree: 0 of 158 required options are
    request-body fields — all are query or path parameters — so `--json-body`
    never substitutes for one, and neither does `--generate-json-body`, which
    Click never reaches until after it has enforced them.
    """
    path = commands_dir / f"{module}.py"
    if not path.exists():
        return {}
    out: dict[str, list[set]] = {}
    for node in ast.walk(ast.parse(path.read_text())):
        if not isinstance(node, ast.FunctionDef):
            continue
        name = _command_name(node)
        if name is None:
            continue
        params = node.args.args + node.args.kwonlyargs
        defaults = ([None] * (len(node.args.args) - len(node.args.defaults))
                    + list(node.args.defaults) + list(node.args.kw_defaults))
        required: list[set] = []
        for param, default in zip(params, defaults):
            call = _typer_call(default, "Option")
            if call is None:
                continue
            if not (call.args and isinstance(call.args[0], ast.Constant)
                    and call.args[0].value is ...):
                continue
            names = {p for a in call.args[1:]
                     if isinstance(a, ast.Constant) and isinstance(a.value, str)
                     for p in a.value.split("/") if p.startswith("-")}
            required.append(names or {"--" + param.arg.replace("_", "-")})
        out.setdefault(name, required)
    return out


def build_required_surface() -> dict[str, dict[str, list[set]]]:
    """{group: {command: [{option spellings}]}} — mirrors build_positional_surface."""
    countable = module_state()["countable"]
    surface = {}
    for group, module in parse_registrations().items():
        if module not in countable:
            continue
        surface[group] = parse_module_required_options(module)
    if "converged-recordings" in surface:
        surface["converged-recordings"].update(
            parse_module_required_options("converged_recordings_export"))
    return surface


def check_required_flags(surface: dict, positional_surface: dict,
                         required_surface: dict) -> tuple[list, int]:
    """Documented examples that omit an option the command declares REQUIRED.

    Check 10 counts positionals only, so an example can have the right argument
    count and still abort: `wxcli video-mesh show CLUSTER_ID --output json`
    supplies the one positional `show` declares and still dies on the missing
    `--from`/`--to`. The generated docstring's own Example line already gets
    this right, which makes the CLI its own oracle here.

    Only a FENCED example fails. An inline single-backtick citation is a
    reference-table entry naming a variant rather than an invocation — measured
    here, `wxcli xapi list --command` and `wxcli xapi list --status` sit in a
    decision-matrix cell whose whole job is to contrast the two flags, and
    demanding `--device-id` there would force a runnable command into a table
    that is not offering one. Flags mentioned in prose are check 7's territory,
    not this one. Inline hits are counted and printed, never failed.
    """
    findings: list[dict] = []
    bare_count = 0
    allow = load_allowlist()
    for inv in doc_invocations(surface, positional_surface):
        rel, group, command = inv["file"], inv["group"], inv["command"]
        required = required_surface.get(group, {}).get(command)
        if not required:
            continue
        if (group in allow or f"{group} {command}" in allow
                or f"required-flag {rel} {group} {command}" in allow):
            continue
        tokens = inv["tokens"]
        if "--help" in tokens:
            continue  # eager: Click prints help before enforcing anything
        if any(t in ("...", "…") for t in tokens):
            continue  # explicitly elided
        cited = {t.split("=", 1)[0] for t in tokens if t.startswith("-")}
        missing = [sorted(names)[0] for names in required if not (names & cited)]
        if not missing:
            continue
        if not inv["in_code"]:
            bare_count += 1
            continue
        findings.append({
            "file": rel, "line": inv["line"], "cmd": f"{group} {command}",
            "missing": missing, "prefixless": inv["prefixless"],
        })
    return findings, bare_count


def doc_invocations(surface: dict, positional_surface: dict):
    """Yield every documented invocation that resolves to a real leaf command.

    Each item: {file, line, group, command, tokens, in_code, prefixless, sig}.
    Checks 10 and 11 both consume this so a citation is parsed exactly once and
    the same way. The token-level corrections below each cost a debugging
    session to find (see tools/CLAUDE.md § "Check 10"); duplicating the walk per
    check is how they come back on one check and not the other.

    Unresolved names are check 2's job and are skipped, exactly as check 6 skips
    them; a name mounted as a sub-typer (cucm's nested `config`) rather than a
    leaf command is skipped the same way (sig is None).
    """
    for rel in sorted(f for pat in SCAN_PATTERNS for f in tracked_files(pat)
                      if f.endswith(".md")):
        text = (REPO / rel).read_text()
        for lineno, span, in_code in code_spans(text, join_continuations=True,
                                                join_quotes=True, with_kind=True):
            for group, command, head_rest, no_prefix in command_heads(span):
                if command is None:
                    continue  # `wxcli <group>` alone — nothing to check
                if group not in surface or command not in surface[group]:
                    continue
                sig = positional_surface.get(group, {}).get(command)
                if sig is None:
                    continue
                rest = arg_region(head_rest, strip_comment=True)
                nxt = rest.find("wxcli")
                if nxt != -1:
                    rest = rest[:nxt]
                # A `\` immediately before an inline `# comment` is a real shell
                # line-continuation, but code_spans only recognizes one when it
                # is the line's literal last character — with prose trailing it,
                # the line is never joined and strip_comment's cut leaves a bare
                # `\` dangling. Left in, posix shlex reads it as an escaped
                # space and manufactures a phantom "" token.
                rest = rest.rstrip()
                if rest.endswith("\\"):
                    rest = rest[:-1].rstrip()
                try:
                    tokens = shlex.split(rest, posix=True)
                except ValueError:
                    continue  # unbalanced quote — not a tokenizable example
                yield {"file": rel, "line": lineno, "group": group,
                       "command": command, "tokens": tokens, "in_code": in_code,
                       "prefixless": no_prefix, "sig": sig}


def check_positionals(surface: dict, positional_surface: dict) -> tuple[list, int]:
    """Documented `wxcli <group> <command> ...` examples whose POSITIONAL
    argument count does not match what the command declares — too many, too
    few, or any positional at all on a command that takes none. Checks 2/6/7
    cover command names and flags; nothing else here checks positionals, and a
    mismatch here means a copy-pasted example aborts before doing anything.

    Returns (findings, bare_name_citation_count). A bare `wxcli <group>
    <command>` with NO arguments at all, cited with single backticks OUTSIDE a
    fenced block, is a reference-table mention ("see `wxcli people show`"),
    not a broken runnable example — counted separately and never a failure.
    The same bare citation INSIDE a fenced code block IS a failure: it reads
    as a copy-pasteable example missing a required argument.

    Unresolved group/command names are check 2's job and are skipped here
    exactly as check 6 skips them; a name mounted as a sub-typer (e.g. cucm's
    nested `config`) rather than a leaf command is skipped the same way
    check 6 skips it (real=None). Neither class has any actionable finding in
    this repo today (verified against d1-positionals/findings.tsv).
    """
    findings: list[dict] = []
    bare_count = 0
    allow = load_allowlist()
    global_bools = global_bool_flags(positional_surface)
    for inv in doc_invocations(surface, positional_surface):
        rel, lineno = inv["file"], inv["line"]
        group, command = inv["group"], inv["command"]
        sig, tokens, in_code, no_prefix = (inv["sig"], inv["tokens"],
                                           inv["in_code"], inv["prefixless"])
        # "positional <file> <group> <command>" — file-scoped, and a DIFFERENT
        # claim from check 2's "ref": it says this doc shows a deliberately
        # WRONG argument list (a "not like this" example), whereas "ref" says
        # the name is not a real citation. Sharing one key would let either
        # claim silence the other check.
        if (group in allow or f"{group} {command}" in allow
                or f"positional {rel} {group} {command}" in allow):
            continue
        positionals, ellipsis, unbalanced = split_doc_positionals(
            tokens, sig["flags"], global_bools)
        if unbalanced:
            continue  # truncated usage-synopsis notation, not an example
        declared = sig["args"]
        need = sum(1 for _, req in declared if req)
        total = len(declared)
        n = len(positionals)
        if n > total:
            kind = "positional_on_zero_arg" if total == 0 else "too_many"
        elif n < need:
            if ellipsis or "--help" in tokens:
                continue  # explicitly elided, or --help short-circuits
            if n == 0 and not in_code:
                bare_count += 1
                continue
            kind = "too_few"
        else:
            continue
        findings.append({
            "file": rel, "line": lineno, "cmd": f"{group} {command}",
            "supplied": n, "need": need, "total": total, "kind": kind,
            "prefixless": no_prefix,
        })
    return findings, bare_count


# ---------------------------------------------------------------- check 11b

ARG_KIND = re.compile(r"Webex ([A-Z][A-Z0-9_]*) id")
ARG_PRODUCER = re.compile(r"from: wxcli ([a-z0-9-]+) ([a-z0-9-]+)")
DOC_PLACEHOLDER = re.compile(r"^[A-Z][A-Z0-9_]*$")


def parse_module_arg_kinds(
        module: str, commands_dir: Path = COMMANDS_DIR) -> dict[str, list[dict]]:
    """command -> ordered [{kind, producer}] for each positional argument.

    Last session's argument-help work writes the ID *kind* and its producing
    command into the help string ("Webex HYBRID_CLUSTER id, from: wxcli
    video-mesh list") on 69.5% of the 1510 positional arguments; a further
    12.5% say only "UUID". That is what makes this checkable at all — a doc
    placeholder can finally be compared against a declared kind.
    """
    path = commands_dir / f"{module}.py"
    if not path.exists():
        return {}
    out: dict[str, list[dict]] = {}
    for node in ast.walk(ast.parse(path.read_text())):
        if not isinstance(node, ast.FunctionDef):
            continue
        name = _command_name(node)
        if name is None:
            continue
        params = node.args.args + node.args.kwonlyargs
        defaults = ([None] * (len(node.args.args) - len(node.args.defaults))
                    + list(node.args.defaults) + list(node.args.kw_defaults))
        args = []
        for param, default in zip(params, defaults):
            call = _typer_call(default, "Argument")
            if call is None:
                continue
            help_text = ""
            for kw in call.keywords:
                if kw.arg == "help" and isinstance(kw.value, ast.Constant):
                    help_text = kw.value.value or ""
            km = ARG_KIND.match(help_text)
            pm = ARG_PRODUCER.search(help_text)
            args.append({
                "param": param.arg,
                "kind": km.group(1) if km else None,
                "uuid": help_text.startswith("UUID"),
                "producer": f"{pm.group(1)} {pm.group(2)}" if pm else None,
            })
        out.setdefault(name, args)
    return out


def build_arg_kind_surface() -> dict[str, dict[str, list[dict]]]:
    countable = module_state()["countable"]
    surface = {}
    for group, module in parse_registrations().items():
        if module not in countable:
            continue
        surface[group] = parse_module_arg_kinds(module)
    if "converged-recordings" in surface:
        surface["converged-recordings"].update(
            parse_module_arg_kinds("converged_recordings_export"))
    return surface


# Words the CLI and its docs use for the SAME resource. English synonyms only —
# never a claim that two Webex resources are interchangeable. Without these,
# `PERSON_ID` against `Webex PEOPLE id` and `WORKSPACE_ID` against
# `Webex PLACE id` read as mismatches, and those two alone accounted for most
# of the first run's 240 findings.
KIND_SYNONYMS = (
    {"PEOPLE", "PERSON", "USER"},
    {"PLACE", "PLACES", "WORKSPACE"},
    {"HYBRID", "CLUSTER"},
)


def _tokens(text: str) -> set[str]:
    """Comparable word set, with English synonyms folded together. `WS_ID` still
    shares nothing with `PLACE`, so the caller treats "no overlap" as UNDECIDED
    unless the placeholder positively names a different known kind."""
    out = {t for t in text.upper().split("_") if t and t != "ID"}
    for group in KIND_SYNONYMS:
        if out & group:
            out |= group
    return out


def check_arg_kinds(surface: dict, positional_surface: dict,
                    kind_surface: dict) -> tuple[list, list]:
    """Doc placeholders that name a different resource than the argument takes.

    Returns (mismatches, advisories) — two tiers, deliberately not one number.

    TIER 1 (mismatches, GATED). The argument declares a specific kind and the
    placeholder positively names a DIFFERENT kind that exists elsewhere in this
    CLI. Both sides are then explicit and disagree, which is mechanical.
    Anything the placeholder does not map to a known kind is UNDECIDED and
    dropped — `WS_ID` against `Webex PLACE id` is a naming-convention gap, not
    a defect, and gating on it would fail the build on correct docs.

    TIER 2 (advisories, NEVER GATED). The argument declares only a bare `UUID`,
    so kind-matching cannot decide it — this is the `wxcli meetings show
    TEMPLATE_ID` shape, where the positional is a meeting and the placeholder
    says template. The only available signal is that the placeholder names a
    resource some OTHER command in the same group is named for, while the
    declared producer command is not. That is a heuristic about English, not a
    fact about the CLI, so it is reported and never failed.
    """
    known_kinds = {k["kind"] for cmds in kind_surface.values()
                   for args in cmds.values() for k in args if k["kind"]}
    kind_tokens = {k: _tokens(k) for k in known_kinds}
    # The CLI's own label is only usable where the CLI agrees with itself. 79 of
    # the 1049 kind-carrying arguments declare a kind their parameter NAME
    # contradicts — `location_id` help-typed "Webex PEOPLE id", `hunt_group_id`
    # typed LOCATION, `call_queue_id` typed HUNT_GROUP. On those, the doc is
    # usually right and the help is wrong, so comparing a placeholder against
    # the label reports correct docs as defects. They are excluded here and
    # reported on their own line as a CLI-side defect.
    suspect = {(g, c, a["param"])
               for g, cmds in kind_surface.items()
               for c, args in cmds.items() for a in args
               if a["kind"] and not (_tokens(a["param"]) & kind_tokens[a["kind"]])
               and any(_tokens(a["param"]) & kt for kt in kind_tokens.values())}
    mismatches: list[dict] = []
    advisories: list[dict] = []
    allow = load_allowlist()
    global_bools = global_bool_flags(positional_surface)
    for inv in doc_invocations(surface, positional_surface):
        rel, group, command = inv["file"], inv["group"], inv["command"]
        declared = kind_surface.get(group, {}).get(command)
        if not declared:
            continue
        if (group in allow or f"{group} {command}" in allow
                or f"arg-kind {rel} {group} {command}" in allow):
            continue
        supplied, _ellipsis, unbalanced = split_doc_positionals(
            inv["tokens"], inv["sig"]["flags"], global_bools)
        if unbalanced or len(supplied) != len(declared):
            continue  # count mismatch is check 10's finding, not this one
        for token, decl in zip(supplied, declared):
            if not DOC_PLACEHOLDER.match(token):
                continue  # a real value, not a placeholder — nothing to compare
            toks = _tokens(token)
            if not toks:
                continue
            if decl["kind"]:
                if (group, command, decl["param"]) in suspect:
                    continue  # the label itself is wrong — see `suspect` above
                if toks & kind_tokens[decl["kind"]]:
                    continue  # placeholder and kind agree
                named = sorted(k for k, kt in kind_tokens.items() if toks & kt)
                if not named:
                    continue  # UNDECIDED — placeholder names no known kind
                mismatches.append({
                    "file": rel, "line": inv["line"],
                    "cmd": f"{group} {command}", "arg": decl["param"],
                    "placeholder": token, "declared": decl["kind"],
                    "reads_as": named[0], "prefixless": inv["prefixless"],
                })
            elif decl["uuid"] and decl["producer"]:
                prod_cmd = decl["producer"].split(" ", 1)[1]
                if toks & _tokens(prod_cmd.replace("-", "_")):
                    continue  # placeholder matches the producer's own name
                sibling = sorted(
                    c for c in surface.get(group, {})
                    if c != command and toks & _tokens(c.replace("-", "_")))
                if not sibling:
                    continue
                advisories.append({
                    "file": rel, "line": inv["line"],
                    "cmd": f"{group} {command}", "arg": decl["param"],
                    "placeholder": token, "producer": decl["producer"],
                    "sibling": sibling[0], "prefixless": inv["prefixless"],
                })
    mislabelled = []
    for g, c, p in sorted(suspect):
        declared = next(a["kind"] for a in kind_surface[g][c] if a["param"] == p)
        reads = sorted(k for k, kt in kind_tokens.items() if _tokens(p) & kt)
        mislabelled.append({"group": g, "command": c, "arg": p,
                            "declared": declared, "reads_as": reads[0]})
    return mismatches, advisories, mislabelled


# ----------------------------------------------------------------- check 12

GATED_SEVERITIES = ("CRITICAL", "HIGH")


def build_naming_findings() -> list[dict]:
    """d3's List B + List C over the shipped CLI surface.

    Modules are deduplicated by MODULE, not by group: `users`, `cx-essentials`
    and `licenses-api` mount an existing module under a second name, and
    counting them twice inflated List C from 156 to 164 on the first run. With
    the dedupe, this reproduces the standalone detector's numbers exactly
    (42 / 156 / 129 HIGH / 27 MEDIUM), which is the cross-check that the port
    is faithful.
    """
    countable = module_state()["countable"]
    by_module: dict[str, list[str]] = {}
    for group, module in parse_registrations().items():
        if module in countable:
            by_module.setdefault(module, []).append(group)
    cmds = []
    for module, groups in by_module.items():
        cmds += verb_naming.parse_module(module, sorted(groups)[0])
    return (verb_naming.numeric_suffix_findings(cmds)
            + verb_naming.resource_mismatch_findings(cmds))


def check_naming(findings: list[dict], acked: dict) -> tuple[list, list, list]:
    """Returns (unacked, stale, advisory).

    `unacked` fails the build: a name whose obvious reading points somewhere
    else, which nobody has signed off on. `stale` also fails — an ack that no
    longer describes reality is the failure mode every exemption in this repo
    has hit at least once. `advisory` is the MEDIUM tier, reported only.

    THRESHOLD (Adam, 2026-07-28): CRITICAL+HIGH fails. CRITICAL alone would
    gate nothing — the only CRITICAL rows anywhere are the four
    `update-access-codes` commands he decided on 2026-07-14 to keep — and a
    gate that cannot fail is the confident-zero failure this repo has hit six
    times. Numeric suffixes fail regardless of severity: a `-N` name carries no
    meaning, so it is always a decision the generator could not make.

    The ack is keyed by OPERATION (`METHOD /path`) and carries the command name
    and severity it was written for, copying verb_semantics_ack exactly. That
    is what makes it un-rottable: rename the command, or have it reclassify,
    and the recorded values stop matching, so the entry must be revisited
    rather than silently covering a name nobody reviewed.
    """
    unacked, stale, advisory = [], [], []
    live: dict[str, dict] = {}
    for f in findings:
        key = f"{f['kind']} {f['op']}"
        live[key] = f
        if f["severity"] not in GATED_SEVERITIES:
            advisory.append(f)
            continue
        ack = acked.get(key)
        if ack is None:
            unacked.append(f)
            continue
        # "<group> <command>": the same command NAME exists in many groups, so
        # the group is part of what was acked.
        cited = f"{f['group']} {f['command']}"
        if ack.get("command") != cited:
            stale.append({**f, "reason": f"acked for command "
                          f"{ack.get('command')!r}, now {cited!r} — "
                          f"renamed; re-review and update or drop the ack"})
        elif ack.get("severity") != f["severity"]:
            stale.append({**f, "reason": f"acked at {ack.get('severity')!r}, "
                          f"now classifies {f['severity']!r}"})
    for key, ack in acked.items():
        if key not in live:
            kind, _, op = key.partition(" ")
            stale.append({"group": ack.get("command", "?").split(" ")[0],
                          "command": ack.get("command", "?"), "op": op,
                          "severity": ack.get("severity", "?"), "kind": kind,
                          "reason": "no longer flagged — the name was fixed or "
                                    "the operation is gone; delete this ack"})
    return unacked, stale, advisory


# ----------------------------------------------------------- checks 13 & 14

# The 11 dev-only modules: gitignored (.gitignore:111), absent from the shipped
# wheel, present only on a developer's disk. A prior round let them inflate
# three separate counts, so the exclusion below is ASSERTED on every run
# (fs_exclusion_audit) rather than assumed — a guard that cannot be shown to
# still bind is not a guard.
FS_MODULES = {
    "fs_connectors", "fs_expression_test", "fs_flow_props", "fs_flow_versions",
    "fs_flows", "fs_flows_v2", "fs_projects", "fs_resources", "fs_templates",
    "fs_tracing", "fs_user_prefs",
}

# tools/field_overrides.yaml: auto_inject_from_config. These query parameters
# are supplied from saved config at runtime, so a spec marking them required is
# satisfied with no flag — the same exception 11a's docstring records.
AUTO_INJECT = {"orgid"}

JSON_CONTENT_KEYS = ("application/json", "application/json;charset=UTF-8",
                     "application/json-patch+json")

_SEPARATE_SPECS: dict[str, dict] | None = None
_SPEC_OP_INDEX: dict[str, dict] | None = None


def _ref(spec: dict, schema: dict) -> dict:
    """Resolve one `$ref` safely — {} rather than KeyError on a dangling ref."""
    node = spec
    for part in schema["$ref"].lstrip("#/").split("/"):
        node = node.get(part, {}) if isinstance(node, dict) else {}
    return node if isinstance(node, dict) else {}


def load_specs_separately() -> dict[str, dict]:
    """{spec filename: parsed spec, overlays merged} — kept APART, never pooled.

    load_spec_ops() collapses all nine specs into one dict with `setdefault`, so
    the first spec to declare a path wins and the rest become invisible. That is
    correct for a parity count and fatal for a per-operation question: check 9's
    predecessor unioned two specs describing one endpoint and reported a
    confident 0 over a live-broken command. Checks 13/14 index per file and SKIP
    an operation whose declaring specs disagree, rather than guessing which is
    authoritative.
    """
    global _SEPARATE_SPECS
    if _SEPARATE_SPECS is None:
        _SEPARATE_SPECS = {}
        for rel in sorted(tracked_specs()):
            spec = json.loads((REPO / rel).read_text())
            _SEPARATE_SPECS[Path(rel).name] = merge_overlay(
                spec, load_overlay(REPO / rel))
    return _SEPARATE_SPECS


def spec_op_index() -> dict[str, dict[tuple[str, str], dict]]:
    """{spec filename: {(METHOD, normalized path): operation}} — one per spec."""
    global _SPEC_OP_INDEX
    if _SPEC_OP_INDEX is None:
        _SPEC_OP_INDEX = {}
        for name, spec in load_specs_separately().items():
            idx: dict[tuple[str, str], dict] = {}
            for path, methods in spec.get("paths", {}).items():
                for method, op in methods.items():
                    if method.lower() not in HTTP_METHODS or not isinstance(op, dict):
                        continue
                    idx.setdefault((method.upper(), normalize_path(path)), op)
            _SPEC_OP_INDEX[name] = idx
    return _SPEC_OP_INDEX


def body_schema(op: dict, spec: dict) -> dict | None:
    """Resolved request-body schema with allOf merged.

    Content-type selection copies openapi_parser.parse_request_body so this sees
    the same body the generator saw. Unlike check 9's `_resolve_schema` this
    keeps `required`, which is the entire oracle for checks 13 and 14.
    """
    content = op.get("requestBody", {}).get("content", {})
    node = next((content[k] for k in JSON_CONTENT_KEYS if k in content), None)
    if not node:
        return None
    schema = node.get("schema", {})
    if "$ref" in schema:
        schema = _ref(spec, schema)
    if "allOf" in schema:
        props, required = {}, []
        for item in schema["allOf"]:
            if "$ref" in item:
                item = _ref(spec, item)
            props.update(item.get("properties", {}))
            required.extend(item.get("required", []))
        schema = {"type": "object", "properties": props,
                  "required": list(dict.fromkeys(required))}
    return schema or None


def required_body_fields(op: dict, spec: dict) -> list[str]:
    schema = body_schema(op, spec)
    if not schema:
        return []
    props = schema.get("properties", {})
    # A `required` entry naming no property is a spec bug, not a CLI gap.
    return [f for f in schema.get("required", []) if f in props]


def required_query_params(op: dict) -> list[str]:
    return [p["name"] for p in op.get("parameters", [])
            if isinstance(p, dict) and p.get("in") == "query"
            and p.get("required") is True and p.get("name")]


def field_shape(op: dict, spec: dict, name: str) -> str:
    """'object' | 'array' | 'scalar' for one top-level body property."""
    prop = (body_schema(op, spec) or {}).get("properties", {}).get(name, {})
    if "$ref" in prop:
        prop = _ref(spec, prop)
    t = prop.get("type")
    if t in ("object", "array"):
        return t
    return "object" if (t is None and "properties" in prop) else "scalar"


def _const_key(node) -> str | None:
    sl = node.slice
    return sl.value if isinstance(sl, ast.Constant) and isinstance(sl.value, str) else None


def command_names(node: ast.FunctionDef) -> list[tuple[str, bool]]:
    """Every `@app.command` name on one function, as (name, hidden).

    38 generated functions carry two decorators: a hidden deprecated alias
    FIRST, then the visible name. `_command_name` returns whichever it meets
    first, which is fine for a resolvable key and wrong for a report an operator
    reads — `announcements generate-a-text` is not in --help at all while
    `tts-generate` is.
    """
    out = []
    for deco in node.decorator_list:
        call = deco if isinstance(deco, ast.Call) else None
        func = call.func if call else deco
        if not (isinstance(func, ast.Attribute) and func.attr == "command"):
            continue
        hidden = any(kw.arg == "hidden"
                     and isinstance(kw.value, ast.Constant)
                     and kw.value.value is True
                     for kw in (call.keywords if call else []))
        name = None
        if call and call.args and isinstance(call.args[0], ast.Constant):
            name = call.args[0].value
        else:
            for kw in (call.keywords if call else []):
                if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                    name = kw.value.value
        out.append((name or node.name.replace("_", "-"), hidden))
    return out


class CommandFacts:
    """Everything checks 13/14 need about ONE generated command.

    Read off the SHIPPED source with `ast` — never by importing wxcli (a
    subagent once imported generated delete functions and four unconfirmed
    DELETEs reached a live org) and never by re-modelling the generator, which
    would go stale the moment an override changed. Reading the source is also
    what makes this immune to `param_name_overrides`: that renames the CLI flag
    and leaves the wire name, and the wire name is what `body[...]` writes.
    """

    def __init__(self, module: str, group: str, node: ast.FunctionDef,
                 src_lines: list[str]):
        self.module, self.group = module, group
        names = command_names(node)
        visible = [n for n, hidden in names if not hidden]
        self.command = visible[0] if visible else names[0][0]
        self.node = node
        self.doc = ast.get_docstring(node, clean=False) or ""
        self.lineno = node.lineno
        self._read_params()
        self._read_dict_writes()
        self._read_url(src_lines)
        self._read_examples()

    def _read_params(self):
        self.flags: dict[str, set[str]] = {}
        params = self.node.args.args + self.node.args.kwonlyargs
        defaults = ([None] * (len(self.node.args.args) - len(self.node.args.defaults))
                    + list(self.node.args.defaults) + list(self.node.args.kw_defaults))
        for param, default in zip(params, defaults):
            opt = _typer_call(default, "Option")
            if opt is not None:
                names = {p for a in opt.args[1:]
                         if isinstance(a, ast.Constant) and isinstance(a.value, str)
                         for p in a.value.split("/") if p.startswith("-")}
                self.flags[param.arg] = names or {"--" + param.arg.replace("_", "-")}
        self.has_json_body = "json_body" in self.flags

    def _read_dict_writes(self):
        """Which wire fields the function can actually set, and from what.

        A body field is REACHABLE iff the function contains `body["<wire>"] =
        <param>` or a `setdefault`. `setdefault(k, <literal>)` hard-wires a
        value with no flag — hunt_group does this for callPolicies/agents/
        enabled — and the field IS satisfied, so treating it as flagless would
        be a false positive. Any write this parse cannot resolve to a constant
        key sets `opaque_writes`, and the command is skipped rather than judged.
        """
        self.body_from: dict[str, str | None] = {}
        self.query_from: dict[str, str | None] = {}
        self.opaque_writes = False
        for n in ast.walk(self.node):
            tgt = dest = None
            if isinstance(n, ast.Assign) and len(n.targets) == 1 \
                    and isinstance(n.targets[0], ast.Subscript) \
                    and isinstance(n.targets[0].value, ast.Name):
                tgt, dest, val = n.targets[0], n.targets[0].value.id, n.value
            elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                    and n.func.attr in ("setdefault", "update") \
                    and isinstance(n.func.value, ast.Name):
                dest = n.func.value.id
                if dest not in ("body", "params"):
                    continue
                if n.func.attr == "update" or not n.args \
                        or not isinstance(n.args[0], ast.Constant):
                    self.opaque_writes = True
                    continue
                key, val = n.args[0].value, (n.args[1] if len(n.args) > 1 else None)
                sink = self.body_from if dest == "body" else self.query_from
                sink.setdefault(key, val.id if isinstance(val, ast.Name) else None)
                continue
            if dest not in ("body", "params"):
                continue
            key = _const_key(tgt)
            if key is None:
                self.opaque_writes = True
                continue
            sink = self.body_from if dest == "body" else self.query_from
            sink.setdefault(key, val.id if isinstance(val, ast.Name) else None)

    def _read_url(self, src_lines: list[str]):
        """(METHOD, normalized path) pairs for this function.

        Per-function rather than `parse_module_commands`, which is regex over
        the whole module and merges same-named commands. Normalization and
        URL_BASES stripping stay the gate's.
        """
        seg = "\n".join(src_lines[self.node.lineno - 1:self.node.end_lineno])
        self.urls: list[tuple[str, str]] = []
        current = None
        for m in re.finditer(r'url = f?"([^"]+)"'
                             r'|rest_(get|put|post|patch|delete)\('
                             r'|follow_pagination\(', seg):
            if m.group(1):
                current = m.group(1)
                for base in URL_BASES:
                    if current.startswith(base):
                        current = current[len(base):]
                        break
            elif current is not None:
                self.urls.append(((m.group(2) or "get").upper(),
                                  normalize_path(current)))
        self.urls = list(dict.fromkeys(self.urls))

    def _read_examples(self):
        self.example = None
        for line in self.doc.split("\n"):
            s = line.strip()
            if s.startswith("Example:"):
                self.example = s

    def example_tokens(self) -> list[str] | None:
        """Tokens of the printed example, via the gate's own arg_region + shlex.

        Reused rather than re-implemented: round 2 lost two agents to hand-rolled
        versions (a redirect's `2` counted as an argument; an unterminated quote
        silently truncated a scan).
        """
        if not self.example:
            return None
        body = self.example[len("Example:"):].strip()
        for group, command, head_rest, _ in command_heads(body):
            if command is None:
                continue
            rest = arg_region(head_rest, strip_comment=True).rstrip()
            if rest.endswith("\\"):
                rest = rest[:-1].rstrip()
            try:
                return shlex.split(rest, posix=True)
            except ValueError:
                return None
        return None


def parse_module_facts(module: str, group: str) -> list[CommandFacts]:
    path = COMMANDS_DIR / f"{module}.py"
    if not path.exists():
        return []
    text = path.read_text()
    lines = text.splitlines()
    return [CommandFacts(module, group, node, lines)
            for node in ast.walk(ast.parse(text))
            if isinstance(node, ast.FunctionDef) and command_names(node)]


def skeleton_lies(skel, schema: dict, spec: dict, path: str = ""):
    """Yield (json path, spec type, rendered value) where the skeleton flattens.

    `_schema_to_example` used to return the literal string "..." past depth 2.
    For a scalar leaf that is a correct placeholder; for an object or array it
    is a lie — `licenses update` printed `"properties":"..."` where `properties`
    is a three-field object, and an operator following the printed shape sends a
    string. The bounds that remain (a $ref cycle, _MAX_EXAMPLE_DEPTH) return
    `_empty_for`, i.e. `{}` or `[]`, so they degrade to a type-correct container
    and this check stays satisfiable on a pathological schema.
    """
    if "$ref" in schema:
        schema = _ref(spec, schema)
    t = schema.get("type") or ("object" if "properties" in schema else None)
    if t in ("object", "array") and not isinstance(skel, (dict, list)):
        yield path or "<root>", t, skel
        return
    if t == "object" and isinstance(skel, dict):
        props = schema.get("properties", {})
        for k, v in skel.items():
            if k in props:
                yield from skeleton_lies(v, props[k], spec,
                                         f"{path}.{k}" if path else k)
    elif t == "array" and isinstance(skel, list) and skel:
        yield from skeleton_lies(skel[0], schema.get("items", {}), spec,
                                 f"{path}[]")


def check_generated_help() -> tuple[list, list, dict]:
    """Checks 13 and 14, in ONE pass: (bad_examples, bad_skeletons, fs_audit).

    Both read the same join — shipped generated source against the ONE spec
    that declares the operation — so they share the pass rather than paying for
    two. Splitting them would double a ~1s scan to answer the same question
    twice.

    Requiredness comes from the spec; reachability comes from the shipped
    source. Neither direction is inferred from the other, which is what lets a
    finding mean "the printed string cannot work" rather than "these two
    representations differ".
    """
    indexes = spec_op_index()
    specs = load_specs_separately()
    registrations = parse_registrations()
    countable = module_state()["countable"]

    # Alias groups share a module; count each command once under the canonical
    # (first, non-alias) group name.
    canonical: dict[str, str] = {}
    for group, module in sorted(registrations.items()):
        canonical.setdefault(module, group)
    if "converged-recordings" in registrations:
        canonical.setdefault("converged_recordings_export", "converged-recordings")

    # Prove the fs_* exclusion instead of trusting it. These 11 are on a
    # developer's disk and excluded by .gitignore, so they must reach neither
    # `countable` nor `parse_registrations`. Reporting the audit every run is
    # what stops the guard becoming silently vacuous.
    fs_audit = {
        "declared": sorted(FS_MODULES),
        "present_on_disk": sorted(p.stem for p in COMMANDS_DIR.glob("fs_*.py")),
        "leaked": sorted((FS_MODULES & countable)
                         | (FS_MODULES & set(registrations.values()))),
    }

    bad_examples, bad_skeletons = [], []
    for module, group in sorted(canonical.items()):
        if module in FS_MODULES or module not in countable:
            continue
        module_src = (COMMANDS_DIR / f"{module}.py").read_text()

        for cf in parse_module_facts(module, group):
            if not cf.urls:
                continue                      # hand-written, no rest_* call
            write = [u for u in cf.urls if u[0] != "GET"] or cf.urls
            method, npath = write[0]
            declaring = [(name, idx[(method, npath)])
                         for name, idx in indexes.items()
                         if (method, npath) in idx]
            if not declaring:
                continue                      # in no tracked spec
            per_spec = {name: (required_body_fields(op, specs[name]),
                               required_query_params(op))
                        for name, op in declaring}
            if len({(tuple(sorted(b)), tuple(sorted(q)))
                    for b, q in per_spec.values()}) > 1:
                continue                      # specs disagree — never guess
            spec_name, op = declaring[0]
            spec = specs[spec_name]
            req_body, req_query = per_spec[spec_name]

            # -- check 14: the --generate-json-body skeleton -----------------
            m = re.search(rf"_BODY_SKELETON_{re.escape(cf.node.name.upper())}"
                          r"\s*=\s*('.*?'|\".*?\")\n", module_src)
            schema = body_schema(op, spec) if m else None
            if m and schema:
                try:
                    skel = json.loads(ast.literal_eval(m.group(1)))
                except (ValueError, SyntaxError):
                    skel = None
                    # A skeleton that will not parse is a DEFECT, not a reason
                    # to look away — `--generate-json-body` prints it verbatim
                    # for the caller to edit and pass back, so malformed JSON
                    # is unusable. Silently skipping it is how a check reports
                    # a confident 0 over the very thing it exists to catch.
                    bad_skeletons.append({
                        "group": group, "command": cf.command,
                        "kind": "skeleton-not-parseable",
                        "json_path": "(whole body)",
                        "spec_type": "n/a", "rendered": m.group(1)[:120],
                        "spec": spec_name})
                if skel is not None:
                    for jpath, stype, rendered in skeleton_lies(skel, schema, spec):
                        bad_skeletons.append({
                            "group": group, "command": cf.command,
                            "kind": "nested-object-as-scalar",
                            "json_path": jpath, "spec_type": stype,
                            "rendered": json.dumps(rendered), "spec": spec_name})
                    if isinstance(skel, dict):
                        for f in req_body:
                            if f not in skel:
                                bad_skeletons.append({
                                    "group": group, "command": cf.command,
                                    "kind": "required-field-omitted",
                                    "json_path": f,
                                    "spec_type": field_shape(op, spec, f),
                                    "rendered": "(absent)", "spec": spec_name})

            # -- check 13: the printed Example line --------------------------
            # Only spec-REQUIRED fields are ever considered, so an optional
            # field with no flag is structurally incapable of firing this — the
            # negative control the reference detector used to prove the check
            # is not merely flagging any absent flag.
            if not cf.example or not (req_body or req_query) or cf.opaque_writes:
                continue
            tokens = cf.example_tokens()
            if tokens is None:
                continue
            # An example that reaches for --json-body is NOT exempt: the inline
            # payload must itself carry every required field.
            #
            # 2026-07-28: this used to `continue` on "--json-body" in tokens,
            # calling it "the escape hatch". That skip made the check blind to
            # exactly the population it was built to police — the generator fix
            # rewrote all 99 unrunnable examples to pass --json-body, so 121
            # examples took the exemption and the check read a confident 0 over
            # them. Planting the live anchor's defect back (dropping the
            # required `address` object from `location-settings create`) did not
            # fire it. Same shape as check 9's spec union and check 3's regex:
            # an exemption wider than the evidence justifying it.
            inline_body = None
            if "--json-body" in tokens:
                jb = re.search(r"--json-body\s+'(\{.*?\})'\s*$", cf.example)
                if not jb:
                    continue          # not an inline literal — nothing to judge
                try:
                    inline_body = json.loads(jb.group(1))
                except ValueError:
                    inline_body = None
                if not isinstance(inline_body, dict):
                    continue
            if inline_body is not None:
                missing = [f"{f} ({field_shape(op, spec, f)})"
                           for f in req_body if f not in inline_body]
            else:
                missing = [f"{f} ({field_shape(op, spec, f)})"
                           for f in req_body if f not in cf.body_from]
            missing += [f"{q} (query)" for q in req_query
                        if q not in cf.query_from and q.lower() not in AUTO_INJECT]
            if missing:
                bad_examples.append({
                    "group": group, "command": cf.command, "module": module,
                    "line": cf.lineno, "example": cf.example, "missing": missing,
                    "spec": spec_name, "operation": f"{method} {npath}",
                    "json_body": cf.has_json_body})

    bad_examples.sort(key=lambda f: (f["group"], f["command"]))
    bad_skeletons.sort(key=lambda f: (f["kind"], f["group"], f["command"],
                                      f["json_path"]))
    return bad_examples, bad_skeletons, fs_audit


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


# ----------------------------------------------------------------- check 15

#: Registries whose size is claimed in prose, and where the claim is made.
#: Each entry: (label, source file, registry variable, [(file, regex) claims]).
#: The regex must capture the claimed number in group 1.
#:
#: Round-3 finding F17 measured the state before this check existed: mappers were
#: claimed as 20 in two places and 26 in two others (26 correct); analyzers as 13,
#: 14 and 15 (15 correct); preflight checks as 7, 8, 9 and 8 — and **no source
#: anywhere claimed the real number, 10**. Per the project's Source of Truth
#: Precedence, `--help` outranks the docs, so an agent trusting it under-counted
#: the analysis coverage it was verifying.
_REGISTRY_CLAIMS: list[tuple[str, str, str, list[tuple[str, str]]]] = [
    (
        "transform mappers",
        "src/wxcli/migration/transform/engine.py",
        "MAPPER_ORDER",
        [
            ("src/wxcli/commands/cucm.py", r"Run (\d+) transform mappers"),
            ("src/wxcli/migration/transform/engine.py",
             r"Orchestrates all (\d+) transform mappers"),
            ("src/wxcli/migration/CLAUDE.md", r"Phase 05 — (\d+) mappers"),
        ],
    ),
    (
        "analyzers",
        "src/wxcli/migration/transform/analysis_pipeline.py",
        "ALL_ANALYZERS",
        [
            ("src/wxcli/commands/cucm.py", r"Run (\d+) analyzers"),
            ("src/wxcli/migration/transform/analysis_pipeline.py",
             r"runs all (\d+) analyzers"),
            ("src/wxcli/migration/CLAUDE.md", r"Phase 06 — (\d+) analyzers"),
        ],
    ),
]

#: The preflight check registry is a dict literal inside a method, not a
#: module-level assignment, so it needs its own extractor.
_PREFLIGHT_CLAIMS: list[tuple[str, str]] = [
    ("src/wxcli/migration/preflight/runner.py",
     r"Orchestrates all (\d+) preflight checks"),
    ("src/wxcli/migration/preflight/CLAUDE.md", r"## The (\d+) Checks"),
    ("src/wxcli/migration/preflight/CLAUDE.md", r"\| (\d+) check functions"),
    ("src/wxcli/migration/preflight/CLAUDE.md", r"run (\d+) checks as pure functions"),
    ("src/wxcli/migration/preflight/CLAUDE.md", r"Phase 10 — checks\.py \((\d+) preflight checks\)"),
    ("src/wxcli/migration/CLAUDE.md", r"checks\.py \((\d+) preflight checks\)"),
    (".claude/skills/cucm-migrate/SKILL.md", r"Preflight runs (\d+) checks"),
]


def _list_literal_len(path: Path, var: str) -> int | None:
    """Length of a module-level list assigned to ``var``, via ast. No import."""
    try:
        tree = ast.parse(path.read_text())
    except (OSError, SyntaxError):
        return None
    for node in ast.walk(tree):
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        for t in targets:
            if isinstance(t, ast.Name) and t.id == var:
                if isinstance(node.value, (ast.List, ast.Tuple, ast.Set)):
                    return len(node.value.elts)
    return None


def _preflight_check_count() -> int | None:
    """Number of entries in ``PreflightRunner.run``'s ``all_checks`` dict."""
    path = REPO / "src/wxcli/migration/preflight/runner.py"
    try:
        tree = ast.parse(path.read_text())
    except (OSError, SyntaxError):
        return None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == "all_checks":
                if isinstance(node.value, ast.Dict):
                    return len(node.value.keys)
    return None


def check_registry_counts() -> list[dict]:
    """Prose that claims a registry's size but disagrees with the registry.

    The count is derived from the registry by ``ast`` — reading the source, never
    importing it. Runtime derivation was considered and rejected: the CLI mounts
    groups lazily (870ms -> 108ms startup, see tools/CLAUDE.md), and importing
    the transform stack just to render a docstring would give that back. A gate
    check also covers the claims a runtime value cannot reach at all — the ones
    in CLAUDE.md and SKILL.md.
    """
    findings: list[dict] = []

    def _check(label: str, actual: int | None, claims: list[tuple[str, str]]) -> None:
        if actual is None:
            findings.append({
                "kind": "unreadable_registry",
                "label": label,
                "where": "-",
                "claimed": "-",
                "actual": "-",
                "detail": f"could not derive the {label} count from its registry",
            })
            return
        for rel, pattern in claims:
            p = REPO / rel
            if not p.exists():
                continue
            text = p.read_text()
            for m in re.finditer(pattern, text):
                claimed = int(m.group(1))
                if claimed != actual:
                    line = text[:m.start()].count("\n") + 1
                    findings.append({
                        "kind": "count_mismatch",
                        "label": label,
                        "where": f"{rel}:{line}",
                        "claimed": claimed,
                        "actual": actual,
                        "detail": (
                            f"claims {claimed} {label}, registry has {actual} "
                            f"— fix the prose or the registry"
                        ),
                    })

    for label, src, var, claims in _REGISTRY_CLAIMS:
        _check(label, _list_literal_len(REPO / src, var), claims)
    _check("preflight checks", _preflight_check_count(), _PREFLIGHT_CLAIMS)

    return findings


def check_inert_overrides() -> tuple[list, list]:
    """Override configuration in field_overrides.yaml that cannot apply.

    Two kinds, both of which parse, pass every existing test, and do nothing:

      * TAG-keyed — a top-level tag block, a `tag_overrides` entry or a
        `cli_name_overrides` entry naming a tag no spec on disk generates. Six
        blocks were inert this way until 2026-07-29, plus a table_columns block
        and a name mapping keyed on `Features: Customer Experience Essentials`
        after upstream renamed the tag, and four keyed on CLI GROUP names
        (`fs-flows`) instead of tags.
      * COMMAND-keyed — a per-command key inside a resolved tag block naming a
        command that tag does not render (`table_columns: {list-calls: ...}` in a
        group whose commands are list-calls-members / list-calls-me). The
        generator refuses these outright; this re-checks them from the gate, so
        the finding does not depend on somebody running a regen.

    Deliberately NOT flagged: `tag_merge` sources and `tag_op_excludes` keys. Both
    are "if this tag is present, correct it" — an absent tag makes them a no-op by
    design, and gating them would fight a legitimately defensive pattern. What
    bites is config that is supposed to change a name or a column TODAY.

    `inert_tag_ack` declares the exceptions (one today: the AI Assistant tag,
    removed upstream, whose name mapping is kept on purpose). Every ack is
    re-validated: an acked tag that resolves again is returned as a stale ack and
    fails, so the list cannot decay into an allowlist.

    Resolution is the GENERATOR's, imported rather than reimplemented — tags come
    from the same merge/skip pipeline and commands from the same parse_tag plus
    apply_endpoint_overrides, keyed on the same COMMAND_KEYED_OVERRIDES. A second
    copy of that logic here is how a check ends up disagreeing with the thing it
    is checking.

    Specs are read from DISK, not from git — unlike the rest of this file. A
    per-spec section keyed on a spec that is absent (webex-flow-store.json on a
    fresh clone) is out of scope rather than inert, and the dev-only tags it
    declares must not read as defects just because the spec is untracked.
    """
    import yaml   # load_overrides()'s hand-rolled parser stays for the other
                  # checks; this one needs three levels of nesting and a folded
                  # scalar (command_help_notes), which a line parser reads wrong.
                  #
                  # This used to claim yaml "cannot be missing where this runs,
                  # since it is a hard runtime dependency in pyproject". That was
                  # false: CI's drift-gate job installed nothing on purpose, so
                  # the gate crashed with ModuleNotFoundError before check 1 and
                  # reported NOTHING while looking like an ordinary red build.
                  # The job now installs pyyaml explicitly — if you move this
                  # import or add another dependency, update that job too.
    try:
        from tools import generate_commands as gc
        from tools.openapi_parser import get_tags, load_spec, parse_tag
        from tools.postman_parser import apply_endpoint_overrides
    except ImportError:  # pragma: no cover — runnable as a bare script
        import generate_commands as gc
        from openapi_parser import get_tags, load_spec, parse_tag
        from postman_parser import apply_endpoint_overrides

    ovr = yaml.safe_load(OVERRIDES.read_text()) or {}
    acks = ovr.get("inert_tag_ack") or {}
    on_disk = sorted(p.name for p in SPECS_DIR.glob("*.json"))

    specs, generated = {}, {}
    for name in on_disk:
        spec = load_spec(str(SPECS_DIR / name))
        merge = gc.resolve_tag_merge(ovr.get("tag_merge"), name)
        if merge:
            gc.merge_tags(spec, merge)
        skip = gc.resolve_skip_patterns(ovr.get("skip_tags"), name)
        specs[name] = spec
        generated[name] = {t for t in get_tags(spec)
                           if not gc.should_skip_tag(t, skip)}
    everywhere = set().union(*generated.values()) if generated else set()

    top_blocks = {k: v for k, v in ovr.items()
                  if k not in gc.KNOWN_GLOBAL_KEYS and not k.startswith("_")
                  and isinstance(v, dict)}
    findings = []

    def resolves(spec_key: str, tag: str) -> bool | None:
        """True/False, or None when the spec is not on disk (out of scope)."""
        if spec_key == "_global":
            return tag in everywhere
        if spec_key not in generated:
            return None
        return tag in generated[spec_key]

    for tag, block in sorted(top_blocks.items()):
        if tag not in everywhere:
            findings.append({"kind": "tag", "where": "top-level block",
                             "spec": "*", "tag": tag,
                             "detail": f"keys={', '.join(sorted(block))}"})
    for family in ("tag_overrides", "cli_name_overrides"):
        for spec_key, tags in sorted((ovr.get(family) or {}).items()):
            for tag, val in sorted((tags or {}).items()):
                if resolves(spec_key, tag) is False:
                    detail = (f"keys={', '.join(sorted(val))}"
                              if isinstance(val, dict) else f"-> {val!r}")
                    findings.append({"kind": "tag", "where": family,
                                     "spec": spec_key, "tag": tag,
                                     "detail": detail})

    # The shallow-merge clash the generator also refuses: a family declared in
    # both forms for one tag, where tag_overrides wins and the top-level copy is
    # dropped whole — the original defect, one level down.
    for spec_key, tags in sorted((ovr.get("tag_overrides") or {}).items()):
        for tag, block in sorted((tags or {}).items()):
            clash = sorted(set(top_blocks.get(tag) or {}) & set(block or {}))
            if clash:
                findings.append({"kind": "clash", "where": "tag_overrides",
                                 "spec": spec_key, "tag": tag,
                                 "detail": f"declared twice: {', '.join(clash)}"})

    # Command-keyed keys, per (spec, tag) that actually resolves.
    raw_tag_ovr = ovr.get("tag_overrides") or {}
    for name in on_disk:
        excludes = gc.resolve_tag_op_excludes(ovr.get("tag_op_excludes"), name)
        for tag in sorted(generated[name]):
            block = dict(top_blocks.get(tag) or {})
            block.update((raw_tag_ovr.get("_global") or {}).get(tag, {}))
            block.update((raw_tag_ovr.get(name) or {}).get(tag, {}))
            if not any(f in block for f in gc.COMMAND_KEYED_OVERRIDES):
                continue
            endpoints, _ = parse_tag(
                tag, specs[name],
                omit_query_params=list(ovr.get("omit_query_params", [])),
                auto_inject_params=set(
                    ovr.get("auto_inject_from_config", ["orgId"])),
                seen_operation_ids=set(), exclude_paths=excludes.get(tag))
            for ep in endpoints:
                apply_endpoint_overrides(ep, block)
            claimed = {ep.command_name for ep in endpoints}
            for family in gc.COMMAND_KEYED_OVERRIDES:
                entry = block.get(family)
                if not isinstance(entry, dict):
                    continue
                for cmd in sorted(k for k in entry if k not in claimed):
                    findings.append({"kind": "command", "where": family,
                                     "spec": name, "tag": tag,
                                     "detail": f"no command {cmd!r} in this tag"})

    acked_tags = {f["tag"] for f in findings if f["kind"] == "tag"} & set(acks)
    findings = [f for f in findings
                if not (f["kind"] == "tag" and f["tag"] in acks)]
    stale = [{"tag": t, "reason": " ".join(str(acks[t]).split())[:120]}
             for t in sorted(set(acks) - acked_tags)]
    return findings, stale


# Paging totals a Webex response uses to say "there is more than this page".
# Same four spellings src/wxcli/auth.py's _body_says_more reads at runtime, so
# the static check and the runtime warning agree on what a total looks like.
PAGING_TOTALS = frozenset({"totalResources", "totalRecords",
                           "totalResults", "total"})


def _schema_props(node, spec: dict, depth: int = 0) -> set[str]:
    """Top-level property names of a (possibly $ref'd) schema."""
    if depth > 4 or not isinstance(node, dict):
        return set()
    ref = node.get("$ref")
    if ref:
        target = spec.get("components", {}).get("schemas", {}).get(
            ref.rsplit("/", 1)[-1], {})
        return _schema_props(target, spec, depth + 1)
    return set(node.get("properties") or {})


def check_undeclared_paging(acks: dict | None = None,
                            commands_dir: Path = COMMANDS_DIR,
                            specs_dir: Path = SPECS_DIR) -> tuple[list, list]:
    """A list command whose `--all` is inert on an endpoint that pages anyway.

    `--all` ships on every list command, but which of three fetch branches it
    gets is decided entirely by what the SPEC declares — `_pagination_style`
    reads paging query parameters and a `Link` response header, nothing else.
    An endpoint that really pages, described by a spec declaring neither,
    renders into the non-paginating branch where `--all` is accepted and does
    nothing. Flag exists, flag does not work; the command exits 0 with page one.

    The signal this check adds is the spec's own 200 SCHEMA: a response that
    declares a paging total (`totalResources` / `totalRecords` / `totalResults`
    / `total`) is a response that expects to be paged, whatever its parameter
    list says. Those are the same four keys `_body_says_more` reads at runtime,
    so a hit here is an endpoint the CLI will WARN about on stderr while
    offering no flag that fixes it.

    The oracle is the RENDERED command, not the spec — a module on disk whose
    fetch block calls `rest_get` with no `all_pages` branch is the inert case by
    construction, so a generator change that starts honouring the schema
    silently retires findings instead of leaving them to rot.

    `/count`-terminating paths are excluded, and that exclusion is measured, not
    defensive: 5 of the 7 raw hits are `.../availableMembers/count`, where
    `totalCount` IS the answer the endpoint exists to return. `totalCount` is
    deliberately absent from PAGING_TOTALS for the same reason.

    Acked per operation in `undeclared_paging_ack`, re-validated every run: an
    ack whose operation no longer qualifies — spec fixed, command regenerated
    onto a walking branch, endpoint gone — is returned as stale and fails, so
    the list cannot decay into an allowlist.

    Specs are globbed from DISK, which for most of this file would make the
    result non-reproducible from a clone (the untracked dev-only
    webex-flow-store.json is on a developer's machine and nowhere else). It is
    safe HERE only because the COMMAND side is filtered first: dev-only modules
    are `fs_*` and are skipped, so no flow-store operation can ever reach the
    spec loop. Verified by removing the spec and re-running — identical
    findings. If that `fs_` skip is ever relaxed, filter the specs too.
    """
    if acks is None:
        import yaml   # hard runtime dependency of wxcli itself — see check 15
        acks = (yaml.safe_load(OVERRIDES.read_text())
                or {}).get("undeclared_paging_ack") or {}
    inert: dict[tuple[str, str], list[str]] = {}
    for mod in sorted(commands_dir.glob("*.py")):
        if mod.stem.startswith(("fs_", "_")):
            continue
        for block in re.split(r"\n(?=@app\.command)", mod.read_text()):
            if 'all_pages: bool = typer.Option(False, "--all"' not in block:
                continue
            if "if all_pages:" in block or "and not all_pages:" in block:
                continue  # --all reaches a walker on this command
            named = re.search(r'@app\.command\("([^"]+)"', block)
            url = re.search(r'url = f?"([^"]+)"', block)
            if not (named and url):
                continue
            path = url.group(1)
            for base in URL_BASES:
                if path.startswith(base):
                    path = path[len(base):]
                    break
            inert.setdefault(("GET", normalize_path(path)), []).append(
                f"{mod.stem.replace('_', '-')} {named.group(1)}")

    findings = []
    for spec_file in sorted(specs_dir.glob("webex-*.json")):
        spec = json.loads(spec_file.read_text())
        for path, methods in (spec.get("paths") or {}).items():
            op = (methods or {}).get("get")
            if not isinstance(op, dict):
                continue
            if normalize_path(path).rstrip("/").rsplit("/", 1)[-1] == "count":
                continue
            key = ("GET", normalize_path(path))
            if key not in inert:
                continue
            resp = ((op.get("responses") or {}).get("200") or {})
            schema = ((resp.get("content") or {}).get(
                "application/json") or {}).get("schema") or {}
            declared = _schema_props(schema, spec) & PAGING_TOTALS
            if not declared:
                continue
            findings.append({
                "op": f"GET {key[1]}",
                "commands": sorted(set(inert[key])),
                "spec": spec_file.name,
                "declares": sorted(declared),
            })

    seen = {f["op"] for f in findings}
    findings = [f for f in findings if f["op"] not in acks]
    stale = [{"op": op, "reason": " ".join(str(acks[op]).split())[:140]}
             for op in sorted(set(acks) - seen)]
    return findings, stale


# ----------------------------------------------------------------- check 18

REFERENCE_DIR = REPO / "docs" / "reference"
# docs/reference/ files that are not API reference docs and are exempt from the
# shape rules: the directory's own CLAUDE.md, its TODO list, and the migration
# spec TEMPLATE (a skeleton to copy, deliberately not a reference doc).
NON_REFERENCE_DOCS = {"CLAUDE.md", "TODO.md", "migration-spec-template.md"}

_FENCE = re.compile(r"^\s*(```|~~~)", re.M)
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_INDOC_LINK = re.compile(r"\]\(#([^)]+)\)")


def strip_fences(text: str) -> str:
    """Blank out fenced code blocks, preserving line count.

    Both harvests below must ignore fences: a bash example's `# comment` is not
    a heading, and a `](#anchor)` inside a fence is sample text, not a live
    link. Lines are replaced rather than removed so reported line numbers stay
    true to the file.
    """
    out, in_fence, marker = [], False, ""
    for line in text.split("\n"):
        hit = _FENCE.match(line)
        if hit and not in_fence:
            in_fence, marker = True, hit.group(1)
            out.append("")
            continue
        if in_fence:
            out.append("")
            if line.strip().startswith(marker):
                in_fence = False
            continue
        out.append(line)
    return "\n".join(out)


def heading_slugs(body: str) -> set[str]:
    """Every anchor GitHub would mint for this document's headings.

    Mirrors GitHub's slugger: strip inline code and link syntax, drop emphasis
    and punctuation, lowercase, spaces to hyphens. Repeated heading text gets
    the `-1`, `-2` … suffixes GitHub appends, so both forms are accepted.
    """
    slugs, seen = set(), {}
    for line in body.split("\n"):
        m = _HEADING.match(line)
        if not m:
            continue
        text = m.group(2)
        text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)   # [label](url) -> label
        text = text.replace("`", "")
        text = re.sub(r"[*_~]", "", text)
        text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
        base = re.sub(r"\s", "-", text.strip().lower())
        n = seen.get(base, 0)
        seen[base] = n + 1
        slugs.add(base if n == 0 else f"{base}-{n}")
        slugs.add(base)
    return slugs


def check_reference_doc_shape(
        reference_dir: Path = None) -> tuple[list, list]:
    """Structural conformance of docs/reference/**, per that directory's CLAUDE.md.

    Two tiers, and the split is the whole point. GATED are the rules every
    reference doc already satisfies and that a machine can judge with no
    taste involved:

      * every in-document `](#anchor)` lands on a heading in the same file
      * the file ends with exactly one newline
      * a `## See Also` section exists

    The anchor rule is the one with teeth. It is the only check in this gate
    that reads a doc as a DOCUMENT rather than as a carrier of wxcli commands,
    and it catches a rot nothing else can see: devices-core.md's contents list
    pointed at `#5-raw-http` and `#6-gotchas` while the headings had long since
    become `## 6.` and `## 7.`, so four links silently landed nowhere. That
    was hand-repaired once (commit a016cea) and drifted straight back, which
    is the argument for checking it mechanically instead of by eye.

    ADVISORY are conventions with real exceptions on disk — a doc may
    legitimately have no gotchas to record, and a short one needs no contents
    list. They are reported so a gap is visible, never failed, because a gate
    that fails on a judgement call is a gate someone switches off.
    """
    root = REFERENCE_DIR if reference_dir is None else Path(reference_dir)
    failures, advisories = [], []
    for path in sorted(root.glob("*.md")):
        if path.name in NON_REFERENCE_DOCS:
            continue
        raw = path.read_text()
        body = strip_fences(raw)
        slugs = heading_slugs(body)
        h2 = [_HEADING.match(ln).group(2).strip() for ln in body.split("\n")
              if _HEADING.match(ln) and _HEADING.match(ln).group(1) == "##"]
        lower = [h.lower() for h in h2]

        for n, line in enumerate(body.split("\n"), 1):
            for anchor in _INDOC_LINK.findall(line):
                if anchor not in slugs:
                    failures.append({"file": f"docs/reference/{path.name}",
                                     "line": n, "kind": "dead anchor",
                                     "detail": f"](#{anchor}) matches no heading"})

        trailing = len(raw) - len(raw.rstrip("\n"))
        if trailing != 1:
            failures.append({
                "file": f"docs/reference/{path.name}",
                "line": raw.count("\n") + 1, "kind": "trailing newlines",
                "detail": f"file ends with {trailing} newline(s), expected 1"})

        if not any("see also" in h for h in lower):
            failures.append({"file": f"docs/reference/{path.name}", "line": 0,
                             "kind": "missing section",
                             "detail": "no `## See Also` section"})
        elif "see also" not in lower[-1]:
            advisories.append({"file": f"docs/reference/{path.name}",
                               "detail": f"`## See Also` is not the last section "
                                         f"(last is {h2[-1]!r})"})

        if not any(h.startswith("source") for h in lower):
            advisories.append({"file": f"docs/reference/{path.name}",
                               "detail": "no `## Sources` section"})
        if not any("gotcha" in h for h in lower):
            advisories.append({"file": f"docs/reference/{path.name}",
                               "detail": "no `## Gotchas` section"})
        if not any("table of contents" in h or h == "contents" for h in lower):
            advisories.append({"file": f"docs/reference/{path.name}",
                               "detail": f"no contents list ({len(h2)} sections)"})
    return failures, advisories


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
    dead_refs, group_refs, prefixless_refs = check_references(surface, top_level)
    count_mismatches = check_counts(surface)
    unreferenced = check_unreferenced(group_refs)
    stale_overlays = check_overlays()
    flag_surface = build_flag_surface()
    dead_flags = check_flags(surface, flag_surface)
    prose_flags = check_prose_flags(flag_surface)
    untracked_mods = check_untracked_modules()
    # .get, not [] — a caller supplying a partial overrides dict must not crash
    # main(). Defaulting to {} is deliberately fail-CLOSED: with no authority
    # declared, every spec conflict reports as unpinned and check 9 fails, which
    # is the safe direction. Silently permissive is the bug this check exists for.
    bad_columns, wrapper_only, unpinned_specs = check_table_columns(
        authority=overrides.get("spec_authority") or {})
    positional_surface = build_positional_surface()
    bad_positionals, bare_citations = check_positionals(surface, positional_surface)
    required_surface = build_required_surface()
    missing_flags, bare_flag_citations = check_required_flags(
        surface, positional_surface, required_surface)
    kind_surface = build_arg_kind_surface()
    kind_mismatches, kind_advisories, mislabelled_args = check_arg_kinds(
        surface, positional_surface, kind_surface)
    naming_unacked, naming_stale, naming_advisory = check_naming(
        build_naming_findings(), overrides.get("naming_ack") or {})
    bad_examples, bad_skeletons, fs_audit = check_generated_help()
    inert_overrides, stale_inert_acks = check_inert_overrides()
    inert_paging, stale_paging_acks = check_undeclared_paging()
    registry_counts = check_registry_counts()
    doc_shape, doc_shape_advisory = check_reference_doc_shape()

    results = {
        "1_spec_cli_parity": parity,
        "2_dead_references": dead_refs,
        "3_count_mismatches": count_mismatches,
        "4_undeclared_unreferenced_groups": unreferenced,
        "5_stale_overlays": stale_overlays,
        "6_dead_flags": dead_flags,
        "7_prose_flags": prose_flags,
        "8_untracked_modules": untracked_mods,
        "9_table_columns": bad_columns,
        "9_wrapper_only_responses": wrapper_only,
        "9_unpinned_spec_conflicts": unpinned_specs,
        "10_positional_mismatches": bad_positionals,
        "10_bare_name_citations": bare_citations,
        "11a_missing_required_flags": missing_flags,
        "11a_bare_name_citations": bare_flag_citations,
        "11b_arg_kind_mismatches": kind_mismatches,
        "11b_arg_kind_advisories": kind_advisories,
        "11b_mislabelled_arguments": mislabelled_args,
        "12_naming_unacked": naming_unacked,
        "12_naming_stale_acks": naming_stale,
        "12_naming_advisory": naming_advisory,
        "13_unrunnable_examples": bad_examples,
        "14_truncated_skeletons": bad_skeletons,
        "14_fs_exclusion_audit": fs_audit,
        "15_inert_overrides": inert_overrides,
        "15_stale_inert_acks": stale_inert_acks,
        "16_inert_all_flag": inert_paging,
        "16_stale_paging_acks": stale_paging_acks,
        "17_registry_count_claims": registry_counts,
        "18_reference_doc_shape": doc_shape,
        "18_reference_doc_advisory": doc_shape_advisory,
    }
    failed = bool(parity["missing_from_cli"] or parity["cli_ahead_of_spec"]
                  or dead_refs or count_mismatches or unreferenced
                  or stale_overlays or dead_flags or prose_flags
                  or untracked_mods or bad_columns or unpinned_specs
                  or bad_positionals or missing_flags or kind_mismatches
                  or naming_unacked or naming_stale
                  or bad_examples or bad_skeletons or fs_audit["leaked"]
                  or inert_overrides or stale_inert_acks
                  or inert_paging or stale_paging_acks
                  or registry_counts or doc_shape)
    # kind_advisories is deliberately NOT in `failed` — tier 2 is a heuristic
    # about English, and a gate that fails on one gets switched off.

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
        print(f"[2] dead wxcli references: {len(dead_refs)}"
              f"   ({prefixless_refs} cited without the `wxcli` prefix)")
        for ref in dead_refs[:20]:
            print(f"      {ref['file']}:{ref['line']}  {ref['ref']}  (dead {ref['kind']})")
        if len(dead_refs) > 20:
            print(f"      ... and {len(dead_refs) - 20} more (--json for all)")
        print(f"[3] published-count mismatches: {len(count_mismatches)}")
        for cm in count_mismatches:
            if cm.get("contradiction"):
                print(f"      SELF-CONTRADICTION — {cm['claim']} "
                      f"(measured {cm['measured']})")
                print(f"        {cm['contradiction']}")
            else:
                print(f"      {cm['file']}:{cm['line']}: says \"{cm['claim']}\", "
                      f"measured {cm['measured']}")
        print(f"[4] unreferenced groups not on the out-of-scope list: {len(unreferenced)}")
        if unreferenced:
            print(f"      {', '.join(unreferenced)}")
        print(f"[5] stale overlays (upstream now publishes the path): {len(stale_overlays)}")
        for s in stale_overlays:
            print(f"      {s['spec']}: {s['path']} — delete this overlay entry")
        print(f"[6] non-existent flags cited: {len(dead_flags)}")
        for f in dead_flags[:20]:
            print(f"      {f['file']}:{f['line']}  {f['ref']}  {f['flag']}")
        if len(dead_flags) > 20:
            print(f"      ... and {len(dead_flags) - 20} more (--json for all)")
        print(f"[7] prose flags on no command: {len(prose_flags)}")
        for f in prose_flags[:20]:
            print(f"      {f['file']}:{f['line']}  {f['flag']}")
        if len(prose_flags) > 20:
            print(f"      ... and {len(prose_flags) - 20} more (--json for all)")
        print(f"[8] untracked modules present but not staged: {len(untracked_mods)}")
        for u in untracked_mods:
            print(f"      {u['module']}"
                  f"{' (registered in the CLI)' if u['registered'] else ''}"
                  f" — run git add src/wxcli/commands/{u['module']}.py")
        print(f"[9] list commands with columns the response cannot fill: {len(bad_columns)}"
              f"   ({len(wrapper_only)} wrapper-shaped responses excluded — no"
              f" column can fix those, use -o json)")
        for c in bad_columns[:20]:
            print(f"      wxcli {c['group']} {c['command']}  missing "
                  f"{', '.join(c['missing'])}  (have: {', '.join(c['available'][:6])})")
        if len(bad_columns) > 20:
            print(f"      ... and {len(bad_columns) - 20} more (--json for all)")
        if unpinned_specs:
            print(f"      {len(unpinned_specs)} unpinned spec conflicts — add a "
                  f"spec_authority entry in tools/field_overrides.yaml:")
            for u in unpinned_specs[:10]:
                print(f"        wxcli {u['group']} {u['command']}  {u['op']}"
                      f"  — {u['reason']}")
        print(f"[10] documented examples with a positional-argument mismatch: "
              f"{len(bad_positionals)}"
              f"   ({sum(p['prefixless'] for p in bad_positionals)} cited "
              f"without the `wxcli` prefix; {bare_citations} bare command-name "
              f"citations excluded — incomplete, not broken)")
        for p in bad_positionals[:20]:
            cite = p['cmd'] if p['prefixless'] else f"wxcli {p['cmd']}"
            print(f"      {p['file']}:{p['line']}  {cite}  "
                  f"supplied={p['supplied']} declared={p['need']}-{p['total']}"
                  f"  ({p['kind']})")
        if len(bad_positionals) > 20:
            print(f"      ... and {len(bad_positionals) - 20} more (--json for all)")
        print(f"[11a] documented examples missing a REQUIRED flag: "
              f"{len(missing_flags)}"
              f"   ({sum(f['prefixless'] for f in missing_flags)} cited without "
              f"the `wxcli` prefix; {bare_flag_citations} bare command-name "
              f"citations excluded — incomplete, not broken)")
        for f in missing_flags[:20]:
            cite = f['cmd'] if f['prefixless'] else f"wxcli {f['cmd']}"
            print(f"      {f['file']}:{f['line']}  {cite}  "
                  f"missing {' '.join(f['missing'])}")
        if len(missing_flags) > 20:
            print(f"      ... and {len(missing_flags) - 20} more (--json for all)")
        print(f"[11b] doc placeholders naming the wrong resource: "
              f"{len(kind_mismatches)}")
        for k in kind_mismatches[:20]:
            print(f"      {k['file']}:{k['line']}  wxcli {k['cmd']}  "
                  f"{k['arg']} is a {k['declared']}, cited as {k['placeholder']}"
                  f" (reads as {k['reads_as']})")
        if len(kind_mismatches) > 20:
            print(f"      ... and {len(kind_mismatches) - 20} more (--json for all)")
        print(f"[11b] ADVISORY — bare-UUID arguments whose placeholder names a "
              f"sibling command's resource: {len(kind_advisories)}"
              f"   (heuristic, never fails the build)")
        for k in kind_advisories[:20]:
            print(f"      {k['file']}:{k['line']}  wxcli {k['cmd']}  "
                  f"{k['arg']} comes from `{k['producer']}` but is cited as "
                  f"{k['placeholder']} — see `{k['cmd'].split()[0]} {k['sibling']}`")
        if len(kind_advisories) > 20:
            print(f"      ... and {len(kind_advisories) - 20} more (--json for all)")
        print(f"[11b] ADVISORY — arguments whose declared kind contradicts their "
              f"own name: {len(mislabelled_args)}"
              f"   (CLI-side; excluded from the gated count above)")
        for k in mislabelled_args[:10]:
            print(f"      wxcli {k['group']} {k['command']}  {k['arg']} is "
                  f"help-typed {k['declared']}, reads as {k['reads_as']}")
        if len(mislabelled_args) > 10:
            print(f"      ... and {len(mislabelled_args) - 10} more (--json for all)")
        print(f"[12] command names whose obvious reading is wrong, unacked: "
              f"{len(naming_unacked)}   (stale acks: {len(naming_stale)}; "
              f"{len(naming_advisory)} MEDIUM reported, not gated)")
        for n in naming_unacked[:20]:
            print(f"      wxcli {n['group']} {n['command']}  [{n['severity']}]"
                  f"  {n['url']}")
            print(f"        {n.get('why', 'numeric suffix carries no meaning')}")
            print(f"        rename via command_name_overrides (proposed: "
                  f"{n['proposed']}), or ack it in tools/field_overrides.yaml")
        if len(naming_unacked) > 20:
            print(f"      ... and {len(naming_unacked) - 20} more (--json for all)")
        for n in naming_stale[:20]:
            print(f"      STALE ACK  {n['kind']} {n['op']}  — {n['reason']}")
        print(f"[13] generated `Example:` lines that cannot succeed: "
              f"{len(bad_examples)}"
              f"   (fs_* exclusion asserted: {len(fs_audit['declared'])} declared,"
              f" {len(fs_audit['present_on_disk'])} on disk,"
              f" {len(fs_audit['leaked'])} leaked)")
        for f in bad_examples[:20]:
            print(f"      wxcli {f['group']} {f['command']}  omits "
                  f"{', '.join(f['missing'])}  ({f['spec']}: {f['operation']})")
            print(f"        {f['example']}")
        if len(bad_examples) > 20:
            print(f"      ... and {len(bad_examples) - 20} more (--json for all)")
        if fs_audit["leaked"]:
            print(f"      LEAKED dev-only modules into the counted surface: "
                  f"{', '.join(fs_audit['leaked'])}")
        print(f"[14] --generate-json-body skeletons that truncate: "
              f"{len(bad_skeletons)}")
        for s in bad_skeletons[:20]:
            print(f"      wxcli {s['group']} {s['command']}  {s['json_path']} "
                  f"is {s['spec_type']} in {s['spec']}, rendered {s['rendered']}"
                  f"  ({s['kind']})")
        if len(bad_skeletons) > 20:
            print(f"      ... and {len(bad_skeletons) - 20} more (--json for all)")
        print(f"[15] override entries that cannot apply: {len(inert_overrides)}"
              f"   (stale acks: {len(stale_inert_acks)})")
        for f in inert_overrides[:20]:
            print(f"      {f['kind'].upper():8} {f['where']}  spec={f['spec']}  "
                  f"tag={f['tag']!r}  {f['detail']}")
        if len(inert_overrides) > 20:
            print(f"      ... and {len(inert_overrides) - 20} more (--json for all)")
        for a in stale_inert_acks:
            print(f"      STALE ACK  inert_tag_ack[{a['tag']!r}] resolves now "
                  f"— delete the ack: {a['reason']}")
        print(f"[16] list commands whose `--all` is inert on a paging endpoint: "
              f"{len(inert_paging)}   (stale acks: {len(stale_paging_acks)})")
        for f in inert_paging[:20]:
            print(f"      {', '.join(f['commands'])}  {f['op']}  "
                  f"response declares {', '.join(f['declares'])}  ({f['spec']})")
        if len(inert_paging) > 20:
            print(f"      ... and {len(inert_paging) - 20} more (--json for all)")
        for a in stale_paging_acks:
            print(f"      STALE ACK  undeclared_paging_ack[{a['op']!r}] no longer "
                  f"qualifies — delete the ack: {a['reason']}")
        print(f"[17] prose counts that disagree with their registry: "
              f"{len(registry_counts)}")
        for f in registry_counts[:20]:
            print(f"      {f['where']}  {f['detail']}")
        if len(registry_counts) > 20:
            print(f"      ... and {len(registry_counts) - 20} more (--json for all)")
        print(f"[18] reference docs with a broken shape: {len(doc_shape)}")
        for f in doc_shape[:20]:
            where = f"{f['file']}:{f['line']}" if f["line"] else f["file"]
            print(f"      {where}  {f['kind']} — {f['detail']}")
        if len(doc_shape) > 20:
            print(f"      ... and {len(doc_shape) - 20} more (--json for all)")
        print(f"[18] ADVISORY — reference-doc conventions not followed: "
              f"{len(doc_shape_advisory)}   (style, never fails the build)")
        for f in doc_shape_advisory[:10]:
            print(f"      {f['file']}  {f['detail']}")
        if len(doc_shape_advisory) > 10:
            print(f"      ... and {len(doc_shape_advisory) - 10} more (--json for all)")
        print(f"\nresult: {'FAIL' if failed else 'PASS'}"
              f"{' (advisory — not enforcing)' if failed and not args.enforce else ''}")

    return 1 if (failed and args.enforce) else 0


# Exit codes are a SIGNAL, and they used to carry no information:
#   0 = ran, clean
#   1 = ran, found problems (with --enforce)
#   2 = DID NOT RUN — crashed before finishing
#
# Code 2 exists because of a real 11-day outage. `import yaml` at check 15 was
# unavailable in CI's drift-gate job, so the gate died before check 1 and
# reported nothing — and an unhandled traceback exits 1, which is byte-identical
# to "the gate ran and found problems". Four consecutive red builds were read as
# "we know why that's failing" when in fact nothing had been checked since
# 2026-07-25. A guard whose failure is indistinguishable from its success-with-
# findings is not a guard.
#
# KeyboardInterrupt and SystemExit are BaseException, not Exception, so Ctrl-C
# and main()'s own exit propagate untouched.
if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        import traceback
        traceback.print_exc()
        # Goes to stdout on purpose: `result:` is the line every reader and the
        # CI assertion greps for, so the crash must speak in the same place the
        # verdict normally does, not only in a stderr traceback.
        print("\nresult: CRASHED — the gate did not run to completion.")
        print("This is NOT a findings failure. Nothing above was verified; the "
              "checks that did not print did not run. Fix the crash, then judge "
              "the findings.")
        sys.exit(2)
