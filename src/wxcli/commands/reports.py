import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling reports.")


@app.command("create")
def create(
    template_id: str = typer.Option(None, "--template-id", help="(required) Unique ID representing valid report templates."),
    start_date: str = typer.Option(None, "--start-date", help="Data in the report will be from this date onwards."),
    end_date: str = typer.Option(None, "--end-date", help="Data in the report will be until this date."),
    site_list: str = typer.Option(None, "--site-list", help="Sites belonging to user's organization. This attribute is ne"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Report."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/reports"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if template_id is not None:
            body["templateId"] = template_id
        if start_date is not None:
            body["startDate"] = start_date
        if end_date is not None:
            body["endDate"] = end_date
        if site_list is not None:
            body["siteList"] = site_list
        _missing = [f for f in ['templateId'] if f not in body or body[f] is None]
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


