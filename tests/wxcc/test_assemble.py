"""Tests for the ONE assembler, wxcli-dist/assemble.py — enumeration scope,
curated substitution, the link-audit gate, byte-identical idempotency, and the
Codex transform. Ported from wxcc's suite (Plan 2 Tasks 7 and 12); wxcc's own
assembler is not loaded here any more."""
import hashlib
import importlib.util
import json
import re
import subprocess
import tomllib
from pathlib import Path

import pytest

from tests.wxcc.conftest import REPO

# Held files: Supabase MCP entry + wxcc's settings. Frozen copies of
# wxcc-dist/settings.bundled.json and mcp.bundled.json, kept when `wxcc/` was
# removed (Plan 6).
WXCC_DIST = REPO / "tests" / "wxcc" / "fixtures" / "wxcc_dist_held"
WXCLI_DIST = REPO / "wxcli-dist"
_SPEC = importlib.util.spec_from_file_location(
    "wxcli_assemble", WXCLI_DIST / "assemble.py"
)


def _load_assemble():
    mod = importlib.util.module_from_spec(_SPEC)
    _SPEC.loader.exec_module(mod)
    return mod


def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _tree_digest(root):
    return [
        (p.relative_to(root).as_posix(), hashlib.sha256(p.read_bytes()).hexdigest())
        for p in sorted(root.rglob("*")) if p.is_file()
    ]


# A JWT starts `eyJ`, a Supabase PAT `sbp_`; a Webex PAT is a long run of
# base64/hex/uuid characters. 40+ such characters with no `.`, `/` or space is
# token-shaped, and no curated file has a legitimate one.
_TOKEN_LIKE = re.compile(r"eyJ|sbp_|[A-Za-z0-9_\-]{40,}")
# A `Bearer` value is only ever a YOUR_* placeholder in a curated file.
_BEARER_VALUE = re.compile(r"Bearer\s+(\S+)")


def _curated_files(root=WXCLI_DIST):
    """Every file under `root` that SHIPS: tracked, or untracked-but-not-ignored,
    minus code (`.py`). `git ls-files --cached --others --exclude-standard` skips
    gitignored binaries (`.DS_Store`, `__pycache__/*.pyc`) that a used checkout
    accumulates and that the assembler never copies."""
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z", "."],
        cwd=root, check=True, capture_output=True, text=True).stdout
    return sorted(root / rel for rel in out.split("\0")
                  if rel and (root / rel).is_file() and not rel.endswith(".py"))


def test_curated_files_skip_gitignored_binaries(tmp_path):
    """Regression: a planted ignored non-UTF-8 binary must not enter the scan."""
    _git(tmp_path, "init", "-q")
    (tmp_path / ".gitignore").write_text(".DS_Store\n__pycache__/\n")
    (tmp_path / "mcp.bundled.json").write_text("{}")
    (tmp_path / "code.py").write_text("x = 1\n")
    (tmp_path / ".DS_Store").write_bytes(b"\xed\xff\x00bad")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "junk.pyc").write_bytes(b"\xed\xff\x00bad")
    (tmp_path / "new-untracked.json").write_text("{}")
    names = [p.name for p in _curated_files(tmp_path)]
    assert names == [".gitignore", "mcp.bundled.json", "new-untracked.json"]


def test_curated_configs_are_customer_safe():
    files = _curated_files()
    assert WXCLI_DIST / "mcp.bundled.json" in files
    assert WXCLI_DIST / "settings.bundled.json" in files
    for path in files:
        text = path.read_text()
        rel = path.relative_to(REPO).as_posix()
        # Booleans, not the matches: a failing assert must name the file without
        # echoing a real token into the test log.
        # A permission entry such as "mcp__wxcc-flow-builder__get_activity_node_schema"
        # is 40+ token-alphabet characters; blank those quoted names before scanning.
        scanned = re.sub(r'"mcp__[\w-]+__\w+"', '""', text)
        token_like = _TOKEN_LIKE.search(scanned) is not None
        assert not token_like, f"token-like string in {rel}"
        placeholders_only = all(re.fullmatch(r"YOUR_[A-Z_]+\"?", v)
                                for v in _BEARER_VALUE.findall(text))
        assert placeholders_only, f"non-placeholder Bearer in {rel}"


