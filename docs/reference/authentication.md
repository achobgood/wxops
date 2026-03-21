# Authentication Reference — Webex Calling APIs

This document covers every authentication method available for the Webex Calling APIs, including token types, OAuth flows, scope requirements, and the `wxc_sdk` Python SDK patterns for each.

## Sources

- wxc_sdk v1.30.0
- OpenAPI specs: webex-cloud-calling.json, webex-admin.json
- developer.webex.com Authentication APIs

---

## Table of Contents

1. [Authentication Methods Overview](#authentication-methods-overview)
2. [Personal Access Tokens](#personal-access-tokens)
3. [OAuth Integrations](#oauth-integrations)
4. [Service Apps](#service-apps)
5. [Bot Tokens](#bot-tokens)
6. [Guest Issuer Tokens](#guest-issuer-tokens)
7. [Calling-Related Scopes](#calling-related-scopes)
8. [wxc_sdk Auth Setup](#wxc_sdk-auth-setup)
9. [Raw HTTP via api.session](#raw-http-via-apisession)
10. [Token Refresh Flow](#token-refresh-flow)
11. [Common Auth Errors](#common-auth-errors)

---

## Authentication Methods Overview

| Method | Lifetime | Refresh? | Use Case | Calling API Access |
|--------|----------|----------|----------|-------------------|
| Personal Access Token | 12 hours | No | Dev/testing only | Full (your own scopes) |
| OAuth Integration | 14-day access / 90-day refresh | Yes | Production apps, user-delegated | Full (requested scopes) |
| Service App | Access token via refresh | Yes | Machine-to-machine, no user present | Full (admin-authorized scopes) |
| Bot Token | Does not expire | No | Automation, messaging-focused | Limited to bot scopes |
| Guest Issuer | Short-lived | No | Anonymous guest users | Not applicable to Calling |

All methods authenticate against the same base URL:

```
https://webexapis.com/v1
```

Every API request requires an `Authorization` header:

```
Authorization: Bearer <ACCESS_TOKEN>
```

---

## Personal Access Tokens

**What they are:** A quick-start token tied to your own Webex identity. Available from [developer.webex.com](https://developer.webex.com) by clicking your avatar and copying the token.

**Key facts:**
- Expires after **12 hours** from the time it is displayed
- Cannot be refreshed — you must generate a new one manually
- Carries all scopes your account has access to (including admin scopes if you are an admin)
- Intended strictly for development and testing — never embed in production code

**wxc_sdk usage:**

```python
from wxc_sdk import WebexSimpleApi

# Pass token directly as a string
api = WebexSimpleApi(tokens='YOUR_PERSONAL_ACCESS_TOKEN')

# Or set the environment variable and pass nothing
# export WEBEX_ACCESS_TOKEN=YOUR_PERSONAL_ACCESS_TOKEN
api = WebexSimpleApi()
```

---

## OAuth Integrations

OAuth integrations use the **Authorization Code Grant** flow (OAuth 2.0). This is the standard method for production applications that act on behalf of a user.

### Creating an Integration

1. Log into [developer.webex.com](https://developer.webex.com)
2. Click your avatar > **My Webex Apps** > **Create a New App** > **Create an Integration**
3. Provide app name, description, logo, redirect URI, and select scopes
4. Save the **Client ID** and **Client Secret** (secret shown only once)

### OAuth Flow (4 Steps)

**Step 1 — Authorization Request:**
Redirect the user to:
```
https://webexapis.com/v1/authorize?
  client_id=YOUR_CLIENT_ID&
  response_type=code&
  redirect_uri=http://localhost:6001/redirect&
  scope=spark:calls_read spark:calls_write spark:people_read spark-admin:telephony_config_read&
  state=RANDOM_STATE_STRING
```

**Step 2 — User Authenticates:**
User logs into Webex and approves the requested scopes.

**Step 3 — Receive Authorization Code:**
Webex redirects to your `redirect_uri` with a `code` parameter:
```
http://localhost:6001/redirect?code=AUTH_CODE&state=RANDOM_STATE_STRING
```

**Step 4 — Exchange Code for Tokens:**
POST to `https://webexapis.com/v1/access_token`:
```
grant_type=authorization_code
client_id=YOUR_CLIENT_ID
client_secret=YOUR_CLIENT_SECRET
code=AUTH_CODE
redirect_uri=http://localhost:6001/redirect
```

**Response:**
```json
{
  "access_token": "...",
  "expires_in": 1209600,
  "refresh_token": "...",
  "refresh_token_expires_in": 7776000,
  "token_type": "Bearer",
  "scope": "spark:calls_read spark:calls_write ..."
}
```

### Token Lifetimes

| Token | Lifetime | Notes |
|-------|----------|-------|
| Access token | **14 days** (1,209,600 seconds) | Must refresh before expiry |
| Refresh token | **90 days** (7,776,000 seconds) | Refreshing the access token also renews the refresh token |

### PKCE Support

Webex supports **Proof Key for Code Exchange (PKCE)** for enhanced security in the Authorization Code flow.

### OpenID Connect Discovery

Endpoint locations and server capabilities are available at:
```
https://idbroker.webex.com/idb/.well-known/openid-configuration
```

This returns a standard OpenID Connect discovery document including `authorization_endpoint`, `token_endpoint`, `userinfo_endpoint`, `jwks_uri`, supported scopes (`openid`, `email`, `profile`, `phone`, `address`), and `code_challenge_methods_supported` (`plain`, `S256`). <!-- Corrected via live API 2026-03-19: the URL was listed as webexapis.com/v1/... but the actual working endpoint is idbroker.webex.com/idb/... -->

### Gotchas

- **wxc_sdk does not support PKCE natively.** The `Integration.auth_url()` method builds the authorization URL with only `client_id`, `response_type`, `redirect_uri`, `scope`, and `state` — no `code_challenge` or `code_challenge_method` parameters. The `tokens_from_code()` method does not send a `code_verifier`. To use PKCE with Webex, you would need to construct the authorization URL and token exchange manually. <!-- Verified via wxc_sdk source (integration/__init__.py) 2026-03-19 -->

---

## Service Apps

Service apps are designed for **machine-to-machine** scenarios where no interactive user login is possible (background jobs, server daemons, scheduled automation).

### How They Differ from Integrations

| Aspect | Integration | Service App |
|--------|-------------|-------------|
| User presence | Requires user to authorize | No user interaction after admin approval |
| Token source | OAuth code flow | Refresh token provided at creation |
| Admin approval | User grants scopes | Org admin authorizes the app |
| Use case | User-facing apps | Backend automation, scheduled jobs |

### Creating & Registering a Service App

Service app creation is a 3-step process spanning two portals: the Developer Portal (registration) and Control Hub (authorization).

#### Step 1: Register on developer.webex.com

1. Log into [developer.webex.com](https://developer.webex.com)
2. Click your avatar (top right) → **My Webex Apps**
3. Click **Create a New App**
4. Select **Create a Service App**
5. Fill in the registration form:
   - **App Name** — displayed to admins during authorization
   - **Description** — what the app does
   - **Logo** — appears in Control Hub when admins review the app
   - **Scopes** — select the permissions your app needs (see [Calling-Related Scopes](#calling-related-scopes) below)
6. Click **Create** (or **Add Service App**)
7. **Immediately copy and save the Client Secret** — it is shown only once and cannot be retrieved later

You now have a **Client ID** and **Client Secret**. The app is registered but not yet authorized for any org.

#### Step 2: Authorize in Control Hub

An org Full Admin must authorize the service app before it can access that org's data.

1. Log into [admin.webex.com](https://admin.webex.com)
2. Navigate to **Management → Apps → Service Apps** tab
3. Find your service app in the list
4. Click it and select **Authorize**
5. Review the requested scopes
6. Click **Save**

The authorization is recorded in Admin Audit events. Any admin can later enable/disable the app from this same page.

#### Step 3: Generate Tokens

1. Return to [developer.webex.com](https://developer.webex.com) → **My Webex Apps** → your service app
2. In the **Org Authorizations** section, select your organization
3. Enter your **Client Secret**
4. Click **Generate Tokens**
5. You receive:
   - **Access Token** (valid 14 days)
   - **Refresh Token** (valid 90 days)
6. **Immediately copy and save the Refresh Token** — it is shown only once

Your service app is now ready to make API calls. Use the refresh token to obtain new access tokens programmatically (see below).

#### Scope Restrictions for Service Apps

Not all scopes work with service apps:

| Restriction | Detail |
|-------------|--------|
| XSI scopes | Not supported |
| Analytics scopes | Not supported |
| Organization contacts | Cannot manage |
| CDR records | Cannot query |
| Meeting scopes | Limited to `adminOnBehalf` functions (require `hostEmail` parameter) |
| Compliance scopes (`spark-compliance:*`) | Require Full Admin with Compliance Officer role |
| Scope string length | Limited to ~880 characters total — only request what you need |

### Authentication Flow

Service apps receive a **refresh token**, **client ID**, and **client secret** upon creation. They obtain access tokens by calling the same token endpoint used for integration refresh:

```
POST https://webexapis.com/v1/access_token

grant_type=refresh_token
client_id=SERVICE_APP_CLIENT_ID
client_secret=SERVICE_APP_CLIENT_SECRET
refresh_token=SERVICE_APP_REFRESH_TOKEN
```

The response includes a new `access_token` (and potentially a renewed `refresh_token`).

### Token Lifecycle

| Token | Lifetime | Renewal |
|-------|----------|---------|
| Access token | 14 days | Refresh using refresh token |
| Refresh token | 90 days | Automatically renewed each time you generate a new access token |
| Client secret | Does not expire | Regenerate via developer portal if compromised |

**For long-lived automations**, Webex recommends a 3-tier pattern:

1. **Tier 1:** Use the service app's refresh token to get new access tokens (normal operation)
2. **Tier 2:** If the refresh token expires (90 days unused), use the Applications API with a separate OAuth integration to regenerate it
3. **Tier 3:** The OAuth integration's own refresh token, refreshed by your token manager

This requires two Webex apps: your working service app and a token-manager integration. See the [Service App Token Management blog post](https://developer.webex.com/blog/service-app-token-management-a-developer-s-guide-to-automation) for details.

### Environment Variables (Convention from wxc_sdk examples)

```bash
SERVICE_APP_REFRESH_TOKEN=<refresh_token>
SERVICE_APP_CLIENT_ID=<client_id>
SERVICE_APP_CLIENT_SECRET=<client_secret>
```

### wxc_sdk Service App Pattern

From `examples/service_app.py` in the SDK:

```python
from wxc_sdk import WebexSimpleApi
from wxc_sdk.integration import Integration
from wxc_sdk.tokens import Tokens

# Build an Integration object (used only for the refresh call)
integration = Integration(
    client_id=client_id,
    client_secret=client_secret,
    scopes=[],          # scopes not needed for refresh
    redirect_url=None   # no redirect needed for service apps
)

# Create a Tokens object with just the refresh token
tokens = Tokens(refresh_token=refresh_token)

# Refresh to get a valid access token
integration.refresh(tokens=tokens)

# Use the tokens
with WebexSimpleApi(tokens=tokens) as api:
    users = list(api.people.list())
    queues = list(api.telephony.callqueue.list())
```

### Token Caching

The SDK example caches tokens to a YML file keyed by `client_id` to avoid unnecessary refresh calls. It checks `tokens.remaining` and refreshes when remaining lifetime drops below 24 hours:

```python
if tokens.expires_in is not None and tokens.remaining < 24 * 60 * 60:
    tokens = get_access_token(client_id=client_id, client_secret=client_secret, refresh=refresh)
```

---

## Bot Tokens

Bots are special Webex identities with their own access token.

**Key facts:**
- Bot tokens **do not expire** — they remain valid until the bot is deleted or regenerated
- No refresh token is provided (none needed)
- Bots have their own identity (separate from any user)
- Bots can interact with messaging, spaces, and webhooks
- Bot tokens have **limited scope for Calling APIs** — bots cannot place or manage calls on behalf of users

**wxc_sdk usage:**

```python
from wxc_sdk import WebexSimpleApi

api = WebexSimpleApi(tokens='BOT_ACCESS_TOKEN')
```

Since bot tokens never expire, no refresh logic is needed.

### Gotchas

- **Bot calling scopes unverified.** The exact list of calling-related scopes available to bots (if any) has not been confirmed. The developer.webex.com docs list scopes with a `show_for_app_type` property for "integration" and "serviceApp" but do not enumerate bot-specific scopes. Calling scopes like `spark:calls_read` and `spark:calls_write` appear to be user-level scopes for integrations. Bots likely cannot use calling scopes since they don't act on behalf of a user, but this has not been confirmed with a live bot token. *(Unverified — requires live bot token testing. Checked 2026-03-19.)*

---

## Guest Issuer Tokens

Guest Issuer tokens create temporary, anonymous guest users for scenarios like customer-facing meetings or support sessions.

**Key facts:**
- Managed via Service Apps with `guest-issuer:read` and `guest-issuer:write` scopes
- Guest tokens are short-lived
- **Not applicable to Webex Calling APIs** — guests cannot access telephony features

### Gotchas

- **Guest token lifetime is variable, set by `expiresIn` in the response.** The OpenAPI spec example shows `expiresIn: 64799` (~18 hours), but the actual lifetime is returned per-token at creation time via the `expiresIn` field. The SDK `Guest` model exposes this as `expires_in` and computes `expires_at` from it. There is no single fixed lifetime — it depends on org/service-app configuration. <!-- Verified via OpenAPI spec (webex-admin.json Guest schema) and wxc_sdk source (guests/__init__.py) 2026-03-19 -->

---

## Calling-Related Scopes

### User-Level Scopes

These scopes operate in the context of the authenticated user. Any Webex Calling-licensed user can authorize these.

| Scope | Description |
|-------|-------------|
| `spark:calls_read` | List all active calls the user is part of; list call history from Webex Calling |
| `spark:calls_write` | Invoke call commands on the authenticated user (answer, hold, transfer, etc.) |
| `spark:xsi` | Access Webex Calling resources via XSI (calls and call settings) |
| `spark:webrtc_calling` | Access WebRTC services for Webex Calling |
| `spark:people_read` | Read people/user information (commonly needed alongside calling scopes) |
| `spark:kms` | Key Management Service — required for end-to-end encryption operations |

### Admin-Level Scopes

These scopes require the authenticated user to be a **full org administrator**. They provide organization-wide access.

| Scope | Description |
|-------|-------------|
| `spark-admin:telephony_config_read` | Read and list telephony configuration (locations, numbers, call routing, features) |
| `spark-admin:telephony_config_write` | Create, edit, and delete telephony configuration |
| `spark-admin:calls_read` | List all calls across the organization |
| `spark-admin:calls_write` | Invoke call commands on any user in the organization |
| `spark-admin:calling_cdr_read` | Access comprehensive Call Detail Records, including PII-protected phone numbers |
| `spark-admin:people_read` | Read people across the organization |
| `spark-admin:people_write` | Create, update, delete people in the organization |

### Scope Categories by API Function

**Administrator / Provisioning APIs** (require `spark-admin:` scopes):
- Telephony configuration (locations, numbers, call routing, auto attendants, call queues, hunt groups)
- CDR / reporting
- User/workspace provisioning

**End-User / Call Control APIs** (require `spark:` scopes):
- Call commands (dial, answer, hold, resume, transfer, park)
- Call history
- Voicemail
- Call settings (forwarding, DND, etc.)
- XSI-based operations

### The `spark:all` Scope

The `spark:all` scope grants full access to a Webex account and allows applications to behave as native Webex clients, including calling features when using Webex SDKs. Use this scope sparingly — prefer requesting only the scopes your application needs.

### Scope Parsing in wxc_sdk

The SDK includes a `parse_scopes` utility that handles multiple input formats — full authorization URLs, query strings, URL-encoded strings, or plain space-separated scope lists:

```python
from wxc_sdk.scopes import parse_scopes

# All of these work:
scopes = parse_scopes('spark:calls_read spark:calls_write spark:people_read')
scopes = parse_scopes('spark%3Acalls_read%20spark%3Acalls_write')
scopes = parse_scopes('https://webexapis.com/v1/authorize?...&scope=spark%3Acalls_read%20...')
```

---

## wxc_sdk Auth Setup

> **Note:** The async variant `AsWebexSimpleApi` (from `wxc_sdk.as_api`) accepts identical token arguments and initialization patterns. See `wxc-sdk-patterns.md` section 4 for async usage details.

### Initialization Patterns

The `WebexSimpleApi` class accepts tokens in three forms:

```python
from wxc_sdk import WebexSimpleApi
from wxc_sdk.tokens import Tokens
```

**Pattern 1 — String token (simplest, for dev/testing):**

```python
api = WebexSimpleApi(tokens='YOUR_ACCESS_TOKEN')
```

Internally, this wraps the string in a `Tokens(access_token='...')` object.

**Pattern 2 — Environment variable (no arguments):**

```python
import os
os.environ['WEBEX_ACCESS_TOKEN'] = 'YOUR_ACCESS_TOKEN'

api = WebexSimpleApi()  # reads from WEBEX_ACCESS_TOKEN
```

If no `tokens` argument is provided and `WEBEX_ACCESS_TOKEN` is not set, a `ValueError` is raised:
```
ValueError: if no access token is passed, then a valid access token has to be present in
WEBEX_ACCESS_TOKEN environment variable
```

**Pattern 3 — Tokens object (for OAuth/service app flows):**

```python
tokens = Tokens(
    access_token='...',
    refresh_token='...',
    expires_in=1209600,
    refresh_token_expires_in=7776000,
    token_type='Bearer',
    scope='spark:calls_read spark:calls_write'
)
tokens.set_expiration()  # calculate expires_at from expires_in

api = WebexSimpleApi(tokens=tokens)
```

**Pattern 4 — Pre-built RestSession:**

```python
from wxc_sdk.rest import RestSession

session = RestSession(tokens=tokens, concurrent_requests=10, retry_429=True)
api = WebexSimpleApi(session=session)
```

### Constructor Parameters

```python
WebexSimpleApi(
    tokens: Union[str, Tokens] = None,    # access token or Tokens object
    concurrent_requests: int = 10,         # max parallel requests (semaphore)
    retry_429: bool = True,                # auto-retry on rate limiting
    session: RestSession = None,           # pre-built session (overrides above)
)
```

### Context Manager Support

`WebexSimpleApi` supports the context manager protocol, which closes the underlying session on exit:

```python
with WebexSimpleApi(tokens=tokens) as api:
    me = api.people.me()
    # session is automatically closed at the end of the block
```

### Full OAuth Integration Example

From `examples/get_tokens.py` — obtains tokens via OAuth flow, caches to YML, and initializes the API:

```python
from dotenv import load_dotenv
from wxc_sdk import WebexSimpleApi
from wxc_sdk.integration import Integration
from wxc_sdk.scopes import parse_scopes
from wxc_sdk.tokens import Tokens

# Load environment variables
load_dotenv('get_tokens.env')

# Build integration from env vars
integration = Integration(
    client_id=os.getenv('TOKEN_INTEGRATION_CLIENT_ID'),
    client_secret=os.getenv('TOKEN_INTEGRATION_CLIENT_SECRET'),
    scopes=parse_scopes(os.getenv('TOKEN_INTEGRATION_CLIENT_SCOPES')),
    redirect_url='http://localhost:6001/redirect'
)

# Get tokens (reads from cache or initiates OAuth flow)
tokens = integration.get_cached_tokens_from_yml(yml_path='get_tokens.yml')

# Use the API
api = WebexSimpleApi(tokens=tokens)
me = api.people.me()
print(f'Authenticated as {me.display_name} ({me.emails[0]})')
```

**Required `.env` file:**
```bash
TOKEN_INTEGRATION_CLIENT_ID=Ce429631...
TOKEN_INTEGRATION_CLIENT_SECRET=a1b2c3d4...
TOKEN_INTEGRATION_CLIENT_SCOPES=spark:calls_read spark:calls_write spark:people_read spark-admin:telephony_config_read
```

---

## Raw HTTP via api.session

<!-- Added by playbook session 2026-03-18 -->

The wxc_sdk `WebexSimpleApi` object is not just an SDK client — it also provides a pre-authenticated HTTP session you can use to call **any** Webex API endpoint directly, without going through typed SDK methods. This is the pattern used by the wxcli auto-generated commands.

### Why Use Raw HTTP

- **Coverage gaps:** The SDK may not yet wrap every Webex Calling endpoint. Raw HTTP lets you call any documented (or undocumented) API.
- **Exact control:** You send the exact JSON body and query params the API expects, with no SDK data model translation.
- **Same auth:** The session inherits all authentication, token refresh, rate-limit retry, and concurrency control from the `WebexSimpleApi` you already set up.

### How It Works

Initialize `WebexSimpleApi` using any auth method from the sections above. Then use `api.session.rest_*()` methods for direct HTTP calls:

```python
from wxc_sdk import WebexSimpleApi

# Auth via environment variable (same as SDK usage)
# export WEBEX_ACCESS_TOKEN=YOUR_TOKEN
api = WebexSimpleApi()

BASE = "https://webexapis.com/v1"

# GET — list people
result = api.session.rest_get(f"{BASE}/people", params={"max": 100})
# result is a parsed JSON dict, e.g. {"items": [...]}

# POST — create a resource
body = {"displayName": "Test User", "emails": ["test@example.com"]}
result = api.session.rest_post(f"{BASE}/people", json=body)

# PUT — update a resource
api.session.rest_put(f"{BASE}/people/{person_id}", json=updated_body)

# DELETE — remove a resource
api.session.rest_delete(f"{BASE}/people/{person_id}")
```

### Available Session Methods

| Method | HTTP Verb | Returns | Notes |
|--------|-----------|---------|-------|
| `api.session.rest_get(url, params=...)` | GET | Parsed JSON dict | Use `params` for query string |
| `api.session.rest_post(url, json=...)` | POST | Parsed JSON dict | Use `json` for request body |
| `api.session.rest_put(url, json=...)` | PUT | Parsed JSON dict or `None` | Use `json` for request body |
| `api.session.rest_delete(url)` | DELETE | `None` | No response body |

### Key Constraints

- **Full URLs required:** You must provide the complete URL including `https://webexapis.com/v1/...`. The session does not prepend a base URL.
- **No auto-pagination:** Unlike typed SDK methods (e.g., `api.people.list()`), raw HTTP calls return a single page. To paginate, pass `max=1000` and handle `next` links yourself.
- **Responses are plain dicts:** Results are parsed JSON dictionaries, not SDK model objects. Access fields with bracket notation (`result["items"]`), not dot notation.
- **Errors raise `RestError`:** All HTTP errors (401, 403, 404, 429, etc.) raise `wxc_sdk.rest.RestError`, just like typed SDK calls.

### Auth Inheritance

The session inherits every auth behavior from `WebexSimpleApi`:

| Feature | Behavior with raw HTTP |
|---------|----------------------|
| `WEBEX_ACCESS_TOKEN` env var | Works — session reads the token automatically |
| `Tokens` object with refresh | Works — session refreshes transparently before expired requests |
| Service app tokens | Works — same `Integration.refresh()` flow, then pass `Tokens` to `WebexSimpleApi` |
| `retry_429=True` | Works — session retries rate-limited requests automatically |
| `concurrent_requests=10` | Works — session enforces the semaphore on raw HTTP calls too |
| Debug logging | Works — `Authorization` headers are masked as `Bearer ***` |

### Complete Example: Service App + Raw HTTP

```python
import os
from wxc_sdk import WebexSimpleApi
from wxc_sdk.integration import Integration
from wxc_sdk.tokens import Tokens

# Set up service app auth (identical to SDK pattern)
tokens = Tokens(refresh_token=os.getenv('SERVICE_APP_REFRESH_TOKEN'))
integration = Integration(
    client_id=os.getenv('SERVICE_APP_CLIENT_ID'),
    client_secret=os.getenv('SERVICE_APP_CLIENT_SECRET'),
    scopes=[],
    redirect_url=None
)
integration.refresh(tokens=tokens)

# Use the authenticated session for raw HTTP calls
BASE = "https://webexapis.com/v1"

with WebexSimpleApi(tokens=tokens) as api:
    # List all locations
    locations = api.session.rest_get(
        f"{BASE}/locations", params={"max": 1000}
    )
    for loc in locations.get("items", []):
        print(f"{loc['name']} ({loc['id']})")

    # Read telephony config for a location
    loc_id = locations["items"][0]["id"]
    tele = api.session.rest_get(
        f"{BASE}/telephony/config/locations/{loc_id}"
    )
    print(f"Calling line ID: {tele.get('callingLineId')}")
```

### When to Use SDK Methods vs Raw HTTP

| Situation | Use |
|-----------|-----|
| Endpoint is wrapped by wxc_sdk (e.g., `api.people.list()`) | SDK method — typed, paginated, validated |
| Endpoint is not in wxc_sdk yet | Raw HTTP via `api.session.rest_*()` |
| You need exact control over request body/params | Raw HTTP |
| You need auto-pagination over large result sets | SDK method (handles `next` links automatically) |
| Building CLI commands from Postman collections | Raw HTTP (the wxcli auto-gen pattern) |

---

## Token Refresh Flow

### How the SDK Handles Refresh

The `Integration` class provides the refresh logic. Here is the flow:

1. **Check remaining lifetime** via `tokens.remaining` (returns seconds until expiry)
2. **If below threshold**, call `integration.refresh(tokens=tokens)` which POSTs to `https://webexapis.com/v1/access_token`
3. **Tokens are updated in place** — the `access_token`, `expires_in`, `expires_at`, `refresh_token`, and `refresh_token_expires_at` fields are all refreshed

```python
# Manual refresh check
if tokens.remaining < 300:  # less than 5 minutes
    integration.refresh(tokens=tokens)
```

### Automatic Token Validation

The `Integration.validate_tokens()` method encapsulates the check-and-refresh pattern:

```python
changed = integration.validate_tokens(tokens=tokens, min_lifetime_seconds=300)
# changed=True means a refresh was attempted
# If refresh fails, tokens.access_token is set to None
```

### Cached Token Flow (get_cached_tokens)

The `Integration.get_cached_tokens()` method implements the full lifecycle:

1. Read tokens from cache (callback-based — YML, database, etc.)
2. Validate tokens (refresh if needed)
3. If no valid token exists, initiate a full OAuth flow
4. Write updated tokens back to cache

```python
tokens = integration.get_cached_tokens_from_yml(
    yml_path='tokens.yml',
    force_new=False  # set True to skip cache and force new OAuth flow
)
```

### The Tokens Model

```python
class Tokens(BaseModel):
    access_token: Optional[str]              # the bearer token
    expires_in: Optional[int]                # lifetime in seconds at creation time
    expires_at: Optional[datetime]           # computed absolute expiry (UTC)
    refresh_token: Optional[str]             # refresh token
    refresh_token_expires_in: Optional[int]  # refresh token lifetime at creation
    refresh_token_expires_at: Optional[datetime]  # computed absolute expiry (UTC)
    token_type: Optional[Literal['Bearer']]  # always 'Bearer'
    scope: Optional[str]                     # space-separated scope list
```

Key methods:
- `set_expiration()` — computes `expires_at` and `refresh_token_expires_at` from current time + `expires_in`
- `remaining` — property returning seconds until access token expiry
- `update(new_tokens)` — copies all fields from another `Tokens` instance (used during refresh)

### Service App Refresh (No OAuth Flow)

Service apps skip the authorization code flow entirely. They use only the refresh step:

```python
# Service app environment variables
# SERVICE_APP_REFRESH_TOKEN, SERVICE_APP_CLIENT_ID, SERVICE_APP_CLIENT_SECRET

tokens = Tokens(refresh_token=os.getenv('SERVICE_APP_REFRESH_TOKEN'))
integration = Integration(
    client_id=os.getenv('SERVICE_APP_CLIENT_ID'),
    client_secret=os.getenv('SERVICE_APP_CLIENT_SECRET'),
    scopes=[],
    redirect_url=None
)
integration.refresh(tokens=tokens)

# tokens now has a valid access_token
api = WebexSimpleApi(tokens=tokens)
```

---

## Common Auth Errors

### HTTP 401 Unauthorized

**Causes:**
- Access token has expired (personal access token after 12 hours, integration token after 14 days)
- Token is malformed or has been revoked
- Missing `Authorization` header entirely
- Wrong token type (e.g., using a refresh token as an access token)

**SDK behavior:** Raises `RestError` with `response.status_code == 401`.

**Fix:** Refresh the token (for integrations/service apps) or generate a new personal access token.

### HTTP 403 Forbidden

**Causes:**
- Token is valid but lacks the required scope for the endpoint
- Non-admin user trying to access `spark-admin:` endpoints
- Bot token trying to access calling endpoints it does not have permission for
- Service app not authorized by the org admin

**Common scope mismatches:**

| Attempted Action | Missing Scope |
|-----------------|---------------|
| Read telephony config | `spark-admin:telephony_config_read` |
| Modify call queue | `spark-admin:telephony_config_write` |
| Read call history | `spark:calls_read` |
| Control a call | `spark:calls_write` |
| Read CDR records | `spark-admin:calling_cdr_read` |

**Fix:** Verify the scopes on your integration/service app include what the endpoint requires. For admin scopes, confirm the authorizing user is a full org admin.

### HTTP 429 Too Many Requests

**Cause:** Rate limiting. Webex APIs enforce per-token request limits.

**SDK behavior:** When `retry_429=True` (the default), the SDK automatically retries after the duration specified in the `Retry-After` response header, up to a maximum wait of 60 seconds (`RETRY_429_MAX_WAIT`).

**Response header:**
```
Retry-After: 5
```

### Token Expiry Symptoms

| Symptom | Likely Cause |
|---------|-------------|
| 401 after exactly 12 hours | Personal access token expired |
| 401 after ~14 days | Integration access token expired, refresh needed |
| 401 immediately after refresh attempt | Refresh token also expired (>90 days) — full re-auth required |
| `tokens.remaining` returns 0 | Access token is not set or has expired |
| `ValueError` on `WebexSimpleApi()` | No token provided and `WEBEX_ACCESS_TOKEN` env var not set |

### Error Response Format

Webex API errors return JSON with a tracking ID useful for support:

```json
{
  "message": "The request requires a valid access token set in the Authorization request header.",
  "errors": [
    {
      "description": "The request requires a valid access token set in the Authorization request header."
    }
  ],
  "trackingId": "ROUTER_6542a1b2-..."
}
```

The SDK parses this into a `RestError` with `.detail` containing an `ErrorDetail` object:
- `error.detail.message` — the error message
- `error.detail.tracking_id` — the tracking ID for Webex TAC support
- `error.detail.description` — specific error description (from nested `errors` array)
- `error.detail.code` — numeric error code (when present)

### Debugging Auth Issues

Enable SDK debug logging to see full request/response details (tokens are masked automatically):

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

The SDK masks `Authorization` headers as `Bearer ***` and redacts `access_token`, `refresh_token`, and `client_secret` values in logged output.

---

## Quick Reference: Which Auth Method to Use

| Scenario | Method | Notes |
|----------|--------|-------|
| Quick API test in terminal | Personal Access Token | Fastest to start, expires in 12h |
| Production app acting as a user | OAuth Integration | Standard OAuth 2.0 code flow |
| Nightly automation / cron job | Service App | No user interaction needed |
| Chatbot responding to messages | Bot Token | Does not expire, but limited calling access |
| One-off script during development | Personal Access Token or `WEBEX_ACCESS_TOKEN` env var | Use env var to avoid token in source code |
| CI/CD pipeline | Service App | Store credentials in secrets manager |

---

## Gotchas (Cross-Cutting)

- **call-controls requires user-level OAuth.** Admin tokens and service-app tokens get HTTP 400 "Target user not authorized" on `/telephony/calls` endpoints. Use a calling-licensed user's OAuth token for call control operations.
- **`spark-admin:` scopes require full org admin.** If the authorizing user is a read-only admin or compliance officer, requests to admin endpoints will return 403 even with the correct scopes listed on the integration.
- **Personal access tokens carry all scopes silently.** A personal access token for an org admin includes all `spark-admin:` scopes without requesting them, which can mask scope-related bugs that appear only in production integrations.
- **Service app refresh tokens can expire.** Although the initial refresh token is long-lived, if it is not used within its expiry window the service app must be re-authorized by an org admin.

---

## Webex for Government (FedRAMP)

Webex for Government is a parallel deployment with separate URLs and feature restrictions.

### Base URLs

| Service | Standard | FedRAMP |
|---------|----------|---------|
| API | `webexapis.com/v1` | `api-usgov.webex.com/v1` |
| Control Hub | `admin.webex.com` | `admin-usgov.webex.com` |
| Developer Portal | `developer.webex.com` | `developer-usgov.webex.com` |
| CDR/Analytics | `analytics.webexapis.com` | `analytics-calling-gov.webexapis.com` |

### Feature Restrictions

These features/APIs are **not supported** in FedRAMP deployments:

| Feature | Reference Doc | Notes |
|---------|---------------|-------|
| DECT Devices | [devices-dect.md](devices-dect.md) | Entire DECT API excluded |
| Announcements & Playlists | [location-call-settings-media.md](location-call-settings-media.md) | Upload and playlist APIs excluded |
| Call Recording (location-level) | [location-call-settings-advanced.md](location-call-settings-advanced.md) | Recording vendor config excluded |
| Caller Reputation | [location-call-settings-advanced.md](location-call-settings-advanced.md) | Provider config excluded |
| Operating Modes | [call-features-additional.md](call-features-additional.md) | Mode management excluded |
| Hot Desking | [devices-dect.md](devices-dect.md) | Hot desk portal excluded |
| AA `directLineCallerIdName` | [call-features-major.md](call-features-major.md) | Use `firstName`/`lastName` instead |
| AA `dialByName` | [call-features-major.md](call-features-major.md) | Not available |
| 3rd-party device SIP mgmt | [devices-core.md](devices-core.md) | `line_port`, `sip_user_name` retrieval and SIP password modification |
| UC-One settings | [person-call-settings-behavior.md](person-call-settings-behavior.md) | UC Manager Profile config |
| MS Teams integration | [person-call-settings-behavior.md](person-call-settings-behavior.md) | MS Teams calling settings |

### Authentication Differences

- **Service App tokens** (`spark:applications_token` scope): NOT supported in FedRAMP
- **Bot/Integration creation**: Must use REST API (`POST /applications`), not the developer portal UI
- **Application webhooks** (`application:webhooks_write/read`): NOT supported

### wxcli Usage

Set the base URL before running commands:

```bash
# Configure wxcli for FedRAMP
wxcli configure --base-url https://api-usgov.webex.com/v1
```

---

## See Also

- **`provisioning.md`** — Provisioning-specific scope requirements and end-to-end user/license/location provisioning workflows.
- **`wxc-sdk-patterns.md`** — SDK code recipes, async auth patterns, and the service app token caching pattern (section 3, Pattern D).
