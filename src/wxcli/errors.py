"""Centralized error handler for wxcli commands."""
import json
import typer


class WebexError(Exception):
    """Webex API error. Message-first: WebexError(response.text) remains valid.

    status_code and body (parsed JSON error, when parseable) are optional
    enrichments so handlers can key off status instead of substring matching.
    """

    def __init__(self, message: str, status_code: int | None = None, body: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


_ERROR_TIPS = {
    4003: "This endpoint requires a user-level OAuth token, not an admin or service app token.",
    4008: "This endpoint requires the target user to have a Webex Calling license.",
    9601: "This endpoint requires a user-level OAuth token, not an admin or service app token.",
    25008: "Use --json-body for full control over the request body.",
    25409: "This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.",
    28018: "CX Essentials is not enabled for this queue. Use --has-cx-essentials true when creating/querying CX queues.",
}

_MESSAGE_TIPS = {
    "Target user not authorized": "This endpoint requires a user-level OAuth token, not an admin or service app token.",
}


def _extract_error_code(err: str) -> int | None:
    """Extract error code from a Webex API JSON error response."""
    try:
        body = json.loads(err)
        for entry in body.get("errors", []):
            code = entry.get("errorCode") or entry.get("code")
            if code is not None:
                return int(code)
    except (json.JSONDecodeError, ValueError, AttributeError):
        pass
    return None


def _truncate_html(err: str) -> str:
    """Extract a readable message from HTML error responses."""
    if not err.lstrip().startswith("<"):
        return err
    import re
    title = re.search(r"<title>(.*?)</title>", err, re.IGNORECASE)
    h1 = re.search(r"<h1>(.*?)</h1>", err, re.IGNORECASE)
    msg = (h1 and h1.group(1)) or (title and title.group(1)) or "Non-JSON error response"
    return msg.strip()


def handle_rest_error(e: WebexError) -> None:
    """Centralized error handler with actionable tips."""
    err = str(e)
    code = _extract_error_code(err)

    if code == 4003 and "Target user not authorized" not in err:
        code = None

    if code and code in _ERROR_TIPS:
        typer.echo(f"Error: {_truncate_html(err)}", err=True)
        typer.echo(f"Tip: {_ERROR_TIPS[code]}", err=True)
    elif any(msg in err for msg in _MESSAGE_TIPS):
        tip = next(v for k, v in _MESSAGE_TIPS.items() if k in err)
        typer.echo(f"Error: {_truncate_html(err)}", err=True)
        typer.echo(f"Tip: {tip}", err=True)
    elif "wxcc" in err and "403" in err:
        typer.echo(f"Error: {_truncate_html(err)}", err=True)
        typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
    else:
        typer.echo(f"Error: {_truncate_html(err)}", err=True)
    raise typer.Exit(1)


_NETWORK_TIPS = {
    "ReadTimeout": "The server did not respond in time. Raise the limit with WXCLI_READ_TIMEOUT=<seconds>.",
    "WriteTimeout": "The request body could not be sent in time. Raise WXCLI_READ_TIMEOUT=<seconds>.",
    "ConnectTimeout": "Could not reach the API host in time. Check connectivity, or raise WXCLI_CONNECT_TIMEOUT=<seconds>.",
    "ConnectError": "Could not connect to the API host. Check network access and any proxy settings.",
    "PoolTimeout": "Connection pool exhausted. Retry, or reduce concurrency.",
}


def handle_network_error(e: Exception) -> None:
    """Handle transport failures that never produced an HTTP response.

    These bypass WebexError entirely — without this, a read timeout reaches
    the user as a raw traceback.
    """
    kind = type(e).__name__
    detail = f"{kind}: {e}" if str(e) else kind
    typer.echo(f"Error: request failed — {detail}", err=True)
    typer.echo(f"Tip: {_NETWORK_TIPS.get(kind, 'Transport-level failure with no HTTP response.')}", err=True)
    raise typer.Exit(1)
