# Webex API Feedback — For Cisco Collaboration BU

**Prepared by:** Adam Hobgood
**Date:** May 2026
**Source:** 9 months of building production automation tooling against the Webex API surface — 173 CLI command groups generated from 9 OpenAPI specs, 48 reference docs, 250+ documented gotchas, and thousands of live API calls across calling, admin, device, messaging, meetings, and contact center domains.

---

## Executive Summary

The Webex APIs are functionally broad — most things an admin needs to do can be done programmatically. The individual endpoints mostly work. The pain is in the **seams between them**: inconsistent auth models, hidden data, unpredictable response shapes, misleading status codes, no dependency graph, no bulk path, and async operations with no tracking. Every integrator ends up building the same workaround layer independently.

This document catalogs **34 distinct issues** organized into 8 categories, with evidence, impact, and suggested fixes. These aren't feature requests — they're consistency and completeness gaps that affect every team building automation against this platform.

---

## How to Read This Document

Each issue includes:

- **What happens** — the observable behavior
- **Evidence** — specific endpoints, error codes, or test results
- **Impact** — who this affects and how
- **Suggested fix** — what would resolve it

Severity indicators:

- **[CRITICAL]** — Blocks a common workflow entirely; no workaround or workaround is fragile
- **[HIGH]** — Causes significant rework or confusion; workaround exists but is expensive
- **[MEDIUM]** — Causes friction; workaround is straightforward but shouldn't be necessary

---

## Category 1: Authentication & Authorization Gaps

### 1. [CRITICAL] 19 person call settings have no admin endpoint

**What happens:** Settings including `simultaneousRing`, `sequentialRing`, `priorityAlert`, `callNotify`, `anonymousCallReject`, `callBlock`, `callCaptions`, `preferredAnswerEndpoint`, `guestCalling`, and `modeManagement` only exist at `/telephony/config/people/me/settings/{feature}`. Admin tokens get 404. There is no `/telephony/config/people/{personId}/` equivalent.

**Evidence:** Confirmed across all 19 endpoints. Admin tokens (PAT, service app, OAuth with `spark-admin:*` scopes) all return 404. Only user-level OAuth with `spark:people_*` scopes works.

**Impact:** A partner or admin managing hundreds of users cannot programmatically configure these settings. Each user requires their own OAuth token. At scale, this forces admins back to Control Hub click-ops for settings that are trivially scriptable for every other call setting.

**Suggested fix:** Add admin-path equivalents (`/telephony/config/people/{personId}/settings/{feature}`) for all 19 endpoints. Every other person call setting has both paths.

---

### 2. [CRITICAL] Personal Access Tokens don't carry Contact Center scopes

**What happens:** A full org admin on a Contact Center-licensed org gets 403 on every `cc-*` endpoint when using a Personal Access Token. The only path is to create a dedicated OAuth integration with `cjp:config_read`/`cjp:config_write` explicitly selected and run a separate auth flow.

**Evidence:** Tested with full admin PATs on CC-licensed orgs. All CC API calls return 403. Confirmed that a separate OAuth integration with explicit `cjp:config_*` scopes resolves it.

**Impact:** This is the only API domain in the entire Webex platform where "full admin" doesn't actually mean full admin. It creates a two-tier auth experience that confuses every admin who encounters it. The error message (generic 403) doesn't explain the scope requirement.

**Suggested fix:** If the org has CC and the user is a full admin, the PAT should carry `cjp:config_read` at minimum. Alternatively, surface the scope requirement in the 403 error body.

---

### 3. [HIGH] Reports API requires Pro Pack license — error doesn't say so

**What happens:** The Reports API (templates, scheduled reports) requires a Pro Pack license add-on. The CDR Feed API does not. When you lack Pro Pack, you get a generic 403 with no indication that licensing is the issue.

**Evidence:** 403 on Reports API calls with valid admin tokens on non-Pro-Pack orgs. CDR Feed (`/v1/analytics/cdr_feed`) works fine with the same token.

**Impact:** Admins spend time debugging auth/scope issues when the real problem is licensing. The debugging path is completely wrong — you check tokens, scopes, and roles before eventually discovering a product-tier dependency that isn't documented in the API response.

