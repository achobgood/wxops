# WxCC Provisioning API — Programmatic Resource Creation

<!-- ref-tag: wxcc-provisioning-v2 -->

The WxCC Provisioning API creates Contact Center resources (teams, queues, business hours, entry points) that the Flow Store API cannot. Use these patterns when building flows programmatically — the flow needs queues and business hours to exist before it can reference them.

**Base URL:** `https://api.wxcc-us1.cisco.com` (US1 region)
**Auth:** `Authorization: Bearer <token>` — a Webex access token. `wxcli` is the one tool for both provisioning and flow authoring, so it uses one token — see Trap 1 below.

## Before Anything Else — Two Traps That Break Every Command

Both traps cause total failure before any recipe below can work. Check them first.

### Trap 1: One Tool, One Token

`wxcli` is the one tool for Control Hub / Contact Center provisioning (the `cc-*` groups) and for flow authoring (the `cc-flow*` and `cc-functions` groups). It resolves one token for all of them: the `WEBEX_ACCESS_TOKEN` environment variable, then `WEBEX_TOKEN`, then `profiles.default.token` in `~/.wxcli/config.json`. Claude runs `wxcli configure`; you paste the token at its prompt.

History: before the two tools were merged, wxcc's separate flow tool (wxcc-flow) kept its token in its own config file, with its own environment-variable order, and the two tools held different tokens (verified 2026-07-25: the SHA-256 fingerprints of the two token strings differed). That is why a 401 used to mean refreshing that one tool's own token. With one tool and one token, a 401 means the one token expired: Claude runs `wxcli configure` again and you paste a fresh one.

**Region:** `wxcli` resolves its region from `profiles.default.cc_region` in `~/.wxcli/config.json` (default `us1`). `wxcli set-cc-region` offers 7 values: `us1`, `eu1`, `eu2`, `anz1`, `ca1`, `jp1`, `sg1` — the same 7 region codes Cisco's Salesforce-integration help page lists (fetched 2026-10-19); India (`in1`) resolves in DNS but no Cisco page read names the code, and `wxcli` does not offer it [owner: `contact-center-core.md` § API Base and Authentication]. All 8 gateways resolve in DNS (2026-10-19); only `us1` has been used live. (Before 2026-10-19 this line said "The valid values in `CC_REGIONS` are `us1`, `eu1`, and `eu2`".) `us1` corresponds to the `https://api.wxcc-us1.cisco.com` base URL used throughout this doc — verified working live on 2026-07-25.

### Trap 2: A Stale `switch-org` Target Makes Every `cc-*` Command Return 403

A `403` on any `wxcli cc-*` command with a valid, unexpired token is a **targeting** problem, not a permissions problem and not a token problem.

`wxcli switch-org` sets a persistent target org. If that target is a different org from the one hosting your Contact Center, every `cc-*` call is issued against the wrong org and the API rejects it — while presenting the failure as "access denied".

Verified sequence (2026-07-25):

1. `wxcli whoami` printed all three of these at once:
   - `Org: …<your-org-id>` — the user's own org
   - `Target: …<other-org-id>` — a **different** org, set earlier with `wxcli switch-org`
   - `Token: expires in 11h 59m` — the token was valid
2. `wxcli cc-site list -o json` → `403`:
   ```json
   {"error":{"key":"403","reason":"Access denied - Client is forbidden access to the resource"}}
   ```
3. A direct `curl` with the SAME token against the correct org returned **HTTP 200**:
   ```
   GET https://api.wxcc-us1.cisco.com/organization/<your-org-id>/site?page=0&pageSize=3
   ```
   It returned `Site-1` (`<site-id>`, `systemDefault: true`). This isolates the cause to the target-org setting — not the token, not the endpoint.
4. `wxcli clear-org` → "Cleared target org. Commands will now target your own organization."
5. `wxcli cc-site list -o json` → 200. `wxcli cc-queue list` then returned 13 queues.

**Diagnostic:** on a 403 from any `cc-*` command, run `wxcli whoami` and compare the `Target:` line to the `Org:` line. If `Target:` names a different org than the one hosting your Contact Center, that is the cause — the token was never the issue.

