<!-- Verified via CLI Batches 1-4, 2026-03-19 through 2026-03-21 -->
# Self-Service Call Settings Reference — /people/me/ API Surface

User-level self-service endpoints for managing personal call settings via user OAuth tokens. These endpoints mirror many admin-path settings but use `/telephony/config/people/me/` instead of `/telephony/config/people/{personId}/`.

## Sources

- specs/webex-cloud-calling.json (5 "Call Settings For Me" tags + Mode Management + Beta Barge-In, 151 endpoints across 95 paths)
- CLAUDE.md known issue #4 (6 user-only endpoints)
- person-call-settings-*.md (admin-path equivalents)

---

## 1. Overview & Authentication

### Token Requirements

All `/telephony/config/people/me/` endpoints require **user-level OAuth tokens**. Admin tokens (service app, integration with admin grant) will not work — they return 404 on user-only endpoints and are not supported on any `/me/` path.

The authenticated user **must have a Webex Calling license** assigned. Users without a calling license receive error 4008.

### Scopes

| Operation | Required Scope |
|-----------|---------------|
| GET (read settings) | `spark:people_read` |
| PUT (modify settings) | `spark:people_write` |
| POST (create criteria/numbers) | `spark:people_write` |
| DELETE (remove criteria/numbers) | `spark:people_write` |

### Error Patterns

| HTTP Code | Error Code | Meaning | Resolution |
|-----------|-----------|---------|------------|
| 404 | 4008 | User not calling-licensed | Assign Webex Calling license to the authenticated user |
| 404 | — | Endpoint not found | Verify the path; some settings require specific feature enablement |
| 400 | — | Bad request | Check request body against the schema |
| 401 | — | Unauthorized | Token expired or missing required scope |
| 403 | — | Forbidden | User lacks permission for this setting (may be admin-locked) |

### Base URL

All endpoints use `https://webexapis.com/v1` as the base URL:

```
https://webexapis.com/v1/telephony/config/people/me/...
```

---

## 2. User-Only Settings (No Admin Path)

These 6 settings exist **only** at `/telephony/config/people/me/settings/{feature}`. There is no admin-path equivalent (`/telephony/config/people/{personId}/...`). Admin tokens get 404. You **must** use a user-level OAuth token from the calling-licensed user whose settings you want to read or modify.

### Summary Table

| Setting | GET | PUT | Criteria CRUD | Tag |
|---------|-----|-----|---------------|-----|
| simultaneousRing | Yes | Yes | Create/Get/Update/Delete | Call Settings For Me Phase 4 |
| sequentialRing | Yes | Yes | Create/Get/Update/Delete | Call Settings For Me With UserHub Phase3 |
| priorityAlert | Yes | Yes | Create/Get/Update/Delete | Call Settings For Me With UserHub Phase2 |
| callNotify | Yes | Yes | Create/Get/Update/Delete | Call Settings For Me With UserHub Phase2 |
| anonymousCallReject | Yes | Yes | — | Call Settings For Me With UserHub Phase3 |
| callPolicies | Yes | Yes | — | Beta Call Settings For Me With Userhub Phase1 |

> **Note:** There is no standalone "List criteria" endpoint. Criteria are returned as a `criterias` array in the parent GET response (e.g., `GET /me/settings/simultaneousRing` includes all criteria in its response body).

### 2.1 Simultaneous Ring

Rings multiple phone numbers/destinations at the same time when the user receives an incoming call.

**Endpoints:**

| Method | Path | Summary |
|--------|------|---------|
| GET | `/me/settings/simultaneousRing` | Retrieve settings |
| PUT | `/me/settings/simultaneousRing` | Modify settings |
| POST | `/me/settings/simultaneousRing/criteria` | Create criteria |
| GET | `/me/settings/simultaneousRing/criteria/{id}` | Get criteria |
| PUT | `/me/settings/simultaneousRing/criteria/{id}` | Modify criteria |
| DELETE | `/me/settings/simultaneousRing/criteria/{id}` | Delete criteria |

**Raw HTTP — Read:**
```http
GET https://webexapis.com/v1/telephony/config/people/me/settings/simultaneousRing
Authorization: Bearer {user_token}
```

**Raw HTTP — Modify:**
```http
PUT https://webexapis.com/v1/telephony/config/people/me/settings/simultaneousRing
Authorization: Bearer {user_token}
Content-Type: application/json

{
  "enabled": true,
  "doNotRingIfOnCall": false,
  "phoneNumbers": [
    {
      "phoneNumber": "+14085551234",
      "answerConfirmationEnabled": false
    }
  ]
}
```

Data model details: see `person-call-settings-handling.md` section 4 (Simultaneous Ring).

### 2.2 Sequential Ring

Rings a sequence of phone numbers one after another until the call is answered or goes to voicemail.

**Endpoints:**

| Method | Path | Summary |
|--------|------|---------|
| GET | `/me/settings/sequentialRing` | Retrieve settings |
| PUT | `/me/settings/sequentialRing` | Modify settings |
| POST | `/me/settings/sequentialRing/criteria` | Create criteria |
| GET | `/me/settings/sequentialRing/criteria/{id}` | Get criteria |
| PUT | `/me/settings/sequentialRing/criteria/{id}` | Modify criteria |
| DELETE | `/me/settings/sequentialRing/criteria/{id}` | Delete criteria |

**Raw HTTP — Read:**
```http
GET https://webexapis.com/v1/telephony/config/people/me/settings/sequentialRing
Authorization: Bearer {user_token}
```

**Raw HTTP — Modify:**
```http
PUT https://webexapis.com/v1/telephony/config/people/me/settings/sequentialRing
Authorization: Bearer {user_token}
Content-Type: application/json

{
  "enabled": true,
  "ringBaseLocationFirst": true,
  "baseLocationNumberOfRings": 3,
  "continueIfBaseLocationIsBusy": true,
  "callerIdForOutgoingCalls": false,
  "phoneNumbers": [
    {
      "phoneNumber": "+14085551234",
      "numberOfRings": 3,
      "answerConfirmationEnabled": false
    }
  ]
}
```

