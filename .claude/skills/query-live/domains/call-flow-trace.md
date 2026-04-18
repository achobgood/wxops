# Call Flow Trace Domain

**Covers:** "What happens when someone calls +1-512-555-1000?", call path tracing, schedule evaluation, routing chain visualization.

This is the most complex domain module. It traces the path a call takes through the routing chain, evaluating time-of-day schedules to show the specific path at a given moment.

## Question Patterns

| Pattern | Example |
|---------|---------|
| Simple trace | "What happens when someone calls +1-512-555-1000?" |
| Time-specific | "What happens if someone calls the main number at 7pm Saturday?" |
| Schedule check | "Is the Main auto attendant on business hours or after hours right now?" |
| Path comparison | "What's the difference between calling during business hours vs after hours?" |
| Resource trace | "Trace the call flow for the Sales hunt group" |

## Input Parsing

The user provides:
1. **A phone number** (e.g., "+1-512-555-1000") OR **a resource name** (e.g., "the Main auto attendant", "the Sales hunt group")
2. **An optional datetime** — if omitted, use current time in the resource's location timezone

**Natural language time expressions to support:**
- "right now" → current time
- "at 3am" → today at 3:00 AM in location timezone
- "at 7pm on Saturday" → next Saturday at 7:00 PM
- "on Christmas Day" → December 25 (use current year if ambiguous)
- "next Tuesday at noon" → next Tuesday at 12:00 PM

## Algorithm

### Step 1 — Resolve the entry point

**If user gave a phone number:**
```bash
wxcli numbers list --phone-number "+15125551000" -o json
```
Extract the `owner` object → get `type` and `id`. The `owner.type` tells you what the number is assigned to: PEOPLE, AUTO_ATTENDANT, CALL_QUEUE, HUNT_GROUP, VIRTUAL_LINE, PLACE (workspace), or BROADWORKS_ANYWHERE.

Also get the `location` from the number response — you'll need the location ID and timezone.

**If user gave a resource name:**
Search for the resource by name in the appropriate list command:
- "Main auto attendant" → `wxcli auto-attendant list --name "Main" -o json`
- "Sales hunt group" → `wxcli hunt-group list --name "Sales" -o json`
- "Support queue" → `wxcli call-queue list --name "Support" -o json`
- Person name → `wxcli people list --display-name "Jane Smith" -o json`

Extract the resource's `id` and `locationId` from the list response.

### Step 2 — Get the location timezone

```bash
wxcli locations show LOCATION_ID -o json
```
Extract `timeZone` (e.g., "America/Chicago"). Use this to evaluate schedules against the queried datetime.

### Step 3 — Walk the chain

Based on the entry point type, follow the appropriate path. **Maximum depth: 5 hops.** Track visited resources to detect loops.

#### Auto Attendant path

1. **Get AA detail:**
```bash
wxcli auto-attendant show LOCATION_ID AA_ID -o json
```

2. **Get the AA's schedule(s):**
The AA response includes `businessHoursSchedule` and/or `holidaySchedule` references (with schedule `name` and `id`).

For each schedule reference:
```bash
wxcli location-schedules show LOCATION_ID TYPE SCHEDULE_ID -o json
```
Where TYPE is `businessHours` or `holidays`.

3. **Evaluate which schedule is active at the queried time:**

**Precedence:**
1. Check holiday schedule first — if the queried date matches a holiday entry, use the `holidaySchedule` action
2. Check business hours schedule — if the queried time falls within the defined business hours for that day of week, use the `businessHours` menu
3. Otherwise — use the `afterHours` menu

**Business hours evaluation:**
The schedule response includes per-day entries. Each day has `startTime` and `endTime` (24-hour format). Check if the queried time (converted to location timezone) falls within the range for the queried day of week.

Example schedule data:
```json
{
  "type": "businessHours",
  "events": [
    {"name": "Monday", "startTime": "08:00", "endTime": "17:00"},
    {"name": "Tuesday", "startTime": "08:00", "endTime": "17:00"},
    ...
  ]
}
```

If the day is Saturday/Sunday and no entry exists → after hours.

**Holiday evaluation:**
Check the holiday schedule's `events` for a date match. Holiday events may have `startDate`/`endDate` or specific dates with optional yearly recurrence.

4. **Report the active menu:**
Show the greeting message (if available) and the menu options. Each option maps a key press to a destination (transfer to another AA, HG, CQ, person, voicemail, etc.).

5. **Recurse:** For each destination that is another AA, CQ, or HG → follow that chain (increment hop count).

#### Hunt Group path

1. **Get HG detail:**
```bash
wxcli hunt-group show LOCATION_ID HG_ID -o json
```

