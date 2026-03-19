# Messaging Expansion Design Spec

**Date:** 2026-03-19
**Status:** Approved
**Scope:** Add messaging API coverage to the playbook — reference docs, skills, agent updates

---

## Summary

Expand the Webex playbook from calling-only to calling + messaging. The messaging CLI surface is 10 groups / 55 commands covering spaces, messages, teams, webhooks, bots, and enterprise content. This spec defines exactly what gets built, where every boundary is, and what changes in the existing agent.

**Deliverables:**
- 2 new reference docs (`messaging-spaces.md`, `messaging-bots.md`)
- 1 expanded reference doc (`webhooks-events.md` — add messaging resource events)
- 2 new skills (`messaging-spaces`, `messaging-bots`)
- Agent updates to `wxc-calling-builder.md` (interview, dispatch, doc loading, frontmatter)
- CLAUDE.md file map and description updates

**Constraints:**
- Do NOT modify any CLI code or generated command files
- Do NOT modify existing calling reference docs or skills (except `webhooks-events.md` expansion)
- Do NOT rename the agent file
- Mark unverified information with `<!-- NEEDS VERIFICATION -->`

---

## Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Doc count | 2 new (not 3) | ECM is space management, HDS is read-only monitoring — neither warrants its own doc |
| Skill count | 2 new | Space lifecycle (admin work) vs bot building (developer work) — different audiences, different tokens |
| Webhook boundary | Expand existing `webhooks-events.md` | Already has CRUD + all resource list. Messaging docs signpost, don't duplicate |
| Adaptive cards | Curated recipe catalog (5-8 patterns) + signpost to Microsoft | Covers 80% of use cases without duplicating the full schema |
| Agent approach | Expand existing agent (Option A) | Single entry point, skills do the heavy lifting |
| Skill naming | `messaging-bots` not `messaging-automation` | Clearer for target audience (developers building bots) |

---

## CLI Surface Inventory

### 10 Messaging CLI Groups (55 commands total)

| Group | Commands | Read/Write | Maps To |
|-------|----------|-----------|---------|
| `rooms` | list, create, show, update, delete, show-meeting-info | 3R / 3W | Spaces |
| `messages` | list, create, list-direct, show, update, delete | 3R / 3W | Messages |
| `teams` | list, create, show, update, delete | 2R / 3W | Teams |
| `memberships` | list, create, show, update, delete | 2R / 3W | Space members |
| `team-memberships` | list, create, show, update, delete | 2R / 3W | Team members |
| `webhooks` | list, create, show, update, delete | 2R / 3W | Event subscriptions |
| `room-tabs` | list, create, show, update, delete | 2R / 3W | Embedded apps |
| `attachment-actions` | create-an-attachment, show | 1R / 1W | Card interactions |
| `ecm` | list, create, show, update, delete | 2R / 3W | Enterprise content |
| `hds` | show, show-clusters, show-nodes, list, list-multi-tenant, list-network-test, list-availability | 7R / 0W | Hybrid data security |

### Known CLI Issue

`teams show` has a spurious `--description` query param from a Cisco OpenAPI spec bug. Harmless (optional, API ignores it). Can suppress via `field_overrides.yaml` later.

### Out of Scope

- `/people` and `/events` paths in `webex-messaging.json` — these are separate admin CLI groups
- Meetings API — separate spec, separate expansion

---

## Reference Doc 1: `docs/reference/messaging-spaces.md`

### Purpose

The "admin's guide" to messaging infrastructure. Covers the 40 commands an IT admin or space manager uses to create/manage spaces, teams, memberships, and enterprise content. Analogous to calling's provisioning + location settings docs.

### Token Type Matrix (top of doc)

This matrix appears first, before any API details. It's the most important thing for an inexperienced user to see.

