---
name: reporting-meetings
description: |
  Query and analyze Webex meetings quality, usage reports, workspace utilization,
  historical platform analytics, and live meeting monitoring.
  NOT for: Webex Calling CDR/queue stats (use reporting skill), Contact Center analytics
  (use reporting-cc skill), or scheduling/managing meetings (use manage-meetings skill).
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [meetings-report-type]
---

# Meetings & Workspace Analytics Workflow

**Checkpoint — do NOT proceed until you can answer these:**
1. Which CLI group provides per-meeting quality data in JSON? (Answer: `wxcli meeting-qualities` — returns jitter, latency, packet loss per media session. Faster than async CSV reports for single-meeting troubleshooting.)
2. Which CLI group provides historical platform analytics? (Answer: `wxcli analytics` — messaging daily totals, room device metrics, meetings aggregates.)

If you cannot answer both, read `docs/reference/meetings-infrastructure.md` and `docs/reference/reporting-analytics.md` before proceeding.

## Step 1: Load references

1. Read `docs/reference/meetings-infrastructure.md` for meeting quality, participants, Video Mesh
2. Read `docs/reference/meetings-core.md` for meeting CRUD and reports
3. Read `docs/reference/reporting-analytics.md` Section 2-3 for report templates

**Mandatory --help verification:** Before constructing any wxcli command, run `wxcli <group> --help` to verify the subcommand exists, then `wxcli <group> <subcommand> --help` to verify the exact flags (e.g. `wxcli meeting-qualities --help` and `wxcli meeting-reports --help`). Do NOT rely on examples in this skill or reference docs — the CLI is auto-generated and flag names may differ from what documentation suggests.

## Step 2: Verify auth token

```bash
wxcli whoami
```

### Required scopes

| Report Type | Scope |
|-------------|-------|
| Meeting quality | `analytics:read_all` |
| Meeting usage/attendees | `analytics:read_all` |
| Historical analytics | `analytics:read_all` |
| Workspace metrics | `spark-admin:workspace_metrics_read` |
| Live monitoring | `analytics:read_all` |

## Step 3: Identify the reporting need

| Need | CLI Group | Command |
|------|-----------|---------|
| Quality for a specific meeting (jitter, latency, loss) | `meeting-qualities` | `list` |
| Meeting usage trends | `meeting-reports` | `list` |
| Meeting attendee details | `meeting-reports` | `list-attendees` |
| Historical messaging metrics | `analytics` | `show` |
| Historical room device metrics | `analytics` | `show-daily-totals` |
| Historical meetings aggregates | `analytics` | `show-aggregates` |
| Workspace usage | `workspace-metrics` | `list` |
| Workspace duration | `workspace-metrics` | `list-workspace-duration-metrics` |
| Live meeting counts | `live-monitoring` | `create` |

## Step 4: Execute and analyze

### Meeting Quality

```bash
wxcli meeting-qualities list --meeting-id MEETING_ID -o json
```

#### Recipe M-1 — Meeting quality for a specific meeting
Question: "How was the quality on yesterday's all-hands?"

Quality is reported per media session, not per participant: `jitter`, `latency` and
`packetLoss` are sample arrays inside each `audioIn`/`audioOut` entry, so this takes
the peak across a participant's audio sessions. The participant is named by
`webexUserName`.
```bash
wxcli meeting-qualities list --meeting-id MEETING_ID -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
items = data if isinstance(data, list) else data.get('items', [data])
for p in items:
    name = p.get('webexUserName') or p.get('webexUserEmail') or '?'
    sessions = (p.get('audioIn') or []) + (p.get('audioOut') or [])
    peaks = []
    for metric in ('jitter', 'latency', 'packetLoss'):
        vals = [v for s in sessions for v in (s.get(metric) or [])]
        peaks.append(metric + '=' + (str(max(vals)) if vals else 'N/A'))
    print(f'{name}: peak audio ' + ' '.join(peaks))
"
```

