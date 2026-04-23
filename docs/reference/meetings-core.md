# Meetings: Core API — Schedule, Manage, and Control Meetings

Reference for the Webex Meetings core API. Covers the 46 commands in the `meetings` CLI group that a user or admin uses to create, schedule, manage, and control Webex meetings, webinars, and events. Includes meeting lifecycle, templates, controls, registration, interpreters, breakout sessions, surveys, and invitation sources. Sourced from the Webex Meetings API (OpenAPI spec: `specs/webex-meetings.json`).

## Sources

- OpenAPI spec: `specs/webex-meetings.json`
- [developer.webex.com Meetings API](https://developer.webex.com/docs/api/v1/meetings)

---

## Token Type Matrix

Check this matrix before running any meetings command. The wrong token type will produce a 403 or empty results.

| Operation | User Token | Admin Token | Notes |
|-----------|-----------|-------------|-------|
| Meeting CRUD (user endpoints) | Yes | No (use admin endpoints) | User sees only their own meetings |
| Meeting CRUD (admin endpoints) | No | Yes | Admin can query any user's meetings via `--host-email` |
| Join a meeting | Yes | No | Generates join/start links for the authenticated user |
| End a meeting | Yes | Yes (with `--host-email`) | Only the host or admin can end |
| Meeting controls | Yes (host only) | No | Lock, recording start/pause |
| Templates | Yes | Yes (with `--host-email`) | Templates are site-specific |
| Registration & registrants | Yes (host only) | Yes (with `--host-email`) | Only applies to webinar-type meetings |
| Interpreters | Yes (host only) | Yes (with `--host-email`) | Simultaneous interpretation setup |
| Breakout sessions | Yes (host only) | Yes (with `--host-email`) | Must be configured before meeting starts |
| Surveys | Yes | Yes (with `--host-email`) | Results available only after meeting ends |
| Session types | Yes | Yes (with `--host-email`) | Read-only; configured at site level |
| Tracking codes | Yes | Yes (with `--host-email`) | Read-only via meetings group; admin CRUD in meetings-settings |

---

## Table of Contents

1. [Meeting Data Model](#1-meeting-data-model)
2. [Meeting CRUD](#2-meeting-crud)
3. [Meeting Lifecycle](#3-meeting-lifecycle)
4. [Meeting Templates](#4-meeting-templates)
5. [Meeting Controls](#5-meeting-controls)
6. [Registration and Registrants](#6-registration-and-registrants)
7. [Interpreters and Simultaneous Interpretation](#7-interpreters-and-simultaneous-interpretation)
8. [Breakout Sessions](#8-breakout-sessions)
9. [Surveys](#9-surveys)
10. [Invitation Sources](#10-invitation-sources)
11. [Session Types and Tracking Codes](#11-session-types-and-tracking-codes)
12. [Raw HTTP Endpoints](#12-raw-http-endpoints)
13. [Gotchas](#13-gotchas)
14. [See Also](#14-see-also)

---

## 1. Meeting Data Model

A meeting object returned by the API contains these key fields:

```
Meeting
  ├── id                          Unique meeting ID
  ├── meetingSeriesId              Series ID (for recurring meetings)
  ├── scheduledMeetingId           Scheduled instance ID
  ├── meetingNumber                Numeric meeting number (used for dialing in)
  ├── title                        Meeting title
  ├── agenda                       Meeting agenda/description
  ├── start / end                  ISO 8601 start and end times
  ├── timezone                     Timezone for the meeting
  ├── state                        active | inactive | ended | missed | expired
  ├── meetingType                  meetingSeries | scheduledMeeting | meeting (instance)
  ├── scheduledType                meeting | webinar | personalRoomMeeting
  ├── hostEmail / hostDisplayName  Meeting host
  ├── hostUserId                   Host's Webex user ID
  ├── password                     Meeting password
  ├── webLink                      Join link
  ├── sipAddress                   SIP URI for video endpoints
  ├── dialInIpAddress              IP for H.323/SIP dial-in
  ├── telephony                    PSTN dial-in numbers
  ├── recurrence                   Recurrence rule (RFC 5545 RRULE)
  ├── meetingOptions               Chat, file transfer, video, polling settings
  ├── attendeePrivileges           Share, annotate, remote control permissions
  ├── registration                 Registration settings (webinar)
  ├── simultaneousInterpretation   Interpreter settings
  ├── trackingCodes                Array of tracking code name/value pairs
  ├── integrationTags              External integration keys
  ├── has* flags                   hasRecording, hasChat, hasTranscription, etc.
  └── links                        Related resource links
```

**Meeting ID types:** The `meetingId` parameter accepts three different ID types, and behavior changes depending on which is used:
- **Series ID** (`meetingSeriesId`) — represents the entire recurring series
- **Scheduled meeting ID** (`scheduledMeetingId`) — a specific occurrence in the series
- **Meeting instance ID** (`id`) — the actual meeting instance (only exists after meeting starts)

**Scheduled types:**
- `meeting` — standard Webex meeting
- `webinar` — webinar with registration, panelists, and attendee roles
- `personalRoomMeeting` — personal meeting room (PMR) meeting

---

## 2. Meeting CRUD

**CLI group:** `meetings`
**API base:** `https://webexapis.com/v1/meetings`

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| List meetings | `wxcli meetings list-meetings` | GET /meetings | List meetings for the authenticated user |
| Create meeting | `wxcli meetings create-meetings` | POST /meetings | Schedule a new meeting |
| Show meeting | `wxcli meetings show-meetings MEETING_ID` | GET /meetings/{meetingId} | Get meeting details |
| Update meeting (full) | `wxcli meetings update-meetings MEETING_ID` | PUT /meetings/{meetingId} | Replace all meeting fields |
| Update meeting (partial) | `wxcli meetings update-meetings-1 MEETING_ID` | PATCH /meetings/{meetingId} | Update only specified fields |
| Delete meeting | `wxcli meetings delete-meetings MEETING_ID` | DELETE /meetings/{meetingId} | Cancel/delete a meeting |
| List meetings (admin) | `wxcli meetings list-meetings-admin` | GET /admin/meetings | List any user's meetings (admin token) |
| Show meeting (admin) | `wxcli meetings show-meetings-admin MEETING_ID` | GET /admin/meetings/{meetingId} | Get any meeting's details (admin token) |

### Key Parameters

#### `meetings list-meetings`

| Option | Description |
|--------|-------------|
| `--meeting-number TEXT` | Filter by meeting number |
| `--web-link TEXT` | Filter by meeting join link (URL-encoded) |
| `--room-id TEXT` | Filter by associated Webex space ID |
| `--meeting-series-id TEXT` | Filter by series ID |
| `--meeting-type meetingSeries\|scheduledMeeting\|meeting` | Filter by meeting type |
| `--state active\|inactive\|ended\|missed\|expired` | Filter by state (default: all future meetings) |
| `--scheduled-type meeting\|webinar\|personalRoomMeeting` | Filter by scheduled type |
| `--is-modified` | Filter to modified scheduled meetings only |
| `--has-chat` | Filter to ended meetings with chat logs |
| `--has-recording` | Filter to ended meetings with recordings |
| `--has-transcription` | Filter to ended meetings with transcripts |
| `--has-summary` | Filter to ended meetings with AI summaries |
| `--has-closed-caption` | Filter to ended meetings with closed captions |
| `--has-polls` | Filter to ended meetings with polls |
| `--has-qa` | Filter to ended meetings with Q&A |
| `--has-slido` | Filter to ended meetings with Slido interactions |
| `--from DATETIME` | Start of time range (ISO 8601) |
| `--to DATETIME` | End of time range (ISO 8601) |
| `--host-email EMAIL` | Admin: query another user's meetings |
| `--site-url URL` | Webex site to query (default: user's default site) |
| `--current` | Return only the current scheduled meeting in a series |
| `--integration-tag TEXT` | Filter by integration application tag |
| `--max N` | API-level page size (up to 100) |
| `--output table\|json` | Output format |

#### `meetings create-meetings`

| Option | Required | Description |
|--------|:--------:|-------------|
| `--title TEXT` | Yes | Meeting title |
| `--start DATETIME` | Yes | Start time (ISO 8601) |
| `--end DATETIME` | Yes | End time (ISO 8601) |
| `--timezone TEXT` | No | Timezone (default: host's timezone) |
| `--agenda TEXT` | No | Meeting description/agenda |
| `--password TEXT` | No | Meeting password (auto-generated if omitted) |
| `--scheduled-type meeting\|webinar` | No | Meeting or webinar (default: meeting) |
| `--recurrence TEXT` | No | RFC 5545 RRULE for recurring meetings |
| `--template-id TEXT` | No | Apply a meeting template |
| `--session-type-id TEXT` | No | Session type (from list-session-types) |
| `--host-email EMAIL` | No | Admin: schedule on behalf of another user |
| `--site-url URL` | No | Webex site (default: host's default site) |
| `--invitees JSON` | No | Array of invitee objects (email, displayName, coHost) |
| `--send-email` | No | Send email invitations to invitees |
| `--enabled-join-before-host` | No | Allow attendees to join before host |
| `--join-before-host-minutes N` | No | Minutes before start that attendees can join |
| `--enabled-auto-record-meeting` | No | Auto-record the meeting |
| `--enabled-breakout-sessions` | No | Enable breakout session capability |
| `--enabled-webcast-view` | No | Enable webcast view for webinars |
| `--room-id TEXT` | No | Associate with a Webex space |
| `--json-body JSON` | No | Full JSON body (overrides all other options) |

#### `meetings update-meetings` (PUT — full replace)

Same options as `create-meetings`. All fields must be provided; omitted fields revert to defaults.

#### `meetings update-meetings-1` (PATCH — partial update)

Same options as `create-meetings`. Only provided fields are updated; omitted fields remain unchanged.

#### `meetings list-meetings-admin` / `meetings show-meetings-admin`

These admin endpoints accept the same filtering options as their user-level counterparts, plus:

| Option | Description |
|--------|-------------|
| `--host-email EMAIL` | Required for admin queries — specifies which user's meetings to list |

### Raw HTTP

```python
import requests

BASE = "https://webexapis.com/v1"
headers = {"Authorization": f"Bearer {token}"}

# List future meetings
resp = requests.get(f"{BASE}/meetings", headers=headers,
                    params={"from": "2026-03-01T00:00:00Z", "to": "2026-04-01T00:00:00Z"})
meetings = resp.json().get("items", [])
# Each item: {"id", "title", "start", "end", "meetingNumber", "webLink", "state", ...}

# Create a meeting
body = {
    "title": "Weekly Standup",
    "start": "2026-04-01T09:00:00-05:00",
    "end": "2026-04-01T09:30:00-05:00",
    "timezone": "America/Chicago",
    "sendEmail": True,
    "invitees": [
        {"email": "alice@example.com", "coHost": True},
        {"email": "bob@example.com"}
    ]
}
resp = requests.post(f"{BASE}/meetings", headers=headers, json=body)
meeting_id = resp.json().get("id")

# Get meeting details
resp = requests.get(f"{BASE}/meetings/{meeting_id}", headers=headers)

# Patch a meeting (partial update)
resp = requests.patch(f"{BASE}/meetings/{meeting_id}", headers=headers,
                      json={"title": "Updated Standup", "agenda": "Sprint review added"})

# Delete a meeting
resp = requests.delete(f"{BASE}/meetings/{meeting_id}", headers=headers)

# Admin: list another user's meetings
resp = requests.get(f"{BASE}/admin/meetings", headers=headers,
                    params={"hostEmail": "user@example.com", "from": "2026-03-01T00:00:00Z",
                            "to": "2026-04-01T00:00:00Z"})
```

### Gotchas

- **`update-meetings` (PUT) is a full replace.** Every field you omit reverts to its default. Use `update-meetings-1` (PATCH) for partial updates.
- **`list-meetings` defaults to future meetings only.** To see past meetings, you must provide `--from` and `--to`.
- **`state` filter only applies to certain meeting types.** For example, `ended` only applies to meeting instances, not series.
- **Creating a recurring meeting** uses RFC 5545 RRULE syntax: `--recurrence "FREQ=WEEKLY;COUNT=10;BYDAY=MO"`.

---

## 3. Meeting Lifecycle

Commands for joining, ending, and reassigning meetings.

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| Join meeting | `wxcli meetings create-join` | POST /meetings/join | Generate a join link for a meeting |
| End meeting | `wxcli meetings create-end MEETING_ID` | POST /meetings/{meetingId}/end | End an active meeting |
| Reassign host | `wxcli meetings create-reassign-host` | POST /meetings/reassignHost | Move all meetings from one host to another |

### Key Parameters

#### `meetings create-join`

| Option | Description |
|--------|-------------|
| `--meeting-id TEXT` | Join by meeting ID (use one of meetingId, meetingNumber, or webLink) |
| `--meeting-number TEXT` | Join by meeting number |
| `--web-link TEXT` | Join by meeting join link |
| `--email TEXT` | Email of the user joining |
| `--display-name TEXT` | Display name for the joining user |
| `--password TEXT` | Meeting password (required if meeting is password-protected) |
| `--expiration-minutes N` | Link expiration time in minutes |
| `--host-email TEXT` | Admin: join on behalf of another user |
| `--join-directly` | Join directly without lobby |
| `--registration-id TEXT` | Registration ID for webinar registrants |
| `--json-body JSON` | Full JSON body |

#### `meetings create-reassign-host`

| Option | Description |
|--------|-------------|
| `--current-host-email EMAIL` | Current host email (meetings will be moved FROM this user) |
| `--new-host-email EMAIL` | New host email (meetings will be moved TO this user) |

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"

# Join a meeting by meeting number
body = {
    "meetingNumber": "1234567890",
    "password": "Pa$$w0rd",
    "email": "user@example.com",
    "displayName": "John Doe"
}
resp = requests.post(f"{BASE}/meetings/join", headers=headers, json=body)
join_link = resp.json().get("joinLink")
start_link = resp.json().get("startLink")  # Only returned for hosts

# End an active meeting
resp = requests.post(f"{BASE}/meetings/{meeting_id}/end", headers=headers)

# Reassign all meetings to a new host
body = {
    "currentHostEmail": "leaving@example.com",
    "newHostEmail": "replacement@example.com"
}
resp = requests.post(f"{BASE}/meetings/reassignHost", headers=headers, json=body)
```

### Gotchas

- **`create-join` can use meetingId, meetingNumber, or webLink** — exactly one must be provided.
- **`create-join` returns different links for hosts vs attendees.** Hosts get both `joinLink` and `startLink`; attendees only get `joinLink`.
- **`create-end` only works on active (in-progress) meetings.** Calling it on a scheduled or ended meeting returns an error.
- **`create-reassign-host` moves ALL meetings** from the current host to the new host. There is no per-meeting reassignment via this endpoint.

---

## 4. Meeting Templates

Templates define default meeting settings (audio options, attendee privileges, meeting options) that can be applied when creating meetings.

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| List templates | `wxcli meetings list-templates` | GET /meetings/templates | List available meeting templates |
| Show template | `wxcli meetings show TEMPLATE_ID` | GET /meetings/templates/{templateId} | Get template details |

### Key Parameters

#### `meetings list-templates`

| Option | Description |
|--------|-------------|
| `--template-type TEXT` | Filter by template type |
| `--locale TEXT` | Locale for template names |
| `--is-default` | Filter to default templates only |
| `--is-standard` | Filter to standard (system) templates only |
| `--host-email EMAIL` | Admin: list templates available to another user |

#### `meetings show TEMPLATE_ID`

| Option | Description |
|--------|-------------|
| `--host-email EMAIL` | Admin: get template for another user |

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"

# List available templates
resp = requests.get(f"{BASE}/meetings/templates", headers=headers)
templates = resp.json().get("items", [])

# Get template details (includes full meeting defaults)
resp = requests.get(f"{BASE}/meetings/templates/{template_id}", headers=headers)
template = resp.json()
# Returns: meeting settings, meetingOptions, attendeePrivileges, trackingCodes, etc.
```

---

## 5. Meeting Controls

Real-time controls for an active meeting. Only the meeting host can use these.

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| Show controls | `wxcli meetings show-controls` | GET /meetings/controls | Get lock and recording status |
| Update controls | `wxcli meetings update` | PUT /meetings/controls | Lock/unlock meeting, start/pause recording |

### Key Parameters

#### `meetings show-controls`

| Option | Description |
|--------|-------------|
| `--meeting-id TEXT` | Meeting ID of the active meeting |

#### `meetings update` (meeting controls)

| Option | Description |
|--------|-------------|
| `--meeting-id TEXT` | Meeting ID of the active meeting (query parameter) |
| `--locked` | Lock or unlock the meeting |
| `--recording-started` | Start or stop recording |
| `--recording-paused` | Pause or resume recording |

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"

# Get meeting control status
resp = requests.get(f"{BASE}/meetings/controls", headers=headers,
                    params={"meetingId": meeting_id})
# Returns: {"locked": false, "recordingStarted": false, "recordingPaused": false}

# Lock the meeting and start recording
resp = requests.put(f"{BASE}/meetings/controls", headers=headers,
                    params={"meetingId": meeting_id},
                    json={"locked": True, "recordingStarted": True})
```

### Gotchas

- **Only works on active (in-progress) meetings.** Returns an error if the meeting has not started or has already ended.
- **Only the host can control the meeting.** Co-hosts may have limited control depending on site settings.
- **`recordingStarted` and `recordingPaused` are independent.** You can pause a recording without stopping it.

---

## 6. Registration and Registrants

Registration forms and registrant management for webinar-type meetings. These endpoints only apply when the meeting has registration enabled (typically webinars).

### Registration Form Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| Get form | `wxcli meetings list-registration MEETING_ID` | GET /meetings/{meetingId}/registration | Get the registration form configuration |
| Update form | `wxcli meetings update-registration MEETING_ID` | PUT /meetings/{meetingId}/registration | Configure registration form fields |
| Delete form | `wxcli meetings delete MEETING_ID` | DELETE /meetings/{meetingId}/registration | Remove registration form |

### Registrant Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| List registrants | `wxcli meetings list-registrants MEETING_ID` | GET /meetings/{meetingId}/registrants | List all registrants |
| Register one | `wxcli meetings create MEETING_ID` | POST /meetings/{meetingId}/registrants | Register a single person |
| Batch register | `wxcli meetings create-bulk-insert MEETING_ID` | POST /meetings/{meetingId}/registrants/bulkInsert | Register multiple people at once |
| Show registrant | `wxcli meetings show-registrants MEETING_ID REGISTRANT_ID` | GET /meetings/{meetingId}/registrants/{registrantId} | Get registrant details |
| Update registrant | `wxcli meetings create-registrants MEETING_ID REGISTRANT_ID` | POST /meetings/{meetingId}/registrants/{registrantId} | Update registrant status |
| Delete registrant | `wxcli meetings delete-registrants MEETING_ID REGISTRANT_ID` | DELETE /meetings/{meetingId}/registrants/{registrantId} | Remove a registrant |
| Query registrants | `wxcli meetings create-query MEETING_ID` | POST /meetings/{meetingId}/registrants/query | Query registrants with filters |
| Batch approve | `wxcli meetings create-approve MEETING_ID` | POST /meetings/{meetingId}/registrants/approve | Approve multiple registrants |
| Batch reject | `wxcli meetings create-reject MEETING_ID` | POST /meetings/{meetingId}/registrants/reject | Reject multiple registrants |
| Batch cancel | `wxcli meetings create-cancel MEETING_ID` | POST /meetings/{meetingId}/registrants/cancel | Cancel multiple registrations |
| Batch delete | `wxcli meetings create-bulk-delete MEETING_ID` | POST /meetings/{meetingId}/registrants/bulkDelete | Delete multiple registrants |

### Key Parameters

#### `meetings update-registration`

| Option | Description |
|--------|-------------|
| `--auto-accept-request` | Automatically approve registrants (no manual review) |
| `--max-register-num N` | Maximum number of registrants allowed |
| `--require-first-name` | Require first name on the form |
| `--require-last-name` | Require last name on the form |
| `--require-email` | Require email on the form |
| `--require-company-name` | Require company name |
| `--require-job-title` | Require job title |
| `--require-work-phone` | Require work phone number |
| `--require-address-1` | Require address line 1 |
| `--require-city` | Require city |
| `--require-state` | Require state/province |
| `--require-zip-code` | Require postal code |
| `--require-country-region` | Require country/region |
| `--host-email EMAIL` | Admin: configure for another user's meeting |
| `--json-body JSON` | Full JSON body (required for customizedQuestions and rules) |

#### `meetings create` (register a single registrant)

| Option | Description |
|--------|-------------|
| `--first-name TEXT` | Registrant's first name |
| `--last-name TEXT` | Registrant's last name |
| `--email TEXT` | Registrant's email |
| `--send-email` | Send confirmation email |
| `--json-body JSON` | Full JSON body (for custom question answers) |

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"

# Get registration form
resp = requests.get(f"{BASE}/meetings/{meeting_id}/registration", headers=headers)

# Update registration form with custom questions
body = {
    "autoAcceptRequest": True,
    "maxRegisterNum": 500,
    "requireFirstName": "required",
    "requireLastName": "required",
    "requireEmail": "required",
    "requireCompanyName": "required",
    "customizedQuestions": [
        {"question": "What is your role?", "type": "singleLineTextBox", "required": True}
    ]
}
resp = requests.put(f"{BASE}/meetings/{meeting_id}/registration", headers=headers, json=body)

# Register a person
body = {"firstName": "Jane", "lastName": "Doe", "email": "jane@example.com", "sendEmail": True}
resp = requests.post(f"{BASE}/meetings/{meeting_id}/registrants", headers=headers, json=body)
registrant_id = resp.json().get("id")

# Batch approve registrants
body = {"registrantIds": [registrant_id_1, registrant_id_2]}
resp = requests.post(f"{BASE}/meetings/{meeting_id}/registrants/approve", headers=headers, json=body)

# Query registrants by status
body = {"status": "pending"}
resp = requests.post(f"{BASE}/meetings/{meeting_id}/registrants/query", headers=headers, json=body)
```

### Gotchas

- **Registration only applies to webinar-type meetings.** Standard meetings do not support registration forms.
- **`create-registrants` (POST to `/{registrantId}`) is a status update, not a create.** Despite the CLI name, this updates an existing registrant's status (approve/reject/cancel).
- **`delete` (registration form) uses a bare command name** because it maps to `DELETE /meetings/{meetingId}/registration` — not to be confused with `delete-meetings` which deletes the meeting itself.
- **Batch operations (approve, reject, cancel, bulkDelete) accept arrays of registrant IDs** via `--json-body`.
- **Custom questions and rules require `--json-body`** — the CLI does not expose individual flags for nested question objects.

---

## 7. Interpreters and Simultaneous Interpretation

Manage interpreters for multilingual meetings. Interpreters provide real-time translation between language channels.

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| List interpreters | `wxcli meetings list-interpreters MEETING_ID` | GET /meetings/{meetingId}/interpreters | List all interpreters for a meeting |
| Create interpreter | `wxcli meetings create-interpreters MEETING_ID` | POST /meetings/{meetingId}/interpreters | Add an interpreter |
| Show interpreter | `wxcli meetings show-interpreters MEETING_ID INTERPRETER_ID` | GET /meetings/{meetingId}/interpreters/{interpreterId} | Get interpreter details |
| Update interpreter | `wxcli meetings update-interpreters MEETING_ID INTERPRETER_ID` | PUT /meetings/{meetingId}/interpreters/{interpreterId} | Update interpreter assignment |
| Delete interpreter | `wxcli meetings delete-interpreters MEETING_ID INTERPRETER_ID` | DELETE /meetings/{meetingId}/interpreters/{interpreterId} | Remove an interpreter |
| Update SI settings | `wxcli meetings update-simultaneous-interpretation MEETING_ID` | PUT /meetings/{meetingId}/simultaneousInterpretation | Update overall SI configuration |

### Key Parameters

#### `meetings create-interpreters`

| Option | Description |
|--------|-------------|
| `--email TEXT` | Interpreter's email address |
| `--display-name TEXT` | Interpreter's display name |
| `--language-code-1 TEXT` | First language code (e.g., "en") |
| `--language-code-2 TEXT` | Second language code (e.g., "es") |
| `--host-email EMAIL` | Admin: add interpreter to another user's meeting |
| `--send-email` | Send invitation email to the interpreter |

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"

# List interpreters
resp = requests.get(f"{BASE}/meetings/{meeting_id}/interpreters", headers=headers)
interpreters = resp.json().get("items", [])

# Add an interpreter (English <-> Spanish)
body = {
    "email": "interpreter@example.com",
    "displayName": "Maria Garcia",
    "languageCode1": "en",
    "languageCode2": "es",
    "sendEmail": True
}
resp = requests.post(f"{BASE}/meetings/{meeting_id}/interpreters", headers=headers, json=body)

# Update simultaneous interpretation settings
body = {"enabled": True}
resp = requests.put(f"{BASE}/meetings/{meeting_id}/simultaneousInterpretation",
                    headers=headers, json=body)
```

### Gotchas

- **Language codes use ISO 639-1 format** (e.g., "en", "es", "fr", "de", "zh", "ja").
- **Interpreters must be added before the meeting starts.** You cannot add interpreters to an active meeting via API.
- **`update-simultaneous-interpretation` controls the overall SI feature toggle** — it enables/disables SI for the meeting, separate from individual interpreter CRUD.

---

## 8. Breakout Sessions

Breakout sessions split a meeting into smaller sub-groups. They must be configured before the meeting starts.

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| List breakout sessions | `wxcli meetings list-breakout-sessions MEETING_ID` | GET /meetings/{meetingId}/breakoutSessions | List all breakout sessions |
| Update breakout sessions | `wxcli meetings update-breakout-sessions MEETING_ID` | PUT /meetings/{meetingId}/breakoutSessions | Create or update breakout sessions |
| Delete breakout sessions | `wxcli meetings delete-breakout-sessions MEETING_ID` | DELETE /meetings/{meetingId}/breakoutSessions | Remove all breakout sessions |

### Key Parameters

#### `meetings update-breakout-sessions`

| Option | Description |
|--------|-------------|
| `--host-email EMAIL` | Admin: configure for another user's meeting |
| `--send-email` | Send notification emails |
| `--json-body JSON` | Full JSON body with breakout session items (required) |

The `items` array in the JSON body defines the breakout sessions:

```json
{
    "items": [
        {
            "name": "Group A",
            "invitees": ["alice@example.com", "bob@example.com"]
        },
        {
            "name": "Group B",
            "invitees": ["charlie@example.com", "dana@example.com"]
        }
    ],
    "sendEmail": true
}
```

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"

# List breakout sessions
resp = requests.get(f"{BASE}/meetings/{meeting_id}/breakoutSessions", headers=headers)
sessions = resp.json().get("items", [])

# Create/update breakout sessions
body = {
    "items": [
        {"name": "Engineering", "invitees": ["eng1@example.com", "eng2@example.com"]},
        {"name": "Marketing", "invitees": ["mkt1@example.com", "mkt2@example.com"]}
    ],
    "sendEmail": True
}
resp = requests.put(f"{BASE}/meetings/{meeting_id}/breakoutSessions", headers=headers, json=body)

# Delete all breakout sessions
resp = requests.delete(f"{BASE}/meetings/{meeting_id}/breakoutSessions", headers=headers)
```

### Gotchas

- **Breakout sessions must be configured before the meeting starts.** The API does not support creating breakout sessions during an active meeting.
- **`update-breakout-sessions` (PUT) is a full replace** — it replaces all existing breakout sessions with the provided set.
- **`delete-breakout-sessions` removes ALL breakout sessions** for the meeting. There is no per-session delete.
- **`enabledBreakoutSessions` must be `true` on the meeting** (set during create or update) for breakout sessions to work.
- **Breakout session configuration requires `--json-body`** because the items array is a nested structure.

---

## 9. Surveys

Retrieve meeting surveys and survey results. Surveys are configured in the Webex meeting client, not via API — these endpoints only read the survey definition and collect results after the meeting ends.

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| Get survey | `wxcli meetings list-survey MEETING_ID` | GET /meetings/{meetingId}/survey | Get the survey definition for a meeting |
| List survey results | `wxcli meetings list-survey-results MEETING_ID` | GET /meetings/{meetingId}/surveyResults | List survey responses from attendees |
| Get survey links | `wxcli meetings create-survey-links MEETING_ID` | POST /meetings/{meetingId}/surveyLinks | Generate shareable survey links |

### Key Parameters

#### `meetings list-survey-results`

| Option | Description |
|--------|-------------|
| `--meeting-id TEXT` | Meeting ID (required) |
| `--max N` | API-level page size |
| `--output table\|json` | Output format |

#### `meetings create-survey-links`

| Option | Description |
|--------|-------------|
| `--meeting-id TEXT` | Meeting ID (required) |
| `--host-email EMAIL` | Admin: generate links for another user's meeting |
| `--json-body JSON` | Full JSON body |

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"

# Get survey definition
resp = requests.get(f"{BASE}/meetings/{meeting_id}/survey", headers=headers)
survey = resp.json()
# Returns: questions, options, survey settings

# List survey results (after meeting ends)
resp = requests.get(f"{BASE}/meetings/{meeting_id}/surveyResults", headers=headers)
results = resp.json().get("items", [])

# Generate survey links
resp = requests.post(f"{BASE}/meetings/{meeting_id}/surveyLinks", headers=headers)
links = resp.json()
```

### Gotchas

- **Survey results are only available after the meeting ends.** Querying during an active meeting returns empty results.
- **Surveys are configured in the Webex meeting client**, not via this API. These endpoints are read-only (survey definition) plus link generation.

---

## 10. Invitation Sources

Track where meeting invitations were sent from (e.g., calendar integrations, email clients). This is a tracking/analytics feature.

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| List sources | `wxcli meetings list-invitation-sources MEETING_ID` | GET /meetings/{meetingId}/invitationSources | List invitation sources for a meeting |
| Create sources | `wxcli meetings create-invitation-sources MEETING_ID` | POST /meetings/{meetingId}/invitationSources | Record an invitation source |

### Key Parameters

#### `meetings create-invitation-sources`

| Option | Description |
|--------|-------------|
| `--host-email EMAIL` | Admin: create for another user's meeting |
| `--person-id TEXT` | Person who sent the invitation |
| `--json-body JSON` | Full JSON body with items array |

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"

# List invitation sources
resp = requests.get(f"{BASE}/meetings/{meeting_id}/invitationSources", headers=headers)
sources = resp.json().get("items", [])

# Record an invitation source
body = {
    "personId": person_id,
    "items": [{"sourceType": "email", "sourceId": "outlook"}]
}
resp = requests.post(f"{BASE}/meetings/{meeting_id}/invitationSources", headers=headers, json=body)
```

---

## 11. Session Types and Tracking Codes

These are read-only configuration endpoints. Session types define what meeting capabilities are available (based on Webex site configuration). Tracking codes are metadata tags applied to meetings for reporting and compliance.

**Note:** Admin-level CRUD for session types and tracking codes is in the `meeting-config` and `meeting-user-config` CLI groups, documented in `meetings-settings.md`.

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| List session types | `wxcli meetings list-session-types` | GET /meetings/sessionTypes | List available session types |
| Show session type | `wxcli meetings show-session-types SESSION_TYPE_ID` | GET /meetings/sessionTypes/{sessionTypeId} | Get session type details |
| List tracking codes | `wxcli meetings list` | GET /meetings/trackingCodes | List tracking codes for the site |

### Key Parameters

#### `meetings list-session-types`

| Option | Description |
|--------|-------------|
| `--host-email EMAIL` | Admin: list session types for another user |
| `--site-url URL` | Webex site to query |

#### `meetings list` (tracking codes)

| Option | Description |
|--------|-------------|
| `--host-email EMAIL` | Admin: list tracking codes for another user |
| `--site-url URL` | Webex site to query |

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"

# List session types
resp = requests.get(f"{BASE}/meetings/sessionTypes", headers=headers)
session_types = resp.json().get("items", [])
# Each item: {"id", "name", "type", "subType", ...}

# Get session type details
resp = requests.get(f"{BASE}/meetings/sessionTypes/{session_type_id}", headers=headers)

# List tracking codes
resp = requests.get(f"{BASE}/meetings/trackingCodes", headers=headers)
tracking_codes = resp.json().get("items", [])
# Each item: {"name", "value", ...}
```

### Gotchas

- **Session types are configured at the Webex site level.** You cannot create or modify session types via the meetings API — use the admin `meeting-config` group.
- **`meetings list` maps to tracking codes** (GET /meetings/trackingCodes), which can be confusing since `meetings list-meetings` maps to GET /meetings. Use `--help` to verify.
- **Tracking codes vary by site.** Different Webex sites in the same org may have different tracking codes configured.

---

## 12. Raw HTTP Endpoints

Complete table of all 46 endpoints in the `meetings` CLI group.

| HTTP Method | Path | CLI Command | Summary |
|-------------|------|-------------|---------|
| GET | /meetings | `list-meetings` | List Meetings |
| POST | /meetings | `create-meetings` | Create a Meeting |
| GET | /meetings/{meetingId} | `show-meetings` | Get a Meeting |
| PUT | /meetings/{meetingId} | `update-meetings` | Update a Meeting (full replace) |
| PATCH | /meetings/{meetingId} | `update-meetings-1` | Patch a Meeting (partial update) |
| DELETE | /meetings/{meetingId} | `delete-meetings` | Delete a Meeting |
| GET | /admin/meetings | `list-meetings-admin` | List Meetings By an Admin |
| GET | /admin/meetings/{meetingId} | `show-meetings-admin` | Get a Meeting By an Admin |
| POST | /meetings/join | `create-join` | Join a Meeting |
| POST | /meetings/{meetingId}/end | `create-end` | End a Meeting |
| POST | /meetings/reassignHost | `create-reassign-host` | Reassign Meetings to a New Host |
| GET | /meetings/templates | `list-templates` | List Meeting Templates |
| GET | /meetings/templates/{templateId} | `show` | Get a Meeting Template |
| GET | /meetings/controls | `show-controls` | Get Meeting Control Status |
| PUT | /meetings/controls | `update` | Update Meeting Control Status |
| GET | /meetings/{meetingId}/registration | `list-registration` | Get Registration Form |
| PUT | /meetings/{meetingId}/registration | `update-registration` | Update Meeting Registration Form |
| DELETE | /meetings/{meetingId}/registration | `delete` | Delete Meeting Registration Form |
| GET | /meetings/{meetingId}/registrants | `list-registrants` | List Meeting Registrants |
| POST | /meetings/{meetingId}/registrants | `create` | Register a Meeting Registrant |
| POST | /meetings/{meetingId}/registrants/bulkInsert | `create-bulk-insert` | Batch Register Meeting Registrants |
| GET | /meetings/{meetingId}/registrants/{registrantId} | `show-registrants` | Get Registrant Details |
| POST | /meetings/{meetingId}/registrants/{registrantId} | `create-registrants` | Batch Update Registrant Status |
| DELETE | /meetings/{meetingId}/registrants/{registrantId} | `delete-registrants` | Delete a Meeting Registrant |
| POST | /meetings/{meetingId}/registrants/query | `create-query` | Query Meeting Registrants |
| POST | /meetings/{meetingId}/registrants/approve | `create-approve` | Batch Approve Meeting Registrants |
| POST | /meetings/{meetingId}/registrants/reject | `create-reject` | Batch Reject Meeting Registrants |
| POST | /meetings/{meetingId}/registrants/cancel | `create-cancel` | Batch Cancel Meeting Registrants |
| POST | /meetings/{meetingId}/registrants/bulkDelete | `create-bulk-delete` | Batch Delete Meeting Registrants |
| GET | /meetings/{meetingId}/interpreters | `list-interpreters` | List Meeting Interpreters |
| POST | /meetings/{meetingId}/interpreters | `create-interpreters` | Create a Meeting Interpreter |
| GET | /meetings/{meetingId}/interpreters/{interpreterId} | `show-interpreters` | Get a Meeting Interpreter |
| PUT | /meetings/{meetingId}/interpreters/{interpreterId} | `update-interpreters` | Update a Meeting Interpreter |
| DELETE | /meetings/{meetingId}/interpreters/{interpreterId} | `delete-interpreters` | Delete a Meeting Interpreter |
| PUT | /meetings/{meetingId}/simultaneousInterpretation | `update-simultaneous-interpretation` | Update Simultaneous Interpretation |
| GET | /meetings/{meetingId}/breakoutSessions | `list-breakout-sessions` | List Meeting Breakout Sessions |
| PUT | /meetings/{meetingId}/breakoutSessions | `update-breakout-sessions` | Update Meeting Breakout Sessions |
| DELETE | /meetings/{meetingId}/breakoutSessions | `delete-breakout-sessions` | Delete Meeting Breakout Sessions |
| GET | /meetings/{meetingId}/survey | `list-survey` | Get a Meeting Survey |
| GET | /meetings/{meetingId}/surveyResults | `list-survey-results` | List Meeting Survey Results |
| POST | /meetings/{meetingId}/surveyLinks | `create-survey-links` | Get Meeting Survey Links |
| GET | /meetings/{meetingId}/invitationSources | `list-invitation-sources` | List Invitation Sources |
| POST | /meetings/{meetingId}/invitationSources | `create-invitation-sources` | Create Invitation Sources |
| GET | /meetings/sessionTypes | `list-session-types` | List Meeting Session Types |
| GET | /meetings/sessionTypes/{sessionTypeId} | `show-session-types` | Get a Meeting Session Type |
| GET | /meetings/trackingCodes | `list` | List Meeting Tracking Codes |

---

## 13. Gotchas

These issues span multiple meetings API surfaces. Check per-section Gotchas for endpoint-specific notes.

1. **Admin endpoints (`/admin/meetings`) require an admin token; user endpoints require a user token.** Admin tokens cannot access `/meetings` (user-scoped). User tokens cannot access `/admin/meetings`. The admin endpoints mirror the user endpoints but accept `--host-email` to query any user's meetings.

2. **`meetingId` can be a series ID, scheduled meeting ID, or meeting instance ID — behavior differs.** When you pass a series ID, the API returns the series-level data. When you pass a scheduled meeting ID, you get that specific occurrence. When you pass a meeting instance ID, you get the actual meeting that ran (with attendee counts, duration, etc.). Use `meetingType` to understand which type you received.

3. **`list-meetings` defaults to returning future meetings only.** If you do not specify `--from` and `--to`, the API returns only upcoming scheduled meetings. To see historical meetings, you must explicitly provide a date range. The maximum range is 90 days per query.

4. **`update-meetings` (PUT) replaces all fields; `update-meetings-1` (PATCH) updates only specified fields.** Always use PATCH for partial updates. PUT with missing fields will reset those fields to defaults, potentially removing invitees, agenda text, and other configuration.

5. **`create-join` can join by meetingId, meetingNumber, or webLink — exactly one must be provided.** If you pass multiple, the API returns an error. The `webLink` value must be URL-encoded.

6. **Registration and registrants only apply to webinar-type meetings.** Attempting to configure registration on a standard meeting type returns an error. Set `--scheduled-type webinar` when creating the meeting.

7. **Breakout sessions must be created before the meeting starts.** The API does not support creating or modifying breakout sessions during an active meeting. Plan your breakout configuration during meeting scheduling.

8. **Survey results are only available after the meeting ends.** The `list-survey-results` endpoint returns empty results for active or scheduled meetings. Similarly, `has*` filter flags (`--has-recording`, `--has-chat`, etc.) only apply to ended meeting instances.

9. **The `--host-email` parameter is the admin override mechanism.** Admin-scoped endpoints require `--host-email` to specify which user's meetings to operate on. Without it, the API operates on the authenticated admin's own meetings (if they have a Webex Meetings license) or returns an error.

10. **Passwords may be auto-generated.** If you do not provide `--password` when creating a meeting, the API generates one based on site password policy. The password is returned in the create response and in subsequent GET calls.

11. **Recurring meeting operations.** When updating or deleting a recurring meeting using the series ID, the change applies to ALL future occurrences. To modify a single occurrence, use the scheduled meeting ID for that specific occurrence.

12. **Site URL matters for multi-site orgs.** Organizations with multiple Webex sites (e.g., `site1.webex.com` and `site2.webex.com`) must specify `--site-url` to target the correct site. The default is the user's primary site.

13. **CLI command name collisions.** Several commands have generic names (`list`, `create`, `delete`, `show`, `update`) that map to non-obvious endpoints. For example, `meetings list` maps to tracking codes (GET /meetings/trackingCodes), not meeting listing. `meetings delete` maps to registration form deletion. Always check `wxcli meetings <command> --help` to verify which endpoint a command targets.

---

## 14. See Also

- `meetings-content.md` — Meeting content: recordings, transcripts, closed captions, chat, polls, Q&A, summaries
- `meetings-settings.md` — Meeting preferences, site configuration, session types (admin CRUD), tracking codes (admin CRUD), common settings
- `meetings-infrastructure.md` — Meeting participants, invitees, reports, Video Mesh, Slido compliance
- [`admin-hybrid.md`](admin-hybrid.md) — Meeting quality metrics (`GET /meeting/qualities`), hybrid analytics
- [`admin-apps-data.md`](admin-apps-data.md) — Admin/group recordings, soft-delete/restore/purge, access lists
- [`authentication.md`](authentication.md) — Token types (user, admin), scopes, OAuth flows
- [`webhooks-events.md`](webhooks-events.md) — Webhook events for meeting lifecycle (meeting started, ended, participant joined/left)
