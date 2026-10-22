# Flow Designer Patterns & Advanced Topics

<!-- ref-tag: fd-patterns-v2 -->

> Activity configuration: essentials in [flow-designer-essentials.md](flow-designer-essentials.md), situational activities in [flow-designer-activities/_index.md](flow-designer-activities/_index.md). Platform setup (Control Hub, Queues, Teams, Entry Points, Global Variables) is in [wxcc-platform.md](wxcc-platform.md).

## Flow Versioning

Flow Designer supports **version labels** that enable Blue-Green deployments — promoting flows through Dev → Test → Live environments without disrupting production traffic.

### Three-Stage Environment Model

| Stage | Label | Purpose |
|-------|-------|---------|
| **Development** | `Dev` | Build and test enhancements. Assign "Dev" label to test against an Entry Point without impacting production callers. |
| **Testing** | `Test` | Promote with "Test" label for validation. Creates a separate flow copy for staging — real customer interactions can be routed here via Entry Point configuration. |
| **Production** | `Live` | Deploy with "Live" label after successful testing. This is the label that serves production traffic. |

A fourth pseudo-label, `Latest`, always points to the most recently published version regardless of label assignment.

### How Version Labels Work

1. **Publish with a label:** When publishing a flow, select a version label (Dev, Test, or Live). Each label assignment creates an independent snapshot of the flow at that point in time.
2. **Assign at the Entry Point:** In **Control Hub > Entry Points**, edit the entry point and select which version label to route traffic to. This means the same flow can serve Dev traffic on one Entry Point and Live traffic on another.
3. **Promote without disruption:** Publishing a new version with a "Dev" label does not affect the "Live" label. The Live version continues serving production traffic unchanged until you explicitly publish a new Live version.
4. **Rollback:** Re-assign the Entry Point to a previous version label (or re-publish the prior version with the Live label) to roll back.

### Entry Point Version Assignment

Version labels are assigned at the **Entry Point level**, not the flow level. This means:

- Different Entry Points can point to different versions of the same flow
- A test Entry Point (with a test PSTN number) can run the Dev version while the production Entry Point runs the Live version
- Subsequent updates receive new version labels without disrupting existing traffic on other labels

### Publish and Label Workflow

```
1. Create/edit flow → Publish with "Dev" label
2. Assign Dev Entry Point → Flow (select "Dev" version)
3. Test via Dev Entry Point phone number
4. Satisfied → Publish same flow with "Live" label
5. Production Entry Point already points to "Live" — new version takes effect
```

### `NewContact.FlowVersionLabel`

The output variable `NewContact.FlowVersionLabel` contains the label (`Dev`, `Test`, `Live`, or `Latest`) that was used to enter the current flow execution. Use it in logging, Global Variable writes, or Analyzer reporting to distinguish which environment a call ran through.

### When to Use

- **Always in production deployments.** Never publish directly to Live without testing via Dev or Test first.
- **Multi-team development.** Different teams can test their changes via Dev while production remains stable on Live.
- **Gradual rollout.** Combine with Percentage Allocation (below) to split traffic between old Live and new Live versions.

---

## Percentage Allocation

The **Percentage Allocation** activity splits traffic across multiple flow branches using weighted round-robin distribution. Use it for A/B testing, gradual rollouts, and comparing different CX approaches on live traffic.

### Configuration

| Field | Section | Description |
|---|---|---|
| Activity Label | General Settings | Name for the activity |
| Activity Description | General Settings | Optional description |
| Exit Path Labels | Percentage Allocation | One label per output path. Click **Add New** to add paths (2–10 total). |
| Percentage Weight | Percentage Allocation | Integer percentage for each path. All weights must sum to exactly 100. Range: 0–100 per path. |
| Path Description | Percentage Allocation | Optional description for each output path |

Drag **Percentage Allocation** from the Activity Library onto the canvas, add output paths, assign percentage weights, and wire each output to the desired downstream activity.

### Distribution Algorithm

Percentage Allocation uses **weighted round-robin**, not random sampling. Over a sufficient volume of contacts, the actual distribution converges to the configured percentages. Small sample sizes may show variance.

### Use Cases

| Scenario | Split | Path A | Path B |
|----------|-------|--------|--------|
| IVR modernization | 70/30 | Existing DTMF IVR | New TTS-based IVR |
| Virtual agent pilot | 50/50 | Queue to human agent | Virtual Agent V2 first |
| Three-way comparison | 40/30/30 | DTMF IVR | TTS IVR | Conversational bot |
| Screen pop migration | 70/30 | Old agent screen pop | New screen pop app |
| Gradual rollout | 90/10 → 70/30 → 50/50 → 100/0 | Current flow | New flow (increase over time) |

### Measuring Results

Combine Percentage Allocation with Global Variables to capture which path each contact took:

