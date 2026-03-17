# wxcadm Core Architecture

Reference for the core modules that form the foundation of wxcadm: entry point, organization management, API transport, data models, and exceptions.

Source: `wxcadm/__init__.py`, `wxcadm/webex.py`, `wxcadm/org.py`, `wxcadm/common.py`, `wxcadm/models.py`, `wxcadm/exceptions.py`

---

## Object Model Hierarchy

```
Webex                           # Entry point. Holds token, orgs list.
 +-- api: WebexApi              # Session-based HTTP client (added v4.6.0)
 +-- me: Me                     # Lazy-loaded identity of the token owner
 +-- orgs: list[Org]            # All orgs the token can manage
 +-- org: Org                   # Default org (first, or selected by org_id)
      +-- api: WebexApi         # Org-scoped HTTP client (auto-adds orgId param)
      +-- locations: LocationList
      +-- people: PersonList
      +-- devices: DeviceList
      +-- call_queues: CallQueueList
      +-- hunt_groups: HuntGroupList
      +-- auto_attendants: AutoAttendantList
      +-- workspaces: WorkspaceList
      +-- virtual_lines: VirtualLineList
      +-- numbers: NumberList
      +-- licenses: WebexLicenseList
      +-- announcements: AnnouncementList
      +-- call_routing: CallRouting
      +-- webhooks: Webhooks
      +-- ...  (20+ lazy-loaded collection properties)
```

Nearly every collection property on `Org` is **lazy-loaded** -- the API call fires the first time the property is accessed, then the result is cached in a private `_attr`.

---

## Webex Class

**Module:** `wxcadm/webex.py`

The entry point. Authenticates with a Webex API access token, discovers orgs, and provides cross-org person lookups.

### Constructor

```python
wxcadm.Webex(
    access_token: str,
    fast_mode: bool = False,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    refresh_token: Optional[str] = None,
    org_id: Optional[str] = None,
    auto_refresh_token: bool = False,
    read_only: bool = False,
) -> Webex
```

| Parameter | Purpose |
|-----------|---------|
| `access_token` | Webex API bearer token (required) |
| `fast_mode` | Skip per-person Call Control API calls on init. **Loses phone number data.** |
| `client_id` / `client_secret` / `refresh_token` | Needed only if you plan to call `get_new_token()` |
| `org_id` | Pin `self.org` to a specific org (UUID or full Webex ID accepted) |
| `auto_refresh_token` | Auto-refresh token when < 30 min from expiry. **Still in development -- do not use.** |
| `read_only` | If True, skips `GET /v1/organizations` (which needs admin scope) and discovers the org from `/v1/people/me` instead |

**Init behavior:**
1. Creates a `WebexApi` instance at `self.api`.
2. Sets the global `_webex_headers` dict (used by the legacy `webex_api_call()` function).
3. If `read_only=False`: calls `GET /v1/organizations`, builds an `Org` for each, populates `self.orgs`.
4. If `read_only=True`: calls `GET /v1/people/me`, extracts `orgId`, creates a single `Org`.
5. Sets `self.org` to the first org, or to the org matching `org_id` if provided.

**Raises on init:**
- `TokenError` -- invalid/rejected access token (non-200 from `/v1/organizations`)
- `OrgError` -- no orgs returned, or `org_id` not found

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `orgs` | `list[Org]` | All orgs the token can manage |
| `org` | `Org` | Default org |
| `client_id` | `Optional[str]` | Integration/Service App client ID |
| `client_secret` | `Optional[str]` | Integration/Service App client secret |
| `refresh_token` | `Optional[str]` | Refresh token for token renewal |
| `access_token_expires` | `Optional[datetime]` | Set after `get_new_token()` |
| `refresh_token_expires` | `Optional[datetime]` | Set after `get_new_token()` |

### Properties

```python
@property
def headers(self) -> dict
```
Returns the `{"Authorization": "Bearer ..."}` dict.

```python
@property
def me(self) -> Me
```
Lazy-loaded `Me` instance representing the token owner. Calls `GET /v1/people/me` on first access.

### Methods

```python
def get_new_token(
    self,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    refresh_token: Optional[str] = None,
) -> dict
```
Refreshes the access token via `POST /v1/access_token`. Updates the instance and global headers in-place. Returns the token response dict. Raises `ValueError` if credentials are missing.

