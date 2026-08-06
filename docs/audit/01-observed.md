# 01 — Observed: what actually breaks under agent operation

**Phase 1, revised.** Mined from existing transcripts. **No code was changed and no
`wxcli` command was run.** Every count below is measured from the Claude Code
transcript store; extraction scripts live in the session scratchpad, not the repo.

> **Read this before any number in this document.** One operator, one machine, no
> downstream users. A count here means *"how often Adam's agent did X"* — never
> *"how often users do X."* Treat every frequency as **ordinal**, not as a rate:
> useful for ranking shapes against each other, worthless as a population estimate.
> The brief says this and it bears repeating, because the counts below are large
> enough to look like a sample and are not one.

---

## 0. Method, denominators, and four corrections to the brief

### 0.1 The substrate is 4.2× larger than the brief states, and it is in the wrong place

`[verified 2026-08-05]` The brief and the audit spec's STATUS block both describe
**132 (or 128) transcripts** holding **157 `wxcli` invocations**. Both counted only
the top-level session files. Measured:

| | Files | Size | Date range |
|---|---:|---:|---|
| Main-session transcripts (top level) | **136** | 196 MB | 2026-07-06 → 2026-08-05 |
| **Subagent transcripts** (`*/subagents/*.jsonl`) | **433** | 144 MB | **2026-06-30** → 2026-08-05 |
| **Total** | **569** | **347 MB** | 2026-06-30 → 2026-08-05 |

The subagent tree is not a detail. **1,817 of 2,062 `wxcli`-invoking Bash calls —
88% — come from subagents, not from the main session.** The split is corroborated
independently by the transcripts' own `isSidechain` flag, which agrees exactly
(1,817 true / 245 false).

This is the single most important fact for anyone deciding where to attach a logger,
and it is a direct consequence of the project's own design: `CLAUDE.md` forbids the
main session from running `wxcli` and routes everything through
`wxc-calling-builder`. **The brief's substrate description would have pointed Phase 1
at the 12% slice.** The subagent tree also starts six days *earlier* than the main
transcripts.

### 0.2 The counts, and how they were derived

`[verified]` A Bash call is counted as a `wxcli` invocation when, after splitting on
`|| && ; | newline $( \``, stripping leading environment assignments and
`time`/`nohup`/`timeout` wrappers, some segment's first token is `wxcli`.

| Quantity | Count |
|---|---:|
| Bash calls invoking `wxcli` | **2,062** |
| — from subagents / main session | 1,817 / 245 |
| `wxcli` segments (chained calls counted separately) | **2,515** |
| Distinct transcripts containing one | **238** of 569 |
| Blocked by the `PreToolUse` gate, never executed | **126** |
| Rejected by the user at the permission prompt | **3** |
| **Actually executed** | **1,933** |
| — of those, carrying `--help` | **837 (43%)** |
| — non-`--help` "work" calls | **1,096** |
| Executed calls that failed | **81** (75 of them non-`--help`) |
| **Failure rate over non-`--help` work calls** | **6.8%** |

The spec's 157 is not reproducible by any method I tried and I did not try to
reverse-engineer it; it is superseded, not corrected.

### 0.3 The extraction trap — three ways this measurement silently returns zero

Stated because the next person to mine this substrate will hit all three, and each
one fails *quietly*, in the direction of "everything is fine."

1. **A failed tool call stores `toolUseResult` as a JSON *string*; a successful one
   stores an *object*.** `[verified]` Guarding on `type == "object"` — the natural
   way to reach `.stdout`/`.stderr` — **excludes 100% of errors.** My first pass
   reported `is_error: false` on all 1,800 results and zero failures. All 602 error
   results in the store live in the string form.
2. **`is_error` is absent on success, `false` on some results, `true` only on
   failure.** Defaulting absent → `false` conflates "no error" with "not recorded."
3. **The tool_result block is not always `content[0]`.** Indexing it directly drops
   records.

### 0.4 What the transcript structurally cannot tell you

`[verified]` A Bash `toolUseResult` object carries exactly
`{interrupted, isImage, noOutputExpected, stderr, stdout}` — plus occasionally
`returnCodeInterpretation`. **There is no exit-code field.** Exit status is
recoverable *only for failures*, by parsing the literal string `Error: Exit code N`
out of the error text. A command that exits non-zero is visible; a command that
**exits 0 and is wrong is invisible**.

That limit lands precisely on the two cases this audit cares most about:

- `wxcli cucm execute` exits 0 regardless of outcome (established, Phase 6). Its
  four appearances here therefore prove nothing about whether they succeeded.
- The `--calling-data` and `--all` classes are *defined* by exiting 0 with a
  confidently wrong answer.

**So the transcripts can rank what breaks loudly. They cannot measure what breaks
quietly.** Every silent-failure question below is answered `UNKNOWN` for this reason,
and that is the strongest argument in this document for instrumenting something.

### 0.5 Corrections to the brief and to KNOWN CONTEXT

