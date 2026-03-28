---
name: manage-meetings
description: |
  Schedule, manage, and query Webex meetings, registrants, interpreters,
  breakout sessions, transcripts, recordings, and polls using wxcli CLI commands.
  Guides the user from prerequisites through execution and verification.
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [meeting-operation]
---

<!-- Created by playbook session 2026-03-28 -->

# Manage Meetings Workflow

**Checkpoint — do NOT proceed until you can answer these:**
1. What is the command to list meetings as an admin? (Answer: `wxcli meetings list-meetings-admin` — the non-admin version is `wxcli meetings list-meetings`.)
2. How do you list meeting transcripts for compliance? (Answer: `wxcli meeting-transcripts list` — the per-meeting version is `wxcli meeting-transcripts list-meeting-transcripts`.)

If you cannot answer both, you skipped reading this skill. Go back and read it.

## Step 1: Load references

1. Read `docs/reference/meetings-core.md` for meeting CRUD, templates, controls, registrants, interpreters, breakouts, surveys
2. Read `docs/reference/meetings-content.md` for transcripts, captions, chats, summaries, meeting messages
3. Read `docs/reference/meetings-settings.md` for preferences, session types, tracking codes, site settings, polls, Q&A, reports

---

## Step 2: Verify auth token

Before any API calls, confirm the user has a working auth token:

```bash
wxcli whoami
```

If this fails, stop and resolve authentication first (`wxcli configure`).

**Required scopes by operation area:**

| Operation | User Scope | Admin Scope |
|-----------|-----------|-------------|
| Meeting CRUD | `meeting:schedules_read`, `meeting:schedules_write` | `meeting:admin_schedule_read`, `meeting:admin_schedule_write` |
| Participants | `meeting:participants_read` | `meeting:admin_participants_read` |
| Preferences | `meeting:preferences_read`, `meeting:preferences_write` | `meeting:admin_preferences_read`, `meeting:admin_preferences_write` |
| Transcripts | `meeting:transcripts_read` | `meeting:admin_transcripts_read` |
| Recordings | `meeting:recordings_read`, `meeting:recordings_write` | `meeting:admin_recordings_read`, `meeting:admin_recordings_write` |
| Controls | `meeting:controls_read`, `meeting:controls_write` | — |

**Admin vs. user tokens:** Admin tokens can operate on behalf of any user by passing `--host-email`. User tokens operate only on the authenticated user's meetings.

---

## Step 3: Identify the operation type

Ask the user what they want to accomplish. Present this decision matrix if they are unsure:

| User Wants To | Operation Type | CLI Group(s) |
|--------------|---------------|-------------|
| Schedule, update, or delete meetings | Meeting CRUD | `meetings` |
| List meetings (admin view, across org) | Admin meeting query | `meetings` (`list-meetings-admin`, `show-meetings-admin`) |
| Manage registrants (approve, reject, batch) | Registration management | `meetings` |
| Set up simultaneous interpretation | Interpreter management | `meetings` |
| Create/update breakout session assignments | Breakout sessions | `meetings` |
| View/manage meeting surveys | Survey management | `meetings` |
| List/admit participants, SIP callout | Participant control | `meeting-participants` |
| Invite attendees, batch invite | Invitee management | `meeting-invitees` |
| Download/manage transcripts | Transcript access | `meeting-transcripts` |
| View/download closed captions | Caption access | `meeting-captions` |
| Get AI meeting summaries | Summary retrieval | `meeting-summaries` |
| View in-meeting chat logs | Chat access | `meeting-chats` |
| Review polls, Q&A, respondents | Poll/Q&A analytics | `meeting-polls`, `meeting-qa` |
| Configure personal room, audio, video | Preference settings | `meeting-preferences` |
| Manage tracking codes | Tracking codes | `meeting-tracking-codes` |
| View/update session types | Session type config | `meeting-session-types` |
| Pull usage/attendee reports | Meeting reports | `meeting-reports` |
| Configure site-wide meeting settings | Site settings | `meeting-site` |
| View Slido compliance events | Slido compliance | `meeting-slido` |
| Delete a meeting message | Message cleanup | `meeting-messages` |
| Not a meeting operation? | For Video Mesh monitoring → `video-mesh` skill. For call features → `configure-features` skill. For call control → `call-control` skill. | — |

