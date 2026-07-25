import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import resolve_org_id, get_cc_base_url, get_cc_org_id


app = typer.Typer(help="Manage Webex Contact Center cc-queue.")


@app.command("list")
def cmd_list(
    filter_param: str = typer.Option(None, "--filter", help="Specify a filter based on which the results will be fetched. Supported filterable fields: id. The examples below show some search queries - id==\"57efb0e6-5af0-4245-a67d-d3c5045cdb6e\" - id!=\"57efb0e6-5af0-4245-a67d-d3c5045cdb6e\" -..."),
    channel_types: str = typer.Option(None, "--channel-types", help="[DEPRECATED] Channel type(s) allowed by the system.Separate values with commas.Use uppercase. By default, there is no channel type filtering."),
    attributes: str = typer.Option(None, "--attributes", help="Specify the attributes to be returned. By default, all attributes are returned along with the specified columns. All attributes are supported. except (callDistributionGroups,queueSkillRequirements,links)"),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    single_object_response: str = typer.Option(None, "--single-object-response", help="Specify whether to include array fields in the response. This query parameter should be used only when the response contains a single record. It is not supported for responses with multiple objects and throws an exception."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Contact Service Queues."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue"
    params = {}
    if filter_param is not None:
        params["filter"] = filter_param
    if channel_types is not None:
        params["channelTypes"] = channel_types
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
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



_BODY_SKELETON_CREATE = '{"items":[{"itemIdentifier":"...","item":"...","requestAction":"..."}]}'

@app.command("create")
def create(
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk save Contact Service Queues\n\nExample --json-body:\n  '{"items":[{"itemIdentifier":"...","item":"...","requestAction":"..."}]}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/bulk"
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



_BODY_SKELETON_UPDATE = '{"items":[{"itemIdentifier":"...","item":"...","requestAction":"..."}]}'

@app.command("update")
def update(
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk partial update Contact Service Queues\n\nExample --json-body:\n  '{"items":[{"itemIdentifier":"...","item":"...","requestAction":"..."}]}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/bulk"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_patch(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": orgid}, output=output, fields=fields)



@app.command("show")
def show(
    id: str = typer.Argument(help="id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """List skill-based Contact Service Queues by skill profile ID (public)."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/by-skill-profile-id/{id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_CREATE_DELETE_REFERENCE = '{"references":{}}'

@app.command("create-delete-reference")
def create_delete_reference(
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete references from Contact Service Queues\n\nExample --json-body:\n  '{"references":{}}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_DELETE_REFERENCE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/delete-reference"
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
        typer.echo("Deleted.")
    else:
        emit(result, output=output, fields=fields)



_BODY_SKELETON_CREATE_FETCH_BY_DYNAMIC_SKILLS_AND_SKILL_PROFILE = '{"skillProfileId":"...","dynamicSkills":[{"skillId":"...","textValue":"...","booleanValue":"...","proficiencyValue":"...","enumSkillValues":"..."}],"userId":"..."}'

@app.command("create-fetch-by-dynamic-skills-and-skill-profile")
def create_fetch_by_dynamic_skills_and_skill_profile(
    skill_profile_id: str = typer.Option(None, "--skill-profile-id", help="Unique identifier of the skill profile to look up queues for."),
    user_id: str = typer.Option(None, "--user-id", help="Unique identifier of the user (agent) whose skill-based queues should be retrieved. Used by the user-and-skill-profile lookup endpoint."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """List skill-based Contact Service Queues by dynamic skills and skill profile\n\nExample --json-body:\n  '{"skillProfileId":"...","dynamicSkills":[{"skillId":"...","textValue":"...","booleanValue":"...","proficiencyValue":"...","enumSkillValues":"..."}],"userId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_FETCH_BY_DYNAMIC_SKILLS_AND_SKILL_PROFILE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/fetch-by-dynamic-skills-and-skillProfile"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if skill_profile_id is not None:
            body["skillProfileId"] = skill_profile_id
        if user_id is not None:
            body["userId"] = user_id
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



_BODY_SKELETON_CREATE_FETCH_BY_USER_ID_SKILL_PROFILE_ID = '{"skillProfileId":"...","dynamicSkills":[{"skillId":"...","textValue":"...","booleanValue":"...","proficiencyValue":"...","enumSkillValues":"..."}],"userId":"..."}'

@app.command("create-fetch-by-user-id-skill-profile-id")
def create_fetch_by_user_id_skill_profile_id(
    skill_profile_id: str = typer.Option(None, "--skill-profile-id", help="Unique identifier of the skill profile to look up queues for."),
    user_id: str = typer.Option(None, "--user-id", help="Unique identifier of the user (agent) whose skill-based queues should be retrieved. Used by the user-and-skill-profile lookup endpoint."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """List skill-based Contact Service Queues by skill profile ID and user ID\n\nExample --json-body:\n  '{"skillProfileId":"...","dynamicSkills":[{"skillId":"...","textValue":"...","booleanValue":"...","proficiencyValue":"...","enumSkillValues":"..."}],"userId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_FETCH_BY_USER_ID_SKILL_PROFILE_ID), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/fetch-by-userId-skillProfileId"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if skill_profile_id is not None:
            body["skillProfileId"] = skill_profile_id
        if user_id is not None:
            body["userId"] = user_id
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



_BODY_SKELETON_CREATE_FETCH_MANUALLY_ASSIGNABLE_QUEUES = '{"agentId":"...","teamId":"..."}'

@app.command("create-fetch-manually-assignable-queues")
def create_fetch_manually_assignable_queues(
    agent_id: str = typer.Option(None, "--agent-id", help="Unique identifier of the agent (CI user ID) for whom manually assignable queues should be retrieved."),
    team_id: str = typer.Option(None, "--team-id", help="Unique identifier of the team that the agent belongs to. Used to scope the queues that the agent can be manually assigned contacts from."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """List manually assignable Contact Service Queues\n\nExample --json-body:\n  '{"agentId":"...","teamId":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_FETCH_MANUALLY_ASSIGNABLE_QUEUES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/fetch-manually-assignable-queues"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if agent_id is not None:
            body["agentId"] = agent_id
        if team_id is not None:
            body["teamId"] = team_id
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



@app.command("create-purge-inactive-entities")
def create_purge_inactive_entities(
    next_start_id: str = typer.Option(None, "--next-start-id", help="This is the entity ID from which items for the next purge batch will be selected."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Purge inactive Contact Service Queues."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/purge-inactive-entities"
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



@app.command("show-contact-service-queue-organization")
def show_contact_service_queue_organization(
    id: str = typer.Argument(help="id"),
    agents_updated_info: str = typer.Option(None, "--agents-updated-info", help="If `true`, returns the user details who has last updated the agents list in an agent based queue."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get specific Contact Service Queue by ID."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/{id}"
    params = {}
    if agents_updated_info is not None:
        params["agentsUpdatedInfo"] = agents_updated_info
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("delete")
def delete(
    id: str = typer.Argument(help="id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete specific Contact Service Queue by ID."""
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/{id}"
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



@app.command("list-incoming-references")
def list_incoming_references(
    id: str = typer.Argument(help="id"),
    type_param: str = typer.Option(None, "--type", help="Entity type of the other entity that has a reference to this specific entity."),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List references for a specific Contact Service Queue."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/{id}/incoming-references"
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
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



_BODY_SKELETON_CREATE_BULK = '{"items":[{"itemIdentifier":"...","item":"...","requestAction":"..."}]}'

@app.command("create-bulk")
def create_bulk(
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk save Contact Service Queues\n\nExample --json-body:\n  '{"items":[{"itemIdentifier":"...","item":"...","requestAction":"..."}]}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_BULK), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/v2/bulk"
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



@app.command("list-contact-service-queue-v2")
def list_contact_service_queue_v2(
    filter_param: str = typer.Option(None, "--filter", help="Specify a filter based on which the results will be fetched. All the fields are supported except: organizationId, queueSkillRequirements, xspVersion, createdTime, lastUpdatedTime The examples below show some search queries - id==\"57efb0e6-5af0-4245-a67d-d3c5045cdb6e\" -..."),
    attributes: str = typer.Option(None, "--attributes", help="Specify the attributes to be returned. By default, all attributes are returned along with the specified columns. All attributes are supported. except (callDistributionGroups,queueSkillRequirements,links)"),
    search: str = typer.Option(None, "--search", help="Filter data based on the search keyword.Supported search columns(name, description) The examples below show some search queries - \"Cisco\" - field==\"name\";value==\"Cisco\" - fields=in=(\"name\",\"description\");value==\"Cisco\""),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    desktop_profile_filter: str = typer.Option(None, "--desktop-profile-filter", help="If set to true, the API will return only the data that the user has access to according to its Desktop Profile. If unspecified, the default value is false."),
    provisioning_view: str = typer.Option(None, "--provisioning-view", help="If set to true, the API will only return data that the user has access to, according to the User Profile. This query parameter is applicable only when desktopProfileFilter query parameter is false."),
    single_object_response: str = typer.Option(None, "--single-object-response", help="Specify whether to include array fields in the response. This query parameter should be used only when the response contains a single record. It is not supported for responses with multiple objects and throws an exception."),
    include_ai_mapping_count: str = typer.Option(None, "--include-ai-mapping-count", help="If set to true, the API response will include the count of each AI feature mapped to the entity."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Contact Service Queues."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/v2/contact-service-queue"
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
    if desktop_profile_filter is not None:
        params["desktopProfileFilter"] = desktop_profile_filter
    if provisioning_view is not None:
        params["provisioningView"] = provisioning_view
    if single_object_response is not None:
        params["singleObjectResponse"] = single_object_response
    if include_ai_mapping_count is not None:
        params["includeAIMappingCount"] = include_ai_mapping_count
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
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



_BODY_SKELETON_CREATE_CONTACT_SERVICE_QUEUE = '{"name":"...","queueType":"INBOUND","checkAgentAvailability":true,"channelType":"TELEPHONY","serviceLevelThreshold":0,"maxActiveContacts":0,"maxTimeInQueue":0,"active":true}'

@app.command("create-contact-service-queue")
def create_contact_service_queue(
    organization_id: str = typer.Option(None, "--organization-id", help="ID of the contact center organization. This field is required for all bulk save operations."),
    id_param: str = typer.Option(None, "--id", help="ID of this contact center resource. It should not be specified when creating a new resource. However, it is mandatory when updating a resource."),
    version: str = typer.Option(None, "--version", help="The version of this resource. For a newly created resource, it will be 0 unless specified otherwise."),
    name: str = typer.Option(None, "--name", help="(required) Name of the Contact Service Queue"),
    description: str = typer.Option(None, "--description", help="(Optional) A short description of the queue."),
    queue_type: str = typer.Option(None, "--queue-type", help="(required) Choices: INBOUND, OUTBOUND"),
    check_agent_availability: bool = typer.Option(None, "--check-agent-availability/--no-check-agent-availability", help="(required) This setting specifies whether the system can exclude teams with no logged in agents for the relevant routing strategies. It does not support Social Channel Type."),
    channel_type: str = typer.Option(None, "--channel-type", help="(required) Choices: TELEPHONY, EMAIL, FAX, CHAT, VIDEO, OTHERS, SOCIAL_CHANNEL, WORK_ITEM, CUSTOM_MESSAGING"),
    social_channel_type: str = typer.Option(None, "--social-channel-type", help="Choices: MESSAGEBIRD, MESSENGER, WHATSAPP, APPLE_BUSINESS_CHAT, GOOGLE_BUSINESS_MESSAGES"),
    service_level_threshold: str = typer.Option(None, "--service-level-threshold", help="(required) The time in seconds that a customer request can be in a queue before the system flags it as outside the service level. It does not support Social Channel Type."),
    max_active_contacts: str = typer.Option(None, "--max-active-contacts", help="(required) The maximum number of simultaneous contacts allowed for this queue. It does not support Social Channel Type."),
    max_time_in_queue: str = typer.Option(None, "--max-time-in-queue", help="(required) The time in seconds after which the system distributes the queued customer request to the overflow number that you provision for this queue."),
    default_music_in_queue_media_file_id: str = typer.Option(None, "--default-music-in-queue-media-file-id", help="Identifies the default audio file which will be played for calls when they arrive or are waiting in queue. This setting is available only for the Telephony channel type."),
    timezone: str = typer.Option(None, "--timezone", help="(Optional) Any routing strategy for this queue uses the time zone that you select here."),
    active: bool = typer.Option(None, "--active/--no-active", help="(required) Specify whether the queue is active or not active"),
    outdial_campaign_enabled: bool = typer.Option(None, "--outdial-campaign-enabled/--no-outdial-campaign-enabled", help="Should be specified only for outdial queues; if enabled, then Call Distribution and Queue Routing Type can be specified."),
    monitoring_permitted: bool = typer.Option(None, "--monitoring-permitted/--no-monitoring-permitted", help="Indicates whether or not monitoring is permitted. This setting is available only for the Telephony channel type."),
    parking_permitted: bool = typer.Option(None, "--parking-permitted/--no-parking-permitted", help="Indicates whether or not parking is permitted. This setting is available only for the Telephony channel type."),
    recording_permitted: bool = typer.Option(None, "--recording-permitted/--no-recording-permitted", help="Indicates whether or not recording is permitted. This setting is available only for the Telephony channel type."),
    recording_all_calls_permitted: bool = typer.Option(None, "--recording-all-calls-permitted/--no-recording-all-calls-permitted", help="Indicates whether or not recording all calls is permitted. This setting is available only for the Telephony channel type."),
    pause_recording_permitted: bool = typer.Option(None, "--pause-recording-permitted/--no-pause-recording-permitted", help="Indicates whether or not pausing the recording is permitted. This setting is available only for the Telephony channel type."),
    recording_pause_duration: str = typer.Option(None, "--recording-pause-duration", help="The duration in seconds of pause in recording. This setting is available only for the Telephony channel type."),
    control_flow_script_url: str = typer.Option(None, "--control-flow-script-url", help="The URL for the queue or the default control script of the queue. If you do not use the routing strategy module to configure the control script, the system automatically populates the URL. This setting is available only for the Telephony channel type."),
    ivr_requeue_url: str = typer.Option(None, "--ivr-requeue-url", help="This setting is available only for the Telephony channel type."),
    overflow_number: str = typer.Option(None, "--overflow-number", help="The destination phone number to which the system distributes the customer calls when they exceed the Maximum Time in Queue that you have set in the routing strategy. This setting is applicable only for the Telephony channel type and it is optional."),
    vendor_id: str = typer.Option(None, "--vendor-id", help="The unique alphanumeric string that maps this queue to the vendor. This setting is available only for the Telephony channel type and it is optional."),
    routing_type: str = typer.Option(None, "--routing-type", help="(required) Choices: LONGEST_AVAILABLE_AGENT, SKILLS_BASED, CIRCULAR, LINEAR"),
    skill_based_routing_type: str = typer.Option(None, "--skill-based-routing-type", help="Choices: LONGEST_AVAILABLE_AGENT, BEST_AVAILABLE_AGENT"),
    queue_routing_type: str = typer.Option(None, "--queue-routing-type", help="(required) Choices: TEAM_BASED, SKILL_BASED, AGENT_BASED"),
    xsp_version: str = typer.Option(None, "--xsp-version", help="(Optional) Used to subscribe for recording events."),
    subscription_id: str = typer.Option(None, "--subscription-id", help="(Optional) Used to subscribe for recording events."),
    system_default: bool = typer.Option(None, "--system-default/--no-system-default", help="Indicates whether the created resource is system created or not"),
    manually_assignable: bool = typer.Option(None, "--manually-assignable/--no-manually-assignable", help="If `true`, the queue can be manually assigned."),
    agents_last_updated_by_user_name: str = typer.Option(None, "--agents-last-updated-by-user-name", help="The name of the user who last modified the agents list."),
    agents_last_updated_by_user_email_prefix: str = typer.Option(None, "--agents-last-updated-by-user-email-prefix", help="The email of the user who last modified the agents list."),
    agents_last_updated_time: str = typer.Option(None, "--agents-last-updated-time", help="The date when the agents list was last modified (epoch timestamp in milliseconds)."),
    queue_level_summaries_inclusion: str = typer.Option(None, "--queue-level-summaries-inclusion", help="Queue level summaries inclusion type. Used only when Queue inclusion for summaries is set to 'Specific Queues' at the org level AI Assistant->Summaries configuration. During entity creation(single or bulk), if this parameter is not provided or null, default will be set to 'EXCLUDED' During entity..."),
    queue_level_sentiment_analysis_inclusion: str = typer.Option(None, "--queue-level-sentiment-analysis-inclusion", help="Queue level sentiment analysis inclusion type. Used only when Queue inclusion for sentiment analysis is set to 'Specific Queues' at the org level AI Assistant->Quality Management configuration. During entity creation(single or bulk), if this parameter is not provided or null, default will be set to..."),
    queue_level_predicted_wait_time_inclusion: str = typer.Option(None, "--queue-level-predicted-wait-time-inclusion", help="Queue level predicted wait time inclusion type. Used only when Queue inclusion for predicted wait time is set to 'Specific Queues' at the org level AI Assistant->Predicted Wait Time configuration. During entity creation(single or bulk), if this parameter is not provided or null, default will be set..."),
    queue_level_auto_csat_inclusion: str = typer.Option(None, "--queue-level-auto-csat-inclusion", help="Queue level auto CSAT inclusion type. Used only when Queue inclusion for auto CSAT is set to 'Specific Queues' at the org level AI Assistant->Auto CSAT configuration. During entity creation(single or bulk), if this parameter is not provided or null, default will be set to 'EXCLUDED' During entity..."),
    queue_level_real_time_transcriptions_inclusion: str = typer.Option(None, "--queue-level-real-time-transcriptions-inclusion", help="Queue level real time transcriptions inclusion type. Used only when Queue inclusion for real time transcriptions is set to 'Specific Queues' at the org level AI Assistant->Real Time Transcriptions configuration. During entity creation(single or bulk), if this parameter is not provided or null,..."),
    created_time: str = typer.Option(None, "--created-time", help="This is the created time of the entity."),
    last_updated_time: str = typer.Option(None, "--last-updated-time", help="This is the updated time of the entity."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new Contact Service Queue\n\nExample --json-body:\n  '{"name":"...","queueType":"INBOUND","checkAgentAvailability":true,"channelType":"TELEPHONY","serviceLevelThreshold":0,"maxActiveContacts":0,"maxTimeInQueue":0,"active":true}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_CONTACT_SERVICE_QUEUE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/v2/contact-service-queue"
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
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if queue_type is not None:
            body["queueType"] = queue_type
        if check_agent_availability is not None:
            body["checkAgentAvailability"] = check_agent_availability
        if channel_type is not None:
            body["channelType"] = channel_type
        if social_channel_type is not None:
            body["socialChannelType"] = social_channel_type
        if service_level_threshold is not None:
            body["serviceLevelThreshold"] = service_level_threshold
        if max_active_contacts is not None:
            body["maxActiveContacts"] = max_active_contacts
        if max_time_in_queue is not None:
            body["maxTimeInQueue"] = max_time_in_queue
        if default_music_in_queue_media_file_id is not None:
            body["defaultMusicInQueueMediaFileId"] = default_music_in_queue_media_file_id
        if timezone is not None:
            body["timezone"] = timezone
        if active is not None:
            body["active"] = active
        if outdial_campaign_enabled is not None:
            body["outdialCampaignEnabled"] = outdial_campaign_enabled
        if monitoring_permitted is not None:
            body["monitoringPermitted"] = monitoring_permitted
        if parking_permitted is not None:
            body["parkingPermitted"] = parking_permitted
        if recording_permitted is not None:
            body["recordingPermitted"] = recording_permitted
        if recording_all_calls_permitted is not None:
            body["recordingAllCallsPermitted"] = recording_all_calls_permitted
        if pause_recording_permitted is not None:
            body["pauseRecordingPermitted"] = pause_recording_permitted
        if recording_pause_duration is not None:
            body["recordingPauseDuration"] = recording_pause_duration
        if control_flow_script_url is not None:
            body["controlFlowScriptUrl"] = control_flow_script_url
        if ivr_requeue_url is not None:
            body["ivrRequeueUrl"] = ivr_requeue_url
        if overflow_number is not None:
            body["overflowNumber"] = overflow_number
        if vendor_id is not None:
            body["vendorId"] = vendor_id
        if routing_type is not None:
            body["routingType"] = routing_type
        if skill_based_routing_type is not None:
            body["skillBasedRoutingType"] = skill_based_routing_type
        if queue_routing_type is not None:
            body["queueRoutingType"] = queue_routing_type
        if xsp_version is not None:
            body["xspVersion"] = xsp_version
        if subscription_id is not None:
            body["subscriptionId"] = subscription_id
        if system_default is not None:
            body["systemDefault"] = system_default
        if manually_assignable is not None:
            body["manuallyAssignable"] = manually_assignable
        if agents_last_updated_by_user_name is not None:
            body["agentsLastUpdatedByUserName"] = agents_last_updated_by_user_name
        if agents_last_updated_by_user_email_prefix is not None:
            body["agentsLastUpdatedByUserEmailPrefix"] = agents_last_updated_by_user_email_prefix
        if agents_last_updated_time is not None:
            body["agentsLastUpdatedTime"] = agents_last_updated_time
        if queue_level_summaries_inclusion is not None:
            body["queueLevelSummariesInclusion"] = queue_level_summaries_inclusion
        if queue_level_sentiment_analysis_inclusion is not None:
            body["queueLevelSentimentAnalysisInclusion"] = queue_level_sentiment_analysis_inclusion
        if queue_level_predicted_wait_time_inclusion is not None:
            body["queueLevelPredictedWaitTimeInclusion"] = queue_level_predicted_wait_time_inclusion
        if queue_level_auto_csat_inclusion is not None:
            body["queueLevelAutoCsatInclusion"] = queue_level_auto_csat_inclusion
        if queue_level_real_time_transcriptions_inclusion is not None:
            body["queueLevelRealTimeTranscriptionsInclusion"] = queue_level_real_time_transcriptions_inclusion
        if created_time is not None:
            body["createdTime"] = created_time
        if last_updated_time is not None:
            body["lastUpdatedTime"] = last_updated_time
        _missing = [f for f in ['name', 'queueType', 'checkAgentAvailability', 'channelType', 'serviceLevelThreshold', 'maxActiveContacts', 'maxTimeInQueue', 'active', 'routingType', 'queueRoutingType'] if f not in body or body[f] is None]
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



@app.command("list-agent-based-queues")
def list_agent_based_queues(
    userid: str = typer.Argument(help="userid"),
    search: str = typer.Option(None, "--search", help="Filter data based on the search keyword.Supported search columns(firstName, lastName, email) The examples below show some search queries - \"Cisco\" - field==\"firstName\";value==\"Cisco\" - fields=in=(\"firstName\",\"lastName\");value==\"Cisco\""),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List agent-based Contact Service Queues by user ID."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/v2/contact-service-queue/by-user-id/{userid}/agent-based-queues"
    params = {}
    if search is not None:
        params["search"] = search
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
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-skill-based-queues")
def list_skill_based_queues(
    userid: str = typer.Argument(help="userid"),
    search: str = typer.Option(None, "--search", help="Filter data based on the search keyword.Supported search columns(firstName, lastName, email) The examples below show some search queries - \"Cisco\" - field==\"firstName\";value==\"Cisco\" - fields=in=(\"firstName\",\"lastName\");value==\"Cisco\""),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List skill-based Contact Service Queues by user ID."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/v2/contact-service-queue/by-user-id/{userid}/skill-based-queues"
    params = {}
    if search is not None:
        params["search"] = search
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
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-team-based-queues")
def list_team_based_queues(
    userid: str = typer.Argument(help="userid"),
    search: str = typer.Option(None, "--search", help="Filter data based on the search keyword.Supported search columns(firstName, lastName, email) The examples below show some search queries - \"Cisco\" - field==\"firstName\";value==\"Cisco\" - fields=in=(\"firstName\",\"lastName\");value==\"Cisco\""),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List team-based Contact Service Queues by user ID."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/v2/contact-service-queue/by-user-id/{userid}/team-based-queues"
    params = {}
    if search is not None:
        params["search"] = search
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
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



_BODY_SKELETON_CREATE_FETCH_BY_GROUPED_ASSISTANT_SKILL = '{"assistantSkillIds":["..."]}'

@app.command("create-fetch-by-grouped-assistant-skill")
def create_fetch_by_grouped_assistant_skill(
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """List queue mapping summary grouped by Assistant Skill\n\nExample --json-body:\n  '{"assistantSkillIds":["..."]}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_FETCH_BY_GROUPED_ASSISTANT_SKILL), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/v2/contact-service-queue/fetch-by-grouped-assistant-skill"
    params = {}
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["pageSize"] = page_size
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



@app.command("show-contact-service-queue-v2")
def show_contact_service_queue_v2(
    id: str = typer.Argument(help="id"),
    agents_updated_info: str = typer.Option(None, "--agents-updated-info", help="If `true`, returns the user details who has last updated the agents list in an agent based queue."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get specific Contact Service Queue by ID."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/v2/contact-service-queue/{id}"
    params = {}
    if agents_updated_info is not None:
        params["agentsUpdatedInfo"] = agents_updated_info
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_CONTACT_SERVICE_QUEUE = '{"name":"...","queueType":"INBOUND","checkAgentAvailability":true,"channelType":"TELEPHONY","serviceLevelThreshold":0,"maxActiveContacts":0,"maxTimeInQueue":0,"active":true}'

@app.command("update-contact-service-queue")
def update_contact_service_queue(
    id: str = typer.Argument(help="id"),
    organization_id: str = typer.Option(None, "--organization-id", help="ID of the contact center organization. This field is required for all bulk save operations."),
    id_param: str = typer.Option(None, "--id", help="ID of this contact center resource. It should not be specified when creating a new resource. However, it is mandatory when updating a resource."),
    version: str = typer.Option(None, "--version", help="The version of this resource. For a newly created resource, it will be 0 unless specified otherwise."),
    name: str = typer.Option(None, "--name", help="Name of the Contact Service Queue"),
    description: str = typer.Option(None, "--description", help="(Optional) A short description of the queue."),
    queue_type: str = typer.Option(None, "--queue-type", help="Choices: INBOUND, OUTBOUND"),
    check_agent_availability: bool = typer.Option(None, "--check-agent-availability/--no-check-agent-availability", help="This setting specifies whether the system can exclude teams with no logged in agents for the relevant routing strategies. It does not support Social Channel Type."),
    channel_type: str = typer.Option(None, "--channel-type", help="Choices: TELEPHONY, EMAIL, FAX, CHAT, VIDEO, OTHERS, SOCIAL_CHANNEL, WORK_ITEM, CUSTOM_MESSAGING"),
    social_channel_type: str = typer.Option(None, "--social-channel-type", help="Choices: MESSAGEBIRD, MESSENGER, WHATSAPP, APPLE_BUSINESS_CHAT, GOOGLE_BUSINESS_MESSAGES"),
    service_level_threshold: str = typer.Option(None, "--service-level-threshold", help="The time in seconds that a customer request can be in a queue before the system flags it as outside the service level. It does not support Social Channel Type."),
    max_active_contacts: str = typer.Option(None, "--max-active-contacts", help="The maximum number of simultaneous contacts allowed for this queue. It does not support Social Channel Type."),
    max_time_in_queue: str = typer.Option(None, "--max-time-in-queue", help="The time in seconds after which the system distributes the queued customer request to the overflow number that you provision for this queue."),
    default_music_in_queue_media_file_id: str = typer.Option(None, "--default-music-in-queue-media-file-id", help="Identifies the default audio file which will be played for calls when they arrive or are waiting in queue. This setting is available only for the Telephony channel type."),
    timezone: str = typer.Option(None, "--timezone", help="(Optional) Any routing strategy for this queue uses the time zone that you select here."),
    active: bool = typer.Option(None, "--active/--no-active", help="Specify whether the queue is active or not active"),
    outdial_campaign_enabled: bool = typer.Option(None, "--outdial-campaign-enabled/--no-outdial-campaign-enabled", help="Should be specified only for outdial queues; if enabled, then Call Distribution and Queue Routing Type can be specified."),
    monitoring_permitted: bool = typer.Option(None, "--monitoring-permitted/--no-monitoring-permitted", help="Indicates whether or not monitoring is permitted. This setting is available only for the Telephony channel type."),
    parking_permitted: bool = typer.Option(None, "--parking-permitted/--no-parking-permitted", help="Indicates whether or not parking is permitted. This setting is available only for the Telephony channel type."),
    recording_permitted: bool = typer.Option(None, "--recording-permitted/--no-recording-permitted", help="Indicates whether or not recording is permitted. This setting is available only for the Telephony channel type."),
    recording_all_calls_permitted: bool = typer.Option(None, "--recording-all-calls-permitted/--no-recording-all-calls-permitted", help="Indicates whether or not recording all calls is permitted. This setting is available only for the Telephony channel type."),
    pause_recording_permitted: bool = typer.Option(None, "--pause-recording-permitted/--no-pause-recording-permitted", help="Indicates whether or not pausing the recording is permitted. This setting is available only for the Telephony channel type."),
    recording_pause_duration: str = typer.Option(None, "--recording-pause-duration", help="The duration in seconds of pause in recording. This setting is available only for the Telephony channel type."),
    control_flow_script_url: str = typer.Option(None, "--control-flow-script-url", help="The URL for the queue or the default control script of the queue. If you do not use the routing strategy module to configure the control script, the system automatically populates the URL. This setting is available only for the Telephony channel type."),
    ivr_requeue_url: str = typer.Option(None, "--ivr-requeue-url", help="This setting is available only for the Telephony channel type."),
    overflow_number: str = typer.Option(None, "--overflow-number", help="The destination phone number to which the system distributes the customer calls when they exceed the Maximum Time in Queue that you have set in the routing strategy. This setting is applicable only for the Telephony channel type and it is optional."),
    vendor_id: str = typer.Option(None, "--vendor-id", help="The unique alphanumeric string that maps this queue to the vendor. This setting is available only for the Telephony channel type and it is optional."),
    routing_type: str = typer.Option(None, "--routing-type", help="Choices: LONGEST_AVAILABLE_AGENT, SKILLS_BASED, CIRCULAR, LINEAR"),
    skill_based_routing_type: str = typer.Option(None, "--skill-based-routing-type", help="Choices: LONGEST_AVAILABLE_AGENT, BEST_AVAILABLE_AGENT"),
    queue_routing_type: str = typer.Option(None, "--queue-routing-type", help="Choices: TEAM_BASED, SKILL_BASED, AGENT_BASED"),
    xsp_version: str = typer.Option(None, "--xsp-version", help="(Optional) Used to subscribe for recording events."),
    subscription_id: str = typer.Option(None, "--subscription-id", help="(Optional) Used to subscribe for recording events."),
    system_default: bool = typer.Option(None, "--system-default/--no-system-default", help="Indicates whether the created resource is system created or not"),
    manually_assignable: bool = typer.Option(None, "--manually-assignable/--no-manually-assignable", help="If `true`, the queue can be manually assigned."),
    agents_last_updated_by_user_name: str = typer.Option(None, "--agents-last-updated-by-user-name", help="The name of the user who last modified the agents list."),
    agents_last_updated_by_user_email_prefix: str = typer.Option(None, "--agents-last-updated-by-user-email-prefix", help="The email of the user who last modified the agents list."),
    agents_last_updated_time: str = typer.Option(None, "--agents-last-updated-time", help="The date when the agents list was last modified (epoch timestamp in milliseconds)."),
    queue_level_summaries_inclusion: str = typer.Option(None, "--queue-level-summaries-inclusion", help="Queue level summaries inclusion type. Used only when Queue inclusion for summaries is set to 'Specific Queues' at the org level AI Assistant->Summaries configuration. During entity creation(single or bulk), if this parameter is not provided or null, default will be set to 'EXCLUDED' During entity..."),
    queue_level_sentiment_analysis_inclusion: str = typer.Option(None, "--queue-level-sentiment-analysis-inclusion", help="Queue level sentiment analysis inclusion type. Used only when Queue inclusion for sentiment analysis is set to 'Specific Queues' at the org level AI Assistant->Quality Management configuration. During entity creation(single or bulk), if this parameter is not provided or null, default will be set to..."),
    queue_level_predicted_wait_time_inclusion: str = typer.Option(None, "--queue-level-predicted-wait-time-inclusion", help="Queue level predicted wait time inclusion type. Used only when Queue inclusion for predicted wait time is set to 'Specific Queues' at the org level AI Assistant->Predicted Wait Time configuration. During entity creation(single or bulk), if this parameter is not provided or null, default will be set..."),
    queue_level_auto_csat_inclusion: str = typer.Option(None, "--queue-level-auto-csat-inclusion", help="Queue level auto CSAT inclusion type. Used only when Queue inclusion for auto CSAT is set to 'Specific Queues' at the org level AI Assistant->Auto CSAT configuration. During entity creation(single or bulk), if this parameter is not provided or null, default will be set to 'EXCLUDED' During entity..."),
    queue_level_real_time_transcriptions_inclusion: str = typer.Option(None, "--queue-level-real-time-transcriptions-inclusion", help="Queue level real time transcriptions inclusion type. Used only when Queue inclusion for real time transcriptions is set to 'Specific Queues' at the org level AI Assistant->Real Time Transcriptions configuration. During entity creation(single or bulk), if this parameter is not provided or null,..."),
    created_time: str = typer.Option(None, "--created-time", help="This is the created time of the entity."),
    last_updated_time: str = typer.Option(None, "--last-updated-time", help="This is the updated time of the entity."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update specific Contact Service Queue by ID\n\nExample --json-body:\n  '{"name":"...","queueType":"INBOUND","checkAgentAvailability":true,"channelType":"TELEPHONY","serviceLevelThreshold":0,"maxActiveContacts":0,"maxTimeInQueue":0,"active":true}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CONTACT_SERVICE_QUEUE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/v2/contact-service-queue/{id}"
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
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if queue_type is not None:
            body["queueType"] = queue_type
        if check_agent_availability is not None:
            body["checkAgentAvailability"] = check_agent_availability
        if channel_type is not None:
            body["channelType"] = channel_type
        if social_channel_type is not None:
            body["socialChannelType"] = social_channel_type
        if service_level_threshold is not None:
            body["serviceLevelThreshold"] = service_level_threshold
        if max_active_contacts is not None:
            body["maxActiveContacts"] = max_active_contacts
        if max_time_in_queue is not None:
            body["maxTimeInQueue"] = max_time_in_queue
        if default_music_in_queue_media_file_id is not None:
            body["defaultMusicInQueueMediaFileId"] = default_music_in_queue_media_file_id
        if timezone is not None:
            body["timezone"] = timezone
        if active is not None:
            body["active"] = active
        if outdial_campaign_enabled is not None:
            body["outdialCampaignEnabled"] = outdial_campaign_enabled
        if monitoring_permitted is not None:
            body["monitoringPermitted"] = monitoring_permitted
        if parking_permitted is not None:
            body["parkingPermitted"] = parking_permitted
        if recording_permitted is not None:
            body["recordingPermitted"] = recording_permitted
        if recording_all_calls_permitted is not None:
            body["recordingAllCallsPermitted"] = recording_all_calls_permitted
        if pause_recording_permitted is not None:
            body["pauseRecordingPermitted"] = pause_recording_permitted
        if recording_pause_duration is not None:
            body["recordingPauseDuration"] = recording_pause_duration
        if control_flow_script_url is not None:
            body["controlFlowScriptUrl"] = control_flow_script_url
        if ivr_requeue_url is not None:
            body["ivrRequeueUrl"] = ivr_requeue_url
        if overflow_number is not None:
            body["overflowNumber"] = overflow_number
        if vendor_id is not None:
            body["vendorId"] = vendor_id
        if routing_type is not None:
            body["routingType"] = routing_type
        if skill_based_routing_type is not None:
            body["skillBasedRoutingType"] = skill_based_routing_type
        if queue_routing_type is not None:
            body["queueRoutingType"] = queue_routing_type
        if xsp_version is not None:
            body["xspVersion"] = xsp_version
        if subscription_id is not None:
            body["subscriptionId"] = subscription_id
        if system_default is not None:
            body["systemDefault"] = system_default
        if manually_assignable is not None:
            body["manuallyAssignable"] = manually_assignable
        if agents_last_updated_by_user_name is not None:
            body["agentsLastUpdatedByUserName"] = agents_last_updated_by_user_name
        if agents_last_updated_by_user_email_prefix is not None:
            body["agentsLastUpdatedByUserEmailPrefix"] = agents_last_updated_by_user_email_prefix
        if agents_last_updated_time is not None:
            body["agentsLastUpdatedTime"] = agents_last_updated_time
        if queue_level_summaries_inclusion is not None:
            body["queueLevelSummariesInclusion"] = queue_level_summaries_inclusion
        if queue_level_sentiment_analysis_inclusion is not None:
            body["queueLevelSentimentAnalysisInclusion"] = queue_level_sentiment_analysis_inclusion
        if queue_level_predicted_wait_time_inclusion is not None:
            body["queueLevelPredictedWaitTimeInclusion"] = queue_level_predicted_wait_time_inclusion
        if queue_level_auto_csat_inclusion is not None:
            body["queueLevelAutoCsatInclusion"] = queue_level_auto_csat_inclusion
        if queue_level_real_time_transcriptions_inclusion is not None:
            body["queueLevelRealTimeTranscriptionsInclusion"] = queue_level_real_time_transcriptions_inclusion
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
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": id}, output=output, fields=fields)



_BODY_SKELETON_CREATE_REASSIGN_AGENTS = '{"add":["..."],"remove":["..."]}'

@app.command("create-reassign-agents")
def create_reassign_agents(
    id: str = typer.Argument(help="id"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add or remove agents/users to/from an agent based queue\n\nExample --json-body:\n  '{"add":["..."],"remove":["..."]}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_REASSIGN_AGENTS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/v2/contact-service-queue/{id}/reassign-agents"
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



@app.command("list-contact-service-queue-v3")
def list_contact_service_queue_v3(
    filter_param: str = typer.Option(None, "--filter", help="Specify a filter based on which the results will be fetched. All the fields are supported except: organizationId, queueSkillRequirements, xspVersion, createdTime, lastUpdatedTime The examples below show some search queries - id==\"57efb0e6-5af0-4245-a67d-d3c5045cdb6e\" -..."),
    attributes: str = typer.Option(None, "--attributes", help="Specify the attributes to be returned. By default, all attributes are returned along with the specified columns. All attributes are supported. except (callDistributionGroups,queueSkillRequirements,links)"),
    search: str = typer.Option(None, "--search", help="Filter data based on the search keyword.Supported search columns(name, description) The examples below show some search queries - \"Cisco\" - field==\"name\";value==\"Cisco\" - fields=in=(\"name\",\"description\");value==\"Cisco\""),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    desktop_profile_filter: str = typer.Option(None, "--desktop-profile-filter", help="If set to true, the API will return only the data that the user has access to according to its Desktop Profile. If unspecified, the default value is false."),
    provisioning_view: str = typer.Option(None, "--provisioning-view", help="If set to true, the API will only return data that the user has access to, according to the User Profile. This query parameter is applicable only when desktopProfileFilter query parameter is false."),
    single_object_response: str = typer.Option(None, "--single-object-response", help="Specify whether to include array fields in the response. This query parameter should be used only when the response contains a single record. It is not supported for responses with multiple objects and throws an exception."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Contact Service Queues."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/v3/contact-service-queue"
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
    if desktop_profile_filter is not None:
        params["desktopProfileFilter"] = desktop_profile_filter
    if provisioning_view is not None:
        params["provisioningView"] = provisioning_view
    if single_object_response is not None:
        params["singleObjectResponse"] = single_object_response
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
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)


