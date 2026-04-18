---
name: query-live
description: |
  Answer natural-language questions about a Webex Calling environment using live API data.
  Read-only queries against people, call features, routing, numbers, call history, and call flow tracing.
  Use when the user asks "who", "what", "which", "how many", "does", "is", "show me", or "check" questions
  about their current Webex Calling configuration. Invoked by the wxc-calling-builder agent on query intent,
  or directly via /query-live.
allowed-tools: Read, Grep, Glob, Bash, Skill
argument-hint: [question]
---

# Query Live State

Answer plain-English questions about a Webex Calling environment using live API data. **Read-only only.**

## Checkpoint — verify before proceeding

1. Has `wxcli whoami` succeeded in this session? If not, run it now. Do not proceed without a valid token.
2. Do you know which domain(s) this question touches? (people, features, routing, numbers, call-history, call-flow). If unsure, read the Domain Routing table below.

## Step 1: Classify the question

**Query signals** — this skill handles these:
- Interrogative form: "Who...?", "What...?", "Which...?", "How many...?", "Does...?", "Is...?"
- Inspection verbs: "show me", "list", "check", "look up", "find", "tell me about"
- State references: "current", "right now", "configured", "enabled", "assigned"
- Comparison/audit: "which users don't have...", "compare", "differences between"

**Not a query** — hand back to the builder's normal workflow:
- Action verbs: "create", "set up", "enable", "add", "configure", "change", "move", "delete"
- Future intent: "I want to...", "we need to...", "can you make..."

**Edge case:** "Can you check if voicemail is enabled and turn it on if not?"
→ Classify as query first. Answer the check. Then say: "I can look things up but can't make changes. To enable voicemail, you'd go to Control Hub → Calling → User Settings → Voicemail, or I can help configure it if you'd like to switch to build mode."

## Step 2: Route to domain module(s)

Read the domain module(s) that match the question. Cross-domain queries load multiple modules.

### Domain Routing Table

| Question about... | Domain module | Load with |
|-------------------|--------------|-----------|
| Users, person settings (voicemail, forwarding, DND, recording, caller ID, permissions) | people-and-settings | `Read .claude/skills/query-live/domains/people-and-settings.md` |
| Hunt groups, call queues, auto attendants, paging, call park, pickup, voicemail groups | features | `Read .claude/skills/query-live/domains/features.md` |
| Trunks, route groups, route lists, dial plans, translation patterns, PSTN | routing | `Read .claude/skills/query-live/domains/routing.md` |
| Phone numbers, number inventory, assignment status, available numbers | numbers | `Read .claude/skills/query-live/domains/numbers.md` |
| Call history, CDR, call volume, missed calls, busiest hours | call-history | `Read .claude/skills/query-live/domains/call-history.md` |
| "What happens when someone calls...", call path tracing, schedule evaluation | call-flow-trace | `Read .claude/skills/query-live/domains/call-flow-trace.md` |

**Cross-domain examples:**
- "Show me all users at Austin with their devices and voicemail status" → people-and-settings (primary)
- "Who's in the Sales hunt group and what are their forwarding settings?" → features + people-and-settings
- "What number is assigned to the Main auto attendant?" → features + numbers

## Step 3: Execute the domain module's recipes

Follow the loaded domain module's command recipes, resolution rules, and join patterns exactly. Use `-o json` on all commands for programmatic parsing.

### Resource Resolution Protocol

When the user references a resource by name (not ID):

1. **List** the resource type with `-o json`
2. **Search** the response for name matches (case-insensitive substring)
3. **Exact match** → use it immediately
4. **Multiple partial matches** → disambiguate:
   ```
   I found 2 hunt groups matching "Sales":
     1. Sales - East (Austin, 5 members)
     2. Sales - West (Denver, 3 members)
   Which one?
   ```
5. **No match** → report with suggestion:
   ```
   I couldn't find a hunt group named "Sales". The hunt groups at your org are:
     - Support (Austin)
     - Engineering (Denver)
     - Front Desk (Austin)
   Did you mean one of these?
   ```

### Batch Query Protocol

For audit queries checking a setting across many users (e.g., "which users don't have voicemail?"):

1. **Count first:** `wxcli people list -o json` → count results
2. **If ≤ 50 users:** Fetch settings for each user sequentially
3. **If > 50 users:** Note upfront: "Checking [N] users — this will take a moment." Batch in groups of 20 with brief progress updates every 20 users.
4. **Report:** "Checked all [N] users at [location]. [X] of [N] don't have voicemail enabled."

## Step 4: Format the response

### Formatting Principles

- **Lead with the direct answer**, then supporting details
- **Use the admin's language**: "voicemail" not "voicemailEnabled", "forwarding" not "callForwarding"
- **Include counts and context**: "3 of 12 users" not just "3 users"
- **Be specific about what was checked**: "I checked all 45 users at the Austin location"

### Format by Query Type

**Membership queries** ("Who's in the Sales hunt group?"):
```
Sales Hunt Group has 4 members:
  - Jane Smith (ext 2001, Austin)
  - Bob Lee (ext 2002, Austin)
  - Maria Garcia (ext 2003, Denver)
  - Tom Chen (ext 2004, Denver)

Ring pattern: Simultaneous
No-answer action: Forward to Sales voicemail after 20 seconds
```

**Yes/no queries** ("Does John have voicemail enabled?"):
```
Yes, John Smith has voicemail enabled.
  - Messages sent to: john.smith@acme.com
  - PIN required: Yes
  - Greeting: Custom greeting uploaded
```

**Inventory/audit queries** ("Which users at Austin don't have voicemail?"):
```
12 of 45 users at Austin don't have voicemail enabled:
  - Alice Johnson (ext 3001)
  - Brian Kim (ext 3002)
  - Carol Davis (ext 3003)
  ... and 9 more

Note: I checked all 45 Webex Calling-licensed users at the Austin location.
```

**Large result sets (> 10 items):**
- Show first 10 with "...and N more" note
- Include summary count at top
- Offer to show full list if needed

### Disambiguation format:
```
I found 2 queues matching "Sales":
  1. Sales - East (Austin, 5 agents)
  2. Sales - West (Denver, 3 agents)

Which one?
```

## Safety Guardrails

### Read-Only Enforcement

**Only use these command verbs:** `list`, `show`, `test`

**Blocklisted verbs — NEVER use these in query mode:**
`create`, `add`, `update`, `modify`, `delete`, `remove`, `assign`, `enable`, `disable`, `configure`

If the user requests a change, respond with:
1. The current state (the query result)
2. "I can look things up but can't make changes in query mode."
3. Where in Control Hub they'd make the change, OR offer to switch to build mode

### Scope Limiting

- Operate within the org authenticated via `wxcli configure`
- If a partner/multi-org token is active, query the currently-selected org only
- No cross-org queries or comparisons

### Error Handling

| Error | Response |
|-------|----------|
| 401 Unauthorized | "Your session may have expired. Run `wxcli configure` to re-authenticate." |
| 403 Forbidden | "Your account doesn't have permission to view [resource]. Contact your org admin." |
| 404 Not Found | "I couldn't find [resource]. It may have been deleted or the name might be different." |
| 429 Rate Limited | "The API is rate-limiting requests. Try again in a minute." |
| Timeout | "The request timed out. The org may have a large number of [resources]. Try narrowing your query to a specific location." |
