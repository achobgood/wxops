import json
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error
from wxcli.output import print_table, print_json
from wxcli.config import resolve_org_id, get_cc_org_id, get_fs_base_url, get_fs_project_id


app = typer.Typer(help="Manage WxCC Flow Store fs-flow-props.")


@app.command("show")
def show(
    flow_id: str = typer.Argument(help="flowId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """getFlowPreferences."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{projectId}/flows/{flow_id}/preferences"
    try:
        result = api.session.rest_get(url)
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
    flow_id: str = typer.Argument(help="flowId"),
    empty: bool = typer.Option(None, "--empty/--no-empty", help=""),
    traversable_again: bool = typer.Option(None, "--traversable-again/--no-traversable-again", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """createFlowPreference."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{projectId}/flows/{flow_id}/preferences"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if empty is not None:
            body["empty"] = empty
        if traversable_again is not None:
            body["traversableAgain"] = traversable_again
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



@app.command("update")
def update(
    flow_id: str = typer.Argument(help="flowId"),
    empty: bool = typer.Option(None, "--empty/--no-empty", help=""),
    traversable_again: bool = typer.Option(None, "--traversable-again/--no-traversable-again", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """updateFlowPreferences."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{projectId}/flows/{flow_id}/preferences"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if empty is not None:
            body["empty"] = empty
        if traversable_again is not None:
            body["traversableAgain"] = traversable_again
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("delete")
def delete(
    flow_id: str = typer.Argument(help="flowId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """removeFlowPreferencesByPreferenceNames."""
    if not force:
        typer.confirm(f"Delete {flow_id}?", abort=True)
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{projectId}/flows/{flow_id}/preferences"
    try:
        api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    typer.echo(f"Deleted: {flow_id}")



@app.command("show-tags")
def show_tags(
    flow_id: str = typer.Argument(help="flowId"),
    all: str = typer.Option(None, "--all", help="If true, returns all eligible tags. Otherwise returns tags a"),
    skip_rs_ep_check: str = typer.Option(None, "--skip-rs-ep-check", help="If true, skips the check on connected Entry Points."),
    show_ext_vars: str = typer.Option(None, "--show-ext-vars", help="If true, returns the tags with externalized variables for th"),
    tag_id: str = typer.Option(None, "--tag-id", help="One of 'Live', 'Latest', 'Test', 'Dev'. The tag must be in u"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List the tags of a flow."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    project_id = get_fs_project_id()
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}/tags"
    params = {}
    if all is not None:
        params["all"] = all
    if skip_rs_ep_check is not None:
        params["skipRsEPCheck"] = skip_rs_ep_check
    if show_ext_vars is not None:
        params["showExtVars"] = show_ext_vars
    if tag_id is not None:
        params["tagId"] = tag_id
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



@app.command("show-tag-histories")
def show_tag_histories(
    flow_id: str = typer.Argument(help="flowId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """getTagHistories."""
    api = get_api(debug=debug)
    fs_base_url = get_fs_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{projectId}/flows/{flow_id}/tagHistories"
    try:
        result = api.session.rest_get(url)
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


