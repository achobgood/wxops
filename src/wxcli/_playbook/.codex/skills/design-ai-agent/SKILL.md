---
name: design-ai-agent
description: |
  Start a new Contact Center build whose type is not settled yet: interviews one
  question at a time, decides AI agent, IVR, notification or digital channel, and
  writes the design doc to docs/plans/. Hands off to design-flow or
  design-scripted-agent once the type is settled.
allowed-tools: Read, Grep, Glob, Bash, Skill
argument-hint: [what you want to build]
---

# Design AI Agent Workflow

## When to use this skill

Use it for a new Contact Center build from scratch whose type the user has not settled yet (AI agent, IVR, outbound notification or digital channel). Mid-build work goes to the specific skill instead (root `AGENTS.md` § Routing Table). The build spans three platforms:
- **Webex Connect**: flow-based integration layer where HTTP nodes call backend APIs
- **Webex AI Agent Studio**: LLM configuration layer where you define the agent's personality, slot entities, and actions
- **Webex Contact Center (WxCC)**: routing layer that connects phone numbers and digital channels to the AI agent via Flow Designer

## CONTINUATION RULE (READ THIS FIRST)

**If the user is answering a question you already asked, do NOT use any tools.** No file reads, no Glob, no Bash, no template reads. Just process their answer conversationally and ask the next question. Tools are only needed during:
- First-time setup detection (your very first message only)
- Build Phase (when generating action configs via skills)
- Design Phase (when reading the design doc template)

During the Interview Phase, you are just having a conversation. No tools required.

---

## FIRST-TIME SETUP DETECTION

**Run these checks ONLY on your very first message.** If this is a continuation (the user is answering a question), skip to the Interview Phase.

On first invocation, use the Glob tool (not Bash) to check for files. Run all three checks in parallel in a single tool call, then greet the user based on the results.

1. **Does `.codex/config.toml` have a `supabase` (database) server with real values, not the `YOUR_SUPABASE_…` placeholders?** (Glob for `.codex/config.toml`, then read it)
   - If YES: read it to identify the backend. Proceed to check 2.
   - If NO: the user has no database MCP connection yet. Before starting the interview, ask what database or API their data lives in.
     - If **Supabase**: help them fill in the switched-off `supabase` entry in their MCP config (`.codex/config.toml`) — the server runs `npx @supabase/mcp-server-supabase@latest --project-ref {ref}` and needs their Supabase project ref (in place of `YOUR_SUPABASE_PROJECT_REF`) plus a personal access token (in place of `YOUR_SUPABASE_ACCESS_TOKEN`); then, in `.codex/config.toml`, remove `"supabase"` from `disabledMcpjsonServers` and add it to `enabledMcpjsonServers`. Once connected, the agent can query their schema during the interview to make smarter suggestions.
     - If **another backend**: note it and move on. You'll gather schema details in Question 7. Don't block the interview — non-MCP users may not have a schema ready to paste upfront.

2. **Does `docs/plans/` contain any design docs?** (Glob for `docs/plans/*.md`)
   - If YES: ask the user -- "I found an existing design doc at [path]. Are you continuing this build, or starting a new agent?" Wait for their answer before proceeding.
   - If NO: this is a fresh start.

3. **Does the project have reference docs?** (Glob for `docs/reference/*.md`)
   - If missing: warn the user that platform reference files are not present and the build may require more manual input.

After the checks complete, greet the user and begin the Interview Phase with Question 1.

---

## INTERVIEW PHASE

**CRITICAL RULE: Ask exactly ONE question per message. Never combine questions from different steps. Wait for the user's answer before asking the next question. The numbered questions below are sequential steps -- each one is a separate conversational turn.**

**No question may be skipped.** Even if the user volunteers information that seems to cover a future question, you must still ask it when you reach it — confirm what you heard, fill in gaps, and get explicit agreement before moving on.

### Question 1: Use Case

> "What should your AI agent do?"

Get the use case in the user's own words. Understand the domain (healthcare scheduling, customer service, order tracking, IT helpdesk, etc.). Listen for what actions the caller should be able to perform.

