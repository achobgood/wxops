# Digital Inbound Agent -- Quick Reference

## Flow Structure

```
Start (Channel Trigger) -> Search Conversation -> Create/Append Conversation -> AI Agent (Process Message) -> Channel Reply -> Receive -> [Loop] -> Queue Task (escalation) -> End
```

## Channel Triggers

| Channel | Channel Section | Start Trigger | Message Variable | Customer ID |
|---------|----------------|--------------|------------------|-------------|
| SMS | Mobile Originated | Mobile Originated - MO | `$(n1.sms.message)` | `$(n1.sms.senderNumber)` |
| WhatsApp | WhatsApp | Incoming Message | `$(n1.whatsapp.message)` | `$(n1.whatsapp.waId)` |
| Live Chat | Mobile & Web App | Incoming Message | `$(n1.inappmessaging.message)` | `$(n1.inappmessaging.userId)` |
| Email | Email | Incoming Message | `$(n1.email.message)` | `$(n1.email.emailId)` |
| FB Messenger | Messenger | Incoming Message | `$(n1.messenger.message)` | `$(n1.messenger.psId)` |
| Apple Messages | Apple Messages for Business | Incoming Message | `$(n1.abc.message)` | `$(n1.abc.abcUserId)` |

## AI Agent Node (Process Message)

### Input Fields

| Field | Value |
|-------|-------|
| Method | Process Message |
| Agent Type | Scripted or Autonomous |
| Agent | Select from AI Agent Studio dropdown |
| Message Variable | Channel-specific: `$(n1.{channel}.message)` (first turn), `$(nX.{channel}.message)` (subsequent — no `.receive.` segment) |
| Channel | Channel name string (e.g., "WhatsApp", "SMS") |
| User Identifier | Channel-specific customer ID |
| Custom Parameters | Optional key-value pairs (scripted agents only on digital) |

### Output Variables

| Variable | Description |
|----------|-------------|
| `TextResponse` | Text-only response (first text item from agent reply) |
| `FullResponse` | Complete response array including rich elements (carousels, quick replies, etc.) |
| `SessionId` | Conversation session ID -- MUST store and reuse on every subsequent call |
| `Datastore` | Session variables JSON |
| `ConsumerId` | Customer identifier from AI Agent Studio |
| `TransactionId` | Transaction identifier |
| `MessageMetadata` | Metadata about the inbound message |
| `SessionMetadata` | Session-level metadata from the agent |
| `ResponsePayload` | Full response payload from the agent |

### Exit Paths

| Path | Routes To |
|------|-----------|
| onSuccess | Channel Reply -> Receive -> Loop back to AI Agent |
| onAgentHandover | Queue Task -> End |
| onError | Error handling -> End |
| onTimeOut | Timeout handling -> End |
| onInvalidCustomerID | Error handling -> End |
| onInvalidMessage | Error handling -> End |

## Queue Task Node

| Field | Value |
|-------|-------|
| Task ID | `$(flid)` |
| Conversation ID | `$(conversationId)` -- from Create Conversation node |
| Media Type | `Social` (SMS, WhatsApp, FB, Apple) / `Email` / `Chat` (Live Chat) |
| Media Channel | Dropdown: select matching originating channel |
| Queue | Select target queue |
| Contact Priority | 1-9 (optional, default 10) |

### Queue Task Exit Paths

| Exit | When | Route To |
|------|------|----------|
| `Queued` | Task successfully queued | End |
| `onError` | General processing error | Error handling -> End |
| `onInvalidData` | Invalid field values | Error handling -> End |
| `onInvalidChoice` | Invalid queue or media channel | Error handling -> End |
| `onauthorizationfail` | Node not authorized | Error handling -> End |
| `taskFailed` | Task creation failed | Error handling -> End |
| `onTimeout` | Queue Task timed out | Error handling -> End |

## Queue Task vs Queue Contact

| Aspect | Queue Task | Queue Contact |
|--------|-----------|---------------|
| Used for | Digital channels | Voice channels |
| Platform | Webex Connect node | WxCC Flow Designer activity |
| Trigger | onAgentHandover from AI Agent node | Escalated from Virtual Agent V2 |
| Key inputs | Task ID, Conversation ID, Media Type, Channel, Queue | Queue name/ID |
| Node palette | Webex CC Engage | Flow Designer built-in |

## Voice vs Digital Side-by-Side

| Aspect | Voice | Digital |
|--------|-------|---------|
| Orchestration | WxCC Flow Designer | Webex Connect Flow Builder |
| AI Agent node | Virtual Agent V2 | AI Agent (Process Message) |
| Selecting the agent | In the Virtual Agent V2 activity: pick `Webex AI Agent Autonomous` / `Webex AI Agent Scripted` from its **Contact Center AI Config** dropdown, then pick the agent. Nothing is created in Control Hub — that flow is Google CCAI, a different product [`ai-agent-studio.md` § CCAI Config] | In the AI Agent node: select the agent directly |
| Escalation | Queue Contact | Queue Task |
| Action flows | Same (channel-agnostic) | Same (channel-agnostic) |
| Entry Point type | Telephony | Social Channel |

