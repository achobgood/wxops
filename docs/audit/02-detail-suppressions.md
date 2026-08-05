# Suppression-Surface Audit — wxcli drift gate

Scope: every allowlist/ack/skip mechanism `tools/drift_check.py` consults, per
the brief. All claims below are `[verified]` against files in this working
tree at commit range up to `HEAD` (branch `main`, `b578a52` per session start)
plus one live `python -m tools.drift_check` run (report-only, exit 0, no
mutation) unless marked `[inferred]`.

## Method

- Read every suppression file/block in full (not sampled).
- For each, ran `git log -S'<text>' --oneline -- <file>` to date the entry
  and read the introducing commit's message.
- Ran `python3.14 -m tools.drift_check` once (report-only mode — the team's
  own tooling confirms this always exits 0 and never mutates anything) to get
  live current-state counts per check, then diffed those counts against the
  prose claims in `tools/CLAUDE.md`.
- Ran two single targeted pytest tests directly (not the suite) to verify two
  specific staleness-check claims rather than trust the docstrings.
- Never imported `wxcli`; never ran a mutating command; did not edit any file
  except this one.

---

## 1. `tools/drift_check_allowlist.txt` (check 2 — dead `wxcli` references)

**31 live entries** (154 lines total, rest is comments/blank). Full enumeration:

| Form | Count | Entries |
|---|---|---|
| bare group | 9 | `commands`, `cucm commands`, `call-controls accessible`, `locations-api`, `users assign-license`, `location-settings update-location-calling`, `trunk`, `route-group` (+ implicit blank-line group) |
| `ref FILE GROUP [CMD]` | 3 | `user-call-settings` (manage-devices), `user-settings list-monitoring` (manage-call-settings), `archive-users show` ×2 (skill + reference doc) |
| `positional FILE GROUP CMD` | 2 | `hunt-group delete` ×2 (configure-features, provision-calling) |
| `required-flag FILE GROUP CMD` | 9 | `security-audit list` ×1, `cc-team/cc-skill/cc-skill-profile/cc-desktop-profile create` ×2 each (skill + reference doc) |
| `prose-flag FILE --flag` | 7 | `--macs`, `--base-station-macs`, `--emails` ×2, `--exclude-devices`, `--calling-only`, `--invitees`, `--files` |

**Every entry carries an in-file comment giving a reason**, and every one I
spot-checked against the cited doc line matches the comment (I read the full
154-line file, not a sample).

**Verdict: overwhelmingly deliberate, not quieted.** This file's own header
(`drift_check_allowlist.txt:6-12`) records the ONE past incident where a bare
entry (`user-call-settings`) hid 6 real dead references in
`person-call-settings-behavior.md`, found live 2026-07-27, fixed in commit
`0cccca8` (2026-07-28, "fix(gate): close two false negatives...") by
introducing the file-scoped `ref` form specifically to prevent recurrence.

**One live, if currently-dormant, gap that repeats that exact shape:**
`trunk` and `route-group` (lines 46-47) are still **bare**, not file-scoped,
even though their own comment (lines 43-45) says they exist for exactly ONE
file's negative example (`query-live/domains/routing.md:120`) — the identical
situation `user-call-settings` was in before the fix. `git log -S'trunk'`
shows they were added in the original sweep commit `bc3a7e7` and were **not**
touched by the `0cccca8` fix that converted `user-call-settings` right above
them in the same file. `[verified]` via `git show 0cccca8 -- tools/drift_check_allowlist.txt`:
the diff touches only the `user-call-settings` entry.

I searched the full `.claude/skills/` and `docs/reference/` trees for any
other citation of `wxcli trunk` / `wxcli route-group` as a real (non-negative)
recommendation and found none — every other hit is the plural, real command
names (`delete-trunks`, `list-trunks`, `delete-route-groups`) or the English
word "trunk"/"route group" in prose. **So today this hides nothing** — but the
allowlist entry is broader than its stated justification in exactly the form
the file's own maintainer comment warns against, and nothing would stop it
from silently absorbing a future stray `wxcli trunk ...` recommendation
elsewhere. `[verified: currently benign; inferred: latent risk, same shape as
a fixed incident]`.

