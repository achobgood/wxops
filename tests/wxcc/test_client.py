"""Client hardening behaviors (Phase D — design § 14b), retargeted to wxcli.

Originally pinned `wxcc_flow.client.FlowClient`; Plan 2 Task 6 merged that
client into `wxcli.auth.WebexSession` and `wxcli.errors.handle_rest_error`, so
the same cases now run against the one runtime.
"""
import json

import httpx
import pytest
import typer
from unittest.mock import patch

from wxcli import config
from wxcli.auth import WebexSession
from wxcli.errors import WebexError, handle_rest_error

FAKE_TOKEN = "fake-token-not-a-secret"


class TestResultGuard:
    """_json_or_raise tolerates non-JSON success bodies (14b.1)."""

    def test_json_body_parses(self):
        assert WebexSession._json_or_raise(None, httpx.Response(200, json={"a": 1})) == {"a": 1}

    def test_non_json_body_returns_text(self):
        resp = httpx.Response(200, text="/flow-store is HEALTHY!")
        assert WebexSession._json_or_raise(None, resp) == "/flow-store is HEALTHY!"

    def test_empty_body_returns_empty_dict(self):
        assert WebexSession._json_or_raise(None, httpx.Response(200, content=b"")) == {}


def _print_error(resp: httpx.Response) -> None:
    """Drive a failed response through the real error path: raise, then handle."""
    try:
        WebexSession._json_or_raise(None, resp)
    except WebexError as e:
        handle_rest_error(e)
    raise AssertionError("a non-2xx response must raise WebexError")


class TestErrorBody:
    """handle_rest_error prints whole error bodies — never silently cut mid-body (14b.2)."""

    def test_under_limit_full_body(self, capsys):
        body = '{"error": "' + "x" * 500 + '"}'
        with pytest.raises(typer.Exit):
            _print_error(httpx.Response(500, text=body))
        assert body in capsys.readouterr().err

    def test_over_limit_explicit_marker(self, capsys):
        # wxcc truncated past 2,000 characters with an explicit marker; wxcli
        # prints the whole body, so the tail of a 2,500-character body arrives.
        body = "y" * 2480 + "END-OF-BODY-MARKER-1"
        assert len(body) == 2500
        with pytest.raises(typer.Exit):
            _print_error(httpx.Response(500, text=body))
        assert body[-20:] in capsys.readouterr().err

    def test_handle_error_500_prints_beyond_old_200_bound(self, capsys):
        body = '{"message": "' + "z" * 800 + '"}'
        with pytest.raises(typer.Exit):
            _print_error(httpx.Response(500, text=body))
        assert body in capsys.readouterr().err


def test_multipart_sends_file_part():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"id": "flow-1"})

    transport = httpx.MockTransport(handler)

    def fake_request(method, url, **kwargs):
        with httpx.Client(transport=transport) as client:
            return client.request(method, url, **kwargs)

    session = WebexSession(FAKE_TOKEN)
    with patch("httpx.request", side_effect=fake_request):
        result = session.rest_post_multipart(
            "https://flow-store.example.test/flow-store/v1/flows:import",
            files={"file": ("flow.json", json.dumps({"a": 1}).encode(), "application/json")},
            params={"overwrite": "true"},
        )

    assert result == {"id": "flow-1"}
    assert len(seen) == 1
    req = seen[0]
    assert req.method == "POST"
    assert req.headers["content-type"].startswith("multipart/form-data; boundary=")
    assert req.headers["authorization"] == f"Bearer {FAKE_TOKEN}"
    assert req.url.params["overwrite"] == "true"
    body = req.read()
    assert b'name="file"' in body
    assert b'filename="flow.json"' in body
    assert b'{"a": 1}' in body


def test_flow_store_url_precedence(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    monkeypatch.delenv("WXCLI_FLOW_STORE_URL", raising=False)

    # Nothing set: the default recorded in docs/merge/flow-store-host-map.md § Decision.
    assert config.FLOW_STORE_DEFAULT_URL == "https://flow-store.produs1.ciscoccservice.com/flow-store"
    assert config.get_flow_store_base_url(path) == config.FLOW_STORE_DEFAULT_URL

    # Config beats the default; a trailing slash is stripped.
    config.save_flow_store_url("https://flow-store.example.test/flow-store/", path)
    assert config.get_flow_store_base_url(path) == "https://flow-store.example.test/flow-store"

    # Env beats config.
    monkeypatch.setenv("WXCLI_FLOW_STORE_URL", "https://env.example.test/flow-store")
    assert config.get_flow_store_base_url(path) == "https://env.example.test/flow-store"
    monkeypatch.delenv("WXCLI_FLOW_STORE_URL")

    # None removes the key, back to the default.
    config.save_flow_store_url(None, path)
    assert "flow_store_url" not in config.load_config(path)["profiles"]["default"]
    assert config.get_flow_store_base_url(path) == config.FLOW_STORE_DEFAULT_URL

    # Gateway form follows the saved CC region (Review Focus 2).
    config.save_cc_region("eu2", path)
    config.save_flow_store_url("{cc_base_url}/flow-store", path)
    assert config.get_flow_store_base_url(path) == "https://api.wxcc-eu2.cisco.com/flow-store"


def test_rest_get_returns_non_json_success_text():
    """The 14b.1 guard holds end to end, past rest_get's truncation-note check."""
    def fake_request(method, url, **kwargs):
        return httpx.Response(200, text="/flow-store is HEALTHY!")

    with patch("httpx.request", side_effect=fake_request):
        assert WebexSession(FAKE_TOKEN).rest_get("https://flow-store.example.test/health") \
            == "/flow-store is HEALTHY!"


@pytest.mark.parametrize("statuses, expected_attempts", [
    ([503, 200], 1),   # a 5xx on a POST is never resent (ADR-15)
    ([429, 200], 2),   # a 429 is, like rest_post
])
def test_multipart_follows_post_retry_policy(statuses, expected_attempts):
    sent = []

    def fake_request(method, url, **kwargs):
        sent.append(kwargs)
        return httpx.Response(statuses[len(sent) - 1], json={"id": "flow-1"},
                              headers={"Retry-After": "0"})

    session = WebexSession(FAKE_TOKEN)
    files = {"file": ("flow.json", b"{}", "application/json")}
    with patch("httpx.request", side_effect=fake_request), patch("time.sleep"):
        try:
            session.rest_post_multipart("https://flow-store.example.test/import", files=files)
        except WebexError as e:
            assert e.status_code == 503
    assert len(sent) == expected_attempts
    assert all(kw["files"] is files and "Content-Type" not in kw["headers"] for kw in sent)
