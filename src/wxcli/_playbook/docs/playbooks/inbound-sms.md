# Inbound SMS Playbook

<!-- ref-tag: inbound-sms-v1 -->

> **SMS values on this page are owned by `docs/reference/connect-sms.md`** (ref-tag `connect-sms-v2`) — the `sms.*` output variables, SMS node fields, 10DLC registration, provisioning and sandbox limits. They are reproduced here so the build can be completed without leaving the page; the reference doc wins on any disagreement. Evaluate-node, Branch-node and HTTP-Request-node values are owned by `docs/reference/webex-connect.md` and `docs/reference/webex-connect-advanced.md`.

## Overview

This playbook covers how to build **standalone inbound SMS flows** in Webex Connect — flows where a customer texts a command to your number and gets a response, WITHOUT an AI Agent, Engage conversation nodes, or the multi-turn AI Agent loop documented in `digital-inbound.md`.

This is the inbound complement to `outbound-sms.md` (webhook → SMS out). Where outbound-sms covers "system pushes a text to a user," this playbook covers "user texts a command and gets a response."

**Use cases:** On-call roster updates via text, keyword-triggered lookups, SMS-based admin commands, two-way opt-in/opt-out flows.

**Key distinction from AI Agent flows:** These flows use Start (SMS - Mobile Originated - MO) → Evaluate → HTTP → SMS Reply. No AI Agent node, no Engage conversation nodes, no Receive loop. For AI Agent conversation flows over SMS, see `digital-inbound-agent.md`.

---

## 1. Flow Structure

### Happy Path

```
Start (SMS - Mobile Originated - MO)
  |
  v
Evaluate (parse CSV, validate E.164, set custom flow variables)
  |
  +-- ["invalid" branch] --> SMS (error reply to sender) --> End
  |
  +-- ["valid" branch] -->
  |
  v
HTTP Request (PUT to Webex People API — update user title)
  |
  +-- onSuccess --> Branch (statusCode == 200?)
  |                   |
  |                   +-- [Yes] --> SMS (success reply to sender) --> End
  |                   |
  |                   +-- [No]  --> SMS (error reply to sender) --> End
  |
  +-- onError ------> SMS (error reply to sender) --> End
  |
  +-- onTimeout ----> SMS (error reply to sender) --> End
```

### Required Nodes

- **Start node** (always first): SMS - Mobile Originated - MO trigger receives the inbound text
- **Evaluate node**: parses, validates, and transforms the message body
- **HTTP Request node**: calls the external API
- **Branch node**: checks the HTTP response status code
- **SMS node(s)**: replies to the sender with success/error messages
- **End node**: terminates the flow

