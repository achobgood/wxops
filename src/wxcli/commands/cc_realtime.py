import json
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error
from wxcli.output import print_table, print_json
from wxcli.config import get_cc_base_url


app = typer.Typer(help="Manage Webex Contact Center cc-realtime.")


@app.command("create")
def create(
    is_keep_alive_enabled: bool = typer.Option(None, "--is-keep-alive-enabled/--no-is-keep-alive-enabled", help="This represents that a json message {\\\"keepalive\\\":\\\"true\\\"} is expected over the websocket connection from Client. This should be sent periodically (usually 4s). If there are no keep-alive messages from the client for a period of 15 seconds, the server will drop the websocket."),
    client_type: str = typer.Option(None, "--client-type", help="ClientType is used to identify a web application differently from other web applications. It is used to group connections together for a specific user coming from that specific web application."),
    allow_multi_login: bool = typer.Option(None, "--allow-multi-login/--no-allow-multi-login", help="This cannot be used without providing \\\"clientType\\\". When set to true, it informs the server to allow multiple logins for this user coming from the same clientType. Upto 10 multiple logins will be allowed."),
    force: bool = typer.Option(None, "--force/--no-force", help="When true, will drop a random connection and then subscribes if connections for a user exceed maximum limit. When allowMultiLogin is false and a multi-login is attempted, if set to true will drop all connections for that user of that clientType & then subscribes."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Subscribe Realtime Notification."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/realtime/subscribe"
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


