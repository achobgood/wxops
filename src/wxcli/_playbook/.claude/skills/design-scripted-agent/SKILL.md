---
name: design-scripted-agent
description: |
  Design a scripted AI agent's intents, entities, responses, and context flow
  BEFORE building it in AI Agent Studio. Interviews the user and produces a
  design document that fills Section 4d of the ai-agent-design-doc template,
  including fulfillment planning for digital and voice channels.
  Use for: designing a scripted agent's conversation architecture BEFORE
  building it — this is the design phase (design-scripted-agent →
  configure-scripted-agent → build-scripted-fulfillment).
  NOT for: building the agent (configure-scripted-agent), fulfillment wiring
  (build-scripted-fulfillment), autonomous agents (configure-ai-agent).
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [interview-summary or requirements text]
---

# Design Scripted Agent Workflow

> **Autonomous agent, or type not settled?** This skill designs scripted agents. For an autonomous agent, or when the user has not yet settled which type, the `design-ai-agent` skill runs the interview (it asks the agent-type question and writes the design doc); an autonomous agent is then built with `build-action` → `configure-ai-agent` → `build-digital-inbound`, in that order.

## Step 1: Load references

YOU MUST use the Read tool on each of these files **sequentially (one at a time)** — do NOT read them in parallel. Do not proceed to Step 2 until all reads are complete.

1. Read `docs/playbooks/scripted-agent-design.md` — the design methodology (intent planning, entity design, response authoring, context flow mapping, fulfillment planning)
2. Read `docs/reference/ai-agent-studio-scripted.md` — scripted agent platform reference (AI engines, entity types, context rules, response variables)
3. Read `docs/templates/ai-agent-design-doc.md` — the template this skill fills out (Section 4d for scripted agents)

**Checkpoint — do NOT proceed until you can answer these from the docs you just loaded:**

- Q1: What entity types are available and when should each be used?
- Q2: What is the response variable syntax for entity values vs eventStore vs extra_params?
- Q3: What sections does the ai-agent-design-doc.md template's Section 4d require?
- Q4: What are the context flow rules (max entry/exit contexts, duration meaning)?

If you cannot answer all four, re-read the docs. Do not proceed to Step 2.

## Step 2: Receive requirements or existing design

This skill operates in two modes:

### Mode A: Existing design doc (validate and update)

Check if an argument path was passed, or use the Glob tool to check `docs/plans/*.md` for a design doc that has Section 4d populated (intents table, entities table, context flow, slot design, response templates).

If a design doc exists:
1. Read it in full
2. Validate each intent has 3+ utterances (10+ recommended)
3. Validate entity types match the Entity Type Selection Guide from the playbook
4. Validate context chains are connected (no orphaned entry contexts without a matching exit context)
5. Validate every fulfillment intent has a fulfillment plan entry
6. Present findings to the user and fix validated issues
7. Proceed to Step 7 (Review and save)

### Mode B: Fresh design (from interview answers or direct requirements)

This skill receives interview answers directly from the user (or from the agent running it, such as `wxops`). These include the use case, channel, agent type (already confirmed as Scripted), escalation triggers, database backend, and outbound notification needs.

The skill still needs to interview the user about scripted-agent-specific design decisions. Ask these **one at a time** — present one, wait for the answer, then ask the next.

Proceed to Step 3.

## Step 3: Define the agent's purpose

If not already provided from the interview:

> "Let's define what your scripted agent does in one sentence:
> 'This agent helps [who] do [what] on [channel].'
> For example: 'This agent helps patients book, reschedule, and cancel appointments on voice.'
> What's yours?"

This becomes the **Agent Goal** in AI Agent Studio.

## Step 4: Interview — Intents

> "List every action a customer should be able to perform with this agent. Each action becomes an 'intent.' For example:
> - Book an appointment
> - Check appointment status
> - Cancel an appointment
>
> What actions should your agent handle?"

After receiving the intent list:

1. For each intent, ask:
   > "For the **[intent_name]** intent — what are 3-5 example phrases a customer might say to trigger this? I'll generate additional variations. Also, does this intent need to call an API or database (fulfillment)?"

2. Build the intent planning table with: Intent Name, Description, Utterances, Needs Fulfillment, Entry Contexts (ask about prerequisites), Exit Contexts (ask about follow-ups)

Ask about context chains:
> "Do any of these intents depend on another being completed first? For example, should 'confirm booking' only be available after 'book appointment'? Or are all intents available from the start?"

## Step 5: Interview — Entities and Slots

For each intent, identify what data needs to be collected:

> "For the **[intent_name]** intent, what information does the agent need to collect from the customer? For example: date, time, phone number, appointment type, etc."

