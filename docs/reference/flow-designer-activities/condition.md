## Condition

<!-- ref-tag: fd-act-condition-v1 -->

The Condition activity represents a decision. The flow takes the True or False path depending on whether the condition is met. You can configure an error-handling path (Undefined Error) to handle system errors that may occur during flow execution.

### Configuration

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | Optional description |
| Expression | Enter an expression using `{{}}` syntax to evaluate. The flow follows the True path when the expression evaluates to true, and the False path otherwise. |

### Output Paths

| Output Path | Fires When |
|---|---|
| **True** | Expression evaluates to true |
| **False** | Expression evaluates to false |
| **Undefined Error** | System error during expression evaluation |

### Output Variables

No activity-specific output variables. The Condition activity is a pure logic gate — it routes the flow based on the expression result but does not produce any output variables for downstream activities to consume.

### Error Handling

No enumerated failure codes. The Condition activity does not expose `FailureCode` or `FailureDescription` output variables.

The only documented error behavior is a **Flow Validation Error** (not a runtime error code): if you use an expression without double curly braces `{{ }}`, the system throws a Flow Error at validation time. Always wrap expressions as `{{Enter Expression}}`.

### Expression Syntax

Allowed operators: `==`, `!=`, `<`, `>`, `<=`, `>=`, `+`, `-`, `*`, `/`

Variables use double curly brace syntax: `{{variableName}}`

### Limitations (confirmed from testing)

| What | Works? | Notes |
|---|---|---|
| Numeric comparison | Yes | `{{VerifiedCount}} > 0` |
| String equality | Yes | `{{variable}} == "value"` |
| Compare to empty string `""` | **No** | Expression validator rejects `{{variable}} == ""` — the quotes collide with expression syntax |
| `!=` operator | **Unreliable** | Listed as allowed but may not validate in all contexts |
| String functions | **No** | Not available — use numeric comparisons instead |

### Recommended Patterns

| Check | Expression | TRUE Branch | FALSE Branch |
|---|---|---|---|
| Has a value (numeric) | `{{count > 0}}` | Has value | Empty/zero |
| Equals specific value | `{{status == 200}}` | Match | No match |
| Digit pressed | `{{CollectDigit.DigitsEntered == 1}}` | Pressed 1 | Other |
| Counter threshold | `{{noInputCount >= 3}}` | Threshold reached | Keep going |

**Operator placement:** The operator and comparison value go **inside** the double braces — `{{variable > 0}}` not `{{variable}} > 0`.

### Workaround for Empty Checks

Instead of checking if a string variable is empty, use a numeric field from the API response. For example, use `$.meta.resultCount` from CJDS instead of checking if a parsed string ID is empty:

- **Avoid:** `{{EventId == ""}}` (won't validate — empty string comparison unsupported)
- **Use:** `{{ResultCount > 0}}` (clean numeric check)

---

