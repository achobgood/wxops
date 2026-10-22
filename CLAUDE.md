# Webex Ops

Build, configure, migrate and audit Webex with Claude Code: Webex Calling, admin, devices, messaging and meetings through the `wxcli` command line; Contact Center voice flows (Flow Designer), Webex Connect flows, AI agents (AI Agent Studio) and Business Rules Engine lookups through the skills and docs below.

**Execution pattern:** `wxcli` commands first, raw HTTP as the fallback. `wxcli` has 200 command groups covering the full Webex Calling, admin, device, messaging, meetings, and contact center API surface; the raw HTTP forms are in `docs/reference/`.

**MCP only when it does the whole job.** `wxcli` commands are the default. Move a job to an official Cisco MCP server only when that server does the whole job, writes included, has been tested live on a real tenant, and costs the same or fewer tokens.

## You run the commands

Claude runs every command — through the builder agent (§ Quick Start) — and never hands the user one to type. The only exceptions are steps a person must do:
- **The Webex token.** It is the user's secret, so they run `wxcli configure` and paste it at the prompt — first time, and again after a 401/403 or expiry. The skills' "run `wxcli configure`" lines mean this.
- **Clicks in a Cisco screen with no API** (Control Hub, Webex Connect, AI Agent Studio, DataSync, developer.webex.com): give them as UI steps (§ Answering platform questions).
- **CUCM migration decisions.** The operator answers each review prompt in `/cucm-migrate`. The operator runbook's own `wxcli` steps are for an operator working without Claude.

## Mandatory Grounding Rule

**Never answer any question about Webex Calling from training data alone.** The same holds for every Cisco platform this repo covers: Webex Calling, Contact Center and its Control Hub configuration, Flow Designer, Webex Connect, AI Agent Studio (autonomous and scripted agents), the Business Rules Engine (BRE), the Customer Journey Data Service (CJDS), Service Apps and the other Webex APIs (admin, devices, messaging, meetings), and the `@webex/contact-center` agent-desktop SDK. It applies to every build — AI agent, Connect flow, Flow Designer IVR, outbound notification, BRE lookup, Calling configuration — not only the AI-agent path.

For every such question — capability, configuration, behavior, limits, or anything else — you MUST either:
1. Invoke the relevant skill (§ Routing Table names it), OR
2. Read the relevant doc in `docs/reference/` (and, for a procedure, `docs/playbooks/`)

The skills and docs are the authoritative source for this project. Training data about Cisco/Webex products is unreliable — product tiers get conflated, feature names change, and capabilities vary by license. Every platform instruction — UI fields, node settings, header values, deployment steps, routing configuration — must come from a skill or a file in `docs/reference/` or `docs/playbooks/`. If it isn't there, say "I don't have that documented" and either search the project docs or tell the user it needs to be added. Inventing a plausible-sounding platform detail is the single most damaging failure mode in this project — the user has no way to know it's wrong until it fails at runtime.

## Answering platform questions

For every platform question — every platform § Mandatory Grounding Rule names, digital inbound flows and database integration included — read the docs before responding, even when the question seems simple or you feel sure: training data is stale, the docs are authoritative. § Routing Table names the first doc for each topic and what to read next. If you catch yourself about to answer without a Read of a doc in this turn, STOP and read first.

**Default position.** Your starting answer is **"I don't have that documented in the reference docs."** Replace it only after the lookup finds a source you can cite. If the lookup finds nothing, the default stands: your reply must contain that exact sentence, apostrophe included — not a paraphrase such as "I couldn't find…" or "the docs don't say".

**Which directory — value vs. procedure.** Classify the question before reading:
- **Value question** ("what / which / how many / what does it return / is it possible") → answer from `docs/reference/`. **Never from a playbook alone.**
- **Procedure question** ("how do I / build / set up / walk me through") → read the `docs/playbooks/` file **and** every reference doc it cites.

`docs/reference/` owns values — field names, valid values, limits, output variables, ports, error codes, restrictions, syntax. `docs/playbooks/` owns procedure — ordering, decisions, prerequisites, which-UI-next, judgment. The test: **would this still be true if the user's goal changed?** Yes → reference. No → playbook. A playbook cites reference facts rather than restating them. Full doctrine: `.claude/rules/doc-placement.md`.

⚠ **Until the source repository's remediation backlog (`docs/plans/2026-07-25-documentation-remediation-backlog.md`, not shipped) is closed out, neither directory is reliably authoritative** — an April 2026 audit corrected the playbooks and skills but never swept `docs/reference/`. Where the two overlap, read both and treat any disagreement as a **finding**, not a coin flip: resolve it against the live API, official vendor documentation, or the platform owner. Never pick the more plausible one.

**Hard rules.**
- NEVER answer a platform question from training data or memory alone.
- NEVER say "I believe…" or "typically…" about a platform detail — either cite the doc or say "I don't have that documented".
- If the doc doesn't cover the question, say so explicitly — do not fill the gap with plausible-sounding invented details.
- Every one of these must trace to a line in the docs: Control Hub navigation and paths; field, node (Connect, Webex Engage) and activity names; configuration values and steps; entity, agent and channel-specific configuration; output variables, variable paths and syntax; global variable names; queue settings; routing configuration; restrictions; sizing and table limits; CCAI settings; action descriptions; slot syntax; instruction patterns; deployment steps; intents, entities (names, types); response templates; fulfillment patterns; context flow; AI engines and options; channel triggers; Process Message configuration; escalation patterns and steps; headers (names, values; Supabase); PostgREST query syntax and parameters; API endpoint patterns; backend selection criteria; flow wiring; BRE data tables; rule syntax; DataSync configuration.

