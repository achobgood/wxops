# Meetings: Settings, Preferences, and Administration

Reference for Webex Meetings settings and preferences management. Covers the 34 commands across 8 CLI groups that an IT admin or meeting host uses to manage meeting preferences, session types, tracking codes, site settings, polls, Q&A, reports, and Slido compliance events. Sourced from the Webex Meetings API (OpenAPI spec: `specs/webex-meetings.json`).

## Sources

- OpenAPI spec: `specs/webex-meetings.json`
- [developer.webex.com Meeting Preferences API](https://developer.webex.com/docs/api/v1/meeting-preferences)
- [developer.webex.com Tracking Codes API](https://developer.webex.com/docs/api/v1/tracking-codes)

---

## Token Type Matrix

| Operation | User Token | Admin Token | Notes |
|-----------|-----------|-------------|-------|
| Meeting preferences (get/update) | Yes (own) | Yes (any user via `userEmail`) | Default: operates on authenticated user |
| Sites list/update default | Yes (own) | Yes (any user via `userEmail`) | |
| PMR options (get/update) | Yes (own) | Yes (any user via `userEmail`) | |
| Batch refresh PMR IDs | No | Yes | Admin-only endpoint under `/admin/` |
| Session types (site) | No | Yes | Admin-only |
| Session types (user) | No | Yes | Admin-only |
| Tracking codes (site CRUD) | No | Yes | Admin-only |
| Tracking codes (user get/update) | No | Yes | Admin-only |
| Site common settings | No | Yes | Admin-only |
| Meeting polls/results | Yes (host or attendee) | Yes (with admin scopes) | Read-only |
| Meeting Q&A | Yes (host or attendee) | Yes (with admin scopes) | Read-only |
| Meeting reports | No | Yes | Requires siteUrl |
| Slido compliance events | No | Yes | Requires Slido Secure Premium license |

---

## Table of Contents

1. [Meeting Preferences](#1-meeting-preferences)
2. [Session Types](#2-session-types)
3. [Tracking Codes](#3-tracking-codes)
4. [Site Settings](#4-site-settings)
5. [Meeting Polls](#5-meeting-polls)
6. [Meeting Q&A](#6-meeting-qa)
7. [Meeting Reports](#7-meeting-reports)
8. [Slido Compliance](#8-slido-compliance)
9. [Raw HTTP Endpoints](#9-raw-http-endpoints)
10. [Gotchas](#10-gotchas)
11. [See Also](#11-see-also)

---

## 1. Meeting Preferences

**CLI group:** `meeting-preferences`
**API base:** `https://webexapis.com/v1/meetingPreferences`

Meeting preferences control audio/video settings, scheduling options, delegate access, site selection, and Personal Meeting Room (PMR) configuration for individual users. All preference endpoints operate on the authenticated user by default; admins can target another user via `--user-email`.

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| Get all preferences | `wxcli meeting-preferences list-meeting-preferences` | GET /meetingPreferences | Get complete meeting preference details |
| Get audio options | `wxcli meeting-preferences show` | GET /meetingPreferences/audio | Get audio preferences (call-in, VoIP, toll-free) |
| Update audio options | `wxcli meeting-preferences update` | PUT /meetingPreferences/audio | Update audio preferences |
| Get video options | `wxcli meeting-preferences list` | GET /meetingPreferences/video | Get video device preferences |
| Update video options | `wxcli meeting-preferences update-video` | PUT /meetingPreferences/video | Update video device preferences |
| Get scheduling options | `wxcli meeting-preferences list-scheduling-options` | GET /meetingPreferences/schedulingOptions | Get scheduling preferences (delegates, join-before-host) |
| Update scheduling options | `wxcli meeting-preferences update-scheduling-options` | PUT /meetingPreferences/schedulingOptions | Update scheduling preferences |
| Insert delegate emails | `wxcli meeting-preferences create-insert` | POST /meetingPreferences/schedulingOptions/delegateEmails/insert | Add delegate emails for scheduling |
| Delete delegate emails | `wxcli meeting-preferences create` | POST /meetingPreferences/schedulingOptions/delegateEmails/delete | Remove delegate emails |
| Get site list | `wxcli meeting-preferences list-sites` | GET /meetingPreferences/sites | List available Webex sites and default site |
| Update default site | `wxcli meeting-preferences update-sites` | PUT /meetingPreferences/sites | Change the user's default Webex site |
| Get PMR options | `wxcli meeting-preferences list-personal-meeting-room` | GET /meetingPreferences/personalMeetingRoom | Get Personal Meeting Room settings |
| Update PMR options | `wxcli meeting-preferences update-personal-meeting-room` | PUT /meetingPreferences/personalMeetingRoom | Update PMR settings (co-hosts, auto-lock, PIN) |
| Batch refresh PMR IDs | `wxcli meeting-preferences create-refresh-id` | POST /admin/meetingPreferences/personalMeetingRoom/refreshId | Batch refresh PMR IDs for multiple users (admin) |

### Key Parameters

#### Common Parameters (all preference endpoints)

| Option | Description |
|--------|-------------|
| `--user-email EMAIL` | Email of the target user. Admin-only -- acts on behalf of the specified user |
| `--site-url URL` | URL of the Webex site to query. Defaults to the user's default site |

#### `meeting-preferences update` (Audio Options)

| Option | Description |
|--------|-------------|
| `--default-audio-type TEXT` | Default audio type: `voipOnly`, `phoneOnly`, `otherTeleconferenceService`, `none` |
| `--enabled-toll-free / --no-enabled-toll-free` | Enable/disable toll-free call-in numbers |
| `--enabled-global-call-in / --no-enabled-global-call-in` | Enable/disable global call-in numbers |
| `--enabled-auto-connection / --no-enabled-auto-connection` | Auto-connect to audio on join |
| `--audio-pin TEXT` | Audio PIN for call-in authentication |
| `--json-body JSON` | Full JSON body for nested fields (`officeNumber`, `mobileNumber`) |

#### `meeting-preferences update-video` (Video Options)

| Option | Description |
|--------|-------------|
| `--json-body JSON` | Required for video device array: `{"videoDevices": [{"deviceName": "...", "deviceAddress": "...", "isDefault": true}]}` |

#### `meeting-preferences update-scheduling-options` (Scheduling Options)

| Option | Description |
|--------|-------------|
| `--enabled-join-before-host / --no-enabled-join-before-host` | Allow attendees to join before host |
| `--join-before-host-minutes N` | Minutes before start that attendees can join (5, 10, 15) |
| `--enabled-auto-share-recording / --no-enabled-auto-share-recording` | Auto-share recording after meeting |
| `--enabled-webex-assistant-by-default / --no-enabled-webex-assistant-by-default` | Enable Webex Assistant by default |
| `--json-body JSON` | Full JSON body (includes `delegateEmails` array) |

#### `meeting-preferences create-insert` (Insert Delegate Emails)

| Option | Description |
|--------|-------------|
| `--json-body JSON` | Required: `{"emails": ["delegate1@example.com", "delegate2@example.com"]}` |

#### `meeting-preferences create` (Delete Delegate Emails)

| Option | Description |
|--------|-------------|
| `--json-body JSON` | Required: `{"emails": ["delegate1@example.com"]}` |

#### `meeting-preferences update-sites` (Update Default Site)

| Option | Description |
|--------|-------------|
| `--site-url URL` | URL of the site to set as default |
| `--default-site / --no-default-site` | Whether to set this as the default site (must be `true`) |

#### `meeting-preferences update-personal-meeting-room` (PMR Options)

| Option | Description |
|--------|-------------|
| `--topic TEXT` | PMR meeting topic/title |
| `--host-pin TEXT` | Host PIN |
| `--enabled-auto-lock / --no-enabled-auto-lock` | Auto-lock after host joins |
| `--auto-lock-minutes N` | Minutes after host joins to auto-lock (0, 5, 10, 15, 20) |
| `--enabled-notify-host / --no-enabled-notify-host` | Notify host when someone waits in lobby |
| `--support-co-host / --no-support-co-host` | Enable co-host capability |
| `--support-anyone-as-co-host / --no-support-anyone-as-co-host` | Allow any attendee to become co-host |
| `--allow-first-user-to-be-co-host / --no-allow-first-user-to-be-co-host` | First user to join becomes co-host |
| `--allow-authenticated-devices / --no-allow-authenticated-devices` | Allow authenticated video devices |
| `--json-body JSON` | Full JSON body (required for `coHosts` array) |

#### `meeting-preferences create-refresh-id` (Batch Refresh PMR IDs)

| Option | Description |
|--------|-------------|
| `--json-body JSON` | Required: `{"siteUrl": "site.webex.com", "personalMeetingRoomIds": [{"email": "user@example.com", "personalMeetingRoomId": "newId", "systemGenerated": true}]}` |

### Raw HTTP

```python
import requests

BASE = "https://webexapis.com/v1"
headers = {"Authorization": "Bearer TOKEN", "Content-Type": "application/json"}

# Get all meeting preferences
resp = requests.get(f"{BASE}/meetingPreferences",
                    headers=headers, params={"userEmail": "user@example.com"})
prefs = resp.json()
# Returns: {personalMeetingRoom, audio, video, schedulingOptions, sites, ...}

# Get audio options
resp = requests.get(f"{BASE}/meetingPreferences/audio", headers=headers)
audio = resp.json()
# Returns: {defaultAudioType, enabledTollFree, enabledGlobalCallIn, officeNumber, mobileNumber, ...}

# Update audio options
body = {
    "defaultAudioType": "voipOnly",
    "enabledTollFree": True,
    "enabledGlobalCallIn": True,
    "enabledAutoConnection": False
}
resp = requests.put(f"{BASE}/meetingPreferences/audio", headers=headers, json=body)

# Get video options
resp = requests.get(f"{BASE}/meetingPreferences/video", headers=headers)
# Returns: {videoDevices: [{deviceName, deviceAddress, isDefault}]}

# Get scheduling options
resp = requests.get(f"{BASE}/meetingPreferences/schedulingOptions", headers=headers)
# Returns: {enabledJoinBeforeHost, joinBeforeHostMinutes, enabledAutoShareRecording, delegateEmails, ...}

# Insert delegate emails
body = {"emails": ["delegate1@example.com", "delegate2@example.com"]}
resp = requests.post(f"{BASE}/meetingPreferences/schedulingOptions/delegateEmails/insert",
                     headers=headers, json=body)

# Delete delegate emails
body = {"emails": ["delegate1@example.com"]}
resp = requests.post(f"{BASE}/meetingPreferences/schedulingOptions/delegateEmails/delete",
                     headers=headers, json=body)
# Returns: 204 No Content

# Get site list
resp = requests.get(f"{BASE}/meetingPreferences/sites", headers=headers)
# Returns: {sites: [{siteUrl, default}]}

# Update default site
body = {"siteUrl": "mysite.webex.com"}
resp = requests.put(f"{BASE}/meetingPreferences/sites",
                    headers=headers, json=body, params={"defaultSite": "true"})

# Get PMR options
resp = requests.get(f"{BASE}/meetingPreferences/personalMeetingRoom", headers=headers)
# Returns: {topic, hostPin, personalMeetingRoomLink, sipAddress, telephony, coHosts, ...}

# Update PMR options
body = {
    "topic": "Weekly Standup",
    "hostPin": "123456",
    "enabledAutoLock": True,
    "autoLockMinutes": 5,
    "supportCoHost": True
}
resp = requests.put(f"{BASE}/meetingPreferences/personalMeetingRoom", headers=headers, json=body)

# Batch refresh PMR IDs (admin only)
body = {
    "siteUrl": "mysite.webex.com",
    "personalMeetingRoomIds": [
        {"email": "user1@example.com", "personalMeetingRoomId": "newpmr1", "systemGenerated": False},
        {"email": "user2@example.com", "systemGenerated": True}
    ]
}
resp = requests.post(f"{BASE}/admin/meetingPreferences/personalMeetingRoom/refreshId",
                     headers=headers, json=body)
```

---

## 2. Session Types

**CLI group:** `meeting-session-types`
**API base:** `https://webexapis.com/v1/admin/meeting/config/sessionTypes` (site) and `.../userconfig/sessionTypes` (user)

Session types define meeting capabilities (MeetingCenter, EventCenter, TrainingCenter, SupportCenter, webinar, etc.) available at the site level and assigned to individual users. All session type endpoints are admin-only.

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| List site session types | `wxcli meeting-session-types list` | GET /admin/meeting/config/sessionTypes | List session types available for a site |
| List user session types | `wxcli meeting-session-types list-session-types` | GET /admin/meeting/userconfig/sessionTypes | List session types assigned to a user |
| Update user session types | `wxcli meeting-session-types update` | PUT /admin/meeting/userconfig/sessionTypes | Assign session types to a user |

### Key Parameters

#### `meeting-session-types list` (Site Session Types)

| Option | Description |
|--------|-------------|
| `--site-url URL` | URL of the Webex site. Defaults to admin's default site |

#### `meeting-session-types list-session-types` (User Session Types)

| Option | Description |
|--------|-------------|
| `--site-url URL` | URL of the Webex site |
| `--person-id ID` | Unique identifier for the user |
| `--email EMAIL` | Email of the user (passed as header) |

#### `meeting-session-types update` (Update User Session Types)

| Option | Description |
|--------|-------------|
| `--json-body JSON` | Required: `{"personId": "...", "email": "user@example.com", "siteUrl": "site.webex.com", "sessionTypeIds": ["1", "3", "120"]}` |

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"

# List site session types
resp = requests.get(f"{BASE}/admin/meeting/config/sessionTypes",
                    headers=headers, params={"siteUrl": "mysite.webex.com"})
session_types = resp.json().get("items", [])
# Each item: {id, name, shortName, type, siteUrl}
# type values: "meeting", "privateMeeting", "TrainCenter", "EventCenter", "SupportCenter", "webinar"

# List user session types
resp = requests.get(f"{BASE}/admin/meeting/userconfig/sessionTypes",
                    headers=headers,
                    params={"siteUrl": "mysite.webex.com", "personId": "PERSON_ID"})
user_types = resp.json().get("items", [])
# Each item: {personId, email, siteUrl, sessionTypes: [{id, name, shortName, type}]}

# Update user session types
body = {
    "personId": "PERSON_ID",
    "email": "user@example.com",
    "siteUrl": "mysite.webex.com",
    "sessionTypeIds": ["1", "3", "120"]
}
resp = requests.put(f"{BASE}/admin/meeting/userconfig/sessionTypes",
                    headers=headers, json=body)
```

---

## 3. Tracking Codes

**CLI group:** `meeting-tracking-codes`
**API base:** `https://webexapis.com/v1/admin/meeting/config/trackingCodes` (site-level) and `.../userconfig/trackingCodes` (user-level)

Tracking codes are custom metadata fields (e.g., department, project, cost center) that admins attach to meetings for reporting and compliance. Site-level tracking codes define the schema; user-level tracking codes set default values per user. All endpoints are admin-only.

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| List tracking codes | `wxcli meeting-tracking-codes list` | GET /admin/meeting/config/trackingCodes | List site-level tracking code definitions |
| Create tracking code | `wxcli meeting-tracking-codes create` | POST /admin/meeting/config/trackingCodes | Create a new tracking code definition |
| Get tracking code | `wxcli meeting-tracking-codes show TRACKING_CODE_ID` | GET /admin/meeting/config/trackingCodes/{trackingCodeId} | Get a specific tracking code |
| Update tracking code | `wxcli meeting-tracking-codes update-tracking-codes TRACKING_CODE_ID` | PUT /admin/meeting/config/trackingCodes/{trackingCodeId} | Update a tracking code definition |
| Delete tracking code | `wxcli meeting-tracking-codes delete TRACKING_CODE_ID` | DELETE /admin/meeting/config/trackingCodes/{trackingCodeId} | Delete a tracking code |
| Get user tracking codes | `wxcli meeting-tracking-codes list-tracking-codes` | GET /admin/meeting/userconfig/trackingCodes | Get tracking code values for a user |
| Update user tracking codes | `wxcli meeting-tracking-codes update` | PUT /admin/meeting/userconfig/trackingCodes | Set tracking code values for a user |

### Key Parameters

#### `meeting-tracking-codes list` (Site Tracking Codes)

| Option | Description |
|--------|-------------|
| `--site-url URL` | URL of the Webex site. Defaults to admin's preferred site |

#### `meeting-tracking-codes create` (Create Tracking Code)

| Option | Description |
|--------|-------------|
| `--json-body JSON` | Required. See example below |

Create body example:
```json
{
  "name": "Department",
  "siteUrl": "mysite.webex.com",
  "inputMode": "select",
  "hostProfileCode": "optional",
  "scheduleStartCodes": [
    {"service": "MeetingCenter", "type": "required"},
    {"service": "EventCenter", "type": "optional"}
  ],
  "options": [
    {"value": "Engineering", "defaultValue": false},
    {"value": "Sales", "defaultValue": true}
  ]
}
```

**`inputMode` values:** `text`, `select`, `editableSelect`, `hostProfileSelect`
**`hostProfileCode` values:** `optional`, `required`, `notUsed`, `adminSet`
**`scheduleStartCodes` type values:** `optional`, `required`, `notUsed`, `notApplicable`, `adminSet`

#### `meeting-tracking-codes show` / `meeting-tracking-codes delete`

| Option | Description |
|--------|-------------|
| `TRACKING_CODE_ID` | Positional argument -- the tracking code ID |
| `--site-url URL` | URL of the Webex site |

#### `meeting-tracking-codes list-tracking-codes` (User Tracking Codes)

| Option | Description |
|--------|-------------|
| `--site-url URL` | URL of the Webex site |
| `--person-id ID` | User's person ID (at least one of personId or email required) |
| `--email EMAIL` | User's email (passed as header) |

#### `meeting-tracking-codes update` (Update User Tracking Codes)

| Option | Description |
|--------|-------------|
| `--json-body JSON` | Required: `{"personId": "...", "email": "user@example.com", "siteUrl": "site.webex.com", "trackingCodes": [{"name": "Department", "value": "Engineering"}]}` |

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"

# List site tracking codes
resp = requests.get(f"{BASE}/admin/meeting/config/trackingCodes",
                    headers=headers, params={"siteUrl": "mysite.webex.com"})
codes = resp.json().get("items", [])
# Each item: {id, name, siteUrl, inputMode, hostProfileCode, scheduleStartCodes, options}

# Create tracking code
body = {
    "name": "CostCenter",
    "siteUrl": "mysite.webex.com",
    "inputMode": "select",
    "hostProfileCode": "optional",
    "scheduleStartCodes": [{"service": "MeetingCenter", "type": "required"}],
    "options": [{"value": "CC100", "defaultValue": True}, {"value": "CC200", "defaultValue": False}]
}
resp = requests.post(f"{BASE}/admin/meeting/config/trackingCodes", headers=headers, json=body)

# Get a specific tracking code
resp = requests.get(f"{BASE}/admin/meeting/config/trackingCodes/{tracking_code_id}",
                    headers=headers, params={"siteUrl": "mysite.webex.com"})

# Delete a tracking code
resp = requests.delete(f"{BASE}/admin/meeting/config/trackingCodes/{tracking_code_id}",
                       headers=headers)

# Get user tracking codes
resp = requests.get(f"{BASE}/admin/meeting/userconfig/trackingCodes",
                    headers=headers,
                    params={"siteUrl": "mysite.webex.com", "personId": "PERSON_ID"})
# Returns: {personId, email, siteUrl, trackingCodes: [{name, id, value}]}

# Update user tracking codes
body = {
    "personId": "PERSON_ID",
    "email": "user@example.com",
    "siteUrl": "mysite.webex.com",
    "trackingCodes": [
        {"name": "Department", "value": "Engineering"},
        {"name": "CostCenter", "value": "CC100"}
    ]
}
resp = requests.put(f"{BASE}/admin/meeting/userconfig/trackingCodes",
                    headers=headers, json=body)
```

---

## 4. Site Settings

**CLI group:** `meeting-site`
**API base:** `https://webexapis.com/v1/admin/meeting/config/commonSettings`

Site-level common settings control security policies, scheduler defaults, telephony configuration, and meeting scheduling options for an entire Webex site. Admin-only. The update endpoint uses PATCH (partial update semantics) rather than PUT.

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| Get site settings | `wxcli meeting-site show` | GET /admin/meeting/config/commonSettings | Get meeting common settings for a site |
| Update site settings | `wxcli meeting-site update` | PATCH /admin/meeting/config/commonSettings | Partially update meeting common settings |

### Key Parameters

#### `meeting-site show`

| Option | Description |
|--------|-------------|
| `--site-url URL` | URL of the Webex site. Required |

#### `meeting-site update`

| Option | Description |
|--------|-------------|
| `--json-body JSON` | Required for nested settings structure. See example below |

Update body example (all fields optional -- PATCH semantics):
```json
{
  "siteOptions": {
    "allowCustomPersonalRoomURL": true
  },
  "defaultSchedulerOptions": {
    "VoIP": true,
    "telephonySupport": "CallInAndCallBack",
    "joinTeleconfNotPress1": false,
    "entryAndExitTone": "Beep",
    "tollFree": true
  },
  "securityOptions": {
    "joinBeforeHost": true,
    "audioBeforeHost": false,
    "firstAttendeeAsPresenter": false,
    "unlistAllMeetings": false,
    "requireLoginBeforeAccess": true,
    "allowMobileScreenCapture": true,
    "requireStrongPassword": true,
    "passwordCriteria": {
      "minLength": 8,
      "minNumeric": 1,
      "minAlpha": 1,
      "minSpecial": 1,
      "mixedCase": true
    }
  },
  "scheduleMeetingOptions": {
    "emailReminders": true
  }
}
```

**`telephonySupport` values:** `None`, `CallInOnly`, `CallInAndCallBack`
**`entryAndExitTone` values:** `Beep`, `AnnounceNameOnly`, `AnnounceNameAndTone`, `NoTone`

The GET response includes an additional read-only `telephonyConfig` object with: `allowCallIn`, `allowCallBack`, `allowOtherTeleconf`, `allowTollFreeCallin`, `allowInternationalCallin`, `allowInternationalCallback`, `VoIP`.

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"

# Get site common settings
resp = requests.get(f"{BASE}/admin/meeting/config/commonSettings",
                    headers=headers, params={"siteUrl": "mysite.webex.com"})
settings = resp.json()
# Returns: {siteOptions, defaultSchedulerOptions, telephonyConfig, securityOptions, scheduleMeetingOptions}

# Update site settings (PATCH -- partial update)
body = {
    "securityOptions": {
        "requireStrongPassword": True,
        "passwordCriteria": {"minLength": 10, "minSpecial": 1}
    }
}
resp = requests.patch(f"{BASE}/admin/meeting/config/commonSettings",
                      headers=headers, json=body,
                      params={"siteUrl": "mysite.webex.com"})
```

---

## 5. Meeting Polls

**CLI group:** `meeting-polls`
**API base:** `https://webexapis.com/v1/meetings/polls` and `.../pollResults`

Read-only access to poll data from completed meeting instances. Retrieve poll questions, answer summaries, and individual respondent answers. Polls cannot be created or modified via API -- they are created during live meetings in the Webex client.

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| List polls | `wxcli meeting-polls list-polls` | GET /meetings/polls | List polls from a meeting instance |
| Get poll results | `wxcli meeting-polls list` | GET /meetings/pollResults | Get poll results with answer summaries |
| List respondents | `wxcli meeting-polls list-respondents POLL_ID QUESTION_ID` | GET /meetings/polls/{pollId}/questions/{questionId}/respondents | List individual respondent answers |

### Key Parameters

#### `meeting-polls list-polls` (List Polls)

| Option | Description |
|--------|-------------|
| `--meeting-id ID` | Required. Meeting instance ID (ended meetings only) |

#### `meeting-polls list` (Poll Results)

| Option | Description |
|--------|-------------|
| `--meeting-id ID` | Required. Meeting instance ID |
| `--max N` | Maximum number of respondents per poll (up to 100) |

#### `meeting-polls list-respondents` (Respondents)

| Option | Description |
|--------|-------------|
| `POLL_ID` | Positional argument -- the poll ID |
| `QUESTION_ID` | Positional argument -- the question ID |
| `--meeting-id ID` | Required. Meeting instance ID |
| `--max N` | Maximum number of respondents (up to 100) |

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"

# List polls from a meeting
resp = requests.get(f"{BASE}/meetings/polls",
                    headers=headers, params={"meetingId": "MEETING_INSTANCE_ID"})
polls = resp.json().get("items", [])
# Each poll: {id, meetingId, email, displayName, personId, startTime, endTime, timerDuration,
#             questions: [{id, order, title, type, options: [{order, value, isCorrect}]}]}
# Question types: "short", "long", "singleAnswer", "multipleAnswer"

# Get poll results (includes answer summaries and respondent data)
resp = requests.get(f"{BASE}/meetings/pollResults",
                    headers=headers, params={"meetingId": "MEETING_INSTANCE_ID", "max": 50})
results = resp.json().get("items", [])
# Each result: {id, meetingId, totalAttendees, totalRespondents,
#               questions: [{id, title, type, answerSummary: [{value, totalRespondents, isCorrect}],
#                            respondents: {items: [{email, displayName, answers}]}}]}

# List respondents for a specific question
resp = requests.get(f"{BASE}/meetings/polls/{poll_id}/questions/{question_id}/respondents",
                    headers=headers, params={"meetingId": "MEETING_INSTANCE_ID", "max": 100})
respondents = resp.json().get("items", [])
# Each respondent: {email, displayName, answers: ["selected option 1", ...]}
```

---

## 6. Meeting Q&A

**CLI group:** `meeting-qa`
**API base:** `https://webexapis.com/v1/meetings/q_and_a`

Read-only access to Q&A data from completed meeting instances. Retrieve questions asked during meetings and their answers.

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| List Q&A | `wxcli meeting-qa list` | GET /meetings/q_and_a | List questions from a meeting instance |
| List answers | `wxcli meeting-qa list-answers QUESTION_ID` | GET /meetings/q_and_a/{questionId}/answers | List answers for a specific question |

### Key Parameters

#### `meeting-qa list` (List Q&A)

| Option | Description |
|--------|-------------|
| `--meeting-id ID` | Required. Meeting instance ID (ended meetings only) |
| `--max N` | Maximum number of answers (up to 100) |

#### `meeting-qa list-answers` (List Answers)

| Option | Description |
|--------|-------------|
| `QUESTION_ID` | Positional argument -- the question ID |
| `--meeting-id ID` | Required. Meeting instance ID |
| `--max N` | Maximum number of answers (up to 100) |

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"

# List Q&A from a meeting
resp = requests.get(f"{BASE}/meetings/q_and_a",
                    headers=headers, params={"meetingId": "MEETING_INSTANCE_ID", "max": 50})
questions = resp.json().get("items", [])
# Each question: {id, meetingId, question, email, displayName, totalAttendees, totalRespondents,
#                 answers: {items: [{email, displayName, personId, answer, answered}]}}

# List answers for a specific question
resp = requests.get(f"{BASE}/meetings/q_and_a/{question_id}/answers",
                    headers=headers, params={"meetingId": "MEETING_INSTANCE_ID", "max": 100})
answers = resp.json().get("items", [])
# Each answer: {email, displayName, personId, answer: ["answer text"], answered}
```

---

## 7. Meeting Reports

**CLI group:** `meeting-reports`
**API base:** `https://webexapis.com/v1/meetingReports`

Meeting usage and attendee reports for site administrators. Returns meeting statistics, participant details, and telephony usage data for a specified date range. Admin-only.

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| List usage reports | `wxcli meeting-reports list` | GET /meetingReports/usage | List meeting usage reports |
| List attendee reports | `wxcli meeting-reports list-attendees` | GET /meetingReports/attendees | List meeting attendee detail reports |

### Key Parameters

#### `meeting-reports list` (Usage Reports)

| Option | Description |
|--------|-------------|
| `--site-url URL` | URL of the Webex site (recommended) |
| `--service-type TEXT` | Filter by service: `MeetingCenter` (default), `EventCenter`, `SupportCenter`, `TrainingCenter` |
| `--from DATETIME` | Start date/time (ISO 8601). Default: 7 days before `to` |
| `--to DATETIME` | End date/time (ISO 8601). Default: current time |
| `--max N` | Page size (1-1000) |

#### `meeting-reports list-attendees` (Attendee Reports)

| Option | Description |
|--------|-------------|
| `--site-url URL` | URL of the Webex site (recommended) |
| `--meeting-id ID` | Filter to a specific ended meeting instance |
| `--meeting-number TEXT` | Filter by meeting number |
| `--meeting-title TEXT` | Filter by meeting title |
| `--from DATETIME` | Start date/time (ISO 8601). Default: 7 days before `to` |
| `--to DATETIME` | End date/time (ISO 8601). Default: current time |
| `--max N` | Page size (1-1000) |

**Date range constraints:** The interval between `from` and `to` cannot exceed 30 days. `from` cannot be earlier than 90 days ago.

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"

# List meeting usage reports
resp = requests.get(f"{BASE}/meetingReports/usage",
                    headers=headers,
                    params={
                        "siteUrl": "mysite.webex.com",
                        "serviceType": "MeetingCenter",
                        "from": "2026-03-01T00:00:00Z",
                        "to": "2026-03-28T00:00:00Z",
                        "max": 100
                    })
reports = resp.json().get("items", [])
# Each report: {meetingId, meetingNumber, meetingTitle, hostEmail, hostDisplayName,
#               scheduledType, serviceType, start, end, peakAttendee,
#               totalPeopleMinutes, totalParticipantsVoip, totalParticipantsCallIn,
#               totalParticipantsCallOut, totalCallInMinutes, totalVoipMinutes,
#               totalCallInTollFreeMinutes, totalRegistered, totalInvitee,
#               totalCallOutDomestic, totalCallOutInternational, trackingCodes}

# List attendee reports
resp = requests.get(f"{BASE}/meetingReports/attendees",
                    headers=headers,
                    params={
                        "siteUrl": "mysite.webex.com",
                        "meetingId": "MEETING_INSTANCE_ID",
                        "from": "2026-03-01T00:00:00Z",
                        "to": "2026-03-28T00:00:00Z",
                        "max": 100
                    })
attendees = resp.json().get("items", [])
# Each attendee: {meetingId, meetingNumber, meetingTitle, email, displayName,
#                 joinedTime, leftTime, duration, participantType, invited,
#                 registered, company, phoneNumber, address1, city, state,
#                 country, zipCode, clientAgent}
```

---

## 8. Slido Compliance

**CLI group:** `meeting-slido`
**API base:** `https://webexapis.com/v1/slido/compliance/events`

Read-only compliance event log for Slido interactions within Webex Meetings. Returns events such as poll responses, Q&A submissions, and session metadata for compliance and audit purposes. Requires a Slido Secure Premium license.

### Commands

| Command | CLI | HTTP Method | What It Does |
|---------|-----|------------|-------------|
| List compliance events | `wxcli meeting-slido list` | GET /slido/compliance/events | List Slido compliance events |

### Key Parameters

| Option | Description |
|--------|-------------|
| `--session-org-id ID` | Webex organization UUID |
| `--session-id ID` | Webex meeting instance ID (format: `{meetingSeriesId}_I_{conferenceId}`) |
| `--start TOKEN` | Pagination token (returned as `next` in response) |

### Raw HTTP

```python
BASE = "https://webexapis.com/v1"

# List Slido compliance events
resp = requests.get(f"{BASE}/slido/compliance/events",
                    headers=headers,
                    params={"sessionOrgId": "ORG_UUID", "sessionId": "MEETING_INSTANCE_ID"})
events = resp.json()
# Returns: {next, items: [{userId, sessionOrgId, sessionId, createdAtMs,
#                          data: {type, sessionId, anonymityEnabled, createdAtMs, modifiedAtMs, isDeleted}}]}
# Event data types: "session", "poll", "question", "answer", "reply", etc.

# Paginate through events
next_token = events.get("next")
if next_token:
    resp = requests.get(f"{BASE}/slido/compliance/events",
                        headers=headers,
                        params={"sessionOrgId": "ORG_UUID", "start": next_token})
```

---

## 9. Raw HTTP Endpoints

All 34 endpoints across the 8 CLI groups, for quick reference.

| # | Method | Path | CLI Group | CLI Command | Description |
|---|--------|------|-----------|-------------|-------------|
| 1 | GET | /meetingPreferences | meeting-preferences | `list-meeting-preferences` | Get all meeting preferences |
| 2 | GET | /meetingPreferences/audio | meeting-preferences | `show` | Get audio options |
| 3 | PUT | /meetingPreferences/audio | meeting-preferences | `update` | Update audio options |
| 4 | GET | /meetingPreferences/video | meeting-preferences | `list` | Get video options |
| 5 | PUT | /meetingPreferences/video | meeting-preferences | `update-video` | Update video options |
| 6 | GET | /meetingPreferences/schedulingOptions | meeting-preferences | `list-scheduling-options` | Get scheduling options |
| 7 | PUT | /meetingPreferences/schedulingOptions | meeting-preferences | `update-scheduling-options` | Update scheduling options |
| 8 | POST | /meetingPreferences/schedulingOptions/delegateEmails/insert | meeting-preferences | `create-insert` | Insert delegate emails |
| 9 | POST | /meetingPreferences/schedulingOptions/delegateEmails/delete | meeting-preferences | `create` | Delete delegate emails |
| 10 | GET | /meetingPreferences/sites | meeting-preferences | `list-sites` | Get site list |
| 11 | PUT | /meetingPreferences/sites | meeting-preferences | `update-sites` | Update default site |
| 12 | GET | /meetingPreferences/personalMeetingRoom | meeting-preferences | `list-personal-meeting-room` | Get PMR options |
| 13 | PUT | /meetingPreferences/personalMeetingRoom | meeting-preferences | `update-personal-meeting-room` | Update PMR options |
| 14 | POST | /admin/meetingPreferences/personalMeetingRoom/refreshId | meeting-preferences | `create-refresh-id` | Batch refresh PMR IDs |
| 15 | GET | /admin/meeting/config/sessionTypes | meeting-session-types | `list` | List site session types |
| 16 | GET | /admin/meeting/userconfig/sessionTypes | meeting-session-types | `list-session-types` | List user session types |
| 17 | PUT | /admin/meeting/userconfig/sessionTypes | meeting-session-types | `update` | Update user session types |
| 18 | GET | /admin/meeting/config/trackingCodes | meeting-tracking-codes | `list` | List site tracking codes |
| 19 | POST | /admin/meeting/config/trackingCodes | meeting-tracking-codes | `create` | Create tracking code |
| 20 | GET | /admin/meeting/config/trackingCodes/{trackingCodeId} | meeting-tracking-codes | `show` | Get tracking code |
| 21 | PUT | /admin/meeting/config/trackingCodes/{trackingCodeId} | meeting-tracking-codes | `update-tracking-codes` | Update tracking code |
| 22 | DELETE | /admin/meeting/config/trackingCodes/{trackingCodeId} | meeting-tracking-codes | `delete` | Delete tracking code |
| 23 | GET | /admin/meeting/userconfig/trackingCodes | meeting-tracking-codes | `list-tracking-codes` | Get user tracking codes |
| 24 | PUT | /admin/meeting/userconfig/trackingCodes | meeting-tracking-codes | `update` | Update user tracking codes |
| 25 | GET | /admin/meeting/config/commonSettings | meeting-site | `show` | Get site common settings |
| 26 | PATCH | /admin/meeting/config/commonSettings | meeting-site | `update` | Update site common settings |
| 27 | GET | /meetings/polls | meeting-polls | `list-polls` | List meeting polls |
| 28 | GET | /meetings/pollResults | meeting-polls | `list` | Get meeting poll results |
| 29 | GET | /meetings/polls/{pollId}/questions/{questionId}/respondents | meeting-polls | `list-respondents` | List poll respondents |
| 30 | GET | /meetings/q_and_a | meeting-qa | `list` | List meeting Q&A |
| 31 | GET | /meetings/q_and_a/{questionId}/answers | meeting-qa | `list-answers` | List Q&A answers |
| 32 | GET | /meetingReports/usage | meeting-reports | `list` | List usage reports |
| 33 | GET | /meetingReports/attendees | meeting-reports | `list-attendees` | List attendee reports |
| 34 | GET | /slido/compliance/events | meeting-slido | `list` | List Slido compliance events |

---

## 10. Gotchas

1. **Preferences endpoints default to the authenticated user.** Pass `--user-email` to act on behalf of another user. This requires admin-level scopes (`meeting:admin_preferences_read`, `meeting:admin_preferences_write`). Without admin scopes, the parameter is silently ignored and the API operates on the caller.

2. **`create` in meeting-preferences actually deletes delegate emails.** The CLI command `wxcli meeting-preferences create` maps to `POST /meetingPreferences/schedulingOptions/delegateEmails/delete`. This is a confusing auto-generated name because the generator maps all POST endpoints to `create`. To add delegates, use `create-insert` instead.

3. **`create-refresh-id` is an admin-only batch endpoint.** It lives under `/admin/meetingPreferences/...` and refreshes PMR IDs for multiple users at once. Requires an admin token. The `personalMeetingRoomId` field in the request can be set to a custom value, or `systemGenerated: true` will auto-generate a new ID.

4. **Session types and tracking codes are admin-only.** All endpoints under `/admin/meeting/config/` and `/admin/meeting/userconfig/` require admin-level scopes. User tokens return 403.

5. **Site settings use PATCH not PUT.** The `meeting-site update` command sends a PATCH request, meaning you only need to include the fields you want to change. Other fields are preserved. This differs from most Webex API update endpoints which use PUT (full replacement).

6. **Poll and Q&A data are read-only.** You can retrieve poll results and Q&A content after a meeting ends, but you cannot create, modify, or delete polls or Q&A via the API. Polls are created in the Webex client during a live meeting.

7. **Reports require `siteUrl` in practice.** While `siteUrl` is technically optional for reports, omitting it defaults to the admin's default site, which may not be the site you want to query. Always specify `siteUrl` for predictable results.

8. **Report date range is capped at 30 days, max 90 days ago.** The interval between `from` and `to` cannot exceed 30 days, and `from` cannot be earlier than 90 days before the current date. For longer historical queries, make multiple requests with sliding date windows.

9. **Slido compliance events require Slido Secure Premium license.** Without this license, the endpoint returns 403. The `sessionId` format is `{meetingSeriesId}_I_{conferenceId}`, not a standard Webex meeting ID.

10. **Tracking codes can be mapped (one-way migration).** Admins can switch a site from classic tracking codes to mapped tracking codes in Control Hub. This is a one-time irreversible operation. After mapping, the tracking codes API returns mapped attributes, and create/update operations are blocked during or after the mapping process.

11. **User session types and tracking codes use `email` as a header, not a query parameter.** The `email` parameter for `/admin/meeting/userconfig/sessionTypes` and `/admin/meeting/userconfig/trackingCodes` is passed as a request header, not a query string parameter. The CLI handles this correctly, but when making raw HTTP calls, set the `email` header explicitly.

12. **`meetingId` for polls, Q&A, and attendee reports must be an ended meeting instance ID.** Meeting series IDs, scheduled meeting IDs, and personal room meeting IDs are not supported. Only IDs of completed (ended) meeting instances work.

---

## 11. See Also

- [`meetings-core.md`](meetings-core.md) — Meeting CRUD, templates, controls, registrants, interpreters, breakouts, surveys
- [`meetings-content.md`](meetings-content.md) — Transcripts, captions, chats, summaries, meeting messages
- [`meetings-infrastructure.md`](meetings-infrastructure.md) — Video Mesh (clusters, nodes, health, utilization), participants, invitees
- [`authentication.md`](authentication.md) -- Token types, scopes, OAuth flows (meeting-specific admin scopes: `meeting:admin_preferences_read/write`, `meeting:admin_config_read/write`)
- [`reporting-analytics.md`](reporting-analytics.md) -- CDR, call quality, and queue statistics (Webex Calling reports, complementary to meeting reports)
