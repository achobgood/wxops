## Virtual Agent Activity

<!-- ref-tag: fd-act-virtual-agent-legacy-v1 -->

> **Legacy activity.** The Virtual Agent activity uses Google Dialogflow ES. For new flows, prefer [Virtual Agent V2](#virtual-agent-v2) which supports multiple AI engines including Webex AI Agent.

The Virtual Agent activity provides a real-time conversational experience for your contact center customers. You can add a Virtual Agent to the call flow to handle customer queries in the conversational format. The Virtual Agent is powered by Google's Dialogflow capabilities. When a customer speaks, the Dialogflow matches the customer conversation to the best intent in the Virtual Agent. Further, it assists the customer as part of the Interactive Voice Response (IVR) experience.

### Prerequisites

- Set up a Dialogflow agent in Google Cloud. Include "Hello" as a training phrase in the preferred language for the Dialogflow agent to start a conversation with the caller. You can add this training phrase in the default welcome intent or in any other intent of the Dialogflow agent.
- Configure a Virtual Agent in Control Hub.

### Configuration

#### General Settings

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | (Optional) Description for the activity |

#### Conversational Experience

| Field | Description |
|---|---|
| Virtual Agent | Choose a Virtual Agent configured in Control Hub. The Virtual Agent powers the natural language conversation as part of the IVR experience with the caller. |
| Make Prompts Interruptible | Enables the customers to interrupt the Virtual Agent to make new requests or end the call. |
| Override Default Language & Voice Settings | Toggle to override the language and voice settings configured in `Global_Language` and `Global_VoiceName` variables. Enabled by default. To use the flow, you need to set the global variables to configure the default input language and output voice for the virtual agent. |
| Input Language | The language the customer uses while speaking to the Virtual Agent. Appears only when Override Default Language & Voice Settings is enabled. Virtual Agent voice deployments in Webex Contact Center support only languages with the recognition model as an enhanced phone call available with Dialogflow Essentials (ES). If the input language that Google supports is not available in the Input Language drop-down list, disable the Override Default Language & Voice Settings toggle button and include a Set Variable activity before the Virtual Agent activity. Set the variable to `Global_Language` and the value to the required language code (for example, `fr-CA`). |
| Output Voice | Default value is `Automatic`. When Automatic, the Dialogflow chooses the voice name for a given language. Ensure the voice name configured matches the chosen language. If the output voice name that Google supports is not available in the Output Voice drop-down list, disable Override Default Language & Voice Settings and include a Set Variable activity before the Virtual Agent activity. Set the variable to `Global_VoiceName` and the value to the required output voice name code (for example, `en-US-Standard-D`). |

### Variable Passing

The optional parameters in the Virtual Agent activity may contain personally identifiable information (PII). Webex Contact Center passes these parameters to Google Dialogflow as variables to support advanced conversational logic with the bot.

| Field | Description |
|---|---|
| Key-Value | Allows you to enter a variable name and the associated value. You can enter variable values by using the double curly braces syntax. Example: Key = `ANI`, Value = `{{NewContact.ANI}}`. Click **Add New** to add a row for each key-value pair. The contact center sends these parameter values to Google Dialogflow as a JSON value in the `request.query_param.payload` object. The system parses and handles this JSON in the fulfillment application reached through the webhook configured in Dialogflow. |

### Advanced Settings

| Field | Default | Range | Description |
|---|---|---|---|
| No-Input Timeout | 5 seconds | 1–30 seconds | The amount of time the Virtual Agent waits for customer input (voice or DTMF). |
| Max No-Input Attempts | 3 | 0–9 | The number of times the Virtual Agent waits for customer input (voice or DTMF). When the maximum number of attempts elapse, the Virtual Agent exits with the output variable ErrorCode set to `max_no_input`. |
| Inter-digit Timeout | 3 seconds | 0–30 seconds | The amount of time the Virtual Agent waits for the next DTMF input from the customer before the Virtual Agent moves on in the conversation flow. |
| Terminator Symbol | — | `#` or `*` | The character the customer enters to indicate the end of input. The Terminator Symbol can be either `#` or `*` depending on the configuration. |
| Termination Delay | — | 1–30 seconds | Enables the Virtual Agent to complete the last message before the activity stops and moves on to the next step in the flow. For example, if you want the Virtual Agent to indicate something to the caller before the system escalates the call to an agent, consider the time it takes to complete the final message before escalation. If configured as 0, the system does not play the last audio message to the caller. |
| Speaking Rate | 1.0 wpm | 0.25–4.0 wpm | The rate of speech. Increase or decrease the numeric input to maintain the ideal rate of speech and control the output speaking rate. |
| Volume Gain | 0.0 dB | -96.0–16.0 dB | The increase or decrease in volume output. Increase or decrease the numeric input to maintain the ideal volume of output speech. |
| Enable Conversation Transcript | — | — | Enables the Desktop to display the transcript of the conversation between the Virtual Agent and the customer. The raw transcript is also available through a dynamic URL. You can use this URL to extract specific sections from the transcript using an HTTP request. |

### Output Variables

| Variable | Description |
|---|---|
| `VVA.LastIntent` | Stores the last intent that is triggered by the Virtual Agent before moving to the Escalation or Handled intent. |
| `VVA.TranscriptURL` | Stores the URL that points to the transcript of the conversation between the Virtual Agent and the customer. Use the Parse activity to extract parameters from the Virtual Agent transcript. |
| `VVA.ErrorCode` | Stores the status code whose value depends on the outcome of the conversation between the Virtual Agent and the customer. Values listed below. |

#### VVA.ErrorCode Values

| Value | Description |
|---|---|
| `no_error` | Indicates that the Handled and Escalated outputs had no errors. |
| `max_no_input` | Indicates that the customer didn't have any input errors within the specified Max No-Input Attempts. |
| `term_char_without_input` | Indicates that the customer pressed the termination key without any input (spoken or by key press). The terminator symbol can be either `#` or `*` depending on the configuration. |
| `system_error` | Indicates any other error in the system. For example, Dialogflow error, network issue, and so on. |

### Output Paths

**Outcomes:**

- **Handled** — The Dialogflow takes this path if the system triggers the Handled intent.
- **Escalated** — The Dialogflow takes this path if the system triggers the Escalation intent.

**Error Handling:**

- **Error** — The flow takes this path in any error scenarios. If there is an error, the contact center does not play any audio message to notify the customer of the error, by default. The flow developer can configure a Play Message activity either generically or based on the error code as described in the Output Variables section.

### Restrictions

- Cannot be used directly with `OutboundCampaignCallResult`. For outbound campaign IVR, place a GoTo activity to map the flow to a second flow and use Virtual Agent in the second flow.

---

