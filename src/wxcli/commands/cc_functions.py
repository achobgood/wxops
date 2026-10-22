import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import resolve_org_id, get_cc_base_url, get_cc_org_id
from wxcli.common import verify_write
from pathlib import Path


app = typer.Typer(help="Manage Webex Contact Center: cc-functions.")


@app.command("list", short_help="List Custom Functions.")
def cmd_list(
    is_partial_match: str = typer.Option(None, "--is-partial-match", help="Whether to search with partial matches. If `false`, search/filter is based on exact match."),
    is_case_sensitive: str = typer.Option(None, "--is-case-sensitive", help="Whether the search should be case-sensitive. Currently applicable only to the `name` field."),
    name: str = typer.Option(None, "--name", help="Filter by function name."),
    language: str = typer.Option(None, "--language", help="Choices: js, py"),
    status: str = typer.Option(None, "--status", help="Filter by one or more function statuses (comma-separated, no spaces). Case-sensitive."),
    sort_by: str = typer.Option(None, "--sort-by", help="Comma-separated fields with order. Supported fields (case-sensitive): `name`, `language`, `status`, `lastModifiedDate`. Prefix a field with `-` for descending order; no prefix means ascending."),
    page: str = typer.Option(None, "--page", help="Zero-based page number for the paginated query."),
    size: str = typer.Option(None, "--size", help="Number of results per page."),
    ids: str = typer.Option(None, "--ids", help="Comma-separated list of function IDs to fetch."),
    function_fields: str = typer.Option(None, "--function-fields", help="Comma-separated list of function fields to include in the response."),
    is_validation: str = typer.Option(None, "--is-validation", help="Used by the Tenant Management team to validate the existence of functions with given IDs regardless of the user's RBAC access."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results, sent as the page size (size); 0 = the server default page. Ignored with --all."),
    offset: int = typer.Option(0, "--offset", help="Skip this many records (translated to the page number; record-exact)."),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Custom Functions."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/v1/{org_id}/functions"
    params = {}
    if is_partial_match is not None:
        params["isPartialMatch"] = is_partial_match
    if is_case_sensitive is not None:
        params["isCaseSensitive"] = is_case_sensitive
    if name is not None:
        params["name"] = name
    if language is not None:
        params["language"] = language
    if status is not None:
        params["status"] = status
    if sort_by is not None:
        params["sortBy"] = sort_by
    if page is not None:
        params["page"] = page
    if size is not None:
        params["size"] = size
    if ids is not None:
        params["ids"] = ids
    if function_fields is not None:
        params["fields"] = function_fields
    if is_validation is not None:
        params["isValidation"] = is_validation
    if limit > 0 and not all_pages and params.get("size") is None:
        params["size"] = limit
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_page_param(url=url, params=params, item_key="data", size_param="size"))
        elif offset > 0:
            result = api.session.fetch_from_offset(url=url, params=params, offset=offset, count=limit, item_key="data", size_param="size", remedies=("all", "offset"))
        else:
            result = api.session.rest_get(url, params=params, remedies=("all", "offset"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("data", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Description', 'description'), ('Language', 'language'), ('Selected Runtime', 'selectedRuntime')], limit=limit)



_BODY_SKELETON_CREATE = '{"name":"...","description":"...","language":"js","selectedRuntime":"...","timeoutInSec":0,"sourceCode":"...","inputs":[{"name":"...","dataType":"boolean","value":{}}],"outputs":"..."}'

@app.command("create", short_help="Create a Custom Function.")
def create(
    name: str = typer.Option(None, "--name", help="Function name. Must be unique within the organization."),
    description: str = typer.Option(None, "--description", help="Human-readable description of the function."),
    language: str = typer.Option(None, "--language", help="Choices: js, py"),
    selected_runtime: str = typer.Option(None, "--selected-runtime", help="Runtime identifier (case-sensitive). For example, `nodejs22.x` or `python3.13`. Defaults to the highest supported runtime for the chosen language."),
    timeout_in_sec: str = typer.Option(None, "--timeout-in-sec", help="Maximum execution time for the function, in seconds."),
    source_code: str = typer.Option(None, "--source-code", help="Function source code as an escaped string. The handler must be an exported async function `export const handle = async (request, response) => { ... }`. Read inputs from `request.inputs.*`, set the result via `response.data = { ... }`, and `return response`."),
    outputs: str = typer.Option(None, "--outputs", help="Stringified JSON of output variable names mapped to sample values."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Custom Function.\n\n\b\nExample --json-body: '{"name":"...","description":"...","language":"js","selectedRuntime":"...","timeoutInSec":0,"sourceCode":"...","inputs":[{"name":"...","dataType":"boolean","value":{}}],"outputs":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/v1/{org_id}/functions"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if language is not None:
            body["language"] = language
        if selected_runtime is not None:
            body["selectedRuntime"] = selected_runtime
        if timeout_in_sec is not None:
            body["timeoutInSec"] = timeout_in_sec
        if source_code is not None:
            body["sourceCode"] = source_code
        if outputs is not None:
            body["outputs"] = outputs
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



@app.command("show", short_help="Get a Custom Function.")
def show(
    id: str = typer.Argument(help="24-char hex id, from: wxcli cc-functions list"),
    version_or_tag: str = typer.Option(None, "--version-or-tag", help="Version number or publish tag of the source code to return (for example, `Dev`, `Live`, or `2`). If omitted, the draft version is returned."),
    meta_data_only: str = typer.Option(None, "--meta-data-only", help="If `true`, returns only metadata and excludes source code. If `false` or omitted, returns both metadata and source code."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get a Custom Function.\n\n\b\nExample: wxcli cc-functions show ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/v1/{org_id}/functions/{id}"
    params = {}
    if version_or_tag is not None:
        params["versionOrTag"] = version_or_tag
    if meta_data_only is not None:
        params["metaDataOnly"] = meta_data_only
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"name":"...","description":"...","language":"js","selectedRuntime":"...","timeoutInSec":0,"sourceCode":"...","inputs":[{"name":"...","dataType":"boolean","value":{}}],"outputs":"..."}'

@app.command("update", short_help="Update a Custom Function.")
def update(
    id: str = typer.Argument(help="24-char hex id, from: wxcli cc-functions list"),
    name: str = typer.Option(None, "--name", help="Function name. Must be unique within the organization."),
    description: str = typer.Option(None, "--description", help="Human-readable description of the function."),
    language: str = typer.Option(None, "--language", help="Choices: js, py"),
    selected_runtime: str = typer.Option(None, "--selected-runtime", help="Runtime identifier (case-sensitive). For example, `nodejs22.x` or `python3.13`. Defaults to the highest supported runtime for the chosen language."),
    timeout_in_sec: str = typer.Option(None, "--timeout-in-sec", help="Maximum execution time for the function, in seconds."),
    source_code: str = typer.Option(None, "--source-code", help="Function source code as an escaped string. The handler must be an exported async function `export const handle = async (request, response) => { ... }`. Read inputs from `request.inputs.*`, set the result via `response.data = { ... }`, and `return response`."),
    outputs: str = typer.Option(None, "--outputs", help="Stringified JSON of output variable names mapped to sample values."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Custom Function.\n\n\b\nExample: wxcli cc-functions update ID\n\n\b\nExample --json-body: '{"name":"...","description":"...","language":"js","selectedRuntime":"...","timeoutInSec":0,"sourceCode":"...","inputs":[{"name":"...","dataType":"boolean","value":{}}],"outputs":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/v1/{org_id}/functions/{id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if language is not None:
            body["language"] = language
        if selected_runtime is not None:
            body["selectedRuntime"] = selected_runtime
        if timeout_in_sec is not None:
            body["timeoutInSec"] = timeout_in_sec
        if source_code is not None:
            body["sourceCode"] = source_code
        if outputs is not None:
            body["outputs"] = outputs
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
        emit({"status": "updated", "id": id}, output=output, fields=fields)



@app.command("delete", short_help="Delete a Custom Function.")
def delete(
    id: str = typer.Argument(help="24-char hex id, from: wxcli cc-functions list"),
    is_force_deletion: str = typer.Option(None, "--is-force-deletion", help="If `true`, deletes the function regardless of its usage in flows."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Custom Function.\n\n\b\nExample: wxcli cc-functions delete ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    url = f"{cc_base_url}/v1/{org_id}/functions/{id}"
    params = {}
    if is_force_deletion is not None:
        params["isForceDeletion"] = is_force_deletion
    try:
        result = api.session.rest_delete(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {id}")
    else:
        emit({"status": "deleted", "id": id}, output=output, fields=fields)



@app.command("import", short_help="Import a Custom Function.")
def cmd_import(
    overwrite: str = typer.Option(None, "--overwrite", help="If `true`, overwrites a function with the same name if one already exists."),
    associated_rcs: str = typer.Option(None, "--associated-rcs", help="Optional list of associated routing-context IDs."),
    file: Path = typer.Option(..., "--file", exists=True, dir_okay=False, readable=True, help="Path of the file to upload, sent as the multipart 'file' part."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Import a Custom Function.\n\n\b\nExample: wxcli cc-functions import --file FILE"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/v1/{org_id}/functions:import"
    params = {}
    if overwrite is not None:
        params["overwrite"] = overwrite
    if associated_rcs is not None:
        params["associatedRcs"] = associated_rcs
    try:
        result = api.session.rest_post_multipart(url, files={"file": (Path(file).name, Path(file).read_bytes(), "application/json")}, params=params)
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



@app.command("unlock", short_help="Unlock a Custom Function.")
def unlock(
    id: str = typer.Argument(help="24-char hex id"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Unlock a Custom Function.\n\n\b\nExample: wxcli cc-functions unlock ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/v1/{org_id}/functions/{id}:unlock"
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



@app.command("lock", short_help="Lock a Custom Function.")
def lock(
    id: str = typer.Argument(help="24-char hex id"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Lock a Custom Function.\n\n\b\nExample: wxcli cc-functions lock ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/v1/{org_id}/functions/{id}:lock"
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



_BODY_SKELETON_PUBLISH = '{"tags":["Dev"],"comment":"..."}'

@app.command("publish", short_help="Publish a Custom Function.")
def publish(
    id: str = typer.Argument(help="24-char hex id"),
    comment: str = typer.Option(None, "--comment", help="Optional publish comment."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Publish a Custom Function.\n\n\b\nExample: wxcli cc-functions publish ID\n\n\b\nExample --json-body: '{"tags":["Dev"],"comment":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_PUBLISH), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/v1/{org_id}/functions/{id}:publish"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if comment is not None:
            body["comment"] = comment
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



@app.command("export", short_help="Export a Custom Function.")
def export(
    id: str = typer.Argument(help="24-char hex id"),
    version_or_tag: str = typer.Option(None, "--version-or-tag", help="Version number or publish tag of the source code to export. If omitted, the latest published version is exported."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Export a Custom Function.\n\n\b\nExample: wxcli cc-functions export ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/v1/{org_id}/functions/{id}:export"
    params = {}
    if version_or_tag is not None:
        params["versionOrTag"] = version_or_tag
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body, params=params)
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