---

## 2. `tools/field_overrides.yaml` — ack/exemption blocks

Enumerated top-level keys in the file (`grep -n "^[A-Za-z_]\+:$"`): `skip_tags`,
`tag_op_excludes`, `verb_semantics_ack`, `spec_authority`, `tag_merge`,
`cli_name_overrides`, `keep_endpoints`, `inert_tag_ack`,
`undeclared_paging_ack`, `tag_overrides`, `naming_ack`. Also
`omit_query_params: []` (empty — nothing suppressed there today).
`tag_merge`/`cli_name_overrides`/`tag_overrides` are naming/routing config,
not suppression, and are out of scope here except where noted.

### 2a. `verb_semantics_ack` (6 entries) — known issue #20

All 6 read in full (`field_overrides.yaml:930-945`). 4 are the `accessCodes`
PUT-that-deletes family (location/person/virtualLine/workspace), 1 is CC
`agent-personal-greeting/delete-reference`, 1 is CC identity removal. Each has
an inline reason. Dated 2026-07-14 per the block's own header comment and
`tools/CLAUDE.md` known issue #20.

**Staleness-check claim, verified rather than repeated:** `tools/CLAUDE.md`
calls this ack "the pattern to copy" / "unchanged" and says "the generator
re-checks each ack against its own classification, so the YAML cannot rot."
That mechanism exists (`generate_commands.py:201 check_verb_semantics`), but
**`drift_check.py` never calls it** — `grep -n "check_verb_semantics\|
classify_real_semantics" tools/drift_check.py` returns nothing except a prose
comment mentioning the name. The re-validation this ack actually gets in CI
comes from a *different* mechanism than the one namechecked: pytest test
`tests/test_field_overrides.py::test_verb_semantics_acks_still_match_the_spec`,
which loads the real tracked specs and re-runs `classify_real_semantics`
against every acked path. I ran it directly:

```
tests/test_field_overrides.py::TestOverridesYamlValidity::test_verb_semantics_ack_shape PASSED
tests/test_field_overrides.py::TestOverridesYamlValidity::test_verb_semantics_acks_still_match_the_spec PASSED
```

