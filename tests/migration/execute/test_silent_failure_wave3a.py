"""Wave 3A of silent-failure-hardening.

Covers the Group 3 (HIGH) engine fallback-gap fixes:

* Fix #5 — ``_build_fallback_context`` now logs a WARNING for each
  covered_cid missing a resolved webex_id and returns
  ``excluded_unresolved_count`` so the silent drops are auditable.
* Fix #7 — ``execute_bulk_op`` emits a per-job summary INFO log line
  accounting for bulk_updated, fallback_attempted, fallback_recovered,
  and excluded_unresolved_count on every exit path. Error messages on
  partial-failure paths also include the excluded count so no device
  is silently dropped from operator visibility.
* Fix #8 — ``_validate_job_id`` is called immediately before polling.
  A missing, empty, whitespace-only, or implausibly-short job_id is
  converted to ``OpResult(status=500, error=...)`` instead of being
  polled into oblivion.
"""

from __future__ import annotations

import asyncio
import logging

import pytest
from aioresponses import aioresponses

from wxcli.migration.execute.engine import (
    BASE,
    _build_fallback_context,
    _validate_job_id,
    execute_bulk_op,
)


# ---------------------------------------------------------------------------
# Fix #5 — _build_fallback_context surfaces silently-dropped devices
# ---------------------------------------------------------------------------

class TestBuildFallbackContextExcluded:
    def test_unresolved_cids_are_excluded_and_logged(self, caplog):
        """Three devices covered, only two resolved. The third must be
        logged, the returned context must report excluded_unresolved_count=1,
        and covered_devices must contain ONLY the resolved devices.
        """
        op = {
            "data": {
                "covered_canonical_ids": [
                    "device:resolved1",
                    "device:resolved2",
                    "device:unresolved",
                ],
                "fallback_handler_key": ["device", "configure_settings"],
            },
            "resolved_deps": {
                "device:resolved1": "WID1",
                "device:resolved2": "WID2",
                # "device:unresolved" missing on purpose.
            },
        }

        with caplog.at_level(logging.WARNING,
                              logger="wxcli.migration.execute.engine"):
            fc = _build_fallback_context(op, ctx={})

        assert fc is not None
        assert fc["excluded_unresolved_count"] == 1
        assert "device:unresolved" in fc["excluded_canonical_ids"]

        covered_cids = {d["canonical_id"] for d in fc["covered_devices"]}
        assert covered_cids == {"device:resolved1", "device:resolved2"}

        # Exactly one WARNING naming the unresolved cid.
        warning_messages = [
            rec.message for rec in caplog.records
            if rec.levelno == logging.WARNING
        ]
        assert any("device:unresolved" in m for m in warning_messages), (
            f"expected WARN naming device:unresolved, got: {warning_messages}"
        )
        assert any("excluding from fallback" in m for m in warning_messages)

    def test_all_resolved_yields_zero_excluded(self, caplog):
        """With every cid resolved the excluded count must be 0 and no
        warnings emitted."""
        op = {
            "data": {
                "covered_canonical_ids": ["device:a", "device:b"],
                "fallback_handler_key": ["device", "configure_settings"],
            },
            "resolved_deps": {"device:a": "W1", "device:b": "W2"},
        }
        with caplog.at_level(logging.WARNING,
                              logger="wxcli.migration.execute.engine"):
            fc = _build_fallback_context(op, ctx={})
        assert fc is not None
        assert fc["excluded_unresolved_count"] == 0
        assert fc["excluded_canonical_ids"] == []
        assert not [r for r in caplog.records if r.levelno == logging.WARNING]

    def test_missing_metadata_returns_none_unchanged(self):
        """Guard: the short-circuit for ops without covered_canonical_ids or
        fallback_handler_key must still return None — excluded bookkeeping
        should never be attached to a non-fallback op."""
        op = {"data": {}, "resolved_deps": {}}
        assert _build_fallback_context(op, ctx={}) is None


# ---------------------------------------------------------------------------
# Fix #7 — summary log + excluded count in error messages
# ---------------------------------------------------------------------------

