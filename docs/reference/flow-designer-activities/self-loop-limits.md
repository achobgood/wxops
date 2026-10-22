## Self-Loop Limits

<!-- ref-tag: fd-act-self-loop-limits-v1 -->

Flow Designer enforces **system-level self-loop limits** on activities to prevent infinite loops. When an activity's output edge routes back to itself (directly or through a short chain), the system counts each iteration. Once the limit is reached, the flow takes the error path.

### Complete Limits Table

| Activity | Self-Loop Limit |
|---|---|
| Advanced Queue Information | 1500 |
| Blind Transfer | 10 |
| Bridged Transfer | 75 |
| Callback | 10 |
| Call Progress Analysis | 10 |
| Collect Digits | 100 |
| Disconnect Contact | 0 |
| Escalate Call Distribution Group | 750 |
| Feedback V2 | 10 |
| Menu | 100 |
| Queue Contact | 100 |
| Queue To Agent | 100 |
| Record | 10 |
| Recording Control | 10 |
| Schedule Callback | 10 |
| Set Caller ID | 100 |
| Set Contact Priority | 100 |
| Start Media Stream | 20 |
| Upload Audio | 3 |
| Virtual Agent | 20 |
| Virtual Agent V2 | 20 |

> **Flow-control activities:** Flow-control activities (Case, Condition, GoTo, Percent Allocation, Wait, End Flow) are subject to system-configured surge limits to ensure stability and prevent infinite looping. These surge limits are separate from the per-activity self-loop limits listed above. The specific numeric surge limit values for these activities are not published in Cisco's public documentation — they are managed internally by the platform.

> **Activities not listed above:** Activities not listed in the table above (e.g., Set Variable, Play Message, Play Music, Parse, HTTP Request, Business Hours, Screen Pop, Functions, Condition, Case, GoTo, Percent Allocation, Wait, End Flow, Set Announcement, Set Whisper, Send Digits) do not have per-activity self-loop limits documented in Cisco's public references. Flow-control activities are covered by surge limits (see note above). Other activities either have no self-loop limit or their limits are not published.

### Design Guidance

- **Always include an exit condition** when looping an activity back to itself. For example, track a `retryCount` variable and break out after N attempts.
- **Use the OnGlobalError event** as a safety net — if a loop exceeds its limit, the flow errors and OnGlobalError fires.
- **Avoid tight Wait loops.** A Wait activity looping to itself for polling will hit the limit. Use a finite retry pattern with a counter instead.

---

