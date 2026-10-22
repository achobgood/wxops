# Functions Setup

<!-- ref-tag: functions-setup-v2 -->

This playbook owns the **sequence** -- create, test, publish, use in a flow -- and the judgment about when to reach for a Function at all. The values it reproduces are owned elsewhere and annotated inline:

| Owner | Owns |
|---|---|
| `docs/reference/flow-designer-activities/functions-activity.md` | The Flow Designer activity: input/output wiring, output paths, limits, the Functions-vs-other-options table |
| `docs/reference/custom-functions.md` | The API layer: `/v1/{orgId}/functions` endpoints, the `handle` contract, definition fields, runtimes, dataTypes, tags, lifecycle, the `wxcli cc-functions` commands |

## When to Use Functions

**Try Functions first.** When a voice flow needs complex data transformation (date formatting, string manipulation, JSON restructuring, routing logic), check if the Functions Activity can handle it before proposing external services, Connect webhooks, Supabase Edge Functions, or complex Pebble templates. Functions run locally in the flow with no external dependency, no latency penalty, and nothing the customer has to maintain.

> **Owner: `flow-designer-activities/functions-activity.md` § Functions vs. Other Options.** Reproduced here so this page works standalone; the reference doc wins on any disagreement.

| Need | Use |
|------|-----|
| Complex data transformation, routing maps, regex | **Function** -- runs locally, no external call |
| Simple string/date manipulation in Set Variable | **Pebble templates** -- lighter weight |
| External API call | **HTTP Request activity** -- Function cannot make network calls |
| Caller interaction (collect digits, play message) | **Standard activities** -- Function is data-only |

**Key constraint:** Functions cannot make outbound HTTP requests [`functions-activity.md` § Functions Activity (Custom Code)]. If your logic needs network access (database queries, external APIs), use an HTTP Request activity instead.

---

## Creating a Function

### Step 1: Navigate to Functions

**Control Hub > Services > Contact Center > Customer Experience > Functions** [`functions-activity.md` § Where to Create Functions]

You can also create a function from the **Functions** tab within the Flow Designer module.

### Step 2: Choose Language and Runtime

Click **New Function**, then configure:

> **Owner: `flow-designer-activities/functions-activity.md` § Runtime** (UI labels) and **`custom-functions.md` § Function Definition Fields** (API values). Reproduced here so this page works standalone; the reference docs win on any disagreement.

| Setting | Options |
|---------|---------|
| **Language** | JavaScript or Python (3.13) |
| **Runtime** | Node.js 22.x (auto-assigned for JavaScript); Python 3.13 (auto-assigned for Python) |
| **Name** | Descriptive name (e.g., `dnis-router`, `date-formatter`). Must be unique **within the organization** -- a duplicate returns `409 Conflict` over the API [`custom-functions.md` § Function Definition Fields] |
| **Description** | What the function does |

If you build the definition as JSON instead of using the UI form, the same two settings are the API fields `language` (`js` or `py`) and `selectedRuntime` (`nodejs22.x` or `python3.13`, **case-sensitive**) [`custom-functions.md` § Function Definition Fields].

### Step 3: Write the Handler

> **Owner: `custom-functions.md` § The `handle` Contract** (the signature and the `request.inputs` / `response.data` contract). Reproduced here so this page works standalone; the reference doc wins on any disagreement.

#### JavaScript

```javascript
export const handle = async (request, response) => {
    const { variableName } = request.inputs;
    
    // Custom logic here
    
    response.data = { key: "value" };
    return response;
}
```

- **Inputs:** Access flow variables mapped to the function via destructuring: `const { myVar } = request.inputs;`
- **Outputs:** Assign to `response.data` as a JSON object. The calling flow extracts values using JSONPath (e.g., `$.key`).

#### Python

> **Documentation pending** -- Cisco help docs confirm Python 3.13 is supported but do not publish the Python handler function signature. The signature below is inferred from the JavaScript pattern and the documented input/output contract (inputs via `request.inputs`, output via `response.data`). **Verify against the function editor template in your tenant.** [Owner: `functions-activity.md` § Function Signature (Python)]

```python
async def handle(request, response):
    variable_name = request.inputs["variableName"]

    # Custom logic here

    response.data = {"key": "value"}
    return response
```

- **Inputs:** Access flow variables via dictionary access: `request.inputs["myVar"]`.
- **Outputs:** Assign to `response.data` as a dictionary. The calling flow extracts values using JSONPath.

### Step 4: Define Input Variables

Click **Add Input Variable** for each input the function needs from the flow. Specify:

- **Name** -- must match the destructured variable name in code (e.g., `input`, `lower_bound`). This is also the key the code reads from `request.inputs` [`custom-functions.md` § `inputs[]` entries]
- **Type** -- one of exactly six values: `boolean`, `datetime`, `decimal`, `integer`, `json`, `string` [`custom-functions.md` § `inputs[]` entries -- see the UNRESOLVED note there on label casing between the UI/import shape and the API enum]