| # | Claim | Measured |
|---|---|---|
| C1 | "132 transcripts, 337 MB, 157 `wxcli` invocations" | **569 transcripts, 347 MB, 2,062 invoking calls / 2,515 segments** (§0.1–0.2) |
| C2 | Substrate spans 2026-07-06 → 2026-08-05 | **2026-06-30** → 2026-08-05 (subagents start earlier) |
| C3 | `wxcli-gate.sh:41-44`: "four unconfirmed DELETEs **reached the live org**" | **Three reached the network. The fourth was stopped by a local guard** (§5) |
| C4 | KNOWN CONTEXT: dev-only modules gitignored at `.gitignore:145` | `src/wxcli/commands/fs_*.py` is at **`.gitignore:171`**; 11 on disk, **0 tracked** |

### 0.6 Are these findings current, or are they archaeology?

The operator raised this directly: most of the data may predate the flag and help-text
work of the last two weeks. **Tested, because it decides how much of this document the
final report may rely on. The answer is split, and the split is informative.**

`[verified]` Cut at **2026-07-22** (the "last two weeks" boundary), over 1,933
executed calls:

| | Before 07-22 | On/after 07-22 |
|---|---:|---:|
| Executed calls | 849 | **1,084 (56%)** |
| Non-`--help` work calls | 432 | 664 |
| Failures (work calls) | 38 — **8.8%** | 37 — **5.6%** |
| Parse errors (exit 2) | 10 | **4** |
| `no such option` | 5 | **2** |
| `no such command` | 16 | **9** |
| `--fields` used | **0** | **104** |
| `--all` used | **0** | **95** |
| `--calling-data` used | 22 | 42 |
| `--help` share of all calls | 49.1% | **38.7%** |
| **`--force` used** | **26** | **26** |

**Where the operator is right, and it is measurable.** The flag surface demonstrably
improved. `--fields` and `--all` go from **zero to 104 and 95** — they are being used
now and were not before. Parse failures more than halved (10 → 4), `no such command`
fell 16 → 9, and the failure rate on work calls dropped from 8.8% to 5.6%. §1.2's
parse-error classes are therefore **decaying, not current**, and the final report
should treat them as fixed-and-verified rather than open.

**Cut sensitivity — because the fixes did not all land on one date.** The operator
notes some improvements are ~3 weeks old, which would place them *inside* the "before"
bucket and understate the gain. Re-run across six cut dates, the improvement direction
**holds at every one**, and gets larger the earlier the cut:

| Cut | Failure rate before → after | `exit 2` before → after | `--fields` / `--all` before |
|---|---|---|---:|
| 2026-07-08 | **15.1% → 5.6%** | 3 → 11 | 0 / 0 |
| 2026-07-13 | 12.4% → 5.8% | 3 → 11 | 0 / 0 |
| 2026-07-15 | 9.9% → 5.4% | 7 → 7 | 0 / 0 |
| 2026-07-17 | 9.1% → 5.4% | 10 → 4 | 0 / 0 |
| 2026-07-22 | 8.8% → 5.6% | 10 → 4 | 0 / 0 |
| 2026-07-27 | 7.0% → 6.7% | 11 → 3 | 42 / 0 |

The improvement claim is **robust to where the boundary is drawn**, which is a
stronger result than the single cut above gives it.

**Where the premise does not hold.** One thing, and one self-correction:

1. **The dataset is not mostly old. 56% of executed calls fall on or after
   2026-07-22** — the volume skews *recent*, not historic. Whatever else is true, this
   is not a portrait of a CLI that no longer exists.
2. **Correction to this section's own first draft.** I initially reported `--force`
   as *"unchanged — 26 before, 26 after"* and called §3.1 current on that basis. That
   compared raw counts across **unequal denominators** (432 vs 664 work calls).
   Normalised per 100 non-`--help` work calls, `--force` runs **6.0 before → 3.9
   after** at the 07-22 cut — a *decline* — but **5.3 after vs 1.4 before** at the
   07-08 cut, i.e. the sign flips with the boundary. The weekly series is dominated by
   two spikes (2026-W29 at 10.1 per 100; 2026-W32 at 100 per 100 on a base of **7**
   work calls, which is noise, not signal).

   **The defensible statement is narrower than either version: `--force` appears in
   every period including the most recent, so it is not a fixed-and-gone behaviour —
   but no trend in its rate is claimable from this data.** §3.1's *mechanism* finding
   stands on its own evidence and does not depend on a trend: `--force` was added
   after a failure **0 times** and appeared on a first invocation **21 times**, and
   that ratio is what makes it prophylactic rather than reactive.

**The confound, stated.** The post-07-22 window contains the audit sessions
themselves, which are read-heavy and `--help`-heavy: week 2026-W32 has 74 executed
calls but only **7** non-`--help` work calls. So the two periods differ in *what the
agent was doing*, not only in *what the CLI offered*. The improvement is directionally
supported by four independent measures moving the same way, but it is **not cleanly
isolated**, and I am not claiming a controlled before/after.

**How to read the rest of this document, therefore:**

| Section | Status |
|---|---|
| §1.2 parse-error classes, §2's `--output`/`--json` retry examples | **Largely historical** — the gap they exercise is closed |
| §1.4 `licenses-api update` crash | **Historical** — module retired in `47eb791` |
| §1.4 `whoami` tracebacks | **Historical** — fixed in `94744c6`, 2026-07-29 |
| **§1.3a empty positional → malformed URL** | **Current** — no guard exists |
| §5 near-miss | **Historical** — fixed in `5b16343`, door closed by the hook |
| **§3.1 `--force`** | **Mechanism current**; no rate trend claimable (§0.6) |
| **§1.1 the 43% `--help` share** | **Current** — still 38.7% in the recent window |
| **§1.3 opaque failures / §1.5 envelope mismatch** | **Current** — neither has been addressed |
| §3.3 paging note, §0.4 silent failure | **Unanswerable on this substrate, at any date** |

