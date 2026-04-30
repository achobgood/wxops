import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_cc_base_url


app = typer.Typer(help="Manage Webex Contact Center cc-notification.")


@app.command("create")
def create(
    is_keep_alive_enabled: bool = typer.Option(None, "--is-keep-alive-enabled/--no-is-keep-alive-enabled", help="This represents that a json message {\\\"keepalive\\\":\\\"true\\\"}"),
    client_type: str = typer.Option(None, "--client-type", help="ClientType is used to identify a web application differently"),
    allow_multi_login: bool = typer.Option(None, "--allow-multi-login/--no-allow-multi-login", help="This cannot be used without providing \\\"clientType\\\". When s"),
    force: bool = typer.Option(None, "--force/--no-force", help="When true, will drop a random connection and then subscribes"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Subscribe Notification."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/notification/subscribe"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if is_keep_alive_enabled is not None:
            body["isKeepAliveEnabled"] = is_keep_alive_enabled
        if client_type is not None:
            body["clientType"] = client_type
        if allow_multi_login is not None:
            body["allowMultiLogin"] = allow_multi_login
        if force is not None:
            body["force"] = force
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


