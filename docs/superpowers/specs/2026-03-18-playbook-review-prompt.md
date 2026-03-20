# Webex Calling Playbook Review

You are evaluating a Webex Calling playbook built with Claude Code. The playbook consists of:

- **1 agent workflow** (`.claude/agents/wxc-calling-builder.md`) — interviews the user, designs a deployment
  plan, dispatches to domain-specific skills, executes via wxcli CLI commands, verifies results
- **14 skills** (`.claude/skills/*/SKILL.md`) — each covering a specific domain: provisioning, call features,
  call settings, routing, devices, device platform, call control, reporting, identity/SCIM, audit/compliance,
  licensing, messaging spaces, messaging bots, and debugging
- **~39 reference docs** (`docs/reference/*.md`, excluding `_review-*.md`) — every Webex Calling API surface
  documented with SDK method signatures and Raw HTTP sections
- **~100 CLI command groups** (`wxcli`) — the execution layer, generated from an OpenAPI spec
- **README.md** and **CLAUDE.md** — project documentation

## What was built

A system where Claude Code can autonomously provision and configure Webex Calling environments by running
wxcli CLI commands via the Bash tool. The CLI wraps the Webex REST API. The agent workflow guides the
conversation (interview → design → execute → verify), dispatches to domain-specific skills via a SKILL
DISPATCH table, and the skills handle specific domains with CLI command mappings and gotchas.

## Architecture

The agent workflow has a SKILL DISPATCH section with a dispatch table mapping 15 task domains to skill files.
Skills are loaded on-demand as the agent enters each domain's execution steps. Some admin operations (org
settings, hybrid monitoring, partner operations) are handled inline via reference docs rather than dedicated
skills.

## Your task

Dispatch 4 review agents in parallel. Each agent reads specific files, evaluates them against specific
criteria, and returns a findings table. After all 4 complete, synthesize their findings into a single
prioritized punch list.

---

## Agent 1: Agent Architecture Reviewer

**Persona:** Senior AI agent architect who has built production Claude Code agents. Evaluates whether the
agent workflow and skills will actually guide Claude to do the right thing at the right time.

**Files to read (ONE AT A TIME — take notes after each):**

First, read the orchestrator:
1. `.claude/agents/wxc-calling-builder.md` — the main agent workflow (~600 lines)

Then read all 14 skills (you have 1M context — read them all):
2. `.claude/skills/provision-calling/SKILL.md`
3. `.claude/skills/configure-features/SKILL.md`
4. `.claude/skills/manage-call-settings/SKILL.md`
5. `.claude/skills/configure-routing/SKILL.md`
6. `.claude/skills/manage-devices/SKILL.md`
7. `.claude/skills/device-platform/SKILL.md`
8. `.claude/skills/call-control/SKILL.md`
9. `.claude/skills/reporting/SKILL.md`
10. `.claude/skills/manage-identity/SKILL.md`
11. `.claude/skills/audit-compliance/SKILL.md`
12. `.claude/skills/manage-licensing/SKILL.md`
13. `.claude/skills/messaging-spaces/SKILL.md`
14. `.claude/skills/messaging-bots/SKILL.md`
15. `.claude/skills/wxc-calling-debug/SKILL.md`

If context gets tight, use subagents to read groups of skills and report findings back.

**Evaluate:**

1. **Workflow completeness** — Does the agent workflow cover the full lifecycle? Are there gaps where Claude
   would be left without instructions? What happens if the user changes their mind mid-execution?
2. **SKILL DISPATCH table accuracy** — Does every skill file referenced in the dispatch table actually exist?
   Are the task domain descriptions accurate? Would Claude route to the correct skill for ambiguous requests
   like "set up call forwarding" (manage-call-settings) vs "create a hunt group" (configure-features)?
3. **Skill consistency** — Do all 14 skills follow the same structural pattern? (Load refs → verify auth →
   check prereqs → plan → execute → verify → report) Are there skills that deviate or are missing sections?
4. **Error recovery** — What happens when a wxcli command fails? Does the workflow give Claude enough
   guidance to diagnose and recover? Is the error handling pattern consistent across all skills? Does the
   debug skill integrate well with the others?
5. **Context efficiency** — How much of the agent/skill content is actually useful vs boilerplate? Could
   any skills do their job with less text? Are there sections that repeat information already in other
   skills or reference docs?
