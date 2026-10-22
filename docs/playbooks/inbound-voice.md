# Inbound Voice Playbook

<!-- ref-tag: inbound-voice-v4 -->

## Overview

This playbook covers how to handle inbound voice calls in Webex Connect — specifically, flows triggered when a PSTN caller dials a Connect-provisioned voice number. This is the pattern for IVR menus, caller lookup, and inbound call routing.

**Key distinction from outbound voice flows:** Inbound flows use the **Start node** (Inbound Call trigger) instead of a webhook. There is no Call User node — the call already exists. The Voice Node Group auto-creates from the inbound call trigger, not from a Call User node.

For outbound voice handling, see `outbound-voice.md`.

### Inbound vs. Outbound Comparison

| Aspect | Outbound Voice | Inbound Voice |
|--------|---------------|---------------|
| **Start trigger** | Webhook (external event) | Inbound Call (PSTN ring) |
| **Call initiation** | Call User node (outside VNG) | No Call User — call already exists |
| **Voice Node Group** | Auto-created by Call User node | Auto-created by inbound call trigger |
| **Caller context** | Webhook payload (order_id, phone, etc.) | ANI (caller ID), DNIS (dialed number), timestamp |
| **Use case** | Proactive notifications | Reactive call handling |

---

## 1. Start Node (Inbound Call Trigger)

The **Start node** must be configured with trigger type **Inbound Call**. This fires when a caller dials the voice number assigned to the flow.

### Configuration

| Field | Details |
|-------|---------|
| **Trigger Type** | Inbound Call |
| **Voice Number** | Select from dropdown of provisioned inbound-capable numbers |

**One trigger per flow.** Each flow has exactly one Start node. To handle multiple voice numbers, create separate flows or use a single number with Branch logic downstream.

### Output Variables

Variables are shown in expression syntax as used inside flow nodes (e.g., `$(n1.voice.msisdn)`). Official docs list bare field names without the wrapper.

| Variable | Description |
|----------|-------------|
| `$(n1.voice.msisdn)` | Caller's phone number (ANI) |
| `$(n1.voice.serviceNumber)` | Dialed number (the Connect voice number) |
| `$(n1.voice.timestamp)` | Call arrival timestamp (Unix epoch) |
| `$(n1.voice.transId)` | Unique transaction ID |
| `$(n1.voice.offeredOn)` | Call initiation timestamp |
| `$(n1.voice.callType)` | `"IBD"` for inbound (documented for Receive Node missed-call events; unverified for live answered inbound Start trigger) |
| `$(n1.voice.releasedOn)` | Call end timestamp (documented for Receive Node; availability on live inbound Start trigger is unverified) |

---

## 2. Voice Node Group (Inbound)

The **Voice Node Group** auto-creates from the inbound call trigger. Do NOT add a Call User node — doing so creates a second VNG and causes confusion.

### Key Rules

> **Owner: `webex-connect-advanced.md` § Voice Nodes (Voice Node Group) → Voice Node Group Rules.** Reproduced here so this page works standalone; the reference doc wins on any disagreement.

- Up to **1,000 Voice Node Groups** per flow
- Cannot be deleted once created
- **Wait for** and **Delay** nodes are NOT supported inside the group
- Call terminates immediately when any internal node connects to VNG edges (exits the group)
- AMD configurable in VNG settings

### Voice-Specific Nodes (Inside Group)

| Node | Purpose |
|------|---------|
| **Play** | Play TTS or audio to the caller |
| **Record** | Record caller audio |
| **Collect Input** | Capture DTMF or speech input |
| **IVR Menu** | Multi-option menu with branching |
| **Call Patch** | Bridge caller with another number |
| **Call Transfer** | Blind or warm transfer to another number |

### General-Purpose Nodes (Inside Group)

These non-voice nodes can run inside the group while the call is active:

Evaluate, Branch, HTTP Request, Data Parser, Data Transform, Profile, SMS, WhatsApp, Email, Apple Messages for Business, Messenger, RCS, Generate OTP, Validate OTP, Encryption, Decryption

### Nodes That Must Be OUTSIDE the VNG

