"""Wave 1 of silent-failure-hardening.

Covers the Wave 1 foundation primitives:

* ``SkippedResult`` sentinel + ``skipped()`` helper in ``handlers.py``
* Engine integration — a handler returning a ``SkippedResult`` causes the op
  to land in status='skipped' with the reason surfaced in ``error_message``
* ``OpStatus`` enum values match the existing SQL string literals
* engine.py fix #6 — ``fetch_job_errors`` now raises ``JobErrorFetchFailed``
  on non-200 / network error (instead of silently returning ``[]``)
* engine.py fix #19 — 0-update bulk jobs with no ``fallback_context`` are
  now a hard failure instead of silently COMPLETED
* engine.py fix #4 — partial-update jobs where the errors endpoint returns
  an INCOMPLETE list still surface as FAILED, not COMPLETED, because some
  devices were never attempted
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import MagicMock

import networkx as nx
import pytest
from aioresponses import aioresponses

from wxcli.migration.execute import DependencyType
from wxcli.migration.execute.batch import save_plan_to_store
from wxcli.migration.execute.engine import (
    BASE,
    JobErrorFetchFailed,
    execute_all_batches,
    execute_bulk_op,
    fetch_job_errors,
)
from wxcli.migration.execute.handlers import (
    HANDLER_REGISTRY,
    HandlerResult,
    SkippedResult,
    skipped,
)
from wxcli.migration.models import (
    CanonicalLocation,
    MigrationStatus,
    OpStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _prov() -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id="pk",
        source_name="test",
        extracted_at=datetime.now(timezone.utc),
    )


class _MockResponse:
    """Async-context-manager wrapper matching the existing test_engine.py style."""

    def __init__(self, status: int, body: dict, headers: dict | None = None):
        self.status = status
        self._body = body
        self.headers = headers or {}

    async def json(self):
        return self._body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


# ---------------------------------------------------------------------------
# Primitives: SkippedResult + skipped()
# ---------------------------------------------------------------------------

class TestSkippedResultSentinel:
    def test_sentinel_imports_from_handlers(self):
        """SkippedResult and skipped() are part of the public handlers surface."""
        # If either import failed the module would have raised at collection time.
        assert SkippedResult is not None
        assert callable(skipped)

    def test_skipped_helper_builds_sentinel_with_reason(self):
        s = skipped("upstream user never resolved")
        assert isinstance(s, SkippedResult)
        assert s.reason == "upstream user never resolved"

    def test_sentinel_is_frozen_dataclass(self):
        """Sentinel should be immutable so handlers can't mutate reason."""
        s = skipped("x")
        with pytest.raises(Exception):
            s.reason = "y"  # type: ignore[misc]

    def test_handler_result_union_accepts_both_shapes(self):
        """HandlerResult alias should type-check both a list and a SkippedResult.

        Runtime-only smoke test — we assert each value is valid per the union
        (by construction), not that mypy accepts them.
        """
        list_shape: HandlerResult = []
        sentinel_shape: HandlerResult = skipped("test")
        assert list_shape == []
        assert isinstance(sentinel_shape, SkippedResult)


# ---------------------------------------------------------------------------
# OpStatus enum — must match the raw string literals already in use
# ---------------------------------------------------------------------------

class TestOpStatusEnum:
    """OpStatus.value strings must match the literals baked into SQL / runtime."""

    def test_pending(self):
        assert OpStatus.PENDING.value == "pending"

    def test_in_progress(self):
        assert OpStatus.IN_PROGRESS.value == "in_progress"

    def test_completed(self):
        assert OpStatus.COMPLETED.value == "completed"

    def test_skipped(self):
        assert OpStatus.SKIPPED.value == "skipped"

    def test_failed(self):
        assert OpStatus.FAILED.value == "failed"


# ---------------------------------------------------------------------------
# Engine integration: SkippedResult -> 'skipped' status
# ---------------------------------------------------------------------------

@pytest.fixture
def store(tmp_path):
    s = MigrationStore(tmp_path / "wave1.db")
    yield s
    s.close()


def _setup_single_location_plan(store: MigrationStore) -> None:
    """One tier-0 location:create op — simplest possible plan."""
    loc = CanonicalLocation(
        canonical_id="location:hq",
        provenance=_prov(),
        name="HQ",
        time_zone="America/New_York",
        preferred_language="en_US",
        announcement_language="en_us",
        status=MigrationStatus.ANALYZED,
    )
    store.upsert_object(loc)

    g = nx.DiGraph()
    g.add_node(
        "location:hq:create",
        canonical_id="location:hq",
        op_type="create",
        resource_type="location",
        tier=0,
        batch="org-wide",
        api_calls=1,
        description="Create location HQ",
    )
    save_plan_to_store(g, store)