1. **Create a reportable Global Variable** (e.g., `AB_Test_Path`, type: STRING)
2. On each Percentage Allocation output path, add a **Set Variable** activity that sets `AB_Test_Path` to a label (e.g., `"dtmf_ivr"`, `"tts_ivr"`, `"bot"`)
3. The variable appears in **WxCC Analyzer** as a Contact Session custom field
4. Build Analyzer reports that compare metrics (self-service rate, CSAT, handle time) per path

### Wiring Pattern

```
NewContact
  → Percentage Allocation
      ├── 70% → Set Variable (AB_Test_Path = "current")
      │           → [existing flow logic]
      └── 30% → Set Variable (AB_Test_Path = "experiment")
                  → [new flow logic]
```

### Adjusting Allocations

Edit the Percentage Allocation activity, change the weights, and re-publish the flow. Traffic shifts to the new distribution immediately on the next publish. Combine with Flow Versioning to test new allocations via "Dev" before promoting to "Live."

### Output Variables

| Variable | Description |
|---|---|
| `Percentallocation.percentage` | Stores the next percentage route |
| `Percentallocation.description` | Stores the description of the path |

### WRR Distribution Behavior

The system uses a Weighted Round Robin (WRR) algorithm to distribute traffic, which may create imbalances with small sample sizes. The algorithm resets every time you publish the flow. For example, with a 50%/30%/20% split across 10 calls, the system eventually distributes 5, 3, and 2 calls respectively, but does so dynamically in an adjusted manner with the weights of 5:3:2. One possible sequence for 10 consecutive calls: Path1, Path2, Path1, Path2, Path3, Path1, Path2, Path3, Path1, Path1. Test the flow execution before deploying changes into production.

### 0% Switchboard Use Case

Percentage values range from 0% to 100%. The 0% setting allows you to create switchboard use cases — traffic is turned off on that path by default. You can activate these connections later by changing the allocation to greater than 0%.

### Output Paths

| Output Path | Fires When |
|---|---|
| **Path 1 … Path N** | One output edge per configured path — the WRR algorithm selects the path for the current contact |
| **Undefined Error** | System error during evaluation |

### Error Handling

The Percentage Allocation activity does not expose `FailureCode` or `FailureDescription` output variables. The only error path is the **Undefined Error** edge. If Undefined Error is not wired, the flow falls back to the global `OnGlobalError` event handler.

> **Documentation pending** — behavior when weights do not sum to exactly 100 (whether the flow canvas prevents publishing, or the activity errors at runtime) is not verified against Cisco help docs. The canvas is expected to enforce the sum-to-100 constraint at design time, but test before relying on this assumption.

### Limitations

- Minimum two output paths, maximum ten
- Weights must be integers that sum to exactly 100
- No built-in session affinity — a returning caller may take a different path on their next call

---

## Subflows

Subflows are independent, reusable flow fragments that execute as a single activity within a main flow. They modularize common logic (business hours checks, API calls, queue treatments) so it can be built once and shared across multiple flows.

### Create a Subflow

1. **Contact Center > Flows > Subflows > New Subflow**
2. Name the subflow descriptively (e.g., `RefreshTheToken`, `CheckBusinessHours`)
3. Build logic on the subflow canvas — same activity library as main flows
4. Define **Input Variables** (data the main flow passes in) and **Output Variables** (data the subflow passes back)
5. Publish the subflow

### Subflow Activity Configuration (Main Flow Canvas)

When you drag a **Subflow** activity onto a main flow's canvas, the properties panel shows:

| Field | Section | Description |
|---|---|---|
| Activity Label | General Settings | Name for the activity |
| Activity Description | General Settings | Optional description |
| Subflow | Subflow Settings | Select the subflow from the dropdown of published subflows in the organization |
| Version Label | Subflow Settings | Select which version of the subflow to invoke: Dev, Test, Live, or Latest. Follows the same version label model as main flows. |
| Subflow Input Variables | Subflow Settings | Map main flow variables to the subflow's defined input variables (one mapping per subflow input) |
| Subflow Output Variables | Subflow Settings | Map the subflow's defined output variables back to main flow variables (one mapping per subflow output) |

### Input / Output Mapping

| Direction | Configuration |
|-----------|---------------|
| **Input** | Map main flow variables → subflow input variables. Example: `WEBEX_ACCESS_TOKEN` → subflow's `access_token` input |
| **Output** | Map subflow output variables → main flow variables. Example: subflow's `new_token` output → main flow's `WEBEX_ACCESS_TOKEN` |

Input and output mappings are configured on the Subflow activity's properties panel in the main flow.

### Global Variables in Subflows

Global Variables **cannot be added directly to subflows**. To use a Global Variable's value inside a subflow:

1. In the main flow, read the Global Variable into a local flow variable
2. Pass that local variable as an input to the subflow
3. If the subflow needs to update the Global Variable, return the new value as an output and set it in the main flow

### Propagate Changes

The **"Propagate changes to all flows"** setting on a subflow controls what happens when you publish a new version:

| Setting | Behavior |
|---------|----------|
| **ON** (default) | All main flows that reference this subflow automatically use the new version. One publish updates everything. |
| **OFF** | Each main flow continues using the version of the subflow it was last published with. Main flows must be individually re-published to pick up the new subflow version. |

