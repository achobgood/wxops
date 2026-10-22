## Custom Connectors (Flow Designer → External APIs)

<!-- ref-tag: fd-act-custom-connectors-v1 -->

Custom Connectors provide managed authentication for calling **third-party APIs** (ServiceNow, Salesforce, custom backends) from Flow Designer flows. They work the same way as the built-in WxCC HTTP Connector but target external services instead of WxCC APIs.

### When to Use

Use a Custom Connector when a Flow Designer flow needs to call an external API that requires OAuth 2.0 or Basic Auth. The connector manages the token lifecycle — no manual token refresh logic needed.

**Custom Connector vs. WxCC Connector vs. manual auth:**

| Approach | Target APIs | Auth Management | Setup Location |
|---|---|---|---|
| WxCC HTTP Connector | WxCC APIs only (Search, CC Config) | Fully managed | Control Hub → Connectors → Webex Contact Center |
| **Custom Connector** | **Any external API** (ServiceNow, Salesforce, etc.) | **Fully managed** | **Control Hub → Connectors → Custom Connectors** |
| Manual auth headers | Any API | Manual (you handle tokens) | Per-HTTPRequest activity |

### Create a Custom Connector

1. Log into **Webex Control Hub** (admin.webex.com)
2. Navigate to **Contact Center → Connectors**
3. Under **Custom Connectors**, click **Add More**
4. Configure:

| Field | Description |
|---|---|
| **Name** | Descriptive name (e.g., "SNOWConnector") — appears in Flow Designer dropdown |
| **Authentication Type** | Basic Authentication or OAuth 2.0 |

**For OAuth 2.0:**

| Field | Description |
|---|---|
| **Grant Type** | Client Credentials – Client Secret, Client Credentials – Certificate, or Password Grant |
| **Token URL** | The external service's OAuth token endpoint |
| **Client ID** | OAuth client ID from the external service |
| **Client Secret** | OAuth client secret (for Client Credentials – Client Secret grant) |
| **Scope** | Required OAuth scopes (service-specific) |

**For Basic Authentication:**

| Field | Description |
|---|---|
| **Username** | Username for basic auth |
| **Password** | Password for basic auth |
| **Validation URL** | URL used to validate the credentials |

**All authentication types also require:**

| Field | Description |
|---|---|
| **Resource Domain URL** | The base URL of the external service (must include `https://` prefix) |

5. Save and authorize

### Use in a Flow

In the Flow Designer **HTTPRequest** activity:

1. Enable **Use Authenticated Endpoint** (toggle ON)
2. Select your Custom Connector from the **Connector** dropdown
3. In **Request Path**, enter the relative API path only (e.g., `/api/now/table/incident`) — the connector supplies the base URL and auth headers
4. Configure query parameters, request body, and parse settings as usual

### Example: ServiceNow Incident Lookup

```
HTTPRequest
  Use Authenticated Endpoint: ON
  Connector: SNOWConnector
  Request Path: /api/now/table/incident
  Method: GET
  Query Params: sysparm_query=caller_id={{callerId}}&sysparm_limit=1
```

### Error Handling

Custom Connectors manage the OAuth token lifecycle internally — the platform ensures the access token remains valid and refreshes it automatically. However, the HTTP Request activity can still fail for connector-related reasons:

| Scenario | Behavior |
|---|---|
| Token refresh succeeds | Transparent to the flow — the request proceeds normally |
| External service unreachable | The HTTP Request activity returns a non-2xx `httpStatusCode` or fires the **Undefined Error** path |
| Invalid credentials (client secret changed, revoked) | The HTTP Request activity returns an auth error status code (401/403) via the default exit path |
| Connection timeout | The HTTP Request activity's Response Timeout applies; if exceeded, the request fails via the default exit path |

The HTTP Request activity does not have a separate output edge for connector auth failures. All completed requests (regardless of status code) exit via the default path. Use a Condition or Case activity downstream to branch on `{{HTTPRequest.httpStatusCode}}`. System-level failures (DNS resolution, malformed URL, platform error) fire the **Undefined Error** path.

> **Documentation pending** — Cisco documentation states the platform "internally ensures that the OAuth access token remains valid" but does not enumerate specific error codes or retry behavior when token refresh itself fails. If you encounter persistent 401 errors, verify the connector credentials in Control Hub.

### Restrictions

- **Maximum connectors:** Up to 10 custom connectors per organization.
- **Authentication required:** Custom Connectors are only needed when the external endpoint requires authentication. For unauthenticated endpoints, disable the **Use Authenticated Endpoint** toggle in the HTTP Request activity.
- **HTTPS only:** The Resource Domain URL must use an `https://` prefix.
- **Supported grant types:** OAuth 2.0 supports Client Credentials – Client Secret, Client Credentials – Certificate, and Password Grant. Other grant types (e.g., Authorization Code) are not supported.

> **Documentation pending** — region availability restrictions for Custom Connectors have not been verified against Cisco help docs. Custom Connectors are documented as generally available, but specific regional limitations (if any) are not enumerated.

### Custom Connectors vs. Webex Connect HTTP Nodes

Custom Connectors are a **Flow Designer** concept. They do not exist in Webex Connect.

| Aspect | Custom Connector (Flow Designer) | HTTP Request node (Webex Connect) |
|---|---|---|
| **Platform** | WxCC Flow Designer | Webex Connect |
| **Auth management** | Fully managed — connector handles token lifecycle | Manual — you manage tokens in flow variables or via Custom Nodes |
| **Setup location** | Control Hub → Contact Center → Connectors | Per-node configuration within the Connect flow |
| **Use case** | Voice IVR flows calling external APIs | Digital channel flows, action flows, notification flows |

Do not confuse these two mechanisms. If you are building in Flow Designer, use Custom Connectors (or the WxCC HTTP Connector for WxCC APIs). If you are building in Webex Connect, use the HTTP Request node with manual auth headers or Custom Nodes.

---

