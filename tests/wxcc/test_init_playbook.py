"""Tests for `wxcli init` (src/wxcli/commands/init_playbook.py).

Invokes the real command surface on the main Typer app so registration in
main.py is exercised too. bundle_root() is monkeypatched to a fake installed
bundle so tests never depend on the generated src/wxcli/_playbook/.
"""
import json

import pytest
from typer.testing import CliRunner

import wxcli.commands.init_playbook as I
from wxcli.main import app

runner = CliRunner()
MANIFEST = ".claude/.wxops-manifest.json"


@pytest.fixture
def bundle(tmp_path, monkeypatch):
    """Fake installed _playbook/ (incl. hidden .mcp.json + .claude/) + patched bundle_root()."""
    b = tmp_path / "_playbook"
    for rel, text in {
        "CLAUDE.md": "# Playbook\n",
        ".mcp.json": '{"mcpServers": {}}\n',
        ".claude/settings.json": '{"permissions": {"allow": ["Bash(wxcli:*)"]}}',
        ".claude/agents/wxcc-agent-builder.md": "agent\n",
        ".claude/skills/design-flow/SKILL.md": "skill v1\n",
        "docs/reference/flow-designer-essentials.md": "ref\n",
        "docs/playbooks/wxcc-setup.md": "playbook\n",
    }.items():
        p = b / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    # Codex profile (mirrors what assemble_codex generates)
    (b / "AGENTS.md").write_text("# agents instructions\n")
    (b / ".codex" / "agents").mkdir(parents=True)
    (b / ".codex" / "agents" / "wxcc-agent-builder.toml").write_text('name = "x"\n')
    (b / ".codex" / "rules").mkdir(parents=True)
    (b / ".codex" / "rules" / "r.md").write_text("rule\n")
    (b / ".codex" / "config.toml").write_text('approval_policy = "on-request"\n')
    (b / ".codex" / "skills" / "sk").mkdir(parents=True)
    (b / ".codex" / "skills" / "sk" / "SKILL.md").write_text("skill\n")
    monkeypatch.setattr(I, "bundle_root", lambda: b)
    return b


def _init(*args):
    return runner.invoke(app, ["init", *args])


def _registered_opts(cmd_name):
    """Flags registered on a top-level command — robust to typer/rich help
    rendering, which colorizes flag text and can break literal substring matches
    on newer typer/rich versions."""
    import typer
    click_app = typer.main.get_command(app)
    return {opt for p in click_app.commands[cmd_name].params for opt in p.opts}


def test_init_command_registered_on_main_app():
    """The flat registration in main.py exposes `init` with its flags."""
    r = runner.invoke(app, ["init", "--help"])
    assert r.exit_code == 0, r.output
    opts = _registered_opts("init")
    assert "--uninstall" in opts and "--force" in opts


def test_fresh_init_writes_tree_and_manifest(bundle, tmp_path):
    pb = tmp_path / "pb"
    r = _init(str(pb), "--yes")
    assert r.exit_code == 0, r.output
    # layout mirrors the repo → references resolve from folder root
    assert (pb / "CLAUDE.md").exists()
    assert (pb / ".mcp.json").exists()                       # hidden bundle-root file lands
    assert (pb / "docs/playbooks/wxcc-setup.md").exists()    # playbooks included
    m = json.loads((pb / MANIFEST).read_text())
    assert m["wxops_playbook"] is True and "version" in m
    assert set(m["files"]) == {
        "CLAUDE.md", ".mcp.json", ".claude/settings.json",
        ".claude/agents/wxcc-agent-builder.md",
        ".claude/skills/design-flow/SKILL.md",
        "docs/reference/flow-designer-essentials.md",
        "docs/playbooks/wxcc-setup.md",
    }
    assert "fresh session" in r.output


def test_first_init_into_nonempty_folder_aborts_with_collision_list(bundle, tmp_path):
    pb = tmp_path / "pb"
    (pb / "CLAUDE.md").parent.mkdir(parents=True)
    (pb / "CLAUDE.md").write_text("the user's own file\n")
    r = _init(str(pb))
    assert r.exit_code == 1
    assert "CLAUDE.md" in r.output                            # names the colliding path
    assert (pb / "CLAUDE.md").read_text() == "the user's own file\n"  # untouched


def test_first_init_force_overwrites_collisions(bundle, tmp_path):
    pb = tmp_path / "pb"
    pb.mkdir()
    (pb / "CLAUDE.md").write_text("old\n")
    r = _init(str(pb), "--force")
    assert r.exit_code == 0, r.output
    assert (pb / "CLAUDE.md").read_text() == "# Playbook\n"


