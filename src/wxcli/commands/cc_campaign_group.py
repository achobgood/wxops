import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_cc_base_url


app = typer.Typer(help="Manage Webex Contact Center cc-campaign-group.")


@app.command("list")
def cmd_list(
    campaign_group_name: str = typer.Argument(help="campaignGroupName"),
    page: str = typer.Option(None, "--page", help="The page number of the result set to retrieve (1-based)."),
    page_size: str = typer.Option(None, "--page-size", help="The number of campaigns to return per page. Must be between 1 and 100."),
    campaign_status: str = typer.Option(None, "--campaign-status", help="Choices: Draft, Running, Pending, Paused, Completed, Ended"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Campaigns by Campaign Group."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v3/campaign-management/campaign-groups/{campaign_group_name}/campaigns"
    params = {}
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["pageSize"] = page_size
    if campaign_status is not None:
        params["campaignStatus"] = campaign_status
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("campaigns", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Campaign ID', 'campaignId'), ('Name', 'campaignName'), ('Status', 'status'), ('Dialing Mode', 'campaignDialingMode')], limit=limit)


