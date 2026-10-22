## Record Activity

<!-- ref-tag: fd-act-record-v1 -->

Records caller audio (voicemail messages, verbal confirmations, or compliance recordings).

### Configuration

**General Settings:**

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | Optional description |

**Record Settings:**

| Field | Default | Range | Description |
|---|---|---|---|
| Start Beep | Enabled | On/Off | Plays an audible beep before recording begins to signal the caller |
| Silence Timeout | 4 seconds | 1–120 seconds | Seconds of silence before the recording automatically stops |
| Maximum Recording Duration | 30 seconds | 1–120 seconds | Maximum length of the recording |
| Termination Symbol | # | # / * | Character the caller presses to stop recording |

### Output Variables

| Variable | Description |
|---|---|
| `Record_audioFileData` | Details of the recorded audio file. Access sub-fields via Pebble: `{{Record_label.audioFileData.name}}` |
| `Record_errorCode` | Error status code on failure |
| `Record_errorDescription` | Error description on failure |

### Output Paths

| Output Path | Fires When |
|---|---|
| *(default exit)* | Recording completes successfully — the caller spoke and the audio was captured. The `Record_audioFileData` variable is populated. Wire to the next activity (e.g., Upload Audio, Play Message confirmation, or Disconnect Contact). |
| **No Input Timeout** | Trigger semantics not documented. The live registry lists this as a distinct error output port on the Record activity, separate from Undefined Error (wxcc-flow describe record (today `wxcli cc-flow show-activity PROJECT_ID record`) → `outputPorts`: `noInputTimeout`, `undefinedErrors`; flow-designer-flowir.md § 8). |
| **Undefined Error** | System error during recording (e.g., media services failure, feature not enabled, API error, or no audio input detected). The `Record_errorCode` and `Record_errorDescription` variables are populated with the specific failure code. If no Undefined Error path is configured, the flow falls back to the `OnGlobalError` event handler. |

> **Wiring pattern:** See the [Upload Audio](upload-audio.md) activity for a complete Record → Upload Audio wiring example. The Record default exit feeds into Upload Audio, and the Undefined Error path feeds into a Play Message ("Recording failed") → Disconnect Contact.

### Failure Codes

| Code | Description |
|---|---|
| 1001 | INVALID_SILENCE_TIMEOUT — timeout not between 1–120 seconds |
| 1002 | INVALID_MAXIMUM_RECORDING_DURATION — record time not between 1–120 seconds |
| 1003 | INVALID_TERMINATION_SYMBOL — not * or # |
| 1004 | RECORD_API_FAILURE — API error initiating recording |
| 1005 | FEATURE_DISABLED_FOR_ORG — feature not enabled for organization |
| 1006 | No input audio detected |
| 1007 | Media services error during recording |

### Restrictions

- Available only for Next Generation media platform customers.
- Audio files are unencrypted and automatically deleted after call completion.

---

