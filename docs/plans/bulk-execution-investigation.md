# Investigation: Bulk Migration Execution Performance

**Date:** 2026-03-24
**Status:** Findings complete, ready for decision

## Problem Statement

The CUCM-to-Webex migration execution loop processes operations serially through a conversational cycle: `next-batch → skill load → think → construct CLI command → run it → parse output → mark-complete → repeat`. Each operation takes ~20-25 seconds wall clock, but only ~5 seconds is actual API time. At 500 users + 500 phones (~1,050 operations), this approach would take ~7 hours. The raw API time at 100 req/min is ~10 minutes.

**The bottleneck is conversational overhead, not the API.**

---

## What Exists Today

### Execution Architecture

| Component | What It Does | Key File |
|-----------|-------------|----------|
| `get_next_batch()` | Returns ALL pending ops in the lowest ready (tier, batch) group | `runtime.py:23-111` |
| `update_op_status()` | Marks ops completed/failed/skipped, cascades skips | `runtime.py:114-198` |
| `partition_into_batches()` | Groups DAG into tier-ordered batches | `batch.py:29-83` |
| `plan_operations` table | SQLite: node_id, status, webex_id, error, attempts | store schema |
| cucm-migrate skill | Serial loop: next-batch → domain skill → mark-complete | `SKILL.md` step 4b |

**Key finding:** `get_next_batch()` already returns entire batches — it doesn't gate consumption to one-at-a-time. For 500 user:create ops at tier 2, all 500 come back in one call. The serialization happens in the skill's `FOR EACH operation in batch` loop.

### SQLite Store Concurrency

- **WAL mode** enabled (`PRAGMA journal_mode=WAL`) — concurrent reads are safe
- **Single connection per process** — `sqlite3.connect()` in `__init__`
- **Writes serialize** through SQLite's internal locking, but WAL allows multiple readers + one writer concurrently
- **`update_op_status()` commits per operation** — fine for serial, would cause lock contention with multiple concurrent writers from different processes (but WAL handles this with retry/timeout, not deadlock)

### Existing Bulk/Batch Capabilities in wxcli

| Command | Bulk? | What It Does |
|---------|-------|-------------|
| `wxcli scim-bulk create` | Yes | SCIM `/v2/Bulk` — creates identity-level users. Does NOT assign calling licenses, extensions, or locations. |
| `wxcli dect-devices create-bulk` | Yes | DECT handset bulk add to a network |
| `wxcli org-contacts create-bulk` | Yes | Bulk create/update org contacts |
| `wxcli activation-email create` | Yes | Bulk activation email resend job |
| `wxcli cucm decide --all` | Yes | Batch-resolve decisions by type |

**No bulk commands exist for:** People (calling users), Locations, Hunt Groups, Call Queues, Auto Attendants, Devices (non-DECT), or any call feature.

### Webex API Bulk Endpoints

| API | Bulk Support | Limitation |
|-----|-------------|------------|
| SCIM `/v2/Bulk` | Multi-op in one request | Identity-level only — no calling config, no extension, no license assignment in same call |
| Manage Numbers Jobs | Batch job (async) | Number moves between locations only |
| Admin Batch Jobs | Batch job (async) | Routing prefix changes, location customizations — not user/feature creation |
| People API `POST /v1/people` | **No bulk endpoint** | One user per request. `callingData=true` requires extension at creation time. |
| Call Features APIs | **No bulk endpoints** | One resource per POST for HG, CQ, AA, parks, pickups, paging |

**Bottom line:** The Webex API does not offer bulk create endpoints for the resources a CUCM migration needs. High throughput requires concurrent individual API calls.

### wxc_sdk Async Capabilities

The SDK provides a production-ready async engine (`docs/reference/wxc-sdk-patterns.md` section 4):

```python
from wxc_sdk.as_api import AsWebexSimpleApi

async with AsWebexSimpleApi(concurrent_requests=40) as api:
    results = await asyncio.gather(
        *[api.session.rest_post(url, json=body) for body in bodies],
        return_exceptions=True,
    )
```

- Semaphore-based concurrency control (configurable 10-100)
- Automatic 429 retry with backoff
- `return_exceptions=True` collects errors without stopping the batch
- Documented and battle-tested for bulk operations in wxc_sdk examples