**STOP. Wait for the user's response before proceeding.**

### Use Case Branch: Inbound vs. Outbound

After Question 1, determine whether the user needs an **inbound AI agent** or an **outbound notification flow**:

| Signal | Pattern | Path |
|--------|---------|------|
| Caller dials in, asks questions, agent responds | Inbound AI agent | Continue with Question 2 below |
| System initiates call based on event (order ready, status change, reminder) | Outbound notification | Redirect to outbound path |
| Caller dials in, system connects to on-call staff (sequential dialing, find-me/follow-me) | Inbound voice flow (non-agent) | Redirect to inbound voice path |
| Caller dials in, IVR menu, queue routing, business hours, DNIS routing, data dip + route, skill-based routing, callback offer, hold treatment | Flow Designer voice flow (non-agent) | Redirect to Flow Designer path |
| Customer texts a keyword/command, system processes and replies (no AI agent, no conversation loop) | Inbound SMS (non-agent) | Redirect to inbound SMS path |
| Caller dials in AND system also sends notifications | Both | Build the inbound agent first, then outbound flow separately |

**If inbound voice (non-agent):** Tell the user this is an inbound voice flow, not an AI agent. The caller dials in and the flow handles the call directly — playing greetings, collecting DTMF input, looking up data mid-call, or connecting to another party via Call Patch. No AI Agent Studio is involved. Point the user to `docs/playbooks/inbound-voice.md` for general inbound voice handling, and `docs/playbooks/sequential-dialing.md` for on-call connect / sequential dialing patterns. These playbooks cover Start node (Inbound Call trigger), Voice Node Group behavior, Play/Collect Input/Call Patch configuration, and complete flow examples.

Signal phrases for inbound voice (Connect):
- "caller dials in and hears a greeting..." → inbound voice (`inbound-voice.md`)
- "connect the caller to on-call staff..." → sequential dialing (`sequential-dialing.md`)
- "try multiple numbers until someone answers..." → sequential dialing (`sequential-dialing.md`)
- "find-me/follow-me..." → sequential dialing (`sequential-dialing.md`)
- "escalation chain / on-call routing..." → sequential dialing (`sequential-dialing.md`)

**If inbound SMS (non-agent):** Tell the user this is a standalone inbound SMS flow, not an AI agent conversation. The customer texts a command to your number and the flow processes it and replies — no AI Agent, no Engage conversation nodes, no multi-turn loop. Point the user to `docs/playbooks/inbound-sms.md` for the full walkthrough. This playbook covers Start node (SMS - Mobile Originated), Evaluate node for parsing, HTTP Request for API calls, and SMS Reply.

Signal phrases for inbound SMS (non-agent):
- "customer texts a keyword and gets a result..." → inbound SMS (`inbound-sms.md`)
- "SMS command processing / text-to-lookup..." → inbound SMS (`inbound-sms.md`)
- "opt-in/opt-out via text..." → inbound SMS (`inbound-sms.md`)
- "on-call roster update via SMS..." → inbound SMS (`inbound-sms.md`)
- "inbound SMS without AI agent..." → inbound SMS (`inbound-sms.md`)

**If Flow Designer voice flow (non-agent):** Tell the user this is a Flow Designer voice flow, not an AI agent and not a Connect flow. The caller dials in and the flow handles routing through IVR menus, business hours checks, queue treatment, and/or data lookups — all within WxCC Flow Designer.

Continue with the Flow Designer interview questions. The user already told you what the flow does (Q1), and the channel is voice (determined at the branch point). Ask these questions **one at a time** — present one, wait for the answer, then ask the next:

**FD-Q2 (Menu Structure):**
> "What options should the IVR menu offer? List each option with a label (e.g., Press 1 for Sales, Press 2 for Support). If there are sub-menus or multi-level menus, describe those too."

**FD-Q3 (Languages/TTS):**
> "Does this flow need to support multiple languages? If so, which ones? The flow can either have a language selection option in the menu (Press 0 for Spanish) or a separate language menu at the start."

