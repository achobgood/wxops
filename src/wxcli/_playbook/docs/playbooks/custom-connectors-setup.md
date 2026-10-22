# Custom Connectors Setup

<!-- ref-tag: custom-connectors-setup-v1 -->

Custom Connectors provide managed authentication for calling **third-party APIs** (ServiceNow, Salesforce, custom backends) from Flow Designer flows. The connector manages the OAuth token lifecycle automatically — no manual token refresh logic or subflows needed.

---

## When to Use

| Approach | Target APIs | Auth Management | Setup Location |
|---|---|---|---|
| WxCC HTTP Connector | WxCC APIs only (Search, CC Config) | Fully managed | Control Hub > Connectors > Webex Contact Center |
| **Custom Connector** | **Any external API** (ServiceNow, Salesforce, etc.) | **Fully managed** | **Control Hub > Connectors > Custom Connectors** |
| Manual auth headers | Any API | Manual (you handle tokens) | Per-HTTPRequest activity |
| Service App + Token Refresh Subflow | Any Webex API (People, SCIM2, Calling, CJDS) | Self-managed via subflow | Flow Designer subflow |
| Custom Node with OAuth | Any Webex API from Connect | Managed by Connect | Webex Connect Custom Nodes |

**Use a Custom Connector when:**
- Your Flow Designer flow calls an external API that requires OAuth 2.0 or Basic Auth
- You want the platform to handle token refresh automatically (no subflow needed)
- The target is a third-party service, not a Webex API

**Do NOT use a Custom Connector when:**
- You only need WxCC's own APIs (Search, CC Config) — use the built-in HTTP Connector instead
- You need to call Webex platform APIs (People, SCIM2, Calling) — use a Service App + Token Refresh Subflow (see `webex-api-auth.md` Pattern 2)
- You are building in Webex Connect, not Flow Designer — Custom Connectors do not exist in Connect. Use manual auth headers or Custom Nodes.

[source: custom-connectors.md]

---

## Prerequisites

### Service App or API Credentials

Before creating a Custom Connector, you need credentials from the external service:

