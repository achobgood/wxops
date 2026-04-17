"""Centralized error handler for wxcli commands."""
import typer


class WebexError(Exception):
    pass


def handle_rest_error(e: WebexError) -> None:
    """Centralized error handler with actionable tips."""
    err = str(e)
    if "25008" in err:
        typer.echo(f"Error: Missing required field. {e}", err=True)
        typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
    elif "4003" in err or "Target user not authorized" in err:
        typer.echo(f"Error: {e}", err=True)
        typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
    elif "4008" in err:
        typer.echo(f"Error: {e}", err=True)
        typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
    elif "25409" in err:
        typer.echo(f"Error: {e}", err=True)
        typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
    elif "28018" in err:
        typer.echo(f"Error: {e}", err=True)
        typer.echo("Tip: CX Essentials is not enabled for this queue. Use --has-cx-essentials true when creating/querying CX queues.", err=True)
    else:
        typer.echo(f"Error: {e}", err=True)
    raise typer.Exit(1)
