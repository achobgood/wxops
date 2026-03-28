import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_cc_base_url


app = typer.Typer(help="Manage Webex Contact Center cc-ai-assistant.")


@app.command("create")
def create(
    event_type: str = typer.Option(None, "--event-type", help=""),
    org_id: str = typer.Option(None, "--org-id", help=""),
    event_name: str = typer.Option(None, "--event-name", help=""),
    agent_id: str = typer.Option(None, "--agent-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get suggestions\n\nExample --json-body:\n  '{"eventType":"...","orgId":"...","eventName":"...","eventDetails":{"data":{"source":"...","languageCode":"...","trackingId":"...","actionTimeStamp":"...","interactionId":"...","aiAssistantSkillId":"..."}},"agentId":"..."}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/event"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if event_type is not None:
            body["eventType"] = event_type
        if org_id is not None:
            body["orgId"] = org_id
        if event_name is not None:
            body["eventName"] = event_name
        if agent_id is not None:
            body["agentId"] = agent_id
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)


