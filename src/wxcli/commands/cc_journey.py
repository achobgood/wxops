import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_cc_base_url


app = typer.Typer(help="Manage Webex Contact Center cc-journey.")


@app.command("update")
def update(
    workspace_id: str = typer.Argument(help="workspaceId"),
    person_id: str = typer.Argument(help="personId"),
    value: str = typer.Option(None, "--value", help="Value for replace op (JSON-parsed: string, number, bool, or array)"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add/Remove/Replace details of a Person."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/person/workspace-id/{workspace_id}/person-id/{person_id}"
    if json_body:
        body = json.loads(json_body)
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
    typer.echo(f"Updated.")



@app.command("delete")
def delete(
    workspace_id: str = typer.Argument(help="workspaceId"),
    person_id: str = typer.Argument(help="personId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete specific Person by id."""
    if not force:
        typer.confirm(f"Delete {person_id}?", abort=True)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/person/workspace-id/{workspace_id}/person-id/{person_id}"
    try:
        api.session.rest_delete(url)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {person_id}")



@app.command("update-person-id-workspace-id")
def update_person_id_workspace_id(
    workspace_id: str = typer.Argument(help="workspaceId"),
    person_id: str = typer.Argument(help="personId"),
    value: str = typer.Option(None, "--value", help="Value for replace op (JSON-parsed: string, number, bool, or array)"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add one/more Identities to a person\n\nExample --json-body:\n  '{"phone":["..."],"email":["..."],"temporaryId":["..."],"customerId":["..."]}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/person/add-identities/workspace-id/{workspace_id}/person-id/{person_id}"
    if json_body:
        body = json.loads(json_body)
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
    typer.echo(f"Updated.")



@app.command("update-person-id-workspace-id-1")
def update_person_id_workspace_id_1(
    workspace_id: str = typer.Argument(help="workspaceId"),
    person_id: str = typer.Argument(help="personId"),
    value: str = typer.Option(None, "--value", help="Value for replace op (JSON-parsed: string, number, bool, or array)"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Remove one/more Identities from a person."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/person/remove-identities/workspace-id/{workspace_id}/person-id/{person_id}"
    if json_body:
        body = json.loads(json_body)
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
    typer.echo(f"Updated.")



@app.command("show")
def show(
    workspace_id: str = typer.Argument(help="workspaceId"),
    person_id: str = typer.Option(None, "--person-id", help="Person ID"),
    filter_param: str = typer.Option(None, "--filter", help="Optional filter which can be applied to the elements to be f"),
    sort_by: str = typer.Option(None, "--sort-by", help="Sort By Field"),
    sort: str = typer.Option(None, "--sort", help="Sort direction"),
    page: str = typer.Option(None, "--page", help="Index of the page of results to be fetched.  Results are ret"),
    page_size: str = typer.Option(None, "--page-size", help="Number of items to be displayed on a page"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get all or a specific Person Details."""
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
    workspace_id: str = typer.Argument(help="workspaceId"),
    first_name: str = typer.Option(None, "--first-name", help="firstName"),
    last_name: str = typer.Option(None, "--last-name", help="lastName"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Person\n\nExample --json-body:\n  '{"firstName":"...","lastName":"...","phone":["..."],"email":["..."],"temporaryId":["..."],"customerId":["..."]}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/person/workspace-id/{workspace_id}"
    if json_body:
        body = json.loads(json_body)
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
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("create-primary-person-id")
def create_primary_person_id(
    workspace_id: str = typer.Argument(help="workspaceId"),
    primary_person_id: str = typer.Argument(help="primaryPersonId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Merges Identities to a Primary Identity\n\nExample --json-body:\n  '{"personIdsToMerge":["..."]}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/person/merge/workspace-id/{workspace_id}/primary-person-id/{primary_person_id}"
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



@app.command("create-workspace-id-merge-identities")
def create_workspace_id_merge_identities(
    workspace_id: str = typer.Argument(help="workspaceId"),
    override: bool = typer.Option(None, "--override/--no-override", help="Override flag which will override the existing person with t"),
    first_name: str = typer.Option(None, "--first-name", help="firstName"),
    last_name: str = typer.Option(None, "--last-name", help="lastName"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Creates or merges aliases to an Individual in JDS\n\nExample --json-body:\n  '{"override":true,"firstName":"...","lastName":"...","phone":["..."],"email":["..."],"temporaryId":["..."],"customerId":["..."],"socialId":["..."]}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/person/merge-identities/workspace-id/{workspace_id}"
    if json_body:
        body = json.loads(json_body)
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
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("show-aliases")
def show_aliases(
    workspace_id: str = typer.Argument(help="workspaceId"),
    aliases: str = typer.Argument(help="aliases"),
    sort_by: str = typer.Option(None, "--sort-by", help="Sort By Field"),
    sort: str = typer.Option(None, "--sort", help="Sort direction"),
    page: str = typer.Option(None, "--page", help="Index of the page of results to be fetched.  Results are ret"),
    page_size: str = typer.Option(None, "--page-size", help="Number of items to be displayed on a page."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Search for an Identity via aliases."""
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
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("create-event")
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
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Journey Event Posting\n\nExample --json-body:\n  '{"id":"...","specversion":"...","type":"...","source":"...","identity":"...","identitytype":"...","datacontenttype":"...","data":{"agentId":"...","destination":"...","profileType":"...","currentState":"...","idleCodeId":"...","createdTime":"..."}}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/publish/v1/api/event"
    params = {}
    if workspace_id is not None:
        params["workspaceId"] = workspace_id
    if json_body:
        body = json.loads(json_body)
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
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("show-template-id-workspace-id")
def show_template_id_workspace_id(
    workspace_id: str = typer.Argument(help="workspaceId"),
    template_id: str = typer.Argument(help="templateId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get A specific Template searched by template id."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/profile-view-template/workspace-id/{workspace_id}/template-id/{template_id}"
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



@app.command("update-template-id")
def update_template_id(
    workspace_id: str = typer.Argument(help="workspaceId"),
    template_id: str = typer.Argument(help="templateId"),
    name: str = typer.Option(None, "--name", help="Template Name"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update existing ProfileViewTemplate\n\nExample --json-body:\n  '{"name":"...","attributes":[{"displayName":"...","version":"...","event":"...","metaDataType":"...","metaData":"...","limit":"...","lookBackDurationType":"...","lookBackPeriod":"..."}]}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/profile-view-template/workspace-id/{workspace_id}/template-id/{template_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Updated.")



@app.command("delete-template-id")
def delete_template_id(
    workspace_id: str = typer.Argument(help="workspaceId"),
    template_id: str = typer.Argument(help="templateId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Template by template Id."""
    if not force:
        typer.confirm(f"Delete {template_id}?", abort=True)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/profile-view-template/workspace-id/{workspace_id}/template-id/{template_id}"
    try:
        api.session.rest_delete(url)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {template_id}")



@app.command("show-workspace-id-profile-view-template")
def show_workspace_id_profile_view_template(
    workspace_id: str = typer.Argument(help="workspaceId"),
    filter_param: str = typer.Option(None, "--filter", help="Optional filter which can be applied to the elements to be f"),
    sort: str = typer.Option(None, "--sort", help="Sort direction"),
    sort_by: str = typer.Option(None, "--sort-by", help="Sort By Field"),
    page: str = typer.Option(None, "--page", help="Index of the page of results to be fetched.  Results are ret"),
    page_size: str = typer.Option(None, "--page-size", help="Number of items to be displayed on a page."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get All Template Details."""
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
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("create-workspace-id-profile-view-template")
def create_workspace_id_profile_view_template(
    workspace_id: str = typer.Argument(help="workspaceId"),
    name: str = typer.Option(None, "--name", help="(required) Template Name"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create Template\n\nExample --json-body:\n  '{"name":"...","attributes":[{"displayName":"...","version":"...","event":"...","metaDataType":"...","metaData":"...","limit":"...","lookBackDurationType":"...","lookBackPeriod":"..."}]}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/profile-view-template/workspace-id/{workspace_id}"
    if json_body:
        body = json.loads(json_body)
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
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("show-template-name-workspace-id")
def show_template_name_workspace_id(
    workspace_id: str = typer.Argument(help="workspaceId"),
    template_name: str = typer.Argument(help="templateName"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get A specific Template searched by template name."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/profile-view-template/workspace-id/{workspace_id}/template-name/{template_name}"
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



@app.command("show-template-name-person-id")
def show_template_name_person_id(
    workspace_id: str = typer.Argument(help="workspaceId"),
    person_id: str = typer.Argument(help="personId"),
    template_name: str = typer.Argument(help="templateName"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Historic Progressive Profile View by Template Name."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/api/progressive-profile-view/workspace-id/{workspace_id}/person-id/{person_id}/template-name/{template_name}"
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



@app.command("show-template-id-person-id")
def show_template_id_person_id(
    workspace_id: str = typer.Argument(help="workspaceId"),
    person_id: str = typer.Argument(help="personId"),
    template_id: str = typer.Argument(help="templateId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Historic Progressive Profile View."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/api/progressive-profile-view/workspace-id/{workspace_id}/person-id/{person_id}/template-id/{template_id}"
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



@app.command("show-template-name-identity")
def show_template_name_identity(
    workspace_id: str = typer.Argument(help="workspaceId"),
    identity: str = typer.Argument(help="identity"),
    template_name: str = typer.Argument(help="templateName"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Historic Progressive Profile View By Template Name."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/api/progressive-profile-view/workspace-id/{workspace_id}/identity/{identity}/template-name/{template_name}"
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



@app.command("show-template-id-identity")
def show_template_id_identity(
    workspace_id: str = typer.Argument(help="workspaceId"),
    identity: str = typer.Argument(help="identity"),
    template_id: str = typer.Argument(help="templateId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Historic Progressive Profile View By Template Id."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/api/progressive-profile-view/workspace-id/{workspace_id}/identity/{identity}/template-id/{template_id}"
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



@app.command("show-template-name-identity-1")
def show_template_name_identity_1(
    workspace_id: str = typer.Argument(help="workspaceId"),
    identity: str = typer.Argument(help="identity"),
    template_name: str = typer.Argument(help="templateName"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Stream Progressive profile Views By Template Name."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/api/progressive-profile-view/stream/workspace-id/{workspace_id}/identity/{identity}/template-name/{template_name}"
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



@app.command("show-template-id-identity-1")
def show_template_id_identity_1(
    workspace_id: str = typer.Argument(help="workspaceId"),
    identity: str = typer.Argument(help="identity"),
    template_id: str = typer.Argument(help="templateId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Stream Progressive profile Views By Template Id."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/api/progressive-profile-view/stream/workspace-id/{workspace_id}/identity/{identity}/template-id/{template_id}"
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



@app.command("show-workspace-id-events")
def show_workspace_id_events(
    workspace_id: str = typer.Argument(help="workspaceId"),
    identity: str = typer.Option(None, "--identity", help="Identity to search events for.    In case the identity conta"),
    sort_by: str = typer.Option(None, "--sort-by", help="sort By Field"),
    sort: str = typer.Option(None, "--sort", help="sort direction"),
    filter_param: str = typer.Option(None, "--filter", help="Optional filter which can be applied to the elements to be f"),
    data: str = typer.Option(None, "--data", help="Optional filter on data filed which can be applied to the el"),
    page: str = typer.Option(None, "--page", help="Index of the page of results to be fetched.  Results are ret"),
    page_size: str = typer.Option(None, "--page-size", help="Number of items to be displayed on a page."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Historic Journey Events."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v1/api/events/workspace-id/{workspace_id}"
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
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("show-identity")
def show_identity(
    workspace_id: str = typer.Argument(help="workspaceId"),
    identity: str = typer.Argument(help="identity"),
    filter_param: str = typer.Option(None, "--filter", help="Optional filter which can be applied to the elements to be f"),
    data: str = typer.Option(None, "--data", help="Optional filter on data filed which can be applied to the el"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Stream Events By Identity."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v1/api/events/stream/workspace-id/{workspace_id}/identity/{identity}"
    params = {}
    if filter_param is not None:
        params["filter"] = filter_param
    if data is not None:
        params["data"] = data
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



@app.command("show-workspace-id-wxcc-subscription")
def show_workspace_id_wxcc_subscription(
    workspace_id: str = typer.Argument(help="workspaceId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get WXCC Subscription."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/wxcc-subscription/workspace-id/{workspace_id}"
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



@app.command("create-workspace-id-wxcc-subscription")
def create_workspace_id_wxcc_subscription(
    workspace_id: str = typer.Argument(help="workspaceId"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create WXCC Subscription."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/wxcc-subscription/workspace-id/{workspace_id}"
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



@app.command("delete-workspace-id-wxcc-subscription")
def delete_workspace_id_wxcc_subscription(
    workspace_id: str = typer.Argument(help="workspaceId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete WXCC Subscription."""
    if not force:
        typer.confirm(f"Delete {workspace_id}?", abort=True)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/wxcc-subscription/workspace-id/{workspace_id}"
    try:
        api.session.rest_delete(url)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {workspace_id}")



@app.command("show-workspace-id-journey-actions")
def show_workspace_id_journey_actions(
    workspace_id: str = typer.Argument(help="workspaceId"),
    sort_by: str = typer.Option(None, "--sort-by", help="Sort By Field"),
    sort: str = typer.Option(None, "--sort", help="Sort direction"),
    page: str = typer.Option(None, "--page", help="Index of the page of results to be fetched.  Results are ret"),
    page_size: str = typer.Option(None, "--page-size", help="Number of items to be displayed on a page."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get all Journey Actions."""
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
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("show-template-id-workspace-id-1")
def show_template_id_workspace_id_1(
    workspace_id: str = typer.Argument(help="workspaceId"),
    template_id: str = typer.Argument(help="templateId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get all Journey Actions for a template."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/journey-actions/workspace-id/{workspace_id}/template-id/{template_id}"
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



@app.command("create-template-id")
def create_template_id(
    workspace_id: str = typer.Argument(help="workspaceId"),
    template_id: str = typer.Argument(help="templateId"),
    name: str = typer.Option(None, "--name", help="(required) Name"),
    cooldown_period_in_minutes: str = typer.Option(None, "--cooldown-period-in-minutes", help="Cooldown Period In Minutes"),
    is_active: bool = typer.Option(None, "--is-active/--no-is-active", help="Is Journey Action Configuration Active"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new  Journey Action\n\nExample --json-body:\n  '{"name":"...","rules":{"logic":"...","args":["..."]},"cooldownPeriodInMinutes":0,"actionTriggers":[{"type":"..."}],"isActive":true}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/journey-actions/workspace-id/{workspace_id}/template-id/{template_id}"
    if json_body:
        body = json.loads(json_body)
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
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("show-action-name")
def show_action_name(
    workspace_id: str = typer.Argument(help="workspaceId"),
    template_id: str = typer.Argument(help="templateId"),
    action_name: str = typer.Argument(help="actionName"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get specific Journey Action By Name."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/journey-actions/workspace-id/{workspace_id}/template-id/{template_id}/action-name/{action_name}"
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



@app.command("show-action-id")
def show_action_id(
    workspace_id: str = typer.Argument(help="workspaceId"),
    template_id: str = typer.Argument(help="templateId"),
    action_id: str = typer.Argument(help="actionId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get specific Journey Action By ActionId."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/journey-actions/workspace-id/{workspace_id}/template-id/{template_id}/action-id/{action_id}"
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



@app.command("update-action-id")
def update_action_id(
    workspace_id: str = typer.Argument(help="workspaceId"),
    template_id: str = typer.Argument(help="templateId"),
    action_id: str = typer.Argument(help="actionId"),
    name: str = typer.Option(None, "--name", help="Name"),
    cooldown_period_in_minutes: str = typer.Option(None, "--cooldown-period-in-minutes", help="Cooldown Period In Minutes"),
    is_active: bool = typer.Option(None, "--is-active/--no-is-active", help="Is Journey Action Configuration Active"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update existing Journey Action\n\nExample --json-body:\n  '{"name":"...","rules":{"logic":"...","args":["..."]},"cooldownPeriodInMinutes":0,"actionTriggers":[{"type":"..."}],"isActive":true}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/journey-actions/workspace-id/{workspace_id}/template-id/{template_id}/action-id/{action_id}"
    if json_body:
        body = json.loads(json_body)
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
    typer.echo(f"Updated.")



@app.command("delete-action-id")
def delete_action_id(
    workspace_id: str = typer.Argument(help="workspaceId"),
    template_id: str = typer.Argument(help="templateId"),
    action_id: str = typer.Argument(help="actionId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Journey Action configuration By ActionId."""
    if not force:
        typer.confirm(f"Delete {action_id}?", abort=True)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/journey-actions/workspace-id/{workspace_id}/template-id/{template_id}/action-id/{action_id}"
    try:
        api.session.rest_delete(url)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {action_id}")



@app.command("show-workspace-id-api")
def show_workspace_id_api(
    workspace_id: str = typer.Argument(help="workspaceId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Workspace."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/workspace/workspace-id/{workspace_id}"
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



@app.command("update-workspace-id")
def update_workspace_id(
    workspace_id: str = typer.Argument(help="workspaceId"),
    name: str = typer.Option(None, "--name", help="Workspace Name"),
    description: str = typer.Option(None, "--description", help="Workspace Description"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Workspace."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/workspace/workspace-id/{workspace_id}"
    if json_body:
        body = json.loads(json_body)
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
    typer.echo(f"Updated.")



@app.command("delete-workspace-id-api")
def delete_workspace_id_api(
    workspace_id: str = typer.Argument(help="workspaceId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Workspace."""
    if not force:
        typer.confirm(f"Delete {workspace_id}?", abort=True)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/workspace/workspace-id/{workspace_id}"
    try:
        api.session.rest_delete(url)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {workspace_id}")



@app.command("list")
def cmd_list(
    filter_param: str = typer.Option(None, "--filter", help="Optional filter which can be applied to the elements to be f"),
    sort_by: str = typer.Option(None, "--sort-by", help="Sort By Field"),
    sort: str = typer.Option(None, "--sort", help="Sort direction"),
    page: str = typer.Option(None, "--page", help="Index of the page of results to be fetched.  Results are ret"),
    page_size: str = typer.Option(None, "--page-size", help="Number of items to be displayed on a page."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
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
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
            handle_rest_error(e)
    result = result or []
    items = result.get("data", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create-workspace")
def create_workspace(
    name: str = typer.Option(None, "--name", help="(required) Workspace Name"),
    description: str = typer.Option(None, "--description", help="(required) Workspace Description"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create Workspace."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/admin/v1/api/workspace"
    if json_body:
        body = json.loads(json_body)
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
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)


