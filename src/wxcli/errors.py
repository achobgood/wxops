"""Centralized error handler for wxcli commands."""
import json
import typer


class WebexError(Exception):
    pass


_ERROR_TIPS = {
    4003: "This endpoint requires a user-level OAuth token, not an admin or service app token.",
    4008: "This endpoint requires the target user to have a Webex Calling license.",
    25008: "Use --json-body for full control over the request body.",
    25409: "This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.",
    28018: "CX Essentials is not enabled for this queue. Use --has-cx-essentials true when creating/querying CX queues.",
}


def _extract_error_code(err: str) -> int | None:
    """Extract errorCode from a Webex API JSON error response."""
    try:
        body = json.loads(err)
        for entry in body.get("errors", []):
            code = entry.get("errorCode")
            if code is not None:
                return int(code)
    except (json.JSONDecodeError, ValueError, AttributeError):
        pass
    return None


def handle_rest_error(e: WebexError) -> None:
    """Centralized error handler with actionable tips."""
    err = str(e)
    code = _extract_error_code(err)

    if code == 4003 and "Target user not authorized" not in err:
        code = None

    if code and code in _ERROR_TIPS:
        typer.echo(f"Error: {e}", err=True)
        typer.echo(f"Tip: {_ERROR_TIPS[code]}", err=True)
    elif "wxcc" in err and "403" in err:
        typer.echo(f"Error: {e}", err=True)
        typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
    else:
        typer.echo(f"Error: {e}", err=True)
    raise typer.Exit(1)
