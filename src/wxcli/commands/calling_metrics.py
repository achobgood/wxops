import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Calling calling-metrics.")


@app.command("show", short_help="Webex Calling Call Quality Stats.")
def show(
    from_param: str = typer.Option(None, "--from", help="Inclusive UTC start time in yyyy-MM-ddTHH:mm:ssZ format. If omitted while to is provided, it is seven days before the effective to time. If both times are omitted, it is seven days before the current time."),
    to: str = typer.Option(None, "--to", help="Exclusive UTC end time in yyyy-MM-ddTHH:mm:ssZ format. A value later than the current time is clamped to the current time. If omitted while from is provided, it is the earlier of seven days after from and the current time. If both times are omitted, it is the current time."),
    location: str = typer.Option(None, "--location", help="Exact Webex Calling location name. Omit it or provide an empty value to include all locations."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Webex Calling Call Quality Stats."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/analytics/callQualityStats"
    params = {}
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if location is not None:
        params["location"] = location
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)