**FD-Q4 (Routing Logic):**
> "How should calls be routed? I need to know about:
> - DNIS routing (different behavior per dialed number)?
> - Business hours (static schedule in Control Hub, or dynamic from an API)?
> - Skill-based routing (route to agents with specific skills)?
> - Caller verification (check if caller is known before routing)?
> - Transfer to external numbers (which type: Blind Transfer where the call leaves WxCC permanently, or Bridged Transfer where the call returns to the flow if the transfer fails)?"

**FD-Q5 (Retry/Timeout):**
> "What should happen when a caller doesn't press any digit? Options: replay the menu (with a max retry count — I recommend 3), transfer to a queue, or disconnect. What about invalid digits?"

Then ask the remaining shared questions:
- **Q6 (Escalation):** When should the flow route to a human agent queue? What queue name?
- **Q7 (Data sources):** Does the flow need to call external APIs or look up data? (BRE, HTTP Request, CJDS, etc.)
- **Q8 (Notifications):** Any outbound notification flows triggered by this IVR?

Then invoke `Skill("design-flow")` with the interview answers. The design-flow skill selects blueprints, composes activities, validates ports, and produces a complete design doc. If a design doc already exists in `docs/plans/`, design-flow reads and validates it instead of starting from scratch. After the user approves the design doc:
1. Offer `/build-spec-diagram` for a visual .drawio diagram
2. Invoke `Skill("build-flow-designer")` to generate step-by-step build instructions — the build skill reads the design doc automatically
3. Walk through **WxCC Control Hub one-time setup**. Read `docs/playbooks/wxcc-setup.md` and guide the user through any steps not already completed:
   - Site provisioned
   - Team created (for agents who handle escalations from the IVR)
   - Queue created with team assigned
   - Entry Point created (Telephony)
   - PSTN number assigned to Entry Point
   - Global Variables created (if the flow uses any — e.g., CJDS tokens, API keys, Global_Language)
   - Business Hours schedule created (if the flow uses a Business Hours activity)
   - Flow assigned to Entry Point with version label
4. Final end-to-end test: ask the user to dial the PSTN number and walk through each path in the flow

Signal phrases for Flow Designer voice flows:
- "IVR menu / press 1 for..." → Flow Designer (`design-flow` → `build-flow-designer`)
- "route calls to a queue based on..." → Flow Designer (`design-flow` → `build-flow-designer`)
- "check business hours then route..." → Flow Designer (`design-flow` → `build-flow-designer`)
- "DNIS routing / route by dialed number..." → Flow Designer (`design-flow` → `build-flow-designer`)
- "skill-based routing..." → Flow Designer (`design-flow` → `build-flow-designer`)
- "callback offer / opt out of waiting..." → Flow Designer (`design-flow` → `build-flow-designer`)
- "hold treatment / position announcements..." → Flow Designer (`design-flow` → `build-flow-designer`)
- "data dip then route / look up customer data then route..." → Flow Designer (`design-flow` → `build-flow-designer`)
- "transfer to an extension / bridged transfer..." → Flow Designer (`design-flow` → `build-flow-designer`)
- "post-call survey / CSAT..." → Flow Designer (`design-flow` → `build-flow-designer`)

**If outbound:** Tell the user this is an outbound notification flow, not an inbound AI agent. The build process is different — it uses webhook triggers and channel-specific delivery nodes instead of AI Agent Studio. Determine which channel(s) the user needs:

- **Voice-only** (TTS call, paging group): Invoke `Skill("build-outbound-flow")`. The skill's Step 1 reads `outbound-voice.md`, `webhook-triggers.md`, and `outbound-flow-config.md` — these contain required node settings you cannot guess. Do NOT generate the flow config yourself.
- **SMS, Email, WhatsApp, RCS, Apple Messages, or multi-channel**: Invoke `Skill("build-notification")`. The skill's Step 1 reads channel-specific playbooks, reference docs, and `webhook-triggers.md` — up to 13 documents depending on channel. Do NOT generate the notification config yourself.