**When you give UI steps.** The target user has ZERO prior experience with WxCC, Webex Connect, AI Agent Studio, or Flow Designer, whatever they are building. Every instruction must:
- Name the exact platform and UI location (e.g., "Webex Connect → HTTP Request node → Headers section", "Control Hub → Contact Center → Queues → Create Queue", "Flow Designer → Call Patch node → Caller ID field")
- Specify the exact value to enter or select, not just "configure it"
- Include the exact click path when navigating between platforms (Connect, Control Hub, AI Agent Studio, and Flow Designer are four different UIs)
- Never assume a previous step was already completed unless the user explicitly confirmed it
- Never say "as you did before" — repeat the instruction or link to where it was given
- Never combine platform steps across different UIs in a single bullet — each platform switch is a distinct step

If you're about to write "configure the [X]" without saying exactly where and how, stop and look it up in `docs/`.

**Cite every claim.** Every platform-specific claim in your response needs an inline citation in the format `[source: filename § section heading]`, for example:
- "A telephony contact can remain in queue for at most 86,400 seconds (24 hours) [source: flow-designer-essentials.md § Queue Contact Activity]"
- "Scripted agents support two engines — Webex AI Pro 2.0 (with Swiftmatch) and Webex AI Pro 1.0 (with Swiftmatch) [source: ai-agent-studio-scripted.md § AI Engines]"

If you cannot produce a citation for a claim, replace the claim with "I don't have that documented in the reference docs." This is not optional formatting — a missing citation means an unverified claim, which means potential hallucination.

**Proof of read.** Each primary reference doc carries a `<!-- ref-tag: <slug>-vN -->` comment near the top. When answering, state the ref-tags of every doc you consulted:

> Docs consulted: `<slug>-vN`, `<slug>-vN`

If you cannot produce the ref-tag for a doc you are citing, you did not read the current version. Do not cite it.

## Source of Truth Precedence

Applies to everyone touching `wxcli` — main session, skills, and agents alike. When
sources conflict, trust them in this order:

1. **`wxcli <command> --help`** — the running code; always current
2. **Skills** — verified against live APIs; contain exact command examples
3. **Reference docs** — comprehensive but can lag behind skill and CLI updates
4. **Your training data** — least reliable; NEVER trust over the above three

**This covers corrections.** Overriding `--help`, a doc, or a subagent's
doc-grounded finding is itself a rank-4 claim unless you checked. A retraction
*sounds* more verified than what it replaces — it is not. Flagging that
something may be wrong is always fine; asserting the replacement as fact needs
the same evidence as the original.

This refines the grounding rule above: skills and docs outrank your training, but
`--help` outranks *them*. A skill's recipe is a starting point, not a guarantee — recipes
are hand-written and drift as the CLI regenerates. When a recipe and `--help` disagree,
`--help` wins, and the stale recipe should be fixed, not worked around.

**Platform facts follow a second order.** The ladder above is for `wxcli` (command names,
flags, examples). A platform value (field, limit, port, error code) is owned by
`docs/reference/`, which wins every disagreement; a playbook or skill that repeats it names
that owner. Different questions, so keep both — subject to the interim ⚠ in § Answering
platform questions.

**The ladder above does not apply to the `@webex/contact-center` JavaScript SDK** — `wxcli --help` cannot see `webex.cc` or `task.*`. Its own order (live observation first; its typedoc documents the `next` prerelease, ahead of stable; never conclude a field is missing by grepping the minified bundle) is `docs/reference/contact-center-agent-sdk.md` § Source of Truth for This Surface.

**A read-only command can be silently wrong.** It can exit 0, return every record, and
still omit the field you are counting (`people list` drops `extension` and `locationId`
unless `--calling-data true` is passed). Before trusting a read, confirm via `--help` that
the command was actually capable of returning the field you are about to draw a
conclusion from.

**`--help` outranks docs on command names, flags and requiredness — but NOT on two
things, both measured.** (1) **Argument ID kinds:** where help and the doc disagree on an
ID *kind*, the doc is right. (2) **Enum choices:** help is wrong in both directions. On
these two, a live call settles it, not a re-read of `--help`.

**A value from the spec is a hypothesis, not a correction.** `--help` is generated from the
OpenAPI spec, so it inherits the spec's mistakes in enum spellings, example values and
requiredness. Never change an existing doc or skill example to match the spec or a `--help`
example unless a live call confirms it, and label any spec-only change `> **Unverified:**`.

The measured cases behind the last three rules: `docs/reference/wxcli-behavior.md` § 5. When `--help` Is Wrong.

## Discovery-First Rule

Applies to ALL work — reads, queries, and builds — not just execution. When checking
whether a capability, config key, API field, or setting exists, discover first, act second:

1. **One broad query** — enumerate what's available
2. **Evaluate the result** — is the target in the response?
3. **If yes** → proceed. **If no** → report what you found and **stop within 3 total commands**.

**Anti-pattern: refusing a negative result.** If a broad query shows the target doesn't
exist, accept it. Do not try alternate key names, narrower/broader filters, the same query
on a different resource, speculative writes, or workaround paths. Report the negative
finding — that IS the answer. Three total commands max before reporting back.

