import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import resolve_org_id, get_cc_base_url, get_cc_org_id
from wxcli.common import verify_write


app = typer.Typer(help="Manage Webex Contact Center cc-tenant-config.")


@app.command("list", short_help="List Tenant Configuration.")
def cmd_list(
    filter_param: str = typer.Option(None, "--filter", help="Specify a filter based on which the results will be fetched. Supported filterable fields: id. The examples below show some search queries - id==\"57efb0e6-5af0-4245-a67d-d3c5045cdb6e\" - id!=\"57efb0e6-5af0-4245-a67d-d3c5045cdb6e\" -..."),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Tenant Configuration."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/tenant-configuration"
    params = {}
    if filter_param is not None:
        params["filter"] = filter_param
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



@app.command("show", short_help="Get specific Tenant Configuration by ID.")
def show(
    id: str = typer.Argument(help="UUID, from: wxcli cc-tenant-config list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get specific Tenant Configuration by ID.\n\n\b\nExample: wxcli cc-tenant-config show ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/tenant-configuration/{id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"timeoutRonaTelephonySeconds":0,"timeoutRonaSocialSeconds":0,"timeoutRonaChatSeconds":0,"timeoutRonaEmailSeconds":0,"organizationId":"...","id":"...","version":0,"outdialEnabled":true,"centralLogLevel":"...","autoWrapUpInterval":0,"localDiskLogLevel":"...","dnOtherDescription":"...","dnDefaultDescription":"...","notRespondingToAvailableTimeout":0,"heartBeatInterval":0,"callVariablesSuppressed":"...","endCallEnabled":true,"incidentReportingEnabled":true,"watsonAnalyticsPassword":"...","systemRecoveryMsg":"...","watsonAnalyticsBaseUrl":"...","dnTargetStripChars":"...","watsonAnalyticsUserName":"...","dnOtherRegex":"...","configurationVersion":0,"callVariablesBaseUrl":"...","lostConnectionRecoveryTimeout":0,"diagnosticsPostUrl":"...","dnDefaultRegex":"...","apsUrl":"...","endConsultEnabled":true,"rejectDuplicateDn":true,"dnTargetRegex":"...","forceDefaultDn":true,"dnDefaultPrefix":"...","privacyShieldVisible":true,"consoleLogLevel":"...","dnTargetPrefix":"...","autoBaseUrl":true,"dnOtherPrefix":"...","dnDefaultStripChars":"...","missedHeartBeatsAllowed":0,"dnOtherStripChars":"...","apsEnabled":true,"timeoutDesktopInactivityEnabled":true,"timeoutDesktopInactivityMins":0,"timeoutRonaWorkItemSeconds":0,"timeoutRonaCustomMessagingSeconds":0,"systemDefault":true,"createdTime":0,"lastUpdatedTime":0}'

@app.command("update", short_help="Update specific Tenant Configuration by ID.")
def update(
    id: str = typer.Argument(help="UUID, from: wxcli cc-tenant-config list"),
    organization_id: str = typer.Option(None, "--organization-id", help="ID of the contact center organization. This field is required for all bulk save operations. User-token updates are not permitted for this field."),
    id_param: str = typer.Option(None, "--id", help="ID of this contact center resource. It should not be specified when creating a new resource. However, it is mandatory when updating a resource."),
    version: str = typer.Option(None, "--version", help="The version of this resource. For a newly created resource, it will be 0 unless specified otherwise."),
    outdial_enabled: bool = typer.Option(None, "--outdial-enabled/--no-outdial-enabled", help="Outdial Enabled. User-token updates are not permitted for this field."),
    central_log_level: str = typer.Option(None, "--central-log-level", help="Central Log Level. User-token updates are not permitted for this field."),
    auto_wrap_up_interval: str = typer.Option(None, "--auto-wrap-up-interval", help="Auto Wrap Up Interval. User-token updates are permitted for this field when authorized by the required scope and User Profile permission."),
    local_disk_log_level: str = typer.Option(None, "--local-disk-log-level", help="Local Disk Log Level. User-token updates are not permitted for this field."),
    dn_other_description: str = typer.Option(None, "--dn-other-description", help="Dn Other Description. User-token updates are not permitted for this field."),
    dn_default_description: str = typer.Option(None, "--dn-default-description", help="Dn Default Description. User-token updates are not permitted for this field."),
    not_responding_to_available_timeout: str = typer.Option(None, "--not-responding-to-available-timeout", help="Not Responding To Available Timeout. User-token updates are not permitted for this field."),
    heart_beat_interval: str = typer.Option(None, "--heart-beat-interval", help="Heart Beat Interval. User-token updates are not permitted for this field."),
    call_variables_suppressed: str = typer.Option(None, "--call-variables-suppressed", help="Call Variables Suppressed. User-token updates are not permitted for this field."),
    end_call_enabled: bool = typer.Option(None, "--end-call-enabled/--no-end-call-enabled", help="End Call Enabled. User-token updates are permitted for this field when authorized by the required scope and User Profile permission."),
    incident_reporting_enabled: bool = typer.Option(None, "--incident-reporting-enabled/--no-incident-reporting-enabled", help="Incident Reporting Enabled. User-token updates are not permitted for this field."),
    watson_analytics_password: str = typer.Option(None, "--watson-analytics-password", help="Watson Analytics Password. User-token updates are not permitted for this field."),
    system_recovery_msg: str = typer.Option(None, "--system-recovery-msg", help="System Recovery Msg. User-token updates are not permitted for this field."),
    watson_analytics_base_url: str = typer.Option(None, "--watson-analytics-base-url", help="Watson Analytics Base Url. User-token updates are not permitted for this field."),
    dn_target_strip_chars: str = typer.Option(None, "--dn-target-strip-chars", help="Dn Target Strip Chars. User-token updates are not permitted for this field."),
    watson_analytics_user_name: str = typer.Option(None, "--watson-analytics-user-name", help="Watson Analytics User Name. User-token updates are not permitted for this field."),
    dn_other_regex: str = typer.Option(None, "--dn-other-regex", help="Dn Other Regex. User-token updates are not permitted for this field."),
    configuration_version: str = typer.Option(None, "--configuration-version", help="Configuration Version. User-token updates are not permitted for this field."),
    call_variables_base_url: str = typer.Option(None, "--call-variables-base-url", help="Call Variables Base Url. User-token updates are not permitted for this field."),
    lost_connection_recovery_timeout: str = typer.Option(None, "--lost-connection-recovery-timeout", help="Lost Connection Recovery Timeout. User-token updates are permitted for this field when authorized by the required scope and User Profile permission."),
    diagnostics_post_url: str = typer.Option(None, "--diagnostics-post-url", help="Diagnostics Post Url. User-token updates are not permitted for this field."),
    dn_default_regex: str = typer.Option(None, "--dn-default-regex", help="Dn Default Regex. User-token updates are not permitted for this field."),
    aps_url: str = typer.Option(None, "--aps-url", help="Aps Url. User-token updates are not permitted for this field."),
    end_consult_enabled: bool = typer.Option(None, "--end-consult-enabled/--no-end-consult-enabled", help="End Consult Enabled. User-token updates are permitted for this field when authorized by the required scope and User Profile permission."),
    reject_duplicate_dn: bool = typer.Option(None, "--reject-duplicate-dn/--no-reject-duplicate-dn", help="Reject Duplicate Dn. User-token updates are not permitted for this field."),
    dn_target_regex: str = typer.Option(None, "--dn-target-regex", help="Dn Target Regex. User-token updates are not permitted for this field."),
    force_default_dn: bool = typer.Option(None, "--force-default-dn/--no-force-default-dn", help="Force Default Dn. User-token updates are permitted for this field when authorized by the required scope and User Profile permission."),
    dn_default_prefix: str = typer.Option(None, "--dn-default-prefix", help="Dn Default Prefix. User-token updates are not permitted for this field."),
    privacy_shield_visible: bool = typer.Option(None, "--privacy-shield-visible/--no-privacy-shield-visible", help="Privacy Shield Visible. User-token updates are permitted for this field when authorized by the required scope and User Profile permission."),
    console_log_level: str = typer.Option(None, "--console-log-level", help="Console Log Level. User-token updates are not permitted for this field."),
    dn_target_prefix: str = typer.Option(None, "--dn-target-prefix", help="Dn Target Prefix. User-token updates are not permitted for this field."),
    auto_base_url: bool = typer.Option(None, "--auto-base-url/--no-auto-base-url", help="Auto Base Url. User-token updates are not permitted for this field."),
    dn_other_prefix: str = typer.Option(None, "--dn-other-prefix", help="Dn Other Prefix. User-token updates are not permitted for this field."),
    dn_default_strip_chars: str = typer.Option(None, "--dn-default-strip-chars", help="Dn Default Strip Chars. User-token updates are not permitted for this field."),
    missed_heart_beats_allowed: str = typer.Option(None, "--missed-heart-beats-allowed", help="Missed Heart Beats Allowed. User-token updates are not permitted for this field."),
    dn_other_strip_chars: str = typer.Option(None, "--dn-other-strip-chars", help="Dn Other Strip Chars. User-token updates are not permitted for this field."),
    aps_enabled: bool = typer.Option(None, "--aps-enabled/--no-aps-enabled", help="Aps Enabled. User-token updates are not permitted for this field."),
    timeout_desktop_inactivity_enabled: bool = typer.Option(None, "--timeout-desktop-inactivity-enabled/--no-timeout-desktop-inactivity-enabled", help="Timeout Desktop Inactivity Enabled. User-token updates are permitted for this field when authorized by the required scope and User Profile permission."),
    timeout_desktop_inactivity_mins: str = typer.Option(None, "--timeout-desktop-inactivity-mins", help="Timeout Desktop Inactivity Mins. User-token updates are permitted for this field when authorized by the required scope and User Profile permission."),
    timeout_rona_telephony_seconds: str = typer.Option(None, "--timeout-rona-telephony-seconds", help="Timeout Rona Telephony Seconds. User-token updates are permitted for this field when authorized by the required scope and User Profile permission."),
    timeout_rona_social_seconds: str = typer.Option(None, "--timeout-rona-social-seconds", help="Timeout Rona Social Seconds. User-token updates are permitted for this field when authorized by the required scope and User Profile permission."),
    timeout_rona_chat_seconds: str = typer.Option(None, "--timeout-rona-chat-seconds", help="Timeout Rona Chat Seconds. User-token updates are permitted for this field when authorized by the required scope and User Profile permission."),
    timeout_rona_email_seconds: str = typer.Option(None, "--timeout-rona-email-seconds", help="Timeout Rona Email Seconds. User-token updates are permitted for this field when authorized by the required scope and User Profile permission."),
    timeout_rona_work_item_seconds: str = typer.Option(None, "--timeout-rona-work-item-seconds", help="RONA timeout for work items in seconds. Valid range: 1-6000. Only applicable when wxcc_digital_work_item feature flag is enabled. User-token updates are permitted for this field when authorized by the required scope and User Profile permission."),
    timeout_rona_custom_messaging_seconds: str = typer.Option(None, "--timeout-rona-custom-messaging-seconds", help="RONA timeout for custom messaging in seconds. Valid range: 1-6000. Only applicable when wxcc_digital_byoc feature flag is enabled. User-token updates are not permitted for this field."),
    system_default: bool = typer.Option(None, "--system-default/--no-system-default", help="Indicates whether the created resource is system created or not User-token updates are not permitted for this field."),
    created_time: str = typer.Option(None, "--created-time", help="This is the created time of the entity. User-token updates are not permitted for this field."),
    last_updated_time: str = typer.Option(None, "--last-updated-time", help="This is the updated time of the entity. User-token updates are not permitted for this field."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update specific Tenant Configuration by ID.\n\n\b\nExample: wxcli cc-tenant-config update ID --timeout-rona-telephony-seconds TIMEOUT_RONA_TELEPHONY_SECONDS --timeout-rona-social-seconds TIMEOUT_RONA_SOCIAL_SECONDS --timeout-rona-chat-seconds TIMEOUT_RONA_CHAT_SECONDS --timeout-rona-email-seconds TIMEOUT_RONA_EMAIL_SECONDS\n\n\b\nExample --json-body: '{"timeoutRonaTelephonySeconds":0,"timeoutRonaSocialSeconds":0,"timeoutRonaChatSeconds":0,"timeoutRonaEmailSeconds":0,"organizationId":"...","id":"...","version":0,"outdialEnabled":true,"centralLogLevel":"...","autoWrapUpInterval":0,"localDiskLogLevel":"...","dnOtherDescription":"...","dnDefaultDescription":"...","notRespondingToAvailableTimeout":0,"heartBeatInterval":0,"callVariablesSuppressed":"...","endCallEnabled":true,"incidentReportingEnabled":true,"watsonAnalyticsPassword":"...","systemRecoveryMsg":"...","watsonAnalyticsBaseUrl":"...","dnTargetStripChars":"...","watsonAnalyticsUserName":"...","dnOtherRegex":"...","configurationVersion":0,"callVariablesBaseUrl":"...","lostConnectionRecoveryTimeout":0,"diagnosticsPostUrl":"...","dnDefaultRegex":"...","apsUrl":"...","endConsultEnabled":true,"rejectDuplicateDn":true,"dnTargetRegex":"...","forceDefaultDn":true,"dnDefaultPrefix":"...","privacyShieldVisible":true,"consoleLogLevel":"...","dnTargetPrefix":"...","autoBaseUrl":true,"dnOtherPrefix":"...","dnDefaultStripChars":"...","missedHeartBeatsAllowed":0,"dnOtherStripChars":"...","apsEnabled":true,"timeoutDesktopInactivityEnabled":true,"timeoutDesktopInactivityMins":0,"timeoutRonaWorkItemSeconds":0,"timeoutRonaCustomMessagingSeconds":0,"systemDefault":true,"createdTime":0,"lastUpdatedTime":0}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/tenant-configuration/{id}"
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
        if outdial_enabled is not None:
            body["outdialEnabled"] = outdial_enabled
        if central_log_level is not None:
            body["centralLogLevel"] = central_log_level
        if auto_wrap_up_interval is not None:
            body["autoWrapUpInterval"] = auto_wrap_up_interval
        if local_disk_log_level is not None:
            body["localDiskLogLevel"] = local_disk_log_level
        if dn_other_description is not None:
            body["dnOtherDescription"] = dn_other_description
        if dn_default_description is not None:
            body["dnDefaultDescription"] = dn_default_description
        if not_responding_to_available_timeout is not None:
            body["notRespondingToAvailableTimeout"] = not_responding_to_available_timeout
        if heart_beat_interval is not None:
            body["heartBeatInterval"] = heart_beat_interval
        if call_variables_suppressed is not None:
            body["callVariablesSuppressed"] = call_variables_suppressed
        if end_call_enabled is not None:
            body["endCallEnabled"] = end_call_enabled
        if incident_reporting_enabled is not None:
            body["incidentReportingEnabled"] = incident_reporting_enabled
        if watson_analytics_password is not None:
            body["watsonAnalyticsPassword"] = watson_analytics_password
        if system_recovery_msg is not None:
            body["systemRecoveryMsg"] = system_recovery_msg
        if watson_analytics_base_url is not None:
            body["watsonAnalyticsBaseUrl"] = watson_analytics_base_url
        if dn_target_strip_chars is not None:
            body["dnTargetStripChars"] = dn_target_strip_chars
        if watson_analytics_user_name is not None:
            body["watsonAnalyticsUserName"] = watson_analytics_user_name
        if dn_other_regex is not None:
            body["dnOtherRegex"] = dn_other_regex
        if configuration_version is not None:
            body["configurationVersion"] = configuration_version
        if call_variables_base_url is not None:
            body["callVariablesBaseUrl"] = call_variables_base_url
        if lost_connection_recovery_timeout is not None:
            body["lostConnectionRecoveryTimeout"] = lost_connection_recovery_timeout
        if diagnostics_post_url is not None:
            body["diagnosticsPostUrl"] = diagnostics_post_url
        if dn_default_regex is not None:
            body["dnDefaultRegex"] = dn_default_regex
        if aps_url is not None:
            body["apsUrl"] = aps_url
        if end_consult_enabled is not None:
            body["endConsultEnabled"] = end_consult_enabled
        if reject_duplicate_dn is not None:
            body["rejectDuplicateDn"] = reject_duplicate_dn
        if dn_target_regex is not None:
            body["dnTargetRegex"] = dn_target_regex
        if force_default_dn is not None:
            body["forceDefaultDn"] = force_default_dn
        if dn_default_prefix is not None:
            body["dnDefaultPrefix"] = dn_default_prefix
        if privacy_shield_visible is not None:
            body["privacyShieldVisible"] = privacy_shield_visible
        if console_log_level is not None:
            body["consoleLogLevel"] = console_log_level
        if dn_target_prefix is not None:
            body["dnTargetPrefix"] = dn_target_prefix
        if auto_base_url is not None:
            body["autoBaseUrl"] = auto_base_url
        if dn_other_prefix is not None:
            body["dnOtherPrefix"] = dn_other_prefix
        if dn_default_strip_chars is not None:
            body["dnDefaultStripChars"] = dn_default_strip_chars
        if missed_heart_beats_allowed is not None:
            body["missedHeartBeatsAllowed"] = missed_heart_beats_allowed
        if dn_other_strip_chars is not None:
            body["dnOtherStripChars"] = dn_other_strip_chars
        if aps_enabled is not None:
            body["apsEnabled"] = aps_enabled
        if timeout_desktop_inactivity_enabled is not None:
            body["timeoutDesktopInactivityEnabled"] = timeout_desktop_inactivity_enabled
        if timeout_desktop_inactivity_mins is not None:
            body["timeoutDesktopInactivityMins"] = timeout_desktop_inactivity_mins
        if timeout_rona_telephony_seconds is not None:
            body["timeoutRonaTelephonySeconds"] = timeout_rona_telephony_seconds
        if timeout_rona_social_seconds is not None:
            body["timeoutRonaSocialSeconds"] = timeout_rona_social_seconds
        if timeout_rona_chat_seconds is not None:
            body["timeoutRonaChatSeconds"] = timeout_rona_chat_seconds
        if timeout_rona_email_seconds is not None:
            body["timeoutRonaEmailSeconds"] = timeout_rona_email_seconds
        if timeout_rona_work_item_seconds is not None:
            body["timeoutRonaWorkItemSeconds"] = timeout_rona_work_item_seconds
        if timeout_rona_custom_messaging_seconds is not None:
            body["timeoutRonaCustomMessagingSeconds"] = timeout_rona_custom_messaging_seconds
        if system_default is not None:
            body["systemDefault"] = system_default
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



@app.command("list-tenant-configuration", short_help="List Tenant Configuration.")
def list_tenant_configuration(
    filter_param: str = typer.Option(None, "--filter", help="Specify a filter based on which the results will be fetched. All the fields are supported except: organizationId, createdTime, lastUpdatedTime The examples below show some search queries - id==\"57efb0e6-5af0-4245-a67d-d3c5045cdb6e\" - id!=\"57efb0e6-5af0-4245-a67d-d3c5045cdb6e\" -..."),
    attributes: str = typer.Option(None, "--attributes", help="Specify the attributes to be returned. By default, all attributes are returned along with the specified columns. All attributes are supported."),
    search: str = typer.Option(None, "--search", help="Filter data based on the search keyword.Supported search columns(name) The examples below show some search queries - \"Cisco\" - field==\"name\";value==\"Cisco\" - fields=in=(\"name\");value==\"Cisco\""),
    page: str = typer.Option(None, "--page", help="Defines the number of displayed page. The page number starts from 0."),
    page_size: str = typer.Option(None, "--page-size", help="Defines the number of items to be displayed on a page. If the number specified is more than allowed max page size, the API will automatically adjust the page size to the max page size."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Tenant Configuration."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    orgid = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{orgid}/v2/tenant-configuration"
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