#### Recipe M-2 — Quality issues in a meeting
Question: "Did anyone have bad quality?"
```bash
wxcli meeting-qualities list --meeting-id MEETING_ID -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
items = data if isinstance(data, list) else data.get('items', [data])
issues = []
for p in items:
    name = p.get('webexUserName') or p.get('webexUserEmail') or '?'
    sessions = (p.get('audioIn') or []) + (p.get('audioOut') or [])
    bad = []
    for metric, limit in (('jitter', 30), ('latency', 200), ('packetLoss', 5)):
        vals = [float(v) for s in sessions for v in (s.get(metric) or []) if v is not None]
        if vals and max(vals) > limit:
            bad.append(f'{metric}={max(vals)}')
    if bad:
        issues.append(f'{name}: ' + ' '.join(bad))
if issues:
    print(f'{len(issues)} participants with quality issues:')
    for i in issues: print(f'  {i}')
else:
    print('No quality issues detected (thresholds: jitter>30ms, latency>200ms, packetLoss>5%)')
"
```

### Meeting Usage

#### Recipe M-3 — Meeting usage summary
Question: "How many meetings are we having?"
```bash
wxcli meeting-reports list --site-url SITE_URL -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
items = data if isinstance(data, list) else data.get('items', [data])
print(f'Meetings in the report window: {len(items)}')
by_day = Counter(str(r.get('start', ''))[:10] or '?' for r in items)
for day in sorted(by_day)[:10]:
    print(f'  {day}: {by_day[day]} meetings')
"
```

#### Recipe M-4 — Meeting attendance
Question: "Who joined, and how many of them were on the invite list?"

The attendee report only contains people who joined — there is no row for an invitee
who never showed up, so the join *rate* is not answerable here. For the invited total,
read `totalInvitee` from `meeting-reports list`.
```bash
wxcli meeting-reports list-attendees --site-url SITE_URL --meeting-id MEETING_ID -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
items = data if isinstance(data, list) else data.get('items', [data])
invited = [a for a in items if a.get('invited')]
print(f'Joined: {len(items)}; of those, {len(invited)} were invited' if items else 'No data')
"
```

### Historical Analytics

#### Recipe M-5 — Messaging adoption trend
Question: "Is messaging usage growing?"

This endpoint returns one object, not a list: `startDate`, `endDate`, and a `metrics`
object holding parallel arrays — `dates` alongside `totalMessagesSent`, `dailyActiveUsers`
and the rest. Zip them to get a per-day series.
```bash
wxcli analytics show -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
m = data.get('metrics') or {}
series = [m.get(k) or [] for k in ('dates', 'totalMessagesSent')]
print(f\"{data.get('startDate', '?')} to {data.get('endDate', '?')}\")
for d, n in list(zip(*series))[:14]:
    print(f'{d}: {n} messages')
"
```

#### Recipe M-6 — Room device utilization
Question: "Are our room devices being used?"

Same object shape as M-5: `metrics` holds `dates` alongside `totalActiveDevices`,
`totalUsageHours`, `incallUsageDuration` and the rest.
```bash
wxcli analytics show-daily-totals -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
m = data.get('metrics') or {}
series = [m.get(k) or [] for k in ('dates', 'totalActiveDevices')]
print(f\"{data.get('startDate', '?')} to {data.get('endDate', '?')}\")
for d, n in list(zip(*series))[:14]:
    print(f'{d}: {n} active devices')
"
```

#### Recipe M-7 — Meetings aggregate comparison
Question: "How do this month's meetings compare?"
```bash
wxcli analytics show-aggregates --site-url SITE_URL -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
if isinstance(data, dict):
    for key, val in data.items():
        print(f'{key}: {val}')
else:
    print(json.dumps(data, indent=2))
"
```

### Workspace Metrics

#### Recipe M-8 — Workspace occupancy
Question: "Which rooms are used the most?"
```bash
wxcli workspace-metrics list --workspace-id WORKSPACE_ID --metric-name soundLevel -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
items = data if isinstance(data, list) else data.get('items', [data])
for w in sorted(items, key=lambda x: x.get('utilizationPercentage', x.get('occupancy', 0)), reverse=True)[:15]:
    name = w.get('workspaceName', w.get('name', '?'))
    util = w.get('utilizationPercentage', w.get('occupancy', 0))
    print(f'{name}: {util}% utilized')
"
```

