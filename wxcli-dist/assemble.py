#!/usr/bin/env python3
"""Assemble the shippable Claude Code playbook into src/wxcli/_playbook/.

"Package it" script (spec 2026-07-09 §4.1). Enumerates TRACKED sources via
`git ls-files` (never the filesystem), substitutes the curated
settings.bundled.json for the live .claude/settings.json, writes the sanitized
mcp.bundled.json as .mcp.json (a live .mcp.json can hold a real token and is
never shipped), preserves the repo-relative layout, then runs the link-audit
gate: any residual repo-only token fails the run. src/wxcli/_playbook/ is
generated — never hand-edit it.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BUNDLE_DIR = REPO_ROOT / "src" / "wxcli" / "_playbook"
CURATED_SETTINGS = Path(__file__).resolve().parent / "settings.bundled.json"
# The PreToolUse gate ships, but not the development copy: that one cites repo
# paths an installed playbook does not have. Substituted the same way settings
# are — keep the POLICY identical between the two, only the guidance differs.
CURATED_HOOK = Path(__file__).resolve().parent / "wxcli-gate.bundled.sh"
# The project MCP config ships SANITIZED: placeholders only, never a token. Plan 2
# carries just the Flow Designer server (wxcc-flow-builder); wxcc's Supabase entry
# moves only with a skill that needs it (Plans 3–5).
CURATED_MCP = Path(__file__).resolve().parent / "mcp.bundled.json"

# Enumerate the three .claude subdirs explicitly — `.claude/` wholesale would
# also sweep the tracked .claude/projects/**/memory path.
INCLUDE_PATHS = [
    "CLAUDE.md",
    ".claude/agents",
    ".claude/skills",
    ".claude/rules",
    "docs/reference",
    # The CUCM migration skill and advisor read these at runtime.  They must
    # travel with `wxcli init`, not just live in a source checkout.
    "docs/knowledge-base/migration",
    "docs/runbooks/cucm-migration",
    # The builder agent reads deployment-plan.md and execution-report.md at
    # runtime (docs/playbooks/calling-build.md § Deployment plan, and the agent
    # body's § 5. Report). The agent file has always shipped; the templates it
    # points at once did not.
    "docs/templates",
    # wxcc's playbooks and FlowIR examples (wxcc's assembler shipped both,
    # wxcc/wxcc-dist/assemble.py:33-42). Plan 3 moves them in.
    "docs/playbooks",
    "docs/examples",
]
EXCLUDE_FILES = {
    # Dev-facing spec-authoring template (19 src/ refs); its only shipping
    # referrer (.claude/rules/cucm-migration.md) is scrubbed in Task 5/B3.
    "docs/reference/migration-spec-template.md",
    # Internal review notes, not operator-facing playbook material.
    "docs/runbooks/cucm-migration/self-review-findings.md",
    # Maintainer-only local context for authoring reference docs: cites tests/,
    # the drift gate and the Sync Protocol, none of which an installed playbook
    # has. Nothing an end user reads points at it.
    "docs/reference/CLAUDE.md",
    # Maintainer-only sync pairs (wxcc's Sync Checklist and Playbook ↔
    # Reference Doc Pairs; Plan 4 P4-4): cites tests/, tools/ and this file.
    ".claude/rules/doc-maintenance.md",
    # Maintainer-only test command and interpreter notes (Plan 4 P4-4).
    ".claude/rules/repo-development.md",
}
EXCLUDE_BASENAMES = {"TODO.md", ".DS_Store"}
AUDIT_TOKENS = ("src/", "tools/", "python3.14 -m", "field_overrides",
                "venv/", ".worktrees", ".superpowers", "node_modules/")
# A developer's home directory. wxcc audited the bare substring "/Users/"; that
# fires on correct API docs (SCIM `/identity/scim/{orgId}/v2/Users/{userId}`,
# `"path": "/Users/USER_ID_1"`), so it is a pattern here: "/Users/" followed by
# a lowercase account name and a slash, not preceded by a word character or `}`
# (which is how every SCIM path reaches it). Reported under HOME_DIR_TOKEN.
HOME_DIR_RE = re.compile(r"(?<![\w}])/Users/[a-z][\w.-]*/")
HOME_DIR_TOKEN = "/Users/<name>/"
# These operator docs cite implementation files as provenance. The code is not
# shipped in an installed playbook, but the citations are explanatory rather
# than executable links; retain them while keeping the usual audit elsewhere.
SOURCE_CITATION_PREFIXES = (
    "docs/knowledge-base/migration/",
    "docs/runbooks/cucm-migration/",
)

# ── Existence gate: references that name a shipped file which never shipped ──
# AUDIT_TOKENS is a DENYLIST. It can only catch a repo-only prefix that leaked
# IN; it has no way to notice a file that is MISSING. That is exactly how
# docs/templates/{deployment-plan,execution-report}.md — read at runtime by
# the builder agent (see INCLUDE_PATHS above) — stayed out of INCLUDE_PATHS for
# months while this audit, the unit tests and the wheel smoke test all passed,
# and how dangling docs/plans/ and docs/superpowers/ citations survived beside
# them. This is the complementary direction: a reference that CLAIMS to name a
# file inside the shipped tree must resolve inside the shipped tree.
#
# Deliberately scoped to docs/, .claude/ and .codex/. src/ and tools/ are the
# already-solved provenance case: audit_bundle owns them and
# SOURCE_CITATION_PREFIXES already rules on where a src/ citation is intended.
# Re-judging them here would either duplicate that ruling or contradict it. A
# docs/→docs/ reference has no such ambiguity — both sides claim to be
# shipped-tree paths, so it should always resolve.
REF_PREFIXES = ("docs/", ".claude/", ".codex/")

# A reference carrying any of these is a PATTERN, not a filename — a glob, a
# fill-in-the-blank, or a date stamp. Checking it for existence is meaningless
# (`docs/reference/*.md`, `docs/knowledge-base/migration/<doc>.md`).
REF_PLACEHOLDER_RE = re.compile(r"[*?<>{}\[\]|]|YYYY|MM-DD")

# Paths a shipped file names on purpose even though the bundle does not, and
# must not, contain them. EXACT matches, never prefixes, and each entry states
# why. A `docs/plans/` prefix rule was tried first and rejected: it also
# swallowed `docs/plans/cucm-pipeline/02b-cucm-extraction.md`, one of the two
# real dangling citations this gate exists to catch. Exempting the write-target
# itself keeps the surrounding tree audited.
REF_EXEMPT = {
    "docs/plans":
        "WRITE-target directory, not a read. The builder agent CREATES the "
        "deployment plan here inside the customer's own folder (the agent "
        "body's § 2. Plan; docs/playbooks/calling-build.md § Deployment plan). "
        "Nothing reads it out of the bundle, so its absence at build time is "
        "correct.",
    "docs/plans/session-state.md":
        "WRITE-target. The builder agent's compaction-recovery state file, "
        "written per run (the agent body's § After a context reset).",
    "docs/demo/2026-04-22-acme":
        "WRITE-target. The worked example of --output-dir for the cucm-migrate "
        "customer deliverables bundle (.claude/skills/cucm-migrate/SKILL.md).",
    "docs/spec-sync-contract.md":
        "Repo-only by design, and CLAUDE.md's file-map row already says so "
        "inline: '(repo-only — present in a source checkout, not in an "
        "installed playbook)'. Kept as a pointer for whoever reads the source.",
}

# Plan 3 (P3-3): wxcc's shipped docs cite repo-local vetting evidence that was
# never tracked in wxcc-agent-builder either. Cited as provenance, never read at
# runtime; one exact entry per target (open question 1 of Plan 3).
_LOCAL_FINDINGS_REASON = (
    "Repo-local vetting evidence from wxcc-agent-builder (never tracked there "
    "either); cited as provenance, not read at runtime. Plan 3 P3-3; open "
    "question 1.")
_LOCAL_PLAN_REASON = (
    "Repo-local wxcc audit plan, cited as provenance; not shipped. Plan 3 P3-3.")
REF_EXEMPT.update({
    f"docs/tests/findings/{name}-findings.md": _LOCAL_FINDINGS_REASON
    for name in (
        "digital-inbound-agent", "inbound-sms", "inbound-voice",
        "multi-channel-routing", "outbound-apple-messages", "outbound-email",
        "outbound-rcs", "outbound-sms", "outbound-whatsapp",
        "sequential-dialing", "skill-build-scripted-fulfillment",
        "webex-calling-paging", "webhook-triggers")
})
REF_EXEMPT.update({
    path: _LOCAL_PLAN_REASON for path in (
        "docs/plans/2026-07-25-documentation-remediation-backlog.md",
        "docs/plans/2026-07-25-findings-corpus-audit.md",
        "docs/plans/2026-07-25-webex-connect-doc-audit.md",
        "docs/plans/2026-07-27-reference-sweep-triage-ledger.md",
        "docs/plans/spec-a-voice-nodes-reference.md")
})

_REF_BACKTICK_RE = re.compile(r"`([^`\n]+)`")
_REF_MDLINK_RE = re.compile(r"\]\(([^)\s]+)\)")
# Bare prose mentions (113 of them in the bundle) — no backticks, no link.
_REF_BARE_RE = re.compile(
    r"(?<![`\w/(])((?:docs|\.claude|\.codex)/[^\s`)\]]*\.(?:md|json|py|sh|ya?ml))"
)
# `.claude/agents/migration-advisor.md:136` and `…:188-200` cite a line range,
# not a file named "…md:136".
_REF_LINE_CITE_RE = re.compile(r":\d+(?:-\d+)?$")

# ── Codex playbook transform ──────────────────────────────────────────────
# The Codex shape (.codex/ + AGENTS.md) is GENERATED from the assembled Claude
# bundle; canonical .claude/ is never touched.
CODEX_OVERLAY = Path(__file__).resolve().parent / "codex"
# The Codex PreToolUse gate is wired here, and unlike the Claude side it ships
# no script: the handler calls `wxcli codex-gate`. Codex hands a hook no
# project-dir variable and FAILS OPEN when a hook cannot execute, so a script
# path that does not resolve is a silent no-gate rather than an error —
# resolving the installed binary on PATH is the only form with no path to get
# wrong. The inline fallback in the handler covers wxcli being off PATH.
CODEX_HOOKS = CODEX_OVERLAY / "hooks.json"
GROUNDING_MARKER = "Never answer any question about Webex Calling from training data alone"
_EFFORT = {"opus": "high", "sonnet": "medium", "haiku": "low"}

# Ordered Claude→Codex rewrite pipeline (Codex copy only). Slash-command names
# (/agents, /query-live, /wxc-calling-debug, /cucm-migrate) are ALSO path
# segments in the file-map, so they use a regex with a negative lookbehind
# `(?<!\w)` (paths always have a word char before the slash) — a naive
# str.replace would corrupt those paths AND slip past the audit.
CODEX_PIPELINE: list[tuple[str, object, str]] = [
    # A stray reference to the retired WxCC agent is rewritten to the agent
    # that replaced it (Plan 5); the pattern still matches the old name.
    ("re", re.compile(r"(?<!\w)/wxcc-agent-builder\b"), "the **wxops** agent"),
    ("re", re.compile(r"(?<!\w)/wxcc-debug\b"), "the `wxcc-debug` skill"),
    ("re", re.compile(r"Skill\(([a-z][a-z-]*)\)"), r"the `\1` skill"),
    ("re", re.compile(r"(?<!\w)/agents\b(?!/)"), "the agents catalog"),
    ("re", re.compile(r"(?<!\w)/query-live\b"), "the `query-live` skill"),
    ("re", re.compile(r"(?<!\w)/wxc-calling-debug\b"), "the `wxc-calling-debug` skill"),
    ("re", re.compile(r"(?<!\w)/cucm-migrate\b"), "the `cucm-migrate` skill"),
    ("lit", "`SendMessage`", "a follow-up instruction to the agent"),
    ("lit", "SendMessage", "a follow-up instruction to the agent"),
    ("lit", "Claude Code", "Codex"),
    ("lit", "CLAUDE.md", "AGENTS.md"),
    ("lit", ".claude/agents/wxops.md", ".codex/agents/wxops.toml"),
    ("lit", ".claude/agents/migration-advisor.md", ".codex/agents/migration-advisor.toml"),
    ("lit", ".claude/agents/wxcc-agent-builder.md", ".codex/agents/wxops.toml"),
    ("lit", ".claude/settings.local.json", ".codex/config.toml"),
    ("lit", ".claude/settings.json", ".codex/config.toml"),
    # Codex configures MCP in .codex/config.toml, not the Claude-only root .mcp.json
    ("lit", ".mcp.json", ".codex/config.toml"),
    ("lit", ".claude/", ".codex/"),   # generic path prefix — safe (always a prefix)
]

# Residual Claude-isms that must NOT survive into the Codex outputs. Slash-command
# patterns carry the same path-guard so a legit `.codex/skills/query-live/` path
# is not falsely flagged.
CODEX_FORBIDDEN = [
    re.compile(r"SendMessage"),
    re.compile(r"(?<!\w)/query-live\b"),
    re.compile(r"(?<!\w)/wxc-calling-debug\b"),
    re.compile(r"(?<!\w)/cucm-migrate\b"),
    re.compile(r"Claude Code"),
    re.compile(r"CLAUDE\.md"),
    re.compile(r"\.claude/"),
    re.compile(r"(?<!\w)/agents\b(?!/)"),
    re.compile(r"\.mcp\.json"),
    re.compile(r"(?<!\w)/wxcc-agent-builder\b"),
    re.compile(r"(?<!\w)/wxcc-debug\b"),
    re.compile(r"Skill\([a-z][a-z-]*\)"),
]

# Our own cap on AGENTS.md (Plan 4 decision P4-14). Codex reads only the first
# project_doc_max_bytes of it (default 32,768; measured on Codex 0.163.0), so the
# shipped codex/config.toml raises that to 65,536, honoured once the folder is
# trusted. A test pins config value >= this cap; build_agents_md fails above it.
CODEX_AGENTS_MD_MAX_BYTES = 44000
CODEX_AGENTS_MD_WARN_BYTES = 42000

# CLAUDE.md sections moved out of AGENTS.md into .codex/docs/ files, anchor ->
# destination path. Empty until Plan 4 (wxcc's table is keyed to headings of wxcc's
# own CLAUDE.md, which has not merged yet).
EXTRACTED_SECTIONS: dict[str, str] = {}


def _keep(rel: str) -> bool:
    return bool(rel) and rel not in EXCLUDE_FILES and Path(rel).name not in EXCLUDE_BASENAMES


def enumerate_sources(repo_root: Path) -> list[str]:
    """Tracked playbook files minus explicit excludes.

    Tracked, not on-disk, and that is correct: the bundle must be reproducible
    from a fresh clone. What was WRONG is doing it silently — see
    untracked_sources().
    """
    out = subprocess.run(
        ["git", "ls-files", "--", *INCLUDE_PATHS],
        cwd=repo_root, capture_output=True, text=True, check=True,
    ).stdout
    return [f for f in out.splitlines() if _keep(f)]


def untracked_sources(repo_root: Path) -> list[str]:
    """Playbook files present on disk, not gitignored, and not yet `git add`ed.

    This script enumerates with `git ls-files`, so a doc you have written but
    not staged is invisible to it — and it used to say nothing: `Assembled … 91
    Claude file(s)`, exit 0, file absent from the bundle. Reproduced 2026-08-04
    with a new docs/reference/*.md: unstaged it was silently dropped, and `git
    add` alone (identical bytes) put it in the bundle and correctly failed the
    link audit. A build step that reports success while omitting a file is the
    same defect drift_check's check 8 exists for, one layer over.

    Membership is `on_disk - tracked - ignored`, exactly as drift_check's
    module_state() classifies command modules — and for the same reason: index
    membership is the wrong proxy for "dev-only". The five untracked playbook
    files on disk today (seven-advisors, researcher, settings.local.json) are
    all gitignored, so they stay out structurally rather than by name.
    """
    tracked = set(enumerate_sources(repo_root))
    on_disk: set[str] = set()
    for rel in INCLUDE_PATHS:
        p = repo_root / rel
        if p.is_file():
            on_disk.add(rel)
        elif p.is_dir():
            on_disk.update(str(f.relative_to(repo_root))
                           for f in p.rglob("*") if f.is_file())
    extra = sorted(f for f in on_disk - tracked if _keep(f))
    if not extra:
        return []
    ignored = set(subprocess.run(
        ["git", "check-ignore", "--stdin"], input="\n".join(extra),
        cwd=repo_root, capture_output=True, text=True,
    ).stdout.split("\n"))
    return [f for f in extra if f not in ignored]


def assemble(repo_root: Path, bundle_dir: Path, curated_settings: Path,
             curated_hook: Path = CURATED_HOOK,
             curated_mcp: Path = CURATED_MCP) -> list[str]:
    """Wipe bundle_dir, copy sources preserving layout, substitute settings+hook,
    and write the sanitized MCP config as .mcp.json."""
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    files = enumerate_sources(repo_root)
    for rel in files:
        dest = bundle_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(repo_root / rel, dest)
    settings_dest = bundle_dir / ".claude" / "settings.json"
    settings_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(curated_settings, settings_dest)
    # settings.bundled.json wires PreToolUse to this path; shipping one without
    # the other is a silent no-op gate, so they move together.
    hook_dest = bundle_dir / ".claude" / "hooks" / "wxcli-gate.sh"
    hook_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(curated_hook, hook_dest)
    hook_dest.chmod(0o755)
    shutil.copy2(curated_mcp, bundle_dir / ".mcp.json")
    return files


def _body_start(rel: str, lines: list[str]) -> int:
    """Rules frontmatter is exempt: its paths: globs (src/...) are Claude Code
    activation metadata — inert in a customer folder, not broken references."""
    if rel.startswith((".claude/rules/", ".codex/rules/")) and lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return i + 1
    return 0


def audit_bundle(bundle_dir: Path) -> list[tuple[str, int, str]]:
    """Every (relpath, lineno, token) repo-only reference left in the bundle."""
    violations: list[tuple[str, int, str]] = []
    for path in sorted(bundle_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(bundle_dir).as_posix()
        lines = path.read_text(errors="replace").splitlines()
        tokens = AUDIT_TOKENS
        if rel.startswith(SOURCE_CITATION_PREFIXES):
            tokens = tuple(tok for tok in AUDIT_TOKENS if tok != "src/")
        for i in range(_body_start(rel, lines), len(lines)):
            for tok in tokens:
                if tok in lines[i]:
                    violations.append((rel, i + 1, tok))
            if HOME_DIR_RE.search(lines[i]):
                violations.append((rel, i + 1, HOME_DIR_TOKEN))
    return violations


def _normalize_ref(raw: str) -> str | None:
    """Reduce one cited reference to a path, or None if it is not checkable.

    Handles the four citation shapes the docs actually use: `path`,
    `path#anchor`, `path:120` / `path:188-200`, and `path § Some Section`.
    """
    raw = raw.strip()
    if not raw:
        return None
    ref = raw.split()[0].split("#", 1)[0]
    ref = _REF_LINE_CITE_RE.sub("", ref)
    ref = ref.rstrip(".,;:)").rstrip("/")
    if not ref or REF_PLACEHOLDER_RE.search(ref):
        return None
    return ref


def _line_refs(line: str) -> list[tuple[str, bool]]:
    """(raw reference, resolve-relative-to-the-citing-file) pairs on one line."""
    found: list[tuple[str, bool]] = []
    for m in _REF_MDLINK_RE.finditer(line):
        target = m.group(1)
        if not target.startswith(("http://", "https://", "mailto:", "#")):
            found.append((target, True))
    for m in _REF_BACKTICK_RE.finditer(line):
        span = m.group(1).strip()
        if span.startswith(REF_PREFIXES):
            found.append((span, False))
    for m in _REF_BARE_RE.finditer(line):
        found.append((m.group(1), False))
    return found


def audit_missing_references(bundle_dir: Path) -> list[tuple[str, int, str]]:
    """Every (relpath, lineno, reference) naming a shipped-tree file that is
    not in the bundle. The missing-file direction audit_bundle cannot see."""
    violations: list[tuple[str, int, str]] = []
    seen: set[tuple[str, int, str]] = set()
    root = bundle_dir.resolve()

    for path in sorted(bundle_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(bundle_dir).as_posix()
        try:
            lines = path.read_text().splitlines()
        except UnicodeDecodeError:
            continue
        for i, line in enumerate(lines, 1):
            for raw, file_relative in _line_refs(line):
                ref = _normalize_ref(raw)
                if ref is None:
                    continue
                base = path.parent if file_relative else root
                resolved = (base / ref).resolve()
                try:
                    target = resolved.relative_to(root).as_posix()
                except ValueError:
                    # Escapes the bundle entirely — an installed playbook has
                    # no parent tree to climb into, so this can never resolve.
                    target = None
                if target in REF_EXEMPT:
                    continue
                if resolved.exists():
                    continue
                key = (rel, i, ref)
                if key not in seen:
                    seen.add(key)
                    violations.append(key)
    return violations


def main() -> int:
    # Before assembling, not after: the run must not report a file count that
    # silently excludes work sitting in the working tree.
    unstaged = untracked_sources(REPO_ROOT)
    if unstaged:
        for rel in unstaged:
            print(f"UNSTAGED {rel}", file=sys.stderr)
        print(f"FAILED: {len(unstaged)} playbook file(s) on disk but not staged. "
              f"The bundle is enumerated with `git ls-files` so it stays "
              f"reproducible from a clone — these would be silently omitted. "
              f"Run `git add` on them, or gitignore them if they are dev-only.",
              file=sys.stderr)
        return 1
    files = assemble(REPO_ROOT, BUNDLE_DIR, CURATED_SETTINGS)
    assemble_codex(BUNDLE_DIR)
    violations = audit_bundle(BUNDLE_DIR)
    codex_violations = audit_codex(BUNDLE_DIR)
    missing = audit_missing_references(BUNDLE_DIR)
    if violations or codex_violations or missing:
        for rel, lineno, tok in violations:
            print(f"LINK-AUDIT {rel}:{lineno}: residual '{tok}'", file=sys.stderr)
        for rel, lineno, tok in codex_violations:
            print(f"CODEX-AUDIT {rel}:{lineno}: residual Claude-ism /{tok}/", file=sys.stderr)
        for rel, lineno, ref in missing:
            print(f"REF-AUDIT {rel}:{lineno}: cites '{ref}', which is not in the "
                  f"bundle. Add its source dir to INCLUDE_PATHS, fix the "
                  f"reference, or exempt it in REF_EXEMPT with a reason.",
                  file=sys.stderr)
        print(f"FAILED: {len(violations) + len(codex_violations) + len(missing)} "
              f"bad reference(s) in the bundle.", file=sys.stderr)
        return 1
    print(f"Assembled Claude+Codex playbook ({len(files) + 2} Claude file(s) + "
          f"generated .codex/ + AGENTS.md) into {BUNDLE_DIR.relative_to(REPO_ROOT)}")
    return 0


def apply_phrase_map(text: str) -> str:
    """Rewrite Claude-specific invocation phrasing for the Codex copy. Slash-command
    rules never touch path segments (negative lookbehind on a word char)."""
    for kind, a, b in CODEX_PIPELINE:
        text = a.sub(b, text) if kind == "re" else text.replace(a, b)
    return text


def _heading_level(line: str) -> int:
    n = 0
    for ch in line:
        if ch == "#":
            n += 1
        else:
            break
    return n if (n and line[n:n + 1] == " ") else 0


def _section_bounds(lines: list[str], anchor: str,
                    stops: frozenset[str] = frozenset()) -> tuple[int, int]:
    """(start, end) of the anchored block: heading + body up to the next
    same-or-higher heading, or the next heading in `stops` (another anchored
    section), whichever comes first. Lines inside ``` fences are never headings.
    Missing anchor → KeyError (keeps the overlay honest)."""
    start = next((i for i, ln in enumerate(lines)
                  if ln.rstrip("\n") == anchor), None)
    if start is None:
        raise KeyError(f"anchor not found in CLAUDE.md: {anchor!r}")
    level = _heading_level(anchor)
    end, fenced = len(lines), False
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        lv = _heading_level(lines[j])
        if lv and (lv <= level or lines[j].rstrip("\n") in stops):
            end = j
            break
    return start, end


def replace_sections(md: str, replacements: dict[str, str]) -> str:
    """Replace each anchored section (heading + body up to the next same/higher
    heading, or up to another anchored section it contains). Missing anchor →
    KeyError (keeps the overlay honest)."""
    lines = md.splitlines(keepends=True)
    for anchor, new_block in replacements.items():
        start, end = _section_bounds(lines, anchor, frozenset(replacements) - {anchor})
        block = new_block if new_block.endswith("\n") else new_block + "\n"
        lines[start:end] = block.splitlines(keepends=True)
    return "".join(lines)


def extract_section(md: str, anchor: str) -> str:
    """The anchored block (heading + body), unchanged. Missing anchor → KeyError."""
    lines = md.splitlines(keepends=True)
    start, end = _section_bounds(lines, anchor)
    return "".join(lines[start:end])


def _split_frontmatter(md: str) -> tuple[dict[str, str], str]:
    """Return (scalar-frontmatter dict, body). Handles `key: value` and `key: |`
    block scalars; ignores list keys (tools/allowed-tools)."""
    if not md.startswith("---\n"):
        raise ValueError("agent file missing frontmatter")
    end = md.index("\n---\n", 4)
    head, body = md[4:end], md[end + 5:]
    fm: dict[str, str] = {}
    lines = head.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line or line[0] in " -":
            i += 1
            continue
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()
        if val == "|":
            buf: list[str] = []
            i += 1
            while i < len(lines) and (lines[i].startswith(" ") or not lines[i]):
                buf.append(lines[i].strip())
                i += 1
            fm[key] = " ".join(b for b in buf if b)
            continue
        if val:
            fm[key] = val
        i += 1
    return fm, body


# Codex validates custom-agent names and, when one is invalid, SILENTLY IGNORES
# the profile — no warning, no error. A user who asks for the agent gets a
# generic one carrying none of the playbook rules, and nothing says so.
# Measured 2026-08-10: Codex 0.144.1 rejected hyphenated names, so
# the builder agent did not load there at all; 0.147.0 accepts them. The rule
# below is 0.147's ("lowercase ASCII letters, digits, or hyphens").
#
# This check exists because the failure is silent at RUNTIME, on the user's
# machine, in the shipped bundle. Failing the build instead is the only place the
# mistake is visible to us. Same reasoning as the link audit.
#
# This validates the agent's DEFINITION name, which may carry hyphens (0.163.0
# loads `probe-hy`). The spawn-time `task_name` is a different field with a
# stricter rule (lowercase letters, digits and underscores); do not "fix" this
# regex to match it.
CODEX_AGENT_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def _validate_codex_agent_name(name: str) -> str:
    if not CODEX_AGENT_NAME_RE.fullmatch(name):
        raise ValueError(
            f"agent name {name!r} is not a valid Codex custom-agent name. "
            f"Codex accepts lowercase ASCII letters, digits and hyphens; an "
            f"invalid name is SILENTLY IGNORED at runtime, so the agent would "
            f"ship and never load. Rename the agent in .claude/agents/."
        )
    return name


def md_agent_to_toml(md: str) -> str:
    """Convert a Claude agent .md (frontmatter + body) to a Codex agent TOML."""
    fm, body = _split_frontmatter(md)
    body = apply_phrase_map(body).rstrip("\n")
    if "'''" in body:
        raise ValueError("agent body contains ''' — cannot use TOML literal string")
    effort = _EFFORT.get(fm.get("model", "sonnet"), "medium")
    name = _validate_codex_agent_name(fm["name"].strip())
    desc = apply_phrase_map(fm.get("description", "").strip()).replace(
        "\\", "\\\\").replace('"', '\\"')
    return (
        f'name = "{name}"\n'
        f'description = "{desc}"\n'
        f'model_reasoning_effort = "{effort}"\n'
        f'sandbox_mode = "workspace-write"\n'
        f"developer_instructions = '''\n{body}\n'''\n"
    )


def _load_overlay_sections() -> dict[str, str]:
    text = (CODEX_OVERLAY / "agents-md-sections.md").read_text()
    parts = re.split(r"<!-- @section: (.*?) -->\n", text)
    return {parts[i].strip(): parts[i + 1].rstrip() + "\n"
            for i in range(1, len(parts), 2)}


def build_agents_md(claude_md: str) -> str:
    md = replace_sections(claude_md, _load_overlay_sections())
    md = apply_phrase_map(md)
    if GROUNDING_MARKER not in md:
        raise ValueError("grounding rule not preserved verbatim in AGENTS.md")
    size = len(md.encode("utf-8"))
    if size > CODEX_AGENTS_MD_MAX_BYTES:
        raise ValueError(f"AGENTS.md is {size} bytes, over the {CODEX_AGENTS_MD_MAX_BYTES}-byte "
                         f"cap (P4-14; shrink CLAUDE.md, or raise the cap with the shipped "
                         f"codex/config.toml project_doc_max_bytes)")
    if size > CODEX_AGENTS_MD_WARN_BYTES:
        print(f"WARNING: AGENTS.md is {size} bytes, nearing the "
              f"{CODEX_AGENTS_MD_MAX_BYTES}-byte cap", file=sys.stderr)
    return md


def _write_text_or_bytes(src: Path, dest: Path, transform) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        dest.write_text(transform(src.read_text()))
    except UnicodeDecodeError:
        dest.write_bytes(src.read_bytes())


# HTTP MCP servers whose Codex bearer token comes from an env var instead of a
# static in-file header — keeps the real token OUT of the shipped project file.
# Maps server name -> env var Codex reads at runtime. WEBEX_ACCESS_TOKEN is the
# var wxcli resolves first (auth.py), so one sign-in serves both (spec §10.3;
# wxcc named it WXCC_FLOW_TOKEN). DO NOT revert this to a static token header —
# test_mcp_servers_toml_translates_sanitized_bundle guards it.
_CODEX_HTTP_BEARER_ENV = {"wxcc-flow-builder": "WEBEX_ACCESS_TOKEN"}


def _mcp_servers_toml(curated_mcp: Path, enabled: set[str] | None = None) -> str:
    """Translate the SANITIZED mcp.bundled.json (never a live .mcp.json — it can
    hold a real token) into a Codex [mcp_servers] TOML fragment.
    Unknown server shapes fail assembly loudly rather than ship broken.
    `enabled` is the Claude side's enabledMcpjsonServers: a server outside it ships
    `enabled = false`, so Codex does not start it either (Plan 5 P5-14: the
    Supabase entry is switched off until the user fills in its placeholders)."""
    data = json.loads(curated_mcp.read_text())

    def q(s: str) -> str:
        if '"' in s or "\\" in s or "\n" in s:
            raise ValueError(f"MCP value needs escaping not supported here: {s!r}")
        return f'"{s}"'

    out = [
        "",
        "# MCP servers — generated from wxcli-dist/mcp.bundled.json. HTTP servers listed",
        "# in _CODEX_HTTP_BEARER_ENV use bearer_token_env_var so Codex sources the token",
        "# from an env var at runtime (no secret in this file); WEBEX_ACCESS_TOKEN is the",
        "# same var wxcli reads first. Other servers ship sanitized placeholders.",
    ]
    for name, cfg in data["mcpServers"].items():
        out.append(f"[mcp_servers.{name}]")
        if "command" in cfg:
            out.append(f'command = {q(cfg["command"])}')
            out.append(f'args = [{", ".join(q(a) for a in cfg.get("args", []))}]')
            if cfg.get("env"):
                pairs = ", ".join(f"{q(k)} = {q(v)}" for k, v in cfg["env"].items())
                out.append(f"env = {{ {pairs} }}")
        elif "url" in cfg:
            out.append(f'url = {q(cfg["url"])}')
            env_var = _CODEX_HTTP_BEARER_ENV.get(name)
            if env_var:
                out.append(f"bearer_token_env_var = {q(env_var)}")
            elif cfg.get("headers"):
                pairs = ", ".join(f"{q(k)} = {q(v)}" for k, v in cfg["headers"].items())
                out.append(f"http_headers = {{ {pairs} }}")
        else:
            raise ValueError(f"unsupported MCP server shape for {name!r}: {sorted(cfg)}")
        if enabled is not None and name not in enabled:
            out.append("enabled = false")
        out.append("")
    return "\n".join(out)


def _enabled_mcp_servers(bundle_dir: Path) -> set[str] | None:
    """The bundle's Claude enabledMcpjsonServers, or None when it declares none."""
    settings = bundle_dir / ".claude" / "settings.json"
    if not settings.is_file():
        return None
    names = json.loads(settings.read_text()).get("enabledMcpjsonServers")
    return None if names is None else set(names)


def assemble_codex(bundle_dir: Path, curated_mcp: Path = CURATED_MCP) -> None:
    """Transform the assembled Claude bundle into the Codex shape, in place."""
    claude = bundle_dir / ".claude"
    sk_src = claude / "skills"
    if sk_src.is_dir():
        for p in sorted(sk_src.rglob("*")):
            if p.is_file():
                _write_text_or_bytes(
                    p, bundle_dir / ".codex/skills" / p.relative_to(sk_src),
                    apply_phrase_map)
    ru_src = claude / "rules"
    if ru_src.is_dir():
        for p in sorted(ru_src.rglob("*")):
            if p.is_file():
                _write_text_or_bytes(
                    p, bundle_dir / ".codex/rules" / p.relative_to(ru_src),
                    apply_phrase_map)
    ag_src = claude / "agents"
    if ag_src.is_dir():
        for p in sorted(ag_src.glob("*.md")):
            dest = bundle_dir / ".codex/agents" / (p.stem + ".toml")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(md_agent_to_toml(p.read_text()))
    (bundle_dir / "AGENTS.md").write_text(
        build_agents_md((bundle_dir / "CLAUDE.md").read_text()))
    cfg_dest = bundle_dir / ".codex/config.toml"
    cfg_dest.parent.mkdir(parents=True, exist_ok=True)
    cfg_dest.write_text((CODEX_OVERLAY / "config.toml").read_text()
                        + _mcp_servers_toml(curated_mcp, _enabled_mcp_servers(bundle_dir)))
    # config.toml documents the gate; hooks.json is what actually arms it.
    # Shipping the prose without the wiring is a gate that reads as a gate and
    # is not one — the same defect the Claude side pins with its settings/hook
    # pairing, so they move together here too.
    shutil.copy2(CODEX_HOOKS, bundle_dir / ".codex/hooks.json")


def audit_codex(bundle_dir: Path) -> list[tuple[str, int, str]]:
    """Residual Claude-isms in generated Codex outputs (.codex/** + AGENTS.md)."""
    out: list[tuple[str, int, str]] = []
    targets = [bundle_dir / "AGENTS.md"]
    cx = bundle_dir / ".codex"
    if cx.is_dir():
        targets += [p for p in sorted(cx.rglob("*")) if p.is_file()]
    for path in targets:
        if not path.is_file():
            continue
        rel = path.relative_to(bundle_dir).as_posix()
        try:
            lines = path.read_text().splitlines()
        except UnicodeDecodeError:
            continue
        for i, line in enumerate(lines):
            for pat in CODEX_FORBIDDEN:
                if pat.search(line):
                    out.append((rel, i + 1, pat.pattern))
    return out


if __name__ == "__main__":
    sys.exit(main())