---

## Step 4: Check prerequisites per operation

### 4a. Meeting CRUD

No special prerequisites beyond a valid token. To create a meeting, you need:

| Prerequisite | Check |
|-------------|-------|
| Auth token | `wxcli whoami` |
| Meeting title | Required for create |
| Start/end time | Required for scheduled meetings |
| Site URL (if multi-site org) | `wxcli meeting-preferences list-sites --output json` |

To check if meetings already exist in a time range:

```bash
wxcli meetings list-meetings --from 2026-04-01T00:00:00Z --to 2026-04-30T23:59:59Z --output json
```

For admin operations across the org:

```bash
wxcli meetings list-meetings-admin --from 2026-04-01T00:00:00Z --to 2026-04-30T23:59:59Z --output json
```

### 4b. Registrants

The meeting must exist and have registration enabled:

```bash
# Get meeting details and check registration status
wxcli meetings show-meetings MEETING_ID --output json

# Check existing registration form
wxcli meetings list-registration MEETING_ID --output json
```

### 4c. Interpreters and breakouts

The meeting must exist:

```bash
# List existing interpreters
wxcli meetings list-interpreters MEETING_ID --output json

# List existing breakout sessions
wxcli meetings list-breakout-sessions MEETING_ID --output json
```

### 4d. Transcripts and content (post-meeting)

The meeting must have ended and have the relevant content available:

```bash
# List transcripts for a specific meeting
wxcli meeting-transcripts list-meeting-transcripts --meeting-id MEETING_ID --output json

# List captions
wxcli meeting-captions list-meeting-closed-captions MEETING_ID --output json

# Get AI summary
wxcli meeting-summaries list-meeting-summaries MEETING_ID --output json
```

### 4e. Preferences and site settings

No prerequisites beyond a valid token:

```bash
# Check current preferences
wxcli meeting-preferences list-meeting-preferences --output json

# List available sites
wxcli meeting-preferences list-sites --output json

# Get personal meeting room settings
wxcli meeting-preferences list-personal-meeting-room --output json
```

### 4f. Tracking codes

Admin token required for org-wide tracking code management:

```bash
# List existing tracking codes
wxcli meeting-tracking-codes list --output json
```

---

## Step 5: Gather configuration and present deployment plan — [SHOW BEFORE EXECUTING]

Based on the selected operation, collect the required parameters from the user. **Always present the plan before executing.**

---

### Meeting CRUD

Collect from user:

| Parameter | Required | Notes |
|-----------|:--------:|-------|
| Title | Yes | Meeting title |
| Start | Yes | ISO 8601 format (e.g., `2026-04-15T10:00:00Z`) |
| End | Yes | ISO 8601 format |
| Password | No | Auto-generated if not provided |
| Timezone | No | e.g., `America/New_York` |
| Site URL | No | Required if multi-site org |
| Host email | No | For admin creating on behalf of user |
| Scheduled type | No | `meeting` (default), `webinar`, `personalRoomMeeting` |
| Agenda | No | Meeting description/agenda text |
| Recurrence | No | Requires `--json-body` for recurrence patterns |

**CLI commands:**

```bash
# Create a meeting
wxcli meetings create-meetings \
  --title "Weekly Standup" \
  --start 2026-04-15T10:00:00Z \
  --end 2026-04-15T10:30:00Z \
  --timezone America/New_York

# Create on behalf of another user (admin)
wxcli meetings create-meetings \
  --title "Department Review" \
  --start 2026-04-15T14:00:00Z \
  --end 2026-04-15T15:00:00Z \
  --host-email user@example.com

# Update a meeting
wxcli meetings update-meetings MEETING_ID \
  --title "Updated Title" \
  --password NewPass123

# Patch a meeting (partial update)
wxcli meetings update-meetings-1 MEETING_ID --title "Patched Title"

# Delete a meeting
wxcli meetings delete-meetings MEETING_ID

# End an in-progress meeting
wxcli meetings create-end MEETING_ID

# Join a meeting
wxcli meetings create-join MEETING_ID

# Reassign meetings to a new host
wxcli meetings create-reassign-host --json-body '{"meetingIds": ["ID1"], "hostEmail": "new@example.com"}'
```

