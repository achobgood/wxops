## Recording Control Activity

<!-- ref-tag: fd-act-recording-control-v1 -->

Controls call recording during an interaction by toggling recording on or off based on a flow variable that captures user consent.

### Configuration

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | Optional description |
| Enable Recording | Select a flow variable from the dropdown that controls whether recording is enabled or disabled |

### Output Variables

Verified via the live registry (wxcc-flow describe RecordingControl (today `wxcli cc-flow show-activity PROJECT_ID RecordingControl`), 2026-07-12):

| Variable | Description |
|---|---|
| `RecordingControl.FailureCode` | Failure code, set only when the activity fails |
| `RecordingControl.FailureDescription` | Detailed failure description, set only when the activity fails |
| `RecordingControl.status` | Status of the activity |

### Output Paths

Default success exit, plus a **Failure** output path (registry `failure` port, `isErrorPath: true`). On failure the flow takes the Failure edge and populates the `FailureCode`/`FailureDescription` output variables. (Live registry: wxcc-flow describe RecordingControl (today `wxcli cc-flow show-activity PROJECT_ID RecordingControl`) → `outputPorts` includes a `failure` port, verified 2026-07-12.)

**Consent priority:** The Recording Control activity interacts with recording settings at three levels — tenant, queue, and user consent. The priority order:
1. If user consent = Yes → recording is enabled regardless of tenant/queue settings
2. If user consent = No → recording is disabled regardless of tenant/queue settings
3. If user consent is not configured → tenant and queue level settings determine recording behavior
4. If none of the three levels are configured → recording defaults to disabled

### Restrictions

- **Consent capture pattern:** Use a Menu activity upstream to capture the caller's consent into a Boolean flow variable, then assign that variable as input to the Recording Control activity's Enable Recording field. The activity is designed to work in tandem with a Menu for this purpose.
- **Reporting:** If you need to report the user's consent value in an Analyzer consent report, store the consent value in a reportable global variable. A local variable can be used if reporting is not required.
- **Self-loop limit:** 10 (see [self-loop-limits.md](self-loop-limits.md)).
- **Next Generation platform restriction:** Not documented. Unlike the Record activity (which explicitly requires the Next Generation media platform), Cisco documentation does not state a platform restriction for Recording Control. Documentation pending — verify with your tenant if in doubt.
- **Event flow eligibility:** Not documented. Cisco documentation does not explicitly state whether Recording Control can be placed in event flows. Use in the main flow canvas where the consent Menu activity precedes it.

---