def test_bundled_settings_carry_wxcc_permissions():
    """wxcc's curated permissions, merged into wxcli-dist/settings.bundled.json
    (Plan 2 Task 12). Replaces test_wxcc_curated_settings_shape_until_task12.
    Plan 5 (P5-14) carries the 9 Supabase allows with design-ai-agent, the skill that
    needs them; the 'supabase' server stays out of enabledMcpjsonServers and is listed in
    disabledMcpjsonServers (switched off).
    Not carried: Bash(wxcc-flow:*) / Bash(wxcc-toolkit:*) (those commands are gone)."""
    ours = json.loads((WXCLI_DIST / "settings.bundled.json").read_text())
    theirs = json.loads((WXCC_DIST / "settings.bundled.json").read_text())
    allow = ours["permissions"]["allow"]
    assert sum(1 for a in allow if a.startswith("Skill(")) == 15      # wxcc's 14 + design-ai-agent
    assert "Skill(design-ai-agent)" in allow
    assert sum(1 for a in allow if a.startswith("mcp__wxcc-flow-builder__")) == 12
    assert sum(1 for a in allow if a.startswith("mcp__supabase__")) == 9
    assert not any(a.startswith(("Bash(wxcc-flow", "Bash(wxcc-toolkit")) for a in allow)
    assert "Bash(which:*)" in allow                                  # wxcli's own allow kept
    assert ours["enabledMcpjsonServers"] == ["wxcc-flow-builder"]
    # left out of enabled, a project server still starts headless (measured, Plan 5 Step 7)
    assert ours["disabledMcpjsonServers"] == ["supabase"]
    assert "hooks" in ours                                           # hooks block unchanged
    # every carried allow is one of wxcc's, and the split of wxcc's 37 adds up
    wxcc_allow = theirs["permissions"]["allow"]
    carried = [a for a in allow if a.startswith(("Skill(", "mcp__wxcc-flow-builder__",
                                                 "mcp__supabase__"))
               and a != "Skill(design-ai-agent)"]
    assert set(carried) <= set(wxcc_allow)
    assert len(wxcc_allow) == 37 == len(carried) + 2                 # 14 + 12 + 9 carried, 2 Bash held back


def test_wxcc_held_files_keep_supabase():
    """wxcc's own files stay in place holding what Plan 2 did not carry (A1)."""
    settings = json.loads((WXCC_DIST / "settings.bundled.json").read_text())
    assert settings["enabledMcpjsonServers"] == ["supabase", "wxcc-flow-builder"]
    assert sum(1 for a in settings["permissions"]["allow"] if a.startswith("mcp__supabase__")) == 9
    mcp = json.loads((WXCC_DIST / "mcp.bundled.json").read_text())
    raw = (WXCC_DIST / "mcp.bundled.json").read_text()
    assert set(mcp["mcpServers"]) == {"supabase", "wxcc-flow-builder"}
    assert "YOUR_SUPABASE_ACCESS_TOKEN" in raw and "sbp_" not in raw


def test_bundled_mcp_carries_supabase_switched_off():
    """Plan 5 (P5-14): the Supabase entry moves with design-ai-agent, placeholders only;
    it is not in enabledMcpjsonServers (test_bundled_settings_carry_wxcc_permissions)."""
    ours = json.loads((WXCLI_DIST / "mcp.bundled.json").read_text())
    theirs = json.loads((WXCC_DIST / "mcp.bundled.json").read_text())
    raw = (WXCLI_DIST / "mcp.bundled.json").read_text()
    assert set(ours["mcpServers"]) == {"supabase", "wxcc-flow-builder"}
    assert ours["mcpServers"]["wxcc-flow-builder"] == theirs["mcpServers"]["wxcc-flow-builder"]
    assert ours["mcpServers"]["supabase"] == theirs["mcpServers"]["supabase"]
    assert "YOUR_SUPABASE_ACCESS_TOKEN" in raw and "sbp_" not in raw


