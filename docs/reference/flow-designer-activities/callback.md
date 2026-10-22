## Callback Activity

<!-- ref-tag: fd-act-callback-v1 -->

Registers an immediate (courtesy) callback — the caller hangs up and the system calls them back when an agent becomes available. Unlike Schedule Callback (which registers a future callback), Callback keeps the contact's position in queue and calls back as soon as an agent is free.

> **Note:** A Consult interaction cannot include a Courtesy Callback activity.

If a new queue is preferred, the task is placed at the bottom of the preferred queue. As an agent accepts the task, the Callback is initiated. If the caller does not answer, the Callback is not retried.

> **Important:** You must use a Disconnect Contact activity to terminate a flow branch that uses a Callback activity. Otherwise, the call does not end when a Callback request is placed.

### Configuration

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | Optional description |
| Callback Dial Number | Flow variable containing the callback number. Defaults to `{{NewContact.ANI}}`. |
| Register callback to different destination? | Toggle (default: off). When enabled, allows routing the callback to a different queue. |
| Callback Queue | **Static Queue** (select from dropdown) or **Variable Queue** (STRING variable). Defaults to the queue from the Queue Contact activity. |
| Callback ANI | Optional. **Static ANI** (select from dropdown) or **Variable ANI** (STRING variable, must be 10-digit number with country code). |

**Customized ANI Validation:**

If the ANI provided is incorrect, the callback switches to the default system ANI (DNIS).

| Description | Tenant Management ANI | PreDial/Courtesy Callback ANI (Flow Control) | Validation |
|---|---|---|---|
| ANI without country code | Without country code (e.g., 2567312213) | Without country code (e.g., 2567312213) | Valid ANI. Same ANI is used. |
| Tenant with country code, Flow Control without | With country code (e.g., +1-2567312213) | Without country code (e.g., 2567312213) | Invalid ANI. DNIS is used. |
| Tenant without country code, Flow Control with | Without country code (e.g., 2567312213) | With country code (e.g., +1-2567312213) | Invalid ANI. DNIS is used. |
| Both with country code | With country code (e.g., +1-2567312213) | With country code (e.g., +1-2567312213) | Valid ANI. Same ANI is used. |
| Tenant no spaces, Flow Control with spaces | No space (e.g., +1-2567312213) | Space in number (e.g., +1-256 7312213) | Valid ANI. Same ANI is used. |
| Tenant no hyphens, Flow Control with hyphens | No extra hyphens (e.g., +1-2567312213) | Hyphens in number (e.g., +1-256-731-2213) | Valid ANI. Same ANI is used. |
| Flow Control matches only last few digits | Complete ANI (e.g., +1-2567312213) | Last four digits only (e.g., 2213) | Invalid ANI. DNIS is used. |
| Flow Control has more digits than Tenant | Partial ANI (e.g., 2213) | 10-digit ANI (e.g., 2567312213) | Invalid ANI. DNIS is used. |
| Tenant configured, Flow Control not configured | Complete ANI (e.g., +1-2567312213) | ANI is not configured | Invalid ANI. DNIS is used. |
| Flow Control ANI missing plus symbol | Plus symbol used (e.g., +1-2567312213) | Plus symbol not used (e.g., 12567312213) | Invalid ANI. DNIS is used. |

### Output Paths

| Output Path | Fires When |
|---|---|
| *(default exit)* | Callback request registered successfully. Wire to a Play Message (confirmation) then Disconnect Contact, or directly to Disconnect Contact. If an agent is found during callback registration or the Play Message period, the customer is immediately connected to the agent. |
| **Undefined Error** | System error during callback registration (errors not covered by the predefined failure codes below) |

> **Important:** You must use a Disconnect Contact activity to terminate the flow branch after Callback. Otherwise the call does not end when a Callback request is placed.

### Output Variables

| Variable | Description |
|---|---|
| `Callback.FailureCode` | Error code on failure |
| `Callback.FailureDescription` | Error description on failure |

### Failure Codes

| Code | Description |
|---|---|
| 1 | INVALID_REQUEST — invalid request made in the activity |
| 2 | CALLBACK_NOT_SUPPORTED_ON_CHILD_INTERACTION — callback not allowed on a child contact |
| 3 | INVALID_QUEUE — invalid queue specified |
| 4 | INVALID_DESTINATION — destination number for callback is invalid |
| 5 | FEATURE_NOT_ENABLED — feature not enabled in Webex Contact Center |
| 6 | SYSTEM_ERROR — system encountered an internal error |

### CallbackFailed Event Flow

If the callback call fails (no answer, answering machine, busy), the **CallbackFailed** global event flow fires. The event exposes a `reason` output variable:

| Reason | Description |
|---|---|
| `AMD` | Answering machine or voicemail detected on the callback attempt |

> **Documentation pending** — Cisco documentation only enumerates `AMD` as a named `reason` value. Other failure scenarios (no answer, busy, network error, etc.) may produce additional reason values, but these are not enumerated in the Cisco help docs. Do not invent values; branch on `AMD` explicitly and treat all other values as a generic failure path.

Wire the CallbackFailed event flow to handle retries or record the failed callback.

### Retry Configuration

When handling the CallbackFailed event flow, you can configure retry logic using the Wait activity:

| Parameter | Value |
|---|---|
| Minimum retry interval | 10 seconds |
| Maximum retry interval | 72 hours |
| Maximum retry attempts | 10 (across a maximum span of 14 days) |

Wire the CallbackFailed event flow to a Wait activity, then loop back to a new Callback attempt, using a counter variable to track the number of retries.

### Restrictions

- **Placement:** Must be placed after a Queue Contact or Queue To Agent activity. Cannot be used before queueing.
- **Consult interactions:** A Consult interaction cannot include a Courtesy Callback activity.
- **Capacity-based teams (CBT):** Courtesy callback is not supported with CBTs. CBTs have no individual agents assigned to them, and courtesy callback requires an Agent ID to function. If the callback flows to an entry point or a queue served by a CBT, the call fails.
- **Disconnect required:** You must wire a Disconnect Contact activity after Callback to terminate the flow branch. Otherwise the call does not end when the callback request is placed.
- **Self-loop limit:** 10 (see [self-loop-limits.md](self-loop-limits.md)).

### Callback vs. Schedule Callback

| Aspect | Callback | Schedule Callback |
|---|---|---|
| Timing | Immediate — calls back when agent is available | Future — calls back at a scheduled time |
| Queue position | Preserves the contact's queue position | Registers a new contact in the queue |
| Use case | "We'll call you back shortly" during high volume | "We'll call you back at 3 PM" |

---