**Use ON** for shared utility subflows (token refresh, business hours) where you want a single fix to propagate everywhere.

**Use OFF** when a subflow change might break some consumers — lets you update main flows one at a time after validation.

### Common Subflow Patterns

| Subflow | Purpose | Input | Output |
|---------|---------|-------|--------|
| Token Refresh | Refresh OAuth token, update Global Variable | `refresh_token`, `client_id`, `client_secret` | `access_token` |
| Business Hours Check | Determine if current time is within working hours | (none — reads system time) | `is_open` (boolean) |
| Queue Treatment | Play hold music, announce position, offer callback | `queue_id` | `callback_requested` |
| Common API Lookup | Reusable HTTP call to a shared backend | `lookup_key` | `result_json` |

### Version Labels

Subflows support the same version labels as main flows (Dev, Test, Live). The Subflow activity on the main flow canvas lets you select which version label to use.

### When to Extract a Subflow

- Logic appears in **two or more** main flows (DRY)
- A team needs to develop and test a component **independently** of the main flow
- A utility (token refresh, API call) needs a **controlled update path** across many flows
- A flow is becoming too large to manage on a single canvas

Do NOT extract a subflow for logic that only appears in one flow and is unlikely to be reused — the input/output mapping overhead isn't worth it.

### Output Paths

| Output Path | Fires When |
|---|---|
| *(default exit)* | Subflow completes successfully — the flow continues to the next wired activity |
| **Undefined Error** | System error during subflow execution (e.g., referenced subflow not found, subflow encounters an unhandled error internally, input/output mapping failure) |

### Error Handling

> **Documentation pending** — whether the Subflow activity exposes `FailureCode` or `FailureDescription` output variables is not verified against Cisco help docs. The **Undefined Error** edge is the known error path. If Undefined Error is not wired, the flow falls back to the global `OnGlobalError` event handler.

Error scenarios include:
- **Subflow not found:** The selected subflow has been deleted or is not published in the chosen version label
- **Internal subflow error:** An activity within the subflow encounters an unhandled error and the subflow has no internal error handling
- **Mapping failure:** An input or output variable mapping references a variable that does not exist or has an incompatible type

### Limitations

- Subflows cannot contain other subflows (no nesting)
- Maximum subflow depth: 1 level
- Subflow activity timeout follows the calling flow's timeout
- Global Variables cannot be added directly to subflows — pass them as input variables from the main flow

---

## Dynamic Variables in Activities

Several Flow Designer activities accept **variables** in fields that traditionally take static values. This enables runtime behavior changes without editing or re-publishing the flow.

### Supported Activities

| Activity | Dynamic Field | Variable Type | Example |
|----------|--------------|---------------|---------|
| **Business Hours** | Business Hours object | STRING | `{{BH_Schedule}}` — switch schedules per product line |
| **Go To Flow** | Target flow | STRING | `{{Target_Flow}}` — route to different flows per campaign |
| **Go To Entry Point** | Target Entry Point | STRING | `{{Target_EP}}` — redirect to a different Entry Point |

### How It Works

Instead of selecting a static Business Hours schedule, flow, or Entry Point from a dropdown, you select a **flow variable** that contains the ID or name of the target at runtime. The variable value can be:

- Set by a **Set Variable** activity earlier in the flow (based on DNIS, time, caller segment, etc.)
- Read from a **Global Variable** (changed externally via API without re-publishing the flow)
- Returned from a **Function** activity or **HTTP Request** (dynamic routing based on backend data)

### Use Case: Per-DNIS Business Hours

Instead of creating N copies of a flow for N product lines with different schedules, use one flow with a dynamic Business Hours reference:

```
NewContact → Function (DNIS lookup → returns BH schedule name)
  → Set Variable (BH_Schedule = {{function output}})
  → Business Hours ({{BH_Schedule}})
      ├── Open → Virtual Agent V2
      └── Closed → Play Message ("We're closed") → Disconnect
```

### Use Case: Environment-Specific Routing

Combine dynamic variables with Flow Versioning to route Dev and Live traffic differently:

```
NewContact → Condition ({{NewContact.FlowVersionLabel}} == "Dev")
  ├── TRUE → Set Variable (Target_Flow = "Experimental_IVR")
  └── FALSE → Set Variable (Target_Flow = "Production_IVR")
→ Go To Flow ({{Target_Flow}})
```

### Use Case: Reduce Flow Count

Without dynamic variables, supporting 10 product lines × 3 environments = 30 flows. With dynamic variables, you build 1 flow and control behavior via Global Variables or Function lookups. The flow count drops from 30 to 1, and updates are configuration changes instead of flow re-publishes.

### Limitations

- The variable must resolve to a valid target at runtime. If the Business Hours schedule name, flow ID, or Entry Point ID doesn't exist, the activity errors.
- Use the **OnGlobalError** event handler as a safety net for invalid variable values.

---

