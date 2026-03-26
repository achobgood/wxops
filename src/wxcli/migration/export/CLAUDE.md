# export/ — Phase 09 → 12b: Export Layer

Generates summary deployment plans and data exports from the SQLite migration store.

Phase 12b removed the command_builder (static CLI string generation) in favor of
skill-delegated execution. The deployment plan is now summary-only — no CLI commands,
no placeholders. The cucm-migrate skill queries the DB for operation metadata and
delegates to domain skills at runtime.

## Files

| File | Purpose |
|------|---------|
| `deployment_plan.py` | Generates 8-section summary plan for admin review (no CLI commands) |
| `json_export.py` | Full JSON export (objects, decisions, cross-refs, plan ops/edges) |
| `csv_export.py` | CSV decisions export for stakeholder review |

## Key Design Decisions

### Summary-only deployment plan (Phase 12b)

The deployment plan no longer contains CLI commands or `{STEP_N_ID}` placeholders.
It shows: objective, prerequisites, resource summary (Webex types only), decisions
made, batch execution order, estimated impact, rollback strategy, and approval.
The cucm-migrate skill uses `wxcli cucm next-batch` to get operation metadata and
delegates execution to domain skills.

### --json-body bypasses required flags (Phase 12b)

The generator now makes all required body fields `typer.Option(None)` when
`--json-body` is present. Runtime validation checks for missing required fields
only when `--json-body` is NOT used. This allows domain skills to pass
`--json-body '{"name":"X",...}'` without also specifying `--name X`.

### License assignment at create time

`wxcli users update` does NOT have a `--license` flag. The `--license` flag only
exists on `wxcli users create`. License and extension are included in the
`user:create` step.

### Feature delete commands need LOCATION_ID

All feature delete commands require `LOCATION_ID RESOURCE_ID` as two positional
arguments. Rollback uses `get_completed_ops_for_rollback()` which resolves the
location_webex_id from dependencies.

## Tests

- `tests/migration/export/test_deployment_plan.py` — summary plan tests
