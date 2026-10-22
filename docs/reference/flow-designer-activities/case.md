## Case Activity

<!-- ref-tag: fd-act-case-v1 -->

Branches the flow based on a variable's value — equivalent to a switch/case statement. Use it when a single variable can take multiple known values that each require different handling.

### Configuration

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | Optional description |
| Variable | Choose a variable against which you want to evaluate the different cases |
| Expression | Enter an expression to evaluate the different cases against, using Pebble Template syntax |

The Case activity accepts both a **Variable** (dropdown selection) and an **Expression** (Pebble template) as evaluation input. Use Variable when matching against a single flow variable's value; use Expression for more complex evaluations.

**Adding Cases:**

Click **Add New** to add case statement blocks. Each case specifies a value to match against the variable using Pebble Template Syntax. When the variable equals the case value, the flow takes that branch's output path. Maximum **20 case statements** per activity.

A **Default** branch handles all values that don't match any defined case. The Default branch cannot be removed.

### Output Paths

| Output Path | Fires When |
|---|---|
| **Case 1 … Case N** | One output edge per configured case — fires when the variable/expression matches that case's value |
| **Default** | No configured case matched the variable's value (cannot be removed) |
| **Undefined Error** | System error during expression evaluation (e.g., malformed Pebble expression) |

Wire each case edge and the Default edge to the appropriate downstream activity. If no Undefined Error path is configured, the flow uses the `OnGlobalError` event handler.

### Output Variables

No activity-specific output variables. The Case activity is a pure branching node — it routes the flow based on matching the variable/expression value but does not produce output variables for downstream activities to consume.

### Error Handling

The Case activity does not expose `FailureCode` or `FailureDescription` output variables. The only error path is the **Undefined Error** edge, which fires on system errors during evaluation. If Undefined Error is not wired, the flow falls back to the global `OnGlobalError` event handler.

### Restrictions

- Maximum **20 case statements** per Case activity
- Pebble expressions in case values must be on a **single line** — carriage returns inside the expression will cause a runtime failure even if the expression tester validates successfully
- The **Default** branch cannot be removed
- Matching is **string-based** — the variable's value is compared to each case value as a string

> **Documentation pending** — case sensitivity behavior (whether matching is case-sensitive or case-insensitive) and behavior when the evaluated variable is null/empty are not verified against Cisco help docs. Test in your environment before relying on either assumption.

### Common Patterns

- **Multi-intent routing:** Branch on `VirtualAgentV2.StateEventName` to route different Custom Events to different HTTP Request activities
- **DNIS-based routing:** Branch on `NewContact.DNIS` to route calls to different queues per dialed number
- **HTTP status handling:** Branch on `httpStatusCode` (200, 400, 401, 404, 429, 500) to handle each response code differently
- **Intent-based queue routing:** Branch on `previousIntent` parsed from `VirtualAgentV2.MetaData` to escalate to different queues per intent

---

