## HTTP Connector (Flow Designer → WxCC APIs)

<!-- ref-tag: fd-act-http-connector-v1 -->

The HTTP Connector provides managed authentication for calling WxCC APIs from Flow Designer flows. It eliminates the need to build a separate token server or manage OAuth refresh tokens manually — the connector handles token lifecycle natively.

### When to Use

Use an HTTP Connector when a Flow Designer flow needs to call any public Webex Contact Center API:

- **Search API**: Look up previous interactions (e.g., route caller to their last agent)
- **CC Configuration API**: Read/write Global Variables, queue configs, team assignments
- **Any other public WxCC API endpoint**

**Not for Webex Connect.** HTTP Connectors are a Flow Designer concept. In Webex Connect flows, use the standard HTTP Request node with manual auth headers (API key, Bearer token, etc.).

### Prerequisites

One of these Control Hub roles:

- Full Administrator
- External Admin with Full Administrator Access
- Contact Center Service Administrator

### Create a Connector

1. Log into **Webex Control Hub** (admin.webex.com)
2. Navigate to **Contact Center → Connectors**
3. Under **Webex Contact Center Connector**, click **Set Up** (first time) or **Add More**
4. Configure:

| Field | Value | Notes |
|-------|-------|-------|
| **Connector Name** | Descriptive name (e.g., "WxCC Search Connector") | This name appears in the Flow Designer dropdown |
| **Access Level** | **Read** or **Read/Write** | Read = GET only; Read/Write = GET + POST/PUT/UPDATE |

5. Click **Authorize** to complete setup

**Best practice:** Create separate connectors for read-only vs. mutating operations. Use Read for flows that only query data; use Read/Write only when the flow needs to create or update records.

### Use the Connector in a Flow

In the Flow Designer **HTTPRequest** activity:

1. Enable **Use Authenticated Endpoint** (checkbox/toggle)
2. Select your connector from the dropdown
3. In **Request Path**, enter the relative path only (e.g., `/search`) — the connector supplies the base URL and auth headers automatically
4. Configure request body, output variables, and error handling as usual

### Example: Route to Previous Agent via Search API

```
NewPhoneContact
  → Set Variable (current_time, one_day_ago, trimmed_ANI)
  → HTTPRequest
      Use Authenticated Endpoint: enabled
      Connector: "WxCC Search Connector"
      Request Path: /search
      Body: { filter on ANI + time range }
      Output: Agent_ID
  → Case (Agent_ID found?)
      → Yes: Queue Contact (specific agent)
      → No: Queue Contact (main queue)
```

### Rate Limiting

API calls from Flow Designer are rate limited. Handle 429 (Too Many Requests) errors using a **Case** activity that checks the HTTP status code and routes to a fallback path (e.g., queue to default pool instead of retrying).

### Error Handling

Use a **Case** activity after the HTTPRequest to handle all error codes listed in the API definition. Common codes:

| Code | Meaning | Recommended Action |
|------|---------|-------------------|
| 200 | Success | Continue flow |
| 400 | Bad request | Log error, route to fallback |
| 401 | Auth failure | Connector misconfigured — check access level |
| 403 | Forbidden | Insufficient permissions on connector |
| 404 | Not found | No matching record — handle gracefully |
| 429 | Rate limited | Route to fallback path |
| 500 | Server error | Log error, route to fallback |

**Sensitive data:** Do not store sensitive API response data in flow logs.

---