For each entity:
1. Determine the entity type using the Entity Type Selection Guide from the playbook
2. Determine if the slot is required
3. Draft the slot prompt (what the agent asks to collect it)
4. Set retry count (recommend 2-3)

Build the entity table and slot design table.

## Step 6: Interview — Responses

For each intent, draft the response the agent gives after completing it:

> "When the **[intent_name]** intent completes, what should the agent say? I'll draft the response using the collected data. For example:
> 'Your appointment is confirmed for ${entity.appointment_date} at ${entity.appointment_time}.'
>
> Do you need different response formats for different channels (e.g., buttons on WhatsApp, plain text on SMS)?"

Also draft:
- **Welcome message**: The agent's greeting
- **Fallback message**: What the agent says when it doesn't understand
- **Escalation message**: What the agent says when transferring to a human

Build the response planning table with template keys, channel variants, and conditional responses.

## Step 7: Design fulfillment plan

For each intent that needs fulfillment (API calls):

> "For **[intent_name]**, what API endpoint should the agent call? What data goes in (from the collected entities) and what comes back?"

Build the fulfillment planning table:
- Intent, Template Key, API Endpoint, Method, Input, Output, Channel Pattern

Include the channel pattern distinction:
- **Digital**: Branch on template_key → HTTP → Evaluate → Channel Reply
- **Voice**: Custom Event → Flow Designer HTTP → state_update

## Step 8: Map context flow

Using the intent dependencies from Step 4:

1. Draw the context flow diagram showing how intents chain
2. Set duration values for each exit context (recommend 3-5 turns for short chains, 5+ for longer ones)
3. Validate no orphaned contexts exist

## Step 9: Validate the design

Before generating the design document, check:

1. **Every intent has 3+ utterances** (10+ recommended for Pro 2.0)
2. **Every required slot has a prompt response** with a template key
3. **Entity types are appropriate** (not Custom list when a System type exists)
4. **Context chains are connected** (every entry context has a matching exit context from another intent)
5. **Fulfillment plan is complete** for every intent marked "Needs Fulfillment"
6. **System responses are customized** (welcome, fallback, escalation)
7. **Channel-specific variants exist** for channels the agent will use

If any check fails, go back and ask the user for the missing information.

## Step 10: Generate the design document

Re-read `docs/templates/ai-agent-design-doc.md` before generating — context compression may have evicted the template structure.

Fill in the design document:

### Section 1: Purpose
- Agent name, what it does, who it serves

### Section 2: Agent Metadata
- Agent Name, Agent Type (Scripted), Channel(s), Entry Point, Queue, Team

### Section 3: Database Backend
- Type, Base URL, Auth, Schema (from interview Q7)

### Section 4d: Scripted Agent Configuration
- **Intents table**: all intents with descriptions, utterances, entities, template keys, fulfillment flag, contexts
- **Entities table**: all entities with types, descriptions, example values, used-by intents
- **Context Flow diagram**: visual context chain
- **Slot Design table**: per-intent slots with required flag, retries, prompt text
- **Response Templates table**: all responses with template keys, channel, response type, text
- **Fulfillment Plan table**: API details for fulfillment intents

### Section 4b: Outbound Notifications (if applicable)
### Section 4c: Digital Inbound Flow Architecture (if applicable)

### Section 6: Welcome Message
### Section 7: WxCC Routing Plan

Present the complete design doc to the user for review. Do not save it until they approve.

## Step 11: Save and handoff

After user approval:

1. Save the design doc to `docs/plans/YYYY-MM-DD-{agent-name}-design.md` (use today's date). If the file exceeds 150 lines, write in chunks.
2. Tell the user what to do next:

> "Your design doc is saved at `docs/plans/[path]`. Next steps:
> 1. **Configure the agent**: Run `/configure-scripted-agent` to set up intents, entities, and responses in AI Agent Studio
> 2. **Build fulfillment** (if any intents need API calls): Run `/build-scripted-fulfillment` for each fulfillment intent
> 3. **Build digital inbound** (if using a digital channel): Run `/build-digital-inbound` for the conversation flow
>
> Would you like to proceed with configuring the agent now?"

---

## ANTI-HALLUCINATION GUARD

Every entity type, response variable syntax, context rule, and platform detail in your output MUST appear verbatim in the docs you loaded in Step 1. If you are about to write something you did not read in the docs:

1. STOP and say "I don't have that documented — would you like me to do a web search to find the correct answer?"
2. Wait for the user's response before proceeding.
3. If they approve, use the WebSearch tool to find the answer.
4. Mark web search results as `[FROM WEB SEARCH — not yet in project docs]`.

Do not invent plausible-sounding platform details under any circumstances.
