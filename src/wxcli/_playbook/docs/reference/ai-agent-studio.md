# Webex AI Agent Studio -- Platform Reference (Autonomous Agents)

<!-- ref-tag: ai-agent-studio-v6 -->

> This reference covers **autonomous** agents. For **scripted** agents, see `ai-agent-studio-scripted.md`.

## Access

1. Log in to **Webex Control Hub** (admin.webex.com)
2. Navigate to **Contact Center > AI Agents**
3. Click **AI Agent Studio** -- opens in a new tab

---

## Agent Types

| Type | Description | Use When |
|------|-------------|----------|
| **Autonomous** | LLM-driven conversation; agent decides what to say and when to call actions | Natural language interactions, complex workflows |
| **Scripted** | Intent-entity-response architecture; NLU classifies input, agent returns pre-authored responses (see `ai-agent-studio-scripted.md`) | Deterministic responses, compliance-sensitive, high-volume/cost-sensitive deployments |

---

## Creating an Agent

1. Click **Create Agent**
2. Select agent type (Autonomous or Scripted)
3. Fill in:
   - **Name**: descriptive name for the agent
   - **Description**: brief description for admin reference
4. Click **Create**

---

## Agent Goal

The Agent Goal field is a short, concise statement of the agent's overall purpose. It focuses on the end result or benefit for the caller.

**Do's:**
- Keep it short and concise
- Focus on the overall function or purpose
- Consider the end result or benefit for the user
- Use clear and concise language
- Ensure the goal aligns with the actions and capabilities of the agent

**Don'ts:**
- Don't include specific details like locations, dates, or user information
- Don't mention particular actions or implementation methods
- Don't use technical jargon or complex terminology
- Don't use overly long or complicated goal statements
- Don't include multiple unrelated goals in a single prompt
- Don't use ambiguous or vague language

---

## Agent Instructions (System Prompt)

The Instructions tab defines the agent's personality, capabilities, and constraints. The LLM reads this on every turn. Use markdown headings and lists for best results.

**Tip:** Add instructions after configuring actions and testing the agent. Adding instructions after testing enhances efficiency and accuracy.

### Instructions Template

#### 1. Identity

- **Role Definition**: Define the persona and expertise. "You are [Name/Role], a [description] for [Organization]."
- **Tone and Demeanor**: Specify friendly, formal, or casual. Match the organization's brand voice.

#### 2. Context

- **Background Information**: Relevant context (e.g., "This is a customer support line for scheduling and account inquiries").
- **Environment Details**: System constraints (e.g., "The caller is on voice and may have background noise which impacts transcription quality").

#### 3. Task

Break down the overall task into specific, sequential steps. Reference the actions at each step that will be used to fulfill the task.

- Step 1: What happens first (e.g., identity verification)
- Step 2: What the agent can do next
- Step N: Additional capabilities

For each step: when to call the action, what it returns, how to use the data.

**Forceful language**: The LLM is non-deterministic and may skip required actions. Use:
- "You MUST call [action_name] before anything else."
- "Do NOT proceed without first calling [action_name]."
- "EVERY conversation starts with [action_name]. No exceptions."

Weak phrasing like "you should" or "try to" will be ignored intermittently.

**Timezone handling**: If the database stores timestamps in UTC, add explicit conversion:
> "All times returned from the database are in UTC. You MUST convert to [Local Timezone] (subtract/add N hours) before telling the customer any time. Never mention UTC to the customer."

#### 4. Response Guidelines

- **Formatting Rules**: For voice: one to two sentences at a time, don't stack multiple questions. For digital: bullet lists for options, numbered steps.
- **Language Style**: Natural filler ("Let me check on that", "One moment"). Confirm before committing -- read back details and wait for "yes". Wrap up: "Anything else I can help with?" Sign off warm: "Thanks for calling, [Name]. Have a great day!" Handle mid-conversation pivots gracefully.

#### 5. Error Handling and Fallbacks

