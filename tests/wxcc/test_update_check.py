"""Tests for the best-effort PyPI update check (wxcli.update_check).

Fully hermetic: every test mocks httpx and points the cache at tmp_path, so
nothing here reaches the network. The conftest disables the check session-wide;
the autouse fixture below re-enables it for this module's tests.
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
    """Undo the conftest session-wide disable so these tests hit the enabled
    path; the gate tests re-set the env in their own body. Pin a managed 'pip'
    install so the editable-silence guard doesn't hide notices in a dev checkout."""
    monkeypatch.delenv(uc.ENV_DISABLE, raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setattr(uc, "detect_install_method", lambda: "pip")


# ------------------------------------------------------------ version compare
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


def test_is_newer_ignores_prerelease_suffix():
    # Rewritten from wxcc's test_parse_version_strips_suffix: wxcli has no
    # _parse_version, so the suffix handling is checked through _is_newer.
    assert uc._is_newer("1.10.0rc1", "1.9.0") is False
    assert uc._is_newer("1.2.3.post1", "1.2.3") is True
    assert uc._is_newer("", "1.2.3") is False


# ------------------------------------------------------------ check_for_update
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


# ------------------------------------------------------------ maybe_notify
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


# ------------------------------------------------------------ CLI wiring
def test_version_flag_still_works():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_no_update_check_option_registered():
    import typer
    cmd = typer.main.get_command(app)
    assert "no_update_check" in {p.name for p in cmd.params}
