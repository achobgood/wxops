## Call Progress Analysis Activity

<!-- ref-tag: fd-act-call-progress-analysis-v1 -->

Detects whether an outbound call was answered by a live person or an answering machine. Used in callback and outbound campaign scenarios.

**Prerequisites:** This activity is available only if the preferred queue and the callback features are enabled for the enterprise.

**Survey note:** If you have configured a postcall customer survey in your flow, it will not be initiated if the call is answered by an AMD or voicemail, preventing unnecessary surveys.

### Configuration

**General Settings:**

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | Optional description |

**Advanced Media Parameters:**

| Field | Default | Range | Description |
|---|---|---|---|
| Min Silence Period | 608 ms | 100–1000 ms | Minimum silence duration to detect a pause in speech |
| Analysis Period | 2500 ms | 1000–10000 ms | Window of time to analyze the audio for voice/machine detection |
| Min Valid Speech | 112 ms | 50–500 ms | Minimum speech duration to consider as valid voice |
| Max Time Analysis | 3000 ms | 1000–10000 ms | Maximum time to spend on analysis before returning a result |

### Output Variables

| Variable | Description |
|---|---|
| `CallProgressAnalysis.FailureCode` | Error code on failure |
| `CallProgressAnalysis.FailureDescription` | Error description on failure |

### How CPA Results Are Communicated

The Call Progress Analysis activity does **not** expose its own branch edges (e.g., "Live Voice" / "Machine Detected" output paths on the node itself). Instead, the CPA detection result is communicated through **event handler output variables**, depending on the scenario:

> **Note:** The activity does expose a single `failure` error output port (isErrorPath), but no result-based branches — the Live-Voice/Machine-Detected outcome always arrives via the events described below (wxcc-flow describe call-progress-analysis (today `wxcli cc-flow show-activity PROJECT_ID call-progress-analysis`) → `outputPorts`: `failure`; flow-designer-flowir.md § 8).

**Callback scenario (courtesy, scheduled, or personal):**

When a callback attempt encounters an answering machine or voicemail, the system marks the call as unsuccessful and fires the **CallbackFailed** global event. The AMD result is captured in the `CallbackFailed.reason` output variable.

| `CallbackFailed.reason` value | Meaning |
|---|---|
| `AMD` | Answering machine / voicemail detected |
| Other values | Other failure reasons (no answer, busy, etc.) |

Branch on `CallbackFailed.reason == "AMD"` in the CallbackFailed event handler to distinguish answering-machine failures from other callback failures.

**Outbound campaign scenario (progressive/predictive IVR campaigns):**

CPA results are delivered through the **OutboundCampaignCallResult** event, which exposes two output variables:

| Variable | Description |
|---|---|
| `OutboundCampaignCallResult.CPAResult` | The CPA detection result string |
| `OutboundCampaignCallResult.CPAResultCode` | Numeric code for the CPA result |

| `CPAResult` value | Meaning |
|---|---|
| `AMD` | Answering machine detected |
| `ABANDONED` | Call abandoned due to unavailability of an agent |
| `LIVE_VOICE` | Live voice of a customer detected (IVR campaigns) |

Add call control activities (Play Music, Disconnect Contact, etc.) to the OutboundCampaignCallResult event handler and branch on the `CPAResult` value.

> For outbound campaigns, CPA/AMD must also be enabled at the campaign group level: turn on the **Terminating Tone Detection** toggle in the **Configure Campaign Group** page in Campaign Manager.

### Failure Codes

> **Documentation pending** — specific failure codes for the Call Progress Analysis activity are not enumerated in the Cisco help docs. The `FailureCode` and `FailureDescription` output variables follow the same pattern as other activities (e.g., Callback uses codes 1–6). Verify specific CPA failure codes in a live tenant.

### Placement

- In the main flow, at any point after a **Callback** activity (courtesy callback)
- In the main flow, after **NewPhoneContact** for scheduled callback or personal scheduled callback scenarios
- In the **CallbackFailed** event handler (event flow only — not supported in other event handlers)

### Restrictions

- **Feature gate:** Available only when the preferred queue and callback features are enabled for the enterprise.
- **Event flow placement:** In event flows, the activity is supported **only** in the CallbackFailed event handler — not in other event handlers.
- **Self-loop limit:** 10 (see [self-loop-limits.md](self-loop-limits.md)).
- **Post-call survey suppression:** When CPA detects AMD/voicemail, the Feedback V2 (survey) activity is automatically suppressed — the survey will not be initiated.
- **Outbound campaign prerequisite:** For progressive campaigns, CPA and AMD must be enabled at the campaign group level with the Terminating Tone Detection toggle.

### Wiring Pattern — Courtesy Callback with CPA

```
Queue Contact → Play Message ("We'll call you back") → Callback ({{NewContact.ANI}})
  │
  ▼
Call Progress Analysis (configure AMD parameters)
  │
  ▼
Disconnect Contact
```

**In the CallbackFailed event handler:**

```
CallbackFailed fires
  │
  ▼
Condition: {{CallbackFailed.reason}} == "AMD"
  ├── TRUE (answering machine) → [optional: increment retry counter]
  │     → Wait (retry interval, min 10s, max 72h)
  │       → Callback (retry) → Call Progress Analysis → Disconnect Contact
  └── FALSE (other failure) → [log failure / end]
```

> **Retry limits:** The maximum number of callback retry attempts is 10, across a maximum span of 14 days. The delay between retries is configured using the Wait activity (minimum 10 seconds, maximum 72 hours).

### Wiring Pattern — Outbound Campaign with CPA

```
OutboundCampaignCallResult event fires
  │
  ▼
Condition: {{OutboundCampaignCallResult.CPAResult}} == "LIVE_VOICE"
  ├── TRUE → [continue IVR flow / connect to agent]
  └── FALSE → Condition: {{OutboundCampaignCallResult.CPAResult}} == "AMD"
        ├── TRUE → Play Music (brief) → Disconnect Contact
        └── FALSE (ABANDONED) → Disconnect Contact
```

---