Data model details: see `person-call-settings-handling.md` section 5 (Sequential Ring).

### 2.3 Priority Alert

Plays a distinctive ring pattern for calls matching specific criteria (e.g., from certain callers or during specific schedules).

**Endpoints:**

| Method | Path | Summary |
|--------|------|---------|
| GET | `/me/settings/priorityAlert` | Retrieve settings |
| PUT | `/me/settings/priorityAlert` | Modify settings |
| POST | `/me/settings/priorityAlert/criteria` | Create criteria |
| GET | `/me/settings/priorityAlert/criteria/{id}` | Get criteria |
| PUT | `/me/settings/priorityAlert/criteria/{id}` | Modify criteria |
| DELETE | `/me/settings/priorityAlert/criteria/{id}` | Delete criteria |

**Raw HTTP — Read:**
```http
GET https://webexapis.com/v1/telephony/config/people/me/settings/priorityAlert
Authorization: Bearer {user_token}
```

**Raw HTTP — Modify:**
```http
PUT https://webexapis.com/v1/telephony/config/people/me/settings/priorityAlert
Authorization: Bearer {user_token}
Content-Type: application/json

{
  "enabled": true
}
```

Data model details: see `person-call-settings-handling.md` section 10 (Priority Alert).

### 2.4 Call Notify

Sends email/text notifications when calls matching specific criteria are received.

**Endpoints:**

| Method | Path | Summary |
|--------|------|---------|
| GET | `/me/settings/callNotify` | Retrieve settings |
| PUT | `/me/settings/callNotify` | Modify settings |
| POST | `/me/settings/callNotify/criteria` | Create criteria |
| GET | `/me/settings/callNotify/criteria/{id}` | Get criteria |
| PUT | `/me/settings/callNotify/criteria/{id}` | Modify criteria |
| DELETE | `/me/settings/callNotify/criteria/{id}` | Delete criteria |

**Raw HTTP — Read:**
```http
GET https://webexapis.com/v1/telephony/config/people/me/settings/callNotify
Authorization: Bearer {user_token}
```

**Raw HTTP — Modify:**
```http
PUT https://webexapis.com/v1/telephony/config/people/me/settings/callNotify
Authorization: Bearer {user_token}
Content-Type: application/json

{
  "enabled": true,
  "destination": "user@example.com"
}
```

### 2.5 Anonymous Call Reject

Rejects calls from callers who have blocked their caller ID.

**Endpoints:**

| Method | Path | Summary |
|--------|------|---------|
| GET | `/me/settings/anonymousCallReject` | Retrieve settings |
| PUT | `/me/settings/anonymousCallReject` | Modify settings |

**Raw HTTP — Read:**
```http
GET https://webexapis.com/v1/telephony/config/people/me/settings/anonymousCallReject
Authorization: Bearer {user_token}
```

**Raw HTTP — Modify:**
```http
PUT https://webexapis.com/v1/telephony/config/people/me/settings/anonymousCallReject
Authorization: Bearer {user_token}
Content-Type: application/json

{
  "enabled": true
}
```

Data model details: see `person-call-settings-media.md` section 4 (Anonymous Call Rejection).

### 2.6 Call Policies [BETA]

Controls privacy behavior on redirected calls. Tagged as Beta.

**Endpoints:**

| Method | Path | Summary |
|--------|------|---------|
| GET | `/me/settings/callPolicies` | Retrieve settings |
| PUT | `/me/settings/callPolicies` | Modify settings |

**Raw HTTP — Read:**
```http
GET https://webexapis.com/v1/telephony/config/people/me/settings/callPolicies
Authorization: Bearer {user_token}
```

**Raw HTTP — Modify:**
```http
PUT https://webexapis.com/v1/telephony/config/people/me/settings/callPolicies
Authorization: Bearer {user_token}
Content-Type: application/json

{
  "privacyOnRedirectedCalls": "NO_PRIVACY"
}
```

Data model details: see `person-call-settings-permissions.md` section 5 (Call Policy). Note: the admin path uses `/telephony/config/people/{personId}/callPolicies` but that path does NOT appear in the current OpenAPI spec as an admin endpoint — it may exist but is undocumented.

---

## 3. Call Handling

Settings controlling how incoming calls are routed, forwarded, blocked, and selectively handled.

### Endpoint Table

| Setting | GET | PUT | Path Suffix | Admin Equivalent |
|---------|-----|-----|-------------|-----------------|
| Call Forwarding | Yes | Yes | `settings/callForwarding` | `/people/{personId}/features/callForwarding` |
| Call Waiting | Yes | Yes | `settings/callWaiting` | `/people/{personId}/features/callWaiting` |
| Do Not Disturb | Yes | Yes | `settings/doNotDisturb` [BETA] | `/people/{personId}/features/doNotDisturb` |
| Selective Accept | Yes | Yes | `settings/selectiveAccept` | `/telephony/config/people/{personId}/selectiveAccept` |
| Selective Accept Criteria | CRUD | — | `settings/selectiveAccept/criteria[/{id}]` | `/telephony/config/people/{personId}/selectiveAccept/criteria[/{id}]` |
| Selective Forward | Yes | Yes | `settings/selectiveForward` | `/telephony/config/people/{personId}/selectiveForward` |
| Selective Forward Criteria | CRUD | — | `settings/selectiveForward/criteria[/{id}]` | `/telephony/config/people/{personId}/selectiveForward/criteria[/{id}]` |
| Selective Reject | Yes | Yes | `settings/selectiveReject` | `/telephony/config/people/{personId}/selectiveReject` |
| Selective Reject Criteria | CRUD | — | `settings/selectiveReject/criteria[/{id}]` | `/telephony/config/people/{personId}/selectiveReject/criteria[/{id}]` |
| Call Block | Yes | — | `settings/callBlock` | — |
| Call Block Numbers | GET/POST/DELETE | — | `settings/callBlock/numbers[/{phoneNumberId}]` | — |
| Personal Assistant | Yes | Yes | `settings/personalAssistant` | `/telephony/config/people/{personId}/features/personalAssistant` |

