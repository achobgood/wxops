import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from wxcli.commands import init_playbook as I

runner = CliRunner()
MANIFEST = ".claude/.wxops-manifest.json"


@pytest.fixture
def bundle(tmp_path, monkeypatch):
    """Fake installed _playbook/ + a target folder; bundle_root() patched."""
    b = tmp_path / "_playbook"
    for rel, text in {
        "CLAUDE.md": "# Playbook\n",
        ".claude/settings.json": '{"permissions": {"allow": ["Bash(wxcli:*)"]}}',
        ".claude/skills/provision-calling/SKILL.md": "skill v1\n",
        "docs/reference/authentication.md": "auth doc\n",
    }.items():
        p = b / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    monkeypatch.setattr(I, "bundle_root", lambda: b)
    return b


def _init(*args):
    return runner.invoke(I.app, list(args))


def test_fresh_init_writes_tree_and_manifest(bundle, tmp_path):
    pb = tmp_path / "pb"
    r = _init(str(pb), "--yes")
    assert r.exit_code == 0, r.output
    # spec §4.3: layout mirrors the repo → references resolve from folder root
    assert (pb / "CLAUDE.md").exists()
    assert (pb / "docs/reference/authentication.md").exists()
    m = json.loads((pb / MANIFEST).read_text())
    assert m["wxops_playbook"] is True and "version" in m
    assert set(m["files"]) == {
        "CLAUDE.md", ".claude/settings.json",
        ".claude/skills/provision-calling/SKILL.md",
        "docs/reference/authentication.md",
    }
    assert "fresh session" in r.output          # post-init Claude Code notice


def test_first_init_into_nonempty_folder_aborts_with_collision_list(bundle, tmp_path):
    pb = tmp_path / "pb"
    (pb / "CLAUDE.md").parent.mkdir(parents=True)
    (pb / "CLAUDE.md").write_text("the user's own file\n")
    r = _init(str(pb))
    assert r.exit_code == 1
    assert "CLAUDE.md" in r.output              # names the colliding path
    assert (pb / "CLAUDE.md").read_text() == "the user's own file\n"  # untouched


def test_first_init_force_overwrites_collisions(bundle, tmp_path):
    pb = tmp_path / "pb"
    pb.mkdir(); (pb / "CLAUDE.md").write_text("old\n")
    r = _init(str(pb), "--force")
    assert r.exit_code == 0, r.output
    assert (pb / "CLAUDE.md").read_text() == "# Playbook\n"


def test_refresh_replaces_deletes_owned_and_spares_user_files(bundle, tmp_path):
    pb = tmp_path / "pb"
    assert _init(str(pb), "--yes").exit_code == 0
    (pb / "my-notes.md").write_text("mine\n")                    # user-added
    (pb / "CLAUDE.md").write_text("locally edited\n")            # owned, drifted
    # new bundle version: skill retired, CLAUDE.md changed
    (bundle / "CLAUDE.md").write_text("# Playbook v2\n")
    (bundle / ".claude/skills/provision-calling/SKILL.md").unlink()
    r = _init(str(pb), "--yes")
    assert r.exit_code == 0, r.output
    assert (pb / "CLAUDE.md").read_text() == "# Playbook v2\n"   # owned → replaced
    assert not (pb / ".claude/skills/provision-calling/SKILL.md").exists()  # retired → deleted
    assert (pb / "my-notes.md").read_text() == "mine\n"          # non-owned → untouched


def test_uninstall_removes_exactly_manifest_set(bundle, tmp_path):
    pb = tmp_path / "pb"
    assert _init(str(pb), "--yes").exit_code == 0
    (pb / "my-notes.md").write_text("mine\n")
    r = _init(str(pb), "--uninstall")
    assert r.exit_code == 0, r.output
    assert not (pb / "CLAUDE.md").exists()
    assert not (pb / MANIFEST).exists()
    assert (pb / "my-notes.md").exists()                         # user file survives


def test_uninstall_without_manifest_errors(bundle, tmp_path):
    pb = tmp_path / "pb"; pb.mkdir()
    assert _init(str(pb), "--uninstall").exit_code == 1


# ── Codex profile (both-by-default, per-profile manifests) ─────────────────

@pytest.fixture
def bundle_both(tmp_path, monkeypatch):
    """Fake installed _playbook/ with BOTH Claude and Codex shapes + shared docs."""
    b = tmp_path / "_playbook"
    for rel, text in {
        "CLAUDE.md": "# Playbook\n",
        "AGENTS.md": "# Playbook (Codex)\n",
        ".claude/settings.json": '{"permissions": {"allow": ["Bash(wxcli:*)"]}}',
        ".claude/skills/provision-calling/SKILL.md": "skill v1\n",
        ".codex/config.toml": 'approval_policy = "on-request"\n',
        ".codex/skills/provision-calling/SKILL.md": "skill v1\n",
        "docs/reference/authentication.md": "auth doc\n",
    }.items():
        p = b / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    monkeypatch.setattr(I, "bundle_root", lambda: b)
    return b


def test_default_init_writes_both_profiles(bundle_both, tmp_path):
    pb = tmp_path / "pb"
    r = _init(str(pb), "--yes")
    assert r.exit_code == 0, r.output
    assert (pb / "CLAUDE.md").exists() and (pb / "AGENTS.md").exists()
    assert (pb / ".codex/config.toml").exists()
    assert (pb / ".claude/.wxops-manifest.json").exists()
    assert (pb / ".codex/.wxops-manifest.json").exists()
    assert (pb / "docs/reference/authentication.md").exists()   # shared, written once


def test_codex_only_skips_claude(bundle_both, tmp_path):
    pb = tmp_path / "pb"
    assert _init(str(pb), "--yes", "--codex-only").exit_code == 0
    assert (pb / "AGENTS.md").exists()
    assert not (pb / "CLAUDE.md").exists()
    assert not (pb / ".claude/.wxops-manifest.json").exists()
    assert (pb / ".codex/.wxops-manifest.json").exists()


def test_uninstall_codex_only_keeps_claude_and_docs(bundle_both, tmp_path):
    pb = tmp_path / "pb"
    assert _init(str(pb), "--yes").exit_code == 0
    assert _init(str(pb), "--uninstall", "--codex-only").exit_code == 0
    assert not (pb / "AGENTS.md").exists()
    assert not (pb / ".codex/config.toml").exists()
    assert (pb / "CLAUDE.md").exists()                          # claude stays
    assert (pb / "docs/reference/authentication.md").exists()   # shared kept (claude owns it)
    assert not (pb / ".codex/.wxops-manifest.json").exists()
    assert (pb / ".claude/.wxops-manifest.json").exists()


def test_claude_and_codex_only_conflict(bundle_both, tmp_path):
    pb = tmp_path / "pb"
    r = _init(str(pb), "--claude-only", "--codex-only")
    assert r.exit_code == 1
    assert "at most one" in r.output