```python
def get_org_by_name(self, name: str) -> Org
```
Case-insensitive partial match on org name. Raises `KeyError` if not found.

```python
def get_org_by_id(self, id: str) -> Org
```
Matches against `org.id` or the decoded Spark ID. Raises `KeyError` if not found.

```python
def get_person_by_email(self, email: str) -> Optional[Person]
```
Cross-org lookup. Calls `GET /v1/people?email=...&callingData=True`. Returns `None` if no match. Raises `APIError` if Webex returns more than one record.

```python
def get_person_by_id(self, id: str) -> Optional[Person]
```
Cross-org lookup by Webex person ID. Same behavior as `get_person_by_email`.

---

## Org Class

**Module:** `wxcadm/org.py`

Represents a Webex Organization. Central hub for accessing all telephony resources.

### Constructor

```python
Org(
    api_connection: Union[WebexApi, str],
    name: str,
    id: str,
    parent: Webex = None,
    xsi: bool = False,
    **kwargs,
)
```

Normally created by `Webex.__init__()`, not instantiated directly. Creates its own `WebexApi` instance scoped to this org (auto-injects `orgId` param on every request).

### Lazy-Loaded Collection Properties

All are **cached after first access**. The API call happens on first read.

| Property | Return Type | Description |
|----------|-------------|-------------|
| `locations` | `LocationList` | All locations in the org |
| `people` | `PersonList` | All people (users) in the org |
| `devices` | `DeviceList` | All devices in the org |
| `numbers` | `NumberList` | All phone numbers in the org |
| `call_queues` | `CallQueueList` | All call queues |
| `hunt_groups` | `HuntGroupList` | All hunt groups |
| `auto_attendants` | `AutoAttendantList` | All auto attendants |
| `workspaces` | `WorkspaceList` | All workspaces |
| `virtual_lines` | `VirtualLineList` | All virtual lines |
| `licenses` | `WebexLicenseList` | All licenses in the org |
| `announcements` | `AnnouncementList` | All announcements |
| `playlists` | `PlaylistList` | All playlists |
| `voicemail_groups` | `VoicemailGroupList` | All voicemail groups |
| `dect_networks` | `DECTNetworkList` | All DECT networks |
| `paging_groups` | `list[PagingGroup]` | All paging groups |
| `supported_devices` | `SupportedDeviceList` | Supported device models |
| `translation_patterns` | `TranslationPatternList` | Translation patterns (org + location level) |
| `reports` | `ReportList` | All reports |
| `number_management_jobs` | `NumberManagementJobList` | Number management jobs |
| `user_move_jobs` | `UserMoveJobList` | User move jobs |
| `rebuild_phones_jobs` | `RebuildPhonesJobList` | Rebuild phones jobs |

### Non-Cached Properties (re-fetched each access)

| Property | Return Type | Description |
|----------|-------------|-------------|
| `webhooks` | `Webhooks` | Webhooks for the org |
| `usergroups` | `UserGroups` | User groups |
| `applications` | `WebexApplications` | Service apps and integrations |
| `calls` | `Calls` | Active calls instance |
| `queue_settings` | `OrgQueueSettings` | Org-level queue settings |
| `compliance_announcement_settings` | `ComplianceAnnouncementSettings` | Call recording compliance settings |
| `recording_vendor` | `OrgRecordingVendorSelection` | Recording vendor config |

### Computed Properties

```python
@property
def spark_id(self) -> str
```
Base64-decodes the Webex org ID to the Spark URI (e.g. `ciscospark://us/ORGANIZATION/...`).

```python
@property
def org_id(self) -> str
```
Alias for `self.id`. Convenience for API calls that need an `orgId` parameter.

### Eagerly-Set Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Organization display name |
| `id` | `str` | Webex organization ID |
| `xsi` | `dict` | XSI endpoint details (populated by `get_xsi_endpoints()`) |
| `call_routing` | `CallRouting` | Call routing instance (created in `__init__`) |
| `api` | `WebexApi` | Org-scoped API client |

### Methods

#### Resource Lookup