## Scripted Agent Fulfillment Pattern

When a scripted AI agent needs to call an external API on voice, the fulfillment happens in Flow Designer (not Webex Connect). The agent raises a Custom Event, Flow Designer calls the API, then resumes the agent with the result via a State Event.

> **Also applies to autonomous agents** using custom event fulfillment ("Set custom logic for fulfillment" in AI Agent Studio). The activity chain and State Event resume mechanism are identical.

### The Activity Chain

```
VirtualAgentV2 (ENDED / Custom Event)
  → Parse (extract input from MetaData)
  → Case (branch on StateEventName)
  → HTTP Request (call external API)
  → Condition (check httpStatusCode == 200)
    → TRUE: SetVariable (event_name = "<intent>_confirm_entry")
            → SetVariable (event_data_string = "{{ event_data }}")
            → VirtualAgentV2 (resume via State Event)
    → FALSE: PlayMessage (TTS error) → QueueContact (escalate)
```

### Key Variables

| Variable | Type | Purpose |
|---|---|---|
| `event_name` | STRING | Name of the State Event to send back to the agent (e.g., `check_availability_confirm_entry`) |
| `event_data` | JSON | Parsed API response body |
| `event_data_string` | STRING | Stringified `event_data` — required because VAV2 `eventData` field accepts STRING, not JSON |
| `http_input` | STRING | Parsed from `VirtualAgentV2.MetaData` — the payload the agent sent with its Custom Event |

### State Event Resume Mechanism

The VirtualAgentV2 activity can be **re-entered** after exiting. When the flow routes back to VAV2, it sends a State Event to the agent:

1. Flow sets `event_name` to a confirm entry event (e.g., `track_package_confirm_entry`)
2. Flow sets `event_data_string` to the stringified API response
3. Flow routes back to the VAV2 activity node
4. VAV2 reads `{{ event_name }}` and `{{ event_data_string }}` from its `eventName` and `eventData` properties
5. The agent receives the data and delivers the result to the caller

The event names follow a convention: `<intent_name>_exit` (agent → flow) and `<intent_name>_confirm_entry` (flow → agent). These must match exactly between the agent's Custom Event configuration and the flow's Case/SetVariable activities.

### Multi-Event Routing (Multiple Intents)

When a scripted agent has multiple intents that each need fulfillment, use a **Case** activity to branch on `VirtualAgentV2.StateEventName`:

```
Case ({{VirtualAgentV2.StateEventName}})
  ├── "check_availability_exit"  → HTTPRequest (POST /check_availability)
  ├── "create_appointment_exit"  → HTTPRequest (POST /create_appointment)
  ├── "lookup_appointment_exit"  → HTTPRequest (POST /lookup_appointment)
  ├── "cancel_appointment_exit"  → HTTPRequest (POST /cancel_appointment)
  └── default                    → DisconnectContact
```

Each branch follows the same pattern: HTTP Request → Condition → SetVariable (event_name) → SetVariable (event_data_string) → back to VAV2.

### Intent-Based Queue Routing (previousIntent)

For scripted agents, the flow can route escalations to different queues based on which intent the caller was discussing:

1. Parse `$.previous-intent.name` from `VirtualAgentV2.MetaData` into a `previousIntent` variable
2. Use a **Case** activity to branch on `previousIntent`
3. Route each intent to a different QueueContact activity (e.g., "Track Package" → Package Support Queue, default → General Queue)

### CustomAIAgentInteractionOutcome (Analytics)

Create a **global reportable variable** named `CustomAIAgentInteractionOutcome` (type: STRING) to track how each interaction ended. Set it at each exit path:

| Exit Path | Value | When |
|---|---|---|
| VAV2 → conversation complete | `HANDLED` | AI agent resolved the query |
| VAV2 → ESCALATE | `ESCALATED` | Caller requested human agent |
| VAV2 → error | `ERRORED` | System fault |
| HTTP Request → failure | `ERRORED` | Fulfillment API call failed |

Initialize to `ABANDONED` at flow start (covers callers who hang up before any exit path fires). This variable appears in WxCC Analyzer for outcome reporting.

### Reference Implementations

