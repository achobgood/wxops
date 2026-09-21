# v1.8.0 — weekly spec sync

**Verdict:** minor — new command group(s): asset, calling_metrics, channel, usage_reports

## New command groups

- `asset`
- `calling_metrics`
- `channel`
- `usage_reports`

### Routing decision

# Routing decisions — spec sync 2026-09-21

Four new command groups appeared in `_registry.py` this week. One line per group,
per contract §2 rule B.

- channel -> contact-center (a channel is the medium a CC contact arrives on; it is CC config, not a Webex messaging space and not a Calling concept)
- asset -> contact-center (an asset is one configured instance of a channel and is invalid without a channelId, so it belongs with the group that owns channels)
- usage-reports -> reporting-cc (CC consumption/billing extracts; the Calling-side `reporting` skill owns CDR, which is a different API and a different question)
- calling-metrics -> reporting (GET /v1/analytics/callQualityStats is a Webex Calling endpoint on webexapis.com, alongside the Calling Quality report the `reporting` skill already routes)

Reference-doc coverage written the same day (contract §2 rule C):

- channel, asset -> docs/reference/contact-center-routing.md §§ 15-16
- usage-reports -> docs/reference/contact-center-analytics.md § 14
- calling-metrics -> docs/reference/reporting-analytics.md § 4

Naming pins written this week (contract §2 rules A and D — D forbids acking, so
each of these is a rename, not an ack):

- cc-tasks create-pause / create-resume pinned back to the RECORDING endpoints
  (/tasks/{}/record/pause|resume). Upstream added task-level /tasks/{}/pause|resume,
  which collided and pushed both shipped names onto -record suffixes. The new
  task-level pair keeps the derived create-pause-tasks / create-resume-tasks.
- asset list -> list-incoming-references, channel list -> list-incoming-references,
  usage-reports list -> list-resource-types. In all three the generator gave the
  bare `list` to an operation that is not the group's headline collection.

## New commands

- `call_routing validate-a-trunk`
- `cc_tasks create-pause-tasks`
- `cc_tasks create-resume-tasks`
- `asset create`
- `asset create-bulk`
- `asset delete`
- `asset list-asset`
- `asset list-incoming-references`
- `asset show`
- `asset update`
- `asset update-asset`
- `calling_metrics show`
- `channel create`
- `channel delete`
- `channel list-channel`
- `channel list-incoming-references`
- `channel show`
- `channel update`
- `usage_reports create`
- `usage_reports delete`
- `usage_reports list-download`
- `usage_reports list-resource-types`
- `usage_reports list-usage-reports`
- `usage_reports show`

## Spec delta acknowledged by this sync (check 19)

```
spec-snapshot refresh: 29 structural, 0 ID-kind flip(s), 2 prose delta(s)
  STRUCTURAL   operation_added    webex-admin.json GET /analytics/callQualityStats
               Calling Metrics — Webex Calling Call Quality Stats
  STRUCTURAL   operation_added    webex-cloud-calling.json GET /analytics/callQualityStats
               Calling Metrics — Webex Calling Call Quality Stats
  STRUCTURAL   operation_added    webex-cloud-calling.json POST /telephony/config/premisePstn/trunks/actions/validate/invoke
               Call Routing — Validate a Trunk
  STRUCTURAL   required_removed   webex-cloud-calling.json GET /telephony/config/queues/agents/{} query:max
               spec requiredness changed
  STRUCTURAL   required_removed   webex-cloud-calling.json GET /telephony/config/queues/agents/{} query:start
               spec requiredness changed
  STRUCTURAL   field_added        webex-cloud-calling.json POST /telephony/config/premisePstn/trunks body:peerIdentity
               #72c936
  STRUCTURAL   field_added        webex-cloud-calling.json PUT /telephony/config/voicemail/settings body:voicePortalAccessVmDepositEnabled
               #bb9f42
  STRUCTURAL   operation_added    webex-contact-center.json DELETE /organization/{}/asset/{}
               Asset — Delete specific Asset by ID
  STRUCTURAL   operation_added    webex-contact-center.json DELETE /organization/{}/channel/{}
               Channel — Delete specific Channel by ID
  STRUCTURAL   operation_added    webex-contact-center.json DELETE /usage-reports/{}
               Usage Reports — Delete usage report
  STRUCTURAL   operation_added    webex-contact-center.json GET /organization/{}/asset/{}
               Asset — Get specific Asset by ID
  STRUCTURAL   operation_added    webex-contact-center.json GET /organization/{}/asset/{}/incoming-references
               Asset — List references for a specific Asset
  STRUCTURAL   operation_added    webex-contact-center.json GET /organization/{}/channel/{}
               Channel — Get specific Channel by ID
  STRUCTURAL   operation_added    webex-contact-center.json GET /organization/{}/channel/{}/incoming-references
               Channel — List references for a specific Channel
  STRUCTURAL   operation_added    webex-contact-center.json GET /organization/{}/v2/asset
               Asset — List Assets
  STRUCTURAL   operation_added    webex-contact-center.json GET /organization/{}/v2/channel
               Channel — List Channels
  STRUCTURAL   operation_added    webex-contact-center.json GET /usage-reports
               Usage Reports — List usage reports
  STRUCTURAL   operation_added    webex-contact-center.json GET /usage-reports/resource-types
               Usage Reports — Get available resource types
  STRUCTURAL   operation_added    webex-contact-center.json GET /usage-reports/{}
               Usage Reports — Get usage report details
  STRUCTURAL   operation_added    webex-contact-center.json GET /usage-reports/{}/download
               Usage Reports — Download usage report file
  STRUCTURAL   operation_added    webex-contact-center.json PATCH /organization/{}/asset/{}
               Asset — Partially update Asset by ID
  STRUCTURAL   operation_added    webex-contact-center.json PATCH /organization/{}/channel/{}
               Channel — Partially update Channel by ID
  STRUCTURAL   operation_added    webex-contact-center.json POST /organization/{}/asset
               Asset — Create a new Asset
  STRUCTURAL   operation_added    webex-contact-center.json POST /organization/{}/asset/bulk
               Asset — Bulk save Assets
  STRUCTURAL   operation_added    webex-contact-center.json POST /organization/{}/channel/bulk
               Channel — Bulk save Channels
  STRUCTURAL   operation_added    webex-contact-center.json POST /tasks/{}/pause
               Tasks — Pause Task
  STRUCTURAL   operation_added    webex-contact-center.json POST /tasks/{}/resume
               Tasks — Resume Task
  STRUCTURAL   operation_added    webex-contact-center.json POST /usage-reports
               Usage Reports — Create usage report
  STRUCTURAL   operation_added    webex-contact-center.json PUT /organization/{}/asset/{}
               Asset — Update specific Asset by ID
  PROSE        wording_changed    webex-cloud-calling.json POST /telephony/config/premisePstn/trunks/actions/fqdnValidation/invoke (operation)
               description text changed
  PROSE        summary_changed    webex-contact-center.json POST /tasks/{}/unhold (summary)
               'Resume Task' -> 'Unhold Task'
wrote tools/spec_semantics.json (captured 2026-09-21)
```

