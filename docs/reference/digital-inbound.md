# Webex Connect — Digital Inbound Agent Architecture

<!-- ref-tag: digital-inbound-v3 -->

How digital channels (SMS, WhatsApp, Live Chat, Email, Facebook Messenger, Apple Messages) connect to AI Agent Studio through Webex Connect for inbound customer conversations. This is the digital equivalent of the voice inbound path (Virtual Agent V2 in Flow Designer). For digital, the entire flow lives in Webex Connect — Flow Designer is not used.

**Prerequisites:** This document assumes familiarity with `webex-connect.md` (core flow concepts), `wxcc-platform.md` (WxCC routing and entry points), and `ai-agent-studio.md` (agent configuration and deployment).

---

## Voice vs Digital Inbound — Side-by-Side

| Aspect | Voice | Digital |
|--------|-------|---------|
| **Entry Point type** | Telephony | Social Channel |
| **Flow orchestration** | WxCC Flow Designer | Webex Connect Flow Builder |
| **AI Agent integration** | Virtual Agent V2 node | AI Agent node (Process Message) |
| **CCAI Config required** | Yes | No (agent selected directly in node) |
| **Escalation** | Queue Contact (Flow Designer) | Queue Task (Connect node) |
| **Action flows** | Same (channel-agnostic) | Same (channel-agnostic) |

Key difference: Voice uses two platforms (Flow Designer for routing, Connect for actions). Digital uses one platform (Connect for everything — routing, AI Agent interaction, channel I/O, and escalation).

---

## End-to-End Flow Diagram

```
Customer sends message (SMS / WhatsApp / Chat / Email)
  |
  v
Webex Connect: Start node (channel-specific trigger)
  |
  v
Search Conversation (Webex Engage) — branch on conversation state (5 exits)
  |
  +-- _noConversationFound -> Create Conversation (outputs $(conversationId))
  |
  +-- _conversationActive --> Append Conversation
  |
  +-- _conversationClosed --> Reopen Conversation (or Create Conversation)
  |
  +-- _conversationInQueue -> handle or log (already queued for an agent)
  |
  +-- _conversationOnHold --> handle or log (conversation is on hold)
  |
  v
AI Agent node (Process Message)
  |
  +-- onSuccess ---------> Channel Reply node --> Receive node --> [loop to AI Agent]
  |
  +-- onAgentHandover ---> Queue Task node --> End
  |
  +-- onError -----------> Error handling --> End
  |
  +-- onTimeOut ----------> Timeout handling --> End
```

The Receive node waits for the customer's next message, then loops back to the AI Agent node for multi-turn conversation handling.

---

## Node-by-Node Configuration

### 1. Start Node

Channel-specific triggers determine which message fields are available:

| Channel | Start Trigger | Message Variable | Customer ID Variable |
|---------|--------------|------------------|---------------------|
| **Voice** | Voice - Inbound Call | N/A (voice has no text message) | `$(n1.voice.msisdn)` |
| **Voice** | Voice - Missed Call | N/A | `$(n1.voice.msisdn)` |
| **SMS** | SMS - Mobile Originated | `$(n1.sms.message)` | `$(n1.sms.senderNumber)` |
| **WhatsApp** | WhatsApp - Incoming Message | `$(n1.whatsapp.message)` | `$(n1.whatsapp.waId)` |
| **Live Chat** | Mobile & Web App - Incoming Message | `$(n1.inappmessaging.message)` | `$(n1.inappmessaging.userId)` |
| **Email** | Email - Incoming Message | `$(n1.email.message)` | `$(n1.email.emailId)` |
| **FB Messenger** | Messenger - Incoming Message | `$(n1.messenger.message)` | `$(n1.messenger.psId)` |
| **Apple Messages** | Apple Messages for Business - Incoming Message | `$(n1.abc.message)` | `$(n1.abc.abcUserId)` |

Each label above is written as `Channel Section - Trigger Name` — in the Start node the channel section and the trigger are two separate selections, not one hyphenated label. The section/trigger split per channel is in `docs/playbooks/digital-inbound-agent.md` § 3 Start Node Configuration.

⚠ **Messenger `psId` casing is unconfirmed.** The value `$(n1.messenger.psId)` is preserved as written, but `psId` vs `psid` was **not** confirmed from Cisco's Start node page (tracked as Not Verifiable #6 in `docs/tests/findings/digital-inbound-agent-findings.md`). Confirm the exact casing in the Webex Connect variable picker on your tenant before hard-coding it.

