# Cross-Channel Escalation Playbook

## Overview

Step-by-step guide for escalating a digital AI agent conversation (SMS, WhatsApp, Chat) to a voice call with a human agent — while preserving the chat transcript so the voice agent has full context.

**Key distinction from same-channel escalation:** Same-channel escalation (Queue Task) keeps the customer on the same digital channel and the human agent sees the conversation thread natively. Cross-channel escalation bridges two separate platforms: Webex Connect (digital) and WxCC Flow Designer (voice). There is no native hand-off object — CJDS is the bridge.

**Key distinction from outbound voice:** This is not a standalone outbound call. It's an outbound call triggered by a digital escalation, with chat context attached via CJDS.

---

## 1. Flow Structure

Two flows work together:

```
DIGITAL FLOW (Webex Connect):
  ... AI Agent conversation loop ...
  → onAgentHandover
  → Fetch Conversation Transcript (Update Conversation, method: Fetch transcript)
  → Write to CJDS (chat:transcript event with transcript content)
  → Trigger outbound voice call (Call User node OR webhook to separate voice flow)
  → End

VOICE FLOW (Webex Connect outbound OR Flow Designer):
  → Call User / Start (inbound callback)
  → Voice Node Group (Play TTS: "Please hold while we connect you")
  → Queue Contact (routes to human agent queue)
  → Disconnect Contact
  → End

AGENT DESKTOP:
  → Agent accepts voice call
  → Customer Journey Widget auto-loads events by ANI
  → chat:transcript event shows full chat history
```

---

## 2. Prerequisites

Before building:

1. **Digital inbound flow working** — AI Agent conversation loop with Search/Create/Append Conversation nodes (see `docs/playbooks/digital-inbound-agent.md`)
2. **CJDS provisioned** — Workspace ID, auth token, Webex Contact Center connector activated (see `docs/playbooks/cjds-integration.md` §1–2)
3. **Customer Journey Widget configured** in Agent Desktop layout (see `docs/playbooks/cjds-integration.md` §8)
4. **Voice queue and team configured** for human agents receiving escalated calls
5. **Outbound voice number** — a phone number asset in Connect for the Call User node, or a Flow Designer flow for inbound callbacks

---

## 3. Digital Flow: Fetch and Store Transcript

### Step 1: Fetch Conversation Transcript

On the `onAgentHandover` exit from the AI Agent node, add an **Update Conversation** node (Webex CC Engage palette):

| Field | Value |
|-------|-------|
| **Method Name** | `Fetch transcript` |
| **Authorization** | Default Authentication (Webex Engage Integrations) |
| **Conversation ID** | `$(conversationId)` |
| **Limit** | `500` (max — retrieves up to 500 messages) |
| **Offset** | `0` |

**Output:** `$(nX.transcriptJsonEsc)` contains the escaped JSON message array. `$(nX.countOfRecords)` gives the total message count.

See `docs/reference/digital-inbound.md` § 4b for full node documentation.

### Step 2: Write Transcript to CJDS

Add a **Customer Journey Data** node (Flex 3) or **HTTP Request** node after the Fetch Transcript node.

**Using the native CJD node (Flex 3):**

| Field | Value |
|-------|-------|
| **Method** | Write to CJDS |
| **Authorization** | Pre-configured CJDS auth |
| **Event ID** | Unique string (use flow transaction ID: `$(flid)`) |
| **Event Type** | `chat:transcript` |
| **Event Source** | `ai_agent` |
| **Identity Type** | `phone` |
| **Identity** | Customer phone number (from Start node variables) |

**Using HTTP Request (non-Flex 3):**

| Field | Value |
|-------|-------|
| **Method** | POST |
| **URL** | `https://api.wxcc-{region}.cisco.com/publish/v1/api/event?workspaceId={workspaceId}` |
| **Authorization** | `Bearer $(CJDS_Auth_Token)` |
| **Content-Type** | `application/json` |

**Request body:**
```json
{
  "id": "$(flid)",
  "specversion": "1.0",
  "type": "chat:transcript",
  "source": "ai_agent",
  "identity": "<customer phone number>",
  "identitytype": "phone",
  "datacontenttype": "application/json",
  "data": {
    "messages": $(nX.transcriptJsonEsc),
    "channel": "whatsapp",
    "agentName": "<AI agent name>",
    "escalationReason": "customer requested human agent",
    "messageCount": "$(nX.countOfRecords)"
  }
}
```

> **Write domain differs from read domain.** Event writes go to `api.wxcc-{region}.cisco.com`. See `docs/playbooks/cjds-integration.md` §4c.

Wire `onEventPostSuccess` / HTTP 202 to the next step (trigger outbound call). Wire failure paths to error handling — if CJDS write fails, you can still place the call; the agent just won't have the transcript.

---

## 4. Trigger the Outbound Voice Call

Two options depending on your architecture:

