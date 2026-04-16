# Silent Failure Hardening — Design Spec
**Date:** 2026-04-16  
**Scope:** `src/wxcli/migration/execute/` + `src/wxcli/commands/cleanup.py`  
**Approach:** Implement all 19 issues, CRITICAL first, using Opus subagents in dependency-sequenced waves  
**Session note:** Implement in a NEW session — do not mix with device config work

---

## Problem Summary

The migration execute layer has 19 silent failure patterns where operations appear to succeed but resources are silently not created, skipped, or partially configured. The most dangerous are in `handlers.py` (30+ guard clauses that return `[]`, making "prerequisite missing" indistinguishable from "nothing to do") and `engine.py` (bulk jobs with 0 updates silently marked success).

---

## Architecture: The Core Fix

### New `OpResult` status: `SKIPPED`

Add `SKIPPED` alongside `completed` and `failed` in the execution status enum. This is the load-bearing change that enables everything else.

```python
class OpStatus(str, Enum):
    PENDING    = "pending"
    RUNNING    = "running"
    COMPLETED  = "completed"
    SKIPPED    = "skipped"   # NEW — prerequisite missing, op not attempted
    FAILED     = "failed"
```

**`SKIPPED` semantics:**
- Used when a handler can't proceed because a required dependency wasn't resolved (e.g., upstream op failed/skipped, member not created)
- NOT used for legitimate no-ops ("no configuration needed") — those still return `[]`
- The runtime cascade-skips all dependents of a SKIPPED op (same as FAILED)
- The execution report surfaces SKIPPED ops separately from FAILED ops
- Operators can see exactly which ops were skipped and why

**Where `[]` stays vs. changes:**
- `return []` stays for true no-ops: "this feature is disabled", "no agents to assign", "no members to configure"
- `return []` changes to `return skipped(reason=...)` at any guard clause where a REQUIRED dependency is missing

---

## Issue Groups and Fix Strategies

### GROUP 1 — CRITICAL: Engine bulk job failures (engine.py)
*Must land before GROUP 2 (handlers) since fallback logic is tested end-to-end*

**#19: 0-update bulk job marked success when no fallback_context**
- **Fix:** After `execute_bulk_op()`, always check `updated >= expected`. If not, and `fallback_context is None`, return `OpResult(status=FAILED, error="Bulk job updated 0/{expected} devices and no fallback is configured")`.
- **File:** `engine.py` ~line 304-309

**#6: `fetch_job_errors()` returns `[]` on endpoint failure**
- **Fix:** Raise (or return a typed error) instead of returning `[]`. Callers should treat a fetch failure as "we don't know the error count — treat as total failure."
- **File:** `engine.py` ~lines 102-110
- **Option:** Add `class JobErrorFetchFailed(Exception)` and let callers catch it to trigger the appropriate fallback behavior.

**#4: Bulk partial success marked full success after fallback**
- **Fix:** After the fallback loop completes, count how many devices actually succeeded. If `fallback_successes < expected - updated`, return a PARTIAL status (or FAILED with a count in the error message). Never mark the whole op COMPLETED if any device is unconfigured.
- **File:** `engine.py` ~lines 301-336

### GROUP 2 — CRITICAL: Handler guard clauses (handlers.py)
*Depends on GROUP 1 (needs `SKIPPED` status and `skipped()` helper)*

**#10: 30+ handlers return `[]` on missing prerequisite (CRITICAL)**

The fix is mechanical but must be applied carefully. The key is distinguishing:
- **True no-op** (keep `[]`): `if not feature.enabled: return []` — nothing to configure
- **Missing dep** (change to `skipped()`): `if not dep_id: return skipped("dependency X not resolved")` — should have been created

**Approach:**
1. Add a `skipped(reason: str) -> list[OpCallable]` helper that returns a special sentinel the runtime recognizes
   - OR: Return `OpResult(status=SKIPPED, reason=...)` directly (simpler if handlers can return either type)
2. Audit all 30+ `return []` guard clauses at the top of handlers, classify each as no-op vs. missing-dep
3. Change missing-dep sites to return the skipped sentinel

**Specific sites to change (high-confidence missing-dep):**
- `handle_route_list_create()` — returns `[]` if route group not created (hard dep)
- `handle_hg_configure_forwarding()` — returns `[]` if `hg_wid` is None
- `handle_shared_line_configure()` — returns `[]` if < 2 owners resolve
- `handle_monitoring_list_configure()` — returns `[]` if targets don't resolve
- Any handler starting with: `if not <upstream_webex_id>: return []`

**#15: `_resolve_agents()` silently omits unresolved members**
- **Fix:** Return a `(agents_list, skipped_list)` tuple. Callers log a warning for each skipped agent and record them in the op's metadata.
- **File:** `handlers.py` ~lines 94-111

**#16: Monitoring list silently drops unresolved members**
- **Fix:** Same as #15 — log which members were dropped and include count in OpResult metadata.
- **File:** `handlers.py` ~lines 943-952

**#17: Shared line returns `[]` if < 2 owners resolve**
- **Fix:** Change to `return skipped("shared line requires 2+ resolved owners; only N resolved")` instead of `[]`.
- **File:** `handlers.py` ~lines 1131-1138

**#18: Device create doesn't verify returned ID**
- **Fix:** After the API call, if `result.get("id")` is None, return `OpResult(status=FAILED, error="device created but no ID returned")`.
- **File:** `handlers.py` ~lines 460-478

### GROUP 3 — HIGH: Engine fallback gaps (engine.py)
*Can be done alongside GROUP 2*

**#5: `_build_fallback_context()` skips missing devices without warning**
- **Fix:** Add `logger.warning("Device %s not yet created, excluding from fallback", cucm_id)` for each skipped device. Include a count in the returned context object.
- **File:** `engine.py` ~lines 512-549

