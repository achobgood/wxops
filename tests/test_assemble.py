"""Local tests for wxcli-dist/assemble.py (gitignored per the CI decision)."""
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location(
    "assemble", REPO_ROOT / "wxcli-dist" / "assemble.py"
)


def _load_assemble():
    mod = importlib.util.module_from_spec(_SPEC)
    _SPEC.loader.exec_module(mod)
    return mod


def test_curated_settings_has_wxcli_perms_only():
    curated = json.loads(
        (REPO_ROOT / "wxcli-dist" / "settings.bundled.json").read_text()
    )
    assert curated["permissions"]["allow"] == ["Bash(wxcli:*)", "Bash(which:*)"]
    assert "env" not in curated
    assert set(curated.keys()) == {"permissions", "hooks"}

    # The SessionStart hook is deliberate (326a0ab): it checks PyPI for a newer
    # wxcli. The original ban here was on a *git-fetch* hook, from when updates
    # meant pulling a clone — customer folders have no clone. Assert the shape
    # rather than the absence, so the retired git path cannot come back.
    hooks = curated["hooks"]
    assert set(hooks) == {"SessionStart"}, "only SessionStart is expected"
    commands = [
        h["command"]
        for entry in hooks["SessionStart"]
        for h in entry["hooks"]
    ]
    assert commands == ["wxcli --no-update-check update --hook"]
    for command in commands:
        assert "git" not in command, (
            f"customer folders have no clone — no git in a bundled hook: {command!r}"
        )


def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def fake_repo(tmp_path):
    """Mini repo mirroring the real tree's shipping/dev split."""
    repo = tmp_path / "repo"
    tracked = {
        "CLAUDE.md": "# Playbook\n",
        ".claude/agents/wxc-calling-builder.md":
            "---\nname: wxc-calling-builder\ndescription: Build Webex.\n"
            "model: sonnet\n---\nbody uses `/agents`.\n",
        ".claude/skills/provision-calling/SKILL.md": "skill\n",
        ".claude/skills/reporting/references/cdr.md": "nested\n",
        ".claude/rules/cleanup.md":
            '---\npaths:\n  - "src/wxcli/commands/cleanup.py"\n---\n\n# Cleanup\n',
        ".claude/settings.json": '{"hooks": {"SessionStart": []}}',
        "docs/reference/authentication.md": "auth\n",
        "docs/knowledge-base/migration/kb-webex-limits.md": "limits\n",
        "docs/runbooks/cucm-migration/operator-runbook.md": "runbook\n",
        "docs/runbooks/cucm-migration/self-review-findings.md": "internal\n",
        "docs/reference/TODO.md": "dev todo: src/wxcli\n",
        "docs/reference/migration-spec-template.md": "check src/wxcli/migration\n",
        "TODO.md": "dev notes src/\n",
        "src/wxcli/main.py": "app\n",
    }
    for rel, content in tracked.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    # untracked dev junk that must never ship. GITIGNORED, as it is in the real
    # tree — that is what keeps it out of untracked_sources() structurally
    # rather than by name, and the real tree was verified to gitignore all five
    # of its untracked playbook files on 2026-08-04.
    (repo / ".claude/skills/seven-advisors").mkdir(parents=True)
    (repo / ".claude/skills/seven-advisors/SKILL.md").write_text("dev only\n")
    (repo / ".claude/settings.local.json").write_text("{}")
    (repo / ".gitignore").write_text(
        ".claude/skills/seven-advisors/\n.claude/settings.local.json\n")
    _git(repo, "init", "-q")
    _git(repo, "add", "-f", *tracked)
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "x")
    return repo


