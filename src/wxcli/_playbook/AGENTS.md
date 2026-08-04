# Webex Calling Playbook

Build and configure Webex Calling, admin, device, and messaging APIs programmatically with guided Codex assistance.

**Execution pattern:** `wxcli` CLI commands (primary) → raw HTTP (fallback).
The wxcli CLI has 178 command groups covering calling, admin, device, messaging, meetings, and contact center APIs. Raw HTTP docs in `docs/reference/` serve as reference and fallback.

## Mandatory Grounding Rule

**Never answer any question about Webex Calling from training data alone.**

For every question — capability, configuration, behavior, limits, or anything else — you MUST either:
1. Invoke the relevant skill (`configure-features`, `customer-assist`, `contact-center`, etc.), OR
2. Read the relevant reference doc in `docs/reference/`

The reference docs and skills are the authoritative source for this project. Training data about Cisco/Webex products is unreliable — product tiers get conflated, feature names change, and capabilities vary by license. If the answer isn't in the docs or skills, say so explicitly rather than filling the gap from training data.

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

**The ladder above does not apply to the `@webex/contact-center` JavaScript SDK.**
It tops out at `wxcli --help`, which has zero visibility into a JS SDK — no `wxcli`
command can tell you anything about `webex.cc` or `task.*`. For that surface only,
the order is:

1. **Live observation against a real tenant** — the wire format is repeatedly not the
   declared type (`Team` declares `{teamId}`, the wire sends `{id}`)
2. **The SDK's own TypeScript sources** — `sourcesContent` inside the shipped `.map`
3. **The published typedoc** (`web-sdk.webex.com/wxcc`) — built from the **`next`
   prerelease**, so it is *ahead of* stable and documents members that exist in no
   shipping release
4. **Your training data**

Never conclude "field X does not exist" by grepping the minified bundle: TypeScript
types are erased at compile time, so a type-only field never appears in the `.js`.
Enumerate a type's members instead. See `docs/reference/contact-center-agent-sdk.md`.

**A read-only command can be silently wrong.** Real case: the query-live recipe said
`wxcli people list -o json`, but Webex omits `extension` and `locationId` unless
`--calling-data true` is passed. The command exits 0 and returns every user, so
"how many users have extensions?" answers **0** instead of the true count. No error, no
warning. Before trusting a read, confirm via `--help` that the command was actually
capable of returning the field you are about to draw a conclusion from.

**`--help` outranks docs on command names, flags and requiredness — but NOT on two
things, both measured.** (1) **Argument ID kinds:** 79 arguments declare a kind their own
name contradicts — `location_id` help-typed "Webex PEOPLE id", `call_queue_id` typed
HUNT_GROUP. Where help and the doc disagree on an ID *kind*, the doc is right.
(2) **Enum choices:** proven
both ways — `--event all` works though the enum omits it, and `announcements
--location-id` advertises a sample ID that exits 1. On these two, a live call settles it,
not a re-read of `--help`.

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
"none found" — a false negative delivered confidently is worse than no answer.

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

---

## Quick Start

You MUST ask Codex to use the **wxc-calling-builder** agent. This is the primary interface for all operations.
The agent walks you through authentication, interviews you about what you want to build, designs
a deployment plan, executes via `wxcli` commands, and verifies the results. **Do not run `wxcli`
commands directly** — the agent handles the full workflow.

**To build or configure Webex Calling:** the **wxc-calling-builder** agent → describe what you want.

**To migrate from CUCM:** the **wxc-calling-builder** agent → "Run a CUCM migration" and provide
the CUCM host/credentials. The agent runs the full pipeline: discover → normalize → map → analyze
→ resolve addresses → review decisions → plan → execute → verify. See the CUCM migration section
below for what the pipeline does. Pipeline and tool details in `.codex/rules/cucm-migration.md` (path-scoped).

**To debug a failing configuration:** Use `the `wxc-calling-debug` skill` (this one is a skill, invoked directly).

**To query live org state:** Use `the `query-live` skill` for read-only questions about the current environment ("who has call forwarding enabled?", "which locations have no users?", "show me all hunt groups").

**To audit org health:** the **wxc-calling-builder** agent → "audit my org". The `org-health` skill orchestrates collection, analysis, and HTML report generation.

### Agent Invocation Pattern

Codex orchestrates subagents itself — it spawns them, routes follow-up
instructions, waits for results, and closes agent threads. There is no
phase-per-invocation requirement and no manual message-passing.