```python
def get_number_assignment(self, number: str) -> object | None
```
Finds the owner (Person, Workspace, etc.) of a phone number. Uses partial match to handle E.164 vs. national format differences. Returns `None` if unassigned.

```python
def get_paging_group(
    self,
    id: Optional[str] = None,
    name: Optional[str] = None,
    spark_id: Optional[str] = None,
) -> Optional[PagingGroup]
```
Search order: id, then name, then spark_id. Raises `ValueError` if called with no arguments.

```python
def get_device_by_id(self, device_id: str) -> Device | False
```
Finds a device by ID or decoded Spark ID. Returns `False` if not found.

```python
def get_workspace_devices(self, workspace: Optional[Workspace] = None) -> list
```
Without argument: returns list of Workspace instances with devices populated from number data. With argument: returns `workspace.devices`.

```python
def get_all_monitoring(self) -> dict
```
Returns a dict with keys `'people'`, `'workspaces'`, `'park_extensions'`, `'virtual_lines'`, each mapping monitored entity IDs to lists of monitoring Person/Workspace instances. Iterates all Webex Calling people and workspaces -- can be slow on large orgs.

#### License Helpers

```python
def get_license_name(self, license_id: str) -> Optional[str]
```
Returns license name by ID, or `None`.

#### XSI

```python
def get_xsi_endpoints(self) -> Optional[dict]
```
Calls `GET /v1/organizations/{id}?callingData=true` to populate `self.xsi` dict with keys: `xsi_domain`, `actions_endpoint`, `events_endpoint`, `events_channel_endpoint`. Returns `None` if XSI is not enabled.

#### Audit & Recordings

```python
def get_audit_events(self, start: str, end: str) -> AuditEventList
```
`start`/`end` format: `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS.000Z`. Auto-pads date-only strings.

```python
def get_recordings(self, **kwargs) -> RecordingList
```
<!-- NEEDS VERIFICATION --> kwargs likely include date range and other filters -- see RecordingList for details.

#### Admin Operations

```python
def delete_person(self, person: Person) -> bool
```
Calls `DELETE /v1/people/{id}`. Removes all licenses, numbers, and devices. Resets internal people cache.

#### Deprecated Methods

| Method | Replacement |
|--------|-------------|
| `get_person_by_id(id)` | `org.people.get(id=id)` |
| `get_person_by_email(email)` | `org.people.get(email=email)` |
| `get_hunt_group_by_id(id)` | `org.hunt_groups.get(id=id)` |
| `recorded_people` (property) | `org.people.recorded(True)` |
| `wxc_licenses` (property) | `org.licenses.webex_calling()` |
| `get_wxc_person_license()` | Use `org.licenses` / `WebexLicenseList` directly |
| `get_wxc_standard_license()` | Use `org.licenses` / `WebexLicenseList` directly |

---

## WebexLicenseList and WebexLicense

**Module:** `wxcadm/org.py`

### WebexLicenseList

Extends `collections.UserList`. Fetches all licenses from `GET /v1/licenses` on init.

```python
WebexLicenseList(org: Org)
```

**Attributes:**
- `data: list[WebexLicense]` -- the license objects
- `assignable_subscriptions: list[str]` -- unique subscription IDs available for assignment

**Methods:**

```python
def refresh(self) -> None
```
Re-fetches license data from the API and updates counts.

```python
def get(
    self,
    id: Optional[str] = None,
    name: Optional[str] = None,
    subscription: Optional[str] = None,
) -> Optional[Union[WebexLicense, list[WebexLicense]]]
```
Lookup by ID (exact), name (exact), or subscription (case-insensitive). Returns single match, list of matches, or `None`.

```python
def webex_calling(
    self,
    type: str = 'all',
    available_licenses_only: bool = False,
) -> list[WebexLicense]
```
Filter to Webex Calling licenses. `type` options: `'all'`, `'professional'`, `'workspace'`, `'hotdesk'`, `'standard'`.

```python
def get_assignable_license(
    self,
    license_type: str,
    ignore_license_overage: bool = False,
) -> WebexLicense
```
Finds an available license of the requested type from an assignable subscription. Raises `LicenseOverageError` or `NotSubscribedForLicenseError` as appropriate. `license_type` values: `'professional'`, `'workspace'`, `'standard'`, `'hotdesk'`.

### WebexLicense

