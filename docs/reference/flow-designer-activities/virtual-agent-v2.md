## Virtual Agent V2 Activity

<!-- ref-tag: fd-act-virtual-agent-v2-v1 -->

The Virtual Agent V2 activity provides a real-time conversational experience for contacts. It handles speech-based AI-enabled conversations within the IVR flow. When a caller speaks, the system matches the speech to the best intent in the virtual agent.

> Do not place a Virtual Agent V2 activity after a Queue Contact activity — this configuration is not supported. Do not place a Virtual Agent V2 activity in the Event Flow canvas.

### Configuration

**General Settings:**

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | Optional description |

**Conversational Experience — CCAI Config:**

| Option | Description |
|---|---|
| **Static** | Choose the CCAI config to handle conversations within the default PSTN region. The Contact Center AI config is populated based on the CCAI feature configured on Control Hub. |
| **Variable** | Choose the CCAI config to handle conversations within the same location of the caller while the call originates from a remote or non-default PSTN region. This variable maps the PSTN region to the corresponding Google profile region. |

**Language and voice override (Variable CCAI config):** For a VAV flow to work, set the global variables in the flow to configure the default input language and output voice. If you want to override the default input language and output voice, include a Set Variable activity before the Virtual Agent V2 activity:

- For custom input language: set the variable to `Global_Language` with the required language code (e.g., `fr-CA`)
- For custom output voice: set the variable to `Global_VoiceName` with the required output voice name code (e.g., `en-US-Standard-D`)

**Connector types** (visible in exported flow JSON, set automatically by CCAI Config selection):

| Connector Value | Agent Type | CCAI Config Selection |
|---|---|---|
| `NATIVE_ADVANCED_VIRTUAL_AGENT` | Autonomous | "Webex AI Agent Autonomous" |
| `NATIVE_BASIC_VIRTUAL_AGENT` | Scripted | "Webex AI Agent Scripted" |

### State Event Settings

The State Event settings panel has two columns: **Event Name** and **Event Data**. These serve two distinct purposes depending on whether Event Name is blank or populated:

| Event Name | Event Data | Purpose | Agent Type |
|---|---|---|---|
| *(blank)* | Key-value pairs | **Custom data at session start** — passes data to the agent before it speaks. Variables accessible via `{{variable_name}}` in agent Goal, Welcome Message, Instructions, Action descriptions, Slot descriptions. | Autonomous |
| Custom event name (e.g., `custom_welcome`) | Key-value pairs | **Incoming custom event** — triggers a specific response in the agent, bypassing the default welcome. Data accessible via `${eventStore.<key>}` in the response. | Scripted |
| `{{event_name}}` variable | `{{event_data_string}}` variable | **Fulfillment resume** — returns fulfillment results to the agent after a Custom Event exit. See "Flow Designer — Scripted Agent Fulfillment Pattern" below. | Both |

> **Autonomous custom event fulfillment:** When an autonomous agent action is configured with "Set custom logic for fulfillment" in AI Agent Studio, it exits via `StateEventName`/`MetaData` just like scripted Custom Events. The State Event resume mechanism (row 3) is used to return the result.

Event Data values support Flow Designer variable syntax: `{{NewContact.ANI}}`, `{{StoreName}}`, etc. Use SetVariable activities to prepare the values before the VAV2 activity.

You can specify the event name and data as a static value or expression using `{{ variable }}` syntax. Example:

- **Event Name:** `CustomWelcome`
- **Event Data:** `{"Name": "John"}`

### Advanced Settings