#### Recipe M-9 — Workspace duration analysis
Question: "How long is this room occupied on average?"

`--workspace-id` is required, so one call covers one workspace and the rows carry no
workspace name — each row is one interval: `start`, `end`, `duration`. The command
emits only `items`, dropping the response's top-level `unit` (example: `minutes`), so
the durations below are left in the unit the API returned them in.
```bash
wxcli workspace-metrics list-workspace-duration-metrics --workspace-id WORKSPACE_ID -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
items = data if isinstance(data, list) else data.get('items', [data])
durations = [d for d in (i.get('duration') for i in items) if isinstance(d, (int, float))]
if durations:
    print(f'{len(durations)} intervals: avg {sum(durations)/len(durations):.1f}, max {max(durations):.1f}')
else:
    print('No duration data')
"
```

### Live Monitoring

#### Recipe M-10 — Live meetings right now
Question: "How many meetings are happening globally?"
```bash
wxcli live-monitoring create -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
if isinstance(data, dict):
    for country, count in sorted(data.items(), key=lambda x: x[1] if isinstance(x[1], (int,float)) else 0, reverse=True):
        print(f'{country}: {count}')
else:
    print(json.dumps(data, indent=2))
"
```

#### Recipe M-11 — Quality by participant (recurring issues)
Question: "Who has recurring quality issues across meetings?"
Note: Requires multiple meeting quality pulls. Run for each recent meeting ID.
```bash
wxcli meeting-qualities list --meeting-id MEETING_ID_1 -o json > /tmp/mq1.json
wxcli meeting-qualities list --meeting-id MEETING_ID_2 -o json > /tmp/mq2.json
python3.11 -c "
import json
from collections import defaultdict
issues = defaultdict(int)
for f in ['/tmp/mq1.json', '/tmp/mq2.json']:
    data = json.load(open(f))
    items = data if isinstance(data, list) else data.get('items', [data])
    for p in items:
        name = p.get('participantName', p.get('displayName', '?'))
        jitter = float(p.get('audioJitter', p.get('jitter', 0)) or 0)
        latency = float(p.get('audioLatency', p.get('latency', 0)) or 0)
        loss = float(p.get('audioPacketLoss', p.get('packetLoss', 0)) or 0)
        if jitter > 30 or latency > 200 or loss > 5:
            issues[name] += 1
for name, count in sorted(issues.items(), key=lambda x: x[1], reverse=True):
    print(f'{name}: quality issues in {count} meetings')
"
```

#### Recipe M-12 — Attendee report for compliance
Question: "Who attended this meeting?"
```bash
wxcli meeting-reports list-attendees --site-url SITE_URL --meeting-id MEETING_ID -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
items = data if isinstance(data, list) else data.get('items', [data])
for a in items:
    name = a.get('displayName', a.get('name', '?'))
    email = a.get('email', '?')
    joined = a.get('joinTime', a.get('joinedTime', '?'))
    left = a.get('leaveTime', a.get('leftTime', '?'))
    print(f'{name} ({email}): joined {joined}, left {left}')
"
```

#### Recipe M-13 — Top meeting hosts
Question: "Who schedules the most meetings?"
```bash
wxcli meeting-reports list --site-url SITE_URL -o json | python3.11 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
items = data if isinstance(data, list) else data.get('items', [data])
hosts = Counter(r.get('hostEmail', r.get('hostName', '?')) for r in items)
for host, count in hosts.most_common(15):
    print(f'{host}: {count} meetings')
"
```

---

## Critical Rules

1. **Meeting quality requires a meeting ID.** Use `wxcli meetings list` to find meeting IDs first.
2. **Historical analytics may require Pro Pack.** Depends on the data type.
3. **Live monitoring is a snapshot.** Data is current, not historical.
4. **Workspace metrics require workspace admin scope.** `spark-admin:workspace_metrics_read`.
5. **Response shapes vary across API versions.** Recipes use `isinstance` checks and field fallbacks.

---

## Context Compaction Recovery

If context compacts mid-execution:
1. Read `docs/reference/meetings-infrastructure.md` for meeting quality API details
2. Read `docs/reference/reporting-analytics.md` for report template details
3. Resume from the appropriate recipe
