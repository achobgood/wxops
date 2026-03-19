import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling historical-analytics-apis.")


@app.command("show")
def show(
    from_param: str = typer.Option(None, "--from", help="UTC date starting from which the data needs to be returned."),
    to: str = typer.Option(None, "--to", help="UTC date up to which the data needs to be returned"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Historical Data related to Messaging."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/v1/analytics/messagingMetrics/dailyTotals"
    params = {}
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("show-daily-totals")
def show_daily_totals(
    from_param: str = typer.Option(None, "--from", help="Starting UTC Date from which historical data should be retur"),
    to: str = typer.Option(None, "--to", help="Ending UTC Date for which data should be returned."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Historical Data related to Room Devices."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/v1/analytics/roomDeviceMetrics/dailyTotals"
    params = {}
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)



@app.command("show-aggregates")
def show_aggregates(
    site_url: str = typer.Option(..., "--site-url", help="URL of the Webex site for which historical data is requested"),
    from_param: str = typer.Option(None, "--from", help="UTC Date starting from which the data needs to be returned"),
    to: str = typer.Option(None, "--to", help="UTC Date up to which the data needs to be returned"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Historical Data related to Meetings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/v1/analytics/meetingsMetrics/aggregates"
    params = {}
    if site_url is not None:
        params["siteUrl"] = site_url
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    print_json(result)


