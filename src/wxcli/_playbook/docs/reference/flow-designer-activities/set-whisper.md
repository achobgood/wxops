## Set Whisper Announcement Activity

<!-- ref-tag: fd-act-set-whisper-v1 -->

Plays a short audio announcement to the **agent only** before connecting the caller. The caller does not hear the whisper.

### Configuration

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | Optional description |

**Prompt (supports both audio files and TTS):**

| Field | Description |
|---|---|
| Enable Text-to-Speech | Toggle. When enabled, adds TTS options below. |
| Connector | TTS connector (Cisco Cloud TTS or Google TTS) |
| Override Default Language & Voice Settings | Toggle (default: enabled). Override flow-level language/voice for this whisper. |
| Output Voice | Voice selection (when override is enabled) |
| Add Audio File | Select a pre-uploaded audio file |
| Add Text-to-Speech Message | Enter text for TTS synthesis |
| Add Audio Variable | Select a flow variable resolving to an audio file |

### Placement

Wire the Set Whisper Announcement activity **after Queue Contact** and before the agent connection. When an agent is offered the call, they hear the whisper announcement before being connected to the caller. Applicable to incoming calls and blind transfer to Entry Point.

### Restrictions

When a whisper plays, you cannot:
- Put the call on hold, transfer, or conference
- Request supervisor assistance

These features become available again after the announcement completes.

A whisper announcement:
- Is applicable to incoming calls and blind transfer to EP
- Can be a prompt or text-to-speech (TTS) string
- Can be combined with compliance message and agent greeting, in which case the whisper plays first
- Is not included in the call recording
- Supports all agent endpoint types: phone, soft client, and WebRTC

### Output Variables

This activity has no output variables.

### Output Paths

Single default (success) exit. You can configure an error-handling path (**Undefined Error**) to handle system errors during flow execution.

### Failure Codes

No failure codes are documented for this activity.

### Use Cases

- **Queue identification:** "This call is from the Sales queue" — tells the agent which queue the call came from.
- **Topic context:** "Caller is asking about order returns" — gives the agent context from IVR data collection.
- **Priority flag:** "This is a VIP caller" — alerts the agent to high-priority interactions.

---

