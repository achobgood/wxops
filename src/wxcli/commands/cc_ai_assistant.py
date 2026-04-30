import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_cc_base_url


app = typer.Typer(help="Manage Webex Contact Center cc-ai-assistant.")


@app.command("create")
def create(
    agent_id: str = typer.Option(None, "--agent-id", help="(required) Agent identifier"),
    org_id: str = typer.Option(None, "--org-id", help="(required) Organization identifier"),
    event_type: str = typer.Option(None, "--event-type", help="(required) Choices: CUSTOM_EVENT"),
    event_name: str = typer.Option(None, "--event-name", help="(required) Choices: GET_SUGGESTIONS"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get suggestions\n\nExample --json-body:\n  '{"agentId":"...","orgId":"...","eventType":"CUSTOM_EVENT","eventName":"GET_SUGGESTIONS","eventDetails":{"data":{"interactionId":"...","actionTimeStamp":"...","trackingId":"...","languageCode":"...","aiAssistantSkillId":"...","source":"..."}}}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/event"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if agent_id is not None:
            body["agentId"] = agent_id
        if org_id is not None:
            body["orgId"] = org_id
        if event_type is not None:
            body["eventType"] = event_type
        if event_name is not None:
            body["eventName"] = event_name
        _missing = [f for f in ['agentId', 'orgId', 'eventType', 'eventName'] if f not in body or body[f] is None]
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