@pytest.fixture
def fake_repo(tmp_path):
    """Mini repo mirroring the real tree's shipping/dev split."""
    repo = tmp_path / "repo"
    tracked = {
        "CLAUDE.md": "# Playbook\n",
        ".claude/agents/wxops.md": "agent\n",
        ".claude/skills/provision-calling/SKILL.md": "skill\n",
        ".claude/skills/reporting/references/notes.md": "nested\n",
        ".claude/settings.json": '{"hooks": {"SessionStart": []}}',
        "docs/reference/authentication.md": "ref\n",
        "docs/reference/.DS_Store": "junk\n",
        "docs/plans/session-state.md": "dev plan\n",
        "docs/templates/deployment-plan.md": "template\n",
        "src/wxcli/main.py": "app\n",
    }
    for rel, content in tracked.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    # untracked / gitignored dev junk that must never ship
    (repo / ".claude/settings.local.json").write_text("{}")
    (repo / ".mcp.json").write_text('{"mcpServers": {"supabase": {"env": {"SUPABASE_ACCESS_TOKEN": "sbp_LIVE"}}}}')
    _git(repo, "init", "-q")
    _git(repo, "add", "-f", *tracked)
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "x")
    return repo


def test_enumeration_scopes_and_excludes(fake_repo):
    A = _load_assemble()
    files = A.enumerate_sources(fake_repo)
    assert "CLAUDE.md" in files
    assert ".claude/skills/reporting/references/notes.md" in files     # nested layout kept
    assert "docs/templates/deployment-plan.md" in files                # templates included
    assert "docs/plans/session-state.md" not in files                  # outside include scope
    assert "docs/reference/.DS_Store" not in files                     # basename exclude
    assert ".claude/settings.local.json" not in files                 # untracked
    assert ".claude/settings.json" not in files                       # substituted, not enumerated
    assert ".mcp.json" not in files                                   # live secret, never enumerated
    assert "src/wxcli/main.py" not in files                           # outside include scope


def test_assemble_substitutes_settings_and_mcp(fake_repo, tmp_path):
    A = _load_assemble()
    curated_s = tmp_path / "s.json"
    curated_s.write_text('{"permissions": {"allow": ["Bash(wxcc-flow:*)"]}}')
    bundle = tmp_path / "bundle"
    A.assemble(fake_repo, bundle, curated_s)
    assert (bundle / "CLAUDE.md").read_text() == "# Playbook\n"
    assert (bundle / ".claude/skills/reporting/references/notes.md").exists()
    shipped = json.loads((bundle / ".claude/settings.json").read_text())
    assert "hooks" not in shipped                                     # live settings NOT shipped
    mcp = (bundle / ".mcp.json").read_bytes()
    assert mcp == (WXCLI_DIST / "mcp.bundled.json").read_bytes()      # curated mcp shipped as-is
    assert b"sbp_LIVE" not in mcp                                     # live .mcp.json never shipped
    assert not (bundle / "docs/reference/.DS_Store").exists()
    # an explicit curated file wins over the default
    curated_m = tmp_path / "m.json"
    curated_m.write_text('{"mcpServers": {}}')
    A.assemble(fake_repo, bundle, curated_s, curated_mcp=curated_m)
    assert (bundle / ".mcp.json").read_bytes() == curated_m.read_bytes()


def test_assemble_is_idempotent_byte_identical(fake_repo, tmp_path):
    A = _load_assemble()
    curated_s = tmp_path / "s.json"
    curated_s.write_text('{"permissions": {"allow": []}}')
    curated_m = tmp_path / "m.json"
    curated_m.write_text('{"mcpServers": {}}')
    bundle = tmp_path / "bundle"
    A.assemble(fake_repo, bundle, curated_s, curated_mcp=curated_m)
    first = _tree_digest(bundle)
    A.assemble(fake_repo, bundle, curated_s, curated_mcp=curated_m)
    second = _tree_digest(bundle)
    assert first == second and len(first) > 0