---

## 1. What actually breaks — ranked

### 1.1 The dominant shape is not failure. It is discovery.

**`[verified]` 837 of 1,933 executed `wxcli` invocations — 43% — carry `--help`,
across 130 distinct command groups.** Non-`--help` work calls: 1,096.

Nothing in this dataset comes close to that magnitude. The agent spends roughly two
invocations discovering the surface for every three doing work. This is the
behavioural signature of the repo's own rules — `CLAUDE.md`'s source-of-truth ladder
puts `wxcli <command> --help` at rank 1 and instructs skills to verify against it —
so the number is **the intended design working**, not a defect. It is reported here
because it is the shape any Phase 1 summarizer will see first, and because it prices
the alternative: a machine-readable command index would convert ~837 subprocess
launches into lookups.

I did **not** measure the token or wall-clock cost of that, and will not estimate it.

### 1.2 Failure taxonomy — 81 executed failures

Denominator: **1,933 executed calls**; failure defined as `is_error == true` after
excluding gate blocks and user rejections.

| Class | n |
|---|---:|
| Remote error, raw JSON body, no tip | 31 |
| Traceback (see §1.4 — only 4 are `wxcli`'s own) | 11 |
| Unclassified | 10 |
| Remote 400 validation | 9 |
| CLI parse: no such command | 6 |
| CLI parse: other (exit 2) | 4 |
| Timeout (exit 143, 2-minute Bash limit) | 3 |
| CLI parse: no such option | 2 |
| Remote 401/403 auth | 2 |
| CLI parse: missing argument | 2 |
| Remote 409 conflict | 1 |

Exit codes among failures: **1** × 63, **2** × 14, **143** × 3, **5** × 1. This
matches `00-facts.md` Q13 exactly — remote rejection and network failure are both
exit 1, and only Click's parse errors get 2. **The operator cannot distinguish
"I typed it wrong" from "the server said no" by exit code**, and 63 of 81 failures
land in the undifferentiated bucket.

Most-failing commands (fails / total non-`--help` invocations):

| n | Command |
|---|---|
| 5 / 9 | `pstn list-connection` |
| 5 / 81 | `whoami` |
| 4 / 27 | `users list` |
| 3 / 80 | `locations list` |
| 3 / 7 | `location-settings create` |
| 3 / 23 | `hunt-group list` |
| 3 / 8 | `location-schedules create` |
| 3 / 59 | `people list` |
| 2 / 2 | `dect-devices create` |
| 2 / 2 | `converged-recordings delete` |

`people frobnicate` (2/4) is a deliberate probe of a non-existent command, not a
defect.

### 1.3 "This failed" vs "this failed and the agent could not tell why"

This is the finding, per the brief's closing instruction.

`[verified]` Of the 81 failures, classified by whether the output names a concrete
thing to change (a flag, an argument, a documented tip, a `Try '... --help'` line):

- **41 name a next action.**
- **40 do not.** Of those, **17 are raw remote JSON carrying a `trackingId` and
  nothing else actionable.**

**Just under half of all failures leave the operator with no stated next move.** The
raw-JSON class is the mechanism `06-machinery.md` §6.2 predicted and `07-testability.md`
§3.6 called a published contract: the remote body is passed through verbatim. Four
representative cases, redacted:

- `numbers delete` → `"errorCode":"ERR.V.TRM.TMN60004","errorMessage":"DELETE
  number(s) is supported only for non-integrated CCP and LGW locations."` — states a
  precondition, names no way to check it.
- `converged-recordings delete` → `"the access token is missing required scopes or
  the user is missing required roles"` — names neither the scope nor the role.
- `numbers delete` (above) and `call-queue delete-dnis-queues` / `dect-devices
  create` — the last two are **not** what they first appear; see §1.3a.

#### 1.3a An empty positional becomes a malformed URL, and the CLI sends it

**Correction to this document's own first draft.** I initially read these two —

```
Error: {"message":"No static resource hydra/v1/telephony/config/locations/queues/dnis."}
Error: {"message":"No static resource hydra/v1/telephony/config/locations/dectNetworks."}
```

— as spec↔service drift: a command generated from a spec, pointed at a path the
service does not serve. **That was wrong, and the evidence against it was in the
command string I had already extracted.** `[verified]` The two invocations were:

```
wxcli call-queue delete-dnis-queues "$LOC" "$QUEUE" --json-body '{"items":[]}' --force
wxcli dect-devices create "$LOC" --json-body '{"name":"TestDECT"}' -o json
```

`$LOC` and `$QUEUE` were **unset shell variables**. The code template is
`.../config/locations/{location_id}/dectNetworks` (`commands/dect_devices.py:36`);
with an empty `location_id` it renders `.../locations//dectNetworks`, which the
server normalises to the path in the error. **The segment is missing because the
argument was empty.** Nothing upstream is drifting.

The real finding is better than the one I withdrew, and it is current:

**A required positional accepts the empty string, and the resulting malformed URL is
sent to the live API.** `[verified]` Typer/Click treat `""` as satisfying a required
`str` argument, and there is no non-empty guard — not in the generated module, not in
`common.py`, not in `auth.py`. The operator gets back a *resource* error for what is
actually an *argument* error, which is precisely the §1.3 class: **it failed, and the
agent could not tell why.** One of the two then retried by editing the JSON body —
the wrong variable entirely — before giving up.

This is the measured cost of the repo's own `CLAUDE.md` rule *"Always inline resource
IDs directly as arguments. Never use multi-line shell variable assignments"*: the rule
exists, it was not followed here, and the CLI's failure mode when it is not followed
is a misleading remote error rather than a local one.

**The cheap fix is at the generator**, so it lands across the whole surface at once:
reject an empty or whitespace-only value for any positional that is interpolated into
a URL path, with a message naming the argument. This is Target A, upstream of 1,887
commands, and it needs no spec change.

### 1.4 Four genuine `wxcli` crashes

`[verified]` 11 failures contain a traceback. **Only 4 originate inside
`src/wxcli/`** — the rest are the agent's own downstream Python (§1.5). The four:

- **3 × `wxcli whoami`**, Rich-boxed tracebacks at `src/wxcli/main.py:34` (2026-07-02),
  `:48` (07-27) and `:52` (07-29). **All three are the same defect**, not three: the
  same call site (`rest_get("…/people/me")` → `auth.py rest_get`) at three points in
  the file's growth. `whoami` was bare — no `try/except` — so an auth failure surfaced
  as a Python traceback on the one command that exists to diagnose auth failure.
  **Already fixed, and independently of this audit:** commit `94744c6` (2026-07-29,
  *"fix(errors): whoami tracebacked on exactly the failure it exists to diagnose"*)
  added `except WebexError → handle_rest_error` and `except Exception →
  handle_network_error` (`main.py:57-62`). The last traceback and the fix are the same
  day. Two later `whoami` failures (07-29 13:51, 07-30) show the repaired path
  working: a clean message plus *"Re-run: `wxcli configure`"*. **Closed — do not carry
  forward as open.**
- **1 × `wxcli licenses-api update`** at `src/wxcli/commands/licenses_api.py:101`.
  This corroborates the standing note that `licenses-api update` was broken.
  **Now historical**: the module is gone — retired in `47eb791`
  ("licenses consolidation — retire the last hand-written legacy module (S3.1)"),
  and `src/wxcli/commands/` today contains only `licenses.py`.

`whoami` is the command every skill runs first to verify auth. It is also the
5-in-81 top failure by count. I did not establish the cause of the three crashes and
do not assert one.

### 1.5 The agent mis-predicts the output envelope

`[verified]` 68 of 2,062 `wxcli` calls pipe into `python` or `jq`; 8 of those failed.
**Four failed the same way:** `AttributeError: 'list' object has no attribute 'get'`
— the agent wrote `data.get('items', ...)`, expecting `{"items": [...]}`, and
received a bare JSON array.

Small n, but it is the *only* failure mode in this dataset that repeats verbatim
across different commands (`licenses list`, `numbers list`, `people list`,
`users list`) and different sessions. It is `07-testability.md` §3.6 — raw remote
response shapes are the CLI's published contract — costing the operator something
measurable. The envelope varies by endpoint and nothing at the CLI surface declares
which shape a given command returns.

---

## 2. The retry loop — KNOWN CONTEXT's assertion, tested

KNOWN CONTEXT asserts the operator *"retries automatically, often with altered
arguments because it reads failure as its own mistake."*

**Confirmed, with a qualification that matters.** `[verified]` Of 81 failures,
looking ahead at most 5 `wxcli` calls within the same transcript:

| Outcome | n |
|---|---:|
| Retried the same `group leaf` | **43** |
| — with **altered** arguments | **33** |
| — with **identical** arguments | 10 |
| Retried the same group, different leaf | 11 |
| Abandoned the group entirely | 27 |

So the assertion holds: **when it retries, it alters — 33 of 43.** Two qualifications
the assertion does not carry:

**(a) A third of failures are abandoned, not retried** (27 of 81). The operator is
not uniformly persistent.

**(b) The dominant alteration is the agent *withdrawing something it invented*, not
correcting a value.** Breaking down the 33:

| Change | n |
|---|---:|
| Flags swapped | 15 |
| Same flags, different values / positionals | 10 |
| Flags **removed**: `--output` | 2 |
| Flags removed: `--json`, `--force`, `--fields`, and a 4-flag removal | 4 |
| Flags added: `--debug`; `--comment,--reason` | 2 |

And **27 of 81 failures are followed within 3 calls by `--help` on the same group** —
the agent's most common recovery is not a smarter guess, it is going back to read the
interface. Worked examples, verbatim from the transcripts:

```
wxcli locations list --limit 1 --json     → exit 2 → wxcli locations list --limit 1
wxcli users list --location-id <ID> -o json → exit 1 → …--debug → exit 1 → wxcli users list --help
wxcli hunt-group list <LOC> --output json → exit 2 → wxcli hunt-group list --help
wxcli call-queue create --generate-json-body → exit 2 → wxcli call-queue create --help
```

The third is the `--output`-not-on-every-command gap, caught in the act. The fourth
is the documented `--generate-json-body` caveat (it does not bypass required
positionals) — the agent hit it and fell back to `--help`.

**One caution on my own detector.** "Altered arguments" over-counts: iterating a list
of locations (`pstn list-connection <LOC-A>` → `<LOC-B>`) is indistinguishable from a
corrective retry by argument diff alone, and `pstn list-connection` is the top
failing command precisely because it was being swept across locations. I did not
separate these, so **33 is an upper bound.**

---

## 3. Three playbook claims, tested against the data

### 3.1 `--force` — the answer is stronger than Phase 5 expected, and inverted

Phase 5 asks whether `--force` reads as the normal unattended mode. `[verified]`:

- **52 invocations carry `--force`**, across 26 transcripts, split evenly
  main/subagent (26/26).
- **`--force` was added after a same-command failure that lacked it: 0 times.**
- **`--force` was present on the *first* invocation of that command: 21 times.**

**`--force` is not a fallback the agent reaches for after a confirm blocks it. It is
the form the agent writes first.** That is a more direct answer than inference could
give, and it is worse for the guard than the reactive story: a confirm prompt cannot
deter an operator that never encounters it. Nine of the 52 `--force` calls failed
anyway — on remote grounds, not on the guard.

It also shows up where it does not belong: `wxcli dect-devices create <LOC>
--json-body '{…}' --force` → **exit 2**, followed by the same command with `--force`
removed. The agent applied `--force` to a *create*. It is treating the flag as
generic unattended-mode boilerplate, exactly as Phase 5 feared.

Note the confound and weigh it accordingly: the `PreToolUse` gate rejects
state-changing commands outside the builder agent, so `--force` habits are partly
trained by *this repo's* harness.

### 3.2 `--calling-data` — the trap is real but rarely sprung here

`[verified]` Over `people|users list|show|create|update|show-me`: **164 invocations,
61 with `--calling-data`, 103 without.** Of the 103, **5 reference `extension` or
`locationId`** in the command itself — the exact silent-wrong-answer shape. 32
results mention `--calling-data` in their output (interlock message or help text).

I **cannot** report a clean before/after for the interlock. Determining whether each
of the 103 *needed* the flag requires knowing what question the call was meant to
answer, which is not in the command string. Marked `UNKNOWN`; the 5 are a floor, not
a count.

### 3.3 The paging note — the falsifiable test the brief wanted cannot run. **n = 2.**

The brief asks for a direct test of a load-bearing `CLAUDE.md` claim: that the
`Note: N records returned and the server has more pages` is *visible* to the model,
so the failure mode is ignoring it rather than missing it.

`[verified]` **Across 1,933 executed calls, the note appears in exactly 2 results.**
Once the agent re-ran with `--all`; once it did not.

**One-for-one is not evidence.** The claim is neither supported nor refuted —
`UNKNOWN`, and it will stay `UNKNOWN` on this substrate. The reason is the org, not
the CLI: this is a sandbox with ~16 people and 2 locations, so almost nothing
paginates. For context, 77 of 590 `list` invocations carry `--all`.

This is the clearest case in the document where **mining cannot substitute for
instrumenting.** A one-line counter in the paging path would answer it in a week on
any real org; 569 transcripts cannot.

---

## 4. The gate, measured

`[verified]` **126 invocations were blocked before execution**, across 71
transcripts — 28 from the main session, 98 from subagents:

| Reason | n |
|---|---:|
| Must route through the builder agent | 88 |
| Read-only verb policy (state-changing call outside an agent) | 35 |
| Python-import side door | 3 |

Most-blocked: `whoami` (8), `call-queue list-supervisors` (7), `call-queue list` (5),
`numbers delete` (4), `call-queue create` (4).

Two observations. First, **the gate fires far more often on subagents than on the
main session** (98 vs 28) — it is a working control, not a formality. Second, the
most-blocked single command is `whoami`, which is read-only and harmless; those are
blocked by the *routing* rule, not the verb rule. The gate's cost is concentrated on
calls that were never dangerous.

---

## 5. The 2026-07-28 near-miss, read deliberately

The brief calls this the only recorded near-miss in the repository and the best
available evidence about how an agent gets there. It is in the transcripts. The
account below is `[verified]` from
`f9ee0df6…/subagents/agent-afix-blocker-7-9c05c1e3f3b7934a.jsonl:45-69` and
`f9ee0df6-ff87-4fe4-898b-bca061c5d39e.jsonl:1971-1980`, all on 2026-07-28.

### What happened

A subagent was investigating a real defect: `typer.confirm(f"Delete {orgid}?")` was
emitted **before** the line that assigns `orgid`. Python treats a name assigned
anywhere in a function as local throughout, so the *safe* invocation — no `--force` —
raised `UnboundLocalError` instead of prompting.

It measured the blast radius statically first, and correctly:
`Total dynamic-confirm delete commands scanned: 176. CRASH candidates: 4.` The four
were `cc_dial_number.delete`, `fs_projects.delete`, `fs_user_prefs.delete`,
`organizations.delete`.

It then called those four functions directly from Python to confirm the crash,
building kwargs with `isinstance(p.default, bool)` to pass `force=False`. A Typer
default is an `OptionInfo`, not a `bool`; the guard missed it; `OptionInfo` is
truthy; `if not force:` evaluated false; the confirm was skipped. It verified the
root cause immediately afterwards:
`<class 'typer.models.OptionInfo'> True False`.

### Outcome, corrected

| Command | Result |
|---|---|
| `organizations delete` | **HTTP 409** — *"cannot be deleted as it has active subscriptions"* |
| `cc-dial-number delete` (deletes **all** CC dial-number mappings) | **HTTP 403** |
| `fs-user-prefs delete` | **HTTP 401** (token lacked rights) |
| `fs-projects delete` | **Never reached the network** — stopped locally by *"Flow Store project ID not configured"* |

No call returned 2xx. State was verified intact afterwards by an independent
read-only agent (org, 2 locations, ~16 people, 17 license SKUs).

**This corrects the repository's own record.** `wxcli-gate.sh:41-44` says *"four
unconfirmed DELETEs reached the live org … Only Cisco refusing them saved it."*
Measured: **three reached the network, not four** — and the fourth was stopped by a
**local** guard, which is the one piece of good news in the incident and the one
detail the record erases. Two of the four (`fs_*`) are dev-only modules, untracked
(`.gitignore:171`) and absent from the published wheel, so **only two of the four are
reachable by a user of the shipped product**.

### What it is actually evidence of

Four things, and the ordering matters:

1. **The confirm gate — the repository's only destructive-write guard at the time —
   was non-functional on 4 of 176 commands, including `organizations delete`, the
   single most destructive command in the CLI.** It did not prompt weakly; it raised
   `UnboundLocalError`. Fixed in `5b16343`
   (*"fix(safety): the delete confirmation could not run, and named the wrong
   object"*); `commands/organizations.py` now resolves `org_id` **before** the
   confirm. Verified in the current tree.
2. **The architecture offered no safe way to test it.** There is no layer below the
   CLI (`07-testability.md` §3.1), so "does this function crash before prompting?"
   could not be answered by executing anything that did not also perform the HTTP
   call. The agent's instinct — verify rather than assume — was right, and the code
   left it no safe move. That is a testability finding, not an operator failure.
3. **The agent self-reported within 76 seconds**, unprompted, before being asked and
   before finishing its task. The escalation path worked.
4. **What bounded the damage was the remote API and one local config guard — no
   control in this repository.** `00-context.md` already says this; the incident is
   its proof.

### The finding the brief did not anticipate

**This invocation is invisible to the substrate the brief told me to mine.** It never
produced a `wxcli` command string — it was a Python import. My §0.2 extraction misses
it by construction, and so would any logger attached to argv.

Measured: **412 Bash calls across 108 transcripts import the CLI package from
Python** — 82 of them on 2026-07-28 alone. That is a whole invocation class, ~20% the
size of the `wxcli`-command class, with **full capability and no argv**.

The gate now blocks this door (`wxcli-gate.sh:56-58` matches the import and calls
`deny_import`, `:30-33`), and
the hook's own comment states the limit honestly: a hook sees only the command
string, so a `.py` file on disk that imports the CLI is invisible to it.
**Any Phase 1 instrumentation attached at the Bash/argv layer inherits exactly that
blind spot — including for the one event in this repository's history that most
needed recording.**

---

## 6. `07-testability.md` §6 predictions vs. what showed up

Ten things were predicted to break with a green suite. Checked against 1,933 executed
invocations:

| # | Prediction | Observed |
|---|---|---|
| 7 | Retry loop / `rest_*` — zero coverage | **Not observed.** No retry-exhaustion or 429 failure in the dataset. |
| 8 | `follow_pagination` — silent short read | **Not testable here** (§3.3, n=2) |
| 10 | `config.py` at 24% — resolves which org `orgId` points at | **Indirectly implicated**: `organizations.delete` calls `resolve_org_id`, and it was the ordering of that call vs. the confirm that produced the near-miss (§5) |
| 1–6 | Target B execute-path branches, 409 recovery, bulk jobs, preflight probe, AXL extractors | **Not observed. `cucm execute` appears 4 times: 3 are `--help`, 1 is a bare invocation.** And since it exits 0 on any outcome (Phase 6), even that one proves nothing. |
| 9 | The generator — untracked tests | Not observable from invocations |
| — | *Cross-cutting: spec→CLI→docs drift with the gate green* | **Not observed.** I initially scored this "observed" on the two `No static resource` failures; §1.3a retracts that — they are empty-positional argument errors, not spec drift. **No spec↔service drift appears in this dataset.** |

**The audit's highest-severity predictions are all on the migration write path, and
that path is essentially absent from a month of real operation.** That is not
evidence the predictions are wrong — it is evidence that the most dangerous code in
the repository is also the least exercised, which makes every one of those findings
*less* likely to be caught by use and *more* dependent on the guards the audit is
recommending. Consequence, not frequency, remains the right severity model for
Target B.

---

## 7. Where a durable record should attach

Two substrates exist and neither is used. Judged, not re-derived.

### 7.1 The hook — cheapest, and it buys less than it looks like

`[verified]` `.claude/hooks/wxcli-gate.sh:35-37` receives the full command string on
stdin and contains no log, `tee`, redirect or JSONL write.

**Four limits, and together they are disqualifying as the primary record:**

1. **It does not ship — and what ships in its place is weaker than nothing.**
   `wxcli-dist/assemble.py:161` copies `settings.bundled.json` over
   `.claude/settings.json`. `[verified]` The dev settings' only hook event is
   `PreToolUse`; the bundled file's only hook is a `SessionStart` update check, and
   **`.claude/hooks/` is absent from the shipped payload entirely** —
   `src/wxcli/_playbook/.claude/` contains `agents`, `rules`, `settings.json`,
   `skills` and no `hooks` directory. So instrumenting it captures **this machine
   only**: the same single operator whose data this document already mines.

   **Worth flagging beyond Phase 1's remit**, because it is a safety observation and
   no phase owns it: the bundled file also declares
   `"permissions": {"allow": ["Bash(wxcli:*)", "Bash(which:*)"]}`. A downstream
   install therefore gets **every `wxcli` command pre-approved without a prompt, and
   no `PreToolUse` gate** — the inverse of this machine, where 126 invocations were
   blocked (§4). What stands between a downstream agent and a destructive call is
   then the generated `typer.confirm` alone — the guard §3.1 shows the operator
   routinely pre-empts with `--force`. **Whether `typer.confirm(abort=True)` even
   prompts, aborts, or hangs under a non-interactive Bash tool is `UNKNOWN`; I did not
   test it, because testing it means running a destructive command.** It is the single
   highest-value one-line experiment left in this audit and it needs a throwaway org,
   not this one.
2. **It is `PreToolUse`. It sees the request, never the result.** No exit code, no
   error text, no duration. It cannot answer "what actually breaks" — only "what was
   attempted."
3. **It is blind to the class that caused the only near-miss** (§5, 412 Python-import
   calls).
4. **It is blind to silent failure** by construction, and §0.4 establishes that is
   the class that matters most.

**Verdict: not the place — for *logging*.** Adding a logger there would re-measure the
one operator this document already measured. **Do not build that.**

**But the gate itself should ship, and that is a separate question this phase got
wrong on first pass.** The argument against — "it encodes one operator's workflow" —
does not survive the data:

- **The two malformed-URL calls in §1.3a both came from the main session, not from
  the builder agent** (`[main]`, 2026-07-14). The un-agented path produced exactly the
  failure the agent's own rules exist to prevent (*"always inline resource IDs; never
  use shell variables"*). That is a worked example of the gate's value, not of its
  parochialism.
- **28 of the 126 blocks are the main session trying to run `wxcli` directly** (§4).
  The behaviour the gate suppresses is the model's default, not this repo's quirk.
- The routing target already ships: `src/wxcli/_playbook/.claude/agents/` contains
  `wxc-calling-builder.md`, so a downstream install has something to route *to*.
- The script is portable: 138 lines, **no hardcoded machine paths** (the sole
  `/opt/homebrew` occurrence is inside a comment), and it communicates allow/deny by
  JSON payload rather than exit status.

**Two things must change for it to ship coherently, and both are in the bundle, not
the script:**

1. **The blanket permission allow becomes redundant, not required.** `[verified]` The
   hook grants permission itself: `allow()` emits
   `{"permissionDecision":"allow"}` (`:20-23`), and the builder agents are exempted
   wholesale — `wxc-calling-builder|migration-advisor) allow` (`:64-67`). A
   `PreToolUse` "allow" satisfies the permission layer, so the agent is **not**
   prompted and **not** blocked when `Bash(wxcli:*)` is absent. The two mechanisms are
   separate: `permissions.allow` suppresses the human prompt; the hook decides
   allow/deny. **Today's shipped combination — blanket allow, no hook — is the worst
   of the four:** no prompt *and* no gate. Ship both together and the allow can go;
   ship neither and the allow is needed for usability but nothing is guarding.
2. **The script needs `jq`** (`:26`, `:31`, `:36`) — **less of a risk than I first
   stated, and worth correcting.** `[verified]` `jq` is at `/usr/bin/jq`, root-owned
   and Apple-supplied, on this macOS; it is not a Homebrew dependency here. So the
   common case is covered. It is still not universal (older macOS, Linux, Windows),
   and a hook whose dependency is missing **fails open** — silently allowing
   everything while the operator believes a gate is running. Worth a `SessionStart`
   presence check that fails loudly, not worth blocking the ship.

`UNKNOWN`, and it gates the decision: whether `typer.confirm(abort=True)` prompts,
aborts, or hangs under a non-interactive agent. If it aborts cleanly, downstream has
one real guard today; if not, the gate is the only one available.

### 7.2 `journal` — the right place, and it must be designed once

`[verified]` `migration/store.py:120-130` declares
`journal(timestamp, entry_type, canonical_id, resource_type, request, response,
pre_state)`. Two writers, both read-only discovery (`commands/cucm.py:1220`,
`migration/cucm/discovery.py:251`); nothing in `execute/` writes it; `pre_state` is
supplied by no caller anywhere.

**This phase and Phase 5 arrived at this table independently, from opposite
directions — Phase 5 §1.8 wants it as a post-hoc audit trail ("what did we send /
what was there before"), this phase wants it as telemetry ("what did the operator do
/ what happened"). Those are one record, and the fact that two phases converged on it
without coordinating is the argument that one design serves both.** Two schemas would
be the worst outcome available.

**The single schema is the declared one — no new columns are required.** Both uses
are served by populating it on the execute path:

| Column | Audit use (Phase 5) | Telemetry use (Phase 1) |
|---|---|---|
| `timestamp`, `entry_type` | when / what kind | sequencing, retry-window detection |
| `canonical_id`, `resource_type` | which object | grouping by operation type |
| `request` | **what did we send** | the argv-equivalent, at the layer that matters |
| `response` | what came back | error text, status, failure taxonomy |
| `pre_state` | **what was there before** | — |

Two costs, stated plainly:

**(a) `pre_state` requires a read-back that does not exist.** Phase 5 §1.7 established
that `completed` means "2xx", not "applied", and that there is **no read-back
anywhere** on the write path. So `pre_state` is not free bookkeeping — it is one
additional GET before each mutating call. That roughly doubles request count on the
execute path, which runs at concurrency 20 (`commands/cucm.py:3151`) against an API
whose 429 handling Phase 6 D1–D5 found to be the weaker of the two stacks.
**Recommendation: populate `request`/`response` unconditionally, and `pre_state` only
for PUT/PATCH — the verbs where "what was there before" is unrecoverable.** A DELETE's
prior state is recoverable from `objects`; a POST has none. This is also the smaller
change: `add_journal_entry` already accepts the parameter (`store.py:756`).

**(b) `clear_all` deletes `journal`** (Phase 5 §1.5), so entries are not durable
across a re-normalize. Phase 5 already fixed the adjacent hole — `normalize` now
refuses to erase the execution record — but the same reasoning has to be extended to
`journal` or the audit trail evaporates exactly when someone re-runs the pipeline to
recover from the failure they need it to explain.

**What it fixes beyond Phase 1.** Phase 6 D13 established that a half-applied
migration is indistinguishable from a not-yet-started one, and Phase 6 §4 that
`plan_operations` has no `run_id` column, so two `execute` runs are
indistinguishable in the store. A `journal` written per operation with a run
identifier in `entry_type` resolves both — and `plan_operations` needs no schema
change to get it.

**One structural obstacle, unchanged from Phase 5 §1.8:** `journal.canonical_id` is
an FK into `objects` with `PRAGMA foreign_keys = ON` (`store.py:129`). Bulk-job ops
carry synthetic canonical_ids; `save_plan_to_store` already handles this with an
`INSERT OR IGNORE` placeholder (`batch.py:185-192`), so the pattern exists and does
not need inventing.

### 7.3 What no attachment point can fix, and the one thing worth adding

§0.4's limit is not a property of the transcripts — it is a property of the CLI. A
command that exits 0 with a wrong answer is invisible to argv logging, to the hook,
and to `journal` alike, because **nothing anywhere records that the answer was
wrong.**

The `--calling-data` interlock is the repository's one existing counter-example: it
converts a silent wrong answer into a loud one *at the point of the mistake*. The
paging note tries to do the same and §3.3 could not establish whether it works.

**The one measurement worth adding is therefore not a logger. It is a counter on the
paging path** — how often a single fetch left pages behind, and how often `--all`
followed. That is the one load-bearing claim in `CLAUDE.md` this document could not
test, it cannot be answered by mining, and unlike the hook it would ship. **I did not
build it** (the brief forbids instrumenting); the cost is a counter and a summary
line, and unlike `pre_state` it adds no remote requests.

---

## 8. Read coverage, and what I did not do

**Read in full:** the brief; `00-context.md` Q3; `00-facts.md` Q11–14;
`07-testability.md` §6; `05-safety.md` §1.8; the audit spec's STATUS, ROLE, KNOWN
CONTEXT, HARD CONSTRAINTS and PHASE 0/1 bodies; `.claude/hooks/wxcli-gate.sh:30-60`;
`src/wxcli/commands/organizations.py:64-82`.

**Machine-processed, never read as prose:** all 569 transcripts (347 MB), via `jq`
field extraction into a 2,062-row dataset. **No transcript was `Read`, `cat`ed or
`tail`ed.** The only transcript content I read directly is the §5 incident window
(~35 records across two files), extracted by targeted line range, as the brief
directs.

**Redaction:** Spark IDs, org/tracking UUIDs, emails, phone numbers and long tokens
are pattern-redacted in every quotation above. Error text was the expected exposure
site (Phase 6 §6.5) and it was — the incident's raw 409 body carries a live org UUID
and a tracking ID.

**Not done, deliberately:**

- **No code was changed**, per the brief. §7.3's counter is proposed, not built.
- **No `wxcli` command was run**, of any kind.
- I did not reverse-engineer the spec's 157 figure.
- I did not separate corrective retries from resource sweeps (§2), so 33 is an upper
  bound.
- I did not measure the token or wall-clock cost of the 43% `--help` share.

**Marked `UNKNOWN` and not guessed:** whether the `--calling-data` interlock changed
behaviour (§3.2); whether the paging note is read or ignored (§3.3); whether the four
`cucm execute` invocations succeeded (§0.4); the cause of the three `whoami` crashes
(§1.4).

**The load-bearing caveat, restated:** every count here describes one operator on one
machine against one sandbox org of ~16 people and 2 locations. The counts rank shapes
against each other. They are not rates, and §3.3 is the worked example of what
happens when you ask this substrate for one.