2. **Report:**
```
→ Sales Hunt Group
  Ring pattern: [SIMULTANEOUS|CIRCULAR|TOP_DOWN|WEIGHTED]
  Members ([N]):
    - Jane Smith (ext 2001)
    - Bob Lee (ext 2002)
  No-answer: After [timeout]s → [action/destination]
```

3. **If no-answer destination is another feature** (AA, CQ, voicemail group) → recurse.

#### Call Queue path

1. **Get CQ detail:**
```bash
wxcli call-queue show LOCATION_ID CQ_ID -o json
```

2. **Report:**
```
→ Support Call Queue
  Routing: [Longest Idle|Circular|Top Down|Weighted|Simultaneous]
  Agents ([N]):
    - Agent 1 (ext XXXX)
    - Agent 2 (ext XXXX)
  Overflow: After [threshold]s/[max callers] → [destination]
```

3. **If overflow destination is another feature** → recurse.

#### Person path

1. **End of chain.** Report:
```
→ Jane Smith (ext 2001, Austin)
```

2. **Optionally check call forwarding:**
```bash
wxcli user-settings show-call-forwarding PERSON_ID -o json
```
If `noAnswer.enabled` is true, note:
```
  If no answer after [rings] rings → forwards to [destination]
```

#### Workspace path

End of chain:
```
→ Conference Room A (workspace, Austin)
```

### Step 4 — Format the output

Use the numbered-hop format:

```
Call to +1-512-555-1000 at 7:00 PM Saturday (CST):

1. → Main Auto Attendant (after-hours schedule active)
   Greeting: "Thank you for calling Acme Corp. Our offices are closed."
   Menu: Press 1 for Sales, Press 2 for Support, Press 0 for Operator

2. [Press 1] → Sales Call Queue
   Routing: Longest idle agent
   Agents: Jane Smith (ext 2001), Bob Lee (ext 2002), Maria Garcia (ext 2003)
   Overflow: After 120 seconds → Sales Voicemail Group

3. [Overflow] → Sales Voicemail Group
   Members: Jane Smith, Bob Lee
```

**For time-comparison queries** ("business hours vs after hours"), trace both paths and present side by side:

```
Call to +1-512-555-1000:

BUSINESS HOURS (Mon-Fri 8am-5pm CST):
1. → Main Auto Attendant (business hours)
   Menu: Press 1 for Sales, Press 2 for Support, Press 0 for Operator
2. [Press 1] → Sales Hunt Group (4 members, simultaneous ring)

AFTER HOURS (evenings, weekends):
1. → Main Auto Attendant (after hours)
   Greeting: "Our offices are closed."
   Menu: Press 1 for urgent Sales, Press 0 for general voicemail
2. [Press 1] → Sales On-Call (1 member)
```

## Constraints

1. **Depth limit: 5 hops.** If the chain goes deeper, report what's been traced and note: "Call flow continues beyond 5 hops — check Control Hub for the full chain."
2. **No live agent state.** The tracer shows the *configured* path, not real-time availability. Note: "This shows the configured routing — actual behavior depends on agent availability at the time of the call."
3. **Missing schedule.** If an AA has no schedule assigned, report: "No schedule configured — default behavior applies (business hours menu active at all times)."
4. **Missing menu data.** AA menus may not be fully available via API. Report what's available; note gaps.
5. **Inbound only (v1).** This traces inbound call paths. For outbound routing through dial plans/trunks, suggest: "For outbound routing, try: 'What dial plan handles calls to +44...?' (uses the routing domain)."
6. **Loop detection.** Track visited resource IDs. If a chain references a resource already visited, report: "Loop detected — [resource] routes back to [earlier resource]." Stop recursion.

## Gotchas

1. **Schedule show needs THREE positional args.** `wxcli location-schedules show LOCATION_ID TYPE SCHEDULE_ID` — not just the schedule ID. The TYPE must be `businessHours` or `holidays`.
2. **Schedule list is location-scoped.** `wxcli location-schedules list LOCATION_ID -o json` — locationId is a required positional arg.
3. **AA menu key mappings.** The AA show response includes `businessHours` and `afterHours` objects with `actions` arrays. Each action has a `key` (0-9, #, *) and a `value` (transfer destination).
4. **Timezone handling.** Always convert the queried time to the location's timezone before evaluating schedules. A query at "7pm" from a user in EST targeting an AA in CST should evaluate at 6pm CST.
5. **Holiday recurrence.** Some holidays recur annually (Christmas, New Year's). Check the `recurrence` field in holiday events. If `recurAnnually: true`, match the month/day regardless of year.
