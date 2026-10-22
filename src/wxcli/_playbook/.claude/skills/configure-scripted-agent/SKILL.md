---
name: configure-scripted-agent
description: |
  Configure a SCRIPTED AI agent in Webex AI Agent Studio. Walks through creating
  the agent, selecting the AI engine, intents with training phrases, entities and
  slot prompts, responses with template keys, context flow, testing, and deployment.
  Use for: configuring a scripted AI agent in Agent Studio. Mid-pipeline skill —
  run design-scripted-agent first to produce the design doc, then this skill.
  NOT for: autonomous agents (configure-ai-agent) or fulfillment wiring (build-scripted-fulfillment).
allowed-tools: Read, Grep, Glob
argument-hint: [agent-name]
---

# Configure Scripted Agent Workflow

> **Autonomous agents?** This skill is for scripted agents. Autonomous agents use a different architecture (actions with LLM-driven descriptions instead of intents/entities/responses). Use `configure-ai-agent` for autonomous agents.

## Step 1: Load references

YOU MUST use the Read tool on each of these files. Do not proceed to Step 2 until all reads are complete.

1. Read `docs/reference/ai-agent-studio-scripted.md` for scripted agent Studio conventions
2. Read `docs/playbooks/scripted-agent-build.md` for the step-by-step build playbook
3. Read this skill's `reference.md` for the quick-reference cheat sheet

**Checkpoint — do NOT proceed until you can answer these from the docs you just read:**
- What AI engines are available for scripted agents, and which is recommended? (from `ai-agent-studio-scripted.md`)
- What is the correct CCAI Config dropdown value for a scripted agent? (from `ai-agent-studio-scripted.md`)
- How do you reference entity values in response templates? (from `scripted-agent-build.md`)

If you cannot answer all three, you skipped Step 1. Go back and read the docs.

## Step 2: Confirm prerequisites

Before configuring in AI Agent Studio, verify:

- A design document exists with intents, entities, responses, and context flow mapped out
- The user knows what API endpoints fulfillment will call (if any intents need fulfillment)
- The user has access to AI Agent Studio (Control Hub > Contact Center > AI Agents)

If no design document exists, tell the user to run `design-scripted-agent` first — this skill configures from a design, it does not create the design.

## Step 3: Create the Agent — `[AI Agent Studio]`

1. Open **AI Agent Studio**
2. Click **Create Agent** — or start from a **built-in template** if one matches the use case:
   - **Doctor's Appointment**: 4 intents (check availability, book, lookup, cancel) with slots pre-configured
   - **Track Package**: single intent with package number extraction
   - Templates include pre-authored utterances, entities, and responses — customize rather than build from scratch
3. Select **Scripted**
4. Enter **Agent Name** and **Description**
5. Select **AI Engine** — scripted agents have exactly two options:
   - **Webex AI Pro 2.0 (with Swiftmatch)**: Cisco — "Each intent must include at least 10 representative utterances." Requires intent descriptions
   - **Webex AI Pro 1.0 (with Swiftmatch)**: Cisco — for "fewer than 10 utterances per intent" and multilingual agents
   - "MindMeld" and "Rasa" are NOT AI Agent Studio engines — that is Webex Connect Bot Builder terminology from a different product. See `reference.md` § AI Engines
6. Click **Create**

## Step 4: Configure Profile Settings — `[AI Agent Studio → Profile]`

Navigate to the **Profile** section and set:

| Setting | Value |
|---------|-------|
| **Agent Goal** | One sentence purpose statement from the design doc |
| **Timezone** | Match the organization's timezone |
| **Custom Error Message** | "I'm experiencing technical difficulties. Please try again in a moment." |

## Step 5: Create Entities — `[AI Agent Studio → Scripts → Entities]`

**Important:** Create entities BEFORE intents, since you'll link entities to intents as slots.

For each entity from the design doc:

1. Click **Create Entity**
2. Enter **Name** (lowercase_underscores: `appointment_date`)
3. Select **Type** (cannot be changed after creation) — Cisco documents six custom types:
   - **Custom list**: Add all valid values with synonyms
   - **Regex**: Enter the pattern (e.g., `[A-Z]{3}\d{6}`)
   - **Digits**: Set the expected length (fixed-length numeric, especially for voice)
   - **Alphanumeric**: Combinations of letters and numbers, for voice and nonvoice inputs
   - **Free form**: Flexible data points that are difficult to define or validate
   - **Map location (WhatsApp)**: Location data shared on the WhatsApp channel

   Eleven prebuilt (system) entities also exist — see `reference.md` § Entity Types.
4. Configure type-specific settings
5. Click **Save**

Present entities as a table for the user to copy:

| Entity Name | Type | Configuration |
|-------------|------|---------------|
| (from design doc) | (from design doc) | (values/pattern/length) |

