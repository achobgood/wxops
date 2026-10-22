# Sequential Dialing (On-Call Connect) Playbook

<!-- ref-tag: sequential-dialing-v2 -->

## Overview

This playbook covers how to build sequential dialing flows in Webex Connect — looping through a list of phone numbers inside a Voice Node Group until one answers. This is the pattern for on-call routing, escalation chains, and find-me/follow-me.

**Key distinction from standard outbound voice:** Sequential dialing uses a **Call Patch node INSIDE the Voice Node Group** with an Evaluate-driven loop — NOT Call User nodes outside the VNG. The inbound caller stays connected to the VNG while each B-party attempt is made and released.

**Prerequisite:** Read `inbound-voice.md` for inbound call handling basics before starting here.

---

## 1. Pattern Overview

The sequential dialing pattern uses a **loop** inside a single Voice Node Group — one Evaluate node + one Call Patch node, with `onNoAnswer` looping back to the Evaluate:

```
Evaluate --"continue"--> Call Patch --onNoAnswer--> Evaluate (loop)
   |                        |
   +"failed"                +--onSuccess
   [fallback TTS]           [bridged]
```

The Evaluate node uses custom flow variables (`retryCount`, `oncall_number`, `maxRetryCount`) to track which number to try next. Each iteration increments `retryCount`, sets `oncall_number` to the next number in the list, and returns `"continue"`. When `retryCount` exceeds `maxRetryCount`, it returns `"failed"` to exit to fallback TTS.

> **Warning:** The pattern of re-entering a Call Patch node via `onNoAnswer` loop inside a single VNG is unverified in sandbox. See §8 Open Items before relying on this in production.

### Why This Works

1. The inbound call's VNG remains active throughout all attempts
2. Call Patch operates inside the VNG — A-party (caller) stays connected
3. Each failed attempt releases the B-party but keeps A-party in the VNG
4. The Evaluate sets `oncall_number` to the next number before each Call Patch attempt
5. Custom flow variables persist across loop iterations within a single flow execution

---

## 2. Call Patch Node Configuration

The **Call Patch** node bridges the active caller (A-party) with a new outbound party (B-party). It lives inside a Voice Node Group and is only available inside VNGs.

### Fields

> **Owner: `webex-connect-advanced.md` § Call Patch Node (Voice Node Group) → Configuration.** Reproduced here so this page works standalone; the reference doc wins on any disagreement.

| Field | Required | Notes |
|-------|----------|-------|
| **Destination (B-PARTY)** | Yes | Target number in E.164 format. Invalid format exits through `onError`. The only required field on the node. |
| **From Number** | No | Dropdown — the number used as the calling party for the outbound leg. Separate field from Display Number. |
| **Display Number** | No | Number shown to B-party. Selected from Assets > Numbers. Disabled by default. Requires account manager to enable. Not all carriers support this. |
| **Display Name** | No | Business name. 10-digit max — Cisco's literal wording, and the unit is Cisco's own ambiguity on a name field. Both Display Number and Display Name are disabled by default and require account manager enablement. [`webex-connect-advanced.md` § Call Patch Node (Voice Node Group) → Configuration, "Note — the Display Name limit"] |
| **Play audio to A-Party (calling party) while attempting the call patch** | No | When checked, enables audio source for A-party during ringing. Audio source configured via four tabs: Pre-recorded / Upload / URL / TTS (verify TTS availability in sandbox) — ⚠ **disputed, see the UNRESOLVED note below this table**. |
| **Play audio to B-Party (called party) before patching the call** | No | When checked, enables audio source for B-party announcement before bridge. Audio source configured via four tabs: Pre-recorded / Upload / URL / TTS — ⚠ **disputed, see the UNRESOLVED note below this table**. |
| **Loop audio until DTMF keypress** | No | Sub-field: **DTMF input from B-party**. Repeats B-party announcement in a loop until B-party presses a DTMF key or the looping threshold is reached. Exits `onNoAnswer` if threshold hit without DTMF. |
| **Looping Threshold (number of times)** | Conditional | Max loop iterations. Default: **10**. Required when DTMF looping is enabled. Misconfiguration risks prolonged line occupation. |
| **Transfer DTMFs after call patch** | No | Transfers DTMF inputs pressed after call patch by A-party to B-party and/or vice-versa. If announcement loop is enabled, DTMFs are transferred only after the loop has been exited. |
| **Record the call upon successfully patching both calls** | No | Saved to **Voice Recordings** page under Tools (not Voice Media library). Filename uses prefix + NodeTID. Label is Cisco's exact wording [source: https://help.webexconnect.io/docs/call-patch-node § Node Configuration — verified 2026-07-25]. |