class TestExecuteBulkOpSummaryLog:
    @pytest.mark.asyncio
    async def test_summary_log_on_full_success(self, caplog):
        """When updated >= expected, a summary INFO log line must still
        fire, accounting for fallback_attempted=0 and the excluded count."""
        submit_url = f"{BASE}/telephony/config/jobs/devices/callDeviceSettings"
        poll_url = f"{submit_url}/JOB_SUMMARY_OK_LONG"
        calls = [("POST", submit_url, {"locationId": "LOC"})]
        fallback_ctx = {
            "fallback_handler_key": ("device", "configure_settings"),
            "covered_devices": [
                {"canonical_id": "device:a", "webex_id": "W1",
                 "data": {"id": "W1", "settings": {}}},
                {"canonical_id": "device:b", "webex_id": "W2",
                 "data": {"id": "W2", "settings": {}}},
            ],
            "deps": {},
            "excluded_unresolved_count": 3,
            "excluded_canonical_ids": ["device:x", "device:y", "device:z"],
        }

        import aiohttp

        with aioresponses() as m:
            m.post(submit_url, status=202, payload={"id": "JOB_SUMMARY_OK_LONG"})
            m.get(poll_url, status=200, payload={
                "latestExecutionExitCode": "COMPLETED",
                "percentageComplete": 100,
                "updatedCount": 2,
            })
            async with aiohttp.ClientSession() as session:
                sem = asyncio.Semaphore(5)
                with caplog.at_level(logging.INFO,
                                      logger="wxcli.migration.execute.engine"):
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
        summary_lines = [
            r.message for r in caplog.records
            if "summary" in r.message
            and "bulk_updated" in r.message
            and "excluded_unresolved" in r.message
        ]
        assert summary_lines, (
            f"expected summary log line, got: "
            f"{[r.message for r in caplog.records]}"
        )
        joined = " ".join(summary_lines)
        assert "excluded_unresolved=3" in joined
        assert "bulk_updated=2/2" in joined
        assert "fallback_attempted=0" in joined
        assert "fallback_recovered=0" in joined

    @pytest.mark.asyncio
    async def test_excluded_count_in_partial_failure_error(self, caplog):
        """On the 'unaccounted for' path, the error message must include
        excluded_unresolved so operators can reconcile every device."""
        submit_url = f"{BASE}/telephony/config/jobs/devices/callDeviceSettings"
        poll_url = f"{submit_url}/JOB_PARTIAL_LONG"
        errors_url = f"{poll_url}/errors"
        calls = [("POST", submit_url, {"locationId": "LOC"})]

        covered = [
            {"canonical_id": f"device:d{i}", "webex_id": f"DEV{i}",
             "data": {"id": f"DEV{i}", "settings": {}}}
            for i in range(5)
        ]
        fallback_ctx = {
            "fallback_handler_key": ("device", "configure_settings"),
            "covered_devices": covered,
            "deps": {},
            "excluded_unresolved_count": 2,
            "excluded_canonical_ids": ["device:gone1", "device:gone2"],
        }

        import aiohttp

        with aioresponses() as m:
            m.post(submit_url, status=202, payload={"id": "JOB_PARTIAL_LONG"})
            m.get(poll_url, status=200, payload={
                "latestExecutionExitCode": "COMPLETED",
                "percentageComplete": 100,
                "updatedCount": 3,  # 5 expected, 2 missing
            })
            m.get(errors_url, status=200, payload={
                "items": [{"itemId": "DEV4", "trackingId": "t",
                           "error": {"key": "E1"}}],
            })
            m.put(f"{BASE}/telephony/config/devices/DEV4/settings", status=204)

            async with aiohttp.ClientSession() as session:
                sem = asyncio.Semaphore(5)
                with caplog.at_level(logging.INFO,
                                      logger="wxcli.migration.execute.engine"):
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
        assert "excluded_unresolved=2" in (result.error or "")
        # Summary line also fires on the failure path.
        assert any("bulk_updated=3/5" in r.message
                    and "fallback_attempted=1" in r.message
                    and "excluded_unresolved=2" in r.message
                   for r in caplog.records)

    @pytest.mark.asyncio
    async def test_excluded_count_in_empty_errors_path(self):
        """When fetch_job_errors returns [] (or blew up), the error message
        must still surface the excluded count."""
        submit_url = f"{BASE}/telephony/config/jobs/devices/callDeviceSettings"
        poll_url = f"{submit_url}/JOB_EMPTY_LONG"
        errors_url = f"{poll_url}/errors"
        calls = [("POST", submit_url, {"locationId": "LOC"})]

        covered = [
            {"canonical_id": f"device:d{i}", "webex_id": f"DEV{i}",
             "data": {"id": f"DEV{i}", "settings": {}}}
            for i in range(3)
        ]
        fallback_ctx = {
            "fallback_handler_key": ("device", "configure_settings"),
            "covered_devices": covered,
            "deps": {},
            "excluded_unresolved_count": 4,
            "excluded_canonical_ids": ["device:a", "device:b",
                                       "device:c", "device:d"],
        }

        import aiohttp

        with aioresponses() as m:
            m.post(submit_url, status=202, payload={"id": "JOB_EMPTY_LONG"})
            m.get(poll_url, status=200, payload={
                "latestExecutionExitCode": "COMPLETED",
                "percentageComplete": 100,
                "updatedCount": 1,
            })
            # Errors endpoint returns 200 but empty items → failed_ids == [].
            m.get(errors_url, status=200, payload={"items": []})

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
        assert "excluded_unresolved=4" in (result.error or "")


