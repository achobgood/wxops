"""CUCM-to-Webex Calling migration CLI commands.

Wires the migration pipeline (Phases 01-07) into the wxcli CLI as
``wxcli cucm <command>``. Each pipeline command opens the project store,
checks prerequisites, calls the pipeline function, updates state, and
prints a summary.

(from phase-08-cucm-cli.md)
"""

from __future__ import annotations

import csv
import io
import json
import logging
import shutil
import subprocess
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import typer
from rich.console import Console
from rich.table import Table

from wxcli.commands.cucm_config import (
    DEFAULT_CONFIG,
    coerce_value,
    load_config,
    save_config,
)

logger = logging.getLogger(__name__)
console = Console()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MIGRATIONS_DIR = Path.home() / ".wxcli" / "migrations"
CURRENT_PROJECT_FILE = Path.home() / ".wxcli" / "current_project"

# Pipeline stages in execution order.
PIPELINE_STAGES = ["init", "discover", "normalize", "map", "analyze", "plan", "preflight"]

# Map each stage to its prerequisite stage.
STAGE_PREREQUISITES: dict[str, str] = {
    "discover": "init",
    "normalize": "discover",
    "map": "normalize",
    "analyze": "map",
    "plan": "analyze",
    "preflight": "plan",
}

# Severity → Rich color for decision tables.
SEVERITY_COLORS: dict[str, str] = {
    "CRITICAL": "bold red",
    "HIGH": "red",
    "MEDIUM": "yellow",
    "LOW": "green",
}

# ---------------------------------------------------------------------------
# Typer apps
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="cucm",
    help="CUCM-to-Webex Calling migration tools.",
    no_args_is_help=True,
)

config_app = typer.Typer(
    name="config",
    help="Migration project configuration.",
    no_args_is_help=True,
)
app.add_typer(config_app, name="config")

# ---------------------------------------------------------------------------
# Project resolution helpers
# ---------------------------------------------------------------------------


def _get_current_project() -> str | None:
    """Read the current project name from ~/.wxcli/current_project."""
    if CURRENT_PROJECT_FILE.exists():
        name = CURRENT_PROJECT_FILE.read_text().strip()
        return name if name else None
    return None


def _set_current_project(name: str) -> None:
    """Write the current project name."""
    CURRENT_PROJECT_FILE.parent.mkdir(parents=True, exist_ok=True)
    CURRENT_PROJECT_FILE.write_text(name)


def _resolve_project_dir(project: str | None) -> Path:
    """Resolve the project directory path, using current project as default."""
    name = project or _get_current_project()
    if not name:
        console.print(
            "[red]No project specified and no current project set.[/red]\n"
            "Run 'wxcli cucm init <name>' first, or pass --project <name>.",
        )
        raise typer.Exit(1)
    project_dir = MIGRATIONS_DIR / name
    if not project_dir.exists():
        console.print(f"[red]Project directory not found:[/red] {project_dir}")
        raise typer.Exit(1)
    return project_dir


# ---------------------------------------------------------------------------
# Pipeline stage tracking (stored in state.json alongside ProjectState)
# ---------------------------------------------------------------------------


def _load_state_data(project_dir: Path) -> dict[str, Any]:
    """Load the raw state.json dict."""
    state_path = project_dir / "state.json"
    if state_path.exists():
        with open(state_path) as f:
            return json.load(f)
    return {}


def _save_state_data(project_dir: Path, data: dict[str, Any]) -> None:
    """Write the raw state.json dict."""
    state_path = project_dir / "state.json"
    with open(state_path, "w") as f:
        json.dump(data, f, indent=2)


def _completed_stages(project_dir: Path) -> list[str]:
    """Read completed pipeline stages from state.json."""
    return _load_state_data(project_dir).get("completed_stages", [])


def _mark_stage_complete(project_dir: Path, stage: str) -> None:
    """Record a pipeline stage as completed in state.json and advance ProjectState."""
    data = _load_state_data(project_dir)
    stages = data.get("completed_stages", [])
    if stage not in stages:
        stages.append(stage)
    data["completed_stages"] = stages
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    _save_state_data(project_dir, data)

    # Advance ProjectState where transitions are defined
    _advance_project_state(project_dir, stage)


def _advance_project_state(project_dir: Path, stage: str) -> None:
    """Advance the MigrationState project-level state for major transitions."""
    from wxcli.migration.state import MigrationState, ProjectState, InvalidTransitionError

    state_path = project_dir / "state.json"
    if not state_path.exists():
        return

    ms = MigrationState(state_path)

    # Map CLI stages to ProjectState transitions
    # normalize/map have no dedicated ProjectState — they stay at DISCOVERED
    transitions: dict[str, list[ProjectState]] = {
        "discover": [ProjectState.CONNECTED, ProjectState.DISCOVERED],
        "analyze": [ProjectState.ANALYZED],
        "plan": [],  # handled specially below (READY or BLOCKED → PLANNED)
    }

    targets = transitions.get(stage)
    if targets is None:
        return

    for target in targets:
        try:
            ms.transition(target)
        except InvalidTransitionError:
            pass  # Already past this state (e.g., re-running a stage)


def _advance_to_planned(project_dir: Path, has_pending_decisions: bool) -> None:
    """Advance ProjectState through ANALYZED → READY/BLOCKED → PLANNED."""
    from wxcli.migration.state import MigrationState, ProjectState, InvalidTransitionError

    state_path = project_dir / "state.json"
    ms = MigrationState(state_path)

    # ANALYZED → READY or BLOCKED
    intermediate = ProjectState.BLOCKED if has_pending_decisions else ProjectState.READY
    try:
        ms.transition(intermediate)
    except InvalidTransitionError:
        pass

    # READY/BLOCKED → PLANNED
    try:
        ms.transition(ProjectState.PLANNED)
    except InvalidTransitionError:
        pass


def _check_prerequisite(project_dir: Path, stage: str) -> None:
    """Abort if the prerequisite stage hasn't been completed."""
    required = STAGE_PREREQUISITES.get(stage)
    if required is None:
        return
    completed = _completed_stages(project_dir)
    if required not in completed:
        console.print(
            f"[red]Cannot run '{stage}' — prerequisite '{required}' "
            f"has not been completed.[/red]\n"
            f"Completed stages: {', '.join(completed) if completed else '(none)'}",
        )
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# Store helper
# ---------------------------------------------------------------------------


def _open_store(project_dir: Path):
    """Open the MigrationStore for a project."""
    from wxcli.migration.store import MigrationStore

    db_path = project_dir / "migration.db"
    return MigrationStore(db_path)


# ===================================================================
# PROJECT MANAGEMENT COMMANDS
# ===================================================================


@app.command()
def init(
    project_name: str = typer.Argument(..., help="Name for the migration project"),
):
    """Create a new migration project directory with empty store and config."""
    project_dir = MIGRATIONS_DIR / project_name
    if project_dir.exists():
        console.print(f"[yellow]Project '{project_name}' already exists at {project_dir}[/yellow]")
        raise typer.Exit(1)

    project_dir.mkdir(parents=True)

    # Create migration.db (schema auto-created by MigrationStore)
    store = _open_store(project_dir)
    store.close()

    # Create state.json
    from wxcli.migration.state import MigrationState

    MigrationState.create(project_dir / "state.json", project_name)

    # Mark init stage + add completed_stages to state.json
    data = _load_state_data(project_dir)
    data["completed_stages"] = ["init"]
    _save_state_data(project_dir, data)

    # Create config.json with defaults
    save_config(project_dir, DEFAULT_CONFIG)

    # Set as current project
    _set_current_project(project_name)

    console.print(f"[green]Created migration project:[/green] {project_dir}")
    console.print(f"  migration.db  — SQLite store")
    console.print(f"  state.json    — pipeline state")
    console.print(f"  config.json   — project configuration")
    console.print(f"\nCurrent project set to '{project_name}'.")


