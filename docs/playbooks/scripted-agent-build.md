# Scripted Agent Build Playbook

<!-- ref-tag: scripted-agent-build-v2 -->

## Overview

Step-by-step guide for building a scripted AI agent in Webex AI Agent Studio and wiring up fulfillment flows. Follow this after completing the design phase (`scripted-agent-design.md`).

**Prerequisites:**
- Design document complete (intents, entities, responses, context flow, fulfillment plan)
- AI Agent Studio access (Control Hub > Contact Center > AI Agents > AI Agent Studio)
- Webex Connect access (for digital channel fulfillment flows)
- WxCC Flow Designer access (for voice fulfillment flows)
- Database/API endpoints ready for fulfillment

---

## 1. Create the Agent

1. Open **AI Agent Studio**
2. Click **Create Agent** — or start from a **built-in template**:
   - **Doctor's Appointment**: 4 intents (check availability, book, lookup, cancel) with slot entities pre-configured
   - **Track Package**: single intent with package number extraction
   - Templates include pre-authored utterances, entities, and responses — customize rather than build from scratch
3. Select **Scripted**
4. Enter **Agent Name** and **Description**
5. Select **AI Engine**:
   - **Webex AI Pro 2.0 (with Swiftmatch)**: Cisco requires "at least 10 representative utterances" per intent; also requires intent descriptions
   - **Webex AI Pro 1.0 (with Swiftmatch)**: For "fewer than 10 utterances per intent", and for multilingual agents
   - ⚠ Cisco documents only these **two** engines for scripted agents [`ai-agent-studio-scripted.md` § AI Engines]. "MindMeld" and "RASA" are Webex Connect **Bot Builder** terminology — a different product — and were previously listed here in error. Cisco publishes no deprecation notice, so this does not mean they were removed.
6. Click **Create**

---

## 2. Configure Profile Settings

Navigate to the **Profile** section:

| Setting | Value |
|---------|-------|
| **Agent Goal** | Paste from design doc (one sentence purpose statement) |
| **Timezone** | Match your organization's timezone |
| **Custom Error Message** | "I'm experiencing technical difficulties. Please try again in a moment." |

---

## 3. Create Entities

Navigate to **Scripts > Entities**. Create all entities from your design doc.

For each entity:
1. Click **Create Entity**
2. Enter **Name** (lowercase_underscores: `appointment_date`)
3. Select **Type** (cannot be changed after creation)
4. Configure type-specific settings:
   - **Custom list**: Add all valid values with synonyms
   - **Regex**: Enter the pattern (e.g., `[A-Z]{3}\d{6}`)
   - **Digits**: Set the expected length
5. Click **Save**

**Important:** Create entities BEFORE intents, since you'll link entities to intents as slots.

---

## 4. Create Intents

Navigate to **Scripts > Intents**. Create each intent from your design doc.

For each intent:

### 4a. Basic Configuration
1. Click **Create Intent**
2. Enter **Intent Name** (e.g., `book_appointment`)
3. Enter **Description** (mandatory for Pro 2.0 -- helps NLU distinguish similar intents)

### 4b. Add Utterances
1. Add training phrases -- minimum 3 (10+ recommended for Pro 2.0)
2. Use **Generate variants** button to auto-generate additional phrases
3. **Annotate entities** in utterances: highlight entity values and tag them with the correct entity name
   - Example: "Book me in for **next Tuesday**" → annotate "next Tuesday" as `appointment_date`

### 4c. Link Slots
1. Click **+Link** to connect an entity as a slot
2. Configure each slot:
   - **Required**: Toggle ON for mandatory data
   - **Retries**: Set retry count (2-3 recommended)
   - **Response**: Select which response template prompts for this slot
   - **Update slot values**: Toggle ON if the user should be able to change their answer

### 4d. Configure Contexts
1. **Entry Contexts**: Add context values required for this intent to match (from design doc)
2. **Exit Contexts**: Add context values this intent activates when matched, with **Duration** (number of turns the context stays active)

### 4e. Intent Settings
- **Reset slots after completion**: Toggle ON if slot values should clear after the intent completes (prevents stale data on re-entry)
- **End conversation**: Toggle ON for terminal intents (e.g., goodbye)