- **Start node** — always first, always outside
- **Call User node** — *"This node cannot exist within the Voice Node Group"* — not permitted inside, not merely unnecessary for inbound [`webex-connect-advanced.md` § Voice Nodes (Voice Node Group) → Nodes That Must Be OUTSIDE the Group]

### Flow Termination — Disconnect Node

*"Every voice flow must start with a Start node and end with a **Disconnect** node."* [source: https://help.webexconnect.io/docs/flows-introduction — quote re-verified against the live page 2026-07-25; the same rule is recorded in `webex-connect.md` § Voice flows must end with Disconnect]

The same page also states *"Every node outcome must either be mapped to the next node or terminate onto an End node"* [source: https://help.webexconnect.io/docs/flows-introduction — verified 2026-07-25], which is why every outcome listed in the node tables in Sections 3–6 (including each `onError`) needs a wired destination, and why every branch in the Section 8 examples terminates on `End`.

The Disconnect node *"allows you to record the logs and report when a call is terminated in a voice flow"*, and it exists to make edge wiring tractable in large voice flows — *"Here the action of connecting to node group edge will disconnect the call."* Its configuration groups are **Disconnect Settings** (Disconnect Code, Disconnect Reason), **Play Options** (Type, Session Variables, Offset, Duration, User Assets), **Properties** (Label), and **Params** (Session Data) [source: https://help.webexconnect.io/docs/voice-disconnect].

⚠ **Open question — do not treat as settled.** The `flows-introduction` rule above is stated for voice flows generally, but the node page it links to is titled **"Voice: Disconnect (deprecated)"** and carries the notice *"The older version of voice nodes are deprecated. If you are using an older version and wish to switch to the newer version, contact Customer Support."* [source: https://help.webexconnect.io/docs/voice-disconnect — verified 2026-07-25]. Whether a tenant on the current voice-node version terminates with this same node, or with a replacement node, is **not established by either page**. Confirm against your tenant's node palette before building. The examples in Section 8 therefore show a generic terminal `End` rather than asserting a node name.

---

## 3. Play Node (TTS Greeting)

The **Play node** lives inside the Voice Node Group and plays audio or TTS to the caller. For inbound flows, this is typically a greeting or informational message.

For full TTS configuration details (Azure Neural voices, SSML tags, variable insertion, audio alternatives), see `outbound-voice.md` Section 4 and Section 5.

**Note:** The Play node has no barge-in capability. "Interrupt audio on user input" is a Collect Input node option only — it does not apply to Play.

### Inbound Greeting Patterns

**Plain Text:**
```
Thank you for calling Contoso Property Management. How can we help you today?
```

**SSML:**
```xml
<speak>
  Thank you for calling Contoso Property Management.
  <break time="300ms"/>
  Please listen carefully as our menu options have changed.
</speak>
```

**Dynamic greeting with caller lookup:**
```
Hello $(n3.first_name). Thank you for calling. Your account balance is $(n3.balance).
```

### Play Node Outcomes

> **Owner: `webex-connect-advanced.md` § Play Node (Voice Node Group) → Exit Paths.** Reproduced here so this page works standalone; the reference doc wins on any disagreement.

| Outcome | When |
|---------|------|
| `onSuccess` | Audio plays without errors |
| `onError` | Playback encounters issues |

---

## 4. Collect Input Node (DTMF / Speech)

The **Collect Input** node captures caller input via DTMF keypress or speech recognition. Use it for IVR menus, account number entry, or speech-driven routing.

### DTMF Configuration

| Field | Details |
|-------|---------|
| **Input Size** | Maximum characters expected (e.g., `1` for menu selection, `10` for account number) |
| **Termination Character** | Character that ends input early. Options: `None` or `Any character`. Set to `None` when collecting a fixed number of digits. |
| **Input Timeout** | Seconds to wait for input before triggering `oninputTimeout` |
| **Interrupt audio on user input** | Toggle. When enabled, caller input interrupts any playing audio. |

### Speech Configuration

| Field | Details |
|-------|---------|
| **Input Timeout** | Seconds to wait for speech before triggering `oninputTimeout` |
| **Silence Timeout** | Seconds of silence after speech starts before input is finalized |
| **Engine** | Speech recognition engine |
| **Language** | Recognition language (ISO code) |
| **Enable Recording** | Optional. Records the speech input for review. |

**Note:** Speech input has pricing implications — contact your account manager to discuss commercials before enabling.

### Output Variable

| Variable | Description |
|----------|-------------|
| `$(nX.collect.input)` | The collected input (DTMF digits or speech transcription) |

### Exit Paths

| Event | When |
|-------|------|
| `onSuccess` (green) | Input collected successfully |
| `oninputTimeout` (orange) | Caller did not provide input within the timeout period |
| `onFailure` (yellow) | Input collection failed (e.g., invalid input) |
| `onError` (red) | Collection failed (e.g., configuration error) |

---

## 5. HTTP Request (Mid-Call Data Fetch)

The **HTTP Request** node runs inside the Voice Node Group while the call is active. Use it to look up caller information, query a database, or call an external API mid-call.

### Common Inbound Use Case: Caller Lookup by ANI

| Field | Value |
|-------|-------|
| **Method** | GET |
| **URL** | `https://your-api.example.com/customers?phone=$(n1.voice.msisdn)` |
| **Headers** | Authorization, Content-Type as needed |

The caller's ANI (`$(n1.voice.msisdn)`) is available from the Start node and can be passed directly into the HTTP Request URL or body.

### Configuration

Same as standard HTTP Request nodes — Method, URL, Headers, Body, Timeout. See the platform HTTP Request documentation for full field reference.

### Exit Paths

> **Owner: `webex-connect-advanced.md` § Error Handling on HTTP Request Nodes → Exit Paths.** Reproduced here so this page works standalone; the reference doc wins on any disagreement.

The HTTP Request node has **three** exit edges, not two:

| Event | When |
|-------|------|
| `onSuccess` (green) | HTTP response received (any status code, including 4xx/5xx) |
| `onError` (red) | Request could not be processed — connection failure, invalid input, internal error |
| `onTimeout` (orange) | No response within the configured timeout |

⚠ **`onTimeout` is a real third edge and is easy to miss.** This section listed only `onSuccess` and `onError` until 2026-07-27, and folded timeouts into `onError` — they are separate edges. An unwired `onTimeout` is an unhandled path in a live call [`docs/tests/findings/inbound-sms-findings.md` row 11, severity **Error**, source https://help.webexconnect.io/docs/http-request-node; same finding recorded as M4 in `docs/plans/2026-07-25-webex-connect-doc-audit.md`]. Wire all three — Cisco requires every node outcome to be mapped or terminated on an End node (see Section 2 § Flow Termination).

Parse the response status code in a downstream Branch node to handle 200 vs. 404 vs. error cases — a `404` or `500` exits through `onSuccess`, because the request itself completed.

---

## 6. Call Patch Node

The **Call Patch** node bridges the inbound caller (A-party) with a dialed B-party, creating a two-party conversation. It lives INSIDE the Voice Node Group (unlike Call User, which sits outside).

### Configuration Fields

> **Owner: `webex-connect-advanced.md` § Call Patch Node (Voice Node Group) → Configuration.** Reproduced here so this page works standalone; the reference doc wins on any disagreement.

| Field | Required | Notes |
|-------|----------|-------|
| **Destination (B-PARTY)** | Yes | E.164 format. Invalid format exits through `onError`. The only required field on the node. |
| **From Number** | No | Dropdown — "Select a number". The calling party for the outbound leg. **A separate field from Display Number** — setting one does not set the other [`webex-connect-advanced.md` § Call Patch Node (Voice Node Group) → Configuration]. |
| **Display Number** | No | From Assets > Numbers. Not all carriers support. Disabled by default — **Display Number and Display Name are enabled together** by your account manager. |
| **Display Name** | No | 10-digit max — Cisco's literal wording, and the unit is Cisco's own ambiguity on a name field. Disabled by default. [`webex-connect-advanced.md` § Call Patch Node (Voice Node Group) → Configuration, "Note — the Display Name limit"] |
| **Play audio to the A party (calling party) while attempting the call patch** | No | Activates Jingle File dropdown — ⚠ **disputed, see the UNRESOLVED note below this table** |
| **Jingle File** | No | Pre-uploaded audio from Voice Media library — ⚠ **disputed, see the UNRESOLVED note below this table** |
| **Play audio to the B party (calling party) before patching the call** | No | Activates Announcement File dropdown — ⚠ **disputed, see the UNRESOLVED note below this table** |
| **Announcement File** | No | Pre-uploaded audio file — ⚠ **disputed, see the UNRESOLVED note below this table** |
| **Loop audio until DTMF keypress** | No | Repeats announcement. Exits `onNoAnswer` if threshold hit without DTMF. |
| **Looping Threshold** | Conditional | Max loop iterations. **Default: 10** [`webex-connect-advanced.md` § Call Patch Node (Voice Node Group) → Configuration]. Required when looping is enabled. Misconfiguration risks prolonged line occupation. |
| **Transfer DTMFs after call patch** | No | Passes A-party DTMF to B-party post-bridge |
| **Record the call upon successfully patching both calls** | No | Recordings are saved to the **Voice Recordings** page under **Tools** — *not* the Voice Media library, which holds audio prompt files only. Filename uses the configured prefix + NodeTID [`webex-connect-advanced.md` § Call Patch Node (Voice Node Group) → Configuration; § Record Node (Voice Node Group)]. |

> ⚠ **UNRESOLVED — do not "correct" the four Jingle / Announcement rows above.** Whether ticking "Play audio to A party" / "Play audio to B party" reveals a **single-file dropdown** (as written above) or **four source tabs — Pre-recorded / Upload / URL / TTS** (as written in `sequential-dialing.md` § 2) is an open conflict. Two vetting passes run on the same day against the same Cisco page reached opposite conclusions, and the remediation backlog carries it as open, blocked on "Conflicting accounts". Both readings are stated side by side, with their evidence, at [`webex-connect-advanced.md` § Call Patch Node (Voice Node Group) → "⚠ UNRESOLVED — Call Patch audio source"]. Check your own tenant's Call Patch node before building against either. What is **not** in dispute: both checkboxes exist, both are optional, and each gates the audio played to its own party.

**IMPORTANT:** There is no explicit ring timeout field on the Call Patch node. `onNoAnswer` fires based on carrier behavior. The commonly cited range of 30-45 seconds is unverified; no official documentation confirms a specific timeout value [`webex-connect-advanced.md` § Call Patch Node (Voice Node Group) → Exit Paths]. The closest thing to a configurable per-attempt timeout is the announcement loop threshold — `sequential-dialing.md` § 3 covers how to size it.

**Resolved — recording checkbox label.** Three spellings of this one field label were previously live across our docs and Cisco's. The label above is now Cisco's exact wording, *"Record the call upon successfully patching both calls"* [source: https://help.webexconnect.io/docs/call-patch-node § Node Configuration — re-verified 2026-07-25]. The two superseded variants were *"Record the call after successful patching"* (`webex-connect-advanced.md` § Call Patch Node and `sequential-dialing.md` § 2) and *"Record the call upon successful patching"* (this playbook). All three sources always agreed on the **storage location** — Tools → Voice Recordings — which was never in dispute.

### Exit Paths

> **Owner: `webex-connect-advanced.md` § Call Patch Node (Voice Node Group) → Exit Paths.** Reproduced here so this page works standalone; the reference doc wins on any disagreement.

| Event | When |
|-------|------|
| `onSuccess` (green) | B-party answered and call was bridged |
| `onNoAnswer` (yellow) | B-party did not answer, **or** the announcement loop threshold was reached without a DTMF keypress |
| `onError` (red) | Invalid destination or call setup failure |

### Output Variables

> **Owner: `webex-connect-advanced.md` § Call Patch Node (Voice Node Group) → Output Variables.** Reproduced here so this page works standalone; the reference doc wins on any disagreement.

| Variable | Description |
|----------|-------------|
| `$(nX.patch.APartyNumber)` | The number from which the outbound call is in progress (A-party) |
| `$(nX.patch.BPartyNumber)` | The B-party (patched destination) number |

### Bridge Behavior

The flow pauses while the bridge is active and resumes after one party disconnects. Post-bridge, the flow continues from the `onSuccess` exit — use this to play a post-call message or log the interaction. Post-bridge resumption behavior is not explicitly documented; verify in sandbox before production deployment.

---

## 7. Voice Channel Prerequisites (Inbound)

### Production Tenants

- **Voice-enabled phone number** with **inbound capability** — purchase/rent via Assets > Numbers. Ensure the number has Inbound enabled.
- **Number assignment** — the voice number must be assigned to the flow's Start trigger. An unassigned number will not route calls to the flow.
- **Flow must be Made Live** — draft flows do not receive inbound calls.

### Sandbox/Testing

- **Two-way voice** (make + receive) available in **USA, Canada, UK only**. Other countries: outbound only, no inbound.
- **Pre-provisioned number** — sandbox provides a voice number automatically.
- **5 test numbers max** — register up to 5 caller phone numbers for testing (same country).
- **5000 inbound calls** — sandbox limit across all flows. Whether inbound and outbound counts are tracked separately is not clarified in official docs.

---

## 8. Complete Flow Examples

**On the terminal node in these examples:** `End` is shown as a generic terminator. Cisco states *"Every voice flow must start with a Start node and end with a Disconnect node"* [source: https://help.webexconnect.io/docs/flows-introduction], but the linked Disconnect node page is marked deprecated — see Section 2 § Flow Termination — Disconnect Node before wiring the last node.

### Example 1: Simple Greeting + Info Line

```
Start (Inbound Call)
  |
  v
Voice Node Group
  |--- Play (TTS: "Thank you for calling. Our hours are Monday through Friday,
  |          9 AM to 5 PM. Goodbye.") → End
```

### Example 2: IVR Menu

```
Start (Inbound Call)
  |
  v
Voice Node Group
  |--- Play (TTS: "Press 1 for hours, Press 2 for directions...")
  |       |
  |       v
  |   Collect Input (DTMF, Input Size: 1)
  |       |
  |       v
  |   Branch (on $(nX.collect.input))
  |       |--- "1" → Play ("Our hours are...") → End
  |       |--- "2" → Play ("We are located at...") → End
  |       |--- default → Play ("Invalid selection. Goodbye.") → End
```

### Example 3: Caller Lookup + Personalized Response

```
Start (Inbound Call)
  |
  v
Voice Node Group
  |--- Play (TTS: "Thank you for calling. Let me look up your account.")
  |       |
  |       v
  |   HTTP Request (GET customer by ANI: $(n1.voice.msisdn))
  |       |
  |       v
  |   Branch (on HTTP status)
  |       |--- 200 → Play ("Hello $(n3.first_name). Your balance is...") → End
  |       |--- other → Play ("We couldn't find your account. Goodbye.") → End
```

---

## 9. Known Gotchas

| Issue | Fix |
|-------|-----|
| Flow doesn't trigger on inbound call | Voice number not assigned to the flow's Start trigger, or flow not Made Live |
| No Voice Node Group appears | For inbound, the VNG auto-creates from the trigger — don't add a Call User node |
| Caller hears nothing | Play node not wired as first node inside the VNG |
| Call drops immediately | Flow exits the VNG without any nodes — add at least a Play node |
| Sandbox inbound doesn't work | Two-way voice only available in USA, Canada, UK sandbox |
| ANI shows as empty | Caller ID may be blocked; handle the empty-ANI case in the flow |
| DTMF not detected | Collect Input node may need specific codec/DTMF relay settings |

---

## References

- [Start Node / Flow Triggers](https://help.webexconnect.io/docs/start-node)
- [Voice Node Group](https://help.webexconnect.io/docs/voice-node-group)
- [Play Node](https://help.webexconnect.io/docs/play-node)
- [Collect Input Node](https://help.webexconnect.io/docs/collect-input-node)
- [Call Patch Node](https://help.webexconnect.io/docs/call-patch-node)
- [Phone Numbers](https://help.webexconnect.io/docs/phone-numbers)
- [Sandbox Voice](https://help.webexconnect.io/docs/making-and-receiving-voice-calls-using-sandbox)
