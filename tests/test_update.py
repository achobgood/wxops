import json

import httpx
import pytest
from typer.testing import CliRunner

from wxcli.commands import update as U

runner = CliRunner()

EDITABLE_DIRECT_URL = json.dumps(
    {"url": "file:///home/u/wxops", "dir_info": {"editable": True}}
)
NONEDITABLE_DIRECT_URL = json.dumps(
    {"url": "file:///home/u/wxops", "dir_info": {"editable": False}}
)


def test_detect_editable_from_direct_url():
    assert U.detect_install_method(direct_url=EDITABLE_DIRECT_URL, prefix="/usr") == "editable"


def test_detect_editable_from_git_worktree_fallback():
    # no direct_url, but running inside a git work tree → editable
    assert U.detect_install_method(direct_url=None, prefix="/usr", in_git_worktree=True) == "editable"


def test_detect_pipx_from_prefix():
    prefix = "/home/u/.local/pipx/venvs/wxcli"
    assert U.detect_install_method(direct_url=None, prefix=prefix, in_git_worktree=False) == "pipx"


def test_detect_plain_pip():
    # in_git_worktree=False is required: the repo under test has a .git, so the live
    # fallback would otherwise classify this as editable.
    assert U.detect_install_method(direct_url=None, prefix="/usr", in_git_worktree=False) == "pip"


def test_detect_noneditable_direct_url_is_not_editable():
    # a non-editable direct_url (e.g. VCS install) falls through to prefix logic
    assert (
        U.detect_install_method(direct_url=NONEDITABLE_DIRECT_URL, prefix="/usr", in_git_worktree=False)
        == "pip"
    )


def test_compare_versions():
    assert U.compare_versions("1.2.0", "1.2.1") == "behind"
    assert U.compare_versions("1.2.0", "1.2.0") == "equal"
    assert U.compare_versions("1.3.0", "1.2.0") == "ahead"
    assert U.compare_versions("1.2.0rc1", "1.2.0rc2") == "behind"


def test_compare_versions_unparseable_current_is_behind():
    assert U.compare_versions("dev", "1.2.0") == "behind"


