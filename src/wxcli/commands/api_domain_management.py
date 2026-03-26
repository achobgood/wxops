import json
import typer
from wxc_sdk.rest import RestError
from wxcli.auth import get_api
from wxcli.errors import handle_rest_error
from wxcli.output import print_table, print_json


app = typer.Typer(help="Manage Webex Calling api-domain-management.")


@app.command("get-domain-verification")
def get_domain_verification(
    org_id: str = typer.Argument(help="orgId"),
    domain: str = typer.Option(None, "--domain", help="A valid domain name."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Get Domain Verification Token."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/identity/organizations/{org_id}/actions/getDomainVerificationToken"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if domain is not None:
            body["domain"] = domain
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        handle_rest_error(e)
    print_json(result)



@app.command("verify-domain")
def verify_domain(
    org_id: str = typer.Argument(help="orgId"),
    domain: str = typer.Option(None, "--domain", help="The domain name to be verified."),
    claim_domain: str = typer.Option(None, "--claim-domain", help="A boolean to specify whether the domain needs to be claimed."),
    reserve_domain: str = typer.Option(None, "--reserve-domain", help="For FedRAMP only: If true, add the domain to the FedRAMP res"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Verify Domain."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/identity/organizations/{org_id}/actions/verifyDomain"
    if json_body:
        body = json.loads(json_body)
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
    except RestError as e:
        handle_rest_error(e)
    print_json(result)



@app.command("claim-domain")
def claim_domain(
    org_id: str = typer.Argument(help="orgId"),
    force_domain_claim: str = typer.Option(None, "--force-domain-claim", help="Indicate if the domain should be claimed when there are user"),
    claim_domain_only: str = typer.Option(None, "--claim-domain-only", help="Indicate to just claim the domain only without searching/mar"),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Claim Domain\n\nExample --json-body:\n  '{"data":[{"domain":"..."}],"forceDomainClaim":true,"claimDomainOnly":true}'."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/identity/organizations/{org_id}/actions/claimDomain"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if force_domain_claim is not None:
            body["forceDomainClaim"] = force_domain_claim
        if claim_domain_only is not None:
            body["claimDomainOnly"] = claim_domain_only
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        handle_rest_error(e)
    print_json(result)



@app.command("unverify-domain")
def unverify_domain(
    org_id: str = typer.Argument(help="orgId"),
    domain: str = typer.Option(None, "--domain", help="Domain name to be verified."),
    remove_pending: str = typer.Option(None, "--remove-pending", help="Specify whether to remove pending domain. Default is false ("),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Unverify Domain."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/identity/organizations/{org_id}/actions/unverifyDomain"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if domain is not None:
            body["domain"] = domain
        if remove_pending is not None:
            body["removePending"] = remove_pending
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        handle_rest_error(e)
    print_json(result)



@app.command("unclaim-domain")
def unclaim_domain(
    org_id: str = typer.Argument(help="orgId"),
    domain: str = typer.Option(None, "--domain", help="A claimed domain."),
    json_body: str = typer.Option(None, "--json-body", help="Full JSON body"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Unclaim Domain."""
    api = get_api(debug=debug)
    url = f"https://webexapis.com/identity/organizations/{org_id}/actions/unclaimDomain"
    if json_body:
        body = json.loads(json_body)
    else:
        body = {}
        if domain is not None:
            body["domain"] = domain
    try:
        result = api.session.rest_post(url, json=body)
    except RestError as e:
        handle_rest_error(e)
    print_json(result)


