# 06 — Hand-written machinery, and the two stacks *(the core of Target B)*

Phase 6 of `docs/arch/wxops-architecture-audit-prompt_2.md`. Extends
`docs/audit/00-facts.md` Q7 (which compared the two retry policies'
**declarations**), `docs/audit/00-context.md` Q4 (the stage map that sets the
blast radius) and `docs/audit/02-drift.md` §6.2 (which asserted the gate is
"almost untouched" by Target B — quantified below).

Labels: `[verified]` = I ran or parsed something this session. `[inferred]` =
reasoned from evidence short of direct observation. `UNKNOWN` = not established.

**Method.** `wxcli` is never imported (hook-blocked). Source read directly or
parsed; `wxcli … --help` run only as a subprocess with `COLUMNS=400`; no mutating
command run. Tracked-file questions answered with `git ls-files` /
`git check-ignore -v`, never the working disk. Two targeted test files were
executed; the full suite was not. Read coverage is stated in §9.

**Target A** = the generated endpoint layer + the 1,790-line shared runtime
(`src/wxcli/*.py`). **Target B** = `src/wxcli/migration/` (46,684 lines) plus its
driving command `src/wxcli/commands/cucm.py`.

---

## 0. Two corrections that change this phase's premises

Both were load-bearing assumptions in the audit spec and in `00-facts.md`. Both
are wrong, and each changes what the phase is measuring.

### C1 — `migration/rate_limiter.py` does not run. Nothing imports it.

`[verified]` `git grep` for `rate_limiter|RateLimiter|RateLimitConfig` across the
repo returns, outside the module's own body, exactly three consumers:

| Consumer | What it is |
|---|---|
| `tests/migration/test_rate_limiter.py:14` | its own unit test |
| `docs/architecture/04-operations-and-evolution.md:357` | a tracked architecture doc telling future contributors to use it |
| — | **no production import anywhere in `src/`** |

`src/wxcli/migration/rate_limiter.py` is 145 lines of dead code. Its
`RateLimitConfig` (`rate_limiter.py:18-24`) — `max_concurrent=5`,
`base_delay=1.0`, `max_delay=60.0`, `backoff_factor=2.0`, `max_retries=5` — is the
policy `00-facts.md` Q7 named as "the migration execute path"'s retry policy, and
the same values fill the Target B column of this phase's own table in the audit
spec (`wxops-architecture-audit-prompt_2.md:264-265`).

**None of those five numbers is in force.** The policy that actually runs is
written inline in `migration/execute/engine.py` and shares no parameter with the
declared one:

| Parameter | Declared (`rate_limiter.py`) | **In force** (`engine.py`) |
|---|---|---|
| Max concurrent | 5 (`:20`) | **20**, `-c/--concurrency` 1–50 (`commands/cucm.py:3151-3153`; `engine.py:869`) |
| Backoff | `base_delay × 2^n`, capped 60s (`:68-71`) | `Retry-After` verbatim, **uncapped**; else literal `5` (`engine.py:200`) |
| Max retries | 5 (`:24`) | 5 (`engine.py:36`, `:188`) — the one value that coincides |
| Per-endpoint state | yes, `_EndpointState` (`:27-31`) | **none** — no per-endpoint tracking exists |
| Backoff reset on success | `record_success` (`:75-79`) | not called; no such concept |