---

### Registrants

```bash
# Get registration form
wxcli meetings list-registration MEETING_ID --output json

# Update registration form
wxcli meetings update-registration MEETING_ID --json-body '{"requireFirstName": true, "requireLastName": true}'

# Register a single registrant
wxcli meetings create MEETING_ID --json-body '{"firstName": "Jane", "lastName": "Doe", "email": "jane@example.com"}'

# Batch register
wxcli meetings create-bulk-insert MEETING_ID --json-body '{"items": [{"firstName": "Jane", "email": "jane@example.com"}]}'

# List registrants
wxcli meetings list-registrants MEETING_ID --output json

# Approve registrants
wxcli meetings create-approve MEETING_ID --json-body '{"registrants": [{"registrantId": "REG_ID"}]}'

# Reject registrants
wxcli meetings create-reject MEETING_ID --json-body '{"registrants": [{"registrantId": "REG_ID"}]}'

# Cancel registrants
wxcli meetings create-cancel MEETING_ID --json-body '{"registrants": [{"registrantId": "REG_ID"}]}'

# Delete registration form
wxcli meetings delete MEETING_ID
```

---

### Interpreters and Breakouts

```bash
# List interpreters
wxcli meetings list-interpreters MEETING_ID --output json

# Create an interpreter
wxcli meetings create-interpreters MEETING_ID --json-body '{"items": [{"email": "interpreter@example.com", "languageCode1": "en", "languageCode2": "es"}]}'

# Update an interpreter
wxcli meetings update-interpreters MEETING_ID INTERPRETER_ID --json-body '{"languageCode1": "en", "languageCode2": "fr"}'

# Delete an interpreter
wxcli meetings delete-interpreters MEETING_ID INTERPRETER_ID

# Update simultaneous interpretation settings
wxcli meetings update-simultaneous-interpretation MEETING_ID --json-body '{"enabled": true}'

# List breakout sessions
wxcli meetings list-breakout-sessions MEETING_ID --output json

# Update breakout sessions
wxcli meetings update-breakout-sessions MEETING_ID --json-body '{"items": [{"name": "Group A", "invitees": ["user1@example.com"]}]}'

# Delete breakout sessions
wxcli meetings delete-breakout-sessions MEETING_ID
```

---

### Participants

```bash
# List participants
wxcli meeting-participants list --meeting-id MEETING_ID --output json

# Query participants by email
wxcli meeting-participants create --json-body '{"meetingId": "MEETING_ID", "emails": ["user@example.com"]}'

# Get participant details
wxcli meeting-participants show PARTICIPANT_ID --output json

# Update a participant (mute/unmute, expel)
wxcli meeting-participants update PARTICIPANT_ID --json-body '{"muted": true}'

# Admit participants from lobby
wxcli meeting-participants create-admit --json-body '{"items": [{"id": "PARTICIPANT_ID"}]}'

# SIP callout
wxcli meeting-participants create-callout --json-body '{"meetingId": "MEETING_ID", "sipAddress": "sip:room@example.com"}'

# Cancel SIP callout
wxcli meeting-participants create-cancel-callout --json-body '{"meetingId": "MEETING_ID", "calloutId": "CALLOUT_ID"}'
```

---

### Invitees

```bash
# List invitees
wxcli meeting-invitees list --meeting-id MEETING_ID --output json

# Create an invitee
wxcli meeting-invitees create --json-body '{"meetingId": "MEETING_ID", "email": "user@example.com", "displayName": "Jane Doe"}'

# Batch create invitees
wxcli meeting-invitees create-bulk-insert --json-body '{"meetingId": "MEETING_ID", "items": [{"email": "user1@example.com"}, {"email": "user2@example.com"}]}'

# Update an invitee
wxcli meeting-invitees update INVITEE_ID --json-body '{"email": "user@example.com", "coHost": true}'

# Delete an invitee
wxcli meeting-invitees delete INVITEE_ID
```

