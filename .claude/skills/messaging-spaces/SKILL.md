---
name: messaging-spaces
description: |
  Manage Webex spaces, teams, memberships, messages, and enterprise content (ECM/HDS)
  using wxcli CLI commands. Guides the user from prerequisites through execution and verification.
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [operation-type]
---

<!-- Created by playbook session 2026-03-19 -->

# Messaging Spaces Workflow

**Checkpoint — do NOT proceed until you can answer these:**
1. What token type do messaging space operations require? (Answer: User-level or bot token with `spark:rooms_read`/`spark:rooms_write` — admin tokens work for listing but some operations need the acting user's token.)
2. How do you list messages in a space? (Answer: `wxcli messages list --room-id SPACE_ID` — the API uses `roomId` not `spaceId`, matching the older "rooms" terminology.)

If you cannot answer both, you skipped reading this skill. Go back and read it.

## Step 1: Load references

1. Read `docs/reference/messaging-spaces.md` for spaces/messages/teams/ECM/HDS data models and CLI commands
2. Read `docs/reference/authentication.md` for auth token conventions

---

## Step 2: Verify auth token

Before any API calls, confirm the user has a working auth token:

```bash
wxcli whoami
```

If this fails, stop and resolve authentication first (`wxcli configure`).

Check the `type` field in the response to determine the token type:

| `type` value | Token type | Notes |
|-------------|-----------|-------|
| `bot` | Bot token | Limited — cannot create teams, cannot add self to spaces |
| `person` | User token | Full messaging access; space-scoped operations |
| `person` (with `spark-admin:` scopes) | Admin token | Required for ECM, HDS, and org-wide operations. API returns `type: person`, not `admin` — detect admin by checking if `spark-admin:` scoped operations succeed. |

**Required scopes by operation:**

| Operation | Required Scopes |
|-----------|----------------|
| Spaces read | `spark:rooms_read` |
| Spaces write | `spark:rooms_write` |
| Messages read | `spark:messages_read` |
| Messages write | `spark:messages_write` |
| Memberships read | `spark:memberships_read` |
| Memberships write | `spark:memberships_write` |
| Teams read | `spark:teams_read` |
| Teams write | `spark:teams_write` |
| Team memberships | `spark:team_memberships_read`, `spark:team_memberships_write` |
| ECM folder linking | `spark-admin:room_linkedFolders_read`, `spark-admin:room_linkedFolders_write` |
| HDS monitoring | `spark-admin:hds_read` |

**Warn the user** if they are using a bot token and attempting ECM, HDS, or team management operations. Bot tokens will return 403 for those endpoints.

---

## Step 3: Identify the operation type

Ask the user what they want to accomplish. Present this decision matrix if they are unsure:

| User Wants To | Operation Type | Token Required |
|--------------|---------------|---------------|
| Create/manage spaces | Space lifecycle | User or admin token |
| Send/manage messages | Message management | User or bot token (bot must be member) |
| Add/remove space members | Membership management | User token (moderator) or admin token |
| Create/manage teams and team spaces | Team management | User or admin token (NOT bot) |
| Link SharePoint/OneDrive folder to space | ECM setup | Admin token only |
| Monitor HDS cluster health and key availability | HDS monitoring | Admin token only |

---

## Step 4: Check prerequisites per operation

### 4a. Space lifecycle

Check whether the target space already exists before creating:

```bash
# List all spaces the token has access to
wxcli rooms list --output json

# Filter by type
wxcli rooms list --type group --output json

# Filter by team
wxcli rooms list --team-id TEAM_ID --output json
```

If creating a new space, no prerequisites are required beyond a valid token.

If targeting an existing space, capture the `id` field from the list output.

### 4b. Message management

The space must exist and the authenticated user or bot must be a member:

```bash
# Verify the space exists and get its ID
wxcli rooms show ROOM_ID --output json

# Verify the token's identity is a member
wxcli memberships list --room-id ROOM_ID --output json
```

**Bot tokens:** Bots can only read messages where they are @mentioned, except in 1:1 direct spaces. Bots cannot add themselves to spaces — they must be added by a user.

### 4c. Membership management

Confirm the target space exists and the person is identifiable:

```bash
# Verify space exists
wxcli rooms show ROOM_ID --output json

# List current members (to check if person is already a member or find membership IDs)
wxcli memberships list --room-id ROOM_ID --output json

# Find all spaces a specific person belongs to
wxcli memberships list --person-email user@example.com --output json
```

| Prerequisite | Check |
|-------------|-------|
| Space exists | `wxcli rooms show ROOM_ID` |
| Person email or ID is known | Have it ready before `memberships create` |
| Caller is moderator (for locked spaces) | Confirm `isModerator: true` in own membership |
| At least one moderator will remain after removal | Check current moderators before `memberships delete` |

### 4d. Team management

Teams require a user or admin token (bot tokens cannot create or manage teams).

```bash
# List existing teams
wxcli teams list --output json

# Show a team
wxcli teams show TEAM_ID --output json

# List team members
wxcli team-memberships list --team-id TEAM_ID --output json
```

**Warning:** Deleting a team deletes ALL team spaces and their content. This is irreversible.

### 4e. ECM folder linking

ECM requires an admin token and Microsoft Graph API identifiers obtained before calling wxcli:

| Prerequisite | How to obtain |
|-------------|--------------|
| Admin token with `spark-admin:` scopes | `wxcli configure`, verify admin access by testing a `spark-admin:` scoped operation |
| Target space ID (`roomId`) | `wxcli rooms show ROOM_ID` or `wxcli rooms list` |
| SharePoint/OneDrive `driveId` | Microsoft Graph API: `GET /sites/{site-id}/drive` |
| SharePoint/OneDrive `itemId` | Microsoft Graph API: `GET /drives/{drive-id}/root:/path/to/folder` |
| Content URL (`contentUrl`) | The full URL to the SharePoint/OneDrive folder |
| Display name | Human-readable name for the folder link |

### 4f. HDS monitoring

HDS requires an admin token. Obtain org and cluster IDs first:

```bash
# Get the org ID
wxcli organizations list --output json

# Check HDS org enrollment status
wxcli hds show ORG_ID --output json

# List available clusters (if org has HDS enrolled)
wxcli hds list ORG_ID --output json
```

---

## Step 5: Build and present deployment plan — [SHOW BEFORE EXECUTING]

Before executing any commands, present the full plan to the user:

```
DEPLOYMENT PLAN
===============
Operation: [type — e.g., "Create project team with 3 spaces and 5 members"]
Target: [space name / team name / org-wide]

Resources to create/modify:
  - [Team: "Acme Project"] (if applicable)
  - [Space: "Engineering"] (if applicable)
  - [Space: "Announcements" — announcement-only] (if applicable)
  - [Members to add: lead@example.com (moderator), dev1@example.com, dev2@example.com]

Prerequisites verified:
  [checkmark] Auth token verified — type: [user/admin/bot]
  [checkmark] Required scopes present
  [checkmark] Target space/team identified or does not yet exist (new)
  [checkmark] Person emails/IDs confirmed
  [checkmark] ECM drive/item IDs obtained (if ECM operation)

Commands to execute:
  1. wxcli teams create --name "Acme Project" --description "..."
  2. wxcli rooms create --title "Engineering" --team-id TEAM_ID
  3. wxcli rooms create --title "Announcements" --team-id TEAM_ID --is-announcement-only
  4. wxcli team-memberships create --team-id TEAM_ID --person-email lead@example.com --is-moderator
  5. wxcli team-memberships create --team-id TEAM_ID --person-email dev1@example.com
  6. wxcli team-memberships create --team-id TEAM_ID --person-email dev2@example.com

Proceed? (yes/no)
```

**Wait for user confirmation before executing.**

---

## Step 6: Execute via wxcli

Run the commands in plan order. Capture IDs from each creation response to use in subsequent commands.

Refer to the **CLI Command Reference** section at the bottom of this skill for the full command catalog per resource type.

Handle errors explicitly:

- **401/403**: Token expired or insufficient scopes — run `wxcli configure` to re-authenticate
- **404**: Resource not found — confirm the ID is correct and the token has access
- **409**: Conflict (e.g., space already exists with that name) — verify with `list`, then proceed or skip
- **400**: Validation error — read the error message and fix the parameter (e.g., missing required field)
- **429**: Rate limiting — add `sleep 1` between commands; use sequential execution for bulk operations

## Step 7: Verify

Read back each created resource to confirm:

```bash
# Verify a space
wxcli rooms show ROOM_ID --output json

# Verify memberships in a space
wxcli memberships list --room-id ROOM_ID --output json

# Verify a team
wxcli teams show TEAM_ID --output json

# Verify team members
wxcli team-memberships list --team-id TEAM_ID --output json

# Verify ECM folder link
wxcli ecm show FOLDER_ID --output json

# Verify HDS status
wxcli hds show ORG_ID --output json
```

---

## Step 8: Report results

Present the operation results:

```
OPERATION COMPLETE
==================
Operation: [type]
Status: Success

Resources Created/Modified:
  [Team: "Acme Project"]
    ID: [team_id]
    Created: [timestamp]

  [Space: "Engineering"]
    ID: [room_id]
    Team: Acme Project
    Type: group

  [Space: "Announcements"]
    ID: [room_id]
    Team: Acme Project
    Type: group (announcement-only)

  Members added: 3
    lead@example.com — team moderator
    dev1@example.com
    dev2@example.com

Next steps:
  - [e.g., "Add remaining team members"]
  - [e.g., "Upload project files and link ECM folder"]
  - [e.g., "Configure webhooks for message events — see webhooks-events.md"]
  - [e.g., "Set up bot integrations — see messaging-bots.md"]
```

---

## Critical Rules

1. **Always verify token type before executing.** Bot tokens cannot create teams, manage team memberships, or access ECM/HDS. Check `type` in `wxcli whoami` output.
2. **Always show the deployment plan** (Step 5) and wait for user confirmation before executing any create, update, or delete commands.
3. **Membership operations require valid person IDs or emails.** Use `wxcli memberships list` or `wxcli team-memberships list` to find existing membership IDs — they are different from person IDs.
4. **Deleting a space or team is permanent.** There is no recycle bin. Confirm with the user explicitly before running any `delete` command. Deleting a team removes ALL team spaces and content.
5. **Bot tokens cannot create teams or manage team memberships.** Only user tokens and admin tokens can do this. Bot tokens also cannot add themselves to spaces.
6. **ECM and HDS require admin tokens with `spark-admin:` scopes.** User tokens return 403. Verify token type before attempting ECM or HDS commands.
7. **`rooms list` only returns spaces the authenticated user or bot is a member of.** It does not list all org spaces. Use an admin token or the compliance API for org-wide space auditing.
8. **Direct (1:1) spaces cannot be deleted or renamed via API.** The delete endpoint returns an error for direct spaces. The `title` field may be empty for direct spaces.
9. **When adding members in bulk, execute sequentially with `sleep 1` between operations.** The messaging API enforces rate limits (~5 requests/second for bot tokens). Parallel bulk adds risk 429 errors.
10. **Always check if a space or team already exists before creating (idempotency).** Run `wxcli rooms list` or `wxcli teams list` first. Creating a duplicate may succeed but creates clutter, or may fail with a 409 conflict.

---

## Context Compaction Recovery

If context compacts mid-execution, recover by:

1. Read the deployment plan from `docs/plans/` to recover what was planned
2. Check what has already been created:
   ```bash
   wxcli rooms list --output json
   wxcli teams list --output json
   wxcli memberships list --room-id ROOM_ID --output json
   ```
3. Resume from the first incomplete step in the plan

---

## CLI Command Reference

### Spaces (`rooms`)

```bash
# List spaces (authenticated user's spaces only)
wxcli rooms list --output json
wxcli rooms list --type group --sort-by lastactivity --output json
wxcli rooms list --org-public-spaces --output json

# Create a space
wxcli rooms create --title "Project Alpha"
wxcli rooms create --title "Announcements" --team-id TEAM_ID --is-announcement-only
wxcli rooms create --title "Private Discussion" --is-locked

# Show space details
wxcli rooms show ROOM_ID --output json

# Update a space
wxcli rooms update ROOM_ID --title "New Name"
wxcli rooms update ROOM_ID --is-locked
wxcli rooms update ROOM_ID --is-announcement-only

# Get space meeting/SIP info
wxcli rooms show-meeting-info ROOM_ID --output json

# Delete a space (permanent — use with caution)
wxcli rooms delete ROOM_ID --force
```

### Messages (`messages`)

```bash
# List messages in a space
wxcli messages list --room-id ROOM_ID --output json
wxcli messages list --room-id ROOM_ID --limit 50 --output json

# Send a message
wxcli messages create --room-id ROOM_ID --text "Hello team"
wxcli messages create --room-id ROOM_ID --markdown "**Alert:** Deploy complete"
wxcli messages create --to-person-email user@example.com --text "Hi there"

# Reply to a thread
wxcli messages create --room-id ROOM_ID --parent-id MESSAGE_ID --text "Acknowledged"

# List 1:1 direct messages
wxcli messages list-direct --person-email user@example.com --output json

# Show a message
wxcli messages show MESSAGE_ID --output json

# Edit a message (own messages only)
wxcli messages update MESSAGE_ID --text "Updated text"

# Delete a message
wxcli messages delete MESSAGE_ID --force

# Send adaptive card or file attachment (requires --json-body)
wxcli messages create --json-body '{"roomId": "ROOM_ID", "text": "fallback", "attachments": [...]}'
```

### Memberships (`memberships`)

```bash
# List all members of a space
wxcli memberships list --room-id ROOM_ID --output json

# Find all spaces a person belongs to
wxcli memberships list --person-email user@example.com --output json

# Add a member to a space
wxcli memberships create --room-id ROOM_ID --person-email user@example.com
wxcli memberships create --room-id ROOM_ID --person-email user@example.com --is-moderator

# Show membership details (need membership ID, not person ID)
wxcli memberships show MEMBERSHIP_ID --output json

# Promote/demote moderator
wxcli memberships update MEMBERSHIP_ID --is-moderator
wxcli memberships update MEMBERSHIP_ID --no-is-moderator

# Remove a member from a space
wxcli memberships delete MEMBERSHIP_ID --force
```

**Finding a membership ID for a specific person:**

```bash
wxcli memberships list --room-id ROOM_ID --output json | python3 -c "
import sys, json
members = json.load(sys.stdin)
for m in members:
    if m.get('personEmail') == 'user@example.com':
        print(m['id'])
"
```

### Teams (`teams`)

```bash
# List teams
wxcli teams list --output json

# Create a team (auto-creates a General space)
wxcli teams create --name "Engineering" --description "Engineering team spaces"

# Show team details
wxcli teams show TEAM_ID --output json

# Rename a team
wxcli teams update TEAM_ID --name "New Name"

# Delete a team (DESTRUCTIVE — deletes ALL team spaces and content)
wxcli teams delete TEAM_ID --force
```

### Team memberships (`team-memberships`)

```bash
# List team members
wxcli team-memberships list --team-id TEAM_ID --output json

# Add a member to a team (auto-adds to all team spaces)
wxcli team-memberships create --team-id TEAM_ID --person-email user@example.com
wxcli team-memberships create --team-id TEAM_ID --person-email lead@example.com --is-moderator

# Show team membership details
wxcli team-memberships show MEMBERSHIP_ID --output json

# Change moderator role
wxcli team-memberships update MEMBERSHIP_ID --is-moderator
wxcli team-memberships update MEMBERSHIP_ID --no-is-moderator

# Remove from team
wxcli team-memberships delete MEMBERSHIP_ID --force
```

### ECM (`ecm`)

```bash
# List linked folders for a space
wxcli ecm list --room-id ROOM_ID --output json

# Link a SharePoint/OneDrive folder to a space
wxcli ecm create \
  --room-id ROOM_ID \
  --content-url "https://contoso.sharepoint.com/sites/Engineering/Shared Documents/Project" \
  --display-name "Project Files" \
  --drive-id DRIVE_ID \
  --item-id ITEM_ID \
  --default-folder true

# Show linked folder details
wxcli ecm show FOLDER_ID --output json

# Update folder link
wxcli ecm update FOLDER_ID --display-name "Updated Name"

# Unlink folder (does NOT delete files in SharePoint/OneDrive)
wxcli ecm delete FOLDER_ID --force
```

### HDS (`hds`) — read-only

```bash
# Get HDS org enrollment status
wxcli hds show ORG_ID --output json

# Get cluster details
wxcli hds show-clusters CLUSTER_ID --output json

# Get node details
wxcli hds show-nodes NODE_ID --output json

# Get HDS database configuration
wxcli hds list ORG_ID --output json

# Get multi-tenant HDS details
wxcli hds list-multi-tenant ORG_ID --output json

# Get node network test results
wxcli hds list-network-test NODE_ID --trigger-type All --output json

# Get cluster availability metrics
wxcli hds list-availability CLUSTER_ID --from 2026-01-01T00:00:00Z --to 2026-03-19T00:00:00Z --output json
```