- **Clarification Prompts**: "I didn't catch that, could you please repeat?"
- **Default Responses**: "I'm sorry, I didn't understand. Can you try rephrasing?"
- **Action Failures**: "I'm having trouble looking that up. Let me transfer you to someone who can help."
- **Escalation Triggers**: State the *conditions* that hand the caller to a human, not only the wording. "If the caller asks for a person, or you cannot help with what they need, say: 'Let me connect you with someone who can help.' Then transfer." Also cover the no-record case: if the identifying lookup returns no match, escalate rather than guessing.

#### 6. Guardrails

Instruct the agent to respond only in the context of the goal and not entertain unrelated queries. Include domain-specific restrictions (no unauthorized advice, no internal IDs, etc.).

#### 7. Examples (Optional)

Add a sample conversation between the caller and the agent for better prompt adherence. Most useful for complex or nuanced flows.

### Worked Example — A Complete Instructions Prompt

The template above says what each section must contain. This is one filled-in
instance of it, end to end, for a voice agent. Bracketed values are the parts you
replace.

Note the two syntaxes in play, which are not interchangeable: returned action data
is referenced by **quoted name** (`"customer_first_name"`), while session-start
custom data is referenced with **double braces** (`{{customer_name}}`). See
[What Does NOT Work for Flow Outcomes Data](#what-does-not-work-for-flow-outcomes-data).

```
You are a friendly, professional virtual assistant for [Organization]. You help callers with [list of capabilities — e.g., scheduling, account lookups, order status]. Keep it natural, like a real phone conversation. One to two sentences at a time.

REQUIRED FIRST ACTION:
You MUST call lookup_customer before anything else. EVERY conversation starts by identifying the caller via their phone number. No exceptions. Don't use their name until you've actually gotten it back from the system via "customer_first_name."

If their number doesn't match any account, say: "I'm not finding an account with that number. Let me connect you with someone who can help." Then transfer.

ONCE YOU HAVE THEIR RECORD:
Use their first name right away — "Hey Sarah, thanks for calling!" Then ask what they need help with. Let them lead.

[Add action-by-action guidance for each action your agent supports. For each one, describe:
- When to call it
- What to say before/after calling it
- How to present the returned data naturally
- What to do if the action fails or returns no results]

Example — scheduling flow:
1. Ask what service/item they need → call get_item_info → confirm details and any prep instructions
2. Ask what date works → call check_availability → present open times naturally ("I've got a 10 AM and a 2:30 in the afternoon")
3. Confirm all details before booking → call create_order → read back confirmation number

IMPORTANT ABOUT TIMES: All timestamps from the database are in UTC. Convert to [local timezone, e.g., US Eastern — subtract 5 hours] before telling the caller. Never mention UTC — callers don't need to hear that.

ESCALATION:
If you can't help or the caller asks for a person, say: "Let me connect you with someone who can help." Then transfer.

GROUND RULES:
- Never reveal internal IDs or database values (UUIDs, etc.) to the caller.
- Never guess — if you don't know, say so. "I'm not sure about that" is always better than making something up.
- Confirm details before making changes (booking, cancelling, updating).
- [Add domain-specific restrictions — e.g., "Don't give medical/legal/financial advice."]

HOW TO SOUND ON THE PHONE:
- Keep it short. One or two sentences at a time. This is a phone call, not an email.
- Don't stack multiple questions in one breath.
- It's OK to say "Let me check on that" or "One sec" — it sounds human.
- If someone seems unsure or confused, slow down. Repeat the important part. Ask if they have questions.
- If they change their mind or go in a different direction mid-conversation, just roll with it.
- Always wrap up with: "Anything else I can help with?"
- Sign off warm: "Thanks for calling [Organization], Sarah. Have a great day!"
```

---

## Welcome Message

The Welcome Message is a **separate field** from the Instructions. It is the first thing the caller hears when they connect.

Set it under the agent's configuration (not in the Instructions tab).

Example:
```
Thanks for calling! I can help you with account inquiries, placing orders, checking status, or general questions. How can I help you today?
```

---

## Slot Entities

Slot entities define the variables the agent collects from the caller and passes to actions.

Navigate to **Slots** tab > **Add Slot**

### Entity Fields

| Field | Notes |
|-------|-------|
| **Entity Type** | `String` for most values including phone numbers; `Date` for date inputs; `Number` for numeric quantities |
| **Entity Name** | Lowercase underscores: `phone_number`, `preferred_date` |
| **Entity Description** | Plain language for the LLM -- tells it what to ask the caller |
| **Entity Example** | Example value the LLM uses as a format hint |
| **Required** | Toggle ON for entities the action cannot run without |

### Phone Number = String (NOT Number)

Phone numbers must be entity type **String**, not Number. Using Number causes issues with leading zeros, formatting, and length validation.

---

## Actions

Each action maps to one Webex Connect flow. Navigate to **Actions** tab > **Add Action**.

### Action Fields

**Name**: A free-form label the LLM uses to refer to the action. Example: `lookup_customer`. It does **not** have to match anything in Webex Connect — an action is bound to its flow by **manual selection**, not by name (see Fulfillment below). Matching the action name to the flow name is a readability convention at most; nothing enforces it.

**Fulfillment (how the action is bound to a Connect flow)**: In the action's **Fulfillment** section, "Select a service that is configured in the Webex Connect client workspace... then Select a flow from the dropdown" [source: [Configure fulfilment flows for AI agent actions](https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions)]. Both the Service and the Flow are picked by hand, and neither has to correspond to the action's Name.

The binding is stored by ID, not by name — an exported agent's `fulfillment` block carries a numeric `service_id` / `service_name` pair, a numeric `flow_id` / `flow_name` pair, `type: "flow"`, and a `webhook_url` of the form `https://hooks.us.webexconnect.io/flows/<flow_id>/trigger/aiagent` (observed on a US tenant; whether the `us` segment varies by region is not verified). The webhook is keyed on the numeric flow ID, not on any name.

**Description**: The LLM reads this to decide when and how to call the action. Include:

- When to call it: "Call this action when you need to look up a customer..."
- What it returns: "Returns 'first_name', 'last_name', 'account_status'..."
- How to use the returned data: "Use 'first_name' to greet the customer by name."

**Input Entities**: Select which slot entities this action requires.

**Configure AI Agent Event**: This is configured in **Webex Connect**, not in AI Agent Studio — on the flow's **trigger node**, which presents as **Configure AI Agent Event** when the AI Agent trigger category is selected. The trigger event auto-populates from the binding; there is no event-name field to type or match. See `docs/reference/webex-connect.md` for details.

**Enable toggle**: Must be switched ON for the action to fire.

### Referencing Returned Variables in Action Description

- Use **quoted variable names**: `"first_name"`, `"confirmation_number"` -- CONFIRMED WORKING
- The LLM reads the description and knows to use these variable names from the Flow Outcomes response

### What Does NOT Work for Flow Outcomes Data

- `{{variable_name}}` syntax in action descriptions — returns the literal string `{{variable_name}}` instead of the value when referencing **Flow Outcomes return data**. Use quoted names instead: `"first_name"`, `"confirmation_number"`.

> **Important distinction:** `{{variable_name}}` DOES work for **custom data variables** injected at session start via Flow Designer State Event settings. See [Custom Data at Session Start](#custom-data-at-session-start-voice-only) below. The syntax fails only when referencing data returned by Flow Outcomes.

### Enable Toggle -- Most Common Oversight

Actions must be **ENABLED** (toggle ON) to fire. If the toggle is OFF, the action silently does not execute -- no error, no log, no indication. This is the single most common reason an action fails to fire.

### Standard Action Template

The fields above, assembled into one worked action. The last block is **not** an AI
Agent Studio field — it is the sample payload you paste on the Connect flow's
trigger node (see [Configure AI Agent Event (Sample JSON)](#configure-ai-agent-event-sample-json)).

```
Action Name: lookup_customer

Description:
Call this action when you need to look up a customer record.
Requires: phone_number (collected from caller)
Returns: "customer_first_name", "customer_last_name", "account_status"
Use "customer_first_name" to greet the caller by name after this action completes.

Input Entities: phone_number (required)

Fulfillment: select the Webex Connect Service, then select the Flow.

Sample JSON — paste on the Connect flow's trigger node, not here:
{
  "phone_number": "5551234567"
}
```

---

## Configure AI Agent Event (Sample JSON)

**Note:** Despite being referenced during AI Studio action setup, this JSON is configured in **Webex Connect** — on the trigger node of the action's flow (the **Configure AI Agent Event** node). See `docs/reference/webex-connect.md` for the full details.

This JSON tells Connect what variable shape the action sends. Required for every action.

### Rules

- One key per slot entity the action uses
- Use realistic example values
- Keys must match entity names exactly
- Configure this on the Connect flow's trigger node (**Configure AI Agent Event**), not in AI Agent Studio

### Example

```json
{
  "phone_number": "5551234567"
}
```

---

## Output Variables

AI Agent Studio does **not** have an output variables section. Outputs are returned to the agent via **Flow Outcomes** from the Webex Connect flow.

The agent reads returned values by the key names set in the Connect flow's Flow Outcomes settings. Reference those keys in the action description with quotes (e.g., `"confirmation_number"`).

### Where Flow Outcomes Lives in Webex Connect

Flow Outcomes is **not a canvas node**. It is configured at **Flow Settings > Flow Outcomes**, on the **Last Execution Status** row: enable **Notify**, confirm **Notify AI Agent** is the selected target, then enter the key/value pairs to return. "Last Execution Status captures the final node outcome and doesn't require a mapping," and Cisco describes the **Notify AI Agent** radio button as "enabled by default for the start node with 'AI Agent' as the trigger" [source: [Configure fulfilment flows for AI agent actions](https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions)].

> **UNVERIFIED — whether Notify AI Agent needs an explicit click.** Cisco documents it as a **radio button** "enabled by default for the start node with 'AI Agent' as the trigger", i.e. possibly already selected when you open the row; the tenant owner describes selecting it explicitly under a **Notification Settings** heading, a label that appears on no crawled Cisco page. **Whether it is pre-selected or a separate explicit click is unconfirmed — check this in the tenant UI.** Either way, confirm **Notify AI Agent** is the selected target before publishing. Owner: [`webex-connect.md` § Flow Outcomes] — reproduced here so this page works standalone; the owner doc wins on any disagreement.

There is **one key-set per flow** — every action flow returns a single set of keys, not one per branch.

### Payload Limit and Default Keys

- **Payload cap:** "The maximum length of payload can be 16000 characters" returned from the flow to the AI agent [source: [Configure fulfilment flows for AI agent actions](https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions)]. Trim or summarize large API responses in the Connect flow before returning them — do not pass a raw multi-record response straight through.
- **Default key-value pairs:** "The system provides default key-value pairs for TransactionID, service name, status code" [source: [Configure fulfilment flows for AI agent actions](https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions)]. These are supplied automatically — you do not need to add them, and they count toward the payload you return.

---

## Custom Event Fulfillment (Voice Only)

Autonomous agents have two fulfillment paths. The standard path uses Webex Connect flows (AI Agent trigger node → HTTP Request → Flow Outcomes configured in Flow Settings, not as a canvas node — see "Where Flow Outcomes Lives in Webex Connect" above). The alternative uses **custom event fulfillment** — the agent exits to Flow Designer for fulfillment, then Flow Designer returns the result via State Event.

**Channel support:** Voice channel only. Not available on digital channels.

**Use case:** PCI-compliant fulfillment where sensitive payment data must stay in Flow Designer and never pass through the AI agent or Webex Connect.

### Configure in AI Agent Studio

1. Navigate to the **Actions** tab > create or edit an action
2. In the **Fulfillment** section, select **"Set custom logic for fulfillment"**
3. The action will now exit to Flow Designer instead of triggering a Connect flow

### Flow Designer Side

When the agent calls this action, the Virtual Agent V2 activity exits:
- **StateEventName** = the action name
- **MetaData** = JSON with the collected slot values

The Flow Designer flow:
1. Parses `VirtualAgentV2.MetaData` for the input data
2. Routes on `VirtualAgentV2.StateEventName` (use a Case activity if multiple actions use custom fulfillment)
3. Executes the fulfillment logic (HTTP Request, database call, etc.)
4. Sets `event_name` and `event_data_string` flow variables with the result
5. Routes back to the Virtual Agent V2 activity, which sends the State Event to the agent

This is the same State Event resume mechanism used for scripted agent voice fulfillment. See `docs/reference/flow-designer-patterns.md` § Scripted Agent Fulfillment Pattern for the full activity chain — the pattern is identical for autonomous agents using custom event fulfillment.

### When to Use Custom Event Fulfillment vs. Connect Flows

| Factor | Connect Flows (standard) | Custom Event Fulfillment |
|--------|--------------------------|--------------------------|
| **PCI/compliance** | Data passes through Connect | Data stays in Flow Designer |
| **Build effort** | Need a separate Connect flow per action | Fulfillment logic in the existing Flow Designer flow |
| **Reusability** | Same Connect flow works for voice and digital | Voice only |
| **Debugging** | Connect flow debug logs | Flow Designer activity logs |
| **When to choose** | Default for most actions | PCI requirements, or when all actions need Flow Designer logic anyway |

---

<!-- SYNC: also update docs/reference/ai-agent-studio-scripted.md (Welcome Message / custom data mentions) when changing this section -->
## Custom Data at Session Start (Voice Only)

Developers can pass data from Flow Designer to an autonomous AI agent at the beginning of a session, before the agent speaks. This enables personalized welcome messages, dynamic instructions per customer, and optimized agent behavior.

**Channel support:** Voice channel only. Not available on digital channels.

### How It Works

1. In WxCC Flow Designer, configure the **Virtual Agent V2** activity's **State Event** settings
2. Leave the **Event Name** column blank (this signals session-start data, not a named event)
3. Enter custom data key-value pairs in the **Event Data** column (e.g., `customer_name` = `{{CallerName}}`)
4. The agent receives these as session-level variables accessible via `{{variable_name}}` syntax

### Where Custom Data Variables Can Be Used

| Location | Example |
|----------|---------|
| **Agent Goal** | "Help {{customer_name}} with their account" |
| **Welcome Message** | "Hi {{customer_name}}, thanks for calling!" |
| **Instructions** | "The caller is calling from {{calling_number}}. Use this to look up their account." |
| **Action Description** | "Call this when {{customer_name}} needs to check their order status" |
| **Slot Description** | "The customer's phone number is {{calling_number}}" |

### Example

A Flow Designer flow sets two custom data variables before the Virtual Agent V2 activity:
- `customer_name` = result of a CRM lookup by ANI
- `calling_number` = `{{NewContact.ANI}}`

The agent's Welcome Message uses them: "Hi {{customer_name}}, thanks for calling! I can see you're calling from {{calling_number}}. How can I help?"

### Custom Data vs. Flow Outcomes Variables

| Feature | Custom Data (`{{variable}}`) | Flow Outcomes (quoted names) |
|---------|------------------------------|------------------------------|
| **Set by** | Flow Designer State Event settings | Connect Flow Settings > Flow Outcomes |
| **When available** | Session start (before agent speaks) | After an action completes |
| **Syntax in AI Studio** | `{{variable_name}}` | `"variable_name"` (quoted in description) |
| **Scope** | Entire session | Per-action return |
| **Where it works** | Goal, Welcome Message, Instructions, Action descriptions, Slot descriptions | Action descriptions only |

> **Key rule:** `{{variable_name}}` works for custom data. It does NOT work for Flow Outcomes data. If you see literal `{{variable_name}}` in agent responses, check whether you're referencing custom data (correct syntax) or Flow Outcomes data (use quoted names instead).

---

<!-- SYNC: also update docs/reference/ai-agent-studio-scripted.md (Testing section) when changing this section -->
## Testing

### Chat Preview

- Use the **Preview** panel in AI Agent Studio
- Chat preview is **non-deterministic** -- the LLM may skip actions unpredictably. ⚠ **UNVERIFIED** — this is a project observation, not a documented behaviour: no Cisco page states it, and it is on the manual-confirmation list [`docs/plans/2026-07-25-findings-corpus-audit.md`]. Treat it as a working assumption, not a platform guarantee
- If an action doesn't fire in chat preview, add forceful language before assuming a config issue

### Voice Preview

- Voice preview is **more reliable** and closer to production behavior
- Test via WxCC Flow Designer using the **Virtual Agent V2** activity with **Webex AI Agent Autonomous** selected in its **Contact Center AI Config** dropdown (see CCAI Config below)

---

<!-- SYNC: also update docs/reference/ai-agent-studio-scripted.md (Deployment section) when changing this section -->
## Deploying the Agent

1. In AI Agent Studio, click **Deploy** (or **Publish**)
2. Note the **Agent ID** -- identifies the published agent when you link it to WxCC (see CCAI Config below). There is no Contact Center AI Config to create

> **Publishing needs at least one action or one knowledge base** (observed by Adam 2026-10-16, on an imported autonomous agent; not checked for scripted agents). An agent whose only tool is the system **Agent handover** could not be published. Import JSON cannot supply either one: an action needs live Webex Connect flow IDs, and `kb_ids` must stay `[]` [`ai-agent-studio-import-json.md`]. What unblocked it: put the facts the agent needs in the instructions, upload the same facts as a `.txt` knowledge base in AI Agent Studio, attach it to the agent, then publish. The call then worked end to end through the entry point, the flow and Virtual Agent V2. Creating or importing an agent has no API; it is a UI step.

---

<!-- SYNC: also update docs/reference/ai-agent-studio-scripted.md (Deployment section) when changing this section -->
## CCAI Config (Linking Agent to WxCC)

**CCAI (Contact Center AI) is Google's product. Webex AI Agent is Cisco's own. They are different products** — a Webex AI Agent build never creates a Contact Center AI Config; it only *selects* one that already exists.

For a Webex AI Agent on **voice**, the link to Webex Contact Center is made entirely in Flow Designer:

1. In AI Agent Studio, **Publish** the agent
2. In WxCC Flow Designer, open the **Virtual Agent V2** activity
3. In its **Contact Center AI Config** dropdown, select **Webex AI Agent Autonomous** — "Select **Webex AI Agent Autonomous** from the **Contact Center AI Config** drop-down list." [source: [Integrate AI Agent with Voice and Digital channels](https://help.webex.com/en-us/article/s0qro1/Integrate-AI-Agent-with-Voice-and-Digital-channels)]
4. Select your published agent

There is no Control Hub step. On **digital** channels no Contact Center AI Config is involved at all — the AI Agent is selected directly in the Webex Connect flow's AI Agent node.

**Prerequisite:** a one-time tenant enablement is required before **Webex AI Agent Autonomous** appears in that dropdown [`wxcc-platform.md § Webex AI Agent Tenant Prerequisite`].

### Why there is no Control Hub step

The Control Hub creation flow **Services > Contact Center > Tenant settings > Integrations > Features tab > New > Contact Center AI Config** belongs to Google CCAI / BYOVA / Agent Answers — not to Webex AI Agent. Its stated prerequisite is "Ensure that the service-specific integration connector is created. For example, **Google** Contact Center AI connector", and its **Contact Center AI Connector** field offers exactly three options — "Webex CCAI", "Integration Connector", "Service App" — with no Webex AI Agent option [source: [Create a Contact Center AI configuration](https://help.webex.com/en-us/article/npbt02j/Create-a-Contact-Center-AI-configuration)] (page updated November 03, 2025; checked 2026-07-27). That procedure is documented in `wxcc-platform.md` / `wxcc-setup.md` for the Google path; do not run it as part of a Webex AI Agent build.

For a Webex AI Agent, Cisco documents only the *selection* — "Select **Webex AI Agent Autonomous** from the **Contact Center AI Config** drop-down list." / "Select **Webex AI Agent Scripted** from the **Contact Center AI Config** drop-down list." — with no creation step anywhere in that article [source: [Integrate AI Agent with Voice and Digital channels](https://help.webex.com/en-us/article/s0qro1/Integrate-AI-Agent-with-Voice-and-Digital-channels)]. The Webex AI Agent Studio Administration guide mentions neither "Contact Center AI Config" nor "Tenant settings" nor the "Features tab". Confirmed by the platform owner 2026-07-27.

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Action never fires | Action enable toggle is OFF | Turn the toggle ON |
| Action never fires (toggle is ON) | The action has no flow bound to it — the Service and Flow were never selected in the action's Fulfillment section | In AI Agent Studio > Actions > the action > Fulfillment, select the Webex Connect **Service**, then select the **Flow**. Names are irrelevant; the binding is the selection |
| Action never fires (toggle is ON, flow is bound) | ⚠ **UNVERIFIED** — likely that the bound Connect flow is not live. The exact condition (draft vs. live) was never tested; Cisco is cited only for "only flows whose start node is AI Agent are listed" [`webex-connect.md` § How an action binds to a flow], which says nothing about live vs. draft | Publish/make the flow live in Webex Connect, then retest — harmless either way, and it rules the condition out |
| Agent skips a required action | LLM non-determinism | Strengthen instruction language: "You MUST call..." |
| Variables returned as literal strings | Using `{{variable}}` syntax to reference Flow Outcomes data | Use quoted variable names for Flow Outcomes data: `"variable_name"`. Note: `{{variable}}` DOES work for custom data variables from State Event — see Custom Data section. |
| Agent gives wrong time | Missing timezone conversion note in instructions | Add explicit UTC-to-local conversion instruction |
| Chat preview is unpredictable | ⚠ **UNVERIFIED** — believed to be expected LLM non-determinism, but no Cisco source states it; on the manual-confirmation list | Use voice preview for reliable testing |
| Agent doesn't greet caller | Welcome Message field is empty | Set Welcome Message (separate from Instructions) |
| Agent doesn't appear in the **Virtual Agent V2** agent selector | Agent not deployed | Click Deploy in AI Agent Studio first |
| **Webex AI Agent Autonomous** is missing from the **Contact Center AI Config** dropdown | One-time tenant enablement not done | See [`wxcc-platform.md § Webex AI Agent Tenant Prerequisite`] |
| Flow Outcomes data doesn't reach agent | **Notify AI Agent** is not the selected target in the Connect flow — it is a **radio button**, not a toggle | In Webex Connect: Flow Settings > Flow Outcomes > **Last Execution Status** row, enable **Notify** and confirm **Notify AI Agent** is selected [`webex-connect.md` § Flow Outcomes] |

---

## Key Sources

- [Webex AI Agent Studio Administration Guide](https://help.webex.com/en-us/article/ncs9r37/Webex-AI-Agent-Studio-Administration-guide)
- [Configure custom data and custom events for AI agents](https://help.webex.com/en-us/article/n5uo60x/Configure-custom-data-and-custom-events-for-AI-agents)
- [Guidelines and best practices](https://help.webex.com/en-us/article/nelkmxk/Guidelines-and-best-practices-for-automating-with-AI-agent)
- [Use AI agents for customer interactions](https://help.webex.com/en-us/article/s0qro1/Use-AI-agents-for-customer-interactions)
- [Configure fulfilment flows for AI agent actions](https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions) -- Service/Flow selection, Flow Outcomes key-value return, 16000-character payload cap, default TransactionID / service name / status code keys

## See Also

- [ai-agent-studio-scripted.md](ai-agent-studio-scripted.md) — the scripted counterpart, for choosing between the two agent types
- [webex-connect.md](webex-connect.md) — the Connect flow an agent action calls, where the action name must match the Connect event name
- [flow-designer-patterns.md](flow-designer-patterns.md) — how an agent is placed in a Flow Designer flow
- [ai-agent-studio.md](../playbooks/ai-agent-studio.md) — the step-by-step setup that pairs with this reference
