import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_cc_base_url


app = typer.Typer(help="Manage Webex Contact Center cc-agent-summaries.")


_BODY_SKELETON_CREATE = '{"orgId":"...","searchType":"AGENT","interactionId":"...","agentCiUserId":"..."}'

@app.command("create", short_help="List summaries.")
def create(
    org_id: str = typer.Option(None, "--org-id", help="(required) The unique identifier of the organization to which the summarized interactions belong."),
    search_type: str = typer.Option(None, "--search-type", help="(required) Choices: AGENT"),
    interaction_id: str = typer.Option(None, "--interaction-id", help="(required) The unique identifier of a specific interaction."),
    agent_ci_user_id: str = typer.Option(None, "--agent-ci-user-id", help="(required) The CI (Common Identity) user ID of the agent associated with the summaries."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """List summaries.\n\n\b\nExample: wxcli cc-agent-summaries create --org-id ORG_ID --search-type AGENT --interaction-id INTERACTION_ID --agent-ci-user-id AGENT_CI_USER_ID\n\n\b\nExample --json-body: '{"orgId":"...","searchType":"AGENT","interactionId":"...","agentCiUserId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/generated-summaries/search"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if org_id is not None:
            body["orgId"] = org_id
        if search_type is not None:
            body["searchType"] = search_type
        if interaction_id is not None:
            body["interactionId"] = interaction_id
        if agent_ci_user_id is not None:
            body["agentCiUserId"] = agent_ci_user_id
        _missing = [f for f in ['orgId', 'searchType', 'interactionId', 'agentCiUserId'] if f not in body or body[f] is None]
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


