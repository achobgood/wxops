"""Tests for the best-effort PyPI update check (wxcli.update_check).

Fully hermetic: every test mocks httpx and points the cache at tmp_path, so
nothing here reaches the network. The conftest disables the check session-wide;
the autouse fixture below re-enables it (and pins a managed install method).
"""
import json

import httpx
import pytest
from typer.testing import CliRunner

import wxcli.update_check as uc
from wxcli import __version__
from wxcli.main import app

runner = CliRunner()


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _fake_get(version):
    def _get(url, timeout=None):
        assert "wxcli" in url
        return _FakeResp({"info": {"version": version}})
    return _get


@pytest.fixture(autouse=True)
def _enable_checks(monkeypatch):
    """Undo the conftest session-wide disable, and pin a managed 'pip' install
    so the editable-silence guard doesn't suppress notices when the suite runs
    inside a dev/editable checkout. Env/editable tests override in their body."""
    monkeypatch.delenv(uc.ENV_DISABLE, raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setattr(uc, "detect_install_method", lambda: "pip")


@pytest.mark.parametrize("latest,current,expected", [
    ("0.3.4", "0.3.3", True),
    ("0.3.10", "0.3.3", True),      # numeric, not string, comparison
    ("0.10.0", "0.9.9", True),
    ("1.0.0", "0.99.99", True),
    ("0.3.3", "0.3.3", False),
    ("0.3.2", "0.3.3", False),
    ("0.4.0rc1", "0.4.0", False),   # don't nag toward a prerelease
    ("", "0.3.3", False),
    ("garbage", "0.3.3", False),
])
def test_is_newer(latest, current, expected):
    assert uc._is_newer(latest, current) is expected


def test_returns_latest_when_newer(monkeypatch, tmp_path):
    monkeypatch.setattr(uc.httpx, "get", _fake_get("9.9.9"))
    cache = tmp_path / "u.json"
    assert uc.check_for_update("0.3.3", cache_path=cache, now=1000.0) == "9.9.9"
    saved = json.loads(cache.read_text())
    assert saved["latest"] == "9.9.9" and saved["last_check"] == 1000.0


def test_returns_none_when_current(monkeypatch, tmp_path):
    monkeypatch.setattr(uc.httpx, "get", _fake_get(__version__))
    assert uc.check_for_update(__version__, cache_path=tmp_path / "u.json", now=1.0) is None


def test_fresh_cache_skips_network(monkeypatch, tmp_path):
    cache = tmp_path / "u.json"
    cache.write_text(json.dumps({"latest": "9.9.9", "last_check": 1000.0}))

    def _boom(*a, **k):
        raise AssertionError("network must not be hit on a fresh cache")
    monkeypatch.setattr(uc.httpx, "get", _boom)
    assert uc.check_for_update("0.3.3", cache_path=cache, now=1000.0 + 60) == "9.9.9"


def test_stale_cache_refetches(monkeypatch, tmp_path):
    cache = tmp_path / "u.json"
    cache.write_text(json.dumps({"latest": "0.0.1", "last_check": 1000.0}))
    monkeypatch.setattr(uc.httpx, "get", _fake_get("9.9.9"))
    now = 1000.0 + uc.CACHE_TTL_SECONDS + 1
    assert uc.check_for_update("0.3.3", cache_path=cache, now=now) == "9.9.9"
    assert json.loads(cache.read_text())["latest"] == "9.9.9"


def test_network_error_is_swallowed(monkeypatch, tmp_path):
    def _raise(*a, **k):
        raise httpx.ConnectError("no network")
    monkeypatch.setattr(uc.httpx, "get", _raise)
    assert uc.check_for_update("0.3.3", cache_path=tmp_path / "u.json", now=1.0) is None


def test_force_ignores_fresh_cache(monkeypatch, tmp_path):
    cache = tmp_path / "u.json"
    cache.write_text(json.dumps({"latest": "0.0.1", "last_check": 1000.0}))
    monkeypatch.setattr(uc.httpx, "get", _fake_get("9.9.9"))
    assert uc.check_for_update("0.3.3", cache_path=cache, now=1000.0 + 1, force=True) == "9.9.9"


class _Sink:
    def __init__(self):
        self.text = ""

    def write(self, s):
        self.text += s


def test_notify_prints_when_newer(monkeypatch, tmp_path):
    monkeypatch.setattr(uc.httpx, "get", _fake_get("9.9.9"))
    sink = _Sink()
    out = uc.maybe_notify_update("0.3.3", stream=sink, cache_path=tmp_path / "u.json", now=1.0)
    assert out == "9.9.9"
    assert "9.9.9 available" in sink.text
    assert "wxcli update" in sink.text


def test_notify_silent_when_current(monkeypatch, tmp_path):
    monkeypatch.setattr(uc.httpx, "get", _fake_get(__version__))
    sink = _Sink()
    assert uc.maybe_notify_update(__version__, stream=sink,
                                  cache_path=tmp_path / "u.json", now=1.0) is None
    assert sink.text == ""


def test_notify_silent_when_flag_disabled(monkeypatch, tmp_path):
    monkeypatch.setattr(uc.httpx, "get", _fake_get("9.9.9"))
    sink = _Sink()
    assert uc.maybe_notify_update("0.3.3", disabled=True, stream=sink,
                                  cache_path=tmp_path / "u.json", now=1.0) is None
    assert sink.text == ""


@pytest.mark.parametrize("env", ["WXCLI_NO_UPDATE_CHECK", "CI"])
def test_notify_silent_when_env_set(monkeypatch, tmp_path, env):
    monkeypatch.setenv(env, "1")
    monkeypatch.setattr(uc.httpx, "get", _fake_get("9.9.9"))
    sink = _Sink()
    assert uc.maybe_notify_update("0.3.3", stream=sink,
                                  cache_path=tmp_path / "u.json", now=1.0) is None
    assert sink.text == ""


def test_notify_env_falsey_stays_enabled(monkeypatch, tmp_path):
    monkeypatch.setenv("WXCLI_NO_UPDATE_CHECK", "0")  # explicit "don't disable"
    monkeypatch.setattr(uc.httpx, "get", _fake_get("9.9.9"))
    sink = _Sink()
    assert uc.maybe_notify_update("0.3.3", stream=sink,
                                  cache_path=tmp_path / "u.json", now=1.0) == "9.9.9"


def test_notify_silent_on_editable_install(monkeypatch, tmp_path):
    monkeypatch.setattr(uc, "detect_install_method", lambda: "editable")
    monkeypatch.setattr(uc.httpx, "get", _fake_get("9.9.9"))
    sink = _Sink()
    assert uc.maybe_notify_update("0.3.3", stream=sink,
                                  cache_path=tmp_path / "u.json", now=1.0) is None
    assert sink.text == ""


def test_version_flag_still_works():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_no_update_check_option_registered():
    import typer
    cmd = typer.main.get_command(app)
    assert "no_update_check" in {p.name for p in cmd.params}


def test_callback_passes_disabled_flag(monkeypatch):
    """The top-level callback calls maybe_notify_update with the flag value."""
    import wxcli.main as m
    seen = {}

    def _fake(cur, **kw):
        seen["current"] = cur
        seen.update(kw)
        return None

    monkeypatch.setattr("wxcli.update_check.maybe_notify_update", _fake)
    m.main(version=False, no_update_check=True)
    assert seen["disabled"] is True
    assert seen["current"]  # the installed version string is passed through


def test_update_hook_exits_2_when_behind(monkeypatch):
    import wxcli.commands.update as up
    monkeypatch.setattr(up, "detect_install_method", lambda: "pip")
    monkeypatch.setattr("wxcli.update_check.check_for_update", lambda *a, **k: "9.9.9")
    result = runner.invoke(app, ["update", "--hook"])
    assert result.exit_code == 2
    assert "newer wxcli is available: 9.9.9" in result.output
    assert "wxcli update" in result.output


def test_update_hook_exits_0_when_current(monkeypatch):
    import wxcli.commands.update as up
    monkeypatch.setattr(up, "detect_install_method", lambda: "pip")
    monkeypatch.setattr("wxcli.update_check.check_for_update", lambda *a, **k: None)
    result = runner.invoke(app, ["update", "--hook"])
    assert result.exit_code == 0
    assert result.output.strip() == ""


def test_update_hook_silent_on_editable(monkeypatch):
    import wxcli.commands.update as up
    monkeypatch.setattr(up, "detect_install_method", lambda: "editable")
    monkeypatch.setattr("wxcli.update_check.check_for_update", lambda *a, **k: None)
    result = runner.invoke(app, ["update", "--hook"])
    assert result.exit_code == 0
    assert result.output.strip() == ""


def test_bundled_settings_ships_pypi_hook():
    import json
    from pathlib import Path
    repo = Path(__file__).resolve().parent.parent
    settings = json.loads((repo / "wxcli-dist" / "settings.bundled.json").read_text())
    cmds = [h["command"] for h in settings["hooks"]["SessionStart"][0]["hooks"]]
    assert "wxcli --no-update-check update --hook" in cmds
    assert settings["permissions"]["allow"]  # permissions preserved


def test_bundle_and_codex_have_no_git_update_path():
    from pathlib import Path
    repo = Path(__file__).resolve().parent.parent
    bundled = (repo / "wxcli-dist" / "settings.bundled.json").read_text()
    codex = (repo / "wxcli-dist" / "codex" / "config.toml").read_text()
    assert "rev-list" not in bundled and "origin/main" not in bundled
    assert "rev-list" not in codex
    # There used to be an `assert "update --hook" in codex` here. It asserted the
    # PRESENCE of a hook, which is not this test's invariant — the name says
    # "no git update path", and the two `rev-list` assertions are what carry it.
    # `e35d8a1` then retracted the Codex-side update hook deliberately: a Codex
    # SessionStart hook fires but shows the human nothing, so the PyPI nudge is
    # served by the startup banner in update_check.py instead, and config.toml
    # says so in a comment. The assertion outlived the design it pinned and was
    # red at HEAD. Nothing replaces it here on purpose — the Codex hook surface
    # is `.codex/hooks.json` now (a PreToolUse safety gate, not an updater), and
    # `test_bundled_settings_ships_pypi_hook` above already guards the Claude
    # side, which is where the update hook actually ships.


def test_dev_repo_has_no_git_update_hook():
    from pathlib import Path
    repo = Path(__file__).resolve().parent.parent
    text = (repo / ".claude" / "settings.json").read_text()
    assert "rev-list" not in text and "origin/main" not in text


def test_error_negative_caches_to_throttle(monkeypatch, tmp_path):
    cache = tmp_path / "u.json"
    calls = {"n": 0}

    def _raise(*a, **k):
        calls["n"] += 1
        raise httpx.ConnectError("no network")

    monkeypatch.setattr(uc.httpx, "get", _raise)
    assert uc.check_for_update("0.3.3", cache_path=cache, now=1000.0) is None
    assert calls["n"] == 1 and cache.exists()
    # within TTL the next call must NOT hit the network again
    assert uc.check_for_update("0.3.3", cache_path=cache, now=1000.0 + 60) is None
    assert calls["n"] == 1


def test_error_preserves_last_known_good(monkeypatch, tmp_path):
    cache = tmp_path / "u.json"
    cache.write_text(json.dumps({"pkg": "wxcli", "latest": "9.9.9", "last_check": 0.0}))

    def _raise(*a, **k):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(uc.httpx, "get", _raise)
    now = uc.CACHE_TTL_SECONDS + 100  # stale -> fetch -> fail -> preserve 9.9.9
    assert uc.check_for_update("0.3.3", cache_path=cache, now=now) == "9.9.9"
