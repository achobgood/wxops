# Design AI Agent — Build Sequence

Read this when the design doc is approved (`SKILL.md` § DESIGN PHASE).

## BUILD PHASE

### Platform Dependency Chain

**Autonomous agents:**
```
Connect (build action flows) → AI Agent Studio (configure actions, select flows) → WxCC Flow Designer (route calls)
```
Each platform depends on the previous one. You cannot configure an action in AI Agent Studio until its Connect flow exists and is made live.

**Scripted agents:**
```
AI Agent Studio (create agent, intents, entities, responses) → Connect (build fulfillment logic inline) → WxCC Flow Designer (route calls)
```
Scripted agents are configured first in AI Agent Studio (intents, entities, responses), then fulfillment flows are built around them. There are no standalone action flows.

---

### If Scripted: Build in AI Agent Studio First

Scripted agents are built differently. Follow `docs/playbooks/scripted-agent-build.md` for the full step-by-step guide. The high-level sequence:

1. **Create the agent** in AI Agent Studio (select Scripted, choose AI engine). **Check for built-in templates first** — AI Agent Studio offers importable scripted agent templates (e.g., "Doctor's Appointment", "Track Package") that come pre-configured with intents, entities, utterances, and responses. If the user's use case aligns with an available template, recommend starting from it and customizing rather than building from scratch.
2. **Create entities** in the Scripts > Entities tab (create ALL entities before intents)
3. **Create intents** with utterances, slot linkages, and context chains
4. **Create responses** in the Response Designer — per-channel, with conditional rules
5. **Test** via Chat Preview and Voice Preview
6. **Build fulfillment** (if intents require API calls):
   - **Voice**: Add Custom Event responses, wire Flow Designer for fulfillment and state_update
   - **Digital**: Build fulfillment branching inline in the Webex Connect conversation flow (Branch on template_key → HTTP → send response → loop)
7. **Deploy** — Voice: Publish, then select the agent in the Flow Designer **Virtual Agent V2** activity. Digital: Publish, then select the agent in the Connect flow's **AI Agent** node.

For each step, present the configuration to the user (intent definitions, entity types, response text, etc.) and wait for confirmation before proceeding.

**For intents that require API calls:** Invoke `Skill("build-scripted-fulfillment")` for each intent that needs fulfillment. The skill's Step 1 reads `ai-agent-studio-scripted.md` (fulfillment section), `webex-connect.md`, and `db-integration.md` — these contain the template_key branching pattern, HTTP node conventions, and DB header requirements. Do NOT generate fulfillment config yourself — the skill is the only source of truth for the digital (Data Parser → Branch on template_key → HTTP → Evaluate → Channel Reply → loop) and voice (Custom Event → Flow Designer HTTP → state_update) patterns.

**For digital channels:** After configuring the agent, also invoke `Skill("build-digital-inbound")` to build the conversation flow. The skill's Step 1 reads `digital-inbound.md`, `digital-inbound-agent.md`, `wxcc-platform.md`, and `ai-agent-studio.md` — these define the conversation loop architecture and channel-specific node settings. Do NOT generate the conversation flow yourself. The fulfillment branching (from `build-scripted-fulfillment`) is added inline within this conversation flow.

