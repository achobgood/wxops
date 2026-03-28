import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling desktop-profile.")


@app.command("create")
def create(
    orgid: str = typer.Argument(help="orgid"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk save Desktop Profile(s)\n\nExample --json-body:\n  '{"items":[{"item":"...","itemIdentifier":"...","requestAction":"..."}]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/agent-profile/bulk"
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
    url = f"https://webexapis.com/v1/organization/{orgid}/agent-profile"
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
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create-agent-profile")
def create_agent_profile(
    orgid: str = typer.Argument(help="orgid"),
    agent_dn_validation_criteria: str = typer.Option(None, "--agent-dn-validation-criteria", help=""),
    timeout_desktop_inactivity_custom_enabled: str = typer.Option(None, "--timeout-desktop-inactivity-custom-enabled", help=""),
    show_user_details_ms: str = typer.Option(None, "--show-user-details-ms", help=""),
    state_synchronization_ms: str = typer.Option(None, "--state-synchronization-ms", help=""),
    parent_type: str = typer.Option(None, "--parent-type", help=""),
    state_synchronization_webex: str = typer.Option(None, "--state-synchronization-webex", help=""),
    timeout_desktop_inactivity_mins: str = typer.Option(None, "--timeout-desktop-inactivity-mins", help=""),
    version: str = typer.Option(None, "--version", help=""),
    address_book_id: str = typer.Option(None, "--address-book-id", help=""),
    site_id: str = typer.Option(None, "--site-id", help=""),
    allow_auto_wrap_up_extension: str = typer.Option(None, "--allow-auto-wrap-up-extension", help=""),
    show_user_details_webex: str = typer.Option(None, "--show-user-details-webex", help=""),
    auto_answer: str = typer.Option(None, "--auto-answer", help=""),
    last_agent_routing: str = typer.Option(None, "--last-agent-routing", help=""),
    name: str = typer.Option(None, "--name", help=""),
    agent_available_after_outdial: str = typer.Option(None, "--agent-available-after-outdial", help=""),
    auto_wrap_after_seconds: str = typer.Option(None, "--auto-wrap-after-seconds", help=""),
    organization_id: str = typer.Option(None, "--organization-id", help=""),
    auto_wrap_up: str = typer.Option(None, "--auto-wrap-up", help=""),
    active: str = typer.Option(None, "--active", help=""),
    id_param: str = typer.Option(None, "--id", help=""),
    access_buddy_team: str = typer.Option(None, "--access-buddy-team", help=""),
    access_entry_point: str = typer.Option(None, "--access-entry-point", help=""),
    description: str = typer.Option(None, "--description", help=""),
    access_queue: str = typer.Option(None, "--access-queue", help=""),
    access_wrap_up_code: str = typer.Option(None, "--access-wrap-up-code", help=""),
    agent_dn_validation: str = typer.Option(None, "--agent-dn-validation", help=""),
    screen_popup: str = typer.Option(None, "--screen-popup", help=""),
    system_default: str = typer.Option(None, "--system-default", help=""),
    access_idle_code: str = typer.Option(None, "--access-idle-code", help=""),
    consult_to_queue: str = typer.Option(None, "--consult-to-queue", help=""),
    outdial_enabled: str = typer.Option(None, "--outdial-enabled", help=""),
    outdial_entry_point_id: str = typer.Option(None, "--outdial-entry-point-id", help=""),
    outdial_ani_id: str = typer.Option(None, "--outdial-ani-id", help=""),
    dial_plan_enabled: str = typer.Option(None, "--dial-plan-enabled", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new Desktop Profile\n\nExample --json-body:\n  '{"agentDNValidationCriteria":"...","agentDNValidationCriterions":["..."],"loginVoiceOptions":["..."],"thresholdRules":["..."],"timeoutDesktopInactivityCustomEnabled":"...","showUserDetailsMS":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/agent-profile"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if agent_dn_validation_criteria is not None:
            body["agentDNValidationCriteria"] = agent_dn_validation_criteria
        if timeout_desktop_inactivity_custom_enabled is not None:
            body["timeoutDesktopInactivityCustomEnabled"] = timeout_desktop_inactivity_custom_enabled
        if show_user_details_ms is not None:
            body["showUserDetailsMS"] = show_user_details_ms
        if state_synchronization_ms is not None:
            body["stateSynchronizationMS"] = state_synchronization_ms
        if parent_type is not None:
            body["parentType"] = parent_type
        if state_synchronization_webex is not None:
            body["stateSynchronizationWebex"] = state_synchronization_webex
        if timeout_desktop_inactivity_mins is not None:
            body["timeoutDesktopInactivityMins"] = timeout_desktop_inactivity_mins
        if version is not None:
            body["version"] = version
        if address_book_id is not None:
            body["addressBookId"] = address_book_id
        if site_id is not None:
            body["siteId"] = site_id
        if allow_auto_wrap_up_extension is not None:
            body["allowAutoWrapUpExtension"] = allow_auto_wrap_up_extension
        if show_user_details_webex is not None:
            body["showUserDetailsWebex"] = show_user_details_webex
        if auto_answer is not None:
            body["autoAnswer"] = auto_answer
        if last_agent_routing is not None:
            body["lastAgentRouting"] = last_agent_routing
        if name is not None:
            body["name"] = name
        if agent_available_after_outdial is not None:
            body["agentAvailableAfterOutdial"] = agent_available_after_outdial
        if auto_wrap_after_seconds is not None:
            body["autoWrapAfterSeconds"] = auto_wrap_after_seconds
        if organization_id is not None:
            body["organizationId"] = organization_id
        if auto_wrap_up is not None:
            body["autoWrapUp"] = auto_wrap_up
        if active is not None:
            body["active"] = active
        if id_param is not None:
            body["id"] = id_param
        if access_buddy_team is not None:
            body["accessBuddyTeam"] = access_buddy_team
        if access_entry_point is not None:
            body["accessEntryPoint"] = access_entry_point
        if description is not None:
            body["description"] = description
        if access_queue is not None:
            body["accessQueue"] = access_queue
        if access_wrap_up_code is not None:
            body["accessWrapUpCode"] = access_wrap_up_code
        if agent_dn_validation is not None:
            body["agentDNValidation"] = agent_dn_validation
        if screen_popup is not None:
            body["screenPopup"] = screen_popup
        if system_default is not None:
            body["systemDefault"] = system_default
        if access_idle_code is not None:
            body["accessIdleCode"] = access_idle_code
        if consult_to_queue is not None:
            body["consultToQueue"] = consult_to_queue
        if outdial_enabled is not None:
            body["outdialEnabled"] = outdial_enabled
        if outdial_entry_point_id is not None:
            body["outdialEntryPointId"] = outdial_entry_point_id
        if outdial_ani_id is not None:
            body["outdialANIId"] = outdial_ani_id
        if dial_plan_enabled is not None:
            body["dialPlanEnabled"] = dial_plan_enabled
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



@app.command("list-bulk-export")
def list_bulk_export(
    orgid: str = typer.Argument(help="orgid"),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts"),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If th"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk export Desktop Profile(s)."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/agent-profile/bulk-export"
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
    """Purge inactive Desktop Profile(s)."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/agent-profile/purge-inactive-entities"
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



@app.command("show")
def show(
    orgid: str = typer.Argument(help="orgid"),
    id: str = typer.Argument(help="id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get specific Desktop Profile by ID."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/agent-profile/{id}"
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
    agent_dn_validation_criteria: str = typer.Option(None, "--agent-dn-validation-criteria", help=""),
    timeout_desktop_inactivity_custom_enabled: str = typer.Option(None, "--timeout-desktop-inactivity-custom-enabled", help=""),
    show_user_details_ms: str = typer.Option(None, "--show-user-details-ms", help=""),
    state_synchronization_ms: str = typer.Option(None, "--state-synchronization-ms", help=""),
    parent_type: str = typer.Option(None, "--parent-type", help=""),
    state_synchronization_webex: str = typer.Option(None, "--state-synchronization-webex", help=""),
    timeout_desktop_inactivity_mins: str = typer.Option(None, "--timeout-desktop-inactivity-mins", help=""),
    version: str = typer.Option(None, "--version", help=""),
    address_book_id: str = typer.Option(None, "--address-book-id", help=""),
    site_id: str = typer.Option(None, "--site-id", help=""),
    allow_auto_wrap_up_extension: str = typer.Option(None, "--allow-auto-wrap-up-extension", help=""),
    show_user_details_webex: str = typer.Option(None, "--show-user-details-webex", help=""),
    auto_answer: str = typer.Option(None, "--auto-answer", help=""),
    last_agent_routing: str = typer.Option(None, "--last-agent-routing", help=""),
    name: str = typer.Option(None, "--name", help=""),
    agent_available_after_outdial: str = typer.Option(None, "--agent-available-after-outdial", help=""),
    auto_wrap_after_seconds: str = typer.Option(None, "--auto-wrap-after-seconds", help=""),
    organization_id: str = typer.Option(None, "--organization-id", help=""),
    auto_wrap_up: str = typer.Option(None, "--auto-wrap-up", help=""),
    active: str = typer.Option(None, "--active", help=""),
    id_param: str = typer.Option(None, "--id", help=""),
    access_buddy_team: str = typer.Option(None, "--access-buddy-team", help=""),
    access_entry_point: str = typer.Option(None, "--access-entry-point", help=""),
    description: str = typer.Option(None, "--description", help=""),
    access_queue: str = typer.Option(None, "--access-queue", help=""),
    access_wrap_up_code: str = typer.Option(None, "--access-wrap-up-code", help=""),
    agent_dn_validation: str = typer.Option(None, "--agent-dn-validation", help=""),
    screen_popup: str = typer.Option(None, "--screen-popup", help=""),
    system_default: str = typer.Option(None, "--system-default", help=""),
    access_idle_code: str = typer.Option(None, "--access-idle-code", help=""),
    consult_to_queue: str = typer.Option(None, "--consult-to-queue", help=""),
    outdial_enabled: str = typer.Option(None, "--outdial-enabled", help=""),
    outdial_entry_point_id: str = typer.Option(None, "--outdial-entry-point-id", help=""),
    outdial_ani_id: str = typer.Option(None, "--outdial-ani-id", help=""),
    dial_plan_enabled: str = typer.Option(None, "--dial-plan-enabled", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update specific Desktop Profile by ID\n\nExample --json-body:\n  '{"agentDNValidationCriteria":"...","agentDNValidationCriterions":["..."],"loginVoiceOptions":["..."],"thresholdRules":["..."],"timeoutDesktopInactivityCustomEnabled":"...","showUserDetailsMS":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/agent-profile/{id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if agent_dn_validation_criteria is not None:
            body["agentDNValidationCriteria"] = agent_dn_validation_criteria
        if timeout_desktop_inactivity_custom_enabled is not None:
            body["timeoutDesktopInactivityCustomEnabled"] = timeout_desktop_inactivity_custom_enabled
        if show_user_details_ms is not None:
            body["showUserDetailsMS"] = show_user_details_ms
        if state_synchronization_ms is not None:
            body["stateSynchronizationMS"] = state_synchronization_ms
        if parent_type is not None:
            body["parentType"] = parent_type
        if state_synchronization_webex is not None:
            body["stateSynchronizationWebex"] = state_synchronization_webex
        if timeout_desktop_inactivity_mins is not None:
            body["timeoutDesktopInactivityMins"] = timeout_desktop_inactivity_mins
        if version is not None:
            body["version"] = version
        if address_book_id is not None:
            body["addressBookId"] = address_book_id
        if site_id is not None:
            body["siteId"] = site_id
        if allow_auto_wrap_up_extension is not None:
            body["allowAutoWrapUpExtension"] = allow_auto_wrap_up_extension
        if show_user_details_webex is not None:
            body["showUserDetailsWebex"] = show_user_details_webex
        if auto_answer is not None:
            body["autoAnswer"] = auto_answer
        if last_agent_routing is not None:
            body["lastAgentRouting"] = last_agent_routing
        if name is not None:
            body["name"] = name
        if agent_available_after_outdial is not None:
            body["agentAvailableAfterOutdial"] = agent_available_after_outdial
        if auto_wrap_after_seconds is not None:
            body["autoWrapAfterSeconds"] = auto_wrap_after_seconds
        if organization_id is not None:
            body["organizationId"] = organization_id
        if auto_wrap_up is not None:
            body["autoWrapUp"] = auto_wrap_up
        if active is not None:
            body["active"] = active
        if id_param is not None:
            body["id"] = id_param
        if access_buddy_team is not None:
            body["accessBuddyTeam"] = access_buddy_team
        if access_entry_point is not None:
            body["accessEntryPoint"] = access_entry_point
        if description is not None:
            body["description"] = description
        if access_queue is not None:
            body["accessQueue"] = access_queue
        if access_wrap_up_code is not None:
            body["accessWrapUpCode"] = access_wrap_up_code
        if agent_dn_validation is not None:
            body["agentDNValidation"] = agent_dn_validation
        if screen_popup is not None:
            body["screenPopup"] = screen_popup
        if system_default is not None:
            body["systemDefault"] = system_default
        if access_idle_code is not None:
            body["accessIdleCode"] = access_idle_code
        if consult_to_queue is not None:
            body["consultToQueue"] = consult_to_queue
        if outdial_enabled is not None:
            body["outdialEnabled"] = outdial_enabled
        if outdial_entry_point_id is not None:
            body["outdialEntryPointId"] = outdial_entry_point_id
        if outdial_ani_id is not None:
            body["outdialANIId"] = outdial_ani_id
        if dial_plan_enabled is not None:
            body["dialPlanEnabled"] = dial_plan_enabled
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
    """Delete specific Desktop Profile by ID."""
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/agent-profile/{id}"
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
    """List references for a specific Desktop Profile."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/organization/{orgid}/agent-profile/{id}/incoming-references"
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



@app.command("list-agent-profile")
def list_agent_profile(
    orgid: str = typer.Argument(help="orgid"),
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
    url = f"https://webexapis.com/v1/organization/{orgid}/v2/agent-profile"
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
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)