| Operation | User Token | Bot Token | Admin Token |
|-----------|-----------|-----------|-------------|
| Space CRUD | Yes | Yes (bot must be member) | Yes |
| Send/list messages | Yes | Yes (bot must be member) | No (admin can list via compliance, not send) |
| Membership CRUD | Yes (if moderator or creator) | Limited (can't add self) | Yes |
| Team CRUD | Yes | No | Yes |
| Team membership CRUD | Yes | No | Yes |
| ECM folder linking | No | No | Yes (requires `spark-admin:` scopes) |
| HDS monitoring | No | No | Yes (requires `spark-admin:` scopes) |

### Section Structure

**Section 1: Messaging Model Overview**

```
Organization
  └── Teams (optional grouping)
       └── Team Spaces (rooms belonging to a team)
  └── Spaces (rooms — the core unit)
       ├── Members (memberships)
       ├── Messages (text, files, cards)
       └── Tabs (embedded apps)
```

- Spaces vs rooms: "room" is the API term, "space" is the Webex App term. They're the same thing.
- Space types: `direct` (1:1), `group` (multi-person)
- Team relationship: a team is a grouping of spaces. Creating a team auto-creates a "General" space.

**Section 2: Spaces (rooms CLI group — 6 commands)**

| Command | CLI | Method | What It Does |
|---------|-----|--------|-------------|
| List spaces | `wxcli rooms list` | GET /rooms | List spaces the caller belongs to |
| Create space | `wxcli rooms create --title "Name"` | POST /rooms | Create a new group space |
| Show space | `wxcli rooms show ROOM_ID` | GET /rooms/{roomId} | Get space details |
| Update space | `wxcli rooms update ROOM_ID --title "New Name"` | PUT /rooms/{roomId} | Rename, lock, set read-only |
| Delete space | `wxcli rooms delete ROOM_ID` | DELETE /rooms/{roomId} | Delete space and all content |
| Meeting info | `wxcli rooms show-meeting-info ROOM_ID` | GET /rooms/{roomId}/meetingInfo | Get SIP/meeting URI for space |

Key parameters:
- `--type` filter: `direct` or `group` (list only)
- `--team-id`: associate space with a team (create only)
- `--is-locked/--no-is-locked`: prevent non-moderators from adding members
- `--is-announcement-only/--no-is-announcement-only`: only moderators can post
- `--is-read-only/--no-is-read-only`: no one can post (archive pattern)
- `--sort-by`: `id`, `lastactivity`, `created` (list only)

Gotchas:
- Deleting a space is permanent — no recycle bin
- `list` only returns spaces the authenticated user/bot is a member of
- `show-meeting-info` returns the SIP URI and meeting link for the space — useful for bridging calling + messaging
- Direct spaces (1:1) cannot be deleted via API
- Space titles are optional for direct spaces (the API uses participant names)

**Section 3: Messages (messages CLI group — 6 commands)**

| Command | CLI | Method | What It Does |
|---------|-----|--------|-------------|
| List messages | `wxcli messages list --room-id ROOM_ID` | GET /messages | List messages in a space |
| Send message | `wxcli messages create --room-id ROOM_ID --text "Hello"` | POST /messages | Send a message |
| List direct | `wxcli messages list-direct --person-id PERSON_ID` | GET /messages/direct | List 1:1 messages with a person |
| Show message | `wxcli messages show MESSAGE_ID` | GET /messages/{messageId} | Get message details |
| Edit message | `wxcli messages update MESSAGE_ID --text "Updated"` | PUT /messages/{messageId} | Edit an existing message |
| Delete message | `wxcli messages delete MESSAGE_ID` | DELETE /messages/{messageId} | Delete a message |

Message format options (create/update):
- `--text`: plain text
- `--markdown`: markdown formatted (supports bold, italic, links, mentions, code blocks)
- `--files`: attach file by URL (up to 1 file per message via this param)
- `--to-person-id` or `--to-person-email`: send direct message (alternative to --room-id)
- `--parent-id`: reply to a specific message (threading)
- `--json-body`: full control — required for adaptive cards (see `messaging-bots.md`)

Gotchas:
- `--room-id` is required for list (you list messages IN a space, not globally)
- `--before` and `--before-message` filters for pagination (list)
- `--mentioned-people` filter: list only messages that mention specific people (or `me`)
- Bots can only see messages where they are @mentioned (unless in 1:1 spaces)
- File uploads via `--files` accept a URL, not a local file path — the URL must be publicly accessible or a Webex content URL
- Adaptive card payloads use `attachments` field in the JSON body — cannot be sent via `--text` or `--markdown`. See `messaging-bots.md` for card recipes.
- Edit only works on messages sent by the authenticated user/bot

**Section 4: Memberships (memberships CLI group — 5 commands)**

| Command | CLI | Method | What It Does |
|---------|-----|--------|-------------|
| List members | `wxcli memberships list --room-id ROOM_ID` | GET /memberships | List space members |
| Add member | `wxcli memberships create --room-id ROOM_ID --person-email user@example.com` | POST /memberships | Add person to space |
| Show membership | `wxcli memberships show MEMBERSHIP_ID` | GET /memberships/{membershipId} | Get membership details |
| Update membership | `wxcli memberships update MEMBERSHIP_ID --is-moderator` | PUT /memberships/{membershipId} | Change moderator status, hide space |
| Remove member | `wxcli memberships delete MEMBERSHIP_ID` | DELETE /memberships/{membershipId} | Remove person from space |

Key parameters:
- `--person-id` or `--person-email`: identify person (create)
- `--is-moderator/--no-is-moderator`: grant/revoke moderator role
- `--is-room-hidden/--no-is-room-hidden`: hide space from member's space list

Gotchas:
- Removing the last moderator from a locked space makes it unmodifiable — always ensure at least one moderator
- Bots cannot add themselves to spaces — they must be added by a user or via an integration
- `list` requires `--room-id` (list members of a space) or `--person-id` (list spaces a person is in)
- The membership ID is NOT the person ID — it's a separate identifier for the person-in-space relationship

**Section 5: Teams (teams + team-memberships CLI groups — 10 commands)**

| Command | CLI | Method |
|---------|-----|--------|
| List teams | `wxcli teams list` | GET /teams |
| Create team | `wxcli teams create --name "Team Name"` | POST /teams |
| Show team | `wxcli teams show TEAM_ID` | GET /teams/{teamId} |
| Update team | `wxcli teams update TEAM_ID --name "New Name"` | PUT /teams/{teamId} |
| Delete team | `wxcli teams delete TEAM_ID` | DELETE /teams/{teamId} |
| List team members | `wxcli team-memberships list --team-id TEAM_ID` | GET /team/memberships |
| Add team member | `wxcli team-memberships create --team-id TEAM_ID --person-email user@example.com` | POST /team/memberships |
| Show team membership | `wxcli team-memberships show MEMBERSHIP_ID` | GET /team/memberships/{membershipId} |
| Update team membership | `wxcli team-memberships update MEMBERSHIP_ID --is-moderator` | PUT /team/memberships/{membershipId} |
| Remove team member | `wxcli team-memberships delete MEMBERSHIP_ID` | DELETE /team/memberships/{membershipId} |

Gotchas:
- Deleting a team deletes ALL team spaces and their content — destructive
- Adding a member to a team auto-adds them to all team spaces
- Team membership is separate from space membership — a user can be removed from individual team spaces while remaining a team member
- Bot tokens cannot create or manage teams

**Section 6: ECM — Enterprise Content Management (ecm CLI group — 5 commands)**

| Command | CLI | Method |
|---------|-----|--------|
| List linked folders | `wxcli ecm list` | GET /room/linkedFolders |
| Link folder | `wxcli ecm create --room-id ROOM_ID --content-url URL` | POST /room/linkedFolders |
| Show linked folder | `wxcli ecm show FOLDER_ID` | GET /room/linkedFolders/{id} |
| Update linked folder | `wxcli ecm update FOLDER_ID` | PUT /room/linkedFolders/{id} |
| Unlink folder | `wxcli ecm delete FOLDER_ID` | DELETE /room/linkedFolders/{id} |

<!-- NEEDS VERIFICATION: Exact required fields for ECM create (content URL format, provider type). Check developer.webex.com ECM API docs. -->

- Requires admin token with `spark-admin:` scopes
- Links SharePoint/OneDrive/Box folders to Webex spaces
- `--default-folder` flag sets the folder as the default for the space

**Section 7: HDS — Hybrid Data Security (hds CLI group — 8 commands, read-only)**

| Command | CLI | What It Shows |
|---------|-----|--------------|
| Org status | `wxcli hds show` | HDS organization enrollment status |
| Cluster details | `wxcli hds show-clusters` | HDS cluster configuration |
| Node details | `wxcli hds show-nodes` | Individual node status |
| Database details | `wxcli hds list` | HDS database configuration |
| Multi-tenant info | `wxcli hds list-multi-tenant` | Multi-tenant HDS org details |
| Network tests | `wxcli hds list-network-test` | Node network test results |
| Availability | `wxcli hds list-availability` | Cluster availability metrics |

- All read-only — no write operations
- Requires admin token
- HDS manages encryption keys on-premises for compliance — this section is monitoring only
- `--trigger-type` filter on network tests: `OnDemand`, `Periodic`, `All`

**Section 8: Common Patterns**

Recipes for common multi-step workflows:
- Bulk create spaces from a list
- Audit all space memberships in the org
- Archive old spaces (set read-only + post archival notice)
- Set up a project team (create team → create spaces → add members)
- Export messages from a space (paginated list)

**Section 9: See Also**

- `messaging-bots.md` — Bot development, adaptive cards, interactive workflows
- `webhooks-events.md` — Webhook CRUD and event payloads (messaging + telephony)
- `authentication.md` — Token types, scopes, OAuth flows

---

## Reference Doc 2: `docs/reference/messaging-bots.md`

### Purpose

The "developer's guide" to building bots and integrations. Covers the 7 commands a bot developer uses plus the adaptive card recipe catalog and cross-domain patterns. Analogous to calling's `call-control.md` — it's about runtime behavior, not infrastructure.

### Section Structure

**Section 1: Bot Fundamentals**

What a Webex bot is and isn't:
- A bot is a special Webex user with its own token — always on, no human login
- Created at developer.webex.com → My Apps → Create a Bot
- Bot token scopes are fixed: `spark:messages_read`, `spark:messages_write`, `spark:rooms_read`, `spark:memberships_read`, `spark:kms`
- Cannot do: create teams, manage team memberships, add self to spaces, access admin APIs, use `spark-admin:` scopes
- Can do: send/receive messages in spaces it belongs to, create 1:1 conversations, receive webhooks

Bot vs user vs admin token comparison:

| Capability | Bot Token | User Token | Admin Token |
|-----------|-----------|-----------|-------------|
| Send messages | Yes (spaces it's in) | Yes (spaces they're in) | No |
| Create spaces | Yes | Yes | Yes |
| Join spaces | No (must be added) | Yes (if invited or discoverable) | N/A |
| Create teams | No | Yes | Yes |
| Manage memberships | No (except removing self) | Yes (if moderator) | Yes |
| See all messages | Only @mentions + 1:1 | All in their spaces | Compliance API only |
| Admin operations | No | No | Yes |

How to configure a bot token:
```bash
wxcli configure
# Enter the bot's access token when prompted
wxcli whoami  # Verify — should show the bot's display name
```

**Section 2: Sending Messages**

Three tiers of message complexity:

| Tier | Format | CLI Approach |
|------|--------|-------------|
| Plain text | `--text "Hello"` | Direct CLI option |
| Markdown | `--markdown "**Bold** and [link](url)"` | Direct CLI option |
| Adaptive card | `--json-body '{"roomId": "...", "attachments": [...]}'` | JSON body required |

Plain text example:
```bash
wxcli messages create --room-id ROOM_ID --text "Build completed successfully"
```

Markdown example:
```bash
wxcli messages create --room-id ROOM_ID --markdown "## Build Status\n**Project:** myapp\n**Result:** ✅ Passed"
```

Adaptive card example (signpost to recipe catalog below):
```bash
wxcli messages create --json-body '{
  "roomId": "ROOM_ID",
  "text": "Fallback text for clients that cannot render cards",
  "attachments": [{
    "contentType": "application/vnd.microsoft.card.adaptive",
    "content": { ... card payload ... }
  }]
}'
```

Critical: The `text` field is required even when sending a card — it's the fallback for clients that can't render adaptive cards (email notifications, older Webex versions).

**Section 3: Adaptive Card Recipe Catalog**

Each recipe includes:
1. Screenshot description (what it looks like)
2. Complete JSON payload (copy-paste ready)
3. `wxcli messages create --json-body` command
4. How to handle the `Action.Submit` response

**Recipe 1: Notification Card**
- Use case: CI/CD alerts, monitoring alerts, status notifications
- Elements: TextBlock (title), FactSet (key-value details), Action.OpenUrl (link to dashboard)
- No user input — informational only

**Recipe 2: Approval Flow**
- Use case: Change approvals, expense approvals, access requests
- Elements: TextBlock (title + description), FactSet (request details), Action.Submit × 2 (Approve / Reject)
- Requires webhook on `attachmentActions` resource to capture response
- Response handling: `wxcli attachment-actions show ACTION_ID` to get user's choice

**Recipe 3: Form / Survey**
- Use case: Feedback collection, onboarding forms, incident reports
- Elements: Input.Text (free text), Input.ChoiceSet (dropdown/radio), Input.Date, Action.Submit
- Shows how to extract input values from the attachment action response

**Recipe 4: Status Dashboard**
- Use case: System status, deployment progress, queue metrics
- Elements: ColumnSet (multi-column layout), TextBlock with color/weight styling, Image (optional status icons)
- Demonstrates column layout and conditional text styling

**Recipe 5: Incident Alert**
- Use case: PagerDuty-style alerts, on-call notifications
- Elements: TextBlock with `attention` style (red), FactSet (incident details), Action.Submit (Acknowledge), Action.OpenUrl (Runbook)
- Cross-domain example: triggered by calling queue overflow

**Recipe 6: Dropdown Menu**
- Use case: Configuration selection, routing choice, preference setting
- Elements: Input.ChoiceSet (dropdown mode), Action.Submit
- Simplest interactive pattern — good starter template

**Section 4: Webex Adaptive Cards — Supported Features and Gaps**

Webex supports Adaptive Cards schema version 1.3. Known gaps/differences from the full schema:

<!-- NEEDS VERIFICATION: Confirm exact Webex Adaptive Cards support level and gaps against developer.webex.com/docs/api/guides/cards -->

Supported elements: TextBlock, Image, FactSet, ColumnSet, Column, Container, ImageSet, ActionSet, RichTextBlock
Supported inputs: Input.Text, Input.Number, Input.Date, Input.Time, Input.Toggle, Input.ChoiceSet
Supported actions: Action.Submit, Action.OpenUrl, Action.ShowCard, Action.ToggleVisibility

Signpost: Full Adaptive Cards schema reference → https://adaptivecards.io/explorer/
Signpost: Webex cards guide → developer.webex.com/docs/api/guides/cards

Gotchas:
- Maximum card payload size: 4KB (cards larger than this silently fail to render)
- `Action.Execute` (Adaptive Cards 1.4+) is NOT supported — use `Action.Submit`
- `Media` element is NOT supported — use Image instead or link to media via Action.OpenUrl
- Card rendering varies between Webex desktop, mobile, and web clients
- `fallback` property on elements is supported but behavior is inconsistent across clients

**Section 5: Attachment Actions (attachment-actions CLI group — 2 commands)**

| Command | CLI | Method | What It Does |
|---------|-----|--------|-------------|
| Create action | `wxcli attachment-actions create-an-attachment --type submit --message-id MSG_ID --json-body '{"inputs": {...}}'` | POST /attachment/actions | Submit a card response (programmatic) |
| Show action | `wxcli attachment-actions show ACTION_ID` | GET /attachment/actions/{id} | Get user's card response |

The flow:
1. Bot sends message with adaptive card (via `wxcli messages create --json-body`)
2. User clicks `Action.Submit` button in the card
3. Webex fires webhook with resource=`attachmentActions`, event=`created`
4. Bot calls `wxcli attachment-actions show ACTION_ID` to get the user's input values
5. Bot processes the response and sends a follow-up message

Response object fields:
- `id`: the attachment action ID
- `type`: always `submit`
- `messageId`: the message that contained the card
- `inputs`: object with key-value pairs from the card's input fields
- `personId`: who submitted the response
- `roomId`: which space
- `created`: timestamp

**Section 6: Room Tabs (room-tabs CLI group — 5 commands)**

| Command | CLI | Method | What It Does |
|---------|-----|--------|-------------|
| List tabs | `wxcli room-tabs list --room-id ROOM_ID` | GET /room/tabs | List tabs in a space |
| Create tab | `wxcli room-tabs create --room-id ROOM_ID --content-url URL --display-name "Name"` | POST /room/tabs | Add a tab to a space |
| Show tab | `wxcli room-tabs show TAB_ID` | GET /room/tabs/{id} | Get tab details |
| Update tab | `wxcli room-tabs update TAB_ID` | PUT /room/tabs/{id} | Update tab URL or name |
| Delete tab | `wxcli room-tabs delete TAB_ID` | DELETE /room/tabs/{id} | Remove tab from space |

<!-- NEEDS VERIFICATION: Confirm exact required fields for room tab creation and whether contentUrl must be HTTPS -->

- Tabs embed web content (dashboards, wikis, tools) directly in a Webex space
- `--content-url`: the URL to embed (must be HTTPS)
- `--display-name`: shown in the tab bar

**Section 7: Cross-Domain Recipes (Calling + Messaging)**

Patterns that bridge the two domains:

**Recipe A: Queue Alert → Space Notification**
1. Create webhook for `telephony_calls` with filter (see `webhooks-events.md`)
2. In webhook handler, detect queue wait time threshold
3. Send card to ops space: `wxcli messages create --json-body` with incident alert recipe

**Recipe B: Voicemail → Space Notification**
1. Create webhook for `telephony_mwi` resource
2. On new voicemail event, send notification card to user's 1:1 space with bot
3. Card includes caller info, timestamp, Action.OpenUrl to voicemail portal

**Recipe C: Automated Incident Response**
1. Detect calling issue (via CDR analysis or webhook pattern)
2. Create a new space: `wxcli rooms create --title "Incident-2026-03-19"`
3. Add responders: `wxcli memberships create --room-id ROOM_ID --person-email oncall@example.com`
4. Post diagnostics: `wxcli messages create --room-id ROOM_ID --json-body` with status dashboard card

**Section 8: Webhook Signpost**

> **Webhook CRUD and event setup:** See [`webhooks-events.md`](webhooks-events.md).
> For messaging bots, the key webhook resources are:
> - `messages` — fires when a message is posted (how bots "hear" messages)
> - `attachmentActions` — fires when a user submits an adaptive card (how bots get card responses)
> - `memberships` — fires when someone joins/leaves a space
> - `rooms` — fires when a space is created/updated/deleted
>
> Create a webhook: `wxcli webhooks create --name "Bot Listener" --target-url https://your-bot.com/webhook --resource messages --event created`

**Section 9: See Also**

- `messaging-spaces.md` — Space/team/membership CRUD, ECM, HDS
- `webhooks-events.md` — Webhook CRUD, event payloads, HMAC verification
- `authentication.md` — Token types, scopes, OAuth flows
- Adaptive Cards Designer: https://adaptivecards.io/designer/
- Webex Cards Guide: developer.webex.com/docs/api/guides/cards

---

## Reference Doc 3: Expand `docs/reference/webhooks-events.md`

### What Exists Today

The doc currently has 9 sections covering webhook CRUD, data model, ALL webhook resources (section 3 already lists messaging resources), telephony call events (sections 4-9), filtering, setup, SDK class hierarchy, HMAC security, and gotchas.

### What to Add

**Do NOT modify sections 1-3 or 7-10.** They are already universal (CRUD, data model, resource list, security, gotchas).

**Add Section 4b: Messaging Resource Events** (after existing section 4 "Telephony Call Events")

For each messaging webhook resource, document:
- Event types (created, updated, deleted)
- Payload structure (the `data` object)
- Key data fields
- Filter options

Resources to document:

| Resource | Events | Key Data Fields |
|----------|--------|----------------|
| `messages` | created, deleted | `id`, `roomId`, `roomType`, `personId`, `personEmail`, `text` (not included for bots — must call GET /messages/{id}), `files`, `created` |
| `memberships` | created, updated, deleted | `id`, `roomId`, `personId`, `personEmail`, `isModerator`, `isMonitor`, `created` |
| `rooms` | created, updated | `id`, `title`, `type`, `isLocked`, `creatorId`, `created`, `lastActivity` |
| `attachmentActions` | created | `id`, `type`, `messageId`, `inputs`, `personId`, `roomId`, `created` |

<!-- NEEDS VERIFICATION: Confirm exact data fields in webhook payloads for messaging resources. The above is based on the Webex API documentation patterns. -->

Critical gotcha for `messages` resource webhooks:
- The webhook payload does NOT include the message text for bots (security measure)
- The bot must call `GET /messages/{messageId}` to retrieve the actual message content
- This is the standard bot pattern: webhook fires → bot calls messages API → bot processes text

**Add to Section 5: Messaging Filters**

| Resource | Filter | Example |
|----------|--------|---------|
| `messages` | `roomId` | Only messages in a specific space |
| `messages` | `personId` | Only messages from a specific person |
| `messages` | `mentionedPeople` | Only messages that @mention someone |
| `memberships` | `roomId` | Only membership changes in a specific space |
| `memberships` | `personId` | Only membership changes for a specific person |

<!-- NEEDS VERIFICATION: Confirm exact filter field names for messaging webhook resources -->

**Add Section 6b: Bot Webhook Pattern** (after existing section 6 "Webhook Setup")

The standard bot interaction loop:
1. Bot creates webhook for `messages` resource, event `created`
2. User sends message mentioning @bot in a space
3. Webhook fires → bot receives POST with message metadata (no text)
4. Bot calls `wxcli messages show MESSAGE_ID` to get the message text
5. Bot processes the text and sends a response: `wxcli messages create --room-id ROOM_ID --text "Response"`

For card interactions, add a second webhook:
1. Bot creates webhook for `attachmentActions` resource, event `created`
2. User clicks Action.Submit on a card
3. Webhook fires → bot receives POST with action metadata
4. Bot calls `wxcli attachment-actions show ACTION_ID` to get input values
5. Bot processes inputs and responds

---

## Skill 1: `.claude/skills/messaging-spaces/SKILL.md`

### Frontmatter

```yaml
name: messaging-spaces
description: >
  Manage Webex spaces, teams, memberships, messages, and enterprise content (ECM/HDS)
  using wxcli CLI commands. Guides the user from prerequisites through execution and verification.
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [operation-type]
```

### Section Structure (mirrors configure-features skill)

**Section 1: Load References**
- `docs/reference/messaging-spaces.md`
- `docs/reference/authentication.md`

**Section 2: Verify Auth Token**
- Run `wxcli whoami`
- Detect token type from response (bot tokens show bot display name, admin tokens show admin user)
- Warn if bot token for admin-only operations (ECM, HDS, teams)
- Required scopes vary by operation:
  - Spaces/messages: `spark:rooms_read/write`, `spark:messages_read/write`
  - Memberships: `spark:memberships_read/write`
  - Teams: `spark:teams_read/write`, `spark:team_memberships_read/write`
  - ECM: `spark-admin:room_linkedFolders_read/write`
  - HDS: `spark-admin:hds_read`

**Section 3: Decision Matrix**

| User Wants To | Operation Type | Prerequisites |
|--------------|---------------|---------------|
| Create/manage spaces | Space lifecycle | User or admin token |
| Send/manage messages | Message management | User or bot token + space membership |
| Add/remove space members | Membership management | User token (moderator) or admin token |
| Create/manage teams | Team management | User or admin token (NOT bot) |
| Link content folders | ECM setup | Admin token |
| Check HDS status | HDS monitoring | Admin token |

**Section 4: Prerequisites per Operation**

| Operation | Check | CLI Command |
|-----------|-------|-------------|
| Messages | Space exists | `wxcli rooms show ROOM_ID` |
| Memberships | Space exists | `wxcli rooms show ROOM_ID` |
| Team memberships | Team exists | `wxcli teams show TEAM_ID` |
| ECM | Space exists + admin token | `wxcli rooms show ROOM_ID` + `wxcli whoami` |

**Section 5: CLI Command Catalog**

Full command reference organized by operation type, with example commands for each. Includes `--json-body` patterns for complex operations (e.g., creating a space with specific settings).

**Section 6: Deployment Plan Template**

```
DEPLOYMENT PLAN
Operation: [type]
Target: [space name / team name / org-wide]

Resources:
- Spaces to create: [list]
- Members to add: [list with emails]
- Teams to create: [list]

Prerequisites verified: [✓ checkmarks]
Commands to execute: [wxcli commands in order]

Proceed? (yes/no)
```

**Section 7: Execute + Verify**

Run commands in plan order. Read back each resource after creation:
- `wxcli rooms show ROOM_ID --output json`
- `wxcli memberships list --room-id ROOM_ID --output json`
- `wxcli teams show TEAM_ID --output json`

**Section 8: Report Results**

```
OPERATION COMPLETE
Type: [operation type]
Resources created/modified: [count]
- Space: [name] (ID: [id])
- Members added: [count]

Next steps: [context-specific follow-up]
```

**Section 9: Critical Rules**

1. Always verify token type before executing — bot tokens can't do admin ops
2. Always show deployment plan and wait for approval before executing
3. Membership operations require valid person IDs or emails
4. Deleting a space or team is permanent — confirm with user
5. Bot tokens cannot create teams or manage team memberships
6. ECM and HDS require admin tokens with `spark-admin:` scopes
7. Space `list` only returns spaces the authenticated user is a member of — for org-wide audit, need admin compliance API
8. Direct (1:1) spaces cannot be deleted or renamed
9. When adding members in bulk, add sequentially (not parallel) to avoid rate limiting
10. Always check if space/team already exists before creating (idempotency)

**Section 10: Context Compaction Recovery**

1. Read deployment plan from `docs/plans/`
2. Check what's already created (list spaces, list memberships)
3. Resume from first incomplete step

---

## Skill 2: `.claude/skills/messaging-bots/SKILL.md`

### Frontmatter

```yaml
name: messaging-bots
description: >
  Build Webex bots and automated workflows: send notifications, create interactive
  adaptive card flows, set up webhooks, embed room tabs, and bridge calling + messaging.
  Guides from bot setup through card recipe selection, webhook configuration, and verification.
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [bot-task-type]
```

### Section Structure

**Section 1: Load References**
- `docs/reference/messaging-bots.md`
- `docs/reference/webhooks-events.md`
- `docs/reference/authentication.md`

**Section 2: Verify Auth Token**
- Run `wxcli whoami`
- Detect if bot token (bot display name in response) vs user token vs admin token
- For bot operations: bot token preferred, user token works for testing
- Warn: admin tokens cannot send messages
- Bot token scopes: `spark:messages_read/write`, `spark:rooms_read`, `spark:memberships_read`, `spark:kms`

**Section 3: Decision Matrix**

| User Wants To | Task Type | Prerequisites |
|--------------|-----------|---------------|
| Send notifications to a space | Send notification | Bot/user token + bot is member of target space |
| Build interactive card flow | Card interaction | Bot token + webhook URL + target space |
| Subscribe to events | Webhook setup | Bot/user token + publicly accessible webhook URL |
| Embed an app in a space | Room tab | User token (moderator) + content URL |
| Bridge calling events to messaging | Cross-domain | Bot token + calling webhook + target space |

**Section 4: Bot Setup Prerequisites**

| Check | How | What to Do If Missing |
|-------|-----|----------------------|
| Bot token configured | `wxcli whoami` | `wxcli configure` with bot access token |
| Bot is member of target space | `wxcli memberships list --room-id ROOM_ID` (look for bot's person ID) | Have a user add the bot: `wxcli memberships create --room-id ROOM_ID --person-email bot@webex.bot` |
| Webhook callback URL available | Ask user | Options: ngrok for dev, cloud function for prod, any HTTPS endpoint |
| Target space exists | `wxcli rooms show ROOM_ID` | Create one: `wxcli rooms create --title "Bot Space"` then add bot |

**Section 5: Card Recipe Selection**

Guide user to the right recipe based on their use case:

| Use Case | Recipe | Key Elements |
|----------|--------|-------------|
| "Alert when X happens" | Notification | TextBlock + FactSet + Action.OpenUrl |
| "Get approval for X" | Approval Flow | TextBlock + FactSet + Action.Submit × 2 |
| "Collect information from users" | Form / Survey | Input.Text + Input.ChoiceSet + Action.Submit |
| "Show status of X" | Status Dashboard | ColumnSet + styled TextBlocks |
| "Alert on-call engineer" | Incident Alert | Attention TextBlock + FactSet + Action.Submit + Action.OpenUrl |
| "Let user pick from options" | Dropdown Menu | Input.ChoiceSet + Action.Submit |

After selection:
1. Load the recipe JSON from `messaging-bots.md`
2. Customize placeholder values (room ID, field names, button labels)
3. Show the complete `wxcli messages create --json-body` command
4. If recipe uses Action.Submit, also set up the webhook + attachment action handling

**Section 6: Webhook Setup for Bots**

For interactive bots (not just notification senders):

Step 1 — Create webhook for messages (so bot can "hear"):
```bash
wxcli webhooks create --name "Bot Messages" --target-url https://your-bot.com/webhook --resource messages --event created
```

Step 2 — Create webhook for card responses (if using adaptive cards):
```bash
wxcli webhooks create --name "Bot Card Responses" --target-url https://your-bot.com/webhook --resource attachmentActions --event created
```

Step 3 — Verify webhooks are active:
```bash
wxcli webhooks list --output json
```

Signpost to `webhooks-events.md` for: HMAC verification, webhook data model, auto-deactivation handling, advanced filtering.

**Section 7: Cross-Domain Dispatch**

When the user's objective involves both calling and messaging:
1. Identify the calling component (e.g., "monitor call queue overflow")
2. Identify the messaging component (e.g., "post alert to ops space")
3. Load the appropriate calling skill for the calling component
4. Use this skill for the messaging component
5. The cross-domain recipes in `messaging-bots.md` Section 7 provide the glue patterns

**Section 8: Execute + Verify**

For notification bots:
1. Send test message: `wxcli messages create --room-id ROOM_ID --text "Test notification"`
2. Verify in Webex App that message appears
3. Send test card: `wxcli messages create --json-body '...'`
4. Verify card renders correctly

For interactive bots:
1. Send card, click button in Webex App
2. Check webhook received the action (user must verify their webhook endpoint)
3. `wxcli attachment-actions show ACTION_ID` to verify input capture

**Section 9: Critical Rules**

1. Always verify bot is a member of the target space before sending messages
2. Bot tokens cannot add themselves to spaces — a user must add the bot
3. Adaptive cards REQUIRE `text` field as fallback — never send a card without it
4. Card payloads must be under 4KB — large cards silently fail to render
5. `Action.Execute` (Cards 1.4+) is NOT supported — use `Action.Submit`
6. Webhook `targetUrl` must be publicly accessible HTTPS — no HTTP, no localhost
7. Bot webhook for `messages` does NOT include message text — must call `wxcli messages show MESSAGE_ID`
8. Webhooks auto-deactivate after repeated delivery failures — monitor status
9. For cross-domain: calling webhooks need `spark:calls_read` scope (separate from bot's messaging scopes — may need a different token)
10. Room tabs require moderator-level user token, not bot token
11. When sending multiple messages rapidly, add `sleep 1` between sends to avoid rate limiting

**Section 10: Context Compaction Recovery**

1. Read deployment plan from `docs/plans/`
2. Check what webhooks exist: `wxcli webhooks list`
3. Check what messages were sent (if tracking IDs)
4. Resume from first incomplete step

---

## Agent Updates: `wxc-calling-builder.md`

### Exact Changes Required

The agent file is 554 lines. All changes are additive — no existing content is modified or removed.

### Change 1: Frontmatter (line ~7)

**Current:**
```
skills: provision-calling, configure-features, manage-call-settings, configure-routing, manage-devices, call-control, reporting, wxc-calling-debug
```

**New:**
```
skills: provision-calling, configure-features, manage-call-settings, configure-routing, manage-devices, call-control, reporting, wxc-calling-debug, messaging-spaces, messaging-bots
```

### Change 2: Interview Phase — Question 1 Objective Recognition (line ~95)

**Current domain detection list:**
provisioning, features, settings, routing, devices, control, monitoring, bulk

**Add to the recognition list:**

| New Domain Keyword | Detection Phrases | Maps To |
|-------------------|-------------------|---------|
| messaging-spaces | "create a space", "manage spaces", "set up a team", "add members", "space membership", "ECM", "HDS", "enterprise content" | `messaging-spaces` skill |
| messaging-bots | "build a bot", "send notifications", "adaptive card", "interactive card", "bot integration", "alert to space", "webhook for messages", "room tab" | `messaging-bots` skill |
| cross-domain | "calling + messaging", "queue alert to space", "incident response space", "voicemail notification" | `messaging-bots` skill (with calling skill co-dispatch) |

### Change 3: Interview Phase — Question 2 Scope (line ~108)

**Add messaging-specific scope probes** (only triggered when domain is messaging):

Current calling scope: org-wide / location(s) / user(s)

Messaging scope equivalents:
- Specific space(s): "Which space? Do you have the room ID?"
- Team: "Which team? Creating new or modifying existing?"
- Bot: "Is this for a bot or a user integration?"
- Org-wide: "Org-wide space audit? This needs admin token + compliance API"

Additional messaging probes:
- "Are you building a bot or managing spaces as an admin?"
- "Do you have a webhook callback URL?" (needed for interactive bots)
- "Will you need adaptive cards?" (triggers card recipe selection in bot skill)

### Change 4: Interview Phase — Question 5 Special Requirements (line ~145)

**Add messaging-specific probes** (only triggered when domain is messaging):

- Token type: "Bot token, user token, or admin token?" (explain differences if user is unsure)
- Card interactions: "Will users interact with cards (approve/reject/fill forms)?" → triggers card recipe + webhook setup
- Cross-domain: "Does this involve both calling and messaging?" → triggers co-dispatch

### Change 5: Skill Dispatch Table (line ~330)

**Add 2 rows to existing 8-row table:**

| Task Domain | Skill File | What It Provides |
|-------------|-----------|------------------|
| Spaces, teams, memberships, messages, ECM, HDS | `.claude/skills/messaging-spaces/SKILL.md` | Space lifecycle, team structure, membership management, token type requirements |
| Bot development, notifications, adaptive cards, room tabs, cross-domain integrations | `.claude/skills/messaging-bots/SKILL.md` | Bot patterns, card recipe catalog, webhook setup, cross-domain recipes |

### Change 6: Reference Doc Loading (line ~458)

**Add 2 domain entries to existing loading map:**

| Domain | Docs to Load |
|--------|-------------|
| Messaging Spaces (spaces, teams, memberships, messages, ECM, HDS) | `docs/reference/messaging-spaces.md`, `docs/reference/authentication.md` |
| Messaging Bots (bots, notifications, cards, integrations, cross-domain) | `docs/reference/messaging-bots.md`, `docs/reference/webhooks-events.md`, `docs/reference/authentication.md` |

### Change 7: First-Time Setup — Reference Docs Check (line ~75)

Add messaging reference docs to the existence check alongside calling docs.

---

## CLAUDE.md Updates

### File Map — Skills Table

Add 2 rows:

| Path | Purpose |
|------|---------|
| `.claude/skills/messaging-spaces/` | Skill: manage spaces, teams, memberships, ECM, HDS |
| `.claude/skills/messaging-bots/` | Skill: build bots, adaptive cards, webhooks, cross-domain integrations |

### File Map — Reference Docs Table

Add 2 rows:

| Path | Purpose |
|------|---------|
| `docs/reference/messaging-spaces.md` | Spaces, messages, memberships, teams, ECM, HDS |
| `docs/reference/messaging-bots.md` | Bot development, adaptive cards, room tabs, cross-domain recipes |

### Project Description (line 1)

Change from:
> Build and configure Webex Calling, admin, device, and messaging APIs programmatically

(Already mentions messaging — verify this is accurate after expansion. May need to update the detail text to explicitly call out messaging reference docs and skills.)

### CLI Status

Update total command group count to reflect messaging groups are now documented (not just generated).

---

## Scope Boundaries — The Sharp Edges

These are the exact rules for what goes where when content could live in multiple places.

| Content | Lives In | NOT In | Rule |
|---------|----------|--------|------|
| Webhook CRUD (create, list, update, delete) | `webhooks-events.md` | messaging docs | One source of truth for webhook management |
| Webhook resource/event values for messaging | `webhooks-events.md` section 4b | `messaging-bots.md` | Bots doc has a signpost only |
| Webhook resource/event values for telephony | `webhooks-events.md` section 4 | `call-control.md` | Unchanged |
| Adaptive card JSON schema | Signpost to adaptivecards.io | Any local doc | We don't own the schema |
| Adaptive card recipes (complete payloads) | `messaging-bots.md` section 3 | `messaging-spaces.md` | Cards are bot territory |
| Webex card rendering gaps | `messaging-bots.md` section 4 | `webhooks-events.md` | Card-specific, not webhook-specific |
| "Send a plain text message" | `messaging-spaces.md` section 3 | `messaging-bots.md` | Simple CRUD is spaces territory |
| "Send an adaptive card message" | `messaging-bots.md` section 2 | `messaging-spaces.md` | Card payloads are bot territory |
| Membership CRUD | `messaging-spaces.md` section 4 | `messaging-bots.md` | Admin/space management |
| ECM folder linking | `messaging-spaces.md` section 6 | nowhere else | Admin-only, space-scoped |
| HDS monitoring | `messaging-spaces.md` section 7 | nowhere else | Admin-only, read-only |
| Cross-domain recipes (calling + messaging) | `messaging-bots.md` section 7 | calling docs | The glue pattern is always "calling event → messaging action" = bot territory |
| Bot token capabilities/limitations | `messaging-bots.md` section 1 | `messaging-spaces.md` | Bots doc owns bot identity |
| Token type matrix (all types) | `messaging-spaces.md` (top of doc) | `messaging-bots.md` | Spaces doc has the master matrix; bots doc has bot-specific subset |
| Room tabs | `messaging-bots.md` section 6 | `messaging-spaces.md` | Tabs embed apps = developer/integration territory |
| `attachment-actions` commands | `messaging-bots.md` section 5 | `messaging-spaces.md` | Only meaningful in card interaction context |
| `webhooks` CLI group documentation | `webhooks-events.md` | messaging docs | CLI commands map to the CRUD section already there |

### Message Sending Split (the trickiest boundary)

`messaging-spaces.md` covers:
- `wxcli messages create --text "..."` (plain text)
- `wxcli messages create --markdown "..."` (markdown)
- `wxcli messages create --files URL` (file attachment)
- Message CRUD (list, show, edit, delete)
- Direct messages (`--to-person-id`, `--to-person-email`)
- Threading (`--parent-id`)

`messaging-bots.md` covers:
- `wxcli messages create --json-body '{"attachments": [...]}'` (adaptive cards)
- The three-tier message format table (text → markdown → card) for context
- Card recipe catalog
- The attachment action response flow

The rule: if `--json-body` with `attachments` is involved, it's bots territory. Everything else is spaces territory.

---

## Implementation Order

1. `docs/reference/messaging-spaces.md` — standalone, no dependencies
2. `docs/reference/messaging-bots.md` — standalone, references messaging-spaces.md in See Also
3. Expand `docs/reference/webhooks-events.md` — add sections 4b and 6b
4. `.claude/skills/messaging-spaces/SKILL.md` — references messaging-spaces.md
5. `.claude/skills/messaging-bots/SKILL.md` — references messaging-bots.md + webhooks-events.md
6. Update `wxc-calling-builder.md` — 7 changes (frontmatter, interview ×3, dispatch, doc loading, setup check)
7. Update `CLAUDE.md` — file map + description