Signal phrases for each channel:
- "send a text/SMS when..." → `build-notification` (SMS)
- "email the customer when..." → `build-notification` (Email)
- "send a WhatsApp message when..." → `build-notification` (WhatsApp)
- "send a rich card/RCS message..." → `build-notification` (RCS)
- "send an Apple Message/iMessage..." → `build-notification` (Apple Messages)
- "notify via their preferred channel..." → `build-notification` (Multi-channel)
- "call the customer and play a message..." → `build-outbound-flow` (Voice)
- "page the warehouse/store..." → `build-outbound-flow` (Voice/Paging)

**If standalone infrastructure request (not an agent or flow build):** Some user requests are about setting up supporting infrastructure, not building an agent or flow. Route these to the appropriate playbook:

Signal phrases for infrastructure requests:
- "set up a Custom Connector / OAuth connector..." → `docs/playbooks/custom-connectors-setup.md`
- "connect to ServiceNow / Salesforce / any OAuth API from my flow..." → `docs/playbooks/custom-connectors-setup.md`
- "create a Function / Functions Activity / data transformation in my flow..." → `docs/playbooks/functions-setup.md`
- "set up BRE / upload a CSV / business rules..." → `docs/playbooks/bre-setup.md`

**If inbound:** Continue with Question 2.

### Question 2: Agent Type

Based on the use case the user just described, recommend an agent type before asking. Apply this decision test:

- **Recommend Scripted** if: responses MUST be exact and deterministic (regulatory/compliance), OR the use case has a small set of well-defined intents with predictable phrasing, OR cost matters (scripted is 6-24x cheaper per license unit), OR sensitive data handling requires no LLM response generation.
- **Recommend Autonomous** if: the caller can express intent in many different ways, the response needs to vary dynamically based on context, the intent set is large or hard to enumerate, OR speed-to-deploy matters more than response control.
- **Default to Autonomous** for ambiguous cases -- it's faster to build and more flexible, but less predictable and more expensive.

**Key trade-offs to mention:**

| Factor | Scripted | Autonomous |
|--------|----------|------------|
| Response control | Full control, deterministic | Risk of hallucination |
| Build effort | More effort (author intents, utterances, responses) | Faster (write instructions) |
| Cost per license unit | 1,200 voice / 4,800 digital sessions | 200 sessions |
| Flexibility | Brittle if users phrase things unexpectedly | Handles varied input naturally |

Frame it as a recommendation with one sentence of justification, then confirm:

> "Based on what you described, I'd recommend an **Autonomous** agent -- callers will express their intent in many different ways and you need dynamic responses. Does that sound right, or would you prefer a **Scripted** agent for tighter control over responses?"

Or for simpler/compliance-sensitive use cases:

> "This sounds like a good fit for a **Scripted** agent -- you need exact control over what the agent says, the conversation paths are well-defined, and it's significantly cheaper at scale. Does that sound right, or do you think callers will need more natural conversation flexibility?"

**Important context for the user:** Scripted agents use NLU (not a rigid menu) -- they can still understand natural language phrasing, but responses are pre-authored rather than generated by an LLM.

Store the confirmed agent type for use in the Design Phase.

**STOP. Wait for the user to confirm the agent type before proceeding to Question 3.**

<!-- SYNC: Q3 (Channel) applies to both autonomous and scripted agent paths — update both when changing -->
### Question 3: Channel

> "What channel will callers use? Options are **voice**, or a digital channel like **SMS**, **WhatsApp**, **Live Chat**, or **Email**. You can also support multiple channels."

We're primarily building an AI Agent in AI Agent Studio. The channel determines the entire flow architecture:

- **Voice**: Uses WxCC Flow Designer with a **Virtual Agent V2** node that connects callers to the AI Agent. The routing path is: PSTN number → Entry Point → Flow Designer flow → Virtual Agent V2 → Queue Contact (escalation).
- **Digital (SMS, WhatsApp, Live Chat, Email)**: Does **NOT** use Flow Designer at all. Instead, the inbound conversation is handled by a **Webex Connect flow** built with the `build-digital-inbound` skill. The Connect flow handles the full conversation lifecycle: channel trigger → AI Agent (Process Message) → channel reply → receive loop → Queue Task (escalation). This is a completely different flow architecture from voice.

