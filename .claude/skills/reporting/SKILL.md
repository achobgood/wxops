---
name: reporting
description: |
  Query and analyze Webex Calling reporting and analytics: Detailed Call History (CDR),
  Call Queue statistics, Auto Attendant statistics, call quality, report templates,
  and converged recordings. 75 CDR recipes + query composition guide for answering
  any natural-language question about a calling environment.
  For Contact Center analytics, use the reporting-cc skill.
  For meetings/workspace analytics, use the reporting-meetings skill.
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

```bash
wxcli cdr list-cdr_stream --start-time "2026-04-10T14:00:00.000Z" --end-time "2026-04-10T16:00:00.000Z" -o json
```

#### Filter by location

```bash
wxcli cdr list --start-time START --end-time END --locations "San Jose,Austin" -o json
```

## CDR Query Composition Guide

Use this guide to construct CDR queries for ANY natural-language question. The recipes below cover common patterns — for questions not covered by a recipe, compose a query using the field taxonomy, composition rules, and output patterns.

**All recipes follow this execution pattern:**
1. Pull CDR data: `wxcli cdr list --start-time START --end-time END -o json`
2. Pipe to Python: `| python3.11 -c "import json, sys; data = json.load(sys.stdin); ..."`
3. Filter, aggregate, and print results

**Time window rules:**
- Replace START/END with ISO 8601 timestamps: `2026-04-10T14:00:00.000Z`
- Maximum 12-hour window per request — for longer ranges, issue multiple requests
- Data available for the last 30 days only, with a minimum 5-minute delay
- Add `--locations "Name1,Name2"` to filter by location (up to 10)
- `--limit` is not supported for CDR: `wxcli cdr list` auto-paginates and always returns all records in the window regardless of `--limit`. To get a small sample, use a short time window (30 minutes) instead of relying on `--limit`.

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
| **Correlation** | `Correlation ID`, `Call ID`, `Interaction ID`, `Network call ID`, `Related call ID`, `Transfer related call ID` | "trace this call" |

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

### Category 1: Call Volume & Traffic

**Recipe 1 — Total call count**
Question: "How many calls did we get?"
# Output: Metric | Value
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
orig = len([r for r in data if r.get('Direction') == 'ORIGINATING'])
term = len([r for r in data if r.get('Direction') == 'TERMINATING'])
unique = len(set(r.get('Correlation ID') for r in data if r.get('Correlation ID')))
# Note: CDR generates one record per call leg (ORIGINATING + TERMINATING).
# Total count below includes both legs. For unique call count, use Correlation ID dedup
# or filter by Direction == 'ORIGINATING' only.
print(f'Total CDR legs: {len(data)} (ORIGINATING: {orig}, TERMINATING: {term})')
print(f'Unique calls (by Correlation ID): {unique}')
"
```

**Recipe 2 — Calls by location**
Question: "Which office is busiest?"
# Output: Location | Total | Answered | Missed | Answer% | Avg Duration(s)
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import defaultdict
data = json.load(sys.stdin)
stats = defaultdict(lambda: {'total':0,'answered':0,'dur':0})
for r in data:
    loc = r.get('Location','Unknown')
    stats[loc]['total'] += 1
    if r.get('Answer indicator') == 'Yes':
        stats[loc]['answered'] += 1
        stats[loc]['dur'] += int(r.get('Duration',0))
print(f\"{'Location':<25} {'Total':>6} {'Answered':>9} {'Missed':>7} {'Ans%':>6} {'AvgDur':>7}\")
for loc, s in sorted(stats.items(), key=lambda x: x[1]['total'], reverse=True):
    missed = s['total'] - s['answered']
    rate = s['answered']/s['total']*100 if s['total'] else 0
    avg = s['dur']/s['answered'] if s['answered'] else 0
    print(f\"{loc:<25} {s['total']:>6} {s['answered']:>9} {missed:>7} {rate:>5.1f}% {avg:>6.0f}s\")
"
```

**Recipe 3 — Calls by hour**
Question: "When is our peak call time?"
# Output: Hour | Total | Answered | Missed Rate%
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import defaultdict
data = json.load(sys.stdin)
stats = defaultdict(lambda: {'total':0,'answered':0})
for r in data:
    h = r.get('Start time','')[:13]
    if h:
        stats[h]['total'] += 1
        if r.get('Answer indicator') == 'Yes':
            stats[h]['answered'] += 1