### Option A: Call User Node in the Same Connect Flow

Add a **Call User** node after the CJDS write. This initiates an outbound call to the customer directly from the digital flow.

| Field | Value |
|-------|-------|
| **Destination** | Customer phone number |
| **From Number** | Your outbound voice number asset |

Inside the Voice Node Group that auto-creates:
- **Play TTS**: "We're connecting you with an agent now. One moment please."
- The call must be transferred to WxCC for queue routing — use **Call Patch** to bridge to a WxCC entry point, or use a webhook to a Flow Designer flow that handles Queue Contact.

> **Limitation:** Call User places an outbound call via Connect's PSTN. Routing this call into a WxCC queue requires either a Call Patch to a WxCC entry point or a separate inbound Flow Designer flow triggered by the outbound call reaching a WxCC number.

### Option B: Webhook to a Separate Voice Flow

Post the customer's phone number and metadata to a webhook-triggered outbound voice flow (see `docs/playbooks/outbound-voice.md`). The voice flow handles the Call User and subsequent queue routing independently.

| Field | Value |
|-------|-------|
| **HTTP Request** | POST to your outbound voice flow's webhook URL |
| **Body** | `{ "phone": "<customer phone>", "reason": "chat_escalation" }` |

The outbound voice flow receives the webhook, places the call, plays a TTS message, and routes to the queue.

---

## 5. Voice Flow: Build the Flow Designer Inbound Flow

The outbound call from Connect (via Call User + Call Patch, or via a mapped PSTN number) lands on a WxCC voice entry point. A Flow Designer flow must be assigned to that entry point to route the call to a human agent queue.

This flow is simple — its only job is to greet the caller and queue the call.

### Flow Structure

```
NewContact
  → Play Message ("Thank you for waiting. Connecting you with an agent now.")
  → Queue Contact (your voice escalation queue)
  → Play Music (hold music while waiting for agent)
  → Disconnect Contact
```

### Build Steps

1. **Create the flow:** Control Hub → Contact Center → Flows → **New Flow**. Name it (e.g., `Chat-Escalation-Voice-Flow`). Choose "Start from scratch" or use the "Simple Inbound Call to Queue" template. [source: flow-designer-essentials.md § Create a New Flow]

2. **Add Play Message:** Drag a **Play Message** activity from the activity panel. Wire `NewContact` → Play Message.
   - Click **Add Text-to-Speech Message** in the Prompt section
   - Connector: **Cisco Cloud TTS** [source: flow-designer-essentials.md § Play Message Activity]
   - Text: `Thank you for waiting. Connecting you with an agent now.`

3. **Add Queue Contact:** Drag a **Queue Contact** activity. Wire Play Message → Queue Contact.
   - **Static Queue**: select your voice escalation queue from the dropdown [source: flow-designer-essentials.md § Queue Contact Activity]

4. **Add Play Music:** Drag a **Play Music** activity. Wire Queue Contact (default exit) → Play Music.
   - **Music File**: select a hold music audio file from the dropdown
   - **Music Duration**: `300` (seconds — 5 minutes; adjust to match your expected queue wait) [source: flow-designer-essentials.md § Play Music Activity]

5. **Add Disconnect Contact:** Drag a **Disconnect Contact** activity. Wire Play Music → Disconnect Contact. This terminates the call after the agent conversation ends. [source: flow-designer-essentials.md § Disconnect Contact Activity]

### Error Handling

Wire the **Undefined Error** output on Queue Contact to an error path [source: flow-designer-essentials.md § Queue Contact Activity]:

```
Queue Contact → Undefined Error → Play Message ("We're unable to connect you at this time. Please try again later.") → Disconnect Contact
```

Also wire the flow's **OnGlobalError** event handler (Event Flows tab) to a fallback Play Message + Disconnect Contact, so any unhandled error announces gracefully instead of silently dropping the call. [source: flow-designer-essentials.md § OnGlobalError]

### Publish and Assign

1. Click **Validate** in the toolbar — fix any errors
2. Click **Publish**
3. Go to **Control Hub → Contact Center → Entry Points**, edit your voice entry point (the one mapped to the callback PSTN number)
4. Under **Flow**, select the published flow
5. Save

[source: flow-designer-essentials.md § Publish and Link]

---

## 6. Voice Side: Agent Receives Call with Context

No additional flow work is needed on the voice side for transcript visibility. The **Customer Journey Widget** in the Agent Desktop handles it:

1. Voice call lands in the queue
2. Human agent accepts the call
3. Widget auto-loads CJDS events using the caller's ANI (phone number)
4. The `chat:transcript` event appears in the journey timeline
5. Agent sees the full chat message history, channel, AI agent name, and escalation reason in the event's `data` payload

**Prerequisite:** The Customer Journey Widget must be configured in the desktop layout. See `docs/playbooks/cjds-integration.md` §8.

---

