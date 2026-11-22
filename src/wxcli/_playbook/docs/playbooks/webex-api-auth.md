# Calling Webex APIs from WxCC Flows

<!-- ref-tag: webex-api-auth-v1 -->

## Overview

WxCC flows often need to call Webex platform APIs (People, SCIM2, Calling, CJDS) that are outside the WxCC-managed scope. Standard WxCC Integrations don't support the OAuth methods these APIs require. This playbook covers three patterns for authenticating to Webex APIs from within your flows.

**Choose your pattern:**

| Pattern | Platform | Auth Lifecycle | Best For |
|---------|----------|----------------|----------|
| [HTTP Connector](#pattern-1-http-connector-flow-designer) | Flow Designer | Fully managed | WxCC APIs only (Search, CC Config) |
| [Custom Connector](#pattern-4-custom-connector-flow-designer) | Flow Designer | Fully managed | Third-party APIs with OAuth/Basic Auth (ServiceNow, Salesforce) |
| [Service App + Token Refresh Subflow](#pattern-2-service-app--token-refresh-subflow-flow-designer) | Flow Designer | Self-managed via subflow | Any Webex API from voice flows |
| [Custom Node with OAuth](#pattern-3-custom-node-with-oauth-webex-connect) | Webex Connect | Managed by Connect | Any Webex API from digital/action flows |

---

## Pattern 1: HTTP Connector (Flow Designer)

The simplest option when you only need WxCC's own APIs. The connector handles token lifecycle automatically.

**Limitation:** Only works with WxCC APIs (Search, CC Configuration). Cannot call People API, SCIM2, Calling APIs, or other Webex platform APIs.

Full reference: `docs/reference/flow-designer-activities/http-connector.md`.

---

## Pattern 2: Service App + Token Refresh Subflow (Flow Designer)

For calling any Webex API (People, SCIM2, Calling, CJDS) from a Flow Designer voice flow. Uses a Webex Service App for credentials and a reusable subflow that handles token refresh automatically.

### How It Works

```
Main Flow
  → HTTP Request (Webex API call, Bearer token from Global Variable)
  → Condition: httpStatusCode == 401?
      → TRUE: Call Subflow (RefreshTheToken)
              → Retry HTTP Request
      → FALSE: Continue (success path)

RefreshTheToken Subflow
  → HTTP Request (POST /access_token with refresh_token + client credentials)
  → Parse new access_token from response
  → HTTP Request (PUT Global Variable via WxCC CC Config API — updates stored token)
  → Return new access_token to main flow
```

### Prerequisites

| Requirement | Details |
|-------------|---------|
| Webex Service App | Created at developer.webex.com with required scopes |
| Service App authorized | Toggled ON in Control Hub > Apps > Service Apps |
| WxCC Global Variable | Stores the current access token |
| HTTP Connector (Read/Write) | For the subflow's PUT call to update the Global Variable |

### Step 1: Create a Webex Service App

1. Go to **developer.webex.com** → avatar menu → **My Webex Apps**
2. Click **Create a New App** → **Service App**
3. Configure:
   - **Name**: descriptive (e.g., "WxCC Flow API Access")
   - **Description**: purpose of the integration
   - **Contact email**: team or admin email
   - **Scopes**: select only what you need (e.g., `spark-admin:people_read` for People API)
4. Record the **Client ID** and **Client Secret**

> **Scope limits:** Service Apps have a maximum number of selectable scopes. Only request what your flows actually need.

### Step 2: Authorize the Service App

1. Go to **Control Hub** (admin.webex.com) → **Apps > Service Apps**
2. Search by **Client ID** (not name — the search only matches IDs)
3. Toggle the **Authorize** switch to ON
4. Refresh the page — an **Org Authorizations** section appears
5. Select your Org from the dropdown
6. Paste the Client Secret
7. Click **Generate** — copy both the **Access Token** and **Refresh Token**

> **Two places generate the tokens.** Cisco's help pages (fetched 2026-10-19) describe both: in
> Control Hub, "go to Apps > Service apps, select the application, and click Get a token >
> Authorize to get token" ([Synchronize Okta users into Control Hub](https://help.webex.com/en-US/article/nmm9pzdb/Synchronize-Okta-Users-into-Cisco-Webex-Control-Hub);
> "Token generation in Control Hub for service apps" is listed in
> [What's new in Control Hub](https://help.webex.com/en-us/article/u9dlxd/What-s-New-in-Cisco-Webex-Control-Hub), June 2026);
> and, once the app is authorized, the developer "can generate tokens through Developer Portal"
> (developer.webex.com → My Webex Apps → the app → Org Authorizations → **Generate Tokens**)
> [Owner: `authentication.md` § Step 3: Generate Tokens]. The button labels in steps 4–7 above
> were not re-checked against the current Control Hub UI.

### Step 3: Store Access Token in a Global Variable

1. Go to **Control Hub > Contact Center > Flows > Global Variables**
2. Create a new variable:
   - **Name**: `WEBEX_ACCESS_TOKEN` (or descriptive name for your use case)
   - **Type**: String
   - **Default Value**: paste the access token from Step 2
   - **Sensitive**: Yes (hides from logs and reports)
3. Save — note the variable **Name** and **ID** from the details page (needed for API updates)

### Step 4: Create the WxCC API Connector

The subflow needs a Read/Write connector to update the Global Variable via the CC Config API.

1. **Control Hub > Contact Center > Connectors**
2. Under **Webex Contact Center Connector**, click **Add More**
3. Configure:
   - **Name**: "WxCC API Access" (or similar)
   - **Access Level**: **Read/Write** (required for PUT operations)
4. Click **Authorize**

### Step 5: Build the Token Refresh Subflow

Create a subflow (reusable across all flows that call Webex APIs):

**Flow variables:**

| Variable | Type | Purpose |
|----------|------|---------|
| `client_id` | STRING | Service App Client ID |
| `client_secret` | STRING | Service App Client Secret |
| `refresh_token` | STRING | Service App Refresh Token |
| `global_var_id` | STRING | ID of the WEBEX_ACCESS_TOKEN Global Variable |
| `access_token` | STRING (output) | New access token returned to calling flow |

**Activity chain:**

```
Start
  → HTTP Request: "GetNewToken"
      Method: POST
      URL: https://webexapis.com/v1/access_token
      Content-Type: application/x-www-form-urlencoded
      Body: grant_type=refresh_token
            &client_id={{client_id}}
            &client_secret={{client_secret}}
            &refresh_token={{refresh_token}}
      Output: access_token (path: $.access_token)
  → HTTP Request: "UpdateGlobalVariable"
      Use Authenticated Endpoint: ON
      Connector: "WxCC API Access" (Read/Write)
      Method: PUT
      Request Path: /organization/{{orgId}}/cad-variable/{{global_var_id}}
      Body: { "defaultValue": "{{access_token}}", ... }
  → End (return access_token)
```

The `UpdateGlobalVariable` activity uses the CC Config API to overwrite the Global Variable's `defaultValue` with the fresh token. See `docs/reference/wxcc-platform.md` → WxCC Global Variables → API Access for the full PUT body schema.

> **Importable subflow:** The TeamCCEP community provides a pre-built subflow JSON at [github.com/TeamCCEP/teamccep.github.io](https://github.com/TeamCCEP/teamccep.github.io/tree/master/assets/files/WebexAPIFromWxCC). Import `subflow.json` into Flow Designer, then update the flow variables with your credentials and connector.

### Step 6: Build the Main Flow

Wire the subflow into your main flow with a 401-retry pattern:

```
NewContact
  → HTTP Request: "GetPersonDetails"
      Method: GET
      URL: https://webexapis.com/v1/people?email={{target_user}}
      Headers: Authorization = Bearer {{WEBEX_ACCESS_TOKEN}}
      Output: displayName, status, etc.
  → Condition: "HaveAccessToken"
      Expression: {{GetPersonDetails.httpStatusCode}} == 200
      → TRUE: Continue (use response data)
      → FALSE: Subflow "RefreshTheToken"
          Output mapping: access_token → WEBEX_ACCESS_TOKEN (Global Variable)
          → Retry HTTP Request (or route to fallback)
```

**Key wiring details:**
- The initial HTTP Request uses the Global Variable as the Bearer token
- The Condition checks for 200 (success) vs. 401 (token expired)
- On failure, the subflow refreshes the token and updates the Global Variable
- After refresh, retry the API call or continue with fallback logic

### Token Lifecycle Notes

| Concern | Detail |
|---------|--------|
| Access token lifespan | 14 days (OAuth tokens from Service Apps and Integrations) |
| Personal Access Token (PAT) lifespan | 12 hours — do not use in production |
| Refresh token lifespan | ~90 days — monitor and regenerate before expiry |
| Concurrent flows | Multiple flows reading the same Global Variable is safe; only the subflow writes |
| Rate limits | Webex token endpoint: respect 429 responses |
| Scope changes | If you add scopes to the Service App, re-authorize and generate new tokens |

### People API: callingData Query Parameter

When calling `GET /v1/people/{personId}`, you **must** include `?callingData=true` as a query parameter to receive calling-related fields. Without it, the following fields are **absent from the response entirely** — not null, not empty, just missing:

| Field | Requires callingData=true |
|-------|---------------------------|
| `locationId` | Yes — needed for Schedules API, location-based routing |
| `extension` | Yes — calling extension number |
| Calling-related `phoneNumbers` entries | Yes — work_extension type entries |

This is the single most common mistake with this API. Always include it:

```
GET https://webexapis.com/v1/people/{personId}?callingData=true
```

---

## Pattern 3: Custom Node with OAuth (Webex Connect)

For calling Webex APIs from Webex Connect flows (digital inbound, AI agent actions, notifications). Creates a reusable node with built-in OAuth that handles token refresh transparently.

### How It Works

Instead of raw HTTP Request nodes with manual Bearer tokens, you create a **Custom Node** backed by a Webex Integration. Connect manages the full OAuth lifecycle (authorization code grant, token refresh) — your flow just uses the node like any built-in node.

**Token refresh mechanism:** When you configure OAuth on the Custom Node, you set the **Refresh URL Token** and enable **"Access token has a limited validity"** with the token's lifespan. Connect tracks the token validity internally and automatically calls the Refresh URL Token endpoint to obtain a new access token when the current one expires. The official Cisco documentation for Email assets states: *"Token has a fixed expiry time and the backend application automatically calls the API to regenerate token before that."* The Custom Node docs do not specify whether this refresh is a background process or triggered at call time — treat it as platform-managed and opaque. Each refresh also resets the refresh token's 90-day expiry, so the integration stays authorized indefinitely as long as the refresh token is used before it expires. If no flow uses the Custom Node for 90+ days and the refresh token is not exercised, it expires and you must re-authorize via the browser popup.

**Re-authorization triggers:** If you edit the OAuth config in the admin portal, you will be prompted to re-authorize. If credentials are updated in the integrating system, Connect loses access and users must re-authorize manually. Existing integrations are not impacted until the Refresh Token expires or you decide to reauthorize.

[source: [Custom Node Integration](https://help.webexconnect.io/docs/custom-nodes); [Custom Nodes Integration](https://help.webexconnect.io/docs/custom-nodes-integration); [Email - WXCC](https://help.webexconnect.io/docs/wxcc-email-asset-creation)]

### Step 1: Create a Webex Integration

1. Go to **developer.webex.com** → avatar menu → **My Webex Apps**
2. Click **Create a New App** → **Integration**
3. Configure:
   - **Will this integration use a mobile SDK?**: No
   - **Redirect URI**: `https://oauth.us.webexconnect.io/callback`
   - **Scopes**: select what you need (e.g., `spark-admin:people_read`)
4. Record the **Client ID** and **Client Secret**

> **Region-specific callback URLs:** The redirect URI depends on your Connect data center. Don't guess — in Step 4 below, the **Call Back URL** field in the Custom Node OAuth config will show the correct URL for your region. Copy it from there and paste it here as the Redirect URI. Known regional patterns: `us` (Oregon/AWS), `us1` (USA/Azure), `eu` (Ireland), `uk` (London), `ca` (Canada), `in` (Mumbai), `au` (Sydney), `sg` (Singapore). Format: `https://oauth.[tenantName].[region].webexconnect.io/callback`.

### Step 2: Create the Custom Node

1. Go to **Control Hub → Contact Center → Webex Connect**
2. Navigate to **Assets → Integrations → Add Integration → Custom Node**

| Field | Value |
|-------|-------|
| **Creation type** | From blank (or copy an existing node) |
| **API Integration Type** | REST (or SOAP — use REST for Webex APIs) |
| **Node name** | Descriptive name (e.g., "Webex People Lookup") |
| **Description** | Optional — what this node does |
| **Node category** | Choose or create (e.g., "Webex APIs") |
| **Node icon** | Optional SVG file (64×64 pixels) |

### Step 3: Add a Request Method

A Custom Node supports **up to 25 methods** (from v5.6.0). Each method has its own independent authorization, URL, parameters, and response mapping — auth does NOT inherit between methods. When the node is placed on the flow canvas, the user selects which method to invoke via a **"Method Name" dropdown**.

Example: look up a person by email.

1. Click **Add Method**
2. Configure:
   - **Method name**: "GetPersonByEmail"
   - **Type**: GET
   - **Resource URL**: `https://webexapis.com/v1/people`
   - **Request Timeout**: 2000ms
   - **Connection Timeout**: 2000ms

### Step 4: Configure OAuth Authorization

In the method's **Authorization** section:

| Field | Value |
|-------|-------|
| **Type** | OAuth 2.0 |
| **Grant Type** | Authorization Code |
| **Consumer ID** | Your Integration Client ID (from Step 1) |
| **Consumer Secret** | Your Integration Client Secret (from Step 1) |
| **Call Back URL** | Auto-populated by Connect — copy this and register it as a Redirect URI in the Webex Integration at developer.webex.com |
| **Authorization URL** | `https://webexapis.com/v1/authorize` |
| **Scopes** | `spark-admin:people_read spark:kms` (space-separated) |
| **Access Token URL** | `https://webexapis.com/v1/access_token` |
| **Access Token URL Method** | POST |
| **Access Token URL Parameter type** | Body |
| **Access Token URL Headers** | Leave blank (not needed for Webex) |
| **Access token has a limited validity** | Checked (enabled) |
| **Validity** | `14` days (Webex OAuth access token lifespan) |
| **Refresh URL Token** | `https://webexapis.com/v1/access_token` |
| **Client Authentication** | Send client credentials in body (default — correct for Webex) |

After filling in these fields, click **Authorize** (or **Get Access Token**). Here is what happens:

1. A **browser popup** opens and navigates to the Authorization URL (the Webex login page)
2. Sign in with your Webex account (if not already logged in)
3. A **scope consent screen** appears showing the requested permissions — click **Accept**
4. The popup redirects to the Call Back URL (handled by Connect's server) and **closes automatically**
5. Back in the Custom Node config, the **Access Token** and **Refresh Token** fields auto-populate — this confirms authorization succeeded

If the popup doesn't appear, check that your browser allows popups for the Connect domain. If authorization fails, the Webex error message is displayed in the popup.

> **Grant Type — why Authorization Code:** Webex APIs (People, SCIM2, Calling) only support Authorization Code grant — they do not accept `grant_type=client_credentials`. If you select Client Credentials, the Webex token endpoint will reject the request. Client Credentials is only for third-party APIs that explicitly support it (e.g., some ServiceNow or Salesforce configurations).
>
> **Client Authentication options:** Two choices — "Send client credentials in body" (default, sends `client_id`/`client_secret` as POST body params) or "Send as Basic Auth header" (sends `Authorization: Basic <base64>` header). Webex supports both; use the default — all Cisco examples send credentials in body.
>
> **`spark:kms` scope:** Required for key management. Always include it alongside your functional scopes.
>
> **Validity field:** This tells Connect when to refresh. Set it to match the actual access token lifespan (14 days for Webex OAuth tokens).
>
> **Refresh URL Token:** Connect uses this endpoint to obtain a new access token when the current one expires. For Webex, it's the same endpoint as the Access Token URL.
>
> **Call Back URL — regional variations:** Auto-populated based on your Connect data center. Pattern: `https://oauth.[tenantName].[region].webexconnect.io/callback`. Known regions: `us` (Oregon/AWS), `us1` (USA/Azure), `eu` (Ireland), `uk` (London), `ca` (Canada), `in` (Mumbai), `au` (Sydney), `sg` (Singapore). Register this exact URL as a Redirect URI in the Webex Integration at developer.webex.com.
>
> **Callback URL note:** The callback URL is not accessible through a web browser. You can only test it by executing the Custom Node in a flow.

### Step 5: Configure Security (Optional)

If the target API requires mutual TLS or a specific SSL/TLS version:

**Key Store** (client certificate):

| Field | Value |
|-------|-------|
| **Browse Certificate** | Upload your key store certificate file |
| **Select File Format** | JKS or PKCS12 |
| **Store Password** | Password to access the store |
| **Key Password** | Password to access the key |
| **Name** | Descriptive name for the certificate |

**Trust Store** (server certificate): same fields minus Key Password.

**Security Protocol:** Select TLS 1.2 (recommended).

> For standard Webex API calls, skip this step — no client certificates needed.

### Step 6: Define Header Parameters

Add any custom headers the API requires beyond what OAuth provides:

| Parameter | Parameter Value Type | Value / Field Name |
|-----------|---------------------|-------------------|
| `Content-Type` | Static | `application/json` |

- **Static** parameters have a fixed value set here
- **Dynamic** parameters create an input field on the node — the flow passes a value at runtime

> The `Authorization: Bearer <token>` header is injected automatically by Connect — do not add it manually.

### Step 7: Define URL Parameters

Add query parameters the method needs:

| Parameter | Parameter Value Type | Value / Field Name |
|-----------|---------------------|-------------------|
| `email` | Dynamic | Field name: "email" (passed from flow at runtime) |
| `callingData` | Static | Value: "true" (always include calling details) |

### Step 8: Configure Request Body (POST/PUT/PATCH Only)

If the method is POST, PUT, or PATCH:

| Field | Value |
|-------|-------|
| **Body format** | JSON (`application/json`), XML (`application/xml`), Text (`text/plain`), or form-data |
| **Parameters** | Add body fields as Static or Dynamic (same pattern as URL/header parameters) |

Skip this step for GET and DELETE methods.

### Step 9: Configure Node Events

Define success/error routing — these become the output ports on the node:

| Event | Condition |
|-------|-----------|
| **Success** | HTTP Status equals 200 |
| **Error** | HTTP Status not equals 200 |

### Step 10: Define Response Object

| Field | Value |
|-------|-------|
| **Response Format** | JSON (or Text/XML depending on API) |
| **Parameter name** | Descriptive name (e.g., "Person") |
| **Body** | Body (also supports HTTP Status or HTTP Header) |
| **Response Path** | `$.items[0]` (first array element) or `$` (whole response) |

The output is available downstream as the node's variable (e.g., `$(n3.person)` where `n3` is the node number).

### Step 11: Configure Throttling (Optional)

Protect the target API from overload:

| Field | Value |
|-------|-------|
| **Rate Limit** | Max requests per second |
| **Concurrency Limit** | Max parallel Custom Node executions |
| **Volume Limit** | Max Custom Node executions within a time period |

Set these based on the target API's rate limits.

### Step 12: Configure Node UI (Optional)

Customize how the node's input fields appear in the flow editor:

| Field | Value |
|-------|-------|
| **Information Text** | Description shown in the node config dialog |
| **Field Type** | Text box, Selection box, or Date and time |
| **Regex Validation** | Validation string for text inputs |
| **Mandatory Parameter** | Whether the field is required |
| **Tooltip** | Help text shown on hover |

### Step 13: Activate and Use

1. Save the Custom Node configuration
2. Back in **Assets → Integrations**, find your node — it is **OFF by default**
3. **Toggle it ON** — otherwise the node won't appear in the flow palette
4. In any Connect flow, drag the Custom Node from the palette
5. Select the **request method** (e.g., "GetPersonByEmail")
6. Fill in any **dynamic parameters** (using the variable picker or hardcoded values)
7. Wire the **Success** and **Error** outputs to downstream nodes

### Using the Response in an Evaluate Node

```javascript
const person_json = JSON.parse("$(n3.person)");
const person_name = person_json.displayName;
const person_status = person_json.status;
```

### Testing the Custom Node

To validate the Custom Node before wiring it into a production flow:

1. Create a test flow with a **webhook-triggered Start node** — this generates a unique webhook URL
2. Wire: Start → Custom Node → Evaluate (parse response) → End
3. In Postman or curl, **POST an empty JSON body `{}`** to the webhook URL to trigger the flow
4. In Webex Connect, open the flow's **debug logs** (decrypt if needed) and inspect the Custom Node output to confirm the response shape and field extraction

> The callback URL configured in OAuth is not accessible through a web browser. You can only test it by executing the Custom Node in a flow.

### Troubleshooting Custom Node OAuth

| Symptom | Cause | Fix |
|---------|-------|-----|
| Integration shows **"Auth Pending"** or **"re-authorize"** status | Access token and refresh token both expired, OR credentials updated at developer.webex.com | Navigate to **Assets → Integrations** → select the Custom Node → re-authorize (triggers the OAuth popup again) |
| Custom Node returns HTTP 401 at runtime | Access token expired and refresh failed | Re-authorize the integration. Verify the Refresh URL Token is correct and the refresh token hasn't exceeded its 90-day lifespan |
| OAuth popup doesn't appear | Browser popup blocker | Allow popups for the Connect domain |
| Popup shows Webex error | Incorrect Consumer ID/Secret, wrong scopes, or redirect URI mismatch | Verify Consumer ID and Secret match the Integration at developer.webex.com. Verify scopes match. Verify the Call Back URL is registered as a Redirect URI in the Integration |
| HTTP 429/430/431 at runtime | Rate/concurrency/volume limit exceeded | Adjust Throttling settings on the Custom Node, or reduce request frequency |
| Custom Node not in flow palette | Integration is toggled OFF | **Assets → Integrations** → toggle ON |

> **No proactive token monitoring:** Cisco does not provide email notifications or dashboard alerts for OAuth token expiry on Custom Nodes. Certificate expiry (mTLS) has email alerts at 30/15/7/3/2/1 days before expiry, but OAuth tokens do not. Test flows periodically or check integration status in Assets → Integrations.

---

## Which Pattern Should I Use?

| Question | Answer |
|----------|--------|
| Calling WxCC-only APIs from Flow Designer? | Pattern 1 (HTTP Connector) — simplest, fully managed |
| Calling any Webex API from a voice flow? | Pattern 2 (Service App + Refresh Subflow) — handles token lifecycle |
| Calling any Webex API from a Connect flow? | Pattern 3 (Custom Node) — OAuth managed by Connect |
| Need to call the same API from both platforms? | Use Pattern 2 for Flow Designer + Pattern 3 for Connect |
| One-off test or prototype? | A Personal Access Token (PAT) from developer.webex.com works for 12 hours — don't use in production |

---

## Pattern 4: Custom Connector (Flow Designer)

For calling **third-party APIs** (not Webex APIs) from Flow Designer flows with managed OAuth or Basic Auth. The connector handles token lifecycle automatically — no subflow or manual refresh needed.

**Scope:** External services only (ServiceNow, Salesforce, custom backends). For Webex platform APIs, use Pattern 1 (WxCC APIs) or Pattern 2 (other Webex APIs).

### Setup

1. **Control Hub → Contact Center → Connectors → Custom Connectors → Add More**
2. Configure name, authentication type (Basic Auth or OAuth 2.0), and credentials
3. For OAuth 2.0: set Grant Type (Client Credentials or Password Grant), Token URL, Client ID/Secret, Scopes
4. In Flow Designer HTTPRequest activity: enable **Use Authenticated Endpoint**, select the custom connector

Full reference: `docs/reference/wxcc-platform.md` → Custom Connectors section.

---

## Common Scopes Reference

| API | Scope | Used For |
|-----|-------|----------|
| People API (read) | `spark-admin:people_read` | Look up user details by email/ID |
| People API (write) | `spark-admin:people_write` | Update user profiles |
| SCIM2 API | `identity:people_read` | Search users with extended attributes |
| Calling API (write) | `spark:calls_write` | Initiate calls, manage paging |
| Calling Config API (read) | `spark-admin:telephony_config_read` | Read schedules, locations, telephony settings |
| CJDS (read) | `cjds:admin_org_read` | Read journey events and profiles |
| CJDS (write) | `cjds:admin_org_write` | Write events, manage identities |
| CC Config API | `cjp:config_read` / `cjp:config_write` | Read/update Global Variables, queues, etc. |
| **CC agent runtime** | **`cjp:user`** | The `@webex/contact-center` JS SDK (`register`, `stationLogin`, `setAgentState`, call control) and `PATCH /v1/tasks/{taskId}`. Acts as **one specific agent at their station**, not as a tenant admin [Owner: `contact-center-agent-sdk.md` § 10] |
| Key Management | `spark:kms` | Required alongside other scopes for encrypted content |

> **`cjp:config_*` and `cjp:user` are different families — do not substitute one for the other.**
> A **Personal Access Token does carry `cjp:user`** (verified live 2026-07-31 driving
> `register()`, `stationLogin()` and `setAgentState()` against a live tenant), so a PAT is
> enough to run a custom agent desktop. A full-admin PAT also reached the CC config endpoints
> (verified live on the sandbox tenant: on 2026-10-13 `cc-flow`, `cc-queue list`,
> `cc-entry-point list` and `cc-global-vars list-cad-variable` returned 200; on 2026-10-19 a
> full-admin PAT read `cc-global-vars list-cad-variable` and created, read and deleted a team,
> a queue, an entry point, a global variable and flows), so a
> 403 on a `cjp:config_*` endpoint means the token lacks those scopes, not that every PAT is
> refused; a PAT from a user with fewer roles was not tested [Owner: `contact-center-core.md`
> § 25 Gotchas, gotcha 23]. (Before 2026-10-19 this note said a PAT returns 403 "on every
> `cjp:config_*` endpoint"; that 2026-04 observation did not reproduce.) The reverse also holds: a Service App with full CC config scopes cannot act as an
> agent. Note `spark:kms` is **not** available to Service Apps, so a custom desktop — which
> needs it for media — requires a per-agent OAuth integration rather than a Service App
> [Owner: `contact-center-agent-sdk.md` § 10].

---

## References

- [TeamCCEP: Webex API From WxCC](https://teamccep.github.io/pages/WebexAPIFromWxCC/) — original guide with importable Flow Designer JSONs
- [Importable subflow/mainflow JSON](https://github.com/TeamCCEP/teamccep.github.io/tree/master/assets/files/WebexAPIFromWxCC) — pre-built refresh subflow for Pattern 2
- `docs/reference/flow-designer-activities/http-connector.md`
- `docs/reference/wxcc-platform.md` → Global Variables API
- `docs/reference/webex-connect.md` → Custom Nodes section
- `docs/playbooks/cjds-integration.md` → Service App setup for CJDS-specific scopes