> ⚠ **OPEN QUESTION — the SMS trigger name is UNRESOLVED. Do not rely on the SMS row above.**
>
> Three spellings of the SMS Start trigger are live in this repo: `SMS - Mobile Originated - MO`, `Mobile Originated - MO`, and `SMS - Mobile Originated` (the value in the table above). The value above is preserved verbatim and has **not** been corrected, because no verified label was available. Tracked as **open item O5** in `docs/plans/2026-07-25-documentation-remediation-backlog.md` § 6 "Open items requiring tenant or platform access". Resolving it requires reading the literal label out of the Webex Connect Start node trigger picker on the tenant — do not settle it from the other two spellings, from majority use in this repo, or from memory.

**Voice note:** Voice inbound in WxCC typically uses **Flow Designer** (Virtual Agent V2 node), not a Connect Start trigger. The Voice Start triggers listed above are for Connect-native voice flows (e.g., outbound voice, IVR-only flows). For the standard WxCC voice inbound path, see `wxcc-platform.md`.

Each channel has a unique variable namespace. The message variable feeds into the AI Agent node; the customer ID variable feeds into conversation management and reply routing.

**Note:** The Start triggers above are channel-level events in Webex Connect — they work in any flow type, not only AI Agent conversation flows. You can use SMS - Mobile Originated (⚠ unresolved spelling — see the O5 note above), WhatsApp - Incoming Message, Email - Incoming Message, Messenger - Incoming Message, Apple Messages for Business - Incoming Message, and Mobile & Web App - Incoming Message as triggers for standalone processing flows that have no AI Agent node, no Engage conversation nodes, and no Receive loop. See `docs/playbooks/inbound-sms.md` for an example.

### Live Chat: Passing Custom Data from Website

The Live Chat widget (`imichatwidget`) supports injecting custom data from the hosting webpage into the Connect flow. This enables pre-populating customer name, email, account ID, or any context the website already knows.

**Widget-side JavaScript (on the hosting webpage):**

```javascript
const wait = setInterval(() => {
    if (typeof imichatwidget === "undefined") return;
    if (typeof imichatwidget.on === "undefined") return;
    clearInterval(wait);
    imichatwidget.on("imichat-widget:ready", () => {
        imichatwidget.init(
            JSON.stringify({
                "custom_chat_fields": {
                    "name": "Jane Smith",
                    "email": "jane@example.com"
                }
            }), () => {});
    });
}, 250);
```

The polling pattern (250ms `setInterval`) is required because the widget loads asynchronously.

**Flow-side variable:** `$(nX.inappmessaging.message.extras)` — contains the injected data as a nested JSON string.

**Parsing in an Evaluate node (double-parse required):**

```javascript
try {
    const extras = JSON.parse("$(n2.inappmessaging.message.extras)");
    const data = JSON.parse(extras.custom_chat_attr);
    customer_name = data.name;
    customer_email = data.email;
} catch(e) {}
0;
```

**Key gotcha:** The website sends data under key `custom_chat_fields`, but it arrives in Connect as `custom_chat_attr`. This naming transformation happens internally — parse `extras.custom_chat_attr`, not `extras.custom_chat_fields`.