# ---------------------------------------------------------------------------
# Fix #8 — _validate_job_id + execute_bulk_op malformed-id guard
# ---------------------------------------------------------------------------

class TestValidateJobId:
    def test_none_raises_value_error(self):
        with pytest.raises(ValueError):
            _validate_job_id(None)

    def test_empty_string_raises_value_error(self):
        with pytest.raises(ValueError):
            _validate_job_id("")

    def test_whitespace_only_raises_value_error(self):
        with pytest.raises(ValueError):
            _validate_job_id("   ")

    def test_single_char_raises_value_error(self):
        with pytest.raises(ValueError):
            _validate_job_id("x")

    def test_non_string_type_raises_value_error(self):
        with pytest.raises(ValueError):
            _validate_job_id(12345)  # type: ignore[arg-type]

    def test_plausible_id_accepted(self):
        # 10+ chars is the enforced floor (Fix #4). Anything shorter is
        # treated as a truncation / parse bug. Long realistic URNs pass.
        _validate_job_id("JOB_OK_0123")  # 11 chars, above the floor
        _validate_job_id("Y2lzY29zcGFyazovL3VzL0pPQi8xMjM0NQ==")


class TestExecuteBulkOpMalformedJobId:
    @pytest.mark.asyncio
    async def test_single_char_job_id_returns_op_result_500(self):
        """Submit succeeds but returns a bogus single-char id. Must be
        converted to OpResult(status=500, error='malformed job_id').
        Poll URL is NOT registered — if the code polled, aioresponses
        would raise ConnectionError, which would surface as a different
        failure mode.
        """
        submit_url = f"{BASE}/telephony/config/jobs/devices/callDeviceSettings"
        calls = [("POST", submit_url, {"locationId": "LOC"})]

        import aiohttp

        with aioresponses() as m:
            m.post(submit_url, status=202, payload={"id": "x"})

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
        assert "malformed job_id" in (result.error or "")

    @pytest.mark.asyncio
    async def test_whitespace_job_id_returns_op_result_500(self):
        """Submit returns "   " — non-empty by `bool()` but still
        malformed. Must NOT be polled."""
        submit_url = f"{BASE}/telephony/config/jobs/devices/callDeviceSettings"
        calls = [("POST", submit_url, {"locationId": "LOC"})]

        import aiohttp

        with aioresponses() as m:
            m.post(submit_url, status=202, payload={"id": "   "})

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
        assert "malformed job_id" in (result.error or "")


# ---------------------------------------------------------------------------
# Finding #7 + #8 — _run_per_device_fallback aggregates errors & handles
# SkippedResult instead of raising TypeError.
# ---------------------------------------------------------------------------


