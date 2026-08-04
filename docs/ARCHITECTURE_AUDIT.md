# wxops — Architectural Audit

**Date:** 2026-08-04
**Commit audited:** `a898c76` (`claude/wxops-architecture-audit-s2c55b`, identical to `main` — `git diff main...HEAD` is empty)
**Scope:** read-only. No source files were modified; this document is the only file added.

---

## 0. Two corrections to the audit premise

Stating these up front because two Phase-5 questions and one Phase-1 question are unanswerable as posed.

**There is no MCP server layer.** I searched `src/`, `tools/`, `pyproject.toml`, and the docs. The only hits are prose. `README.md:46-55` is a section titled *"Why a CLI, not an MCP server?"* arguing explicitly against building one ("you wrap the CLI behind **one** small MCP surface — a single 'run a wxcli command' tool — not several hundred"). So every Phase-5 question about MCP-vs-CLI boundary integrity, and Phase-3's question about whether the MCP layer restates the CLI's schemas, has the same answer: the layer does not exist, and its absence is a documented decision I agree with. I judged the CLI-surface boundary in its place.

**The endpoint count is ~1,845, not 828.** Measured by `tools/drift_check.py`: 1,845 non-skipped spec operations across 9 tracked OpenAPI specs, 154 deliberately skipped, rendering to 1,872 commands in 176 command sets. (828 is coincidentally the exact line count of the five top-level modules in `src/wxcli/*.py`.) Every "multiplied by N" argument below uses 1,872. This makes the leverage argument stronger, not weaker.

---

## 1. Verdict

**Structurally sound, with one broken load-bearing mechanism and localized rot around it.** The core bet — 1,872 commands generated from Cisco's own OpenAPI specs, mounted through one manifest, all flowing through a single 105-line HTTP session — is correct and is actually implemented: 65,253 lines of command code are generated from 5,951 lines of generator, and adding endpoint 1,846 genuinely touches one or two files. But the tool that makes that bet pay off, `tools/spec_sync.py`, **cannot run to completion** — it aborts with `FileNotFoundError` on a directory that does not exist — and the enforcing CI drift gate is consequently **red on `main` right now**, with 42 spec operations having no CLI command. The second structural problem is that essentially none of the shared machinery is tested: 2,902 tests exist and cover the CUCM migration subsystem at 88.9%, while `src/wxcli/commands/` sits at **1.8%** and the generator at **16.4%**. Fix the sync path and put tests on the machinery and this is a genuinely well-built system; leave them and every future spec refresh widens the gap silently.

---

## 2. Findings