Both pass — **the 6 acks are currently accurate, not stale.** But the
enforcement point is `pytest tests/` (CI job `test`), not
`python -m tools.drift_check` (CI job `drift-gate`) — the two are separate
jobs in `.github/workflows/ci.yml`. Someone who runs only the drift gate
locally, the way the tools/CLAUDE.md prose frames it ("the gate re-checks
each ack"), gets zero validation of `verb_semantics_ack`; they'd need to also
run the pytest suite. Not a suppressed finding (both CI jobs must presumably
pass to merge, and the test is real and currently green) — but the
"unchanged... the model" framing overstates that this lives in the same
mechanism as `naming_ack`/`spec_authority`/`inert_tag_ack`/
`undeclared_paging_ack`, which are re-validated **inside `drift_check.py`
itself** (checks 12, 9, 15, 16) on every single gate run. `[verified]`

### 2b. `spec_authority` (7 entries) — check 9

Read in full (`:973-1006`). 1 entry (`GET /locations`) is `basis: live`,
captured 2026-07-27 against org `ahobgood-lab`, with explicit `live_fields`
naming the 4 fields the winning spec omits by omission. The other 6 are
`spec: union, basis: unverified` — explicitly weaker, explicitly labeled as
such, each with a one-line reason it hasn't been live-verified (device job
error paths nobody has triggered; one partner-scoped endpoint unreachable with
this org's token). This is the fix for the "check 9 union hid a live-broken
`locations list` for months" incident (`tools/CLAUDE.md` decision record). No
entry here understates its own confidence — the file is honest about which 6
of 7 are guesses. **Deliberate, current, not quieted.**

### 2c. `inert_tag_ack` (1 entry) — check 15

`"AI Assistant"` tag, dormant because upstream removed it from the published
CC spec; `cc_ai_assistant.py` is kept hand-maintained (see §2f below — this
overlaps directly with `keep_endpoints`, and that overlap is where the real
problem lives, not here). The ack itself is correctly scoped (one tag, one
stated reason, re-validated every run per check 15's own code at
`drift_check.py:2740` — confirmed live output: `[15] override entries that
cannot apply: 0 (stale acks: 0)`).

### 2d. `undeclared_paging_ack` (2 entries) — check 16

Both entries (`ArchivedUser` SCIM list, `contacts/search`) are dated
2026-07-29, explicitly labeled "static evidence only — no live call," and each
states exactly what would make it stale (upstream declaring the missing
paging params, or a generator fix). Live run confirms: `[16] list commands
whose --all is inert on a paging endpoint: 0 (stale acks: 0)`. **Deliberate,
narrow, honestly hedged.**

### 2e. `naming_ack` (167 entries, not 171) — check 12

Counted precisely via `yaml.safe_load` (not grep, to avoid comment
false-matches): **167 entries, all severity HIGH, 0 CRITICAL, 0 MEDIUM**
(MEDIUM findings — 27 of them per the live gate run — are advisory-only and
correctly carry no ack, since they don't gate the build). Split:
42 `numeric-suffix` + 125 `resource-mismatch`.

**This differs from `tools/CLAUDE.md`'s own prose**, which states "171
entries (42 + 129)" as of 2026-07-28. `git log -S'resource-mismatch'` shows 4
entries were removed since — 3 in `2c4a7fa` ("fix(cli): --all was
undocumented, and three names answered a different question") and 1 more in
the same commit range, matching that commit's documented work (folding
`call-settings-for-me-phase-5`, renaming `cc-agents list`→`list-activities`,
etc.). **This is the mechanism working as designed** ("deleting a fixed
command's ack is part of fixing it"), not drift — but it means the 171 figure
in `tools/CLAUDE.md` is now stale prose (167 is current truth), a minor
documentation-lag finding in its own right, not a suppression finding.

Live run: `[12] command names whose obvious reading is wrong, unacked: 0
(stale acks: 0; 27 MEDIUM reported, not gated)` — confirms every current HIGH
finding has a live-valid ack and none have rotted.

### 2f. `keep_endpoints` (1 entry) — check 1, CLI-ahead-of-spec — **MOST SUSPICIOUS FINDING**

`- "POST /event"   # cc-ai-assistant create` (`field_overrides.yaml:1303`).

Read the full comment block (`:1272-1303`). It records, in its own words:

> "2026-07-25 live probe (16:16:01 UTC) DISPROVES 'may still work
> server-side': POST https://api.wxcc-us1.cisco.com/event -> 404,
> content-length: 0, empty body... /event's bare gateway 404 means no route
> is registered upstream for this operation at all."

— i.e., the entry's *own justifying evidence*, added in the same commit that
kept the exemption, **disproves the reason the exemption exists.** The
comment then adds "RECOMMENDED FOLLOW-UP: retire this command group
entirely... Deferred from this branch only because it changes the drift
baseline from 176/1872 to 175/1871, which this plan's gate is specified to
match exactly."

`[verified]`:
- `git log -S'DISPROVES' --format="%H %ad %s" --date=short -- tools/field_overrides.yaml`
  → `1ae7eaa 2026-07-25 fix(cc): bring cc-ai-assistant up to the uniform
  --output/--fields surface` — the disproof and the decision to keep the
  entry landed in the **same commit**.
- `src/wxcli/commands/cc_ai_assistant.py` still exists on disk (last touched
  Jul 25) and is still registered: `_registry.py:38 ("cc_ai_assistant",
  "cc-ai-assistant")`.
- No commit since `1ae7eaa` (10 days ago as of today, 2026-08-04) removes it.
- Live gate run: `[1] spec->CLI missing: 0   CLI-ahead-of-spec: 0` — the
  exemption is actively suppressing what would otherwise be a live check-1
  finding, right now, on a command Cisco's own gateway 404s.

This is not an ack that quietly rotted — it is an ack whose comment **states
its own falsification** and was kept anyway, for a reason (matching a
historical baseline count in a specific plan) that has nothing to do with
whether the command works. It ships a `create` command to any operator or
agent that will always fail at the wire with a bare gateway 404, and the gate
reports clean. This is the single clearest instance in the whole suppression
surface of "quieted to keep a number green" rather than "deliberately
exempted for a live reason" — the live reason was checked and came back
negative, and the exemption survived the negative result.

### 2g. `skip_tags` / `tag_op_excludes` / `omit_query_params`

- **`omit_query_params: []`** — empty. Nothing suppressed. `[verified]`
- **`skip_tags`** (`:862-895`) — 1 global (`Beta *`), plus per-spec
  canonical-routing dedup entries (People/Reports/Devices/Workspaces/etc.
  each skipped in the *non-canonical* spec so `--all` regen doesn't clobber
  files) and 4 CC tags (`Functions`, `Activities`, `Templates`, `Events`) each
  with a one-line dated reason. `load_spec_ops`
  (`drift_check.py:390-421`) counts every skipped op into the "154
  deliberately skipped" figure the gate prints on line 1 of every run —
  confirmed live: `1845 non-skipped spec ops (154 deliberately skipped)`.
  These are architectural dedup/scope decisions with stated reasons, not
  findings hidden from a check; check 1 treats them as first-class "skipped,"
  not "passed." **Not suppression in the audited sense.**
- **`tag_op_excludes`** (`:899-911`) — 1 entry, `External Voicemail` excluding
  `/telephony/calls*` paths. This is the fix for known issue #22 (a real,
  shipped break where 24 mistagged call-control ops flooded
  `external-voicemail` and silently renamed `create` from "set MWI" to
  "dial a call"). **Deliberately has no staleness check**, and `check_inert_overrides`'s
  own docstring says so explicitly (`drift_check.py:2698-2701`): "Deliberately
  NOT flagged: `tag_merge` sources and `tag_op_excludes` keys... an absent tag
  makes them a no-op by design." That is a reasoned, stated design choice
  (the failure mode of *not* checking it is silent-no-op, not silent-wrong),
  not an oversight — I verified the docstring states the reasoning rather than
  omitting it silently.

---

## 3. `tools/spec_semantics.json` — check 19 (spec-change acknowledgment snapshot)

944KB / 25,385 lines — one encoded line per spec field, not human-curated, so
it cannot be "quietly edited" the way a short YAML list can; the audit
question here is whether it has a secondary ack layer riding on top of it.
`tools/CLAUDE.md` explicitly claims it does not ("a second ack mechanism on
top would reintroduce exactly the blind spot the snapshot removes, and
`test_check_19_has_no_ack_list` pins that it stays absent"). Verified rather
than repeated:

```
tests/test_drift_check_semantics.py::test_check_19_has_no_ack_list PASSED
```

Live gate run: `[19] spec changes not in tools/spec_semantics.json: 0
structural, 0 ID-kind flip(s)` and `[19] ADVISORY — spec prose that changed:
0` — the snapshot is currently in sync with the 9 tracked specs on disk,
confirmed by an actual run, not by trusting the file's freshness.

---

## Live gate run (full, for reference)

```
drift-check: 178 command sets (181 registered names incl. aliases), 1963 commands, 1845 non-skipped spec ops (154 deliberately skipped)

[1] spec->CLI missing: 0   CLI-ahead-of-spec: 0
[2] dead wxcli references: 0   (0 cited without the `wxcli` prefix)
...
[9] list commands with columns the response cannot fill: 0   (14 wrapper-shaped responses excluded)
[12] command names whose obvious reading is wrong, unacked: 0   (stale acks: 0; 27 MEDIUM reported, not gated)
[15] override entries that cannot apply: 0   (stale acks: 0)
[16] list commands whose --all is inert on a paging endpoint: 0   (stale acks: 0)
[19] spec changes not in tools/spec_semantics.json: 0 structural, 0 ID-kind flip(s)
[20] command sets with no docs/reference/ coverage: 0

result: PASS
```

Note `[1] CLI-ahead-of-spec: 0` is the number directly falsified by §2f above:
it is 0 **because** `keep_endpoints` exempts the one CLI-ahead command whose
own commit disproved its justification. A "0" on this line is not evidence of
nothing kept-ahead — it is evidence of one exemption doing its job.
