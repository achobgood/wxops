# src/wxcli/migration/preflight/

Preflight checks that verify the Webex org is ready for the migration plan. Read-only — queries Webex via wxcli CLI subprocess calls, never modifies anything.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Data models (CheckStatus, CheckResult, PreflightResult, PreflightIssue, PreflightError), `_run_wxcli()` subprocess helper, `preflight_fingerprint()` |
| `checks.py` | 10 check functions — each takes store + fetched data, returns CheckResult (or tuple with decisions) |
| `runner.py` | PreflightRunner — fetches shared Webex data once, runs all checks, merges decisions |

## Architecture

```
wxcli cucm preflight
  → PreflightRunner.run()
    → _fetch() shared data (licenses, locations, numbers, people, trunks)
    → run 10 checks as pure functions of (store, fetched_data)
    → merge NUMBER_CONFLICT + DUPLICATE_USER decisions into store
    → return PreflightResult (overall PASS/WARN/FAIL/SKIP)
```

## The 10 Checks

Count derived from `runner.py`'s `all_checks` registry and asserted by
`tools/drift_check.py` check [17] — four different numbers (7, 8, 9, 8) were
claimed across this file, `runner.py` and `cucm-migrate/SKILL.md`, and none of
them was 10 (finding F17).

1. **User licenses** — enough Calling Professional licenses
2. **Workspace licenses** — enough Workspace licenses (matches API's `UserLicenseType.WORKSPACE`)
3. **Locations** — target locations exist in Webex + PSTN connection check per location
4. **Trunks** — no trunk name conflicts
5. **Feature entitlements** — AA/CQ/HG/Paging within known limits
6. **Number conflicts** — E.164 and extension collisions (produces NUMBER_CONFLICT decisions, skips same-owner)
7. **Duplicate users** — planned users already in Webex (produces DUPLICATE_USER decisions, 3 scenarios)
8. **Rate limit budget** — estimated migration duration from plan_operations
9. **E911 readiness** — Every user has a resolvable ECBN candidate (DIRECT_LINE or LOCATION_ECBN); no unresolved E911 decisions; extension-only users warn, missing candidates fail.
10. **Bulk device job support** — probes the bulk device job endpoint when the plan contains bulk ops; SKIPs when auth is unavailable. This is the check every prior count omitted.

### INCOMPLETE — a check that could not run

`CheckStatus.INCOMPLETE` is returned when a check's required Webex data was never
retrieved. `_fetch` records the failure against the dataset label, and
`_mark_incomplete_if_unfetched` replaces the check's verdict (keeping its display
name) for every check listed in `_CHECK_FETCH_DEPS`.

Before this existed, `_fetch` swallowed `PreflightError` and returned `[]`, so with
no token at all preflight reported `✓ PASS Number conflicts: No number/extension
conflicts` and `✓ PASS Duplicate users: No cross-system duplicate users` — the two
checks that exist to stop a live org being corrupted on execute (finding F06).
`_count_existing_features` had the same swallow and is now recorded too.

`INCOMPLETE` ranks above `WARN` and below `FAIL` in `_STATUS_PRIORITY`: a definite
failure is the more actionable message, but "we do not know" must still stop the
gate. Any decisions a check captured from unfetched data are discarded rather than
merged into the store.

## Key Design Decisions

- **Subprocess, not import** — Checks call `wxcli` via subprocess to reuse CLI auth, pagination, error handling
- **Scoped merge** — `merge_decisions(decision_types=["NUMBER_CONFLICT", "DUPLICATE_USER"], stage="preflight")` prevents stale-marking analyzer decisions
- **Same-owner dedup** — NUMBER_CONFLICT skips collisions where the existing owner has the same email as the planned user
- **Gated fetches** — When `--check` filter is set, only fetch the data needed for that check
- **Re-runnable** — State machine allows `PREFLIGHT → PREFLIGHT` and `PREFLIGHT_FAILED → PREFLIGHT`

## Tests

- `tests/migration/preflight/test_checks.py` — 38 unit tests for all check functions
- `tests/migration/preflight/test_runner.py` — 14 integration tests (mocked wxcli)

## Known Limitations

- PSTN connection check calls `wxcli pstn list-connection` per location — produces WARN (not FAIL) for locations without PSTN
- ~~`wxcli users list` callingData limitation~~ — FIXED: `users` is now an alias for the generated `people` command group, and the preflight runner passes `--calling-data true`
