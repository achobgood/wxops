# Playbook Expansion: Messaging APIs

## Context

The wxcli CLI now covers the `webex-messaging.json` OpenAPI spec: 10 command groups, ~53 commands covering rooms/spaces, messages, teams, webhooks, memberships, room tabs, attachment actions, ECM, and hybrid data security. The playbook currently covers only Webex Calling. This session expands coverage to the Messaging domain.

**What exists today:**
- CLI commands are generated and registered (`wxcli <group> --help` works for all 10 groups)
- No reference docs exist for messaging APIs
- No skills exist for messaging workflows
- The builder agent doesn't know about messaging operations
- There is a `docs/later/` directory that was parked for post-calling expansion — check if it contains any messaging notes

**Your job:** Investigate the messaging CLI surface, map it to Webex App functionality and real-world automation use cases, then build the reference docs and skills to support it.

**Important framing:** Messaging is fundamentally different from Calling. Calling is admin-provisioned infrastructure (locations, queues, phones). Messaging is user-facing collaboration (spaces, messages, bots). The use cases, token types, and audience are different:

| Aspect | Calling | Messaging |
|--------|---------|-----------|
| Primary audience | IT admins | Developers, integrators, bot builders |
| Token type | Admin tokens (`spark-admin:`) | User tokens (`spark:`) or bot tokens |
| Control Hub equivalent | Calling settings | N/A — messaging is API-native, not a Control Hub config task |
| Primary use case | Provisioning infrastructure | Building integrations and automations |

---

## Phase 1: Discovery

### 1a. Map every messaging CLI group

Run `--help` on each:

```bash
wxcli rooms --help
wxcli messages --help
wxcli teams --help
wxcli memberships --help
wxcli team-memberships --help
wxcli webhooks --help
wxcli room-tabs --help
wxcli attachment-actions --help
wxcli ecm --help
wxcli hds --help
```

For each group, note: command count, read vs write operations, what Webex App feature it maps to.

### 1b. Understand the messaging model

The Webex messaging model has a specific hierarchy:

```
Organization
  └── Teams (optional grouping)
       └── Team Spaces (rooms belonging to a team)
  └── Spaces (rooms — the core unit)
       ├── Members (memberships)
       ├── Messages (text, files, cards/adaptive cards)
       ├── Tabs (embedded apps in the space)
       └── Webhooks (event subscriptions)
```

Map each CLI group to this model:

| Concept | CLI Group | What It Does |
|---------|-----------|-------------|
| Spaces | rooms | Create, list, update, delete spaces |
| Messages | messages | Send, list, get, delete messages in spaces |
| Space members | memberships | Add/remove people from spaces |
| Teams | teams | Create, list, update, delete teams |
| Team members | team-memberships | Add/remove people from teams |
| Webhooks | webhooks | Subscribe to events (messages, memberships, etc.) |
| Embedded apps | room-tabs | Add/remove tabs (apps) in spaces |
| Card interactions | attachment-actions | Get user responses to adaptive cards |
| Enterprise content | ecm | Enterprise Content Management integration |
| Hybrid data security | hds | Hybrid Data Security settings |

### 1c. Identify use cases

Messaging automation use cases are very different from calling. Investigate and document:

**Bot development:**
- Send notifications to a space (CI/CD alerts, monitoring, incident response)
- Create interactive workflows with adaptive cards (approval flows, forms, surveys)
- Build a help desk bot that routes requests
- Automated onboarding — add users to spaces, post welcome messages