Maximum 10 input variables per function [`functions-activity.md` § Runtime].

### Step 5: Test the Function

Use the built-in test panel:

1. Provide sample input JSON for each input variable
2. Click **Test**
3. Verify the output appears under the `data` key

**Test panel gotcha** [`functions-activity.md` § Test Panel Gotchas]**:** The test panel shows a validation message: "Variable value cannot contain backslashes or double quotes. Alphanumerics, spaces and other characters are allowed." Despite this warning, **raw JSON strings work in both the test panel and at runtime.** Pasting a full JSON object (e.g., an API response body) into the test panel input field succeeds and the function processes it correctly via `JSON.parse()`. At runtime, passing `httpResponseBody` from an HTTP Request node also works.

**If you are testing from the CLI instead of the UI:** wxcc-flow functions test (today `wxcli cc-functions test FUNCTION_ID --json-body '{"inputs":{}}'`) currently returns HTTP 400 (`"Failed to test custom fn, received unexpected response"`). The request shape is correct and the failure is in the execution backend, not the payload -- verified live 2026-07-25 [`custom-functions.md` § Gotchas]. Use the UI test panel above, or publish the function (Step 6) and exercise it from a flow's Function activity.

### Step 6: Publish

Functions use **Version Labels** (like flows) [`functions-activity.md` § Runtime]. Publish the function under one or more of exactly four tags -- `Dev`, `Test`, `Latest`, `Live` -- before it can be selected in a flow activity [`custom-functions.md` § Publishing and tags]. Only a published function can be referenced from a flow.

From the CLI, the same step is `wxcli cc-functions publish ID --json-body '{"tags":["Live"],"comment":"Initial release."}'` [`custom-functions.md` § Publishing and tags].

---

## Using a Function in a Flow

> **Owner: `flow-designer-activities/functions-activity.md` § Input Wiring and § Output Wiring.** Reproduced here so this page works standalone; the reference doc wins on any disagreement.

1. **Drag** the Functions activity from the activity panel onto the Flow Designer canvas
2. **Select Function:** Choose the function name from the dropdown
3. **Select Version Label:** Pick the published tag -- `Dev`, `Test`, `Latest`, or `Live` [`custom-functions.md` § Publishing and tags]
4. **Configure Input Mappings:** Map flow variables to function inputs. The activity shows a dropdown of available flow variables for each input. **Flow variables of matching type must exist before you can map them.** HTTP Request node outputs (like `httpResponseBody`) are available as selectable flow variables without creating a custom variable first. If no flow variables of the required type exist, the activity shows: "No variables of type 'String' are available."
5. **Configure Output:**
   - Create a flow variable in **Flow Settings > Custom Variables** (e.g., `ttsMessage`, type String)
   - On the Function activity canvas, set the **Output Variable** to the flow variable you created
   - Set the **Path Expression** to extract the value from `response.data` (e.g., `$.ttsMessage`)

**Output mapping examples:**

| Flow Variable | Path Expression | Function Code |
|---------------|-----------------|---------------|
| `ttsMessage` | `$.ttsMessage` | `response.data = { ttsMessage: "..." }` |
| `queue_id` | `$.output.queue_id` | `response.data = { output: { queue_id: "..." } }` |

**Important:** The "Output variable" field in the **Function editor** (where you write code) is **documentation only** -- it describes what the function returns for other flow builders to see. The actual output mapping happens on the **Function activity** on the canvas.

### Output Paths

> **Owner: `flow-designer-activities/functions-activity.md` § Output Paths.** Reproduced here so this page works standalone; the reference doc wins on any disagreement.

| Output Path | Fires When |
|---|---|
| **Done** | Function executed successfully and `response.data` is populated. |
| **Undefined Error** | Function threw an unhandled exception, exceeded the 5-second limit, or encountered a runtime error (syntax error, memory overflow). |

> **Documentation pending** -- Cisco help docs confirm that Flow Designer activities have an error handling path via the "Undefined Error" node, and that Functions supports "error messages returned by the function output, status and error codes, runtime error handling." However, the exact output path names and specific failure codes for the Functions activity are not enumerated in the Cisco help docs. The path names above ("Done" / "Undefined Error") follow the general Flow Designer error handling pattern. **Verify against the canvas in your tenant.** (The API layer corroborates that the activity has exactly two ports -- one success, one error -- naming them `default` and `error` [`flow-designer-flowir.md` § 8. Complete Activity Registry]. That is evidence for the port count and error behavior, not confirmation of the UI labels.)

If you do not connect the Undefined Error path to another activity, the flow falls back to the `OnGlobalError` event handler.

---

## Access Control

Supervisors and administrators can manage functions. Supervisor access is controlled by the **Function** setting (Edit, View, or None) under **Customer Experience** within the **User Profile** in Control Hub [`functions-activity.md` § Access Control].

