# Customer Journey Data Service (CJDS) — Platform Reference

<!-- ref-tag: cjds-v1 -->

The single owner for CJDS **values**: endpoints, domains, OAuth scopes, the event
schema, identity types, node outcome branches, HTTP codes, path expressions and
RSQL syntax.

CJDS spans three surfaces — a REST API, a native **Webex Connect** node, and a
**WxCC Flow Designer** HTTP Request pattern. This file owns the facts for all
three. For build sequence, prerequisites and which-UI-next, see
`docs/playbooks/cjds-integration.md`.

**Availability:** the native Connect node is **Flex 3 only**.

---

## Workspace ID and Regional Domains

Every CJDS API call requires a **workspaceId** (also called Project ID) — this is
**not** your org ID. Found at Control Hub → Contact Center → Customer Journey
Data.

**Reads and writes use one host: the regional gateway `https://api.wxcc-{region}.cisco.com`**
[owner: `contact-center-journey.md`, intro]. Verified live 2026-10-19 (us1): the workspace
list, the person list and an alias lookup answered on `https://api.wxcc-us1.cisco.com`
(`wxcli cc-journey list`, `show`, `show-aliases`). Only `us1` was tested.

| Operation | Host |
|---|---|
| **Reads** — alias lookup, progressive profile, event queries | `https://api.wxcc-{region}.cisco.com` (alias lookup and admin reads verified 2026-10-19; progressive profile and event queries not run on it) |
| **Writes** — event publishing | `https://api.wxcc-{region}.cisco.com` |

**History — the separate read hosts do not resolve.** Before 2026-10-19 this section
said "⚠ Read and write use different domains. This is the single most common
integration error", and gave reads the host below. On 2026-10-19 every one of these
names, and the domain `ciscowxdap.com` itself, returned NXDOMAIN in DNS (the gateway
resolved on the same resolver), and a GET to the US East 1 host failed before any
HTTP status (`nodename nor servname provided`):

| Data Center | Former CJDS read base URL (NXDOMAIN 2026-10-19) |
|---|---|
| US East 1 | `https://api-jds.prod-useast1.ciscowxdap.com` |
| US East 2 | `https://api-jds.prod-useast2.ciscowxdap.com` |
| EU / Frankfurt | `https://api-jds.prod-eu.ciscowxdap.com` |
| APJC | `https://api-jds.prod-apjc.ciscowxdap.com` |
| Other regions | Pattern `https://api-jds.prod-{region}.ciscowxdap.com` |

Region is shown at Control Hub → Contact Center → Settings → General.

### Write-domain region slugs

The region slug is the gateway's (`us1`, `eu1`, …), not the former read hosts'
(`useast1`, `eu`, …). Before 2026-10-19 this section warned that the write-domain slug
"may differ from the read-domain one"; with one host for both, there is one slug.

| Region | CJDS write base URL |
|---|---|
| US | `https://api.wxcc-us1.cisco.com` |
| EU | `https://api.wxcc-eu1.cisco.com` — *may*; unconfirmed |
| Other regions | Needs confirmation from your Cisco partner |

⚠ **`cjaas.cisco.com` is deprecated.** That was the original CJDS domain. The current
host is `api.wxcc-{region}.cisco.com` for reads and writes (verified 2026-10-19; the
`ciscowxdap.com` read domain this line used to name returned NXDOMAIN that day).

⚠ **Deprecated endpoints.** Older documentation references
`/v1/api/journey-events` and `/v1/api/journey-event-posting` on the
`ciscowxdap.com` domain. The confirmed working write endpoint is
`/publish/v1/api/event` on the `wxcc-{region}.cisco.com` domain.

---

## Authentication

Bearer token on all API calls.

| Scope | Grants |
|---|---|
| `cjds:admin_org_read` | Read journey data and person profiles |
| `cjds:admin_org_write` | Write events and manage identities |

**Alternate scopes:** some documentation references `cjp:config_read` and
`cjp:config_write`. Both scope sets are accepted; use `cjds:admin_org_*` for new
integrations.

> **Unverified (2026-10-19):** [contact-center-journey.md](contact-center-journey.md)
> gotcha 2 says the opposite — that `cjp:config_*` does **not** grant the JDS admin APIs.
> Neither claim has a live test behind it. A full-admin personal access token carries
> both sets, so it cannot tell them apart, and Cisco's JDS API reference on
> developer.webex.com could not be fetched that day. What would settle it: the same
> admin read with a token holding only `cjp:config_*`, then one holding only
> `cjds:admin_org_*` [owner: `contact-center-journey.md` § 9 Gotchas, gotcha 2].