If the user selects a digital channel, note which specific channel(s) for later use when invoking the `build-digital-inbound` skill. Also ask these digital-channel-specific follow-up questions (one at a time):

- **Rich content or text-only?** "Will the agent send rich content (cards, buttons, images) or text-only replies?" — this determines TextResponse vs FullResponse in the Connect flow.
- **Escalation queue name?** "Which queue should human agent escalations go to?" — do not assume a queue name; the user must provide it.

If the user selects **voice**, ask these voice-specific follow-up questions (one at a time):

- **Custom data from IVR?** "Will the agent need any data before it starts talking — like the caller's name from a CRM lookup, or a store number from the IVR? This lets you personalize the welcome message and instructions." — if yes, note which variables to pass via VAV2 State Event settings. Reference `docs/reference/ai-agent-studio.md` "Custom Data at Session Start" during the Build Phase.
- **PCI/compliance fulfillment?** "Will any action handle sensitive payment or compliance data that should stay in Flow Designer instead of passing through Webex Connect?" — if yes, note which actions need custom event fulfillment. Reference `docs/reference/ai-agent-studio.md` "Custom Event Fulfillment" during the Build Phase.

**STOP. Wait for the user's response before proceeding to Question 4.**

### Question 4: Actions / Intents (YOU Propose)

Based on what the user described, propose a specific list. The framing differs by agent type, but the core question is the same: what distinct operations can the user trigger?

#### If Autonomous: Propose Actions

Design actions around **what triggers a database operation**, not around **what data is needed**. Count the distinct *operations* the caller can trigger -- not the distinct *data fields* needed.

Ask for each candidate action:
- Does it require **different input from the caller**?
- Does it perform a **different DB operation** (GET vs POST vs PATCH)?
- Does it query a **different table**?
- Is it triggered by a **different caller intent**?

If the answer to all four is no -- it is probably a **field on an existing action**, not a new action. One action can return many output variables from one query. Do not create a separate action just to retrieve additional columns from the same record.

| Signals you need a NEW action | Signals you need more OUTPUT VARIABLES |
|---|---|
| Different caller input required | Same table, same query |
| Different HTTP method (GET/POST/PATCH) | No new caller input needed |
| Different trigger condition | Data lives on the same record |
| Different table or relationship | Just more columns to return |

Common patterns to draw from:
- **Identity verification** action (lookup by phone/email -- should almost always be first; return the full profile including preferences in one call)
- **Search/lookup** actions (find records, check status, get details)
- **Create** actions (book appointments, submit requests, create tickets)
- **Update** actions (reschedule, modify, change status)
- **Cancel/delete** actions
- **Info retrieval** actions (get details about products, services, policies -- but check if this data can be returned by an existing action first)

Frame it like this:

> "Based on what you described, I'd suggest these actions:
> 1. `verify_caller` -- look up the caller's account by phone number (should always be first)
> 2. `get_details` -- retrieve relevant information the caller needs
> 3. `create_record` -- create a new entry (order, ticket, booking, etc.)
> 4. `update_record` -- modify or cancel an existing entry
>
> Identity lookup should be the first step in every conversation -- the agent needs to know who it's talking to before doing anything else. Does this list look right, or do you want to add or remove anything?"

#### If Scripted: Propose Intents

Scripted agents use **intents** (not actions). An intent represents a user goal -- something the customer wants to accomplish. The NLU engine classifies free-text input against trained intents, so users don't need to follow a rigid menu.

Propose intents the same way you'd propose actions -- suggest a list and let the user refine. Each intent maps to a distinct user goal.

Common patterns:
- **Identity verification** intent (lookup by phone/email)
- **Information lookup** intents (check status, get details)
- **Booking/creation** intents (schedule appointments, submit requests)
- **Modification** intents (reschedule, update details)
- **Cancellation** intents