def test_enumeration_scopes_and_excludes(fake_repo):
    A = _load_assemble()
    files = A.enumerate_sources(fake_repo)
    assert "CLAUDE.md" in files
    assert ".claude/skills/reporting/references/cdr.md" in files   # nested layout kept
    assert "TODO.md" not in files                                  # basename exclude
    assert "docs/reference/TODO.md" not in files                   # basename exclude anywhere
    assert "docs/reference/migration-spec-template.md" not in files  # explicit exclude
    assert "docs/knowledge-base/migration/kb-webex-limits.md" in files
    assert "docs/runbooks/cucm-migration/operator-runbook.md" in files
    assert "docs/runbooks/cucm-migration/self-review-findings.md" not in files
    assert ".claude/skills/seven-advisors/SKILL.md" not in files   # untracked dev skill
    assert ".claude/settings.local.json" not in files              # untracked
    assert ".claude/settings.json" not in files                    # substituted, not enumerated
    assert "src/wxcli/main.py" not in files                        # outside scope


def test_an_unstaged_playbook_file_is_reported_not_silently_omitted(fake_repo):
    """The 2026-08-04 defect. `git ls-files` cannot see an unstaged file, so a
    newly written docs/reference/*.md was dropped from the bundle while the run
    printed a file count and exited 0. Reproduced live before this fix: unstaged
    it vanished; `git add` alone (identical bytes) put it in the bundle."""
    A = _load_assemble()
    assert A.untracked_sources(fake_repo) == []          # control: clean tree
    (fake_repo / "docs/reference/new-surface.md").write_text("new\n")
    assert A.untracked_sources(fake_repo) == ["docs/reference/new-surface.md"]
    assert "docs/reference/new-surface.md" not in A.enumerate_sources(fake_repo)
    _git(fake_repo, "add", "docs/reference/new-surface.md")
    assert A.untracked_sources(fake_repo) == []
    assert "docs/reference/new-surface.md" in A.enumerate_sources(fake_repo)


def test_gitignored_dev_content_is_not_reported_as_unstaged(fake_repo):
    """Membership is on_disk - tracked - IGNORED, the same classification
    drift_check.module_state() uses. Dropping the ignore step turns every
    dev-only skill into a permanent failure and the guard gets deleted."""
    A = _load_assemble()
    assert A.untracked_sources(fake_repo) == []
    assert (fake_repo / ".claude/skills/seven-advisors/SKILL.md").exists()


def test_excluded_basenames_are_not_reported_as_unstaged(fake_repo):
    """A stray TODO.md is excluded from the bundle by design; demanding it be
    staged would be a failure with no correct resolution."""
    A = _load_assemble()
    (fake_repo / "docs/reference/TODO.md").write_text("scratch\n")
    (fake_repo / ".claude/skills/provision-calling/.DS_Store").write_bytes(b"\x00")
    assert A.untracked_sources(fake_repo) == []


def test_assemble_preserves_layout_and_substitutes_settings(fake_repo, tmp_path):
    A = _load_assemble()
    curated = tmp_path / "settings.bundled.json"
    curated.write_text('{"permissions": {"allow": ["Bash(wxcli:*)"]}}')
    bundle = tmp_path / "bundle"
    A.assemble(fake_repo, bundle, curated)
    assert (bundle / "CLAUDE.md").read_text() == "# Playbook\n"
    assert (bundle / ".claude/skills/reporting/references/cdr.md").exists()
    assert (bundle / "docs/knowledge-base/migration/kb-webex-limits.md").exists()
    assert (bundle / "docs/runbooks/cucm-migration/operator-runbook.md").exists()
    shipped = json.loads((bundle / ".claude/settings.json").read_text())
    assert "hooks" not in shipped                                  # live settings NOT shipped
    assert not (bundle / "TODO.md").exists()
    # re-run is idempotent (wipe + rebuild)
    A.assemble(fake_repo, bundle, curated)
    assert (bundle / "CLAUDE.md").exists()


