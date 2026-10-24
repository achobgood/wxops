# CJDS Integration Playbook

<!-- ref-tag: cjds-integration-v1 -->

## Overview

The **Customer Journey Data Service (CJDS)** is Webex's built-in customer journey store. It captures interactions across any channel, stores them against a customer identity, and exposes them for real-time routing decisions.

**Two integration paths — use the right one:**

| Where your flow lives | Use |
|---|---|
| **Webex Connect** flow | Native **Customer Journey Data** node (no HTTP Request needed) |
| **WxCC Flow Designer** flow | **HTTP Request** activity calling CJDS REST APIs directly |

> **Flex 3 requirement:** The native Webex Connect CJD node is available only for Flex 3 Webex Contact Center customers. Flow Designer flows use the HTTP Request node regardless of license tier.

---

## 1. Find Your Workspace ID and Region

Every CJDS API call requires a **workspaceId** (not the same as your org ID).

1. Go to **Control Hub** (admin.webex.com)
2. Navigate to **Contact Center > Customer Journey Data**
3. Copy the **Workspace ID** (also called Project ID)

4. Find your region under **Contact Center > Settings > General**, then read your base URL out of the table below.

**One host for reads and writes: `https://api.wxcc-{region}.cisco.com`** [owner: `contact-center-journey.md` intro]. Verified live 2026-10-19 (us1): the workspace list, the person list and an alias lookup answered on `https://api.wxcc-us1.cisco.com`; the progressive-profile and event-query reads in Section 4 were not run on it. The examples below use that host.

**History — the former read domain does not resolve.** Before 2026-10-19 this section sent reads (alias lookups, progressive profile, event queries) to the hosts below. On 2026-10-19 each of them, and `ciscowxdap.com` itself, returned NXDOMAIN in DNS:

| Data Center | Former CJDS read base URL (NXDOMAIN 2026-10-19) |
|---|---|
| US East 1 | `https://api-jds.prod-useast1.ciscowxdap.com` |
| US East 2 | `https://api-jds.prod-useast2.ciscowxdap.com` |
| EU / Frankfurt | `https://api-jds.prod-eu.ciscowxdap.com` |
| APJC | `https://api-jds.prod-apjc.ciscowxdap.com` |
| Other regions | Pattern: `https://api-jds.prod-{region}.ciscowxdap.com` |

Event publishing uses the same gateway host. (Before 2026-10-19 this paragraph called the write domain "a **different host**" and its mix-up "the most common CJDS integration failure".)

⚠ **Do not use `cjaas.cisco.com` URLs** — this was the original CJDS domain and is deprecated. The current host is `api.wxcc-{region}.cisco.com` for reads and writes (the `ciscowxdap.com` read domain this note used to name returned NXDOMAIN on 2026-10-19). If you find `cjaas.cisco.com` in any existing config, it is stale.

