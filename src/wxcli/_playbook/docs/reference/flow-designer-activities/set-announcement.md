## Set Announcement Activity

<!-- ref-tag: fd-act-set-announcement-v1 -->

Configures announcements that play during call handling — including compliance messages, agent greetings, and whisper announcements. This is a combined configuration point for multiple announcement types.

### Configuration

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | Optional description |
| Enable Agent Greeting | Toggle. When enabled, plays a personal agent greeting to the caller when the agent answers. |
| Greeting Purpose | Name of the greeting purpose (when Agent Greeting is enabled) |
| Enable Compliance Message | Toggle. When enabled, plays a compliance/legal message (e.g., "This call may be recorded") |
| Audio File | Select the audio file for the compliance message |

### Announcement Types

The Set Announcement activity can configure three announcement types in a single node:

1. **Compliance message** — plays to both parties (e.g., recording disclosure)
2. **Agent greeting** — agent's personal greeting plays to the caller
3. **Whisper announcement** — plays to the agent only. Whisper is **not configured on this activity**; drag the separate **Set Whisper Announcement** activity onto the flow canvas to configure whisper announcements.

### Output Variables

No activity-specific output variables. The live registry exposes only a generic `status` output, which is undocumented. [source: wxcc-flow describe set-announcement → outputs: status; flow-designer-flowir.md § 8]

### Failure Codes

No failure codes are documented for this activity.

### Output Paths

| Output Path | Fires When |
|---|---|
| *(default exit)* | The announcement configuration is applied successfully — wire to the next activity |
| **Undefined Error** | System error while applying the announcement configuration |

If the Undefined Error path is not configured, the flow falls back to the global `OnGlobalError` event handler. [source: wxcc-flow describe set-announcement → outputPorts: error (isErrorPath); flow-designer-flowir.md § 8 Activity Registry]

### Placement

- **Inbound flows:** Configure before Queue Contact or within the PreDial event flow
- **Outbound flows:** Must be configured within the PreDial event flow, with Set Caller ID as the terminal activity

---

