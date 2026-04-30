import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling analytics.")


@app.command("show")
def show(
    from_param: str = typer.Option(None, "--from", help="UTC date starting from which the data needs to be returned."),
    to: str = typer.Option(None, "--to", help="UTC date up to which the data needs to be returned"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Historical Data related to Messaging."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/analytics/messagingMetrics/dailyTotals"
    params = {}
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
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



@app.command("show-daily-totals")
def show_daily_totals(
    from_param: str = typer.Option(None, "--from", help="Starting UTC Date from which historical data should be retur"),
    to: str = typer.Option(None, "--to", help="Ending UTC Date for which data should be returned."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Historical Data related to Room Devices."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/analytics/roomDeviceMetrics/dailyTotals"
    params = {}
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
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
    url = f"https://webexapis.com/v1/analytics/meetingsMetrics/aggregates"
    params = {}
    if site_url is not None:
        params["siteUrl"] = site_url
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
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


