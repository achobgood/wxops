# Location Call Settings — Announcements, Playlists, Schedules & Access Codes

## Sources

- wxc_sdk v1.30.0
- OpenAPI spec: specs/webex-cloud-calling.json
- developer.webex.com Location Call Settings APIs

Reference for managing audio media (announcements, playlists), time-based routing (schedules), and outgoing-permission bypass codes at the location and org level via the `wxc_sdk`.

> **Not supported for Webex for Government (FedRAMP)** — Announcements and Playlists APIs are explicitly excluded. See [authentication.md → FedRAMP](authentication.md#webex-for-government-fedramp) for all FedRAMP restrictions.

---

## 1. Announcements Repository

The announcement repository stores binary audio files (WAV) used by Auto Attendants, Call Queues, and Music On Hold. Files can be uploaded at the **organization level** or scoped to a **specific location**.

**SDK access path:** `api.telephony.announcements_repo`

**API class:** `AnnouncementsRepositoryApi` (base: `telephony/config`)

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

### 1.2 Methods

#### `list(...)` — List announcement greetings

```python
def list(
    self,
    location_id: str = None,    # None = org-level; "all" or "locations" or specific ID
    order: str = None,           # Sort by "fileName" or "fileSize" (ascending default)
    file_name: str = None,       # Filter by file name
    file_type: str = None,       # Filter by file type
    media_file_type: str = None, # Filter by media file type
    name: str = None,            # Filter by announcement label
    org_id: str = None,
    **params
) -> Generator[RepoAnnouncement, None, None]
```

- Returns a **paginated generator** of `RepoAnnouncement` objects.
- Without `location_id`, returns enterprise (org) level announcements.
- With `location_id` set to a specific location ID, returns that location's announcements.
- Special values for `location_id`: `"all"` (all levels), `"locations"` (all location-level).

**Required scope:** `spark-admin:telephony_config_read`

#### `upload_announcement(...)` — Upload a new audio file

```python
def upload_announcement(
    self,
    name: str,                          # Display name (required)
    file: Union[BufferedReader, str],    # File path (str) or open binary reader
    upload_as: str = None,              # Filename for upload (required if file is a reader)
    location_id: str = None,            # None = org level
    org_id: str = None,
) -> str                                # Returns the new announcement ID
```

- Accepts a **file path** (str) or a **BufferedReader** / `BytesIO` object.
- When passing a reader, `upload_as` is required and must be a `.wav` filename.
- Uses `multipart/form-data` with `audio/wav` content type internally.
- Without `location_id`, uploads to org-level repository.
- With `location_id`, uploads to that location's repository.

**Required scope:** `spark-admin:telephony_config_write`

**Usage examples:**

```python
# Upload from file path
ann_id = api.telephony.announcements_repo.upload_announcement(
    name='Welcome Greeting', file='/path/to/greeting.wav'
)

# Upload from open file handle
with open('greeting.wav', mode='rb') as f:
    ann_id = api.telephony.announcements_repo.upload_announcement(
        name='Welcome Greeting', file=f, upload_as='greeting.wav'
    )

# Upload from bytes via BytesIO
import io
binary_file = io.BytesIO(wav_bytes)
ann_id = api.telephony.announcements_repo.upload_announcement(
    name='Welcome Greeting', file=binary_file, upload_as='greeting.wav'
)

# Upload to a specific location
ann_id = api.telephony.announcements_repo.upload_announcement(
    name='Location Greeting', file='greeting.wav', location_id='<location_id>'
)
```

#### `details(...)` — Get single announcement details

```python
def details(
    self,
    announcement_id: str,
    location_id: str = None,    # None = org level
    org_id: str = None,
) -> RepoAnnouncement
```

- Returns `feature_reference_count`, `feature_references`, and `playlists` (which `list()` does not).

**Required scope:** `spark-admin:telephony_config_read`

#### `modify(...)` — Replace an existing announcement file

```python
def modify(
    self,
    announcement_id: str,
    name: str,                          # New display name
    file: Union[BufferedReader, str],    # Replacement file
    upload_as: str = None,
    location_id: str = None,
    org_id: str = None,
) -> str                                # Returns announcement ID
```

- Same file-handling semantics as `upload_announcement`.
- Uses `multipart/form-data` PUT request internally.

**Required scope:** `spark-admin:telephony_config_write`

#### `delete(...)` — Delete an announcement

```python
def delete(
    self,
    announcement_id: str,
    location_id: str = None,    # None = org level
    org_id: str = None,
)
```

**Required scope:** `spark-admin:telephony_config_write`

#### `usage(...)` — Get repository storage usage

```python
def usage(
    self,
    location_id: str = None,    # None = org level
    org_id: str = None,
) -> RepositoryUsage
```

- Returns file size limits and current usage.

**Required scope:** `spark-admin:telephony_config_read`

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

**Gotcha:** Upload and modify (file replacement) use `multipart/form-data` with `audio/wav` content type. The SDK handles this via `upload_announcement()` and `modify()`. For raw HTTP, you would need to construct the multipart body manually -- the `rest_put`/`rest_post` JSON helpers do not handle file uploads.

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
wxcli announcements show-usage Y2lzY29zcGFyazovL_LOC_ID

# Delete an org-level announcement
wxcli announcements delete Y2lzY29zcGFyazovL_ANN_ID --force

# Delete a location-level announcement
wxcli announcements delete-announcements Y2lzY29zcGFyazovL_LOC_ID Y2lzY29zcGFyazovL_ANN_ID --force

# Update an org-level announcement (metadata via --json-body)
wxcli announcements update Y2lzY29zcGFyazovL_ANN_ID --json-body '{"name": "Updated Greeting"}'
```

> **Note:** File upload (creating new announcements) requires `multipart/form-data` which the CLI does not support. Use the SDK `upload_announcement()` method or raw HTTP with `curl` for uploads.

### 1.4 Key Patterns

- **Org vs. location scoping:** Every method takes an optional `location_id`. When `None`, the operation targets the org-level repository. When set, it targets that location's repository.
- **URL pattern:** Org-level uses `/telephony/config/announcements/...`; location-level uses `/telephony/config/locations/{locationId}/announcements/...`.
- **File format:** WAV audio files. The SDK hard-codes `audio/wav` as the MIME type for uploads.
- **Checking references before delete:** Use `details()` to inspect `feature_references` and `playlists` before deleting an announcement that may be in use.

---

## 2. Playlists (Music On Hold)

Playlists group multiple announcement files for Music On Hold. A playlist can contain up to **25 announcement files** and can be assigned to one or more locations.

**SDK access path:** `api.telephony.playlists`

**API class:** `PlayListApi` (base: `telephony/config/announcements/playlists`)

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
| `announcements` | `list[PlaylistAnnouncement]` | Announcement details (populated in `details()`) |

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

### 2.2 Methods

#### `list(...)` — List all playlists

```python
def list(
    self,
    org_id: str = None,
) -> list[PlayList]
```

- Returns a **list** (not a generator) of all playlists in the org.
- Does **not** use pagination.

**Required scope:** `spark-admin:telephony_config_read`

#### `create(...)` — Create a new playlist

```python
def create(
    self,
    name: str,                        # Unique playlist name
    announcement_ids: list[str],      # IDs of announcements to include (max 25)
    org_id: str = None,
) -> str                              # Returns the new playlist ID
```

- **Max 25 announcements** per playlist.
- Announcements must already exist in the repository.

**Required scope:** `spark-admin:telephony_config_write`

#### `details(...)` — Get playlist details

```python
def details(
    self,
    play_list_id: str,
    org_id: str = None,
) -> PlayList
```

- Returns full details including the `announcements` list.

**Required scope:** `spark-admin:telephony_config_read`

#### `modify(...)` — Update a playlist

```python
def modify(
    self,
    play_list_id: str,
    name: str = None,                    # New name (optional)
    announcement_ids: list[str] = None,  # New set of announcement IDs (optional)
    org_id: str = None,
)
```

- You can update the name, the announcement list, or both.

**Required scope:** `spark-admin:telephony_config_write`

#### `delete(...)` — Delete a playlist

```python
def delete(
    self,
    play_list_id: str,
    org_id: str = None,
)
```

**Required scope:** `spark-admin:telephony_config_write`

#### `usage(...)` — Get playlist usage

```python
def usage(
    self,
    play_list_id: str,
    playlist_usage_type: PlaylistUsageType = None,  # Filter by 'feature' or 'location'
) -> PlaylistUsage
```

- Returns which locations and features reference this playlist.

- **Scopes:** `spark-admin:telephony_config_read` (the `PlayListApi` class docstring confirms all read operations use `spark-admin:telephony_config_read`; the `usage()` method itself has no explicit scope docstring but inherits from the class-level scope) <!-- Verified via wxc_sdk source (PlayListApi class docstring) 2026-03-19 -->

#### `assigned_locations(...)` — List locations assigned to a playlist

```python
def assigned_locations(
    self,
    play_list_id: str,
    org_id: str = None,
) -> list[IdAndName]
```

- Returns `IdAndName` objects (id + name) for each assigned location.

**Required scope:** `spark-admin:telephony_config_read`

#### `modify_assigned_locations(...)` — Assign playlist to locations

```python
def modify_assigned_locations(
    self,
    play_list_id: str,
    location_ids: list[str],    # Full list of location IDs to assign
    org_id: str = None,
)
```

- This **replaces** the entire location assignment list. To add a location, you must include all existing location IDs plus the new one.
- Assigning a playlist to a location sets it as that location's Music On Hold source.

**Required scope:** `spark-admin:telephony_config_write`

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

- **Playlists are org-level only.** They are created at the org level, then assigned to locations via `modify_assigned_locations()`.
- **Workflow:** Upload announcements to the repo first, then create a playlist referencing those announcement IDs, then assign the playlist to locations.
- **Location assignment is a full replace**, not incremental. Always read current assignments with `assigned_locations()` before modifying.

---

## 3. Access Codes

Access codes (also called authorization codes) let authorized users bypass outgoing or incoming calling permission restrictions. They exist at two levels: **location** and **organization**.

### 3.1 Location Access Codes

**SDK access path:** `api.telephony.access_codes`

**API class:** `LocationAccessCodesApi` (base: `telephony/config/locations`)

**Endpoint pattern:** `/telephony/config/locations/{locationId}/outgoingPermission/accessCodes`

#### Data Model: `AuthCode`

| Field | Type | Notes |
|-------|------|-------|
| `code` | `str` | The authorization code string |
| `description` | `str` | Human-readable description |
| `level` | `AuthCodeLevel` | `LOCATION` or `CUSTOM` (read-only, set by system) |

#### Methods

##### `read(...)` — List access codes for a location

```python
def read(
    self,
    location_id: str,
    org_id: str = None,
) -> list[AuthCode]
```

**Required scope:** `spark-admin:telephony_config_read`

##### `create(...)` — Add access codes to a location

```python
def create(
    self,
    location_id: str,
    access_codes: list[AuthCode],    # One or more codes to add
    org_id: str = None,
) -> list[AuthCode]
```

- Can add multiple codes in a single call.

**Required scope:** `spark-admin:telephony_config_write`

##### `delete_codes(...)` — Delete specific access codes

```python
def delete_codes(
    self,
    location_id: str,
    access_codes: list[Union[str, AuthCode]],    # Code strings or AuthCode objects
    org_id: str = None,
) -> list[AuthCode]
```

- Accepts either `AuthCode` objects or plain code strings.
- Uses a PUT request with `deleteCodes` in the body (not a DELETE endpoint).

**Required scope:** `spark-admin:telephony_config_write`

##### `delete_all(...)` — Delete all access codes for a location

```python
def delete_all(
    self,
    location_id: str,
    org_id: str = None,
)
```

- Wipes all codes for the specified location.

**Required scope:** `spark-admin:telephony_config_write`

### 3.2 Organization Access Codes

**SDK access path:** `api.telephony.org_access_codes`

**API class:** `OrganisationAccessCodesApi` (base: `telephony/config/outgoingPermission/accessCodes`)

Organization-level access codes apply across all locations in the org.

#### Methods

##### `list(...)` — List org-level access codes

```python
def list(
    self,
    code: list[str] = None,           # Filter by code values (comma-separated internally)
    description: list[str] = None,     # Filter by descriptions (comma-separated internally)
    org_id: str = None,
    **params
) -> Generator[AuthCode, None, None]
```

- Returns a **paginated generator** (unlike the location-level `read()` which returns a plain list).
- Supports filtering by code and description.

**Required scope:** `spark-admin:telephony_config_read`

##### `create(...)` — Create org-level access codes

```python
def create(
    self,
    access_codes: list[AuthCode],    # Max 10,000 per request
    org_id: str = None,
)
```

- Supports up to **10,000 codes per request**.

**Required scope:** `spark-admin:telephony_config_write`

##### `delete(...)` — Delete org-level access codes

```python
def delete(
    self,
    delete_codes: list[str] = None,    # Code strings to delete (max 10,000 per request)
    org_id: str = None,
)
```

- Supports up to **10,000 codes per request**.
- Uses a PUT request with `deleteCodes` in the body (same pattern as location-level).

**Required scope:** `spark-admin:telephony_config_write`

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
- **Delete uses PUT:** Both location and org `delete` methods send a PUT with `deleteCodes` in the body, not an HTTP DELETE. The SDK handles this transparently.
- **Batch limits:** Org-level create and delete support up to 10,000 codes per request (confirmed in SDK docstrings: "max limit is 10k per request"). Location-level create/delete has no documented batch limit in the SDK source -- the `LocationAccessCodesApi.create()` and `delete_codes()` methods accept a `list[AuthCode]` with no stated maximum. <!-- Verified via wxc_sdk source (org_access_codes/__init__.py + access_codes.py) 2026-03-19 -->

---

## 4. Schedules & Holiday Schedules

Schedules define time windows (business hours, holidays) that control call routing behavior for features like Auto Attendants. They can be created at the **location** or **person (user)** level.

**SDK access path:** `api.telephony.schedules`

**API class:** `ScheduleApi` (base depends on context: `telephony/config/locations` for location schedules, `people` for user schedules)

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
| `new_name` | `str` | New name (only used in `update()`) |
| `schedule_id` | `str` | Unique identifier (alias: `id`) |
| `level` | `ScheduleLevel` | Scope level (returned in user-level listing) |
| `location_name` | `str` | Location name (returned by `list()` for location schedules) |
| `location_id` | `str` | Location identifier (returned by `list()` for location schedules) |
| `schedule_type` | `ScheduleType` | `businessHours` or `holidays` (alias: `type`) |
| `events` | `list[Event]` | List of events in this schedule |

**Convenience constructor:**

```python
Schedule.business(
    name: str,
    day_start: Union[int, datetime.time] = 9,
    day_end: Union[int, datetime.time] = 17,
    break_start: Union[int, datetime.time] = 12,
    break_end: Union[int, datetime.time] = 13,
) -> Schedule
```

Creates a Mon-Fri business hours schedule with two events per day (morning + afternoon, split by lunch break). Integers are interpreted as hours.

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

**Convenience constructor:**

```python
Event.day_start_end(
    name: str,
    day: datetime.date,
    start_time: Union[int, datetime.time],
    end_time: Union[int, datetime.time],
) -> Event
```

Creates an event on a specific day with given start/end times and a weekly recurrence on that day of the week.

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

**Convenience constructor:**

```python
Recurrence.every_week(day: Union[ScheduleDay, datetime.date]) -> Recurrence
```

Creates a weekly recurrence for a single day that repeats forever.

#### Supporting Recurrence Models

- **`RecurWeekly`** — boolean flags for each day of the week + `recur_interval` (weeks between occurrences). Helper: `RecurWeekly.single_day(day, recur_interval=1)`.
- **`RecurYearlyByDate`** — `day_of_month` (int) + `month` (ScheduleMonth enum). Helper: `RecurYearlyByDate.from_date(date)`.
- **`RecurYearlyByDay`** — `day` (ScheduleDay) + `week` (ScheduleWeek: FIRST/SECOND/THIRD/FOURTH) + `month` (ScheduleMonth).
- **`RecurDaily`** — `recur_interval` (int, days between occurrences). User schedules only.

### 4.2 Methods

All schedule methods take `obj_id` as the first parameter, which is a **location ID** (for location schedules) or a **user/person ID** (for user schedules).

#### `list(...)` — List schedules

```python
def list(
    self,
    obj_id: str,                          # Location or user ID
    org_id: str = None,
    schedule_type: ScheduleType = None,   # Filter by businessHours or holidays
    name: str = None,                     # Filter by name
    **params
) -> Generator[Schedule, None, None]
```

- Returns a **paginated generator**.
- Listing does **not** include events; use `details()` to get events.

**Required scope:** Depends on schedule level. The wxc_sdk `ScheduleApi.list()` docstring says `spark-admin:people_read` (this applies when listing **person/user** schedules via `/people/{id}/features/schedules`). For **location** schedules via `/telephony/config/locations/{id}/schedules`, the OpenAPI spec requires `spark-admin:telephony_config_read`. <!-- Corrected via OpenAPI spec + wxc_sdk source 2026-03-19: person schedules use people_read, location schedules use telephony_config_read -->

#### `details(...)` — Get schedule details with events

```python
def details(
    self,
    obj_id: str,
    schedule_type: ScheduleTypeOrStr,
    schedule_id: str,
    org_id: str = None,
) -> Schedule
```

- Returns the full schedule including all `events`.

**Required scope:** `spark-admin:telephony_config_read`

#### `create(...)` — Create a schedule

<!-- Verified via CLI implementation 2026-03-17: Schedule create/update works with just name + schedule_type for holidays type. No issues found — events can be added later via event_create(). -->

```python
def create(
    self,
    obj_id: str,
    schedule: Schedule,    # Must include name, schedule_type, and events
    org_id: str = None,
) -> str                   # Returns the new schedule ID
```

**Required scope:** `spark-admin:telephony_config_write`

#### `update(...)` — Update a schedule

```python
def update(
    self,
    obj_id: str,
    schedule: Schedule,
    schedule_type: ScheduleTypeOrStr = None,   # Default: from schedule object
    schedule_id: str = None,                   # Default: from schedule object
    org_id: str = None,
) -> str                                       # Returns schedule ID (changes if name changed)
```

> **Important:** The schedule ID **changes** if the schedule name is modified.

<!-- Verified via CLI implementation 2026-03-17: Schedule IDs are name-derived (base64-encoded from the schedule name). Renaming a schedule changes its ID — the old ID returns 404 after rename. Always re-fetch the ID after a name change. -->

**Required scope:** `spark-admin:telephony_config_write`

#### `delete_schedule(...)` — Delete a schedule

```python
def delete_schedule(
    self,
    obj_id: str,
    schedule_type: ScheduleTypeOrStr,
    schedule_id: str,
    org_id: str = None,
)
```

**Required scope:** `spark-admin:telephony_config_write`

#### `event_details(...)` — Get a single event

```python
def event_details(
    self,
    obj_id: str,
    schedule_type: ScheduleTypeOrStr,
    schedule_id: str,
    event_id: str,
    org_id: str = None,
) -> Event
```

**Required scope:** `spark-admin:telephony_config_read`

#### `event_create(...)` — Add an event to an existing schedule

```python
def event_create(
    self,
    obj_id: str,
    schedule_type: ScheduleTypeOrStr,
    schedule_id: str,
    event: Event,
    org_id: str = None,
) -> str    # Returns the new event ID
```

**Required scope:** `spark-admin:telephony_config_write`

#### `event_update(...)` — Update an event

```python
def event_update(
    self,
    obj_id: str,
    schedule_type: ScheduleTypeOrStr,
    schedule_id: str,
    event: Event,
    event_id: str = None,    # Default: from event object
    org_id: str = None,
) -> str                     # Returns event ID (changes if name changed)
```

> **Important:** The event ID **changes** if the event name is modified.

**Required scope:** `spark-admin:telephony_config_write`

#### `event_delete(...)` — Delete an event

```python
def event_delete(
    self,
    obj_id: str,
    schedule_type: ScheduleTypeOrStr,
    schedule_id: str,
    event_id: str,
    org_id: str = None,
)
```

**Required scope:** `spark-admin:telephony_config_write`

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
<!-- Verified via CLI implementation 2026-03-17 -->

**Gotcha:** The `ScheduleApi` import path is `wxc_sdk.common.schedules`, NOT `wxc_sdk.telephony.schedules`.

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

### 4.4 US Holidays Example (from `examples/us_holidays.py`)

The SDK repo includes a complete example showing how to programmatically create and maintain a "National Holidays" schedule across all US locations. Key patterns from this example:

**Full workflow:**

1. **Get US locations:** Filter `api.locations.list()` by `address.country == 'US'`.
2. **Get holidays:** Uses the `calendarific` package to fetch US national holidays for a year range.
3. **Check for existing schedule:** List holiday schedules filtered by name `"National Holidays"`.
4. **Create or update:**
   - If no schedule exists, create a new one with all future holiday events.
   - If schedule exists, get details (to load events), delete past events, and add missing future events.

**Key code patterns from the example:**

```python
# Access the schedules API
ats = api.telephony.schedules

# List holiday schedules for a location, filter by name
schedule = next(
    (s for s in ats.list(
        obj_id=location.location_id,
        schedule_type=ScheduleType.holidays,
        name='National Holidays'
    ) if s.name == 'National Holidays'),
    None
)

# Get full details (list doesn't include events)
schedule = ats.details(
    obj_id=location.location_id,
    schedule_type=ScheduleType.holidays,
    schedule_id=schedule.schedule_id
)

# Create an all-day holiday event
event = Event(
    name='Independence Day 2026',
    start_date=date(2026, 7, 4),
    end_date=date(2026, 7, 4),
    all_day_enabled=True
)

# Create a new holiday schedule with events
schedule = Schedule(
    name='National Holidays',
    schedule_type=ScheduleType.holidays,
    events=[event1, event2, ...]
)
schedule_id = ats.create(obj_id=location.location_id, schedule=schedule)

# Add a single event to an existing schedule
event_id = ats.event_create(
    obj_id=location.location_id,
    schedule_type=ScheduleType.holidays,
    schedule_id=schedule.schedule_id,
    event=event
)

# Delete a past event
ats.event_delete(
    obj_id=location.location_id,
    schedule_type=ScheduleType.holidays,
    schedule_id=schedule.schedule_id,
    event_id=event.event_id
)

# Delete an entire holiday schedule
ats.delete_schedule(
    obj_id=location.location_id,
    schedule_type=ScheduleType.holidays,
    schedule_id=schedule.schedule_id
)
```

**Threading pattern:** The example uses `ThreadPoolExecutor` with per-location locks to safely update schedules across multiple locations concurrently. Each location gets its own lock to prevent race conditions when multiple years are processed in parallel.

**Holiday event filtering:** Events are excluded if they fall on a Sunday or are in the past (`holiday.date >= today and holiday.date.weekday() != 6`).

---

## 5. Cross-Cutting Patterns

### Auth Scopes Summary

| Operation | Required Scope |
|-----------|---------------|
| Read announcements, playlists, schedules, access codes | `spark-admin:telephony_config_read` |
| Write announcements, playlists, schedules, access codes | `spark-admin:telephony_config_write` |
| List schedules (location) | `spark-admin:telephony_config_read` <!-- Corrected via OpenAPI spec 2026-03-19 --> |
| List schedules (user/person) | `spark-admin:people_read` <!-- Verified via OpenAPI spec + wxc_sdk source 2026-03-19 --> |

### Org vs. Location Scoping

| Resource | Org-Level | Location-Level |
|----------|-----------|----------------|
| Announcements | Yes (default when `location_id` is None) | Yes (pass `location_id`) |
| Playlists | Yes (created at org, assigned to locations) | No (assigned via `modify_assigned_locations`) |
| Access Codes | Yes (`OrganisationAccessCodesApi`) | Yes (`LocationAccessCodesApi`) |
| Schedules | No | Yes (primary), also user-level |

### Typical Music On Hold Setup Workflow

1. Upload WAV files to the announcement repository (org or location level).
2. Create a playlist referencing the uploaded announcement IDs (max 25).
3. Assign the playlist to target locations via `modify_assigned_locations()`.

### Typical Holiday Schedule Workflow

1. Identify target locations (e.g., filter by country).
2. Check if a holiday schedule already exists for each location.
3. Create the schedule with all-day events, or add events to an existing schedule.
4. Periodically clean up past events and add future ones.

---

## See Also

- **[Call Features — Major](call-features-major.md)** — Auto Attendants, Call Queues, and Hunt Groups that consume schedules for time-based routing
