"""Hand-written `test` command for the `cc-functions` group.

Ported from wxcc-flow (`wxcc/src/wxcc_flow/functions.py:111-125`, Plan 2
Task 15):

    wxcc-flow functions test FUNCTION_ID BODY.json
        -> wxcli cc-functions test FUNCTION_ID --json-body '{"inputs": {...}}'

The other ten Custom Function commands are generated from the CC spec's
`Functions` tag (`cc_functions.py`). This one is hand-written because
`POST /v1/{orgId}/functions/{id}:test` was removed from the published spec
upstream on 2026-07-26 (`tools/CLAUDE.md`) while the endpoint is still live.
`register(app)` mounts it onto the generated cc-functions Typer app
(`_lazy.GROUP_EXTENSIONS`).

Changed from wxcc: the body is `--json-body` (inline JSON, file://path, a
path, or `-` for stdin), not a second positional argument.
"""
from __future__ import annotations

import httpx
import typer

from wxcli.auth import get_api
from wxcli.common import emit, load_json_body
from wxcli.config import get_cc_base_url, get_cc_org_id
from wxcli.errors import WebexError, handle_network_error, handle_rest_error


def register(app: typer.Typer) -> None:
    """Register `test` on the generated cc-functions app."""

    @app.command("test", short_help="Run a Custom Function with a test payload.")
    def test(
        function_id: str = typer.Argument(help="24-char hex id, from: wxcli cc-functions list"),
        json_body: str = typer.Option(..., "--json-body", help="Test payload, {\"inputs\": {...}}. Accepts inline JSON, file://path, a path, or - for stdin."),
        output: str = typer.Option("json", "--output", "-o", help="Output format: table|json|text"),
        fields: str = typer.Option(None, "--fields", help="JMESPath expression selecting/filtering response fields, e.g. \"[].{name:name,id:id}\""),
        debug: bool = typer.Option(False, "--debug"),
    ):
        """Run a Custom Function with a test payload.

        Implicitly publishes the latest draft first, so it always executes the
        most recent source. This operation is absent from the published OpenAPI
        spec but is live (verified 2026-07-25).

        Known limitation: on some orgs this returns 400 "Failed to test custom
        fn, received unexpected response". The request shape is correct
        ({"inputs": {...}} and {} both parse; {"inputs": []} returns "request
        body is not readable"), and it reproduces on a no-input function that
        returns a constant, so the failure is the execution backend, not the
        payload (verified 2026-07-25). Use the test panel in the Flow Designer
        UI instead.

        \b
        Example: wxcli cc-functions test FUNCTION_ID --json-body '{"inputs": {"name": "x"}}'
        """
        body = load_json_body(json_body)
        api = get_api(debug=debug)
        cc_base_url = get_cc_base_url()
        org_id = get_cc_org_id(api.session)
        url = f"{cc_base_url}/v1/{org_id}/functions/{function_id}:test"
        try:
            result = api.session.rest_post(url, json=body)
        except WebexError as e:
            handle_rest_error(e)
        except httpx.HTTPError as e:
            handle_network_error(e)
        emit(result, output=output, fields=fields)