Represents a single license entry.

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | License name (e.g. "Webex Calling - Professional") |
| `id` | `str` | License ID |
| `total` | `int` | Total units in subscription |
| `consumed` | `int` | Consumed units |
| `consumed_by_users` | `int` | Units consumed by users |
| `consumed_by_workspaces` | `int` | Units consumed by workspaces |
| `subscription` | `Optional[str]` | Subscription ID |
| `wxc_license` | `bool` | True if this is a Webex Calling license |
| `wxc_type` | `Optional[str]` | `'professional'`, `'workspace'`, `'hotdesk'`, `'standard'`, or `None` |

Type detection is name-based: "Professional" -> `professional`, "Workspace" -> `workspace`, "Hot desk only" -> `hotdesk`, "Basic" -> `standard`.

---

## WebexApi Class

**Module:** `wxcadm/common.py`

Session-based HTTP client for the Webex API. Added in v4.6.0 to replace the standalone `webex_api_call()` function.

### Constructor

```python
WebexApi(
    access_token: str,
    org_id: Optional[str] = None,
    url_base: str = "https://webexapis.com/",
    retry_count: int = 10,
)
```

When `org_id` is provided, every request automatically includes `orgId` as a query parameter.

Uses a persistent `requests.Session` with pre-configured headers:
```
Authorization: Bearer {access_token}
Content-Type: application/json
Accept: application/json
```

### Methods

All methods handle:
- **429 Too Many Requests**: sleeps for `Retry-After` seconds, retries up to `retry_count` times
- **451 Unavailable For Legal Reasons**: cross-region redirect -- extracts new domain from error message and retries
- **Pagination**: follows `r.links['next']` until all pages are collected (GET only)

```python
def get(
    self,
    endpoint: str,
    params: Optional[dict] = None,
    items_key: str = 'items',
    kwargs: Optional[dict] = None,
) -> Union[list, dict]
```
Returns `response[items_key]` for list responses (with automatic pagination), or the full response dict for single-entity responses.

```python
def put(self, endpoint: str, payload: Optional[dict] = None, params: Optional[dict] = None) -> Union[dict, bool]
```

```python
def post(self, endpoint: str, payload: Optional[dict] = None, params: Optional[dict] = None) -> Union[dict, bool]
```

```python
def delete(self, endpoint: str, params: Optional[dict] = None) -> Union[dict, bool]
```

```python
def patch(self, endpoint: str, payload: Optional[dict] = None, params: Optional[dict] = None) -> Union[dict, bool]
```

```python
def put_upload(self, endpoint: str, payload: MultipartEncoder = None, params: Optional[dict] = None) -> Union[dict, bool]
```

```python
def post_upload(self, endpoint: str, payload: MultipartEncoder = None, params: Optional[dict] = None) -> Union[dict, bool]
```

For `put_upload` and `post_upload`, the payload must be a `requests_toolbelt.MultipartEncoder`. A separate session is created with `Content-Type` set to `payload.content_type`.

All mutating methods (PUT, POST, DELETE, PATCH) return:
- The parsed JSON response dict if the API returns a body
- `True` if the API returns success with no body
- `False` if retries are exhausted (429 scenario)

All raise `APIError` on non-retryable HTTP errors.

### Two-Instance Pattern

`Webex.__init__` creates one `WebexApi` at `self.api` (no org scope). Each `Org.__init__` creates a second `WebexApi` scoped to that org. In practice you use `org.api` for most calls.

---

## Legacy webex_api_call() Function

**Module:** `wxcadm/common.py`

```python
def webex_api_call(
    method: str,
    url: str,
    headers: Optional[dict] = None,
    params: Optional[dict] = None,
    payload: dict | MultipartEncoder | None = None,
    retry_count: Optional[int] = 5,
    domain: Optional[str] = None,
    **kwargs,
) -> Union[list, dict, bool]
```

Standalone function that predates `WebexApi`. Still in the codebase and used by some modules. Supports the same HTTP methods and retry logic as `WebexApi` but creates a new `requests.Session` per call instead of reusing one.

`method` values: `"get"`, `"post"`, `"put"`, `"put_upload"`, `"post_upload"`, `"delete"`, `"patch"`.