def test_audit_flags_planted_tokens_with_path_and_line(tmp_path):
    A = _load_assemble()
    bundle = tmp_path / "b"
    (bundle / "docs").mkdir(parents=True)
    (bundle / "docs/x.md").write_text(
        "clean line\nsee src/wxcli/main.py\nrun python3.14 -m x\n"
        "edit tools/field_overrides.yaml\n"
    )
    got = A.audit_bundle(bundle)
    assert ("docs/x.md", 2, "src/") in got
    assert ("docs/x.md", 3, "python3.14 -m") in got
    assert ("docs/x.md", 4, "tools/") in got
    assert ("docs/x.md", 4, "field_overrides") in got


def test_audit_passes_clean_bundle(tmp_path):
    A = _load_assemble()
    bundle = tmp_path / "b"
    bundle.mkdir()
    (bundle / "CLAUDE.md").write_text("only customer-safe content\n")
    assert A.audit_bundle(bundle) == []


def test_audit_exempts_rules_frontmatter_but_not_body(tmp_path):
    A = _load_assemble()
    bundle = tmp_path / "b"
    (bundle / ".claude/rules").mkdir(parents=True)
    (bundle / ".claude/rules/cleanup.md").write_text(
        '---\npaths:\n  - "src/wxcli/commands/cleanup.py"\n---\n\nbody tools/ ref\n'
    )
    got = A.audit_bundle(bundle)
    assert (".claude/rules/cleanup.md", 6, "tools/") in got        # body still audited
    assert not any(tok == "src/" for _, _, tok in got)             # frontmatter glob exempt


def test_audit_allows_source_citations_only_in_shipped_migration_docs(tmp_path):
    A = _load_assemble()
    bundle = tmp_path / "b"
    doc = bundle / "docs/runbooks/cucm-migration/operator-runbook.md"
    doc.parent.mkdir(parents=True)
    doc.write_text("Implementation: src/wxcli/commands/cucm.py\n")
    assert A.audit_bundle(bundle) == []
    (bundle / "docs/reference/x.md").parent.mkdir(parents=True)
    (bundle / "docs/reference/x.md").write_text("src/wxcli/main.py\n")
    assert ("docs/reference/x.md", 1, "src/") in A.audit_bundle(bundle)


# ── Codex transform ────────────────────────────────────────────────────────

def test_phrase_map_rewrites_claude_isms_ordered():
    A = _load_assemble()
    src = (
        "Use `/agents` and select **wxc-calling-builder**.\n"
        "Then use SendMessage for follow-ups. See /query-live.\n"
        "Builder lives at .claude/agents/wxc-calling-builder.md and "
        "skills at .claude/skills/. Edit .claude/settings.json.\n"
        "This is a Claude Code playbook. See CLAUDE.md.\n"
    )
    out = A.apply_phrase_map(src)
    assert "SendMessage" not in out
    assert ".claude/agents/wxc-calling-builder.md" not in out
    assert ".codex/agents/wxc-calling-builder.toml" in out    # specific rule before generic
    assert ".codex/skills/" in out
    assert ".codex/config.toml" in out                         # settings.json → config.toml
    assert "Claude Code" not in out and "Codex" in out
    assert "CLAUDE.md" not in out and "AGENTS.md" in out


def test_phrase_map_slash_commands_do_not_corrupt_paths():
    """Regression: /query-live etc. are ALSO path segments in the file map."""
    A = _load_assemble()
    assert "the `query-live` skill" in A.apply_phrase_map("Use `/query-live` now.")
    assert A.apply_phrase_map("`.claude/skills/query-live/` row") == "`.codex/skills/query-live/` row"
    assert A.apply_phrase_map("`.claude/skills/cucm-migrate/`") == "`.codex/skills/cucm-migrate/`"
    assert "the agents catalog" not in A.apply_phrase_map(".claude/agents/wxc-calling-builder.md")
    assert A.apply_phrase_map(".claude/agents/wxc-calling-builder.md") == ".codex/agents/wxc-calling-builder.toml"


