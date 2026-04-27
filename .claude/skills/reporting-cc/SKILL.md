---
name: reporting-cc
description: |
  Query and analyze Webex Contact Center analytics: queue statistics, agent statistics,
  estimated wait time, agent summaries, task search, and real-time monitoring.
  Requires CC-scoped OAuth (cjp:config_read). For Webex Calling CDR and reports,
  use the reporting skill instead.
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [cc-report-type]
---

# Contact Center Analytics Workflow

**Checkpoint — do NOT proceed until you can answer these:**
1. What OAuth scope do CC analytics require? (Answer: `cjp:config_read` / `cjp:config_write` — standard admin tokens will NOT work.)
2. How is the CC region configured? (Answer: `wxcli set-cc-region <region>` — defaults to us1.)

If you cannot answer both, read `docs/reference/contact-center-analytics.md` before proceeding.

## Step 1: Load references

1. Read `docs/reference/contact-center-analytics.md` for CC analytics API details

## Step 2: Verify auth and region

```bash
wxcli whoami
```

CC APIs require CJP scopes (`cjp:config_read` / `cjp:config_write`). Two options: **OAuth Integration** (user-facing apps, interactive login) or **Service App** (production automation, no interactive login needed). If the token lacks CC scopes, the user needs to re-authenticate with one of these.

Verify region is set:
```bash
wxcli get-cc-region
```

If not set, configure it:
```bash
wxcli set-cc-region us1
```

Available regions: us1, eu1, eu2, anz1, ca1, jp1, sg1.

## Step 3: Identify the CC reporting need

| Need | CLI Group | Command |
|------|-----------|---------|
| Queue volume, wait times, service level | `cc-queue-stats` | `list` |
| Agent handle time, calls handled | `cc-agents` | `list-statistics` |
| Current estimated wait time | `cc-ewt` | `show` |
| AI-generated interaction summaries | `cc-agent-summaries` | `create`, `create-list` |
| Historical task/contact search | `cc-search` | `create` |
| Real-time queue/agent state | `cc-realtime` | `create` |
| Call monitoring | `cc-call-monitoring` | 7 commands |

## Step 4: Execute and analyze

### Queue Statistics

```bash
wxcli cc-queue-stats list -o json
```

#### Recipe CC-1 — Queue volume ranking
Question: "Which queue gets the most calls?"
```bash
wxcli cc-queue-stats list -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
items = data if isinstance(data, list) else data.get('items', [data])
for q in sorted(items, key=lambda x: x.get('totalCalls', x.get('callsOffered', 0)), reverse=True):
    name = q.get('queueName', q.get('name', '?'))
    calls = q.get('totalCalls', q.get('callsOffered', 0))
    print(f'{name}: {calls} calls')
"
```

#### Recipe CC-2 — Queue abandonment rate
Question: "What's our abandonment rate per queue?"
```bash
wxcli cc-queue-stats list -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
items = data if isinstance(data, list) else data.get('items', [data])
for q in items:
    name = q.get('queueName', q.get('name', '?'))
    total = q.get('totalCalls', q.get('callsOffered', 0))
    abandoned = q.get('callsAbandoned', 0)
    rate = abandoned/total*100 if total else 0
    print(f'{name}: {rate:.1f}% abandoned ({abandoned}/{total})')
"
```

#### Recipe CC-3 — Average wait time per queue
Question: "How long are callers waiting?"
```bash
wxcli cc-queue-stats list -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
items = data if isinstance(data, list) else data.get('items', [data])
for q in sorted(items, key=lambda x: x.get('avgWaitTime', x.get('averageWaitTime', 0)), reverse=True):
    name = q.get('queueName', q.get('name', '?'))
    wait = q.get('avgWaitTime', q.get('averageWaitTime', 0))
    print(f'{name}: avg {wait}s wait')
"
```

#### Recipe CC-4 — Service level by queue
Question: "Are we meeting our SLA?"
```bash
wxcli cc-queue-stats list -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
items = data if isinstance(data, list) else data.get('items', [data])
for q in items:
    name = q.get('queueName', q.get('name', '?'))
    sl = q.get('serviceLevel', q.get('serviceLevelPercentage', 'N/A'))
    print(f'{name}: {sl}% service level')
"
```

### Agent Statistics

```bash
wxcli cc-agents list-statistics -o json
```

