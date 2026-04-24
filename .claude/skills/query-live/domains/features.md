# Features Domain

**Covers:** Hunt groups, call queues, auto attendants, paging groups, call park, call pickup, voicemail groups.

## Question Patterns

| Pattern | Example |
|---------|---------|
| Membership | "Who's in the Sales hunt group?", "List agents in the Support queue" |
| Inventory | "How many call queues are at Denver?", "What auto attendants do we have?" |
| Configuration | "What's the ring pattern for Support HG?", "Show overflow for Main CQ" |
| Schedule | "Which auto attendants use the Holiday schedule?" |
| Cross-feature | "Which features are at the Austin location?" |

## Command Recipes

### Hunt Groups

**List all (org-wide or per-location):**
```bash
wxcli hunt-group list -o json
wxcli hunt-group list --location-id LOCATION_ID -o json
wxcli hunt-group list --name "Sales" -o json
```

**Show detail (requires BOTH locationId AND huntGroupId):**
```bash
wxcli hunt-group show LOCATION_ID HUNT_GROUP_ID -o json
```
Response includes: `agents` (members list), `callPolicies` (ring pattern: SIMULTANEOUS, CIRCULAR, TOP_DOWN, WEIGHTED), `noAnswer` action and settings.

### Call Queues

**List:**
```bash
wxcli call-queue list -o json
wxcli call-queue list --location-id LOCATION_ID -o json
wxcli call-queue list --has-cx-essentials true -o json
```

**Show detail (requires BOTH locationId AND queueId):**
```bash
wxcli call-queue show LOCATION_ID QUEUE_ID -o json
```
Response includes: `agents`, `callPolicies` (routing type), `queueSettings` (overflow threshold, wait treatment), `overflowSettings`.

### Auto Attendants

**List:**
```bash
wxcli auto-attendant list -o json
wxcli auto-attendant list --location-id LOCATION_ID -o json
wxcli auto-attendant list --name "Main" -o json
```

**Show detail (requires BOTH locationId AND autoAttendantId):**
```bash
wxcli auto-attendant show LOCATION_ID AA_ID -o json
```
Response includes: `businessHoursSchedule`, `holidaySchedule`, `businessHours` (menu config), `afterHours` (menu config), `extension`, `phoneNumber`.

### Paging Groups

**List:**
```bash
wxcli paging-group list -o json
wxcli paging-group list --location-id LOCATION_ID -o json
```

**Show detail (requires BOTH locationId AND pagingGroupId):**
```bash
wxcli paging-group show LOCATION_ID PAGING_GROUP_ID -o json
```

### Call Park (location-scoped list)

**List (locationId is REQUIRED positional arg):**
```bash
wxcli call-park list LOCATION_ID -o json
```

**Show detail:**
```bash
wxcli call-park show LOCATION_ID CALL_PARK_ID -o json
```

### Call Pickup (location-scoped list)

**List (locationId is REQUIRED positional arg):**
```bash
wxcli call-pickup list LOCATION_ID -o json
```

**Show detail:**
```bash
wxcli call-pickup show LOCATION_ID CALL_PICKUP_ID -o json
```

## Resolution Rules

**Finding a feature by name:**
1. List the feature type: e.g., `wxcli hunt-group list --name "Sales" -o json`
2. If the `--name` filter doesn't match, list all and search the JSON response
3. When showing detail, you MUST have both the `locationId` AND the feature's `id`
4. The list response includes both — extract them from the matching item

**Finding all features at a location:**
1. Resolve location name → ID
2. Run each feature list with `--location-id`:
   ```bash
   wxcli hunt-group list --location-id LOC_ID -o json
   wxcli call-queue list --location-id LOC_ID -o json
   wxcli auto-attendant list --location-id LOC_ID -o json
   wxcli paging-group list --location-id LOC_ID -o json
   wxcli call-park list LOC_ID -o json
   wxcli call-pickup list LOC_ID -o json
   ```
3. Note: call-park and call-pickup take locationId as positional arg, others as --location-id flag

## Response Guidance

**Membership query** ("Who's in the Sales hunt group?"):
```
Sales Hunt Group has 4 members:
  - Jane Smith (ext 2001, Austin)
  - Bob Lee (ext 2002, Austin)
  - Maria Garcia (ext 2003, Denver)
  - Tom Chen (ext 2004, Denver)

Ring pattern: Simultaneous
No-answer action: Forward to Sales voicemail after 20 seconds
```

**Inventory query** ("How many call queues at Denver?"):
```
Denver has 3 call queues:
  - Support Queue (ext 5001, 8 agents)
  - Sales Queue (ext 5002, 4 agents)
  - Billing Queue (ext 5003, 3 agents)
```

**Configuration query** ("Show overflow for Main CQ"):
```
Main Call Queue overflow settings:
  - Overflow after: 120 seconds in queue
  - Overflow action: Transfer to Main Voicemail Group
  - Max callers in queue: 25
  - When queue is full: Play busy treatment
```

**Cross-feature inventory** ("What features are at Austin?"):
```
Austin has 12 call features:
  - 3 auto attendants: Main Menu, Sales AA, Support AA
  - 4 call queues: Sales, Support, Billing, General
  - 2 hunt groups: Front Desk, Dispatch
  - 1 paging group: Warehouse PA
  - 1 call park: Lobby Park
  - 1 call pickup: Front Desk Pickup
```

## Gotchas

1. **CX Essentials queues are hidden by default.** `wxcli call-queue list` does NOT show CX queues unless you pass `--has-cx-essentials true`. If a user asks about a queue you can't find, try: `wxcli call-queue list --has-cx-essentials true -o json`.
2. **Call park and call pickup have no org-wide list.** You must enumerate per-location. If the user asks "show all call parks" without specifying a location, list locations first, then query each.
3. **Feature show commands need TWO positional args.** `wxcli hunt-group show LOCATION_ID HG_ID` — not just the feature ID. Both IDs are in the list response.
4. **Voicemail groups are not yet in wxcli.** If asked about voicemail groups, note they can be managed in Control Hub under Calling → Features → Voicemail Groups.
5. **Hunt groups ignore member personal call forwarding.** HG calls route directly to the agent's device and bypass any personal call forwarding the member has configured. Only the hunt group's own no-answer/forwarding settings (feature-level) govern what happens when a member doesn't answer.
6. **DND on a hunt group member skips them, not their voicemail.** If a member has DND enabled, the hunt group skips that member and moves to the next — it does NOT send the call to the member's personal voicemail. The HG's no-answer action only triggers after all members are exhausted.
