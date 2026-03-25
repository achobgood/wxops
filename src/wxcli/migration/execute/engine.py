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

from wxcli.migration.execute.handlers import HANDLER_REGISTRY
from wxcli.migration.execute.runtime import get_next_batch, update_op_status
from wxcli.migration.store import MigrationStore

logger = logging.getLogger(__name__)

BASE = "https://webexapis.com/v1"
MAX_RETRIES = 5


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
) -> OpResult:
    """Execute one operation's API call(s) with rate limiting and retry.

    For multi-call operations (e.g., user:configure_settings), calls are
    executed sequentially. The operation fails if any sub-call fails.
    The webex_id comes from the first call's response (the create).
    """
    webex_id = None
    last_body = {}

    for method, url, body in calls:
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

                # Success — extract ID from first call
                if webex_id is None and isinstance(resp_body, dict):
                    webex_id = resp_body.get("id")
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

    return OpResult(
        node_id=node_id, status=200,
        webex_id=webex_id, body=last_body,
    )


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

    # For other types, we can't easily search — return None
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
                if not calls:
                    # No-op (e.g., empty workspace assign_number)
                    update_op_status(store, op["node_id"], "completed")
                    summary["completed"] += 1
                    continue

                tasks.append((op, calls))

            # Execute all ops in this batch concurrently
            if tasks:
                results = await asyncio.gather(
                    *[execute_single_op(session, op["node_id"], calls, semaphore)
                      for op, calls in tasks],
                    return_exceptions=True,
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
