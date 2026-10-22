# [Agent Name] -- Design Document

Created: [YYYY-MM-DD]

## 1. Purpose

[What the AI agent does, who it serves, what problem it solves]

## 2. Agent Metadata

| Field | Value |
|-------|-------|
| Agent Name | [display name in AI Agent Studio] |
| Agent Type | Autonomous / Scripted |
| Channel(s) | Voice / SMS / WhatsApp / Live Chat / Email / [list all] |
| Entry Point Name | [EP name in Control Hub] |
| Entry Point Type | Telephony / Social Channel |
| Queue Name | [escalation queue] |
| Team | [team assigned to queue] |

## 3. Database Backend

- **Type**: [Supabase / Firebase / Custom REST API / BRE / etc.]
- **Base URL**: [API endpoint base]
- **Auth**: [header pattern — e.g., "apikey + Bearer token"]

### Schema

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| | | |

### Relationships

| FK Column | References | Cardinality |
|-----------|-----------|-------------|
| | | |

### Key Constraints

- **Primary keys**: [list auto-generated PKs — never used as caller input]
- **Unique columns**: [columns safe for exact-match lookup]
- **Timezone**: [UTC / other — specify conversion rule if needed]

## 4. Actions (Autonomous)

> Skip this section for Scripted agents — use Section 4d instead.

### Actions Table

| # | Action Name | Purpose | Input Entities | DB Query (Method + Table + Filter) | Returns | Status |
|---|-------------|---------|---------------|-------------------------------------|---------|--------|
| 1 | | | | | | pending |

### Action Descriptions

**Chained actions:** Some actions use output from a previous action instead of collecting input from the caller. For these:
- The **Input Entities table** still lists the entity (e.g., `patient_id`) because the Connect flow's Start node needs it in the sample JSON
- The **Entity Description** should say "Internal — auto-filled by the agent from a previous action's result. Not collected from the caller."
- The **Action Description** should NOT list it under "Requires:" — instead say "Requires: no caller input — uses the patient 'id' from verify_member."
- The **Required** toggle should still be **Yes** in AI Agent Studio — the LLM fills it from conversation context

This pattern applies whenever one action's return value feeds the next action's input. The caller never provides these values directly.

For each action, provide the formatted description for AI Agent Studio (max 1024 chars):

#### Action 1: [action_name]

```
Call this action when [trigger condition].
Requires: [entity_name] (collected from the caller).
Returns: "returned_var_1", "returned_var_2", "returned_var_3".
[How to use the returned data]
[Timezone note if times are returned]
```

**Sample JSON** (for Connect Start node → Provide sample JSON → Parse):

```json
{
  "entity_name": "example_value"
}
```

**Input Entities:**

| Entity Name | Entity Type | Entity Description | Entity Example | Required |
|-------------|-------------|-------------------|----------------|----------|
| | | | | |

[Repeat Action Description block for each action]

## 4b. Outbound Notification Flows (if applicable)

> Write "N/A" if no outbound notifications are needed.

| # | Flow Name | Trigger Event | Channel(s) | Webhook Payload Fields | DB Lookup? | Message Summary | Status |
|---|-----------|--------------|------------|------------------------|------------|-----------------|--------|
| O1 | | | | | | | pending |

## 4c. Digital Inbound Flow Architecture (if applicable)

> Skip this section for voice-only agents.

| Field | Value |
|-------|-------|
| Digital Channel | [SMS / WhatsApp / Live Chat / Email / etc.] |
| Rich Responses | Yes / No [if yes: buttons, quick replies, rich cards, list pickers] |
| Escalation Queue | [queue name] |
| Agent Node Type | Process Message |
| Message Variable (first turn) | [e.g., `$(n1.whatsapp.message)`] |
| Customer ID Variable | [e.g., `$(n1.whatsapp.waId)`] |
| Reply Node Type | [e.g., WhatsApp] |
| Response Source | TextResponse / FullResponse |

### Digital Flow Diagram

```
Start ({Channel} - Incoming Message)
  → Search Conversation → Create/Append/Reopen Conversation
  → AI Agent (Process Message)
    → onSuccess → {Channel} Reply → Receive → [loop to AI Agent]
    → onAgentHandover → Queue Task → End
    → onError → Error handler → End
    → onTimeOut → Timeout handler → End
```

## 4d. Scripted Agent Configuration (if agent type is Scripted)

> Skip this section for Autonomous agents.

