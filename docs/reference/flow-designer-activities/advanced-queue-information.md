## Advanced Queue Information Activity

<!-- ref-tag: fd-act-advanced-queue-information-v1 -->

Returns real-time agent counts and queue position without the lookback-based EWT calculation. Use when you need current agent availability data rather than wait time estimates.

### Configuration

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | Optional description |
| Queue | Select from dropdown |

### Difference from Get Queue Info

| Aspect | Get Queue Info | Advanced Queue Information |
|---|---|---|
| EWT (Estimated Wait Time) | Yes — uses lookback window | No |
| PIQ (Position in Queue) | Yes | Yes |
| Lookback Time parameter | Yes (5–240 min) | No |
| Real-time agent counts | Yes | Yes |
| Call distribution group tracking | No | Yes (CurrentGroup, TotalGroups) |

### Output Variables

| Variable | Description |
|---|---|
| `AdvancedQueueInformation.PositionInQueue` | Caller's position in queue |
| `AdvancedQueueInformation.LoggedOnAgentsCurrent` | Logged-on agents in current distribution group |
| `AdvancedQueueInformation.LoggedOnAgentsAll` | Logged-on agents across all distribution groups |
| `AdvancedQueueInformation.AvailableAgentsCurrent` | Available agents in current distribution group |
| `AdvancedQueueInformation.AvailableAgentsAll` | Available agents across all distribution groups |
| `AdvancedQueueInformation.CurrentGroup` | Current call distribution group |
| `AdvancedQueueInformation.TotalGroups` | Total number of call distribution groups in the queue |
| `AdvancedQueueInformation.FailureCode` | Error code on failure |
| `AdvancedQueueInformation.FailureDescription` | Error description on failure |

### Output Paths

**Single output path** with error handling. Unlike Get Queue Info (which has Success / Insufficient Information / Failure edges), Advanced Queue Information has one output edge. Check `FailureCode` to determine success (0) or error. You can configure an error-handling path (Undefined Error) to handle system errors during flow execution.

### Failure Codes

| Code | Description |
|---|---|
| 1 | INVALID_REQUEST |
| 2 | QUEUE_NOT_FOUND |
| 3 | FEATURE_NOT_ENABLED |
| 4 | DATABASE_OPERATION_FAILURE |
| 5 | INVALID_QUEUE |
| 48 | UNSUPPORTED_FLOW_ACTIVITY |

### Restrictions

- Not supported for queues with skills criteria assigned to the queue.
- Not supported when the contact is already queued but in a different queue than the one where the information is requested.
- Not supported when the contact is queued directly against a preferred agent.
- Can be used **before** the contact is queued — in that case, `PositionInQueue` returns the number of contacts currently waiting in the queue + 1.
- Self-loop limit: 1500.

> **Documentation pending** — event flow eligibility is not verified against Cisco help docs.

---

