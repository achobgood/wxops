import json
import typer
from wxcli.errors import WebexError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id, get_cc_base_url


app = typer.Typer(help="Manage Webex Contact Center cc-queue.")


@app.command("create")
def create(
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk save Contact Service Queue(s)\n\nExample --json-body:\n  '{"items":[{"item":"...","itemIdentifier":"...","requestAction":"..."}]}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_org_id() or api.people.me().org_id
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/bulk"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
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



@app.command("update")
def update(
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk partial update Contact Service Queue(s)\n\nExample --json-body:\n  '{"items":[{"item":"...","itemIdentifier":"...","requestAction":"..."}]}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_org_id() or api.people.me().org_id
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/bulk"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_patch(url, json=body)
    except WebexError as e:
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
    typer.echo(f"Updated.")



@app.command("list")
def cmd_list(
    type_param: str = typer.Option(None, "--type", help="Indicates the queue type; can be INBOUND or OUTBOUND."),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts"),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If th"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk export Contact Service Queue(s)."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_org_id() or api.people.me().org_id
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/bulk-export"
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
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
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("show")
def show(
    id: str = typer.Argument(help="id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get specific By skill profile ID."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_org_id() or api.people.me().org_id
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/by-skill-profile-id/{id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
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
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("create-fetch-manually-assignable-queues")
def create_fetch_manually_assignable_queues(
    team_id: str = typer.Option(None, "--team-id", help=""),
    agent_id: str = typer.Option(None, "--agent-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Fetch manually assignable Queues."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_org_id() or api.people.me().org_id
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/fetch-manually-assignable-queues"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if team_id is not None:
            body["teamId"] = team_id
        if agent_id is not None:
            body["agentId"] = agent_id
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
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



@app.command("list-incoming-references")
def list_incoming_references(
    id: str = typer.Argument(help="id"),
    type_param: str = typer.Option(None, "--type", help="Entity type of the other entity that has a reference to this"),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts"),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If th"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List references for a specific Contact Service Queue."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_org_id() or api.people.me().org_id
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
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
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-contact-service-queue-v2")
def list_contact_service_queue_v2(
    filter_param: str = typer.Option(None, "--filter", help="Specify a filter based on which the results will be fetched."),
    attributes: str = typer.Option(None, "--attributes", help="Specify the attributes to be returned.Default all attributes"),
    search: str = typer.Option(None, "--search", help="Filter data based on the search keyword.Supported search col"),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts"),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If th"),
    desktop_profile_filter: str = typer.Option(None, "--desktop-profile-filter", help="If set to true, the API will return only the data that the u"),
    provisioning_view: str = typer.Option(None, "--provisioning-view", help="If set to true, the API will only return data that user has"),
    single_object_response: str = typer.Option(None, "--single-object-response", help="Specifiy whether to include array fields in the response, Th"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Contact Service Queue(s)."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_org_id() or api.people.me().org_id
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
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
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
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create-contact-service-queue-v2")
def create_contact_service_queue_v2(
    channel_type: str = typer.Option(None, "--channel-type", help=""),
    check_agent_availability: str = typer.Option(None, "--check-agent-availability", help=""),
    control_flow_script_url: str = typer.Option(None, "--control-flow-script-url", help=""),
    default_music_in_queue_media_file_id: str = typer.Option(None, "--default-music-in-queue-media-file-id", help=""),
    ivr_requeue_url: str = typer.Option(None, "--ivr-requeue-url", help=""),
    max_active_contacts: str = typer.Option(None, "--max-active-contacts", help=""),
    max_time_in_queue: str = typer.Option(None, "--max-time-in-queue", help=""),
    monitoring_permitted: str = typer.Option(None, "--monitoring-permitted", help=""),
    parking_permitted: str = typer.Option(None, "--parking-permitted", help=""),
    pause_recording_permitted: str = typer.Option(None, "--pause-recording-permitted", help=""),
    queue_routing_type: str = typer.Option(None, "--queue-routing-type", help=""),
    queue_type: str = typer.Option(None, "--queue-type", help=""),
    recording_all_calls_permitted: str = typer.Option(None, "--recording-all-calls-permitted", help=""),
    recording_permitted: str = typer.Option(None, "--recording-permitted", help=""),
    routing_type: str = typer.Option(None, "--routing-type", help=""),
    service_level_threshold: str = typer.Option(None, "--service-level-threshold", help=""),
    version: str = typer.Option(None, "--version", help=""),
    outdial_campaign_enabled: str = typer.Option(None, "--outdial-campaign-enabled", help=""),
    recording_pause_duration: str = typer.Option(None, "--recording-pause-duration", help=""),
    overflow_number: str = typer.Option(None, "--overflow-number", help=""),
    vendor_id: str = typer.Option(None, "--vendor-id", help=""),
    skill_based_routing_type: str = typer.Option(None, "--skill-based-routing-type", help=""),
    timezone: str = typer.Option(None, "--timezone", help=""),
    xsp_version: str = typer.Option(None, "--xsp-version", help=""),
    subscription_id: str = typer.Option(None, "--subscription-id", help=""),
    manually_assignable: str = typer.Option(None, "--manually-assignable", help=""),
    agents_last_updated_by_user_name: str = typer.Option(None, "--agents-last-updated-by-user-name", help=""),
    agents_last_updated_by_user_email_prefix: str = typer.Option(None, "--agents-last-updated-by-user-email-prefix", help=""),
    agents_last_updated_time: str = typer.Option(None, "--agents-last-updated-time", help=""),
    active: str = typer.Option(None, "--active", help=""),
    description: str = typer.Option(None, "--description", help=""),
    system_default: str = typer.Option(None, "--system-default", help=""),
    id_param: str = typer.Option(None, "--id", help=""),
    organization_id: str = typer.Option(None, "--organization-id", help=""),
    name: str = typer.Option(None, "--name", help=""),
    social_channel_type: str = typer.Option(None, "--social-channel-type", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new Contact Service Queue\n\nExample --json-body:\n  '{"channelType":"...","checkAgentAvailability":"...","controlFlowScriptUrl":"...","defaultMusicInQueueMediaFileId":"...","ivrRequeueUrl":"...","maxActiveContacts":"..."}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_org_id() or api.people.me().org_id
    url = f"{cc_base_url}/organization/{orgid}/v2/contact-service-queue"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if channel_type is not None:
            body["channelType"] = channel_type
        if check_agent_availability is not None:
            body["checkAgentAvailability"] = check_agent_availability
        if control_flow_script_url is not None:
            body["controlFlowScriptUrl"] = control_flow_script_url
        if default_music_in_queue_media_file_id is not None:
            body["defaultMusicInQueueMediaFileId"] = default_music_in_queue_media_file_id
        if ivr_requeue_url is not None:
            body["ivrRequeueUrl"] = ivr_requeue_url
        if max_active_contacts is not None:
            body["maxActiveContacts"] = max_active_contacts
        if max_time_in_queue is not None:
            body["maxTimeInQueue"] = max_time_in_queue
        if monitoring_permitted is not None:
            body["monitoringPermitted"] = monitoring_permitted
        if parking_permitted is not None:
            body["parkingPermitted"] = parking_permitted
        if pause_recording_permitted is not None:
            body["pauseRecordingPermitted"] = pause_recording_permitted
        if queue_routing_type is not None:
            body["queueRoutingType"] = queue_routing_type
        if queue_type is not None:
            body["queueType"] = queue_type
        if recording_all_calls_permitted is not None:
            body["recordingAllCallsPermitted"] = recording_all_calls_permitted
        if recording_permitted is not None:
            body["recordingPermitted"] = recording_permitted
        if routing_type is not None:
            body["routingType"] = routing_type
        if service_level_threshold is not None:
            body["serviceLevelThreshold"] = service_level_threshold
        if version is not None:
            body["version"] = version
        if outdial_campaign_enabled is not None:
            body["outdialCampaignEnabled"] = outdial_campaign_enabled
        if recording_pause_duration is not None:
            body["recordingPauseDuration"] = recording_pause_duration
        if overflow_number is not None:
            body["overflowNumber"] = overflow_number
        if vendor_id is not None:
            body["vendorId"] = vendor_id
        if skill_based_routing_type is not None:
            body["skillBasedRoutingType"] = skill_based_routing_type
        if timezone is not None:
            body["timezone"] = timezone
        if xsp_version is not None:
            body["xspVersion"] = xsp_version
        if subscription_id is not None:
            body["subscriptionId"] = subscription_id
        if manually_assignable is not None:
            body["manuallyAssignable"] = manually_assignable
        if agents_last_updated_by_user_name is not None:
            body["agentsLastUpdatedByUserName"] = agents_last_updated_by_user_name
        if agents_last_updated_by_user_email_prefix is not None:
            body["agentsLastUpdatedByUserEmailPrefix"] = agents_last_updated_by_user_email_prefix
        if agents_last_updated_time is not None:
            body["agentsLastUpdatedTime"] = agents_last_updated_time
        if active is not None:
            body["active"] = active
        if description is not None:
            body["description"] = description
        if system_default is not None:
            body["systemDefault"] = system_default
        if id_param is not None:
            body["id"] = id_param
        if organization_id is not None:
            body["organizationId"] = organization_id
        if name is not None:
            body["name"] = name
        if social_channel_type is not None:
            body["socialChannelType"] = social_channel_type
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
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



@app.command("list-agent-based-queues")
def list_agent_based_queues(
    userid: str = typer.Argument(help="userid"),
    search: str = typer.Option(None, "--search", help="Filter data based on the search keyword.Supported search col"),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts"),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If th"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List agent based Contact Service Queue(s)by user ID."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_org_id() or api.people.me().org_id
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
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
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-skill-based-queues")
def list_skill_based_queues(
    userid: str = typer.Argument(help="userid"),
    search: str = typer.Option(None, "--search", help="Filter data based on the search keyword.Supported search col"),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts"),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If th"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List skill based Contact Service Queue(s)by user ID."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_org_id() or api.people.me().org_id
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
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
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-team-based-queues")
def list_team_based_queues(
    userid: str = typer.Argument(help="userid"),
    search: str = typer.Option(None, "--search", help="Filter data based on the search keyword.Supported search col"),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts"),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If th"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Team based Contact Service Queue(s)by user id."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_org_id() or api.people.me().org_id
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
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
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("show-contact-service-queue-v2")
def show_contact_service_queue_v2(
    id: str = typer.Argument(help="id"),
    agents_updated_info: str = typer.Option(None, "--agents-updated-info", help="If `true`, returns the user details who has last updated the"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get specific Contact Service Queue by Id."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_org_id() or api.people.me().org_id
    url = f"{cc_base_url}/organization/{orgid}/v2/contact-service-queue/{id}"
    params = {}
    if agents_updated_info is not None:
        params["agentsUpdatedInfo"] = agents_updated_info
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
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
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("update-contact-service-queue-v2")
def update_contact_service_queue_v2(
    id: str = typer.Argument(help="id"),
    channel_type: str = typer.Option(None, "--channel-type", help=""),
    check_agent_availability: str = typer.Option(None, "--check-agent-availability", help=""),
    control_flow_script_url: str = typer.Option(None, "--control-flow-script-url", help=""),
    default_music_in_queue_media_file_id: str = typer.Option(None, "--default-music-in-queue-media-file-id", help=""),
    ivr_requeue_url: str = typer.Option(None, "--ivr-requeue-url", help=""),
    max_active_contacts: str = typer.Option(None, "--max-active-contacts", help=""),
    max_time_in_queue: str = typer.Option(None, "--max-time-in-queue", help=""),
    monitoring_permitted: str = typer.Option(None, "--monitoring-permitted", help=""),
    parking_permitted: str = typer.Option(None, "--parking-permitted", help=""),
    pause_recording_permitted: str = typer.Option(None, "--pause-recording-permitted", help=""),
    queue_routing_type: str = typer.Option(None, "--queue-routing-type", help=""),
    queue_type: str = typer.Option(None, "--queue-type", help=""),
    recording_all_calls_permitted: str = typer.Option(None, "--recording-all-calls-permitted", help=""),
    recording_permitted: str = typer.Option(None, "--recording-permitted", help=""),
    routing_type: str = typer.Option(None, "--routing-type", help=""),
    service_level_threshold: str = typer.Option(None, "--service-level-threshold", help=""),
    version: str = typer.Option(None, "--version", help=""),
    outdial_campaign_enabled: str = typer.Option(None, "--outdial-campaign-enabled", help=""),
    recording_pause_duration: str = typer.Option(None, "--recording-pause-duration", help=""),
    overflow_number: str = typer.Option(None, "--overflow-number", help=""),
    vendor_id: str = typer.Option(None, "--vendor-id", help=""),
    skill_based_routing_type: str = typer.Option(None, "--skill-based-routing-type", help=""),
    timezone: str = typer.Option(None, "--timezone", help=""),
    xsp_version: str = typer.Option(None, "--xsp-version", help=""),
    subscription_id: str = typer.Option(None, "--subscription-id", help=""),
    manually_assignable: str = typer.Option(None, "--manually-assignable", help=""),
    agents_last_updated_by_user_name: str = typer.Option(None, "--agents-last-updated-by-user-name", help=""),
    agents_last_updated_by_user_email_prefix: str = typer.Option(None, "--agents-last-updated-by-user-email-prefix", help=""),
    agents_last_updated_time: str = typer.Option(None, "--agents-last-updated-time", help=""),
    active: str = typer.Option(None, "--active", help=""),
    description: str = typer.Option(None, "--description", help=""),
    system_default: str = typer.Option(None, "--system-default", help=""),
    id_param: str = typer.Option(None, "--id", help=""),
    organization_id: str = typer.Option(None, "--organization-id", help=""),
    name: str = typer.Option(None, "--name", help=""),
    social_channel_type: str = typer.Option(None, "--social-channel-type", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update specific Contact Service Queue by ID\n\nExample --json-body:\n  '{"channelType":"...","checkAgentAvailability":"...","controlFlowScriptUrl":"...","defaultMusicInQueueMediaFileId":"...","ivrRequeueUrl":"...","maxActiveContacts":"..."}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_org_id() or api.people.me().org_id
    url = f"{cc_base_url}/organization/{orgid}/v2/contact-service-queue/{id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if channel_type is not None:
            body["channelType"] = channel_type
        if check_agent_availability is not None:
            body["checkAgentAvailability"] = check_agent_availability
        if control_flow_script_url is not None:
            body["controlFlowScriptUrl"] = control_flow_script_url
        if default_music_in_queue_media_file_id is not None:
            body["defaultMusicInQueueMediaFileId"] = default_music_in_queue_media_file_id
        if ivr_requeue_url is not None:
            body["ivrRequeueUrl"] = ivr_requeue_url
        if max_active_contacts is not None:
            body["maxActiveContacts"] = max_active_contacts
        if max_time_in_queue is not None:
            body["maxTimeInQueue"] = max_time_in_queue
        if monitoring_permitted is not None:
            body["monitoringPermitted"] = monitoring_permitted
        if parking_permitted is not None:
            body["parkingPermitted"] = parking_permitted
        if pause_recording_permitted is not None:
            body["pauseRecordingPermitted"] = pause_recording_permitted
        if queue_routing_type is not None:
            body["queueRoutingType"] = queue_routing_type
        if queue_type is not None:
            body["queueType"] = queue_type
        if recording_all_calls_permitted is not None:
            body["recordingAllCallsPermitted"] = recording_all_calls_permitted
        if recording_permitted is not None:
            body["recordingPermitted"] = recording_permitted
        if routing_type is not None:
            body["routingType"] = routing_type
        if service_level_threshold is not None:
            body["serviceLevelThreshold"] = service_level_threshold
        if version is not None:
            body["version"] = version
        if outdial_campaign_enabled is not None:
            body["outdialCampaignEnabled"] = outdial_campaign_enabled
        if recording_pause_duration is not None:
            body["recordingPauseDuration"] = recording_pause_duration
        if overflow_number is not None:
            body["overflowNumber"] = overflow_number
        if vendor_id is not None:
            body["vendorId"] = vendor_id
        if skill_based_routing_type is not None:
            body["skillBasedRoutingType"] = skill_based_routing_type
        if timezone is not None:
            body["timezone"] = timezone
        if xsp_version is not None:
            body["xspVersion"] = xsp_version
        if subscription_id is not None:
            body["subscriptionId"] = subscription_id
        if manually_assignable is not None:
            body["manuallyAssignable"] = manually_assignable
        if agents_last_updated_by_user_name is not None:
            body["agentsLastUpdatedByUserName"] = agents_last_updated_by_user_name
        if agents_last_updated_by_user_email_prefix is not None:
            body["agentsLastUpdatedByUserEmailPrefix"] = agents_last_updated_by_user_email_prefix
        if agents_last_updated_time is not None:
            body["agentsLastUpdatedTime"] = agents_last_updated_time
        if active is not None:
            body["active"] = active
        if description is not None:
            body["description"] = description
        if system_default is not None:
            body["systemDefault"] = system_default
        if id_param is not None:
            body["id"] = id_param
        if organization_id is not None:
            body["organizationId"] = organization_id
        if name is not None:
            body["name"] = name
        if social_channel_type is not None:
            body["socialChannelType"] = social_channel_type
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
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
    typer.echo(f"Updated.")



@app.command("create-reassign-agents")
def create_reassign_agents(
    id: str = typer.Argument(help="id"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add or remove agents/users to/from an agent based queue\n\nExample --json-body:\n  '{"add":["..."],"remove":["..."]}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_org_id() or api.people.me().org_id
    url = f"{cc_base_url}/organization/{orgid}/v2/contact-service-queue/{id}/reassign-agents"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
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



@app.command("create-purge-inactive-entities")
def create_purge_inactive_entities(
    next_start_id: str = typer.Option(None, "--next-start-id", help="This is the entity ID from which items for the next purge ba"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Purge inactive Contact Service Queue(s)."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_org_id() or api.people.me().org_id
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/purge-inactive-entities"
    params = {}
    if next_start_id is not None:
        params["nextStartId"] = next_start_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
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



@app.command("show-contact-service-queue-organization")
def show_contact_service_queue_organization(
    id: str = typer.Argument(help="id"),
    agents_updated_info: str = typer.Option(None, "--agents-updated-info", help="If `true`, returns the user details who has last updated the"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get specific Contact Service Queue by Id."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_org_id() or api.people.me().org_id
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/{id}"
    params = {}
    if agents_updated_info is not None:
        params["agentsUpdatedInfo"] = agents_updated_info
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
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
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("update-contact-service-queue-organization")
def update_contact_service_queue_organization(
    id: str = typer.Argument(help="id"),
    channel_type: str = typer.Option(None, "--channel-type", help=""),
    check_agent_availability: str = typer.Option(None, "--check-agent-availability", help=""),
    control_flow_script_url: str = typer.Option(None, "--control-flow-script-url", help=""),
    default_music_in_queue_media_file_id: str = typer.Option(None, "--default-music-in-queue-media-file-id", help=""),
    ivr_requeue_url: str = typer.Option(None, "--ivr-requeue-url", help=""),
    max_active_contacts: str = typer.Option(None, "--max-active-contacts", help=""),
    max_time_in_queue: str = typer.Option(None, "--max-time-in-queue", help=""),
    monitoring_permitted: str = typer.Option(None, "--monitoring-permitted", help=""),
    parking_permitted: str = typer.Option(None, "--parking-permitted", help=""),
    pause_recording_permitted: str = typer.Option(None, "--pause-recording-permitted", help=""),
    queue_routing_type: str = typer.Option(None, "--queue-routing-type", help=""),
    queue_type: str = typer.Option(None, "--queue-type", help=""),
    recording_all_calls_permitted: str = typer.Option(None, "--recording-all-calls-permitted", help=""),
    recording_permitted: str = typer.Option(None, "--recording-permitted", help=""),
    routing_type: str = typer.Option(None, "--routing-type", help=""),
    service_level_threshold: str = typer.Option(None, "--service-level-threshold", help=""),
    version: str = typer.Option(None, "--version", help=""),
    outdial_campaign_enabled: str = typer.Option(None, "--outdial-campaign-enabled", help=""),
    recording_pause_duration: str = typer.Option(None, "--recording-pause-duration", help=""),
    overflow_number: str = typer.Option(None, "--overflow-number", help=""),
    vendor_id: str = typer.Option(None, "--vendor-id", help=""),
    skill_based_routing_type: str = typer.Option(None, "--skill-based-routing-type", help=""),
    timezone: str = typer.Option(None, "--timezone", help=""),
    xsp_version: str = typer.Option(None, "--xsp-version", help=""),
    subscription_id: str = typer.Option(None, "--subscription-id", help=""),
    manually_assignable: str = typer.Option(None, "--manually-assignable", help=""),
    agents_last_updated_by_user_name: str = typer.Option(None, "--agents-last-updated-by-user-name", help=""),
    agents_last_updated_by_user_email_prefix: str = typer.Option(None, "--agents-last-updated-by-user-email-prefix", help=""),
    agents_last_updated_time: str = typer.Option(None, "--agents-last-updated-time", help=""),
    active: str = typer.Option(None, "--active", help=""),
    description: str = typer.Option(None, "--description", help=""),
    system_default: str = typer.Option(None, "--system-default", help=""),
    id_param: str = typer.Option(None, "--id", help=""),
    organization_id: str = typer.Option(None, "--organization-id", help=""),
    name: str = typer.Option(None, "--name", help=""),
    social_channel_type: str = typer.Option(None, "--social-channel-type", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update specific Contact Service Queue by ID\n\nExample --json-body:\n  '{"channelType":"...","checkAgentAvailability":"...","controlFlowScriptUrl":"...","defaultMusicInQueueMediaFileId":"...","ivrRequeueUrl":"...","maxActiveContacts":"..."}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_org_id() or api.people.me().org_id
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/{id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if channel_type is not None:
            body["channelType"] = channel_type
        if check_agent_availability is not None:
            body["checkAgentAvailability"] = check_agent_availability
        if control_flow_script_url is not None:
            body["controlFlowScriptUrl"] = control_flow_script_url
        if default_music_in_queue_media_file_id is not None:
            body["defaultMusicInQueueMediaFileId"] = default_music_in_queue_media_file_id
        if ivr_requeue_url is not None:
            body["ivrRequeueUrl"] = ivr_requeue_url
        if max_active_contacts is not None:
            body["maxActiveContacts"] = max_active_contacts
        if max_time_in_queue is not None:
            body["maxTimeInQueue"] = max_time_in_queue
        if monitoring_permitted is not None:
            body["monitoringPermitted"] = monitoring_permitted
        if parking_permitted is not None:
            body["parkingPermitted"] = parking_permitted
        if pause_recording_permitted is not None:
            body["pauseRecordingPermitted"] = pause_recording_permitted
        if queue_routing_type is not None:
            body["queueRoutingType"] = queue_routing_type
        if queue_type is not None:
            body["queueType"] = queue_type
        if recording_all_calls_permitted is not None:
            body["recordingAllCallsPermitted"] = recording_all_calls_permitted
        if recording_permitted is not None:
            body["recordingPermitted"] = recording_permitted
        if routing_type is not None:
            body["routingType"] = routing_type
        if service_level_threshold is not None:
            body["serviceLevelThreshold"] = service_level_threshold
        if version is not None:
            body["version"] = version
        if outdial_campaign_enabled is not None:
            body["outdialCampaignEnabled"] = outdial_campaign_enabled
        if recording_pause_duration is not None:
            body["recordingPauseDuration"] = recording_pause_duration
        if overflow_number is not None:
            body["overflowNumber"] = overflow_number
        if vendor_id is not None:
            body["vendorId"] = vendor_id
        if skill_based_routing_type is not None:
            body["skillBasedRoutingType"] = skill_based_routing_type
        if timezone is not None:
            body["timezone"] = timezone
        if xsp_version is not None:
            body["xspVersion"] = xsp_version
        if subscription_id is not None:
            body["subscriptionId"] = subscription_id
        if manually_assignable is not None:
            body["manuallyAssignable"] = manually_assignable
        if agents_last_updated_by_user_name is not None:
            body["agentsLastUpdatedByUserName"] = agents_last_updated_by_user_name
        if agents_last_updated_by_user_email_prefix is not None:
            body["agentsLastUpdatedByUserEmailPrefix"] = agents_last_updated_by_user_email_prefix
        if agents_last_updated_time is not None:
            body["agentsLastUpdatedTime"] = agents_last_updated_time
        if active is not None:
            body["active"] = active
        if description is not None:
            body["description"] = description
        if system_default is not None:
            body["systemDefault"] = system_default
        if id_param is not None:
            body["id"] = id_param
        if organization_id is not None:
            body["organizationId"] = organization_id
        if name is not None:
            body["name"] = name
        if social_channel_type is not None:
            body["socialChannelType"] = social_channel_type
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
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
    typer.echo(f"Updated.")



@app.command("delete")
def delete(
    id: str = typer.Argument(help="id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete specific Contact Service Queue by ID."""
    if not force:
        typer.confirm(f"Delete {orgid}?", abort=True)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_org_id() or api.people.me().org_id
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/{id}"
    try:
        api.session.rest_delete(url)
    except WebexError as e:
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
    typer.echo(f"Deleted: {orgid}")



@app.command("list-contact-service-queue-v3")
def list_contact_service_queue_v3(
    filter_param: str = typer.Option(None, "--filter", help="Specify a filter based on which the results will be fetched."),
    attributes: str = typer.Option(None, "--attributes", help="Specify the attributes to be returned.Default all attributes"),
    search: str = typer.Option(None, "--search", help="Filter data based on the search keyword.Supported search col"),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts"),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If th"),
    desktop_profile_filter: str = typer.Option(None, "--desktop-profile-filter", help="If set to true, the API will return only the data that the u"),
    provisioning_view: str = typer.Option(None, "--provisioning-view", help="If set to true, the API will only return data that user has"),
    single_object_response: str = typer.Option(None, "--single-object-response", help="Specifiy whether to include array fields in the response, Th"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Contact Service Queue(s)."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_org_id() or api.people.me().org_id
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
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
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create-bulk")
def create_bulk(
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk save Contact Service Queue(s)\n\nExample --json-body:\n  '{"items":[{"item":"...","itemIdentifier":"...","requestAction":"..."}]}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_org_id() or api.people.me().org_id
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/v2/bulk"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
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



@app.command("create-delete-reference")
def create_delete_reference(
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete References\n\nExample --json-body:\n  '{"references":{"key_0":"...","key_1":"..."}}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_org_id() or api.people.me().org_id
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/delete-reference"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
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



@app.command("list-contact-service-queue-organization")
def list_contact_service_queue_organization(
    filter_param: str = typer.Option(None, "--filter", help="Specify a filter based on which the results will be fetched."),
    channel_types: str = typer.Option(None, "--channel-types", help="[DEPRECATED] Channel type(s) allowed by the system.Separate"),
    attributes: str = typer.Option(None, "--attributes", help="Specify the attributes to be returned.Default all attributes"),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts"),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If th"),
    single_object_response: str = typer.Option(None, "--single-object-response", help="Specifiy whether to include array fields in the response, Th"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Contact Service Queue(s)."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_org_id() or api.people.me().org_id
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
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
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create-contact-service-queue-organization")
def create_contact_service_queue_organization(
    channel_type: str = typer.Option(None, "--channel-type", help=""),
    check_agent_availability: str = typer.Option(None, "--check-agent-availability", help=""),
    control_flow_script_url: str = typer.Option(None, "--control-flow-script-url", help=""),
    default_music_in_queue_media_file_id: str = typer.Option(None, "--default-music-in-queue-media-file-id", help=""),
    ivr_requeue_url: str = typer.Option(None, "--ivr-requeue-url", help=""),
    max_active_contacts: str = typer.Option(None, "--max-active-contacts", help=""),
    max_time_in_queue: str = typer.Option(None, "--max-time-in-queue", help=""),
    monitoring_permitted: str = typer.Option(None, "--monitoring-permitted", help=""),
    parking_permitted: str = typer.Option(None, "--parking-permitted", help=""),
    pause_recording_permitted: str = typer.Option(None, "--pause-recording-permitted", help=""),
    queue_routing_type: str = typer.Option(None, "--queue-routing-type", help=""),
    queue_type: str = typer.Option(None, "--queue-type", help=""),
    recording_all_calls_permitted: str = typer.Option(None, "--recording-all-calls-permitted", help=""),
    recording_permitted: str = typer.Option(None, "--recording-permitted", help=""),
    routing_type: str = typer.Option(None, "--routing-type", help=""),
    service_level_threshold: str = typer.Option(None, "--service-level-threshold", help=""),
    version: str = typer.Option(None, "--version", help=""),
    outdial_campaign_enabled: str = typer.Option(None, "--outdial-campaign-enabled", help=""),
    recording_pause_duration: str = typer.Option(None, "--recording-pause-duration", help=""),
    overflow_number: str = typer.Option(None, "--overflow-number", help=""),
    vendor_id: str = typer.Option(None, "--vendor-id", help=""),
    skill_based_routing_type: str = typer.Option(None, "--skill-based-routing-type", help=""),
    timezone: str = typer.Option(None, "--timezone", help=""),
    xsp_version: str = typer.Option(None, "--xsp-version", help=""),
    subscription_id: str = typer.Option(None, "--subscription-id", help=""),
    manually_assignable: str = typer.Option(None, "--manually-assignable", help=""),
    agents_last_updated_by_user_name: str = typer.Option(None, "--agents-last-updated-by-user-name", help=""),
    agents_last_updated_by_user_email_prefix: str = typer.Option(None, "--agents-last-updated-by-user-email-prefix", help=""),
    agents_last_updated_time: str = typer.Option(None, "--agents-last-updated-time", help=""),
    active: str = typer.Option(None, "--active", help=""),
    description: str = typer.Option(None, "--description", help=""),
    system_default: str = typer.Option(None, "--system-default", help=""),
    id_param: str = typer.Option(None, "--id", help=""),
    organization_id: str = typer.Option(None, "--organization-id", help=""),
    name: str = typer.Option(None, "--name", help=""),
    social_channel_type: str = typer.Option(None, "--social-channel-type", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new Contact Service Queue\n\nExample --json-body:\n  '{"channelType":"...","checkAgentAvailability":"...","controlFlowScriptUrl":"...","defaultMusicInQueueMediaFileId":"...","ivrRequeueUrl":"...","maxActiveContacts":"..."}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_org_id() or api.people.me().org_id
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if channel_type is not None:
            body["channelType"] = channel_type
        if check_agent_availability is not None:
            body["checkAgentAvailability"] = check_agent_availability
        if control_flow_script_url is not None:
            body["controlFlowScriptUrl"] = control_flow_script_url
        if default_music_in_queue_media_file_id is not None:
            body["defaultMusicInQueueMediaFileId"] = default_music_in_queue_media_file_id
        if ivr_requeue_url is not None:
            body["ivrRequeueUrl"] = ivr_requeue_url
        if max_active_contacts is not None:
            body["maxActiveContacts"] = max_active_contacts
        if max_time_in_queue is not None:
            body["maxTimeInQueue"] = max_time_in_queue
        if monitoring_permitted is not None:
            body["monitoringPermitted"] = monitoring_permitted
        if parking_permitted is not None:
            body["parkingPermitted"] = parking_permitted
        if pause_recording_permitted is not None:
            body["pauseRecordingPermitted"] = pause_recording_permitted
        if queue_routing_type is not None:
            body["queueRoutingType"] = queue_routing_type
        if queue_type is not None:
            body["queueType"] = queue_type
        if recording_all_calls_permitted is not None:
            body["recordingAllCallsPermitted"] = recording_all_calls_permitted
        if recording_permitted is not None:
            body["recordingPermitted"] = recording_permitted
        if routing_type is not None:
            body["routingType"] = routing_type
        if service_level_threshold is not None:
            body["serviceLevelThreshold"] = service_level_threshold
        if version is not None:
            body["version"] = version
        if outdial_campaign_enabled is not None:
            body["outdialCampaignEnabled"] = outdial_campaign_enabled
        if recording_pause_duration is not None:
            body["recordingPauseDuration"] = recording_pause_duration
        if overflow_number is not None:
            body["overflowNumber"] = overflow_number
        if vendor_id is not None:
            body["vendorId"] = vendor_id
        if skill_based_routing_type is not None:
            body["skillBasedRoutingType"] = skill_based_routing_type
        if timezone is not None:
            body["timezone"] = timezone
        if xsp_version is not None:
            body["xspVersion"] = xsp_version
        if subscription_id is not None:
            body["subscriptionId"] = subscription_id
        if manually_assignable is not None:
            body["manuallyAssignable"] = manually_assignable
        if agents_last_updated_by_user_name is not None:
            body["agentsLastUpdatedByUserName"] = agents_last_updated_by_user_name
        if agents_last_updated_by_user_email_prefix is not None:
            body["agentsLastUpdatedByUserEmailPrefix"] = agents_last_updated_by_user_email_prefix
        if agents_last_updated_time is not None:
            body["agentsLastUpdatedTime"] = agents_last_updated_time
        if active is not None:
            body["active"] = active
        if description is not None:
            body["description"] = description
        if system_default is not None:
            body["systemDefault"] = system_default
        if id_param is not None:
            body["id"] = id_param
        if organization_id is not None:
            body["organizationId"] = organization_id
        if name is not None:
            body["name"] = name
        if social_channel_type is not None:
            body["socialChannelType"] = social_channel_type
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
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


