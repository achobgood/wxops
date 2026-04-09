# Layer 3 Benchmark Fixture

SQLite migration store and pre-recorded tool responses for the Layer 3
efficiency benchmark harness (`tools/layer3_benchmark.py`).

## Design Intent

20 decisions across 4 categories:
- **Recommended (4):** D0001-D0004 — known recommendation values for accuracy testing
- **Dissent triggers (2):** D0005-D0006 — activate KB dissent protocol testing
- **Gotcha-path (3):** D0007 (null address), D0008 (token expiry via mock), D0009 (preflight fail via mock)
- **Normal (11):** D0010-D0020 — fill out the review flow

## Regenerating

If the MigrationStore schema changes (new columns, changed field names):
```
PYTHONPATH=. python3.11 tools/build_benchmark_fixture.py
```

Then validate:
```
PYTHONPATH=. pytest tests/migration/transferability/test_benchmark_fixture.py -v
```

The regeneration script does NOT require the cucm-testbed-2026-03-24 project
to be present — all decisions are hardcoded in build_benchmark_fixture.py.

## Tool Responses

`tool_responses/` contains pre-recorded JSON for Bash tool calls. Format:
```json
{"stdout": "...", "returncode": 0}
```

The harness maps each expected `wxcli cucm <cmd>` to a fixture file by
command pattern. See `tools/layer3_benchmark.py` TOOL_RESPONSE_MAP.

## Maintenance Owner

Claude Code — via `tools/build_benchmark_fixture.py`. When the schema
changes, run the script and commit the updated migration.db.