6. **Skill boundaries** — Do the 14 skills have clear, non-overlapping scopes? Or are there gray areas?
   Specific overlaps to check:
   - provision-calling vs manage-licensing (both touch licenses)
   - configure-features vs manage-call-settings (user says "configure voicemail" — which skill?)
   - manage-devices vs device-platform (both touch devices)
   - messaging-spaces vs messaging-bots (user says "send a message" — which skill?)
7. **Cross-skill coordination** — When a deployment plan spans multiple domains (e.g., create location →
   provision users → configure features → set up routing), does the agent correctly sequence skill loading?
   Are dependency chains documented?
8. **Compaction safety** — The agent has a COMPACTION RECOVERY section. Does it actually work? Would Claude
   be able to resume mid-execution after context compaction? Do the skills also have compaction recovery?
9. **Bulk operations gap** — The agent says "fall back to async Python for 50+ items." Is this actually
   feasible? Would Claude know how to write the async code from the reference docs alone?
10. **wxcadm integration** — The agent says wxcadm is for XSI/E911/CP-API. Does the call-control skill
    properly handle the user-token requirement? Is the wxcadm guidance consistent across agent + skills?
11. **Admin operations without skills** — The agent handles some domains inline via reference docs (org
    settings, hybrid, partner ops). Is this guidance clear? Would Claude know when to use a skill vs
    handle inline?
12. **Messaging domain** — The messaging-spaces and messaging-bots skills are new additions. Do they
    integrate cleanly with the Webex Calling-focused agent? Is the token type guidance clear (bot vs user
    vs admin)?

**Output format:**
```
## Agent Architecture Review

### Top Issues
1. [Most impactful finding]
2. [Second most impactful]
3. [Third]

### Full Findings
| # | File | Section | Issue | Suggested Fix | Severity |
|---|------|---------|-------|---------------|----------|
```

Severity levels: Critical (will cause failures), Medium (degrades quality), Low (improvement opportunity)

---

## Agent 2: CLI Integration Reviewer

**Persona:** QA engineer who verifies that documentation matches reality. Trusts nothing — runs actual
commands to check.

**Files to read:**
1. `.claude/agents/wxc-calling-builder.md` (the EXECUTE PHASE and Common wxcli Commands sections)
2. All 14 `.claude/skills/*/SKILL.md` files

For each file, extract every `wxcli` command referenced. Use subagents if needed to parallelize across
skill files.

**For every wxcli command referenced, verify it exists by running:**
```bash
wxcli <group> <command> --help
```

**Check:**
1. **Group names** — Does `wxcli <group>` exist? (e.g., `wxcli auto-attendant`, not `wxcli auto-attendants`)
2. **Command names** — Does `wxcli <group> <command>` exist? (e.g., `wxcli auto-attendant create`)
3. **Flag names** — Do the flags match? (e.g., `--location` vs `--location-id`, `--json-body` vs `--body`)
4. **Positional vs option arguments** — Are positional args shown as positional? Options shown with `--`?
5. **Output flags** — Is `--output json` / `-o json` correctly documented?

**Also check:**
- Does `wxcli whoami` work as documented?
- Do the README.md command examples match actual CLI syntax?
- Are there wxcli command groups that exist but aren't referenced in any skill?

**Output format:**
```
## CLI Integration Review

### Commands Verified: X/Y correct
### Commands with Issues: Z

| # | File | Line | Documented Command | Actual Command | Issue | Severity |
|---|------|------|-------------------|----------------|-------|----------|
```

---

## Agent 3: Reference Doc Quality Reviewer

**Persona:** Technical writer who reviews API documentation for accuracy and completeness.

**Files to spot-check (read ONE AT A TIME):**
1. `docs/reference/call-features-major.md` — AA, CQ, HG (most complex features)
2. `docs/reference/person-call-settings-handling.md` — call forwarding, DND, sim ring
3. `docs/reference/call-routing.md` — dial plans, trunks (complex URL patterns)
4. `docs/reference/wxcadm-xsi-realtime.md` — wxcadm guidance table
5. Pick 1-2 of the newer reference docs (messaging, admin, devices-platform) if they exist

**For each doc, evaluate:**

1. **Raw HTTP sections present** — Does every documented operation have a ### Raw HTTP subsection?
2. **URL correctness** — Are URLs using full `https://webexapis.com/v1/...` format? Are path segments
   correct? (e.g., `/premisePstn/dialPlans` not `/dialPlans`)