## Channel Reply Nodes

| Channel | Reply Node | Destination Field | Message Field |
|---------|-----------|-------------------|---------------|
| SMS | SMS | `$(n1.sms.senderNumber)` | `$(nX.TextResponse)` |
| WhatsApp | WhatsApp | `$(n1.whatsapp.waId)` | `$(nX.TextResponse)` |
| Live Chat | In-App Messaging | `$(n1.inappmessaging.userId)` | `$(nX.TextResponse)` |
| Email | Email | `$(n1.email.emailId)` | `$(nX.TextResponse)` |
| FB Messenger | Messenger | `$(n1.messenger.psId)` | `$(nX.TextResponse)` |
| Apple Messages | Apple Messages for Business | `$(n1.abc.abcUserId)` | `$(nX.TextResponse)` |

Use `$(nX.FullResponse)` instead of `$(nX.TextResponse)` for rich content. Set Wait For to **Gateway Submit** on all reply nodes.

## Rich Response Types

Text, Carousel, Quick Reply, Image, Video, Audio, File, Reply Button, List Messages, Numbered List, Rich Link, Form, List Picker, Time Picker

### Channel-Specific Rich Capabilities

| Channel | Supported Rich Content |
|---------|----------------------|
| WhatsApp | Text, templates, images, video, documents, list messages, reply buttons |
| SMS | Text only (MMS for images) |
| Live Chat | Text, cards, quick replies, forms |
| Email | HTML with attachments |
| FB Messenger | Text, images, cards, quick replies |
| Apple Messages | Rich links, list pickers, time pickers, forms |

## Webex Engage Conversation Nodes

| Node | Purpose | Key Output |
|------|---------|-----------|
| Search Conversation | Check if conversation exists for customer | 5 exits: `_noConversationFound`, `_conversationActive`, `_conversationClosed`, `_conversationInQueue`, `_conversationOnHold` |
| Create Conversation | Creates new conversation thread | `$(conversationId)` -- required for Queue Task |
| Append Conversation | Appends message to existing thread | Maintains conversation continuity |

**Engage nodes require authorization** -- navigate to Assets → Integrations → Pre-built Integrations → Actions → Manage → Node Authorizations. Requires Contact Center License and Admin role.

## Multi-Turn Session Management

| Layer | Mechanism | Tracks |
|-------|-----------|--------|
| AI Agent Studio | `SessionId` | Slots, context, intent history, fulfillment results |
| Connect flow | Flow variables + Receive loop | Flow-level variables, loop iteration |
| Webex Engage | Conversation ID | WxCC conversation thread for agent handoff |

### Timeouts and Limits

| Constraint | Value |
|-----------|-------|
| Per-call timeout | 15 seconds (triggers onTimeOut) |
| Rate limit | 240 transactions per minute (default) |

## Entry Point Configuration (Digital)

| Field | Value |
|-------|-------|
| Channel Type | Social Channel |
| Social Channel Type | Specific channel (SMS, WhatsApp, Chat, etc.) |
| Asset Name | Maps to channel asset configured in Connect |

Digital entry points do NOT link to Flow Designer flows. The flow is determined by the channel asset configuration in Connect.

## Testing

| Channel | How to Test |
|---------|------------|
| WhatsApp | Sandbox with registered test numbers |
| SMS | Sandbox SMS Receive tab |
| Live Chat | Embed widget script on a test page |
| Email | Send to the configured inbound email address |

Debug tools: Flow Debug (bug icon) for node-by-node logs, Transaction logs for variable inspection, AI Agent Studio transaction history.

## Gotchas

| Issue | Cause | Fix |
|-------|-------|-----|
| Empty AI Agent response | Wrong message variable | Use correct channel-specific variable from triggers table |
| Escalation fails | Missing `$(conversationId)` | Ensure Create Conversation runs before Queue Task; pass `$(conversationId)` to Queue Task |
| Engage nodes unauthorized | Node authorization not completed | Assets → Integrations → Pre-built Integrations → Actions → Manage → Node Authorizations (requires Contact Center License + Admin role) |
| Actions don't fire | Action flows not Made Live | Make Live in Connect |
| Context lost between turns | SessionId not passed back | Store and reuse SessionId on every loop iteration |
| Wrong reply channel | Mismatched reply node | Reply node must match Start trigger channel |
| Rich content not rendering | Using TextResponse | Parse FullResponse for rich elements |
| onTimeOut fires frequently | Agent response exceeds 15s | Check agent complexity, reduce action flow latency |
| Custom Parameters ignored | Using autonomous agent | Custom Parameters only work with scripted agents on digital |
| Flow doesn't trigger | Flow not Made Live | Click Make Live after saving |
| Variable arrives empty | Typed manually | Use the variable picker -- never type variable references |