**Fix:** run `wxcli clear-org` to go back to targeting your own org, or `wxcli switch-org <correct-org-id>` if the Contact Center lives elsewhere. In this environment the Contact Center is in the user's own org, so `clear-org` is the correct fix.

## Discover Existing Resources

Before creating new resources, check what exists. Use `wxcli` or direct API calls:

```bash
wxcli cc-site list          # Sites
wxcli cc-team list          # Teams
wxcli cc-queue list         # Queues
wxcli cc-business-hour list # Business Hours
wxcli cc-entry-point list   # Entry Points
wxcli cc-global-vars list   # Global Variables (use -o json for UUIDs)
```

## Create a Team

```bash
curl -s -X POST "https://api.wxcc-us1.cisco.com/organization/{orgId}/team" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "MyTeam",
    "siteId": "<site-uuid>",
    "teamType": "AGENT",
    "teamStatus": "IN_SERVICE",
    "active": true
  }'
```

| Field | Required | Notes |
|-------|----------|-------|
| `name` | Yes | Team name |
| `siteId` | Yes | UUID of the site (from `wxcli cc-site list`) |
| `teamType` | Yes | `AGENT` or `CAPACITY` |
| `teamStatus` | Yes | `IN_SERVICE` — omitting causes 409 error |
| `active` | Yes | `true` or `false` — omitting causes 400 error |

## Create a Queue

Queues require many fields that are not obvious from the API docs. Copy the structure below and customize.

```bash
curl -s -X POST "https://api.wxcc-us1.cisco.com/organization/{orgId}/contact-service-queue" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "MyQueue",
    "queueType": "INBOUND",
    "channelType": "TELEPHONY",
    "routingType": "LONGEST_AVAILABLE_AGENT",
    "queueRoutingType": "TEAM_BASED",
    "serviceLevelThreshold": 60,
    "maxTimeInQueue": 3600,
    "maxActiveContacts": 0,
    "checkAgentAvailability": false,
    "active": true,
    "parkingPermitted": false,
    "recordingPermitted": false,
    "monitoringPermitted": true,
    "recordingAllCallsPermitted": false,
    "pauseRecordingPermitted": true,
    "recordingPauseDuration": 10,
    "defaultMusicInQueueMediaFileId": "<music-file-uuid>",
    "callDistributionGroups": [
      {
        "agentGroups": [{"teamId": "<team-uuid>"}],
        "order": 1,
        "duration": 0
      }
    ]
  }'
```

| Field | Required | Notes |
|-------|----------|-------|
| `name` | Yes | Queue name |
| `queueType` | Yes | `INBOUND` or `OUTBOUND` |
| `channelType` | Yes | `TELEPHONY`, `EMAIL`, `CHAT`, `SOCIAL_CHANNEL`, etc. |
| `routingType` | Yes | `LONGEST_AVAILABLE_AGENT`, `SKILLS_BASED`, `CIRCULAR`, `LINEAR` — the server's own list in a 400, verified live 2026-10-19 (`SKILL_BASED` is rejected here) [owner: `contact-center-core.md` § 6 Queues, Key Parameters] |
| `queueRoutingType` | Yes | `TEAM_BASED`, `SKILL_BASED`, `AGENT_BASED` (from `--help`; `TEAM_BASED` verified live 2026-10-19, the other two not sent) [owner: `contact-center-core.md` § 6 Queues, Key Parameters] |
| `serviceLevelThreshold` | Yes | Seconds — SLA target for queue |
| `maxTimeInQueue` | Yes | Seconds — max wait before overflow |
| `maxActiveContacts` | Yes | `0` = unlimited |
| `checkAgentAvailability` | Yes | Boolean |
| `active` | Yes | Boolean |
| `parkingPermitted` | Yes | Boolean — 400 error if omitted |
| `recordingPermitted` | Yes | Boolean — 400 error if omitted |
| `monitoringPermitted` | Yes | Boolean — 400 error if omitted |
| `recordingAllCallsPermitted` | Yes | Boolean — 400 error if omitted |
| `pauseRecordingPermitted` | Yes | Boolean — 400 error if omitted |
| `recordingPauseDuration` | Yes when `pauseRecordingPermitted` is `true` | Integer seconds. Verified live 2026-10-19: omitting it with `pauseRecordingPermitted: true` → 400 `recordingPauseDuration: invalid value`; `10` (the system `Queue-1` value) accepted. With `false` it was not tried. (Before 2026-10-19 this row said "No — default 10".) |
| `defaultMusicInQueueMediaFileId` | Yes | UUID of hold music audio file — 400 error if omitted. Get from an existing queue. |
| `callDistributionGroups` | Yes | At least one CDG with at least one `teamId`. 400 error if omitted. Each CDG's `order` must be **greater than 0**: verified live 2026-10-19, `0` → 400 `callDistributionGroups[].order: should be a value greater than 0 (zero).`, `1` accepted and read back as `1` (values above 1 not tried) |

