# Behavioral Characteristics — wxcli

How the system behaves at runtime: failure modes, fragility points, performance characteristics, state management, and known issues with workarounds.

---

## 1. Failure Modes

### 1a. CLI Framework (`src/wxcli/`)

#### (a) Handled Gracefully

| Failure | Code Path | Behavior |
|---------|-----------|----------|
| Missing token | `auth.py:86-89` | Prints "No token found" + `typer.Exit(1)` |
| Known API error codes (4003, 4008, 9601, 25008, 25409, 28018) | `errors.py:10-17, 48-68` | Error message + actionable tip |
| CC 403 with wxcc in URL | `errors.py:63-65` | Detects CC scope issue, prints OAuth tip |
| HTML error responses (WAF/gateway errors) | `errors.py:37-45` | Extracts `<title>` or `<h1>`, truncates HTML |
| Paginated responses with `Link` header | `auth.py:52-58` | Follows `rel="next"` links until exhausted |
| Token in multiple env vars | `auth.py:67-77` | Priority: `WEBEX_ACCESS_TOKEN` → `WEBEX_TOKEN` → config file |

#### (b) Useful Error, Requires User Action

| Failure | Code Path | Behavior |
|---------|-----------|----------|
| Non-success HTTP response | `auth.py:22-42` | Raises `WebexError(response.text)` — full response body exposed |
| Unknown error code | `errors.py:66-67` | Prints truncated error, no tip — user must interpret |
| Token expired | `main.py:51-65` | Warns at startup (if parseable) — doesn't block |
| CC wrong region | `config.py:89-93` | Falls back to `us1` — user gets 401 or wrong data |

#### (c) Confusing Errors

| Failure | Code Path | What Happens |
|---------|-----------|--------------|
| JSON parse failure on success response | `auth.py:25, 31, 37, 43` | `response.json()` raises if body isn't JSON — unhelpful traceback |
| Error code 4003 + "Target user not authorized" in body | `errors.py:53-54` | Special-case logic clears the code → falls through to generic handler (inverted check is non-obvious) |
| `orgId` silently omitted for partner tokens | Generated commands via `config.py:28-31` | `get_org_id()` returns `None` → query param missing → API returns wrong org's data |
| Base64 decode failure on Spark ID | `config.py:48-55` | Returns the raw encoded ID — CC API gets wrong org ID silently |

#### (d) Silent Failures

| Failure | Code Path | Impact |
|---------|-----------|--------|
| API listing returns error during cleanup | `cleanup.py:250-278` | Returns empty list — operator proceeds with incomplete inventory, thinks org is clean |
| Empty response body on success | `auth.py:25, 31, 37, 43` | Returns `{}` — downstream code treats missing fields as None |
| Config file missing | `config.py:8-9` | Returns `{"profiles": {}}` — no warning |
| Token expiry not parseable | `main.py:64` | `except ValueError: pass` — expiry check silently skipped |
| User has single-org token | `main.py:95` | Returns without message if `len(items) <= 1` |
| Location-scoped listing with no location_ids | `cleanup.py:237-238` | Returns `[]` — no resources enumerated, no warning |

---

### 1b. Cleanup Subsystem (`src/wxcli/commands/cleanup.py`)

#### (a) Handled Gracefully

| Failure | Code Path | Behavior |
|---------|-----------|----------|
| Location delete 409 (resources still attached) | `cleanup.py:694-732` | Retries up to 5× with 60s sleep between |
| CCP-integrated numbers | `cleanup.py:851-870` | Detects `ERR.V.TRM.TMN60004`, marks as CCP-blocked (not an error) |
| Concurrent deletion via ThreadPool | `cleanup.py:6` | ThreadPoolExecutor with configurable `max_concurrent` |

#### (b) Useful Error, Requires User Action

| Failure | Code Path | Behavior |
|---------|-----------|----------|
| CCP-integrated error on location | `cleanup.py:715` | Short-circuits retry loop, reports CCP gate |
| 3 consecutive number-batch failures | `cleanup.py:881-891` | Aborts remaining numbers, reports which were skipped |

