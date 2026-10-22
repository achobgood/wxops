## Schedule Callback Activity

<!-- ref-tag: fd-act-schedule-callback-v1 -->

Registers a callback request so the system calls the customer back at a later time, rather than keeping them waiting in queue.

> **Before you begin:** Ensure to configure the callback entry point in Control Hub. See the "Setup a callback entry point" section in Control Hub documentation.

### Configuration

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | Optional description |
| Callback Dial Number | 7–15 characters with country code. Digits 0–9, space, hyphen, parentheses, period allowed. |
| Callback Queue | Static queue (dropdown) or Variable queue (STRING variable) |
| Customer Name | Optional — name associated with the callback |
| Schedule Date | ISO-8601 format: YYYY-MM-DD. Must be within 31 days from the current date. |
| Schedule Start Time | ISO-8601 format: HH:mm:ss. Must be at least 30 minutes from the current time. |
| Schedule End Time | ISO-8601 format: HH:mm:ss. Must be at least 30 minutes after start time, maximum 8 hours after start. |
| Schedule Timezone | IANA time zone name (e.g., `America/New_York`) |

### Output Paths

| Output Path | Fires When |
|---|---|
| *(default exit)* | Callback request scheduled successfully. Wire to a Play Message (confirmation) then Disconnect Contact, or directly to Disconnect Contact. |
| **Undefined Error** | System error during callback scheduling (errors not covered by the predefined failure codes below). If no error-handling path is configured, the flow uses the global OnGlobalError event handler. |

> **Important:** It is recommended to add a Disconnect Contact activity immediately after the Schedule Callback activity to ensure the current call ends properly once the callback is scheduled.

### Output Variables

| Variable | Description |
|---|---|
| `ScheduleCallback.FailureCode` | Error code on failure |
| `ScheduleCallback.FailureDescription` | Error description on failure |

### Failure Codes

| Code | Description |
|---|---|
| 1 | INVALID_REQUEST — invalid inputs |
| 3 | INVALID_QUEUE — invalid queue details |
| 6 | SYSTEM_ERROR — miscellaneous errors |

### Restrictions

- **Callback entry point required:** Before using this activity, the Callback Default Entry Point must be configured in Control Hub at **Services > Contact Center > Customer experience > Channels > Settings**. This must be an outdial entry point dedicated to processing all scheduled callback calls in the organization.
- **Placement:** Schedule Callback does not require a prior Queue Contact activity (unlike the Callback activity). It can appear anywhere in the flow where you want to offer the customer a future callback.
- **Disconnect recommended:** Add a Disconnect Contact activity immediately after Schedule Callback to ensure the current call ends properly.
- **Capacity-based teams (CBT):** Courtesy callback is not supported with CBTs. CBTs have no individual agents assigned, and callback requires an Agent ID. If the callback flows to a queue served by a CBT, the call fails.
- **Queue type:** Can be scheduled using any telephony queue — inbound or outbound.
- **Self-loop limit:** 10 (see [self-loop-limits.md](self-loop-limits.md)).
- **Date constraints:** Must be within 31 days from the current date.
- **Time constraints:** Start time must be at least 30 minutes from the current time. The callback window must be between 30 minutes and 8 hours.
- **Feature enablement:** The preferred queue and callback features must be enabled for the enterprise.

### Relationship to Callback Activity and CallbackFailed Event

- **Callback** activity (separate from Schedule Callback) is used for immediate (courtesy) callbacks — the customer hangs up and receives a callback when an agent becomes available in the current session.
- **Schedule Callback** registers a future callback at a specified time.
- Both use the **CallbackFailed** event flow. If the callback call fails (e.g., answering machine detected, no answer), the `CallbackFailed` event fires with a `reason` output variable (e.g., `AMD` for answering machine detection).

---

