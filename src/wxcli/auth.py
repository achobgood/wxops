import os
import time
import logging
from pathlib import Path

import httpx
import typer

from wxcli.config import DEFAULT_CONFIG_PATH, get_token
from wxcli.errors import WebexError

logger = logging.getLogger("wxcli")

# Bounded retry policy. Opt out (scripted contexts) with WXCLI_NO_RETRY=1.
MAX_RETRIES_429 = 3
MAX_RETRY_AFTER_SECONDS = 30


class WebexSession:
    def __init__(self, token: str):
        self._token = token

    def _headers(self, content_type: str | None = None) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": content_type or "application/json",
        }

    def _request(self, method: str, url: str, json=None, params=None,
                 content_type: str | None = None) -> httpx.Response:
        """Single HTTP path for all verbs: bounded 429/Retry-After honor +
        one connect-error retry. WXCLI_NO_RETRY=1 disables both."""
        retry_enabled = not os.environ.get("WXCLI_NO_RETRY")
        retries_429 = MAX_RETRIES_429 if retry_enabled else 0
        connect_retries = 1 if retry_enabled else 0
        while True:
            try:
                response = httpx.request(
                    method, url, headers=self._headers(content_type),
                    json=json, params=params,
                )
            except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                if connect_retries:
                    connect_retries -= 1
                    logger.warning("Connect error on %s %s (%s) — retrying once", method, url, e)
                    continue
                raise
            if response.status_code == 429 and retries_429:
                retries_429 -= 1
                try:
                    delay = min(int(response.headers.get("Retry-After", 5)), MAX_RETRY_AFTER_SECONDS)
                except ValueError:
                    delay = 5
                logger.warning("429 on %s %s — waiting %ss (Retry-After)", method, url, delay)
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
        return self._json_or_raise(self._request("GET", url, params=params))

    def rest_put(self, url: str, json=None, params=None) -> dict:
        return self._json_or_raise(self._request("PUT", url, json=json, params=params))

    def rest_post(self, url: str, json=None, params=None) -> dict:
        return self._json_or_raise(self._request("POST", url, json=json, params=params))

    def rest_patch(self, url: str, json=None, params=None, content_type: str | None = None) -> dict:
        return self._json_or_raise(self._request("PATCH", url, json=json, params=params,
                                                 content_type=content_type))

    def rest_delete(self, url: str, params=None) -> dict:
        return self._json_or_raise(self._request("DELETE", url, params=params))

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


def get_api(debug: bool = False) -> WebexApi:
    """Get a configured WebexApi instance, or exit with error."""
    if debug:
        logging.basicConfig(level=logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    token = resolve_token()
    if not token:
        typer.echo("Error: No token found. Run 'wxcli configure' or set WEBEX_ACCESS_TOKEN.", err=True)
        raise typer.Exit(1)

    try:
        api = WebexApi(WebexSession(token))
    except Exception as e:
        typer.echo(f"Error: Failed to initialize API: {e}", err=True)
        raise typer.Exit(1)

    return api
