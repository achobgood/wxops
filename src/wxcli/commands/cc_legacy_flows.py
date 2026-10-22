import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import resolve_org_id, get_cc_base_url, get_cc_org_id
from pathlib import Path


app = typer.Typer(help="Manage Webex Contact Center: cc-legacy-flows.")


@app.command("list", hidden=True)
@app.command("export-ui", short_help="Export a Flow or Subflow.")
def export_ui(
    flow_id: str = typer.Argument(help="24-char hex id"),
    project_id: str = typer.Argument(help="24-char hex id"),
    version: str = typer.Option(None, "--version", help="Version ID. Possible values are 'draft', 'latest' or version ID like '64b92c004ccd9f3d1c680709'. Defaulted to 'latest'."),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW'."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Export a Flow or Subflow.\n\n\b\nExample: wxcli cc-legacy-flows export-ui FLOW_ID PROJECT_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/flow-store/{org_id}/project/{project_id}/flows/{flow_id}:export"
    params = {}
    if version is not None:
        params["version"] = version
    if flow_type is not None:
        params["flowType"] = flow_type
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("import-ui", short_help="Import a Flow or Subflow.")
def import_ui(
    project_id: str = typer.Argument(help="24-char hex id"),
    overwrite: str = typer.Option(None, "--overwrite", help="Determines whether to overwrite the existing flow or not. Possible values: yes/no."),
    flow_type: str = typer.Option(None, "--flow-type", help="Either of 'FLOW' or 'SUBFLOW'."),
    associated_rcs: str = typer.Option(None, "--associated-rcs", help="Sets the `associatedRcs` query param (associated resource collections)"),
    file: Path = typer.Option(..., "--file", exists=True, dir_okay=False, readable=True, help="Path of the file to upload, sent as the multipart 'file' part."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Import a Flow or Subflow.\n\n\b\nExample: wxcli cc-legacy-flows import-ui PROJECT_ID --file FILE"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/flow-store/{org_id}/project/{project_id}/flows:import"
    params = {}
    if overwrite is not None:
        params["overwrite"] = overwrite
    if flow_type is not None:
        params["flowType"] = flow_type
    if associated_rcs is not None:
        params["associatedRcs"] = associated_rcs
    try:
        result = api.session.rest_post_multipart(url, files={"file": (Path(file).name, Path(file).read_bytes(), "application/json")}, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if output == "id":
        if isinstance(result, dict) and "id" in result:
            typer.echo(f"Created: {result['id']}")
        elif not result or result == {}:
            typer.echo("Created.")
        else:
            print_json(result)
    else:
        emit(result, output=output, fields=fields)