Uses the global `_webex_headers` dict (set during `Webex.__init__`) unless `headers` is explicitly provided.

**Prefer `WebexApi` methods over this function in new code.**

---

## Utility Functions

**Module:** `wxcadm/common.py`

```python
def console_logging(level: str = "debug", formatter: Optional[logging.Formatter] = None) -> None
```
Adds a STDOUT logging handler. `level` options: `"debug"`, `"info"`, `"warning"`, `"critical"`, `"none"` (removes handler). Default format: `%(levelname)s:\t%(message)s`.

```python
def decode_spark_id(id: str) -> str
```
Base64-decodes a Webex ID to its Spark URI. Example result: `ciscospark://us/PEOPLE/5b7ddefe-cc47-496a-8df0-18d8e4182a99`. Use `.split('/')[-1]` to extract just the UUID.

```python
def tracking_id() -> str
```
Generates a tracking ID string in the format `WXCADM_{uuid4}`.

```python
def location_finder(location_id: str, parent) -> Optional[Location]
```
Resolves a Location instance from either an Org or Location parent. Used internally.

---

## Data Models

**Module:** `wxcadm/models.py`

### LocationEmergencySettings

```python
class LocationEmergencySettings(NamedTuple):
    integration: bool   # Whether location data is being sent to RedSky
    routing: bool       # Whether 911 calls are being routed to RedSky
```

### OutboundProxy

Dataclass with `dataclass_json` serialization. Represents SIP outbound proxy configuration.

| Field | JSON Key | Type | Description |
|-------|----------|------|-------------|
| `service_type` | `sipAccessServiceType` | `str` | What the proxy is used for |
| `dns_type` | `dnsType` | `str` | DNS record type |
| `proxy_address` | `outboundProxy` | `str` | Hostname of the proxy |
| `srv_prefix` | `srvPrefix` | `Optional[str]` | SRV prefix (if DNS type is SRV) |
| `cname_records` | `cnameRecords` | `Optional[str]` | Associated CNAME records |
| `attachment_updated` | `attachmentUpdated` | `bool` | Whether proxy was updated (excluded from serialization) |

### BargeInSettings

Dataclass with `dataclass_json` serialization. Works for both Person and Workspace.

| Field | JSON Key | Type | Description |
|-------|----------|------|-------------|
| `parent` | -- | `object` | The Person or Workspace that owns these settings |
| `enabled` | `enabled` | `bool` | Whether barge-in is enabled |
| `tone_enabled` | `toneEnabled` | `bool` | Whether barge-in tone is enabled |

**Methods:**

```python
def set_enabled(self, enabled: bool) -> bool
```
PUTs the updated enabled state. Returns True on success.

```python
def set_tone_enabled(self, enabled: bool) -> bool
```
PUTs the updated tone state. Returns True on success.

API endpoint is determined by parent type:
- Person: `v1/people/{id}/features/bargeIn`
- Workspace: `v1/telephony/config/workspaces/{id}/bargeIn`

---

## Exception Hierarchy

**Module:** `wxcadm/exceptions.py`

```
Exception
 +-- OrgError                        # Org-related problems
 |    +-- LicenseError               # License problems within the org
 |         +-- NotSubscribedForLicenseError   # Not subscribed for a feature's license
 |         +-- LicenseOverageError            # Exceeded license limit
 +-- APIError                        # API communication problems
      +-- TokenError                 # Access token rejected/invalid
      +-- PutError                   # PUT operation failed
      +-- XSIError                   # XSI API problems
      |    +-- NotAllowed            # XSI action not allowed by platform/user settings
      +-- CSDMError                  # CSDM-related errors
```

**Where raised:**

| Exception | Raised by |
|-----------|-----------|
| `TokenError` | `Webex.__init__` when token is rejected |
| `OrgError` | `Webex.__init__` when no orgs found or `org_id` not found |
| `APIError` | `WebexApi` methods and `webex_api_call()` on non-retryable HTTP errors |
| `LicenseError` | `WebexLicenseList.get_assignable_license()` when no license in assignable subscriptions |
| `LicenseOverageError` | `WebexLicenseList.get_assignable_license()` when all licenses consumed |
| `NotSubscribedForLicenseError` | `WebexLicenseList.get_assignable_license()` when license type not found |

---

## Package Exports