---

## Approach 1: Parallel Agent Dispatch

### How It Would Work

The cucm-migrate skill already gets all tier operations via `next-batch`. Instead of looping serially, it would dispatch parallel agents — one per operation or small batch of operations.

### What Would Need to Change

1. **Skill loop** — replace `FOR EACH operation` with parallel `Agent()` calls (5-6 at a time per user's sizing guidance)
2. **SQLite concurrency** — each agent opens its own `MigrationStore` connection. WAL mode handles concurrent reads. Write contention on `mark-complete` is manageable (SQLite retries with busy_timeout).
3. **next-batch consumption** — already returns full batches, no changes needed
4. **Agent task** — each agent loads the domain skill, constructs and runs the wxcli command, parses output, and calls `mark-complete`

### Performance Estimate

| Agents | Ops/min (API-bound) | Ops/min (agent overhead) | 1,050 ops | Limiting Factor |
|--------|--------------------|-----------------------|-----------|----------------|
| 1 (current) | ~3 | ~3 | ~350 min (5.8h) | Conversational overhead |
| 5 | ~60 | ~15 | ~70 min | Agent startup + skill load (~20s each) |
| 6 | ~72 | ~18 | ~58 min | Approaches API rate limit |
| 10 | ~100 | ~30 | ~35 min | API rate limit (100 req/min) + 529 overload risk |

The constraint isn't the API — it's that **each agent still carries ~15-20s of conversational overhead** (skill loading, LLM thinking, tool invocation parsing). Even with 10 parallel agents, you're looking at ~30-35 minutes.

### Risks

- **529 overload errors** from Claude API at 10+ concurrent agents (observed per user feedback)
- **Claude API cost** — each operation generates ~2-3K tokens of skill content + response. At 1,050 ops × 5K tokens = 5.25M tokens.
- **SQLite write contention** — manageable with WAL but adds latency under high concurrency
- **Error handling** — an agent that fails mid-operation may leave the DB in an inconsistent state (marked in_progress but agent died)
- **Debugging** — parallel agent failures are harder to diagnose than serial ones

### Verdict

**Feasible but expensive and still slow.** You'd spend significant Claude API tokens to save time on something that doesn't need LLM intelligence for the happy path. The domain skills exist to help with error diagnosis and edge cases — not to construct a known-good CLI command string for the 500th user create that's identical to the previous 499.

---

## Approach 2: Bulk CLI Command (`wxcli cucm execute`)

### How It Would Work

A new CLI command that internalizes the entire execution loop in Python with async concurrency:

```bash
wxcli cucm execute [--concurrency 20] [--dry-run] [--tier N] [--batch NAME]
```

The command:
1. Opens the migration store
2. Calls `get_next_batch()` to get ready operations
3. Groups operations by resource type
4. Executes each group concurrently using `aiohttp` (raw HTTP, same pattern as wxcli commands)
5. Handles 429 retries automatically (semaphore + exponential backoff)
6. Calls `update_op_status()` for each completed/failed operation
7. Repeats until no more batches are ready
8. Prints a summary

### What Would Need to Change

1. **New file: `src/wxcli/commands/cucm_execute.py`** — the bulk execution engine
2. **Operation-to-API mapping** — a Python dict that maps `(resource_type, op_type)` → HTTP method + URL template + body builder. This replaces the domain skill's conversational command construction with deterministic Python functions.
3. **Async HTTP engine** — uses `aiohttp` directly (not wxc_sdk typed API) for raw HTTP calls, matching wxcli's existing `requests`-based pattern but async
4. **Rate limiter** — `asyncio.Semaphore(concurrent_requests)` + 429 backoff
5. **Store updates** — `update_op_status()` called from the main event loop thread (SQLite is not thread-safe, but all writes happen in the main async loop = single thread)
6. **Skill change** — cucm-migrate skill invokes `wxcli cucm execute` instead of looping, then reviews failures

### Operation-to-API Mapping (Design Sketch)

```python
# Maps (resource_type, op_type) → callable that returns (method, url, body)
OPERATION_HANDLERS: dict[tuple[str, str], Callable] = {
    ("location", "create"): build_location_create,
    ("location", "enable_calling"): build_location_enable_calling,
    ("user", "create"): build_user_create,
    ("user", "configure_settings"): build_user_settings,
    ("user", "configure_voicemail"): build_user_voicemail,
    ("workspace", "create"): build_workspace_create,
    ("device", "create"): build_device_create,
    ("hunt_group", "create"): build_hunt_group_create,
    ("call_queue", "create"): build_call_queue_create,
    ("auto_attendant", "create"): build_auto_attendant_create,
    # ... ~25 total handlers matching the skill dispatch table
}

async def execute_operation(session, op, token, rate_limiter):
    handler = OPERATION_HANDLERS[(op["resource_type"], op["op_type"])]
    method, url, body = handler(op["data"], op["resolved_deps"])
    async with rate_limiter:
        resp = await session.request(method, url, json=body, headers=auth_headers(token))
        return parse_response(resp, op)
```

Each handler is ~10-30 lines of deterministic Python — no LLM needed. The canonical data from the migration store already has all the fields; the handler just maps them to the API shape.

### CLI Interface

```
$ wxcli cucm execute --help

Execute the migration plan.

Options:
  --concurrency N     Max concurrent API calls (default: 20, max: 50)
  --dry-run           Show what would be executed without calling APIs
  --tier N            Execute only tier N (for staged rollouts)
  --batch NAME        Execute only the named batch
  --stop-on-failure   Stop execution on first failure (default: continue)
  -p, --project NAME  Project name
  -o, --output FORMAT Output: table, json (default: table)

Example:
  wxcli cucm execute                    # Execute all remaining operations
  wxcli cucm execute --dry-run          # Preview execution plan
  wxcli cucm execute --tier 2           # Execute only user/workspace creates
  wxcli cucm execute --concurrency 40   # Higher parallelism
```

### Performance Estimate

| Concurrency | Sustained req/min | 1,050 ops | Notes |
|-------------|------------------|-----------|-------|
| 1 (serial Python) | ~12 | ~88 min | No conversational overhead, just HTTP |
| 10 | ~100 | ~10.5 min | Near API ceiling |
| 20 | ~100 | ~10.5 min | API rate limit is the ceiling, not concurrency |
| 40 | ~100 | ~10.5 min | Same — 429 retries keep you at ~100 req/min sustained |

**Important:** The Webex API rate limit is 100 req/min per token. With `concurrent_requests=20` and automatic 429 retry, you'll sustain ~80-100 req/min regardless of concurrency setting. Higher concurrency just means more 429 retries. The sweet spot is likely **concurrency 15-20** to stay just under the rate limit with minimal retry overhead.

Accounting for multi-call operations (user:configure_settings = ~5 API calls), total API calls for 1,050 ops is closer to ~2,500. At 100 req/min: **~25 minutes**. Compare to ~7 hours serial.

### Relationship to Existing Architecture

This doesn't replace the migration store, the planner, or the dependency graph. It replaces only the **execution loop** — the part that currently lives in the cucm-migrate skill's step 4b.

```
BEFORE:  planner → store → skill loop (serial, conversational) → wxcli commands → API
AFTER:   planner → store → wxcli cucm execute (async, programmatic) → API directly
```

The store's `plan_operations`, `plan_edges`, and `get_next_batch()`/`update_op_status()` functions are reused as-is.

### Error Handling Strategy

```
For each operation result:
  IF 2xx → update_op_status(completed, webex_id=response["id"])
  IF 409 → search for existing resource, if found → mark_complete with existing ID
  IF 429 → retry with backoff (handled by rate limiter)
  IF 400/500 → update_op_status(failed, error=response_body)

After all batches:
  Print summary: N completed, M failed, K skipped
  If failures exist: "Run 'wxcli cucm execution-status' to review, then 'wxcli cucm execute' to retry failed ops"
```

Failed operations stay in `failed` status. Running `wxcli cucm execute` again will pick them up (they'll be pending after a `wxcli cucm retry-failed` command or manual status reset).

---

## Approach 3 (Hybrid): Execute + Skill Review

The recommended approach combines both:

### Phase 1: `wxcli cucm execute` handles the happy path

The new CLI command processes all straightforward operations programmatically. No LLM involvement. This handles ~90-95% of operations.

### Phase 2: cucm-migrate skill handles failures

After `execute` completes, the cucm-migrate skill:
1. Runs `wxcli cucm execution-status -o json` to see results
2. For each failure, loads the appropriate domain skill to diagnose and fix
3. Uses conversational judgment for: retry with modified params, skip and cascade, or escalate to admin

### Updated Skill Flow

```
Step 4b (replaces serial loop):

  1. Run: wxcli cucm execute --concurrency 20
  2. Run: wxcli cucm execution-status -o json
  3. IF all completed → proceed to Step 5 (report)
  4. IF failures exist:
     Show failure summary to admin
     FOR EACH failed operation:
       Load domain skill (Skill tool)
       Diagnose failure
       Present options: fix+retry | skip | rollback
     After resolution: wxcli cucm execute (picks up remaining)
```

This preserves the skill's value (error diagnosis, admin interaction, domain knowledge) while eliminating its bottleneck (serial execution of straightforward operations).

---

## Estimated Impact Comparison

| Approach | 25 ops (test bed) | 1,050 ops (production) | Claude API cost | Implementation effort |
|----------|-------------------|----------------------|----------------|---------------------|
| **Current (serial skill)** | ~8 min | ~350 min (5.8h) | High (all ops) | None |
| **Approach 1 (parallel agents)** | ~3 min | ~35-70 min | Very high (all ops × agents) | Low (skill change only) |
| **Approach 2 (bulk CLI)** | ~1 min | ~25 min | Zero (execution) | Medium (new command + handlers) |
| **Approach 3 (hybrid)** | ~2 min | ~25-30 min | Low (failures only) | Medium (new command + skill update) |

---

## Recommendation: Approach 3 (Hybrid)

**Rationale:**
1. **25x faster** — from ~7 hours to ~25-30 minutes for 1,050 operations
2. **Near-zero Claude API cost** for execution — LLM only used for failure diagnosis
3. **Preserves skill value** — domain skills handle the cases that need judgment
4. **Respects the constraint** — wxcli remains the execution layer
5. **Reuses existing infrastructure** — store, planner, dependency graph, get_next_batch(), update_op_status() all used as-is
6. **Predictable** — deterministic Python, not LLM-generated commands

### What to Build

1. **`src/wxcli/commands/cucm_execute.py`** (~400-600 lines)
   - Async execution engine with rate limiting
   - Operation handler registry (~25 handlers)
   - Each handler: `(resource_type, op_type)` → HTTP method + URL + body
   - Progress display (Rich live table or progress bar)
   - `--dry-run` mode for validation

2. **Wire into CLI** — add to `cucm.py` as `wxcli cucm execute`

3. **Update cucm-migrate skill** — replace step 4b serial loop with `wxcli cucm execute` invocation + failure review

4. **Optional: `wxcli cucm retry-failed`** — resets failed ops to pending so `execute` picks them up

### What NOT to Build

- No changes to the migration store, planner, or dependency graph
- No changes to the domain skills (they're still used for failure diagnosis)
- No changes to the generator pipeline
- No SCIM bulk integration (it doesn't help — calling users need People API + calling config)

### Dependencies

- Depends on Phase 12a (upstream bugfixes) being complete — the operation handlers need correct canonical data shapes
- Depends on Phase 12b (runtime module) being complete — `get_next_batch()` and `update_op_status()` must exist (they do)
- Independent of Phase 12c (model table update)

### Open Questions

1. **Auth token for execute** — should `wxcli cucm execute` read the token from `wxcli configure` (like all other commands), or accept `--token`? Probably the former for consistency.
2. **Progress display** — Rich progress bar vs periodic status prints? The command could run for 25+ minutes; progress feedback matters.
3. **Concurrency tuning** — should we auto-detect the rate limit ceiling (start at 20, back off on 429s, increase on success), or use a fixed semaphore? Fixed is simpler and more predictable.
4. **Multi-call operations** — `user:configure_settings` needs ~5 sequential API calls per user. Should each sub-call be a separate async task, or should the 5 calls for one user be sequential within one task? (Sequential per user, parallel across users — otherwise you'd race-condition a user's settings.)
