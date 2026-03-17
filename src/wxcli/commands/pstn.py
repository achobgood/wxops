import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling pstn.")


@app.command("list")
def cmd_list(
    location_id: str = typer.Argument(help="locationId"),
    service_types: str = typer.Option(None, "--service-types", help="Use the `serviceTypes` parameter to fetch connections for th"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve PSTN Connection Options for a Location."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/pstn/locations/{location_id}/connectionOptions"
    params = {}
    if service_types is not None:
        params["serviceTypes"] = service_types
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
    items = result.get("connectionOptions", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update")
def update(
    location_id: str = typer.Argument(help="locationId"),
    id_param: str = typer.Option(None, "--id", help=""),
    premise_route_type: str = typer.Option(None, "--premise-route-type", help=""),
    premise_route_id: str = typer.Option(None, "--premise-route-id", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Setup PSTN Connection for a Location."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/pstn/locations/{location_id}/connection"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if id_param is not None:
            body["id"] = id_param
        if premise_route_type is not None:
            body["premiseRouteType"] = premise_route_type
        if premise_route_id is not None:
            body["premiseRouteId"] = premise_route_id
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("list-connection")
def list_connection(
    location_id: str = typer.Argument(help="locationId"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Retrieve PSTN Connection for a Location."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/pstn/locations/{location_id}/connection"
    params = {}
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
    items = result.get("connection", result if isinstance(result, list) else [])
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("update-emergency-address")
def update_emergency_address(
    phone_number: str = typer.Argument(help="phoneNumber"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update the Emergency Address for a Phone Number."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/pstn/numbers/{phone_number}/emergencyAddress"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")



@app.command("create")
def create(
    location_id: str = typer.Argument(help="locationId"),
    address1: str = typer.Option(None, "--address1", help=""),
    address2: str = typer.Option(None, "--address2", help=""),
    city: str = typer.Option(None, "--city", help=""),
    state: str = typer.Option(None, "--state", help=""),
    postal_code: str = typer.Option(None, "--postal-code", help=""),
    country: str = typer.Option(None, "--country", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Emergency Address Lookup to Verify if Address is Valid."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/pstn/locations/{location_id}/emergencyAddress/lookup"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if address1 is not None:
            body["address1"] = address1
        if address2 is not None:
            body["address2"] = address2
        if city is not None:
            body["city"] = city
        if state is not None:
            body["state"] = state
        if postal_code is not None:
            body["postalCode"] = postal_code
        if country is not None:
            body["country"] = country
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



@app.command("create-emergency-address")
def create_emergency_address(
    location_id: str = typer.Argument(help="locationId"),
    address1: str = typer.Option(None, "--address1", help=""),
    address2: str = typer.Option(None, "--address2", help=""),
    city: str = typer.Option(None, "--city", help=""),
    state: str = typer.Option(None, "--state", help=""),
    postal_code: str = typer.Option(None, "--postal-code", help=""),
    country: str = typer.Option(None, "--country", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add an Emergency Address to a Location."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/pstn/locations/{location_id}/emergencyAddress"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if address1 is not None:
            body["address1"] = address1
        if address2 is not None:
            body["address2"] = address2
        if city is not None:
            body["city"] = city
        if state is not None:
            body["state"] = state
        if postal_code is not None:
            body["postalCode"] = postal_code
        if country is not None:
            body["country"] = country
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



@app.command("update-emergency-addresses")
def update_emergency_addresses(
    location_id: str = typer.Argument(help="locationId"),
    address_id: str = typer.Argument(help="addressId"),
    address1: str = typer.Option(None, "--address1", help=""),
    address2: str = typer.Option(None, "--address2", help=""),
    city: str = typer.Option(None, "--city", help=""),
    state: str = typer.Option(None, "--state", help=""),
    postal_code: str = typer.Option(None, "--postal-code", help=""),
    country: str = typer.Option(None, "--country", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update the Emergency Address of a Location."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/telephony/pstn/locations/{location_id}/emergencyAddresses/{address_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if address1 is not None:
            body["address1"] = address1
        if address2 is not None:
            body["address2"] = address2
        if city is not None:
            body["city"] = city
        if state is not None:
            body["state"] = state
        if postal_code is not None:
            body["postalCode"] = postal_code
        if country is not None:
            body["country"] = country
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        if "25008" in str(e):
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Updated.")


