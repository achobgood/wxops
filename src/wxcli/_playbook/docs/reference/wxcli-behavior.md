# wxcli: How the Command Layer Behaves — flags, paging, errors, known issues

This is the reference for how the `wxcli` command layer itself behaves: the flags every command takes, how paging and `--fields` work, how partner multi-org tokens are handled, the eleven known issues, and where the cleanup command is documented. It is **not** a Webex API reference. For what an endpoint accepts or returns, use the reference doc for that feature (listed in `docs/reference/INDEX.md`). The `converged-recordings` group combines generated CRUD commands with hand-written `download` and `export` commands.

Use it when a command exits 0 but the answer looks wrong, when a count could be a single page, or when an error code shows up in the "Error → Known Issue Quick Reference" table of the root `CLAUDE.md`.

## Sources

- **The running CLI** — `wxcli <group> <command> --help` is always current and outranks everything below on command names, flags and requiredness.
- **Live measurements** — each dated claim in the sections below (for example "Measured live on 2026-08-01", "Verified live 2026-10-13", "probed live 2026-10-14") was observed against a real tenant on that date. A statement marked *unit-tested, not re-run live* was not.
- **Decision records** — ADR-12, ADR-13, ADR-14, ADR-16, ADR-17 and ADR-18 in the source repository's architecture decisions explain why the paging, `--verify` and `--offset` rules read as they do. Their conclusions are restated here; the rejected alternatives live there.

## Contents