> **Provisioning note:** Orgs created after November 1, 2025 must complete a provisioning form ([SmartSheet form](https://app.smartsheet.com/b/form/7776df72239e47d0bbb73a392e32927f)) before CJDS is available. Allow up to 72 hours. Contact your Cisco partner.

> **Partner admin visibility:** The Customer Journey Data tab in Control Hub is visible only to full customer admins, not partner admins.

### Journey Projects and Connector Activation

After provisioning, CJDS creates a default **Sandbox Project**. You must activate the Webex Contact Center connector within the project before data flows:

1. Navigate to **Control Hub > Customer Journey Data**
2. Select your project (or use the Sandbox Project)
3. **Activate** the Webex Contact Center connector

**Constraint:** Only one project can be activated at a time.

### Data Retention

Configure under **Control Hub > Customer Journey Data > Settings**:
- Minimum: 180 days
- Default: 365 days

### Contact Resolver Subflow

Community-built subflow for retrieving customer details into flow variables: [github.com/TeamCCEP/JDSContactResolver](https://github.com/TeamCCEP/JDSContactResolver)

---

## 2. Authentication

CJDS uses **Bearer token authentication** on all API calls.

### Service App Setup (one-time)

1. Go to **developer.webex.com > My Webex Apps > Create a New App**
2. Choose **Service App**
3. Add scopes:
   - `cjds:admin_org_read` — read journey data and person profiles
   - `cjds:admin_org_write` — write events and manage identities

> **Alternate scopes:** Some documentation references `cjp:config_read` and `cjp:config_write`. Both scope sets are accepted. Use `cjds:admin_org_*` for new integrations. [Owner: `cjds.md` § Authentication]

**Add both scopes even if this integration only reads.** A Service App's scopes cannot be widened without re-approval by the customer admin, and needing a second approval cycle later is the usual cause of a stalled CJDS build.

### Generate a Token

```bash
curl -X POST https://webexapis.com/v1/access_token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "scope=cjds:admin_org_read cjds:admin_org_write"
```

**Where to put the token:** a WxCC Global Variable named `CJDS_Auth_Token`, marked **Sensitive**, or a Webex Connect Asset Integration.

**Build the refresh before you build the integration.** A personal access token lasts 12 hours; a Service App or integration access token lasts 14 days, then must be refreshed, and the refresh token lasts 90 days [`authentication.md` § Authentication Methods Overview, § Token Lifetimes]. (Before 2026-10-19 this line said "8–12 hours".) A hand-pasted token survives a full day of testing and then fails in production overnight (12 hours) or two weeks later (14 days). Use the token-refresh subflow in `docs/playbooks/webex-api-auth.md` § Pattern 2.

---

## 3. Data Model

> **Owner: `cjds.md` § Data Model.** Reproduced here so this page works standalone; the reference doc wins on any disagreement.

### Identity and Aliases

A **Person** in CJDS is a unified customer profile identified by one or more **aliases**. Aliases are the contact methods that link events to a person.

| Identity Type | Example | Accepted by |
|---|---|---|
| `phone` | `+15551234567` (E.164 format) | Event schema + Connect node |
| `email` | `customer@example.com` | Event schema + Connect node |
| `customerId` | Internal CRM ID | Event schema + Connect node |
| `socialId` | Social media handle | **Connect node only** |
| `temporaryId` | Session or chat ID (transient) | **Connect node only** |

### Event Schema (CloudEvents v1.0)

All CJDS events follow the [CloudEvents specification](https://cloudevents.io/):

| Field | Required | Notes |
|---|---|---|
| `specversion` | Yes | Must be `"1.0"` |
| `id` | Yes | Unique string per source+id combination |
| `type` | Yes | Reverse-DNS format: `"task:new"`, `"appointment:booked"`, `"call:cdr_import"` |
| `source` | Yes | URI identifying the event origin: `"wxcc"`, `"web"`, `"ai_agent"` |
| `identity` | Yes | Customer alias value (phone, email, customerId) |
| `identitytype` | Yes | Enum: `email`, `phone`, `customerId` |
| `datacontenttype` | Yes | `"application/json"` |
| `data` | Yes | Freeform JSON payload |
| `time` | No | ISO 8601 timestamp |
| `previousidentity` | No | Used for identity merge operations |

### Three decisions to make before writing anything

**1. Which identity type is your primary key?** Pick one and use it everywhere. `phone` is the natural choice for voice, `customerId` if you have a CRM to join against. Mixing them produces two profiles for one human, and merging after the fact needs a Manage Identity call per duplicate.

⚠ Note the asymmetry above: `socialId` and `temporaryId` are accepted by the **Connect node but not by the event schema**. If you will write events from anywhere other than the node, do not make either of them your primary key.

**2. What is your `type` naming convention?** It is free-form, and it is what every future RSQL filter matches against. Agree the vocabulary once, at the start — renaming an event type does not rewrite history, so old events become unfindable.

**3. How will phone numbers be stored?** ⚠ CJDS may store them as 10 digits without the `+` prefix. **Neither alias lookup nor RSQL filters bridge that**: verified live 2026-10-19, a 10-digit number and its `1…` / `+1…` form do not find each other; only a leading `+` is ignored (`19103915567` ≡ `+19103915567`) [owner: `contact-center-journey.md` § 9 Gotchas, gotcha 5]. (Before 2026-10-19 this said "Alias lookup normalizes".) A lookup or filter tested against one stored form will return nothing in production if the stored form differs. Test against real stored data before relying on it.

---

## 4. WxCC Flow Designer — HTTP Request Pattern

Use these endpoints when building in **WxCC Flow Designer** (not Webex Connect).

### 4a. Check If a Caller Is Known (Alias Lookup)

Look up a person by their phone number. HTTP 200 = known caller; HTTP 404 = unknown.

**Endpoint:**
```
GET /admin/v1/api/person/workspace-id/{workspaceId}/aliases/{phoneNumber}
```

**Full request:**
```bash
curl -s \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.wxcc-us1.cisco.com/admin/v1/api/person/workspace-id/YOUR_WORKSPACE_ID/aliases/+15551234567"
```

> **Phone format matching:** the alias endpoint ignores a leading `+` but does **not** add or strip a country code. Verified live 2026-10-19 with `wxcli cc-journey show-aliases`: `+12094571613` found the person stored as `+12094571613` but not a different person stored as `2094571613`; `9103915567` → 404 although `+19103915567` is stored; `19103915567` and `+19103915567` both found that person [owner: `contact-center-journey.md` § 9 Gotchas, gotcha 5]. The raw ANI from `{{NewPhoneContact.ANI}}` works in the alias path without `%2B` encoding (this doc's earlier claim; not re-tested from a flow). (Before 2026-10-19 this note said "A lookup with `+19103915567` will match a stored value of `9103915567`" — wrong.)

> **Phone storage format:** Phone numbers in CJDS may be stored as 10 digits without country code or `+` prefix (e.g., `9103915567` not `+19103915567`). The alias lookup does not bridge this (see the note above), and RSQL filters used in event queries (Section 4d) require exact match against the stored value. (Said "The alias lookup normalizes this" before 2026-10-19.)

> **RSQL filter syntax:** When filtering by phone or other fields using RSQL, values must be single-quoted. Example: `phone=='9103915567'`, NOT `phone==9103915567`. The RSQL parser throws a `ParseException` if values are unquoted.

**Response — known caller (HTTP 200):**
```json
{
  "meta": {
    "organizationId": "<your-org-id>"
  },
  "data": [
    {
      "id": "68f63b8458f4b21f28121ea9",
      "firstName": null,
      "lastName": null,
      "phone": ["9103915567"],
      "email": [],
      "temporaryId": [],
      "customerId": [],
      "socialId": [],
      "aliases": ["9103915567"],
      "organizationId": "<your-org-id>",
      "workspaceId": "65cfdcee870a2d0e4a9864b8"
    }
  ]
}
```

**Response — unknown caller (HTTP 404):**
```json
{ "message": "Person not found" }
```

**HTTP Request node configuration (Flow Designer):**

| Field | Value |
|---|---|
| Method | GET |
| URL | `https://api.wxcc-us1.cisco.com/admin/v1/api/person/workspace-id/{{CJDS_Workspace_ID}}/aliases/{{NewPhoneContact.ANI}}` |
| Header: Authorization | `Bearer {{CJDS_Auth_Token}}` |
| Header: Content-Type | `application/json` |
| **Output Path Expression** | `$.data[0].id` → maps to flow variable `PersonID` |
| Request Timeout | 5000ms |

> **ANI encoding:** `%2B` encoding is not required; the raw ANI from `{{NewPhoneContact.ANI}}` works directly in the alias path, with the `+` (this doc's earlier claim; not re-tested from a flow — on 2026-10-19 `wxcli cc-journey show-aliases` with `+19103915567` found the stored `+19103915567` person). The endpoint does **not** match a stored 10-digit number from an E.164 ANI [owner: `contact-center-journey.md` § 9 Gotchas, gotcha 5]; if your data may hold 10-digit numbers, look those up too. (Before 2026-10-19 this note said the endpoint "normalizes phone formats".)

**Condition node after the HTTP Request:**

| Status | Meaning | Route to |
|---|---|---|
| 200 | Known caller | Fast path (skip IVR) |
| 404 | Unknown caller | IVR path |
| 500 / timeout / 401 | CJDS unavailable | IVR path (fail safe) |

```
{{CJDSLookup.httpStatusCode}} == 200  →  TRUE branch = known caller
```

Wire the HTTP Request **error** output (network/timeout failure) to the same IVR node as the 404 path.

---

### 4b. Read Progressive Profile (Repeat Caller Detection)

The Progressive Profile API aggregates journey events against a template (e.g., "count of calls in last 24 hours"). Use this for repeat caller detection instead of raw event queries.

**Prerequisite:** Create a Profile Template in Control Hub > Contact Center > Customer Journey Data > Profile Templates.

**Profile Template JSON schema:**
```json
{
  "name": "journey-default-template1",
  "attributes": [
    {
      "version": "0.1",
      "event": "task:new",
      "metaDataType": "string",
      "metaData": "origin",
      "limit": 100,
      "displayName": "No of times contacted in the last 24 hours",
      "lookBackDurationType": "hours",
      "lookBackPeriod": 24,
      "aggregationMode": "Count",
      "rules": null,
      "widgetAttributes": { "type": "table" },
      "verbose": true
    }
  ]
}
```

| Template Field | Purpose |
|---|---|
| `event` | Which event type to aggregate (e.g., `task:new`) |
| `lookBackDurationType` | `"hours"` or `"days"` |
| `lookBackPeriod` | Time window (e.g., `24` hours, `7` days) |
| `aggregationMode` | `"Count"` (other modes may be available) |
| `metaData` | Which `data` field to aggregate on |

**Profile Template admin endpoint:**
```
GET /admin/v1/api/profile-view-template/workspace-id/{workspaceId}/template-id/{templateId}
```

**Endpoint:**
```
GET /v1/api/progressive-profile-view/workspace-id/{workspaceId}/person-id/{personId}/template-id/{templateId}
```

**Full request:**
```bash
# Path from the CLI source (cc-journey); not run.
curl -s \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.wxcc-us1.cisco.com/v1/api/progressive-profile-view/workspace-id/YOUR_WORKSPACE_ID/person-id/person-abc123/template-id/YOUR_TEMPLATE_ID"
```

**Response:**
```json
{
  "data": [
    {
      "attributes": [
        {
          "displayName": "Call Count (24h)",
          "result": 3
        }
      ]
    }
  ]
}
```

**Flow Designer usage:** Requires personId from the alias lookup (Section 4a). Run alias lookup first, extract personId via `Output Path Expression: $.data[0].id`, then call progressive profile with `{{PersonID}}` in the URL.

**Output Path Expression for result:** `$.data[0].attributes[0].result` → maps to flow variable `CallCount`

> **Attribute index depends on template order.** If your template has multiple attributes, the repeat-call count may be at index `[1]` not `[0]`. The JDS_XM lab uses `$.data[0].attributes[1].result`. Check your template's attribute order and adjust the index accordingly.

**Condition after:** `{{CallCount}} >= 3` → repeat caller path

---

### 4c. Write a Journey Event

Record an event against a customer identity. Use this to log interactions to CJDS from a flow.

**Endpoint:**
```
POST https://api.wxcc-{region}.cisco.com/publish/v1/api/event?workspaceId={workspaceId}
```

> **Writes and reads use the same host.** Event writes go to `api.wxcc-{region}.cisco.com` (e.g., `api.wxcc-us1.cisco.com` for US), and so do the reads (Section 1). Before 2026-10-19 this note sent reads to an `api-jds.prod-{region}.ciscowxdap.com` domain, which returned NXDOMAIN that day.

> **Region domains (writes):** US uses `api.wxcc-us1.cisco.com`. EU may use `api.wxcc-eu1.cisco.com`. Other regions need confirmation from your Cisco partner — the slug is the gateway's (`us1`, `eu1`, …); before 2026-10-19 this note warned it "may differ from the read-domain pattern", whose hosts returned NXDOMAIN that day.

> **Deprecated endpoints:** Older documentation references `/v1/api/journey-events` and `/v1/api/journey-event-posting` on the `ciscowxdap.com` domain. The confirmed working endpoint is `/publish/v1/api/event` on the `wxcc-{region}.cisco.com` domain.

**Query parameter:** `workspaceId` (required, appended as query parameter: `?workspaceId={workspaceId}`)

**Request body:**
```json
{
  "id": "unique-event-id",
  "specversion": "1.0",
  "type": "call:cdr_import",
  "source": "webex_calling_cdr",
  "identity": "+15551234567",
  "identitytype": "phone",
  "time": "2024-11-20T09:15:00.000Z",
  "datacontenttype": "application/json",
  "data": {
    "direction": "INBOUND",
    "channelType": "telephony"
  }
}
```

**Full request:**
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.wxcc-us1.cisco.com/publish/v1/api/event?workspaceId=YOUR_WORKSPACE_ID" \
  -d '{...}'
```

Successful write returns **HTTP 202** (Accepted).

**Common event types:**

| Purpose | Recommended `type` |
|---|---|
| Historical CDR import | `call:cdr_import` |
| Live inbound call recorded by flow | `call:inbound_completed` |
| Appointment booked via AI agent | `appointment:booked` |
| Native WxCC interaction start | `task:new` |
| Native WxCC interaction end | `task:ended` |
| Agent state change | `agent:state_change` |

> `type` is freeform — you control the naming. Use a consistent namespace so flows can filter on it.

---

### 4d. Query Historic Events

Retrieve events for a customer identity, with optional RSQL filtering. Use this to check event history for routing decisions (e.g., "has this caller been verified before?").

**Endpoint:**
```
GET /v1/api/events/workspace-id/{workspaceId}
```

**Query parameters:**

| Parameter | Required | Description |
|---|---|---|
| `identity` | Yes | Customer alias value (phone, email, customerId) |
| `filter` | No | RSQL filter expression (e.g., `type=='custom:store_verified'`). Values must be single-quoted. |
| `sortBy` | No | Field to sort by |
| `sort` | No | Sort direction (`asc` or `desc`) |
| `page` | No | Page number for pagination |
| `pageSize` | No | Number of results per page |

**Full request:**
```bash
curl -s \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.wxcc-us1.cisco.com/v1/api/events/workspace-id/YOUR_WORKSPACE_ID?identity=9103915567&filter=type%3D%3D'custom%3Astore_verified'"
```

**Response:**
```json
{
  "meta": {
    "resultCount": 2
  },
  "data": [
    {
      "specversion": "1.0",
      "id": "event-id-1",
      "type": "custom:store_verified",
      "source": "ai_agent",
      "identity": "9103915567",
      "identitytype": "phone",
      "time": "2026-04-20T14:30:00.000Z",
      "data": { "store_number": "1234", "verification_method": "pin" }
    }
  ]
}
```

**Example use case — check if caller was previously verified:**

1. Query events with `filter=type=='custom:store_verified'`
2. Parse `$.meta.resultCount` — if > 0, caller has been verified before
3. Route to fast path (skip re-verification) or standard path

**HTTP Request node configuration (Flow Designer):**

| Field | Value |
|---|---|
| Method | GET |
| URL | `https://api.wxcc-us1.cisco.com/v1/api/events/workspace-id/{{CJDS_Workspace_ID}}?identity={{CallerANI}}&filter=type%3D%3D'custom%3Astore_verified'` (path from the CLI source; not run) |
| Header: Authorization | `Bearer {{CJDS_Auth_Token}}` |
| Header: Content-Type | `application/json` |
| **Output Path Expression** | `$.meta.resultCount` → maps to flow variable `VerificationCount` |
| Request Timeout | 5000ms |

> **RSQL filter values must be single-quoted** even in the URL. URL-encode the filter parameter: `type%3D%3D'custom%3Astore_verified'`. Unquoted values cause a `ParseException`.

---

## 5. Webex Connect — Native Customer Journey Data Node

In Webex Connect flows, use the **Customer Journey Data** node instead of HTTP Request for CJDS operations. This node handles auth, request formatting, and response parsing for you.

**Prerequisites:**
- Configure authorization under **Assets > Integrations > Pre-built Integrations** — select your CJDS workspace. Auth must be configured before using the node.
- Flex 3 license required

> **Early Access migration warning:** If you used the CJD node during Early Access, drag a fresh node onto the canvas and reconfigure it. The "Read from CJDS" method was introduced after EA (the earlier version was renamed to "Read from Progressive Profile"), and old EA nodes may not work correctly.

### Methods

#### Method 1: Manage Identity

Merges multiple customer aliases into a unified person profile.

| Input | Required | Description |
|---|---|---|
| Authorization | Yes | Pre-configured CJDS auth |
| Workspace/Project | Yes | Select from dropdown |
| First Name / Last Name | No | Profile fields |
| Phone Numbers | No | Comma-separated, E.164. Format: `$(phone1),$(phone2)` |
| Email Addresses | No | Comma-separated |
| Customer IDs | No | Internal IDs, comma-separated |
| Social IDs | No | Social handles, comma-separated |
| Temporary IDs | No | Session/chat IDs, comma-separated |
| Overwrite | No | Boolean (default false) — replaces previous aliases if true |

**Output variables:**

| Variable | Description |
|---|---|
| `firstName` | Alias first name |
| `lastName` | Alias last name |
| `aliases` | Array of all identities |
| `phone` | Array of phone numbers |
| `email` | Array of email addresses |
| `customerId` | Array of customer IDs |
| `temporaryId` | Array of temporary IDs |
| `socialId` | Array of social IDs |
| `id` | Alias ID |
| `organizationId` | Organization identifier |
| `responsePayload` | Complete JSON response |

**Success outcome:** `onCreateMergeAliasesSuccess` (HTTP 202)
**Failure outcome:** `onCreateMergeAliasesFailure` (non-202)

#### Method 2: Write to CJDS

Records an event against a customer identity.

| Input | Required | Description |
|---|---|---|
| Authorization | Yes | Pre-configured CJDS auth |
| Workspace/Project | Yes | Select from dropdown |
| Event ID | Yes | Unique string (UUID format) |
| Event Spec Version | Yes | `"1.0"` |
| Event Type | Yes | Reverse-DNS string (e.g., `task:new`, `appointment:booked`) |
| Event Source | Yes | Origin URI (e.g., `/com/cisco/wxcc/123`) |
| Event Time | Yes | UTC, ISO 8601 (e.g., `2022-08-15T22:29:43.768Z`) |
| Identity Type | Yes | `email`, `phone`, `customerId`, `socialId`, `temporaryId` |
| Identity | Yes | Alias value |
| Data Object | Yes | Multi-select: Agent Id, Destination, Profile Type, Current State, Idle Code ID, Created Time |

**Success outcome:** `onEventPostSuccess` (HTTP 202)
**Failure outcome:** `onEventPostFailure` (non-202)

#### Method 3: Get Identity by Aliases

Retrieves all linked identities for a given alias.

| Input | Required | Description |
|---|---|---|
| Authorization | Yes | Pre-configured CJDS auth |
| Workspace/Project | Yes | Select from dropdown |
| Alias IDs | Yes | Comma-separated alias values (e.g., `user@example.com,2771154`) |

**Output variables:**

| Variable | Description |
|---|---|
| `data` | Array with profile template ID, names, aliases, org/workspace IDs |
| `id` | Person ID |
| `firstName` | Person's first name |
| `lastName` | Person's last name |
| `organizationId` | Organization identifier |
| `responsePayload` | Complete JSON response |

**Success outcome:** `onGetIdentityByAliasesSuccess` (HTTP 200)
**Failure outcome:** `onGetIdentityByAliasesFailure` (non-200)

#### Method 4: Read from Progressive Profile

Fetches aggregated journey metrics from a named profile template.

| Input | Required | Description |
|---|---|---|
| Authorization | Yes | Pre-configured CJDS auth |
| Workspace/Project | Yes | Select from dropdown |
| Template Name | Yes | Valid template name from Control Hub |
| Alias ID | Yes | Phone, email, social ID, customer ID, or temporary ID |

**Output variables:** `data` array with profile template ID, names, aliases, org/workspace IDs, aggregated attributes

**Success outcome:** `onGetIdentityByAliasesSuccess` (HTTP 200)
**Failure outcome:** `onGetIdentityByAliasesFailure` (non-200)

> Note: Progressive Profile uses the same success/failure outcome names as Get Identity by Aliases.

#### Method 5: Read from CJDS

Retrieves recent events for a customer, with optional filter.

| Input | Required | Description |
|---|---|---|
| Authorization | Yes | Pre-configured CJDS auth |
| Workspace/Project | Yes | Select from dropdown |
| Identity | Yes | Alias value (phone, email, etc.) |
| Query | No | Filter string, e.g., `filter=type=='agent:state_change'&data=queueId=='8003ddb7-...'&pageSize=1` |

**Output variables:**

| Variable | Description |
|---|---|
| `dataArray` | Array of events with workspace/template/org IDs and attributes |
| `resultCount` | Total events returned |
| `Identity` | Person ID |
| `workspaceId` | Workspace identifier |
| `responsePayload` | Complete JSON response |

**Success outcome:** `onReadfromCJDSSuccess` (HTTP 200)
**Failure outcome:** `onReadfromCJDSFailure` (non-200)

### Outcome Branches

Every method shares these **error** outcomes in addition to its method-specific success/failure:

| Outcome | HTTP Status | When |
|---|---|---|
| `onBadRequest` | 400 | Malformed request |
| `onForbidden` | 403 | Auth token lacks required scope |
| `onNotFound` | 404 | Identity or resource not found |
| `onTooManyRequest` | 429 | Rate limit exceeded |
| `onInternalServerError` | 500 | CJDS service error |
| `onTimeout` | — | 10-second timeout exceeded |
| `onInvalidData` | — | Invalid data provided |
| `onError` | — | Invocation error |
| `onInvalidChoice` | — | Invalid method selection |

**Method-specific success outcomes:**

| Method | Success (HTTP) | Failure |
|---|---|---|
| Manage Identity | `onCreateMergeAliasesSuccess` (202) | `onCreateMergeAliasesFailure` |
| Write to CJDS | `onEventPostSuccess` (202) | `onEventPostFailure` |
| Get Identity by Aliases | `onGetIdentityByAliasesSuccess` (200) | `onGetIdentityByAliasesFailure` |
| Read from Progressive Profile | `onGetIdentityByAliasesSuccess` (200) | `onGetIdentityByAliasesFailure` |
| Read from CJDS | `onReadfromCJDSSuccess` (200) | `onReadfromCJDSFailure` |

> Wire `onNotFound` to your "new customer" path and all error branches to a safe fallback.

**All error outcomes also expose:** `status` (HTTP error name), `message` (error type description), `errors` (array of error messages), `trackingId` (unique error tracking ID).

### When to Use Each Method in a Flow

| Use Case | Method |
|---|---|
| New caller — create profile | Manage Identity |
| Record a completed interaction | Write to CJDS |
| Identify returning caller by phone | Get Identity by Aliases |
| Detect repeat caller (count-based) | Read from Progressive Profile |
| Check last event type for this customer | Read from CJDS (with filter) |

---

## 6. Failure Handling

When CJDS is unavailable, your flow must still route the call.

**Recommendation: fail safe to the IVR / default path.**

| CJDS Response | Treat as | Route |
|---|---|---|
| HTTP 200 | Known caller | Fast path |
| HTTP 404 | Unknown caller | IVR / default path |
| HTTP 500 / timeout / 401 | Unknown (safe default) | IVR / default path |

**Why this default:** If CJDS is down and you fail open (skip IVR for everyone), you've eliminated your spam filter. Legitimate returning callers pressing 1 is a minor inconvenience. Spam bots reaching live agents is not.

**How to wire it:** Connect the HTTP Request **error** output path (or the Webex Connect node `onTimeout`/`onInternalServerError` branches) to the same default path as the 404 — any CJDS failure drops into the safe path automatically.

---

## 7. Identity Management — Bulk Provisioning

To pre-populate CJDS with existing customer identities before go-live:

### CSV Upload (Control Hub)

1. Control Hub > Contact Center > Customer Journey Data > Identities > Import
2. CSV format:

| Column | Notes |
|---|---|
| Id | Leave empty — auto-generated |
| First Name | Optional |
| Last Name | Optional |
| Email Addresses | Up to 5, pipe-separated (`email1|email2`) |
| Phone Numbers | Up to 5, pipe-separated, E.164 format |
| Customer IDs | Up to 5, pipe-separated |

### API — Batch Event Writing

Use `POST https://api.wxcc-{region}.cisco.com/publish/v1/api/event?workspaceId={id}` in a loop to write one event per historical record. Generates the person profile automatically on first write.

---

## 8. Customer Journey Widget (Agent Desktop)

To show CJDS journey data to agents on the Agent Desktop, add the Customer Journey Widget to the desktop layout.

### Desktop Layout Configuration

1. Control Hub > Contact Center > Desktop Layouts
2. Create or edit a layout, assign to the agent team
3. Upload or edit the layout JSON to include this widget block:

```json
{
  "comp": "customer-journey-widget",
  "script": "https://journey-widget.webex.com",
  "attributes": {
    "show-alias-icon": "true",
    "condensed-view": "true"
  },
  "properties": {
    "interactionData": "$STORE.agentContact.taskSelected",
    "bearerToken": "$STORE.auth.accessToken",
    "organizationId": "$STORE.agent.orgId",
    "dataCenter": "$STORE.app.datacenter"
  }
}
```

4. Save the layout

The widget automatically displays the caller's journey timeline, linked aliases, and progressive profile data when an agent accepts a contact.

### Cross-Channel Escalation: Chat Transcript → Voice Agent

When a digital AI agent escalates to a voice callback, the human agent picking up the voice call has no native visibility into the prior chat. CJDS bridges this gap: write the chat transcript as a journey event during escalation, and the Customer Journey Widget surfaces it when the voice agent accepts the call.

**Write side (Webex Connect digital flow, on `onAgentHandover`):**

1. **Fetch Conversation Transcript** — Use the Update Conversation node (method: `Fetch transcript`) with `$(conversationId)` to retrieve the full message history. See `docs/reference/digital-inbound.md` § 4b.
2. **Write to CJDS** — Store the transcript as a journey event keyed to the customer's phone number:

```json
{
  "id": "$(flid)",
  "specversion": "1.0",
  "type": "chat:transcript",
  "source": "ai_agent",
  "identity": "<customer phone number>",
  "identitytype": "phone",
  "datacontenttype": "application/json",
  "data": {
    "messages": $(nX.transcriptJsonEsc),
    "channel": "whatsapp",
    "agentName": "Property Management Bot",
    "escalationReason": "customer requested human agent",
    "messageCount": "$(nX.countOfRecords)"
  }
}
```

> **Event type is freeform.** Use `chat:transcript` or any consistent namespace. The Customer Journey Widget displays all events — filter by type if needed.

**Read side (voice agent picks up call):**

No flow-side work required. The Customer Journey Widget auto-loads events by the caller's phone number (ANI). The `chat:transcript` event appears in the agent's timeline with the full message content in the `data` payload.

> **Payload size:** CJDS event `data` is freeform JSON. Short conversations fit easily. For very long transcripts, consider writing a summary to CJDS and storing the full transcript in your DB with a link in the event data.

For the full step-by-step flow (including outbound call triggering and prerequisites), see `docs/playbooks/cross-channel-escalation.md`.

---

## Quick Reference

| Question | Answer |
|---|---|
| Where is my workspaceId? | Control Hub > Contact Center > Customer Journey Data |
| What is my CJDS base URL? | `api.wxcc-{region}.cisco.com` for reads and writes (verified 2026-10-19, us1; the former read domain `api-jds.prod-{region}.ciscowxdap.com` returned NXDOMAIN that day). Confirm region in Control Hub > Settings > General |
| How do I check if a caller is known? | `GET /admin/v1/api/person/workspace-id/{id}/aliases/{phone}` — 200 = known, 404 = unknown |
| Output Path Expression for personId | `$.data[0].id` |
| How do I get a repeat caller count? | `GET /v1/api/progressive-profile-view/...` with a profile template |
| How do I write an event? | `POST https://api.wxcc-{region}.cisco.com/publish/v1/api/event?workspaceId={id}` (the same host as the reads, verified 2026-10-19; this row used to say "write domain differs from read domain") |
| What OAuth scopes do I need? | `cjds:admin_org_read cjds:admin_org_write` |
| What identity types are supported? | Event schema: `email`, `phone`, `customerId`. Connect node also accepts: `socialId`, `temporaryId` |
| What if CJDS is unavailable? | Route to IVR / default path (treat as unknown) |
| How long does the token last? | Personal access token 12 hours; Service App / integration access token 14 days, then refresh; refresh token 90 days [`authentication.md` § Authentication Methods Overview, § Token Lifetimes] — automate refresh |
| Webex Connect native node available? | Yes — "Customer Journey Data" node, Flex 3 only |
| Where is the Connect node? | Assets > Integrations > Pre-built Integrations |
| Post Nov 2025 provisioning? | Fill out provisioning form — 72-hour setup |
| Write methods succeed on what HTTP code? | 202 (Accepted). Read methods on 200. |
| Profile Template admin API? | `GET /admin/v1/api/profile-view-template/workspace-id/{id}/template-id/{id}` |
| How do I query historic events? | `GET /v1/api/events/workspace-id/{id}?identity={alias}&filter=type=='...'` |
| RSQL filter syntax? | Values must be single-quoted: `type=='custom:verified'`. Unquoted values throw `ParseException`. |
| Phone number format in CJDS? | May be stored as 10 digits without `+` prefix. Alias lookup ignores a leading `+` but does not match 10-digit against `1…`/`+1…` (verified 2026-10-19; said "normalizes" before); RSQL filters require exact match. |
| Agent Desktop widget? | `customer-journey-widget` component, script at `journey-widget.webex.com` |
