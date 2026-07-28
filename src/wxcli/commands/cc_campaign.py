import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import resolve_org_id, get_cc_base_url, get_cc_org_id


app = typer.Typer(help="Manage Webex Contact Center cc-campaign.")


_BODY_SKELETON_CREATE = '{"id":"...","vendorVersion":"...","campaignType":"...","dialingRate":0,"entryPointId":"...","dialingListFetchURL":"...","outdialANI":"...","recordCount":0}'

@app.command("create", short_help="Start Campaign Request.")
def create(
    id_param: str = typer.Option(None, "--id", help="(required) The id represents the unique id with which the Campaign Request will be started, maximum length 64 characters."),
    vendor_version: str = typer.Option(None, "--vendor-version", help="(required) Vendor specific information, maximum length 32 characters."),
    campaign_type: str = typer.Option(None, "--campaign-type", help="(required) Type of campaign and campaignType should be one of \"progressive\", \"campaign\", \"predictive\", \"progressive_ivr\", \"predictive_ivr\" , \"preview_standard\", \"preview_direct\""),
    campaign_name: str = typer.Option(None, "--campaign-name", help="(Optional) Used if different than id, maximum length 64 characters."),
    auth_token: str = typer.Option(None, "--auth-token", help="(Not in use) The token needed by the dialer for querying records."),
    dialing_rate: str = typer.Option(None, "--dialing-rate", help="(required) Number of contacts to be dialed out per available Agent. For Progressive 1:1 Dialer, it will support for only 1 contact and for Progressive 1:N Dialer it can support upto 10 contacts to be dialed out per available Agent"),
    entry_point_id: str = typer.Option(None, "--entry-point-id", help="(required) Webex Contact Center outdial entry point, maximum length 36 characters."),
    dialing_list_fetch_url: str = typer.Option(None, "--dialing-list-fetch-url", help="(required) URL the dialer will use to fetch the list of contacts to dial for the campaign from campaign manager, maximum length 1024 characters."),
    outdial_ani: str = typer.Option(None, "--outdial-ani", help="(required) The ANI (E164) that will be presented to the customer. These must be restricted to the configured outdial Eps in Webex Contact Center, maximum length 50 characters."),
    record_count: str = typer.Option(None, "--record-count", help="(required) Value to indicate the recordCount the Campaign Manager expects the dialer to be able to request, the maximum is 400. If the value is greater than 400 it will be set to the maximum when the request is processed."),
    no_answer_ring_limit: str = typer.Option(None, "--no-answer-ring-limit", help="(Optional) Number of seconds before a dialed call from the dialer is considered not answered, The range is from 16 to 80, default is 32. This field is not applicable for Direct preview campaigns."),
    max_dialing_rate: str = typer.Option(None, "--max-dialing-rate", help="Caps the maximum dialing rate per agent at this value. The range is from 1.0 to 10.0 , default is 1.0."),
    abandon_rate_percentage: str = typer.Option(None, "--abandon-rate-percentage", help="The percentage of calls that are allowed to be abandoned. The range is from 1.0 to 100.0 with a granularity of 0.1. The Default is 3.0"),
    predictive_correction_pace: str = typer.Option(None, "--predictive-correction-pace", help="A count of the number of live voice connections that must occur before the dialer adjusts. Increasing this number results in less frequent adjustments based on a larger sample size. The range is from 10 to 5000 , default is 70."),
    predictive_gain: str = typer.Option(None, "--predictive-gain", help="The size of the adjustment to lines per agent each time an adjustment is made. Increasing this number results in larger per-agent adjustments. The range is 0.1 to 3.0 , default is 1.0."),
    reservation_percentage: str = typer.Option(None, "--reservation-percentage", help="(Not in use) The percentage of agents to reserve within the queue associated with the campaign. The range is from 0 to 100 , default is 100"),
    ivr_ports: str = typer.Option(None, "--ivr-ports", help="The number of IVR ports to use for this campaign. IVR ports are in use when calling a customer until the call is either ended or transferred to an agent. One IVR port can be considered equivalent to an agent in an agent based campaign.The range is from 1 to 1000."),
    preview_offer_timeout: str = typer.Option(None, "--preview-offer-timeout", help="(Required if previewOfferTimeoutAutoAction is provided, optional otherwise) The number of seconds dialer waits for an agent to act on a preview campaign record, before performing the provided previewOfferTimeoutAutoAction. The range is from 0 to 7200(2 hours) for ACCEPT auto-action and 10 to 7200(2..."),
    preview_offer_timeout_auto_action: str = typer.Option(None, "--preview-offer-timeout-auto-action", help="(Required if previewOfferTimeout is provided, optional otherwise) The automatic action to be performed after the previewOfferTimeout duration has elapsed, if agent takes no action on the preview campaign record offered. Should be one of \"ACCEPT\", \"SKIP\", \"REMOVE\". The default is \"SKIP\"."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Start Campaign Request.\n\n\b\nExample: wxcli cc-campaign create --id ID_PARAM --vendor-version VENDOR_VERSION --campaign-type CAMPAIGN_TYPE --dialing-rate DIALING_RATE --entry-point-id ENTRY_POINT_ID --dialing-list-fetch-url DIALING_LIST_FETCH_URL --outdial-ani OUTDIAL_ANI --record-count RECORD_COUNT\n\n\b\nExample --json-body: '{"id":"...","vendorVersion":"...","campaignType":"...","dialingRate":0,"entryPointId":"...","dialingListFetchURL":"...","outdialANI":"...","recordCount":0}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CREATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/dialer/campaign"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if id_param is not None:
            body["id"] = id_param
        if vendor_version is not None:
            body["vendorVersion"] = vendor_version
        if campaign_type is not None:
            body["campaignType"] = campaign_type
        if campaign_name is not None:
            body["campaignName"] = campaign_name
        if auth_token is not None:
            body["authToken"] = auth_token
        if dialing_rate is not None:
            body["dialingRate"] = dialing_rate
        if entry_point_id is not None:
            body["entryPointId"] = entry_point_id
        if dialing_list_fetch_url is not None:
            body["dialingListFetchURL"] = dialing_list_fetch_url
        if outdial_ani is not None:
            body["outdialANI"] = outdial_ani
        if record_count is not None:
            body["recordCount"] = record_count
        if no_answer_ring_limit is not None:
            body["noAnswerRingLimit"] = no_answer_ring_limit
        if max_dialing_rate is not None:
            body["maxDialingRate"] = max_dialing_rate
        if abandon_rate_percentage is not None:
            body["abandonRatePercentage"] = abandon_rate_percentage
        if predictive_correction_pace is not None:
            body["predictiveCorrectionPace"] = predictive_correction_pace
        if predictive_gain is not None:
            body["predictiveGain"] = predictive_gain
        if reservation_percentage is not None:
            body["reservationPercentage"] = reservation_percentage
        if ivr_ports is not None:
            body["ivrPorts"] = ivr_ports
        if preview_offer_timeout is not None:
            body["previewOfferTimeout"] = preview_offer_timeout
        if preview_offer_timeout_auto_action is not None:
            body["previewOfferTimeoutAutoAction"] = preview_offer_timeout_auto_action
        _missing = [f for f in ['id', 'vendorVersion', 'campaignType', 'dialingRate', 'entryPointId', 'dialingListFetchURL', 'outdialANI', 'recordCount'] if f not in body or body[f] is None]
        if _missing:
            typer.echo("Error: Missing required fields: " + ", ".join(_missing), err=True)
            raise typer.Exit(1)
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



@app.command("list", short_help="Get Valid Campaign Times.")
def cmd_list(
    campaign_id: str = typer.Option(..., "--campaign-id", help="The campaign ID for which valid campaign times are being requested."),
    agent_id: str = typer.Option(..., "--agent-id", help="The agent ID for whom valid campaign times are being requested."),
    tracking_id: str = typer.Option(None, "--tracking-id", help="Optional tracking identifier for request tracing."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    limit: int = typer.Option(0, "--limit", help="Max results (0=all for paginated endpoints, API default for non-paginated)"),
    offset: int = typer.Option(0, "--offset", help="Start offset"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Valid Campaign Times.\n\n\b\nExample: wxcli cc-campaign list --campaign-id CAMPAIGN_ID --agent-id AGENT_ID"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    org_id = get_cc_org_id(api.session)
    url = f"{cc_base_url}/organization/{org_id}/getValidCampaignTimes"
    params = {}
    if campaign_id is not None:
        params["campaignId"] = campaign_id
    if agent_id is not None:
        params["agentId"] = agent_id
    if tracking_id is not None:
        params["trackingId"] = tracking_id
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



_BODY_SKELETON_UPDATE = '{"dialingRate":0,"dialingListFetchURL":"...","outdialANI":"...","campaignName":"...","authToken":"...","noAnswerRingLimit":0,"maxDialingRate":0,"reservationPercentage":0}'

@app.command("update", short_help="Update Campaign Request.")
def update(
    campaign_id: str = typer.Argument(help="e.g. Campaign1"),
    dialing_rate: str = typer.Option(None, "--dialing-rate", help="Number of contacts to be dialed out per available Agent. For Progressive 1:1 Dialer, it will support for only 1 contact and for Progressive 1:N Dialer it can support upto 10 contacts to be dialed out per available Agent"),
    campaign_name: str = typer.Option(None, "--campaign-name", help="(Optional) Used if different than id, maximum length 64 characters."),
    auth_token: str = typer.Option(None, "--auth-token", help="(Not in use) The token needed by the dialer for querying records."),
    dialing_list_fetch_url: str = typer.Option(None, "--dialing-list-fetch-url", help="URL the dialer will use to fetch the list of contacts to dial for the campaign from campaign manager, maximum length 1024 characters."),
    outdial_ani: str = typer.Option(None, "--outdial-ani", help="The ANI (E164) that will be presented to the customer. These must be restricted to the configured outdial Eps in Webex Contact Center, maximum length 50 characters."),
    no_answer_ring_limit: str = typer.Option(None, "--no-answer-ring-limit", help="(Optional) Number of seconds before a dialed call from the dialer is considered not answered. The range is from 16 to 80, default is 32. This field is not applicable for Direct preview campaigns."),
    max_dialing_rate: str = typer.Option(None, "--max-dialing-rate", help="Caps the maximum dialing rate per agent at this value. The range is from 1.0 to 10.0, default is 1.0."),
    reservation_percentage: str = typer.Option(None, "--reservation-percentage", help="(Not in use) The percentage of agents to reserve within the queue associated with the campaign. The range is from 0 to 100 , default is 100."),
    preview_offer_timeout: str = typer.Option(None, "--preview-offer-timeout", help="(Required only if previewOfferTimeoutAutoAction is provided) The number of seconds dialer waits for an agent to act on a preview campaign record, before performing the provided previewOfferTimeoutAutoAction. The range is from 0 to 7200 seconds(2 hours) for ACCEPT auto-action, and from 10 to 7200..."),
    preview_offer_timeout_auto_action: str = typer.Option(None, "--preview-offer-timeout-auto-action", help="(Required only if previewOfferTimeout is provided) The automatic action to be performed after the previewOfferTimeout duration has elapsed, if agent takes no action on the preview campaign record offered. The action can be \"ACCEPT\", \"SKIP\" or \"REMOVE\". The default action is \"SKIP\"."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Campaign Request.\n\n\b\nExample: wxcli cc-campaign update Campaign1 --dialing-rate DIALING_RATE --dialing-list-fetch-url DIALING_LIST_FETCH_URL --outdial-ani OUTDIAL_ANI\n\n\b\nExample --json-body: '{"dialingRate":0,"dialingListFetchURL":"...","outdialANI":"...","campaignName":"...","authToken":"...","noAnswerRingLimit":0,"maxDialingRate":0,"reservationPercentage":0}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UPDATE), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/dialer/campaign/{campaign_id}"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if dialing_rate is not None:
            body["dialingRate"] = dialing_rate
        if campaign_name is not None:
            body["campaignName"] = campaign_name
        if auth_token is not None:
            body["authToken"] = auth_token
        if dialing_list_fetch_url is not None:
            body["dialingListFetchURL"] = dialing_list_fetch_url
        if outdial_ani is not None:
            body["outdialANI"] = outdial_ani
        if no_answer_ring_limit is not None:
            body["noAnswerRingLimit"] = no_answer_ring_limit
        if max_dialing_rate is not None:
            body["maxDialingRate"] = max_dialing_rate
        if reservation_percentage is not None:
            body["reservationPercentage"] = reservation_percentage
        if preview_offer_timeout is not None:
            body["previewOfferTimeout"] = preview_offer_timeout
        if preview_offer_timeout_auto_action is not None:
            body["previewOfferTimeoutAutoAction"] = preview_offer_timeout_auto_action
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
        emit({"status": "updated", "id": campaign_id}, output=output, fields=fields)



@app.command("delete", short_help="Stop Campaign Request.")
def delete(
    campaign_id: str = typer.Argument(help="e.g. Campaign1"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Stop Campaign Request.\n\n\b\nExample: wxcli cc-campaign delete Campaign1"""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    if not force:
        typer.confirm(f"Delete {campaign_id}?", abort=True)
    url = f"{cc_base_url}/dialer/campaign/{campaign_id}"
    try:
        result = api.session.rest_delete(url)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    if result:
        emit(result, output=output, fields=fields)
    elif output in ("table", "id") and not fields:
        typer.echo(f"Deleted: {campaign_id}")
    else:
        emit({"status": "deleted", "id": campaign_id}, output=output, fields=fields)


