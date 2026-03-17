import typer
from wxcli.auth import get_api
from wxcli.output import print_table, print_json

app = typer.Typer(help="Manage phone numbers.")


@app.command("list")
def list_numbers(
    location_id: str = typer.Option(None, "--location", help="Filter by location"),
    available: bool = typer.Option(False, "--available", help="Only unassigned numbers"),
    output: str = typer.Option("table", "--output", "-o"),
    limit: int = typer.Option(50, "--limit"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List phone numbers in the organization."""
    api = get_api(debug=debug)

    kwargs = {}
    if location_id:
        kwargs["location_id"] = location_id

    numbers = list(api.telephony.phone_numbers(**kwargs))

    if available:
        numbers = [n for n in numbers if not n.owner]

    if output == "json":
        print_json(numbers)
    else:
        print_table(
            numbers,
            columns=[
                ("Number", "phone_number"),
                ("Type", "phone_number_type"),
                ("Owner", "owner.first_name"),
                ("Location", "location.name"),
            ],
            limit=limit,
        )
