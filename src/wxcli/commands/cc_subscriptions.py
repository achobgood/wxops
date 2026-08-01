import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id, get_cc_base_url, get_cc_org_id
from wxcli.common import verify_write


app = typer.Typer(help="Manage Webex Contact Center cc-subscriptions.")


@app.command("list", short_help="List Subscriptions.")
def cmd_list(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Subscriptions."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/subscriptions"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("data", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Description', 'description'), ('Destination URL', 'destinationUrl'), ('Created Time', 'createdTime')], limit=limit)



_BODY_SKELETON_CREATE = '{"name":"...","eventTypes":["..."],"destinationUrl":"...","description":"...","secret":"...","orgId":"..."}'

@app.command("create", short_help="Register Subscription.")
def create(
    name: str = typer.Option(None, "--name", help="(required) Client-defined string naming the subscription."),
    description: str = typer.Option(None, "--description", help="Client-defined string describing the subscription."),
    destination_url: str = typer.Option(None, "--destination-url", help="(required) URL to which webhooks will be posted. Must be HTTPS on an IANA-listed top-level domain name (e.g. .com) with a path (at least /). No query parameters, userinfo, non-443 ports, or fragments allowed. We do not treat this field as sensitive data, so do not use secrets in this URL such as tokens or API..."),
    secret: str = typer.Option(None, "--secret", help="Secret string used to sign payloads sent to the destination URL."),
    org_id: str = typer.Option(None, "--org-id", help="Organization ID to be used for this operation. If unspecified, the Organization ID is inferred from the token. The token must have permission to interact with the organization."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Register Subscription.\n\n\b\nExample: wxcli cc-subscriptions create --json-body '{"name":"...","eventTypes":["..."],"destinationUrl":"..."}'\n\n\b\nExample --json-body: '{"name":"...","eventTypes":["..."],"destinationUrl":"...","description":"...","secret":"...","orgId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/subscriptions"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if destination_url is not None:
            body["destinationUrl"] = destination_url
        if secret is not None:
            body["secret"] = secret
        if org_id is not None:
            body["orgId"] = org_id
        _missing = [f for f in ['name', 'destinationUrl'] if f not in body or body[f] is None]
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



@app.command("show", short_help="Get Subscription.")
def show(
    id: str = typer.Argument(help="UUID, from: wxcli cc-subscriptions list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Subscription.\n\n\b\nExample: wxcli cc-subscriptions show ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/subscriptions/{id}"
    params = {}
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



_BODY_SKELETON_UPDATE = '{"description":"...","eventTypes":["..."],"destinationUrl":"...","status":"active","secret":"...","orgId":"..."}'

@app.command("update", short_help="Update Subscription.")
def update(
    id: str = typer.Argument(help="UUID, from: wxcli cc-subscriptions list"),
    description: str = typer.Option(None, "--description", help="Client-defined string describing the subscription."),
    destination_url: str = typer.Option(None, "--destination-url", help="URL to which webhooks will be posted. Must be HTTPS on an IANA-listed top-level domain name (e.g. .com) with a path (at least /). No query parameters, userinfo, non-443 ports, or fragments allowed. We do not treat this field as sensitive data, so do not use secrets in this URL such as tokens or API..."),
    status: str = typer.Option(None, "--status", help="Choices: active, inactive"),
    secret: str = typer.Option(None, "--secret", help="Secret string used to sign payloads sent to the destination URL."),
    org_id: str = typer.Option(None, "--org-id", help="Organization ID to be used for this operation. If unspecified, the Organization ID is inferred from the token. The token must have permission to interact with the organization."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Subscription.\n\n\b\nExample: wxcli cc-subscriptions update ID\n\n\b\nExample --json-body: '{"description":"...","eventTypes":["..."],"destinationUrl":"...","status":"active","secret":"...","orgId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/subscriptions/{id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if description is not None:
            body["description"] = description
        if destination_url is not None:
            body["destinationUrl"] = destination_url
        if status is not None:
            body["status"] = status
        if secret is not None:
            body["secret"] = secret
        if org_id is not None:
            body["orgId"] = org_id
    try:
        result = api.session.rest_patch(url, json=body)
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



@app.command("delete", short_help="Delete Subscription.")
def delete(
    id: str = typer.Argument(help="UUID, from: wxcli cc-subscriptions list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Subscription.\n\n\b\nExample: wxcli cc-subscriptions delete ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    url = f"{cc_base_url}/subscriptions/{id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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



@app.command("list-event-types-v1", short_help="List Event Types.")
def list_event_types_v1(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Event Types."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/event-types"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("data", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Name', 'name'), ('Resource', 'resource'), ('Action', 'action')], limit=limit)



@app.command("list-subscriptions", short_help="List Subscriptions.")
def list_subscriptions(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Subscriptions."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v2/subscriptions"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("data", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Description', 'description'), ('Destination URL', 'destinationUrl'), ('Created Time', 'createdTime')], limit=limit)



_BODY_SKELETON_CREATE_SUBSCRIPTIONS = '{"name":"...","eventTypes":["..."],"destinationUrl":"...","resourceVersion":"...","description":"...","secret":"...","orgId":"..."}'

@app.command("create-subscriptions", short_help="Register Subscription.")
def create_subscriptions(
    name: str = typer.Option(None, "--name", help="(required) Client-defined string naming the subscription."),
    description: str = typer.Option(None, "--description", help="Client-defined string describing the subscription."),
    destination_url: str = typer.Option(None, "--destination-url", help="(required) URL to which webhooks will be posted. Must be HTTPS on an IANA-listed top-level domain name (e.g. .com) with a path (at least /). No query parameters, userinfo, non-443 ports, or fragments allowed. We do not treat this field as sensitive data, so do not use secrets in this URL such as tokens or API..."),
    secret: str = typer.Option(None, "--secret", help="Secret string used to sign payloads sent to the destination URL."),
    org_id: str = typer.Option(None, "--org-id", help="Organization ID to be used for this operation. If unspecified, the Organization ID is inferred from the token. The token must have permission to interact with the organization."),
    resource_version: str = typer.Option(None, "--resource-version", help="(required) Represents version of the resource client is interested in. Should be of the format ‘resource:version’. Refer to the List Event Types V2 API for details on the latest available resources and versions."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Register Subscription.\n\n\b\nExample: wxcli cc-subscriptions create-subscriptions --json-body '{"name":"...","eventTypes":["..."],"destinationUrl":"...","resourceVersion":"..."}'\n\n\b\nExample --json-body: '{"name":"...","eventTypes":["..."],"destinationUrl":"...","resourceVersion":"...","description":"...","secret":"...","orgId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_SUBSCRIPTIONS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v2/subscriptions"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if destination_url is not None:
            body["destinationUrl"] = destination_url
        if secret is not None:
            body["secret"] = secret
        if org_id is not None:
            body["orgId"] = org_id
        if resource_version is not None:
            body["resourceVersion"] = resource_version
        _missing = [f for f in ['name', 'destinationUrl', 'resourceVersion'] if f not in body or body[f] is None]
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



@app.command("show-subscriptions", short_help="Get Subscription.")
def show_subscriptions(
    id: str = typer.Argument(help="UUID, from: wxcli cc-subscriptions list-subscriptions"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Subscription.\n\n\b\nExample: wxcli cc-subscriptions show-subscriptions ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v2/subscriptions/{id}"
    params = {}
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



_BODY_SKELETON_UPDATE_SUBSCRIPTIONS = '{"resourceVersion":"...","description":"...","eventTypes":["..."],"destinationUrl":"...","status":"active","secret":"...","orgId":"..."}'

@app.command("update-subscriptions", short_help="Update Subscription.")
def update_subscriptions(
    id: str = typer.Argument(help="UUID, from: wxcli cc-subscriptions list-subscriptions"),
    description: str = typer.Option(None, "--description", help="Client-defined string describing the subscription."),
    destination_url: str = typer.Option(None, "--destination-url", help="URL to which webhooks will be posted. Must be HTTPS on an IANA-listed top-level domain name (e.g. .com) with a path (at least /). No query parameters, userinfo, non-443 ports, or fragments allowed. We do not treat this field as sensitive data, so do not use secrets in this URL such as tokens or API..."),
    status: str = typer.Option(None, "--status", help="Choices: active, inactive"),
    secret: str = typer.Option(None, "--secret", help="Secret string used to sign payloads sent to the destination URL."),
    org_id: str = typer.Option(None, "--org-id", help="Organization ID to be used for this operation. If unspecified, the Organization ID is inferred from the token. The token must have permission to interact with the organization."),
    resource_version: str = typer.Option(None, "--resource-version", help="Represents version of the resource client is interested in. Should be of the format ‘resource:version’. Refer to the List Event Types V2 API for details on the latest available resources and versions."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Subscription.\n\n\b\nExample: wxcli cc-subscriptions update-subscriptions ID --resource-version RESOURCE_VERSION\n\n\b\nExample --json-body: '{"resourceVersion":"...","description":"...","eventTypes":["..."],"destinationUrl":"...","status":"active","secret":"...","orgId":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE_SUBSCRIPTIONS), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v2/subscriptions/{id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if description is not None:
            body["description"] = description
        if destination_url is not None:
            body["destinationUrl"] = destination_url
        if status is not None:
            body["status"] = status
        if secret is not None:
            body["secret"] = secret
        if org_id is not None:
            body["orgId"] = org_id
        if resource_version is not None:
            body["resourceVersion"] = resource_version
    try:
        result = api.session.rest_patch(url, json=body)
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



@app.command("delete-subscriptions", short_help="Delete Subscription.")
def delete_subscriptions(
    id: str = typer.Argument(help="UUID, from: wxcli cc-subscriptions list-subscriptions"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete Subscription.\n\n\b\nExample: wxcli cc-subscriptions delete-subscriptions ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    if not force:
        typer.confirm(f"Delete {id}?", abort=True)
    url = f"{cc_base_url}/v2/subscriptions/{id}"
    params = {}
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
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



@app.command("list-event-types-v2", short_help="List Event Types.")
def list_event_types_v2(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Event Types."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/v2/event-types"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("data", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Name', 'name'), ('Resource', 'resource'), ('Action', 'action')], limit=limit)


