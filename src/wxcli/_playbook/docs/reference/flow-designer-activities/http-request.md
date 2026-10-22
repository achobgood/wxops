## HTTP Request Activity

<!-- ref-tag: fd-act-http-request-v1 -->

The HTTP Request activity makes outbound HTTP calls to external APIs from a Flow Designer flow. Supports Basic Auth, OAuth 2.0 via connectors, and unauthenticated endpoints.

> **Queue Contact buffer:** When you place an HTTP Request activity immediately after Queue Contact, the HTTP Request may not retrieve the required data. Add a buffer activity (Play Message or Play Music) between Queue Contact and HTTP Request to ensure the required data is available.

### Configuration Fields

**General:**

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | Optional description |

**Request:**

| Field | Description |
|---|---|
| Use Authenticated Endpoint | Toggle (default ON). ON = use connector for auth. OFF = manual auth via headers. |
| Connector | Dropdown of connectors from Control Hub (when toggle ON) |
| Request Path | API path only — connector supplies domain (when toggle ON) |
| Request URL | Full URL including domain (when toggle OFF) |
| Method | GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD |

**Method Type Definitions:**

| Method | Description |
|---|---|
| GET | Request data from a specified resource |
| POST | Send data to a server to create or update a resource |
| PUT | Replaces all current representations of the target resource with the request payload |
| PATCH | Apply partial modifications to a resource |
| DELETE | Delete the specified resource |
| OPTIONS | Describe the communication options for the target resource |
| HEAD | Asks for a response identical to that of a GET request, but without the response body |

**Query Parameters:** Key-value pairs. Click **Add New** to add rows. Joined with `&` in the final URL. Supports `{{variable}}` syntax in values. **At least one row is required** — the section cannot be left empty. If the API has no required query parameters, add `orgId` = `{{orgId}}` as a safe default (most Webex APIs accept it).

**HTTP Request Headers:** Key-value pairs. Click **Add New** to add rows. For manual Bearer auth, add `Authorization` = `Bearer {{token_variable}}`.

**Content Type:** Dropdown — Application/JSON, Form URL Encoded, TOML, XML, File, YAML, Form Data, GraphQL, Other.

- **File:** The CONTENT and FILE NAME columns appear. CONTENT dropdown lists JSON variables from the flow and output variables from Record activities. FILE NAME is the name of the audio file as it appears on the destination server.
- **Form Data:** Captures form data in key-value pairs. Supports uploading of files and form data (useful for uploading audio files). Each row has a Key, a Type (Text or File), and a Value. Form Data supports referencing the file name from the Record activity for use in recording prompts and greetings via flow.
- **GraphQL:** The Query and GraphQL Variables fields appear. The Query parameter is required and should contain the source text of a GraphQL document. The GraphQL Variables field represents the dynamic values for the query. With GraphQL support, you can make requests to any API that supports GraphQL natively, such as using the WebexCC API Connector to call the Search API.
- **Other:** Allows you to specify a custom content type if the API requires a Content-Type header not available in the standard dropdown options.

**Request Body:** Appears for POST/PUT/PATCH. Format depends on Content Type. For Application/JSON, enter raw JSON with `{{variable}}` interpolation.

**Response Timeout:** Default 2000ms. The Cisco docs state you can set this to "any unlimited value" — however, the exact system-enforced maximum has not been verified. See Restrictions section below.

**Number of Retries:** Retries only on 5xx status codes (e.g., 500, 503). The Cisco docs state you can set "any unlimited value" for retries — however, the exact system-enforced maximum has not been verified. See Restrictions section below.

**Related Flow Templates:** Avoid duplicate callback, Audio prompt and recording, Last agent routing, Microsoft Dynamics HTTP(S) data dip, Salesforce HTTP(S) data dip, ServiceNow HTTP(S) data dip, Zendesk HTTP(S) data dip.

### Parse Settings (Response)

| Field | Description |
|---|---|
| Content Type | JSON, TOML, XML, YAML — **all normalized to JSON before parsing** |
| Output Variable | Flow variable to receive parsed value |
| Path Expression | **JSONPath** — always JSONPath regardless of response content type |

**JSONPath filter expressions are supported.** You can target specific array elements by field value:

| Pattern | Example | Returns |
|---|---|---|
| Array index | `$.phoneNumbers[0].value` | First phone number (scalar) |
| Filter by type | `$.phoneNumbers[?(@.type=='work_extension')].value` | `["1613"]` — array, not scalar |
| Nested filter | `$.Resources[0].phoneNumbers[?(@.type=='alternate1')].value` | Specific phone type from SCIM2 response |

