# Contact Center: Routing, Campaigns, Flows, and Media

Reference for Webex Contact Center routing configuration, campaign management, flow automation,
and media resources. Covers 15 CLI groups with 98 commands generated from the Contact Center OpenAPI spec.

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
15. [Consolidated Endpoint Reference](#15-consolidated-endpoint-reference)
16. [Gotchas](#16-gotchas)
17. [See Also](#17-see-also)

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
| `wxcli cc-dial-number delete` | DELETE /organization/{orgid}/dial-number | Delete all Dialed Number Mapping(s) |
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

- `--json-body` -- Full JSON body for create/update operations
- `id` (argument) -- Dialed number mapping ID for show/update/delete

### CLI Examples

```bash
# List all dialed number mappings (v2 with pagination)
wxcli cc-dial-number list-dial-number-v2

# List only the dialed numbers (no mapping details)
wxcli cc-dial-number list-numbers-only

# Get a specific mapping
wxcli cc-dial-number show <mapping-id>

# Create a new dialed number mapping
wxcli cc-dial-number create --json-body '{"dialNumber":"+15551234567","entryPointId":"ep-id-here"}'

# Delete a specific mapping
wxcli cc-dial-number delete-dial-number <mapping-id>

# CAUTION: Delete ALL dialed number mappings
wxcli cc-dial-number delete

# Bulk export all mappings
wxcli cc-dial-number list-bulk-export -o json
```

### Raw HTTP

```bash
# List dialed numbers (v2)
GET https://api.wxcc-us1.cisco.com/organization/{orgId}/v2/dial-number
Authorization: Bearer {cc_token}

# Create a dialed number mapping
POST https://api.wxcc-us1.cisco.com/organization/{orgId}/dial-number
Content-Type: application/json
{"dialNumber":"+15551234567","entryPointId":"ep-id-here"}

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

# Add an entry to an ANI profile
wxcli cc-outdial-ani create-entry <ani-id> --json-body '{"dialNumber":"+15551234567"}'

# List entries for a specific ANI (v2)
wxcli cc-outdial-ani list-entry-outdial-ani-1 <ani-id>

# Delete an ANI entry
wxcli cc-outdial-ani delete-entry <ani-id> <entry-id>

# Dump all ANIs as JSON (there is no bulk-export command for outdial ANIs)
wxcli cc-outdial-ani list-outdial-ani -o json
```

### Raw HTTP

```bash
# List outdial ANIs (v2)
GET https://api.wxcc-us1.cisco.com/organization/{orgId}/v2/outdial-ani
Authorization: Bearer {cc_token}

# Create an entry under an ANI profile
POST https://api.wxcc-us1.cisco.com/organization/{orgId}/outdial-ani/{outDialAniId}/entry
Content-Type: application/json
{"dialNumber":"+15551234567"}
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
wxcli cc-contact-number create --json-body '{"name":"+15551234567","type":"TOLL_FREE"}'

# Bulk export
wxcli cc-contact-number list-bulk-export -o json

# Delete a contact number
wxcli cc-contact-number delete <number-id>
```

### Raw HTTP

```bash
# List all contact numbers
GET https://api.wxcc-us1.cisco.com/organization/{orgId}/contact-number/all-numbers
Authorization: Bearer {cc_token}

# Create a contact number
POST https://api.wxcc-us1.cisco.com/organization/{orgId}/contact-number
Content-Type: application/json
{"name":"+15551234567","type":"TOLL_FREE"}
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
# List all scheduled callbacks
wxcli cc-callbacks list

# Get a specific callback
wxcli cc-callbacks show <callback-id>

# Schedule a new callback
wxcli cc-callbacks create --json-body '{"callbackNumber":"+15551234567","queueId":"queue-id","scheduledTime":"2026-04-01T10:00:00Z"}'

# Update a scheduled callback
wxcli cc-callbacks update <callback-id> --json-body '{"scheduledTime":"2026-04-01T14:00:00Z"}'

# Cancel a callback
wxcli cc-callbacks delete <callback-id>
```

### Raw HTTP

```bash
# List scheduled callbacks
GET https://api.wxcc-us1.cisco.com/v1/callbacks/organization/{orgId}/scheduled-callback
Authorization: Bearer {cc_token}

# Schedule a callback
POST https://api.wxcc-us1.cisco.com/v1/callbacks/organization/{orgId}/scheduled-callback
Content-Type: application/json
{"callbackNumber":"+15551234567","queueId":"queue-id","scheduledTime":"2026-04-01T10:00:00Z"}
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
wxcli cc-overrides update <override-id> --json-body '{"active":true}'

# Delete an override
wxcli cc-overrides delete <override-id>

# Dump all overrides as JSON (there is no bulk-export command for overrides)
wxcli cc-overrides list-overrides -o json
```

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
- **`--page` / `--page-size` are the endpoint's own paging controls**, separate from `--limit` / `--offset`. `--page-size` must be between 1 and 100. Use `--all` to walk every page.
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
wxcli cc-contact-list create <campaign-id> --json-body '{"name":"Q1-List","contacts":[]}'

# Add contacts to a list
wxcli cc-contact-list create-contacts <campaign-id> <list-id> --json-body '{"contacts":[{"phoneNumber":"+15551234567","firstName":"Jane"}]}'

# Update a contact's status
wxcli cc-contact-list update <campaign-id> <list-id> <contact-id> --json-body '{"status":"DO_NOT_CALL"}'

# Update list status (activate/deactivate)
wxcli cc-contact-list update-status <campaign-id> <list-id> --json-body '{"status":"ACTIVE"}'

# Add a phone number to DNC list
wxcli cc-dnc create <dnc-list-name> --json-body '{"phoneNumber":"+15559876543"}'

# Check if a number is on the DNC list
wxcli cc-dnc show <dnc-list-name> +15559876543

# Remove a number from DNC list
wxcli cc-dnc delete <dnc-list-name> +15559876543
```

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

- `--json-body` -- Query body with filters (required)

### CLI Examples

```bash
# Query captures for a date range
wxcli cc-captures create --json-body '{"from":"2026-03-01T00:00:00Z","to":"2026-03-28T23:59:59Z","filters":{"queueId":"queue-id"}}' -o json
```

### Raw HTTP

```bash
# Query captures
POST https://api.wxcc-us1.cisco.com/v1/captures/query
Content-Type: application/json
Authorization: Bearer {cc_token}
{"from":"2026-03-01T00:00:00Z","to":"2026-03-28T23:59:59Z"}
```

---

## 11. Flows (cc-flow)

Flows define the IVR and routing logic for contact center interactions. Subflows are reusable
components within flows. The Flow API supports listing, importing, exporting, drafting,
validating, locking, and publishing flows. Uses the `/{orgId}/project/{projectId}/flows` path
family -- note the `projectId` is required for all operations. 11 commands.

### Commands

| CLI Command | HTTP | Description |
|---|---|---|
| `wxcli cc-flow list` | GET /{orgId}/project/{projectId}/flows | List Flows or Subflows |
| `wxcli cc-flow show` | GET /{orgId}/project/{projectId}/v2/flows/{flowId} | Get a Flow |
| `wxcli cc-flow create-flows` | POST /{orgId}/project/{projectId}/v2/flows/{flowId} | Save a Flow Draft |
| `wxcli cc-flow update` | PATCH /{orgId}/project/{projectId}/v2/flows/{flowId} | Patch a Flow Draft |
| `wxcli cc-flow create-import` | POST /{orgId}/project/{projectId}/v2/flows:import | Import a Flow |
| `wxcli cc-flow export` | GET /{orgId}/project/{projectId}/v2/flows/{flowId}:export | Export a Flow |
| `wxcli cc-flow publish` | POST /{orgId}/project/{projectId}/flows/{flowId}:publish | Publish a Flow or Subflow |
| `wxcli cc-flow create-validate` | POST /{orgId}/project/{projectId}/v2/flows:validate | Validate a Flow |
| `wxcli cc-flow list-validate` | GET /{orgId}/project/{projectId}/v2/flows/{flowId}:validate | Validate an existing Flow Draft |
| `wxcli cc-flow create-lock` | POST /{orgId}/project/{projectId}/flows/{flowId}:lock | Lock a Flow or Subflow |
| `wxcli cc-flow create-unlock` | POST /{orgId}/project/{projectId}/flows/{flowId}:unlock | Unlock a Flow or Subflow |

> **Argument-order trap:** `publish`, `create-lock`, and `create-unlock` take `FLOW_ID` **before**
> `PROJECT_ID`. Every other `cc-flow` command takes `PROJECT_ID` first. Always check `--help`.

### Key Parameters

- `project-id` (argument) -- Project ID (required for all commands)
- `flow-id` (argument) -- Flow ID (for show/draft/export/publish/lock/validate)
- `--flow-type` -- Filter by `FLOW` or `SUBFLOW`
- `--ids` -- Comma-separated list of flow IDs to filter (`list` only)
- `--partial-name-search` -- Partial name match filter (`list` only)
- `--page` / `--size` -- Pagination controls (`list` only)
- `--include-pagination` -- Include pagination metadata in response (`list` only)
- `--version` -- Version to export; use `latest` for the most recent published (`export` only)
- `--expected-version` -- Optimistic-locking guard for draft writes (`create-flows` / `update`)
- `--skip-validation` -- Skip pre-publish validation (`publish` only)
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

# Import a flow from exported JSON
wxcli cc-flow create-import <project-id> --json-body "$(cat flow-export.json)"

# Publish a flow -- NOTE: flow-id comes BEFORE project-id here
wxcli cc-flow publish <flow-id> <project-id>
```

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
{...flow definition JSON...}
```

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
wxcli cc-data-sources create --json-body '{"name":"Salesforce-CRM","type":"REST","url":"https://api.salesforce.com"}'

# Update a data source
wxcli cc-data-sources update <data-source-id> --json-body '{"name":"Salesforce-CRM-v2","url":"https://api2.salesforce.com"}'

# Delete a data source
wxcli cc-data-sources delete <data-source-id>
```

### Raw HTTP

```bash
# List all data sources
GET https://api.wxcc-us1.cisco.com/dataSources/
Authorization: Bearer {cc_token}

# Register a data source
POST https://api.wxcc-us1.cisco.com/dataSources
Content-Type: application/json
{"name":"Salesforce-CRM","type":"REST","url":"https://api.salesforce.com"}

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

## 15. Consolidated Endpoint Reference

All 98 endpoints across 15 CLI groups, grouped by resource.

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
| DELETE | /organization/{orgid}/dial-number | `cc-dial-number delete` |
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

### Flows (11)

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

---

## 16. Gotchas

1. **CC dial plans are separate from Webex Calling dial plans.** Different API, different base URL (`api.wxcc-{region}.cisco.com` vs `webexapis.com`), different configuration model. Do not confuse the CC group `wxcli cc-dial-plan` with the Webex Calling dial plan commands, which live under `wxcli call-routing` (`list-dial-plans`, `create`, `show-dial-plans`, `update-dial-plans`, `delete`). There is no top-level `dial-plan` group.

2. **Dial numbers have a "delete all" endpoint.** `wxcli cc-dial-number delete` (DELETE /organization/{orgid}/dial-number) deletes ALL dialed number mappings in the org. To delete a single mapping, use `wxcli cc-dial-number delete-dial-number <id>`.

3. **Callbacks use runtime paths, not config paths.** The callback API uses `/v1/callbacks/organization/{orgId}/scheduled-callback`, not the standard `/organization/{orgid}/` config pattern.

4. **Campaign APIs use `/v1/dialer/` paths.** These are separate from both the config API and the callback API. Campaign start/stop/update all go through the dialer runtime API.

5. **Contact list and DNC APIs use `/v3/campaign-management/` paths.** Yet another path family, distinct from both config and dialer paths. All require a campaign ID in the path.

6. **Flow APIs use `/flow-store/{orgId}/project/{projectId}/flows`.** This is the only path family that requires a `projectId`. You must know your project ID before working with flows.

7. **Data Sources use `/dataSources` (no orgId prefix).** The only resource in this doc that does not include the org ID in the URL path. Auth still determines the org context.

8. **Outdial ANI has a two-level structure.** ANI profiles contain ANI entries. Entry-level operations require both the parent ANI ID (`outDialAniId`) and the entry ID. The `list-entry-outdial-ani` and `list-entry-outdial-ani-1` commands list entries at different API versions.

9. **The captures endpoint uses POST for queries.** `wxcli cc-captures create` is named `create` because it uses POST, but it performs a search/query operation. The request body contains search filters, not a new resource to create.

10. **EWT is read-only.** A single GET endpoint with no write operations. It reports queue wait time estimates, not configuration.

11. **Five distinct path families.** This doc covers endpoints across five different URL patterns:
    - `/organization/{orgid}/...` -- Config API (dial plans, dial numbers, outdial ANI, contact numbers, overrides, audio files, resource collections)
    - `/v1/callbacks/...` -- Callback runtime API
    - `/v1/dialer/...` and `/v1/captures/...` -- Dialer and capture runtime APIs
    - `/v3/campaign-management/...` -- Campaign management API
    - `/flow-store/{orgId}/...` -- Flow store API
    - `/dataSources/...` -- Data sources API

12. **CC APIs require CC-scoped OAuth.** Standard Webex admin tokens will not work. You need tokens with `cjp:config_read` and/or `cjp:config_write` scopes. If you get a 403, run `wxcli set-cc-region <region>` and verify your token has CC scopes.

13. **Region matters.** All CC API calls go to `api.wxcc-{region}.cisco.com`. Valid regions: `us1`, `eu1`, `eu2`, `anz1`, `ca1`, `jp1`, `sg1`. Using the wrong region returns 401/403. Set with `wxcli set-cc-region`.

14. **Bulk operations use different patterns.** Config resources support `/bulk` (POST for bulk save) and `/bulk-export` (GET for bulk export). The bulk save `create` commands expect an `items` array with `requestAction` per item.

15. **`/bulk-export` endpoints deprecated April 2026.** The GET `/bulk-export` endpoints are deprecated in favor of the list endpoints. Prefer `list-dial-plan`, `list-dial-number-v2`, `list-outdial-ani`, `list-overrides`, `list-audio-file`, etc. Dial plans, outdial ANIs, overrides, and audio files no longer have a `list-bulk-export` command at all -- use their list command with `-o json` instead. A `list-bulk-export` command still exists for `cc-dial-number`, `cc-contact-number`, `cc-entry-point`, `cc-site`, `cc-address-book`, `cc-aux-code`, and `cc-multimedia-profile`, but should not be used in new code.

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

---

## 17. See Also

- [Contact Center: Core](contact-center-core.md) -- Agents, queues, teams, skills, desktop, configuration
- [Contact Center: Analytics](contact-center-analytics.md) -- AI, monitoring, subscriptions, tasks, search
- [Contact Center: Journey](contact-center-journey.md) -- JDS: workspaces, persons, identity, profile views, events
- [Contact Center: Agent Desktop SDK](contact-center-agent-sdk.md) -- The `@webex/contact-center` JS SDK. Relevant here because a Flow Designer **Set Variable** node marked *Agent Viewable* is what makes a variable appear in `interaction.callFlowParams` on the agent's desktop
- [Call Routing & PSTN](call-routing.md) -- Webex Calling routing (trunks, route groups, route lists -- entirely separate from CC routing)
- [Authentication](authentication.md) -- CC-specific OAuth scopes and region configuration
