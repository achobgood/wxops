import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import get_org_id


app = typer.Typer(help="Manage Webex Calling video-mesh.")


@app.command("list", short_help="List Clusters Availability.")
def cmd_list(
    from_param: str = typer.Option(..., "--from", help="The starting date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `from` cannot be after `to`."),
    to: str = typer.Option(..., "--to", help="The ending date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Clusters Availability.\n\n\b\nExample: wxcli video-mesh list --from FROM_PARAM --to TO"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/videoMesh/clusters/availability"
    params = {}
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('From', 'from'), ('To', 'to')], limit=limit)



@app.command("show", short_help="Get Cluster Availability.")
def show(
    cluster_id: str = typer.Argument(help="Webex HYBRID_CLUSTER id, from: wxcli video-mesh list"),
    from_param: str = typer.Option(..., "--from", help="The starting date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `from` cannot be after `to`."),
    to: str = typer.Option(..., "--to", help="The ending date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Cluster Availability.\n\n\b\nExample: wxcli video-mesh show CLUSTER_ID --from FROM_PARAM --to TO"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/videoMesh/clusters/availability/{cluster_id}"
    params = {}
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list-availability", short_help="List Node Availability.")
def list_availability(
    from_param: str = typer.Option(..., "--from", help="The starting date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `from` cannot be after `to`."),
    to: str = typer.Option(..., "--to", help="The ending date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format."),
    cluster_id: str = typer.Option(..., "--cluster-id", help="The unique Video Mesh cluster ID."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Node Availability.\n\n\b\nExample: wxcli video-mesh list-availability --from FROM_PARAM --to TO --cluster-id CLUSTER_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/videoMesh/nodes/availability"
    params = {}
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if cluster_id is not None:
        params["clusterId"] = cluster_id
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
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('From', 'from'), ('To', 'to')], limit=limit)



@app.command("show-availability", short_help="Get Node Availability.")
def show_availability(
    node_id: str = typer.Argument(help="Webex HYBRID_CLUSTER id, from: wxcli video-mesh list-availability"),
    from_param: str = typer.Option(..., "--from", help="The starting date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `from` cannot be after `to`."),
    to: str = typer.Option(..., "--to", help="The ending date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Node Availability.\n\n\b\nExample: wxcli video-mesh show-availability NODE_ID --from FROM_PARAM --to TO"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/videoMesh/nodes/availability/{node_id}"
    params = {}
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



@app.command("list-media-health-monitor-test", short_help="List Media Health Monitoring Tool Test results V2.")
def list_media_health_monitor_test(
    trigger_type: str = typer.Option(..., "--trigger-type", help="Choices: OnDemand, Periodic, All"),
    from_param: str = typer.Option(..., "--from", help="The start date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. The `from` parameter cannot have date and time values that exceed `to`."),
    to: str = typer.Option(..., "--to", help="The end date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Media Health Monitoring Tool Test results V2.\n\n\b\nExample: wxcli video-mesh list-media-health-monitor-test --trigger-type OnDemand --from FROM_PARAM --to TO"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/videoMesh/testResults/mediaHealthMonitorTest"
    params = {}
    if trigger_type is not None:
        params["triggerType"] = trigger_type
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-clusters-media-health-monitor-test", short_help="Get Media Health Monitoring Tool Test results for clusters V2.")
def list_clusters_media_health_monitor_test(
    cluster_id: str = typer.Option(..., "--cluster-id", help="Unique ID of the Video Mesh cluster."),
    trigger_type: str = typer.Option(..., "--trigger-type", help="Choices: OnDemand, Periodic, All"),
    from_param: str = typer.Option(..., "--from", help="The start date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. The `from` parameter cannot have date and time values that exceed `to`."),
    to: str = typer.Option(..., "--to", help="The end date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Media Health Monitoring Tool Test results for clusters V2.\n\n\b\nExample: wxcli video-mesh list-clusters-media-health-monitor-test --cluster-id CLUSTER_ID --trigger-type OnDemand --from FROM_PARAM --to TO"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/videoMesh/testResults/mediaHealthMonitorTest/clusters"
    params = {}
    if cluster_id is not None:
        params["clusterId"] = cluster_id
    if trigger_type is not None:
        params["triggerType"] = trigger_type
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
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-nodes-media-health-monitor-test", short_help="Get Media Health Monitoring Tool Test results for node V2.")
def list_nodes_media_health_monitor_test(
    node_id: str = typer.Option(..., "--node-id", help="Unique ID of the Video Mesh node."),
    trigger_type: str = typer.Option(..., "--trigger-type", help="Choices: OnDemand, Periodic, All"),
    from_param: str = typer.Option(..., "--from", help="The start date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. The `from` parameter cannot have date and time values that exceed `to`."),
    to: str = typer.Option(..., "--to", help="The end date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Media Health Monitoring Tool Test results for node V2.\n\n\b\nExample: wxcli video-mesh list-nodes-media-health-monitor-test --node-id NODE_ID --trigger-type OnDemand --from FROM_PARAM --to TO"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/videoMesh/testResults/mediaHealthMonitorTest/nodes"
    params = {}
    if node_id is not None:
        params["nodeId"] = node_id
    if trigger_type is not None:
        params["triggerType"] = trigger_type
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
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-cloud-overflow", short_help="List Overflow to Cloud details.")
def list_cloud_overflow(
    from_param: str = typer.Option(..., "--from", help="The starting date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `from` cannot be after `to`."),
    to: str = typer.Option(..., "--to", help="The ending date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Overflow to Cloud details.\n\n\b\nExample: wxcli video-mesh list-cloud-overflow --from FROM_PARAM --to TO"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/videoMesh/cloudOverflow"
    params = {}
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('From', 'from'), ('To', 'to'), ('Aggregation Interval', 'aggregationInterval')], limit=limit)



@app.command("list-call-redirects-video-mesh", short_help="List Cluster Redirect details.")
def list_call_redirects_video_mesh(
    from_param: str = typer.Option(..., "--from", help="The starting date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `from` cannot be after `to`."),
    to: str = typer.Option(..., "--to", help="The ending date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Cluster Redirect details.\n\n\b\nExample: wxcli video-mesh list-call-redirects-video-mesh --from FROM_PARAM --to TO"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/videoMesh/callRedirects"
    params = {}
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('From', 'from'), ('To', 'to'), ('Aggregation Interval', 'aggregationInterval')], limit=limit)



@app.command("list-call-redirects-clusters", short_help="Get Cluster Redirect details.")
def list_call_redirects_clusters(
    from_param: str = typer.Option(..., "--from", help="The starting date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `from` cannot be after `to`."),
    to: str = typer.Option(..., "--to", help="The ending date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format."),
    cluster_id: str = typer.Option(..., "--cluster-id", help="The unique Video Mesh Cluster ID."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Cluster Redirect details.\n\n\b\nExample: wxcli video-mesh list-call-redirects-clusters --from FROM_PARAM --to TO --cluster-id CLUSTER_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/videoMesh/clusters/callRedirects"
    params = {}
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if cluster_id is not None:
        params["clusterId"] = cluster_id
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
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('From', 'from'), ('To', 'to'), ('Aggregation Interval', 'aggregationInterval')], limit=limit)



@app.command("list-utilization-video-mesh", short_help="List Clusters Utilization.")
def list_utilization_video_mesh(
    from_param: str = typer.Option(..., "--from", help="The starting date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `from` cannot be after `to`."),
    to: str = typer.Option(..., "--to", help="The ending date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Clusters Utilization.\n\n\b\nExample: wxcli video-mesh list-utilization-video-mesh --from FROM_PARAM --to TO"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/videoMesh/utilization"
    params = {}
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Aggregation Interval', 'aggregationInterval'), ('From', 'from'), ('To', 'to')], limit=limit)



@app.command("list-utilization-clusters", short_help="Get Cluster Utilization details.")
def list_utilization_clusters(
    from_param: str = typer.Option(..., "--from", help="The starting date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. `from` cannot be after `to`."),
    to: str = typer.Option(..., "--to", help="The ending date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format."),
    cluster_id: str = typer.Option(..., "--cluster-id", help="The unique Video Mesh Cluster ID."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Cluster Utilization details.\n\n\b\nExample: wxcli video-mesh list-utilization-clusters --from FROM_PARAM --to TO --cluster-id CLUSTER_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/videoMesh/clusters/utilization"
    params = {}
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if cluster_id is not None:
        params["clusterId"] = cluster_id
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
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Aggregation Interval', 'aggregationInterval'), ('From', 'from'), ('To', 'to')], limit=limit)



@app.command("list-reachability-test", short_help="List Reachability Test results V2.")
def list_reachability_test(
    trigger_type: str = typer.Option(..., "--trigger-type", help="Choices: OnDemand, Periodic, All"),
    from_param: str = typer.Option(..., "--from", help="The start date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. The `from` parameter cannot have date and time values that exceed `to`."),
    to: str = typer.Option(..., "--to", help="The end date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Reachability Test results V2.\n\n\b\nExample: wxcli video-mesh list-reachability-test --trigger-type OnDemand --from FROM_PARAM --to TO"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/videoMesh/testResults/reachabilityTest"
    params = {}
    if trigger_type is not None:
        params["triggerType"] = trigger_type
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-clusters-reachability-test", short_help="Get Reachability Test results for cluster V2.")
def list_clusters_reachability_test(
    cluster_id: str = typer.Option(..., "--cluster-id", help="Unique ID of the Video Mesh cluster."),
    trigger_type: str = typer.Option(..., "--trigger-type", help="Choices: OnDemand, Periodic, All"),
    from_param: str = typer.Option(..., "--from", help="The start date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. The `from` parameter cannot have date and time values that exceed `to`."),
    to: str = typer.Option(..., "--to", help="The end date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Reachability Test results for cluster V2.\n\n\b\nExample: wxcli video-mesh list-clusters-reachability-test --cluster-id CLUSTER_ID --trigger-type OnDemand --from FROM_PARAM --to TO"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/videoMesh/testResults/reachabilityTest/clusters"
    params = {}
    if cluster_id is not None:
        params["clusterId"] = cluster_id
    if trigger_type is not None:
        params["triggerType"] = trigger_type
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
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-nodes-reachability-test", short_help="Get Reachability Test results for node V2.")
def list_nodes_reachability_test(
    node_id: str = typer.Option(..., "--node-id", help="Unique ID of the Video Mesh node."),
    trigger_type: str = typer.Option(..., "--trigger-type", help="Choices: OnDemand, Periodic, All"),
    from_param: str = typer.Option(..., "--from", help="The start date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. The `from` parameter cannot have date and time values that exceed `to`."),
    to: str = typer.Option(..., "--to", help="The end date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Reachability Test results for node V2.\n\n\b\nExample: wxcli video-mesh list-nodes-reachability-test --node-id NODE_ID --trigger-type OnDemand --from FROM_PARAM --to TO"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/videoMesh/testResults/reachabilityTest/nodes"
    params = {}
    if node_id is not None:
        params["nodeId"] = node_id
    if trigger_type is not None:
        params["triggerType"] = trigger_type
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
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-clusters-video-mesh", short_help="List Cluster Details.")
def list_clusters_video_mesh(
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Cluster Details."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/videoMesh/clusters"
    params = {}
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Org ID', 'orgId')], limit=limit)



@app.command("show-clusters", short_help="Get Cluster Details.")
def show_clusters(
    cluster_id: str = typer.Argument(help="Webex HYBRID_CLUSTER id, from: wxcli video-mesh list-clusters-video-mesh"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Cluster Details.\n\n\b\nExample: wxcli video-mesh show-clusters CLUSTER_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/videoMesh/clusters/{cluster_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_CREATE = '{"type":"ReachabilityTest","nodes":["..."]}'

@app.command("create", short_help="Trigger on-demand test for cluster.")
def create(
    cluster_id: str = typer.Argument(help="Webex HYBRID_CLUSTER id, from: wxcli video-mesh list-clusters-video-mesh"),
    type_param: str = typer.Option(None, "--type", help="Choices: ReachabilityTest, NetworkTest, MediaHealthMonitorTest"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Trigger on-demand test for cluster.\n\n\b\nExample: wxcli video-mesh create CLUSTER_ID\n\n\b\nExample --json-body: '{"type":"ReachabilityTest","nodes":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/videoMesh/triggerTest/clusters/{cluster_id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if type_param is not None:
            body["type"] = type_param
    try:
        result = api.session.rest_post(url, json=body)
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



_BODY_SKELETON_CREATE_NODES = '{"type":"ReachabilityTest"}'

@app.command("create-nodes", short_help="Trigger on-demand test for node.")
def create_nodes(
    node_id: str = typer.Argument(help="Webex HYBRID_CONNECTOR id"),
    type_param: str = typer.Option(None, "--type", help="Choices: ReachabilityTest, NetworkTest, MediaHealthMonitorTest"),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Trigger on-demand test for node.\n\n\b\nExample: wxcli video-mesh create-nodes NODE_ID\n\n\b\nExample --json-body: '{"type":"ReachabilityTest"}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_NODES), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/videoMesh/triggerTest/nodes/{node_id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if type_param is not None:
            body["type"] = type_param
    try:
        result = api.session.rest_post(url, json=body)
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



@app.command("list-test-status", short_help="Get Triggered test status.")
def list_test_status(
    command_id: str = typer.Option(..., "--command-id", help="The unique command ID generated from Trigger on-demand test API."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Triggered test status.\n\n\b\nExample: wxcli video-mesh list-test-status --command-id COMMAND_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/videoMesh/testStatus"
    params = {}
    if command_id is not None:
        params["commandId"] = command_id
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
    emit(items, output=output, fields=fields, columns=[('Node ID', 'nodeId'), ('Status', 'status')], limit=limit)



@app.command("list-test-results", short_help="Get Triggered test results.")
def list_test_results(
    command_id: str = typer.Option(..., "--command-id", help="The unique command ID generated from Trigger on-demand test API."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Triggered test results.\n\n\b\nExample: wxcli video-mesh list-test-results --command-id COMMAND_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/videoMesh/testResults"
    params = {}
    if command_id is not None:
        params["commandId"] = command_id
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
    items = result.get("results", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-network-test", short_help="List Network Test results.")
def list_network_test(
    trigger_type: str = typer.Option(..., "--trigger-type", help="Choices: OnDemand, Periodic, All"),
    from_param: str = typer.Option(..., "--from", help="The start date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. The `from` parameter cannot have date and time values that exceed `to`."),
    to: str = typer.Option(..., "--to", help="The end date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Network Test results.\n\n\b\nExample: wxcli video-mesh list-network-test --trigger-type OnDemand --from FROM_PARAM --to TO"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/videoMesh/testResults/networkTest"
    params = {}
    if trigger_type is not None:
        params["triggerType"] = trigger_type
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-clusters-network-test", short_help="Get Network Test results for cluster.")
def list_clusters_network_test(
    cluster_id: str = typer.Option(..., "--cluster-id", help="Unique ID of the Video Mesh cluster."),
    trigger_type: str = typer.Option(..., "--trigger-type", help="Choices: OnDemand, Periodic, All"),
    from_param: str = typer.Option(..., "--from", help="The start date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. The `from` parameter cannot have date and time values that exceed `to`."),
    to: str = typer.Option(..., "--to", help="The end date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Network Test results for cluster.\n\n\b\nExample: wxcli video-mesh list-clusters-network-test --cluster-id CLUSTER_ID --trigger-type OnDemand --from FROM_PARAM --to TO"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/videoMesh/testResults/networkTest/clusters"
    params = {}
    if cluster_id is not None:
        params["clusterId"] = cluster_id
    if trigger_type is not None:
        params["triggerType"] = trigger_type
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
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-nodes-network-test", short_help="Get Network Test results for node.")
def list_nodes_network_test(
    node_id: str = typer.Option(..., "--node-id", help="Unique ID of the Video Mesh node."),
    trigger_type: str = typer.Option(..., "--trigger-type", help="Choices: OnDemand, Periodic, All"),
    from_param: str = typer.Option(..., "--from", help="The start date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. The `from` parameter cannot have date and time values that exceed `to`."),
    to: str = typer.Option(..., "--to", help="The end date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Network Test results for node.\n\n\b\nExample: wxcli video-mesh list-nodes-network-test --node-id NODE_ID --trigger-type OnDemand --from FROM_PARAM --to TO"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/videoMesh/testResults/networkTest/nodes"
    params = {}
    if node_id is not None:
        params["nodeId"] = node_id
    if trigger_type is not None:
        params["triggerType"] = trigger_type
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
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[("ID", "id"), ("Name", "name")], limit=limit)



@app.command("list-client-type-distribution", short_help="List Cluster Client Type Distribution details.")
def list_client_type_distribution(
    from_param: str = typer.Option(..., "--from", help="The start date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. The `from` parameter cannot have date and time values that exceed `to`."),
    to: str = typer.Option(..., "--to", help="The end date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format."),
    device_type: str = typer.Option(..., "--device-type", help="Device type(s). - Possible values: `webexDevices` `webexAppVdi` `webexForMobile` `sipEndpoint` `webexForDesktop`"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Cluster Client Type Distribution details.\n\n\b\nExample: wxcli video-mesh list-client-type-distribution --from FROM_PARAM --to TO --device-type DEVICE_TYPE"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/videoMesh/clientTypeDistribution"
    params = {}
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if device_type is not None:
        params["deviceType"] = device_type
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('From', 'from'), ('To', 'to'), ('Aggregation Interval', 'aggregationInterval')], limit=limit)



@app.command("list-clusters-client-type-distribution", short_help="Get Cluster Client Type Distribution details.")
def list_clusters_client_type_distribution(
    cluster_id: str = typer.Option(..., "--cluster-id", help="Unique ID of the Video Mesh cluster."),
    from_param: str = typer.Option(..., "--from", help="The start date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format. The `from` parameter cannot have date and time values that exceed `to`."),
    to: str = typer.Option(..., "--to", help="The end date and time of the requested data in any [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) compliant format."),
    device_type: str = typer.Option(..., "--device-type", help="Device type(s). - Possible values: `webexDevices` `webexAppVdi` `webexForMobile` `sipEndpoint` `webexForDesktop`"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Cluster Client Type Distribution details.\n\n\b\nExample: wxcli video-mesh list-clusters-client-type-distribution --cluster-id CLUSTER_ID --from FROM_PARAM --to TO --device-type DEVICE_TYPE"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/videoMesh/clientTypeDistribution/clusters"
    params = {}
    if cluster_id is not None:
        params["clusterId"] = cluster_id
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    if device_type is not None:
        params["deviceType"] = device_type
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
    items = result.get("items", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('From', 'from'), ('To', 'to'), ('Aggregation Interval', 'aggregationInterval')], limit=limit)



@app.command("list-event-thresholds", short_help="List Event Threshold Configuration.")
def list_event_thresholds(
    event_name: str = typer.Option(None, "--event-name", help="Choices: clusterCallsRedirected, orgCallsOverflowed"),
    cluster_id: str = typer.Option(None, "--cluster-id", help="Unique ID of the Video Mesh Cluster."),
    event_scope: str = typer.Option(None, "--event-scope", help="Choices: CLUSTER, ORG"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    all_pages: bool = typer.Option(False, "--all", help="Fetch every page, not just the first. Overrides --limit."),
    debug: bool = typer.Option(False, "--debug"),
):
    """List Event Threshold Configuration."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/videoMesh/eventThresholds"
    params = {}
    if event_name is not None:
        params["eventName"] = event_name
    if cluster_id is not None:
        params["clusterId"] = cluster_id
    if event_scope is not None:
        params["eventScope"] = event_scope
    if limit > 0:
        params["max"] = limit
    if offset > 0:
        params["start"] = offset
    org_id = get_org_id()
    if org_id is not None:
        params["orgId"] = org_id
    result = None
    try:
        result = api.session.rest_get(url, params=params)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    result = result or []
    items = result.get("eventThresholds", result.get("data", result if isinstance(result, list) else [])) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    emit(items, output=output, fields=fields, columns=[('Event Threshold ID', 'eventThresholdId'), ('Event Name', 'eventName'), ('Event Scope', 'eventScope'), ('Entity ID', 'entityId')], limit=limit)



_BODY_SKELETON_UPDATE = '{"eventThresholds":[{"eventThresholdId":"...","thresholdConfig":{"minThreshold":0}}]}'

@app.command("update", short_help="Update Event Threshold Configuration.")
def update(
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Event Threshold Configuration.\n\n\b\nExample: wxcli video-mesh update --json-body '{"eventThresholds":[{"eventThresholdId":"...","thresholdConfig":{"minThreshold":0}}]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/videoMesh/eventThresholds"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_patch(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Updated.")
    else:
        emit({"status": "updated"}, output=output, fields=fields)



@app.command("show-event-thresholds", short_help="Get Event Threshold Configuration.")
def show_event_thresholds(
    event_threshold_id: str = typer.Argument(help="Webex EVENT id, from: wxcli video-mesh list-event-thresholds"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Event Threshold Configuration.\n\n\b\nExample: wxcli video-mesh show-event-thresholds EVENT_THRESHOLD_ID"""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/videoMesh/eventThresholds/{event_threshold_id}"
    try:
        result = api.session.rest_get(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_CREATE_RESET = '{"eventThresholdIds":["..."]}'

@app.command("create-reset", short_help="Reset Event Threshold Configuration.")
def create_reset(
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Reset Event Threshold Configuration.\n\n\b\nExample: wxcli video-mesh create-reset --json-body '{"eventThresholdIds":["..."]}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE_RESET), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/videoMesh/eventThresholds/reset"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
    try:
        result = api.session.rest_post(url, json=body)
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