**Token lifespan:** a personal access token lasts 12 hours; a Service App or
integration access token lasts 14 days, then refresh; the refresh token lasts
90 days [`authentication.md` § Authentication Methods Overview, § Token Lifetimes]. Plan automated refresh — see
`docs/playbooks/webex-api-auth.md` for the refresh subflow pattern. (This line
said "8–12 hours" before 2026-10-19; corrected to the owner's values.)

---

## Data Model

### Identity Types

| Identity Type | Example | Accepted by |
|---|---|---|
| `phone` | `+15551234567` (E.164) | Event schema + Connect node |
| `email` | `customer@example.com` | Event schema + Connect node |
| `customerId` | Internal CRM ID | Event schema + Connect node |
| `socialId` | Social media handle | **Connect node only** |
| `temporaryId` | Session or chat ID (transient) | **Connect node only** |

A **Person** is a unified profile identified by one or more **aliases** — the
contact methods that link events to that person.

⚠ **Phone numbers may be stored as 10 digits without the `+` prefix.** Alias
lookup does **not** bridge that: verified live 2026-10-19, a 10-digit number and its
`1…` / `+1…` form do not find each other in either direction, while `1…` and `+1…`
find the same person (a leading `+` is ignored) [owner: `contact-center-journey.md`
§ 9 Gotchas, gotcha 5]. Look up both the E.164 form and the 10-digit form if your
data may hold either. **RSQL filters require an exact match** too. A filter or lookup
that works against one storage form silently returns nothing against the other.
(Before 2026-10-19 this note said "Alias lookup normalizes the format".)

### Event Schema (CloudEvents v1.0)

All CJDS events follow the [CloudEvents specification](https://cloudevents.io/).

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

---

## REST Endpoints

| Purpose | Method + Path | Success |
|---|---|---|
| Check whether a caller is known | `GET /admin/v1/api/person/workspace-id/{workspaceId}/aliases/{phoneNumber}` | 200 = known, **404 = unknown** |
| Get a profile-view template | `GET /admin/v1/api/profile-view-template/workspace-id/{workspaceId}/template-id/{templateId}` | 200 |
| Read progressive profile | `GET /v1/api/progressive-profile-view/workspace-id/{workspaceId}/person-id/{personId}/template-id/{templateId}` | 200 |
| Query historic events | `GET /v1/api/events/workspace-id/{workspaceId}?identity={alias}&filter={rsql}` | 200 |
| Write an event | `POST https://api.wxcc-{region}.cisco.com/publish/v1/api/event?workspaceId={workspaceId}` | **202 (Accepted)** |

**Reads succeed on 200; writes succeed on 202.** A write that returns 200 has not
done what you think.

### Output Path Expressions

| Value | Expression |
|---|---|
| `personId` from an alias lookup | `$.data[0].id` |

### RSQL Filter Syntax

Values **must be single-quoted**: `type=='custom:verified'`. Unquoted values
throw a `ParseException`.

---

## Webex Connect — Customer Journey Data Node

A native node (not an HTTP call). Authorization is configured at
**Assets > Integrations > Pre-built Integrations** before use.

### Method Success / Failure Outcomes

| Method | Success (HTTP) | Failure |
|---|---|---|
| Manage Identity | `onCreateMergeAliasesSuccess` (202) | `onCreateMergeAliasesFailure` |
| Write to CJDS | `onEventPostSuccess` (202) | `onEventPostFailure` |
| Get Identity by Aliases | `onGetIdentityByAliasesSuccess` (200) | `onGetIdentityByAliasesFailure` |
| Read from Progressive Profile | `onGetIdentityByAliasesSuccess` (200) | `onGetIdentityByAliasesFailure` |
| Read from CJDS | `onReadfromCJDSSuccess` (200) | `onReadfromCJDSFailure` |

⚠ **Read from Progressive Profile shares Get Identity by Aliases' outcome
names** — they are not distinct ports. Do not assume a one-to-one mapping between
method and outcome name.

### Shared Error Outcomes

Every method carries these in addition to its method-specific pair:

| Outcome | HTTP Status | When |
|---|---|---|
| `onBadRequest` | 400 | Malformed request |
| `onForbidden` | 403 | Auth token lacks required scope |
| `onNotFound` | 404 | Identity or resource not found |
| `onTooManyRequest` | 429 | Rate limit exceeded |
| `onInternalServerError` | 500 | CJDS service error |
| `onTimeout` | — | **10-second** timeout exceeded |
| `onInvalidData` | — | Invalid data provided |
| `onError` | — | Invocation error |
| `onInvalidChoice` | — | Invalid method selection |

**All error outcomes also expose:** `status` (HTTP error name), `message` (error
type description), `errors` (array of error messages), `trackingId` (unique error
tracking ID).

⚠ `onNotFound` is **not** an error in the usual sense — 404 is the documented
"unknown customer" signal. Wire it to the new-customer path, not to the error
fallback.

---

## Tenant Limits and Constraints

| Constraint | Value |
|---|---|
| Data retention — minimum | 180 days |
| Data retention — default | 365 days |
| Active journey projects | **One at a time** |
| Connect node timeout | 10 seconds |
| Provisioning lead time (orgs created after 2026-11-01) | Up to 72 hours, via provisioning form |

**Partner admin visibility:** the Customer Journey Data tab in Control Hub is
visible only to full customer admins, **not** partner admins.

---

## Agent Desktop Widget

| Item | Value |
|---|---|
| Component | `customer-journey-widget` |
| Script host | `journey-widget.webex.com` |

---

## References

- Build procedure, worked examples, failure handling: `docs/playbooks/cjds-integration.md`
- Cross-channel chat → voice escalation: `docs/playbooks/cross-channel-escalation.md`
- Service App / token refresh: `docs/playbooks/webex-api-auth.md`
- Connect node in flow context: `flow-designer-patterns.md` § Customer Journey Data (JDS) Node
- Contact Resolver subflow (community): https://github.com/TeamCCEP/JDSContactResolver

## See Also

- [flow-designer-patterns.md](flow-designer-patterns.md) — where the Customer Journey Data node is wired into a flow
- [cjds-integration.md](../playbooks/cjds-integration.md) — the integration steps that pair with this reference
- [webex-api-auth.md](../playbooks/webex-api-auth.md) — the Service App token setup that the CJDS write API needs