Over the API, the equivalent gate is token scope: `cjp:config_read` to list, get, and export; `cjp:config_write` to create, update, test, publish, lock, unlock, and import [`custom-functions.md` § Authentication].

---

## Common Patterns

> **Owner: `flow-designer-activities/functions-activity.md` § Example: DNIS Data Map (Replaces Case Activities), § Example: Random Number Generator, § Example: Regex Pattern Matcher.** The three code samples below are reproduced verbatim so this page works standalone; the reference doc wins on any disagreement. The example UUIDs are placeholders -- replace them with real queue IDs from your tenant.

### DNIS Data Map (Replaces Case Activities)

Instead of a multi-branch Case activity for DNIS-based routing, use a Function that returns routing data per DNIS:

```javascript
export const handle = async (request, response) => {
    const { input } = request.inputs;
    
    const dnisMap = {
        "+18005551234": {
            queue_id: "7ab606fe-0443-42db-9013-2e9e87edfeed",
            priority: 1,
            tts_message: "Thank you for calling Sales."
        },
        "+18005555678": {
            queue_id: "a1b2c3d4-5678-90ab-cdef-1234567890ab",
            priority: 2,
            tts_message: "Thank you for calling Support."
        }
    };
    
    response.data = { output: dnisMap[input] || dnisMap["default"] };
    return response;
}
```

**Input Mapping:** `input` <-- `{{NewContact.DNIS}}`
**Output JSONPath:** `$.output.queue_id`, `$.output.priority`, `$.output.tts_message`

This replaces a Case activity with N branches -- easier to maintain when DNIS count grows.

### Random Number Generator

```javascript
export const handle = async (request, response) => {
    const { lower_bound, upper_bound } = request.inputs;
    
    if (lower_bound >= upper_bound) {
        response.data = { random_number: -1 };
        return response;
    }
    
    const result = Math.floor(Math.random() * (upper_bound - lower_bound + 1)) + lower_bound;
    response.data = { random_number: result };
    return response;
}
```

### Regex Pattern Matcher

```javascript
export const handle = async (request, response) => {
    const { needle, haystack } = request.inputs;
    
    try {
        const regex = new RegExp(haystack);
        response.data = { match: regex.test(needle) };
    } catch (e) {
        response.data = { match: false };
    }
    return response;
}
```

---

## Importing Functions

Functions can be imported via JSON. See `docs/examples/function-import.json` for the template format. The import includes name, language, runtime, source code, input definitions, and sample output [`functions-activity.md` § Importing Functions].

Over the API this is a pair of calls -- `POST /v1/{orgId}/functions/{id}:export` returns the definition object (`name`, `language`, `runtime`, `description`, `sourceCode`, `inputs`, `outputs`) and `POST /v1/{orgId}/functions:import` accepts it as a **multipart file upload** [`custom-functions.md` § Export / import between environments]. From the CLI: `wxcli cc-functions export ID` and `wxcli cc-functions import --file FILE`.

---

## Logging and Debugging

Console logs are not exposed from the function runtime. To capture debug information, set and access values using a custom output string array in `response.data` [`functions-activity.md` § Logging and Debugging].

---

## Limits

> **Owner: `flow-designer-activities/functions-activity.md` § Runtime.** Reproduced here so this page works standalone; the reference doc wins on any disagreement.

| Property | Value |
|----------|-------|
| Max functions per org | 200 |
| Max memory per function | 128 MB |
| Execution time limit | 5 seconds -- ⚠ **UNRESOLVED**, see the note below the table |
| Max input variables | 10 |
| Code limit | ~5,000 lines |
| Output | One JSON output variable (parse individual values with JSONPath) |
| Music on wait | Automatic -- prevents silence to callers during function execution. Configurable timeout 2-5 seconds (default 2 seconds). |

⚠ **The 5-second figure is UNRESOLVED** -- the API definition also exposes a per-function `timeoutInSec` field, and the repo does not record whether 5 seconds is a hard platform ceiling or the default of that configurable field. Both readings are stated side by side in `functions-activity.md` § Runtime; do not assume either one when sizing a function.

### Failure Scenarios

> **Owner: `flow-designer-activities/functions-activity.md` § Output Paths.** Reproduced here so this page works standalone; the reference doc wins on any disagreement. The path names in this table inherit the "Documentation pending" hedge in § Output Paths above -- verify them against the canvas in your tenant.

| Scenario | Behavior |
|---|---|
| Unhandled exception in code | Flow takes the Undefined Error path. Error details available in flow debug logs. |
| Execution exceeds 5-second limit | Function is terminated. Flow takes the Undefined Error path. |
| Memory usage exceeds 128 MB | Function is terminated. Flow takes the Undefined Error path. |
| Code syntax error at runtime | Flow takes the Undefined Error path. |
| `response.data` not set | Function completes but output variables are empty/null. Flow takes the Done path. |

The Functions activity is subject to system-enforced self-loop limits. If the activity is called in a loop that exceeds the system limit, it automatically exits via the global error path [`functions-activity.md` § Output Paths].