1. [Common Flags](#1-common-flags)
2. [Partner Multi-Org Support](#2-partner-multi-org-support)
3. [Known Issues](#3-known-issues)
4. [Cleanup Command](#4-cleanup-command)
5. [When `--help` Is Wrong](#5-when---help-is-wrong)
6. [See Also](#see-also)

---

## 1. Common Flags

Every generated command takes `--fields` and `--output`/`-o` — **including `update`, `delete`, and action commands.** An earlier build had `--output` only on list/show/create and no `--fields` at all; that split is gone, so don't assume a write command lacks them.

- **`--fields`** — a JMESPath expression applied to the response before rendering. Same syntax on every command: a projection (`[].{name:name,id:id}`) reshapes the output, a filter (`` [?enabled==`false`] ``) narrows it.
- **`--output`/`-o`** — `table|json|text` on every command, plus `id` (create's default) on create only.
- **`--json-body`** accepts inline JSON, `file://path`, a bare path, or `-` for stdin (pairs with `--generate-json-body`; see Known Issue #2 below).
- **`--all`** — on **every `list` command**: fetch every page, not just the first. Default is one fetch; `--all` walks the whole collection and **overrides `--limit`**. Read the detail below before trusting a count.
- **`--verify`** — on **328 update commands** (every PUT/PATCH that has a same-path GET to read back from). Off by default. After the write it re-reads the resource and reports any field you sent that did not take, then prints either `Verified: … all N sent field(s) match.` or a per-field `sent X, now Y` list. It compares **only the fields you sent**, and it **never changes the exit code** — servers legitimately normalise values, so the CLI reports the difference and leaves the judgement to you. Since ADR-17 (2026-10-13; unit-tested, not re-run live) a sent field matches when the read-back **contains** it: `'30'` sent by a string-typed numeric flag matches `30`, `'true'` matches `true`, extra keys the server adds (defaults, ids on nested objects, including inside list elements) are ignored, and lists match regardless of order — but a list must come back with **exactly as many elements** as you sent, so an element you removed that the server kept shows as differing. A nested difference is named by its path (`callForwarding.always.enabled: sent True, now False`); a list of a different length, and a rewritten value such as an E.164 phone number, still show as differing. A list over 1,000 elements that comes back reordered, or any failure inside the compare, prints `could not compare the read-back (<ErrorType>)` — still exit 0. A sent field the read-back does not carry at all is listed separately as **could not be verified** (the endpoint may name it differently — e.g. `monitoring` writes `enableCallParkNotification` and reads `callParkNotificationEnabled`), and the summary then says `N matched, M could not be verified`, never "all match"; check those fields with `show`. **One exception:** a field you sent as `null` that the read-back omits counts as *matched*, because omitting a cleared field is how these endpoints read it back (an ignored clear would bring the old value back, present, and show as differing). Use it whenever a write's success matters: a 2xx means the request was *accepted*, not that it was *applied*. `device-members` is the worked case — it does no port validation, so `PRIMARY` on two ports returns 200 and both persist. A command with no same-path GET deliberately does **not** offer the flag, because a `--verify` that silently verifies nothing is worse than none.
- **On/off fields are a flag pair, never a value.** A boolean body field renders as `--enabled` / `--no-enabled`; `--enabled true` is an error. Check the pair in `--help`.
- **Number fields are sent as text.** Every non-boolean body field renders as a text option, and the command puts the text into the body as a JSON string: `cc-entry-point create --service-level-threshold 60` sends `"serviceLevelThreshold": "60"`, not `60` (noted 2026-09-08; read in the generated command 2026-10-20). Whether an endpoint accepts the string form was not measured per endpoint; when a number must be a number, send it in `--json-body`.

**The `--calling-data` interlock.** `people list/show/create/update/show-me` now check the `--fields` expression before rendering: ask for `extension` or `locationId` without `--calling-data`, and the CLI says so on stderr instead of handing back a silent, confident zero. Measured live on 2026-08-01 — `people list --fields '[].extension' --all` returns `[]` on an org where 15 users have extensions; adding `--calling-data true` returns all 15. The check fires only on endpoints that actually accept the flag, so it can never point you at an option a command does not have.

Four worked examples:

```bash
# Projection — pick just the fields you need
wxcli people list --calling-data true --fields '[].{name:displayName,extension:extension}' -o json

# Filter — JMESPath predicates narrow the response client-side, before rendering
wxcli call-queue list --fields '[?enabled==`false`].name' -o json

# --fields + -o text: one bare value per line, composable in a shell pipeline
wxcli locations list --fields '[].id' -o text | while read -r LOC_ID; do
  wxcli call-park list "$LOC_ID" -o json
done

# --all: never answer "how many?" from a single page
wxcli people list --calling-data true --all --fields 'length(@)' -o json
```

If `--fields` reduces a non-empty response to an empty one, a note goes to stderr naming the unfiltered record count — stdout stays pipeable. The note states the fact (0 of N matched) without diagnosing the cause: it can mean a wrong expression, or it can mean the filter genuinely matched nothing. Decide which based on the expression and what you expected, not from the note alone.

**`--all` in detail — read this before counting or aggregating anything.** The default for a list command is a **single fetch**, which on a paging endpoint quietly hands back page one. `--all` walks the whole collection and overrides `--limit`. Three paging shapes are handled, so it behaves the same across the CLI: `Link: rel="next"`, Contact Center `page`/`pageSize`, and SCIM `startIndex`/`count`.

Three behaviors that will otherwise read as bugs:

- **It is deliberately a no-op on endpoints the spec says do not paginate** — that is roughly half the commands carrying it. The flag is uniform on every list command *by design*: an option present on most commands but not all teaches a rule that breaks unpredictably, costing a failed call plus a `--help` round trip each time (the same reasoning that closed the `--output` gap). One page back from `--all` on a non-paging endpoint is correct, not a failure. On a `list*` command whose response is one object (e.g. `user-settings list-privacy`, `call-queue list-night-service`, which print the whole object as JSON), `--all`, `--limit` and `--offset` are accepted and ignored, and hidden from `--help` (ADR-14).
- **Walking is bounded at 1000 pages**, overridable with `WXCLI_MAX_PAGES`. Hitting the ceiling prints an error to stderr containing the word **INCOMPLETE**. That word means records are missing — not that a request failed. Do not draw a conclusion from output that produced it.
- **Without `--all`, a truncated read warns on stderr, not stdout.** A single fetch that left pages behind prints `Note: N records returned and the server has more pages. Re-run with --all to fetch every page`. Since ADR-18 (2026-10-13; unit-tested, not re-run live) the note names only flags the command really offers: on a command with no page walker (a `show`, a single-object `list*`, an unpaged list) it ends `This command does not walk pages; see its --help for a cursor or paging option.` instead of advising an `--all` that does not exist or walks nothing. **You will see that note — do not assume otherwise.** (Measured 2026-08-01 on Claude Code and Codex 0.144.1: both merge stderr into the tool result the model reads, so it stays visible when stdout is piped, redirected to a file, or large enough to be truncated to a head preview — the note is written by `rest_get` *before* any row is rendered, so it lands on line 1. It is lost only if you suppress it yourself with `2>/dev/null` or `WXCLI_NO_PAGE_WARN=1`.) The failure mode this guards against is therefore *ignoring* the note, not missing it: if you see it and still answer a "how many" question, the answer is wrong. `WXCLI_NO_PAGE_WARN=1` suppresses the note when you have taken one page on purpose.

One precision on "overrides `--limit`": it overrides what is **fetched**. In `-o table` mode `--limit` still caps *printed* rows (with a visible `... N more` row); `-o json` prints everything fetched.

Practical rule: any question of the form *how many*, *which ones*, or *are there any* needs `--all` on a paging endpoint. A read that merely fetches a known record by ID does not.

Watch the inverse too: on a command whose default already walks every page, passing `--limit N` **switches it to a single fetch** and silently drops the rest. `--limit` narrows; it never just "caps the display."

**`--offset N` means "skip N records" on every list command whose endpoint honours it — not provably all of them** (see the Link-header measurement below), including the page-numbered Contact Center ones (`page`/`pageSize`), where the CLI translates it to the right page(s) and `--limit N` to the page size (ADR-12, 2026-10-13; before that both were sent under names those endpoints ignore), and the 5 SCIM-style identity lists (`scim-users list`, `scim-groups list`/`list-members`, `groups list`/`list-members`), where `--offset N` becomes `startIndex=N+1` and `--limit N` becomes `count` — an explicit `--start-index`/`--count` still wins (ADR-13). Drift check 23 fails the gate if a list command ever sends either flag under a name its endpoint does not declare. The truncation note names the absolute `--offset` of the next record wherever `--offset` is offered, so following it works on an endpoint that honours `--offset`, whether or not the command also has a `--page` flag (`cc-tasks list` has none); on a command whose endpoint is measured, or inferred from its spec, to ignore it (below) the note names `--all` only.

**Link-header lists are the exception, measured live 2026-10-13 (6 sampled; 158 more probed 2026-10-14 and the resulting spec rule, at the end of this paragraph).** `devices list`, `workspaces list`, `numbers list` and `hunt-group list` honour it (`--offset 2 --limit 3` equals items 2–4 of `--all`). `people list` and `licenses list` **ignore it**: `people list --offset 2 --limit 3` returned items 0–2, and `licenses list --limit 3` returned all 18 rows. On those two the truncation note's "or --offset N" hint used to loop back to page one. Since ADR-18 (2026-10-13) both are a declared, live-measured set the generator reads: `--offset` above 0 exits 2 with `Error: this endpoint ignores --offset …` before any request (Verified live 2026-10-13 on `people list --offset 2 --limit 3`, which names `--all`; `licenses list` and the reworded messages are unit-tested, not re-run live — on `licenses list` the message says to drop `--offset` and slice, never `--all`, because its `--all` walks nothing), and `people list`'s note names `--all` only (unit-tested; not re-run live). So use `--all` and slice — Verified live 2026-10-13: `people list --all --fields '[2:5].id'` returns the 3 items. `hunt-group list --offset 2 --limit 3` still equals items 2–4 of `--all` after the change (Verified live 2026-10-13, 7 records). `licenses list` ignores `max` too: `--limit` there caps the printed rows in `-o table` only, and `-o json` prints every license. **The other 158 were probed live 2026-10-14 (ADR-18 amendment), and the rule is now the spec.** 28 honour `--offset`; **14 more ignore it** and refuse it like `people list` — `device-dynamic-settings list`, `resource-group-memberships list`/`list-v2`, and, measured on temporary data, `locations list`, `webhooks list`, `rooms list`, `messages list`, `memberships list`, `room-tabs list`, `teams list`, `team-memberships list`, `meetings list-meetings`, `meeting-invitees list`, `meetings list-registrants` (Verified live 2026-10-14: `locations list --offset 2` exits 2; `--all` still works). Every one of the 48 measured matched its spec: those that declare `start` (sometimes via a `$ref`) honour it, those that do not ignore it. So the generator now **refuses `--offset` on every page-walking list whose spec declares no `start`/`offset`**, measured or not — 34 more (`cdr`, `security-audit`, `events`, recordings, meeting participants/Q&A/polls/transcripts/reports, partner/wholesale lists); their message says `its spec declares no offset parameter` instead of "measured live" (Verified live 2026-10-14: `admin-recordings list --offset 2` exits 2). On any refused command, use `--all` and slice with `--fields '[N:M]'`. The 82 lists whose spec declares `start` keep `--offset` and are expected, not proven, to honour it (28 of them measured).

---

## 2. Partner Multi-Org Support

wxcli supports partner/VAR/MSP admins who manage multiple customer orgs with a single partner token.

- **`wxcli configure`** — saves an `orgId` to the config file for every token. On a multi-org token it prompts for a selection; on a single-org token it saves that org automatically. It will not overwrite an org that is already configured.
- **`wxcli switch-org`** — change the active target org at any time. On a single-org token it now saves that org to the config too. The bare form prompts interactively, which will block a script or agent forever on a multi-org token — in automation always pass the id: `wxcli switch-org <orgId>`.
- **`wxcli clear-org`** — remove the saved `orgId` to revert to single-org behavior.
- **`wxcli whoami`** — shows a "Target:" line when an org is set.
- **Most generated commands** auto-inject `orgId` from config on endpoints that accept it (generator `auto_inject_from_config`). No flag is required — the parameter is injected transparently.
- The former hand-coded trio (licenses, locations, numbers) is retired — all three are generated modules now with the same orgId injection. `users` is an alias for the generated `people` group; `licenses-api` is a deprecated one-release alias for `licenses` (renamed 2026-07-02).
- The builder agent has a blocking org confirmation step at session start (section 2b) when a partner token is detected.

See `docs/reference/authentication.md` (Partner/Multi-Org Tokens section) for full details.

---

## 3. Known Issues

1. **call-controls requires user-level OAuth.** Admin tokens get 400 "Target user not authorized". The CLI now detects this error and prints a tip about needing user-level OAuth.
2. **Complex nested settings need `--json-body`.** The generator skips deeply nested object/array body fields. Run the command with `--generate-json-body` to print an indented request-body skeleton and exit before authenticating, e.g. `wxcli user-settings update-call-forwarding PERSON_ID --generate-json-body`; edit the printed skeleton and pass it back via `--json-body`. Caveat, verified live: `--generate-json-body` does not bypass required positional arguments — `wxcli call-queue create --generate-json-body` fails with `Missing argument 'LOCATION_ID'`; pass a placeholder positional first, e.g. `wxcli call-queue create dummy-location-id --generate-json-body`. `cc-team`, `cc-skill-profile` and `cc-desktop-profile` `create`/`update` had no `--generate-json-body` (and required a dummy `--team-dto` / `--skill-profile-dto` / `--agent-profile-dto` beside `--json-body`) because the spec declares their body as a query parameter; since the generator fix of 2026-10-13 (ADR-16) they take `--json-body` alone and offer `--generate-json-body`, and the old option is accepted and ignored — Verified live 2026-10-13 on a temporary team, skill profile and desktop profile (create, show, update, delete; the old option on update for teams and desktop profiles; not tried: the old option on create, or on update for skill profiles).
3. **my-call-settings and mode-management require calling-licensed user.** All `/people/me/*` endpoints return 404 (error 4008) if the authenticated user doesn't have a Webex Calling license. The `my-call-settings` group (130 commands) covers base + UserHub Phase 2/3/4/5 self-service endpoints. Phase 5 was folded in on 2026-07-29 — it had been shipping as its own group named `call-settings-for-me-phase-5`; its 7 commands are now `show-personal-assistant`, `update-personal-assistant`, `show-voicemail-rules`, `update-voicemail-pin`, `show-hoteling-guest`, `update-hoteling-guest`, `list-available-hosts`. The old group name is **deliberately not aliased**: `my-call-settings show`/`update`/`list` are the Preferred Answer Endpoint commands, so an alias would have answered a different question with exit 0. The CLI detects this error and prints a tip.
4. **19 person settings are user-only (no admin path).** Admin tokens get 404. Use `wxcli my-call-settings` with user-level OAuth. Includes core settings (`callBlock`, `callNotify`, `preferredAnswerEndpoint`, `guestCalling`, `modeManagement`) plus informational/read-only endpoints (`availableCallerIds`, `queues`, `services`, etc.). **`callCaptions` and `anonymousCallReject` are NOT user-only** — verified live 2026-10-13: `user-settings show-call-captions` and `show-anonymous-call-reject` return 200 with an admin token (the "19" count predates this correction and has not been re-counted). See `docs/reference/self-service-call-settings.md` gotchas.
5. **Two path families for person settings.** Classic `/people/{id}/features/` vs newer `/telephony/config/people/{id}/`. Some names differ. See `docs/reference/person-call-settings-behavior.md` (lines 36-54) for the full mapping table.
6. **Workspace `/telephony/config/` settings require Professional license.** Basic workspaces get 405. See `docs/reference/devices-workspaces.md` gotcha #10 for the endpoint-by-license matrix.
7. **Customer Assist queues require `--has-cx-essentials true` on `call-queue` commands.** Use `wxcli customer-assist` (alias `cx-essentials`) as the primary CLI group for CX queue management. Standard `call-queue list` omits CX queues unless the flag is passed. See `docs/reference/call-features-additional.md` cross-cutting gotchas.
8. **Supervisor delete returns 204 but supervisor persists.** Workaround: `update-supervisors` with `action: DELETE` on each agent. See `docs/reference/call-features-additional.md` gotchas.
9. **`virtual-extensions` commands use wrong ID type.** Uses `VIRTUAL_EXTENSION`-encoded IDs but virtual lines use `VIRTUAL_LINE` IDs. Still separate path families in the spec (`virtualExtensions/{extensionId}` vs `virtualLines/{virtualLineId}`). `wxcli cleanup` uses raw REST as a workaround. See `docs/reference/virtual-lines.md` Gotchas #9.
10. **Device config schema is firmware-dependent.** Per-line ringtone was absent on PhoneOS 3.5/3.6 but fixed in 4.1. Offline/expired devices retain a stale schema. See `docs/reference/devices-platform.md` gotchas #10-11.
11. **Contact Center (`cc-*`) commands need a token carrying the `cjp:config` scopes, plus region config.** A full-admin personal access token **does** work — verified live 2026-10-13 on the CC Bootcamp Sandbox: `cc-flow` list/show/export/validate/lock/unlock, `cc-queue list`, `cc-entry-point list` and `cc-global-vars list-cad-variable` all returned 200, no 403 anywhere. (An April 2026 entry here said PATs get 403; that was a global-variables 403 on the same org and it no longer reproduces.) If you do get a 403 with a `ccconfig_` tracking ID, the token lacks the scopes: use an OAuth integration or Service App with `cjp:config_read`/`cjp:config_write` explicitly selected, and re-authorize after adding scopes. The CC API also requires the bare UUID org ID (not the base64 Spark ID); `get_cc_org_id()` in `config.py` handles decoding. See `docs/reference/contact-center-core.md` gotchas #18-23. A PAT also carries `cjp:user`, the per-agent runtime scope — verified live driving `register()`/`stationLogin()`/`setAgentState()` through the `@webex/contact-center` JS SDK. See `docs/reference/contact-center-agent-sdk.md` §10.

---

## 4. Cleanup Command

Detailed context in `.claude/rules/cleanup.md` (the file ships; its `paths:` glob targets `cleanup.py`, so it auto-loads only in a source checkout). Contains: all flags, 13-layer deletion order, and known behaviors (virtual line workaround, location disable propagation, workspace ordering).

**Read the rule when:** running `wxcli cleanup`, modifying cleanup logic, or debugging deletion failures. Do not wait for it to auto-load — read the file. The `teardown` skill already instructs this as its step 1.

---

## 5. When `--help` Is Wrong

The measured cases behind three rules in root `CLAUDE.md` § Source of Truth Precedence: a read-only command can be silently wrong; `--help` loses to the docs on argument ID kinds and enum choices; a value from the spec is a hypothesis, not a correction. The rules stay in the root; the evidence moved here in Plan 4 (2026-10-20).

- **A read-only command can be silently wrong** (in the root since 2026-07-17). Real case: the query-live recipe said `wxcli people list -o json`, but Webex omits `extension` and `locationId` unless `--calling-data true` is passed. The command exits 0 and returns every user, so "how many users have extensions?" answers **0** instead of the true count. No error, no warning. The `--calling-data` interlock in § 1 now catches this case on `people` commands.
- **Argument ID kinds** (in the root since 2026-07-29). 79 arguments declare a kind their own name contradicts — `location_id` help-typed "Webex PEOPLE id", `call_queue_id` typed HUNT_GROUP. Where help and the doc disagree on an ID *kind*, the doc is right.
- **Enum choices** (in the root since 2026-07-29). Proven both ways — `--event all` works though the enum omits it, and `announcements --location-id` advertises a sample ID that exits 1. A live call settles it, not a re-read of `--help`.
- **A spec value is a hypothesis** (measured 2026-10-13). An automated pass "corrected" `cc-skill create`'s `skillType` from `PROFICIENCY` to the spec's `Proficiency`; the live API rejects title case (400 listing `BOOLEAN, ENUM, PROFICIENCY, TEXT`) — while the sibling Global Variable `variableType` requires title case. The same day the spec was also wrong on the flow-import body shape and on what `cc-dial-number create` requires (`location`, `regionId`).

---

## See Also

- **[authentication.md](authentication.md)** — token types, scopes and the Partner/Multi-Org Tokens section behind § 2.
- **[provisioning.md](provisioning.md)** — `--calling-data` on `people` commands, the trap described in § 1.
- **[self-service-call-settings.md](self-service-call-settings.md)** — the user-only (`/people/me/`) endpoints behind Known Issues #3 and #4.
- **[virtual-lines.md](virtual-lines.md)** — the virtual-line vs virtual-extension ID types behind Known Issue #9.
- **[contact-center-core.md](contact-center-core.md)** — the Contact Center token and region setup behind Known Issue #11.
