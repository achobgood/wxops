import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_cc_base_url


app = typer.Typer(help="Manage Webex Contact Center cc-dnc.")


@app.command("create")
def create(
    dnc_list_name: str = typer.Argument(help="dncListName"),
    phone_number: str = typer.Option(None, "--phone-number", help="(required) The phone number to add to the DNC list. Must be in E.164 fo"),
    source: str = typer.Option(None, "--source", help="(required) The source or origin of the DNC entry. This helps track wher"),
    reason: str = typer.Option(None, "--reason", help="Optional reason for adding the phone number to the DNC list."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add Phone Number to DNC List."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v3/campaign-management/dncList/{dnc_list_name}/phoneNumber"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if phone_number is not None:
            body["phoneNumber"] = phone_number
        if source is not None:
            body["source"] = source
        if reason is not None:
            body["reason"] = reason
        _missing = [f for f in ['phoneNumber', 'source'] if f not in body or body[f] is None]
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



@app.command("show")
def show(
    dnc_list_name: str = typer.Argument(help="dncListName"),
    phone_number: str = typer.Argument(help="phoneNumber"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Phone Number from DNC List."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v3/campaign-management/dncList/{dnc_list_name}/phoneNumber/{phone_number}"
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



@app.command("delete")
def delete(
    dnc_list_name: str = typer.Argument(help="dncListName"),
    phone_number: str = typer.Argument(help="phoneNumber"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Remove Phone Number from DNC List."""
    if not force:
        typer.confirm(f"Delete {phone_number}?", abort=True)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v3/campaign-management/dncList/{dnc_list_name}/phoneNumber/{phone_number}"
    try:
        api.session.rest_delete(url)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {phone_number}")