**Guard on that rule: only accept a negative once the query could have returned a positive.**
An absent field may mean "not configured" or may mean "you didn't ask for it" (see the
`--calling-data` case above). Confirm the command surfaces the field before reporting
"none found" — a false negative delivered confidently is worse than no answer. Before saying `wxcli` has no command for something, check every group's `--help`, not only the obvious one.

## Plain-English Communication Rule

The target user has ZERO platform experience. When explaining findings, trade-offs, or decisions — or asking the user to choose between options — do NOT lead with jargon, acronyms, or internal feature-names. Instead:
- Lead with **"what we're actually deciding"** in one plain sentence.
- Replace every technical term with a **concrete before/after of what the user would type or see** (e.g. "Today you type X and see Y; the other way you'd type/see Z").
- Answer their real questions directly: **what should we do, why, is it easy to maintain, what risks breaking.**
- **End with a clear recommendation**, not a neutral menu of options.
- If a technical term must appear, define it inline the first time.
- **Report the finding, not the search.** Tool calls are already the record —
  don't narrate them again in prose. Conclusion plus evidence, usually one
  sentence. Progress updates during delegated work are not findings.

This applies to chat answers AND the option text in any question you ask the user.

## Execution Discipline

- **Verify before claiming done.** Run the command, check the output, confirm the state. Never report success from inference alone. Ask yourself: "Would a staff engineer approve this?"
- **When a plan breaks, stop and re-plan.** Don't push through a failing approach — re-assess, update the plan, then resume.
- **Bug fixes: just fix it.** When the reproduction is clear (logs, errors, failing tests), resolve without asking for hand-holding. For ambiguous or architectural bugs, propose first.
- **Learn from every correction.** After any user correction, save a feedback memory capturing the pattern and why it matters. Write the rule so it prevents the same mistake in future sessions — not just this one.
- **Skill invocations and their reference reads are mandatory.** When an agent file or skill says "YOU MUST call Skill(X)" or "Step 1: Load references", do it: the docs hold platform conventions training data cannot guess (Connect node wiring, Flow Designer activities, AI Agent Studio configuration, Control Hub setup, inbound and outbound flow patterns). Skip them and the output WILL contain invented details.
- **Don't ask what the user can't answer.** Ask only what they have context for: business logic, their data schema, their team's preferences. Never ask for API response shapes (give a sample and explain it), data center regions or endpoint URLs (say where Control Hub shows them), event type or naming conventions (recommend one), failure-handling defaults (recommend one with its reason; they may override), or node settings, header values and variable syntax (those come from the docs).
- **No abbreviated documentation.** Never write "etc.", "and more", "and others" or vague wording when documenting API specs, node configurations or platform settings: if there are 9 inputs, list all 9. The user relies on this output as their primary reference.

---

## Never confuse these

- **CCAI is not Webex AI Agent.** "CCAI" / "Contact Center AI" is **Google's** product; a **Webex AI Agent** is Cisco's own, and deploying one has **no** Control Hub step: publish in AI Agent Studio, then pick `Webex AI Agent Autonomous` / `Webex AI Agent Scripted` in the **Contact Center AI Config** dropdown of the Flow Designer **Virtual Agent V2** activity. Control Hub's *"create a Contact Center AI Config"* flow is for Google CCAI / BYOVA / Agent Answers [`wxcc-platform.md` § CCAI Config]. The mix-up once put a non-existent step into every AI-agent deploy walkthrough — do not reintroduce it.
- **Export JSON is never generated; FlowIR is.** Flow Designer **export JSON** (the UI export) and Webex Connect flow JSON are proprietary — internal UUIDs cross-referenced in process links, diagram widgets and port mappings — so never generate or restructure them; the only safe edit is find-and-replace of org-specific values (orgId, virtualAgentId, queueId, display names). FlowIR (the v2 API format; names, not IDs) is the supported way to build a flow [`flow-designer-flowir.md` § FlowIR vs Proprietary Export JSON].
- **Scripted ≠ autonomous agents.** Autonomous agents have *actions* whose descriptions an LLM reads. Scripted agents have intents and entities, no LLM-described actions, and call their API work *fulfillment* — on digital channels inline flow logic (Data Parser → Branch → HTTP → Evaluate → Channel Reply), not standalone action flows.
- **Digital inbound ≠ outbound notification.** A conversation the customer starts vs a message sent to the customer: different flow patterns, different skills.
- **In AI Agent Studio, lead with the AI Agent** (the build artifact), not the routing node, and never guess its variable syntax: `{{variable_name}}` works for custom data and fails for Flow Outcomes data [`ai-agent-studio.md` § Custom Data vs. Flow Outcomes Variables].
- **9800-series phones (9811/9821/9841/9851/9861/9871) run PhoneOS, not RoomOS.**

## Quick Start

Claude spawns the **wxops** agent itself (the `Agent` tool, `subagent_type: "wxops"`) for every job that changes or audits the org; you never pick it from a menu. It authenticates, interviews you about what to build, plans, runs `wxcli` and verifies the results. **Do not run `wxcli` commands directly** — the agent handles the full workflow.

