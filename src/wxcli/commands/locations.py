import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json

app = typer.Typer(help="Manage Webex Calling locations.")


@app.command("list")
def list_locations(
    calling_only: bool = typer.Option(False, "--calling-only", help="Only calling-enabled locations"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results (0 for all)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List all locations in the organization."""
    api = get_api(debug=debug)

    if calling_only:
        locations = list(api.telephony.locations.list())
    else:
        locations = list(api.locations.list())

    if output == "json":
        print_json(locations)
    else:
        print_table(
            locations,
            columns=[
                ("ID", "location_id"),
                ("Name", "name"),
                ("City", "address.city"),
                ("State", "address.state"),
            ],
            limit=limit,
        )


@app.command("show")
def show_location(
    location_id: str = typer.Argument(help="Location ID"),
    output: str = typer.Option("json", "--output", "-o"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Show details for a single location."""
    api = get_api(debug=debug)
    location = api.locations.details(location_id=location_id)
    print_json(location)


@app.command("create")
def create_location(
    name: str = typer.Option(..., "--name", help="Location name"),
    timezone: str = typer.Option(..., "--timezone", help="Timezone e.g. America/New_York"),
    address: str = typer.Option(..., "--address", help="Street address"),
    city: str = typer.Option(..., "--city"),
    state: str = typer.Option(..., "--state"),
    zip_code: str = typer.Option(..., "--zip"),
    country: str = typer.Option("US", "--country"),
    language: str = typer.Option("en_US", "--language", help="Preferred and announcement language"),
    preferred_language: str = typer.Option(None, "--preferred-language"),
    announcement_language: str = typer.Option(None, "--announcement-language"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new location."""
    api = get_api(debug=debug)

    pref_lang = preferred_language or language
    ann_lang = announcement_language or language

    location_id = api.locations.create(
        name=name,
        time_zone=timezone,
        preferred_language=pref_lang,
        announcement_language=ann_lang,
        address1=address,
        city=city,
        state=state,
        postal_code=zip_code,
        country=country,
    )
    typer.echo(f"Created: {location_id} ({name})")


@app.command("enable-calling")
def enable_calling(
    location_id: str = typer.Argument(help="Location ID to enable calling on"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Enable Webex Calling on a location."""
    api = get_api(debug=debug)
    location = api.locations.details(location_id=location_id)
    # API requires announcement_language but details endpoint may return None
    if not location.announcement_language:
        location.announcement_language = (location.preferred_language or "en_US").lower()
    api.telephony.location.enable_for_calling(location=location)
    typer.echo(f"Enabled calling: {location_id} ({location.name})")


@app.command("update")
def update_location(
    location_id: str = typer.Argument(help="Location ID"),
    name: str = typer.Option(None, "--name"),
    timezone: str = typer.Option(None, "--timezone"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a location."""
    api = get_api(debug=debug)
    location = api.locations.details(location_id=location_id)
    if name:
        location.name = name
    if timezone:
        location.time_zone = timezone
    api.locations.update(location_id=location_id, settings=location)
    typer.echo(f"Updated: {location_id}")


@app.command("disable-calling")
def disable_calling(
    location_id: str = typer.Argument(help="Location ID to disable calling on"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Disable Webex Calling on a location."""
    api = get_api(debug=debug)
    url = api.telephony.location.ep(location_id)
    api.telephony.location.delete(url=url)
    typer.echo(f"Disabled calling: {location_id}")


@app.command("delete")
def delete_location(
    location_id: str = typer.Argument(help="Location ID"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a location. Automatically disables Webex Calling first if enabled."""
    if not force:
        typer.confirm(f"Delete location {location_id}?", abort=True)
    api = get_api(debug=debug)
    try:
        api.locations.delete(location_id=location_id)
    except RestError as e:
        if e.response.status_code == 409 and "being referenced" in e.response.text:
            typer.echo("Location has Webex Calling enabled — disabling calling first...")
            url = api.telephony.location.ep(location_id)
            api.telephony.location.delete(url=url)
            api.locations.delete(location_id=location_id)
        else:
            raise
    typer.echo(f"Deleted: {location_id}")
