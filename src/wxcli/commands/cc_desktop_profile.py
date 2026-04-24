import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id, get_cc_base_url, get_cc_org_id


app = typer.Typer(help="Manage Webex Contact Center cc-desktop-profile.")


@app.command("list")
def cmd_list(
    filter_param: str = typer.Option(None, "--filter", help="Specify a filter based on which the results will be fetched."),
    attributes: str = typer.Option(None, "--attributes", help="Specify the attributes to be returned.Default all attributes"),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts"),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If th"),
    single_object_response: str = typer.Option(None, "--single-object-response", help="Specifiy whether to include array fields in the response, Th"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Desktop Profile(s)."""
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create")
def create(
    organization_id: str = typer.Option(None, "--organization-id", help="ID of the contact center organization. It is required to def"),
    id_param: str = typer.Option(None, "--id", help="ID of this contact center resource. It should not be specifi"),
    version: str = typer.Option(None, "--version", help="The version of this resource. For a newly created resource,"),
    name: str = typer.Option(None, "--name", help="(required) Enter a name for the agent profile."),
    description: str = typer.Option(None, "--description", help="(Optional) Enter a description of the profile."),
    parent_type: str = typer.Option(None, "--parent-type", help="(required) Choices: ORGANIZATION, SITE"),
    site_id: str = typer.Option(None, "--site-id", help="Identifier for a site which is a physical contact center loc"),
    screen_popup: bool = typer.Option(None, "--screen-popup/--no-screen-popup", help="Indicates whether to allow external pop-up screens(true) or"),
    last_agent_routing: bool = typer.Option(None, "--last-agent-routing/--no-last-agent-routing", help="This setting use only if your administrator enables the Last"),
    auto_wrap_up: bool = typer.Option(None, "--auto-wrap-up/--no-auto-wrap-up", help="Indicates whether to allow auto wrap-up(true) or not(false)."),
    auto_answer: bool = typer.Option(None, "--auto-answer/--no-auto-answer", help="Indicates whether incoming calls on the Agent Desktop need t"),
    auto_wrap_after_seconds: str = typer.Option(None, "--auto-wrap-after-seconds", help="This setting allows auto wrap-up after seconds"),
    agent_available_after_outdial: bool = typer.Option(None, "--agent-available-after-outdial/--no-agent-available-after-outdial", help="Enabled if you want the agent to go into the Available state"),
    allow_auto_wrap_up_extension: bool = typer.Option(None, "--allow-auto-wrap-up-extension/--no-allow-auto-wrap-up-extension", help="Indicates whether to allow auto wrap-up extension(true) or n"),
    access_wrap_up_code: str = typer.Option(None, "--access-wrap-up-code", help="(required) Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    access_idle_code: str = typer.Option(None, "--access-idle-code", help="(required) Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    access_queue: str = typer.Option(None, "--access-queue", help="(required) Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    access_entry_point: str = typer.Option(None, "--access-entry-point", help="(required) Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    access_buddy_team: str = typer.Option(None, "--access-buddy-team", help="(required) Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    consult_to_queue: bool = typer.Option(None, "--consult-to-queue/--no-consult-to-queue", help="Indicates whether you  want the agent to be able to select a"),
    outdial_enabled: bool = typer.Option(None, "--outdial-enabled/--no-outdial-enabled", help="Indicates whether you want the agent to be able to make outd"),
    outdial_entry_point_id: str = typer.Option(None, "--outdial-entry-point-id", help="If you enabled Outdial, specify the entry point id that the"),
    outdial_ani_id: str = typer.Option(None, "--outdial-ani-id", help="This setting occurs only if you enabled Outdial. Specify the"),
    address_book_id: str = typer.Option(None, "--address-book-id", help="Specify the address book id that includes the speed-dial num"),
    dial_plan_enabled: bool = typer.Option(None, "--dial-plan-enabled/--no-dial-plan-enabled", help="Indicates whether you want the agent to be able to make ad-h"),
    agent_dn_validation: str = typer.Option(None, "--agent-dn-validation", help="(required) Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    agent_dn_validation_criteria: str = typer.Option(None, "--agent-dn-validation-criteria", help="Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    active: bool = typer.Option(None, "--active/--no-active", help="(required) Specify whether the agent profile is active or not Active."),
    timeout_desktop_inactivity_custom_enabled: bool = typer.Option(None, "--timeout-desktop-inactivity-custom-enabled/--no-timeout-desktop-inactivity-custom-enabled", help="This setting enabled time out desktop inactivity feature."),
    show_user_details_ms: bool = typer.Option(None, "--show-user-details-ms/--no-show-user-details-ms", help="Specify whether the show user details of microsoft account u"),
    state_synchronization_ms: bool = typer.Option(None, "--state-synchronization-ms/--no-state-synchronization-ms", help="Specify whether the state synchronization of microsoft accou"),
    show_user_details_webex: bool = typer.Option(None, "--show-user-details-webex/--no-show-user-details-webex", help="Specify whether the show user details of webex account user"),
    state_synchronization_webex: bool = typer.Option(None, "--state-synchronization-webex/--no-state-synchronization-webex", help="Specify whether the state synchronization of webex account u"),
    timeout_desktop_inactivity_mins: str = typer.Option(None, "--timeout-desktop-inactivity-mins", help="This setting occurs only if you enabled time out desktop ina"),
    system_default: bool = typer.Option(None, "--system-default/--no-system-default", help="Indicates whether the created resource is system created or"),
    created_time: str = typer.Option(None, "--created-time", help="Creation time(in epoch millis) of this resource."),
    last_updated_time: str = typer.Option(None, "--last-updated-time", help="Time(in epoch millis) when this resource was last updated."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new Desktop Profile\n\nExample --json-body:\n  '{"name":"...","parentType":"ORGANIZATION","accessWrapUpCode":"SPECIFIC","accessIdleCode":"SPECIFIC","accessQueue":"SPECIFIC","accessEntryPoint":"SPECIFIC","accessBuddyTeam":"SPECIFIC","agentDNValidation":"SPECIFIC"}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/agent-profile"
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
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if parent_type is not None:
            body["parentType"] = parent_type
        if site_id is not None:
            body["siteId"] = site_id
        if screen_popup is not None:
            body["screenPopup"] = screen_popup
        if last_agent_routing is not None:
            body["lastAgentRouting"] = last_agent_routing
        if auto_wrap_up is not None:
            body["autoWrapUp"] = auto_wrap_up
        if auto_answer is not None:
            body["autoAnswer"] = auto_answer
        if auto_wrap_after_seconds is not None:
            body["autoWrapAfterSeconds"] = auto_wrap_after_seconds
        if agent_available_after_outdial is not None:
            body["agentAvailableAfterOutdial"] = agent_available_after_outdial
        if allow_auto_wrap_up_extension is not None:
            body["allowAutoWrapUpExtension"] = allow_auto_wrap_up_extension
        if access_wrap_up_code is not None:
            body["accessWrapUpCode"] = access_wrap_up_code
        if access_idle_code is not None:
            body["accessIdleCode"] = access_idle_code
        if access_queue is not None:
            body["accessQueue"] = access_queue
        if access_entry_point is not None:
            body["accessEntryPoint"] = access_entry_point
        if access_buddy_team is not None:
            body["accessBuddyTeam"] = access_buddy_team
        if consult_to_queue is not None:
            body["consultToQueue"] = consult_to_queue
        if outdial_enabled is not None:
            body["outdialEnabled"] = outdial_enabled
        if outdial_entry_point_id is not None:
            body["outdialEntryPointId"] = outdial_entry_point_id
        if outdial_ani_id is not None:
            body["outdialANIId"] = outdial_ani_id
        if address_book_id is not None:
            body["addressBookId"] = address_book_id
        if dial_plan_enabled is not None:
            body["dialPlanEnabled"] = dial_plan_enabled
        if agent_dn_validation is not None:
            body["agentDNValidation"] = agent_dn_validation
        if agent_dn_validation_criteria is not None:
            body["agentDNValidationCriteria"] = agent_dn_validation_criteria
        if active is not None:
            body["active"] = active
        if timeout_desktop_inactivity_custom_enabled is not None:
            body["timeoutDesktopInactivityCustomEnabled"] = timeout_desktop_inactivity_custom_enabled
        if show_user_details_ms is not None:
            body["showUserDetailsMS"] = show_user_details_ms
        if state_synchronization_ms is not None:
            body["stateSynchronizationMS"] = state_synchronization_ms
        if show_user_details_webex is not None:
            body["showUserDetailsWebex"] = show_user_details_webex
        if state_synchronization_webex is not None:
            body["stateSynchronizationWebex"] = state_synchronization_webex
        if timeout_desktop_inactivity_mins is not None:
            body["timeoutDesktopInactivityMins"] = timeout_desktop_inactivity_mins
        if system_default is not None:
            body["systemDefault"] = system_default
        if created_time is not None:
            body["createdTime"] = created_time
        if last_updated_time is not None:
            body["lastUpdatedTime"] = last_updated_time
        _missing = [f for f in ['name', 'parentType', 'accessWrapUpCode', 'accessIdleCode', 'accessQueue', 'accessEntryPoint', 'accessBuddyTeam', 'agentDNValidation', 'active'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
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



@app.command("create-bulk")
def create_bulk(
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk save Desktop Profile(s)\n\nExample --json-body:\n  '{"items":[{"itemIdentifier":"...","item":"...","requestAction":"..."}]}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/agent-profile/bulk"
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



@app.command("list-bulk-export")
def list_bulk_export(
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts"),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If th"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk export Desktop Profile(s)."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/agent-profile/bulk-export"
    params = {}
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create-purge-inactive-entities")
def create_purge_inactive_entities(
    next_start_id: str = typer.Option(None, "--next-start-id", help="This is the entity ID from which items for the next purge ba"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Purge inactive Desktop Profile(s)."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/agent-profile/purge-inactive-entities"
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



@app.command("show")
def show(
    id: str = typer.Argument(help="id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get specific Desktop Profile by ID."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/agent-profile/{id}"
    try:
        result = api.session.rest_get(url)
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



@app.command("update")
def update(
    id: str = typer.Argument(help="id"),
    organization_id: str = typer.Option(None, "--organization-id", help="ID of the contact center organization. It is required to def"),
    id_param: str = typer.Option(None, "--id", help="ID of this contact center resource. It should not be specifi"),
    version: str = typer.Option(None, "--version", help="The version of this resource. For a newly created resource,"),
    name: str = typer.Option(None, "--name", help="Enter a name for the agent profile."),
    description: str = typer.Option(None, "--description", help="(Optional) Enter a description of the profile."),
    parent_type: str = typer.Option(None, "--parent-type", help="Choices: ORGANIZATION, SITE"),
    site_id: str = typer.Option(None, "--site-id", help="Identifier for a site which is a physical contact center loc"),
    screen_popup: bool = typer.Option(None, "--screen-popup/--no-screen-popup", help="Indicates whether to allow external pop-up screens(true) or"),
    last_agent_routing: bool = typer.Option(None, "--last-agent-routing/--no-last-agent-routing", help="This setting use only if your administrator enables the Last"),
    auto_wrap_up: bool = typer.Option(None, "--auto-wrap-up/--no-auto-wrap-up", help="Indicates whether to allow auto wrap-up(true) or not(false)."),
    auto_answer: bool = typer.Option(None, "--auto-answer/--no-auto-answer", help="Indicates whether incoming calls on the Agent Desktop need t"),
    auto_wrap_after_seconds: str = typer.Option(None, "--auto-wrap-after-seconds", help="This setting allows auto wrap-up after seconds"),
    agent_available_after_outdial: bool = typer.Option(None, "--agent-available-after-outdial/--no-agent-available-after-outdial", help="Enabled if you want the agent to go into the Available state"),
    allow_auto_wrap_up_extension: bool = typer.Option(None, "--allow-auto-wrap-up-extension/--no-allow-auto-wrap-up-extension", help="Indicates whether to allow auto wrap-up extension(true) or n"),
    access_wrap_up_code: str = typer.Option(None, "--access-wrap-up-code", help="Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    access_idle_code: str = typer.Option(None, "--access-idle-code", help="Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    access_queue: str = typer.Option(None, "--access-queue", help="Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    access_entry_point: str = typer.Option(None, "--access-entry-point", help="Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    access_buddy_team: str = typer.Option(None, "--access-buddy-team", help="Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    consult_to_queue: bool = typer.Option(None, "--consult-to-queue/--no-consult-to-queue", help="Indicates whether you  want the agent to be able to select a"),
    outdial_enabled: bool = typer.Option(None, "--outdial-enabled/--no-outdial-enabled", help="Indicates whether you want the agent to be able to make outd"),
    outdial_entry_point_id: str = typer.Option(None, "--outdial-entry-point-id", help="If you enabled Outdial, specify the entry point id that the"),
    outdial_ani_id: str = typer.Option(None, "--outdial-ani-id", help="This setting occurs only if you enabled Outdial. Specify the"),
    address_book_id: str = typer.Option(None, "--address-book-id", help="Specify the address book id that includes the speed-dial num"),
    dial_plan_enabled: bool = typer.Option(None, "--dial-plan-enabled/--no-dial-plan-enabled", help="Indicates whether you want the agent to be able to make ad-h"),
    agent_dn_validation: str = typer.Option(None, "--agent-dn-validation", help="Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    agent_dn_validation_criteria: str = typer.Option(None, "--agent-dn-validation-criteria", help="Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    active: bool = typer.Option(None, "--active/--no-active", help="Specify whether the agent profile is active or not Active."),
    timeout_desktop_inactivity_custom_enabled: bool = typer.Option(None, "--timeout-desktop-inactivity-custom-enabled/--no-timeout-desktop-inactivity-custom-enabled", help="This setting enabled time out desktop inactivity feature."),
    show_user_details_ms: bool = typer.Option(None, "--show-user-details-ms/--no-show-user-details-ms", help="Specify whether the show user details of microsoft account u"),
    state_synchronization_ms: bool = typer.Option(None, "--state-synchronization-ms/--no-state-synchronization-ms", help="Specify whether the state synchronization of microsoft accou"),
    show_user_details_webex: bool = typer.Option(None, "--show-user-details-webex/--no-show-user-details-webex", help="Specify whether the show user details of webex account user"),
    state_synchronization_webex: bool = typer.Option(None, "--state-synchronization-webex/--no-state-synchronization-webex", help="Specify whether the state synchronization of webex account u"),
    timeout_desktop_inactivity_mins: str = typer.Option(None, "--timeout-desktop-inactivity-mins", help="This setting occurs only if you enabled time out desktop ina"),
    system_default: bool = typer.Option(None, "--system-default/--no-system-default", help="Indicates whether the created resource is system created or"),
    created_time: str = typer.Option(None, "--created-time", help="Creation time(in epoch millis) of this resource."),
    last_updated_time: str = typer.Option(None, "--last-updated-time", help="Time(in epoch millis) when this resource was last updated."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update specific Desktop Profile by ID\n\nExample --json-body:\n  '{"name":"...","parentType":"ORGANIZATION","accessWrapUpCode":"SPECIFIC","accessIdleCode":"SPECIFIC","accessQueue":"SPECIFIC","accessEntryPoint":"SPECIFIC","accessBuddyTeam":"SPECIFIC","agentDNValidation":"SPECIFIC"}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/agent-profile/{id}"
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
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if parent_type is not None:
            body["parentType"] = parent_type
        if site_id is not None:
            body["siteId"] = site_id
        if screen_popup is not None:
            body["screenPopup"] = screen_popup
        if last_agent_routing is not None:
            body["lastAgentRouting"] = last_agent_routing
        if auto_wrap_up is not None:
            body["autoWrapUp"] = auto_wrap_up
        if auto_answer is not None:
            body["autoAnswer"] = auto_answer
        if auto_wrap_after_seconds is not None:
            body["autoWrapAfterSeconds"] = auto_wrap_after_seconds
        if agent_available_after_outdial is not None:
            body["agentAvailableAfterOutdial"] = agent_available_after_outdial
        if allow_auto_wrap_up_extension is not None:
            body["allowAutoWrapUpExtension"] = allow_auto_wrap_up_extension
        if access_wrap_up_code is not None:
            body["accessWrapUpCode"] = access_wrap_up_code
        if access_idle_code is not None:
            body["accessIdleCode"] = access_idle_code
        if access_queue is not None:
            body["accessQueue"] = access_queue
        if access_entry_point is not None:
            body["accessEntryPoint"] = access_entry_point
        if access_buddy_team is not None:
            body["accessBuddyTeam"] = access_buddy_team
        if consult_to_queue is not None:
            body["consultToQueue"] = consult_to_queue
        if outdial_enabled is not None:
            body["outdialEnabled"] = outdial_enabled
        if outdial_entry_point_id is not None:
            body["outdialEntryPointId"] = outdial_entry_point_id
        if outdial_ani_id is not None:
            body["outdialANIId"] = outdial_ani_id
        if address_book_id is not None:
            body["addressBookId"] = address_book_id
        if dial_plan_enabled is not None:
            body["dialPlanEnabled"] = dial_plan_enabled
        if agent_dn_validation is not None:
            body["agentDNValidation"] = agent_dn_validation
        if agent_dn_validation_criteria is not None:
            body["agentDNValidationCriteria"] = agent_dn_validation_criteria
        if active is not None:
            body["active"] = active
        if timeout_desktop_inactivity_custom_enabled is not None:
            body["timeoutDesktopInactivityCustomEnabled"] = timeout_desktop_inactivity_custom_enabled
        if show_user_details_ms is not None:
            body["showUserDetailsMS"] = show_user_details_ms
        if state_synchronization_ms is not None:
            body["stateSynchronizationMS"] = state_synchronization_ms
        if show_user_details_webex is not None:
            body["showUserDetailsWebex"] = show_user_details_webex
        if state_synchronization_webex is not None:
            body["stateSynchronizationWebex"] = state_synchronization_webex
        if timeout_desktop_inactivity_mins is not None:
            body["timeoutDesktopInactivityMins"] = timeout_desktop_inactivity_mins
        if system_default is not None:
            body["systemDefault"] = system_default
        if created_time is not None:
            body["createdTime"] = created_time
        if last_updated_time is not None:
            body["lastUpdatedTime"] = last_updated_time
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
    """Delete specific Desktop Profile by ID."""
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/agent-profile/{id}"
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {id}")



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
    """List references for a specific Desktop Profile."""
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-agent-profile")
def list_agent_profile(
    filter_param: str = typer.Option(None, "--filter", help="Specify a filter based on which the results will be fetched."),
    attributes: str = typer.Option(None, "--attributes", help="Specify the attributes to be returned.Default all attributes"),
    search: str = typer.Option(None, "--search", help="Filter data based on the search keyword.Supported search col"),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts"),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If th"),
    single_object_response: str = typer.Option(None, "--single-object-response", help="Specifiy whether to include array fields in the response, Th"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Desktop Profile(s)."""
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
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)


