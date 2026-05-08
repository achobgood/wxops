import json
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error
from wxcli.output import print_table, print_json
from wxcli.config import get_fs_base_url


app = typer.Typer(help="Manage WxCC Flow Store fs-templates.")


@app.command("show")
def show(
    id: str = typer.Argument(help="id"),
    ignore_ff: str = typer.Option(None, "--ignore-ff", help="Whether to return the template even if feature flag is off"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve flow/subflow template by template ID.."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    url = f"{fs_base_url}/templates/{id}"
    params = {}
    if ignore_ff is not None:
        params["ignoreFF"] = ignore_ff
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



@app.command("update")
def update(
    id: str = typer.Argument(help="id"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a flow/subflow template by its ID.."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    url = f"{fs_base_url}/templates/{id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("delete")
def delete(
    id: str = typer.Argument(help="id"),
    is_force_deletion: str = typer.Option(None, "--is-force-deletion", help="If hard delete should be completed rather than soft delete"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a flow/subflow template by its ID.."""
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    url = f"{fs_base_url}/templates/{id}"
    params = {}
    if is_force_deletion is not None:
        params["isForceDeletion"] = is_force_deletion
    try:
        api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    typer.echo(f"Deleted: {id}")



@app.command("show-templates")
def show_templates(
    name: str = typer.Option(None, "--name", help="Template Name. Example: Business Hours Template"),
    flow_type: str = typer.Option(None, "--flow-type", help="Template type - FLOW or SUBFLOW"),
    page: str = typer.Option(None, "--page", help="Desired page number in the paginated query"),
    size: str = typer.Option(None, "--size", help="Number of results per page to return for the paginated query"),
    show_inactive: str = typer.Option(None, "--show-inactive", help="Whether to show deleted flows or not"),
    get_all: str = typer.Option(None, "--get-all", help="Whether to show all templates, regardless of feature flag"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List/search for flow/subflow templates."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    url = f"{fs_base_url}/templates"
    params = {}
    if name is not None:
        params["name"] = name
    if flow_type is not None:
        params["flowType"] = flow_type
    if page is not None:
        params["page"] = page
    if size is not None:
        params["size"] = size
    if show_inactive is not None:
        params["showInactive"] = show_inactive
    if get_all is not None:
        params["getAll"] = get_all
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



@app.command("create")
def create(
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new flow/subflow template."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    url = f"{fs_base_url}/templates"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
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


