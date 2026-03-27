# src/wxcli/migration/preflight/

Preflight checks that verify the Webex org is ready for the migration plan. Read-only — queries Webex via wxcli CLI subprocess calls, never modifies anything.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Data models (CheckStatus, CheckResult, PreflightResult, PreflightIssue, PreflightError), `_run_wxcli()` subprocess helper, `preflight_fingerprint()` |
| `checks.py` | 8 check functions — each takes store + fetched data, returns CheckResult (or tuple with decisions) |
| `runner.py` | PreflightRunner — fetches shared Webex data once, runs all checks, merges decisions |

## Architecture

```
wxcli cucm preflight
  → PreflightRunner.run()
    → _fetch() shared data (licenses, locations, numbers, people, trunks)
    → run 8 checks as pure functions of (store, fetched_data)
    → merge NUMBER_CONFLICT + DUPLICATE_USER decisions into store
    → return PreflightResult (overall PASS/WARN/FAIL/SKIP)
```

## The 8 Checks

1. **User licenses** — enough Calling Professional licenses
2. **Workspace licenses** — enough Workspace licenses (matches API's `UserLicenseType.WORKSPACE`)
3. **Locations** — target locations exist in Webex + PSTN connection check per location
4. **Trunks** — no trunk name conflicts
5. **Feature entitlements** — AA/CQ/HG/Paging within known limits
6. **Number conflicts** — E.164 and extension collisions (produces NUMBER_CONFLICT decisions, skips same-owner)
7. **Duplicate users** — planned users already in Webex (produces DUPLICATE_USER decisions, 3 scenarios)
8. **Rate limit budget** — estimated migration duration from plan_operations

## Key Design Decisions

- **Subprocess, not import** — Checks call `wxcli` via subprocess to reuse CLI auth, pagination, error handling
- **Scoped merge** — `merge_decisions(decision_types=["NUMBER_CONFLICT", "DUPLICATE_USER"], stage="preflight")` prevents stale-marking analyzer decisions
- **Same-owner dedup** — NUMBER_CONFLICT skips collisions where the existing owner has the same email as the planned user
- **Gated fetches** — When `--check` filter is set, only fetch the data needed for that check
- **Re-runnable** — State machine allows `PREFLIGHT → PREFLIGHT` and `PREFLIGHT_FAILED → PREFLIGHT`

## Tests

- `tests/migration/preflight/test_checks.py` — 36 unit tests for all check functions
- `tests/migration/preflight/test_runner.py` — 13 integration tests (mocked wxcli)

## Known Limitations

- PSTN connection check calls `wxcli pstn list-connection` per location — produces WARN (not FAIL) for locations without PSTN
- ~~`wxcli users list` callingData limitation~~ — FIXED: `users` is now an alias for the generated `people` command group, and the preflight runner passes `--calling-data true`
