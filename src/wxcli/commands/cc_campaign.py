import json
import typer
from wxcli.errors import WebexError, handle_rest_error
from wxcli.auth import get_api
from wxcli.output import print_table, print_json
from wxcli.config import get_cc_base_url


app = typer.Typer(help="Manage Webex Contact Center cc-campaign.")


@app.command("create")
def create(
    id_param: str = typer.Option(None, "--id", help="(required) The id represents the unique id with which the Campaign Requ"),
    vendor_version: str = typer.Option(None, "--vendor-version", help="(required) Vendor specific information, maximum length 32 characters."),
    campaign_type: str = typer.Option(None, "--campaign-type", help="(required) Type of campaign and campaignType should be one of \"progress"),
    campaign_name: str = typer.Option(None, "--campaign-name", help="(Optional) Used if different than id, maximum length 64 char"),
    auth_token: str = typer.Option(None, "--auth-token", help="(Not in use) The token needed by the dialer for querying rec"),
    dialing_rate: str = typer.Option(None, "--dialing-rate", help="(required) Number of contacts to be dialed out per available Agent. For"),
    entry_point_id: str = typer.Option(None, "--entry-point-id", help="(required) Webex Contact Center outdial entry point, maximum length 36"),
    dialing_list_fetch_url: str = typer.Option(None, "--dialing-list-fetch-url", help="(required) URL the dialer will use to fetch the list of contacts to dia"),
    outdial_ani: str = typer.Option(None, "--outdial-ani", help="(required) The ANI (E164)  that will be presented to the customer. Thes"),
    record_count: str = typer.Option(None, "--record-count", help="(required) Value to indicate the recordCount the Campaign Manager expec"),
    no_answer_ring_limit: str = typer.Option(None, "--no-answer-ring-limit", help="(Optional) Number of seconds before a dialed call from the d"),
    max_dialing_rate: str = typer.Option(None, "--max-dialing-rate", help="Caps the maximum dialing rate per agent at this value. The r"),
    abandon_rate_percentage: str = typer.Option(None, "--abandon-rate-percentage", help="The percentage of calls that are allowed to be abandoned. Th"),
    predictive_correction_pace: str = typer.Option(None, "--predictive-correction-pace", help="A count of the number of live voice connections that must oc"),
    predictive_gain: str = typer.Option(None, "--predictive-gain", help="The size of the adjustment to lines per agent each time an a"),
    reservation_percentage: str = typer.Option(None, "--reservation-percentage", help="(Not in use) The percentage of agents to reserve within the"),
    ivr_ports: str = typer.Option(None, "--ivr-ports", help="The number of IVR ports to use for this campaign. IVR ports"),
    preview_offer_timeout: str = typer.Option(None, "--preview-offer-timeout", help="(Required if previewOfferTimeoutAutoAction is provided, opti"),
    preview_offer_timeout_auto_action: str = typer.Option(None, "--preview-offer-timeout-auto-action", help="(Required if previewOfferTimeout is provided, optional other"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Start Campaign Request\n\nExample --json-body:\n  '{"id":"...","vendorVersion":"...","campaignType":"...","dialingRate":0,"entryPointId":"...","dialingListFetchURL":"...","outdialANI":"...","recordCount":0}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/dialer/campaign"
    if json_body:
        body = json.loads(json_body)
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
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)



@app.command("update")
def update(
    campaign_id: str = typer.Argument(help="campaignId"),
    dialing_rate: str = typer.Option(None, "--dialing-rate", help="Number of contacts to be dialed out per available Agent. For"),
    campaign_name: str = typer.Option(None, "--campaign-name", help="(Optional) Used if different than id, maximum length 64 char"),
    auth_token: str = typer.Option(None, "--auth-token", help="(Not in use) The token needed by the dialer for querying rec"),
    dialing_list_fetch_url: str = typer.Option(None, "--dialing-list-fetch-url", help="URL the dialer will use to fetch the list of contacts to dia"),
    outdial_ani: str = typer.Option(None, "--outdial-ani", help="The ANI (E164)  that will be presented to the customer. Thes"),
    no_answer_ring_limit: str = typer.Option(None, "--no-answer-ring-limit", help="(Optional) Number of seconds before a dialed call from the d"),
    max_dialing_rate: str = typer.Option(None, "--max-dialing-rate", help="Caps the maximum dialing rate per agent at this value. The r"),
    reservation_percentage: str = typer.Option(None, "--reservation-percentage", help="(Not in use) The percentage of agents to reserve within the"),
    preview_offer_timeout: str = typer.Option(None, "--preview-offer-timeout", help="(Required only if previewOfferTimeoutAutoAction is provided)"),
    preview_offer_timeout_auto_action: str = typer.Option(None, "--preview-offer-timeout-auto-action", help="(Required only if previewOfferTimeout is provided) The autom"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Campaign Request\n\nExample --json-body:\n  '{"dialingRate":0,"dialingListFetchURL":"...","outdialANI":"...","campaignName":"...","authToken":"...","noAnswerRingLimit":0,"maxDialingRate":0,"reservationPercentage":0}'."""
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/dialer/campaign/{campaign_id}"
    if json_body:
        body = json.loads(json_body)
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
    typer.echo(f"Updated.")



@app.command("delete")
def delete(
    campaign_id: str = typer.Argument(help="campaignId"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Stop Campaign Request."""
    if not force:
        typer.confirm(f"Delete {campaign_id}?", abort=True)
    api = get_api(debug=debug)
    cc_base_url = get_cc_base_url()
    url = f"{cc_base_url}/dialer/campaign/{campaign_id}"
    try:
        api.session.rest_delete(url)
    except WebexError as e:
            handle_rest_error(e)
    typer.echo(f"Deleted: {campaign_id}")