**Filter expressions always return arrays.** `$.phoneNumbers[?(@.type=='work_extension')].value` returns `["1613"]` not `"1613"`. Flow Designer's JSONPath engine does not support dereferencing the result with `[0]` — neither `$.phoneNumbers[?(@.type=='work_extension')].value[0]` nor `$.phoneNumbers[?(@.type=='work_extension')][0].value` works; both return `[]`.

**Workaround:** Use a direct array index instead of a filter when the element order is stable. Example: if `work_extension` is always at index 1, use `$.phoneNumbers[1].value` to get the scalar directly.

### Output Variables (auto-exposed)

| Variable | Description |
|---|---|
| `{{label.httpStatusCode}}` | HTTP status code (200, 404, 500, etc.) |
| `{{label.httpResponseBody}}` | Full response body |
| `{{label.httpResponseHeaders}}` | Response headers |

### Activity Wait Settings

| Field | Default | Description |
|---|---|---|
| Enable Audio on Wait | Off | Plays audio file to caller during HTTP response wait |
| Audio File | — | Select uploaded audio file |
| Delay | 2000ms | Wait before playing audio (keep above 2s) |

### Output Paths

| Output Path | Fires When |
|---|---|
| *(default exit)* | HTTP request completes (any status code — 2xx, 4xx, 5xx). The `httpStatusCode` output variable contains the actual status code. Use a Condition or Case activity downstream to branch on success vs. failure status codes. |

The HTTP Request activity exposes only the `default` output port — it has no activity-level error branch (wxcc-flow describe http-request (today `wxcli cc-flow show-activity PROJECT_ID http-request`) → `outputPorts: []`; flow-designer-flowir.md § 8 lists only `default`). System-level errors during the request (connection failure, DNS resolution failure, malformed URL, internal platform error) route to the flow's `OnGlobalError` event handler in the Event Flows tab, not an activity output path.

> **Important:** The HTTP Request activity does **not** have separate output edges for different HTTP status codes. All completed requests (regardless of status code) exit via the default path. To handle 4xx or 5xx responses, add a Condition activity after the HTTP Request that checks `{{HTTPRequest.httpStatusCode}}`.

### Wiring Pattern

```
HTTP Request (GET /api/customers?id={{custId}})
  │
  └── (default exit) → Condition: {{HTTPRequest1.httpStatusCode}} == 200
        ├── TRUE → Parse / continue flow
        └── FALSE → Play Message ("lookup failed") → fallback path

# System-level errors (connection/DNS failure) route to the OnGlobalError event handler, not an output edge.
```

### Failure Codes

No proprietary failure codes. HTTP errors are returned via `httpStatusCode` in the output variables (e.g., 400, 401, 404, 429, 500). Use a Condition or Case activity downstream to branch on the status code. System-level errors (connection failure, DNS resolution) route to the `OnGlobalError` event handler — the activity has no error output port (wxcc-flow describe http-request (today `wxcli cc-flow show-activity PROJECT_ID http-request`) → `outputPorts: []`).

### Restrictions

- **Queue Contact buffer:** Do not place an HTTP Request activity immediately after Queue Contact — the HTTP Request may not retrieve required data. Add a buffer activity (Play Message or Play Music) between them.
- **Retries are automatic on 5xx only:** The retry mechanism triggers only on 5xx server errors, not on 4xx client errors or timeouts.
- **Rate limiting:** API calls from Flow Designer are rate-limited. Handle potential 429 (Too Many Requests) responses gracefully by branching on `httpStatusCode`.
- **Response Timeout and Number of Retries:** The current documentation states these can be set to "any unlimited value." The exact system-enforced maximums are not confirmed.

> **Documentation pending** — the exact maximum values for Response Timeout and Number of Retries have not been verified against Cisco help docs. The UI may accept large values, but the platform likely enforces system limits. Test with your target values in a non-production flow.

### API-Specific Auth Scopes

Different Webex APIs require different OAuth scopes. Common mistake: using a token with the wrong scope family.

| API | Base URL | Required Scope |
|---|---|---|
| People API | `webexapis.com/v1/people` | `spark-admin:people_read` |
| SCIM2 API | `webexapis.com/identity/scim/{orgId}/v2/Users` | `identity:people_read` |
| CJDS (reads) | `api.wxcc-{region}.cisco.com` (the same host as writes; verified 2026-10-19 on `us1`. Until 2026-10-19 this row listed `api-jds.prod-{region}.ciscowxdap.com`, which does not resolve: DNS gives NXDOMAIN) [owner: `contact-center-journey.md` intro] | `cjds:admin_org_read` |
| CJDS (writes) | `api.wxcc-{region}.cisco.com` | `cjds:admin_org_write` |
| WxCC APIs (via connector) | Managed by connector | Connector handles auth |

A PAT (Personal Access Token) from developer.webex.com works for People API but may 401 on SCIM2 if the `identity:people_read` scope isn't present. For production, create an OAuth Integration or Service App with the required scopes explicitly selected.

---

