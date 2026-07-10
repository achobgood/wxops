# Meetings: Transcripts, Captions, Chats, and Summaries

Reference for Webex Meetings content and media APIs. Covers the 16 commands across 5 CLI groups that an admin, compliance officer, or meeting host uses to retrieve, download, and manage meeting transcripts, closed captions, post-meeting chats, in-meeting messages, and AI-generated summaries. Sourced from the Webex Meetings API (OpenAPI spec: `specs/webex-meetings.json`).

## Sources

- OpenAPI spec: `specs/webex-meetings.json`
- [developer.webex.com Meetings APIs](https://developer.webex.com/docs/api/v1/meeting-transcripts)

---

## Table of Contents

1. [Content Model Overview](#1-content-model-overview)
2. [Transcripts](#2-transcripts)
3. [Closed Captions](#3-closed-captions)
4. [Chats](#4-chats)
5. [Meeting Messages](#5-meeting-messages)
6. [Summaries](#6-summaries)
7. [Recordings (Cross-Reference)](#7-recordings-cross-reference)
8. [Raw HTTP Endpoints](#8-raw-http-endpoints)
9. [Gotchas](#9-gotchas)
10. [See Also](#10-see-also)

---

## 1. Content Model Overview

Every Webex meeting can produce multiple content artifacts. These become available after the meeting ends (with the exception of in-meeting messages, which exist during the meeting).

```
Meeting Instance (ended)
  ├── Transcripts       ← speech-to-text of the full meeting audio
  │    └── Snippets     ← individual speaker segments within a transcript
  ├── Closed Captions   ← real-time captions captured during the meeting
  │    └── Snippets     ← individual caption segments
  ├── Post-Meeting Chats ← chat messages sent during the meeting
  ├── Meeting Messages   ← in-meeting chat (compliance deletion only)
  └── Summaries          ← AI-generated meeting summary (requires AI Assistant)
```

**Key distinctions:**
- **Transcripts** are generated after the meeting from the recorded audio. They contain speaker-attributed text segments (snippets) and can be downloaded as VTT or TXT files.
- **Closed captions** are captured in real-time during the meeting. They are separate from transcripts and have their own snippet/download endpoints.
- **Post-meeting chats** (`postMeetingChats`) are the chat messages participants sent during the meeting, made available after the meeting ends.
- **Meeting messages** are a compliance-only deletion endpoint for removing specific messages from a meeting's chat history.
- **Summaries** are AI-generated meeting summaries that require the Webex AI Assistant feature to be enabled in the org.

**Token type requirements:**
- Most endpoints work with **user tokens** (meeting host or attendee).
- Compliance endpoints at `/admin/meetingTranscripts` and `/admin/meetingSummaries` require **admin tokens** with compliance officer scopes.
- The `hostEmail` parameter on several endpoints allows an admin to act on behalf of a specific host.

**CLI groups in this doc:**

| CLI Group | Resource | Commands |
|-----------|----------|---------|
| `meeting-transcripts` | Transcripts + snippets | 7 |
| `meeting-captions` | Closed captions + snippets | 3 |
| `meeting-chats` | Post-meeting chats | 2 |
| `meeting-messages` | In-meeting messages (compliance) | 1 |
| `meeting-summaries` | AI-generated summaries | 3 |

---

## 2. Transcripts

**CLI group:** `meeting-transcripts`
**API base:** `https://webexapis.com/v1/meetingTranscripts`

Transcripts provide speech-to-text content for ended meetings. Each transcript is composed of snippets — individual speaker segments with timestamps. Two list endpoints exist: one for regular users (scoped to their meetings) and one for compliance officers (org-wide).

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| List (compliance) | `wxcli meeting-transcripts list` | GET /admin/meetingTranscripts | List transcripts org-wide (compliance officer) |
| List (user) | `wxcli meeting-transcripts list-meeting-transcripts` | GET /meetingTranscripts | List transcripts for the authenticated user's meetings |
| Download | `wxcli meeting-transcripts list-download TRANSCRIPT_ID` | GET /meetingTranscripts/{transcriptId}/download | Download transcript as VTT or TXT |
| List snippets | `wxcli meeting-transcripts list-snippets TRANSCRIPT_ID` | GET /meetingTranscripts/{transcriptId}/snippets | List speaker segments in a transcript |
| Show snippet | `wxcli meeting-transcripts show TRANSCRIPT_ID SNIPPET_ID` | GET /meetingTranscripts/{transcriptId}/snippets/{snippetId} | Get a single snippet's details |
| Update snippet | `wxcli meeting-transcripts update TRANSCRIPT_ID SNIPPET_ID` | PUT /meetingTranscripts/{transcriptId}/snippets/{snippetId} | Edit the text of a snippet (corrections) |
| Delete | `wxcli meeting-transcripts delete TRANSCRIPT_ID` | DELETE /meetingTranscripts/{transcriptId} | Delete a transcript |

### Key Parameters

#### `meeting-transcripts list` (compliance)

| Option | Description |
|--------|-------------|
| `--from DATETIME` | Starting date/time (inclusive), ISO 8601 |
| `--to DATETIME` | Ending date/time (exclusive), ISO 8601 |
| `--max N` | Page size (1-100) |
| `--site-url URL` | Webex site URL to scope the query |

#### `meeting-transcripts list-meeting-transcripts` (user)

| Option | Description |
|--------|-------------|
| `--meeting-id ID` | Filter to a specific meeting instance. If omitted, returns transcripts for all of the user's meetings |
| `--host-email EMAIL` | Act on behalf of this host (admin token + admin scopes required) |
| `--site-url URL` | Webex site URL. Defaults to user's preferred site |
| `--from DATETIME` | Starting date/time (inclusive), ISO 8601 |
| `--to DATETIME` | Ending date/time (exclusive), ISO 8601 |
| `--max N` | Page size (1-100) |

#### `meeting-transcripts list-download`

| Option | Description |
|--------|-------------|
| `--format FORMAT` | Download format: `vtt` or `txt` |
| `--host-email EMAIL` | Act on behalf of this host (admin token + admin scopes required) |

#### `meeting-transcripts list-snippets`

| Option | Description |
|--------|-------------|
| `--max N` | Maximum snippet items per page |

#### `meeting-transcripts update`

| Option | Description |
|--------|-------------|
| `--reason TEXT` | Reason for the edit |
| `--text TEXT` | Corrected text for the snippet |

#### `meeting-transcripts delete`

| Option | Description |
|--------|-------------|
| `--reason TEXT` | Reason for the deletion |
| `--comment TEXT` | Additional comment |

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"
headers = {"Authorization": f"Bearer {token}"}

# List transcripts for a specific meeting (user token)
resp = requests.get(f"{BASE}/meetingTranscripts",
    headers=headers,
    params={"meetingId": meeting_id})
transcripts = resp.json().get("items", [])
# Each item: {"id", "meetingId", "hostEmail", "siteUrl", "startDate", "endDate", ...}

# List transcripts org-wide (compliance officer / admin token)
resp = requests.get(f"{BASE}/admin/meetingTranscripts",
    headers=headers,
    params={"from": "2026-03-01T00:00:00Z", "to": "2026-03-28T00:00:00Z"})
transcripts = resp.json().get("items", [])

# Download a transcript as VTT
resp = requests.get(f"{BASE}/meetingTranscripts/{transcript_id}/download",
    headers=headers,
    params={"format": "vtt"})
# resp.text contains the raw VTT file content (NOT JSON)
with open("transcript.vtt", "w") as f:
    f.write(resp.text)

# List snippets (speaker segments) in a transcript
resp = requests.get(f"{BASE}/meetingTranscripts/{transcript_id}/snippets",
    headers=headers)
snippets = resp.json().get("items", [])
# Each snippet: {"id", "text", "personName", "personEmail", "startTime", "endTime", ...}

# Get a single snippet
resp = requests.get(
    f"{BASE}/meetingTranscripts/{transcript_id}/snippets/{snippet_id}",
    headers=headers)
snippet = resp.json()

# Update a snippet (correct the text)
resp = requests.put(
    f"{BASE}/meetingTranscripts/{transcript_id}/snippets/{snippet_id}",
    headers=headers,
    json={"text": "Corrected text here", "reason": "Typo fix"})

# Delete a transcript
resp = requests.delete(f"{BASE}/meetingTranscripts/{transcript_id}",
    headers=headers,
    json={"reason": "Data retention policy", "comment": "Removing per compliance request"})
# Returns 204 No Content on success
```

---

## 3. Closed Captions

**CLI group:** `meeting-captions`
**API base:** `https://webexapis.com/v1/meetingClosedCaptions`

Closed captions are the real-time captions captured during a meeting. They are distinct from transcripts (which are generated post-meeting from audio). Only available for ended meeting instances.

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| List captions | `wxcli meeting-captions list-meeting-closed-captions` | GET /meetingClosedCaptions | List closed captions for a meeting |
| List snippets | `wxcli meeting-captions list CAPTION_ID` | GET /meetingClosedCaptions/{closedCaptionId}/snippets | List individual caption segments |
| Download | `wxcli meeting-captions list-download CAPTION_ID` | GET /meetingClosedCaptions/{closedCaptionId}/download | Download captions as VTT or TXT |

### Key Parameters

#### `meeting-captions list-meeting-closed-captions`

| Option | Description |
|--------|-------------|
| `--meeting-id ID` | Meeting instance ID (required). Only works for ended meetings |

#### `meeting-captions list`

| Option | Description |
|--------|-------------|
| `--meeting-id ID` | Meeting instance ID. Only works for ended meetings |

#### `meeting-captions list-download`

| Option | Description |
|--------|-------------|
| `--format FORMAT` | Download format: `vtt` or `txt` |
| `--meeting-id ID` | Meeting instance ID. Only works for ended meetings |
| `--timezone TZ` | Timezone for timestamps (e.g., `UTC`, `America/New_York`). Passed as a header |

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"
headers = {"Authorization": f"Bearer {token}"}

# List closed captions for a meeting
resp = requests.get(f"{BASE}/meetingClosedCaptions",
    headers=headers,
    params={"meetingId": meeting_id})
captions = resp.json().get("items", [])
# Each item: {"id", "meetingId", "language", ...}

# List caption snippets
resp = requests.get(f"{BASE}/meetingClosedCaptions/{caption_id}/snippets",
    headers=headers,
    params={"meetingId": meeting_id})
snippets = resp.json().get("items", [])
# Each snippet: {"id", "text", "personName", "personEmail", "startTime", ...}

# Download captions as VTT
resp = requests.get(f"{BASE}/meetingClosedCaptions/{caption_id}/download",
    headers={**headers, "timezone": "UTC"},
    params={"format": "vtt", "meetingId": meeting_id})
# resp.text contains the raw VTT file content (NOT JSON)
with open("captions.vtt", "w") as f:
    f.write(resp.text)
```

---

## 4. Chats

**CLI group:** `meeting-chats`
**API base:** `https://webexapis.com/v1/meetings/postMeetingChats`

Post-meeting chats are the chat messages participants sent during a meeting. The API path uses `postMeetingChats` — these are only available after the meeting ends. The endpoint does not support in-progress meetings.

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| List chats | `wxcli meeting-chats list` | GET /meetings/postMeetingChats | List chat messages from a meeting |
| Delete chats | `wxcli meeting-chats delete` | DELETE /meetings/postMeetingChats | Delete all chats for a meeting |

### Key Parameters

#### `meeting-chats list`

| Option | Description |
|--------|-------------|
| `--meeting-id ID` | Meeting instance ID (required). Personal room meeting IDs are not supported |
| `--max N` | Maximum number of chats per response, up to 100 |
| `--offset N` | Offset from the first result for pagination |

#### `meeting-chats delete`

| Option | Description |
|--------|-------------|
| `--meeting-id ID` | Meeting instance ID (required). Personal room meeting IDs are not supported |

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"
headers = {"Authorization": f"Bearer {token}"}

# List post-meeting chats
resp = requests.get(f"{BASE}/meetings/postMeetingChats",
    headers=headers,
    params={"meetingId": meeting_id, "max": 100})
chats = resp.json().get("items", [])
# Each item: {"id", "text", "senderName", "senderEmail", "sentTime", ...}

# Delete all chats for a meeting
resp = requests.delete(f"{BASE}/meetings/postMeetingChats",
    headers=headers,
    params={"meetingId": meeting_id})
# Returns 204 No Content on success
```

### Gotchas

- **Chats use offset-based pagination**, not cursor-based. Use `--offset` to page through results, unlike most Webex APIs that use `Link` headers.
- **The delete endpoint removes ALL chats for the meeting** — there is no per-message delete for post-meeting chats.

---

## 5. Meeting Messages

**CLI group:** `meeting-messages`
**API base:** `https://webexapis.com/v1/meeting/messages`

This is a compliance-only endpoint for deleting individual messages from a meeting's in-meeting chat. Note the singular `meeting` in the path (not `meetings`).

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| Delete message | `wxcli meeting-messages delete MESSAGE_ID` | DELETE /meeting/messages/{meetingMessageId} | Delete a specific meeting message (compliance) |

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"
headers = {"Authorization": f"Bearer {token}"}

# Delete a specific meeting message (compliance officer token required)
resp = requests.delete(f"{BASE}/meeting/messages/{meeting_message_id}",
    headers=headers)
# Returns 204 No Content on success
```

### Gotchas

- **This is a compliance endpoint** — it requires admin-level scopes. Regular users cannot delete individual meeting messages.
- **Note the singular path:** `/meeting/messages/{meetingMessageId}` — not `/meetings/messages/`. This differs from the chats endpoint at `/meetings/postMeetingChats`.

---

## 6. Summaries

**CLI group:** `meeting-summaries`
**API base:** `https://webexapis.com/v1/meetingSummaries`

AI-generated meeting summaries produced by the Webex AI Assistant. Two list endpoints exist: one for regular users (by meeting ID) and one for compliance officers (org-wide). Summaries are only available for ended meeting instances — not for meeting series, scheduled meetings, in-progress meetings, or personal room meetings.

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| List (compliance) | `wxcli meeting-summaries list` | GET /admin/meetingSummaries | Get summary org-wide (compliance officer) |
| List (user) | `wxcli meeting-summaries list-meeting-summaries` | GET /meetingSummaries | Get summary by meeting ID |
| Delete | `wxcli meeting-summaries delete SUMMARY_ID` | DELETE /meetingSummaries/{summaryId} | Delete a summary |

### Key Parameters

#### `meeting-summaries list` (compliance)

| Option | Description |
|--------|-------------|
| `--meeting-id ID` | Meeting instance ID (required — query is rejected without it) |

#### `meeting-summaries list-meeting-summaries` (user)

| Option | Description |
|--------|-------------|
| `--meeting-id ID` | Meeting instance ID (required — query is rejected without it) |

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"
headers = {"Authorization": f"Bearer {token}"}

# Get summary by meeting ID (user token)
resp = requests.get(f"{BASE}/meetingSummaries",
    headers=headers,
    params={"meetingId": meeting_id})
summary = resp.json()
# Returns: {"meetingId", "summary", "keywords", "actionItems", ...}

# Get summary for compliance officer (admin token)
resp = requests.get(f"{BASE}/admin/meetingSummaries",
    headers=headers,
    params={"meetingId": meeting_id})
summary = resp.json()

# Delete a summary
resp = requests.delete(f"{BASE}/meetingSummaries/{summary_id}",
    headers=headers)
# Returns 204 No Content on success
```

### Gotchas

- **`meetingId` is required for both list endpoints.** The API rejects the query if `meetingId` is not specified, even though the spec marks it as optional.
- **Summaries require the Webex AI Assistant feature** to be enabled for the org. If not enabled, these endpoints return empty results or errors.
- **Only ended meeting instances are supported.** Meeting series IDs, scheduled meeting IDs, in-progress meeting instance IDs, and personal room meeting IDs are all rejected.

---

## 7. Recordings (Cross-Reference)

Meeting recordings are **not** in the `webex-meetings.json` spec. They are covered by the admin API and managed through the `admin-recordings` CLI group (generated from `specs/webex-admin.json`).

See [`admin-apps-data.md`](admin-apps-data.md) for recording management: list recordings, get recording details, download, delete, and move recordings.

---

## 8. Raw HTTP Endpoints

All 16 endpoints covered by the 5 CLI groups in this doc.

| Method | Path | CLI Group | CLI Command | Token |
|--------|------|-----------|-------------|-------|
| GET | /admin/meetingTranscripts | meeting-transcripts | `list` | Admin |
| GET | /meetingTranscripts | meeting-transcripts | `list-meeting-transcripts` | User |
| GET | /meetingTranscripts/{transcriptId}/download | meeting-transcripts | `list-download` | User/Admin |
| GET | /meetingTranscripts/{transcriptId}/snippets | meeting-transcripts | `list-snippets` | User/Admin |
| GET | /meetingTranscripts/{transcriptId}/snippets/{snippetId} | meeting-transcripts | `show` | User/Admin |
| PUT | /meetingTranscripts/{transcriptId}/snippets/{snippetId} | meeting-transcripts | `update` | User/Admin |
| DELETE | /meetingTranscripts/{transcriptId} | meeting-transcripts | `delete` | User/Admin |
| GET | /meetingClosedCaptions | meeting-captions | `list-meeting-closed-captions` | User |
| GET | /meetingClosedCaptions/{closedCaptionId}/snippets | meeting-captions | `list` | User |
| GET | /meetingClosedCaptions/{closedCaptionId}/download | meeting-captions | `list-download` | User |
| GET | /meetings/postMeetingChats | meeting-chats | `list` | User |
| DELETE | /meetings/postMeetingChats | meeting-chats | `delete` | User/Admin |
| DELETE | /meeting/messages/{meetingMessageId} | meeting-messages | `delete` | Admin |
| GET | /admin/meetingSummaries | meeting-summaries | `list` | Admin |
| GET | /meetingSummaries | meeting-summaries | `list-meeting-summaries` | User |
| DELETE | /meetingSummaries/{summaryId} | meeting-summaries | `delete` | User/Admin |

---

## 9. Gotchas

These issues span multiple meeting content API surfaces. Check per-section Gotchas for endpoint-specific notes.

1. **Admin vs user list endpoints.** Transcripts and summaries each have two list paths: `/admin/meetingTranscripts` and `/admin/meetingSummaries` require admin tokens with compliance officer scopes and return org-wide results. The non-admin paths (`/meetingTranscripts`, `/meetingSummaries`) use user tokens and return results scoped to the authenticated user's meetings.

2. **Download endpoints return raw file content, not JSON.** Both `meeting-transcripts list-download` and `meeting-captions list-download` return the raw VTT or TXT file body. The response `Content-Type` will be `text/vtt` or `text/plain`, not `application/json`. Parse accordingly.

3. **Chats endpoint path is `postMeetingChats`.** The API path is `/meetings/postMeetingChats`, not `/meetings/chats`. These chats are only available after the meeting ends — in-progress meetings return no results.

4. **Meeting messages uses singular `/meeting/messages/` path.** This is distinct from the chats path at `/meetings/postMeetingChats`. The singular path is a compliance-only delete endpoint for individual in-meeting messages.

5. **Personal room meeting IDs are not supported** across most of these endpoints. Transcript lists, caption lists, chat lists, and summary queries all explicitly reject personal room meeting IDs. Use only meeting instance IDs from ended meetings.

6. **Transcript snippet update only allows editing `text` and `reason`.** You cannot change the speaker attribution, timestamps, or other metadata on a snippet — only the transcribed text (for corrections) and an optional reason for the edit.

7. **Transcript delete accepts a request body** (with `reason` and `comment` fields) even though it is a DELETE request. Most REST APIs do not use request bodies on DELETE — this is an unusual pattern.

8. **Summaries require Webex AI Assistant.** The meeting summaries endpoints only return data if the org has the AI Assistant feature enabled and the meeting was configured to generate a summary. Without this feature, the endpoints return empty results.

9. **Caption snippets vs transcript snippets are separate resources.** Even though both represent text segments of meeting content, captions (`/meetingClosedCaptions/{id}/snippets`) and transcript snippets (`/meetingTranscripts/{id}/snippets`) are different API surfaces with different IDs. Captions are captured in real-time; transcripts are generated post-meeting from audio.

10. **Chats use offset-based pagination.** Unlike most Webex APIs that use cursor-based pagination with `Link` headers, the post-meeting chats endpoint uses `--offset` and `--max` for paging.

---

## 10. See Also

- [`meetings-core.md`](meetings-core.md) — Meeting CRUD, templates, controls, registrants, interpreters, breakouts, surveys
- [`meetings-settings.md`](meetings-settings.md) — Preferences, session types, tracking codes, site settings, polls, Q&A, reports
- [`meetings-infrastructure.md`](meetings-infrastructure.md) — Video Mesh (clusters, nodes, health, utilization), participants, invitees
- [`admin-apps-data.md`](admin-apps-data.md) — Recording management (`admin-recordings` CLI group): list, download, delete, and move meeting recordings
- [`webhooks-events.md`](webhooks-events.md) — Webhook CRUD and event payloads for meeting events (`meetings`, `recordings`)
- [`authentication.md`](authentication.md) — Token types, scopes, admin vs user vs compliance officer tokens
