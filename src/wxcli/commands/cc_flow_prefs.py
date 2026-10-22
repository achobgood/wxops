import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import resolve_org_id, get_flow_store_base_url, get_cc_org_id
from wxcli.common import verify_write


app = typer.Typer(help="Manage Webex Contact Center: cc-flow-prefs.")


@app.command("list", short_help="getFlowPreferences.")
def cmd_list(
    project_id: str = typer.Argument(help="24-char hex id"),
    flow_id: str = typer.Argument(help="from: wxcli cc-flow list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", hidden=True, help="Accepted and ignored: this command returns one object."),
    offset: int = typer.Option(0, "--offset", hidden=True, help="Accepted and ignored: this command returns one object."),
    all_pages: bool = typer.Option(False, "--all", hidden=True, help="Accepted and ignored: this command returns one object."),
    debug: bool = typer.Option(False, "--debug"),
):
    """getFlowPreferences.\n\n\b\nExample: wxcli cc-flow-prefs list PROJECT_ID FLOW_ID"""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}/preferences"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_CREATE = '[{}]'

@app.command("create", short_help="createFlowPreference.")
def create(
    project_id: str = typer.Argument(help="24-char hex id"),
    flow_id: str = typer.Argument(help="from: wxcli cc-flow list"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """createFlowPreference.\n\nNOTE: the body is a JSON array of preferences, e.g. --json-body '[{"name":"...","value":"...","type":"..."}]' (shape carried from wxcc, not re-measured in Plan 2).\n\n\b\nExample: wxcli cc-flow-prefs create PROJECT_ID FLOW_ID\n\n\b\nExample --json-body: '[{}]'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}/preferences"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if output == "id":
        if isinstance(result, dict) and "id" in result:
            typer.echo(f"Created: {result['id']}")
        elif not result or result == {}:
            typer.echo("Created.")
        else:
            print_json(result)
    else:
        emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '[{}]'

@app.command("update", short_help="updateFlowPreferences.")
def update(
    project_id: str = typer.Argument(help="24-char hex id"),
    flow_id: str = typer.Argument(help="from: wxcli cc-flow list"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """updateFlowPreferences.\n\nNOTE: the body is a JSON array of preferences, e.g. --json-body '[{"name":"...","value":"...","type":"..."}]' (shape carried from wxcc, not re-measured in Plan 2).\n\n\b\nExample: wxcli cc-flow-prefs update PROJECT_ID FLOW_ID\n\n\b\nExample --json-body: '[{}]'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}/preferences"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if verify:
        verify_write(api, url, None, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": flow_id}, output=output, fields=fields)



_BODY_SKELETON_DELETE = '["..."]'

@app.command("delete", short_help="removeFlowPreferencesByPreferenceNames.")
def delete(
    project_id: str = typer.Argument(help="24-char hex id"),
    flow_id: str = typer.Argument(help="from: wxcli cc-flow list"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """removeFlowPreferencesByPreferenceNames.\n\nNOTE: the body is a JSON array of preference names, e.g. --json-body '["name"]' (shape carried from wxcc, not re-measured in Plan 2).\n\n\b\nExample: wxcli cc-flow-prefs delete PROJECT_ID FLOW_ID\n\n\b\nExample --json-body: '["..."]'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_DELETE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    if not force:
        typer.confirm(f"Delete Preferences for {flow_id}?", abort=True)
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}/preferences"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_delete(url, json=body or None)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {flow_id}")
    else:
        emit({"status": "deleted", "id": flow_id}, output=output, fields=fields)



@app.command("list-tags", short_help="List the tags of a flow.")
def list_tags(
    project_id: str = typer.Argument(help="24-char hex id"),
    flow_id: str = typer.Argument(help="24-char hex id, from: wxcli cc-flow list"),
    all_tags: str = typer.Option(None, "--all-tags", help="If true, returns all eligible tags. Otherwise returns tags attached to the flow."),
    skip_rs_ep_check: str = typer.Option(None, "--skip-rs-ep-check", help="If true, skips the check on connected Entry Points."),
    show_ext_vars: str = typer.Option(None, "--show-ext-vars", help="If true, returns the tags with externalized variables for the tag specified by the 'tagId' parameter."),
    tag_id: str = typer.Option(None, "--tag-id", help="One of 'Live', 'Latest', 'Test', 'Dev'. The tag must be in use."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", hidden=True, help="Accepted and ignored: this command returns one object."),
    offset: int = typer.Option(0, "--offset", hidden=True, help="Accepted and ignored: this command returns one object."),
    all_pages: bool = typer.Option(False, "--all", hidden=True, help="Accepted and ignored: this command returns one object."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List the tags of a flow.\n\n\b\nExample: wxcli cc-flow-prefs list-tags PROJECT_ID FLOW_ID"""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}/tags"
    params = {}
    if all_tags is not None:
        params["all"] = all_tags
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
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list-tag-history", short_help="getTagHistories.")
def list_tag_history(
    project_id: str = typer.Argument(help="24-char hex id"),
    flow_id: str = typer.Argument(help="from: wxcli cc-flow list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", hidden=True, help="Accepted and ignored: this command returns one object."),
    offset: int = typer.Option(0, "--offset", hidden=True, help="Accepted and ignored: this command returns one object."),
    all_pages: bool = typer.Option(False, "--all", hidden=True, help="Accepted and ignored: this command returns one object."),
    debug: bool = typer.Option(False, "--debug"),
):
    """getTagHistories.\n\n\b\nExample: wxcli cc-flow-prefs list-tag-history PROJECT_ID FLOW_ID"""
    api = get_api(debug=debug)
    fs_base_url = get_flow_store_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{fs_base_url}/{org_id}/project/{project_id}/flows/{flow_id}/tagHistories"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)


