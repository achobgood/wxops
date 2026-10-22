## Menu Activity

<!-- ref-tag: fd-act-menu-v1 -->

Plays a prompt and routes the call based on the caller's DTMF selection. Each digit maps to a separate output path.

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
| Make Prompt Interruptible | When enabled, callers can press a digit before the prompt finishes |

**Custom Menu Links:**

Each menu option maps a single digit (0–9) to an output path. You can configure up to ten custom menu links.

| Field | Description |
|---|---|
| DIGIT | Dropdown list of digits 0–9. Corresponds to the DTMF input the caller enters to indicate which path of the flow to follow. Each digit can be selected only once. |
| LINK DESCRIPTION | Text describing what path of the flow the digit corresponds to (e.g., "Sales"). Has no impact on the call itself, but helps track how the Menu is constructed. |
| Add New | Click to add more menu links. You can add a digit and link description for each row, up to 10 links. |

You can configure menu links in both the Properties pane and in the activity itself. The system updates the content in real-time in both locations when an edit is made.

**TTS Settings (when Text-to-Speech is enabled):**

| Field | Default | Range | Description |
|---|---|---|---|
| Speaking Rate | 1.0 wpm | 0.25–4.0 wpm | Speed of speech |
| Volume Gain | 0.0 dB | -96.0–16.0 dB | Loudness adjustment |

**Advanced Settings:**

| Field | Default | Range | Description |
|---|---|---|---|
| No-Input Timeout | 3 seconds | 1–30 seconds | Time to wait for DTMF input before triggering the No-Input Timeout output path |

> **No built-in retry settings.** Unlike some other DTMF activities, the Menu activity does **not** expose Max No-Input Retries, Max Unmatched Entries, or Inter-digit Timeout fields in its Advanced Settings. Retry logic must be implemented manually in the flow using a Set Variable counter and a Condition node that loops back to the Menu activity. See the "Configure Counter in Menu Block" Cisco support article for the recommended pattern: increment a counter variable on each No-Input Timeout or Unmatched Entry, then use a Condition to check whether the counter exceeds your retry limit before looping back or disconnecting.

### Output Variables

| Variable | Description |
|---|---|
| `Menu.OptionEntered` | Menu option selected (single digit 0–9) |

The Cisco help docs do not document `FailureCode` or `FailureDescription` output variables for Menu.

### Output Paths

| Output Path | Fires When |
|---|---|
| **Per-digit branches** | One output edge per configured digit (0–9). Maximum **10 branches**. |
| **Extra registry ports** (`#`, `*`) | Beyond digits 0–9, the activity registry also exposes `#` and `*` output ports (`flow-designer-flowir.md` § 8 Activity Registry — the round-trip-tested wxcc-flow describe ivr-menu (today `wxcli cc-flow show-activity PROJECT_ID ivr-menu`) port list is `0`–`9`, `#`, `*`, `timeout`, `invalid`, `error`). Whether the UI Custom Menu Links dropdown offers `#`/`*` as selectable menu-link values, and the exact trigger semantics of these two ports, are **not documented / not verified**. |
| **No-Input Timeout** | No-Input Timeout duration elapsed without receiving any DTMF input. Wire this to a counter-increment + Condition loop to implement retry behavior (see Advanced Settings note above). |
| **Unmatched Entry** | Caller pressed a DTMF digit not configured in the Custom Menu Links section. Wire this to a clarification prompt and loop back to the Menu activity to let the caller try again. |
| **Undefined Error** | System error during Menu execution. The live activity registry (wxcc-flow describe ivr-menu (today `wxcli cc-flow show-activity PROJECT_ID ivr-menu`), 2026-07-11) exposes an `error` output port (`isErrorPath: true`); its exact trigger semantics are not documented. |

> **Note:** The No-Input Timeout and Unmatched Entry paths fire on each individual occurrence — there is no built-in retry exhaustion. The flow designer must implement retry counting externally (Set Variable + Condition) to limit retries and eventually disconnect or transfer the call.

### Failure Codes

> **Documentation pending** — the Cisco help docs do not enumerate failure codes for the Menu activity. The activity does not expose `FailureCode` or `FailureDescription` output variables. The live activity registry (wxcc-flow describe ivr-menu (today `wxcli cc-flow show-activity PROJECT_ID ivr-menu`), 2026-07-11) shows the Menu activity DOES have an activity-level `error` output port (`isErrorPath: true`) — its trigger semantics are not documented; if that port is not wired, errors during Menu execution (e.g., prompt file unavailable) fall back to the `OnGlobalError` event handler.

### Error Handling

The live activity registry (wxcc-flow describe ivr-menu (today `wxcli cc-flow show-activity PROJECT_ID ivr-menu`), 2026-07-11) shows the Menu activity DOES expose a dedicated `error` output path (`isErrorPath: true`), like HTTP Request, Parse, and Queue Contact. Its exact trigger semantics are not documented. If the `error` path is not wired, a system error during Menu execution falls back to the `OnGlobalError` event handler in the Event Flows tab.

For caller-facing error scenarios:
- **No input:** Wire the No-Input Timeout path to a Play Message ("We didn't receive your selection") → Set Variable (increment counter) → Condition (counter < max) → loop back to Menu or disconnect.
- **Wrong digit:** Wire the Unmatched Entry path to a Play Message ("That wasn't a valid option") → Set Variable (increment counter) → Condition (counter < max) → loop back to Menu or disconnect.

### Restrictions

> **Documentation pending** — the Cisco help docs do not enumerate specific restrictions for the Menu activity. The following are confirmed from documented behavior:

- Maximum **10 custom menu links** (digits 0–9); each digit can be mapped only once.
- The activity only accepts single-digit DTMF input (0–9). For multi-digit collection, use Collect Digits instead.
- No built-in retry mechanism — retry logic must be implemented manually in the flow (see Advanced Settings note above).
- The Menu activity is a **voice-only** activity — it appears in the Activity Library under the Voice group and is not available for digital channel flows.

---

