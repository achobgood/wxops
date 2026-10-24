# Flow Designer — Essential Activities

<!-- ref-tag: fd-essentials-v2 -->

<!-- LOOKUP RULE: You read this file because a user asked a Flow Designer question.
If the answer is NOT in this file, check flow-designer-activities/_index.md and read the
relevant activity file directly. Do NOT answer from training data.
If it's a patterns/advanced topic, read flow-designer-patterns.md instead. -->

> These activities appear in virtually every voice flow. Load this file first for any Flow Designer task.
>
> For situational activities (transfers, callbacks, recording, advanced routing, etc.), see [flow-designer-activities/](flow-designer-activities/).
>
> For patterns and advanced topics (versioning, subflows, dynamic variables, scripted agent fulfillment, connectors auth, multilingual TTS, expression builder, flow debugging, CJDS node, management API), see [flow-designer-patterns.md](flow-designer-patterns.md).
>
> Platform setup (Control Hub, Queues, Teams, Entry Points, Global Variables) is in [wxcc-platform.md](wxcc-platform.md).

## Voice Flow Basics

### Create a New Flow

1. **Contact Center > Flows > New Flow**
2. Choose a starting template or start from scratch
3. Name the flow descriptively
4. Click the canvas -- Flow Designer opens

### Built-in Flow Templates

When creating a new flow, Flow Designer offers templates as starting points:

