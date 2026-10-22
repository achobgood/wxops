# Digital Inbound Agent Playbook

<!-- ref-tag: digital-inbound-agent-v1 -->

## Overview

Step-by-step guide for building a digital inbound AI agent flow in Webex Connect + WxCC. This flow handles customer conversations on digital channels (SMS, WhatsApp, Chat, Email) by integrating with AI Agent Studio — the digital equivalent of the voice inbound path (Virtual Agent V2 in Flow Designer).

**Key distinction from voice:** The entire flow lives in Webex Connect. Flow Designer is NOT used for digital inbound.

**Key distinction from action flows:** This is the parent conversation flow, not a per-action flow. Action flows (Receive → HTTP → Flow Outcomes) are channel-agnostic and work for both voice and digital without changes.

---

## 1. Flow Structure

A digital inbound agent flow follows this pattern:

```
Start (Channel Trigger) → Search Conversation → Create/Append Conversation → AI Agent (Process Message) → Channel Reply → Receive → [Loop to AI Agent] → Queue Task (on escalation) → End
```

### Required Nodes

- **Start node** (always first): channel-specific trigger receives the inbound customer message
- **Search Conversation** (Webex CC Engage): checks if a conversation already exists for this customer
- **Create Conversation** (Webex CC Engage): creates a new conversation thread — outputs `$(conversationId)` needed for escalation
- **Append Conversation** (Webex CC Engage): adds the message to an existing conversation thread
- **AI Agent node** (Process Message): sends the customer message to AI Agent Studio and receives the agent's response
- **Channel Reply node**: channel-specific send node (SMS, WhatsApp, etc.) that delivers the agent's response to the customer
- **Receive node**: waits for the customer's next message, then loops back to AI Agent for multi-turn handling
- **Queue Task node**: routes to a human agent queue when the AI Agent triggers escalation
- **End node**: terminates the flow

---

## 2. Prerequisites

Before building the flow:

1. **Webex Engage and Connect provisioned** — Control Hub > Tenant Settings > Digital
2. **Webex CC Task and Engage nodes authorized** in Connect — navigate to Assets → Integrations → Pre-built Integrations → Actions → Manage → Node Authorizations. The authorizing user must have a Contact Center License and Admin role.
3. **Channel asset created** — Assets > Apps for WhatsApp/Chat/Email; Assets > Numbers for SMS
4. **AI Agent created and deployed** in AI Agent Studio
5. **Entry Point created** in WxCC — Social Channel type, linked to the channel asset
6. **Queue and Team configured** for human agent escalation

---

## 3. Start Node Configuration

Create a new flow in Connect. Configure the Start node with a channel-specific trigger:

| Channel | Channel Section | Trigger Name | Message Variable | Customer ID Variable |
|---------|----------------|--------------|------------------|----------------------|
| **SMS** | Mobile Originated | Mobile Originated - MO | `$(n1.sms.message)` | `$(n1.sms.senderNumber)` |
| **WhatsApp** | WhatsApp | Incoming Message | `$(n1.whatsapp.message)` | `$(n1.whatsapp.waId)` |
| **Live Chat** | Mobile & Web App | Incoming Message | `$(n1.inappmessaging.message)` | `$(n1.inappmessaging.userId)` |
| **Email** | Email | Incoming Message | `$(n1.email.message)` | `$(n1.email.emailId)` |
| **FB Messenger** | Messenger | Incoming Message | `$(n1.messenger.message)` | `$(n1.messenger.psId)` |
| **Apple Messages** | Apple Messages for Business | Incoming Message | `$(n1.abc.message)` | `$(n1.abc.abcUserId)` |

Each channel has a unique variable namespace. The message variable feeds into the AI Agent node; the customer ID variable feeds into conversation management and reply routing.

---

## 4. Search Conversation Node

Drag a **Search Conversation** node from the **Webex CC Engage** palette (full name: Webex CC Engage Integration Nodes, Data Streams, and Node Authorizations).

