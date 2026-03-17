import os
import logging
from pathlib import Path

import typer
from wxc_sdk import WebexSimpleApi

from wxcli.config import DEFAULT_CONFIG_PATH, get_token

logger = logging.getLogger("wxc_sdk")

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

def get_api(debug: bool = False) -> WebexSimpleApi:
    """Get a configured WebexSimpleApi instance, or exit with error."""
    if debug:
        logging.basicConfig(level=logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    token = resolve_token()
    if not token:
        typer.echo("Error: No token found. Run 'wxcli configure' or set WEBEX_ACCESS_TOKEN.", err=True)
        raise typer.Exit(1)

    try:
        api = WebexSimpleApi(tokens=token)
    except Exception as e:
        typer.echo(f"Error: Failed to initialize API: {e}", err=True)
        raise typer.Exit(1)

    return api
