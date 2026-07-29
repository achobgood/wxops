import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling auto-attendant.")


@app.command("list", short_help="Read the List of Auto Attendants.")
def cmd_list(
    location_id: str = typer.Option(None, "--location-id", help="Return the list of auto attendants for this location."),
    name: str = typer.Option(None, "--name", help="Only return auto attendants with the matching name."),
    phone_number: str = typer.Option(None, "--phone-number", help="Only return auto attendants with the matching phone number."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Auto Attendants."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/autoAttendants"
    params = {}
    if location_id is not None:
        params["locationId"] = location_id
    if name is not None:
        params["name"] = name
    if phone_number is not None:
        params["phoneNumber"] = phone_number
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
            items = result.get("autoAttendants", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="autoAttendants"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Extension', 'extension'), ('Location', 'locationName'), ('Phone Number', 'phoneNumber')], limit=limit)



@app.command("show", short_help="Get Details for an Auto Attendant.")
def show(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    auto_attendant_id: str = typer.Argument(help="Webex AUTO_ATTENDANT id, from: wxcli auto-attendant list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Details for an Auto Attendant.\n\n\b\nExample: wxcli auto-attendant show LOCATION_ID AUTO_ATTENDANT_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/autoAttendants/{auto_attendant_id}"
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



_BODY_SKELETON_UPDATE = '{"name":"...","phoneNumber":"...","extension":"...","firstName":"...","lastName":"...","alternateNumbers":[{"phoneNumber":"...","ringPattern":"NORMAL","tollFreeNumber":true}],"languageCode":"...","businessSchedule":"...","holidaySchedule":"...","extensionDialing":"ENTERPRISE","nameDialing":"ENTERPRISE","timeZone":"...","businessHoursMenu":{"greeting":"DEFAULT","extensionEnabled":true,"keyConfigurations":{"key":"0","action":"PLAY_ANNOUNCEMENT","description":"...","value":"...","audioAnnouncementFile":{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}},"audioAnnouncementFile":{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"},"callTreatment":{"retryAttemptForNoInput":"NO_REPEAT","noInputTimer":"...","actionToBePerformed":{"action":"PLAY_MESSAGE_AND_DISCONNECT","greeting":"DEFAULT","audioAnnouncementFile":{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"},"transferCallTo":"..."}}},"afterHoursMenu":{"greeting":"DEFAULT","extensionEnabled":true,"keyConfigurations":{"key":"0","action":"PLAY_ANNOUNCEMENT","description":"...","value":"...","audioAnnouncementFile":{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}},"audioAnnouncementFile":{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"},"callTreatment":{"retryAttemptForNoInput":"NO_REPEAT","noInputTimer":"...","actionToBePerformed":{"action":"PLAY_MESSAGE_AND_DISCONNECT","greeting":"DEFAULT","audioAnnouncementFile":{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"},"transferCallTo":"..."}}},"directLineCallerIdName":{"selection":"CUSTOM_NAME","customName":"..."},"dialByName":"..."}'

@app.command("update", short_help="Update an Auto Attendant.")
def update(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    auto_attendant_id: str = typer.Argument(help="Webex AUTO_ATTENDANT id, from: wxcli auto-attendant list"),
    name: str = typer.Option(None, "--name", help="Unique name for the auto attendant."),
    phone_number: str = typer.Option(None, "--phone-number", help="Auto attendant phone number. Either `phoneNumber` or `extension` is mandatory."),
    extension: str = typer.Option(None, "--extension", help="Auto attendant extension. Either `phoneNumber` or `extension` is mandatory."),
    first_name: str = typer.Option(None, "--first-name", help="First name defined for an auto attendant. This field has been deprecated. Please use `directLineCallerIdName` and `dialByName` instead."),
    last_name: str = typer.Option(None, "--last-name", help="Last name defined for an auto attendant. This field has been deprecated. Please use `directLineCallerIdName` and `dialByName` instead."),
    language_code: str = typer.Option(None, "--language-code", help="Announcement language code for the auto attendant."),
    business_schedule: str = typer.Option(None, "--business-schedule", help="Business hours defined for the auto attendant."),
    holiday_schedule: str = typer.Option(None, "--holiday-schedule", help="Holiday defined for the auto attendant."),
    extension_dialing: str = typer.Option(None, "--extension-dialing", help="Choices: ENTERPRISE, GROUP"),
    name_dialing: str = typer.Option(None, "--name-dialing", help="Choices: ENTERPRISE, GROUP"),
    time_zone: str = typer.Option(None, "--time-zone", help="Time zone defined for the auto attendant."),
    dial_by_name: str = typer.Option(None, "--dial-by-name", help="Sets or clears the name to be used for dial by name functions. To clear the `dialByName`, the attribute must be set to null or empty string. Characters of `%`, `+`, `\\`, `\"` and Unicode characters are not allowed."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update an Auto Attendant.\n\n\b\nExample: wxcli auto-attendant update LOCATION_ID AUTO_ATTENDANT_ID\n\n\b\nExample --json-body: '{"name":"...","phoneNumber":"...","extension":"...","firstName":"...","lastName":"...","alternateNumbers":[{"phoneNumber":"...","ringPattern":"NORMAL","tollFreeNumber":true}],"languageCode":"...","businessSchedule":"...","holidaySchedule":"...","extensionDialing":"ENTERPRISE","nameDialing":"ENTERPRISE","timeZone":"...","businessHoursMenu":{"greeting":"DEFAULT","extensionEnabled":true,"keyConfigurations":{"key":"0","action":"PLAY_ANNOUNCEMENT","description":"...","value":"...","audioAnnouncementFile":{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}},"audioAnnouncementFile":{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"},"callTreatment":{"retryAttemptForNoInput":"NO_REPEAT","noInputTimer":"...","actionToBePerformed":{"action":"PLAY_MESSAGE_AND_DISCONNECT","greeting":"DEFAULT","audioAnnouncementFile":{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"},"transferCallTo":"..."}}},"afterHoursMenu":{"greeting":"DEFAULT","extensionEnabled":true,"keyConfigurations":{"key":"0","action":"PLAY_ANNOUNCEMENT","description":"...","value":"...","audioAnnouncementFile":{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}},"audioAnnouncementFile":{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"},"callTreatment":{"retryAttemptForNoInput":"NO_REPEAT","noInputTimer":"...","actionToBePerformed":{"action":"PLAY_MESSAGE_AND_DISCONNECT","greeting":"DEFAULT","audioAnnouncementFile":{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"},"transferCallTo":"..."}}},"directLineCallerIdName":{"selection":"CUSTOM_NAME","customName":"..."},"dialByName":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/autoAttendants/{auto_attendant_id}"
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
        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
        if language_code is not None:
            body["languageCode"] = language_code
        if business_schedule is not None:
            body["businessSchedule"] = business_schedule
        if holiday_schedule is not None:
            body["holidaySchedule"] = holiday_schedule
        if extension_dialing is not None:
            body["extensionDialing"] = extension_dialing
        if name_dialing is not None:
            body["nameDialing"] = name_dialing
        if time_zone is not None:
            body["timeZone"] = time_zone
        if dial_by_name is not None:
            body["dialByName"] = dial_by_name
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
        emit({"status": "updated", "id": auto_attendant_id}, output=output, fields=fields)



@app.command("delete", short_help="Delete an Auto Attendant.")
def delete(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    auto_attendant_id: str = typer.Argument(help="Webex AUTO_ATTENDANT id, from: wxcli auto-attendant list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete an Auto Attendant.\n\n\b\nExample: wxcli auto-attendant delete LOCATION_ID AUTO_ATTENDANT_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {auto_attendant_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/autoAttendants/{auto_attendant_id}"
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
        typer.echo(f"Deleted: {auto_attendant_id}")
    else:
        emit({"status": "deleted", "id": auto_attendant_id}, output=output, fields=fields)



_BODY_SKELETON_CREATE = '{"name":"...","businessSchedule":"...","businessHoursMenu":{"greeting":"DEFAULT","extensionEnabled":true,"keyConfigurations":{"key":"0","action":"PLAY_ANNOUNCEMENT","description":"...","value":"...","audioAnnouncementFile":{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}},"audioAnnouncementFile":{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"},"callTreatment":{"retryAttemptForNoInput":"NO_REPEAT","noInputTimer":"...","actionToBePerformed":{"action":"PLAY_MESSAGE_AND_DISCONNECT","greeting":"DEFAULT","audioAnnouncementFile":{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"},"transferCallTo":"..."}}},"afterHoursMenu":{"greeting":"DEFAULT","extensionEnabled":true,"keyConfigurations":{"key":"0","action":"PLAY_ANNOUNCEMENT","description":"...","value":"...","audioAnnouncementFile":{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}},"audioAnnouncementFile":{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"},"callTreatment":{"retryAttemptForNoInput":"NO_REPEAT","noInputTimer":"...","actionToBePerformed":{"action":"PLAY_MESSAGE_AND_DISCONNECT","greeting":"DEFAULT","audioAnnouncementFile":{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"},"transferCallTo":"..."}}},"phoneNumber":"...","extension":"...","firstName":"...","lastName":"...","alternateNumbers":[{"phoneNumber":"...","ringPattern":"NORMAL","tollFreeNumber":true}],"languageCode":"...","holidaySchedule":"...","extensionDialing":"ENTERPRISE","nameDialing":"ENTERPRISE","timeZone":"...","directLineCallerIdName":{"selection":"CUSTOM_NAME","customName":"..."},"dialByName":"..."}'

@app.command("create", short_help="Create an Auto Attendant.")
def create(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    name: str = typer.Option(None, "--name", help="(required) Unique name for the auto attendant."),
    phone_number: str = typer.Option(None, "--phone-number", help="Auto attendant phone number. Either `phoneNumber` or `extension` is mandatory."),
    extension: str = typer.Option(None, "--extension", help="Auto attendant extension. Either `phoneNumber` or `extension` is mandatory."),
    first_name: str = typer.Option(None, "--first-name", help="First name defined for an auto attendant. This field has been deprecated. Please use `directLineCallerIdName` and `dialByName` instead."),
    last_name: str = typer.Option(None, "--last-name", help="Last name defined for an auto attendant. This field has been deprecated. Please use `directLineCallerIdName` and `dialByName` instead."),
    language_code: str = typer.Option(None, "--language-code", help="Announcement language code for the auto attendant."),
    business_schedule: str = typer.Option(None, "--business-schedule", help="(required) Business hours defined for the auto attendant."),
    holiday_schedule: str = typer.Option(None, "--holiday-schedule", help="Holiday defined for the auto attendant."),
    extension_dialing: str = typer.Option(None, "--extension-dialing", help="Choices: ENTERPRISE, GROUP"),
    name_dialing: str = typer.Option(None, "--name-dialing", help="Choices: ENTERPRISE, GROUP"),
    time_zone: str = typer.Option(None, "--time-zone", help="Time zone defined for the auto attendant."),
    dial_by_name: str = typer.Option(None, "--dial-by-name", help="The name to be used for dial by name functions. Characters of `%`, `+`, `\\`, `\"` and Unicode characters are not allowed."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create an Auto Attendant.\n\n\b\nExample: wxcli auto-attendant create LOCATION_ID --json-body '{"name":"...","businessSchedule":"...","businessHoursMenu":{"greeting":"DEFAULT","extensionEnabled":true,"keyConfigurations":{"key":"0","action":"PLAY_ANNOUNCEMENT"}},"afterHoursMenu":{"greeting":"DEFAULT","extensionEnabled":true,"keyConfigurations":{"key":"0","action":"PLAY_ANNOUNCEMENT"}}}'\n\n\b\nExample --json-body: '{"name":"...","businessSchedule":"...","businessHoursMenu":{"greeting":"DEFAULT","extensionEnabled":true,"keyConfigurations":{"key":"0","action":"PLAY_ANNOUNCEMENT","description":"...","value":"...","audioAnnouncementFile":{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}},"audioAnnouncementFile":{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"},"callTreatment":{"retryAttemptForNoInput":"NO_REPEAT","noInputTimer":"...","actionToBePerformed":{"action":"PLAY_MESSAGE_AND_DISCONNECT","greeting":"DEFAULT","audioAnnouncementFile":{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"},"transferCallTo":"..."}}},"afterHoursMenu":{"greeting":"DEFAULT","extensionEnabled":true,"keyConfigurations":{"key":"0","action":"PLAY_ANNOUNCEMENT","description":"...","value":"...","audioAnnouncementFile":{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"}},"audioAnnouncementFile":{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"},"callTreatment":{"retryAttemptForNoInput":"NO_REPEAT","noInputTimer":"...","actionToBePerformed":{"action":"PLAY_MESSAGE_AND_DISCONNECT","greeting":"DEFAULT","audioAnnouncementFile":{"id":"...","fileName":"...","mediaFileType":"WAV","level":"ORGANIZATION"},"transferCallTo":"..."}}},"phoneNumber":"...","extension":"...","firstName":"...","lastName":"...","alternateNumbers":[{"phoneNumber":"...","ringPattern":"NORMAL","tollFreeNumber":true}],"languageCode":"...","holidaySchedule":"...","extensionDialing":"ENTERPRISE","nameDialing":"ENTERPRISE","timeZone":"...","directLineCallerIdName":{"selection":"CUSTOM_NAME","customName":"..."},"dialByName":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/autoAttendants"
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
        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
        if language_code is not None:
            body["languageCode"] = language_code
        if business_schedule is not None:
            body["businessSchedule"] = business_schedule
        if holiday_schedule is not None:
            body["holidaySchedule"] = holiday_schedule
        if extension_dialing is not None:
            body["extensionDialing"] = extension_dialing
        if name_dialing is not None:
            body["nameDialing"] = name_dialing
        if time_zone is not None:
            body["timeZone"] = time_zone
        if dial_by_name is not None:
            body["dialByName"] = dial_by_name
        _missing = [f for f in ['name', 'businessSchedule'] if f not in body or body[f] is None]
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



@app.command("show-call-forwarding", short_help="Get Call Forwarding Settings for an Auto Attendant.")
def show_call_forwarding(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    auto_attendant_id: str = typer.Argument(help="Webex AUTO_ATTENDANT id, from: wxcli auto-attendant list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Forwarding Settings for an Auto Attendant.\n\n\b\nExample: wxcli auto-attendant show-call-forwarding LOCATION_ID AUTO_ATTENDANT_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/autoAttendants/{auto_attendant_id}/callForwarding"
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



_BODY_SKELETON_UPDATE_CALL_FORWARDING = '{"callForwarding":{"always":{"enabled":true,"destination":"...","ringReminderEnabled":true,"sendToVoicemailEnabled":true},"selective":{"enabled":true,"destination":"...","ringReminderEnabled":true,"sendToVoicemailEnabled":true},"rules":[{"id":"...","enabled":true}],"operatingModes":{"enabled":true,"modes":[{"normalOperationEnabled":true,"id":"...","forwardTo":{"selection":"FORWARD_TO_DEFAULT_NUMBER","destination":"...","destinationVoicemailEnabled":true}}]}}}'

@app.command("update-call-forwarding", short_help="Update Call Forwarding Settings for an Auto Attendant.")
def update_call_forwarding(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    auto_attendant_id: str = typer.Argument(help="Webex AUTO_ATTENDANT id, from: wxcli auto-attendant list"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Call Forwarding Settings for an Auto Attendant.\n\n\b\nExample: wxcli auto-attendant update-call-forwarding LOCATION_ID AUTO_ATTENDANT_ID --json-body '{"callForwarding":{"always":{"enabled":true,"destination":"...","ringReminderEnabled":true,"sendToVoicemailEnabled":true},"selective":{"enabled":true,"destination":"...","ringReminderEnabled":true,"sendToVoicemailEnabled":true},"rules":[{"id":"..."}],"operatingModes":{"enabled":true,"modes":[{"normalOperationEnabled":true,"id":"...","forwardTo":{"selection":"FORWARD_TO_DEFAULT_NUMBER"}}]}}}'\n\n\b\nExample --json-body: '{"callForwarding":{"always":{"enabled":true,"destination":"...","ringReminderEnabled":true,"sendToVoicemailEnabled":true},"selective":{"enabled":true,"destination":"...","ringReminderEnabled":true,"sendToVoicemailEnabled":true},"rules":[{"id":"...","enabled":true}],"operatingModes":{"enabled":true,"modes":[{"normalOperationEnabled":true,"id":"...","forwardTo":{"selection":"FORWARD_TO_DEFAULT_NUMBER","destination":"...","destinationVoicemailEnabled":true}}]}}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CALL_FORWARDING), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/autoAttendants/{auto_attendant_id}/callForwarding"
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
        emit({"status": "updated", "id": auto_attendant_id}, output=output, fields=fields)



_BODY_SKELETON_CREATE_SELECTIVE_RULES = '{"name":"...","forwardTo":{"selection":"FORWARD_TO_DEFAULT_NUMBER","phoneNumber":"..."},"callsFrom":{"selection":"ANY","customNumbers":{"privateNumberEnabled":true,"unavailableNumberEnabled":true,"numbers":["..."]}},"enabled":true,"businessSchedule":"...","holidaySchedule":"...","callsTo":{"numbers":[{"type":"PRIMARY","phoneNumber":"...","extension":"..."}]}}'

@app.command("create-selective-rules", short_help="Create a Selective Call Forwarding Rule for an Auto Attendant.")
def create_selective_rules(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    auto_attendant_id: str = typer.Argument(help="Webex AUTO_ATTENDANT id, from: wxcli auto-attendant list"),
    name: str = typer.Option(None, "--name", help="(required) Unique name for the selective rule in the auto attendant."),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Reflects if rule is enabled."),
    business_schedule: str = typer.Option(None, "--business-schedule", help="Name of the location's business schedule which determines when this selective call forwarding rule is in effect."),
    holiday_schedule: str = typer.Option(None, "--holiday-schedule", help="Name of the location's holiday schedule which determines when this selective call forwarding rule is in effect."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Selective Call Forwarding Rule for an Auto Attendant.\n\n\b\nExample: wxcli auto-attendant create-selective-rules LOCATION_ID AUTO_ATTENDANT_ID --json-body '{"name":"...","forwardTo":{"selection":"FORWARD_TO_DEFAULT_NUMBER"},"callsFrom":{"selection":"ANY"}}'\n\n\b\nExample --json-body: '{"name":"...","forwardTo":{"selection":"FORWARD_TO_DEFAULT_NUMBER","phoneNumber":"..."},"callsFrom":{"selection":"ANY","customNumbers":{"privateNumberEnabled":true,"unavailableNumberEnabled":true,"numbers":["..."]}},"enabled":true,"businessSchedule":"...","holidaySchedule":"...","callsTo":{"numbers":[{"type":"PRIMARY","phoneNumber":"...","extension":"..."}]}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_SELECTIVE_RULES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/autoAttendants/{auto_attendant_id}/callForwarding/selectiveRules"
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
        if business_schedule is not None:
            body["businessSchedule"] = business_schedule
        if holiday_schedule is not None:
            body["holidaySchedule"] = holiday_schedule
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



@app.command("show-selective-rules", short_help="Get Selective Call Forwarding Rule for an Auto Attendant.")
def show_selective_rules(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    auto_attendant_id: str = typer.Argument(help="Webex AUTO_ATTENDANT id, from: wxcli auto-attendant list"),
    rule_id: str = typer.Argument(help="Webex CALL_FORWARDING_SELECTIVE_RULE id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Selective Call Forwarding Rule for an Auto Attendant.\n\n\b\nExample: wxcli auto-attendant show-selective-rules LOCATION_ID AUTO_ATTENDANT_ID RULE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/autoAttendants/{auto_attendant_id}/callForwarding/selectiveRules/{rule_id}"
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



_BODY_SKELETON_UPDATE_SELECTIVE_RULES = '{"name":"...","enabled":true,"businessSchedule":"...","holidaySchedule":"...","forwardTo":{"selection":"FORWARD_TO_DEFAULT_NUMBER","phoneNumber":"..."},"callsFrom":{"selection":"ANY","customNumbers":{"privateNumberEnabled":true,"unavailableNumberEnabled":true,"numbers":["..."]}},"callsTo":{"numbers":[{"type":"PRIMARY","phoneNumber":"...","extension":"..."}]}}'

@app.command("update-selective-rules", short_help="Update Selective Call Forwarding Rule for an Auto Attendant.")
def update_selective_rules(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    auto_attendant_id: str = typer.Argument(help="Webex AUTO_ATTENDANT id, from: wxcli auto-attendant list"),
    rule_id: str = typer.Argument(help="Webex CALL_FORWARDING_SELECTIVE_RULE id"),
    name: str = typer.Option(None, "--name", help="Unique name for the selective rule in the auto attendant."),
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Reflects if rule is enabled."),
    business_schedule: str = typer.Option(None, "--business-schedule", help="Name of the location's business schedule which determines when this selective call forwarding rule is in effect."),
    holiday_schedule: str = typer.Option(None, "--holiday-schedule", help="Name of the location's holiday schedule which determines when this selective call forwarding rule is in effect."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Selective Call Forwarding Rule for an Auto Attendant.\n\n\b\nExample: wxcli auto-attendant update-selective-rules LOCATION_ID AUTO_ATTENDANT_ID RULE_ID --name NAME\n\n\b\nExample --json-body: '{"name":"...","enabled":true,"businessSchedule":"...","holidaySchedule":"...","forwardTo":{"selection":"FORWARD_TO_DEFAULT_NUMBER","phoneNumber":"..."},"callsFrom":{"selection":"ANY","customNumbers":{"privateNumberEnabled":true,"unavailableNumberEnabled":true,"numbers":["..."]}},"callsTo":{"numbers":[{"type":"PRIMARY","phoneNumber":"...","extension":"..."}]}}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SELECTIVE_RULES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/autoAttendants/{auto_attendant_id}/callForwarding/selectiveRules/{rule_id}"
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
        if business_schedule is not None:
            body["businessSchedule"] = business_schedule
        if holiday_schedule is not None:
            body["holidaySchedule"] = holiday_schedule
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
        emit({"status": "updated", "id": rule_id}, output=output, fields=fields)



@app.command("delete-selective-rules", short_help="Delete a Selective Call Forwarding Rule for an Auto Attendant.")
def delete_selective_rules(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    auto_attendant_id: str = typer.Argument(help="Webex AUTO_ATTENDANT id, from: wxcli auto-attendant list"),
    rule_id: str = typer.Argument(help="Webex CALL_FORWARDING_SELECTIVE_RULE id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Selective Call Forwarding Rule for an Auto Attendant.\n\n\b\nExample: wxcli auto-attendant delete-selective-rules LOCATION_ID AUTO_ATTENDANT_ID RULE_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {rule_id}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/autoAttendants/{auto_attendant_id}/callForwarding/selectiveRules/{rule_id}"
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



@app.command("list-available-numbers-auto-attendants", short_help="Get Auto Attendant Primary Available Phone Numbers.")
def list_available_numbers_auto_attendants(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter phone numbers based on the comma-separated list provided in the `phoneNumber` array."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Auto Attendant Primary Available Phone Numbers.\n\n\b\nExample: wxcli auto-attendant list-available-numbers-auto-attendants LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/autoAttendants/availableNumbers"
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
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('State', 'state'), ('Telephony Type', 'telephonyType'), ('Toll Free', 'tollFreeNumber')], limit=limit)



@app.command("list-available-numbers-alternate", short_help="Get Auto Attendant Alternate Available Phone Numbers.")
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
    """Get Auto Attendant Alternate Available Phone Numbers.\n\n\b\nExample: wxcli auto-attendant list-available-numbers-alternate LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/autoAttendants/alternate/availableNumbers"
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
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('State', 'state'), ('Telephony Type', 'telephonyType'), ('Toll Free', 'tollFreeNumber')], limit=limit)



@app.command("list-available-numbers-call-forwarding", short_help="Get Auto Attendant Call Forward Available Phone Numbers.")
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
    """Get Auto Attendant Call Forward Available Phone Numbers.\n\n\b\nExample: wxcli auto-attendant list-available-numbers-call-forwarding LOCATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/autoAttendants/callForwarding/availableNumbers"
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
    emit(items, output=output, fields=fields, columns=[('Phone Number', 'phoneNumber'), ('Extension', 'extension'), ('State', 'state'), ('Owner Type', 'owner.type'), ('Owner Name', 'owner.firstName')], limit=limit)



@app.command("switch-mode-for", short_help="Switch Mode for Call Forwarding Settings for an Auto Attendant.")
def switch_mode_for(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    auto_attendant_id: str = typer.Argument(help="Webex AUTO_ATTENDANT id, from: wxcli auto-attendant list"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Switch Mode for Call Forwarding Settings for an Auto Attendant.\n\n\b\nExample: wxcli auto-attendant switch-mode-for LOCATION_ID AUTO_ATTENDANT_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/autoAttendants/{auto_attendant_id}/callForwarding/actions/switchMode/invoke"
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



@app.command("delete-announcements", short_help="Delete a Auto Attendant Announcement File.")
def delete_announcements(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    auto_attendant_id: str = typer.Argument(help="Webex CALL_QUEUE id, from: wxcli auto-attendant list"),
    file_name: str = typer.Argument(help="from: wxcli auto-attendant list-announcements"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Auto Attendant Announcement File.\n\n\b\nExample: wxcli auto-attendant delete-announcements LOCATION_ID AUTO_ATTENDANT_ID FILE_NAME"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {file_name}?", abort=True)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/autoAttendants/{auto_attendant_id}/announcements/{file_name}"
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



@app.command("list-announcements", short_help="Read the List of Auto Attendant Announcement Files.")
def list_announcements(
    location_id: str = typer.Argument(help="Webex LOCATION id, from: wxcli location-settings list-calling-details"),
    auto_attendant_id: str = typer.Argument(help="Webex CALL_QUEUE id, from: wxcli auto-attendant list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Read the List of Auto Attendant Announcement Files.\n\n\b\nExample: wxcli auto-attendant list-announcements LOCATION_ID AUTO_ATTENDANT_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/autoAttendants/{auto_attendant_id}/announcements"
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
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('File Name', 'fileName'), ('Level', 'level'), ('Media Type', 'mediaFileType')], limit=limit)


