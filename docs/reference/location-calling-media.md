# Location Call Settings — Announcements, Playlists, Schedules & Access Codes

## Sources

- OpenAPI spec: specs/webex-cloud-calling.json
- developer.webex.com Location Call Settings APIs

Reference for managing audio media (announcements, playlists), time-based routing (schedules), and outgoing-permission bypass codes at the location and org level.

> **Not supported for Webex for Government (FedRAMP)** — Announcements and Playlists APIs are explicitly excluded. See [authentication.md → FedRAMP](authentication.md#webex-for-government-fedramp) for all FedRAMP restrictions.

---

## Table of Contents

1. [Announcements Repository](#1-announcements-repository)
2. [Playlists (Music On Hold)](#2-playlists-music-on-hold)
3. [Access Codes](#3-access-codes)
4. [Schedules & Holiday Schedules](#4-schedules--holiday-schedules)
5. [Cross-Cutting Patterns](#5-cross-cutting-patterns)
6. [Gotchas](#gotchas)
7. [See Also](#see-also)

---

## 1. Announcements Repository

The announcement repository stores binary audio files (WAV) used by Auto Attendants, Call Queues, and Music On Hold. Files can be uploaded at the **organization level** or scoped to a **specific location**.

**REST endpoint:** `/telephony/config/announcements` (org-level) — see §1.3 for location-level and per-operation path variations.

### 1.1 Data Models

#### `RepoAnnouncement` (extends `IdAndName`)

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | Unique identifier |
| `name` | `str` | Display name |
| `file_name` | `str` | Uploaded binary file name |
| `file_size` | `int` | Size in kilobytes |
| `media_file_type` | `MediaFileType` | Audio/video media type |
| `last_updated` | `datetime` | UTC timestamp |
| `level` | `AnnouncementLevel` | Org-level vs. location-level |
| `location` | `IdAndName` | Location details (if location-scoped) |
| `feature_reference_count` | `int` | Number of features referencing this file (**details only**, not returned by list) |
| `feature_references` | `list[FeatureReference]` | Features using this announcement (**details only**) |
| `playlists` | `list[IdAndName]` | Playlists containing this announcement (**details only**) |

#### `FeatureReference`

Describes a call feature (Auto Attendant, Call Queue, Music On Hold) that references an announcement.

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | Feature identifier |
| `name` | `str` | Feature name |
| `type` | `str` | Resource type of the feature |
| `location_id` | `str` | Location identifier |
| `location_name` | `str` | Location name |

#### `RepositoryUsage`

| Field | Type | Notes |
|-------|------|-------|
| `total_file_size_used_kb` | `int` | Total space used (KB) |
| `max_audio_file_size_allowed_kb` | `int` | Max single audio file size (KB) |
| `max_video_file_size_allowed_kb` | `int` | Max single video file size (KB) |
| `total_file_size_limit_mb` | `int` | Total repo capacity (MB) |

### 1.3 Raw HTTP — Announcements

```python
BASE = "https://webexapis.com/v1"

# --- Org-level announcements ---

# GET — List org-level announcements (paginated)
result = api.session.rest_get(f"{BASE}/telephony/config/announcements",
    params={"max": 1000})
# Response: {"announcements": [{"id": "...", "name": "...", "fileName": "...", "fileSize": 123, ...}]}

# GET — Get org-level announcement details
result = api.session.rest_get(f"{BASE}/telephony/config/announcements/{ann_id}")
# Response includes featureReferenceCount, featureReferences, playlists (not returned by list)

# PUT — Update org-level announcement (metadata only; file upload uses multipart)
body = {"name": "Updated Name"}
api.session.rest_put(f"{BASE}/telephony/config/announcements/{ann_id}", json=body)

# DELETE — Delete org-level announcement
api.session.rest_delete(f"{BASE}/telephony/config/announcements/{ann_id}")

# GET — Org-level repository usage
result = api.session.rest_get(f"{BASE}/telephony/config/announcements/usage")
# Response: {"totalFileSizeUsedKB": 1024, "maxAudioFileSizeAllowedKB": 8192,
#            "maxVideoFileSizeAllowedKB": 16384, "totalFileSizeLimitMB": 500}

# --- Location-level announcements ---

# GET — List location announcements (use locationId query param on org endpoint)
result = api.session.rest_get(f"{BASE}/telephony/config/announcements",
    params={"locationId": loc_id, "max": 1000})

# GET — Get location announcement details
result = api.session.rest_get(
    f"{BASE}/telephony/config/locations/{loc_id}/announcements/{ann_id}")

# PUT — Update location announcement
api.session.rest_put(
    f"{BASE}/telephony/config/locations/{loc_id}/announcements/{ann_id}", json=body)

# DELETE — Delete location announcement
api.session.rest_delete(
    f"{BASE}/telephony/config/locations/{loc_id}/announcements/{ann_id}")

# GET — Location repository usage
result = api.session.rest_get(
    f"{BASE}/telephony/config/locations/{loc_id}/announcements/usage")
```

**Gotcha:** The list endpoint uses a query parameter `locationId` on the org-level URL (`/telephony/config/announcements`), but details/update/delete for location announcements use a path segment (`/locations/{locId}/announcements/{annId}`). These are different URL patterns for list vs. CRUD.
<!-- Updated by playbook session 2026-03-18 -->

**Gotcha:** Upload and modify (file replacement) require `multipart/form-data` with `audio/wav` content type. For raw HTTP, you must construct the multipart body manually -- the `rest_put`/`rest_post` JSON helpers used elsewhere in this doc do not handle file uploads.

### CLI Examples

```bash
# List all org-level announcements
wxcli announcements list

# List announcements for a specific location
wxcli announcements list --location-id Y2lzY29zcGFyazovL_LOC_ID

# List all announcements across all locations
wxcli announcements list --location-id all

# Filter by file name or announcement name
wxcli announcements list --file-name "greeting.wav"
wxcli announcements list --name "Welcome Greeting"

# Get org-level repository usage (total space, limits)
wxcli announcements show

# Get details for an org-level announcement
wxcli announcements show-announcements-config Y2lzY29zcGFyazovL_ANN_ID

# Get details for a location-level announcement
wxcli announcements show-announcements-locations Y2lzY29zcGFyazovL_LOC_ID Y2lzY29zcGFyazovL_ANN_ID

# Get repository usage for a specific location
wxcli announcements show-usage-announcements Y2lzY29zcGFyazovL_LOC_ID

# Delete an org-level announcement
wxcli announcements delete Y2lzY29zcGFyazovL_ANN_ID --force

# Delete a location-level announcement
wxcli announcements delete-announcements Y2lzY29zcGFyazovL_LOC_ID Y2lzY29zcGFyazovL_ANN_ID --force

# Update an org-level announcement (metadata via --json-body)
wxcli announcements update Y2lzY29zcGFyazovL_ANN_ID --json-body '{"name": "Updated Greeting"}'
```

> **Note:** The CLI does create announcements: `wxcli announcements create` (org level) and `wxcli announcements create-announcements LOCATION_ID` (location level). Both require `--name`, `--file-uri`, `--file-name`, and `--is-text-to-speech`, and send a JSON body (`fileUri`/`fileName`/`isTextToSpeech`) to `POST /telephony/config/announcements` -- not a `multipart/form-data` upload. `--file-uri` takes a **URI** referencing the file, so these commands do not push local binary `.wav` bytes; for that, use the manual multipart raw HTTP path noted above. `update` / `update-announcements` modify an existing announcement with the same fields.

### 1.4 Key Patterns

- **Org vs. location scoping:** Every method takes an optional `location_id`. When `None`, the operation targets the org-level repository. When set, it targets that location's repository.
- **URL pattern:** Org-level uses `/telephony/config/announcements/...`; location-level uses `/telephony/config/locations/{locationId}/announcements/...`.
- **File format:** WAV audio files. Uploads use `audio/wav` as the MIME type.
- **Checking references before delete:** Use `wxcli announcements show-announcements-config`/`show-announcements-locations` (or `GET .../announcements/{id}`) to inspect `featureReferences` and `playlists` before deleting an announcement that may be in use.

---

## 2. Playlists (Music On Hold)

Playlists group multiple announcement files for Music On Hold. A playlist can contain up to **25 announcement files** and can be assigned to one or more locations.

**REST endpoint:** `/telephony/config/announcements/playlists`

### 2.1 Data Models

#### `PlayList`

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | Unique identifier |
| `name` | `str` | Playlist display name |
| `file_size` | `int` | Total size of files (KB) |
| `file_count` | `int` | Number of announcements in playlist |
| `is_in_use` | `bool` | Whether any feature references this playlist |
| `last_updated` | `datetime` | UTC timestamp |
| `level` | `str` | Level at which playlist exists |
| `location_count` | `int` | Number of locations assigned to this playlist |
| `announcements` | `list[PlaylistAnnouncement]` | Announcement details (populated in the single-playlist details response, not the list response) |

#### `PlaylistAnnouncement`

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | Announcement identifier |
| `name` | `str` | Announcement name |
| `file_name` | `str` | Uploaded file name |
| `file_size` | `int` | Size in KB |
| `media_file_type` | `str` | Media type |
| `last_updated` | `datetime` | UTC timestamp |
| `level` | `str` | Announcement level |

#### `PlaylistUsage`

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | Playlist identifier |
| `locations` | `list[PlaylistUsageLocation]` | Locations using this playlist |

#### `PlaylistUsageLocation`

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | Location identifier |
| `name` | `str` | Location name |
| `feature_reference` | `PlaylistUsageLocationFeatureRef` | Feature referencing the playlist |

#### `PlaylistUsageType` (enum)

| Value | Description |
|-------|-------------|
| `feature` | Filter usage by feature |
| `location` | Filter usage by location |

### 2.3 Raw HTTP — Playlists

```python
BASE = "https://webexapis.com/v1"

# GET — List all playlists (org-level, not paginated)
result = api.session.rest_get(f"{BASE}/telephony/config/announcements/playlists")
# Response: {"playlists": [{"id": "...", "name": "...", "fileSize": 0, "fileCount": 0,
#            "isInUse": false, "lastUpdated": "...", "locationCount": 0}]}

# POST — Create a playlist
body = {
    "name": "Hold Music Rotation",
    "announcements": [{"id": "<ann_id_1>"}, {"id": "<ann_id_2>"}]
}
result = api.session.rest_post(f"{BASE}/telephony/config/announcements/playlists", json=body)
# Returns: {"id": "<playlist_id>"}

# GET — Get playlist details (includes announcement list)
result = api.session.rest_get(f"{BASE}/telephony/config/announcements/playlists/{playlist_id}")

# PUT — Update a playlist (name and/or announcements)
body = {
    "name": "Updated Playlist Name",
    "announcements": [{"id": "<ann_id_1>"}, {"id": "<ann_id_3>"}]
}
api.session.rest_put(f"{BASE}/telephony/config/announcements/playlists/{playlist_id}", json=body)

# DELETE — Delete a playlist
api.session.rest_delete(f"{BASE}/telephony/config/announcements/playlists/{playlist_id}")

# --- Playlist location assignments ---

# GET — List locations assigned to a playlist
result = api.session.rest_get(
    f"{BASE}/telephony/config/announcements/playlists/{playlist_id}/locations")
# Response: {"locations": [{"id": "...", "name": "..."}]}

# PUT — Assign playlist to locations (full replace)
body = {
    "locationIds": ["<loc_id_1>", "<loc_id_2>"]
}
api.session.rest_put(
    f"{BASE}/telephony/config/announcements/playlists/{playlist_id}/locations", json=body)
```

**Gotcha:** Location assignment is a full replace, not incremental. Always GET current locations first, then PUT the complete list including any new additions.
<!-- Updated by playbook session 2026-03-18 -->

### CLI Examples

```bash
# List all playlists in the org
wxcli announcement-playlists list

# Get details for a specific playlist (includes announcement list)
wxcli announcement-playlists show Y2lzY29zcGFyazovL_PLAYLIST_ID

# Create a playlist (announcement IDs must be passed via --json-body)
wxcli announcement-playlists create --name "Hold Music Rotation" \
  --json-body '{"name": "Hold Music Rotation", "announcementIds": ["ANN_ID_1", "ANN_ID_2"]}'

# Update a playlist name
wxcli announcement-playlists update Y2lzY29zcGFyazovL_PLAYLIST_ID --name "New Playlist Name"

# Update a playlist's announcements via --json-body
wxcli announcement-playlists update Y2lzY29zcGFyazovL_PLAYLIST_ID \
  --json-body '{"name": "Hold Music Rotation", "announcementIds": ["ANN_ID_1", "ANN_ID_3"]}'

# Delete a playlist
wxcli announcement-playlists delete Y2lzY29zcGFyazovL_PLAYLIST_ID --force

# List locations assigned to a playlist
wxcli announcement-playlists list-playlists Y2lzY29zcGFyazovL_PLAYLIST_ID

# Assign a playlist to locations (full replace — include ALL desired location IDs)
wxcli announcement-playlists update-playlists Y2lzY29zcGFyazovL_PLAYLIST_ID \
  --json-body '{"locationIds": ["LOC_ID_1", "LOC_ID_2"]}'
```

### CLI: `cq-playlists` (Call Queue Playlist Usage)

The `cq-playlists` CLI group lets you check which call queues or locations reference a specific playlist.

| Command | Description |
|---------|-------------|
| `cq-playlists list <playlist_id>` | Get playlist usage (which queues/locations reference a playlist) |

```bash
# See which features use a specific playlist
wxcli cq-playlists list <playlist_id>

# Filter to see only location-level usage
wxcli cq-playlists list <playlist_id> --playlist-usage-type location

# Filter to see only feature-level usage (call queues, auto attendants)
wxcli cq-playlists list <playlist_id> --playlist-usage-type feature
```

### 2.4 Key Patterns

- **Playlists are org-level only.** They are created at the org level, then assigned to locations via `PUT .../playlists/{id}/locations` (see §2.3).
- **Workflow:** Upload announcements to the repo first, then create a playlist referencing those announcement IDs, then assign the playlist to locations.
- **Location assignment is a full replace**, not incremental. Always read current assignments (`GET .../playlists/{id}/locations`) before modifying.

---

## 3. Access Codes

Access codes (also called authorization codes) let authorized users bypass outgoing or incoming calling permission restrictions. They exist at two levels: **location** and **organization**.

### 3.1 Location Access Codes

**Endpoint pattern:** `/telephony/config/locations/{locationId}/outgoingPermission/accessCodes`

#### Data Model: `AuthCode`

| Field | Type | Notes |
|-------|------|-------|
| `code` | `str` | The authorization code string |
| `description` | `str` | Human-readable description |
| `level` | `AuthCodeLevel` | `LOCATION` or `CUSTOM` (read-only, set by system) |

### 3.2 Organization Access Codes

**REST endpoint:** `/telephony/config/outgoingPermission/accessCodes`

Organization-level access codes apply across all locations in the org.

### 3.3 Raw HTTP — Access Codes

```python
BASE = "https://webexapis.com/v1"

# --- Location-level access codes ---

# GET — List access codes for a location
result = api.session.rest_get(
    f"{BASE}/telephony/config/locations/{loc_id}/outgoingPermission/accessCodes")
# Response: {"accessCodes": [{"code": "1234", "description": "Sales team", "level": "LOCATION"}]}

# POST — Create access codes for a location
body = {
    "accessCodes": [
        {"code": "1234", "description": "Sales team"},
        {"code": "5678", "description": "Support team"}
    ]
}
api.session.rest_post(
    f"{BASE}/telephony/config/locations/{loc_id}/outgoingPermission/accessCodes", json=body)

# PUT — Delete specific access codes (uses PUT, not DELETE)
body = {
    "deleteCodes": ["1234", "5678"]
}
api.session.rest_put(
    f"{BASE}/telephony/config/locations/{loc_id}/outgoingPermission/accessCodes", json=body)

# DELETE — Delete all access codes for a location
api.session.rest_delete(
    f"{BASE}/telephony/config/locations/{loc_id}/outgoingPermission/accessCodes")

# --- Org-level access codes ---

# GET — List org-level access codes (paginated)
result = api.session.rest_get(
    f"{BASE}/telephony/config/outgoingPermission/accessCodes",
    params={"max": 1000})
# Response: {"accessCodes": [{"code": "9999", "description": "Global bypass"}]}

# POST — Create org-level access codes (max 10,000 per request)
body = {
    "accessCodes": [
        {"code": "9999", "description": "Global bypass"}
    ]
}
api.session.rest_post(f"{BASE}/telephony/config/outgoingPermission/accessCodes", json=body)

# PUT — Delete org-level access codes (uses PUT, not DELETE; max 10,000 per request)
body = {
    "deleteCodes": ["9999"]
}
api.session.rest_put(f"{BASE}/telephony/config/outgoingPermission/accessCodes", json=body)
```

**Gotcha:** Deleting specific codes uses PUT with a `deleteCodes` array in the body, not an HTTP DELETE. This applies at both location and org level. The `DELETE` verb is only used for "delete all" at the location level.
<!-- Updated by playbook session 2026-03-18 -->

### 3.4 Key Patterns

- **Location vs. org level:** Location codes bypass permissions for persons/workspaces at that location only. Org codes apply across all locations.
- **No update method:** To change an access code, delete the old one and create a new one.
- **Delete uses PUT:** Both location and org delete operations send a PUT with `deleteCodes` in the body, not an HTTP DELETE.
- **Batch limits:** Org-level create and delete support up to 10,000 codes per request (per the OpenAPI spec: "max limit is 10k per request"). Location-level create/delete has no documented batch limit in the OpenAPI spec.

---

## 4. Schedules & Holiday Schedules

Schedules define time windows (business hours, holidays) that control call routing behavior for features like Auto Attendants. They can be created at the **location** or **person (user)** level.

**REST endpoint:** `/telephony/config/locations/{locationId}/schedules` (location-scoped) or `/people/{personId}/features/schedules` (user-scoped) — see §4.4 for full URL structure.

### 4.1 Data Models

#### `ScheduleType` (enum)

| Value | String | Description |
|-------|--------|-------------|
| `business_hours` | `"businessHours"` | Define operating hours |
| `holidays` | `"holidays"` | Define exceptions to business hours |

#### `ScheduleLevel` (enum)

| Value | Description |
|-------|-------------|
| `LOCATION` | Location-scoped schedule |
| `ORGANIZATION` | Org-scoped schedule |
| `PEOPLE` | User-scoped schedule |

#### `Schedule`

| Field | Type | Notes |
|-------|------|-------|
| `name` | `str` | Schedule display name |
| `new_name` | `str` | New name (only used when renaming a schedule via the PUT/update request) |
| `schedule_id` | `str` | Unique identifier (alias: `id`) |
| `level` | `ScheduleLevel` | Scope level (returned in user-level listing) |
| `location_name` | `str` | Location name (returned by the list endpoint for location schedules) |
| `location_id` | `str` | Location identifier (returned by the list endpoint for location schedules) |
| `schedule_type` | `ScheduleType` | `businessHours` or `holidays` (alias: `type`) |
| `events` | `list[Event]` | List of events in this schedule |

#### `Event`

| Field | Type | Notes |
|-------|------|-------|
| `event_id` | `str` | Unique identifier (alias: `id`) |
| `name` | `str` | Event name |
| `new_name` | `str` | New name (only used in updates) |
| `start_date` | `date` | Start date (required if `all_day_enabled` is set) |
| `end_date` | `date` | End date (required if `all_day_enabled` is set) |
| `start_time` | `time` | Start time (required if `all_day_enabled` is false/omitted) |
| `end_time` | `time` | End time (required if `all_day_enabled` is false/omitted) |
| `all_day_enabled` | `bool` | True for all-day events (e.g., holidays) |
| `recurrence` | `Recurrence` | Optional recurrence pattern |

#### `Recurrence`

Controls how events repeat. Location and user schedules support different recurrence types:

| Field | Type | Supported Level |
|-------|------|-----------------|
| `recur_for_ever` | `bool` | User + Location |
| `recur_end_date` | `date` | User + Location |
| `recur_end_occurrence` | `int` | User only |
| `recur_daily` | `RecurDaily` | User only |
| `recur_weekly` | `RecurWeekly` | User + Location |
| `recur_yearly_by_date` | `RecurYearlyByDate` | Location only |
| `recur_yearly_by_day` | `RecurYearlyByDay` | Location only |

#### Supporting Recurrence Models

- **`RecurWeekly`** — boolean flags for each day of the week + `recur_interval` (weeks between occurrences). Helper: `RecurWeekly.single_day(day, recur_interval=1)`.
- **`RecurYearlyByDate`** — `day_of_month` (int) + `month` (ScheduleMonth enum). Helper: `RecurYearlyByDate.from_date(date)`.
- **`RecurYearlyByDay`** — `day` (ScheduleDay) + `week` (ScheduleWeek: FIRST/SECOND/THIRD/FOURTH) + `month` (ScheduleMonth).
- **`RecurDaily`** — `recur_interval` (int, days between occurrences). User schedules only.

### 4.3 Raw HTTP — Schedules

```python
BASE = "https://webexapis.com/v1"

# --- Location schedules ---

# GET — List schedules for a location (paginated)
result = api.session.rest_get(
    f"{BASE}/telephony/config/locations/{loc_id}/schedules",
    params={"max": 1000, "type": "businessHours"}  # or "holidays"
)
# Response: {"schedules": [{"id": "...", "name": "...", "type": "businessHours"}]}
# Note: list does NOT include events — use details to get events

# POST — Create a schedule
body = {
    "type": "holidays",
    "name": "National Holidays",
    "events": [
        {
            "name": "Independence Day",
            "startDate": "2026-07-04",
            "endDate": "2026-07-04",
            "allDayEnabled": True
        }
    ]
}
result = api.session.rest_post(f"{BASE}/telephony/config/locations/{loc_id}/schedules", json=body)
# Returns: {"id": "<schedule_id>"}

# GET — Get schedule details (includes events)
# sched_type is "businessHours" or "holidays"
result = api.session.rest_get(
    f"{BASE}/telephony/config/locations/{loc_id}/schedules/{sched_type}/{sched_id}"
)

# PUT — Update a schedule
body = {
    "name": "Updated Schedule Name",
    "events": [...]  # Full event list
}
result = api.session.rest_put(
    f"{BASE}/telephony/config/locations/{loc_id}/schedules/{sched_type}/{sched_id}",
    json=body
)
# Returns schedule ID (changes if name changed!)

# DELETE — Delete a schedule
api.session.rest_delete(
    f"{BASE}/telephony/config/locations/{loc_id}/schedules/{sched_type}/{sched_id}"
)

# --- Schedule events ---

# GET — Get a single event
result = api.session.rest_get(
    f"{BASE}/telephony/config/locations/{loc_id}/schedules/{sched_type}/{sched_id}/events/{event_id}"
)

# POST — Add an event to a schedule
body = {
    "name": "Christmas Day",
    "startDate": "2026-12-25",
    "endDate": "2026-12-25",
    "allDayEnabled": True
}
result = api.session.rest_post(
    f"{BASE}/telephony/config/locations/{loc_id}/schedules/{sched_type}/{sched_id}/events",
    json=body
)
# Returns: {"id": "<event_id>"}

# PUT — Update an event
body = {
    "name": "Christmas Day 2026",
    "startDate": "2026-12-25",
    "endDate": "2026-12-25",
    "allDayEnabled": True,
    "recurrence": {
        "recurYearlyByDate": {"dayOfMonth": 25, "month": "DECEMBER"}
    }
}
result = api.session.rest_put(
    f"{BASE}/telephony/config/locations/{loc_id}/schedules/{sched_type}/{sched_id}/events/{event_id}",
    json=body
)
# Returns event ID (changes if name changed!)

# DELETE — Delete an event
api.session.rest_delete(
    f"{BASE}/telephony/config/locations/{loc_id}/schedules/{sched_type}/{sched_id}/events/{event_id}"
)

# --- User-level schedules (same pattern, different base) ---
# Base: {BASE}/people/{person_id}/features/schedules/...
```

**Gotcha:** Schedule IDs are name-derived (base64-encoded from the schedule name). Renaming a schedule changes its ID -- the old ID returns 404 after rename. Always re-fetch the ID after a name change. Event IDs behave the same way.

### CLI Examples

```bash
# List all schedules for a location
wxcli location-schedules list Y2lzY29zcGFyazovL_LOC_ID

# List only business hours schedules
wxcli location-schedules list Y2lzY29zcGFyazovL_LOC_ID --type businessHours

# List only holiday schedules
wxcli location-schedules list Y2lzY29zcGFyazovL_LOC_ID --type holidays

# Filter by schedule name
wxcli location-schedules list Y2lzY29zcGFyazovL_LOC_ID --name "National Holidays"

# Get schedule details (includes events); type is "businessHours" or "holidays"
wxcli location-schedules show Y2lzY29zcGFyazovL_LOC_ID holidays Y2lzY29zcGFyazovL_SCHED_ID

# Create a holiday schedule (events can be added later)
wxcli location-schedules create Y2lzY29zcGFyazovL_LOC_ID \
  --type holidays --name "National Holidays"

# Create a business hours schedule with events via --json-body
wxcli location-schedules create Y2lzY29zcGFyazovL_LOC_ID \
  --type businessHours --name "Office Hours" \
  --json-body '{
    "type": "businessHours",
    "name": "Office Hours",
    "events": [
      {"name": "Monday AM", "startDate": "2026-01-05", "endDate": "2026-01-05",
       "startTime": "09:00", "endTime": "12:00"}
    ]
  }'

# Add an all-day holiday event to an existing schedule
wxcli location-schedules create-events Y2lzY29zcGFyazovL_LOC_ID holidays Y2lzY29zcGFyazovL_SCHED_ID \
  --name "Independence Day" --start-date 2026-07-04 --end-date 2026-07-04 --all-day-enabled

# Add a timed event (business hours block)
wxcli location-schedules create-events Y2lzY29zcGFyazovL_LOC_ID businessHours Y2lzY29zcGFyazovL_SCHED_ID \
  --name "Monday AM" --start-date 2026-01-05 --end-date 2026-01-05 \
  --start-time "09:00" --end-time "12:00"

# Get details for a specific event
wxcli location-schedules show-events Y2lzY29zcGFyazovL_LOC_ID holidays Y2lzY29zcGFyazovL_SCHED_ID Y2lzY29zcGFyazovL_EVENT_ID

# Delete an event from a schedule
wxcli location-schedules delete-events Y2lzY29zcGFyazovL_LOC_ID holidays Y2lzY29zcGFyazovL_SCHED_ID Y2lzY29zcGFyazovL_EVENT_ID --force

# Delete an entire schedule
wxcli location-schedules delete Y2lzY29zcGFyazovL_LOC_ID holidays Y2lzY29zcGFyazovL_SCHED_ID --force
```

> **Note:** Schedule and event IDs are name-derived (base64-encoded). Renaming a schedule or event changes its ID -- always re-fetch the ID after a name change.

### 4.4 Endpoint URL Structure

Location schedules:
```
/v1/telephony/config/locations/{locationId}/schedules
/v1/telephony/config/locations/{locationId}/schedules/{scheduleType}/{scheduleId}
/v1/telephony/config/locations/{locationId}/schedules/{scheduleType}/{scheduleId}/events
/v1/telephony/config/locations/{locationId}/schedules/{scheduleType}/{scheduleId}/events/{eventId}
```

User schedules:
```
/v1/people/{personId}/features/schedules
/v1/people/{personId}/features/schedules/{scheduleType}/{scheduleId}
/v1/people/{personId}/features/schedules/{scheduleType}/{scheduleId}/events
/v1/people/{personId}/features/schedules/{scheduleType}/{scheduleId}/events/{eventId}
```

---

## 5. Cross-Cutting Patterns

### Auth Scopes Summary

| Operation | Required Scope |
|-----------|---------------|
| Read announcements, playlists, schedules, access codes | `spark-admin:telephony_config_read` |
| Write announcements, playlists, schedules, access codes | `spark-admin:telephony_config_write` |
| List schedules (location) | `spark-admin:telephony_config_read`  |
| List schedules (user/person) | `spark-admin:people_read`  |

### Org vs. Location Scoping

| Resource | Org-Level | Location-Level |
|----------|-----------|----------------|
| Announcements | Yes (default when `location_id` is None) | Yes (pass `location_id`) |
| Playlists | Yes (created at org, assigned to locations) | No (assigned via the playlist locations endpoint) |
| Access Codes | Yes (org-level endpoint) | Yes (location-level endpoint) |
| Schedules | No | Yes (primary), also user-level |

### Typical Music On Hold Setup Workflow

1. Upload WAV files to the announcement repository (org or location level).
2. Create a playlist referencing the uploaded announcement IDs (max 25).
3. Assign the playlist to target locations via `PUT /telephony/config/announcements/playlists/{id}/locations` (see §2.3).

### Typical Holiday Schedule Workflow

1. Identify target locations (e.g., filter by country).
2. Check if a holiday schedule already exists for each location.
3. Create the schedule with all-day events, or add events to an existing schedule.
4. Periodically clean up past events and add future ones.

---

## Gotchas

These are collected from the sections above; each is stated where it was first
documented, and nothing here is new.

1. **Schedule and event IDs are name-derived, so renaming changes the ID.** They are
   base64-encoded from the schedule name — the old ID returns 404 after a rename. Always
   re-fetch the ID after a name change. Event IDs behave the same way. (§4.3, §4.4)

2. **`schedules list` does NOT include events.** It returns
   `{"schedules": [{"id", "name", "type"}]}` only. Use the details endpoint to get the
   events inside a schedule — a caller that reads `list` and reports "no events" is
   answering a different question than the one asked. (§4.3)

3. **`announcements create --file-uri` takes a URI, not a local file.** Both
   `wxcli announcements create` (org level) and `create-announcements LOCATION_ID`
   (location level) send a JSON body (`fileUri`/`fileName`/`isTextToSpeech`) to
   `POST /telephony/config/announcements` — **not** a `multipart/form-data` upload. They
   do not push local binary `.wav` bytes. For that, use the manual multipart raw HTTP path
   in §1.3. (§1)

4. **Playlist announcement IDs must go through `--json-body`.** There is no repeatable
   flag for `announcementIds` on `announcement-playlists create`. Maximum 25 announcements
   per playlist. (§2, §5)

5. **Announcements and Playlists are not supported on Webex for Government (FedRAMP).**
   Both APIs are explicitly excluded. See
   [authentication.md → FedRAMP](authentication.md#webex-for-government-fedramp) for the
   full restriction list. (§1)

6. **Deleting specific access codes uses PUT with a `deleteCodes` array, not DELETE.** This
   applies at both location and org level. The `DELETE` verb means *delete all*, and only at
   the location level — so reaching for it to remove one code removes every code. This is
   the destructive-PUT shape described in the root `CLAUDE.md` known issue #20. (§3)

---

## See Also

- **[Call Features — Major](call-features-major.md)** — Auto Attendants, Call Queues, and Hunt Groups that consume schedules for time-based routing
