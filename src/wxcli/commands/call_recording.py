import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling call-recording.")


@app.command("show")
def show(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
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
    enabled: bool = typer.Option(None, "--enabled/--no-enabled", help="Whether or not the call recording is enabled."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Call Recording Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/callRecording"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("show-terms-of-service")
def show_terms_of_service(
    vendor_id: str = typer.Argument(help="vendorId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Recording Terms Of Service Settings."""
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
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("update-terms-of-service")
def update_terms_of_service(
    vendor_id: str = typer.Argument(help="vendorId"),
    terms_of_service_enabled: bool = typer.Option(None, "--terms-of-service-enabled/--no-terms-of-service-enabled", help="Whether or not the call recording terms of service are enabl"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Call Recording Terms Of Service Settings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/callRecording/vendors/{vendor_id}/termsOfService"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if terms_of_service_enabled is not None:
            body["termsOfServiceEnabled"] = terms_of_service_enabled
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("show-compliance-announcement-call-recording")
def show_compliance_announcement_call_recording(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
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
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("update-compliance-announcement-call-recording")
def update_compliance_announcement_call_recording(
    inbound_pstn_calls_enabled: bool = typer.Option(None, "--inbound-pstn-calls-enabled/--no-inbound-pstn-calls-enabled", help="Flag to indicate whether the call recording START/STOP annou"),
    outbound_pstn_calls_enabled: bool = typer.Option(None, "--outbound-pstn-calls-enabled/--no-outbound-pstn-calls-enabled", help="Flag to indicate whether the call recording START/STOP annou"),
    outbound_pstn_calls_delay_enabled: bool = typer.Option(None, "--outbound-pstn-calls-delay-enabled/--no-outbound-pstn-calls-delay-enabled", help="Flag to indicate whether compliance announcement is played a"),
    delay_in_seconds: str = typer.Option(None, "--delay-in-seconds", help="Number of seconds to wait before playing the compliance anno"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update the organization Compliance Announcement."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/callRecording/complianceAnnouncement"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
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
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("show-compliance-announcement-call-recording-1")
def show_compliance_announcement_call_recording_1(
    location_id: str = typer.Argument(help="locationId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get details for the Location Compliance Announcement Setting."""
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
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("update-compliance-announcement-call-recording-1")
def update_compliance_announcement_call_recording_1(
    location_id: str = typer.Argument(help="locationId"),
    inbound_pstn_calls_enabled: bool = typer.Option(None, "--inbound-pstn-calls-enabled/--no-inbound-pstn-calls-enabled", help="Flag to indicate whether the Call Recording START/STOP annou"),
    use_org_settings_enabled: bool = typer.Option(None, "--use-org-settings-enabled/--no-use-org-settings-enabled", help="Flag to indicate whether to use the customer level complianc"),
    outbound_pstn_calls_enabled: bool = typer.Option(None, "--outbound-pstn-calls-enabled/--no-outbound-pstn-calls-enabled", help="Flag to indicate whether the Call Recording START/STOP annou"),
    outbound_pstn_calls_delay_enabled: bool = typer.Option(None, "--outbound-pstn-calls-delay-enabled/--no-outbound-pstn-calls-delay-enabled", help="Flag to indicate whether compliance announcement is played a"),
    delay_in_seconds: str = typer.Option(None, "--delay-in-seconds", help="Number of seconds to wait before playing the compliance anno"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update the Location Compliance Announcement."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callRecording/complianceAnnouncement"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
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
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("list")
def cmd_list(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("regions", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-vendor-users-call-recording")
def list_vendor_users_call_recording(
    standard_user_only: str = typer.Option(None, "--standard-user-only", help="If true, results only include Webex Calling standard users."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("members", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('First Name', 'firstName'), ('Last Name', 'lastName')], limit=limit)



@app.command("update-vendor-call-recording")
def update_vendor_call_recording(
    location_id: str = typer.Argument(help="locationId"),
    id_param: str = typer.Option(None, "--id", help="Unique identifier of the call recording vendor."),
    org_default_enabled: bool = typer.Option(None, "--org-default-enabled/--no-org-default-enabled", help="Vendor is enabled by default."),
    storage_region: str = typer.Option(None, "--storage-region", help="Regions where call recordings are stored."),
    org_storage_region_enabled: bool = typer.Option(None, "--org-storage-region-enabled/--no-org-storage-region-enabled", help="Region-based call recording storage is enabled."),
    failure_behavior: str = typer.Option(None, "--failure-behavior", help="Choices: PROCEED_WITH_CALL_NO_ANNOUNCEMENT, PROCEED_CALL_WITH_ANNOUNCEMENT, END_CALL_WITH_ANNOUNCEMENT"),
    org_failure_behavior_enabled: bool = typer.Option(None, "--org-failure-behavior-enabled/--no-org-failure-behavior-enabled", help="Failure behavior is enabled."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Set Call Recording Vendor for a Location\n\nExample --json-body:\n  '{"id":"...","orgDefaultEnabled":true,"storageRegion":"...","orgStorageRegionEnabled":true,"failureBehavior":"PROCEED_WITH_CALL_NO_ANNOUNCEMENT","orgFailureBehaviorEnabled":true}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/locations/{location_id}/callRecording/vendor"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if id_param is not None:
            body["id"] = id_param
        if org_default_enabled is not None:
            body["orgDefaultEnabled"] = org_default_enabled
        if storage_region is not None:
            body["storageRegion"] = storage_region
        if org_storage_region_enabled is not None:
            body["orgStorageRegionEnabled"] = org_storage_region_enabled
        if failure_behavior is not None:
            body["failureBehavior"] = failure_behavior
        if org_failure_behavior_enabled is not None:
            body["orgFailureBehaviorEnabled"] = org_failure_behavior_enabled
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("list-vendors")
def list_vendors(
    location_id: str = typer.Argument(help="locationId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Location Call Recording Vendors."""
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("vendors", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-vendor-users-call-recording-1")
def list_vendor_users_call_recording_1(
    location_id: str = typer.Argument(help="locationId"),
    standard_user_only: str = typer.Option(None, "--standard-user-only", help="If true, results only include Webex Calling standard users."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Call Recording Vendor Users for a Location."""
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("members", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[('ID', 'id'), ('First Name', 'firstName'), ('Last Name', 'lastName')], limit=limit)



@app.command("list-call-recording")
def list_call_recording(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("show-call-recording")
def show_call_recording(
    job_id: str = typer.Argument(help="jobId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get the Job Status of a Call Recording Job."""
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
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("list-errors")
def list_errors(
    job_id: str = typer.Argument(help="jobId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Job Errors for a Call Recording Job."""
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("show-vendors")
def show_vendors(
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
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
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("update-vendor-call-recording-1")
def update_vendor_call_recording_1(
    vendor_id: str = typer.Option(None, "--vendor-id", help="Unique identifier of the vendor."),
    storage_region: str = typer.Option(None, "--storage-region", help="Call recording storage region. Only applicable for Webex as"),
    failure_behavior: str = typer.Option(None, "--failure-behavior", help="Choices: PROCEED_WITH_CALL_NO_ANNOUNCEMENT, PROCEED_CALL_WITH_ANNOUNCEMENT, END_CALL_WITH_ANNOUNCEMENT"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Set Organization Call Recording Vendor\n\nExample --json-body:\n  '{"vendorId":"...","storageRegion":"...","failureBehavior":"PROCEED_WITH_CALL_NO_ANNOUNCEMENT"}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/config/callRecording/vendor"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if vendor_id is not None:
            body["vendorId"] = vendor_id
        if storage_region is not None:
            body["storageRegion"] = storage_region
        if failure_behavior is not None:
            body["failureBehavior"] = failure_behavior
    try:
        result = api.session.rest_put(url, json=body, params=params)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")


