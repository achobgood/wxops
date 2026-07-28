import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import resolve_org_id, get_cc_base_url, get_cc_org_id


app = typer.Typer(help="Manage Webex Contact Center cc-entry-point.")


@app.command("list", short_help="List Entry Point(s).")
def cmd_list(
    filter_param: str = typer.Option(None, "--filter", help="Specify a filter based on which the results will be fetched. Supported filterable fields: id. The examples below show some search queries - id==\"57efb0e6-5af0-4245-a67d-d3c5045cdb6e\" - id!=\"57efb0e6-5af0-4245-a67d-d3c5045cdb6e\" -..."),
    channel_types: str = typer.Option(None, "--channel-types", help="[DEPRECATED] Channel type(s) allowed by the system.Separate values with commas.Use uppercase. By default, there is no channel type filtering."),
    attributes: str = typer.Option(None, "--attributes", help="Specify the attributes to be returned.Default all attributes are returned along with specified columns. All Attributes are supported except (ccOneQueue, userIds, queueRankings, links)"),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    single_object_response: str = typer.Option(None, "--single-object-response", help="Specifiy whether to include array fields in the response, This query param should use only if the response contain single record, if we are using for multiple objects response query param not supported and throws an exception."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Entry Point(s)."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/entry-point"
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



_BODY_SKELETON_CREATE = '{"name":"...","entryPointType":"INBOUND","channelType":"TELEPHONY","socialChannelType":"MESSAGEBIRD","active":true,"serviceLevelThreshold":0,"maximumActiveContacts":0,"controlFlowScriptUrl":"..."}'

@app.command("create", short_help="Create a new Entry Point.")
def create(
    organization_id: str = typer.Option(None, "--organization-id", help="ID of the contact center organization. It is required to define for the following operations - All bulk save operations"),
    id_param: str = typer.Option(None, "--id", help="ID of this contact center resource. It should not be specified when creating a new resource. However, it is mandatory when updating a resource."),
    version: str = typer.Option(None, "--version", help="The version of this resource. For a newly created resource, it will be 0 unless specified otherwise."),
    name: str = typer.Option(None, "--name", help="(required) A unique name for the entry point within the organization. It is required only during a create or an update operation."),
    description: str = typer.Option(None, "--description", help="A short description of the entry point."),
    entry_point_type: str = typer.Option(None, "--entry-point-type", help="(required) Choices: INBOUND, OUTBOUND"),
    channel_type: str = typer.Option(None, "--channel-type", help="(required) Choices: TELEPHONY, EMAIL, FAX, CHAT, VIDEO, OTHERS, SOCIAL_CHANNEL"),
    social_channel_type: str = typer.Option(None, "--social-channel-type", help="(required) Choices: MESSAGEBIRD, MESSENGER, WHATSAPP, APPLE_BUSINESS_CHAT, GOOGLE_BUSINESS_MESSAGES"),
    active: bool = typer.Option(None, "--active/--no-active", help="(required) Used to toggle the state of the entrypoint from active to inactive and vice-versa. It is required only during a create or an update operation."),
    service_level_threshold: str = typer.Option(None, "--service-level-threshold", help="(required) Allows to set the time that a customer request can be in a queue before the system flags it as outside the service level. If the agent completes a customer service request within this time interval, the system considers it within the service level. It is required only for a create or an update..."),
    maximum_active_contacts: str = typer.Option(None, "--maximum-active-contacts", help="(required) Caps the maximum number of simultaneous calls for this entry point. The system busies out any additional calls when the number of active calls exceeds this number. It is required only for a create or an update operation."),
    control_flow_script_url: str = typer.Option(None, "--control-flow-script-url", help="(required) The system automatically populates this field with the URL for this entry point or the default control script of the queue.It happens when you don’t configure the control script using the Webex Contact Center Routing Strategy module.This setting is available for the Telephony channel type."),
    overflow_number: str = typer.Option(None, "--overflow-number", help="(required) Allows to set the destination phone number to which the system diverts the customer calls when they exceed the Maximum Time in Queue that has been set in the routing strategy. This setting is applicable only for the Telephony channel type."),
    timezone: str = typer.Option(None, "--timezone", help="(Optional) Any routing strategy for this entry point uses the time zone that you select here."),
    imi_org_type: str = typer.Option(None, "--imi-org-type", help="(required) Choices: MIXED_MODE, IMI"),
    asset_id: str = typer.Option(None, "--asset-id", help="(required) ID of the asset in IMI that corresponds to this entrypoint."),
    xsp_version: str = typer.Option(None, "--xsp-version", help="(Optional) Used to subscribe for recording events."),
    subscription_id: str = typer.Option(None, "--subscription-id", help="(Optional) Used to subscribe for recording events."),
    route_point_id: str = typer.Option(None, "--route-point-id", help="The identifier of a route point of WxC which is similar to entry point of WxCC"),
    flow_id: str = typer.Option(None, "--flow-id", help=""),
    flow_tag_id: str = typer.Option(None, "--flow-tag-id", help=""),
    music_on_hold_id: str = typer.Option(None, "--music-on-hold-id", help=""),
    outdial_queue_id: str = typer.Option(None, "--outdial-queue-id", help=""),
    system_default: bool = typer.Option(None, "--system-default/--no-system-default", help="Indicates whether the created resource is system created or not"),
    callback_enabled: bool = typer.Option(None, "--callback-enabled/--no-callback-enabled", help="Indicates whether the created resource is call back enabled or not"),
    outdial_transfer_to_queue_enabled: bool = typer.Option(None, "--outdial-transfer-to-queue-enabled/--no-outdial-transfer-to-queue-enabled", help="Indicates whether the resource is Default Outdial Transfer to Queue."),
    dn_ep_mapping_count: str = typer.Option(None, "--dn-ep-mapping-count", help=""),
    created_time: str = typer.Option(None, "--created-time", help="Creation time(in epoch millis) of this resource."),
    last_updated_time: str = typer.Option(None, "--last-updated-time", help="Time(in epoch millis) when this resource was last updated."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new Entry Point.\n\n\b\nExample: wxcli cc-entry-point create --name NAME --entry-point-type INBOUND --channel-type TELEPHONY --social-channel-type MESSAGEBIRD --active --service-level-threshold SERVICE_LEVEL_THRESHOLD --maximum-active-contacts MAXIMUM_ACTIVE_CONTACTS --control-flow-script-url CONTROL_FLOW_SCRIPT_URL --overflow-number OVERFLOW_NUMBER --imi-org-type MIXED_MODE --asset-id ASSET_ID\n\n\b\nExample --json-body: '{"name":"...","entryPointType":"INBOUND","channelType":"TELEPHONY","socialChannelType":"MESSAGEBIRD","active":true,"serviceLevelThreshold":0,"maximumActiveContacts":0,"controlFlowScriptUrl":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/entry-point"
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
        if entry_point_type is not None:
            body["entryPointType"] = entry_point_type
        if channel_type is not None:
            body["channelType"] = channel_type
        if social_channel_type is not None:
            body["socialChannelType"] = social_channel_type
        if active is not None:
            body["active"] = active
        if service_level_threshold is not None:
            body["serviceLevelThreshold"] = service_level_threshold
        if maximum_active_contacts is not None:
            body["maximumActiveContacts"] = maximum_active_contacts
        if control_flow_script_url is not None:
            body["controlFlowScriptUrl"] = control_flow_script_url
        if overflow_number is not None:
            body["overflowNumber"] = overflow_number
        if timezone is not None:
            body["timezone"] = timezone
        if imi_org_type is not None:
            body["imiOrgType"] = imi_org_type
        if asset_id is not None:
            body["assetId"] = asset_id
        if xsp_version is not None:
            body["xspVersion"] = xsp_version
        if subscription_id is not None:
            body["subscriptionId"] = subscription_id
        if route_point_id is not None:
            body["routePointId"] = route_point_id
        if flow_id is not None:
            body["flowId"] = flow_id
        if flow_tag_id is not None:
            body["flowTagId"] = flow_tag_id
        if music_on_hold_id is not None:
            body["musicOnHoldId"] = music_on_hold_id
        if outdial_queue_id is not None:
            body["outdialQueueId"] = outdial_queue_id
        if system_default is not None:
            body["systemDefault"] = system_default
        if callback_enabled is not None:
            body["callbackEnabled"] = callback_enabled
        if outdial_transfer_to_queue_enabled is not None:
            body["outdialTransferToQueueEnabled"] = outdial_transfer_to_queue_enabled
        if dn_ep_mapping_count is not None:
            body["dnEpMappingCount"] = dn_ep_mapping_count
        if created_time is not None:
            body["createdTime"] = created_time
        if last_updated_time is not None:
            body["lastUpdatedTime"] = last_updated_time
        _missing = [f for f in ['name', 'entryPointType', 'channelType', 'socialChannelType', 'active', 'serviceLevelThreshold', 'maximumActiveContacts', 'controlFlowScriptUrl', 'overflowNumber', 'imiOrgType', 'assetId'] if f not in body or body[f] is None]
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



_BODY_SKELETON_CREATE_BULK = '{"items":[{"itemIdentifier":"...","item":"...","requestAction":"..."}]}'

@app.command("create-bulk", short_help="Bulk save Entry Point(s).")
def create_bulk(
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk save Entry Point(s).\n\n\b\nExample --json-body: '{"items":[{"itemIdentifier":"...","item":"...","requestAction":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_BULK), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/entry-point/bulk"
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



@app.command("list-bulk-export", short_help="Bulk export Entry Point(s).")
def list_bulk_export(
    type_param: str = typer.Option(..., "--type", help="Choices: INBOUND, OUTBOUND"),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk export Entry Point(s).\n\n\b\nExample: wxcli cc-entry-point list-bulk-export --type INBOUND"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/entry-point/bulk-export"
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



@app.command("create-purge-inactive-entities", hidden=True)
@app.command("delete-purge-inactive-entities", short_help="Purge inactive Entry Point(s).")
def delete_purge_inactive_entities(
    next_start_id: str = typer.Option(None, "--next-start-id", help="This is the entity ID from which items for the next purge batch with be selected."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Purge inactive Entry Point(s)."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/entry-point/purge-inactive-entities"
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



@app.command("show", short_help="Get specific Entry Point by ID.")
def show(
    id: str = typer.Argument(help="from: wxcli cc-entry-point list"),
    include_names: str = typer.Option(None, "--include-names", help="Specifiy whether to include flow override settings reference variable names."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get specific Entry Point by ID.\n\n\b\nExample: wxcli cc-entry-point show ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/entry-point/{id}"
    params = {}
    if include_names is not None:
        params["includeNames"] = include_names
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"name":"...","entryPointType":"INBOUND","channelType":"TELEPHONY","socialChannelType":"MESSAGEBIRD","active":true,"serviceLevelThreshold":0,"maximumActiveContacts":0,"controlFlowScriptUrl":"..."}'

@app.command("update", short_help="Update specific Entry Point by ID.")
def update(
    id: str = typer.Argument(help="from: wxcli cc-entry-point list"),
    organization_id: str = typer.Option(None, "--organization-id", help="ID of the contact center organization. It is required to define for the following operations - All bulk save operations"),
    id_param: str = typer.Option(None, "--id", help="ID of this contact center resource. It should not be specified when creating a new resource. However, it is mandatory when updating a resource."),
    version: str = typer.Option(None, "--version", help="The version of this resource. For a newly created resource, it will be 0 unless specified otherwise."),
    name: str = typer.Option(None, "--name", help="A unique name for the entry point within the organization. It is required only during a create or an update operation."),
    description: str = typer.Option(None, "--description", help="A short description of the entry point."),
    entry_point_type: str = typer.Option(None, "--entry-point-type", help="Choices: INBOUND, OUTBOUND"),
    channel_type: str = typer.Option(None, "--channel-type", help="Choices: TELEPHONY, EMAIL, FAX, CHAT, VIDEO, OTHERS, SOCIAL_CHANNEL"),
    social_channel_type: str = typer.Option(None, "--social-channel-type", help="Choices: MESSAGEBIRD, MESSENGER, WHATSAPP, APPLE_BUSINESS_CHAT, GOOGLE_BUSINESS_MESSAGES"),
    active: bool = typer.Option(None, "--active/--no-active", help="Used to toggle the state of the entrypoint from active to inactive and vice-versa. It is required only during a create or an update operation."),
    service_level_threshold: str = typer.Option(None, "--service-level-threshold", help="Allows to set the time that a customer request can be in a queue before the system flags it as outside the service level. If the agent completes a customer service request within this time interval, the system considers it within the service level. It is required only for a create or an update..."),
    maximum_active_contacts: str = typer.Option(None, "--maximum-active-contacts", help="Caps the maximum number of simultaneous calls for this entry point. The system busies out any additional calls when the number of active calls exceeds this number. It is required only for a create or an update operation."),
    control_flow_script_url: str = typer.Option(None, "--control-flow-script-url", help="The system automatically populates this field with the URL for this entry point or the default control script of the queue.It happens when you don’t configure the control script using the Webex Contact Center Routing Strategy module.This setting is available for the Telephony channel type."),
    overflow_number: str = typer.Option(None, "--overflow-number", help="Allows to set the destination phone number to which the system diverts the customer calls when they exceed the Maximum Time in Queue that has been set in the routing strategy. This setting is applicable only for the Telephony channel type."),
    timezone: str = typer.Option(None, "--timezone", help="(Optional) Any routing strategy for this entry point uses the time zone that you select here."),
    imi_org_type: str = typer.Option(None, "--imi-org-type", help="Choices: MIXED_MODE, IMI"),
    asset_id: str = typer.Option(None, "--asset-id", help="ID of the asset in IMI that corresponds to this entrypoint."),
    xsp_version: str = typer.Option(None, "--xsp-version", help="(Optional) Used to subscribe for recording events."),
    subscription_id: str = typer.Option(None, "--subscription-id", help="(Optional) Used to subscribe for recording events."),
    route_point_id: str = typer.Option(None, "--route-point-id", help="The identifier of a route point of WxC which is similar to entry point of WxCC"),
    flow_id: str = typer.Option(None, "--flow-id", help=""),
    flow_tag_id: str = typer.Option(None, "--flow-tag-id", help=""),
    music_on_hold_id: str = typer.Option(None, "--music-on-hold-id", help=""),
    outdial_queue_id: str = typer.Option(None, "--outdial-queue-id", help=""),
    system_default: bool = typer.Option(None, "--system-default/--no-system-default", help="Indicates whether the created resource is system created or not"),
    callback_enabled: bool = typer.Option(None, "--callback-enabled/--no-callback-enabled", help="Indicates whether the created resource is call back enabled or not"),
    outdial_transfer_to_queue_enabled: bool = typer.Option(None, "--outdial-transfer-to-queue-enabled/--no-outdial-transfer-to-queue-enabled", help="Indicates whether the resource is Default Outdial Transfer to Queue."),
    dn_ep_mapping_count: str = typer.Option(None, "--dn-ep-mapping-count", help=""),
    created_time: str = typer.Option(None, "--created-time", help="Creation time(in epoch millis) of this resource."),
    last_updated_time: str = typer.Option(None, "--last-updated-time", help="Time(in epoch millis) when this resource was last updated."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update specific Entry Point by ID.\n\n\b\nExample: wxcli cc-entry-point update ID --name NAME --entry-point-type INBOUND --channel-type TELEPHONY --social-channel-type MESSAGEBIRD --active --service-level-threshold SERVICE_LEVEL_THRESHOLD --maximum-active-contacts MAXIMUM_ACTIVE_CONTACTS --control-flow-script-url CONTROL_FLOW_SCRIPT_URL --overflow-number OVERFLOW_NUMBER --imi-org-type MIXED_MODE --asset-id ASSET_ID\n\n\b\nExample --json-body: '{"name":"...","entryPointType":"INBOUND","channelType":"TELEPHONY","socialChannelType":"MESSAGEBIRD","active":true,"serviceLevelThreshold":0,"maximumActiveContacts":0,"controlFlowScriptUrl":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/entry-point/{id}"
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
        if entry_point_type is not None:
            body["entryPointType"] = entry_point_type
        if channel_type is not None:
            body["channelType"] = channel_type
        if social_channel_type is not None:
            body["socialChannelType"] = social_channel_type
        if active is not None:
            body["active"] = active
        if service_level_threshold is not None:
            body["serviceLevelThreshold"] = service_level_threshold
        if maximum_active_contacts is not None:
            body["maximumActiveContacts"] = maximum_active_contacts
        if control_flow_script_url is not None:
            body["controlFlowScriptUrl"] = control_flow_script_url
        if overflow_number is not None:
            body["overflowNumber"] = overflow_number
        if timezone is not None:
            body["timezone"] = timezone
        if imi_org_type is not None:
            body["imiOrgType"] = imi_org_type
        if asset_id is not None:
            body["assetId"] = asset_id
        if xsp_version is not None:
            body["xspVersion"] = xsp_version
        if subscription_id is not None:
            body["subscriptionId"] = subscription_id
        if route_point_id is not None:
            body["routePointId"] = route_point_id
        if flow_id is not None:
            body["flowId"] = flow_id
        if flow_tag_id is not None:
            body["flowTagId"] = flow_tag_id
        if music_on_hold_id is not None:
            body["musicOnHoldId"] = music_on_hold_id
        if outdial_queue_id is not None:
            body["outdialQueueId"] = outdial_queue_id
        if system_default is not None:
            body["systemDefault"] = system_default
        if callback_enabled is not None:
            body["callbackEnabled"] = callback_enabled
        if outdial_transfer_to_queue_enabled is not None:
            body["outdialTransferToQueueEnabled"] = outdial_transfer_to_queue_enabled
        if dn_ep_mapping_count is not None:
            body["dnEpMappingCount"] = dn_ep_mapping_count
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



@app.command("delete", short_help="Delete specific Entry Point by ID.")
def delete(
    id: str = typer.Argument(help="from: wxcli cc-entry-point list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete specific Entry Point by ID.\n\n\b\nExample: wxcli cc-entry-point delete ID"""
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/entry-point/{id}"
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



@app.command("list-incoming-references", short_help="List references for a specific Entry Point.")
def list_incoming_references(
    id: str = typer.Argument(help="UUID, from: wxcli cc-entry-point list"),
    type_param: str = typer.Option(None, "--type", help="Entity type of the other entity that has a reference to this specific entity."),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List references for a specific Entry Point.\n\n\b\nExample: wxcli cc-entry-point list-incoming-references ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/entry-point/{id}/incoming-references"
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



@app.command("list-entry-point", short_help="List Entry Point(s).")
def list_entry_point(
    filter_param: str = typer.Option(None, "--filter", help="Specify a filter based on which the results will be fetched. All the fields are supported except: organizationId, xspVersion, createdTime, lastUpdatedTime The examples below show some search queries - id==\"57efb0e6-5af0-4245-a67d-d3c5045cdb6e\" - id!=\"57efb0e6-5af0-4245-a67d-d3c5045cdb6e\" -..."),
    attributes: str = typer.Option(None, "--attributes", help="Specify the attributes to be returned.Default all attributes are returned along with specified columns. All Attributes are supported except (ccOneQueue, userIds, queueRankings, links)"),
    search: str = typer.Option(None, "--search", help="Filter data based on the search keyword.Supported search columns(name, description) The examples below show some search queries - \"Cisco\" - field==\"name\";value==\"Cisco\" - fields=in=(\"name\",\"description\");value==\"Cisco\""),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    desktop_profile_filter: str = typer.Option(None, "--desktop-profile-filter", help="If set to true, the API will return only the data that the user has access to according to its Desktop Profile. If set to false, the API will not check for Desktop Profile level access."),
    provisioning_view: str = typer.Option(None, "--provisioning-view", help="If set to true, the API will only return data that user has access to, according to User Profile. If set to false and desktopProfileFilter query parameter is not specified, the API will add user associated data, based on desktop."),
    include_count: str = typer.Option(None, "--include-count", help="Enable the flag to get the count of DN-EP Mapping"),
    single_object_response: str = typer.Option(None, "--single-object-response", help="Specifiy whether to include array fields in the response, This query param should use only if the response contain single record, if we are using for multiple objects response query param not supported and throws an exception."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Entry Point(s)."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/v2/entry-point"
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