**Suggested fix:** Return a 403 with a body that includes `"reason": "Pro Pack license required"` or similar. Document the licensing requirement in the OpenAPI spec description for affected endpoints.

---

## Category 2: Data Shape & Response Inconsistency

### 4. [HIGH] Response list keys are unpredictable

**What happens:** There is no convention for the key name in paginated list responses. You cannot predict the key from the endpoint URL, resource type, or any other pattern.

**Evidence (sampling across domains):**

| Endpoint | Expected Key | Actual Key |
|----------|-------------|------------|
| `/telephony/config/numbers` | `numbers` | `phoneNumbers` |
| `/workspaces` | `workspaces` | `items` |
| `/telephony/config/jobs/numbers/manageNumbers` | `manageNumbers` | `items` |
| `/telephony/config/paging` | `paging` | `locationPaging` |
| `/telephony/config/outgoingPermission` | `outgoingPermission` | `callingPermissions` |
| `/telephony/config/supportedDevices` | `supportedDevices` | `devices` |
| `/telephony/config/devices/availableMembers` | `availableMembers` | `members` |
| `/telephony/config/autoAttendants/availableNumbers` | `availableNumbers` | `phoneNumbers` |
| CC v2 list endpoints | `items` | `data` |

**Impact:** Every list endpoint requires trial-and-error to find the correct response key. Automated code generation, SDK development, and integration testing all require per-endpoint special-casing. We maintain a 60+ entry override table just for response keys.

**Suggested fix:** Standardize on one convention. The simplest: all list endpoints return `{"items": [...]}`. If backward-compatibility prevents that, document the response key in every list endpoint's OpenAPI response schema.

---

### 5. [HIGH] Member/agent format differs across features

**What happens:** The same concept — "a list of members/agents" — uses three different JSON shapes depending on the feature.

**Evidence:**

| Feature | Create Format | Example |
|---------|--------------|---------|
| Hunt Group, Call Queue | Array of objects | `[{"id": "person_id"}]` |
| Call Pickup, Paging Group | Array of plain strings | `["person_id"]` |
| Dial Plan (create) | Array of plain strings | `["+1!"]` |
| Dial Plan (modify) | Array of action objects | `[{"dialPattern": "+1!", "action": "ADD"}]` |

**Impact:** Every integrator discovers this through 400 errors. Using `[{"id": ...}]` format for pickup/paging produces `400 "Invalid field value: agents/targets"`. The dial plan create-vs-modify difference is particularly surprising.

**Suggested fix:** Standardize member arrays to `[{"id": "..."}]` across all features. For dial plan patterns, use the same shape for create and modify.

---

### 6. [MEDIUM] Notification type serialization asymmetry

**What happens:** The `notification_type` field in person voicemail settings returns the string `"None"` on GET but requires JSON `null` on PUT.

**Evidence:** GET response contains `"notificationType": "None"`. Sending that value back on PUT fails. Must send `"notificationType": null`.

**Impact:** Breaks any naive read-modify-write pattern. The API returns a value that it won't accept back.

**Suggested fix:** Accept both `"None"` (string) and `null` on write, or return `null` on read. The API should accept any value it produces.

---

### 7. [MEDIUM] Language codes must be lowercase — not documented, no helpful error

**What happens:** The `announcementLanguage` field rejects standard locale codes like `en_US` and requires the non-standard lowercase form `en_us`.

**Evidence:** `PUT /telephony/config/locations/{id}` with `"announcementLanguage": "en_US"` returns 400. `"en_us"` succeeds.

**Impact:** Standard locale libraries produce `en_US`. Every integrator has to add a `.lower()` call and discover this through failed requests. The error message doesn't indicate the casing requirement.

**Suggested fix:** Accept both `en_US` and `en_us`. If case-sensitive, document the requirement in the field description and include the expected format in the error message.

---

### 8. [MEDIUM] `announcementLanguage` returns `None` on read even when set

**What happens:** After successfully setting `announcementLanguage` via PUT, the subsequent GET response returns `null` for this field.

**Evidence:** Confirmed on `GET /telephony/config/locations/{id}` after setting `announcementLanguage` to `en_us`. The field reads back as `null`.

**Impact:** Breaks any audit or configuration-drift detection that relies on reading current state. You can't verify that a language was set correctly because the API won't tell you what it's currently set to.

