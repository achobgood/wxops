"""Unit tests for the async job polling loop in engine.py."""

from __future__ import annotations

import pytest
from aioresponses import aioresponses

from wxcli.migration.execute.engine import BASE, poll_job_until_complete


@pytest.fixture
def poll_url():
    return f"{BASE}/telephony/config/jobs/devices/callDeviceSettings/JOB_ABC"


@pytest.mark.asyncio
async def test_poll_returns_on_completed(poll_url):
    with aioresponses() as m:
        m.get(poll_url, status=200, payload={
            "latestExecutionStatus": "STARTED",
            "latestExecutionExitCode": "UNKNOWN",
            "percentageComplete": 10,
        })
        m.get(poll_url, status=200, payload={
            "latestExecutionStatus": "COMPLETED",
            "latestExecutionExitCode": "COMPLETED",
            "percentageComplete": 100,
            "updatedCount": 50,
        })
        import aiohttp
        async with aiohttp.ClientSession() as session:
            result = await poll_job_until_complete(
                session, "callDeviceSettings", "JOB_ABC",
                poll_interval=0, max_poll_time=5, ctx={},
            )
    assert result["latestExecutionExitCode"] == "COMPLETED"
    assert result["updatedCount"] == 50


@pytest.mark.asyncio
async def test_poll_returns_on_failed(poll_url):
    with aioresponses() as m:
        m.get(poll_url, status=200, payload={
            "latestExecutionStatus": "FAILED",
            "latestExecutionExitCode": "FAILED",
            "percentageComplete": 30,
        })
        import aiohttp
        async with aiohttp.ClientSession() as session:
            result = await poll_job_until_complete(
                session, "callDeviceSettings", "JOB_ABC",
                poll_interval=0, max_poll_time=5, ctx={},
            )
    assert result["latestExecutionExitCode"] == "FAILED"


@pytest.mark.asyncio
async def test_poll_timeout(poll_url):
    with aioresponses() as m:
        for _ in range(20):
            m.get(poll_url, status=200, payload={
                "latestExecutionStatus": "STARTED",
                "latestExecutionExitCode": "UNKNOWN",
                "percentageComplete": 20,
            })
        import aiohttp
        async with aiohttp.ClientSession() as session:
            with pytest.raises(TimeoutError):
                await poll_job_until_complete(
                    session, "callDeviceSettings", "JOB_ABC",
                    poll_interval=0, max_poll_time=0, ctx={},
                )


@pytest.mark.asyncio
async def test_poll_injects_orgid_in_url(poll_url):
    expected = f"{poll_url}?orgId=org-xyz"
    with aioresponses() as m:
        m.get(expected, status=200, payload={
            "latestExecutionExitCode": "COMPLETED",
            "percentageComplete": 100,
        })
        import aiohttp
        async with aiohttp.ClientSession() as session:
            result = await poll_job_until_complete(
                session, "callDeviceSettings", "JOB_ABC",
                poll_interval=0, max_poll_time=5, ctx={"orgId": "org-xyz"},
            )
    assert result["latestExecutionExitCode"] == "COMPLETED"


@pytest.mark.asyncio
async def test_fetch_job_errors_parses_items():
    from wxcli.migration.execute.engine import fetch_job_errors, BASE
    import aiohttp

    url = f"{BASE}/telephony/config/jobs/devices/callDeviceSettings/JOB_XYZ/errors"
    with aioresponses() as m:
        m.get(url, status=200, payload={
            "items": [
                {"itemId": "device-1", "trackingId": "t1",
                 "error": {"key": "E100", "message": ["boom"]}},
                {"itemId": "device-2", "trackingId": "t2",
                 "error": {"key": "E200", "message": ["bam"]}},
            ]
        })
        async with aiohttp.ClientSession() as session:
            errors = await fetch_job_errors(
                session, "callDeviceSettings", "JOB_XYZ", ctx={},
            )
    assert len(errors) == 2
    assert errors[0]["itemId"] == "device-1"
    assert errors[1]["error"]["key"] == "E200"


@pytest.mark.asyncio
async def test_fetch_job_errors_empty_on_none():
    from wxcli.migration.execute.engine import fetch_job_errors, BASE
    import aiohttp

    url = f"{BASE}/telephony/config/jobs/devices/callDeviceSettings/JOB_XYZ/errors"
    with aioresponses() as m:
        m.get(url, status=200, payload={"items": []})
        async with aiohttp.ClientSession() as session:
            errors = await fetch_job_errors(
                session, "callDeviceSettings", "JOB_XYZ", ctx={},
            )
    assert errors == []


@pytest.mark.asyncio
async def test_execute_bulk_op_submits_then_polls():
    """execute_bulk_op POSTs the submit URL, captures job id, then polls."""
    from wxcli.migration.execute.engine import execute_bulk_op, BASE
    import aiohttp
    import asyncio

    submit_url = f"{BASE}/telephony/config/jobs/devices/callDeviceSettings"
    # Realistic 30+ char URN-shaped id (Webex returns base64-encoded URNs).
    long_id = "Y2lzY29zcGFyazovL3VzL0pPQi9YWVpfMTExMQ"
    poll_url = f"{submit_url}/{long_id}"
    calls = [("POST", submit_url, {"locationId": "LOC"})]

    with aioresponses() as m:
        m.post(submit_url, status=202, payload={
            "id": long_id,
            "latestExecutionStatus": "STARTED",
            "percentageComplete": 5,
        })
        m.get(poll_url, status=200, payload={
            "latestExecutionExitCode": "COMPLETED",
            "percentageComplete": 100,
            "updatedCount": 100,
        })
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
            )

    assert result.success
    assert result.status == 200
    assert result.webex_id == long_id
    assert result.body.get("updatedCount") == 100


@pytest.mark.asyncio
async def test_execute_bulk_op_failed_exit_marks_failed():
    from wxcli.migration.execute.engine import execute_bulk_op, BASE
    import aiohttp
    import asyncio

    submit_url = f"{BASE}/telephony/config/jobs/devices/rebuildPhones"
    # Realistic 30+ char URN-shaped id.
    long_id = "Y2lzY29zcGFyazovL3VzL0pPQi9SRUJfMzMzMw"
    poll_url = f"{submit_url}/{long_id}"
    calls = [("POST", submit_url, {"locationId": "LOC"})]

    with aioresponses() as m:
        m.post(submit_url, status=202, payload={"id": long_id})
        m.get(poll_url, status=200, payload={
            "latestExecutionExitCode": "FAILED",
            "percentageComplete": 30,
        })
        async with aiohttp.ClientSession() as session:
            sem = asyncio.Semaphore(5)
            result = await execute_bulk_op(
                session,
                node_id="bulk_rebuild_phones:loc-1:submit",
                resource_type="bulk_rebuild_phones",
                calls=calls,
                semaphore=sem,
                poll_interval=0,
                max_poll_time=5,
                ctx={},
            )

    assert not result.success
    assert result.error and "FAILED" in result.error
