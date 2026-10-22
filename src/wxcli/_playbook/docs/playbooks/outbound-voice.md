# Outbound Voice & TTS Playbook

<!-- ref-tag: outbound-voice-v2 -->

## Overview

This playbook covers how to build outbound automated voice calls in Webex Connect — specifically, webhook-triggered flows that dial a phone number and play a TTS message. This is the pattern for order-ready notifications, appointment reminders, and automated paging.

**Key distinction from AI Agent flows:** Outbound voice flows use the **Start node** (webhook trigger), **Call User node**, and **Play node** — NOT the Receive node / AI Agent Event / Flow Outcomes pattern documented in `connect-flows.md`.

**For inbound voice handling** (caller dials in, flow reacts), see `inbound-voice.md`. Inbound flows use a Voice > Inbound Call trigger instead of a webhook, and the Voice Node Group auto-creates from the inbound call — no Call User node is needed.

---

## 1. Flow Structure

An outbound voice call flow follows this pattern:

```
Start (Webhook) → [Optional: HTTP Request] → Call User → Voice Node Group [ Play (TTS) ] → End
```

### Required Nodes

- **Start node** (always first): webhook trigger receives the external event
- **Call User node**: initiates the outbound call (sits OUTSIDE the Voice Node Group)
- **Voice Node Group**: container that auto-creates when Call User is added — all voice interaction nodes live inside it
- **Play node** (inside Voice Node Group): plays TTS or audio to the answered call
- **End node**: terminates the flow

### Optional Nodes

- **HTTP Request node** (before Call User): fetch dynamic data from a DB/API before placing the call
- **Branch node** (after Call User): handle different call outcomes (busy, no answer, etc.)
- **Collect Input / IVR Menu** (inside Voice Node Group): capture DTMF or speech input, multi-option menus
- **Record / Call Patch / Call Transfer** (inside Voice Node Group): record audio, bridge calls, or transfer calls (see `webex-connect-advanced.md` for full reference)

### Flow Termination — Disconnect Node

