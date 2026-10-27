# Contact Center: Routing, Campaigns, Flows, and Media

Reference for Webex Contact Center routing configuration, campaign management, flow automation,
and media resources. Covers 17 CLI groups with 112 commands generated from the Contact Center OpenAPI spec.

All commands use the regional base URL `https://api.wxcc-{region}.cisco.com` and require
CC-specific OAuth scopes (`cjp:config_read`, `cjp:config_write`). The `orgId` path parameter
is auto-injected from saved config. Set the region with `wxcli set-cc-region <region>`.

## Sources

- OpenAPI spec: `specs/webex-contact-center.json`
- developer.webex.com Contact Center APIs

---

## Table of Contents

1. [Dial Plans (cc-dial-plan)](#1-dial-plans-cc-dial-plan)
2. [Dial Numbers (cc-dial-number)](#2-dial-numbers-cc-dial-number)
3. [Outdial ANI (cc-outdial-ani)](#3-outdial-ani-cc-outdial-ani)
4. [Contact Numbers (cc-contact-number)](#4-contact-numbers-cc-contact-number)
5. [Callbacks (cc-callbacks)](#5-callbacks-cc-callbacks)
6. [Estimated Wait Time (cc-ewt)](#6-estimated-wait-time-cc-ewt)
7. [Overrides (cc-overrides)](#7-overrides-cc-overrides)
8. [Campaigns (cc-campaign)](#8-campaigns-cc-campaign)
9. [Contact Lists & DNC (cc-contact-list, cc-dnc)](#9-contact-lists--dnc-cc-contact-list-cc-dnc)
10. [Captures (cc-captures)](#10-captures-cc-captures)
11. [Flows (cc-flow)](#11-flows-cc-flow)
12. [Audio Files (cc-audio-files)](#12-audio-files-cc-audio-files)
13. [Data Sources (cc-data-sources)](#13-data-sources-cc-data-sources)
14. [Resource Collections (cc-resource-collection)](#14-resource-collections-cc-resource-collection)
15. [Channels (channel)](#15-channels-channel)
16. [Assets (asset)](#16-assets-asset)
17. [Consolidated Endpoint Reference](#17-consolidated-endpoint-reference)
18. [Gotchas](#18-gotchas)
19. [See Also](#19-see-also)

---

## 1. Dial Plans (cc-dial-plan)

Dial plans in Contact Center define routing rules that map dialed numbers to entry points and queues.
CC dial plans are entirely separate from Webex Calling dial plans -- different API, different base
URL, different configuration model. 8 commands.

### Commands

| CLI Command | HTTP | Description |
|---|---|---|
| `wxcli cc-dial-plan list` | GET /organization/{orgid}/dial-plan | List Dial Plan(s) |
| `wxcli cc-dial-plan create` | POST /organization/{orgid}/dial-plan | Create a new Dial Plan |
| `wxcli cc-dial-plan create-bulk` | POST /organization/{orgid}/dial-plan/bulk | Bulk save Dial Plan(s) |
| `wxcli cc-dial-plan show` | GET /organization/{orgid}/dial-plan/{id} | Get specific Dial Plan by ID |
| `wxcli cc-dial-plan update` | PUT /organization/{orgid}/dial-plan/{id} | Update specific Dial Plan by ID |
| `wxcli cc-dial-plan delete` | DELETE /organization/{orgid}/dial-plan/{id} | Delete specific Dial Plan by ID |
| `wxcli cc-dial-plan list-incoming-references` | GET /organization/{orgid}/dial-plan/{id}/incoming-references | List references for a specific Dial Plan |
| `wxcli cc-dial-plan list-dial-plan` | GET /organization/{orgid}/v2/dial-plan | List Dial Plan(s) (v2, supports `--search`) |

There is no bulk-export command for dial plans. Use `list-dial-plan -o json` to dump them,
or call the raw `bulk-export` endpoint over HTTP if the API exposes one for your org.

### Key Parameters

- `--json-body` -- Full JSON body for create/update operations (all create/update commands)
- `id` (argument) -- Dial plan ID for show/update/delete/list references

### CLI Examples

```bash
# List all dial plans (v2 with pagination and --search)
wxcli cc-dial-plan list-dial-plan

# List dial plans for the org (v1)
wxcli cc-dial-plan list

# Get a specific dial plan
wxcli cc-dial-plan show <dial-plan-id>

# Create a new dial plan (--name, --regular-expression, --active are required)
wxcli cc-dial-plan create --name "US-Main" --regular-expression '^\+1[0-9]{10}$' --active \
  --description "Main US routing"

# Bulk save dial plans
wxcli cc-dial-plan create-bulk --json-body '{"items":[{"itemIdentifier":"...","item":"...","requestAction":"SAVE"}]}'

# Delete a dial plan
wxcli cc-dial-plan delete <dial-plan-id>

# List incoming references for a dial plan
wxcli cc-dial-plan list-incoming-references <dial-plan-id>
```

### Raw HTTP

```bash
# List all dial plans (v2)
GET https://api.wxcc-us1.cisco.com/organization/{orgId}/v2/dial-plan
Authorization: Bearer {cc_token}

# Create a dial plan
POST https://api.wxcc-us1.cisco.com/organization/{orgId}/dial-plan
Content-Type: application/json
{"name":"US-Main","description":"Main US routing"}
```

---

## 2. Dial Numbers (cc-dial-number)

Dialed number mappings associate external phone numbers with Contact Center entry points. When a
customer calls a mapped number, the call routes to the configured entry point and flow. 12 commands.

### Commands

| CLI Command | HTTP | Description |
|---|---|---|
| `wxcli cc-dial-number list` | GET /organization/{orgid}/dial-number | List Dialed Number Mapping(s) (org) |
| `wxcli cc-dial-number create` | POST /organization/{orgid}/dial-number | Create a new Dialed Number Mapping |
| `wxcli cc-dial-number delete` | DELETE /organization/{orgid}/dial-number | **⚠ Deletes EVERY dialed number mapping in the org.** Takes no ID; its confirm prompt reads only "Delete Dial Number for <orgid>?". To delete one mapping use `delete-dial-number <id>` |
| `wxcli cc-dial-number create-bulk` | POST /organization/{orgid}/dial-number/bulk | Bulk save |
| `wxcli cc-dial-number list-numbers-only` | GET /organization/{orgid}/dial-number/numbers-only | List only dialed numbers |
| `wxcli cc-dial-number list-bulk-export` | GET /organization/{orgid}/dial-number/bulk-export | Bulk export |
| `wxcli cc-dial-number show` | GET /organization/{orgid}/dial-number/{id} | Get by ID |
| `wxcli cc-dial-number update` | PUT /organization/{orgid}/dial-number/{id} | Update by ID |
| `wxcli cc-dial-number delete-dial-number` | DELETE /organization/{orgid}/dial-number/{id} | Delete by ID |
| `wxcli cc-dial-number list-incoming-references` | GET /organization/{orgid}/dial-number/{id}/incoming-references | List references |
| `wxcli cc-dial-number list-dial-number-v2` | GET /organization/{orgid}/v2/dial-number | List (v2) |
| `wxcli cc-dial-number list-dial-number-v3` | GET /organization/{orgid}/v3/dial-number | List (v3) |

### Key Parameters

- `--dialled-number` -- the DN to map, E.164 (`dialledNumber` in the body — double "l", NOT `dialNumber`)
- `--entry-point-id` / `--entry-point-name` -- the inbound entry point the DN routes to (the name comes from `cc-entry-point list-entry-point`)
- `--location` -- the Webex Calling location's **bare UUID** — the tail of the decoded `wxcli locations list` id (`ciscospark://us/LOCATION/<uuid>`). The spec calls it optional; the API does not: omitting it returns 400 `location: should not be null or blank` (live 2026-10-13)
- `--region-id` -- the telephony region id. Also optional in the spec and required by the API: omitting it returns 400 `Telephony regionId should be provided.` (live 2026-10-13). No `wxcli` command lists regions; copy `regionId` from an existing mapping (`wxcli cc-dial-number list --all -o json`). On the 2026-10-13 sandbox all 3 mappings carried the same `regionId` and the same `location`
- Since 2026-10-13 `create --help` marks `--entry-point-id`, `--entry-point-name`, `--location` and `--region-id` required and the CLI refuses locally when one is missing (generator `make_required` override on this operation)
- `--json-body` -- Full JSON body for create/update operations (same field names as above)
- `id` (argument) -- Dialed number mapping ID for show/update/delete

### CLI Examples

```bash
# List all dialed number mappings (v2 with pagination)
wxcli cc-dial-number list-dial-number-v2

# List only the dialed numbers (no mapping details)
wxcli cc-dial-number list-numbers-only

# Get a specific mapping
wxcli cc-dial-number show <mapping-id>

# Read location/regionId off an existing mapping (there is no region-list command)
wxcli cc-dial-number list --all -o json --fields '[].{dn:dialledNumber,location:location,regionId:regionId}'

# Create a new dialed number mapping (flags form verified live 2026-10-13)
wxcli cc-dial-number create --dialled-number +15551234567 \
  --entry-point-id ENTRY_POINT_ID --entry-point-name "Main Inbound EP" \
  --location LOCATION_UUID --region-id REGION_ID
# ...or the same as a body:
wxcli cc-dial-number create --json-body '{"dialledNumber":"+15551234567","entryPointId":"ENTRY_POINT_ID","entryPointName":"Main Inbound EP","location":"LOCATION_UUID","regionId":"REGION_ID"}'

# Delete a specific mapping (verified live 2026-10-13: {"status": "deleted", ...})
wxcli cc-dial-number delete-dial-number <mapping-id>

# NOTE: bare `cc-dial-number delete` takes NO id and deletes EVERY mapping in the
# org (DELETE /organization/{orgid}/dial-number). It is deliberately not shown as
# an example; never run it to remove one number.

# Bulk export all mappings
wxcli cc-dial-number list-bulk-export -o json
```

### Raw HTTP

```bash
# List dialed numbers (v2)
GET https://api.wxcc-us1.cisco.com/organization/{orgId}/v2/dial-number
Authorization: Bearer {cc_token}

# Create a dialed number mapping (`location` = bare UUID of the Calling location)
POST https://api.wxcc-us1.cisco.com/organization/{orgId}/dial-number
Content-Type: application/json
{"dialledNumber":"+15551234567","entryPointId":"ENTRY_POINT_ID","entryPointName":"Main Inbound EP","location":"LOCATION_UUID","regionId":"REGION_ID"}

# Delete ALL dialed number mappings (use with extreme caution)
DELETE https://api.wxcc-us1.cisco.com/organization/{orgId}/dial-number
```

---

## 3. Outdial ANI (cc-outdial-ani)

Outdial ANI (Automatic Number Identification) controls the caller ID presented on outbound calls
from the contact center. Has a two-level structure: ANI profiles contain ANI entries, each entry
mapping to a specific phone number. 15 commands.

### Commands

| CLI Command | HTTP | Description |
|---|---|---|
| `wxcli cc-outdial-ani list` | GET /organization/{orgid}/outdial-ani | List Outdial ANI(s) |
| `wxcli cc-outdial-ani create` | POST /organization/{orgid}/outdial-ani | Create a new Outdial ANI |
| `wxcli cc-outdial-ani list-entry-outdial-ani` | GET /organization/{orgid}/outdial-ani/entry | List Outdial ANI Entry(s) |
| `wxcli cc-outdial-ani show` | GET /organization/{orgid}/outdial-ani/{id} | Get by ID |
| `wxcli cc-outdial-ani update` | PUT /organization/{orgid}/outdial-ani/{id} | Update by ID |
| `wxcli cc-outdial-ani delete` | DELETE /organization/{orgid}/outdial-ani/{id} | Delete by ID |
| `wxcli cc-outdial-ani list-incoming-references` | GET /organization/{orgid}/outdial-ani/{id}/incoming-references | List references |
| `wxcli cc-outdial-ani list-outdial-ani` | GET /organization/{orgid}/v2/outdial-ani | List (v2) |
| `wxcli cc-outdial-ani list-entry-outdial-ani-1` | GET /organization/{orgid}/v2/outdial-ani/{outDialAniId}/entry | List entries (v2) |
| `wxcli cc-outdial-ani create-bulk-outdial-ani` | POST /organization/{orgid}/outdial-ani/bulk | Bulk save Outdial ANI(s) |
| `wxcli cc-outdial-ani create-entry` | POST /organization/{orgid}/outdial-ani/{outDialAniId}/entry | Create entry |
| `wxcli cc-outdial-ani create-bulk-entry` | POST /organization/{orgid}/outdial-ani/{outDialAniId}/entry/bulk | Bulk save entries |
| `wxcli cc-outdial-ani show-entry` | GET /organization/{orgid}/outdial-ani/{outDialAniId}/entry/{id} | Get entry by ID |
| `wxcli cc-outdial-ani update-entry` | PUT /organization/{orgid}/outdial-ani/{outDialAniId}/entry/{id} | Update entry by ID |
| `wxcli cc-outdial-ani delete-entry` | DELETE /organization/{orgid}/outdial-ani/{outDialAniId}/entry/{id} | Delete entry by ID |

### Key Parameters

- `--json-body` -- Full JSON body for create/update operations
- `id` (argument) -- Outdial ANI ID for ANI-level operations
- `out-dial-ani-id` (argument) -- Parent ANI ID for entry-level operations
- `id` (argument) -- Entry ID for entry-level get/update/delete

### CLI Examples

```bash
# List all outdial ANIs (v2)
wxcli cc-outdial-ani list-outdial-ani

# Create an outdial ANI profile
wxcli cc-outdial-ani create --json-body '{"name":"US-OutdialANI","description":"US outbound caller ID"}'

# Add an entry to an ANI profile. `create-entry --help` requires --name and --number;
# the body field is `number`, not `dialNumber`. Verified live 2026-10-13 (sandbox agent run): create-entry returned
# `Created: <id>`, `list-entry-outdial-ani-1` read back {name, number, defaultANIEntry:false}, `update-entry --verify`
# matched all 3 fields (the update body must carry "id"), and `delete-entry` returned {"status":"deleted"}.
# A 555-style test number was accepted.
wxcli cc-outdial-ani create-entry <ani-id> --name "Main line" --number +15551234567

# List entries for a specific ANI (v2)
wxcli cc-outdial-ani list-entry-outdial-ani-1 <ani-id>

# Delete an ANI entry
wxcli cc-outdial-ani delete-entry <ani-id> <entry-id>

# Dump all ANIs as JSON (there is no bulk-export command for outdial ANIs)
wxcli cc-outdial-ani list-outdial-ani -o json
```

> **`cc-outdial-ani update <id>` is a full replace, and it deletes the profile's entries if the body omits them.**
> Verified live 2026-10-13 (sandbox agent run, 2 of 2 attempts): a PUT without `outdialANIEntries` returned success,
> then `show` gave `outdialANIEntries: null` and `show-entry` gave 404; `update-entry` on the lost entry then returned
> `422 "Existing entity [...] not present for update"`. `--verify` still printed "all 3 sent field(s) match", so it
> does not flag the loss. To rename a profile, `show` it first and send its `outdialANIEntries` back in the body.
> `cc-outdial-ani create --json-body '{"name":…,"description":…}'` works with no placeholder option. (`cc-team`, `cc-desktop-profile` and `cc-skill-profile` create/update demanded a dummy DTO option until the generator fix of 2026-10-13, ADR-16; they no longer do — not re-run live for those commands.)

### Raw HTTP

```bash
# List outdial ANIs (v2)
GET https://api.wxcc-us1.cisco.com/organization/{orgId}/v2/outdial-ani
Authorization: Bearer {cc_token}

# Create an entry under an ANI profile
POST https://api.wxcc-us1.cisco.com/organization/{orgId}/outdial-ani/{outDialAniId}/entry
Content-Type: application/json
{"name":"Main line","number":"+15551234567"}
```

---

## 4. Contact Numbers (cc-contact-number)

Contact numbers are the phone numbers available to the contact center for inbound and outbound
operations. These are distinct from dialed number mappings -- contact numbers represent the pool
of numbers, while dial numbers define routing rules. 8 commands.

### Commands

| CLI Command | HTTP | Description |
|---|---|---|
| `wxcli cc-contact-number create` | POST /organization/{orgid}/contact-number | Create a new Contact Number |
| `wxcli cc-contact-number list` | GET /organization/{orgid}/contact-number/all-numbers | List all contact numbers |
| `wxcli cc-contact-number create-bulk` | POST /organization/{orgid}/contact-number/bulk | Bulk save |
| `wxcli cc-contact-number list-contact-number` | GET /organization/{orgid}/v2/contact-number | List (v2) |
| `wxcli cc-contact-number show` | GET /organization/{orgid}/contact-number/{id} | Get by ID |
| `wxcli cc-contact-number update` | PUT /organization/{orgid}/contact-number/{id} | Update by ID |
| `wxcli cc-contact-number delete` | DELETE /organization/{orgid}/contact-number/{id} | Delete by ID |
| `wxcli cc-contact-number list-bulk-export` | GET /organization/{orgid}/contact-number/bulk-export | Bulk export |

### Key Parameters

- `--json-body` -- Full JSON body for create/update operations
- `id` (argument) -- Contact number ID for show/update/delete

### CLI Examples

```bash
# List all contact numbers
wxcli cc-contact-number list

# List contact numbers (v2 with pagination)
wxcli cc-contact-number list-contact-number

# Get a specific contact number
wxcli cc-contact-number show <number-id>

# Create a contact number
wxcli cc-contact-number create --json-body '{"number":"+15551234567"}'

# Bulk export
wxcli cc-contact-number list-bulk-export -o json

# Delete a contact number
wxcli cc-contact-number delete <number-id>
```

> **Unverified:** the create body is from the spec, not a live call: `number` (the customized
> ANI) is the only required key, and there is no `name` or `type`.

### Raw HTTP

```bash
# List all contact numbers
GET https://api.wxcc-us1.cisco.com/organization/{orgId}/contact-number/all-numbers
Authorization: Bearer {cc_token}

# Create a contact number
POST https://api.wxcc-us1.cisco.com/organization/{orgId}/contact-number
Content-Type: application/json
{"number":"+15551234567"}
```

---

## 5. Callbacks (cc-callbacks)

Scheduled callbacks allow customers to request a return call instead of waiting in queue. The
callback API manages the lifecycle of these requests -- scheduling, listing, updating, and
canceling. Uses the runtime path family (`/v1/callbacks/`) rather than the config path. 5 commands.

### Commands

| CLI Command | HTTP | Description |
|---|---|---|
| `wxcli cc-callbacks create` | POST /v1/callbacks/organization/{orgId}/scheduled-callback | Schedule a Callback |
| `wxcli cc-callbacks list` | GET /v1/callbacks/organization/{orgId}/scheduled-callback | Get scheduled callbacks |
| `wxcli cc-callbacks show` | GET /v1/callbacks/organization/{orgId}/scheduled-callback/{id} | Get by ID |
| `wxcli cc-callbacks update` | PUT /v1/callbacks/organization/{orgId}/scheduled-callback/{id} | Update by ID |
| `wxcli cc-callbacks delete` | DELETE /v1/callbacks/organization/{orgId}/scheduled-callback/{id} | Delete by ID |

### Key Parameters

- `--json-body` -- Full JSON body for create/update
- `id` (argument) -- Callback ID for show/update/delete

### CLI Examples

```bash
# List scheduled callbacks -- at least one of --callback-number / --assignee-agent is required
wxcli cc-callbacks list --callback-number +15551234567 -o json

# Get a specific callback
wxcli cc-callbacks show <callback-id>

# Schedule a new callback (all seven flags are required; see gotcha 12 for the entry-point prerequisite)
wxcli cc-callbacks create --customer-name "Pat Doe" --callback-number +15551234567 \
  --timezone America/New_York --schedule-date 2026-09-20 --start-time 10:00:00 \
  --end-time 11:00:00 --queue-id <queue-id>

# Update a scheduled callback (PUT -- send the full object, same required fields as create)
wxcli cc-callbacks update <callback-id> --json-body '{"id":"<callback-id>","customerName":"Pat Doe","callbackNumber":"+15551234567","timezone":"America/New_York","scheduleDate":"2026-09-20","startTime":"14:00:00","endTime":"15:00:00","queueId":"<queue-id>"}'

# Cancel a callback
wxcli cc-callbacks delete <callback-id>
```

### Raw HTTP

```bash
# List scheduled callbacks
GET https://api.wxcc-us1.cisco.com/v1/callbacks/organization/{orgId}/scheduled-callback?callbackNumber=%2B15551234567
Authorization: Bearer {cc_token}

# Schedule a callback
POST https://api.wxcc-us1.cisco.com/v1/callbacks/organization/{orgId}/scheduled-callback
Content-Type: application/json
{"customerName":"Pat Doe","callbackNumber":"+15551234567","timezone":"America/New_York","scheduleDate":"2026-09-20","startTime":"10:00:00","endTime":"11:00:00","queueId":"queue-id"}
```

---

## 6. Estimated Wait Time (cc-ewt)

A single read-only endpoint that returns the estimated wait time for a given queue and media
channel. Useful for IVR flows that announce hold times to callers. 1 command.

### Commands

| CLI Command | HTTP | Description |
|---|---|---|
| `wxcli cc-ewt show` | GET /v1/ewt | Get Estimated Wait Time |

### Key Parameters

- `--queue-id` -- Queue ID to check (required)
- `--lookback-minutes` -- Sampling window, 5-240 (required)
- `--max-cv` -- Maximum coefficient of variance within a subset of samples (wait times for tasks
  connected to an agent in a one-minute interval), used to determine whether the average of those
  values is treated as a valid sample for EWT computation. 1-100, defaults to 40%
- `--min-valid-samples` -- Minimum percentage of valid samples, with respect to the total number of
  samples, within the specified lookback window. 1-100, defaults to 40%

### CLI Examples

```bash
# Get estimated wait time for a queue (--lookback-minutes is required, 5-240)
wxcli cc-ewt show --queue-id <queue-id> --lookback-minutes 30

# Get EWT as JSON
wxcli cc-ewt show --queue-id <queue-id> --lookback-minutes 30 -o json
```

### Raw HTTP

```bash
# Get estimated wait time
GET https://api.wxcc-us1.cisco.com/v1/ewt?queueId={queueId}&mediaType=telephony
Authorization: Bearer {cc_token}
```

---

## 7. Overrides (cc-overrides)

Overrides temporarily replace normal routing behavior -- for example, routing all calls to an
overflow queue during a holiday or outage. They can be scheduled or activated on demand. 8 commands.

### Commands

| CLI Command | HTTP | Description |
|---|---|---|
| `wxcli cc-overrides list` | GET /organization/{orgid}/overrides | List Overrides resource(s) |
| `wxcli cc-overrides create` | POST /organization/{orgid}/overrides | Create a new Override |
| `wxcli cc-overrides create-bulk` | POST /organization/{orgid}/overrides/bulk | Bulk save |
| `wxcli cc-overrides show` | GET /organization/{orgid}/overrides/{id} | Get by ID |
| `wxcli cc-overrides update` | PUT /organization/{orgid}/overrides/{id} | Update by ID |
| `wxcli cc-overrides delete` | DELETE /organization/{orgid}/overrides/{id} | Delete by ID |
| `wxcli cc-overrides list-incoming-references` | GET /organization/{orgid}/overrides/{id}/incoming-references | List references |
| `wxcli cc-overrides list-overrides` | GET /organization/{orgid}/v2/overrides | List (v2) |

### Key Parameters

- `--json-body` -- Full JSON body for create/update
- `id` (argument) -- Override ID for show/update/delete/references

### CLI Examples

```bash
# List all overrides (v2)
wxcli cc-overrides list-overrides

# Get a specific override
wxcli cc-overrides show <override-id>

# Create an override
wxcli cc-overrides create --json-body '{"name":"Holiday-Override","description":"Route to overflow during holidays"}'

# Update an override
wxcli cc-overrides update <override-id> --json-body '{"name":"Holiday-Override","timezone":"America/New_York","overrides":[{"name":"Christmas","startDateTime":"2026-12-25T00:00","endDateTime":"2026-12-25T23:59","workingHours":false,"frequency":"DontRepeat"}]}'

# Delete an override
wxcli cc-overrides delete <override-id>

# Dump all overrides as JSON (there is no bulk-export command for overrides)
wxcli cc-overrides list-overrides -o json
```

> **Unverified:** the `update` body is from the spec, not a live call. It is a PUT: `name`,
> `timezone` and `overrides` are required, and there is no `active` flag. Each override needs
> `name` and `workingHours`; `frequency` is `DontRepeat`, `Daily`, `Weekly`, `Monthly` or
> `Yearly`.

### Raw HTTP

```bash
# List overrides (v2)
GET https://api.wxcc-us1.cisco.com/organization/{orgId}/v2/overrides
Authorization: Bearer {cc_token}

# Create an override
POST https://api.wxcc-us1.cisco.com/organization/{orgId}/overrides
Content-Type: application/json
{"name":"Holiday-Override","description":"Route to overflow during holidays"}
```

---

## 8. Campaigns (cc-campaign)

Campaign management controls outbound dialing campaigns. Campaigns are started, updated (to change
dialing parameters), and stopped via these endpoints. Uses the runtime path family (`/v1/dialer/`).
3 commands.

### Commands

| CLI Command | HTTP | Description |
|---|---|---|
| `wxcli cc-campaign create` | POST /v1/dialer/campaign | Start Campaign |
| `wxcli cc-campaign update` | PUT /v1/dialer/campaign/{campaignId} | Update Campaign |
| `wxcli cc-campaign delete` | DELETE /v1/dialer/campaign/{campaignId} | Stop Campaign |

### Key Parameters

- `campaign-id` (argument) -- Campaign ID for update/delete
- `--dialing-list-fetch-url` -- URL to fetch the dialing list
- `--outdial-ani` -- Outdial ANI to use for the campaign
- `--reservation-percentage` -- Percentage of agents to reserve
- `--dialing-rate` / `--max-dialing-rate` -- Dialing rate controls
- `--preview-offer-timeout` -- Timeout for preview offer (seconds)
- `--preview-offer-timeout-auto-action` -- Action when preview times out
- `--campaign-name` -- Campaign name
- `--no-answer-ring-limit` -- Ring limit before treating as no answer
- `--json-body` -- Full JSON body (overrides individual options)

### CLI Examples

```bash
# Start a campaign
wxcli cc-campaign create --json-body '{"campaignName":"Q1-Outreach","dialingListFetchURL":"https://crm.example.com/list","outdialANI":"+15551234567","dialingRate":5}'

# Update campaign parameters
wxcli cc-campaign update <campaign-id> --dialing-rate 10 --max-dialing-rate 20

# Stop a campaign
wxcli cc-campaign delete <campaign-id>
```

### Raw HTTP

```bash
# Start a campaign
POST https://api.wxcc-us1.cisco.com/v1/dialer/campaign
Content-Type: application/json
{"campaignName":"Q1-Outreach","dialingListFetchURL":"https://crm.example.com/list","outdialANI":"+15551234567"}

# Stop a campaign
DELETE https://api.wxcc-us1.cisco.com/v1/dialer/campaign/{campaignId}
Authorization: Bearer {cc_token}
```

### Campaign Groups (cc-campaign-group)

Campaign groups bundle campaigns for reporting and bulk handling. The only operation is the reverse lookup — given a group, which campaigns belong to it. 1 command, on the configuration path family (`/v3/campaign-management/`), not the runtime `/v1/dialer/` family the three commands above use.

| CLI Command | HTTP | Description |
|---|---|---|
| `wxcli cc-campaign-group list` | GET /v3/campaign-management/campaign-groups/{campaignGroupName}/campaigns | List Campaigns by Campaign Group |

```bash
# Every campaign in a group
wxcli cc-campaign-group list CAMPAIGN_GROUP_NAME -o json

# Only the ones currently dialing, one page at a time
wxcli cc-campaign-group list CAMPAIGN_GROUP_NAME --campaign-status Running --page-size 50
```

#### Gotchas

- **The positional is a group NAME, not an ID.** Most `cc-*` commands take a UUID; the spec declares this one as `campaignGroupName` and it goes into the URL path verbatim. What the API does with a UUID passed here is untested.
- **`--page` / `--page-size` are the endpoint's own paging controls; `--limit` / `--offset` are translated onto them.** On every page-numbered `cc-*` list command (since 2026-10-13) `--limit N` is sent as the page size and `--offset N` returns records N onward, record-exact, by fetching the right page(s) — before that they were sent as `max`/`start`, which these endpoints ignore. `--page-size` must be between 1 and 100. Use `--all` to walk every page.
- **There is no create/update/delete here.** The tracked spec declares one operation for this group, so the CLI has one command — creating or deleting a campaign group is not an API surface wxcli can reach.

---

## 9. Contact Lists & DNC (cc-contact-list, cc-dnc)

Contact lists hold the records for outbound campaigns. Each campaign can have multiple contact
lists, and each list contains individual contacts. The DNC (Do Not Call) list prevents the
dialer from calling specific phone numbers. Uses the `/v3/campaign-management/` path family.
8 commands across 2 CLI groups.

### cc-contact-list Commands (5)

| CLI Command | HTTP | Description |
|---|---|---|
| `wxcli cc-contact-list create` | POST /v3/campaign-management/campaigns/{campaignId}/contact-list | Create contact list |
| `wxcli cc-contact-list create-contacts` | POST /v3/campaign-management/campaigns/{campaignId}/contact-list/{contactListId}/contacts | Create contacts within a list |
| `wxcli cc-contact-list update` | PATCH /v3/campaign-management/campaigns/{campaignId}/contact-list/{contactListId}/contacts/{contactId} | Update a contact's status |
| `wxcli cc-contact-list update-status` | PATCH /v3/campaign-management/campaigns/{campaignId}/contact-list/{contactListId}/status | Update contact list status |
| `wxcli cc-contact-list list` | GET /v3/campaign-management/campaigns/{campaignId}/contact-lists | Get Contact Lists within a Campaign |

### cc-dnc Commands (3)

| CLI Command | HTTP | Description |
|---|---|---|
| `wxcli cc-dnc create` | POST /v3/campaign-management/dncList/{dncListName}/phoneNumber | Add Phone Number to DNC List |
| `wxcli cc-dnc show` | GET /v3/campaign-management/dncList/{dncListName}/phoneNumber/{phoneNumber} | Get Phone Number from DNC List |
| `wxcli cc-dnc delete` | DELETE /v3/campaign-management/dncList/{dncListName}/phoneNumber/{phoneNumber} | Remove Phone Number from DNC List |

### Key Parameters

- `campaign-id` (argument) -- Campaign ID (contact list commands)
- `contact-list-id` (argument) -- Contact list ID within a campaign
- `contact-id` (argument) -- Individual contact ID
- `dnc-list-name` (argument) -- DNC list name (DNC commands)
- `phone-number` (argument) -- Phone number for DNC lookup/delete
- `--json-body` -- Full JSON body for create/update

### CLI Examples

```bash
# List contact lists for a campaign
wxcli cc-contact-list list <campaign-id>

# Create a contact list
wxcli cc-contact-list create <campaign-id> --json-body '{"supportedChannels":["Voice"],"activationTimeLagMinutes":0}'

# Add contacts to a list
wxcli cc-contact-list create-contacts <campaign-id> <list-id> --json-body '{"contacts":[{"phoneNumber":"+15551234567","firstName":"Jane"}]}'

# Close a contact
wxcli cc-contact-list update <campaign-id> <list-id> <contact-id> --json-body '{"contactStatus":"CLOSED"}'

# Update list status
wxcli cc-contact-list update-status <campaign-id> <list-id> --json-body '{"contactListStatus":"EXPIRED"}'

# Add a phone number to DNC list
wxcli cc-dnc create <dnc-list-name> --json-body '{"phoneNumber":"+15559876543"}'

# Check if a number is on the DNC list
wxcli cc-dnc show <dnc-list-name> +15559876543

# Remove a number from DNC list
wxcli cc-dnc delete <dnc-list-name> +15559876543
```

> **Unverified:** the contact-list bodies are from the spec, not a live call. `create` requires
> `supportedChannels` (`Voice`, `SMS` or `Email`) plus `activationTimeLagMinutes` or
> `activationDateTime`; there is no `name` or `contacts` key, so add contacts with
> `create-contacts`. A contact's `contactStatus` accepts only `CLOSED`. A list's
> `contactListStatus` takes values like the spec's `EXPIRED` (not case-sensitive).

### Raw HTTP

```bash
# List contact lists for a campaign
GET https://api.wxcc-us1.cisco.com/v3/campaign-management/campaigns/{campaignId}/contact-lists
Authorization: Bearer {cc_token}

# Add to DNC list
POST https://api.wxcc-us1.cisco.com/v3/campaign-management/dncList/{dncListName}/phoneNumber
Content-Type: application/json
{"phoneNumber":"+15559876543"}

# Check DNC
GET https://api.wxcc-us1.cisco.com/v3/campaign-management/dncList/{dncListName}/phoneNumber/{phoneNumber}
```

---

## 10. Captures (cc-captures)

The captures endpoint queries interaction capture records (recordings, transcripts). Uses POST
for querying rather than GET -- the request body contains the search criteria. 1 command.

### Commands

| CLI Command | HTTP | Description |
|---|---|---|
| `wxcli cc-captures create` | POST /v1/captures/query | List Captures (POST query) |

### Key Parameters

- `--json-body` -- `{"query":{"taskIds":[...]}}` (required). Captures are looked up **by task ID** — there is no date range or queue filter. Optional `query` fields: `orgId` (filled from the token if omitted), `urlExpiration`, `includeSegments`, `includeVARecordings`, `includeScreenRecordings`, `includeAllDigitalVersions` (see `--generate-json-body`). Get task IDs from `cc-tasks list --from <epoch-ms>` or `cc-search create`.

### CLI Examples

```bash
# Get captures (recording URLs) for specific tasks.
# Verified live 2026-10-13: this shape returns 200 ({meta:{orgId,urlExpiration}, data:[{taskId,...}]});
# the old {"from","to","filters"} body returned 400 "Invalid request entity". Real-capture content untested.
wxcli cc-captures create --json-body '{"query":{"taskIds":["TASK_ID"]}}' -o json
```

### Raw HTTP

```bash
# Query captures
POST https://api.wxcc-us1.cisco.com/v1/captures/query
Content-Type: application/json
Authorization: Bearer {cc_token}
{"query":{"taskIds":["TASK_ID"]}}
```

---

## 11. Flows (cc-flow)

Flows define the IVR and routing logic for contact center interactions. Subflows are reusable
components within flows. The Flow API supports listing, importing, exporting, drafting,
validating, locking, and publishing flows. Uses the `/{orgId}/project/{projectId}/flows` path
family -- note the `projectId` is required for all operations. 17 commands (the 4 activity-catalog
commands were added 2026-10-13).

### Commands

| CLI Command | HTTP | Description |
|---|---|---|
| `wxcli cc-flow list` | GET /{orgId}/project/{projectId}/flows | List Flows or Subflows |
| `wxcli cc-flow list-search` | GET /{orgId}/project/{projectId}/flows:search | Search Flows (`--query` required, case-sensitive) |
| `wxcli cc-flow show` | GET /{orgId}/project/{projectId}/v2/flows/{flowId} | Get a Flow |
| `wxcli cc-flow delete` | DELETE /{orgId}/project/{projectId}/flows/{flowId} | Delete a Flow or Subflow |
| `wxcli cc-flow create-flows` | POST /{orgId}/project/{projectId}/v2/flows/{flowId} | Save a Flow Draft |
| `wxcli cc-flow update` | PATCH /{orgId}/project/{projectId}/v2/flows/{flowId} | Patch a Flow Draft |
| `wxcli cc-flow create-import` | POST /{orgId}/project/{projectId}/v2/flows:import | Import a Flow |
| `wxcli cc-flow export` | GET /{orgId}/project/{projectId}/v2/flows/{flowId}:export | Export a Flow |
| `wxcli cc-flow publish` | POST /{orgId}/project/{projectId}/flows/{flowId}:publish | Publish a Flow or Subflow |
| `wxcli cc-flow create-validate` | POST /{orgId}/project/{projectId}/v2/flows:validate | Validate a Flow |
| `wxcli cc-flow list-validate` | GET /{orgId}/project/{projectId}/v2/flows/{flowId}:validate | Validate an existing Flow Draft (returns `{valid, results}`, verified 2026-10-13) |
| `wxcli cc-flow list-activities` | GET /{orgId}/project/{projectId}/v2/activities | List activity definitions: `list-activities PROJECT_ID` |
| `wxcli cc-flow show-activity` | GET /{orgId}/project/{projectId}/v2/activities/{activityName} | Describe one activity: `show-activity PROJECT_ID ACTIVITY_NAME` |
| `wxcli cc-flow list-activity-choices` | GET /{orgId}/project/{projectId}/v2/activities/{activityName}/inputs/{inputName}/choices | Input choices: `list-activity-choices PROJECT_ID ACTIVITY_NAME INPUT_NAME`; optional `--search`, `--validate`. A dependent input needs `--parent-input-name` and `--parent-value` or it returns 400 "requires a parent value" |
| `wxcli cc-flow list-event-specifications` | GET /{orgId}/project/{projectId}/v2/event-specifications | List event specifications: `list-event-specifications PROJECT_ID` |
| `wxcli cc-flow create-lock` | POST /{orgId}/project/{projectId}/flows/{flowId}:lock | Lock a Flow or Subflow |
| `wxcli cc-flow create-unlock` | POST /{orgId}/project/{projectId}/flows/{flowId}:unlock | Unlock a Flow or Subflow |

> **Argument-order trap:** `publish`, `create-lock`, and `create-unlock` take `FLOW_ID` **before**
> `PROJECT_ID`. Every other `cc-flow` command (`show`, `export`, `list-validate`, `delete`, ...)
> takes `PROJECT_ID` first. Always check `--help`. Verified live 2026-10-13: `export PROJECT_ID FLOW_ID`
> returns 200; `export FLOW_ID PROJECT_ID` returns 404 "Flow ... not found".

> **Verified live, 2026-10-13** (org "CC Bootcamp Sandbox", full-admin PAT):
> - **Finding the project ID.** No `cc-*` command lists projects. Get a flow id from
>   `cc-entry-point show <id>` (field `flowId`), then read the `projectId` field of
>   `cc-flow show <project-id> <flow-id>`; if you already know a project id, `cc-flow list <project-id>`
>   gives flow ids. On reads the server does not enforce `projectId` in the path (a made-up project id
>   returned the real flow).
> - **`export` vs `show`.** `cc-flow export` emits the full export envelope (15 keys incl.
>   `schemaVersion`, `id`, `name`, `nodes`, `edges`, `variables`, `eventFlows`, `preferences`), verified
>   2026-10-13 (identical to raw HTTP; `--version draft` also works). An earlier CLI build printed only
>   the `nodes` array; that was a CLI rendering bug, fixed 2026-10-13. `cc-flow show -o json` returns the
>   full flow definition (FlowIr schema 2.0).
> - **Exports do not round-trip (as observed).** `create-validate` on export-derived bodies returned
>   `valid:false` with errors such as "key not found: eventSourceName" and "Condition 'default' is not
>   valid for activity 'bridged-transfer'". Likely cause (attribution, not proven): the start node's
>   incomplete `flowType` plus the validator false positives described in "Building a flow from scratch".
> - **`create-import` works with a well-formed FlowIr body (supersedes the earlier "500 / not demonstrated"
>   note).** Verified live 2026-10-13: `cc-flow create-import <project-id> --json-body file://flow.json`
>   created a 43-node, 108-edge flow on the first attempt; `cc-flow show` then matched the body sent
>   (the server added only `activityId` and connector display fields). It is a **full create**, not a
>   merge: it returns `409 FLOW_ALREADY_EXISTS` ("set overwrite to yes or rename it") when the name is
>   taken, unless `--overwrite true` is passed. The response can carry non-fatal preflight warnings
>   (`preflightWarningsCount`, severity WARNING) that dry-run `create-validate` does not report. The
>   earlier 500s ("Oops... Something broke", trackingIds `693ce99d-ab7d-48f0-aef4-4ca1080105ca`,
>   `5fb767c8-9135-48d5-93df-35a0c09c1425`) were on export-derived bodies, and no flow was created. Their
>   cause is unproven. **Hypothesis (not re-tested):** the incomplete start-node `flowType`, the same
>   defect that makes `create-validate` say "key not found: eventSourceName". See "Building a flow from
>   scratch" below for the body shape.
> - **`list` paging fixed 2026-10-13.** `cc-flow list --all` now returns every flow (56 of 56 live); the
>   default fetch returns 10 and prints a note ("more pages ... `--offset 10`"). Earlier builds stopped at 10
>   because the CLI sent `pageSize`, which this endpoint ignores (it takes `size`). No `--size 100`
>   workaround is needed. `--offset` works here too (translated to `page`/`size`; live 2026-10-13:
>   `--offset 25 --limit 10` returned flows 25-34 of the `--all` order, from pages 2 and 3 at size 10).
> - **`list-search` is not routed on us1 — use `list --all` with `--fields` instead.** Verified live
>   2026-10-13: `GET …/flows:search` returns 404 with an **empty body** from the API gateway
>   (`server: istio-envoy`, `TrackingID: GTWY_…`), i.e. no route, not an application "not found". The same
>   empty 404 came back for `?query=Test`, `?query=Test&page=0&size=10&flowType=ALL`, no query at all,
>   `flows%3Asearch`, `flows/search`, `v2/flows:search` and `/flow-store/…/flows:search`, while
>   `…/flows?size=2` on the same org/project returned 200. The spec path is not wrong in any way a probe
>   could find; the route is simply absent. Search by name client-side:
>   `wxcli cc-flow list PROJECT_ID --all --fields "[?contains(name, 'Test')].name" -o json` (verified live).
>   The command's `--help` carries the same note.
> - **Lock/unlock.** `create-lock` / `create-unlock` return 200 "OK", but no command exposes lock state
>   for read-back.
> - **`create-validate` changes nothing, but it is not an authoritative verdict.** It is a POST that
>   writes no state, so it is safe to run, but `valid:false` can be a false positive. Two are proven
>   against Designer-built flows (Verified live 2026-10-13): the collect-digits success edge (below), and
>   FC1038 "Variable ... is referenced but not declared" on `{{Node.Output}}` references. It also reports
>   **one** edge-condition error per call, and edge checks gate the FC semantic checks, so errors surface
>   one layer at a time. See "Building a flow from scratch" -> "What the validators get wrong".

### Key Parameters

- `project-id` (argument) -- Project ID (required for all commands)
- `flow-id` (argument) -- Flow ID (for show/draft/export/publish/lock/validate)
- `--flow-type` -- Filter by `FLOW` or `SUBFLOW`
- `--ids` -- Comma-separated list of flow IDs to filter (`list` only)
- `--partial-name-search` -- Partial name match filter (`list` only)
- `--page` / `--size` -- Pagination controls (`list` only)
- `--include-pagination` -- Include pagination metadata in response (`list` only)
- `--version` -- Version to export; use `latest` for the most recent published (`export` only)
- `--expected-version` -- Optimistic-locking guard for draft writes (`create-flows` / `update`). Verified live 2026-10-19: `cc-flow update` with `--expected-version 99` on a draft at version 0 returned `409 Version conflict … expected version 99 but found 0` and wrote nothing; `--expected-version 0` was accepted. The draft `version` stayed `0` after the accepted patch, after publishes and after a rename, so the guard rejects a wrong number but does not separate two writers who both read `0` [`flow-designer-flowir.md` § 9 Step 6]
- `--overwrite` -- Replace an existing flow of the same name (`create-import` only)
- `--json-body` -- Full JSON body for import/draft/publish/lock

### CLI Examples

```bash
# List all flows in a project
wxcli cc-flow list <project-id>

# List only subflows
wxcli cc-flow list <project-id> --flow-type SUBFLOW

# Search flows by name
wxcli cc-flow list <project-id> --partial-name-search "Main-IVR"

# Export a flow definition (latest published version)
wxcli cc-flow export <project-id> <flow-id> --version latest -o json

# Import (create) a flow from a FlowIr 2.0 body -- see "Building a flow from scratch" below.
# 409 FLOW_ALREADY_EXISTS if the name is taken; add --overwrite true to replace it.
wxcli cc-flow create-import <project-id> --json-body file://flow.json

# Publish a flow -- NOTE: flow-id comes BEFORE project-id here
wxcli cc-flow publish <flow-id> <project-id>
```

`cc-flow publish` runs the pre-publish validation, and there is no flag to skip it. Upstream dropped the
`skipValidation` query parameter from the publish operation in the spec sync of 2026-10-26, so the generated
command no longer renders the skip flag it carried until then.

> **Unverified:** whether the server still honours a hand-sent `?skipValidation=true` on the raw HTTP path
> was not retested after the parameter left the spec. Only the CLI flag's removal is established.

### Raw HTTP

Paths below mirror what the CLI calls.

```bash
# List flows
GET https://api.wxcc-us1.cisco.com/{orgId}/project/{projectId}/flows?flowType=FLOW
Authorization: Bearer {cc_token}

# Export a flow
GET https://api.wxcc-us1.cisco.com/{orgId}/project/{projectId}/v2/flows/{flowId}:export?version=latest

# Import a flow
POST https://api.wxcc-us1.cisco.com/{orgId}/project/{projectId}/v2/flows:import
Content-Type: application/json
{...FlowIr 2.0 body, see "Building a flow from scratch" below...}
```

### Building a flow from scratch

Verified live 2026-10-13 (org "CC Bootcamp Sandbox", full-admin PAT, region us1): a 43-node, 108-edge
bilingual IVR (language menu, business hours, emergency fast path, outage lookup with callback, billing,
service) was written by hand, imported with `cc-flow create-import`, published as version 1 with
`cc-flow publish` (validation not skipped), and wired to a new entry point. **No test call was placed**, so
nothing here is runtime-verified (TTS voices, expressions, callback). The flow was not opened in Flow
Designer; FlowIr carries no node positions, so the canvas layout is unknown.

To look up activity names, their inputs/output ports and valid choice values while writing a body, use
`cc-flow list-activities PROJECT_ID`, `cc-flow show-activity PROJECT_ID ACTIVITY_NAME` and
`cc-flow list-activity-choices` (added 2026-10-13, all returned 200 live: 54 activities;
`show-activity queue-contact` 16 inputs). Re-counted live 2026-10-19: 54 for a FLOW, 29 with
`--flow-type SUBFLOW`, 57 with `--check-ui-enabled true` (the extra three are the feature-gated
`LiveCallerSentiment`, `flow-test-activity`, `queue-reservation`, hidden by default)
[`flow-designer-flowir.md` § 8]. Raw `GET /v2/activities` remains the fallback.

**The documented body shape is wrong.** The spec's FlowV2 schema and the `--help` example for
`create-validate` / `create-import` / `create-flows` show nodes `{name, activityName, inputs, outputs,
position}`, edges `{key, from_node, from_port, to_node, condition}`, `flowName`, and `eventFlows` as an
array. The server does not read that shape. Verified live 2026-10-13, `create-validate` on a body in the
spec shape returned `400 BAD_REQUEST`: `main flow edge from must not be empty.; main flow edge to must not
be empty.` plus `No start node found. Add one node with activityType='start'`. The server reads **FlowIr
2.0**:

- **Top level:** `{schemaVersion: "2.0", name, flowType: "FLOW", description, variables: [], nodes: [],
  edges: [], eventFlows: {nodes: [], edges: []}, preferences: []}`. `eventFlows` is an **object**, not an
  array. `name` was accepted; `flowName` was not tested. There is no `position`.
- **Node:** `{name, activityType: "start" | "action" | "end", properties: {activityName, <inputs flat>}}`.
  Inputs sit directly in `properties` (not under `inputs`). The working body also repeated `name` inside
  `properties`.
- **Edge:** `{from, to, condition}` (node names). The working body also set `properties: {value: <condition>}`.
  No edge `id` is needed: verified live 2026-10-19, validate passes with and without edge `id`s and the
  server does not store them [`flow-designer-flowir.md` § 5].

A `cc-flow show -o json` of an existing flow is a reliable template **for shape only**; its start-node
values are not trustworthy (next point).

**Minimum valid start node.** Verified live 2026-10-13: this start node gave a minimal `valid:true` and
imported. Two traps: the start activity is `NewContact` (`NewPhoneContact`, used by older Designer flows
and the spec example, returns `FC1024 Activity is not allowed for the current flow type ... flowType =
FLOW, channelType = telephony`), and the three `*Name` fields must be present even though the activity
definition's own default `flowType` omits them (without them: `FC0000 Validation pipeline error: key not
found: eventSourceName`).

The `FC1024` did **not** reproduce on 2026-10-19 (verified live, CC Bootcamp Sandbox): on the starter
flow, `create-validate` returned `valid: true` for this node, for the same node with `name`,
`activityName` and `event` all `NewPhoneContact`, and for the `NewPhoneContact` node of
`flow-designer-flowir.md` § 7 `start`. The 2026-10-13 `FC1024` came inside the 43-node flow; whether
that context triggers it was not re-tested. Stored flows use both names (`CCBootCampTest` and
`Record_Agent_Greeting` start at `NewPhoneContact`, `Retail_IVR_Test` at `NewContact`)
[`flow-designer-flowir.md` § 7 `start`]. Validate accepts either name (no deliberately wrong start node
was sent, so that is all it shows); runtime was not tested. This node is the one the working body used.

```json
{"name": "NewContact", "activityType": "start", "properties": {
  "name": "NewContact", "activityName": "NewContact", "activityId": "start", "event": "NewContact",
  "flowType": {
    "eventSourceId": "5eff0e2eb10162499bc9f932", "eventSourceName": "WebexContactCenter",
    "eventClassificationId": "5f10475cf021306e89e1692c", "eventClassificationName": "VoiceInteractions",
    "eventSpecificationId": "5f2d02144332507e39cc8a7f", "eventSpecificationName": "ContactStartWorkflow"}}}
```

**Edge-condition port names observed.** Port names differ per activity, and the activity catalog does
not match the validators in two places. The names below are the `condition` values that appeared in the
imported, published body (Verified live 2026-10-13; whether each fires correctly at runtime is untested):

| Activity | `condition` values used | Note |
|---|---|---|
| start (`NewContact`), `set-variable` | `out`, `error` | start has `out` only |
| `play-message`, `play-music` | `default`, `error` | |
| `ivr-menu` | the digit (`1`, `2`, `9`...), plus `timeout`, `invalid`, `error` | one edge per menu digit |
| `ivr-collectdigits` | `default`, plus `timeout`, `invalid`, `error` | the validator rejects `default` (below); Designer writes it; an edge with no `condition` validates clean (2026-10-19) |
| `condition-activity` | `true`, `false`, `error` | |
| `business-hours` | `workingHours`, `holidays`, `override`, `default`, `error` | accepted |
| `queue-contact` | `default` (queued), `failure` | `failure` draws a preflight WARNING on import (below); validate accepts both once the node has `channelType` (2026-10-19) |
| `callback` | `default`, `failure` | |
| `disconnect-contact` | none | `activityType: "end"` |

The spec's edge description ("`done` is rewritten to `out`") did **not** hold for collect-digits: `done`
was rejected verbatim, as were `out` and `success`.

**What the validators get wrong.** All verified live 2026-10-13; the first two are proven against
Designer-built flows, so the flow is not at fault:

- *ivr-collectdigits has no accepted success edge.* `create-validate` says `Condition 'default' is not
  valid for activity 'ivr-collectdigits'. Use one of: error, invalid, timeout`, and `out`, `done` and
  `success` get the same error. The Designer-built `CCBootCampTest` fails identically, so Flow Designer
  itself writes `default`. Import and publish both accepted `default`. Re-measured live 2026-10-19:
  validate still rejects `default`, import accepts it with **0** preflight warnings and stores it, and
  `CCBootCampTest` still stores `default`; an edge with **no `condition` field** validates clean (as
  wxcc recorded on 2026-07-25), though no stored flow read uses that form. Write `default`; which form
  fires at runtime is untested [`flow-designer-flowir.md` § 2].
- *FC1038 "Variable 'X' is referenced but not declared"* fires on every `{{Node.Output}}` reference
  (`{{CollectZip.DigitsEntered}}`, `{{QueueNode.QueueId}}`) except the start node's (`{{NewContact.ANI}}`
  passes), even when the node is directly upstream or has `outputs` declared. The published Designer flow
  `Record_Agent_Greeting` fails `list-validate` with the same code.
- *One edge error per call; edge checks gate the FC checks.* Fix one, re-run, and a new layer appears.
  Four errors (FC1015 twice, FC1038 twice) only surfaced after the edge error was removed.
- *Preflight WARNINGs on import contradict the catalog.* The import response carried
  `preflightWarningsCount: 5`, each `Condition 'failure' is not valid for activity 'queue-contact'. Use
  one of: default`, although `GET /v2/activities` (`cc-flow list-activities` / `show-activity queue-contact`) lists `failure` as a queue-contact output port. Only
  the tail of the response was captured, so three of the five are named (the callback, billing and
  service queues); the other two are presumably the emergency and outage queues (unverified).
- *Publish does not enforce what `list-validate` calls ERROR.* `cc-flow publish` with no skip-validation
  flag passed returned 200 with `latestVersion.version: 1` while `cc-flow list-validate` reported
  `ERROR FC1038` on the same draft. Publish's validation is evidently not the same check as either
  validate endpoint; which checks it does enforce was not mapped.

**Variables in FlowIr.** `variables` entries are `{name, description, type, value, isCAD, desktopLabel,
isAgentEditable, source, isReportable, overwrite, isSecure, id, isExternalized, resourceType}`. A
**global variable** is a FlowIr variable with `source: "GLOBAL"` and `id` set to the global's id (from
`cc-global-vars list-cad-variable`); a flow-local variable has `source: ""` and `id: ""`. Re-checked live
2026-10-19: `create-validate` also passes `source: "GLOBAL_TM"`, but every global variable in the stored
flows read (`Record_Agent_Greeting`, `Retail_IVR_Test`) is `"GLOBAL"`, so write `"GLOBAL"`
[`flow-designer-flowir.md` § 3]. An agent-viewable
variable (`isCAD: true`) needs a non-empty `desktopLabel`, including a global re-declared in the flow;
otherwise `FC1015 Desktop label is required for agent viewable variable`. Verified live 2026-10-13.

**Minimal example body.** Start, play a message, hang up. Every shape below also appears in the
working 43-node body; this three-node cut itself was not imported separately (**unverified as a
standalone body**). It declares no variables.

```json
{
  "schemaVersion": "2.0", "name": "Minimal_Greeting", "flowType": "FLOW",
  "description": "Start, greet, hang up",
  "variables": [],
  "nodes": [
    {"name": "NewContact", "activityType": "start", "properties": {
      "name": "NewContact", "activityName": "NewContact", "activityId": "start", "event": "NewContact",
      "flowType": {
        "eventSourceId": "5eff0e2eb10162499bc9f932", "eventSourceName": "WebexContactCenter",
        "eventClassificationId": "5f10475cf021306e89e1692c", "eventClassificationName": "VoiceInteractions",
        "eventSpecificationId": "5f2d02144332507e39cc8a7f", "eventSpecificationName": "ContactStartWorkflow"}}},
    {"name": "Greeting", "activityType": "action", "properties": {
      "name": "Greeting", "activityName": "play-message", "description": "Greeting",
      "toggle": true, "connector": "Cisco Cloud Text-to-Speech", "connector_name": "Cisco Cloud Text-to-Speech",
      "promptsTts": [{"type": "tts", "value": "Thank you for calling.", "name": "Thank you for calling."}],
      "speakingRate": 1, "volumeGainDb": 0}},
    {"name": "Disconnect", "activityType": "end", "properties": {
      "name": "Disconnect", "activityName": "disconnect-contact", "description": "Hang up"}}
  ],
  "edges": [
    {"from": "NewContact", "to": "Greeting", "condition": "out", "properties": {"value": "out"}},
    {"from": "Greeting", "to": "Disconnect", "condition": "default", "properties": {"value": "default"}},
    {"from": "Greeting", "to": "Disconnect", "condition": "error", "properties": {"value": "error"}}
  ],
  "eventFlows": {"nodes": [], "edges": []},
  "preferences": [{"name": "hideSecureCADWarning", "value": "false", "type": "Boolean"},
                  {"name": "autoSave", "value": "true", "type": "Boolean"}]
}
```

**Recipe notes (not runtime-tested; no test call was placed):**

- *Callback without a node-output reference.* `callback` with `toggleCallbackDestination: false` calls the
  caller back into the queue the contact is already in, so you avoid `{{QueueNode.QueueId}}` (and its
  FC1038 false positive). The working body queued the contact first (`queue-contact`), then ran `callback`
  with `callbackDn: "{{NewContact.ANI}}"`.
- *Bilingual TTS.* With the built-in "Cisco Cloud Text-to-Speech" connector, the voice comes from the
  `Global_Language` / `Global_VoiceName` globals, set per call with `set-variable` (`es-US` /
  `es-US-Alonso` for Spanish; `en-US` / `Automatic` for English). The pattern was copied from an existing
  flow (`Retail_IVR_Test`), then reused. One set of nodes speaks `{{msgX}}` prompt-text variables, loaded
  by a language-specific `set-variable` node, so the menus are not duplicated per language.

### Flow Store groups (added 2026-10-19)

Seven groups generated from the WxCC Flow Store spec (`specs/webex-cc-flow-store.json`) for flow
operations `cc-flow` does not cover. Six call the Flow Store host,
`https://flow-store.produs1.ciscoccservice.com/flow-store` by default (a tenant outside the US sets
`flow_store_url`); the gateway does not route most of their reads (the merge's Flow Store host map, § Decision:
flow-store-host-map.md under docs/merge in the source repository; not shipped). Every command takes `PROJECT_ID` positionally; read it from
`wxcli cc-flow-projects show-user-preferences` (`projectId`). The old-to-new command map
(wxcc-flow-command-map.md under docs/merge in the source repository; not shipped) maps every
`wxcc-flow` command to its `wxcli` command. FlowIR authoring — the body shape, the validate →
create → publish workflow and its gotchas — is in `flow-designer-flowir.md` (§ 9 and § 11); the
Custom Functions API is in `custom-functions.md`.

- `cc-flow-store` — flow metadata, copy, revert, consume from JSON or a template, name check (exit 1 when taken), variable mapping, where-used (`list-usages`), expression test, service health, build info and current user. Flow Store host.
- `cc-flow-versions` — a flow's published versions, one version, latest, draft, and every flow's versions (`list-all`; `list-all-latest` can 500 org-wide). Flow Store host.
- `cc-flow-tracing` — a flow's interactions, one interaction, its traces (`list-traces-decrypted` needs `--process-id`) and per-version analytics. Flow Store host.
- `cc-flow-prefs` — per-flow preferences (list, create, update, delete), tags and tag history. Flow Store host.
- `cc-flow-projects` — user preferences (the `projectId` source), projects, one project and resource collections. `list` and `show` see user-created projects only: the system project answers 404. Flow Store host.
- `cc-flow-connectors` — connectors of a user-created project; the system project answers 404. Flow Store host.
- `cc-flow-templates` — the flow/subflow template catalog (`list` walks with `--all`, `show ID`). CC API host (`GET /templates` routes on the gateway).
- `cc-functions` — Custom Functions: `list` (server-side column selection is `--function-fields`, not `--fields`), `show`, `create`, `update`, `delete`, `publish`, `export`, `import --file`, `lock`, `unlock`, and the hand-written `test ID --json-body '{"inputs":{…}}'` (the operation left the spec; it can return a 400 on some orgs, see its `--help`).
- `cc-legacy-flows` — the v1 UI-format flow: `export-ui FLOW_ID PROJECT_ID [--version draft]` (old name `list` is a hidden alias) and `import-ui PROJECT_ID --file PATH` (multipart; the gateway accepted it, HTTP 201, measured live 2026-10-19). Use it for the `export-ui` → remap → `import-ui` workaround; clear `id`/`flowId` and set a unique `name` in the file first.

History: these groups and `cc-flow` replace wxcc's `wxcc-flow` CLI (66 commands over the
93-operation Flow Store contract, verified against live prod 2026-07-24), which had itself
replaced the `wxcc-flow-builder` MCP server: its `list_flows` returned empty arrays, its tokens
rotated, and it covered 12 of 63+ endpoints (wxcc, 2026-07; see `flow-designer-flowir.md` § 11
"MCP list_flows Bug").

Defaults that differ from `wxcc-flow` (the command map's "pass the old defaults explicitly"):
- `cc-flow export` with no `--version` gives the **published** version; wxcc-flow's `export`
  gave the draft. Pass `--version draft` for the draft: `wxcli cc-flow export PROJECT_ID FLOW_ID --version draft -o json`.
- `cc-flow publish` validates first; wxcc-flow's `publish` skipped validation unless asked. There is no
  longer any way to reproduce the old default from the CLI — upstream dropped the `skipValidation` query
  parameter in the spec sync of 2026-10-26, so the flag that did it is gone (see CLI Examples above).
- `cc-flow delete` sends `--force` to the server: `--force yes` also deletes a flow that is
  still referenced, `--force no` is the server default; any value also skips the confirmation
  prompt (`wxcli cc-flow delete PROJECT_ID FLOW_ID --force no`; read from the command source, not run live). wxcc's bare `--force` only
  skipped the prompt.
- `cc-flow create-flows` and `cc-flow update` do not fill `--expected-version`; `wxcc-flow`
  read the draft's version and sent it. See `--expected-version` under § 11 Key Parameters.
- `cc-flow-store test-expression` takes the expression and its bindings in `--json-body`;
  `variables` is a map, not an array (`flow-designer-flowir.md` § 11 "test-expr Bindings Are a Map").

---

## 12. Audio Files (cc-audio-files)

Audio files are the prompts, greetings, and announcements used in flows, queues, and IVR menus.
The CLI covers read and delete only -- see the upload gap below. 4 commands.

### Commands

| CLI Command | HTTP | Description |
|---|---|---|
| `wxcli cc-audio-files list-audio-file` | GET /organization/{orgid}/v2/audio-file | List (v2) |
| `wxcli cc-audio-files show` | GET /organization/{orgid}/audio-file/{id} | Get by ID |
| `wxcli cc-audio-files delete` | DELETE /organization/{orgid}/audio-file/{id} | Delete by ID |
| `wxcli cc-audio-files list` | GET /organization/{orgid}/audio-file/{id}/incoming-references | List references |

> **Upload gap:** there is no `create` or `update` command for audio files. Uploading a prompt is a
> multipart/form-data request carrying the binary file, which the CLI generator does not render.
> Upload and replace audio files via the Control Hub UI, or call the endpoint over raw HTTP with a
> multipart body. Do not substitute `list` or `delete` -- they cannot upload.

### Key Parameters

- `id` (argument) -- Audio file ID for show/delete/references

### CLI Examples

```bash
# List all audio files (v2)
wxcli cc-audio-files list-audio-file

# Get a specific audio file
wxcli cc-audio-files show <audio-file-id>

# NOTE: uploading/replacing an audio file has no CLI command (multipart upload).
# Use Control Hub or a raw multipart HTTP request.

# Delete an audio file
wxcli cc-audio-files delete <audio-file-id>

# List references (what uses this audio file)
wxcli cc-audio-files list <audio-file-id>
```

### Raw HTTP

```bash
# List audio files (v2)
GET https://api.wxcc-us1.cisco.com/organization/{orgId}/v2/audio-file
Authorization: Bearer {cc_token}

# Partial update
PATCH https://api.wxcc-us1.cisco.com/organization/{orgId}/audio-file/{id}
Content-Type: application/json
{"name":"updated-greeting"}
```

---

## 13. Data Sources (cc-data-sources)

Data sources define external data connections (CRM systems, databases, APIs) that flows and
agents can query during interactions. Supports schema discovery for structured data access.
Uses the `/dataSources` path family (no orgId prefix in the path). 7 commands.

### Commands

| CLI Command | HTTP | Description |
|---|---|---|
| `wxcli cc-data-sources create` | POST /dataSources | Register a Data Source |
| `wxcli cc-data-sources list` | GET /dataSources/ | Retrieve All Data Sources |
| `wxcli cc-data-sources list-schemas` | GET /dataSources/schemas | Retrieve Data Source Schemas |
| `wxcli cc-data-sources show` | GET /dataSources/schemas/{schemaId} | Retrieve Specific Data Source Schema |
| `wxcli cc-data-sources show-data-sources` | GET /dataSources/{dataSourceId} | Retrieve Data Source Details |
| `wxcli cc-data-sources update` | PUT /dataSources/{dataSourceId} | Update a Data Source |
| `wxcli cc-data-sources delete` | DELETE /dataSources/{dataSourceId} | Delete a Data Source |

### Key Parameters

- `--json-body` -- Full JSON body for create/update
- `schema-id` (argument) -- Schema ID for schema retrieval
- `data-source-id` (argument) -- Data source ID for show/update/delete

### CLI Examples

```bash
# List all data sources
wxcli cc-data-sources list

# List available schemas
wxcli cc-data-sources list-schemas

# Get a specific schema
wxcli cc-data-sources show <schema-id>

# Get data source details
wxcli cc-data-sources show-data-sources <data-source-id>

# Register a new data source
wxcli cc-data-sources create --json-body '{"schemaId":"SCHEMA_ID","url":"https://myapp.example.com/webhook","audience":"my-app","subject":"data-feed","nonce":"unique-nonce-value","tokenLifetimeMinutes":60}'

# Update a data source (e.g. pause it)
wxcli cc-data-sources update <data-source-id> --json-body '{"status":"disabled","errorMessage":"Maintenance window"}'

# Delete a data source
wxcli cc-data-sources delete <data-source-id>
```

> **Unverified:** the bodies are from the spec, not a live call. A data source is a JWT-signed
> webhook registration (`schemaId`, `url`, `audience`, `subject`, `nonce`,
> `tokenLifetimeMinutes`) — it has no `name` or `type`. `update` adds `status`
> (`active`/`disabled`) and `errorMessage`. Same API as `data-sources` in
> [admin-apps-data.md](admin-apps-data.md).

### Raw HTTP

```bash
# List all data sources
GET https://api.wxcc-us1.cisco.com/dataSources/
Authorization: Bearer {cc_token}

# Register a data source
POST https://api.wxcc-us1.cisco.com/dataSources
Content-Type: application/json
{"schemaId":"SCHEMA_ID","url":"https://myapp.example.com/webhook","audience":"my-app","subject":"data-feed","nonce":"unique-nonce-value","tokenLifetimeMinutes":60}

# List schemas
GET https://api.wxcc-us1.cisco.com/dataSources/schemas
```

---

## 14. Resource Collections (cc-resource-collection)

Resource collections group related resources (e.g., a set of audio files, skill definitions, or
team configurations) for bulk management and assignment. 8 commands.

### Commands

| CLI Command | HTTP | Description |
|---|---|---|
| `wxcli cc-resource-collection create` | POST /organization/{orgid}/resource-collection | Create a new Resource Collection |
| `wxcli cc-resource-collection update` | PATCH /organization/{orgid}/resource-collection/bulk | Bulk partial update |
| `wxcli cc-resource-collection create-update-resource` | POST /organization/{orgid}/resource-collection/update-resource | Update resource with default collection |
| `wxcli cc-resource-collection show` | GET /organization/{orgid}/resource-collection/{id} | Get by ID |
| `wxcli cc-resource-collection update-resource-collection` | PUT /organization/{orgid}/resource-collection/{id} | Update by ID |
| `wxcli cc-resource-collection delete` | DELETE /organization/{orgid}/resource-collection/{id} | Delete by ID |
| `wxcli cc-resource-collection list-resource-collection` | GET /organization/{orgid}/v2/resource-collection | List (v2) |
| `wxcli cc-resource-collection list` | GET /organization/{orgid}/resource-collection/{id}/incoming-references | List references (takes an ID) |

### Key Parameters

- `--json-body` -- Full JSON body for create/update
- `id` (argument) -- Resource collection ID for show/update/delete/references

### CLI Examples

```bash
# List all resource collections (v2)
wxcli cc-resource-collection list-resource-collection

# Get a specific resource collection
wxcli cc-resource-collection show <collection-id>

# Create a resource collection
wxcli cc-resource-collection create --json-body '{"name":"US-Resources","description":"US region resource set"}'

# Update a resource collection
wxcli cc-resource-collection update-resource-collection <collection-id> --json-body '{"name":"US-Resources-v2"}'

# Bulk partial update
wxcli cc-resource-collection update --json-body '{"items":[{"id":"coll-1","name":"Updated-1"},{"id":"coll-2","name":"Updated-2"}]}'

# Delete a resource collection
wxcli cc-resource-collection delete <collection-id>

# List what references this collection
wxcli cc-resource-collection list <collection-id>
```

### Raw HTTP

```bash
# List resource collections (v2)
GET https://api.wxcc-us1.cisco.com/organization/{orgId}/v2/resource-collection
Authorization: Bearer {cc_token}

# Create a resource collection
POST https://api.wxcc-us1.cisco.com/organization/{orgId}/resource-collection
Content-Type: application/json
{"name":"US-Resources","description":"US region resource set"}

# Bulk partial update
PATCH https://api.wxcc-us1.cisco.com/organization/{orgId}/resource-collection/bulk
Content-Type: application/json
{"items":[{"id":"coll-1","name":"Updated-1"}]}
```

---

## 15. Channels (channel)

A channel is the **medium** a contact arrives on -- telephony, email, chat, social, or a custom
work-item type -- together with the branding (name, description, logo) the Agent Desktop shows for
it. Channels are *not* entry points and carry no routing logic: an entry point decides where a
contact goes, a channel only describes what it arrived through. They are also not the messaging
`channel` concept in Webex spaces, and nothing here touches Webex Calling. Assets (section 16)
reference a channel by `channelId`, so channels are created first. 6 commands.

**Unverified:** every statement in this section is read from `specs/webex-contact-center.json`
(2026-09-21 refresh) and from the generated module. No live call was made against a Contact Center
org, so treat response shapes and error behaviour as spec-derived, not measured.

### Commands

| CLI Command | HTTP | Description |
|---|---|---|
| `wxcli channel list-channel` | GET /organization/{orgid}/v2/channel | List Channels (v2, paginated) |
| `wxcli channel show` | GET /organization/{orgid}/channel/{id} | Get specific Channel by ID |
| `wxcli channel create` | POST /organization/{orgid}/channel/bulk | Bulk save Channels (create/update/delete in one call) |
| `wxcli channel update` | PATCH /organization/{orgid}/channel/{id} | Partially update Channel by ID |
| `wxcli channel delete` | DELETE /organization/{orgid}/channel/{id} | Delete specific Channel by ID |
| `wxcli channel list-incoming-references` | GET /organization/{orgid}/channel/{id}/incoming-references | List the assets and entry points that reference this channel |

Two spec operations have **no** CLI command: `POST /organization/{orgid}/channel` (single create)
and `PUT /organization/{orgid}/channel/{id}` (full update). Both are `multipart/form-data` because
they carry the channel logo image, which the generator cannot render, so they are recorded as a
deliberate gap in the CLI rather than as a bug. Use the Raw HTTP forms below for those two.

### Key Parameters

- `id` (argument) -- Channel ID, from `wxcli channel list-channel`. Required by show/update/delete/list-incoming-references.
- `--include-logo-url-versioned` -- on `show` and `list-channel`, adds `logoUrlVersioned` to the response.
- `--json-body` -- full JSON body; required shape for `create`, which is the *bulk* endpoint.

### CLI Examples

```bash
# List every channel in the org (walks all pages)
wxcli channel list-channel --all

# Just the id/name pairs, for scripting
wxcli channel list-channel --all --fields '[].{id:id,name:name}' -o json

# Get one channel, including its versioned logo URL
wxcli channel show <channel-id> --include-logo-url-versioned true

# Create a channel via the bulk endpoint (note: `create` is POST .../channel/bulk)
wxcli channel create --json-body '{"items":[{"requestAction":"CREATE","name":"Web Chat","description":"Public website chat","channelType":"CHAT"}]}'

# Rename a channel (PATCH -- only the fields you send change)
wxcli channel update <channel-id> --json-body '{"name":"Web Chat EU"}' --verify

# Find out what breaks if you delete it, BEFORE deleting it
wxcli channel list-incoming-references <channel-id>

# Delete a channel
wxcli channel delete <channel-id>
```

### Raw HTTP

```bash
# List channels (v2)
GET https://api.wxcc-us1.cisco.com/organization/{orgId}/v2/channel
Authorization: Bearer {cc_token}

# Partially update a channel
PATCH https://api.wxcc-us1.cisco.com/organization/{orgId}/channel/{id}
Content-Type: application/json
{"name":"Web Chat EU"}

# Single create -- multipart, no CLI command exists for this
POST https://api.wxcc-us1.cisco.com/organization/{orgId}/channel
Content-Type: multipart/form-data
(form fields: name, description, channelType; file field: logo)

# Full update incl. replacing the logo image -- multipart, no CLI command
PUT https://api.wxcc-us1.cisco.com/organization/{orgId}/channel/{id}
Content-Type: multipart/form-data
```

### Gotcha

**`wxcli channel create` is the BULK endpoint, not a single create, and it needs an `items` array.**
The single-create operation is multipart and therefore unrenderable, so the generator gave the bare
`create` name to `POST .../channel/bulk`. A body shaped like one channel (`{"name":"Web Chat"}`)
is the natural thing to type and is the wrong shape -- each element goes inside `items[]` with its
own `requestAction` (`CREATE`, `UPDATE`, or `DELETE`). The same call can therefore delete channels,
which a command named `create` gives no hint of. Run
`wxcli channel create --generate-json-body` to print the real skeleton before composing one.

See also section 16 below (Assets), because an asset is invalid without a `channelId` naming a
channel that already exists -- create the channel first or the asset create fails.

---

## 16. Assets (asset)

An asset is a **configured instance** of a channel: the concrete mailbox, chat widget, or
custom-messaging endpoint that a channel type is realised as, plus the business address and data
schema attached to it. An asset is not a channel (the channel is the medium; the asset is one
deployment of it), not an entry point (entry points reference assets, not the other way round), and
has nothing to do with Webex Calling devices or Webex messaging attachments. 8 commands.

**Unverified:** as with section 15, everything here is derived from the 2026-09-21 spec refresh and
the generated module, not from a live Contact Center org.

### Commands

| CLI Command | HTTP | Description |
|---|---|---|
| `wxcli asset list-asset` | GET /organization/{orgid}/v2/asset | List Assets (v2, paginated) |
| `wxcli asset show` | GET /organization/{orgid}/asset/{id} | Get specific Asset by ID |
| `wxcli asset create` | POST /organization/{orgid}/asset | Create a new Asset |
| `wxcli asset create-bulk` | POST /organization/{orgid}/asset/bulk | Bulk save Assets (CREATE/UPDATE/DELETE in one call) |
| `wxcli asset update` | PUT /organization/{orgid}/asset/{id} | Full update -- WORK_ITEM assets only |
| `wxcli asset update-asset` | PATCH /organization/{orgid}/asset/{id} | Partial update -- CUSTOM_MESSAGING assets only |
| `wxcli asset delete` | DELETE /organization/{orgid}/asset/{id} | Delete specific Asset by ID |
| `wxcli asset list-incoming-references` | GET /organization/{orgid}/asset/{id}/incoming-references | List the entities (e.g. entry points) that reference this asset |

### Key Parameters

- `id` (argument) -- Asset ID, from `wxcli asset list-asset`.
- `--name`, `--channel-type`, `--channel-id`, `--business-address` -- the four fields the spec marks required on create.
- `--channel-type` -- one of `TELEPHONY`, `EMAIL`, `FAX`, `CHAT`, `VIDEO`, `OTHERS`, `SOCIAL_CHANNEL`, `WORK_ITEM`, `CUSTOM_MESSAGING`.
- `--include-channel-name` -- on `show` and `list-asset`, resolves `channelId` to a readable channel name in the response.
- `--exclude-ep-associated` -- on `list-asset`, returns only assets **not** attached to an entry point.

### CLI Examples

```bash
# List every asset, with the channel name resolved rather than a bare channelId
wxcli asset list-asset --all --include-channel-name true

# Find assets nothing routes to yet -- the orphan check before a cleanup
wxcli asset list-asset --all --exclude-ep-associated true --fields '[].{id:id,name:name}' -o json

# Get one asset
wxcli asset show <asset-id> --include-channel-name true

# Create a work-item asset against an existing channel
wxcli asset create --name "Tier 2 Work Items" --channel-type WORK_ITEM --channel-id <channel-id> --business-address "600 Congress Ave, Austin TX"

# Full update -- WORK_ITEM assets only
wxcli asset update <asset-id> --json-body '{"name":"Tier 2 Work Items (EU)"}' --verify

# Partial update -- CUSTOM_MESSAGING assets only
wxcli asset update-asset <asset-id> --json-body '{"description":"Migrated 2026-09"}'

# Check what references an asset before removing it
wxcli asset list-incoming-references <asset-id>

# Delete an asset
wxcli asset delete <asset-id>
```

### Raw HTTP

```bash
# List assets (v2)
GET https://api.wxcc-us1.cisco.com/organization/{orgId}/v2/asset?includeChannelName=true
Authorization: Bearer {cc_token}

# Create an asset
POST https://api.wxcc-us1.cisco.com/organization/{orgId}/asset
Content-Type: application/json
{"name":"Tier 2 Work Items","channelType":"WORK_ITEM","channelId":"{channelId}","businessAddress":"600 Congress Ave, Austin TX"}

# Full update (WORK_ITEM)
PUT https://api.wxcc-us1.cisco.com/organization/{orgId}/asset/{id}
Content-Type: application/json
{"name":"Tier 2 Work Items (EU)"}

# Partial update (CUSTOM_MESSAGING)
PATCH https://api.wxcc-us1.cisco.com/organization/{orgId}/asset/{id}
Content-Type: application/json
{"description":"Migrated 2026-09"}
```

### Gotcha

**`update` and `update-asset` are not the same command with different granularity -- they apply to
different asset types, and picking the wrong one is a 4xx, not a partial write.** The spec is
explicit in both directions: `PUT /asset/{id}` says *"Supported for WORK_ITEM assets. For
CUSTOM_MESSAGING assets, use PATCH instead"*, and `PATCH /asset/{id}` says *"Supported only for
CUSTOM_MESSAGING assets... For WORK_ITEM assets, use PUT instead."* The CLI names give no hint of
that split, and `update` reads like the default choice for both. Check `channelType` with
`wxcli asset show <asset-id>` first. One more asymmetry worth knowing: `PATCH` leaves
`webhookConfig` alone when you omit it, so omitting it preserves existing credentials rather than
clearing them.

See also section 15 above (Channels), because `--channel-id` on create must name an existing
channel, and `wxcli channel list-incoming-references` is what tells you which assets a channel is
already carrying before you change it.

---

## 17. Consolidated Endpoint Reference

All 112 endpoints across 17 CLI groups, grouped by resource.

### Dial Plans (8)

| Method | Path | CLI Command |
|---|---|---|
| GET | /organization/{orgid}/dial-plan | `cc-dial-plan list` |
| POST | /organization/{orgid}/dial-plan | `cc-dial-plan create` |
| POST | /organization/{orgid}/dial-plan/bulk | `cc-dial-plan create-bulk` |
| GET | /organization/{orgid}/dial-plan/{id} | `cc-dial-plan show` |
| DELETE | /organization/{orgid}/dial-plan/{id} | `cc-dial-plan delete` |
| PUT | /organization/{orgid}/dial-plan/{id} | `cc-dial-plan update` |
| GET | /organization/{orgid}/dial-plan/{id}/incoming-references | `cc-dial-plan list-incoming-references` |
| GET | /organization/{orgid}/v2/dial-plan | `cc-dial-plan list-dial-plan` |

### Dial Numbers (12)

| Method | Path | CLI Command |
|---|---|---|
| GET | /organization/{orgid}/dial-number | `cc-dial-number list` |
| DELETE | /organization/{orgid}/dial-number | `cc-dial-number delete` — **⚠ deletes ALL mappings in the org; no ID** |
| POST | /organization/{orgid}/dial-number | `cc-dial-number create` |
| POST | /organization/{orgid}/dial-number/bulk | `cc-dial-number create-bulk` |
| GET | /organization/{orgid}/dial-number/bulk-export | `cc-dial-number list-bulk-export` |
| GET | /organization/{orgid}/dial-number/numbers-only | `cc-dial-number list-numbers-only` |
| GET | /organization/{orgid}/dial-number/{id} | `cc-dial-number show` |
| DELETE | /organization/{orgid}/dial-number/{id} | `cc-dial-number delete-dial-number` |
| PUT | /organization/{orgid}/dial-number/{id} | `cc-dial-number update` |
| GET | /organization/{orgid}/dial-number/{id}/incoming-references | `cc-dial-number list-incoming-references` |
| GET | /organization/{orgid}/v2/dial-number | `cc-dial-number list-dial-number-v2` |
| GET | /organization/{orgid}/v3/dial-number | `cc-dial-number list-dial-number-v3` |

### Outdial ANI (16)

| Method | Path | CLI Command |
|---|---|---|
| GET | /organization/{orgid}/outdial-ani | `cc-outdial-ani list` |
| POST | /organization/{orgid}/outdial-ani | `cc-outdial-ani create` |
| POST | /organization/{orgid}/outdial-ani/bulk | `cc-outdial-ani create-bulk-outdial-ani` |
| GET | /organization/{orgid}/outdial-ani/entry | `cc-outdial-ani list-entry-outdial-ani` |
| GET | /organization/{orgid}/outdial-ani/{id} | `cc-outdial-ani show` |
| DELETE | /organization/{orgid}/outdial-ani/{id} | `cc-outdial-ani delete` |
| PUT | /organization/{orgid}/outdial-ani/{id} | `cc-outdial-ani update` |
| GET | /organization/{orgid}/outdial-ani/{id}/incoming-references | `cc-outdial-ani list-incoming-references` |
| POST | /organization/{orgid}/outdial-ani/{outDialAniId}/entry | `cc-outdial-ani create-entry` |
| POST | /organization/{orgid}/outdial-ani/{outDialAniId}/entry/bulk | `cc-outdial-ani create-bulk-entry` |
| GET | /organization/{orgid}/outdial-ani/{outDialAniId}/entry/{id} | `cc-outdial-ani show-entry` |
| DELETE | /organization/{orgid}/outdial-ani/{outDialAniId}/entry/{id} | `cc-outdial-ani delete-entry` |
| PUT | /organization/{orgid}/outdial-ani/{outDialAniId}/entry/{id} | `cc-outdial-ani update-entry` |
| GET | /organization/{orgid}/v2/outdial-ani | `cc-outdial-ani list-outdial-ani` |
| GET | /organization/{orgid}/v2/outdial-ani/{outDialAniId}/entry | `cc-outdial-ani list-entry-outdial-ani-1` |

### Contact Numbers (8)

| Method | Path | CLI Command |
|---|---|---|
| POST | /organization/{orgid}/contact-number | `cc-contact-number create` |
| GET | /organization/{orgid}/contact-number/all-numbers | `cc-contact-number list` |
| POST | /organization/{orgid}/contact-number/bulk | `cc-contact-number create-bulk` |
| GET | /organization/{orgid}/contact-number/bulk-export | `cc-contact-number list-bulk-export` |
| GET | /organization/{orgid}/contact-number/{id} | `cc-contact-number show` |
| DELETE | /organization/{orgid}/contact-number/{id} | `cc-contact-number delete` |
| PUT | /organization/{orgid}/contact-number/{id} | `cc-contact-number update` |
| GET | /organization/{orgid}/v2/contact-number | `cc-contact-number list-contact-number` |

### Callbacks (5)

| Method | Path | CLI Command |
|---|---|---|
| POST | /v1/callbacks/organization/{orgId}/scheduled-callback | `cc-callbacks create` |
| GET | /v1/callbacks/organization/{orgId}/scheduled-callback | `cc-callbacks list` |
| GET | /v1/callbacks/organization/{orgId}/scheduled-callback/{id} | `cc-callbacks show` |
| DELETE | /v1/callbacks/organization/{orgId}/scheduled-callback/{id} | `cc-callbacks delete` |
| PUT | /v1/callbacks/organization/{orgId}/scheduled-callback/{id} | `cc-callbacks update` |

### Estimated Wait Time (1)

| Method | Path | CLI Command |
|---|---|---|
| GET | /v1/ewt | `cc-ewt show` |

### Overrides (9)

| Method | Path | CLI Command |
|---|---|---|
| GET | /organization/{orgid}/overrides | `cc-overrides list` |
| POST | /organization/{orgid}/overrides | `cc-overrides create` |
| POST | /organization/{orgid}/overrides/bulk | `cc-overrides create-bulk` |
| GET | /organization/{orgid}/overrides/{id} | `cc-overrides show` |
| DELETE | /organization/{orgid}/overrides/{id} | `cc-overrides delete` |
| PUT | /organization/{orgid}/overrides/{id} | `cc-overrides update` |
| GET | /organization/{orgid}/overrides/{id}/incoming-references | `cc-overrides list-incoming-references` |
| GET | /organization/{orgid}/v2/overrides | `cc-overrides list-overrides` |

### Campaigns (3)

| Method | Path | CLI Command |
|---|---|---|
| POST | /v1/dialer/campaign | `cc-campaign create` |
| PUT | /v1/dialer/campaign/{campaignId} | `cc-campaign update` |
| DELETE | /v1/dialer/campaign/{campaignId} | `cc-campaign delete` |

### Contact Lists (5)

| Method | Path | CLI Command |
|---|---|---|
| POST | /v3/campaign-management/campaigns/{campaignId}/contact-list | `cc-contact-list create` |
| POST | /v3/campaign-management/campaigns/{campaignId}/contact-list/{contactListId}/contacts | `cc-contact-list create-contacts` |
| PATCH | /v3/campaign-management/campaigns/{campaignId}/contact-list/{contactListId}/contacts/{contactId} | `cc-contact-list update` |
| PATCH | /v3/campaign-management/campaigns/{campaignId}/contact-list/{contactListId}/status | `cc-contact-list update-status` |
| GET | /v3/campaign-management/campaigns/{campaignId}/contact-lists | `cc-contact-list list` |

### DNC (3)

| Method | Path | CLI Command |
|---|---|---|
| POST | /v3/campaign-management/dncList/{dncListName}/phoneNumber | `cc-dnc create` |
| GET | /v3/campaign-management/dncList/{dncListName}/phoneNumber/{phoneNumber} | `cc-dnc show` |
| DELETE | /v3/campaign-management/dncList/{dncListName}/phoneNumber/{phoneNumber} | `cc-dnc delete` |

### Captures (1)

| Method | Path | CLI Command |
|---|---|---|
| POST | /v1/captures/query | `cc-captures create` |

### Flows (15)

| Method | Path | CLI Command |
|---|---|---|
| GET | /{orgId}/project/{projectId}/flows | `cc-flow list` |
| POST | /{orgId}/project/{projectId}/flows/{flowId}:publish | `cc-flow publish` |
| POST | /{orgId}/project/{projectId}/flows/{flowId}:lock | `cc-flow create-lock` |
| POST | /{orgId}/project/{projectId}/flows/{flowId}:unlock | `cc-flow create-unlock` |
| POST | /{orgId}/project/{projectId}/v2/flows:validate | `cc-flow create-validate` |
| POST | /{orgId}/project/{projectId}/v2/flows:import | `cc-flow create-import` |
| GET | /{orgId}/project/{projectId}/v2/flows/{flowId} | `cc-flow show` |
| POST | /{orgId}/project/{projectId}/v2/flows/{flowId} | `cc-flow create-flows` |
| PATCH | /{orgId}/project/{projectId}/v2/flows/{flowId} | `cc-flow update` |
| GET | /{orgId}/project/{projectId}/v2/flows/{flowId}:validate | `cc-flow list-validate` |
| GET | /{orgId}/project/{projectId}/v2/flows/{flowId}:export | `cc-flow export` |
| GET | /{orgId}/project/{projectId}/v2/activities | `cc-flow list-activities` |
| GET | /{orgId}/project/{projectId}/v2/activities/{activityName} | `cc-flow show-activity` |
| GET | /{orgId}/project/{projectId}/v2/activities/{activityName}/inputs/{inputName}/choices | `cc-flow list-activity-choices` |
| GET | /{orgId}/project/{projectId}/v2/event-specifications | `cc-flow list-event-specifications` |

### Audio Files (4)

| Method | Path | CLI Command |
|---|---|---|
| DELETE | /organization/{orgid}/audio-file/{id} | `cc-audio-files delete` |
| GET | /organization/{orgid}/audio-file/{id} | `cc-audio-files show` |
| GET | /organization/{orgid}/audio-file/{id}/incoming-references | `cc-audio-files list` |
| GET | /organization/{orgid}/v2/audio-file | `cc-audio-files list-audio-file` |

### Data Sources (7)

| Method | Path | CLI Command |
|---|---|---|
| POST | /dataSources | `cc-data-sources create` |
| GET | /dataSources/ | `cc-data-sources list` |
| GET | /dataSources/schemas | `cc-data-sources list-schemas` |
| GET | /dataSources/schemas/{schemaId} | `cc-data-sources show` |
| DELETE | /dataSources/{dataSourceId} | `cc-data-sources delete` |
| PUT | /dataSources/{dataSourceId} | `cc-data-sources update` |
| GET | /dataSources/{dataSourceId} | `cc-data-sources show-data-sources` |

### Resource Collections (8)

| Method | Path | CLI Command |
|---|---|---|
| POST | /organization/{orgid}/resource-collection | `cc-resource-collection create` |
| PATCH | /organization/{orgid}/resource-collection/bulk | `cc-resource-collection update` |
| POST | /organization/{orgid}/resource-collection/update-resource | `cc-resource-collection create-update-resource` |
| GET | /organization/{orgid}/resource-collection/{id} | `cc-resource-collection show` |
| DELETE | /organization/{orgid}/resource-collection/{id} | `cc-resource-collection delete` |
| PUT | /organization/{orgid}/resource-collection/{id} | `cc-resource-collection update-resource-collection` |
| GET | /organization/{orgid}/resource-collection/{id}/incoming-references | `cc-resource-collection list` |
| GET | /organization/{orgid}/v2/resource-collection | `cc-resource-collection list-resource-collection` |

### Channels (6)

| Method | Path | CLI Command |
|---|---|---|
| GET | /organization/{orgid}/v2/channel | `channel list-channel` |
| GET | /organization/{orgid}/channel/{id} | `channel show` |
| POST | /organization/{orgid}/channel/bulk | `channel create` |
| PATCH | /organization/{orgid}/channel/{id} | `channel update` |
| DELETE | /organization/{orgid}/channel/{id} | `channel delete` |
| GET | /organization/{orgid}/channel/{id}/incoming-references | `channel list-incoming-references` |

`POST /organization/{orgid}/channel` and `PUT /organization/{orgid}/channel/{id}` are multipart
(logo upload) and have no CLI command -- see section 15 above.

### Assets (8)

| Method | Path | CLI Command |
|---|---|---|
| GET | /organization/{orgid}/v2/asset | `asset list-asset` |
| GET | /organization/{orgid}/asset/{id} | `asset show` |
| POST | /organization/{orgid}/asset | `asset create` |
| POST | /organization/{orgid}/asset/bulk | `asset create-bulk` |
| PUT | /organization/{orgid}/asset/{id} | `asset update` |
| PATCH | /organization/{orgid}/asset/{id} | `asset update-asset` |
| DELETE | /organization/{orgid}/asset/{id} | `asset delete` |
| GET | /organization/{orgid}/asset/{id}/incoming-references | `asset list-incoming-references` |

---

## 18. Gotchas

1. **CC dial plans are separate from Webex Calling dial plans.** Different API, different base URL (`api.wxcc-{region}.cisco.com` vs `webexapis.com`), different configuration model. Do not confuse the CC group `wxcli cc-dial-plan` with the Webex Calling dial plan commands, which live under `wxcli call-routing` (`list-dial-plans`, `create`, `show-dial-plans`, `update-dial-plans`, `delete`). There is no top-level `dial-plan` group.

2. **Dial numbers have a "delete all" endpoint.** `wxcli cc-dial-number delete` (DELETE /organization/{orgid}/dial-number) deletes ALL dialed number mappings in the org. To delete a single mapping, use `wxcli cc-dial-number delete-dial-number <id>`.

3. **Callbacks use runtime paths, not config paths.** The callback API uses `/v1/callbacks/organization/{orgId}/scheduled-callback`, not the standard `/organization/{orgid}/` config pattern.

4. **Campaign APIs use `/v1/dialer/` paths.** These are separate from both the config API and the callback API. Campaign start/stop/update all go through the dialer runtime API.

5. **Contact list and DNC APIs use `/v3/campaign-management/` paths.** Yet another path family, distinct from both config and dialer paths. All require a campaign ID in the path.

6. **Flow APIs use `/{orgId}/project/{projectId}/flows` (the `cc-flow` commands call this path).** This is the only path family that requires a `projectId`. You must know your project ID before working with flows.

7. **Data Sources use `/dataSources` (no orgId prefix).** The only resource in this doc that does not include the org ID in the URL path. Auth still determines the org context.

8. **Outdial ANI has a two-level structure.** ANI profiles contain ANI entries. Entry-level operations require both the parent ANI ID (`outDialAniId`) and the entry ID. The `list-entry-outdial-ani` and `list-entry-outdial-ani-1` commands list entries at different API versions.

9. **The captures endpoint uses POST for queries.** `wxcli cc-captures create` is named `create` because it uses POST, but it performs a search/query operation. The request body contains search filters, not a new resource to create.

10. **EWT is read-only.** A single GET endpoint with no write operations. It reports queue wait time estimates, not configuration.

11. **Five distinct path families.** This doc's endpoint tables cover the five URL patterns below. The flow-store `/flow-store/{orgId}/...` API, a sixth family on its own host, is covered since 2026-10-19 by the Flow Store groups (§ 11 "Flow Store groups"; `cc-flow-store`, `cc-flow-versions`, `cc-flow-tracing`, `cc-flow-prefs`, `cc-flow-projects`, `cc-flow-connectors` on the Flow Store host `https://flow-store.produs1.ciscoccservice.com/flow-store`; ADR-19). (History: on 2026-10-13 this gotcha said the flow-store API was not covered because the then-tried hosts did not work with production tokens.) The five patterns:
    - `/organization/{orgid}/...` -- Config API (dial plans, dial numbers, outdial ANI, contact numbers, overrides, audio files, resource collections)
    - `/v1/callbacks/...` -- Callback runtime API
    - `/v1/dialer/...` and `/v1/captures/...` -- Dialer and capture runtime APIs
    - `/v3/campaign-management/...` -- Campaign management API
    - `/dataSources/...` -- Data sources API

12. **`cc-callbacks create` fails until an entry point has callbacks enabled.** Verified live 2026-09-14: create returns HTTP 400 `Callback default Entry Point is not configured` on an org where no entry point has `callbackEnabled: true`, even with every required field valid. Enable callbacks on an entry point first (`wxcli cc-entry-point` — see `contact-center-core.md`), then retry. `cc-callbacks list` is unaffected and returns 200 with `totalRecords: 0`.

13. **`cc-callbacks list` requires a filter.** At least one of `--callback-number` or `--assignee-agent` must be passed; there is no org-wide "list every callback" call.

14. **Before wxcli 1.7.6.1, every `/v1/` Contact Center command called the wrong URL (404).** The generator stripped the spec's `/v1` prefix for all paths because the Webex Calling base URL already ends in `/v1` — but the CC base URL (`https://api.wxcc-{region}.cisco.com`) does not. Affected: `cc-callbacks`, `cc-tasks`, `cc-agents`, `cc-call-monitoring`, `cc-subscriptions`, `cc-journey` (progressive-profile/events), `cc-campaign` (dialer), `cc-agent-wellbeing`, `cc-captures`, `cc-ewt`, `cc-notification`, `cc-queue-stats`, `cc-realtime`. Unversioned config paths (`/organization/{orgid}/...`) were never affected. If an older wxcli returns 404 on one of these, upgrade.

12. **CC config APIs need `cjp:config_read` / `cjp:config_write` on the token.** Verified live 2026-10-13: a full-admin personal access token (PAT) from developer.webex.com worked on org "CC Bootcamp Sandbox" — `cc-flow` list/show/export/list-validate/create-validate/create-lock/create-unlock, `cc-queue list`, `cc-entry-point list` and `cc-global-vars list-cad-variable` all returned 200, no 403. (An April 2026 claim that PATs get 403 came from global variables on this same org; that now returns 200.) If you get a 403 (`ccconfig_` trackingId), the token lacks those scopes: use an OAuth integration or Service App with them selected and re-authorize after adding scopes; also run `wxcli set-cc-region <region>` and verify the region.

13. **Region matters.** All CC API calls go to `api.wxcc-{region}.cisco.com`. Valid regions: `us1`, `eu1`, `eu2`, `anz1`, `ca1`, `jp1`, `sg1`. Using the wrong region returns 401/403. Set with `wxcli set-cc-region`.

14. **Bulk operations use different patterns.** Config resources support `/bulk` (POST for bulk save) and `/bulk-export` (GET for bulk export). The bulk save `create` commands expect an `items` array with `requestAction` per item.

15. **`/bulk-export` endpoints deprecated April 2026.** The GET `/bulk-export` endpoints are deprecated in favor of the list endpoints. Prefer `list-dial-plan`, `list-dial-number-v2`, `list-outdial-ani`, `list-overrides`, `list-audio-file`, etc. Dial plans, outdial ANIs, overrides, and audio files no longer have a `list-bulk-export` command at all -- use their list command with `-o json` instead. A `list-bulk-export` command still exists for `cc-dial-number`, `cc-contact-number`, `cc-entry-point`, `cc-site`, `cc-address-book`, `cc-aux-code`, and `cc-multimedia-profile` (and `cc-global-vars list` / `cc-work-types list` are bulk exports too), but should not be used in new code. **Before 2026-10-13 the seven `*/*`-typed bulk exports printed 0 rows**: their records sit under `resources`, which the CLI never extracted, and a false "server has more pages" note followed (`cc-global-vars list`: 0 of the org's variables). Fixed in the generator; live 2026-10-13 they return 13 aux codes, 3 dial numbers, 9 global variables, 2 multimedia profiles, 7 inbound entry points, 1 site. Their `pageNumber` field does NOT track the page served (page=0 → 1, page=1 → 2, page=2 → 2); read `rel` (`next`/`last`) instead — the CLI does.

16. **Posting JDS events from Flow Designer requires `workspaceId` as a query parameter.** Use an HTTP Request node with method POST and full absolute URL: `https://api.wxcc-us1.cisco.com/publish/v1/api/event?workspaceId={{CJDS_Workspace_ID}}`. The body does not contain `workspaceId` — it goes on the query string only. Minimum body:
    ```json
    {
      "id": "{{DialedDNIS}}-{{CallerANI}}",
      "specversion": "1.0",
      "type": "custom:your_event_type",
      "source": "wxcc_flow",
      "identity": "{{CallerANI}}",
      "identitytype": "phone",
      "datacontenttype": "application/json",
      "data": {}
    }
    ```

17. **Flow Designer HTTP connector requires a full absolute URL.** Relative paths like `/publish/v1/api/event` return HTTP 500 "is not a valid HTTP URL". Always prefix with `https://api.wxcc-{region}.cisco.com`.

18. **Use JDS alias lookup to detect returning callers in a flow.** Query `GET /admin/v1/api/person/workspace-id/{workspaceId}/aliases/{callerANI}` at flow entry. If the person exists and has prior events (events with timestamps before the current contact), they are a returning caller. If NOT_FOUND or no prior events, treat as first-time. WXCC writes ANI in E.164 format (`+19103915567`) — pass the number with `+1` prefix in the lookup or it will miss.

19. **`cc-flow create-validate` / `list-validate` verdicts are not authoritative, and `publish` does not enforce them.** Verified live 2026-10-13: `valid:false` came back for correct flows because of two proven false positives (`default` rejected as the `ivr-collectdigits` success edge, which Designer writes — on 2026-10-19 an edge with no `condition` validated clean; FC1038 on every `{{Node.Output}}` reference except the start node's), only one edge-condition error is reported per call, and a draft that `list-validate` flagged `ERROR FC1038` published with no skip-validation flag passed. Use validate to find real errors (FC1015, FC1024, missing start-node fields), not as a pass/fail gate. Details and the working body shape are in §11, "Building a flow from scratch".

---

## 19. See Also

- [Contact Center: Core](contact-center-core.md) -- Agents, queues, teams, skills, desktop, configuration. Go here after sections 15-16: entry points live in that doc, and an entry point is what a channel or asset is ultimately attached to, so `list-incoming-references` on either resource returns entities documented there
- [Contact Center: Analytics](contact-center-analytics.md) -- AI, monitoring, subscriptions, tasks, search. It also carries Usage Reports, which is where you go to measure how much traffic the channels and assets in sections 15-16 actually carried
- [Contact Center: Journey](contact-center-journey.md) -- JDS: workspaces, persons, identity, profile views, events
- [Contact Center: Agent Desktop SDK](contact-center-agent-sdk.md) -- The `@webex/contact-center` JS SDK. Relevant here because a Flow Designer **Set Variable** node marked *Agent Viewable* is what makes a variable appear in `interaction.callFlowParams` on the agent's desktop
- [Call Routing & PSTN](call-routing.md) -- Webex Calling routing (trunks, route groups, route lists -- entirely separate from CC routing)
- [Authentication](authentication.md) -- CC-specific OAuth scopes and region configuration
