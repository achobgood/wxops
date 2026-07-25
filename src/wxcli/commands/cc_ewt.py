import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id, get_cc_base_url, get_cc_org_id


app = typer.Typer(help="Manage Webex Contact Center cc-ewt.")


@app.command("show")
def show(
    queue_id: str = typer.Option(..., "--queue-id", help="Id of the queue for which the EWT is to be returned"),
    lookback_minutes: str = typer.Option(..., "--lookback-minutes", help="Integer between 5 and 240 (4 hours) signifying how long back to look at the data points to determine EWT for this queue"),
    max_cv: str = typer.Option(None, "--max-cv", help="This an optional parameter. Maximum value of Coefficient of Variance in a subset of samples (wait times for tasks that got connected to agent in one minute interval) to determine whether the average of such values should be treated as a valid sample for EWT computation. If its not passed it takes..."),
    min_valid_samples: str = typer.Option(None, "--min-valid-samples", help="This an optional parameter. Minimum value of percentage of valid samples (with respect to total number of samples) in the specified lookbackMinutes minutes. If its not passed it takes the default value of 40 %"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)