## Step 6: Create Intents — `[AI Agent Studio → Scripts → Intents]`

For each intent from the design doc:

### 6a. Basic Configuration
1. Click **Create Intent**
2. Enter **Intent Name** (e.g., `book_appointment`)
3. Enter **Description** (mandatory for Pro 2.0 — helps NLU distinguish similar intents)

### 6b. Add Utterances
1. Add training phrases — minimum 3 (10+ recommended for Pro 2.0)
2. Use **Generate variants** button to auto-generate additional phrases
3. **Annotate entities** in utterances: highlight entity values and tag them with the correct entity name

### 6c. Link Slots
1. Click **+Link** to connect an entity as a slot
2. Configure each slot:
   - **Required**: Toggle ON for mandatory data
   - **Retries**: Set retry count (2-3 recommended)
   - **Response**: Select which response template prompts for this slot
   - **Update slot values**: Toggle ON if the user should be able to change their answer

### 6d. Configure Contexts
1. **Entry Contexts**: Add context values required for this intent to match
2. **Exit Contexts**: Add context values this intent activates when matched, with **Duration** (number of turns the context stays active)

### 6e. Intent Settings
- **Reset slots after completion**: Toggle ON if slot values should clear after the intent completes
- **End conversation**: Toggle ON for terminal intents (e.g., goodbye)

Present each intent as a configuration block for the user:

```
Intent: [name]
Description: [from design doc]
Utterances: [list 10+ training phrases]
Slots: [entity_name (Required: yes/no, Retries: N)]
Entry Contexts: [list or "none"]
Exit Contexts: [context_name (Duration: N turns)]
```

## Step 7: Create Responses — `[AI Agent Studio → Scripts → Responses]`

### 7a. Intent Completion Responses
For each intent, create the response delivered after all slots are collected:

1. Click **Create Response**
2. Set the **Template Key** (e.g., `booking_confirmed`)
3. Select channel (Web is default)
4. Choose response type (Text, Quick Reply, List Message, etc.)
5. Write the response text, using variables:
   - `${entity.appointment_date}` — collected slot values
   - `${extra_params.customer_name}` — message parameters from the flow
   - `${eventStore.confirmation_number}` — data from custom events (voice)

### 7b. Slot Prompt Responses
For each required slot, create the prompt response:

1. Create a response with a descriptive template key (e.g., `ask_date`)
2. Write the prompt: "What date would you like your appointment?"
3. Link this response to the slot in the intent configuration (Step 6c)

### 7c. Channel-Specific Variants
For each response, add channel-specific formats:

1. Click the **channel selector dropdown**
2. Select a channel (WhatsApp, Voice, SMS, etc.)
3. Configure channel-appropriate response:
   - **WhatsApp**: Reply Button for yes/no, List Message for multiple options
   - **Voice**: Text (spoken by TTS) or Custom Event (for fulfillment handoff)
   - **Apple Messages**: List Picker, Time Picker, Form
   - **SMS**: Plain text (keep concise)

### 7d. Customize System Responses
Edit the built-in system responses:

| System Response | Customize To |
|----------------|-------------|
| **Welcome message** | Agent greeting from the design doc |
| **Fallback message** | "I didn't understand that. Could you rephrase?" |
| **Partial message** | "Did you mean one of these?" |
| **Agent handover** | "Let me connect you with a team member." |

## Step 8: Configure AI Engine Settings — `[AI Agent Studio → Profile → AI Engine]`

Navigate to **Profile > AI Engine** and tune:

| Setting | Recommendation |
|---------|---------------|
| **Fallback threshold** | Start at default; lower if fallback fires too often |
| **Partial match threshold** | Start at default; adjust based on testing |
| **Spellcheck in inference** | ON for text channels; helps with typos |
| **Expand contractions** | ON (handles "don't" → "do not") |
| **Prioritize slot filling** | ON if entity extraction is more important than intent switching |

## Step 9: Test the Agent — `[AI Agent Studio → Preview]`

### 9a. Chat Preview
1. Click **Preview** > **Chat**
2. Click **Start a Chat**
3. Test each intent with trained utterances AND novel phrasing
4. Verify correct intent classification
5. Verify slot prompts fire in order
6. Verify responses display correctly

### 9b. Voice Preview
1. Click **Preview** > **Voice**
2. Grant browser microphone access (use a headset)
3. Speak utterances naturally
4. Verify speech recognition handles entity formats

### 9c. Test Checklist
Present this checklist to the user:

| Test | Expected Result |
|------|----------------|
| Each intent matches with trained utterances | Correct intent classification |
| Each intent matches with novel phrasing | Correct intent (tests NLU generalization) |
| Required slots prompt correctly | Agent asks for each missing slot |
| Slot retries work | Agent re-asks after invalid input |
| Context chains work | Follow-up intents only available after prerequisite |
| Fallback fires on gibberish | Agent says fallback message |
| "Talk to an agent" triggers handover | Agent escalates |
| Per-channel responses render correctly | WhatsApp buttons, lists, etc. display |

## Step 10: Publish and Deploy — `[AI Agent Studio + Flow Designer / Webex Connect]`

### 10a. Publish
1. In AI Agent Studio, click **Publish**
2. Add a version description
3. The published agent is now live and becomes selectable in the Flow Designer **Virtual Agent V2** activity's **Contact Center AI Config** dropdown (step 10c) — nothing is created anywhere

### 10b. No Control Hub step — Webex AI Agent is not Google CCAI
CCAI (Contact Center AI) is **Google's** product; Webex AI Agent is **Cisco's own**. Do **not** create anything in Control Hub for this agent.

- The Control Hub flow *Services > Contact Center > Tenant settings > Integrations > Features > New > Contact Center AI Config* exists for **Google CCAI / BYOVA / Agent Answers**. Its stated prerequisite is "Ensure that the service-specific integration connector is created. For example, **Google** Contact Center AI connector", and its Contact Center AI Connector field offers only "Webex CCAI", "Integration Connector", and "Service App" ([Cisco npbt02j](https://help.webex.com/en-us/article/npbt02j/Create-a-Contact-Center-AI-configuration)).
- For a Webex AI Agent, Cisco says only: "Select **Webex AI Agent Scripted** from the **Contact Center AI Config** drop-down list" — that dropdown is in the Flow Designer Virtual Agent V2 activity (step 10c) ([Cisco s0qro1](https://help.webex.com/en-us/article/s0qro1/)). Settled with the platform owner 2026-07-27.

A one-time tenant enablement is required before that dropdown entry appears (platform owner, 2026-07-27) — see [`wxcc-platform.md` § Webex AI Agent Tenant Prerequisite].

### 10c. Wire to Voice (Flow Designer)
1. Open your call flow in **WxCC Flow Designer**
2. Add a **Virtual Agent V2** activity
3. Select **"Webex AI Agent Scripted"** from the Contact Center AI Config dropdown
4. Select your published agent from the Virtual Agent dropdown
5. Wire output paths:
   - **Handled** → continue flow or end
   - **Escalated** → Queue Contact node
   - **Errored** → error handling
   - **Custom Event** → fulfillment logic (if applicable)

### 10d. Wire to Digital (Webex Connect)
1. Open your conversation flow in **Webex Connect**
2. In the **AI Agent** node:
   - Set Agent Type to **Scripted**
   - Select your agent
   - Configure Method: **Process Message**
3. Wire exit paths:
   - **onSuccess** → Channel Reply (with fulfillment branching if applicable)
   - **onAgentHandover** → Queue Task
   - **onError** → error handling

## Step 11: Present all config to user

Format everything for direct copy-paste into AI Agent Studio:

1. Agent Name and Description
2. AI Engine selection and rationale
3. Entity table (all entities with types and configuration)
4. Intent configurations (name, description, utterances, slots, contexts — one block per intent)
5. Response templates (template key, text, channel variants — one block per response)
6. System response customizations
7. AI Engine tuning settings
8. Test checklist
9. Deployment steps (Publish → wire to channel: Flow Designer Virtual Agent V2 for voice, Connect AI Agent node for digital)

---

## CRITICAL REMINDERS

- **Entity type cannot be changed after creation.** If wrong, delete and recreate.
- **Pro 2.0 requires intent descriptions.** Without them, similar intents get confused.
- **Minimum 3 utterances per intent, 10+ recommended.** Use Generate variants for more.
- **Create entities BEFORE intents** — you need them to link as slots.
- **Template keys must match** between responses and fulfillment branching (Data Parser checks `$.model_state.template_key`).
- **Context duration is in turns, not time.** A duration of 3 means the context stays active for 3 conversational turns.
- **Scripted agents do NOT use action descriptions or `{{variable_name}}` syntax** — that is the autonomous pattern.

## ANTI-HALLUCINATION GUARD

Every field name, UI location, configuration detail, and syntax rule in your output MUST appear verbatim in the docs you loaded in Step 1. If you are about to write something you did not read in the docs:

1. STOP and say "I don't have that documented — would you like me to do a web search to find the correct answer?"
2. Wait for the user's response before proceeding.
3. If they approve, use the WebSearch tool to find the answer from official Cisco/Webex documentation.
4. Present what you found and mark it as `[FROM WEB SEARCH — not yet in project docs]` so the user knows it hasn't been verified against the local reference.
5. Do NOT mix web search results into your output without that label.

Do not invent plausible-sounding platform details under any circumstances.
