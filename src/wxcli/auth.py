from __future__ import annotations

import os
import random
import time
import logging
from pathlib import Path

import typer

from wxcli.config import DEFAULT_CONFIG_PATH, get_token
from wxcli.errors import WebexError

# httpx itself (not just this module) is imported lazily, inside the methods
# that actually make a request — `import wxcli.auth` is on main.py's eager
# import path (whoami/switch-org reference get_api/resolve_token/WebexApi/
# WebexSession as module globals so tests can `mock.patch("wxcli.main.X")`),
# so keeping httpx off THIS module's own top level is what keeps it off
# `wxcli --version`/`--help`. `from __future__ import annotations` defers
# the httpx.Response type hints below to strings so they don't need the
# real import at class-definition time either.

logger = logging.getLogger("wxcli")


def _next_page_url(response: "httpx.Response") -> str | None:
    """The `Link: rel="next"` target, or None. Same parse as follow_pagination."""
    for part in response.headers.get("Link", "").split(","):
        part = part.strip()
        if 'rel="next"' in part:
            return part.split(";")[0].strip().strip("<>")
    return None


def _warn_if_more_pages(response: "httpx.Response", params=None) -> None:
    """Say so on stderr when a single fetch left pages on the server.

    210 list commands issue one `rest_get` against an endpoint the spec says
    paginates, and discard the `Link: rel="next"` silently — the command exits
    0 and hands back a partial answer with nothing indicating it. The display
    layer cannot cover this: `output.print_table`'s "... N more" row needs
    `len(data) > limit`, and on 502 of 503 list commands `--limit` is ALSO the
    API page size, so the row is unreachable exactly where truncation happens.

    This does not change what any command returns — stdout is untouched. It
    only makes the silent case loud, and tells us which commands truncate in
    practice: the count of 210 is a code shape, and the one live probe on
    record found 105 records returned whole from an endpoint whose spec
    declares a default page of 10.

    Contact Center's `page`/`pageSize` style carries no Link header and is NOT
    covered here — that is the 96 of the 210 this cannot see.
    """
    if not _next_page_url(response):
        return
    if os.environ.get("WXCLI_NO_PAGE_WARN"):
        return
    try:
        body = response.json()
        count = len(body.get("items", body.get("data", [])))
    except Exception:
        count = 0

    # The remedy must be `--offset`, NOT `--limit 0`. On the 210 commands this
    # fires for, `--limit 0` is already the default and does not fetch more —
    # naming it would print a next step that cannot work. Both render branches
    # send `--offset` through as `start`, so it is correct for every caller.
    try:
        start = int((params or {}).get("start") or 0)
    except (TypeError, ValueError):
        start = 0

    shown = f"{count} records returned" if count else "This response was partial"
    nxt = f" Fetch the next page with --offset {start + count}." if count else ""
    typer.echo(f"Note: {shown} and the server has more pages.{nxt}", err=True)

# Bounded retry policy. WXCLI_RETRY_MODE=off (or legacy WXCLI_NO_RETRY=1) disables.
DEFAULT_MAX_ATTEMPTS = 4
MAX_RETRY_AFTER_SECONDS = 30
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})


def _retry_enabled() -> bool:
    if os.environ.get("WXCLI_NO_RETRY"):
        return False
    return os.environ.get("WXCLI_RETRY_MODE", "standard").lower() != "off"


def _max_attempts() -> int:
    try:
        return max(1, int(os.environ.get("WXCLI_MAX_ATTEMPTS", DEFAULT_MAX_ATTEMPTS)))
    except ValueError:
        return DEFAULT_MAX_ATTEMPTS


def _backoff_delay(attempt: int) -> float:
    """Exponential backoff with jitter: attempt 1 -> (0,1], 2 -> (1,2], 3 -> (2,4]."""
    base = 2 ** (attempt - 1)
    lower = base / 2 if attempt > 1 else 0.0
    return lower + random.random() * (base - lower)

# httpx defaults to 5s for connect AND read; Webex list and CDR endpoints
# routinely exceed that. Override per-call or via env.
DEFAULT_CONNECT_TIMEOUT = 10.0
DEFAULT_READ_TIMEOUT = 60.0


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ[name])
    except (KeyError, ValueError):
        return default


