## Feedback V2 Activity

<!-- ref-tag: fd-act-feedback-v2-v1 -->

Presents a post-call IVR survey to the caller after the agent disconnects. Collects CSAT, NPS, or custom scores via DTMF input. Found in the **Activity Library** under **Contact handling**.

### Key Differences from Legacy Feedback

- Feedback V2 is the current version; the legacy Feedback activity is powered by Webex Experience Management — avoid the legacy version in new flows.
- Feedback V2 supports **IVR voice surveys only** (no Email/SMS dispatch). The legacy Feedback activity supported Email/SMS-based surveys via Webex Experience Management dispatch policies.
- Feedback V2 uses questionnaires created in **Control Hub → Contact Center → Customer Experience → Surveys** (Survey Builder), not Webex Experience Management.

### Configuration

#### General Settings

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | (Optional) Description for the activity |

#### Survey

Select a voice-based (IVR) survey questionnaire from the drop-down list. The list shows questionnaires created in Survey Builder (Control Hub → Contact Center → Customer Experience → Surveys).

Supported survey metric types and their DTMF scales:

| Metric | DTMF Scale | Description |
|---|---|---|
| NPS (Net Promoter Score) | 0–9 | Caller presses any number between 0 and 9 |
| CSAT (Customer Satisfaction) | 1–5 | Caller presses a number between 1 and 5 |
| CES (Customer Effort Score) | 1–5 or 1–7 | Caller presses a number within the configured range |
| Other (Custom) | Configurable min/max | Custom scale with administrator-defined minimum and maximum valid inputs |

The survey questionnaire in Survey Builder also includes:
- **Thank You note** — upload an IVR audio prompt to thank the customer after the survey completes.
- **Invalid Input prompt** — upload an audio file to inform the caller of invalid input.
- **Timeout prompt** — upload an audio file to play when the caller does not respond in time.

#### Language Settings

| Field | Description |
|---|---|
| Override Language Settings | Enable to set a custom language for the survey. When disabled, the `Global_Language` variable defines the survey language. |
| Set Language | Select the preferred language from the drop-down list. Appears only when Override Language Settings is enabled. |

#### Advanced Settings

| Field | Default | Description |
|---|---|---|
| Timeout | 3 seconds | Maximum duration the activity waits for a DTMF response from the caller before treating it as a timeout. |
| Maximum invalid inputs and timeout allowed | — | Maximum number of retry attempts for invalid or no DTMF input before the survey terminates. Exact valid range not documented. |

#### Prerequisites

- The `Global_FeedbackSurveyOptin` global variable must be set to `true` before the Feedback V2 activity executes. Add it via Flow configuration → Global Properties → Predefined Variables → check `Global_FeedbackSurveyOptin`.
- The activity must be placed in the **AgentDisconnected** event flow, not on the main flow canvas.
- A **Disconnect Contact** activity must follow the Feedback V2 activity to end the IVR call.
- A Consult interaction cannot include a Post Call Survey Feedback activity.
- Self-loop limit: a single Feedback V2 activity can execute a maximum of **10** times (runtime iteration cap, not a limit on how many Feedback V2 nodes can be placed in a flow).

### Output Variables

No activity-specific output variables (the live registry exposes only a generic `status`, undocumented). Survey responses (including partial responses) are sent directly to the Survey Builder reporting in WxCC Analyzer — they are not captured as flow variables. [source: wxcc-flow describe Feedback-V2 → outputs: status; flow-designer-flowir.md § 8]

### Output Paths

| Output Path | Fires When |
|---|---|
| *(default exit)* | Survey completes (fully or partially) — wire to Disconnect Contact |
| **Undefined Error** | System error during survey execution (e.g., questionnaire load failure, platform error) |

> **Note:** Timeout and invalid input within the survey are handled internally by the activity's retry/prompt mechanism (configured via the Survey Builder prompts and the "Maximum invalid inputs and timeout allowed" field). They do not produce separate output paths. If the caller exhausts all retries or the survey otherwise ends, the activity exits via the default path with whatever partial responses were captured.

### Timeout & Invalid Input Behavior

If the caller partially answers the survey — either by not responding within the configured timeout duration or by providing invalid input — the contact center captures partial survey responses and sends them to reporting. The activity plays the configured invalid-input or timeout audio prompts and retries up to the maximum allowed before exiting.

### Wiring

```
AgentDisconnected (Event Flow)
  → Set Variable (Global_FeedbackSurveyOptin = true)  ← if not already set
  → Feedback V2 (plays questionnaire, collects DTMF scores)
  → Disconnect Contact
```

Survey results are available in WxCC Analyzer reporting.

---