### 4f. Save and Train
Click **Save**. The system retrains the NLU model automatically when you add or modify intents.

---

## 5. Create Responses

Navigate to **Scripts > Responses**. Create response templates for every agent message.

### 5a. Intent Completion Responses
For each intent, create the response the agent delivers after all slots are collected:

1. Click **Create Response** (or edit the auto-generated one)
2. Set the **Template Key** (e.g., `booking_confirmed`)
3. Select channel (Web is default)
4. Choose response type (Text, Quick Reply, List Message, etc.)
5. Write the response text, using variables:
   - `${entity.appointment_date}` -- collected slot values
   - `${extra_params.customer_name}` -- message parameters from the flow
   - `${eventStore.confirmation_number}` -- data from custom events (voice)

### 5b. Slot Prompt Responses
For each required slot, create the prompt response:

1. Create a response with a descriptive template key (e.g., `ask_date`)
2. Write the prompt: "What date would you like your appointment?"
3. Link this response to the slot in the intent configuration (Step 4c)

### 5c. Channel-Specific Variants
For each response, add channel-specific formats:

1. Click the **channel selector dropdown**
2. Select a channel (WhatsApp, Voice, SMS, etc.)
3. Configure channel-appropriate response:
   - **WhatsApp**: Reply Button for yes/no, List Message for multiple options
   - **Voice**: Text (spoken by TTS) or Custom Event (for fulfillment handoff)
   - **Apple Messages**: List Picker, Time Picker, Form
   - **SMS**: Plain text (keep concise)

### 5d. Conditional Responses
For responses that vary based on data:

1. Open the response in the Response Designer
2. Click **Add Rule**
3. Configure: IF `${entity.appointment_type}` equals "urgent" → different response text
4. Add OR/AND conditions as needed

### 5e. Customize System Responses
Edit the built-in system responses:

| System Response | Customize To |
|----------------|-------------|
| **Welcome message** | Your agent's greeting from the design doc |
| **Fallback message** | "I didn't understand that. Could you rephrase?" |
| **Partial message** | "Did you mean one of these?" |
| **Agent handover** | "Let me connect you with a team member." |

---

## 6. Configure Fulfillment (Voice)

For voice agents, use **Custom Events** to hand control to Flow Designer for API calls.

### 6a. Create Custom Event Response
1. In the intent's response, add a **Custom Event** response type (Voice channel)
2. Set the **Event Name** (e.g., `check_availability`)
3. Define the **Payload** with entity values:
   ```json
   {
     "date": "${entity.appointment_date}",
     "time": "${entity.appointment_time}",
     "type": "${entity.appointment_type}"
   }
   ```

### 6b. Wire Flow Designer
1. Open WxCC **Flow Designer**
2. In the **Virtual Agent V2** activity, wire the **Custom Event** output path
3. Add a **Parse** activity to extract event data
4. Add an **HTTP Request** activity to call your API
5. Add a **Condition** activity to check success/failure
6. Return data to the agent via a **state_update** event:

   **On success:**
   ```json
   {
     "intent": "booking_confirmed",
     "slots": {
       "confirmation_number": "ABC12345"
     }
   }
   ```

   **On failure (re-prompt for new time):**
   ```json
   {
     "intent": "book_appointment",
     "slots": {
       "time": ""
     }
   }
   ```

### 6c. Event Store Variables
Data returned via state_update is accessible in responses as `${eventStore.<variable_name>}`.

---

## 7. Configure Fulfillment (Digital)

For digital agents, fulfillment happens **inline** within the Webex Connect conversation flow.

### 7a. Build the Conversation Flow
Follow `docs/playbooks/digital-inbound-agent.md` for the base conversation flow structure. Then add fulfillment branching:

### 7b. Add Fulfillment Branching
After the AI Agent node, before the Channel Reply node:

1. **Data Parser** node: Extract `$.model_state.template_key` from the AI Agent node's SessionMetadata output
2. **Branch** node: Check the template_key value
   - If `template_key` = `"booking_confirmed"` → fulfillment path
   - If `template_key` = `"status_result"` → different fulfillment path
   - Default → send agent's TextResponse directly

### 7c. Fulfillment Path
For each template_key that requires an API call:

