import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import resolve_org_id, get_cc_base_url, get_cc_org_id
from wxcli.common import verify_write


app = typer.Typer(help="Manage Webex Contact Center: cc-desktop-profile.")


@app.command("list", short_help="List Desktop Profiles.")
def cmd_list(
    filter_param: str = typer.Option(None, "--filter", help="Specify a filter based on which the results will be fetched. Supported filterable fields: id. The examples below show some search queries - id==\"57efb0e6-5af0-4245-a67d-d3c5045cdb6e\" - id!=\"57efb0e6-5af0-4245-a67d-d3c5045cdb6e\" -..."),
    attributes: str = typer.Option(None, "--attributes", help="Specify the attributes to be returned. By default, all attributes are returned along with the specified columns. All attributes are supported. except ( wrapUpCodes,queues, idleCodes,entryPoints, buddyTeams, dialPlans, loginVoiceOptions, viewableStatistics, thresholdRules,agentDNValidationCriterions..."),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    single_object_response: str = typer.Option(None, "--single-object-response", help="Specify whether to include array fields in the response. This query parameter should be used only when the response contains a single record. It is not supported for responses with multiple objects and throws an exception."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results, sent as the page size (pageSize); 0 = the server default page. Ignored with --all."),
    offset: int = typer.Option(0, "--offset", help="Skip this many records (translated to the page number; record-exact)."),
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
    if limit > 0 and not all_pages and params.get("pageSize") is None:
        params["pageSize"] = limit
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_page_param(url=url, params=params, item_key="items"))
        elif offset > 0:
            result = api.session.fetch_from_offset(url=url, params=params, offset=offset, count=limit, item_key="items")
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



_BODY_SKELETON_CREATE = '{"name":"...","parentType":"ORGANIZATION","accessWrapUpCode":"SPECIFIC","accessIdleCode":"SPECIFIC","accessQueue":"SPECIFIC","accessEntryPoint":"SPECIFIC","accessBuddyTeam":"SPECIFIC","agentDNValidation":"SPECIFIC","viewableStatistics":{"accessQueueStats":"SPECIFIC","accessTeamStats":"SPECIFIC","organizationId":"...","id":"...","version":0,"agentStats":true,"contactServiceQueues":["..."],"loggedInTeamStats":true,"teams":["..."],"createdTime":0,"lastUpdatedTime":0},"active":true,"organizationId":"...","id":"...","version":0,"description":"...","siteId":"...","screenPopup":true,"lastAgentRouting":true,"scheduleAndManageCallBack":true,"autoWrapUp":true,"autoAnswer":true,"agentPersonalGreeting":true,"autoWrapAfterSeconds":0,"agentAvailableAfterOutdial":true,"allowAutoWrapUpExtension":true,"wrapUpCodes":["..."],"idleCodes":["..."],"queues":["..."],"entryPoints":["..."],"buddyTeams":["..."],"consultToQueue":true,"outdialEnabled":true,"outdialEntryPointId":"...","outdialANIId":"...","addressBookId":"...","dialPlanEnabled":true,"dialPlans":["..."],"agentDNValidationCriteria":"SPECIFIC","agentDNValidationCriterions":["..."],"loginVoiceOptions":["AGENT_DN"],"thresholdRules":["..."],"timeoutDesktopInactivityCustomEnabled":true,"showUserDetailsMS":true,"stateSynchronizationMS":true,"showUserDetailsWebex":true,"stateSynchronizationWebex":true,"manageChannelAvailability":true,"timeoutDesktopInactivityMins":0,"systemDefault":true,"createdTime":0,"lastUpdatedTime":0,"autoAcceptDigitalInteractions":true}'

@app.command("create", short_help="Create a new Desktop Profile.")
def create(
    organization_id: str = typer.Option(None, "--organization-id", help="ID of the contact center organization. This field is required for all bulk save operations."),
    id_param: str = typer.Option(None, "--id", help="ID of this contact center resource. It should not be specified when creating a new resource. However, it is mandatory when updating a resource."),
    version: str = typer.Option(None, "--version", help="The version of this resource. For a newly created resource, it will be 0 unless specified otherwise."),
    name: str = typer.Option(None, "--name", help="(required) Enter a name for the agent profile."),
    description: str = typer.Option(None, "--description", help="(Optional) Enter a description of the profile."),
    parent_type: str = typer.Option(None, "--parent-type", help="(required) Choices: ORGANIZATION, SITE"),
    site_id: str = typer.Option(None, "--site-id", help="Identifier for a site which is a physical contact center location under the control of your enterprise."),
    screen_popup: bool = typer.Option(None, "--screen-popup/--no-screen-popup", help="Indicates whether to allow external pop-up screens(true) or not(false)."),
    last_agent_routing: bool = typer.Option(None, "--last-agent-routing/--no-last-agent-routing", help="This setting use only if your administrator enables the Last Agent Routing feature for your enterprise. Indicates whether to allow Last Agent Routing check box on the Agent Desktop during wrap-up(true) or not(false)."),
    schedule_and_manage_call_back: bool = typer.Option(None, "--schedule-and-manage-call-back/--no-schedule-and-manage-call-back", help="Indicates whether to allow agents to schedule and manage callbacks(true) or not(false)."),
    auto_wrap_up: bool = typer.Option(None, "--auto-wrap-up/--no-auto-wrap-up", help="Indicates whether to allow auto wrap-up(true) or not(false)."),
    auto_answer: bool = typer.Option(None, "--auto-answer/--no-auto-answer", help="Indicates whether incoming calls on the Agent Desktop need to be answered automatically(true) or not(false)."),
    agent_personal_greeting: bool = typer.Option(None, "--agent-personal-greeting/--no-agent-personal-greeting", help="Indicates whether an agent can record a personal greeting(true) or not(false) from the agent desktop."),
    auto_wrap_after_seconds: str = typer.Option(None, "--auto-wrap-after-seconds", help="This setting allows auto wrap-up after seconds"),
    agent_available_after_outdial: bool = typer.Option(None, "--agent-available-after-outdial/--no-agent-available-after-outdial", help="Enabled if you want the agent to go into the Available state after completing and wrapping up an outdial call. The agent can also manually select an Idle state from the STATUS NOW drop-down list before selecting a wrap-up code."),
    allow_auto_wrap_up_extension: bool = typer.Option(None, "--allow-auto-wrap-up-extension/--no-allow-auto-wrap-up-extension", help="Indicates whether to allow auto wrap-up extension(true) or not(false)."),
    access_wrap_up_code: str = typer.Option(None, "--access-wrap-up-code", help="(required) Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    access_idle_code: str = typer.Option(None, "--access-idle-code", help="(required) Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    access_queue: str = typer.Option(None, "--access-queue", help="(required) Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    access_entry_point: str = typer.Option(None, "--access-entry-point", help="(required) Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    access_buddy_team: str = typer.Option(None, "--access-buddy-team", help="(required) Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    consult_to_queue: bool = typer.Option(None, "--consult-to-queue/--no-consult-to-queue", help="Indicates whether you want the agent to be able to select a queue in the Queue drop-down list as a target for a consultation or not."),
    outdial_enabled: bool = typer.Option(None, "--outdial-enabled/--no-outdial-enabled", help="Indicates whether you want the agent to be able to make outdial calls(true) or not(false)."),
    outdial_entry_point_id: str = typer.Option(None, "--outdial-entry-point-id", help="If you enabled Outdial, specify the entry point id that the agent can use to make outdial calls."),
    outdial_ani_id: str = typer.Option(None, "--outdial-ani-id", help="This setting occurs only if you enabled Outdial. Specify the Outdial ANI id that the agent can use to make outdial calls."),
    address_book_id: str = typer.Option(None, "--address-book-id", help="Specify the address book id that includes the speed-dial numbers that the agent can select to make outdial and consult calls."),
    dial_plan_enabled: bool = typer.Option(None, "--dial-plan-enabled/--no-dial-plan-enabled", help="Indicates whether you want the agent to be able to make ad-hoc outdial calls(true) or not(false)."),
    agent_dn_validation: str = typer.Option(None, "--agent-dn-validation", help="(required) Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    agent_dn_validation_criteria: str = typer.Option(None, "--agent-dn-validation-criteria", help="Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    active: bool = typer.Option(None, "--active/--no-active", help="(required) Specify whether the agent profile is active or not Active."),
    timeout_desktop_inactivity_custom_enabled: bool = typer.Option(None, "--timeout-desktop-inactivity-custom-enabled/--no-timeout-desktop-inactivity-custom-enabled", help="This setting enabled time out desktop inactivity feature."),
    show_user_details_ms: bool = typer.Option(None, "--show-user-details-ms/--no-show-user-details-ms", help="Specify whether the show user details of microsoft account user enabled or not"),
    state_synchronization_ms: bool = typer.Option(None, "--state-synchronization-ms/--no-state-synchronization-ms", help="Specify whether the state synchronization of microsoft account user enabled or not"),
    show_user_details_webex: bool = typer.Option(None, "--show-user-details-webex/--no-show-user-details-webex", help="Specify whether the show user details of webex account user enabled or not"),
    state_synchronization_webex: bool = typer.Option(None, "--state-synchronization-webex/--no-state-synchronization-webex", help="Specify whether the state synchronization of webex account user enabled or not"),
    manage_channel_availability: bool = typer.Option(None, "--manage-channel-availability/--no-manage-channel-availability", help="Indicates whether the agent can manage channel availability(true) or not(false)."),
    timeout_desktop_inactivity_mins: str = typer.Option(None, "--timeout-desktop-inactivity-mins", help="This setting occurs only if you enabled time out desktop inactivity feature. Specify time in minute(s)."),
    system_default: bool = typer.Option(None, "--system-default/--no-system-default", help="Indicates whether the created resource is system created or not"),
    created_time: str = typer.Option(None, "--created-time", help="This is the created time of the entity."),
    last_updated_time: str = typer.Option(None, "--last-updated-time", help="This is the updated time of the entity."),
    auto_accept_digital_interactions: bool = typer.Option(None, "--auto-accept-digital-interactions/--no-auto-accept-digital-interactions", help="Automatically accept digital interactions when agent becomes available"),
    agent_profile_dto: str = typer.Option(None, "--agent-profile-dto", hidden=True, help="Accepted and ignored: the request body is --json-body (or the body flags)."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new Desktop Profile.\n\n\b\nExample: wxcli cc-desktop-profile create --json-body '{"name":"...","parentType":"ORGANIZATION","accessWrapUpCode":"SPECIFIC","accessIdleCode":"SPECIFIC","accessQueue":"SPECIFIC","accessEntryPoint":"SPECIFIC","accessBuddyTeam":"SPECIFIC","agentDNValidation":"SPECIFIC","viewableStatistics":{"accessQueueStats":"SPECIFIC","accessTeamStats":"SPECIFIC"},"active":true}'\n\n\b\nExample --json-body: '{"name":"...","parentType":"ORGANIZATION","accessWrapUpCode":"SPECIFIC","accessIdleCode":"SPECIFIC","accessQueue":"SPECIFIC","accessEntryPoint":"SPECIFIC","accessBuddyTeam":"SPECIFIC","agentDNValidation":"SPECIFIC","viewableStatistics":{"accessQueueStats":"SPECIFIC","accessTeamStats":"SPECIFIC","organizationId":"...","id":"...","version":0,"agentStats":true,"contactServiceQueues":["..."],"loggedInTeamStats":true,"teams":["..."],"createdTime":0,"lastUpdatedTime":0},"active":true,"organizationId":"...","id":"...","version":0,"description":"...","siteId":"...","screenPopup":true,"lastAgentRouting":true,"scheduleAndManageCallBack":true,"autoWrapUp":true,"autoAnswer":true,"agentPersonalGreeting":true,"autoWrapAfterSeconds":0,"agentAvailableAfterOutdial":true,"allowAutoWrapUpExtension":true,"wrapUpCodes":["..."],"idleCodes":["..."],"queues":["..."],"entryPoints":["..."],"buddyTeams":["..."],"consultToQueue":true,"outdialEnabled":true,"outdialEntryPointId":"...","outdialANIId":"...","addressBookId":"...","dialPlanEnabled":true,"dialPlans":["..."],"agentDNValidationCriteria":"SPECIFIC","agentDNValidationCriterions":["..."],"loginVoiceOptions":["AGENT_DN"],"thresholdRules":["..."],"timeoutDesktopInactivityCustomEnabled":true,"showUserDetailsMS":true,"stateSynchronizationMS":true,"showUserDetailsWebex":true,"stateSynchronizationWebex":true,"manageChannelAvailability":true,"timeoutDesktopInactivityMins":0,"systemDefault":true,"createdTime":0,"lastUpdatedTime":0,"autoAcceptDigitalInteractions":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/agent-profile"
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
        if parent_type is not None:
            body["parentType"] = parent_type
        if site_id is not None:
            body["siteId"] = site_id
        if screen_popup is not None:
            body["screenPopup"] = screen_popup
        if last_agent_routing is not None:
            body["lastAgentRouting"] = last_agent_routing
        if schedule_and_manage_call_back is not None:
            body["scheduleAndManageCallBack"] = schedule_and_manage_call_back
        if auto_wrap_up is not None:
            body["autoWrapUp"] = auto_wrap_up
        if auto_answer is not None:
            body["autoAnswer"] = auto_answer
        if agent_personal_greeting is not None:
            body["agentPersonalGreeting"] = agent_personal_greeting
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
        if manage_channel_availability is not None:
            body["manageChannelAvailability"] = manage_channel_availability
        if timeout_desktop_inactivity_mins is not None:
            body["timeoutDesktopInactivityMins"] = timeout_desktop_inactivity_mins
        if system_default is not None:
            body["systemDefault"] = system_default
        if created_time is not None:
            body["createdTime"] = created_time
        if last_updated_time is not None:
            body["lastUpdatedTime"] = last_updated_time
        if auto_accept_digital_interactions is not None:
            body["autoAcceptDigitalInteractions"] = auto_accept_digital_interactions
        _missing = [f for f in ['name', 'parentType', 'accessWrapUpCode', 'accessIdleCode', 'accessQueue', 'accessEntryPoint', 'accessBuddyTeam', 'agentDNValidation', 'active'] if f not in body or body[f] is None]
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
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Purge inactive Desktop Profiles."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    if not force:
        typer.confirm(f"Purge Inactive Entities for {orgid}?", abort=True)
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



_BODY_SKELETON_UPDATE = '{"name":"...","parentType":"ORGANIZATION","accessWrapUpCode":"SPECIFIC","accessIdleCode":"SPECIFIC","accessQueue":"SPECIFIC","accessEntryPoint":"SPECIFIC","accessBuddyTeam":"SPECIFIC","agentDNValidation":"SPECIFIC","viewableStatistics":{"accessQueueStats":"SPECIFIC","accessTeamStats":"SPECIFIC","organizationId":"...","id":"...","version":0,"agentStats":true,"contactServiceQueues":["..."],"loggedInTeamStats":true,"teams":["..."],"createdTime":0,"lastUpdatedTime":0},"active":true,"organizationId":"...","id":"...","version":0,"description":"...","siteId":"...","screenPopup":true,"lastAgentRouting":true,"scheduleAndManageCallBack":true,"autoWrapUp":true,"autoAnswer":true,"agentPersonalGreeting":true,"autoWrapAfterSeconds":0,"agentAvailableAfterOutdial":true,"allowAutoWrapUpExtension":true,"wrapUpCodes":["..."],"idleCodes":["..."],"queues":["..."],"entryPoints":["..."],"buddyTeams":["..."],"consultToQueue":true,"outdialEnabled":true,"outdialEntryPointId":"...","outdialANIId":"...","addressBookId":"...","dialPlanEnabled":true,"dialPlans":["..."],"agentDNValidationCriteria":"SPECIFIC","agentDNValidationCriterions":["..."],"loginVoiceOptions":["AGENT_DN"],"thresholdRules":["..."],"timeoutDesktopInactivityCustomEnabled":true,"showUserDetailsMS":true,"stateSynchronizationMS":true,"showUserDetailsWebex":true,"stateSynchronizationWebex":true,"manageChannelAvailability":true,"timeoutDesktopInactivityMins":0,"systemDefault":true,"createdTime":0,"lastUpdatedTime":0,"autoAcceptDigitalInteractions":true}'

@app.command("update", short_help="Update specific Desktop Profile by ID.")
def update(
    id: str = typer.Argument(help="UUID, from: wxcli cc-desktop-profile list"),
    organization_id: str = typer.Option(None, "--organization-id", help="ID of the contact center organization. This field is required for all bulk save operations."),
    id_param: str = typer.Option(None, "--id", help="ID of this contact center resource. It should not be specified when creating a new resource. However, it is mandatory when updating a resource."),
    version: str = typer.Option(None, "--version", help="The version of this resource. For a newly created resource, it will be 0 unless specified otherwise."),
    name: str = typer.Option(None, "--name", help="Enter a name for the agent profile."),
    description: str = typer.Option(None, "--description", help="(Optional) Enter a description of the profile."),
    parent_type: str = typer.Option(None, "--parent-type", help="Choices: ORGANIZATION, SITE"),
    site_id: str = typer.Option(None, "--site-id", help="Identifier for a site which is a physical contact center location under the control of your enterprise."),
    screen_popup: bool = typer.Option(None, "--screen-popup/--no-screen-popup", help="Indicates whether to allow external pop-up screens(true) or not(false)."),
    last_agent_routing: bool = typer.Option(None, "--last-agent-routing/--no-last-agent-routing", help="This setting use only if your administrator enables the Last Agent Routing feature for your enterprise. Indicates whether to allow Last Agent Routing check box on the Agent Desktop during wrap-up(true) or not(false)."),
    schedule_and_manage_call_back: bool = typer.Option(None, "--schedule-and-manage-call-back/--no-schedule-and-manage-call-back", help="Indicates whether to allow agents to schedule and manage callbacks(true) or not(false)."),
    auto_wrap_up: bool = typer.Option(None, "--auto-wrap-up/--no-auto-wrap-up", help="Indicates whether to allow auto wrap-up(true) or not(false)."),
    auto_answer: bool = typer.Option(None, "--auto-answer/--no-auto-answer", help="Indicates whether incoming calls on the Agent Desktop need to be answered automatically(true) or not(false)."),
    agent_personal_greeting: bool = typer.Option(None, "--agent-personal-greeting/--no-agent-personal-greeting", help="Indicates whether an agent can record a personal greeting(true) or not(false) from the agent desktop."),
    auto_wrap_after_seconds: str = typer.Option(None, "--auto-wrap-after-seconds", help="This setting allows auto wrap-up after seconds"),
    agent_available_after_outdial: bool = typer.Option(None, "--agent-available-after-outdial/--no-agent-available-after-outdial", help="Enabled if you want the agent to go into the Available state after completing and wrapping up an outdial call. The agent can also manually select an Idle state from the STATUS NOW drop-down list before selecting a wrap-up code."),
    allow_auto_wrap_up_extension: bool = typer.Option(None, "--allow-auto-wrap-up-extension/--no-allow-auto-wrap-up-extension", help="Indicates whether to allow auto wrap-up extension(true) or not(false)."),
    access_wrap_up_code: str = typer.Option(None, "--access-wrap-up-code", help="Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    access_idle_code: str = typer.Option(None, "--access-idle-code", help="Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    access_queue: str = typer.Option(None, "--access-queue", help="Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    access_entry_point: str = typer.Option(None, "--access-entry-point", help="Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    access_buddy_team: str = typer.Option(None, "--access-buddy-team", help="Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    consult_to_queue: bool = typer.Option(None, "--consult-to-queue/--no-consult-to-queue", help="Indicates whether you want the agent to be able to select a queue in the Queue drop-down list as a target for a consultation or not."),
    outdial_enabled: bool = typer.Option(None, "--outdial-enabled/--no-outdial-enabled", help="Indicates whether you want the agent to be able to make outdial calls(true) or not(false)."),
    outdial_entry_point_id: str = typer.Option(None, "--outdial-entry-point-id", help="If you enabled Outdial, specify the entry point id that the agent can use to make outdial calls."),
    outdial_ani_id: str = typer.Option(None, "--outdial-ani-id", help="This setting occurs only if you enabled Outdial. Specify the Outdial ANI id that the agent can use to make outdial calls."),
    address_book_id: str = typer.Option(None, "--address-book-id", help="Specify the address book id that includes the speed-dial numbers that the agent can select to make outdial and consult calls."),
    dial_plan_enabled: bool = typer.Option(None, "--dial-plan-enabled/--no-dial-plan-enabled", help="Indicates whether you want the agent to be able to make ad-hoc outdial calls(true) or not(false)."),
    agent_dn_validation: str = typer.Option(None, "--agent-dn-validation", help="Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    agent_dn_validation_criteria: str = typer.Option(None, "--agent-dn-validation-criteria", help="Choices: SPECIFIC, ALL, PROVISIONED_VALUE, NONE"),
    active: bool = typer.Option(None, "--active/--no-active", help="Specify whether the agent profile is active or not Active."),
    timeout_desktop_inactivity_custom_enabled: bool = typer.Option(None, "--timeout-desktop-inactivity-custom-enabled/--no-timeout-desktop-inactivity-custom-enabled", help="This setting enabled time out desktop inactivity feature."),
    show_user_details_ms: bool = typer.Option(None, "--show-user-details-ms/--no-show-user-details-ms", help="Specify whether the show user details of microsoft account user enabled or not"),
    state_synchronization_ms: bool = typer.Option(None, "--state-synchronization-ms/--no-state-synchronization-ms", help="Specify whether the state synchronization of microsoft account user enabled or not"),
    show_user_details_webex: bool = typer.Option(None, "--show-user-details-webex/--no-show-user-details-webex", help="Specify whether the show user details of webex account user enabled or not"),
    state_synchronization_webex: bool = typer.Option(None, "--state-synchronization-webex/--no-state-synchronization-webex", help="Specify whether the state synchronization of webex account user enabled or not"),
    manage_channel_availability: bool = typer.Option(None, "--manage-channel-availability/--no-manage-channel-availability", help="Indicates whether the agent can manage channel availability(true) or not(false)."),
    timeout_desktop_inactivity_mins: str = typer.Option(None, "--timeout-desktop-inactivity-mins", help="This setting occurs only if you enabled time out desktop inactivity feature. Specify time in minute(s)."),
    system_default: bool = typer.Option(None, "--system-default/--no-system-default", help="Indicates whether the created resource is system created or not"),
    created_time: str = typer.Option(None, "--created-time", help="This is the created time of the entity."),
    last_updated_time: str = typer.Option(None, "--last-updated-time", help="This is the updated time of the entity."),
    auto_accept_digital_interactions: bool = typer.Option(None, "--auto-accept-digital-interactions/--no-auto-accept-digital-interactions", help="Automatically accept digital interactions when agent becomes available"),
    agent_profile_dto: str = typer.Option(None, "--agent-profile-dto", hidden=True, help="Accepted and ignored: the request body is --json-body (or the body flags)."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update specific Desktop Profile by ID.\n\n\b\nExample: wxcli cc-desktop-profile update ID --json-body '{"name":"...","parentType":"ORGANIZATION","accessWrapUpCode":"SPECIFIC","accessIdleCode":"SPECIFIC","accessQueue":"SPECIFIC","accessEntryPoint":"SPECIFIC","accessBuddyTeam":"SPECIFIC","agentDNValidation":"SPECIFIC","viewableStatistics":{"accessQueueStats":"SPECIFIC","accessTeamStats":"SPECIFIC"},"active":true}'\n\n\b\nExample --json-body: '{"name":"...","parentType":"ORGANIZATION","accessWrapUpCode":"SPECIFIC","accessIdleCode":"SPECIFIC","accessQueue":"SPECIFIC","accessEntryPoint":"SPECIFIC","accessBuddyTeam":"SPECIFIC","agentDNValidation":"SPECIFIC","viewableStatistics":{"accessQueueStats":"SPECIFIC","accessTeamStats":"SPECIFIC","organizationId":"...","id":"...","version":0,"agentStats":true,"contactServiceQueues":["..."],"loggedInTeamStats":true,"teams":["..."],"createdTime":0,"lastUpdatedTime":0},"active":true,"organizationId":"...","id":"...","version":0,"description":"...","siteId":"...","screenPopup":true,"lastAgentRouting":true,"scheduleAndManageCallBack":true,"autoWrapUp":true,"autoAnswer":true,"agentPersonalGreeting":true,"autoWrapAfterSeconds":0,"agentAvailableAfterOutdial":true,"allowAutoWrapUpExtension":true,"wrapUpCodes":["..."],"idleCodes":["..."],"queues":["..."],"entryPoints":["..."],"buddyTeams":["..."],"consultToQueue":true,"outdialEnabled":true,"outdialEntryPointId":"...","outdialANIId":"...","addressBookId":"...","dialPlanEnabled":true,"dialPlans":["..."],"agentDNValidationCriteria":"SPECIFIC","agentDNValidationCriterions":["..."],"loginVoiceOptions":["AGENT_DN"],"thresholdRules":["..."],"timeoutDesktopInactivityCustomEnabled":true,"showUserDetailsMS":true,"stateSynchronizationMS":true,"showUserDetailsWebex":true,"stateSynchronizationWebex":true,"manageChannelAvailability":true,"timeoutDesktopInactivityMins":0,"systemDefault":true,"createdTime":0,"lastUpdatedTime":0,"autoAcceptDigitalInteractions":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/agent-profile/{id}"
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
        if parent_type is not None:
            body["parentType"] = parent_type
        if site_id is not None:
            body["siteId"] = site_id
        if screen_popup is not None:
            body["screenPopup"] = screen_popup
        if last_agent_routing is not None:
            body["lastAgentRouting"] = last_agent_routing
        if schedule_and_manage_call_back is not None:
            body["scheduleAndManageCallBack"] = schedule_and_manage_call_back
        if auto_wrap_up is not None:
            body["autoWrapUp"] = auto_wrap_up
        if auto_answer is not None:
            body["autoAnswer"] = auto_answer
        if agent_personal_greeting is not None:
            body["agentPersonalGreeting"] = agent_personal_greeting
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
        if manage_channel_availability is not None:
            body["manageChannelAvailability"] = manage_channel_availability
        if timeout_desktop_inactivity_mins is not None:
            body["timeoutDesktopInactivityMins"] = timeout_desktop_inactivity_mins
        if system_default is not None:
            body["systemDefault"] = system_default
        if created_time is not None:
            body["createdTime"] = created_time
        if last_updated_time is not None:
            body["lastUpdatedTime"] = last_updated_time
        if auto_accept_digital_interactions is not None:
            body["autoAcceptDigitalInteractions"] = auto_accept_digital_interactions
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
    limit: int = typer.Option(0, "--limit", help="Max results, sent as the page size (pageSize); 0 = the server default page. Ignored with --all."),
    offset: int = typer.Option(0, "--offset", help="Skip this many records (translated to the page number; record-exact)."),
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
    if limit > 0 and not all_pages and params.get("pageSize") is None:
        params["pageSize"] = limit
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_page_param(url=url, params=params, item_key="data"))
        elif offset > 0:
            result = api.session.fetch_from_offset(url=url, params=params, offset=offset, count=limit, item_key="data")
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("data", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
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
    limit: int = typer.Option(0, "--limit", help="Max results, sent as the page size (pageSize); 0 = the server default page. Ignored with --all."),
    offset: int = typer.Option(0, "--offset", help="Skip this many records (translated to the page number; record-exact)."),
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
    if limit > 0 and not all_pages and params.get("pageSize") is None:
        params["pageSize"] = limit
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_page_param(url=url, params=params, item_key="data"))
        elif offset > 0:
            result = api.session.fetch_from_offset(url=url, params=params, offset=offset, count=limit, item_key="data")
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("data", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)


