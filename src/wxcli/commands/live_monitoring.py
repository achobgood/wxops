import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling live-monitoring.")


@app.command("create")
def create(
    site_url: str = typer.Option(None, "--site-url", help="A site URL."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Live Meeting metrics categorized by Country\n\nExample --json-body:\n  '{"siteIds":[0],"siteUrl":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/livemonitoring/liveMeetingsByCountry"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if site_url is not None:
            body["siteUrl"] = site_url
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