def test_get_latest_version_parses_info_version(monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        captured["url"] = url
        # request= is required, or Response.raise_for_status() raises RuntimeError
        return httpx.Response(
            200, json={"info": {"version": "1.2.3"}}, request=httpx.Request("GET", url)
        )

    monkeypatch.setattr(U.httpx, "get", fake_get)
    assert U.get_latest_version("https://pypi.org") == "1.2.3"
    assert captured["url"] == "https://pypi.org/pypi/wxcli/json"


def test_get_latest_version_http_error_propagates(monkeypatch):
    def fake_get(url, **kwargs):
        return httpx.Response(503, request=httpx.Request("GET", url))

    monkeypatch.setattr(U.httpx, "get", fake_get)
    with pytest.raises(httpx.HTTPError):
        U.get_latest_version("https://pypi.org")


def test_index_base_default(monkeypatch):
    monkeypatch.delenv("WXCLI_UPDATE_INDEX_URL", raising=False)
    assert U.index_base() == "https://pypi.org"
    assert U.index_overridden() is False


def test_index_base_override_strips_trailing_slash(monkeypatch):
    monkeypatch.setenv("WXCLI_UPDATE_INDEX_URL", "https://test.pypi.org/")
    assert U.index_base() == "https://test.pypi.org"
    assert U.index_overridden() is True


def test_upgrade_command_pip_default():
    cmd = U.upgrade_command("pip", "https://pypi.org", overridden=False)
    assert cmd[-3:] == ["install", "--upgrade", "wxcli"]
    assert "--index-url" not in cmd


def test_upgrade_command_pip_overridden():
    cmd = U.upgrade_command("pip", "https://test.pypi.org", overridden=True)
    assert "--index-url" in cmd
    assert "https://test.pypi.org/simple" in cmd


def test_upgrade_command_pipx_overridden():
    cmd = U.upgrade_command("pipx", "https://test.pypi.org", overridden=True)
    assert cmd[:3] == ["pipx", "upgrade", "wxcli"]
    assert any("https://test.pypi.org/simple" in a for a in cmd)


def test_editable_install_prints_migration_guidance(monkeypatch):
    monkeypatch.setattr(U, "detect_install_method", lambda: "editable")
    result = runner.invoke(U.app, [])
    assert result.exit_code == 0
    assert "--migrate" in result.stdout
    assert "git pull" in result.stdout


def test_up_to_date_reports_and_exits_zero(monkeypatch):
    monkeypatch.setattr(U, "detect_install_method", lambda: "pip")
    monkeypatch.setattr(U, "get_latest_version", lambda base: U.__version__)
    result = runner.invoke(U.app, ["--check"])
    assert result.exit_code == 0
    assert "already the latest" in result.stdout


def test_behind_check_reports_without_upgrading(monkeypatch):
    calls = []
    monkeypatch.setattr(U, "detect_install_method", lambda: "pip")
    monkeypatch.setattr(U, "get_latest_version", lambda base: "999.0.0")
    monkeypatch.setattr(U.subprocess, "run", lambda *a, **k: calls.append(a) or _Ok())
    result = runner.invoke(U.app, ["--check"])
    assert result.exit_code == 0
    assert "999.0.0" in result.stdout
    assert "releases/tag/v999.0.0" in result.stdout
    assert calls == []  # --check never upgrades


def test_behind_yes_runs_the_upgrade_command(monkeypatch):
    calls = []
    monkeypatch.setattr(U, "detect_install_method", lambda: "pip")
    monkeypatch.setattr(U, "get_latest_version", lambda base: "999.0.0")
    monkeypatch.setattr(U.subprocess, "run", lambda *a, **k: calls.append(a[0]) or _Ok())
    # isolate from cwd: a manifest in pytest's cwd would make refresh_playbook
    # exec the REAL subprocess.run (default bound at def time, immune to the patch)
    monkeypatch.setattr(U, "refresh_playbook", lambda *a, **k: None)
    result = runner.invoke(U.app, ["--yes"])
    assert result.exit_code == 0
    assert calls, "upgrade command should have run"
    assert "wxcli" in calls[0]


def test_pypi_unreachable_is_nonzero(monkeypatch):
    monkeypatch.setattr(U, "detect_install_method", lambda: "pip")

    def boom(base):
        raise httpx.ConnectError("no network")

    monkeypatch.setattr(U, "get_latest_version", boom)
    result = runner.invoke(U.app, [])
    assert result.exit_code != 0


def test_migrate_requires_pipx(monkeypatch):
    monkeypatch.setattr(U.shutil, "which", lambda name: None)
    result = runner.invoke(U.app, ["--migrate"])
    assert result.exit_code != 0
    assert "pipx" in result.stdout


class _Ok:
    returncode = 0


# --- §4.7 playbook refresh after upgrade -----------------------------------

def _mk_manifest(tmp_path, profile="claude"):
    directory = tmp_path / f".{profile}"
    directory.mkdir()
    (directory / ".wxops-manifest.json").write_text("{}")


def test_refresh_playbook_no_manifest_prints_pointer(tmp_path, capsys):
    U.refresh_playbook("9.9.9", yes=True, cwd=tmp_path, run=lambda *a, **k: None)
    out = capsys.readouterr().out
    assert "wxcli init --force" in out and "9.9.9" in out


def test_refresh_playbook_manifest_present_execs_fresh_init(tmp_path):
    _mk_manifest(tmp_path)
    calls = []

    class R:  # minimal CompletedProcess stand-in
        returncode = 0

    U.refresh_playbook("9.9.9", yes=True, cwd=tmp_path,
                       run=lambda cmd, **k: calls.append(cmd) or R())
    assert calls == [["wxcli", "init", "--force", "--claude-only", str(tmp_path)]]


def test_refresh_playbook_codex_only_preserves_profile(tmp_path):
    _mk_manifest(tmp_path, "codex")
    calls = []

    class R:
        returncode = 0

    U.refresh_playbook("9.9.9", yes=True, cwd=tmp_path,
                       run=lambda cmd, **k: calls.append(cmd) or R())
    assert calls == [["wxcli", "init", "--force", "--codex-only", str(tmp_path)]]


def test_refresh_playbook_both_profiles_keeps_default_init(tmp_path):
    _mk_manifest(tmp_path, "claude")
    _mk_manifest(tmp_path, "codex")
    calls = []

    class R:
        returncode = 0

    U.refresh_playbook("9.9.9", yes=True, cwd=tmp_path,
                       run=lambda cmd, **k: calls.append(cmd) or R())
    assert calls == [["wxcli", "init", "--force", str(tmp_path)]]


def test_refresh_playbook_declined_prompt_does_nothing(tmp_path, monkeypatch):
    _mk_manifest(tmp_path)
    monkeypatch.setattr("typer.confirm", lambda *a, **k: False)
    calls = []
    U.refresh_playbook("9.9.9", yes=False, cwd=tmp_path,
                       run=lambda cmd, **k: calls.append(cmd))
    assert calls == []


def test_refresh_playbook_reports_failure(tmp_path, capsys):
    _mk_manifest(tmp_path)

    class R:
        returncode = 1

    U.refresh_playbook("9.9.9", yes=True, cwd=tmp_path, run=lambda *a, **k: R())
    assert "manually" in capsys.readouterr().err
