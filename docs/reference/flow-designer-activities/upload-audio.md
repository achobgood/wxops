## Upload Audio Activity

<!-- ref-tag: fd-act-upload-audio-v1 -->

Uploads an audio file during flow execution. Currently supports uploading agent personal greetings — used with the Record activity to let agents record and store custom greetings via an IVR flow. Once uploaded, recorded files and their assigned attributes appear in Control Hub.

### Configuration

**General Settings:**

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | Optional description |

**Audio File Information:**

| Field | Type | Required | Description |
|---|---|---|---|
| Audio File Type | Select dropdown | Yes | Currently the only option is **Agent Personal Greeting** (value: `agent_greeting`). Determines the category of audio file being uploaded. |
| Greeting Purpose | Text input | Yes | The greeting purpose name used for creating the agent greeting. Enter static text or dynamic variables enclosed in `{{ }}`. Greeting purposes are defined by administrators in Control Hub under the Agent Personal Greeting section. **Validation:** up to 80 alphanumeric characters; hyphens (`-`) and underscores (`_`) allowed; no spaces. |
| Recording Data | Variable select (JSON) | Yes | Select a flow variable of type **JSON** that points to the recorded audio file. Typically the `audioFileData` output from a preceding Record activity — e.g., `{{Record.audioFileData}}`. |
| Agent ID | Variable select (String) | Yes | Select a flow variable of type **String** that yields the unique user ID of the agent. The agent ID is the unique user ID assigned to each Contact Center user in Control Hub. |

### Output Variables

| Variable | Type | Description |
|---|---|---|
| `UploadAudio.status` | String | Status of the upload — `"success"` or `"failure"` |

### Output Paths

**Non-terminal node.** The activity has one output edge and one error path.

| Path | Condition | Description |
|---|---|---|
| (default) | `status == "success"` | Upload completed successfully — flow continues to the next wired activity |
| **Undefined Error** | `status == "failure"` | Upload failed — wire to error handling (Play Message with error notification, retry, or Disconnect) |

### Audio File Requirements

Audio files uploaded through this activity must meet the standard Webex Contact Center audio requirements:

| Requirement | Value |
|---|---|
| Format | WAV |
| Channel | Mono |
| Sample rate | 8 kHz |
| Encoding | 8-bit u-law |
| Max file size | 5 MB |

### Wiring Pattern with Record Activity

The Upload Audio activity is designed to work with the Record activity in an IVR self-service flow that lets agents record and store personal greetings:

```
Collect Digits (agent extension) → Set Variable (agentUserId from lookup)
  → Play Message ("Please record your greeting after the beep")
  → Record (max 30s, termination: #)
    ├── (success) → Upload Audio (Audio File Type: Agent Personal Greeting,
    │                 Greeting Purpose: "welcome", Recording Data: {{Record.audioFileData}},
    │                 Agent ID: {{agentUserId}})
    │                 ├── (success) → Play Message ("Greeting saved") → Disconnect
    │                 └── (error) → Play Message ("Upload failed") → Disconnect
    └── (error) → Play Message ("Recording failed") → Disconnect
```

### Greeting Purpose Configuration

Greeting purposes are created by administrators at the tenant level in Control Hub (Contact Center > Agent Personal Greeting). Each purpose specifies the category or intent behind an agent greeting (e.g., "welcome", "hold", "callback"). The greeting purpose name entered in this activity must match a purpose defined in Control Hub.

In the flow, the greeting is played via the **Set Announcement** activity with the **Enable Agent Greeting** toggle turned on and the matching greeting purpose name configured.

### Restrictions

- Requires an active **IVR session** — the activity is designed for voice call flows.
- Audio File Type is limited to **Agent Personal Greeting** only (no other audio file types are currently supported).
- The agent's Desktop Profile must have the **Personal Greeting** toggle enabled for the greeting to play.
- Self-loop limit: **3**
- Greeting Purpose validation: max 80 characters, alphanumeric plus hyphens and underscores only, no spaces.

---