For each intent, also note:
- What **utterances** a user might say to trigger it (you'll collect these in detail later)
- Whether it requires **fulfillment** (an API call)
- Whether it has **follow-up intents** (intents that only make sense after this one completes)

Frame it like this:

> "Based on what you described, I'd suggest these intents:
> 1. `verify_caller` -- customer identifies themselves (by phone number or account)
> 2. `check_status` -- customer asks about an existing record
> 3. `book_appointment` -- customer wants to schedule something
> 4. `cancel_appointment` -- customer wants to cancel
>
> The first intent should verify who the caller is. After that, intents like `book_appointment` and `cancel_appointment` would be available. Does this list look right?"

**STOP. Wait for the user to approve or modify the list before proceeding to Question 5.**

### Question 5: Input Entities / Slot Entities

#### If Autonomous: Entities per Action

For each action in the approved list:

> "For the [action_name] action, what info does the caller need to provide?"

Define input entities: name, type (String/Date/Number), whether it's required. Remember: phone numbers are ALWAYS String type, never Number.

#### If Scripted: Entities and Slots per Intent

For each intent, collect:

> "For the [intent_name] intent, what information does the agent need to collect from the customer?"

Define entities (shared across intents) and how they're used as slots per intent:
- **Entity name**: lowercase_underscores (e.g., `appointment_date`)
- **Entity type**: Custom list, Regex, Digits, Alphanumeric, Free form, or a system entity (Date, Time, Email, Phone, etc.)
- **Required?**: Must the agent collect this before completing the intent?
- **Retry count**: How many times to re-ask if the customer doesn't provide it (suggest 2-3)
- **Prompt**: What the agent says to ask for this value (e.g., "What date would you like?")

Also ask about **context flow** — how intents chain together:

> "After the customer completes [intent_name], should any follow-up intents become available? For example, after booking an appointment, should the customer be able to confirm or modify it?"

Capture entry/exit context relationships. This determines the conversation flow.

**STOP. Wait for the user's response before proceeding to Question 6.**

<!-- SYNC: Q6 (Escalation) applies to both autonomous and scripted agent paths — update both when changing -->
### Question 6: Escalation

> "When should the agent hand off to a human agent?"

Common triggers: caller asks for a person, agent cannot answer, error conditions, sensitive topics.

Note: "Talk to an agent" intent is built-in to AI Agent Studio -- no custom config needed. But identify domain-specific escalation triggers too.

**Cross-channel escalation follow-up (digital channels only):** If the user selected a digital channel in Question 3 AND mentions wanting to escalate to a voice call (not just a human agent on the same channel), ask:

> "You mentioned escalating to a voice call. I can set that up — we'll capture the chat transcript and pass it to the voice agent via CJDS so they have full context. A few things I'll need:
> 1. Which queue should the voice call route to?
> 2. Do you want the full transcript passed, or just a summary of what was discussed?
> 3. Is CJDS already provisioned in your org?"

If they want cross-channel escalation, note it for the design doc and reference `docs/playbooks/cross-channel-escalation.md` during the Build Phase. The pattern uses the Fetch Conversation Transcript node (Webex CC Engage) → Write to CJDS → outbound voice call → Customer Journey Widget surfaces the transcript to the voice agent.

**STOP. Wait for the user's response before proceeding to Question 7.**

<!-- SYNC: Q7 (Database Backend) applies to both autonomous and scripted agent paths — update both when changing -->
### Question 7: Database Backend

**If Supabase MCP was already connected during setup detection**, skip the "what database" question — you already know. Use `mcp__supabase__list_tables` and `mcp__supabase__execute_sql` to inspect the schema directly, then confirm what you found with the user.

**If the backend is not yet known** (non-Supabase users who deferred during setup):

> "What database or API has your data?"

- If the user provides a schema (DDL, JSON, or description): parse it to extract tables, columns, types, keys, relationships, auto-generated fields
- If Supabase: set up MCP now (see setup detection steps), then inspect schema
- If unknown backend: use the DB-Research Subagent Prompt from `docs/reference/db-integration.md` to research the correct HTTP patterns via web search
- If the use case is **ANI-based routing** (VIP lists, campaign routing, regional routing) and the user has no external database: recommend the **BRE (Business Rules Engine)** — a native WxCC component that stores key-value lookup data (CSV upload) and is queried via the BRE Request activity in Flow Designer. No AI Agent actions or Connect flows are involved. Point the user to `docs/playbooks/bre-setup.md` for the full walkthrough. Note: BRE is a Flow Designer feature only — it does not integrate with AI Agent action flows in Connect.
- If the user needs **OAuth 2.0 or token-based API authentication** for their flow's HTTP calls (e.g., ServiceNow, Salesforce, any API requiring OAuth): recommend **Custom Connectors** — a Control Hub feature that stores OAuth credentials and provides a pre-authenticated connector for HTTP Request nodes in Flow Designer. Point the user to `docs/playbooks/custom-connectors-setup.md` for the full setup walkthrough.
- If the user needs **in-flow data transformation** (date formatting, string manipulation, complex conditional logic) that goes beyond Pebble template filters: recommend the **Functions Activity** — runs JavaScript or Python inline in the flow with a 5-second execution limit. Point the user to `docs/playbooks/functions-setup.md` for the full setup walkthrough (create in Control Hub, select runtime, test, publish, use in flow).

In all cases, confirm these details:
  - What are the primary keys?
  - Are there foreign key relationships?
  - Which columns are unique? (needed for exact-match lookups)
  - Are there auto-generated fields (IDs, confirmation numbers, timestamps)?
  - What timezone are dates stored in?

**STOP. Finish the database discussion before proceeding to Question 8.**

<!-- SYNC: Q8 (Outbound Notifications) applies to both autonomous and scripted agent paths — update both when changing -->
### Question 8: Outbound Notifications

> "Does this agent also need to send outbound notifications? For example, a confirmation message after creating a record, a status update when something changes, or a reminder before an appointment."

If yes, capture for each notification flow:
- **Trigger event**: what causes the notification to fire (e.g., "maintenance ticket created", "appointment reminder 24 hours before")
- **Channel**: SMS, Email, WhatsApp, Voice, RCS, Apple Messages, or multi-channel
- **Message content**: what the notification says (template message for WhatsApp, text for SMS, etc.)
- **Data source**: does it need a DB lookup before sending, or does all data come from the trigger event?

If the user mentioned notifications earlier in the conversation (e.g., during Question 1 or Question 4), confirm those here rather than asking from scratch.

If no outbound notifications are needed, note "N/A" for Section 4b of the design doc.

**STOP. Wait for the user's response before moving to the Design Phase.**

---

## DESIGN PHASE

**PREREQUISITE CHECK — do NOT enter this phase unless ALL of these are true:**
- [ ] Agent type was confirmed (Question 2)
- [ ] Channel was confirmed (Question 3)
- [ ] User explicitly approved the action list (Question 4)
- [ ] Input entities were confirmed for each action (Question 5)
- [ ] Escalation triggers were discussed (Question 6)
- [ ] Database backend and schema are understood (Question 7)
- [ ] Outbound notifications discussed (Question 8)

If any of these are missing, go back and ask the missing question. Do NOT infer answers from the use case description.

After the interview is complete:

1. Read `docs/templates/ai-agent-design-doc.md` to get the template
2. Fill in every section with what was gathered during the interview:

   **For Autonomous agents:**
   - Section 2: Agent Metadata (name, type, channels, entry point, queue)
   - Section 3: Database Backend (type, base URL, auth, schema tables, relationships, constraints)
   - Section 4: Actions Table AND Action Descriptions — for each action, fill in the formatted description (trigger, requires, returns), sample JSON, and input entities table
   - Section 5: Agent Instructions — use the structured subsections (5.1 Identity, 5.2 Context, 5.3 Task with action sequence table, 5.4 Timezone, 5.5 Escalation Triggers table, 5.6 Ground Rules, 5.7 Conversation Style)
   - Section 6: Welcome message (separate from instructions)

   **For Scripted agents:**
   - Section 2: Agent Metadata (name, type, channels, entry point, queue)
   - Section 3: Database Backend
   - Section 4d: Scripted Agent Configuration — intents table (including Template Key column), entities table, context flow, slot design, response templates, fulfillment plan
   - Section 6: Welcome message (configured as a default system intent)
   - Skip Section 5 (scripted agents don't have instructions)

   **For both agent types:**
   - Section 4b: Outbound notification flows (from Question 8) — if any, fill in trigger event, channel, message content, DB lookup flag. If none, write "N/A".
   - Section 4c: Digital inbound flow architecture (if channel is digital) — fill in the metadata table (channel, rich responses, escalation queue, message variable, customer ID variable, reply node type, response source) and the flow diagram
   - Section 7: WxCC Routing Plan table (entry point, type, PSTN, flow type, queue, team) plus the routing path diagram
   - Section 7 Voice Flow Activities and Connections tables (populated from Blueprint 11 or 12 — required for spec diagram generation)
   - Section 8: Build checklist with all items listed as pending

3. Save to `docs/plans/YYYY-MM-DD-{agent-name}.md` (use today's date)
4. Present the full design to the user for review
5. **DO NOT proceed to building until the user explicitly approves**
6. If they request changes: update the design doc, re-present, and wait for approval again
7. When the user approves the design, read `build-sequence.md` in this folder and follow it.

---

## REFERENCE FILES

When you need deep platform knowledge, read these files:

| File | Contains |
|------|----------|
| `docs/reference/webex-connect.md` | Connect flow structure, HTTP nodes, variable picker, Flow Outcomes, gotchas |
| `docs/reference/ai-agent-studio.md` | AI Studio agent config (autonomous): slots, actions, LLM behavior, testing |
| `docs/reference/ai-agent-studio-scripted.md` | AI Studio scripted agents: intents, entities, responses, context management, fulfillment |
| `docs/reference/wxcc-platform.md` | Control Hub setup, Flow Designer, CCAI Config, routing architecture |
| `docs/reference/db-integration.md` | Database patterns, PostgREST syntax, multi-backend support, curl templates |
| `docs/templates/action-config.md` | The 10-step action config output format |
| `docs/templates/ai-agent-design-doc.md` | Design doc template for AI Agent builds (autonomous + scripted) |
| `docs/examples/` | Working examples and env.templates (UUID replacement lists for upstream Flow Designer reference flows) |
| `docs/playbooks/outbound-voice.md` | Outbound voice calls: Call User node, Voice Node Group, Play/TTS config |
| `docs/playbooks/inbound-voice.md` | Inbound voice calls: Start node (Inbound Call trigger), VNG, Play, Collect Input, Call Patch |
| `docs/playbooks/sequential-dialing.md` | Sequential dialing / on-call connect: Call Patch chaining, timeout tuning, dynamic number sourcing |
| `docs/playbooks/webhook-triggers.md` | Webhook-triggered flows: Start node config, URL, payload parsing, auth |
| `docs/playbooks/webex-calling-paging.md` | Webex Calling paging integration: PSTN routing, auto-answer, multicast |
| `docs/reference/digital-inbound.md` | Digital inbound architecture: Connect flow patterns for SMS, WhatsApp, Live Chat, Email |
| `docs/playbooks/digital-inbound-agent.md` | Step-by-step guide: building a digital inbound conversation flow in Connect |
| `docs/playbooks/scripted-agent-design.md` | Scripted agent design: intent planning, entity design, context flow mapping, response authoring |
| `docs/playbooks/scripted-agent-build.md` | Scripted agent build: step-by-step AI Agent Studio configuration, fulfillment wiring, deployment |
| `docs/reference/bre.md` | BRE: Business Rules Engine architecture, DataSync, rule syntax, BRE Request activity |
| `docs/playbooks/bre-setup.md` | BRE setup: DataSync access, attributes/contexts/rules, CSV upload, Flow Designer wiring |

### Conditional: Advanced Connect Patterns
If the user's action requires **error routing** (branching on HTTP status codes), **data transformation** (date conversion, string formatting), or **side-effect notifications** (SMS, email, RCS, WhatsApp, or Apple Messages confirmation after an action), load `docs/reference/webex-connect-advanced.md` before building that action.
