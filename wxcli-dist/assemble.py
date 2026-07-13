#!/usr/bin/env python3
"""Assemble the shippable Claude Code playbook into src/wxcli/_playbook/.

"Package it" script (spec 2026-07-09 §4.1). Enumerates TRACKED sources via
`git ls-files` (never the filesystem), substitutes the curated
settings.bundled.json for the live .claude/settings.json, preserves the
repo-relative layout, then runs the link-audit gate: any residual repo-only
token fails the run. src/wxcli/_playbook/ is generated — never hand-edit it.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BUNDLE_DIR = REPO_ROOT / "src" / "wxcli" / "_playbook"
CURATED_SETTINGS = Path(__file__).resolve().parent / "settings.bundled.json"

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
]
EXCLUDE_FILES = {
    # Dev-facing spec-authoring template (19 src/ refs); its only shipping
    # referrer (.claude/rules/cucm-migration.md) is scrubbed in Task 5/B3.
    "docs/reference/migration-spec-template.md",
    # Internal review notes, not operator-facing playbook material.
    "docs/runbooks/cucm-migration/self-review-findings.md",
}
EXCLUDE_BASENAMES = {"TODO.md", ".DS_Store"}
AUDIT_TOKENS = ("src/", "tools/", "python3.14 -m", "field_overrides")
# These operator docs cite implementation files as provenance. The code is not
# shipped in an installed playbook, but the citations are explanatory rather
# than executable links; retain them while keeping the usual audit elsewhere.
SOURCE_CITATION_PREFIXES = (
    "docs/knowledge-base/migration/",
    "docs/runbooks/cucm-migration/",
)

# ── Codex playbook transform ──────────────────────────────────────────────
# The Codex shape (.codex/ + AGENTS.md) is GENERATED from the assembled Claude
# bundle; canonical .claude/ is never touched.
CODEX_OVERLAY = Path(__file__).resolve().parent / "codex"
GROUNDING_MARKER = "Never answer any question about Webex Calling from training data alone"
_EFFORT = {"opus": "high", "sonnet": "medium", "haiku": "low"}

# Ordered Claude→Codex rewrite pipeline (Codex copy only). Slash-command names
# (/agents, /query-live, /wxc-calling-debug, /cucm-migrate) are ALSO path
# segments in the file-map, so they use a regex with a negative lookbehind
# `(?<!\w)` (paths always have a word char before the slash) — a naive
# str.replace would corrupt those paths AND slip past the audit.
CODEX_PIPELINE: list[tuple[str, object, str]] = [
    ("lit", "You MUST use `/agents` and select **wxc-calling-builder**",
            "You MUST ask Codex to use the **wxc-calling-builder** agent"),
    ("lit", "`/agents` → wxc-calling-builder", "the **wxc-calling-builder** agent"),
    ("re", re.compile(r"(?<!\w)/agents\b(?!/)"), "the agents catalog"),
    ("re", re.compile(r"(?<!\w)/query-live\b"), "the `query-live` skill"),
    ("re", re.compile(r"(?<!\w)/wxc-calling-debug\b"), "the `wxc-calling-debug` skill"),
    ("re", re.compile(r"(?<!\w)/cucm-migrate\b"), "the `cucm-migrate` skill"),
    ("lit", "`SendMessage`", "a follow-up instruction to the agent"),
    ("lit", "SendMessage", "a follow-up instruction to the agent"),
    ("lit", "Claude Code", "Codex"),
    ("lit", "CLAUDE.md", "AGENTS.md"),
    ("lit", ".claude/agents/wxc-calling-builder.md", ".codex/agents/wxc-calling-builder.toml"),
    ("lit", ".claude/agents/migration-advisor.md", ".codex/agents/migration-advisor.toml"),
    ("lit", ".claude/settings.local.json", ".codex/config.toml"),
    ("lit", ".claude/settings.json", ".codex/config.toml"),
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
]


def enumerate_sources(repo_root: Path) -> list[str]:
    """Tracked playbook files minus explicit excludes.

    git ls-files already omits untracked dev-only content (seven-advisors,
    researcher, settings.local.json, docs/references/).
    """
    out = subprocess.run(
        ["git", "ls-files", "--", *INCLUDE_PATHS],
        cwd=repo_root, capture_output=True, text=True, check=True,
    ).stdout
    return [
        f for f in out.splitlines()
        if f and f not in EXCLUDE_FILES and Path(f).name not in EXCLUDE_BASENAMES
    ]


def assemble(repo_root: Path, bundle_dir: Path, curated_settings: Path) -> list[str]:
    """Wipe bundle_dir, copy sources preserving layout, substitute settings."""
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
    return violations


def main() -> int:
    files = assemble(REPO_ROOT, BUNDLE_DIR, CURATED_SETTINGS)
    assemble_codex(BUNDLE_DIR)
    violations = audit_bundle(BUNDLE_DIR)
    codex_violations = audit_codex(BUNDLE_DIR)
    if violations or codex_violations:
        for rel, lineno, tok in violations:
            print(f"LINK-AUDIT {rel}:{lineno}: residual '{tok}'", file=sys.stderr)
        for rel, lineno, tok in codex_violations:
            print(f"CODEX-AUDIT {rel}:{lineno}: residual Claude-ism /{tok}/", file=sys.stderr)
        print(f"FAILED: {len(violations) + len(codex_violations)} bad reference(s) in the bundle.",
              file=sys.stderr)
        return 1
    print(f"Assembled Claude+Codex playbook ({len(files) + 1} Claude file(s) + "
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


def replace_sections(md: str, replacements: dict[str, str]) -> str:
    """Replace each anchored section (heading + body up to the next same/higher
    heading). Missing anchor → KeyError (keeps the overlay honest)."""
    lines = md.splitlines(keepends=True)
    for anchor, new_block in replacements.items():
        start = next((i for i, ln in enumerate(lines)
                      if ln.rstrip("\n") == anchor), None)
        if start is None:
            raise KeyError(f"anchor not found in CLAUDE.md: {anchor!r}")
        level = _heading_level(anchor)
        end = len(lines)
        for j in range(start + 1, len(lines)):
            lv = _heading_level(lines[j])
            if lv and lv <= level:
                end = j
                break
        block = new_block if new_block.endswith("\n") else new_block + "\n"
        lines[start:end] = [block]
    return "".join(lines)


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


def md_agent_to_toml(md: str) -> str:
    """Convert a Claude agent .md (frontmatter + body) to a Codex agent TOML."""
    fm, body = _split_frontmatter(md)
    body = apply_phrase_map(body).rstrip("\n")
    if "'''" in body:
        raise ValueError("agent body contains ''' — cannot use TOML literal string")
    effort = _EFFORT.get(fm.get("model", "sonnet"), "medium")
    name = fm["name"].strip()
    desc = fm.get("description", "").strip().replace("\\", "\\\\").replace('"', '\\"')
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
    return md


def _write_text_or_bytes(src: Path, dest: Path, transform) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        dest.write_text(transform(src.read_text()))
    except UnicodeDecodeError:
        dest.write_bytes(src.read_bytes())


def assemble_codex(bundle_dir: Path) -> None:
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
    shutil.copy2(CODEX_OVERLAY / "config.toml", cfg_dest)


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
