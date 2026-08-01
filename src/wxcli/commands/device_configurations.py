import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.common import verify_write


app = typer.Typer(help="Manage Webex Calling device-configurations.")


@app.command("show", short_help="List Device Configurations for device.")
def show(
    device_id: str = typer.Option(..., "--device-id", help="List device configurations by device ID."),
    key: str = typer.Option(None, "--key", help="This can optionally be used to filter configurations. Keys are composed of segments. It's possible to use absolute paths, wildcards or ranges. - **Absolute** gives only one configuration as a result. `Conference.MaxReceiveCallRate` for example gives the Conference `MaxReceiveCallRate`..."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Device Configurations for device.\n\n\b\nExample: wxcli device-configurations show --device-id DEVICE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/deviceConfigurations"
    params = {}
    if device_id is not None:
        params["deviceId"] = device_id
    if key is not None:
        params["key"] = key
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"op":"remove","path":"..."}'

@app.command("update", short_help="Update Device Configurations.")
def update(
    device_id: str = typer.Option(..., "--device-id", help="Update device configurations by device ID."),
    op: str = typer.Option(None, "--op", help="Choices: remove, replace"),
    path: str = typer.Option(None, "--path", help="Only paths ending in `/sources/configured/value` are supported."),
    value: str = typer.Option(None, "--value", help="Value for replace op (JSON-parsed: string, number, bool, or array)"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    verify: bool = typer.Option(False, "--verify", help="After the write, re-read the resource and report any sent field that did not take. A 2xx means accepted, not applied."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Device Configurations.\n\n\b\nExample: wxcli device-configurations update --device-id DEVICE_ID\n\n\b\nExample --json-body: '{"op":"remove","path":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/deviceConfigurations"
    params = {}
    if device_id is not None:
        params["deviceId"] = device_id
    if json_body:
        body = load_json_body(json_body)
    else:
        patch_op = {}
        if op is not None:
            patch_op["op"] = op
        if path is not None:
            patch_op["path"] = path
        if value is not None:
            try:
                patch_op["value"] = json.loads(value)
            except json.JSONDecodeError:
                patch_op["value"] = value
        body = [patch_op]
    try:
        result = api.session.rest_patch(url, json=body, params=params, content_type="application/json-patch+json")
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if verify:
        verify_write(api, url, params, body)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated"}, output=output, fields=fields)


