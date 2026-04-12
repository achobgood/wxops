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