Consequence for the audit: `00-facts.md` Q7's *Assumptions I could not confirm*
item 5 ("whether `auth.py`'s retry policy and `migration/rate_limiter.py`'s agree
behaviorally") is not merely unanswered — **it is the wrong question.** The
comparison this phase exists to make is `auth.py` versus `engine.py`, and it is
made in §3.

A tracked architecture doc actively propagates the error: *"Any new
bulk-operation module should follow the async pattern with the existing
`rate_limiter.py`"* (`docs/architecture/04-operations-and-evolution.md:357`)
`[verified]`. That sentence points the next contributor at a module the engine
already declined to use.

### C2 — The repository contains **no recorded remote responses for any system.** Not Webex. Not AXL.

`[verified]` `00-facts.md` Q15 and the audit spec's Phase 6 item 4
(`wxops-architecture-audit-prompt_2.md:282`) both rest on the claim that recorded
AXL responses exist under `tests/fixtures/axl-responses/` while Webex REST has
none — and the spec builds its remediation sequencing on that asymmetry.

Measured:

- `tests/fixtures/axl-responses/` holds 18 XML files **on this disk** and is
  **gitignored** — `git check-ignore -v` returns `.gitignore:53:tests/*`.
- `git ls-files tests/ | grep -v '\.py$'` returns **nothing**. Every tracked file
  under `tests/` is a `.py`. `git ls-files | grep -E '^tests/.*\.(xml|json|yaml|har)$'`
  returns **0**.
- Nothing in the repository references the directory: `grep -rn "axl-responses"`
  over `tests/ src/ tools/ .github/` returns **no matches**. The fixtures are both
  untracked *and* unreferenced.
- `tests/migration/cucm/fixtures/` — the one tracked fixtures package — contains
  only `__init__.py`.

This is the same error class `00-facts.md` corrected itself for three times
(`00-facts.md:94-98`, "I counted what was on this disk instead of what is
git-tracked"); it caught three instances and missed this one.

**So the asymmetry the spec plans around does not exist.** Neither stack is
pinned by recorded responses. §8 answers item 4 on that basis.

### C2a — and the untracked retry test does not pass either

A second consequence, found while establishing C2 `[verified]`: `.gitignore:53`
is `tests/*` with re-includes for `tests/migration/**`, `tests/org_health/**` and
23 named files (`.gitignore:54-100`). **`tests/test_auth.py` is not among
them.** It is the only test of Target A's retry policy — it contains
`test_429_retry_honors_retry_after` (`tests/test_auth.py:89`) and
`test_retry_after_header_still_wins_on_429` (`:255`) — and it does not exist in a
fresh clone. CI runs `pytest tests/ -m "not live"` (`.github/workflows/ci.yml:63`),
so in CI nothing pins the `Retry-After` behaviour this entire phase compares
against. `tests/conftest.py` is likewise untracked.

**Then I ran it, and the situation is worse than untracked** `[verified]`:

```
$ /opt/homebrew/opt/python@3.14/bin/python3.14 -m pytest tests/test_auth.py -q
18 failed, 6 passed in 0.58s
```

Every failure is the same cause. The file patches `wxcli.auth.httpx.request` at
ten sites (`tests/test_auth.py:55`, `:66`, `:74`, `:95`, `:108`, `:121`, `:132`,
`:140`, …), but `auth.py` imports `httpx` **lazily, inside the two methods that
issue a request** (`auth.py:206`, `:226`) — so `wxcli.auth.httpx` is not a module
attribute and the patch target does not exist. The failures are
`ImportError`/`AttributeError` at patch time, not assertion failures.

**The source is right and the test is stale.** The lazy import is deliberate and
documented at `auth.py:14-21`: keeping `httpx` off the module's top level is what
keeps `wxcli --version` and `--help` fast. The refactor that introduced it broke
these tests and nobody found out.

**Being gitignored is why.** A tracked test goes red in CI the moment a refactor
invalidates it; an untracked one rots in silence. So the exclusion did not merely
hide the test from CI — **it hid the test's own decay.** Both named `Retry-After`
tests are among the 18.

Two consequences, and the second is the one that matters for this document:

- The remediation sequence cannot start with "add one line to `.gitignore`" (§8
  step 1 is revised accordingly). Tracking a red file would break CI. The 18
  patch targets have to be repointed first — the fix is mechanical, since
  `httpx.request` is resolved fresh inside the method on every call.
- **Target A's retry behaviour — the baseline every comparison in §3 is measured
  against — is currently corroborated by no executing test on any machine.** The
  §3 findings rest on reading `auth.py:157-260` directly, which I did in full, and
  on `docs/reference/authentication.md:566-577`, which states the same contract in
  prose. That is sound evidence and it is not test evidence, and the distinction
  should be visible to whoever acts on this.

Inverted, and worth stating plainly because it runs against expectation: **the
ungated hand-written stack is better pinned in CI than the shared runtime it
diverges from.** `tests/migration/**` is tracked wholesale, CI installs
`aioresponses` for it (`ci.yml:35`), and `tests/migration/execute/test_engine.py`
runs on every PR — while `tests/test_auth.py` does not ship.

---

## 1. The divergence map

The spec's table, filled, with two rows added that it did not anticipate
(timeouts, and the bulk-job path). Every row is `[verified]`. The "Verdict"
column is the finding — the existence of two implementations is not.

| Concept | Target A | Target B | Verdict |
|---|---|---|---|
| **HTTP client** | `httpx`, sync, lazily imported (`auth.py:206`, `:235`) | `aiohttp`, async (`execute/engine.py:17`, `:875`, `:191`) | Split — **defensible**, see §8 |
| **Retry: status set** | `{429,500,502,503,504}` (`auth.py:160`) | **429 only** (`engine.py:199`); every other `>=400` fails the op at once (`engine.py:205-210`) | **DISAGREE — A right** (D1) |
| **Retry: `Retry-After`** | honored, `int()` guarded, capped 30s (`auth.py:247-253`, `:159`) | honored, **unguarded `int()`, uncapped** (`engine.py:200`) | **DISAGREE — A right** (D2, D3) |
| **Retry: fallback delay** | exponential **with jitter** (`auth.py:184-188`) | literal `5` seconds, **no jitter** (`engine.py:200`) | **DISAGREE — A right** (D4) |
| **Retry: connect errors** | 1 retry (`auth.py:239-244`) | up to 5, `2**attempt`, no jitter (`engine.py:222-225`) | Differ; **B defensible** (§4) |
| **Retry: bulk-job path** | n/a | **none anywhere** — submit (`engine.py:324-337`), poll (`:68-71`, no status check) and per-device fallback (`:579-589`) all lack a 429 branch | **B wrong** (D5) |
| **Concurrency** | none (sync) | `asyncio.Semaphore(concurrency)`, default **20** (`engine.py:869`; `commands/cucm.py:3151`) | Split by design; **but see D4/D6** |
| **Timeouts** | connect 10s / read 60s, env-tunable (`auth.py:192-193`, `:196-212`) | **unset** — aiohttp default `total=300s, sock_connect=30s` (`engine.py:875`) | **DISAGREE — A right** (D7) |
| **Pagination** | 3 walkers + cap + short-read warning (`auth.py:297`, `:313`, `:342`, `:50-62`, `:105`) | none; single-page GETs only | **DISAGREE — A right** (D8) |
| **Auth / token** | `resolve_token()` env→env→config (`auth.py:375-385`); headers at `auth.py:215-219` | `resolve_token()` reused (`commands/cucm.py:3164`), raw token → aiohttp headers (`engine.py:870-873`) | **AGREE** on both (§4) |
| **HTTP error → domain error** | `errors.py` `WebexError` + `handle_rest_error` (`:169`), tips, exit 1 (`:203`) | `errors.py` **never imported** on this path; errors become `OpResult.error` strings (`engine.py:206-209`) | **DISAGREE — mixed** (§6) |
| **Config precedence** | `config.py` accessors (`get_org_id`, `:28`) | `get_org_id` **never called**; inline re-read + `except: pass` (`commands/cucm.py:3187-3196`) | **DISAGREE — A right** (D9, D10) |
| **Output formatting** | `common.emit` / `output.py` on every generated command | 18 `emit()` vs 288 `console.print` in `cucm.py`; execute path is all `console.print` to **stdout** | Partial adoption (§6) |
| **Logging** | one logger `"wxcli"` (`auth.py:23`) | **62 loggers**, all `getLogger(__name__)`; **no handler on the execute path** | **DISAGREE — neither right** (D11) |
| **Correlation IDs** | none | none | **AGREE** — both absent (§4) |
| **Env vars (`WXCLI_*`)** | 7 behavioral vars, all in `auth.py` | **0 of the 7** reach the write path (§2.2) | **DISAGREE — B wrong** (D12) |
| **Library-layer `sys.exit`** | `errors.py:203`,`:225`; `common.py:32`,`:252`,`:263`; `config.py:118` | **zero** across 46,684 lines | **DISAGREE — B right** (§4) |

### What the coherence gate covers here

`[verified]` `grep -c migration tools/drift_check.py` → **15 hits**, all in one
place: check 17's count table (`drift_check.py:2556-2587`, `:2615`) plus one
filename exclusion (`:2954`). Those hits assert three integers — mapper count,
analyzer count, preflight-check count — against numbers written in prose in
`migration/CLAUDE.md` and `migration/preflight/CLAUDE.md`.

**The gate's entire coverage of 46,684 lines is three documentation counts. No
check reads `execute/`, `engine.py`, `handlers.py`, or `rate_limiter.py`.** That
sharpens `02-drift.md` §6.2's "almost untouched" from a characterization into a
measurement, and it is why every disagreement below can ship green.

---

## 2. The three questions this phase exists to answer

### 2.1 Does Target B honor `Retry-After`? — **Yes, and worse than not honoring it.**

`[verified]` It does read the header. `engine.py:199-203`:

```python
if resp_status == 429:
    retry_after = int(resp_headers.get("Retry-After", 5))
    logger.debug("429 on %s, retry after %ds", node_id, retry_after)
    await asyncio.sleep(retry_after)
    continue
```

Against `auth.py:246-259`:

```python
if response.status_code in RETRY_STATUSES and attempts_left > 0:
    retry_after = response.headers.get("Retry-After")
    delay = None
    if retry_after:
        try:
            delay = min(int(retry_after), MAX_RETRY_AFTER_SECONDS)   # 30
        except ValueError:
            delay = None
    if delay is None:
        delay = _backoff_delay(attempt)                              # jittered
    logger.warning(...)
    time.sleep(delay)
```

So the *header is honored on both paths* — the naive answer is "agree". Every
detail around it disagrees, and three of them are defects (D2, D3, D4). The
one-line summary: **A treats `Retry-After` as a bounded hint; B treats it as an
unbounded, unvalidated instruction.**

### 2.2 Does Target B respect the `WXCLI_*` environment variables? — **No. Zero of the seven.**

`[verified]` — `git grep -l` per variable over `src/wxcli/`, excluding the bundled
playbook:

| Variable | Read in | Reaches Target B's write path? |
|---|---|---|
| `WXCLI_MAX_ATTEMPTS` | `auth.py:179` | **no** |
| `WXCLI_RETRY_MODE` | `auth.py:174` | **no** |
| `WXCLI_NO_RETRY` | `auth.py:172` | **no** |
| `WXCLI_MAX_PAGES` | `auth.py:45` | **no** |
| `WXCLI_NO_PAGE_WARN` | `auth.py:133` | **no** |
| `WXCLI_CONNECT_TIMEOUT` | `auth.py:210` | **no** |
| `WXCLI_READ_TIMEOUT` | `auth.py:212` | **no** |
| `WXCLI_PLAIN` | `output.py:19` | **yes** — imported by `commands/cucm.py:40`, but it only selects Rich markup mode (`cucm.py:120`, `:127`). Cosmetic. |
| `WXCLI_NO_UPDATE_CHECK` | `update_check.py` | yes — root callback, binary-wide |
| `WXCLI_UPDATE_INDEX_URL` | `commands/update.py` | n/a |
| `WXCLI_PLAN_FAIL_ON_UNRESOLVED` | `commands/cucm.py`, `migration/execute/planner.py:2117` | **B-only**, and absent from the documented env table |

**All seven behavioral HTTP-tuning variables are read in exactly one file,
`auth.py`, and the migration write path never calls into it.** The only variable
that touches the write path is `WXCLI_PLAIN`, which changes box-drawing.

**The asymmetry inside one pipeline is sharper than plain absence.** `preflight`
shells out to the `wxcli` binary — `subprocess.run(["wxcli"] + args + ["-o",
"json"], capture_output=True, text=True)` (`preflight/__init__.py:74-77`) with
**no `env=` argument** `[verified]`, so the child inherits the full environment
and each spawned process re-reads `os.environ` inside `auth.py` exactly as an
interactive invocation would. So in a single migration run:

- `WXCLI_MAX_PAGES`, `WXCLI_RETRY_MODE`, `WXCLI_MAX_ATTEMPTS`,
  `WXCLI_CONNECT_TIMEOUT`, `WXCLI_READ_TIMEOUT` **work** on the preflight reads;
- the same variables **silently do nothing** on the execute writes.

An operator who tunes retry, watches preflight behave differently, and concludes
the setting is in force has drawn the correct inference from the evidence
available and is wrong about the only stage that matters.

The contract is documented without a scope qualifier. `docs/reference/authentication.md`
§*Retries* (`:566-577`) states max attempts, the disable switches, the retried
status set, and the 30-second `Retry-After` cap as properties of the tool. Nothing
in that section says they stop at `wxcli cucm execute`. The doc *does* carry one
honest scope caveat — `:583`, that the hand-written seams including `cucm` omit
the `httpx.HTTPError` catch — so the document knows these seams differ and
discloses it for error handling only, not for retry or for the env vars.

**Consequence for the operator, which is the point of the question.** An LLM
driving this CLI that hits rate limiting mid-migration, reads
`authentication.md` or the 429 tip in `errors.py:59` (*"raise the retry budget
with `WXCLI_MAX_ATTEMPTS=<n>`"*), sets the variable and re-runs `wxcli cucm
execute` gets **no change in behaviour and no warning that the knob was inert.**
That is the exact failure mode the question was written to detect.

### 2.3 Same exit codes and actionability tips as `errors.py`? — **No. Target B never loads `errors.py`.**

`[verified]` The only non-`wxcli.migration` import inside all of
`src/wxcli/migration/` is `from wxcli.auth import get_api`
(`preflight/runner.py:312`). `commands/cucm.py` imports `wxcli.common.emit`
(`:39`), `wxcli.output.plain_mode` (`:40`), `wxcli.auth.resolve_token` (`:3164`)
and `wxcli.auth.get_api` (`:3199`). **`wxcli.errors` appears in neither.**

So none of `errors.py`'s machinery is reachable on the migration write path:
`_extract_error_code` (`:63`), `_truncate_html` (`:76`), `decode_id_kind` (`:90`),
`_passed_id_kinds` (`:125`), `_id_kind_tip` (`:135`), `_is_cc_403` (`:157`), the
five `_ERROR_TIPS`, the two `_MESSAGE_TIPS`, the seven `_STATUS_TIPS`, and the
`Ids you passed, decoded:` line. Detail and the exit-code inventory in §6.

---

## 3. The behavioural disagreements

Each names both sides and says which is right. Ordered by consequence on the
execute path.

### D1 — B does not retry 500/502/503/504. A does. **A is right.**

- A: `RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})` (`auth.py:160`),
  applied at `auth.py:246`.
- B: only `resp_status == 429` is retried (`engine.py:199`). The next branch,
  `if resp_status >= 400`, returns a failed `OpResult` immediately
  (`engine.py:205-210`) `[verified]`.

**Why A is right, on this repo's own evidence.** `docs/reference/authentication.md:573`
states the contract — *"Retried HTTP status codes: **429, 500, 502, 503, 504**
(`RETRY_STATUSES`). Previously only 429 was retried."* That sentence records a
deliberate widening. `docs/reference/…/wxc-calling-debug/SKILL.md:272` classes
502/503 as *"Webex platform issue — retry after a delay."* Target B is the
"previously" state, on the one path where a transient failure is most expensive.

**Consequence.** A single 503 from Webex during a migration fails that operation
permanently *and* cascade-skips every hard dependent
(`runtime.py:218-223`, `_cascade_skip` at `:235`). A 503 while creating a
location skips the location's users, their devices, and the features that hang off
them. Recovery is `retry-failed` → `execute`, which is documented and works — but
the operator is told the operation *failed*, not that the platform blipped, and
the error string is the raw body.

### D2 — B's `Retry-After` parse is unguarded. A's is. **A is right.**

- A: `try: delay = min(int(retry_after), 30) except ValueError: delay = None`,
  falling back to jittered backoff (`auth.py:249-255`).
- B: `int(resp_headers.get("Retry-After", 5))` — no `try` (`engine.py:200`)
  `[verified]`.

RFC 7231 §7.1.3 permits `Retry-After` in two forms: delta-seconds **or**
HTTP-date. On the date form B raises `ValueError`. That exception is not caught
by the surrounding `except aiohttp.ClientError` (`engine.py:222`).

**Where it lands, traced** `[verified]`: it escapes `execute_single_op`, is
absorbed by `asyncio.gather(..., return_exceptions=True)` (`engine.py:822`) and
converted to `OpResult(status=0, error=str(res))` (`engine.py:824-827`). So it
does **not** kill the run — that is the good news, and it is a deliberate control.

The bad news is what it converts: a *transient, retryable* rate-limit becomes a
*permanent* operation failure whose message reaching the operator is
`invalid literal for int() with base 10: 'Wed, 21 Oct 2015 07:28:00 GMT'`. And
because `Retry-After` only appears when the server is throttling, every
concurrent operation in flight hits it in the same window — so the failure mode
is not one op but a batch-wide cascade at peak load.

**Trigger is `UNKNOWN`.** This repo's only recorded Webex `Retry-After` is
delta-seconds (`docs/reference/authentication.md:633`, `Retry-After: 5`). I did
not observe a date form and cannot say Webex sends one. Report it as a latent
defect, not an observed failure. What is *not* uncertain is that **the repo
already decided this is worth defending against and did so in one stack only** —
`auth.py:250-253` exists for exactly this input.

### D3 — B's `Retry-After` sleep is uncapped. A caps it at 30s. **A is right.**

`MAX_RETRY_AFTER_SECONDS = 30` (`auth.py:159`), applied at `auth.py:251`. B has
no cap (`engine.py:200-202`) `[verified]`. A server (or an intermediary) sending
`Retry-After: 3600` puts a migration operation to sleep for an hour. With
`max_retries=5` the ceiling is five such sleeps per sub-call, and see D6 for what
the semaphore is doing meanwhile.

### D4 — B has no jitter; A does. The stacks are inverted on this. **A's behaviour is right, and B needs it more.**

- A: `_backoff_delay` (`auth.py:184-188`) — `lower + random.random() * (base - lower)`.
- B: sleeps the header value verbatim, or literal `5` when absent
  (`engine.py:200`) `[verified]`. No randomization anywhere in `engine.py`.

Jitter exists to break synchronized retry. **A is single-threaded and has it; B
runs 20 concurrent requests by default and does not.** Twenty operations rate-
limited in the same window receive the same `Retry-After`, sleep the identical
duration, and resume in the same instant — reproducing the burst that caused the
throttle. This is the clearest case in the phase where the concurrent stack
inherited the weaker policy.

### D5 — Bulk-job submits have no 429 retry at all. **B is wrong.**

`[verified]` `execute_bulk_op` (`engine.py:284`) does not call
`execute_single_op`. Its submit is a bare `session.request` inside
`try/except aiohttp.ClientError` (`engine.py:324-330`), followed by
`if submit_status >= 400: return OpResult(...)` (`engine.py:332-337`). **There is
no 429 branch.** A rate-limited bulk submit is a permanent operation failure on
the first response.

This lands on the largest blast radius in the plan: `SERIALIZED_RESOURCE_TYPES`
is `{bulk_device_settings, bulk_line_key_template, bulk_dynamic_settings,
bulk_rebuild_phones}` (`execute/__init__.py:307-312`), the ops that replace
per-device work at ≥100 devices — i.e. one op per org-or-location-wide device
job.

It is not only the submit. **The entire bulk path has zero rate-limit
awareness** `[verified]`:

- **Submit** — `engine.py:324-337`, no 429 branch (above).
- **Poll** — `poll_job_until_complete` (`engine.py:45`) **never checks
  `resp.status`**: it does `body = await resp.json()` (`:68-69`) and reads
  `latestExecutionExitCode` with a default of `"UNKNOWN"` (`:71`). A 429 or 500
  during polling is therefore indistinguishable from "job not finished yet" and
  is polled again until `max_poll_time=600s` elapses — at which point the
  operator is handed `TimeoutError: Job … did not complete within 600.0s`, a
  message that reads like a slow job when the cause was a persistent auth or
  rate-limit error on the polling endpoint. If the polling body is not JSON at
  all (a 502 HTML page from a load balancer), `await resp.json()` raises
  unguarded; that is not a `TimeoutError`, so `execute_bulk_op`'s narrow
  `except TimeoutError` (`:368`) misses it and it falls to the serial loop's
  generic handler (`:846-847`), failing the op with a raw parse exception as its
  `error_message`.
- **Per-device fallback** — `_run_per_device_fallback` (`:579-589`) uses the same
  `resp.status >= 400` → record-a-failure shape, again with no 429 branch.

**`execute_single_op` is the only function in `engine.py` with any rate-limit
handling at all.** Everything in `SERIALIZED_RESOURCE_TYPES` — precisely the ops
serialized *because* Webex enforces one job per org, i.e. the ops most likely to
be issued back-to-back against the same endpoint — runs without it.

### D6 — The semaphore slot is *released* across the 429 sleep. **B is right on the mechanism — and that is what makes D4 bite.**

`[verified]` — settled with `ast`, not by eye, because indentation is exactly the
kind of thing a reader gets wrong: the `async with semaphore:` is an `AsyncWith`
node at `col_offset 16` spanning `engine.py:190-197`, and the
`if resp_status == 429:` at `:199` is an `If` node at the **same** `col_offset
16` — a sibling, not a child. So the block closes after the response is read, and
the `await asyncio.sleep(retry_after)` at `:202` runs outside it. The same holds
for the `aiohttp.ClientError` backoff at `:224` by the context manager's
exit-on-exception guarantee.

So the slot is **released** before the sleep. That is the correct behaviour and I
had expected the opposite — recording it because it is a real result: under
rate limiting the engine does not deadlock its own concurrency pool.

But it produces the D4 problem in its sharpest form: because slots are freed, all
20 waiters are eligible the instant their identical sleep expires, and they all
resume together. A held slot would have accidentally serialized them. **B is
right on the mechanism and wrong on the outcome**, and the fix is jitter (D4), not
the semaphore.

### D7 — B sets no HTTP timeout. A sets two, both env-tunable. **A is right.**

- A: `httpx.Timeout(read, connect=connect)` with `DEFAULT_CONNECT_TIMEOUT=10.0` /
  `DEFAULT_READ_TIMEOUT=60.0` (`auth.py:192-193`, `:209-213`), overridable per-call
  and by env (`auth.py:196-200`).
- B: `aiohttp.ClientSession(headers=headers)` (`engine.py:875`) — **no `timeout=`,
  no `connector=`** `[verified]`.

Measured against the installed aiohttp 3.13.3, a bare `ClientSession` gets
`ClientTimeout(total=300, sock_connect=30)` `[verified]`. So a hung request on the
migration path occupies a semaphore slot for **five minutes** versus A's 60
seconds, and neither `WXCLI_READ_TIMEOUT` nor `WXCLI_CONNECT_TIMEOUT` moves it
(D12).

The declared floor is `aiohttp>=3.9` (`pyproject.toml:35`), and that default has
changed across aiohttp releases. **Target B's request timeout is whatever the
installed aiohttp happens to default to** — an unpinned dependency default on the
one path that writes to a live org. A's is a named constant in the source.

### D8 — B does not paginate any read. A has three walkers and a page cap. **A is right where it matters.**

`[verified]` — no `Link`/`rel="next"`/`startIndex`/`pageSize` handling appears
anywhere in `src/wxcli/migration/`. Most of B's reads are single-object GETs where
that is correct. **One is not: the 409 auto-recovery search.**

`_try_find_existing` (`engine.py:612-709`) issues one un-paginated GET with a
server-side `name=`/`email=` filter and `max=100` for the telephony types, then:

```python
items = body.get(item_key, []) if isinstance(body, dict) else body
if items and len(items) > 0:
    return items[0].get("id")          # engine.py:704-706
```

Three defects in five lines `[verified]`:

1. **`items[0]` is returned with no equality check against the name that was
   searched for.** Whether Webex's `name=` filter on
   `/telephony/config/premisePstn/trunks`, `…/dialPlans`, `…/operatingModes`,
   `…/locations/{id}/schedules` and `…/devices/lineKeyTemplates` is exact-match or
   prefix/contains is **`UNKNOWN` — I did not verify it live and no recorded
   response exists to check against (C2).** If any of them is not exact, a 409 on
   creating `HQ` can bind the operation to `HQ-Backup`, mark it `completed`, and
   every dependent op then configures the wrong remote object. A one-line name
   equality check makes the question moot, which is the argument for adding it
   regardless of how the premise resolves.
2. **No pagination.** `user` and `location` pass no page-size parameter at all;
   the other six pass `"max": "100"` but still take one fetch with no `Link`
   walk `[verified]`. A match beyond the first page is invisible — and since the
   function only searches and never writes, the consequence there is a *failed*
   op carrying the original 409, not a duplicate. The duplicate risk lives in
   D13, on the re-issued create.
3. **`except Exception: pass` (`:707-708`) and `if resp.status == 200` (`:701`).**
   A 401, a 500, or a network drop during recovery is indistinguishable from
   "no such resource" — the op then fails carrying the *original* 409 message,
   which tells the operator the resource exists while the code concluded it does
   not.

A documentation drift found alongside: `migration/execute/CLAUDE.md` lists seven
recoverable types (*"user, location, translation_pattern, trunk, dial_plan,
operating_mode, schedule"*); the source has **eight** — `line_key_template`
(`engine.py:681-687`) is uncounted `[verified]`. Harmless today, but it is
exactly the class of prose-vs-source count that drift-gate check 17 exists to
catch for mappers and analyzers and does not cover here (§1).

And the recovery is silent: success is announced by `logger.info("409
auto-recovered %s -> %s", …)` (`engine.py:950`), which goes nowhere (D11). **The
engine can adopt a pre-existing remote object as its own, record its id as the
migration's output, and tell no one.**

### D9 — B re-implements `get_org_id()` inline and swallows the failure. **A is right.**

- A: `config.py:28-31`, one accessor, used everywhere; `orgId` auto-injected on
  the generated surface.
- B: `commands/cucm.py:3187-3196` `[verified]`:

```python
config_path = Path.home() / ".wxcli" / "config.json"
if config_path.exists():
    import json as json_mod
    try:
        cfg = json_mod.loads(config_path.read_text())
        org_id = cfg.get("profiles", {}).get("default", {}).get("org_id")
        if org_id:
            ctx["orgId"] = org_id
    except Exception:
        pass
```

`get_org_id` is **never called anywhere in `commands/cucm.py` or
`src/wxcli/migration/`** `[verified]`. Same file, same key path, duplicated
literal.

**The failure mode is the finding, not the duplication.** `ctx["orgId"]` is what
`_url()` (`handlers.py:58-68`) injects as `?orgId=` on **every write the
migration makes**. A malformed or unreadable `~/.wxcli/config.json` takes the
`except Exception: pass` branch, `ctx` has no `orgId`, and every write goes out
unscoped — resolved server-side to whatever org the token defaults to. On a
partner token managing multiple customer orgs (a first-class supported mode,
`wxcli switch-org`), that writes an entire migration into the wrong org, silently.
A's equivalent path (`config.load_config`, `config.py:10-11`) lets
`json.JSONDecodeError` propagate — loud and wrong-looking, but it cannot
misdirect a write.

### D10 — `WORKSPACE_LICENSE_ID` is read and never set. **B is wrong.**

`[verified]` `handlers.py:490` reads `ctx.get("WORKSPACE_LICENSE_ID")` and adds
`licenses` to the workspace body only when present (`:491-492`). `git grep`
returns exactly two writers of `ctx` on the execute path —
`ctx["orgId"]` (`cucm.py:3194`) and `ctx["CALLING_LICENSE_ID"]` (`cucm.py:3207`).
**Nothing anywhere sets `WORKSPACE_LICENSE_ID`.** Every `workspace:create` the
migration issues omits the license.

`CALLING_LICENSE_ID` has a softer version of the same problem. It is set only if
the `/v1/licenses` scan finds a license whose name contains both `"Calling"` and
`"Professional"` with free units (`cucm.py:3204-3208`). If the loop finds none —
no exception, no warning — `handle_user_create` omits `body["licenses"]`
(`handlers.py:466-468`) and the migration creates **unlicensed users**. The
`[yellow]Warning[/yellow]` at `cucm.py:3210` fires only on an exception from the
GET, and the disclosure at `:3213-3214` prints only when the id *was* found. The
"no matching license" case is announced by nothing.

The same GET is `api.session.rest_get("https://webexapis.com/v1/licenses")`
(`cucm.py:3202`) — a single fetch, not `follow_pagination`, so an org whose
Professional license sits beyond page one silently produces the same outcome.
`rest_get` does emit the "server has more pages" note on stderr
(`auth.py:105`, `:155`), which is the one thing standing between this and total
silence.

Both wrap in `except Exception` (`cucm.py:3209`), so a 401 here — the same token
about to be handed to `aiohttp` for every write — is downgraded to a yellow
warning and execution proceeds.

### D11 — 62 loggers, no handler on the execute path. **Neither stack is right.**

`[verified]` `src/wxcli/migration/` contains 62 `logging.getLogger(__name__)`
calls and no other form. Target A has one, `getLogger("wxcli")` (`auth.py:23`).

`logging.basicConfig` is called at four sites in `commands/cucm.py` — `:1156`,
`:1345`, `:1457`, `:1560` — and **all four belong to the read-only pipeline
stages** (the `-v` paths on discover / normalize / map / analyze). `execute()`
(`cucm.py:3149-3242`) configures nothing `[verified]`.

`execute` has no `-v/--verbose` flag at all (`[verified]` via
`COLUMNS=400 wxcli cucm execute --help`: only `-c/--concurrency` and
`-p/--project`), while `discover`/`normalize`/`map`/`analyze` each have one — so
there is not even a way to reach `basicConfig` on the write path.

So during `wxcli cucm execute` two stdlib defaults apply in sequence
`[verified]`, and the order matters:

1. **The effective level filters first.** No logger sets a level, so all 62
   inherit the root logger's default of `WARNING`. `Logger.isEnabledFor()`
   discards DEBUG and INFO records *before* dispatch.
2. **`logging.lastResort` handles what survives** — a bare `_StderrHandler` at
   level `WARNING` with **no formatter**, so a record prints as
   `record.getMessage()` alone: no timestamp, no level, no logger name.

Concretely:

| Call | Level | Operator sees |
|---|---|---|
| `engine.py:201` — `"429 on %s, retry after %ds"` | DEBUG | **nothing** |
| `engine.py:950` — `"409 auto-recovered %s -> %s"` | INFO | **nothing** |
| `engine.py:884` — batch/tier | INFO | nothing (but `on_progress` duplicates it) |
| `engine.py:156` — reset count | INFO | nothing (but `:3182` prints it) |
| five bulk-path `logger.warning` calls — `engine.py:429`, `:465`, `:512`, `:597`, `:743` | WARNING | **bare unattributed text on stderr** |

**The read-only stages configure logging; the one stage that writes to a live org
does not.** The result is that the two events an operator most needs from an
unattended concurrent run — *we were rate-limited* and *we adopted a resource we
did not create* — are both unobservable.

The outcome is two-tier rather than uniformly silent, and the leaky tier is
arguably worse. Those five WARNING calls carry the highest-stakes messages in the
engine — *"Cannot fetch job errors … treating partial bulk failure as total
failure"*, *"fallback recovered %d but %d device(s) never attempted"*,
*"Bulk fallback: device %s not yet created, excluding from fallback"* — and they
reach stderr with **no logger name, no level prefix, and no timestamp**, while
every one of `execute`'s own `console.print` lines goes to stdout (§6.4). So the
most consequential diagnostics in the run appear on a different stream from all
the surrounding context, unlabelled, with nothing tying them to the operation
they describe. Nobody configured this; it is what the stdlib does when no one
does anything.

Neither stack is right: A's single-logger/two-warnings design is not adequate
either (`00-facts.md` Q14), but A at least emits its retry warnings at WARNING,
so `lastResort` carries them.

### D12 — the `WXCLI_*` contract stops at `auth.py`. **B is wrong.**

Established in §2.2. Recorded here as a numbered disagreement because it is a
**published contract** (`00-facts.md` Q18) that one half of the binary does not
implement, and because the remedy is small: `engine.py` reading the same three
helpers (`_retry_enabled`, `_max_attempts`, `_env_float`) would close it without
touching the async design.

### D13 — the crash-recovery machinery is inert: `in_progress` is never written

Not a two-stack disagreement — Target A has no resumability to compare against —
but it is the central defect in the hand-written *machinery* this phase is named
for, so it belongs here.

`[verified]` `MigrationStore`'s `plan_operations` carries an `in_progress`
status; `OpStatus.IN_PROGRESS` is declared (`models.py:56`); `update_op_status`
implements the transition (`runtime.py:224-228`); `reset_in_progress` exists to
recover from it (`engine.py:148-157`) and is called at the top of every run
(`commands/cucm.py:3180`).

**Nothing ever sets it.** `git grep` for `'in_progress'` across `src/wxcli/`
returns the enum, the `update_op_status` branch, two defensive `status IN
('pending','in_progress')` clauses in the cascade query (`runtime.py:258`,
`:269`), two display/count sites (`cucm.py:2962`, `runtime.py:499`), and the reset
itself. **No producer.** `execute_all_batches` marks ops `completed`, `failed` or
`skipped` only (`engine.py:896`, `:906`, `:931`, `:935`, `:946`, `:953`, `:957`).

Two consequences:

1. `reset_in_progress` can only ever return 0. Its `logger.info("Reset %d …")`
   (`engine.py:156`) and the `[yellow]Reset N in-progress ops[/yellow]` line
   (`cucm.py:3182`) are unreachable. Dead defensive code that reads, to anyone
   auditing the file, like crash recovery is handled.
2. **An operation killed after its POST reached Webex but before
   `update_op_status(..., "completed")` committed remains `pending`** — byte-for-byte
   identical to an operation that was never attempted. The next `wxcli cucm
   execute` picks it up and re-issues the write.

That answers the question the audit spec asks twice (`:236`, `:242`): **a
half-applied migration is not distinguishable from a not-yet-started one at the
operation level.** What happens on the re-issue depends on two things neither
verified here: whether Webex enforces uniqueness for that resource type
(`UNKNOWN`), and whether the type is one of the eight `_try_find_existing` covers
(`user`, `location`, `translation_pattern`, `trunk`, `dial_plan`,
`operating_mode`, `schedule`, `line_key_template` — `engine.py:624-687`). For the
six location-scoped feature types the code declines recovery outright —
*"Skip recovery — let cascade handle it on next run"* (`engine.py:689-693`) — so a
re-issued `hunt_group:create` either 409s into a hard failure or creates a
**duplicate remote object**. `execute/` issues no DELETE anywhere
(`00-context.md` Q1 class 2), so nothing in the tool can clean that up.

The fix is one line in the right place — write `in_progress` before dispatch —
and it is cheap only because every other piece of the machinery already exists.

---

## 4. Where the two stacks agree

Stating these is a real result: each one is a place remediation does not have to
go.

- **Token resolution is genuinely shared.** `commands/cucm.py:3164` calls
  `resolve_token()` (`auth.py:375`), so the migration honours
  `WEBEX_ACCESS_TOKEN` → `WEBEX_TOKEN` → `~/.wxcli/config.json` in the same order
  as every other command, and a partner's `switch-org` token works identically
  `[verified]`. This is the single most important thing that *could* have
  diverged and did not.
- **The request headers are byte-identical.** A builds
  `{"Authorization": f"Bearer {self._token}", "Content-Type": content_type or
  "application/json"}` (`auth.py:215-219`); B builds
  `{"Authorization": f"Bearer {token}", "Content-Type": "application/json"}`
  (`engine.py:870-873`) `[verified]`. Same two headers, same values. One
  structural difference with no behavioural consequence today: A rebuilds them
  per request (`_headers()` called inside `_request()`, `auth.py:236`), B once at
  session construction. That would matter only if a token could change mid-run,
  and per the next bullet it cannot.
- **Neither stack refreshes a token, and neither special-cases 401.** `grep` for
  `refresh`/`expire`/`refresh_token` across `src/wxcli/` finds nothing in code
  `[verified]`, and 401 is absent from `RETRY_STATUSES` (`auth.py:160`) and from
  B's only status branch (`engine.py:199`). The consequence differs only in blast
  radius: A resolves a token per short-lived process, while B resolves once
  (`cucm.py:3173`) and bakes it into the session. A token expiring mid-migration
  401s every remaining call — each correctly recorded as `failed` with cascade
  skip, recoverable by re-auth plus a fresh `execute`. Degraded, not silent, and
  consistent with the resumable design.
- **`max_retries` coincides at 5** — A's `DEFAULT_MAX_ATTEMPTS = 4` plus one
  connect retry versus B's `MAX_RETRIES = 5` (`engine.py:36`) is close enough that
  the *budget* is not the divergence; the *policy* is.
- **Neither stack captures the server's correlation ID.** Webex returns a
  `TrackingID` response header on every call. `auth.py` reads only `Link`
  (`:98`, `:304`) and `Retry-After` (`:247`); `engine.py:200` reads only
  `Retry-After` `[verified]`. The `trackingId` hits elsewhere in `src/` are a
  *response-body* field on async job-status endpoints and a client-supplied
  request parameter on two `cc-*` commands — neither is the header. Both stacks
  are equally blind, so the split does not make cross-stack diagnosis worse; it
  is a shared gap, and a bigger one for B, which runs long async bulk jobs where a
  support escalation would want exactly that value.
  **One refinement in B's favour:** B does carry a self-generated per-*operation*
  id — `plan_operations.node_id` (`store.py:146`, PRIMARY KEY, format
  `canonical_id:op_type`), threaded through the engine's logs (`engine.py:201`),
  `on_progress` (`:962`) and `execution-status` (`cucm.py:3000`, `:3003`). What it
  lacks is a per-*run* id: `store.py:208-214` defines `current_run_id()`/
  `set_run_id()`, but they are written only to the `decisions` and `merge_log`
  tables, and `plan_operations` has **no `run_id` column** (`store.py:145-161`,
  read in full) `[verified]`. **Two `execute` invocations of the same project are
  indistinguishable in the store and in every log line** — which is the specific
  reason D13's "was this op attempted in the run that died?" cannot be answered
  after the fact.
- **Neither stack has ETag / `If-Match` machinery.** `00-facts.md` Q11 established
  it for A and asked whether B built its own. It did not — `git grep -i
  "etag\|if-match"` over `src/wxcli/migration/` returns nothing `[verified]`.
- **Target B's library layer never exits the process.** `typer.Exit`, `sys.exit`
  and `raise SystemExit` appear **zero** times across all 46,684 lines of
  `src/wxcli/migration/` — the single grep hit is a comment
  (`preflight/runner.py:319`) `[verified]`. The shared runtime does the opposite:
  `errors.py:203`, `errors.py:225`, `common.py:32`, `common.py:252`,
  `common.py:263` and `config.py:118` all terminate the process from library code.
  **On layering, B is right and A is wrong.** This matters for §8: the direction
  of "adopt the shared runtime" is not uniformly correct.
- **`asyncio.gather(..., return_exceptions=True)`** (`engine.py:822`) and the
  `try/except Exception` around the serial path (`engine.py:834-847`) mean an
  unexpected exception in one operation cannot take down a batch `[verified]`.
  That is a deliberate, correct containment choice and it is why D2 is a bounded
  defect rather than an unbounded one.

Two further Target B results that are strengths, recorded because the spec asks
about them and the answers are good:

- **Concurrency cannot race the dependency order.** The spec asks what happens to
  dependent objects when a parent write fails mid-flight (`:237`). Structurally,
  it cannot arise: `execute_all_batches`'s loop only calls `get_next_batch(store)`
  again after the current batch's `run_batch_ops` has been fully awaited *and*
  every op in it has been through `update_op_status` in the sequential loop that
  follows (`engine.py:876-964`, `:920-962`), and `get_next_batch`'s SQL filters on
  `dep.status NOT IN ('completed','skipped')` read live from the DB
  (`runtime.py:55-69`) `[verified]`. Batches do not overlap, so a dependent is
  never dispatched while its parent is still running. `tests/migration/execute/
  test_cascade_and_retry.py` covers this with 18 tests including an exhaustive
  `test_get_next_batch_never_returns_blocked_ops` — **run this session, 18/18
  pass**.
- **Serialization of the one-job-per-org types is real, not just declared.**
  `run_batch_ops` partitions on `SERIALIZED_RESOURCE_TYPES` (`engine.py:793-800`)
  and runs those in a plain `for … await` loop that never touches
  `asyncio.gather` (`:831-848`) `[verified]`.
  `tests/migration/execute/test_bulk_serialization.py::test_serialized_ops_do_not_overlap`
  proves it with a live active-counter asserting peak concurrency of 1 — **run
  this session, passes**.

---

## 5. The preflight probe that structurally cannot run — severity, and its root cause

Phase 0 handed this forward `[verified]` but unjudged
(`00-context.md:427-439`). Confirmed here from both sides, and the cause is now
established.

**The defect.** `PreflightRunner._build_bulk_job_probe` returns a closure that
calls `api.session.ep("telephony/config/jobs/devices/callDeviceSettings")`
(`runner.py:327`) and `api.session.get(url, params=params)` (`runner.py:333`).
`api` is `wxcli.auth.get_api()` (`runner.py:312`, `:317`), whose session is
`WebexSession`, whose complete method set is `_headers`, `_request`,
`_json_or_raise`, `rest_get`, `rest_put`, `rest_post`, `rest_patch`,
`rest_delete`, `follow_pagination`, `follow_page_param`, `follow_scim`
(`auth.py:215-367`) `[verified], read in full`. **Neither `ep` nor `get` exists.**
The probe also catches `requests.RequestException` (`runner.py:334`) while
`WebexSession` is `httpx` (`auth.py:206`).

**Root cause, which Phase 0 did not name.** The docstrings say what this was
written against: *"Uses `WebexSimpleApi` so auth/orgId injection matches the rest
of…"* (`runner.py:295`), *"The runner wires this via the authenticated
`WebexSimpleApi` session"* (`checks.py:849`), and `runner.py:156`
`[verified]`. `WebexSimpleApi` is `wxc_sdk`'s class — it exposes `session.ep()`
and `session.get()` and is built on `requests`. **`wxc_sdk` is not a dependency of
this repo and `WebexSimpleApi` is defined nowhere in it** (`git grep` over `src/`,
`tools/`, `pyproject.toml` returns only those three comment mentions)
`[verified]`. The probe was written for a different HTTP client, repointed at
`wxcli.auth.get_api()`, and never adapted — the `.ep`/`.get` calls and the
`requests` catch are all residue of the original.

**Why it survived: the seam that made the check testable made the defect
untestable.** `check_bulk_device_job_support` takes `probe_fn` as an injected
callable, which is good design — and every one of the eight tests passes a lambda
(`tests/migration/preflight/test_checks.py:555`, `:561`, `:567`, `:574`, `:585`,
`:593`, `:604`, `:617`) `[verified]`. `_build_bulk_job_probe`, the factory that
actually builds the broken closure, is referenced **nowhere in `tests/`** — its
only three mentions in the whole repo are its definition (`runner.py:290`), its
one caller (`runner.py:159`), and a docstring (`checks.py:850`) `[verified]`. The
check is thoroughly tested; the only part of it that is wrong is the part no test
constructs.

**Severity: this is the second-worst kind of guard — one that reports a colour it
did not earn.** The chain, all `[verified]`:

1. Every invocation raises `AttributeError: 'WebexSession' object has no
   attribute 'ep'` at `runner.py:327`.
2. `except Exception` at `checks.py:875` catches it and returns
   `CheckStatus.WARN`, detail `"Bulk device job probe failed: …"`
   (`checks.py:876-882`).
3. `_STATUS_PRIORITY` ranks `WARN: 2` below `INCOMPLETE: 3` and `FAIL: 4`
   (`runner.py:42-48`), and the overall verdict is the worst status
   (`runner.py:71-73`, `:215`).
4. The gate is `result.overall not in (CheckStatus.FAIL, CheckStatus.INCOMPLETE)
   and check is None` (`commands/cucm.py:1771-1774`). **WARN passes.**

So check 10 of 10 — the one that verifies the org supports the bulk device jobs
that touch *every device in the org* — has never returned PASS or FAIL in its
life, and cannot stop anything.

**What makes this a machinery finding rather than a bug report:** the repository
already built the exact mechanism for this case and wired it into the gate. The
`INCOMPLETE` status exists precisely so that *"a check whose required Webex data
was never retrieved"* cannot report a verdict it did not earn, and
`preflight/CLAUDE.md` states the doctrine — *"a definite failure is the more
actionable message, but 'we do not know' must still stop the gate"* — recording
that an earlier version of this same swallow (finding F06) made two
org-corruption checks report PASS with no token at all. **This check reproduces
F06's shape in a new place, three lines away from the fix.** `checks.py:875`
returning `CheckStatus.INCOMPLETE` instead of `WARN` would close it, and
`runner.py:324-336` calling `api.session.rest_get(...)` inside `except
WebexError` would make the probe actually run.

One bound on the severity, in fairness: `execute()` performs **no state or
preflight check at all** (`[verified]` — no `state`, `preflight`, `_require_stage`
or `stage` reference anywhere inside `cucm.py:3149-3242`), so preflight does not
gate execution in the first place. A broken check inside an advisory gate is less
costly than one inside a blocking gate. It is more costly in the other direction:
the `cucm-migrate` skill calls preflight MANDATORY and NOT SKIPPABLE, so the
operator is told to trust a verdict that one tenth of is fabricated.

### 5.1 — and fixing the probe alone would not close the gap

`[verified]`, found while establishing the above. `preflight` has **two**
verdict-consumers and they disagree about `INCOMPLETE`:

| Consumer | `cucm.py` | Treats `INCOMPLETE` as |
|---|---|---|
| Stage/state gate | `:1771-1774` — `overall not in (FAIL, INCOMPLETE) and check is None` | **not passing** — stage not marked, `ProjectState` not advanced |
| **Exit code** | `:1797-1798` — `if result.overall == CheckStatus.FAIL: raise typer.Exit(1)` | **passing — exits 0** |

The exit-code branch carries a comment stating exactly why it exists:
*"The exit code has to carry the verdict. A caller that gates on `$?` (the
cucm-migrate skill calls preflight MANDATORY, NOT SKIPPABLE) otherwise reads
success from a run that printed 'Overall: FAIL'"* (`cucm.py:1794-1796`).
`INCOMPLETE` is the status this repository invented for *"we could not check"*,
and `preflight/CLAUDE.md` states the doctrine that *"'we do not know' must still
stop the gate."* **The exit code lets it through.** A `--check <one>` partial run
likewise exits 0 while printing *"The preflight gate is NOT satisfied"*
(`:1786-1792`).

The two findings interlock, and the sequencing matters: today the bulk-job probe
returns `WARN`, so it never reaches this hole. **Correcting `checks.py:875` to
return `INCOMPLETE` — the right fix — would move the failure from one silent path
to another.** `cucm.py:1797` must widen to `in (FAIL, INCOMPLETE)` in the same
change, or the fix is invisible.

---

## 6. Errors, exit codes, and output — the two error languages

`errors.py` is never imported on the migration path (§2.3). This section is what
replaces it.

### 6.1 How a Webex error becomes text

`[verified]` The engine never raises on an HTTP error. It builds a string
(`engine.py:205-210`):

```python
if resp_status >= 400:
    error_msg = resp_body.get("message") or resp_body.get("errors", str(resp_body))
    return OpResult(node_id=node_id, status=resp_status,
                    error=f"{resp_status}: {error_msg}", body=resp_body)
```

with `resp_body` set to `{}` whenever the body will not parse as JSON
(`engine.py:193-196`). Reproduced literally `[verified]`:

| Response | Target B renders | Target A would render |
|---|---|---|
| HTML error page / empty body / gateway error | **`500: {}`** | `Error: <title text>` via `_truncate_html` (`errors.py:76`) + `_STATUS_TIPS` |
| JSON with `message` | `400: Bad Request` | same text **plus** errorCode tip, id-kind decode, status tip |
| JSON with only `errors` | `409: [{'description': "email 'a@b.com' already exists"}]` — a Python repr | parsed via `_extract_error_code` (`errors.py:63`), keyed to a tip |

**`500: {}` is the finding.** The one shape Target A specifically defends against
— a non-JSON error response — is the shape Target B reduces to an empty dict. An
autonomous operator retrying on that string has nothing to act on.

### 6.2 Actionability parity, item by item

| `errors.py` mechanism | Target B equivalent |
|---|---|
| `_extract_error_code` (`:63`) → 5 errorCode tips (`:28-34`) | **none** |
| `decode_id_kind` (`:90`) + `Ids you passed, decoded:` (`:198-202`) | **none** |
| `_MESSAGE_TIPS` (`:36-45`), incl. the "Unauthorized request:" / unlicensed-user tip | **none** |
| `_is_cc_403` → CC-scope tip (`:157`, `:185`) | **none** — n/a, migration does not call CC |
| `_STATUS_TIPS` for 400/401/403/404/405/409/429 (`:49-60`) | **none** |
| `_truncate_html` (`:76`) | **none** — collapses to `{}` |
| `handle_network_error` + `_NETWORK_TIPS` (`:206-225`) | **none**; `aiohttp.ClientError` becomes `Connection error: {e}` (`engine.py:226-229`) |

`docs/reference/authentication.md:583` discloses part of this: the hand-written
seams including `cucm` *"do not add the `httpx.HTTPError` catch, so a transport
failure inside one of those still reaches the terminal as a Python traceback."*
That caveat is accurate and is the one place the docs admit the split. It does
not cover the retry policy, the env vars, or the tip machinery.

### 6.3 Exit codes

`[verified]` — `grep -o "typer\.Exit([^)]*)"`:

| Scope | Exit 1 | Exit 2 | Notes |
|---|---:|---:|---|
| `commands/cucm.py` | 48 | 1 | the single `Exit(2)` is `WXCLI_PLAN_FAIL_ON_UNRESOLVED` on `plan` |
| `src/wxcli/migration/` (46,684 lines) | **0** | **0** | the one grep hit is a comment (`preflight/runner.py:319`) |

So the *codes* agree with Target A — 1 for failure, 2 reserved for a declared
opt-in — and the layering is cleaner (§4). The divergence is **when** they fire.

**`wxcli cucm execute` exits 0 when operations fail.** `[verified]` from source:
`execute()` (`cucm.py:3149-3242`) prints `Completed:` / `Failed:` and a tip
(`:3232-3240`) and returns; there is no `raise` on `summary["failed"] > 0`, and
the only exits in the function are the no-token guard (`:3176`). The source
matches the design note in `migration/execute/CLAUDE.md`
(*"`wxcli cucm execute` exits 0 even with `Failed: N` — decided, not overlooked"*),
and that note's reasoning holds: partial failure is the expected mid-migration
state, the documented recovery loop is `retry-failed` → `execute` repeated, and a
non-zero exit would break a `set -e` wrapper around exactly that loop.

**I agree with the decision and disagree with its blast radius.** The note's
justification is "nothing reads this exit code" — true today, and it is the
*only* thing making exit 0 safe. On a published CLI whose exit codes are contract
(`00-facts.md` Q18), "no current caller gates on it" is a statement about today's
callers, not about the contract. The cheap fix is not `--fail-on-failures` (the
note rejects it, correctly, as speculative surface); it is to say so in the help
text, which currently does not mention the exit behaviour at all.

The asymmetry that *is* a defect: `wxcli cucm preflight` exits non-zero on FAIL /
INCOMPLETE (`cucm.py:1771-1774`) while `execute` exits 0 on any outcome, and
nothing in either command's `--help` distinguishes them. Two commands in one group
with opposite exit semantics and no disclosure is a trap for an operator whose
only specification is `--help`.

### 6.4 Output: stdout/stderr discipline

`[verified]` `cucm.py` defines two consoles — `console = Console()` (`:43`,
**stdout**) and `report_console = Console(stderr=True)` (`:54`). The execute path
uses `console` throughout, so **errors go to stdout**:

- `cucm.py:3175` — `[red]Error:[/red] No token. Run 'wxcli configure' first.` → stdout
- `cucm.py:3210` — `[yellow]Warning: Could not retrieve calling license ID[/yellow]` → stdout
- `cucm.py:3233` — `[red]Failed:[/red] N` → stdout

Target A's convention is data on stdout, notes and errors on stderr —
`handle_rest_error` and `handle_network_error` pass `err=True` on every line
(`errors.py:189`, `:191`, `:202`, `:223`, `:224`), and `auth.py`'s paging note
does the same (`auth.py:155`). **Target B inverts it on the one command whose
output an operator is most likely to pipe.** `DISAGREE — A is right.`

Adoption of the shared output layer is partial and measurable: `cucm.py` contains
**18 `emit(` occurrences (13 real call sites) against 288 console prints — 277
`console.print` plus 11 `report_console.print`** `[verified], independently
reproduced`. Measured over all 27 `cucm` leaf commands via
`COLUMNS=400 wxcli cucm <cmd> --help` `[verified]`:

- **10 carry both `-o/--output` and `--fields`**: `preflight`, `decisions`,
  `inventory`, `next-batch`, `execution-status`, `rollback-ops`, `dry-run`,
  `report`, `user-diff`, `user-notice`.
- **17 carry neither**: `init`, `status`, `discover`, `normalize`, `map`,
  `analyze`, `plan`, `decide`, `export`, `import-locations`, `mark-complete`,
  `mark-failed`, **`execute`**, **`retry-failed`**, and the three `config` leaves.
- No command has one without the other — the convention is applied consistently
  where it is applied at all.

Against the generated surface, where **every** command takes both
(`CLAUDE.md`, *Common Flags*), that is 17 of 27 commands in a mounted group
breaking the tool's most-used convention — including the two that write.

Below `cucm.py`, the migration tree prints directly too, though rarely: **6
`console.print` calls across three files, each of which instantiates its own
`Console()`** — `cucm/discovery.py:41`, `cucm/extractors/users.py:25`,
`cucm/extractors/devices.py:23` `[verified]`. Repo-wide there are eight `Console`
instances (`src/wxcli/output.py:112`, `commands/cucm.py:43`, `:54`,
`commands/converged_recordings_export.py:18`, `commands/cleanup.py:41`, plus those
three), of which only `cleanup.py`'s is on stderr. There are zero `typer.echo`
calls anywhere in `migration/`.

Where `emit` *is* used it behaves correctly: `execution-status -o json` returns
early at `cucm.py:2937-2954` before any `console.print`, so it emits a single
clean JSON document on stdout, equivalent to a generated command's
`[verified]`. The split between the two `Console` objects is deliberate and
documented in a comment at `cucm.py:44-52` — `report`/`user-diff`/`user-notice`
use the stderr console so `| jq` works. **The reasoning is right and `execute`
is simply not covered by it.**

**Progress disclosure during the run.** `on_progress` is
`lambda msg: console.print(msg)` (`cucm.py:3216-3217`). The engine calls it once
per batch before work starts (`engine.py:886-887`) and once per op
(`engine.py:961-962`) — but the per-op calls happen in the sequential loop *after*
`await run_batch_ops(...)` has returned, so every op line in a batch prints in one
burst at the end rather than streaming as each call completes `[verified]`. Ops
resolved as `SkippedResult` (`engine.py:902-911`) or as empty-`[]` no-ops
(`:912-916`) never enter `tasks` and therefore **produce no progress line at
all** — they are invisible until someone runs `execution-status`. Nothing is
persisted; the entire progress record is terminal-only for the life of the
process.

### 6.5 Token and PII exposure

`[verified]`

- **Token:** not reachable. The bearer token lives in the session headers
  (`engine.py:870-873`); nothing echoes request headers into `OpResult.error` or
  into the store.
- **PII: yes, and it is persisted.** When a Webex error body carries no `message`
  key, `error_msg` becomes the repr of the `errors` list (§6.1), which for
  duplicate-user and number-conflict rejections routinely contains the submitted
  email or DID. That string is written to `plan_operations.error_message`
  (`engine.py:953`, `:957` → `runtime.py:213-216`) and read back by
  `wxcli cucm execution-status`. A migration store is therefore a file containing
  end-user emails in its error column. Not a leak to a third party, but it is PII
  at rest in a location nobody has declared as holding PII.

---

## 7. The other stacks: AXL, Unity, and local file mutation

### 7.1 The full stack table

Every cell `[verified]` or `UNKNOWN`. This is the deliverable of item 3.

| | Webex REST — A | Webex REST — B (execute) | CUCM AXL | Unity CUPI | Local files |
|---|---|---|---|---|---|
| Library | `httpx` sync (`auth.py:206`) | `aiohttp` async (`engine.py:17`) | `zeep` over `requests` (`cucm/connection.py:20-24`) | `requests` (`unity_connection.py:15`) | `pathlib`/`shutil` |
| Connect timeout | 10s, env-tunable (`auth.py:192`,`:210`) | aiohttp default `sock_connect=30` (`engine.py:875`) | 5s hard-coded on the probe (`connection.py:125`) | **none passed** — see below | n/a |
| Read timeout | 60s, env-tunable (`auth.py:193`,`:212`) | aiohttp default `total=300` | **none on SOAP calls** — see 7.2 | **none** — inert 30s, see 7.3 | n/a |
| Retry | 5 statuses, bounded, jittered (`auth.py:157-188`) | 429 only, unjittered (`engine.py:199-203`) | **none** | **none** | n/a |
| TLS verification | httpx default **on** | aiohttp default **on** | **`verify_ssl: bool = False`** (`connection.py:174`, applied `:189`) | **`verify_ssl: bool = False`** (`unity_connection.py:42`, applied `:48`) | n/a |
| Warnings | — | — | `urllib3.disable_warnings(InsecureRequestWarning)` at import (`connection.py:27`) | inherits that suppression | — |
| Operator sees on failure | `Error:` + keyed `Tip:` on **stderr** (`errors.py:189-191`) | `"{status}: {msg}"` in a summary on **stdout**; `500: {}` if non-JSON | per-extractor `ExtractionResult.errors` + status (`discovery.py:212-215`) | `logger.warning`, returns `None`/`[]` (`unity_connection.py:79`, `:238`, `:280`) | `err=True` on stderr (`init_playbook.py:185-188`, `update.py:176`) |
| Exit code | 1 (`errors.py:203`,`:225`) | **0**, even with failures (§6.3) | 1 via `_abort_if_nothing_discovered` on total failure (`cucm.py:1307`) | never — Unity failure is non-fatal | 1 |

### 7.2 Does an AXL fault arrive distinguishably? — **Yes, and better than Webex's.**

This is the answer I did not expect. `[verified]`

`zeep.exceptions.Fault` is never referenced by name anywhere in
`cucm/connection.py`; the module defines one exception, `AXLConnectionError`
(`:32`), raised only from the two connect-time paths (`:208`, `:220`). Faults
raised *during* a query are caught generically. But the structure that catches
them is per-extractor and typed:

- `connection.py:359-361` — a fault inside a single `get*` call logs
  `logger.warning("[%s] %s", method_name, exc)` and returns `None`. zeep's
  `Fault.__str__` is the faultstring, so the CUCM-side message survives.
- `discovery.py:212-215` — a fault that escapes an extractor is caught per
  extractor and recorded as `ExtractionResult(extractor=name)` with
  `errors.append(f"Unrecoverable error: {exc}")`, alongside a
  `status` of `ok`/`partial`/`failed`/`unsupported` (`discovery.py:98`).
- `connection.py:295-320` handles the specific AXL schema-mismatch case — a
  `returnedTag` the cluster's AXL version does not know — by dropping the tag,
  retrying, and **accumulating what was dropped** into `dropped_tags`
  (`:311-318`), snapshotted into `raw_data.json` (`:322-324`) so *"a partial
  result cannot later be mistaken for a complete one"* (`:307-309`).

**A partial extraction is therefore distinguishable from a total one, and a total
one aborts:** `_abort_if_nothing_discovered` (`cucm.py:1307-1310`) refuses to
mark the stage complete or advance `ProjectState` when nothing was extracted, with
the comment *"A run that extracted nothing is a FAILED run — every AXL call
failed."*

Bad credentials and an unreachable host are each caught by a dedicated branch
with hand-written remediation: a raw `socket.connect_ex((host, port))` probe
before any zeep code runs (`cucm.py:635-649`, VPN / hostname / firewall guidance
plus a `--from-file` fallback), and an `elif "401" in err_str:` branch naming the
AXL API Access role and service activation (`cucm.py:723-733`). Both exit 1.

**So the answer to item 3's question is the opposite of what it anticipates.**
AXL failures are *more* legible than Webex REST failures on the migration path:
they carry a per-source status, an accumulated record of what was lost, typed
remediation for the two common connect failures, and a hard abort on total
failure. The Webex write path has none of those — it has a flat
`"{status}: {msg}"` string and exit 0. **B is right on AXL and wrong on Webex,
inside the same subsystem.**

Four qualifications, all `[verified]`, and the first two are defects:

- **AXL SOAP operations have no timeout at all.** `Transport(session=session,
  timeout=timeout)` (`connection.py:190`) looks like it sets one, and does not.
  Checked against the installed zeep:
  `Transport.__init__(self, cache=None, timeout=300, operation_timeout=None,
  session=None)` — `timeout` governs **WSDL/XSD document loading only**, while
  `Transport.post()` and `Transport.get()` both pass `timeout=self.operation_timeout`,
  which `connection.py:190` never sets and which defaults to `None`. So every real
  AXL call — `listPhone`, `getPhone`, `executeSQLQuery` — runs unbounded. A CUCM
  host that completes the TCP handshake and then never answers hangs
  `wxcli cucm discover` forever, with no exception for the operator to see or
  retry on. This is the same class of defect as Unity's inert `session.timeout`
  (§7.3) and Target B's unset aiohttp timeout (D7): **three stacks, three
  different ways of ending up with no request timeout, and only `auth.py` has
  one.**
- **Per-object detail faults lose their text entirely.** The legibility above is
  real for *bulk* calls; it is not for detail calls. `AXLConnection.get_detail`
  (`connection.py:342-361`) catches broadly, logs `logger.warning("[%s] %s", …)`
  and returns `None`, so it never re-raises. The extractor therefore sees only
  `detail is None` and records a bare `"getPhone failed for {name}"`
  (`extractors/devices.py:97`) with **no fault text**. The faultstring survives
  only in a `logger.warning` that needs `--verbose` and is persisted nowhere.
  Same shape in `features.py`, `e911.py`, `moh.py`, `remote_destinations.py`,
  `device_profiles.py`, `informational.py`.
- **The faultcode is always dropped.** Nothing in `src/wxcli` imports
  `zeep.exceptions`, so `.code` is never read; `str(fault)` yields the faultstring
  alone.

- **The `ok/partial/failed/unsupported` label is not shown to a watching
  operator.** It is persisted per-extractor into `raw_data.json`
  (`discovery.py:135-152`) and read by the later stages, but `discover`'s console
  output prints only per-extractor counts and a run-wide `total_failed`
  (`cucm.py:1322-1326`). The distinction that makes the design good is invisible
  live.
- **The famous "Unknown fault occured" diagnosis is institutional knowledge, not
  inference.** `_report_failed_discovery` (`cucm.py:1095-1129`) samples the first
  few extractor error strings and prints a hand-written explanation naming that
  string as the WSDL-version-mismatch signature. It works, and it is a hard-coded
  string match rather than anything derived from the fault. It will not
  generalize to the next fault shape.

### 7.3 Unity Connection — read-only, confirmed; **and unreachable from any command**

**Start with the thing that reframes the rest of this subsection.**
`UnityConnectionClient` is **never constructed anywhere in `src/`** `[verified]` —
`grep -rn "UnityConnectionClient(" src/` returns zero. `run_discovery`'s
`unity_client` parameter defaults to `None` (`discovery.py:155-158`) and its only
caller passes two positional arguments: `run_discovery(conn, store)`
(`commands/cucm.py:1295`). `grep -in unity src/wxcli/commands/cucm.py` returns
**zero matches** — there is no `--unity-host`, no credentials option, no wiring of
any kind. Even the tests never run its constructor: they use
`UnityConnectionClient.__new__(UnityConnectionClient)`
(`tests/migration/cucm/test_unity_shared_mailboxes.py:14`, `:46`, `:57`, `:71`) to
bypass `__init__`.

**This corrects both prior artifacts, in opposite directions.** `00-facts.md` Q6
said *"No Unity … found in `src/`"* — wrong, the module is tracked and 304 lines
long. `00-context.md` Q4 refuted that and marked `cucm/` as **Reads Unity ✅**,
calling it "a third external system" — also wrong, operationally: nothing
instantiates it, so no `wxcli` command has ever opened a CUPI connection. The
accurate statement is the third one neither reached: **a complete, tested,
correctly-degrading Unity client exists and has no caller.**

Everything below therefore describes latent behaviour, not behaviour in the field
— which also explains how the two defects survived: `__init__` is the one method
no test executes.

`[verified]` Read-only is confirmed, not assumed: `session.post`/`put`/`patch`/
`delete` return **zero** matches across the file. There are **3** `session.get`
call sites (`:68`, `:235`, `:276`), reached through 6 `_get`/`_get_list` calls
from **8 public read methods**. (`00-context.md` Q4 says "eight call sites, all
`session.get`" and then cites those same three line numbers — the read-only
conclusion is right; the count conflated methods with sites.)

Two defects:

1. **The declared timeout does nothing.** `self.session.timeout = timeout`
   (`unity_connection.py:49`) sets an attribute `requests.Session` does not
   consult — `requests` takes `timeout` per-request only. None of the three
   `session.get` calls passes one (`:68-71`, `:235-237`, `:276`). **Every Unity
   call can hang indefinitely**, and the constructor's `timeout: int = 30`
   (`:43`) and its docstring (`:34`) both advertise a bound that is not enforced.
2. **TLS verification is off by default** (`:42`, applied `:48`), and the
   `InsecureRequestWarning` that would say so is globally suppressed by
   `cucm/connection.py:27` — a module-level `urllib3.disable_warnings` that
   affects the whole process, not just AXL.

Unity failure is correctly non-fatal: every path logs a warning and returns
`None`/`[]`, and `extract_shared_mailboxes` documents the contract that callers
must read absence as *"Unity Connection not available"* rather than *"no shared
mailboxes exist"* (`unity_connection.py:230-233`). That is the right call and it
is written down.

On TLS: defaulting `verify_ssl=False` for on-prem CUCM/Unity, which routinely
run self-signed certificates, is a defensible engineering choice and I am not
calling it a defect. The defect is that it is a **silent** default —
`disable_warnings` at import means nothing on stdout or stderr ever tells the
operator the AXL and CUPI sessions are unverified.

### 7.4 Local file mutation — `init` is careful, and `update` does not undermine it

`[verified]`

`wxcli init` will not clobber: it computes collisions up front, prints every
colliding relative path to **stderr**, and refuses — *"Re-run with --force to
overwrite them, or choose an empty folder"* (`init_playbook.py:183-188`). It also
skips rewriting files whose bytes already match (`:98`), and its deletions are
manifest-scoped: `apply_bundle` removes only `owned - bundle_files` (`:103-109`)
and `do_uninstall` keeps any path still owned by a profile that stays installed
(`:122-128`). **It never deletes a file it did not create.** This is the most
careful write path in the repository.

With one exception, and it is the sharpest thing in this subsection:
**`wxcli init --uninstall` deletes files with no confirmation at all**
`[verified]`. `init()` handles it at `:167-169` — `if uninstall: do_uninstall(...);
return` — which returns *before* the `--force`/`--yes`/`typer.confirm` logic at
`:190-193` is ever reached, and `do_uninstall` itself (`:113-137`) contains no
`typer.confirm`; it goes straight to `target.unlink()` (`:131`). So the flags that
exist to gate destructive behaviour are structurally unreachable on the one
subcommand that only destroys. There is no `--dry-run` either — verified against
`COLUMNS=400 wxcli init --help`, whose full option set is `--claude-only`,
`--codex-only`, `--force`, `--yes`, `--uninstall`, `--help`. Scope is bounded (the
manifest), which is why this is a gap rather than a catastrophe, but it is the
same generated-surface asymmetry inverted: there, every `DELETE` prompts; here,
the only local delete does not.

`wxcli update` does **not** bypass that guard, and an earlier draft of this
section said it did. Corrected `[verified]`: the collision check is nested inside
`if all(m is None for m in manifests.values())` (`init_playbook.py:182`) — it
protects a *fresh, manifest-less* install only. `refresh_playbook` returns early
unless a manifest already exists (`update.py:158-161`) and restricts
`--claude-only`/`--codex-only` to the installed profiles (`:170-174`), so the
`wxcli init --force` it execs (`update.py:175`) always lands on the `elif` branch
(`init_playbook.py:190-193`) instead. There `--force` suppresses the
*refresh confirmation*, which `update.py:166` has already asked — a second prompt
would be worse, so this is correct design, not a bypass.

What remains is small and worth one line: `init` rewrites any owned file whose
bytes differ from the bundle (`init_playbook.py:98`), so a hand-edited playbook
file **is** replaced. The inner prompt discloses this — *"(owned files only)"*
(`init_playbook.py:191`) — but the outer prompt the operator actually answers does
not: *"This folder holds a wxops playbook. Refresh it to v{latest}?"*
(`update.py:167`). `--yes` skips it entirely (`:166`).

The hidden option is confirmed: `--hook` at `update.py:216`, `hidden=True`. It is
the 51st `hidden=True` occurrence and the only hidden *option* rather than a
command alias (`00-context.md:227-228`). It exists for the bundled `SessionStart`
hook, which runs `wxcli --no-update-check update --hook`
(`00-context.md:167-169`) — a legitimate reason to keep it out of `--help`.

Error output here goes to stderr with `err=True` (`init_playbook.py:185`, `:188`;
`update.py:176`), i.e. these hand-written commands follow Target A's stream
convention that `cucm execute` breaks (§6.4).

---

## 8. The decision

**The split stands. The transports stay separate; the *policy* is extracted and
shared; and the shared runtime absorbs two things Target B does better.** Stated
as an answer, not a menu.

### Why not "Target B adopts the shared runtime"

`httpx`-sync versus `aiohttp`-async is a real requirements difference, not an
accident. Unifying it means one of two disproportionate changes: make `auth.py`
async, which touches all 1,857 generated commands and the published surface; or
make the engine synchronous, which deletes the concurrency that is the entire
reason `cucm execute` exists. Neither is warranted by anything in §3 — **not one
disagreement in this phase is caused by the choice of HTTP library.**

### Why not "leave the split alone"

Because the disagreements are not transport-level. Every one of D1, D2, D3, D4,
D7 and D12 is a *policy* expressible as a pure function of `(status, attempt,
headers, env)` — nothing in `RETRY_STATUSES` (`auth.py:160`),
`MAX_RETRY_AFTER_SECONDS` (`:159`), `_backoff_delay` (`:184`), `_retry_enabled`
(`:171`), `_max_attempts` (`:177`) or `_env_float` (`:196`) touches `httpx`. They
are roughly 40 lines that both stacks could import unchanged. The split is
defensible; **six divergent policies behind one binary's published contract are
not.**

### What each side takes from the other

**B adopts from A** — the retry policy module above; `_truncate_html` and
`_extract_error_code` from `errors.py` (§6.1, the `500: {}` case); and the
`WXCLI_*` env contract (§2.2), which is published and currently half-implemented.

**And one thing all four non-`auth.py` stacks need, which the policy module does
not cover: a request timeout.** This phase found three independent ways of not
having one — B's aiohttp session sets none and inherits an unpinned library
default (D7); AXL sets zeep's WSDL-load timeout and leaves `operation_timeout`
at `None`, so SOAP calls are unbounded (§7.2); Unity assigns
`session.timeout`, an attribute `requests` does not read, so CUPI calls are
unbounded (§7.3). Only `auth.py` states its timeouts as named constants and lets
the operator move them. Three different mistakes with one shape is a convention
problem, not three bugs, and the convention is already written down in one file.

**A adopts from B**, and this direction is the one the audit spec did not
anticipate:

1. **No process exit from library code.** B has zero `typer.Exit`/`sys.exit`
   across 46,684 lines; `errors.py`, `common.py` and `config.py` all exit from
   library modules (§4). B's layering is correct and A's is not.
2. **Structured per-source failure records.** `ExtractionResult` with an
   `ok/partial/failed/unsupported` status plus an accumulator of what was lost
   (§7.2) is a better shape than `handle_rest_error`'s print-and-exit for
   anything that processes more than one object — and the generated surface is
   growing bulk and job endpoints (`00-context.md` Q1 classes 3 and 4) that will
   need exactly it.

### What pins current behaviour first — and the constraint C2 imposes

The audit spec sequences Target B remediation on the premise that AXL is pinned
by recorded responses and Webex is not (`wxops-architecture-audit-prompt_2.md:282`).
**§0/C2 removes that premise: nothing is pinned by recorded responses, for either
system.** The sequence has to start further back, and cheaper than expected:

1. **Repair `tests/test_auth.py`, then track it.** *(Revised — an earlier draft of
   this step said "add one line to `.gitignore`". That was wrong: the file is not
   merely untracked, it is **18-of-24 failing**, so tracking it as-is would break
   CI. See §0/C2a.)* Repoint the ten `patch("wxcli.auth.httpx.request", …)` targets
   to survive `auth.py`'s lazy import — patching `httpx.request` itself works,
   because the method re-resolves it on every call. Confirm 24/24 green, then add
   `!tests/test_auth.py` to `.gitignore` beside the other 23 re-includes. It uses
   only `tmp_path` and `monkeypatch`, so it clears the bar the `.gitignore` comment
   sets for tracked tests — no dependency on the untracked `tests/conftest.py`
   `[verified]`. **This restores the only executable proof of the behaviour the
   whole unification is built around, and it comes first for that reason.**
2. **Characterize the engine with `aioresponses`, which CI already installs**
   (`ci.yml:35`) and `tests/migration/execute/` already uses. Five tests, all
   currently absent: a 503 is retried; a date-form `Retry-After` does not become
   a failed op; a `Retry-After` above the cap is clamped; two concurrent 429s do
   not wake together; `_try_find_existing` rejects a name that is not an exact
   match. Each is a red test today — which is the point: they encode the intended
   behaviour before the refactor moves anything.
3. **Then extract the policy module** and have both `auth.py` and `engine.py`
   import it.
4. **Then add the gate check** that asserts both stacks read the same constants.
   This is not optional garnish — `02-drift.md` F3 established that the 24 guards
   added on 2026-08-04 are unpinned because no check asserts them, so a render-path
   change would drop them and ship green. **A unified retry policy with no check
   over it re-diverges the same way.** The gate's total current coverage of Target
   B is three documentation counts (§1), so this would be the first check that
   reads Target B behaviour at all.

**And decide what to do about `tests/fixtures/axl-responses/`.** Eighteen recorded
AXL responses sit on one developer's disk, untracked and referenced by nothing.
Either track them and wire them into `tests/migration/cucm/`, or delete them.
Leaving them is the worst option: this audit's own reconnaissance mistook them for
a safety net and built a remediation plan on it.

**Not on this list, deliberately:** merging `rate_limiter.py` into the engine.
Delete it (and fix `docs/architecture/04-operations-and-evolution.md:357`).
Reviving a dead module whose five parameters all contradict what runs would be
adopting a specification nobody has ever validated against the live API.

---

## 9. Read coverage

Target B is 46,684 lines. This is what was actually read and what was inferred.

**Method note on the parallel work.** Five workers covered one concept row each.
**Every claim of theirs reproduced above was re-verified here against source
before being written down** — that check caught nothing wrong in their reports and
caught two errors in mine (§10). Where a worker's framing and mine differed I
kept theirs only after reading the code myself; three of their findings changed
this document materially (the AXL `operation_timeout` gap, Unity having no
caller, and `init --uninstall`'s missing confirm), and each is cited from source
here rather than from their report.

**Third-party library behaviour was verified by introspection, not assumption**
`[verified]`: `zeep.transports.Transport.__init__`'s signature and the
`operation_timeout` usage inside `post()`/`get()`; `requests.Session.__attrs__`
(no `timeout`); `aiohttp.client.DEFAULT_TIMEOUT`; `logging.lastResort`'s level and
stream.

**Read in full** (me or a worker, cross-checked): `src/wxcli/auth.py` (407),
`src/wxcli/errors.py` (225), `src/wxcli/config.py` (139),
`src/wxcli/migration/rate_limiter.py` (145),
`src/wxcli/migration/execute/engine.py` (964),
`src/wxcli/migration/execute/runtime.py` (571),
`src/wxcli/migration/cucm/unity_connection.py` (304),
`src/wxcli/migration/preflight/__init__.py` (96).

**Read in the regions that matter, grepped elsewhere:**
`src/wxcli/commands/cucm.py` (3,525 lines — read `:1140-1200`, `:1280-1330`,
`:1740-1800`, `:2930-3010`, `:3140-3270`; the remaining ~3,200 lines were
`grep`ped for exits, consoles, `emit`, `ctx`, `orgId`, `basicConfig`);
`src/wxcli/migration/execute/handlers.py` (2,403 — read `:55-80`, `:455-520`;
grepped for `ctx.get`, `_url`, verbs);
`src/wxcli/migration/cucm/connection.py` (read `:95-230`, `:290-370`; grepped for
except/raise/verify/timeout);
`src/wxcli/migration/preflight/{runner,checks}.py` (read `:290-360` and
`:840-900`; grepped for status priority and gate logic);
`src/wxcli/commands/{init_playbook,update}.py` (read the write/confirm regions);
`src/wxcli/{common,output}.py` (read `emit` and `plain_mode` only);
`tools/drift_check.py` (grepped for `migration` only — §1's claim is a grep
result, not a read).

**Executed:** `tests/migration/execute/test_engine.py` (9/9 pass),
`test_cascade_and_retry.py` (18/18), `test_bulk_serialization.py`
(`test_serialized_ops_do_not_overlap` passes). Read but not run:
`tests/test_auth.py`, `test_engine_409_recovery.py`,
`tests/migration/preflight/test_checks.py`. **The full suite was not run**
(project rule).

**Not read at all — inferred from neighbours or simply not covered.** These four
stages are 31,570 of Target B's 46,684 lines and `00-context.md` Q4 establishes
that **none of them makes any remote call**, which is why this phase — scoped to
the two stacks and the remote-write path — does not cover them:
`transform/` (18,517), `report/` (8,302), `advisory/` (3,738), `export/` (1,013).
Also not read: `migration/store.py` beyond the `journal` schema,
`migration/state.py`, `migration/decision_state.py`, `migration/models.py`,
`execute/{planner,dependency,batch}.py`, and the 13 AXL extractors under
`cucm/extractors/`.

**Claims I am explicitly not making:** that `transform/`, `report/`, `advisory/`
or `export/` are clean — I did not read them. That `handlers.py`'s 67 handlers are
correct — I read three. That the drift gate does nothing else with Target B — I
grepped for one string.

**One tracked doc was corrected; no code was changed.**
`docs/architecture/04-operations-and-evolution.md:357` told contributors to build
new bulk modules on `rate_limiter.py`. It is the only tracked, shipping document
that carries an audit-relevant claim, and it was actively misdirecting; the
sentence now says what actually runs and points here. Under the remediation rule, two findings
qualify on root cause (`unity_connection.py:49`'s inert timeout;
`checks.py:875`'s `WARN`) but both fail the "no later phase would teach you more"
test: §5.1 shows the preflight fix needs a paired change in `commands/cucm.py`
that Phase 5 should scope, and the `.gitignore` and `rate_limiter.py` items sit
outside `migration/` and the generator. Everything is sequenced in §8 instead.
The working tree is unchanged apart from this file. (For the record, the tree was
already carrying the previous session's uncommitted generator work when this
phase began, exactly as the brief stated.)

---

## 10. Handed forward

**Corrections this phase makes to earlier artifacts** — each already argued above:

| Claim | Where | Measured |
|---|---|---|
| Target B's retry policy is `migration/rate_limiter.py` (`max_concurrent=5` etc.) | `00-facts.md` Q7; audit spec `:264-265` | **Dead code, imported by nothing.** The policy is inline in `engine.py` and shares no parameter with it (§0/C1) |
| Recorded AXL responses exist at `tests/fixtures/axl-responses/`; Webex has none | `00-facts.md` Q15; audit spec `:282`, `:292`, `:317` | **Neither exists in the repo.** The directory is gitignored *and* referenced by nothing; zero non-`.py` files are tracked under `tests/` (§0/C2) |
| Unity is "a third external system" the pipeline reads (`cucm/` → Reads Unity ✅) | `00-context.md` Q4, refuting `00-facts.md` Q6 | **Both are wrong, oppositely.** The module is real and tracked (Q6 wrong), but `UnityConnectionClient` is constructed **nowhere in `src/`**, `run_discovery` is called with two args, and no CLI option supplies credentials — **no `wxcli` command can reach Unity** (Q4 wrong). Read-only is correct; the "8 call sites" are 3 `session.get` sites behind 8 read methods (§7.3) |
| CUCM AXL calls have a 30s timeout | this document's own §7.1, first draft | **Corrected in place.** `Transport(timeout=…)` bounds WSDL loading only; SOAP operations use `operation_timeout`, never set, default `None` — **AXL calls are unbounded** (§7.2) |
| 409 auto-recovery covers 7 resource types | `migration/execute/CLAUDE.md` | **8** — `line_key_template` is uncounted (§3, D8) |
| `wxcli update` bypasses `init`'s collision guard | **an earlier draft of this document** | Wrong, and corrected in place: the guard is unreachable from that path by construction (§7.4) |

**Open, and belonging to later phases:**

1. **Are the Webex `name=` filters exact-match?** D8's severity turns on it and no
   recorded response exists to settle it. A live read would answer it in one
   call — but the one-line equality check is worth adding either way.
2. **Does a re-issued create actually duplicate?** D13's blast radius depends on
   per-endpoint uniqueness enforcement, which is `UNKNOWN` per resource type.
   → Phase 5.
3. **The `journal` table** (`store.py:120-130`) — an audit-log schema with a
   `pre_state` column no caller populates, written only by the two read-only
   discovery sites. It is the natural home for the request/response record that
   would make D13 and D8 diagnosable after the fact. → Phase 5 and Phase 1.
4. **Per-stage test decomposition.** §9 shows the execute path is genuinely
   tested; whether the 214 migration test files are *concentrated* on the 31,570
   no-network lines is the question Phase 7 must decompose before quoting the
   number. This phase found the tracked/untracked split
   (`tests/test_auth.py` absent from a clone) that Phase 7 should start from.
5. **`tools/drift_check.py` beyond its 15 `migration` hits** — I grepped, did not
   read. §8's step 4 proposes the first behavioural check over Target B; whether
   the gate has a natural seam for it is unestablished.
