import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import resolve_org_id, get_cc_base_url, get_cc_org_id
from wxcli.common import verify_write


app = typer.Typer(help="Manage Webex Contact Center cc-monitoring-schedules.")


_BODY_SKELETON_CREATE = '{"name":"...","timezone":"...","recurrence":true,"teams":[{"id":"...","name":"..."}],"contactServiceQueues":[{"id":"...","name":"..."}],"startTimestamp":0,"endTimestamp":0,"userId":"...","paused":true,"organizationId":"...","id":"...","version":0,"daysOfWeek":["SUN"],"agentsAccessType":"...","agents":[{"id":"...","userDetails":{"firstName":"...","lastName":"...","email":"..."}}],"userDetails":{"firstName":"...","lastName":"...","email":"..."},"filtersCount":{"specificAgents":0,"specificCsqs":0,"specificTeams":0},"createdTime":0,"lastUpdatedTime":0}'

@app.command("create", short_help="Create a new Call Monitoring.")
def create(
    organization_id: str = typer.Option(None, "--organization-id", help="ID of the contact center organization. This field is required for all bulk save operations."),
    id_param: str = typer.Option(None, "--id", help="ID of this contact center resource. It should not be specified when creating a new resource. However, it is mandatory when updating a resource."),
    version: str = typer.Option(None, "--version", help="The version of this resource. For a newly created resource, it will be 0 unless specified otherwise."),
    name: str = typer.Option(None, "--name", help="(required) Name of the call monitoring schedule"),
    timezone: str = typer.Option(None, "--timezone", help="(required) (Optional) The time zone that you provision for your enterprise."),
    recurrence: bool = typer.Option(None, "--recurrence/--no-recurrence", help="(required) Indicates if this is a recurring schedule"),
    agents_access_type: str = typer.Option(None, "--agents-access-type", help="Access type for agents - ALL or SPECIFIC"),
    start_timestamp: str = typer.Option(None, "--start-timestamp", help="(required) Start timestamp of the schedule in epoch milliseconds (UTC)"),
    end_timestamp: str = typer.Option(None, "--end-timestamp", help="(required) End timestamp of the schedule in epoch milliseconds (UTC)"),
    user_id: str = typer.Option(None, "--user-id", help="(required) User ID of the supervisor who created/owns this schedule"),
    paused: bool = typer.Option(None, "--paused/--no-paused", help="(required) Indicates if the schedule is paused"),
    created_time: str = typer.Option(None, "--created-time", help="This is the created time of the entity."),
    last_updated_time: str = typer.Option(None, "--last-updated-time", help="This is the updated time of the entity."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new Call Monitoring.\n\n\b\nExample: wxcli cc-monitoring-schedules create --json-body '{"name":"...","timezone":"...","recurrence":true,"teams":[{"id":"...","name":"..."}],"contactServiceQueues":[{"id":"...","name":"..."}],"startTimestamp":0,"endTimestamp":0,"userId":"...","paused":true}'\n\n\b\nExample --json-body: '{"name":"...","timezone":"...","recurrence":true,"teams":[{"id":"...","name":"..."}],"contactServiceQueues":[{"id":"...","name":"..."}],"startTimestamp":0,"endTimestamp":0,"userId":"...","paused":true,"organizationId":"...","id":"...","version":0,"daysOfWeek":["SUN"],"agentsAccessType":"...","agents":[{"id":"...","userDetails":{"firstName":"...","lastName":"...","email":"..."}}],"userDetails":{"firstName":"...","lastName":"...","email":"..."},"filtersCount":{"specificAgents":0,"specificCsqs":0,"specificTeams":0},"createdTime":0,"lastUpdatedTime":0}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/call-monitoring"
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
        if timezone is not None:
            body["timezone"] = timezone
        if recurrence is not None:
            body["recurrence"] = recurrence
        if agents_access_type is not None:
            body["agentsAccessType"] = agents_access_type
        if start_timestamp is not None:
            body["startTimestamp"] = start_timestamp
        if end_timestamp is not None:
            body["endTimestamp"] = end_timestamp
        if user_id is not None:
            body["userId"] = user_id
        if paused is not None:
            body["paused"] = paused
        if created_time is not None:
            body["createdTime"] = created_time
        if last_updated_time is not None:
            body["lastUpdatedTime"] = last_updated_time
        _missing = [f for f in ['name', 'timezone', 'recurrence', 'startTimestamp', 'endTimestamp', 'userId', 'paused'] if f not in body or body[f] is None]
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



_BODY_SKELETON_CREATE_DELETE_REFERENCE = '{"references":{}}'

@app.command("create-delete-reference", short_help="deleteReferencesCallMonitoring.")
def create_delete_reference(
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """deleteReferencesCallMonitoring.\n\n\b\nExample --json-body: '{"references":{}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_DELETE_REFERENCE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/call-monitoring/delete-reference"
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



@app.command("show", short_help="Get specific Call Monitoring by ID.")
def show(
    id: str = typer.Argument(help="UUID"),
    include_filter_details: str = typer.Option(None, "--include-filter-details", help="If set to true, the API response will include entity details (names) for teams, agents, and contact service queues."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get specific Call Monitoring by ID.\n\n\b\nExample: wxcli cc-monitoring-schedules show ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/call-monitoring/{id}"
    params = {}
    if include_filter_details is not None:
        params["includeFilterDetails"] = include_filter_details
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"name":"...","timezone":"...","recurrence":true,"teams":[{"id":"...","name":"..."}],"contactServiceQueues":[{"id":"...","name":"..."}],"startTimestamp":0,"endTimestamp":0,"userId":"...","paused":true,"organizationId":"...","id":"...","version":0,"daysOfWeek":["SUN"],"agentsAccessType":"...","agents":[{"id":"...","userDetails":{"firstName":"...","lastName":"...","email":"..."}}],"userDetails":{"firstName":"...","lastName":"...","email":"..."},"filtersCount":{"specificAgents":0,"specificCsqs":0,"specificTeams":0},"createdTime":0,"lastUpdatedTime":0}'

@app.command("update", short_help="Update specific Call Monitoring by ID.")
def update(
    id: str = typer.Argument(help="UUID"),
    organization_id: str = typer.Option(None, "--organization-id", help="ID of the contact center organization. This field is required for all bulk save operations."),
    id_param: str = typer.Option(None, "--id", help="ID of this contact center resource. It should not be specified when creating a new resource. However, it is mandatory when updating a resource."),
    version: str = typer.Option(None, "--version", help="The version of this resource. For a newly created resource, it will be 0 unless specified otherwise."),
    name: str = typer.Option(None, "--name", help="Name of the call monitoring schedule"),
    timezone: str = typer.Option(None, "--timezone", help="(Optional) The time zone that you provision for your enterprise."),
    recurrence: bool = typer.Option(None, "--recurrence/--no-recurrence", help="Indicates if this is a recurring schedule"),
    agents_access_type: str = typer.Option(None, "--agents-access-type", help="Access type for agents - ALL or SPECIFIC"),
    start_timestamp: str = typer.Option(None, "--start-timestamp", help="Start timestamp of the schedule in epoch milliseconds (UTC)"),
    end_timestamp: str = typer.Option(None, "--end-timestamp", help="End timestamp of the schedule in epoch milliseconds (UTC)"),
    user_id: str = typer.Option(None, "--user-id", help="User ID of the supervisor who created/owns this schedule"),
    paused: bool = typer.Option(None, "--paused/--no-paused", help="Indicates if the schedule is paused"),
    created_time: str = typer.Option(None, "--created-time", help="This is the created time of the entity."),
    last_updated_time: str = typer.Option(None, "--last-updated-time", help="This is the updated time of the entity."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update specific Call Monitoring by ID.\n\n\b\nExample: wxcli cc-monitoring-schedules update ID --json-body '{"name":"...","timezone":"...","recurrence":true,"teams":[{"id":"...","name":"..."}],"contactServiceQueues":[{"id":"...","name":"..."}],"startTimestamp":0,"endTimestamp":0,"userId":"...","paused":true}'\n\n\b\nExample --json-body: '{"name":"...","timezone":"...","recurrence":true,"teams":[{"id":"...","name":"..."}],"contactServiceQueues":[{"id":"...","name":"..."}],"startTimestamp":0,"endTimestamp":0,"userId":"...","paused":true,"organizationId":"...","id":"...","version":0,"daysOfWeek":["SUN"],"agentsAccessType":"...","agents":[{"id":"...","userDetails":{"firstName":"...","lastName":"...","email":"..."}}],"userDetails":{"firstName":"...","lastName":"...","email":"..."},"filtersCount":{"specificAgents":0,"specificCsqs":0,"specificTeams":0},"createdTime":0,"lastUpdatedTime":0}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/call-monitoring/{id}"
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
        if timezone is not None:
            body["timezone"] = timezone
        if recurrence is not None:
            body["recurrence"] = recurrence
        if agents_access_type is not None:
            body["agentsAccessType"] = agents_access_type
        if start_timestamp is not None:
            body["startTimestamp"] = start_timestamp
        if end_timestamp is not None:
            body["endTimestamp"] = end_timestamp
        if user_id is not None:
            body["userId"] = user_id
        if paused is not None:
            body["paused"] = paused
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
    if verify:
        verify_write(api, url, None, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": id}, output=output, fields=fields)



_BODY_SKELETON_UPDATE_CALL_MONITORING = '{"name":"...","timezone":"...","recurrence":true,"teams":[{"id":"...","name":"..."}],"contactServiceQueues":[{"id":"...","name":"..."}],"startTimestamp":0,"endTimestamp":0,"userId":"...","paused":true,"organizationId":"...","id":"...","version":0,"daysOfWeek":["SUN"],"agentsAccessType":"...","agents":[{"id":"...","userDetails":{"firstName":"...","lastName":"...","email":"..."}}],"userDetails":{"firstName":"...","lastName":"...","email":"..."},"filtersCount":{"specificAgents":0,"specificCsqs":0,"specificTeams":0},"createdTime":0,"lastUpdatedTime":0}'

@app.command("update-call-monitoring", short_help="Partially update Call Monitoring by ID.")
def update_call_monitoring(
    id: str = typer.Argument(help="UUID"),
    organization_id: str = typer.Option(None, "--organization-id", help="ID of the contact center organization. This field is required for all bulk save operations."),
    id_param: str = typer.Option(None, "--id", help="ID of this contact center resource. It should not be specified when creating a new resource. However, it is mandatory when updating a resource."),
    version: str = typer.Option(None, "--version", help="The version of this resource. For a newly created resource, it will be 0 unless specified otherwise."),
    name: str = typer.Option(None, "--name", help="Name of the call monitoring schedule"),
    timezone: str = typer.Option(None, "--timezone", help="(Optional) The time zone that you provision for your enterprise."),
    recurrence: bool = typer.Option(None, "--recurrence/--no-recurrence", help="Indicates if this is a recurring schedule"),
    agents_access_type: str = typer.Option(None, "--agents-access-type", help="Access type for agents - ALL or SPECIFIC"),
    start_timestamp: str = typer.Option(None, "--start-timestamp", help="Start timestamp of the schedule in epoch milliseconds (UTC)"),
    end_timestamp: str = typer.Option(None, "--end-timestamp", help="End timestamp of the schedule in epoch milliseconds (UTC)"),
    user_id: str = typer.Option(None, "--user-id", help="User ID of the supervisor who created/owns this schedule"),
    paused: bool = typer.Option(None, "--paused/--no-paused", help="Indicates if the schedule is paused"),
    created_time: str = typer.Option(None, "--created-time", help="This is the created time of the entity."),
    last_updated_time: str = typer.Option(None, "--last-updated-time", help="This is the updated time of the entity."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Partially update Call Monitoring by ID.\n\n\b\nExample: wxcli cc-monitoring-schedules update-call-monitoring ID --json-body '{"name":"...","timezone":"...","recurrence":true,"teams":[{"id":"...","name":"..."}],"contactServiceQueues":[{"id":"...","name":"..."}],"startTimestamp":0,"endTimestamp":0,"userId":"...","paused":true}'\n\n\b\nExample --json-body: '{"name":"...","timezone":"...","recurrence":true,"teams":[{"id":"...","name":"..."}],"contactServiceQueues":[{"id":"...","name":"..."}],"startTimestamp":0,"endTimestamp":0,"userId":"...","paused":true,"organizationId":"...","id":"...","version":0,"daysOfWeek":["SUN"],"agentsAccessType":"...","agents":[{"id":"...","userDetails":{"firstName":"...","lastName":"...","email":"..."}}],"userDetails":{"firstName":"...","lastName":"...","email":"..."},"filtersCount":{"specificAgents":0,"specificCsqs":0,"specificTeams":0},"createdTime":0,"lastUpdatedTime":0}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CALL_MONITORING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/call-monitoring/{id}"
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
        if timezone is not None:
            body["timezone"] = timezone
        if recurrence is not None:
            body["recurrence"] = recurrence
        if agents_access_type is not None:
            body["agentsAccessType"] = agents_access_type
        if start_timestamp is not None:
            body["startTimestamp"] = start_timestamp
        if end_timestamp is not None:
            body["endTimestamp"] = end_timestamp
        if user_id is not None:
            body["userId"] = user_id
        if paused is not None:
            body["paused"] = paused
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
    if verify:
        verify_write(api, url, None, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": id}, output=output, fields=fields)



@app.command("delete", short_help="Delete specific Call Monitoring by ID.")
def delete(
    id: str = typer.Argument(help="UUID"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete specific Call Monitoring by ID.\n\n\b\nExample: wxcli cc-monitoring-schedules delete ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    url = f"{cc_base_url}/organization/{orgid}/call-monitoring/{id}"
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



@app.command("list", short_help="List Call Monitoring Configurations.")
def cmd_list(
    filter_param: str = typer.Option(None, "--filter", help="Specify a filter based on which the results will be fetched. All the fields are supported except: organizationId, teams, agents, contactServiceQueues, createdTime, lastUpdatedTime The examples below show some search queries - id==\"57efb0e6-5af0-4245-a67d-d3c5045cdb6e\" -..."),
    attributes: str = typer.Option(None, "--attributes", help="Specify the attributes to be returned. By default, all attributes are returned along with the specified columns. All attributes are supported. except teams, agents, contactServiceQueues The examples below show some search queries - id==\"57efb0e6-5af0-4245-a67d-d3c5045cdb6e\" -..."),
    search: str = typer.Option(None, "--search", help="Filter data based on the search keyword.Supported search columns(name) The examples below show some search queries - \"Cisco\" - field==\"name\";value==\"Cisco\" - fields=in=(\"name\");value==\"Cisco\""),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    include_user_details: str = typer.Option(None, "--include-user-details", help="If set to true, the API response will include user details (firstName, lastName, email) for the userId field."),
    include_filters_count: str = typer.Option(None, "--include-filters-count", help="If set to true, the API response will include the count of specific agents, teams, and contact service queues associated with the call monitoring schedule."),
    include_total_call_monitoring_count_in_org: str = typer.Option(None, "--include-total-call-monitoring-count-in-org", help="If set to true, the API response will include the total number of call monitoring schedules for the organization in the metadata."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Call Monitoring Configurations."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/v2/call-monitoring"
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
    if include_user_details is not None:
        params["includeUserDetails"] = include_user_details
    if include_filters_count is not None:
        params["includeFiltersCount"] = include_filters_count
    if include_total_call_monitoring_count_in_org is not None:
        params["includeTotalCallMonitoringCountInOrg"] = include_total_call_monitoring_count_in_org
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


