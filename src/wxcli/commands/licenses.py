import typer
from wxcli.auth import get_api
from wxcli.output import print_table, print_json

app = typer.Typer(help="List and inspect Webex licenses.")


@app.command("list")
def list_licenses(
    calling_only: bool = typer.Option(False, "--calling-only", help="Only calling-related licenses"),
    output: str = typer.Option("table", "--output", "-o"),
    limit: int = typer.Option(50, "--limit"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List available licenses."""
    api = get_api(debug=debug)
    licenses = list(api.licenses.list())

    if calling_only:
        licenses = [lic for lic in licenses if "calling" in (lic.name or "").lower()]

    if output == "json":
        print_json(licenses)
    else:
        print_table(
            licenses,
            columns=[
                ("ID", "license_id"),
                ("Name", "name"),
                ("Total", "total_units"),
                ("Consumed", "consumed_units"),
            ],
            limit=limit,
        )


@app.command("show")
def show_license(
    license_id: str = typer.Argument(help="License ID"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Show details for a single license."""
    api = get_api(debug=debug)
    lic = api.licenses.details(license_id=license_id)
    print_json(lic)