**Casing note on the timeout edge.** The diagram above spells the HTTP Request node's third exit `onTimeout`, which is how Cisco's HTTP Request node page spells it [`docs/tests/findings/inbound-sms-findings.md` #11]. The SMS node's timeout exit is spelled `onTimeOut` with a capital `O`, per Cisco's node-level exception-handling page [`connect-sms.md` § Exit Paths]. Both spellings are genuinely live — they are per-node, so do not normalise one into the other.

### Optional Nodes

- **Receive node** (mid-flow): waits for a second SMS from the sender (confirmation pattern — see Section 7)
- **Branch node** (after Evaluate): routes on validation results before the HTTP call

---

## 2. Start Node Configuration

| Setting | Value |
|---------|-------|
| **Trigger** | SMS - Mobile Originated - MO ⚠ see the O5 note below — the exact label is **not** settled |
| **Incoming Number** | Select the provisioned two-way number from dropdown |
| **Keyword** | Leave blank for free-form body (see Section 10 - Gotchas for keyword interaction) |
| **Trigger Conditions** | Optional — use to filter by sender MSISDN or message content |
| **"Trigger only when there are no live sessions"** | Check this to prevent duplicate flow instances for the same sender |

#### ⚠ Open item O5 — the trigger label is unresolved

Three spellings of the inbound SMS trigger are live in this repo: `SMS - Mobile Originated - MO`, `Mobile Originated - MO`, and `SMS - Mobile Originated`. The spelling used throughout this playbook is **preserved verbatim and has not been corrected**, because no verified label was available. Tracked as **open item O5** in `docs/plans/2026-07-25-documentation-remediation-backlog.md` § 6 "Open items requiring tenant or platform access"; the same hedge appears in `connect-sms.md` § Open item O5 and `docs/reference/digital-inbound.md`.

Resolving it requires reading the literal label out of the Webex Connect trigger-node trigger picker on the tenant. **Do not settle it from the other two spellings, from majority use in this repo, or from memory.** When you open the picker, pick whichever of the three you see — all three refer to the same trigger.

### Output Variables (SMS - Mobile Originated - MO)

> **Owner: `connect-sms.md` § Inbound SMS Output Variables (`sms.*`).** Reproduced here so this page works standalone; the reference doc wins on any disagreement. Note this is the **inbound** `sms.*` namespace — the SMS *send* node exposes a different `send.*` set, and the two never mix.

These are the variables available from the trigger node for an SMS trigger, verified from the official Receive node documentation:

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `$(n1.sms.message)` | Full text content of the inbound SMS | `5551234567,5559876543,5551112222` |
| `$(n1.sms.senderNumber)` | Sender's phone number (E.164) | `+15557770001` |
| `$(n1.sms.serviceNumber)` | Your number that received the message (E.164) | `+15550001234` |
| `$(n1.sms.keyword)` | Matched keyword (if keyword filtering is configured) | `UPDATE` |
| `$(n1.sms.ts)` | Receipt timestamp in ISO 8601 UTC format (official docs use `sms.ts`; some sources show `sms.timestamp` — verify on your platform) | `2026-04-17T14:30:00Z` |
| `$(n1.sms.transId)` | Transaction identifier | `uuid-string` |

The Start node page itself does not enumerate SMS output variables — it redirects to the Receive node page. The variable namespace (`n1.sms.*`) is the same for both Start and Receive nodes; only the node number prefix changes.

**Note on `msisdn` vs `senderNumber`:** Our existing docs reference `$(n1.sms.msisdn)` for the sender's number. The official Receive node docs list only `sms.senderNumber` in the SMS output variables table — `sms.msisdn` does not appear there. This playbook uses `$(n1.sms.senderNumber)` as the canonical reference per official docs. See Section 14 - Open Questions (Q1) for resolution approach.

---

## 3. Evaluate Node (Parse & Validate)

The Evaluate node parses the inbound message body, validates phone numbers, and constructs the HTTP request body. The Evaluate node returns **one result** — the value of the last evaluated expression. "Configure Script Output" names that result, which appears in the Output Variables panel and is accessible as `$(nX.outputName)`. It is primarily used for **branch routing** — the Branch Name must match the result string. For passing multiple values to downstream nodes, use **custom flow variables** created in Flow Settings > Custom Variables.

**Note:** The official docs state "The Evaluate node script returns the result as a decimal value." In practice, string returns (`"valid"`, `"invalid"`) work for branch routing — confirmed by live testing. Writing to custom flow variables from within the script (by assigning without `var`) is observed behavior from testing, not explicitly documented.

### Custom Flow Variables (create in Flow Settings > Custom Variables before writing the script)

| Variable | Init Value | Purpose |
|----------|-----------|---------|
| `parsed_numbers` | (empty) | JSON array of validated E.164 numbers |
| `validation_error` | (empty) | Error message if validation fails |
| `number_count` | `0` | Count of valid numbers |
| `put_body` | (empty) | Constructed JSON body for People API PUT |

Custom flow variables are referenced as `$(variableName)` — NO node prefix, NO `.evaluate.` segment.

### Evaluate Node Settings

| Setting | Value |
|---------|-------|
| **Configure Script Output** | `valid` — names the routing result |
| **Branch: `valid`** | Wire to HTTP Request node |
| **Branch: `invalid`** | Wire to error SMS reply node |

The `+ Add New` button in the Evaluate node adds another script block, NOT an additional output.

### JavaScript: CSV Parsing + E.164 Validation + Body Construction

```javascript
var raw = "$(n1.sms.message)";

// Strip optional command prefix (e.g., "UPDATE 555..., 555...")
var body = raw.replace(/^UPDATE\s*/i, "").trim();

// Split on comma, trim whitespace
var parts = body.split(",");
var valid = [];
var invalid = [];

for (var i = 0; i < parts.length; i++) {
  var num = parts[i].trim();
  // Strip non-digit characters except leading +
  var cleaned = num.replace(/[^\d+]/g, "");
  // Accept 10-digit (US) or E.164 with +1 prefix
  if (/^\+?1?\d{10}$/.test(cleaned)) {
    // Normalize to +1XXXXXXXXXX
    var digits = cleaned.replace(/\D/g, "");
    if (digits.length === 10) digits = "1" + digits;
    valid.push("+" + digits);
  } else {
    invalid.push(num);
  }
}

// Write results to custom flow variables (no var keyword = flow scope assignment)
if (valid.length === 0) {
  validation_error = "No valid phone numbers found. Send comma-separated 10-digit numbers.";
  "invalid";
} else {
  if (invalid.length > 0) {
    validation_error = "Skipped invalid: " + invalid.join(", ") + ". Processing " + valid.length + " valid number(s).";
  }
  number_count = valid.length;
  parsed_numbers = JSON.stringify(valid);
  put_body = JSON.stringify({
    title: valid.join(",")
  });
  "valid";
}
```

The key pattern: `validation_error`, `number_count`, `parsed_numbers`, and `put_body` are **assignments to custom flow variables** (no `var` keyword = writes to flow scope), not local variable declarations. The last expression (`"valid"` or `"invalid"`) is the routing string that determines which branch the flow follows.

**Note:** The Evaluate node runs on the JavaScript engine used by Webex Connect (community knowledge identifies it as Mozilla Rhino, Java-based — the official docs do not name the engine). It runs on the Connect server, not in a browser. It supports Connect's built-in libraries (`imi_general`, `imi_base64`, `imi_strings`, `imi_array`), plus `JSON.stringify` and `JSON.parse`. `let`/`const` work for local variable declarations. Arrow functions and template literals are **not** available — use traditional `function` syntax and string concatenation.

---

## 4. Branch Node (Validation Check)

| Setting | Value |
|---------|-------|
| **Input Variable** | `$(validation_error)` |
| **Condition 1** | Equals `""` (empty string = all valid) → route to HTTP PUT |
| **Condition 2** | Contains `"No valid"` → route to error SMS reply |
| **None of the above** | Route to HTTP PUT (partial success — some invalid numbers skipped, log warning in SMS reply) |

**Note:** If the Evaluate node's own branches can wire directly to downstream nodes (the `valid` branch to HTTP Request, the `invalid` branch to error SMS), this Branch node may be unnecessary. Test in sandbox.

---

## 5. HTTP Request Node (PUT to Webex People API)

| Setting | Value |
|---------|-------|
| **Method** | PUT |
| **URL** | `https://webexapis.com/v1/people/{userId}` — the `userId` is hardcoded or looked up |

### Headers

| Header | Value |
|--------|-------|
| `Authorization` | `Bearer {access_token}` — Webex integration or service app token |
| `Content-Type` | `application/json` |

### Body & Timeouts

| Setting | Value |
|---------|-------|
| **Body** | `$(put_body)` — the JSON body constructed in the Evaluate node (custom flow variable) |
| **Connection Timeout** | `10000` ms (suggested; max is 20,000 ms — no default is documented) |
| **Request Timeout** | `15000` ms (suggested; max is 20,000 ms — no default is documented) |

### Output Variables

Parse a sample People API PUT response:

```json
{
  "id": "Y2lzY29...",
  "displayName": "On-Call Admin",
  "title": "+15551234567,+15559876543",
  "emails": ["oncall@example.com"]
}
```

| Output Variable | JSONPath |
|----------------|----------|
| `updated_title` | `$.title` |
| `display_name` | `$.displayName` |

**Note on PUT vs PATCH:** The Webex People API uses PUT for updating a person record (not PATCH). The HTTP Request node supports PUT — select it from the Method dropdown. Configuration is identical to POST (URL + headers + JSON body).

---

## 6. Branch Node (HTTP Status Check)

| Setting | Value |
|---------|-------|
| **Input Variable** | `$(n4.https.statusCode)` |
| **Condition 1** | Equals `200` → route to success SMS |
| **None of the above** | Route to error SMS |

**Note (empirically observed, not confirmed by official docs):** HTTP 4xx/5xx responses appear to route through the HTTP node's `onSuccess` edge, not `onError`. The Branch node is required to distinguish success from failure by status code.

---

## 7. SMS Node (Reply to Sender)

| Setting | Value |
|---------|-------|
| **Destination Type** | `msisdn` |
| **Destination** | `$(n1.sms.senderNumber)` — the original sender's phone number |
| **From Number** | Select the **same number** that received the inbound message (must match the Start node's provisioned number) |
| **Message Type** | `Text` |
| **Wait For** | `Gateway Submit` |

> **Owner: `connect-sms.md` § SMS Node.** Reproduced here so this page works standalone; the reference doc wins on any disagreement. The reply body is subject to the same **4,000-character** hard cap and **below-450** deliverability recommendation as any other SMS [`connect-sms.md` § Message length — two numbers, do not confuse them].

### Reply Pattern

There is no dedicated "Reply" mechanism in Connect. To reply to an inbound SMS sender:

1. Set **Destination** to `$(n1.sms.senderNumber)` (the inbound sender's MSISDN)
2. Set **From Number** to the same provisioned number from the dropdown (matches `$(n1.sms.serviceNumber)`)

This creates a reply because the sender sees a message from the same number they texted.

### Message Templates

**Success:**
```
Updated $(number_count) on-call number(s) for $(n4.display_name). Title set to: $(n4.updated_title)
```

**Validation Error (no valid numbers):**
```
Error: $(validation_error)
```

**HTTP Error:**
```
Update failed (HTTP $(n4.https.statusCode)). Please try again or contact admin.
```

### Multiple Reply Points

A flow can have multiple SMS reply nodes (success reply, error reply, partial-success reply). Each uses the same Destination/From pattern. Wire them to separate exit paths from Branch nodes.

---

## 8. Multi-Step Confirmation Variant

### When to Use

When the inbound command has irreversible side effects (API updates, record deletions), add a confirmation step: parse and validate first, then ask "Are you sure?" and wait for the reply.

### Flow Diagram

```
Start (SMS-MO) → Evaluate (parse/validate) → SMS ("Update 3 numbers? Reply Y")
  → Receive (SMS, 120s timeout)
    → [Y] → HTTP PUT → Branch (200?) → SMS (success) → End
    → [not Y] → SMS (cancelled) → End
    → [timeout] → SMS (timed out) → End
```

### Additional Nodes Required

| Node | Purpose |
|------|---------|
| **SMS (confirmation prompt)** | Sends "Update 3 numbers? Reply Y to confirm" to sender |
| **Receive (SMS)** | Waits for the sender's reply (Y/N) with a timeout |
| **Branch (Y/N check)** | Routes based on reply content |

### Receive Node Configuration (Mid-Flow SMS)

| Setting | Value |
|---------|-------|
| **Channel** | SMS |
| **Number** | Select the same provisioned two-way number |
| **From Number** | `$(n1.sms.senderNumber)` — only accept replies from the original sender |
| **Max Timeout** | `120` seconds (2 minutes — reasonable wait for a human reply) |
| **Success exit label** | `sms.mo` — the SMS success edge (not generic `onSuccess`); wire downstream nodes to this edge |

#### Receive Node Output Variables

| Variable | Description |
|----------|-------------|
| `$(nX.sms.message)` | The reply text (e.g., "Y" or "N") |
| `$(nX.sms.senderNumber)` | Sender's number (should match original) |

#### Branch After Receive

| Condition | Route |
|-----------|-------|
| `$(nX.sms.message)` equals `Y` (case-insensitive via Equals ignore-case) | Proceed to HTTP PUT |
| None of the above | SMS reply "Cancelled. No changes made." → End |

### Constraints

- **No 30-second timeout** — this is NOT an AI Agent flow, so standard flow timing applies. The Receive node can wait as long as its Max Timeout setting.
- **No prohibited nodes** — Delay, Receive Node, Call Workflow are all allowed in non-agent flows.
- The Receive node's **From Number** filter ensures only the original sender's reply resumes the flow. Other senders' messages will not match.

---

## 9. Evaluate Node Examples

### Example 1: Simple CSV Split

```javascript
var raw = "$(n1.sms.message)";
var parts = raw.split(",");
var trimmed = [];
for (var i = 0; i < parts.length; i++) {
  trimmed.push(parts[i].trim());
}
csv_result = trimmed.join(",");
"done";
```

**Note:** `csv_result` is a custom flow variable (no `var` keyword = writes to flow scope). The last expression `"done"` is the routing string. Create `csv_result` in Flow Settings > Custom Variables before using this script.

### Example 2: E.164 Validation (US Numbers)

```javascript
var num = "$(n1.sms.message)".trim();
var cleaned = num.replace(/[^\d+]/g, "");
var isValid = /^\+?1?\d{10}$/.test(cleaned);
if (isValid) {
  validated_number = cleaned;
  "valid";
} else {
  "invalid";
}
```

**Note:** `validated_number` is a custom flow variable. Branch routes on `"valid"` vs `"invalid"`. Create `validated_number` in Flow Settings > Custom Variables before using this script.

### Example 3: Construct HTTP PUT Body with Dynamic Fields

```javascript
var numbers = "$(parsed_numbers)";
var parsed = JSON.parse(numbers);
var title = parsed.join(",");
put_body = JSON.stringify({
  title: title,
  displayName: "On-Call: " + parsed.length + " numbers"
});
"ready";
```

**Note:** `put_body` is a custom flow variable. `$(parsed_numbers)` references the custom flow variable set by a previous Evaluate node — NO node prefix, NO `.evaluate.` segment.

### Example 4: Keyword + Body Extraction

```javascript
var raw = "$(n1.sms.message)";
// Pattern: "COMMAND arg1,arg2,arg3"
var spaceIdx = raw.indexOf(" ");
command = (spaceIdx > -1) ? raw.substring(0, spaceIdx).toUpperCase() : raw.toUpperCase();
args = (spaceIdx > -1) ? raw.substring(spaceIdx + 1).trim() : "";
"parsed";
```

**Note:** `command` and `args` are custom flow variables (no `var` keyword). The last expression `"parsed"` is the routing string.

---

## 10. Known Gotchas

### Keyword Conflicts

| Issue | Details | Fix |
|-------|---------|-----|
| **Keyword filter swallows the command prefix** | If the Start node has keyword `UPDATE` configured, the `$(n1.sms.keyword)` variable captures it but `$(n1.sms.message)` may or may not include it depending on platform behavior. | Test whether `message` includes or excludes the keyword. If it excludes it, don't strip it again in the Evaluate node. If it includes it, strip it. |
| **Multiple flows competing for the same keyword** | Two flows with the same trigger number and keyword = unpredictable routing. | Use unique keywords per flow, or use one flow with Branch logic on message content. |
| **Blank keyword = catch-all** | A Start node with no keyword configured matches ALL inbound SMS to that number. If you have another flow with a keyword trigger on the same number, the catch-all flow may also fire. | Use "Trigger only when there are no live sessions" or be explicit about which flow handles which messages. |

### Phone Number Encoding

| Issue | Details | Fix |
|-------|---------|-----|
| **Plus sign in SMS body** | Some carriers strip or encode the `+` in `+15551234567`. | In the Evaluate node, handle numbers with or without the `+` prefix. Normalize all to `+1XXXXXXXXXX`. |
| **Unicode spaces and dashes** | Users may type `555-123-4567` or `555 123 4567`. | Strip all non-digit characters (except leading `+`) before validation. |
| **Carrier message encoding** | If the sender's phone adds Unicode characters (smart quotes, em-dashes), the CSV split may fail. | Use a regex-based split that handles multiple separator types: `/[,;\s]+/` |

### People API Rate Limits

| Constraint | Value |
|-----------|-------|
| **Rate limit** | Webex APIs enforce per-app rate limits. People API: typically 100 requests/second for Service Apps. |
| **Throttling response** | HTTP 429 with `Retry-After` header. |
| **Mitigation** | For single-user update flows, rate limits are not a concern. For bulk operations, add delay between calls. |

### Flow Execution

| Issue | Details | Fix |
|-------|---------|-----|
| **Flow not triggering** | Flow not published (not Made Live). | Click Make Live in Flow Builder. |
| **Variables empty in Evaluate** | Start node variables typed manually instead of using variable picker. | Always use the variable picker. |
| **SMS reply not arriving** | From Number in SMS reply node doesn't match the inbound number. | Select the same provisioned number in both Start node and SMS node. |
| **Receive node not resuming** | In multi-step variant: From Number filter doesn't match the sender. | Ensure From Number in Receive node = `$(n1.sms.senderNumber)`. |
| **Multiple flow instances for same sender** | Sender sends a second message before the first flow completes. | Enable "Trigger only when there are no live sessions" on the Start node. |

### Character Limits on Reply

| Issue | Details | Fix |
|-------|---------|-----|
| **Reply exceeds 160 chars** | SMS segments: 160 chars (GSM-7) or 70 chars (Unicode). Long replies split into multiple segments (billed separately). | Keep reply messages under 160 chars when possible. |
| **Variable expansion overflows** | A variable like `$(n4.updated_title)` could expand to a long string of phone numbers. | Truncate or summarize in the Evaluate node before inserting into the SMS body. |

---

## 11. Prerequisites

> **Owner of the SMS rows: `connect-sms.md` § Sender ID Types, § US A2P 10DLC Registration, § Provisioning Prerequisites.** Reproduced here so the prerequisites can be checked without leaving the page; the reference doc wins on any disagreement. ⚠ Unregistered US 10DLC senders are reported to fail with code `7281`, but that code mapping is **unverified** — see the caveat at the owner before branching on it.

### Number Provisioning

| Requirement | Details |
|------------|---------|
| **Two-way SMS number** | Must support receiving inbound SMS. 10DLC, Toll-Free, or Short Code with two-way. |
| **US 10DLC registration** | Required for US long codes. Brand + Campaign registration with TCR, then assign to number in Connect (Assets → Numbers → Actions → Request 10DLC). |
| **SMS feature enabled** | When provisioning, ensure the SMS checkbox is selected. |
| **Number assigned to service** | The number must be in the same service where the flow is created. |

### Webex People API Access

| Requirement | Details |
|------------|---------|
| **Webex Integration or Service App** | OAuth integration with `spark:people_write` scope, or a Service App with People write permissions. |
| **Access token** | Bearer token for the API calls. For production, use a Service App token (long-lived) rather than a personal token (12-hour expiry). |
| **Target user ID** | The `userId` for the person whose title field is being updated. Can be hardcoded for a single-user flow or looked up dynamically. |

### Connect Prerequisites

| Requirement | Details |
|------------|---------|
| **Webex Connect tenant** | Active tenant with Flow Builder access. |
| **Service created** | Flows live inside a service. Create one if none exists. |
| **Node availability** | Start, Evaluate, HTTP Request, Branch, SMS, End. All standard nodes — no special node authorization required (unlike Engage nodes). |

---

## 12. Testing Guide

### Sandbox Setup for Two-Way SMS

1. **Navigate to Sandbox:** Connect dashboard → Sandbox → SMS tab
2. **Register test numbers:** Add up to 5 phone numbers (all same country). These are the numbers that can send inbound SMS to the sandbox number.
3. **Note the sandbox number:** The "From Number" is auto-populated and fixed — this is the number your test phones will text.
4. **Send an inbound SMS:** From a registered test phone, send a text to the sandbox number. The message appears in the "Recently Received SMS" field and the SMS Receive Payload panel.
5. **Build the flow:** In the Flow Builder, create a flow with Start trigger = SMS - Mobile Originated - MO, selecting the sandbox number.
6. **Publish the flow:** Click Make Live. The flow must be live for the Start trigger to accept inbound messages.
7. **Test end-to-end:** Send a text from your registered phone → flow triggers → Evaluate parses → HTTP fires → SMS reply arrives on your phone.

### Sandbox Limitations for Inbound SMS

> **Owner: `connect-sms.md` § Sandbox Limitations.** The 18-country, 10,000-request and 5-number figures are reproduced here so this page works standalone; the reference doc wins on any disagreement. All three are Cisco-confirmed; the "~15 nodes" count is confirmed but **which** ~15 is not enumerated, which is why Receive-node availability stays an open question (§ 14 Q3).

| Constraint | Impact |
|-----------|--------|
| **Two-way SMS in 18 countries only** | If your country isn't in the list, you cannot test inbound SMS in sandbox |
| **10,000 lifetime SMS + WhatsApp requests** | Each inbound + outbound counts. A parse-reply flow burns 2 per test. |
| **Only ~15 nodes available** | HTTP Request, Evaluate, Branch, SMS are all available. Receive (mid-flow) availability should be verified. |
| **5 registered test numbers max** | Only these numbers can send inbound SMS to the sandbox |
| **From number is fixed** | Cannot change the sandbox sender; replies come from this number |

### Production Testing

1. **Provision a two-way number:** Assets → Numbers → Get Numbers → select Phone Number with SMS feature enabled. For US: complete 10DLC registration.
2. **Build and publish the flow** with Start trigger pointing to the provisioned number.
3. **Send a test SMS** from any phone to the provisioned number.
4. **Check Flow Debug:** Click the bug icon in Flow Builder → see the 10 most recent executions with node-by-node traces.
5. **Check Transaction Logs:** Available within ~2 minutes, retained for 30 days.

### curl Testing for the HTTP Node

Test the Webex People API PUT independently before wiring it into the flow:

```bash
curl -X PUT \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{"title": "+15551234567,+15559876543"}' \
  "https://webexapis.com/v1/people/{userId}"
```

Verify the response returns HTTP 200 with the updated person record.

---

## 13. Cross-References

| Document | Relevance |
|----------|-----------|
| `docs/playbooks/outbound-sms.md` | Outbound SMS complement — same SMS node config, different trigger (webhook vs inbound SMS) |
| `docs/playbooks/webhook-triggers.md` | Start node webhook config — similar but for webhook triggers, not SMS triggers |
| `docs/reference/connect-sms.md` | **Owner** of every SMS value on this page — `sms.*` inbound variables, node fields, encoding, segmentation, sender IDs, 10DLC, sandbox limits, delivery status codes |
| `docs/reference/connect-response-codes.md` | Owner of the inbound-webhook / Event-API response codes (`1002`, `7000`–`7029`, `430`) — not the SMS delivery codes |
| `docs/reference/digital-inbound.md` | AI Agent conversation flows using SMS trigger — the pattern this playbook explicitly avoids |
| `docs/reference/webex-connect.md` | Core flow concepts, HTTP Request node, Variable Picker, Flow Outcomes |

---

## 14. Open Questions

These four are unresolved here **and** at the owner — `connect-sms.md` § Inbound SMS Output Variables carries the same hedges for Q1 and for `sms.ts`. Do not close any of them from this page alone. The trigger-label question is tracked separately as open item **O5** (see § 2).

### Q1: `msisdn` vs `senderNumber`

Our docs reference `$(n1.sms.msisdn)` for the sender's number. The official Receive node docs list `sms.senderNumber`. The platform also exposes `msisdn` as a session variable. Need to test which variable name works in the Start node context for SMS - Mobile Originated - MO triggers. This playbook uses `senderNumber` as the canonical reference per official docs and notes `msisdn` as an alternative.

**Resolution approach:** Build a minimal test flow in sandbox — Start (SMS-MO) → Evaluate (log both `$(n1.sms.msisdn)` and `$(n1.sms.senderNumber)`) → SMS reply with both values → verify which populates.

### Q2: Keyword + Message Body Interaction

When a keyword is configured on the Start node (e.g., `UPDATE`), does `$(n1.sms.message)` include or exclude the keyword? E.g., if the user texts "UPDATE 5551234567", is `message` = `"UPDATE 5551234567"` or `"5551234567"`?

**Resolution approach:** Test in sandbox with a keyword-configured Start node.

### Q3: Receive Node Availability in Sandbox

The sandbox documentation says only ~15 nodes are available (vs 50+ in production). The multi-step confirmation variant uses a Receive node mid-flow. Need to verify Receive is available in sandbox.

**Resolution approach:** Check the node palette in a sandbox flow.

### Q4: Start Node Variable Namespace Consistency

The Start node page says "refer to Output Variables in Receive Node page." But the Receive node docs may list variables for the Receive node's context (mid-flow), not the Start node's context. Are the variable names and namespaces identical? Does the Start node use `$(n1.sms.senderNumber)` with the same property name as the Receive node's `$(nX.receive.sms.senderNumber)`, or does it use a different path?

**Resolution approach:** Per official docs, both the Start and Receive nodes use the same variable namespace: `$(nX.sms.message)`, `$(nX.sms.senderNumber)`, etc. — no `.receive.` segment in the path for either node. The official Receive node docs and `digital-inbound.md` both confirm `$(n1.sms.message)` for the Start node.
