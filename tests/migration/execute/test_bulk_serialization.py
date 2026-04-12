"""Verify the batch loop runs SERIALIZED_RESOURCE_TYPES ops sequentially."""

from __future__ import annotations

import asyncio

import pytest
from aioresponses import aioresponses

from wxcli.migration.execute import SERIALIZED_RESOURCE_TYPES
from wxcli.migration.execute.engine import BASE


def test_bulk_types_marked_serialized():
    assert "bulk_device_settings" in SERIALIZED_RESOURCE_TYPES
    assert "bulk_dynamic_settings" in SERIALIZED_RESOURCE_TYPES
    assert "bulk_rebuild_phones" in SERIALIZED_RESOURCE_TYPES
    assert "bulk_line_key_template" in SERIALIZED_RESOURCE_TYPES


@pytest.mark.asyncio
async def test_serialized_ops_do_not_overlap(monkeypatch):
    """Two bulk_device_settings ops in the same batch must run one after
    the other — never concurrently.

    Uses a shared counter that increments on entry, decrements on exit.
    If the counter ever exceeds 1, the test fails.
    """
    from wxcli.migration.execute.engine import run_batch_ops

    active = 0
    peak = [0]
    order: list[str] = []

    async def fake_execute_bulk_op(session, node_id, resource_type, calls,
                                     semaphore, poll_interval, max_poll_time, ctx):
        nonlocal active
        active += 1
        peak[0] = max(peak[0], active)
        order.append(f"+{node_id}")
        await asyncio.sleep(0.02)
        active -= 1
        order.append(f"-{node_id}")
        from wxcli.migration.execute.engine import OpResult
        return OpResult(node_id=node_id, status=200, webex_id="JOB", body={})

    monkeypatch.setattr(
        "wxcli.migration.execute.engine.execute_bulk_op", fake_execute_bulk_op,
    )

    tasks = [
        {
            "op": {"node_id": "bulk_device_settings:loc-1:submit",
                   "resource_type": "bulk_device_settings", "op_type": "submit"},
            "calls": [("POST", f"{BASE}/telephony/config/jobs/devices/callDeviceSettings", {})],
        },
        {
            "op": {"node_id": "bulk_device_settings:loc-2:submit",
                   "resource_type": "bulk_device_settings", "op_type": "submit"},
            "calls": [("POST", f"{BASE}/telephony/config/jobs/devices/callDeviceSettings", {})],
        },
    ]

    import aiohttp
    async with aiohttp.ClientSession() as session:
        sem = asyncio.Semaphore(5)
        results = await run_batch_ops(
            session, tasks, semaphore=sem, ctx={},
            poll_interval=0, max_poll_time=5,
        )

    assert peak[0] == 1, f"Bulk ops ran concurrently, peak={peak[0]}, order={order}"
    assert len(results) == 2
    assert all(r.success for r in results)


@pytest.mark.asyncio
async def test_run_batch_ops_preserves_input_order(monkeypatch):
    """With mixed parallel + serial tasks, results must align with input
    order so callers can zip(tasks, results) safely."""
    from wxcli.migration.execute.engine import run_batch_ops, OpResult

    async def fake_single(session, node_id, calls, semaphore):
        return OpResult(node_id=node_id, status=200, webex_id=f"wid-{node_id}", body={})

    async def fake_bulk(session, node_id, resource_type, calls, semaphore,
                        poll_interval, max_poll_time, ctx):
        return OpResult(node_id=node_id, status=200, webex_id=f"wid-{node_id}", body={})

    monkeypatch.setattr("wxcli.migration.execute.engine.execute_single_op", fake_single)
    monkeypatch.setattr("wxcli.migration.execute.engine.execute_bulk_op", fake_bulk)

    tasks = [
        {"op": {"node_id": "user:u1:create", "resource_type": "user", "op_type": "create"},
         "calls": [("POST", "http://x", {})]},
        {"op": {"node_id": "bulk_device_settings:loc-1:submit",
                "resource_type": "bulk_device_settings", "op_type": "submit"},
         "calls": [("POST", "http://x", {})]},
        {"op": {"node_id": "device:d1:create", "resource_type": "device", "op_type": "create"},
         "calls": [("POST", "http://x", {})]},
        {"op": {"node_id": "bulk_rebuild_phones:loc-1:submit",
                "resource_type": "bulk_rebuild_phones", "op_type": "submit"},
         "calls": [("POST", "http://x", {})]},
    ]

    import aiohttp
    async with aiohttp.ClientSession() as session:
        sem = asyncio.Semaphore(5)
        results = await run_batch_ops(
            session, tasks, semaphore=sem, ctx={},
            poll_interval=0, max_poll_time=5,
        )

    assert len(results) == len(tasks)
    for task, result in zip(tasks, results):
        assert result.node_id == task["op"]["node_id"], (
            f"mismatch: task {task['op']['node_id']} → result {result.node_id}"
        )
