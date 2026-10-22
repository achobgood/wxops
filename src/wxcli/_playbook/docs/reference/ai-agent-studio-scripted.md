# Webex AI Agent Studio -- Scripted Agent Reference

<!-- ref-tag: ai-agent-scripted-v4 -->

> For autonomous agents, see `ai-agent-studio.md`.

## Overview

Scripted agents use an **intent-entity-response** architecture. Unlike autonomous agents (LLM-driven), scripted agents classify user input against trained intents using NLU, collect required entities via fixed prompts, and return pre-authored responses. There is no LLM response generation -- behavior is deterministic and developer-defined.

**Key differences from autonomous agents:**

| Aspect | Autonomous | Scripted |
|--------|-----------|----------|
| Response generation | LLM generates text dynamically | Pre-authored responses only |
| Action mechanism | Dedicated Actions tab + standalone Connect flows | No Actions tab; fulfillment inline via template_key branching |
| Behavior definition | Instructions (system prompt) read by LLM | Intents + Entities + Responses + Context management |
| Slot collection | LLM extracts from natural language | Fixed prompts with configurable retries |
| Cost per license unit | 200 sessions (voice or digital) | 1,200 sessions (voice) / 4,800 sessions (digital) |
| Build effort | Faster (write instructions + action descriptions) | More effort (author intents, utterances, entities, responses) |
| Response control | Risk of hallucination | Full control, deterministic |

---

## Access

Same path as autonomous agents:

1. Log in to **Webex Control Hub** (admin.webex.com)
2. Navigate to **Contact Center > AI Agents**
3. Click **AI Agent Studio** -- opens in a new tab

---

## Creating a Scripted Agent

1. Click **Create Agent**
2. Select **Scripted**
3. Fill in **Name** and **Description**
4. Select **AI Engine** (see AI Engines section below)
5. Click **Create**

Or use a template: **Doctor's Appointment (Scripted)** or **Track Package (Scripted)** are available as starting points.

---

## UI Layout

The scripted agent configuration has these sections in the left navigation:

| Section | Purpose |
|---------|---------|
| **Profile** | Agent name, System ID, description, timezone, profile image, feedback toggle, custom error messages, AI engine selection |
| **Scripts** | Three sub-tabs: **Intents**, **Entities**, **Responses** -- this is where all behavior is defined |
| **Agent Handover** | Transfer-to-agent configuration |
| **Language and Voice** | Language, voice selection, speaking rate (0.7-1.2), response style, disfluencies toggle |
| **Fulfillment** | External system integration |
| **History** | Version History (all published versions) and Change Logs (35-day audit trail) |
| **Sessions** | Record of all customer interactions |
| **Analytics** | Performance metrics |

The **Preview** panel (Chat and Voice) is available for testing at any time.

---

## Agent Goal

The Agent Goal field exists for scripted agents but serves primarily as **administrative metadata**. Since no LLM reads it to guide behavior, the goal describes the agent's purpose for human administrators.

Follow the same do's and don'ts as autonomous agents (see `ai-agent-studio.md`), but understand that the goal does not influence runtime behavior.

---

## Welcome Message

The Welcome Message is a **default system intent** (not a tree node). It fires automatically when a conversation starts.

