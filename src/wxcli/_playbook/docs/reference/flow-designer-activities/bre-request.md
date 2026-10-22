## BRE Request Activity

<!-- ref-tag: fd-act-bre-request-v1 -->

The BRE Request activity invokes the Business Rules Engine to evaluate rules against uploaded datasets during call processing. Use it for ANI-based routing decisions, VIP caller identification, or any key-value lookup stored in BRE.

> Full BRE reference (DataSync setup, rule creation, Drools syntax, regional URLs): `docs/reference/bre.md`

### Configuration

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | Optional description |

### Query Parameters

| Parameter | Required | Editable | Default |
|---|---|---|---|
| `context` | Yes | No (cannot edit/delete) | — |
| `ani` | No | Yes (edit or delete) | `{{NewContact.ANI}}` — Contains the originating phone number of the call. This is a default parameter that you can edit or delete, based on the rules configuration in the BRE. |

The `context` parameter must match the Context name in the BRE Utility. Click **Add New** for additional key-value parameters.

> **TenantID** is automatically injected as a parameter and does not need to be configured.

### Content Type Formats

BRE supports responses in JSON, XML, TOML, and YAML. Data is normalized to an object hierarchy before Path Expression execution, so JSONPath is used in the response object regardless of the configured Content Type. For XML, use a tool like `https://codeshack.io/xml-to-json-converter/` to understand the normalized JSON structure. For TOML/YAML, similar conversion tools exist. The Path Expression always uses JSONPath syntax regardless of the original content type.

### Response Settings

| Field | Default |
|---|---|
| Response Timeout | 2000 ms |
| Number of Retries | — (retries only on 5xx) |

### Parse Settings

| Field | Description |
|---|---|
| Response Variable | Flow variable to receive parsed value |
| Path Expression | JSONPath — always JSONPath regardless of response content type (XML/TOML/YAML/JSON all normalized to JSON) |

### Output Variables

| Variable | Description |
|---|---|
| `BRERequest1.httpResponseBody` | Full response body from BRE (`BRERequest1` is the default activity label — adjust if renamed) |
| `BRERequest1.httpStatusCode` | HTTP status code. Classified as: Informational (100–199), Successful (200–299), Redirects (300–399), Client errors (400–499), Server errors (500–599). |

### Output Paths

| Output Path | Fires When |
|---|---|
| **Success** (`default`) | BRE returned a response (check `httpStatusCode` to distinguish 2xx from 4xx/5xx) |

The BRE Request exposes only the `default` (Success) output port — it has no activity-level error branch (wxcc-flow describe bre-request (today `wxcli cc-flow show-activity PROJECT_ID bre-request`) → `outputPorts: []`; flow-designer-flowir.md § 8 lists only `default`, like `http-request-v2`). System errors during execution (network failure, timeout exhausted after retries, malformed configuration) route to the flow's `OnGlobalError` event handler, not an activity output path.

> **Important:** The Success path fires for all HTTP responses including 4xx/5xx. Always branch on `httpStatusCode` after the BRE Request to handle error responses explicitly.

### Failure Codes

> **Documentation pending** — the Cisco help docs do not enumerate activity-specific failure codes (like `FailureCode` / `FailureDescription`) for the BRE Request activity. The BRE Request does not appear to expose `FailureCode` output variables the way Bridged Transfer or Blind Transfer do. Use `httpStatusCode` to detect BRE-side errors (4xx/5xx) and the `OnGlobalError` event handler for system-level failures (the activity has no error output port — wxcc-flow describe bre-request (today `wxcli cc-flow show-activity PROJECT_ID bre-request`) → `outputPorts: []`).

### Restrictions

- Requires BRE DataSync access (contact Cisco Account Manager to enable)
- Requires Full Administrator role for DataSync configuration
- At least one domain with rules must be created in the BRE Utility before the activity can return results
- The `context` query parameter is mandatory and cannot be edited or deleted
- `TenantID` is injected automatically — do not add it as a manual parameter
- Retries only apply to 5xx status codes; 4xx errors are not retried

> **Documentation pending** — self-loop limit for BRE Request and whether the activity can be used in Event Flows are not verified against Cisco help docs.

### Prerequisites

- BRE DataSync access (contact Cisco Account Manager)
- Full Administrator role for DataSync configuration
- At least one domain with rules created in the BRE Utility

---