#### Recipe CC-5 — Agent handle time ranking
Question: "Which agents are fastest/slowest?"
```bash
wxcli cc-agents list-statistics -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
items = data if isinstance(data, list) else data.get('items', [data])
for a in sorted(items, key=lambda x: x.get('avgHandleTime', x.get('averageHandleTime', 0)), reverse=True):
    name = a.get('agentName', a.get('name', '?'))
    aht = a.get('avgHandleTime', a.get('averageHandleTime', 0))
    print(f'{name}: avg {aht}s handle time')
"
```

#### Recipe CC-6 — Agent utilization
Question: "How busy is each agent?"
```bash
wxcli cc-agents list-statistics -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
items = data if isinstance(data, list) else data.get('items', [data])
for a in sorted(items, key=lambda x: x.get('callsHandled', x.get('totalCalls', 0)), reverse=True):
    name = a.get('agentName', a.get('name', '?'))
    handled = a.get('callsHandled', a.get('totalCalls', 0))
    print(f'{name}: {handled} calls handled')
"
```

### Estimated Wait Time

#### Recipe CC-7 — Current wait time check
Question: "What's the current wait for queue X?"
```bash
wxcli cc-ewt show -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
if isinstance(data, dict):
    print(f\"Estimated wait time: {data.get('estimatedWaitTime', data.get('ewt', 'N/A'))}s\")
else:
    for q in data:
        print(f\"{q.get('queueName', '?')}: {q.get('estimatedWaitTime', q.get('ewt', 'N/A'))}s\")
"
```

### Agent Summaries

#### Recipe CC-8 — Search interaction summaries
Question: "Find summaries mentioning billing disputes"
```bash
wxcli cc-agent-summaries create --json-body '{"query": "billing dispute"}' -o json
```

### Real-Time Monitoring

#### Recipe CC-9 — Real-time queue depth
Question: "How many callers are waiting right now?"
```bash
wxcli cc-realtime create -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
if isinstance(data, list):
    for q in data:
        print(f\"{q.get('queueName', '?')}: {q.get('callsInQueue', q.get('waitingCalls', 0))} waiting\")
else:
    print(json.dumps(data, indent=2))
"
```

#### Recipe CC-10 — Agent availability status
Question: "Who's available right now?"
```bash
wxcli cc-agents list -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
items = data if isinstance(data, list) else data.get('items', [data])
from collections import Counter
states = Counter(a.get('state', a.get('agentState', 'Unknown')) for a in items)
for state, count in states.most_common():
    print(f'{state}: {count} agents')
"
```

### Historical Search

#### Recipe CC-11 — Search tasks by date range
Question: "Show all contacts handled yesterday"
```bash
wxcli cc-search create --json-body '{"from": "2026-04-09T00:00:00Z", "to": "2026-04-10T00:00:00Z"}' -o json
```

#### Recipe CC-12 — Longest wait today
Question: "What was the worst wait time today?"
```bash
wxcli cc-queue-stats list -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
items = data if isinstance(data, list) else data.get('items', [data])
longest = max(items, key=lambda x: x.get('maxWaitTime', x.get('longestWaitTime', 0)), default={})
name = longest.get('queueName', longest.get('name', '?'))
wait = longest.get('maxWaitTime', longest.get('longestWaitTime', 0))
print(f'Longest wait: {wait}s in queue {name}')
"
```

---

## Critical Rules

1. **CC-scoped OAuth or Service App required.** Standard admin tokens get 403. Must use `cjp:config_read` / `cjp:config_write` — via OAuth Integration or Service App (both supported).
2. **Region must be set.** CC APIs route to regional endpoints. Default is us1.
3. **Response shapes vary.** CC APIs may return objects or arrays. Recipes handle both with `isinstance` checks.
4. **Field names vary.** Different CC API versions use different field names (e.g., `avgWaitTime` vs `averageWaitTime`). Recipes use fallbacks with `x.get('field1', x.get('field2', 0))`.
5. **Real-time data is ephemeral.** Snapshot of current state, not historical.

---

## Context Compaction Recovery

If context compacts mid-execution:
1. Read `docs/reference/contact-center-analytics.md` for API details
2. Verify CC auth with `wxcli whoami` and region with `wxcli get-cc-region`
3. Resume from the appropriate recipe
