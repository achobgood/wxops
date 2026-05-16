# Operations & Evolution — wxcli

## 1. Build and Test

### Building the Project

wxcli uses standard Python packaging with `pyproject.toml` as the single source of truth. There is no `Makefile`, no build script, no compilation step.

```bash
# Clone and install (editable mode)
git clone <repo-url>
cd webexCalling
pip install -e .
```

This installs the `wxcli` entry point (defined in `pyproject.toml` as `wxcli = "wxcli.main:app"`) and three runtime dependencies:

| Dependency | Role |
|-----------|------|
| `typer[all]>=0.9.0` | CLI framework (includes `rich` for table output) |
| `httpx>=0.27.0` | HTTP client for all Webex API calls |
| `pyyaml>=6.0` | YAML parsing for `field_overrides.yaml` at generation time |

Version is dynamic via `setuptools-scm` — derived from the latest git tag and written to `src/wxcli/_version.py`. There are no pinned lockfiles; `requirements.txt` was removed (it was a stale pip-compile artifact that referenced the no-longer-used `wxc-sdk`).

**Python version:** `pyproject.toml` declares `>=3.14`. All skill and agent invocations hardcode `python3.14`. CI tests on 3.11 and 3.12 (both pass), so the runtime constraint is softer than declared — the codebase uses `str | None` union syntax (3.10+) but no 3.14-specific features have been identified.

### Test Framework

