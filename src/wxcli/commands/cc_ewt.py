import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id, get_cc_base_url, get_cc_org_id


app = typer.Typer(help="Manage Webex Contact Center cc-ewt.")


@app.command("show")
def show(
    queue_id: str = typer.Option(..., "--queue-id", help="Id of the queue for which the EWT is to be returned"),
    lookback_minutes: str = typer.Option(..., "--lookback-minutes", help="Integer between 5 and 240 (4 hours) signifying how long back"),
    max_cv: str = typer.Option(None, "--max-cv", help="This an optional parameter. Maximum value of Coefficient of"),
    min_valid_samples: str = typer.Option(None, "--min-valid-samples", help="This an optional parameter. Minimum value of percentage of v"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Estimated Wait Time."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/ewt"
    params = {}
    if queue_id is not None:
        params["queueId"] = queue_id
    if lookback_minutes is not None:
        params["lookbackMinutes"] = lookback_minutes
    if max_cv is not None:
        params["maxCV"] = max_cv
    if min_valid_samples is not None:
        params["minValidSamples"] = min_valid_samples
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


