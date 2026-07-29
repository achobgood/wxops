import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling resource-group-memberships.")


@app.command("list", short_help="List Resource Group Memberships.")
def cmd_list(
    license_id: str = typer.Option(None, "--license-id", help="List resource group memberships for a license, by ID."),
    person_id: str = typer.Option(None, "--person-id", help="List resource group memberships for a person, by ID."),
    person_org_id: str = typer.Option(None, "--person-org-id", help="List resource group memberships for an organization, by ID."),
    status: str = typer.Option(None, "--status", help="Choices: pending, activated, error"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Resource Group Memberships."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/resourceGroup/memberships"
    params = {}
    if license_id is not None:
        params["licenseId"] = license_id
    if person_id is not None:
        params["personId"] = person_id
    if person_org_id is not None:
        params["personOrgId"] = person_org_id
    if status is not None:
        params["status"] = status
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    try:
        if limit > 0 and not all_pages:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Resource Group ID', 'resourceGroupId'), ('License ID', 'licenseId'), ('Person ID', 'personId'), ('Person Org ID', 'personOrgId')], limit=limit)



@app.command("list-v2", short_help="List Resource Group Memberships V2.")
def list_v2(
    license_id: str = typer.Option(None, "--license-id", help="List resource group memberships for a license, by ID."),
    id_param: str = typer.Option(None, "--id", help="List resource group memberships by ID."),
    status: str = typer.Option(None, "--status", help="Choices: pending, activated, error"),
    type_param: str = typer.Option(None, "--type", help="Choices: User, Workspace"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Resource Group Memberships V2."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/resourceGroup/memberships/v2"
    params = {}
    if license_id is not None:
        params["licenseId"] = license_id
    if id_param is not None:
        params["id"] = id_param
    if status is not None:
        params["status"] = status
    if type_param is not None:
        params["type"] = type_param
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    try:
        if limit > 0 and not all_pages:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(items, output=output, fields=fields, columns=[('ID', 'id'), ('Resource Group ID', 'resourceGroupId'), ('License ID', 'licenseId'), ('Person ID', 'personId'), ('Person Org ID', 'personOrgId')], limit=limit)



@app.command("show", short_help="Get Resource Group Membership Details.")
def show(
    resource_group_membership_id: str = typer.Argument(help="Webex RESOURCE_GROUP_MEMBERSHIP id, from: wxcli resource-group-memberships list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Resource Group Membership Details.\n\n\b\nExample: wxcli resource-group-memberships show RESOURCE_GROUP_MEMBERSHIP_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/resourceGroup/memberships/{resource_group_membership_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UPDATE = '{"resourceGroupId":"...","licenseId":"...","personId":"...","personOrgId":"...","status":"pending"}'

@app.command("update", short_help="Update a Resource Group Membership.")
def update(
    resource_group_membership_id: str = typer.Argument(help="Webex RESOURCE_GROUP_MEMBERSHIP id, from: wxcli resource-group-memberships list"),
    resource_group_id: str = typer.Option(None, "--resource-group-id", help="The resource group ID."),
    license_id: str = typer.Option(None, "--license-id", help="The license ID."),
    person_id: str = typer.Option(None, "--person-id", help="The person ID."),
    person_org_id: str = typer.Option(None, "--person-org-id", help="The organization ID of the person."),
    status: str = typer.Option(None, "--status", help="Choices: pending, activated, error"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Resource Group Membership.\n\n\b\nExample: wxcli resource-group-memberships update RESOURCE_GROUP_MEMBERSHIP_ID --resource-group-id RESOURCE_GROUP_ID --license-id LICENSE_ID --person-id PERSON_ID --person-org-id PERSON_ORG_ID --status pending\n\n\b\nExample --json-body: '{"resourceGroupId":"...","licenseId":"...","personId":"...","personOrgId":"...","status":"pending"}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/resourceGroup/memberships/{resource_group_membership_id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if resource_group_id is not None:
            body["resourceGroupId"] = resource_group_id
        if license_id is not None:
            body["licenseId"] = license_id
        if person_id is not None:
            body["personId"] = person_id
        if person_org_id is not None:
            body["personOrgId"] = person_org_id
        if status is not None:
            body["status"] = status
    try:
        result = api.session.rest_put(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated", "id": resource_group_membership_id}, output=output, fields=fields)


