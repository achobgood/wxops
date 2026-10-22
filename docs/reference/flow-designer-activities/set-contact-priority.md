## Set Contact Priority Activity

<!-- ref-tag: fd-act-set-contact-priority-v1 -->

Assigns a priority level to a contact, controlling its position in the queue. Higher-priority contacts are served before lower-priority ones regardless of arrival time.

### Configuration

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | Optional description |
| Static Priority | Select a fixed priority P1–P9 from the dropdown (P1 = highest) |
| Variable Priority | Select an INTEGER flow variable (1–9). Values outside 1–9 default to priority 10 (lowest). |

### Output Variables

| Variable | Description |
|---|---|
| `SetContactPriority.FailureCode` | Error code on failure |
| `SetContactPriority.FailureDescription` | Error description on failure |

### Failure Codes

| Code | Description |
|---|---|
| 6 | SYSTEM_ERROR |
| 48 | Unsupported flow activity — Set Contact Priority is not supported for outdial and campaign contacts |

### Output Paths

Default success exit, plus a **Failure** output path (registry `failure` port, `isErrorPath: true`). On failure the flow takes the Failure edge and populates the `FailureCode`/`FailureDescription` output variables. (Live registry: wxcc-flow describe set-contact-priority (today `wxcli cc-flow show-activity PROJECT_ID set-contact-priority`) → `outputPorts` includes a `failure` port, verified 2026-07-12.)

### Restrictions

- Cannot be used with outdial or campaign contacts (failure code 48).
- Place before Queue Contact to set initial priority, or use in a queue treatment loop to dynamically adjust priority based on wait time or caller segment.

---