| Template | Description |
|---|---|
| Hello World | Simple inbound greeting + disconnect |
| Simple Inbound Call to Queue | Greet caller → queue to agent with hold music |
| Comprehensive Inbound Contact | Full scenario: business hours, self-service, queue |
| Business Hours Usage | Business hours branching example |
| CSAT DTMF Survey | Post-call customer satisfaction survey via DTMF keypad |
| DialogFlow ES Virtual Agent | Google DialogFlow ES integration |
| Dynamic Variable Support | External settings retrieval and variable-based routing |
| Menu Auto Attendant | DTMF menu-driven call routing |
| Microsoft Dynamics HTTP(S) Data Dip | Data retrieval from Microsoft Dynamics CRM |
| Percentage Allocation and A/B Distribution | Route contacts across branches by percentage weights |
| Salesforce HTTP(S) Data Dip | Data retrieval from Salesforce |
| ServiceNow HTTP(S) Data Dip | Data retrieval from ServiceNow |
| Virtual Agent with Google DialogFlow CX | Google DialogFlow CX conversational agent |
| Zendesk HTTP(S) Data Dip | Data retrieval from Zendesk |
| Avoid Duplicate Callback | Prevents duplicate callback requests for the same caller |
| Audio Prompt Recording and Management | Record and manage audio prompt files |
| Last Agent Routing Template | Route caller to the agent who handled their previous interaction |
| AI Agent Autonomous (Package Tracking) | Autonomous AI agent for package tracking use case |
| AI Agent Scripted (Package Tracking) | Scripted AI agent for package tracking use case |
| AI Agent Scripted (Doctor's Appointment Booking) | Scripted AI agent for appointment scheduling use case |

Templates are importable and customizable. For AI agent flows, start from scratch or use a simple template and add the Virtual Agent V2 node.

### Built-in Subflow Templates

Flow Designer also provides subflow templates for common reusable patterns:

| Subflow Template | Description |
|---|---|
| Collect Callback Info | Collects callback number and preferences from the caller |
| Error Handling | Standard error handling pattern with TTS message and fallback queue |
| HTTP Data Dip | Reusable HTTP request pattern for external data lookups |
| Queue Treatment | Hold music, position announcements, and callback offers during queue wait |
| Scheduled Callback Subflow Template | Manages callback scheduling and registration logic |

### Add Virtual Agent V2 Node

1. Drag **Virtual Agent V2** from the activity panel
2. Configure:
   - **Contact Center AI Config**: select your CCAI Config (links to AI Agent Studio agent)
   - **Prompt**: leave blank (the AI agent handles its own greeting via Welcome Message)
3. Connect **NewPhoneContact** output to **Virtual Agent V2** input

### Handle Escalation and End

From **Virtual Agent V2**, connect the three outputs:

| Output | Wire To | Purpose |
|--------|---------|---------|
| `Escalated` | **Queue Contact** node | Customer requested a human agent |
| `Handled` | **Disconnect Contact** node | AI agent resolved the interaction |
| `Errored` | **Disconnect Contact** node (or Play Message + Disconnect) | Something went wrong |

Configure the **Queue Contact** node to use your queue.

Connect **Queue Contact** output to **Disconnect Contact** (for after the human agent finishes).

### Publish and Link

1. Click **Validate** in the toolbar -- fix any errors
2. Click **Publish**
3. Back in **Control Hub > Entry Points**, edit your entry point
4. Under **Flow**, select the published flow
5. Save

---

## Play Message Activity

Plays an audio prompt or text-to-speech message to the caller.

### Configuration

**General Settings:**

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | Optional description |

**Prompt:**

Each prompt can contain a sequence of mixed media. Use these buttons to build the prompt:

| Button | Description |
|---|---|
| **Add Audio File** | Select a pre-uploaded audio file from the dropdown |
| **Add Text-to-Speech Message** | Enter text that the TTS engine converts to speech. Supports `{{variable}}` interpolation and SSML tags inside `<speak>` wrappers. |
| **Add Audio Prompt Variable** | Select a flow variable that resolves to an audio file at runtime |

Maximum **5 combined** audio files and audio variables per prompt. Multiple segments can be chained — for example, a pre-recorded greeting followed by a dynamic TTS message with the caller's account balance.

**TTS Settings (when Text-to-Speech is added):**

| Field | Default | Range | Description |
|---|---|---|---|
| Connector | Cisco Cloud TTS | — | TTS connector selection — **Cisco Cloud TTS** (default) or **Google TTS** (if configured) |
| Override Default Language & Voice Settings | Enabled | On/Off | Override the flow-level `Global_Language` and `Global_VoiceName` for this activity |
| Output Voice | — | — | Voice selection (appears when override is enabled) |
| Speaking Rate | 1.0 wpm | 0.25–4.0 wpm | Speed of speech |
| Volume Gain | 0.0 dB | -96.0–16.0 dB | Loudness adjustment |

> **Note:** Play Message is uninterruptible — callers cannot skip playback with DTMF input. To allow digit-based interruption, use Collect Digits or Menu instead.

**Important TTS considerations:**
- Use single quotes instead of double quotes inside pebble expressions.
- Use pebble escape filters if your TTS message has more than one line (so that the system plays the message), for example `{{ variable | escape('json') }}`.
- There is no character limit for Cisco Text-to-Speech messages.

**Connector platform differences:**
- Existing customers on Classic voice platform can view only Google TTS connector in the dropdown.
- Existing customers on the Next Generation voice platform can view both Cisco Cloud Text-to-Speech and Google TTS connectors.

> Do not include only the Play Message activity in loop after the Queue Contact activity in the call flow. Use a combination of the Play Music activity and the Play Message activity in loop to make a valid call flow.

> When you include the Play Message activity before the HTTP Request activity in a call flow, the HTTP request executes only after the audio is played fully.

### Output Variables

No output variables are documented for Play Message in the Cisco help docs. The activity may expose `FailureCode` / `FailureDescription` in the UI, but they are not in the official documentation.

### Output Paths

| Path | Description |
|---|---|
| Default exit | Continues to the next wired activity after playback completes |
| Undefined Error | Error-handling path for system errors during flow execution. If not configured, the flow uses the `OnGlobalError` event handler. |

### Common Patterns

- **Delay before HTTP Request:** Place a Play Message ("Please wait while I look that up") before an HTTP Request activity to fill silence during the API call.
- **Error announcement:** Wire from OnGlobalError or a failed Condition branch to announce the error before disconnecting or queuing.
- **Pre-transfer comfort:** Play "Connecting you now" before a Blind Transfer or Bridged Transfer to fill the silence gap.

---

## Play Music Activity

Plays hold music or background audio on a continuous loop for a specified duration.

### Configuration

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | Optional description |
| Music File | **Static Audio File** — select from the dropdown. **Dynamic Audio File** — enter a Pebble expression that resolves to an audio file at runtime. |
| Start Offset | Position in the audio file to begin playback (in seconds). Static value or Pebble expression. Must be numeric. Example: if the file is 60 seconds long, Start Offset is 45 seconds, and duration is 30 seconds, the last 15 seconds play first, then the audio loops to the beginning and plays the first 15 seconds. A value of 0 starts playback from the beginning. |
| Music Duration | How long to play the music (in seconds). Static value or Pebble expression. Must be numeric. |

**Music playback rules:**
- If the specified Music Duration is shorter than the audio file length, the music plays only for the specified duration (e.g., a 30-second duration with a 40-second file plays for 30 seconds).
- If the Music Duration exceeds the audio file length, the music plays for up to five times the file length, looping as needed (e.g., a 600-second duration with a 40-second file plays for 200 seconds = 5 x 40).

> Play Music activity does not support previewing prompt.

> When you include the Play Music activity before the HTTP Request activity in a call flow, the HTTP request executes only after the audio is played fully.

### Output Variables

| Variable | Description |
|---|---|
| `PlayMusic.FailureCode` | Error code on failure |
| `PlayMusic.FailureDescription` | Error description on failure |

> **Note:** Specific failure code values for Play Music are not enumerated in the Cisco help docs. Use `PlayMusic.FailureCode` and `PlayMusic.FailureDescription` to diagnose failures in the Undefined Error path.

### Output Paths

| Path | Description |
|---|---|
| Default exit | Continues to the next wired activity after music playback completes (or is interrupted by an agent answer) |
| Undefined Error | Error-handling path for system errors during flow execution. If not configured, the flow uses the `OnGlobalError` event handler. |

### Common Patterns

- **Queue hold music:** Wire Play Music after Queue Contact to play audio while the caller waits for an agent. The music plays until an agent answers.
- **Transfer hold music:** Play Music before or during a Bridged Transfer to fill silence.

---


## Set Variable Activity

Found in the **Activity Library** under **Utilities**. Drag it onto the canvas and wire it between activities. A single Set Variable activity can set **up to 10 variables** in one step — including both custom flow variables and Global Variables (like `Global_Language`).

You can configure an error-handling path (Undefined Error) to handle system errors that may occur during flow execution. If you don't configure the error-handling path, the global error handler handles the flow execution error.

### General Settings

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | Optional description |

### Variable Settings

| Field | Description |
|---|---|
| Variable | Choose the variable from the dropdown. You can only set **custom flow variables** to custom values. Predefined variables have fixed values as dictated by the flow execution. |
| Variable Value | **Set Value** radio button: set the variable to a specific static value or an expression using `{{variable}}` syntax. The input field type changes based on the data type of the selected variable. **Set to Variable** radio button: set the variable value to the value of another variable in the flow (all variables are available for selection). |
| Add New | Click **Add New** to add additional variables. You can configure up to 10 variables within a single Set Variable activity. You can reorder the variables within the activity. |

> **Complex expression warning:** Don't include complex expressions when configuring multiple variables within a single Set Variable activity.

### Expression Limitations

The Set Variable activity supports basic assignment and math operators (`+`, `-`, `*`, `/`). It does **not** support JavaScript-style string methods:

- `{{variable}}.substring(2)` — adds literal text `.substring(2)` to the value
- `{{variable}}.replace("+", "%2B")` — `+` is a regex special character, fails silently

**Pebble templates work.** Flow Designer supports Pebble template syntax in Set Variable expressions:

### String Filters

| Operation | Pebble Syntax | Example |
|---|---|---|
| Strip first character | `{{ variable \| slice(1) }}` | `+19103915567` → `19103915567` |
| Strip first N characters | `{{ variable \| slice(N) }}` | Strip `+1` prefix |
| Extract first N characters | `{{ variable \| slice(0,3) }}` | `+442034574333` → `+44` |
| Last N characters | `{{ variable \| slice(variable \| length - N) }}` | Last 4 digits of phone number |
| String length | `{{ variable \| length }}` | Returns character count |
| Replace substring | `{{ variable \| replace({"+":""}) }}` | `+442034574333` → `442034574333` |
| Split and rejoin | `{{ variable \| split("") \| join(",") }}` | `12345678` → `1,2,3,4,5,6,7,8` |
| Split on delimiter | `{{ variable \| split("@") \| last }}` | `test@cisco.com` → `cisco.com` |
| Array membership test | `{{["+44","+31"] contains variable \| slice(0,3)}}` | Returns `true` / `false` |

### Date/Time Functions

| Operation | Pebble Syntax | Returns |
|---|---|---|
| Current timestamp | `{{ now() }}` | `2025-02-06T21:09:02.712Z[UTC]` |
| Current epoch (seconds) | `{{ now() \| epoch }}` | `1738876142` |
| Current epoch (milliseconds) | `{{ now() \| epoch(inMillis=true) }}` | `1738876142712` |
| Parse date string to epoch | `{{ "December 10, 2023 00:00" \| epoch(format="MMMM d, yyyy HH:mm") }}` | Epoch seconds |
| Day of week from epoch | `{{ now() \| epoch(inMillis=true) \| date("EEEE") }}` | `Thursday` |
| Tomorrow's day name | `{{ (now() \| epoch(inMillis=true) + 86400000) \| date("EEEE") }}` | Next day name |
| Format date | `{{ epochMillis \| date("yyyy-MM-dd") }}` | `2025-02-06` |

The `date()` filter accepts Java SimpleDateFormat patterns: `EEEE` (day name), `MMMM` (month name), `yyyy-MM-dd` (ISO date), `HH:mm` (24h time).

### Numeric Filters and Operators

| Operation | Pebble Syntax | Returns |
|---|---|---|
| Round to integer | `{{ value \| numberformat("#") }}` | Drops decimals |
| Modulus (remainder) | `{{ now() \| epoch(inMillis=true) % 10 }}` | `0`–`9` |
| Arithmetic | `{{ now() \| epoch - startTime }}` | Elapsed seconds |

### Practical Patterns

| Use Case | Expression |
|----------|-----------|
| Days since a date | `{{ (now() \| epoch / 86400) - ("October 1, 2023 00:00" \| epoch(format="MMMM d, yyyy HH:mm") / 86400) }}` |
| Random number 0–9 | `{{ now() \| epoch(inMillis=true) % 10 }}` |
| Random in range (90–180) | `{{ ((now() \| epoch(inMillis=true) % 1000 / 1000.0) * (180 - 90) + 90) \| numberformat("#") }}` |
| Queue wait exceeded? | `{{ now() \| epoch - QueueEntryTime > TimeoutThreshold }}` |
| Last 4 digits of ANI | `{{ ANI \| slice(ANI \| length - 4) }}` |
| Strip + from ANI | `{{ NewPhoneContact.ANI \| replace({"+":""}) }}` |
| Extract email domain | `{{ customerEmail \| split("@") \| last }}` |
| Read back digits with pauses | `You entered {{ DigitsEntered \| split("") \| join(", ") }}` |
| Check ANI country code | `{{["+44","+31"] contains NewPhoneContact.ANI \| slice(0,3)}}` |

### Pebble Limitations

**`replace` filter requires map syntax.** The standard 2-argument form `{{ variable | replace('old', 'new') }}` fails with `The argument at position 2 is not allowed. Only 1 argument(s) are allowed.` Use the **map form** instead — wrap the key-value pair in curly braces as a single map argument:

```
{{ variable | replace({"+":""}) }}      ✅ Works — single map argument
{{ variable | replace("+", "") }}       ❌ Fails — two arguments
```

**Alternative when string manipulation isn't needed:** Design API calls to accept the raw variable format. For example, the CJDS alias lookup endpoint normalizes phone formats — `+19103915567` matches a stored value of `9103915567` without needing to strip the prefix.

### Output Paths

| Path | Description |
|---|---|
| Default exit | Continues to the next wired activity after all variables are set |
| Undefined Error | Error-handling path for system errors during flow execution (e.g., invalid expression evaluation). If not configured, the flow uses the `OnGlobalError` event handler. |

---


## Variable Types

Flow Designer has three categories of variables. Their capabilities differ significantly:

| Property | Local Variables | Global Variables | Output Variables |
|---|---|---|---|
| Created In | Flow canvas (per-flow) | Control Hub Provisioning (org-wide) | Auto-generated by activities |
| Agent Viewable | YES | YES | NO |
| Agent Editable | YES | YES | NO |
| Reportable | NO | **YES** | NO |
| Default Values | YES | YES | NO |
| Marked Secure | YES | **NO** | NO |
| Data Types | String, Integer, Date Time, Boolean, Decimal, **JSON** | String, Integer, Date Time, Boolean, Decimal | String, Integer, **JSON** |

Key distinctions:

- **Local Variables** support **JSON as a first-class data type** — use for storing parsed API responses without stringifying
- **Global Variables** are the only type that appears in **WxCC Analyzer reports** (Reportable = YES) but **cannot be marked Secure**
- **Output Variables** are read-only values produced by activities (e.g., `HTTPRequest.httpStatusCode`) — limited to String, Integer, and JSON

Two additional data definition categories exist alongside these three:

- **Event Output Variables** — Each event handler (AgentAccepted, PreDial, etc.) exposes its own output variables, scoped to the event flow canvas only. Not accessible from the main flow.
- **Caller Associated Data (CAD)** — Metadata attached to the contact that travels with the interaction across flows and to the agent desktop. Configured via the **Desktop Viewability & Order** tab in the Global Flow Properties panel (gear icon in the canvas toolbar). Controls which variables appear on the agent desktop and in what order.

> For Global Variables API access (CRUD via REST), see the [WxCC Global Variables](wxcc-platform.md#wxcc-global-variables) section.

### Custom Variable Constraints

When creating custom flow variables (Configuration panel → Variable Definition → Add Flow Variable):

- **Max 30 agent-viewable + reportable variables per flow.** This count includes both global variables and custom flow variables. You can add any number of non-agent-viewable flow variables or non-reportable global variables beyond this limit. To add more, you must delete an equal number of existing variables.
- **Variable Type cannot be changed after creation.** If the variable is already in use, the Variable Type drop-down is disabled and a warning message appears. Choose the type carefully at creation time.
- **Supported types:**

| Variable Type | Default Value Behavior |
|---|---|
| **Boolean** | Drop-down: True or False |
| **String** | Free-text string value. Use `{{variable}}` syntax in expressions |
| **Integer** | Integer value |
| **Decimal** | Decimal value |
| **Date Time** | Supported formats: `yyyy-MM-ddTHH:mm:ss.SSSZ`, `yyyy-MM-ddTHH:mm:ssZ`, `yyyy-MM-ddTHH:mmZ`, `{{now()}}`. Note: `now()` uses SimpleDateFormat — for current time in milliseconds, use the epoch timestamp Pebble filter instead |
| **JSON** | Valid JSON: `{"Key":"Value"}`. Supports simple or nested data |

- **JSON variable limits:** Maximum **5 JSON variables per flow**. Maximum size **16 KB** per JSON variable value. When JSON is selected as the variable type, the **Contains Sensitive Information** and **Make Agent Viewable** toggles are not visible. **JSON variables are not allowed in flow chaining.**
- **Sensitive variables:** Enable the **Contains Sensitive Information** toggle to mark a variable as secure. The system will not log or store any information passed through this variable during flow execution. In flow variable mapping, you cannot map a secure variable to a nonsecure variable in the GoTo activity.
- **Agent Viewable:** Enable the **Make Agent Viewable** toggle to display the variable on the Desktop with the value captured during the flow. This exposes two additional fields:
  - **Desktop Label** — the label shown on the Desktop (enter a clear label, not just the variable name)
  - **Agent Editable** — allows the agent to edit the variable value during the interaction session and save it back to Flow Designer. If the call disconnects before the agent clicks Save, the update is lost.
- **Enable External Override:** Turning on this toggle exposes the variable on the channel configuration page in Control Hub, allowing administrators and supervisors to override its value without opening Flow Designer. When the variable type is String, a **Resource Type** drop-down appears with these options:
  - **Audio Prompt** — override audio prompt settings (e.g., welcome prompt or TTS message)
  - **Business Hours** — override business hours (e.g., emergency shutdown)
  - **Entry Point** — change the entry point setting
  - **Dial Number** — change the dialed number
  - **Flow** — change the flow
  - **Queue** — change the queue
- Variables marked as **Secure** cannot be overridden. Maximum **15 variables** per flow can be configured as overridable.

### Override Flow Settings

The override flow settings feature allows authorized users to modify certain flow parameters from Control Hub without opening Flow Designer. This requires two steps:

1. **Flow Developer:** Configure variables within the flow as externally configurable using the **Enable External Override** toggle (see Custom Variable Constraints above).
2. **Administrator / Supervisor:** Change the variable values on the channel configuration page in Control Hub (see the "Set up a channel" section in Control Hub docs).

Advantages:

- **Flow reusability** — use the same flow for different organizations by configuring different variable values for different channels, without modifying the default value in the flow
- **Faster response times** — changes to variable values are applied immediately, even to calls already in progress
- **Reduced errors** — eliminates risk of mistakes when modifying complex flows
- **Simplified task management** — administrators do not need to open Flow Designer, navigate to the relevant flow path, make changes, and republish

### Desktop Viewable Variables

You can configure system variables, global variables, and custom flow variables for the **Incoming Popover** and **Interaction Pane** on the Agent Desktop for incoming and outgoing voice calls. Only variables marked as **Agent Viewable** can be configured. Configure these via Flow Designer → Global Flow Properties → Variable Definition → **Desktop Viewability & Order** tab.

You must build separate flows for inbound and outbound call scenarios to configure variables for the popover and interaction pane independently.

**Incoming Popover:**

- Appears when an agent receives an incoming call or dials an outgoing call
- Displays key customer information from any combination of system, global, and custom flow variables
- For incoming and outgoing calls: minimum **3** variables, maximum **6** variables
- For consult calls: the consulted agent sees an additional 3 variables (Agent Name, Agent DN, Agent Team) added by default
- **Variables containing sensitive information cannot be configured in the incoming popover**
- Variable display order is configurable via drag handles
- Default system variables: Phone Number, DNIS, Queue Name, RONA Timeout (Phone Number, DNIS, and Queue Name are selected by default)

**Interaction Pane:**

- Appears after the agent accepts the incoming or outgoing call
- Maximum **30** variables, from any combination of system, global, and custom flow variables
- Variable display order is configurable via drag handles
- **Desktop does not currently support translation of labels of dynamic variables**

### Customize System Variables

You can customize the desktop label of **Phone Number** and **DNIS** (Dialed Number Identification Service) system variables only. This creates an alias that appears on the Incoming Popover and Interaction Pane instead of the default system variable name.

Procedure:

1. In Flow Designer → Global Flow Properties → Variable Definition → Configuration tab, click **Add Flow Variable**
2. Enter a **Name** and **Description** for the alias variable
3. Set **Variable Type** to **String**
4. Enable the **Make Agent Viewable** toggle
5. In the **Desktop Label** field, enter the desired label (e.g., "Customer Phone" instead of "Phone Number")
6. Click **Save**
7. Drag a **Set Variable** activity into the canvas
8. In Activity Settings → Variable Settings: select the new variable from the **Variable** drop-down, choose the **Set to Variable** radio button, and select the system variable to alias (`NewContact.ANI` for Phone Number or `NewContact.DNIS` for DNIS)

When the flow is published, the newly created flow variable replaces the chosen system variable. The custom Desktop Label appears in the Incoming Popover and Interaction Pane.

### Global Variable String Limits

- During flow creation (initialization), a global variable of type **String** can be set to a maximum of **256 characters**
- During flow execution (runtime), the variable can be updated to hold up to **1024 characters**
- Exceeding the 1024-character runtime limit can cause call failures and invalid values
- The default value entered for a global variable of type String that is **agent reportable must not exceed 256 characters**
- Global variable metadata (Reportable, Agent Viewable, Agent Editable, Desktop Label) is administered in Control Hub. Changes made in Control Hub reflect across flows with a **cache expiry delay of 8 hours**
- When editing a global variable in Flow Designer, you cannot change metadata values — only the default value via the **Overwrite Default Value** toggle

---


## Activity Output Variables

### NewContact (Start Flow)

> **Renamed from `NewPhoneContact` to `NewContact` in April 2025.** Existing flows keep the legacy name. New flows use `NewContact`. Both work identically.

| Variable | Description |
|---|---|
| `NewContact.ANI` | Caller's phone number. Returns `anonymous` (not empty) for blocked caller ID. |
| `NewContact.DNIS` | Dialed number (the number the caller called). |
| `NewContact.InteractionId` | Unique interaction identifier. Can be displayed on Agent Desktop. |
| `NewContact.EntryPointId` | Entry Point ID that triggered the flow. |
| `NewContact.PSTNRegion` | PSTN region from EP-DN mapping. RTMS (Next Gen voice platform) only. |
| `NewContact.FlowId` | Flow identifier. |
| `NewContact.FlowVersionLabel` | Flow version label (Dev, Test, Live, Latest). |
| `NewContact.OrgId` | Organization identifier. |
| `NewContact.Headers` | SIP headers from the incoming INVITE in **JSON format**. See details below. |
| `NewContact.CallbackType` | `scheduled` or `scheduled_personal` for callbacks. Empty for normal calls. |
| `NewContact.ScheduleSourceInteractionId` | Original interaction ID for callbacks. Empty for normal calls. |
| `NewContact.CallbackReason` | Callback reason text. Empty for normal calls. |
| `NewContact.Payload` | Additional data passed to the flow. May not be available in all tenants — verify in your environment. |

### NewContact.Headers — SIP Header Details

The `Headers` variable contains a JSON object with parsed SIP headers from the inbound INVITE:

```json
{
  "session-id": "d6f0a450...",
  "x-cisco-location-info": "18e8d35d-...;country=US;local",
  "x-cisco-remote-connectivity": "PSTN;provider=\"CcpWxTelnxUS\"",
  "caller_id_name": "Anonymous"
}
```

| Detail | Value |
|---|---|
| `caller_id_name` | Caller display name / CNAM from the carrier. Key for spam filtering. |
| Format | JSON object, all header keys **lowercased** |
| Max headers | 20 (alphabetically sorted if more exist) |
| Max size | 1000 bytes total |
| Platform | RTMS (Next Gen voice) only |
| LGW requirement | Custom X-Headers require Webex Calling with Local Gateway |

**Reserved SIP header patterns:** The following header patterns are reserved for internal use and must not be passed as custom headers. Any headers matching these patterns are dropped and not passed to Webex Contact Center:

- `X-Address`
- `X-ADD-DIVERSION`
- `X-BNR-State`
- `X-BNR-Original-Codec`
- `X-BNR-Bypassed`
- `X-BroadWorks-Correlation-Info`
- `X-FS-Support`
- `X-Path`
- `X-RTMS-CID`
- `X-RTMS-OID`
- `X-RTMS-CONFID`
- `X-RTMS-AGENT-LEGID`
- `X-RTMS-ENTER-SOUND`
- `X-RTMS-APP-PREFIX`
- `X-RTMS-No-Lookup`
- `X-VPOP-DOMAIN`

**Blocked caller ID behavior:** When a caller blocks their ID (e.g., `*67`), `NewContact.ANI` returns the literal string `anonymous` (not empty/null), and `caller_id_name` returns `Anonymous` or `Private`.

To extract `caller_id_name`: Use a **Set Variable** activity to assign `{{NewContact.Headers}}` to a flow variable, then parse the JSON.

To add and parse SIP headers to external IVR systems, use the **Bridged Transfer** and **Blind Transfer** activities.

### Collect Digits

| Variable | Description |
|---|---|
| `CollectDigits.DigitsEntered` | DTMF digits entered by the caller. Label is dynamic based on activity name. |

### Menu

| Variable | Description |
|---|---|
| `Menu.OptionEntered` | Menu option selected (single digit 0-9). |

### Virtual Agent V2

For Virtual Agent V2 output variables, see the [Virtual Agent V2 Activity](flow-designer-activities/virtual-agent-v2.md) section.

### Queue Contact

| Variable | Description |
|---|---|
| `QueueContact.QueueId` | Queue identifier. |
| `QueueContact.FailureCode` | Failure code on error. |
| `QueueContact.FailureDescription` | Failure description on error. |

### Queue To Agent

| Variable | Description |
|---|---|
| `QueueToAgent.AgentId` | Target agent identifier. |
| `QueueToAgent.FailureCode` | Failure code on error. |
| `QueueToAgent.FailureDescription` | Failure description on error. |
| `QueueToAgent.AgentState` | Agent's current state. |
| `QueueToAgent.AgentIdleCode` | Agent's idle code. |

### Get Queue Info

| Variable | Description |
|---|---|
| `GetQueueInfo.PositionInQueue` | Position in queue (PIQ). |
| `GetQueueInfo.EstimatedWaitTime` | Estimated wait time in milliseconds. |
| `GetQueueInfo.LoggedOnAgentsCurrent` | Logged-on agents in current call distribution group. |
| `GetQueueInfo.LoggedOnAgentsAll` | Logged-on agents across all groups. |
| `GetQueueInfo.AvailableAgentsCurrent` | Available agents in current group. |
| `GetQueueInfo.AvailableAgentsAll` | Available agents across all groups. |
| `GetQueueInfo.CallsQueuedNow` | Current calls in queue. |
| `GetQueueInfo.OldestCallTime` | Time of oldest queued call. |
| `GetQueueInfo.FailureCode` | Failure code on error. |
| `GetQueueInfo.FailureDescription` | Failure description on error. |

### Advanced Queue Information

| Variable | Description |
|---|---|
| `AdvancedQueueInformation.PositionInQueue` | Position in queue. |
| `AdvancedQueueInformation.LoggedOnAgentsCurrent` | Logged-on agents in current group. Returns `-1` if used before queueing (current CDG = N/A). |
| `AdvancedQueueInformation.LoggedOnAgentsAll` | Logged-on agents across all groups. |
| `AdvancedQueueInformation.AvailableAgentsCurrent` | Available agents in current group. Returns `-1` if used before queueing (current CDG = N/A). |
| `AdvancedQueueInformation.AvailableAgentsAll` | Available agents across all groups. |
| `AdvancedQueueInformation.CurrentGroup` | Current call distribution group. |
| `AdvancedQueueInformation.TotalGroups` | Total call distribution groups. |
| `AdvancedQueueInformation.FailureCode` | Failure code on error. |
| `AdvancedQueueInformation.FailureDescription` | Failure description on error. |

### Callback

| Variable | Description |
|---|---|
| `Callback.FailureCode` | Failure code on error. |
| `Callback.FailureDescription` | Failure description on error. |

Event flow: `CallbackFailed` event exposes a `reason` output (e.g., `AMD` for answering machine detection).

### Escalate Call Distribution Group

| Variable | Description |
|---|---|
| `EscalateGroup.CurrentGroup` | Current distribution group. |
| `EscalateGroup.TotalGroups` | Total distribution groups. |
| `EscalateGroup.FailureCode` | Failure code on error. |
| `EscalateGroup.FailureDescription` | Failure description on error. |

---


## Global Event Flows

Every Flow Designer flow includes a set of **global event handlers** that fire on lifecycle events. These are separate from the main flow canvas — accessible via the **Event Flows** tab in the designer. By default they are empty stubs, but you can wire activities to them for custom logic.

| Event | Fires When | Use Case |
|---|---|---|
| `AgentAccepted` | A human agent accepts an escalated call | Log escalation time, update CJDS, set post-answer variables |
| `AgentOffered` | A call is offered to an agent (ringing) | Track offer-to-answer metrics |
| `PreDial` | Before an outbound call is placed | Inject SIP headers, modify caller ID |
| `OutboundCampaignCallResult` | An outbound campaign call completes | Record campaign outcome |
| `OnGlobalError` | An unhandled error occurs in any activity | Play generic error TTS, route to fallback queue, log error |
| `PhoneContactEnded` | The phone contact terminates (any reason) | Write final CJDS event, clean up variables |
| `AgentDisconnected` | The agent disconnects from the call | Trigger wrap-up logic, post-call survey |
| `CallbackFailed` | A courtesy, scheduled, or personal scheduled callback fails | Retry callback with Wait + re-queue, track retry count |
| `ContactAniUpdated` | The caller's ANI changes (e.g., operator desk transfer) | Update agent desktop with original caller ID |

### OnGlobalError

The most commonly used global event. Without it, an unhandled activity error (e.g., HTTP timeout, invalid variable) silently drops the call. Wire it to a **PlayMessage** + **QueueContact** path as a safety net:

```
OnGlobalError → PlayMessage ("We're experiencing difficulties. Please hold.")
  → QueueContact (fallback queue)
  → PlayMusic (hold loop)
```

### PhoneContactEnded

Fires after the call terminates regardless of how it ended (AI handled, escalated, errored, caller hung up). Useful for writing a final CJDS event or updating a global variable with the interaction outcome.

> **Note:** Do not add any IVR activity after the `PhoneContactEnded` event. During flow execution, activities added after the contact ends will not work.

### CallbackFailed

Fires when a courtesy callback, scheduled callback, or personal scheduled callback fails. Failure conditions:

- The contact is busy or unavailable, or there is no answer from the contact
- The agent's phone is not reachable or the agent declines the call (call moves back to queue and routes to another available agent)
- For scheduled callbacks: the scheduled end time is reached without the call being routed to an agent
- For personal scheduled callbacks: the assigned agent is not logged in

**Retry pattern:** Configure a local flow variable (using SetVariable) with value 0 and increment it per retry. Attach a Wait activity followed by a Callback or any queuing activity (Queue To Agent, Queue Contact) in any combination or order after the Wait.

**Ending retries:**
- True condition (retries remaining): use End Flow activity. Do not use Disconnect.
- False condition (retries exhausted): use Disconnect after the retry variable check.

**Retry limits:**
- Maximum callback retry attempts: **10**
- Maximum interaction lifetime in the system: **14 days**
- Whichever occurs first is the life of the interaction
- Minimum Wait delay between retries: **10 seconds**
- Maximum Wait delay between retries: **72 hours**

> **Note:** When a callback to a contact fails, the contact is dequeued and the CallbackFailed event generates. The retry handler can queue it again using Callback (same or different destination), Queue Contact, and/or Queue To Agent. If callback is configured to a different destination in the `CallbackFailed` event handler, skills will not be carried forward. For scheduled callback or personal scheduled callback, use `NewContact.DNIS` in the Callback activity if configured in the retry flow.

### AgentAccepted

Fires when a human agent accepts (answers) a queued inbound call. The **Queue To Agent** activity triggers this event. Use it to execute post-answer logic before the caller and agent begin speaking — for example, setting agent-visible variables, writing a CJDS event, or triggering a Screen Pop.

**Key use cases:**
- Log escalation timestamp to a flow variable or CJDS
- Set agent-visible variables (e.g., customer tier, case number) via Set Variable
- Trigger a Screen Pop to open a CRM record on the agent's desktop

> **Note:** The AgentAccepted event handler runs in parallel with the call connection — keep logic lightweight to avoid delaying the conversation. For output variables, see [Global Event Output Variables](flow-designer-activities/global-event-output-variables.md#agentaccepted).

### AgentOffered

Fires when a voice contact is offered to an agent (the agent's phone is ringing but not yet answered). Only the **Queue Contact** activity exposes this event. The primary use case is configuring a **Screen Pop** so that customer information appears on the agent's desktop before they answer.

**Key use cases:**
- Screen Pop a CRM record or customer context before the agent picks up
- Track offer-to-answer metrics by logging the offered timestamp

**Restrictions:**
- The `AgentOffered` event is **not supported** for progressive, predictive, and preview campaigns.
- Event handlers such as AgentOffered are populated based on the activities you add in the main flow — if no Queue Contact activity exists, the event is not available.

> For output variables, see [Global Event Output Variables](flow-designer-activities/global-event-output-variables.md#agentoffered).

### PreDial

Fires before an outbound call leg is placed — including inbound-to-agent legs, outdial calls, courtesy callbacks, campaign calls, transfers, and consults. Any activity in the main flow that generates an outbound call leg populates this event handler. The primary purpose is to customize the outbound caller ID (ANI) using the **Set Caller ID** activity.

**Key use cases:**
- Customize caller ID per call scenario (inbound, outdial, callback, transfer, consult)
- Set local-presence ANI for outbound campaigns
- Display the caller agent's DN/extension to the receiving agent on internal transfers

**Restrictions:**
- **Set Caller ID must be the terminal activity** in the PreDial event flow. Configure every PreDial event handler path with Set Caller ID at the end; otherwise the contact can be abandoned.
- **Do not use flow activities that queue a contact** (Queue Contact, Queue To Agent, Callback) in the PreDial event handler.
- The PreDial event fires for each call leg separately — agent leg and customer leg may each trigger it with different `PreDial.participantType` values.

> For output variables and the operationType mapping table, see [Global Event Output Variables](flow-designer-activities/global-event-output-variables.md#predial).

### OutboundCampaignCallResult

Fires when an outbound campaign call completes and Call Progress Analysis (CPA) determines the outcome. Use this event to branch on the CPA result and take appropriate action — for example, playing a message to a live customer, disconnecting on answering machine detection, or logging an abandoned call.

**Key use cases:**
- Branch on `CPAResult` value: `LIVE_VOICE` (play IVR message or route to agent), `AMD` (disconnect or leave voicemail), `ABANDONED` (log and clean up)
- Play a pre-recorded message or route to a Virtual Agent V2 for IVR campaigns when `LIVE_VOICE` is detected
- Add call control activities such as Play Music, Disconnect Contact, or Queue Contact based on the CPA result

**Restrictions:**
- This event is only available when an outbound campaign flow is configured in the main flow.
- For IVR campaigns where a `LIVE_VOICE` customer needs to be escalated to a live agent, a separate flow must be used for the queuing logic.

> For output variables (`CPAResult`, `CPAResultCode`), see [Global Event Output Variables](flow-designer-activities/global-event-output-variables.md#outboundcampaigncallresult).

### ContactAniUpdated

Fires when the ANI of the caller changes. For example, if a customer's call first goes to an operator desk and is then sent to the agent, the agent's desktop, agent device, and all related information are automatically updated with the caller's ANI. This ensures that the original caller's ID and correct details are always shown.

> **Note:** Only call transfers initiated from desk phones or Jabber clients on-premises reflect the final CLI. Transfers performed via the Webex App on Webex Calling do not update to show the final CLI.

### Event Output Variables

For the full output variable tables for each event handler (AgentAccepted, PhoneContactEnded, AgentOffered, AgentDisconnected, PreDial, OutboundCampaignCallResult), see **[Global Event Output Variables](flow-designer-activities/global-event-output-variables.md)**.

---


## Queue Contact Activity

Routes a contact to a queue where it waits for an available agent. This is the primary activity for connecting callers to human agents.

### Configuration

**General Settings:**

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | Optional description |

**Queue Selection:**

| Field | Description |
|---|---|
| Static Queue | Select a specific queue from the dropdown |
| Variable Queue | Select a STRING flow variable that resolves to a queue ID at runtime. Requires a **Fallback Queue** selection in case the variable is invalid. |

**Contact Priority:**

| Field | Description |
|---|---|
| Set Contact Priority | Toggle (default: disabled). When enabled, assign priority P1–P9 (P1 = highest). |
| Static Priority | Select a fixed priority value from the dropdown |
| Variable Priority | Select an INTEGER flow variable (1–9). Values outside 1–9 default to priority 10 (lowest). |

**Agent Availability:**

| Field | Description |
|---|---|
| Check Agent Availability | Toggle (default: disabled). When enabled, the activity checks if agents are available before queueing. |
| Always Check Agent Availability | Radio button (default). Always checks before queueing. |
| Variable Check Agent Availability | Radio button. Uses a flow variable to determine whether to check. |

**Skill Requirements** (only when the queue uses skill-based routing):

| Field | Description |
|---|---|
| Skill | Select a skill from the dropdown |
| Condition | IS, IS NOT, >=, <= |
| Skill Value | Static value or flow variable |
| Remove skills on blind transfer | Toggle — removes skill requirements if the call is blind-transferred out of this queue |

**Skill Relaxation:**

| Field | Description |
|---|---|
| Enable Skill Relaxation | Toggle. When enabled, skill requirements are progressively loosened after a wait threshold. |
| After waiting in queue for | Seconds before first relaxation step (default: 60) |
| Relaxation Steps | Add multiple steps, each removing or loosening specific skill requirements |

### Output Variables

| Variable | Description |
|---|---|
| `QueueContact.QueueId` | Queue identifier |
| `QueueContact.FailureCode` | Error code on failure |
| `QueueContact.FailureDescription` | Error description on failure |

### Failure Codes

| Code | Description |
|---|---|
| 1 | INVALID_REQUEST |
| 2 | INVALID_ROUTING_STRATEGY |
| 3 | INVALID_WAIT_TIME |
| 4 | INVALID_QUEUE |
| 5 | ROUTING_LIMIT_EXCEEDED |
| 6 | SYSTEM_ERROR |
| 7 | VTEAM_TRANSITION_LIMIT_REACHED |
| 8 | OWNER_ASSIGNED_TO_INTERACTION |
| 9 | INVALID_SKILL_NAME |
| 10 | INVALID_SKILL_CONDITION |
| 11 | INVALID_SKILL_VALUE |
| 12 | INVALID_OPERATION_FOR_INTERACTION_STATE |

### Output Paths

| Path | Description |
|---|---|
| Default exit | Continues to the next wired activity after the contact is placed in queue. Typically wired to Play Music for hold treatment. The flow continues executing this path while the contact waits; when an agent accepts, the `AgentAccepted` event fires. |
| Undefined Error | Error-handling path for system errors during flow execution. If not configured, the flow uses the `OnGlobalError` event handler. |

> **"Default exit" is this project's label, not Cisco's.** Cisco never names a success or exit port for Queue Contact. The [Flow Designer help article](https://help.webex.com/en-us/article/nhovcy4/Build-and-manage-flows-with-Flow-Designer) documents the activity's General Settings, Contact Handling, Contact Priority, skills, output variables (`QueueId`, `FailureCode`, `FailureDescription`) and an error-code table, but no named output path — unlike Virtual Agent V2, whose `Handled` / `Escalated` / `Errored` ports Cisco does name. The continuation behaviour itself *is* documented: "it is recommended to introduce a short delay—such as by adding a Play Message or Play Music activity—between the Queue Contact and HTTP Request activities." The FlowIR/API edge condition for this path is `default` — see [flow-designer-flowir.md § Queue Contact `default` Edge Condition Warning](flow-designer-flowir.md), which records that the validator warns `default` is invalid for `queue-contact` but that it works correctly at runtime and is what wires the hold-treatment path.

> **UNRESOLVED — is Queue Contact terminal?** Cisco's flow-validation error-code table contains "FC1014 — Queue Contact must stop flow. The output link can only connect to an End Flow activity." Its neighbours scope themselves explicitly to the Event Flow ("FC1012 — A broken link in the Event Flow causes the error"; "FC1013 — The system uses the activity in more than one Event Flow"), but FC1014 states no scope. So "Queue Contact is terminal" may be correct **inside an Event Flow** and wrong in a main flow, where the hold-treatment continuation above is the documented pattern. Not resolved here — do not treat either reading as settled. [source: [Build and manage flows with Flow Designer](https://help.webex.com/en-us/article/nhovcy4/Build-and-manage-flows-with-Flow-Designer) § flow validation error codes]

> **System queue time limit:** The maximum time a telephony contact can remain in queue is **86,400 seconds** (24 hours). After this limit the contact is removed from the queue. Digital channels have different limits (chat: 86,400 s; digital: 604,800 s; email: 1,209,600 s). These are system-enforced limits, not configurable per-activity — see [System limits in Webex Contact Center](https://help.webex.com/article/n7s6ed7).

### Restrictions

- Variable Queue does not support skill-based routing — it reverts to Longest Available Agent algorithm.
- An HTTP Request placed immediately after Queue Contact may fail due to timing. Add a delay activity (Play Message or Wait) between them.

---


## Disconnect Contact Activity

Terminates an active call. This is a **terminal node** — the flow ends at this point.

### Configuration

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | Optional description |

No additional configuration is required.

### Output Variables

None.

### Usage

- Place at the end of every flow path to ensure calls are properly terminated.
- Multiple Disconnect Contact activities can be used in a single flow — one per exit path — to ensure the call terminates regardless of which path is taken.
- Use Disconnect Contact (not End Flow) when a caller is on the line. End Flow terminates the flow logic; Disconnect Contact terminates the phone call.

---

## See Also

- [flow-designer-flowir.md](flow-designer-flowir.md) — the FlowIR property reference for these activities
- [flow-designer-patterns.md](flow-designer-patterns.md) — patterns and advanced topics
- [wxcc-platform.md](wxcc-platform.md) — platform setup, including global variables
- [_index.md](flow-designer-activities/_index.md) — every activity not covered here, one file each
