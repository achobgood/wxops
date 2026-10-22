## GoTo Activity

<!-- ref-tag: fd-act-goto-v1 -->

Transfers the call to a different flow or entry point. GoTo is a **terminal node** — the current flow ends and the destination flow takes over. There are two variants:

> **Feature flag:** If the activity library does not display the GoTo activity, contact Cisco Support to have the corresponding feature flag enabled.

### Go To Flow

Transfers to another published flow within the same organization.

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | Optional description |
| Destination Flow | **Static Flow:** Select a flow from the list of pre-configured flows. **Dynamic Flow:** Choose a variable that maps to a valid Flow ID (locate the Flow ID in Flow Settings under the General Settings pane). |

### Go To Entry Point

Transfers to a different Entry Point, which triggers that Entry Point's assigned flow.

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | Optional description |
| Destination Entry Point | **Static Entry Point:** Choose an entry point from the list of pre-configured entry points. **Dynamic Entry Point:** Choose a variable that maps to a valid entry point ID from Control Hub. Only entry points of the same channel type are valid. |

### Dynamic Selection

Both variants support flow variables in the destination field (see Dynamic Variables in Activities). The variable must resolve to a valid flow ID or Entry Point ID at runtime.

### Variable Mapping (Go To Flow only)

When using a **static** destination flow, you can map variables from the current flow to the destination flow:

| Field | Description |
|---|---|
| Map Current Variables | Select flow or global variables from the current flow |
| To Destination Variable | Select the corresponding variable in the destination flow |

- Variables with the same name and data type are mapped automatically for inbound calls
- For outbound calls, only global variables are mapped automatically
- Source variables can map to multiple destinations; destination variables can only receive one mapping
- Variable mapping is **not available** when using a dynamic (variable) flow destination

> **JSON variable mapping note:** When you map a JSON variable from a main flow to the target flow in GoTo activity, store the JSON output in another variable such as a string or any other variable type, and map that to the same type of variable in the target flow.

### Output Paths

GoTo is a **terminal node** — there are no success output edges. The current flow ends and the destination flow takes over. However, GoTo does expose an error-handling path:

| Output Path | Fires When |
|---|---|
| *(none — terminal)* | GoTo succeeds — the call transfers to the destination flow or entry point. No output edge; the current flow ends. |
| **Undefined Error** | System error during the GoTo transfer (e.g., destination flow not found, invalid flow ID, deleted entry point, runtime resolution failure for a dynamic variable). Wire to a Play Message (error notification) then Disconnect Contact or a fallback queue. If no Undefined Error path is configured, the flow falls back to the `OnGlobalError` event handler. |

### Output Variables (Error Codes)

| Variable | Description |
|---|---|
| `FailureCode` | Stores the failure code. The system sets this value only when the activity fails. |
| `FailureDescription` | Stores the failure details. The system sets this value only when the activity fails. |

### Failure Codes

> **Documentation pending** — the specific `FailureCode` values for GoTo are not enumerated in the Cisco help docs. The `FailureCode` and `FailureDescription` output variables are populated only when the activity fails (Undefined Error path). Wire the Undefined Error path to a Play Message that references `{{GoTo.FailureDescription}}` so the error is visible during testing, and log the code via a Set Variable or HTTP Request for debugging.

### View Selected Flow

When using Go To Flow, you can view the destination flow in a separate tab. Click the **View** option while selecting a flow from the list, or click **View Selected Flow** after selecting a flow in the GoTo Flow option.

### Dynamic Destination Variable Mapping

When using a dynamic (variable) flow destination, manual variable mapping is not available. However, Agent Viewable flow variables and Global Variables are still mapped automatically between the current flow and the destination flow.

### Restrictions

- GoTo is a terminal node — no output edges. The call does not return to the calling flow.
- Use GoTo to chain flows for modular IVR designs (e.g., a shared front-door flow that routes to product-specific flows).
- Only telephony entry points created in Webex Control Hub are displayed in the Go To Entry Point dropdown. Only entry points of the same channel type are valid.

### Known Issues with Flow Chaining

- The system prevents you from deleting an entry point that participates in flow chaining. Delete all associated resources (queues and flows) before removing the entry point.
- The system prevents you from deleting a flow that participates in flow chaining. Remove every flow-chaining reference before deleting the flow.
- Force-deleting an entry point or flow in flow chaining skips validation and shows no error messages in the user interface.

---

