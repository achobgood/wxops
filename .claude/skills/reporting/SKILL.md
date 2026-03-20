---
name: reporting
description: |
  Query and analyze Webex Calling reporting and analytics: Detailed Call History (CDR),
  Call Queue statistics, Auto Attendant statistics, call quality, report templates,
  and converged recordings. Guides the user from query design through data retrieval and analysis.
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [report-type]
---

# Reporting & Analytics Workflow

## Step 1: Load references

1. Read `docs/reference/reporting-analytics.md` for CDR fields, report templates, API constraints
2. Read `docs/reference/authentication.md` for auth token conventions

## Step 2: Verify auth token

Before any API calls, confirm the user has a working auth token:

```bash
wxcli whoami
```

If this fails, stop and resolve authentication first (`wxcli configure`).

### Required scopes by report type

| Report Type | Scope | Additional Requirements |
|-------------|-------|------------------------|
| CDR (Detailed Call History) | `spark-admin:calling_cdr_read` | Admin must have "Webex Calling Detailed Call History API access" role enabled in Control Hub |
| Report Templates & Reports | `analytics:read_all` | Admin must be read-only or full administrator. Org must have **Pro Pack for Cisco Webex** license. |
| Converged Recordings | `spark-admin:telephony_config_read` | Admin recordings use `/admin/convergedRecordings` endpoint |
| Recording Reports | `spark-admin:telephony_config_read` | Audit reports for recording access |
| Partner Reports | `analytics:read_all` | Partner admin scope; uses partner-specific templates |

### Scope verification gate

After identifying the report type (Step 3), verify the token has the required scope:
- **CDR:** Run `wxcli cdr list --start-time <recent> --end-time <recent> -o json` — if 403, token lacks `spark-admin:calling_cdr_read`
- **Reports/Templates:** Run `wxcli report-templates show -o json` — if 403, token lacks `analytics:read_all` or org lacks Pro Pack
- **Recordings:** Run `wxcli recordings list --limit 1 -o json` — if 403, token lacks `spark-admin:telephony_config_read`
- **Do not proceed to Step 4 until the required scope is confirmed.**

## Step 3: Identify the reporting need

Ask the user what they want to analyze. Present this decision matrix if they are unsure:

| Need | Report Type | CLI Group |
|------|-------------|-----------|
| Recent call logs (who called whom, when, duration, outcome) | **CDR / Detailed Call History** | `wxcli cdr` |
| Call queue performance (wait times, abandonment, volume) | **Call Queue Stats report** | `wxcli reports` + `wxcli report-templates` |
| Per-agent queue performance (handle time, calls handled) | **Call Queue Agent Stats report** | `wxcli reports` + `wxcli report-templates` |
| Auto attendant call volumes and menu usage | **AA Stats report** | `wxcli reports` + `wxcli report-templates` |
| Auto attendant key-press patterns by time period | **AA Business/After-Hours Key Details report** | `wxcli reports` + `wxcli report-templates` |
| Call quality (jitter, latency, packet loss) | **Calling Quality / Media Quality report** | `wxcli reports` + `wxcli report-templates` |
| Call usage trends and adoption | **Calling Engagement report** | `wxcli reports` + `wxcli report-templates` |
| Call recordings (list, download, manage) | **Converged Recordings** | `wxcli recordings` |
| Recording access audit | **Recording Reports** | `wxcli recording-report` |
| Partner-level report generation | **Partner Reports** | `wxcli partner-reports` |

## Step 4: Check prerequisites

#### 6b-i. Date range validation
- CDR Feed/Stream: max 12-hour window per request, data available for last 30 days only
- Reports API: date range depends on template's `max_days` value, format is `YYYY-MM-DD`
- Confirm the user's desired date range fits within these constraints; split into multiple requests if needed

#### 6b-ii. Data availability
- CDR has a minimum 5-minute delay; recent calls may not appear yet
- Reports are async (CSV generation takes minutes to hours depending on data volume)
- Converged recordings require the recording feature to be enabled on the org

#### 6b-iii. Confirm report selection
- Confirm the report type identified in Step 3 with the user before proceeding
- If multiple report types are needed, plan the execution order

