import json
import httpx
import typer
from wxcli.auth import get_api
from wxcli.errors import WebexError, handle_rest_error, handle_network_error
from wxcli.output import print_table, print_json
from wxcli.common import emit, load_json_body
from wxcli.config import resolve_org_id


app = typer.Typer(help="Manage Webex Calling domains.")


_BODY_SKELETON_GET_DOMAIN_VERIFICATION = '{"domain":"..."}'

@app.command("get-domain-verification", short_help="Get Domain Verification Token.")
def get_domain_verification(
    domain: str = typer.Option(None, "--domain", help="A valid domain name."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Domain Verification Token.\n\n\b\nExample: wxcli domains get-domain-verification --domain DOMAIN\n\n\b\nExample --json-body: '{"domain":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_GET_DOMAIN_VERIFICATION), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/identity/organizations/{org_id}/actions/getDomainVerificationToken"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if domain is not None:
            body["domain"] = domain
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_VERIFY_DOMAIN = '{"domain":"...","claimDomain":true,"reserveDomain":true}'

@app.command("verify-domain", short_help="Verify Domain.")
def verify_domain(
    domain: str = typer.Option(None, "--domain", help="The domain name to be verified."),
    claim_domain: str = typer.Option(None, "--claim-domain", help="A boolean to specify whether the domain needs to be claimed. The default value is false. If false, the domain will be verified but not claimed."),
    reserve_domain: str = typer.Option(None, "--reserve-domain", help="For FedRAMP only: If true, add the domain to the FedRAMP reserved domain list. The default value is false."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Verify Domain.\n\n\b\nExample: wxcli domains verify-domain --domain DOMAIN\n\n\b\nExample --json-body: '{"domain":"...","claimDomain":true,"reserveDomain":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_VERIFY_DOMAIN), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/identity/organizations/{org_id}/actions/verifyDomain"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if domain is not None:
            body["domain"] = domain
        if claim_domain is not None:
            body["claimDomain"] = claim_domain
        if reserve_domain is not None:
            body["reserveDomain"] = reserve_domain
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_CLAIM_DOMAIN = '{"data":[{"domain":"..."}],"forceDomainClaim":true,"claimDomainOnly":true}'

@app.command("claim-domain", short_help="Claim Domain.")
def claim_domain(
    force_domain_claim: str = typer.Option(None, "--force-domain-claim", help="Indicate if the domain should be claimed when there are users outside the organization using the same domain. The default is true."),
    claim_domain_only: str = typer.Option(None, "--claim-domain-only", help="Indicate to just claim the domain only without searching/marking external users as transient. The default is false."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Claim Domain.\n\n\b\nExample --json-body: '{"data":[{"domain":"..."}],"forceDomainClaim":true,"claimDomainOnly":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_CLAIM_DOMAIN), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/identity/organizations/{org_id}/actions/claimDomain"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if force_domain_claim is not None:
            body["forceDomainClaim"] = force_domain_claim
        if claim_domain_only is not None:
            body["claimDomainOnly"] = claim_domain_only
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UNVERIFY_DOMAIN = '{"domain":"...","removePending":true}'

@app.command("unverify-domain", short_help="Unverify Domain.")
def unverify_domain(
    domain: str = typer.Option(None, "--domain", help="Domain name to be verified."),
    remove_pending: str = typer.Option(None, "--remove-pending", help="Specify whether to remove pending domain. Default is false (backward compatibility). If true, domains will be deleted from pending domain list."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Unverify Domain.\n\n\b\nExample: wxcli domains unverify-domain --domain DOMAIN\n\n\b\nExample --json-body: '{"domain":"...","removePending":true}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UNVERIFY_DOMAIN), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/identity/organizations/{org_id}/actions/unverifyDomain"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if domain is not None:
            body["domain"] = domain
        if remove_pending is not None:
            body["removePending"] = remove_pending
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)



_BODY_SKELETON_UNCLAIM_DOMAIN = '{"domain":"..."}'

@app.command("unclaim-domain", short_help="Unclaim Domain.")
def unclaim_domain(
    domain: str = typer.Option(None, "--domain", help="A claimed domain."),
    generate_json_body: bool = typer.Option(False, "--generate-json-body", help="Print a JSON body skeleton and exit, for use with --json-body."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body (overrides other options). Accepts inline JSON, file://path, a path, or - for stdin."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
    fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
    debug: bool = typer.Option(False, "--debug"),
):
    """Unclaim Domain.\n\n\b\nExample: wxcli domains unclaim-domain --domain DOMAIN\n\n\b\nExample --json-body: '{"domain":"..."}'"""
    if generate_json_body:
        typer.echo(json.dumps(json.loads(_BODY_SKELETON_UNCLAIM_DOMAIN), indent=2))
        raise typer.Exit(0)
    api = get_api(debug=debug)
    org_id = resolve_org_id(api.session)
    url = f"https://webexapis.com/identity/organizations/{org_id}/actions/unclaimDomain"
    if json_body:
        body = load_json_body(json_body)
    else:
        body = {}
        if domain is not None:
            body["domain"] = domain
    try:
        result = api.session.rest_post(url, json=body)
    except WebexError as e:
        handle_rest_error(e)
    except httpx.HTTPError as e:
        handle_network_error(e)
    emit(result, output=output, fields=fields)