class WebexSession:
    def __init__(self, token: str, connect_timeout: float | None = None,
                 read_timeout: float | None = None):
        import httpx  # deferred — see module docstring note above the imports

        self._token = token
        connect = connect_timeout if connect_timeout is not None else _env_float(
            "WXCLI_CONNECT_TIMEOUT", DEFAULT_CONNECT_TIMEOUT)
        read = read_timeout if read_timeout is not None else _env_float(
            "WXCLI_READ_TIMEOUT", DEFAULT_READ_TIMEOUT)
        self._timeout = httpx.Timeout(read, connect=connect)

    def _headers(self, content_type: str | None = None) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": content_type or "application/json",
        }

    def _request(self, method: str, url: str, json=None, params=None,
                 content_type: str | None = None) -> httpx.Response:
        """Single HTTP path for all verbs: bounded retry on RETRY_STATUSES
        (Retry-After honored on 429, exponential backoff otherwise) + one
        connect-error retry. WXCLI_RETRY_MODE=off / WXCLI_NO_RETRY=1 disable both."""
        import httpx  # deferred — see module docstring note above the imports

        enabled = _retry_enabled()
        attempts_left = _max_attempts() if enabled else 1
        connect_retries = 1 if enabled else 0
        attempt = 0
        while True:
            attempt += 1
            try:
                response = httpx.request(
                    method, url, headers=self._headers(content_type),
                    json=json, params=params, timeout=self._timeout,
                )
            except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                if connect_retries:
                    connect_retries -= 1
                    logger.warning("Connect error on %s %s (%s) — retrying once", method, url, e)
                    continue
                raise
            attempts_left -= 1
            if response.status_code in RETRY_STATUSES and attempts_left > 0:
                retry_after = response.headers.get("Retry-After")
                delay = None
                if retry_after:
                    try:
                        delay = min(int(retry_after), MAX_RETRY_AFTER_SECONDS)
                    except ValueError:
                        delay = None
                if delay is None:
                    delay = _backoff_delay(attempt)
                logger.warning("%s on %s %s — retrying in %.1fs",
                               response.status_code, method, url, delay)
                time.sleep(delay)
                continue
            return response

    def _json_or_raise(self, response: httpx.Response) -> dict:
        if not response.is_success:
            body = None
            try:
                body = response.json() if response.content else None
            except ValueError:
                pass
            raise WebexError(response.text, status_code=response.status_code, body=body)
        return response.json() if response.content else {}

    def rest_get(self, url: str, params=None) -> dict:
        response = self._request("GET", url, params=params)
        data = self._json_or_raise(response)
        _warn_if_more_pages(response, params)
        return data

    def rest_put(self, url: str, json=None, params=None) -> dict:
        return self._json_or_raise(self._request("PUT", url, json=json, params=params))

    def rest_post(self, url: str, json=None, params=None) -> dict:
        return self._json_or_raise(self._request("POST", url, json=json, params=params))

    def rest_patch(self, url: str, json=None, params=None, content_type: str | None = None) -> dict:
        return self._json_or_raise(self._request("PATCH", url, json=json, params=params,
                                                 content_type=content_type))

    def rest_delete(self, url: str, json=None, params=None) -> dict:
        # DELETE carries a body on 10 Webex operations: the body is what SCOPES
        # the delete (`supervisorIds`, `phoneNumbers`, `backgroundImages`...).
        # Without it the API rejects the call outright — verified live against
        # /telephony/config/supervisors: 400, errorCode 25024, "Required request
        # body is missing". It does NOT delete everything; those endpoints gate
        # delete-all behind an explicit `deleteAll: true`.
        return self._json_or_raise(self._request("DELETE", url, json=json, params=params))

    def follow_pagination(self, url: str, params=None, item_key: str = "items"):
        while url:
            response = self._request("GET", url, params=params)
            if not response.is_success:
                raise WebexError(response.text, status_code=response.status_code)
            data = response.json() if response.content else {}
            yield from (data.get(item_key, []) if isinstance(data, dict) else [])
            link = response.headers.get("Link", "")
            url = None
            for part in link.split(","):
                part = part.strip()
                if 'rel="next"' in part:
                    url = part.split(";")[0].strip().strip("<>")
                    break
            params = None


class WebexApi:
    def __init__(self, session: WebexSession):
        self.session = session


def resolve_token(config_path: Path | None = DEFAULT_CONFIG_PATH) -> str | None:
    """Resolve token: WEBEX_ACCESS_TOKEN env → WEBEX_TOKEN env → config file."""
    token = os.environ.get("WEBEX_ACCESS_TOKEN")
    if token:
        return token
    token = os.environ.get("WEBEX_TOKEN")
    if token:
        return token
    if config_path:
        return get_token(config_path)
    return None


def get_api(debug: bool = False, connect_timeout: float | None = None,
            read_timeout: float | None = None) -> WebexApi:
    """Get a configured WebexApi instance, or exit with error."""
    if debug:
        logging.basicConfig(level=logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    token = resolve_token()
    if not token:
        typer.echo("Error: No token found. Run 'wxcli configure' or set WEBEX_ACCESS_TOKEN.", err=True)
        raise typer.Exit(1)

    try:
        api = WebexApi(WebexSession(token, connect_timeout=connect_timeout,
                                    read_timeout=read_timeout))
    except Exception as e:
        typer.echo(f"Error: Failed to initialize API: {e}", err=True)
        raise typer.Exit(1)

    return api
