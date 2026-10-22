<!-- plan5-agent-sources: built from `git show decc5e76:<path>` (CI clones at depth 1, so tests read this file). Do not edit by hand. -->
=== headings .claude/agents/wxc-calling-builder.md
12	# Webex Calling Builder
14	## ROLE
26	## FIRST-TIME SETUP
30	### 1. CLI Environment
41	### 2. Authentication
69	### 2b. Target Org Confirmation (Partner Tokens)
82	### 3. Existing Design Docs
89	### 4. Reference Docs
98	## INTERVIEW PHASE
102	### Org Health Assessment
109	### Query Intent Detection
142	### CUCM Migration Detection
159	#### Pipeline Walkthrough
214	### Question 1: Objective
244	### Question 2: Scope
269	### Question 3: Prerequisites
292	### Question 4: Constraints
303	### Question 5: Special Requirements
312	## DESIGN PHASE
316	### 1. Load Reference Docs
320	### 2. Build the Deployment Plan
337	### 3. Save and Present
346	## EXECUTE PHASE
352	### Discovery-First Rule
361	### Progress Reporting
381	### Error Handling
390	### Cascading-Impact Decisions
401	### Mid-Execution Changes
411	### Common wxcli Commands for Execution
446	### Bulk Operations
479	## VERIFY PHASE
483	### 1. Read Back
500	### 2. Comparison
507	### 3. Execution Report
522	## SKILL DISPATCH
526	### Dispatch Table
557	### How Dispatch Works
568	### Source of Truth Precedence
578	### Multiple Skills Per Plan
595	### Standalone Skill Use
599	### Admin Operations Without Skills
611	## CONTEXT MANAGEMENT
615	### Phase Boundaries
634	### Session State Protocol
652	### Fresh Start Protocol
662	### Compaction Recovery
671	## CRITICAL RULES
675	### Verify Auth Before Executing
678	### Handle Rate Limiting
681	### Log All Commands
684	### Use Async for Large Bulk Operations
687	### Check Prerequisites Before Creation
696	### Rollback on Failure When Possible
703	### ID Handling
706	### Inline IDs in Commands
709	### Location-Scoped Operations
712	### Idempotency Awareness
718	### Token Scope Awareness
721	### Call Controls Requires User Token
724	### CLI-First with Raw HTTP Fallback
727	### Command Verification (Anti-Hallucination)
744	### Design Doc Requirement
749	## REFERENCE DOC LOADING
753	### Provisioning (users, locations, licenses)
758	### Call Features (AA, CQ, HG, paging, park, pickup, voicemail groups)
764	### Person Call Settings
772	### Location Call Settings
779	### Call Routing (dial plans, trunks, route groups, PSTN)
784	### Devices (phones, DECT, workspaces)
791	### Device Platform (RoomOS configurations, personalization, xAPI)
796	### Call Control (real-time call operations)
802	### Monitoring and Reporting
808	### Emergency Services
813	### Virtual Lines
818	### Organization Management
823	### Identity & SCIM
828	### Licensing
833	### Audit & Security
838	### Hybrid Infrastructure & Analytics
843	### Partner Operations
848	### Apps, Data & Resources
853	### Messaging Spaces (spaces, teams, memberships, messages, ECM, HDS)
858	### Messaging Bots (bots, notifications, adaptive cards, cross-domain)
864	### Meetings (schedule, manage, transcripts, recordings, polls)
872	### Video Mesh (monitoring, clusters, nodes, thresholds)
877	### Contact Center (agents, queues, flows, campaigns, monitoring)
885	### Cross-Cutting (on-demand only — load when debugging or using raw HTTP)
=== headings wxcc/.claude/agents/wxcc-agent-builder.md
21	# WxCC AI Agent Builder
23	## CONTINUATION RULE (READ THIS FIRST)
34	## ROLE
47	## FIRST-TIME SETUP DETECTION
70	## INTERVIEW PHASE
76	### Question 1: Use Case
84	### Use Case Branch: Inbound vs. Outbound
192	### Question 2: Agent Type
224	### Question 3: Channel
245	### Question 4: Actions / Intents (YOU Propose)
249	#### If Autonomous: Propose Actions
286	#### If Scripted: Propose Intents
316	### Question 5: Input Entities / Slot Entities
318	#### If Autonomous: Entities per Action
326	#### If Scripted: Entities and Slots per Intent
348	### Question 6: Escalation
368	### Question 7: Database Backend
393	### Question 8: Outbound Notifications
411	## DESIGN PHASE
457	## BUILD PHASE
459	### Platform Dependency Chain
475	### If Scripted: Build in AI Agent Studio First
497	### If Autonomous: Build Actions One at a Time
501	### Step 1: Test the Backend Query — `[Terminal / API Client]`
514	### Step 2: Build the Connect Flow — `[Webex Connect]`
528	### Step 3: Configure AI Agent Studio — `[AI Agent Studio]`
543	### Step 4: Test End-to-End — `[AI Agent Studio → Voice/Chat Preview]`
559	### Step 5: Repeat
565	## OUTBOUND FLOW BUILD (if applicable)
571	### Step 1: Confirm Requirements
575	### Step 2: Build the Connect Flow
584	### Step 3: Test End-to-End
590	### Step 4: Repeat
596	## AFTER ALL ACTIONS ARE BUILT
600	### 1. Final Agent Instructions — `[AI Agent Studio → Instructions tab]` (Autonomous Only)
621	### 2. Welcome Message — `[AI Agent Studio → Welcome Message field]`
627	### 3. WxCC Control Hub Setup — `[Control Hub → Contact Center]`
645	### 4. Connect the Agent to Flow Designer — `[WxCC Flow Designer → Virtual Agent V2]`
662	### 5. Flow Designer Flow — `[WxCC Flow Designer]` (Voice) / `[Webex Connect]` (Digital)
679	### 6. Final End-to-End Test
685	## COMPACTION RECOVERY
700	## CRITICAL RULES
706	### Variable Picker (Connect)
709	### Action Descriptions — Flow Outcomes Data (AI Studio)
714	### Enable Toggle (AI Studio)
717	### Flow Outcomes Mode (Connect)
720	### Notify AI Agent (Connect)
723	### Test Before Configure
726	### Timezone Handling
729	### Phone Number Entity Type
732	### Array Responses
735	### UUIDs as Input Entities
740	### Prohibited Nodes (Connect)
747	### Action vs. Field
752	### Design Doc Requirement
755	### WhatsApp Template Parameters
758	### Schema Discrepancy Resolution
761	### Never Fabricate User Answers
764	### User-Provided Naming
767	### WhatsApp 24-Hour Window in Designs
770	### Database Confirmation Before Schema Discovery
775	## REFERENCE FILES
801	### Conditional: Advanced Connect Patterns
=== block Q3 wxcc/.claude/agents/wxcc-agent-builder.md:223-244
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

=== block Q6 wxcc/.claude/agents/wxcc-agent-builder.md:347-366
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

=== block Q7 wxcc/.claude/agents/wxcc-agent-builder.md:367-391
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

=== block Q8 wxcc/.claude/agents/wxcc-agent-builder.md:392-408
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

=== critical-rules wxcc/.claude/agents/wxcc-agent-builder.md
### Variable Picker (Connect)
### Action Descriptions — Flow Outcomes Data (AI Studio)
### Enable Toggle (AI Studio)
### Flow Outcomes Mode (Connect)
### Notify AI Agent (Connect)
### Test Before Configure
### Timezone Handling
### Phone Number Entity Type
### Array Responses
### UUIDs as Input Entities
### Prohibited Nodes (Connect)
### Action vs. Field
### Design Doc Requirement
### WhatsApp Template Parameters
### Schema Discrepancy Resolution
### Never Fabricate User Answers
### User-Provided Naming
### WhatsApp 24-Hour Window in Designs
### Database Confirmation Before Schema Discovery
=== end
