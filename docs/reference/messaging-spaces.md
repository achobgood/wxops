# Messaging: Spaces, Messages, Teams, ECM, and HDS

Reference for Webex messaging infrastructure management. Covers the 40 commands across 7 CLI groups that an IT admin or space manager uses to create and manage spaces, messages, memberships, teams, and enterprise content. Sourced from the Webex Messaging API (OpenAPI spec: `webex-messaging.json`).

## Sources

- OpenAPI spec: `webex-messaging.json`
- [developer.webex.com Messaging APIs](https://developer.webex.com/docs/api/v1/messages)

---

## Token Type Matrix

This matrix is the most important thing to check before running any messaging command. The wrong token type will produce a 403 or unexpected empty results.

| Operation | User Token | Bot Token | Admin Token |
|-----------|-----------|-----------|-------------|
| Space CRUD | Yes | Yes (bot must be member) | Yes |
| Send/list messages | Yes | Yes (bot must be member) | No (admin can list via compliance, not send) |
| Membership CRUD | Yes (if moderator or creator) | Limited (can't add self) | Yes |
| Team CRUD | Yes | No | Yes |
| Team membership CRUD | Yes | No | Yes |
| ECM folder linking | No | No | Yes (requires `spark-admin:` scopes) |
| HDS monitoring | No | No | Yes (requires `spark-admin:` scopes) |

---

## Table of Contents

1. [Messaging Model Overview](#1-messaging-model-overview)
2. [Spaces](#2-spaces)
3. [Messages](#3-messages)
4. [Memberships](#4-memberships)
5. [Teams](#5-teams)
6. [ECM — Enterprise Content Management](#6-ecm--enterprise-content-management)
7. [HDS — Hybrid Data Security](#7-hds--hybrid-data-security)
8. [Common Patterns](#8-common-patterns)
9. [See Also](#9-see-also)

---

## 1. Messaging Model Overview

Webex messaging is organized around spaces (also called rooms). Teams are an optional grouping layer.

```
Organization
  └── Teams (optional grouping)
       └── Team Spaces (rooms belonging to a team)
  └── Spaces (rooms — the core unit)
       ├── Members (memberships — who is in the space)
       ├── Messages (text, files, cards)
       └── Tabs (embedded apps — not covered here)
```

**Terminology:**
- **"room"** is the API term. **"space"** is what the Webex App shows users. They are the same thing.
- **Space types:** `direct` (1:1 between two people) or `group` (multi-person).
- **Team relationship:** a team groups multiple spaces under one umbrella. Creating a team auto-creates a "General" space. Adding a member to a team auto-adds them to all team spaces.

**CLI groups in this doc:**

| CLI Group | Resource | Commands |
|-----------|----------|---------|
| `rooms` | Spaces | 6 |
| `messages` | Messages | 6 |
| `memberships` | Space memberships | 5 |
| `teams` | Teams | 5 |
| `team-memberships` | Team memberships | 5 |
| `ecm` | ECM folder links | 5 |
| `hds` | HDS monitoring | 7 (read-only) |

---

## 2. Spaces

**CLI group:** `rooms`
**API base:** `https://webexapis.com/v1/rooms`

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| List spaces | `wxcli rooms list` | GET /rooms | List spaces the caller belongs to |
| Create space | `wxcli rooms create --title "Name"` | POST /rooms | Create a new group space |
| Show space | `wxcli rooms show ROOM_ID` | GET /rooms/{roomId} | Get space details |
| Update space | `wxcli rooms update ROOM_ID --title "New Name"` | PUT /rooms/{roomId} | Rename, lock, set read-only |
| Delete space | `wxcli rooms delete ROOM_ID --force` | DELETE /rooms/{roomId} | Delete space and all content |
| Meeting info | `wxcli rooms show-meeting-info ROOM_ID` | GET /rooms/{roomId}/meetingInfo | Get SIP/meeting URI for space |

### Key Parameters

#### `rooms list`

| Option | Description |
|--------|-------------|
| `--type direct\|group` | Filter by space type |
| `--team-id TEAM_ID` | List spaces belonging to a specific team |
| `--sort-by id\|lastactivity\|created` | Sort order |
| `--org-public-spaces` | Show org's public spaces (joined and unjoined) |
| `--from` | Filter public spaces made public after this time (ISO 8601) |
| `--to` | Filter public spaces made public before this time (ISO 8601) |
| `--max N` | API-level page size |
| `--limit N` | CLI-level result cap |
| `--output table\|json` | Output format (default: table) |

#### `rooms create`

| Option | Required | Description |
|--------|:--------:|-------------|
| `--title TEXT` | Yes | Display name for the space |
| `--team-id TEAM_ID` | No | Associate with an existing team |
| `--is-locked/--no-is-locked` | No | Locked (moderated): creator becomes moderator, others cannot add members |
| `--is-public/--no-is-public` | No | Make space discoverable within the org |
| `--is-announcement-only/--no-is-announcement-only` | No | Only moderators can post |
| `--description TEXT` | No | Space description |
| `--classification-id ID` | No | Data classification label |
| `--json-body JSON` | No | Full JSON body (overrides all other options) |

#### `rooms update`

| Option | Description |
|--------|-------------|
| `--title TEXT` | Rename the space |
| `--is-locked/--no-is-locked` | Lock or unlock the space |
| `--is-public/--no-is-public` | Change public visibility |
| `--is-announcement-only/--no-is-announcement-only` | Set/clear announcement mode |
| `--is-read-only/--no-is-read-only` | Compliance officer can set direct room as read-only (archive pattern) |
| `--description TEXT` | Update description |
| `--team-id TEAM_ID` | Move unowned space to a team |
| `--classification-id ID` | Change classification |

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"

# List spaces
result = api.session.rest_get(f"{BASE}/rooms", params={"type": "group", "sortBy": "lastactivity"})
spaces = result.get("items", [])
# Each item: {"id", "title", "type", "isLocked", "teamId", "lastActivity", "created", ...}

# Create space
body = {"title": "Project Alpha", "teamId": team_id}
result = api.session.rest_post(f"{BASE}/rooms", json=body)
room_id = result.get("id")

# Get meeting info (SIP URI + meeting link)
info = api.session.rest_get(f"{BASE}/rooms/{room_id}/meetingInfo")
# Returns: {"roomId", "meetingLink", "sipAddress", "meetingNumber", "callInTollFreeNumber", ...}
```

### Gotchas

- **Deleting a space is permanent** — no recycle bin. Always confirm with `--force` or the CLI will prompt.
- **`list` only returns spaces the authenticated user or bot is a member of.** To list all org spaces, use an admin token or the compliance API.
- **Direct spaces (1:1) cannot be deleted via API.** The delete endpoint will return an error.
- **Space titles are optional for direct spaces** — the Webex App uses participant names instead. The `title` field may be empty or absent for direct spaces.
- **`show-meeting-info` returns the SIP address and meeting link for a space** — useful for bridging Webex Calling + Messaging (e.g., dialing into a space from a desk phone).
- **`--is-read-only` is a compliance officer capability.** Regular users and admins without the compliance role cannot set this flag.

---

## 3. Messages

**CLI group:** `messages`
**API base:** `https://webexapis.com/v1/messages`

For adaptive card payloads (`attachments` field), use `--json-body`. See `messaging-bots.md` for card recipes.

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| List messages | `wxcli messages list --room-id ROOM_ID` | GET /messages | List messages in a space |
| Send message | `wxcli messages create --room-id ROOM_ID --text "Hello"` | POST /messages | Send a message to a space |
| List direct | `wxcli messages list-direct --person-email user@example.com` | GET /messages/direct | List 1:1 messages with a person |
| Show message | `wxcli messages show MESSAGE_ID` | GET /messages/{messageId} | Get message details |
| Edit message | `wxcli messages update MESSAGE_ID --text "Updated"` | PUT /messages/{messageId} | Edit an existing message |
| Delete message | `wxcli messages delete MESSAGE_ID --force` | DELETE /messages/{messageId} | Delete a message |

### Key Parameters

#### `messages list`

| Option | Description |
|--------|-------------|
| `--room-id ROOM_ID` | Required — list messages in this space |
| `--parent-id MESSAGE_ID` | List threaded replies to a message |
| `--mentioned-people PERSON_ID` | Filter to messages mentioning this person (use `me` for self) |
| `--before DATETIME` | Messages sent before this time (ISO 8601) |
| `--before-message MESSAGE_ID` | Messages sent before this message (pagination) |
| `--max N` | API-level page size |
| `--limit N` | CLI-level result cap |
| `--output table\|json` | Output format (default: table; columns: ID, Person Email, Text) |

#### `messages create`

| Option | Notes |
|--------|-------|
| `--room-id ROOM_ID` | Send to a group or direct space |
| `--to-person-id PERSON_ID` | Send a 1:1 direct message by person ID |
| `--to-person-email EMAIL` | Send a 1:1 direct message by email |
| `--text TEXT` | Plain text content |
| `--markdown TEXT` | Markdown content (bold, italic, links, @mentions, code blocks) |
| `--parent-id MESSAGE_ID` | Reply to a specific message (creates a thread) |
| `--json-body JSON` | Full JSON body — required for `files`, `attachments` (adaptive cards) |

Use exactly one of `--room-id`, `--to-person-id`, or `--to-person-email` to specify the destination.

#### `messages list-direct`

| Option | Description |
|--------|-------------|
| `--person-id PERSON_ID` | List 1:1 messages with this person (by ID) |
| `--person-email EMAIL` | List 1:1 messages with this person (by email) |
| `--parent-id MESSAGE_ID` | Filter to a thread |

#### `messages update`

| Option | Notes |
|--------|-------|
| `--room-id ROOM_ID` | Room ID of the message (required in body for edit) |
| `--text TEXT` | Updated plain text |
| `--markdown TEXT` | Updated markdown text |

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"

# Send a plain text message
body = {"roomId": room_id, "text": "Hello from wxcli"}
result = api.session.rest_post(f"{BASE}/messages", json=body)

# Send a markdown message
body = {"roomId": room_id, "markdown": "**Alert:** Configuration complete for _Location Alpha_."}
result = api.session.rest_post(f"{BASE}/messages", json=body)

# Send a file attachment (URL must be publicly accessible)
body = {"roomId": room_id, "text": "Here is the report", "files": ["https://example.com/report.pdf"]}
result = api.session.rest_post(f"{BASE}/messages", json=body)

# Send adaptive card (see messaging-bots.md for card schema)
body = {
    "roomId": room_id,
    "text": "Fallback text for clients that don't support cards",
    "attachments": [{"contentType": "application/vnd.microsoft.card.adaptive", "content": {...}}]
}
result = api.session.rest_post(f"{BASE}/messages", json=body)

# List messages with pagination
result = api.session.rest_get(f"{BASE}/messages", params={"roomId": room_id, "max": 50})
messages = result.get("items", [])
# Each item: {"id", "roomId", "personId", "personEmail", "text", "markdown", "created", "updated", ...}
```

### Gotchas

- **`--room-id` is required for `list`** — there is no global messages endpoint. You must specify a room.
- **`--files` accepts a URL, not a local file path.** The URL must be publicly accessible or a Webex content URL. For local file uploads, use `--json-body` with a multipart approach or upload first via another mechanism.
- **Bots can only read messages where they are @mentioned**, except in 1:1 direct spaces where they see all messages.
- **Edit only works on messages sent by the authenticated user or bot.** Editing someone else's message will return 403.
- **`--before` and `--before-message` are pagination tools** — use `--before-message` with the ID of the oldest message in the last page to walk backward through history.
- **Adaptive card payloads require `--json-body`** — the `attachments` array cannot be set via `--text` or `--markdown`. See `messaging-bots.md` for adaptive card recipes.

---

## 4. Memberships

**CLI group:** `memberships`
**API base:** `https://webexapis.com/v1/memberships`

A membership is the relationship between a person and a space. The membership ID is distinct from the person ID.

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| List members | `wxcli memberships list --room-id ROOM_ID` | GET /memberships | List space members |
| Add member | `wxcli memberships create --room-id ROOM_ID --person-email user@example.com` | POST /memberships | Add person to space |
| Show membership | `wxcli memberships show MEMBERSHIP_ID` | GET /memberships/{membershipId} | Get membership details |
| Update membership | `wxcli memberships update MEMBERSHIP_ID --is-moderator` | PUT /memberships/{membershipId} | Change moderator status or hide space |
| Remove member | `wxcli memberships delete MEMBERSHIP_ID --force` | DELETE /memberships/{membershipId} | Remove person from space |

### Key Parameters

#### `memberships list`

| Option | Description |
|--------|-------------|
| `--room-id ROOM_ID` | List all members of a specific space |
| `--person-id PERSON_ID` | List all spaces a specific person belongs to |
| `--person-email EMAIL` | List all spaces a specific person belongs to (by email) |
| `--max N` | Page size |
| `--output table\|json` | Output format (default: table; columns: ID, Name) |

#### `memberships create`

| Option | Required | Description |
|--------|:--------:|-------------|
| `--room-id ROOM_ID` | Yes | Space to add the person to |
| `--person-id PERSON_ID` | One of these | Person to add (by ID) |
| `--person-email EMAIL` | One of these | Person to add (by email) |
| `--is-moderator/--no-is-moderator` | No | Grant moderator role on add |

#### `memberships update`

| Option | Description |
|--------|-------------|
| `--is-moderator/--no-is-moderator` | Grant or revoke moderator role |
| `--is-room-hidden/--no-is-room-hidden` | Hide/show the space in the member's space list (Teams client only) |

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"

# List members of a space
result = api.session.rest_get(f"{BASE}/memberships", params={"roomId": room_id})
members = result.get("items", [])
# Each item: {"id", "roomId", "personId", "personEmail", "personDisplayName", "isModerator", "created", ...}

# Add a member
body = {"roomId": room_id, "personEmail": "user@example.com", "isModerator": False}
result = api.session.rest_post(f"{BASE}/memberships", json=body)
membership_id = result.get("id")

# Promote to moderator
body = {"isModerator": True}
api.session.rest_put(f"{BASE}/memberships/{membership_id}", json=body)

# Remove member
api.session.rest_delete(f"{BASE}/memberships/{membership_id}")
```

### Gotchas

- **The membership ID is NOT the person ID.** It is a separate identifier for the person-in-space relationship. You need the membership ID to update or delete a membership. Use `memberships list --room-id ROOM_ID` to find it.
- **Removing the last moderator from a locked space makes it unmodifiable.** Always ensure at least one moderator remains before removing others.
- **Bots cannot add themselves to spaces.** Bots must be added by a user or via an integration OAuth flow.
- **`list` requires at least `--room-id` or `--person-id`.** A bare `memberships list` with no filter will return memberships for the authenticated user only.

---

## 5. Teams

**CLI groups:** `teams` and `team-memberships`
**API bases:** `https://webexapis.com/v1/teams` and `https://webexapis.com/v1/team/memberships`

A team is a grouping of related spaces. When you delete a team, all team spaces and their content are deleted.

### Team Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| List teams | `wxcli teams list` | GET /teams | List teams the caller belongs to |
| Create team | `wxcli teams create --name "Team Name"` | POST /teams | Create a new team |
| Show team | `wxcli teams show TEAM_ID` | GET /teams/{teamId} | Get team details |
| Update team | `wxcli teams update TEAM_ID --name "New Name"` | PUT /teams/{teamId} | Rename or update description |
| Delete team | `wxcli teams delete TEAM_ID --force` | DELETE /teams/{teamId} | Delete team and ALL team spaces |

#### `teams create` Parameters

| Option | Required | Description |
|--------|:--------:|-------------|
| `--name TEXT` | Yes | Display name for the team |
| `--description TEXT` | No | Team description |

#### `teams update` Parameters

| Option | Description |
|--------|-------------|
| `--name TEXT` | New team name |
| `--description TEXT` | Updated description |

### Team Membership Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| List team members | `wxcli team-memberships list --team-id TEAM_ID` | GET /team/memberships | List members of a team |
| Add team member | `wxcli team-memberships create --team-id TEAM_ID --person-email user@example.com` | POST /team/memberships | Add person to team |
| Show team membership | `wxcli team-memberships show MEMBERSHIP_ID` | GET /team/memberships/{membershipId} | Get team membership details |
| Update team membership | `wxcli team-memberships update MEMBERSHIP_ID --is-moderator` | PUT /team/memberships/{membershipId} | Change moderator role |
| Remove team member | `wxcli team-memberships delete MEMBERSHIP_ID --force` | DELETE /team/memberships/{membershipId} | Remove person from team |

#### `team-memberships create` Parameters

| Option | Required | Description |
|--------|:--------:|-------------|
| `--team-id TEAM_ID` | Yes | Team to add the person to |
| `--person-id PERSON_ID` | One of these | Person to add (by ID) |
| `--person-email EMAIL` | One of these | Person to add (by email) |
| `--is-moderator/--no-is-moderator` | No | Grant team moderator role |

#### `team-memberships update` Parameters

| Option | Description |
|--------|-------------|
| `--is-moderator/--no-is-moderator` | Grant or revoke team moderator role |

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"

# Create team
body = {"name": "Engineering", "description": "Engineering team"}
result = api.session.rest_post(f"{BASE}/teams", json=body)
team_id = result.get("id")

# List team members
result = api.session.rest_get(f"{BASE}/team/memberships", params={"teamId": team_id})
members = result.get("items", [])
# Each item: {"id", "teamId", "personId", "personEmail", "personDisplayName", "isModerator", "created", ...}

# Add team member
body = {"teamId": team_id, "personEmail": "engineer@example.com", "isModerator": False}
result = api.session.rest_post(f"{BASE}/team/memberships", json=body)

# Delete team (DESTRUCTIVE — deletes all team spaces)
api.session.rest_delete(f"{BASE}/teams/{team_id}")
```

### Gotchas

- **Deleting a team deletes ALL team spaces and their content.** This is irreversible. Use `--force` to skip confirmation, but do not use `--force` in automated scripts without an explicit safety check.
- **Adding a member to a team auto-adds them to all existing team spaces.** The reverse is not true — removing a team member does not remove them from individual team spaces they were added to directly.
- **Team membership is separate from space membership.** A user can be removed from individual team spaces while remaining a team member, and vice versa.
- **Bot tokens cannot create or manage teams.** Only user tokens and admin tokens have this capability.
- **Note the API URL asymmetry:** teams are at `/teams` but team memberships are at `/team/memberships` (singular "team", not "teams"). The CLI handles this transparently.

---

## 6. ECM — Enterprise Content Management

**CLI group:** `ecm`
**API base:** `https://webexapis.com/v1/room/linkedFolders`

ECM links SharePoint/OneDrive folders to Webex spaces, allowing users to access enterprise content directly from a space. This is an admin-only operation.

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| List linked folders | `wxcli ecm list` | GET /room/linkedFolders | List ECM folder links (optionally filtered by room) |
| Link folder | `wxcli ecm create --room-id ROOM_ID ...` | POST /room/linkedFolders | Link an ECM folder to a space |
| Show linked folder | `wxcli ecm show FOLDER_ID` | GET /room/linkedFolders/{id} | Get linked folder details |
| Update linked folder | `wxcli ecm update FOLDER_ID ...` | PUT /room/linkedFolders/{id} | Update folder link configuration |
| Unlink folder | `wxcli ecm delete FOLDER_ID --force` | DELETE /room/linkedFolders/{id} | Remove folder link from space |

### Key Parameters

#### `ecm list`

| Option | Description |
|--------|-------------|
| `--room-id ROOM_ID` | Filter to linked folders for a specific space |
| `--output table\|json` | Output format (default: table; columns: ID, Name) |

#### `ecm create`

| Option | Required | Description |
|--------|:--------:|-------------|
| `--room-id ROOM_ID` | Yes | Space to link the folder to |
| `--content-url URL` | Yes | URL of the ECM folder |
| `--display-name TEXT` | Yes | Display name (should match the folder name in the ECM backend) |
| `--drive-id ID` | Yes | SharePoint or OneDrive drive ID (query via MS Graph API) |
| `--item-id ID` | Yes | SharePoint or OneDrive item ID (query via MS Graph API) |
| `--default-folder VALUE` | Yes | Set as default storage folder for the space |

#### `ecm update`

Same parameters as create, all optional. Pass only the fields you want to change.

### Required Scopes

ECM operations require an admin token with standard `spark-admin:` scopes (e.g., `spark-admin:rooms_read`). No special ECM-specific scopes are needed -- the `/room/linkedFolders` endpoint works with a full admin token using standard room scopes. Standard user tokens are insufficient. <!-- Verified via live API 2026-03-19 -->

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"

# List ECM linked folders for a space
result = api.session.rest_get(f"{BASE}/room/linkedFolders", params={"roomId": room_id})
folders = result.get("items", [])

# Link a SharePoint folder
body = {
    "roomId": room_id,
    "contentUrl": "https://contoso.sharepoint.com/sites/Engineering/Shared Documents/Project",
    "displayName": "Project",
    "driveId": "<drive-id-from-ms-graph>",
    "itemId": "<item-id-from-ms-graph>",
    "defaultFolder": "true"
}
result = api.session.rest_post(f"{BASE}/room/linkedFolders", json=body)
folder_id = result.get("id")

# Unlink folder
api.session.rest_delete(f"{BASE}/room/linkedFolders/{folder_id}")
```

### Gotchas

- **Admin token with `spark-admin:` scopes is required.** User tokens return 403.
- **`--drive-id` and `--item-id` must be obtained from the Microsoft Graph API** before calling ECM endpoints. They are Microsoft-side identifiers for the SharePoint/OneDrive resource.
- **`--display-name` should match the actual folder name in the ECM backend** to avoid confusion for end users.
- **Unlinking a folder removes the link but does not delete the files** in SharePoint/OneDrive.

**ECM provider support:** The OpenAPI spec and schema definitions reference only Microsoft SharePoint and OneDrive. The `driveId` and `itemId` fields are described as "Sharepoint or OneDrive" identifiers collected via the MS Graph API, and all examples use `sharepoint.com` URLs. Box is not supported as an ECM provider for folder linking. <!-- Verified via OpenAPI spec (webex-messaging.json) 2026-03-19 -->

---

## 7. HDS — Hybrid Data Security

**CLI group:** `hds`
**API base:** `https://webexapis.com/v1/hds`

HDS manages encryption keys on-premises for compliance-sensitive organizations. These commands are monitoring-only — there are no write operations. Requires an admin token.

### Commands

| Command | CLI | What It Shows |
|---------|-----|--------------|
| Org status | `wxcli hds show ORG_ID` | HDS organization enrollment status and configuration |
| Cluster details | `wxcli hds show-clusters CLUSTER_ID` | HDS cluster configuration and health |
| Node details | `wxcli hds show-nodes NODE_ID` | Individual node status |
| Database details | `wxcli hds list ORG_ID` | HDS database configuration |
| Multi-tenant info | `wxcli hds list-multi-tenant ORG_ID` | Multi-tenant HDS org details |
| Network tests | `wxcli hds list-network-test NODE_ID` | Network test results for a node |
| Availability | `wxcli hds list-availability CLUSTER_ID` | Cluster availability metrics over time |

### Key Parameters

#### `hds list-network-test NODE_ID`

| Option | Description |
|--------|-------------|
| `--trigger-type OnDemand\|Periodic\|All` | Filter test results by trigger type |
| `--output table\|json` | Output format (default: table) |

#### `hds list-availability CLUSTER_ID`

| Option | Description |
|--------|-------------|
| `--from DATETIME` | Start of availability window (ISO 8601) |
| `--to DATETIME` | End of availability window (ISO 8601) |
| `--output table\|json` | Output format (default: table) |

### Raw HTTP

```python
BASE = "https://webexapis.com/v1/hds"

# Get HDS org status
org_status = api.session.rest_get(f"{BASE}/organizations/{org_id}")

# Get cluster details
cluster = api.session.rest_get(f"{BASE}/clusters/{cluster_id}")

# Get node details
node = api.session.rest_get(f"{BASE}/nodes/{node_id}")

# Get database details
db = api.session.rest_get(f"{BASE}/organizations/{org_id}/database/details")

# Get multi-tenant details
mt = api.session.rest_get(f"{BASE}/organizations/{org_id}/multiTenant")

# Get node network test results
tests = api.session.rest_get(f"{BASE}/testResults/nodes/{node_id}/networkTest",
                              params={"triggerType": "All"})

# Get cluster availability
avail = api.session.rest_get(f"{BASE}/clusters/{cluster_id}/availability",
                              params={"from": "2026-01-01T00:00:00Z", "to": "2026-03-19T00:00:00Z"})
```

### Gotchas

- **All HDS commands are read-only.** There are no create, update, or delete operations in the `hds` CLI group.
- **Requires admin token.** HDS monitoring is not available via user or bot tokens.
- **IDs are required positional arguments** for all `hds` commands (e.g., `hds show ORG_ID`, `hds show-clusters CLUSTER_ID`). The org ID is available from `wxcli organizations list`.

HDS endpoints work with a standard full admin token -- no special admin role (e.g., Compliance Officer) is required. The `/hybrid/clusters` endpoint returns 200 with a full admin token. <!-- Verified via live API 2026-03-19 -->

---

## 8. Common Patterns

All messaging commands support `--output json|table`. Use `--output json` for scripting and piping results to other tools.

> **Note:** Specific numeric rate limits (~5 req/s for bot tokens) not yet confirmed via live testing. The OpenAPI spec confirms 429 responses with Retry-After headers but does not document per-token-type rates.

### Bulk Create Spaces from a List

```bash
# Create multiple project spaces from a list of names
for name in "Project Alpha" "Project Beta" "Project Gamma"; do
  wxcli rooms create --title "$name" --team-id TEAM_ID
  sleep 1
done
```

### Audit All Memberships in a Space

```bash
# List all members of a space in JSON for processing
wxcli memberships list --room-id ROOM_ID --output json

# Find all spaces a specific user belongs to
wxcli memberships list --person-email user@example.com --output json
```

### Archive a Space (Read-Only + Notice)

```bash
# 1. Post an archival notice
wxcli messages create --room-id ROOM_ID --text "This space is now archived. No further messages will be accepted."

# 2. Set the space to read-only (compliance officer token required)
wxcli rooms update ROOM_ID --is-read-only

# 3. Optionally rename to indicate archived status
wxcli rooms update ROOM_ID --title "[ARCHIVED] Project Alpha"
```

### Set Up a Project Team

```bash
# 1. Create the team (auto-creates a General space)
wxcli teams create --name "Acme Project" --description "Q2 2026 deployment"

# 2. Create additional team spaces
TEAM_ID="<id from step 1>"
wxcli rooms create --title "Engineering" --team-id $TEAM_ID
wxcli rooms create --title "Announcements" --team-id $TEAM_ID --is-announcement-only

# 3. Add team members (auto-adds to all team spaces)
wxcli team-memberships create --team-id $TEAM_ID --person-email lead@example.com --is-moderator
wxcli team-memberships create --team-id $TEAM_ID --person-email dev1@example.com
wxcli team-memberships create --team-id $TEAM_ID --person-email dev2@example.com
```

### Export Messages from a Space (Paginated)

```bash
# Get the first 50 messages
wxcli messages list --room-id ROOM_ID --limit 50 --output json > messages_page1.json

# Get the next page using the oldest message ID from the previous result
OLDEST_ID="<id of oldest message in page 1>"
wxcli messages list --room-id ROOM_ID --before-message $OLDEST_ID --limit 50 --output json > messages_page2.json
```

### Find a Membership ID for a Specific Person

```bash
# You need the membership ID to update or remove a specific person
wxcli memberships list --room-id ROOM_ID --output json | python3 -c "
import sys, json
members = json.load(sys.stdin)
for m in members:
    if m.get('personEmail') == 'user@example.com':
        print(m['id'])
"
```

---

## Gotchas (Cross-Cutting)

These issues span multiple messaging API surfaces. Check per-section Gotchas for endpoint-specific notes.

1. **Rate limits apply across all messaging endpoints.** Bot tokens have lower rate limits than user/admin tokens (exact numbers not officially documented — honor `Retry-After` headers). When bulk-creating spaces, adding members, or sending messages in a loop, add a short delay (e.g., `sleep 1`) between operations. A 429 response includes a `Retry-After` header — always honor it.

2. **Pagination is cursor-based, not offset-based.** All `list` commands use `items` arrays with `Link` headers for the next page. The CLI handles pagination internally via `--max` (API page size) and `--limit` (total result cap). For raw HTTP, follow the `Link: <url>; rel="next"` header to walk through pages.

3. **Membership sync delays on team operations.** Adding a member to a team auto-adds them to all team spaces, but the space-level membership may take a few seconds to propagate. If you add a team member and immediately try to post a message as that user in a team space, the message may fail with 403 until the membership propagates.

4. **Bot vs user vs admin token capabilities differ significantly.** See the Token Type Matrix at the top of this doc before every operation. Bots cannot manage teams. Admins cannot send messages (only list via compliance). Users cannot perform ECM or HDS operations.

5. **Direct (1:1) spaces have special behavior.** They cannot be deleted, cannot be renamed (title is derived from participant names), and are auto-created when you send a message via `--to-person-email` or `--to-person-id`. There is no explicit "create direct space" operation.

6. **IDs are Base64-encoded and org-scoped.** All Webex resource IDs (room, person, membership, team) are long Base64 strings. They are not transferable between orgs. When scripting, always resolve IDs dynamically rather than hardcoding them.

---

## 9. See Also

- [`messaging-bots.md`](messaging-bots.md) — Bot development, adaptive cards, interactive workflows, `--json-body` recipes for `attachments`
- [`webhooks-events.md`](webhooks-events.md) — Webhook CRUD and event payloads for messaging events (`messages`, `memberships`, `rooms`, `attachmentActions`)
- [`authentication.md`](authentication.md) — Token types (user, bot, admin), scopes, OAuth flows