**Space management:**
- Bulk create spaces for a project/event
- Archive old spaces
- Audit space membership (who's in what spaces)
- Manage team structures programmatically

**Webhook-driven automation:**
- React to new messages (chatbot pattern)
- Monitor membership changes (compliance, access control)
- Integration with external systems (Jira, ServiceNow, PagerDuty)

**Enterprise integration:**
- ECM (Enterprise Content Management) — connect Webex to content platforms
- HDS (Hybrid Data Security) — manage encryption key management
- Compliance — message archival, eDiscovery integration

**Cross-domain (Calling + Messaging):**
- Post call queue alerts to a Webex space when queue wait times exceed thresholds
- Send voicemail transcriptions to a space
- Automated incident response: detect calling issue → create space → add responders → post diagnostics

### 1d. Token types and scopes

Messaging APIs work with THREE token types (unlike calling which is almost always admin):

| Token Type | Use Case | Scopes |
|------------|----------|--------|
| **User token** | Act as a specific user | `spark:messages_read/write`, `spark:rooms_read/write`, `spark:memberships_read/write`, etc. |
| **Bot token** | Automated agent, always-on | `spark:messages_read/write`, `spark:rooms_read`, `spark:memberships_read` (bots have limited scopes) |
| **Admin token** | Org-wide operations | `spark-admin:messages_read`, compliance operations |

Document which operations work with which token types. This is critical — a bot can't do everything a user can, and an admin can't send messages as a user.

### 1e. Check docs/later/

```bash
ls docs/later/
```

Check if there are any parked messaging notes from earlier planning sessions.

---

## Phase 2: Reference Docs

Create reference docs for messaging. Since messaging is a cohesive domain, fewer docs are needed than calling:

| File | Covers |
|------|--------|
| `docs/reference/messaging-core.md` | Rooms/spaces, messages, memberships, teams — the core messaging model, CRUD operations, message formatting (markdown, files, adaptive cards), membership management |
| `docs/reference/messaging-automation.md` | Webhooks, room tabs, attachment actions — event-driven patterns, bot development patterns, adaptive card interactions, webhook best practices |
| `docs/reference/messaging-enterprise.md` | ECM, HDS, compliance — enterprise content management, hybrid data security, admin-level messaging operations |

Each doc should have:
- API surface overview
- CLI command mappings
- Token type requirements (user vs bot vs admin)
- Common patterns and recipes
- Gotchas
- Raw HTTP patterns for operations the CLI doesn't cover

**Important:** Messaging has rich content formatting (markdown, file attachments, adaptive cards). Document the message format options and how to use them from the CLI (likely via `--json-body` for complex payloads).

---

## Phase 3: Skills

Create skills for messaging workflows:

| Skill | Covers | Primary Use Case |
|-------|--------|------------------|
| `messaging-spaces` | Rooms, memberships, teams — space lifecycle management | "Manage Webex spaces and memberships programmatically" |
| `messaging-automation` | Messages, webhooks, attachment-actions, room-tabs — building integrations | "Build bots and automated workflows" |

**Why two skills, not one:** Space management (CRUD on rooms/teams/members) is admin work — similar to calling provisioning. Messaging automation (sending messages, handling webhooks, adaptive cards) is developer work — a different audience and workflow.

**Consider whether `messaging-automation` should include cross-domain recipes** that combine calling + messaging (e.g., "post alert to space when call queue overflows"). This would make the skill a bridge between the two domains.

Each skill should follow the same structure as calling skills (frontmatter, decision matrix, prerequisites, CLI commands, critical rules, verification).

---

## Phase 4: Agent Updates

This is the biggest architectural decision. The agent is currently called `wxc-calling-builder`. Options:

**Option A: Expand the existing agent**
Add messaging to the builder agent's interview phase and skill dispatch. The agent becomes a general Webex builder, not just calling.
- Pro: single entry point for everything
- Con: agent definition gets very large, calling context dilutes messaging context

**Option B: Create a separate messaging agent**
New agent at `.claude/agents/wxc-messaging-builder.md` focused on messaging/bot workflows.
- Pro: clean separation, focused context
- Con: users need to know which agent to invoke

**Option C: Rename and expand**
Rename `wxc-calling-builder` to `wxc-builder` and make it a general dispatcher that routes to domain-specific skills.
- Pro: single entry point, skills handle domain focus
- Con: breaking change for existing workflows

**Recommendation:** Option A with minimal changes. Add messaging as a recognized domain in the interview phase, add messaging skills to the dispatch table, but keep the agent's primary identity as the Webex builder. The skills do the heavy lifting — the agent just needs to know when to route to them.

### Updates needed:
1. Agent INTERVIEW PHASE: add messaging objectives to the recognition list
2. Agent SKILL DISPATCH: add messaging skills to the dispatch table
3. Agent frontmatter: add messaging skills to `skills:` list
4. CLAUDE.md: add new reference docs and skills to file map
5. CLAUDE.md: update project description to mention messaging coverage

---

## Constraints

- Do NOT modify any CLI code
- Do NOT modify existing calling reference docs or skills
- Do NOT rename the agent file (keep backward compatibility)
- Messaging APIs use different token types than calling — document this prominently
- Bot tokens have limited scopes — never suggest admin operations with a bot token
- Adaptive card payloads are complex JSON — show `--json-body` patterns
- Webhooks require a publicly accessible URL for the callback — document this prerequisite
- Mark unverified information with `<!-- NEEDS VERIFICATION -->`
- Check `docs/later/` for any parked messaging notes before starting fresh
