import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_cc_base_url


app = typer.Typer(help="Manage Webex Contact Center cc-contact-list.")


_BODY_SKELETON_CREATE = '{"supportedChannels":["Voice"],"activationTimeLagMinutes":0,"activationDateTime":"..."}'

@app.command("create", short_help="Create contact list.")
def create(
    campaign_id: str = typer.Argument(help="e.g. CCV_123456789"),
    activation_time_lag_minutes: str = typer.Option(None, "--activation-time-lag-minutes", help="Contact list activation time lag in minutes (0 = immediate activation, 180 = 3 hours delay). Required if activationDateTime is not provided."),
    activation_date_time: str = typer.Option(None, "--activation-date-time", help="Contact list activation DateTimeStamp (format: YYYY-MM-DDTHH:MM). Required if activationTimeLagMinutes is not provided."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create contact list.\n\n\b\nExample: wxcli cc-contact-list create CCV_123456789 --json-body '{"supportedChannels":["Voice"]}'\n\n\b\nExample --json-body: '{"supportedChannels":["Voice"],"activationTimeLagMinutes":0,"activationDateTime":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v3/campaign-management/campaigns/{campaign_id}/contact-list"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if activation_time_lag_minutes is not None:
            body["activationTimeLagMinutes"] = activation_time_lag_minutes
        if activation_date_time is not None:
            body["activationDateTime"] = activation_date_time
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if output == "id":
        if isinstance(result, dict) and "contactListId" in result:
            typer.echo(f"Created: {result['contactListId']}")
        elif isinstance(result, dict) and "id" in result:
            typer.echo(f"Created: {result['id']}")
        elif not result or result == {}:
            typer.echo("Created.")
        else:
            print_json(result)
    else:
        emit(result, output=output, fields=fields)



_BODY_SKELETON_CREATE_CONTACTS = '{"contacts":[{"contactAttributes":[{"fieldName":"...","value":"..."}]}]}'

@app.command("create-contacts", short_help="Create contacts within a contact list.")
def create_contacts(
    campaign_id: str = typer.Argument(help="e.g. CCV_123456789"),
    contact_list_id: str = typer.Argument(help="contactListId"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create contacts within a contact list.\n\n\b\nExample: wxcli cc-contact-list create-contacts CCV_123456789 CONTACT_LIST_ID\n\n\b\nExample --json-body: '{"contacts":[{"contactAttributes":[{"fieldName":"...","value":"..."}]}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_CONTACTS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v3/campaign-management/campaigns/{campaign_id}/contact-list/{contact_list_id}/contacts"
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



_BODY_SKELETON_UPDATE = '{"contactStatus":"CLOSED"}'

@app.command("update", short_help="Update a contact's status within a contact list.")
def update(
    campaign_id: str = typer.Argument(help="e.g. CCV_123456789"),
    contact_list_id: str = typer.Argument(help="contactListId"),
    contact_id: str = typer.Argument(help="e.g. CUST12345"),
    contact_status: str = typer.Option(None, "--contact-status", help="Choices: CLOSED"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a contact's status within a contact list.\n\n\b\nExample: wxcli cc-contact-list update CCV_123456789 CONTACT_LIST_ID CUST12345\n\n\b\nExample --json-body: '{"contactStatus":"CLOSED"}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v3/campaign-management/campaigns/{campaign_id}/contact-list/{contact_list_id}/contacts/{contact_id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if contact_status is not None:
            body["contactStatus"] = contact_status
    try:
        result = api.session.rest_patch(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": contact_id}, output=output, fields=fields)



_BODY_SKELETON_UPDATE_CONTACTS = '{"contactStatus":"CLOSED","searchAcrossTheCampaignChain":"yes"}'

@app.command("update-contacts", short_help="Update contact status across the campaign chain.")
def update_contacts(
    campaign_id: str = typer.Argument(help="e.g. CCV_1234567890"),
    contact_id: str = typer.Argument(help="contactId"),
    contact_list_id: str = typer.Option(None, "--contact-list-id", help="Optional. Search only the specific contact-list within the campaign specified in the request path. If `searchAcrossTheCampaignChain` is set to `yes`, then all active contact-lists in the other downstream target campaigns in the chain are also searched. When omitted, all active contact lists in that..."),
    contact_fields: str = typer.Option(None, "--contact-fields", help="Optional. Contact field names to include in the response (comma-separated names)."),
    contact_status: str = typer.Option(None, "--contact-status", help="Choices: CLOSED"),
    search_across_the_campaign_chain: str = typer.Option(None, "--search-across-the-campaign-chain", help="Choices: yes, no"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update contact status across the campaign chain.\n\n\b\nExample: wxcli cc-contact-list update-contacts CCV_1234567890 CONTACT_ID --contact-status CLOSED\n\n\b\nExample --json-body: '{"contactStatus":"CLOSED","searchAcrossTheCampaignChain":"yes"}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_CONTACTS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v3/campaign-management/campaigns/{campaign_id}/contacts/{contact_id}"
    params = {}
    if contact_list_id is not None:
        params["contactListId"] = contact_list_id
    if contact_fields is not None:
        params["fields"] = contact_fields
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if contact_status is not None:
            body["contactStatus"] = contact_status
        if search_across_the_campaign_chain is not None:
            body["searchAcrossTheCampaignChain"] = search_across_the_campaign_chain
    try:
        result = api.session.rest_patch(url, json=body, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": contact_id}, output=output, fields=fields)



_BODY_SKELETON_UPDATE_STATUS = '{"contactListStatus":"..."}'

@app.command("update-status", short_help="Update contact list status.")
def update_status(
    campaign_id: str = typer.Argument(help="e.g. CCV_1234567890"),
    contact_list_id: str = typer.Argument(help="contactListId"),
    contact_list_status: str = typer.Option(None, "--contact-list-status", help="Contact List Status (e.g., EXPIRED). Note: This value is not case-sensitive."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update contact list status.\n\n\b\nExample: wxcli cc-contact-list update-status CCV_1234567890 CONTACT_LIST_ID\n\n\b\nExample --json-body: '{"contactListStatus":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_STATUS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v3/campaign-management/campaigns/{campaign_id}/contact-list/{contact_list_id}/status"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if contact_list_status is not None:
            body["contactListStatus"] = contact_list_status
    try:
        result = api.session.rest_patch(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": contact_list_id}, output=output, fields=fields)



@app.command("list", short_help="Get Contact Lists within a Campaign.")
def cmd_list(
    campaign_id: str = typer.Argument(help="e.g. CCV_123456789"),
    status: str = typer.Option(None, "--status", help="Choices: Active, Expired, UploadFailed"),
    source: str = typer.Option(None, "--source", help="Choices: API, SFTP, ManualFile"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Contact Lists within a Campaign.\n\n\b\nExample: wxcli cc-contact-list list CCV_123456789"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v3/campaign-management/campaigns/{campaign_id}/contact-lists"
    params = {}
    if status is not None:
        params["status"] = status
    if source is not None:
        params["source"] = source
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
    items = result.get("contactLists", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Contact List ID', 'contactListId'), ('Contact List Source File Name', 'contactListSourceFileName'), ('Contact List Status', 'contactListStatus'), ('Contact List Source', 'contactListSource'), ('Contact List Counts Timestamp Utc', 'contactListCountsTimestampUtc')], limit=limit)



@app.command("list-contact-lists", short_help="Get Contact Lists within a Campaign.")
def list_contact_lists(
    campaign_id: str = typer.Argument(help="e.g. CCV_123456789"),
    status: str = typer.Option(None, "--status", help="Choices: Active, Expired, UploadFailed"),
    source: str = typer.Option(None, "--source", help="Choices: API, SFTP, ManualFile"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Contact Lists within a Campaign.\n\n\b\nExample: wxcli cc-contact-list list-contact-lists CCV_123456789"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v4/campaign-management/campaigns/{campaign_id}/contact-lists"
    params = {}
    if status is not None:
        params["status"] = status
    if source is not None:
        params["source"] = source
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
    items = result.get("contactLists", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Contact List ID', 'contactListId'), ('Contact List Source File Name', 'contactListSourceFileName'), ('Contact List Status', 'contactListStatus'), ('Contact List Source', 'contactListSource'), ('Contact List Counts Timestamp Utc', 'contactListCountsTimestampUtc')], limit=limit)


