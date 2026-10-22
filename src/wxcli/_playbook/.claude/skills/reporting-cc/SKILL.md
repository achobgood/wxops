---
name: reporting-cc
description: |
  Query and analyze Webex Contact Center analytics: CC queue statistics, CC agent statistics,
  estimated wait time, agent summaries, task search, and real-time CC monitoring.
  CC scopes (cjp:config_read) are required; a full-admin PAT was observed to work on 2026-10-13.
  NOT for: Webex Calling CDR/queue/AA stats (reporting) or meetings/workspace analytics
  (reporting-meetings).
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [cc-report-type]
---

# Contact Center Analytics Workflow

**Checkpoint — do NOT proceed until you can answer these:**
1. What OAuth scope do CC analytics require? (Answer: `cjp:config_read` / `cjp:config_write`. Observed 2026-10-13: a full-admin PAT got 200 on the analytics endpoints, so try the current token first; a 403 means the scopes are missing. A 401 "Token does not have access to OrgId:<base64>" is the orgId-format problem in Critical Rule 6 (fixed in the CLI 2026-10-13), not scope.)
2. How is the CC region configured? (Answer: `wxcli set-cc-region <region>` — defaults to us1.)

If you cannot answer both, read `docs/reference/contact-center-analytics.md` before proceeding.

## Step 1: Load references

1. Read `docs/reference/contact-center-analytics.md` for CC analytics API details