### Raw HTTP — Read Call Forwarding

```http
GET https://webexapis.com/v1/telephony/config/people/me/settings/callForwarding
Authorization: Bearer {user_token}
```

Response includes `callForwarding` (always/busy/noAnswer settings) and `businessContinuity` fields. See `person-call-settings-handling.md` section 1 for the full data model.

### Raw HTTP — Read Call Block Settings

```http
GET https://webexapis.com/v1/telephony/config/people/me/settings/callBlock
Authorization: Bearer {user_token}
```

### Raw HTTP — Add Number to Call Block List

```http
POST https://webexapis.com/v1/telephony/config/people/me/settings/callBlock/numbers
Authorization: Bearer {user_token}
Content-Type: application/json

{
  "phoneNumber": "+14085559999"
}
```

**Cross-references:**
- Call Forwarding: `person-call-settings-handling.md` section 1
- Call Waiting: `person-call-settings-handling.md` section 2
- DND: `person-call-settings-handling.md` section 3
- Selective Accept/Forward/Reject: `person-call-settings-handling.md` sections 7-9
- Personal Assistant: `person-call-settings-behavior.md` section 13

---

## 4. Executive & Assistant

Settings for the executive/assistant feature, including screening, filtering, alerting, and assistant assignment.

### Endpoint Table

| Setting | GET | PUT | Path Suffix | Admin Equivalent | Tag |
|---------|-----|-----|-------------|-----------------|-----|
| Executive Alert | Yes | Yes | `settings/executive/alert` | `/telephony/config/people/{personId}/executive/alert` | Beta |
| Assigned Assistants | Yes | Yes | `settings/executive/assignedAssistants` | `/telephony/config/people/{personId}/executive/assignedAssistants` | — |
| Executive Assistant | Yes | Yes | `settings/executive/assistant` | `/telephony/config/people/{personId}/executive/assistant` | — |
| Available Assistants | Yes | — | `settings/executive/availableAssistants` | `/telephony/config/people/{personId}/executive/availableAssistants` | — |
| Call Filtering | Yes | Yes | `settings/executive/callFiltering` | `/telephony/config/people/{personId}/executive/callFiltering` | Beta |
| Call Filtering Criteria | CRUD | — | `settings/executive/callFiltering/criteria[/{id}]` | `/telephony/config/people/{personId}/executive/callFiltering/criteria[/{id}]` | Beta |
| Screening | Yes | Yes | `settings/executive/screening` | `/telephony/config/people/{personId}/executive/screening` | Beta |

### Raw HTTP — Read Executive Alert Settings

```http
GET https://webexapis.com/v1/telephony/config/people/me/settings/executive/alert
Authorization: Bearer {user_token}
```

### Raw HTTP — Modify Executive Assigned Assistants

```http
PUT https://webexapis.com/v1/telephony/config/people/me/settings/executive/assignedAssistants
Authorization: Bearer {user_token}
Content-Type: application/json

{
  "assistants": [
    {
      "id": "{assistant_person_id}"
    }
  ]
}
```

**Cross-reference:** `person-call-settings-permissions.md` section 4 (Executive / Assistant Settings).

---

## 5. Voicemail & Media

Settings for voicemail, call recording, caller ID, barge-in, and related media settings.

### Endpoint Table

| Setting | GET | PUT | POST | Path Suffix | Admin Equivalent |
|---------|-----|-----|------|-------------|-----------------|
| Voicemail | Yes | Yes | — | `settings/voicemail` | `/people/{personId}/features/voicemail` |
| Voicemail Busy Greeting Upload | — | — | Yes | `settings/voicemail/actions/busyGreetingUpload/invoke` | `/people/{personId}/features/voicemail/actions/uploadBusyGreeting/invoke` |
| Voicemail No Answer Greeting Upload | — | — | Yes | `settings/voicemail/actions/noAnswerGreetingUpload/invoke` | `/people/{personId}/features/voicemail/actions/uploadNoAnswerGreeting/invoke` |
| Caller ID | Yes | Yes | — | `settings/callerId` | `/people/{personId}/features/callerId` |
| Selected Caller ID | Yes | Yes | — | `settings/selectedCallerId` | — |
| Available Caller IDs | Yes | — | — | `settings/availableCallerIds` | `/telephony/config/people/{personId}/agent/availableCallerIds` |
| Call Recording | Yes | — | — | `settings/callRecording` | `/people/{personId}/features/callRecording` |
| Barge-In | Yes | Yes | — | `settings/bargeIn` [BETA] | `/people/{personId}/features/bargeIn` |
| Call Captions | Yes | — | — | `settings/callCaptions` | `/telephony/config/people/{personId}/callCaptions` |
| WebexGo Override | Yes | Yes | — | `settings/webexGoOverride` | — |

### Raw HTTP — Read Voicemail Settings

```http
GET https://webexapis.com/v1/telephony/config/people/me/settings/voicemail
Authorization: Bearer {user_token}
```

### Raw HTTP — Upload Busy Greeting

```http
POST https://webexapis.com/v1/telephony/config/people/me/settings/voicemail/actions/busyGreetingUpload/invoke
Authorization: Bearer {user_token}
Content-Type: multipart/form-data

--boundary
Content-Disposition: form-data; name="file"; filename="busy-greeting.wav"
Content-Type: audio/wav

{binary audio data}
--boundary--
```

