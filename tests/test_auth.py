import os
import json
from unittest.mock import Mock, patch

import httpx
import pytest

from wxcli.auth import (
    DEFAULT_MAX_ATTEMPTS,
    MAX_RETRY_AFTER_SECONDS,
    WebexSession,
    resolve_token,
)
from wxcli.errors import WebexError

# Patch target is bare `httpx.request`, NOT `wxcli.auth.httpx.request`.
# auth.py imports httpx lazily inside the request methods (`auth.py:14-21`,
# `:206`, `:226`) so that `wxcli --help` never pays for it, which means
# `wxcli.auth` has no `httpx` attribute to patch — the old target raised
# AttributeError/ImportError on 18 of these 24 tests from 2026-07-28 until
# this file was repaired. Patching the attribute on the real httpx module
# works because `_request` re-resolves `httpx.request` on every call.


def _response(status_code=200, body=None, headers=None):
    resp = Mock(spec=httpx.Response)
    resp.status_code = status_code
    resp.is_success = 200 <= status_code < 300
    text = json.dumps(body) if body is not None else ""
    resp.text = text
    resp.content = text.encode()
    resp.json = Mock(return_value=body)
    resp.headers = headers or {}
    return resp

def test_resolve_token_from_env():
    with patch.dict(os.environ, {"WEBEX_ACCESS_TOKEN": "env-token"}, clear=False):
        assert resolve_token(config_path=None) == "env-token"

def test_resolve_token_fallback_env():
    env = os.environ.copy()
    env.pop("WEBEX_ACCESS_TOKEN", None)
    env["WEBEX_TOKEN"] = "fallback-token"
    with patch.dict(os.environ, env, clear=False):
        os.environ.pop("WEBEX_ACCESS_TOKEN", None)
        assert resolve_token(config_path=None) == "fallback-token"

def test_resolve_token_from_config(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "profiles": {"default": {"token": "config-token"}}
    }))
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("WEBEX_ACCESS_TOKEN", None)
        os.environ.pop("WEBEX_TOKEN", None)
        assert resolve_token(config_path=config_path) == "config-token"

def test_resolve_token_none_when_missing(tmp_path):
    config_path = tmp_path / "nonexistent.json"
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("WEBEX_ACCESS_TOKEN", None)
        os.environ.pop("WEBEX_TOKEN", None)
        assert resolve_token(config_path=config_path) is None


def test_rest_patch_sends_patch_with_content_type():
    session = WebexSession("tok")
    with patch("httpx.request", return_value=_response(body={"ok": True})) as req:
        result = session.rest_patch("https://api/x", json=[{"op": "replace"}],
                                    content_type="application/json-patch+json")
    assert result == {"ok": True}
    args, kwargs = req.call_args
    assert args[0] == "PATCH"
    assert kwargs["headers"]["Content-Type"] == "application/json-patch+json"


def test_rest_patch_default_content_type():
    session = WebexSession("tok")
    with patch("httpx.request", return_value=_response(body={})) as req:
        session.rest_patch("https://api/x", json={"a": 1})
    assert req.call_args.kwargs["headers"]["Content-Type"] == "application/json"


def test_webex_error_carries_status_and_body():
    session = WebexSession("tok")
    err_body = {"errors": [{"errorCode": 4008, "description": "no license"}]}
    with patch("httpx.request", return_value=_response(404, body=err_body)):
        with pytest.raises(WebexError) as exc_info:
            session.rest_get("https://api/x")
    assert exc_info.value.status_code == 404
    assert exc_info.value.body == err_body
    assert "4008" in str(exc_info.value)


def test_webex_error_message_first_constructor_unchanged():
    e = WebexError("plain text")
    assert str(e) == "plain text"
    assert e.status_code is None
    assert e.body is None


def test_429_retry_honors_retry_after():
    session = WebexSession("tok")
    responses = [_response(429, body={}, headers={"Retry-After": "0"}),
                 _response(body={"ok": True})]
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("WXCLI_NO_RETRY", None)
        with patch("httpx.request", side_effect=responses) as req, \
             patch("wxcli.auth.time.sleep") as sleep:
            result = session.rest_get("https://api/x")
    assert result == {"ok": True}
    assert req.call_count == 2
    sleep.assert_called_once_with(0)


def test_429_retry_is_bounded():
    session = WebexSession("tok")
    always_429 = [_response(429, body={}, headers={"Retry-After": "0"})] * DEFAULT_MAX_ATTEMPTS
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("WXCLI_NO_RETRY", None)
        with patch("httpx.request", side_effect=always_429) as req, \
             patch("wxcli.auth.time.sleep"):
            with pytest.raises(WebexError) as exc_info:
                session.rest_get("https://api/x")
    assert req.call_count == DEFAULT_MAX_ATTEMPTS
    assert exc_info.value.status_code == 429