## Step 5: Build and present deployment plan -- [SHOW BEFORE EXECUTING]

Present the following to the user before executing any queries:

```
REPORTING PLAN
==============
Report type:    {CDR / Queue Stats / AA Stats / Call Quality / Report Template / Recordings}
Date range:     {start} to {end}
Filters:        {location, user, direction, etc.}
Commands:       {list of wxcli commands to run}
Analysis plan:  {what metrics/aggregations to compute}
Expected output: {table, JSON, summary stats}
```

**DO NOT execute until the user approves this plan.**

## Step 6: Execute via wxcli

#### 6d-i. CDR / Detailed Call History

Use `wxcli cdr` for near-real-time call record queries. This is the most common reporting need.

### 6a-i. CDR Feed (batch/historical)

```bash
wxcli cdr list \
  --start-time "2026-03-18T14:00:00.000Z" \
  --end-time "2026-03-18T16:00:00.000Z" \
  -o json
```

### 6a-ii. CDR Stream (near-real-time, lower latency)

```bash
wxcli cdr list-cdr_stream \
  --start-time "2026-03-19T10:00:00.000Z" \
  --end-time "2026-03-19T12:00:00.000Z" \
  -o json
```

### 6a-iii. Filter by location

```bash
wxcli cdr list \
  --start-time "2026-03-18T14:00:00.000Z" \
  --end-time "2026-03-18T16:00:00.000Z" \
  --locations "San Jose,Austin" \
  -o json
```

### 6a-iv. Common CDR analysis patterns

After retrieving CDR data with `-o json`, pipe to `jq` or `python` for analysis:

