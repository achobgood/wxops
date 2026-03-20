# Playbook Review Fixes Implementation Plan

> **STATUS: COMPLETED (2026-03-20).** All 10 tasks in this plan have been executed across multiple sessions (not via this plan's checkboxes, but via direct work on the files). Verified 2026-03-20: command counts synced to 100, all positional arg fixes applied, all skill command names corrected, compaction recovery in all 14 skills, NEEDS VERIFICATION tags swept (136→2), recording bug descriptions consistent. **Do not re-execute this plan.**

> ~~**For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.~~

**Goal:** Fix all documentation-vs-reality mismatches found in the 4-agent playbook review — incorrect CLI commands, wrong flags, non-existent commands, stale counts, missing error handling, and reference doc contradictions.

**Architecture:** Pure documentation/content fixes across 7 files. No code generation, no tests. Every fix is verified against `wxcli <group> <command> --help` output as ground truth. Tasks are grouped by file to minimize context switching, with cross-cutting fixes (like command count) handled in a dedicated task.

**Tech Stack:** Markdown editing only. `wxcli --help` for verification.

---

## File Map

| File | Action | What Changes |
|------|--------|-------------|
| `.claude/agents/wxc-calling-builder.md` | Modify | Fix 12 command errors, update counts, fix template contradictions |
| `.claude/skills/configure-features/SKILL.md` | Modify | Fix 14 command errors, remove stale CX Essentials contradiction |
| `.claude/skills/manage-call-settings/SKILL.md` | Modify | Fix 12 command name errors, add error handling section, fix schedule commands |
| `.claude/skills/provision-calling/SKILL.md` | Modify | Fix 1 command error, remove env var reference, add error handling section |
| `.claude/skills/wxc-calling-debug/SKILL.md` | Modify | Fix 3 command errors (positional args) |
| `README.md` | Modify | Fix 14 errors — group names, flags, counts, placeholder URL, auth section |
| `docs/reference/wxcadm-xsi-realtime.md` | Modify | Fix contradictory recording bug descriptions |

---

## Verification Protocol

Before editing any command in any file, run `wxcli <group> <command> --help` to confirm:
1. The group exists
2. The command exists
3. Which arguments are positional vs `--option`
4. Which flags are required
5. Whether `--output` is available

**Do NOT guess.** If `--help` output differs from what the review agents reported, trust `--help`.

---

### Task 1: Fix Agent File — Command Errors and Counts

**Files:**
- Modify: `.claude/agents/wxc-calling-builder.md`

**Context:** The agent file has 12 command errors spanning lines 20-299. The review found: wrong command count (line 20), wrong `users create` flags (line 236-237), positional args shown as `--location` flags (lines 239-242), wrong `--enabled true` syntax (line 248), wrong `numbers-api` flag (line 253), non-existent `--output json` on `users show` (line 291).

- [ ] **Step 1: Verify all commands against CLI help**

Run each of these and note the actual syntax:
```bash
wxcli --help 2>&1 | grep -c "^  "  # count command groups
wxcli users create --help
wxcli location-schedules create --help
wxcli auto-attendant create --help
wxcli call-queue create --help
wxcli hunt-group create --help
wxcli call-park create --help
wxcli user-settings update-do-not-disturb --help
wxcli numbers-api list --help
wxcli users show --help
wxcli locations show --help
```

- [ ] **Step 2: Fix line 20 — stale command count**

Change: `"53 command groups covering 840+ commands"`
To: Match actual count from `wxcli --help` output. Do NOT hardcode — count the groups from `wxcli --help 2>&1 | grep -c "^  "` and use that number. Drop the "covering X commands" secondary count (hard to maintain).

- [ ] **Step 3: Fix lines 236-237 — `users create` flags**

Change:
```
wxcli users create --display-name "John Smith" --first-name "John" --last-name "Smith" --email "jsmith@example.com"
```
To: Use actual flags from `--help` (expected `--first`, `--last`, no `--display-name`)

- [ ] **Step 4: Fix line 239 — `location-schedules create` positional arg**

Change: `wxcli location-schedules create --location LOCATION_ID --name "..." --type businessHours`
To: `wxcli location-schedules create LOCATION_ID --name "..." --type businessHours`

- [ ] **Step 5: Fix line 240 — `auto-attendant create` positional arg + missing required flag**

Change: `wxcli auto-attendant create --location LOCATION_ID --name "..." --extension 1000`
To: `wxcli auto-attendant create LOCATION_ID --name "..." --extension 1000 --business-schedule "..."`

- [ ] **Step 6: Fix line 241 — `call-queue create` positional arg**

Change: `wxcli call-queue create --location LOCATION_ID --name "..." --extension 2000`
To: `wxcli call-queue create LOCATION_ID --name "..." --extension 2000`

- [ ] **Step 7: Fix line 242 — `hunt-group create` positional arg + missing required flag**

Change: `wxcli hunt-group create --location LOCATION_ID --name "..." --extension 3000`
To: `wxcli hunt-group create LOCATION_ID --name "..." --extension 3000 --enabled`

- [ ] **Step 8: Fix line 248 — `update-do-not-disturb` boolean flag syntax**

Change: `wxcli user-settings update-do-not-disturb PERSON_ID --enabled true`
To: `wxcli user-settings update-do-not-disturb PERSON_ID --enabled`
(Boolean flags don't take `true`/`false` args — use `--enabled` / `--no-enabled`)

- [ ] **Step 9: Fix line 253 — `numbers-api list` flag name**

Change: `wxcli numbers-api list --location LOCATION_ID`
To: `wxcli numbers-api list --location-id LOCATION_ID`

- [ ] **Step 10: Fix line 291 — `users show` doesn't have `--output`**

Change: `wxcli users show PERSON_ID --output json`
To: `wxcli users show PERSON_ID`
(If `--output json` is needed, note to use `wxcli people show PERSON_ID --output json` as alternative, or verify if `users show` supports it)

- [ ] **Step 11: Commit**

```bash
git add .claude/agents/wxc-calling-builder.md
git commit -m "fix: correct 12 wxcli command errors in agent file

Fix positional args shown as --location flags, wrong users create flags,
stale command count, boolean flag syntax, and non-existent --output flag."
```

---

### Task 2: Fix Agent File — Template and Structural Issues

**Files:**
- Modify: `.claude/agents/wxc-calling-builder.md`

**Context:** The review found: rollback contradiction between template reference (line ~420 says auto-rollback) and agent rule (says ask user first), env var contradiction (line 65 says don't use env vars but provision-calling references them), duplicate reference doc inventories (~130 lines of redundancy), hardcoded install path (line 41), and non-existent example directory reference (line 591).

- [ ] **Step 1: Check for rollback contradiction (may be a no-op)**

Search the agent file for any text that says "auto-rollback" or "executes rollback automatically." If found, change to: "The agent will present rollback options for user decision. Do NOT auto-rollback without asking." If the file already says "Do NOT auto-rollback without asking" and there's no contradicting text, skip this step — the reviewer noted this may already be correct.

- [ ] **Step 2: Fix hardcoded install path (line 41)**

Change: `pip install -e /Users/ahobgood/Documents/webexCalling/src`
To: `pip install -e .` (from repo root)

- [ ] **Step 3: Deduplicate reference doc inventories**

The agent has two near-identical sections listing reference docs (REFERENCE DOC LOADING ~lines 459-535 and REFERENCE FILES ~lines 555-592). Merge into one section. Keep the task-grouped version (REFERENCE DOC LOADING) and remove the flat table.

- [ ] **Step 4: Remove non-existent example directory reference**

If line 591 references `docs/examples/user-provisioning/`, remove or comment it out — directory doesn't exist.

- [ ] **Step 5: (Optional) Clarify wxcadm mixing rule (CRITICAL RULES)**

If the current text says "Do not mix wxcadm and wxcli in the same execution block" and could be misread as "never use both in one session," consider clarifying to: "Do not mix wxcadm and wxcli within a single execution step. They use different auth mechanisms. You may use both in the same deployment plan across different steps." If the existing wording is already clear, skip this step.

- [ ] **Step 6: Fix bulk async fallback language**

Find any reference to "fall back to async Python via raw HTTP" and change to "fall back to async Python via wxc_sdk" (the reference doc uses SDK methods, not raw HTTP).

- [ ] **Step 7: Commit**

```bash
git add .claude/agents/wxc-calling-builder.md
git commit -m "fix: resolve agent template contradictions and structural issues

Fix rollback auto/manual contradiction, hardcoded install path, deduplicate
reference doc inventories, clarify wxcadm mixing rule, fix async fallback language."
```

---

### Task 3: Fix configure-features Skill

**Files:**
- Modify: `.claude/skills/configure-features/SKILL.md`

**Context:** 14 command errors. Systematic pattern: all `create` commands use `--location LOCATION_ID` instead of positional. Non-existent commands: `add-agent` (CQ and HG), `available-agents`, `list-screen-pop`. Self-contradiction on CX Essentials CLI availability (line 378 vs rule 10 at line 547). Wrong `location-voicemail show` command name.

- [ ] **Step 1: Verify all commands against CLI help**

Run each:
```bash
wxcli auto-attendant create --help
wxcli call-queue create --help
wxcli call-queue --help  # check for add-agent, list-available-agents-queues
wxcli hunt-group create --help
wxcli hunt-group --help  # check for add-agent
wxcli paging-group create --help
wxcli paging-group list --help
wxcli location-voicemail create --help
wxcli location-voicemail --help  # check show vs show-voicemail-groups
wxcli cx-essentials --help  # check show-screen-pop vs list-screen-pop
wxcli cx-essentials show-screen-pop --help
wxcli cx-essentials update-screen-pop --help
```

- [ ] **Step 2: Fix auto-attendant create (line ~148)**

Change: `wxcli auto-attendant create --location LOCATION_ID --name "..." --extension 1000 --business-schedule "..."`
To: `wxcli auto-attendant create LOCATION_ID --name "..." --extension 1000 --business-schedule "..."`

- [ ] **Step 3: Fix call-queue create (line ~189)**

Change: `wxcli call-queue create --location LOCATION_ID --name "..." --extension 2000`
To: `wxcli call-queue create LOCATION_ID --name "..." --extension 2000`

- [ ] **Step 4: Remove non-existent `call-queue add-agent` (line ~198)**

Replace with a note explaining how to add agents: use `wxcli call-queue update LOCATION_ID QUEUE_ID --json-body '{"agents": [...]}'` or reference the `list-available-agents-queues` command for finding agent IDs.

- [ ] **Step 5: Fix `call-queue available-agents` (line ~204)**

Change: `wxcli call-queue available-agents LOCATION_ID`
To: `wxcli call-queue list-available-agents-queues LOCATION_ID`

- [ ] **Step 6: Fix hunt-group create (line ~235)**

Change: `wxcli hunt-group create --location LOCATION_ID --name "..." --extension 3000`
To: `wxcli hunt-group create LOCATION_ID --name "..." --extension 3000 --enabled`

- [ ] **Step 7: Remove non-existent `hunt-group add-agent` (line ~244)**

Replace with: use `wxcli hunt-group update LOCATION_ID HG_ID --json-body '{"agents": [...]}'`

- [ ] **Step 8: Fix paging-group create (line ~265)**

Change: `wxcli paging-group create --location LOCATION_ID --name "..." --extension 8100`
To: `wxcli paging-group create LOCATION_ID --name "..." --extension 8100`

- [ ] **Step 9: Fix paging-group list flag (line ~275)**

Change: `wxcli paging-group list --location LOCATION_ID`
To: `wxcli paging-group list --location-id LOCATION_ID`

- [ ] **Step 10: Fix location-voicemail create (line ~365)**

Change: `wxcli location-voicemail create --location LOCATION_ID --name "..." --extension 8200 --passcode 740384`
To: `wxcli location-voicemail create LOCATION_ID --name "..." --extension 8200 --passcode 740384 --language-code en_us`

- [ ] **Step 11: Fix CX Essentials commands (lines ~387-391)**

Change `list-screen-pop` to `show-screen-pop`. Change `--location-id LOCATION_ID --queue-id QUEUE_ID` to positional `LOCATION_ID QUEUE_ID`. Same for `update-screen-pop`.

- [ ] **Step 12: Fix `location-voicemail show` (line ~510)**

Change: `wxcli location-voicemail show LOCATION_ID VMG_ID`
To: `wxcli location-voicemail show-voicemail-groups LOCATION_ID VMG_ID`

- [ ] **Step 13: Remove CX Essentials contradiction in Rule 10 (line ~547)**

Delete or update the statement "CX Essentials... no wxcli commands yet" — CX Essentials CLI commands exist and are documented earlier in the same file.

- [ ] **Step 14: Commit**

```bash
git add .claude/skills/configure-features/SKILL.md
git commit -m "fix: correct 14 command errors in configure-features skill

Fix positional args, remove non-existent add-agent commands, fix CX Essentials
command names, add missing required flags, resolve CX CLI availability contradiction."
```

---

### Task 4: Fix manage-call-settings Skill

**Files:**
- Modify: `.claude/skills/manage-call-settings/SKILL.md`

**Context:** 12 errors. Systematic pattern: 6 `show-*` commands should be `list-*`. Non-existent `--file` flag on 3 greeting commands. Schedule CRUD commands have wrong names/args. Missing error handling section entirely. `update-caller-id` should be `update-caller-id-features`.

- [ ] **Step 1: Verify all commands against CLI help**

Run each:
```bash
wxcli user-settings list-privacy --help 2>&1
wxcli user-settings list-monitoring --help 2>&1
wxcli user-settings list-push-to-talk --help 2>&1
wxcli user-settings list-outgoing-permission --help 2>&1
wxcli user-settings list-reception --help 2>&1
wxcli user-settings show-calling-behavior --help 2>&1
wxcli user-settings update-caller-id-features --help 2>&1
wxcli user-settings configure-busy-voicemail --help 2>&1
wxcli user-settings configure-no-answer --help 2>&1
wxcli user-settings configure-call-intercept --help 2>&1
wxcli user-settings create --help 2>&1
wxcli user-settings delete --help 2>&1
wxcli user-settings --help 2>&1 | grep -i schedule
```

- [ ] **Step 2: Fix settings catalog table — 6 `show-*` → `list-*` corrections**

In the settings catalog table (lines ~81-135), fix these show command names:
- `show-privacy` → `list-privacy`
- `show-monitoring` → `list-monitoring`
- `show-push-to-talk` → `list-push-to-talk`
- `show-outgoing-permission` → `list-outgoing-permission`
- `show-reception` → `list-reception`
- Calling Behavior: if table shows `list`, verify — actual may be `show-calling-behavior`

- [ ] **Step 3: Fix `update-caller-id` (line ~101)**

Change: `update-caller-id`
To: `update-caller-id-features`

- [ ] **Step 4: Fix `show-privacy` in example (line ~177)**

Change: `wxcli user-settings show-privacy PERSON_ID --output json`
To: `wxcli user-settings list-privacy PERSON_ID --output json`

- [ ] **Step 5: Remove `--file` flag from 3 greeting commands (lines ~258, 259, 274)**

These commands only accept `--json-body`, not `--file`:
- `configure-busy-voicemail` — remove `--file greeting.wav`, show `--json-body` usage
- `configure-no-answer` — same
- `configure-call-intercept` — same

- [ ] **Step 6: Fix schedule CRUD commands (lines ~319-344)**

Verify actual schedule commands against `--help` and fix:
- `create` — verify positional args and required flags
- `update-schedules` — verify if this exists; if not, document what to use instead
- `delete` — document that it deletes events (not schedules) and requires 4 positional args: `PERSON_ID SCHEDULE_TYPE SCHEDULE_ID EVENT_ID`
- `delete-events` — verify; if it doesn't exist, remove and clarify that `delete` handles events

- [ ] **Step 7: Add error handling section**

Add a new section after the CRITICAL REMINDERS (~line 431) with standardized error handling matching the agent's A/B/C pattern:

```markdown
## Error Handling

When a wxcli command fails:

**A. Fix and retry** — If the error is a missing required field, wrong ID, or format issue:
1. Read the full error message
2. Run `wxcli <group> <command> --help` to check required flags
3. Fix the command and retry

**B. Skip and continue** — If the error is non-blocking (e.g., setting already configured):
1. Verify current state with the corresponding show/list command
2. If already correct, skip and move to next setting

**C. Escalate** — If the error is unclear or persistent:
1. Run with `--debug` to see the raw HTTP request/response
2. Invoke `/wxc-calling-debug` for systematic diagnosis

Common errors:
- 400: Check required fields, verify IDs exist, check `--json-body` format
- 403: Check token scopes — some settings need `spark-admin:people_write`
- 404: Verify person/location ID is correct and has calling license
- 409: Resource already exists — GET current state before retrying
```

- [ ] **Step 8: Fix bulk async example — add concurrency limit (lines ~364-379)**

Change: `asyncio.gather(*[...for u in calling_users])`
To: Use `AsWebexSimpleApi(concurrent_requests=40)` and note the SDK's internal semaphore.

- [ ] **Step 9: Commit**

```bash
git add .claude/skills/manage-call-settings/SKILL.md
git commit -m "fix: correct 12 command errors and add error handling to manage-call-settings

Fix show-*/list-* command names, remove non-existent --file flags, fix schedule
CRUD commands, add standardized error handling section, fix async concurrency."
```

---

### Task 5: Fix provision-calling Skill

**Files:**
- Modify: `.claude/skills/provision-calling/SKILL.md`

**Context:** 3 issues: `numbers-api add` should be `create` (line ~292), references `WEBEX_ACCESS_TOKEN` env var (agent says don't use env vars), missing error handling section.

- [ ] **Step 1: Fix `numbers-api add` → `create` (line ~292)**

Change: "add it via `wxcli numbers-api add`"
To: "add it via `wxcli numbers-api create`"

- [ ] **Step 2: Remove env var reference**

Find any reference to `WEBEX_ACCESS_TOKEN` as a troubleshooting item and replace with: "Check `~/.wxcli/config.json` for stored token or run `wxcli configure` to set token."

- [ ] **Step 3: Add error handling section**

Add after the CRITICAL RULES section (~line 302), using the same A/B/C pattern from Task 4 Step 7, adapted for provisioning-specific errors:

```markdown
## Error Handling

When a wxcli command fails:

**A. Fix and retry** — Missing required field, wrong ID, format issue:
1. Read the full error message
2. Run `wxcli <group> <command> --help` to check required flags
3. Fix the command and retry

**B. Skip and continue** — Resource already exists or already configured:
1. Verify current state: `wxcli users show PERSON_ID` or `wxcli locations show LOCATION_ID`
2. If state is correct, skip to next operation

**C. Escalate** — Unclear or persistent error:
1. Run with `--debug` for raw HTTP details
2. Invoke `/wxc-calling-debug` for systematic diagnosis

Provisioning-specific errors:
- 400 on `users create`: Check email format, verify no existing user with same email
- 400 on `numbers-api create`: Check E.164 format (+1XXXXXXXXXX), verify number not already assigned
- 403: Check token has `spark-admin:people_write` and `spark-admin:telephony_config_write` scopes
- 409: User/location already exists — GET current state first
```

- [ ] **Step 4: Fix Operation E gap (Step 6)**

If operations skip from D to F, renumber to be sequential (A through however many there are).

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/provision-calling/SKILL.md
git commit -m "fix: correct command name, remove env var reference, add error handling

Fix numbers-api add→create, replace WEBEX_ACCESS_TOKEN with wxcli configure,
add standardized error handling section, fix operation numbering."
```

---

### Task 6: Fix wxc-calling-debug Skill

**Files:**
- Modify: `.claude/skills/wxc-calling-debug/SKILL.md`

**Context:** 3 command errors — all are the `--location` positional arg pattern in example commands (lines 92, 184, 256).

- [ ] **Step 1: Verify commands**

```bash
wxcli auto-attendant create --help  # confirm LOCATION_ID is positional
```

- [ ] **Step 2: Fix 3 `auto-attendant create` examples**

Lines ~92, ~184, ~256 all show:
`wxcli auto-attendant create --location LOC_ID --name "Test" --extension 9999 --debug`

Change to:
`wxcli auto-attendant create LOC_ID --name "Test" --extension 9999 --business-schedule "Default" --debug`

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/wxc-calling-debug/SKILL.md
git commit -m "fix: correct positional arg syntax in debug skill examples"
```

---

### Task 7: Fix README.md

**Files:**
- Modify: `README.md`

**Context:** 14 errors. Placeholder git URL (line 8), wrong command count (lines 3, 26), wrong `locations create` flags (lines 32-37), wrong group names in table (7 entries), wrong `create` command syntax (lines 43-52). Also missing: auth setup via `wxcli configure`, "Finding IDs" section, `--json-body` mention, `--debug` mention.

- [ ] **Step 1: Verify all commands and group names**

```bash
wxcli --help 2>&1 | head -120  # get actual group list
wxcli locations create --help
wxcli auto-attendant create --help
wxcli call-queue create --help
wxcli hunt-group create --help
```

- [ ] **Step 2: Fix placeholder URL (line 8)**

Change: `https://github.com/your-org/webexCalling.git`
To: Remove the clone step entirely and just show `cd webexCalling && pip install -e .`
(Or replace with actual URL if one exists)

- [ ] **Step 3: Fix command counts (lines 3 and 26)**

Update "840+ commands" and "53 command groups" to match actual `wxcli --help` count.

- [ ] **Step 4: Fix auth section (lines 13-19)**

Add `wxcli configure` as the primary auth method alongside the env var approach:
```bash
# Option 1: Persistent (recommended)
echo "YOUR_TOKEN" | wxcli configure

# Option 2: Environment variable (per-session only)
export WEBEX_ACCESS_TOKEN="YOUR_TOKEN"
```

- [ ] **Step 5: Fix `locations create` example (lines 32-37)**

**IMPORTANT:** `wxcli locations create --help` does NOT have discrete address flags (`--address1`, `--postal-code`, etc.). The README's example is wrong — those flags don't exist. `--time-zone` IS correct (do not change it).

Remove the address flag lines from the example. Replace with a `--json-body` approach for address:
```bash
wxcli locations create --name "San Jose Office" --time-zone "America/Los_Angeles" \
  --json-body '{"address": {"address1": "123 Main St", "city": "San Jose", "state": "CA", "postalCode": "95113", "country": "US"}}'
```

Or simplify the example to show only the flags that actually exist (`--name`, `--time-zone`, `--preferred-language`, `--announcement-language`, `--latitude`, `--longitude`, `--notes`, `--json-body`) and note that address must go through `--json-body`.

- [ ] **Step 6: Fix `auto-attendant create` (line 43)**

Change: `wxcli auto-attendant create --location LOCATION_ID --name "..." --extension 1000`
To: `wxcli auto-attendant create LOCATION_ID --name "..." --extension 1000 --business-schedule "Business Hours"`

- [ ] **Step 7: Fix `call-queue create` (line 47)**

Change: `wxcli call-queue create --location LOCATION_ID ...`
To: `wxcli call-queue create LOCATION_ID ...`

- [ ] **Step 8: Fix `hunt-group create` (line 51)**

Change: `wxcli hunt-group create --location LOCATION_ID ...`
To: `wxcli hunt-group create LOCATION_ID ... --enabled`

- [ ] **Step 9: Fix command group table (lines ~70-78)**

Fix all 7 wrong group names:
- `numbers-manage` → `numbers-api`
- `schedules` → `location-schedules`
- `auto-attendants` → `auto-attendant`
- `call-queues` → `call-queue`
- `hunt-groups` → `hunt-group`
- `paging` → `paging-group`
- `voicemail-groups` → `location-voicemail`

- [ ] **Step 10: Add "Finding IDs" tip**

Add a brief note after the examples:
```markdown
### Finding IDs
```bash
wxcli locations list --calling-only    # Get location IDs
wxcli users list --location LOC_ID     # Get person IDs
wxcli numbers-api list --location-id LOC_ID  # Get number inventory
```

- [ ] **Step 11: Add `--json-body` and `--debug` tips**

Add brief notes about these flags for complex settings and troubleshooting.

- [ ] **Step 12: Commit**

```bash
git add README.md
git commit -m "fix: correct 14 errors in README — commands, flags, group names, auth

Fix placeholder URL, stale counts, wrong flags on locations create, positional
args on all create commands, 7 wrong group names in table, add wxcli configure
auth method, add Finding IDs section."
```

---

### Task 8: Fix Reference Doc Contradictions

**Files:**
- Modify: `docs/reference/wxcadm-xsi-realtime.md`
- Modify: `docs/reference/person-call-settings-handling.md`

**Context:** Two issues: (1) contradictory recording bug descriptions at lines ~393 and ~940 in wxcadm-xsi-realtime.md, (2) misleading "N/A" for SimRing/SeqRing/PriorityAlert admin APIs in person-call-settings-handling.md.

- [ ] **Step 1: Read the wxcadm source to resolve the recording bug contradiction**

The duplicate `elif action.lower() == "resume"` bug has two contradictory descriptions:
- Line ~393: says `"resume"` maps to `PauseRecording` (wrong mapping)
- Line ~940 (Gotcha #10): says `"pause"` never reaches its intended branch (shadowed)

Check the wxcadm source at `../wxcadm_reference/` to determine which description is correct:
```bash
grep -n "resume\|pause\|Recording" ../wxcadm_reference/wxcadm/xsi.py | head -30
```

- [ ] **Step 2: Fix the recording bug descriptions**

Make both descriptions consistent. Based on the review agents' analysis, if there are two `elif action == "resume"` branches, the second one is dead code, and `"pause"` (between them) would be shadowed. Update line ~393 to match gotcha #10's interpretation, or vice versa — whichever matches the source code.

- [ ] **Step 3: Fix "Me" API Variants table in person-call-settings-handling.md**

At lines ~1058-1075, the table marks SimRing, SeqRing, and PriorityAlert as "N/A" under the admin column. But the Raw HTTP sections earlier in the same file document working admin endpoints at `telephony/config/people/{person_id}/...`.

Add a footnote or clarify: "N/A means the SDK class is not wired to `PersonSettingsApi` — the admin REST endpoint exists and works via raw HTTP (see Raw HTTP sections above)."

- [ ] **Step 4: Commit**

```bash
git add docs/reference/wxcadm-xsi-realtime.md docs/reference/person-call-settings-handling.md
git commit -m "fix: resolve recording bug contradiction, clarify SimRing admin API availability

Reconcile contradictory recording() bug descriptions in wxcadm-xsi-realtime.
Clarify that SimRing/SeqRing/PriorityAlert admin REST endpoints work even though
SDK classes are not wired to PersonSettingsApi."
```

---

### Task 9: Cross-File Command Count Sync

**Files:**
- Modify: `.claude/agents/wxc-calling-builder.md` (if not already fixed in Task 1)
- Modify: `CLAUDE.md`
- Modify: `README.md` (if not already fixed in Task 7)

**Context:** Three files have different command group counts: agent says 53, CLAUDE.md says 99, README says 53. Reality needs to be verified from `wxcli --help`.

- [ ] **Step 1: Get ground truth**

```bash
wxcli --help 2>&1 | grep -c "^  "
```

- [ ] **Step 2: Update all three files to match**

Update the count in:
1. Agent file line 20
2. CLAUDE.md (search for "99 registered command groups" or similar)
3. README.md lines 3 and 26

Use the same number everywhere. Format: "N command groups" (no "covering X commands" — that second number is hard to maintain).

- [ ] **Step 3: Update CLAUDE.md stale `docs/later/` description**

Change: "Parked: messaging, meetings, bots/webhooks (post-calling)"
To: "Parked: meetings, bots/webhooks (messaging commands now generated)"

- [ ] **Step 4: Commit**

```bash
git add .claude/agents/wxc-calling-builder.md CLAUDE.md README.md
git commit -m "fix: sync command group count across agent, CLAUDE.md, and README"
```

---

### Task 10: Add Compaction Recovery Notes to Skills

**Files:**
- Modify: `.claude/skills/provision-calling/SKILL.md`
- Modify: `.claude/skills/configure-features/SKILL.md`
- Modify: `.claude/skills/manage-call-settings/SKILL.md`
- Modify: `.claude/skills/wxc-calling-debug/SKILL.md`

**Context:** The agent has a COMPACTION RECOVERY section, but none of the 4 skills do. If context compacts while executing within a skill, the skill's state is lost.

- [ ] **Step 1: Add compaction note to each skill**

Add to the end of each skill file (before any trailing `---`):

```markdown
## Context Compaction

If context compacts mid-execution, recover by:
1. Read the deployment plan from `docs/plans/` to recover what was planned
2. Check what's already been created: run the relevant `list` commands
3. Resume from the first incomplete step
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/*/SKILL.md
git commit -m "fix: add compaction recovery notes to all 4 skills"
```

---

## Execution Order

Tasks 1-7 can be parallelized in groups:
- **Wave 1 (parallel):** Tasks 1, 3, 4, 5, 6 — each touches a different file
- **Wave 2 (parallel):** Tasks 2, 7 — agent structural fixes + README
- **Wave 3 (sequential):** Task 8 — requires reading wxcadm source
- **Wave 4 (sequential):** Task 9 — cross-file sync, must run after Tasks 1 and 7
- **Wave 5 (parallel):** Task 10 — compaction notes across all skills

## Out of Scope (Documented for Future)

These were identified in the review but are NOT part of this plan:

1. **Location-level call settings skill** — No skill covers internal dialing, voicemail policies, schedules, announcements, access codes, call recording, operating modes. Needs a new skill or expansion of manage-call-settings. (Separate plan needed.)
2. **Scope reference table deduplication** — 3 skills duplicate scope tables. Could consolidate into `docs/reference/authentication.md`. (Low priority.)
3. **person-call-settings-handling.md precedence order** — Incomplete (missing SimRing, SeqRing, SNR, Priority Alert). Needs live API testing to verify. (Blocked on verification.)
4. **Remaining NEEDS VERIFICATION tags** — Swept 2026-03-19: 136 tags across 39 docs resolved (122 verified, 27 corrected). Only 2 remain (bot calling scopes in authentication.md, rate limits in messaging-spaces.md — both need special tokens to test).
