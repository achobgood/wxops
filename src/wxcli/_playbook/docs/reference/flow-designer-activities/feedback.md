## Feedback Activity

<!-- ref-tag: fd-act-feedback-v1 -->

> **Legacy activity.** For new flows, prefer [Feedback V2](#feedback-v2-activity).

Configure the Feedback activity to initiate post-call surveys (powered by Webex Experience Management) to collect feedback from callers. The following types of surveys are available:

- **IVR Post Call Surveys**: Configure the Feedback activity in the Event Flows canvas in the Flow Designer, after the AgentDisconnected event. Depending on the setup in Webex Experience Management, the contact center plays an IVR survey to the callers. The caller uses the keypad to answer the survey. If the caller partially answers the survey by not responding within the configured timeout duration or by providing invalid input, the contact center sends partial survey responses to Webex Experience Management. Ensure that you use the Disconnect Contact activity after the Feedback activity to end the IVR call.
- **Email or SMS Post Call Surveys**: Configure the Feedback activity in the Event Flows tab in the Flow Designer after the PhoneContactEnded event. Depending on the dispatch policy rules set up in Webex Experience Management, the contact center sends a survey to callers over email or SMS.

### Configuration

#### General Settings

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | (Optional) Description for the activity |

#### Survey

Select from a list of questionnaires for Voice, or dispatches for Email or SMS surveys. The questionnaires and invitations configured in Webex Experience Management are available in the list.

| Survey Type | Steps |
|---|---|
| Voice Based | Choose the **Voice Based** radio button, then choose the voice-based survey from the drop-down list. |
| Email/SMS Based | Choose the **Email/SMS Based** radio button, then choose the Email or SMS-based survey from the drop-down list. |

#### Language Settings

Manage the language in which the customer experiences the survey. If the language is not supported in Webex Experience Management, the fallback language is English (US).

| Field | Description |
|---|---|
| Override Language Settings | Enable the toggle to set any custom language for Webex Experience Management. |
| Set Language | Select the preferred language from the drop-down list. The drop-down list displays the languages that Webex Experience Management supports. Appears only when Override Language Settings is enabled. |

If Override Language Settings is not enabled, the `Global_Language` variable is used to define the default Webex Experience Management settings.

#### Customer Information

Specify the customer information to be passed along with the prefills that Webex Experience Management sends to capture the survey response. Depending on the dispatch configurations set in Webex Experience Management, the contact center sends the prefill information.

| Field | Description |
|---|---|
| Customer ID | (Optional) Select a unique identifier for the customer from the drop-down list. |
| Email | (Optional) Select the email of the customer from the drop-down list. |
| Phone Number | (Optional) Select the phone number of the customer from the drop-down list. |

### Variable Passing

Specify additional variables as custom prefills that are passed (in addition to survey responses) from Webex Contact Center to Webex Experience Management.

| Field | Description |
|---|---|
| Key-Value | The optional variable parameters that the contact center passes to Webex Experience Management. The Key and Value columns allow you to enter a variable name and the associated value. The variable value can be either a string, an integer, or an expression with double curly braces syntax (in case of flow variable). Click **Add New** to add a row for each key-value pair. |

Variable passing rules:

- To pass any custom variable from the contact center, the administrator must create a custom prefill question in Webex Experience Management.
- The Key parameter in the variable and the Display Name of the prefill question created in Webex Experience Management must be the same.
- If the Key parameter does not match the Display Name of the prefill question, the contact center doesn't send the Key-Value parameters to Webex Experience Management.
- If the variable includes personal information, make sure to enable the **Mark as Personally Identifiable Information (PII)** toggle for that Question in Webex Experience Management.

### Advanced Settings

| Field | Default | Description |
|---|---|---|
| Timeout | 3 seconds | The maximum duration for which the activity waits for response from the customer. You can configure the maximum number of retry attempts in case of invalid or no DTMF input, as well as audio notification messages (for invalid input, timeout, and maximum retries exceeded) for questionnaires by using Webex Experience Management. |

### Output Variables

No output variables are documented for the legacy Feedback activity. Survey responses (including partial responses) are sent directly to Webex Experience Management — they are not captured as flow variables.

### Output Paths

The legacy Feedback activity exposes **no output ports** in the live activity registry (wxcc-flow describe Feedback (today `wxcli cc-flow show-activity PROJECT_ID Feedback`) → `outputPorts: []`, verified 2026-07-11) — in particular, it has **no error path** (unlike Feedback V2, which exposes an `error` port). The activity continues via its default exit to the next activity.

| Output Path | Fires When |
|---|---|
| *(default exit)* | Survey completes (fully or partially) — wire to Disconnect Contact |

> **Note:** Timeout and invalid input within the survey are handled internally by the activity's retry/prompt mechanism (configured via Webex Experience Management questionnaire settings and the Timeout advanced setting). They do not produce separate output paths.

### Restrictions

- A Consult interaction cannot include a Post Call Survey Feedback activity.
- Use the Disconnect Contact activity after the Feedback activity to end the IVR call.
- The Feedback activity must be placed in an Event Flow (AgentDisconnected for voice surveys, PhoneContactEnded for email/SMS surveys), not in the main flow canvas.

---