| ID | Sev | Category | Files | Description |
|----|-----|----------|-------|-------------|
| C1 | Critical | broken-mechanism | `tools/spec_sync.py:70`, `tools/drift_check.py:628,672-673` | The only atomic spec→CLI sync path aborts (exit 1) because it writes to `docs/arch/`, which does not exist |
| C2 | Critical | gate-red | `.github/workflows/ci.yml:81-83`, `specs/*.json` @ `a898c76` | CI runs `drift_check.py --enforce`; it exits 1 on `main` — 42 spec ops with no command, 1 command ahead of spec |
| C3 | Critical | divergent-duplicate | `src/wxcli/auth.py:29-57`, `src/wxcli/migration/execute/engine.py:188-234`, `src/wxcli/migration/rate_limiter.py:64-90` | Three different 429/retry policies; two are live and disagree on retry count, cap, escape hatch, and malformed-header handling; the third is dead |
| C4 | Critical | boundary | `src/wxcli/auth.py:126-143`, `src/wxcli/errors.py:57-77`, coverage data | No seam below the CLI: auth and error handling terminate in `typer.Exit`, so the machinery all 1,872 commands share is only reachable through a terminal — and is 1.8%/14.4%/16.4% covered |
| H1 | High | accretion | `tools/command_renderer.py:336-366`, `src/wxcli/commands/audit_events.py:41-47` | 449 of 502 list commands issue a single GET; the default `--limit 0` sends no page-size param, so results silently truncate at the API default |
| H2 | High | type-loss | `tools/openapi_parser.py:148-161`, `tools/command_renderer.py:544-546` | Parser computes `field_type="number"`; renderer only special-cases `bool`, so 292 numeric body fields are sent to the API as JSON strings |
| H3 | High | correctness | `src/wxcli/commands/configure.py:51`, `src/wxcli/main.py:60-74` | `whoami` reports a token expiry that was fabricated as `now + 12h` at configure time and has no relationship to the real token |
| H4 | High | security | `src/wxcli/config.py:13-16`, `src/wxcli/commands/configure.py:56` | Full-admin bearer token written to `~/.wxcli/config.json` at default umask, never chmod'd; no refresh path exists anywhere |
| H5 | High | dead-and-swallowed | `src/wxcli/migration/preflight/runner.py:230-237`, `checks.py:873-879`, `tests/migration/preflight/test_checks.py:555-617` | The bulk-job preflight probe calls `session.ep()`/`session.get()`, which do not exist; a bare `except` turns the `AttributeError` into a permanent WARN; every test injects a fake probe |
| M1 | Medium | duplicate | `src/wxcli/errors.py:13-16,33-43,57-77` | `WebexError.status_code`/`.body` are set and never read; the handler re-parses `str(e)` as JSON, then dispatches through three parallel mechanisms |
| M2 | Medium | duplicate | `src/wxcli/auth.py:59-67` vs `:91-105` | Two error-raising paths in one class; `follow_pagination` raises `WebexError` without the `body=` enrichment `_json_or_raise` attaches |
| M3 | Medium | latent-divergence | `tools/command_renderer.py:355` vs `:358` | Within one rendered command, the `--limit>0` branch falls back to a `"data"` response key and the pagination branch does not |
| M4 | Medium | duplicate | `src/wxcli/main.py:101-127` vs `src/wxcli/commands/configure.py:10-35` | Two org-picker implementations that disagree on invalid input (exit 1 vs. warn-and-continue) |
| M5 | Medium | duplicate | `src/wxcli/update_check.py:36-53` vs `src/wxcli/commands/update.py:81-97` | Two PyPI version comparisons that disagree on prereleases |
| M6 | Medium | duplicate | `tools/postman_parser.py:166-171` vs `tools/drift_check.py:89-123` | Two readers of `field_overrides.yaml`: PyYAML, and a hand-rolled indent-based parser |
| M7 | Medium | surface-gap | `tools/command_renderer.py:643-644,700`, `:734-739,805` | `update`/`settings-update`/`delete` commands accept no `--output`; they print a fixed success string and discard the response body |
| M8 | Medium | provenance | `tools/command_renderer.py:912-927` | 65,253 lines across 171 generated modules carry no "generated — do not edit" header; nothing distinguishes them from hand-written code |
| M9 | Medium | dead-code | `src/wxcli/migration/rate_limiter.py` (145 LOC), `tools/command_renderer.py:29-34,300`, `runner.py:199` | `RateLimiter` has no production callers; `V2_MODULES` and `has_spec_start` unreferenced; docstrings cite a `WebexSimpleApi` class that does not exist |
| M10 | Medium | global-state | `tools/generate_commands.py:240`, `src/wxcli/main.py:77-134` | Generated commands have no `--org-id` override; partner org targeting is process-global mutable file state via `switch-org` |
| M11 | Medium | observability | `src/wxcli/auth.py:29-57,126-131` | Webex's `TrackingID` response header is never captured or logged; `--debug` gives an operator nothing to hand Cisco TAC |
| M12 | Medium | config | `src/wxcli/config.py:18-36,89-128` | Eight independent getters each re-open and re-parse the config file; the documented flags>env>file precedence exists only for the token |
| L1 | Low | doc-drift | `docs/architecture/01-structural-map.md:8,15,66-68`, `tools/CLAUDE.md` | Stale counts (172 vs 171 generated, 226 vs 186 test files, 46 vs 42 reference docs, 26 vs 24 skills) and stale `file:line` citations; the drift gate does not check either |
| L2 | Low | hygiene | `tools/command_renderer.py:3,300`, `tools/openapi_parser.py:4,8`, `tools/generate_commands.py:4` | Unused imports and ~15 f-strings with no placeholders (pyflakes) |
| L3 | Low | duplicate | `tools/command_renderer.py:124-127` | The CC and FS branches of `_render_path_inject` are byte-identical |
| L4 | Low | ux | `src/wxcli/output.py:41-49` | `print_table`'s `limit=50` default is never used; callers pass `limit=0`, so a 5,000-row list prints unbounded |

---

## 3. Detailed findings — Critical and High

### C1 — The atomic spec-sync path cannot complete

**What's there.** `tools/spec_sync.py` is the documented one-command path for a spec refresh: pull specs → regenerate every tag of every tracked spec → run the drift gate and emit the deliberate-gaps doc, then land it all as one commit. Its final step is:

```python
run([PYTHON, "tools/drift_check.py", "--write-gaps"])   # spec_sync.py:70
```

`run()` calls `sys.exit(result.returncode)` on any non-zero exit (`spec_sync.py:36-42`). `--write-gaps` reaches `write_gaps_doc`, whose target is `GAPS_DOC = REPO / "docs" / "arch" / "deliberate-gaps.md"` (`drift_check.py:628`). **`docs/arch/` does not exist** — the real directory is `docs/architecture/`.

Reproduced, and the working tree stayed clean because nothing was written:

```
$ python3 tools/drift_check.py --write-gaps
  File "…/drift_check.py", line 672, in write_gaps_doc
    GAPS_DOC.write_text("\n".join(lines))
FileNotFoundError: [Errno 2] No such file or directory:
  '/home/user/wxops/docs/arch/deliberate-gaps.md'
EXIT=1
```

`write_gaps_doc` is called *before* any check runs (`drift_check.py:691-695`), so the operator gets no drift report at all — just a traceback, after all 171 command modules have already been rewritten on disk. The same phantom path appears in `spec_sync.py:10` (`git add … docs/arch/deliberate-gaps.md`, which would also fail), `TODO.md:63`, and `drift_check.py:5`, which cites `docs/arch/target-architecture.md §A6` as the authority for the checks — a file that does not exist either.

**Why it matters at this scale.** This is the one mechanism that converts "Cisco changed the API" into "the CLI changed too." With 1,872 commands there is no manual fallback; the only alternative is `update-specs.py` alone, which pulls specs and regenerates nothing. That is exactly what the most recent commit did (see C2). A five-character path bug has disabled the repo's central leverage.