def test_user_file_survives_force_refresh_and_uninstall(bundle, tmp_path):
    """Required manifest-ownership guarantee: a user-created file is untouched by
    BOTH `init --force` (refresh) and `--uninstall`; owned files refresh/retire."""
    pb = tmp_path / "pb"
    assert _init(str(pb), "--yes").exit_code == 0
    (pb / "my-notes.md").write_text("mine\n")                # user-added, unowned
    (pb / "CLAUDE.md").write_text("locally edited\n")        # owned, drifted

    # new bundle version: a skill retired, CLAUDE.md changed
    (bundle / "CLAUDE.md").write_text("# Playbook v2\n")
    (bundle / ".claude/skills/design-flow/SKILL.md").unlink()

    r = _init(str(pb), "--force")                            # refresh
    assert r.exit_code == 0, r.output
    assert (pb / "CLAUDE.md").read_text() == "# Playbook v2\n"        # owned → refreshed
    assert not (pb / ".claude/skills/design-flow/SKILL.md").exists()  # retired → removed
    assert (pb / "my-notes.md").read_text() == "mine\n"              # unowned → survives --force

    r = _init(str(pb), "--uninstall")
    assert r.exit_code == 0, r.output
    assert not (pb / "CLAUDE.md").exists()                           # owned → removed
    assert not (pb / MANIFEST).exists()
    assert (pb / "my-notes.md").read_text() == "mine\n"             # unowned → survives --uninstall


def test_uninstall_without_manifest_errors(bundle, tmp_path):
    pb = tmp_path / "pb"
    pb.mkdir()
    assert _init(str(pb), "--uninstall").exit_code == 1


# ── Both-profile init ────────────────────────────────────────────────────

def test_classify_profiles():
    assert I.classify("CLAUDE.md") == "claude"
    assert I.classify(".claude/skills/a/SKILL.md") == "claude"
    assert I.classify(".mcp.json") == "claude"
    assert I.classify("AGENTS.md") == "codex"
    assert I.classify(".codex/config.toml") == "codex"
    assert I.classify(".codex/skills/a/SKILL.md") == "codex"
    assert I.classify("docs/reference/x.md") == "shared"


def test_default_init_writes_both_profiles(bundle, tmp_path):
    folder = tmp_path / "f"
    res = _init(str(folder), "--yes")
    assert res.exit_code == 0
    for p in ("CLAUDE.md", "AGENTS.md", ".mcp.json", ".codex/config.toml",
              ".codex/skills/sk/SKILL.md",
              ".claude/.wxops-manifest.json", ".codex/.wxops-manifest.json"):
        assert (folder / p).exists(), p
    cm = json.loads((folder / ".claude/.wxops-manifest.json").read_text())
    xm = json.loads((folder / ".codex/.wxops-manifest.json").read_text())
    assert cm["profile"] == "claude" and xm["profile"] == "codex"
    assert not any(r.startswith(".codex/") or r == "AGENTS.md"
                   for r in cm["files"])
    assert not any(r.startswith(".claude/") or r in ("CLAUDE.md", ".mcp.json")
                   for r in xm["files"])
    assert any(r.startswith("docs/") for r in cm["files"])   # shared in both
    assert any(r.startswith("docs/") for r in xm["files"])


def test_claude_only_and_codex_only(bundle, tmp_path):
    c = tmp_path / "c"
    assert _init(str(c), "--claude-only", "--yes").exit_code == 0
    assert (c / "CLAUDE.md").exists() and not (c / "AGENTS.md").exists()
    assert not (c / ".codex").exists()
    x = tmp_path / "x"
    assert _init(str(x), "--codex-only", "--yes").exit_code == 0
    assert (x / "AGENTS.md").exists() and not (x / "CLAUDE.md").exists()
    assert not (x / ".claude").exists() and not (x / ".mcp.json").exists()
    assert (x / "docs").is_dir()


def test_mutually_exclusive_flags_rejected(bundle, tmp_path):
    res = _init(str(tmp_path / "f"), "--claude-only", "--codex-only")
    assert res.exit_code == 1


def test_uninstall_one_profile_keeps_shared_docs(bundle, tmp_path):
    folder = tmp_path / "f"
    _init(str(folder), "--yes")
    res = _init(str(folder), "--codex-only", "--uninstall")
    assert res.exit_code == 0
    assert not (folder / "AGENTS.md").exists()
    assert not (folder / ".codex").exists()
    assert (folder / "docs").is_dir()                      # still owned by claude
    assert (folder / "CLAUDE.md").exists()
    res2 = _init(str(folder), "--claude-only", "--uninstall")
    assert res2.exit_code == 0
    assert not (folder / "docs").exists()                  # last owner gone
    assert not (folder / "CLAUDE.md").exists()


def test_refresh_one_profile_leaves_other_untouched(bundle, tmp_path):
    folder = tmp_path / "f"
    _init(str(folder), "--yes")
    marker = folder / "AGENTS.md"
    before = marker.read_bytes()
    assert _init(str(folder), "--claude-only", "--force").exit_code == 0
    assert marker.read_bytes() == before