### Raw HTTP — Modify Caller ID

```http
PUT https://webexapis.com/v1/telephony/config/people/me/settings/callerId
Authorization: Bearer {user_token}
Content-Type: application/json

{
  "selected": "DIRECT_LINE",
  "customNumber": null,
  "firstName": "John",
  "lastName": "Doe",
  "externalCallerIdNamePolicy": "DIRECT_LINE"
}
```

### Raw HTTP — Read Barge-In Settings [BETA]

```http
GET https://webexapis.com/v1/telephony/config/people/me/settings/bargeIn
Authorization: Bearer {user_token}
```

### Raw HTTP — Modify Barge-In Settings [BETA]

```http
PUT https://webexapis.com/v1/telephony/config/people/me/settings/bargeIn
Authorization: Bearer {user_token}
Content-Type: application/json

{
  "enabled": true,
  "toneEnabled": true
}
```

**Cross-references:**
- Voicemail: `person-call-settings-media.md` section 1
- Caller ID: `person-call-settings-media.md` sections 2-3
- Call Recording: `person-call-settings-media.md` section 7
- Barge-In: `person-call-settings-media.md` section 5
- Anonymous Call Rejection: `person-call-settings-media.md` section 4

---

## 6. Endpoints & Devices

Manage the user's registered endpoints (desk phones, soft clients, etc.) and preferred answer endpoint configuration.

### Endpoint Table

| Setting | GET | PUT | Path Suffix | Admin Equivalent |
|---------|-----|-----|-------------|-----------------|
| List Endpoints | Yes | — | `endpoints` | `/telephony/config/people/{personId}/devices` |
| Get Endpoint Details | Yes | Yes | `endpoints/{endpointId}` | — |
| Available Preferred Answer Endpoints | Yes | — | `settings/availablePreferredAnswerEndpoints` | `/telephony/config/people/{personId}/preferredAnswerEndpoint` (via availableEndpoints in response) |
| Preferred Answer Endpoint | Yes | Yes | `settings/preferredAnswerEndpoint` | `/telephony/config/people/{personId}/preferredAnswerEndpoint` |

### Raw HTTP — List My Endpoints

```http
GET https://webexapis.com/v1/telephony/config/people/me/endpoints
Authorization: Bearer {user_token}
```

### Raw HTTP — Set Preferred Answer Endpoint

```http
PUT https://webexapis.com/v1/telephony/config/people/me/settings/preferredAnswerEndpoint
Authorization: Bearer {user_token}
Content-Type: application/json

{
  "preferredAnswerEndpointId": "{endpoint_id}"
}
```

**Cross-reference:** `person-call-settings-behavior.md` section 10 (Preferred Answer Endpoint).

---

## 7. Routing & Groups

Read-only views of call park, call pickup, single number reach (SNR), and monitoring settings from the user's perspective.

### Endpoint Table

| Setting | GET | PUT | POST/DELETE | Path Suffix | Admin Equivalent |
|---------|-----|-----|-------------|-------------|-----------------|
| Call Park | Yes | — | — | `settings/callPark` | — (admin uses location-level call park) |
| Call Pickup Group | Yes | — | — | `settings/callPickupGroup` | — (admin uses location-level pickup groups) |
| Single Number Reach | Yes | Yes | — | `settings/singleNumberReach` | `/telephony/config/people/{personId}/singleNumberReach` |
| SNR Numbers | — | PUT | POST/DELETE | `settings/singleNumberReach/numbers[/{phoneNumberId}]` | `/telephony/config/people/{personId}/singleNumberReach/numbers[/{id}]` |
| Monitoring | Yes | — | — | `settings/monitoring` | `/people/{personId}/features/monitoring` |

### Raw HTTP — Read My Call Park Settings

```http
GET https://webexapis.com/v1/telephony/config/people/me/settings/callPark
Authorization: Bearer {user_token}
```

### Raw HTTP — Add Single Number Reach Number

```http
POST https://webexapis.com/v1/telephony/config/people/me/settings/singleNumberReach/numbers
Authorization: Bearer {user_token}
Content-Type: application/json

{
  "phoneNumber": "+14085551234",
  "extension": "1234",
  "answerTooLateAction": "SEND_TO_VOICEMAIL",
  "answerTooSoonNumberOfRings": 0,
  "answerTooLateNumberOfRings": 5
}
```

**Cross-references:**
- Single Number Reach: `person-call-settings-handling.md` section 6
- Monitoring: `person-call-settings-media.md` section 9

---

## 8. Queue & Agent

Settings related to call queue agent behavior and calling services status.

### Endpoint Table

| Setting | GET | PUT | Path Suffix | Admin Equivalent |
|---------|-----|-----|-------------|-----------------|
| Call Center (Queue Agent) | Yes | Yes | `settings/queues` | — |
| Calling Services | Yes | — | `settings/services` | — |
| Contact Center Extensions | Yes | — | `settings/contactCenterExtensions` | — |

### Raw HTTP — Read My Call Center Settings

```http
GET https://webexapis.com/v1/telephony/config/people/me/settings/queues
Authorization: Bearer {user_token}
```

### Raw HTTP — Modify Call Center Settings (Join/Unjoin Queues)

```http
PUT https://webexapis.com/v1/telephony/config/people/me/settings/queues
Authorization: Bearer {user_token}
Content-Type: application/json

{
  "availableInCallQueue": true,
  "callQueueEnabled": true
}
```

### Raw HTTP — Read My Calling Services

```http
GET https://webexapis.com/v1/telephony/config/people/me/settings/services
Authorization: Bearer {user_token}
```

Returns list of calling services available to the user with their enabled/disabled state.

### Raw HTTP — Read Contact Center Extensions

```http
GET https://webexapis.com/v1/telephony/config/people/me/settings/contactCenterExtensions
Authorization: Bearer {user_token}
```