Tests use `pytest` with `pytest-asyncio` (for the migration engine's async execution layer). Configuration lives in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
asyncio_mode = "auto"
markers = ["live: requires a live Webex API token"]
```

**Running tests:**

```bash
# Standard (excludes live API tests)
pytest tests/ -m "not live" -v --tb=short

# Include live API tests (needs WEBEX_ACCESS_TOKEN)
pytest tests/ -v --tb=short
```

**Test organization (226 files):**

| Directory | Scope | Count |
|-----------|-------|-------|
| `tests/` (root) | Core CLI, auth, config, generator, cleanup, smoke | ~25 files |
| `tests/migration/` | Full migration pipeline | ~50+ files |
| `tests/migration/execute/` | Execution engine, handlers, batch, planner | Subdir with own `conftest.py` |
| `tests/migration/report/` | Report generation | Subdir with own `conftest.py` |
| `tests/migration/transform/` | Normalization, mapping, analysis | Subdir |
| `tests/migration/transferability/` | Runbook/KB coverage validation | Subdir with own `conftest.py` |
| `tests/migration/advisory/` | Advisory pattern generation | Subdir |
| `tests/migration/preflight/` | Preflight check validation | Subdir |
| `tests/org_health/` | Org health assessment checks | Subdir with own `conftest.py` |
| `tests/tools/` | Generator, parser, renderer | Subdir |
| `tests/fixtures/` | Shared test data | Subdir |

**Key shared fixtures** (`tests/conftest.py`):
- `runner` — `typer.testing.CliRunner` for command invocation
- `mock_env_token` — sets `WEBEX_ACCESS_TOKEN` to a fake token (sufficient for `--help` and structural tests)

**Test counts by subsystem:** Migration: 2778 passing. Org health: 76 passing. Core CLI + generator: remainder.

### What CI Does

GitHub Actions (`.github/workflows/ci.yml`) runs on push to `main` and on PRs against `main`:

1. Matrix: Python 3.11 and 3.12 on `ubuntu-latest`
2. `pip install -e .` + `pip install pytest`
3. `pytest tests/ -m "not live" -v --tb=short`

That's it. No linting, no type checking, no coverage gates, no deployment step. CI is a correctness gate, not a quality gate. The `live` marker separates tests that hit the real Webex API (require a token, not safe for CI) from pure-logic tests.

**Smoke testing** (`tests/test_smoke.sh`) is a manual script for verifying a live-connected install: runs `wxcli --version`, `wxcli whoami`, and list commands for locations/users/licenses/numbers with `--limit 5`. Not wired into CI.

### Manual Operations a Developer Needs to Know

#### Regenerating Commands from OpenAPI Specs

When Cisco updates their API specs, or when the generator pipeline changes:

```bash
# Pull latest specs from GitHub
python3.14 tools/update-specs.py          # downloads + reports diffs
python3.14 tools/update-specs.py --check  # exit 1 if specs are stale

# Regenerate all (order matters — CC before admin/meetings due to tag collisions)
PYTHONPATH=. python3.14 tools/generate_commands.py --spec specs/webex-cloud-calling.json --all
PYTHONPATH=. python3.14 tools/generate_commands.py --spec specs/webex-device.json --all
PYTHONPATH=. python3.14 tools/generate_commands.py --spec specs/webex-messaging.json --all
PYTHONPATH=. python3.14 tools/generate_commands.py --spec specs/webex-ucm.json --all
PYTHONPATH=. python3.14 tools/generate_commands.py --spec specs/webex-contact-center.json --all
PYTHONPATH=. python3.14 tools/generate_commands.py --spec specs/webex-admin.json --all
PYTHONPATH=. python3.14 tools/generate_commands.py --spec specs/webex-meetings.json --all

# Regenerate a single tag
PYTHONPATH=. python3.14 tools/generate_commands.py --spec specs/webex-cloud-calling.json --tag "Auto Attendant"
```

**Why order matters:** The Contact Center spec has "Data Sources" and "Meeting Site" tags that collide with admin and meetings specs. CC versions are registered as `cc-data-sources` and `cc-site`. Regenerating admin/meetings *after* CC restores the correct non-prefixed files.

**After regenerating:** New command files must be manually registered in `main.py` via `app.add_typer()`. The generator does not auto-register.

**Never hand-edit generated files.** Fix display or naming issues via `tools/field_overrides.yaml` and regenerate. See `tools/CLAUDE.md` for the full generator rule set.

#### Running Migration Against a Real CUCM

The migration pipeline requires SSH and AXL (SOAP) access to a CUCM cluster:

```bash
# Discover CUCM state (requires cluster IP, AXL credentials, SSH access)
wxcli cucm discover --host 10.201.123.107 --username admin --password <pw> --project myproject

# Normalize, map, analyze
wxcli cucm normalize --project myproject
wxcli cucm map --project myproject
wxcli cucm analyze --project myproject

# Export deployment plan
wxcli cucm export --project myproject

# Run preflight checks
wxcli cucm preflight --project myproject
```

State is persisted to SQLite in the project directory. Each command is idempotent — safe to re-run. The full pipeline is documented in `.claude/rules/cucm-migration.md`.

---

## 2. Deployment and Runtime

### Distribution

wxcli is a private tool, not published to PyPI or any package registry. Installation is from the git repo via `pip install -e .`. There is no homebrew formula, no Docker image, no binary distribution.

### Runtime Requirements

| Requirement | Details |
|------------|---------|
| Python | >= 3.14 declared; 3.11+ works in practice |
| OS | macOS, Linux (standard library + cross-platform deps) |
| Network | HTTPS access to `webexapis.com` (Calling/admin), `api.wxcc-{region}.cisco.com` (Contact Center) |
| Auth | Webex API token (personal, admin, service app, or OAuth) |
| For CUCM migration | SSH + AXL access to CUCM cluster |

### Configuration

All runtime config lives in `~/.wxcli/config.json`:

```json
{
  "profiles": {
    "default": {
      "token": "NjY3...",
      "expires_at": "2026-05-03T22:00:00Z",
      "org_id": "Y2lzY29...",
      "org_name": "Acme Corp",
      "cc_region": "us1"
    }
  }
}
```

**Token resolution priority** (`auth.py:67-77`):
1. `WEBEX_ACCESS_TOKEN` environment variable
2. `WEBEX_TOKEN` environment variable
3. `~/.wxcli/config.json` saved token

**Key configuration commands:**
- `wxcli configure` — save token, auto-detects multi-org (partner) tokens
- `wxcli switch-org <org_id>` — change active target org for partner admins
- `wxcli clear-org` — revert to single-org behavior
- `wxcli set-cc-region <region>` — set Contact Center region (us1, eu1, eu2, anz1, ca1, jp1, sg1)
- `wxcli whoami` — show authenticated identity, org, token expiry

**Partner multi-org:** When an admin token has access to multiple orgs, 668 of 804 generated commands auto-inject `orgId` from the saved config. No flag needed — it's transparent.

---

## 3. Debugging Playbook

### Debug Flags

```bash
# Enable debug logging (sets Python logging to DEBUG level)
wxcli <any-command> --debug

# Verbose mode for migration commands
wxcli cucm discover --verbose
```

`--debug` activates `logging.basicConfig(level=logging.DEBUG)` in `auth.py:82-84`. This shows the full HTTP request/response cycle. Migration commands additionally support `--verbose` which sets INFO-level logging with a condensed format.

### Where Logs Go

Logs go to stderr via Python's `logging` module. There is no persistent log file. To capture:

```bash
wxcli locations list --debug 2>debug.log
```

### Error Diagnosis

The centralized error handler (`errors.py:48-68`) maps Webex API error codes to actionable tips:

| Error Code | Symptom | Tip |
|-----------|---------|-----|
| 4003 | "Target user not authorized" | Needs user-level OAuth, not admin token |
| 4008 | 404 on person settings | Target user needs Webex Calling license |
| 9601 | Call control fails | Needs user-level OAuth |
| 25008 | Complex body rejected | Use `--json-body` for nested fields |
| 25409 | 405 on workspace settings | Needs Professional license, not Basic |
| 28018 | CX queue operation fails | CX Essentials not enabled |
| Any 403 on `wxcc` URLs | CC commands fail | Needs CC-scoped OAuth (`cjp:config_read`) |

HTML error responses are automatically truncated to the `<title>` or `<h1>` content.

### First-Time Debugger's Guide

**"Command not found" or wrong command name:**
Two path families exist for person settings: `/people/{id}/features/` (classic) vs. `/telephony/config/people/{id}/` (newer). Names may differ. Always run `wxcli <group> --help` first.

**"Error: No token found":**
Run `wxcli configure` or set `WEBEX_ACCESS_TOKEN`. Token expires after 12 hours; `wxcli whoami` shows remaining time.

**Generated command returns unexpected data:**
Check `field_overrides.yaml` for the endpoint — table columns, response key paths, and display settings are all controlled there. If the API response shape changed upstream, the override may be stale.

**Migration command fails mid-pipeline:**
State is in SQLite. Commands are idempotent. Re-run the failed command. Check `--verbose` output for the specific API call that failed. The store preserves all intermediate state — you won't lose progress.

**Cleanup fails with 409 (resource in use):**
Resources have dependency ordering. `wxcli cleanup` handles this automatically with a 13-layer deletion cascade. If cleaning up manually, delete in reverse dependency order (users before locations, features before users). See `.claude/rules/cleanup.md`.

**Contact Center commands return 403:**
Standard admin tokens (PATs) don't carry `cjp:config` scopes. Create an OAuth integration with `cjp:config_read` and `cjp:config_write` explicitly selected, then re-authenticate.

---

## 4. Areas of Active Change

Based on git history (779 commits, all within 2026):

### Currently Active (May 2026)

**aap-demo (Remotion video project)** — the current branch (`feat/aap-remotion-demo`) with 16 recent commits. A separate `aap-demo/` directory containing a Remotion-based video composition with scenes, TTS narration, and audio mixing. This is parallel to the core CLI work.

### Recently Stabilized (April 2026)

**Migration execution pipeline** — the highest-churn hand-coded subsystem (610+ directory-level changes across `execute/`, `transform/`, `report/`, `advisory/`, `cucm/`). All 11 build phases are complete with 2778 tests. The remaining work is Phase 11-revised (migrate skill) and Phase 5 (integration testing, blocked on Phase 11).

**Org health assessment** — shipped in April 2026 as a compact module (`src/wxcli/org_health/`, 5 files, ~1500 lines, 76 tests). Collects org state via wxcli, runs 18 deterministic checks across 4 categories, generates an HTML report.

**Query-live skill** — 7 commits building domain modules for read-only natural language queries against live org state.

### Stable (Low Churn)

**Core CLI framework** (`auth.py`, `config.py`, `errors.py`, `output.py`, `main.py`) — foundational code that changes only when new command groups are wired in. Last substantive changes were for partner multi-org support and error tip expansion.

**Generated commands** (`src/wxcli/commands/`) — 208 files, regenerated from specs but structurally stable. Changes only when Cisco updates the OpenAPI specs (last refresh: April 27, 2026).

**Code generator pipeline** (`tools/`) — mature and incrementally extended. `field_overrides.yaml` (25 changes) and `command_renderer.py` (25 changes) are the most active parts, both driven by per-endpoint UX fixes.

### Most Frequently Changed Files (Since March 2026)

| Changes | File | Why |
|---------|------|-----|
| 65 | `CLAUDE.md` | Project instructions evolve as features ship |
| 39 | `migration/execute/handlers.py` | Execution handler logic — the core migration engine |
| 34 | `migration/execute/planner.py` | Dependency analysis and operation planning |
| 29 | `.claude/agents/wxc-calling-builder.md` | Agent prompt continuously tuned from operational experience |
| 28 | `migration/models.py` | Canonical data models — stabilizing |
| 26 | `main.py` | New command groups wired in |
| 25 | `tools/field_overrides.yaml` | Generator overrides for display and naming |

---

## 5. Known Technical Debt

### Essentially Zero Code-Level Debt Markers

A sweep of `TODO`, `FIXME`, `HACK`, `WORKAROUND`, and `XXX` across the Python source returned 14 hits — all are either data constants (the `NOT_MIGRATABLE_WORKAROUNDS` dict mapping CUCM features to manual workaround descriptions) or CUCM route pattern literals (`XXXX` is a wildcard pattern, not a marker). No genuine unfinished-work markers exist in the source.

### Structural Debt

**Three legacy hand-written command files** (`locations.py`, `numbers.py`, `licenses.py`) predate the generator. They miss generator improvements (auto-column detection, orgId injection pattern, output formatting). Each one is a drift risk — changes to the generator don't propagate to them. `tools/CLAUDE.md` acknowledges this and warns against creating new hand-written files.

**Stale wxc-sdk references.** The `wxc-sdk` dependency was removed from `pyproject.toml` and no source file imports it, but references persist in documentation: `docs/reference/wxc-sdk-patterns.md` (historical SDK patterns), several skills with `from wxc_sdk import ...` code examples, and `tools/CLAUDE.md`. A cleanup prompt exists at `docs/prompts/remove-wxc-sdk-references.md` but has not been fully executed.

**Python 3.14 version constraint.** `pyproject.toml` declares `>=3.14` but the codebase uses no 3.14-specific features. CI tests on 3.11 and 3.12. All skill and agent invocations hardcode `python3.14`. This limits adoption without providing value — it should either be relaxed to 3.11+ or a 3.14-specific feature should be identified.

**Two independent HTTP stacks.** The CLI uses synchronous `httpx` via `WebexSession`; the migration engine uses async `aiohttp` with its own connection management, retry logic, and rate limiting. There is no shared HTTP infrastructure between them. This emerged organically (migration was built after CLI was stable and needed async), not as a deliberate decoupling decision.

**No persistent logging.** All output goes to stderr. There's no log file, no structured logging, no log rotation. For a CLI tool this is normal; for the migration engine processing hundreds of API calls across multi-hour runs, the lack of a persistent audit trail is a gap. Migration state is in SQLite, which partially compensates.

**80 plan files in `docs/plans/`.** These are artifacts of the iterative design process (execution reports, test project iterations, architecture specs). Most are historical. The active tracking is concentrated in `docs/plans/TODO.md` and `docs/plans/cucm-migration-roadmap.md`. The rest is context that served its purpose during construction.

### Deprecated Patterns (Managed)

These are deprecated with clear dates and retained for serialization compatibility with stored migration projects:

| Pattern | Deprecated | Replacement |
|---------|-----------|-------------|
| `DeviceConvertibility` enum (`models.py:92`) | 2026-04-15 | Device classification system |
| `auto_apply` marker in migration models (`models.py:190`) | 2026-04-15 | Removed from new decision paths |
| `DEVICE_FIRMWARE_CONVERTIBLE` decisions (`recommendation_rules.py:27`) | 2026-04-15 | No longer generated; kept for rendering old projects |
| Legacy CSS class aliases (`report/styles.py`) | Active | Kept for chart test compatibility |

Several upstream Webex API fields are also deprecated by Cisco and marked in the generated commands: `--channel-types` in CC queues/entry points, caller ID first/last name in location voicemail, `--workspace-location-id` in devices.

---

## 6. Roadmap Implications

### What's Coming

Based on `docs/plans/TODO.md`, the transferability plans, and code patterns:

**Phase 11-revised (Migrate Skill)** is the next concrete milestone — wiring the full migration pipeline into the Claude Code skill system so the builder agent can execute migrations end-to-end. All prerequisites are complete. This is the final piece before the migration tool is considered feature-complete.

**Phase 5 (Integration Testing)** is blocked on Phase 11. Once the skill is wired up, end-to-end integration tests will exercise the full pipeline from discovery to execution against a live environment.

**Transferability (Phases 2-3)** — multiple planning docs (`transferability-phase-2*.md`, `transferability-phase-3*.md`) describe making the migration tool portable beyond the original author: improved runbooks, knowledge base docs, and guide material. This is the path from "works for the builder" to "works for anyone."

### What New Code Should Accommodate

**Skill-driven execution.** The project is converging on a pattern where all operations flow through Claude Code skills and agents rather than raw CLI invocation. New capabilities should be designed as skill-invokable workflows, not standalone scripts.

**Generated-first commands.** Any new Webex API coverage should go through the generator pipeline (`openapi_parser.py` → `command_renderer.py` → `field_overrides.yaml`), not hand-written. The three legacy hand-written files are technical debt, not a template.

**Multi-org by default.** Partner multi-org support is deeply embedded — 668 commands auto-inject `orgId`. New commands that accept `orgId` should use the `auto_inject_from_config` mechanism in `field_overrides.yaml`, not manual parameter handling.

**Async for bulk operations.** The migration engine established the pattern: sync `httpx` for single-command CLI work, async `aiohttp` with rate limiting for batch operations. Any new bulk-operation module should follow the async pattern with the existing `rate_limiter.py`.

**SQLite for stateful workflows.** The migration pipeline's `store.py` (SQLite-backed state management) is the proven pattern for multi-step workflows that need persistence across invocations. New stateful features (e.g., org health history, deployment tracking) should adopt a similar approach rather than inventing their own persistence.

**Reference docs as ground truth.** The project enforces a strict grounding rule: never answer Webex questions from training data alone. New domain coverage must be accompanied by a reference doc in `docs/reference/` and optionally a skill in `.claude/skills/`. The doc-and-skill pairing is the project's core architectural pattern for maintaining accuracy.