---

### Transcripts and Content

```bash
# List transcripts (compliance — all meetings)
wxcli meeting-transcripts list --output json

# List transcripts for a specific meeting
wxcli meeting-transcripts list-meeting-transcripts --meeting-id MEETING_ID --output json

# Download a transcript
wxcli meeting-transcripts list-download TRANSCRIPT_ID --output json

# List transcript snippets
wxcli meeting-transcripts list-snippets TRANSCRIPT_ID --output json

# Get a specific snippet
wxcli meeting-transcripts show TRANSCRIPT_ID SNIPPET_ID --output json

# Update a snippet
wxcli meeting-transcripts update TRANSCRIPT_ID SNIPPET_ID --json-body '{"text": "corrected text"}'

# Delete a transcript
wxcli meeting-transcripts delete TRANSCRIPT_ID

# List captions
wxcli meeting-captions list-meeting-closed-captions MEETING_ID --output json

# List caption snippets
wxcli meeting-captions list CAPTION_ID --output json

# Download caption snippets
wxcli meeting-captions list-download CAPTION_ID --output json

# Get AI summary for a meeting
wxcli meeting-summaries list-meeting-summaries MEETING_ID --output json

# Get summary for compliance
wxcli meeting-summaries list --output json

# Delete a summary
wxcli meeting-summaries delete SUMMARY_ID

# List in-meeting chats
wxcli meeting-chats list --meeting-id MEETING_ID --output json

# Delete meeting chats
wxcli meeting-chats delete MEETING_ID

# Delete a meeting message
wxcli meeting-messages delete MESSAGE_ID
```

---

### Preferences and Settings

```bash
# Get full meeting preference details
wxcli meeting-preferences list-meeting-preferences --output json

# Get audio options
wxcli meeting-preferences show --output json

# Update audio options
wxcli meeting-preferences update --json-body '{"defaultAudioType": "webexAudio"}'

# Get video options
wxcli meeting-preferences list --output json

# Update video options
wxcli meeting-preferences update-video --json-body '{"videoEnabled": true}'

# Get scheduling options
wxcli meeting-preferences list-scheduling-options --output json

# Update scheduling options
wxcli meeting-preferences update-scheduling-options --json-body '{"enabledJoinBeforeHost": true}'

# Get personal meeting room options
wxcli meeting-preferences list-personal-meeting-room --output json

# Update personal meeting room
wxcli meeting-preferences update-personal-meeting-room --json-body '{"topic": "My Room"}'

# Batch refresh personal meeting room IDs
wxcli meeting-preferences create-refresh-id --json-body '{"items": [{"email": "user@example.com"}]}'

# List sites
wxcli meeting-preferences list-sites --output json

# Update default site
wxcli meeting-preferences update-sites --json-body '{"defaultSite": true, "siteUrl": "site.webex.com"}'

# Insert delegate emails
wxcli meeting-preferences create-insert --json-body '{"emails": ["delegate@example.com"]}'

# Delete delegate emails
wxcli meeting-preferences create --json-body '{"emails": ["delegate@example.com"]}'
```

---

### Tracking Codes, Session Types, Site Settings

```bash
# List tracking codes
wxcli meeting-tracking-codes list --output json

# Create a tracking code
wxcli meeting-tracking-codes create --json-body '{"name": "Department", "inputMode": "select", "options": [{"value": "Engineering"}, {"value": "Sales"}]}'

# Get a tracking code
wxcli meeting-tracking-codes show TRACKING_CODE_ID --output json

# Update a tracking code
wxcli meeting-tracking-codes update-tracking-codes TRACKING_CODE_ID --json-body '{"name": "Updated Name"}'

# Delete a tracking code
wxcli meeting-tracking-codes delete TRACKING_CODE_ID

# Get user tracking codes
wxcli meeting-tracking-codes list-tracking-codes --output json

# Update user tracking codes
wxcli meeting-tracking-codes update --json-body '{"values": [{"name": "Department", "value": "Engineering"}]}'

# List site session types
wxcli meeting-session-types list --output json

# List user session types
wxcli meeting-session-types list-session-types --output json

# Update user session types
wxcli meeting-session-types update --json-body '{"sessionTypes": [123, 456]}'

# Get site-wide meeting settings
wxcli meeting-site show --output json

# Update site-wide meeting settings
wxcli meeting-site update --json-body '{"defaultScheduledType": "meeting"}'
```