1. **Extract entity values** from SessionMetadata: `${lastdfState.model_state.entities.<entity_name>.value}`
2. **HTTP Request** node: Call your API with extracted entity values
3. **Evaluate** node: Process the API response, format the user-facing message
4. **Channel Reply** node: Send the formatted response to the user
5. **Append Conversation** node: Add the response to the conversation history
6. Wire back to the **Receive** node to continue the conversation loop

### 7d. Flow Sketch
```
AI Agent (Process Message)
  → Data Parser (extract template_key)
  → Branch:
    → "booking_confirmed":
        → HTTP POST /appointments (with entity values)
        → Evaluate (format confirmation message)
        → Channel Reply (send confirmation)
        → Append Conversation
        → Receive (wait for next message)
        → Loop back to AI Agent
    → "status_result":
        → HTTP GET /appointments?phone=X
        → Evaluate (format status message)
        → Channel Reply (send status)
        → Append Conversation
        → Receive → Loop
    → default:
        → Channel Reply (send TextResponse)
        → Receive → Loop
  → onAgentHandover:
        → Queue Task
```

---

## 8. Configure AI Engine Settings

Navigate to **Profile > AI Engine** and tune:

| Setting | Recommendation |
|---------|---------------|
| **Fallback threshold** | Start at default; lower if fallback fires too often |
| **Partial match threshold** | Start at default; adjust based on testing |
| **Spellcheck in inference** | ON for text channels; helps with typos |
| **Expand contractions** | ON (handles "don't" → "do not") |
| **Prioritize slot filling** | ON if entity extraction is more important than intent switching |

---

## 9. Test the Agent

### 9a. Chat Preview
1. Click **Preview** > **Chat**
2. Click **Start a Chat**
3. Test each intent:
   - Type utterances from your training set AND variations not in the set
   - Verify correct intent classification
   - Verify slot prompts fire in order
   - Verify responses display correctly

### 9b. Voice Preview
1. Click **Preview** > **Voice**
2. Grant browser microphone access (use a headset)
3. Speak utterances naturally
4. Verify speech recognition handles your entity formats
5. Test barge-in (interrupt the agent mid-response)

### 9c. Testing Framework
1. Navigate to the **Testing** section
2. Create test cases: define input messages and expected responses
3. Run the test suite
4. Review results -- scripted agents should be deterministic

### 9d. Test Checklist

| Test | Expected Result | Pass? |
|------|----------------|-------|
| Each intent matches with trained utterances | Correct intent classification | [ ] |
| Each intent matches with novel phrasing | Correct intent (tests NLU generalization) | [ ] |
| Required slots prompt correctly | Agent asks for each missing slot | [ ] |
| Slot retries work | Agent re-asks after invalid input | [ ] |
| Context chains work | Follow-up intents only available after prerequisite | [ ] |
| Fallback fires on gibberish | Agent says fallback message | [ ] |
| "Talk to an agent" triggers handover | Agent escalates | [ ] |
| Fulfillment returns correct data | API called, response formatted | [ ] |
| Per-channel responses render correctly | WhatsApp buttons, lists, etc. display | [ ] |

---

## 10. Publish and Deploy

### 10a. Publish
1. In AI Agent Studio, click **Publish**
2. Add a version description
3. The agent is now live and selectable in the **Contact Center AI Config** dropdown inside the Flow Designer **Virtual Agent V2** activity (step 10b) — you do not create anything to make it appear there

### 10b. Deploy Sequence (Voice) — No Control Hub Step
1. In **AI Agent Studio**, **Publish** the agent (step 10a) — the NLU model retrains automatically when intents or entities changed
2. In **WxCC Flow Designer**, open the **Virtual Agent V2** activity
3. In its **Contact Center AI Config** dropdown, select **"Webex AI Agent Scripted"**
4. Select your published agent

Do **not** create a Contact Center AI Config in Control Hub — that Control Hub flow belongs to a different product and is not part of a Webex AI Agent build [`ai-agent-studio-scripted.md` § Deployment].

**Prerequisite**: a one-time tenant enablement is required before "Webex AI Agent Scripted" appears in that dropdown [`wxcc-platform.md` § Webex AI Agent Tenant Prerequisite].

Continue to step 10c for the Virtual Agent V2 output-path wiring.

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

---

## 11. Post-Deployment