def test_connect_error_retries_once():
    session = WebexSession("tok")
    effects = [httpx.ConnectError("boom"), _response(body={"ok": True})]
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("WXCLI_NO_RETRY", None)
        with patch("httpx.request", side_effect=effects) as req:
            result = session.rest_get("https://api/x")
    assert result == {"ok": True}
    assert req.call_count == 2


def test_connect_error_not_retried_twice():
    session = WebexSession("tok")
    effects = [httpx.ConnectError("boom"), httpx.ConnectError("boom again")]
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("WXCLI_NO_RETRY", None)
        with patch("httpx.request", side_effect=effects):
            with pytest.raises(httpx.ConnectError):
                session.rest_get("https://api/x")


def test_wxcli_no_retry_disables_retries():
    session = WebexSession("tok")
    with patch.dict(os.environ, {"WXCLI_NO_RETRY": "1"}, clear=False):
        with patch("httpx.request",
                   side_effect=[_response(429, body={}, headers={"Retry-After": "0"})]) as req:
            with pytest.raises(WebexError):
                session.rest_get("https://api/x")
    assert req.call_count == 1


# ── Explicit timeouts (Task 2) ───────────────────────────────────────────────


def _capture_timeout(monkeypatch):
    seen = {}

    def fake(method, url, headers=None, json=None, params=None, timeout=None):
        seen["timeout"] = timeout
        return httpx.Response(200, json={}, request=httpx.Request(method, url))

    monkeypatch.setattr("httpx.request", fake)
    return seen


def test_defaults_are_10s_connect_60s_read(monkeypatch):
    monkeypatch.delenv("WXCLI_READ_TIMEOUT", raising=False)
    monkeypatch.delenv("WXCLI_CONNECT_TIMEOUT", raising=False)
    seen = _capture_timeout(monkeypatch)
    WebexSession("tok").rest_get("https://x/p")
    assert seen["timeout"].connect == 10.0
    assert seen["timeout"].read == 60.0


def test_constructor_overrides_defaults(monkeypatch):
    seen = _capture_timeout(monkeypatch)
    WebexSession("tok", connect_timeout=1.0, read_timeout=5.0).rest_get("https://x/p")
    assert seen["timeout"].connect == 1.0
    assert seen["timeout"].read == 5.0


def test_env_vars_override_defaults(monkeypatch):
    monkeypatch.setenv("WXCLI_CONNECT_TIMEOUT", "3")
    monkeypatch.setenv("WXCLI_READ_TIMEOUT", "120")
    seen = _capture_timeout(monkeypatch)
    WebexSession("tok").rest_get("https://x/p")
    assert seen["timeout"].connect == 3.0
    assert seen["timeout"].read == 120.0


def test_malformed_env_var_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("WXCLI_READ_TIMEOUT", "not-a-number")
    seen = _capture_timeout(monkeypatch)
    WebexSession("tok").rest_get("https://x/p")
    assert seen["timeout"].read == 60.0


# ── 5xx retry with backoff (Task 3) ──────────────────────────────────────────


def _counting(monkeypatch, statuses):
    """Return a status from the list per call, repeating the last one."""
    calls = {"n": 0}

    def fake(method, url, headers=None, json=None, params=None, timeout=None):
        idx = min(calls["n"], len(statuses) - 1)
        calls["n"] += 1
        return httpx.Response(statuses[idx], json={"ok": True},
                              request=httpx.Request(method, url))

    monkeypatch.setattr("httpx.request", fake)
    monkeypatch.setattr("wxcli.auth.time.sleep", lambda s: None)
    return calls


def test_retries_502_then_succeeds(monkeypatch):
    calls = _counting(monkeypatch, [502, 502, 200])
    assert WebexSession("tok").rest_get("https://x/p") == {"ok": True}
    assert calls["n"] == 3


def test_gives_up_after_max_attempts(monkeypatch):
    calls = _counting(monkeypatch, [503])
    monkeypatch.setenv("WXCLI_MAX_ATTEMPTS", "3")
    with pytest.raises(WebexError):
        WebexSession("tok").rest_get("https://x/p")
    assert calls["n"] == 3


def test_does_not_retry_404(monkeypatch):
    calls = _counting(monkeypatch, [404])
    with pytest.raises(WebexError):
        WebexSession("tok").rest_get("https://x/p")
    assert calls["n"] == 1


def test_retry_mode_off_disables_retries(monkeypatch):
    calls = _counting(monkeypatch, [503])
    monkeypatch.setenv("WXCLI_RETRY_MODE", "off")
    with pytest.raises(WebexError):
        WebexSession("tok").rest_get("https://x/p")
    assert calls["n"] == 1


