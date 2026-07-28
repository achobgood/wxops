import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import resolve_org_id


app = typer.Typer(help="Manage Webex Calling archive-users.")


@app.command("list", short_help="Query Archive User.")
def cmd_list(
    filter_param: str = typer.Option(..., "--filter", help="A SCIM-style filter expression used to search archived users. Supported attributes are `username` and `id`, and only the `eq` operator is supported. Examples: - `username eq \"test_user_1@example.com\"` - `id eq \"40929cc6-2df2-4ab5-871c-ec8e38f07b93\"`"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Query Archive User.\n\n\b\nExample: wxcli archive-users list --filter FILTER_PARAM"""
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/identity/organizations/{org_id}/v1/ArchivedUser"
    params = {}
    if filter_param is not None:
        params["filter"] = filter_param
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
    items = result.get("schemas", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)