def test_audit_flags_planted_tokens_with_path_and_line(tmp_path):
    A = _load_assemble()
    bundle = tmp_path / "b"
    (bundle / "docs").mkdir(parents=True)
    (bundle / "docs/x.md").write_text(
        "clean line\n"
        "see /Users/dev/secret\n"
        "activate venv/bin\n"
        "cd node_modules/pkg\n"
        "edit tools/gen.py\n"
        "git worktree in .worktrees/p2\n"
        "notes in .superpowers/plan\n"
    )
    got = A.audit_bundle(bundle)
    assert ("docs/x.md", 2, A.HOME_DIR_TOKEN) in got
    assert ("docs/x.md", 3, "venv/") in got
    assert ("docs/x.md", 4, "node_modules/") in got
    assert ("docs/x.md", 5, "tools/") in got
    assert ("docs/x.md", 6, ".worktrees") in got
    assert ("docs/x.md", 7, ".superpowers") in got


def test_home_dir_pattern_ignores_scim_paths_but_catches_a_home_directory(tmp_path):
    """wxcc's bare "/Users/" substring would fire on correct API docs (5 files in
    the real bundle, measured 2026-10-19). The pattern needs a lowercase account
    name and a slash, and no word character or `}` before it."""
    A = _load_assemble()
    bundle = tmp_path / "b"
    (bundle / "docs").mkdir(parents=True)
    (bundle / "docs/scim.md").write_text(
        "GET /identity/scim/{orgId}/v2/Users/{userId}\n"
        '"path": "/Users/USER_ID_1"\n'
        "GET https://example.com/scim/v2/Users/jdoe/x\n")
    assert A.audit_bundle(bundle) == []                               # 0 on API docs
    (bundle / "docs/leak.md").write_text("see /Users/someone/x\n")
    assert A.audit_bundle(bundle) == [("docs/leak.md", 1, A.HOME_DIR_TOKEN)]  # 1 planted


def test_extended_audit_is_clean_on_the_real_bundle(codex_bundle):
    """Plan 2 Task 12 Step 3: the extended audit on today's bundle has no hits."""
    A, bundle = codex_bundle
    assert A.audit_bundle(bundle) == []


def test_audit_passes_clean_bundle(tmp_path):
    A = _load_assemble()
    bundle = tmp_path / "b"
    bundle.mkdir()
    # `src/` IS audited in wxcli (wxcc exempted it only for a CLAUDE.md File Map row
    # that arrives in Plan 4); a clean bundle has no repo-only prefix at all
    (bundle / "CLAUDE.md").write_text("| `wxcli people list` | list people |\n")
    assert A.audit_bundle(bundle) == []
    (bundle / "CLAUDE.md").write_text("| `src/wxcli/` | the CLI package |\n")
    assert A.audit_bundle(bundle) == [("CLAUDE.md", 1, "src/")]


def test_audit_exempts_rules_frontmatter_but_not_body(tmp_path):
    A = _load_assemble()
    bundle = tmp_path / "b"
    (bundle / ".claude/rules").mkdir(parents=True)
    (bundle / ".claude/rules/x.md").write_text(
        '---\npaths:\n  - "tools/x.py"\n---\n\nbody tools/ ref\n'
    )
    got = A.audit_bundle(bundle)
    assert (".claude/rules/x.md", 6, "tools/") in got                 # body still audited
    assert not any(ln == 3 for _, ln, _ in got)                       # frontmatter glob exempt


# ── Codex transform: phrase map ──────────────────────────────────────────

