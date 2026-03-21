# wxc_sdk Patterns & Recipes

Reference document for the `wxc_sdk` Python SDK -- the primary tool for automating Webex Calling administration via the Webex REST APIs.

**SDK Version (at time of writing):** `1.30.0`

## Sources

- **wxc_sdk v1.30.0** — [github.com/jeokrohn/wxc_sdk](https://github.com/jeokrohn/wxc_sdk)
- **Docs** — [wxc-sdk.readthedocs.io](http://wxc-sdk.readthedocs.io)
- **Webex API Reference** — [developer.webex.com](https://developer.webex.com/docs/api/getting-started)

## Required Scopes

Token type and scope requirements for common SDK operations. Admin tokens (`spark-admin:*`) cover org-wide management; user tokens (`spark:*`) cover personal settings and call control.

| Operation Category | Required Scope | Token Type | Notes |
|-------------------|----------------|------------|-------|
| List/read people | `spark-admin:people_read` | Admin / Service App | `calling_data=True` requires this scope |
| Create/update/delete people | `spark-admin:people_write` | Admin / Service App | Also needs `_read` for pre-flight checks |
| List/read locations | `spark-admin:locations_read` | Admin / Service App | |
| Manage locations | `spark-admin:locations_write` | Admin / Service App | |
| Read telephony config (queues, HG, AA, etc.) | `spark-admin:telephony_config_read` | Admin / Service App | Covers all `/telephony/config/*` endpoints |
| Write telephony config | `spark-admin:telephony_config_write` | Admin / Service App | Create/update/delete calling features |
| Read person call settings | `spark-admin:people_read` | Admin / Service App | Voicemail, forwarding, caller ID, etc. |
| Write person call settings | `spark-admin:people_write` | Admin / Service App | |
| Read workspace settings | `spark-admin:workspaces_read` | Admin / Service App | |
| Manage workspaces | `spark-admin:workspaces_write` | Admin / Service App | |
| Read devices | `spark-admin:devices_read` | Admin / Service App | |
| Manage devices | `spark-admin:devices_write` | Admin / Service App | |
| Read licenses | `spark-admin:licenses_read` | Admin / Service App | |
| Call control (dial, answer, hold, transfer) | `spark:calls_write` | **User** | Must be calling-licensed user's token; admin tokens get 400 |
| Read own call settings (`/people/me/*`) | `spark:people_read` | **User** | User must have Webex Calling license |
| CDR / call detail records | `spark-admin:cdr_read` | Admin / Service App | |
| Webhooks | `spark:webhooks_read`, `spark:webhooks_write` | Admin or User | |
| Admin audit events | `spark-admin:audit_events_read` | Admin / Service App | |
| Org/roles/authorizations | `spark-admin:organizations_read` | Admin / Service App | |

**Scope naming pattern:** `spark-admin:` prefix = org-wide admin scope; `spark:` prefix = user-level scope. Most SDK operations use admin scopes. Call control and `/people/me/*` endpoints are the main exceptions requiring user-level tokens.

## Table of Contents

1. [Installation](#1-installation)
2. [Raw HTTP Pattern](#15-raw-http-pattern-preferred-execution-method)
3. [WebexSimpleApi -- The Sync Entry Point](#2-webexsimpleapi----the-sync-entry-point)
4. [Authentication Patterns](#3-authentication-patterns)
5. [Sync vs Async](#4-sync-vs-async)
6. [Common Recipes](#5-common-recipes)
7. [Error Handling](#6-error-handling)
8. [REST Client Details](#7-rest-client-details)
9. [Data Types](#8-data-types)
10. [Environment Variable Patterns](#9-environment-variable-patterns)
11. [Logging](#10-logging)
12. [Key Gotchas](#11-key-gotchas)
13. [See Also](#see-also)

---

## 1. Installation

```bash
# Install
pip install wxc-sdk

# Upgrade
pip install wxc-sdk --upgrade
```

Common companion packages used in the examples:

```bash
pip install python-dotenv   # .env file loading
pip install pyyaml          # token caching to YML
```

Core dependencies pulled in automatically by wxc_sdk:
- `requests` (sync HTTP -- powers `RestSession`)
- `aiohttp` (async HTTP -- powers `AsRestSession`)
- `pydantic` (data models)
- `aenum` (dynamic enum extension)
- `python-dateutil` / `pytz` (date handling)

---

## 1.5. Raw HTTP Pattern (Preferred Execution Method)
<!-- Updated by playbook session 2026-03-18 -->

The primary way to execute Webex API calls in this project is **raw HTTP via `api.session.rest_*()`**. We use `wxc_sdk` for authentication and session management only -- all actual API calls go through the REST client methods with full URLs.

### Why Raw HTTP

- **Full control** over request/response -- no SDK model translation surprises
- **Matches the Webex API docs exactly** -- URLs, params, and body keys are 1:1 with developer.webex.com
- **No SDK version dependency** for API coverage -- new endpoints work immediately
- **Responses are plain dicts** -- easy to inspect, log, and forward

### Setup

```python
from wxc_sdk import WebexSimpleApi

api = WebexSimpleApi()  # auth via WEBEX_ACCESS_TOKEN env var
BASE = "https://webexapis.com/v1"
```

### REST Methods

| Method | Signature | Returns |
|--------|-----------|---------|
| `rest_get` | `api.session.rest_get(url, params=dict)` | Parsed JSON dict |
| `rest_post` | `api.session.rest_post(url, json=dict)` | Parsed JSON dict |
| `rest_put` | `api.session.rest_put(url, json=dict)` | Parsed JSON dict (or None) |
| `rest_delete` | `api.session.rest_delete(url)` | None |

All methods require **full URLs** (`https://webexapis.com/v1/...`), not relative paths.

### CRUD Example

```python
from wxc_sdk import WebexSimpleApi
from wxc_sdk.rest import RestError

api = WebexSimpleApi()
BASE = "https://webexapis.com/v1"

# ── LIST (GET with params) ────────────────────────────────────────
result = api.session.rest_get(f"{BASE}/people", params={"max": 1000})
people = result.get("items", [])

# ── CREATE (POST with JSON body) ──────────────────────────────────
body = {
    "emails": ["jsmith@example.com"],
    "displayName": "John Smith",
    "firstName": "John",
    "lastName": "Smith",
}
result = api.session.rest_post(f"{BASE}/people", json=body)
person_id = result["id"]

# ── READ (GET by ID) ──────────────────────────────────────────────
person = api.session.rest_get(f"{BASE}/people/{person_id}")

# ── UPDATE (PUT with full body) ───────────────────────────────────
person["department"] = "Engineering"
api.session.rest_put(f"{BASE}/people/{person_id}", json=person)

# ── DELETE ─────────────────────────────────────────────────────────
api.session.rest_delete(f"{BASE}/people/{person_id}")
```

### Pagination

There is **no automatic pagination** with raw HTTP. The SDK's `follow_pagination()` only works with the typed API methods (e.g., `api.people.list()`). For raw HTTP, request the maximum page size and handle paging manually if needed:

```python
# Request max page size (API maximum is typically 1000)
result = api.session.rest_get(f"{BASE}/people", params={"max": 1000})
items = result.get("items", [])

# For endpoints that may return more than 1000 items,
# check for a next link (rare in practice for most Webex APIs):
# The SDK does NOT auto-follow next links in raw HTTP mode.
```

### Error Handling

All `rest_*()` methods raise `RestError` on HTTP errors. The exception carries the full error detail from the Webex API:

```python
from wxc_sdk.rest import RestError

try:
    api.session.rest_get(f"{BASE}/people/invalid-id")
except RestError as e:
    print(f"HTTP {e.response.status_code}")  # e.g., 404
    print(f"Error code: {e.code}")            # Webex error code
    print(f"Description: {e.description}")    # Human-readable message
    print(f"Tracking ID: {e.detail.tracking_id}")  # For Cisco TAC
```

### Response Parsing

Responses are already-parsed JSON dicts. The response key varies by endpoint:

| Endpoint | List response key |
|----------|------------------|
| `/v1/people` | `items` |
| `/v1/locations` | `items` |
| `/v1/licenses` | `items` |
| `/v1/workspaces` | `items` |
| `/v1/telephony/config/numbers` | `phoneNumbers` |
| `/v1/telephony/config/jobs/numbers/manageNumbers` | `items` |

Single-resource GETs return the resource dict directly (no wrapper key).

### When to Use Typed SDK Methods Instead

The typed SDK API (e.g., `api.people.list()`) is still useful for:
- **Auto-pagination** -- `list()` returns generators that follow all pages automatically
- **Pydantic models** -- typed access with IDE completion and validation
- **Async bulk operations** -- `AsWebexSimpleApi` with `asyncio.gather` for high-concurrency reads

The existing SDK patterns in this doc remain valid. Raw HTTP is the **preferred approach for write operations and targeted reads** where you want direct control over the request.

---

## 2. WebexSimpleApi -- The Sync Entry Point

`WebexSimpleApi` is the main class. It creates a `RestSession` and attaches every sub-API as a property.

### Constructor

```python
from wxc_sdk import WebexSimpleApi

api = WebexSimpleApi(
    tokens=None,                  # str | Tokens | None
    concurrent_requests=10,       # max parallel threads (Semaphore)
    retry_429=True,               # auto-retry on rate limit
    # session=RestSession(...)    # pass your own session (advanced)
)
```

**Token resolution order:**
1. If `tokens` is a `str`, it is wrapped in `Tokens(access_token=tokens)`.
2. If `tokens` is a `Tokens` instance, it is used directly.
3. If `tokens` is `None`, the SDK reads `WEBEX_ACCESS_TOKEN` from the environment.
4. If the environment variable is also missing, a `ValueError` is raised.

### Context Manager

`WebexSimpleApi` supports `with` statements. The `__exit__` method calls `session.close()`:

```python
with WebexSimpleApi() as api:
    users = list(api.people.list())
# session is closed here
```

### Top-Level API Properties

Every property below is an API sub-object. The ones most relevant to Webex Calling are marked with **(WxC)**.

| Property | Class | Notes |
|----------|-------|-------|
| `api.people` | `PeopleApi` | **(WxC)** List/get users, `calling_data=True` |
| `api.locations` | `LocationsApi` | **(WxC)** List/manage locations |
| `api.telephony` | `TelephonyApi` | **(WxC)** Main Calling API -- call queues, hunt groups, auto attendants, schedules, phone numbers, devices, permissions, virtual lines, etc. |
| `api.person_settings` | `PersonSettingsApi` | **(WxC)** Per-user calling settings -- voicemail, forwarding, devices, caller ID, etc. |
| `api.workspace_settings` | `WorkspaceSettingsApi` | **(WxC)** Per-workspace calling settings |
| `api.workspaces` | `WorkspacesApi` | **(WxC)** Workspace CRUD |
| `api.devices` | `DevicesApi` | **(WxC)** Device management |
| `api.licenses` | `LicensesApi` | **(WxC)** License inventory |
| `api.jobs` | `JobsApi` | **(WxC)** Bulk provisioning jobs |
| `api.workspace_locations` | `WorkspaceLocationApi` | Workspace locations |
| `api.workspace_personalization` | `WorkspacePersonalizationApi` | Workspace personalization |
| `api.admin_audit` | `AdminAuditEventsApi` | Audit trail |
| `api.authorizations` | `AuthorizationsApi` | User authorizations/tokens |
| `api.cdr` | `DetailedCDRApi` | Call detail records |
| `api.converged_recordings` | `ConvergedRecordingsApi` | Recordings |
| `api.device_configurations` | `DeviceConfigurationsApi` | Device configs |
| `api.events` | `EventsApi` | Webhooks events |
| `api.groups` | `GroupsApi` | Groups |
| `api.guests` | `GuestManagementApi` | Guest management |
| `api.me` | `MeSettingsApi` | Calling settings for authenticated user |
| `api.meetings` | `MeetingsApi` | Meetings |
| `api.membership` | `MembershipApi` | Space memberships |
| `api.messages` | `MessagesApi` | Messages |
| `api.org_contacts` | `OrganizationContactsApi` | Org contacts |
| `api.organizations` | `OrganizationApi` | Org settings |
| `api.reports` | `ReportsApi` | Reports |
| `api.roles` | `RolesApi` | Roles |
| `api.rooms` | `RoomsApi` | Spaces/rooms |
| `api.room_tabs` | `RoomTabsApi` | Room tabs |
| `api.scim` | `ScimV2Api` | SCIM v2 |
| `api.status` | `StatusAPI` | Webex status |
| `api.teams` | `TeamsApi` | Teams |
| `api.team_memberships` | `TeamMembershipsApi` | Team memberships |
| `api.webhook` | `WebhookApi` | Webhooks |
| `api.xapi` | `XApi` | xAPI |

### Telephony Sub-APIs (via `api.telephony.*`)

The `TelephonyApi` object is the gateway to all calling features. Key sub-properties:

- `api.telephony.access_codes` -- Location access/authentication codes
- `api.telephony.announcements_repo` -- Announcements repository
- `api.telephony.auto_attendant` -- Auto attendant CRUD
- `api.telephony.call_controls_members` -- Call controls members
- `api.telephony.call_intercept` -- Location call intercept settings
- `api.telephony.call_recording` -- Call recording settings
- `api.telephony.call_routing` -- Call routing
- `api.telephony.caller_reputation_provider` -- Caller reputation provider
- `api.telephony.calls` -- Calls API
- `api.telephony.callpark` -- Call park CRUD
- `api.telephony.callpark_extension` -- Call park extensions
- `api.telephony.callqueue` -- Call queue CRUD, agents
- `api.telephony.conference` -- Conference controls
- `api.telephony.cx_essentials` -- Customer Assist (formerly CX Essentials)
- `api.telephony.dect_devices` -- DECT device management
- `api.telephony.devices` -- Telephony device details, members, MAC validation
- `api.telephony.emergency_address` -- Emergency address management
- `api.telephony.emergency_services` -- Org emergency services
- `api.telephony.guest_calling` -- Guest calling
- `api.telephony.hotdesk` -- Hot desk management
- `api.telephony.hotdesking_voiceportal` -- Hot desking sign-in via voice portal
- `api.telephony.huntgroup` -- Hunt group CRUD
- `api.telephony.jobs` -- Bulk provisioning jobs
- `api.telephony.location` -- Location-level telephony settings
- `api.telephony.locations` -- Alias for `location` (same object)
- `api.telephony.ms_teams` -- Org MS Teams settings
- `api.telephony.operating_modes` -- Operating modes
- `api.telephony.organisation_access_codes` -- Org-level access codes
- `api.telephony.organisation_voicemail` -- Org voicemail settings
- `api.telephony.paging` -- Paging groups
- `api.telephony.permissions_out` -- Outgoing call permissions
- `api.telephony.phone_numbers(...)` -- List phone numbers org-wide or per-location (method, not sub-API)
- `api.telephony.pickup` -- Call pickup CRUD
- `api.telephony.playlist` -- Playlists (music on hold)
- `api.telephony.pnc` -- Private network connect
- `api.telephony.prem_pstn` -- Premises PSTN
- `api.telephony.pstn` -- PSTN settings
- `api.telephony.schedules` -- Holiday/business hours schedules
- `api.telephony.supervisors` -- Supervisor management
- `api.telephony.virtual_extensions` -- Virtual extensions
- `api.telephony.virtual_lines` -- Virtual line management
- `api.telephony.voicemail_groups` -- Voicemail groups
- `api.telephony.voicemail_rules` -- Voicemail rules
- `api.telephony.voice_messaging` -- Voice messaging
- `api.telephony.voiceportal` -- Voice portal settings

<!-- Verified via wxc_sdk v1.30.0 source (wxc_sdk/telephony/__init__.py TelephonyApi class) 2026-03-19 -->

---

## 3. Authentication Patterns

### Pattern A: Environment Variable (Simplest)

Set `WEBEX_ACCESS_TOKEN` and construct with no arguments. Best for quick scripts and developer tokens.

```python
from dotenv import load_dotenv
from wxc_sdk import WebexSimpleApi

load_dotenv(override=True)  # reads .env file

api = WebexSimpleApi()
me = api.people.me()
print(f'Authenticated as {me.display_name}')
```

**.env file:**
```
WEBEX_ACCESS_TOKEN=NjY2Yz...
```

### Pattern B: Token String Directly

```python
api = WebexSimpleApi(tokens='NjY2Yz...')
```

### Pattern C: OAuth Integration (Interactive)

For production scripts that need token refresh. Uses `wxc_sdk.integration.Integration` to run a local OAuth flow and cache tokens to a YML file.

```python
import os
from wxc_sdk import WebexSimpleApi
from wxc_sdk.integration import Integration
from wxc_sdk.scopes import parse_scopes
from wxc_sdk.tokens import Tokens

def build_integration() -> Integration:
    client_id = os.getenv('TOKEN_INTEGRATION_CLIENT_ID')
    client_secret = os.getenv('TOKEN_INTEGRATION_CLIENT_SECRET')
    scopes = parse_scopes(os.getenv('TOKEN_INTEGRATION_CLIENT_SCOPES'))
    redirect_url = 'http://localhost:6001/redirect'
    return Integration(
        client_id=client_id,
        client_secret=client_secret,
        scopes=scopes,
        redirect_url=redirect_url,
    )

def get_tokens() -> Tokens:
    integration = build_integration()
    # reads from YML cache; if expired, opens browser for OAuth
    tokens = integration.get_cached_tokens_from_yml(yml_path='tokens.yml')
    return tokens

tokens = get_tokens()
api = WebexSimpleApi(tokens=tokens)
```

**Required .env:**
```
TOKEN_INTEGRATION_CLIENT_ID=C1234...
TOKEN_INTEGRATION_CLIENT_SECRET=abc123...
TOKEN_INTEGRATION_CLIENT_SCOPES="spark-admin:telephony_config_read spark-admin:people_read"
```

### Pattern D: Service App (Headless / Production)

Service apps use a refresh token + client credentials to obtain access tokens without user interaction. Best for automation and scheduled jobs.

```python
import os
from wxc_sdk import WebexSimpleApi
from wxc_sdk.integration import Integration
from wxc_sdk.tokens import Tokens
import yaml

SERVICE_APP_ENVS = (
    'SERVICE_APP_REFRESH_TOKEN',
    'SERVICE_APP_CLIENT_ID',
    'SERVICE_APP_CLIENT_SECRET',
)

def get_tokens() -> Tokens:
    refresh, client_id, client_secret = (
        os.getenv(env) for env in SERVICE_APP_ENVS
    )
    # Try reading cached tokens from YML
    yml_path = f'tokens_{client_id}.yml'
    if os.path.isfile(yml_path):
        with open(yml_path) as f:
            tokens = Tokens.model_validate(yaml.safe_load(f))
        # Refresh if less than 24 hours remaining
        if tokens.remaining >= 24 * 60 * 60:
            return tokens

    # Get fresh tokens using refresh token
    tokens = Tokens(refresh_token=refresh)
    integration = Integration(
        client_id=client_id,
        client_secret=client_secret,
        scopes=[],
        redirect_url=None,
    )
    integration.refresh(tokens=tokens)

    # Cache to file
    with open(yml_path, mode='w') as f:
        yaml.safe_dump(tokens.model_dump(exclude_none=True), f)
    return tokens

tokens = get_tokens()
with WebexSimpleApi(tokens=tokens) as api:
    users = list(api.people.list())
    print(f'{len(users)} users')
```

**Required .env:**
```
SERVICE_APP_CLIENT_ID=C5678...
SERVICE_APP_CLIENT_SECRET=xyz789...
SERVICE_APP_REFRESH_TOKEN=MmI3Zj...
```

### Tokens Class Reference

`wxc_sdk.tokens.Tokens` (Pydantic BaseModel):

| Field | Type | Notes |
|-------|------|-------|
| `access_token` | `Optional[str]` | The bearer token |
| `expires_in` | `Optional[int]` | Lifetime in seconds at creation time |
| `expires_at` | `Optional[datetime]` | Computed expiration datetime |
| `refresh_token` | `Optional[str]` | For refresh flow |
| `refresh_token_expires_in` | `Optional[int]` | Refresh token lifetime |
| `refresh_token_expires_at` | `Optional[datetime]` | Refresh token expiration |
| `token_type` | `Optional[Literal['Bearer']]` | Always "Bearer" |
| `scope` | `Optional[str]` | Space-delimited scopes |

Key property: `tokens.remaining` returns seconds until access_token expires.

---

## 4. Sync vs Async

The SDK provides parallel sync and async APIs with identical method signatures.

| | Sync | Async |
|---|---|---|
| **Class** | `WebexSimpleApi` | `AsWebexSimpleApi` |
| **Import** | `from wxc_sdk import WebexSimpleApi` | `from wxc_sdk.as_api import AsWebexSimpleApi` |
| **HTTP lib** | `requests` (`RestSession`) | `aiohttp` (`AsRestSession`) |
| **Context mgr** | `with api:` | `async with api:` |
| **Concurrency** | `ThreadPoolExecutor` + Semaphore | `asyncio.gather` + Semaphore |
| **Pagination** | Generator (`yield`) | AsyncGenerator (`async for`) |

### When to Use Each

**Use sync (`WebexSimpleApi`)** when:
- Writing simple scripts (list users, read a setting)
- Your script does a handful of sequential API calls
- You want the simplest possible code

**Use async (`AsWebexSimpleApi`)** when:
- You need to make many API calls (bulk operations)
- You want parallel execution without threads
- Performance matters (async is significantly faster for bulk work)

### Async Basic Pattern

```python
import asyncio
from wxc_sdk.as_api import AsWebexSimpleApi

async def main():
    async with AsWebexSimpleApi(concurrent_requests=40) as api:
        # list calls are awaitable
        users = [user for user in await api.people.list(calling_data=True)
                 if user.location_id]

        # parallel detail fetches with asyncio.gather
        details = await asyncio.gather(
            *[api.people.details(person_id=u.person_id, calling_data=True)
              for u in users]
        )
        print(f'Got details for {len(details)} users')

asyncio.run(main())
```

### Async Generator Pattern

Some async list methods return `AsyncGenerator` via `list_gen()`:

```python
async with AsWebexSimpleApi(concurrent_requests=40) as api:
    calling_license_ids = set(
        lic.license_id for lic in await api.licenses.list()
        if lic.webex_calling
    )
    # list_gen() returns an async generator
    calling_users = [
        user async for user in api.people.list_gen()
        if any(lid in calling_license_ids for lid in user.licenses)
    ]
```

### Side-by-Side Comparison: Sync vs Async

**Sync (ThreadPoolExecutor):**
```python
from concurrent.futures import ThreadPoolExecutor
from wxc_sdk import WebexSimpleApi

with WebexSimpleApi(concurrent_requests=5) as api:
    locations = [loc for loc in api.locations.list()
                 if loc.address.country == 'US']
    with ThreadPoolExecutor() as pool:
        list(pool.map(
            lambda loc: do_something(api=api, location=loc),
            locations
        ))
```

**Async (asyncio.gather):**
```python
import asyncio
from wxc_sdk.as_api import AsWebexSimpleApi

async def main():
    async with AsWebexSimpleApi(concurrent_requests=5) as api:
        locations = [loc for loc in await api.locations.list()
                     if loc.address.country == 'US']
        await asyncio.gather(
            *[do_something(api=api, location=loc) for loc in locations]
        )

asyncio.run(main())
```

---

## 5. Common Recipes

### 5.1 List All Calling-Enabled Users

The simplest and most common operation. A user is calling-enabled if `location_id` is set.

```python
from dotenv import load_dotenv
from wxc_sdk import WebexSimpleApi

load_dotenv(override=True)
api = WebexSimpleApi()

calling_users = [user for user in api.people.list(calling_data=True)
                 if user.location_id]
print(f'{len(calling_users)} calling users')
for user in calling_users:
    print(f'  {user.display_name} ({user.emails[0]})')
```

**Key detail:** `calling_data=True` is required to populate `location_id` and other calling-specific fields. Without it, `location_id` will always be `None`.

### 5.2 Filter Users by Location

```python
# Get all locations, find target
locations = list(api.locations.list())
target = next(loc for loc in locations if loc.name == 'San Jose')

# Get calling users in that location
calling_users = [user for user in api.people.list(calling_data=True)
                 if user.location_id == target.location_id]
```

### 5.3 Identify Calling Users via License (Async Approach)

An alternative to `calling_data=True` that avoids the slower per-user calling data fetch:

```python
async with AsWebexSimpleApi(concurrent_requests=40) as api:
    calling_license_ids = set(
        lic.license_id for lic in await api.licenses.list()
        if lic.webex_calling
    )
    calling_users = [
        user async for user in api.people.list_gen()
        if any(lid in calling_license_ids for lid in user.licenses)
    ]
```

### 5.4 Bulk Read Person Settings (Async)

Reading voicemail, forwarding, or device settings for many users in parallel:

```python
import asyncio
from wxc_sdk.as_api import AsWebexSimpleApi

async def main():
    async with AsWebexSimpleApi(concurrent_requests=40) as api:
        calling_users = [u for u in await api.people.list(calling_data=True)
                         if u.location_id]

        # Get voicemail settings for all users in parallel
        vm_settings = await asyncio.gather(
            *[api.person_settings.voicemail.read(person_id=u.person_id)
              for u in calling_users]
        )
        for user, vm in zip(calling_users, vm_settings):
            print(f'{user.display_name}: rings={vm.send_unanswered_calls.number_of_rings}')

asyncio.run(main())
```

### 5.5 Bulk Update Person Settings (Sync with ThreadPoolExecutor)

```python
from concurrent.futures import ThreadPoolExecutor
from wxc_sdk import WebexSimpleApi

api = WebexSimpleApi()
calling_users = [u for u in api.people.list(calling_data=True) if u.location_id]

def set_rings(user):
    vm = api.person_settings.voicemail
    settings = vm.read(person_id=user.person_id)
    settings.send_unanswered_calls.number_of_rings = 6
    vm.configure(user.person_id, settings=settings)

with ThreadPoolExecutor() as pool:
    list(pool.map(set_rings, calling_users))
```

### 5.6 Reset Call Forwarding for All Users (Async)

```python
import asyncio
from wxc_sdk.all_types import PersonForwardingSetting
from wxc_sdk.as_api import AsWebexSimpleApi

async def main():
    async with AsWebexSimpleApi() as api:
        calling_users = [u for u in await api.people.list(calling_data=True)
                         if u.location_id]
        forwarding = PersonForwardingSetting.default()
        await asyncio.gather(
            *[api.person_settings.forwarding.configure(
                entity_id=u.person_id, forwarding=forwarding)
              for u in calling_users]
        )
        print(f'Reset forwarding for {len(calling_users)} users')

asyncio.run(main())
```

### 5.7 Call Queue Management

**List all queues:**
```python
queues = list(api.telephony.callqueue.list())
```

**Get queue details (includes agents):**
```python
details = api.telephony.callqueue.details(
    location_id=queue.location_id,
    queue_id=queue.id
)
for agent in details.agents:
    print(f'  {agent.first_name} {agent.last_name}: '
          f'{"joined" if agent.join_enabled else "not joined"}')
```

**Update queue agents:**
```python
from wxc_sdk.telephony.callqueue import CallQueue
from wxc_sdk.telephony.hg_and_cq import Agent

# Add an agent
details.agents.append(Agent(agent_id=user.person_id))
update = CallQueue(agents=details.agents)
api.telephony.callqueue.update(
    location_id=queue.location_id,
    queue_id=queue.id,
    update=update,
)
```

**Important:** The `list()` response for queues does NOT include agents. You must call `details()` to get the full agent list.

### 5.8 Holiday Schedule Provisioning

```python
from wxc_sdk.all_types import Event, Schedule, ScheduleType

# Create a holiday schedule
schedule = Schedule(
    name='National Holidays',
    schedule_type=ScheduleType.holidays,
    events=[
        Event(
            name='Independence Day 2026',
            start_date=date(2026, 7, 4),
            end_date=date(2026, 7, 4),
            all_day_enabled=True,
        ),
    ],
)
schedule_id = api.telephony.schedules.create(
    obj_id=location.location_id,
    schedule=schedule,
)
```

### 5.9 List Phone Numbers

```python
# All phone numbers in the org
all_numbers = api.telephony.phone_numbers()

# Available (unassigned) numbers in a location
available = api.telephony.phone_numbers(
    available=True,
    location_id=location.location_id,
)

# Numbers owned by workspaces (places)
from wxc_sdk.common import OwnerType
place_numbers = api.telephony.phone_numbers(
    owner_type=OwnerType.place,
)
```

### 5.10 Hunt Group with Call Forwarding

```python
from wxc_sdk.telephony.huntgroup import HuntGroup

# Create a hunt group
settings = HuntGroup.create(
    name='Support HG',
    phone_number='+14085551234',
)
hg_id = api.telephony.huntgroup.create(
    location_id=location.location_id,
    settings=settings,
)

# Set call forwarding on the hunt group
forwarding = api.telephony.huntgroup.forwarding.settings(
    location_id=location.location_id,
    feature_id=hg_id,
)
forwarding.always.enabled = True
forwarding.always.destination = '+14085559999'
api.telephony.huntgroup.forwarding.update(
    location_id=location.location_id,
    feature_id=hg_id,
    forwarding=forwarding,
)
```

### 5.11 Users Without Devices

```python
import asyncio
from wxc_sdk.as_api import AsWebexSimpleApi

async def main():
    async with AsWebexSimpleApi(tokens=tokens) as api:
        calling_users = [u for u in await api.people.list(calling_data=True)
                         if u.location_id]
        device_infos = await asyncio.gather(
            *[api.person_settings.devices(person_id=u.person_id)
              for u in calling_users]
        )
        users_wo_devices = [
            u for u, di in zip(calling_users, device_infos)
            if not di.devices
        ]
        print(f'{len(users_wo_devices)} users without devices')

asyncio.run(main())
```

### 5.12 Workspace Provisioning with 3rd-Party Device

```python
from wxc_sdk.workspaces import (
    CallingType, Workspace, WorkspaceCalling,
    WorkspaceSupportedDevices, WorkspaceWebexCalling,
)
from wxc_sdk.common import DevicePlatform

# Create workspace
settings = Workspace(
    location_id=location.location_id,
    display_name='Lobby Phone',
    capacity=1,
    supported_devices=WorkspaceSupportedDevices.phones,
    device_platform=DevicePlatform.cisco,
    calling=WorkspaceCalling(
        type=CallingType.webex,
        webex_calling=WorkspaceWebexCalling(
            licenses=[calling_license_id],
            extension='2001',
            location_id=location.location_id,
        ),
    ),
)
workspace = await api.workspaces.create(settings=settings)

# Attach a device by MAC address
device = await api.devices.create_by_mac_address(
    mac='DEADDEAD0001',
    workspace_id=workspace.workspace_id,
    model='Generic IPPhone Customer Managed',
    password='generated_password',
)
```

---

## 6. Error Handling

### RestError (Sync)

The sync API raises `wxc_sdk.rest.RestError` (subclass of `requests.HTTPError`) on API errors:

```python
from wxc_sdk.rest import RestError

try:
    api.telephony.callqueue.details(
        location_id='bad-id',
        queue_id='bad-id',
    )
except RestError as e:
    print(f'HTTP {e.response.status_code}')
    print(f'Error code: {e.code}')
    print(f'Description: {e.description}')
    print(f'Tracking ID: {e.detail.tracking_id}')
```

`RestError.detail` is an `ErrorDetail` object with:
- `message` -- error message
- `errors` -- list of `SingleError` (each has `description` and `error_code`)
- `tracking_id` -- Webex tracking ID for support escalation

### AsRestError (Async)

The async API raises `wxc_sdk.as_rest.AsRestError` (subclass of `aiohttp.ClientResponseError`):

```python
from wxc_sdk.as_rest import AsRestError

try:
    await api.telephony.callqueue.details(
        location_id='bad-id',
        queue_id='bad-id',
    )
except AsRestError as e:
    print(f'HTTP {e.status}')
    print(f'Detail: {e.detail}')
```

### Handling Errors in Bulk Operations

Use `return_exceptions=True` with `asyncio.gather` to collect errors without stopping:

```python
results = await asyncio.gather(
    *[do_something(item) for item in items],
    return_exceptions=True,
)
for item, result in zip(items, results):
    if isinstance(result, Exception):
        print(f'Failed on {item}: {result}')
```

---

## 7. REST Client Details

### Base URL

All API requests go to `https://webexapis.com/v1`.

### Request Headers (Auto-Set)

Every request from `RestSession` / `AsRestSession` includes:

```
Authorization: Bearer {access_token}
Content-Type: application/json;charset=utf-8
TrackingID: SIMPLE_{uuid4}
```

### Rate Limiting & 429 Retry

When `retry_429=True` (the default), the SDK automatically:

1. Catches HTTP 429 responses
2. Reads the `Retry-After` header (defaults to 5 seconds if missing)
3. Caps the wait at `RETRY_429_MAX_WAIT` (60 seconds, defined in `wxc_sdk.base`)
4. Sleeps for the specified duration, then retries

The retry loop runs inside a Semaphore-protected block, so the concurrency limit is respected.

**Sync:** Uses `time.sleep(retry_after)`
**Async:** Uses `await asyncio.sleep(retry_after)`

### Concurrency Control

Both sync and async sessions use a Semaphore to limit concurrent requests:

```python
# Sync: threading.Semaphore
# Async: asyncio.Semaphore
self._sem = Semaphore(concurrent_requests)
```

Every request acquires the semaphore before execution. This prevents overwhelming the Webex API. The `concurrent_requests` parameter controls the limit (default: 10).

For bulk async operations, you can raise this significantly:

```python
async with AsWebexSimpleApi(concurrent_requests=40) as api:
    ...

# Some examples go as high as 100:
async with AsWebexSimpleApi(tokens=tokens, concurrent_requests=100) as api:
    ...
```

### Pagination (Automatic)

The SDK handles RFC 5988 pagination transparently via `follow_pagination()`. List methods return generators (sync) or async generators that automatically fetch subsequent pages by following the `next` link header.

You never need to handle pagination manually. Just iterate:

```python
# This fetches ALL pages automatically
all_users = list(api.people.list(calling_data=True))
```

Internally, `follow_pagination()`:
1. Makes the initial GET request
2. Parses `response.links['next']['url']` for the next page
3. Yields each item from the `items` key (or the first list-valued key in the response)
4. Repeats until no `next` link is present

### Proxy and SSL Support

```python
# Sync
api = WebexSimpleApi(
    tokens=tokens,
    proxy_url='https://proxy.corp.com:8080',
    verify='/path/to/ca-bundle.crt',  # or False to disable
)

# Async
api = AsWebexSimpleApi(
    tokens=tokens,
    proxy_url='https://proxy.corp.com:8080',
    ssl=ssl_context,  # ssl.SSLContext or bool
)
```

### Response Callbacks

You can register callbacks to inspect every HTTP response (useful for logging, HAR capture, metrics):

```python
def my_callback(response, diff_ns):
    print(f'{response.request.method} {response.request.url} '
          f'took {diff_ns / 1e6:.1f}ms')

callback_id = api.session.register_response_callback(my_callback)
# ... do work ...
api.session.unregister_response_callback(callback_id)
```

The SDK automatically registers a debug-level logging callback that dumps full request/response details when `logging.DEBUG` is enabled.

### HAR Writer

Several examples use `wxc_sdk.har_writer.HarWriter` for saving HTTP traces in HAR format:

```python
from wxc_sdk.har_writer import HarWriter

async with AsWebexSimpleApi(tokens=tokens) as api:
    with HarWriter(api=api, path='trace.har'):
        # all requests during this block are captured
        await api.people.list()
```

<!-- Verified via wxc_sdk v1.30.0 source (wxc_sdk/har_writer/__init__.py). Constructor: HarWriter(path=None, api=None, with_authorization=False, incremental=False). 2026-03-19 -->

---

## 8. Data Types

### Import Patterns

The SDK provides a convenience module `wxc_sdk.all_types` that re-exports all model types:

```python
# Import everything (convenient for interactive/scripts)
from wxc_sdk.all_types import *

# Import specific types (preferred for production code)
from wxc_sdk.all_types import PersonForwardingSetting, Schedule, ScheduleType, Event
```

For types not in `all_types`, import from the specific module:

```python
from wxc_sdk.people import Person
from wxc_sdk.telephony.callqueue import CallQueue
from wxc_sdk.telephony.hg_and_cq import Agent
from wxc_sdk.telephony.huntgroup import HuntGroup
from wxc_sdk.telephony.forwarding import CallForwarding
from wxc_sdk.telephony import NumberListPhoneNumber
from wxc_sdk.telephony.location import TelephonyLocation
from wxc_sdk.telephony.devices import DeviceMember, DeviceMembersResponse
from wxc_sdk.common import UserType, OwnerType, AlternateNumber, RingPattern, IdAndName
from wxc_sdk.locations import Location
from wxc_sdk.licenses import License
from wxc_sdk.workspaces import Workspace, CallingType, WorkspaceCalling
from wxc_sdk.person_settings import TelephonyDevice, DeviceList
from wxc_sdk.person_settings.permissions_out import Action, DigitPattern
from wxc_sdk.authorizations import Authorization, AuthorizationType
from wxc_sdk.tokens import Tokens
from wxc_sdk.integration import Integration
from wxc_sdk.scopes import parse_scopes
from wxc_sdk.webhook import WebhookEvent, WebhookEventType
```

### ApiModel Base Class

All data models inherit from `wxc_sdk.base.ApiModel` (which extends `pydantic.BaseModel`):

- **Alias generation:** Python `snake_case` attributes are automatically mapped to `camelCase` JSON keys via `to_camel`.
- **Populate by name:** Both `snake_case` and `camelCase` field names are accepted.
- **Extra fields allowed:** By default, unknown JSON fields are kept (configurable via `API_MODEL_ALLOW_EXTRA` env var).
- **Enum values stored:** Enum fields store the value, not the enum member.
- **Serialization defaults:** `model_dump_json()` excludes `None` values and uses aliases by default.

### SafeEnum

`wxc_sdk.base.SafeEnum` extends `aenum.Enum` to automatically handle unknown enum values from the API. If the API returns a value not defined in the enum, it is dynamically added (with a warning log) rather than raising an error. This prevents breakage when Webex adds new enum values.

### Utility Functions

```python
from wxc_sdk.base import webex_id_to_uuid, dt_iso_str, plus1

# Convert a Webex base64-encoded ID to a UUID
uuid = webex_id_to_uuid('Y2lzY29zcGFyazovL3VzL...')

# Format datetime for Webex API (UTC, milliseconds)
from datetime import datetime
iso = dt_iso_str(datetime.now())  # '2026-03-16T12:00:00.000Z'

# Convert 10-digit number to +E.164
phone = plus1('4085551234')  # '+14085551234'
```

---

## 9. Environment Variable Patterns

### Recommended .env Structure

Most examples follow this pattern: a `.env` file named after the script.

```
# For simple scripts: .env
WEBEX_ACCESS_TOKEN=NjY2Yz...

# For OAuth integration: get_tokens.env
TOKEN_INTEGRATION_CLIENT_ID=C1234...
TOKEN_INTEGRATION_CLIENT_SECRET=abc123...
TOKEN_INTEGRATION_CLIENT_SCOPES="spark-admin:telephony_config_read"

# For service apps: service_app.env
SERVICE_APP_CLIENT_ID=C5678...
SERVICE_APP_CLIENT_SECRET=xyz789...
SERVICE_APP_REFRESH_TOKEN=MmI3Zj...
```

### Token Caching Pattern

All OAuth/service-app examples cache tokens to a YML file and check `tokens.remaining` before use:

```python
import yaml
from wxc_sdk.tokens import Tokens

def read_tokens(path: str) -> Tokens:
    with open(path) as f:
        return Tokens.model_validate(yaml.safe_load(f))

def write_tokens(path: str, tokens: Tokens):
    with open(path, mode='w') as f:
        yaml.safe_dump(tokens.model_dump(exclude_none=True), f)

# Refresh if less than 24 hours remaining
if tokens.remaining < 24 * 60 * 60:
    tokens = refresh_tokens()
```

---

## 10. Logging

The SDK uses Python's standard `logging` module. Key loggers:

| Logger | Purpose |
|--------|---------|
| `wxc_sdk.rest` | Sync REST request/response details |
| `wxc_sdk.as_rest` | Async REST request/response details |
| `wxc_sdk` | General SDK messages |

### Enable Full Request Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
# Optional: reduce noise from urllib3
logging.getLogger('urllib3').setLevel(logging.INFO)
```

### Log REST to File Only

```python
import logging

# Console: INFO only
logging.basicConfig(level=logging.INFO)

# REST details to file at DEBUG
rest_logger = logging.getLogger('wxc_sdk.as_rest')
rest_logger.setLevel(logging.DEBUG)
handler = logging.FileHandler('rest.log', mode='w')
handler.setLevel(logging.DEBUG)
rest_logger.addHandler(handler)
```

The SDK's response dump (enabled at DEBUG level) includes:
- Request method, URL, status code, timing
- Request headers (Authorization masked as `Bearer ***`)
- Request body (form data secrets masked)
- Response headers and body
- Access/refresh tokens in response bodies are masked as `***`

---

## 11. Key Gotchas

1. **`calling_data=True` is required** -- `api.people.list()` without `calling_data=True` will not populate `location_id`, phone numbers, or other calling-specific fields.

2. **`list()` returns minimal data** -- Queue, hunt group, and auto attendant list responses omit details like agents and alternate numbers. Always call `details()` to get the full object.

3. **`concurrent_requests` default is 10** -- This is conservative. For bulk async operations, increase to 40-100.

4. **Async list methods may differ** -- Some APIs have both `.list()` (returns a full list) and `.list_gen()` (returns an async generator). Check which is available for your use case.

5. **`MAX_USERS_WITH_CALLING_DATA = 10`** -- The SDK internally limits concurrent requests for users with calling data to prevent API issues. This is hardcoded in `as_api.py`.

6. **Thread safety (sync)** -- The sync `RestSession` uses a `threading.Semaphore` so it is safe to share across threads. Use `ThreadPoolExecutor` for parallel work with the sync API.

7. **Service app tokens expire** -- Always check `tokens.remaining` and refresh proactively. The examples use a 24-hour threshold.

8. **Webex IDs are base64-encoded** -- Use `webex_id_to_uuid()` if you need the raw UUID (e.g., for matching against other systems).

9. **Agent model imports differ per feature** -- Hunt Groups and Call Queues use `from wxc_sdk.telephony.hg_and_cq import Agent`. Call Park and Call Pickup use `from wxc_sdk.common import PersonPlaceAgent`. Paging uses `from wxc_sdk.telephony.paging import PagingAgent`. Do NOT try importing Agent from the individual feature modules. <!-- Verified via CLI implementation 2026-03-17 -->

10. **Named delete methods vs generic `.delete()`** -- Call Park, Call Pickup, Paging, and several other APIs inherit a generic `.delete()` that accepts anything silently. Always use the named method: `delete_callpark()`, `delete_pickup()`, `delete_paging()`, `delete_huntgroup()`, `delete_queue()`, `delete_auto_attendant()`, `delete_schedule()`. <!-- Verified via CLI implementation 2026-03-17 -->

11. **`ScheduleApi` import path** -- Lives at `wxc_sdk.common.schedules`, NOT `wxc_sdk.telephony.schedules` (which doesn't exist). `from wxc_sdk.common.schedules import ScheduleApi, Schedule, Event, ScheduleType`. <!-- Verified via CLI implementation 2026-03-17 -->

12. **`PagingApi.update()` unusual parameter order** -- Signature is `(location_id, update: Paging, paging_id)` — the model object comes BEFORE the ID. Always use keyword arguments to avoid silent misassignment. <!-- Verified via CLI implementation 2026-03-17 -->

---

## See Also

- **`authentication.md`** — Detailed OAuth flows, scope reference, and common auth error handling.
- **`provisioning.md`** — End-to-end user provisioning workflows, license assignment (People API and PATCH methods), and location management.
