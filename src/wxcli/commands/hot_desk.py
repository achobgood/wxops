import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling hot-desk.")


@app.command("list")
def cmd_list(
    person_id: str = typer.Option(None, "--person-id", help="List sessions for this person."),
    workspace_id: str = typer.Option(None, "--workspace-id", help="List sessions for this workspace."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Sessions."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/hotdesk/sessions"
    params = {}
    if person_id is not None:
        params["personId"] = person_id
    if workspace_id is not None:
        params["workspaceId"] = workspace_id
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("delete")
def delete(
    session_id: str = typer.Argument(help="sessionId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Session."""
    if not force:
        typer.confirm(f"Delete {session_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/hotdesk/sessions/{session_id}"
    try:
        api.session.rest_delete(url)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {session_id}")