3. **Response keys** — Do GET list operations show the correct response key? (e.g.,
   `result.get("autoAttendants", [])` not `result.get("items", [])`)
4. **Required fields** — Do POST examples include all required body fields? Are the field names in
   correct camelCase?
5. **Gotchas documented** — Are known issues (AA menu requirements, CQ partial update, VG 7-field
   requirement) documented where relevant?
6. **SDK content preserved** — Are original SDK method signatures still present alongside the Raw HTTP
   sections?
7. **Markdown quality** — Are code blocks properly closed? Tables well-formed? Headers consistent?
8. **NEEDS VERIFICATION tags** — How many remain? Are any contradicted by information elsewhere in the
   same doc?
9. **Consistency with skills** — Do the reference docs and skills agree on command syntax, required fields,
   and gotchas? Or do they contradict each other?

**Output format:**
```
## Reference Doc Quality Review

### Docs Reviewed: N
### NEEDS VERIFICATION tags found: X

| # | File | Section | Issue | Severity |
|---|------|---------|-------|----------|
```

---

## Agent 4: Developer Experience Reviewer

**Persona:** A developer who has never seen this project before. They cloned the repo and are trying to
figure out what it is, how to install it, and how to use it.

**Files to read:**
1. `README.md`
2. `CLAUDE.md`
3. `pyproject.toml`
4. `.claude/agents/wxc-calling-builder.md` (just the FIRST-TIME SETUP and INTERVIEW sections)

**Also run these commands to test the install/discovery experience:**
```bash
wxcli --help
wxcli whoami --help
wxcli auto-attendant create --help
wxcli user-settings --help | head -30
wxcli cx-essentials --help
wxcli workspace-settings --help | head -20
```

**Evaluate:**

1. **README clarity** — Can someone who has never heard of Webex Calling understand what this tool does
   in 30 seconds? Is the install path clear? Are the usage examples copy-pasteable?
2. **Auth setup** — Is it obvious how to get a token and configure it? Does the README explain both
   `wxcli configure` (persistent) and `export WEBEX_ACCESS_TOKEN` (session)?
3. **Discoverability** — If I don't know what command to run, can I find it? Is the command group table
   in the README accurate? With 100 groups, is the table still useful or overwhelming?
4. **CLAUDE.md quality** — Does it give Claude enough context to be helpful? Is the file map accurate?
   Are the known issues section and generator rules clear? Does it reference all 14 skills?
5. **First-run experience** — What happens if I run `wxcli` with no token? Is the error message helpful?
   What if I run `wxcli auto-attendant create` with no args — is the help clear?
6. **Missing documentation** — What questions would a new user have that aren't answered? Common examples:
   "How do I find my location ID?", "What's the difference between auto-attendant and hunt-group?",
   "How do I undo something I just created?", "Which command group do I need for X?"
7. **Claude Code integration** — Is it clear how to use the playbook agent? The README should explain
   how to invoke it (`/agents` → select wxc-calling-builder). Are the 14 skills listed anywhere for
   direct invocation?
8. **Scaling concerns** — With 100 command groups and 14 skills, is the system still navigable? Or has
   it grown past the point where a new user can orient themselves?

**Output format:**
```
## Developer Experience Review

### First Impressions
[2-3 sentences on the overall experience]

### Findings
| # | File/Area | Issue | Suggested Fix | Severity |
|---|-----------|-------|---------------|----------|
```

---

## Synthesis Instructions

After all 4 agents complete, produce:

### 1. Executive Summary (5 sentences max)
What's the overall quality? What's the single biggest gap? How mature is this as a system?

### 2. Top 10 Fixes (prioritized)
| Priority | Issue | File(s) | Fix | Source |
|----------|-------|---------|-----|--------|
| 1 | ... | ... | ... | Agent N |

### 3. Full Findings Table
All findings from all 4 agents, deduplicated, sorted by severity:
| # | Severity | File | Issue | Fix | Reviewer |
|---|----------|------|-------|-----|----------|

### 4. Strengths Worth Preserving
What's working well that should NOT be changed? (Prevents future regressions)

### 5. Architecture Assessment
Is the 1 agent + 14 skills + ~39 reference docs structure the right architecture? Or should it be
restructured (e.g., fewer larger skills, more smaller skills, different dispatch model)?

### 6. Recommended Next Session
What should the next Claude Code session work on first, based on these findings?