Returns contact center extension information for the authenticated user. No admin-path equivalent exists.

---

## 9. Location & System

Endpoints for retrieving location-level data, schedules, assigned numbers, feature access codes, announcement languages, and country configurations.

### Endpoint Table

| Setting | Methods | Path Suffix | Admin Equivalent | Tag |
|---------|---------|-------------|-----------------|-----|
| My Details | GET | (root: `/me`) | `/telephony/config/people/{personId}` (via other APIs) | — |
| Announcement Languages | GET | `announcementLanguages` | — | Beta |
| Country Config | GET | `countries/{countryCode}` | — | Beta |
| Assigned Numbers (Location) | GET | `location/assignedNumbers` | — | — |
| Location Schedule (Get) | GET | `locations/schedules/{scheduleType}/{scheduleId}` | `/people/{personId}/features/schedules` | — |
| User Schedules (List) | GET | `schedules` | `/people/{personId}/features/schedules` | — |
| User Schedule (CRUD) | GET/POST/PUT/DELETE | `schedules[/{scheduleType}/{scheduleId}]` | `/people/{personId}/features/schedules[/{scheduleType}/{scheduleId}]` | — |
| Schedule Events (CRUD) | GET/POST/PUT/DELETE | `schedules/{scheduleType}/{scheduleId}/events[/{eventId}]` | `/people/{personId}/features/schedules/{scheduleType}/{scheduleId}/events[/{eventId}]` | — |
| Feature Access Codes | GET | `settings/featureAccessCode` | — | — |
| Guest Calling Numbers | GET | `settings/guestCalling/numbers` | — | — |

### Raw HTTP — Get My Details

```http
GET https://webexapis.com/v1/telephony/config/people/me
Authorization: Bearer {user_token}
```

### Raw HTTP — List My Schedules

```http
GET https://webexapis.com/v1/telephony/config/people/me/schedules
Authorization: Bearer {user_token}
```

### Raw HTTP — Create a User Schedule

```http
POST https://webexapis.com/v1/telephony/config/people/me/schedules
Authorization: Bearer {user_token}
Content-Type: application/json

{
  "name": "Business Hours",
  "type": "businessHours"
}
```

### Raw HTTP — Get Feature Access Codes

```http
GET https://webexapis.com/v1/telephony/config/people/me/settings/featureAccessCode
Authorization: Bearer {user_token}
```

### Raw HTTP — Get Announcement Languages [BETA]

```http
GET https://webexapis.com/v1/telephony/config/people/me/announcementLanguages
Authorization: Bearer {user_token}
```

---

## 10. Secondary Line Settings

When a user has secondary lines (shared lines from other users), these endpoints let them manage settings for those secondary lines. The `{lineOwnerId}` parameter is the person ID of the line owner.

### Endpoint Table

| Setting | GET | PUT | Path Suffix | Admin Equivalent |
|---------|-----|-----|-------------|-----------------|
| Available Caller IDs | Yes | — | `secondaryLines/{lineownerId}/availableCallerIds` | — |
| Call Forwarding | Yes | Yes | `secondaryLines/{lineownerId}/callForwarding` | — |
| Call Park | Yes | — | `secondaryLines/{lineownerId}/callPark` | — |
| Call Pickup Group | Yes | — | `secondaryLines/{lineownerId}/callPickupGroup` | — |
| Call Recording | Yes | — | `secondaryLines/{lineownerId}/callRecording` | — |
| Caller ID | Yes | Yes | `secondaryLines/{lineownerId}/callerId` | — |
| Feature Access Codes | Yes | — | `secondaryLines/{lineownerId}/featureAccessCode` | — |
| Call Center (Queues) | Yes | Yes | `secondaryLines/{lineownerId}/queues` | — |
| Selected Caller ID | Yes | Yes | `secondaryLines/{lineownerId}/selectedCallerId` | — |
| Calling Services | Yes | — | `secondaryLines/{lineownerId}/services` | — |
| Voicemail | Yes | Yes | `secondaryLines/{lineownerId}/voicemail` | — |
| Available Preferred Answer Endpoints | Yes | — | `secondaryLines/{lineOwnerId}/availablePreferredAnswerEndpoints` | — |
| Preferred Answer Endpoint | Yes | Yes | `secondaryLines/{lineOwnerId}/preferredAnswerEndpoint` | — |

All secondary line endpoints are unique to the `/me/` surface. There are no admin-path equivalents.

### Raw HTTP — Read Secondary Line Call Forwarding

```http
GET https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineOwnerId}/callForwarding
Authorization: Bearer {user_token}
```

### Raw HTTP — Modify Secondary Line Voicemail

```http
PUT https://webexapis.com/v1/telephony/config/people/me/settings/secondaryLines/{lineOwnerId}/voicemail
Authorization: Bearer {user_token}
Content-Type: application/json

{
  "enabled": true,
  "sendBusyCalls": {
    "enabled": true,
    "greeting": "DEFAULT"
  },
  "sendUnansweredCalls": {
    "enabled": true,
    "greeting": "DEFAULT",
    "numberOfRings": 6
  }
}
```

---

## 11. Mode Management

User-level mode management for operating modes (e.g., after-hours, holiday). These endpoints let the calling-licensed user view and switch operating modes for features they participate in. Tagged as "Mode Management" in the spec.

> **Note:** Admin-path equivalents exist at `/telephony/config/people/{personId}/modeManagement/` but only expose `availableFeatures` (GET) and `features` (GET/PUT). The `/me/` surface is significantly richer with 9 endpoints including mode switching actions.

### Endpoint Table