---

### Polls, Q&A, Reports

```bash
# List polls for a meeting
wxcli meeting-polls list-polls MEETING_ID --output json

# Get poll results
wxcli meeting-polls list MEETING_ID POLL_ID --output json

# List respondents for a poll question
wxcli meeting-polls list-respondents MEETING_ID POLL_ID QUESTION_ID --output json

# List Q&A for a meeting
wxcli meeting-qa list --meeting-id MEETING_ID --output json

# List answers for a question
wxcli meeting-qa list-answers QUESTION_ID --output json

# List meeting usage reports
wxcli meeting-reports list --output json

# List attendee reports
wxcli meeting-reports list-attendees --meeting-id MEETING_ID --output json

# List Slido compliance events
wxcli meeting-slido list --output json
```

---

### Surveys and Templates

```bash
# Get meeting survey
wxcli meetings list-survey MEETING_ID --output json

# List survey results
wxcli meetings list-survey-results MEETING_ID --output json

# Get survey links
wxcli meetings create-survey-links MEETING_ID --output json

# List meeting templates
wxcli meetings list-templates --output json

# Get a meeting template
wxcli meetings show TEMPLATE_ID --output json

# List invitation sources
wxcli meetings list-invitation-sources MEETING_ID --output json

# Create invitation sources
wxcli meetings create-invitation-sources MEETING_ID --json-body '{"items": [{"sourceType": "cisco"}]}'
```

---

### Deployment Plan Template

Before executing any commands, present the full plan to the user:

```
DEPLOYMENT PLAN
===============
Operation: [type — e.g., "Schedule recurring weekly meeting with 3 interpreters"]
Target: [meeting title / meeting ID / org-wide query]

Configuration:
  Meeting: [title]
  Time: [start] — [end]
  Timezone: [timezone]
  Type: [meeting / webinar / personalRoomMeeting]
  Host: [host email if admin operation]
  [Operation-specific settings listed here]

Prerequisites verified:
  ✓ Auth token verified
  ✓ Required scopes present
  ✓ [Site URL confirmed (if multi-site)]
  ✓ [Meeting exists (if updating/querying)]

Commands to execute:
  1. wxcli meetings create-meetings --title "..." --start ... --end ...
  2. wxcli meeting-invitees create-bulk-insert --json-body '...'
  3. wxcli meetings create-interpreters MEETING_ID --json-body '...'

Proceed? (yes/no)
```

**Wait for user confirmation before executing.**

---

## Step 6: Execute via wxcli

Run the commands in plan order. Capture IDs from each creation response to use in subsequent commands.

Handle errors explicitly:

**Generic errors:**
- **401/403**: Token expired or insufficient scopes — run `wxcli configure` to re-authenticate. Check scope table in Step 2.
- **404**: Meeting not found — verify the meeting ID is correct and the meeting hasn't ended/been deleted
- **400**: Validation error — read the error message and fix the parameter
- **429**: Rate limiting — add `sleep 1` between commands for bulk operations

**Meeting-specific errors:**
- **403 on admin operations:** Token missing admin scopes (`meeting:admin_*`). Re-authenticate with admin credentials.
- **404 on content endpoints (transcripts, captions, summaries):** The meeting hasn't ended yet, or the feature wasn't enabled during the meeting.
- **400 on create-meetings (missing start/end):** Scheduled meetings require both `--start` and `--end`. Only `personalRoomMeeting` can omit these.
- **400 on registration commands:** The meeting must have registration enabled first. Use `update-registration` to enable.
- **400 on interpreter create (duplicate language pair):** Each language pair can only have one interpreter. Check existing interpreters first.

---

## Step 7: Verify

