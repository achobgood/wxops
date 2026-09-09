# Execution Report: [OBJECTIVE_SUMMARY]

Executed: [YYYY-MM-DD HH:MM] ET
Agent: wxc-calling-builder
Plan: [link or reference to deployment-plan.md used]

---

## 1. Summary

| Field | Value |
|-------|-------|
| Requested | [What the user asked for] |
| Executed | [What was actually done — may differ if partial failure] |
| Overall Status | **SUCCESS** / **PARTIAL** / **FAILED** |
| Steps Completed | [N] of [M] |
| Duration | [estimated wall-clock time] |

## 2. Results

Step-by-step outcome for every wxcli command in the deployment plan.

| Step | Operation | Command | Status | Resource ID | Notes |
|------|-----------|---------|--------|------------|-------|
| 1 | [e.g., Create user Jane Smith] | `wxcli people create --json-body '{"emails":["jane@example.com"],"firstName":"Jane","lastName":"Smith"}'` | SUCCESS | `Y2lzY29...` | Created in Austin location |
| 2 | [e.g., Assign Calling license] | `wxcli licenses update --json-body '...'` | SUCCESS | `license_id` | Professional license applied |
| 3 | [e.g., Assign phone number to Jane Smith] | `wxcli user-settings update-numbers Y2lzY29... --json-body '{"phoneNumbers":[{"primary":true,"action":"ADD","directNumber":"+15125550101"}]}'` | FAILED | -- | Error: +15125550101 is not in the Austin location pool (see Errors) |
| 4 | [e.g., Configure voicemail] | `wxcli user-settings update-voicemail Y2lzY29... --enabled --verify` | SUCCESS | -- | Independent of Step 3 |
| 5 | [e.g., Configure call forwarding] | `wxcli user-settings update-call-forwarding Y2lzY29... --json-body '...' --verify` | SUCCESS | -- | Server normalized the destination — see Verification |

**Legend:** SUCCESS = completed as planned. FAILED = attempted, returned error. SKIPPED = not attempted due to dependency failure.

## 3. Resources Created/Modified

Final state of every resource touched during execution. Use this as the source of truth for what now exists.

| Resource Type | Name | ID | Status | Notes |
|--------------|------|-----|--------|-------|
| Person | Jane Smith | `Y2lzY29...` | Active | Calling license assigned |
| Phone Number | +1 (512) 555-0101 | `num_id` | Not assigned | Step 3 failed — number is not in the Austin location pool |
| [etc.] | | | | |

## 4. Errors

Details on every failure encountered. Empty section if all steps succeeded.

| Step | Operation | Error Code | Error Message | Resolution |
|------|-----------|-----------|--------------|------------|
| 3 | Assign phone number | `404` | `Number not found in location pool` | Need to add numbers to Austin location first |
| [etc.] | | | | |

**Rollback performed:** [Yes — describe what was rolled back / No — partial success retained / N/A — no failures]

## 5. Verification

Confirmation checks the agent ran after execution to validate the deployment. Every row
names a real command that was run and what it returned. A 2xx from the write itself is
**not** verification — it means the request was accepted, not that the setting was applied.

Two kinds of evidence belong here:

- **`--verify` on the write** — available on update commands that have a same-path GET.
  It re-reads the resource after the write and reports any field you *sent* that did not
  take, printing either `Verified: re-read <url> and all N sent field(s) match.` or one
  `<field>: sent X, now Y` line per mismatch. It never changes the exit code, so record
  what it printed, not whether the command exited 0.
- **Read-back** — for creates, deletes, and anything with no `--verify` flag, re-read the
  resource with the matching `show` / `list` command and compare against the plan.

| Check | Command | Result |
|-------|---------|--------|
| User exists and is Calling-enabled | `wxcli people show Y2lzY29... --calling-data true -o json --fields '{ext:extension,loc:locationId}'` | PASS — Austin location; no extension yet (Step 3 failed) |
| Phone number assigned to the user | `wxcli numbers list --location-id Y2lzY29... --phone-number "+15125550101" --all -o json` | FAIL — no matching number in the location, confirming Step 3 did not complete |
| Voicemail enabled | `wxcli user-settings update-voicemail Y2lzY29... --enabled --verify` (Step 4) | PASS — `Verified: ... all 1 sent field(s) match.` |
| Call forwarding busy destination | `wxcli user-settings update-call-forwarding Y2lzY29... --json-body '{"callForwarding":{"busy":{"enabled":true,"destination":"5125554000"}}}' --verify` (Step 5) | PASS — `callForwarding: sent {...'destination': '5125554000'...}, now {...'destination': '+15125554000'...}`; server normalized to E.164 and filled defaults, accepted |
| [Additional checks] | | |

**Reading these results:**
- `--verify` compares **only the fields you sent** — a clean `Verified:` line says nothing
  about fields you did not touch.
- It compares **top-level request-body keys**. A nested body (`callForwarding`, `agents`)
  is reported as one line holding the whole object; read the values inside it rather than
  expecting a per-leaf diff.
- A `sent X, now Y` line is not automatically a failure. Servers legitimately normalize
  values (E.164 rewriting, case folding, defaults filled in). Record the difference and
  state whether you judged it acceptable — do not report it as PASS silently.
- On any `list`-based check that answers *how many* / *which ones* / *are there any*, pass
  `--all`. A single fetch returns page one and will under-count.

## 6. Next Steps

What should happen after this deployment. Items marked with a person icon require manual action.

| # | Action | Owner | Notes |
|---|--------|-------|-------|
| 1 | [e.g., Test inbound call to +1 (512) 555-0101] | User | Verify ring and voicemail |
| 2 | [e.g., Configure receptionist client] | Agent | Run as follow-up deployment |
| 3 | [e.g., Retry failed number assignment] | Agent | Needs numbers added to pool first |
| 4 | [e.g., Share credentials with end users] | User | Portal access for self-service |
