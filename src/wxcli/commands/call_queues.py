import typer
from wxc_sdk.telephony.callqueue import CallQueue, CallQueueCallPolicies, CQRoutingType
from wxc_sdk.telephony.hg_and_cq import Agent, Policy
from wxcli.auth import get_api
from wxcli.output import print_table, print_json

app = typer.Typer(help="Manage Webex Calling call queues.")


@app.command("list")
def list_queues(
    location_id: str = typer.Option(None, "--location", help="Filter by location ID"),
    name: str = typer.Option(None, "--name", help="Filter by name"),
    phone_number: str = typer.Option(None, "--phone-number", help="Filter by phone number"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results (0 for all)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List call queues in the organization."""
    api = get_api(debug=debug)
    queues = list(api.telephony.callqueue.list(
        location_id=location_id,
        name=name,
        phone_number=phone_number,
    ))
    if output == "json":
        print_json(queues)
    else:
        print_table(
            queues,
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
def show_queue(
    location_id: str = typer.Argument(help="Location ID"),
    queue_id: str = typer.Argument(help="Call queue ID"),
    output: str = typer.Option("json", "--output", "-o"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Show details for a single call queue."""
    api = get_api(debug=debug)
    queue = api.telephony.callqueue.details(location_id=location_id, queue_id=queue_id)
    print_json(queue)


@app.command("create")
def create_queue(
    location_id: str = typer.Option(..., "--location", help="Location ID"),
    name: str = typer.Option(..., "--name", help="Call queue name"),
    extension: str = typer.Option(None, "--extension", help="Extension number"),
    phone_number: str = typer.Option(None, "--phone-number", help="Phone number"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Create a new call queue."""
    api = get_api(debug=debug)
    call_policies = CallQueueCallPolicies(
        routing_type=CQRoutingType.priority_based,
        policy=Policy.circular,
    )
    settings = CallQueue(
        name=name,
        extension=extension,
        phone_number=phone_number,
        call_policies=call_policies,
    )
    queue_id = api.telephony.callqueue.create(location_id=location_id, settings=settings)
    typer.echo(f"Created: {queue_id} ({name})")


@app.command("update")
def update_queue(
    location_id: str = typer.Argument(help="Location ID"),
    queue_id: str = typer.Argument(help="Call queue ID"),
    name: str = typer.Option(None, "--name", help="New name"),
    extension: str = typer.Option(None, "--extension", help="New extension"),
    phone_number: str = typer.Option(None, "--phone-number", help="New phone number"),
    enabled: bool = typer.Option(None, "--enabled/--disabled", help="Enable or disable"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a call queue."""
    api = get_api(debug=debug)
    # Use partial object to avoid callingLineIdPolicy issue from full details
    update_fields = {}
    if name is not None:
        update_fields["name"] = name
    if extension is not None:
        update_fields["extension"] = extension
    if phone_number is not None:
        update_fields["phone_number"] = phone_number
    if enabled is not None:
        update_fields["enabled"] = enabled
    update = CallQueue(**update_fields)
    api.telephony.callqueue.update(location_id=location_id, queue_id=queue_id, update=update)
    typer.echo(f"Updated: {queue_id}")


@app.command("delete")
def delete_queue(
    location_id: str = typer.Argument(help="Location ID"),
    queue_id: str = typer.Argument(help="Call queue ID"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Delete a call queue."""
    api = get_api(debug=debug)
    if not force:
        typer.confirm(f"Delete call queue {queue_id}?", abort=True)
    api.telephony.callqueue.delete_queue(location_id=location_id, queue_id=queue_id)
    typer.echo(f"Deleted: {queue_id}")


@app.command("add-agent")
def add_agent(
    location_id: str = typer.Argument(help="Location ID"),
    queue_id: str = typer.Argument(help="Call queue ID"),
    agent_id: str = typer.Argument(help="Agent (person) ID to add"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Add an agent to a call queue."""
    api = get_api(debug=debug)
    cq = api.telephony.callqueue.details(location_id=location_id, queue_id=queue_id)
    if cq.agents is None:
        cq.agents = []
    cq.agents.append(Agent(agent_id=agent_id))
    api.telephony.callqueue.update(location_id=location_id, queue_id=queue_id, update=cq)
    typer.echo(f"Agent {agent_id} added to queue {queue_id}")


@app.command("available-agents")
def available_agents(
    location_id: str = typer.Argument(help="Location ID"),
    name: str = typer.Option(None, "--name", help="Filter by agent name"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(50, "--limit", help="Max results (0 for all)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List agents available to be added to call queues in a location."""
    api = get_api(debug=debug)
    agents = list(api.telephony.callqueue.available_agents(location_id=location_id, name=name))
    if output == "json":
        print_json(agents)
    else:
        print_table(
            agents,
            columns=[
                ("ID", "id"),
                ("Name", "name"),
                ("Extension", "extension"),
                ("Phone", "phone_number"),
                ("Enabled", "enabled"),
            ],
            limit=limit,
        )
