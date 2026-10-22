## Start Media Stream Activity

<!-- ref-tag: fd-act-start-media-stream-v1 -->

Streams live call audio to a configured media destination for real-time processing. The activity streams media across two channels — one streams the media from the customer, the other streams the combined media of all internal employees engaged with the customer. Use it to feed live call audio to AI-powered transcription, sentiment analysis, or agent assist services.

### Configuration

**General Settings:**

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | Optional description |

**Media Streaming Settings:**

| Field | Type | Required | Description |
|---|---|---|---|
| Media Destination | Select dropdown | Yes | The media destination that receives the audio stream. Populated from media destinations configured in Control Hub. Default: **Cisco AI Assistant**. |

The Media Destination dropdown is populated from Control Hub's media destination configuration (Contact Center > Settings > Media Destinations). Select the destination that corresponds to the external service receiving the stream.

### Output Variables

| Variable | Type | Description |
|---|---|---|
| `StartMediaStream.status` | String | Status of the stream request — `"success"` or `"failure"` |

### Output Paths

**Non-terminal node.** The activity has one output edge and one error path.

| Path | Condition | Description |
|---|---|---|
| (default) | `status == "success"` | Stream started successfully — flow continues to the next wired activity |
| **Failure** | `status == "failure"` | Stream failed to start — wire to error handling (Play Message, Disconnect, or retry logic) |

### Audio Channels

The activity streams media across **two channels**:

1. **Customer channel** — streams the media from the customer (caller audio)
2. **Employee channel** — streams the combined media of all internal employees engaged with the customer (agent + any conferenced participants)

> **Documentation pending** — exact audio codec (G.711 u-law vs. Linear16), sample rate (8 kHz vs. 16 kHz), and encoding format for the media stream are not verified against Cisco help docs. The GitHub provider sample code references 8 kHz or 16 kHz mono, Linear16 or G.711 u-law for media forking integrations, but the specific codec used by Start Media Stream is not confirmed.

### Stop Media Stream

> **Documentation pending** — The Cisco help docs reference a separate Stop Media Stream activity that ends the stream. However, Stop Media Stream does not appear in the Flow Designer activity registry (as of 2026-05-07). It is possible that stopping the stream is handled implicitly (e.g., on call disconnect or transfer) or that the activity is available only when the `media-forking-activity` feature flag is enabled. Wire a Stop Media Stream activity (if available in your environment) when the call should stop sending audio to the external service — e.g., before transfer, on disconnect, or when switching flow phases.

### Wiring Pattern

The recommended wiring pattern places Start Media Stream in the **Event flow** after the `AgentAnswered` event, controlled by a boolean global variable:

```
Main Flow:
  Set Variable (Global_MediaStreamEnabled = true) → Queue Contact

Event Flow (AgentAnswered):
  Condition: {{Global_MediaStreamEnabled}} == true
    ├── TRUE → Start Media Stream (Media Destination: Cisco AI Assistant)
    │            └── Failure path → (error handling)
    └── FALSE → (no streaming)
```

### Use Cases

- **Real-time transcription:** Stream call audio to a speech-to-text service for live captioning on the agent desktop
- **Sentiment analysis:** Feed audio to an AI service that scores caller sentiment in real time and surfaces alerts to the agent
- **Compliance monitoring:** Stream to a service that detects compliance keywords or phrases during the call
- **AI Agent Assist:** Feed audio to Cisco AI Assistant for suggested responses and call summarization

### Restrictions

- Available only for **Next Generation media platform** (RTMS) customers.
- Does **not** work on the consult leg (e.g., during consult calls or consult transfers).
- Media streams consume additional bandwidth. Monitor stream health and latency in production.
- The Media Destination must be configured in Control Hub before it appears in the dropdown.
- Self-loop limit: **20**

---