**After the agent is fully configured and deployed**, proceed to the "AFTER ALL ACTIONS ARE BUILT" section for WxCC routing setup — but skip the "Final Agent Instructions" step (scripted agents don't have instructions).

### If Autonomous: Build Actions One at a Time

Build actions one at a time, in the order listed in the design doc. For each action:

### Step 1: Test the Backend Query — `[Terminal / API Client]`

Before building anything in Webex Connect, verify the database query works.

- Construct the curl command (or equivalent) using the user's actual API credentials and test data
- **Show the curl command to the user and ask if they want you to run it.** Do NOT run it automatically.
- If the user approves, run it and verify:
  - HTTP 200 (or 201 for POST)
  - Response shape matches what the output variables will expect
  - Correct data is returned
  - Auto-generated fields appear in POST responses
- If the query fails: debug and fix before proceeding

### Step 2: Build the Connect Flow — `[Webex Connect]`

**YOU MUST call `Skill("build-action")` here.** The skill's Step 1 reads `webex-connect.md`, `db-integration.md`, and `action-config.md` — these contain required HTTP header values, Flow Outcomes conventions, and the output format that you cannot generate correctly without reading. Do NOT summarize, condense, or generate the action config yourself — the skill is the only source of truth. If you skip it, the user will not get the step-by-step walkthrough they need.

After the skill output, remind the user:
- Use the variable picker -- never type variable references manually
- **Verify Notify AI Agent is selected** in Flow Settings > Flow Outcomes > the **Last Execution Status** row > enable **Notify** > confirm **Notify AI Agent** is the selected notification target (**UNVERIFIED** whether it is pre-selected by default or an explicit click under a **Notification Settings** heading — Cisco documents it as enabled by default for the AI Agent start node, the platform owner describes selecting it explicitly, and the two have not been reconciled; check the tenant UI and confirm it is selected either way — open item **O2** in `docs/plans/2026-07-25-documentation-remediation-backlog.md` §6)
- Rename `id` to a descriptive name (e.g., `customer_id`) after parsing sample JSON
- If the action involves a lookup that might return no results (e.g., patient not found), add a **Branch node** after the HTTP node to check `$(nX.https.statusCode)`. There is **no Flow Outcomes node** to route to — the outcome payload is configured once at flow level, and there is **one key-set per flow**, so you cannot return a different payload per Branch leg. Set a status/error variable on each leg, converge the legs into the **End (END FLOW)** node, and return that variable through the single **Last Execution Status** key-set so the agent gets an error message it can use conversationally. See `docs/reference/webex-connect.md` § "Flow Outcomes (Flow Settings — NOT a node)" and `docs/reference/webex-connect-advanced.md` for the Branch node pattern.

Wait for the user to confirm they have built the flow and made it live.

**For digital channels:** After all action flows are built and confirmed live, also invoke `Skill("build-digital-inbound")` to set up the inbound conversation flow on the selected digital channel. The skill's Step 1 reads `digital-inbound.md`, `digital-inbound-agent.md`, `wxcc-platform.md`, and `ai-agent-studio.md` — these define the conversation loop architecture, channel-specific triggers, and escalation patterns. Do NOT generate the conversation flow yourself. This flow is what connects the customer's channel (SMS, WhatsApp, Live Chat, Email) to the AI Agent — without it, the action flows exist but have no way to receive inbound messages. Build this after the action flows so the AI Agent node in the Connect flow can reference the configured agent with all its actions.

### Step 3: Configure AI Agent Studio — `[AI Agent Studio]`

**YOU MUST call `Skill("configure-ai-agent")` here.** The skill's Step 1 reads `ai-agent-studio.md` for Studio conventions (action description syntax, entity types, instruction structure) and the current agent instructions. Do NOT summarize or generate the configuration yourself — the skill generates the complete AI Agent Studio configuration (agent goal, welcome message, action description, input entities, updated agent instructions) formatted for direct copy-paste.

Note: Configure AI Agent Event sample JSON is done in **Webex Connect** on the flow's **trigger node** (Trigger category = **AI Agent**), not in AI Agent Studio. It should already be configured during the Connect flow build (Step 2).

Present to the user.

**Remind the user:**
- Toggle the action **ENABLED** -- this is the #1 most common oversight
- Bind the action to its flow by **selecting** the Webex Connect **Service**, then the **Flow** — the action name does **not** have to match the Connect event name, and there is no case-sensitivity requirement [`ai-agent-studio.md` § Fulfillment; `configure-ai-agent/reference.md`]
- Do NOT use `{{variable_name}}` syntax in the description -- use quoted names like `"first_name"`

Wait for the user to confirm they have configured the action.

### Step 4: Test End-to-End — `[AI Agent Studio → Voice/Chat Preview]`

Ask the user to test via voice preview (preferred) or chat preview:

> "Try testing this action now. Voice preview is more reliable than chat. Say something that should trigger the [action_name] action and let me know what happens."

**If it works:** Mark the action as complete in the design doc. Update the build checklist. Move to the next action.

**If it fails:** Invoke the `/wxcc-debug` skill. Follow the debugging protocol:
1. Check database/API logs first (for Supabase: check API logs for the request)
2. Check the HTTP status code and match to known error patterns
3. Verify the action is enabled in AI Studio
4. Verify the action's **Fulfillment** binding — in AI Agent Studio open the action and confirm the correct Webex Connect **Service** and **Flow** are selected, and that the flow is live in Connect. There is no event name to match; the binding is the selection
5. Verify **Notify AI Agent** is the selected notification target — Flow Settings > Flow Outcomes > the **Last Execution Status** row > enable **Notify** > confirm **Notify AI Agent** is the selected notification target. Have the user check the tenant UI and confirm it is selected either way; do not assume it is already on (see open item **O2** in `docs/plans/2026-07-25-documentation-remediation-backlog.md` §6)
6. If no request appears in logs: the action never fired -- likely an LLM instruction issue or the action is disabled

### Step 5: Repeat

Move to the next action in the design doc. Repeat Steps 1-4.

---

## OUTBOUND FLOW BUILD (if applicable)

If the design doc includes outbound notification flows (see Section 4b), build them AFTER all inbound AI agent actions are complete. Outbound flows have no AI Agent Studio dependency, so they're simpler and independent.

For each outbound flow in the design doc:

### Step 1: Confirm Requirements

> "Your design includes an outbound notification flow: [flow-name]. I'll walk you through building it in Webex Connect now -- this uses a different pattern from the AI agent actions (webhook trigger and delivery nodes instead of an AI Agent trigger node and Flow Outcomes). Ready to start?"

### Step 2: Build the Connect Flow

Invoke the appropriate skill based on the flow's channel(s) from the design doc Section 4b:

- **Voice-only** (TTS call, paging): **`Skill("build-outbound-flow")`** — Step 1 reads `outbound-voice.md`, `webhook-triggers.md`, and `outbound-flow-config.md`
- **SMS, Email, WhatsApp, RCS, Apple Messages, or Multi-channel**: **`Skill("build-notification")`** — Step 1 reads channel-specific playbooks, reference docs, and `webhook-triggers.md`

The skill walks the user through building the flow step by step. Do NOT summarize or generate the config yourself — the skills read platform docs that contain required node settings, field values, and conventions.

### Step 3: Test End-to-End

Ask the user to test via curl:

> "Fire the webhook with a test payload and verify: (1) message delivered to the correct channel, (2) dynamic variables resolved (not literal `$(nX.var)` text), (3) for RCS/Apple Messages — test the SMS fallback by sending to a non-supported device or customer without an active session. Check Flow Debug in Connect for the execution trace."

### Step 4: Repeat

Move to the next outbound flow in the design doc.

---

## AFTER ALL ACTIONS ARE BUILT

Once every action in the design doc is marked complete:

### 1. Final Agent Instructions — `[AI Agent Studio → Instructions tab]` (Autonomous Only)

**Skip this step for Scripted agents** — scripted agents do not have an Instructions tab. Their behavior is fully defined by intents, entities, responses, and context management.

**For Autonomous agents:** Generate the complete agent instructions covering ALL actions. These go in the Instructions tab in AI Agent Studio.

Structure:
- **Identity and purpose**: "You are a [role] for [organization]..."
- **Required first action**: "You MUST call [lookup_action] before anything else. EVERY conversation starts with identity verification. No exceptions."
- **Action-by-action guidance**: for each action, describe when to call it, what it returns, and how to use the returned data
- **Timezone conversion**: if the database returns UTC, include explicit conversion instructions ("All times are in UTC. You MUST convert to [timezone] by subtracting/adding N hours. Never mention UTC to the caller.")
- **Escalation**: when to hand off to a human and what to say
- **Ground rules**: what the agent must NOT do (domain-specific restrictions -- e.g., no unauthorized commitments, never reveal internal IDs, never guess answers)
- **Conversation style**:
  - One to two sentences at a time -- this is a phone call, not an email
  - Do not stack multiple questions in one response
  - Confirm before committing -- read back details and wait for "yes" before creating/modifying records
  - Use natural transitions: "Let me check on that" or "One moment"
  - Wrap up: "Is there anything else I can help with?"
  - Sign off warm: "Thanks for calling, [Name]. Have a great day!"

### 2. Welcome Message — `[AI Agent Studio → Welcome Message field]`

Generate a welcome message (separate field in AI Agent Studio, not part of instructions):

> "Thanks for calling [Organization]! I can help you with [capability list]. How can I help you today?"

### 3. WxCC Control Hub Setup — `[Control Hub → Contact Center]`

If the user hasn't set up WxCC routing yet, walk them through it. Read `docs/reference/wxcc-platform.md` for the full guide:

1. Verify a Site is provisioned
2. Create a Team (for human agents who handle escalations)
3. Create a Queue (assign the team)
4. Create an Entry Point:
   - **Voice**: Telephony entry point. Assign a PSTN number.
   - **Digital**: Channel-specific entry point (SMS, WhatsApp, Live Chat, Email). Configure the channel asset in Connect.
5. Assign a PSTN number (voice only)
6. Create the routing flow:
   - **Voice**: Create a WxCC Flow Designer flow with Virtual Agent V2 node → Escalated: Queue Contact, Handled: Disconnect, Errored: Disconnect. Publish and link to the entry point.
   - **Digital**: Flow Designer is **NOT used**. Instead, invoke `Skill("build-digital-inbound")` to build a Webex Connect flow that handles the full conversation. The skill's Step 1 reads `digital-inbound.md`, `digital-inbound-agent.md`, `wxcc-platform.md`, and `ai-agent-studio.md` — do NOT generate the flow yourself. The Connect flow pattern is: Start (channel trigger) → Search/Create Conversation → AI Agent (Process Message) → Channel Reply → Receive → Loop → Queue Task (escalation). The Connect flow IS the routing — there is no separate Flow Designer step.
7. Publish and link:
   - Voice: publish the Flow Designer flow and link to the entry point
   - Digital: make the Connect flow live (it auto-routes based on the channel asset configuration)

### 4. Connect the Agent to Flow Designer — `[WxCC Flow Designer → Virtual Agent V2]`

**Note: this step is voice-only.** For digital channels, the AI Agent is selected directly in the Connect flow's AI Agent node — there is no Contact Center AI Config at all. Skip this step for digital builds.

**Prerequisite:** a one-time tenant enablement is required before "Webex AI Agent Autonomous" / "Webex AI Agent Scripted" appear in the Contact Center AI Config dropdown [source: `wxcc-platform.md` § Webex AI Agent Tenant Prerequisite].

Walk the user through connecting the published agent to the flow (voice only):

1. In AI Agent Studio: click **Publish** to publish the agent.
2. In WxCC Flow Designer: open the flow and select the **Virtual Agent V2** activity.
3. In that activity's **Contact Center AI Config** dropdown, select:
   - **Autonomous**: "Webex AI Agent Autonomous"
   - **Scripted**: "Webex AI Agent Scripted"
4. Select your published agent.

> **There is no Control Hub step in a Webex AI Agent build.** The Control Hub creation flow (Services > Contact Center > Tenant settings > Integrations > Features tab > New > Contact Center AI Config) belongs to Google CCAI / BYOVA / Agent Answers — its stated prerequisite is "Ensure that the service-specific integration connector is created. For example, Google Contact Center AI connector", and its Contact Center AI Connector field offers only "Webex CCAI", "Integration Connector", and "Service App" [source: https://help.webex.com/en-us/article/npbt02j/Create-a-Contact-Center-AI-configuration]. For a Webex AI Agent, Cisco says only "Select **Webex AI Agent Autonomous** from the **Contact Center AI Config** drop-down list" [source: https://help.webex.com/en-us/article/s0qro1/].

### 5. Flow Designer Flow — `[WxCC Flow Designer]` (Voice) / `[Webex Connect]` (Digital)

**Voice:** Create (or update) the Flow Designer flow that routes calls to the AI agent:
- Virtual Agent V2 node with Escalated → Queue Contact, Handled → Disconnect, Errored → Disconnect

**Digital:** Flow Designer is **NOT used** for digital channels. Instead, invoke `Skill("build-digital-inbound")` to create the Webex Connect flow that handles the full inbound conversation. The skill's Step 1 reads `digital-inbound.md`, `digital-inbound-agent.md`, `wxcc-platform.md`, and `ai-agent-studio.md` — do NOT generate the flow yourself. The flow pattern is:

1. **Start** (channel trigger — SMS, WhatsApp, Live Chat, or Email)
2. **Search/Create Conversation** (link the channel session to a WxCC conversation)
3. **AI Agent** (Process Message — selects the AI Agent directly, no Contact Center AI Config)
4. **Channel Reply** (send the agent's response back to the customer)
5. **Receive** (wait for the next customer message)
6. **Loop** (back to AI Agent for multi-turn conversation)
7. **Queue Task** (escalation — routes to a human agent queue in WxCC)

Reference `docs/reference/digital-inbound.md` for the architecture and `docs/playbooks/digital-inbound-agent.md` for the step-by-step build guide.

### 6. Final End-to-End Test

> "Everything is wired up. Let's do a full test. Dial the PSTN number (or open the chat channel) and run through a complete conversation: identify yourself, try each action, and try asking for a human agent. Let me know how it goes."

---

## COMPACTION RECOVERY

If context compacts during a build session:

1. Immediately read `docs/plans/` to find the current design doc
2. Read the design doc -- check which actions are marked complete vs pending in the build checklist
3. Resume from the next pending action
4. Tell the user:

> "I recovered from a context reset. Based on your design doc at [path], we've completed [list completed actions] and need to build [next pending action] next. Ready to continue?"

This is why the design doc is saved before building starts -- it is the compaction safety net.

---

## CRITICAL RULES

These are non-negotiable. Violating any of these causes silent failures that are difficult to debug.

<!-- SYNC: Shared rules (both agent types): Variable Picker, Phone Number Entity Type, Prohibited Nodes, Test Before Configure, Timezone Handling, Array Responses, UUIDs as Input Entities, Design Doc Requirement -->
<!-- SYNC: Autonomous-only rules: Action Descriptions, Enable Toggle, Flow Outcomes Mode, Notify AI Agent, Action vs Field -->
### Variable Picker (Connect)
NEVER type Webex Connect variable references manually. Always show the format `$(n{X}.aiAgent.variable_name)` and tell the user to use the variable picker icon in the URL or body field. Manually typed variables arrive empty at runtime with no error message.

### Action Descriptions — Flow Outcomes Data (AI Studio)
NEVER use `{{variable_name}}` syntax in action descriptions **to reference Flow Outcomes return data**. It returns the literal string. Use quoted names: `"first_name"`, `"order_number"`. This is confirmed working.

**Exception:** `{{variable_name}}` DOES work in action descriptions (and Goal, Welcome Message, Instructions, Slot descriptions) for **custom data variables** passed from Flow Designer at session start. See `docs/reference/ai-agent-studio.md` "Custom Data at Session Start".

### Enable Toggle (AI Studio)
ALWAYS remind users to enable actions in AI Studio. This is the single most common oversight. When the toggle is OFF, the action silently does not fire -- no error, no log, nothing.

### Flow Outcomes Mode (Connect)
There is **no Flow Outcomes node** — Flow Outcomes is a flow-level settings area reached from the **Flow Settings** button on the Flow Builder page. In the **Last Execution Status** row, ALWAYS choose **Enter key and value**, NEVER **Enter JSON**. Enter JSON mode does not resolve variables -- it returns literal strings like `$(n3.customer_id)` instead of actual values. See `docs/reference/webex-connect.md` § "Flow Outcomes (Flow Settings — NOT a node)".

### Notify AI Agent (Connect)
ALWAYS remind users to verify **Notify AI Agent** is selected: Flow Settings > Flow Outcomes > the **Last Execution Status** row > enable **Notify** > confirm **Notify AI Agent** is the selected notification target. **UNVERIFIED** whether it is pre-selected by default or an explicit click under a **Notification Settings** heading — Cisco documents it as enabled by default for the AI Agent start node, the platform owner describes selecting it explicitly, and the two have not been reconciled. Have the user check the tenant UI and confirm it is selected either way — open item **O2** in `docs/plans/2026-07-25-documentation-remediation-backlog.md` §6. Do not assume it is already on. If it is not enabled, the flow runs but the agent never receives the response data.

### Test Before Configure
ALWAYS run a live test (curl or equivalent) against the user's database BEFORE handing them the action config. Verify the query returns expected data. Never skip this step.

### Timezone Handling
When the database returns timestamps in UTC, add explicit timezone conversion notes in EVERY action description that returns times, AND in the agent instructions. The LLM will NOT convert automatically without explicit instructions.

### Phone Number Entity Type
Phone number entity type = **String**, not Number. Using Number causes issues with leading zeros, formatting, and length validation.

### Array Responses
Avoid array responses where possible. LLMs struggle with arrays -- they may ignore items, miscount, or lose track. Use single-object response headers when available. If arrays are unavoidable, limit to 3-5 items.

### UUIDs as Input Entities
Never use UUIDs as input entities that the **caller** must provide. Callers cannot say UUIDs on a phone call. Use human-speakable identifiers (phone number, email, confirmation number) for caller-provided inputs.

**Exception:** UUIDs returned by one action and consumed by the next (e.g., `test_id` from `get_test_info` passed to `create_appointment`) are acceptable. The LLM carries these in conversation context, not from caller speech. Monitor for reliability — if the LLM drops a UUID between actions, redesign to use a lookup-by-name pattern instead.

### Prohibited Nodes (Connect)
NEVER use these nodes in AI Agent flows -- they cause 30-second timeouts:
- Delay
- Social Hour
- Receive Node
- Call Workflow

### Action vs. Field
NEVER create a separate action just to retrieve additional columns from the same record. If the data comes from the same table and the same query with no new caller input required, add it as an output variable on the existing action. New actions are for new triggers, new tables, or new HTTP methods.

When reviewing a proposed action list, ask: "Could this be an output variable on an existing action instead?" If yes -- collapse it. This keeps the agent simpler, faster, and easier to debug.

### Design Doc Requirement
ALWAYS save the design to `docs/plans/` before starting the build phase. This is the compaction recovery safety net. If context resets mid-build without a design doc, all progress is lost.

### WhatsApp Template Parameters
WhatsApp template parameters are always sequential (`{{1}}`, `{{2}}`), never named (`{{variable_name}}`). Do not use named placeholders even in drafts or examples. Named parameters do not exist in WhatsApp's template system and mislead users.

### Schema Discrepancy Resolution
When a schema discrepancy is identified during curl testing (e.g., a column name mismatch between the user's schema and the query), RESOLVE it before generating the final config. Never produce a config with a known column mismatch.

### Never Fabricate User Answers
Never fabricate user answers. If a question goes unanswered, re-ask it or mark the field as TBD in the design doc. Do not fill in default values and present them as if the user provided them.

### User-Provided Naming
When the user provides explicit action or intent names, use them exactly as given. If you want to suggest alternatives, propose them and wait for approval before using them in the design doc.

### WhatsApp 24-Hour Window in Designs
When the design includes outbound WhatsApp notifications, always document whether the message falls inside or outside the 24-hour session window. Agent-initiated messages outside the window require an approved template message — note this constraint explicitly in the design doc.

### Database Confirmation Before Schema Discovery
The database backend must be confirmed (Question 7 answered) before any schema discovery attempt. Do not assume Supabase or any other backend. Do not pull or inspect schema until the user confirms what database they use.

---

