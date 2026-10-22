## Collect Digits Activity

<!-- ref-tag: fd-act-collect-digits-v1 -->

Collects DTMF input from the caller for authentication, data entry, or menu navigation.

This activity accepts DTMF input digits from 0 through 9 and alphabets A, B, C, and D. The caller can enter # or * as a termination symbol to indicate the end of DTMF input. The caller cannot use the termination symbols for any other scenarios as part of the Collect Digits activity such as confirming the amount or customer ID.

By default, Next Generation media platform supports only RFC2833 type DTMF for both inbound and outbound calls. Next Generation media platform supports in-band DTMF (this feature is available only if the corresponding feature flag is enabled). You can also hear in-band DTMF tones during recording and in conference with other parties.

### Configuration

**General Settings:**

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | Optional description |

**Prompt Settings:**

Same prompt builder as Play Message — supports Add Audio File, Add Text-to-Speech Message, and Add Audio Prompt Variable.

| Field | Description |
|---|---|
| Make Prompt Interruptible | When enabled, callers can begin entering digits before the prompt finishes |

**TTS Settings (when Text-to-Speech is enabled):**

| Field | Default | Range | Description |
|---|---|---|---|
| Connector | — | — | TTS connector selection — dictates the language, gender, and tone for speech. Existing customers on Next Gen voice platform can view both Cisco Cloud TTS and Google TTS connectors. |
| Override Default Language & Voice Settings | Enabled | On/Off | Override the voice settings configured in the `Global_VoiceName` variable for this activity |
| Output Voice | — | — | Voice selection (appears when override is enabled). If the desired voice is not in the dropdown, disable the override and use a Set Variable activity before Collect Digits to set `Global_VoiceName`. |
| Speaking Rate | 1.0 wpm | 0.25–4.0 wpm | Speed of speech |
| Volume Gain | 0.0 dB | -96.0–16.0 dB | Loudness adjustment |

**Important TTS considerations:**
- Use single quotes instead of double quotes inside pebble expressions.
- There is no character limit for Cisco Text-to-Speech messages.

**Advanced Settings:**

| Field | Default | Range | Description |
|---|---|---|---|
| No-Input Timeout | 3 seconds | 1–30 seconds | Time to wait for the first digit before triggering no-input handling |
| Inter-digit Timeout | 3 seconds | 0–30 seconds | Time to wait between digits before accepting the input |
| Minimum Digits | 1 | 1–20 | Minimum number of digits required |
| Maximum Digits | 10 | 1–20 | Maximum number of digits accepted |
| Terminator Symbol | # | # / * | Character the caller can enter to specify the end of input, either # or * depending on the configuration |

### Output Variables

| Variable | Description |
|---|---|
| `CollectDigits.DigitsEntered` | DTMF digits entered by the caller |
| `CollectDigits.FailureCode` | Error code on failure |
| `CollectDigits.FailureDescription` | Error description on failure |

### Output Paths

| Output Path | Fires When |
|---|---|
| **Success** | Valid digits collected within timeouts and digit count constraints |
| **Entry Timeout** | No-input timeout elapsed without receiving any digits |
| **Unmatched Entry** | Input received but did not match expected criteria (e.g., fewer digits than Minimum Digits before terminator or inter-digit timeout) |
| **Undefined Error** | System error during digit collection. If no Undefined Error path is configured, the flow falls back to the `OnGlobalError` event handler in the Event Flows tab. |

### Failure Codes

> **Documentation pending** — the specific `FailureCode` values for Collect Digits are not enumerated in the Cisco help docs. The `CollectDigits.FailureCode` and `CollectDigits.FailureDescription` output variables are populated only when the activity fails (Undefined Error path). The output path itself (Entry Timeout, Unmatched Entry) indicates the failure type for non-system errors.

### Restrictions

- **DTMF type support:** By default, Next Generation media platform supports only RFC2833 type DTMF for both inbound and outbound calls. In-band DTMF support requires a feature flag to be enabled.
- **Termination symbols are reserved:** The caller cannot use `#` or `*` as data input — these characters function only as termination symbols to signal end of input, depending on the configured Terminator Symbol.
- **Digit range:** Accepts DTMF digits `0` through `9` and alphabets `A`, `B`, `C`, and `D` only.
- **Digit count limits:** Minimum Digits range is 1–20; Maximum Digits range is 1–20. Maximum Digits must be >= Minimum Digits.
- **Self-loop limit:** 100 iterations before the system forces an error exit.

---

