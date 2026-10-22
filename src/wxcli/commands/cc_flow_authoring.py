"""Hand-written Flow Designer authoring commands for the `cc-flow` group.

Ported from wxcc-flow (`wxcc/src/wxcc_flow/main.py:111-447`, Plan 2 Task 11):

    wxcc-flow schema      -> wxcli cc-flow show-node-template PROJECT_ID ACTIVITY
    wxcc-flow template    -> wxcli cc-flow show-starter-flow [NAME]
    wxcc-flow connectors  -> wxcli cc-flow list-connectors PROJECT_ID

These compose several API reads (or none) into something no single generated
command returns, so the generator cannot produce them. `register(app)` mounts
them onto the generated cc-flow Typer app (`_lazy.GROUP_EXTENSIONS`), the same
pattern as `converged_recordings_export`.

Not ported, by decision: `configure` (-> `wxcli configure`), `set-project`
(P2-2: PROJECT_ID stays positional; read it from `wxcli cc-flow-projects
show-user-preferences`), `events` (-> `wxcli cc-flow list-event-specifications`),
`spec-diff` (-> Task 16), `init` (-> Task 13), and the version callback.

The reads go to the Contact Center host (`get_cc_base_url`) under the bare-UUID
org id (`get_cc_org_id`), the same base the generated `cc-flow list-activities`
and `list-activity-choices` use.
"""
from __future__ import annotations

import json

import httpx
import typer
from rich.table import Table

from wxcli.auth import get_api
from wxcli.config import get_cc_base_url, get_cc_org_id
from wxcli.errors import WebexError, handle_network_error, handle_rest_error
from wxcli.output import console, print_json, print_table

# Import property names that differ from the activity definition names. The
# definition API uses one name, but the import validator requires another.
_IMPORT_FIELD_OVERRIDES = {
    "queue-contact": {
        "destination": ("queueId", "Queue UUID — import validator requires 'queueId', not 'destination'"),
    },
}

_STARTER_FLOWS = {
    "simple-inbound": {
        "name": "New_Flow",
        "flowType": "FLOW",
        "description": "",
        "variables": [],
        "nodes": [
            {
                "id": "node-start",
                "name": "StartFlow",
                "activityType": "start",
                "properties": {
                    "activityName": "start",
                    "flowType": {
                        "eventSourceName": "WebexContactCenter",
                        "eventClassificationName": "VoiceInteractions",
                        "eventSpecificationName": "ContactStartWorkflow",
                    },
                },
            },
            {
                "id": "node-end",
                "name": "DisconnectContact",
                "activityType": "end",
                "properties": {"activityName": "disconnect-contact"},
            },
        ],
        "edges": [
            {
                "id": "edge-1",
                "from": "StartFlow",
                "to": "DisconnectContact",
                "condition": "out",
                "properties": {},
            }
        ],
        "eventFlows": {},
    }
}


def _iter_inputs(act: dict):
    """Yield top-level input dicts from either definition shape.

    Prod returns a flat `inputs` list (with nested `children`); legacy
    deployments returned `inputGroups`.
    """
    if act.get("inputGroups"):
        for ig in act["inputGroups"]:
            if ig.get("name") == "Decryption settings":
                continue
            yield from ig.get("inputs", [])
        return
    yield from act.get("inputs") or []


def _find_activity(activities, name: str) -> dict | None:
    """Find one activity in a `/v2/activities` response.

    Prod returns a flat list keyed by `activityName`; older deployments
    returned a dict keyed by category with a `name` field.
    """
    if isinstance(activities, list):
        for act in activities:
            if isinstance(act, dict) and act.get("activityName") == name:
                return act
    elif isinstance(activities, dict):
        for category, activity_list in activities.items():
            if isinstance(activity_list, list):
                for act in activity_list:
                    if act.get("activityName") == name or act.get("name") == name:
                        act.setdefault("category", category)
                        return act
    return None