- **Input:** Customer's channel identifier from the Start node
- **Branch on conversation state (5 exits):**
  - `_noConversationFound` → wire to **Create Conversation**
  - `_conversationActive` → wire to **Append Conversation**
  - `_conversationClosed` → wire to **Reopen Conversation** (or Create Conversation if reopen is not available)
  - `_conversationInQueue` → handle or log (conversation already queued for an agent)
  - `_conversationOnHold` → handle or log (conversation is on hold)

This node requires Webex CC Engage authorization in Connect (see Prerequisites).

---

## 5. Create / Append Conversation Nodes

### Create Conversation

- Creates a new conversation in Webex Engage
- **Output:** `$(conversationId)` — the conversation ID required by Queue Task for escalation (note: the exact output variable name from Create Conversation is not explicitly documented in official docs; `$(conversationId)` matches the Queue Task node's default Conversation ID field)
- Links the conversation to the customer's channel identifier
- Wire output to the AI Agent node

### Append Conversation

- Adds the inbound message to an existing conversation thread (Webex CC Engage palette node)
- Maintains continuity for returning customers within the same conversation window
- Wire output to the AI Agent node

---

## 6. AI Agent Node (Process Message)

This is the core node. Drag an **AI Agent** node and configure:

### Input Fields

| Field | Value |
|-------|-------|
| **Method** | Process Message |
| **Agent Type** | Scripted or Autonomous |
| **Agent** | Select your agent from AI Agent Studio dropdown |
| **Message Variable** | Customer's message from Start node: e.g., `$(n1.whatsapp.message)` (first turn) or `$(nX.whatsapp.message)` (subsequent turns from Receive node) |
| **Channel** | Channel name (WhatsApp, SMS, etc.) |
| **User Identifier** | Customer's channel ID: e.g., `$(n1.whatsapp.waId)` |
| **Custom Parameters** | Optional: key-value pairs for customer profile data (not documented as scripted-only in official docs — behavior may vary) |
| **Message Parameters** | Optional: key-value pairs accessible in the agent as `${extra_params.<key>}` |

### Output Variables

| Variable | Description |
|----------|-------------|
| `TextResponse` | Text-only agent response (first text item from the agent's reply) |
| `FullResponse` | Complete response array including rich elements (carousels, quick replies, etc.) |
| `SessionId` | Conversation session ID — **store this and pass it back on every subsequent call** |
| `Datastore` | Session variables JSON |
| `ConsumerId` | Customer identifier from AI Agent Studio |
| `TransactionId` | Transaction identifier |
| `MessageMetadata` | Metadata about the inbound message |
| `SessionMetadata` | Session-level metadata from the agent |
| `ResponsePayload` | Full response payload from the agent |

### Exit Paths

| Exit | When | Route To |
|------|------|----------|
| `onSuccess` | Agent responded | Channel Reply node |
| `onAgentHandover` | Agent escalated to human | Queue Task node |
| `onError` | Processing failed | Error handling → End |
| `onTimeOut` | 15-second timeout exceeded | Timeout handling → End |
| `onInvalidCustomerID` | Customer identifier is invalid or missing | Error handling → End |
| `onInvalidMessage` | Message format is invalid | Error handling → End |

---

## 7. Channel Reply Node

Use the channel-specific send node matching the Start trigger:

| Start Trigger Channel | Reply Node |
|-----------------------|------------|
| SMS inbound | SMS reply node |
| WhatsApp inbound | WhatsApp reply node |
| Live Chat inbound | Live Chat reply node |
| Email inbound | Email reply node |
| FB Messenger inbound | Messenger reply node |
| Apple Messages inbound | Apple Messages reply node |

### Configuration

| Field | Value |
|-------|-------|
| **Destination** | Customer's channel ID from Start node |
| **Message** | `$(nX.TextResponse)` for text, or parse `$(nX.FullResponse)` for rich content |
| **Wait For** | Gateway Submit (field name not confirmed from official docs) |

Wire `onSuccess` to the **Receive** node to continue the conversation loop.

---

## 8. Receive Node

Waits for the customer's next message. Configure for the same channel as the Start trigger.

- **Output:** `$(nX.{channel}.message)` — the customer's next message (e.g., `$(nX.whatsapp.message)`, `$(nX.sms.message)`)
- Wire the Receive node's output **back to the AI Agent node** to create the conversation loop
- **Pass the `SessionId`** from the first AI Agent call on all subsequent calls to maintain conversation context

### Conversation Loop Diagram

```
AI Agent (Process Message)
  |
  +-- onSuccess --> Channel Reply --> Receive --> [loop back to AI Agent]
  |
  +-- onAgentHandover --> Queue Task --> End
```

This loop continues until the customer stops responding, the AI Agent escalates, or the session times out.

---

## 9. Queue Task Node (Escalation)

Configure for the `onAgentHandover` exit from the AI Agent node:

| Field | Value |
|-------|-------|
| **Task ID** | `$(flid)` — flow transaction ID |
| **Conversation ID** | `$(conversationId)` — from Create Conversation node |
| **Media Type** | `Social` (SMS, WhatsApp, FB, Apple), `Email`, or `Chat` (Live Chat) |
| **Media Channel** | Select the originating channel from dropdown |
| **Queue** | Select the queue for human agents (static name or dynamic ID) |
| **Contact Priority** | Optional, 1–9 (1 = highest), default 10 |
| **Skills** | Optional skill-based routing with relaxation |

**Important:** The `$(conversationId)` variable must come from the Create Conversation node. If this variable is missing or empty, the Queue Task will fail.

### Queue Task Exit Paths

| Exit | When | Route To |
|------|------|----------|
| `Queued` | Task successfully queued for an agent | End |
| `onError` | General processing error | Error handling → End |
| `onInvalidData` | Invalid field values supplied | Error handling → End |
| `onInvalidChoice` | Invalid queue or media channel selection | Error handling → End |
| `onauthorizationfail` | Node not authorized | Error handling → End |
| `taskFailed` | Task creation failed | Error handling → End |
| `onTimeout` | Queue Task timed out | Error handling → End |

---

## 10. Error and Timeout Handling

Wire the AI Agent node's `onError` and `onTimeOut` exits:

### onError Path

1. Log error details (use an Evaluate or HTTP node to capture diagnostics)
2. Optionally send a "sorry, try again" message via the channel reply node
3. Route to End

### onTimeOut Path

1. Send a "please wait" message via the channel reply node
2. Optionally retry the AI Agent call (route back to AI Agent node)
3. Or route to End

The AI Agent node has a **15-second per-call timeout**. Frequent timeouts indicate agent complexity or action flow latency issues.

---

## 11. Save and Make Live

1. Click **Save** in the Flow Builder toolbar
2. Click **Make Live** — the flow must be live to receive inbound messages
3. Verify the channel asset is linked to the flow

**Both the parent conversation flow AND all action flows must be Made Live.** A common failure: the parent flow works but actions don't fire because the action flow is still in draft.

---

## 12. Complete Flow Example: WhatsApp AI Agent

```
Start (WhatsApp - Incoming Message)
  |  message: $(n1.whatsapp.message)
  |  customer: $(n1.whatsapp.waId)
  v
Search Conversation (by waId)
  |
  +-- _conversationActive  --> Append Conversation
  |                               |
  +-- _noConversationFound --> Create Conversation --> $(conversationId)
  |                               |
  +-- _conversationClosed  --> Reopen Conversation
  |                               |
  v-------------------------------+
  |
AI Agent (Process Message)
  |  agent: "Property Assistant"
  |  message: $(n1.whatsapp.message) [first turn]
  |           $(n7.whatsapp.message) [subsequent turns from Receive node]
  |  sessionId: $(n5.SessionId) [pass back after first call]
  |
  +-- onSuccess ---------> WhatsApp Reply ($(n5.TextResponse))
  |                            |
  |                            v
  |                         Receive (WhatsApp)
  |                            |
  |                            +-- [loop back to AI Agent]
  |
  +-- onAgentHandover ----> Queue Task
  |                            media: Social
  |                            channel: WhatsApp
  |                            queue: "Support Team"
  |                            conversation: $(conversationId)
  |                            |
  |                            v
  |                           End
  |
  +-- onError ------------> WhatsApp Reply ("Sorry, please try again.")
  |                            |
  |                            v
  |                           End
  |
  +-- onTimeOut -----------> WhatsApp Reply ("One moment please...")
                               |
                               v
                              End
```

---

## 13. Testing

Test approach depends on channel:

| Channel | How to Test |
|---------|-------------|
| **WhatsApp** | Sandbox with registered test numbers |
| **SMS** | Sandbox SMS Receive tab |
| **Live Chat** | Embed widget script on a test page |
| **Email** | Send to the configured inbound email address |
| **FB Messenger** | Requires production Page asset — no sandbox available |
| **Apple Messages** | Requires Apple Business Register enrollment — no sandbox available |

### Debug Tools

| Tool | Purpose |
|------|---------|
| **Flow Debug** (bug icon in Flow Builder) | Node-by-node execution logs with input/output variables |
| **Transaction logs** | Error codes and variable values per node |
| **AI Agent Studio** | Transaction history, session metadata — use "Hide test sessions" filter |

### Verification Checklist

- AI agent responds correctly to customer messages
- Multi-turn conversation works (SessionId maintained across turns)
- Actions (fulfillment flows) fire correctly when the agent needs data
- Escalation routes to Queue Task → human agent receives the conversation
- Rich content renders appropriately for the channel
- Error and timeout paths handle gracefully

---

## 14. Known Gotchas

| Issue | Fix |
|-------|-----|
| AI Agent returns empty response | Check Message Variable — must map to the correct channel message field (e.g., `$(n1.whatsapp.message)` not `$(n1.sms.message)`) |
| Escalation fails / Queue Task error | Ensure Create Conversation ran before Queue Task; pass `$(conversationId)` — if missing, Queue Task fails silently |
| Engage nodes unauthorized | Authorize Webex CC Task and Engage nodes in Connect (Control Hub) |
| Actions don't fire | Ensure action flows are Made Live in Connect — parent flow live is not enough |
| Session context lost between messages | Store `SessionId` from first AI Agent call and pass it on every subsequent call via the Receive loop |
| Response sent on wrong channel | Use the channel-specific reply node matching the Start trigger — do not mix channel nodes |
| Rich content not rendering | Use `FullResponse` instead of `TextResponse` for rich elements; `TextResponse` is text-only |
| `onTimeOut` fires frequently | Check agent complexity, action flow latency — the AI Agent node has a 15-second per-call timeout |
| Flow doesn't trigger on inbound message | Channel asset not linked to service, or flow not Made Live |
| Custom data not available for autonomous agents | Custom Parameters and MessageMetadata are only available for scripted agents on digital channels |
| Confused about AI Agent node vs Virtual Agent V2 | AI Agent node is in Connect (digital). Virtual Agent V2 is in Flow Designer (voice). They are different nodes on different platforms. |

---

## References

- [AI Agent Node](https://help.webexconnect.io/docs/ai-agent-node)
- [Integrate AI Agent with Voice and Digital Channels](https://help.webex.com/en-us/article/s0qro1/Integrate-AI-Agent-with-Voice-and-Digital-channels)
- [Set up Digital Channels](https://help.webex.com/en-us/article/n954r0k/Set-up-digital-channels-in-Webex-Contact-Center)
- [Queue Task Node](https://help.webexconnect.io/docs/queue-task)
- [Create Conversation Node](https://help.webexconnect.io/docs/create-conversation-1)
- [Start Node](https://help.webexconnect.io/docs/start-node)
- [Receive Node](https://help.webexconnect.io/docs/receive)
- [Webex CC Engage Nodes](https://help.webexconnect.io/docs/wxcc-engage-node-palette)
- [WxCC Flow Templates](https://help.webexconnect.io/docs/wxcc-flow-configuration-using-sample-templates)
- Full architecture reference: `docs/reference/digital-inbound.md`
