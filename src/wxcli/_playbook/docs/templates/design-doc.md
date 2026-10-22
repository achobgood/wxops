# [Agent Name] -- Design Document

> **DEPRECATED:** This template is replaced by two purpose-specific templates:
> - **AI Agent builds** (autonomous + scripted): use `docs/templates/ai-agent-design-doc.md`
> - **Flow Designer voice flows**: use `docs/templates/flow-designer-design-doc.md`
>
> This file is preserved for reference. Existing design docs in `docs/plans/` that use this format remain valid.

Created: [YYYY-MM-DD]

## 1. Purpose

[What the AI agent does, who it serves, what problem it solves]

## 2. Channel(s) & Agent Type

- **Agent Type**: [Autonomous / Scripted]
- [ ] Voice
- [ ] Chat
- [ ] SMS

## 3. Database Backend

- Type: [Supabase / Firebase / Custom REST API / etc.]
- Connection: [MCP server configured / manual schema provided]
- Schema summary:

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| | | |

## 4. Actions (Autonomous) / Intents (Scripted)

**If Autonomous — Actions table:**

| # | Action Name | Input Entities | DB Query | Returns | Status |
|---|-------------|---------------|----------|---------|--------|
| 1 | | | | | pending |
| 2 | | | | | pending |
| 3 | | | | | pending |

**If Scripted — use Section 4d below instead.**

## 4b. Outbound Notification Flows (if applicable)

Outbound notification flows are webhook-triggered and do not involve AI Agent Studio. They are built separately from inbound agent actions using the `build-notification` skill (multi-channel) or `build-outbound-flow` skill (voice-only).

| # | Flow Name | Trigger Event | Channel(s) | Webhook Payload | DB Lookup? | Message Summary | Status |
|---|-----------|--------------|------------|-----------------|------------|-----------------|--------|
| O1 | | | SMS / Email / Voice / RCS / Apple / WhatsApp / Multi | | | | pending |

## 4c. Digital Inbound Flow Architecture (if applicable)

Digital inbound flows handle customer-initiated conversations on messaging channels (SMS, WhatsApp, Apple Messages, etc.) where an AI agent converses in real time.

- **Digital Channel(s)**: [SMS / WhatsApp / Apple Messages / Web Chat / Facebook Messenger / etc.]
- **Rich Responses Needed**: [Yes / No — if yes, specify: buttons, quick replies, rich cards, list pickers]
- **Escalation Queue**: [queue name for handoff to live agent on digital channel]

**Flow Structure:**

```
Start (channel event) → Engage (lock conversation) → AI Agent (process message)
  → Reply (send response) → Receive (wait for next customer message) → [loop back to AI Agent]
  → Queue Task (on escalation trigger)
```

| Node | Purpose | Key Settings |
|------|---------|-------------|
| Start | Receives inbound message from digital channel | Channel asset configured |
| Engage | Locks the conversation to this flow instance | Prevents duplicate processing |
| AI Agent | Sends customer message to AI Agent Studio, gets response | Agent ID, conversation ID for context continuity |
| Reply | Sends agent response back to customer on same channel | Uses channel-appropriate reply node |
| Receive | Waits for next customer message (keeps flow alive) | Timeout configurable (e.g., 15 min inactivity) |
| Queue Task | Escalates to human agent via WxCC queue | Triggered by AI agent escalation signal or timeout |

**Conversation Context:**
- Conversation ID maps to channel session (e.g., WhatsApp thread, SMS thread)
- AI Agent Studio maintains context across the Engage → AI Agent → Reply → Receive loop
- Each loop iteration sends the new customer message with the same conversation ID

## 4d. Scripted Agent Configuration (if agent type is Scripted)

Scripted agents define behavior through intents, entities, and responses — not through LLM instructions or actions.

### Intents

| # | Intent Name | Description | Utterance Examples (3+) | Required Entities | Needs Fulfillment? | Entry Contexts | Exit Contexts | Status |
|---|-------------|-------------|------------------------|-------------------|-------------------|----------------|---------------|--------|
| 1 | | | | | | | | pending |
| 2 | | | | | | | | pending |
| 3 | | | | | | | | pending |

### Entities

| Entity Name | Type | Description | Example Values | Used By Intents |
|-------------|------|-------------|----------------|----------------|
| | | | | |

### Context Flow

```
[intent_1] --(exit: "context_name")--> [intent_2] --(exit: "context_name")--> [intent_3]
```

### Slot Design (Per Intent)

| Intent | Slot (Entity) | Required? | Retries | Prompt Text |
|--------|--------------|-----------|---------|-------------|
| | | | | |

### Response Templates

| Template Key | Intent/Slot | Channel | Response Type | Response Text/Description |
|-------------|-------------|---------|---------------|--------------------------|
| `welcome` | (system) | All | Text | |
| `fallback` | (system) | All | Text | |
| | | | | |

