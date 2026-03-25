"""Tests for the async execution engine.

Uses aiohttp test utilities to mock HTTP responses.
"""

import asyncio
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import networkx as nx

from wxcli.migration.execute import DependencyType
from wxcli.migration.execute.batch import save_plan_to_store
from wxcli.migration.execute.engine import (
    execute_all_batches,
    execute_single_op,
    OpResult,
)
from wxcli.migration.execute.runtime import (
    get_execution_progress,
    update_op_status,
)
from wxcli.migration.models import (
    CanonicalLocation,
    CanonicalUser,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore


def _prov():
    return Provenance(
        source_system="cucm", source_id="pk", source_name="test",
        extracted_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def store(tmp_path):
    s = MigrationStore(tmp_path / "test.db")
    yield s
    s.close()


def _setup_simple_plan(store):
    """Location -> user plan."""
    loc = CanonicalLocation(
        canonical_id="location:hq", provenance=_prov(),
        name="HQ", time_zone="America/New_York",
        preferred_language="en_US", announcement_language="en_us",
        status=MigrationStatus.ANALYZED,
    )
    user = CanonicalUser(
        canonical_id="user:alice", provenance=_prov(),
        emails=["alice@acme.com"], first_name="Alice", last_name="Smith",
        location_id="location:hq", extension="1001",
        status=MigrationStatus.ANALYZED,
    )
    store.upsert_object(loc)
    store.upsert_object(user)

    G = nx.DiGraph()
    G.add_node("location:hq:create", canonical_id="location:hq",
               op_type="create", resource_type="location",
               tier=0, batch="org-wide", api_calls=1,
               description="Create location HQ")
    G.add_node("user:alice:create", canonical_id="user:alice",
               op_type="create", resource_type="user",
               tier=2, batch="location:hq", api_calls=1,
               description="Create user alice@acme.com")
    G.add_edge("location:hq:create", "user:alice:create",
               type=DependencyType.REQUIRES)
    save_plan_to_store(G, store)


class TestOpResult:
    def test_success(self):
        r = OpResult(node_id="loc:hq:create", status=200,
                     webex_id="wx-123", body={"id": "wx-123"})
        assert r.success
        assert r.webex_id == "wx-123"

    def test_failure(self):
        r = OpResult(node_id="loc:hq:create", status=400,
                     error="Bad Request", body={})
        assert not r.success


class _MockResponse:
    """Mock aiohttp response that supports async context manager protocol.

    aiohttp's session.request() returns a _RequestContextManager (sync return,
    async context manager). So mock request() must be a sync method returning
    an object with __aenter__/__aexit__.
    """
    def __init__(self, status, body, headers=None):
        self.status = status
        self._body = body
        self.headers = headers or {}
    async def json(self):
        return self._body
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        pass


class TestExecuteSingleOp:
    @pytest.mark.asyncio
    async def test_success_extracts_id(self):
        mock_resp = _MockResponse(200, {"id": "wx-new-123", "name": "HQ"})

        mock_session = MagicMock()
        mock_session.request = MagicMock(return_value=mock_resp)

        sem = asyncio.Semaphore(10)
        result = await execute_single_op(
            session=mock_session,
            node_id="location:hq:create",
            calls=[("POST", "https://webexapis.com/v1/locations", {"name": "HQ"})],
            semaphore=sem,
        )
        assert result.success
        assert result.webex_id == "wx-new-123"

    @pytest.mark.asyncio
    async def test_429_retries(self):
        call_count = 0

        def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _MockResponse(429, {}, {"Retry-After": "0"})
            return _MockResponse(200, {"id": "wx-123"})

        mock_session = MagicMock()
        mock_session.request = mock_request
        sem = asyncio.Semaphore(10)
        result = await execute_single_op(
            session=mock_session,
            node_id="loc:hq:create",
            calls=[("POST", "https://webexapis.com/v1/locations", {"name": "HQ"})],
            semaphore=sem,
        )
        assert result.success
        assert call_count == 2


class TestResetInProgress:
    def test_resets_to_pending(self, store):
        """Any in_progress ops should be reset to pending on startup."""
        _setup_simple_plan(store)
        update_op_status(store, "location:hq:create", "in_progress")

        row = store.conn.execute(
            "SELECT status FROM plan_operations WHERE node_id = ?",
            ("location:hq:create",),
        ).fetchone()
        assert row["status"] == "in_progress"

        from wxcli.migration.execute.engine import reset_in_progress
        reset_in_progress(store)

        row = store.conn.execute(
            "SELECT status FROM plan_operations WHERE node_id = ?",
            ("location:hq:create",),
        ).fetchone()
        assert row["status"] == "pending"


class TestExecuteAllBatches:
    @pytest.mark.asyncio
    async def test_full_plan_completes(self, store):
        """Integration: execute a simple plan with mocked HTTP, verify all ops complete."""
        _setup_simple_plan(store)

        # Mock aiohttp to return success for all requests
        call_log = []

        class MockSession:
            def request(self, method, url, **kwargs):
                call_log.append((method, url))
                rid = f"wx-{len(call_log)}"
                return _MockResponse(200, {"id": rid, "name": "test"})
            def get(self, url, **kwargs):
                return _MockResponse(200, {"id": "wx-search", "items": []})
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass

        # Patch aiohttp.ClientSession to return our mock
        import aiohttp
        original_session = aiohttp.ClientSession
        aiohttp.ClientSession = lambda **kwargs: MockSession()

        try:
            summary = await execute_all_batches(
                store=store,
                token="fake-token",
                concurrency=5,
                ctx={"CALLING_LICENSE_ID": "wx-lic-123"},
            )
            assert summary["completed"] == 2  # location + user
            assert summary["failed"] == 0

            # Verify DB state
            progress = get_execution_progress(store)
            assert progress["completed"] == 2
            assert progress["pending"] == 0
        finally:
            aiohttp.ClientSession = original_session