def test_replace_sections_swaps_body_and_fails_on_missing_anchor():
    A = _load_assemble()
    md = (
        "# Title\n\n## Keep\nkeep me\n\n"
        "### Replace Me\nold body\nmore old\n\n"
        "## After\ntail\n"
    )
    out = A.replace_sections(md, {"### Replace Me": "### Replace Me\nNEW body\n"})
    assert "old body" not in out and "NEW body" in out
    assert "keep me" in out and "tail" in out
    with pytest.raises(KeyError):
        A.replace_sections(md, {"### Nope": "x"})


def test_md_agent_to_toml_maps_model_and_wraps_body():
    import tomllib
    A = _load_assemble()
    md = (
        "---\nname: wxc-calling-builder\n"
        "description: |\n  Build Webex Calling.\n"
        "tools: Read, Bash\nmodel: sonnet\n---\n"
        "You are the builder. Use /agents to start.\n"
    )
    data = tomllib.loads(A.md_agent_to_toml(md))
    assert data["name"] == "wxc-calling-builder"
    assert data["description"].strip() == "Build Webex Calling."
    assert data["model_reasoning_effort"] == "medium"
    assert data["sandbox_mode"] == "workspace-write"
    assert "model" not in data
    assert "/agents" not in data["developer_instructions"]


def test_assemble_codex_generates_tree_agents_and_config(fake_repo, tmp_path):
    import tomllib
    A = _load_assemble()
    curated = tmp_path / "settings.bundled.json"
    curated.write_text('{"permissions": {"allow": ["Bash(wxcli:*)"]}}')
    bundle = tmp_path / "bundle"
    A.assemble(fake_repo, bundle, curated)
    # give the bundle a CLAUDE.md carrying the overlay anchors + grounding marker
    (bundle / "CLAUDE.md").write_text(
        "# Playbook\n\n## Mandatory Grounding Rule\n"
        "Never answer any question about Webex Calling from training data alone.\n\n"
        "### Agent Invocation Pattern\nold\n\n"
        "### Agent Model Selection\nold\n\n"
        "### Agent Orchestration — Long-Running Work & Silence Detection\nold\n\n"
        "## Next\ntail\n"
    )
    A.assemble_codex(bundle)
    assert (bundle / ".codex/skills/provision-calling/SKILL.md").exists()
    assert not (bundle / ".codex/docs").exists()               # docs NOT duplicated into .codex
    tomllib.loads((bundle / ".codex/agents/wxc-calling-builder.toml").read_text())
    agents_md = (bundle / "AGENTS.md").read_text()
    assert A.GROUNDING_MARKER in agents_md
    assert "Codex orchestrates subagents itself" in agents_md  # overlay section applied
    cfg = (bundle / ".codex/config.toml").read_text()
    assert 'approval_policy = "on-request"' in cfg
    assert 'sandbox_mode = "workspace-write"' in cfg


def test_audit_codex_flags_claude_isms_but_not_codex_paths(tmp_path):
    A = _load_assemble()
    b = tmp_path / "b"
    (b / ".codex/agents").mkdir(parents=True)
    (b / ".codex/agents/x.toml").write_text('developer_instructions = "ok"\n')
    (b / ".codex/skills/query-live").mkdir(parents=True)
    (b / ".codex/skills/query-live/SKILL.md").write_text("ref .codex/skills/query-live/ path\n")
    (b / "AGENTS.md").write_text("Use SendMessage and /query-live.\nSee .claude/skills.\n")
    got = A.audit_codex(b)
    pats = {tok for _, _, tok in got}
    assert any("SendMessage" in p for p in pats)
    assert any("query-live" in p for p in pats)                # the prose slash-command
    assert any(r"\.claude/" in p for p in pats)
    assert not any(rel == ".codex/agents/x.toml" for rel, _, _ in got)          # no false positive
    assert not any(rel == ".codex/skills/query-live/SKILL.md" for rel, _, _ in got)  # path not flagged
