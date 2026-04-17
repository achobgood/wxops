import os
import logging
from pathlib import Path

import httpx
import typer

from wxcli.config import DEFAULT_CONFIG_PATH, get_token
from wxcli.errors import WebexError

logger = logging.getLogger("wxcli")


class WebexSession:
    def __init__(self, token: str):
        self._token = token

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}

    def rest_get(self, url: str, params=None) -> dict:
        response = httpx.get(url, headers=self._headers(), params=params)
        if not response.is_success:
            raise WebexError(response.text)
        return response.json() if response.content else {}

    def rest_put(self, url: str, json=None, params=None) -> dict:
        response = httpx.put(url, headers=self._headers(), json=json, params=params)
        if not response.is_success:
            raise WebexError(response.text)
        return response.json() if response.content else {}

    def rest_post(self, url: str, json=None, params=None) -> dict:
        response = httpx.post(url, headers=self._headers(), json=json, params=params)
        if not response.is_success:
            raise WebexError(response.text)
        return response.json() if response.content else {}

    def rest_delete(self, url: str, params=None) -> dict:
        response = httpx.delete(url, headers=self._headers(), params=params)
        if not response.is_success:
            raise WebexError(response.text)
        return response.json() if response.content else {}

    def follow_pagination(self, url: str, params=None, item_key: str = "items"):
        while url:
            response = httpx.get(url, headers=self._headers(), params=params)
            if not response.is_success:
                raise WebexError(response.text)
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
