import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling call-recording.")


@app.command("show", short_help="Get Call Recording Settings.")
def show(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Recording Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/callRecording"
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



_BODY_SKELETON_UPDATE = '{"enabled":true}'

@app.command("update", short_help="Update Call Recording Settings.")
def update(
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Whether or not the call recording is enabled."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Call Recording Settings.\n\n\b\nExample: wxcli call-recording update --enabled\n\n\b\nExample --json-body: '{"enabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/callRecording"
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
        emit({"status": "updated"}, output=output, fields=fields)



@app.command("show-terms-of-service", short_help="Get Call Recording Terms Of Service Settings.")
def show_terms_of_service(
    vendor_id: str = typer.Argument(help="Webex RECORDING_VENDOR id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Recording Terms Of Service Settings.\n\n\b\nExample: wxcli call-recording show-terms-of-service VENDOR_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/callRecording/vendors/{vendor_id}/termsOfService"
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



_BODY_SKELETON_UPDATE_TERMS_OF_SERVICE = '{"termsOfServiceEnabled":true}'

@app.command("update-terms-of-service", short_help="Update Call Recording Terms Of Service Settings.")
def update_terms_of_service(
    vendor_id: str = typer.Argument(help="Webex RECORDING_VENDOR id"),
    terms_of_service_enabled: bool = typer.Option(None, "--terms-of-service-enabled/--no-terms-of-service-enabled", help="Whether or not the call recording terms of service are enabled."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Call Recording Terms Of Service Settings.\n\n\b\nExample: wxcli call-recording update-terms-of-service VENDOR_ID --terms-of-service-enabled\n\n\b\nExample --json-body: '{"termsOfServiceEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_TERMS_OF_SERVICE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/callRecording/vendors/{vendor_id}/termsOfService"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if terms_of_service_enabled is not None:
            body["termsOfServiceEnabled"] = terms_of_service_enabled
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
        emit({"status": "updated", "id": vendor_id}, output=output, fields=fields)



@app.command("show-compliance-announcement-call-recording", short_help="Get details for the organization Compliance Announcement Setting.")
def show_compliance_announcement_call_recording(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get details for the organization Compliance Announcement Setting."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/callRecording/complianceAnnouncement"
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



_BODY_SKELETON_UPDATE_COMPLIANCE_ANNOUNCEMENT_CALL_RECORDING = '{"inboundPSTNCallsEnabled":true,"outboundPSTNCallsEnabled":true,"outboundPSTNCallsDelayEnabled":true,"delayInSeconds":0,"useCustomAnnouncementEnabled":true,"audioAnnouncementFileId":"..."}'

@app.command("update-compliance-announcement-call-recording", short_help="Update the organization Compliance Announcement.")
def update_compliance_announcement_call_recording(
    inbound_pstn_calls_enabled: bool = typer.Option(None, "--inbound-pstn-calls-enabled/--no-inbound-pstn-calls-enabled", help="Flag to indicate whether the call recording START/STOP announcement is played to an inbound caller."),
    outbound_pstn_calls_enabled: bool = typer.Option(None, "--outbound-pstn-calls-enabled/--no-outbound-pstn-calls-enabled", help="Flag to indicate whether the call recording START/STOP announcement is played to an outbound caller."),
    outbound_pstn_calls_delay_enabled: bool = typer.Option(None, "--outbound-pstn-calls-delay-enabled/--no-outbound-pstn-calls-delay-enabled", help="Flag to indicate whether compliance announcement is played after a specified delay in seconds."),
    delay_in_seconds: str = typer.Option(None, "--delay-in-seconds", help="Number of seconds to wait before playing the compliance announcement."),
    use_custom_announcement_enabled: bool = typer.Option(None, "--use-custom-announcement-enabled/--no-use-custom-announcement-enabled", help="Flag to indicate whether to use the custom compliance announcement. If true it uses the organization's custom compliance announcement file, and if false default compliance announcement used."),
    audio_announcement_file_id: str = typer.Option(None, "--audio-announcement-file-id", help="Unique identifier for the custom audio announcement file."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update the organization Compliance Announcement.\n\n\b\nExample --json-body: '{"inboundPSTNCallsEnabled":true,"outboundPSTNCallsEnabled":true,"outboundPSTNCallsDelayEnabled":true,"delayInSeconds":0,"useCustomAnnouncementEnabled":true,"audioAnnouncementFileId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_COMPLIANCE_ANNOUNCEMENT_CALL_RECORDING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/callRecording/complianceAnnouncement"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if inbound_pstn_calls_enabled is not None:
            body["inboundPSTNCallsEnabled"] = inbound_pstn_calls_enabled
        if outbound_pstn_calls_enabled is not None:
            body["outboundPSTNCallsEnabled"] = outbound_pstn_calls_enabled
        if outbound_pstn_calls_delay_enabled is not None:
            body["outboundPSTNCallsDelayEnabled"] = outbound_pstn_calls_delay_enabled
        if delay_in_seconds is not None:
            body["delayInSeconds"] = delay_in_seconds
        if use_custom_announcement_enabled is not None:
            body["useCustomAnnouncementEnabled"] = use_custom_announcement_enabled
        if audio_announcement_file_id is not None:
            body["audioAnnouncementFileId"] = audio_announcement_file_id
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
        emit({"status": "updated"}, output=output, fields=fields)



@app.command("show-compliance-announcement-call-recording-1", short_help="Get details for the Location Compliance Announcement Setting.")
def show_compliance_announcement_call_recording_1(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get details for the Location Compliance Announcement Setting.\n\n\b\nExample: wxcli call-recording show-compliance-announcement-call-recording-1 LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callRecording/complianceAnnouncement"
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



_BODY_SKELETON_UPDATE_COMPLIANCE_ANNOUNCEMENT_CALL_RECORDING_1 = '{"inboundPSTNCallsEnabled":true,"useOrgSettingsEnabled":true,"outboundPSTNCallsEnabled":true,"outboundPSTNCallsDelayEnabled":true,"delayInSeconds":0,"useOrgLevelAnnouncementEnabled":true,"customComplianceAnnouncement":{"type":"CUSTOM","audioAnnouncementFileId":"..."}}'

@app.command("update-compliance-announcement-call-recording-1", short_help="Update the Location Compliance Announcement.")
def update_compliance_announcement_call_recording_1(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    inbound_pstn_calls_enabled: bool = typer.Option(None, "--inbound-pstn-calls-enabled/--no-inbound-pstn-calls-enabled", help="Flag to indicate whether the Call Recording START/STOP announcement is played to an inbound caller."),
    use_org_settings_enabled: bool = typer.Option(None, "--use-org-settings-enabled/--no-use-org-settings-enabled", help="Flag to indicate whether to use the customer level compliance announcement default settings."),
    outbound_pstn_calls_enabled: bool = typer.Option(None, "--outbound-pstn-calls-enabled/--no-outbound-pstn-calls-enabled", help="Flag to indicate whether the Call Recording START/STOP announcement is played to an outbound caller."),
    outbound_pstn_calls_delay_enabled: bool = typer.Option(None, "--outbound-pstn-calls-delay-enabled/--no-outbound-pstn-calls-delay-enabled", help="Flag to indicate whether compliance announcement is played after a specified delay in seconds."),
    delay_in_seconds: str = typer.Option(None, "--delay-in-seconds", help="Number of seconds to wait before playing the compliance announcement."),
    use_org_level_announcement_enabled: bool = typer.Option(None, "--use-org-level-announcement-enabled/--no-use-org-level-announcement-enabled", help="Flag to indicate whether to use the organization level custom compliance announcement. If this flag is set to true, takes the organization's announcement setting. If this flag is set to false, takes the location's custom announcement."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update the Location Compliance Announcement.\n\n\b\nExample: wxcli call-recording update-compliance-announcement-call-recording-1 LOCATION_ID\n\n\b\nExample --json-body: '{"inboundPSTNCallsEnabled":true,"useOrgSettingsEnabled":true,"outboundPSTNCallsEnabled":true,"outboundPSTNCallsDelayEnabled":true,"delayInSeconds":0,"useOrgLevelAnnouncementEnabled":true,"customComplianceAnnouncement":{"type":"CUSTOM","audioAnnouncementFileId":"..."}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_COMPLIANCE_ANNOUNCEMENT_CALL_RECORDING_1), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callRecording/complianceAnnouncement"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if inbound_pstn_calls_enabled is not None:
            body["inboundPSTNCallsEnabled"] = inbound_pstn_calls_enabled
        if use_org_settings_enabled is not None:
            body["useOrgSettingsEnabled"] = use_org_settings_enabled
        if outbound_pstn_calls_enabled is not None:
            body["outboundPSTNCallsEnabled"] = outbound_pstn_calls_enabled
        if outbound_pstn_calls_delay_enabled is not None:
            body["outboundPSTNCallsDelayEnabled"] = outbound_pstn_calls_delay_enabled
        if delay_in_seconds is not None:
            body["delayInSeconds"] = delay_in_seconds
        if use_org_level_announcement_enabled is not None:
            body["useOrgLevelAnnouncementEnabled"] = use_org_level_announcement_enabled
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
        emit({"status": "updated", "id": location_id}, output=output, fields=fields)



@app.command("list", short_help="Get Call Recording Regions.")
def cmd_list(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Recording Regions."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/callRecording/regions"
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
    items = result.get("regions", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Name', 'name'), ('Code', 'code'), ('Default Enabled', 'defaultEnabled')], limit=limit)



@app.command("list-vendor-users-call-recording", short_help="Get Call Recording Vendor Users.")
def list_vendor_users_call_recording(
    standard_user_only: str = typer.Option(None, "--standard-user-only", help="If true, results only include Webex Calling standard users."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Recording Vendor Users."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/callRecording/vendorUsers"
    params = {}
    if standard_user_only is not None:
        params["standardUserOnly"] = standard_user_only
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
            result = list(api.session.follow_pagination(url=url, params=params, item_key="members"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("members", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('First Name', 'firstName'), ('Last Name', 'lastName')], limit=limit)



_BODY_SKELETON_UPDATE_VENDOR_CALL_RECORDING = '{"id":"...","orgDefaultEnabled":true,"failureBehavior":{},"orgFailureBehaviorEnabled":true}'

@app.command("update-vendor-call-recording", short_help="Set Call Recording Vendor for a Location.")
def update_vendor_call_recording(
    location_id: str = typer.Argument(help="Webex RECORDING_VENDOR id, from: wxcli location-settings list-calling-details"),
    id_param: str = typer.Option(None, "--id", help="Unique identifier of the call recording vendor."),
    org_default_enabled: bool = typer.Option(None, "--org-default-enabled/--no-org-default-enabled", help="Vendor is enabled by default."),
    failure_behavior: str = typer.Option(None, "--failure-behavior", help="Type of failure behavior."),
    org_failure_behavior_enabled: bool = typer.Option(None, "--org-failure-behavior-enabled/--no-org-failure-behavior-enabled", help="Failure behavior is enabled."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Set Call Recording Vendor for a Location.\n\n\b\nExample: wxcli call-recording update-vendor-call-recording LOCATION_ID\n\n\b\nExample --json-body: '{"id":"...","orgDefaultEnabled":true,"failureBehavior":{},"orgFailureBehaviorEnabled":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_VENDOR_CALL_RECORDING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callRecording/vendor"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if id_param is not None:
            body["id"] = id_param
        if org_default_enabled is not None:
            body["orgDefaultEnabled"] = org_default_enabled
        if failure_behavior is not None:
            body["failureBehavior"] = failure_behavior
        if org_failure_behavior_enabled is not None:
            body["orgFailureBehaviorEnabled"] = org_failure_behavior_enabled
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
        emit({"status": "updated", "id": location_id}, output=output, fields=fields)



@app.command("list-vendors", short_help="Get Location Call Recording Vendors.")
def list_vendors(
    location_id: str = typer.Argument(help="Webex RECORDING_VENDOR id, from: wxcli location-settings list-calling-details"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Location Call Recording Vendors.\n\n\b\nExample: wxcli call-recording list-vendors LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callRecording/vendors"
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
    items = result.get("vendors", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Description', 'description'), ('Migrate User Creation Enabled', 'migrateUserCreationEnabled'), ('Login URL', 'loginUrl')], limit=limit)



@app.command("list-vendor-users-call-recording-1", short_help="Get Call Recording Vendor Users for a Location.")
def list_vendor_users_call_recording_1(
    location_id: str = typer.Argument(help="Webex RECORDING_VENDOR id, from: wxcli location-settings list-calling-details"),
    standard_user_only: str = typer.Option(None, "--standard-user-only", help="If true, results only include Webex Calling standard users."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Recording Vendor Users for a Location.\n\n\b\nExample: wxcli call-recording list-vendor-users-call-recording-1 LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callRecording/vendorUsers"
    params = {}
    if standard_user_only is not None:
        params["standardUserOnly"] = standard_user_only
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
            result = list(api.session.follow_pagination(url=url, params=params, item_key="members"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("members", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('First Name', 'firstName'), ('Last Name', 'lastName')], limit=limit)



@app.command("list-call-recording", short_help="List Call Recording Jobs.")
def list_call_recording(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Call Recording Jobs."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/callRecording"
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
        if all_pages:
            result = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Tracking ID', 'trackingId'), ('Source User ID', 'sourceUserId'), ('Source Customer ID', 'sourceCustomerId')], limit=limit)



@app.command("show-call-recording", short_help="Get the Job Status of a Call Recording Job.")
def show_call_recording(
    job_id: str = typer.Argument(help="Webex JOB_ID id, from: wxcli call-recording list-call-recording"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get the Job Status of a Call Recording Job.\n\n\b\nExample: wxcli call-recording show-call-recording JOB_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/callRecording/{job_id}"
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



@app.command("list-errors", short_help="Get Job Errors for a Call Recording Job.")
def list_errors(
    job_id: str = typer.Argument(help="Webex JOB_ID id, from: wxcli call-recording list-call-recording"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Job Errors for a Call Recording Job.\n\n\b\nExample: wxcli call-recording list-errors JOB_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/jobs/callRecording/{job_id}/errors"
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
        if all_pages:
            result = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Tracking ID', 'trackingId'), ('Item', 'item'), ('Item Number', 'itemNumber')], limit=limit)



@app.command("show-vendors", short_help="Get Organization Call Recording Vendors.")
def show_vendors(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Organization Call Recording Vendors."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/callRecording/vendors"
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



_BODY_SKELETON_UPDATE_VENDOR_CALL_RECORDING_1 = '{"vendorId":"...","failureBehavior":{}}'

@app.command("update-vendor-call-recording-1", short_help="Set Organization Call Recording Vendor.")
def update_vendor_call_recording_1(
    vendor_id: str = typer.Option(None, "--vendor-id", help="Unique identifier of the vendor."),
    failure_behavior: str = typer.Option(None, "--failure-behavior", help="Call recording failure behavior."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Set Organization Call Recording Vendor.\n\n\b\nExample: wxcli call-recording update-vendor-call-recording-1 --vendor-id VENDOR_ID\n\n\b\nExample --json-body: '{"vendorId":"...","failureBehavior":{}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_VENDOR_CALL_RECORDING_1), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/callRecording/vendor"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if vendor_id is not None:
            body["vendorId"] = vendor_id
        if failure_behavior is not None:
            body["failureBehavior"] = failure_behavior
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
        emit({"status": "updated"}, output=output, fields=fields)



@app.command("show-announcements-call-recording", short_help="Get Organization Call Recording Announcement Settings.")
def show_announcements_call_recording(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Organization Call Recording Announcement Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/callRecording/announcements"
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



_BODY_SKELETON_UPDATE_ANNOUNCEMENTS_CALL_RECORDING = '{"start":{"type":"CUSTOM","audioAnnouncementFileId":"..."},"stop":{"type":"CUSTOM","audioAnnouncementFileId":"..."},"pause":{"type":"CUSTOM","audioAnnouncementFileId":"..."},"resume":{"type":"CUSTOM","audioAnnouncementFileId":"..."},"failureEndWithCall":{"type":"CUSTOM","audioAnnouncementFileId":"..."},"failureProceedWithCall":{"type":"CUSTOM","audioAnnouncementFileId":"..."}}'

@app.command("update-announcements-call-recording", short_help="Update Organization Call Recording Announcement Settings.")
def update_announcements_call_recording(
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Organization Call Recording Announcement Settings.\n\n\b\nExample --json-body: '{"start":{"type":"CUSTOM","audioAnnouncementFileId":"..."},"stop":{"type":"CUSTOM","audioAnnouncementFileId":"..."},"pause":{"type":"CUSTOM","audioAnnouncementFileId":"..."},"resume":{"type":"CUSTOM","audioAnnouncementFileId":"..."},"failureEndWithCall":{"type":"CUSTOM","audioAnnouncementFileId":"..."},"failureProceedWithCall":{"type":"CUSTOM","audioAnnouncementFileId":"..."}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_ANNOUNCEMENTS_CALL_RECORDING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/callRecording/announcements"
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
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated"}, output=output, fields=fields)



@app.command("show-announcements-call-recording-1", short_help="Get Location Call Recording Announcement Settings.")
def show_announcements_call_recording_1(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Location Call Recording Announcement Settings.\n\n\b\nExample: wxcli call-recording show-announcements-call-recording-1 LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callRecording/announcements"
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



_BODY_SKELETON_UPDATE_ANNOUNCEMENTS_CALL_RECORDING_1 = '{"useOrgLevelAnnouncementEnabled":true,"start":{"type":"CUSTOM","audioAnnouncementFileId":"..."},"stop":{"type":"CUSTOM","audioAnnouncementFileId":"..."},"pause":{"type":"CUSTOM","audioAnnouncementFileId":"..."},"resume":{"type":"CUSTOM","audioAnnouncementFileId":"..."},"failureEndWithCall":{"type":"CUSTOM","audioAnnouncementFileId":"..."},"failureProceedWithCall":{"type":"CUSTOM","audioAnnouncementFileId":"..."}}'

@app.command("update-announcements-call-recording-1", short_help="Update Location Call Recording Announcement Settings.")
def update_announcements_call_recording_1(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    use_org_level_announcement_enabled: bool = typer.Option(None, "--use-org-level-announcement-enabled/--no-use-org-level-announcement-enabled", help="Flag to indicate whether to use the organization level call recording announcement settings. If the flag is set to true, indicates that the callRecordingAnnouncementSelection setting is inherited from the organization-level configuration. If the flag is set to false, indicates that the..."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Location Call Recording Announcement Settings.\n\n\b\nExample: wxcli call-recording update-announcements-call-recording-1 LOCATION_ID\n\n\b\nExample --json-body: '{"useOrgLevelAnnouncementEnabled":true,"start":{"type":"CUSTOM","audioAnnouncementFileId":"..."},"stop":{"type":"CUSTOM","audioAnnouncementFileId":"..."},"pause":{"type":"CUSTOM","audioAnnouncementFileId":"..."},"resume":{"type":"CUSTOM","audioAnnouncementFileId":"..."},"failureEndWithCall":{"type":"CUSTOM","audioAnnouncementFileId":"..."},"failureProceedWithCall":{"type":"CUSTOM","audioAnnouncementFileId":"..."}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_ANNOUNCEMENTS_CALL_RECORDING_1), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callRecording/announcements"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if use_org_level_announcement_enabled is not None:
            body["useOrgLevelAnnouncementEnabled"] = use_org_level_announcement_enabled
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
        emit({"status": "updated", "id": location_id}, output=output, fields=fields)