#### (c) Confusing Errors

| Failure | Code Path | What Happens |
|---------|-----------|--------------|
| Delete fails for non-WebexError reason | `cleanup.py:368-375` | Catches all `Exception`, returns `DeleteResult(success=False, error=str(e))` — no distinction between network failure and logic error |
| Blocker probe failures during location delete | `cleanup.py:584, 615, 628` | `except Exception: pass` — error context lost, user sees generic failure |

#### (d) Silent Failures

| Failure | Code Path | Impact |
|---------|-----------|--------|
| Resource listing failure | `cleanup.py:250-278` | Empty list returned, no aggregate error reporting — proceeds to delete phase with partial inventory |
| Numbers not in inventory | `cleanup.py:305-306` | `continue` — numbers populated separately, but if `build_number_inventory` also fails, no numbers deleted before location removal |

---

### 1c. Migration Execution Engine (`src/wxcli/migration/execute/`)

#### (a) Handled Gracefully

| Failure | Code Path | Behavior |
|---------|-----------|----------|
| 429 Too Many Requests | `engine.py:199-203` | Reads `Retry-After` header, sleeps, retries up to 5× |
| Network errors (aiohttp.ClientError) | `engine.py:222-229` | Exponential backoff (2^attempt seconds), up to 5 retries |
| 409 Conflict on create | `engine.py:939-951` | Searches for existing resource by name/email, reuses ID |
| Handler returns SkippedResult | `engine.py:902-911` | Op marked `skipped`, cascade skip to dependents |
| Handler returns empty list | `engine.py:912-916` | Op marked `completed` (legitimate no-op) |
| In-progress ops on restart | `engine.py:148-157` | `reset_in_progress()` resets to `pending` for resumability |
| Cascade skip on failure | `runtime.py:235-274` | All hard-edge dependents recursively marked `skipped` |
| Undo cascade on retry success | `runtime.py:277-300` | Cascade-skipped dependents reset to `pending` |

#### (b) Useful Error, Requires User Action

