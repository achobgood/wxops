import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.common import verify_write


app = typer.Typer(help="Manage Webex Calling webhooks.")


@app.command("list", short_help="List Webhooks.")
def cmd_list(
    owned_by: str = typer.Option(None, "--owned-by", help="Limit the result list to org wide webhooks. Only allowed value is `org`."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Webhooks."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/webhooks"
    params = {}
    if owned_by is not None:
        params["ownedBy"] = owned_by
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        if limit > 0 and not all_pages:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Name', 'name'), ('Target URL', 'targetUrl'), ('Resource', 'resource')], limit=limit)



_BODY_SKELETON_CREATE = '{"name":"...","targetUrl":"...","resource":"attachmentActions","event":"created","filter":"...","secret":"...","ownedBy":"..."}'

@app.command("create", short_help="Create a Webhook.")
def create(
    name: str = typer.Option(None, "--name", help="(required) A user-friendly name for the webhook."),
    target_url: str = typer.Option(None, "--target-url", help="(required) URL that receives POST requests for each event."),
    resource: str = typer.Option(None, "--resource", help="(required) Resource type for the webhook. Creating a webhook requires 'read' scope on the resource the webhook is for. * `attachmentActions` - [Attachment Actions](/docs/api/v1/attachment-actions) resource. * `dataSources` - [data sources](/docs/api/v1/data-sources) resource. * `memberships` -... (use --help for choices)"),
    event: str = typer.Option(None, "--event", help="(required) Choices: created, updated, deleted, started, ended, joined, left, migrated, authorized, deauthorized, statusChanged"),
    filter_param: str = typer.Option(None, "--filter", help="Filter that defines the webhook scope. See [Filtering Webhooks](/docs/api/guides/webhooks#filtering-webhooks) for more information. Please note that if a filter of `hostEmail`, `hostUserId`, `ownerEmail` or `ownerId` is specified, `ownedBy` must be set to `org`."),
    secret: str = typer.Option(None, "--secret", help="Secret used to generate payload signature."),
    owned_by: str = typer.Option(None, "--owned-by", help="Specify `org` when creating an org/admin level webhook. Supported for `meetings`, `recordings`, `convergedRecordings`,`meetingParticipants`, `meetingTranscripts`, `videoMeshAlerts`, `controlHubAlerts`, `rooms`, `messaging` and `adminBatchJobs` (for Compliance Officers and messages with file..."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a Webhook.\n\n\b\nExample: wxcli webhooks create --name NAME --target-url TARGET_URL --resource attachmentActions --event created\n\n\b\nExample --json-body: '{"name":"...","targetUrl":"...","resource":"attachmentActions","event":"created","filter":"...","secret":"...","ownedBy":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/webhooks"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if target_url is not None:
            body["targetUrl"] = target_url
        if resource is not None:
            body["resource"] = resource
        if event is not None:
            body["event"] = event
        if filter_param is not None:
            body["filter"] = filter_param
        if secret is not None:
            body["secret"] = secret
        if owned_by is not None:
            body["ownedBy"] = owned_by
        _missing = [f for f in ['name', 'targetUrl', 'resource', 'event'] if f not in body or body[f] is None]
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



@app.command("show", short_help="Get Webhook Details.")
def show(
    webhook_id: str = typer.Argument(help="Webex WEBHOOK id, from: wxcli webhooks list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Webhook Details.\n\n\b\nExample: wxcli webhooks show WEBHOOK_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/webhooks/{webhook_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"name":"...","targetUrl":"...","secret":"...","ownedBy":"...","status":"active"}'

@app.command("update", short_help="Update a Webhook.")
def update(
    webhook_id: str = typer.Argument(help="Webex WEBHOOK id, from: wxcli webhooks list"),
    name: str = typer.Option(None, "--name", help="A user-friendly name for the webhook."),
    target_url: str = typer.Option(None, "--target-url", help="URL that receives POST requests for each event."),
    secret: str = typer.Option(None, "--secret", help="Secret used to generate payload signature."),
    owned_by: str = typer.Option(None, "--owned-by", help="Specify `org` when creating an org/admin level webhook. Supported for `meetings`, `recordings`, `convergedRecordings`, `meetingParticipants`, `meetingTranscripts`, `videoMeshAlerts`, `controlHubAlerts`, `rooms`, `messaging` and `adminBatchJobs` (for Compliance Officers and messages with file..."),
    status: str = typer.Option(None, "--status", help="Choices: active"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Webhook.\n\n\b\nExample: wxcli webhooks update WEBHOOK_ID --name NAME --target-url TARGET_URL\n\n\b\nExample --json-body: '{"name":"...","targetUrl":"...","secret":"...","ownedBy":"...","status":"active"}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/webhooks/{webhook_id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if name is not None:
            body["name"] = name
        if target_url is not None:
            body["targetUrl"] = target_url
        if secret is not None:
            body["secret"] = secret
        if owned_by is not None:
            body["ownedBy"] = owned_by
        if status is not None:
            body["status"] = status
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
        emit({"status": "updated", "id": webhook_id}, output=output, fields=fields)



@app.command("delete", short_help="Delete a Webhook.")
def delete(
    webhook_id: str = typer.Argument(help="Webex WEBHOOK id, from: wxcli webhooks list"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Webhook.\n\n\b\nExample: wxcli webhooks delete WEBHOOK_ID"""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete {webhook_id}?", abort=True)
    url = f"https://webexapis.com/v1/webhooks/{webhook_id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {webhook_id}")
    else:
        emit({"status": "deleted", "id": webhook_id}, output=output, fields=fields)


