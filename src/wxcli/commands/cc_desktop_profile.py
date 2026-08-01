import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import resolve_org_id, get_cc_base_url, get_cc_org_id
from wxcli.common import verify_write


app = typer.Typer(help="Manage Webex Contact Center cc-desktop-profile.")


@app.command("list", short_help="List Desktop Profiles.")
def cmd_list(
    filter_param: str = typer.Option(None, "--filter", help="Specify a filter based on which the results will be fetched. Supported filterable fields: id. The examples below show some search queries - id==\"57efb0e6-5af0-4245-a67d-d3c5045cdb6e\" - id!=\"57efb0e6-5af0-4245-a67d-d3c5045cdb6e\" -..."),
    attributes: str = typer.Option(None, "--attributes", help="Specify the attributes to be returned. By default, all attributes are returned along with the specified columns. All attributes are supported. except ( wrapUpCodes,queues, idleCodes,entryPoints, buddyTeams, dialPlans, loginVoiceOptions, viewableStatistics, thresholdRules,agentDNValidationCriterions..."),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    single_object_response: str = typer.Option(None, "--single-object-response", help="Specify whether to include array fields in the response. This query parameter should be used only when the response contains a single record. It is not supported for responses with multiple objects and throws an exception."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Desktop Profiles."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/agent-profile"
    params = {}
    if filter_param is not None:
        params["filter"] = filter_param
    if attributes is not None:
        params["attributes"] = attributes
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["pageSize"] = page_size
    if single_object_response is not None:
        params["singleObjectResponse"] = single_object_response
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_page_param(url=url, params=params, item_key="items"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create", short_help="Create a new Desktop Profile.")
def create(
    agent_profile_dto: str = typer.Option(..., "--agent-profile-dto", help="Agent profile configuration data"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new Desktop Profile.\n\n\b\nExample: wxcli cc-desktop-profile create --agent-profile-dto AGENT_PROFILE_DTO"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/agent-profile"
    params = {}
    if agent_profile_dto is not None:
        params["agentProfileDTO"] = agent_profile_dto
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body, params=params)
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



_BODY_SKELETON_CREATE_BULK = '{"items":[{"itemIdentifier":0,"item":{"name":"...","parentType":"ORGANIZATION","accessWrapUpCode":"SPECIFIC","accessIdleCode":"SPECIFIC","accessQueue":"SPECIFIC","accessEntryPoint":"SPECIFIC","accessBuddyTeam":"SPECIFIC","agentDNValidation":"SPECIFIC","viewableStatistics":{"accessQueueStats":"SPECIFIC","accessTeamStats":"SPECIFIC","organizationId":"...","id":"...","version":0,"agentStats":true,"contactServiceQueues":["..."],"loggedInTeamStats":true,"teams":["..."],"createdTime":0,"lastUpdatedTime":0},"active":true,"organizationId":"...","id":"...","version":0,"description":"...","siteId":"...","screenPopup":true,"lastAgentRouting":true,"scheduleAndManageCallBack":true,"autoWrapUp":true,"autoAnswer":true,"agentPersonalGreeting":true,"autoWrapAfterSeconds":0,"agentAvailableAfterOutdial":true,"allowAutoWrapUpExtension":true,"wrapUpCodes":["..."],"idleCodes":["..."],"queues":["..."],"entryPoints":["..."],"buddyTeams":["..."],"consultToQueue":true,"outdialEnabled":true,"outdialEntryPointId":"...","outdialANIId":"...","addressBookId":"...","dialPlanEnabled":true,"dialPlans":["..."],"agentDNValidationCriteria":"SPECIFIC","agentDNValidationCriterions":["..."],"loginVoiceOptions":["AGENT_DN"],"thresholdRules":["..."],"timeoutDesktopInactivityCustomEnabled":true,"showUserDetailsMS":true,"stateSynchronizationMS":true,"showUserDetailsWebex":true,"stateSynchronizationWebex":true,"manageChannelAvailability":true,"timeoutDesktopInactivityMins":0,"systemDefault":true,"createdTime":0,"lastUpdatedTime":0,"autoAcceptDigitalInteractions":true},"requestAction":"..."}]}'

@app.command("create-bulk", short_help="Bulk save Desktop Profiles.")
def create_bulk(
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk save Desktop Profiles.\n\n\b\nExample --json-body: '{"items":[{"itemIdentifier":0,"item":{"name":"...","parentType":"ORGANIZATION","accessWrapUpCode":"SPECIFIC","accessIdleCode":"SPECIFIC","accessQueue":"SPECIFIC","accessEntryPoint":"SPECIFIC","accessBuddyTeam":"SPECIFIC","agentDNValidation":"SPECIFIC","viewableStatistics":{"accessQueueStats":"SPECIFIC","accessTeamStats":"SPECIFIC","organizationId":"...","id":"...","version":0,"agentStats":true,"contactServiceQueues":["..."],"loggedInTeamStats":true,"teams":["..."],"createdTime":0,"lastUpdatedTime":0},"active":true,"organizationId":"...","id":"...","version":0,"description":"...","siteId":"...","screenPopup":true,"lastAgentRouting":true,"scheduleAndManageCallBack":true,"autoWrapUp":true,"autoAnswer":true,"agentPersonalGreeting":true,"autoWrapAfterSeconds":0,"agentAvailableAfterOutdial":true,"allowAutoWrapUpExtension":true,"wrapUpCodes":["..."],"idleCodes":["..."],"queues":["..."],"entryPoints":["..."],"buddyTeams":["..."],"consultToQueue":true,"outdialEnabled":true,"outdialEntryPointId":"...","outdialANIId":"...","addressBookId":"...","dialPlanEnabled":true,"dialPlans":["..."],"agentDNValidationCriteria":"SPECIFIC","agentDNValidationCriterions":["..."],"loginVoiceOptions":["AGENT_DN"],"thresholdRules":["..."],"timeoutDesktopInactivityCustomEnabled":true,"showUserDetailsMS":true,"stateSynchronizationMS":true,"showUserDetailsWebex":true,"stateSynchronizationWebex":true,"manageChannelAvailability":true,"timeoutDesktopInactivityMins":0,"systemDefault":true,"createdTime":0,"lastUpdatedTime":0,"autoAcceptDigitalInteractions":true},"requestAction":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_BULK), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/agent-profile/bulk"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
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



@app.command("create-purge-inactive-entities", hidden=True)
@app.command("delete-purge-inactive-entities", short_help="Purge inactive Desktop Profiles.")
def delete_purge_inactive_entities(
    next_start_id: str = typer.Option(None, "--next-start-id", help="This is the entity ID from which items for the next purge batch will be selected."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Purge inactive Desktop Profiles."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/agent-profile/purge-inactive-entities"
    params = {}
    if next_start_id is not None:
        params["nextStartId"] = next_start_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if output == "id":
        typer.echo("Purged.")
    else:
        emit(result, output=output, fields=fields)



@app.command("show", short_help="Get specific Desktop Profile by ID.")
def show(
    id: str = typer.Argument(help="UUID, from: wxcli cc-desktop-profile list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get specific Desktop Profile by ID.\n\n\b\nExample: wxcli cc-desktop-profile show ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/agent-profile/{id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("update", short_help="Update specific Desktop Profile by ID.")
def update(
    id: str = typer.Argument(help="UUID, from: wxcli cc-desktop-profile list"),
    agent_profile_dto: str = typer.Option(..., "--agent-profile-dto", help="Agent profile configuration data for update"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update specific Desktop Profile by ID.\n\n\b\nExample: wxcli cc-desktop-profile update ID --agent-profile-dto AGENT_PROFILE_DTO"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/agent-profile/{id}"
    params = {}
    if agent_profile_dto is not None:
        params["agentProfileDTO"] = agent_profile_dto
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if verify:
        verify_write(api, url, params, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": id}, output=output, fields=fields)



@app.command("delete", short_help="Delete specific Desktop Profile by ID.")
def delete(
    id: str = typer.Argument(help="UUID, from: wxcli cc-desktop-profile list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete specific Desktop Profile by ID.\n\n\b\nExample: wxcli cc-desktop-profile delete ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    url = f"{cc_base_url}/organization/{orgid}/agent-profile/{id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {id}")
    else:
        emit({"status": "deleted", "id": id}, output=output, fields=fields)



@app.command("list-incoming-references", short_help="List references for a specific Desktop Profile.")
def list_incoming_references(
    id: str = typer.Argument(help="UUID, from: wxcli cc-desktop-profile list"),
    type_param: str = typer.Option(None, "--type", help="Entity type of the other entity that has a reference to this specific entity."),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List references for a specific Desktop Profile.\n\n\b\nExample: wxcli cc-desktop-profile list-incoming-references ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/agent-profile/{id}/incoming-references"
    params = {}
    if type_param is not None:
        params["type"] = type_param
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
        if all_pages:
            result = list(api.session.follow_page_param(url=url, params=params, item_key="items"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-agent-profile", short_help="List Desktop Profiles.")
def list_agent_profile(
    filter_param: str = typer.Option(None, "--filter", help="Specify a filter based on which the results will be fetched. All the fields are supported except: organizationId, autoWrapAfterSeconds, wrapUpCodes, idleCodes, queues, entryPoints, buddyTeams, dialPlans, agentDNValidationCriteria, agentDNValidationCriterions, loginVoiceOptions, viewableStatistics,..."),
    attributes: str = typer.Option(None, "--attributes", help="Specify the attributes to be returned. By default, all attributes are returned along with the specified columns. All attributes are supported. except ( wrapUpCodes,queues, idleCodes,entryPoints, buddyTeams, dialPlans, loginVoiceOptions, viewableStatistics, thresholdRules,agentDNValidationCriterions..."),
    search: str = typer.Option(None, "--search", help="Filter data based on the search keyword.Supported search columns(name, description) The examples below show some search queries - \"Cisco\" - field==\"name\";value==\"Cisco\" - fields=in=(\"name\",\"description\");value==\"Cisco\""),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    single_object_response: str = typer.Option(None, "--single-object-response", help="Specify whether to include array fields in the response. This query parameter should be used only when the response contains a single record. It is not supported for responses with multiple objects and throws an exception."),
    provisioning_view: str = typer.Option(None, "--provisioning-view", help="If set to true, the API will only return data that the user has access to, according to the User Profile."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Desktop Profiles."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/v2/agent-profile"
    params = {}
    if filter_param is not None:
        params["filter"] = filter_param
    if attributes is not None:
        params["attributes"] = attributes
    if search is not None:
        params["search"] = search
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["pageSize"] = page_size
    if single_object_response is not None:
        params["singleObjectResponse"] = single_object_response
    if provisioning_view is not None:
        params["provisioningView"] = provisioning_view
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_page_param(url=url, params=params, item_key="items"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)


