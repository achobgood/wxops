import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id
from wxcli.common import verify_write


app = typer.Typer(help="Manage Webex Calling call-queue.")


@app.command("list", short_help="Read the List of Call Queues with Customer Assist.")
def cmd_list(
    location_id: str = typer.Option(None, "--location-id", help="Returns the list of call queues in this location."),
    name: str = typer.Option(None, "--name", help="Returns only the call queues matching the given name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Returns only the call queues matching the given primary phone number or extension."),
    department_id: str = typer.Option(None, "--department-id", help="Returns only call queues matching the given department ID."),
    department_name: str = typer.Option(None, "--department-name", help="Returns only call queues matching the given department name."),
    has_cx_essentials: str = typer.Option(None, "--has-cx-essentials", help="Returns only the list of call queues with Customer Assist license when `true`, otherwise returns the list of Customer Experience Basic call queues."),
    digital_inbox_enabled: str = typer.Option(None, "--digital-inbox-enabled", help="Returns only the list of call queues with digital inbox enabled when `true`, or disabled when `false`. This query parameter is only valid when `hasCxEssentials` is `true`."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Call Queues with Customer Assist."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/queues"
    params = {}
    if location_id is not None:
        params["locationId"] = location_id
    if name is not None:
        params["name"] = name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if department_id is not None:
        params["departmentId"] = department_id
    if department_name is not None:
        params["departmentName"] = department_name
    if has_cx_essentials is not None:
        params["hasCxEssentials"] = has_cx_essentials
    if digital_inbox_enabled is not None:
        params["digitalInboxEnabled"] = digital_inbox_enabled
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        if limit > 0 and not all_pages:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("queues", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="queues"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Enabled', 'enabled')], limit=limit)



@app.command("show-org-settings", short_help="Get Call Queue Settings.")
def show_org_settings(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Queue Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/queues/settings"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_ORG_SETTINGS = '{"maintainQueuePositionForSimRingEnabled":true,"forceAgentUnavailableOnBouncedEnabled":true,"playToneToAgentForBargeInEnabled":true,"playToneToAgentForSilentMonitoringEnabled":true,"playToneToAgentForSupervisorCoachingEnabled":true}'

@app.command("update-org-settings", short_help="Update Call Queue Settings.")
def update_org_settings(
    maintain_queue_position_for_sim_ring_enabled: bool = typer.Option(None, "--maintain-queue-position-for-sim-ring-enabled/--no-maintain-queue-position-for-sim-ring-enabled", help="Indicates whether callers keep their queue position when simultaneous ringing routes a call to multiple agents."),
    force_agent_unavailable_on_bounced_enabled: bool = typer.Option(None, "--force-agent-unavailable-on-bounced-enabled/--no-force-agent-unavailable-on-bounced-enabled", help="Indicates whether Customer Assist agents are changed to unavailable after bounced calls."),
    play_tone_to_agent_for_barge_in_enabled: bool = typer.Option(None, "--play-tone-to-agent-for-barge-in-enabled/--no-play-tone-to-agent-for-barge-in-enabled", help="Organization-wide default that plays a tone to agents when a supervisor joins an active call using barge in."),
    play_tone_to_agent_for_silent_monitoring_enabled: bool = typer.Option(None, "--play-tone-to-agent-for-silent-monitoring-enabled/--no-play-tone-to-agent-for-silent-monitoring-enabled", help="Organization-wide default that plays a tone to agents when a supervisor monitors their active call without joining."),
    play_tone_to_agent_for_supervisor_coaching_enabled: bool = typer.Option(None, "--play-tone-to-agent-for-supervisor-coaching-enabled/--no-play-tone-to-agent-for-supervisor-coaching-enabled", help="Organization-wide default that plays a tone to agents when a supervisor coaches an agent during an active call."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Call Queue Settings.\n\n\b\nExample --json-body: '{"maintainQueuePositionForSimRingEnabled":true,"forceAgentUnavailableOnBouncedEnabled":true,"playToneToAgentForBargeInEnabled":true,"playToneToAgentForSilentMonitoringEnabled":true,"playToneToAgentForSupervisorCoachingEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_ORG_SETTINGS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/queues/settings"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if maintain_queue_position_for_sim_ring_enabled is not None:
            body["maintainQueuePositionForSimRingEnabled"] = maintain_queue_position_for_sim_ring_enabled
        if force_agent_unavailable_on_bounced_enabled is not None:
            body["forceAgentUnavailableOnBouncedEnabled"] = force_agent_unavailable_on_bounced_enabled
        if play_tone_to_agent_for_barge_in_enabled is not None:
            body["playToneToAgentForBargeInEnabled"] = play_tone_to_agent_for_barge_in_enabled
        if play_tone_to_agent_for_silent_monitoring_enabled is not None:
            body["playToneToAgentForSilentMonitoringEnabled"] = play_tone_to_agent_for_silent_monitoring_enabled
        if play_tone_to_agent_for_supervisor_coaching_enabled is not None:
            body["playToneToAgentForSupervisorCoachingEnabled"] = play_tone_to_agent_for_supervisor_coaching_enabled
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
        emit({"status": "updated"}, output=output, fields=fields)



_BODY_SKELETON_CREATE = '{"name":"...","callPolicies":{"routingType":"PRIORITY_BASED","policy":"CIRCULAR","callBounce":{"callBounceEnabled":true,"callBounceMaxRings":0,"agentUnavailableEnabled":true,"alertAgentEnabled":true,"alertAgentMaxSeconds":0,"callBounceOnHoldEnabled":true,"callBounceOnHoldMaxSeconds":0},"distinctiveRing":{"enabled":true,"ringPattern":"NORMAL"}},"queueSettings":{"queueSize":0,"overflow":{"action":"PERFORM_BUSY_TREATMENT","greeting":"CUSTOM","sendToVoicemail":true,"transferNumber":"...","overflowAfterWaitEnabled":true,"overflowAfterWaitTime":0,"playOverflowGreetingEnabled":true,"audioAnnouncementFiles":[{"id":"...","name":"...","mediaFileType":"...","level":"LOCATION"}]},"callOfferToneEnabled":true,"resetCallStatisticsEnabled":true,"welcomeMessage":{"greeting":"CUSTOM","enabled":true,"alwaysEnabled":true,"audioAnnouncementFiles":[{"id":"...","name":"...","mediaFileType":"...","level":"LOCATION"}]},"waitMessage":{"waitMode":"TIME","enabled":true,"handlingTime":0,"defaultHandlingTime":0,"queuePosition":0,"highVolumeMessageEnabled":true,"estimatedWaitingTime":0,"callbackOptionEnabled":true,"minimumEstimatedCallbackTime":0,"internationalCallbackEnabled":true,"playUpdatedEstimatedWaitMessage":true},"comfortMessage":{"greeting":"CUSTOM","enabled":true,"timeBetweenMessages":0,"audioAnnouncementFiles":[{"id":"...","name":"...","mediaFileType":"...","level":"LOCATION"}]},"comfortMessageBypass":{"greeting":"CUSTOM","enabled":true,"callWaitingAgeThreshold":0,"audioAnnouncementFiles":[{"id":"...","name":"...","mediaFileType":"...","level":"LOCATION"}]},"mohMessage":{"normalSource":{"greeting":"CUSTOM","enabled":true,"audioAnnouncementFiles":[{"id":"...","name":"...","mediaFileType":"...","level":"LOCATION"}],"audioPlaylistId":"..."},"alternateSource":{"greeting":"CUSTOM","enabled":true,"audioAnnouncementFiles":[{"id":"...","name":"...","mediaFileType":"...","level":"LOCATION"}],"audioPlaylistId":"..."}},"whisperMessage":{"greeting":"CUSTOM","enabled":true,"audioAnnouncementFiles":[{"id":"...","name":"...","mediaFileType":"...","level":"LOCATION"}]},"useEnterprisePlayToneToAgentSettingsEnabled":true,"playToneToAgentForBargeInEnabled":true,"playToneToAgentForSilentMonitoringEnabled":true,"playToneToAgentForSupervisorCoachingEnabled":true},"agents":[{"id":"...","weight":"...","skillLevel":0}],"phoneNumber":"...","extension":"...","languageCode":"...","firstName":"...","lastName":"...","timeZone":"...","callingLineIdPolicy":"DIRECT_LINE","callingLineIdPhoneNumber":"...","allowAgentJoinEnabled":true,"phoneNumberForOutgoingCallsEnabled":true,"directLineCallerIdName":{"selection":"CUSTOM_NAME","customName":"..."},"dialByName":"...","digitalInboxEnabled":true}'

@app.command("create", short_help="Create a Call Queue with Customer Assist.")
def create(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    has_cx_essentials: str = typer.Option(None, "--has-cx-essentials", help="Creates a Customer Assist call queue, when `true`. This requires Customer Assist licensed agents."),
    name: str = typer.Option(None, "--name", help="(required) Unique name for the call queue."),
    phone_number: str = typer.Option(None, "--phone-number", help="Primary phone number of the call queue. Either a `phoneNumber` or `extension` is mandatory."),
    extension: str = typer.Option(None, "--extension", help="Primary phone extension of the call queue. Either a `phoneNumber` or extension is mandatory."),
    language_code: str = typer.Option(None, "--language-code", help="Language code."),
    first_name: str = typer.Option(None, "--first-name", help="First name to be shown when calls are forwarded out of this call queue. Defaults to \".\". This field has been deprecated. Please use `directLineCallerIdName` and `dialByName` instead."),
    last_name: str = typer.Option(None, "--last-name", help="Last name to be shown when calls are forwarded out of this call queue. Defaults to `phoneNumber` if set, otherwise defaults to call group name. This field has been deprecated. Please use `directLineCallerIdName` and `dialByName` instead."),
    time_zone: str = typer.Option(None, "--time-zone", help="Time zone for the call queue."),
    calling_line_id_policy: str = typer.Option(None, "--calling-line-id-policy", help="Choices: DIRECT_LINE, LOCATION_NUMBER, CUSTOM"),
    calling_line_id_phone_number: str = typer.Option(None, "--calling-line-id-phone-number", help="Calling line ID Phone number which will be shown if CUSTOM is selected."),
    allow_agent_join_enabled: bool = typer.Option(None, "--allow-agent-join-enabled/--no-allow-agent-join-enabled", help="Whether or not to allow agents to join or unjoin a queue."),
    phone_number_for_outgoing_calls_enabled: bool = typer.Option(None, "--phone-number-for-outgoing-calls-enabled/--no-phone-number-for-outgoing-calls-enabled", help="When `true`, indicates that the agent's configuration allows them to use the queue's Caller ID for outgoing calls."),
    dial_by_name: str = typer.Option(None, "--dial-by-name", help="The name to be used for dial by name functions. Characters of `%`, `+`, `\\`, `\"` and Unicode characters are not allowed."),
    digital_inbox_enabled: bool = typer.Option(None, "--digital-inbox-enabled/--no-digital-inbox-enabled", help="Digital Inbox enabled for Queue. This field is applicable for queue which has `hasCxEssentials=true`."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Call Queue with Customer Assist.\n\n\b\nExample: wxcli call-queue create LOCATION_ID --json-body '{"name":"...","callPolicies":{"routingType":"PRIORITY_BASED","policy":"CIRCULAR","callBounce":{"callBounceEnabled":true,"callBounceMaxRings":0,"agentUnavailableEnabled":true,"alertAgentEnabled":true,"alertAgentMaxSeconds":0,"callBounceOnHoldEnabled":true,"callBounceOnHoldMaxSeconds":0},"distinctiveRing":{"enabled":true}},"queueSettings":{"queueSize":0,"overflow":{"action":"PERFORM_BUSY_TREATMENT","greeting":"CUSTOM"}},"agents":[{"id":"..."}]}'\n\n\b\nExample --json-body: '{"name":"...","callPolicies":{"routingType":"PRIORITY_BASED","policy":"CIRCULAR","callBounce":{"callBounceEnabled":true,"callBounceMaxRings":0,"agentUnavailableEnabled":true,"alertAgentEnabled":true,"alertAgentMaxSeconds":0,"callBounceOnHoldEnabled":true,"callBounceOnHoldMaxSeconds":0},"distinctiveRing":{"enabled":true,"ringPattern":"NORMAL"}},"queueSettings":{"queueSize":0,"overflow":{"action":"PERFORM_BUSY_TREATMENT","greeting":"CUSTOM","sendToVoicemail":true,"transferNumber":"...","overflowAfterWaitEnabled":true,"overflowAfterWaitTime":0,"playOverflowGreetingEnabled":true,"audioAnnouncementFiles":[{"id":"...","name":"...","mediaFileType":"...","level":"LOCATION"}]},"callOfferToneEnabled":true,"resetCallStatisticsEnabled":true,"welcomeMessage":{"greeting":"CUSTOM","enabled":true,"alwaysEnabled":true,"audioAnnouncementFiles":[{"id":"...","name":"...","mediaFileType":"...","level":"LOCATION"}]},"waitMessage":{"waitMode":"TIME","enabled":true,"handlingTime":0,"defaultHandlingTime":0,"queuePosition":0,"highVolumeMessageEnabled":true,"estimatedWaitingTime":0,"callbackOptionEnabled":true,"minimumEstimatedCallbackTime":0,"internationalCallbackEnabled":true,"playUpdatedEstimatedWaitMessage":true},"comfortMessage":{"greeting":"CUSTOM","enabled":true,"timeBetweenMessages":0,"audioAnnouncementFiles":[{"id":"...","name":"...","mediaFileType":"...","level":"LOCATION"}]},"comfortMessageBypass":{"greeting":"CUSTOM","enabled":true,"callWaitingAgeThreshold":0,"audioAnnouncementFiles":[{"id":"...","name":"...","mediaFileType":"...","level":"LOCATION"}]},"mohMessage":{"normalSource":{"greeting":"CUSTOM","enabled":true,"audioAnnouncementFiles":[{"id":"...","name":"...","mediaFileType":"...","level":"LOCATION"}],"audioPlaylistId":"..."},"alternateSource":{"greeting":"CUSTOM","enabled":true,"audioAnnouncementFiles":[{"id":"...","name":"...","mediaFileType":"...","level":"LOCATION"}],"audioPlaylistId":"..."}},"whisperMessage":{"greeting":"CUSTOM","enabled":true,"audioAnnouncementFiles":[{"id":"...","name":"...","mediaFileType":"...","level":"LOCATION"}]},"useEnterprisePlayToneToAgentSettingsEnabled":true,"playToneToAgentForBargeInEnabled":true,"playToneToAgentForSilentMonitoringEnabled":true,"playToneToAgentForSupervisorCoachingEnabled":true},"agents":[{"id":"...","weight":"...","skillLevel":0}],"phoneNumber":"...","extension":"...","languageCode":"...","firstName":"...","lastName":"...","timeZone":"...","callingLineIdPolicy":"DIRECT_LINE","callingLineIdPhoneNumber":"...","allowAgentJoinEnabled":true,"phoneNumberForOutgoingCallsEnabled":true,"directLineCallerIdName":{"selection":"CUSTOM_NAME","customName":"..."},"dialByName":"...","digitalInboxEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues"
    params = {}
    if has_cx_essentials is not None:
        params["hasCxEssentials"] = has_cx_essentials
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if phone_number is not None:
            body["phoneNumber"] = phone_number
        if extension is not None:
            body["extension"] = extension
        if language_code is not None:
            body["languageCode"] = language_code
        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
        if time_zone is not None:
            body["timeZone"] = time_zone
        if calling_line_id_policy is not None:
            body["callingLineIdPolicy"] = calling_line_id_policy
        if calling_line_id_phone_number is not None:
            body["callingLineIdPhoneNumber"] = calling_line_id_phone_number
        if allow_agent_join_enabled is not None:
            body["allowAgentJoinEnabled"] = allow_agent_join_enabled
        if phone_number_for_outgoing_calls_enabled is not None:
            body["phoneNumberForOutgoingCallsEnabled"] = phone_number_for_outgoing_calls_enabled
        if dial_by_name is not None:
            body["dialByName"] = dial_by_name
        if digital_inbox_enabled is not None:
            body["digitalInboxEnabled"] = digital_inbox_enabled
        _missing = [f for f in ['name'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
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



@app.command("show-queues", hidden=True)
@app.command("show", short_help="Get Details for a Call Queue with Customer Assist.")
def show(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    queue_id: str = typer.Argument(help="Webex CALL_QUEUE id, from: wxcli call-queue list"),
    has_cx_essentials: str = typer.Option(None, "--has-cx-essentials", help="Must be set to `true`, to view the details of a call queue with Customer Assist license. This can otherwise be ommited or set to `false`."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Call Queue with Customer Assist.\n\n\b\nExample: wxcli call-queue show LOCATION_ID QUEUE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}"
    params = {}
    if has_cx_essentials is not None:
        params["hasCxEssentials"] = has_cx_essentials
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"queueSettings":{"queueSize":0,"overflow":{"action":"PERFORM_BUSY_TREATMENT","greeting":"CUSTOM","sendToVoicemail":true,"transferNumber":"...","overflowAfterWaitEnabled":true,"overflowAfterWaitTime":0,"playOverflowGreetingEnabled":true,"audioAnnouncementFiles":[{"id":"...","name":"...","mediaFileType":"...","level":"LOCATION"}]},"callOfferToneEnabled":true,"resetCallStatisticsEnabled":true,"welcomeMessage":{"greeting":"CUSTOM","enabled":true,"alwaysEnabled":true,"audioAnnouncementFiles":[{"id":"...","name":"...","mediaFileType":"...","level":"LOCATION"}]},"waitMessage":{"waitMode":"TIME","enabled":true,"handlingTime":0,"defaultHandlingTime":0,"queuePosition":0,"highVolumeMessageEnabled":true,"estimatedWaitingTime":0,"callbackOptionEnabled":true,"minimumEstimatedCallbackTime":0,"internationalCallbackEnabled":true,"playUpdatedEstimatedWaitMessage":true},"comfortMessage":{"greeting":"CUSTOM","enabled":true,"timeBetweenMessages":0,"audioAnnouncementFiles":[{"id":"...","name":"...","mediaFileType":"...","level":"LOCATION"}]},"comfortMessageBypass":{"greeting":"CUSTOM","enabled":true,"callWaitingAgeThreshold":0,"audioAnnouncementFiles":[{"id":"...","name":"...","mediaFileType":"...","level":"LOCATION"}]},"mohMessage":{"normalSource":{"greeting":"CUSTOM","enabled":true,"audioAnnouncementFiles":[{"id":"...","name":"...","mediaFileType":"...","level":"LOCATION"}],"audioPlaylistId":"..."},"alternateSource":{"greeting":"CUSTOM","enabled":true,"audioAnnouncementFiles":[{"id":"...","name":"...","mediaFileType":"...","level":"LOCATION"}],"audioPlaylistId":"..."}},"whisperMessage":{"greeting":"CUSTOM","enabled":true,"audioAnnouncementFiles":[{"id":"...","name":"...","mediaFileType":"...","level":"LOCATION"}]},"useEnterprisePlayToneToAgentSettingsEnabled":true,"playToneToAgentForBargeInEnabled":true,"playToneToAgentForSilentMonitoringEnabled":true,"playToneToAgentForSupervisorCoachingEnabled":true},"enabled":true,"name":"...","languageCode":"...","firstName":"...","lastName":"...","timeZone":"...","phoneNumber":"...","extension":"...","alternateNumberSettings":{"distinctiveRingEnabled":true,"alternateNumbers":[{"phoneNumber":"...","ringPattern":"NORMAL"}]},"callPolicies":{"routingType":"PRIORITY_BASED","policy":"CIRCULAR","callBounce":{"callBounceEnabled":true,"callBounceMaxRings":0,"agentUnavailableEnabled":true,"alertAgentEnabled":true,"alertAgentMaxSeconds":0,"callBounceOnHoldEnabled":true,"callBounceOnHoldMaxSeconds":0},"distinctiveRing":{"enabled":true,"ringPattern":"NORMAL"}},"callingLineIdPolicy":"DIRECT_LINE","callingLineIdPhoneNumber":"...","allowCallWaitingForAgentsEnabled":true,"agents":[{"id":"...","weight":"...","skillLevel":0,"joinEnabled":true}],"allowAgentJoinEnabled":true,"phoneNumberForOutgoingCallsEnabled":true,"directLineCallerIdName":{"selection":"CUSTOM_NAME","customName":"..."},"dialByName":"...","digitalInboxEnabled":true}'

@app.command("update-queues", hidden=True)
@app.command("update", short_help="Update a Call Queue.")
def update(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    queue_id: str = typer.Argument(help="Webex CALL_QUEUE id, from: wxcli call-queue list"),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Whether or not the call queue is enabled."),
    name: str = typer.Option(None, "--name", help="Unique name for the call queue."),
    language_code: str = typer.Option(None, "--language-code", help="Language code."),
    first_name: str = typer.Option(None, "--first-name", help="First name to be shown when calls are forwarded out of this call queue. Defaults to `.`. This field has been deprecated. Please use `directLineCallerIdName` and `dialByName` instead."),
    last_name: str = typer.Option(None, "--last-name", help="Last name to be shown when calls are forwarded out of this call queue. Defaults to the `phoneNumber` if set, otherwise defaults to call group name. This field has been deprecated. Please use `directLineCallerIdName` and `dialByName` instead."),
    time_zone: str = typer.Option(None, "--time-zone", help="Time zone for the hunt group."),
    phone_number: str = typer.Option(None, "--phone-number", help="Primary phone number of the call queue."),
    extension: str = typer.Option(None, "--extension", help="Extension of the call queue."),
    calling_line_id_policy: str = typer.Option(None, "--calling-line-id-policy", help="Choices: DIRECT_LINE, LOCATION_NUMBER, CUSTOM"),
    calling_line_id_phone_number: str = typer.Option(None, "--calling-line-id-phone-number", help="Calling line ID Phone number which will be shown if CUSTOM is selected."),
    allow_call_waiting_for_agents_enabled: bool = typer.Option(None, "--allow-call-waiting-for-agents-enabled/--no-allow-call-waiting-for-agents-enabled", help="Flag to indicate whether call waiting is enabled for agents."),
    allow_agent_join_enabled: bool = typer.Option(None, "--allow-agent-join-enabled/--no-allow-agent-join-enabled", help="Whether or not to allow agents to join or unjoin a queue."),
    phone_number_for_outgoing_calls_enabled: bool = typer.Option(None, "--phone-number-for-outgoing-calls-enabled/--no-phone-number-for-outgoing-calls-enabled", help="When `true`, indicates that the agent's configuration allows them to use the queue's Caller ID for outgoing calls."),
    dial_by_name: str = typer.Option(None, "--dial-by-name", help="Sets or clears the name to be used for dial by name functions. To clear the `dialByName`, the attribute must be set to null or empty string. Characters of `%`, `+`, `\\`, `\"` and Unicode characters are not allowed."),
    digital_inbox_enabled: bool = typer.Option(None, "--digital-inbox-enabled/--no-digital-inbox-enabled", help="Digital Inbox enabled for Queue. This field is applicable for queue which has `hasCxEssentials=true`."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Call Queue.\n\n\b\nExample: wxcli call-queue update LOCATION_ID QUEUE_ID --json-body '{"queueSettings":{"queueSize":0,"overflow":{"action":"PERFORM_BUSY_TREATMENT","greeting":"CUSTOM"}}}'\n\n\b\nExample --json-body: '{"queueSettings":{"queueSize":0,"overflow":{"action":"PERFORM_BUSY_TREATMENT","greeting":"CUSTOM","sendToVoicemail":true,"transferNumber":"...","overflowAfterWaitEnabled":true,"overflowAfterWaitTime":0,"playOverflowGreetingEnabled":true,"audioAnnouncementFiles":[{"id":"...","name":"...","mediaFileType":"...","level":"LOCATION"}]},"callOfferToneEnabled":true,"resetCallStatisticsEnabled":true,"welcomeMessage":{"greeting":"CUSTOM","enabled":true,"alwaysEnabled":true,"audioAnnouncementFiles":[{"id":"...","name":"...","mediaFileType":"...","level":"LOCATION"}]},"waitMessage":{"waitMode":"TIME","enabled":true,"handlingTime":0,"defaultHandlingTime":0,"queuePosition":0,"highVolumeMessageEnabled":true,"estimatedWaitingTime":0,"callbackOptionEnabled":true,"minimumEstimatedCallbackTime":0,"internationalCallbackEnabled":true,"playUpdatedEstimatedWaitMessage":true},"comfortMessage":{"greeting":"CUSTOM","enabled":true,"timeBetweenMessages":0,"audioAnnouncementFiles":[{"id":"...","name":"...","mediaFileType":"...","level":"LOCATION"}]},"comfortMessageBypass":{"greeting":"CUSTOM","enabled":true,"callWaitingAgeThreshold":0,"audioAnnouncementFiles":[{"id":"...","name":"...","mediaFileType":"...","level":"LOCATION"}]},"mohMessage":{"normalSource":{"greeting":"CUSTOM","enabled":true,"audioAnnouncementFiles":[{"id":"...","name":"...","mediaFileType":"...","level":"LOCATION"}],"audioPlaylistId":"..."},"alternateSource":{"greeting":"CUSTOM","enabled":true,"audioAnnouncementFiles":[{"id":"...","name":"...","mediaFileType":"...","level":"LOCATION"}],"audioPlaylistId":"..."}},"whisperMessage":{"greeting":"CUSTOM","enabled":true,"audioAnnouncementFiles":[{"id":"...","name":"...","mediaFileType":"...","level":"LOCATION"}]},"useEnterprisePlayToneToAgentSettingsEnabled":true,"playToneToAgentForBargeInEnabled":true,"playToneToAgentForSilentMonitoringEnabled":true,"playToneToAgentForSupervisorCoachingEnabled":true},"enabled":true,"name":"...","languageCode":"...","firstName":"...","lastName":"...","timeZone":"...","phoneNumber":"...","extension":"...","alternateNumberSettings":{"distinctiveRingEnabled":true,"alternateNumbers":[{"phoneNumber":"...","ringPattern":"NORMAL"}]},"callPolicies":{"routingType":"PRIORITY_BASED","policy":"CIRCULAR","callBounce":{"callBounceEnabled":true,"callBounceMaxRings":0,"agentUnavailableEnabled":true,"alertAgentEnabled":true,"alertAgentMaxSeconds":0,"callBounceOnHoldEnabled":true,"callBounceOnHoldMaxSeconds":0},"distinctiveRing":{"enabled":true,"ringPattern":"NORMAL"}},"callingLineIdPolicy":"DIRECT_LINE","callingLineIdPhoneNumber":"...","allowCallWaitingForAgentsEnabled":true,"agents":[{"id":"...","weight":"...","skillLevel":0,"joinEnabled":true}],"allowAgentJoinEnabled":true,"phoneNumberForOutgoingCallsEnabled":true,"directLineCallerIdName":{"selection":"CUSTOM_NAME","customName":"..."},"dialByName":"...","digitalInboxEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
        if name is not None:
            body["name"] = name
        if language_code is not None:
            body["languageCode"] = language_code
        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
        if time_zone is not None:
            body["timeZone"] = time_zone
        if phone_number is not None:
            body["phoneNumber"] = phone_number
        if extension is not None:
            body["extension"] = extension
        if calling_line_id_policy is not None:
            body["callingLineIdPolicy"] = calling_line_id_policy
        if calling_line_id_phone_number is not None:
            body["callingLineIdPhoneNumber"] = calling_line_id_phone_number
        if allow_call_waiting_for_agents_enabled is not None:
            body["allowCallWaitingForAgentsEnabled"] = allow_call_waiting_for_agents_enabled
        if allow_agent_join_enabled is not None:
            body["allowAgentJoinEnabled"] = allow_agent_join_enabled
        if phone_number_for_outgoing_calls_enabled is not None:
            body["phoneNumberForOutgoingCallsEnabled"] = phone_number_for_outgoing_calls_enabled
        if dial_by_name is not None:
            body["dialByName"] = dial_by_name
        if digital_inbox_enabled is not None:
            body["digitalInboxEnabled"] = digital_inbox_enabled
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
        emit({"status": "updated", "id": queue_id}, output=output, fields=fields)



@app.command("delete", short_help="Delete a Call Queue.")
def delete(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    queue_id: str = typer.Argument(help="Webex CALL_QUEUE id, from: wxcli call-queue list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Call Queue.\n\n\b\nExample: wxcli call-queue delete LOCATION_ID QUEUE_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {queue_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {queue_id}")
    else:
        emit({"status": "deleted", "id": queue_id}, output=output, fields=fields)



@app.command("list-announcements", short_help="Read the List of Call Queue Announcement Files.")
def list_announcements(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    queue_id: str = typer.Argument(help="Webex CALL_QUEUE id, from: wxcli call-queue list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Call Queue Announcement Files.\n\n\b\nExample: wxcli call-queue list-announcements LOCATION_ID QUEUE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/announcements"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("announcements", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('File Name', 'fileName'), ('File Size', 'fileSize'), ('Media File Type', 'mediaFileType'), ('Level', 'level')], limit=limit)



@app.command("delete-announcements", short_help="Delete a Call Queue Announcement File.")
def delete_announcements(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    queue_id: str = typer.Argument(help="Webex CALL_QUEUE id, from: wxcli call-queue list"),
    file_name: str = typer.Argument(help="from: wxcli call-queue list-announcements"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Call Queue Announcement File.\n\n\b\nExample: wxcli call-queue delete-announcements LOCATION_ID QUEUE_ID FILE_NAME"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {file_name}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/announcements/{file_name}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {file_name}")
    else:
        emit({"status": "deleted", "id": file_name}, output=output, fields=fields)



@app.command("show-call-forwarding", short_help="Get Call Forwarding Settings for a Call Queue.")
def show_call_forwarding(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    queue_id: str = typer.Argument(help="Webex CALL_QUEUE id, from: wxcli call-queue list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Forwarding Settings for a Call Queue.\n\n\b\nExample: wxcli call-queue show-call-forwarding LOCATION_ID QUEUE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/callForwarding"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_CALL_FORWARDING = '{"callForwarding":{"always":{"enabled":true,"destination":"...","ringReminderEnabled":true,"destinationVoicemailEnabled":true},"selective":{"enabled":true,"destination":"...","ringReminderEnabled":true,"destinationVoicemailEnabled":true},"rules":[{"id":"...","enabled":true}],"operatingModes":{"enabled":true,"modes":[{"normalOperationEnabled":true,"id":"...","forwardTo":{"selection":"FORWARD_TO_DEFAULT_NUMBER","destination":"...","destinationVoicemailEnabled":true}}]}}}'

@app.command("update-call-forwarding", short_help="Update Call Forwarding Settings for a Call Queue.")
def update_call_forwarding(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    queue_id: str = typer.Argument(help="Webex CALL_QUEUE id, from: wxcli call-queue list"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Call Forwarding Settings for a Call Queue.\n\n\b\nExample: wxcli call-queue update-call-forwarding LOCATION_ID QUEUE_ID\n\n\b\nExample --json-body: '{"callForwarding":{"always":{"enabled":true,"destination":"...","ringReminderEnabled":true,"destinationVoicemailEnabled":true},"selective":{"enabled":true,"destination":"...","ringReminderEnabled":true,"destinationVoicemailEnabled":true},"rules":[{"id":"...","enabled":true}],"operatingModes":{"enabled":true,"modes":[{"normalOperationEnabled":true,"id":"...","forwardTo":{"selection":"FORWARD_TO_DEFAULT_NUMBER","destination":"...","destinationVoicemailEnabled":true}}]}}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CALL_FORWARDING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/callForwarding"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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
        emit({"status": "updated", "id": queue_id}, output=output, fields=fields)



_BODY_SKELETON_CREATE_SELECTIVE_RULES = '{"name":"...","callsFrom":{"selection":"ANY","customNumbers":{"privateNumberEnabled":true,"unavailableNumberEnabled":true,"numbers":["..."]}},"callsTo":{"numbers":[{"type":"PRIMARY","phoneNumber":"...","extension":"..."}]},"enabled":true,"holidaySchedule":"...","businessSchedule":"...","forwardTo":{"selection":"FORWARD_TO_DEFAULT_NUMBER","phoneNumber":"..."}}'

@app.command("create-selective-rules", short_help="Create a Selective Call Forwarding Rule for a Call Queue.")
def create_selective_rules(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    queue_id: str = typer.Argument(help="Webex HUNT_GROUP id, from: wxcli call-queue list"),
    name: str = typer.Option(None, "--name", help="(required) Unique name for the selective rule in the hunt group."),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Reflects if rule is enabled."),
    holiday_schedule: str = typer.Option(None, "--holiday-schedule", help="Name of the location's holiday schedule which determines when this selective call forwarding rule is in effect."),
    business_schedule: str = typer.Option(None, "--business-schedule", help="Name of the location's business schedule which determines when this selective call forwarding rule is in effect."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Selective Call Forwarding Rule for a Call Queue.\n\n\b\nExample: wxcli call-queue create-selective-rules LOCATION_ID QUEUE_ID --json-body '{"name":"...","callsFrom":{"selection":"ANY","customNumbers":{"privateNumberEnabled":true,"unavailableNumberEnabled":true}},"callsTo":{"numbers":[{"type":"PRIMARY"}]}}'\n\n\b\nExample --json-body: '{"name":"...","callsFrom":{"selection":"ANY","customNumbers":{"privateNumberEnabled":true,"unavailableNumberEnabled":true,"numbers":["..."]}},"callsTo":{"numbers":[{"type":"PRIMARY","phoneNumber":"...","extension":"..."}]},"enabled":true,"holidaySchedule":"...","businessSchedule":"...","forwardTo":{"selection":"FORWARD_TO_DEFAULT_NUMBER","phoneNumber":"..."}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_SELECTIVE_RULES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/callForwarding/selectiveRules"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if enabled is not None:
            body["enabled"] = enabled
        if holiday_schedule is not None:
            body["holidaySchedule"] = holiday_schedule
        if business_schedule is not None:
            body["businessSchedule"] = business_schedule
        _missing = [f for f in ['name'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
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



@app.command("show-selective-rules", short_help="Get Selective Call Forwarding Rule for a Call Queue.")
def show_selective_rules(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    queue_id: str = typer.Argument(help="Webex HUNT_GROUP id, from: wxcli call-queue list"),
    rule_id: str = typer.Argument(help="Webex CALL_FORWARDING_SELECTIVE_RULE id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Selective Call Forwarding Rule for a Call Queue.\n\n\b\nExample: wxcli call-queue show-selective-rules LOCATION_ID QUEUE_ID RULE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/callForwarding/selectiveRules/{rule_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_SELECTIVE_RULES = '{"name":"...","enabled":true,"holidaySchedule":"...","businessSchedule":"...","forwardTo":{"selection":"FORWARD_TO_DEFAULT_NUMBER","phoneNumber":"..."},"callsFrom":{"selection":"ANY","customNumbers":{"privateNumberEnabled":true,"unavailableNumberEnabled":true,"numbers":["..."]}},"callsTo":{"numbers":[{"type":"PRIMARY","phoneNumber":"...","extension":"..."}]}}'

@app.command("update-selective-rules", short_help="Update a Selective Call Forwarding Rule for a Call Queue.")
def update_selective_rules(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    queue_id: str = typer.Argument(help="Webex HUNT_GROUP id, from: wxcli call-queue list"),
    rule_id: str = typer.Argument(help="Webex CALL_FORWARDING_SELECTIVE_RULE id"),
    name: str = typer.Option(None, "--name", help="Unique name for the selective rule in the hunt group."),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Reflects if rule is enabled."),
    holiday_schedule: str = typer.Option(None, "--holiday-schedule", help="Name of the location's holiday schedule which determines when this selective call forwarding rule is in effect."),
    business_schedule: str = typer.Option(None, "--business-schedule", help="Name of the location's business schedule which determines when this selective call forwarding rule is in effect."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Selective Call Forwarding Rule for a Call Queue.\n\n\b\nExample: wxcli call-queue update-selective-rules LOCATION_ID QUEUE_ID RULE_ID\n\n\b\nExample --json-body: '{"name":"...","enabled":true,"holidaySchedule":"...","businessSchedule":"...","forwardTo":{"selection":"FORWARD_TO_DEFAULT_NUMBER","phoneNumber":"..."},"callsFrom":{"selection":"ANY","customNumbers":{"privateNumberEnabled":true,"unavailableNumberEnabled":true,"numbers":["..."]}},"callsTo":{"numbers":[{"type":"PRIMARY","phoneNumber":"...","extension":"..."}]}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SELECTIVE_RULES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/callForwarding/selectiveRules/{rule_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if enabled is not None:
            body["enabled"] = enabled
        if holiday_schedule is not None:
            body["holidaySchedule"] = holiday_schedule
        if business_schedule is not None:
            body["businessSchedule"] = business_schedule
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
        emit({"status": "updated", "id": rule_id}, output=output, fields=fields)



@app.command("delete-selective-rules", short_help="Delete a Selective Call Forwarding Rule for a Call Queue.")
def delete_selective_rules(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    queue_id: str = typer.Argument(help="Webex HUNT_GROUP id, from: wxcli call-queue list"),
    rule_id: str = typer.Argument(help="Webex CALL_FORWARDING_SELECTIVE_RULE id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Selective Call Forwarding Rule for a Call Queue.\n\n\b\nExample: wxcli call-queue delete-selective-rules LOCATION_ID QUEUE_ID RULE_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {rule_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/callForwarding/selectiveRules/{rule_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {rule_id}")
    else:
        emit({"status": "deleted", "id": rule_id}, output=output, fields=fields)



@app.command("list-holiday-service", short_help="Get Details for a Call Queue Holiday Service.")
def list_holiday_service(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    queue_id: str = typer.Argument(help="Webex CALL_QUEUE id, from: wxcli call-queue list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Call Queue Holiday Service.\n\n\b\nExample: wxcli call-queue list-holiday-service LOCATION_ID QUEUE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/holidayService"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("audioFiles", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('File Name', 'fileName'), ('Media File Type', 'mediaFileType'), ('Level', 'level'), ('Is Text To Speech', 'isTextToSpeech')], limit=limit)



_BODY_SKELETON_UPDATE_HOLIDAY_SERVICE = '{"holidayServiceEnabled":true,"action":"BUSY","holidayScheduleLevel":"LOCATION","playAnnouncementBeforeEnabled":true,"audioMessageSelection":"DEFAULT","holidayScheduleName":"...","transferPhoneNumber":"...","audioFiles":[{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}]}'

@app.command("update-holiday-service", short_help="Update a Call Queue Holiday Service.")
def update_holiday_service(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    queue_id: str = typer.Argument(help="Webex CALL_QUEUE id, from: wxcli call-queue list"),
    holiday_service_enabled: bool = typer.Option(None, "--holiday-service-enabled/--no-holiday-service-enabled", help="Enable or Disable the call queue holiday service routing policy."),
    action: str = typer.Option(None, "--action", help="Choices: BUSY, TRANSFER"),
    holiday_schedule_level: str = typer.Option(None, "--holiday-schedule-level", help="Choices: LOCATION, ORGANIZATION"),
    holiday_schedule_name: str = typer.Option(None, "--holiday-schedule-name", help="Name of the schedule configured for a holiday service as one of from `holidaySchedules` list."),
    transfer_phone_number: str = typer.Option(None, "--transfer-phone-number", help="Call gets transferred to this number when action is set to `TRANSFER`. This can also be an extension."),
    play_announcement_before_enabled: bool = typer.Option(None, "--play-announcement-before-enabled/--no-play-announcement-before-enabled", help="Indicates whether an announcement plays to callers before the action is applied."),
    audio_message_selection: str = typer.Option(None, "--audio-message-selection", help="Choices: DEFAULT, CUSTOM"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Call Queue Holiday Service.\n\n\b\nExample: wxcli call-queue update-holiday-service LOCATION_ID QUEUE_ID --holiday-service-enabled --action BUSY --holiday-schedule-level LOCATION --play-announcement-before-enabled --audio-message-selection DEFAULT\n\n\b\nExample --json-body: '{"holidayServiceEnabled":true,"action":"BUSY","holidayScheduleLevel":"LOCATION","playAnnouncementBeforeEnabled":true,"audioMessageSelection":"DEFAULT","holidayScheduleName":"...","transferPhoneNumber":"...","audioFiles":[{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_HOLIDAY_SERVICE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/holidayService"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if holiday_service_enabled is not None:
            body["holidayServiceEnabled"] = holiday_service_enabled
        if action is not None:
            body["action"] = action
        if holiday_schedule_level is not None:
            body["holidayScheduleLevel"] = holiday_schedule_level
        if holiday_schedule_name is not None:
            body["holidayScheduleName"] = holiday_schedule_name
        if transfer_phone_number is not None:
            body["transferPhoneNumber"] = transfer_phone_number
        if play_announcement_before_enabled is not None:
            body["playAnnouncementBeforeEnabled"] = play_announcement_before_enabled
        if audio_message_selection is not None:
            body["audioMessageSelection"] = audio_message_selection
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
        emit({"status": "updated", "id": queue_id}, output=output, fields=fields)



@app.command("list-night-service", short_help="Get Details for a Call Queue Night Service.")
def list_night_service(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    queue_id: str = typer.Argument(help="Webex CALL_QUEUE id, from: wxcli call-queue list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Call Queue Night Service.\n\n\b\nExample: wxcli call-queue list-night-service LOCATION_ID QUEUE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/nightService"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("audioFiles", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('File Name', 'fileName'), ('Media File Type', 'mediaFileType'), ('Level', 'level'), ('Is Text To Speech', 'isTextToSpeech')], limit=limit)



_BODY_SKELETON_UPDATE_NIGHT_SERVICE = '{"nightServiceEnabled":true,"playAnnouncementBeforeEnabled":true,"announcementMode":"NORMAL","audioMessageSelection":"DEFAULT","forceNightServiceEnabled":true,"manualAudioMessageSelection":"DEFAULT","action":"BUSY","transferPhoneNumber":"...","audioFiles":[{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}],"businessHoursName":"...","businessHoursLevel":"ORGANIZATION","manualAudioFiles":[{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}]}'

@app.command("update-night-service", short_help="Update a Call Queue Night Service.")
def update_night_service(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    queue_id: str = typer.Argument(help="Webex CALL_QUEUE id, from: wxcli call-queue list"),
    night_service_enabled: bool = typer.Option(None, "--night-service-enabled/--no-night-service-enabled", help="Enable or disable call queue night service routing policy."),
    action: str = typer.Option(None, "--action", help="Choices: BUSY, TRANSFER"),
    transfer_phone_number: str = typer.Option(None, "--transfer-phone-number", help="Call gets transferred to this number when action is set to `TRANSFER`. This can also be an extension."),
    play_announcement_before_enabled: bool = typer.Option(None, "--play-announcement-before-enabled/--no-play-announcement-before-enabled", help="Indicates whether an announcement plays to callers before the action is applied."),
    announcement_mode: str = typer.Option(None, "--announcement-mode", help="Choices: NORMAL, MANUAL"),
    audio_message_selection: str = typer.Option(None, "--audio-message-selection", help="Choices: DEFAULT, CUSTOM"),
    business_hours_name: str = typer.Option(None, "--business-hours-name", help="Name of the schedule configured for a night service as one of from `businessHourSchedules` list."),
    business_hours_level: str = typer.Option(None, "--business-hours-level", help="Choices: ORGANIZATION, LOCATION"),
    force_night_service_enabled: bool = typer.Option(None, "--force-night-service-enabled/--no-force-night-service-enabled", help="Force night service regardless of business hour schedule."),
    manual_audio_message_selection: str = typer.Option(None, "--manual-audio-message-selection", help="Choices: DEFAULT, CUSTOM"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Call Queue Night Service.\n\n\b\nExample: wxcli call-queue update-night-service LOCATION_ID QUEUE_ID --night-service-enabled --play-announcement-before-enabled --announcement-mode NORMAL --audio-message-selection DEFAULT --force-night-service-enabled --manual-audio-message-selection DEFAULT\n\n\b\nExample --json-body: '{"nightServiceEnabled":true,"playAnnouncementBeforeEnabled":true,"announcementMode":"NORMAL","audioMessageSelection":"DEFAULT","forceNightServiceEnabled":true,"manualAudioMessageSelection":"DEFAULT","action":"BUSY","transferPhoneNumber":"...","audioFiles":[{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}],"businessHoursName":"...","businessHoursLevel":"ORGANIZATION","manualAudioFiles":[{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_NIGHT_SERVICE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/nightService"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if night_service_enabled is not None:
            body["nightServiceEnabled"] = night_service_enabled
        if action is not None:
            body["action"] = action
        if transfer_phone_number is not None:
            body["transferPhoneNumber"] = transfer_phone_number
        if play_announcement_before_enabled is not None:
            body["playAnnouncementBeforeEnabled"] = play_announcement_before_enabled
        if announcement_mode is not None:
            body["announcementMode"] = announcement_mode
        if audio_message_selection is not None:
            body["audioMessageSelection"] = audio_message_selection
        if business_hours_name is not None:
            body["businessHoursName"] = business_hours_name
        if business_hours_level is not None:
            body["businessHoursLevel"] = business_hours_level
        if force_night_service_enabled is not None:
            body["forceNightServiceEnabled"] = force_night_service_enabled
        if manual_audio_message_selection is not None:
            body["manualAudioMessageSelection"] = manual_audio_message_selection
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
        emit({"status": "updated", "id": queue_id}, output=output, fields=fields)



@app.command("list-forced-forward", short_help="Get Details for a Call Queue Forced Forward.")
def list_forced_forward(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    queue_id: str = typer.Argument(help="Webex CALL_QUEUE id, from: wxcli call-queue list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Call Queue Forced Forward.\n\n\b\nExample: wxcli call-queue list-forced-forward LOCATION_ID QUEUE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/forcedForward"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("audioFiles", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('File Name', 'fileName'), ('Media File Type', 'mediaFileType'), ('Level', 'level'), ('Is Text To Speech', 'isTextToSpeech')], limit=limit)



_BODY_SKELETON_UPDATE_FORCED_FORWARD = '{"forcedForwardEnabled":true,"playAnnouncementBeforeEnabled":true,"audioMessageSelection":"DEFAULT","transferPhoneNumber":"...","audioFiles":[{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}]}'

@app.command("update-forced-forward", short_help="Update a Call Queue Forced Forward Service.")
def update_forced_forward(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    queue_id: str = typer.Argument(help="Webex CALL_QUEUE id, from: wxcli call-queue list"),
    forced_forward_enabled: bool = typer.Option(None, "--forced-forward-enabled/--no-forced-forward-enabled", help="Enable or disable call forced forward service routing policy."),
    transfer_phone_number: str = typer.Option(None, "--transfer-phone-number", help="Call gets transferred to this number when action is set to `TRANSFER`. This can also be an extension."),
    play_announcement_before_enabled: bool = typer.Option(None, "--play-announcement-before-enabled/--no-play-announcement-before-enabled", help="Indicates whether an announcement plays to callers before the action is applied."),
    audio_message_selection: str = typer.Option(None, "--audio-message-selection", help="Choices: DEFAULT, CUSTOM"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Call Queue Forced Forward Service.\n\n\b\nExample: wxcli call-queue update-forced-forward LOCATION_ID QUEUE_ID --forced-forward-enabled --play-announcement-before-enabled --audio-message-selection DEFAULT\n\n\b\nExample --json-body: '{"forcedForwardEnabled":true,"playAnnouncementBeforeEnabled":true,"audioMessageSelection":"DEFAULT","transferPhoneNumber":"...","audioFiles":[{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_FORCED_FORWARD), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/forcedForward"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if forced_forward_enabled is not None:
            body["forcedForwardEnabled"] = forced_forward_enabled
        if transfer_phone_number is not None:
            body["transferPhoneNumber"] = transfer_phone_number
        if play_announcement_before_enabled is not None:
            body["playAnnouncementBeforeEnabled"] = play_announcement_before_enabled
        if audio_message_selection is not None:
            body["audioMessageSelection"] = audio_message_selection
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
        emit({"status": "updated", "id": queue_id}, output=output, fields=fields)



@app.command("list-stranded-calls", short_help="Get Details for a Call Queue Stranded Calls.")
def list_stranded_calls(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    queue_id: str = typer.Argument(help="Webex CALL_QUEUE id, from: wxcli call-queue list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Call Queue Stranded Calls.\n\n\b\nExample: wxcli call-queue list-stranded-calls LOCATION_ID QUEUE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/strandedCalls"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("audioFiles", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('File Name', 'fileName'), ('Media File Type', 'mediaFileType'), ('Level', 'level'), ('Is Text To Speech', 'isTextToSpeech')], limit=limit)



_BODY_SKELETON_UPDATE_STRANDED_CALLS = '{"action":"NONE","audioMessageSelection":"DEFAULT","transferPhoneNumber":"...","audioFiles":[{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}],"triggerPolicyWhenAllAgentsAreUnreachableEnabled":true}'

@app.command("update-stranded-calls", short_help="Update a Call Queue Stranded Calls Service.")
def update_stranded_calls(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    queue_id: str = typer.Argument(help="Webex CALL_QUEUE id, from: wxcli call-queue list"),
    action: str = typer.Option(None, "--action", help="Choices: NONE, BUSY, TRANSFER, NIGHT_SERVICE, RINGING, ANNOUNCEMENT"),
    transfer_phone_number: str = typer.Option(None, "--transfer-phone-number", help="Call gets transferred to this number when action is set to `TRANSFER`. This can also be an extension."),
    audio_message_selection: str = typer.Option(None, "--audio-message-selection", help="Choices: DEFAULT, CUSTOM"),
    trigger_policy_when_all_agents_are_unreachable_enabled: bool = typer.Option(None, "--trigger-policy-when-all-agents-are-unreachable-enabled/--no-trigger-policy-when-all-agents-are-unreachable-enabled", help="Trigger stranded calls queue policy when all agents are unreachable."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Call Queue Stranded Calls Service.\n\n\b\nExample: wxcli call-queue update-stranded-calls LOCATION_ID QUEUE_ID --action NONE --audio-message-selection DEFAULT\n\n\b\nExample --json-body: '{"action":"NONE","audioMessageSelection":"DEFAULT","transferPhoneNumber":"...","audioFiles":[{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}],"triggerPolicyWhenAllAgentsAreUnreachableEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_STRANDED_CALLS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/strandedCalls"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if action is not None:
            body["action"] = action
        if transfer_phone_number is not None:
            body["transferPhoneNumber"] = transfer_phone_number
        if audio_message_selection is not None:
            body["audioMessageSelection"] = audio_message_selection
        if trigger_policy_when_all_agents_are_unreachable_enabled is not None:
            body["triggerPolicyWhenAllAgentsAreUnreachableEnabled"] = trigger_policy_when_all_agents_are_unreachable_enabled
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
        emit({"status": "updated", "id": queue_id}, output=output, fields=fields)



@app.command("list-available-numbers-queues", short_help="Get Call Queue Primary Available Phone Numbers.")
def list_available_numbers_queues(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provided in the `phoneNumber` array."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Queue Primary Available Phone Numbers.\n\n\b\nExample: wxcli call-queue list-available-numbers-queues LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/availableNumbers"
    params = {}
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_pagination(url=url, params=params, item_key="phoneNumbers"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("phoneNumbers", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('State', 'state'), ('Is Main Number', 'isMainNumber'), ('Toll Free Number', 'tollFreeNumber'), ('Telephony Type', 'telephonyType')], limit=limit)



@app.command("list-available-numbers-alternate", short_help="Get Call Queue Alternate Available Phone Numbers.")
def list_available_numbers_alternate(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provided in the `phoneNumber` array."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Queue Alternate Available Phone Numbers.\n\n\b\nExample: wxcli call-queue list-available-numbers-alternate LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/alternate/availableNumbers"
    params = {}
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_pagination(url=url, params=params, item_key="phoneNumbers"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("phoneNumbers", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('State', 'state'), ('Is Main Number', 'isMainNumber'), ('Toll Free Number', 'tollFreeNumber'), ('Telephony Type', 'telephonyType')], limit=limit)



@app.command("list-available-numbers-call-forwarding", short_help="Get Call Queue Call Forward Available Phone Numbers.")
def list_available_numbers_call_forwarding(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provided in the `phoneNumber` array."),
    owner_name: str = typer.Option(None, "--owner-name", help="Return the list of phone numbers that are owned by the given `ownerName`. Maximum length is 255."),
    extension: str = typer.Option(None, "--extension", help="Returns the list of PSTN phone numbers with the given `extension`."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Queue Call Forward Available Phone Numbers.\n\n\b\nExample: wxcli call-queue list-available-numbers-call-forwarding LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/callForwarding/availableNumbers"
    params = {}
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if owner_name is not None:
        params["ownerName"] = owner_name
    if extension is not None:
        params["extension"] = extension
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_pagination(url=url, params=params, item_key="phoneNumbers"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("phoneNumbers", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('Extension', 'extension'), ('State', 'state'), ('Is Main Number', 'isMainNumber'), ('Toll Free Number', 'tollFreeNumber')], limit=limit)



@app.command("list-available-agents-queues", short_help="Get Call Queue Available Agents.")
def list_available_agents_queues(
    location_id: str = typer.Option(..., "--location-id", help="The location ID of the call queue. Temporary mandatory query parameter, used for performance reasons only and not a filter."),
    name: str = typer.Option(None, "--name", help="Search based on name (user first and last name combination)."),
    phone_number: str = typer.Option(None, "--phone-number", help="Search based on number or extension."),
    order: str = typer.Option(None, "--order", help="Order the available agents according to the designated fields. Up to three comma-separated sort order fields may be specified. Available sort fields are: `userId`, `fname`, `firstname`, `lname`, `lastname`, `dn`, and `extension`. Sort order can be added together with each field using a hyphen, `-`...."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Queue Available Agents.\n\n\b\nExample: wxcli call-queue list-available-agents-queues --location-id LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/queues/agents/availableAgents"
    params = {}
    if location_id is not None:
        params["locationId"] = location_id
    if name is not None:
        params["name"] = name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if order is not None:
        params["order"] = order
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_pagination(url=url, params=params, item_key="agents"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("agents", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('Last Name', 'lastName'), ('First Name', 'firstName'), ('Type', 'type')], limit=limit)



@app.command("list-supervisors", short_help="Get List of Supervisors with Customer Assist.")
def list_supervisors(
    name: str = typer.Option(None, "--name", help="Only return the supervisors that match the given name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Only return the supervisors that match the given phone number, extension, or ESN."),
    order: str = typer.Option(None, "--order", help="Sort results alphabetically by supervisor name, in ascending or descending order."),
    has_cx_essentials: str = typer.Option(None, "--has-cx-essentials", help="Returns only the list of supervisors with Customer Assist license, when `true`. Otherwise returns the list of supervisors with Customer Experience Basic license."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get List of Supervisors with Customer Assist."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/supervisors"
    params = {}
    if name is not None:
        params["name"] = name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if order is not None:
        params["order"] = order
    if has_cx_essentials is not None:
        params["hasCxEssentials"] = has_cx_essentials
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_pagination(url=url, params=params, item_key="supervisors"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("supervisors", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('First Name', 'firstName'), ('Last Name', 'lastName'), ('Phone Number', 'phoneNumber'), ('Extension', 'extension')], limit=limit)



_BODY_SKELETON_CREATE_SUPERVISORS = '{"id":"...","agents":[{"id":"..."}]}'

@app.command("create-supervisors", short_help="Create a Supervisor with Customer Assist.")
def create_supervisors(
    has_cx_essentials: str = typer.Option(None, "--has-cx-essentials", help="Creates a Customer Assist queue supervisor, when `true`. Customer Assist queue supervisors must have a Customer Assist license."),
    id_param: str = typer.Option(None, "--id", help="(required) A unique identifier for the supervisor."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Supervisor with Customer Assist.\n\n\b\nExample: wxcli call-queue create-supervisors --json-body '{"id":"...","agents":[{"id":"..."}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_SUPERVISORS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/supervisors"
    params = {}
    if has_cx_essentials is not None:
        params["hasCxEssentials"] = has_cx_essentials
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if id_param is not None:
            body["id"] = id_param
        _missing = [f for f in ['id'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
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



_BODY_SKELETON_DELETE_SUPERVISORS_CONFIG = '{"supervisorIds":["..."],"hasCxEssentials":true,"deleteAll":true}'

@app.command("delete-supervisors-config", short_help="Delete the Call Queue or Customer Assist Supervisors.")
def delete_supervisors_config(
    has_cx_essentials: bool = typer.Option(None, "--has-cx-essentials/--no-has-cx-essentials", help="Delete the Customer Assist supervisors, when `true`. Otherwise delete the Call Queue supervisors. The default value is `false`."),
    delete_all: bool = typer.Option(None, "--delete-all/--no-delete-all", help="If present the `supervisorIds` array is ignored, and all supervisors in the context are deleted. **WARNING**: This will remove all supervisors from the organization."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete the Call Queue or Customer Assist Supervisors.\n\n\b\nExample: wxcli call-queue delete-supervisors-config --json-body '{"supervisorIds":["..."]}'\n\n\b\nExample --json-body: '{"supervisorIds":["..."],"hasCxEssentials":true,"deleteAll":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_DELETE_SUPERVISORS_CONFIG), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    if not force:
        typer.confirm("Delete this resource?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/supervisors"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if has_cx_essentials is not None:
            body["hasCxEssentials"] = has_cx_essentials
        if delete_all is not None:
            body["deleteAll"] = delete_all
    missing = [f for f in ['supervisorIds'] if f not in body]
    if missing:
        typer.echo(f"Error: required body field(s) missing: {', '.join(missing)}. Pass them via --json-body — this delete needs to know what to delete.", err=True)
        raise typer.Exit(1)
    try:
        result = api.session.rest_delete(url, json=body or None, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo("Deleted.")
    else:
        emit({"status": "deleted"}, output=output, fields=fields)



@app.command("show-supervisors", short_help="Get Supervisor Detail with Customer Assist.")
def show_supervisors(
    supervisor_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli call-queue list-supervisors"),
    max: str = typer.Option(None, "--max", help="Limit the number of objects returned to this maximum count."),
    start: str = typer.Option(None, "--start", help="Start at the zero-based offset in the list of matching objects."),
    name: str = typer.Option(None, "--name", help="Only return the agents that match the given name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Only return agents that match the given phone number, extension, or ESN."),
    order: str = typer.Option(None, "--order", help="Sort results alphabetically by supervisor name, in ascending or descending order."),
    has_cx_essentials: str = typer.Option(None, "--has-cx-essentials", help="Must be set to `true`, to view the details of a supervisor with Customer Assist license. This can otherwise be ommited or set to `false`."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Supervisor Detail with Customer Assist.\n\n\b\nExample: wxcli call-queue show-supervisors SUPERVISOR_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/supervisors/{supervisor_id}"
    params = {}
    if max is not None:
        params["max"] = max
    if start is not None:
        params["start"] = start
    if name is not None:
        params["name"] = name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if order is not None:
        params["order"] = order
    if has_cx_essentials is not None:
        params["hasCxEssentials"] = has_cx_essentials
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_SUPERVISORS = '{"agents":[{"id":"...","action":"ADD"}]}'

@app.command("update-supervisors", short_help="Assign or Unassign Agents to Supervisor with Customer Assist.")
def update_supervisors(
    supervisor_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli call-queue list-supervisors"),
    has_cx_essentials: str = typer.Option(None, "--has-cx-essentials", help="Must be set to `true` to modify a supervisor with Customer Assist license. This can otherwise be ommited or set to `false`."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Assign or Unassign Agents to Supervisor with Customer Assist.\n\n\b\nExample: wxcli call-queue update-supervisors SUPERVISOR_ID --json-body '{"agents":[{"id":"...","action":"ADD"}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SUPERVISORS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/supervisors/{supervisor_id}"
    params = {}
    if has_cx_essentials is not None:
        params["hasCxEssentials"] = has_cx_essentials
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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
        emit({"status": "updated", "id": supervisor_id}, output=output, fields=fields)



@app.command("delete-supervisors-config-1", short_help="Delete a Supervisor.")
def delete_supervisors_config_1(
    supervisor_id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli call-queue list-supervisors"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Supervisor.\n\n\b\nExample: wxcli call-queue delete-supervisors-config-1 SUPERVISOR_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {supervisor_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/supervisors/{supervisor_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {supervisor_id}")
    else:
        emit({"status": "deleted", "id": supervisor_id}, output=output, fields=fields)



@app.command("list-available-supervisors", short_help="List Available Supervisors with Customer Assist.")
def list_available_supervisors(
    name: str = typer.Option(None, "--name", help="Only return the supervisors that match the given name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Only return the supervisors that match the given phone number, extension, or ESN."),
    order: str = typer.Option(None, "--order", help="Sort results alphabetically by supervisor name, in ascending or descending order."),
    has_cx_essentials: str = typer.Option(None, "--has-cx-essentials", help="Returns only the list of available supervisors with Customer Assist license, when `true`. When ommited or set to 'false', will return the list of available supervisors with Customer Experience Basic license."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Available Supervisors with Customer Assist."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/supervisors/availableSupervisors"
    params = {}
    if name is not None:
        params["name"] = name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if order is not None:
        params["order"] = order
    if has_cx_essentials is not None:
        params["hasCxEssentials"] = has_cx_essentials
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_pagination(url=url, params=params, item_key="supervisors"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("supervisors", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('First Name', 'firstName'), ('Last Name', 'lastName'), ('Phone Number', 'phoneNumber')], limit=limit)



@app.command("list-available-agents-supervisors", short_help="List Available Agents with Customer Assist.")
def list_available_agents_supervisors(
    name: str = typer.Option(None, "--name", help="Returns only the agents that match the given name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Returns only the agents that match the phone number, extension, or ESN."),
    order: str = typer.Option(None, "--order", help="Sort results alphabetically by supervisor name, in ascending or descending order."),
    has_cx_essentials: str = typer.Option(None, "--has-cx-essentials", help="Returns only the list of available agents with Customer Assist license, when `true`. When ommited or set to `false`, will return the list of available agents with Customer Experience Basic license."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Available Agents with Customer Assist."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/supervisors/availableAgents"
    params = {}
    if name is not None:
        params["name"] = name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if order is not None:
        params["order"] = order
    if has_cx_essentials is not None:
        params["hasCxEssentials"] = has_cx_essentials
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_pagination(url=url, params=params, item_key="agents"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("agents", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Display Name', 'displayName'), ('First Name', 'firstName'), ('Last Name', 'lastName'), ('Phone Number', 'phoneNumber')], limit=limit)



@app.command("list-agents", short_help="Read the List of Call Queue Agents with Customer Assist.")
def list_agents(
    location_id: str = typer.Option(None, "--location-id", help="Return only the call queue agents in this location."),
    queue_id: str = typer.Option(None, "--queue-id", help="Only return call queue agents with the matching queue ID."),
    name: str = typer.Option(None, "--name", help="Returns only the list of call queue agents that match the given name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Returns only the list of call queue agents that match the given phone number or extension."),
    join_enabled: str = typer.Option(None, "--join-enabled", help="Returns only the list of call queue agents that match the given `joinEnabled` value."),
    has_cx_essentials: str = typer.Option(None, "--has-cx-essentials", help="Returns only the list of call queues with Customer Assist license when `true`, otherwise returns the list of Customer Experience Basic call queues."),
    order: str = typer.Option(None, "--order", help="Sort results alphabetically by call queue agent's name, in ascending or descending order."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Call Queue Agents with Customer Assist."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/queues/agents"
    params = {}
    if location_id is not None:
        params["locationId"] = location_id
    if queue_id is not None:
        params["queueId"] = queue_id
    if name is not None:
        params["name"] = name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if join_enabled is not None:
        params["joinEnabled"] = join_enabled
    if has_cx_essentials is not None:
        params["hasCxEssentials"] = has_cx_essentials
    if order is not None:
        params["order"] = order
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        if limit > 0 and not all_pages:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("agents", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="agents"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('First Name', 'firstName'), ('Last Name', 'lastName'), ('Phone Number', 'phoneNumber'), ('Extension', 'extension')], limit=limit)



@app.command("show-agents", short_help="Get Details for a Call Queue Agent with Customer Assist.")
def show_agents(
    id: str = typer.Argument(help="Webex CALL_QUEUE id, from: wxcli call-queue list-agents"),
    has_cx_essentials: str = typer.Option(None, "--has-cx-essentials", help="Must be set to `true` to view the details of an agent with Customer Assist license. This can otherwise be ommited or set to `false`."),
    max: str = typer.Option(..., "--max", help="Limit the number of objects returned to this maximum count."),
    start: str = typer.Option(..., "--start", help="Start at the zero-based offset in the list of matching objects."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for a Call Queue Agent with Customer Assist.\n\n\b\nExample: wxcli call-queue show-agents ID --max MAX --start START"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/queues/agents/{id}"
    params = {}
    if has_cx_essentials is not None:
        params["hasCxEssentials"] = has_cx_essentials
    if max is not None:
        params["max"] = max
    if start is not None:
        params["start"] = start
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_SETTINGS_AGENTS = '{"settings":[{"queueId":"...","joinEnabled":true}]}'

@app.command("update-settings-agents", short_help="Update an Agent's Settings of One or More Call Queues with Customer Assist.")
def update_settings_agents(
    id: str = typer.Argument(help="Webex PEOPLE id, from: wxcli call-queue list-agents"),
    has_cx_essentials: str = typer.Option(None, "--has-cx-essentials", help="Must be set to `true` to modify an agent that has Customer Assist license. This can otherwise be ommited or set to `false`."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update an Agent's Settings of One or More Call Queues with Customer Assist.\n\n\b\nExample: wxcli call-queue update-settings-agents ID --json-body '{"settings":[{"queueId":"...","joinEnabled":true}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SETTINGS_AGENTS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/queues/agents/{id}/settings"
    params = {}
    if has_cx_essentials is not None:
        params["hasCxEssentials"] = has_cx_essentials
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": id}, output=output, fields=fields)



@app.command("switch-mode-for", short_help="Switch Mode for Call Forwarding Settings for a Call Queue.")
def switch_mode_for(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    queue_id: str = typer.Argument(help="Webex CALL_QUEUE id, from: wxcli call-queue list"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Switch Mode for Call Forwarding Settings for a Call Queue.\n\n\b\nExample: wxcli call-queue switch-mode-for LOCATION_ID QUEUE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/callForwarding/actions/switchMode/invoke"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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
    emit(result, output=output, fields=fields)



@app.command("list-dnis", short_help="Get List of DNIS for a Call Queue.")
def list_dnis(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    queue_id: str = typer.Argument(help="Webex CALL_QUEUE id, from: wxcli call-queue list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get List of DNIS for a Call Queue.\n\n\b\nExample: wxcli call-queue list-dnis LOCATION_ID QUEUE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/dnis"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("dnisList", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Phone Number', 'phoneNumber'), ('Extension', 'extension'), ('Routing Prefix', 'routingPrefix')], limit=limit)



_BODY_SKELETON_CREATE_DNIS = '{"name":"...","ringPattern":"NORMAL","phoneNumber":"...","extension":"..."}'

@app.command("create-dnis", short_help="Create a DNIS for a Call Queue.")
def create_dnis(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    queue_id: str = typer.Argument(help="Webex CALL_QUEUE id, from: wxcli call-queue list"),
    name: str = typer.Option(None, "--name", help="(required) Name of the DNIS. Must be unique across the call queue."),
    phone_number: str = typer.Option(None, "--phone-number", help="Phone number of the DNIS. Must be a valid phone number from the same location. Either phoneNumber or extension is required."),
    extension: str = typer.Option(None, "--extension", help="Extension of the DNIS. Either phoneNumber or extension is required."),
    ring_pattern: str = typer.Option(None, "--ring-pattern", help="(required) Choices: NORMAL, LONG_LONG, SHORT_SHORT_LONG, SHORT_LONG_SHORT"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a DNIS for a Call Queue.\n\n\b\nExample: wxcli call-queue create-dnis LOCATION_ID QUEUE_ID --name NAME --ring-pattern NORMAL\n\n\b\nExample --json-body: '{"name":"...","ringPattern":"NORMAL","phoneNumber":"...","extension":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_DNIS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/dnis"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if phone_number is not None:
            body["phoneNumber"] = phone_number
        if extension is not None:
            body["extension"] = extension
        if ring_pattern is not None:
            body["ringPattern"] = ring_pattern
        _missing = [f for f in ['name', 'ringPattern'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
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



_BODY_SKELETON_DELETE_DNIS_QUEUES = '{"items":["..."]}'

@app.command("delete-dnis-queues", short_help="Bulk Delete DNIS for a Call Queue.")
def delete_dnis_queues(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    queue_id: str = typer.Argument(help="Webex CALL_QUEUE id, from: wxcli call-queue list"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk Delete DNIS for a Call Queue.\n\n\b\nExample: wxcli call-queue delete-dnis-queues LOCATION_ID QUEUE_ID --json-body '{"items":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_DELETE_DNIS_QUEUES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete Dnis for {queue_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/dnis"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
    missing = [f for f in ['items'] if f not in body]
    if missing:
        typer.echo(f"Error: required body field(s) missing: {', '.join(missing)}. Pass them via --json-body — this delete needs to know what to delete.", err=True)
        raise typer.Exit(1)
    try:
        result = api.session.rest_delete(url, json=body or None, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {queue_id}")
    else:
        emit({"status": "deleted", "id": queue_id}, output=output, fields=fields)



@app.command("show-dnis", short_help="Get a DNIS for a Call Queue.")
def show_dnis(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    queue_id: str = typer.Argument(help="Webex CALL_QUEUE id, from: wxcli call-queue list"),
    dnis_id: str = typer.Argument(help="Webex DNIS id, from: wxcli call-queue list-dnis"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a DNIS for a Call Queue.\n\n\b\nExample: wxcli call-queue show-dnis LOCATION_ID QUEUE_ID DNIS_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/dnis/{dnis_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_DNIS = '{"name":"...","phoneNumber":"...","extension":"...","ringPattern":"NORMAL","customDnisAnnouncementSettingsEnabled":true}'

@app.command("update-dnis", short_help="Modify a DNIS for a Call Queue.")
def update_dnis(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    queue_id: str = typer.Argument(help="Webex CALL_QUEUE id, from: wxcli call-queue list"),
    dnis_id: str = typer.Argument(help="Webex DNIS id, from: wxcli call-queue list-dnis"),
    name: str = typer.Option(None, "--name", help="Name of the DNIS. Must be unique across the call queue."),
    phone_number: str = typer.Option(None, "--phone-number", help="Phone number of the DNIS. Set to `null` to remove the phone number."),
    extension: str = typer.Option(None, "--extension", help="Extension of the DNIS. Set to `null` to remove the extension."),
    ring_pattern: str = typer.Option(None, "--ring-pattern", help="Choices: NORMAL, LONG_LONG, SHORT_SHORT_LONG, SHORT_LONG_SHORT"),
    custom_dnis_announcement_settings_enabled: bool = typer.Option(None, "--custom-dnis-announcement-settings-enabled/--no-custom-dnis-announcement-settings-enabled", help="Use custom announcement settings for the DNIS."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify a DNIS for a Call Queue.\n\n\b\nExample: wxcli call-queue update-dnis LOCATION_ID QUEUE_ID DNIS_ID\n\n\b\nExample --json-body: '{"name":"...","phoneNumber":"...","extension":"...","ringPattern":"NORMAL","customDnisAnnouncementSettingsEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_DNIS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/dnis/{dnis_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if phone_number is not None:
            body["phoneNumber"] = phone_number
        if extension is not None:
            body["extension"] = extension
        if ring_pattern is not None:
            body["ringPattern"] = ring_pattern
        if custom_dnis_announcement_settings_enabled is not None:
            body["customDnisAnnouncementSettingsEnabled"] = custom_dnis_announcement_settings_enabled
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
        emit({"status": "updated", "id": dnis_id}, output=output, fields=fields)



@app.command("delete-dnis-queues-1", short_help="Delete a DNIS for a Call Queue.")
def delete_dnis_queues_1(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    queue_id: str = typer.Argument(help="Webex CALL_QUEUE id, from: wxcli call-queue list"),
    dnis_id: str = typer.Argument(help="Webex DNIS id, from: wxcli call-queue list-dnis"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a DNIS for a Call Queue.\n\n\b\nExample: wxcli call-queue delete-dnis-queues-1 LOCATION_ID QUEUE_ID DNIS_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {dnis_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/dnis/{dnis_id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {dnis_id}")
    else:
        emit({"status": "deleted", "id": dnis_id}, output=output, fields=fields)



@app.command("show-settings", short_help="Get DNIS Settings for a Call Queue.")
def show_settings(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    queue_id: str = typer.Argument(help="Webex CALL_QUEUE id, from: wxcli call-queue list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get DNIS Settings for a Call Queue.\n\n\b\nExample: wxcli call-queue show-settings LOCATION_ID QUEUE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/dnis/settings"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_SETTINGS_DNIS = '{"distinctiveRingingEnabled":true,"displayDnisNameAndNumberEnabled":true}'

@app.command("update-settings-dnis", short_help="Modify DNIS Settings for a Call Queue.")
def update_settings_dnis(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    queue_id: str = typer.Argument(help="Webex CALL_QUEUE id, from: wxcli call-queue list"),
    distinctive_ringing_enabled: bool = typer.Option(None, "--distinctive-ringing-enabled/--no-distinctive-ringing-enabled", help="Whether distinctive ringing is enabled for the queue."),
    display_dnis_name_and_number_enabled: bool = typer.Option(None, "--display-dnis-name-and-number-enabled/--no-display-dnis-name-and-number-enabled", help="Whether the DNIS name and number is displayed to agents."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify DNIS Settings for a Call Queue.\n\n\b\nExample: wxcli call-queue update-settings-dnis LOCATION_ID QUEUE_ID\n\n\b\nExample --json-body: '{"distinctiveRingingEnabled":true,"displayDnisNameAndNumberEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SETTINGS_DNIS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/dnis/settings"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if distinctive_ringing_enabled is not None:
            body["distinctiveRingingEnabled"] = distinctive_ringing_enabled
        if display_dnis_name_and_number_enabled is not None:
            body["displayDnisNameAndNumberEnabled"] = display_dnis_name_and_number_enabled
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
        emit({"status": "updated", "id": queue_id}, output=output, fields=fields)



@app.command("show-announcements", short_help="Get DNIS Announcements for a Call Queue.")
def show_announcements(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    queue_id: str = typer.Argument(help="Webex CALL_QUEUE id, from: wxcli call-queue list"),
    dnis_id: str = typer.Argument(help="Webex DNIS id, from: wxcli call-queue list-dnis"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get DNIS Announcements for a Call Queue.\n\n\b\nExample: wxcli call-queue show-announcements LOCATION_ID QUEUE_ID DNIS_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/dnis/{dnis_id}/announcements"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_ANNOUNCEMENTS = '{"customDnisAnnouncementSettingsEnabled":true,"welcomeMessage":{"enabled":true,"alwaysEnabled":true,"greeting":"DEFAULT","audioAnnouncementFiles":[{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}]},"comfortMessage":{"enabled":true,"timeBetweenMessages":0,"greeting":"DEFAULT","audioAnnouncementFiles":[{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}]},"comfortMessageBypass":{"enabled":true,"callWaitingAgeThreshold":0,"greeting":"DEFAULT","audioAnnouncementFiles":[{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}]},"mohMessage":{"normalSource":{"enabled":true,"greeting":"DEFAULT","audioAnnouncementFiles":[{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}],"audioPlaylistId":"..."},"alternateSource":{"enabled":true,"greeting":"DEFAULT","audioAnnouncementFiles":[{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}],"audioPlaylistId":"..."}},"waitMessage":{"enabled":true,"waitMode":"TIME","handlingTime":0,"defaultHandlingTime":0,"queuePosition":0,"highVolumeMessageEnabled":true,"estimatedWaitingTime":0,"callbackOptionEnabled":true,"minimumEstimatedCallbackTime":0,"internationalCallbackEnabled":true,"playUpdatedEstimatedWaitMessage":true},"whisperMessage":{"enabled":true,"greeting":"DEFAULT","audioAnnouncementFiles":[{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}]}}'

@app.command("update-announcements", short_help="Modify DNIS Announcements for a Call Queue.")
def update_announcements(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    queue_id: str = typer.Argument(help="Webex CALL_QUEUE id, from: wxcli call-queue list"),
    dnis_id: str = typer.Argument(help="Webex DNIS id, from: wxcli call-queue list-dnis"),
    custom_dnis_announcement_settings_enabled: bool = typer.Option(None, "--custom-dnis-announcement-settings-enabled/--no-custom-dnis-announcement-settings-enabled", help="Whether custom DNIS announcement settings are enabled for this DNIS."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Modify DNIS Announcements for a Call Queue.\n\n\b\nExample: wxcli call-queue update-announcements LOCATION_ID QUEUE_ID DNIS_ID\n\n\b\nExample --json-body: '{"customDnisAnnouncementSettingsEnabled":true,"welcomeMessage":{"enabled":true,"alwaysEnabled":true,"greeting":"DEFAULT","audioAnnouncementFiles":[{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}]},"comfortMessage":{"enabled":true,"timeBetweenMessages":0,"greeting":"DEFAULT","audioAnnouncementFiles":[{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}]},"comfortMessageBypass":{"enabled":true,"callWaitingAgeThreshold":0,"greeting":"DEFAULT","audioAnnouncementFiles":[{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}]},"mohMessage":{"normalSource":{"enabled":true,"greeting":"DEFAULT","audioAnnouncementFiles":[{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}],"audioPlaylistId":"..."},"alternateSource":{"enabled":true,"greeting":"DEFAULT","audioAnnouncementFiles":[{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}],"audioPlaylistId":"..."}},"waitMessage":{"enabled":true,"waitMode":"TIME","handlingTime":0,"defaultHandlingTime":0,"queuePosition":0,"highVolumeMessageEnabled":true,"estimatedWaitingTime":0,"callbackOptionEnabled":true,"minimumEstimatedCallbackTime":0,"internationalCallbackEnabled":true,"playUpdatedEstimatedWaitMessage":true},"whisperMessage":{"enabled":true,"greeting":"DEFAULT","audioAnnouncementFiles":[{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}]}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_ANNOUNCEMENTS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/{queue_id}/dnis/{dnis_id}/announcements"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if custom_dnis_announcement_settings_enabled is not None:
            body["customDnisAnnouncementSettingsEnabled"] = custom_dnis_announcement_settings_enabled
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
        emit({"status": "updated", "id": dnis_id}, output=output, fields=fields)



@app.command("list-available-numbers-dnis", short_help="Get Available Phone Numbers for DNIS.")
def list_available_numbers_dnis(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter by phone number."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Available Phone Numbers for DNIS.\n\n\b\nExample: wxcli call-queue list-available-numbers-dnis LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/queues/dnis/availableNumbers"
    params = {}
    if phone_number is not None:
        params["phoneNumber"] = phone_number
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_pagination(url=url, params=params, item_key="phoneNumbers"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("phoneNumbers", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('State', 'state'), ('Is Main Number', 'isMainNumber'), ('Telephony Type', 'telephonyType'), ('Toll Free Number', 'tollFreeNumber')], limit=limit)


