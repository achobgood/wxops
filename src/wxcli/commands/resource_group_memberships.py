import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling resource-group-memberships.")


@app.command("list")
def cmd_list(
    license_id: str = typer.Option(None, "--license-id", help="List resource group memberships for a license, by ID."),
    person_id: str = typer.Option(None, "--person-id", help="List resource group memberships for a person, by ID."),
    person_org_id: str = typer.Option(None, "--person-org-id", help="List resource group memberships for an organization, by ID."),
    status: str = typer.Option(None, "--status", help="Choices: pending, activated, error"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
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
        if limit > 0:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except WebexError as e:
            handle_rest_error(e)
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-v2")
def list_v2(
    license_id: str = typer.Option(None, "--license-id", help="List resource group memberships for a license, by ID."),
    id_param: str = typer.Option(None, "--id", help="List resource group memberships by ID."),
    status: str = typer.Option(None, "--status", help="Choices: pending, activated, error"),
    type_param: str = typer.Option(None, "--type", help="Choices: User, Workspace"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json"),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
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
        if limit > 0:
            result = api.session.rest_get(url, params=params)
            result = result or {}
            items = result.get("items", result if isinstance(result, list) else []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
        else:
            items = list(api.session.follow_pagination(url=url, params=params, item_key="items"))
    except WebexError as e:
            handle_rest_error(e)
    if output == "json":
        print_json(items)
    else:
        print_table(items, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("show")
def show(
    resource_group_membership_id: str = typer.Argument(help="resourceGroupMembershipId"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Resource Group Membership Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/resourceGroup/memberships/{resource_group_membership_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
            handle_rest_error(e)
    if output == "json":
        print_json(result)
    else:
        if isinstance(result, dict):
            print_table([result], columns=[("Key", ""), ("Value", "")], limit=0)
        elif isinstance(result, list):
            print_table(result, columns=[("ID", "id"), ("Name", "name")], limit=0)
        else:
            print_json(result)



@app.command("update")
def update(
    resource_group_membership_id: str = typer.Argument(help="resourceGroupMembershipId"),
    resource_group_id: str = typer.Option(None, "--resource-group-id", help="The resource group ID."),
    license_id: str = typer.Option(None, "--license-id", help="The license ID."),
    person_id: str = typer.Option(None, "--person-id", help="The person ID."),
    person_org_id: str = typer.Option(None, "--person-org-id", help="The organization ID of the person."),
    status: str = typer.Option(None, "--status", help="Choices: pending, activated, error"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update a Resource Group Membership."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/resourceGroup/memberships/{resource_group_membership_id}"
    if json_body:
        body = json.loads(json_body)
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
    typer.echo(f"Updated.")


