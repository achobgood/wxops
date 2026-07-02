---
name: reporting
description: |
  Query and analyze Webex Calling reporting and analytics: Detailed Call History (CDR),
  Call Queue statistics, Auto Attendant statistics, call quality, report templates,
  converged recording download/export, and call volume trends. 75 CDR recipes + query
  composition guide for answering any natural-language question about a calling environment.
  NOT for: Contact Center analytics (use reporting-cc skill), meetings/workspace analytics
  (use reporting-meetings skill), or per-user recording toggle (use manage-call-settings skill).
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [report-type]
---

# Reporting & Analytics Workflow

**Checkpoint — do NOT proceed until you can answer these:**
1. What is the maximum date range for a single CDR query? (Answer: 12 hours per request. For longer ranges, issue multiple sequential requests.)
2. What base URL does CDR use? (Answer: `https://analytics-calling.webexapis.com` — different from the standard `webexapis.com` base. The CLI handles this automatically.)
3. CDR field names use spaces in JSON output — what format? (Answer: `"Start time"`, `"Call outcome reason"`, `"Answer indicator"` — use `r.get('Field Name')` in Python.)
4. Does `/tmp/cdr-session.json` exist and what window does it cover? (If yes, check the `_meta` object for `start` and `end` timestamps before re-pulling.)

If you cannot answer all four, read `docs/reference/reporting-analytics.md` before proceeding.

## Step 1: Load references

