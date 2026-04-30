import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_cc_base_url


app = typer.Typer(help="Manage Webex Contact Center cc-contact-list.")


@app.command("create")
def create(
    campaign_id: str = typer.Argument(help="campaignId"),
    activation_time_lag_minutes: str = typer.Option(None, "--activation-time-lag-minutes", help="Contact list activation time lag in minutes (0 = immediate a"),
    activation_date_time: str = typer.Option(None, "--activation-date-time", help="Contact list activation DateTimeStamp (format: YYYY-MM-DDTHH"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create contact list\n\nExample --json-body:\n  '{"supportedChannels":["Voice"],"activationTimeLagMinutes":0,"activationDateTime":"..."}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v3/campaign-management/campaigns/{campaign_id}/contact-list"
    if json_body:
        body = json.loads(json_body)
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
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "contactListId" in result:
        typer.echo(f"Created: {result['contactListId']}")
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("create-contacts")
def create_contacts(
    campaign_id: str = typer.Argument(help="campaignId"),
    contact_list_id: str = typer.Argument(help="contactListId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create contacts within a contact list\n\nExample --json-body:\n  '{"contacts":[{"contactAttributes":"..."}]}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v3/campaign-management/campaigns/{campaign_id}/contact-list/{contact_list_id}/contacts"
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
    campaign_id: str = typer.Argument(help="campaignId"),
    contact_list_id: str = typer.Argument(help="contactListId"),
    contact_id: str = typer.Argument(help="contactId"),
    contact_status: str = typer.Option(None, "--contact-status", help="Choices: CLOSED"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a contact's status within a contact list."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v3/campaign-management/campaigns/{campaign_id}/contact-list/{contact_list_id}/contacts/{contact_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if contact_status is not None:
            body["contactStatus"] = contact_status
    try:
        result = api.session.rest_patch(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("update-status")
def update_status(
    campaign_id: str = typer.Argument(help="campaignId"),
    contact_list_id: str = typer.Argument(help="contactListId"),
    contact_list_status: str = typer.Option(None, "--contact-list-status", help="Contact List Status (e.g., EXPIRED). Note: This value is not"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update contact list status."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v3/campaign-management/campaigns/{campaign_id}/contact-list/{contact_list_id}/status"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if contact_list_status is not None:
            body["contactListStatus"] = contact_list_status
    try:
        result = api.session.rest_patch(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("list")
def cmd_list(
    campaign_id: str = typer.Argument(help="campaignId"),
    status: str = typer.Option(None, "--status", help="Choices: Active, Expired, UploadFailed"),
    source: str = typer.Option(None, "--source", help="Choices: API, SFTP, ManualFile, GlobalUpload, GlobalSFTP"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Contact Lists within a Campaign."""
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("contactLists", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)