def test_adding_second_profile_does_not_clobber_user_file(bundle, tmp_path):
    """Incremental adoption: claude installed first, then an explicit codex add
    must NOT silently overwrite a user's own file sitting at a codex path.
    (Plain/no-flag init now refreshes only installed profiles, so the collision
    guard here fires on the EXPLICIT --codex-only add, not a plain init.)"""
    folder = tmp_path / "f"
    assert _init(str(folder), "--claude-only", "--yes").exit_code == 0
    (folder / "AGENTS.md").write_text("mine — keep\n")      # user's own file, unowned
    res = _init(str(folder), "--codex-only", "--yes")        # explicitly add codex
    assert res.exit_code == 1                                # aborts on collision
    assert "AGENTS.md" in res.output
    assert (folder / "AGENTS.md").read_text() == "mine — keep\n"   # untouched
    res2 = _init(str(folder), "--codex-only", "--force")     # --force lets it through
    assert res2.exit_code == 0
    assert (folder / "AGENTS.md").read_text() != "mine — keep\n"   # now overwritten


def test_plain_refresh_on_claude_only_folder_refreshes_only_claude(bundle, tmp_path):
    """No profile flag on an existing folder refreshes only what's installed — an
    upgrade never silently adds the other profile."""
    folder = tmp_path / "f"
    assert _init(str(folder), "--claude-only", "--yes").exit_code == 0
    assert not (folder / "AGENTS.md").exists()
    r = _init(str(folder), "--force")
    assert r.exit_code == 0
    assert (folder / "CLAUDE.md").exists()
    assert not (folder / "AGENTS.md").exists()
    assert not (folder / ".codex").exists()
    assert not (folder / ".codex/.wxops-manifest.json").exists()


def test_plain_refresh_on_codex_only_folder_refreshes_only_codex(bundle, tmp_path):
    folder = tmp_path / "f"
    assert _init(str(folder), "--codex-only", "--yes").exit_code == 0
    r = _init(str(folder), "--force")
    assert r.exit_code == 0
    assert (folder / "AGENTS.md").exists()
    assert not (folder / "CLAUDE.md").exists() and not (folder / ".claude").exists()
    assert not (folder / ".mcp.json").exists()


def test_explicit_flag_adds_second_profile_then_plain_refresh_covers_both(bundle, tmp_path):
    folder = tmp_path / "f"
    assert _init(str(folder), "--claude-only", "--yes").exit_code == 0
    assert _init(str(folder), "--codex-only", "--yes").exit_code == 0   # explicitly add codex
    assert (folder / "CLAUDE.md").exists() and (folder / "AGENTS.md").exists()
    r = _init(str(folder), "--force")                                    # both installed → both
    assert r.exit_code == 0
    assert (folder / "CLAUDE.md").exists() and (folder / "AGENTS.md").exists()


# ── .mcp.json ownership (Plan 2 Task 13; Review Focus 4) ─────────────────

def test_user_mcp_json_is_a_collision_without_force(bundle, tmp_path):
    pb = tmp_path / "pb"
    pb.mkdir()
    (pb / ".mcp.json").write_text('{"mcpServers": {"mine": {}}}\n')   # the user's own
    r = _init(str(pb), "--yes")                                        # --yes is not --force
    assert r.exit_code == 1
    assert ".mcp.json" in r.output
    assert (pb / ".mcp.json").read_text() == '{"mcpServers": {"mine": {}}}\n'
    assert not (pb / "CLAUDE.md").exists()                             # aborted before any write

    (pb / "my-notes.md").write_text("mine\n")
    r = _init(str(pb), "--force")
    assert r.exit_code == 0, r.output
    assert (pb / ".mcp.json").read_text() == '{"mcpServers": {}}\n'    # replaced
    assert ".mcp.json" in json.loads((pb / MANIFEST).read_text())["files"]

    assert _init(str(pb), "--uninstall").exit_code == 0
    assert not (pb / ".mcp.json").exists()                             # the manifest-owned copy goes
    assert (pb / "my-notes.md").read_text() == "mine\n"                # user files stay


def test_refresh_does_not_overwrite_unowned_mcp_json(bundle, tmp_path):
    pb = tmp_path / "pb"
    shipped = (bundle / ".mcp.json").read_text()
    (bundle / ".mcp.json").unlink()                          # an older bundle: no .mcp.json
    assert _init(str(pb), "--yes").exit_code == 0
    assert ".mcp.json" not in json.loads((pb / MANIFEST).read_text())["files"]
    (pb / ".mcp.json").write_text('{"mcpServers": {"mine": {}}}\n')   # the user's own
    (bundle / ".mcp.json").write_text(shipped)               # upgrade: bundle now ships it
    (bundle / "CLAUDE.md").write_text("# Playbook v2\n")
    r = _init(str(pb), "--yes")                              # refresh; --yes is not --force
    assert r.exit_code == 1
    assert ".mcp.json" in r.output
    assert (pb / ".mcp.json").read_text() == '{"mcpServers": {"mine": {}}}\n'
    assert (pb / "CLAUDE.md").read_text() == "# Playbook\n"  # aborted before any write
    r = _init(str(pb), "--force")
    assert r.exit_code == 0, r.output
    assert (pb / ".mcp.json").read_text() == shipped
    assert ".mcp.json" in json.loads((pb / MANIFEST).read_text())["files"]