The required set above was measured on a `TELEPHONY` queue on 2026-10-19: the five `*Permitted` booleans, `defaultMusicInQueueMediaFileId`, and `recordingPauseDuration` (with `pauseRecordingPermitted: true`) are all demanded by the server although `--help` does not mark them required. Whether an `EMAIL` or `SOCIAL_CHANNEL` queue needs the same fields was not tested (on the sandbox those queues store `defaultMusicInQueueMediaFileId: null`) [owner: `contact-center-core.md` § 25 Gotchas, gotcha 27].

**Getting the music file UUID:** Query an existing queue: `curl -s "https://api.wxcc-us1.cisco.com/organization/{orgId}/contact-service-queue/{queueId}" -H "Authorization: Bearer $TOKEN"` and extract `defaultMusicInQueueMediaFileId`.

## Create Business Hours

```bash
curl -s -X POST "https://api.wxcc-us1.cisco.com/organization/{orgId}/business-hours" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "MyBusinessHours",
    "description": "Mon-Fri 8AM-5PM Eastern",
    "timezone": "America/New_York",
    "workingHours": [
      {
        "name": "Weekday-Shift",
        "days": ["MON", "TUE", "WED", "THU", "FRI"],
        "startTime": "08:00",
        "endTime": "17:00"
      }
    ]
  }'
```

| Field | Required | Notes |
|-------|----------|-------|
| `name` | Yes | Schedule name. Pattern: `^[a-zA-Z0-9_-]+(\s?[a-zA-Z0-9_-]+)*$` (max 80 chars) |
| `timezone` | Yes | IANA timezone (e.g., `America/New_York`, `America/Chicago`) |
| `workingHours` | Yes | Array of shift objects |
| `workingHours[].name` | Yes | Shift name. Same pattern as parent name — no special characters. Use hyphens, not spaces with special chars. |
| `workingHours[].days` | Yes | **Array** of 3-letter uppercase day codes: `SUN`, `MON`, `TUE`, `WED`, `THU`, `FRI`, `SAT`. NOT comma-separated string. |
| `workingHours[].startTime` | Yes | `HH:MM` format (24-hour) |
| `workingHours[].endTime` | Yes | `HH:MM` format (24-hour) |
| `holidaysId` | No | UUID of a holiday list (create separately via `cc-holiday-list`) |

**Gotcha:** `days` MUST be an array of strings, not a single comma-separated string. `"days": "MON,TUE"` causes "Bad payload: Cannot deserialize".

## Create an Entry Point

```bash
curl -s -X POST "https://api.wxcc-us1.cisco.com/organization/{orgId}/entry-point" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "MyEntryPoint",
    "entryPointType": "INBOUND",
    "channelType": "TELEPHONY",
    "serviceLevelThreshold": 60,
    "maximumActiveContacts": 0,
    "active": true,
    "timezone": "America/New_York",
    "flowId": "<flow-uuid>",
    "flowTagId": "Latest",
    "musicOnHoldId": "<music-file-uuid>",
    "callbackEnabled": false
  }'
```

