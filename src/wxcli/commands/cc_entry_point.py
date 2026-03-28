import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling entry-point.")


@app.command("create")
def create(
    orgid: str = typer.Argument(help="orgid"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk save Entry Point(s)\n\nExample --json-body:\n  '{"items":[{"item":"...","itemIdentifier":"...","requestAction":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/entry-point/bulk"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
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



@app.command("list")
def cmd_list(
    orgid: str = typer.Argument(help="orgid"),
    type_param: str = typer.Option(None, "--type", help="Indicates the type of Entrypoint; can be INBOUND or OUTBOUND"),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts"),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If th"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk export Entry Point(s)."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/entry-point/bulk-export"
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
    except RestError as e:
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
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create-purge-inactive-entities")
def create_purge_inactive_entities(
    orgid: str = typer.Argument(help="orgid"),
    next_start_id: str = typer.Option(None, "--next-start-id", help="This is the entity ID from which items for the next purge ba"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Purge inactive Entry Point(s)."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/entry-point/purge-inactive-entities"
    params = {}
    if next_start_id is not None:
        params["nextStartId"] = next_start_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except RestError as e:
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



@app.command("list-entry-point-organization")
def list_entry_point_organization(
    orgid: str = typer.Argument(help="orgid"),
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
    """List Entry Point(s)."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/entry-point"
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
    except RestError as e:
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
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create-entry-point")
def create_entry_point(
    orgid: str = typer.Argument(help="orgid"),
    subscription_id: str = typer.Option(None, "--subscription-id", help=""),
    channel_type: str = typer.Option(None, "--channel-type", help=""),
    music_on_hold_id: str = typer.Option(None, "--music-on-hold-id", help=""),
    control_flow_script_url: str = typer.Option(None, "--control-flow-script-url", help=""),
    callback_enabled: str = typer.Option(None, "--callback-enabled", help=""),
    outdial_transfer_to_queue_enabled: str = typer.Option(None, "--outdial-transfer-to-queue-enabled", help=""),
    dn_ep_mapping_count: str = typer.Option(None, "--dn-ep-mapping-count", help=""),
    active: str = typer.Option(None, "--active", help=""),
    description: str = typer.Option(None, "--description", help=""),
    flow_id: str = typer.Option(None, "--flow-id", help=""),
    outdial_queue_id: str = typer.Option(None, "--outdial-queue-id", help=""),
    service_level_threshold: str = typer.Option(None, "--service-level-threshold", help=""),
    version: str = typer.Option(None, "--version", help=""),
    flow_tag_id: str = typer.Option(None, "--flow-tag-id", help=""),
    system_default: str = typer.Option(None, "--system-default", help=""),
    overflow_number: str = typer.Option(None, "--overflow-number", help=""),
    route_point_id: str = typer.Option(None, "--route-point-id", help=""),
    xsp_version: str = typer.Option(None, "--xsp-version", help=""),
    name: str = typer.Option(None, "--name", help=""),
    id_param: str = typer.Option(None, "--id", help=""),
    imi_org_type: str = typer.Option(None, "--imi-org-type", help=""),
    organization_id: str = typer.Option(None, "--organization-id", help=""),
    social_channel_type: str = typer.Option(None, "--social-channel-type", help=""),
    asset_id: str = typer.Option(None, "--asset-id", help=""),
    entry_point_type: str = typer.Option(None, "--entry-point-type", help=""),
    timezone: str = typer.Option(None, "--timezone", help=""),
    maximum_active_contacts: str = typer.Option(None, "--maximum-active-contacts", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new Entry Point\n\nExample --json-body:\n  '{"subscriptionId":"...","channelType":"...","musicOnHoldId":"...","controlFlowScriptUrl":"...","callbackEnabled":"...","outdialTransferToQueueEnabled":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/entry-point"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if subscription_id is not None:
            body["subscriptionId"] = subscription_id
        if channel_type is not None:
            body["channelType"] = channel_type
        if music_on_hold_id is not None:
            body["musicOnHoldId"] = music_on_hold_id
        if control_flow_script_url is not None:
            body["controlFlowScriptUrl"] = control_flow_script_url
        if callback_enabled is not None:
            body["callbackEnabled"] = callback_enabled
        if outdial_transfer_to_queue_enabled is not None:
            body["outdialTransferToQueueEnabled"] = outdial_transfer_to_queue_enabled
        if dn_ep_mapping_count is not None:
            body["dnEpMappingCount"] = dn_ep_mapping_count
        if active is not None:
            body["active"] = active
        if description is not None:
            body["description"] = description
        if flow_id is not None:
            body["flowId"] = flow_id
        if outdial_queue_id is not None:
            body["outdialQueueId"] = outdial_queue_id
        if service_level_threshold is not None:
            body["serviceLevelThreshold"] = service_level_threshold
        if version is not None:
            body["version"] = version
        if flow_tag_id is not None:
            body["flowTagId"] = flow_tag_id
        if system_default is not None:
            body["systemDefault"] = system_default
        if overflow_number is not None:
            body["overflowNumber"] = overflow_number
        if route_point_id is not None:
            body["routePointId"] = route_point_id
        if xsp_version is not None:
            body["xspVersion"] = xsp_version
        if name is not None:
            body["name"] = name
        if id_param is not None:
            body["id"] = id_param
        if imi_org_type is not None:
            body["imiOrgType"] = imi_org_type
        if organization_id is not None:
            body["organizationId"] = organization_id
        if social_channel_type is not None:
            body["socialChannelType"] = social_channel_type
        if asset_id is not None:
            body["assetId"] = asset_id
        if entry_point_type is not None:
            body["entryPointType"] = entry_point_type
        if timezone is not None:
            body["timezone"] = timezone
        if maximum_active_contacts is not None:
            body["maximumActiveContacts"] = maximum_active_contacts
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
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
    orgid: str = typer.Argument(help="orgid"),
    id: str = typer.Argument(help="id"),
    type_param: str = typer.Option(None, "--type", help="Entity type of the other entity that has a reference to this"),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts"),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If th"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List references for a specific Entry Point."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/entry-point/{id}/incoming-references"
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
    except RestError as e:
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
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-entry-point-v2")
def list_entry_point_v2(
    orgid: str = typer.Argument(help="orgid"),
    filter_param: str = typer.Option(None, "--filter", help="Specify a filter based on which the results will be fetched."),
    attributes: str = typer.Option(None, "--attributes", help="Specify the attributes to be returned.Default all attributes"),
    search: str = typer.Option(None, "--search", help="Filter data based on the search keyword.Supported search col"),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts"),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If th"),
    desktop_profile_filter: str = typer.Option(None, "--desktop-profile-filter", help="If set to true, the API will return only the data that the u"),
    provisioning_view: str = typer.Option(None, "--provisioning-view", help="If set to true, the API will only return data that user has"),
    include_count: str = typer.Option(None, "--include-count", help="Enable the flag to get the count of DN-EP Mapping"),
    single_object_response: str = typer.Option(None, "--single-object-response", help="Specifiy whether to include array fields in the response, Th"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Entry Point(s)."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/v2/entry-point"
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
    if include_count is not None:
        params["includeCount"] = include_count
    if single_object_response is not None:
        params["singleObjectResponse"] = single_object_response
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
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
    orgid: str = typer.Argument(help="orgid"),
    id: str = typer.Argument(help="id"),
    include_names: str = typer.Option(None, "--include-names", help="Specifiy whether to include flow override settings reference"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get specific Entry Point by ID."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/entry-point/{id}"
    params = {}
    if include_names is not None:
        params["includeNames"] = include_names
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
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



@app.command("update")
def update(
    orgid: str = typer.Argument(help="orgid"),
    id: str = typer.Argument(help="id"),
    subscription_id: str = typer.Option(None, "--subscription-id", help=""),
    channel_type: str = typer.Option(None, "--channel-type", help=""),
    music_on_hold_id: str = typer.Option(None, "--music-on-hold-id", help=""),
    control_flow_script_url: str = typer.Option(None, "--control-flow-script-url", help=""),
    callback_enabled: str = typer.Option(None, "--callback-enabled", help=""),
    outdial_transfer_to_queue_enabled: str = typer.Option(None, "--outdial-transfer-to-queue-enabled", help=""),
    dn_ep_mapping_count: str = typer.Option(None, "--dn-ep-mapping-count", help=""),
    active: str = typer.Option(None, "--active", help=""),
    description: str = typer.Option(None, "--description", help=""),
    flow_id: str = typer.Option(None, "--flow-id", help=""),
    outdial_queue_id: str = typer.Option(None, "--outdial-queue-id", help=""),
    service_level_threshold: str = typer.Option(None, "--service-level-threshold", help=""),
    version: str = typer.Option(None, "--version", help=""),
    flow_tag_id: str = typer.Option(None, "--flow-tag-id", help=""),
    system_default: str = typer.Option(None, "--system-default", help=""),
    overflow_number: str = typer.Option(None, "--overflow-number", help=""),
    route_point_id: str = typer.Option(None, "--route-point-id", help=""),
    xsp_version: str = typer.Option(None, "--xsp-version", help=""),
    name: str = typer.Option(None, "--name", help=""),
    id_param: str = typer.Option(None, "--id", help=""),
    imi_org_type: str = typer.Option(None, "--imi-org-type", help=""),
    organization_id: str = typer.Option(None, "--organization-id", help=""),
    social_channel_type: str = typer.Option(None, "--social-channel-type", help=""),
    asset_id: str = typer.Option(None, "--asset-id", help=""),
    entry_point_type: str = typer.Option(None, "--entry-point-type", help=""),
    timezone: str = typer.Option(None, "--timezone", help=""),
    maximum_active_contacts: str = typer.Option(None, "--maximum-active-contacts", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update specific Entry Point by ID\n\nExample --json-body:\n  '{"subscriptionId":"...","channelType":"...","musicOnHoldId":"...","controlFlowScriptUrl":"...","callbackEnabled":"...","outdialTransferToQueueEnabled":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/entry-point/{id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if subscription_id is not None:
            body["subscriptionId"] = subscription_id
        if channel_type is not None:
            body["channelType"] = channel_type
        if music_on_hold_id is not None:
            body["musicOnHoldId"] = music_on_hold_id
        if control_flow_script_url is not None:
            body["controlFlowScriptUrl"] = control_flow_script_url
        if callback_enabled is not None:
            body["callbackEnabled"] = callback_enabled
        if outdial_transfer_to_queue_enabled is not None:
            body["outdialTransferToQueueEnabled"] = outdial_transfer_to_queue_enabled
        if dn_ep_mapping_count is not None:
            body["dnEpMappingCount"] = dn_ep_mapping_count
        if active is not None:
            body["active"] = active
        if description is not None:
            body["description"] = description
        if flow_id is not None:
            body["flowId"] = flow_id
        if outdial_queue_id is not None:
            body["outdialQueueId"] = outdial_queue_id
        if service_level_threshold is not None:
            body["serviceLevelThreshold"] = service_level_threshold
        if version is not None:
            body["version"] = version
        if flow_tag_id is not None:
            body["flowTagId"] = flow_tag_id
        if system_default is not None:
            body["systemDefault"] = system_default
        if overflow_number is not None:
            body["overflowNumber"] = overflow_number
        if route_point_id is not None:
            body["routePointId"] = route_point_id
        if xsp_version is not None:
            body["xspVersion"] = xsp_version
        if name is not None:
            body["name"] = name
        if id_param is not None:
            body["id"] = id_param
        if imi_org_type is not None:
            body["imiOrgType"] = imi_org_type
        if organization_id is not None:
            body["organizationId"] = organization_id
        if social_channel_type is not None:
            body["socialChannelType"] = social_channel_type
        if asset_id is not None:
            body["assetId"] = asset_id
        if entry_point_type is not None:
            body["entryPointType"] = entry_point_type
        if timezone is not None:
            body["timezone"] = timezone
        if maximum_active_contacts is not None:
            body["maximumActiveContacts"] = maximum_active_contacts
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
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
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("delete")
def delete(
    orgid: str = typer.Argument(help="orgid"),
    id: str = typer.Argument(help="id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete specific Entry Point by ID."""
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/entry-point/{id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
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
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {id}")


