import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Calling analytics.")


@app.command("show", short_help="Historical Data related to Messaging.")
def show(
    from_param: str = typer.Option(None, "--from", help="UTC date starting from which the data needs to be returned."),
    to: str = typer.Option(None, "--to", help="UTC date up to which the data needs to be returned"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-daily-totals", short_help="Historical Data related to Room Devices.")
def show_daily_totals(
    from_param: str = typer.Option(None, "--from", help="Starting UTC Date from which historical data should be returned."),
    to: str = typer.Option(None, "--to", help="Ending UTC Date for which data should be returned."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-aggregates", short_help="Historical Data related to Meetings.")
def show_aggregates(
    site_url: str = typer.Option(..., "--site-url", help="URL of the Webex site for which historical data is requested."),
    from_param: str = typer.Option(None, "--from", help="UTC Date starting from which the data needs to be returned"),
    to: str = typer.Option(None, "--to", help="UTC Date up to which the data needs to be returned"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Historical Data related to Meetings.\n\n\b\nExample: wxcli analytics show-aggregates --site-url SITE_URL"""
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)


