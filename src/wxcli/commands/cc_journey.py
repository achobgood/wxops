import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_cc_base_url


app = typer.Typer(help="Manage Webex Contact Center cc-journey.")


@app.command("update", short_help="Add/Remove/Replace details of a Person.")
def update(
    workspace_id: str = typer.Argument(help="workspaceId"),
    person_id: str = typer.Argument(help="24-char hex id"),
    value: str = typer.Option(None, "--value", help="Value for replace op (JSON-parsed: string, number, bool, or array)"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add/Remove/Replace details of a Person.\n\n\b\nExample: wxcli cc-journey update WORKSPACE_ID PERSON_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/person/workspace-id/{workspace_id}/person-id/{person_id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        patch_op = {}
        if value is not None:
            try:
                patch_op["value"] = json.loads(value)
            except json.JSONDecodeError:
                patch_op["value"] = value
        body = [patch_op]
    try:
        result = api.session.rest_patch(url, json=body, content_type="application/json-patch+json")
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("delete", hidden=True)
@app.command("delete-person-id", short_help="Delete specific Person by id.")
def delete_person_id(
    workspace_id: str = typer.Argument(help="workspaceId"),
    person_id: str = typer.Argument(help="24-char hex id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete specific Person by id.\n\n\b\nExample: wxcli cc-journey delete-person-id WORKSPACE_ID PERSON_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    if not force:
        typer.confirm(f"Delete {person_id}?", abort=True)
    url = f"{cc_base_url}/admin/v1/api/person/workspace-id/{workspace_id}/person-id/{person_id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {person_id}")
    else:
        emit({"status": "deleted", "id": person_id}, output=output, fields=fields)



_BODY_SKELETON_UPDATE_PERSON_ID_WORKSPACE_ID = '{"phone":["..."],"email":["..."],"temporaryId":["..."],"customerId":["..."]}'

@app.command("update-person-id-workspace-id", short_help="Add one/more Identities to a person.")
def update_person_id_workspace_id(
    workspace_id: str = typer.Argument(help="workspaceId"),
    person_id: str = typer.Argument(help="24-char hex id"),
    value: str = typer.Option(None, "--value", help="Value for replace op (JSON-parsed: string, number, bool, or array)"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add one/more Identities to a person.\n\n\b\nExample: wxcli cc-journey update-person-id-workspace-id WORKSPACE_ID PERSON_ID\n\n\b\nExample --json-body: '{"phone":["..."],"email":["..."],"temporaryId":["..."],"customerId":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_PERSON_ID_WORKSPACE_ID), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/person/add-identities/workspace-id/{workspace_id}/person-id/{person_id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        patch_op = {}
        if value is not None:
            try:
                patch_op["value"] = json.loads(value)
            except json.JSONDecodeError:
                patch_op["value"] = value
        body = [patch_op]
    try:
        result = api.session.rest_patch(url, json=body, content_type="application/json-patch+json")
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": person_id}, output=output, fields=fields)



@app.command("update-person-id-workspace-id-1", hidden=True)
@app.command("delete-person-id-workspace-id", short_help="Remove one/more Identities from a person.")
def delete_person_id_workspace_id(
    workspace_id: str = typer.Argument(help="workspaceId"),
    person_id: str = typer.Argument(help="24-char hex id"),
    value: str = typer.Option(None, "--value", help="Value for replace op (JSON-parsed: string, number, bool, or array)"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Remove one/more Identities from a person.\n\n\b\nExample: wxcli cc-journey delete-person-id-workspace-id WORKSPACE_ID PERSON_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/person/remove-identities/workspace-id/{workspace_id}/person-id/{person_id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        patch_op = {}
        if value is not None:
            try:
                patch_op["value"] = json.loads(value)
            except json.JSONDecodeError:
                patch_op["value"] = value
        body = [patch_op]
    try:
        result = api.session.rest_patch(url, json=body, content_type="application/json-patch+json")
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Removed.")
    else:
        emit({"status": "removed", "id": person_id}, output=output, fields=fields)



@app.command("show", short_help="Get all or a specific Person Details.")
def show(
    workspace_id: str = typer.Argument(help="workspaceId"),
    person_id: str = typer.Option(None, "--person-id", help="Person ID"),
    filter_param: str = typer.Option(None, "--filter", help="Optional filter which can be applied to the elements to be fetched. This parameter uses the RSQL query syntax, a URI-friendly format for expressing criteria for filtering REST entities. For more information about RSQL in general, see [this..."),
    sort_by: str = typer.Option(None, "--sort-by", help="Sort By Field"),
    sort: str = typer.Option(None, "--sort", help="Sort direction"),
    page: str = typer.Option(None, "--page", help="Index of the page of results to be fetched. Results are returned in blocks of pageSize elements. This parameter specifies which page number to retrieve. The page numbering starts with 0."),
    page_size: str = typer.Option(None, "--page-size", help="Number of items to be displayed on a page"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get all or a specific Person Details.\n\n\b\nExample: wxcli cc-journey show WORKSPACE_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/person/workspace-id/{workspace_id}"
    params = {}
    if person_id is not None:
        params["personId"] = person_id
    if filter_param is not None:
        params["filter"] = filter_param
    if sort_by is not None:
        params["sortBy"] = sort_by
    if sort is not None:
        params["sort"] = sort
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["pageSize"] = page_size
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_CREATE = '{"firstName":"...","lastName":"...","phone":["..."],"email":["..."],"temporaryId":["..."],"customerId":["..."]}'

@app.command("create", short_help="Create a Person.")
def create(
    workspace_id: str = typer.Argument(help="workspaceId"),
    first_name: str = typer.Option(None, "--first-name", help="firstName"),
    last_name: str = typer.Option(None, "--last-name", help="lastName"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Person.\n\n\b\nExample: wxcli cc-journey create WORKSPACE_ID\n\n\b\nExample --json-body: '{"firstName":"...","lastName":"...","phone":["..."],"email":["..."],"temporaryId":["..."],"customerId":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/person/workspace-id/{workspace_id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
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



_BODY_SKELETON_CREATE_PRIMARY_PERSON_ID = '{"personIdsToMerge":["..."]}'

@app.command("create-primary-person-id", short_help="Merges Identities to a Primary Identity.")
def create_primary_person_id(
    workspace_id: str = typer.Argument(help="workspaceId"),
    primary_person_id: str = typer.Argument(help="24-char hex id"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Merges Identities to a Primary Identity.\n\n\b\nExample: wxcli cc-journey create-primary-person-id WORKSPACE_ID PRIMARY_PERSON_ID --json-body '{"personIdsToMerge":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_PRIMARY_PERSON_ID), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/person/merge/workspace-id/{workspace_id}/primary-person-id/{primary_person_id}"
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



_BODY_SKELETON_CREATE_WORKSPACE_ID_MERGE_IDENTITIES = '{"override":true,"firstName":"...","lastName":"...","phone":["..."],"email":["..."],"temporaryId":["..."],"customerId":["..."],"socialId":["..."]}'

@app.command("create-workspace-id-merge-identities", short_help="Creates or merges aliases to an Individual in JDS.")
def create_workspace_id_merge_identities(
    workspace_id: str = typer.Argument(help="workspaceId"),
    override: bool = typer.Option(None, "--override/--no-override", help="Override flag which will override the existing person with the new data if set to true. Default is false."),
    first_name: str = typer.Option(None, "--first-name", help="firstName"),
    last_name: str = typer.Option(None, "--last-name", help="lastName"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Creates or merges aliases to an Individual in JDS.\n\n\b\nExample: wxcli cc-journey create-workspace-id-merge-identities WORKSPACE_ID\n\n\b\nExample --json-body: '{"override":true,"firstName":"...","lastName":"...","phone":["..."],"email":["..."],"temporaryId":["..."],"customerId":["..."],"socialId":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_WORKSPACE_ID_MERGE_IDENTITIES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/person/merge-identities/workspace-id/{workspace_id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if override is not None:
            body["override"] = override
        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
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



@app.command("show-aliases", short_help="Search for an Identity via aliases.")
def show_aliases(
    workspace_id: str = typer.Argument(help="workspaceId"),
    aliases: str = typer.Argument(help="aliases"),
    sort_by: str = typer.Option(None, "--sort-by", help="Sort By Field"),
    sort: str = typer.Option(None, "--sort", help="Sort direction"),
    page: str = typer.Option(None, "--page", help="Index of the page of results to be fetched. Results are returned in blocks of pageSize elements. This parameter specifies which page number to retrieve.The page numbering starts with 0."),
    page_size: str = typer.Option(None, "--page-size", help="Number of items to be displayed on a page."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Search for an Identity via aliases.\n\n\b\nExample: wxcli cc-journey show-aliases WORKSPACE_ID ALIASES"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/person/workspace-id/{workspace_id}/aliases/{aliases}"
    params = {}
    if sort_by is not None:
        params["sortBy"] = sort_by
    if sort is not None:
        params["sort"] = sort
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["pageSize"] = page_size
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_CREATE_EVENT = '{"id":"...","specversion":"...","type":"...","source":"...","identity":"...","identitytype":"...","datacontenttype":"...","data":{"agentId":"...","destination":"...","profileType":"...","currentState":"...","idleCodeId":"...","createdTime":"..."},"time":"...","previousidentity":"..."}'

@app.command("create-event", short_help="Journey Event Posting.")
def create_event(
    workspace_id: str = typer.Option(..., "--workspace-id", help="Workspace ID"),
    id_param: str = typer.Option(None, "--id", help="(required) Event ID"),
    specversion: str = typer.Option(None, "--specversion", help="(required) Event Spec Version"),
    type_param: str = typer.Option(None, "--type", help="(required) Event Type"),
    source: str = typer.Option(None, "--source", help="(required) Event Source"),
    time: str = typer.Option(None, "--time", help="Event Time"),
    identity: str = typer.Option(None, "--identity", help="(required) Identity"),
    identitytype: str = typer.Option(None, "--identitytype", help="(required) Identity Type"),
    previousidentity: str = typer.Option(None, "--previousidentity", help="Previous Identity"),
    datacontenttype: str = typer.Option(None, "--datacontenttype", help="(required) Event Data Content Type"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Journey Event Posting.\n\n\b\nExample: wxcli cc-journey create-event --workspace-id WORKSPACE_ID --json-body '{"id":"...","specversion":"...","type":"...","source":"...","identity":"...","identitytype":"...","datacontenttype":"...","data":{"agentId":"...","destination":"...","profileType":"...","currentState":"...","idleCodeId":"...","createdTime":"..."}}'\n\n\b\nExample --json-body: '{"id":"...","specversion":"...","type":"...","source":"...","identity":"...","identitytype":"...","datacontenttype":"...","data":{"agentId":"...","destination":"...","profileType":"...","currentState":"...","idleCodeId":"...","createdTime":"..."},"time":"...","previousidentity":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_EVENT), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/publish/v1/api/event"
    params = {}
    if workspace_id is not None:
        params["workspaceId"] = workspace_id
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if id_param is not None:
            body["id"] = id_param
        if specversion is not None:
            body["specversion"] = specversion
        if type_param is not None:
            body["type"] = type_param
        if source is not None:
            body["source"] = source
        if time is not None:
            body["time"] = time
        if identity is not None:
            body["identity"] = identity
        if identitytype is not None:
            body["identitytype"] = identitytype
        if previousidentity is not None:
            body["previousidentity"] = previousidentity
        if datacontenttype is not None:
            body["datacontenttype"] = datacontenttype
        _missing = [f for f in ['id', 'specversion', 'type', 'source', 'identity', 'identitytype', 'datacontenttype'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
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



@app.command("show-template-id-workspace-id", short_help="Get A specific Template searched by template id.")
def show_template_id_workspace_id(
    workspace_id: str = typer.Argument(help="workspaceId"),
    template_id: str = typer.Argument(help="24-char hex id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get A specific Template searched by template id.\n\n\b\nExample: wxcli cc-journey show-template-id-workspace-id WORKSPACE_ID TEMPLATE_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/profile-view-template/workspace-id/{workspace_id}/template-id/{template_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_TEMPLATE_ID = '{"name":"...","attributes":[{"displayName":"...","version":"...","event":"...","metaDataType":"...","metaData":"...","limit":0,"lookBackDurationType":"...","lookBackPeriod":0,"aggregationMode":"...","verbose":true,"widgetAttributes":{"type":"..."},"rules":{"logic":"...","args":["..."]}}]}'

@app.command("update-template-id", short_help="Update existing ProfileViewTemplate.")
def update_template_id(
    workspace_id: str = typer.Argument(help="workspaceId"),
    template_id: str = typer.Argument(help="24-char hex id"),
    name: str = typer.Option(None, "--name", help="Template Name"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update existing ProfileViewTemplate.\n\n\b\nExample: wxcli cc-journey update-template-id WORKSPACE_ID TEMPLATE_ID --json-body '{"name":"...","attributes":[{"displayName":"...","version":"...","event":"...","metaDataType":"...","metaData":"...","limit":0,"lookBackDurationType":"...","lookBackPeriod":0,"aggregationMode":"...","verbose":true}]}'\n\n\b\nExample --json-body: '{"name":"...","attributes":[{"displayName":"...","version":"...","event":"...","metaDataType":"...","metaData":"...","limit":0,"lookBackDurationType":"...","lookBackPeriod":0,"aggregationMode":"...","verbose":true,"widgetAttributes":{"type":"..."},"rules":{"logic":"...","args":["..."]}}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_TEMPLATE_ID), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/profile-view-template/workspace-id/{workspace_id}/template-id/{template_id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": template_id}, output=output, fields=fields)



@app.command("delete-template-id", short_help="Delete Template by template Id.")
def delete_template_id(
    workspace_id: str = typer.Argument(help="workspaceId"),
    template_id: str = typer.Argument(help="24-char hex id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Template by template Id.\n\n\b\nExample: wxcli cc-journey delete-template-id WORKSPACE_ID TEMPLATE_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    if not force:
        typer.confirm(f"Delete {template_id}?", abort=True)
    url = f"{cc_base_url}/admin/v1/api/profile-view-template/workspace-id/{workspace_id}/template-id/{template_id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {template_id}")
    else:
        emit({"status": "deleted", "id": template_id}, output=output, fields=fields)



@app.command("show-workspace-id-profile-view-template", short_help="Get All Template Details.")
def show_workspace_id_profile_view_template(
    workspace_id: str = typer.Argument(help="workspaceId"),
    filter_param: str = typer.Option(None, "--filter", help="Optional filter which can be applied to the elements to be fetched. This parameter uses the RSQL query syntax, a URI-friendly format for expressing criteria for filtering REST entities. For more information about RSQL in general, see [this..."),
    sort: str = typer.Option(None, "--sort", help="Sort direction"),
    sort_by: str = typer.Option(None, "--sort-by", help="Sort By Field"),
    page: str = typer.Option(None, "--page", help="Index of the page of results to be fetched. Results are returned in blocks of pageSize elements. This parameter specifies which page number to retrieve.The page numbering starts with 0."),
    page_size: str = typer.Option(None, "--page-size", help="Number of items to be displayed on a page."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get All Template Details.\n\n\b\nExample: wxcli cc-journey show-workspace-id-profile-view-template WORKSPACE_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/profile-view-template/workspace-id/{workspace_id}"
    params = {}
    if filter_param is not None:
        params["filter"] = filter_param
    if sort is not None:
        params["sort"] = sort
    if sort_by is not None:
        params["sortBy"] = sort_by
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["pageSize"] = page_size
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_CREATE_WORKSPACE_ID_PROFILE_VIEW_TEMPLATE = '{"name":"...","attributes":[{"displayName":"...","version":"...","event":"...","metaDataType":"...","metaData":"...","limit":0,"lookBackDurationType":"...","lookBackPeriod":0,"aggregationMode":"...","verbose":true,"widgetAttributes":{"type":"..."},"rules":{"logic":"...","args":["..."]}}]}'

@app.command("create-workspace-id-profile-view-template", short_help="Create Template.")
def create_workspace_id_profile_view_template(
    workspace_id: str = typer.Argument(help="workspaceId"),
    name: str = typer.Option(None, "--name", help="(required) Template Name"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create Template.\n\n\b\nExample: wxcli cc-journey create-workspace-id-profile-view-template WORKSPACE_ID --json-body '{"name":"...","attributes":[{"displayName":"...","version":"...","event":"...","metaDataType":"...","metaData":"...","limit":0,"lookBackDurationType":"...","lookBackPeriod":0,"aggregationMode":"...","verbose":true}]}'\n\n\b\nExample --json-body: '{"name":"...","attributes":[{"displayName":"...","version":"...","event":"...","metaDataType":"...","metaData":"...","limit":0,"lookBackDurationType":"...","lookBackPeriod":0,"aggregationMode":"...","verbose":true,"widgetAttributes":{"type":"..."},"rules":{"logic":"...","args":["..."]}}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_WORKSPACE_ID_PROFILE_VIEW_TEMPLATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/profile-view-template/workspace-id/{workspace_id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        _missing = [f for f in ['name'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
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



@app.command("show-template-name-workspace-id", short_help="Get A specific Template searched by template name.")
def show_template_name_workspace_id(
    workspace_id: str = typer.Argument(help="workspaceId"),
    template_name: str = typer.Argument(help="e.g. sample-template"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get A specific Template searched by template name.\n\n\b\nExample: wxcli cc-journey show-template-name-workspace-id WORKSPACE_ID sample-template"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/profile-view-template/workspace-id/{workspace_id}/template-name/{template_name}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-template-name-person-id", short_help="Historic Progressive Profile View by Template Name.")
def show_template_name_person_id(
    workspace_id: str = typer.Argument(help="24-char hex id"),
    person_id: str = typer.Argument(help="personId"),
    template_name: str = typer.Argument(help="e.g. insurance-template"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Historic Progressive Profile View by Template Name.\n\n\b\nExample: wxcli cc-journey show-template-name-person-id WORKSPACE_ID PERSON_ID insurance-template"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/api/progressive-profile-view/workspace-id/{workspace_id}/person-id/{person_id}/template-name/{template_name}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-template-id-person-id", short_help="Historic Progressive Profile View.")
def show_template_id_person_id(
    workspace_id: str = typer.Argument(help="24-char hex id"),
    person_id: str = typer.Argument(help="personId"),
    template_id: str = typer.Argument(help="templateId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Historic Progressive Profile View.\n\n\b\nExample: wxcli cc-journey show-template-id-person-id WORKSPACE_ID PERSON_ID TEMPLATE_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/api/progressive-profile-view/workspace-id/{workspace_id}/person-id/{person_id}/template-id/{template_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-template-name-identity", short_help="Historic Progressive Profile View By Template Name.")
def show_template_name_identity(
    workspace_id: str = typer.Argument(help="24-char hex id"),
    identity: str = typer.Argument(help="identity"),
    template_name: str = typer.Argument(help="e.g. insurance-template"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Historic Progressive Profile View By Template Name.\n\n\b\nExample: wxcli cc-journey show-template-name-identity WORKSPACE_ID IDENTITY insurance-template"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/api/progressive-profile-view/workspace-id/{workspace_id}/identity/{identity}/template-name/{template_name}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-template-id-identity", short_help="Historic Progressive Profile View By Template Id.")
def show_template_id_identity(
    workspace_id: str = typer.Argument(help="24-char hex id"),
    identity: str = typer.Argument(help="identity"),
    template_id: str = typer.Argument(help="templateId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Historic Progressive Profile View By Template Id.\n\n\b\nExample: wxcli cc-journey show-template-id-identity WORKSPACE_ID IDENTITY TEMPLATE_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/api/progressive-profile-view/workspace-id/{workspace_id}/identity/{identity}/template-id/{template_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-template-name-identity-1", short_help="Stream Progressive profile Views By Template Name.")
def show_template_name_identity_1(
    workspace_id: str = typer.Argument(help="24-char hex id"),
    identity: str = typer.Argument(help="identity"),
    template_name: str = typer.Argument(help="e.g. insurance-template"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Stream Progressive profile Views By Template Name.\n\n\b\nExample: wxcli cc-journey show-template-name-identity-1 WORKSPACE_ID IDENTITY insurance-template"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/api/progressive-profile-view/stream/workspace-id/{workspace_id}/identity/{identity}/template-name/{template_name}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-template-id-identity-1", short_help="Stream Progressive profile Views By Template Id.")
def show_template_id_identity_1(
    workspace_id: str = typer.Argument(help="24-char hex id"),
    identity: str = typer.Argument(help="identity"),
    template_id: str = typer.Argument(help="templateId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Stream Progressive profile Views By Template Id.\n\n\b\nExample: wxcli cc-journey show-template-id-identity-1 WORKSPACE_ID IDENTITY TEMPLATE_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/api/progressive-profile-view/stream/workspace-id/{workspace_id}/identity/{identity}/template-id/{template_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-workspace-id-events", short_help="Historic Journey Events.")
def show_workspace_id_events(
    workspace_id: str = typer.Argument(help="24-char hex id"),
    identity: str = typer.Option(None, "--identity", help="Identity to search events for. In case the identity contains non-uri-encodable characters, eg: '+', '>' etc, you can URL-encode the same and then pass it as parameter."),
    sort_by: str = typer.Option(None, "--sort-by", help="sort By Field"),
    sort: str = typer.Option(None, "--sort", help="sort direction"),
    filter_param: str = typer.Option(None, "--filter", help="Optional filter which can be applied to the elements to be fetched. This parameter uses the RSQL query syntax, a URI-friendly format for expressing criteria for filtering REST entities. For more information about RSQL in general, see [this..."),
    data: str = typer.Option(None, "--data", help="Optional filter on data filed which can be applied to the elements to be fetched. This parameter uses the RSQL query syntax, a URI-friendly format for expressing criteria for filtering REST entities. For more information about RSQL in general, see [this..."),
    page: str = typer.Option(None, "--page", help="Index of the page of results to be fetched. Results are returned in blocks of pageSize elements. This parameter specifies which page number to retrieve.The page numbering starts with 0."),
    page_size: str = typer.Option(None, "--page-size", help="Number of items to be displayed on a page."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Historic Journey Events.\n\n\b\nExample: wxcli cc-journey show-workspace-id-events WORKSPACE_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/api/events/workspace-id/{workspace_id}"
    params = {}
    if identity is not None:
        params["identity"] = identity
    if sort_by is not None:
        params["sortBy"] = sort_by
    if sort is not None:
        params["sort"] = sort
    if filter_param is not None:
        params["filter"] = filter_param
    if data is not None:
        params["data"] = data
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["pageSize"] = page_size
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-identity", short_help="Stream Events By Identity.")
def show_identity(
    workspace_id: str = typer.Argument(help="24-char hex id"),
    identity: str = typer.Argument(help="identity"),
    filter_param: str = typer.Option(None, "--filter", help="Optional filter which can be applied to the elements to be fetched. This parameter uses the RSQL query syntax, a URI-friendly format for expressing criteria for filtering REST entities. For more information about RSQL in general, see [this..."),
    data: str = typer.Option(None, "--data", help="Optional filter on data filed which can be applied to the elements to be fetched. This parameter uses the RSQL query syntax, a URI-friendly format for expressing criteria for filtering REST entities. For more information about RSQL in general, see [this..."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Stream Events By Identity.\n\n\b\nExample: wxcli cc-journey show-identity WORKSPACE_ID IDENTITY"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/api/events/stream/workspace-id/{workspace_id}/identity/{identity}"
    params = {}
    if filter_param is not None:
        params["filter"] = filter_param
    if data is not None:
        params["data"] = data
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-workspace-id-wxcc-subscription", short_help="Get WXCC Subscription.")
def show_workspace_id_wxcc_subscription(
    workspace_id: str = typer.Argument(help="24-char hex id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get WXCC Subscription.\n\n\b\nExample: wxcli cc-journey show-workspace-id-wxcc-subscription WORKSPACE_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/wxcc-subscription/workspace-id/{workspace_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("create-workspace-id-wxcc-subscription", short_help="Create WXCC Subscription.")
def create_workspace_id_wxcc_subscription(
    workspace_id: str = typer.Argument(help="24-char hex id"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create WXCC Subscription.\n\n\b\nExample: wxcli cc-journey create-workspace-id-wxcc-subscription WORKSPACE_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/wxcc-subscription/workspace-id/{workspace_id}"
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



@app.command("delete-workspace-id-wxcc-subscription", short_help="Delete WXCC Subscription.")
def delete_workspace_id_wxcc_subscription(
    workspace_id: str = typer.Argument(help="24-char hex id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete WXCC Subscription.\n\n\b\nExample: wxcli cc-journey delete-workspace-id-wxcc-subscription WORKSPACE_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    if not force:
        typer.confirm(f"Delete {workspace_id}?", abort=True)
    url = f"{cc_base_url}/admin/v1/api/wxcc-subscription/workspace-id/{workspace_id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {workspace_id}")
    else:
        emit({"status": "deleted", "id": workspace_id}, output=output, fields=fields)



@app.command("show-workspace-id-journey-actions", short_help="Get all Journey Actions.")
def show_workspace_id_journey_actions(
    workspace_id: str = typer.Argument(help="workspaceId"),
    sort_by: str = typer.Option(None, "--sort-by", help="Sort By Field"),
    sort: str = typer.Option(None, "--sort", help="Sort direction"),
    page: str = typer.Option(None, "--page", help="Index of the page of results to be fetched. Results are returned in blocks of pageSize elements. This parameter specifies which page number to retrieve. The page numbering starts with 0."),
    page_size: str = typer.Option(None, "--page-size", help="Number of items to be displayed on a page."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get all Journey Actions.\n\n\b\nExample: wxcli cc-journey show-workspace-id-journey-actions WORKSPACE_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/journey-actions/workspace-id/{workspace_id}"
    params = {}
    if sort_by is not None:
        params["sortBy"] = sort_by
    if sort is not None:
        params["sort"] = sort
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["pageSize"] = page_size
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-template-id-workspace-id-1", short_help="Get all Journey Actions for a template.")
def show_template_id_workspace_id_1(
    workspace_id: str = typer.Argument(help="workspaceId"),
    template_id: str = typer.Argument(help="templateId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get all Journey Actions for a template.\n\n\b\nExample: wxcli cc-journey show-template-id-workspace-id-1 WORKSPACE_ID TEMPLATE_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/journey-actions/workspace-id/{workspace_id}/template-id/{template_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_CREATE_TEMPLATE_ID = '{"name":"...","rules":{"logic":"...","args":["..."]},"cooldownPeriodInMinutes":0,"actionTriggers":[{"type":"..."}],"isActive":true}'

@app.command("create-template-id", short_help="Create a new Journey Action.")
def create_template_id(
    workspace_id: str = typer.Argument(help="workspaceId"),
    template_id: str = typer.Argument(help="templateId"),
    name: str = typer.Option(None, "--name", help="(required) Name"),
    cooldown_period_in_minutes: str = typer.Option(None, "--cooldown-period-in-minutes", help="Cooldown Period In Minutes"),
    is_active: bool = typer.Option(None, "--is-active/--no-is-active", help="Is Journey Action Configuration Active"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new Journey Action.\n\n\b\nExample: wxcli cc-journey create-template-id WORKSPACE_ID TEMPLATE_ID --json-body '{"name":"...","rules":{"logic":"...","args":["..."]}}'\n\n\b\nExample --json-body: '{"name":"...","rules":{"logic":"...","args":["..."]},"cooldownPeriodInMinutes":0,"actionTriggers":[{"type":"..."}],"isActive":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_TEMPLATE_ID), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/journey-actions/workspace-id/{workspace_id}/template-id/{template_id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if cooldown_period_in_minutes is not None:
            body["cooldownPeriodInMinutes"] = cooldown_period_in_minutes
        if is_active is not None:
            body["isActive"] = is_active
        _missing = [f for f in ['name'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
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



@app.command("show-action-name", short_help="Get specific Journey Action By Name.")
def show_action_name(
    workspace_id: str = typer.Argument(help="workspaceId"),
    template_id: str = typer.Argument(help="templateId"),
    action_name: str = typer.Argument(help="actionName"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get specific Journey Action By Name.\n\n\b\nExample: wxcli cc-journey show-action-name WORKSPACE_ID TEMPLATE_ID ACTION_NAME"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/journey-actions/workspace-id/{workspace_id}/template-id/{template_id}/action-name/{action_name}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-action-id", short_help="Get specific Journey Action By ActionId.")
def show_action_id(
    workspace_id: str = typer.Argument(help="workspaceId"),
    template_id: str = typer.Argument(help="templateId"),
    action_id: str = typer.Argument(help="actionId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get specific Journey Action By ActionId.\n\n\b\nExample: wxcli cc-journey show-action-id WORKSPACE_ID TEMPLATE_ID ACTION_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/journey-actions/workspace-id/{workspace_id}/template-id/{template_id}/action-id/{action_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_ACTION_ID = '{"name":"...","rules":{"logic":"...","args":["..."]},"cooldownPeriodInMinutes":0,"actionTriggers":[{"type":"..."}],"isActive":true}'

@app.command("update-action-id", short_help="Update existing Journey Action.")
def update_action_id(
    workspace_id: str = typer.Argument(help="workspaceId"),
    template_id: str = typer.Argument(help="templateId"),
    action_id: str = typer.Argument(help="actionId"),
    name: str = typer.Option(None, "--name", help="Name"),
    cooldown_period_in_minutes: str = typer.Option(None, "--cooldown-period-in-minutes", help="Cooldown Period In Minutes"),
    is_active: bool = typer.Option(None, "--is-active/--no-is-active", help="Is Journey Action Configuration Active"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update existing Journey Action.\n\n\b\nExample: wxcli cc-journey update-action-id WORKSPACE_ID TEMPLATE_ID ACTION_ID --json-body '{"name":"...","rules":{"logic":"...","args":["..."]}}'\n\n\b\nExample --json-body: '{"name":"...","rules":{"logic":"...","args":["..."]},"cooldownPeriodInMinutes":0,"actionTriggers":[{"type":"..."}],"isActive":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_ACTION_ID), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/journey-actions/workspace-id/{workspace_id}/template-id/{template_id}/action-id/{action_id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if cooldown_period_in_minutes is not None:
            body["cooldownPeriodInMinutes"] = cooldown_period_in_minutes
        if is_active is not None:
            body["isActive"] = is_active
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": action_id}, output=output, fields=fields)



@app.command("delete-action-id", short_help="Delete Journey Action configuration By ActionId.")
def delete_action_id(
    workspace_id: str = typer.Argument(help="workspaceId"),
    template_id: str = typer.Argument(help="templateId"),
    action_id: str = typer.Argument(help="actionId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Journey Action configuration By ActionId.\n\n\b\nExample: wxcli cc-journey delete-action-id WORKSPACE_ID TEMPLATE_ID ACTION_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    if not force:
        typer.confirm(f"Delete {action_id}?", abort=True)
    url = f"{cc_base_url}/admin/v1/api/journey-actions/workspace-id/{workspace_id}/template-id/{template_id}/action-id/{action_id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {action_id}")
    else:
        emit({"status": "deleted", "id": action_id}, output=output, fields=fields)



@app.command("show-workspace-id-api", short_help="Get Workspace.")
def show_workspace_id_api(
    workspace_id: str = typer.Argument(help="24-char hex id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Workspace.\n\n\b\nExample: wxcli cc-journey show-workspace-id-api WORKSPACE_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/workspace/workspace-id/{workspace_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE_WORKSPACE_ID = '{"name":"...","description":"..."}'

@app.command("update-workspace-id", short_help="Update Workspace.")
def update_workspace_id(
    workspace_id: str = typer.Argument(help="24-char hex id"),
    name: str = typer.Option(None, "--name", help="Workspace Name"),
    description: str = typer.Option(None, "--description", help="Workspace Description"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Workspace.\n\n\b\nExample: wxcli cc-journey update-workspace-id WORKSPACE_ID --name NAME --description DESCRIPTION\n\n\b\nExample --json-body: '{"name":"...","description":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_WORKSPACE_ID), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/workspace/workspace-id/{workspace_id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": workspace_id}, output=output, fields=fields)



@app.command("delete-workspace-id-api", short_help="Delete Workspace.")
def delete_workspace_id_api(
    workspace_id: str = typer.Argument(help="24-char hex id"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Workspace.\n\n\b\nExample: wxcli cc-journey delete-workspace-id-api WORKSPACE_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    if not force:
        typer.confirm(f"Delete {workspace_id}?", abort=True)
    url = f"{cc_base_url}/admin/v1/api/workspace/workspace-id/{workspace_id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {workspace_id}")
    else:
        emit({"status": "deleted", "id": workspace_id}, output=output, fields=fields)



@app.command("list", short_help="Get All Workspaces.")
def cmd_list(
    filter_param: str = typer.Option(None, "--filter", help="Optional filter which can be applied to the elements to be fetched. This parameter uses the RSQL query syntax, a URI-friendly format for expressing criteria for filtering REST entities. For more information about RSQL in general, see [this..."),
    sort_by: str = typer.Option(None, "--sort-by", help="Sort By Field"),
    sort: str = typer.Option(None, "--sort", help="Sort direction"),
    page: str = typer.Option(None, "--page", help="Index of the page of results to be fetched. Results are returned in blocks of pageSize elements. This parameter specifies which page number to retrieve.The page numbering starts with 0."),
    page_size: str = typer.Option(None, "--page-size", help="Number of items to be displayed on a page."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get All Workspaces."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/workspace"
    params = {}
    if filter_param is not None:
        params["filter"] = filter_param
    if sort_by is not None:
        params["sortBy"] = sort_by
    if sort is not None:
        params["sort"] = sort
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["pageSize"] = page_size
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    result = None
    try:
        if all_pages:
            result = list(api.session.follow_page_param(url=url, params=params, item_key="data"))
        else:
            result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("data", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Description', 'description')], limit=limit)



_BODY_SKELETON_CREATE_WORKSPACE = '{"name":"...","description":"..."}'

@app.command("create-workspace", short_help="Create Workspace.")
def create_workspace(
    name: str = typer.Option(None, "--name", help="(required) Workspace Name"),
    description: str = typer.Option(None, "--description", help="(required) Workspace Description"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create Workspace.\n\n\b\nExample: wxcli cc-journey create-workspace --name NAME --description DESCRIPTION\n\n\b\nExample --json-body: '{"name":"...","description":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_WORKSPACE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/workspace"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        _missing = [f for f in ['name', 'description'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
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


