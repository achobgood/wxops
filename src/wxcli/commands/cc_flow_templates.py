import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_cc_base_url


app = typer.Typer(help="Manage Webex Contact Center: cc-flow-templates.")


@app.command("list", short_help="List Flow Templates.")
def cmd_list(
    flow_type: str = typer.Option(None, "--flow-type", help="SUBFLOW or FLOW. Measured 2026-10-19: SUBFLOW returned only the 8 SUBFLOW templates of 39. Omitted, every template is returned."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results, sent as the page size (size); 0 = the server default page. Ignored with --all."),
    offset: int = typer.Option(0, "--offset", help="Skip this many records (translated to the page number; record-exact)."),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Flow Templates."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/templates"
    params = {}
    if flow_type is not None:
        params["flowType"] = flow_type
    if limit > 0 and not all_pages and params.get("size") is None:
        params["size"] = limit
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_page_param(url=url, params=params, item_key="items", size_param="size"))
        elif offset > 0:
            result = api.session.fetch_from_offset(url=url, params=params, offset=offset, count=limit, item_key="items", size_param="size", remedies=("all", "offset"))
        else:
            result = api.session.rest_get(url, params=params, remedies=("all", "offset"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Description', 'description'), ('Type', 'flowType')], limit=limit)



@app.command("show", short_help="Get a Flow Template.")
def show(
    id: str = typer.Argument(help="from: wxcli cc-flow-templates list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Flow Template.\n\n\b\nExample: wxcli cc-flow-templates show ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/templates/{id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)