def test_legacy_no_retry_env_still_works(monkeypatch):
    calls = _counting(monkeypatch, [503])
    monkeypatch.setenv("WXCLI_NO_RETRY", "1")
    with pytest.raises(WebexError):
        WebexSession("tok").rest_get("https://x/p")
    assert calls["n"] == 1


def test_backoff_grows_and_is_jittered():
    from wxcli.auth import _backoff_delay
    assert 0 <= _backoff_delay(1) <= 1.0
    assert 1.0 <= _backoff_delay(2) <= 2.0
    assert 2.0 <= _backoff_delay(3) <= 4.0


def test_retry_after_header_still_wins_on_429(monkeypatch):
    slept = []
    calls = {"n": 0}

    def fake(method, url, headers=None, json=None, params=None, timeout=None):
        calls["n"] += 1
        status = 429 if calls["n"] == 1 else 200
        hdrs = {"Retry-After": "7"} if status == 429 else {}
        return httpx.Response(status, json={}, headers=hdrs,
                              request=httpx.Request(method, url))

    monkeypatch.setattr("httpx.request", fake)
    monkeypatch.setattr("wxcli.auth.time.sleep", lambda s: slept.append(s))
    WebexSession("tok").rest_get("https://x/p")
    assert slept == [7]


# ── The two residual gaps in `_request`'s retry loop (auth.py:226-260) ────────
#
# Repairing the patch targets above already drives 31 of the 35 statements in
# `_request`. Measured, not assumed: a stdlib `trace` run of the repaired file
# reports 226,228-237,239-251,254-260 executed. Exactly two statements stay
# dark — the `except ValueError` fallback at :252-253 — and one branch is
# executed but never actually exercised: the `min(..., MAX_RETRY_AFTER_SECONDS)`
# clamp at :251 only ever saw "0" and "7", both under the 30s cap.
#
# Those two are not arbitrary leftovers. They are two of the six rows in the
# audit's Target A / Target B disagreement table (ARCHITECTURE_AUDIT.md §2 #2):
# the `Retry-After` parse that survives the RFC-permitted HTTP-date form, and
# the 30s cap. Phase B extracts this policy into a module both stacks import,
# so these two assertions are what will distinguish "the engine now shares
# Target A's policy" from "the engine now does something else too."


def _retry_after(monkeypatch, header_value, status=429):
    """Serve one retryable response carrying `Retry-After`, then a 200.

    Returns the list `time.sleep` was called with.
    """
    slept = []
    calls = {"n": 0}

    def fake(method, url, headers=None, json=None, params=None, timeout=None):
        calls["n"] += 1
        code = status if calls["n"] == 1 else 200
        hdrs = {"Retry-After": header_value} if code == status else {}
        return httpx.Response(code, json={}, headers=hdrs,
                              request=httpx.Request(method, url))

    monkeypatch.setattr("httpx.request", fake)
    monkeypatch.setattr("wxcli.auth.time.sleep", lambda s: slept.append(s))
    return slept


def test_retry_after_above_cap_is_clamped_to_30s(monkeypatch):
    """A server asking for an hour gets waited on for 30s, not an hour.

    `auth.py:251`. Uncapped is what `engine.py` does today, and it is the row
    the audit's table marks A-is-right.
    """
    slept = _retry_after(monkeypatch, "3600")
    WebexSession("tok").rest_get("https://x/p")
    assert slept == [MAX_RETRY_AFTER_SECONDS]
    assert MAX_RETRY_AFTER_SECONDS == 30


def test_retry_after_http_date_form_falls_back_to_backoff(monkeypatch):
    """The RFC-permitted HTTP-date form is not an integer and must not raise.

    `auth.py:252-253` — the two statements the repair alone leaves dark.
    `int("Wed, 21 Oct 2015 07:28:00 GMT")` raises ValueError; the handler
    swallows it and falls through to `_backoff_delay(1)`, whose range is (0,1].
    `engine.py:200` does the bare `int(...)` and lets it raise, which is how a
    date-form header becomes a permanently failed migration operation.
    """
    slept = _retry_after(monkeypatch, "Wed, 21 Oct 2015 07:28:00 GMT")
    WebexSession("tok").rest_get("https://x/p")
    assert len(slept) == 1
    assert 0 <= slept[0] <= 1.0