print(f\"{'Hour':<14} {'Total':>6} {'Answered':>9} {'Missed%':>8}\")
for h, s in sorted(stats.items()):
    missed_rate = (s['total']-s['answered'])/s['total']*100 if s['total'] else 0
    print(f\"{h:<14} {s['total']:>6} {s['answered']:>9} {missed_rate:>7.1f}%\")
"
```

**Recipe 4 — Calls by day of week**
Question: "Which day of the week is busiest?"
# Output: Day | Total | Answered | Missed Rate%
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import defaultdict
from datetime import datetime
data = json.load(sys.stdin)
stats = defaultdict(lambda: {'total':0,'answered':0})
for r in data:
    ts = r.get('Start time','')
    if ts:
        try:
            dt = datetime.fromisoformat(ts.replace('Z','+00:00'))
            day = dt.strftime('%A')
            stats[day]['total'] += 1
            if r.get('Answer indicator') == 'Yes':
                stats[day]['answered'] += 1
        except: pass
print(f\"{'Day':<12} {'Total':>6} {'Answered':>9} {'Missed%':>8}\")
for day in ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']:
    if stats[day]['total'] > 0:
        s = stats[day]
        missed_rate = (s['total']-s['answered'])/s['total']*100 if s['total'] else 0
        print(f\"{day:<12} {s['total']:>6} {s['answered']:>9} {missed_rate:>7.1f}%\")
"
```

**Recipe 5 — Calls by type**
Question: "How many internal vs external vs international calls?"
# Output: Call Type | Count | %
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
types = Counter(r.get('Call type', 'Unknown') for r in data)
for t, c in types.most_common():
    print(f'{t}: {c} calls ({c/len(data)*100:.1f}%)')
"
```

**Recipe 6 — Inbound vs outbound ratio**
Question: "What's our inbound/outbound split?"
# Output: Metric | Value
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
total = len(data)
inb = len([r for r in data if r.get('Direction') == 'TERMINATING'])
outb = len([r for r in data if r.get('Direction') == 'ORIGINATING'])
print(f'Total: {total}')
print(f'Inbound:  {inb} ({inb/total*100:.1f}%)' if total else 'No data')
print(f'Outbound: {outb} ({outb/total*100:.1f}%)' if total else '')
"
```

**Recipe 7 — Peak hour identification**
Question: "What's the single busiest hour?"
# Output: Metric | Value
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
hours = Counter(r.get('Start time', '')[:13] for r in data)
if hours:
    peak, count = hours.most_common(1)[0]
    print(f'Peak hour: {peak} with {count} calls')
    print(f'Average: {len(data)/len(hours):.1f} calls/hour')
"
```

**Recipe 8 — Volume trend comparison**
Question: "Are calls up or down vs last week?"
Note: Requires two CDR pulls — one for this week, one for last week. Replace THIS_START/THIS_END and LAST_START/LAST_END accordingly.
# Output: Period | Calls | Change | % Change
```bash
wxcli cdr list --start-time THIS_START --end-time THIS_END -o json > /tmp/cdr_this.json
wxcli cdr list --start-time LAST_START --end-time LAST_END -o json > /tmp/cdr_last.json
python3.11 -c "
import json
this_week = json.load(open('/tmp/cdr_this.json'))
last_week = json.load(open('/tmp/cdr_last.json'))
diff = len(this_week) - len(last_week)
pct = (diff / len(last_week) * 100) if last_week else 0
direction = 'up' if diff > 0 else 'down'
print(f'This period: {len(this_week)} calls')
print(f'Last period: {len(last_week)} calls')
print(f'Change: {direction} {abs(diff)} ({abs(pct):.1f}%)')
"
```

### Category 2: Call Outcomes & Quality

**Recipe 9 — Missed calls**
Question: "How many calls did we miss?"
# Output: Time | User | Calling # | Called # | Ring Duration | Reason
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
missed = [r for r in data if r.get('Answer indicator') == 'No']
print(f'Missed calls: {len(missed)} of {len(data)} ({len(missed)/len(data)*100:.1f}%)' if data else 'No data')
print(f'No matching records found in this time window.') if not missed else None
for c in missed[:10]:
    print(f\"  {c.get('Start time','')[:16]} | {c.get('User','?')} | {c.get('Calling number','?')} -> {c.get('Called number','?')} | ring {c.get('Ring duration','?')}s | {c.get('Call outcome reason','?')}\")
"
```

**Recipe 10 — Failed calls**
Question: "How many calls failed?"
# Output: Time | User | Calling # | Called # | Outcome | Reason
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
failed = [r for r in data if r.get('Call outcome') in ('Failure', 'Refusal')]
print(f'Failed/refused: {len(failed)} of {len(data)}')
if not failed:
    print('No matching records found in this time window.')
else:
    for c in failed[:10]:
        print(f\"  {c.get('Start time','')[:16]} | {c.get('User','?')} | {c.get('Calling number','?')} -> {c.get('Called number','?')} | {c.get('Call outcome','?')}: {c.get('Call outcome reason','?')}\")
"
```

**Recipe 11 — Abandoned calls**
Question: "How many callers hung up before we answered?"
# Output: Time | User | Calling # | Called # | Ring Duration
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
abandoned = [r for r in data if r.get('Answer indicator') == 'No' and r.get('Releasing party') == 'Local']
print(f'Abandoned (caller hung up before answer): {len(abandoned)}')
if not abandoned:
    print('No matching records found in this time window.')
else:
    for c in abandoned[:10]:
        print(f\"  {c.get('Start time','')[:16]} | {c.get('User','?')} | {c.get('Calling number','?')} -> {c.get('Called number','?')} | rang {c.get('Ring duration','?')}s\")
"
```

**Recipe 12 — Answer rate**
Question: "What percentage of calls do we answer?"
# Output: Metric | Value
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
answered = len([r for r in data if r.get('Answer indicator') == 'Yes'])
total = len(data)
print(f'Answer rate: {answered/total*100:.1f}% ({answered} of {total})' if total else 'No data')
"
```

**Recipe 13 — Calls by outcome reason**
Question: "Why are calls failing?"
# Output: Reason | Count | %
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
reasons = Counter(r.get('Call outcome reason', 'Unknown') for r in data if r.get('Call outcome') != 'Success')
total_non_success = sum(reasons.values())
for reason, count in reasons.most_common():
    pct = count/total_non_success*100 if total_non_success else 0
    print(f'{reason}: {count} ({pct:.1f}%)')
"
```

**Recipe 14 — Short calls (possible misroutes)**
Question: "How many calls lasted under 10 seconds?"
# Output: Time | User | Called # | Duration | Outcome
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
short = [r for r in data if r.get('Answer indicator') == 'Yes' and int(r.get('Duration', 0)) < 10]
print(f'Short calls (<10s, answered): {len(short)} of {len(data)}')
if not short:
    print('No matching records found in this time window.')
else:
    for c in short[:10]:
        print(f\"  {c.get('Start time','')[:16]} | {c.get('User','?')} | {c.get('Called number','?')} | {c.get('Duration','?')}s | {c.get('Call outcome','?')}\")
"
```

**Recipe 15 — Long-ring no-answer**
Question: "Calls that rang for over 30 seconds and weren't answered?"
# Output: Time | User | Calling # | Ring Duration
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
long_ring = [r for r in data if r.get('Answer indicator') == 'No' and int(r.get('Ring duration', 0)) > 30]
print(f'Long-ring no-answer (>30s ring): {len(long_ring)}')
if not long_ring:
    print('No matching records found in this time window.')
else:
    for c in long_ring[:10]:
        print(f\"  {c.get('Start time')} | {c.get('User')} | rang {c.get('Ring duration')}s | from {c.get('Calling number')}\")
"
```

**Recipe 16 — Call outcome by location**
Question: "Which office has the worst answer rate?"
# Output: Location | Total | Answered | Answer%
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import defaultdict
data = json.load(sys.stdin)
stats = defaultdict(lambda: {'total': 0, 'answered': 0})
for r in data:
    loc = r.get('Location', 'Unknown')
    stats[loc]['total'] += 1
    if r.get('Answer indicator') == 'Yes':
        stats[loc]['answered'] += 1
print(f\"{'Location':<25} {'Total':>6} {'Answered':>9} {'Ans%':>6}\")
for loc, s in sorted(stats.items(), key=lambda x: x[1]['answered']/max(x[1]['total'],1)):
    rate = s['answered']/s['total']*100 if s['total'] else 0
    print(f\"{loc:<25} {s['total']:>6} {s['answered']:>9} {rate:>5.1f}%\")
"
```

### Category 3: Hold & Wait Time

**Recipe 17 — Average hold time**
Question: "What's our average hold time?"
# Output: Metric | Value
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
holds = [int(r.get('Hold duration', 0)) for r in data if int(r.get('Hold duration', 0)) > 0]
if holds:
    print(f'Calls with hold: {len(holds)}')
    print(f'Average hold: {sum(holds)/len(holds):.1f}s')
    print(f'Max hold: {max(holds)}s')
else:
    print('No calls with hold time found')
"
```

**Recipe 18 — Calls with excessive hold (>30s)**
Question: "How many calls had over 30 seconds of hold?"
# Output: Time | User | Calling # | Hold Duration
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
over30 = [r for r in data if int(r.get('Hold duration', 0)) > 30]
print(f'Calls with >30s hold: {len(over30)}')
if not over30:
    print('No matching records found in this time window.')
else:
    for c in over30[:10]:
        print(f\"  {c.get('Start time')} | {c.get('User')} | hold {c.get('Hold duration')}s | {c.get('Calling number')}\")
"
```

**Recipe 19 — Calls with excessive hold (>60s)**
Question: "How many calls had over a minute of hold?"
# Output: Time | User | Calling # | Hold Duration
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
over60 = [r for r in data if int(r.get('Hold duration', 0)) > 60]
print(f'Calls with >60s hold: {len(over60)}')
if not over60:
    print('No matching records found in this time window.')
else:
    for c in over60[:10]:
        print(f\"  {c.get('Start time')} | {c.get('User')} | hold {c.get('Hold duration')}s | {c.get('Calling number')}\")
"
```

**Recipe 20 — Hold-then-abandoned (>30s)**
Question: "Calls we answered, put on hold >30s, and the caller hung up?"
# Output: Time | User | Hold Duration | Total Duration
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
hold_abandoned = [r for r in data
    if r.get('Answer indicator') == 'Yes'
    and int(r.get('Hold duration', 0)) > 30
    and r.get('Releasing party') == 'Remote']
print(f'Answered -> held >30s -> caller hung up: {len(hold_abandoned)}')
if not hold_abandoned:
    print('No matching records found in this time window.')
else:
    for c in hold_abandoned[:10]:
        print(f\"  {c.get('Start time')} | {c.get('User')} | hold {c.get('Hold duration')}s | {c.get('Duration')}s total\")
"
```

**Recipe 21 — Hold-then-abandoned (>60s)**
Question: "Calls we answered, put on hold >60s, and the caller hung up?"
# Output: Time | User | Hold Duration | Total Duration
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
hold_abandoned = [r for r in data
    if r.get('Answer indicator') == 'Yes'
    and int(r.get('Hold duration', 0)) > 60
    and r.get('Releasing party') == 'Remote']
print(f'Answered -> held >60s -> caller hung up: {len(hold_abandoned)}')
if not hold_abandoned:
    print('No matching records found in this time window.')
else:
    for c in hold_abandoned[:10]:
        print(f\"  {c.get('Start time')} | {c.get('User')} | hold {c.get('Hold duration')}s | {c.get('Duration')}s total\")
"
```

**Recipe 22 — Average ring duration**
Question: "How long are callers waiting before we pick up?"
# Output: Metric | Value
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
rings = [int(r.get('Ring duration', 0)) for r in data if r.get('Answer indicator') == 'Yes' and int(r.get('Ring duration', 0)) > 0]
if rings:
    print(f'Answered calls with ring data: {len(rings)}')
    print(f'Average ring: {sum(rings)/len(rings):.1f}s')
    print(f'Max ring: {max(rings)}s')
"
```

**Recipe 23 — Ring duration by location**
Question: "Which office is slowest to answer?"
# Output: Location | Avg Ring(s) | Calls
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import defaultdict
data = json.load(sys.stdin)
stats = defaultdict(list)
for r in data:
    if r.get('Answer indicator') == 'Yes' and int(r.get('Ring duration', 0)) > 0:
        stats[r.get('Location', 'Unknown')].append(int(r.get('Ring duration', 0)))
for loc, rings in sorted(stats.items(), key=lambda x: sum(x[1])/len(x[1]), reverse=True):
    avg = sum(rings)/len(rings)
    print(f'{loc}: avg {avg:.1f}s ring ({len(rings)} calls)')
"
```

**Recipe 24 — Hold time by user**
Question: "Which agents put callers on hold the longest?"
# Output: User | Avg Hold(s) | Calls with Hold | Max Hold(s)
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import defaultdict
data = json.load(sys.stdin)
stats = defaultdict(list)
for r in data:
    hold = int(r.get('Hold duration', 0))
    if hold > 0:
        stats[r.get('User', 'Unknown')].append(hold)
for user, holds in sorted(stats.items(), key=lambda x: sum(x[1])/len(x[1]), reverse=True)[:15]:
    avg = sum(holds)/len(holds)
    print(f'{user}: avg {avg:.1f}s hold, {len(holds)} calls with hold, max {max(holds)}s')
"
```

### Category 4: User & Agent Performance

**Recipe 25 — Top talkers (by call count)**
Question: "Who makes/receives the most calls?"
# Output: User | Total | Answered | Missed | Answer% | Avg Duration(s)
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import defaultdict
data = json.load(sys.stdin)
stats = defaultdict(lambda: {'total':0,'answered':0,'dur':0})
for r in data:
    user = r.get('User','Unknown')
    stats[user]['total'] += 1
    if r.get('Answer indicator') == 'Yes':
        stats[user]['answered'] += 1
        stats[user]['dur'] += int(r.get('Duration',0))
print(f\"{'User':<30} {'Total':>6} {'Answered':>9} {'Missed':>7} {'Ans%':>6} {'AvgDur':>7}\")
for user, s in sorted(stats.items(), key=lambda x: x[1]['total'], reverse=True)[:15]:
    missed = s['total'] - s['answered']
    rate = s['answered']/s['total']*100 if s['total'] else 0
    avg = s['dur']/s['answered'] if s['answered'] else 0
    print(f\"{user:<30} {s['total']:>6} {s['answered']:>9} {missed:>7} {rate:>5.1f}% {avg:>6.0f}s\")
"
```

**Recipe 26 — Top talkers (by total duration)**
Question: "Who spends the most time on the phone?"
# Output: User | Total Min | Avg Duration(s) | Calls | Answer%
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import defaultdict
data = json.load(sys.stdin)
stats = defaultdict(lambda: {'total':0,'answered':0,'dur':0})
for r in data:
    user = r.get('User','Unknown')
    stats[user]['total'] += 1
    if r.get('Answer indicator') == 'Yes':
        stats[user]['answered'] += 1
    stats[user]['dur'] += int(r.get('Duration',0))
print(f\"{'User':<30} {'Total Min':>10} {'Avg Dur':>8} {'Calls':>6} {'Ans%':>6}\")
for user, s in sorted(stats.items(), key=lambda x: x[1]['dur'], reverse=True)[:15]:
    rate = s['answered']/s['total']*100 if s['total'] else 0
    avg = s['dur']/s['total'] if s['total'] else 0
    print(f\"{user:<30} {s['dur']/60:>10.1f} {avg:>7.0f}s {s['total']:>6} {rate:>5.1f}%\")
"
```

**Recipe 27 — Calls per user**
Question: "How many calls does each user handle?"
# Output: User | Total | Answered | Missed | Answer%
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import defaultdict
data = json.load(sys.stdin)
stats = defaultdict(lambda: {'total':0,'answered':0})
for r in data:
    user = r.get('User','Unknown')
    stats[user]['total'] += 1
    if r.get('Answer indicator') == 'Yes':
        stats[user]['answered'] += 1
print(f\"{'User':<30} {'Total':>6} {'Answered':>9} {'Missed':>7} {'Ans%':>6}\")
for user, s in sorted(stats.items(), key=lambda x: x[1]['total'], reverse=True):
    missed = s['total'] - s['answered']
    rate = s['answered']/s['total']*100 if s['total'] else 0
    print(f\"{user:<30} {s['total']:>6} {s['answered']:>9} {missed:>7} {rate:>5.1f}%\")
"
```

**Recipe 28 — Average duration per user**
Question: "Who has the longest average call?"
# Output: User | Avg Duration(s) | Calls | Answer%
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import defaultdict
data = json.load(sys.stdin)
stats = defaultdict(lambda: {'durs':[], 'total':0, 'answered':0})
for r in data:
    user = r.get('User','Unknown')
    stats[user]['total'] += 1
    if r.get('Answer indicator') == 'Yes':
        stats[user]['answered'] += 1
        stats[user]['durs'].append(int(r.get('Duration',0)))
print(f\"{'User':<30} {'Avg Dur':>8} {'Calls':>6} {'Ans%':>6}\")
for user, s in sorted(stats.items(), key=lambda x: sum(x[1]['durs'])/len(x[1]['durs']) if x[1]['durs'] else 0, reverse=True)[:15]:
    avg = sum(s['durs'])/len(s['durs']) if s['durs'] else 0
    rate = s['answered']/s['total']*100 if s['total'] else 0
    print(f\"{user:<30} {avg:>7.0f}s {s['total']:>6} {rate:>5.1f}%\")
"
```

**Recipe 29 — Users with most missed calls**
Question: "Who misses the most calls?"
# Output: User | Missed | Total | Miss%
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import defaultdict
data = json.load(sys.stdin)
stats = defaultdict(lambda: {'total':0,'missed':0})
for r in data:
    user = r.get('User','Unknown')
    stats[user]['total'] += 1
    if r.get('Answer indicator') == 'No':
        stats[user]['missed'] += 1
print(f\"{'User':<30} {'Missed':>7} {'Total':>6} {'Miss%':>6}\")
for user, s in sorted(stats.items(), key=lambda x: x[1]['missed'], reverse=True)[:15]:
    rate = s['missed']/s['total']*100 if s['total'] else 0
    print(f\"{user:<30} {s['missed']:>7} {s['total']:>6} {rate:>5.1f}%\")
"
```

**Recipe 30 — User answer rate**
Question: "What's each user's answer rate?"
# Output: User | Total | Answered | Answer%
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import defaultdict
data = json.load(sys.stdin)
stats = defaultdict(lambda: {'total': 0, 'answered': 0})
for r in data:
    user = r.get('User', 'Unknown')
    stats[user]['total'] += 1
    if r.get('Answer indicator') == 'Yes':
        stats[user]['answered'] += 1
for user, s in sorted(stats.items(), key=lambda x: x[1]['answered']/max(x[1]['total'],1)):
    rate = s['answered']/s['total']*100 if s['total'] else 0
    print(f\"{user}: {rate:.1f}% ({s['answered']}/{s['total']})\")
"
```

**Recipe 31 — International calls per user**
Question: "Who makes the most international calls?"
# Output: User | Intl Calls | Total Calls | Intl%
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import defaultdict
data = json.load(sys.stdin)
stats = defaultdict(lambda: {'total':0,'intl':0})
for r in data:
    user = r.get('User','Unknown')
    stats[user]['total'] += 1
    if r.get('Call type') == 'SIP_INTERNATIONAL':
        stats[user]['intl'] += 1
intl_users = {u: s for u, s in stats.items() if s['intl'] > 0}
print(f\"{'User':<30} {'Intl':>5} {'Total':>6} {'Intl%':>6}\")
for user, s in sorted(intl_users.items(), key=lambda x: x[1]['intl'], reverse=True)[:15]:
    rate = s['intl']/s['total']*100 if s['total'] else 0
    print(f\"{user:<30} {s['intl']:>5} {s['total']:>6} {rate:>5.1f}%\")
"
```

**Recipe 32 — After-hours activity**
Question: "Who's making calls outside business hours (before 8am or after 6pm)?"
# Output: User | After-Hours | Total | AH%
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import defaultdict
data = json.load(sys.stdin)
stats = defaultdict(lambda: {'total':0,'ah':0})
for r in data:
    user = r.get('User','Unknown')
    stats[user]['total'] += 1
    ts = r.get('Start time','')
    if ts:
        try:
            hour = int(ts[11:13])
            if hour < 8 or hour >= 18:
                stats[user]['ah'] += 1
        except: pass
ah_users = {u: s for u, s in stats.items() if s['ah'] > 0}
print(f\"{'User':<30} {'After-Hours':>12} {'Total':>6} {'AH%':>5}\")
for user, s in sorted(ah_users.items(), key=lambda x: x[1]['ah'], reverse=True)[:15]:
    rate = s['ah']/s['total']*100 if s['total'] else 0
    print(f\"{user:<30} {s['ah']:>12} {s['total']:>6} {rate:>4.1f}%\")
"
```

### Category 5: Trunk & Routing

**Recipe 33 — Calls per trunk**
Question: "How much traffic on each trunk?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
inbound = Counter(r.get('Inbound trunk') for r in data if r.get('Inbound trunk'))
outbound = Counter(r.get('Outbound trunk') for r in data if r.get('Outbound trunk'))
print('Inbound trunks:')
for trunk, count in inbound.most_common():
    print(f'  {trunk}: {count} calls')
print('Outbound trunks:')
for trunk, count in outbound.most_common():
    print(f'  {trunk}: {count} calls')
"
```

**Recipe 34 — Trunk utilization by hour**
Question: "When are our trunks busiest?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
trunk_hours = Counter()
for r in data:
    trunk = r.get('Outbound trunk') or r.get('Inbound trunk')
    hour = r.get('Start time', '')[:13]
    if trunk and hour:
        trunk_hours[(trunk, hour)] += 1
for (trunk, hour), count in sorted(trunk_hours.items()):
    print(f'{trunk} | {hour}: {count} calls')
"
```

**Recipe 35 — Route group distribution**
Question: "How is traffic distributed across route groups?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
groups = Counter(r.get('Route group') for r in data if r.get('Route group'))
for group, count in groups.most_common():
    print(f'{group}: {count} calls')
"
```

**Recipe 36 — Redirect chain analysis**
Question: "How many calls were forwarded/redirected?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
redirected = [r for r in data if r.get('Redirect reason')]
print(f'Redirected calls: {len(redirected)} of {len(data)} ({len(redirected)/len(data)*100:.1f}%)' if data else 'No data')
reasons = Counter(r.get('Redirect reason') for r in redirected)
for reason, count in reasons.most_common():
    print(f'  {reason}: {count}')
"
```

**Recipe 37 — Calls by redirect reason**
Question: "Why are calls being redirected?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
orig = Counter(r.get('Original reason') for r in data if r.get('Original reason'))
redirect = Counter(r.get('Redirect reason') for r in data if r.get('Redirect reason'))
related = Counter(r.get('Related reason') for r in data if r.get('Related reason'))
print('Original reasons:')
for r, c in orig.most_common(10): print(f'  {r}: {c}')
print('Redirect reasons:')
for r, c in redirect.most_common(10): print(f'  {r}: {c}')
print('Related reasons:')
for r, c in related.most_common(10): print(f'  {r}: {c}')
"
```

**Recipe 38 — Calls by original reason**
Question: "What triggers the first redirect?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
reasons = Counter(r.get('Original reason') for r in data if r.get('Original reason'))
for reason, count in reasons.most_common():
    print(f'{reason}: {count}')
"
```

**Recipe 39 — Forwarding loop detection**
Question: "Any calls redirected 3+ times (possible forwarding loops)?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import defaultdict
data = json.load(sys.stdin)
corr_counts = defaultdict(int)
corr_samples = {}
for r in data:
    cid = r.get('Correlation ID')
    if cid:
        corr_counts[cid] += 1
        corr_samples[cid] = r
loops = {cid: count for cid, count in corr_counts.items() if count >= 3}
print(f'Calls with 3+ legs (possible loops): {len(loops)}')
for cid, count in sorted(loops.items(), key=lambda x: x[1], reverse=True)[:10]:
    s = corr_samples[cid]
    print(f\"  {count} legs | {s.get('Start time')} | {s.get('Calling number')} -> {s.get('Called number')}\")
"
```

### Category 6: PSTN & Billing

**Recipe 40 — Calls by PSTN vendor**
Question: "How is traffic split across carriers?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
vendors = Counter(r.get('PSTN vendor name') for r in data if r.get('PSTN vendor name'))
for vendor, count in vendors.most_common():
    print(f'{vendor}: {count} calls')
"
```

**Recipe 41 — Duration by PSTN vendor**
Question: "Which carrier carries the most minutes?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import defaultdict
data = json.load(sys.stdin)
vendor_dur = defaultdict(int)
vendor_count = defaultdict(int)
for r in data:
    v = r.get('PSTN vendor name')
    if v:
        vendor_dur[v] += int(r.get('Duration', 0))
        vendor_count[v] += 1
for v, dur in sorted(vendor_dur.items(), key=lambda x: x[1], reverse=True):
    print(f'{v}: {dur}s ({dur/60:.1f} min) across {vendor_count[v]} calls')
"
```

**Recipe 42 — International calls by country**
Question: "Which countries are we calling?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
countries = Counter(r.get('International country') for r in data if r.get('International country'))
print(f'International calls to {len(countries)} countries:')
for country, count in countries.most_common():
    print(f'  {country}: {count} calls')
"
```

**Recipe 43 — International call duration by country**
Question: "How many minutes to each country?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import defaultdict
data = json.load(sys.stdin)
country_dur = defaultdict(int)
country_count = defaultdict(int)
for r in data:
    c = r.get('International country')
    if c:
        country_dur[c] += int(r.get('Duration', 0))
        country_count[c] += 1
for c, dur in sorted(country_dur.items(), key=lambda x: x[1], reverse=True):
    print(f'{c}: {dur/60:.1f} min ({country_count[c]} calls)')
"
```

**Recipe 44 — Call type mix**
Question: "What's our toll-free vs premium vs national breakdown?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
types = Counter(r.get('Call type', 'Unknown') for r in data)
total = len(data)
for t, c in types.most_common():
    print(f'{t}: {c} ({c/total*100:.1f}%)')
"
```

**Recipe 45 — Authorization code usage**
Question: "Which auth codes are being used and how often?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
codes = Counter(r.get('Authorization code') for r in data if r.get('Authorization code'))
if codes:
    print(f'{len(codes)} auth codes in use:')
    for code, count in codes.most_common():
        print(f'  {code}: {count} calls')
else:
    print('No calls with authorization codes found')
"
```

**Recipe 46 — PSTN vendor comparison**
Question: "Compare carriers on volume and duration"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import defaultdict
data = json.load(sys.stdin)
stats = defaultdict(lambda: {'calls': 0, 'duration': 0, 'answered': 0})
for r in data:
    v = r.get('PSTN vendor name')
    if v:
        stats[v]['calls'] += 1
        stats[v]['duration'] += int(r.get('Duration', 0))
        if r.get('Answer indicator') == 'Yes':
            stats[v]['answered'] += 1
print(f\"{'Vendor':<30} {'Calls':>6} {'Minutes':>8} {'Answer%':>8}\")
print('-' * 55)
for v, s in sorted(stats.items(), key=lambda x: x[1]['calls'], reverse=True):
    rate = s['answered']/s['calls']*100 if s['calls'] else 0
    print(f\"{v:<30} {s['calls']:>6} {s['duration']/60:>8.1f} {rate:>7.1f}%\")
"
```

### Category 7: Device & Client

**Recipe 47 — Client type distribution**
Question: "What are people using to make calls?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
clients = Counter(r.get('Client type', 'Unknown') for r in data)
total = len(data)
for client, count in clients.most_common():
    print(f'{client}: {count} ({count/total*100:.1f}%)')
"
```

**Recipe 48 — Device model inventory**
Question: "What phone models are active in CDR?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
models = Counter(r.get('Model') for r in data if r.get('Model'))
print(f'{len(models)} device models seen:')
for model, count in models.most_common():
    print(f'  {model}: {count} calls')
"
```

**Recipe 49 — Calls by OS type**
Question: "Mobile vs desktop breakdown?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
os_types = Counter(r.get('OS type') for r in data if r.get('OS type'))
for os, count in os_types.most_common():
    print(f'{os}: {count} calls')
"
```

**Recipe 50 — Softphone vs desk phone ratio**
Question: "How many calls from Webex app vs physical phones?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
total = len(data)
app = len([r for r in data if r.get('Client type') in ('WXC_CLIENT', 'TEAMS_WXC_CLIENT')])
device = len([r for r in data if r.get('Client type') == 'WXC_DEVICE'])
sip = len([r for r in data if r.get('Client type') == 'SIP'])
other = total - app - device - sip
print(f'Webex App (softphone): {app} ({app/total*100:.1f}%)')
print(f'Desk phone (WXC_DEVICE): {device} ({device/total*100:.1f}%)')
print(f'SIP endpoint: {sip} ({sip/total*100:.1f}%)')
print(f'Other: {other} ({other/total*100:.1f}%)')
"
```

**Recipe 51 — Webex Go mobile calls**
Question: "How many calls over cellular (Webex Go)?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
mobile = [r for r in data if r.get('Sub client type') == 'MOBILE_NETWORK']
print(f'Webex Go (mobile network) calls: {len(mobile)} of {len(data)}')
if not mobile:
    print('No matching records found in this time window.')
else:
    for c in mobile[:10]:
        print(f\"  {c.get('Start time')} | {c.get('User')} | {c.get('Direction')} | {c.get('Duration')}s\")
"
```

**Recipe 52 — Client version distribution**
Question: "Are users on the latest app version?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
versions = Counter(r.get('Client version') for r in data if r.get('Client version'))
for version, count in versions.most_common(15):
    print(f'{version}: {count} calls')
"
```

### Category 8: Spam & Reputation

**Recipe 53 — Reputation score distribution**
Question: "How many calls by reputation score range?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
buckets = Counter()
for r in data:
    score = r.get('Caller Reputation Score')
    if score:
        s = float(score)
        if s <= 1.0: buckets['0-1 (likely spam)'] += 1
        elif s <= 2.0: buckets['1-2 (suspicious)'] += 1
        elif s <= 3.0: buckets['2-3 (neutral)'] += 1
        elif s <= 4.0: buckets['3-4 (probably ok)'] += 1
        else: buckets['4-5 (trusted)'] += 1
has_score = sum(buckets.values())
print(f'Calls with reputation scores: {has_score} of {len(data)}')
for bucket, count in sorted(buckets.items()):
    print(f'  {bucket}: {count}')
"
```

**Recipe 54 — Blocked vs allowed ratio**
Question: "What percentage of calls are we blocking?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
results = Counter(r.get('Caller Reputation Service Result') for r in data if r.get('Caller Reputation Service Result'))
total = sum(results.values())
for result, count in results.most_common():
    print(f'{result}: {count} ({count/total*100:.1f}%)')
"
```

**Recipe 55 — Top blocked numbers**
Question: "Which numbers get blocked most?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
blocked = Counter(r.get('Calling number') for r in data
    if r.get('Caller Reputation Service Result') in ('block', 'captcha-block'))
print(f'Top blocked callers:')
for number, count in blocked.most_common(15):
    print(f'  {number}: {count} blocked calls')
"
```

**Recipe 56 — Spam rate by location**
Question: "Which office gets the most spam?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import defaultdict
data = json.load(sys.stdin)
stats = defaultdict(lambda: {'total': 0, 'spam': 0})
for r in data:
    loc = r.get('Location', 'Unknown')
    stats[loc]['total'] += 1
    result = r.get('Caller Reputation Service Result', '')
    if result in ('block', 'captcha-block', 'captcha-allow'):
        stats[loc]['spam'] += 1
for loc, s in sorted(stats.items(), key=lambda x: x[1]['spam'], reverse=True):
    rate = s['spam']/s['total']*100 if s['total'] else 0
    print(f\"{loc}: {s['spam']} spam ({rate:.1f}%) of {s['total']} total\")
"
```

**Recipe 57 — Captcha effectiveness**
Question: "How many captcha challenges succeed vs fail?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
captcha_allow = len([r for r in data if r.get('Caller Reputation Service Result') == 'captcha-allow'])
captcha_block = len([r for r in data if r.get('Caller Reputation Service Result') == 'captcha-block'])
total_captcha = captcha_allow + captcha_block
if total_captcha:
    print(f'Captcha challenges: {total_captcha}')
    print(f'  Passed: {captcha_allow} ({captcha_allow/total_captcha*100:.1f}%)')
    print(f'  Failed: {captcha_block} ({captcha_block/total_captcha*100:.1f}%)')
else:
    print('No captcha challenges found')
"
```

### Category 9: Recording Compliance

**Recipe 58 — Recording success rate**
Question: "What percentage of recordings succeed?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
results = Counter(r.get('Call Recording Result') for r in data if r.get('Call Recording Result'))
total = sum(results.values())
print(f'Calls with recording data: {total}')
for result, count in results.most_common():
    print(f'  {result}: {count} ({count/total*100:.1f}%)')
"
```

**Recipe 59 — Recording by platform**
Question: "Which recording platforms are in use?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
platforms = Counter(r.get('Call Recording Platform Name') for r in data if r.get('Call Recording Platform Name'))
for platform, count in platforms.most_common():
    print(f'{platform}: {count} calls')
"
```

**Recipe 60 — Recording by trigger type**
Question: "How are recordings initiated?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
triggers = Counter(r.get('Call Recording Trigger') for r in data if r.get('Call Recording Trigger'))
for trigger, count in triggers.most_common():
    print(f'{trigger}: {count} calls')
"
```

**Recipe 61 — Failed recordings**
Question: "Which calls failed to record?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
failed = [r for r in data if r.get('Call Recording Result') == 'failed']
print(f'Failed recordings: {len(failed)}')
if not failed:
    print('No matching records found in this time window.')
else:
    for c in failed[:15]:
        print(f\"  {c.get('Start time')} | {c.get('User')} | {c.get('Call Recording Platform Name')} | {c.get('Calling number')} -> {c.get('Called number')}\")
"
```

**Recipe 62 — Unrecorded calls analysis**
Question: "How many answered calls have no recording data?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
answered = [r for r in data if r.get('Answer indicator') == 'Yes']
no_recording = [r for r in answered if not r.get('Call Recording Result')]
print(f'Answered calls: {len(answered)}')
print(f'With recording data: {len(answered) - len(no_recording)}')
print(f'Without recording data: {len(no_recording)}')
if no_recording:
    locs = Counter(r.get('Location', 'Unknown') for r in no_recording)
    print('Unrecorded by location:')
    for loc, count in locs.most_common():
        print(f'  {loc}: {count}')
"
```

**Recipe 63 — Recording compliance by location**
Question: "Which office has the worst recording rate?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import defaultdict
data = json.load(sys.stdin)
stats = defaultdict(lambda: {'answered': 0, 'recorded': 0, 'failed': 0})
for r in data:
    if r.get('Answer indicator') == 'Yes':
        loc = r.get('Location', 'Unknown')
        stats[loc]['answered'] += 1
        result = r.get('Call Recording Result', '')
        if result == 'successful':
            stats[loc]['recorded'] += 1
        elif result == 'failed':
            stats[loc]['failed'] += 1
for loc, s in sorted(stats.items(), key=lambda x: x[1]['recorded']/max(x[1]['answered'],1)):
    rate = s['recorded']/s['answered']*100 if s['answered'] else 0
    print(f\"{loc}: {rate:.1f}% recorded ({s['recorded']}/{s['answered']}, {s['failed']} failed)\")
"
```

### Category 10: Call Tracing & Diagnostics

**Recipe 64 — Trace call by correlation ID**
Question: "Find all legs of this call"
Note: Replace CORRELATION_ID with the actual value.
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
cid = 'CORRELATION_ID'
legs = [r for r in data if r.get('Correlation ID') == cid]
print(f'Found {len(legs)} legs for correlation ID {cid}:')
if not legs:
    print('No matching records found in this time window.')
else:
    for i, c in enumerate(sorted(legs, key=lambda x: x.get('Start time', '')), 1):
        print(f'  Leg {i}: {c.get(\"Start time\")} | {c.get(\"Direction\")} | {c.get(\"Calling number\")} -> {c.get(\"Called number\")} | {c.get(\"Duration\")}s | {c.get(\"Related reason\", \"\")}')
"
```

**Recipe 65 — Transfer chain reconstruction**
Question: "Show the full transfer path for this call"
Note: Replace CALL_ID with the actual Call ID.
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
target = 'CALL_ID'
chain = [r for r in data if r.get('Call ID') == target or r.get('Transfer related call ID') == target or r.get('Related call ID') == target]
print(f'Transfer chain ({len(chain)} records):')
if not chain:
    print('No matching records found in this time window.')
else:
    for c in sorted(chain, key=lambda x: x.get('Start time', '')):
        print(f\"  {c.get('Start time')} | {c.get('User')} | {c.get('Direction')} | {c.get('Related reason', '')} | {c.get('Calling number')} -> {c.get('Called number')}\")
"
```

**Recipe 66 — Park and retrieve trace**
Question: "How many calls were parked? Average park duration?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
parked = [r for r in data if r.get('Related reason') and 'CallPark' in r.get('Related reason', '')]
retrieved = [r for r in data if r.get('Related reason') and 'CallParkRetrieve' in r.get('Related reason', '')]
print(f'Call Park events: {len(parked)}')
print(f'Call Park Retrieve events: {len(retrieved)}')
if not parked:
    print('No matching records found in this time window.')
else:
    for c in parked[:10]:
        print(f\"  {c.get('Start time')} | {c.get('User')} | {c.get('Calling number')} -> {c.get('Called number')}\")
"
```

**Recipe 67 — Forwarding path reconstruction**
Question: "How did this call reach this user?"
Note: Replace CORRELATION_ID with the actual value.
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
cid = 'CORRELATION_ID'
legs = sorted([r for r in data if r.get('Correlation ID') == cid], key=lambda x: x.get('Start time', ''))
print(f'Forwarding path ({len(legs)} hops):')
if not legs:
    print('No matching records found in this time window.')
else:
    for i, c in enumerate(legs, 1):
        orig = c.get('Original reason', '-')
        redir = c.get('Redirect reason', '-')
        related = c.get('Related reason', '-')
        print(f'  Hop {i}: {c.get(\"User\", \"?\")} | orig={orig} | redirect={redir} | related={related}')
"
```

**Recipe 68 — Call quality proxy (failure patterns)**
Question: "Find calls with likely quality issues"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
short_fail = [r for r in data
    if r.get('Answer indicator') == 'Yes'
    and int(r.get('Duration', 0)) < 5
    and r.get('Call outcome') == 'Failure']
sip_errors = [r for r in data if r.get('Call outcome reason', '').startswith('SIP')]
print(f'Short answered calls that failed (<5s): {len(short_fail)}')
print(f'SIP error outcomes: {len(sip_errors)}')
if sip_errors:
    from collections import Counter
    reasons = Counter(r.get('Call outcome reason') for r in sip_errors)
    for reason, count in reasons.most_common(10):
        print(f'  {reason}: {count}')
"
```

**Recipe 69 — Repeated caller detection**
Question: "Who's calling the same number over and over?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
pairs = Counter((r.get('Calling number', '?'), r.get('Called number', '?')) for r in data)
repeats = {pair: count for pair, count in pairs.items() if count >= 3}
print(f'Number pairs with 3+ calls:')
for (caller, called), count in sorted(repeats.items(), key=lambda x: x[1], reverse=True)[:15]:
    print(f'  {caller} -> {called}: {count} calls')
"
```

### Category 11: Cross-Category Compound Queries

**Recipe 70 — Spam that reached a queue and was abandoned**
Question: "Spam calls that made it into a queue and the caller hung up?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
spam_queue_abandoned = [r for r in data
    if r.get('Caller Reputation Service Result') in ('captcha-allow', 'allow')
    and float(r.get('Caller Reputation Score') or '5') < 2.0
    and r.get('Queue type')
    and r.get('Answer indicator') == 'No']
print(f'Low-reputation calls that reached a queue and were abandoned: {len(spam_queue_abandoned)}')
if not spam_queue_abandoned:
    print('No matching records found in this time window.')
else:
    for c in spam_queue_abandoned[:10]:
        print(f\"  {c.get('Start time')} | score={c.get('Caller Reputation Score')} | {c.get('Calling number')} | queue={c.get('Queue type')}\")
"
```

**Recipe 71 — International calls on a specific trunk during business hours**
Question: "International calls on trunk X during business hours?"
Note: Replace TRUNK_NAME with the actual trunk name.
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
trunk_name = 'TRUNK_NAME'
results = [r for r in data
    if r.get('Call type') == 'SIP_INTERNATIONAL'
    and (r.get('Outbound trunk') == trunk_name or r.get('Inbound trunk') == trunk_name)
    and 8 <= int(r.get('Start time', '')[11:13] or '0') < 18]
print(f'International calls on {trunk_name} during business hours: {len(results)}')
total_dur = sum(int(r.get('Duration', 0)) for r in results)
print(f'Total duration: {total_dur/60:.1f} min')
if not results:
    print('No matching records found in this time window.')
else:
    for c in results[:10]:
        print(f\"  {c.get('Start time')} | {c.get('User')} | {c.get('Called number')} | {c.get('Duration')}s\")
"
```

**Recipe 72 — Calls forwarded twice that ended in voicemail**
Question: "Calls that were forwarded multiple times and ended in voicemail?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import defaultdict
data = json.load(sys.stdin)
corr_legs = defaultdict(list)
for r in data:
    cid = r.get('Correlation ID')
    if cid:
        corr_legs[cid].append(r)
multi_fwd_vm = []
for cid, legs in corr_legs.items():
    redirected = [l for l in legs if l.get('Redirect reason')]
    vm = [l for l in legs if 'VoiceMail' in l.get('Related reason', '') or 'VoiceMailRetrieval' in l.get('Related reason', '')]
    if len(redirected) >= 2 and vm:
        multi_fwd_vm.append((cid, legs))
print(f'Calls forwarded 2+ times ending in voicemail: {len(multi_fwd_vm)}')
if not multi_fwd_vm:
    print('No matching records found in this time window.')
else:
    for cid, legs in multi_fwd_vm[:5]:
        first = sorted(legs, key=lambda x: x.get('Start time', ''))[0]
        print(f\"  {first.get('Start time')} | {first.get('Calling number')} | {len(legs)} legs\")
"
```

**Recipe 73 — Missed calls from repeat callers**
Question: "Repeat callers we keep missing?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
missed = [r for r in data if r.get('Answer indicator') == 'No']
repeat_missed = Counter(r.get('Calling number', '?') for r in missed)
repeats = {num: count for num, count in repeat_missed.items() if count >= 2}
print(f'Callers with 2+ missed calls:')
for num, count in sorted(repeats.items(), key=lambda x: x[1], reverse=True)[:15]:
    print(f'  {num}: {count} missed calls')
"
```

**Recipe 74 — Long-hold calls that were transferred**
Question: "Calls with long hold that ended up being transferred?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
hold_transfer = [r for r in data
    if int(r.get('Hold duration', 0)) > 60
    and r.get('Related reason') and 'Transfer' in r.get('Related reason', '')]
print(f'Calls with >60s hold then transferred: {len(hold_transfer)}')
if not hold_transfer:
    print('No matching records found in this time window.')
else:
    for c in hold_transfer[:10]:
        print(f\"  {c.get('Start time')} | {c.get('User')} | hold {c.get('Hold duration')}s | {c.get('Related reason')}\")
"
```

**Recipe 75 — After-hours emergency calls**
Question: "Emergency calls outside business hours?"
```bash
wxcli cdr list --start-time START --end-time END -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
after_hours_emergency = [r for r in data
    if r.get('Call type') == 'SIP_EMERGENCY'
    and (int(r.get('Start time', '')[11:13] or '0') < 8 or int(r.get('Start time', '')[11:13] or '0') >= 18)]
print(f'After-hours emergency calls: {len(after_hours_emergency)}')
if not after_hours_emergency:
    print('No matching records found in this time window.')
else:
    for c in after_hours_emergency[:10]:
        print(f\"  {c.get('Start time')} | {c.get('User')} | {c.get('Location')} | {c.get('Calling number')} -> {c.get('Called number')}\")
"
```

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
curl -H "Authorization: Bearer $(wxcli token)" -o report.zip "DOWNLOAD_URL"
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

CDR pulls are slow (8+ sequential API calls for a multi-day window). This section prevents redundant pulls across follow-up questions in the same conversation.

### Two-phase split

1. **Pull phase** — requires `wxc-calling-builder` agent (wxcli hook blocks direct CLI calls). The caller (Claude's main context) spawns the builder agent with instructions to pull CDR data and save to `/tmp/cdr-session.json`. The builder agent handles multi-pull merge for windows >12h automatically. Once the file is written, the builder agent's job is done — do not keep it running.
2. **Recipe phase** — runs directly via Bash, no agent spawn needed. `cat /tmp/cdr-session.json | python3.11 -c "..."` executes in ~2 seconds. The skill guides recipe selection; Claude executes inline.

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
3. **Cache miss** — requested window extends beyond `_meta` boundaries, or file doesn't exist, or user says "refresh" → spawn `wxc-calling-builder` to re-pull. Builder overwrites the cache file with the new window.
4. **Explicit refresh** — if the user says "refresh", "re-pull", or "new data", always re-pull regardless of cache state.

### Presentation format

Read the recipe's `print()` output, match it to the closest pattern below, and format accordingly. Do not pre-map recipes to patterns — match dynamically from the output shape.

**Patterns:**

| Pattern | Output shape | Markdown format |
|---------|-------------|-----------------|
| **Summary stats** | Key/value pairs (Total: N, Rate: X%) | 2-column table: Metric / Value |
| **Top-N / Counter** | Item + count, sorted | 2-column table: [Field] / Count, sorted desc. Top 15 max; note total if truncated |
| **Detail rows** | Per-record details (time, user, number, reason) | Multi-column table: one row per record, max 10 rows; note "N more not shown" if truncated |
| **Aggregation** | Stats like avg/max/min/count | 2-column table: Metric / Value |
| **Grouped** | Group key + multiple metrics per group | Multi-column table: [Group] / Metric1 / Metric2 / ..., sorted by worst-performing first |
| **Trace** | Ordered sequence of call legs | Multi-column table: Leg # / Time / Direction / User / Reason, chronological order |

**Rules for all patterns:**
- One summary line above the table (e.g., "5 missed calls out of 247 total (2.0%)")
- No commentary below the table unless the user asks "why", "what do you see", or "analyze this"
- If the recipe prints `No matching records found in this time window.`, say that — no table
- Percentages to 1 decimal place
- Timestamps trimmed to `YYYY-MM-DD HH:MM` (drop seconds and timezone)
- Phone numbers as-is (don't format E.164)
- If output doesn't fit any pattern, fall back to a fenced code block with raw output

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
6. **Rate limits:** 1 request/minute + 10 pagination/minute per user token.
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