## 7. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Transcript empty / `countOfRecords` = 0 | `conversationId` wrong or Append Conversation nodes missing from the chat flow | Verify Create/Append Conversation nodes ran before Fetch Transcript; check `$(conversationId)` is populated |
| CJDS write returns 401 | Token expired | Refresh CJDS auth token (8–12 hour lifespan). See `docs/playbooks/cjds-integration.md` §2 |
| CJDS write returns 403 | Missing `cjds:admin_org_write` scope | Add scope to Service App and regenerate token |
| Agent doesn't see transcript in desktop | Customer Journey Widget not configured, or phone number mismatch between chat identity and voice ANI | Verify widget is in desktop layout JSON; verify identity written to CJDS matches the ANI of the outbound call |
| Transcript shows in CJDS but is truncated | Fetch Transcript limit too low (default: 10) | Set Limit to `500` on the Fetch Transcript node |
| Outbound call fails | Invalid phone number or no voice number asset | Check From Number is a valid Connect voice asset; check destination format |
| Call places but agent has no context | CJDS event identity doesn't match voice ANI | Ensure the phone number written as `identity` in the CJDS event matches the caller ID the agent sees (E.164 format recommended) |
| Call Transfer node unavailable in Connect | Tenant is in London or Europe region — Call Transfer is region-restricted [source: webex-connect-advanced.md § Call Transfer Node] | Use **Call Patch** instead (no region restriction) to bridge the call to the WxCC entry point |
| Flow Designer flow not triggered when call hits WxCC entry point | Routing strategy not assigned to the voice entry point | Control Hub → Contact Center → Entry Points → edit the entry point → under Flow, select the published flow [source: flow-designer-essentials.md § Publish and Link] |

---

## 8. Design Considerations

**Transcript size:** CJDS event `data` is freeform JSON with no documented hard size limit. Short-to-medium conversations (under ~100 messages) fit easily. For very long conversations, consider writing a structured summary to CJDS and storing the full transcript in your database with a link in the event data.

**Timing:** The Fetch Transcript + CJDS write + Call User sequence adds latency before the customer hears anything. Consider sending a chat message ("We'll call you shortly") before starting the voice sequence, so the customer knows what's happening.

**Phone number matching:** CJDS alias lookup normalizes phone formats, but the Customer Journey Widget matches by ANI. Write the CJDS event `identity` in the same format the voice call will present (E.164 with `+` prefix preferred). CJDS may store numbers as 10 digits without country code — test in your environment.

**Fallback:** If CJDS write fails, still place the call. The agent won't have the transcript but can still help the customer. Don't block the escalation on a CJDS failure.

---

## 9. Testing Checklist

| # | Test | Expected Result | How to Verify |
|---|------|----------------|---------------|
| 1 | Send a chat message via Live Chat widget | AI agent responds in chat | Chat window shows response |
| 2 | Multi-turn conversation | AI agent maintains context across turns via SessionId | Chat continues coherently |
| 3 | Say "talk to a person" or trigger escalation | AI agent asks for phone number | Chat shows phone number prompt |
| 4 | Provide phone number; agent escalates | Chat says "We'll call you shortly" | Chat window shows confirmation message |
| 5 | Outbound call placed to customer | Customer's phone rings | Customer receives call from Connect outbound number |
| 6 | Call bridges to WxCC via Call Patch or entry point | Flow Designer flow plays greeting, queues call | Caller hears "Connecting you with an agent now" |
| 7 | Agent accepts voice call | Agent desktop shows call + Customer Journey Widget | Desktop rings, widget loads |
| 8 | Transcript visible in widget | `chat:transcript` event shows full chat history | Widget timeline shows chat messages, channel, agent name, escalation reason |
| 9 | CJDS write failure does not block callback | Outbound call still places even if CJDS write fails | Disconnect CJDS auth token, verify call still goes out |
| 10 | Fetch Transcript with Limit=500 | All messages retrieved | Check `countOfRecords` matches expected message count |

---

## References

- `docs/reference/digital-inbound.md` — Fetch Conversation Transcript node (§4b), digital flow architecture
- `docs/playbooks/cjds-integration.md` — CJDS auth, event writes, Customer Journey Widget (§8), cross-channel escalation example
- `docs/playbooks/digital-inbound-agent.md` — Digital inbound conversation flow setup
- `docs/playbooks/outbound-voice.md` — Outbound voice call patterns (Call User, Voice Node Group)
- `docs/reference/flow-designer-essentials.md` — Play Message, Queue Contact, Play Music, Disconnect Contact, OnGlobalError (§5 voice flow build)
- `docs/reference/webex-connect-advanced.md` — Call Patch, Call Transfer region restrictions
- [Fetch Conversation Transcript (official docs)](https://help.webexconnect.io/docs/fetch-conversation-transcript)
- [Queue Task Node (official docs)](https://help.webexconnect.io/docs/queue-task)
