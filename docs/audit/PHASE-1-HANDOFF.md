# Handoff prompt — PHASE 1 (revised: mine, do not instrument)

Paste everything below the line into a new Claude Code chat.

**Read this first, before the prompt below.** PHASE 1 in the audit spec asks you to
*add logging* and observe for a week. **That is not this session's task.** The spec's
own STATUS block deferred it on evidence: with one operator and no downstream
telemetry, a week of new logging yields almost nothing, and the document already says
not to draw volume conclusions from it. **Two substrates already hold the data it
asks for, and this session mines them.**

The spec's closing line is the reason this is worth running at all:
*"The audit finds what is theoretically wrong; the transcripts will tell you what
actually breaks. Do not wait for them."* Seven phases have established what is
theoretically wrong. This is the only session that produces evidence about what
actually fails in practice.

---

Continue an architectural audit of the wxops repository at
/Users/ahobgood/Documents/webexCalling. Run PHASE 1 (revised) only, then stop.

## Read these first, in this order

1. `docs/arch/wxops-architecture-audit-prompt_2.md` — the audit spec. Read STATUS
   (top — especially the *"Phase 1 is deferred on evidence, not skipped"* paragraph),
   ROLE, KNOWN CONTEXT (especially *"The operator is an LLM driving the CLI
   directly"*), and HARD CONSTRAINTS. **Skip PHASE 1's own body** — it describes the
   instrumentation approach this session replaces.
2. `docs/audit/00-context.md` **Q3** — "Invocation logging, shell history, CI
   record." It enumerates both substrates and is the direct input to this session.
3. `docs/audit/00-facts.md` **Q14** — the logging baseline. Do not re-derive it.

Consult as needed: `docs/audit/06-machinery.md` §2.2 and §6 (what an operator
actually sees on failure), `docs/audit/07-testability.md` §6 (what can break with a
green suite — this session tests those predictions against reality).

## Your task

Write `docs/audit/01-observed.md`.

**Two deliverables, and the first is the point:**

1. **What actually breaks.** A ranked, counted account of real `wxcli` failures
   drawn from the transcripts — the command, the error, and *what the agent did
   next*.
2. **Where a durable record should attach**, given that two substrates already exist
   and neither is used.

## Substrate 1 — the transcripts

`[verified 2026-08-05]` `/Users/ahobgood/.claude/projects/-Users-ahobgood-Documents-webexCalling/`
holds **132 `.jsonl` session transcripts**, **337 MB total**, spanning
**2026-07-06 → 2026-08-05**. The audit spec's STATUS block records **157 `wxcli`
invocations with their command strings and results** as of 2026-08-04; the count will
now be higher. Re-derive it — it is one of the few numbers this session should
measure rather than inherit.

### ⚠ The failure mode that will kill this session

**337 MB of JSONL. Do NOT `Read`, `cat`, or `tail` a transcript.** A single session
file can exceed your entire context. The project's own `CLAUDE.md` says it outright:
*"do not `tail`/Read large JSONL transcripts — use targeted line ranges only."*

Work with `jq`, `grep -o`, and `awk` that emit **only the extracted fields**, never
the surrounding records. Build the dataset first, then reason over the dataset —
never over the raw files. A safe shape:

```sh
P=/Users/ahobgood/.claude/projects/-Users-ahobgood-Documents-webexCalling
# Extract only Bash tool_use command strings that start with wxcli, one per line.
grep -ho '"command":"wxcli[^"]*"' "$P"/*.jsonl | wc -l
```

Then widen carefully to pair each invocation with its `tool_result`. Write the
extracted dataset to the scratchpad as a small CSV/JSONL and analyse *that*.

**Do not read a transcript to "get a feel for it."** Extract, then read your own
extract.

### What to extract, per invocation

- the full command string, and the command **group + leaf** (e.g. `people list`)
- exit status / whether the result was an error
- the error text, truncated
- **whether the next `wxcli` call was a retry of the same intent**, and if so,
  **whether the arguments were altered** — this is the single most valuable field
- whether the invocation came from the main session or a subagent, if determinable

### The questions the extract exists to answer

KNOWN CONTEXT asserts things about the operator that have never been checked against
data. Check them:

- **Does the agent read failure as its own mistake and retry with altered
  arguments?** The spec asserts it does. Confirm or refute, with counts.
- **Does it reach for `--force`?** Phase 5 asks whether `--force` reads as the normal
  unattended mode. The transcripts can answer it empirically rather than by
  inference — count invocations where `--force` appears after a failure that did not
  mention it.
- **Does it hit the `--calling-data` trap?** `people list` without `--calling-data`
  silently returns no `extension`/`locationId` and exits 0. An interlock was added
  (`CLAUDE.md`, *Common Flags*). Count occurrences before and after.
- **Does it ignore the paging note?** A single fetch that left pages behind prints a
  `Note: N records returned and the server has more pages` on stderr. `CLAUDE.md`
  claims the note is visible to the model and the failure mode is *ignoring* it, not
  missing it. **Count how often the note appeared and the agent did not add `--all`.**
  That is a direct, falsifiable test of a load-bearing claim in the playbook.
- **Which commands fail most, and are the failures the ones the audit predicted?**
  `07-testability.md` §6 lists ten things that can break with a green suite. Check
  whether any of them show up.
- **Did any invocation reach a destructive command?** Note the 2026-07-28 incident
  (four unconfirmed DELETEs, one `DELETE /v1/organizations/{id}`) recorded at
  `.claude/hooks/wxcli-gate.sh:41-44`. **If that session is in the transcript range,
  read it deliberately** — it is the only recorded near-miss in the repository and
  the best available evidence about how an agent gets there.

**Do NOT draw volume conclusions.** One operator, one machine, no downstream users.
Frequency here means "how often Adam's agent did X," not "how often users do X."
Report shape and mechanism; treat counts as ordinal, not as a rate. Say this in the
document.

## Substrate 2 — the two attachment points that already exist

Both are `[verified]` in `00-context.md` Q3. Do not re-derive; judge them.

1. **The hook has argv in hand and logs nothing.** `.claude/settings.json` registers
   a `PreToolUse` hook on `Bash` running `.claude/hooks/wxcli-gate.sh`, which
   receives the full command string on stdin (`wxcli-gate.sh:35-37`) and contains
   **zero** log, `tee`, redirect or JSONL write. It decides allow/deny and exits.
   **This is the cheapest possible attachment point in the whole system.**
   *But:* `wxcli-dist/assemble.py:161` substitutes `settings.bundled.json` in the
   shipped bundle, whose only hook is a `SessionStart` update check — so **the hook
   does not ship, and instrumenting it captures this machine only.** Say what that
   does and does not buy.
2. **The `journal` table is an audit-log schema the write path never uses.**
   `migration/store.py:120-130` declares
   `journal(timestamp, entry_type, canonical_id, resource_type, request, response,
   pre_state)` — precisely the shape Phase 1 asks for. It is written at **two** sites,
   **both read-only discovery** (`commands/cucm.py:1220`,
   `migration/cucm/discovery.py:251`), and **`pre_state` is populated by no caller
   anywhere**. Nothing in `execute/` writes it.
   Phase 6 (D13) established that a half-applied migration is indistinguishable from
   a not-yet-started one, and Phase 6 §4 that `plan_operations` has **no `run_id`
   column** — so two `execute` runs are indistinguishable in the store. **`journal` is
   the natural home for the record that would fix both.** Judge whether populating it
   is the right move, and what it costs.

   **Phase 5 adds a constraint that changes how you judge this, and it is the most
   important sentence in this section: `journal` must be designed ONCE, as both the
   audit trail and Phase 1's substrate — not twice.** `05-safety.md` §1.8 reaches the
   same table from the safety side and wants it for post-hoc "what did we send / what
   was there before"; this phase wants it for "what did the operator do and what
   happened." **Those are the same record.** Two independent designs — one an audit
   log, one a telemetry log — would be the worst outcome available, and both phases
   arriving at the same table independently is the argument that one design serves
   both. Say what the single schema is, including whether `pre_state` needs a
   read-back to populate (Phase 5 §1.7 established that `completed` means "2xx", not
   "applied", and that **there is no read-back anywhere**), and what that costs.

The only durable record of remote writes today is `plan_operations`
(`store.py:145-159`): `status`, `webex_id`, `error_message`, `completed_at`,
`attempts`. Per-operation outcome only — no argv, no request body, no response body,
no prior state. It answers *"did op X succeed"* and cannot answer *"what did we
send"* or *"what was there before."*

## Do not build anything

**This session mines and judges. It does not instrument.** HARD CONSTRAINT 1 allows
Phase 1 instrumentation, but the STATUS block deferred exactly that, and the reason
still holds: a week of new logging on one machine yields almost nothing next to 132
existing transcripts. If your analysis shows a specific attachment point is worth
building, **propose it in the document with its cost** — do not add it. Throwaway
extraction scripts in the scratchpad are fine and expected; they are not repo edits.

## Repo-specific constraints

- **The interpreter is `/opt/homebrew/opt/python@3.14/bin/python3.14`.** Bare
  `python3` is the system 3.9.
- **`wxcli` CANNOT be imported from Python.** A hook blocks it, matching the string
  `import wxcli` anywhere in a Bash command — **and this session will be quoting
  transcript content that contains `wxcli` command strings, so expect the hook to
  fire on your own extraction one-liners.** Keep extraction commands free of the
  literal `import wxcli` / `from wxcli` substrings; grep for `"command":"wxcli` and
  similar instead.
- **Never run a mutating `wxcli` command.** This repo points at a live org and
  `~/.wxcli/config.json` holds a working token. This session should run **no** `wxcli`
  command at all — it reads history.
- **The transcripts contain real tokens, org IDs, emails and phone numbers.** Treat
  them as sensitive. Redact anything you quote: no bearer tokens, no full org IDs, no
  end-user emails or DIDs in the written document. Phase 6 §6.5 already established
  that PII reaches error strings, so error text is exactly where it will appear.
- **Count git-tracked files, never the working disk.** Four phases have got this wrong.
- **`docs/audit/` and `docs/arch/` are untracked/gitignored.**
- **The working tree is NOT at `b578a52`** — 28 tracked files are modified and
  uncommitted.
- Write extracts to the session scratchpad, not into the repo.

## Established — do not re-litigate

- **Usage of individual commands is unmeasured, and publication — not observed
  usage — is why nothing is safe to break.** Do not claim a command is unused on the
  strength of its absence from 132 transcripts; that is one operator's sample.
- One logger, two retry warnings, no argv or exit-code capture (`00-facts.md` Q14).
- No CI record of agent runs: `ci.yml` runs pytest and the drift gate, greps
  `gate.log` in-job, and uploads no artifact.
- The migration `execute` path emits no handler-attached logging at all; the two
  events an operator most needs (rate-limited, adopted-a-resource-we-did-not-create)
  are unobservable (Phase 6 D11).
- `wxcli cucm execute` exits 0 regardless of outcome, so exit status in the
  transcripts is **not** a reliable failure signal for migration runs.

## Rules

Every finding cites `path:line` or `transcript:line`. Label claims `[verified]` or
`[inferred]`. `UNKNOWN` is a correct answer. **Do not estimate — count**, and state
the denominator every time. Where a count contradicts an assertion in KNOWN CONTEXT
or in an earlier phase, **say so plainly**; that is the highest-value output this
session can produce, and six such corrections have already been made. Distinguish
throughout between *"this failed"* and *"this failed and the agent could not tell
why"* — the second is the finding.

Stop after writing `docs/audit/01-observed.md`. Do not begin the final report.