class TestEngineSkippedResultIntegration:
    @pytest.mark.asyncio
    async def test_handler_returning_skipped_marks_op_skipped(self, store, monkeypatch):
        """When a handler returns a SkippedResult the engine must:

        * Record status='skipped' on the op
        * Persist the reason into error_message
        * Increment summary['skipped'] (not summary['completed'])
        * NOT issue any HTTP request
        """
        _setup_single_location_plan(store)

        # Swap the real location:create handler for a stub that declares a
        # missing dependency. We restore via monkeypatch so other tests see
        # the real registry.
        skip_reason = "location has no webex_id resolved from deps"
        monkeypatch.setitem(
            HANDLER_REGISTRY,
            ("location", "create"),
            lambda data, deps, ctx: skipped(skip_reason),
        )

        http_calls: list[tuple[str, str]] = []

        class MockSession:
            def request(self, method, url, **kwargs):
                http_calls.append((method, url))
                return _MockResponse(200, {"id": "wx-should-not-be-hit"})

            def get(self, url, **kwargs):
                http_calls.append(("GET", url))
                return _MockResponse(200, {"items": []})

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        import aiohttp

        original = aiohttp.ClientSession
        aiohttp.ClientSession = lambda **kwargs: MockSession()  # type: ignore[assignment]
        try:
            summary = await execute_all_batches(
                store=store, token="tok", concurrency=2, ctx={},
            )
        finally:
            aiohttp.ClientSession = original  # type: ignore[assignment]

        assert summary["skipped"] == 1
        assert summary["completed"] == 0
        assert summary["failed"] == 0
        # No HTTP ever issued for a skipped op.
        assert http_calls == []

        row = store.conn.execute(
            "SELECT status, error_message FROM plan_operations WHERE node_id = ?",
            ("location:hq:create",),
        ).fetchone()
        assert row["status"] == OpStatus.SKIPPED.value
        assert row["error_message"] == skip_reason

    @pytest.mark.asyncio
    async def test_empty_list_still_marked_completed(self, store, monkeypatch):
        """Sanity check: bare ``return []`` still means no-op completed.

        Wave 1 must be strictly additive — the engine's existing contract
        for ``[]`` (mark completed without an API call) must not regress.
        """
        _setup_single_location_plan(store)

        monkeypatch.setitem(
            HANDLER_REGISTRY,
            ("location", "create"),
            lambda data, deps, ctx: [],
        )

        class MockSession:
            def request(self, method, url, **kwargs):
                raise AssertionError(f"Unexpected HTTP {method} {url}")

            def get(self, url, **kwargs):
                raise AssertionError(f"Unexpected GET {url}")

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        import aiohttp

        original = aiohttp.ClientSession
        aiohttp.ClientSession = lambda **kwargs: MockSession()  # type: ignore[assignment]
        try:
            summary = await execute_all_batches(
                store=store, token="tok", concurrency=2, ctx={},
            )
        finally:
            aiohttp.ClientSession = original  # type: ignore[assignment]

        assert summary["completed"] == 1
        assert summary["skipped"] == 0

        row = store.conn.execute(
            "SELECT status FROM plan_operations WHERE node_id = ?",
            ("location:hq:create",),
        ).fetchone()
        assert row["status"] == OpStatus.COMPLETED.value


# ---------------------------------------------------------------------------
# Fix #6 — fetch_job_errors raises JobErrorFetchFailed instead of returning []
# ---------------------------------------------------------------------------

class TestFetchJobErrorsRaises:
    @pytest.mark.asyncio
    async def test_500_response_raises_job_error_fetch_failed(self):
        url = f"{BASE}/telephony/config/jobs/devices/callDeviceSettings/JOB_FAIL/errors"
        import aiohttp

        with aioresponses() as m:
            m.get(url, status=500, payload={"message": "boom"})
            async with aiohttp.ClientSession() as session:
                with pytest.raises(JobErrorFetchFailed):
                    await fetch_job_errors(
                        session, "callDeviceSettings", "JOB_FAIL", ctx={},
                    )

    @pytest.mark.asyncio
    async def test_404_response_raises_job_error_fetch_failed(self):
        url = f"{BASE}/telephony/config/jobs/devices/callDeviceSettings/JOB_404/errors"
        import aiohttp

        with aioresponses() as m:
            m.get(url, status=404, payload={})
            async with aiohttp.ClientSession() as session:
                with pytest.raises(JobErrorFetchFailed):
                    await fetch_job_errors(
                        session, "callDeviceSettings", "JOB_404", ctx={},
                    )

    @pytest.mark.asyncio
    async def test_200_empty_items_still_returns_empty_list(self):
        """A legitimately-empty items list on a 200 is NOT an error."""
        url = f"{BASE}/telephony/config/jobs/devices/callDeviceSettings/JOB_OK/errors"
        import aiohttp

        with aioresponses() as m:
            m.get(url, status=200, payload={"items": []})
            async with aiohttp.ClientSession() as session:
                items = await fetch_job_errors(
                    session, "callDeviceSettings", "JOB_OK", ctx={},
                )
        assert items == []


