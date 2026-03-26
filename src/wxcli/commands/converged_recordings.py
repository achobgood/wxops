import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.errors import handle_rest_error
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling converged-recordings.")


@app.command("list")
def cmd_list(
    max: str = typer.Option(None, "--max", help="Maximum number of recordings to return in a single page. `ma"),
    from_param: str = typer.Option(None, "--from", help="Starting date and time (inclusive) for recordings to return,"),
    to: str = typer.Option(None, "--to", help="Ending date and time (exclusive) for List recordings to retu"),
    status: str = typer.Option(None, "--status", help="Choices: available, deleted"),
    service_type: str = typer.Option(None, "--service-type", help="Choices: calling, customerAssist"),
    format_param: str = typer.Option(None, "--format", help="Choices: MP3"),
    owner_type: str = typer.Option(None, "--owner-type", help="Choices: user, place, virtualLine, callQueue"),
    storage_region: str = typer.Option(None, "--storage-region", help="Choices: US, SG, GB, JP, DE, AU, IN, CA"),
    location_id: str = typer.Option(None, "--location-id", help="Fetch recordings for users in a particular Webex Calling loc"),
    topic: str = typer.Option(None, "--topic", help="Recording's topic. If specified, the API filters recordings"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Recordings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/convergedRecordings"
    params = {}
    if max is not None:
        params["max"] = max
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
            items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except RestError as e:
        handle_rest_error(e)
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-converged-recordings")
def list_converged_recordings(
    max: str = typer.Option(None, "--max", help="Maximum number of recordings to return in a single page. `ma"),
    from_param: str = typer.Option(None, "--from", help="Starting date and time (inclusive) for recordings to return,"),
    to: str = typer.Option(None, "--to", help="Ending date and time (exclusive) for List recordings to retu"),
    status: str = typer.Option(None, "--status", help="Choices: available, deleted, purged"),
    service_type: str = typer.Option(None, "--service-type", help="Choices: calling, customerAssist"),
    format_param: str = typer.Option(None, "--format", help="Choices: MP3"),
    owner_id: str = typer.Option(None, "--owner-id", help="Webex user Id to fetch recordings for a particular user."),
    owner_email: str = typer.Option(None, "--owner-email", help="Webex email address to fetch recordings for a particular use"),
    owner_type: str = typer.Option(None, "--owner-type", help="Choices: user, place, virtualLine, callQueue"),
    storage_region: str = typer.Option(None, "--storage-region", help="Choices: US, SG, GB, JP, DE, AU, IN, CA"),
    location_id: str = typer.Option(None, "--location-id", help="Fetch recordings for users in a particular Webex Calling loc"),
    topic: str = typer.Option(None, "--topic", help="Recording's topic. If specified, the API filters recordings"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Recordings for Admin or Compliance officer."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/admin/convergedRecordings"
    params = {}
    if max is not None:
        params["max"] = max
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
            items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except RestError as e:
        handle_rest_error(e)
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("show")
def show(
    recording_id: str = typer.Argument(help="recordingId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Recording Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/convergedRecordings/{recording_id}"
    try:
        result = api.session.rest_get(url)
    except RestError as e:
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



@app.command("delete")
def delete(
    recording_id: str = typer.Argument(help="recordingId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a Recording."""
    if not force:
        typer.confirm(f"Delete {recording_id}?", abort=True)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/convergedRecordings/{recording_id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        handle_rest_error(e)
    typer.echo(f"Deleted: {recording_id}")



@app.command("show-metadata")
def show_metadata(
    recording_id: str = typer.Argument(help="recordingId"),
    show_all_types: str = typer.Option(None, "--show-all-types", help="If `showAllTypes` is `true`, all attributes will be shown. I"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
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
    except RestError as e:
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
    owner_email: str = typer.Option(None, "--owner-email", help="Recording owner email."),
    owner_id: str = typer.Option(None, "--owner-id", help="Recording owner ID. Can be a user, a virtual line, or a work"),
    reassign_owner_email: str = typer.Option(None, "--reassign-owner-email", help="(required) New owner of the recordings."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Reassign Recordings\n\nExample --json-body:\n  '{"ownerEmail":"...","ownerID":"...","recordingIds":["..."],"reassignOwnerEmail":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/convergedRecordings/reassign"
    if json_body:
        body = json.loads(json_body)
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
    except RestError as e:
        handle_rest_error(e)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("create-soft-delete")
def create_soft_delete(
    trash_all: bool = typer.Option(None, "--trash-all/--no-trash-all", help="If not specified or `false`, moves the recordings specified"),
    owner_email: str = typer.Option(None, "--owner-email", help="Email address for the recording owner. This parameter is onl"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Move Recordings into the Recycle Bin\n\nExample --json-body:\n  '{"trashAll":true,"ownerEmail":"...","recordingIds":["..."]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/convergedRecordings/softDelete"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if trash_all is not None:
            body["trashAll"] = trash_all
        if owner_email is not None:
            body["ownerEmail"] = owner_email
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        handle_rest_error(e)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("create-restore")
def create_restore(
    restore_all: bool = typer.Option(None, "--restore-all/--no-restore-all", help="If not specified or `false`, restores the recordings specifi"),
    owner_email: str = typer.Option(None, "--owner-email", help="Email address for the recording owner. This parameter is onl"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Restore Recordings from Recycle Bin\n\nExample --json-body:\n  '{"restoreAll":true,"ownerEmail":"...","recordingIds":["..."]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/convergedRecordings/restore"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if restore_all is not None:
            body["restoreAll"] = restore_all
        if owner_email is not None:
            body["ownerEmail"] = owner_email
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        handle_rest_error(e)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("create-purge")
def create_purge(
    purge_all: bool = typer.Option(None, "--purge-all/--no-purge-all", help="If not specified or `false`, purges the recordings specified"),
    owner_email: str = typer.Option(None, "--owner-email", help="Email address for the recording owner. This parameter is onl"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Purge Recordings from Recycle Bin\n\nExample --json-body:\n  '{"purgeAll":true,"ownerEmail":"...","recordingIds":["..."]}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/convergedRecordings/purge"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if purge_all is not None:
            body["purgeAll"] = purge_all
        if owner_email is not None:
            body["ownerEmail"] = owner_email
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        handle_rest_error(e)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)


