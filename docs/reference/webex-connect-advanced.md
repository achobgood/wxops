# Webex Connect — Advanced Node Reference

<!-- ref-tag: connect-advanced-v9 -->

Advanced node types for AI agent action flows. Load this reference when the action requires error routing, data transformation, or side-effect notifications (SMS, email, RCS, Apple Messages, WhatsApp). All nodes documented here are safe within the 30-second agent flow timeout.

**Prerequisite:** This document assumes familiarity with `webex-connect.md`. Read that first for core concepts (trigger node, HTTP nodes, Variable Picker, Flow Outcomes).

Every Webex Connect flow starts with a **trigger node**: you pick a **trigger category**, and the node presents as that category's configuration — **Configure AI Agent Event** for AI Agent, **Configure SMS Event** for SMS, and a **Webex CC Task** node for Webex CC Task. The `Trigger → ...` shorthand used in the flow sketches below means that trigger node.

> **Flow Outcomes is NOT a node — read this before using the flow sketches below.**
>
> Flow Outcomes lives in the flow-level **Flow Settings** area, opened from the **Flow Settings** button on the Flow Builder page. There is nothing to drop on the canvas [source: https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions; Flow Outcomes is listed as a Flow Settings section, not a node, at https://help.webexconnect.io/docs/flow-settings].
>
> **Consequence: exactly ONE outcome key-set per flow.** Every path through the flow returns the *same set of keys*. You cannot give one Branch leg its own return payload. To vary what the agent sees, set flow variables on each leg and read them from the single key-set.
>
> On the canvas, every sketch below terminates at an **End (END FLOW)** node. `→ End` is the canvas terminal; the returned payload is configured in Flow Settings.
>
> **Settled configuration facts:** use **Enter key and value** mode, never **Enter JSON** (JSON mode returns literal `$(nX.y)` strings instead of resolved values — the mode split is documented by Cisco, the variable-resolution failure is a project finding and is **unverified** against Cisco docs). On the **Last Execution Status** row, enable **Notify** and make sure **Notify AI Agent** is the selected target, or the agent never receives the data. Cisco documents the Notify AI Agent radio button as *"enabled by default for the start node with 'AI Agent' as the trigger"*; the tenant owner describes selecting it under a **Notification Settings** heading (a label that does not appear in the Cisco page) — **which of the two it is remains unverified** [source: https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions]. Full detail in `webex-connect.md` § Flow Outcomes.

---

## Branch Node (Conditional Logic)

Routes flow execution based on if/then/else conditions. Evaluates conditions top-to-bottom; first match wins. If nothing matches, the default "None of the above" outcome fires.

### When to Use in AI Agent Flows

Check an HTTP status code before returning data to the agent. Example: if a patient lookup returns 404, set a status variable that tells the agent "no record found" instead of returning empty data.

**Because there is only one outcome key-set per flow, Branch legs do not return different payloads.** Every leg converges on the same End node, and the same keys are always returned. The pattern that works: each leg sets a **status/error flow variable**, the single Flow Settings key-set returns those variables alongside the data keys, and the agent reads `status` to decide what to say. Data keys on a failure path simply come back empty.

### Configuration

- **Input Variable**: e.g., `$(n3.https.statusCode)`
- **Condition operators** — the official list is **15**: Equals, Not equals, Less than, Greater than, Less than or equals, Greater than or equals, Regular expression (RegEx), Equals ignore case, Contains, Contains ignore case, In, Not in, Starts with, Ends with, Between [source: https://help.webexconnect.io/docs/branch-node]
- **Logical operators**: AND / OR to combine multiple conditions per branch
- **Outcomes**: one exit edge per branch + "None of the above" default + onError

**Output variable:** the node emits `branch.output`, returning `True` or `False` [source: https://help.webexconnect.io/docs/branch-node].

### Example: HTTP Error Routing

```
HTTP Request (Node 3)
  → Branch (Node 4): $(n3.https.statusCode) equals "200"
    → [Yes]                → Evaluate: status = "found"
                             → End
    → [None of the above]  → Evaluate: status = "not_found"
                                       error_message = "No record found"
                             → End
```

Declare `status` and `error_message` in **Flow Settings > Custom Variables**, then assign them inside each leg's Evaluate script (without `var`) or via a **Set Variable transition action**. Both are referenced with no node prefix — `$(status)`, `$(error_message)`.

Flow Settings > Flow Outcomes — ONE key-set, used by every leg:

| Key | Value |
|-----|-------|
| `status` | `$(status)` |
| `error_message` | `$(error_message)` — empty on the success leg |
| `patient_name` | `$(n3.patient_name)` — empty when the lookup failed |

Do **not** try to attach a different payload to each leg — there is nothing to attach it to. The agent branches its reply on `status`.

**Key detail — a strongly-supported inference, not a documented statement**: HTTP 4xx responses are *expected* to go through the HTTP node's **onSuccess** edge (the request completed), not onError. ⚠️ **Cisco never states this outright** — see § Error Handling on HTTP Request Nodes → *4xx/5xx Is Expected to Go Through onSuccess (strongly-supported inference, not a documented statement)* for Cisco's exact wording and why the inference is only strongly-supported. The remedy is correct under either reading: branch on `statusCode` to handle them.

---

## Evaluate Node (JavaScript Execution)

Executes inline JavaScript within a flow. The most powerful data manipulation node — handles string operations, date math, conditional logic, array manipulation. Runs on the JavaScript engine used by Webex Connect. ⚠️ **Unverified:** community knowledge identifies it as **Mozilla Rhino** (Java-based), but the official Evaluate node page names no engine and no ECMAScript level [source: https://help.webexconnect.io/docs/evaluate-node]. The behaviours below are **observed**, not documented: `let`/`const` work for local declarations; arrow functions and template literals do **not**; error messages and type representations (e.g., `org.mozilla.javascript.NativeArray` for arrays) are Rhino-shaped, not V8.

### When to Use in AI Agent Flows

- **Date/time conversion**: Convert UTC timestamps to local time in the flow instead of relying on the LLM (which does this unreliably)
- **String formatting**: Concatenate or reformat values between HTTP nodes
- **Derived values**: Compute values that don't come directly from an API response

### How the Evaluate Node Actually Works

The Evaluate node returns **one result** — the value of the last evaluated expression in the script. It does NOT produce multiple named output variables from `var` declarations.

| Concept | What It Does |
|---------|-------------|
| **Configure Script Output** | Names the single result. It appears in the Output Variables panel as `$(nX.outputName)` and is primarily used for branch routing (e.g., `continue`, `failed`, `valid`) |
| **Branch Name** | Creates a routing path that matches the result string — wire each branch to downstream nodes |
| **Custom flow variables** | How you pass **multiple data values** to downstream nodes. Create them in Flow Settings > Custom Variables, then assign them inside the script (without `var`). Referenced as `$(variableName)` — no node prefix |
| **`+ Add New` button** | Adds another **script block** with its own script, output name, and branch — NOT an "additional output" on the same script |

### Variable Reference Formats

| Source | Format | Example |
|--------|--------|---------|
| Custom flow variables (set in Evaluate script) | `$(variableName)` — no node prefix | `$(oncall_number)`, `$(retryCount)` |
| Script output (last expression) | `$(nX.outputName)` — also matched against Branch Name for routing | `$(n5.continue)` — value is the routing string |
| HTTP Request outputs | `$(nX.https.property)` for built-ins, `$(nX.variableName)` for parsed outputs | `$(n3.https.statusCode)`, `$(n3.oncall_csv)` |

To pass multiple data values from an Evaluate node to downstream nodes, use **custom flow variables** — create them in Flow Settings > Custom Variables, assign them inside the script (without `var`), and reference them as `$(variableName)` with no node prefix. The script output (named via "Configure Script Output") is a single value primarily used for **branch routing**.

**Official docs vs. observed behavior:** The docs state "The Evaluate node script returns the result as a decimal value." In practice, string returns (`"continue"`, `"failed"`) work for branch routing — confirmed by live testing. Writing to custom flow variables from within the script (by assigning without `var`) is observed behavior, not explicitly documented.

### Configuration

- **Script input**: JavaScript code block (engine unnamed by Cisco; observed behaviour — `let`/`const` supported, no arrow functions or template literals — see the engine caveat above)
- **Configure Script Output**: names the single result — appears in Output Variables panel and used for branch routing
- **Branch Name**: routing path that matches the result — wire to downstream nodes
- **Variable access**: use `$(variableName)` syntax inside the script to read flow variables — case-sensitive. ⚠ **Two forms appear in this file and they have never been reconciled.** This line asserts the `$( )` form; the worked example in § Example: Loop with retryCount (Sequential Dialing Pattern) reads and writes the same custom flow variables **bare** — `Number(retryCount)`, `oncall_number = numbers[0]...` — and is backed by live-run test evidence in that same section (`_wfnoderesult`, `oncall_number`, `retryCount` all populated). Do **not** treat either form as disproven: check both in your own tenant, and prefer the tested example's bare form for custom flow variables. (Values pulled from *another node's* output are a separate case — those are quoted and wrapped in the examples: `var csv = "$(n4.oncall_csv)";`.)

### Custom Variable Prerequisite

Per the official docs: a custom variable must be **referenced in one or more preceding nodes** in the flow (in the Configuration tab or Transition Actions tab) for its value to populate during flow execution. If the Evaluate script reads a custom variable that hasn't been referenced upstream, it may arrive empty.

### Testing the Script

The Evaluate node has a test panel (right side of the script editor) with **Variable Name / Value** fields. Add entries for each `$(variableName)` your script references so you can run the script in isolation before deploying.

### Built-in Libraries (include via `includeJs(libraryName)`)

| Library | Functions |
|---------|-----------|
| `imi_general` | typeof, length, URL encode/decode |
| `imi_base64` | base64 encode/decode |
| `imi_strings` | indexOf, replace, slice, substring |
| `imi_array` | concat, indexOf, isArray, join, push, reverse, splice |

### Gotchas and Constraints

**Exit paths — ⚠️ observed, not documented.** The official Evaluate node page describes only a generic "Node Outcomes" panel and **names no outcomes at all** [source: https://help.webexconnect.io/docs/evaluate-node]. The three outcomes below come from project observation; confirm the exact edge names in the node's Node Outcomes panel before wiring:
1. Named success branches (matching the script's output value)
2. `onInvalidChoice` — code executes successfully but output matches no configured branch name (⚠️ **unverified name**)
3. `onError` — code execution fails (syntax error, runtime exception)

Wire `onInvalidChoice` to a fallback path to avoid silent flow failures when the script returns an unexpected value.

**⚠️ Unverified: two success branches cannot connect to the same downstream node.** This restriction is **not stated anywhere in the official Webex Connect documentation** — it is a project observation. If you hit it, the workaround is a "passthrough" Evaluate between them, or restructuring to use a single branch name.

**Node output variables are read-only inside Evaluate.** Modifying a variable that came from a previous node's output (like `$(n3.statusCode)`) inside the script does NOT change its value downstream. Only custom flow variables (assigned without `var`/`let`/`const`) persist changes to flow scope.

**Variable shadowing causes errors.** If a flow already has a variable named `email` (from a webhook input or previous node), writing `let email = email;` or `const email = $(n2.email);` causes a scope clash. Use a different local name:
```javascript
const userEmail = "$(n2.email)";
```

**On-Leave workaround for scoping:** If you need a node's output variable available in an Evaluate but hit scoping issues, use the preceding node's **Transition Actions > On-Leave > Set Variable** to copy the value into a custom flow variable before the Evaluate node executes.

**Library invocation pattern:** Import with lowercase, reference with UPPERCASE:
```javascript
includeJs("imi_strings");
var idx = IMI_STRINGS.indexOf("hello world", "world");
```

### Example: Loop with retryCount (Sequential Dialing Pattern)

This pattern uses custom flow variables (`oncall_number`, `retryCount`, `maxRetryCount`) to loop through a list of phone numbers. One Evaluate + one Call Patch replace the old 3-Call-Patch chain.

**Custom flow variables (create in Flow Settings > Custom Variables):**
- `retryCount` — init `0`
- `maxRetryCount` — init `2`
- `oncall_number` — init empty

**Script:**
```javascript
var csv = "$(n4.oncall_csv)";
var numbers = csv.split(",");

if (Number(retryCount) <= Number(maxRetryCount)) {
    if (Number(retryCount) === 0) {
        oncall_number = numbers[0] ? numbers[0].trim() : "";
    }
    if (Number(retryCount) === 1) {
        oncall_number = numbers[1] ? numbers[1].trim() : "";
    }
    if (Number(retryCount) === 2) {
        oncall_number = numbers[2] ? numbers[2].trim() : "";
    }
    retryCount = Number(retryCount) + 1;
    "continue";
} else {
    "failed";
}
```

**Configure Script Output:** `continue`
**Branch Names:** `continue` (wire to Call Patch), `failed` (wire to fallback TTS)

**Test evidence (from live flow execution):**
```json
{
  "_wfnoderesult": "continue",
  "oncall_number": "9103915567",
  "retryCount": "1.0",
  "_wferrorstatus": "3003",
  "_wferrordesc": "result : continue"
}
```

- `_wfnoderesult` = the script output (last expression) — used for branch routing
- `oncall_number` = custom flow variable set by the script — referenced downstream as `$(oncall_number)`
- `retryCount` = custom flow variable incremented by the script
- `_wferrorstatus: 3003` — **Cisco's published definition:** on the Evaluate node, `3003` is `invalid result`, "Returned when an invalid results are produced" [source: https://help.webexconnect.io/docs/references-flowbuilder-response-codes § Evaluate]. Treat it as a signal that the node produced something the platform considered invalid.
  - **Separate observation from one live run (not a definition):** in the single execution captured above, the flow continued through the `continue` branch with `3003` present, so in that run the code was non-fatal. One run is not evidence that `3003` is safe to ignore — if you see it, check the script's output against the configured Branch Names before shipping.

### Example: UTC to Eastern Time Conversion

```javascript
var utcTime = new Date("$(n3.scheduled_at)");
var jan = new Date(utcTime.getFullYear(), 0, 1);
var jul = new Date(utcTime.getFullYear(), 6, 1);
var stdOffset = Math.max(jan.getTimezoneOffset(), jul.getTimezoneOffset());
var isDST = utcTime.getTimezoneOffset() < stdOffset;
var offset = isDST ? 4 : 5;
utcTime.setHours(utcTime.getHours() - offset);
var etTime = utcTime.toISOString();
```

**Note:** This JavaScript runs on the Connect server (not in the caller's browser), so `getTimezoneOffset()` reflects the server's timezone. If the server is UTC, use a simpler approach — hardcode the offset but document which months require -4 vs -5:

```javascript
var month = new Date("$(n3.scheduled_at)").getUTCMonth();
var offset = (month >= 2 && month <= 10) ? 4 : 5;
var utcTime = new Date("$(n3.scheduled_at)");
utcTime.setHours(utcTime.getHours() - offset);
var etTime = utcTime.toISOString();
```

This replaces the unreliable "tell the LLM to subtract 5 hours" pattern with a deterministic conversion. For precise DST boundaries, use an RPC function in the database instead.

---

## Error Handling on HTTP Request Nodes

### Exit Paths

Every HTTP Request node has three exit edges:

| Edge | Trigger | Visual |
|------|---------|--------|
| **onSuccess** | HTTP request completed (ANY status code, including 4xx/5xx) | Green |
| **onError** | Connection failure, invalid input, internal error | Red |
| **onTimeout** | No response within configured timeout | Orange |

### 4xx/5xx Is Expected to Go Through onSuccess (strongly-supported inference, not a documented statement)

A `404 Not Found` or `500 Server Error` is expected to exit via **onSuccess**, not onError — the request completed, it just returned an error status.

⚠️ **Cisco never states this outright.** The HTTP Request node page says only: "**onSuccess** — the flow exits through this node when the HTTP request is successfully executed" and "**onError** — the flow exits through this node when the HTTP request cannot be processed due to invalid input" [source: https://help.webexconnect.io/docs/http-request-node]. That wording is *consistent with* the behaviour above (a 404 is a successfully executed request; "invalid input" is a request-construction failure) but does not assert it. Treat it as a strongly-supported inference.

**The remedy is correct either way:** wire a **Branch node** after the HTTP node and check `$(nX.https.statusCode)`. Branching on the status code handles both readings, so build it regardless of which edge fires.

### Timeout Configuration

- **Connection Timeout**: max 20,000ms
- **Request Timeout**: max 20,000ms

Keep both well under 20s to leave headroom within the 30-second agent flow timeout.

### Recommended Error Pattern for Agent Flows

One key-set per flow, so both legs return the same keys and differ only in the **values** they set:

```
HTTP Request → Branch (statusCode == 200?)
  → [Yes] → set status = "ok"                                    → End
  → [No]  → set status = "error",
                error_message = "Could not find record"          → End
```

Set the variables with a **Set Variable transition action** (see Transition Actions below) on each leg's next node, or with a small Evaluate node. Then map `status` and `error_message` as keys in **Flow Settings > Flow Outcomes > Last Execution Status**, alongside the data keys. The agent branches its reply on `status`; the data keys arrive empty on the error leg.

Do NOT use retry loops — they'll exceed the 30-second timeout. Fail fast and let the agent handle it conversationally.

---

## Transition Actions (Set Variable / Debug Logging)

Every node has a **Transition Actions** tab with On-enter and On-leave events. These let you capture or log values without adding a standalone node.

### Set Variable

Capture a node output into a custom flow variable. Useful for renaming or storing intermediate values.

- Use the **+Add** control to "add and set multiple custom variable - values" in one operation [source: https://help.webexconnect.io/docs/transition-actions]
- ⚠️ **Unverified observation:** a previous version of this doc stated a "max 30 variables per Set Variable operation" limit. **No quantity limit is documented anywhere on the Transition Actions page.** Do not design around 30 as a hard cap, and do not treat it as verified
- Variables are case-sensitive

### The Four Transition Actions

Cisco documents **four** actions, not three [source: https://help.webexconnect.io/docs/transition-actions]:

| Action | Purpose | Requirement |
|--------|---------|-------------|
| **Set Variable** | Add and set one or more custom variable values (see above) | Custom variable must exist |
| **[DEBUG] Log all Flow Variables to Transaction Log** | Snapshot all variables to the transaction log | "Descriptive logging" enabled in Flow Settings |
| **[DEBUG] Log a Value to Transaction Log** | Log a specific variable with a Log ID (integer > 1000) | Same |
| **Log a Value to Logbook** | Record data into an existing logbook | Requires **logbook mapping in Flow Settings** |

> ⚠️ **PII warning (Cisco's own):** debug logging "is not stored in an encrypted format" and must not contain sensitive or personally identifiable information (PII) [source: https://help.webexconnect.io/docs/transition-actions]. Never log a patient name, phone number, email address, account number, or anything else that identifies a person.

### When to Use in AI Agent Flows

- Capture an HTTP response field into a named variable for use in a later Branch condition
- Debug a flow that's returning unexpected data — enable descriptive logging temporarily, then check transaction logs

---

## Data Parser Node

Extracts fields from JSON or XML data using JSONPath. A standalone version of the HTTP Request node's built-in output variable parsing.

### When to Use

Only when the HTTP node's built-in Parse button can't handle the response structure — e.g., deeply nested JSON, or re-parsing data already stored in a variable.

### Configuration

1. **Import Data From**: variable containing JSON (e.g., `$(n4.https.responseBody)`)
2. **Input Data Format**: JSON or XML
3. **Sample Body**: paste representative response, click **Parse**
4. Select fields to extract, each gets a JSONPath (e.g., `$.data.nested.field`) and output variable name

> **Footnote — Cisco's own docs are inconsistent about this variable name.** The HTTP Request node page writes it as `https.responseBody`; the Data Parser page's worked example writes the same thing as `$(n4.http.responsebody)` — a different prefix (`http` vs `https`) *and* different casing. This doc uses `$(n4.https.responseBody)`, matching the HTTP Request node page, which is the authoritative owner of that variable. If the variable picker in your tenant shows `http.responsebody`, that is the same value, not a defect in this doc — copy whichever form the picker gives you [sources: https://help.webexconnect.io/docs/http-request-node, https://help.webexconnect.io/docs/data-parser-node].

For typical REST API responses, the HTTP node's built-in parsing is sufficient. Reach for this node only when it isn't.

---

## Data Transform Node

Converts data between **JSON and XML** using Velocity Template Language (VTL) [source: https://help.webexconnect.io/docs/data-transform-node].

### Configuration

| Field | Purpose |
|-------|---------|
| **Input Variable** | The variable holding the data to transform |
| **Input Data Format** | JSON or XML |
| **Define Template (Using VTL)** | The Velocity template that produces the output |

**Output variable:** `dataTransform.output`.

> **If the data came from an HTTP Request node, it is already stringified by Webex Connect.** Account for that when writing the template — you are not starting from a live object.

---

## Page Connector Node

Flows can be split across **pages**. You create a page with the **'+'** control next to the main flow tab, and a Page Connector node moves execution from one page to another [source: https://help.webexconnect.io/docs/page-connector-node].

Two rules matter:

1. **You must connect the Page Connector node to the target node.** Cisco: "Otherwise, the flow may not execute properly."
2. **Flow variables are NOT automatically shared across pages.** Cisco: "You can use custom variables to selectively share the relevant variables across various pages." If a value has to survive a page hop, it must be a **custom variable** — a node output variable will not follow you across the boundary.

---

## Delay Node

Pauses flow execution for a configured number of seconds [source: https://help.webexconnect.io/docs/delay-node].

**Output variable:** `delay.waitTime`.

**Outcomes:** `onTimeout` (yellow — this is the *normal* continuation path, not a failure) and `onError` (red).

> **The delay is a floor, not an exact figure.** Cisco: "When you configure 'x' seconds of delay using the delay node, the processing is delayed by at least 'x' seconds. It can sometimes be higher depending on the number of active flow execution sessions across all services within your tenant."

**Not for AI agent action flows.** Delay is one of the Waiting Nodes Cisco restricts in AI agent fulfillment flows because it can push execution past the 30-second limit.

---

## Receive Node

Waits for an inbound message or event before continuing [source: https://help.webexconnect.io/docs/receive-node].

| Field | Purpose |
|-------|---------|
| **Max Timeout** | "Specifies duration in seconds that the node waits for incoming messages/events. If no response arrives within this period, the flow exits via the `ontimeout` edge." |

A single Receive node can listen on **multiple channels and custom events** at once — you do not need one node per channel.

**Not for AI agent action flows.** Receive is one of the Waiting Nodes Cisco restricts in AI agent fulfillment flows, unqualified — there is no "one Receive is fine" carve-out.

---

## Social Hour Check Node

Checks whether the current time falls inside configured social hours [source: https://help.webexconnect.io/docs/social-hour-check-node].

### Two policies — only one of them waits

| Policy | Behaviour |
|--------|-----------|
| **Wait for next available social hours** | **Blocks** until the next social-hour window opens. This is the policy that makes the node unsafe inside a 30-second AI agent flow |
| **Branch requests not in social hours** | **Exits immediately** through the `notInSocialHour` edge. Nothing blocks |

Because the second policy never waits, the node is **not unconditionally unsafe** — the risk is specific to the waiting policy. Cisco's restriction on Waiting Nodes in AI agent flows still lists Social Hour, so treat the blocking policy as prohibited there and confirm the branch-only policy in your tenant before relying on it.

### Four outcomes

| Edge | Colour | Meaning |
|------|--------|---------|
| `onSuccess` | Green | Inside social hours |
| `nextSocialHour` | Yellow | Waiting for the next window (waiting policy only) |
| `notInSocialHour` | Red | Outside social hours, branch-immediately policy |
| `onError` | Red | Node error |

---

## Call Workflow Node

Invokes another flow from the current one [sources: https://help.webexconnect.io/docs/call-workflow-node, https://help.webexconnect.io/docs/calling-a-flow-from-another-flow].

### Configuration

| Field | Value |
|-------|-------|
| **Workflow Name** | Dropdown — the flow to invoke |
| **Node Type** | `All` / `Start` / `End` |
| **Node Name** | The specific node to enter at |

Node Type supports both a **Start invocation** (enter the child flow at its beginning) and an **Intermediate invocation** (enter at a named node).

### Constraint: only custom variables cross the boundary

Cisco states that "when called, the full context of the current flow along with the session data is passed to the newly invoked flow" — **but** also that "only Custom Variables from parent flow are reference-able in the child flow."

In practice: a node output variable in the parent (`$(n3.https.responseBody)`) is **not** addressable in the child. Copy anything the child needs into a **custom variable** first, using a Set Variable transition action in the parent.

### Trap: "Channel Bean is null"

A parent flow with **no channel nodes** that invokes a child flow which **does** have channel nodes may fail with a `Channel Bean is null` error. Cisco's workaround: add "a placeholder Send Node in the parent flow and map it with the relevant channel asset during publishing."

**Not for AI agent action flows.** Call Workflow is one of the Waiting Nodes Cisco restricts in AI agent fulfillment flows.

---

## Variable Scoping

### Flow-level Custom Variables

- Created in **Flow Settings > Custom Variables** tab or inline on any node
- Available throughout the entire flow
- Can be "externalized" to defer value assignment until flow launch

### No Org-level Secrets Manager

Webex Connect does NOT have a built-in org-level variable store or secrets manager. Options for API keys:

| Approach | Trade-off |
|----------|-----------|
| Hardcode in each flow | Simple but duplicated; fine for demo |
| Externalized variables | Set per flow at launch; better for multi-env |
| Node Runtime Authorization ⚠️ **unverified** | OAuth/API key configs stored at service level, selectable in HTTP node. **No page in the official Webex Connect documentation uses the term "Node Runtime Authorization"**, and the HTTP Request node page documents headers and proxy settings but no service-level auth store. Confirm this exists in your tenant before designing around it [source checked: https://help.webexconnect.io/docs/http-request-node] |

---

## SMS Node (Side-Effect Notifications)

Sends an SMS message to a customer via the configured SMS gateway. In AI agent flows, use it as a **side effect** — fire-and-forget confirmation after the core API work is done, before returning data through Flow Outcomes.

### When to Use in AI Agent Flows

After an HTTP POST creates a record (appointment, order, etc.), drop an SMS node between the last HTTP node and the End node to send a confirmation text. The agent still returns structured data to the caller; the SMS is a bonus notification.

```
Trigger → HTTP GET (lookup) → HTTP POST (create) → SMS → End
```

### Required Configuration

| Field | Value | Notes |
|-------|-------|-------|
| **Destination Type** | `msisdn` or `Customer Id` | `msisdn` = mobile number in international format. `Customer Id` = the master ID used for cross-channel communication |
| **Destination** | Variable from flow (e.g., `$(n2.aiAgent.phone_number)`) | ⚠ **The `aiAgent` path segment is not documented in official docs** — the AI Agent fulfillment page shows no variable-syntax example at all. Use the variable picker to confirm the exact format your tenant produces; **do not type this path from memory** [`webex-connect.md` § Variable Picker Syntax → Format]. **Country codes are mandatory for MSISDN numbers** — omitting one causes delivery failures. The `+E.164` format applies to the "To" field only if E.164 is enabled |
| **From Number** | Select from dropdown | Pre-configured sender ID in your Connect tenant |
| **Message Type** | `Text` | Options are `Text`, `Flash`, `Binary`, `Unicode`, `Template`. `Template` additionally requires variable configuration |
| **Message** | Body text with variables | Use `\n` for line breaks; insert variables via picker |

**Character limit — two different numbers, do not confuse them** [source: https://help.webexconnect.io/docs/sms-node]:

| | Value | What it is |
|---|---|---|
| **Hard cap** | **4000 characters** | The platform limit. "You can send short messages up to 4000 characters." / "The message should not be longer than 4000 characters." Exceeding it is a platform error |
| **Recommendation** | **below 450 characters** | Cisco's own deliverability guidance, not a limit: "We recommend that you keep SMS messages below 450 characters for better deliverability and user experience." Going over 450 is allowed and will send |

A message of, say, 900 characters is legal (under the 4000 cap) but outside the recommendation — it will send, with a deliverability trade-off.

### Additional SMS Node Fields

None of these are required for the side-effect confirmation pattern above, but all are documented settings on the node [source: https://help.webexconnect.io/docs/sms-node]:

| Field | Purpose |
|-------|---------|
| **Correlation ID** | Unique message identifier for tracking; returned with delivery reports |
| **Notify URL** | Optional webhook that receives delivery reports for this message |
| **Enable Notify URL Auth** | Checkbox — adds authentication to the Notify URL callback |
| **Callback Data** | Additional data sent along with delivery reports |
| **Extra Parameters** | Custom attributes beyond the standard payload |
| **SmartLink** | A single URL containing multiple offers, with an optional validity period |
| **Shortened Links** | Automatically shortens HTTPS URLs (excludes SmartLinks); supports click tracking via webhook |
| **Expiry** | "You can define the maximum time allocated for the execution of this node." This is the field that drives the `onTimeout` edge |

### Critical: Wait For Setting

The SMS node has two execution modes under **Advanced Options**:

| Mode | Behavior | Use in agent flows? |
|------|----------|---------------------|
| **Gateway Submit** | Node completes when the message enters the gateway queue | **Yes** — recommended |
| **Delivery Report** | Node waits for carrier delivery confirmation | **No** — blocks until the carrier confirms |

**Always set Wait For to "Gateway Submit"** in AI agent flows. Delivery Report mode blocks the flow waiting for carrier confirmation.

⚠️ **The two Wait For options are documented; the latency numbers are not.** Cisco's SMS node page confirms both modes exist but publishes **no** latency figures for either [source: https://help.webexconnect.io/docs/sms-node]. The characterisation "seconds to minutes, will timeout in an agent flow" is this project's own inference from the 30-second AI agent flow limit, not a Cisco statement. The recommendation stands — a mode that waits on a third-party carrier is the wrong shape for a 30-second budget — but do not quote a specific delay to anyone.

⚠️ **The exit *timing* is inference too.** Cisco documents the queuing mechanism but never says the node exits *immediately* or *as soon as* the message enters the queue — the exact exit timing is unspecified, which is why the table above says "when", not "as soon as" [`connect-sms.md` § Wait For Setting, which owns this hedge; `docs/tests/findings/outbound-sms-findings.md` #15].

### Example: Appointment Confirmation SMS

After `create_appointment` returns a confirmation number, send a text before the End node (the return payload itself is set in Flow Settings > Flow Outcomes):

**Message body:**
```
Your booking is confirmed.\nConfirmation: $(n5.confirmation_number)\nDate: $(n5.scheduled_at)\nPlease arrive 15 minutes early.
```

- `n5` references the HTTP POST node that created the appointment — adjust node number via variable picker
- The SMS fires on the HTTP node's **onSuccess** edge, the same path that continues to End
- If SMS fails, wire its **onError** edge directly to the End node so the agent still gets the appointment data

### Exit Edges

| Edge | Trigger |
|------|---------|
| **onSuccess** | Message accepted by gateway (Gateway Submit mode) |
| **onError** | Invalid destination, misconfigured sender, gateway rejection |
| **onTimeout** | Expiry threshold exceeded (only relevant in Delivery Report mode) |

> ⚠ **UNRESOLVED — the casing of the timeout event. Do NOT normalise it.**
>
> Cisco's own doc set spells this event **three different ways**, and no page states which is authoritative:
>
> | Spelling | Where |
> |---|---|
> | `onTimeOut` | Cisco's exception-handling page — **section heading** |
> | `ontimeout` | Cisco's exception-handling page — **body text**: *"The 'ontimeout' event occurs when the time (in seconds) mentioned in the Timeout field has been exceeded."* |
> | `onTimeout` | HTTP Request node page **and** RCS Message node page |
>
> Cisco also never states whether the exception-handling *event* is even the same thing as a node *exit path*. The spelling used in the tables above (`onTimeout`) is therefore **left as-is deliberately** — an earlier pass queued a rewrite to `onTimeOut` and it was **disproven**. Confirm the exact edge label in the node's Node Outcomes panel in your tenant before writing a condition against it (three-casing conflict verified 2026-07-27).

---

## Email Node (Side-Effect Notifications)

Sends an email to a recipient via the configured email asset. In AI agent flows, use it as a **side effect** — fire-and-forget confirmation after the core API work is done, before returning data through Flow Outcomes.

### When to Use in AI Agent Flows

After an HTTP POST creates a record (appointment, order, etc.), drop an Email node between the last HTTP node and the End node to send a confirmation email with details the patient can reference later (confirmation number, prep instructions, location info).

```
Trigger → HTTP GET (lookup) → HTTP POST (create) → Email → End
```

### Required Configuration

| Field | Value | Notes |
|-------|-------|-------|
| **Destination Type** | `Email ID` | Use Email ID for direct address targeting |
| **Destination ID** | Variable from flow (e.g., `$(n3.patient_email)`) | Supports multiple comma-separated addresses; use variable picker. **The local part** — everything before the `@` — **can only contain 7-bit ASCII characters** [source: https://help.webexconnect.io/docs/email-node] |
| **From Email** | *(auto-populated)* | Pulled from the email app asset config; field is disabled on the node |
| **From Name** | Display name (e.g., `Acme Services`) | Optional but recommended for professional appearance |
| **Subject** | Subject line with variables | e.g., `Appointment Confirmed - $(n5.confirmation_number)` |
| **Email Type** | `Text`, `Template`, or `HTML` | Text for simple confirmations; `Template` or `HTML` for branded output. Selecting `Template` or `HTML` surfaces a **Fallback Text** field |
| **Template Type** | `Full template` or `Partial template` | Only appears when Email Type is `Template` |
| **Message** | Body content with variables | Insert variables via picker; use HTML markup if Email Type is HTML |

### Optional Fields

| Field | Notes |
|-------|-------|
| **ReplyTo Email** | Where replies go (e.g., a no-reply or support address) |
| **CC / BCC** | Comma-separated addresses; useful for sending a copy to the clinic |
| **Attachments** | Up to 5 files, 10 MB total; requires MIME type, name, and media URL. **39 MIME types are supported** — including doc/docx, pdf, xls/xlsx, ppt/pptx, zip, mp3, jpeg/jpg, png. All 39 are enumerated in `connect-email.md` § Supported Attachment MIME Types, which owns this list — do not assume an unlisted type is accepted |
| **Dynamic attachments** | Supplied as a JSON payload: `"attachmentType": 2` for a media URL, `"attachmentType": 1` for base64. **Attachment URLs must end with a file extension.** Cisco recommends uploading through Media Manager |
| **List Unsubscribe URL** | Unsubscribe link surfaced by the recipient's mail client |
| **Unsubscribe Mail To Address** | Address used for mailto-style unsubscribe |
| **Unsubscribe Email Subject** | Subject line pre-filled on the unsubscribe email |
| **Enable Link Tracking** | Link clicks are reported via outbound webhook as a "Clicked" delivery receipt |
| **Track Opens** | Monitors email open events |
| **SMTP Headers** | Cc, Bcc, In-Reply-To — available when SMTP-based sending is enabled |

All fields in this section: [source: https://help.webexconnect.io/docs/email-node].

### Output Variables

| Variable | Description |
|----------|-------------|
| `send.sentDateTime` | Timestamp the message was sent |
| `send.gatewayTid` | Gateway transaction ID |
| `send.deliveryStatusDescription` | Human-readable delivery status |
| `send.deliveryStatusCode` | Delivery status code |
| `send.response_data` | Response data returned by the gateway |
| `send.response_interactive` | Interactive-response payload |

[source: https://help.webexconnect.io/docs/email-node]

### Sending Route: AWS SES vs SMTP

The node sends via **AWS SES** or **SMTP**, and the Notify Status values differ by route [source: https://help.webexconnect.io/docs/email-node]:

| Route | Notify Status values |
|-------|----------------------|
| **AWS SES** | Sent, Delivered, Read, Bounce, Spam, Rejected, Answered — default bounce-list retention is seven days |
| **SMTP** | Sent, Failed — only these two |

If you are wiring logic to a status like `Read` or `Bounce`, confirm the asset uses SES; on an SMTP asset those statuses never arrive.

### Critical: Wait For Setting

The Email node has two execution modes under **Advanced Options** — identical pattern to SMS:

| Mode | Behavior | Use in agent flows? |
|------|----------|---------------------|
| **Gateway Submit** | Node completes when the message enters the email gateway queue | **Yes** — recommended |
| **Delivery Report** | Node waits for delivery/bounce confirmation | **No** — blocks until delivery is confirmed |

**Always set Wait For to "Gateway Submit"** in AI agent flows. Delivery Report mode blocks the flow waiting for email delivery confirmation.

⚠️ **The two option *labels* above are NOT documented on the Email node page — they are carried over from the SMS node.** Cisco's Email node page says only: *"Before proceeding to the next node, you can choose to wait for a delivery report. You can also limit the maximum wait time by defining it in the Timeout field."* It names **no node events at all**, and a strict search confirms the string **"Gateway Submit" does not appear on it** (verified 2026-07-27) [source: https://help.webexconnect.io/docs/email-node]. "Gateway Submit" is a documented `Wait For` option on the **SMS node page only** [source: https://help.webexconnect.io/docs/sms-node]. What Cisco *does* document for Email is the choice to wait for a delivery report and a **Timeout** field bounding that wait — so the recommendation below is sound, but **confirm the exact option labels in the node's Advanced Options in your tenant** rather than assuming they read the same as SMS.

⚠️ **Same latency caveat as SMS:** **no latency figures are published for either mode** [source: https://help.webexconnect.io/docs/email-node]. "Seconds to minutes, will timeout" is this project's inference from the 30-second agent flow limit, not a Cisco statement.

### Example: Appointment Confirmation Email with Prep Instructions

After `create_appointment` returns a confirmation number and `get_test_info` returned prep instructions, send an email before the End node (the return payload itself is set in Flow Settings > Flow Outcomes):

**Subject:**
```
Appointment Confirmed - $(n5.confirmation_number)
```

**Email Type:** HTML

**Message body:**
```html
<p>Hi $(n3.patient_first_name),</p>
<p>Your booking has been confirmed.</p>
<ul>
  <li><strong>Confirmation:</strong> $(n5.confirmation_number)</li>
  <li><strong>Date:</strong> $(n5.scheduled_at)</li>
  <li><strong>Test:</strong> $(n4.test_name)</li>
</ul>
<p><strong>Preparation:</strong> $(n4.prep_instructions)</p>
<p>Please arrive 15 minutes early with your insurance card and photo ID.</p>
```

- Node numbers reference earlier HTTP nodes — adjust via variable picker
- The Email fires on the HTTP POST node's **onSuccess** edge, the same path that continues to End
- If Email fails, wire its **onError** edge directly to the End node so the agent still gets the appointment data

### Exit Edges

| Edge | Trigger |
|------|---------|
| **onSuccess** | Message accepted by email gateway (Gateway Submit mode) |
| **onError** | Invalid destination, misconfigured email asset, gateway rejection |
| **onTimeout** | Expiry threshold exceeded (only relevant in Delivery Report mode) |

---

## RCS Messaging (Side-Effect Notifications)

Sends rich, app-like messages (rich cards with images, descriptions, and interactive buttons) to Android devices via RCS Business Messaging. RCS requires a two-node pattern: first check whether the recipient's device supports RCS, then send the message — with an SMS fallback if it doesn't.

### When to Use in AI Agent Flows

After an HTTP POST creates a record (appointment, order, etc.), use the RCS Capability + RCS Message nodes to send a rich card confirmation with interactive buttons (e.g., "View Details", "Cancel Appointment") before returning data through Flow Outcomes. Always include an SMS fallback path — not every device supports RCS.

```
Trigger → HTTP GET → HTTP POST → RCS Capability → Branch (enabled?)
  → [Yes] → RCS Message → End
  → [No]  → SMS → End
```

### Node 1: RCS Capability Check

Verifies whether the recipient's device can receive RCS messages.

| Field | Value | Notes |
|-------|-------|-------|
| **Mobile Number** | Variable from flow (e.g., `$(n2.aiAgent.phone_number)`) | ⚠ `aiAgent` is **undocumented** — copy the path out of the variable picker, never type it from memory [`webex-connect.md` § Variable Picker Syntax → Format]. Must include country code |
| **Force Refresh** | Set it to `false` explicitly — **the UI defaults to `true`** | `false` = 7-day cached lookup (near-instant). `true` = live network check (3–6s latency — avoid in agent flows). Because the default is the slow option, leaving this field alone is the wrong choice in an AI agent flow |
| **Carrier** | *(leave blank)* | An **integer**, not a string carrier code — the UI placeholder is `302`. Set only if you know the customer's carrier [`connect-rcs.md` § RCS Capability Node] |

**Key output variables:**

| Variable | Purpose |
|----------|---------|
| `rcs.enabled` | Boolean — `true` if device has any RCS support |
| `rcs.version` | `up1` (basic), `up2` (rich cards/carousels), or `disabled` |
| `rcs.capabilties.richcard` | Boolean — `true` if device supports rich cards. ⚠️ **Verified MISSPELLED on the platform** (`capabilties` — missing the "i"). Do not "correct" it |

> ⚠️ **Platform typo warning.** The RCS Capability node emits capability variable names that are **misspelled on the platform**, and inconsistently so — `rcs.capabilties.richcard` drops an "i" while `rcs.capabilites.richcardCarousel` and `rcs.capabilites.dialPhoneNumber` use a *different* typo. `rcs.capabilities.openUrl` is spelled correctly. **Do not type these by hand** — run the Capability node once and copy the exact names out of the variable picker. Typing the correctly-spelled version produces a Branch condition that silently never matches. Full table and per-variable verification status in `connect-rcs.md § RCS Capability Node → Output Variables`.

**Exit edges:** `onSuccess` (check completed) · `onError` (lookup failed)

### Node 2: Branch on RCS Support

After the capability check, add a Branch node to route the flow.

- **Input Variable**: `$(nX.rcs.enabled)` (where `nX` is the RCS Capability node)
- **Condition**: Equals `true` → route to RCS Message node
- **None of the above** → route to SMS fallback

For rich card support specifically, branch on `$(nX.rcs.capabilties.richcard)` equals `true` — note the platform misspelling flagged above, and copy the name from the variable picker rather than typing it.

### Node 3: RCS Message

Sends the rich message to the recipient.

| Field | Value | Notes |
|-------|-------|-------|
| **Destination Type** | `MSISDN` | Mobile number |
| **Destination** | Variable from flow (e.g., `$(n2.aiAgent.phone_number)`) | ⚠ `aiAgent` is **undocumented** — copy the path out of the variable picker, never type it from memory [`webex-connect.md` § Variable Picker Syntax → Format]. Must include country code |
| **Message Type** | `Rich Card` | Also supports: Text, File, Carousel Card, Typing Indicator |

**Rich Card fields:**

| Field | Value | Notes |
|-------|-------|-------|
| **Card Orientation** | `Vertical` | Or Horizontal; Vertical is standard for confirmations |
| **Media Height** | `Medium` | Short, Medium, or Tall |
| **Media URL** | Image URL (e.g., company logo or location photo) | Max 2048 characters |
| **Title** | Card title with variables (e.g., `Appointment Confirmed`) | Max 200 characters |
| **Description** | Card body with variables | Max 2000 characters; insert variables via picker |
| **Suggestions** | Up to 4 interactive buttons per card | See suggestion types below |

**Suggestion types for buttons:**

| Type | Use Case |
|------|----------|
| **Reply** | Quick-reply text back to agent (e.g., "Confirm"). ⚠ This file previously called it "Simple Reply"; the confirmed name is **Reply** [`connect-rcs.md` § Suggestion Types; `docs/tests/findings/outbound-rcs-findings.md` #20, vetted 2026-04-17] |
| **Open URL** | Link to a web page (e.g., appointment portal) |
| **Dial Phone** | Tap to call the location |
| **View Location** | Open map to location address |
| **Calendar Event** | Add appointment to device calendar |

### Critical: Wait For Setting

Same pattern as SMS and Email — under **Advanced Options**:

| Mode | Behavior | Use in agent flows? |
|------|----------|---------------------|
| **Gateway Submit** | Node completes when the message enters the gateway queue | **Yes** — fast, stays under 30s |
| **Delivery Report** | Node waits for carrier delivery confirmation | **No** — will timeout |

**Always set Wait For to "Gateway Submit"** in AI agent flows.

### Timeout Warning

The two-node RCS pattern (Capability check → Branch → RCS Message or SMS) adds more nodes than a simple SMS side effect. All of them must complete within the 30-second agent flow timeout. **Set `Force Refresh` to `false` on the Capability node** — cached lookup is near-instant versus 3–6s for a live check, and the UI default is `true`, so this is an active change, not a confirmation of the default. If you're already chaining multiple HTTP nodes before the RCS side effect, test the full flow end-to-end to confirm it stays under 30 seconds.

*(Provenance: the 7-day cache window, the 3–6s live-check latency, and the `true` default all come from the RCS findings review — the same evidence behind `connect-rcs.md` and `outbound-rcs.md`. They are outside the scope of the Webex Connect documentation crawl, which covered the core node pages only.)*

### Example: Appointment Confirmation Rich Card

After `create_appointment` returns a confirmation number, send a rich card before the End node (the return payload itself is set in Flow Settings > Flow Outcomes):

**Message Type:** Rich Card

**Card Orientation:** Vertical · **Media Height:** Medium

**Title:**
```
Appointment Confirmed
```

**Description:**
```
Confirmation: $(n5.confirmation_number)
Date: $(n5.scheduled_at)
Test: $(n4.test_name)

Preparation: $(n4.prep_instructions)

Please arrive 15 minutes early with your insurance card and photo ID.
```

**Suggestions:**
1. **Open URL** — text: `View Details`, URL: `https://example.com/appointments`
2. **Dial Phone** — text: `Call Clinic`, phone: `+19105551234`
3. **Calendar Event** — text: `Add to Calendar`, title: `Lab Appointment`, start: `$(n5.scheduled_at)`

- Node numbers reference earlier HTTP nodes — adjust via variable picker
- Wire the RCS Message node's **onError** edge directly to the End node so the agent still gets the appointment data even if the RCS message fails
- The SMS fallback branch should send the same core information (confirmation number, date, prep instructions) as plain text

### Exit Edges

> **Owner: `connect-rcs.md` § Exit Paths.** Reproduced here so this page works standalone; the channel reference wins on any disagreement.

The RCS Message node has **seven** exit paths, not three:

| Edge | Trigger |
|------|---------|
| **onSuccess** | Message sent successfully |
| **onSubmit** | The **Wait For: Gateway Submit** condition was met |
| **onDeliveryReportSuccess** | Delivery confirmed (Delivery Report mode) |
| **onError** | Invalid destination, RCS not supported (if capability check was skipped), gateway rejection |
| **onDeliveryReportFail** | Delivery report returned failure |
| **onPolicyFail** | Expiry condition not met |
| **onTimeout** | Timeout period elapsed |

⚠ **`onSuccess` and `onSubmit` are distinct exit paths, not aliases** — they are separate branches and must be wired separately [`connect-rcs.md` § Exit Paths, source https://help.webexconnect.io/docs/rcs-message-node, verified 2026-04-17]. This matters directly here: § Critical: Wait For Setting above prescribes **Gateway Submit**, and in that mode the edge that fires is **`onSubmit`** — so wire the success path off `onSubmit`, not off `onSuccess`.

---

## Apple Messages for Business (Side-Effect Notifications)

Sends rich, interactive messages to iOS users via Apple Messages for Business. Supports interactive message types (rich links, list pickers, time pickers, forms) that render natively in the Messages app — no app install required.

### When to Use in AI Agent Flows

After an HTTP POST creates a record (appointment, order, etc.), drop an Apple Messages node between the last HTTP node and the End node to send a rich confirmation. Unlike SMS, the customer must have an **active session** — they must have messaged your business first. This makes it ideal for flows triggered by an inbound customer interaction (e.g., a contact center call or chat), but it cannot cold-send to a phone number.

```
Trigger → HTTP GET → HTTP POST → Apple Messages → End
```

### Key Constraint: Active Session Required

Apple Messages for Business requires the customer to have initiated a conversation with your business first. You cannot send outbound messages to arbitrary phone numbers like SMS. If no active session exists, the node will fail. Always wire the **onError** edge to the End node so the agent still returns data even if the Apple Message cannot be delivered.

### Required Configuration

> **Owner: `connect-apple-messages.md` § Apple Messages Configuration.** Reproduced here for agent-flow context; that file wins on any disagreement. ⚠ This table carried four disproven values until 2026-07-27 — `User ID`, `Gateway Submit`, a freetext `MIME Type`, and a merged `Title / Subtitle` — because the April 2026 audit swept the playbook and the channel reference but never this third copy.

| Field | Value | Notes |
|-------|-------|-------|
| **Destination Type** | `AbcUser Id` | The exact UI dropdown label. ⚠ **Not `User ID`** — a builder searching the dropdown for "User ID" will not find it |
| **Destination** | The customer's `abcId` from the session (opaque ID, **not** a phone number) | Use variable picker |
| **Message Type** | See interactive types below | Select based on use case |
| **Wait For** | `GW submit` | The exact label on this node. There is no Delivery Report option — Apple does not provide DRs |
| **Expiry** | `Seconds` with reasonable duration | Or `UTC` with a specific date |

### Interactive Message Types

| Type | What It Does | When to Use in Agent Flows |
|------|-------------|---------------------------|
| **Rich Link** | Displays a URL preview card with image, title, and tap-to-open link | Appointment confirmation linking to a portal or directions page |
| **List Picker** | Shows a scrollable list of items the customer can select from (up to 20 sections × 20 items) | Let the customer pick from available time slots or test types mid-flow |
| **Time Picker** | Presents selectable time slots with location details (title, lat/long) | Appointment scheduling — show 3-5 available slots with the clinic location |
| **Form Message** | Multi-page structured form with typed input fields | Collect patient intake information or insurance details |

### Rich Link Fields

| Field | Value | Notes |
|-------|-------|-------|
| **URL** | Link to open on tap | e.g., appointment portal URL |
| **Title** | Display title (max 128 chars) | e.g., `Appointment Confirmed - $(n5.confirmation_number)` |
| **Image URL** | Preview image | Company logo or location photo |
| **MIME** | Image type, chosen from a dropdown | The field is labelled `MIME`, and it is a **dropdown of extensions** (`png`, `jpeg`), not a freetext field taking `image/png` |

### List Picker Fields

| Field | Value | Notes |
|-------|-------|-------|
| **Title** | Bubble text shown before customer taps | e.g., `Select a Time Slot` |
| **Subtitle** | Secondary bubble text | A **separate, required** field — not merged with Title |
| **Sections** | Grouped items (max 20 sections, 20 items each) | Each item has title, subtitle, and identifier |
| **Multi-select** | Toggle on/off | Off for single-selection scenarios like picking one time slot |
| **Request Identifier** | Unique string to correlate the reply | Use a flow variable or hardcoded action name |

### Time Picker Fields

| Field | Value | Notes |
|-------|-------|-------|
| **Title** | Picker header (bubble preview text) — **required** | e.g., `Available Appointments` |
| **Subtitle** | Bubble preview subtext | A **separate, required** field — not merged with Title [`connect-apple-messages.md` § Time Picker] |
| **Time Slots** | Up to 10 slots, each with start time, duration (seconds), and identifier | Past time slots are automatically hidden by Apple. The UI labels the duration field `Slot Duration (In Secs)` |
| **Location** | Title, latitude, longitude, radius | Clinic address for context |
| **Request Identifier** | Unique string to correlate the reply | Same pattern as List Picker |

### Critical: Wait For Setting

> **Owner: `connect-apple-messages.md` § Wait For Options.** Reproduced here so this page works standalone; the channel reference wins on any disagreement.

⚠ **This node does NOT follow the SMS/Email/RCS pattern.** It has exactly **two** options, and the labels differ:

| Mode | Behavior | Use in agent flows? |
|------|----------|---------------------|
| **None** | Fire and forget — this is the **default** | Works, but you get no submission confirmation |
| **GW submit** | Waits for submission confirmation from the Apple gateway | **Yes** — recommended |

**Always set Wait For to `GW submit`** in AI agent flows — that is the exact UI label on this node, not "Gateway Submit" (same as the Required Configuration table above).

**There is no Delivery Report option on this node** — *"Apple does not provide delivery/read receipts to MSPs"* [`connect-apple-messages.md` § Wait For Options]. A Delivery Report row stood here until 2026-07-27; it described a mode that does not exist.

### Example: Appointment Confirmation as Rich Link

After `create_appointment` returns a confirmation number, send a rich link before the End node (the return payload itself is set in Flow Settings > Flow Outcomes):

**Message Type:** Rich Link

**Title:**
```
Appointment Confirmed - $(n5.confirmation_number)
```

**URL:**
```
https://example.com/appointments/$(n5.confirmation_number)
```

**Image URL:** `https://example.com/assets/clinic-logo.png`

**MIME:** `png` — the field is labelled **`MIME`** and is a **dropdown of extensions** (`png`, `jpeg`, `mp4`), **not** a freetext field taking an `image/*` media type [`connect-apple-messages.md` § Rich Link; matches the Rich Link Fields table above]

- Node numbers reference earlier HTTP nodes — adjust via variable picker
- Wire the Apple Messages node's **onError** edge directly to the End node so the agent still gets the appointment data if the message fails (e.g., no active session)
- Consider an SMS fallback for customers not on iOS or without an active Apple Messages session

### Exit Edges

> **Owner: `connect-apple-messages.md` § Exit Paths.** Reproduced here so this page works standalone; the channel reference wins on any disagreement.

**The node has exactly these three exits.** There is **no `onTimeout`** edge (an `onTimeout` row stood here until 2026-07-27 and described an edge this node does not have) and **no `onInvalidData`** edge:

| Edge | Trigger |
|------|---------|
| **onSuccess** | Message submitted to the Apple gateway. ⚠ This means *"submitted to Apple's servers"*, **not** *"delivered to device"* — Apple does not provide delivery or read receipts to MSPs |
| **onError** | No active session, invalid destination, gateway rejection |
| **onPolicyFail** | Policy violation |

---

## WhatsApp (Side-Effect Notifications)

Sends a WhatsApp message to a customer via the configured WhatsApp asset. In AI agent flows, use it as a **side effect** — fire-and-forget confirmation after the core API work is done, before returning data through Flow Outcomes.

Two ways to send: with **Message Type = `Template`** (proactive — works anytime, requires pre-approval from Meta), or with one of the free-form Message Types (`Text`, `Media`, `Location`, `Contact`, `List Messages`, `Reply Buttons`), which only work **inside the 24-hour window** after the customer last messaged. ⚠ **There is no "session message" Message Type** — the valid values are exactly `Text`, `Media`, `Template`, `Location`, `Contact`, `List Messages`, `Reply Buttons` [`connect-whatsapp.md` § Required Fields]; the 24-hour window is a *constraint on the free-form types*, not a Message Type of its own. For agent flow side effects, **`Template`** is recommended because the 24-hour window status is unpredictable.

### Flow Pattern

```
Trigger → HTTP GET → HTTP POST → WhatsApp → End
```

### Key Constraint: 24-Hour Window

WhatsApp enforces a 24-hour session window from the customer's last message. Free-form messages (text, media, interactive) only work within this window. Outside the window, only **template messages** are allowed. Since agent flows are triggered by customer interactions, a session window is typically open — but for reliability, use template messages for side-effect confirmations.

### Required Fields

| Field | Value | Details |
|-------|-------|---------|
| **Destination Type** | `WA ID` or `Customer ID` | Two options. `WA ID` = WhatsApp ID (phone number including country code) of your customer / recipient of this message. `Customer ID` = primary key of the customer profile; a customer profile can be created to link one or more channel-specific identifiers. ⚠ **Casing is node-specific — do NOT normalise across nodes.** WhatsApp spells it `WA ID` / `Customer ID` (capital `D`). Call User uses `msisdn` / `Customer Id`; RCS Message uses `MSISDN` / `Customer Id`. All three spellings are correct in their own node — leave them as-is |
| **Destination** | WhatsApp ID | Use variable picker: `$(n2.aiAgent.phone_number)`. ⚠ `aiAgent` is **undocumented** — copy the path out of the variable picker, never type it from memory [`webex-connect.md` § Variable Picker Syntax → Format] |
| **Message Type** | `Template` or `Text` | Template for reliability outside 24hr window |

### Template Message Configuration

| Field | Details |
|-------|---------|
| **Template Name** | Select from approved templates dropdown |
| **Header Parameters** | Map via variable picker if template has header variables |
| **Body Parameters** | Map via variable picker: `$(n3.confirmation_number)`, `$(n3.appointment_date)`, etc. |

### Text Message Configuration (Within 24hr Window)

| Field | Details |
|-------|---------|
| **Message** | Max 4,096 characters. Supports `*bold*`, `_italic_`, `~strikethrough~`, `` `monospace` `` |
| **Preview URL** | Optional — renders first URL as clickable preview |

### Wait For

| Mode | Agent Flows? |
|------|-------------|
| **Gateway Submit** | **Yes** — fast, recommended |
| **None** | Yes — no delivery confirmation |
| **Delivery Report** | No — too slow for 30-second timeout |
| **Read** | No — privacy settings may block |

**Always use Gateway Submit** in agent flows.

### Exit Paths

> **Owner: `connect-whatsapp.md` § Exit Paths.** Reproduced here so this page works standalone; the channel reference wins on any disagreement.

The WhatsApp node has **seven** exit paths. ⚠ **`onSuccess` and `onSubmit` are separate events with different triggers, not aliases** — a `onSuccess / onSubmit` combined row stood here until 2026-07-27 and would have sent a builder to wire the wrong edge:

| Event | When |
|-------|------|
| `onSuccess` | Wait For = **None**; message send executed |
| `onSubmit` | Wait For = **Gateway Submit**; message submitted to WhatsApp — **this is the edge that fires under the Gateway Submit setting recommended above** |
| `onDeliveryReportSuccess` | Wait For = **Delivery Report**; delivery receipt received |
| `onTimeout` | No acknowledgment received within the timeout window |
| `onError` | Execution failed — invalid field values, malformed request (invalid destination, template mismatch, configuration error) |
| `onPolicyFail` | Policy checks failed (expiry, contact policy restrictions) |
| `onDeliveryReportFail` | Delivery or read condition not met within timeout |

### Output Variables

| Variable | Description |
|----------|-------------|
| `send.deliveryStatusCode` | Numeric status code |
| `send.deliveryStatusDescription` | Status description |
| `send.gatewayTid` | Transaction ID |

### Example: Appointment Confirmation via Template

```
Trigger → HTTP POST (create appointment) → WhatsApp (Template: appointment_confirmed) → End
```

Configure the WhatsApp node:
- Destination Type: WA ID
- Destination: `$(n2.aiAgent.phone_number)` — take this from the variable picker; ⚠ the `aiAgent` segment is **undocumented**, never type it from memory [`webex-connect.md` § Variable Picker Syntax → Format]
- Message Type: Template
- Template: `appointment_confirmed`
- Body Parameter 1: `$(n3.patient_name)` — patient name from POST response
- Body Parameter 2: `$(n3.appointment_date)` — date from POST response
- Body Parameter 3: `$(n3.confirmation_number)` — confirmation from POST response
- Wait For: Gateway Submit

Wire **onError** to the End node so the agent still returns data if the WhatsApp message fails.

### Gotchas

| Issue | Cause | Fix |
|-------|-------|-----|
| Template not in dropdown | Not approved by Meta | Check status in Tools > Templates; allow 24-72 hrs |
| Error 7710 | Free-form message outside 24-hour window | Use template message instead |
| Parameter mismatch (7804) | Template body expects N params but fewer provided | Match parameter count exactly |
| Variable arrives empty | Typed manually | Use variable picker |
| Message not delivered | Customer not on WhatsApp (7865) | Consider SMS fallback |

Full WhatsApp reference: `connect-whatsapp.md`.

---

## Call User Node (Initiates the Call)

Initiates the outbound voice call. It is **not** inside the Voice Node Group — it is the node that *creates* one. Adding a Call User node auto-creates the Voice Node Group its `onAnswer` edge connects to.

It replaces the deprecated **Send Voice** node (deprecated in v5.4.x).

### Required Fields

| Field | Details |
|-------|---------|
| **Destination Type** | `msisdn` (phone number) or `Customer Id` (platform identifier) |
| **Destination** | Phone number in **E.164 format** (e.g., `+15551234567`). Accepts a variable: `$(n1.inboundWebhook.phone)`. ⚠ **The literal path segment `inboundWebhook` appears on no Cisco page** — strict search of *Variable Management in Flows* and *Inbound Webhooks* on both help.webexconnect.io and developer.webexconnect.io found no occurrence (verified 2026-07-27); Cisco's examples use dot-notation over the parsed webhook payload instead. Confirm the exact path in the variable picker; **do not type it from memory** |
| **From Number** | Select from a dropdown of provisioned voice-enabled numbers. Supports **Dynamic** mode — select "Dynamic" and supply a variable |

⚠ **`Customer Id` casing is node-specific — do NOT normalise it across nodes.** Call User spells it `Customer Id` (lowercase `d`), as does RCS Message; the WhatsApp node spells the same concept `Customer ID` (capital `D`) and pairs it with `WA ID` rather than `msisdn`. All three spellings are correct in their own node. See § WhatsApp (Side-Effect Notifications) → Required Fields for the full cross-node casing rule.

### Optional Fields

| Field | Details |
|-------|---------|
| **Correlation ID** | User-defined tracking ID. Accepts dynamic values |
| **Callback Data** | Data passed back to client systems. **Limited to 2KB** — exceeding it causes `onPolicyFail` |
| **Notify URL** | Webhook URL for call status notifications |
| **Expiry Time** | Seconds before expiry, or a specific UTC date/time. Webex Connect strongly advises setting an expiry time |

### Exit Paths (Events)

| Event | Colour | When |
|-------|--------|------|
| `onAnswer` | green | Call answered — auto-connects to the Voice Node Group |
| `onError` | red | Invalid user ID or missing phone digits |
| `oncallfail` | red | Network connectivity issues |
| `onnoanswer` | red | Call unanswered |
| `onbusy` | red | Busy signal |
| `onreject` | red | Call rejected by the recipient |
| `onPolicyFail` | red | Policy failure (e.g. callback data > 2KB) |
| `onExpiry` | orange | Request expired (fires only when an expiry is configured) |

⚠ **Event casing is exact and deliberately inconsistent — do NOT "normalise" it.** The platform spells four of these events all-lowercase (`onbusy`, `onnoanswer`, `onreject`, `oncallfail`) and four in mixed case (`onAnswer`, `onError`, `onPolicyFail`, `onExpiry`) [source: https://help.webexconnect.io/docs/voice-call-user]. Casing is also **node-specific**: the Call Patch node, inside the Voice Node Group, uses `onNoAnswer` in mixed case — see § Call Patch Node (Voice Node Group) → Exit Paths. Never copy one node's casing onto another.

### Output Variables

| Variable | Description |
|----------|-------------|
| `call.fromNumber` | Originating number |
| `call.destination` | Receiving number |
| `call.transId` | Transaction ID |
| `call.timestamp` | Call timestamp |

---

## Voice Nodes (Voice Node Group)

The following nodes live inside the Voice Node Group. They are used in voice call flows (Start/Call User pattern), NOT in AI Agent action flows.

⚠ **"Exclusively" is stronger than Cisco states — this line previously said it, and the claim is withdrawn to a hedge rather than dropped.** Cisco documents these nodes as **permitted inside** a Voice Node Group; it does not state that they exist *only* there. For **Call Patch** specifically the playbook already carries the hedge: *"Call Patch is only available inside VNGs (documented as permitted inside VNGs; exclusive restriction is not explicitly stated in official docs)"* [`sequential-dialing.md` § Troubleshooting]. Treat "inside the group" as where you *will* use them, not as a documented prohibition elsewhere. (The **reverse** direction *is* documented, for Call User only — Cisco states outright that it *"cannot exist within the Voice Node Group"*; see § Nodes That Must Be OUTSIDE the Group.)

### Voice Node Group Rules

- Up to **1,000 Voice Node Groups** per flow
- Cannot be deleted once created
- **Wait for** and **Delay** nodes are NOT supported inside the group
- **The call terminates immediately when a node inside the group connects to a Voice Node Group edge** — wiring an internal node to a group edge exits the group and drops the call. Keep every node in a voice loop (Play, Evaluate, Call Patch, Branch) inside the group [confirmed against https://help.webexconnect.io/docs/voice-node-group; `docs/tests/findings/inbound-voice-findings.md` § Items Confirmed Accurate #4]
- **Answering Machine Detection is configured in the group's Settings panel** — see § Answering Machine Detection (AMD) below
- The group **auto-creates**: from the **Inbound Call** trigger on the Start node for inbound flows, and from the **Call User** node for outbound flows. Do not add a Call User node to an inbound flow — it creates a second group

### Nodes That Must Be OUTSIDE the Group

| Node | Why |
|------|-----|
| **Start node** | Always first, always outside the group |
| **Call User node** | *"This node cannot exist within the Voice Node Group"* — it is not permitted inside, not merely unnecessary [source: https://help.webexconnect.io/docs/voice-call-user] |

### Voice-Specific Nodes (Inside the Group)

| Node | Purpose |
|------|---------|
| **Play** | Play TTS or audio to the caller |
| **Record** | Record caller audio (voicemail, statements) |
| **Collect Input** | Capture DTMF or speech input |
| **IVR Menu** | Multi-option menu with branching |
| **Call Patch** | Bridge the caller with another number (two-party conference) |
| **Call Transfer** | Blind or warm transfer to another number (available on request) |

### General-Purpose Nodes (Inside the Group)

These non-voice nodes can run inside the group while the call is active:

Evaluate, Branch, HTTP Request, Data Parser, Data Transform, SMS, Email, WhatsApp, Messenger, Apple Messages for Business, **RCS**, Profile, Generate OTP, Validate OTP, Decryption, Encryption

(**RCS** was missing from this list until 2026-07-27; the official node palette includes it [`docs/tests/findings/inbound-voice-findings.md` row 5, source https://help.webexconnect.io/docs/voice-node-group].)

### Answering Machine Detection (AMD)

Configured in the Voice Node Group **Settings** panel. The detection prompt supports Pre-recorded, Upload File, URL, or TTS.

**AMD TTS prompt limit — 2,000 characters.** On the TTS prompt option: *"**Text To Speech** — enter the **Text Message** that needs to be converted to speech. The maximum number of characters you can enter is **2000**."* [source: https://help.webexconnect.io/docs/voice-node-group, AMD prompt option (iv), verified 2026-07-27].

⚠ **This is a different limit from the Play node's — do not mix them up.** The Play node allows **3,000** characters in Plain Text and **6,000** in SSML (§ Play Node (Voice Node Group) → TTS Settings, a few lines below). Those numbers do **not** apply to the AMD detection prompt, and the AMD prompt's 2,000 does **not** apply to a Play node.

| Exit Path | When |
|-----------|------|
| **Success (green)** | Human answered — AMD determined a person picked up; connects normally to the Voice Node Group |
| `onAnsweringMachine` | Machine/voicemail detected — fires as the **default** outcome *under* the Success edge; when detection is ambiguous, the system assumes machine |
| `onCallDrop` | Call dropped during AMD detection |

The **Success (green)** edge is the human-answered path. `onAnsweringMachine` branches off Success — it is an outcome *within* Success, not a sibling of it.

---

## Play Node (Voice Node Group)

Plays audio or TTS to the caller. Lives inside the Voice Node Group.

### TTS Settings

| Setting | Options |
|---------|---------|
| **TTS Processor** | Azure (the only supported engine in Connect) |
| **Voice Type** | Neural (Standard is deprecated) |
| **Language** | Select from the list, or "Dynamic" (pass an ISO 639 code at runtime) |
| **Voice** | Azure Neural voice name (e.g. `AriaNeural`, `GuyNeural`), or dynamic |
| **Input Format** | **Plain Text** (3,000 character limit) or **SSML** (6,000 character limit) |

⚠ **Webex Connect uses Azure Neural TTS, not Cisco TTS.** Cisco TTS exists only in WxCC Flow Designer, a separate platform — see `flow-designer-patterns.md` § TTS.

### Audio Alternatives (Non-TTS)

- **Pre-recorded audio** from the Voice Media library (Tools > Voice Media)
- **File upload** — drag/drop WAV or MP3, max **20MB**. (The 10MB limit applies to Voice Media Manager uploads and AMD prompt uploads, **not** the Play node's own upload field)
- **URL** — a hosted audio file; supports a dynamic variable in the URL

**Add New Audio** queues multiple prompts in sequence within a single Play node.

### Exit Paths

| Outcome | When |
|---------|------|
| `onSuccess` | Audio plays without errors |
| `onError` | Playback encounters issues |

### SSML Tags (Azure Neural TTS)

Available when **Input Format** is set to SSML. These are the tags that matter for notification-style prompts.

| Tag | Purpose | Example |
|-----|---------|---------|
| `<speak>` | Required root wrapper for all SSML | `<speak>Your message here</speak>` |
| `<say-as interpret-as="characters">` | Spell out letter/digit by letter/digit | `ORD-4521` → "O-R-D-four-five-two-one" |
| `<say-as interpret-as="cardinal">` | Read as number | `42` → "forty-two" |
| `<say-as interpret-as="ordinal">` | Read as ordinal | `3` → "third" |
| `<say-as interpret-as="telephone">` | Read as phone number | Standard phone cadence |
| `<say-as interpret-as="currency">` | Read as money | `$53.21` → "fifty-three dollars and twenty-one cents" |
| `<say-as interpret-as="date">` | Read as date | Standard date reading |
| `<break time="500ms"/>` | Insert pause | Half-second silence |
| `<prosody rate="slow">` | Control speed | Slow down for important info |
| `<sub alias="...">` | Substitute pronunciation | `<sub alias="World Wide Web">WWW</sub>` |
| `<audio src="..."/>` | Embed a pre-recorded audio clip inline | Mix TTS with audio files |
| `<p>` / `<s>` | Paragraph / sentence boundaries | Natural pauses between sections |

⚠ **This is the Azure Neural TTS tag set, used by Webex Connect.** WxCC Flow Designer runs **Cisco** TTS and has its own tag table — see `flow-designer-patterns.md` § SSML. Do not carry tags between the two engines without checking.

---

## Call Patch Node (Voice Node Group)

Bridges the ongoing call (A-party) with another number (B-party) inside the Voice Node Group. Used for two-party conferencing — dials the B-party, plays optional audio to both parties during connection, then merges the calls.

### When to Use

- Transfer a caller to a live agent or specialist while keeping the flow in control
- Conference two parties (e.g., caller + on-call technician) during an automated voice flow
- Patch a caller through to a destination with jingle/hold audio and optional recording

**Not for AI agent action flows.** This node lives inside a Voice Node Group, which only exists in outbound/inbound voice call flows (Start/Call User pattern), not in AI Agent Event flows.

### Configuration

| Field | Value | Notes |
|-------|-------|-------|
| **Destination (B-PARTY)** | E.164 phone number or variable | Format errors exit through ErrorEdge |
| **From Number** | Dropdown — "Select a number" | The calling party for the outbound leg. **A separate field from Display Number** — do not assume setting one sets the other |
| **Display Number** | Select from provisioned voice numbers (Assets) | Number shown to B-party as caller ID |
| **Display Name** | Business name. Cisco's page states the limit as **"10 digits"** — see the unit note below the table | Disabled by default. **Both Display Number and Display Name** must be enabled by your account manager, not Display Name alone |
| **Play Audio** (toggle) | Enable/disable pre-patch audio | Controls the two audio fields below |
| **Play audio to A party** | Jingle played to the caller during the patch attempt. Cisco's full label: *"Play audio to A-Party (calling party) while attempting the call patch"* | ⚠ How the audio source is chosen (four tabs vs. a single **Jingle File** dropdown) is **UNRESOLVED** — see the block below the table |
| **Play audio to B party** | Announcement played to the B-party before merge (e.g. "You have an incoming patched call"). Cisco's full label: *"Play audio to B-Party (called party) before patching the call"* | ⚠ How the audio source is chosen (four tabs vs. a single **Announcement File** dropdown) is **UNRESOLVED** — see the block below the table |
| **Announcement loop** | Repeat the announcement until a DTMF keypress or the loop threshold is reached | **Default loop threshold: 10.** Configurable; prevents infinite playback |
| **Transfer DTMFs** | Forward DTMF keypresses by A-party to B-party and/or vice-versa after the patch | **If the announcement loop is enabled, DTMFs transfer only after the loop has exited** |
| **Record the call** | Field label is **"Record the call upon successfully patching both calls"** | Configure a file prefix; files appear in Tools > Voice Recordings |

**Note — the Display Name limit is "10 digits", and the unit is Cisco's own ambiguity.** Cisco's Call Patch page states the limit as **10 digits** for what is a *name* field. Our April 2026 vetting pass recorded this verbatim and flagged the unit as probably a Cisco documentation error, without resolving it: *"Official docs also state '10 digits' — likely a documentation error on Cisco's side (should be characters, not digits for a name field). Both docs and playbook agree but neither clarifies the unit."* [`docs/tests/findings/inbound-voice-findings.md` row 11, vetted 2026-04-17 against https://help.webexconnect.io/docs/call-patch-node]. A "max 10 characters" reading previously stood in this table; it came from `docs/plans/spec-a-voice-nodes-reference.md` line 50 as an unsourced paraphrase and has been withdrawn in favour of Cisco's literal string. `inbound-voice.md` § 6 and `sequential-dialing.md` § 2 both already carry the literal "10-digit max" and are correct as written. **Confirm the real character budget in your tenant before relying on a 10-character name.**

> ⚠ **UNRESOLVED — Call Patch audio source: four tabs, or a single-file dropdown?**
>
> Do **not** treat either reading below as settled, and do not silently pick one. Two vetting passes run on the **same day** (2026-04-17) against the **same** Cisco page reached opposite conclusions, and the remediation backlog carries this as an open item, blocked on "Conflicting accounts" [`docs/plans/2026-07-25-documentation-remediation-backlog.md` § 4 open-items table, row *"Jingle / Announcement File dropdown-vs-tabs"*].
>
> | Reading | Claim | Evidence |
> |---|---|---|
> | **A — four source tabs** | Checking either box reveals **four tabs: Pre-recorded / Upload / URL / TTS**, not a single-file dropdown. Applies to both A-party and B-party. | `docs/tests/findings/sequential-dialing-findings.md` rows 4 and 9, source https://help.webexconnect.io/docs/call-patch-node. **Self-hedged:** the same document's *Items Not Verifiable* #3 says the four-tab component for the A-party was inferred from a **screenshot** — "text docs don't enumerate" whether the A-party jingle supports TTS. |
> | **B — single-file dropdown** | "Play audio to A party" activates a **Jingle File** dropdown; "Play audio to B party" activates an **Announcement File** dropdown. Both list pre-uploaded audio from the Voice Media library. | `docs/tests/findings/inbound-voice-findings.md` *Items Confirmed Accurate* #11 — recorded as **confirmed** against the same Cisco page on the same date. |
>
> **What is not in dispute:** both checkboxes exist, both are optional, and each gates the audio played to its own party. Only the source-selection UI is disputed.
>
> **To close this:** open Call Patch in a live tenant's Voice Node Group, tick each box, and record what appears — four tabs, one dropdown, or a dropdown that has since become tabs on a newer voice-node version. Until then, `inbound-voice.md` § 6 (dropdown) and `sequential-dialing.md` § 2 (four tabs) are both labelled in place and neither is to be "corrected" to match the other.

### Exit Paths

| Edge | Color | Trigger |
|------|-------|---------|
| **onSuccess** | Green | Call successfully patched — both parties connected |
| **onNoAnswer** | Yellow | B-party does not answer, or announcement loop threshold reached without DTMF |
| **onError** | Red | Patching error (e.g., invalid E.164 format on destination) |

**There is no ring-timeout field on Call Patch.** The node exposes no setting for how long the B-party is allowed to ring before `onNoAnswer` fires — Cisco's page says only that `onNoAnswer` fires "when the user does not answer the call", and **Destination (B-PARTY)** is the node's only required field. Ring duration is therefore carrier-controlled and not configurable here.

⚠ **The commonly cited "30–45 seconds" is an estimate with no source.** Two independent vetting passes each filed it as unverifiable: *"Call Patch `onNoAnswer` carrier timeout (30-45 seconds) — no official source"* [`docs/tests/findings/inbound-voice-findings.md` § Items Not Verifiable #4] and *"Ring timeout carrier defaults (30–45 seconds) — not in official docs"* [`docs/tests/findings/sequential-dialing-findings.md` § Items Not Verifiable #7]. Do not build a timing budget that depends on it without measuring in your own tenant.

**The nearest thing to a configurable timeout** is the announcement loop: enable **Loop audio until DTMF keypress** on the B-party announcement with a short clip and a low **Looping threshold**, and `onNoAnswer` fires once the threshold is reached without a DTMF keypress. That gives indirect control over per-attempt duration. `sequential-dialing.md` § 3 owns the procedure for sizing it.

### Output Variables

| Variable | Description |
|----------|-------------|
| `patch.APartyNumber` | Cisco's wording: *"the number from which the **outbound call is in progress**"* — i.e. the A-party of the **patch leg**. ⚠ Do **not** assume this returns the original inbound caller's ANI; "Originating number (A-party / caller)" stood here until 2026-07-27 and invited exactly that reading [`inbound-voice.md` § 6 → Output Variables] |
| `patch.BPartyNumber` | The B-party (patched destination) number |

### Example: Patch Caller to On-Call Technician

```
Start (Inbound Call) → Voice Node Group
  → IVR Menu ("Press 1 for emergency dispatch")
    → [1] → Call Patch (destination: on-call number, jingle to A-party, announcement to B-party)
      → onSuccess → Play ("You are now connected") → End
      → onNoAnswer → Play ("No technician available, please try again later") → End
      → onError → Play ("We encountered an error") → End
```

### Gotchas

| Issue | Cause | Fix |
|-------|-------|-----|
| onError fires immediately | Destination not in E.164 format | Include `+` and country code (e.g., `+15551234567`) |
| B-party hears nothing before patch | "Play audio to B party" not configured or toggle off | Enable Play Audio and set the announcement file |
| Announcement loops forever | Loop threshold not set | Configure the announcement loop threshold |
| No recording saved | "Record the call" not enabled, or missing file prefix | Enable recording and set an alphanumeric prefix |

---

## Call Transfer Node (Voice Node Group)

Transfers the active call to a specified phone number. Supports two modes: **blind transfer** (disconnect immediately when transferee rings) and **warm transfer** (disconnect when transferee answers, with a failure path if unanswered). Lives inside the Voice Node Group.

### When to Use

- Hand off a call to an external number (e.g., specialist, clinic, department) without maintaining the connection
- Blind transfer when Connect does not need to track the outcome
- Warm transfer when you need a fallback path if the transfer fails

**Not for AI agent action flows.** Voice Node Group only.

### Availability Restrictions

- **Available only on request** — contact your account manager to enable this node on your tenant
- **Not available in London or Europe regions** — this feature is region-restricted

### Configuration

| Field | Value | Notes |
|-------|-------|-------|
| **Play Audio** | Optional audio before transfer begins | Configure per Play node pattern (TTS, file, URL) |
| **To Number** | E.164 phone number or variable | Format errors exit through ErrorEdge |
| **Transfer Type** | `Blind` or `Warm` | See behavior differences below |

### Transfer Type Behavior

| Type | When Connect Disconnects | Failure Handling |
|------|--------------------------|-----------------|
| **Blind** | When the call starts **ringing** at the transferee's end | No failure path — Connect has already disconnected |
| **Warm** | When the transferee **answers** | If unanswered, exits via `TransferFailed` edge — flow can continue |

### Exit Paths

| Edge | Trigger |
|------|---------|
| **ErrorEdge** | To Number not in valid E.164 format |
| **TransferFailed** | Warm transfer only — transferee did not answer |

**Note:** Blind transfers have no TransferFailed edge because Connect disconnects at ring time. If the transferee doesn't answer a blind transfer, the caller hears ringing until they hang up — Connect has no visibility.

### Example: Warm Transfer to Specialist with Fallback

```
Start (Inbound Call) → Voice Node Group
  → Play ("Transferring you to a specialist, please hold")
  → Call Transfer (To Number: +15559876543, Type: Warm)
    → TransferFailed → Play ("The specialist is unavailable. Returning to main menu.") → IVR Menu
    → ErrorEdge → Play ("We encountered an error with the transfer") → End
```

### Gotchas

| Issue | Cause | Fix |
|-------|-------|-----|
| Node not in palette | Not enabled on tenant | Contact account manager to enable |
| Node unavailable | Tenant in London or Europe region | Not supported in these regions — use Call Patch as alternative |
| ErrorEdge fires immediately | To Number not in E.164 format | Include `+` and country code |
| Caller hears ringing forever (blind) | Normal blind transfer behavior — Connect disconnects at ring | Use warm transfer if you need a failure path |
| TransferFailed never fires | Transfer Type set to Blind | TransferFailed only exists for Warm transfers |

---

## Record Node (Voice Node Group)

Records audio from the caller during an active voice call. The recording is saved to Voice Recordings (Tools > Voice Recordings) with a configurable file prefix. Lives inside the Voice Node Group.

### When to Use

- Capture a voicemail message when no agent is available
- Record a caller's verbal statement (e.g., incident description, authorization consent)
- Log a call segment for compliance or quality purposes

**Not for AI agent action flows.** Voice Node Group only.

### Configuration

| Field | Value | Notes |
|-------|-------|-------|
| **Play Audio** (toggle) | Optional prompt before recording starts | e.g., "Please leave your message after the beep" |
| **Play short beep before starting the recording** | Checkbox | Auditory cue signaling recording has begun |
| **Recording Timeout (in seconds)** | Max recording duration | Maximum value: **300 seconds** (5 minutes) |
| **Stop Recording on Keypress** | DTMF key that ends recording | e.g., `#` — caller presses to stop early |
| **Audio File Prefix Name** | Prefix for saved recording files | Alphanumeric, underscores, `$` signs, or variables |

### Exit Paths

| Edge | Color | Trigger |
|------|-------|---------|
| **onSuccess** | Green | Recording completed (caller pressed stop key or finished speaking) |
| **onrecordingTimeout** | Yellow | Recording hit the configured timeout duration |
| **onError** | Red | Recording failed |

### Output Variables

| Variable | Description |
|----------|-------------|
| `record.recordingFilePath` | Path to the saved recording file in Voice Recordings |

### Example: Voicemail After No Answer

```
Call User → onnoanswer → Voice Node Group
  → Play ("The person you are calling is unavailable. Please leave a message after the beep.")
  → Record (timeout: 120s, stop key: #, prefix: voicemail)
    → onSuccess → Play ("Your message has been recorded. Goodbye.") → End
    → onrecordingTimeout → Play ("Recording limit reached. Goodbye.") → End
    → onError → Play ("We could not record your message. Please try again later.") → End
```

### Gotchas

| Issue | Cause | Fix |
|-------|-------|-----|
| Recording cuts off too early | Timeout set too low | Increase Recording Timeout (max 300 seconds) |
| No beep before recording | Checkbox not enabled | Enable "Play short beep before starting the recording" |
| Recording file not found | Missing or invalid Audio File Prefix Name | Set a valid alphanumeric prefix |
| Caller can't stop recording | Stop Recording on Keypress not configured | Set a DTMF key (e.g., `#`) |

## See Also

- [webex-connect.md](webex-connect.md) — the Connect flow basics
- [connect-multi-channel.md](connect-multi-channel.md) — combining messaging channels
- [inbound-voice.md](../playbooks/inbound-voice.md) — the inbound voice build steps that pair with this reference
- [sequential-dialing.md](../playbooks/sequential-dialing.md) — the sequential dialing build steps that pair with this reference
- [outbound-voice.md](../playbooks/outbound-voice.md) — the outbound voice build steps that pair with this reference