| Setting | Method | Path Suffix | Admin Equivalent |
|---------|--------|-------------|-----------------|
| List Mode Management Features | GET | `settings/modeManagement/features` | `/telephony/config/people/{personId}/modeManagement/features` |
| Get Common Modes | GET | `settings/modeManagement/features/commonModes` | — |
| Get Mode Management Feature | GET | `settings/modeManagement/features/{featureId}` | — |
| Get Normal Operation Mode | GET | `settings/modeManagement/features/{featureId}/normalOperationMode` | — |
| Get Operating Mode | GET | `settings/modeManagement/features/{featureId}/modes/{modeId}` | — |
| Switch Mode (Multiple Features) | POST | `settings/modeManagement/features/actions/switchMode/invoke` | — |
| Switch Mode (Single Feature) | POST | `settings/modeManagement/features/{featureId}/actions/switchMode/invoke` | — |
| Extend Current Mode Duration | POST | `settings/modeManagement/features/{featureId}/actions/extendMode/invoke` | — |
| Switch to Normal Operation | POST | `settings/modeManagement/features/{featureId}/actions/switchToNormalOperation/invoke` | — |

### Raw HTTP — List Mode Management Features

```http
GET https://webexapis.com/v1/telephony/config/people/me/settings/modeManagement/features
Authorization: Bearer {user_token}
```

### Raw HTTP — Switch Mode for a Feature

```http
POST https://webexapis.com/v1/telephony/config/people/me/settings/modeManagement/features/{featureId}/actions/switchMode/invoke
Authorization: Bearer {user_token}
Content-Type: application/json

{
  "modeId": "{mode_id}"
}
```

### Raw HTTP — Switch to Normal Operation

```http
POST https://webexapis.com/v1/telephony/config/people/me/settings/modeManagement/features/{featureId}/actions/switchToNormalOperation/invoke
Authorization: Bearer {user_token}
```

**Cross-reference:** CLAUDE.md known issue #3 (mode-management requires calling-licensed user). See also `location-call-settings-advanced.md` for admin-level operating modes.

---

## 12. Admin Path Cross-Reference Table

Master mapping of every `/me/` endpoint to its admin equivalent. Path suffixes are relative to `/telephony/config/people/me/` (user) and the noted admin base path.