### Intents

| # | Intent Name | Description | Utterances (3+) | Required Entities | Template Key | Needs Fulfillment? | Entry Contexts | Exit Contexts | Status |
|---|-------------|-------------|-----------------|-------------------|-------------|-------------------|----------------|---------------|--------|
| 1 | | | | | | | | | pending |

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

| Template Key | Intent/Slot | Channel | Response Type | Response Text |
|-------------|-------------|---------|---------------|---------------|
| `welcome` | (system) | All | Text | |
| `fallback` | (system) | All | Text | |
| | | | | |

### Fulfillment Plan (for intents needing API calls)

| Intent | Template Key | API Endpoint | Method | Input (from entities) | Output (to response) | Channel Pattern |
|--------|-------------|-------------|--------|----------------------|---------------------|----------------|
| | | | | | | Digital: Branch on template_key / Voice: Custom Event |

## 5. Agent Instructions (Autonomous Only)

> Scripted agents: skip this section. Behavior is defined by intents/entities/responses in Section 4d.

### 5.1 Identity

- **Role**: "You are a [role] for [organization]..."
- **Tone**: [conversational / formal / friendly-professional]

### 5.2 Context

- **Background**: [what the agent needs to know about the business/domain]
- **Environment**: [voice = background noise caveat; digital = typing delay acceptable]

### 5.3 Task (Action Sequence)

| Step | Action | Trigger | Returns | Agent Behavior |
|------|--------|---------|---------|----------------|
| 1 | verify_caller | ALWAYS first, no exceptions | "name", "account_id" | Greet by name |
| 2 | | | | |
| 3 | | | | |

### 5.4 Timezone Handling

- **DB timezone**: [UTC / other]
- **Caller timezone**: [e.g., Eastern Time]
- **Conversion rule**: [e.g., "subtract 5 hours for EST, 4 for EDT"]
- **Instruction**: "All times from the database are in UTC. You MUST convert to [timezone] before saying any time to the caller. Never mention UTC."

### 5.5 Escalation Triggers

| Trigger | Agent Says |
|---------|-----------|
| Caller asks for human | "Let me connect you with..." |
| Verification fails | "I wasn't able to find..." |
| Emergency / safety | [domain-specific] |
| Action error after retry | "I'm having trouble..." |
| | |

### 5.6 Ground Rules

- NEVER [domain-specific restriction 1]
- NEVER [domain-specific restriction 2]
- NEVER reveal internal IDs or database details
- NEVER guess at information — escalate instead

### 5.7 Conversation Style

- One to two sentences at a time
- Do not stack multiple questions
- Confirm before committing (read back details, wait for "yes")
- Natural transitions: "Let me check on that"
- Wrap up: "Is there anything else I can help with?"
- Sign off: "Thanks for calling, [Name]. Have a great day!"

## 6. Welcome Message

> Separate field in AI Agent Studio — not part of instructions.

```
[Welcome message text]
```

## 7. WxCC Routing Plan

| Field | Value |
|-------|-------|
| Entry Point | [name] |
| Entry Point Type | Telephony / Social Channel |
| PSTN Number | [voice only — number assigned to EP] |
| Flow Type | Virtual Agent V2 (voice) / AI Agent node in Connect (digital) |
| Flow Designer Flow Name | [voice only — flow name] |
| Escalation Queue | [queue name] |
| Escalation Team | [team name] |

### Custom Data at Session Start (voice only)

> Skip if the agent doesn't need IVR data before starting the conversation.

Variables passed from Flow Designer to the AI Agent via Virtual Agent V2 State Event Settings:

| Variable Name | Source | Purpose |
|---------------|--------|---------|
| caller_ani | `{{NewPhoneContact.ANI}}` | Caller's phone number for auto-verification |
| store_number | `{{storeNumber}}` (from IVR) | Store context for personalized greeting |

These variables are accessible in Agent Studio via `{{variable_name}}` syntax in the Agent Goal, Welcome Message, Instructions, and Action Descriptions (but NOT for Flow Outcomes return data — see Critical Rules).

### Voice Routing Path (voice only)

```
PSTN → Entry Point → Flow Designer Flow → Virtual Agent V2
  → Escalated → Queue Contact → Play Music → [agent answers]
  → Handled → Disconnect Contact
  → Errored → Play Message (error) → Disconnect Contact
```

### Digital Routing Path (digital only)