- To build/configure/tear down: ask Codex to use the **wxc-calling-builder**
  agent (defined in `.codex/agents/wxc-calling-builder.toml`), describing what
  you want. Codex sequences multi-step work (auth → provisioning → feature
  config) within the turn and keeps context; refine conversationally ("also add
  voicemail to that user").
- For CUCM migration advisory and decision review, ask Codex to use the
  **migration-advisor** agent (`.codex/agents/migration-advisor.toml`).
### Agent Model Selection

Codex agents inherit the session model; task complexity maps to reasoning
effort, set per agent via `model_reasoning_effort` in its TOML: cleanup /
read-only checks → `low`; standard provisioning and feature config → `medium`;
multi-phase CUCM migration and architectural decisions → `high`. The
migration-advisor runs at `high`; the builder at `medium`.
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

### Agent Orchestration — Long-Running Work

Codex manages subagent lifecycle and result collection, so no manual
silence-detection or transcript-inspection protocol is needed. For
long-running commands (e.g. `wxcli cucm execute`), run them and let Codex await
completion; when a command must run outside the sandbox, Codex escalates for
your approval. Always verify final state with `wxcli` read commands rather than
trusting a single command's self-reported result.
## File Map

### Agent & Skills

| Path | Purpose |
|------|---------|
| `.codex/agents/wxc-calling-builder.toml` | Main builder agent — drives the full workflow |
| `.codex/agents/migration-advisor.toml` | Opus-powered CCIE-level migration advisor — architectural reasoning + decision review |
| `.codex/skills/provision-calling/` | Skill: provision users, locations, licenses |
| `.codex/skills/teardown/` | Skill: dependency-safe teardown, `wxcli cleanup`, manual deletion procedure |
| `.codex/skills/configure-features/` | Skill: set up call features (AA, CQ, HG, etc.; Customer Assist → see customer-assist skill) |
| `.codex/skills/customer-assist/`      | Skill: configure Customer Assist (screen pop, wrap-up, recording, supervisors) |
| `.codex/skills/manage-call-settings/` | Skill: configure person/workspace call settings, phone number add/remove/reassign |
| `.codex/skills/configure-routing/` | Skill: configure routing (trunks, dial plans, PSTN) |
| `.codex/skills/manage-devices/` | Skill: manage devices (phones, DECT, workspaces) |
| `.codex/skills/device-platform/` | Skill: manage PhoneOS/RoomOS device configs, workspace personalization, xAPI; 9800-series phones (9811/9821/9841/9851/9861/9871) use PhoneOS (not RoomOS) |
| `.codex/skills/call-control/` | Skill: real-time call control, webhooks |
| `.codex/skills/reporting/` | Skill: CDR query engine (75 recipes + composition guide), report templates, recordings |
| `.codex/skills/reporting-cc/` | Skill: Contact Center analytics (queue stats, agent stats, EWT, summaries) |
| `.codex/skills/reporting-meetings/` | Skill: meetings quality, workspace metrics, historical analytics, live monitoring |
| `.codex/skills/wxc-calling-debug/` | Skill: debug failing configurations |
| `.codex/skills/manage-identity/` | Skill: SCIM sync, directory, groups, contacts, domains |
| `.codex/skills/audit-compliance/` | Skill: audit events, security, compliance, authorizations |
| `.codex/skills/manage-licensing/` | Skill: license audit, assignment, reclamation |
| `.codex/skills/messaging-spaces/` | Skill: manage spaces, teams, memberships, ECM, HDS |
| `.codex/skills/messaging-bots/` | Skill: build bots, adaptive cards, webhooks, cross-domain integrations |
| `.codex/skills/manage-meetings/` | Skill: schedule, manage, query meetings + content |
| `.codex/skills/video-mesh/` | Skill: Video Mesh monitoring and threshold configuration |
| `.codex/skills/contact-center/` | Skill: CC provisioning (agents, queues, entry points, dial numbers, flows, campaigns) |
| `.codex/skills/org-health/` | Skill: org health assessment — collect, analyze 18 checks, HTML report |
| `.codex/skills/cucm-migrate/` | Skill: execute CUCM-to-Webex migration from exported deployment plan |
| `.codex/skills/query-live/` | Skill: read-only natural language queries against live Webex Calling state |

### Skill Disambiguation

When multiple skills could match, use this lookup. (Basic skill-vs-skill routing already lives in each skill's `NOT for:` description, which the session always sees — the rows below cover only what those don't resolve: subtle overlaps, Calling-vs-CC terminology collisions, and undocumented capabilities.)

| If the user wants to... | Use this skill | NOT this one |
|--------------------------|---------------|-------------|
| Add/remove phone numbers on a user, number reassignment | `manage-call-settings` | `provision-calling` (that's for initial user/license creation; provision-calling owns number *inventory*, not per-user assignment) |
| Update user profile fields (alternate numbers, display name) | `provision-calling` | `manage-call-settings` (profile fields are People API, not telephony config) |
| Configure voicemail groups (shared location mailbox) | `configure-features` | `manage-call-settings` ("voicemail" collides: groups are a location feature, not person voicemail) |
| **Calling vs CC terminology — when the same word means different things:** | | |
| "Create a queue" (Calling call queue) | `configure-features` | `contact-center` (that's CC queues — different API, different entity) |
| "Create a queue" (Contact Center queue) | `contact-center` | `configure-features` (that's Calling queues — no skill-based routing) |
| "Set up a dial plan" (Calling outbound routing) | `configure-routing` | `contact-center` (CC dial plans map DNs to entry points, different API) |
| "Set up a dial plan" (CC DN-to-entry-point mapping) | `contact-center` | `configure-routing` (that's Calling outbound routing) |
| "Create a team" (Messaging spaces) | `messaging-spaces` | `contact-center` (CC teams group agents for routing) |
| "Create a team" (CC agent grouping) | `contact-center` | `messaging-spaces` (that's collaboration spaces) |
| "Set up recording" (per-user call recording) | `manage-call-settings` | `customer-assist` (that's CC queue recording) |
| "Set up recording" (CC queue recording) | `customer-assist` | `manage-call-settings` (that's per-user Calling recording) |
| "Download/export recordings" (converged recordings) | `reporting` | `manage-call-settings` (that's the per-user toggle, not retrieval) |
| "Configure the site" (Calling location) | `provision-calling` | `contact-center` (CC sites are logical agent groupings, not locations) |
| "Configure the site" (CC site for agent teams) | `contact-center` | `provision-calling` (Calling locations have addresses and PSTN) |
| "Create a workspace" (Calling device workspace) | `manage-devices` | `contact-center` (CC JDS workspaces are journey data containers) |
| "Set up business hours / holidays" (Calling schedule) | `configure-features` | `contact-center` (CC business hours are a separate entity type) |
| "Set up business hours / holidays" (CC schedule) | `contact-center` | `configure-features` (Calling schedules attach to AA/CQ/HG) |
| Build a custom agent desktop / browser softphone with WebRTC audio | **`docs/reference/contact-center-agent-sdk.md`** (a reference doc, not a skill — no CLI path exists for this) | `contact-center` (that provisions the agents/queues the desktop connects to) and **not** `cc-desktop-layout` (that configures Cisco's own Agent Desktop; a custom desktop ignores layouts entirely) |
| **Undocumented capabilities — user asks, table must route:** | | |
| Set up executive-assistant delegation | `manage-call-settings` | `configure-features` (delegation is a person setting, not a call feature) |
| Configure line keys, BLF, speed dials on phones | `manage-devices` | `manage-call-settings` (line key templates are device config, not call settings) |
| Digit manipulation (strip digits, add country code) | `configure-routing` (translation patterns) | `manage-call-settings` (that's per-person settings, not digit transforms) |
| Bulk import users from CSV | `provision-calling` | `manage-identity` (SCIM is directory sync, not bulk user provisioning) |
| How many licenses are unused / license audit | `manage-licensing` | `reporting` (reporting is CDR/call data, not license inventory) |
| Verify domain for SCIM / DNS setup | `manage-identity` | `provision-calling` (domain verification is identity, not calling provisioning) |
| Enable hoteling on a workspace | `manage-call-settings` | `manage-devices` (hoteling is a workspace calling setting, not device provisioning) |
| Import org contacts / directory entries | `manage-identity` | `provision-calling` (org contacts are directory, not calling users) |
| Set where calling data is stored (data/storage policy region, org or per-location) | `provision-calling` (group: `data-policies`) | `manage-call-settings` (it is an org/location storage policy, not a per-person setting) |
| List the campaigns belonging to a campaign group | `contact-center` (group: `cc-campaign-group`) | `configure-features` (outbound campaigns are Contact Center, not Calling) |
| Reclaim licenses from inactive users | `manage-licensing` | `teardown` (license reclamation ≠ resource deletion) |
| Manage announcement repository files/playlists (AA/CQ greetings), or generate text-to-speech prompts | `configure-features` (groups: `announcements` — incl. `tts-generate`/`tts-usage`/`tts-status`/`tts-voices`; `announcement-playlists`, `cq-playlists`) | `reporting` (that's recordings, not announcements) |
| Set up an AI that answers calls, its intents, or the knowledge base it answers from | `configure-features` (group: `ai-receptionist`) | `configure-features`'s **Auto Attendant** (that's a key-press IVR menu, not an AI) and `contact-center` (AI Receptionist is a Calling feature, not a WxCC agent) |
| Configure E911 emergency services/addresses (`emergency-services` group) | `provision-calling` (location addresses) + `manage-call-settings` (per-person ECBN) | `wxc-calling-debug` |
| Virtual line call settings (`virtual-line-settings`) | `manage-call-settings` (virtual lines are person-like settings; see `virtual-lines.md`) | `provision-calling` |
| Operating modes / mode management (`mode-management`, user-token only per Known Issue #3) | `manage-call-settings` | `configure-features` (`operating-modes` location/feature side stays there) |
| Org/admin recordings retrieval (`admin-recordings`) | `reporting` | `manage-meetings` |
| Org profile, settings, roles (`identity-org`, `org-settings`, `roles`) | `manage-identity` | `audit-compliance` |
| Person-level hot-desking members (`hot-desking-members`) | `manage-call-settings` (person settings) | `manage-devices` (workspace/device-level hot-desk stays there) |

### Multi-Skill Workflows

Common admin goals that span multiple skills. When the user states one of these end goals, orchestrate the skills in sequence — don't pick just one.

| User goal | Skills needed (in order) | Why it's multi-skill |
|-----------|------------------------|---------------------|
| Offboard a user | `manage-call-settings` → `manage-devices` → `manage-licensing` → `teardown` → `manage-identity` | Must remove settings, release device, reclaim license, delete user, sync directory |
| Set up call recording for a team | `manage-call-settings` (per-person toggle) + `configure-features` (location recording policy) + `customer-assist` (if CX queue recording) | Recording config lives at person, location, AND queue level |
| E911 compliance for a location | `provision-calling` (emergency address on location) + `manage-call-settings` (per-person ECBN) | Address is location-level, ECBN callback number is per-person |
| Shared line on physical phones | `manage-call-settings` (shared line appearance / exec-assistant) + `manage-devices` (line key assignment on devices) | Pairing is a call setting, line key layout is device config |
| Port numbers and assign to users | `provision-calling` (location number inventory) → `manage-call-settings` (assign to users) → `configure-routing` (update dial plan if needed) | Numbers flow through location inventory before user assignment |
| Convert workspace to licensed user | `teardown` (decommission workspace) → `provision-calling` (create user, assign license) → `manage-call-settings` (voicemail, forwarding) → `manage-devices` (reassign device) | Workspace-to-user is a lifecycle change spanning 4 domains |
| CC overflow to Calling hunt group | `contact-center` (CC queue/entry point config) + `configure-features` (hunt group) + `configure-routing` (dial plan to connect them) | CC and Calling are separate routing worlds joined by PSTN/dial plan |
| Hot desking on conference phones | `manage-devices` (enable hot desking; workspace/device level) + `device-platform` (PhoneOS config keys for hot desk behavior) + `manage-call-settings` (workspace hoteling settings AND person-level hot-desking members via `hot-desking-members`) | Device provisioning, firmware config, and calling settings are three layers; person-level members are person settings |

### Reference Docs — Webex API Surface

| Path | Purpose |
|------|---------|
| `docs/reference/authentication.md` | Auth methods, tokens, scopes, OAuth flows |
| `docs/reference/provisioning.md` | People (profile fields, phoneNumbers array incl. alternate1/alternate2), licenses, locations, org setup |
| `docs/reference/call-features-major.md` | Auto attendants, call queues, hunt groups |
| `docs/reference/call-features-additional.md` | Paging, call park, pickup, voicemail groups, Customer Assist |
| `docs/reference/ai-receptionist.md` | AI Receptionist (AI call answering), intents, knowledge bases + documents |
| `docs/reference/person-call-settings-handling.md` | Call forwarding, DND, call waiting, sim/sequential ring |
| `docs/reference/person-call-settings-media.md` | Voicemail, caller ID, privacy, barge, recording, intercept |
| `docs/reference/person-call-settings-permissions.md` | Incoming/outgoing permissions, feature access, executive/assistant |
| `docs/reference/person-call-settings-behavior.md` | Calling behavior, app services, hoteling, receptionist, phone number add/remove/reassign, ECBN |
| `docs/reference/self-service-call-settings.md` | User self-service call settings (/people/me/ endpoints) |
| `docs/reference/location-calling-core.md` | Location enablement, internal dialing, voicemail policies, voice portal |
| `docs/reference/location-calling-media.md` | Announcements, playlists, schedules, access codes |
| `docs/reference/location-recording-advanced.md` | Call recording, caller reputation, conference, supervisor, operating modes |
| `docs/reference/call-routing.md` | Dial plans, trunks, route groups, route lists, translation patterns, PSTN |
| `docs/reference/devices-core.md` | Device CRUD, activation, device configurations, telephony devices |
| `docs/reference/devices-dect.md` | DECT networks, base stations, handsets, hotdesking |
| `docs/reference/devices-workspaces.md` | Workspaces, workspace settings, workspace locations |
| `docs/reference/devices-platform.md` | RoomOS device configurations, workspace personalization, xAPI |
| `docs/reference/call-control.md` | Real-time call control (dial, answer, hold, transfer, park, recording) |
| `docs/reference/webhooks-events.md` | Webhooks: CRUD, telephony + messaging event types, payloads |
| `docs/reference/reporting-analytics.md` | CDR, report templates, call quality, queue/AA stats |
| `docs/reference/virtual-lines.md` | Virtual line/extension settings, voicemail, recording |
| `docs/reference/emergency-services.md` | E911, emergency addresses, ECBN |

### Reference Docs — Admin & Identity APIs

| Path | Purpose |
|------|---------|
| `docs/reference/admin-org-management.md` | Organizations, org settings, contacts, roles, domains |
| `docs/reference/admin-identity-scim.md` | SCIM users/groups, schemas, bulk ops, identity org, people, groups |
| `docs/reference/admin-licensing.md` | License inventory, assignment, usage auditing |
| `docs/reference/admin-audit-security.md` | Admin audit events, security audit, compliance events |
| `docs/reference/admin-hybrid.md` | Hybrid clusters/connectors, analytics, meeting quality |
| `docs/reference/admin-partner.md` | Partner admins, tags, partner reports |
| `docs/reference/admin-apps-data.md` | Service apps, authorizations, activation emails, data sources, recordings, resource groups |

### Reference Docs — Messaging APIs

| Path | Purpose |
|------|---------|
| `docs/reference/messaging-spaces.md` | Spaces, messages, memberships, teams, ECM, HDS |
| `docs/reference/messaging-bots.md` | Bot development, adaptive cards, room tabs, cross-domain recipes |

### Reference Docs — Meetings APIs

| Path | Purpose |
|------|---------|
| `docs/reference/meetings-core.md` | Meeting CRUD, templates, controls, registrants, interpreters, breakouts, surveys |
| `docs/reference/meetings-content.md` | Transcripts, captions, chats, summaries, meeting messages |
| `docs/reference/meetings-settings.md` | Preferences, session types, tracking codes, site settings, polls, Q&A, reports |
| `docs/reference/meetings-infrastructure.md` | Video Mesh (clusters, nodes, health, utilization), participants, invitees |

### Reference Docs — Contact Center APIs

| Path | Purpose |
|------|---------|
| `docs/reference/contact-center-core.md` | CC agents, queues, entry points, teams, skills, desktop, configuration |
| `docs/reference/contact-center-routing.md` | CC dial plans, dial number-to-entry-point mapping, campaigns, flows, audio, contacts, outdial |
| `docs/reference/contact-center-analytics.md` | CC AI, monitoring, subscriptions, tasks, search |
| `docs/reference/contact-center-journey.md` | JDS: workspaces, persons, identity, profile views, events, WXCC subscription |
| `docs/reference/contact-center-agent-sdk.md` | `@webex/contact-center` JS SDK — building a **custom agent desktop** (browser softphone): `webex.cc`/`task.*`, WebRTC audio, events, flow variables, `cjp:user` runtime scope. Not the REST/`wxcli` surface |

### Migration (KB, Runbooks, Tool)

Detailed migration context lives in `.codex/rules/cucm-migration.md` (auto-loaded when touching migration paths). Contains: knowledge base file map (8 KB docs for the Opus advisor), operator runbooks (3 docs for pipeline walkthrough, decision guide, tuning), migration tool pipeline commands, advisory workflow, report/diff/notice generation commands, and the phase-by-phase agent invocation example.

**Read the rule when:** handling any CUCM migration question, running `the `cucm-migrate` skill`, or working with the migration advisor agent — even if not editing migration source files directly.

### CLI (wxcli) — Primary Execution Layer

| Path | Purpose |
|------|---------|
| `wxcli --help` | Shows all command groups |
| `wxcli <group> --help` | Shows commands within a group |
| `wxcli <group> <command> --help` | Shows options for a command |

### Org Health Assessment

Detailed context in `.codex/rules/org-health.md` (auto-loaded when touching org health paths). Contains: file map (models, collector, checks, analyze, report), run instructions, and check category breakdown (Security Posture, Routing Hygiene, Feature Utilization, Device Health).

**Read the rule when:** running an org health audit, modifying checks, or working on the report generator.

### CUCM→Webex Migration Tool

The migration tool is wired into the CLI as `wxcli cucm <command>`. Pipeline workflow, report generation, and advisory details are in `.codex/rules/cucm-migration.md`.

## Out-of-Skill-Scope Command Groups

These groups are registered in the CLI but deliberately have **no skill routing** — the playbook does not cover them. Drift-gate check 4 reads this list.

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
| `cc-legacy-flows` | Superseded by the current cc-flow group, which the contact-center skill already routes to. Retained for API parity only. |
| `ucm-profile` | UCM calling-profile stub. The CUCM story in this repo is the migration pipeline (the cucm command group), not this group. |

## CLI Status & Known Issues

**178 command groups covering calling, admin, device, messaging, meetings, wholesale, and contact center APIs.** The `converged-recordings` group combines generated CRUD commands with hand-written `download` and `export` commands.

### Common Flags (`--fields`, `--output`, `--json-body`, `--all`, `--verify`)

Every generated command takes `--fields` and `--output`/`-o` — **including `update`, `delete`, and action commands.** An earlier build had `--output` only on list/show/create and no `--fields` at all; that split is gone, so don't assume a write command lacks them.

- **`--fields`** — a JMESPath expression applied to the response before rendering. Same syntax on every command: a projection (`[].{name:name,id:id}`) reshapes the output, a filter (`` [?enabled==`false`] ``) narrows it.
- **`--output`/`-o`** — `table|json|text` on every command, plus `id` (create's default) on create only.
- **`--json-body`** accepts inline JSON, `file://path`, a bare path, or `-` for stdin (pairs with `--generate-json-body`; see Known Issue #2 below).
- **`--all`** — on **every `list` command**: fetch every page, not just the first. Default is one fetch; `--all` walks the whole collection and **overrides `--limit`**. Read the detail below before trusting a count.
- **`--verify`** — on **328 update commands** (every PUT/PATCH that has a same-path GET to read back from). Off by default. After the write it re-reads the resource and reports any field you sent that did not take, then prints either `Verified: … all N sent field(s) match.` or a per-field `sent X, now Y` list. It compares **only the fields you sent**, and it **never changes the exit code** — servers legitimately normalise values, so the CLI reports the difference and leaves the judgement to you. Use it whenever a write's success matters: a 2xx means the request was *accepted*, not that it was *applied*. `device-members` is the worked case — it does no port validation, so `PRIMARY` on two ports returns 200 and both persist. A command with no same-path GET deliberately does **not** offer the flag, because a `--verify` that silently verifies nothing is worse than none.

**The `--calling-data` interlock.** `people list/show/create/update/show-me` now check the `--fields` expression before rendering: ask for `extension` or `locationId` without `--calling-data`, and the CLI says so on stderr instead of handing back a silent, confident zero. Measured live on 2026-08-01 — `people list --fields '[].extension' --all` returns `[]` on an org where 15 users have extensions; adding `--calling-data true` returns all 15. The check fires only on endpoints that actually accept the flag, so it can never point you at an option a command does not have.

Four worked examples:

```bash
# Projection — pick just the fields you need
wxcli people list --calling-data true --fields '[].{name:displayName,extension:extension}' -o json

# Filter — JMESPath predicates narrow the response client-side, before rendering
wxcli call-queue list --fields '[?enabled==`false`].name' -o json

# --fields + -o text: one bare value per line, composable in a shell pipeline
wxcli locations list --fields '[].id' -o text | while read -r LOC_ID; do
  wxcli call-park list "$LOC_ID" -o json
done

# --all: never answer "how many?" from a single page
wxcli people list --calling-data true --all --fields 'length(@)' -o json
```

If `--fields` reduces a non-empty response to an empty one, a note goes to stderr naming the unfiltered record count — stdout stays pipeable. The note states the fact (0 of N matched) without diagnosing the cause: it can mean a wrong expression, or it can mean the filter genuinely matched nothing. Decide which based on the expression and what you expected, not from the note alone.

**`--all` in detail — read this before counting or aggregating anything.** The default for a list command is a **single fetch**, which on a paging endpoint quietly hands back page one. `--all` walks the whole collection and overrides `--limit`. Three paging shapes are handled, so it behaves the same across the CLI: `Link: rel="next"`, Contact Center `page`/`pageSize`, and SCIM `startIndex`/`count`.

Three behaviors that will otherwise read as bugs:

- **It is deliberately a no-op on endpoints the spec says do not paginate** — that is roughly half the commands carrying it. The flag is uniform on every list command *by design*: an option present on most commands but not all teaches a rule that breaks unpredictably, costing a failed call plus a `--help` round trip each time (the same reasoning that closed the `--output` gap). One page back from `--all` on a non-paging endpoint is correct, not a failure.
- **Walking is bounded at 1000 pages**, overridable with `WXCLI_MAX_PAGES`. Hitting the ceiling prints an error to stderr containing the word **INCOMPLETE**. That word means records are missing — not that a request failed. Do not draw a conclusion from output that produced it.
- **Without `--all`, a truncated read warns on stderr, not stdout.** A single fetch that left pages behind prints `Note: N records returned and the server has more pages. Re-run with --all to fetch every page`. **You will see that note — do not assume otherwise.** (Measured 2026-08-01 on Codex and Codex 0.144.1: both merge stderr into the tool result the model reads, so it stays visible when stdout is piped, redirected to a file, or large enough to be truncated to a head preview — the note is written by `rest_get` *before* any row is rendered, so it lands on line 1. It is lost only if you suppress it yourself with `2>/dev/null` or `WXCLI_NO_PAGE_WARN=1`.) The failure mode this guards against is therefore *ignoring* the note, not missing it: if you see it and still answer a "how many" question, the answer is wrong. `WXCLI_NO_PAGE_WARN=1` suppresses the note when you have taken one page on purpose.

One precision on "overrides `--limit`": it overrides what is **fetched**. In `-o table` mode `--limit` still caps *printed* rows (with a visible `... N more` row); `-o json` prints everything fetched.

Practical rule: any question of the form *how many*, *which ones*, or *are there any* needs `--all` on a paging endpoint. A read that merely fetches a known record by ID does not.

Watch the inverse too: on a command whose default already walks every page, passing `--limit N` **switches it to a single fetch** and silently drops the rest. `--limit` narrows; it never just "caps the display."

### Partner Multi-Org Support

wxcli supports partner/VAR/MSP admins who manage multiple customer orgs with a single partner token.

- **`wxcli configure`** — saves an `orgId` to the config file for every token. On a multi-org token it prompts for a selection; on a single-org token it saves that org automatically. It will not overwrite an org that is already configured.
- **`wxcli switch-org`** — change the active target org at any time. On a single-org token it now saves that org to the config too. The bare form prompts interactively, which will block a script or agent forever on a multi-org token — in automation always pass the id: `wxcli switch-org <orgId>`.
- **`wxcli clear-org`** — remove the saved `orgId` to revert to single-org behavior.
- **`wxcli whoami`** — shows a "Target:" line when an org is set.
- **Most generated commands** auto-inject `orgId` from config on endpoints that accept it (generator `auto_inject_from_config`). No flag is required — the parameter is injected transparently.
- The former hand-coded trio (licenses, locations, numbers) is retired — all three are generated modules now with the same orgId injection. `users` is an alias for the generated `people` group; `licenses-api` is a deprecated one-release alias for `licenses` (renamed 2026-07-02).
- The builder agent has a blocking org confirmation step at session start (section 2b) when a partner token is detected.

See `docs/reference/authentication.md` (Partner/Multi-Org Tokens section) for full details.

### Error → Known Issue Quick Reference

When you hit one of these errors, jump to the matching known issue:

| Error | Symptom | Known Issue |
|-------|---------|-------------|
| 400 "Target user not authorized" | `call-controls` with admin token | #1 — needs user-level OAuth |
| 404 (error 4008) | `my-call-settings` or `mode-management` | #3 — user needs Calling license |
| 404 on person settings | Admin token on user-only endpoints | #4 — 19 settings have no admin path |
| 405 on workspace settings | Workspace `/telephony/config/` endpoint | #6 — needs Professional license |
| 403 on `cc-*` commands | PAT or wrong OAuth scopes | #11 — needs `cjp:config_*` OAuth scopes |
| 409 on location delete | Resources still assigned | See `.codex/rules/cleanup.md` |
| 400 "Required request parameter 'orgId' ... is not present" | `audit-events list`, `security-audit list`, or any `video-mesh` command | No org saved in config — run `wxcli switch-org` (or `wxcli switch-org <orgId>` in automation); fixed for new configs. See `docs/reference/meetings-infrastructure.md` gotcha #8. |
| Unexpected command name | `show-*` vs `list-*`, singular vs plural | #5 — two path families; always run `--help` first |
| `--json-body` needed | Complex nested fields in request body | #2 — run the command with `--generate-json-body` for a skeleton |

### Known issues

1. **call-controls requires user-level OAuth.** Admin tokens get 400 "Target user not authorized". The CLI now detects this error and prints a tip about needing user-level OAuth.
2. **Complex nested settings need `--json-body`.** The generator skips deeply nested object/array body fields. Run the command with `--generate-json-body` to print an indented request-body skeleton and exit before authenticating, e.g. `wxcli user-settings update-call-forwarding PERSON_ID --generate-json-body`; edit the printed skeleton and pass it back via `--json-body`. Caveat, verified live: `--generate-json-body` does not bypass required positional arguments — `wxcli call-queue create --generate-json-body` fails with `Missing argument 'LOCATION_ID'`; pass a placeholder positional first, e.g. `wxcli call-queue create dummy-location-id --generate-json-body`.
3. **my-call-settings and mode-management require calling-licensed user.** All `/people/me/*` endpoints return 404 (error 4008) if the authenticated user doesn't have a Webex Calling license. The `my-call-settings` group (130 commands) covers base + UserHub Phase 2/3/4/5 self-service endpoints. Phase 5 was folded in on 2026-07-29 — it had been shipping as its own group named `call-settings-for-me-phase-5`; its 7 commands are now `show-personal-assistant`, `update-personal-assistant`, `show-voicemail-rules`, `update-voicemail-pin`, `show-hoteling-guest`, `update-hoteling-guest`, `list-available-hosts`. The old group name is **deliberately not aliased**: `my-call-settings show`/`update`/`list` are the Preferred Answer Endpoint commands, so an alias would have answered a different question with exit 0. The CLI detects this error and prints a tip.
4. **19 person settings are user-only (no admin path).** Admin tokens get 404. Use `wxcli my-call-settings` with user-level OAuth. Includes core settings (`callBlock`, `callCaptions`, `anonymousCallReject`, `callNotify`, `preferredAnswerEndpoint`, `guestCalling`, `modeManagement`) plus informational/read-only endpoints (`availableCallerIds`, `queues`, `services`, etc.). See `docs/reference/self-service-call-settings.md` gotchas.
5. **Two path families for person settings.** Classic `/people/{id}/features/` vs newer `/telephony/config/people/{id}/`. Some names differ. See `docs/reference/person-call-settings-behavior.md` (lines 36-54) for the full mapping table.
6. **Workspace `/telephony/config/` settings require Professional license.** Basic workspaces get 405. See `docs/reference/devices-workspaces.md` gotcha #10 for the endpoint-by-license matrix.
7. **Customer Assist queues require `--has-cx-essentials true` on `call-queue` commands.** Use `wxcli customer-assist` (alias `cx-essentials`) as the primary CLI group for CX queue management. Standard `call-queue list` omits CX queues unless the flag is passed. See `docs/reference/call-features-additional.md` cross-cutting gotchas.
8. **Supervisor delete returns 204 but supervisor persists.** Workaround: `update-supervisors` with `action: DELETE` on each agent. See `docs/reference/call-features-additional.md` gotchas.
9. **`virtual-extensions` commands use wrong ID type.** Uses `VIRTUAL_EXTENSION`-encoded IDs but virtual lines use `VIRTUAL_LINE` IDs. Still separate path families in the spec (`virtualExtensions/{extensionId}` vs `virtualLines/{virtualLineId}`). `wxcli cleanup` uses raw REST as a workaround. See `docs/reference/virtual-lines.md` Gotchas #9.
10. **Device config schema is firmware-dependent.** Per-line ringtone was absent on PhoneOS 3.5/3.6 but fixed in 4.1. Offline/expired devices retain a stale schema. See `docs/reference/devices-platform.md` gotchas #10-11.
11. **Contact Center (`cc-*`) commands require CC-scoped OAuth and region config.** PATs do NOT carry `cjp:config` scopes — even full admins on CC orgs get 403. Use an OAuth integration with `cjp:config_read`/`cjp:config_write` explicitly selected, then re-run the OAuth flow. The CC API also requires the bare UUID org ID (not the base64 Spark ID); `get_cc_org_id()` in `config.py` handles decoding. See `docs/reference/contact-center-core.md` gotchas #18-23. **Scope of this issue: the config surface only.** A PAT *does* carry `cjp:user`, the per-agent runtime scope — verified live driving `register()`/`stationLogin()`/`setAgentState()` through the `@webex/contact-center` JS SDK. See `docs/reference/contact-center-agent-sdk.md` §10.

### Cleanup Command

Detailed context in `.codex/rules/cleanup.md` (auto-loaded when touching `cleanup.py`). Contains: all flags, 13-layer deletion order, and known behaviors (virtual line workaround, location disable propagation, workspace ordering).

**Read the rule when:** running `wxcli cleanup`, modifying cleanup logic, or debugging deletion failures.

