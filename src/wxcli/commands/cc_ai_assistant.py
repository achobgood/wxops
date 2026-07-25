import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_cc_base_url


app = typer.Typer(help="Manage Webex Contact Center cc-ai-assistant.")


_BODY_SKELETON_CREATE = '{"agentId":"...","orgId":"...","eventType":"CUSTOM_EVENT","eventName":"GET_SUGGESTIONS","eventDetails":{"data":{"interactionId":"...","actionTimeStamp":"...","trackingId":"...","languageCode":"...","aiAssistantSkillId":"...","source":"..."}}}'

@app.command("create")
def create(
    agent_id: str = typer.Option(None, "--agent-id", help="(required) Agent identifier"),
    org_id: str = typer.Option(None, "--org-id", help="(required) Organization identifier"),
    event_type: str = typer.Option(None, "--event-type", help="(required) Choices: CUSTOM_EVENT"),
    event_name: str = typer.Option(None, "--event-name", help="(required) Choices: GET_SUGGESTIONS"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get suggestions\n\nExample --json-body:\n  '{"agentId":"...","orgId":"...","eventType":"CUSTOM_EVENT","eventName":"GET_SUGGESTIONS","eventDetails":{"data":{"interactionId":"...","actionTimeStamp":"...","trackingId":"...","languageCode":"...","aiAssistantSkillId":"...","source":"..."}}}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/event"
    if json_body:
        body = load_json_body(json_body)
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    if output == "id":
        if isinstance(result, dict) and "id" in result:
            typer.echo(f"Created: {result['id']}")
        elif not result or result == {}:
            typer.echo("Created.")
        else:
            print_json(result)
    else:
        emit(result, output=output, fields=fields)


