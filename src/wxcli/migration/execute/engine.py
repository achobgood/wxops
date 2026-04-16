"""Async bulk execution engine for CUCM migration operations.

Processes migration operations concurrently via aiohttp with:
- Semaphore-based rate limiting
- Automatic 429 retry with Retry-After backoff
- Per-operation status tracking via update_op_status()
- 409 auto-recovery (search for existing resource)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

import aiohttp

from wxcli.migration.execute.handlers import HANDLER_REGISTRY, SkippedResult
from wxcli.migration.execute.runtime import get_next_batch, update_op_status
from wxcli.migration.store import MigrationStore


class JobErrorFetchFailed(Exception):
    """Raised when the bulk job errors endpoint cannot be read.

    Distinguishes a legitimately-empty errors list (200 response with empty
    ``items``) from a fetch failure (non-200 or network error). Callers must
    treat the fetch failure as "we don't know which devices failed" and
    escalate to a total failure rather than silently assume zero errors.
    """

logger = logging.getLogger(__name__)

BASE = "https://webexapis.com/v1"
MAX_RETRIES = 5

# Sentinel key: when present in a call's body dict, the engine deep-merges
# the previous call's response body into this body before sending.
# The sentinel key itself is stripped before the request is made.
# Usage: handler emits [("GET", url, None), ("PUT", url, {**overrides, "_merge_from_previous": True})]
MERGE_FROM_PREVIOUS = "_merge_from_previous"


async def poll_job_until_complete(
    session: aiohttp.ClientSession,
    job_type: str,
    job_id: str,
    poll_interval: float = 5,
    max_poll_time: float = 600,
    ctx: dict | None = None,
) -> dict:
    """Poll a Webex bulk device job until completion or timeout.

    Returns the final job status dict. Raises TimeoutError if max_poll_time
    elapses without reaching COMPLETED or FAILED.
    """
    from urllib.parse import urlencode

    ctx = ctx or {}
    path = f"/telephony/config/jobs/devices/{job_type}/{job_id}"
    url = f"{BASE}{path}"
    if ctx.get("orgId"):
        url += f"?{urlencode({'orgId': ctx['orgId']})}"

    elapsed: float = 0
    while elapsed <= max_poll_time:
        async with session.get(url) as resp:
            body = await resp.json()

        exit_code = body.get("latestExecutionExitCode", "UNKNOWN")
        if exit_code in ("COMPLETED", "FAILED"):
            logger.info(
                "Job %s %s: exit=%s updated=%d",
                job_type, job_id[:16], exit_code, body.get("updatedCount", 0),
            )
            return body

        logger.debug(
            "Job %s %s: %d%% (elapsed %.0fs)",
            job_type, job_id[:16], body.get("percentageComplete", 0), elapsed,
        )
        if elapsed >= max_poll_time:
            break
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

    raise TimeoutError(f"Job {job_type}/{job_id} did not complete within {max_poll_time}s")


async def fetch_job_errors(
    session: aiohttp.ClientSession,
    job_type: str,
    job_id: str,
    ctx: dict | None = None,
) -> list[dict]:
    """GET the errors endpoint for a bulk job and return the items list.

    GET /v1/telephony/config/jobs/devices/{jobType}/{jobId}/errors

    Returns the parsed ``items`` list on a 200 response (empty list if the
    payload carries no items). Raises ``JobErrorFetchFailed`` on any
    non-200 status or network exception so the caller can distinguish
    "no errors reported" from "we couldn't ask". Fix #6.
    """
    from urllib.parse import urlencode

    ctx = ctx or {}
    path = f"/telephony/config/jobs/devices/{job_type}/{job_id}/errors"
    url = f"{BASE}{path}"
    if ctx.get("orgId"):
        url += f"?{urlencode({'orgId': ctx['orgId']})}"

    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise JobErrorFetchFailed(
                    f"fetch_job_errors {job_id[:16]} -> HTTP {resp.status}"
                )
            body = await resp.json()
    except JobErrorFetchFailed:
        raise
    except Exception as e:
        raise JobErrorFetchFailed(
            f"fetch_job_errors {job_id[:16]} raised: {e}"
        ) from e

    if not isinstance(body, dict):
        return []
    items = body.get("items", [])
    return list(items) if isinstance(items, list) else []


@dataclass
class OpResult:
    """Result of executing one operation."""
    node_id: str
    status: int = 0
    webex_id: str | None = None
    error: str | None = None
    body: dict = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return 200 <= self.status < 300


def reset_in_progress(store: MigrationStore) -> int:
    """Reset any in_progress ops back to pending. Returns count reset."""
    cursor = store.conn.execute(
        "UPDATE plan_operations SET status = 'pending' WHERE status = 'in_progress'"
    )
    count = cursor.rowcount
    store.conn.commit()
    if count:
        logger.info("Reset %d in_progress operations to pending", count)
    return count


async def execute_single_op(
    session: aiohttp.ClientSession,
    node_id: str,
    calls: list[tuple[str, str, dict | None]],
    semaphore: asyncio.Semaphore,
    max_retries: int = MAX_RETRIES,
    require_webex_id: bool = False,
) -> OpResult:
    """Execute one operation's API call(s) with rate limiting and retry.

    For multi-call operations (e.g., user:configure_settings), calls are
    executed sequentially. The operation fails if any sub-call fails.
    The webex_id comes from the first call's response (the create).

    When ``require_webex_id`` is True (Fix #18 — create ops), a success
    response with no ``id`` / ``code`` in the body is treated as FAILED
    instead of silently succeeding. Some backends return 200/204 without a
    body on server-side hiccups — the resource may not exist and we'd have
    no way to reference it in later ops.
    """
    webex_id = None
    last_body = {}

    for method, url, body in calls:
        # Read-before-write: merge previous response into this body if requested
        if isinstance(body, dict) and body.pop(MERGE_FROM_PREVIOUS, None):
            body = {**last_body, **body}

        for attempt in range(max_retries):
            try:
                async with semaphore:
                    async with session.request(method, url, json=body) as resp:
                        resp_status = resp.status
                        try:
                            resp_body = await resp.json()
                        except Exception:
                            resp_body = {}
                        resp_headers = resp.headers

                if resp_status == 429:
                    retry_after = int(resp_headers.get("Retry-After", 5))
                    logger.debug("429 on %s, retry after %ds", node_id, retry_after)
                    await asyncio.sleep(retry_after)
                    continue

                if resp_status >= 400:
                    error_msg = resp_body.get("message") or resp_body.get("errors", str(resp_body))
                    return OpResult(
                        node_id=node_id, status=resp_status,
                        error=f"{resp_status}: {error_msg}", body=resp_body,
                    )

                # Success — extract ID from first call.
                # Activation-code responses (POST /devices/activationCode)
                # return {"code": "...", "expiryTime": "..."} with no "id" field,
                # so fall back to "code" so the activation string is persisted
                # into plan_operations.webex_id for export.
                if webex_id is None and isinstance(resp_body, dict):
                    webex_id = resp_body.get("id") or resp_body.get("code")
                last_body = resp_body
                break  # Move to next sub-call

            except aiohttp.ClientError as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return OpResult(
                    node_id=node_id, status=0,
                    error=f"Connection error: {e}", body={},
                )
        else:
            return OpResult(
                node_id=node_id, status=429,
                error="Max retries exceeded (429)", body={},
            )

    # Fix #18: create ops must return a usable identifier. A silent success
    # with no id means the downstream planner has no webex_id to record, and
    # any dependent op will fail to resolve this create's output. Surface it
    # as a FAILED op instead of silently completing.
    if require_webex_id and not webex_id:
        return OpResult(
            node_id=node_id, status=500,
            error="create succeeded but response contained no id/code",
            body=last_body,
        )

    return OpResult(
        node_id=node_id, status=200,
        webex_id=webex_id, body=last_body,
    )


# Webex bulk job IDs are base64-encoded URN strings (typically 60-120 chars).
# We enforce a floor of 10 characters — this catches the spec's obvious
# garbage cases ("x", "", whitespace) *and* any plausible truncation /
# off-by-one parsing bug. 10 is deliberately conservative vs. the real 60+
# length: enough to rule out any 1-9 char typo while staying well under the
# real minimum so test fixtures that use mock IDs just need to use
# realistic-looking strings (which is cheap to do).
_MIN_JOB_ID_LEN = 10


def _validate_job_id(job_id: str | None) -> None:
    """Fix #8: raise ``ValueError`` for missing/malformed bulk job IDs.

    Webex returns base64-encoded URN job IDs. A submit response with an
    empty, None, single-char, or whitespace ``id`` field points to either an
    upstream backend bug or a parsing error — polling such an ID would 404
    endlessly. Fail fast with a clear error so the operator knows the submit
    response was bogus and the bulk op is FAILED rather than silently stuck
    mid-poll.
    """
    if job_id is None or not isinstance(job_id, str):
        raise ValueError(f"job_id is missing or not a string: {job_id!r}")
    if not job_id.strip():
        raise ValueError(f"job_id is empty / whitespace: {job_id!r}")
    if len(job_id) < _MIN_JOB_ID_LEN:
        raise ValueError(
            f"job_id {job_id!r} is implausibly short "
            f"(<{_MIN_JOB_ID_LEN} chars); refusing to poll"
        )


async def execute_bulk_op(
    session: aiohttp.ClientSession,
    node_id: str,
    resource_type: str,
    calls: list[tuple[str, str, dict | None]],
    semaphore: asyncio.Semaphore,
    poll_interval: float = 5,
    max_poll_time: float = 600,
    ctx: dict | None = None,
    fallback_context: dict | None = None,
) -> OpResult:
    """Submit a Webex bulk job, poll to completion, return an OpResult.

    Expects exactly one call in ``calls`` — the submit POST. The response
    body's ``id`` is the job ID. After submission, this function polls
    using ``poll_job_until_complete`` until the job reaches COMPLETED or
    FAILED (or times out). If the job completes but ``updatedCount`` is
    less than the number of covered devices and ``fallback_context`` is
    provided, the function fetches the job errors endpoint, identifies
    failed device IDs, and re-runs a per-device handler for each.
    """
    from wxcli.migration.execute import BULK_JOB_TYPES

    if len(calls) != 1:
        return OpResult(
            node_id=node_id, status=0,
            error=f"execute_bulk_op expects exactly 1 call, got {len(calls)}",
            body={},
        )

    method, url, body = calls[0]
    job_type = BULK_JOB_TYPES.get(resource_type)
    if not job_type:
        return OpResult(
            node_id=node_id, status=0,
            error=f"No BULK_JOB_TYPES mapping for {resource_type}",
            body={},
        )

    # Submit the job
    try:
        async with semaphore:
            async with session.request(method, url, json=body) as resp:
                submit_status = resp.status
                submit_body = await resp.json()
    except aiohttp.ClientError as e:
        return OpResult(node_id=node_id, status=0, error=f"Submit error: {e}", body={})

    if submit_status >= 400:
        msg = submit_body.get("message") if isinstance(submit_body, dict) else str(submit_body)
        return OpResult(
            node_id=node_id, status=submit_status,
            error=f"{submit_status}: {msg}", body=submit_body or {},
        )

    job_id = submit_body.get("id") if isinstance(submit_body, dict) else None
    if not job_id:
        return OpResult(
            node_id=node_id, status=submit_status,
            error="Submit succeeded but returned no job id",
            body=submit_body or {},
        )

    # Fix #8: validate the job ID *before* polling. A non-empty but malformed
    # id (e.g. truncated, single-char) would otherwise pass the `if not job_id`
    # check above and then fail mid-poll with a confusing 404. Surface as a
    # FAILED OpResult with the offending value attached for diagnostics.
    try:
        _validate_job_id(job_id)
    except ValueError as e:
        return OpResult(
            node_id=node_id, status=500,
            error=f"Bulk submit returned malformed job_id: {e}",
            body=submit_body or {},
        )

    # Poll to completion
    try:
        final = await poll_job_until_complete(
            session, job_type, job_id,
            poll_interval=poll_interval,
            max_poll_time=max_poll_time,
            ctx=ctx,
        )
    except TimeoutError as e:
        return OpResult(node_id=node_id, status=0, error=str(e), body={"id": job_id})

    exit_code = final.get("latestExecutionExitCode", "UNKNOWN")
    if exit_code != "COMPLETED":
        return OpResult(
            node_id=node_id, status=500,
            error=f"Job {job_id} ended in {exit_code}",
            body=final,
        )

    # Partial-failure check.
    updated = final.get("updatedCount", 0)
    expected = 0
    excluded_unresolved = 0
    if fallback_context:
        expected = len(fallback_context.get("covered_devices", []))
        # Fix #5/#7 companion: devices the upstream create never produced.
        # `_build_fallback_context` already logged each one at WARN.
        excluded_unresolved = fallback_context.get("excluded_unresolved_count", 0)

    # Fix #19: when no fallback_context is configured we used to return
    # success unconditionally. That silently accepted 0-update jobs. Now
    # treat (fallback_context is None AND updated == 0) as a hard failure;
    # when updated > 0 we keep the legacy success path (no way to verify
    # `expected` without context, but SOMETHING worked).
    if fallback_context is None:
        if updated == 0:
            return OpResult(
                node_id=node_id, status=500,
                error=(
                    f"Bulk job {job_id}: updated 0 devices and no fallback "
                    "configured; cannot verify success"
                ),
                body=final,
            )
        return OpResult(
            node_id=node_id, status=200, webex_id=job_id, body=final,
        )

    if updated >= expected:
        # Fix #7: even on the all-bulk-succeeded path, log a summary that
        # accounts for the silently-excluded devices so the operator never
        # has to guess whether anything was dropped.
        logger.info(
            "Bulk job %s summary: bulk_updated=%d/%d, fallback_attempted=0, "
            "fallback_recovered=0, excluded_unresolved=%d",
            job_id[:16], updated, expected, excluded_unresolved,
        )
        return OpResult(
            node_id=node_id, status=200, webex_id=job_id, body=final,
        )

    logger.info(
        "Bulk job %s partial: %d/%d succeeded — running per-device fallback",
        job_id[:16], updated, expected,
    )
    failed_ids = await _resolve_failed_devices(
        session, job_type, job_id, fallback_context, ctx,
    )
    if not failed_ids:
        logger.warning(
            "Bulk job %s updated=%d < expected=%d but error endpoint returned nothing",
            job_id[:16], updated, expected,
        )
        return OpResult(
            node_id=node_id, status=500,
            error=(
                f"Bulk job {job_id} partial failure with no error items "
                f"(excluded_unresolved={excluded_unresolved})"
            ),
            body=final,
        )

    fallback_ok, fallback_error = await _run_per_device_fallback(
        session, failed_ids, fallback_context, semaphore,
    )
    # Fix #4: even on fallback_ok we must verify we actually attempted every
    # missing device. If the errors endpoint returned an incomplete list,
    # some devices are still unaccounted for and the op must be reported
    # FAILED, not COMPLETED.
    attempted = len(failed_ids)
    missing = (expected - updated) - attempted
    fallback_recovered = attempted if fallback_ok else 0
    # Fix #7: summary log fires on EVERY exit path of the fallback branch so
    # bulk_updated, fallback_attempted, fallback_recovered, and the count of
    # devices excluded by `_build_fallback_context` are always visible to
    # the operator. Logged before the early-return so we capture it on
    # both COMPLETED and FAILED outcomes.
    logger.info(
        "Bulk job %s summary: bulk_updated=%d/%d, fallback_attempted=%d, "
        "fallback_recovered=%d, excluded_unresolved=%d",
        job_id[:16], updated, expected, attempted,
        fallback_recovered, excluded_unresolved,
    )
    if fallback_ok:
        if missing > 0:
            logger.warning(
                "Bulk job %s: fallback recovered %d but %d device(s) never attempted",
                job_id[:16], attempted, missing,
            )
            return OpResult(
                node_id=node_id, status=500,
                error=(
                    f"Bulk {job_id}: partial failure — {updated} succeeded in bulk, "
                    f"{attempted} recovered via fallback, but {missing} device(s) "
                    f"still unaccounted for "
                    f"(excluded_unresolved={excluded_unresolved})"
                ),
                body=final,
            )
        logger.info("Bulk job %s: fallback recovered all %d failed devices",
                    job_id[:16], attempted)
        return OpResult(
            node_id=node_id, status=200, webex_id=job_id, body=final,
        )
    return OpResult(
        node_id=node_id, status=500,
        error=(
            f"Bulk {job_id}: fallback failed — {fallback_error} "
            f"(excluded_unresolved={excluded_unresolved})"
        ),
        body=final,
    )


async def _resolve_failed_devices(
    session: aiohttp.ClientSession,
    job_type: str,
    job_id: str,
    fallback_context: dict,
    ctx: dict | None,
) -> list[str]:
    """Return the list of webex device IDs that failed in the bulk job.

    Reads the errors endpoint and pulls itemId for each failed row. If the
    errors endpoint itself can't be read (HTTP non-200 or network failure),
    returns ``[]`` and logs a WARNING. ``execute_bulk_op`` already treats
    an empty ``failed_ids`` list as a total failure, so this preserves the
    safe behavior. Fix #6.
    """
    try:
        items = await fetch_job_errors(session, job_type, job_id, ctx)
    except JobErrorFetchFailed:
        logger.warning(
            "Cannot fetch job errors for %s — treating partial bulk failure as total failure",
            job_id[:16],
        )
        return []
    return [i["itemId"] for i in items if i.get("itemId")]


async def _run_per_device_fallback(
    session: aiohttp.ClientSession,
    failed_webex_ids: list[str],
    fallback_context: dict,
    semaphore: asyncio.Semaphore,
) -> tuple[bool, str | None]:
    """Re-run the per-device handler for each failed device.

    Returns (all_ok, error_message). The handler is looked up in
    HANDLER_REGISTRY by fallback_context['fallback_handler_key']. Deps
    are augmented with the device's own canonical_id → webex_id so the
    handler can resolve the device. If the handler still returns no calls
    (e.g. because the settings dict is empty but present), a direct PUT
    to the device settings endpoint is issued using the record's data.
    """
    handler_key = fallback_context.get("fallback_handler_key")
    handler = HANDLER_REGISTRY.get(handler_key) if handler_key else None
    if handler is None:
        return False, f"No handler for fallback key {handler_key}"

    covered = {d["webex_id"]: d for d in fallback_context.get("covered_devices", [])}
    deps = fallback_context.get("deps", {})
    ctx = fallback_context.get("ctx", {})

    for wid in failed_webex_ids:
        record = covered.get(wid)
        if not record:
            return False, f"Failed device {wid} not in covered_devices"
        # Augment deps with the device's own webex_id so handler can resolve it.
        per_device_deps = {**deps, record["canonical_id"]: record["webex_id"]}
        calls = handler(record.get("data", {}), per_device_deps, ctx)
        if not calls:
            # Handler returned no-op. Issue a direct settings PUT using the
            # record's data (supports both "device_settings" and "settings" keys).
            data_body = record.get("data", {})
            settings = data_body.get("device_settings")
            if settings is None:
                settings = data_body.get("settings")
            if settings is None:
                continue  # truly nothing to apply → treat as success
            url = f"{BASE}/telephony/config/devices/{wid}/settings"
            calls = [("PUT", url, settings)]
        for method, url, body in calls:
            async with semaphore:
                async with session.request(method, url, json=body) as resp:
                    if resp.status >= 400:
                        text = await resp.text()
                        return False, f"{wid} fallback {resp.status}: {text[:200]}"
    return True, None


async def _try_find_existing(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    resource_type: str,
    data: dict,
    ctx: dict,
) -> str | None:
    """On 409, search for the existing resource and return its Webex ID."""
    from urllib.parse import urlencode
    search_url = None
    item_key = None

    if resource_type == "user":
        email = (data.get("emails") or [""])[0]
        if email:
            params = {"email": email}
            if ctx.get("orgId"):
                params["orgId"] = ctx["orgId"]
            search_url = f"{BASE}/people?{urlencode(params)}"
            item_key = "items"
    elif resource_type == "location":
        name = data.get("name")
        if name:
            params = {"name": name}
            if ctx.get("orgId"):
                params["orgId"] = ctx["orgId"]
            search_url = f"{BASE}/locations?{urlencode(params)}"
            item_key = "items"
    elif resource_type == "translation_pattern":
        name = data.get("name")
        if name:
            params = {"name": name, "max": "100"}
            if ctx.get("orgId"):
                params["orgId"] = ctx["orgId"]
            search_url = f"{BASE}/telephony/config/callRouting/translationPatterns?{urlencode(params)}"
            item_key = "translationPatterns"
    elif resource_type == "trunk":
        name = data.get("name")
        if name:
            params = {"name": name, "max": "100"}
            if ctx.get("orgId"):
                params["orgId"] = ctx["orgId"]
            search_url = f"{BASE}/telephony/config/premisePstn/trunks?{urlencode(params)}"
            item_key = "trunks"
    elif resource_type == "dial_plan":
        name = data.get("name")
        if name:
            params = {"name": name, "max": "100"}
            if ctx.get("orgId"):
                params["orgId"] = ctx["orgId"]
            search_url = f"{BASE}/telephony/config/premisePstn/dialPlans?{urlencode(params)}"
            item_key = "dialPlans"
    elif resource_type == "operating_mode":
        name = data.get("name")
        if name:
            params = {"name": name, "max": "100"}
            if ctx.get("orgId"):
                params["orgId"] = ctx["orgId"]
            search_url = f"{BASE}/telephony/config/operatingModes?{urlencode(params)}"
            item_key = "operatingModes"
    elif resource_type == "schedule":
        name = data.get("name")
        location_id = data.get("location_id") or data.get("locationId", "")
        if name and location_id:
            params = {"name": name, "max": "100"}
            if ctx.get("orgId"):
                params["orgId"] = ctx["orgId"]
            search_url = f"{BASE}/telephony/config/locations/{location_id}/schedules?{urlencode(params)}"
            item_key = "schedules"
    elif resource_type == "line_key_template":
        name = data.get("name")
        if name:
            params = {"name": name, "max": "100"}
            if ctx.get("orgId"):
                params["orgId"] = ctx["orgId"]
            search_url = f"{BASE}/telephony/config/devices/lineKeyTemplates?{urlencode(params)}"
            item_key = "lineKeyTemplates"
    elif resource_type in ("call_park", "pickup_group", "paging_group",
                           "hunt_group", "call_queue", "auto_attendant"):
        # Location-scoped features — need location_id from deps
        # These are harder to 409-recover because they need a location search.
        # Skip recovery — let cascade handle it on next run.
        pass

    # For types without search support, return None
    if not search_url:
        return None

    try:
        async with semaphore:
            async with session.get(search_url) as resp:
                if resp.status == 200:
                    body = await resp.json()
                    items = body.get(item_key, []) if isinstance(body, dict) else body
                    if items and len(items) > 0:
                        return items[0].get("id")
    except Exception:
        pass
    return None


def _build_fallback_context(op: dict, ctx: dict) -> dict | None:
    """Build fallback_context for a bulk op from its payload and resolved deps.

    Returns None if the op's payload lacks ``covered_canonical_ids`` or
    ``fallback_handler_key`` — e.g. for ``bulk_rebuild_phones`` which has
    no per-device fallback path.

    Fix #5: when a covered_cid has no resolved webex_id (because its upstream
    create op failed/skipped or hasn't run yet), the device cannot participate
    in either the bulk submit or the per-device fallback. We log a WARNING
    per-cid and surface the count via ``excluded_unresolved_count`` so callers
    (and the operator-facing summary log in ``execute_bulk_op``) can account
    for every device that was silently dropped from the fallback path.
    """
    data = op.get("data", {})
    covered_cids = data.get("covered_canonical_ids")
    fallback_key = data.get("fallback_handler_key")
    if not covered_cids or not fallback_key:
        return None

    resolved_deps = op.get("resolved_deps", {})
    store = ctx.get("store")

    covered_devices = []
    excluded: list[str] = []
    for cid in covered_cids:
        webex_id = resolved_deps.get(cid)
        if not webex_id:
            # Fix #5: surface the silent drop so it lands in the logs and in
            # the returned context, instead of a bare `continue`.
            logger.warning(
                "Bulk fallback: device %s not yet created, excluding from fallback",
                cid,
            )
            excluded.append(cid)
            continue
        device_data = {}
        if store:
            obj = store.get_object(cid)
            if obj:
                device_data = obj if isinstance(obj, dict) else obj
        covered_devices.append({
            "canonical_id": cid,
            "webex_id": webex_id,
            "data": device_data,
        })

    return {
        "fallback_handler_key": tuple(fallback_key),
        "covered_devices": covered_devices,
        "deps": resolved_deps,
        "ctx": ctx,
        "excluded_unresolved_count": len(excluded),
        "excluded_canonical_ids": excluded,
    }


async def run_batch_ops(
    session: aiohttp.ClientSession,
    tasks: list[dict],
    semaphore: asyncio.Semaphore,
    ctx: dict,
    poll_interval: float = 5,
    max_poll_time: float = 600,
) -> list[OpResult]:
    """Execute all tasks in one (batch, tier) group.

    Each task is ``{"op": {...}, "calls": [(method, url, body), ...]}``.
    Tasks whose op.resource_type is in ``SERIALIZED_RESOURCE_TYPES`` run
    sequentially; all others run concurrently via ``asyncio.gather``.
    Bulk ops dispatch to ``execute_bulk_op``; non-bulk ops use
    ``execute_single_op``.

    Results are returned in the same order as the input tasks list so
    that callers can zip(tasks, results) without misalignment.
    """
    from wxcli.migration.execute import SERIALIZED_RESOURCE_TYPES

    results: list[OpResult | None] = [None] * len(tasks)

    parallel_indexed: list[tuple[int, dict]] = []
    serial_indexed: list[tuple[int, dict]] = []
    for idx, t in enumerate(tasks):
        op = t["op"]
        if op["resource_type"] in SERIALIZED_RESOURCE_TYPES:
            serial_indexed.append((idx, t))
        else:
            parallel_indexed.append((idx, t))

    # Kick off parallel ops
    if parallel_indexed:
        parallel_coros = [
            execute_single_op(
                session,
                t["op"]["node_id"],
                t["calls"],
                semaphore,
                # Fix #18: require a returned id/code for create ops so a
                # silent "200 OK with empty body" cannot masquerade as a
                # successful resource creation. Fix #3: also gate
                # ``create_activation_code`` ops — convertible phones use
                # this op_type and fall back to the response's ``code``
                # field as the webex_id (see execute_single_op).
                require_webex_id=(
                    t["op"].get("op_type") in ("create", "create_activation_code")
                ),
            )
            for _, t in parallel_indexed
        ]
        parallel_results = await asyncio.gather(*parallel_coros, return_exceptions=True)
        for (idx, t), res in zip(parallel_indexed, parallel_results):
            if isinstance(res, Exception):
                results[idx] = OpResult(
                    node_id=t["op"]["node_id"], status=0, error=str(res), body={},
                )
            else:
                results[idx] = res

    # Then serial bulk ops, one at a time
    for idx, t in serial_indexed:
        op = t["op"]
        fallback_ctx = _build_fallback_context(op, ctx)
        try:
            res = await execute_bulk_op(
                session,
                node_id=op["node_id"],
                resource_type=op["resource_type"],
                calls=t["calls"],
                semaphore=semaphore,
                poll_interval=poll_interval,
                max_poll_time=max_poll_time,
                ctx=ctx,
                fallback_context=fallback_ctx,
            )
        except Exception as e:
            res = OpResult(node_id=op["node_id"], status=0, error=str(e), body={})
        results[idx] = res

    # At this point every slot should be filled; cast for the return type
    return [r for r in results if r is not None]  # type: ignore[misc]


async def execute_all_batches(
    store: MigrationStore,
    token: str,
    concurrency: int = 20,
    ctx: dict | None = None,
    on_progress: Any = None,
) -> dict[str, int]:
    """Execute all pending operations in batch order.

    Returns summary: {"completed": N, "failed": M, "skipped": K}
    """
    ctx = ctx or {}
    ctx.setdefault("store", store)
    summary = {"completed": 0, "failed": 0, "skipped": 0, "batches": 0}
    semaphore = asyncio.Semaphore(concurrency)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        while True:
            batch = get_next_batch(store)
            if not batch:
                break

            summary["batches"] += 1
            batch_name = batch[0]["batch"] or "org-wide"
            tier = batch[0]["tier"]
            logger.info("Batch %s / tier %d: %d operations",
                        batch_name, tier, len(batch))
            if on_progress:
                on_progress(f"Batch: {batch_name} / tier {tier} ({len(batch)} ops)")

            # Build tasks for this batch
            tasks = []
            for op in batch:
                handler = HANDLER_REGISTRY.get(
                    (op["resource_type"], op["op_type"])
                )
                if not handler:
                    update_op_status(store, op["node_id"], "failed",
                                     error_message=f"No handler for {op['resource_type']}:{op['op_type']}")
                    summary["failed"] += 1
                    continue

                calls = handler(op["data"], op["resolved_deps"], ctx)
                if isinstance(calls, SkippedResult):
                    # Handler declared a hard-prerequisite miss — record as
                    # 'skipped' so the report separates these from FAILED ops
                    # and cascades skip to dependents just like a failure.
                    update_op_status(
                        store, op["node_id"], "skipped",
                        error_message=calls.reason,
                    )
                    summary["skipped"] += 1
                    continue
                if not calls:
                    # No-op (e.g., empty workspace assign_number)
                    update_op_status(store, op["node_id"], "completed")
                    summary["completed"] += 1
                    continue

                tasks.append((op, calls))

            # Execute all ops in this batch — serialized bulk types run sequentially.
            if tasks:
                results = await run_batch_ops(
                    session, [{"op": op, "calls": calls} for op, calls in tasks],
                    semaphore=semaphore, ctx=ctx,
                )

                for (op, _calls), result in zip(tasks, results):
                    op_status = "failed"  # default

                    if isinstance(result, Exception):
                        update_op_status(store, op["node_id"], "failed",
                                         error_message=str(result))
                        summary["failed"] += 1
                    elif result.success:
                        update_op_status(store, op["node_id"], "completed",
                                         webex_id=result.webex_id)
                        summary["completed"] += 1
                        op_status = "completed"
                    elif result.status == 409:
                        # Auto-recover: search for existing resource
                        existing_id = await _try_find_existing(
                            session, semaphore,
                            op["resource_type"], op["data"], ctx,
                        )
                        if existing_id:
                            update_op_status(store, op["node_id"], "completed",
                                             webex_id=existing_id)
                            summary["completed"] += 1
                            op_status = "completed"
                            logger.info("409 auto-recovered %s -> %s",
                                        op["node_id"], existing_id)
                        else:
                            update_op_status(store, op["node_id"], "failed",
                                             error_message=result.error)
                            summary["failed"] += 1
                    else:
                        update_op_status(store, op["node_id"], "failed",
                                         error_message=result.error)
                        summary["failed"] += 1

                    if on_progress:
                        on_progress(f"  {op['node_id']}: {op_status}")

    return summary