| Failure | Code Path | Behavior |
|---------|-----------|----------|
| No handler in registry | `engine.py:896-899` | Op marked `failed` with clear message: "No handler for X:Y" |
| Create response has no ID | `engine.py:240-245` (Fix #18) | Fails explicitly instead of silently succeeding |
| Malformed bulk job ID | `engine.py:263-281` (Fix #8) | Raises `ValueError` immediately instead of 404 polling loop |
| Bulk job fetch error vs empty | `engine.py:24-31` (Fix #6) | `JobErrorFetchFailed` distinguishes "can't read errors" from "zero errors" |
| All-REQUIRES cycle | `dependency.py:379-452` | Hard error — reports cycle, requires human intervention |

#### (c) Confusing Errors

| Failure | Code Path | What Happens |
|---------|-----------|--------------|
| 409 on unsupported resource type | `engine.py:952-955` | Only 7 types have auto-recovery; others show "409" error without explaining the resource already exists |
| Multi-call op fails on sub-call N>1 | `engine.py:183-220` | First call succeeded (wrote to API), subsequent call failed — partial state written, op marked `failed` but first call's side effect persists |
| Bulk job timeout (600s) | `engine.py:45-50` | TimeoutError — user must investigate job status manually |

#### (d) Silent Failures

| Failure | Code Path | Impact |
|---------|-----------|--------|
| Partial bulk failure (not yet wired) | execute/CLAUDE.md | `run_batch_ops` doesn't populate `fallback_context` — partial bulk failures treated as total failures |
| Unresolved members in monitoring_list | `handlers.py` (monitoring_list:configure) | Silently omits unresolved members with only a warning log — no user-visible notification |
| MOH/Announcement placeholders | `handlers.py:1028-1040` | Return `[]` — ops auto-complete but no actual config applied |
| FedRAMP `rebuildPhones` unsupported | execute/CLAUDE.md | No runtime detection — operator must know to set `bulk_device_threshold=999999` |

---

### 1d. Command Generation (`tools/`)

#### (d) Silent Failures (generation-time)

| Failure | Code Path | Impact |
|---------|-----------|--------|
| OpenAPI spec uses unexpected content-type | `openapi_parser.py:42-44` | Only handles `application/json` and `charset=UTF-8` variant — other content types produce empty bodies |
| Response list key mismatch | `command_renderer.py:292, 338` | Falls through chain: `items` → `data` → raw list → `[]` — user sees empty output |
| Tag collision across specs | `generate_commands.py:161-163` | Later spec overwrites earlier — depends on regen order being correct |

---

## 2. Fragility Map

### High-Risk (Small Change Likely to Break Things)

| Area | What to Preserve | Why |
|------|-----------------|-----|
| **OpenAPI spec structure** | `$ref` resolution with `#/` separator, `allOf` merging, `200` status responses only | Parser has no fallback for structural changes — silent misparse |
| **Base URL constants** | `command_renderer.py:5-19` — hardcoded in 200+ generated files | Any URL change requires full regeneration of all command files |
| **`orgId` injection pattern** | `command_renderer.py:90-97` — `get_org_id()` called in every generated command | Silent behavior change if function signature or return semantics change |
| **Response key detection** | `openapi_parser.py:181-194` — `response_list_key` from schema | Wrong key → pagination silently yields nothing |
| **`main.py` registration block** (lines 143-509) | One `from ... import` + one `app.add_typer()` per command group, exact ordering | Missing or duplicate registration → CLI silently drops commands |
| **HANDLER_REGISTRY keys** | `(resource_type, op_type)` tuples in `handlers.py` | Typo in either string → "No handler" failure at execution time, not at import time |
| **TIER_ASSIGNMENTS constants** | `execute/__init__.py` | Must stay synchronized with HANDLER_REGISTRY — no compile-time check |
| **Cascade skip logic** | `runtime.py:235-274` — recursive dependency walk | Off-by-one in edge traversal orphans entire subtrees |
| **Deletion layer order** | `cleanup.py:195-208` | Wrong order → 409 cascades (resources reference each other) |
| **CC base URL placeholder** | `{cc_base_url}` in generated CC commands | Must resolve at runtime via `get_cc_base_url()` — if placeholder leaks to HTTP client, DNS resolution of literal string crashes |

### Medium-Risk

| Area | What to Preserve | Why |
|------|-----------------|-----|
| **Field overrides YAML** | `tools/field_overrides.yaml` — 27KB of per-endpoint customizations | Controls which params are CLI args vs. auto-injected; wrong override silently omits params |
| **CLI param naming** | `_safe_param_name()` — maps API camelCase to CLI kebab-case | Changing the mapping breaks backwards compatibility for all users |
| **Dependency graph edge types** | `DependencyType` enum values: REQUIRES, CONFIGURES, SOFT | Cycle breaker selects which edges to cut based on type — wrong type assignment can produce unbreakable cycles |
| **State machine transitions** | `state.py:42-58` — `VALID_TRANSITIONS` dict | Adding a state without wiring transitions locks the project in a dead state |
| **Bulk serialization constraint** | `SERIALIZED_RESOURCE_TYPES` list | Removing a type from this list → concurrent bulk submissions → Webex rejects (one-job-per-org) |

### Low-Risk (Safe to Change)

| Area | Why Safe |
|------|----------|
| Individual handler function bodies | Pure functions with clear contracts — only affect that one resource type |
| Test files | No runtime dependency |
| Advisory patterns (`advisory/`) | Static recommendation text — no execution path dependency |
| Report generation (`report/`) | Read-only against store, produces HTML — no side effects |
| Knowledge base docs (`docs/knowledge-base/`) | Read by agent at runtime, not imported |
| CLI help text and descriptions | Display-only |
| Logging messages | Observability only, no logic dependency |

### Patterns to Preserve When Adding New Code

1. **New command group:** Must add both `from wxcli.commands.X import app` AND `app.add_typer(X_app, name="x")` in `main.py`
2. **New handler:** Must update 4 locations — `handlers.py` (function + HANDLER_REGISTRY), `__init__.py` (TIER_ASSIGNMENTS + API_CALL_ESTIMATES), `planner.py` (_EXPANDERS)
3. **New resource type in cleanup:** Must add to `RESOURCE_TYPES` dict AND insert into `DELETION_LAYERS` at correct position
4. **New migration state:** Must add to both `ProjectState` enum AND `VALID_TRANSITIONS` dict
5. **New cross-object dependency:** Must add to `_CROSS_OBJECT_RULES` in `dependency.py` AND verify no new cycles introduced
6. **New spec for generation:** Must update regeneration order (CC → admin → meetings) to avoid tag collision

---

## 3. Performance Characteristics

### 3a. CLI Commands (Individual)

| Operation | Performance | Bottleneck |
|-----------|-------------|-----------|
| Single API call (list/show/create) | ~200-800ms | Network RTT to `webexapis.com` |
| Paginated list (large org, 1000+ items) | 2-10s | Sequential page fetches, no parallelism in `follow_pagination` |
| Cleanup inventory build | 15-60s for full org | Sequential listing of 13 resource types × N locations |
| Cleanup deletion | 30s-5min per layer | ThreadPoolExecutor(max_concurrent=5), limited by API rate limits |
| Location deletion | Up to 5min per location worst case | 5 retries × 60s sleep on 409 |

### 3b. Migration Execution Engine — Performance Under Load

| Metric | Value | Source |
|--------|-------|--------|
| **Concurrency ceiling** | 20 concurrent requests (semaphore) | `engine.py:869` |
| **Effective throughput** | ~100 requests/minute sustained | Empirical; Webex 429 threshold |
| **Batch timing estimate** | `api_calls / 100` minutes | `batch.py:73-81` |
| **Bulk job polling** | Every 5s, max 600s timeout | `engine.py:45-50` |
| **Retry overhead** | 2^N seconds per network error (max 16s) | `engine.py:224` |
| **429 backoff** | `Retry-After` header value (typically 5s) | `engine.py:200-202` |

**Scaling characteristics:**

| Migration Size | Estimated Duration | Bottleneck |
|----------------|-------------------|-----------|
| Small (50 users, 1 location) | 3-8 minutes | Tier ordering overhead |
| Medium (200 users, 5 locations) | 15-30 minutes | Rate limiting (429s) at tier 2-3 |
| Large (500+ users, 10+ locations) | 45-90 minutes | Bulk job polling time + rate limiting |
| Enterprise (2000+ users) | 2-4 hours | Serialized bulk jobs (one at a time per org) |

**Known bottlenecks:**

1. **Serialized bulk jobs** (`engine.py:789-849`): `SERIALIZED_RESOURCE_TYPES` (4 types) run one at a time — Webex enforces one-bulk-job-per-org, so this can't be parallelized
2. **Tier ordering** (7 tiers executed sequentially): Cross-tier dependencies prevent full parallelism — tier 5 (settings) can't start until tier 2-3 (people/devices) completes
3. **Dependency resolution** (`runtime.py:25-139`): `get_next_batch()` queries SQLite for every batch — O(ops × edges) per batch fetch, acceptable for <10K ops
4. **No connection pooling in CLI** (`auth.py`): Each `rest_get`/`rest_post` creates a new HTTPX connection — no keepalive for sequential commands (the migration engine uses aiohttp session with keepalive)
5. **Sequential pagination** (`auth.py:45-59`): `follow_pagination` is synchronous and single-threaded — large orgs with 50+ pages are slow

**Practical capacity ceiling:** The engine is designed for migrations up to ~5000 operations (large enterprise). Beyond that:
- SQLite `get_next_batch()` becomes slow (full table scan of plan_operations WHERE status='pending')
- Memory usage for the dependency graph (NetworkX) grows with edges²
- Single-org Webex rate limits (~100 req/min) become the hard wall regardless of client-side concurrency

**Test to surface:** Run `get_next_batch()` with a synthetic store of 10K+ operations and 50K+ edges — measure query time. The SQLite query lacks an index on `(status, tier, batch)` — this would be the first scaling fix.

---

## 4. State and Side Effects

### 4a. State Written to Disk

| Location | Written By | Format | Recovery |
|----------|-----------|--------|----------|
| `~/.wxcli/config.json` | `config.py:13-16` | JSON (token, org_id, cc_region) | Delete file, re-run `wxcli configure` |
| `~/.wxcli/current_project` | `commands/cucm.py:46, 102` | Plain text (project name) | Delete file, re-specify project |
| `~/.wxcli/migrations/{project}/store.db` | `store.py:40-172` | SQLite WAL mode (7 tables) | Re-run pipeline from `discover` |
| `~/.wxcli/migrations/{project}/state.json` | `state.py:72-139` | JSON (state machine + history) | Manually edit state value or re-init |
| `~/.wxcli/migrations/{project}/config.json` | `commands/cucm_config.py` | JSON (project config) | Re-run `wxcli cucm config` |

### 4b. External State (Webex API Writes)

| Operation | Idempotent? | Recovery on Failure |
|-----------|-------------|-------------------|
| POST (create resource) | **Yes** — via 409 auto-recovery for 7 types (user, location, translation_pattern, trunk, dial_plan, operating_mode, schedule) | Search by name/email, reuse existing ID |
| POST (create resource) — other types | **No** — duplicate creation possible on re-run if first attempt returned 2xx but result was lost | Manual cleanup required |
| PUT (configure settings) | **Yes** — overwrites existing state | Re-run applies same config |
| DELETE | **N/A** — not automated in migration; cleanup uses it | Delete is inherently idempotent (404 on re-run) |
| POST bulk job | **No** — each submission creates a new job | If first job succeeded but status lost, re-run creates duplicate job (unlikely to cause data corruption for settings jobs, but may double-apply) |
| POST /devices/activationCode | **No** — generates new code each call | Previous code expires; new code is valid |

### 4c. Idempotency Summary

| Subsystem | Safe to Re-Run? | Caveats |
|-----------|----------------|---------|
| `wxcli cucm discover` through `plan` | **Yes** — deterministic pipeline, same input → same output | Re-discover overwrites store tables |
| `wxcli cucm execute` (partially failed) | **Yes** — completed ops skip, pending ops re-queue | 409 auto-recovery handles duplicates |
| `wxcli cucm execute` (fully completed) | **Yes** — no pending ops, returns immediately | No-op |
| `wxcli cleanup run` | **Yes** — deletes are idempotent (404s are acceptable) | Re-run safe but may show "already deleted" warnings |
| Generated CLI `create` commands | **No** — duplicate creation possible | User must check existence first |
| Generated CLI `update` commands | **Yes** — PUT overwrites | Safe to repeat |
| Generated CLI `delete` commands | **Mostly** — 404 on already-deleted | Some endpoints return 400 instead of 404 for missing resources |

### 4d. Partial Failure Recovery

**Migration engine:**
1. Op fails → status=`failed`, cascade skip to dependents → persisted to SQLite
2. `wxcli cucm retry-failed` (`commands/cucm.py:2538-2574`) → resets failed ops to `pending`
3. Re-run `execute` → only pending ops re-queue, completed ops skip
4. 409 auto-recovery catches cases where API call succeeded but response was lost

**Cleanup:**
1. Individual delete failures are recorded in `DeleteResult` → reported in summary
2. Re-running cleanup is safe — already-deleted resources return 404, treated as success
3. Location delete retries are built-in (5 attempts × 60s)

**CLI commands (non-migration):**
1. No automatic retry or recovery
2. User re-runs the command manually
3. No state persisted between runs — each invocation is independent

---

## 5. Known Issues and Workarounds

### Baked-In Bugs

| Issue | Code Path | Impact | Workaround |
|-------|-----------|--------|-----------|
| Generated command `result` undefined after exception | `command_renderer.py:336-338` | If `handle_rest_error(e)` doesn't exit (impossible today since it always calls `typer.Exit(1)`), code crashes with `NameError` | Currently unexploitable because `handle_rest_error` always exits — but fragile if error handler ever changed to non-exit |
| `follow_pagination` resets params to None | `auth.py:59` | After first page, query params are cleared — second page URL must be fully qualified | Works because Webex includes full URL in Link header, but would break if any API returns relative Links |
| Empty dict `{}` returned for no-content 204 responses | `auth.py:25, 31, 37, 43` | `response.json() if response.content else {}` — but 204 has no content, so all 204 responses look like empty success | Downstream code must check status code separately if it needs to distinguish "success with no body" from "empty object returned" |

### Baked-In Limitations

| Limitation | Code Path | Why It Exists | Workaround in Code |
|------------|-----------|---------------|-------------------|
| Virtual line ID type mismatch | CLAUDE.md Known Issue #11 | `virtual-extensions` commands use VIRTUAL_EXTENSION-encoded IDs, but virtual lines are VIRTUAL_LINE | `cleanup.py` uses raw REST DELETE instead of CLI commands |
| No retry logic in sync CLI | `auth.py:21-43` | Design choice — CLI commands are short-lived, user can re-run | Migration engine has full retry (async); CLI doesn't |
| 6 person settings are user-only | Known Issue #4 | No admin API path exists | Use `wxcli my-call-settings` with user OAuth |
| Partial bulk failure treated as total | execute/CLAUDE.md | `fallback_context` not wired in `run_batch_ops` | Primitives exist, just not connected — entire bulk op marked failed, retry re-submits everything |
| Workspace settings require Professional license | Known Issue #6 | API returns 405 on Basic workspace | No workaround — feature limitation |
| Contact Center requires CC-scoped OAuth | Known Issue #13 | PATs don't carry `cjp:config` scopes even for CC admins | User must create OAuth integration with explicit CC scopes |

### Workarounds in Code (Deliberate Technical Debt)

| Workaround | Location | Why |
|------------|----------|-----|
| `decode_webex_id()` strips Spark URN to bare UUID | `config.py:38-55` | CC API requires UUID; Calling API returns base64 URN — two ID formats coexist |
| CCP error code short-circuit | `cleanup.py:25, 715` | Cisco Calling Plan resources can't be deleted via API — detect and skip instead of retry |
| Virtual line raw REST in cleanup | `cleanup.py` | CLI `virtual-extensions` uses wrong ID encoding — bypass it |
| `_merge_from_previous` sentinel | `engine.py:38-42` | Read-before-write pattern (GET then PUT merged) — handlers can't hold state between calls |
| Activation code `code` field fallback | `engine.py:218` | `/devices/activationCode` returns `{"code": ...}` not `{"id": ...}` — engine checks both |
| `phones_using == 0` skip in line_key_template | `planner.py` | Templates that no phone references are dead — skip instead of creating orphans |
| Response list key chain (`items` → `data` → raw) | Generated commands | CC API uses `data`, Calling uses `items` — single code path handles both |
| `handle_rest_error` always exits | `errors.py:68` | Ensures no code after error handler executes — masks the `result` undefined bug in generated commands |

### Known Unknowns (Requires Testing)

| Question | How to Test | Risk if Untested |
|----------|-------------|-----------------|
| What happens when `get_next_batch()` processes 10K+ operations? | Synthetic store with large op count; measure query time | May hit unacceptable latency without index |
| Does `follow_pagination` handle Webex APIs that return relative Link URLs? | Mock server returning `Link: </v1/next?page=2>; rel="next"` | Would break pagination silently (returns 0 items) |
| What's the actual Webex 429 threshold per endpoint? | Rate-test different endpoints (people vs. telephony/config) | May need per-endpoint rate limits instead of global semaphore |
| How does the engine behave when SQLite WAL file grows past 1GB? | Long-running migration with high write volume | WAL checkpoint may stall reads during heavy writes |
| What happens if token expires mid-migration (engine run)? | Set token TTL to 5 minutes, start 20-minute migration | Every request after expiry gets 401 — no refresh logic in engine |
| Does cleanup correctly handle orgs with >10K numbers? | Create test org with bulk-provisioned numbers | Pagination may exceed memory for very large pages |
| What's the blast radius of a cycle-broken fixup that fails at tier 7? | Create migration with known cycles, fail the fixup op | May leave resources in partially-configured state with no clear recovery path |