| Setting | User Path Suffix | Admin Path | Reference Doc |
|---------|-----------------|------------|---------------|
| **User-Only (no admin path)** | | | |
| Simultaneous Ring | `settings/simultaneousRing` | USER ONLY | person-call-settings-handling.md sec 4 |
| Simultaneous Ring Criteria | `settings/simultaneousRing/criteria[/{id}]` | USER ONLY | person-call-settings-handling.md sec 4 |
| Sequential Ring | `settings/sequentialRing` | USER ONLY | person-call-settings-handling.md sec 5 |
| Sequential Ring Criteria | `settings/sequentialRing/criteria[/{id}]` | USER ONLY | person-call-settings-handling.md sec 5 |
| Priority Alert | `settings/priorityAlert` | USER ONLY | person-call-settings-handling.md sec 10 |
| Priority Alert Criteria | `settings/priorityAlert/criteria[/{id}]` | USER ONLY | person-call-settings-handling.md sec 10 |
| Call Notify | `settings/callNotify` | USER ONLY | person-call-settings-handling.md |
| Call Notify Criteria | `settings/callNotify/criteria[/{id}]` | USER ONLY | person-call-settings-handling.md |
| Anonymous Call Reject | `settings/anonymousCallReject` | USER ONLY | person-call-settings-media.md sec 4 |
| Call Policies | `settings/callPolicies` [BETA] | USER ONLY | person-call-settings-permissions.md sec 5 |
| **Call Handling** | | | |
| Call Forwarding | `settings/callForwarding` | `/people/{personId}/features/callForwarding` | person-call-settings-handling.md sec 1 |
| Call Waiting | `settings/callWaiting` | `/people/{personId}/features/callWaiting` | person-call-settings-handling.md sec 2 |
| Do Not Disturb | `settings/doNotDisturb` [BETA] | `/people/{personId}/features/doNotDisturb` | person-call-settings-handling.md sec 3 |
| Selective Accept | `settings/selectiveAccept` | `/telephony/config/people/{personId}/selectiveAccept` | person-call-settings-handling.md sec 7 |
| Selective Accept Criteria | `settings/selectiveAccept/criteria[/{id}]` | `/telephony/config/people/{personId}/selectiveAccept/criteria[/{id}]` | person-call-settings-handling.md sec 7 |
| Selective Forward | `settings/selectiveForward` | `/telephony/config/people/{personId}/selectiveForward` | person-call-settings-handling.md sec 8 |
| Selective Forward Criteria | `settings/selectiveForward/criteria[/{id}]` | `/telephony/config/people/{personId}/selectiveForward/criteria[/{id}]` | person-call-settings-handling.md sec 8 |
| Selective Reject | `settings/selectiveReject` | `/telephony/config/people/{personId}/selectiveReject` | person-call-settings-handling.md sec 9 |
| Selective Reject Criteria | `settings/selectiveReject/criteria[/{id}]` | `/telephony/config/people/{personId}/selectiveReject/criteria[/{id}]` | person-call-settings-handling.md sec 9 |
| Call Block | `settings/callBlock` | — | — |
| Call Block Numbers | `settings/callBlock/numbers[/{phoneNumberId}]` | — | — |
| Personal Assistant | `settings/personalAssistant` | `/telephony/config/people/{personId}/features/personalAssistant` | person-call-settings-behavior.md sec 13 |
| **Executive & Assistant** | | | |
| Executive Alert | `settings/executive/alert` [BETA] | `/telephony/config/people/{personId}/executive/alert` | person-call-settings-permissions.md sec 4 |
| Assigned Assistants | `settings/executive/assignedAssistants` | `/telephony/config/people/{personId}/executive/assignedAssistants` | person-call-settings-permissions.md sec 4 |
| Executive Assistant | `settings/executive/assistant` | `/telephony/config/people/{personId}/executive/assistant` | person-call-settings-permissions.md sec 4 |
| Available Assistants | `settings/executive/availableAssistants` | `/telephony/config/people/{personId}/executive/availableAssistants` | person-call-settings-permissions.md sec 4 |
| Call Filtering | `settings/executive/callFiltering` [BETA] | `/telephony/config/people/{personId}/executive/callFiltering` | person-call-settings-permissions.md sec 4 |
| Call Filtering Criteria | `settings/executive/callFiltering/criteria[/{id}]` [BETA] | `/telephony/config/people/{personId}/executive/callFiltering/criteria[/{id}]` | person-call-settings-permissions.md sec 4 |
| Screening | `settings/executive/screening` [BETA] | `/telephony/config/people/{personId}/executive/screening` | person-call-settings-permissions.md sec 4 |
| **Voicemail & Media** | | | |
| Voicemail | `settings/voicemail` | `/people/{personId}/features/voicemail` | person-call-settings-media.md sec 1 |
| Voicemail Busy Greeting | `settings/voicemail/actions/busyGreetingUpload/invoke` | `/people/{personId}/features/voicemail/actions/uploadBusyGreeting/invoke` | person-call-settings-media.md sec 1 |
| Voicemail No Answer Greeting | `settings/voicemail/actions/noAnswerGreetingUpload/invoke` | `/people/{personId}/features/voicemail/actions/uploadNoAnswerGreeting/invoke` | person-call-settings-media.md sec 1 |
| Caller ID | `settings/callerId` | `/people/{personId}/features/callerId` | person-call-settings-media.md sec 2 |
| Selected Caller ID | `settings/selectedCallerId` | — | person-call-settings-media.md sec 3 |
| Available Caller IDs | `settings/availableCallerIds` | `/telephony/config/people/{personId}/agent/availableCallerIds` | person-call-settings-media.md sec 3 |
| Call Recording | `settings/callRecording` | `/people/{personId}/features/callRecording` | person-call-settings-media.md sec 7 |
| Barge-In | `settings/bargeIn` [BETA] | `/people/{personId}/features/bargeIn` | person-call-settings-media.md sec 5 |
| Call Captions | `settings/callCaptions` | `/telephony/config/people/{personId}/callCaptions` | — |
| WebexGo Override | `settings/webexGoOverride` | — | — |
| **Endpoints & Devices** | | | |
| List Endpoints | `endpoints` | `/telephony/config/people/{personId}/devices` | devices-core.md |
| Endpoint Details | `endpoints/{endpointId}` | — | — |
| Available Preferred Answer | `settings/availablePreferredAnswerEndpoints` | — | person-call-settings-behavior.md sec 10 |
| Preferred Answer Endpoint | `settings/preferredAnswerEndpoint` | `/telephony/config/people/{personId}/preferredAnswerEndpoint` | person-call-settings-behavior.md sec 10 |
| **Routing & Groups** | | | |
| Call Park | `settings/callPark` | — (location-level) | call-features-additional.md |
| Call Pickup Group | `settings/callPickupGroup` | — (location-level) | call-features-additional.md |
| Single Number Reach | `settings/singleNumberReach` | `/telephony/config/people/{personId}/singleNumberReach` | person-call-settings-handling.md sec 6 |
| SNR Numbers | `settings/singleNumberReach/numbers[/{phoneNumberId}]` | `/telephony/config/people/{personId}/singleNumberReach/numbers[/{id}]` | person-call-settings-handling.md sec 6 |
| Monitoring | `settings/monitoring` | `/people/{personId}/features/monitoring` | person-call-settings-media.md sec 9 |
| **Queue & Agent** | | | |
| Call Center (Queues) | `settings/queues` | — | — |
| Calling Services | `settings/services` | — | — |
| Contact Center Extensions | `settings/contactCenterExtensions` | — | — |
| **Mode Management** | | | |
| Mode Management Features | `settings/modeManagement/features` | `/telephony/config/people/{personId}/modeManagement/features` | location-call-settings-advanced.md |
| Common Modes | `settings/modeManagement/features/commonModes` | — | — |
| Mode Management Feature | `settings/modeManagement/features/{featureId}` | — | — |
| Normal Operation Mode | `settings/modeManagement/features/{featureId}/normalOperationMode` | — | — |
| Operating Mode | `settings/modeManagement/features/{featureId}/modes/{modeId}` | — | — |
| Switch Mode (Multi) | `settings/modeManagement/features/actions/switchMode/invoke` | — | — |
| Switch Mode (Single) | `settings/modeManagement/features/{featureId}/actions/switchMode/invoke` | — | — |
| Extend Mode Duration | `settings/modeManagement/features/{featureId}/actions/extendMode/invoke` | — | — |
| Switch to Normal | `settings/modeManagement/features/{featureId}/actions/switchToNormalOperation/invoke` | — | — |
| **Location & System** | | | |
| My Details | (root: `/me`) | — | — |
| Announcement Languages | `announcementLanguages` [BETA] | — | — |
| Country Config | `countries/{countryCode}` [BETA] | — | — |
| Assigned Numbers | `location/assignedNumbers` | — | — |
| Location Schedule | `locations/schedules/{scheduleType}/{scheduleId}` | — | — |
| User Schedules | `schedules` | `/people/{personId}/features/schedules` | — |
| User Schedule CRUD | `schedules/{scheduleType}/{scheduleId}` | `/people/{personId}/features/schedules/{scheduleType}/{scheduleId}` | — |
| Schedule Events CRUD | `schedules/.../events[/{eventId}]` | `/people/{personId}/features/schedules/.../events[/{eventId}]` | — |
| Feature Access Codes | `settings/featureAccessCode` | — | — |
| Guest Calling Numbers | `settings/guestCalling/numbers` | — | — |
| **Secondary Line Settings** | | | |
| Secondary Line Available Caller IDs | `settings/secondaryLines/{lineownerId}/availableCallerIds` | USER ONLY | — |
| Secondary Line Call Forwarding | `settings/secondaryLines/{lineownerId}/callForwarding` | USER ONLY | — |
| Secondary Line Call Park | `settings/secondaryLines/{lineownerId}/callPark` | USER ONLY | — |
| Secondary Line Call Pickup Group | `settings/secondaryLines/{lineownerId}/callPickupGroup` | USER ONLY | — |
| Secondary Line Call Recording | `settings/secondaryLines/{lineownerId}/callRecording` | USER ONLY | — |
| Secondary Line Caller ID | `settings/secondaryLines/{lineownerId}/callerId` | USER ONLY | — |
| Secondary Line Feature Access Codes | `settings/secondaryLines/{lineownerId}/featureAccessCode` | USER ONLY | — |
| Secondary Line Queues | `settings/secondaryLines/{lineownerId}/queues` | USER ONLY | — |
| Secondary Line Selected Caller ID | `settings/secondaryLines/{lineownerId}/selectedCallerId` | USER ONLY | — |
| Secondary Line Calling Services | `settings/secondaryLines/{lineownerId}/services` | USER ONLY | — |
| Secondary Line Voicemail | `settings/secondaryLines/{lineownerId}/voicemail` | USER ONLY | — |
| Secondary Line Available Preferred Answer | `settings/secondaryLines/{lineOwnerId}/availablePreferredAnswerEndpoints` | USER ONLY | — |
| Secondary Line Preferred Answer | `settings/secondaryLines/{lineOwnerId}/preferredAnswerEndpoint` | USER ONLY | — |