**Module:** `wxcadm/__init__.py`

The `__init__.py` uses star-imports from most submodules to make the entire API surface available from `import wxcadm`. Key explicit imports:

- `wxcadm.Webex` -- entry point
- `wxcadm.Org`, `wxcadm.WebexLicenseList`, `wxcadm.WebexLicense` -- org management
- `wxcadm.WebexApi` -- HTTP client (from common)
- All exception classes
- All feature modules: person, location, call_queue, hunt_group, auto_attendant, workspace, virtual_line, device, number, call_routing, webhooks, announcements, recording, monitoring, dect, pstn, reports, jobs, pickup_group, models

---

## wxcadm vs. wxc_sdk Comparison

| Dimension | wxcadm | wxc_sdk |
|-----------|--------|---------|
| **Author** | Community / Kris Odoms | Cisco DevNet (official) |
| **Data model** | Mutable class instances with lazy-loaded properties | Pydantic/dataclass models, mostly immutable |
| **API transport** | `WebexApi` (session-based, auto-pagination, 429 retry) + legacy `webex_api_call()` | `WebexSimpleApi` with typed method signatures per endpoint |
| **Org scoping** | `WebexApi` auto-injects `orgId` param when scoped to an Org | Explicit `org_id` param on each API call |
| **Collection pattern** | Custom `UserList` subclasses (e.g. `PersonList`, `LocationList`) with `.get()` helpers | Returns plain lists or generators of typed objects |
| **Object hierarchy** | `Webex -> Org -> [People, Locations, ...]` with back-references to parent | Flat API -- no parent references, each call is independent |
| **Rate limiting** | Built-in 429 retry with `Retry-After` header | Built-in 429 retry |
| **XSI support** | Yes -- XSI events, calls, call queues | No |
| **CPAPI support** | Yes (internal Cisco API) <!-- NEEDS VERIFICATION --> | No |
| **Pagination** | Automatic (follows `r.links['next']`) | Automatic |
| **Auth patterns** | Token, Integration refresh, Service App flow | Token, Integration, Service App, JWT |
| **Typical use** | Admin scripts, bulk provisioning, monitoring | Any Webex integration, broader API coverage |

**When to use wxcadm:**
- You need XSI event subscriptions or real-time call control
- You want an object model where `person.org.locations` traversal is natural
- You need CPAPI access <!-- NEEDS VERIFICATION -->
- You're building admin/provisioning scripts and prefer the lazy-loaded collection pattern

**When to use wxc_sdk:**
- You need broader Webex API coverage (meetings, messaging, etc.)
- You prefer typed/validated request and response models
- You want the officially maintained Cisco library

---

## Quickstart

From the official docs:

```python
import wxcadm

access_token = "your_api_access_token"
webex = wxcadm.Webex(access_token)

# Single-org admin (most common)
org = webex.org

# Iterate people
for person in org.people:
    print(person.email)

# Access locations
for location in org.locations:
    print(location.name)
```

### Enabling Debug Logging

```python
wxcadm.console_logging("debug")
```

### Service Application Token Flow

```python
# Developer creates the service app
developer_webex = wxcadm.Webex(developer_token)
new_app = developer_webex.org.applications.create_service_application(
    name='My App',
    contact='help@example.com',
    logo='https://example.com/logo.png',
    scopes=['spark:people_read', 'spark-admin:people_write', ...]
)
app_id = new_app['id']
client_secret = new_app['clientSecret']

# Admin authorizes
admin_webex = wxcadm.Webex(admin_token)
app = admin_webex.org.applications.get_app_by_id(app_id)
app.authorize()

# Developer gets token for admin's org
app = developer_webex.org.applications.get_app_by_id(app_id)
token_info = app.get_token(client_secret, admin_org_id)
# token_info keys: access_token, expires_in, refresh_token,
#                  refresh_token_expires_in, token_type

# Refresh when needed
token_info = app.get_token_refresh(client_secret, refresh_token)
```

### Token Refresh (Integration)

```python
webex = wxcadm.Webex(
    access_token,
    client_id="...",
    client_secret="...",
    refresh_token="...",
)

# Later, when token is about to expire:
new_token_info = webex.get_new_token()
# The Webex instance is updated in-place with the new token
```
