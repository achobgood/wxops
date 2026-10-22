## Percentage Allocation Activity

<!-- ref-tag: fd-act-percentage-allocation-v1 -->

Splits traffic across multiple flow branches using weighted round-robin distribution. Use for A/B testing, gradual rollouts, and comparing different CX approaches on live traffic.

> Full configuration walkthrough, use case matrix, wiring patterns, and Analyzer integration: [flow-designer-patterns.md § Percentage Allocation](../flow-designer-patterns.md#percentage-allocation).

### Configuration

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | Optional description |
| Output Paths | 2 to 10 branches; click **Add New** to add paths |
| Percentage Weight | Integer percentage for each path; all weights must sum to exactly 100 |
| Path Description | Optional description for each output path |

Drag **Percentage Allocation** from the Activity Library onto the canvas, add output paths, assign percentage weights, and wire each output to the desired downstream activity.

### Distribution Algorithm

Uses **Weighted Round Robin (WRR)**, not random sampling. Over sufficient volume, actual distribution converges to configured percentages. Small sample sizes may show variance. The algorithm resets every time you publish the flow. [source: flow-designer-patterns.md § WRR Distribution Behavior]

### Output Variables

| Variable | Type | Description |
|---|---|---|
| `Percentallocation.percentage` | STRING | The percentage route selected for the current contact. The live registry types this `STRING` (wxcc-flow describe percent-allocation (today `wxcli cc-flow show-activity PROJECT_ID percent-allocation`) → `percentage`: STRING, "Next Percentage Route"; flow-designer-flowir.md § 8) |
| `Percentallocation.description` | STRING | The description of the selected path |

[source: flow-designer-patterns.md § Output Variables]

### Output Paths

| Output Path | Fires When |
|---|---|
| **Path 1 … Path N** | One output edge per configured path — the WRR algorithm selects the path for the current contact |
| **Undefined Error** | System error during evaluation |

### Error Handling

The Percentage Allocation activity does not expose `FailureCode` or `FailureDescription` output variables. The only error path is the **Undefined Error** edge. If Undefined Error is not wired, the flow falls back to the global `OnGlobalError` event handler.

### Restrictions

- Minimum **2** output paths, maximum **10**
- Weights must be **integers** that sum to exactly **100**
- Percentage values range from **0%** to **100%** — the 0% setting creates switchboard use cases (traffic off by default, activate later by changing to >0%)
- No built-in session affinity — a returning caller may take a different path on the next call
- **Surge limits:** Percentage Allocation is a flow-control activity and is subject to system-configured surge limits (separate from per-activity self-loop limits) to ensure stability and prevent infinite looping. See [self-loop-limits.md](self-loop-limits.md) for details.

### Common Patterns

- **A/B testing:** Split traffic between existing and experimental IVR to compare metrics
- **Gradual rollout:** Start at 90/10, shift to 70/30 → 50/50 → 100/0 as confidence grows
- **Multi-path comparison:** 40/30/30 across DTMF IVR, TTS IVR, and conversational bot
- **Switchboard:** Set unused paths to 0% and activate later without re-publishing

---