- **Build or configure Webex Calling:** describe what you want; the agent follows `docs/playbooks/calling-build.md`.
- **Contact Center flows, Webex Connect flows, AI agents:** the agent starts with `design-ai-agent` (it settles what the build is), then runs the WxCC skills in the order § Routing Table gives.
- **Migrate from CUCM:** "Run a CUCM migration", with the CUCM host and credentials. It runs discover → normalize → map → analyze → resolve addresses → review decisions → plan → execute → verify; details in `.claude/rules/cucm-migration.md`.
- **Debug:** `/wxc-calling-debug` for a failing Calling configuration, `/wxcc-debug` for a failing AI agent action (skills, invoked directly).
- **Query live org state (read-only):** `/query-live` — "who has call forwarding enabled?", "which locations have no users?", "show me all hunt groups".
- **Audit org health:** "audit my org"; the agent runs the `org-health` skill, which collects, analyzes and writes an HTML report.

### Agent Invocation Pattern

**One agent per job.** Spawn one `wxops` agent for a job and keep the whole job — interview, plan, run, verify, report — in that agent.

- **Unrelated jobs** (a hunt group for one team, a queue report for another) run as separate agents **in parallel**, spawned in one message.
- **Follow-ups and interview answers** go to the same agent with `SendMessage` ("also add voicemail to that user", "change the extension to 2001 instead"); don't spawn a new one per question.
- **Dependent steps** stay in one agent, in order — never split them across parallel agents.
- **The one exception — CUCM migration:** it stays phase-per-invocation, one fresh agent per phase, one phase at a time, because a whole migration outgrows one agent's context (`.claude/rules/cucm-migration.md`).
- **Naming is optional:** the safety hook matches the agent's type, not its name.
- After a long silence, check that the agent is alive before you message it (§ Agent Orchestration below).

**Prompt template for a new agent** (a new job, or the next CUCM phase). The agent reads state from disk on startup and checks it against the prompt:
```
"Project: [name]. Current state: [stage, e.g. 'provisioning complete, 3 users + 2 locations created'].
Next: [what to do]. Key context: [anything the agent needs that isn't on disk]."
```

**CUCM migration invocation example:** See `.claude/rules/cucm-migration.md` for the phase-by-phase spawning pattern.

### Agent Model Selection

The agent's own instructions are about 8 KB, and it starts with about 31k tokens of context. It runs on `sonnet` unless you pass another model; choose the model to match the task complexity:

| Task type | Model | Why |
|-----------|-------|-----|
| Cleanup, teardown, batch delete | `haiku` | All logic is in `wxcli cleanup run` — agent just picks flags and runs it |
| Simple read-only checks (list users, verify resource) | `sonnet` with minimal prompt (1-2 sentences) | Base context load is unavoidable; keep prompt short to minimize output tokens |
| Standard provisioning, feature config, single-phase builds | `sonnet` (default) | Good balance of capability and cost |
| WxCC builds (AI agents, Flow Designer and Connect flows), CUCM migration, complex routing, architectural decisions | `opus` | Needs reasoning about dependencies, cross-feature interactions |
| Batch multiple simple checks into one agent call | `sonnet` | One agent with 3 checks < three separate agent spawns |

**Anti-patterns:**
- Never use Haiku for implementation subagents — it misses details and produces rework
- Don't spawn a full builder agent just to run one `wxcli` read command — keep the prompt minimal
- Don't spawn separate agents for each simple check — batch them

### Inline IDs in Commands

Always inline resource IDs directly as arguments. Never use multi-line shell variable assignments before wxcli commands.

```bash
# WRONG — multi-line breaks permission prefix matching
HQ="Y2lz..."
wxcli dect-devices show "$HQ" "Y2xz..."

# RIGHT — inline the ID
wxcli dect-devices show "Y2lz..." "Y2xz..."
```

**Why:** Permission rules use prefix matching. A variable assignment line before `wxcli` means the command string doesn't start with `wxcli`, so it won't match `Bash(wxcli:*)` permission patterns, triggering unnecessary prompts.

### Agent Orchestration — Long-Running Work & Silence Detection

A subagent can die mid-work when a long-running tool call (e.g. a Python polling loop) outlives Bash's ~10-min timeout: the call is killed, the agent loop never resumes to emit a final message, and `SendMessage` pings queue to a dead mailbox. The agent's own rules for long-running work are in its body (§ 3. Run); this is the parent's half.

#### For parent agents when a subagent goes silent

1. **Wait up to 5 min** of silence before investigating — normal operations can have gaps.
2. **After 5 min silence, read the subagent's transcript directly** at `~/.claude/projects/<project-hash>/subagents/agent-<id>.jsonl`. Check:
   - Last entry type: `tool_use` with no paired `tool_result` → subagent is blocked in a tool call (likely Bash timeout pending).
   - Last entry is `assistant` text → subagent thinking, give it more time.
3. **Do NOT use `SendMessage` to ping a subagent blocked in a tool call.** `SendMessage` cannot interrupt an in-flight tool call; the message queues to a dead mailbox.
4. **If the subagent is dead** (transcript ends on unpaired `tool_use`), spawn a fresh agent to continue the work from current state. Do not wait longer.
5. **Check external state** via a fresh diagnostic agent (e.g., "run `wxcli locations list`") rather than trusting the dead subagent's last self-reported state.

## Routing Table

Find the user's words in the first column. **When the row names a skill, invoking that skill is your first action** — the skill reads the row's docs itself. Open a doc from the row yourself first only for a value question (what / which / how many / is it possible) or when the row names no skill. A row naming several meanings lists each; if the user hasn't said which, ask. CC = Contact Center. A doc named without a folder is in `docs/reference/`; "CC core/routing/analytics/journey § N" is section N of docs/reference/contact-center-core.md (or -routing, -analytics, -journey).

