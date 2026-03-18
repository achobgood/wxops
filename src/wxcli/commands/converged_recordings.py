import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling converged-recordings.")


@app.command("list")
def cmd_list(
    max: str = typer.Option(None, "--max", help="Maximum number of recordings to return in a single page. `ma"),
    from_param: str = typer.Option(None, "--from", help="Starting date and time (inclusive) for recordings to return,"),
    to: str = typer.Option(None, "--to", help="Ending date and time (exclusive) for List recordings to retu"),
    status: str = typer.Option(None, "--status", help="Recording's status. If not specified or `available`, retriev"),
    service_type: str = typer.Option(None, "--service-type", help="Recording's service-type. If specified, the API filters reco"),
    format_param: str = typer.Option(None, "--format", help="Recording's file format. If specified, the API filters recor"),
    owner_type: str = typer.Option(None, "--owner-type", help="Recording based on type of user."),
    storage_region: str = typer.Option(None, "--storage-region", help="Recording stored in certain Webex locations."),
    location_id: str = typer.Option(None, "--location-id", help="Fetch recordings for users in a particular Webex Calling loc"),
    topic: str = typer.Option(None, "--topic", help="Recording's topic. If specified, the API filters recordings"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
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
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("items", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-converged-recordings")
def list_converged_recordings(
    max: str = typer.Option(None, "--max", help="Maximum number of recordings to return in a single page. `ma"),
    from_param: str = typer.Option(None, "--from", help="Starting date and time (inclusive) for recordings to return,"),
    to: str = typer.Option(None, "--to", help="Ending date and time (exclusive) for List recordings to retu"),
    status: str = typer.Option(None, "--status", help="Recording's status. If not specified or `available`, retriev"),
    service_type: str = typer.Option(None, "--service-type", help="Recording's service-type. If specified, the API filters reco"),
    format_param: str = typer.Option(None, "--format", help="Recording's file format. If specified, the API filters recor"),
    owner_id: str = typer.Option(None, "--owner-id", help="Webex user Id to fetch recordings for a particular user."),
    owner_email: str = typer.Option(None, "--owner-email", help="Webex email address to fetch recordings for a particular use"),
    owner_type: str = typer.Option(None, "--owner-type", help="Recording based on type of user."),
    storage_region: str = typer.Option(None, "--storage-region", help="Recording stored in certain Webex locations."),
    location_id: str = typer.Option(None, "--location-id", help="Fetch recordings for users in a particular Webex Calling loc"),
    topic: str = typer.Option(None, "--topic", help="Recording's topic. If specified, the API filters recordings"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
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
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("items", result if isinstance(result, list) else [])
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
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
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
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {recording_id}")



@app.command("list-metadata")
def list_metadata(
    recording_id: str = typer.Argument(help="recordingId"),
    show_all_types: str = typer.Option(None, "--show-all-types", help="If `showAllTypes` is `true`, all attributes will be shown. I"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=use API default)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Recording metadata."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/convergedRecordings/{recording_id}/metadata"
    params = {}
    if show_all_types is not None:
        params["showAllTypes"] = show_all_types
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        result = api.session.rest_get(url, params=params)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    items = result.get("metadata", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("create")
def create(
    reassign_owner_email: str = typer.Option(None, "--reassign-owner-email", help=""),
    owner_email: str = typer.Option(None, "--owner-email", help=""),
    owner_i_d: str = typer.Option(None, "--owner-i-d", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Reassign Recordings."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/convergedRecordings/reassign"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if reassign_owner_email is not None:
            body["reassignOwnerEmail"] = reassign_owner_email
        if owner_email is not None:
            body["ownerEmail"] = owner_email
        if owner_i_d is not None:
            body["ownerID"] = owner_i_d
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    else:
        print_json(result)



@app.command("create-soft-delete")
def create_soft_delete(
    trash_all: bool = typer.Option(None, "--trash-all/--no-trash-all", help=""),
    owner_email: str = typer.Option(None, "--owner-email", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Move Recordings into the Recycle Bin."""
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
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    else:
        print_json(result)



@app.command("create-restore")
def create_restore(
    restore_all: bool = typer.Option(None, "--restore-all/--no-restore-all", help=""),
    owner_email: str = typer.Option(None, "--owner-email", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Restore Recordings from Recycle Bin."""
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
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    else:
        print_json(result)



@app.command("create-purge")
def create_purge(
    purge_all: bool = typer.Option(None, "--purge-all/--no-purge-all", help=""),
    owner_email: str = typer.Option(None, "--owner-email", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Purge Recordings from Recycle Bin."""
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
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    else:
        print_json(result)