**For OAuth 2.0:**
- Client ID
- Client Secret (for Client Credentials - Client Secret grant)
- Token URL (the external service's OAuth token endpoint)
- Required OAuth scopes (service-specific)

**For Basic Auth:**
- Username
- Password
- Validation URL (URL used to validate the credentials)

### If Calling Webex APIs

Custom Connectors are scoped to **third-party APIs**, not Webex APIs. If you need to call Webex platform APIs (People, SCIM2, Calling, CJDS), see `webex-api-auth.md` for the correct patterns:

- **Pattern 1 (HTTP Connector):** WxCC APIs only
- **Pattern 2 (Service App + Token Refresh Subflow):** Any Webex API from Flow Designer
- **Pattern 3 (Custom Node with OAuth):** Any Webex API from Webex Connect
- **Pattern 4 (Custom Connector):** Third-party APIs from Flow Designer (this playbook)

To create a Service App (needed for Pattern 2):
1. Go to **developer.webex.com** > avatar menu > **My Webex Apps**
2. Click **Create a New App** > **Service App**
3. Configure: Name, Description, Contact email, Scopes (only request what your flows need)
4. Record the **Client ID** and **Client Secret**
5. Authorize in **Control Hub > Apps > Service Apps** (search by Client ID, not name)

[source: webex-api-auth.md SS Step 1-2]

---

## Creating a Custom Connector

### Step 1: Open the Connectors Page

1. Log into **Webex Control Hub** (admin.webex.com)
2. Navigate to **Contact Center > Connectors**
3. Under **Custom Connectors**, click **Add More**

[source: custom-connectors.md SS Create a Custom Connector]

### Step 2: Name and Authentication Type

| Field | Description |
|---|---|
| **Name** | Descriptive name (e.g., "SNOWConnector") — this appears in the Flow Designer dropdown when selecting a connector |
| **Authentication Type** | Basic Authentication or OAuth 2.0 |

[source: custom-connectors.md SS Create a Custom Connector]

### Step 3a: OAuth 2.0 Configuration

If you selected **OAuth 2.0** as the authentication type:

| Field | Description |
|---|---|
| **Grant Type** | Client Credentials - Client Secret, Client Credentials - Certificate, or Password Grant |
| **Token URL** | The external service's OAuth token endpoint |
| **Client ID** | OAuth client ID from the external service |
| **Client Secret** | OAuth client secret (for Client Credentials - Client Secret grant) |
| **Scope** | Required OAuth scopes (service-specific) |

**Supported grant types:** Client Credentials - Client Secret, Client Credentials - Certificate, and Password Grant. Other grant types (e.g., Authorization Code) are not supported.

[source: custom-connectors.md SS Create a Custom Connector, Restrictions]

### Step 3b: Basic Auth Configuration

If you selected **Basic Authentication** as the authentication type:

| Field | Description |
|---|---|
| **Username** | Username for basic auth |
| **Password** | Password for basic auth |
| **Validation URL** | URL used to validate the credentials |

[source: custom-connectors.md SS Create a Custom Connector]

### Step 4: Resource Domain URL (All Authentication Types)

| Field | Description |
|---|---|
| **Resource Domain URL** | The base URL of the external service. **Must include `https://` prefix.** Example: `https://your-instance.service-now.com` |

This is the base URL that all API requests through this connector will use. In Flow Designer, you only enter the relative path — the connector supplies this base URL automatically.

[source: custom-connectors.md SS Create a Custom Connector]

### Step 5: Save and Authorize

Click **Save** to create the connector. The connector must be authorized before it can be used in flows.

---

## Linking to an HTTP Request Activity

Once the Custom Connector is created, use it in any Flow Designer flow:

1. Drag an **HTTPRequest** activity onto the Flow Designer canvas
2. Enable **Use Authenticated Endpoint** (toggle ON)
3. Select your Custom Connector from the **Connector** dropdown
4. In **Request Path**, enter the relative API path only (e.g., `/api/now/table/incident`) — the connector supplies the base URL and auth headers
5. Configure query parameters, request body, and parse settings as usual

[source: custom-connectors.md SS Use in a Flow]

### Example: ServiceNow Incident Lookup

```
HTTPRequest
  Use Authenticated Endpoint: ON
  Connector: SNOWConnector
  Request Path: /api/now/table/incident
  Method: GET
  Query Params: sysparm_query=caller_id={{callerId}}&sysparm_limit=1
```

[source: custom-connectors.md SS Example]

---

## Testing the Connector

### Verify Token Refresh Works

Custom Connectors manage the OAuth token lifecycle internally — the platform ensures the access token remains valid and refreshes it automatically. To verify:

1. Build a simple test flow: NewPhoneContact > Set Variable > HTTPRequest (with Custom Connector) > Parse > Play Message (read back a value) > Disconnect Contact
2. Wire OnGlobalError to a Play Message + Disconnect for safety
3. Publish and call the test Entry Point
4. Verify the HTTP Request returns data (check via Flow Debugging — click the **Debug** button at the bottom of the Flow Designer canvas)
5. Wait for the token to expire (depends on the external service), then call again — the connector should refresh automatically

### Verify Error Handling

All completed requests (regardless of status code) exit via the HTTPRequest activity's default path. Use a **Condition** or **Case** activity downstream to branch on `{{HTTPRequest.httpStatusCode}}`:

- `200`: Success — continue processing
- `401/403`: Auth error — connector credentials may be invalid or revoked
- `404`: Resource not found — check the Request Path
- `5xx`: External service error — retry or route to fallback

System-level failures (DNS resolution, malformed URL, platform error) fire the **Undefined Error** path.

[source: custom-connectors.md SS Error Handling]

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| Persistent 401 errors | Client secret changed or revoked at the external service | Verify the connector credentials in Control Hub > Contact Center > Connectors > Custom Connectors. Update the Client Secret if it was rotated. |
| Connector not appearing in Flow Designer dropdown | Connector not saved or not authorized | Return to Control Hub > Contact Center > Connectors and verify the connector was saved successfully |
| Request Path returns 404 | Wrong relative path — the connector supplies the base URL | Verify the Request Path is relative (e.g., `/api/now/table/incident`), not a full URL |
| Resource Domain URL rejected | Missing `https://` prefix | The Resource Domain URL must include `https://` |
| "Use Authenticated Endpoint" not visible | HTTPRequest activity misconfigured | Check the HTTPRequest activity properties panel — the toggle should be visible in the configuration |
| Scope mismatch (403 Forbidden) | OAuth scopes on the connector do not include the required scope for the API endpoint | Check what scopes the external API endpoint requires, then update the Scope field on the Custom Connector in Control Hub |
| Connection timeout | External service unreachable or slow | The HTTPRequest activity's Response Timeout applies. Increase the timeout if the external service is known to be slow. |

> **Note:** Cisco documentation states the platform "internally ensures that the OAuth access token remains valid" but does not enumerate specific error codes or retry behavior when token refresh itself fails. [source: custom-connectors.md SS Error Handling, Documentation pending]

> **Note:** Region availability restrictions for Custom Connectors have not been verified against Cisco help docs. Custom Connectors are documented as generally available, but specific regional limitations (if any) are not enumerated. [source: custom-connectors.md SS Restrictions, Documentation pending]

---

## Restrictions

- **Maximum connectors:** Up to 10 custom connectors per organization
- **HTTPS only:** The Resource Domain URL must use an `https://` prefix
- **Supported OAuth grant types:** Client Credentials - Client Secret, Client Credentials - Certificate, and Password Grant. Other grant types (e.g., Authorization Code) are not supported.
- **Authentication required:** Custom Connectors are only needed when the external endpoint requires authentication. For unauthenticated endpoints, disable the **Use Authenticated Endpoint** toggle in the HTTP Request activity.
- **Flow Designer only:** Custom Connectors do not exist in Webex Connect. For Connect flows, use manual auth headers in the HTTP Request node or Custom Nodes with OAuth.

[source: custom-connectors.md SS Restrictions, Custom Connectors vs. Webex Connect HTTP Nodes]

---

## Custom Connectors vs. Webex Connect HTTP Nodes

| Aspect | Custom Connector (Flow Designer) | HTTP Request node (Webex Connect) |
|---|---|---|
| **Platform** | WxCC Flow Designer | Webex Connect |
| **Auth management** | Fully managed — connector handles token lifecycle | Manual — you manage tokens in flow variables or via Custom Nodes |
| **Setup location** | Control Hub > Contact Center > Connectors | Per-node configuration within the Connect flow |
| **Use case** | Voice IVR flows calling external APIs | Digital channel flows, action flows, notification flows |

[source: custom-connectors.md SS Custom Connectors vs. Webex Connect HTTP Nodes]

---

## Related References

- `docs/reference/flow-designer-activities/custom-connectors.md` — activity-level reference with field tables
- `docs/reference/flow-designer-activities/http-connector.md` — WxCC HTTP Connector (for WxCC APIs only)
- `docs/reference/flow-designer-activities/http-request.md` — HTTP Request activity (manual auth)
- `docs/playbooks/webex-api-auth.md` — all four auth patterns (HTTP Connector, Service App + Subflow, Custom Node, Custom Connector)
- `docs/reference/flow-designer-patterns.md` — Token Refresh Subflow Pattern, Scripted Agent Fulfillment Pattern
