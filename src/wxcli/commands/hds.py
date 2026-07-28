import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body


app = typer.Typer(help="Manage Webex Calling hds.")


@app.command("show", short_help="Get organization details.")
def show(
    organization_id: str = typer.Argument(help="Webex ORGANIZATION id, from: wxcli organizations list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get organization details.\n\n\b\nExample: wxcli hds show ORGANIZATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/hds/organizations/{organization_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list", short_help="List clusters for an Hybrid Data Security organization.")
def cmd_list(
    organization_id: str = typer.Argument(help="Webex ORGANIZATION id, from: wxcli organizations list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List clusters for an Hybrid Data Security organization.\n\n\b\nExample: wxcli hds list ORGANIZATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/hds/organizations/{organization_id}/clusters"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("clusters", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Cluster ID', 'clusterId'), ('Cluster Name', 'clusterName'), ('Cluster Status', 'clusterStatus'), ('Release Channel', 'releaseChannel')], limit=limit)



@app.command("show-clusters", short_help="Get cluster details.")
def show_clusters(
    cluster_id: str = typer.Argument(help="Webex HYBRID_CLUSTER id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get cluster details.\n\n\b\nExample: wxcli hds show-clusters CLUSTER_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/hds/clusters/{cluster_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list-nodes", short_help="List nodes for an Hybrid Data Security cluster.")
def list_nodes(
    cluster_id: str = typer.Argument(help="Webex HYBRID_CLUSTER id"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """List nodes for an Hybrid Data Security cluster.\n\n\b\nExample: wxcli hds list-nodes CLUSTER_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/hds/clusters/{cluster_id}/nodes"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("nodes", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Node ID', 'nodeId'), ('Host', 'host'), ('Release Version', 'releaseVersion'), ('Proxy Type', 'proxyType'), ('Proxy Status', 'proxyStatus')], limit=limit)



@app.command("show-nodes", short_help="Get node details.")
def show_nodes(
    node_id: str = typer.Argument(help="Webex HYBRID_CONNECTOR id"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get node details.\n\n\b\nExample: wxcli hds show-nodes NODE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/hds/nodes/{node_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("show-database", short_help="Get database details for the Hybrid Data Security organization.")
def show_database(
    organization_id: str = typer.Argument(help="Webex ORGANIZATION id, from: wxcli organizations list"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get database details for the Hybrid Data Security organization.\n\n\b\nExample: wxcli hds show-database ORGANIZATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/hds/organizations/{organization_id}/database"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list-tenants", short_help="Get Multi-Tenant Hybrid Data Security organization details.")
def list_tenants(
    organization_id: str = typer.Argument(help="Webex ORGANIZATION id, from: wxcli organizations list"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Multi-Tenant Hybrid Data Security organization details.\n\n\b\nExample: wxcli hds list-tenants ORGANIZATION_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/hds/organizations/{organization_id}/tenants"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("tenants", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Tenant Org ID', 'tenantOrgId'), ('Tenant Org Name', 'tenantOrgName'), ('Cmk State', 'cmkState'), ('Tenant Org State', 'tenantOrgState')], limit=limit)



@app.command("list-alarms", short_help="Get alarms for an Hybrid Data Security node.")
def list_alarms(
    node_id: str = typer.Argument(help="Webex HYBRID_CONNECTOR id"),
    from_param: str = typer.Option(..., "--from", help="The start date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format."),
    to: str = typer.Option(..., "--to", help="The end date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get alarms for an Hybrid Data Security node.\n\n\b\nExample: wxcli hds list-alarms NODE_ID --from FROM_PARAM --to TO"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/hds/nodes/{node_id}/alarms"
    params = {}
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("alarms", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Alarm ID', 'alarmId'), ('Alarm Name', 'alarmName'), ('Alarm Severity', 'alarmSeverity'), ('Alarm Details', 'alarmDetails'), ('Possible Remediation', 'possibleRemediation')], limit=limit)



@app.command("list-network-test", short_help="Get test results for Hybrid Data Security node.")
def list_network_test(
    node_id: str = typer.Argument(help="Webex HYBRID_CONNECTOR id"),
    trigger_type: str = typer.Option(None, "--trigger-type", help="Choices: OnDemand, Periodic, All"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get test results for Hybrid Data Security node.\n\n\b\nExample: wxcli hds list-network-test NODE_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/hds/testResults/nodes/{node_id}/networkTest"
    params = {}
    if trigger_type is not None:
        params["triggerType"] = trigger_type
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("testResults", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Timestamp', 'timestamp'), ('Trigger Type', 'triggerType')], limit=limit)



@app.command("list-resource-usage", short_help="Get resource usage for an Hybrid Data Security node.")
def list_resource_usage(
    node_id: str = typer.Argument(help="Webex HYBRID_CLUSTER id"),
    from_param: str = typer.Option(..., "--from", help="The start date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format."),
    to: str = typer.Option(..., "--to", help="The end date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get resource usage for an Hybrid Data Security node.\n\n\b\nExample: wxcli hds list-resource-usage NODE_ID --from FROM_PARAM --to TO"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/hds/nodes/{node_id}/resourceUsage"
    params = {}
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("resourceUsage", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Start Time', 'startTime'), ('End Time', 'endTime')], limit=limit)



@app.command("list-availability", short_help="Get availability details for Hybrid Data Security cluster.")
def list_availability(
    cluster_id: str = typer.Argument(help="Webex HYBRID_CLUSTER id"),
    from_param: str = typer.Option(..., "--from", help="The start date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. The 'from' value cannot be later than the 'to' value, and it cannot be more than 1 day older than the current date and time."),
    to: str = typer.Option(..., "--to", help="The end date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get availability details for Hybrid Data Security cluster.\n\n\b\nExample: wxcli hds list-availability CLUSTER_ID --from FROM_PARAM --to TO"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/hds/clusters/{cluster_id}/availability"
    params = {}
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("availabilitySegments", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Segment Start Time', 'segmentStartTime'), ('Segment End Time', 'segmentEndTime'), ('No Of Online Nodes', 'noOfOnlineNodes'), ('No Of Offline Nodes', 'noOfOfflineNodes'), ('Total Nodes', 'totalNodes')], limit=limit)