def register(app: typer.Typer) -> None:
    """Register show-node-template, show-starter-flow and list-connectors on the cc-flow app."""

    @app.command("show-node-template", short_help="Build a FlowIR node template for an activity.")
    def show_node_template(
        project_id: str = typer.Argument(help="24-char hex id, from: wxcli cc-flow-projects show-user-preferences (projectId)"),
        activity: str = typer.Argument(help="Activity name, e.g. queue-contact, from: wxcli cc-flow list-activities"),
        flow_type: str = typer.Option("FLOW", "--flow-type", help="FLOW or SUBFLOW"),
        output: str = typer.Option("table", "--output", "-o", help="Output format: table|json (json prints the raw activity definition)"),
        debug: bool = typer.Option(False, "--debug"),
    ):
        """Build a FlowIR node template for an activity.

        Uses the real property names from the activity definition's required
        inputs, and applies the known import-name overrides (queue-contact
        `destination` is imported as `queueId`). `-o json` prints the raw
        activity definition instead.

        \b
        Example: wxcli cc-flow show-node-template PROJECT_ID queue-contact
        """
        if output not in ("table", "json"):
            typer.echo(f"Error: --output {output!r} is not supported here; use table or json.", err=True)
            raise typer.Exit(2)
        api = get_api(debug=debug)
        cc_base_url = get_cc_base_url()
        org_id = get_cc_org_id(api.session)
        url = f"{cc_base_url}/{org_id}/project/{project_id}/v2/activities"
        result = None
        try:
            result = api.session.rest_get(url, params={"flowType": flow_type})
        except WebexError as e:
            handle_rest_error(e)
        except httpx.HTTPError as e:
            handle_network_error(e)
        act = _find_activity(result, activity)
        if act is None:
            typer.echo(f"Error: Activity '{activity}' not found in the registry.", err=True)
            raise typer.Exit(1)

        if output == "json":
            print_json(act)
            return

        raw_group = act.get("group", "action")
        group = raw_group.get("name", str(raw_group)) if isinstance(raw_group, dict) else str(raw_group)
        # Prod definitions carry activityType directly; guess from the name
        # only when it's absent (legacy shape).
        activity_type = act.get("activityType")
        if not activity_type:
            end_activities = {"disconnect-contact", "end-subflow", "end"}
            if activity in end_activities:
                activity_type = "end"
            elif activity == "start":
                activity_type = "start"
            else:
                activity_type = "action"

        node_id = f"node-{activity.replace('-', '_')}"
        display_name = act.get("displayName", activity)
        overrides = _IMPORT_FIELD_OVERRIDES.get(activity, {})

        # Build properties from required inputs
        properties = {"activityName": activity}
        conditional_props = {}
        seen_fields = set()
        warnings = []
        for inp in _iter_inputs(act):
            if not inp.get("required"):
                continue
            field_name = inp.get("name", "")
            if field_name in seen_fields:
                continue
            seen_fields.add(field_name)
            if field_name in overrides:
                import_name, note = overrides[field_name]
                warnings.append(f"  ⚠ '{field_name}' → '{import_name}': {note}")
                field_name = import_name
            default = inp.get("defaultValue")
            children = inp.get("children") or []
            if default not in (None, "", [], {}):
                if isinstance(default, str) and default.startswith('"') and default.endswith('"'):
                    default = default[1:-1]
                val = default
            elif children:
                # object[] input: show one example element with its child fields
                val = [{ch.get("name", ""): f"<{ch.get('type', 'string')}>"
                        for ch in children}]
            else:
                val = f"<{inp.get('type', 'string')}>"
            show_cond = inp.get("showOnCondition")
            if show_cond:
                cond_str = f"{show_cond.get('name', '')} == {show_cond.get('value', '')}" if isinstance(show_cond, dict) else str(show_cond)
                conditional_props[field_name] = (val, cond_str)
            else:
                properties[field_name] = val

        # Build output ports (prod flat outputPorts, or legacy errorPathLinks)
        error_ports = []
        for p in act.get("outputPorts") or []:
            error_ports.append({
                "id": p.get("condition", ""),
                "displayName": p.get("label", "")
                or ("error path" if p.get("isErrorPath") else ""),
            })
        for link in (act.get("shapeProperties") or {}).get("errorPathLinks", []):
            error_ports.append({
                "id": link.get("id", ""),
                "displayName": link.get("displayName", ""),
            })

        console.print(f"[bold]FlowIR Node Template for: {activity}[/bold]")
        console.print()
        template = {
            "id": node_id,
            "name": display_name,
            "activityType": activity_type,
            "group": group,
            "properties": properties,
        }
        console.print(json.dumps(template, indent=2), markup=False, highlight=False)

        if conditional_props:
            console.print()
            console.print("[bold]Conditional properties (include when condition is met):[/bold]")
            for fname, (val, cond) in conditional_props.items():
                console.print(f"  {fname}: {json.dumps(val)}  [dim]when {cond}[/dim]")

        if warnings:
            console.print()
            console.print("[bold yellow]Import field overrides:[/bold yellow]")
            for w in warnings:
                console.print(w, markup=False, highlight=False)

        if error_ports:
            console.print()
            table = Table(title="Output Ports", show_header=True, header_style="bold")
            table.add_column("Port ID")
            table.add_column("Display Name")
            for p in error_ports:
                table.add_row(p["id"], p["displayName"])
            console.print(table)

    @app.command("show-starter-flow", short_help="Print a starter FlowIR flow (local, no API call).")
    def show_starter_flow(
        name: str = typer.Argument("simple-inbound", help="Starter flow name: simple-inbound"),
        output: str = typer.Option("json", "--output", "-o", help="Output format: json"),
    ):
        """Print a starter FlowIR flow document (built locally, no API call).

        To write it to a file, redirect stdout: `-o json > FILE`.

        \b
        Example: wxcli cc-flow show-starter-flow simple-inbound -o json > flow.json
        """
        if output != "json":
            typer.echo(f"Error: --output {output!r} is not supported here; use json.", err=True)
            raise typer.Exit(2)
        tpl = _STARTER_FLOWS.get(name)
        if not tpl:
            typer.echo(f"Unknown starter flow '{name}'. Available: {', '.join(_STARTER_FLOWS)}", err=True)
            raise typer.Exit(1)
        print_json(tpl)

    @app.command("list-connectors", short_help="List TTS and HTTP connectors usable in flows.")
    def list_connectors(
        project_id: str = typer.Argument(help="24-char hex id, from: wxcli cc-flow-projects show-user-preferences (projectId)"),
        output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
        debug: bool = typer.Option(False, "--debug"),
    ):
        """List connectors (TTS and HTTP/Custom) usable in flows.

        Merges the choices of play-message's `connector` input (TTS) and the
        `connectorId` input of http-request-v2 and http-request (HTTP/Custom),
        de-duplicated by ID. All three were measured 200 on 2026-10-19
        (docs/merge/flow-store-host-map.md § list-connectors sources);
        http-request-v2's list held connectors http-request's did not. A
        source that fails is named on stderr and skipped; exits 1 with
        "No connectors found." when none returns any.

        \b
        Example: wxcli cc-flow list-connectors PROJECT_ID
        """
        api = get_api(debug=debug)
        cc_base_url = get_cc_base_url()
        org_id = get_cc_org_id(api.session)
        items = []
        seen_ids = set()
        sources = (("play-message", "connector", "TTS"),
                   ("http-request-v2", "connectorId", "HTTP"),
                   ("http-request", "connectorId", "HTTP"))
        for activity_name, input_name, kind in sources:
            url = f"{cc_base_url}/{org_id}/project/{project_id}/v2/activities/{activity_name}/inputs/{input_name}/choices"
            try:
                data = api.session.rest_get(url)
            except WebexError as e:
                # one source failing must not hide the others, but say so
                typer.echo(f"Note: {activity_name} {input_name} choices failed "
                           f"(HTTP {e.status_code}): {e}; its connectors are not listed.", err=True)
                continue
            except httpx.HTTPError as e:
                handle_network_error(e)
            if not isinstance(data, dict):
                continue
            for ch in data.get("choices", []):
                cid = ch.get("value", "")
                if cid and cid not in seen_ids:
                    seen_ids.add(cid)
                    items.append({"id": cid, "name": ch.get("name", ""), "type": kind})

        if not items:
            typer.echo("No connectors found.", err=True)
            raise typer.Exit(1)

        if output == "json":
            print_json(items)
        else:
            print_table(items, [("ID", "id"), ("Name", "name"), ("Type", "type")])