**Missed calls:**
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
missed = [r for r in data if r.get('Answer indicator') == 'No']
print(f'Missed calls: {len(missed)}')
for c in missed[:10]:
    print(f\"  {c.get('Start time')} | {c.get('Calling number')} -> {c.get('Called number')} | {c.get('Call outcome reason')}\")
"
```

**Calls by direction (inbound vs outbound):**
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
counts = Counter(r.get('Direction') for r in data)
for d, c in counts.items():
    print(f'{d}: {c}')
"
```

**Average call duration:**
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
durations = [int(r.get('Duration', 0)) for r in data if r.get('Answer indicator') == 'Yes']
if durations:
    print(f'Answered calls: {len(durations)}')
    print(f'Avg duration: {sum(durations)/len(durations):.0f}s')
    print(f'Max duration: {max(durations)}s')
"
```

**Busiest hours (call volume by hour):**
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
hours = Counter(r.get('Start time', '')[:13] for r in data)
for h, c in sorted(hours.items()):
    print(f'{h}: {c} calls')
"
```

### 6a-v. CDR key fields reference

| Field | Description |
|-------|-------------|
| `Start time` | Call start (UTC) |
| `Answer time` | When answered (UTC) |
| `Duration` | Call length in seconds |
| `Direction` | `ORIGINATING` or `TERMINATING` |
| `Calling number` | Caller's number |
| `Called number` | Destination number |
| `Call outcome` | `Success`, `Failure`, or `Refusal` |
| `Call outcome reason` | `Normal`, `UserBusy`, `NoAnswer`, `CallRejected`, etc. |
| `User` | User who made/received the call |
| `Location` | Location name |
| `Call type` | `SIP_ENTERPRISE`, `SIP_NATIONAL`, `SIP_INTERNATIONAL`, etc. |
| `Client type` | `SIP`, `WXC_CLIENT`, `WXC_DEVICE`, etc. |
| `Answer indicator` | `Yes`, `No`, or `Yes-PostRedirection` |

See `docs/reference/reporting-analytics.md` Section 1 for the full 55+ field reference.

#### 6d-ii. Queue statistics

Queue statistics are generated via the **Reports API** as CSV reports. They are NOT available in real-time like CDR.

#### 6b-i. Discover available templates

```bash
wxcli report-templates show -o json
```

Look for templates with "Call Queue" in the title:
- **Call Queue Stats** -- queue-level KPIs (incoming volume, wait times, abandonment rates, handling efficiency)
- **Call Queue Agent Stats** -- per-agent performance (calls handled, average handle time, service level)

#### 6b-ii. Create a queue stats report

```bash
wxcli reports create \
  --template-id TEMPLATE_ID \
  --start-date "2026-03-01" \
  --end-date "2026-03-15"
```

The `--template-id` comes from `wxcli report-templates show`. Template IDs are org-specific -- always discover them at runtime.

#### 6b-iii. Check report status and download

Reports are generated asynchronously. Use `wxcli partner-reports` to list and check status:

```bash
wxcli partner-reports list -o json
wxcli partner-reports show REPORT_ID -o json
```

Poll until `status` is `"done"`, then use the `downloadURL` to fetch the CSV ZIP file.

#### 6b-iv. Key queue metrics available

| Metric | Description |
|--------|-------------|
| Incoming calls | Total calls entering the queue |
| Calls handled | Calls answered by agents |
| Calls abandoned | Calls where caller hung up before answer |
| Average wait time | Mean time in queue before answer |
| Average handle time | Mean agent talk time |
| Service level | Percentage of calls answered within threshold |
| Agent utilization | Per-agent breakdown of handled calls |

#### 6d-iii. Auto Attendant statistics

AA statistics are also generated via the Reports API.

#### 6c-i. Available AA report templates

- **Auto-attendant Stats Summary** -- overall AA performance (call volume, handling metrics)
- **Auto-attendant Business & After-Hours Key Details** -- DTMF key press patterns by time period

#### 6c-ii. Create an AA stats report

```bash
wxcli report-templates show -o json
# Find the AA template ID, then:
wxcli reports create \
  --template-id AA_TEMPLATE_ID \
  --start-date "2026-03-01" \
  --end-date "2026-03-15"
```

#### 6c-iii. Real-time AA key press data

The CDR field `Auto Attendant Key Pressed` is available in real-time CDR records. Use `wxcli cdr list` and filter for AA interactions:

```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
aa_calls = [r for r in data if r.get('Auto Attendant Key Pressed')]
for c in aa_calls:
    print(f\"{c.get('Start time')} | Key: {c.get('Auto Attendant Key Pressed')} | {c.get('Calling number')}\")
"
```

### 6d. Call quality metrics

Call quality data is available via report templates, not real-time CDR.

#### 6d-i. Available quality report templates

- **Calling Media Quality** -- per-call-leg quality measurements (latency, jitter, packet loss)
- **Calling Quality** -- client-side quality from the Webex Calling app

#### 6d-ii. Create a quality report

```bash
wxcli report-templates show -o json
# Find the quality template ID, then:
wxcli reports create \
  --template-id QUALITY_TEMPLATE_ID \
  --start-date "2026-03-01" \
  --end-date "2026-03-15"
```

#### 6d-iii. CDR-based quality indicators

While CDR does not contain jitter/latency, you can identify quality issues through outcome fields:

```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
failed = [r for r in data if r.get('Call outcome') in ('Failure', 'Refusal')]
print(f'Failed/refused calls: {len(failed)} of {len(data)} total')
for c in failed[:10]:
    print(f\"  {c.get('Start time')} | {c.get('User')} | {c.get('Call outcome')}: {c.get('Call outcome reason')}\")
"
```

### 6e. Report templates -- full lifecycle

The Reports API supports a complete workflow: discover templates, create reports, poll status, download CSVs, and clean up.

#### 6e-i. List all available report templates

```bash
wxcli report-templates show -o json
```

#### 6e-ii. Create a report

```bash
wxcli reports create \
  --template-id TEMPLATE_ID \
  --start-date "2026-03-01" \
  --end-date "2026-03-15"
```

Date format is `YYYY-MM-DD`. The maximum date range depends on the template's `max_days` value.

#### 6e-iii. Partner report templates (partner admins only)

```bash
# List partner-specific templates
wxcli partner-reports list-templates -o json

# Create a partner report
wxcli partner-reports create \
  --template-id TEMPLATE_ID \
  --start-date "2026-03-01" \
  --end-date "2026-03-15"

# List generated reports
wxcli partner-reports list -o json

# Check report status
wxcli partner-reports show REPORT_ID -o json

# Delete a report (free quota)
wxcli partner-reports delete REPORT_ID
```

#### 6e-iv. Standard Webex Calling report templates

| Template Name | Description |
|---------------|-------------|
| Detailed Call History | Comprehensive call log (all CDR fields) |
| Calling Media Quality | Per-call-leg quality (latency, jitter, packet loss) |
| Calling Engagement | Usage and adoption tracking |
| Calling Quality | Client-side quality from Webex Calling app |
| Call Queue Stats | Queue-level KPIs |
| Call Queue Agent Stats | Per-agent queue performance |
| Auto-attendant Stats Summary | AA call volume and handling |
| Auto-attendant Business & After-Hours Key Details | AA key-press patterns by time period |

### 6f. Converged recordings

Manage call recordings -- list, view details, reassign, and clean up.

#### 6f-i. List recordings (user-level)

```bash
wxcli recordings list -o json

# Filter by date range
wxcli recordings list --from "2026-03-01T00:00:00Z" --to "2026-03-18T00:00:00Z" -o json

# Filter by service type (calling only)
wxcli recordings list --service-type calling -o json

# Filter by location
wxcli recordings list --location-id LOCATION_ID -o json

# Filter by owner type
wxcli recordings list --owner-type user -o json

# Filter by status
wxcli recordings list --status available -o json
```

#### 6f-ii. List recordings (admin/compliance)

```bash
wxcli recordings list-converged-recordings -o json

# Filter by owner
wxcli recordings list-converged-recordings --owner-email user@company.com -o json
wxcli recordings list-converged-recordings --owner-id USER_ID -o json
```

#### 6f-iii. View recording details and metadata

```bash
wxcli recordings show RECORDING_ID -o json
wxcli recordings show-metadata RECORDING_ID -o json

# Include all attribute types (not just default subset)
wxcli recordings show-metadata RECORDING_ID --show-all-types true -o json
```

#### 6f-iv. Manage recordings

```bash
# Reassign recordings to a new owner
wxcli recordings create --json-body '{"reassignOwnerEmail": "newowner@company.com", "ownerEmail": "oldowner@company.com"}'

# Move recordings to recycle bin
wxcli recordings create-soft-delete --json-body '{"trashAll": true, "ownerEmail": "user@company.com"}'

# Restore recordings from recycle bin
wxcli recordings create-restore --json-body '{"restoreAll": true, "ownerEmail": "user@company.com"}'

# Purge recordings permanently from recycle bin
wxcli recordings create-purge --json-body '{"purgeAll": true, "ownerEmail": "user@company.com"}'

# Delete a single recording
wxcli recordings delete RECORDING_ID
```

#### 6f-v. Recording audit reports

```bash
# Access summary (who accessed which recordings)
wxcli recording-report list -o json

# Access detail
wxcli recording-report list-access-detail -o json

# Meeting archive summaries
wxcli recording-report list-meeting-archive-summaries -o json

# Meeting archive detail
wxcli recording-report show ARCHIVE_ID -o json
```

## Step 7: Verify

After retrieving data, verify the results make sense and present key findings to the user.

### Quick verification checks

```bash
# Verify CDR data is returning (simple count)
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "import json,sys; data=json.load(sys.stdin); print(f'Records returned: {len(data)}')"

# Verify report templates are accessible
wxcli report-templates show -o json | python3.11 -c "import json,sys; data=json.load(sys.stdin); print(f'Templates available: {len(data)}')"

# Verify recordings access
wxcli recordings list --limit 5 -o json
```

### Common analysis recipes

**Call volume by location:**
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
locations = Counter(r.get('Location', 'Unknown') for r in data)
for loc, count in locations.most_common():
    print(f'{loc}: {count} calls')
"
```

**International call summary (billing):**
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
intl = [r for r in data if r.get('Call type') == 'SIP_INTERNATIONAL']
total_dur = sum(int(r.get('Duration', 0)) for r in intl)
print(f'International calls: {len(intl)}')
print(f'Total duration: {total_dur}s ({total_dur/60:.1f} min)')
"
```

**Recording compliance audit:**
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
results = Counter(r.get('Call recording result') for r in data if r.get('Call recording result'))
for result, count in results.most_common():
    print(f'{result}: {count}')
"
```

**Calls per user (top talkers):**
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
users = Counter(r.get('User', 'Unknown') for r in data)
for user, count in users.most_common(10):
    print(f'{user}: {count} calls')
"
```

## Step 8: Report results

Present findings to the user in a structured format:

- **Data retrieved:** Report type, date range, record count
- **Key findings:** Top metrics, trends, anomalies discovered
- **Data quality notes:** Any gaps, missing records, or incomplete data
- **Next steps:** Recommended follow-up queries or actions
- **Cleanup reminders:** Delete reports to free quota if applicable

---

## Critical Rules

1. **CDR is NOT real-time.** There is a minimum 5-minute delay before records appear. Data may take up to 24 hours to fully populate. Do not expect to see a call that just happened.
2. **12-hour maximum query window.** CDR Feed/Stream requests cannot span more than 12 hours between `startTime` and `endTime`. For longer ranges, issue multiple sequential requests with consecutive 12-hour windows.
3. **30-day data retention.** CDR data is only available for the last 30 days. Older data must be retrieved via Reports API (CSV).
4. **Date/time format matters.** CDR uses ISO 8601 with milliseconds: `2026-03-18T14:00:00.000Z`. Reports API uses `YYYY-MM-DD` date format for `startDate`/`endDate`.
5. **Regional endpoints.** If CDR returns HTTP 451, the response body contains the correct regional endpoint URL. Retry with that URL.
6. **Rate limits are strict.** CDR allows 1 request/minute + 10 pagination requests/minute per user token. Do not hammer the endpoint.
7. **Report quota: max 50 reports.** Only 50 reports can exist at any time. Always delete reports after downloading to free quota. Use `wxcli partner-reports delete REPORT_ID`.
8. **Pro Pack required for Reports API.** The `wxcli reports` and `wxcli report-templates` commands require the Pro Pack for Cisco Webex license on the org. CDR Feed does NOT require Pro Pack.
9. **Template IDs are org-specific.** Never hardcode template IDs. Always discover them at runtime with `wxcli report-templates show`.
10. **Reports are async CSV/ZIP.** Creating a report returns a report ID. Poll `wxcli partner-reports show REPORT_ID` until `status` is `"done"`, then use `downloadURL` to fetch the ZIP file containing CSV data.
11. **CDR field names use spaces.** The raw API returns field names like `"Start time"`, `"Call outcome reason"`, `"Answer indicator"`. Use these exact names when processing JSON output.
12. **Location filter uses names, not IDs.** The CDR `--locations` parameter takes location names as shown in Control Hub, not location IDs. Up to 10 locations, comma-separated.
13. **Recording management is destructive.** `create-purge` permanently deletes recordings. Always confirm with the user before purging. `create-soft-delete` moves to recycle bin (recoverable via `create-restore`).
14. **Converged recordings scope split.** User-level listing uses `wxcli recordings list`. Admin/compliance listing uses `wxcli recordings list-converged-recordings` (supports `--owner-email` and `--owner-id` filters).

---

## Scope Quick Reference

| Scope | Grants Access To |
|-------|-----------------|
| `spark-admin:calling_cdr_read` | CDR Feed and Stream (`wxcli cdr`) |
| `analytics:read_all` | Report Templates and Reports (`wxcli report-templates`, `wxcli reports`, `wxcli partner-reports`) |
| `spark-admin:locations_read` | Location name filtering on CDR queries |
| `spark-admin:telephony_config_read` | Converged recordings read (`wxcli recordings list`) |
| `spark-admin:telephony_config_write` | Recording management (reassign, delete, purge) |
| `spark-compliance:recordings_read` | Compliance officer recording access |

---

## Context Compaction Recovery

If context compacts mid-execution, recover by:
1. Read `docs/reference/reporting-analytics.md` to recover field references and API constraints
2. Check what data has already been retrieved by reviewing recent command output
3. Review Steps 1-8 and identify which step was in progress
4. Resume from the first incomplete step