**Mandatory --help verification:** Before constructing any wxcli command, run `wxcli <group> --help` to verify the subcommand exists, then `wxcli <group> <subcommand> --help` to verify the exact flags (e.g. `wxcli cc-queue-stats --help` and `wxcli cc-agents --help` — CC analytics groups carry the `cc-` prefix and are distinct from the Calling `reporting` skill's groups). Do NOT rely on examples in this skill or reference docs — the CLI is auto-generated and flag names may differ from what documentation suggests.

## Step 2: Verify auth and region

```bash
wxcli whoami
```

CC APIs require CJP scopes (`cjp:config_read` / `cjp:config_write`). Two options: **OAuth Integration** (user-facing apps, interactive login) or **Service App** (production automation, no interactive login needed). If a call returns 403, the token lacks CC scopes and the user needs to re-authenticate with one of these. (Observed 2026-10-13: a full-admin PAT from developer.webex.com returned 200 on queue stats, agent stats/activities, EWT, task search, search metadata and agent summaries, so a PAT is worth trying first.)

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
| Which fields a search may filter, sort, group or aggregate on | `cc-search-metadata` | `list` |
| Real-time notifications (opens a websocket subscription — a change, not a read; see CC-9) | `cc-realtime` | `create` |
| Call monitoring | `cc-call-monitoring` | 7 commands |
| Consumption/billing extract for a resource type over a date range | `usage-reports` | `list-resource-types`, `create`, `show`, `list-download` |

## Step 4: Execute and analyze

### Queue Statistics

```bash
wxcli cc-queue-stats list --from 1784592000000 --to 1784677500000 -o json
```

Queue statistics answer at most 24 hours per call (live 400 `Querying only supported for 24 hours at a time`, 2026-10-20). The spec says the window must be **less than** 24 hours (86,400,000 ms) and rounds `--to` down to a 15-minute mark, so every example here asks for 23 h 45 min; for a longer period, make one call per day.

#### Recipe CC-1 — Queue volume ranking
Question: "Which queue gets the most tasks offered?"
```bash
wxcli cc-queue-stats list --from 1784592000000 --to 1784677500000 --fields 'reverse(sort_by(@, &totalOfferedTasks))[].{queueName: queueName, totalOfferedTasks: totalOfferedTasks}' -o table
```

#### Recipe CC-2 — Queue abandonment rate
Question: "What's our abandonment rate per queue?"
```bash
wxcli cc-queue-stats list --from 1784592000000 --to 1784677500000 -o json | python3.11 -c "
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
wxcli cc-queue-stats list --from 1784592000000 --to 1784677500000 --fields 'reverse(sort_by(@, &averageEnqueuedTime))[].{queueName: queueName, averageEnqueuedTime: averageEnqueuedTime}' -o table
```
`averageEnqueuedTime` is in milliseconds.

#### Recipe CC-4 — Service level by queue
Question: "Are we meeting our SLA?"
```bash
wxcli cc-queue-stats list --from 1784592000000 --to 1784677500000 --fields '[].{queueName: queueName, serviceLevelThresholdPercentage: serviceLevelThresholdPercentage}' -o table
```

### Agent Statistics

```bash
wxcli cc-agents list-statistics --from 1784592000000 --to 1784677500000 -o json
```

> **Unverified:** the spec gives `cc-agents list-statistics` the same limit (the window must be less than 24 hours, 86,400,000 ms); not measured live. The examples use the same 23 h 45 min window.

#### Recipe CC-5 — Agent handle time ranking
Question: "Which agents are fastest/slowest?"
```bash
wxcli cc-agents list-statistics --from 1784592000000 --to 1784677500000 -o json | python3.11 -c "
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
wxcli cc-agents list-statistics --from 1784592000000 --to 1784677500000 -o json | python3.11 -c "
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
wxcli cc-ewt show --queue-id QUEUE_ID --lookback-minutes 30 --fields '{estimatedWaitTime: estimatedWaitTime || ewt}' -o json
```
`null` means the API returned no estimate: it answers `204` when there are too few recent samples, and also for an unknown queue ID. The value is in **milliseconds**.

> **Unverified:** the spec says milliseconds; not measured live.

### Usage Reports

Consumption extracts, not live analytics: you request a report, it is generated asynchronously, and
you download the resulting **file(s)**. One request can yield several files — a long range is split
by calendar month — so read the ids out of `show` rather than assuming one.

#### Recipe CC-U1 — Generate and download a usage report
Question: "How much of resource X did we consume last month?"
```bash
# 1. What can be reported on, and for which dates is there data?
wxcli usage-reports list-resource-types

# 2. Request the report (asynchronous; returns the reportId)
wxcli usage-reports create --resource-type RESOURCE_TYPE --start-date 2026-08-01 --end-date 2026-09-01

# 3. Read the file ids off the report once it has generated
wxcli usage-reports show REPORT_ID --fields 'reportFiles[].fileId' -o text

# 4. Download each FILE by fileId -- a reportId will not work here
wxcli usage-reports list-download FILE_ID
```

`list-download` takes a `fileId`, never a `reportId`. `list-resource-types` is the real name of the
resource-type read — `list` is a hidden alias kept for compatibility and returns types, not reports;
the report collection is `list-usage-reports`. Full detail:
`docs/reference/contact-center-analytics.md` § 14.

### Agent Summaries

#### Recipe CC-8 — Look up an interaction's generated summary
Question: "Show me the AI summary of this interaction"
```bash
wxcli cc-agent-summaries create --json-body '{"orgId":"ORG_UUID","searchType":"AGENT","interactionId":"INTERACTION_ID","agentCiUserId":"AGENT_CI_USER_ID"}' -o json
```
This is a lookup of **one interaction for one agent** (body verified live 2026-10-13), not a
text search — there is no `query` key, so "find summaries mentioning X" is not answerable
here. `orgId` is the bare CC org UUID. Full detail: `docs/reference/contact-center-analytics.md`.

### Real-Time Monitoring

#### Recipe CC-9 — Real-time queue depth
Question: "How many callers are waiting right now?"

No read command returns live queue depth today; `cc-realtime create` opens a subscription (a change, so only the `wxops` agent may run it). `cc-queue-stats list` returns totals and averages over a time window (`totalEnqueuedTasks`, `averageEnqueuedTime` and the rest), not the number of callers waiting now. Say so rather than answering from it.

#### Recipe CC-10 — Agent availability status
Question: "Who's available right now?"
```bash
wxcli cc-agents list-activities --from 1784592000000 -o json | python3.11 -c "
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

> **Unverified:** the spec says the `--to` minus `--from` window of `cc-agents list-activities` must be less than 24 hours (86,400,000 ms), and `--to` defaults to now. For "right now", pass a `--from` (epoch ms) within the last 24 hours; the fixed `--from` above is only an example date. Not measured live.

### Historical Search

#### Recipe CC-11 — Search tasks by date range
Question: "Show all contacts handled yesterday"
```bash
# from/to are GraphQL arguments in epoch ms (ISO strings -> 400 "not a valid 'Long'"); example = 2026-10-12 UTC
wxcli cc-search create --query '{task(from: 1791763200000, to: 1791849600000){tasks{id channelType createdTime status}}}' -o json
```

#### Recipe CC-12 — Worst queue by average wait
Question: "Which queue kept callers waiting longest on average?"
Queue statistics expose no per-task maximum wait — `averageEnqueuedTime` is the
only wait metric in the response, so the peak wait of a single contact cannot be
answered here.
```bash
wxcli cc-queue-stats list --from 1784592000000 --to 1784677500000 --fields 'max_by(@, &averageEnqueuedTime).{queueName: queueName, averageEnqueuedTime: averageEnqueuedTime}' -o table
```
`averageEnqueuedTime` is in milliseconds.

---

## Critical Rules

1. **CC scopes (`cjp:config_read` / `cjp:config_write`) are required; a 403 means they are missing.** Fix: OAuth Integration or Service App with those scopes (both supported). Observed 2026-10-13: a full-admin PAT got no 403 on any analytics endpoint tried (queue stats, agent stats, agent activities, EWT, task search, search metadata, agent summaries), so do not assume a PAT is blocked.
2. **Region must be set.** CC APIs route to regional endpoints. Default is us1.
3. **Response shapes vary.** CC APIs may return objects or arrays. The Python recipes handle both with `isinstance` checks; the `--fields` recipes rely on `cc-queue-stats list` printing an array and `cc-ewt show` printing one object, and CC-9 branches on `type(@)`.
4. **Field names vary.** Different CC API versions use different field names (e.g., `avgWaitTime` vs `averageWaitTime`). Recipes use fallbacks with `x.get('field1', x.get('field2', 0))`.
5. **Real-time data is ephemeral.** Snapshot of current state, not historical.
6. **401 "Token does not have access to OrgId:<base64 id>" is NOT a scope problem, and is FIXED in the CLI (2026-10-13).** Older wxcli builds sent the saved base64 Spark org id as `orgId` on `cc-queue-stats list`, `cc-agents list-statistics`/`list-activities`, `cc-ewt show` and `cc-search create`, and the CC API rejected it. The CLI now sends the bare UUID; verified 200 on `cc-queue-stats list`, `cc-agents list-statistics`/`list-activities`, `cc-tasks list`, `cc-subscriptions` and 204 on `cc-ewt show`, and 200 on `cc-search create` (GraphQL task query). If you still see this 401, upgrade wxcli and check `wxcli whoami`'s Target org; raw HTTP with the bare UUID `orgId` (or none) is the fallback.

---

## Context Compaction Recovery

If context compacts mid-execution:
1. Read `docs/reference/contact-center-analytics.md` for API details
2. Verify CC auth with `wxcli whoami` and region — check `cc_region` in `~/.wxcli/config.json` (no getter command; set/reset via `wxcli set-cc-region`)
3. Resume from the appropriate recipe