- Customizable text per channel (Web, Voice, WhatsApp, SMS, RCS, Apple Messages, Messenger)
- Supports variable interpolation: `{{customer_name}}` from custom data passed via Flow Designer State Event
- Triggered by the `welcome_event` — can be overridden with a custom incoming event (see [Incoming Custom Events](#incoming-custom-events-voice-only) below)
- Custom events can bypass the welcome prompt entirely, starting the agent at a specific response instead
- Cannot be deleted -- it is a non-deletable default system event (separate from the three system intents: Fallback, Partial Match, Talk to an agent)

Example:
```
Welcome to Acme Support! I can help you with appointment scheduling, order tracking, or general questions. What can I help you with?
```

---

## Building Blocks: Intents, Entities, Responses

All scripted agent behavior is defined through three interconnected building blocks in the **Scripts** tab.

### Intents

An intent represents a specific user goal (e.g., "Book Appointment", "Track Package", "Cancel Order"). The NLU engine classifies free-text user input against trained intents.

#### Intent Configuration

| Field | Description |
|-------|-------------|
| **Name** | Descriptive name (e.g., `book_appointment`) |
| **Description** | Plain-language description; mandatory for Pro 2.0 engine |
| **Utterances** | Training phrases -- minimum 3 (10+ for Pro 2.0). Use **Generate variants** button to auto-generate additional utterances via LLM |
| **Slots** | Entities linked to this intent for collection (see Slots section) |
| **Entry Contexts** | Max 5. The intent only matches if ALL entry contexts are active in the session |
| **Exit Contexts** | Max 15. When this intent fires, these contexts become active (with configurable lifespan/duration) |
| **Reset slots after completion** | Toggle: clears collected entity values when the intent completes |
| **End conversation** | Toggle: terminates the session after the intent completes |

#### Slots (Per-Intent Entity Linking)

Click **+Link** within an intent to link an entity. Each linked slot has:

| Property | Description |
|----------|-------------|
| **Required** | Checkbox -- if ON, the agent must collect this before completing the intent |
| **Retries** | Number of retry attempts if the slot is not filled |
| **Response** | Which response template to use when prompting for this slot value |
| **Update slot values** | Toggle -- allows the user to change the slot value during conversation |

Slot values are accessible in responses via `${entity.<entity_name>}`.

#### System Intents (Built-in, Non-Deletable)

| Intent | Purpose |
|--------|---------|
| **Default Fallback** | Fires when no intent matches above the confidence threshold |
| **Talk to an agent** | Triggers human agent escalation via `agent_handover` template |
| **Partial Match** | Fires when multiple intents score similarly -- prompts clarification |

#### Small Talk Intents (Built-in, Customizable/Deletable)

Greetings, Thank you, Not helpful, Goodbye

### Entities

Entities define what data the agent extracts from user input. Defined globally (shared across intents), then linked to specific intents as slots.

| Entity Type | Description | Example |
|-------------|-------------|---------|
| **Custom list** | Predefined strings with optional synonyms | Service types: "oil change", "tire rotation" |
| **Regex** | Regular expression pattern matching | Tracking number: `[A-Z]{3}\d{6}` |
| **Digits** | Capture fixed-length numerical inputs with high accuracy, especially in voice interactions | 6-digit account PIN |
| **Alphanumeric** | Mixed letters and numbers | License plate: `ABC1234` |
| **Free form** | Accept any text input | Customer name, description |
| **Map location (WhatsApp)** | WhatsApp-specific location sharing | GPS coordinates |

Type names above are verbatim from [Understand intents, entities, and responses](https://help.webex.com/en-us/article/sz02k8/Understand-intents,-entities,-and-responses-in-AI-Agent-Studio) (Cisco page last updated July 16, 2026; verified 2026-07-27).

#### System Entities (Prebuilt)

Date, Time, Email, Phone number, Monetary units, Ordinal, Cardinal, Geolocation, Person names, Quantity, Duration

#### Entity Rules

- Entity type **cannot be changed** after creation
- ⚠ **UNVERIFIED** -- **Entity Roles** (e.g., origin city vs. destination city for the same Airport entity) are supported only with MindMeld and RASA engines. Those engine names are not in Cisco's current AI Agent Studio documentation and the string "entity roles" does not appear on Cisco's entities page; do not rely on this line. See § AI Engines → *UNVERIFIED -- Entity Roles inherit the same provenance problem*
- Minimum **2 slot annotations** required for training

### Responses

Responses are organized by **template key** (a named response). The agent delivers the response associated with the matched intent's template key.

#### Response Designer

The Response Designer provides a form-based interface for creating responses:

- **Channel selector**: Web (default), Voice, WhatsApp, SMS, RCS, Apple Messages, Messenger -- each can have a different response format
- **Response types** (vary by channel):
  - **All channels**: Text
  - **Web**: Carousel, Quick Reply, Image, Video, Audio, File
  - **WhatsApp**: Reply Button, List Message, Numbered List, File, Image, Video, Audio
  - **Apple Messages**: List Picker, Time Picker, Media, Rich Link, Form
  - **SMS/RCS**: Quick Reply
  - **Voice**: Custom Event (for fulfillment handoff)

#### Conditional Responses

The Response Designer supports **IF/OR rules** for branching responses:

- Rule builder with: Left variable → Operator → Right variable → Data type
- Different response content per condition
- Example: IF `${entity.appointment_type}` equals "urgent" → "I'll prioritize this for you"

#### Response Variables

> ⚠ **UNRESOLVED — `${}` vs `$()` in response templates.** The `${...}` syntax below is preserved as written and has **not** been corrected, because no verified alternative was available. Whether AI Agent Studio response templates take `${variable}` or `$(variable)` is an **open verification**, not a settled fact — the action item *"Verify against official AI Agent Studio documentation whether response template variables use `${}` or `$()`"* is still outstanding in `docs/tests/findings/skill-build-scripted-fulfillment-findings.md` § 1. Note this is a **different** context from Webex Connect flow variables, which use `$(...)` via the variable picker. Confirm in the Response Designer on your tenant before hard-coding either form.

| Syntax | Source | Scope |
|--------|--------|-------|
| `${entity.<entity_name>}` | Collected slot values | Current session |
| `${extra_params.<key>}` | Message parameters from Connect flow | One message turn only |
| `${eventStore.<variable_name>}` | Custom event data from Flow Designer | Current session |
| `${consumerData.extra_params.<key>}` | Custom Parameters from Connect (⚠ "scripted digital only" is UNVERIFIED — open item O8, see § Scripted-Only Features on Digital Channels) | Current session |

#### System Responses (Non-Deletable)

| Response | Purpose |
|----------|---------|
| **Welcome message** | First message when conversation starts |
| **Response suggestion** | Partial match clarification options |
| **Partial message** | Ambiguous intent handling |
| **Fallback message** | No intent matched |
| **Entity suggestion** | Entity value suggestions |
| **Agent handover** | Escalation message (changing text does NOT affect handover behavior) |

---

## Context Management (Conversation Flow Control)

Context management is how scripted agents create **conversation flows** -- controlling which intents are reachable at any point. There is no visual tree; the flow is implicit in the context chain.

### How It Works

1. **Exit contexts** on Intent A activate context values (with duration/lifespan)
2. **Entry contexts** on Intent B require those context values to be active
3. The NLU only matches Intent B if its entry context requirements are met

### Example: Appointment Booking Flow

```
Intent: greeting
  Exit contexts: ["greeted" (duration: 3 turns)]

Intent: book_appointment
  Entry contexts: ["greeted"]
  Slots: [date (required), time (required)]
  Exit contexts: ["appointment_booked" (duration: 3 turns)]

Intent: confirm_appointment
  Entry contexts: ["appointment_booked"]
```

This creates a flow: User greets → can book appointment → can confirm appointment. Without the greeting, `book_appointment` won't match.

### Limits

- Max **5 entry contexts** per intent
- Max **15 exit contexts** per intent
- You **cannot link to default intents** (welcome, fallback, partial match) from other intents via context

---

## AI Engines

Cisco names five engines across both agent types. Engine names below are verbatim from [Understand AI engines for AI agents](https://help.webex.com/en-us/article/ne6s80cb/Understand-AI-engines-for-AI-agents) (Cisco page last updated July 16, 2026; verified 2026-07-27).

**Scripted agents support two engines:**

| Engine | Cisco guidance |
|--------|----------------|
| **Webex AI Pro 2.0 (with Swiftmatch)** | "Each intent must include at least 10 representative utterances." |
| **Webex AI Pro 1.0 (with Swiftmatch)** | For "fewer than 10 utterances per intent" and multilingual agents. |

**Autonomous agents support three engines** -- listed here only so the split is explicit; these are not selectable for scripted agents (for autonomous agents see `ai-agent-studio.md`):

| Engine |
|--------|
| **Webex AI Pro 1.0** |
| **Webex AI Pro-US 1.0** |
| **Webex AI Pro-Europe 1.0** |

**Webex AI Pro 2.0 note:** Uses LLM for **training-time pattern generation** and semantic intent classification. It does NOT use LLM for response generation -- all responses remain pre-authored. Whether LLM is invoked at inference time (per-message) or only at training time is unverified -- requires hands-on testing. Intent descriptions are mandatory with Pro 2.0.

### Note -- RASA and MindMeld were carried here in error

Revisions of this file before 2026-07-27 listed four scripted-agent engines: **Swiftmatch (Pro 1.0)**, **Swiftmatch (Pro 2.0)**, **MindMeld** ("Classical ML with entity role support"), and **RASA** ("Open-source NLU framework"). That content is preserved here rather than deleted, because it does not describe AI Agent Studio:

- Those names come from [NLU Engines - Webex Connect Platform Overview](https://help.webexconnect.io/docs/nlu-engine), which documents **Webex Connect Bot Builder -- a different product**. Its own text says "Rasa and Mindmeld NLU engines only support English **in the bot builder** for now".
- Checked 2026-07-27: the strings "RASA", "Rasa", "MindMeld", and "Mindmeld" do **not** appear on Cisco's [Understand AI engines for AI agents](https://help.webex.com/en-us/article/ne6s80cb/Understand-AI-engines-for-AI-agents) page.
- Cisco publishes **no** deprecation notice for RASA or MindMeld. This file therefore does **not** claim either engine was removed or deprecated -- only that the current AI Agent Studio engine documentation does not name them.
- "Swiftmatch" is likewise not an engine name on its own; it is a parenthetical component of "Webex AI Pro 2.0 (with Swiftmatch)".

#### UNVERIFIED -- Entity Roles inherit the same provenance problem

Two claims elsewhere in this file gate **Entity Roles** on the same two engine names, and so inherit the same Bot Builder provenance. Both are preserved verbatim here and flagged UNVERIFIED at their original locations:

| Location | Claim as written |
|----------|------------------|
| § Entities → Entity Rules | "**Entity Roles** (e.g., origin city vs. destination city for the same Airport entity) are supported only with MindMeld and RASA engines" |
| § Troubleshooting | "Entity roles not working \| Wrong AI engine \| Entity roles require MindMeld or RASA (not Swiftmatch)" |

What is established, as of 2026-07-27:

- The string "entity roles" does **not** appear on Cisco's [Understand intents, entities, and responses](https://help.webex.com/en-us/article/sz02k8/Understand-intents,-entities,-and-responses-in-AI-Agent-Studio) page (last updated July 16, 2026).
- Cisco publishes **no** statement either way. Absence from that page is not proof of removal.

This file therefore does **not** claim that Entity Roles were removed, that they are deprecated, or that they still work -- all three would be guesses. The claims stand as UNVERIFIED until resolved against the live platform, Cisco documentation, or the platform owner.

### Engine Settings

| Setting | Description |
|---------|-------------|
| **Fallback threshold** | Score below which the Default Fallback intent fires |
| **Partial match threshold** | Score difference triggering a clarification prompt |
| **Spellcheck in inference** | Auto-correct user input before NLU processing |
| **Expand contractions** | Expand "don't" → "do not" before processing |
| **Stopwords removal** | Remove common words before NLU |
| **Special character removal** | Strip special characters before NLU |
| **Prioritize slot filling** | Prioritize entity extraction over intent classification |

---

## Fulfillment (Calling External APIs)

Scripted agents do NOT use the Actions tab or standalone fulfillment flows. Fulfillment architecture differs by channel.

### Digital Channel Fulfillment

> See also: `docs/reference/digital-inbound.md` for the full digital inbound architecture, and `docs/playbooks/digital-inbound-agent.md` for the step-by-step build guide.

On digital channels (WhatsApp, SMS, Chat, etc.), fulfillment happens **inline** within the conversation flow in Webex Connect:

```
AI Agent node → Data Parser (extract template_key from SessionMetadata)
  → Branch (check if template_key requires fulfillment)
    → YES: HTTP Request → Evaluate → Send response to user → Append conversation → Loop back to Receive
    → NO: Send agent response to user → Loop back to Receive
```

**Key concepts:**
- The AI Agent node outputs **MessageMetadata** and **SessionMetadata** (⚠ "scripted digital only" is UNVERIFIED — the AI Agent node docs list both output variables with no agent-type qualifier. Open item O8, see § Scripted-Only Features on Digital Channels)
- A **Data Parser** node extracts `$.model_state.template_key` to identify which response triggered
- A **Branch** node checks if that template_key requires an API call
- The **Connect flow itself** sends the fulfillment result to the user -- the agent does NOT "see" the result
- Entity values collected by the agent are accessible in SessionMetadata: `${lastdfState.model_state.entities.<entity_name>.value}`

### Incoming Custom Events (Voice Only)

Flow Designer can send **incoming custom events** to a scripted agent via the Virtual Agent V2 State Event settings. This enables custom starting points (bypassing the welcome prompt), passing data from IVR to agent, and resuming an agent after fulfillment.

**Channel support:** Voice channel only.

#### Configure in AI Agent Studio

1. Go to **Scripts > Responses** tab
2. Create a new response (or select an existing one)
3. Under **Default response**, click **+** next to **Default (Web)** to add a **Voice** channel
4. In the **Incoming event name** field, enter the event name the agent will receive from Flow Designer (e.g., `custom_welcome`)
5. Author the response content — this is what the agent says when it receives this event

The agent will deliver this response (instead of the default welcome) when Flow Designer sends a State Event with the matching event name.

#### Invoke from Flow Designer

In the Virtual Agent V2 activity's **State Event** settings:

| Column | Value |
|--------|-------|
| **Event Name** | The custom event name configured in the Response tab (e.g., `custom_welcome`) |
| **Event Data** | Custom data to pass (e.g., `store_name` = `{{StoreName}}`) |

#### Access Custom Event Data in Responses

Event data is accessible in the response where the incoming event was configured:
- Use `${eventStore.<variable_name>}` syntax in response text
- Example: If Flow Designer sends `store_name` = "Downtown", the response can say: "Welcome to our ${eventStore.store_name} location!"

#### Use Case: Custom Starting Point

Instead of the generic welcome prompt, start the agent in a context-aware state:

1. IVR collects initial data (e.g., store number from DTMF)
2. Flow Designer looks up the store name
3. Virtual Agent V2 sends `custom_welcome` event with `store_name` data
4. Agent skips the default welcome and says: "Welcome to our Downtown location! How can I help?"

### Voice Channel Fulfillment

On voice, scripted agents use **Custom Events** to hand control to WxCC Flow Designer:

1. A response with type **Custom Event** emits a payload (e.g., `{"PackageNumber":"${entity.PackageNum}"}`)
2. The Virtual Agent V2 activity exits via its `ENDED` path with `StateEventName` set to the event name (e.g., `track_package_exit`)
3. Flow Designer parses `VirtualAgentV2.MetaData`, routes on `StateEventName`, calls the external API, and evaluates the response
4. Flow Designer returns data via a **State Event** by re-entering the VirtualAgentV2 activity with `event_name` and `event_data_string` set

The full activity chain in Flow Designer:

```
VirtualAgentV2 (ENDED) → Parse (MetaData → http_input)
  → Case (StateEventName)
  → HTTP Request (POST with http_input body)
  → Condition (httpStatusCode == 200)
    → TRUE: SetVariable event_name = "<intent>_confirm_entry"
            → SetVariable event_data_string = "{{ event_data }}"
            → VirtualAgentV2 (resume — agent delivers result to caller)
    → FALSE: PlayMessage (error TTS) → QueueContact (escalate)
```

> **Full reference:** See `docs/reference/flow-designer-patterns.md` § Scripted Agent Fulfillment Pattern for complete details on the State Event resume mechanism, multi-event routing, intent-based queue routing, and the `CustomAIAgentInteractionOutcome` analytics variable.

The State Event can also update the agent's state to force re-prompting:
- **intent**: Navigate to a different intent
- **slots**: Set or clear slot values (clearing forces re-prompting)
- **context**: Activate or deactivate context values

Example state_update payload:
```json
{
  "intent": "book_appointment",
  "slots": {"time": ""},
  "context": {"retry": 1}
}
```
This clears the `time` slot and forces the agent to re-ask for a new time.

#### state_update Use Cases

**Re-prompt after failed fulfillment:** When appointment booking fails because the time slot is unavailable, clear the slot to re-prompt:

```json
{
  "intent": "book_appointment",
  "slots": {
    "time": ""
  }
}
```

Setting a slot to empty string (`""`) forces the agent to re-ask for that value.

**Navigate to a prerequisite intent:** When a balance inquiry requires identity verification first:

```json
{
  "intent": "verify_user"
}
```

**Prepopulate known information when switching intents:** Skip re-asking for data you already have:

```json
{
  "intent": "verify_user",
  "slots": {
    "date_of_birth": "06/26/1993"
  }
}
```

**Reset context after failed verification:** Clear sensitive slots and reset context flags:

```json
{
  "intent": "verify_user",
  "slots": {
    "date_of_birth": "",
    "pincode": ""
  },
  "context": {
    "verified": 0
  }
}
```

Setting `context.verified` to `0` deactivates any downstream intents that require verification.

### Fulfillment Comparison

| Aspect | Autonomous | Scripted (Digital) | Scripted (Voice) |
|--------|-----------|-------------------|-----------------|
| Trigger | LLM calls action | Branch on template_key | Custom Event response |
| Flow location | Standalone Connect flow | Inline in conversation flow | WxCC Flow Designer |
| Entry node | AI Agent Start node | N/A (inline) | Virtual Agent V2 Custom Event path |
| Results return | Flow Outcomes payload → agent | Flow sends response directly to user | state_update event → agent |
| Execution limit | 30 seconds | No separate limit | Flow Designer timeout |
| Agent awareness | Agent receives and uses results | Agent is "blind" to results | Agent receives state updates |

---

<!-- SYNC: also update docs/reference/ai-agent-studio.md (escalation mentions in Instructions Template) when changing this section -->
## Escalation

Escalation uses the built-in **"Talk to an agent"** system intent:

- Fires when the user requests a human agent at any point
- Triggers the `agent_handover` response template
- The handover is triggered by the template key, not the message text -- changing the response text does NOT affect handover behavior

### Flow-Side Handling

| Channel | Escalation Path |
|---------|----------------|
| **Voice** | Virtual Agent V2 → **Escalated** output → Queue Contact |
| **Digital** | AI Agent node → **onAgentHandover** outcome → Queue Task |

### Intent-Based Routing at Escalation

At handover, the flow can read `$.previous_intent_model_state.intent.name` to route to different queues based on what the user was discussing when they asked for a human.

---

## Error Handling

Scripted agents have a multi-layered error handling system:

### Layer 1: Confidence Thresholds
NLU classifies input with a confidence score. Two thresholds control behavior:
- **Fallback threshold**: Below this → Default Fallback intent fires
- **Partial match threshold**: Multiple intents score similarly → clarification prompt

### Layer 2: Default Fallback Intent
- Built-in, non-deletable
- Customizable per-channel fallback message
- Failed messages logged to the **Curation Console** (AI Agent Studio > Issues tab) for review
- Use the Curation Console to identify patterns in unmatched queries, review low-confidence classifications, and create new intents to handle common misses

### Layer 3: Slot Filling Retries
- Per-slot configurable retry count
- Each retry re-sends the configured prompt
- If retries exhausted and slot unfilled, the conversation can be redirected

### Layer 4: Partial Match (Clarification)
- When the system detects ambiguity between intents
- Presents clarification options (List Picker on Apple Messages, text on other channels)

### Layer 5: Agent Handover
- "Talk to an agent" system intent available at any point

### Layer 6: Custom Event Re-Prompting (Voice Only)
- Flow Designer sends `state_update` to clear slots and force re-prompting
- Useful when fulfillment fails (e.g., appointment slot unavailable)

### Layer 7: Preprocessing
- Spellcheck, stopword removal, special character filtering normalize input before NLU

---

<!-- SYNC: also update docs/reference/ai-agent-studio.md (Testing section) when changing this section -->
## Testing

Three testing mechanisms:

### Chat Preview
- Built into AI Agent Studio
- Click **Start a Chat** to interact as a customer via text
- For scripted agents, responses should be deterministic (unlike autonomous)

### Voice Preview
- Browser microphone required (headset recommended)
- Supports barge-in (interrupting the agent mid-speech)
- Tests the full voice interaction including speech recognition

### Testing Framework
- Create and run comprehensive test case sets
- Define test messages and expected responses
- Simulate complex interactions with multi-message test cases
- One-click execution

---

<!-- SYNC: also update docs/reference/ai-agent-studio.md (Deploying the Agent, CCAI Config sections) when changing this section -->
## Deployment

Deployment follows the same process as autonomous agents:

1. **Publish** the agent in AI Agent Studio (the NLU model retrains automatically when you add or modify intents/entities before publishing)
2. **Voice**: In WxCC Flow Designer → **Virtual Agent V2** activity → **Contact Center AI Config** dropdown → select **"Webex AI Agent Scripted"** → select the published agent
3. **Digital**: In Webex Connect → AI Agent node → select agent type (Scripted) → select the agent

There is **no Control Hub creation step** for a Webex AI Agent. [Use AI agents for customer interactions](https://help.webex.com/en-us/article/s0qro1/) (updated 2026-05-12; verified 2026-07-27) states only: "Select **Webex AI Agent Scripted** from the **Contact Center AI Config** drop-down list."

The only difference from an autonomous agent: select **"Webex AI Agent Scripted"** instead of "Webex AI Agent Autonomous" in that dropdown.

**Prerequisite**: a one-time tenant enablement is required before "Webex AI Agent Scripted" appears in the Contact Center AI Config dropdown (confirmed by the platform owner 2026-07-27) — see [`wxcc-platform.md` § Webex AI Agent Tenant Prerequisite].

### Note: CCAI Config in Control Hub is a different product

**CCAI (Contact Center AI) is Google's product; Webex AI Agent is Cisco's own.** The Control Hub flow `Control Hub > Services > Contact Center > Tenant settings > Integrations > Features tab > New > Contact Center AI Config` exists for **Google CCAI / BYOVA / Agent Answers** — not for a Webex AI Agent build. Cisco's stated prerequisite for that flow is "Ensure that the service-specific integration connector is created. For example, **Google** Contact Center AI connector", and its **Contact Center AI Connector** field offers only "Webex CCAI", "Integration Connector" and "Service App" — no Webex AI Agent option [source: [Cisco help article npbt02j](https://help.webex.com/en-us/article/npbt02j/), updated 2025-11-03; verified 2026-07-27].

Do not perform the Control Hub creation step when deploying a Webex AI Agent. The identically named **Contact Center AI Config** dropdown inside the Flow Designer Virtual Agent V2 activity is where a Webex AI Agent is selected (step 2 above).

---

## Import / Export

- **Export**: Ellipsis menu on agent card or Version History → downloads agent as JSON
- **Import**: Dashboard → Import agent → upload JSON → edit name/System ID
- Templates can be cloned as starting points

---

## Licensing & Cost

Scripted agents are significantly cheaper than autonomous:

| Type | Sessions per AI Agent License Unit |
|------|-----------------------------------|
| Scripted Digital | 4,800 |
| Scripted Voice | 1,200 |
| Autonomous (voice or digital) | 200 |

**Session measurement:**
- Voice: 2-minute increments, rounded up
- Digital: 15-message exchange increments, rounded up

**LLM cost:** Scripted agents using Pro 1.0 engines make zero LLM calls. Pro 2.0 may use LLM for intent classification, but never for response generation.

---

## Limits

| Limit | Value |
|-------|-------|
| Max agents per org | 100 (scripted + autonomous combined) |
| Max entry contexts per intent | 5 |
| Max exit contexts per intent | 15 |
| Min utterances per intent | 3 (10+ for Pro 2.0) |
| Min slot annotations for training | 2 |
| Max agent name length | 256 characters |
| Rate limit | 240 transactions/minute/tenant |
| Change log retention | 35 days |
| Advanced log retention | 180 days |

---

## Scripted-Only Features on Digital Channels

> ⚠ **UNVERIFIED — the "scripted-only" restriction, not the features (including this heading's own claim).** This repo states the three features below are available **ONLY** for scripted agents on digital channels (via the AI Agent node in Webex Connect). That restriction is **not documented in the official AI Agent node docs** [https://help.webexconnect.io/docs/ai-agent-node], which list Custom Parameters, MessageMetadata, and SessionMetadata **with no agent-type qualifier**. Tracked as **open item O8**; `docs/reference/digital-inbound.md` § AI Agent Node and § Caveats and Limitations carry the same hedge. Verify against the tenant before relying on the exclusivity — the feature descriptions themselves are unaffected.

These features are available for scripted agents on digital channels (via the AI Agent node in Webex Connect). ⚠ Whether they are *exclusive* to scripted agents is UNVERIFIED — see the note above:

| Feature | Description |
|---------|-------------|
| **Custom Parameters** | Key-value pairs passed to the agent, accessible via `${consumerData.extra_params.<key>}` |
| **MessageMetadata** | Metadata from the current agent response |
| **SessionMetadata** | Session-level metadata including `model_state.template_key` (used for fulfillment branching) |

---

## When to Use Scripted vs Autonomous

| Factor | Choose Scripted | Choose Autonomous |
|--------|----------------|-------------------|
| **Response control** | Must be exact (regulatory, compliance) | Natural tone more important than exact wording |
| **Conversation predictability** | Fixed paths, known outcomes | Open-ended, varied user inputs |
| **Cost sensitivity** | High volume, cost matters | Lower volume, flexibility matters |
| **Build effort tolerance** | Willing to invest in utterance authoring | Need fast time-to-deploy |
| **Data sensitivity** | Strict data handling rules | Standard data handling acceptable |
| **Scope changes** | Infrequent | Frequent iteration expected |

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Wrong intent matched | Insufficient/overlapping utterances | Add more diverse utterances; increase fallback threshold |
| Fallback fires too often | Threshold too high or too few utterances | Lower fallback threshold; add utterances; check Curation Console |
| Slot not collected | Entity type mismatch or retries exhausted | Verify entity type; increase retry count |
| Fulfillment doesn't fire (digital) | Branch node not checking correct template_key | Verify template_key in Data Parser and Branch conditions |
| Fulfillment doesn't fire (voice) | Custom Event response not configured | Add Custom Event response type to the intent's response |
| Agent handover not working | Flow not handling onAgentHandover outcome | Wire the escalation path in Connect/Flow Designer |
| Context chain broken | Entry context not active | Check exit context lifespan/duration on upstream intent |
| Entity roles not working | Wrong AI engine | ⚠ **UNVERIFIED** -- previously documented as "Entity roles require MindMeld or RASA (not Swiftmatch)". Those engine names are not in Cisco's current AI Agent Studio documentation. See § AI Engines → *UNVERIFIED -- Entity Roles inherit the same provenance problem* |

---

## Key Sources

- [Webex AI Agent Studio Administration Guide](https://help.webex.com/en-us/article/ncs9r37/Webex-AI-Agent-Studio-Administration-guide)
- [Understand intents, entities, and responses](https://help.webex.com/en-us/article/sz02k8/Understand-intents,-entities,-and-responses-in-AI-Agent-Studio)
- [Understand AI engines for AI agents](https://help.webex.com/en-us/article/ne6s80cb/Understand-AI-engines-for-AI-agents)
- [Configure fulfillment for scripted AI agents](https://help.webex.com/en-us/article/mzpuseb/Configure-fulfillment-for-scripted-AI-agents)
- [Configure custom events for AI agents](https://help.webex.com/en-us/article/n5uo60x/Configure-custom-events-for-AI-agents)
- [Use AI agent templates](https://help.webex.com/en-us/article/n8mo4c/Use-AI-agent-templates)
- [Use AI agents for customer interactions](https://help.webex.com/en-us/article/s0qro1/Use-AI-agents-for-customer-interactions)
- [Guidelines and best practices](https://help.webex.com/en-us/article/nelkmxk/Guidelines-and-best-practices-for-automating-with-AI-agent)
- [AI Agent node (Webex Connect)](https://help.webexconnect.io/docs/ai-agent-node)
- [License consumption and reporting](https://help.webex.com/en-us/article/n9vhuwe/Webex-Contact-Center-license-consumption-and-reporting)

## See Also

- [ai-agent-studio.md](ai-agent-studio.md) — the autonomous-agent counterpart, for choosing between the two agent types
- [digital-inbound.md](digital-inbound.md) — the digital-channel flows that hand a conversation to a scripted agent
- [flow-designer-patterns.md](flow-designer-patterns.md) — scripted agent fulfillment wiring in Flow Designer
- [scripted-agent-build.md](../playbooks/scripted-agent-build.md) — the build sequence this reference supports