---

## Gotchas

1. **Admin tokens do not work on /me/ paths.** All 151 endpoints require user-level OAuth. Admin tokens (from service apps or admin-granted integrations) will get 404 or 401, not a helpful error.

2. **User must have Webex Calling license.** Error 4008 ("User not found or not calling-licensed") is returned for all `/me/` endpoints if the authenticated user lacks a Calling license.

3. **6 settings have NO admin path.** `simultaneousRing`, `sequentialRing`, `priorityAlert`, `callNotify`, `anonymousCallReject`, and `callPolicies` can only be managed via user OAuth through the `/me/` surface. There is no way for an admin to read or modify these settings on behalf of a user via API.

4. **Beta endpoints may change.** Endpoints tagged with `Beta Call Settings For Me With Userhub Phase1` (callPolicies) and several executive/DND endpoints are marked beta. Their schemas may change without notice.

5. **Secondary line settings are entirely user-only.** The 13 secondary line endpoints under `settings/secondaryLines/{lineOwnerId}/...` have no admin-path equivalent. Admins cannot manage a user's secondary line settings via API.

6. **Path naming differs from admin paths.** Some `/me/` path suffixes differ from admin equivalents:
   - `/me/endpoints` vs admin `/devices`
   - `/me/settings/voicemail/actions/busyGreetingUpload/invoke` vs admin `.../actions/uploadBusyGreeting/invoke`
   - `/me/settings/callBlock` has no admin equivalent at all

7. **Read-only settings.** Several settings only expose GET (no PUT): `callRecording`, `callCaptions`, `callPark`, `callPickupGroup`, `monitoring`, `featureAccessCode`, `services`, `availableCallerIds`, `availablePreferredAnswerEndpoints`, `guestCalling/numbers`, `announcementLanguages`, `countries/{countryCode}`. These are informational views of settings controlled by the admin.

8. **Call Block is self-service only.** The call block feature (personal block list for phone numbers) exists only on the `/me/` surface with no admin equivalent. Users manage their own block list via GET/POST/DELETE on `settings/callBlock/numbers`.

9. **Two schedule path families.** User schedules are at `schedules/{scheduleType}/{scheduleId}`, while location-level schedules (read-only to the user) are at `locations/schedules/{scheduleType}/{scheduleId}`.

10. **Criteria CRUD pattern.** Eight settings use the criteria sub-resource pattern (simultaneousRing, sequentialRing, priorityAlert, callNotify, selectiveAccept, selectiveForward, selectiveReject, and executive callFiltering). GET on the parent resource returns a `criterias` array with summary objects. Full CRUD on individual criteria uses the `/criteria/{id}` sub-path.

11. **Mode management is richer on /me/ than admin.** The admin path only has 2 endpoints (`availableFeatures` GET and `features` GET/PUT) while the `/me/` surface exposes 9 endpoints including mode switching, extending, and normal operation actions. Mode management requires a calling-licensed user (CLAUDE.md known issue #3).

12. **Barge-In is tagged Beta.** The `/me/settings/bargeIn` endpoints are tagged `Beta Settings Features For Barge-In`. The admin equivalent at `/people/{personId}/features/bargeIn` is the stable path.

13. **Contact Center Extensions is user-only.** The `contactCenterExtensions` GET endpoint has no admin-path equivalent and no tag assignment in the spec.

---

## See Also

- [person-call-settings-handling.md](person-call-settings-handling.md) — Call forwarding, waiting, DND, sim/sequential ring, selective accept/forward/reject, priority alert, SNR
- [person-call-settings-media.md](person-call-settings-media.md) — Voicemail, caller ID, anonymous call reject, privacy, barge-in, call recording, monitoring
- [person-call-settings-permissions.md](person-call-settings-permissions.md) — Incoming/outgoing permissions, feature access, executive/assistant, call policy
- [person-call-settings-behavior.md](person-call-settings-behavior.md) — Calling behavior, app services, hoteling, receptionist, numbers, preferred answer, personal assistant
- [authentication.md](authentication.md) — OAuth flows, user-level tokens, scopes
- [call-features-additional.md](call-features-additional.md) — Call park, call pickup (location-level admin equivalents)
- [devices-core.md](devices-core.md) — Device management (admin equivalent of endpoints)