def test_phrase_map_rewrites_prose_slash_commands_not_paths():
    A = _load_assemble()
    out = A.apply_phrase_map(
        "Run `/wxcc-agent-builder` to start. Run `/wxcc-debug` to debug.\n"
        "| `.claude/skills/wxcc-debug/` | Skill: debug failing actions |\n"
        "Run /query-live, /wxc-calling-debug and /cucm-migrate.\n"
    )
    assert "/wxcc-agent-builder" not in out
    assert "the **wxops** agent" in out                 # retired agent: its successor
    assert ".codex/skills/wxcc-debug/" in out           # path segment survived intact (P2-4)
    assert "the `wxcc-debug` skill" in out
    assert "the `query-live` skill" in out and "the `cucm-migrate` skill" in out


def test_phrase_map_path_swaps_most_specific_first():
    A = _load_assemble()
    out = A.apply_phrase_map(
        ".claude/agents/wxcc-agent-builder.md and .claude/settings.json "
        "and .claude/rules/cleanup.md and .claude/anythingelse"
    )
    assert ".codex/agents/wxops.toml" in out             # retired agent: its successor
    assert ".codex/config.toml" in out
    assert ".codex/rules/cleanup.md" in out              # wxcli layout, not .codex/docs/rules
    assert ".codex/anythingelse" in out                  # generic catch-all last
    assert ".claude/" not in out
    assert A.apply_phrase_map("edit .mcp.json to add a server") == "edit .codex/config.toml to add a server"


def test_phrase_map_tool_isms():
    A = _load_assemble()
    out = A.apply_phrase_map(
        "use SendMessage to continue; YOU MUST call Skill(build-action); "
        "Claude Code loads CLAUDE.md"
    )
    assert "SendMessage" not in out
    assert "Skill(build-action)" not in out
    assert "the `build-action` skill" in out
    assert "Codex loads AGENTS.md" in out


# ── Codex transform: AGENTS.md build ─────────────────────────────────────

def test_replace_sections_swaps_anchored_block_and_errors_on_miss():
    A = _load_assemble()
    md = "# T\n\n## Keep\nbody\n\n## Swap\nold\n\n### Sub\nx\n\n## After\ny\n"
    out = A.replace_sections(md, {"## Swap": "## Swapped\nnew"})
    assert "## Swapped\nnew" in out and "old" not in out
    assert "### Sub" not in out            # ### is deeper → swallowed with the ## block
    assert "## After\ny" in out
    with pytest.raises(KeyError):
        A.replace_sections(md, {"## Missing": "z"})


def test_extract_section_returns_heading_and_body():
    A = _load_assemble()
    md = "## A\na1\n\n### K\nk1\nk2\n\n### L\nl1\n\n## B\nb1\n"
    block = A.extract_section(md, "### K")
    assert block.startswith("### K\n") and "k2" in block
    assert "l1" not in block and "## B" not in block
    with pytest.raises(KeyError):
        A.extract_section(md, "### Missing")


def test_section_bounds_ignore_hash_lines_inside_code_fences():
    """A `# comment` inside a fenced block is not a heading (Inline IDs in Commands has one)."""
    A = _load_assemble()
    md = "### K\nk1\n```bash\n# WRONG — a comment\nx=1\n```\nwhy\n## B\nb1\n"
    out = A.replace_sections(md, {"### K": "### K\nnew\n"})
    assert out == "### K\nnew\n## B\nb1\n"
    assert A.extract_section(md, "### K").endswith("why\n")


def test_replaced_section_stops_at_the_next_anchored_section():
    """`## Quick Start` holds the `###` agent sections; replacing both must not let the
    `##` block swallow the `###` ones (P4-8's Quick Start replacement, Plan 4 Step 6)."""
    A = _load_assemble()
    md = "## Q\nq\n### A\na\n### B\nb\n## R\nr\n"
    out = A.replace_sections(md, {"## Q": "## Q\nnew-q\n", "### A": "### A\nnew-a\n"})
    assert out == "## Q\nnew-q\n### A\nnew-a\n### B\nb\n## R\nr\n"
    out = A.replace_sections(md, {"### A": "### A\nnew-a\n", "## Q": "## Q\nnew-q\n"})
    assert out == "## Q\nnew-q\n### A\nnew-a\n### B\nb\n## R\nr\n"