# ---------------------------------------------------------------------------
# Fix #19 — 0-update + no fallback_context = hard failure
# ---------------------------------------------------------------------------

class TestBulkZeroUpdateNoFallback:
    @pytest.mark.asyncio
    async def test_zero_update_without_fallback_context_is_failure(self):
        submit_url = f"{BASE}/telephony/config/jobs/devices/callDeviceSettings"
        poll_url = f"{submit_url}/JOB_ZERO"
        calls = [("POST", submit_url, {"locationId": "LOC"})]

        import aiohttp

        with aioresponses() as m:
            m.post(submit_url, status=202, payload={"id": "JOB_ZERO"})
            m.get(poll_url, status=200, payload={
                "latestExecutionExitCode": "COMPLETED",
                "percentageComplete": 100,
                "updatedCount": 0,
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
                    fallback_context=None,
                )

        assert not result.success
        assert result.status == 500
        assert "updated 0" in (result.error or "")
        assert "no fallback" in (result.error or "")

    @pytest.mark.asyncio
    async def test_nonzero_update_without_fallback_context_still_succeeds(self):
        """Legacy behavior: updated > 0 with no context stays success (can't verify expected)."""
        submit_url = f"{BASE}/telephony/config/jobs/devices/callDeviceSettings"
        poll_url = f"{submit_url}/JOB_NZ"
        calls = [("POST", submit_url, {"locationId": "LOC"})]

        import aiohttp

        with aioresponses() as m:
            m.post(submit_url, status=202, payload={"id": "JOB_NZ"})
            m.get(poll_url, status=200, payload={
                "latestExecutionExitCode": "COMPLETED",
                "percentageComplete": 100,
                "updatedCount": 5,
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
                    fallback_context=None,
                )

        assert result.success
        assert result.status == 200


# ---------------------------------------------------------------------------
# Fix #4 — partial update + incomplete error endpoint => FAILED
# ---------------------------------------------------------------------------

class TestBulkPartialIncompleteErrorEndpoint:
    @pytest.mark.asyncio
    async def test_incomplete_error_list_marks_op_failed(self):
        """Bulk job reports 8/10 updated but errors endpoint only returns ONE
        failed item. The missing device was never attempted, so the op must
        surface as FAILED rather than silently COMPLETED after fallback.
        """
        submit_url = f"{BASE}/telephony/config/jobs/devices/callDeviceSettings"
        poll_url = f"{submit_url}/JOB_INCOMPLETE"
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

        import aiohttp

        with aioresponses() as m:
            m.post(submit_url, status=202, payload={"id": "JOB_INCOMPLETE"})
            m.get(poll_url, status=200, payload={
                "latestExecutionExitCode": "COMPLETED",
                "percentageComplete": 100,
                "updatedCount": 8,  # expected 10, so 2 should have failed
            })
            # Errors endpoint returns only 1 item — one failed device is
            # unaccounted for. This is the silent-failure scenario.
            m.get(errors_url, status=200, payload={
                "items": [
                    {"itemId": "DEV8", "trackingId": "t", "error": {"key": "E1"}},
                ]
            })
            # Per-device fallback for DEV8 succeeds.
            m.put(f"{BASE}/telephony/config/devices/DEV8/settings", status=204)

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

        assert not result.success, (
            f"expected partial failure but got success: {result.body}"
        )
        assert result.status == 500
        assert "unaccounted" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_error_fetch_failure_marks_op_failed(self):
        """When the errors endpoint itself returns 500, fix #6 swallows the
        JobErrorFetchFailed and produces an empty failed_ids list. With
        updated < expected, ``execute_bulk_op`` already returned FAILED on
        that path — this test locks the behavior so we don't regress it.
        """
        submit_url = f"{BASE}/telephony/config/jobs/devices/callDeviceSettings"
        poll_url = f"{submit_url}/JOB_ERR_EP"
        errors_url = f"{poll_url}/errors"
        calls = [("POST", submit_url, {"locationId": "LOC"})]

        covered = [
            {"canonical_id": f"device:d{i}",
             "webex_id": f"DEV{i}",
             "data": {"id": f"DEV{i}", "settings": {}}}
            for i in range(5)
        ]
        fallback_ctx = {
            "fallback_handler_key": ("device", "configure_settings"),
            "covered_devices": covered,
            "deps": {},
        }

        import aiohttp

        with aioresponses() as m:
            m.post(submit_url, status=202, payload={"id": "JOB_ERR_EP"})
            m.get(poll_url, status=200, payload={
                "latestExecutionExitCode": "COMPLETED",
                "percentageComplete": 100,
                "updatedCount": 3,
            })
            # Errors endpoint is itself broken — fix #6 surfaces this as a
            # JobErrorFetchFailed, which _resolve_failed_devices catches and
            # converts to [].
            m.get(errors_url, status=500, payload={"message": "broken"})

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
        assert result.status == 500
        # Empty failed_ids path returns this specific error string.
        assert "no error items" in (result.error or "").lower()