class TestRunPerDeviceFallbackSkippedResult:
    """Fix #8: a fallback handler can legitimately return ``SkippedResult``
    when a required upstream dep is missing. Previously that sentinel — a
    truthy, non-iterable frozen dataclass — would raise ``TypeError`` on
    the ``for method, url, body in calls`` loop. Fix must detect and record
    it as a per-device failure with the reason, without the loop ever
    seeing it.
    """

    @pytest.mark.asyncio
    async def test_skipped_result_recorded_as_failure_not_raised(self):
        """Handler returns ``SkippedResult`` for the failed device. Fallback
        must return ``(False, "...skipped: dep X missing...")`` rather than
        bubble a TypeError from attempting to iterate the sentinel."""
        from wxcli.migration.execute.engine import _run_per_device_fallback
        from wxcli.migration.execute.handlers import (
            HANDLER_REGISTRY,
            SkippedResult,
        )

        sentinel_key = ("__test__", "skipped_always")

        def _always_skipped(data, deps, ctx):
            return SkippedResult(reason="dep X missing")

        HANDLER_REGISTRY[sentinel_key] = _always_skipped
        try:
            fallback_ctx = {
                "fallback_handler_key": sentinel_key,
                "covered_devices": [
                    {"canonical_id": "device:d1",
                     "webex_id": "DEV1",
                     "data": {"settings": {}}},
                ],
                "deps": {},
                "ctx": {},
            }

            import aiohttp

            async with aiohttp.ClientSession() as session:
                sem = asyncio.Semaphore(5)
                ok, err = await _run_per_device_fallback(
                    session, ["DEV1"], fallback_ctx, sem,
                )
        finally:
            HANDLER_REGISTRY.pop(sentinel_key, None)

        assert ok is False
        assert err is not None
        # Error message surfaces the SkippedResult reason. The exact shape
        # is "unresolved=0, failed=1: [('DEV1', 'skipped: dep X missing')]"
        # but we just assert the key bits.
        assert "dep X missing" in err
        assert "skipped" in err.lower()
        assert "DEV1" in err


class TestRunPerDeviceFallbackAggregation:
    """Fix #7: collect all unresolved + per-device failures and emit one
    WARN summary, instead of returning on the first missing device."""

    @pytest.mark.asyncio
    async def test_unresolved_and_errors_aggregated_not_fail_fast(self, caplog):
        """Three devices in failed_webex_ids: one unresolved (not in
        covered), one returning 400 from the PUT, one succeeding. Old
        behavior was to return False on the first unresolved case. New
        behavior collects both the unresolved id and the 400-failure,
        emits ONE WARN summary after the loop, and returns a compacted
        error string with counts."""
        import logging

        from wxcli.migration.execute.engine import _run_per_device_fallback

        fallback_ctx = {
            "fallback_handler_key": ("device", "configure_settings"),
            "covered_devices": [
                # Only DEV2 and DEV3 are covered; DEV1 is unresolved.
                # Both records must have a canonical_id that's keyed in
                # per_device_deps (the engine auto-augments with that one
                # entry) so the handle_device_configure_settings handler
                # can resolve the device and return real calls.
                {"canonical_id": "device:d2",
                 "webex_id": "DEV2",
                 "data": {
                     "canonical_id": "device:d2",
                     "device_settings": {"allowThirdPartyControl": True},
                 }},
                {"canonical_id": "device:d3",
                 "webex_id": "DEV3",
                 "data": {
                     "canonical_id": "device:d3",
                     "device_settings": {"allowThirdPartyControl": True},
                 }},
            ],
            "deps": {},
            "ctx": {},
        }

        import aiohttp

        with aioresponses() as m:
            # DEV2 → 400 (per-device failure).
            m.put(f"{BASE}/telephony/config/devices/DEV2/settings",
                  status=400, payload={"message": "boom"})
            # DEV3 → 204 (success).
            m.put(f"{BASE}/telephony/config/devices/DEV3/settings", status=204)

            async with aiohttp.ClientSession() as session:
                sem = asyncio.Semaphore(5)
                with caplog.at_level(logging.WARNING,
                                      logger="wxcli.migration.execute.engine"):
                    ok, err = await _run_per_device_fallback(
                        session, ["DEV1", "DEV2", "DEV3"], fallback_ctx, sem,
                    )

        # Aggregated result: not ok, error cites unresolved=1 and failed=1.
        assert ok is False
        assert err is not None
        assert "unresolved=1" in err
        assert "failed=1" in err
        assert "DEV2" in err  # the 400 failure is in the first-3 head.
        # A single WARN summary fired, naming the unresolved DEV1 and
        # the per-device failure count.
        summaries = [
            r.message for r in caplog.records
            if r.levelno == logging.WARNING and "Fallback summary" in r.message
        ]
        assert len(summaries) == 1, (
            f"expected exactly one WARN summary, got: {summaries}"
        )
        assert "1 unresolved" in summaries[0]
        assert "DEV1" in summaries[0]
        assert "1 per-device failure" in summaries[0]