### Monitor with Curation Console
- Review **low-confidence** classifications in the Issues tab
- Identify patterns in fallback messages
- Create new intents or add utterances to handle common misses

### Iterate
- Add utterances as you discover new ways users phrase requests
- **Important:** The system retrains automatically when you add/update intents or entities
- Use the **Version History** tab to track changes and roll back if needed

### Export for Backup
- Use the **Export** option (ellipsis menu on agent card) to download the agent as JSON
- Store JSON backups before major changes

---

## 12. Known Gotchas

| Issue | Cause | Fix |
|-------|-------|-----|
| Entity type can't be changed | Entity type is locked after creation | Delete and recreate the entity with the correct type |
| Pro 2.0 requires intent descriptions | The LLM-enhanced engine uses descriptions to distinguish similar intents | Add a clear, unique description to every intent |
| Too few utterances → poor matching | NLU needs variety to generalize | Add 10+ utterances per intent; use **Generate variants** for more |
| template_key not found in fulfillment | Response doesn't have a template key set, or Data Parser path is wrong | Verify the response has a template key; check JSON path `$.model_state.template_key` |
| Custom Event not firing (voice) | Response type not set to Custom Event on Voice channel | In the Response Designer, select Voice channel and add a Custom Event response type |
| Slot not collected | Entity not linked as a Required slot on the intent | In the intent config, click +Link, toggle Required ON, set retry count |
| Context chain breaks | Exit context duration too short | Increase the exit context duration (number of turns it stays active) |
| Fulfillment response not appearing (digital) | Missing Append Conversation node after Channel Reply | Add Append Conversation between Channel Reply and Receive in the Connect flow |
| Agent says raw JSON to customer | Evaluate node missing or misconfigured | Add an Evaluate node to format the API response into human-readable text |

---

## Demo API for Testing

Cisco provides a public demo appointment API for testing scripted agent fulfillment without building a real backend:

**Base URL:** `http://ec2-18-225-36-23.us-east-2.compute.amazonaws.com:5003`

| Endpoint | Method | Purpose |
|---|---|---|
| `/check_availability` | POST | Check available appointment slots |
| `/create_appointment` | POST | Book a new appointment |
| `/lookup_appointment` | POST | Retrieve an existing appointment |
| `/cancel_appointment` | POST | Cancel an existing appointment |

All endpoints accept JSON POST bodies and return JSON responses. This API is for **testing and demonstrations only** — it has no SLA and may be unavailable without notice. Replace with your real backend before production.

> Source: [Cisco WebexPlaybooks — scripted appointment](https://github.com/webex/WebexPlaybooks/tree/main/playbooks/wxcc-ai-agent-scripted-appointment)

---

## References

- `docs/reference/ai-agent-studio-scripted.md` — comprehensive scripted agent reference
- `docs/reference/flow-designer-patterns.md` § Scripted Agent Fulfillment Pattern — State Event resume mechanism for voice
- [wxcc-ai-agent-scripted-appointment](https://github.com/webex/WebexPlaybooks/tree/main/playbooks/wxcc-ai-agent-scripted-appointment) — importable reference flow (4-intent appointment)
- [wxcc-ai-agent-scripted-tracking](https://github.com/webex/WebexPlaybooks/tree/main/playbooks/wxcc-ai-agent-scripted-tracking) — importable reference flow (package tracking)
- `docs/examples/flow-designer-scripted-*.env.template` — UUID replacement lists for each reference flow
- `docs/playbooks/scripted-agent-design.md` — companion design playbook (plan before you build)
- `docs/playbooks/digital-inbound-agent.md` — digital inbound conversation flow (base flow for digital fulfillment)
- [Webex AI Agent Studio Administration Guide](https://help.webex.com/en-us/article/ncs9r37/Webex-AI-Agent-Studio-Administration-guide)
- [Configure fulfillment for scripted AI agents](https://help.webex.com/en-us/article/mzpuseb/Configure-fulfillment-for-scripted-AI-agents)
- [Configure custom events for AI agents](https://help.webex.com/en-us/article/n5uo60x/Configure-custom-events-for-AI-agents)
- [Cisco WebexPlaybooks repo](https://github.com/webex/WebexPlaybooks) — official reference implementations
