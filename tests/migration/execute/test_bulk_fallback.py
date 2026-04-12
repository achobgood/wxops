"""Tests for the in-engine partial-failure fallback path."""

from __future__ import annotations

import asyncio

import pytest
from aioresponses import aioresponses

from wxcli.migration.execute.engine import BASE, execute_bulk_op


@pytest.mark.asyncio
async def test_all_success_no_fallback():
    submit_url = f"{BASE}/telephony/config/jobs/devices/callDeviceSettings"
    poll_url = f"{submit_url}/JOB_ALL_OK"
    calls = [("POST", submit_url, {"locationId": "LOC"})]

    covered = [
        {"canonical_id": f"device:d{i}",
         "webex_id": f"DEV{i}", "data": {}} for i in range(10)
    ]
    fallback_ctx = {
        "fallback_handler_key": ("device", "configure_settings"),
        "covered_devices": covered,
        "deps": {},
    }

    with aioresponses() as m:
        m.post(submit_url, status=202, payload={"id": "JOB_ALL_OK"})
        m.get(poll_url, status=200, payload={
            "latestExecutionExitCode": "COMPLETED",
            "percentageComplete": 100,
            "updatedCount": 10,
        })
        import aiohttp
        async with aiohttp.ClientSession() as session:
            sem = asyncio.Semaphore(5)
            result = await execute_bulk_op(
                session,
                node_id="bulk_device_settings:loc-1:submit",
                resource_type="bulk_device_settings",
                calls=calls,
                semaphore=sem,
                poll_interval=0,
                max_poll_time=5,
                ctx={},
                fallback_context=fallback_ctx,
            )

    assert result.success


@pytest.mark.asyncio
async def test_partial_failure_runs_per_device_fallback():
    submit_url = f"{BASE}/telephony/config/jobs/devices/callDeviceSettings"
    poll_url = f"{submit_url}/JOB_PARTIAL"
    errors_url = f"{poll_url}/errors"
    calls = [("POST", submit_url, {"locationId": "LOC"})]

    covered = [
        {"canonical_id": f"device:d{i}",
         "webex_id": f"DEV{i}",
         "data": {"id": f"DEV{i}", "settings": {}}}
        for i in range(10)
    ]
    fallback_ctx = {
        "fallback_handler_key": ("device", "configure_settings"),
        "covered_devices": covered,
        "deps": {},
    }

    with aioresponses() as m:
        m.post(submit_url, status=202, payload={"id": "JOB_PARTIAL"})
        m.get(poll_url, status=200, payload={
            "latestExecutionExitCode": "COMPLETED",
            "percentageComplete": 100,
            "updatedCount": 8,
        })
        m.get(errors_url, status=200, payload={
            "items": [
                {"itemId": "DEV8", "trackingId": "t", "error": {"key": "E1"}},
                {"itemId": "DEV9", "trackingId": "t", "error": {"key": "E2"}},
            ]
        })
        # Per-device handler for configure_settings issues a PUT per device.
        for wid in ("DEV8", "DEV9"):
            put_url = f"{BASE}/telephony/config/devices/{wid}/settings"
            m.put(put_url, status=204)

        import aiohttp
        async with aiohttp.ClientSession() as session:
            sem = asyncio.Semaphore(5)
            result = await execute_bulk_op(
                session,
                node_id="bulk_device_settings:loc-1:submit",
                resource_type="bulk_device_settings",
                calls=calls,
                semaphore=sem,
                poll_interval=0,
                max_poll_time=5,
                ctx={},
                fallback_context=fallback_ctx,
            )

    assert result.success, result.error


@pytest.mark.asyncio
async def test_partial_failure_fallback_itself_fails():
    submit_url = f"{BASE}/telephony/config/jobs/devices/callDeviceSettings"
    poll_url = f"{submit_url}/JOB_BAD"
    errors_url = f"{poll_url}/errors"
    calls = [("POST", submit_url, {"locationId": "LOC"})]

    covered = [
        {"canonical_id": "device:d1",
         "webex_id": "DEV1", "data": {"id": "DEV1", "settings": {}}},
    ]
    fallback_ctx = {
        "fallback_handler_key": ("device", "configure_settings"),
        "covered_devices": covered,
        "deps": {},
    }

    with aioresponses() as m:
        m.post(submit_url, status=202, payload={"id": "JOB_BAD"})
        m.get(poll_url, status=200, payload={
            "latestExecutionExitCode": "COMPLETED",
            "percentageComplete": 100,
            "updatedCount": 0,
        })
        m.get(errors_url, status=200, payload={
            "items": [{"itemId": "DEV1", "error": {"key": "E"}}]
        })
        m.put(f"{BASE}/telephony/config/devices/DEV1/settings",
              status=400, payload={"message": "boom"})

        import aiohttp
        async with aiohttp.ClientSession() as session:
            sem = asyncio.Semaphore(5)
            result = await execute_bulk_op(
                session,
                node_id="bulk_device_settings:loc-1:submit",
                resource_type="bulk_device_settings",
                calls=calls,
                semaphore=sem,
                poll_interval=0,
                max_poll_time=5,
                ctx={},
                fallback_context=fallback_ctx,
            )

    assert not result.success
    assert "fallback" in (result.error or "").lower()
