import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id, get_cc_base_url, get_cc_org_id


app = typer.Typer(help="Manage Webex Contact Center cc-queue.")


@app.command("list")
def cmd_list(
    filter_param: str = typer.Option(None, "--filter", help="Specify a filter based on which the results will be fetched."),
    channel_types: str = typer.Option(None, "--channel-types", help="[DEPRECATED] Channel type(s) allowed by the system.Separate"),
    attributes: str = typer.Option(None, "--attributes", help="Specify the attributes to be returned. By default, all attri"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create")
def create(
    organization_id: str = typer.Option(None, "--organization-id", help="ID of the contact center organization. This field is require"),
    id_param: str = typer.Option(None, "--id", help="ID of this contact center resource. It should not be specifi"),
    version: str = typer.Option(None, "--version", help="The version of this resource. For a newly created resource,"),
    name: str = typer.Option(None, "--name", help="(required) Name of the Contact Service Queue"),
    description: str = typer.Option(None, "--description", help="(Optional) A short description of the queue."),
    queue_type: str = typer.Option(None, "--queue-type", help="(required) Choices: INBOUND, OUTBOUND"),
    check_agent_availability: bool = typer.Option(None, "--check-agent-availability/--no-check-agent-availability", help="(required) This setting specifies whether the system can exclude teams"),
    channel_type: str = typer.Option(None, "--channel-type", help="(required) Choices: TELEPHONY, EMAIL, FAX, CHAT, VIDEO, OTHERS, SOCIAL_CHANNEL, WORK_ITEM"),
    social_channel_type: str = typer.Option(None, "--social-channel-type", help="Choices: MESSAGEBIRD, MESSENGER, WHATSAPP, APPLE_BUSINESS_CHAT, GOOGLE_BUSINESS_MESSAGES"),
    service_level_threshold: str = typer.Option(None, "--service-level-threshold", help="(required) The time in seconds that a customer request can be in a queu"),
    max_active_contacts: str = typer.Option(None, "--max-active-contacts", help="(required) The maximum number of simultaneous contacts allowed for this"),
    max_time_in_queue: str = typer.Option(None, "--max-time-in-queue", help="(required) The time in seconds after which the system distributes the q"),
    default_music_in_queue_media_file_id: str = typer.Option(None, "--default-music-in-queue-media-file-id", help="Identifies the default audio file which will be played for c"),
    timezone: str = typer.Option(None, "--timezone", help="(Optional) Any routing strategy for this queue uses the time"),
    active: bool = typer.Option(None, "--active/--no-active", help="(required) Specify whether the queue is active or not active"),
    outdial_campaign_enabled: bool = typer.Option(None, "--outdial-campaign-enabled/--no-outdial-campaign-enabled", help="Should be specified only for outdial queues; if enabled, the"),
    monitoring_permitted: bool = typer.Option(None, "--monitoring-permitted/--no-monitoring-permitted", help="Indicates whether or not monitoring is permitted.  This sett"),
    parking_permitted: bool = typer.Option(None, "--parking-permitted/--no-parking-permitted", help="Indicates whether or not parking is permitted.  This setting"),
    recording_permitted: bool = typer.Option(None, "--recording-permitted/--no-recording-permitted", help="Indicates whether or not recording is permitted.  This setti"),
    recording_all_calls_permitted: bool = typer.Option(None, "--recording-all-calls-permitted/--no-recording-all-calls-permitted", help="Indicates whether or not recording all calls is permitted."),
    pause_recording_permitted: bool = typer.Option(None, "--pause-recording-permitted/--no-pause-recording-permitted", help="Indicates whether or not pausing the recording is permitted."),
    recording_pause_duration: str = typer.Option(None, "--recording-pause-duration", help="The duration in seconds of pause in recording.  This setting"),
    control_flow_script_url: str = typer.Option(None, "--control-flow-script-url", help="The URL for the queue or the default control script of the q"),
    ivr_requeue_url: str = typer.Option(None, "--ivr-requeue-url", help="This setting is available only for the Telephony channel typ"),
    overflow_number: str = typer.Option(None, "--overflow-number", help="The destination phone number to which the system distributes"),
    vendor_id: str = typer.Option(None, "--vendor-id", help="The unique alphanumeric string that maps this queue to the v"),
    routing_type: str = typer.Option(None, "--routing-type", help="(required) Choices: LONGEST_AVAILABLE_AGENT, SKILLS_BASED, CIRCULAR, LINEAR"),
    skill_based_routing_type: str = typer.Option(None, "--skill-based-routing-type", help="Choices: LONGEST_AVAILABLE_AGENT, BEST_AVAILABLE_AGENT"),
    queue_routing_type: str = typer.Option(None, "--queue-routing-type", help="(required) Choices: TEAM_BASED, SKILL_BASED, AGENT_BASED"),
    xsp_version: str = typer.Option(None, "--xsp-version", help="(Optional) Used to subscribe for recording events."),
    subscription_id: str = typer.Option(None, "--subscription-id", help="(Optional) Used to subscribe for recording events."),
    system_default: bool = typer.Option(None, "--system-default/--no-system-default", help="Indicates whether the created resource is system created or"),
    manually_assignable: bool = typer.Option(None, "--manually-assignable/--no-manually-assignable", help="If `true`, the queue can be manually assigned."),
    agents_last_updated_by_user_name: str = typer.Option(None, "--agents-last-updated-by-user-name", help="The name of the user who last modified the agents list."),
    agents_last_updated_by_user_email_prefix: str = typer.Option(None, "--agents-last-updated-by-user-email-prefix", help="The email of the user who last modified the agents list."),
    agents_last_updated_time: str = typer.Option(None, "--agents-last-updated-time", help="The date when the agents list was last modified."),
    queue_level_summaries_inclusion: str = typer.Option(None, "--queue-level-summaries-inclusion", help="Queue level summaries inclusion type. Used only when Queue i"),
    queue_level_sentiment_analysis_inclusion: str = typer.Option(None, "--queue-level-sentiment-analysis-inclusion", help="Queue level sentiment analysis inclusion type. Used only whe"),
    queue_level_predicted_wait_time_inclusion: str = typer.Option(None, "--queue-level-predicted-wait-time-inclusion", help="Queue level predicted wait time inclusion type. Used only wh"),
    queue_level_auto_csat_inclusion: str = typer.Option(None, "--queue-level-auto-csat-inclusion", help="Queue level auto CSAT inclusion type. Used only when Queue i"),
    queue_level_real_time_transcriptions_inclusion: str = typer.Option(None, "--queue-level-real-time-transcriptions-inclusion", help="Queue level real time transcriptions inclusion type. Used on"),
    created_time: str = typer.Option(None, "--created-time", help="This is the created time of the entity."),
    last_updated_time: str = typer.Option(None, "--last-updated-time", help="This is the updated time of the entity."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new Contact Service Queue\n\nExample --json-body:\n  '{"name":"...","queueType":"INBOUND","checkAgentAvailability":true,"channelType":"TELEPHONY","serviceLevelThreshold":0,"maxActiveContacts":0,"maxTimeInQueue":0,"active":true}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue"
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
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("create-bulk-contact-service-queue")
def create_bulk_contact_service_queue(
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk save Contact Service Queue(s)\n\nExample --json-body:\n  '{"items":[{"itemIdentifier":"...","item":"...","requestAction":"..."}]}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/bulk"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
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
    """Bulk partial update Contact Service Queue(s)\n\nExample --json-body:\n  '{"items":[{"itemIdentifier":"...","item":"...","requestAction":"..."}]}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/bulk"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_patch(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("list-bulk-export")
def list_bulk_export(
    type_param: str = typer.Option(..., "--type", help="Choices: INBOUND, OUTBOUND"),
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
    orgid = get_cc_org_id(api.session)
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
            handle_rest_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
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
    """List Skill CSQs by Skill Profile."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/by-skill-profile-id/{id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
            handle_rest_error(e)
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("list-internal-by-skill-profile-id")
def list_internal_by_skill_profile_id(
    id: str = typer.Argument(help="id"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Internal Skill CSQs by Profile."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/by-skill-profile-id/{id}/internal"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-internal-by-team-id")
def list_internal_by_team_id(
    id: str = typer.Argument(help="id"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Team CSQs by Team ID."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/by-team-id/{id}/internal"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-internal-by-user-ci-id")
def list_internal_by_user_ci_id(
    ci_user_id: str = typer.Argument(help="ciUserId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Agent CSQs by CI User ID."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/by-user-ci-id/{ci_user_id}/internal"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create-delete-reference")
def create_delete_reference(
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete CSQ References\n\nExample --json-body:\n  '{"references":{}}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/delete-reference"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("create-fetch-by-dynamic-skills-and-skill-profile")
def create_fetch_by_dynamic_skills_and_skill_profile(
    skill_profile_id: str = typer.Option(None, "--skill-profile-id", help="The skill profile ID to filter queues by."),
    user_id: str = typer.Option(None, "--user-id", help="The user ID to filter queues by."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List CSQs by Skills and Profile\n\nExample --json-body:\n  '{"skillProfileId":"...","dynamicSkills":[{"skillId":"...","textValue":"...","booleanValue":"...","proficiencyValue":"...","enumSkillValues":"..."}],"userId":"..."}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/fetch-by-dynamic-skills-and-skillProfile"
    if json_body:
        body = json.loads(json_body)
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
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("create-fetch-by-user-id-skill-profile-id")
def create_fetch_by_user_id_skill_profile_id(
    skill_profile_id: str = typer.Option(None, "--skill-profile-id", help="The skill profile ID to filter queues by."),
    user_id: str = typer.Option(None, "--user-id", help="The user ID to filter queues by."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List CSQs by User and Profile\n\nExample --json-body:\n  '{"skillProfileId":"...","dynamicSkills":[{"skillId":"...","textValue":"...","booleanValue":"...","proficiencyValue":"...","enumSkillValues":"..."}],"userId":"..."}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/fetch-by-userId-skillProfileId"
    if json_body:
        body = json.loads(json_body)
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
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("create-fetch-manually-assignable-queues")
def create_fetch_manually_assignable_queues(
    agent_id: str = typer.Option(None, "--agent-id", help="The ID of the agent to check queue assignments for."),
    team_id: str = typer.Option(None, "--team-id", help="The ID of the team to check queue assignments for."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Manually Assignable CSQs."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/fetch-manually-assignable-queues"
    if json_body:
        body = json.loads(json_body)
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
    orgid = get_cc_org_id(api.session)
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
            handle_rest_error(e)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("list-internal-by-ci-user-id")
def list_internal_by_ci_user_id(
    id: str = typer.Argument(help="id"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Skill CSQs by CI User ID."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/skill-based-queues/by-ci-user-id/{id}/internal"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("show-contact-service-queue-organization")
def show_contact_service_queue_organization(
    id: str = typer.Argument(help="id"),
    agents_updated_info: str = typer.Option(None, "--agents-updated-info", help="If `true`, returns the user details who has last updated the"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
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
    organization_id: str = typer.Option(None, "--organization-id", help="ID of the contact center organization. This field is require"),
    id_param: str = typer.Option(None, "--id", help="ID of this contact center resource. It should not be specifi"),
    version: str = typer.Option(None, "--version", help="The version of this resource. For a newly created resource,"),
    name: str = typer.Option(None, "--name", help="Name of the Contact Service Queue"),
    description: str = typer.Option(None, "--description", help="(Optional) A short description of the queue."),
    queue_type: str = typer.Option(None, "--queue-type", help="Choices: INBOUND, OUTBOUND"),
    check_agent_availability: bool = typer.Option(None, "--check-agent-availability/--no-check-agent-availability", help="This setting specifies whether the system can exclude teams"),
    channel_type: str = typer.Option(None, "--channel-type", help="Choices: TELEPHONY, EMAIL, FAX, CHAT, VIDEO, OTHERS, SOCIAL_CHANNEL, WORK_ITEM"),
    social_channel_type: str = typer.Option(None, "--social-channel-type", help="Choices: MESSAGEBIRD, MESSENGER, WHATSAPP, APPLE_BUSINESS_CHAT, GOOGLE_BUSINESS_MESSAGES"),
    service_level_threshold: str = typer.Option(None, "--service-level-threshold", help="The time in seconds that a customer request can be in a queu"),
    max_active_contacts: str = typer.Option(None, "--max-active-contacts", help="The maximum number of simultaneous contacts allowed for this"),
    max_time_in_queue: str = typer.Option(None, "--max-time-in-queue", help="The time in seconds after which the system distributes the q"),
    default_music_in_queue_media_file_id: str = typer.Option(None, "--default-music-in-queue-media-file-id", help="Identifies the default audio file which will be played for c"),
    timezone: str = typer.Option(None, "--timezone", help="(Optional) Any routing strategy for this queue uses the time"),
    active: bool = typer.Option(None, "--active/--no-active", help="Specify whether the queue is active or not active"),
    outdial_campaign_enabled: bool = typer.Option(None, "--outdial-campaign-enabled/--no-outdial-campaign-enabled", help="Should be specified only for outdial queues; if enabled, the"),
    monitoring_permitted: bool = typer.Option(None, "--monitoring-permitted/--no-monitoring-permitted", help="Indicates whether or not monitoring is permitted.  This sett"),
    parking_permitted: bool = typer.Option(None, "--parking-permitted/--no-parking-permitted", help="Indicates whether or not parking is permitted.  This setting"),
    recording_permitted: bool = typer.Option(None, "--recording-permitted/--no-recording-permitted", help="Indicates whether or not recording is permitted.  This setti"),
    recording_all_calls_permitted: bool = typer.Option(None, "--recording-all-calls-permitted/--no-recording-all-calls-permitted", help="Indicates whether or not recording all calls is permitted."),
    pause_recording_permitted: bool = typer.Option(None, "--pause-recording-permitted/--no-pause-recording-permitted", help="Indicates whether or not pausing the recording is permitted."),
    recording_pause_duration: str = typer.Option(None, "--recording-pause-duration", help="The duration in seconds of pause in recording.  This setting"),
    control_flow_script_url: str = typer.Option(None, "--control-flow-script-url", help="The URL for the queue or the default control script of the q"),
    ivr_requeue_url: str = typer.Option(None, "--ivr-requeue-url", help="This setting is available only for the Telephony channel typ"),
    overflow_number: str = typer.Option(None, "--overflow-number", help="The destination phone number to which the system distributes"),
    vendor_id: str = typer.Option(None, "--vendor-id", help="The unique alphanumeric string that maps this queue to the v"),
    routing_type: str = typer.Option(None, "--routing-type", help="Choices: LONGEST_AVAILABLE_AGENT, SKILLS_BASED, CIRCULAR, LINEAR"),
    skill_based_routing_type: str = typer.Option(None, "--skill-based-routing-type", help="Choices: LONGEST_AVAILABLE_AGENT, BEST_AVAILABLE_AGENT"),
    queue_routing_type: str = typer.Option(None, "--queue-routing-type", help="Choices: TEAM_BASED, SKILL_BASED, AGENT_BASED"),
    xsp_version: str = typer.Option(None, "--xsp-version", help="(Optional) Used to subscribe for recording events."),
    subscription_id: str = typer.Option(None, "--subscription-id", help="(Optional) Used to subscribe for recording events."),
    system_default: bool = typer.Option(None, "--system-default/--no-system-default", help="Indicates whether the created resource is system created or"),
    manually_assignable: bool = typer.Option(None, "--manually-assignable/--no-manually-assignable", help="If `true`, the queue can be manually assigned."),
    agents_last_updated_by_user_name: str = typer.Option(None, "--agents-last-updated-by-user-name", help="The name of the user who last modified the agents list."),
    agents_last_updated_by_user_email_prefix: str = typer.Option(None, "--agents-last-updated-by-user-email-prefix", help="The email of the user who last modified the agents list."),
    agents_last_updated_time: str = typer.Option(None, "--agents-last-updated-time", help="The date when the agents list was last modified."),
    queue_level_summaries_inclusion: str = typer.Option(None, "--queue-level-summaries-inclusion", help="Queue level summaries inclusion type. Used only when Queue i"),
    queue_level_sentiment_analysis_inclusion: str = typer.Option(None, "--queue-level-sentiment-analysis-inclusion", help="Queue level sentiment analysis inclusion type. Used only whe"),
    queue_level_predicted_wait_time_inclusion: str = typer.Option(None, "--queue-level-predicted-wait-time-inclusion", help="Queue level predicted wait time inclusion type. Used only wh"),
    queue_level_auto_csat_inclusion: str = typer.Option(None, "--queue-level-auto-csat-inclusion", help="Queue level auto CSAT inclusion type. Used only when Queue i"),
    queue_level_real_time_transcriptions_inclusion: str = typer.Option(None, "--queue-level-real-time-transcriptions-inclusion", help="Queue level real time transcriptions inclusion type. Used on"),
    created_time: str = typer.Option(None, "--created-time", help="This is the created time of the entity."),
    last_updated_time: str = typer.Option(None, "--last-updated-time", help="This is the updated time of the entity."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update specific Contact Service Queue by ID\n\nExample --json-body:\n  '{"name":"...","queueType":"INBOUND","checkAgentAvailability":true,"channelType":"TELEPHONY","serviceLevelThreshold":0,"maxActiveContacts":0,"maxTimeInQueue":0,"active":true}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/{id}"
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
    typer.echo(f"Updated.")



@app.command("delete")
def delete(
    id: str = typer.Argument(help="id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
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
        api.session.rest_delete(url)
    except WebexError as e:
            handle_rest_error(e)
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
    """List CSQ References by ID."""
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create-bulk-v2")
def create_bulk_v2(
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Bulk save Contact Service Queue(s)\n\nExample --json-body:\n  '{"items":[{"itemIdentifier":"...","item":"...","requestAction":"..."}]}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/contact-service-queue/v2/bulk"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("list-contact-service-queue-v2")
def list_contact_service_queue_v2(
    filter_param: str = typer.Option(None, "--filter", help="Specify a filter based on which the results will be fetched."),
    attributes: str = typer.Option(None, "--attributes", help="Specify the attributes to be returned. By default, all attri"),
    search: str = typer.Option(None, "--search", help="Filter data based on the search keyword.Supported search col"),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts"),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If th"),
    desktop_profile_filter: str = typer.Option(None, "--desktop-profile-filter", help="If set to true, the API will return only the data that the u"),
    provisioning_view: str = typer.Option(None, "--provisioning-view", help="If set to true, the API will only return data that user has"),
    single_object_response: str = typer.Option(None, "--single-object-response", help="Specifiy whether to include array fields in the response, Th"),
    include_ai_mapping_count: str = typer.Option(None, "--include-ai-mapping-count", help="If set to true, the API response will include the count of e"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Contact Service Queue(s)."""
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create-contact-service-queue")
def create_contact_service_queue(
    organization_id: str = typer.Option(None, "--organization-id", help="ID of the contact center organization. This field is require"),
    id_param: str = typer.Option(None, "--id", help="ID of this contact center resource. It should not be specifi"),
    version: str = typer.Option(None, "--version", help="The version of this resource. For a newly created resource,"),
    name: str = typer.Option(None, "--name", help="(required) Name of the Contact Service Queue"),
    description: str = typer.Option(None, "--description", help="(Optional) A short description of the queue."),
    queue_type: str = typer.Option(None, "--queue-type", help="(required) Choices: INBOUND, OUTBOUND"),
    check_agent_availability: bool = typer.Option(None, "--check-agent-availability/--no-check-agent-availability", help="(required) This setting specifies whether the system can exclude teams"),
    channel_type: str = typer.Option(None, "--channel-type", help="(required) Choices: TELEPHONY, EMAIL, FAX, CHAT, VIDEO, OTHERS, SOCIAL_CHANNEL, WORK_ITEM"),
    social_channel_type: str = typer.Option(None, "--social-channel-type", help="Choices: MESSAGEBIRD, MESSENGER, WHATSAPP, APPLE_BUSINESS_CHAT, GOOGLE_BUSINESS_MESSAGES"),
    service_level_threshold: str = typer.Option(None, "--service-level-threshold", help="(required) The time in seconds that a customer request can be in a queu"),
    max_active_contacts: str = typer.Option(None, "--max-active-contacts", help="(required) The maximum number of simultaneous contacts allowed for this"),
    max_time_in_queue: str = typer.Option(None, "--max-time-in-queue", help="(required) The time in seconds after which the system distributes the q"),
    default_music_in_queue_media_file_id: str = typer.Option(None, "--default-music-in-queue-media-file-id", help="Identifies the default audio file which will be played for c"),
    timezone: str = typer.Option(None, "--timezone", help="(Optional) Any routing strategy for this queue uses the time"),
    active: bool = typer.Option(None, "--active/--no-active", help="(required) Specify whether the queue is active or not active"),
    outdial_campaign_enabled: bool = typer.Option(None, "--outdial-campaign-enabled/--no-outdial-campaign-enabled", help="Should be specified only for outdial queues; if enabled, the"),
    monitoring_permitted: bool = typer.Option(None, "--monitoring-permitted/--no-monitoring-permitted", help="Indicates whether or not monitoring is permitted.  This sett"),
    parking_permitted: bool = typer.Option(None, "--parking-permitted/--no-parking-permitted", help="Indicates whether or not parking is permitted.  This setting"),
    recording_permitted: bool = typer.Option(None, "--recording-permitted/--no-recording-permitted", help="Indicates whether or not recording is permitted.  This setti"),
    recording_all_calls_permitted: bool = typer.Option(None, "--recording-all-calls-permitted/--no-recording-all-calls-permitted", help="Indicates whether or not recording all calls is permitted."),
    pause_recording_permitted: bool = typer.Option(None, "--pause-recording-permitted/--no-pause-recording-permitted", help="Indicates whether or not pausing the recording is permitted."),
    recording_pause_duration: str = typer.Option(None, "--recording-pause-duration", help="The duration in seconds of pause in recording.  This setting"),
    control_flow_script_url: str = typer.Option(None, "--control-flow-script-url", help="The URL for the queue or the default control script of the q"),
    ivr_requeue_url: str = typer.Option(None, "--ivr-requeue-url", help="This setting is available only for the Telephony channel typ"),
    overflow_number: str = typer.Option(None, "--overflow-number", help="The destination phone number to which the system distributes"),
    vendor_id: str = typer.Option(None, "--vendor-id", help="The unique alphanumeric string that maps this queue to the v"),
    routing_type: str = typer.Option(None, "--routing-type", help="(required) Choices: LONGEST_AVAILABLE_AGENT, SKILLS_BASED, CIRCULAR, LINEAR"),
    skill_based_routing_type: str = typer.Option(None, "--skill-based-routing-type", help="Choices: LONGEST_AVAILABLE_AGENT, BEST_AVAILABLE_AGENT"),
    queue_routing_type: str = typer.Option(None, "--queue-routing-type", help="(required) Choices: TEAM_BASED, SKILL_BASED, AGENT_BASED"),
    xsp_version: str = typer.Option(None, "--xsp-version", help="(Optional) Used to subscribe for recording events."),
    subscription_id: str = typer.Option(None, "--subscription-id", help="(Optional) Used to subscribe for recording events."),
    system_default: bool = typer.Option(None, "--system-default/--no-system-default", help="Indicates whether the created resource is system created or"),
    manually_assignable: bool = typer.Option(None, "--manually-assignable/--no-manually-assignable", help="If `true`, the queue can be manually assigned."),
    agents_last_updated_by_user_name: str = typer.Option(None, "--agents-last-updated-by-user-name", help="The name of the user who last modified the agents list."),
    agents_last_updated_by_user_email_prefix: str = typer.Option(None, "--agents-last-updated-by-user-email-prefix", help="The email of the user who last modified the agents list."),
    agents_last_updated_time: str = typer.Option(None, "--agents-last-updated-time", help="The date when the agents list was last modified."),
    queue_level_summaries_inclusion: str = typer.Option(None, "--queue-level-summaries-inclusion", help="Queue level summaries inclusion type. Used only when Queue i"),
    queue_level_sentiment_analysis_inclusion: str = typer.Option(None, "--queue-level-sentiment-analysis-inclusion", help="Queue level sentiment analysis inclusion type. Used only whe"),
    queue_level_predicted_wait_time_inclusion: str = typer.Option(None, "--queue-level-predicted-wait-time-inclusion", help="Queue level predicted wait time inclusion type. Used only wh"),
    queue_level_auto_csat_inclusion: str = typer.Option(None, "--queue-level-auto-csat-inclusion", help="Queue level auto CSAT inclusion type. Used only when Queue i"),
    queue_level_real_time_transcriptions_inclusion: str = typer.Option(None, "--queue-level-real-time-transcriptions-inclusion", help="Queue level real time transcriptions inclusion type. Used on"),
    created_time: str = typer.Option(None, "--created-time", help="This is the created time of the entity."),
    last_updated_time: str = typer.Option(None, "--last-updated-time", help="This is the updated time of the entity."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new Contact Service Queue\n\nExample --json-body:\n  '{"name":"...","queueType":"INBOUND","checkAgentAvailability":true,"channelType":"TELEPHONY","serviceLevelThreshold":0,"maxActiveContacts":0,"maxTimeInQueue":0,"active":true}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/v2/contact-service-queue"
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
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
    """List team based Contact Service Queue(s)by user ID."""
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create-fetch-by-grouped-assistant-skill")
def create_fetch_by_grouped_assistant_skill(
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts"),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If th"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List queue mapping summary grouped by Assistant Skill\n\nExample --json-body:\n  '{"assistantSkillIds":["..."]}'."""
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
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("show-contact-service-queue-v2")
def show_contact_service_queue_v2(
    id: str = typer.Argument(help="id"),
    agents_updated_info: str = typer.Option(None, "--agents-updated-info", help="If `true`, returns the user details who has last updated the"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
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
    organization_id: str = typer.Option(None, "--organization-id", help="ID of the contact center organization. This field is require"),
    id_param: str = typer.Option(None, "--id", help="ID of this contact center resource. It should not be specifi"),
    version: str = typer.Option(None, "--version", help="The version of this resource. For a newly created resource,"),
    name: str = typer.Option(None, "--name", help="Name of the Contact Service Queue"),
    description: str = typer.Option(None, "--description", help="(Optional) A short description of the queue."),
    queue_type: str = typer.Option(None, "--queue-type", help="Choices: INBOUND, OUTBOUND"),
    check_agent_availability: bool = typer.Option(None, "--check-agent-availability/--no-check-agent-availability", help="This setting specifies whether the system can exclude teams"),
    channel_type: str = typer.Option(None, "--channel-type", help="Choices: TELEPHONY, EMAIL, FAX, CHAT, VIDEO, OTHERS, SOCIAL_CHANNEL, WORK_ITEM"),
    social_channel_type: str = typer.Option(None, "--social-channel-type", help="Choices: MESSAGEBIRD, MESSENGER, WHATSAPP, APPLE_BUSINESS_CHAT, GOOGLE_BUSINESS_MESSAGES"),
    service_level_threshold: str = typer.Option(None, "--service-level-threshold", help="The time in seconds that a customer request can be in a queu"),
    max_active_contacts: str = typer.Option(None, "--max-active-contacts", help="The maximum number of simultaneous contacts allowed for this"),
    max_time_in_queue: str = typer.Option(None, "--max-time-in-queue", help="The time in seconds after which the system distributes the q"),
    default_music_in_queue_media_file_id: str = typer.Option(None, "--default-music-in-queue-media-file-id", help="Identifies the default audio file which will be played for c"),
    timezone: str = typer.Option(None, "--timezone", help="(Optional) Any routing strategy for this queue uses the time"),
    active: bool = typer.Option(None, "--active/--no-active", help="Specify whether the queue is active or not active"),
    outdial_campaign_enabled: bool = typer.Option(None, "--outdial-campaign-enabled/--no-outdial-campaign-enabled", help="Should be specified only for outdial queues; if enabled, the"),
    monitoring_permitted: bool = typer.Option(None, "--monitoring-permitted/--no-monitoring-permitted", help="Indicates whether or not monitoring is permitted.  This sett"),
    parking_permitted: bool = typer.Option(None, "--parking-permitted/--no-parking-permitted", help="Indicates whether or not parking is permitted.  This setting"),
    recording_permitted: bool = typer.Option(None, "--recording-permitted/--no-recording-permitted", help="Indicates whether or not recording is permitted.  This setti"),
    recording_all_calls_permitted: bool = typer.Option(None, "--recording-all-calls-permitted/--no-recording-all-calls-permitted", help="Indicates whether or not recording all calls is permitted."),
    pause_recording_permitted: bool = typer.Option(None, "--pause-recording-permitted/--no-pause-recording-permitted", help="Indicates whether or not pausing the recording is permitted."),
    recording_pause_duration: str = typer.Option(None, "--recording-pause-duration", help="The duration in seconds of pause in recording.  This setting"),
    control_flow_script_url: str = typer.Option(None, "--control-flow-script-url", help="The URL for the queue or the default control script of the q"),
    ivr_requeue_url: str = typer.Option(None, "--ivr-requeue-url", help="This setting is available only for the Telephony channel typ"),
    overflow_number: str = typer.Option(None, "--overflow-number", help="The destination phone number to which the system distributes"),
    vendor_id: str = typer.Option(None, "--vendor-id", help="The unique alphanumeric string that maps this queue to the v"),
    routing_type: str = typer.Option(None, "--routing-type", help="Choices: LONGEST_AVAILABLE_AGENT, SKILLS_BASED, CIRCULAR, LINEAR"),
    skill_based_routing_type: str = typer.Option(None, "--skill-based-routing-type", help="Choices: LONGEST_AVAILABLE_AGENT, BEST_AVAILABLE_AGENT"),
    queue_routing_type: str = typer.Option(None, "--queue-routing-type", help="Choices: TEAM_BASED, SKILL_BASED, AGENT_BASED"),
    xsp_version: str = typer.Option(None, "--xsp-version", help="(Optional) Used to subscribe for recording events."),
    subscription_id: str = typer.Option(None, "--subscription-id", help="(Optional) Used to subscribe for recording events."),
    system_default: bool = typer.Option(None, "--system-default/--no-system-default", help="Indicates whether the created resource is system created or"),
    manually_assignable: bool = typer.Option(None, "--manually-assignable/--no-manually-assignable", help="If `true`, the queue can be manually assigned."),
    agents_last_updated_by_user_name: str = typer.Option(None, "--agents-last-updated-by-user-name", help="The name of the user who last modified the agents list."),
    agents_last_updated_by_user_email_prefix: str = typer.Option(None, "--agents-last-updated-by-user-email-prefix", help="The email of the user who last modified the agents list."),
    agents_last_updated_time: str = typer.Option(None, "--agents-last-updated-time", help="The date when the agents list was last modified."),
    queue_level_summaries_inclusion: str = typer.Option(None, "--queue-level-summaries-inclusion", help="Queue level summaries inclusion type. Used only when Queue i"),
    queue_level_sentiment_analysis_inclusion: str = typer.Option(None, "--queue-level-sentiment-analysis-inclusion", help="Queue level sentiment analysis inclusion type. Used only whe"),
    queue_level_predicted_wait_time_inclusion: str = typer.Option(None, "--queue-level-predicted-wait-time-inclusion", help="Queue level predicted wait time inclusion type. Used only wh"),
    queue_level_auto_csat_inclusion: str = typer.Option(None, "--queue-level-auto-csat-inclusion", help="Queue level auto CSAT inclusion type. Used only when Queue i"),
    queue_level_real_time_transcriptions_inclusion: str = typer.Option(None, "--queue-level-real-time-transcriptions-inclusion", help="Queue level real time transcriptions inclusion type. Used on"),
    created_time: str = typer.Option(None, "--created-time", help="This is the created time of the entity."),
    last_updated_time: str = typer.Option(None, "--last-updated-time", help="This is the updated time of the entity."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update specific Contact Service Queue by ID\n\nExample --json-body:\n  '{"name":"...","queueType":"INBOUND","checkAgentAvailability":true,"channelType":"TELEPHONY","serviceLevelThreshold":0,"maxActiveContacts":0,"maxTimeInQueue":0,"active":true}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/v2/contact-service-queue/{id}"
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
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/v2/contact-service-queue/{id}/reassign-agents"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("list-contact-service-queue-v3")
def list_contact_service_queue_v3(
    filter_param: str = typer.Option(None, "--filter", help="Specify a filter based on which the results will be fetched."),
    attributes: str = typer.Option(None, "--attributes", help="Specify the attributes to be returned. By default, all attri"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)


