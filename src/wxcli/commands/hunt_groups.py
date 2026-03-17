import typer
from wxc_sdk.telephony.huntgroup import HuntGroup
from wxc_sdk.telephony.hg_and_cq import Agent
from wxcli.auth import get_api
from wxcli.output import print_table, print_json

app = typer.Typer(help="Manage Webex Calling hunt groups.")


@app.command("list")
def list_hunt_groups(
    location_id: str = typer.Option(None, "--location", help="Filter by location ID"),
    name: str = typer.Option(None, "--name", help="Filter by name"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter by phone number"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results (0 for all)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List hunt groups in the organization."""
    api = get_api(debug=debug)
    hunt_groups = list(api.telephony.huntgroup.list(
        location_id=location_id,
        name=name,
        phone_number=phone_number,
    ))
    if output == "json":
        print_json(hunt_groups)
    else:
        print_table(
            hunt_groups,
            columns=[
                ("ID", "id"),
                ("Name", "name"),
                ("Extension", "extension"),
                ("Phone", "phone_number"),
                ("Enabled", "enabled"),
            ],
            limit=limit,
        )


@app.command("show")
def show_hunt_group(
    location_id: str = typer.Argument(help="Location ID"),
    huntgroup_id: str = typer.Argument(help="Hunt group ID"),
    output: str = typer.Option("json", "--output", "-o"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Show details for a single hunt group."""
    api = get_api(debug=debug)
    hg = api.telephony.huntgroup.details(location_id=location_id, huntgroup_id=huntgroup_id)
    print_json(hg)


@app.command("create")
def create_hunt_group(
    location_id: str = typer.Option(..., "--location", help="Location ID"),
    name: str = typer.Option(..., "--name", help="Hunt group name"),
    extension: str = typer.Option(..., "--extension", help="Extension number"),
    phone_number: str = typer.Option(None, "--phone-number", help="Phone number"),
    enabled: bool = typer.Option(True, "--enabled/--disabled", help="Enable hunt group"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new hunt group."""
    api = get_api(debug=debug)
    settings = HuntGroup(
        name=name,
        extension=extension,
        phone_number=phone_number,
        enabled=enabled,
    )
    hg_id = api.telephony.huntgroup.create(location_id=location_id, settings=settings)
    typer.echo(f"Created: {hg_id} ({name})")


@app.command("update")
def update_hunt_group(
    location_id: str = typer.Argument(help="Location ID"),
    huntgroup_id: str = typer.Argument(help="Hunt group ID"),
    name: str = typer.Option(None, "--name", help="New name"),
    extension: str = typer.Option(None, "--extension", help="New extension"),
    phone_number: str = typer.Option(None, "--phone-number", help="New phone number"),
    enabled: bool = typer.Option(None, "--enabled/--disabled", help="Enable or disable"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a hunt group."""
    api = get_api(debug=debug)
    hg = api.telephony.huntgroup.details(location_id=location_id, huntgroup_id=huntgroup_id)
    if name is not None:
        hg.name = name
    if extension is not None:
        hg.extension = extension
    if phone_number is not None:
        hg.phone_number = phone_number
    if enabled is not None:
        hg.enabled = enabled
    api.telephony.huntgroup.update(location_id=location_id, huntgroup_id=huntgroup_id, update=hg)
    typer.echo(f"Updated: {huntgroup_id}")


@app.command("delete")
def delete_hunt_group(
    location_id: str = typer.Argument(help="Location ID"),
    huntgroup_id: str = typer.Argument(help="Hunt group ID"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a hunt group."""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete hunt group {huntgroup_id}?", abort=True)
    api.telephony.huntgroup.delete_huntgroup(location_id=location_id, huntgroup_id=huntgroup_id)
    typer.echo(f"Deleted: {huntgroup_id}")


@app.command("add-agent")
def add_agent(
    location_id: str = typer.Argument(help="Location ID"),
    hg_id: str = typer.Argument(help="Hunt group ID"),
    agent_id: str = typer.Argument(help="Agent (user) ID to add"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add an agent to a hunt group (read-modify-write)."""
    api = get_api(debug=debug)
    hg = api.telephony.huntgroup.details(location_id=location_id, huntgroup_id=hg_id)
    if hg.agents is None:
        hg.agents = []
    hg.agents.append(Agent(agent_id=agent_id))
    api.telephony.huntgroup.update(location_id=location_id, huntgroup_id=hg_id, update=hg)
    typer.echo(f"Added agent {agent_id} to hunt group {hg_id}")