**Suggested fix:** Return the actual configured value on GET.

---

## Category 3: Path & Naming Inconsistency

### 9. [HIGH] Two parallel path families for person call settings

**What happens:** Person settings are split across two URL path patterns with different command naming:

- Classic: `/people/{id}/features/{setting}` — e.g., `callForwarding`, `callWaiting`, `doNotDisturb`
- Newer: `/telephony/config/people/{id}/{setting}` — e.g., `singleNumberReach`, `selectiveAccept`, `musicOnHold`

Some settings exist in both path families with different names.

**Evidence:** Documented in `person-call-settings-behavior.md` lines 36-54 with the full mapping table. At least 6 settings have overlapping paths.

**Impact:** Integrators must know which path family each setting belongs to. Getting it wrong returns 404, and the error doesn't suggest the correct path. SDK wrappers must maintain a per-setting path mapping.

**Suggested fix:** Consolidate to one path family. If both must coexist, cross-reference them in error responses: "This setting is available at /telephony/config/people/{id}/singleNumberReach."

---

### 10. [HIGH] Device API has two surfaces with different ID encodings

**What happens:** `/v1/devices` and `/v1/telephony/config/devices` are parallel APIs for the same physical devices. They use different ID encodings. Tags use `application/json-patch+json` content type (unique across the entire API surface). Settings endpoints require a `deviceModel` query parameter.

**Evidence:** A device created via `/v1/devices` has a different ID format than the same device returned by `/v1/telephony/config/devices`. The tags PATCH endpoint is the only one across all Webex APIs that uses JSON Patch content type.

**Impact:** Building a complete device management workflow requires using both API surfaces and translating between ID formats. The JSON Patch content type is an additional surprise that breaks generic API clients.

**Suggested fix:** Unify the device API surfaces or provide a documented ID translation mechanism. Standardize the content type to `application/json`.

---

### 11. [HIGH] Contact Center is a separate API universe

**What happens:** CC APIs differ from the rest of Webex in every dimension:

| Dimension | Webex APIs | CC APIs |
|-----------|-----------|---------|
| Base URL | `webexapis.com` | `api.wxcc-{region}.cisco.com` |
| Scopes | `spark-admin:*` | `cjp:config_*` |
| Org ID format | Base64 Spark ID | Bare UUID |
| Response key | `items` | `data` |
| JDS scopes | N/A | `cjds:*` (separate again) |
| Path families | 1-2 | 5+ within CC alone |

**Evidence:** Cataloged across `contact-center-core.md`, `contact-center-routing.md`, `contact-center-analytics.md`, `contact-center-journey.md`. JDS adds 3 additional path families and its own scope set.

**Impact:** An integrator who has learned the Webex API conventions has to unlearn all of them for CC. The org ID translation (base64 decode + extract UUID) is particularly error-prone.

**Suggested fix:** If full consolidation isn't feasible, publish a Webex-to-CC translation guide as a first-class resource. At minimum, accept both ID formats on CC endpoints.

---

### 12. [MEDIUM] Three audit/event APIs with overlapping names

**What happens:** `audit-events`, `security-audit`, and `events` are three separate APIs with different scopes, different data, and different pagination patterns. They sound interchangeable but aren't.

**Evidence:** Each requires different scopes (`spark-admin:events_read` vs `spark-compliance:events_read` vs `audit:events_read`). They return different event types with different schemas.

**Impact:** An admin looking for "what happened in my org" has to know which of three APIs to query. The naming gives no indication of which to choose.

**Suggested fix:** Publish a decision tree or consolidate into a unified event query endpoint with filters for event category.

---

### 13. [MEDIUM] Meeting API endpoint naming collisions

**What happens:** Generic operation names (`create`, `list`, `show`) map to semantically different operations than expected:

- Meeting `create` for participants is actually "Query by Email" (a POST search)
- Video Mesh `list` maps to "client type distribution" (not a resource list)
- `live-monitoring create` is semantically a read operation (POST query)

**Evidence:** Documented in `meetings-infrastructure.md` and `admin-hybrid.md`. The POST-as-search pattern appears in at least 4 endpoint groups.

**Impact:** `operationId` values in the spec actively mislead — the opposite of their purpose. Code generators produce function names that don't match the operation's semantics.