def test_retry_after_is_honored_on_5xx_not_just_429(monkeypatch):
    """`:247` reads the header for every status in RETRY_STATUSES, with no 429
    check — a 503 carrying `Retry-After: 5` sleeps 5, not a backoff draw.

    The docstring at `auth.py:223-225` used to say "honored on 429, exponential
    backoff otherwise", which this test proved wrong; the docstring was
    corrected to match rather than the code, because honouring `Retry-After` on
    503 is what RFC 9110 §10.2.3 describes — 503 is the status the field was
    defined for. This assertion is what keeps the two from drifting again.
    """
    slept = _retry_after(monkeypatch, "5", status=503)
    WebexSession("tok").rest_get("https://x/p")
    assert slept == [5]


# ── follow_pagination (auth.py:298-311) ──────────────────────────────────────
#
# Measured at literal zero coverage — not merely in CI, but on this disk, even
# with every untracked test running (07-testability.md §3.3/§3.5). It is the
# walker behind `--all` on 173 of the generated list commands, and its
# `Link` parse at :304-310 is a hand-rolled split(",")/strip("<>").


def _pages(monkeypatch, pages):
    """Serve `pages` in order as (body, headers) pairs. Records each request."""
    seen = []

    def fake(method, url, headers=None, json=None, params=None, timeout=None):
        body, hdrs = pages[len(seen)]
        seen.append({"url": url, "params": params})
        return httpx.Response(200, json=body, headers=hdrs,
                              request=httpx.Request(method, url))

    monkeypatch.setattr("httpx.request", fake)
    return seen


def test_follow_pagination_walks_link_header_to_exhaustion(monkeypatch):
    seen = _pages(monkeypatch, [
        ({"items": [{"id": 1}, {"id": 2}]},
         {"Link": '<https://api/x?cursor=2>; rel="next"'}),
        ({"items": [{"id": 3}]}, {}),
    ])
    session = WebexSession("tok")
    assert list(session.follow_pagination("https://api/x")) == [
        {"id": 1}, {"id": 2}, {"id": 3}]
    assert [r["url"] for r in seen] == ["https://api/x", "https://api/x?cursor=2"]


def test_follow_pagination_picks_next_out_of_a_multi_rel_header(monkeypatch):
    """Webex sends first/prev/next/last in one header; only next may be walked.

    This is the parse at `auth.py:304-310`. A parser that took `split(",")[0]`
    would loop on `rel="first"` forever.
    """
    seen = _pages(monkeypatch, [
        ({"items": [{"id": 1}]},
         {"Link": '<https://api/x?cursor=0>; rel="first",'
                  '<https://api/x?cursor=9>; rel="last",'
                  '<https://api/x?cursor=2>; rel="next"'}),
        ({"items": [{"id": 2}]}, {}),
    ])
    session = WebexSession("tok")
    assert list(session.follow_pagination("https://api/x")) == [{"id": 1}, {"id": 2}]
    assert seen[1]["url"] == "https://api/x?cursor=2"


def test_follow_pagination_stops_when_no_rel_next(monkeypatch):
    seen = _pages(monkeypatch, [
        ({"items": [{"id": 1}]}, {"Link": '<https://api/x?cursor=0>; rel="prev"'}),
    ])
    session = WebexSession("tok")
    assert list(session.follow_pagination("https://api/x")) == [{"id": 1}]
    assert len(seen) == 1


def test_follow_pagination_drops_params_after_the_first_page(monkeypatch):
    """`auth.py:311`. The `Link` URL already carries the cursor; re-sending the
    original query string alongside it is how a walker re-requests page one."""
    seen = _pages(monkeypatch, [
        ({"items": [{"id": 1}]}, {"Link": '<https://api/x?cursor=2>; rel="next"'}),
        ({"items": []}, {}),
    ])
    session = WebexSession("tok")
    list(session.follow_pagination("https://api/x", params={"max": 100}))
    assert seen[0]["params"] == {"max": 100}
    assert seen[1]["params"] is None


def test_follow_pagination_honors_a_custom_item_key(monkeypatch):
    _pages(monkeypatch, [({"data": [{"id": 1}]}, {})])
    session = WebexSession("tok")
    assert list(session.follow_pagination("https://api/x", item_key="data")) == [{"id": 1}]


def test_follow_pagination_raises_webex_error_on_failure(monkeypatch):
    """`auth.py:300-301`. 404 rather than 500 on purpose: 500 is in
    RETRY_STATUSES, so it would exercise the retry loop before the raise."""
    def fake(method, url, headers=None, json=None, params=None, timeout=None):
        return httpx.Response(404, json={"message": "nope"},
                              request=httpx.Request(method, url))

    monkeypatch.setattr("httpx.request", fake)
    session = WebexSession("tok")
    with pytest.raises(WebexError) as exc_info:
        list(session.follow_pagination("https://api/x"))
    assert exc_info.value.status_code == 404