### Fulfillment Plan (for intents needing API calls)

| Intent | Template Key | API Endpoint | Method | Input (from entities) | Output (to response) | Channel Pattern |
|--------|-------------|-------------|--------|----------------------|---------------------|----------------|
| | | | | | | Digital: Branch on template_key / Voice: Custom Event |

## 5. Agent Instructions (Draft) (Autonomous Only)

> **Scripted agents:** Skip this section. Scripted agents do not have an Instructions/system prompt. Behavior is fully defined by intents, entities, responses, and context management in Section 4d.

Write instructions covering:

- **Identity and greeting**: Who the agent is, how it should sound
- **First action**: What MUST happen before anything else (e.g., identity verification)
- **Action sequence**: How to walk through each capability naturally
- **Timezone handling**: If DB returns UTC, specify conversion (e.g., "subtract 5 hours for Eastern")
- **Escalation triggers**: When to hand off to a human agent
- **Ground rules**: What the agent must NOT do — domain-specific restrictions (e.g., no unauthorized commitments, no guessing)
- **Tone**: Conversational, not robotic. Short sentences. One question at a time.

```
[Draft instructions here]
```

## 6. Welcome Message

This is a separate field in AI Agent Studio -- not part of the instructions. It is the first thing the caller hears.

```
[Welcome message here]
```

## 7. WxCC Routing Plan

- **Entry Point**: [name, channel type (Telephony / Chat / Email)]
- **Flow**: [Virtual Agent V2 (voice) / AI Agent node in Connect (digital)]
- **Queue**: [queue name, team assignment]
- **Escalation**: [triggers and queue routing for handoff to human]
- **CCAI Config**: [config name linking deployed agent to WxCC]

## 8. Build Checklist

### Autonomous Agent Build Checklist

| # | Action | Curl Test | Connect Flow | AI Studio Config | End-to-End Test | Status |
|---|--------|-----------|-------------|-----------------|-----------------|--------|
| 1 | | [ ] | [ ] | [ ] | [ ] | pending |
| 2 | | [ ] | [ ] | [ ] | [ ] | pending |
| 3 | | [ ] | [ ] | [ ] | [ ] | pending |

### Scripted Agent Build Checklist

| # | Step | Details | Status |
|---|------|---------|--------|
| S1 | Create agent | Scripted type, AI engine selected | pending |
| S2 | Create entities | All entity definitions | pending |
| S3 | Create intents | Utterances, slots, contexts | pending |
| S4 | Create responses | Per-channel, conditional rules | pending |
| S5 | Test (Chat Preview) | All intents, slots, fallback | pending |
| S6 | Build fulfillment | Per-intent API calls (digital: Branch on template_key / voice: Custom Event) | pending |
| S7 | Test fulfillment | Curl test + end-to-end | pending |
| S8 | Publish + Deploy | CCAI Config (voice) or AI Agent node (digital) | pending |

### Outbound Flow Build Checklist (if applicable)

| # | Flow | Webhook Test | Connect Flow | Delivery Validated | End-to-End Test | Status |
|---|------|-------------|-------------|-------------------|-----------------|--------|
| O1 | | [ ] | [ ] | [ ] | [ ] | pending |

### Build Order

**For autonomous inbound agent actions**, follow this sequence:
1. Run curl test to verify the backend query works
2. Build the Webex Connect flow (HTTP nodes, output variables, Flow Outcomes)
3. Configure the action in AI Agent Studio (description, input entities, sample JSON, enable toggle)
4. Test end-to-end via voice preview
5. Update agent instructions to cover the new action
6. Update status tables in design doc and CLAUDE.md

**For scripted agents**, follow this sequence:
1. Create the agent in AI Agent Studio (Scripted type, select AI engine)
2. Create entities (all types needed across intents)
3. Create intents (utterances, slot linkages, context chains)
4. Create responses (per-channel, conditional variants, system response customization)
5. Test via Chat Preview (all intents, slot collection, fallback behavior)
6. Build fulfillment for intents needing API calls (use `build-scripted-fulfillment` skill)
7. Test fulfillment end-to-end (curl + chat/voice preview)
8. Publish and deploy (CCAI Config for voice, AI Agent node for digital)

**For outbound notification flows** (Section 4b), follow this sequence:
1. Configure webhook trigger and test with curl
2. Build the Connect flow using `build-notification` (multi-channel) or `build-outbound-flow` (voice-only)
3. Make Live and test webhook end-to-end
4. Validate delivery on target channel (SMS received, email delivered, RCS card rendered, etc.)
5. For RCS/Apple Messages: test fallback path (send to non-RCS device, or customer without active session)
6. Update status tables in design doc