**Correct shape.** One constant, defined once, pointing at the real directory, and a test that asserts the gaps-doc parent directory exists — or better, `mkdir(parents=True, exist_ok=True)` before writing so the path cannot rot again. The four other citations of `docs/arch/` should move with it.

---

### C2 — The enforcing CI gate is red on `main`

**What's there.** `.github/workflows/ci.yml:81-83` runs `python tools/drift_check.py --enforce` as a dedicated job, with an excellent comment explaining why it is separate ("the only thing standing between a fabricated `wxcli …` reference and the docs the agent is REQUIRED to read"). Run today on `main`:

```
drift-check: 176 command sets (179 registered names incl. aliases), 1872 commands,
             1845 non-skipped spec ops (154 deliberately skipped)
[1] spec->CLI missing: 42   CLI-ahead-of-spec: 1
[2] dead wxcli references: 0     [3] published-count mismatches: 0
[4] unreferenced groups: 0       [5] stale overlays: 0
[6] non-existent flags cited: 0  [7] prose flags on no command: 0
result: FAIL
$ python3 tools/drift_check.py --enforce ; echo $?
1
```

The 42 break down as:

| Count | Spec | Tag |
|---|---|---|
| 27 | `webex-cloud-calling.json` | AI Receptionist for Webex Calling |
| 5 | `webex-cloud-calling.json` | Call Settings Configurable Storage Region |
| 4 | `webex-cloud-calling.json` | Features: Announcement Repository |
| 2 | `webex-contact-center.json` | Flows |
| 2 | `webex-contact-center.json` | Contact List Management |
| 1 | `webex-contact-center.json` | Campaign Group |
| 1 | `webex-admin.json` | Archive Users |

**How it got here — provable.** HEAD is `a898c76 chore(specs): update OpenAPI specs from upstream (2026-08-03)`. Its diffstat is *five spec files and nothing else*: no `src/wxcli/commands/` change, no `_registry.py` change, no docs change. And the new surface is genuinely new — `git show 27f3e28:specs/webex-cloud-calling.json | grep -c aiReceptionists` returns **0**; the same grep at `a898c76` returns **14**. So a whole new product area (AI Receptionist, 27 operations) entered the spec and the CLI never learned about it. This is C1's consequence: the operator ran the half of the pipeline that works.