**Suggested fix:** Use descriptive `operationId` values: `queryParticipantsByEmail`, `getClientTypeDistribution`, `queryLiveMonitoring`. Reserve `create` for operations that create resources.

---

### 14. [MEDIUM] Virtual extension/line ID type mismatch

**What happens:** Virtual extensions use `VIRTUAL_EXTENSION`-encoded IDs in their endpoint paths, but virtual lines (conceptually the same objects) use `VIRTUAL_LINE`-encoded IDs. The numbers API returns `VIRTUAL_LINE` IDs. Using a `VIRTUAL_LINE` ID against a `virtualExtensions/` endpoint returns 400.

**Evidence:** `wxcli virtual-extensions delete` consistently fails because the CLI obtains IDs from the numbers API (`VIRTUAL_LINE` encoding) and passes them to the `virtualExtensions/` endpoint.

**Impact:** Any automation that discovers virtual lines via the numbers API and then tries to manage them via the virtual extensions API fails. We use raw REST as a workaround.

**Suggested fix:** Accept both ID encodings on both endpoint families, or consolidate to one path family.

---

## Category 4: Silent Failures & Misleading Responses

### 15. [CRITICAL] Supervisor delete returns 204 but supervisor persists

**What happens:** `DELETE /telephony/config/supervisors/{id}` returns HTTP 204 (No Content) — the standard success response for deletions. The supervisor is not actually deleted.

**Evidence:** Confirmed repeatedly. Workaround: use `PUT /telephony/config/supervisors/{id}` with `{"supervisors": [{"id": "...", "action": "DELETE"}]}` on each agent instead.

**Impact:** A 204 is a contract that the deletion succeeded. Any automation that deletes a supervisor and proceeds based on the 204 will have data integrity issues. This is not a "gotcha" — it's a bug that violates HTTP semantics.

**Suggested fix:** Either make the DELETE endpoint actually delete, or return a 4xx/5xx indicating the operation isn't supported via DELETE.

---

### 16. [HIGH] CX Essentials queues hidden in default call queue list

**What happens:** `GET /telephony/config/queues` silently omits all Customer Assist (CX Essentials) queues unless `hasCxEssentials=true` is passed as a query parameter.

**Evidence:** An org with 5 standard queues and 3 CX queues returns only 5 results without the flag. All 8 appear with `hasCxEssentials=true`.

**Impact:** An admin listing "all my queues" doesn't see all their queues. Any audit, migration, or inventory tool that doesn't know about this flag will silently miss CX resources.

**Suggested fix:** Default to returning all queues the caller is authorized to see. Add a `type` filter for narrowing, not for revealing.

---

### 17. [HIGH] HTTP 405 for license-gated workspace settings (should be 403)

**What happens:** Workspace `/telephony/config/` settings endpoints return HTTP 405 (Method Not Allowed) when the workspace has a Basic Calling license instead of Professional.

**Evidence:** `GET /telephony/config/workspaces/{id}/callForwarding` returns 405 for Basic-license workspaces. Same endpoint returns 200 for Professional-license workspaces.

**Impact:** 405 means "this HTTP method doesn't exist on this endpoint." The real issue is authorization/entitlement. Developers debug the wrong layer — checking if the method is correct, if the URL is right — when the answer is "upgrade the license."

**Suggested fix:** Return 403 with a body indicating `"reason": "Professional Calling license required"`. Or return the data with a `licenseType` field and let the caller handle it.

---

### 18. [HIGH] Read-only fields silently ignored on write

**What happens:** Person call settings include fields like `greetingUploaded`, `systemMaxNumberOfRings`, and `voiceMessageForwardingEnabled` that are returned on GET but silently ignored on PUT.

**Evidence:** Modifying `systemMaxNumberOfRings` in a PUT body produces a 200 response but no change. The field is read-only but not documented as such and not rejected.

**Impact:** Read-modify-write cycles include these fields naturally. When a setting "doesn't take," the developer has no signal that the field is read-only — the API said 200. Debugging requires process-of-elimination testing.

**Suggested fix:** Either reject requests containing read-only fields with a clear 400 error, or mark fields as `readOnly: true` in the OpenAPI schema.

---

