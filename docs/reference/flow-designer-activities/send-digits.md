## Send Digits Activity

<!-- ref-tag: fd-act-send-digits-v1 -->

Sends DTMF tones during an active call. Use it to navigate external IVR systems after a transfer or to transmit authentication codes.

### Configuration

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | Optional description |
| Digits | The digit string to send. **Set Value** (static) or **Set to Variable** (dynamic). Maximum **32 characters**. Supported: 0–9, A–D, *, #, comma. Comma (,) inserts a 1-second delay. |

### Output Variables

No activity-specific output variables. The live registry exposes only a generic `status` output, which is undocumented. [source: wxcc-flow describe send-digits → outputs: status; flow-designer-flowir.md § 8]

### Output Paths

Default success exit, plus a **Failure** output path (registry `failure` port, `isErrorPath: true`) that fires on system errors during flow execution. (Live registry: wxcc-flow describe send-digits (today `wxcli cc-flow show-activity PROJECT_ID send-digits`) → `outputPorts` includes a `failure` port, verified 2026-07-12.)

### Use Cases

- **IVR navigation after transfer:** After a Bridged Transfer connects, send DTMF digits to navigate the destination's IVR menu (e.g., `1,,2` to press 1, wait 2 seconds, then press 2)
- **PIN entry:** Send an authentication PIN to an external system during a transfer
- **Extension dialing:** Dial an extension after connecting to a PBX main number

### Restrictions

- Can only be used during the first caller leg to the IVR. Ignored if used within a consult interaction or transfer to entry point.

---