1. Read `docs/reference/reporting-analytics.md` for CDR fields, report templates, API constraints
2. The 75 CDR recipes live in `references/cdr-recipes.md` (this skill's `references/` dir) — load on demand when a question maps to a recipe; see the Recipe Catalog index under the CDR Query Composition Guide below

**Mandatory --help verification:** Before constructing any wxcli command, run `wxcli <group> --help` to verify the subcommand exists, then `wxcli <group> <subcommand> --help` to verify the exact flags (e.g. `wxcli cdr list --help` for call detail records, `wxcli reports --help` for templated reports — date-range and filter flag names are spec-generated). Even read commands differ by name (`show` vs `list`, known issue #5), so confirm before running. Do NOT rely on examples in this skill or reference docs — the CLI is auto-generated and flag names may differ from what documentation suggests.

## Step 2: Verify auth token

```bash
wxcli whoami
```

If this fails, stop and resolve authentication first (`wxcli configure`).

### Required scopes by report type

| Report Type | Scope | Additional Requirements |
|-------------|-------|------------------------|
| CDR (Detailed Call History) | `spark-admin:calling_cdr_read` | Admin must have "Webex Calling Detailed Call History API access" role enabled in Control Hub |
| Report Templates & Reports | `analytics:read_all` | Read-only or full admin. Org must have **Pro Pack for Cisco Webex** license. |
| Converged Recordings | `spark-admin:telephony_config_read` | Admin recordings use `/admin/convergedRecordings` endpoint |
| Recording Reports | `spark-admin:telephony_config_read` | Audit reports for recording access |
| Partner Reports | `analytics:read_all` | Partner admin scope |
| **Contact Center stats** | `cjp:config_read` | **Use the `reporting-cc` skill instead** |
| **Meeting quality/analytics** | `analytics:read_all` | **Use the `reporting-meetings` skill instead** |

### Scope verification gate

After identifying the report type (Step 3), verify the token has the required scope:
- **CDR:** Run `wxcli cdr list --start-time <recent> --end-time <recent> -o json` — if 403, token lacks `spark-admin:calling_cdr_read`
- **Reports/Templates:** Run `wxcli report-templates list -o json` — if 403, token lacks `analytics:read_all` or org lacks Pro Pack
- **Recordings:** Run `wxcli converged-recordings list --limit 1 -o json` — if 403, token lacks `spark-admin:telephony_config_read`
- **Do not proceed to Step 4 until the required scope is confirmed.**

## Step 3: Identify the reporting need

Ask the user what they want to analyze. Present this decision matrix if they are unsure:

| Need | Report Type | CLI Group |
|------|-------------|-----------|
| Recent call logs (who called whom, when, duration, outcome) | **CDR / Detailed Call History** | `wxcli cdr` |
| Any question about calls (volume, performance, devices, trunks, etc.) | **CDR + Recipe** | `wxcli cdr` + Python analysis |
| Call queue performance (wait times, abandonment, volume) | **Call Queue Stats report** | `wxcli reports` + `wxcli report-templates` |
| Per-agent queue performance (handle time, calls handled) | **Call Queue Agent Stats report** | `wxcli reports` + `wxcli report-templates` |
| Auto attendant call volumes and menu usage | **AA Stats report** | `wxcli reports` + `wxcli report-templates` |
| Call quality (jitter, latency, packet loss) | **Calling Quality / Media Quality report** | `wxcli reports` + `wxcli report-templates` |
| Call recordings (list, download, manage) | **Converged Recordings** | `wxcli converged-recordings` |
| Recording access audit | **Recording Reports** | `wxcli recording-report` |
| Partner-level report generation | **Partner Reports** | `wxcli partner-reports` |
| Contact Center queue/agent stats | **→ Use `reporting-cc` skill** | CC-scoped OAuth required |
| Meeting quality, workspace metrics | **→ Use `reporting-meetings` skill** | Standard admin scopes |

## Step 4: Check prerequisites

### Date range validation
- CDR Feed/Stream: max 12-hour window per request, data available for last 30 days only
- Reports API: date range depends on template's `max_days` value, format is `YYYY-MM-DD`
- Confirm the user's desired date range fits within these constraints; split into multiple requests if needed

### Data availability
- CDR has a minimum 5-minute delay; recent calls may not appear yet
- Reports are async (CSV generation takes minutes to hours depending on data volume)
- Converged recordings require the recording feature to be enabled on the org

## Step 5: Build and present deployment plan — [SHOW BEFORE EXECUTING]

Present the following to the user before executing any queries:

```
REPORTING PLAN
==============
Report type:    {CDR / Queue Stats / AA Stats / Call Quality / Recordings}
Date range:     {start} to {end}
Filters:        {location, user, direction, etc.}
Commands:       {list of wxcli commands to run}
Analysis plan:  {which recipe(s) or composition to apply}
Expected output: {table, JSON, summary stats}
```

**DO NOT execute until the user approves this plan.**

## Step 6: Execute via wxcli

### 6a. CDR / Detailed Call History

#### CDR Feed (batch/historical)

```bash
wxcli cdr list --start-time "2026-04-10T14:00:00.000Z" --end-time "2026-04-10T16:00:00.000Z" -o json
```

#### CDR Stream (near-real-time)

CDR Stream uses **database write time** (not call start time), has a **2-hour max window** and **12-hour retention**. Use it for near-real-time monitoring or to catch late-arriving records that Feed may miss.

```bash
wxcli cdr list-cdr_stream --start-time "2026-04-10T14:00:00.000Z" --end-time "2026-04-10T16:00:00.000Z" -o json
```

#### Filter by location

```bash
wxcli cdr list --start-time START --end-time END --locations "San Jose,Austin" -o json
```

#### Multi-pull merge pattern (windows >12 hours)

CDR Feed allows a maximum 12-hour window per request. For longer ranges (e.g., "yesterday" = 24h, "this week" = ~4 days), issue sequential 12-hour pulls and merge the results before running any recipe. Rate limit: 1 request/minute — budget ~1 min per pull.

**Example: yesterday (24h = 2 pulls)**
```bash
wxcli cdr list --start-time "2026-04-16T00:00:00.000Z" --end-time "2026-04-16T12:00:00.000Z" -o json > /tmp/cdr_p1.json
wxcli cdr list --start-time "2026-04-16T12:00:00.000Z" --end-time "2026-04-17T00:00:00.000Z" -o json > /tmp/cdr_p2.json
python3.11 -c "
import json
data = json.load(open('/tmp/cdr_p1.json')) + json.load(open('/tmp/cdr_p2.json'))
json.dump(data, open('/tmp/cdr-session.json','w'))
print(f'Merged: {len(data)} records')
"
# Now pipe /tmp/cdr-session.json to any recipe
cat /tmp/cdr-session.json | python3.11 -c "import json,sys; data=json.load(sys.stdin); ..."
```

**Window count by range:**
| Range | 12h windows | ~Time at 1 req/min |
|-------|-------------|-------------------|
| 24h (yesterday) | 2 | ~2 min |
| 48h (2 days) | 4 | ~4 min |
| 4 days (this week Mon–Thu) | 8 | ~8 min |
| 7 days | 14 | ~14 min |

Surface the pull count and estimated wait time in your plan before executing.

## CDR Query Composition Guide

Use this guide to construct CDR queries for ANY natural-language question. The recipes below cover common patterns — for questions not covered by a recipe, compose a query using the field taxonomy, composition rules, and output patterns.

**All recipes follow this execution pattern:**
1. Pull CDR data: `wxcli cdr list --start-time START --end-time END -o json`
2. Pipe to Python: `| python3.11 -c "import json, sys; data = json.load(sys.stdin); ..."`
3. Filter, aggregate, and print results

**Time window rules:**
- Replace START/END with ISO 8601 timestamps: `2026-04-10T14:00:00.000Z`
- **CDR Feed** (`wxcli cdr list`): 12-hour max window, 30-day retention, timestamps = call start time
- **CDR Stream** (`wxcli cdr list-cdr_stream`): 2-hour max window, 12-hour retention, timestamps = database write time
- All recipes use CDR Feed unless noted otherwise
- Data available for the last 30 days (Feed) or 12 hours (Stream), with a minimum 5-minute delay
- Add `--locations "Name1,Name2"` to filter by location (up to 10)
- `--limit` is not supported for CDR: `wxcli cdr list` auto-paginates and always returns all records in the window regardless of `--limit`. To get a small sample, use a short time window (30 minutes) instead of relying on `--limit`.

### CDR Call Leg Model

Every call generates one CDR record per **call leg** (one per participant perspective). Understanding leg relationships is essential for correct recipe logic:

- **Correlation ID** groups all legs of one call. A simple call has 2 legs (ORIGINATING + TERMINATING) sharing one Correlation ID.
- **Hunt Group / Call Queue**: All CDRs for the interaction share the **same Correlation ID**. The HG appears in CDRs **twice per ring attempt**: as TERMINATING (HG "receives" the inbound call — one total) and as ORIGINATING (HG "dials" each agent — one per ring attempt), each ORIGINATING paired with an agent TERMINATING. A HG call with 3 ring attempts = 1 inbound ORIGINATING + 1 HG TERMINATING + 3×(HG ORIGINATING + agent TERMINATING) = 8 CDRs. `Answered=Yes` on a HuntGroup CDR means the HG processed the call — **not that a human answered**.
- **Attended (consultative) transfer**: creates a second call with a new Correlation ID. `Transfer related call ID` on the bridging CDRs contains a **`Local call ID`** from the other call group — NOT the other call's Correlation ID. Linking rule: if `CDR1.'Transfer related call ID'` = `CDR2.'Local call ID'`, their Correlation IDs are linked.
- **Blind transfer**: creates a new call with a new Correlation ID. `Transfer related call ID` is **NOT populated** — blind transfers cannot be linked to the original call via this field.
- **Related Call ID**: deflection chaining key. Each HG ring attempt's ORIGINATING CDR has `Related call ID` = the HG's TERMINATING CDR's `Local call ID`. This chains each agent delivery back to the HG that distributed it. Also used when service activation (recording, exec-assistant) spawns a new separate call.
- **Direction**: ORIGINATING = the party who placed/initiated the leg. TERMINATING = the party who received it. The HG itself generates BOTH directions (see HG pattern above).
- **Answer indicator**: `Yes` on answered legs, `No` on unanswered. In a HG with 5 ring attempts: HG TERMINATING = `Yes` (HG processed it), only the answering agent's HG ORIGINATING + agent TERMINATING pair = `Yes`; all other agent attempts = `No`.

See `docs/reference/reporting-analytics.md` § CDR Data Model for the full reference including diagrams and all enum values.

### Field Taxonomy

CDR returns 55+ fields with space-separated JSON keys. Use this taxonomy to find the right fields:

| Category | Fields (JSON keys) | Answers |
|----------|-------------------|---------|
| **Timing** | `Start time`, `Answer time`, `Duration`, `Ring duration`, `Hold duration`, `Release time` | "how long", "when", "average duration" |
| **Outcome** | `Answer indicator` (Yes/No/Yes-PostRedirection), `Call outcome` (Success/Failure/Refusal), `Call outcome reason`, `Releasing party` (Local/Remote/Unknown), `Answered elsewhere` | "what happened", "who hung up" |
| **Party** | `Calling number`, `Called number`, `User`, `User number`, `User type`, `Caller ID number`, `Dialed digits`, `Department ID` | "who called", "which user" |
| **Routing** | `Direction` (ORIGINATING/TERMINATING), `Call type` (SIP_ENTERPRISE/SIP_NATIONAL/SIP_INTERNATIONAL/SIP_TOLLFREE/SIP_PREMIUM/SIP_MOBILE/SIP_EMERGENCY), `Original reason`, `Redirect reason`, `Related reason`, `Route group` | "inbound or outbound", "was it forwarded" |
| **Infrastructure** | `Inbound trunk`, `Outbound trunk`, `Client type` (SIP/WXC_CLIENT/WXC_DEVICE/WXC_THIRD_PARTY/TEAMS_WXC_CLIENT/WXC_SIP_GW), `Client version`, `Model`, `Device MAC`, `OS type`, `Sub client type` | "which trunk", "what device" |
| **Location** | `Location`, `Site main number`, `Site timezone`, `Site UUID` | "which office" |
| **PSTN** | `PSTN vendor name`, `PSTN legal entity`, `PSTN provider ID`, `International country`, `Authorization code` | "which carrier", "cost" |
| **Recording** | `Call Recording Platform Name`, `Call Recording Result` (successful/failed/successful but not kept), `Call Recording Trigger` (always/always-pause-resume/on-demand/on-demand-user-start) | "was it recorded" |
| **Reputation** | `Caller Reputation Score` (0.0-5.0), `Caller Reputation Service Result` (allow/block/captcha-allow/captcha-block), `Caller Reputation Score Reason` | "spam calls" |
| **Queue/AA** | `Queue type` (Customer Assist/Call Queue), `Auto Attendant Key Pressed` | "queue CDR data", "AA menu" |
| **Correlation** | `Correlation ID`, `Call ID`, `Interaction ID`, `Local call ID` (this CDR's identity), `Remote call ID` (paired CDR's local ID), `Network call ID` (secondary leg-pairing key), `Related call ID` (deflection chain: ORIGINATING.relatedCallId = source TERMINATING.localCallId), `Transfer related call ID` (contains a localCallId from the other transfer call group — NOT a Correlation ID) | "trace this call", "link legs", "follow transfer" |

### Composition Rules

| User Says | Python Translation |
|-----------|-------------------|
| "How many [calls that X]" | `filtered = [r for r in data if COND]; len(filtered)` |
| "Average / mean [metric]" | `vals = [int(r.get(F,0)) for r in data if COND]; sum(vals)/len(vals) if vals else 0` |
| "Longest / max / worst" | `max(vals) if vals else 0` |
| "By [field]" / "per [field]" | `Counter(r.get(F) for r in data)` |
| "[X] that then [Y]" | Chain: `[r for r in data if COND_A and COND_B]` |
| "Over the last N hours" | Compute start/end from `datetime.now(timezone.utc) - timedelta(hours=N)` |
| "Top N" / "worst N" | `Counter(...).most_common(N)` |
| "Percentage" / "rate" | `len(subset) / len(total) * 100` |
| "Per hour" / "hourly" | `Counter(r.get('Start time','')[:13] for r in data)` |
| "Per day" / "daily" | `Counter(r.get('Start time','')[:10] for r in data)` |
| "Trend" / "compare" | Two CDR pulls, compare counts |
| "Which [X] has worst/best" | Group-by + aggregate + sort |

### Output Patterns

**A — Count:** `len([r for r in data if COND])`

**B — Top-N:** `Counter(r.get(F) for r in data).most_common(N)`

**C — Time-series:** `Counter(r.get('Start time','')[:13] for r in data)` then `sorted()`

**D — Cross-tab:** `Counter((r.get(F1), r.get(F2)) for r in data)`

**E — Percentage:** `len(subset) / len(total) * 100`

**F — Threshold:** `[r for r in data if int(r.get(F, 0)) > T]`

**G — Chained filter:** `[r for r in data if COND_A and COND_B and COND_C]`

**H — Aggregation:** `sum(vals)/len(vals) if vals else 0` / `max(vals) if vals else 0` / `min(vals) if vals else 0`

### Recipe Catalog — 75 recipes across 11 categories

The full recipe catalog lives in `references/cdr-recipes.md` (relative to this skill). **Do not inline it here — read it on demand** when you need a specific recipe, then adapt the snippet using the Field Taxonomy and Composition Rules above. For questions no recipe covers, compose a query from the Output Patterns above.

| # | Category | Recipes | Covers |
|---|----------|---------|--------|
| 1 | Call Volume & Traffic | 1–8 | total count, by location/hour/day/type, inbound vs outbound, peak hour, trend |
| 2 | Call Outcomes & Quality | 9–16 | missed/failed/abandoned, answer rate, outcome reason, short calls, long-ring no-answer |
| 3 | Hold & Wait Time | 17–24 | avg hold, excessive hold (>30s/>60s), hold-then-abandon, ring duration, hold by user |
| 4 | User & Agent Performance | 25–32 | top talkers, calls/duration per user, missed per user, answer rate, international, after-hours |
| 5 | Trunk & Routing | 33–39 | calls per trunk, utilization by hour, route groups, redirect/original reason, forwarding loops |
| 6 | PSTN & Billing | 40–46 | by vendor, duration by vendor, international by country, call-type mix, auth codes, vendor comparison |
| 7 | Device & Client | 47–52 | client type, device model inventory, OS type, softphone vs desk, Webex Go mobile, client version |
| 8 | Spam & Reputation | 53–57 | reputation score distribution, blocked vs allowed, top blocked numbers, spam by location, captcha |
| 9 | Recording Compliance | 58–63 | success rate, by platform, by trigger, failed recordings, unrecorded analysis, compliance by location |
| 10 | Call Tracing & Diagnostics | 64–69 | trace by correlation ID, transfer chains, park/retrieve, forwarding path, quality proxy, repeat callers |
| 11 | Cross-Category Compound | 70–75 | multi-filter queries combining dimensions from other categories: spam→queue→abandon, international calls on a trunk during business hours, forwarded-twice→voicemail, missed calls from repeat callers, long-hold calls that were transferred, after-hours emergency (look here when a question crosses trunk + call-type + time, etc., not just one category) |

**To find a recipe:** `grep -nE '^### Category|^\*\*Recipe' .claude/skills/reporting/references/cdr-recipes.md` for the full list, or grep by keyword (e.g. `grep -ni "emergency" .claude/skills/reporting/references/cdr-recipes.md`).

### 6b. Reports API (async CSV reports)

Use the Reports API for queue stats, AA stats, call quality, and engagement reports. These are generated asynchronously as CSV files.

#### Discover templates

```bash
wxcli report-templates list -o json
```

Look for templates by name: "Call Queue Stats", "Call Queue Agent Stats", "Auto-attendant Stats Summary", "Calling Media Quality", "Calling Quality", "Calling Engagement".

#### Create a report

```bash
wxcli reports create --template-id TEMPLATE_ID --start-date "2026-04-01" --end-date "2026-04-10"
```

Template IDs are org-specific — always discover them at runtime. Date format is `YYYY-MM-DD`.

#### Poll status

```bash
wxcli reports show REPORT_ID -o json
```

Poll until `status` is `"done"`. The response will include `downloadURL` for the CSV ZIP file.

#### Download the CSV

```bash
curl -H "Authorization: Bearer $WEBEX_ACCESS_TOKEN" -o report.zip "DOWNLOAD_URL"
unzip report.zip
```

#### Delete the report (free quota — max 50 reports)

```bash
wxcli reports delete REPORT_ID --force
```

#### Standard report templates

| Template Name | Description |
|---------------|-------------|
| Detailed Call History | Comprehensive call log (all CDR fields) |
| Calling Media Quality | Per-call-leg quality (latency, jitter, packet loss) |
| Calling Engagement | Usage and adoption tracking |
| Calling Quality | Client-side quality from Webex Calling app |
| Call Queue Stats | Queue-level KPIs (volume, wait, abandonment) |
| Call Queue Agent Stats | Per-agent queue performance |
| Auto-attendant Stats Summary | AA call volume and handling |
| Auto-attendant Business & After-Hours Key Details | AA key-press patterns |

### 6c. Converged recordings

#### List recordings

```bash
wxcli converged-recordings list --from "2026-04-01T00:00:00Z" --to "2026-04-10T00:00:00Z" -o json
wxcli converged-recordings list-converged-recordings --owner-email user@company.com -o json
```

#### Download artifacts

```bash
wxcli converged-recordings download RECORDING_ID
wxcli converged-recordings download RECORDING_ID --include-audio
```

#### Bulk export for BI

```bash
wxcli converged-recordings export --from "2026-04-01T00:00:00Z" --to "2026-04-10T00:00:00Z"
wxcli converged-recordings export --from START --to END --owner-email user@company.com --include-audio
```

#### Recording audit

```bash
wxcli recording-report list -o json
wxcli recording-report list-access-detail --recording-id RECORDING_ID -o json
```

## Step 7: Session Pattern — Pull Once, Query Many

CDR pulls are slow due to the CDR API rate limit (1 request/minute) and the 12-hour max window per request. A 7-day pull requires 14 sequential requests = ~14 minutes. This section prevents redundant pulls and sets correct user expectations.

### Rate limit reality

The CDR Feed API (`analytics-calling.webexapis.com`) enforces **1 request per minute** per user token. wxcli's `wxcli cdr list` respects this limit with built-in sleep between requests, so each pull takes ~60 seconds regardless of data volume. Calculate expected pull time before starting:

| Window | Pulls | Expected Time |
|--------|-------|---------------|
| ≤12h | 1 | ~1 min |
| 12–24h | 2 | ~2 min |
| 1–3 days | 2–6 | ~2–6 min |
| 7 days | 14 | ~14 min |
| 30 days | 60 | ~60 min — use Reports API instead |

**For windows >24 hours:** Tell the user the expected pull time before starting. Example: "A 7-day CDR pull requires 14 API requests at ~1/minute = approximately 14 minutes. Proceed?"

**For windows >7 days:** Recommend the Reports API (Detailed Call History template) instead — it's async but handles up to 30 days in a single request with no per-minute rate limit. Requires `analytics:read_all` scope and Pro Pack. If the org lacks Pro Pack, CDR Feed is the only option — warn about the wait time.

### Two-phase split

1. **Pull phase** — requires `wxc-calling-builder` agent (wxcli hook blocks direct CLI calls). The caller (Claude's main context) spawns the builder agent with instructions to pull CDR data and save to `/tmp/cdr-session.json`. The builder agent handles multi-pull merge for windows >12h automatically. Once the file is written, the builder agent's job is done — do not keep it running.
2. **Recipe phase** — runs directly via Bash, no agent spawn needed. `cat /tmp/cdr-session.json | python3.11 -c "..."` executes in ~2 seconds. The skill guides recipe selection; Claude executes inline.

### Pull phase instructions for builder agent

When spawning the builder agent for CDR pulls, include these instructions in the prompt:

1. **Progress output:** After each window, print: `echo "✓ Window N/TOTAL: START → END (X records)" >&2`
2. **Error handling:** Use this pattern for each pull to prevent 0-byte files on API errors:
   ```bash
   wxcli cdr list --start-time START --end-time END -o json > /tmp/cdr_wNN.json 2>/tmp/cdr_err.log
   if [ ! -s /tmp/cdr_wNN.json ]; then echo "[]" > /tmp/cdr_wNN.json; fi
   ```
3. **Merge:** After all pulls complete, merge with Python and write `/tmp/cdr-session.json`.
4. **Run foreground, not background:** CDR pulls take minutes. Run the builder agent in the foreground so its progress output streams to the user. Do NOT use `run_in_background`.

### Cache file format

The pull phase writes `/tmp/cdr-session.json` as a JSON object:
```json
{"_meta": {"start": "2026-04-10T00:00:00.000Z", "end": "2026-04-13T00:00:00.000Z", "pulled": "2026-04-13T12:34:56Z", "records": 1847}, "data": [ ...CDR records... ]}
```

Recipes read from the `data` array: `data = json.load(sys.stdin)['data']`

### Cache decision logic

On every CDR question:

1. **Check** — does `/tmp/cdr-session.json` exist? Read `_meta.start`, `_meta.end`.
2. **Cache hit** — requested window is within `_meta` boundaries → run recipe directly via Bash. No agent spawn.
3. **Cache miss** — requested window extends beyond `_meta` boundaries, or file doesn't exist, or user says "refresh" → spawn `wxc-calling-builder` to re-pull (foreground). Builder overwrites the cache file with the new window.
4. **Explicit refresh** — if the user says "refresh", "re-pull", or "new data", always re-pull regardless of cache state.

### Presentation Rules

**Rule 1 — Format what the recipe prints.**
Present all columns the recipe outputs. The `# Output:` comment above each recipe's bash block tells you exactly what columns to expect. Never collapse to 2 columns if the recipe produces more.

**Rule 2 — Collapse to prose when ≤ 2 rows.**
A table with 1–2 rows is worse than a sentence.
- ✅ "All 10 calls came from HQ (10/10)."
- ❌ | Location | Total | ... | / | HQ | 10 | ...

**Rule 3 — Adapt to the user's question framing.**

| User says | Format |
|---|---|
| "how many", "what's the count" | Lead with the number inline; table is secondary or omitted |
| "show me", "list", "breakdown", "by X" | Table is primary |
| "analyze", "what do you see", "explain" | Narrative with numbers embedded inline |
| "compare" | Two-row side-by-side if two windows; sorted table otherwise |

**Rule 4 — One summary line above every table.**
e.g., "5 missed calls out of 247 total (2.0%)" — always present, even for large tables.

**Rule 5 — Timestamps trimmed to YYYY-MM-DD HH:MM.** Drop seconds and timezone.

**Rule 6 — No unsolicited commentary.**
No analysis, recommendations, or data quality notes below the table unless the user asks "why", "what do you see", or "analyze this".

### Recipe adaptation for cached data

When running recipes against the cache file, adapt the standard recipe pattern:
```bash
# Standard (from pull): wxcli cdr list ... -o json | python3.11 -c "..."
# Cached: read from file, access the 'data' array
cat /tmp/cdr-session.json | python3.11 -c "import json,sys; raw=json.load(sys.stdin); data=raw['data']; ..."
```

All 75 recipes work unchanged except: replace `data = json.load(sys.stdin)` with `data = json.load(sys.stdin)['data']`.

## Step 8: Verify

After retrieving data, verify the results make sense and present key findings.

```bash
# Quick CDR sanity check
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "import json,sys; data=json.load(sys.stdin); print(f'Records: {len(data)}')"

# Quick report templates check
wxcli report-templates list -o json | python3.11 -c "import json,sys; data=json.load(sys.stdin); print(f'Templates: {len(data)}')"
```

## Step 9: Report results

Present findings using the Step 7 presentation format: one-line summary + markdown table. No unsolicited recommendations or data quality commentary unless the user asks.

For non-CDR results (Reports API, recordings), use:
- **Data retrieved:** Report type, date range, record count
- **Key findings:** Top metrics, trends, anomalies discovered
- **Cleanup reminders:** Delete reports to free quota if applicable

---

## Critical Rules

1. **CDR is NOT real-time.** Minimum 5-minute delay. Data may take up to 24 hours to fully populate.
2. **12-hour maximum query window.** For longer ranges, issue multiple sequential requests.
3. **30-day data retention.** Older data must come from Reports API (CSV).
4. **Date format:** CDR uses ISO 8601 with milliseconds: `2026-04-10T14:00:00.000Z`. Reports API uses `YYYY-MM-DD`.
5. **Regional endpoints.** CDR HTTP 451 means wrong region — response body has the correct URL.
6. **Rate limits:** CDR Feed enforces 1 request/minute per user token (+ 10 pagination/minute). A 7-day pull = 14 requests = ~14 minutes. Always tell the user the expected wait time before starting. For windows >7 days, recommend the Reports API instead.
7. **Report quota: max 50.** Always delete reports after downloading.
8. **Pro Pack required for Reports API.** CDR Feed does NOT require Pro Pack.
9. **Template IDs are org-specific.** Never hardcode — discover at runtime.
10. **Reports are async CSV/ZIP.** Poll `wxcli reports show REPORT_ID` until `status` is `"done"`.
11. **CDR field names use spaces.** `"Start time"`, `"Call outcome reason"` — use exact names in Python.
12. **Location filter uses names, not IDs.** Up to 10, comma-separated.
13. **Recording management is destructive.** `create-purge` is permanent. Always confirm.
14. **Converged recordings scope split.** User-level: `wxcli converged-recordings list`. Admin: `wxcli converged-recordings list-converged-recordings`.

---

## Scope Quick Reference

| Scope | Grants Access To |
|-------|-----------------|
| `spark-admin:calling_cdr_read` | CDR Feed and Stream |
| `analytics:read_all` | Report Templates, Reports, Partner Reports |
| `spark-admin:locations_read` | Location name filtering on CDR |
| `spark-admin:telephony_config_read` | Converged recordings read |
| `spark-admin:telephony_config_write` | Recording management (reassign, delete, purge) |
| `spark-compliance:recordings_read` | Compliance officer recording access |

---

## Context Compaction Recovery

If context compacts mid-execution:
1. Read `docs/reference/reporting-analytics.md` to recover field references
2. Check what data has already been retrieved by reviewing recent command output
3. Review Steps 1-8 and resume from the first incomplete step
