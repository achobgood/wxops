## Get Queue Info Activity

<!-- ref-tag: fd-act-get-queue-info-v1 -->

Retrieves real-time queue metrics including estimated wait time (EWT) and position in queue (PIQ). Use it to inform callers of wait times or to make routing decisions based on queue load.

### Configuration

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | Optional description |
| Queue Information | **Static Queue** (select from dropdown) or **Variable Queue** (STRING flow variable resolving to queue ID) |
| Lookback Time | Time window for EWT calculation, in minutes. Range: **5–240 minutes**. |

### EWT Calculation

The system samples recent call data within the Lookback Time window. Samples must be statistically valid (coefficient of variance < 40%). At least 40% of samples must be valid for EWT computation. If insufficient data exists, EWT returns –1.

> **Note:** Expected Wait Time (EWT) does not apply to queues with team assignment with skills assigned in flow. For contacts in these queues, the EWT output variable always returns -1.

### Output Variables

| Variable | Description |
|---|---|
| `GetQueueInfo.PositionInQueue` | Caller's position in queue (PIQ) |
| `GetQueueInfo.EstimatedWaitTime` | Estimated wait time in **milliseconds**. Returns –1 if insufficient data. |
| `GetQueueInfo.LoggedOnAgentsCurrent` | Logged-on agents in current call distribution group. If the activity is used before queueing, stats for agents in the current Call Distribution Group cycle will be returned based on the first Call Distribution Group cycle. |
| `GetQueueInfo.LoggedOnAgentsAll` | Logged-on agents across all distribution groups |
| `GetQueueInfo.AvailableAgentsCurrent` | Available agents in current distribution group. If the activity is used before queueing, stats for agents in the current Call Distribution Group cycle will be returned based on the first Call Distribution Group cycle. |
| `GetQueueInfo.AvailableAgentsAll` | Available agents across all distribution groups |
| `GetQueueInfo.CallsQueuedNow` | Current number of calls in queue |
| `GetQueueInfo.OldestCallTime` | Duration of the oldest call in queue (in seconds) |
| `GetQueueInfo.FailureCode` | Error code on failure |
| `GetQueueInfo.FailureDescription` | Error description on failure |

### Output Paths

| Output Path | Fires When |
|---|---|
| **Success** | Valid PIQ and positive EWT returned |
| **Insufficient Information** | Valid PIQ but EWT = –1 (not enough data for estimation) |
| **Failure** | API failure or invalid queue |

### Failure Codes

| Code | Description |
|---|---|
| 1 | SYSTEM_ERROR |
| 2 | STALE_DATA |
| 3 | INSUFFICIENT_DATA |
| 4 | INVALID_QUEUE |

### Restrictions

- **Placement:** Can be used both **before** and **after** Queue Contact. When used before queueing, `LoggedOnAgentsCurrent` and `AvailableAgentsCurrent` return stats based on the first Call Distribution Group cycle.
- **Skills-based queues (EWT caveat):** EWT does not apply to queues with team assignment where skills are assigned in the flow. For contacts in these queues, `GetQueueInfo.EstimatedWaitTime` always returns –1. The Insufficient Information output path fires in this case, not the Failure path.
- **Self-loop limit:** Get Queue Info does not appear in the Cisco-documented self-loop limits table. It is not listed alongside activities like Callback (10), Queue Contact (100), or Advanced Queue Information (1500).

> **Documentation pending** — event flow eligibility for Get Queue Info is not verified against Cisco help docs. The Cisco documentation does not explicitly state whether this activity can or cannot be used in event flows.

---

