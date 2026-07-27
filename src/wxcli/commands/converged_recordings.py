import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Calling converged-recordings.")


@app.command("list")
def cmd_list(
    from_param: str = typer.Option(None, "--from", help="Starting date and time (inclusive) for recordings to return, in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `from` cannot be after `to`."),
    to: str = typer.Option(None, "--to", help="Ending date and time (exclusive) for List recordings to return, in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `to` cannot be before `from`."),
    status: str = typer.Option(None, "--status", help="Choices: available, deleted"),
    service_type: str = typer.Option(None, "--service-type", help="Choices: calling, customerAssist"),
    format_param: str = typer.Option(None, "--format", help="Choices: MP3"),
    owner_type: str = typer.Option(None, "--owner-type", help="Choices: user, place, virtualLine, callQueue"),
    storage_region: str = typer.Option(None, "--storage-region", help="Choices: US, SG, GB, JP, DE, AU, IN, CA"),
    location_id: str = typer.Option(None, "--location-id", help="Fetch recordings for users in a particular Webex Calling location (as configured in Control Hub)."),
    topic: str = typer.Option(None, "--topic", help="Recording's topic. If specified, the API filters recordings by topic in a case-insensitive manner."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Recordings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/convergedRecordings"
    params = {}
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if status is not None:
        params["status"] = status
    if service_type is not None:
        params["serviceType"] = service_type
    if format_param is not None:
        params["format"] = format_param
    if owner_type is not None:
        params["ownerType"] = owner_type
    if storage_region is not None:
        params["storageRegion"] = storage_region
    if location_id is not None:
        params["locationId"] = location_id
    if topic is not None:
        params["topic"] = topic
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        if limit > 0:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Topic', 'topic'), ('Create Time', 'createTime'), ('Time Recorded', 'timeRecorded'), ('Format', 'format')], limit=limit)



@app.command("list-converged-recordings")
def list_converged_recordings(
    from_param: str = typer.Option(None, "--from", help="Starting date and time (inclusive) for recordings to return, in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `from` cannot be after `to`. The interval between `from` and `to` must be within 30 days."),
    to: str = typer.Option(None, "--to", help="Ending date and time (exclusive) for List recordings to return, in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `to` cannot be before `from`. The interval between `from` and `to` must be within 30 days."),
    status: str = typer.Option(None, "--status", help="Choices: available, deleted, purged"),
    service_type: str = typer.Option(None, "--service-type", help="Choices: calling, customerAssist"),
    format_param: str = typer.Option(None, "--format", help="Choices: MP3"),
    owner_id: str = typer.Option(None, "--owner-id", help="Webex user Id to fetch recordings for a particular user."),
    owner_email: str = typer.Option(None, "--owner-email", help="Webex email address to fetch recordings for a particular user."),
    owner_type: str = typer.Option(None, "--owner-type", help="Choices: user, place, virtualLine, callQueue"),
    storage_region: str = typer.Option(None, "--storage-region", help="Choices: US, SG, GB, JP, DE, AU, IN, CA"),
    location_id: str = typer.Option(None, "--location-id", help="Fetch recordings for users in a particular Webex Calling location (as configured in Control Hub)."),
    topic: str = typer.Option(None, "--topic", help="Recording's topic. If specified, the API filters recordings by topic in a case-insensitive manner."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Recordings for Admin or Compliance officer."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/convergedRecordings"
    params = {}
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if status is not None:
        params["status"] = status
    if service_type is not None:
        params["serviceType"] = service_type
    if format_param is not None:
        params["format"] = format_param
    if owner_id is not None:
        params["ownerId"] = owner_id
    if owner_email is not None:
        params["ownerEmail"] = owner_email
    if owner_type is not None:
        params["ownerType"] = owner_type
    if storage_region is not None:
        params["storageRegion"] = storage_region
    if location_id is not None:
        params["locationId"] = location_id
    if topic is not None:
        params["topic"] = topic
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        if limit > 0:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Topic', 'topic'), ('Create Time', 'createTime'), ('Time Recorded', 'timeRecorded'), ('Format', 'format')], limit=limit)



@app.command("show")
def show(
    recording_id: str = typer.Argument(help="recordingId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Recording Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/convergedRecordings/{recording_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_DELETE = '{"reason":"...","comment":"..."}'

@app.command("delete")
def delete(
    recording_id: str = typer.Argument(help="recordingId"),
    reason: str = typer.Option(None, "--reason", help="Reason for deleting a recording. Only required when a Compliance Officer is operating on another user's recording."),
    comment: str = typer.Option(None, "--comment", help="Compliance Officer's explanation for deleting a recording. The comment can be a maximum of 255 characters long."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Recording\n\nExample --json-body:\n  '{"reason":"...","comment":"..."}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_DELETE), indent=2))
        raise typer.Exit(0)
    if not force:
        typer.confirm(f"Delete {recording_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/convergedRecordings/{recording_id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if reason is not None:
            body["reason"] = reason
        if comment is not None:
            body["comment"] = comment
    try:
        result = api.session.rest_delete(url, json=body or None)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {recording_id}")
    else:
        emit({"status": "deleted", "id": recording_id}, output=output, fields=fields)



@app.command("show-metadata")
def show_metadata(
    recording_id: str = typer.Argument(help="recordingId"),
    show_all_types: str = typer.Option(None, "--show-all-types", help="If `showAllTypes` is `true`, all attributes will be shown. If it's `false` or not specified, the following attributes of the metadata will be hidden. serviceData.callActivity.mediaStreams serviceData.callActivity.participants serviceData.callActivity.redirectInfo..."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Recording metadata."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/convergedRecordings/{recording_id}/metadata"
    params = {}
    if show_all_types is not None:
        params["showAllTypes"] = show_all_types
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_CREATE = '{"reassignOwnerEmail":"...","ownerEmail":"...","ownerID":"...","recordingIds":["..."]}'

@app.command("create")
def create(
    owner_email: str = typer.Option(None, "--owner-email", help="Recording owner email."),
    owner_id: str = typer.Option(None, "--owner-id", help="Recording owner ID. Can be a user, a virtual line, or a workspace."),
    reassign_owner_email: str = typer.Option(None, "--reassign-owner-email", help="(required) New owner of the recordings."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Reassign Recordings\n\nExample --json-body:\n  '{"reassignOwnerEmail":"...","ownerEmail":"...","ownerID":"...","recordingIds":["..."]}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/convergedRecordings/reassign"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if owner_email is not None:
            body["ownerEmail"] = owner_email
        if owner_id is not None:
            body["ownerID"] = owner_id
        if reassign_owner_email is not None:
            body["reassignOwnerEmail"] = reassign_owner_email
        _missing = [f for f in ['reassignOwnerEmail'] if f not in body or body[f] is None]
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



_BODY_SKELETON_CREATE_SOFT_DELETE = '{"trashAll":true,"ownerEmail":"...","recordingIds":["..."]}'

@app.command("create-soft-delete")
def create_soft_delete(
    trash_all: bool = typer.Option(None, "--trash-all/--no-trash-all", help="If not specified or `false`, moves the recordings specified by `recordingIds` to the recycle bin. If `true`, moves all recordings owned by the caller in case of `user`, and all recordings owned by `ownerEmail` in case of `administrator` to the recycle bin."),
    owner_email: str = typer.Option(None, "--owner-email", help="Email address for the recording owner. This parameter is only used if `trashAll` is set to `true` and the user or application calling the API has the required administrator scope `spark-admin:recordings_write`. The administrator may specify the email of a user from an org they manage and the API..."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Move Recordings into the Recycle Bin\n\nExample --json-body:\n  '{"trashAll":true,"ownerEmail":"...","recordingIds":["..."]}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_SOFT_DELETE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/convergedRecordings/softDelete"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if trash_all is not None:
            body["trashAll"] = trash_all
        if owner_email is not None:
            body["ownerEmail"] = owner_email
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



_BODY_SKELETON_CREATE_RESTORE = '{"restoreAll":true,"ownerEmail":"...","recordingIds":["..."]}'

@app.command("create-restore")
def create_restore(
    restore_all: bool = typer.Option(None, "--restore-all/--no-restore-all", help="If not specified or `false`, restores the recordings specified by `recordingIds` from the recycle bin. If `true`, restores all recordings owned by the caller in case of `user`, and all recordings owned by `ownerEmail` in case of `administrator` from the recycle bin."),
    owner_email: str = typer.Option(None, "--owner-email", help="Email address for the recording owner. This parameter is only used if `restoreAll` is set to `true` and the user or application calling the API has the required administrator scope `spark-admin:recordings_write`. The administrator may specify the email of a user from an org they manage and the API..."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Restore Recordings from Recycle Bin\n\nExample --json-body:\n  '{"restoreAll":true,"ownerEmail":"...","recordingIds":["..."]}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_RESTORE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/convergedRecordings/restore"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if restore_all is not None:
            body["restoreAll"] = restore_all
        if owner_email is not None:
            body["ownerEmail"] = owner_email
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



_BODY_SKELETON_CREATE_PURGE = '{"purgeAll":true,"ownerEmail":"...","recordingIds":["..."]}'

@app.command("create-purge")
def create_purge(
    purge_all: bool = typer.Option(None, "--purge-all/--no-purge-all", help="If not specified or `false`, purges the recordings specified by `recordingIds` from the recycle bin. If `true`, purges all recordings owned by the caller in case of `user`, and all recordings owned by `ownerEmail` in case of `administrator` from the recycle bin."),
    owner_email: str = typer.Option(None, "--owner-email", help="Email address for the recording owner. This parameter is only used if `purgeAll` is set to `true` and the user or application calling the API has the required administrator scope `spark-admin:recordings_write`. The administrator may specify the email of a user from an org they manage and the API..."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Purge Recordings from Recycle Bin\n\nExample --json-body:\n  '{"purgeAll":true,"ownerEmail":"...","recordingIds":["..."]}'."""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_PURGE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/convergedRecordings/purge"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if purge_all is not None:
            body["purgeAll"] = purge_all
        if owner_email is not None:
            body["ownerEmail"] = owner_email
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if output == "id":
        typer.echo("Purged.")
    else:
        emit(result, output=output, fields=fields)