### 19. [HIGH] DECT handset assignment to Standard license silently disables Webex Calling

**What happens:** Adding a DECT handset to a person with a Standard Calling license silently disables Webex Calling across all their apps. No warning, no error, no confirmation prompt.

**Evidence:** Confirmed during device provisioning testing. The API returns success, and the user's calling capability is broken.

**Impact:** This is a destructive side effect of what appears to be a routine provisioning operation. The API gives no indication that assigning a DECT handset will disable a user's calling. Discovery requires a support case or manual investigation.

**Suggested fix:** Return a 409 or 422 with `"warning": "DECT assignment on Standard license will disable Webex Calling for this user"`, or block the operation entirely.

---

### 20. [MEDIUM] `callingData=true` silently caps page size from 500 to 100

**What happens:** Adding `callingData=true` to the People API (necessary to retrieve any calling-related fields) silently reduces the maximum page size from 500 to 100. Adding `locationId` further reduces it to 50.

**Evidence:** `GET /people?max=500` returns up to 500 results. `GET /people?max=500&callingData=true` returns at most 100. No warning, no `X-Rate-Limit` header, no documentation.

**Impact:** An admin paginating through 2,000 users needs 4 requests without calling data but 20+ with it. The performance cliff is invisible until you notice truncated results or hit rate limits from the extra requests.

**Suggested fix:** Document the cap reduction in the endpoint description. Better: return a `Link` header or `nextPage` field that makes pagination explicit regardless of cap.

---

## Category 5: Missing Capabilities

### 21. [CRITICAL] No location dependency discovery endpoint

**What happens:** Deleting a location fails with 409 if any resource is assigned to it. There is no endpoint that returns what's blocking the delete. You must query 13+ resource types individually.

**Evidence:** Resources that can block location deletion include: users, workspaces, auto attendants, call queues, hunt groups, paging groups, call parks, call pickups, voicemail groups, DECT networks, virtual lines, trunks, route groups, phone numbers, and schedules. Each requires a separate API call scoped to the location.

**Impact:** Every admin or automation tool that needs to clean up a location has to independently implement the same resource discovery loop. We built a 13-layer dependency resolver to handle this.

**Suggested fix:** Add `GET /telephony/config/locations/{id}/dependencies` that returns all resources referencing the location, grouped by type with IDs.

---

### 22. [HIGH] No bulk calling settings API

**What happens:** Configuring calling settings (call forwarding, voicemail, DND, etc.) for multiple users requires individual API calls per user per setting. There is no batch or template-based endpoint.

**Evidence:** Enabling call forwarding for 200 users requires 200 sequential PUT calls, each subject to rate limiting. SCIM has bulk operations for identity. Calling has nothing equivalent.

**Impact:** The most common admin workflow — "apply this configuration to these users" — takes minutes of API calls and rate-limit management instead of one request.

**Suggested fix:** Add a batch endpoint: `POST /telephony/config/people/bulk/settings` accepting an array of `{personId, settings}` objects. Or a template-based approach: `POST /telephony/config/settingsTemplates/{id}/apply` with a list of person IDs.

---

### 23. [HIGH] `devices list` caps at 100 results with no pagination or warning

**What happens:** `GET /v1/devices` returns at most 100 devices regardless of `max` parameter. There is no `hasMore` flag, no `Link` header, no indication that results are truncated.

**Evidence:** An org with 300 devices silently receives 100. Combined with the absence of a `mac` query parameter, finding a specific device requires scoping by person or location and iterating manually.

**Impact:** Any device inventory or audit tool built on this endpoint silently misses devices. There is no way to know you're getting partial results unless you independently count via another method.

**Suggested fix:** Implement standard cursor-based pagination. Add a `mac` filter parameter. At minimum, include a `total` count in the response so callers know when results are truncated.

---

### 24. [MEDIUM] Video Mesh API is read-only — no programmatic provisioning

**What happens:** The Video Mesh API supports monitoring (clusters, nodes, health, utilization, event thresholds) but not provisioning or configuration changes. All setup requires the Control Hub UI.

**Evidence:** `GET` endpoints exist for cluster/node inventory and metrics. No `POST`/`PUT`/`DELETE` endpoints for provisioning. `event-thresholds update` exists but resets thresholds to defaults — it doesn't set custom values.

