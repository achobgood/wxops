import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Contact Center cc-campaign.")


@app.command("update")
def update(
    campaign_id: str = typer.Argument(help="campaignId"),
    dialing_list_fetch_url: str = typer.Option(None, "--dialing-list-fetch-url", help=""),
    outdial_ani: str = typer.Option(None, "--outdial-ani", help=""),
    reservation_percentage: str = typer.Option(None, "--reservation-percentage", help=""),
    preview_offer_timeout_auto_action: str = typer.Option(None, "--preview-offer-timeout-auto-action", help=""),
    preview_offer_timeout: str = typer.Option(None, "--preview-offer-timeout", help=""),
    dialing_rate: str = typer.Option(None, "--dialing-rate", help=""),
    max_dialing_rate: str = typer.Option(None, "--max-dialing-rate", help=""),
    campaign_name: str = typer.Option(None, "--campaign-name", help=""),
    auth_token: str = typer.Option(None, "--auth-token", help=""),
    no_answer_ring_limit: str = typer.Option(None, "--no-answer-ring-limit", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Update Campaign Request\n\nExample --json-body:\n  '{"dialingListFetchURL":"...","outdialANI":"...","reservationPercentage":"...","previewActionsDisabled":["..."],"previewOfferTimeoutAutoAction":"...","previewOfferTimeout":"..."}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/dialer/campaign/{campaign_id}"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if dialing_list_fetch_url is not None:
            body["dialingListFetchURL"] = dialing_list_fetch_url
        if outdial_ani is not None:
            body["outdialANI"] = outdial_ani
        if reservation_percentage is not None:
            body["reservationPercentage"] = reservation_percentage
        if preview_offer_timeout_auto_action is not None:
            body["previewOfferTimeoutAutoAction"] = preview_offer_timeout_auto_action
        if preview_offer_timeout is not None:
            body["previewOfferTimeout"] = preview_offer_timeout
        if dialing_rate is not None:
            body["dialingRate"] = dialing_rate
        if max_dialing_rate is not None:
            body["maxDialingRate"] = max_dialing_rate
        if campaign_name is not None:
            body["campaignName"] = campaign_name
        if auth_token is not None:
            body["authToken"] = auth_token
        if no_answer_ring_limit is not None:
            body["noAnswerRingLimit"] = no_answer_ring_limit
    try:
        result = api.session.rest_put(url, json=body)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
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
    url = f"https://webexapis.com/v1/dialer/campaign/{campaign_id}"
    try:
        api.session.rest_delete(url)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Deleted: {campaign_id}")



@app.command("create")
def create(
    dialing_list_fetch_url: str = typer.Option(None, "--dialing-list-fetch-url", help=""),
    outdial_ani: str = typer.Option(None, "--outdial-ani", help=""),
    predictive_correction_pace: str = typer.Option(None, "--predictive-correction-pace", help=""),
    predictive_gain: str = typer.Option(None, "--predictive-gain", help=""),
    reservation_percentage: str = typer.Option(None, "--reservation-percentage", help=""),
    entry_point_id: str = typer.Option(None, "--entry-point-id", help=""),
    ivr_ports: str = typer.Option(None, "--ivr-ports", help=""),
    preview_offer_timeout: str = typer.Option(None, "--preview-offer-timeout", help=""),
    preview_offer_timeout_auto_action: str = typer.Option(None, "--preview-offer-timeout-auto-action", help=""),
    dialing_rate: str = typer.Option(None, "--dialing-rate", help=""),
    campaign_type: str = typer.Option(None, "--campaign-type", help=""),
    id_param: str = typer.Option(None, "--id", help=""),
    vendor_version: str = typer.Option(None, "--vendor-version", help=""),
    max_dialing_rate: str = typer.Option(None, "--max-dialing-rate", help=""),
    abandon_rate_percentage: str = typer.Option(None, "--abandon-rate-percentage", help=""),
    record_count: str = typer.Option(None, "--record-count", help=""),
    campaign_name: str = typer.Option(None, "--campaign-name", help=""),
    auth_token: str = typer.Option(None, "--auth-token", help=""),
    no_answer_ring_limit: str = typer.Option(None, "--no-answer-ring-limit", help=""),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options)"),
    output: str = typer.Option("id", "--output", "-o", help="Output format: id|json"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Start Campaign Request\n\nExample --json-body:\n  '{"dialingListFetchURL":"...","outdialANI":"...","predictiveCorrectionPace":"...","predictiveGain":"...","reservationPercentage":"...","callProgressAnalysisParams":{"minSilencePeriod":"...","analysisPeriod":"...","minimumValidSpeech":"...","maxTimeAnalysis":"...","maxTermToneAnalysis":"...","terminatingToneDetect":"..."}}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/v1/dialer/campaign"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if dialing_list_fetch_url is not None:
            body["dialingListFetchURL"] = dialing_list_fetch_url
        if outdial_ani is not None:
            body["outdialANI"] = outdial_ani
        if predictive_correction_pace is not None:
            body["predictiveCorrectionPace"] = predictive_correction_pace
        if predictive_gain is not None:
            body["predictiveGain"] = predictive_gain
        if reservation_percentage is not None:
            body["reservationPercentage"] = reservation_percentage
        if entry_point_id is not None:
            body["entryPointId"] = entry_point_id
        if ivr_ports is not None:
            body["ivrPorts"] = ivr_ports
        if preview_offer_timeout is not None:
            body["previewOfferTimeout"] = preview_offer_timeout
        if preview_offer_timeout_auto_action is not None:
            body["previewOfferTimeoutAutoAction"] = preview_offer_timeout_auto_action
        if dialing_rate is not None:
            body["dialingRate"] = dialing_rate
        if campaign_type is not None:
            body["campaignType"] = campaign_type
        if id_param is not None:
            body["id"] = id_param
        if vendor_version is not None:
            body["vendorVersion"] = vendor_version
        if max_dialing_rate is not None:
            body["maxDialingRate"] = max_dialing_rate
        if abandon_rate_percentage is not None:
            body["abandonRatePercentage"] = abandon_rate_percentage
        if record_count is not None:
            body["recordCount"] = record_count
        if campaign_name is not None:
            body["campaignName"] = campaign_name
        if auth_token is not None:
            body["authToken"] = auth_token
        if no_answer_ring_limit is not None:
            body["noAnswerRingLimit"] = no_answer_ring_limit
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        err = str(e)
        if "25008" in err:
            typer.echo(f"Error: Missing required field. {e}", err=True)
            typer.echo("Tip: Use --json-body for full control over the request body.", err=True)
        elif "4003" in err or "Target user not authorized" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires a user-level OAuth token, not an admin or service app token.", err=True)
        elif "4008" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This endpoint requires the target user to have a Webex Calling license.", err=True)
        elif "25409" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.", err=True)
        elif "wxcc" in err and "403" in err:
            typer.echo(f"Error: {e}", err=True)
            typer.echo("Tip: Contact Center APIs require CC-scoped OAuth (cjp:config_read / cjp:config_write). Standard admin tokens won't work.", err=True)
        else:
            typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    if output == "json":
        print_json(result)
    elif isinstance(result, dict) and "id" in result:
        typer.echo(f"Created: {result['id']}")
    elif not result or result == {}:
        typer.echo("Created.")
    else:
        print_json(result)


