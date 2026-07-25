import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import resolve_org_id, get_cc_base_url, get_cc_org_id


app = typer.Typer(help="Manage Webex Contact Center cc-agent-wellbeing.")


_BODY_SKELETON_CREATE = '{"name":"...","eventTypes":["..."],"destinationUrl":"...","description":"...","secret":"...","orgId":"..."}'

@app.command("create")
def create(
    name: str = typer.Option(None, "--name", help="(required) Client-defined string naming the subscription."),
    description: str = typer.Option(None, "--description", help="Client-defined string describing the subscription."),
    destination_url: str = typer.Option(None, "--destination-url", help="(required) URL to which webhooks will be posted. Must be HTTPS on an IANA-listed top-level domain name (e.g. .com) with a path (at least /). No query parameters, userinfo, non-443 ports, or fragments allowed. We do not treat this field as sensitive data, so do not use secrets in this URL such as tokens or API..."),
    secret: str = typer.Option(None, "--secret", help="Secret string used to sign payloads sent to the destination URL."),
    org_id: str = typer.Option(None, "--org-id", help="Organization ID to be used for this operation. If unspecified, the Organization ID is inferred from the token. The token must have permission to interact with the organization."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Subscribe for realtime burnout events\n\nExample --json-body:\n  '{"name":"...","eventTypes":["..."],"destinationUrl":"...","description":"...","secret":"...","orgId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/agentburnout/subscribe"
    if json_body:
        body = load_json_body(json_body)
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



_BODY_SKELETON_CREATE_ACTION = '{"interactionId":"...","agentId":"...","clientId":"...","actionType":"...","actionDateType":{}}'

@app.command("create-action")
def create_action(
    interaction_id: str = typer.Option(None, "--interaction-id", help="A unique identifier for each interaction or contact within the contact center."),
    agent_id: str = typer.Option(None, "--agent-id", help="The identifier for the agent whose burnout index has been calculated."),
    client_id: str = typer.Option(None, "--client-id", help="The name of the client initiating the action related to the agent burnout index. The name is limited to a maximum of 20 characters."),
    action_type: str = typer.Option(None, "--action-type", help="Specifies the type of action initiated based on the agent burnout index"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Record the realtime burnout events\n\nExample --json-body:\n  '{"interactionId":"...","agentId":"...","clientId":"...","actionType":"...","actionDateType":{}}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_ACTION), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/agentburnout/action"
    if json_body:
        body = load_json_body(json_body)
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



@app.command("show")
def show(
    id: str = typer.Argument(help="id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"enabled":true,"agentInclusionType":"ALL","organizationId":"...","id":"...","version":0,"wellnessBreakReminders":"DISABLED","createdTime":0,"lastUpdatedTime":0}'

@app.command("update")
def update(
    id: str = typer.Argument(help="id"),
    organization_id: str = typer.Option(None, "--organization-id", help="ID of the contact center organization. This field is required for all bulk save operations."),
    id_param: str = typer.Option(None, "--id", help="ID of this contact center resource. It should not be specified when creating a new resource. However, it is mandatory when updating a resource."),
    version: str = typer.Option(None, "--version", help="The version of this resource. For a newly created resource, it will be 0 unless specified otherwise."),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Used to toggle the state of the agent burnout configuration from active to inactive and vice-versa. Mandatory for create/update operation."),
    agent_inclusion_type: str = typer.Option(None, "--agent-inclusion-type", help="Choices: ALL, SPECIFIC"),
    wellness_break_reminders: str = typer.Option(None, "--wellness-break-reminders", help="Choices: DISABLED, ENABLED"),
    created_time: str = typer.Option(None, "--created-time", help="This is the created time of the entity."),
    last_updated_time: str = typer.Option(None, "--last-updated-time", help="This is the updated time of the entity."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update specific Agent Burnout resource by ID\n\nExample --json-body:\n  '{"enabled":true,"agentInclusionType":"ALL","organizationId":"...","id":"...","version":0,"wellnessBreakReminders":"DISABLED","createdTime":0,"lastUpdatedTime":0}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/agent-burnout/{id}"
    if json_body:
        body = load_json_body(json_body)
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    else:
        typer.echo(f"Updated.")



@app.command("list")
def cmd_list(
    filter_param: str = typer.Option(None, "--filter", help="Specify a filter based on which the results will be fetched. All the fields are supported except: organizationId, createdTime, lastUpdatedTime The examples below show some search queries - id==\"57efb0e6-5af0-4245-a67d-d3c5045cdb6e\" - id!=\"57efb0e6-5af0-4245-a67d-d3c5045cdb6e\" -..."),
    attributes: str = typer.Option(None, "--attributes", help="Specify the attributes to be returned. By default, all attributes are returned along with the specified columns. All attributes are supported."),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("data", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)