| Field | Default | Range | Description |
|---|---|---|---|
| Speaking Rate | 1.0 | 0.25–4.0 | Rate of speech output. Lower values slow speech; higher values speed it up. Supports `{{variable}}` expressions. |
| Volume Gain | 0.0 dB | -96.0–16.0 dB | Increase or decrease the volume of speech output. Supports `{{variable}}` expressions. |
| Pitch | 0.0 Hz | -20.0–20.0 Hz | Increase or decrease the pitch of speech output. Supports `{{variable}}` expressions. |
| Termination Delay | 30 seconds | 0–30 seconds | Time to wait after the conversation ends before the activity exits. Gives the AI agent time to deliver a final response before the flow takes over. If set to 0, the system does not play the last audio message to the caller. |
| Enable Conversation Transcript | (checkbox) | — | Enables Agent Desktop to display the transcript of the conversation between the virtual agent and the caller. The raw transcript is also available through a dynamic URL that can be used to extract specific sections via HTTP request. |

### Decryption Settings

If decryption is enabled at the flow level, users with debug decryption access can view the unmasked output values of the VAV2 activity in the flow debug logs. Turn off the **Enable decryption** toggle to disable decryption at the activity level for additional protection.

### Default System-Level Settings

The following settings are defined in the system internally by default. They do not appear on the user interface and cannot be changed:

- Infinite number of retries for handling invalid or no input errors
- Barge-in is enabled to interrupt the Virtual Agent during interaction
- DTMF termination symbol = #. Indicates the end of input.
- DTMF No-Input Timeout = 5 seconds. Time the Virtual Agent waits for the caller's input.
- DTMF Inter-digit Timeout = 3 seconds. Time the Virtual Agent waits for the next DTMF input before moving on in the conversation flow.

### Output Variables

| Variable | Description |
|---|---|
| `VirtualAgentV2.TranscriptURL` | URL to the AI agent conversation transcript. |
| `VirtualAgentV2.MetaData` | JSON data from the agent (fulfillment, custom events, transfer actions). Not applicable for Dialogflow-based Virtual Agent V2 agents. |
| `VirtualAgentV2.StateEventName` | Name of the custom event received from the agent. Not applicable for Dialogflow-based Virtual Agent V2 agents. |

> Use the Parse activity to extract parameters from the Virtual Agent Voice transcript.

### Output Paths

| Output Path | Fires When |
|---|---|
| **Handled** | Virtual agent execution completed. |
| **Escalated** | Call needs to be escalated to a human agent. |
| **Errored** | Any error scenario during the conversation. |

> For scripted agents, `Handled` is called `ENDED` in the flow JSON. The `ENDED` output fires when the agent raises a **Custom Event** (for fulfillment) or completes the conversation. The `StateEventName` and `MetaData` variables are populated on the `ENDED` path.

**Errored path details:** The Errored path fires on any error during the virtual agent conversation (e.g., connectivity failures, AI engine errors, CCAI config issues). Unlike the legacy Virtual Agent activity, **Virtual Agent V2 does not expose a `VirtualAgentV2.ErrorCode` output variable** — there is no programmatic way to distinguish error types on the Errored path. The flow developer should connect the Errored path to a Play Message or other graceful-failure activity. If no error handling path is configured, the flow falls back to the `OnGlobalError` event handler.

> **Documentation pending** — Cisco help docs confirm the Errored path fires "in any error scenarios" but do not enumerate specific error codes or an error output variable for VAV2. If Cisco adds an ErrorCode variable in a future release, update this section.

### Differences from Legacy Virtual Agent

The legacy Virtual Agent activity (Dialogflow ES) provides two output variables that **Virtual Agent V2 does not have**:

| Legacy Variable | Description | VAV2 Equivalent |
|---|---|---|
| `VVA.LastIntent` | Last intent triggered before Escalation or Handled. | **Not available.** VAV2 does not expose an intent-level output variable. For scripted agents, intent context is embedded in `VirtualAgentV2.MetaData`. For autonomous agents, the agent handles intent resolution internally. |
| `VVA.ErrorCode` | Status code with values: `no_error`, `max_no_input`, `term_char_without_input`, `system_error`. | **Not available.** VAV2 uses infinite retries by default (no Max No-Input Attempts setting) and does not surface error codes. The Errored output path is the only error signal. |

### Restrictions

- Do not place after a Queue Contact activity
- Do not place in the Event Flow canvas
- Currently, en-US is the only supported language
- Only the U-law codec is supported

---