@app.command()
def status(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
):
    """Show pipeline stage, object counts, and decision summary."""
    project_dir = _resolve_project_dir(project)
    state_data = _load_state_data(project_dir)
    completed = state_data.get("completed_stages", [])
    project_state = state_data.get("state", "initialized")

    console.print(f"[bold]Project:[/bold] {project_dir.name}")
    console.print(f"[bold]State:[/bold]   {project_state}")
    console.print(f"[bold]Stages:[/bold]  {' → '.join(completed) if completed else '(none)'}")

    # Object counts
    store = _open_store(project_dir)
    try:
        row = store.conn.execute(
            "SELECT object_type, COUNT(*) as cnt FROM objects GROUP BY object_type ORDER BY cnt DESC"
        ).fetchall()
        if row:
            console.print(f"\n[bold]Objects:[/bold]")
            total = 0
            for r in row:
                console.print(f"  {r['object_type']:<25s} {r['cnt']:>5d}")
                total += r["cnt"]
            console.print(f"  {'TOTAL':<25s} {total:>5d}")

        # Decision summary
        all_decisions = store.get_all_decisions()
        non_stale = [d for d in all_decisions if d.get("chosen_option") != "__stale__"]
        if non_stale:
            pending = [d for d in non_stale if d.get("chosen_option") is None]
            resolved = [d for d in non_stale if d.get("chosen_option") is not None]
            console.print(
                f"\n[bold]Decisions:[/bold] {len(non_stale)} total "
                f"({len(resolved)} resolved, {len(pending)} pending)"
            )
            if pending:
                by_severity: dict[str, int] = defaultdict(int)
                for d in pending:
                    by_severity[d.get("severity", "UNKNOWN")] += 1
                parts = []
                for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
                    cnt = by_severity.get(sev, 0)
                    if cnt:
                        color = SEVERITY_COLORS.get(sev, "white")
                        parts.append(f"[{color}]{sev}: {cnt}[/{color}]")
                console.print(f"  Pending: {', '.join(parts)}")

        # Plan summary
        plan_count = store.conn.execute("SELECT COUNT(*) as cnt FROM plan_operations").fetchone()
        if plan_count and plan_count["cnt"] > 0:
            console.print(f"\n[bold]Plan:[/bold] {plan_count['cnt']} operations")
    finally:
        store.close()


# ===================================================================
# CONFIG COMMANDS
# ===================================================================


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Config key to set"),
    value: str = typer.Argument(..., help="Value to set"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
):
    """Set a configuration value."""
    project_dir = _resolve_project_dir(project)
    config = load_config(project_dir)
    config[key] = coerce_value(value)
    save_config(project_dir, config)
    console.print(f"[green]Set[/green] {key} = {config[key]!r}")


@config_app.command("show")
def config_show(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
):
    """Show current project configuration."""
    project_dir = _resolve_project_dir(project)
    config = load_config(project_dir)
    console.print(f"[bold]Configuration:[/bold] {project_dir / 'config.json'}\n")
    for k, v in sorted(config.items()):
        console.print(f"  {k:<30s} {json.dumps(v)}")


# ===================================================================
# PIPELINE COMMANDS
# ===================================================================