| Topic or trigger words | Invoke first | Docs (the skill reads them; read one directly only for a value question or when no skill is named) |
|---|---|---|
| queue | Calling call queue: `configure-features`. CC queue: `contact-center`. Customer Assist queue: `customer-assist` (`call-queue` needs `--has-cx-essentials true`, `docs/reference/wxcli-behavior.md` Known Issue #7) | CC core § 6. Flow Designer Queue Contact activity: `docs/reference/flow-designer-essentials.md`; Control Hub queues: `docs/playbooks/wxcc-setup.md` |
| flow, call flow, flow for our contact center | voice flow: `design-flow`, then `build-flow-designer` or `build-flow-programmatic`. Webex Connect flow: `build-action`, `build-digital-inbound`, `build-notification`, `build-outbound-flow`. List/export/import/publish a CC flow: `contact-center` | CC routing § 11. Not said: ask voice IVR, AI agent, or digital (chat/SMS)? |
| AI agent, Agent Studio, "set up my agent" | autonomous (actions + LLM descriptions): `configure-ai-agent`. Scripted (intents + entities): `design-scripted-agent`, then `configure-scripted-agent`. Mid-build: that skill. From scratch: `design-ai-agent` (§ Multi-Skill Workflows). | Not said: ask which |
| agent (a person), agent records, users, user profiles | CC agents, profiles, greetings, wellbeing: `contact-center`. Claude's builder subagent: `wxops` | CC core §§ 1–5; a human agent's app: desktop row |
| action, fulfillment, "wire up the API call for my agent" | autonomous agent *action*: `build-action`. Scripted agent *fulfillment*: `build-scripted-fulfillment` | Not said: ask which |
| team | messaging team: `messaging-spaces`. CC agent team: `contact-center` | CC core § 9 |
| site | Calling location (address, PSTN): `provision-calling`. CC site (agent grouping): `contact-center` | CC core § 19 |
| dial plan, dial number, map a number to an entry point | Calling outbound routing: `configure-routing`. CC dial plan, dial number: `contact-center` | CC routing §§ 1–2 |
| desktop, desktop layout, agent desktop, browser softphone, WebRTC, `webex.cc`, `task.*` | your own agent desktop: no skill, no CLI (not `configure-ai-agent`; a custom desktop ignores layouts). Cisco's Agent Desktop layout, desktop profile: `contact-center` | `docs/reference/contact-center-agent-sdk.md`; CC core §§ 13–14 |
| recording | per-user Calling recording: `manage-call-settings`. CC / Customer Assist queue recording: `customer-assist`. Download converged or org/admin recordings (`admin-recordings`): `reporting` | |
| workspace | Calling device workspace: `manage-devices`; its hoteling, hot desking: `manage-call-settings`. CC journey (JDS) workspace: `contact-center`. Workspace metrics: `reporting-meetings` | CC journey § 1 |
| business hours, holidays, schedule | Calling schedule (AA/CQ/HG): `configure-features`. CC business hours, holiday list: `contact-center` | CC core §§ 15–16 |
| IVR, phone menu, voice menu | Flow Designer IVR: `design-flow` first, not `build-flow-designer`. Calling auto attendant (key presses): `configure-features`. AI that answers calls (`ai-receptionist`): `configure-features` | |
| SMS, text message | outbound: `build-notification`. Inbound with an AI agent: `build-digital-inbound` | inbound without one: `docs/playbooks/inbound-sms.md` |
| webhook, event subscription | Calling telephony events, `webhook-interest-registrations`: `call-control`. Messaging webhooks: `messaging-bots`. CC event subscriptions (`cc-subscriptions`): `contact-center` | Connect flow trigger: `docs/playbooks/webhook-triggers.md`; CC analytics § 9 |
| debug, not working, failing, not routing | Calling configuration: `wxc-calling-debug`. AI agent action: `wxcc-debug`. Not Claude Code's built-in `debug` skill | voice flow: `docs/reference/flow-designer-patterns.md` § Flow Debugging (no skill) |
| wrap-up | live Calling call (`call-controls-members`): `call-control`. CC wrap-up, aux codes (`cc-aux-code`): `contact-center`. Reasons on a Customer Assist queue: `customer-assist` | |
| voicemail | voicemail group: `configure-features`. A person's voicemail and the messages in a box (`user-call-settings-members`): `manage-call-settings` | |
| bot, chatbot, flow for my chatbot | ask: from scratch, the conversation loop (`build-digital-inbound`), or an API call (`build-action` / `build-scripted-fulfillment`)? Webex messaging bot: `messaging-bots` | |
| outbound notification, outbound flow (no channel) | ask: voice with TTS (`build-outbound-flow`), SMS/email/WhatsApp/RCS/Apple Messages (`build-notification`), or both with fallback? | |
| audio, skill profile, outdial, callback, campaign, contact list, DNC, channel, asset | `contact-center` (`cc-campaign-group` lists a group's campaigns; a Webex space is not a CC channel) | audio CC routing § 12; skills, skill profiles CC core §§ 10–11; outdial ANI routing § 3; callbacks routing § 5 (the Callback activity: `docs/reference/flow-designer-activities/_index.md`); campaigns, lists, DNC routing §§ 8–9; channels, assets routing §§ 15–16 |
| CC tenant settings, entitlements, thresholds, auto wrap-up interval, logging levels; monitoring schedule, live monitoring, barge; correct global variables on handled contacts | `contact-center` (`cc-org-settings`, `cc-tenant-config`, not `manage-identity`'s `org-settings`; `cc-monitoring-schedules`, `cc-call-monitoring`; `external-data-updates`). Calling barge-in: `call-control` | CC core §§ 21–23; CC analytics §§ 7, 15 |
| CC analytics, queue/agent stats, EWT, search fields, usage/billing report | `reporting-cc` (`cc-search-metadata`, `usage-reports`) | CC analytics |
| CC provisioning: agents, queues, entry points, teams | `contact-center` | `docs/reference/contact-center-core.md` |
| phone numbers on a user, reassign a number | `manage-call-settings` (a location's inventory: `provision-calling`) | |
| users, locations, licenses, profile fields (alternate numbers, display name), bulk CSV import (not SCIM), data region (`data-policies`) | `provision-calling` | |
| auto attendant, call queue, hunt group, paging, call park, pickup, announcements, playlists, text-to-speech (`tts-*`) | `configure-features` | |
| person or workspace call settings: forwarding, DND, executive-assistant, virtual lines (`virtual-line-settings`), operating modes (`mode-management`, user token: `docs/reference/wxcli-behavior.md` Known Issue #3), hot-desking members, hoteling | `manage-call-settings` | |
| trunks, PSTN, route groups, route lists, translation patterns, digit manipulation | `configure-routing` | |
| phones, DECT, line keys, BLF, speed dials | `manage-devices` | |
| PhoneOS / RoomOS configuration, xAPI, workspace personalization | `device-platform` | |
| E911, emergency address, ECBN | `provision-calling` (address) + `manage-call-settings` (ECBN) | |
| live call control: dial, answer, hold, transfer, park | `call-control` (user OAuth: `docs/reference/wxcli-behavior.md` Known Issue #1) | |
| CDR, call history, Calling call quality (packet loss, jitter, latency) | `reporting` | |
| "who has / which / how many" in the live org | `query-live` | |
| delete, tear down, clean up | `teardown` | `.claude/rules/cleanup.md` (read it; it does not auto-load in a customer folder) |
| Customer Assist: screen pop, wrap-up, recording, supervisors | `customer-assist` | |
| licenses: audit, unused, assign, reclaim from inactive users | `manage-licensing` (not `reporting`, not `teardown`) | |
| SCIM, directory, groups, org contacts, domain verification, org profile, org settings, roles | `manage-identity` | |
| audit events, security audit, compliance, authorizations, service app credentials | `audit-compliance` | |
| org health, "audit my org" | `org-health` (self-contained) | |
| partner, several customer orgs, switch org | | `docs/reference/wxcli-behavior.md` § 2; `docs/reference/authentication.md` |
| BroadWorks, wholesale, partner admins/tags, hybrid, UCM profile | not covered | § Out-of-Skill-Scope Command Groups |
| Webex spaces, messages, memberships, ECM, HDS | `messaging-spaces` | |
| bots, adaptive cards, cross-domain integrations | `messaging-bots` | |
| schedule or manage meetings, transcripts, meeting content | `manage-meetings` | |
| meeting quality, live meeting monitoring | `reporting-meetings` | |
| Video Mesh | `video-mesh` | |
| CUCM migration, `wxcli cucm` | `cucm-migrate`; `migration-advisor` agent | `.claude/rules/cucm-migration.md` |
| any other Webex API (endpoint, scope, raw HTTP) | | `docs/reference/INDEX.md` |
| how `wxcli` behaves: flags, paging, errors, known issues | | `docs/reference/wxcli-behavior.md` |
| Flow Designer: activities, settings, restrictions, capabilities, error codes, event flows, wiring rules, configuration fields, "can I do X in Flow Designer?", Virtual Agent V2, Queue Contact, Collect Input, Play Message, Call Patch, BRE Request, Functions Activity, flow variables, entry point routing | | `docs/reference/flow-designer-essentials.md` first (the 9 activities every flow uses); other activities: `docs/reference/flow-designer-activities/_index.md`, then the activity's file; versioning, subflows, fulfillment, TTS, debugging: `docs/reference/flow-designer-patterns.md`; FlowIR, API property names, v2 REST: `docs/reference/flow-designer-flowir.md` |
| Contact Center Control Hub: entry points, queues, teams, sites, PSTN assignment, channel assets, routing strategy, global variables, CCAI config, Analyzer reporting, Service Apps, token refresh, CJDS, "where do I configure X in Control Hub?" | CLI: `contact-center` | `docs/reference/wxcc-platform.md` first; setup: `docs/playbooks/wxcc-setup.md`; API auth: `docs/playbooks/webex-api-auth.md`; CJDS: `docs/playbooks/cjds-integration.md` |
| autonomous agent: goal, welcome message, actions, action descriptions, slot entities, sample JSON, instructions, Custom Data, Custom Event Fulfillment, CCAI config, deployment, "how do I configure X in Agent Studio?" | `configure-ai-agent` | `docs/reference/ai-agent-studio.md` first; an action's flow: `docs/reference/webex-connect.md` + `docs/playbooks/connect-flows.md`; deployment: also `docs/reference/wxcc-platform.md`; import JSON: `docs/reference/ai-agent-studio-import-json.md` |
| scripted agent: intents, entities, responses, fulfillment, AI engines, context flow, training phrases, Incoming Custom Events, state_update, voice channel fulfillment, "how do I set up a scripted agent?" | `design-scripted-agent` → `configure-scripted-agent` → `build-scripted-fulfillment` | `docs/reference/ai-agent-studio-scripted.md` first; design: `docs/playbooks/scripted-agent-design.md`; build: `docs/playbooks/scripted-agent-build.md`; voice fulfillment: flow-designer-patterns.md § Scripted Agent Fulfillment Pattern |
| digital inbound: channel Start triggers, Webex Engage nodes, Process Message, multi-turn loops, human escalation, Queue Task, Fetch Conversation Transcript, cross-channel escalation, "set up a digital channel for my agent" | `build-digital-inbound` | `docs/reference/digital-inbound.md` first; steps: `docs/playbooks/digital-inbound-agent.md`; chat → voice: `docs/playbooks/cross-channel-escalation.md`; channel nodes: connect-*.md |
| database: Supabase, PostgREST, choosing a backend, HTTP headers for DB calls, research protocol, "what database should I use?" | | `docs/reference/db-integration.md` first (backend not documented: its research protocol, don't guess); `docs/playbooks/supabase.md`; BRE: `docs/reference/bre.md` |
| Webex Connect: flow structure, nodes (HTTP Request, Branch, Evaluate, Play, Call User, Voice Node Group, channels), variable picker, Flow Outcomes, Custom Connectors, Start node triggers, flow wiring, "how do I do X in Connect?" | | `docs/reference/webex-connect.md` first; Branch, Evaluate, voice, channel nodes: `docs/reference/webex-connect-advanced.md`; action flow: `docs/playbooks/connect-flows.md` |
| Connect channel: SMS/MMS, email, RCS, Apple Messages, WhatsApp, multi-channel | send to customers: `build-notification`; receive with an AI agent: `build-digital-inbound` | `docs/reference/connect-sms.md`, `docs/reference/connect-email.md`, `docs/reference/connect-rcs.md`, `docs/reference/connect-apple-messages.md`, `docs/reference/connect-whatsapp.md`, `docs/reference/connect-multi-channel.md` |
| BRE (Business Rules Engine): DataSync, rules, CSV upload, BRE Request, data tables, sizing limits, lookup patterns, "how do I use BRE for X?" | | `docs/reference/bre.md` first; setup: `docs/playbooks/bre-setup.md`; the activity: flow-designer-activities/_index.md; vs other backends: db-integration.md |
| build the flow from a design doc | manual UI: `build-flow-designer`; programmatic (FlowIR): `build-flow-programmatic`; no design doc: `design-flow` | Not said: ask |
| outbound voice call, TTS alert | `build-outbound-flow` | |
| outbound SMS, email, WhatsApp, RCS, Apple Messages | `build-notification` | |
| diagram, visualize, drawio, presentation, deck | activity-level `.drawio`: `build-spec-diagram`; architecture HTML + PPTX: `build-solution-docs` (not MARP, not Gamma) | "a diagram from this plan": ask |
| Connect flow for my agent | single API call: `build-action`; conversation: `build-digital-inbound` | Not said: ask |

### Multi-Skill Workflows

Common goals that span several skills. When the user states one of these end goals, orchestrate the skills in sequence — don't pick just one.

| Goal | Skills in order | Why |
|---|---|---|
| Offboard a user | `manage-call-settings` → `manage-devices` → `manage-licensing` → `teardown` → `manage-identity` | settings, device, license, user, directory |
| Recording for a team | `manage-call-settings` + `configure-features` + `customer-assist` | set per person, location and queue |
| E911 for a location | `provision-calling` + `manage-call-settings` | address per location, ECBN per person |
| Shared line on phones | `manage-call-settings` + `manage-devices` | pairing is a setting; line keys are device config |
| Port numbers to users | `provision-calling` → `manage-call-settings` → `configure-routing` | numbers enter location inventory first |
| Workspace → licensed user | `teardown` → `provision-calling` → `manage-call-settings` → `manage-devices` | lifecycle change across 4 areas |
| CC overflow to a hunt group | `contact-center` + `configure-features` + `configure-routing` | two routing worlds joined by PSTN / dial plan |
| Hot desking on conference phones | `manage-devices` + `device-platform` + `manage-call-settings` | device, PhoneOS config, calling settings |
| AI agent from scratch | `design-ai-agent` → `build-action` → `configure-ai-agent` → `build-digital-inbound`, in one `wxops` agent | design first; one agent for the build |
| Voice flow | `design-flow` → review → `build-spec-diagram` (optional) → `build-flow-designer` or `build-flow-programmatic` → `docs/playbooks/wxcc-setup.md` | design doc first |
| Notification, voice fallback | `build-notification` + `build-outbound-flow` | voice needs Call User |
| Scripted agent | `design-scripted-agent` → review → `configure-scripted-agent` → `build-scripted-fulfillment` → `build-digital-inbound` | design before build |
| Solution docs from a plan | `build-solution-docs`, `build-spec-diagram` | can run both |
| Digital inbound, escalate to voice | `build-digital-inbound` → `docs/playbooks/cross-channel-escalation.md` → `design-flow` | the voice leg is a flow |

## Where the rest lives

- `docs/reference/INDEX.md` — every reference doc, one line each; `docs/reference/flow-designer-activities/_index.md` — every Flow Designer activity.
- `docs/playbooks/INDEX.md` — step-by-step guides by goal; `docs/templates/INDEX.md` — design-doc and report templates; `docs/examples/INDEX.md` — working FlowIR flows and other build artifacts.
- Rules that auto-load only when their files are touched — read them yourself when the topic comes up: `.claude/rules/cleanup.md` (`wxcli cleanup`, deletion order), `.claude/rules/cucm-migration.md` (any CUCM migration question, `/cucm-migrate`, the migration advisor), `.claude/rules/org-health.md` (changing the checks or the report; to run an audit the `org-health` skill is self-contained), `.claude/rules/doc-placement.md` (which directory owns a fact), `.claude/rules/flowir-mcp-verification.md` (before writing FlowIR).

## Out-of-Skill-Scope Command Groups

These groups are registered in the CLI but deliberately have **no skill routing** — the playbook does not cover them. Drift-gate checks **4 and 20** both read this list: check 4 asks whether a skill claims the group, check 20 asks whether a `docs/reference/*.md` describes it. One declaration answers both, because the premise of this table is that the playbook does not cover the group at all, and a group the playbook does not cover needs neither a skill nor a reference doc. If a group ever needs to be skill-routed *and* deliberately undocumented, that is a different decision and needs its own table with its own reason — do not stretch a row here to cover it.

Listing a group here is a commitment that we intentionally do not route to it. It is **not** a way to quiet the gate: if a group belongs in a skill, wire it into the skill instead. Every entry states a reason.

> **Maintainer note:** only the group names in the left column may be backticked in this section. The gate harvests every backticked token between this heading and the next one, so a backticked group name in a *reason* would silently declare that group out of scope too.

| Group | Why the playbook does not cover it |
|-------|-----------------------------------|
| `broadworks-billing-reports` | BroadWorks carrier billing. Service-provider tooling, not customer-org administration. No reference doc exists. |
| `broadworks-enterprises` | BroadWorks carrier enterprise provisioning. Service-provider scope. No reference doc exists. |
| `broadworks-subscribers` | BroadWorks carrier subscriber provisioning. Service-provider scope. No reference doc exists. |
| `broadworks-workspaces` | BroadWorks carrier workspace provisioning. Service-provider scope. No reference doc exists. |
| `wholesale-billing-reports` | Wholesale Route-to-Market carrier billing. Service-provider scope. No reference doc exists. |
| `wholesale-provisioning` | Wholesale Route-to-Market customer/subscriber provisioning. Service-provider scope. No reference doc exists. |
| `partner-admins` | Partner/VAR org administration. The playbook targets one customer org at a time; partner multi-org is handled by the switch-org top-level command, not by a skill. |
| `partner-tags` | Partner/VAR org tagging. Same reason as partner-admins. |
| `hybrid-clusters` | On-premises hybrid connector infrastructure (Expressway). Out of scope for a cloud-calling playbook. |
| `hybrid-connectors` | On-premises hybrid connector infrastructure. Same reason as hybrid-clusters. |
| `ucm-profile` | UCM calling-profile stub. The CUCM story in this repo is the migration pipeline (the cucm command group), not this group. |

## Before you trust a wxcli command

1. **Run `--help` first.** `wxcli --help` lists the groups, `wxcli <group> --help` its commands, `wxcli <group> <command> --help` its options. Never guess a command name.
2. **`--calling-data true`** on any `people` read that needs `extension` or `locationId`; without it they are silently absent.
3. **`--all`** for any "how many / which ones / are there any" — the default fetches one page. Output that says **INCOMPLETE** is missing records: conclude nothing from it.
4. **`--verify`** after a write that matters: a 2xx means accepted, not applied.
5. **`--offset` refused** (exit 2, "this endpoint ignores --offset"): use `--all` and slice with `--fields '[N:M]'`.

Everything behind these rules — every flag, paging, partner multi-org, the eleven Known Issues, cleanup — is in `docs/reference/wxcli-behavior.md`. In a source checkout only, `docs/spec-sync-contract.md` is the weekly spec-sync's definition of done (the cloud routine's prompt points there).

### Error → Known Issue Quick Reference

When you hit one of these errors, read the matching Known Issue in `docs/reference/wxcli-behavior.md` § 3:

| Error | Symptom | Known Issue |
|-------|---------|-------------|
| 400 "Target user not authorized" | `call-controls` with admin token | #1 — needs user-level OAuth |
| 404 (error 4008) | `my-call-settings` or `mode-management` | #3 — user needs Calling license |
| 404 on person settings | Admin token on user-only endpoints | #4 — 19 settings have no admin path |
| 405 on workspace settings | Workspace `/telephony/config/` endpoint | #6 — needs Professional license |
| 403 on `cc-*` commands | Token lacks `cjp:config_*` scopes (a full-admin PAT has them — verified 2026-10-13) | #11 — OAuth integration / Service App with `cjp:config_*` selected |
| 409 on location delete | Resources still assigned | See `.claude/rules/cleanup.md` |
| 400 "Required request parameter 'orgId' ... is not present" | `audit-events list`, `security-audit list`, or any `video-mesh` command | No org saved in config — run `wxcli switch-org` (or `wxcli switch-org <orgId>` in automation); fixed for new configs. See `docs/reference/meetings-infrastructure.md` gotcha #8. |
| Unexpected command name | `show-*` vs `list-*`, singular vs plural | #5 — two path families; always run `--help` first |
| `--json-body` needed | Complex nested fields in request body | #2 — run the command with `--generate-json-body` for a skeleton |