> ⚠ **UNRESOLVED — do not "correct" the two audio-source rows above.** Whether ticking "Play audio to A-Party" / "Play audio to B-Party" reveals **four source tabs — Pre-recorded / Upload / URL / TTS** (as written above) or a **single-file dropdown** — a "Jingle File" / "Announcement File" picker from the Voice Media library, as written in `inbound-voice.md` § 6 — is an open conflict. Two vetting passes run on the same day against the same Cisco page reached opposite conclusions, and this playbook's own source finding hedges the A-party case: the four-tab component was read off a **screenshot**, and whether the A-party jingle supports TTS is filed as not verifiable. Both readings are stated side by side, with their evidence, at [`webex-connect-advanced.md` § Call Patch Node (Voice Node Group) → "⚠ UNRESOLVED — Call Patch audio source"]. Check your own tenant's Call Patch node before building against either. What is **not** in dispute: both checkboxes exist, both are optional, and each gates the audio played to its own party.

### Exit Paths

> **Owner: `webex-connect-advanced.md` § Call Patch Node (Voice Node Group) → Exit Paths.** Reproduced here so this page works standalone; the reference doc wins on any disagreement.

| Edge | Color | When | Route To |
|------|-------|------|----------|
| `onSuccess` | Green | Call patched (bridged) | Parties are bridged. Whether the flow pauses until B-party disconnects is unverified — see §8 Open Items. |
| `onNoAnswer` | Yellow | B-party doesn't answer, or DTMF loop threshold exceeded | Next Call Patch or fallback |
| `onError` | Red | Patch fails (invalid E.164, network issue) | Fallback TTS |

### Output Variables

> **Owner: `webex-connect-advanced.md` § Call Patch Node (Voice Node Group) → Output Variables.** Reproduced here so this page works standalone; the reference doc wins on any disagreement.

| Variable | Description |
|----------|-------------|
| `patch.APartyNumber` | Originating party (caller) number |
| `patch.BPartyNumber` | Destination party number |

