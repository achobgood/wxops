"""Characterization of the migration engine's retry and failure semantics.

**These tests record what `execute/engine.py` does TODAY. Several of them
deliberately assert behaviour this repository's own audit calls wrong.** That
is the point: `ARCHITECTURE_AUDIT.md` §3.2 B1 extracts `auth.py`'s retry policy
into a module both stacks import, which changes how the engine behaves under
real rate limiting — and rate limiting is not observable in a test suite. These
six tests are the instrument that distinguishes "the engine now retries a 503"
from "the engine now does something else too."

**Do not "fix" the engine to make one of these go green.** When B1 lands, the
correct move is to update the assertion *and* its comment in the same commit,
so the diff shows the behaviour change explicitly. A characterization test that
was quietly edited to match a new implementation has pinned the fix, not the
baseline.

The six behaviours, and where each sits on the audit's Target A / Target B
disagreement table (`ARCHITECTURE_AUDIT.md` §2 #2):

| # | Behaviour | `auth.py` (A) | `engine.py` (B) — pinned here |
|---|---|---|---|
| 1 | 503 | retried (`RETRY_STATUSES`) | **not retried** — fails the op at once |
| 2 | date-form `Retry-After` | `try/except ValueError` → backoff | **raises**, and the op fails |
| 3 | `Retry-After` above cap | clamped to 30s | **uncapped** — sleeps whatever is sent |
| 4 | concurrent 429s | jittered backoff | **unjittered** — they wake together |
| 5 | 409 recovery search | n/a | **no exact-name check** on the match |
| 6 | 4xx/5xx on a write | — | recorded `failed`, not `completed` ✓ |

Row 6 is the one that agrees with its own docs. It is here because the audit's
Mutation 2 showed nothing was asserting it.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import aiohttp
import networkx as nx
import pytest
from aioresponses import aioresponses

from wxcli.migration.execute.batch import save_plan_to_store
from wxcli.migration.execute.engine import (
    BASE,
    OpResult,
    _try_find_existing,
    execute_all_batches,
    execute_single_op,
    run_batch_ops,
)
from wxcli.migration.models import (
    CanonicalLocation,
    MigrationStatus,
    OpStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore

LOCATIONS = f"{BASE}/locations"
PEOPLE = f"{BASE}/people"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _prov() -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id="pk",
        source_name="test",
        extracted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


@pytest.fixture
def slept(monkeypatch):
    """Record every `asyncio.sleep` duration and return immediately.

    The engine's only backoff mechanism is `await asyncio.sleep(retry_after)`
    (`engine.py:206`), so the recorded list *is* the retry policy's output.
    """
    recorded: list[float] = []
    real_sleep = asyncio.sleep

    async def fake_sleep(delay, *args, **kwargs):
        recorded.append(delay)
        return await real_sleep(0)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    return recorded


def _request_count(mocked: aioresponses) -> int:
    return sum(len(calls) for calls in mocked.requests.values())


async def _run_op(mocked_calls, node_id="location:hq:create", concurrency=1,
                  **kwargs) -> OpResult:
    """Drive `execute_single_op` against a real ClientSession."""
    async with aiohttp.ClientSession() as session:
        return await execute_single_op(
            session, node_id, mocked_calls,
            asyncio.Semaphore(concurrency), **kwargs,
        )


def _single_location_plan(store: MigrationStore) -> None:
    """The simplest possible plan: one tier-0 `location:create`."""
    store.upsert_object(CanonicalLocation(
        canonical_id="location:hq",
        provenance=_prov(),
        name="HQ",
        time_zone="America/New_York",
        preferred_language="en_US",
        announcement_language="en_us",
        status=MigrationStatus.ANALYZED,
    ))
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


@pytest.fixture
def store(tmp_path):
    s = MigrationStore(tmp_path / "retry-characterization.db")
    yield s
    s.close()


# ---------------------------------------------------------------------------
# 1. A 503 is NOT retried — it fails the operation on the first response
# ---------------------------------------------------------------------------

async def test_503_fails_the_op_at_once_and_is_never_retried(slept):
    """`engine.py:203-214`. Only 429 reaches the retry branch; every other
    `>= 400` returns an `OpResult` immediately.

    `auth.py:160` retries {429, 500, 502, 503, 504}. The consequence the audit
    names: a single 503 from Webex while creating a location fails that op
    permanently and cascade-skips the location's users, their devices, and
    every feature hanging off them — and the operator is told the operation
    *failed*, not that the platform blipped.
    """
    with aioresponses() as m:
        m.post(LOCATIONS, status=503, payload={"message": "upstream unavailable"})
        result = await _run_op([("POST", LOCATIONS, {"name": "HQ"})])

        assert _request_count(m) == 1, "a retry would have issued a second POST"

    assert result.success is False
    assert result.status == 503
    assert result.error == "503: upstream unavailable"
    assert slept == [], "no backoff was attempted at all"


async def test_500_and_502_and_504_also_fail_at_once(slept):
    """The other three statuses `auth.py` retries and `engine.py` does not."""
    for status in (500, 502, 504):
        with aioresponses() as m:
            m.post(LOCATIONS, status=status, payload={"message": "blip"})
            result = await _run_op([("POST", LOCATIONS, {"name": "HQ"})])
            assert _request_count(m) == 1
        assert result.success is False
        assert result.status == status
    assert slept == []


# ---------------------------------------------------------------------------
# 2. A date-form Retry-After raises, and the op fails
# ---------------------------------------------------------------------------

async def test_date_form_retry_after_raises_valueerror_out_of_the_op():
    """`engine.py:204` is a bare `int(resp_headers.get("Retry-After", 5))`.

    RFC 9110 §10.2.3 permits `Retry-After` in either delta-seconds or HTTP-date
    form. `int("Wed, 21 Oct 2015 07:28:00 GMT")` raises ValueError, and the only
    `except` in the retry loop catches `aiohttp.ClientError` (`:226`), so the
    exception escapes `execute_single_op` entirely.

    `auth.py:250-253` wraps the same parse in `try/except ValueError` and falls
    back to `_backoff_delay`.
    """
    with aioresponses() as m:
        m.post(LOCATIONS, status=429, headers={"Retry-After": "Wed, 21 Oct 2015 07:28:00 GMT"},
               payload={})
        with pytest.raises(ValueError):
            await _run_op([("POST", LOCATIONS, {"name": "HQ"})])


async def test_date_form_retry_after_becomes_a_failed_op_with_status_zero():
    """One level up, `run_batch_ops` catches it — as a failure, not a retry.

    `engine.py:826-831` gathers with `return_exceptions=True` and converts any
    exception into `OpResult(status=0, error=str(e))`. So a rate-limit response
    the CLI stack would have *waited out* becomes a permanently failed
    migration operation, reported with a status of 0 — which reads as a
    connection error, not as a 429.
    """
    task = {
        "op": {"node_id": "location:hq:create", "resource_type": "location",
               "op_type": "create"},
        "calls": [("POST", LOCATIONS, {"name": "HQ"})],
    }
    with aioresponses() as m:
        m.post(LOCATIONS, status=429, headers={"Retry-After": "Fri, 31 Dec 1999 23:59:59 GMT"},
               payload={})
        async with aiohttp.ClientSession() as session:
            results = await run_batch_ops(session, [task], asyncio.Semaphore(1), ctx={})

    assert len(results) == 1
    assert results[0].success is False
    assert results[0].status == 0
    assert "invalid literal for int()" in results[0].error


# ---------------------------------------------------------------------------
# 3. Retry-After is honoured uncapped
# ---------------------------------------------------------------------------

async def test_retry_after_is_not_capped(slept):
    """`engine.py:204-206` sleeps whatever the server sent.

    `auth.py:159`/`:251` clamps to `MAX_RETRY_AFTER_SECONDS = 30`. Uncapped, a
    single misbehaving or hostile `Retry-After` stalls one of 20 concurrent
    workers for as long as it likes — inside an unattended migration whose
    caller has no timeout of its own (`engine.py:875` sets none).
    """
    with aioresponses() as m:
        m.post(LOCATIONS, status=429, headers={"Retry-After": "3600"}, payload={})
        m.post(LOCATIONS, status=200, payload={"id": "wx-hq"})
        result = await _run_op([("POST", LOCATIONS, {"name": "HQ"})])
        assert _request_count(m) == 2

    assert result.success is True
    assert slept == [3600], "a 30s cap would have recorded 30"


async def test_missing_retry_after_falls_back_to_a_flat_five_seconds(slept):
    """`engine.py:204`'s default arg is the literal `5` — no backoff growth,
    no jitter. `auth.py:184-188` uses exponential backoff with jitter."""
    with aioresponses() as m:
        m.post(LOCATIONS, status=429, payload={})
        m.post(LOCATIONS, status=429, payload={})
        m.post(LOCATIONS, status=200, payload={"id": "wx-hq"})
        result = await _run_op([("POST", LOCATIONS, {"name": "HQ"})])

    assert result.success is True
    assert slept == [5, 5], "identical on every attempt — the delay does not grow"


# ---------------------------------------------------------------------------
# 4. Two concurrent 429s wake together
# ---------------------------------------------------------------------------

async def test_two_concurrent_429s_wake_at_the_same_instant(slept):
    """The thundering herd, pinned.

    Two things compound here, and the first of them is *correct*: the engine
    releases its semaphore slot across the sleep (`engine.py:194-206` — the
    `async with semaphore` block closes before the `await asyncio.sleep`),
    which the audit settled with `ast` and explicitly tells maintainers to
    leave alone. It means the pool does not deadlock under rate limiting.

    The consequence is the second thing: every rate-limited operation receives
    the same `Retry-After`, sleeps the *identical* unjittered duration, and
    resumes in the same instant — reproducing the burst that caused the
    throttle. At the default `concurrency=20` that is 20 simultaneous retries.

    The fix is jitter (`auth.py:184-188`), not holding the slot.
    """
    with aioresponses() as m:
        m.post(LOCATIONS, status=429, headers={"Retry-After": "5"}, payload={})
        m.post(LOCATIONS, status=200, payload={"id": "wx-hq"})
        m.post(PEOPLE, status=429, headers={"Retry-After": "5"}, payload={})
        m.post(PEOPLE, status=200, payload={"id": "wx-user"})

        semaphore = asyncio.Semaphore(2)
        async with aiohttp.ClientSession() as session:
            results = await asyncio.gather(
                execute_single_op(session, "location:hq:create",
                                  [("POST", LOCATIONS, {"name": "HQ"})], semaphore),
                execute_single_op(session, "user:jane:create",
                                  [("POST", PEOPLE, {"emails": ["j@x.com"]})], semaphore),
            )

    assert all(r.success for r in results)
    assert len(slept) == 2
    assert slept[0] == slept[1] == 5
    assert len(set(slept)) == 1, "jitter would have made these two differ"


# ---------------------------------------------------------------------------
# 5. The 409 recovery search does not verify the name it matched
# ---------------------------------------------------------------------------

async def test_409_recovery_accepts_a_name_that_is_not_an_exact_match():
    """`engine.py:704-714` returns `items[0].get("id")` with no name comparison.

    **This is the one test in this file that pins something the audit did not
    already predict, and it is a finding rather than a policy difference.**
    `_try_find_existing` searches `GET /locations?name=HQ` and takes the first
    item the API returns. Webex's `name` filter is not documented as an exact
    match, so an org containing "HQ Annex" can answer a search for "HQ".

    What that costs: the 409 path exists to recover from "this resource already
    exists". Adopting the wrong id marks the op `completed` and writes that id
    into `plan_operations.webex_id` (`engine.py:960-966`), where every dependent
    op resolves it out of `deps`. Users, devices and features intended for HQ
    would be created against HQ Annex, and `execute/` issues no DELETE anywhere,
    so nothing in the tool can undo it.

    Left asserting the observed behaviour per Phase A's rule. A fix belongs in
    Phase B alongside the rest of the write path, and needs a live check of what
    the `name` filter actually matches before the comparison is written.
    """
    with aioresponses() as m:
        m.get(f"{LOCATIONS}?name=HQ",
              payload={"items": [{"id": "wx-annex", "name": "HQ Annex"}]})
        async with aiohttp.ClientSession() as session:
            found = await _try_find_existing(
                session, asyncio.Semaphore(1), "location", {"name": "HQ"}, {},
            )

    assert found == "wx-annex", "no exact-match check — the first item wins"


async def test_409_recovery_returns_none_for_an_unsupported_resource_type():
    """The complement, and it is deliberate: location-scoped features
    (`engine.py:693-698`) skip recovery entirely rather than guess, and
    cascade-fail on the next run instead."""
    async with aiohttp.ClientSession() as session:
        found = await _try_find_existing(
            session, asyncio.Semaphore(1), "hunt_group", {"name": "Support"}, {},
        )
    assert found is None


# ---------------------------------------------------------------------------
# 6. Mutation 2 — a 4xx/5xx on the write path is recorded `failed`
# ---------------------------------------------------------------------------

async def test_a_5xx_write_is_recorded_failed_not_completed(store):
    """End-to-end through `execute_all_batches`, reading the store afterwards.

    `completed` in this schema means "2xx", not "applied" — nothing re-reads the
    resource. That is a separate finding. What this pins is narrower and is what
    the audit's Mutation 2 found unasserted: a write that comes back 5xx must not
    land in the store as `completed`.
    """
    _single_location_plan(store)

    with aioresponses() as m:
        m.post(LOCATIONS, status=500, payload={"message": "internal error"})
        summary = await execute_all_batches(store=store, token="tok",
                                            concurrency=2, ctx={})

    assert summary["failed"] == 1
    assert summary["completed"] == 0

    row = store.conn.execute(
        "SELECT status, error_message, webex_id FROM plan_operations WHERE node_id = ?",
        ("location:hq:create",),
    ).fetchone()
    assert row["status"] == OpStatus.FAILED.value
    assert row["webex_id"] is None
    assert "500" in row["error_message"]


async def test_a_4xx_write_is_recorded_failed_not_completed(store):
    """The 4xx half of the same assertion. 400 rather than 409: 409 has its own
    auto-recovery branch (`engine.py:954-970`), which is a different path."""
    _single_location_plan(store)

    with aioresponses() as m:
        m.post(LOCATIONS, status=400, payload={"message": "invalid timeZone"})
        summary = await execute_all_batches(store=store, token="tok",
                                            concurrency=2, ctx={})

    assert summary["failed"] == 1
    assert summary["completed"] == 0

    row = store.conn.execute(
        "SELECT status, error_message FROM plan_operations WHERE node_id = ?",
        ("location:hq:create",),
    ).fetchone()
    assert row["status"] == OpStatus.FAILED.value
    assert "invalid timeZone" in row["error_message"]