**#7: `_run_per_device_fallback()` skips unresolved devices silently**
- **Fix:** Collect unresolved devices into a list and log them all at WARNING level after the loop. Return a result that includes `unresolved_count`.
- **File:** `engine.py` ~lines 384-408

**#8: No preflight on bulk job polling (job ID may be malformed)**
- **Fix:** Validate `job_id` is non-empty and well-formed before entering the poll loop. If `job_id` is None/empty, raise immediately.
- **File:** `engine.py` ~lines 282-291

### GROUP 4 — MEDIUM: Runtime cascade tracking (runtime.py)
*Small change, can be done in parallel with GROUP 3*

**#13: Cascade skip doesn't surface reason in execution report**
- **Fix:** When `_cascade_skip()` marks an op skipped, write `reason="Cascade skip: dependency {node_id} {status}"` to the op record. The execution report should group cascade-skipped ops under the failed dependency they cascaded from, not in a flat "skipped: N" count.
- **File:** `runtime.py` ~lines 210-235

### GROUP 5 — MEDIUM: Cleanup tracking (cleanup.py)
*Independent — no dependencies on other groups*

**#1: Skipped extension-only records not listed**
- **Fix:** Collect skipped ext-only records into a list and print them in the dry-run/summary output. At minimum: "Skipped N extension-only records: [email1, email2, ...]"

**#2: Unresolved location names not reported**
- **Fix:** When a requested location name doesn't match, add it to an "unresolved locations" list and print it before proceeding. Don't silently ignore.

**#3: Domain exclusions not recorded in output**
- **Fix:** Print "Excluding users from domains: [domain1, domain2]. N users excluded." in both dry-run and live output.

**#11: Calling-disable failure doesn't gate the wait**
- **Fix:** If `disable_location_calling()` returns `success=False`, skip the 90-second wait for that location and mark the location as "disable failed — will retry deletion anyway."

**#14: Number deletion batch failure continues inefficiently**
- **Fix:** After 3 consecutive batch failures at a location, stop and log a warning: "Too many batch failures for location X — stopping number deletion." Low priority, but prevents pathological retry storms.

### GROUP 6 — LOW: Planner preflight (planner.py)
*Can be done last, independent*

**#9: No preflight on bulk operation support**
- **Fix:** In `preflight/checks.py`, add a check that validates the org supports bulk device jobs before the plan emits any bulk ops. If not supported, the planner should emit per-device ops instead.

**#12: stdout flush swallows errors**
- **Fix:** Wrap `click.flush()` calls with a log instead of bare `pass`: `except Exception: logger.debug("stdout flush failed — parent may lose liveness signal")`. Low priority cosmetic change.

---

## Implementation Plan

### Wave sequence (Opus subagents, max 2 files per agent)

**Wave 1 — Foundation (must complete before Wave 2)**
- Agent A: Add `SKIPPED` to status enum + `skipped()` helper + update runtime to handle it (`models.py` + `runtime.py`)
- Agent B: Fix `engine.py` issues #4, #6, #19 (bulk job critical fixes)

**Wave 2 — Handler guard clauses (depends on Wave 1)**
- Agent C: Audit and fix handler guard clauses in `handlers.py` lines 1-500 (issues #10 partial, #15, #17)
- Agent D: Audit and fix handler guard clauses in `handlers.py` lines 500-1000 (issues #10 partial, #16, #18)
- Agent E: Audit and fix handler guard clauses in `handlers.py` lines 1000-end (issue #10 partial)

**Wave 3 — Secondary fixes (can run parallel with Wave 2)**
- Agent F: Fix `engine.py` issues #5, #7, #8 (fallback gaps)
- Agent G: Fix `runtime.py` issue #13 (cascade tracking)
- Agent H: Fix `cleanup.py` issues #1, #2, #3, #11, #14 (tracking)

**Wave 4 — Final**
- Agent I: Fix `planner.py`/`preflight/checks.py` issue #9 + `cleanup.py` issue #12
- Final agent: Run `pytest src/wxcli/migration/` — fix any test breakage from status enum change

### Test expectations
- All existing 2535 tests must still pass after Wave 1
- New tests for SKIPPED status behavior added in Wave 1
- Each handler fix should add/update a test that asserts SKIPPED (not `[]`) is returned when dep is missing
- Cleanup fixes don't have unit tests — verify via dry-run output review

### Commit strategy
- Wave 1: single commit ("feat(execute): add SKIPPED op status + runtime support")
- Wave 2: single commit per agent or one combined ("fix(handlers): distinguish guard-clause skips from no-ops")
- Wave 3+: one commit per group

---

## What NOT to change

- The `[]` return for legitimate no-ops — don't over-correct. "Feature disabled" → `[]` is correct.
- The cascade-skip behavior itself — SKIPPED ops should cascade-skip dependents just like FAILED ops. Don't change the cascade logic, only the labeling.
- External API interfaces — this is all internal execute layer plumbing.
- The planner output format — the plan format doesn't change, only how handlers respond to missing deps.

---

## Open questions for next session

1. Should `SKIPPED` ops be retryable (like `FAILED`) or terminal? Current assumption: terminal (if a dep was missing, retrying won't help unless the dep is manually created).
2. Should the execution report show a SKIPPED section in the summary, or merge SKIPPED with FAILED? Recommendation: separate section — they mean different things operationally.
3. For `_resolve_agents()` (#15) — should a hunt group with 1 of 3 agents missing be SKIPPED entirely, or created with partial membership? Recommendation: created with partial membership + WARNING in op metadata. Don't block creation over a partial member list.
