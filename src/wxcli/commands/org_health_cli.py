"""wxcli org-health — analyze collected org data and generate the HTML report.

Wraps wxcli.org_health so the org-health skill works under pipx installs,
where `python3.14 -m wxcli.org_health.*` cannot resolve (spec §4.5).
"""
from __future__ import annotations

import json
from pathlib import Path

import typer

from wxcli.org_health.analyze import run_analysis
from wxcli.org_health.collector import validate_collection
from wxcli.org_health.report import _deserialize_result, generate_report
from wxcli.output import plain_mode

app = typer.Typer(
    help="Org health assessment — analyze collected data, generate the report.",
    rich_markup_mode=None if plain_mode() else "rich",
)


@app.command()
def analyze(
    collected_dir: Path = typer.Argument(..., help="Path to the collected/ directory"),
    output: Path = typer.Option(..., "--output", help="Directory to write results.json into"),
):
    """Run all 18 health checks over collected JSON and write results.json."""
    errors = validate_collection(collected_dir)
    if errors:
        for e in errors:
            typer.echo(f"ERROR: {e}", err=True)
        raise typer.Exit(1)
    result = run_analysis(collected_dir)
    output.mkdir(parents=True, exist_ok=True)
    results_path = output / "results.json"
    results_path.write_text(json.dumps(result.to_dict(), indent=2))
    typer.echo(f"Results written to {results_path}")
    typer.echo(f"  Findings: {len(result.findings)} total")


@app.command()
def report(
    results_dir: Path = typer.Argument(..., help="Path to the results/ directory"),
    brand: str = typer.Option(..., "--brand", help="Customer/org brand name"),
    prepared_by: str = typer.Option(..., "--prepared-by", help="Name of the report author"),
):
    """Generate the self-contained HTML report from results.json."""
    results_path = results_dir / "results.json"
    if not results_path.exists():
        typer.echo(f"ERROR: results.json not found in {results_dir}", err=True)
        raise typer.Exit(1)
    result = _deserialize_result(json.loads(results_path.read_text()))
    report_dir = results_dir.parent / "report"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "org-health-report.html"
    report_path.write_text(generate_report(result, brand=brand, prepared_by=prepared_by))
    typer.echo(f"Report written to {report_path}")