```
Channel Asset → Connect Flow → AI Agent (Process Message) → Channel Reply → Receive → [loop]
  → onAgentHandover → Queue Task → [human agent]
```

### Voice Flow Activities (for spec diagram generation)

| ID | Label | Activity Type | Key Configuration |
|----|-------|--------------|-------------------|
| 1 | NewPhoneContact | NewPhoneContact | (start) |
| 2 | AIAgent | Virtual Agent V2 | CCAI Config: [config name] |
| 3 | QueueEscalation | Queue Contact | Queue: [escalation queue] |
| 4 | HoldMusic | Play Music | File: Default; Duration: 600 |
| 5 | ErrorMsg | Play Message | TTS: "We're experiencing technical difficulties. Goodbye." |
| 6 | Disconnect | Disconnect Contact | (terminal) |
| 7 | DisconnectHandled | Disconnect Contact | (terminal) |
| 8 | DisconnectError | Disconnect Contact | (terminal) |

> Customize this table if the voice flow is more complex (e.g., pre-IVR data dip, custom data at session start, post-call survey).

### Voice Flow Connections

| Source Activity | Port | Target Activity |
|----------------|------|-----------------|
| NewPhoneContact | Out | AIAgent |
| AIAgent | Handled | DisconnectHandled |
| AIAgent | Escalated | QueueEscalation |
| AIAgent | Error | ErrorMsg |
| QueueEscalation | Default | HoldMusic |
| HoldMusic | Default | Disconnect |
| ErrorMsg | Default | DisconnectError |

> Only include rows for activities actually in the voice flow.

## 8. Build Checklist

### Autonomous Agent Build Checklist

| # | Action | Curl Test | Connect Flow | AI Studio Config | End-to-End Test | Status |
|---|--------|-----------|-------------|-----------------|-----------------|--------|
| 1 | | [ ] | [ ] | [ ] | [ ] | pending |

### Scripted Agent Build Checklist

| # | Step | Details | Status |
|---|------|---------|--------|
| S1 | Create agent | Scripted type, AI engine selected | pending |
| S2 | Create entities | All entity definitions | pending |
| S3 | Create intents | Utterances, slots, contexts | pending |
| S4 | Create responses | Per-channel, conditional rules | pending |
| S5 | Test (Chat Preview) | All intents, slots, fallback | pending |
| S6 | Build fulfillment | Per-intent API calls | pending |
| S7 | Test fulfillment | Curl test + end-to-end | pending |
| S8 | Publish + Deploy | Virtual Agent V2 (voice) or AI Agent node (digital) | pending |

### Outbound Flow Build Checklist (if applicable)

| # | Flow | Webhook Test | Connect Flow | Delivery Validated | End-to-End Test | Status |
|---|------|-------------|-------------|-------------------|-----------------|--------|
| O1 | | [ ] | [ ] | [ ] | [ ] | pending |

### Digital Inbound Flow Checklist (if applicable)

| Step | Task | Status |
|------|------|--------|
| D1 | Channel asset created and registered to Webex Engage | pending |
| D2 | Entry Point created (Social Channel) | pending |
| D3 | Queue created with team assigned | pending |
| D4 | Engage and CC Task nodes authorized in Connect | pending |
| D5 | Digital inbound flow built | pending |
| D6 | Queue Task node configured for escalation | pending |
| D7 | Flow Made Live | pending |
| D8 | End-to-end test on channel | pending |

### Build Order

**For autonomous inbound agent actions**, follow this sequence:
1. Run curl test to verify the backend query works
2. Build the Webex Connect flow (HTTP nodes, output variables, Flow Outcomes)
3. Configure the action in AI Agent Studio (description, input entities, sample JSON, enable toggle)
4. Test end-to-end via voice preview
5. Update agent instructions to cover the new action
6. Update status tables in design doc

**For scripted agents**, follow this sequence:
1. Create the agent in AI Agent Studio (Scripted type, select AI engine)
2. Create entities (all types needed across intents)
3. Create intents (utterances, slot linkages, context chains)
4. Create responses (per-channel, conditional variants)
5. Test via Chat Preview
6. Build fulfillment for intents needing API calls (use `build-scripted-fulfillment` skill)
7. Test fulfillment end-to-end
8. Publish and deploy

**For outbound notification flows** (Section 4b), build AFTER all inbound actions are complete.

**For digital inbound flows** (Section 4c), build AFTER all action flows are built and live.