Cisco publishes importable Flow Designer JSONs for this pattern in the [WebexPlaybooks](https://github.com/webex/WebexPlaybooks) repo:

| Flow | Agent Type | Upstream Source |
|---|---|---|
| Autonomous package tracking | Autonomous | [wxcc-ai-agent-autonomous](https://github.com/webex/WebexPlaybooks/tree/main/playbooks/wxcc-ai-agent-autonomous) |
| Scripted doctor's appointment | Scripted (4 intents: check/book/lookup/cancel) | [wxcc-ai-agent-scripted-appointment](https://github.com/webex/WebexPlaybooks/tree/main/playbooks/wxcc-ai-agent-scripted-appointment) |
| Scripted package tracking | Scripted (package tracking + intent-based routing) | [wxcc-ai-agent-scripted-tracking](https://github.com/webex/WebexPlaybooks/tree/main/playbooks/wxcc-ai-agent-scripted-tracking) |

The same repo also has two Dialogflow playbooks that are not Webex AI Agent flows: `playbooks/byova-dialogflow-agent/` (a BYOVA gRPC gateway for Dialogflow CX — a Python server implementing the WxCC BYOVA protocol) and `playbooks/wxcc-dialogflow-fulfillment/` (Dialogflow CX and ES webhook fulfillment, with importable WxCC flow JSONs). WebexPlaybooks itself draws on [WebexSamples/webex-contact-center-flows](https://github.com/WebexSamples/webex-contact-center-flows). Each playbook folder holds `APPHUB.yaml` (metadata), `README.md`, `diagrams/` and a source folder whose `env.template` lists the IDs to replace. Recorded by wxcc, 2026-07; the repo may have changed since.

Each flow requires replacing sample UUIDs (`orgId`, `virtualAgentId`, queue `destination`) with org-specific values before import. See the `.env.template` files in `docs/examples/` for the full replacement list per flow.

**These JSONs are NOT hand-editable.** The Flow Designer export format is proprietary and undocumented. The JSON includes internal activity UUIDs, diagram widget coordinates, port mappings, and link references that must be internally consistent. The only safe modification is find-and-replace on the org-specific values listed in the env.template. Any structural changes (adding activities, changing links, modifying conditions) must be done in the Flow Designer GUI after importing.

---

## Expression Builder

The Expression Builder is a built-in testing tool for validating Pebble expressions before publishing a flow.

### Access

Click the `</>` icon in any expression field (Set Variable, Condition, Play Message TTS, etc.) to open the **Test Expression** dialog.

### Usage

| Field | Purpose |
|---|---|
| **Expression** | The Pebble expression to test (e.g., `{{ NewPhoneContact.ANI \| replace({"+":""}) }}`) |
| **Variable inputs** | Sample values for each variable referenced in the expression |
| **Result** | Computed output after clicking **Test** |

Click **Test** to evaluate the expression with the sample values. Click **Apply Changes** to commit the expression to the activity field. The builder supports all Pebble filters (`split`, `join`, `replace`, `slice`, `last`, `contains`, etc.) and is the fastest way to debug complex expressions.

---

## Flow Debugging

Flow Designer includes a built-in debug mode for tracing live call execution through a flow.

### Access

Click the **Debug** button at the bottom of the Flow Designer canvas to open the interaction log pane.

### Capabilities

- Real-time trace of which activities fired during a live call
- Variable values at each step in the flow
- Error paths taken and failure codes
- Available for voice calls routed through the flow via the assigned Entry Point

Use Flow Debugging alongside the Expression Builder to validate both expression logic (offline) and end-to-end flow behavior (live).

---

## Token Refresh Subflow Pattern (Webex APIs from Flow Designer)

The HTTP Connector only works with WxCC's own APIs. To call other Webex platform APIs (People, SCIM2, Calling) from a Flow Designer flow, use a **Service App token stored in a Global Variable** with a reusable subflow that refreshes the token on 401.

### Architecture

```
Main Flow
  → HTTP Request (Webex API, Bearer {{WEBEX_ACCESS_TOKEN}})
  → Condition: httpStatusCode == 200?
      → TRUE: Use response data
      → FALSE (401): Subflow "RefreshTheToken"
          → Retry or fallback

RefreshTheToken Subflow
  → HTTP POST https://webexapis.com/v1/access_token (refresh_token grant)
  → Parse new access_token
  → HTTP PUT /organization/{orgId}/cad-variable/{id} (update Global Variable via CC Config API)
  → Return access_token to caller
```

### Setup Summary

1. **Create a Service App** at developer.webex.com with the required scopes (e.g., `spark-admin:people_read`)
2. **Authorize** in Control Hub > Apps > Service Apps (search by Client ID, not name)
3. **Generate tokens** — record both Access Token and Refresh Token
4. **Store access token** in a Global Variable (type: STRING, marked Sensitive)
5. **Create a Read/Write HTTP Connector** for the subflow's PUT call to CC Config API
6. **Build the subflow** — or import the pre-built one from [TeamCCEP](https://github.com/TeamCCEP/teamccep.github.io/tree/master/assets/files/WebexAPIFromWxCC)

### Subflow Internals

The subflow stores credentials in flow variables and exposes one output (`access_token`):

| Flow Variable | Content |
|---------------|---------|
| `client_id` | Service App Client ID |
| `client_secret` | Service App Client Secret |
| `refresh_token` | Service App Refresh Token |
| `global_var_id` | ID of the target Global Variable |

**Activity 1 — GetNewToken:**

```
POST https://webexapis.com/v1/access_token
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token&client_id={{client_id}}&client_secret={{client_secret}}&refresh_token={{refresh_token}}
```

Output: `$.access_token` from the JSON response.

**Activity 2 — UpdateGlobalVariable:**

Uses the Read/Write HTTP Connector (authenticated endpoint ON). Calls the CC Config API to overwrite the Global Variable's `defaultValue` with the fresh token:

```
PUT /organization/{orgId}/cad-variable/{global_var_id}
```

Body includes the full Global Variable object with updated `defaultValue`. See the [API Access](wxcc-platform.md#api-access-connect-or-external) section for required fields.

### Main Flow Wiring

In the main flow, map the subflow output to the Global Variable:

1. Add a **Subflow** activity named "RefreshTheToken"
2. Under **Output Mapping**, map `access_token` → your `WEBEX_ACCESS_TOKEN` Global Variable
3. After the subflow returns, retry the original HTTP Request or continue with fallback logic

### Token Lifecycle

| Concern | Detail |
|---------|--------|
| Access token lifespan | 14 days for a Service App or integration access token, then refresh; a personal access token lasts 12 hours [`authentication.md` § Authentication Methods Overview, § Token Lifetimes]. Said "~12 hours" before 2026-10-19 |
| Refresh token lifespan | 90 days — regenerate before expiry [`authentication.md` § Authentication Methods Overview, § Token Lifetimes] |
| Concurrent flows | Multiple flows can read the same Global Variable safely |
| First-time setup | Manually paste the initial access token as the Global Variable's default value |

> Full walkthrough with step-by-step screenshots: `docs/playbooks/webex-api-auth.md`

---

## Multilingual TTS

Flow Designer uses **Cisco TTS** (not Azure Neural TTS — that's Webex Connect only). Cisco TTS supports 22 languages with two voices per language (one masculine, one feminine).

### Voice Name Format

Pattern: `{locale}-{Name}`

| Language | Masculine | Feminine |
|----------|-----------|----------|
| English (US) | `en-US-Daniel` | `en-US-Maria` |
| Spanish (US) | `es-US-Alejandro` | `es-US-Paloma` |
| French (FR) | `fr-FR-Henri` | `fr-FR-Ariane` |
| English (GB) | `en-GB-Colton` | `en-GB-Elizabeth` |

Full list: [Webex TTS documentation](https://help.webex.com/en-us/article/ntkjqhw/Text-to-Speech-(TTS)-in-Webex-Contact-Center)

### Global Variables for Language Switching

`Global_Language` and `Global_VoiceName` are **pre-defined system variables** — they already exist in your WxCC tenant. Do not create them. Their defaults are:

| Variable | Purpose | Default | Example |
|----------|---------|---------|---------|
| `Global_Language` | Language/locale code | `en-US` | `es-US`, `fr-FR` |
| `Global_VoiceName` | Voice name | `Automatic` | `es-US-Paloma` |

**Before you can use them in a flow, you must add them to the flow:**

1. Click the **settings icon (cog)** in the Flow Designer zoom toolbar to open the **Global Properties pane**
2. Find the **Global Variables** section
3. Click **Add Global Variable**
4. Add `Global_Language` and `Global_VoiceName`

Once added, they appear in the Set Variable activity dropdown. Set them before any TTS activity (Play Message or Menu):

```
Set Variable: Global_Language = "es-US", Global_VoiceName = "es-US-Paloma"
→ Play Message or Menu (TTS plays in Spanish)
```

A single Set Variable activity can set up to 10 variables at once — you can set `Global_Language`, `Global_VoiceName`, and a custom `language` flow variable in one node.

### Key Limitation

**Cisco TTS cannot switch languages within a single Play Message activity.** You must use a Set Variable activity to change `Global_Language` and `Global_VoiceName` before each TTS activity (Play Message or Menu) that uses a different language. Setting the variables once at the start of a language path carries through to all subsequent TTS activities — you don't need to set them again before each one. Google TTS (if configured as a TTS connector) can overcome the single-activity restriction.

### SSML in Flow Designer (Cisco TTS)

Activities with TTS capability — **Play Message**, **Collect Digits**, **Menu** — support SSML (Speech Synthesis Markup Language) for custom voice intonation and personalization. Enable the **Enable Text-to-Speech** toggle in the activity's Prompt section. Wrap TTS content in `<speak>` tags to enable SSML processing. Variables use `{{ variable }}` syntax inside TTS messages.

Each prompt can contain a **sequence of mixed media**: use the "Add Audio File", "Add Audio Prompt Variable", and "Add Text-to-Speech Message" buttons to chain pre-recorded audio and dynamic TTS messages in a single activity.

**Key SSML Tags:**

| Tag | Purpose | Example |
|---|---|---|
| `<speak>` | Root wrapper (required for all SSML) | `<speak>Your message here</speak>` |
| `<say-as interpret-as="characters">` | Spell out character by character | Confirmation codes, order IDs |
| `<say-as interpret-as="currency">` | Read as money amount | `EUR263.56` → "two hundred sixty-three euros and fifty-six cents" |
| `<break time="500ms"/>` | Insert pause | Natural-sounding pauses between sections |

**Example TTS message with SSML:**

```xml
<speak>
  Welcome Rob, <break time="500ms"/> your current balance is
  <say-as interpret-as="currency">EUR263.56</say-as>.
</speak>
```

**TTS Settings (per-activity):**

| Setting | Default | Description |
|---|---|---|
| Speaking Rate | 1 | Speed of speech (adjustable) |
| Volume Gain | 1 decibel | Loudness adjustment |

> This section covers SSML for Flow Designer's Cisco TTS engine. For SSML in Webex Connect nodes (Azure Neural TTS), see `webex-connect-advanced.md` § SSML Tags (Azure Neural TTS).

### Multilingual IVR Pattern (Per-DNIS Language Selection)

For flows handling multiple DIDs in different languages, use a **Case** activity on `{{NewContact.DNIS}}` to branch into language-specific paths:

```
NewContact → Case (DNIS)
  ├── "+18005551234" → Set Variable (en-US) → Play Message (English)
  ├── "+18005555678" → Set Variable (es-US) → Play Message (Spanish)
  └── default → Set Variable (en-US) → Play Message (English)
```

### JSON-Based Prompt Localization

For flows with many prompts in multiple languages, store all language variants in a JSON Global Variable and use a **Parse** activity to extract the right prompt at runtime:

```json
{
    "en-US": { "welcome": "Hello, world!", "goodbye": "Thank you for calling." },
    "es-US": { "welcome": "¡Hola Mundo!", "goodbye": "Gracias por llamar." },
    "fr-FR": { "welcome": "Bonjour le monde!", "goodbye": "Merci d'avoir appelé." }
}
```

Parse with JSONPath: `$["en-US"].welcome` → feeds into Play Message.

> **TTS is not a translation service.** All prompt text must be authored in the target language — the TTS engine only converts text to speech, it does not translate.

---

## Customer Journey Data (JDS) Node

A dedicated Webex Connect node (not an HTTP call) that reads/writes customer journey data in WxCC. Records events, merges identities, and reads progressive profiles. **Flex 3 only.**

**Prerequisites:** Configure authorization under **Assets > Integrations > Pre-built Integrations** before using.

> **Values are owned by `cjds.md`** — endpoints, regional domains, OAuth scopes, the CloudEvents schema, identity types, outcome branches, HTTP codes and RSQL syntax. Build sequence and worked examples: `docs/playbooks/cjds-integration.md`.

### Five Methods

| Method | Purpose | Key Inputs | Success Outcome |
|--------|---------|------------|----------------|
| **Manage Identity** | Merge customer aliases into unified profile | First/Last Name, phone(s), email(s), customer IDs, social IDs, temporary IDs, Overwrite flag | `onCreateMergeAliasesSuccess` (202) |
| **Write to CJDS** | Record an event in the customer journey | Event ID, Spec Version, Type, Source, Time (UTC), Identity Type (`email`/`phone`/`customerId`/`socialId`/`temporaryId`), Identity, Data Object | `onEventPostSuccess` (202) |
| **Get Identity by Aliases** | Look up all linked identities from one alias | Comma-separated alias IDs | `onGetIdentityByAliasesSuccess` (200) |
| **Read from Progressive Profile** | Get aggregated customer metrics from a template | Template Name, Alias ID | `onGetIdentityByAliasesSuccess` (200) |
| **Read from CJDS** | Retrieve recent events/behaviors | Identity, Query Filter (e.g., `filter=type=='agent:state_change'&pageSize=1`) | `onReadfromCJDSSuccess` (200) |

### Node Outcomes

**Error outcomes (all methods):** `onBadRequest` (400), `onForbidden` (403), `onNotFound` (404), `onTooManyRequest` (429), `onInternalServerError` (500), `onTimeout` (10s), `onInvalidData`, `onError`, `onInvalidChoice`

Each method also has a method-specific failure outcome (e.g., `onCreateMergeAliasesFailure`, `onEventPostFailure`, `onGetIdentityByAliasesFailure`, `onReadfromCJDSFailure`) that fires for non-success HTTP codes not covered by the error outcomes above.

### When to Use in AI Agent Flows

- **Write to CJDS**: Record that a customer booked/cancelled/rescheduled an appointment after your action completes
- **Read from CJDS**: Check if a caller has contacted recently for personalized handling

**Timeout warning:** Keep JDS operations lightweight. The 30-second AI agent flow timeout applies. A Write + Flow Outcomes is safe; chaining multiple reads is risky. The CJD node itself has a strict **10-second timeout**.

### Example: Record Appointment Booked

After the create_appointment HTTP node succeeds:

```
HTTP POST (create appointment) → Customer Journey Data (Write to CJDS)
  Event Type: "appointment:booked"
  Source: "ai_agent"
  Identity: phone_number
  Identity Type: phone
  Data: { confirmation_number, scheduled_at }
→ End (END FLOW)
```

> **The confirmation is returned to the agent by Flow Outcomes — which is not a node.** There is no Flow Outcomes node in the palette and nothing on the canvas to route into; it is a **flow-level settings area** reached from the **Flow Settings** button on the Webex Connect Flow Builder page. Wire the last node to an **End (END FLOW)** node and configure the returned payload in Flow Settings > Flow Outcomes [owner: `webex-connect.md` § Flow Outcomes (Flow Settings — NOT a node); source: https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions].

---

## Flow Designer Management API

WxCC Flow Designer (separate from Webex Connect) exposes REST APIs for programmatic flow management.

### Endpoints

| Operation | Method | Path |
|-----------|--------|------|
| List Flows or Subflows | GET | `/flow-store/{orgId}/project/{projectId}/flows` |
| Import a Flow or Subflow | POST | `/flow-store/{orgId}/project/{projectId}/flows:import` |
| Export a Flow or Subflow | GET | `/flow-store/{orgId}/project/{projectId}/flows/{flowId}:export` |
| Publish a Flow or Subflow | POST | `/flow-store/{orgId}/project/{projectId}/flows/{flowId}:publish` |

### Authentication

| Field | Value |
|---|---|
| Scopes | `cjp:config_read` (list, export), `cjp:config_write` (import, publish) |
| Required Roles | Organizational Full Admin, Supervisor, Contact Center Service Admin, User Admin |

### Important Constraints

- Exported JSON is **proprietary** — internal activity UUIDs, diagram widget coordinates, port mappings, and link references must be internally consistent
- The only safe modification to exported JSON is find-and-replace on org-specific values (orgId, virtualAgentId, queue destination UUIDs)
- Structural changes (adding activities, changing links, modifying conditions) must be done in the Flow Designer GUI after importing
- Use these APIs for CI/CD pipelines, flow backup/restore, and cross-environment promotion — not for programmatic flow editing

> **Cross-reference:** The "not for programmatic flow editing" caveat above applies only to this proprietary export/import JSON format. Programmatic flow *building* via the supported FlowIR path is documented separately in `flow-designer-flowir.md` § 9 (Validate → Create Workflow) and the `build-flow-programmatic` skill.

---

## Queue Parking Pattern

The Queue Contact activity can be used as a temporary "parking lot" for a caller while an asynchronous action (e.g., an API call to trigger a parallel outbound call) executes.

**How it works:** Set an impossible skill requirement on the Queue Contact activity so no agent matches. Enable **Check Agent Availability** — if no agents match, the contact may not enter the queued state, avoiding Blind Transfer failure code 48 (which blocks transfers after queueing).

**Limitation:** Queue Contact does not have a configurable short timeout. Skill Relaxation defaults to 60 seconds for the first step. The caller remains in queue until an agent accepts, the 24-hour system max, or the caller disconnects. There is no "release after N seconds" timer.

**Warning:** Blind Transfer after Queue Contact fails with failure code 48: "Can't transfer after queueing or agent assigned." If the contact enters the queued state, you cannot Blind Transfer out. See the Bridged Transfer dequeue enhancement for a potential workaround.

---

## Audio Injection Limitations

Flow Designer's Play Message activity plays audio **only to the current caller's call leg**. There is no mechanism to:

- Inject TTS audio into a Bridged Transfer bridge (the far end does not hear Play Message)
- Play audio to a different call or endpoint
- Send audio to a third party while the caller is on hold

During a Bridged Transfer, the flow is suspended until the bridge completes. No activities execute during the bridge. The only signal that can be injected during a bridge is DTMF via the "Send Output Digits" field on the Bridged Transfer activity.

**Implication:** If you need TTS audio to reach a third-party endpoint (e.g., a paging system), the audio must be delivered through a separate call channel — Flow Designer cannot inject it into the current call's bridge.

---

## Outbound Call Limitations

Flow Designer cannot spawn independent outbound calls. Key constraints:

- **No outbound dial activity** — Flow Designer handles inbound calls. There is no "Place Outbound Call" activity that creates a new call leg.
- **Subflows are same-call, sequential** — Subflows execute on the same call as the main flow and return control when complete. They cannot create new calls or run in parallel.
- **Blind Transfer and Bridged Transfer redirect the existing call** — they do not create new calls; they transfer the current caller to another destination.
- **GoTo redirects the existing call** — GoTo transfers the current call to another entry point or flow. It does not create a new call.

**Workaround — Create Task API:** The WxCC Create Task API can programmatically create a new telephony task that runs through a separate flow. Use the HTTP Request activity in the main flow to call it, triggering a parallel outbound call while the main flow continues handling the inbound caller. Endpoint, body and field values: `wxcc-platform.md` § Create Task API. Build sequence: `docs/playbooks/dual-call-paging.md`.

## See Also

- [flow-designer-essentials.md](flow-designer-essentials.md) — the everyday activities these patterns combine
- [flow-designer-flowir.md](flow-designer-flowir.md) — the FlowIR format for authoring them
- [wxcc-platform.md](wxcc-platform.md) — platform setup the patterns assume
- [webex-connect.md](webex-connect.md) — the Connect flows several patterns call
- [webex-api-auth.md](../playbooks/webex-api-auth.md) — token setup for the API calls in these patterns
