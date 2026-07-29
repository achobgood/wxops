---
name: reporting-cc
description: |
  Query and analyze Webex Contact Center analytics: CC queue statistics, CC agent statistics,
  estimated wait time, agent summaries, task search, and real-time CC monitoring.
  Requires CC-scoped OAuth (cjp:config_read).
  NOT for: Webex Calling CDR/queue/AA stats (use reporting skill) or
  meetings/workspace analytics (use reporting-meetings skill).
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

**Mandatory --help verification:** Before constructing any wxcli command, run `wxcli <group> --help` to verify the subcommand exists, then `wxcli <group> <subcommand> --help` to verify the exact flags (e.g. `wxcli cc-queue-stats --help` and `wxcli cc-agents --help` — CC analytics groups carry the `cc-` prefix and are distinct from the Calling `reporting` skill's groups). Do NOT rely on examples in this skill or reference docs — the CLI is auto-generated and flag names may differ from what documentation suggests.

## Step 2: Verify auth and region

```bash
wxcli whoami
```

CC APIs require CJP scopes (`cjp:config_read` / `cjp:config_write`). Two options: **OAuth Integration** (user-facing apps, interactive login) or **Service App** (production automation, no interactive login needed). If the token lacks CC scopes, the user needs to re-authenticate with one of these.

Verify region is set. There is no getter command — region is stored in the wxcli
config file (`~/.wxcli/config.json`, `cc_region` key), set via `wxcli set-cc-region`.
Inspect the config file directly, or just call `set-cc-region` to (re)set it:

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
wxcli cc-queue-stats list --from 1784592000000 --to 1785196800000 -o json
```

#### Recipe CC-1 — Queue volume ranking
Question: "Which queue gets the most tasks offered?"
```bash
wxcli cc-queue-stats list --from 1784592000000 --to 1785196800000 -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
items = data if isinstance(data, list) else data.get('items', [data])
for q in sorted(items, key=lambda x: x.get('totalOfferedTasks', 0), reverse=True):
    name = q.get('queueName', q.get('name', '?'))
    offered = q.get('totalOfferedTasks', 0)
    print(f'{name}: {offered} tasks offered')
"
```

#### Recipe CC-2 — Queue abandonment rate
Question: "What's our abandonment rate per queue?"
```bash
wxcli cc-queue-stats list --from 1784592000000 --to 1785196800000 -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
items = data if isinstance(data, list) else data.get('items', [data])
for q in items:
    name = q.get('queueName', q.get('name', '?'))
    total = q.get('totalOfferedTasks', 0)
    abandoned = q.get('totalAbandonedTasks', 0)
    rate = abandoned/total*100 if total else 0
    print(f'{name}: {rate:.1f}% abandoned ({abandoned}/{total})')
"
```

#### Recipe CC-3 — Average wait time per queue
Question: "How long are callers waiting?"
```bash
wxcli cc-queue-stats list --from 1784592000000 --to 1785196800000 -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
items = data if isinstance(data, list) else data.get('items', [data])
for q in sorted(items, key=lambda x: x.get('averageEnqueuedTime', 0), reverse=True):
    name = q.get('queueName', q.get('name', '?'))
    wait = q.get('averageEnqueuedTime', 0)
    print(f'{name}: avg {wait}ms in queue')
"
```

#### Recipe CC-4 — Service level by queue
Question: "Are we meeting our SLA?"
```bash
wxcli cc-queue-stats list --from 1784592000000 --to 1785196800000 -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
items = data if isinstance(data, list) else data.get('items', [data])
for q in items:
    name = q.get('queueName', q.get('name', '?'))
    sl = q.get('serviceLevelThresholdPercentage', 'N/A')
    print(f'{name}: {sl}% service level')
"
```

### Agent Statistics

```bash
wxcli cc-agents list-statistics --from 1784592000000 --to 1785196800000 -o json
```

#### Recipe CC-5 — Agent handle time ranking
Question: "Which agents are fastest/slowest?"
```bash
wxcli cc-agents list-statistics --from 1784592000000 --to 1785196800000 -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
items = data if isinstance(data, list) else data.get('items', [data])
rows = [(a.get('agentName', a.get('name', '?')), c.get('channelType', '?'), c.get('averageHandledTime', 0))
        for a in items for c in a.get('channels', [])]
for name, channel, aht in sorted(rows, key=lambda r: r[2], reverse=True):
    print(f'{name} [{channel}]: avg {aht}ms handle time')
"
```

#### Recipe CC-6 — Agent utilization
Question: "How busy is each agent?"
```bash
wxcli cc-agents list-statistics --from 1784592000000 --to 1785196800000 -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
items = data if isinstance(data, list) else data.get('items', [data])
rows = [(a.get('agentName', a.get('name', '?')), sum(c.get('totalAcceptedTasks', 0) for c in a.get('channels', [])))
        for a in items]
for name, accepted in sorted(rows, key=lambda r: r[1], reverse=True):
    print(f'{name}: {accepted} tasks accepted')
"
```

### Estimated Wait Time

#### Recipe CC-7 — Current wait time check
Question: "What's the current wait for queue X?"
```bash
wxcli cc-ewt show --queue-id QUEUE_ID --lookback-minutes 30 -o json | python3.11 -c "
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
wxcli cc-agents list --from 1784592000000 -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
items = data if isinstance(data, list) else data.get('items', [data])
from collections import Counter
current = {}
for a in sorted(items, key=lambda x: x.get('startTime', 0)):
    if a.get('active'):
        current[a.get('agentId')] = a.get('currentState', 'Unknown')
states = Counter(current.values())
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

#### Recipe CC-12 — Worst queue by average wait
Question: "Which queue kept callers waiting longest on average?"
Queue statistics expose no per-task maximum wait — `averageEnqueuedTime` is the
only wait metric in the response, so the peak wait of a single contact cannot be
answered here.
```bash
wxcli cc-queue-stats list --from 1784592000000 --to 1785196800000 -o json | python3.11 -c "
import json, sys
data = json.load(sys.stdin)
items = data if isinstance(data, list) else data.get('items', [data])
worst = max(items, key=lambda x: x.get('averageEnqueuedTime', 0), default={})
name = worst.get('queueName', worst.get('name', '?'))
wait = worst.get('averageEnqueuedTime', 0)
print(f'Worst average wait: {wait}ms in queue {name}')
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
2. Verify CC auth with `wxcli whoami` and region — check `cc_region` in `~/.wxcli/config.json` (no getter command; set/reset via `wxcli set-cc-region`)
3. Resume from the appropriate recipe