@app.command()
def discover(
    host: Optional[str] = typer.Option(None, "--host", help="CUCM hostname or IP"),
    username: Optional[str] = typer.Option(None, "--username", help="AXL admin username"),
    password: Optional[str] = typer.Option(None, "--password", help="AXL admin password"),
    port: int = typer.Option(8443, "--port", help="AXL port"),
    version: str = typer.Option("14.0", "--version", help="AXL schema version"),
    wsdl: Optional[str] = typer.Option(None, "--wsdl", help="Path to local AXL WSDL file"),
    from_file: Optional[str] = typer.Option(None, "--from-file", help="Path to collector file (.json.gz or .json)"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
):
    """Extract objects from a live CUCM cluster via AXL, or load from a collector file."""
    project_dir = _resolve_project_dir(project)
    _check_prerequisite(project_dir, "discover")

    # Validate: must provide either --from-file or --host
    if not from_file and not host:
        console.print(
            "[red]Must provide either --from-file or --host.[/red]\n"
            "  Use --from-file to load a collector export file.\n"
            "  Use --host to connect to a live CUCM cluster via AXL."
        )
        raise typer.Exit(1)

    # --from-file path: ingest collector file, skip AXL
    if from_file:
        from wxcli.migration.report.ingest import ingest_collector_file

        file_path = Path(from_file)
        if not file_path.exists():
            console.print(f"[red]Collector file not found:[/red] {file_path}")
            raise typer.Exit(1)

        console.print(f"[bold]Loading collector file[/bold]: {file_path.name}...")
        t0 = time.time()

        try:
            raw_data, metadata = ingest_collector_file(file_path)
        except ValueError as exc:
            console.print(f"[red]Invalid collector file:[/red] {exc}")
            raise typer.Exit(1)

        # Save collector metadata (cucm_version, cluster_name) to project config
        from wxcli.commands.cucm_config import load_config, save_config

        cfg = load_config(project_dir)
        cfg["cucm_version"] = metadata.get("cucm_version", "")
        cfg["cluster_name"] = metadata.get("cluster_name", "")
        save_config(project_dir, cfg)

        # Persist raw_data for the normalize command
        raw_data_path = project_dir / "raw_data.json"
        with open(raw_data_path, "w") as f:
            json.dump(raw_data, f, default=str)

        # Record journal entry
        store = _open_store(project_dir)
        try:
            store.add_journal_entry(
                entry_type="file_ingestion",
                canonical_id="system:discovery",
                resource_type="collector_file",
                request={"file": str(file_path)},
                response={"groups": list(raw_data.keys())},
            )
        finally:
            store.close()

        _mark_stage_complete(project_dir, "discover")
        elapsed = time.time() - t0

        # Print summary
        total = 0
        console.print(f"\n[green]File ingestion complete[/green] in {elapsed:.1f}s")
        console.print(f"  Source: {file_path.name}")
        for group, sub_data in raw_data.items():
            group_total = sum(len(v) for v in sub_data.values() if isinstance(v, list))
            total += group_total
            console.print(f"    {group:<15s} {group_total:>5d} objects")
        console.print(f"  Total objects: {total}")
        return

    # Live AXL path — prompt for password if not provided
    if not password and not from_file:
        password = typer.prompt("AXL admin password", hide_input=True)
    if not username:
        console.print("[red]--username is required for live AXL discovery.[/red]")
        raise typer.Exit(1)

    from wxcli.migration.cucm.connection import AXLConnection
    from wxcli.migration.cucm.discovery import run_discovery

    console.print(f"[bold]Connecting to CUCM[/bold] at {host}:{port} (AXL v{version})...")
    t0 = time.time()

    try:
        conn = AXLConnection(
            host=host,
            username=username,
            password=password,
            version=version,
            wsdl_path=wsdl,
        )
    except Exception as exc:
        err_str = str(exc)
        console.print(f"[red]Connection failed:[/red] {exc}")
        if "403" in err_str and "wsdl" in err_str.lower():
            console.print(
                "\n[yellow]Tip:[/yellow] CUCM is blocking remote WSDL download (403).\n"
                "Download the AXL WSDL locally and use --wsdl:\n"
                "  1. CUCM Admin > Application > Plugins > Cisco AXL Toolkit > Download\n"
                "  2. Unzip — the WSDL is at schema/current/AXLAPI.wsdl\n"
                f"  3. Re-run with: wxcli cucm discover --host {host} --username {username} "
                f"--wsdl /path/to/AXLAPI.wsdl --version {version}"
            )
        elif "401" in err_str:
            console.print(
                "\n[yellow]Tip:[/yellow] Authentication failed. Check your AXL username/password "
                "and ensure the user has the 'Standard AXL API Access' role in CUCM."
            )
        elif "Connection refused" in err_str or "timed out" in err_str.lower():
            console.print(
                f"\n[yellow]Tip:[/yellow] Cannot reach {host}:{port}. Check:\n"
                "  - CUCM is reachable from this machine\n"
                "  - Port 8443 is open (firewall)\n"
                "  - The Cisco AXL Web Service is activated in CUCM Serviceability"
            )
        raise typer.Exit(1)

    store = _open_store(project_dir)
    try:
        result = run_discovery(conn, store)

        # Persist raw_data for the normalize command
        raw_data_path = project_dir / "raw_data.json"
        with open(raw_data_path, "w") as f:
            json.dump(result.raw_data, f, default=str)

        _mark_stage_complete(project_dir, "discover")
        elapsed = time.time() - t0

        console.print(f"\n[green]Discovery complete[/green] in {elapsed:.1f}s")
        console.print(f"  CUCM version: {result.cucm_version}")
        console.print(f"  Total objects: {result.total_objects}")
        if result.total_failed:
            console.print(f"  [yellow]Failed: {result.total_failed}[/yellow]")
        for name, ext_result in result.extractor_results.items():
            console.print(f"    {name:<15s} {ext_result.total:>5d} extracted")
    except Exception as exc:
        console.print(f"[red]Discovery failed:[/red] {exc}")
        logger.exception("Discovery failed")
        raise typer.Exit(1)
    finally:
        store.close()


@app.command()
def normalize(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
):
    """Run pass 1 normalizers + pass 2 cross-reference builder."""
    project_dir = _resolve_project_dir(project)
    _check_prerequisite(project_dir, "normalize")

    raw_data_path = project_dir / "raw_data.json"
    if not raw_data_path.exists():
        console.print("[red]raw_data.json not found — run 'discover' first.[/red]")
        raise typer.Exit(1)

    from wxcli.migration.transform.pipeline import normalize_discovery

    with open(raw_data_path) as f:
        raw_data = json.load(f)

    config = load_config(project_dir)
    store = _open_store(project_dir)
    t0 = time.time()

    try:
        summary = normalize_discovery(
            raw_data=raw_data,
            store=store,
            default_country_code=config.get("default_country", "US"),
            site_prefix_rules=config.get("site_prefix_rules"),
        )
        _mark_stage_complete(project_dir, "normalize")
        elapsed = time.time() - t0

        console.print(f"\n[green]Normalization complete[/green] in {elapsed:.1f}s")
        pass1 = summary.get("pass1", {})
        console.print(f"  Pass 1 objects: {pass1.get('total', 0)}")
        for k, v in sorted(pass1.items()):
            if k != "total" and isinstance(v, int) and v > 0:
                console.print(f"    {k:<35s} {v:>5d}")
        pass2 = summary.get("pass2", {})
        xref_total = sum(v for v in pass2.values() if isinstance(v, int))
        if xref_total:
            console.print(f"  Pass 2 cross-refs: {xref_total}")
    except Exception as exc:
        console.print(f"[red]Normalization failed:[/red] {exc}")
        logger.exception("Normalization failed")
        raise typer.Exit(1)
    finally:
        store.close()


@app.command("map")
def map_cmd(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
):
    """Run 9 transform mappers to produce canonical Webex objects + decisions."""
    project_dir = _resolve_project_dir(project)
    _check_prerequisite(project_dir, "map")

    from wxcli.migration.transform.engine import TransformEngine

    config = load_config(project_dir)
    store = _open_store(project_dir)
    t0 = time.time()

    try:
        engine = TransformEngine(config=config)
        result = engine.run(store)
        _mark_stage_complete(project_dir, "map")
        elapsed = time.time() - t0

        console.print(f"\n[green]Mapping complete[/green] in {elapsed:.1f}s")
        console.print(f"  Decisions: {len(result.decisions)}")
        if result.errors:
            console.print(f"  [yellow]Mapper errors: {len(result.errors)}[/yellow]")
            for err in result.errors:
                console.print(f"    {err.mapper_name}: {err.error_message}")
    except Exception as exc:
        console.print(f"[red]Mapping failed:[/red] {exc}")
        logger.exception("Mapping failed")
        raise typer.Exit(1)
    finally:
        store.close()


@app.command()
def analyze(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
):
    """Run 12 analyzers + auto-rules + merge decisions."""
    project_dir = _resolve_project_dir(project)
    _check_prerequisite(project_dir, "analyze")

    from wxcli.migration.transform.analysis_pipeline import AnalysisPipeline
    from wxcli.migration.transform.decisions import format_decision_report

    config = load_config(project_dir)
    store = _open_store(project_dir)
    t0 = time.time()

    try:
        pipeline = AnalysisPipeline(config=config)
        result = pipeline.run(store)
        _mark_stage_complete(project_dir, "analyze")
        elapsed = time.time() - t0

        console.print(f"\n[green]Analysis complete[/green] in {elapsed:.1f}s")
        console.print(f"  Decisions produced: {len(result.decisions)}")
        for analyzer_name, count in sorted(result.stats.items()):
            if count == -1:
                console.print(f"    {analyzer_name:<35s} [red]FAILED[/red]")
            elif count > 0:
                console.print(f"    {analyzer_name:<35s} {count:>3d} decisions")

        # Print full decision report
        all_decisions = store.get_all_decisions()
        non_stale = [d for d in all_decisions if d.get("chosen_option") != "__stale__"]
        if non_stale:
            console.print()
            console.print(format_decision_report(non_stale))
    except Exception as exc:
        console.print(f"[red]Analysis failed:[/red] {exc}")
        logger.exception("Analysis failed")
        raise typer.Exit(1)
    finally:
        store.close()


@app.command()
def plan(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
):
    """Expand objects to operations, build dependency DAG, partition into batches."""
    project_dir = _resolve_project_dir(project)
    _check_prerequisite(project_dir, "plan")

    from wxcli.migration.execute.batch import (
        format_batch_plan,
        partition_into_batches,
        save_plan_to_store,
    )
    from wxcli.migration.execute.dependency import (
        build_dependency_graph,
        create_fixup_operations,
        detect_and_break_cycles,
        validate_tiers,
    )
    from wxcli.migration.execute.planner import expand_to_operations

    store = _open_store(project_dir)
    t0 = time.time()

    try:
        # Step 1: Expand to operations
        ops = expand_to_operations(store)
        console.print(f"  Expanded to {len(ops)} operations")

        # Step 2: Build dependency graph
        G = build_dependency_graph(ops, store)
        console.print(f"  Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

        # Step 3: Validate tiers
        violations = validate_tiers(G)
        if violations:
            console.print(f"  [yellow]Tier violations: {len(violations)}[/yellow]")
            for v in violations[:5]:
                console.print(f"    {v}")

        # Step 4: Detect and break cycles
        broken_cycles, cycle_errors = detect_and_break_cycles(G)
        if broken_cycles:
            create_fixup_operations(broken_cycles, G)
            console.print(f"  Broke {len(broken_cycles)} cycle(s) — fixup ops created")
        if cycle_errors:
            for err in cycle_errors:
                console.print(f"  [red]{err}[/red]")

        # Step 5: Partition into batches
        batches = partition_into_batches(G)

        # Step 6: Save plan to SQLite
        save_plan_to_store(G, store)

        # Check pending decisions for state transition
        from wxcli.migration.transform.decisions import pending_decisions as _pending

        has_pending = len(_pending(store)) > 0

        _mark_stage_complete(project_dir, "plan")
        _advance_to_planned(project_dir, has_pending)
        elapsed = time.time() - t0

        console.print(f"\n[green]Planning complete[/green] in {elapsed:.1f}s")
        console.print(format_batch_plan(batches))
    except Exception as exc:
        console.print(f"[red]Planning failed:[/red] {exc}")
        logger.exception("Planning failed")
        raise typer.Exit(1)
    finally:
        store.close()


# ===================================================================
# PREFLIGHT COMMAND
# ===================================================================


# Rich symbols and colors for preflight output
_STATUS_SYMBOLS = {
    "PASS": ("[green]✓ PASS[/green]", "green"),
    "WARN": ("[yellow]⚠ WARN[/yellow]", "yellow"),
    "FAIL": ("[red]✗ FAIL[/red]", "red"),
    "SKIP": ("[dim]○ SKIP[/dim]", "dim"),
}


@app.command()
def preflight(
    check: Optional[str] = typer.Option(
        None, "--check", "-c",
        help="Run only this check: licenses, workspace-licenses, locations, trunks, features, numbers, users, rate-limit",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be checked without querying Webex"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table or json"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
):
    """Run preflight checks against live Webex org before migration."""
    project_dir = _resolve_project_dir(project)
    _check_prerequisite(project_dir, "preflight")

    from wxcli.migration.preflight import CheckStatus
    from wxcli.migration.preflight.runner import PreflightRunner

    config = load_config(project_dir)
    store = _open_store(project_dir)
    t0 = time.time()

    try:
        runner = PreflightRunner(config=config)
        result = runner.run(store, check_filter=check, dry_run=dry_run)
        elapsed = time.time() - t0

        if output == "json":
            _preflight_json_output(result)
        else:
            _preflight_table_output(result, elapsed)

        # Store preflight result in state.json
        if not dry_run:
            data = _load_state_data(project_dir)
            data["preflight_result"] = result.overall.value
            data["preflight_checks"] = [
                {"name": c.name, "status": c.status.value, "detail": c.detail}
                for c in result.checks
            ]
            _save_state_data(project_dir, data)

            if result.overall != CheckStatus.FAIL:
                _mark_stage_complete(project_dir, "preflight")

                # Advance project state to PREFLIGHT
                from wxcli.migration.state import MigrationState, ProjectState, InvalidTransitionError
                state_path = project_dir / "state.json"
                ms = MigrationState(state_path)
                try:
                    ms.transition(ProjectState.PREFLIGHT)
                except InvalidTransitionError:
                    pass

    except Exception as exc:
        console.print(f"[red]Preflight failed:[/red] {exc}")
        logger.exception("Preflight failed")
        raise typer.Exit(1)
    finally:
        store.close()


def _preflight_table_output(result, elapsed: float) -> None:
    """Print Rich formatted preflight results."""
    from wxcli.migration.preflight import CheckStatus

    console.print(f"\n[bold]Preflight Check Results:[/bold] ({elapsed:.1f}s)\n")

    for check in result.checks:
        symbol, _ = _STATUS_SYMBOLS.get(check.status.value, ("[dim]?[/dim]", "dim"))
        console.print(f"  {symbol}  {check.name}: {check.detail}")

    # Overall
    overall_sym, _ = _STATUS_SYMBOLS.get(result.overall.value, ("[dim]?[/dim]", "dim"))
    console.print(f"\n[bold]Overall:[/bold] {overall_sym}")

    if result.new_decision_ids:
        ids_str = ", ".join(result.new_decision_ids[:10])
        if len(result.new_decision_ids) > 10:
            ids_str += f" ... +{len(result.new_decision_ids) - 10} more"
        console.print(f"  New decisions: {ids_str}")
        console.print("  Run 'wxcli cucm decisions --status pending' to review.")

    if result.overall == CheckStatus.FAIL:
        fail_checks = [c for c in result.checks if c.status == CheckStatus.FAIL]
        console.print(f"\n[red]  {len(fail_checks)} blocking issue(s) must be fixed:[/red]")
        for i, c in enumerate(fail_checks, 1):
            for issue in c.issues:
                console.print(f"    {i}. {issue.detail}")
        console.print("\n  After fixing, run [bold]wxcli cucm preflight[/bold] again.")


def _preflight_json_output(result) -> None:
    """Print JSON preflight results.
    (from 05a-preflight-checks.md, JSON output format)
    """
    import json as json_mod
    data = {
        "overall": result.overall.value,
        "checks": [
            {
                "name": c.name,
                "status": c.status.value,
                "detail": c.detail,
                "data": c.data,
            }
            for c in result.checks
        ],
        "new_decisions": result.new_decision_ids,
        "merge_result": result.merge_result,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    typer.echo(json_mod.dumps(data, indent=2))


# ===================================================================
# DECISION MANAGEMENT COMMANDS
# ===================================================================


@app.command()
def decisions(
    type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by decision type"),
    severity: Optional[str] = typer.Option(None, "--severity", "-s", help="Filter by severity"),
    status_filter: Optional[str] = typer.Option(None, "--status", help="Filter: pending or resolved"),
    export_review: bool = typer.Option(False, "--export-review", help="Generate markdown decision review file"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Output format: table (default) or json"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
):
    """List all migration decisions in a Rich table."""
    project_dir = _resolve_project_dir(project)
    store = _open_store(project_dir)

    try:
        def _serialize_decision(d):
            """Strip non-serializable fields for JSON output."""
            return {
                "decision_id": d.get("decision_id"),
                "type": d.get("type"),
                "severity": d.get("severity"),
                "summary": d.get("summary"),
                "options": d.get("options", []),
                "context": d.get("context", {}),
                "affected_objects": d.get("affected_objects", []),
                "auto_choice": d.get("auto_choice"),
                "auto_reason": d.get("auto_reason"),
                "recommendation": d.get("recommendation"),
                "recommendation_reasoning": d.get("recommendation_reasoning"),
            }

        # --export-review: generate markdown review file + optional JSON
        if export_review:
            import json as json_mod
            from wxcli.migration.transform.decisions import (
                classify_decisions, generate_decision_review,
            )
            project_id = project_dir.name if hasattr(project_dir, "name") else str(project_dir).split("/")[-1]

            # Always write the markdown file for admin offline review
            content = generate_decision_review(store, project_id)
            exports_dir = project_dir / "exports"
            exports_dir.mkdir(parents=True, exist_ok=True)
            review_path = exports_dir / "decision-review.md"
            review_path.write_text(content)

            auto, needs = classify_decisions(store)

            if output == "json":
                # JSON output for agent consumption — structured data
                data = {
                    "review_file": str(review_path),
                    "auto_apply": [_serialize_decision(d) for d in auto],
                    "needs_input": [_serialize_decision(d) for d in needs],
                }
                typer.echo(json_mod.dumps(data, indent=2))
            else:
                console.print(f"[green]Decision review written to:[/green] {review_path}")
                console.print(f"  Auto-apply: {len(auto)} decisions")
                console.print(f"  Needs input: {len(needs)} decisions")
            return

        all_decisions = store.get_all_decisions()
        # Exclude stale
        decs = [d for d in all_decisions if d.get("chosen_option") != "__stale__"]

        # Apply filters
        if type:
            filter_val = ("ARCHITECTURE_ADVISORY" if type.lower() == "advisory"
                          else type.upper())
            decs = [d for d in decs if d.get("type") == filter_val]
        if severity:
            decs = [d for d in decs if d.get("severity") == severity.upper()]
        if status_filter:
            if status_filter.lower() == "pending":
                decs = [d for d in decs if d.get("chosen_option") is None]
            elif status_filter.lower() == "resolved":
                decs = [d for d in decs if d.get("chosen_option") is not None]

        if not decs:
            if output == "json":
                typer.echo("[]")
            else:
                console.print("No decisions found matching filters.")
            return

        # JSON output for filtered decisions (without --export-review)
        if output == "json":
            import json as json_mod
            data = [_serialize_decision(d) for d in decs]
            typer.echo(json_mod.dumps(data, indent=2))
            return

        # Summary line
        pending = sum(1 for d in decs if d.get("chosen_option") is None)
        resolved = len(decs) - pending
        console.print(
            f"\n[bold]Migration Decisions:[/bold] {pending} pending, {resolved} resolved\n"
        )

        # Rich table
        table = Table(show_header=True, header_style="bold")
        table.add_column("ID", style="cyan", width=6)
        table.add_column("Type", width=30)
        table.add_column("Severity", width=10)
        table.add_column("Summary", width=50)
        table.add_column("Status", width=10)

        for d in decs:
            sev = d.get("severity", "")
            color = SEVERITY_COLORS.get(sev, "white")
            chosen = d.get("chosen_option")
            status_str = chosen if chosen else "pending"
            table.add_row(
                d.get("decision_id", ""),
                d.get("type", ""),
                f"[{color}]{sev}[/{color}]",
                d.get("summary", "")[:50],
                status_str,
            )

        console.print(table)

        # Show recommendations below the table
        recs_shown = False
        for d in decs:
            rec = d.get("recommendation")
            if rec:
                if not recs_shown:
                    console.print("\n[bold]Recommendations:[/bold]")
                    recs_shown = True
                rec_text = d.get("recommendation_reasoning", "")
                console.print(
                    f"  {d.get('decision_id', '')}  "
                    f"[cyan][REC: {rec}][/cyan] {rec_text}"
                )

        # Filter hints
        console.print(
            "\nFilters: --type <TYPE>  --severity HIGH  --status pending"
        )
    finally:
        store.close()


@app.command()
def decide(
    decision_id: Optional[str] = typer.Argument(None, help="Decision ID to resolve (e.g. D001)"),
    choice: Optional[str] = typer.Argument(None, help="Chosen option ID"),
    type: Optional[str] = typer.Option(None, "--type", "-t", help="Decision type for batch resolve"),
    all_: bool = typer.Option(False, "--all", help="Batch resolve all matching decisions"),
    batch_choice: Optional[str] = typer.Option(None, "--choice", help="Choice for batch resolve"),
    apply_auto: bool = typer.Option(False, "--apply-auto", help="Apply all auto-resolvable decisions"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt (for non-interactive use)"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
):
    """Resolve a single decision or batch-resolve by type."""
    project_dir = _resolve_project_dir(project)
    store = _open_store(project_dir)

    try:
        # --apply-auto: resolve only the clear-cut decisions
        if apply_auto:
            from wxcli.migration.transform.decisions import classify_decisions
            auto, _needs = classify_decisions(store)
            if not auto:
                console.print("No auto-resolvable decisions found.")
                return

            # Show what will be applied
            console.print(f"\n[bold]Auto-apply:[/bold] {len(auto)} clear-cut decisions\n")
            by_type: dict[str, list[dict]] = {}
            for d in auto:
                t = d.get("type", "UNKNOWN")
                by_type.setdefault(t, []).append(d)
            for t, decs in sorted(by_type.items()):
                choice = decs[0].get("auto_choice", "skip")
                console.print(f"  {len(decs)} {t} → {choice}")

            if not yes and not typer.confirm(f"\nApply {len(auto)} auto-resolved decisions?"):
                console.print("Cancelled.")
                return

            for d in auto:
                store.resolve_decision(
                    d["decision_id"], d["auto_choice"], resolved_by="auto_apply"
                )
            console.print(f"[green]Auto-applied {len(auto)} decisions.[/green]")
            return

        # Batch resolve mode
        if all_ and type and batch_choice:
            all_decisions = store.get_all_decisions()
            targets = [
                d for d in all_decisions
                if d.get("type") == type
                and d.get("chosen_option") is None
            ]
            if not targets:
                console.print(f"No pending {type} decisions to resolve.")
                return

            console.print(f"\n[bold]Batch resolve:[/bold] {len(targets)} {type} decisions → {batch_choice}\n")
            for d in targets[:10]:
                console.print(f"  {d['decision_id']}: {d.get('summary', '')[:60]}")
            if len(targets) > 10:
                console.print(f"  ... and {len(targets) - 10} more")

            if not yes and not typer.confirm(f"\nResolve all {len(targets)} decisions as '{batch_choice}'?"):
                console.print("Cancelled.")
                return

            for d in targets:
                store.resolve_decision(d["decision_id"], batch_choice, resolved_by="batch")
            console.print(f"[green]Resolved {len(targets)} decisions as '{batch_choice}'[/green]")
            return

        # Single decision resolve
        if not decision_id:
            console.print("[red]Provide a decision ID or use --type --all --choice for batch.[/red]")
            raise typer.Exit(1)

        decision = store.get_decision(decision_id)
        if decision is None:
            console.print(f"[red]Decision {decision_id} not found.[/red]")
            raise typer.Exit(1)

        # Show decision detail
        sev = decision.get("severity", "")
        color = SEVERITY_COLORS.get(sev, "white")
        console.print(f"\n[bold]{decision.get('type')}:[/bold] [{color}]{sev}[/{color}]")
        console.print(f"  {decision.get('summary', '')}\n")

        # Show context details
        context = decision.get("context", {})
        for k, v in context.items():
            if k.startswith("_"):
                continue
            if isinstance(v, list) and len(v) <= 5:
                console.print(f"  {k}: {', '.join(str(x) for x in v)}")
            elif not isinstance(v, (dict, list)):
                console.print(f"  {k}: {v}")

        # Show options
        options = decision.get("options", [])
        if options:
            console.print(f"\n[bold]Options:[/bold]")
            for i, opt in enumerate(options, 1):
                if isinstance(opt, dict):
                    console.print(f"  [{i}] {opt.get('id', '?')} — {opt.get('label', '')}")
                    if opt.get("impact"):
                        console.print(f"      Impact: {opt['impact']}")
                else:
                    console.print(f"  [{i}] {opt}")

        # Resolve (resolve_and_cascade handles both resolution and cascading)
        if choice is None:
            choice = typer.prompt("Select option")

        from wxcli.migration.transform.analysis_pipeline import AnalysisPipeline

        pipeline = AnalysisPipeline()
        warnings = pipeline.resolve_and_cascade(store, decision_id, choice, resolved_by="user")
        console.print(f"\n[green]Resolved {decision_id}: {choice}[/green]")
        for w in warnings:
            console.print(f"  [yellow]{w}[/yellow]")
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[red]Error resolving decision:[/red] {exc}")
        raise typer.Exit(1)
    finally:
        store.close()


# ===================================================================
# EXPORT COMMANDS
# ===================================================================


@app.command()
def export(
    format: str = typer.Option(
        "deployment-plan", "--format", "-f",
        help="Export format: deployment-plan, json, csv-decisions",
    ),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
):
    """Export migration data in various formats."""
    project_dir = _resolve_project_dir(project)
    store = _open_store(project_dir)

    try:
        if format == "deployment-plan":
            _export_deployment_plan(project_dir, store)
        elif format == "json":
            _export_json(project_dir, store)
        elif format == "csv-decisions":
            _export_csv_decisions(project_dir, store)
        else:
            console.print(
                f"[red]Unknown format: {format}[/red]\n"
                "Valid formats: deployment-plan, json, csv-decisions"
            )
            raise typer.Exit(1)
    finally:
        store.close()


def _export_deployment_plan(project_dir: Path, store) -> None:
    """Export a summary-only deployment plan for admin review.

    Generates an 8-section summary (no CLI commands, no placeholders).
    Also copies to docs/plans/ for builder agent discovery.
    """
    from wxcli.migration.export.deployment_plan import generate_plan_summary

    # Verify plan operations exist
    op_count = store.conn.execute(
        "SELECT COUNT(*) as cnt FROM plan_operations"
    ).fetchone()["cnt"]
    if op_count == 0:
        console.print(
            "[red]Execution plan is empty.[/red] Run `wxcli cucm plan` first."
        )
        raise typer.Exit(1)

    project_id = project_dir.name
    plan_md = generate_plan_summary(store, project_id)

    # Write to project exports directory
    exports_dir = project_dir / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    output_path = exports_dir / "deployment-plan.md"
    output_path.write_text(plan_md)
    console.print(f"[green]Deployment plan exported:[/green] {output_path}")

    # Copy to docs/plans/ for builder agent discovery
    docs_plans_dir = Path("docs/plans")
    if docs_plans_dir.exists():
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        plans_path = docs_plans_dir / f"{today}-cucm-migration-{project_id}.md"
        plans_path.write_text(plan_md)
        console.print(f"[green]Builder-ready copy:[/green] {plans_path}")


def _export_json(project_dir: Path, store) -> None:
    """Export full migration state as JSON."""
    from wxcli.migration.export.json_export import generate_json_export

    data = generate_json_export(store, project_dir.name)

    exports_dir = project_dir / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    output_path = exports_dir / "export.json"
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    console.print(f"[green]JSON export:[/green] {output_path}")


def _export_csv_decisions(project_dir: Path, store) -> None:
    """Export decisions as CSV for stakeholder review."""
    from wxcli.migration.export.csv_export import generate_csv_decisions, has_decisions

    if not has_decisions(store):
        console.print("No decisions to export.")
        return

    csv_content = generate_csv_decisions(store)

    exports_dir = project_dir / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    output_path = exports_dir / "decisions.csv"
    output_path.write_text(csv_content)
    console.print(f"[green]CSV decisions exported:[/green] {output_path}")


# ===================================================================
# INVENTORY BROWSING
# ===================================================================


@app.command()
def inventory(
    type: Optional[str] = typer.Option(None, "--type", "-t", help="Object type to list"),
    filter: Optional[str] = typer.Option(None, "--filter", help="Key=value filter"),
    output: str = typer.Option("table", "--output", "-o", help="Output: table, detail, json"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
):
    """Browse the migration inventory — summary counts or object details."""
    project_dir = _resolve_project_dir(project)
    store = _open_store(project_dir)

    try:
        if type is None:
            # Summary counts by type
            rows = store.conn.execute(
                "SELECT object_type, COUNT(*) as cnt FROM objects GROUP BY object_type ORDER BY cnt DESC"
            ).fetchall()
            if not rows:
                console.print("No objects in inventory.")
                return

            table = Table(title="Migration Inventory", show_header=True, header_style="bold")
            table.add_column("Object Type", width=25)
            table.add_column("Count", justify="right", width=8)
            total = 0
            for r in rows:
                table.add_row(r["object_type"], str(r["cnt"]))
                total += r["cnt"]
            table.add_row("[bold]TOTAL[/bold]", f"[bold]{total}[/bold]")
            console.print(table)
            return

        # List objects of a specific type
        objects = store.get_objects(type)
        if not objects:
            console.print(f"No '{type}' objects found.")
            return

        # Apply filter
        if filter:
            key, _, val = filter.partition("=")
            objects = [o for o in objects if _matches_filter(o, key.strip(), val.strip())]
            if not objects:
                console.print(f"No '{type}' objects matching filter '{filter}'.")
                return

        if output == "json":
            typer.echo(json.dumps(objects, indent=2, default=str))
            return

        if output == "detail":
            _print_object_detail(objects, store)
            return

        # Table output — auto-detect columns
        _print_inventory_table(type, objects)
    finally:
        store.close()


def _matches_filter(obj: dict, key: str, value: str) -> bool:
    """Check if an object matches a key=value filter."""
    obj_val = obj.get(key)
    if obj_val is None:
        return False
    if isinstance(obj_val, list):
        return value in [str(v) for v in obj_val]
    return str(obj_val).lower() == value.lower()


def _print_inventory_table(obj_type: str, objects: list[dict]) -> None:
    """Print objects in a Rich table with auto-detected columns."""
    if not objects:
        return

    # Pick columns: canonical_id + name/display_name + status + a few more
    cols = [("ID", "canonical_id")]
    for name_field in ("name", "display_name", "pattern", "extension"):
        if name_field in objects[0]:
            cols.append((name_field.replace("_", " ").title(), name_field))
            break
    if "status" in objects[0]:
        cols.append(("Status", "status"))
    if "location_id" in objects[0]:
        cols.append(("Location", "location_id"))

    table = Table(title=f"{obj_type} ({len(objects)})", show_header=True, header_style="bold")
    for header, _ in cols:
        table.add_column(header)

    for obj in objects[:50]:
        row = []
        for _, key in cols:
            val = obj.get(key, "")
            if isinstance(val, list):
                val = ", ".join(str(v) for v in val[:3])
            row.append(str(val) if val is not None else "")
        table.add_row(*row)

    if len(objects) > 50:
        table.add_row(f"... {len(objects) - 50} more", *["" for _ in range(len(cols) - 1)])

    console.print(table)


def _print_object_detail(objects: list[dict], store) -> None:
    """Print detailed view of objects with their decisions."""
    for obj in objects[:10]:
        cid = obj.get("canonical_id", "?")
        console.print(f"\n[bold]{cid}[/bold]")
        for k, v in obj.items():
            if k in ("canonical_id", "provenance", "pre_migration_state"):
                continue
            if isinstance(v, dict):
                continue
            if isinstance(v, list) and len(v) > 5:
                console.print(f"  {k}: [{len(v)} items]")
            else:
                console.print(f"  {k}: {v}")

        # Show decisions affecting this object
        all_decisions = store.get_all_decisions()
        obj_decisions = [
            d for d in all_decisions
            if cid in d.get("context", {}).get("_affected_objects", [])
            and d.get("chosen_option") != "__stale__"
        ]
        if obj_decisions:
            console.print(f"\n  [bold]Decisions:[/bold]")
            for d in obj_decisions:
                chosen = d.get("chosen_option") or "pending"
                console.print(
                    f"    {d['decision_id']} {d['type']} ({d['severity']}) → {chosen}"
                )

    if len(objects) > 10:
        console.print(f"\n... {len(objects) - 10} more objects not shown")


# ===================================================================
# EXECUTION COMMANDS (Phase 12b)
# ===================================================================


@app.command("next-batch")
def next_batch(
    output: str = typer.Option("table", "--output", "-o", help="Output: table, json"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
):
    """Show the next batch of migration operations ready to execute.

    Returns operations whose dependencies are all completed/skipped,
    with canonical data and resolved dependency IDs.
    """
    from wxcli.migration.execute.runtime import get_next_batch

    project_dir = _resolve_project_dir(project)
    store = _open_store(project_dir)

    try:
        batch = get_next_batch(store)

        if not batch:
            console.print("No operations ready to execute.")
            console.print("Tip: Run 'wxcli cucm execution-status' to check progress.")
            return

        if output == "json":
            typer.echo(json.dumps(batch, indent=2, default=str))
            return

        # Table output
        tier = batch[0]["tier"]
        batch_name = batch[0]["batch"] or "org-wide"
        console.print(f"\n[bold]Next batch:[/bold] {batch_name} / tier {tier} ({len(batch)} operations)")

        table = Table(show_header=True, header_style="bold")
        table.add_column("Node ID", width=40)
        table.add_column("Type", width=15)
        table.add_column("Op", width=20)
        table.add_column("Description")

        for op in batch:
            table.add_row(
                op["node_id"],
                op["resource_type"],
                op["op_type"],
                op["description"],
            )

        console.print(table)
    finally:
        store.close()


@app.command("mark-complete")
def mark_complete(
    node_id: str = typer.Argument(help="Operation node_id to mark as completed"),
    webex_id: str = typer.Option(None, "--webex-id", help="Webex resource ID created by this operation"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
):
    """Mark a migration operation as completed.

    For create operations, pass --webex-id to record the created resource's ID.
    This ID is available to dependent operations via resolved_deps.
    """
    from wxcli.migration.execute.runtime import update_op_status

    project_dir = _resolve_project_dir(project)
    store = _open_store(project_dir)

    try:
        # Verify the node exists
        row = store.conn.execute(
            "SELECT status FROM plan_operations WHERE node_id = ?",
            (node_id,),
        ).fetchone()
        if not row:
            console.print(f"[red]Operation not found:[/red] {node_id}")
            raise typer.Exit(1)

        update_op_status(store, node_id, "completed", webex_id=webex_id)
        msg = f"[green]Marked completed:[/green] {node_id}"
        if webex_id:
            msg += f" (webex_id: {webex_id})"
        console.print(msg)
    finally:
        store.close()


@app.command("mark-failed")
def mark_failed(
    node_id: str = typer.Argument(help="Operation node_id to mark as failed"),
    error: str = typer.Option(..., "--error", help="Error message"),
    skip: bool = typer.Option(False, "--skip", help="Skip this op and cascade to dependents"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
):
    """Mark a migration operation as failed or skipped.

    With --skip: marks as skipped and cascades to all dependent operations.
    Without --skip: marks as failed, does not cascade (can be retried).
    """
    from wxcli.migration.execute.runtime import update_op_status

    project_dir = _resolve_project_dir(project)
    store = _open_store(project_dir)

    try:
        # Verify the node exists
        row = store.conn.execute(
            "SELECT status FROM plan_operations WHERE node_id = ?",
            (node_id,),
        ).fetchone()
        if not row:
            console.print(f"[red]Operation not found:[/red] {node_id}")
            raise typer.Exit(1)

        if skip:
            update_op_status(store, node_id, "skipped", error_message=error)
            # Count all transitively cascaded ops (direct + indirect)
            skipped_count = store.conn.execute(
                "SELECT COUNT(*) as cnt FROM plan_operations WHERE status = 'skipped' AND error_message LIKE 'Dependency %'",
            ).fetchone()["cnt"]
            console.print(f"[yellow]Skipped:[/yellow] {node_id} ({error})")
            if skipped_count:
                console.print(f"  Cascaded to {skipped_count} dependent operation(s)")
        else:
            update_op_status(store, node_id, "failed", error_message=error)
            console.print(f"[red]Marked failed:[/red] {node_id} ({error})")
    finally:
        store.close()


@app.command("execution-status")
def execution_status(
    output: str = typer.Option("table", "--output", "-o", help="Output: table, json"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
):
    """Show migration execution progress."""
    from wxcli.migration.execute.runtime import get_execution_progress

    project_dir = _resolve_project_dir(project)
    store = _open_store(project_dir)

    try:
        progress = get_execution_progress(store)

        if output == "json":
            typer.echo(json.dumps(progress, indent=2, default=str))
            return

        # Summary table
        console.print(f"\n[bold]Migration Execution Progress[/bold]")
        table = Table(show_header=True, header_style="bold")
        table.add_column("Status", width=15)
        table.add_column("Count", justify="right", width=8)

        for status in ("completed", "in_progress", "pending", "failed", "skipped"):
            count = progress.get(status, 0)
            color = {
                "completed": "green",
                "in_progress": "blue",
                "pending": "white",
                "failed": "red",
                "skipped": "yellow",
            }.get(status, "white")
            table.add_row(f"[{color}]{status}[/{color}]", str(count))
        table.add_row("[bold]Total[/bold]", f"[bold]{progress['total']}[/bold]")
        console.print(table)

        # Per-resource-type breakdown
        by_rt = progress.get("by_resource_type", {})
        if by_rt:
            console.print(f"\n[bold]By Resource Type:[/bold]")
            rt_table = Table(show_header=True, header_style="bold")
            rt_table.add_column("Resource Type", width=20)
            rt_table.add_column("Done", justify="right", width=6)
            rt_table.add_column("Pend", justify="right", width=6)
            rt_table.add_column("Fail", justify="right", width=6)
            rt_table.add_column("Skip", justify="right", width=6)

            for rt in sorted(by_rt.keys()):
                counts = by_rt[rt]
                rt_table.add_row(
                    rt,
                    str(counts.get("completed", 0)),
                    str(counts.get("pending", 0)),
                    str(counts.get("failed", 0)),
                    str(counts.get("skipped", 0)),
                )
            console.print(rt_table)

        # Last error / completion
        if progress.get("last_error"):
            err = progress["last_error"]
            console.print(f"\n[red]Last error:[/red] {err['node_id']}: {err['error']}")
        if progress.get("last_completed"):
            comp = progress["last_completed"]
            console.print(f"[green]Last completed:[/green] {comp['node_id']}: {comp['description']}")
    finally:
        store.close()


@app.command("rollback-ops")
def rollback_ops(
    batch: Optional[str] = typer.Option(None, "--batch", help="Only show ops from this batch"),
    output: str = typer.Option("table", "--output", "-o", help="Output: table, json"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
):
    """Show completed create operations in reverse order for rollback.

    Lists all completed CREATE operations that would need to be deleted
    to roll back the migration, in reverse dependency order (features first,
    locations last).
    """
    from wxcli.migration.execute.runtime import get_completed_ops_for_rollback

    project_dir = _resolve_project_dir(project)
    store = _open_store(project_dir)

    try:
        scope = "batch" if batch else "all"
        ops = get_completed_ops_for_rollback(store, scope=scope, batch_name=batch)

        if not ops:
            console.print("No completed create operations to roll back.")
            return

        if output == "json":
            typer.echo(json.dumps(ops, indent=2, default=str))
            return

        # Table output
        label = f"batch '{batch}'" if batch else "all batches"
        console.print(f"\n[bold]Rollback Operations ({label}):[/bold] {len(ops)} resources to delete\n")

        table = Table(show_header=True, header_style="bold")
        table.add_column("Resource Type", width=20)
        table.add_column("Description", width=40)
        table.add_column("Webex ID", width=30)
        table.add_column("Location ID", width=30)

        for op in ops:
            data = op.get("data", {})
            desc = data.get("name") or (data.get("emails") or [None])[0] or op["canonical_id"]
            table.add_row(
                op["resource_type"],
                str(desc),
                op.get("webex_id") or "-",
                op.get("location_webex_id") or "-",
            )

        console.print(table)
        console.print(
            "\n[yellow]Tip:[/yellow] Delete in the order shown (reverse dependency). "
            "See the cucm-migrate skill's Rollback Dispatch Table for delete commands."
        )
    finally:
        store.close()


@app.command("dry-run")
def dry_run(
    output: str = typer.Option("table", "--output", "-o", help="Output: table, json"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
):
    """Preview the full execution sequence without making changes.

    Walks all batches in execution order, resolving dependencies as if
    each operation completed successfully. No database state is changed.
    """
    from wxcli.migration.execute.runtime import dry_run_all_batches

    project_dir = _resolve_project_dir(project)
    store = _open_store(project_dir)

    try:
        result = dry_run_all_batches(store)

        if output == "json":
            typer.echo(json.dumps(result, indent=2, default=str))
            return

        batches = result["batches"]
        if not batches:
            console.print("No pending operations to execute.")
            return

        console.print("\n[bold]=== Dry Run: Full Execution Sequence ===[/bold]\n")

        op_num = 0
        for batch_info in batches:
            batch_name = batch_info["batch"]
            tier = batch_info["tier"]
            ops = batch_info["operations"]
            console.print(
                f"[bold]Batch: {batch_name} / tier {tier}[/bold] "
                f"({len(ops)} operation{'s' if len(ops) != 1 else ''})"
            )

            for op in ops:
                op_num += 1
                deps_str = ""
                if op["resolved_deps"]:
                    dep_names = list(op["resolved_deps"].keys())
                    deps_str = f" (depends on: {', '.join(dep_names)})"
                console.print(
                    f"  {op_num:>3d}. {op['op_type'].capitalize()} "
                    f"{op['resource_type']} — {op['description']}{deps_str}"
                )
            console.print()

        # Summary
        est_minutes = result["total_api_calls"] / 100  # ~100 req/min rate limit
        console.print(
            f"[bold]Total:[/bold] {result['total_operations']} operations in "
            f"{result['total_batches']} batches, ~{result['total_api_calls']} API calls, "
            f"~{max(1, round(est_minutes))} min at 100 req/min"
        )
        console.print("\n[dim]No changes made to the database.[/dim]")
    finally:
        store.close()


@app.command("execute")
def execute(
    concurrency: int = typer.Option(20, "--concurrency", "-c",
                                     help="Max concurrent API calls (1-50)",
                                     min=1, max=50),
    project: Optional[str] = typer.Option(None, "--project", "-p",
                                           help="Project name"),
):
    """Execute the migration plan — bulk async with rate limiting.

    Processes all pending operations using concurrent API calls.
    Failed operations are recorded and can be retried.
    Run 'wxcli cucm dry-run' first to preview the execution plan.
    """
    import asyncio
    from wxcli.auth import resolve_token
    from wxcli.migration.execute.engine import (
        execute_all_batches,
        reset_in_progress,
    )

    project_dir = _resolve_project_dir(project)
    store = _open_store(project_dir)

    token = resolve_token()
    if not token:
        console.print("[red]Error:[/red] No token. Run 'wxcli configure' first.")
        raise typer.Exit(1)

    try:
        # Reset any in_progress ops from crashed runs
        reset_count = reset_in_progress(store)
        if reset_count:
            console.print(f"[yellow]Reset {reset_count} in-progress ops to pending[/yellow]")

        # Build context
        ctx = {}
        # Load orgId from config if set
        config_path = Path.home() / ".wxcli" / "config.json"
        if config_path.exists():
            import json as json_mod
            try:
                cfg = json_mod.loads(config_path.read_text())
                org_id = cfg.get("profiles", {}).get("default", {}).get("org_id")
                if org_id:
                    ctx["orgId"] = org_id
            except Exception:
                pass

        # Look up calling license ID
        from wxcli.auth import get_api
        api = get_api()
        try:
            resp = api.session.rest_get("https://webexapis.com/v1/licenses")
            licenses = resp.get("items", []) if isinstance(resp, dict) else resp if isinstance(resp, list) else []
            for lic in licenses:
                if "Calling" in lic.get("name", "") and "Professional" in lic.get("name", ""):
                    if lic.get("totalUnits", 0) - lic.get("consumedUnits", 0) > 0:
                        ctx["CALLING_LICENSE_ID"] = lic["id"]
                        break
        except Exception:
            console.print("[yellow]Warning: Could not retrieve calling license ID[/yellow]")

        console.print(f"\n[bold]Starting migration execution[/bold] (concurrency: {concurrency})")
        if ctx.get("CALLING_LICENSE_ID"):
            console.print(f"  Calling license: {ctx['CALLING_LICENSE_ID'][:20]}...")

        def progress_callback(msg):
            console.print(msg)

        summary = asyncio.run(
            execute_all_batches(
                store=store,
                token=token,
                concurrency=concurrency,
                ctx=ctx,
                on_progress=progress_callback,
            )
        )

        # Print summary
        console.print(f"\n[bold]{'=' * 50}[/bold]")
        console.print(f"[bold]Execution Complete[/bold]")
        console.print(f"  [green]Completed:[/green] {summary['completed']}")
        console.print(f"  [red]Failed:[/red]    {summary['failed']}")
        console.print(f"  Batches:   {summary['batches']}")

        if summary["failed"] > 0:
            console.print(
                f"\n[yellow]Tip:[/yellow] Run 'wxcli cucm execution-status' to review failures, "
                f"then 'wxcli cucm execute' again after fixing."
            )
    finally:
        store.close()


@app.command("retry-failed")
def retry_failed(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
):
    """Reset all failed operations to pending so they can be retried.

    Run this after fixing the cause of failures, then run 'wxcli cucm execute' again.
    """
    project_dir = _resolve_project_dir(project)
    store = _open_store(project_dir)

    try:
        cursor = store.conn.execute(
            "UPDATE plan_operations SET status = 'pending', error_message = NULL "
            "WHERE status = 'failed'"
        )
        count = cursor.rowcount
        store.conn.commit()

        if count:
            console.print(f"[green]Reset {count} failed operations to pending.[/green]")
            console.print("Run 'wxcli cucm execute' to retry them.")
        else:
            console.print("No failed operations to retry.")
    finally:
        store.close()


# ===================================================================
# REPORT GENERATION
# ===================================================================


@app.command()
def report(
    brand: str = typer.Option(..., "--brand", help="Customer name for report header"),
    prepared_by: str = typer.Option(..., "--prepared-by", help="SE/partner name"),
    output: str = typer.Option(
        "assessment-report", "--output", "-o",
        help="Output filename (without extension)",
    ),
    pdf: bool = typer.Option(False, "--pdf", help="Also generate PDF via headless Chrome"),
    executive_only: bool = typer.Option(
        False, "--executive-only",
        help="Generate executive summary only, skip technical appendix",
    ),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
):
    """Generate a migration assessment report (HTML + optional PDF)."""
    project_dir = _resolve_project_dir(project)

    # Check that analyze stage is complete (report is not in STAGE_PREREQUISITES)
    completed = _completed_stages(project_dir)
    if "analyze" not in completed:
        console.print(
            "[red]Cannot generate report — 'analyze' stage has not been completed.[/red]\n"
            f"Completed stages: {', '.join(completed) if completed else '(none)'}",
        )
        raise typer.Exit(1)

    store = _open_store(project_dir)
    try:
        # Read cluster_name and cucm_version from project config
        cfg = load_config(project_dir)
        cluster_name = cfg.get("cluster_name", "")
        cucm_version = cfg.get("cucm_version", "")

        from wxcli.migration.report.assembler import assemble_report

        html_content = assemble_report(
            store,
            brand=brand,
            prepared_by=prepared_by,
            cluster_name=cluster_name,
            cucm_version=cucm_version,
            executive_only=executive_only,
        )

        # Write HTML file
        html_path = project_dir / f"{output}.html"
        html_path.write_text(html_content, encoding="utf-8")
        console.print(f"[green]Report generated:[/green] {html_path}")

        # Optional PDF generation via headless Chrome
        if pdf:
            # Check PATH first, then macOS .app bundle locations
            chrome_bin = (
                shutil.which("chromium")
                or shutil.which("google-chrome")
                or shutil.which("chrome")
            )
            if not chrome_bin:
                macos_paths = [
                    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                    "/Applications/Chromium.app/Contents/MacOS/Chromium",
                    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
                ]
                for p in macos_paths:
                    if Path(p).exists():
                        chrome_bin = p
                        break
            if chrome_bin:
                pdf_path = project_dir / f"{output}.pdf"
                try:
                    subprocess.run(
                        [
                            chrome_bin,
                            "--headless",
                            "--disable-gpu",
                            f"--print-to-pdf={pdf_path}",
                            html_path.as_uri(),
                        ],
                        check=True,
                        capture_output=True,
                        timeout=60,
                    )
                    console.print(f"[green]PDF generated:[/green] {pdf_path}")
                except subprocess.CalledProcessError as exc:
                    console.print(
                        f"[yellow]PDF generation failed:[/yellow] {exc.stderr.decode()[:200]}"
                    )
                except subprocess.TimeoutExpired:
                    console.print("[yellow]PDF generation timed out after 60 seconds.[/yellow]")
            else:
                console.print(
                    "[yellow]No Chrome/Chromium found — skipping PDF generation.[/yellow]\n"
                    "Install Chrome or Chromium to enable PDF output."
                )
    finally:
        store.close()
