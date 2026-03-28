# Generate Reference Docs: Webex Contact Center

## What This Session Does

Write 3 reference docs for the Webex Contact Center API surface (48 CLI groups, 431 commands).
The OpenAPI spec and CLI commands already exist — this session writes the docs that ground
them in API details, data models, raw HTTP examples, and gotchas.

## Context (Zero-Context Briefing)

This project is a Webex Calling CLI (`wxcli`) with guided agent assistance. The CLI has
165 command groups generated from 7 OpenAPI specs. Every API surface has **reference docs**
(`docs/reference/*.md`) — deep technical references documenting CLI commands, raw HTTP
endpoints, data models, and gotchas. Contact Center was just added but has NO reference docs.

**IMPORTANT:** The Contact Center API is NOT in wxc_sdk or wxcadm. Do NOT include SDK
method signatures. Reference docs should document **wxcli CLI commands** (primary) and
**Raw HTTP endpoints** (from the OpenAPI spec) only.

## Key Files

### Patterns (READ THESE FIRST)

| What | Path | Why |
|------|------|-----|
| Reference doc pattern (features) | `docs/reference/call-features-major.md` | Best example (~1300 lines): Sources, TOC, API sections, data models, CLI examples, Raw HTTP, Gotchas, See Also |
| Reference doc pattern (simpler) | `docs/reference/messaging-spaces.md` | Simpler example (~700 lines) |
| Project instructions | `CLAUDE.md` | Full file map, CLI status, known issues |

### Source Material

| What | Path | Contents |
|------|------|----------|
| Contact Center spec | `specs/webex-contact-center.json` | ~300 paths, 50 tags (48 generated after merge), 431 commands |
| CLI commands | `src/wxcli/commands/cc_*.py` | 48 generated command files |
| Field overrides | `tools/field_overrides.yaml` | CLI name overrides and tag merges |

### CLI Groups (48 groups, organized by domain)

**Agent Management (62 ops):**
`cc-agents` (11), `cc-agent-greetings` (13), `cc-agent-summaries` (2), `cc-agent-wellbeing` (5), `cc-user-profiles` (17), `cc-users` (14)

**Queue & Routing (73 ops):**
`cc-queue` (23), `cc-queues` (1), `cc-entry-point` (10), `cc-dial-plan` (9), `cc-dial-number` (12), `cc-callbacks` (5), `cc-ewt` (1), `cc-overrides` (9)

**Campaign & Contacts (36 ops):**
`cc-campaign` (3), `cc-contact-list` (5), `cc-contact-number` (8), `cc-dnc` (3), `cc-outdial-ani` (16), `cc-captures` (1)

**Configuration (126 ops):**
`cc-site` (10), `cc-business-hour` (9), `cc-holiday-list` (9), `cc-aux-code` (11), `cc-work-types` (9), `cc-desktop-layout` (9), `cc-desktop-profile` (10), `cc-multimedia-profile` (10), `cc-global-vars` (10), `cc-skill` (10), `cc-skill-profile` (9), `cc-team` (10)

**Flows & Automation (26 ops):**
`cc-flow` (4), `cc-data-sources` (7), `cc-audio-files` (7), `cc-resource-collection` (8)

**AI & Analytics (56 ops):**
`cc-ai-assistant` (1), `cc-ai-feature` (3), `cc-auto-csat` (8), `cc-summaries` (3), `cc-journey` (41)

**Monitoring & Events (56 ops):**
`cc-call-monitoring` (7), `cc-realtime` (1), `cc-subscriptions` (12), `cc-tasks` (24), `cc-notification` (1), `cc-search` (1), `cc-address-book` (19)

## Guardrails

- **Read the pattern files first.** Do not write any docs until you've read at least one
  reference doc to understand the structure.
- **Extract endpoint details from the spec and CLI.** Use `wxcli <group> --help` and
  `wxcli <group> <command> --help` to verify command signatures. Use a python one-liner
  to extract paths/methods/summaries from the spec per tag.
- **Break large writes into sections.** The core doc is ~1200-1500 lines. Write in
  sections to avoid 502 errors.
- **Never hand-edit generated command files.**
- **Stage specific files only.** Never `git add -A` or `git add .`.
- **Self-review after each doc.**
- **Build an explicit checklist before writing each doc.**

## Step-by-Step Procedure

### Step 1: Read Patterns

1. Read `CLAUDE.md` — project structure, file map, known issues.
2. Read `docs/reference/call-features-major.md` — the reference doc pattern.
3. Read `tools/field_overrides.yaml` — CC-specific CLI name overrides and tag merges.

### Step 2: Extract Endpoint Details

For each doc, extract endpoints from the spec:

```bash
# Example: extract all endpoints for a given tag
python3.11 -c "
import json
with open('specs/webex-contact-center.json') as f:
    spec = json.load(f)
for path, methods in sorted(spec['paths'].items()):
    for method, op in methods.items():
        if isinstance(op, dict) and 'TAG_NAME' in op.get('tags', []):
            print(f'{method.upper():7s} {path:70s} {op.get(\"summary\", \"\")[:50]}')
"
```