**Why it matters at this scale.** A permanently-red enforcing gate is worse than no gate. Six of the seven checks are currently clean and genuinely valuable — check 2 (dead `wxcli` references in the docs the agent must read) and check 6 (flags cited that the command doesn't accept) are the specific defenses against the failure mode `tools/CLAUDE.md` known-issue #22 describes as having "shipped a broken CLI once already." Once contributors learn the gate is always red, all seven stop being read.

**Correct shape.** Regenerate from the current specs so parity returns to zero, then keep `--enforce`. If some gap must persist (the one `cli_ahead_of_spec` entry, `GET /identity/organizations/{}/v1/ArchivedUser/{}`, looks like a legitimate overlay candidate), it belongs in `keep_endpoints` or `specs/overlays/` with a reason — the mechanisms already exist and check 5 already polices overlays for staleness.

---

### C3 — Three retry/rate-limit policies; two live and divergent

**What's there.** Every one of the 1,872 CLI commands goes through exactly one path — `WebexSession._request` (`auth.py:29-57`), reached via 1,888 `api.session.*` call sites across 175 modules. That part is right, and it is the single best structural decision in the repo. But it is not the only path.

| | `auth.py:29-57` (CLI, httpx, sync) | `engine.py:188-234` (migration, aiohttp, async) | `rate_limiter.py:64-90` |
|---|---|---|---|
| 429 retries | 3 (`MAX_RETRIES_429`) | 5 (`MAX_RETRIES`) | 5 (`max_retries`) |
| Backoff | honor `Retry-After`, **capped at 30s** | honor `Retry-After`, **uncapped** | exponential, 1s→60s, ignores `Retry-After` |
| Malformed `Retry-After` | `except ValueError: delay = 5` | `int(...)` **unguarded** — `ValueError` escapes past `except aiohttp.ClientError` | n/a |
| Connect-error retry | 1 | 5, `2**attempt` backoff | n/a |
| Escape hatch | `WXCLI_NO_RETRY=1` | none | none |
| Error mapping | `WebexError` + `_ERROR_TIPS` | `OpResult(status, error=str)` — no tips | n/a |
| Callers | 1,872 commands | migration execute | **none** |

Three concrete divergences worth naming. First, `Retry-After` per RFC 7231 may be an HTTP-date; `auth.py:50-53` handles that, `engine.py:200` does not, and the surrounding `try` only catches `aiohttp.ClientError`, so a date-valued header crashes the operation out of `execute_single_op` rather than retrying. Second, a Webex `Retry-After: 3600` stalls a migration for an hour but is clamped to 30s in the CLI. Third, `WXCLI_NO_RETRY=1` — documented in `auth.py:14` as the scripted-context escape hatch — does nothing to the migration engine, which is the one place a long run actually needs to be interruptible.

`RateLimiter` (145 LOC) implements a *fourth* policy — per-endpoint exponential backoff — and is referenced only by `tests/migration/test_rate_limiter.py` (124 LOC of tests for code nothing calls). Its own `_SyncSlot` docstring concedes it "is NOT thread-safe."

**Why it matters at this scale.** Rate limiting is the one behavior that must be identical everywhere, because the org-wide 429 budget is shared: the CLI and a running migration hit the same quota. Two policies means tuning one does not fix the other, and the difference only shows up under exactly the load where it is most expensive to debug.

**Correct shape.** One retry/backoff policy object — `(max_retries, cap, parse_retry_after, honor_kill_switch)` — with two thin transport adapters (httpx sync, aiohttp async) that both consume it. Delete `RateLimiter` and its test file, or promote it to be that policy object. Note this is *not* an argument for one transport: the migration engine's concurrency model genuinely needs async, and I would leave that alone (§5). It is an argument against one transport carrying a second, silently different set of rules.

---

### C4 — No testable seam below the CLI

**What's there.** A generated command inlines the whole vertical slice. From `hunt_group.py:22-49`:

```python
api = get_api(debug=debug)                       # auth + typer.Exit on failure
url = f"https://webexapis.com/v1/telephony/config/huntGroups"
params = {}; …; params["orgId"] = get_org_id()   # config read
try: items = list(api.session.follow_pagination(...))
except WebexError as e: handle_rest_error(e)     # prints + typer.Exit(1)
print_table(items, columns=[…])                  # rich → stdout
```

There is no function here that takes inputs and returns hunt groups. `get_api` (`auth.py:126-143`) calls `typer.echo(..., err=True)` and `raise typer.Exit(1)` when no token is present. `handle_rest_error` (`errors.py:57-77`) *always* ends in `raise typer.Exit(1)` — a `WebexError` can never be handled by a caller. `config.get_fs_project_id` (`config.py:118-122`) raises `SystemExit` with a multi-line help message. So the answer to "can core operation logic be exercised without a terminal, without argparse/click, and without a live network?" is **no** for the CLI surface.

The migration layer knows this and works around it twice: `preflight/runner.py:221-223` wraps `get_api()` in `except SystemExit` with the comment *"get_api raises typer.Exit when no token is configured"*, and the module's stated convention (`runner.py:202-204`) is **"subprocess, not import" — checks shell out to `wxcli` via `_run_wxcli` to reuse the CLI's auth, pagination, and error handling.** That is an accurate description of the situation: the only way to reuse the CLI's behavior is to run the binary and parse its stdout. `org_health` does the same at one further remove — `collector.py` reads JSON files that the skill produced by shelling out.

**The measurement.** Full suite, `pytest tests/ -m "not live"` → **2,902 passed** (3 failures + 4 errors here are local only: they shell out to a `wxcli` binary I did not install). Coverage by layer:

| Layer | Covered / statements | % |
|---|---|---|
| `src/wxcli/commands/` (171 generated + 8 hand-written) | 801 / 45,210 | **1.8%** |
| `tools/` (the generator producing those 45k statements) | 433 / 2,645 | **16.4%** |
| `src/wxcli/*.py` (auth, config, errors, output, main) | 76 / 526 | **14.4%** |
| `src/wxcli/migration/` | 14,098 / 15,861 | 88.9% |
| `src/wxcli/org_health/` | 391 / 438 | 89.3% |

Per-file for the shared machinery: `auth.py` 37%, `config.py` 30%, `errors.py` 20%, `output.py` **0%**, `main.py` **0%**, `update_check.py` **0%**. The 37% on `auth.py` is incidental — it comes from migration tests importing it, not from tests of it.

**I want to be fair about what this does and does not mean.** Testing 171 generated modules file-by-file would be wrong; you test the generator and the runtime machinery instead. That is the correct shape. But the generator is at 16.4% (one test file, `tests/test_field_overrides.py`, and it validates the YAML overrides rather than rendered output), and the runtime machinery is at 14.4% with `output.py` at zero. So the correctly-shaped tests do not exist either. 2,902 tests is a real and impressive number; it just describes one command group out of 176.

**What can break in production with a green suite — specifically.**
- Every failure mode in H1, H2, H3, H5 below. None is detectable by the current suite.
- Any change to `WebexSession._request` — retry, header, pagination — affects all 1,872 commands and is caught by nothing.
- `print_table`'s auto-detect fallback (`output.py:52-55`) silently rewrites the column set when the configured accessors all resolve empty. Zero coverage. A table that quietly shows different columns than the one an operator saw yesterday is exactly the kind of thing a screenshot-based check never catches.
- Nothing in the suite would fail if any duplicate pair in §2 (M2, M4, M5, M6, or C3) drifted further apart. I looked for such a test specifically; there is none.

**Correct shape.** (a) Golden-file tests on the renderer: pin ~8 representative `Endpoint` fixtures — list-paginating, list-flat, create-with-required, update-json-patch, delete-with-scoping-body, action, CC-base-url, org-id-path-injected — and assert the rendered text. That makes every generator change a reviewable diff and would have caught H1 and H2 at authoring time. (b) Contract tests for `WebexSession` against recorded responses (`respx`/`httpx.MockTransport`): 429 with numeric and date `Retry-After`, `Link`-header pagination across pages, error-body extraction, `WXCLI_NO_RETRY`. (c) Split `handle_rest_error` into a pure `classify(WebexError) -> Tip | None` plus a thin printer, so the classification is testable without a terminal.

---

### H1 — 449 of 502 list commands do not paginate, and the default hides it

**What's there.** `openapi_parser.py:479-483` decides pagination from one signal: `paginates = "Link" in op["responses"]["200"]["headers"]`. When true, the renderer emits a `follow_pagination` loop; when false, it emits a single `rest_get` (`command_renderer.py:336-366`). AST-counting every list-style command in `src/wxcli/commands/`:

- with `follow_pagination`: **53**
- single GET: **449**

The default is `--limit 0`, and `if limit > 0: params["max"] = limit` (`command_renderer.py:320`) — so at the default **no page-size parameter is sent at all** and the API's own default applies. `audit_events.py:12-51` is the clean example: Webex's Admin Audit Events endpoint paginates and the command even renders `--limit`/`--offset` mapped onto `max`/`offset`, but the default path issues one GET, takes whatever page Webex returns, and prints it with no indication that more exist.

The help string is honest — `"Max results (0=all for paginated endpoints, API default for non-paginated)"` — but it puts the burden on the operator to know which of the two kinds they are holding, and there is no way to find out short of reading the generated source.

**Why it matters at this scale.** `CLAUDE.md`'s own "Source of Truth Precedence" section documents this exact failure class with a real incident: `wxcli people list -o json` answering "how many users have extensions?" with **0** because `--calling-data true` was not passed — "no error, no warning." H1 is the same shape with a wider blast radius: 449 commands where `-o json | jq length` returns a confidently wrong count. Every new non-`Link`-declaring endpoint adds one more.

**Correct shape.** Three parts. (1) When the endpoint declares `max`/`limit` but no `Link` header, still page: loop on `offset`/`start` until a short page comes back. (2) When the response cannot be paged at all, say so — emit a stderr note when the returned item count equals the requested or default page size, so "there may be more" is visible rather than inferred. (3) Make `--limit 0` mean *all* uniformly, since that is what the help text already claims. This is renderer-only; it changes one function and regenerates.

---

### H2 — Numeric body fields are sent as JSON strings

**What's there.** `openapi_parser.py:148-161` maps OpenAPI `integer` and `number` to `field_type="number"`. Every renderer then branches on exactly two types:

```python
if bf.field_type == "bool":
    params.append(f'{param}: bool = typer.Option(None, "--{…}/--no-{…}", …)')
else:
    params.append(f'{param}: str = typer.Option(None, "--{…}", …)')   # renderer:544-546
...
body["{bf.name}"] = {param}      # the str goes straight into the JSON body
```

`"number"` is computed and then discarded. Confirmed in the output — `user_settings.py:4433,4464`:

```python
rollover_wait_time_in_secs: str = typer.Option(None, "--rollover-wait-time-in-secs", …)
...
body["rolloverWaitTimeInSecs"] = rollover_wait_time_in_secs    # sends "30", spec says 30
```

Counting scalar numeric body properties across the tracked specs: **292** (contact-center 213, cloud-calling 32, meetings 22, admin 14, device 11). Not all become flags — nested-object fields are `--json-body`-only — but the ones that do are all affected, and `--json-body` is the only correct way to set them today, which is not discoverable from `--help`.

**Why it matters at this scale.** It is per-field, so it grows with the spec. It fails at the API with a 400 rather than silently, which is the merciful version — but the operator gets a type error on a flag the CLI itself offered them, with no hint that the flag is unusable. And a JSON-lenient endpoint that coerces is worse: it succeeds with a value the CLI can no longer round-trip.

**Correct shape.** Add `number` to the type switch: render `int`/`float` typer options, let Typer parse and validate, and put the parsed value in the body. Same one-line-per-renderer change in five places, then regenerate. The golden-file tests from C4(a) pin it.

---

### H3 — `whoami` reports a fabricated token expiry

**What's there.** `configure.py:51` invents the expiry:

```python
expires_at = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()
```

Nothing about the token is consulted — not an `expires_in` from an OAuth response (there is no OAuth flow), not an introspection call. It is a hardcoded twelve hours from whenever `wxcli configure` was run. `main.py:60-74` then reads it back and presents it to the operator as fact:

```
Token: expires in 3h 12m — consider refreshing soon
```

A 12-hour guess happens to match a developer Personal Access Token. It does not match an OAuth integration token (14 days) or a service-app token. And `CLAUDE.md` known-issue #11 *requires* an OAuth integration token for every `cc-*` command, and #1/#3/#4 require user-level OAuth for `call-controls` and `my-call-settings` — so the users most likely to run `whoami` are exactly the users for whom the number is most wrong. The countdown expires while the token is still good for a fortnight.

**Why it matters.** `whoami` exists to answer "am I authenticated and as whom." Two of its four lines are trustworthy; the fourth is a guess rendered in the same voice. In a tool whose top-level rule is "Never answer from training data alone… say so explicitly rather than filling the gap," a fabricated field in the CLI's own identity command is the wrong lesson to ship.

**Correct shape.** Either store a real expiry (from an OAuth token response, once one exists) or drop the field. If a heuristic is genuinely useful, label it: `Token: saved 8h ago (expiry unknown — PATs last ~12h)`.

---

### H4 — Admin bearer token at default umask, with no refresh path

**What's there.** `configure.py:56-58` writes the token to `~/.wxcli/config.json` through `config.save_config`:

```python
def save_config(data: dict, path: Path = DEFAULT_CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)      # config.py:13-16
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
```

No `mode=` on the `mkdir`, no `chmod` on the file. Under a default umask of 022 that is a `0755` directory and a `0644` file containing a bearer token that, for this tool's intended user, is a full-organization admin credential. `grep -n "chmod\|0o600\|mode=" src/wxcli/config.py` returns nothing.

Separately: searching `src/` and `tools/` for `refresh_token`, `refreshToken`, `grant_type`, or `oauth2/v1/access_token` returns **zero hits**. There is no refresh anywhere. Phase 2 asks for every place that implements "authentication and token refresh": authentication is `resolve_token()` (`auth.py:113-123`), exactly one place, which is correct; refresh is zero places. Recovery is re-running `wxcli configure` and pasting a new token by hand.

**Why it's rated High.** By the rubric's letter this is Medium — it does not compound with endpoint count. I am rating it on impact instead and saying so rather than letting the rubric hide it: the file is a standing org-admin credential on a shared or backed-up home directory, and the mitigation is two lines.

**Correct shape.** `mkdir(mode=0o700)` and `os.chmod(path, 0o600)` after write, plus a warning if the existing file is group/other-readable. Longer term, an OAuth device-code flow with a stored refresh token would fix H3 and H4 together and remove the paste-a-token step that makes both necessary.

---

### H5 — A preflight check that has never worked, hidden by a bare `except`

**What's there.** `preflight/runner.py:194-242` builds the bulk-device-job probe. Its body:

```python
url = api.session.ep("telephony/config/jobs/devices/callDeviceSettings")   # :230
...
try:
    resp = api.session.get(url, params=params)                             # :235
except requests.RequestException as exc:
    return 0, str(exc)
```

`WebexSession` has no `ep()` and no `get()`. Its full method surface is `_headers`, `_request`, `_json_or_raise`, `rest_get`, `rest_put`, `rest_post`, `rest_patch`, `rest_delete`, `follow_pagination` (`auth.py:23-105`). And it is built on httpx, so `requests.RequestException` cannot be raised by it. Executed:

```
$ WEBEX_ACCESS_TOKEN=dummy python3 -c "…"
WebexSession has 'ep': False
WebexSession has 'get': False
probe raises: AttributeError 'WebexSession' object has no attribute 'ep'
```

The `AttributeError` is then absorbed at `checks.py:873-879`:

```python
try:
    status, err = probe_fn()
except Exception as exc:  # noqa: BLE001 — probe is best-effort
    return CheckResult(status=CheckStatus.WARN,
                       detail=f"Bulk device job probe failed: {exc}", …)
```

So the check does not error — it reports WARN with a plausible-looking message, every single time, for every org. And it is *tested*: `tests/migration/preflight/test_checks.py:555-617` exercises seven paths, and every one injects its own `probe_fn` lambda. `_build_bulk_job_probe` itself has no test. The docstrings at `runner.py:199` and `checks.py:848` claim it "Uses `WebexSimpleApi`" — a class that exists nowhere in the repo, a leftover from the SDK purge in `988eddc`.

**Why it matters.** This is the concrete answer to Phase 6's "what can break in production with a green test suite." The check exists to catch, before a 100+-device migration starts, that the org cannot run bulk device jobs — the failure it prevents is expensive and late. It has never once run. Two independent smells hid it: mocking at the wrong seam, and a bare `except Exception` that converts a programming error into a domain-shaped result.

**Correct shape.** Call `api.session.rest_get(url, params=params)` and catch `WebexError`; the status code is already on the exception (M1). Narrow the `except` in `checks.py` to the transport error it means, so an `AttributeError` crashes loudly. Add one test that calls `_build_bulk_job_probe()` against a stubbed transport rather than replacing it.

---

## 4. Remediation plan

Ordered by risk reduced ÷ disruption caused. Steps 1-2 must precede everything else: until the gate is green and trustworthy, no later step can be verified.

**Step 1 — Fix the sync path.** *Closes C1.* Point `GAPS_DOC` at `docs/architecture/deliberate-gaps.md` (or create `docs/arch/`), add `mkdir(parents=True, exist_ok=True)` before the write, and update the four other citations (`spec_sync.py:10`, `TODO.md:63`, `drift_check.py:5` — the last of which points at a `target-architecture.md` that does not exist and needs either writing or repointing at `docs/architecture/`). **Blast radius: 3 files.** *Verify:* `python3 tools/spec_sync.py --skip-update` runs to completion and `git status` shows only the gaps doc.

**Step 2 — Regenerate and get the gate green.** *Closes C2. Depends on 1.* Run `tools/spec_sync.py --skip-update` against the specs already on disk, review the diff for command **renames** and not just additions (known issues #18 and #22 — a renamed bare command is worse than a deleted one), and land one commit. The 27 AI-Receptionist ops become a new group, which per drift check 4 also needs either a skill route or an entry on `CLAUDE.md`'s out-of-scope list. Decide the one `cli_ahead_of_spec` entry deliberately: `keep_endpoints` or an overlay. **Blast radius: ~5-15 command modules, `_registry.py`, `CLAUDE.md`, possibly one skill.** *Verify:* `drift_check.py --enforce` exits 0; `pytest tests/ -m "not live"` still reports 2,902 passing; diff command *names* per group against the pre-change tree and confirm zero unintended renames.

**Step 3 — Golden-file tests for the renderer.** *Opens the door to 4, 5, 6; partially closes C4.* Eight `Endpoint` fixtures covering the seven `RENDERERS` entries plus the CC base-URL and org-id-path-injection variants; assert rendered text. **Blast radius: 1 new test file, 0 source files.** *Verify:* the tests pass against today's renderer unchanged — that is the point; they are a behavior lock, and any diff at this step means the fixtures are wrong.

**Step 4 — Fix pagination.** *Closes H1. Depends on 3.* Page on `offset`/`start` when the endpoint declares paging params without a `Link` header; warn on a full-looking page otherwise; make `--limit 0` mean all. **Blast radius: 1 renderer function + regenerate (~449 commands change, all mechanically).** *Verify:* golden files show the intended shape change and nothing else; `drift_check.py --enforce` still 0 (flags are unchanged, so checks 6/7 stay clean); spot-check one high-cardinality endpoint live against a known count.

**Step 5 — Fix numeric fields.** *Closes H2. Depends on 3.* Add `number` to the type switch in all five renderers. **Blast radius: 1 renderer file + regenerate.** *Verify:* golden files; `--help` for a known numeric flag shows `INTEGER`; a live PUT with a numeric flag succeeds where it previously 400'd.

**Step 6 — Unify retry policy.** *Closes C3, part of M2.* One policy object; httpx and aiohttp adapters consume it; delete `RateLimiter` and `tests/migration/test_rate_limiter.py`. Guard the `Retry-After` parse in both. **Blast radius: `auth.py`, `engine.py`, 1 new module, 2 deletions.** *Verify:* contract tests from C4(b) — numeric and HTTP-date `Retry-After`, cap honored, `WXCLI_NO_RETRY` respected — run against **both** adapters from the same table; migration suite (41 files under `tests/migration/execute/`) stays green.

**Step 7 — Fix the preflight probe and narrow the swallow.** *Closes H5.* Use `rest_get`, catch `WebexError`, narrow `checks.py:874`, add a test that exercises the real probe against a stubbed transport, delete the `WebexSimpleApi` references. **Blast radius: 2 source files, 1 test file.** *Verify:* the new test fails against today's code and passes after; a run against a real org produces PASS/FAIL rather than WARN.

**Step 8 — Token hygiene and the expiry lie.** *Closes H3, H4.* `chmod 0600`, `mkdir(mode=0o700)`, warn on loose existing perms; drop or label the fabricated `expires_at`. **Blast radius: `config.py`, `configure.py`, `main.py`.** *Verify:* new file is `0600`; `whoami` no longer prints an unbacked countdown.

**Step 9 — Contract tests for `WebexSession`; split `handle_rest_error`.** *Closes the rest of C4, plus M1 and M2.* Record fixtures for pagination, 429, error-body shapes; make `classify()` pure and read `e.body`/`e.status_code` instead of re-parsing `str(e)`; give `follow_pagination` the same enrichment as `_json_or_raise`. **Blast radius: `auth.py`, `errors.py`, 2 new test files.** *Verify:* coverage on `src/wxcli/*.py` moves off 14.4%; every `_ERROR_TIPS` code has a test.

**Step 10 — Medium cleanup, batched.** M4/M5/M6 (collapse the duplicate org-picker, version comparison, and YAML reader), M8 (provenance header on generated files — a one-line renderer change worth doing on its own, since 65,253 lines currently carry no signal that they are machine-written), M9 (delete dead code), M11 (capture and log `TrackingID`), L1-L4. **Blast radius: wide but shallow; do it after the gate is trustworthy, not before.**

---

## 5. What I'd leave alone

**The generator, wholesale.** 5,951 lines of `tools/` producing 65,253 lines across 171 modules, against 5,258 lines of hand-written command code in 8 modules. The parser→`Endpoint`→renderer pipeline is the correct decomposition, and `parse_tag`'s primary-tag-first name derivation (`openapi_parser.py:597-605`) is a subtle, correct fix to a real incident. Do not restructure it; test it.

**Generated Typer files as the runtime artifact.** Generating executable Python rather than dispatching a table at runtime looks like duplication and is not: it is what makes `wxcli <group> <command> --help` a real, complete, self-documenting surface with no runtime indirection, which is precisely what the README argues the tool is for. `tools/CLAUDE.md` states the invariant plainly — "The generated files are the CLI; nothing else runs behind them."

**Two HTTP transports.** C3 argues against two *policies*, not two transports. The migration engine's `asyncio.gather` + semaphore model over hundreds of operations genuinely needs aiohttp; forcing it through the sync session would be a real regression.

**`drift_check.py` itself.** 765 lines, dependency-free, AST-based, seven checks. Check 2 (dead `wxcli` references in agent-read docs) and check 6 (flags cited that a command does not accept) are unusual and exactly right for a repo where prose is a runtime input. Checks 2-7 are all currently clean. This is the best-designed thing here; it just needs to be able to run (C1) and to be believed (C2).

**`cleanup.py`'s shape.** 1,427 lines is a lot, but the core is a declarative `RESOURCE_TYPES` table (19 entries) plus a `DELETION_LAYERS` list (13 layers) — the generalized form, not an if-chain. The per-resource comments earn their place (`cleanup.py:173-176` on `/people?locationId=` needing `callingData=true` documents the same silent-empty-result trap as H1). It duplicates URL knowledge the specs already hold, but a dependency-ordered teardown is not derivable from OpenAPI, so hand-maintaining it is the right call.

**`src/wxcli/_playbook/` (4.1 MB mirroring `.claude/` and `docs/`).** A committed duplicate of 127 files. Defensible: it ships the playbook inside the wheel, it is generated by `wxcli-dist/assemble.py`, and CI's `playbook-freshness` job rebuilds it and fails the PR if the committed copy is stale. Mechanically verified duplication is not rot.

**The migration subsystem's registry pattern.** `HANDLER_REGISTRY`, `_EXPANDERS`, `_CROSS_OBJECT_RULES`, `TIER_ASSIGNMENTS` — 65 handlers dispatched by `(resource_type, op_type)` rather than by conditional chain. Phase 4 asked me to hunt for type-keyed if-chains; across all of `src/wxcli/` there are only 39 `*_type ==` comparisons, and the concentrations (planner 9, engine 8) are dispatch guards, not accretion. I went looking for this and did not find it.

**Wrong but not worth fixing.** `V2_MODULES` (`command_renderer.py:29-34`) and `has_spec_start` (`:300`) are dead but harmless — delete them when touching the file, not before. The `_playbook` mirror's size. The `licenses-api` alias (`main.py:192`) is a deliberate one-release deprecation shim with a date on it. The ~15 pyflakes f-string warnings are noise.

**One thing I'll defend that looks wrong.** `rest_delete` carrying a request body (`auth.py:82-89`) violates the usual reading of HTTP DELETE semantics. It is correct here: 10 Webex operations require it, and on 5 the body is what *scopes* the delete. The comment records the live verification (HTTP 400, errorCode 25024) and known issue #21 documents that an earlier version of that same comment asserted the opposite as fact without testing. Both the code and the correction are right.

---

## 6. Read coverage

**Read in full** (every line): `src/wxcli/main.py`, `auth.py`, `config.py`, `errors.py`, `output.py`, `__init__.py`; `src/wxcli/commands/configure.py`; `tools/generate_commands.py`, `command_renderer.py`, `openapi_parser.py`, `postman_parser.py`, `spec_sync.py`; `src/wxcli/migration/rate_limiter.py`; `pyproject.toml`; `CLAUDE.md`, `tools/CLAUDE.md`, `src/wxcli/migration/CLAUDE.md`, `src/wxcli/migration/execute/CLAUDE.md`, `.claude/rules/cleanup.md`, `.claude/rules/cucm-migration.md`.

**Read in substantial part** (named ranges): `tools/drift_check.py` — lines 1-180 and 626-765 read, full function outline extracted, executed three ways (default, `--json`, `--enforce`, `--write-gaps`); `src/wxcli/commands/cleanup.py` — lines 1-215 plus full function outline; `src/wxcli/migration/execute/engine.py` — lines 1-360 of 900+; `src/wxcli/migration/preflight/runner.py` — lines 190-260; `preflight/checks.py` — lines 819-915; `src/wxcli/org_health/collector.py` — lines 1-80; `src/wxcli/update_check.py` and `commands/update.py` — the version-comparison and PyPI paths; `.github/workflows/ci.yml` — the `test`, `drift-gate`, and `playbook-freshness` jobs; `docs/architecture/01-structural-map.md` — §1-2.

**Sampled, with the rest analyzed mechanically:** the 171 generated command modules. I read `hunt_group.py:1-60` and `audit_events.py:1-60` line by line as representatives, plus targeted regions of `user_settings.py` (4433-4464). The remaining 169 I analyzed programmatically rather than by eye: AST-parsed all of them to classify list-style commands as paginating vs. single-GET (53/449), counted `api.session.*` call sites (1,888 across 175 modules), tallied `follow_pagination` item keys, split generated vs. hand-written LOC (65,253 / 5,258), and let `drift_check.py`'s own AST pass enumerate all 1,872 commands and their flags. **Extrapolation claimed:** that the two modules I read are representative of renderer output. That is a safe extrapolation *because* the files are machine-generated by the seven functions in `command_renderer.py`, all of which I read in full — but it is an extrapolation, and I flag it.

**Deliberately skipped:** `src/wxcli/migration/transform/**` (~30k LOC — 42 normalizers, 26 mappers, 13 analyzers), `migration/cucm/extractors/**`, `migration/report/**`, `migration/advisory/**`. Reasons: they sit at 88.9% test coverage behind 2,902 tests, they are a self-contained pipeline behind one of 176 command groups, and CUCM-domain correctness is outside an architectural audit's remit. I read their `CLAUDE.md` files and sampled their import graph and dispatch patterns, which is what §5's registry-pattern claim rests on. `tools/create_stress_test_db.py` and `expand_cucm_data.py` (2,217 LOC of test-data generators) skipped as non-production. The 19 MB of `specs/*.json` was queried programmatically (numeric-field counts, `aiReceptionists` presence across two commits), never read. `src/wxcli/_playbook/**` skipped as CI-verified generated output. Individual test files were surveyed by coverage instrumentation and grep rather than read, except `tests/migration/preflight/test_checks.py:555-617`, which I read to establish H5.

**Commands executed** (all read-only; the working tree was verified clean afterward): `drift_check.py` in four modes; `pytest tests/ -m "not live"` with and without `--cov`; `pyflakes` over `tools/` and the non-generated `src/`; a `WebexSession` attribute probe with a dummy token; `git show` against two commits' spec files. Dependencies were installed into the container's site-packages; the repo itself was not `pip install -e`'d, which is why 3 tests fail and 4 error locally on a missing `wxcli` binary.
