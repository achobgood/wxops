## Escalate Call Distribution Group Activity

<!-- ref-tag: fd-act-escalate-cdg-v1 -->

Escalates a queued contact to the next (or last) call distribution group within its current queue. Use it in queue treatment loops to progressively widen the agent pool when wait time exceeds a threshold.

### Configuration

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | Optional description |

No additional configuration is required — the activity operates on the contact's current queue and advances it to the next distribution group automatically.

### Output Variables

| Variable | Description |
|---|---|
| `EscalateGroup.CurrentGroup` | Current call distribution group after escalation |
| `EscalateGroup.TotalGroups` | Total number of distribution groups in the queue |
| `EscalateGroup.FailureCode` | Error code on failure |
| `EscalateGroup.FailureDescription` | Error description on failure |

### Failure Codes

| Code | Description |
|---|---|
| 1 | INVALID_REQUEST |
| 2 | CONTACT_NOT_QUEUED — the contact is not currently in a queue |
| 3 | FEATURE_NOT_ENABLED |

### Output Paths

**Single output path** with error handling. The activity has one output edge — check `FailureCode` to determine success (0) or error. You can configure an error-handling path (Undefined Error) to handle system errors during flow execution.

### Escalation Modes

The activity supports two escalation behaviors:

| Mode | Behavior |
|---|---|
| **Next Group** | Expands the set of eligible teams to include the ones added in the immediate next call distribution group |
| **Last Group** | Expands the set of eligible teams to include all teams mapped across all call distribution groups configured for the queue |

### Restrictions

- The contact **must already be queued** — using this activity on an unqueued contact results in failure code 2 (CONTACT_NOT_QUEUED).
- Not supported in queues that do not use call distribution groups (e.g., queues with skills-based team assignment instead of CDG-based team assignment).
- Updates the call distribution group immediately, instead of waiting for the automatic expansion timer to advance to the next group.
- Self-loop limit: 750.

> **Documentation pending** — event flow eligibility and behavior when the contact is already at the last CDG are not verified against Cisco help docs.

### Common Pattern

```
Queue Contact → Play Music (hold) → Wait (60s)
  → Get Queue Info (check wait time)
  → Condition: EWT > threshold?
    → TRUE: Escalate Call Distribution Group → loop back to Play Music
    → FALSE: continue holding
```

---

