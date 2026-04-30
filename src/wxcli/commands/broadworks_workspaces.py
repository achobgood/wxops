import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling broadworks-workspaces.")


@app.command("create")
def create(
    provisioning_id: str = typer.Option(None, "--provisioning-id", help="(required) Provisioning ID that defines how this workspace is to be pro"),
    user_id: str = typer.Option(None, "--user-id", help="(required) The user ID of the workspace on BroadWorks."),
    sp_enterprise_id: str = typer.Option(None, "--sp-enterprise-id", help="(required) The Service Provider supplied unique identifier for the work"),
    display_name: str = typer.Option(None, "--display-name", help="(required) The display name of the workspace."),
    primary_phone_number: str = typer.Option(None, "--primary-phone-number", help="The primary phone number configured against the workspace on"),
    extension: str = typer.Option(None, "--extension", help="The extension number configured against the workspace on Bro"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Provision a BroadWorks Workspace."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/broadworks/workspaces"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if provisioning_id is not None:
            body["provisioningId"] = provisioning_id
        if user_id is not None:
            body["userId"] = user_id
        if sp_enterprise_id is not None:
            body["spEnterpriseId"] = sp_enterprise_id
        if display_name is not None:
            body["displayName"] = display_name
        if primary_phone_number is not None:
            body["primaryPhoneNumber"] = primary_phone_number
        if extension is not None:
            body["extension"] = extension
        _missing = [f for f in ['provisioningId', 'userId', 'spEnterpriseId', 'displayName'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("update")
def update(
    workspace_id: str = typer.Argument(help="workspaceId"),
    user_id: str = typer.Option(None, "--user-id", help="The user ID of the workspace on BroadWorks."),
    primary_phone_number: str = typer.Option(None, "--primary-phone-number", help="The primary phone number configured against the workspace on"),
    extension: str = typer.Option(None, "--extension", help="The extension number configured against the workspace on Bro"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Broadworks Workspace."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/broadworks/workspaces/{workspace_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if user_id is not None:
            body["userId"] = user_id
        if primary_phone_number is not None:
            body["primaryPhoneNumber"] = primary_phone_number
        if extension is not None:
            body["extension"] = extension
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("delete")
def delete(
    workspace_id: str = typer.Argument(help="workspaceId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Remove a BroadWorks Workspace."""
    if not force:
        typer.confirm(f"Delete {workspace_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/broadworks/workspaces/{workspace_id}"
    try:
        api.session.rest_delete(url)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {workspace_id}")