def test_agents_md_under_codex_cap():
    """Replaces test_build_agents_md_real_claude_md_under_cap_with_pointers. wxcc's
    assembler hard-failed here; wxcli's warned until Plan 4. Plan 4 met the cap."""
    A = _load_assemble()
    claude_md = (Path(A.REPO_ROOT) / "CLAUDE.md").read_text()
    agents_md = A.build_agents_md(claude_md)
    assert A.GROUNDING_MARKER in agents_md
    assert len(agents_md.encode("utf-8")) <= A.CODEX_AGENTS_MD_MAX_BYTES


def test_agents_md_cap_constants_and_empty_extraction_table():
    A = _load_assemble()
    assert A.CODEX_AGENTS_MD_MAX_BYTES == 44000            # Plan 4 decision P4-14
    assert A.CODEX_AGENTS_MD_WARN_BYTES == 42000
    assert A.EXTRACTED_SECTIONS == {}                    # empty by Plan 4 decision P4-8


def test_build_agents_md_fails_when_over_cap():
    """Over the cap is a hard failure again (P4-14: the cap is measured and ours),
    naming the byte count."""
    A = _load_assemble()
    claude_md = (Path(A.REPO_ROOT) / "CLAUDE.md").read_text()
    padded = ("x" * 40000) + "\n" + claude_md
    with pytest.raises(ValueError, match=r"AGENTS.md is \d+ bytes, over the 44000-byte cap"):
        A.build_agents_md(padded)


def test_shipped_codex_config_reads_the_whole_agents_md():
    """P4-14: Codex reads only project_doc_max_bytes of AGENTS.md (default 32,768,
    measured on Codex 0.163.0), so the shipped config must never be the smaller number."""
    A = _load_assemble()
    cfg = tomllib.loads((Path(A.REPO_ROOT) / "wxcli-dist/codex/config.toml").read_text())
    assert cfg["project_doc_max_bytes"] == 65536
    assert cfg["project_doc_max_bytes"] >= A.CODEX_AGENTS_MD_MAX_BYTES


def test_build_agents_md_near_cap_message(capsys, monkeypatch):
    """Between the warn and max thresholds the message says 'nearing', not 'over'.
    Thresholds are patched so the real CLAUDE.md lands in the band."""
    A = _load_assemble()
    monkeypatch.setattr(A, "CODEX_AGENTS_MD_WARN_BYTES", 1000)
    monkeypatch.setattr(A, "CODEX_AGENTS_MD_MAX_BYTES", 10_000_000)
    A.build_agents_md((Path(A.REPO_ROOT) / "CLAUDE.md").read_text())
    err = capsys.readouterr().err
    assert "nearing the 10000000-byte cap" in err and "over the" not in err


# ── Codex transform: agent → TOML ────────────────────────────────────────

AGENT_MD = """---
name: test-agent
description: |
  Build things. Use SendMessage to continue the "existing" agent.
tools: Read, Edit
model: opus
---
Body here. Run `/wxcc-debug` if stuck. See .claude/skills/build-action/.
"""


def test_md_agent_to_toml_fields_and_phrase_map():
    A = _load_assemble()
    tomllib = pytest.importorskip("tomllib")
    out = A.md_agent_to_toml(AGENT_MD)
    data = tomllib.loads(out)
    assert data["name"] == "test-agent"
    assert data["model_reasoning_effort"] == "high"          # opus → high
    assert data["sandbox_mode"] == "workspace-write"
    assert "model" not in data                                # inherit Codex default
    assert "SendMessage" not in data["description"]           # description phrase-mapped
    assert '"existing"' in data["description"]                # quotes escaped, survive parse
    assert "the `wxcc-debug` skill" in data["developer_instructions"]
    assert ".codex/skills/build-action/" in data["developer_instructions"]  # P2-4 layout