After execution, fetch the details back and confirm:

```bash
# Verify a meeting was created/updated
wxcli meetings show-meetings MEETING_ID --output json

# Verify registrants
wxcli meetings list-registrants MEETING_ID --output json

# Verify interpreters
wxcli meetings list-interpreters MEETING_ID --output json

# Verify breakout sessions
wxcli meetings list-breakout-sessions MEETING_ID --output json

# Verify invitees
wxcli meeting-invitees list --meeting-id MEETING_ID --output json

# Verify participants (in-progress meeting)
wxcli meeting-participants list --meeting-id MEETING_ID --output json

# Verify preferences
wxcli meeting-preferences list-meeting-preferences --output json

# Verify tracking codes
wxcli meeting-tracking-codes list --output json

# Verify site settings
wxcli meeting-site show --output json
```

---

## Step 8: Report results

Present the operation results:

```
OPERATION COMPLETE
==================
Operation: [type]
Status: Success

Meeting: [title]
  ID: [meeting_id]
  Start: [start_time]
  End: [end_time]
  Host: [host_email]
  Password: [password]
  Join URL: [web_link]

Resources Created/Modified:
  - [Registrants: 5 approved]
  - [Interpreters: 2 (EN↔ES, EN↔FR)]
  - [Breakout sessions: 3]
  - [Invitees: 10 added]

Next steps:
  - [e.g., "Share the join URL with attendees"]
  - [e.g., "Configure breakout session assignments before the meeting"]
  - [e.g., "Download transcripts after the meeting ends"]
  - [e.g., "Review poll results after the meeting"]
```

---

## Critical Rules

1. **Always verify auth token and scopes** before any operation. Meeting operations fail silently or with confusing errors when scopes are missing.
2. **Always show the deployment plan** (Step 5) and wait for user confirmation before executing any create, update, or delete commands.
3. **Admin vs. user operations use different commands.** `list-meetings` returns the user's meetings; `list-meetings-admin` returns org-wide meetings. Same for `show-meetings` vs. `show-meetings-admin`.
4. **Meeting IDs can represent different objects.** A meeting series ID, a scheduled meeting ID, and a meeting instance ID are all valid `MEETING_ID` values but behave differently. The `current` parameter on `show-meetings` controls which instance is returned.
5. **Post-meeting content endpoints only work after the meeting ends.** Transcripts, captions, summaries, chats, polls, and Q&A are only available after the meeting concludes and processing completes (allow a few minutes).
6. **Registration must be enabled before managing registrants.** Use `meetings update-registration` to set up the registration form before adding registrants.
7. **Breakout sessions are replaced on update, not merged.** The `update-breakout-sessions` command replaces all breakout sessions — include all sessions in the payload, not just the one you want to change.
8. **Multi-site orgs must specify `--site-url`.** If the org has multiple Webex sites, meeting creation may fail without `--site-url`. Check available sites with `wxcli meeting-preferences list-sites`.
9. **Delegate operations use non-obvious command names.** Insert delegates = `meeting-preferences create-insert`. Delete delegates = `meeting-preferences create`. The `create` command on `meeting-preferences` actually deletes delegate emails (API design quirk).
10. **Complex meeting options require `--json-body`.** Meeting options (file transfer, chat, video, polling), attendee privileges, tracking codes, and recurrence patterns are nested objects that must be passed via `--json-body`.
11. **Cross-skill handoffs:**
    - Video Mesh monitoring → `video-mesh` skill
    - Real-time call control → `call-control` skill
    - Meeting recordings → `reporting` skill (for CDR/analytics) or `meeting-transcripts` group (for transcript management)
    - Webhooks for meeting events → `call-control` skill (webhook configuration)

---

## Context Compaction Recovery

If context compacts mid-execution, recover by:
1. Read the deployment plan from `docs/plans/` to recover what was planned
2. Check what has already been created:
   ```bash
   wxcli meetings list-meetings --from 2026-01-01T00:00:00Z --output json
   wxcli meeting-invitees list --meeting-id MEETING_ID --output json
   ```
3. Resume from the first incomplete step in the plan
