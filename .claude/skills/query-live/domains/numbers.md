# Numbers Domain

**Covers:** Phone number inventory, assignment status, available numbers, number lookups by person or location.

## Question Patterns

| Pattern | Example |
|---------|---------|
| Number inventory | "How many numbers do we have?", "Show me all numbers at Austin" |
| Assignment lookup | "What number is John Smith on?", "Who has +1-512-555-1000?" |
| Available numbers | "Which phone numbers aren't assigned?", "How many numbers are available at Denver?" |
| Number type query | "Show me all toll-free numbers", "Which numbers are DID vs extension?" |

## Command Recipes

### List all numbers (org-wide)
```bash
wxcli numbers list -o json
```

### List numbers at a location
```bash
wxcli numbers list --location-id LOCATION_ID -o json
```

### List available (unassigned) numbers
```bash
wxcli numbers list --available true -o json
```

### List numbers filtered by state
```bash
wxcli numbers list --state ACTIVE -o json
# States: ACTIVE, INACTIVE
```

### Find a number by phone number
```bash
wxcli numbers list --phone-number "+15125551000" -o json
```

### Find numbers by owner
```bash
wxcli numbers list --owner-id PERSON_ID -o json
```

## Resolution Rules

**Finding a person's number:**
1. `wxcli people list --display-name "John Smith" -o json` → get person ID
2. `wxcli numbers list --owner-id <personId> -o json` → get their number(s)

**Finding who has a number:**
1. `wxcli numbers list --phone-number "+15125551000" -o json` → check `owner` field
2. The `owner` object contains `type` (PEOPLE, AUTO_ATTENDANT, CALL_QUEUE, HUNT_GROUP, etc.) and `id`
3. If type is PEOPLE: `wxcli people show <ownerId> -o json` → get the person's name

**Finding a location's numbers:**
1. If user says a location name (not ID): `wxcli locations list -o json` → search by name → get location ID
2. `wxcli numbers list --location-id <locationId> -o json`

## Response Guidance

**Inventory query** ("Show me all numbers at Austin"):
Group by assignment status. Show counts.
```
Austin has 50 phone numbers:
  - 38 assigned (32 to users, 3 to auto attendants, 2 to call queues, 1 to hunt group)
  - 12 available

Number range: +1-512-555-1000 through +1-512-555-1049
```

**Lookup query** ("What number is John on?"):
```
John Smith has 1 number:
  - +1-512-555-1023 (extension 1023, Austin location)
```

**Available query** ("Which numbers aren't assigned?"):
```
12 numbers are available at Austin:
  - +1-512-555-1038
  - +1-512-555-1039
  ... and 10 more
```

## Gotchas

1. **Number list can be large.** For orgs with 1000+ numbers, encourage location-scoped queries: "That's a lot of numbers. Want me to check a specific location?"
2. **Owner field structure.** The `owner` object in the number response has `type`, `id`, `firstName`, `lastName`. Use firstName/lastName directly when available — avoids an extra API call.
3. **Main number flag.** Numbers with `mainNumber: true` are the location's main line. Note this in responses: "+1-512-555-1000 (main number for Austin)".
4. **Extension vs DID.** Numbers may be extension-only (no external DID). Check `phoneNumberType` field.