*"Every voice flow must start with a Start node and end with a **Disconnect** node."* [source: https://help.webexconnect.io/docs/flows-introduction — quote re-verified against the live page 2026-07-25; the same rule is recorded in `webex-connect.md` § Voice flows must end with Disconnect and in `inbound-voice.md` § Flow Termination — Disconnect Node]

The same page also states *"Every node outcome must either be mapped to the next node or terminate onto an End node"* [source: https://help.webexconnect.io/docs/flows-introduction — verified 2026-07-25], which is why the unanswered call outcomes in Section 7 (`onbusy`, `onnoanswer`, `onreject`, `onError`, `oncallfail`) terminate on `End`.

The Disconnect node *"allows you to record the logs and report when a call is terminated in a voice flow"*, and it exists to make edge wiring tractable in large voice flows — *"Here the action of connecting to node group edge will disconnect the call."* Its configuration groups are **Disconnect Settings** (Disconnect Code, Disconnect Reason), **Play Options** (Type, Session Variables, Offset, Duration, User Assets), **Properties** (Label), and **Params** (Session Data) [source: https://help.webexconnect.io/docs/voice-disconnect].

⚠ **Open question — do not treat as settled.** The `flows-introduction` rule above is stated for voice flows generally, but the node page it links to is titled **"Voice: Disconnect (deprecated)"** and carries the notice *"The older version of voice nodes are deprecated. If you are using an older version and wish to switch to the newer version, contact Customer Support."* [source: https://help.webexconnect.io/docs/voice-disconnect — verified 2026-07-25]. Whether a tenant on the current voice-node version terminates with this same node, or with a replacement node, is **not established by either page**. Confirm against your tenant's node palette before building. The examples in Section 7 therefore show a generic terminal `End` rather than asserting a node name.

---

## 2. Call User Node Configuration

The **Call User** node initiates the outbound call. It replaces the deprecated "Send Voice" node (deprecated in v5.4.x).

> **Owner: `webex-connect-advanced.md` § Call User Node (Initiates the Call).** The tables below are reproduced here so this page works on its own — if they ever disagree with the reference doc, **the reference doc wins.**

**Build order:** drag a Call User node onto the canvas after the Start node (the **Voice Node Group** auto-creates alongside it — you do not add that separately), fill in the fields below, then wire the exit paths. `onAnswer` goes into the Voice Node Group; every other edge must terminate (see § 1 Flow Termination). Section 7 shows the full wiring.

### Required Fields

| Field | Details |
|-------|---------|
| **Destination Type** | `msisdn` (phone number) or `Customer Id` (platform identifier) |
| **Destination** | Phone number in **E.164 format** (e.g., `+15551234567`). Accepts a variable: `$(n1.inboundWebhook.phone)` |
| **From Number** | Select from dropdown of provisioned voice-enabled numbers. Supports **Dynamic** mode — select "Dynamic" and provide a variable. |

### Optional Fields

| Field | Details |
|-------|---------|
| **Correlation ID** | User-defined tracking ID. Accepts dynamic values. |
| **Callback Data** | Data passed back to client systems. **Limited to 2KB** — exceeding causes `onPolicyFail`. |
| **Notify URL** | Webhook URL for call status notifications. |
| **Expiry Time** | Seconds before expiry, or a specific UTC date/time. Webex Connect strongly advises setting one — it is also the only way the `onExpiry` edge can ever fire. |

### Exit Paths (Events)

| Event | When |
|-------|------|
| `onAnswer` (green) | Call answered — auto-connects to Voice Node Group |
| `onError` (red) | Invalid user ID or missing phone digits |
| `oncallfail` (red) | Network connectivity issues |
| `onnoanswer` (red) | Call unanswered |
| `onbusy` (red) | Busy signal |
| `onreject` (red) | Call rejected by recipient |
| `onPolicyFail` (red) | Policy failure (e.g., callback data > 2KB) |
| `onExpiry` (orange) | Request expired (only when expiry is configured) |

⚠ **Do not retype the event names from memory.** Call User mixes lowercase (`onbusy`, `onnoanswer`, `onreject`, `oncallfail`) with mixed case (`onAnswer`, `onError`, `onPolicyFail`, `onExpiry`), and Call Patch spells its no-answer edge `onNoAnswer` — different node, different casing. Copy them exactly.

### Output Variables

| Variable | Description |
|----------|-------------|
| `call.fromNumber` | Originating number |
| `call.destination` | Receiving number |
| `call.transId` | Transaction ID |
| `call.timestamp` | Call timestamp |

---

## 3. Voice Node Group

The **Voice Node Group** is the container that auto-creates when you add a Call User node. All voice interaction nodes must live inside it.

> **Owner: `webex-connect-advanced.md` § Voice Nodes (Voice Node Group).** Reproduced here so this page works standalone; the reference doc wins on any disagreement.

### Key Rules

- Up to **1,000 Voice Node Groups** per flow
- Cannot be deleted once created — so do not add a Call User node speculatively
- **Wait for** and **Delay** nodes are NOT supported inside the group. If your design needs a pause, it belongs *before* the Call User node

### Voice-Specific Nodes (Inside Group)

| Node | Purpose |
|------|---------|
| **Play** | Play TTS or audio to the caller |
| **Record** | Record caller audio (voicemail, statements) |
| **Collect Input** | Capture DTMF or speech input |
| **IVR Menu** | Multi-option menu with branching |
| **Call Patch** | Bridge caller with another number (two-party conference) |
| **Call Transfer** | Blind or warm transfer to another number (available on request) |

### General-Purpose Nodes (Inside Group)

These non-voice nodes can run inside the group while the call is active:

Evaluate, Branch, HTTP Request, Data Parser, Data Transform, SMS, Email, WhatsApp, Messenger, Apple Messages for Business, Profile, Generate OTP, Validate OTP, Decryption, Encryption

### Answering Machine Detection (AMD)

Enable AMD only if the message is worth leaving on a machine — or worth *not* leaving. It costs a detection delay on every call.

Configure it in the Voice Node Group **Settings** panel:

1. Enable AMD in group settings
2. Configure a prompt to play during detection (supports Pre-recorded, Upload File, URL, or TTS)
3. Wire the AMD exit paths:

| Exit Path | When |
|-----------|------|
| **Success (green)** | Human answered — AMD determined a person picked up; connects normally to the Voice Node Group |
| `onAnsweringMachine` | Machine/voicemail detected — fires as the **default** outcome under the Success edge; when detection is ambiguous, the system assumes machine |
| `onCallDrop` | Call dropped during AMD detection |

⚠ **The most common wiring mistake:** treating `onAnsweringMachine` as a sibling of the green **Success** edge. It is not — it branches *off* Success, and it is the **default** when detection is ambiguous. Wire the human path deliberately or machines will get it.

---

## 4. Play Node — TTS Configuration

The **Play node** lives inside the Voice Node Group and plays audio or TTS to the caller.

### TTS Settings

> **Owner: `webex-connect-advanced.md` § Play Node (Voice Node Group).** Reproduced here so this page works standalone; the reference doc wins on any disagreement.

| Setting | Options |
|---------|---------|
| **TTS Processor** | Azure (only supported engine in Connect) |
| **Voice Type** | Neural (Standard is deprecated) |
| **Language** | Select from list, or "Dynamic" (pass ISO 639 code at runtime) |
| **Voice** | Azure Neural voice name (e.g., `AriaNeural`, `GuyNeural`), or dynamic |
| **Input Format** | **Plain Text** (3,000 char limit) or **SSML** (6,000 char limit) |

⚠ **Webex Connect uses Azure Neural TTS, not Cisco TTS.** Cisco TTS exists only in WxCC Flow Designer, a separate platform. Voice names, SSML support and the language list all come from Azure — do not carry Cisco TTS voice names over from a Flow Designer build.

**Two decisions are yours at this step:**

**Plain Text or SSML?** Pick SSML if the message reads out an order number, phone number, date or amount — `<say-as>` is the difference between "O-R-D dash four five two one" and an unintelligible mumble. Pick Plain Text otherwise; it is simpler and gives you a 3,000 character budget instead of SSML's 6,000. Section 5 has worked examples of both.

**Static or Dynamic language?** Set **Language** to "Dynamic" only if the flow actually knows the recipient's language at runtime (from the webhook payload or a database lookup). Otherwise pick it from the list — a Dynamic language field with an empty variable fails the call, not just the prompt.

### Audio Alternatives (Non-TTS)

The Play node also supports:
- **Pre-recorded audio** from Voice Media library (Tools > Voice Media)
- **File upload** — drag/drop WAV or MP3, max 20MB (the 10MB limit applies to Voice Media Manager uploads and AMD prompt uploads, not the Play node's own upload field)
- **URL** — point to a hosted audio file, supports dynamic variable in URL

Click **Add New Audio** to queue multiple prompts in sequence within a single Play node.

### Play Node Outcomes

| Outcome | When |
|---------|------|
| `onSuccess` | Audio plays without errors |
| `onError` | Playback encounters issues |

---

## 5. TTS Variable Insertion

Use Connect's standard `$(nX.variableName)` syntax to insert dynamic values into TTS messages. **Always use the variable picker** — manually typed variables may arrive empty.

### Plain Text Example

```
Hello. Your order $(n3.order_number) is ready for pickup at $(n3.location_name). Thank you.
```

### SSML Example

```xml
<speak>
  Hello. Your order number
  <say-as interpret-as="characters">$(n3.order_number)</say-as>
  is ready for pickup at $(n3.location_name).
  <break time="500ms"/>
  Thank you for your business.
</speak>
```

### Key SSML Tags for Notifications

> **Owner: `webex-connect-advanced.md` § SSML Tags (Azure Neural TTS).** Reproduced here so this page works standalone; the reference doc wins on any disagreement.

| Tag | Purpose | Example |
|-----|---------|---------|
| `<speak>` | Required root wrapper for all SSML | `<speak>Your message here</speak>` |
| `<say-as interpret-as="characters">` | Spell out letter/digit by letter/digit | `ORD-4521` → "O-R-D-four-five-two-one" |
| `<say-as interpret-as="cardinal">` | Read as number | `42` → "forty-two" |
| `<say-as interpret-as="ordinal">` | Read as ordinal | `3` → "third" |
| `<say-as interpret-as="telephone">` | Read as phone number | Standard phone cadence |
| `<say-as interpret-as="currency">` | Read as money | `$53.21` → "fifty-three dollars and twenty-one cents" |
| `<say-as interpret-as="date">` | Read as date | Standard date reading |
| `<break time="500ms"/>` | Insert pause | Half-second silence |
| `<prosody rate="slow">` | Control speed | Slow down for important info |
| `<sub alias="...">` | Substitute pronunciation | `<sub alias="World Wide Web">WWW</sub>` |
| `<audio src="..."/>` | Embed pre-recorded audio clip inline | Mix TTS with audio files |
| `<p>` / `<s>` | Paragraph / sentence boundaries | Natural pauses between sections |

**Three do most of the work in a notification flow:** `<say-as interpret-as="characters">` around any order number or confirmation code; `<break time="500ms"/>` before the closing line so the message does not run into the hang-up; `<say-as interpret-as="currency">` for any amount.

⚠ Wrap the whole message in `<speak>` or the prompt fails — and remember SSML markup counts against the 6,000 character budget, not just the words the caller hears.

### Variable Sources

| Source | Syntax | Example |
|--------|--------|---------|
| Start node (webhook payload) | `$(n1.inboundWebhook.fieldName)` | `$(n1.inboundWebhook.order_id)` |
| HTTP Request node output | `$(nX.outputVar)` | `$(n3.customer_name)` |
| Evaluate script output | `$(nX.outputName)` | `$(n4.formatted_date)` |
| Evaluate custom flow variable | `$(variableName)` — no node prefix | `$(formatted_date)` |

---

## 6. Voice Channel Prerequisites

### Production Tenants

- **Voice-enabled phone numbers** — purchase/rent via Assets > Numbers. Ensure the **Voice** feature flag is enabled on the number.
- **Number types**: Landline, Toll-free, or Mobile. Lead times vary (US TFNs ~2 weeks, long codes ~2 days).
- **Azure TTS** — available by default in Connect; no separate Azure subscription needed.
- **Voice Media Manager** (optional) — for pre-recorded prompts: Tools > Voice Media. WAV/MP3, max 10MB per file, 1GB total per tenant.

### Sandbox/Testing

- **5,000 lifetime outbound calls** limit
- Must **register test phone numbers** first (up to 5 per account, same country)
- Two-way voice (make + receive) in **USA, Canada, UK only**. Other countries: outbound only.
- From number is pre-provisioned and auto-populated.

---

## 7. Complete Flow Example: Order-Ready Notification

```
Start (Webhook: order_id, customer_phone)
  |
  v
HTTP Request (GET order details from DB by order_id)
  |
  v
Call User (destination: $(n1.inboundWebhook.customer_phone), from: provisioned number)
  |
  |--- onAnswer ---> Voice Node Group
  |                      |
  |                      v
  |                  Play (TTS: "Hello. Order $(n3.order_number) is ready for pickup
  |                              at $(n3.location_name). Thank you.")
  |                      |
  |                      v
  |                  End (call disconnects when flow exits Voice Node Group)
  |
  |--- onbusy ---------> End
  |--- onnoanswer -----> End (or: retry logic via separate flow)
  |--- onreject -------> End
  |--- onError --------> End
  |--- oncallfail -----> End
```

**On the terminal node in this example:** `End` is shown as a generic terminator. Cisco states *"Every voice flow must start with a Start node and end with a Disconnect node"* [source: https://help.webexconnect.io/docs/flows-introduction], but the linked Disconnect node page is marked deprecated — see Section 1 § Flow Termination — Disconnect Node before wiring the last node.

---

## 8. API Alternative (No Flow)

For simple fire-and-forget outbound TTS calls without interactive logic, use the API directly:

**Voice API v1:**
```
POST https://api.{region}.webexconnect.io/v1/voice/messages
```

**Send Message API v2:**
```
POST https://{region}.webexconnect.io/v2/messages
```
With `channel: "voice"` and a content object containing TTS text.

These skip the flow builder entirely but do not support branching, AMD, or interactive responses.

---

## 9. Known Gotchas

| Issue | Fix |
|-------|-----|
| TTS says "dollar sign n three dot order number" literally | Variable not resolved — used manual typing instead of variable picker |
| Call connects but no audio plays | Play node not wired inside the Voice Node Group, or TTS text field is empty |
| `onError` fires immediately | Destination number not in E.164 format (must include `+` and country code) |
| AMD always detects "machine" | AMD tuning thresholds are not publicly documented — test with real numbers |
| AMD TTS prompt truncated or errors | AMD TTS prompt has a **2,000-character limit** — different from Play node limits (3,000 plain text / 6,000 SSML) |
| Call drops after TTS plays | Expected behavior — call disconnects when flow exits Voice Node Group |
| "Send Voice" node missing from palette | Deprecated in v5.4.x — use **Call User** node instead |
| TTS voice sounds wrong | Verify Language and Voice dropdowns match — mismatched language/voice produces unexpected results |
| SSML tags read aloud as text | Input Format set to "Plain Text" instead of "SSML" |
| Variable picker shows no webhook variables | Start node sample input not parsed — go back to Start node and click Parse |

---

## References

- [Call User Node](https://help.webexconnect.io/docs/voice-call-user)
- [Voice Node Group](https://help.webexconnect.io/docs/voice-node-group)
- [Play Node](https://help.webexconnect.io/docs/play-node)
- [Voice Media](https://help.webexconnect.io/docs/voice-media)
- [Phone Numbers](https://help.webexconnect.io/docs/phone-numbers)
- [Sandbox Voice](https://help.webexconnect.io/docs/making-and-receiving-voice-calls-using-sandbox)
- [Voice API v1](https://developers.webexconnect.io/reference/voice-only-api-v1-make-outbound-calls)
- [Send Message API v2](https://developers.webexconnect.io/reference/send-message-api-v2-make-voice-call)
