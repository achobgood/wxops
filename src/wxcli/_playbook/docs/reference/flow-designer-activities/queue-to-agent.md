## Queue To Agent Activity

<!-- ref-tag: fd-act-queue-to-agent-v1 -->

Routes a contact directly to a specific agent by ID or email, bypassing the normal queue distribution. Use for preferred-agent routing, last-agent routing, or VIP handling.

### Configuration

**General Settings:**

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | Optional description |

**Contact Handling:**

| Field | Description |
|---|---|
| Agent Variable | Flow variable containing the agent identifier |
| Agent Lookup Type | **Email** or **ID** — how to interpret the Agent Variable value |
| Set Contact Priority | Toggle (default: disabled). Static P1–P9 or variable INTEGER 1–9. |
| Reporting Queue | Queue used for contact reporting details. Also specifies configuration for: Permit monitoring, Permit recording, Record all calls, Pause and resume enabled, Service level threshold, Maximum time in queue, Default music in queue, Time zone. Select from dropdown. |
| Park Contact if Agent is unavailable | Toggle (default: disabled). When enabled, parks the contact and waits for the agent instead of failing immediately. |
| Recovery Queue | Fallback queue if the agent rejects or is unavailable and parking is disabled |

### Output Variables

| Variable | Description |
|---|---|
| `QueueToAgent.AgentId` | Target agent identifier |
| `QueueToAgent.FailureCode` | Error code on failure |
| `QueueToAgent.FailureDescription` | Error description on failure |
| `QueueToAgent.AgentState` | Agent's current state (AVAILABLE, Idle, NOT_APPLICABLE) |
| `QueueToAgent.AgentIdleCode` | Agent's idle/aux code |

**AgentState and AgentIdleCode Values:**

| Use Case | AgentState | AgentIdleCode |
|---|---|---|
| Invalid queue, invalid agent, or agent is not signed in | NOT_APPLICABLE | NOT_APPLICABLE |
| Agent is reserved for this call | AVAILABLE | NOT_APPLICABLE |
| Park Contact toggle is **On** and the agent is idle | Idle | `<AuxCode Name>` (the idle code selected by the agent in Agent Desktop) |
| Park Contact toggle is **On** and the agent channel is busy | AVAILABLE | NOT_APPLICABLE |
| Park Contact toggle is **Off** and the agent is idle | Idle | `<AuxCode Name>` (the idle code selected by the agent in Agent Desktop) |
| Park Contact toggle is **Off**, agent is available, and agent channel is busy | AVAILABLE | NOT_APPLICABLE |

### Output Paths

| Output Path | Fires When |
|---|---|
| *(default exit)* | Agent is available and reserved for the contact, or the contact is successfully parked (Park Contact ON) or routed to the Recovery Queue. Wire to Play Music (hold treatment) or downstream logic. |
| **Undefined Error** | System error during flow execution (errors not covered by the predefined failure codes below). If no error-handling path is configured, the flow uses the global `OnGlobalError` event handler. |

**Park Contact OFF — agent unavailable:** The activity exits via the default path with a failure code set in `QueueToAgent.FailureCode` (e.g., `1` = AGENT_UNAVAILABLE). If a Recovery Queue is configured, the contact is routed to that queue using Longest Available Agent routing. If no Recovery Queue is configured, use a Condition activity after Queue To Agent to branch on the failure code.

**Park Contact ON — agent unavailable:** The contact parks and waits for the agent. The flow continues executing downstream activities (Play Music, Callback, etc.). When the agent becomes available, routing proceeds automatically.

**Recovery Queue behavior:** The Recovery Queue is not a separate output edge — it is a configuration parameter. When the preferred agent rejects, does not answer, or is unavailable (with Park Contact OFF), the contact is routed to the Recovery Queue automatically. The Recovery Queue does not support skills-based routing; it uses Longest Available Agent routing only.

### Event Triggers

The Queue To Agent activity triggers the following events in the **Event Flows** tab:

- **AgentAccepted** — fires when an agent accepts the queued contact
- **AgentDisconnected** — fires when the agent disconnects from a live call

### Failure Codes

| Code | Description |
|---|---|
| 1 | AGENT_UNAVAILABLE |
| 2 | AGENT_NOT_FOUND |
| 3 | AGENT_NOT_LOGGED_IN |
| 4 | FEATURE_NOT_ENABLED |
| 5 | INVALID_VTEAM_ERROR |
| 6 | AGENT_BUSY |
| 7 | VTEAM_TRANSITION_LIMIT_REACHED |
| 8 | INVALID_OPERATION_FOR_INTERACTION_STATE |

### Restrictions

- **Agent-based Routing feature:** Must be enabled for the enterprise. If not enabled, `FailureCode` = 4 (FEATURE_NOT_ENABLED).
- **Placement:** Can be chained with another Queue To Agent activity, a Queue Contact activity, or a Callback activity in both Main flows and Event flows.
- **Cannot use when agent already assigned:** If an agent is already assigned to the contact, the activity fails with `FailureCode` = 8 (INVALID_OPERATION_FOR_INTERACTION_STATE).
- **Invalid agent:** If the agent ID or email is invalid or the agent does not exist, `FailureCode` = 2 (AGENT_NOT_FOUND).
- **Recovery Queue:** Does not support skills-based routing — uses Longest Available Agent only.
- **Self-loop limit:** 100 (see [self-loop-limits.md](self-loop-limits.md)).

---