def test_md_agent_to_toml_rejects_triple_quote_body():
    A = _load_assemble()
    bad = AGENT_MD.replace("Body here.", "Body ''' here.")
    with pytest.raises(ValueError, match="'''"):
        A.md_agent_to_toml(bad)


def test_real_agent_converts_and_parses():
    A = _load_assemble()
    tomllib = pytest.importorskip("tomllib")
    src = (Path(A.REPO_ROOT) / ".claude/agents/wxops.md").read_text()
    data = tomllib.loads(A.md_agent_to_toml(src))
    assert data["name"] == "wxops"
    model = A._split_frontmatter(src)[0].get("model", "sonnet")
    assert data["model_reasoning_effort"] == A._EFFORT[model]
    assert data["developer_instructions"].strip()


# ── Codex transform: MCP translation ─────────────────────────────────────

def test_mcp_servers_toml_translates_sanitized_bundle():
    """THE GUARD: the shipped Codex MCP config names an env var, never a token.
    One sign-in (spec §10.3): it is WEBEX_ACCESS_TOKEN, the var wxcli reads first."""
    A = _load_assemble()
    frag = A._mcp_servers_toml(A.CURATED_MCP)
    data = tomllib.loads(frag)
    src = json.loads(A.CURATED_MCP.read_text())
    assert set(data["mcp_servers"]) == set(src["mcpServers"]) == {"wxcc-flow-builder", "supabase"}
    fb = data["mcp_servers"]["wxcc-flow-builder"]
    assert fb["url"] == src["mcpServers"]["wxcc-flow-builder"]["url"]
    assert fb["bearer_token_env_var"] == "WEBEX_ACCESS_TOKEN"   # env-backed: no token in the file
    assert "http_headers" not in fb                              # static header replaced
    assert 'bearer_token_env_var = "WEBEX_ACCESS_TOKEN"' in frag
    assert "Bearer " not in frag
    assert "WXCC_FLOW_TOKEN" not in frag
    # Plan 5 (P5-14): Supabase carried with design-ai-agent, placeholders only
    sup = data["mcp_servers"]["supabase"]
    assert sup["env"] == {"SUPABASE_ACCESS_TOKEN": "YOUR_SUPABASE_ACCESS_TOKEN"}
    assert "YOUR_SUPABASE_PROJECT_REF" in sup["args"] and "sbp_" not in frag


def test_mcp_servers_toml_translates_command_servers(tmp_path):
    """The stdio branch: the Supabase entry (wxcc's held copy, which Plan 5 ships
    switched off) is its real input."""
    A = _load_assemble()
    held = json.loads((WXCC_DIST / "mcp.bundled.json").read_text())
    sup_src = held["mcpServers"]["supabase"]
    f = tmp_path / "mcp.json"
    f.write_text(json.dumps({"mcpServers": {"supabase": sup_src}}))
    sup = tomllib.loads(A._mcp_servers_toml(f))["mcp_servers"]["supabase"]
    assert sup["command"] == "npx"
    assert sup["args"] == sup_src["args"]
    assert sup["env"] == {"SUPABASE_ACCESS_TOKEN": "YOUR_SUPABASE_ACCESS_TOKEN"}


def test_mcp_servers_toml_rejects_unknown_shape(tmp_path):
    A = _load_assemble()
    bad = tmp_path / "mcp.json"
    bad.write_text(json.dumps({"mcpServers": {"weird": {"transport": "ws"}}}))
    with pytest.raises(ValueError, match="weird"):
        A._mcp_servers_toml(bad)


@pytest.fixture(scope="module")
def codex_bundle(tmp_path_factory):
    """The real repo's assembly incl. the Codex pass, into a temp bundle dir."""
    A = _load_assemble()
    bundle = tmp_path_factory.mktemp("bundle") / "_playbook"
    A.assemble(Path(A.REPO_ROOT), bundle, A.CURATED_SETTINGS)
    A.assemble_codex(bundle)
    return A, bundle


