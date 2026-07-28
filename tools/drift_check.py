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
    section = None      # "skip_tags" | "keep_endpoints" | "spec_authority" | None
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
    return {"skip_tags": skip_tags, "skip_reasons": skip_reasons,
            "keep_endpoints": keep_endpoints, "spec_authority": spec_authority}


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
    for rel in sorted(f for pat in SCAN_PATTERNS for f in tracked_files(pat)
                      if f.endswith(".md")):
        text = (REPO / rel).read_text()
        for lineno, span, in_code in code_spans(text, join_continuations=True,
                                                join_quotes=True, with_kind=True):
            for m in FLAG_CMD.finditer(span):
                group, command = m.group(1), m.group(2)
                if group in allow or f"{group} {command}" in allow:
                    continue
                if group not in surface or command not in surface[group]:
                    continue  # check 2 owns names that don't resolve
                sig = positional_surface.get(group, {}).get(command)
                if sig is None:
                    continue  # mounted sub-typer, not a leaf command
                rest = arg_region(span[m.end():], strip_comment=True)
                nxt = rest.find("wxcli")
                if nxt != -1:
                    rest = rest[:nxt]
                # A `\` immediately before an inline `# comment` is a real
                # shell line-continuation, but code_spans only recognizes one
                # when it is the line's literal last character — with prose
                # trailing it, the line is never joined and strip_comment's
                # cut leaves a bare `\` dangling. Left in, posix shlex reads
                # it as an escaped space and manufactures a phantom "" token
                # that counts as a positional on an otherwise zero-arg command.
                rest = rest.rstrip()
                if rest.endswith("\\"):
                    rest = rest[:-1].rstrip()
                try:
                    tokens = shlex.split(rest, posix=True)
                except ValueError:
                    continue  # unbalanced quote — not a tokenizable example
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
                })
    return findings, bare_count


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
    }
    failed = bool(parity["missing_from_cli"] or parity["cli_ahead_of_spec"]
                  or dead_refs or count_mismatches or unreferenced
                  or stale_overlays or dead_flags or prose_flags
                  or untracked_mods or bad_columns or unpinned_specs
                  or bad_positionals)

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
              f"   ({bare_citations} bare command-name citations excluded — "
              f"incomplete, not broken)")
        for p in bad_positionals[:20]:
            print(f"      {p['file']}:{p['line']}  wxcli {p['cmd']}  "
                  f"supplied={p['supplied']} declared={p['need']}-{p['total']}"
                  f"  ({p['kind']})")
        if len(bad_positionals) > 20:
            print(f"      ... and {len(bad_positionals) - 20} more (--json for all)")
        print(f"\nresult: {'FAIL' if failed else 'PASS'}"
              f"{' (advisory — not enforcing)' if failed and not args.enforce else ''}")

    return 1 if (failed and args.enforce) else 0


if __name__ == "__main__":
    sys.exit(main())
