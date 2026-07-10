# People & Settings Domain

**Covers:** User lookups, call settings audits (voicemail, forwarding, DND, recording, caller ID, permissions, executive-assistant pairing).

## Question Patterns

| Pattern | Example |
|---------|---------|
| User lookup | "Show me users at Austin", "Find John Smith" |
| Setting check (single user) | "Does John have voicemail enabled?", "Show me Jane's call forwarding" |
| Setting audit (bulk) | "Which users at Austin don't have voicemail?", "Who has DND turned on?" |
| Recording audit | "Show me everyone whose calls are being recorded" |
| Executive-assistant | "Which users have executive-assistant pairing?" |
| Comparison | "What's different about John's settings vs Jane's?" |

## Command Recipes

### List users (org-wide or filtered)
```bash
wxcli people list -o json
wxcli people list --location-id LOCATION_ID -o json
wxcli people list --display-name "John Smith" -o json
wxcli people list --email "john@example.com" -o json
```

### Show a specific user
```bash
wxcli people show PERSON_ID -o json
```

### Voicemail settings
```bash
wxcli user-settings show-voicemail PERSON_ID -o json
```
Response includes: `enabled`, `sendBusyCalls`, `sendUnansweredCalls`, `emailCopyOfMessage`, `messageStorage`, `notifications`.

### Call forwarding settings
```bash
wxcli user-settings show-call-forwarding PERSON_ID -o json
```
Response includes 4 blocks: `always`, `busy`, `noAnswer`, `businessContinuity`. Each has `enabled` and `destination`.

### Call recording settings
```bash
wxcli user-settings show-call-recording PERSON_ID -o json
```
Response includes: `enabled`, `record` (Always/Never/Always with Pause/On Demand), `startStopAnnouncement`.

### Do Not Disturb
```bash
wxcli user-settings show-do-not-disturb PERSON_ID -o json
```
Response includes: `enabled`, `ringSplashEnabled`.

### Caller ID
```bash
wxcli user-settings show-caller-id PERSON_ID -o json
```

### Executive-assistant pairing
```bash
wxcli user-settings show-executive-assistant PERSON_ID -o json
```
Response includes: `type` (UNASSIGNED, EXECUTIVE, or EXECUTIVE_ASSISTANT).

### Call intercept
```bash
wxcli user-settings show-intercept PERSON_ID -o json
```

### Barge-in
```bash
wxcli user-settings show-barge-in PERSON_ID -o json
```

### Call waiting
```bash
wxcli user-settings show-call-waiting PERSON_ID -o json
```

### Hoteling
```bash
wxcli user-settings show-hoteling PERSON_ID -o json
```

## Resolution Rules

**Finding a person by name:**
1. `wxcli people list --display-name "John Smith" -o json`
2. If exact match → use it. If multiple → disambiguate by location/email.
3. If no results → try partial: `wxcli people list --display-name "John" -o json`

**Finding users at a location by name:**
1. `wxcli locations list -o json` → search for location name → get ID
2. `wxcli people list --location-id <locationId> -o json`

## Join Patterns

**Audit query** ("Which users at Austin don't have voicemail?"):
1. Resolve location name → ID: `wxcli locations list -o json`
2. List users at location: `wxcli people list --location-id <locationId> -o json`
3. For each user, fetch setting: `wxcli user-settings show-voicemail <personId> -o json`
4. Filter to matches (enabled=false or missing)
5. Format as audit table

**Comparison query** ("Compare John's settings vs Jane's"):
1. Resolve both names to person IDs
2. Fetch the same setting(s) for both
3. Present side-by-side with differences highlighted

## Response Guidance

**Single-user setting check:**
```
John Smith has voicemail enabled.
  - Send busy calls to voicemail: Yes
  - Send unanswered calls after 3 rings: Yes
  - Email copy to: john.smith@acme.com
  - Greeting: Custom
```

**Bulk audit:**
```
12 of 45 users at Austin don't have voicemail enabled:
  - Alice Johnson (ext 3001)
  - Brian Kim (ext 3002)
  - Carol Davis (ext 3003)
  ... and 9 more

Note: I checked all 45 Webex Calling-licensed users at the Austin location.
```

**Executive-assistant pairing:**
```
3 executive-assistant pairings found:
  - Jane Smith (Executive) ↔ Alice Johnson (Assistant)
  - Bob Lee (Executive) ↔ Carol Davis (Assistant)
  - Tom Chen (Executive) ↔ Maria Garcia (Assistant)
```

## Gotchas

1. **6 person settings are user-only (no admin path).** If a setting returns 404 with error 4008, it requires user-level OAuth. Report: "This setting can only be viewed by the user themselves, not by an admin."
2. **Two path families for person settings.** The CLI abstracts this — use `wxcli user-settings` commands and they route to the correct path. No need to worry about `/people/{id}/features/` vs `/telephony/config/people/{id}/`.
3. **Workspace settings differ from person settings.** Basic workspaces return 405 for most `/telephony/config/` settings. If a workspace query fails with 405, report: "This workspace has a Basic license — only DND and Music on Hold settings are available."
4. **Large org batching.** For orgs with 100+ users, batch settings checks and provide progress updates. Don't try to fetch all settings in a single burst.