Also run `wxcli cc-<group> --help` for each group to verify subcommand names.

### Step 3: Write the 3 Reference Docs

**Present the section outlines for all 3 docs to the user before writing. Wait for approval.**

#### 3a. `docs/reference/contact-center-core.md` (~1200-1500 lines)

Covers agent management, queues, and configuration (26 CLI groups, ~250 commands).

1. Sources (spec file, developer.webex.com Contact Center APIs)
2. Agents (`cc-agents`, 11 commands)
3. Agent Greetings (`cc-agent-greetings`, 13 commands)
4. Agent Summaries & Wellbeing (`cc-agent-summaries` 2, `cc-agent-wellbeing` 5)
5. Users & Profiles (`cc-users` 14, `cc-user-profiles` 17)
6. Queues (`cc-queue` 23, `cc-queues` 1)
7. Entry Points (`cc-entry-point`, 10 commands)
8. Teams (`cc-team`, 10 commands)
9. Skills & Skill Profiles (`cc-skill` 10, `cc-skill-profile` 9)
10. Multimedia Profiles (`cc-multimedia-profile`, 10 commands)
11. Desktop Layouts & Profiles (`cc-desktop-layout` 9, `cc-desktop-profile` 10)
12. Business Hours & Holidays (`cc-business-hour` 9, `cc-holiday-list` 9)
13. Aux Codes & Work Types (`cc-aux-code` 11, `cc-work-types` 9)
14. Sites (`cc-site`, 10 commands)
15. Global Variables (`cc-global-vars`, 10 commands)
16. Raw HTTP Endpoints
17. Gotchas
18. See Also

#### 3b. `docs/reference/contact-center-routing.md` (~800-1000 lines)

Covers routing, campaigns, flows, and media (15 CLI groups, ~100 commands).

1. Sources
2. Dial Plans (`cc-dial-plan`, 9 commands)
3. Dial Numbers (`cc-dial-number`, 12 commands)
4. Outdial ANI (`cc-outdial-ani`, 16 commands)
5. Contact Numbers (`cc-contact-number`, 8 commands)
6. Callbacks (`cc-callbacks`, 5 commands)
7. Estimated Wait Time (`cc-ewt`, 1 command)
8. Overrides (`cc-overrides`, 9 commands)
9. Campaigns (`cc-campaign`, 3 commands)
10. Contact Lists & DNC (`cc-contact-list` 5, `cc-dnc` 3)
11. Captures (`cc-captures`, 1 command)
12. Flows (`cc-flow`, 4 commands)
13. Audio Files (`cc-audio-files`, 7 commands)
14. Data Sources (`cc-data-sources`, 7 commands)
15. Resource Collections (`cc-resource-collection`, 8 commands)
16. Raw HTTP Endpoints
17. Gotchas
18. See Also

#### 3c. `docs/reference/contact-center-analytics.md` (~600-800 lines)

Covers AI, analytics, monitoring, and events (7 CLI groups, ~80 commands).

1. Sources
2. AI Assistant (`cc-ai-assistant`, 1 command)
3. AI Feature (`cc-ai-feature`, 3 commands)
4. Auto CSAT (`cc-auto-csat`, 8 commands)
5. Generated Summaries (`cc-summaries`, 3 commands)
6. Journey (`cc-journey`, 41 commands)
7. Call Monitoring (`cc-call-monitoring`, 7 commands)
8. Realtime (`cc-realtime`, 1 command)
9. Subscriptions (`cc-subscriptions`, 12 commands)
10. Tasks (`cc-tasks`, 24 commands)
11. Notifications (`cc-notification`, 1 command)
12. Search (`cc-search`, 1 command)
13. Address Book (`cc-address-book`, 19 commands)
14. Raw HTTP Endpoints
15. Gotchas
16. See Also

### Step 4: Update CLAUDE.md

Add the 3 new reference docs to the file map table:

```
| `docs/reference/contact-center-core.md` | CC agents, queues, entry points, teams, skills, desktop, configuration |
| `docs/reference/contact-center-routing.md` | CC dial plans, campaigns, flows, audio, contacts, outdial |
| `docs/reference/contact-center-analytics.md` | CC AI, journey, monitoring, subscriptions, tasks |
```

### Step 5: Commit

Stage specific files:
```
docs/reference/contact-center-core.md
docs/reference/contact-center-routing.md
docs/reference/contact-center-analytics.md
CLAUDE.md
```

Commit message: `docs(cc): reference docs for Contact Center API (3 docs, 48 CLI groups)`

## Success Criteria

- [ ] 3 reference docs exist and follow the pattern
- [ ] All 48 CC CLI groups are documented in at least one reference doc
- [ ] No wxc_sdk or wxcadm method signatures
- [ ] All wxcli command examples use actual CLI group and command names (verified via --help)
- [ ] Raw HTTP endpoint tables include method, path, and description
- [ ] CLAUDE.md file map updated
- [ ] Committed with specific file staging