**Impact:** Organizations automating their entire Webex deployment hit a manual gap at Video Mesh. The monitoring API's existence creates an expectation that configuration is also programmable.

**Suggested fix:** Add provisioning endpoints for cluster creation, node registration, and threshold customization.

---

### 25. [MEDIUM] Call Queue show-agents requires `limit` query parameter

**What happens:** `GET /telephony/config/queues/{id}/agents` — a simple GET-by-ID to retrieve the agent list for a specific queue — requires a `limit` query parameter. Without it, the endpoint returns 400.

**Evidence:** `GET /telephony/config/queues/{queueId}/agents` → 400. `GET /telephony/config/queues/{queueId}/agents?limit=100` → 200 with agent list.

**Impact:** A GET-by-ID endpoint should not require pagination parameters to function at all. The error message doesn't indicate that `limit` is the missing parameter.

**Suggested fix:** Default `limit` to a reasonable value (100 or the total agent count) when not provided.

---

## Category 6: Async Operations & State Management

### 26. [HIGH] No consistent async operation tracking pattern

**What happens:** Async operations across the API use at least four different patterns — or no pattern at all:

| Operation | Returns | Tracking Method |
|-----------|---------|-----------------|
| Device create (9800-series) | 204, empty body | None — poll `devices list` |
| Location disable calling | 200, immediate | Job status endpoint (separate) |
| Activation email | Job ID | Poll job status |
| Number management jobs | Job ID | Poll job status |
| Location delete after disable | 409 for minutes/hours | Retry and hope |

**Evidence:** 9800-series (PhoneOS) device creation returns HTTP 204 with an empty body. The device appears 30-120 seconds later via CSDM. Classic MPP phones return 200 with the full device object synchronously. There is no job ID, no status endpoint, and no webhook for the 9800 path. Meanwhile, number management jobs return a job ID and have a proper status endpoint.

**Impact:** Every async operation requires a bespoke polling strategy. Some have job IDs, some require list-and-match, some require retry-on-409. Integrators build and maintain separate async handlers per feature.

**Suggested fix:** Standardize: all async operations return a `202 Accepted` with a `Location` header pointing to a status endpoint. Status endpoints return `{status: "pending"|"completed"|"failed", result: {...}}`. Optionally fire a webhook on completion.

---

### 27. [HIGH] Location delete 409 persists for minutes to hours after all resources removed

**What happens:** After removing every resource from a location and disabling calling, `DELETE /locations/{id}` continues to return 409 "is being referenced" for an indeterminate period — sometimes minutes, sometimes hours. For CCP (Cisco Calling Plan) orgs, this can persist for 1-4 hours while the backend asynchronously releases number inventory.

**Evidence:** Confirmed in both standard and CCP orgs. `safe-delete-check` returns `UNBLOCKED`, yet DELETE still returns 409. No API endpoint indicates when the backend will be ready.

**Impact:** Automated teardown workflows cannot determine when deletion will succeed. The only option is retry loops with arbitrary backoff. For CI/CD pipelines, this creates unpredictable pipeline durations.

**Suggested fix:** Add a `readyForDeletion` field to `safe-delete-check` or return a `Retry-After` header on the 409 with an estimated wait time.

---

### 28. [HIGH] Schedule and entity IDs derived from names — rename changes ID

**What happens:** Schedule IDs are base64-encoded from the schedule name. Renaming a schedule changes its ID. The old ID returns 404 (or worse — returns 200 on delete but does nothing). This also affects Call Park and Call Pickup entities, and selective call forwarding rules.

**Evidence:** Create schedule "Business Hours" → ID = `base64("Business Hours")`. Rename to "Office Hours" → old ID returns 404. Any automation referencing the old ID breaks silently.

**Impact:** Any system that stores resource IDs (webhooks, integrations, migration tools) has references invalidated by a rename. IDs should be immutable; names should be mutable metadata.

**Suggested fix:** Generate server-side UUIDs for all resource IDs. Names should be a mutable display field, not an ID-derivation input.

---

### 29. [MEDIUM] Webhook auto-deactivation with limited recovery

**What happens:** Webhooks that fail delivery repeatedly are auto-deactivated by the platform. You can reactivate or delete, but you cannot update the resource, event, or filter — only `name`, `targetUrl`, `secret`, and `status` are mutable after creation.

