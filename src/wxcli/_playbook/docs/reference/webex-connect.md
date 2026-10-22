# Webex Connect — Platform Reference

<!-- ref-tag: webex-connect-v6 -->

## Flow Structure for AI Agent Actions

Every AI agent action maps to exactly one Webex Connect flow. The flow follows this pattern:

```
Trigger node (Configure AI Agent Event) -> HTTP Request Node(s) -> End
```

Data is returned to the AI agent **not by a node on the canvas** but by the flow-level **Flow Settings > Flow Outcomes** configuration — see the Flow Outcomes section below.

### Required Nodes

- **Trigger node** (always first): every Webex Connect flow starts with a trigger node (the official Cisco docs call this the **Start node** — *"Every flow must begin with a Start node."* [source: https://help.webexconnect.io/docs/flows-introduction]). You pick a **trigger category**, and the node then presents as that category's configuration. For AI agent actions the category is AI Agent, so the first node is **Configure AI Agent Event**.
- **HTTP Request node(s)**: calls the backend API (REST endpoint)
- **End node** (END FLOW): terminates the flow. There is **no Flow Outcomes node** — the payload returned to the agent is configured in Flow Settings, not on the canvas.

### Prohibited Nodes in AI Agent Flows

AI Agent flows have a **30-second execution time limit**. Cisco restricts these Waiting Nodes because they *"can cause flow execution to exceed this limit"* [source: https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions]. Never use them:

- **Delay** -- introduces wait time the agent cannot tolerate
- **Social Hour Check** -- time-based routing that stalls the flow
- **Receive Node** -- creates a blocking listener. The restriction is on the **Receive Node**, unqualified — there is **no** "only the second instance" carve-out in the official text [source: https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions]
- **Call Workflow** -- hands off to another flow, exceeding timeout

**Those four are examples of a category, not a closed list.** Cisco's wording is *"Using Waiting Nodes such as Delay, Social Hour, Receive Node, and Call Workflow is restricted"* [source: https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions], and a second Cisco page defines the same category more fully — *"Examples of waiting nodes are Delay, Social hour, Receive, Wait for events in Send nodes, and Prebuilt asynchronous events"* [source: https://help.webexconnect.io/docs/flow-monitoring] — so **Wait for events in Send nodes** and **Prebuilt asynchronous events** are waiting nodes too and fall under the same restriction by category. The practical rule is that anything making the flow **wait** risks the 30-second limit, so treat the four named nodes as the common cases rather than the whole set. **No exhaustive list of waiting nodes is published** — both pages say only "such as" / "Examples of", so these six are not a complete set either.

### Safe Non-HTTP Nodes for AI Agent Flows

These nodes execute fast and are safe within the 30-second timeout:

- **Branch** -- conditional routing (check HTTP status codes)
- **Evaluate** -- inline JavaScript (date conversion, string ops)
- **Data Parser** -- JSON field extraction (when HTTP node parsing isn't enough)
- **Customer Journey Data** -- JDS reads/writes (keep lightweight)
- **SMS** -- side-effect notifications (use Gateway Submit mode, not Delivery Report)
- **Email** -- side-effect notifications (use Gateway Submit mode, not Delivery Report)
- **RCS** -- rich side-effect notifications (requires Capability check + Branch fallback to SMS; use Gateway Submit mode)
- **Apple Messages** -- rich side-effect notifications for iOS users (requires active customer session; set Wait For to `GW submit` — the label on this node is not "Gateway Submit" [`connect-apple-messages.md` § Wait For])

See `webex-connect-advanced.md` for configuration details on all non-HTTP nodes.

---

## Trigger Node Configuration

Every Webex Connect flow begins with a trigger node (the official Cisco docs call this the **Start node** [source: https://help.webexconnect.io/docs/flows-introduction]). You first pick a **trigger category**; the node then presents as that category's configuration. The first node is named after the category you chose:

| Trigger category | First node in the flow |
|---|---|
| AI Agent | **Configure AI Agent Event** |
| SMS | **Configure SMS Event** |
| Webex CC Task | **Webex CC Task** node |

### Full trigger category inventory

Cisco's Start node page groups the trigger categories in three sets [source: https://help.webexconnect.io/docs/start-node]:

| Group | Categories |
|---|---|
| **Channel Events** | SMS, Voice, MMS, Messenger, Instagram (Deprecated), WhatsApp, Mobile & Web App, Email, Apple Messages for Business, RCS |
| **Integration Triggers** | CCSP (Deprecated), BOT (Deprecated), AI Agent |
| **Custom Triggers** | Webhook, Custom event |

> **Webex CC Task.** The official Start node inventory above does **not** list Webex CC Task as a trigger category. The tenant owner has confirmed the Webex CC Task row in the table above, so it is retained. Cisco documents the Webex CC Task *integration nodes* (Create Task, Set Variable, Queue Task, PIQ and EWT, Routed Notification, Modify Notification, Screen Pop, Close Task, Resolve Conversation) separately, as palette nodes with node authorizations rather than as a Start-node trigger [source: https://help.webexconnect.io/docs/wxcc-task-integration-nodes-and-node-authorizations].

### Per-channel trigger events

Once you pick a Channel Events category, you pick the specific event [source: https://help.webexconnect.io/docs/start-node]:

| Channel | Trigger events |
|---|---|
| SMS | Mobile Originated, Link Click |
| Voice | Inbound Call, Missed Call |
| MMS | Mobile Originated |
| Messenger | Incoming Message, Link Click, Postback |
| WhatsApp | Incoming Message, Postback, List Message, Reply Buttons |
| Email | Incoming Message, Subscribe, Unsubscribe |
| RCS | Incoming Attachment, Message, Location Response, Postback, Subscribe, Unsubscribe |

### Trigger Conditions

*"The platform allows selective triggering of the flow only when the conditions set on the trigger event are fully met."* This is the mechanism for routing different inbound values (for example different SMS keywords) to different flows. The **13 operators the Start node page lists** [source: https://help.webexconnect.io/docs/start-node]:

Equals, Not equals, In, Not in, Contains, Greater than, Less than, Greater than equal to, Less than equal to, Equals ignore-case, Between, Starts with, Ends with.

⚠ **Those 13 are not stated to be the complete set.** Cisco's lead-in is *"**One of the several** conditional operators that can be used to set conditions are listed below:"* [source: https://help.webexconnect.io/docs/start-node] — the page lists 13 but never claims they are all of them, so do not treat the absence of an operator here as proof the Start node lacks it. Verified live 2026-07-27: the 13 above are exactly what that page lists, and `Regex` / `Contains ignore-case` do **not** appear on it.

**Different from the Branch node's list — and that is not a contradiction.** The Branch node page separately documents **15** operators, including *Regular expression (RegEx)* and *Contains ignore case*, which is why `webex-connect-advanced.md` § Branch Node (Conditional Logic) → Configuration lists 15 [source: https://help.webexconnect.io/docs/branch-node]. Each list is correct for its own node. Cisco also spells shared operators differently per node — Start: `Less than equal to`, `Equals ignore-case`; Branch: `Less than or equals`, `Equals ignore case` — that difference is genuine in Cisco's own text; **do not normalise the spellings across the two nodes.**

### "Trigger only when there are no live sessions"

A checkbox available on SMS, RCS and digital channel triggers. It prevents a second flow execution starting while a Receive-node session from an earlier execution is still live. Set it on any two-way messaging flow [source: https://help.webexconnect.io/docs/start-node].

### Flow Type is chosen at flow creation, not on the trigger node

*"Enter the Flow Name and choose the **Type** as WorkFlow. You can select 'Voice Flow' in case you want to build a voice flow."* Then choose **Method** → **New Flow** → **Start from Scratch** (or select a pre-built template) [source: https://help.webexconnect.io/docs/create-a-new-flow].

### Other ways a live flow can be triggered

Beyond the Start node, a live flow can also be invoked by the **Event Scheduler** (via the Custom Event API or an Inbound Webhook), by **Rules**, and by another flow through the **Call Workflow** node [source: https://help.webexconnect.io/docs/trigger-flow].

### AI agent action flows

For an AI agent action flow, pick the **AI Agent** category, then:

1. Set **Trigger category**: **AI Agent** — the node then presents as **Configure AI Agent Event**
2. The **event auto-populates** as *"Trigger from AI Agent to initiate flow"* — you do **not** type an event name, and nothing has to be typed to match the action name in AI Agent Studio [source: https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions]
3. Shape the sample payload in **Provide sample JSON** — *"A sample input JSON is provided by default"* there, which you modify to match the action's inputs — then *"click **Parse** to view the sample payload's parameters as output variables"* [source: https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions]. See §Configure AI Agent Event

### How an action binds to a flow

The binding is made **in AI Agent Studio**, not in Connect, and it is a **manual two-dropdown selection** — no name has to match anything. On the action, under **Webex Connect Flow Builder Fulfillment**, you **Select a service** and then **Select a flow** (only flows whose start node is AI Agent are listed) [source: https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions].

Confirmed against a real exported agent: each action's `fulfillment` block records both the service and the flow by **numeric id**, not by name:

```json
"fulfillment": {
  "type": "flow",
  "service_id": 55064, "service_name": "LabCorp_Appt",
  "flow_id": 82711,    "flow_name": "lookup_patient",
  "webhook_url": "https://hooks.us.webexconnect.io/flows/82711/trigger/aiagent",
  "authentication": { "type": "ci_bearer_token", "service_key": "" }
}
```

- `service_id` and `flow_id` are **integers**, not UUIDs
- The webhook URL is keyed on the **numeric flow id**
- **Names are irrelevant to the binding.** Naming the flow after the action (as above) is a readability convention only — the owner confirms they do not have to match
- Whether AI Agent Studio generates the `webhook_url` when you pick the flow, or it is populated some other way, is **unverified** — it appears in the export, but do not tell a user to construct or paste it

> AI Agent flows have a **30-second execution time limit** [source: https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions].
>
> Webex AI Agent Studio can only access services and flows configured within the **Client-level workspace** [source: https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions].

---

> **Connect vs. Flow Designer HTTP:** This section covers the Webex Connect HTTP Request node used in AI agent action flows, notification flows, and digital inbound flows. For calling WxCC APIs from Flow Designer voice flows with managed authentication, see the **HTTP Connector** section in `docs/reference/wxcc-platform.md`.

## HTTP Request Node -- GET Requests

### URL Format

```
https://{api-base-url}/{endpoint}?{filters}
```

Use the **variable picker** (click, don't type) to insert AI Agent variables into the URL:

```
...?phone_number=eq.$(n2.aiAgent.phone_number)
```

Node numbers change based on flow layout -- always use the picker to get the correct reference.

### Headers

Configure headers appropriate to your backend API. Common headers include:

| Header | Purpose |
|--------|---------|
| Auth header(s) | API key, Bearer token, etc. |
| `Content-Type` | `application/json` |
| `Accept` | Controls response format (single object vs. array) -- backend-specific |

### Output Variables Tab

1. Click **Import from Sample**, paste your sample JSON response into the **Data Parser** dialog box and click **Parse**, select the required parameters under **Select key paths to be extracted**, then click **Import** — rows are generated from the key paths you selected [source: https://help.webexconnect.io/docs/http-request-node]
2. Renaming output variables after parsing is **not documented in official docs**. The node page describes key-path selection and an output-variable name field, but no post-parse rename step. Use consistent, descriptive field names in your sample JSON so names do not collide when chaining multiple HTTP nodes [source: https://help.webexconnect.io/docs/http-request-node]
3. Response path format (**not documented in official docs** — the HTTP Request node UI uses key-path selection; JSONPath-style notation such as `$.glossary.title` appears only on the Data Parser page [source: https://help.webexconnect.io/docs/data-parser-node]):
   - **Single object**: `$.field_name`
   - **Array -- first element**: `$[0].field_name`
   - **Array -- whole array**: `$`

Output variable names may use only **alphabets, numbers, underscores, hyphens, and spaces** [source: https://help.webexconnect.io/docs/http-request-node]. This is a *different* rule from the one for custom variables — see §Variable Naming Rules.

### Built-in Output Variables

Every HTTP Request node emits four built-in output variables in addition to the key paths you extract [source: https://help.webexconnect.io/docs/http-request-node]:

| Variable | Contains |
|---|---|
| `https.statusCode` | HTTP status code of the response |
| `https.statusText` | HTTP status text of the response |
| `https.responseBody` | Response body |
| `https.responseHeaders` | Response headers |

Reference them with the node prefix, e.g. `$(n3.https.statusCode)`.

### Timeouts and the `onTimeout` edge

| Field | Detail |
|---|---|
| **Connection Timeout** | Time allowed to establish the connection. *"Starting release v5.6.3 onwards, the max. timeout configuration is 20,000 milliseconds"* |
| **Request Timeout** | Time allowed for the request to complete. Same 20,000 ms maximum from v5.6.3 onwards |
| **Proxy address** (optional) | An additional IP through which the HTTP URL is reached |

The node has a third exit edge beyond success and error: *"outcome onTimeout - this is the duration after which the HTTP request times out"* [source: https://help.webexconnect.io/docs/http-request-node]. Wire it — an unwired `onTimeout` leaves the flow with nowhere to go on a slow backend.

### Query Parameter Encoding

The node encodes query parameters using standard URL encoding — spaces become `+` and special characters are percent-encoded [source: https://help.webexconnect.io/docs/http-request-node]. This matters for PostgREST-style filters such as `ilike.*value*`, which contain characters that will be encoded on the wire.

---

## HTTP Request Node -- POST Requests

For create/update operations:

### Method: POST

### Additional Headers

If your backend supports it, add a header to return the created record in the response. For example, PostgREST-compatible APIs use:

```
Prefer: return=representation
```

This returns the created record so you can capture auto-generated IDs, confirmation numbers, etc.

### Body

- Set body type to **JSON**
- Use the **variable picker** to insert values from previous HTTP nodes or AI agent entities
- Example body referencing a previous node's output and AI agent slot entities:

```json
{
  "customer_id": "$(n3.customer_id)",
  "location_id": "hardcoded-known-uuid",
  "item_id": "$(n2.aiAgent.item_id)",
  "scheduled_at": "$(n2.aiAgent.scheduled_at)",
  "status": "active"
}
```

---

## HTTP Request Node -- PATCH Requests

For updating existing records (reschedule, cancel, status changes).

### Method: PATCH

### URL

Include filters to target the specific record:

```
https://{api-base-url}/{table}?{unique_filter}
```

Example -- cancel a record by ID:

```
/rest/v1/{table}?id=eq.$(n3.record_id)
```

### Headers

Same as POST, including `Prefer: return=representation` to get the updated record back.

### Body

Only include the fields being changed:

```json
{
  "status": "cancelled"
}
```

Use the variable picker for dynamic values:

```json
{
  "scheduled_at": "$(n2.aiAgent.new_scheduled_at)",
  "status": "rescheduled"
}
```

### Two-Node Pattern: Lookup Then Update

Most PATCH actions require two HTTP nodes — the caller provides a human-speakable identifier (phone number, confirmation number), but PATCH needs the record's primary key.

```
Trigger (Configure AI Agent Event) → HTTP GET (lookup by phone/confirmation) → HTTP PATCH (update by ID) → End
```

- **Node 1 (GET)**: Look up the record using the caller's identifier. Output the record's `id`.
- **Node 2 (PATCH)**: Update using `$(n{node1}.record_id)` in the filter URL.

---

## HTTP Request Node -- PUT Requests

For full-record replacement (overwrite all fields on an existing record).

### Method: PUT

### URL

Include filters to target the specific record, same pattern as PATCH:

```
https://{api-base-url}/{table}?{unique_filter}
```

### Headers

Same as POST/PATCH, including `Prefer: return=representation` if supported by your backend.

### Body

Include **all fields** for the record — PUT replaces the entire resource, unlike PATCH which updates only specified fields:

```json
{
  "customer_id": "$(n3.customer_id)",
  "location_id": "hardcoded-known-uuid",
  "item_id": "$(n2.aiAgent.item_id)",
  "scheduled_at": "$(n2.aiAgent.new_scheduled_at)",
  "status": "rescheduled",
  "notes": "$(n2.aiAgent.notes)"
}
```

### PUT vs PATCH

| Method | Behavior | When to Use |
|--------|----------|------------|
| **PATCH** | Updates only the fields you send | Most update operations — changing status, rescheduling |
| **PUT** | Replaces the entire record with what you send | Full-record rewrites where omitted fields should be cleared |

**Default to PATCH** for AI agent actions. PUT is available if the backend API requires it, but PATCH is safer — you won't accidentally null out fields you forgot to include.

---

## HTTP Request Node -- DELETE Requests

The HTTP Request node supports five methods: **GET, POST, PUT, PATCH and DELETE** [source: https://help.webexconnect.io/docs/http-request-node]. DELETE is selected from the same **Method** dropdown as the others.

Target the record with URL filters, the same way PATCH does:

```
https://{api-base-url}/{table}?{unique_filter}
```

The official node page does not document a request body for DELETE — check your backend API's requirements before adding one.

---

## Variable Picker

### Format

```
$(n{nodeNumber}.aiAgent.{entity_name})
```

- `n{nodeNumber}` -- the trigger node number (changes based on flow layout)
- `aiAgent` -- indicates the variable came from the AI agent
- `{entity_name}` -- the slot entity name

> **The `aiAgent` path segment is not documented in official docs.** The AI Agent fulfillment page shows no variable-syntax example at all [source: https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions]. Use the variable picker to confirm the exact format your tenant produces — do not type this path from memory.

### Rules

- **NEVER type variable references manually** -- always use the variable picker (click the variable icon in the URL or body field)
- Manually typed variables will arrive empty at runtime with no error
- The picker auto-generates the correct `$(nX.variableName)` syntax

### Referencing Previous Node Output

When chaining HTTP nodes, reference output variables from an earlier node:

```
$(n{nodeNumber}.{variableName})
```

Note: no `aiAgent` prefix -- this is a direct node output reference, not an AI agent entity.

### Inbound webhook payload variables

Flows triggered by an **Inbound Webhook** are documented throughout this repo as exposing the parsed payload at:

```
$(n{nodeNumber}.inboundWebhook.{fieldName})
```

> **The `inboundWebhook` path segment is not documented in official docs.** Verified live 2026-07-27: the literal segment `inboundWebhook` appears on **no** Cisco page — checked `variable-management-in-flows`, `inbound-webhooks` (both help.webexconnect.io and developers.webexconnect.io), `configure-fulfilment-flows-for-ai-agent-actions`, and `ai-agent-node`. Cisco documents only the general shape `$(n[nodeID].[nodeType].[fieldName])` [source: https://help.webexconnect.io/docs/variable-management-in-flows], and for inbound webhooks shows **dot-notation over the parsed payload** (`employee.name`, `data.attributes.title`) rather than a fixed `inboundWebhook` segment. **This is not evidence the examples are wrong** — `inboundWebhook` may well be the `[nodeType]` your tenant emits for that node; nothing crawled confirms or refutes it. Only a live tenant's variable picker can settle it. Use the variable picker to confirm the exact format your tenant produces — **do not type this path from memory.**

> **Owner note.** This hedge is the owner for every unhedged `$(nX.inboundWebhook.…)` example elsewhere in the repo — `connect-sms.md`, `connect-whatsapp.md`, `connect-rcs.md`, `connect-email.md`, `connect-apple-messages.md`, `connect-multi-channel.md`, `webex-connect-advanced.md`. Those copies state the pattern as fact; this section wins on any disagreement. Status: **UNRESOLVED** pending a tenant variable-picker check.

---

## Variable Naming Rules

Cisco documents **two different naming rules** for two different kinds of variable. They are not the same rule — do not apply one to the other.

### Rule 1 — HTTP Request node OUTPUT variables

> *"You can only use alphabets, numbers, underscores, hyphens, and spaces in the variable names."* [source: https://help.webexconnect.io/docs/http-request-node]

For these, use lowercase underscores consistently:

- `customer_first_name` -- recommended
- `customerFirstName` -- avoid (camelCase inconsistent with Connect conventions)
- `customer-first-name` -- allowed but inconsistent with underscore convention

### Rule 2 — CUSTOM variables

> *"Variable name can have Alpha Numeric values(for e.g; channel13). We do not support the use of special characters in the variable name."* [source: https://help.webexconnect.io/docs/create-custom-variable-webexconnect]

Custom variables are documented as **alphanumeric only, with no special characters**. Cisco's own worked example is `channel13` — no separator at all. Underscores, hyphens and spaces are **not** listed as permitted here, and the underscore convention recommended in Rule 1 is therefore **not validated for custom variables**. Whether an underscore is rejected as a "special character" is unconfirmed against the tenant UI — when you create a custom variable, prefer a plain alphanumeric name (`oncallnumber`, `retryCount`) unless you have confirmed in your tenant that underscores are accepted.

### All flow variables are case-sensitive

> *"All flow variables are case-sensitive."* [source: https://help.webexconnect.io/docs/variable-management-in-flows]

This applies to every variable category, in every node.

---

## Variable Categories

Cisco documents **five** variable categories [source: https://help.webexconnect.io/docs/variable-management-in-flows]:

| Category | Definition |
|---|---|
| **Input Variables** | *"node-level variables that you can use from the preceding nodes"* |
| **Custom Variables** | *"Variables explicitly defined by you"* |
| **External Variables** | Variables sourced from outside the flow |
| **Output Variables** | *"The auto-generated node-level variables of the current node that can be used in the subsequent nodes in the flow"* |
| **Session Variables** | Platform-controlled — you do not create them |

### Session variables

Session variables are supplied by the platform, not by you. This is how values such as `servicekey` and `deliverychannel` become available inside a flow. The documented examples are `ts`, `servicekey`, `deliverychannel`, `message`, `destination` and `senderid`; the Cisco page does not publish a complete list [source: https://help.webexconnect.io/docs/variable-management-in-flows].

### Two ways to create a custom variable

1. **Node-level** — in a node's **Input Variables** → **Custom Variables** → **+Add new custom variable**
2. **Flow-level** — **Flow Settings** → **Custom Variables** tab

Either way *"they remain available throughout the entire flow regardless of creation location"* [source: https://help.webexconnect.io/docs/variable-management-in-flows; https://help.webexconnect.io/docs/create-custom-variable-webexconnect].

### Output variable naming convention

Output variables *"are prefixed with node IDs (e.g., `nodeid.receive.message`)"* [source: https://help.webexconnect.io/docs/variable-management-in-flows]. This is the same shape as the `$(nX.https.statusCode)` references used throughout this document.

Note the scope: `nodeid.receive.message` is the **generic Receive-node capture variable** (Cisco's own example is `$(n11.receive.message)`), whereas **channel-specific** inbound variables are namespaced by channel instead (`sms.message`, `whatsapp.waId`, `abc.abcUserId`) and carry no `.receive.` segment — two different scopes, not a Cisco contradiction.

---

## Flow Outcomes (Flow Settings — NOT a node)

**Flow Outcomes is not a node.** There is no Flow Outcomes node in the palette and nothing to drop on the canvas. It is a **flow-level settings area** reached from the **Flow Settings** button on the Flow Builder page [source: https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions].

> **Which page documents what.** `https://help.webexconnect.io/docs/flow-settings` covers only the *generic* outcome feature — Flow Outcomes as one of four Flow Settings sections, the default **Success / Error / Incomplete** outcomes, custom outcomes via status code + description, and **Outcome-based Notifications** (HTTP GET/POST/PUT/DELETE callbacks to your own application). It says **nothing** about Last Execution Status, Notify AI Agent, or key-value vs JSON entry. The AI-agent path below comes from `https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions` and from the tenant owner.

Wire the last HTTP Request node to an **End (END FLOW)** node. The data the AI agent receives comes from the Flow Outcomes settings, not from the canvas.

### The Last Execution Status row

Flow Outcomes classifies the result of a flow run. The platform provides three standard outcomes by default — **Success**, **Error**, and **Incomplete** — each with a status code and an optional description, and you can add custom outcomes [source: https://help.webexconnect.io/docs/flow-settings].

For an AI agent action flow the row that matters is **Last Execution Status**: *"In the Flow Outcomes, open the 'Last Execution Status' Outcome."* It *"captures the final node outcome and doesn't require a mapping between node event and flow outcome in the End pop up screen"* and *"automatically captures the last node event and sends a notification to AI Agent"* [source: https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions].

Per the tenant owner, the path is: open the **Last Execution Status** row → enable the **Notify** parameter → under **Notification Settings** select **Notify AI Agent** → enter the keys and values that map back to your action.

> **UNVERIFIED — the "Notification Settings" step.** The string "Notification Settings" does **not** appear on either crawled Cisco page. Cisco describes Notify AI Agent as a radio button that is *"enabled by default for the start node with 'AI Agent' as the trigger"* [source: https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions], i.e. possibly already selected once you open the row. The owner describes it as an explicit selection under a Notification Settings heading. **Whether it is pre-selected or a separate explicit click is unconfirmed — check this in the tenant UI.** Either way, confirm Notify AI Agent is the selected target before publishing.

Disabling the outcome *"prevents the AI Agent from receiving notifications"*; toggling Notify back on *"restores your last configured payload or key-value information"* [source: https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions].

### One key-set per flow

The outcome payload is configured **once, at flow level**. There is no way to return a different key-set from different Branch legs, because there is no canvas terminal to attach a payload to. If different paths must return different data, set variables on each path and return them through the single Last Execution Status key-set — see the Branch pattern in `webex-connect-advanced.md`.

(Non-AI-agent flows can additionally notify an external application per outcome over HTTP GET/POST/PUT/DELETE — "Outcome-based Notifications" [source: https://help.webexconnect.io/docs/flow-settings]. That is a separate mechanism from Notify AI Agent.)

### Enter key and value vs. Enter JSON

Two entry modes exist: *"Select 'Enter key' and 'value' or 'Enter JSON' to use the nested payloads"* [source: https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions].

**Critical:** Always use **Enter key and value**, NOT Enter JSON mode.

Enter JSON mode does NOT resolve variables -- it returns literal strings like `$(n3.customer_id)` instead of the actual value. This is a platform bug/limitation with no workaround other than using **Enter key and value**. *(This variable-resolution failure is a project finding; the Cisco page documents both modes but does not describe this behaviour — treat the cause as **unverified**, the workaround as settled.)*

Cisco's documented rules for the payload:

- Default key-value pairs are pre-populated for **TransactionID**, **service name**, and **status code**; you can add more or delete entries as required [source: https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions]. *(This file previously also listed **flow name** as a fourth default. The tenant owner's ground-truth list has three, not four — **flow name is unconfirmed**; verify in the tenant UI before relying on it.)*
- *"Variables can be added with a '$' prefixed. Variable names are case-sensitive."* [same source]
- Maximum payload length: **16,000 characters** [same source]

### Configuration Steps

1. On the canvas, wire the **last HTTP Request node** to an **End (END FLOW)** node. Do not look for a Flow Outcomes node — there isn't one.
2. Click **Flow Settings** on the Flow Builder page, then click **Flow Outcomes** [source: https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions]
3. On the **Last Execution Status** row, enable the **Notify** parameter
4. Confirm **Notify AI Agent** is the selected notification target. The owner reports selecting it under **Notification Settings**; Cisco documents it as pre-selected by default for AI Agent start nodes. **Unverified which — verify in the tenant UI, but either way check it is selected**
5. Choose **Enter key and value** — never **Enter JSON**
6. Add one row per variable to return to the AI agent:
   - **Key**: the name the AI agent will reference (e.g., `customer_first_name`)
   - **Value**: use the **variable picker** to select from HTTP node output (variables are `$`-prefixed and case-sensitive)
7. Click **Make Live** to publish; select the assets used and enter comments before going live [source: https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions]

### If the agent receives nothing

Check that **Notify** is enabled on the **Last Execution Status** row and that **Notify AI Agent** is the selected notification target. Disabling the outcome prevents the AI agent from receiving notifications; re-enabling Notify restores the last configured key-value payload [source: https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions].

---

## Configure AI Agent Event (Sample JSON)

Every action requires a sample JSON payload on the flow's **trigger node**. Double-click the trigger node — with the trigger category set to AI Agent it presents as **Configure AI Agent Event**.

**You do not start from an empty field.** *"A sample input JSON is provided by default in the **Provide sample JSON** which you can modify within the Webex AI Agent Studio."* [source: https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions]. So the sequence is: the default sample is already in the field, you shape it to match the action's inputs, and after providing it you *"click **Parse** to view the sample payload's parameters as output variables"* [same source]. Without the Parse step the parameters are not available as output variables to downstream nodes.

This tells Connect what shape of data to expect from the agent.

### Slot entities must be expressed as JSON

Entities collected by slot filling are supplied to the flow as JSON key-value pairs — for example `{"city": "city_value", "country": "country_value"}` [source: https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions]. Convert the action's declared slot entities into that shape when you build the sample payload.

### The Service dropdown is client-level only

When you bind the flow from the other side — AI Agent Studio → **Actions** → **Webex Connect Flow Builder Fulfillment** — you *"Select the Service (client-level workspace only)"* and then select the flow [source: https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions]. A flow built in a **group-level or team-level** workspace will not appear in that dropdown at all.

### Format

```json
{
  "phone_number": "5551234567",
  "preferred_date": "2026-03-15"
}
```

### Rules

- One key per slot entity the action declares
- Use realistic example values (actual test data works well)
- Keys must match the entity names in AI Agent Studio exactly

---

## Chaining Multiple HTTP Nodes

One action = one Connect flow, but you can chain multiple HTTP Request nodes inside a single flow when an action requires multiple API calls (e.g., look up a customer ID, then create a record using that ID).

### How to Chain

1. Add a second HTTP Request node after the first
2. Wire first node's **Success** output to the second node's input
3. Reference output variables from the first node in the second node's URL or body using the variable picker
4. Variable format from a previous node: `$(n{nodeNumber}.{variableName})`

### Example: Two-Node Flow

- **Node 3** (GET): Looks up customer by phone number, outputs `customer_id`
- **Node 5** (POST): Creates a record using `$(n3.customer_id)` in the body

---

## Common URL Patterns (Generic REST/PostgREST)

| Operation | URL Pattern |
|-----------|-------------|
| Exact match lookup | `/{table}?{column}=eq.$(n2.aiAgent.{entity})` |
| Fuzzy text search | `/{table}?{column}=ilike.*$(n2.aiAgent.{entity})*` |
| Date range filter | `/{table}?{date_col}=gte.{start}&{date_col}=lte.{end}` |
| Sort + limit | `&order={column}.asc&limit=3` |
| Hardcoded filter | `/{table}?{column}=eq.{known_uuid}` |

---

## Testing and Debugging a Flow

Before wiring a flow to an AI agent action:

1. Use **curl** (or any HTTP client) to test the raw API URL with the same headers
2. Verify the response shape matches what your output variables expect
3. Trigger the flow (via a test AI agent session in AI Agent Studio, or by whatever its trigger category is), then read the execution in **Flow Debug**

> **There is no "Test Flow" control.** No Cisco page documents a flow-level Test Flow button. Individual nodes do have their own test panels — Branch has a testing mode that validates configured conditions against sample inputs, Data Parser has a testing-data step, Evaluate has a Variable Name / Value test panel — but the flow-level equivalent is **Flow Debug** [source: https://help.webexconnect.io/docs/flows-introduction; https://help.webexconnect.io/docs/navigate-flow-builder-canvas; https://help.webexconnect.io/docs/branch-node].

### Flow Debug (per-flow)

Open it from the **Flow Debug** icon in the flow canvas's **right navigation panel**. It opens as a split view at the bottom of the canvas showing *"a list of 10 most recent flow runs"* and a *"step-wise execution trace for your recent flow executions"* [source: https://help.webexconnect.io/docs/transaction-logs-and-debugging].

**Three log levels:**

| Level | Contains |
|---|---|
| **Level 1 — Summary Logs** | Run summary, no PII |
| **Level 2 — Sequence Summary** | The node execution sequence, with timing |
| **Level 3 — Node Execution Details** | Full parameters; may be encrypted |

**Transaction log fields:** Timestamp (with timezone), Transaction ID, Invoked By, Time Taken, Last Node, NodeID, Outcome, Details [source: https://help.webexconnect.io/docs/transaction-logs-and-debugging].

**Latency and retention:** logs appear within roughly **two minutes** and are retained for the **latest 30 days**. Filter by transaction ID and date range [same source].

**Descriptive Logs must be enabled per flow**, under **Flow Settings**. Cisco warns: *"this feature is suggested to be used only during initial flow set-up and troubleshooting. Enabling this feature in production mode can impact your tenant performance."* The two debug transition actions (`[DEBUG] Log all Flow Variables to Transaction Log` and `[DEBUG] Log a Value to Transaction Log`) depend on it [same source].

**PII decryption is permission-gated.** Node Execution Details are *"available only to users authorized by the tenant owner"*, and *"only users who are authorized by the client admin can decrypt these detailed logs to view them in plain text"* [same source].

### Debug Console (tenant-wide)

Flow Debug is per-flow and shows only the last 10 runs. The **Debug Console** is the tool for *"transaction details and historical logs for all your API, flow, and rule executions"* [source: https://help.webexconnect.io/docs/console].

**Realtime vs Buffered logs:**

| Mode | Availability | Query window |
|---|---|---|
| **Realtime** | ~2-minute delay | Up to 30 days back |
| **Buffered** | Up to 10 minutes to become accessible | Single-day queries only, within 30 days |

**The three flow transaction types** [same source]:

- **Node Outbound** — API calls sent by the Webex Connect system to the integrating system
- **Inbound Event** — API calls sent by the integrating system to the Webex Connect system
- **Async Event** — API calls sent to the integrating system for which the response is received after a certain time lag

**Archive search** extends retention: base retention is 30 days; with archive search enabled, queries extend to a **60–90 day** maximum [same source].

### Node error codes

Cisco publishes a complete per-node response-code table at https://help.webexconnect.io/docs/references-flowbuilder-response-codes. The codes are per-node, so the same number means different things on different nodes:

| Node | 3001 | 3002 | 3003 | 3004 |
|---|---|---|---|---|
| HTTP | validation fail | http exception | http response null | — |
| Evaluate | validation fail | script execution fail | invalid result | — |
| Data Parser | validation fail | invalid datatype | mandatory path not found | exception |
| CallWorkflow | validation fail | workflow not available | — | — |
| SMS | message not available | http exception | endpoint unreachable | gateway exception |
| ExternalEvent | validation fail | invalid event occurs | — | — |
| Transform | validation fail | transform exception | — | — |

Additional tables exist on the same page for AddToQueue, CDR, Error, ReceiveSMS, Redirect, Repository and ServiceBundle.

---

## Known Gotchas

| Issue | Cause | Fix |
|-------|-------|-----|
| Variable arrives empty in URL | Variable not substituted -- typed manually instead of using picker | Use variable picker, never type manually |
| `401` error | Auth headers missing or malformed (e.g., missing space after `Bearer`) | Verify auth headers exactly match API requirements |
| `400` error | Wrong filter column or invalid query syntax | Check URL -- ensure filter column matches actual DB column name |
| `406` error | Single-object Accept header used but query returned 0 rows | Remove single-object Accept header, or fix filter to match a row |
| Flow Outcomes variables show as literal strings | Using Enter JSON mode instead of **Enter key and value** | Switch to **Enter key and value** in Flow Settings > Flow Outcomes |
| Array response breaks output variables | Using single-object Accept header with an array response | Remove the single-object Accept header |
| Flow execution exceeds the 30-second limit in an agent flow | Restricted Waiting Node in use (Delay, Social Hour Check, **Receive Node**, Call Workflow) | Remove the restricted node. The Receive Node restriction is unqualified — there is no "one instance is fine" allowance |
| Output variable name collision | Multiple HTTP nodes both have a variable named `id` | Use distinct, descriptive field names in the sample JSON you parse (e.g. `customer_id`, `order_id`). Renaming output variables *after* parsing is not documented in official docs |
| Flow never triggers | The action in AI Agent Studio is not pointed at this flow (the flow is selected there, not named in Connect) | In AI Agent Studio > Actions > **Webex Connect Flow Builder Fulfillment**, select the service and then the flow. Confirm the flow is **Live** and lives in the Client-level workspace |
| Notify AI Agent is OFF | Flow runs but agent never receives data | In Flow Settings > Flow Outcomes, enable **Notify** on the **Last Execution Status** row and select **Notify AI Agent** |
| HTTP 4xx/5xx doesn't trigger onError edge | HTTP errors are **expected** to go through **onSuccess** (the request completed), with onError for connection / invalid-input failures — a **strongly-supported inference, not a documented statement**. ⚠️ Cisco never states this outright; the node page says only that onSuccess fires when the request "is successfully executed" and onError when it "cannot be processed due to invalid input" [source: https://help.webexconnect.io/docs/http-request-node; owner: `webex-connect-advanced.md` § 4xx/5xx Is Expected to Go Through onSuccess] | Branch on `$(nX.https.statusCode)` after the HTTP node — **the remedy is correct either way**, so build it regardless of which edge fires. See `webex-connect-advanced.md` for the Branch node pattern. |

---

## Node Palette Inventory

The full palette Cisco documents, by category [source: https://help.webexconnect.io/docs/nodes]:

| Category | Nodes |
|---|---|
| **Utilities** | Evaluate, Branch, HTTP request, Delay, DataParser, Data Transform, Call Workflow, Page connector, Profile, Generate OTP, Validate OTP, SocialHour, Cryptographic Hash, Decryption, Encryption |
| **Channels** | Send SMS, Push, RCS Capability, RCS Message, In-app messaging, Email, Messenger, Send Voice, Apple Messages for Business, WhatsApp, Receive |
| **Embedded Voice** | Call User, Voice Node Group, Play, Record, Collect Input, IVR Menu, Call Patch |
| **Integrations** | Create Chat, Validate Chat, Inbound Webhooks, Outbound Webhooks, Custom Events, Generic Bot, Custom Node |

### AI Agent node (Process Message / Close Session)

Used in **digital inbound conversation flows**, not in AI agent *action* flows. `docs/reference/digital-inbound.md` is the owner for how to wire it; named here so the palette inventory is complete.

| Outcome | Colour |
|---|---|
| `onSuccess`, `onAgentHandover` | green |
| `onTimeOut` — **15-second threshold** | amber |
| `onError`, `onInvalidCustomerID`, `onInvalidMessage` | red |

Output variables: `TextResponse`, `FullResponse`, `Datastore`, `TransactionId`, `SessionId`, `ConsumerId`, `MessageMetadata`, `SessionMetadata`, `ResponsePayload`.

> **Different variable syntax.** On this node, Custom Parameters are read as `${consumerData.extra_params.<key>}` and Message Parameters as `${extra_params.<key>}` — `${...}` braces, not the `$(...)` parentheses used everywhere else in this document.

**Rate limit:** *"The default rate limit for AI Agents for a tenant is 240 transactions per minute"* [source: https://help.webexconnect.io/docs/ai-agent-node].

---

## Error Handling and Flow Wiring

### The three node-level exception events

| Event | Cisco's definition |
|---|---|
| `onError` | *"Triggered when a flow fails due to internal errors within a node operation"* |
| `onPolicyFail` | *"Activated when policy-related constraints are violated during node execution"* |
| `onTimeOut` | The node's configured time budget was exceeded |

[source: https://help.webexconnect.io/docs/exception-handling-at-the-node-level]

`onPolicyFail` is a **third** exception event, distinct from `onError`. Wire it — a node that only has `onError` and `onTimeOut` wired can still exit through an unhandled path.

### Exception handlers can branch, not just terminate

*"there are cases when you may want to branch the flow i.e. transition to some other node in case of onError or other such events"* [same source]. An exception event does not have to end the flow — retry, fall back, or route to an alternate path.

### Flow result codes on termination

When you configure an exception handler you select the flow result the run ends with. Documented examples: **102 — Flow completed with an error**, **103 — Flow ended due to an interruption** [same source].

### How you actually create a terminating edge

There is no "End node" you drag from the palette for this. Drag the edge from the node's right-edge dot *"and release it in the free space"* — that opens a configuration window where you select the node event and its corresponding flow result [source: https://help.webexconnect.io/docs/node-transitions].

### Every node event must be wired separately

*"there may be multiple node events associated with the same node (e.g., onSuccess, onError, onPolicyFailure, etc.). You will need to complete this step for all such events separately."* [same source]

### The intermediate-vs-final checkbox

The transition config carries a checkbox marking *"whether this is an intermediate break point in the flow or the final flow termination"*. It applies only to *"specific pre-built integration nodes"*; the documented guidance is to skip it in the general case [same source].

### Connector colour semantics

*"connector colors indicate outcome types (green for continuation, orange for time-bound events, red for errors)"* [source: https://help.webexconnect.io/docs/nodes].

### The node config dialog has three tabs

**Configuration**, **Transition actions**, and **Data Streams** [source: https://help.webexconnect.io/docs/nodes]. The Data Streams tab is not covered elsewhere in this repo.

---

## Flow Limits

| Limit | Value | Source |
|---|---|---|
| **Flow size** | *"The maximum allowed flow size is 10 MB, we recommend keeping your flow size below this limit to avoid issues with saving or publishing flows."* | https://help.webexconnect.io/docs/flows-introduction |
| **Nodes per flow (recommended)** | *"For best user experience, we recommend you to keep number of nodes within a flow to be lesser than 150"* — this counts nodes on other pages reached via Page Connector, not just the visible canvas | https://help.webexconnect.io/docs/faqs-visual-flow-builder |
| **Node executions per flow (hard)** | *"For all the flows created after the v6.3.0 release, there is a limit of 1000 for the number of node executions within a single flow."* | https://help.webexconnect.io/docs/transaction-logs-and-debugging |
| **Canvas performance** | Roughly 200 nodes on one canvas degrades performance — Page Connector exists partly for this reason | https://help.webexconnect.io/docs/page-connector-node |
| **Inbound webhook payload** | *"whenever the inbound webhook requests contain payloads of size higher than the limit configured at the tenant level, the request is rejected with an error code - 430."* Default 256 KB, tenant-adjustable | https://help.webexconnect.io/docs/inbound-webhooks |
| **Flow Outcomes payload** | 16,000 characters — see §Flow Outcomes | https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions |

> **The 1000-node-execution cap is a runtime limit, not a design-time one.** A flow with 20 nodes can still hit it if it loops. Retry-loop patterns are the usual cause — count executions, not boxes on the canvas.

---

## Flow Lifecycle — Draft, Live, Rollback

### Working Draft vs Live

*"Changes made to the working draft do not affect the live functioning of flow until the flow is made live."* and *"Every flow is assigned a version when it is made live."* [source: https://help.webexconnect.io/docs/flow-version-history]

### The three canvas buttons

| Button | Effect |
|---|---|
| **Save** | Creates/updates the working draft. Does not affect the live flow |
| **Make Live** | Publishes a new version |
| **Edit** | Creates a new draft from the live version |

[source: https://help.webexconnect.io/docs/navigate-flow-builder-canvas]

### You cannot publish a flow with errors

*"You cannot make a flow live if the flow has errors, however, you can save it as a draft."* [source: https://help.webexconnect.io/docs/flow-version-history]

### Rollback

*"You can view any previous version of the flow and rollback control to that version by editing it and then making it live."* Editing a prior version creates a draft marked **"Forked from Version X"** [same source].

### Import / export restrictions

*"Flows with custom integration nodes cannot be imported across Webex Connect tenants."* Import and export **within** a client, group, or team level is supported [source: https://help.webexconnect.io/docs/faqs-visual-flow-builder; https://help.webexconnect.io/docs/flows-introduction].

### Read-only sharing

A flow can be shared *"in **Read-only** format with an external user for a brief view"* [source: https://help.webexconnect.io/docs/flows-introduction].

### Voice flows must end with Disconnect

*"Every voice flow must start with a Start node and end with a Disconnect node."* [source: https://help.webexconnect.io/docs/flows-introduction]

---

## Triggering Flows Programmatically

### Authentication — owned by `connect-auth.md`

Service keys, JWT tokens (claims, 60-minute lifetime, priority over the service
key), HMAC signature validation, IP allowlisting, credential rotation, and the
three Custom Event rules (auto-generated `evtid`, mandatory Service Key, and the
silent group-scoping failure) are all owned by **`connect-auth.md`**.

> **The group-scoping failure is the one to memorise when debugging.** You get **HTTP 200 and no flow execution** — nothing in the response tells you the credential was scoped to the wrong group. If a flow "never triggers" but the API call succeeds, check the credential's group before anything else [`connect-auth.md` § Custom Event Authentication Rules].

### Inbound webhooks

- Authentication is **optional** for inbound webhooks but **mandatory** for Custom Events — see `connect-auth.md` § Authentication Is Optional — Except Where It Is Not
- They *"work the same way as custom events but are flexible with the input JSON/XML body that will be parsed as JPath/Xpath and the variables will be made available in flows/rules"* [source: https://help.webexconnect.io/docs/inbound-webhooks] — this is how you accept an arbitrary third-party payload without pre-declaring its shape
- Payload cap: see §Flow Limits (default 256 KB, rejected with error code **430** — see `connect-response-codes.md`)
- Build procedure: `docs/playbooks/webhook-triggers.md`

---

## Production Operations

### Concurrency

*"Concurrency in Webex Connect refers to the ability to execute multiple flow threads in parallel."* Tenant owners can *"reserve 75% of the 'Maximum Allocated flow concurrency' against flows"*; the remaining 25% is first-come, first-serve [source: https://help.webexconnect.io/docs/flow-monitoring].

### Mean Thread Rejection Rate

*"In instances when the reserved/available concurrency is very low compared to the load on the flow, one may observe a higher 'Mean Thread Rejection Rate' as Connect keeps on retrying the queued requests on constant intervals."* [same source]

### Flow Monitoring metrics

Flow Invocation & Resume Volume, Median/Mean/Peak Thread Execution Rate, Average Thread Execution Time, Mean Thread Rejection Rate, and Reserved Concurrency — over a window from 1 hour to 30 days [same source].

### Flow Analytics

An **add-on** feature giving *"an aggregate view of the execution counters at every node"*. Data refreshes every **15 minutes**. Provides per-node and per-connector counters, Sankey charts, and SVG/PNG/CSV export. Only versions published **after** analytics was enabled are selectable [source: https://help.webexconnect.io/docs/flow-analytics].

---

## Custom Nodes (Webex API Integration)

Custom Nodes let you call Webex platform APIs (People, SCIM2, Calling) from Connect flows with **managed OAuth** — no manual Bearer tokens or refresh logic. Connect handles the full OAuth lifecycle (authorization code grant, token refresh) transparently.

**Token refresh mechanism:** When you configure OAuth on the Custom Node, you set the **Refresh URL Token** and enable **"Access token has a limited validity"** with the token's lifespan. Connect tracks the token validity internally and automatically calls the Refresh URL Token endpoint to obtain a new access token when the current one expires. The official Cisco documentation for Email assets states: *"Token has a fixed expiry time and the backend application automatically calls the API to regenerate token before that."* The Custom Node docs do not specify whether this refresh is a background process or triggered at call time — treat it as platform-managed and opaque. Each refresh also resets the refresh token's 90-day expiry, so the integration stays authorized indefinitely as long as the refresh token is used before it expires.

[source: [Custom Node Integration](https://help.webexconnect.io/docs/custom-nodes-integration); [Email - WXCC](https://help.webexconnect.io/docs/wxcc-email-asset-creation)]

### When to Use Custom Nodes vs Raw HTTP

| Scenario | Use |
|----------|-----|
| Calling your own backend (Supabase, custom API) | Raw HTTP Request node with API key |
| Calling Webex APIs (People, Calling, SCIM2) | Custom Node with OAuth — token refresh handled automatically |
| Calling WxCC APIs (CC Config, Search) | Either — but raw HTTP with a stored token works fine for simple calls |

### Prerequisites

| Requirement | Details |
|-------------|---------|
| Webex Integration | Created at developer.webex.com (NOT a Service App — Integrations support Authorization Code grant) |
| Redirect URI | **Do not guess or construct it.** Create the Custom Node first (Step 2 below), open its OAuth config, and copy the **Call Back URL** that Connect auto-populates. Cisco publishes no callback-URL format — the only thing the official page states about it is: *"The callback URL is not accessible through a web browser. You need to test it using the custom node only."* [source: https://help.webexconnect.io/docs/custom-nodes-integration] |
| Scopes | API-specific (e.g., `spark-admin:people_read`) plus `spark:kms` |

### Create the Webex Integration

1. Go to **developer.webex.com** → avatar → **My Webex Apps** → **Create a New App** → **Integration**
2. Set **Will this integration use a mobile SDK?** to **No**
3. Set **Redirect URI** to the **Call Back URL** that Connect auto-populates in the Custom Node's OAuth config — copy it verbatim, do not type a URL from a pattern. If you have not created the Custom Node yet, create it first (see *Create the Custom Node* → *Configure Authorization* below), copy the Call Back URL from there, then come back and fill this field
4. Select required **Scopes** (e.g., `spark-admin:people_read`, `spark:kms`)
5. Record **Client ID** and **Client Secret**

### Create the Custom Node

1. In Webex Connect: **Assets → Integrations → Add Integration → Custom Node**

| Field | Value |
|-------|-------|
| **Creation type** | From blank (or copy an existing node) |
| **API Integration Type** | REST (or SOAP — use REST for Webex APIs) |
| **Node name** | Descriptive name (e.g., "Webex People Lookup") |
| **Description** | Optional — what this node does |
| **Node category** | Choose or create a category (e.g., "Webex APIs") |
| **Node icon** | Optional SVG file (64×64 pixels) |

[source: [Custom Node Integration](https://help.webexconnect.io/docs/custom-nodes-integration)]

### Add a Request Method

Each Custom Node supports **up to 25 distinct request methods** (limit enforced from v5.6.0). Each method has its own independent authorization config, URL, parameters, and response mapping — authorization does NOT inherit from one method to another. Different methods on the same node can use different auth types (e.g., method 1 uses OAuth 2.0, method 2 uses Basic Auth).

When the Custom Node is placed on the flow canvas, the user selects which method to invoke via a **"Method Name" dropdown** in the node configuration dialog.

Example: "GetPersonByEmail" for the People API.

[source: [Custom Node Integration](https://help.webexconnect.io/docs/custom-nodes-integration)]

| Field | Value |
|-------|-------|
| **Method name** | GetPersonByEmail |
| **Type** | GET |
| **Resource URL** | `https://webexapis.com/v1/people` |
| **Request Timeout** | 2000ms |
| **Connection Timeout** | 2000ms |

### Configure Authorization

Custom Nodes support **Basic Auth**, **Digest Auth**, **AWS Signature** and **OAuth 2.0**, plus a **No Auth** option when the target API needs no authorization. This section covers OAuth 2.0 (the most common for Webex APIs). For the other types see [Custom Node Integration](https://help.webexconnect.io/docs/custom-nodes-integration).

In the method's **Authorization** section:

| Field | Value |
|-------|-------|
| **Type** | OAuth 2.0 |
| **Grant Type** | Authorization Code — see Grant Type note below |
| **Consumer ID** | Integration Client ID (from Step 1) |
| **Consumer Secret** | Integration Client Secret (from Step 1) |
| **Call Back URL** | Auto-populated by Connect — copy this and register it in your OAuth provider's redirect URI list |
| **Authorization URL** | `https://webexapis.com/v1/authorize` |
| **Scopes** | Space-separated scope list (e.g., `spark-admin:people_read spark:kms`) |
| **Access Token URL** | `https://webexapis.com/v1/access_token` |
| **Access Token URL Method** | POST (default for Webex) |
| **Access Token URL Parameter type** | Body (or URL — depends on provider) |
| **Access Token URL Headers** | Leave blank unless the provider requires additional headers |
| **Access token has a limited validity** | Checked (enabled) |
| **Validity** | `14` days (Webex OAuth access token lifespan) |
| **Refresh URL Token** | `https://webexapis.com/v1/access_token` |
| **Client Authentication** | Send client credentials in body (default — correct for Webex) |

After filling in these fields, click **Authorize** (or **Get Access Token**). A **browser popup window** opens:

1. The popup navigates to the **Authorization URL** you configured (for Webex: the Webex login page)
2. The user signs in with their Webex account (if not already logged in)
3. A **scope consent screen** appears showing the requested permissions — the user clicks **Accept**
4. The popup redirects to the Call Back URL (handled by Connect's server) and **closes automatically**
5. Back in the Custom Node config, the **Access Token** and **Refresh Token** fields auto-populate

If the popup is blocked by the browser, authorization will fail silently — ensure popups are allowed for the Connect domain. If authorization fails, the third-party provider's error message is displayed in the popup.

> **Grant Type — when to use which:**
> - **Authorization Code**: use for APIs that issue tokens in the context of a user (requires browser popup for consent). **Webex APIs only support Authorization Code** — they do not accept `grant_type=client_credentials`. If you are calling Webex APIs (People, SCIM2, Calling), you must use Authorization Code.
> - **Client Credentials**: use for third-party APIs that support machine-to-machine tokens without user context (no browser popup needed). Only use this if the target API provider explicitly supports it (e.g., some ServiceNow, Salesforce configurations).
>
> **Client Authentication options:** Two choices — "Send client credentials in body" (default, sends `client_id` and `client_secret` as POST body parameters) and "Send as Basic Auth header" (sends `Authorization: Basic <base64(client_id:client_secret)>` header). Webex supports both; use the default ("Send client credentials in body") — this matches all Cisco example code.
>
> **`spark:kms` scope:** Required for key management. Always include it alongside your functional scopes.
>
> **Validity field:** This tells Connect when to refresh. Set it to match the actual access token lifespan (14 days for Webex OAuth tokens).
>
> **Refresh URL Token:** Connect uses this endpoint to obtain a new access token when the current one expires. For Webex, it's the same endpoint as the Access Token URL.
>
> **Call Back URL:** Connect auto-populates this field. **Copy the exact string Connect shows you** and register it in your OAuth provider's redirect URI list. Cisco publishes **no** callback-URL format and **no** region list — the only documented statement about it is *"The callback URL is not accessible through a web browser. You need to test it using the custom node only."* [source: https://help.webexconnect.io/docs/custom-nodes-integration]. Do not construct this URL from a template.
>
> *Recorded but **unverified** (project observation, not Cisco documentation): earlier revisions of this file carried two mutually incompatible templates — `https://oauth.us.webexconnect.io/callback` and `https://oauth.[tenantName].[region].webexconnect.io/callback` — along with a region list of `us` (Oregon/AWS), `us1` (USA/Azure), `eu` (Ireland), `uk` (London), `ca` (Canada), `in` (Mumbai), `au` (Sydney), `sg` (Singapore). A URL cannot match both templates, so at least one is wrong, and neither is sourced. Kept here only so the observation is not lost; do not build from it.*
>
> **Re-authorization triggers:** If you edit the OAuth config in the admin portal, you will be prompted to re-authorize. If credentials are updated in the integrating system, Connect loses access and users must re-authorize manually. Existing integrations are not impacted until the Refresh Token expires or you decide to reauthorize.

[source: [Custom Node Integration](https://help.webexconnect.io/docs/custom-nodes-integration); [Webex Integrations and Authorization](https://developer.webex.com/docs/api/guides/integrations-and-authorization); [Product Update July 2022](https://help.webexconnect.io/changelog/product-update-july-2022)]

### Configure Security (Optional)

If the target API requires mutual TLS or a specific SSL/TLS version:

**Key Store** (client certificate):

| Field | Value |
|-------|-------|
| **Browse Certificate** | Upload your key store certificate file |
| **Select File Format** | JKS or PKCS12 |
| **Store Password** | Password to access the store |
| **Key Password** | Password to access the key |
| **Name** | Descriptive name for the certificate |

**Trust Store** (server certificate):

| Field | Value |
|-------|-------|
| **Browse Certificate** | Upload the trust store certificate file |
| **Select File Format** | JKS or PKCS12 |
| **Store Password** | Password to access the store |

**Security Protocol options:** SSL 2.0, SSL 3.0, TLS 1.0, TLS 1.1, TLS 1.2. Use TLS 1.2.

> For standard Webex API calls, skip this section — no client certificates needed.

[source: [Custom Node Integration](https://help.webexconnect.io/docs/custom-nodes-integration)]

### Define Header Parameters

Add any custom headers the API requires beyond what OAuth provides:

| Parameter | Parameter Value Type | Value / Field Name |
|-----------|---------------------|-------------------|
| `Content-Type` | Static | `application/json` |

- **Static** parameters have a fixed value set here
- **Dynamic** parameters create an input field on the node — the flow passes a value at runtime

> **UNVERIFIED — the auto-injected Authorization header.** This file previously stated that *"the `Authorization: Bearer <token>` header is injected automatically by Connect — do not add it manually"* and cited it to the Custom Node Integration page. **That page contains no such statement** (confirmed by targeted re-fetch, 2026-07-25) — the citation was false, not merely thin. The claim is retained here as an unverified project observation only. Before relying on it, check in your tenant whether an OAuth-configured Custom Node method sends the Authorization header without you defining one.

### Define URL Parameters

| Parameter | Parameter Value Type | Value / Field Name |
|-----------|---------------------|-------------------|
| `email` | Dynamic | Field name: "email" (passed from flow at runtime) |
| `callingData` | Static | Value: "true" |

Same Static/Dynamic distinction as header parameters.

[source: [Custom Node Integration](https://help.webexconnect.io/docs/custom-nodes-integration)]

### Configure Request Body (POST/PUT/PATCH Only)

If the method is POST, PUT, or PATCH, configure the request body:

| Field | Value |
|-------|-------|
| **Body format** | JSON (`application/json`), XML (`application/xml`), Text (`text/plain`), or form-data |
| **Parameters** | Add body fields as Static or Dynamic (same pattern as URL/header parameters) |

Skip this section for GET and DELETE methods.

[source: [Custom Node Integration](https://help.webexconnect.io/docs/custom-nodes-integration)]

### Configure Node Events

Define success/error routing — these become the output ports on the node in the flow canvas:

| Event | Condition |
|-------|-----------|
| **Success** | HTTP Status equals 200 |
| **Error** | HTTP Status not equals 200 |

[source: [Custom Node Integration](https://help.webexconnect.io/docs/custom-nodes-integration)]

### Define Response Object

| Field | Value |
|-------|-------|
| **Response Format** | JSON (or Text/XML depending on API) |
| **Parameter name** | Descriptive name (e.g., "Person") |
| **Body** | Body (also supports HTTP Status or HTTP Header) |
| **Response Path** | JSON path to extract (e.g., `$.items[0]` for first array element, `$` for whole response) |

The output is available downstream as the node's variable (e.g., `$(n3.person)` where `n3` is the node number).

[source: [Custom Node Integration](https://help.webexconnect.io/docs/custom-nodes-integration)]

### Configure Throttling (Optional)

Protect the target API from overload:

| Field | Value |
|-------|-------|
| **Rate Limit** | Max requests per second |
| **Concurrency Limit** | Max parallel Custom Node executions |
| **Volume Limit** | Max Custom Node executions within a time period |

Set these based on the target API's rate limits.

[source: [Custom Node Integration](https://help.webexconnect.io/docs/custom-nodes-integration)]

### Configure Node UI (Optional)

Customize how the node's input fields appear in the flow editor:

| Field | Value |
|-------|-------|
| **Information Text** | Description shown in the node config dialog |
| **Field Type** | Text box, Selection box, or Date and time — for each dynamic input |
| **Regex Validation** | Validation string for text inputs (text box only) |
| **Display Name** | Label for selection box options |
| **Value** | Value of selection box options |
| **Date format** | Format of date fields (Date and time only) |
| **Date-Time Separator** | Separator between date and time (Date and time only) |
| **Time format** | Format of time fields (Date and time only) |
| **Mandatory Parameter** | Whether the field is required |
| **Tooltip** | Help text shown on hover |

[source: [Custom Node Integration](https://help.webexconnect.io/docs/custom-nodes-integration)]

### Activate the Integration

After saving, the integration is **off by default**. Toggle it ON in the integrations list — otherwise the node won't appear in the flow palette.

### Using the Response

Parse the Custom Node output in an Evaluate node. Set the **Script Output** field to `0`:

```javascript
const person_json = JSON.parse("$(n3.person)");
const person_name = person_json.displayName;
const person_status = person_json.status;
```

### Testing the Custom Node

To validate the Custom Node before wiring it into a production flow:

1. Create a test flow with a **webhook-triggered Start node** (generates a unique webhook URL)
2. Wire: Start → Custom Node → Evaluate (parse response) → End
3. In Postman or curl, **POST an empty JSON body `{}`** to the webhook URL to trigger the flow
4. In Webex Connect, open the flow's **debug logs** (decrypt if needed) and inspect the Custom Node output to confirm the response shape and field extraction

> The callback URL configured in OAuth is not accessible through a web browser. You can only test it by executing the Custom Node in a flow.

[source: [Custom Node Integration](https://help.webexconnect.io/docs/custom-nodes-integration)]

### Troubleshooting Custom Node OAuth

| Symptom | Cause | Fix |
|---------|-------|-----|
| Integration shows **"Auth Pending"** or **"re-authorize"** status | Access token and refresh token both expired, OR credentials updated in the integrating system | Navigate to **Assets → Integrations** → select the Custom Node → re-authorize (triggers the OAuth popup flow again) |
| Custom Node returns HTTP 401 at runtime | Access token expired and refresh failed | Same as above — re-authorize. Check that the Refresh URL Token is correct and the refresh token hasn't expired (90-day lifespan for Webex) |
| OAuth popup doesn't appear after clicking Authorize | Browser popup blocker | Allow popups for the Connect domain. Try a different browser if the issue persists |
| OAuth popup shows an error from the provider | Incorrect Consumer ID/Secret, wrong scopes, or redirect URI mismatch | Verify the Consumer ID and Consumer Secret match the Integration at developer.webex.com. Verify the scopes match. Verify the Call Back URL from the Custom Node config is registered as a Redirect URI in the Integration |
| HTTP 429 at runtime | Rate limit exceeded | Reduce request frequency or increase the **Rate Limit** in Throttling config |
| HTTP 430 at runtime | Concurrency limit exceeded | Reduce parallel flow executions or increase the **Concurrency Limit** in Throttling config |
| HTTP 431 at runtime | Volume limit exceeded | Wait for the time window to reset or increase the **Volume Limit** in Throttling config |
| Custom Node not appearing in flow palette | Integration is toggled OFF | Go to **Assets → Integrations** and toggle the integration ON |

> **No proactive token health monitoring:** Cisco does not document email notifications or dashboard indicators for OAuth token expiry on Custom Nodes. Certificate expiry (mTLS) has email alerts at 30/15/7/3/2/1 days before expiry, but OAuth tokens do not. Monitor token health by testing flows periodically or checking the integration status in Assets → Integrations.

[source: [Integrations Troubleshooting](https://help.webexconnect.io/docs/integrations); [Custom Node Integration](https://help.webexconnect.io/docs/custom-nodes-integration)]

> Full walkthrough including Service App and Flow Designer patterns: `docs/playbooks/webex-api-auth.md`

---

## Other Flow Types

This document covers **AI Agent action flows** (trigger node → HTTP Request → End, with the return payload set in Flow Settings > Flow Outcomes). Webex Connect also supports other flow patterns documented in separate playbooks:

- **Outbound voice calls** (webhook → Call User → TTS): see `docs/playbooks/outbound-voice.md`
- **Inbound voice calls** (Start node with Inbound Call trigger → Voice Node Group → Play/Collect Input/Call Patch): see `docs/playbooks/inbound-voice.md`
- **Sequential dialing / on-call connect** (Call Patch chaining inside VNG for find-me/follow-me): see `docs/playbooks/sequential-dialing.md`
- **Webhook-triggered flows** (Start node with inbound webhook): see `docs/playbooks/webhook-triggers.md`
- **Webex Calling paging integration** (Connect → paging group via PSTN): see `docs/playbooks/webex-calling-paging.md`

### Voice Outbound Limitations

Webex Connect's Call User node and Voice API v1 dial via PSTN only. They cannot reach Webex Calling internal extensions — only E.164 phone numbers with PSTN routing. If the target endpoint (e.g., a paging adapter, hunt group, or workspace phone) only has a Webex Calling extension and no DID, Connect cannot dial it directly. See `docs/playbooks/dual-call-paging.md` for workarounds using the WxCC Create Task API.

## See Also

- [webex-connect-advanced.md](webex-connect-advanced.md) — voice and other advanced node types
- [connect-auth.md](connect-auth.md) — inbound webhook authentication
- [digital-inbound.md](digital-inbound.md) — digital-channel flows that start in Connect
- [wxcc-platform.md](wxcc-platform.md) — the Contact Center platform setup Connect flows depend on
- [webhook-triggers.md](../playbooks/webhook-triggers.md) — setting up webhook triggers for Connect flows
