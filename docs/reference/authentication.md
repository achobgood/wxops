# Authentication Reference — Webex Calling APIs

This document covers every authentication method available for the Webex Calling APIs, including token types, OAuth flows, and scope requirements for each.

**Execution path:** authenticate with `wxcli configure` and verify with `wxcli whoami`. When an operation has no `wxcli` command, fall back to raw HTTP via `wxcli.auth.get_api()` (see [Raw HTTP via api.session](#raw-http-via-apisession)).

## Sources

- OpenAPI specs: specs/webex-cloud-calling.json, specs/webex-admin.json
- developer.webex.com Authentication APIs

---

## Table of Contents

1. [Authentication Methods Overview](#authentication-methods-overview)
2. [Personal Access Tokens](#personal-access-tokens)
3. [OAuth Integrations](#oauth-integrations)
4. [Service Apps](#service-apps)
5. [Partner/Multi-Org Tokens](#partnerulti-org-tokens)
6. [Bot Tokens](#bot-tokens)
7. [Guest Issuer Tokens](#guest-issuer-tokens)
8. [Calling-Related Scopes](#calling-related-scopes)
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
- Carries most scopes your account has access to (including `spark-admin:*` scopes if you are an admin), but does NOT include Contact Center scopes (`cjp:config_read`, `cjp:config_write`). CC config operations require an OAuth integration with CC scopes explicitly selected.
- Intended strictly for development and testing — never embed in production code
- **Contact Center limitation:** Even full admins on CC-provisioned orgs get 403 on CC config endpoints (`api.wxcc-{region}.cisco.com`) with a PAT. Create an OAuth integration at developer.webex.com with `cjp:config_read` and `cjp:config_write` scopes, complete the OAuth flow, and use that token instead.

**Usage:**

`wxcli configure` prompts for the token and saves it to `~/.wxcli/config.json`, so it persists across shell invocations. Verify with `wxcli whoami`.

```bash
# Prompts for the token ("Webex API token:")
wxcli configure

# Or pipe it in non-interactively
echo "YOUR_PERSONAL_ACCESS_TOKEN" | wxcli configure

# Confirm the token works — prints the authenticated user, org, and time remaining
wxcli whoami
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

This returns a standard OpenID Connect discovery document including `authorization_endpoint`, `token_endpoint`, `userinfo_endpoint`, `jwks_uri`, supported scopes (`openid`, `email`, `profile`, `phone`, `address`), and `code_challenge_methods_supported` (`plain`, `S256`).

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
| CJP scopes (`cjp:config_read`, `cjp:config_write`) | **Supported.** Select them at app creation in the developer portal. Confirmed by Cisco's "Introducing Service Apps for Webex Contact Center" blog post. `spark:applications_token` and `spark:kms` are NOT available for CC service apps — those require a separate OAuth integration. |
| CJDS scopes (`cjds:admin_org_read`, `cjds:admin_org_write`) | **Required for JDS admin APIs** (`/admin/v1/api/...` — workspace, person, template management). Standard `cjp:` scopes alone do NOT grant JDS admin access. The runtime profile view and event stream endpoints (`/v1/api/...`) may differ — verify per endpoint. Select these in addition to `cjp:` scopes when building JDS integrations. |
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
| Refresh token | 90 days | 90-day expiry clock resets each time you make a refresh call (use the refresh token to generate a new access token). Simply using the access token does NOT reset it. |
| Client secret | Does not expire | Regenerate via developer portal if compromised |

**For long-lived automations**, Webex recommends a 3-tier pattern:

1. **Tier 1:** Use the service app's refresh token to get new access tokens (normal operation)
2. **Tier 2:** If the refresh token expires (90 days unused), use the Applications API with a separate OAuth integration to regenerate it
3. **Tier 3:** The OAuth integration's own refresh token, refreshed by your token manager

This requires two Webex apps: your working service app and a token-manager integration. See the [Service App Token Management blog post](https://developer.webex.com/blog/service-app-token-management-a-developer-s-guide-to-automation) for details.

### Environment Variables (Service App Credentials)

```bash
SERVICE_APP_REFRESH_TOKEN=<refresh_token>
SERVICE_APP_CLIENT_ID=<client_id>
SERVICE_APP_CLIENT_SECRET=<client_secret>
```

### Service App Refresh — API Shape Reference

With `wxcli`, feed the service app's current access token to `wxcli configure` and verify with `wxcli whoami`. There is no `wxcli` command for the refresh-token exchange itself — perform that against `https://webexapis.com/v1/access_token` (see [Token Refresh Flow](#token-refresh-flow)), then configure the resulting access token.

### Region Extraction from Token

Webex access tokens encode the CI (Common Identity) cluster and org ID directly in the token string. A production app can extract both without a separate API call:

```python
parts = access_token.split('_')
# parts[0] = the access token value
# parts[1] = ciCluster (e.g. "us1", "eu1", "us2")
# parts[2] = orgId (base64-encoded Spark ID)
ci_cluster = parts[1]
```

This is especially important for **Contact Center APIs**, which use a regional base URL rather than `webexapis.com`:

```
https://api.wxcc-{ciCluster}.cisco.com
```

For example, a token from a US org with `ciCluster = "us1"` hits `https://api.wxcc-us1.cisco.com`. The `get_cc_org_id()` helper in `wxcli/config.py` performs both the cluster extraction and the org ID decoding.

---

## Partner/Multi-Org Tokens

Partner/VAR/MSP admins hold tokens that have access to multiple customer organizations. Most Webex API endpoints accept an `orgId` query parameter to target a specific customer org; without it, the API defaults to the partner's own org (usually not what you want).

### How wxcli handles partner tokens

wxcli detects multi-org tokens automatically and manages `orgId` injection transparently:

| Command | Purpose |
|---------|---------|
| `wxcli configure` | Detects whether the token has multi-org access. If so, lists available customer orgs and prompts you to select one. The chosen `orgId` is saved to the config file. |
| `wxcli switch-org` | Change the active target org at any time without re-running `configure`. |
| `wxcli clear-org` | Remove the saved `orgId` to revert to single-org (partner-org) behavior. |
| `wxcli whoami` | Shows a "Target: <org name>" line when a target org is set. |

Once a target org is configured, 668 of 804 generated commands automatically inject `orgId` from config on every API call that accepts the parameter — no `--org-id` flag required. The four hand-coded command files (users, licenses, locations, numbers) also inject `orgId` the same way.

### Builder agent behavior

When the builder agent detects a partner token (section 2b of its workflow), it pauses and requires explicit org confirmation before proceeding. This prevents accidentally configuring the wrong customer org.

### Scopes for partner tokens

Partner tokens use the same `spark-admin:` scopes as regular admin tokens. No additional scopes are required to access customer org data — the token type (partner) is what grants cross-org access, not a special scope.

### Gotchas

- **`organizations list` returns multiple orgs for partner tokens.** wxcli uses this call to detect partner tokens: if the response contains more than one org, it treats the token as multi-org and prompts for selection. Single-org admins always see exactly one result.
- **Some endpoints do not accept `orgId`.** The 136 of 804 endpoints that do not accept `orgId` operate in the context of the token's own org. These are typically endpoints that are inherently org-scoped (e.g., `/v1/organizations/{orgId}/...` where the org is a path param, not a query param).
- **Service app tokens scoped to a single customer org** behave like single-org tokens and do not trigger multi-org detection.

---

## Bot Tokens

Bots are special Webex identities with their own access token.

**Key facts:**
- Bot tokens **do not expire** — they remain valid until the bot is deleted or regenerated
- No refresh token is provided (none needed)
- Bots have their own identity (separate from any user)
- Bots can interact with messaging, spaces, and webhooks
- Bot tokens have **limited scope for Calling APIs** — bots cannot place or manage calls on behalf of users

**Usage:**

```bash
echo "BOT_ACCESS_TOKEN" | wxcli configure
wxcli whoami
```

Since bot tokens never expire, no refresh logic is needed.

### Gotchas

- **Bot calling scopes unverified.** The exact list of calling-related scopes available to bots (if any) has not been confirmed. The developer.webex.com docs list scopes with a `show_for_app_type` property for "integration" and "serviceApp" but do not enumerate bot-specific scopes. Calling scopes like `spark:calls_read` and `spark:calls_write` appear to be user-level scopes for integrations. Bots likely cannot use calling scopes since they don't act on behalf of a user, but this has not been confirmed with a live bot token. *(Unverified — requires live bot token testing. Checked 2026-03-19.)*

---

## Guest Issuer Tokens

> **⚠️ End of Life — December 31, 2025**
> The Guest Issuer API has been deprecated and reached End of Life on December 31, 2025. New Guest Issuer applications can no longer be created. Existing applications should migrate to **Service Apps** with guest management functionality. The section below is retained for reference only.

Guest Issuer tokens create temporary, anonymous guest users for scenarios like customer-facing meetings or support sessions.

**Key facts:**
- Managed via Service Apps with `guest-issuer:read` and `guest-issuer:write` scopes
- Guest tokens are short-lived
- **Not applicable to Webex Calling APIs** — guests cannot access telephony features

### Gotchas

- **Guest token lifetime is variable, set by `expiresIn` in the response.** The OpenAPI spec example shows `expiresIn: 64799` (~6 hours), but the actual lifetime is returned per-token at creation time via the `expiresIn` field. There is no single fixed lifetime — it depends on org/service-app configuration.

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

---

## Raw HTTP via api.session

<!-- Added by playbook session 2026-03-18 -->

`wxcli.auth.get_api()` returns a pre-authenticated object whose `.session` can call **any** Webex API endpoint directly. This is the fallback path when no `wxcli` command covers an operation.

### Why Use Raw HTTP

- **Coverage gaps:** Not every Webex Calling endpoint has a `wxcli` command. Raw HTTP lets you call any documented (or undocumented) API.
- **Exact control:** You send the exact JSON body and query params the API expects, with no data model translation.
- **Same auth:** The session reads the token saved by `wxcli configure` and inherits its token resolution and rate-limit retry.

### How It Works

`get_api()` picks up the token you saved with `wxcli configure` — no separate auth setup. Then use `api.session.rest_*()` methods for direct HTTP calls:

```python
from wxcli.auth import get_api

# Reads the token saved by `wxcli configure`
api = get_api()

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
| `api.session.rest_delete(url, params=...)` | DELETE | Parsed JSON dict | Typically no response body |
| `api.session.rest_patch(url, json=..., content_type=...)` | PATCH | Parsed JSON dict | `content_type` overrides the default when an endpoint demands it |
| `api.session.follow_pagination(url, params=..., item_key="items")` | GET | Generator of items | Follows `Link: rel="next"` and yields each item across all pages |

### Key Constraints

- **Full URLs required:** You must provide the complete URL including `https://webexapis.com/v1/...`. The session does not prepend a base URL.
- **`rest_get` returns one page:** `rest_get` returns a single page. For multi-page result sets use `api.session.follow_pagination(url)`, which follows the `Link: rel="next"` header and yields every item.
- **Responses are plain dicts:** Results are parsed JSON dictionaries, not model objects. Access fields with bracket notation (`result["items"]`), not dot notation.
- **Errors raise `WebexError`:** All HTTP errors (401, 403, 404, 429, etc.) raise `wxcli.auth.WebexError`, which carries a `status_code` attribute.

### Auth Inheritance

The session inherits its auth from whatever `wxcli configure` saved:

| Feature | Behavior with raw HTTP |
|---------|----------------------|
| `WEBEX_ACCESS_TOKEN` / `WEBEX_TOKEN` env var | Checked first, in that order — an env var overrides the config file |
| Token saved by `wxcli configure` | Read from `~/.wxcli/config.json` when neither env var is set |
| No token at all | `get_api()` exits with `Error: No token found. Run 'wxcli configure' or set WEBEX_ACCESS_TOKEN.` |
| Rate-limit retry | Up to 3 retries on 429, honoring `Retry-After`; set `WXCLI_NO_RETRY=1` to disable |
| Debug logging | `get_api(debug=True)` raises the log level to DEBUG |

### Complete Example: Raw HTTP

Whatever token `wxcli configure` saved (personal, integration, or service app access token) is the one this session uses.

```python
from wxcli.auth import get_api

api = get_api()

BASE = "https://webexapis.com/v1"

# List all locations — follow_pagination yields items across every page
locations = list(api.session.follow_pagination(f"{BASE}/locations"))
for loc in locations:
    print(f"{loc['name']} ({loc['id']})")

# Read telephony config for a location
loc_id = locations[0]["id"]
tele = api.session.rest_get(f"{BASE}/telephony/config/locations/{loc_id}")
print(f"Calling line ID: {tele.get('callingLineId')}")
```

### When to Use a wxcli Command vs Raw HTTP

| Situation | Use |
|-----------|-----|
| A `wxcli` command covers the operation | The `wxcli` command — it encodes required fields, auth, and validation. Confirm with `wxcli <group> <command> --help` |
| No `wxcli` command covers the endpoint | Raw HTTP via `api.session.rest_*()` |
| You need exact control over request body/params | Raw HTTP |
| You need every item across a large result set | `api.session.follow_pagination()` (handles `next` links automatically) |

---

## Token Refresh Flow

Both OAuth integrations and service apps refresh access tokens the same way: POST to `https://webexapis.com/v1/access_token` with `grant_type=refresh_token` (see [OAuth Flow (4 Steps)](#oauth-flow-4-steps) and [Authentication Flow](#authentication-flow) under Service Apps). The response returns a new `access_token` and, in most cases, a renewed `refresh_token` with a fresh 90-day (60-day in FedRAMP) expiry.

Via `wxcli`, there is no dedicated refresh command — perform the raw HTTP refresh call above, then feed the resulting access token to `wxcli configure` and confirm with `wxcli whoami`.

---

## Common Auth Errors

### HTTP 401 Unauthorized

**Causes:**
- Access token has expired (personal access token after 12 hours, integration token after 14 days)
- Token is malformed or has been revoked
- Missing `Authorization` header entirely
- Wrong token type (e.g., using a refresh token as an access token)

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
| Access token has no remaining lifetime | Access token is not set or has expired |
| `Error: No token found` from `get_api()` | No token saved by `wxcli configure` and `WEBEX_ACCESS_TOKEN` env var not set |

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

### Debugging Auth Issues

Enable debug logging via `wxcli.auth.get_api(debug=True)`, which raises the log level to DEBUG for full request/response visibility.

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
| Production CC app | Service App with CJP scopes | Select `cjp:config_read`/`cjp:config_write` at creation; regional base URL (`api.wxcc-{ciCluster}.cisco.com`) |

---

## Gotchas (Cross-Cutting)

- **call-controls requires user-level OAuth.** Admin tokens and service-app tokens get HTTP 400 "Target user not authorized" on `/telephony/calls` endpoints. Use a calling-licensed user's OAuth token for call control operations.
- **`spark-admin:` scopes require full org admin.** If the authorizing user is a read-only admin or compliance officer, requests to admin endpoints will return 403 even with the correct scopes listed on the integration.
- **Personal access tokens carry all scopes silently.** A personal access token for an org admin includes all `spark-admin:` scopes without requesting them, which can mask scope-related bugs that appear only in production integrations.
- **Service app refresh tokens can expire.** Although the initial refresh token is long-lived, if it is not used **to generate a new access token** within 90 days, it expires and the service app must be re-authorized by an org admin. Simply using the access token does not reset the 90-day clock — only making a refresh call does.

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
| Announcements & Playlists | [location-calling-media.md](location-calling-media.md) | Upload and playlist APIs excluded |
| Call Recording (location-level) | [location-recording-advanced.md](location-recording-advanced.md) | Recording vendor config excluded |
| Caller Reputation | [location-recording-advanced.md](location-recording-advanced.md) | Provider config excluded |
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
- **OAuth integration refresh token lifetime:** 60 days in FedRAMP (vs. 90 days in commercial). The 60-day clock resets each time a refresh call is made.
- **Guest Issuer tokens:** Not supported in FedRAMP (and globally EOL'd December 31, 2025 — see Guest Issuer section).

### wxcli Usage

Set the base URL before running commands:

```bash
# Configure wxcli for FedRAMP
wxcli configure --base-url https://api-usgov.webex.com/v1
```

---

## See Also

- **`provisioning.md`** — Provisioning-specific scope requirements and end-to-end user/license/location provisioning workflows.