| Field | Required | Notes |
|-------|----------|-------|
| `name` | Yes | Entry point name |
| `entryPointType` | Yes | `INBOUND` — 400 error if omitted ("invalid value") |
| `channelType` | Yes | `TELEPHONY`, `EMAIL`, `CHAT`, `SOCIAL_CHANNEL` |
| `serviceLevelThreshold` | Yes | Seconds |
| `maximumActiveContacts` | Yes | `0` = unlimited — 400 error if omitted |
| `active` | Yes | Boolean |
| `timezone` | No | IANA timezone |
| `flowId` | No | UUID of the Flow Designer flow to assign |
| `flowTagId` | No | `Latest`, `Dev`, `Test`, or `Live` |
| `musicOnHoldId` | Yes when `flowId` is set | UUID of hold music audio file. Verified live 2026-10-19: a create with `flowId` and no `musicOnHoldId` → 400 `musicOnHoldId: should have a proper value when flowId is present`; on the sandbox every entry point with a flow used the same file ID as the telephony queues' `defaultMusicInQueueMediaFileId` — copy it from an existing entry point [owner: `contact-center-core.md` § 8 Entry Points] |
| `callbackEnabled` | No | Boolean |

**Gotcha:** creating an entry point with `flowId` and `flowTagId: "Latest"` saved on the CC Bootcamp Sandbox on 2026-10-19 (and `show` read `flowId` back), once the body also carried `musicOnHoldId`; no 500 [owner: `contact-center-core.md` § 25 Gotchas, gotcha 29]. History: in 2026-07 this doc recorded that "`flowId` assignment may fail with 500 error on some orgs" and advised creating the entry point without `flowId`, then setting it with a PUT; that 500 did not reproduce on 2026-10-19 (one org, one run, so other orgs are not ruled out).

## History: wxcli Sent the Team Body as a Query Parameter (Fixed)

`wxcli cc-team create --json-body '{...}'` sends the JSON as the request body. Verified live 2026-10-19 on the CC Bootcamp Sandbox: `wxcli cc-team create --json-body` with the body in § Create a Team (no `--team-dto`) created the team, and `cc-team show` read back its name and site [owner: `contact-center-core.md` § 9 Teams, Key Parameters]. Queues and entry points were created the same way that day: `wxcli cc-queue create-contact-service-queue --json-body` and `wxcli cc-entry-point create --json-body`, with the bodies in § Create a Queue and § Create an Entry Point. The curl calls in this doc stay as the Raw HTTP form.

History (July 2026): the generated `wxcli cc-team create --team-dto '{...}'` and similar commands sent the JSON payload as a URL-encoded query parameter instead of the request body, so the API received an empty body and returned 400. The workaround then was "Use direct `curl` calls instead of `wxcli` for CC resource creation". It was a generator defect (the spec declares the team body as a query parameter), fixed by ADR-16 on 2026-10-13; `--team-dto` is still accepted and ignored.

## Provisioning Pipeline for Flow Building

When building a flow programmatically, provision resources in this order:

```
1. Confirm site exists (usually pre-provisioned) → wxcli cc-site list
2. Create team(s)             → wxcli cc-team create --json-body file://team.json
3. Create queue(s)            → wxcli cc-queue create-contact-service-queue --json-body file://queue.json
4. Create business hours      → curl POST /organization/{org}/business-hours
5. Get global variable UUIDs for FlowIR → wxcli cc-flow-store list-global-variables PROJECT_ID --fields variables
6. Compose FlowIR             → reference queue/BH UUIDs + global var metadata
7. Dry-run check → wxcli cc-flow create-validate PROJECT_ID --json-body file://flow.json
8. Import flow → wxcli cc-flow create-import PROJECT_ID --json-body file://flow.json
9. Publish draft → wxcli cc-flow publish FLOW_ID PROJECT_ID --skip-validation true
10. Create entry point, body with flowId + musicOnHoldId → wxcli cc-entry-point create --json-body file://ep.json
11. Assign PSTN number        → Control Hub or wxcli numbers (Webex Calling API)
```

## See Also

- [wxcc-platform.md](wxcc-platform.md) — what each resource is and how to set it up in Control Hub
- [flow-designer-flowir.md](flow-designer-flowir.md) — the FlowIR that references the queues and business hours created here
- [flow-designer-patterns.md](flow-designer-patterns.md) — publishing and managing flows once the resources exist