**Evidence:** Documented in the webhooks API. Also: org-level `telephony_calls` webhooks work in practice but are absent from the OpenAPI spec.

**Impact:** If your event subscription needs change (different filter, different event type), you must delete and recreate the webhook. Combined with auto-deactivation, this means webhooks require external health monitoring that the API itself could provide.

**Suggested fix:** Allow updating `resource`, `event`, and `filter` on existing webhooks. Add a health/status endpoint for webhook delivery metrics. Document `telephony_calls` org-level events in the spec.

---

## Category 7: Validation & Input Handling

### 30. [HIGH] PUT replaces entire resource — no PATCH on most endpoints

**What happens:** Most update endpoints use PUT with full-replace semantics. Omitting a field on update effectively deletes it. SCIM PUT is the most aggressive: omitting any attribute removes it from the user record.

**Evidence:** `PUT /v1/scim/{orgId}/Users/{userId}` — any attribute not included in the body is deleted. `PUT /people/{id}/features/voicemail` — same behavior. The meetings API offers both PUT and PATCH variants (`update-meetings` vs `update-meetings-1`), proving the platform can support both.

**Impact:** Every update requires a read-modify-write cycle. Any field you don't know about gets silently deleted. This is technically correct HTTP, but in practice it means integrators must fetch the complete current state before every update — doubling API calls and creating race conditions.

**Suggested fix:** Add PATCH endpoints alongside PUT. The meetings API already has this pattern — extend it to calling, identity, and device APIs.

---

### 31. [HIGH] Translation pattern replacements reject all wildcards without clear errors

**What happens:** Matching patterns support wildcards (`X`, `[2-9]`, `!`), but replacement patterns reject every wildcard character. The error message says "invalid pattern" without specifying that wildcards are the issue.

**Evidence:** `+1919666XXXX` fails. `+1212!` fails. `10XX` fails. Only fully specified E.164 strings like `+19196660000` succeed.

**Impact:** Anyone coming from a CUCM or traditional PBX background expects wildcard replacements (which CUCM supports). The error gives no guidance on what's actually allowed.

**Suggested fix:** If wildcards aren't supported in replacements, say so explicitly in the error: "Replacement patterns must be fully specified digits; wildcards (X, !, []) are only supported in match patterns." Also document this in the API spec.

---

### 32. [MEDIUM] Trunk password character restrictions undocumented

**What happens:** Trunk password fields reject `?` and `!` characters with `400 "Invalid characters ? or ! in password"`. The restriction isn't in the OpenAPI spec or docs.

**Evidence:** Confirmed during trunk provisioning. The error message is actually helpful — it names the invalid characters — but the restriction should be in the spec.

**Suggested fix:** Add a `pattern` constraint to the password field in the OpenAPI spec. Document allowed characters in the field description.

---

### 33. [MEDIUM] Delete access codes uses PUT with `deleteCodes` array instead of HTTP DELETE

**What happens:** To delete specific location access codes, you send `PUT /telephony/config/locations/{id}/accessCodes` with a `deleteCodes` array in the body. There is no HTTP DELETE method for individual access codes.

**Evidence:** Documented in `location-calling-media.md`. The DELETE method is not available on the access codes endpoint.

**Impact:** This violates REST conventions where DELETE removes a resource. Integrators using standard REST patterns will look for a DELETE endpoint that doesn't exist. The PUT-with-deleteCodes pattern is unique across the Webex API surface.

**Suggested fix:** Add `DELETE /telephony/config/locations/{id}/accessCodes/{codeId}` for individual code deletion. Keep the bulk PUT as an alternative.

---

## Category 8: OpenAPI Spec Quality

### 34. [HIGH] OpenAPI specs need investment as a first-class product

The OpenAPI specs are the actual product for anyone building automation — not the docs site, not Control Hub. Current issues compound:

**Missing or incorrect response schemas:**
- List endpoint response keys don't match the schema's predicted key (see issue #4 — affects 60+ endpoints)
- `operationId` values are semantically misleading (see issue #13)

**Incomplete request schemas:**
- Complex nested body parameters are defined in the schema but impractical to use without examples
- Call forwarding, voicemail, monitoring list — all require nested JSON that the spec defines structurally but doesn't illustrate

**Cross-spec inconsistency:**
- 9 specs across 6 domains use different conventions for the same patterns (pagination, error shapes, member arrays)
- Contact Center specs use entirely different conventions from Calling specs

**Missing documentation in descriptions:**
- Read-only fields not marked as such (see issue #18)
- License requirements not documented (see issues #3, #17)
- Character restrictions not in field patterns (see issue #32)
- Async behavior not indicated (see issue #26)

**Suggested fix:** Treat the OpenAPI specs as the primary deliverable for developer experience:
1. Add inline examples for every endpoint with a request body
2. Mark read-only fields with `readOnly: true`
3. Use consistent `operationId` naming conventions across all specs
4. Document response keys in response schemas
5. Add `description` text that includes licensing requirements and async behavior
6. Publish a cross-spec style guide and enforce it

---

## Summary Table

| # | Severity | Category | Issue |
|---|----------|----------|-------|
| 1 | CRITICAL | Auth | 19 person settings have no admin endpoint |
| 2 | CRITICAL | Auth | PATs don't carry Contact Center scopes |
| 3 | HIGH | Auth | Reports API requires Pro Pack — error doesn't say so |
| 4 | HIGH | Data Shape | Response list keys are unpredictable |
| 5 | HIGH | Data Shape | Member/agent format differs across features |
| 6 | MEDIUM | Data Shape | Notification type serialization asymmetry |
| 7 | MEDIUM | Data Shape | Language codes must be lowercase — no helpful error |
| 8 | MEDIUM | Data Shape | `announcementLanguage` returns None when set |
| 9 | HIGH | Path/Naming | Two parallel path families for person settings |
| 10 | HIGH | Path/Naming | Device API has two surfaces with different IDs |
| 11 | HIGH | Path/Naming | Contact Center is a separate API universe |
| 12 | MEDIUM | Path/Naming | Three audit/event APIs with overlapping names |
| 13 | MEDIUM | Path/Naming | Meeting API endpoint naming collisions |
| 14 | MEDIUM | Path/Naming | Virtual extension/line ID type mismatch |
| 15 | CRITICAL | Silent Fail | Supervisor delete returns 204 but doesn't delete |
| 16 | HIGH | Silent Fail | CX queues hidden in default list |
| 17 | HIGH | Silent Fail | 405 for license-gated workspaces (should be 403) |
| 18 | HIGH | Silent Fail | Read-only fields silently ignored on write |
| 19 | HIGH | Silent Fail | DECT + Standard license silently breaks calling |
| 20 | MEDIUM | Silent Fail | `callingData=true` silently caps page size |
| 21 | CRITICAL | Missing | No location dependency discovery endpoint |
| 22 | HIGH | Missing | No bulk calling settings API |
| 23 | HIGH | Missing | `devices list` caps at 100 with no warning |
| 24 | MEDIUM | Missing | Video Mesh API is read-only |
| 25 | MEDIUM | Missing | CQ show-agents requires `limit` param |
| 26 | HIGH | Async | No consistent async operation tracking |
| 27 | HIGH | Async | Location delete 409 persists for hours |
| 28 | HIGH | Async | IDs derived from names — rename breaks references |
| 29 | MEDIUM | Async | Webhook auto-deactivation with limited recovery |
| 30 | HIGH | Validation | PUT replaces entire resource — no PATCH |
| 31 | HIGH | Validation | Translation wildcards rejected without clear errors |
| 32 | MEDIUM | Validation | Trunk password restrictions undocumented |
| 33 | MEDIUM | Validation | Delete access codes uses PUT instead of DELETE |
| 34 | HIGH | Spec | OpenAPI specs need first-class investment |

**By severity:** 4 CRITICAL, 17 HIGH, 13 MEDIUM

---

## Closing Note

These issues share a common thread: **the API's individual endpoints mostly work — the pain is in the seams between them.** Inconsistent auth models, hidden data, misleading status codes, no dependency graph, no bulk path, no consistent async pattern. Every integrator builds the same workaround layer independently. Pushing that layer into the platform would be the single highest-leverage investment for developer experience.

We would welcome the opportunity to share specific reproduction cases, discuss prioritization, or provide additional detail on any of these items.