**API reference:** [docs.imi.chat/reference/imichatwidgetinit](https://docs.imi.chat/reference/imichatwidgetinit)

---

### 2. Search Conversation Node (Webex CC Engage)

- Looks up an existing conversation by the customer's channel identifier
- Branches on conversation state — **five exits**, not a binary found / not-found split:

| Exit | Wire to |
|------|---------|
| `_noConversationFound` | Create Conversation node |
| `_conversationActive` | Append Conversation node |
| `_conversationClosed` | Reopen Conversation node (or Create Conversation if reopen is not available) |
| `_conversationInQueue` | Handle or log — the conversation is already queued for an agent |
| `_conversationOnHold` | Handle or log — the conversation is on hold |

This node is from the **Webex CC Engage** palette in Connect (full palette name: **Webex CC Engage Integration Nodes, Data Streams, and Node Authorizations**). Engage nodes require separate authorization (see [WxCC Digital Channel Setup](#wxcc-digital-channel-setup-8-steps) below).

---

### 3. Create Conversation Node (Webex CC Engage)

- Creates a new conversation in Webex Engage
- Output: `$(conversationId)` — the conversation ID required by Queue Task for escalation. ⚠ **The literal output variable name is not documented by Cisco.** The Create Conversation node page documents no literal output variable; `$(conversationId)` is the **default value of the Queue Task node's Conversation ID field** [https://help.webexconnect.io/docs/wxcc-queue-task], and this repo carries it forward as the Create Conversation output on that basis. Confirm the actual variable name in the Webex Connect variable picker before relying on it. (Tracked as Not Verifiable #1 in `docs/tests/findings/digital-inbound-agent-findings.md`; the same hedge is in `docs/playbooks/digital-inbound-agent.md` § 5.)
- Links the conversation to the customer's channel identifier

---

### 4. Append Conversation Node (Webex CC Engage)

- Appends the inbound message to an existing conversation thread
- Maintains continuity for returning customers within the same conversation window

---

### 4b. Fetch Conversation Transcript Node (Webex CC Engage)

Retrieves the full message history of a conversation. This is a method on the **Update Conversation** node (Engage palette), not a separate node type.

**Setup:** Drag an Update Conversation node → set **Method Name** to `Fetch transcript` → set **Authorization** to Default Authentication configured in Webex Engage's Integrations screen.

| Field | Details |
|-------|---------|
| **Method Name** | `Fetch transcript` (dropdown on Update Conversation node) |
| **Authorization** | Node Runtime Authorization — use Default Authentication from Webex Engage Integrations |
| **Conversation ID** | `$(conversationId)` — from Create Conversation node |
| **Offset** | Number of records to skip (for pagination) |
| **Limit** | Max records to return. Maximum: 500, default: 10 |

#### Output Variables

| Variable | Description |
|----------|-------------|
| `transcriptJsonEsc` | Escaped JSON payload containing the message array |
| `countOfRecords` | Total message count for this conversation |
| `status` | `Success` or `Failure` |
| `apiStatus` | HTTP status code from Webex Engage API |
| `code` | Numeric code from Webex Engage response |
| `description` | Description text from API response |
| `responsePayload` | Raw JSON API response |

#### Exit Paths

| Exit | When |
|------|------|
| `success` | Transcript retrieved successfully |
| `onTimeout` | No API response within timeout window |
| `onInvalidData` | Misconfigured node parameters |
| `onError` | Middleware service failure |
| `onInvalidChoice` | Invalid selection |
| `onauthorizationfail` | Authorization issue — recheck Authorize Integration settings in Connect |
| `Failure` | Other runtime failures |

**When to use:** This node is not part of the standard inbound conversation loop. Use it when you need to read back the conversation history — primarily for cross-channel escalation (e.g., passing chat transcript to a voice agent via CJDS). See `docs/playbooks/cross-channel-escalation.md`.

---

### 5. AI Agent Node (Process Message)

This is the core integration point. Same node type as the AI Agent trigger used in action flows, but configured differently for inbound conversation handling.

#### Input Fields

| Field | Details |
|-------|---------|
| **Agent Type** | Scripted or Autonomous |
| **Agent** | Select specific agent from AI Agent Studio dropdown |
| **Message Variable** | Customer message: `$(n1.whatsapp.message)` on first turn, `$(nX.{channel}.message)` on subsequent turns (from the Receive node — there is no `.receive.` path segment) |
| **Channel** | Originating channel name |
| **User Identifier** | Channel-specific customer ID |
| **Custom Parameters** | Optional key-value pairs for customer profile data. Read inside the agent as `${consumerData.extra_params.<key>}`. ⚠ This repo previously stated these are scripted-agents-only on digital; that restriction is **not documented in the official AI Agent node docs** — verify against the tenant before relying on it |
| **Message Parameters** | Optional per-exchange metadata. Read inside the agent as `${extra_params.<key>}`. ⚠ Same unverified scripted-only caveat as Custom Parameters |

**Parameter syntax warning:** Custom Parameters and Message Parameters are read with `${...}`, which is **not** the `$(...)` Webex Connect variable-picker syntax used everywhere else in this document. Source: https://help.webexconnect.io/docs/ai-agent-node

#### Output Variables

| Variable | Description |
|----------|-------------|
| `TextResponse` | Text-only response (first text item from the agent's reply) |
| `FullResponse` | Complete response array including rich elements (carousels, quick replies, etc.) |
| `SessionId` | Conversation session ID for multi-turn continuity |
| `Datastore` | Session variables JSON |
| `ConsumerId` | Customer identifier from AI Agent Studio |
| `TransactionId` | Transaction identifier |
| `MessageMetadata` | Metadata about the inbound message |
| `SessionMetadata` | Session-level metadata from the agent |
| `ResponsePayload` | Full response payload from the agent |

#### Exit Paths

| Exit | Canvas colour | When |
|------|---------------|------|
| `onSuccess` | Green | Agent responded successfully — send reply and continue conversation |
| `onAgentHandover` | Green | Agent escalated to human — route to Queue Task |
| `onError` | Red | Processing failed — handle gracefully |
| `onInvalidCustomerID` | Red | Customer identifier is invalid or missing — handle gracefully |
| `onInvalidMessage` | Red | Message format is invalid — handle gracefully |
| `onTimeOut` | Amber | 15-second per-call timeout exceeded — notify customer |

---

### 6. Channel Reply Node

- Use the channel-specific send node matching the Start trigger (SMS node for SMS, WhatsApp node for WhatsApp, etc.)
- **Destination:** Customer's channel identifier from the Start node
- **Message:** `$(nX.TextResponse)` for text-only, or parse `$(nX.FullResponse)` for rich content
- Wire `onSuccess` to the Receive node to continue the conversation loop

---

### 7. Receive Node

- Waits for the customer's next message on the same channel
- Configured for the same channel type as the Start node
- Output: `$(nX.{channel}.message)` for subsequent messages (e.g. `$(nX.whatsapp.message)`, `$(nX.sms.message)`) — there is no `.receive.` path segment
- Loops back to the AI Agent node for the next turn

---

### 8. Queue Task Node (Digital Escalation)

| Field | Value |
|-------|-------|
| **Task ID** | `$(flid)` — flow transaction ID |
| **Conversation ID** | `$(conversationId)` — from Create Conversation node |
| **Media Type** | `Social` (SMS, WhatsApp, FB, Apple), `Email`, or `Chat` (Live Chat) |
| **Media Channel** | Dropdown matching originating channel |
| **Queue** | Static queue name or dynamic queue ID |
| **Contact Priority** | 1–9 (1 = highest), default 10. Optional. |
| **Skills** | Optional skill-based routing with relaxation |

#### Exit Paths

| Exit | When |
|------|------|
| `Queued` | Task successfully queued for an agent |
| `onError` | General processing error |
| `onInvalidData` | Invalid field values supplied |
| `onInvalidChoice` | Invalid queue or media channel selection |
| `onauthorizationfail` | Node not authorized |
| `taskFailed` | Task creation failed |
| `onTimeout` | Queue Task timed out |

Wire at minimum `onError`, `taskFailed`, and `onTimeout` to an error-handling path — an unwired failure exit leaves the customer with no escalation and no message.

---

## Queue Task vs Queue Contact

| Aspect | Queue Task | Queue Contact |
|--------|-----------|---------------|
| **Used for** | Digital channels | Voice channels |
| **Platform** | Webex Connect node | WxCC Flow Designer activity |
| **Trigger** | `onAgentHandover` from AI Agent node | `Escalated` from Virtual Agent V2 |
| **Key inputs** | Task ID, Conversation ID, Media Type, Channel, Queue | Queue name/ID |
| **Media Type values** | `Social`, `Email`, `Chat` | N/A (voice implied) |

---

## Actions in Digital Context

Action flows (a trigger node with the **AI Agent** trigger category, which presents as **Configure AI Agent Event** → HTTP Request → Flow Outcomes configured in Flow Settings, not as a canvas node) are **channel-agnostic**. The same action flow works for both voice and digital conversations. AI Agent Studio triggers the action flow automatically when the agent needs fulfillment data.

What differs is the **parent conversation flow**:

| Parent Flow | Platform | AI Integration Node |
|-------------|----------|-------------------|
| Voice | WxCC Flow Designer | Virtual Agent V2 |
| Digital | Webex Connect | AI Agent node + Receive loop |

No changes are needed to existing action flows to support digital channels. An action built for voice works identically when the conversation originates from WhatsApp, SMS, or any other digital channel.

---

## Multi-Turn Conversation Handling

Three layers of state work together:

| Layer | Mechanism | Tracks |
|-------|-----------|--------|
| **AI Agent Studio** | `SessionId` | Slots, context, intent history, fulfillment results |
| **Connect flow** | Flow variables + Receive loop | Flow-level variables, loop iteration |
| **Webex Engage** | Conversation ID | WxCC conversation thread for agent handoff |

### Session Management

- `SessionId` is generated on the first Process Message call
- Pass it back on all subsequent calls to maintain conversation continuity
- Use the AI Agent node's **Close Session** method to explicitly end a session

### Timeouts and Limits

| Constraint | Value |
|-----------|-------|
| **Per-call timeout** | 15 seconds (triggers `onTimeOut` exit) |
| **Session timeout** | Not published by Cisco — sessions close after an unspecified period of inactivity |
| **Rate limit** | 240 transactions per minute (default, can be increased) |

---

## Rich Message Support

AI Agent Studio supports rich response types on digital channels:

- Text, Carousel, Quick Reply, Image, Video, Audio, File
- Reply Button, List Messages, Numbered List
- List Picker, Time Picker (Apple Messages)
- Rich Link, Form

These come back in the `FullResponse` output variable. `TextResponse` only returns the first text item.

### Channel-Specific Rich Capabilities

| Channel | Rich Content Support |
|---------|---------------------|
| **WhatsApp** | Text, templates, images, video, documents, list messages, reply buttons |
| **SMS** | Text only (MMS for images) |
| **Live Chat** | Text, cards, quick replies, forms |
| **Email** | HTML with attachments |
| **FB Messenger** | Text, images, cards, quick replies |
| **Apple Messages** | Rich links, list pickers, time pickers, forms |

The Connect flow must convert `FullResponse` to channel-appropriate formats. Sending an unsupported rich type to a channel (e.g., a carousel to SMS) will fail or render as plain text.

---

## WxCC Digital Channel Setup (8 Steps)

1. **Provision Webex Engage and Connect** — Control Hub > Tenant Settings > Digital
2. **Authorize nodes** — Authorize the Webex CC Task and Webex CC Engage nodes in Webex Connect: Assets → Integrations → Pre-built Integrations → Actions → Manage → Node Authorizations. The authorizing user must have a Contact Center License and Admin role.
3. **Set up agents** — Configure agents with multimedia profiles, sites, teams
4. **Configure RONA** — Set Redirection on No Answer timeout for digital channels
5. **Create channel assets** — Assets > Apps in Connect (channel-specific)
6. **Create Entry Points and Queues** — Entry Points (Social Channel type) and Queues in WxCC
7. **Design channel templates** — Configure channel templates in Webex Engage
8. **Build digital inbound flows** — Create flows in Connect Flow Builder

---

## Entry Point Configuration (Digital)

| Field | Value |
|-------|-------|
| **Channel Type** | Social Channel |
| **Social Channel Type** | Specific channel (SMS, WhatsApp, Chat, etc.) |
| **Asset Name** | Maps to channel asset configured in Connect |

Digital entry points do **NOT** link to Flow Designer flows. The flow is determined by the channel asset configuration in Connect. This is fundamentally different from voice, where the entry point links directly to a Flow Designer flow.

---

## Caveats and Limitations

| Limitation | Details |
|-----------|---------|
| **Custom data/events for autonomous agents** | Voice channel ONLY — not available for digital autonomous agents. Custom data at session start and custom event fulfillment require Flow Designer (voice path). See `docs/reference/ai-agent-studio.md` "Custom Data at Session Start" and "Custom Event Fulfillment". For scripted agents on digital, use Custom Parameters instead. |
| **MessageMetadata / SessionMetadata** | ⚠ **UNVERIFIED** — this repo previously stated these are available only for scripted agents on digital, not autonomous. That restriction is **not documented in the official AI Agent node docs**; verify against the tenant before relying on it. Both are listed as AI Agent node output variables without an agent-type qualifier |
| **Webex Engage dependency** | Digital inbound requires Webex Engage provisioned. Engage nodes need separate authorization in Connect. |
| **Multiple Queue Task paths** | Use separate sub-flows for different queue routing based on intent |
| **No Flow Designer** | WxCC Flow Designer is not used for digital inbound — the entire flow lives in Connect |

---

## Testing Digital Inbound Flows

### Sandbox

Available for SMS and WhatsApp (combined 10,000 lifetime requests, 5 test numbers).

### Debug Tools

| Tool | Purpose |
|------|---------|
| **Flow Debug** (bug icon in Flow Builder) | Node-by-node execution logs |
| **Transaction logs** | Input/output variables, error codes per node |
| **AI Agent Studio** | Transaction history, session metadata. Use "Hide test sessions" filter. ⚠ Repo record — the "Hide test sessions" filter was **not** confirmed in Cisco's published pages (Not Verifiable #4 in `docs/tests/findings/digital-inbound-agent-findings.md`). Guidance retained; confirm the control name in the Studio UI. |

### Per-Channel Testing

| Channel | How to Test |
|---------|------------|
| **WhatsApp** | Sandbox with registered test numbers |
| **SMS** | Sandbox SMS Receive tab |
| **Live Chat** | Embed widget script on a test page |
| **Email** | Send to the configured inbound email address |

---

## Known Gotchas

| Issue | Cause | Fix |
|-------|-------|-----|
| AI Agent node returns empty response | Wrong Message Variable — not mapped to channel's message field | Use correct variable: `$(n1.whatsapp.message)` for WhatsApp, `$(n1.sms.message)` for SMS, etc. |
| Escalation fails / Queue Task error | Missing Conversation ID | Ensure Create Conversation runs before Queue Task; pass `$(conversationId)` |
| Engage nodes unauthorized | Node authorization not completed | In Webex Connect: Assets → Integrations → Pre-built Integrations → Actions → Manage → Node Authorizations. Authorize the Webex CC Task and Webex CC Engage nodes. The authorizing user must have a Contact Center License and Admin role. |
| Actions not firing from digital | Action flow not Made Live | Ensure action flows are live in Connect. ⚠ Repo record — Cisco's published pages do **not** state that a draft action flow fails to fire until separately Made Live (Not Verifiable #5 in `docs/tests/findings/digital-inbound-agent-findings.md`). Guidance retained as a first check, not a confirmed cause. |
| Response sent on wrong channel | Channel reply node misconfigured | Use channel-specific reply node matching the Start trigger |
| Session context lost between messages | SessionId not passed back | Store SessionId from first AI Agent call and pass it on all subsequent calls |
| Rich content not rendering | TextResponse used instead of FullResponse | Parse `FullResponse` for rich elements; `TextResponse` is text-only |
| onTimeOut fires frequently | AI Agent Studio response exceeds 15 seconds | Check agent complexity, action flow performance, reduce fulfillment latency |
| `wxcc-platform.md` mentions "AI Agent node" in Flow Designer | Misleading — AI Agent node is in Connect, not Flow Designer | VAV2 = voice (Flow Designer), AI Agent = digital (Connect) |

---

## References

- [AI Agent Node](https://help.webexconnect.io/docs/ai-agent-node)
- [Integrate AI Agent with Voice and Digital channels](https://help.webex.com/en-us/article/s0qro1/Integrate-AI-Agent-with-Voice-and-Digital-channels)
- [Set up Digital Channels](https://help.webex.com/en-us/article/n954r0k/Set-up-digital-channels-in-Webex-Contact-Center)
- [Queue Task Node](https://help.webexconnect.io/docs/queue-task)
- [WxCC Flow Templates](https://help.webexconnect.io/docs/wxcc-flow-configuration-using-sample-templates)
- [WxCC Overview in Connect](https://help.webexconnect.io/docs/wxcc-overview)
- [Webex CC Engage Nodes](https://help.webexconnect.io/docs/wxcc-engage-node-palette)
- [Create Conversation Node](https://help.webexconnect.io/docs/create-conversation-1)
- [Configure Fulfillment for AI Agent Actions](https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions)
- [AI Agent Studio Admin Guide](https://help.webex.com/en-us/article/ncs9r37/Webex-AI-Agent-Studio-Administration-guide)
- [Configure Custom Events for AI Agents](https://help.webex.com/en-us/article/n5uo60x/Configure-custom-events-for-AI-agents)
- [Webex Contact Center Architecture](https://help.webex.com/en-us/article/utqcm7/Webex-Contact-Center-Architecture)
- [Start Node](https://help.webexconnect.io/docs/start-node)
- [Receive Node](https://help.webexconnect.io/docs/receive)

## See Also

- [wxcc-platform.md](wxcc-platform.md) — the channel, entry point and queue setup that inbound digital flows depend on
- [webex-connect.md](webex-connect.md) — the Connect flow basics the inbound start node builds on
- [ai-agent-studio.md](ai-agent-studio.md) — the AI agent that handles the conversation
- [digital-inbound-agent.md](../playbooks/digital-inbound-agent.md) — the build steps that pair with this reference
