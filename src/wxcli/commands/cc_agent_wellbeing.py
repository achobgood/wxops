import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id, get_cc_base_url, get_cc_org_id


app = typer.Typer(help="Manage Webex Contact Center cc-agent-wellbeing.")


@app.command("create")
def create(
    name: str = typer.Option(None, "--name", help="(required) Client-defined string naming the subscription."),
    description: str = typer.Option(None, "--description", help="Client-defined string describing the subscription."),
    destination_url: str = typer.Option(None, "--destination-url", help="(required) URL to which webhooks will be posted. Must be HTTPS on an IA"),
    secret: str = typer.Option(None, "--secret", help="Secret string used to sign payloads sent to the destination"),
    org_id: str = typer.Option(None, "--org-id", help="Organization ID to be used for this operation. If unspecifie"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Subscribe for realtime burnout events\n\nExample --json-body:\n  '{"name":"...","eventTypes":["..."],"destinationUrl":"...","description":"...","secret":"...","orgId":"..."}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/agentburnout/subscribe"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if destination_url is not None:
            body["destinationUrl"] = destination_url
        if secret is not None:
            body["secret"] = secret
        if org_id is not None:
            body["orgId"] = org_id
        _missing = [f for f in ['name', 'destinationUrl'] if f not in body or body[f] is None]
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



@app.command("create-action")
def create_action(
    interaction_id: str = typer.Option(None, "--interaction-id", help="A unique identifier for each interaction or contact within t"),
    agent_id: str = typer.Option(None, "--agent-id", help="The identifier for the agent whose burnout index has been ca"),
    client_id: str = typer.Option(None, "--client-id", help="The name of the client initiating the action related to the"),
    action_type: str = typer.Option(None, "--action-type", help="Specifies the type of action initiated based on the agent bu"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Record the realtime burnout events\n\nExample --json-body:\n  '{"interactionId":"...","agentId":"...","clientId":"...","actionType":"...","actionDateType":{}}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/agentburnout/action"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if interaction_id is not None:
            body["interactionId"] = interaction_id
        if agent_id is not None:
            body["agentId"] = agent_id
        if client_id is not None:
            body["clientId"] = client_id
        if action_type is not None:
            body["actionType"] = action_type
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



@app.command("show")
def show(
    id: str = typer.Argument(help="id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get specific Agent Burnout resource by ID."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/agent-burnout/{id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
            handle_rest_error(e)
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("update")
def update(
    id: str = typer.Argument(help="id"),
    organization_id: str = typer.Option(None, "--organization-id", help="ID of the contact center organization. This field is require"),
    id_param: str = typer.Option(None, "--id", help="ID of this contact center resource. It should not be specifi"),
    version: str = typer.Option(None, "--version", help="The version of this resource. For a newly created resource,"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Used to toggle the state of the agent burnout  configuration"),
    agent_inclusion_type: str = typer.Option(None, "--agent-inclusion-type", help="Choices: ALL, SPECIFIC"),
    wellness_break_reminders: str = typer.Option(None, "--wellness-break-reminders", help="Choices: DISABLED, ENABLED"),
    created_time: str = typer.Option(None, "--created-time", help="This is the created time of the entity."),
    last_updated_time: str = typer.Option(None, "--last-updated-time", help="This is the updated time of the entity."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update specific Agent Burnout resource by ID."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/agent-burnout/{id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if organization_id is not None:
            body["organizationId"] = organization_id
        if id_param is not None:
            body["id"] = id_param
        if version is not None:
            body["version"] = version
        if enabled is not None:
            body["enabled"] = enabled
        if agent_inclusion_type is not None:
            body["agentInclusionType"] = agent_inclusion_type
        if wellness_break_reminders is not None:
            body["wellnessBreakReminders"] = wellness_break_reminders
        if created_time is not None:
            body["createdTime"] = created_time
        if last_updated_time is not None:
            body["lastUpdatedTime"] = last_updated_time
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("list")
def cmd_list(
    filter_param: str = typer.Option(None, "--filter", help="Specify a filter based on which the results will be fetched."),
    attributes: str = typer.Option(None, "--attributes", help="Specify the attributes to be returned. By default, all attri"),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts"),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If th"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Agent Burnout resource(s)."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/v2/agent-burnout"
    params = {}
    if filter_param is not None:
        params["filter"] = filter_param
    if attributes is not None:
        params["attributes"] = attributes
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["pageSize"] = page_size
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("data", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)


