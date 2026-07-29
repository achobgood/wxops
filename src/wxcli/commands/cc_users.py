import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import resolve_org_id, get_cc_base_url, get_cc_org_id


app = typer.Typer(help="Manage Webex Contact Center cc-users.")


@app.command("list", short_help="List Users.")
def cmd_list(
    filter_param: str = typer.Option(None, "--filter", help="Specify a filter based on which the results will be fetched. Supported filterable fields: id. The examples below show some search queries - id==\"57efb0e6-5af0-4245-a67d-d3c5045cdb6e\" - id!=\"57efb0e6-5af0-4245-a67d-d3c5045cdb6e\" -..."),
    attributes: str = typer.Option(None, "--attributes", help="Specify the attributes to be returned. By default, all attributes are returned along with the specified columns. All attributes are supported."),
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
    """List Users."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/user"
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
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('First Name', 'firstName'), ('Organization ID', 'organizationId'), ('Version', 'version'), ('Last Name', 'lastName')], limit=limit)



_BODY_SKELETON_UPDATE = '{"items":[{"itemIdentifier":0,"item":{"firstName":"...","lastName":"...","email":"...","ciUserId":"...","userProfileId":"...","contactCenterEnabled":true,"active":true,"organizationId":"...","id":"...","version":0,"workPhone":"...","mobile":"...","broadCloudUserId":"...","timezone":"...","xspVersion":"...","subscriptionId":"...","siteId":"...","teamIds":[{}],"skillProfileId":"...","agentProfileId":"...","multimediaProfileId":"...","deafultDialledNumber":"...","externalIdentifier":"...","imiUserCreated":true,"preferredSupervisorTeamId":"...","userLevelBurnoutInclusion":"INCLUDED","userLevelAutoCSATInclusion":"INCLUDED","userLevelWellnessBreakReminders":"DISABLED","userLevelSummariesInclusion":"INCLUDED","supervisorCapabilitiesEnabled":true,"agentCapabilitiesEnabled":true,"dynamicSkills":[{"skillId":"...","organizationId":"...","id":"...","version":0,"skillName":"...","textValue":"...","booleanValue":true,"proficiencyValue":0,"enumValue":"...","enumSkillValues":"...","createdTime":0,"lastUpdatedTime":0}],"createdTime":0,"lastUpdatedTime":0},"requestAction":"..."}]}'

@app.command("update", short_help="Bulk partial update Users.")
def update(
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk partial update Users.\n\n\b\nExample --json-body: '{"items":[{"itemIdentifier":0,"item":{"firstName":"...","lastName":"...","email":"...","ciUserId":"...","userProfileId":"...","contactCenterEnabled":true,"active":true,"organizationId":"...","id":"...","version":0,"workPhone":"...","mobile":"...","broadCloudUserId":"...","timezone":"...","xspVersion":"...","subscriptionId":"...","siteId":"...","teamIds":[{}],"skillProfileId":"...","agentProfileId":"...","multimediaProfileId":"...","deafultDialledNumber":"...","externalIdentifier":"...","imiUserCreated":true,"preferredSupervisorTeamId":"...","userLevelBurnoutInclusion":"INCLUDED","userLevelAutoCSATInclusion":"INCLUDED","userLevelWellnessBreakReminders":"DISABLED","userLevelSummariesInclusion":"INCLUDED","supervisorCapabilitiesEnabled":true,"agentCapabilitiesEnabled":true,"dynamicSkills":[{"skillId":"...","organizationId":"...","id":"...","version":0,"skillName":"...","textValue":"...","booleanValue":true,"proficiencyValue":0,"enumValue":"...","enumSkillValues":"...","createdTime":0,"lastUpdatedTime":0}],"createdTime":0,"lastUpdatedTime":0},"requestAction":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/user/bulk"
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



_BODY_SKELETON_UPDATE_DYNAMIC_SKILL = '{"items":[{"itemIdentifier":0,"item":{"organizationId":"...","id":"...","version":0,"userId":"...","enumSkillValues":["..."],"textValue":"...","booleanValue":true,"proficiencyValue":0,"skillId":"...","createdTime":0,"lastUpdatedTime":0},"requestAction":"..."}]}'

@app.command("update-update-dynamic-skill", hidden=True)
@app.command("update-dynamic-skill", short_help="Bulk partial update Users with dynamic skills.")
def update_dynamic_skill(
    skill_id: str = typer.Argument(help="UUID"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk partial update Users with dynamic skills.\n\n\b\nExample: wxcli cc-users update-dynamic-skill SKILL_ID\n\n\b\nExample --json-body: '{"items":[{"itemIdentifier":0,"item":{"organizationId":"...","id":"...","version":0,"userId":"...","enumSkillValues":["..."],"textValue":"...","booleanValue":true,"proficiencyValue":0,"skillId":"...","createdTime":0,"lastUpdatedTime":0},"requestAction":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_DYNAMIC_SKILL), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/user/bulk/update-dynamic-skill/{skill_id}"
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
        emit({"status": "updated", "id": skill_id}, output=output, fields=fields)



@app.command("show", short_help="List users by call monitoring id.")
def show(
    id: str = typer.Argument(help="UUID"),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """List users by call monitoring id.\n\n\b\nExample: wxcli cc-users show ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/user/by-call-monitoring-id/{id}"
    params = {}
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["pageSize"] = page_size
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-by-ci-user-id-organization", short_help="Get specific User by CI User ID.")
def show_by_ci_user_id_organization(
    id: str = typer.Argument(help="UUID"),
    include_user_profile: str = typer.Option(None, "--include-user-profile", help="Specifiy whether to include user profile data"),
    include_skill_details: str = typer.Option(None, "--include-skill-details", help="If set to true, the response includes skill information for each dynamic skill assignment."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get specific User by CI User ID.\n\n\b\nExample: wxcli cc-users show-by-ci-user-id-organization ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/user/by-ci-user-id/{id}"
    params = {}
    if include_user_profile is not None:
        params["includeUserProfile"] = include_user_profile
    if include_skill_details is not None:
        params["includeSkillDetails"] = include_skill_details
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-by-dynamic-skill-id", short_help="Get users by dynamic skill ID.")
def show_by_dynamic_skill_id(
    skill_id: str = typer.Argument(help="UUID"),
    search: str = typer.Option(None, "--search", help="Filter data based on the search keyword.Supported search columns(firstName, lastName, email, value) The examples below show some search queries - \"Cisco\""),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get users by dynamic skill ID.\n\n\b\nExample: wxcli cc-users show-by-dynamic-skill-id SKILL_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/user/by-dynamic-skill-id/{skill_id}"
    params = {}
    if search is not None:
        params["search"] = search
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["pageSize"] = page_size
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_CREATE = '{"skillRequirements":[{"skillId":"...","condition":"...","skillValue":"...","organizationId":"...","id":"...","version":0,"skillName":"...","skillType":"...","weight":0,"dynamicSkill":true,"createdTime":0,"lastUpdatedTime":0}]}'

@app.command("create", short_help="Get the agents matching skill requirements criteria.")
def create(
    search: str = typer.Option(None, "--search", help="Filter data based on the search keyword.Supported search columns(firstName, lastName, email) The examples below show some search queries - \"Cisco\" - field==\"firstName\";value==\"Cisco\" - fields=in=(\"firstName\",\"lastName\");value==\"Cisco\""),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get the agents matching skill requirements criteria.\n\n\b\nExample --json-body: '{"skillRequirements":[{"skillId":"...","condition":"...","skillValue":"...","organizationId":"...","id":"...","version":0,"skillName":"...","skillType":"...","weight":0,"dynamicSkill":true,"createdTime":0,"lastUpdatedTime":0}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/user/fetch-by-skill-requirements"
    params = {}
    if search is not None:
        params["search"] = search
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



_BODY_SKELETON_CREATE_FETCH_USER_DETAILS_BY_IDS = '{"userIds":[{}],"search":"...","queueId":"..."}'

@app.command("create-fetch-user-details-by-ids", short_help="List Users with details.")
def create_fetch_user_details_by_ids(
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    search: str = typer.Option(None, "--search", help="Text used to search for users (e.g., by firstName, lastName or email of the user). If provided, `queueId` is **required**. Cannot be used in combination with `userIds`."),
    queue_id: str = typer.Option(None, "--queue-id", help="Agent Based Queue ID to filter users . Required if `search` is provided. Cannot be used with `userIds`."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Users with details.\n\n\b\nExample --json-body: '{"userIds":[{}],"search":"...","queueId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_FETCH_USER_DETAILS_BY_IDS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/user/fetch-user-details-by-ids"
    params = {}
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["pageSize"] = page_size
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if search is not None:
            body["search"] = search
        if queue_id is not None:
            body["queueId"] = queue_id
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



@app.command("list-with-user-profile", short_help="List Users along with profile.")
def list_with_user_profile(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Users along with profile."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/user/with-user-profile"
    params = {}
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
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('First Name', 'firstName'), ('Organization ID', 'organizationId'), ('Version', 'version'), ('Last Name', 'lastName')], limit=limit)



@app.command("show-with-user-profile", short_help="Get specific User along with profile by ID.")
def show_with_user_profile(
    id: str = typer.Argument(help="UUID, from: wxcli cc-users list-with-user-profile"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get specific User along with profile by ID.\n\n\b\nExample: wxcli cc-users show-with-user-profile ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/user/with-user-profile/{id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-user", short_help="Get specific User by ID.")
def show_user(
    id: str = typer.Argument(help="UUID, from: wxcli cc-users list"),
    include_count: str = typer.Option(None, "--include-count", help="If set to true, the API response will include the count of each type of Contact Service Queue to which the user is assigned."),
    include_user_profile_type: str = typer.Option(None, "--include-user-profile-type", help="If set to true, the API response includes the User Profile."),
    include_skill_profile_audit: str = typer.Option(None, "--include-skill-profile-audit", help="If set to true gives skill profile modification info."),
    include_reskill_audit_info: str = typer.Option(None, "--include-reskill-audit-info", help="If set to true gives skill profile and dynamic skill modification info."),
    include_skill_details: str = typer.Option(None, "--include-skill-details", help="If set to true, the response includes skill information for each dynamic skill assignment."),
    check_if_user_has_dynamic_skill: str = typer.Option(None, "--check-if-user-has-dynamic-skill", help="If set to true, checks if user has the specified dynamic skill"),
    dynamic_skill_id: str = typer.Option(None, "--dynamic-skill-id", help="Dynamic skill ID to check if user has it assigned (required when checkIfUserHasDynamicSkill is true)"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get specific User by ID.\n\n\b\nExample: wxcli cc-users show-user ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/user/{id}"
    params = {}
    if include_count is not None:
        params["includeCount"] = include_count
    if include_user_profile_type is not None:
        params["includeUserProfileType"] = include_user_profile_type
    if include_skill_profile_audit is not None:
        params["includeSkillProfileAudit"] = include_skill_profile_audit
    if include_reskill_audit_info is not None:
        params["includeReskillAuditInfo"] = include_reskill_audit_info
    if include_skill_details is not None:
        params["includeSkillDetails"] = include_skill_details
    if check_if_user_has_dynamic_skill is not None:
        params["checkIfUserHasDynamicSkill"] = check_if_user_has_dynamic_skill
    if dynamic_skill_id is not None:
        params["dynamicSkillId"] = dynamic_skill_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_USER = '{"firstName":"...","lastName":"...","email":"...","ciUserId":"...","userProfileId":"...","contactCenterEnabled":true,"active":true,"organizationId":"...","id":"...","version":0,"workPhone":"...","mobile":"...","broadCloudUserId":"...","timezone":"...","xspVersion":"...","subscriptionId":"...","siteId":"...","teamIds":[{}],"skillProfileId":"...","agentProfileId":"...","multimediaProfileId":"...","deafultDialledNumber":"...","externalIdentifier":"...","imiUserCreated":true,"preferredSupervisorTeamId":"...","userLevelBurnoutInclusion":"INCLUDED","userLevelAutoCSATInclusion":"INCLUDED","userLevelWellnessBreakReminders":"DISABLED","userLevelSummariesInclusion":"INCLUDED","supervisorCapabilitiesEnabled":true,"agentCapabilitiesEnabled":true,"dynamicSkills":[{"skillId":"...","organizationId":"...","id":"...","version":0,"skillName":"...","textValue":"...","booleanValue":true,"proficiencyValue":0,"enumValue":"...","enumSkillValues":"...","createdTime":0,"lastUpdatedTime":0}],"createdTime":0,"lastUpdatedTime":0}'

@app.command("update-user", short_help="Update specific User by ID.")
def update_user(
    id: str = typer.Argument(help="UUID, from: wxcli cc-users list"),
    organization_id: str = typer.Option(None, "--organization-id", help="ID of the contact center organization. This field is required for all bulk save operations."),
    id_param: str = typer.Option(None, "--id", help="ID of this contact center resource. It should not be specified when creating a new resource. However, it is mandatory when updating a resource."),
    version: str = typer.Option(None, "--version", help="The version of this resource. For a newly created resource, it will be 0 unless specified otherwise."),
    first_name: str = typer.Option(None, "--first-name", help="The first name of the user. Can be changed using Users Management in Cisco Webex Control Hub."),
    last_name: str = typer.Option(None, "--last-name", help="The last name of the user. Can be changed using Users Management in Cisco Webex Control Hub."),
    email: str = typer.Option(None, "--email", help="The email address of the user. Can be changed using Users Management in Cisco Webex Control Hub."),
    work_phone: str = typer.Option(None, "--work-phone", help="The work phone number of the user."),
    mobile: str = typer.Option(None, "--mobile", help="The mobile phone number of the user."),
    ci_user_id: str = typer.Option(None, "--ci-user-id", help="Cisco Common Identity user Id. Existence of a CI user is a prerequisite to create a new WxCC user. It cannot be modified."),
    broad_cloud_user_id: str = typer.Option(None, "--broad-cloud-user-id", help="Broadcloud user Id. This field cannot be modified."),
    user_profile_id: str = typer.Option(None, "--user-profile-id", help="Identifier for an user profile which a Contact Center administrator has configured. Changing the profile type requires a token with `FLS:Read_Scope` scope. As of today, changing the profile type for a user is supported only from Cisco Webex Control Hub."),
    contact_center_enabled: bool = typer.Option(None, "--contact-center-enabled/--no-contact-center-enabled", help="The setting is for accessing the Agent Desktop to handle customer requests."),
    timezone: str = typer.Option(None, "--timezone", help="(Optional) The time zone that you provision for your enterprise."),
    xsp_version: str = typer.Option(None, "--xsp-version", help="(Optional) Used to subscribe for recording events. This field cannot be modified."),
    subscription_id: str = typer.Option(None, "--subscription-id", help="(Optional) Used to subscribe for recording events. This field cannot be modified."),
    site_id: str = typer.Option(None, "--site-id", help="(Optional) Identifier for a site which is a physical contact center location under the control of your enterprise. This field is applicable only when contactCenterEnabled is true."),
    skill_profile_id: str = typer.Option(None, "--skill-profile-id", help="(Optional) If your enterprise uses the optional Skills-Based Routing feature, This profile overrides any skill profile at the team level that is associated with the agent.This field is applicable only when contactCenterEnabled is true."),
    agent_profile_id: str = typer.Option(None, "--agent-profile-id", help="Identifier for a Desktop Profile which is a group of permissions and Agent Desktop behaviors that you assign to specific users. This field is applicable only when contactCenterEnabled is true."),
    multimedia_profile_id: str = typer.Option(None, "--multimedia-profile-id", help="(Optional) If your organization administrator enables Multimedia for your enterprise, you can select a multimedia profile for this team. This field is applicable only when contactCenterEnabled is true."),
    deafult_dialled_number: str = typer.Option(None, "--deafult-dialled-number", help="(Optional) The dial number of the agent. This field is applicable only when contactCenterEnabled is true."),
    external_identifier: str = typer.Option(None, "--external-identifier", help="(Optional) Agent identification details, such as the employee number."),
    active: bool = typer.Option(None, "--active/--no-active", help="Indicates whether the user is active or not active. Can be changed using Users Management in Cisco Webex Control Hub."),
    imi_user_created: bool = typer.Option(None, "--imi-user-created/--no-imi-user-created", help="(Optional) Indicates whether this user has a corresponding user created in IMI digital channel. This field cannot be modified."),
    preferred_supervisor_team_id: str = typer.Option(None, "--preferred-supervisor-team-id", help="(Optional) Indicates the id of a preferred supervisor."),
    user_level_burnout_inclusion: str = typer.Option(None, "--user-level-burnout-inclusion", help="Choices: INCLUDED, EXCLUDED"),
    user_level_auto_csat_inclusion: str = typer.Option(None, "--user-level-auto-csat-inclusion", help="Choices: INCLUDED, EXCLUDED"),
    user_level_wellness_break_reminders: str = typer.Option(None, "--user-level-wellness-break-reminders", help="Choices: DISABLED, ENABLED"),
    user_level_summaries_inclusion: str = typer.Option(None, "--user-level-summaries-inclusion", help="Choices: INCLUDED, EXCLUDED"),
    supervisor_capabilities_enabled: bool = typer.Option(None, "--supervisor-capabilities-enabled/--no-supervisor-capabilities-enabled", help="Indicates whether supervisor capabilities are enabled for the user."),
    agent_capabilities_enabled: bool = typer.Option(None, "--agent-capabilities-enabled/--no-agent-capabilities-enabled", help="Indicates whether agent capabilities are enabled for the user."),
    created_time: str = typer.Option(None, "--created-time", help="This is the created time of the entity."),
    last_updated_time: str = typer.Option(None, "--last-updated-time", help="This is the updated time of the entity."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update specific User by ID.\n\n\b\nExample: wxcli cc-users update-user ID --first-name FIRST_NAME --last-name LAST_NAME --email EMAIL --ci-user-id CI_USER_ID --user-profile-id USER_PROFILE_ID --contact-center-enabled --active\n\n\b\nExample --json-body: '{"firstName":"...","lastName":"...","email":"...","ciUserId":"...","userProfileId":"...","contactCenterEnabled":true,"active":true,"organizationId":"...","id":"...","version":0,"workPhone":"...","mobile":"...","broadCloudUserId":"...","timezone":"...","xspVersion":"...","subscriptionId":"...","siteId":"...","teamIds":[{}],"skillProfileId":"...","agentProfileId":"...","multimediaProfileId":"...","deafultDialledNumber":"...","externalIdentifier":"...","imiUserCreated":true,"preferredSupervisorTeamId":"...","userLevelBurnoutInclusion":"INCLUDED","userLevelAutoCSATInclusion":"INCLUDED","userLevelWellnessBreakReminders":"DISABLED","userLevelSummariesInclusion":"INCLUDED","supervisorCapabilitiesEnabled":true,"agentCapabilitiesEnabled":true,"dynamicSkills":[{"skillId":"...","organizationId":"...","id":"...","version":0,"skillName":"...","textValue":"...","booleanValue":true,"proficiencyValue":0,"enumValue":"...","enumSkillValues":"...","createdTime":0,"lastUpdatedTime":0}],"createdTime":0,"lastUpdatedTime":0}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_USER), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/user/{id}"
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
        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
        if email is not None:
            body["email"] = email
        if work_phone is not None:
            body["workPhone"] = work_phone
        if mobile is not None:
            body["mobile"] = mobile
        if ci_user_id is not None:
            body["ciUserId"] = ci_user_id
        if broad_cloud_user_id is not None:
            body["broadCloudUserId"] = broad_cloud_user_id
        if user_profile_id is not None:
            body["userProfileId"] = user_profile_id
        if contact_center_enabled is not None:
            body["contactCenterEnabled"] = contact_center_enabled
        if timezone is not None:
            body["timezone"] = timezone
        if xsp_version is not None:
            body["xspVersion"] = xsp_version
        if subscription_id is not None:
            body["subscriptionId"] = subscription_id
        if site_id is not None:
            body["siteId"] = site_id
        if skill_profile_id is not None:
            body["skillProfileId"] = skill_profile_id
        if agent_profile_id is not None:
            body["agentProfileId"] = agent_profile_id
        if multimedia_profile_id is not None:
            body["multimediaProfileId"] = multimedia_profile_id
        if deafult_dialled_number is not None:
            body["deafultDialledNumber"] = deafult_dialled_number
        if external_identifier is not None:
            body["externalIdentifier"] = external_identifier
        if active is not None:
            body["active"] = active
        if imi_user_created is not None:
            body["imiUserCreated"] = imi_user_created
        if preferred_supervisor_team_id is not None:
            body["preferredSupervisorTeamId"] = preferred_supervisor_team_id
        if user_level_burnout_inclusion is not None:
            body["userLevelBurnoutInclusion"] = user_level_burnout_inclusion
        if user_level_auto_csat_inclusion is not None:
            body["userLevelAutoCSATInclusion"] = user_level_auto_csat_inclusion
        if user_level_wellness_break_reminders is not None:
            body["userLevelWellnessBreakReminders"] = user_level_wellness_break_reminders
        if user_level_summaries_inclusion is not None:
            body["userLevelSummariesInclusion"] = user_level_summaries_inclusion
        if supervisor_capabilities_enabled is not None:
            body["supervisorCapabilitiesEnabled"] = supervisor_capabilities_enabled
        if agent_capabilities_enabled is not None:
            body["agentCapabilitiesEnabled"] = agent_capabilities_enabled
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



@app.command("list-incoming-references", short_help="List references for a specific User.")
def list_incoming_references(
    id: str = typer.Argument(help="UUID, from: wxcli cc-users list"),
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
    """List references for a specific User.\n\n\b\nExample: wxcli cc-users list-incoming-references ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/user/{id}/incoming-references"
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
            result = list(api.session.follow_page_param(url=url, params=params, item_key="data"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("data", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Created Date', 'createdDate'), ('Last Modified Date', 'lastModifiedDate'), ('Version', 'version')], limit=limit)



_BODY_SKELETON_UPDATE_RESKILL = '{"organizationId":"...","id":"...","version":0,"skillProfileId":"...","dynamicSkills":{"add":[{"organizationId":"...","id":"...","version":0,"userId":"...","enumSkillValues":["..."],"textValue":"...","booleanValue":true,"proficiencyValue":0,"skillId":"...","createdTime":0,"lastUpdatedTime":0}],"remove":["..."]},"createdTime":0,"lastUpdatedTime":0}'

@app.command("update-reskill", short_help="Reskill Agents.")
def update_reskill(
    id: str = typer.Argument(help="UUID, from: wxcli cc-users list"),
    organization_id: str = typer.Option(None, "--organization-id", help="ID of the contact center organization. This field is required for all bulk save operations."),
    id_param: str = typer.Option(None, "--id", help="ID of this contact center resource. It should not be specified when creating a new resource. However, it is mandatory when updating a resource."),
    version: str = typer.Option(None, "--version", help="The version of this resource. For a newly created resource, it will be 0 unless specified otherwise."),
    skill_profile_id: str = typer.Option(None, "--skill-profile-id", help="The unique identifier of the skill profile to assign to the agent"),
    created_time: str = typer.Option(None, "--created-time", help="This is the created time of the entity."),
    last_updated_time: str = typer.Option(None, "--last-updated-time", help="This is the updated time of the entity."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Reskill Agents.\n\n\b\nExample: wxcli cc-users update-reskill ID\n\n\b\nExample --json-body: '{"organizationId":"...","id":"...","version":0,"skillProfileId":"...","dynamicSkills":{"add":[{"organizationId":"...","id":"...","version":0,"userId":"...","enumSkillValues":["..."],"textValue":"...","booleanValue":true,"proficiencyValue":0,"skillId":"...","createdTime":0,"lastUpdatedTime":0}],"remove":["..."]},"createdTime":0,"lastUpdatedTime":0}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_RESKILL), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/user/{id}/reskill"
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
        if skill_profile_id is not None:
            body["skillProfileId"] = skill_profile_id
        if created_time is not None:
            body["createdTime"] = created_time
        if last_updated_time is not None:
            body["lastUpdatedTime"] = last_updated_time
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
        emit({"status": "updated", "id": id}, output=output, fields=fields)



@app.command("list-user", short_help="List Users.")
def list_user(
    filter_param: str = typer.Option(None, "--filter", help="Specify a filter based on which the results will be fetched. All the fields are supported except: organizationId, xspVersion, createdTime, lastUpdatedTime The examples below show some search queries - id==\"57efb0e6-5af0-4245-a67d-d3c5045cdb6e\" - id!=\"57efb0e6-5af0-4245-a67d-d3c5045cdb6e\" -..."),
    attributes: str = typer.Option(None, "--attributes", help="Specify the attributes to be returned. By default, all attributes are returned along with the specified columns. All attributes are supported."),
    search: str = typer.Option(None, "--search", help="Filter data based on the search keyword.Supported search columns(firstName, lastName, email) The examples below show some search queries - \"Cisco\" - field==\"firstName\";value==\"Cisco\" - fields=in=(\"firstName\",\"lastName\");value==\"Cisco\""),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    supervisor_managed_agents_only: str = typer.Option(None, "--supervisor-managed-agents-only", help="If set to true, the API will return contact center enabled users based on the invoking supervisor user's user profile access rights to sites and teams."),
    single_object_response: str = typer.Option(None, "--single-object-response", help="Specify whether to include array fields in the response. This query parameter should be used only when the response contains a single record. It is not supported for responses with multiple objects and throws an exception."),
    buddy_team_agents_only: str = typer.Option(None, "--buddy-team-agents-only", help="If set to true, returns only users who are part of buddy teams without PBAC check."),
    user_in_queue: str = typer.Option(None, "--user-in-queue", help="Can be either assigned or unassigned. If passed, returns the users who are assigned or not assigned to an agent based queue managed by the supervisor."),
    queue_id: str = typer.Option(None, "--queue-id", help="Contact Service Queue ID for which the list of assigned or unassigned agents must be fetched."),
    include_ai_mapping_count: str = typer.Option(None, "--include-ai-mapping-count", help="If set to true, the API response will include the count of each AI feature mapped to the entity."),
    include_dynamic_skills_limit_reached: str = typer.Option(None, "--include-dynamic-skills-limit-reached", help="If true, includes whether each user has reached the dynamic skills assignment limit."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Users."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/v2/user"
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
    if supervisor_managed_agents_only is not None:
        params["supervisorManagedAgentsOnly"] = supervisor_managed_agents_only
    if single_object_response is not None:
        params["singleObjectResponse"] = single_object_response
    if buddy_team_agents_only is not None:
        params["buddyTeamAgentsOnly"] = buddy_team_agents_only
    if user_in_queue is not None:
        params["userInQueue"] = user_in_queue
    if queue_id is not None:
        params["queueId"] = queue_id
    if include_ai_mapping_count is not None:
        params["includeAIMappingCount"] = include_ai_mapping_count
    if include_dynamic_skills_limit_reached is not None:
        params["includeDynamicSkillsLimitReached"] = include_dynamic_skills_limit_reached
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_page_param(url=url, params=params, item_key="data"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("data", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('First Name', 'firstName'), ('Organization ID', 'organizationId'), ('Version', 'version'), ('Last Name', 'lastName')], limit=limit)



@app.command("show-by-ci-user-id-v2", short_help="Get specific User by CI User ID.")
def show_by_ci_user_id_v2(
    id: str = typer.Argument(help="UUID"),
    include_user_profile: str = typer.Option(None, "--include-user-profile", help="Specifiy whether to include user profile data"),
    include_names: str = typer.Option(None, "--include-names", help="Specifiy whether to include resource collection names"),
    include_skill_details: str = typer.Option(None, "--include-skill-details", help="If set to true, the response includes skill information for each dynamic skill assignment."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get specific User by CI User ID.\n\n\b\nExample: wxcli cc-users show-by-ci-user-id-v2 ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/v2/user/by-ci-user-id/{id}"
    params = {}
    if include_user_profile is not None:
        params["includeUserProfile"] = include_user_profile
    if include_names is not None:
        params["includeNames"] = include_names
    if include_skill_details is not None:
        params["includeSkillDetails"] = include_skill_details
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)