**CRITICAL:** There is NO explicit ring timeout field on Call Patch. The `onNoAnswer` edge fires based on carrier behavior (typically 30-45 seconds — **not confirmed in official docs**; both of this project's vetting passes filed the figure as unverifiable). The DTMF looping threshold is the closest thing to a configurable timeout — see Section 3. [`webex-connect-advanced.md` § Call Patch Node (Voice Node Group) → Exit Paths]

---

## 3. Timeout Tuning

### Recommended: DTMF Looping Threshold as Timeout

Enable "Loop audio until DTMF keypress" with a short announcement and a low threshold. The B-party announcement repeats until the threshold is hit, then `onNoAnswer` fires.

**Example:** 5-second announcement with threshold 3 = ~15 seconds before `onNoAnswer` fires.

This gives you indirect control over per-attempt duration without relying on carrier-default ring timeouts.

### Timing Budget (With DTMF Threshold)

| Phase | Duration (est.) | Running Total |
|-------|-----------------|---------------|
| TTS greeting | ~5s | 5s |
| HTTP GET (People API) | ~1-2s | 7s |
| Evaluate (CSV parse) | <1s | 7s |
| Call Patch attempt 1 (~15-20s) | ~15-20s | 22-27s |
| Inter-attempt Play | ~3s | 25-30s |
| Call Patch attempt 2 (~15-20s) | ~15-20s | 40-50s |
| Inter-attempt Play | ~3s | 43-53s |
| Call Patch attempt 3 (~15-20s) | ~15-20s | 58-73s |
| Fallback TTS | ~5s | 63-78s |

Total worst case: ~63-78 seconds. Acceptable for an inbound caller on hold.

### Alternative: Carrier Default (No DTMF Threshold)

Without DTMF looping, each attempt takes 30-45 seconds (carrier-controlled). Three attempts = 90-135 seconds total. Recommend max 2 attempts without DTMF threshold to avoid caller abandonment.

⚠ **The 30-45 second figure is an estimate, not a documented value** — there is no ring-timeout field on Call Patch and no Cisco source for a specific duration [`webex-connect-advanced.md` § Call Patch Node (Voice Node Group) → Exit Paths]. Treat the budget above as a planning starting point and measure it in your own tenant before committing to a number of attempts.

**Note:** Non-agent flows have no 30-second timeout. The 30-second limit applies only to AI Agent action flows. Sequential dialing flows triggered by inbound calls are not subject to this constraint.

**Note:** The DTMF threshold as timeout is a recommended approach but should be verified in sandbox before relying on it. Test that `onNoAnswer` fires as expected when the loop threshold is hit without a DTMF keypress.

---

## 4. Looping with retryCount

### Custom Flow Variables

Create these in **Flow Settings > Custom Variables** before building the loop, or from the Input Variables panel of any node using "+ Add New Custom Variable":

| Variable | Init Value | Purpose |
|----------|-----------|---------|
| `retryCount` | `0` | Tracks which attempt we're on |
| `maxRetryCount` | `2` | Zero-indexed max (2 = three attempts: 0, 1, 2) |
| `oncall_number` | *(empty)* | Set by Evaluate to the current target number |

### Wiring Pattern

1. Wire Evaluate `"continue"` branch → Call Patch (destination: `$(oncall_number)`)
2. Wire Call Patch `onNoAnswer` → Play ("Trying next number...") → Evaluate (loop back)
3. Wire Call Patch `onSuccess` → post-bridge handling (Play goodbye → End)
4. Wire Call Patch `onError` → fallback TTS → End
5. Wire Evaluate `"failed"` branch → fallback TTS → End

**Note:** All nodes in this loop (Evaluate, Call Patch, and any Play nodes between them) must be inside the Voice Node Group. Any node outside the VNG connected to a VNG edge will terminate the call.

### Evaluate Script

```javascript
var csv = "$(n4.oncall_csv)";
var numbers = csv.split(",");

if (Number(retryCount) <= Number(maxRetryCount)) {
    if (Number(retryCount) === 0) {
        oncall_number = numbers[0] ? numbers[0].trim() : "";
    }
    if (Number(retryCount) === 1) {
        oncall_number = numbers[1] ? numbers[1].trim() : "";
    }
    if (Number(retryCount) === 2) {
        oncall_number = numbers[2] ? numbers[2].trim() : "";
    }
    retryCount = Number(retryCount) + 1;
    "continue";
} else {
    "failed";
}
```

> **Warning — variable syntax:** Official docs show custom flow variables accessed as `$(varName)` (e.g., `$(retryCount)`) in Evaluate scripts. The bare-name syntax above (`retryCount`, `oncall_number`) is unverified and may not work. Writing back to variables via assignment (e.g., `retryCount = ...`) is not documented. Verify in sandbox before relying on this script.

**Configure Script Output (per branch):** Each branch is added separately via **+ Add New**. For each branch, two fields must be filled:
- **Configure Script output:** the value the script returns (e.g., `continue`)
- **Branch Name:** the label for the exit edge (e.g., `continue`)

| Configure Script output | Branch Name |
|------------------------|-------------|
| `continue` | `continue` |
| `failed` | `failed` |

The script assigns `oncall_number` (a custom flow variable) to the next number in the CSV, increments `retryCount`, and returns `"continue"` as its last expression (unverified — return-by-last-expression behavior is not documented). The Call Patch node reads `$(oncall_number)` — no node prefix needed for custom flow variables.

When `retryCount` exceeds `maxRetryCount`, the script returns `"failed"`, routing to the fallback branch.

**Custom variable prerequisite:** Per official docs, a custom variable **must** be referenced in at least one preceding node (Configuration tab or Transition Actions tab) before the Evaluate node — this is mandatory, not optional. If you create `retryCount` and `oncall_number` in Flow Settings without referencing them in a preceding node, the variables will not populate during execution. Use a Transition Action on a preceding node (e.g., the HTTP Request node's On-leave) to set initial values.

### Maximum Practical Length

Three attempts is the recommended maximum. The limit is caller patience, not platform constraints. To add more attempts, increase `maxRetryCount` and add more `if` blocks for higher `retryCount` values.

### Inter-Attempt Status Messages

Place a Play node between the Call Patch `onNoAnswer` edge and the Evaluate loop-back to keep the caller informed:

- "That number is not available. Trying the next technician..."

After the Evaluate returns `"failed"`: "We were unable to reach anyone on call. Please try again later or leave a message after the beep."

**Note:** Whether Play nodes execute mid-VNG between Call Patch attempts should be verified in sandbox testing. The expected behavior is that they do, but this is untested.

---

## 5. Dynamic Number Sourcing

Fetch the on-call roster mid-call using an HTTP Request node before the Evaluate loop.

### Example: Webex People API

```
GET https://webexapis.com/v1/people?displayName={on-call-group-name}
Authorization: Bearer {bot_token}
```

This uses the People API `title` field as a lightweight store for a CSV of phone numbers. The `displayName` query parameter finds the on-call group user record. The HTTP node's output (e.g., `$(n4.oncall_csv)`) feeds the Evaluate script.

### How the Evaluate Uses the CSV

The Evaluate script reads the CSV from the HTTP node output using `$(nX.variableName)` syntax, splits it into an array, and uses `retryCount` to index into the right number each iteration. See Section 4 for the full script.

The key difference from what you might expect: the Evaluate does NOT produce multiple named output variables (like `phone1`, `phone2`, `phone3`). Instead, it sets a single custom flow variable `oncall_number` to the current target, and the Call Patch reads `$(oncall_number)`.

**Note:** The People API title field is a lightweight hack for demo purposes. Production deployments should use a proper on-call roster API (PagerDuty, OpsGenie, etc.) and replace the HTTP Request endpoint accordingly.

---

## 6. Caller Experience

What the caller hears during each phase of a sequential dialing flow:

| Phase | What Caller Hears |
|-------|-------------------|
| Initial greeting | "Thank you for calling. Please hold while we connect you to the on-call technician." |
| During ringing (attempt active) | Jingle audio (if configured) or silence |
| Between attempts | "Trying the next available technician..." |
| On successful bridge | Silence — parties are connected, bidirectional audio |
| After B-party hangs up | "The other party has disconnected. Goodbye." |
| All attempts fail | "We were unable to reach anyone. Please try again later or leave a message after the beep." |

**Note:** Post-bridge behavior (what happens after B-party hangs up) should be verified in sandbox. The expected behavior is that the flow continues from the `onSuccess` edge to the next node after the bridge ends.

---

## 7. Complete On-Call Connect Example

### Custom Flow Variables

Create these in **Flow Settings > Custom Variables** before building:

| Variable | Init Value |
|----------|-----------|
| `retryCount` | `0` |
| `maxRetryCount` | `2` |
| `oncall_number` | *(empty)* |

### Flow Diagram

```
PSTN Caller dials Connect voice number
  |
  v
Start (Voice > Inbound Call)
  |
  v
Voice Node Group [inbound call is active]
  |
  |--- Play (TTS: "Thank you for calling. Please hold while we connect you
  |          to the on-call technician.")
  |       |
  |       v
  |   HTTP Request (GET Webex People API — fetch on-call CSV from title field)
  |       |
  |       v
  |   Evaluate (check retryCount, set oncall_number, increment retryCount)
  |       |
  |       +-- "continue" --> Call Patch (dial $(oncall_number))
  |       |                      |
  |       |                      +-- onSuccess --> [call bridged — flow pauses]
  |       |                      |                    |
  |       |                      |                    v
  |       |                      |                 [B-party hangs up] --> Play ("Goodbye") --> End
  |       |                      |
  |       |                      +-- onNoAnswer --> Play ("Trying next number...") -->
  |       |                      |                  Evaluate (loop back — retryCount incremented)
  |       |                      |
  |       |                      +-- onError --> Play (fallback TTS) --> End
  |       |
  |       +-- "failed" --> Play ("We were unable to reach anyone on call.
  |                         Please try again later.") --> End
```

### Node-by-Node Configuration

| Node | Type | Key Settings |
|------|------|-------------|
| n1 | Start | Voice > Inbound Call trigger |
| n2 | Play | TTS greeting: "Thank you for calling. Please hold while we connect you to the on-call technician." TTS processor: Azure, Voice Type: Neural (must be selected manually — not pre-selected by default), language: en-US |
| n3 | HTTP Request | GET `https://webexapis.com/v1/people?displayName={group}`, Header: `Authorization: Bearer {bot_token}`. Output: `oncall_csv` from response `title` field |
| n4 | Evaluate | Script: parse CSV, set `oncall_number`, increment `retryCount`, return `"continue"` or `"failed"`. Add two branches via **+ Add New**: (1) Configure Script output: `continue`, Branch Name: `continue`; (2) Configure Script output: `failed`, Branch Name: `failed` |
| n5 | Call Patch | Destination: `$(oncall_number)`, Jingle: enabled, DTMF loop threshold: 3 |
| n6 | Play | "That number is not available. Trying the next technician..." (between `onNoAnswer` and Evaluate loop-back) |
| n7 | Play | Fallback: "We were unable to reach anyone on call. Please try again later or leave a message after the beep." (wired from Evaluate `"failed"` branch and Call Patch `onError`) |

---

## 8. Testing

### Sandbox Setup

- Two-way voice is available in **USA, Canada, UK only**
- Register test phone numbers first (max 5 per account, same country)
- Need at least two registered numbers: one for caller, one for B-party

### Test Cases

| # | Test | Steps | Expected Result |
|---|------|-------|-----------------|
| 1 | onNoAnswer path | Set all targets to non-answering numbers | Chain advances through all Call Patch nodes, fallback TTS plays |
| 2 | onSuccess path | Set first target to a number you control, answer it | Bridge established, bidirectional audio confirmed |
| 3 | Mid-chain answer | Set first target to non-answering, second to answering | First attempt times out, second attempt bridges |
| 4 | All-fail path | Set all targets to non-answering numbers | All attempts exhaust, fallback TTS plays, call ends |
| 5 | HTTP failure | Break the API endpoint URL | HTTP `onError` fires, graceful fallback TTS plays |
| 6 | Invalid E.164 | Set a target to malformed number (missing +) | Call Patch `onError` fires, fallback TTS plays |

### Debugging

Use **Flow Debug** for node-by-node execution trace. Check each Call Patch node's exit path to confirm the expected edge fired.

### Open Items to Verify in Sandbox

These behaviors are expected but not yet confirmed with live testing:

- **Call Patch post-bridge behavior:** Does the flow continue from `onSuccess` after B-party hangs up?
- **Multiple Call Patch chaining:** Can multiple Call Patch nodes chain inside a single VNG?
- **DTMF looping threshold as timeout:** Does `onNoAnswer` fire when the threshold is hit without a DTMF keypress?
- **Play node mid-VNG:** Does TTS play between Call Patch attempts while the VNG is active?

---

## 9. Known Gotchas

| Issue | Fix |
|-------|-----|
| Call Patch dials but caller doesn't hear ringback | Configure Jingle Audio in the Call Patch node |
| B-party answers but no audio bridge | Check DTMF relay and codec settings on Call Patch |
| All attempts fail even though a number should answer | Timeout too short — increase DTMF looping threshold or accept carrier-default timing |
| Caller dropped before all attempts complete | Total attempt time exceeds carrier or flow timeout — reduce attempts or timeout per attempt |
| Variable arrives empty in Call Patch destination | Used manual typing instead of variable picker — use the picker |
| Call Patch node not available in palette | Ensure you're working inside a Voice Node Group — Call Patch is only available inside VNGs (documented as permitted inside VNGs; exclusive restriction is not explicitly stated in official docs) |
| HTTP Request fails mid-call | The call remains active — wire HTTP `onError` to a fallback Play node |
| CSV parsing returns empty phone variables | Malformed CSV (trailing commas, spaces, non-E.164) — validate and clean in Evaluate node |

---

## Managing the On-Call Number List (IVR Self-Service)

This playbook covers the **call routing** side — dialing through a list of numbers. The companion pattern is **how supervisors update that list at runtime** without accessing Control Hub.

The pattern: a separate IVR flow lets authorized users call in with a PIN and update the Global Variable containing the on-call number list. This eliminates the need for admin portal access to change on-call rotations.

**Two community-built Flow Designer JSONs for this pattern:**

| Flow | Purpose |
|------|---------|
| `CC_OnCall_Changer_GlobalVariable.json` | Update on-call telephone number via IVR with departmental PIN auth |
| `CC_Status_Changer_GlobalVariable.json` | Open/close the contact center manually via IVR with PIN auth |

Source: [TeamCCEP On Call Status Changer](https://teamccep.github.io/pages/OnCallStatus/)

The approach uses Collect Digits (for PIN) → Condition (verify PIN) → Set Variable (update Global Variable) → Play Message (confirm change). The Global Variable update persists immediately and is read by the routing flow on the next inbound call.

---

## References

- [Call Patch Node](https://help.webexconnect.io/docs/call-patch-node)
- [Voice Node Group](https://help.webexconnect.io/docs/voice-node-group)
- [Play Node](https://help.webexconnect.io/docs/play-node)
- [Collect Input Node](https://help.webexconnect.io/docs/collect-input)
- [Phone Numbers](https://help.webexconnect.io/docs/phone-numbers)
- [Sandbox Voice](https://help.webexconnect.io/docs/making-and-receiving-voice-calls-using-sandbox)
- [Webex People API](https://developer.webex.com/docs/api/v1/people)
