"""Centralized error handler for wxcli commands."""
import base64
import json
import re
import sys

import typer


class WebexError(Exception):
    """Webex API error. Message-first: WebexError(response.text) remains valid.

    status_code and body (parsed JSON error, when parseable) are optional
    enrichments so handlers can key off status instead of substring matching.
    """

    def __init__(self, message: str, status_code: int | None = None, body: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


# Code 4003 is deliberately absent. It is real but ambiguous: the Cloud Calling
# spec lists it as `User Not Found` (validate=true), while live runs also return
# `[Error 4003] Unauthorized request: ...` for admin-token writes to user-only
# endpoints. Only the message distinguishes them, so the OAuth tip is keyed on
# the message in _MESSAGE_TIPS instead.
_ERROR_TIPS = {
    4008: "The target user has no Webex Calling license. Check with: wxcli people show <personId> --calling-data true (an unlicensed user comes back with no extension or locationId). See what is available with: wxcli licenses list",
    9601: "This endpoint acts as the signed-in user, so it needs a user-level OAuth token — an admin or service app token cannot stand in. Re-run: wxcli configure with that user's own access token, then confirm the owner with: wxcli whoami",
    25008: "Use --json-body for full control over the request body.",
    25409: "This workspace setting requires a Professional license. Use -o json with the /features/ path commands for Basic workspaces.",
    28018: "CX Essentials is not enabled for this queue. Use --has-cx-essentials true when creating/querying CX queues.",
}

_MESSAGE_TIPS = {
    "Target user not authorized": "This endpoint needs a user-level OAuth token, not an admin or service app token. Re-run: wxcli configure with the target user's own access token, then confirm the owner with: wxcli whoami",
}

# Last-resort tips, keyed on the HTTP status carried by WebexError. Reached only
# when no errorCode or message tip matched, so a specific tip always wins.
_STATUS_TIPS = {
    400: "The request body or a parameter was rejected. Re-check every ID you passed against the list command of the group it came from; if this command sends a body, re-run it with --generate-json-body to print the exact skeleton it accepts (that exits before authenticating).",
    401: "The token is missing, expired, or revoked. Re-run: wxcli configure — then confirm it works with: wxcli whoami",
    403: "The token is valid but is not an admin of the target org, or lacks this endpoint's scope. Run: wxcli whoami — it prints the token owner and the 'Target:' org. If the Target line is wrong or missing, run: wxcli switch-org <orgId>",
    404: "No such resource in the target org — the ID may belong to a different org, or already be deleted. Get a live ID from this command group's list subcommand, and confirm which org you are pointed at with: wxcli whoami",
    # A 405 here is usually not about the verb. Live: a PUT to /people that
    # succeeded on three licensed users returned this on an unlicensed one, and
    # workspace /telephony/config/ returns it for Basic licenses (Known Issue #6).
    405: "The API rejected this method on this path — but the same verb works on comparable resources, so treat this as an entitlement problem before a verb problem. Check the target is licensed for what you are writing: wxcli people show <personId> --calling-data true (an unlicensed user comes back with no extension or locationId).",
    409: "The resource is still referenced by something else, so it cannot be changed or deleted yet. Delete the dependents first — wxcli cleanup run removes them in dependency-safe order.",
    429: "Rate limited, and the built-in retries were already exhausted. Wait and re-run; raise the retry budget with WXCLI_MAX_ATTEMPTS=<n>.",
}


def _extract_error_code(err: str) -> int | None:
    """Extract error code from a Webex API JSON error response."""
    try:
        body = json.loads(err)
        for entry in body.get("errors", []):
            code = entry.get("errorCode") or entry.get("code")
            if code is not None:
                return int(code)
    except (json.JSONDecodeError, ValueError, AttributeError):
        pass
    return None


def _truncate_html(err: str) -> str:
    """Extract a readable message from HTML error responses."""
    if not err.lstrip().startswith("<"):
        return err
    import re
    title = re.search(r"<title>(.*?)</title>", err, re.IGNORECASE)
    h1 = re.search(r"<h1>(.*?)</h1>", err, re.IGNORECASE)
    msg = (h1 and h1.group(1)) or (title and title.group(1)) or "Non-JSON error response"
    return msg.strip()


_SPARK_URN = re.compile(r"^ciscospark://[^/]+/([A-Z_]+)/")


def decode_id_kind(token: str) -> str | None:
    """'Y2lzY29zcGFyazovL3VzL0RFVklDRS8x…' -> 'DEVICE'. None if not a Webex id.

    Webex ids are base64 of `ciscospark://<cluster>/<KIND>/<uuid>`, so the kind
    is knowable locally, before the call and before any error.
    """
    if len(token) < 24 or not re.fullmatch(r"[A-Za-z0-9_\-+/]+=*", token):
        return None
    try:
        raw = base64.b64decode(token + "=" * (-len(token) % 4)).decode("utf-8")
    except Exception:
        return None
    m = _SPARK_URN.match(raw)
    return m.group(1) if m else None


# ALLOWLIST, not broad detection. A naive "declared kind != passed kind" check
# cannot be trusted here: 79 CLI arguments declare a kind their own name
# contradicts (`location_id` help-typed PEOPLE, `call_queue_id` typed
# HUNT_GROUP — see CLAUDE.md), so comparing against the declared kind would
# manufacture false warnings on correct calls. Only pairs proven live go here.
#
# Keyed (invoked group, kind actually passed). Each entry must name a remedy
# that produces the right id, or it is not worth printing.
_ID_KIND_TIPS = {
    ("device-settings", "DEVICE"): (
        "You passed a DEVICE id, but this group needs the callingDeviceId — a "
        "different id for the same phone, of kind CALLING_DEVICE. Webex reports "
        "the mismatch as 'device not found', which reads as though the phone does "
        "not exist, so this is easy to misdiagnose. Get the right id with: "
        "wxcli devices show <deviceId> -o json (use the callingDeviceId field)."
    ),
}


def _passed_id_kinds() -> list[tuple[str, str]]:
    """(token-prefix, KIND) for every Webex id on the command line."""
    out = []
    for arg in sys.argv[1:]:
        kind = decode_id_kind(arg)
        if kind:
            out.append((arg[:12] + "…", kind))
    return out


def _id_kind_tip() -> str | None:
    """The allowlisted remedy for an id-kind mismatch, if one applies."""
    group = _invoked_group()
    for _, kind in _passed_id_kinds():
        tip = _ID_KIND_TIPS.get((group, kind))
        if tip:
            return tip
    return None


def _invoked_group() -> str:
    """The command group this process was invoked with, e.g. 'cc-queue'.

    Every root-level option is a boolean flag (--version, --no-update-check),
    so none consumes a value and the first non-flag token is always the group.
    """
    for arg in sys.argv[1:]:
        if not arg.startswith("-"):
            return arg
    return ""


def _is_cc_403(e: WebexError, err: str) -> bool:
    """A 403 raised by a Contact Center (cc-*) command.

    Keys on the real HTTP status, not on the literal '403' appearing inside the
    body — auth.py builds WebexError from response.text alone, so the status is
    on the exception and never in the text. The CC discriminator has the same
    problem: the api.wxcc-* host is not in the body either, so argv carries it.
    The body check is kept for the case where the payload does name the host.
    """
    return e.status_code == 403 and (_invoked_group().startswith("cc-") or "wxcc" in err)


def handle_rest_error(e: WebexError) -> None:
    """Centralized error handler with actionable tips."""
    err = str(e)
    code = _extract_error_code(err)

    # Order is specific-to-generic. A CC 403 that also carries a known errorCode
    # takes the earlier branch, which is correct: no code in _ERROR_TIPS is
    # documented as arriving with a 403 (4008/25409 are 404/405, 25008/28018 are
    # 400), so an errorCode on a 403 is new information the scope tip would hide.
    if code and code in _ERROR_TIPS:
        tip = _ERROR_TIPS[code]
    elif any(msg in err for msg in _MESSAGE_TIPS):
        tip = next(v for k, v in _MESSAGE_TIPS.items() if k in err)
    elif _id_kind_tip():
        tip = _id_kind_tip()
    elif _is_cc_403(e, err):
        tip = "Contact Center APIs need CC-scoped OAuth (cjp:config_read / cjp:config_write); a personal access token or plain admin token always gets 403 here. Create an integration with those scopes at developer.webex.com, complete the OAuth flow, then re-run: wxcli configure with that token."
    else:
        tip = _STATUS_TIPS.get(e.status_code)

    typer.echo(f"Error: {_truncate_html(err)}", err=True)
    if tip:
        typer.echo(f"Tip: {tip}", err=True)

    # Neutral, and deliberately not a diagnosis. "No such resource" reads as
    # "it does not exist" when the real fault is often an id of the wrong KIND
    # for this endpoint. Stating what was actually passed costs one line and
    # cannot be wrong — unlike guessing what the endpoint wanted, which the 79
    # mis-declared arguments make unsafe.
    if e.status_code in (400, 404):
        kinds = _passed_id_kinds()
        if kinds:
            shown = ", ".join(f"{tok} = {kind}" for tok, kind in kinds)
            typer.echo(f"Ids you passed, decoded: {shown}", err=True)
    raise typer.Exit(1)


_NETWORK_TIPS = {
    "ReadTimeout": "The server did not respond in time. Raise the limit with WXCLI_READ_TIMEOUT=<seconds>.",
    "WriteTimeout": "The request body could not be sent in time. Raise WXCLI_READ_TIMEOUT=<seconds>.",
    "ConnectTimeout": "Could not reach the API host in time. Check connectivity, or raise WXCLI_CONNECT_TIMEOUT=<seconds>.",
    "ConnectError": "Could not connect to the API host. Check network access and any proxy settings.",
    "PoolTimeout": "Connection pool exhausted. Retry, or reduce concurrency.",
}


def handle_network_error(e: Exception) -> None:
    """Handle transport failures that never produced an HTTP response.

    These bypass WebexError entirely — without this, a read timeout reaches
    the user as a raw traceback.
    """
    kind = type(e).__name__
    detail = f"{kind}: {e}" if str(e) else kind
    typer.echo(f"Error: request failed — {detail}", err=True)
    typer.echo(f"Tip: {_NETWORK_TIPS.get(kind, 'Transport-level failure with no HTTP response.')}", err=True)
    raise typer.Exit(1)
