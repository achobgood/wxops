## End Flow Activity

<!-- ref-tag: fd-act-end-flow-v1 -->

Terminates flow execution without disconnecting the call. Use in event flows (AgentAccepted, PhoneContactEnded, etc.) where the flow logic is complete but the call itself should continue.

### Configuration

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | (Optional) Description for the activity |

> **Warning:** Don't use the End Flow activity in an IVR flow. End Flow use with IVR may result in dead air and the call may not disconnect.

You can use any number of End Flow activities to construct your flow to ensure that all flow paths terminate.

### Output Variables

None. End Flow is a terminal activity with no downstream processing.

### Output Paths

N/A — terminal node. No exit edges.

### End Flow vs. Disconnect Contact

| Activity | Terminates Flow? | Terminates Call? | Use In |
|---|---|---|---|
| **End Flow** | Yes | No | Event flows, subflows |
| **Disconnect Contact** | Yes | Yes | Main flow exit paths |

---