def test_codex_config_toml_parses_with_mcp_servers(codex_bundle):
    A, bundle = codex_bundle
    text = (bundle / ".codex/config.toml").read_text()
    data = tomllib.loads(text)
    assert data["approval_policy"] == "on-request"
    assert data["sandbox_mode"] == "workspace-write"
    assert list(data["mcp_servers"]) == ["wxcc-flow-builder", "supabase"]
    assert data["mcp_servers"]["wxcc-flow-builder"]["bearer_token_env_var"] == "WEBEX_ACCESS_TOKEN"
    assert "Bearer" not in text
    # switched off on Codex too, as on Claude (not in enabledMcpjsonServers; P5-14)
    assert "enabled" not in data["mcp_servers"]["wxcc-flow-builder"]
    assert data["mcp_servers"]["supabase"]["enabled"] is False


# ── Codex transform: full pass ───────────────────────────────────────────

def test_assemble_codex_produces_expected_tree(codex_bundle):
    A, bundle = codex_bundle
    assert (bundle / "AGENTS.md").is_file()
    assert (bundle / ".codex/config.toml").is_file()
    assert (bundle / ".codex/agents/wxops.toml").is_file()
    assert (bundle / ".codex/hooks.json").is_file()
    assert sorted(p.name for p in (bundle / ".codex/rules").iterdir()) == \
           sorted(p.name for p in (bundle / ".claude/rules").iterdir())
    # wxcli's Codex layout (P2-4), not wxcc's .agents/skills + .codex/docs/rules
    assert (bundle / ".codex/skills").is_dir()
    assert not (bundle / ".agents").exists()
    assert not (bundle / ".codex/docs").exists()          # EXTRACTED_SECTIONS is empty


def test_codex_skills_equivalence(codex_bundle):
    A, bundle = codex_bundle
    src_root = bundle / ".claude/skills"
    dst_root = bundle / ".codex/skills"
    src_files = sorted(p.relative_to(src_root) for p in src_root.rglob("*") if p.is_file())
    dst_files = sorted(p.relative_to(dst_root) for p in dst_root.rglob("*") if p.is_file())
    assert src_files == dst_files
    for rel in src_files:
        s, d = src_root / rel, dst_root / rel
        if rel.suffix == ".md":
            assert d.read_text() == A.apply_phrase_map(s.read_text()), rel
        else:
            assert d.read_bytes() == s.read_bytes(), rel   # non-text files byte-copied


def test_audit_codex_clean_on_real_bundle_and_catches_seeded_ism(codex_bundle, tmp_path):
    A, bundle = codex_bundle
    assert A.audit_codex(bundle) == []
    seeded = tmp_path / "b"
    (seeded / ".codex").mkdir(parents=True)
    (seeded / ".codex" / "x.md").write_text("Claude Code does it.\nSee .claude/skills/a/\n")
    (seeded / ".codex" / "y.md").write_text(
        "edit .mcp.json\nrun /wxcc-debug\nrun /wxcc-agent-builder\nuse Skill(build-action)\n")
    (seeded / "AGENTS.md").write_text("path .codex/skills/wxcc-debug/ is fine\n")
    hits = A.audit_codex(seeded)
    assert {(rel, line) for rel, line, _ in hits} == {
        (".codex/x.md", 1), (".codex/x.md", 2),
        (".codex/y.md", 1), (".codex/y.md", 2), (".codex/y.md", 3), (".codex/y.md", 4)}


def test_claude_half_of_bundle_unchanged_by_codex_pass(codex_bundle):
    A, bundle = codex_bundle
    fresh = bundle.parent / "claude_only"
    A.assemble(Path(A.REPO_ROOT), fresh, A.CURATED_SETTINGS)
    for p in sorted(fresh.rglob("*")):
        if p.is_file():
            rel = p.relative_to(fresh)
            assert (bundle / rel).read_bytes() == p.read_bytes(), rel
