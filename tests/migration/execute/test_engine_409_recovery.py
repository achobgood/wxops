"""Tests for _try_find_existing 409 auto-recovery."""

import asyncio
import pytest
from unittest.mock import MagicMock

from wxcli.migration.execute.engine import _try_find_existing


class FakeResponse:
    def __init__(self, status, body):
        self.status = status
        self._body = body

    async def json(self):
        return self._body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


def _run(coro):
    """Run an async coroutine synchronously."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestTryFindExistingOperatingMode:
    def test_finds_by_name(self):
        session = MagicMock()
        session.get = MagicMock(return_value=FakeResponse(200, {
            "operatingModes": [{"id": "om-123", "name": "Business Hours"}]
        }))
        semaphore = asyncio.Semaphore(1)
        result = _run(_try_find_existing(session, semaphore, "operating_mode",
                                         {"name": "Business Hours"}, {}))
        assert result == "om-123"
        call_url = session.get.call_args[0][0]
        assert "operatingModes" in call_url
        assert "Business" in call_url

    def test_returns_none_when_no_name(self):
        session = MagicMock()
        semaphore = asyncio.Semaphore(1)
        result = _run(_try_find_existing(session, semaphore, "operating_mode", {}, {}))
        assert result is None

    def test_includes_org_id(self):
        session = MagicMock()
        session.get = MagicMock(return_value=FakeResponse(200, {
            "operatingModes": [{"id": "om-456", "name": "After Hours"}]
        }))
        semaphore = asyncio.Semaphore(1)
        result = _run(_try_find_existing(session, semaphore, "operating_mode",
                                         {"name": "After Hours"}, {"orgId": "org-999"}))
        assert result == "om-456"
        call_url = session.get.call_args[0][0]
        assert "orgId=org-999" in call_url

    def test_returns_none_on_empty_results(self):
        session = MagicMock()
        session.get = MagicMock(return_value=FakeResponse(200, {"operatingModes": []}))
        semaphore = asyncio.Semaphore(1)
        result = _run(_try_find_existing(session, semaphore, "operating_mode",
                                         {"name": "Nonexistent"}, {}))
        assert result is None


class TestTryFindExistingSchedule:
    def test_finds_by_name(self):
        session = MagicMock()
        session.get = MagicMock(return_value=FakeResponse(200, {
            "schedules": [{"id": "sched-1", "name": "Holiday Schedule", "type": "holidays"}]
        }))
        semaphore = asyncio.Semaphore(1)
        result = _run(_try_find_existing(session, semaphore, "schedule",
                                         {"name": "Holiday Schedule", "locationId": "loc-1"},
                                         {"orgId": "org-1"}))
        assert result == "sched-1"
        call_url = session.get.call_args[0][0]
        assert "loc-1" in call_url
        assert "schedules" in call_url

    def test_returns_none_when_no_name(self):
        session = MagicMock()
        semaphore = asyncio.Semaphore(1)
        result = _run(_try_find_existing(session, semaphore, "schedule",
                                         {"locationId": "loc-1"}, {}))
        assert result is None

    def test_returns_none_when_no_location_id(self):
        session = MagicMock()
        semaphore = asyncio.Semaphore(1)
        result = _run(_try_find_existing(session, semaphore, "schedule",
                                         {"name": "Holiday Schedule"}, {}))
        assert result is None

    def test_returns_none_on_empty_results(self):
        session = MagicMock()
        session.get = MagicMock(return_value=FakeResponse(200, {"schedules": []}))
        semaphore = asyncio.Semaphore(1)
        result = _run(_try_find_existing(session, semaphore, "schedule",
                                         {"name": "Nonexistent", "locationId": "loc-1"}, {}))
        assert result is None

    def test_includes_org_id(self):
        session = MagicMock()
        session.get = MagicMock(return_value=FakeResponse(200, {
            "schedules": [{"id": "sched-2", "name": "Weekend", "type": "businessHours"}]
        }))
        semaphore = asyncio.Semaphore(1)
        result = _run(_try_find_existing(session, semaphore, "schedule",
                                         {"name": "Weekend", "locationId": "loc-5"},
                                         {"orgId": "org-42"}))
        assert result == "sched-2"
        call_url = session.get.call_args[0][0]
        assert "orgId=org-42" in call_url
        assert "loc-5" in call_url
