# Webex Contact Center (WxCC) -- Platform Reference

<!-- ref-tag: wxcc-platform-v5 -->

## Architecture Overview

The routing chain in WxCC is:

```
Entry Point -> Flow (Flow Designer) -> Queue -> Team -> Agent
```

Entry Points do NOT connect directly to Queues. A Flow Designer flow always sits in between, handling the AI agent interaction and routing logic.

---

> Flow Designer activities are split across two files: essentials in [flow-designer-essentials.md](flow-designer-essentials.md), situational activities in [flow-designer-activities/_index.md](flow-designer-activities/_index.md). Patterns and advanced topics are in [flow-designer-patterns.md](flow-designer-patterns.md).


## Control Hub Prerequisites

Log into **Webex Control Hub** (admin.webex.com) with an admin account that has WxCC entitlements.

### User Activation Prerequisite

Users must click their activation email and create a password (unless SSO is configured) before they appear in WxCC user lists. A user who is licensed but hasn't activated will not be available for team assignment or agent login. Common gotcha on new deployments.

### Site Setup

- Navigate to **Contact Center > Settings > General**
- Confirm a Site is provisioned (e.g., "Default Site")
- If no site exists, contact your Cisco partner to provision one
- Sites are organizational units -- most deployments use a single default site

### Create a Team

1. **Contact Center > Teams > Add Team**
2. Fill in:
   - **Team Name**: descriptive name (e.g., "Support Agents")
   - **Site**: select provisioned site
   - **Type**: Agent-Based
3. Save

Teams contain the human agents who receive escalated calls from the AI agent.

### Create a Queue

1. **Contact Center > Queues > Add Queue**
2. Fill in:
   - **Name**: descriptive name (e.g., `Support_Queue`)
   - **Channel Type**: Telephony (for voice) or Chat (for digital)
   - **Routing Type**: Longest Available Agent (most common)
3. Under **Team Assignment**, add the team created above
4. Save

The queue holds contacts waiting for an available agent. It must have at least one team with agents assigned.

> **Routing Type is immutable.** Once a queue is created, its Routing Type (Longest Available Agent, Skills Based, etc.) cannot be changed. If you need a different routing type, delete and recreate the queue.

### Create an Entry Point

1. **Contact Center > Entry Points > Add Entry Point**
2. Fill in:
   - **Name**: descriptive name (e.g., `Main_Voice_EP`)
   - **Channel Type**: Telephony (or Chat, SMS)
   - **Service Level Threshold**: target answer time in seconds (e.g., 60)
3. Save -- note the Entry Point ID (shown in the URL)

### Assign a PSTN Number

1. **Contact Center > Phone Numbers**
2. Click an unassigned number
3. Assign to the Entry Point created above
4. Save

This is the phone number callers dial to reach your AI agent.

---

## CCAI Config (Google CCAI / BYOVA / Agent Answers)

> ⚠ **If you are building a Webex AI Agent, you are in the wrong section.** CCAI (Contact Center AI) is **Google's** product; Webex AI Agent is Cisco's own — they are different things. This procedure creates a Contact Center AI configuration for the **Google CCAI / BYOVA (Bring Your Own Virtual Agent) / Agent Answers** integration only. A Webex AI Agent has **no Control Hub creation step at all**: you publish the agent in AI Agent Studio, then *select* "Webex AI Agent Autonomous" or "Webex AI Agent Scripted" from the **Contact Center AI Config** drop-down in the Flow Designer **Virtual Agent V2** activity. For that path go to [`ai-agent-studio.md` § CCAI Config (Linking Agent to WxCC)](ai-agent-studio.md), and see § Webex AI Agent Tenant Prerequisite below. Confirmed by the platform owner 2026-07-27.

**Prerequisite:** "Ensure that the service-specific integration connector is created. For example, **Google** Contact Center AI connector" [source: [Create a Contact Center AI configuration](https://help.webex.com/en-us/article/npbt02j/Create-a-Contact-Center-AI-configuration)].

1. **Control Hub > Services > Contact Center > Tenant settings > Integrations > Features tab > New > Contact Center AI Config**
2. **Contact Center AI Connector** — the field offers exactly three options: **Webex CCAI**, **Integration Connector**, **Service App**. There is **no** Webex AI Agent option in this field.
3. **Feature** — the choices are **Agent Answers** or **Virtual Agent**.
4. Name the config descriptively
5. Save
6. Reference this CCAI Config in the Virtual Agent V2 node in Flow Designer

The navigation path above is verbatim from [Create a Contact Center AI configuration](https://help.webex.com/en-us/article/npbt02j/Create-a-Contact-Center-AI-configuration) (Cisco page last updated November 03, 2025; verified 2026-07-27). "CCAI Config" is Cisco's prose shorthand — the UI label is **Contact Center AI Config**.

The remaining fields on this form are not documented in the WxCC platform reference — see the Cisco article cited above.

If your virtual agent doesn't appear in this form's dropdowns, check that the service-specific integration connector named in the prerequisite above exists.

If instead you are looking for why **Webex AI Agent Autonomous** / **Webex AI Agent Scripted** is missing from a Virtual Agent V2 **Contact Center AI Config** drop-down, that is a different problem — see § Webex AI Agent Tenant Prerequisite below, and confirm the agent is published in AI Agent Studio.

---

## Webex AI Agent Tenant Prerequisite

Before **Webex AI Agent Autonomous** and **Webex AI Agent Scripted** appear as selectable entries in the **Contact Center AI Config** drop-down of the Flow Designer **Virtual Agent V2** activity, a **one-time tenant enablement is required**. Confirmed by the platform owner (2026-07-27).

**What it gates:** those two drop-down entries, and nothing else. Until the enablement is done, a published AI Agent Studio agent cannot be attached to a voice flow, because the entries are simply absent from the drop-down.

**There is no Control Hub toggle for this — all three gates below are Cisco-side.** Verified against Cisco 2026-07-27.

| # | Gate | Cisco's exact wording |
|---|---|---|
| 1 | **Purchased entitlement** | "To sign up for subscription, customers need to purchase the AI Agent add-on for the Flex-3.0 Contact Center license. Based on entitlements, Webex Contact Center provisions AI Agent as one of its services for an organization." |
| 2 | **Cisco-side feature flag** | "If you don't see **Webex AI Agent**, contact Cisco Support to enable the corresponding feature flag." |
| 3 | **Autonomous-on-voice only — an extra approval** | "Access to the autonomous AI agent for the voice calls is currently limited to specific customers. For more information, please reach out to Cisco support." |

Gates 1 and 2: [source: [Webex AI Agent Studio Administration guide](https://help.webex.com/en-us/article/ncs9r37/Webex-AI-Agent-Studio-Administration-guide) § Prerequisites and § Access Webex AI Agent Studio]. Gate 3: [source: [Use AI agents for customer interactions](https://help.webex.com/en-us/article/s0qro1/Use-AI-agents-for-customer-interactions)].

⚠ **Gate 3 is the one that catches people building autonomous voice agents** — scripted carries no equivalent restriction, so `Webex AI Agent Scripted` may appear in the drop-down while `Webex AI Agent Autonomous` does not. That asymmetry is documented by Cisco, not inferred.

**Self-check before you build:** sign in to Control Hub → **Services > Contact Center**, and look in the navigation pane for **Customer experience > AI Agent**. If that item is missing, the tenant is not enabled — raise a case with Cisco Support before going further.

**Ordering:** tenant enabled → AI Agent Studio reachable → agent created → agent **published** → agent selectable in Virtual Agent V2. Cisco is explicit that publishing is required: "Select one of the **published** scripted agents under the Virtual Agent drop-down list" [source: s0qro1].

⚠ **Still not documented by Cisco (O11a):** the AI Agent **SKU part number** — public collateral names the add-on only descriptively ("AI Agent units under the Collaboration Flex 3.0 Contact Center Offering"), and the Flex Plan Contact Center Ordering Guide that carries part numbers is behind a login. Note the contrast: Cisco *does* publish `A-FLEX-AI-ASST` for the sibling AI Assistant add-on. Also **inferred, not stated**: Cisco never writes a sentence directly linking these gates to those two drop-down entries appearing. The gates are what Cisco documents as controlling access to Webex AI Agent overall; the causal link to the drop-down is our reading, consistent with the platform owner's account. Tracked in [`docs/plans/2026-07-25-documentation-remediation-backlog.md`](../plans/2026-07-25-documentation-remediation-backlog.md).

**This is NOT the Google CCAI Config creation covered above.** § CCAI Config (Google CCAI / BYOVA / Agent Answers) creates a configuration for **Google's** CCAI product; its Contact Center AI Connector field offers no Webex AI Agent option, and running it does not satisfy this prerequisite. Conversely, satisfying this prerequisite involves no Control Hub Contact Center AI Config creation step.

---

## Digital (Chat/SMS) Channel Setup

### Digital Channel Entry Point

1. **Contact Center > Entry Points > Add Entry Point**
2. Channel Type: Chat (or SMS)
3. Assign a Webex Connect Service (links WxCC to your Connect organization)

### Digital Flow in Flow Designer

1. Create a new flow using an **AI Agent** node (NOT Virtual Agent V2 -- that's voice only)
2. Connect to **Queue Task** on escalation (not Queue Contact -- that's voice only)
3. Publish and link to the digital entry point

### Webex Connect for Digital

- The actual inbound handler for digital channels lives in Webex Connect, not WxCC Flow Designer
- Connect flow routes to the AI Agent, then optionally escalates via Queue Task API call

---

## Built-in Escalation

The "Talk to an agent" intent is **built-in** to AI Agent Studio. No custom configuration is needed. When a caller says something like "let me talk to a person," the agent automatically triggers the `Escalated` output on the Virtual Agent V2 node.

---

## Agent Desktop

Human agents who receive escalated calls use the Webex Contact Center agent desktop.

1. Agents log in at the region-specific URL:
   | Region | URL |
   |--------|-----|
   | US | `https://desktop.wxcc-us1.cisco.com/` |
   | EU1 | `https://desktop.wxcc-eu1.cisco.com/` |
   | EU2 | `https://desktop.wxcc-eu2.cisco.com/` |
2. Agent must be assigned to the team linked to the queue
3. Agent sets status to **Available** to receive contacts
4. When a contact is queued, the desktop rings for available agents

---

## Testing Voice End-to-End

1. Dial the PSTN number assigned to your Entry Point
2. Flow routes to Virtual Agent V2, which connects to your AI agent
3. AI agent answers and handles the conversation
4. If the caller says "talk to an agent," call escalates to the queue
5. Agent desktop rings for available agents in the assigned team

---

## Webex Connect API Limitations

Webex Connect does **not** expose a public REST API for flow CRUD operations. All flow management is UI-only.

| Capability | Available? | Notes |
|-----------|-----------|-------|
| Create/edit/delete flows | UI only | No REST API |
| Export/import flows as JSON | UI only | Schema is undocumented |
| Trigger a flow programmatically | Yes | Custom Event API or Inbound Webhooks |
| List/read flow definitions | No | Not exposed via API |
| WxCC Flow Designer APIs | Yes | List, export, import, publish — see [Flow Designer Management API](flow-designer-patterns.md#flow-designer-management-api) |
| SDK or CLI for flow management | No | Does not exist |

---

## Create Task API

Programmatically creates a WxCC task, optionally placing an outbound call that runs through its own flow. Used to start a second, parallel call leg while an existing flow keeps handling the original caller.

**Endpoint:** `POST https://api.wxcc-{region}.cisco.com/v1/tasks`

**Headers**

| Header | Value |
|--------|-------|
| `Authorization` | `Bearer {token}` |
| `Content-Type` | `application/json` |
| `Accept` | `application/json` |

**Request body**

```json
{
  "outboundType": "OUTDIAL",
  "destination": "+1XXXXXXXXXX",
  "entryPointId": "{outbound-entry-point-uuid}",
  "mediaType": "telephony",
  "origin": "+1XXXXXXXXXX",
  "attributes": {
    "dept_name": "Electronics"
  }
}
```

| Field | Description |
|---|---|
| `outboundType` | `OUTDIAL` for outbound voice calls. `EXECUTE_FLOW` creates a task but does **not** place an outbound call — the flow starts but stops at NewPhoneContact because no media channel exists. `CALLBACK` requires callback-specific entry point configuration |
| `destination` | The number to dial. Accepts E.164 (`+12095551234`) and extensions (`1613`) |
| `entryPointId` | UUID of an **outbound** entry point. `OUTDIAL` requires an outbound EP; `EXECUTE_FLOW` requires an inbound EP |
| `mediaType` | `telephony` for voice calls |
| `origin` | Outdial ANI in E.164 format. **Must include the `+` prefix** — without it the API returns "Invalid origin." Must be configured as an Outdial ANI in Control Hub |
| `attributes` | Key-value pairs passed to the triggered flow. Use to pass department name, paging extension, or other dynamic data |

### `outboundType` Comparison

| Type | Entry Point | Places call? | Flow runs? | Use case |
|---|---|---|---|---|
| `OUTDIAL` | Outbound EP | Yes | Yes | Agent-assisted or automated outbound calls |
| `EXECUTE_FLOW` | Inbound EP | No | Partial (stops at start) | Digital channel flows, not telephony |
| `CALLBACK` | Callback-configured EP | Yes | Yes | Web callbacks to customers |

### OUTDIAL Entry Point Requirements

All four must be configured or the Create Task API returns a 500 Analyzer error:

- **Outdial queue** created and associated with the outbound entry point
- **Team** assigned to the outdial queue
- **Flow** published and assigned to the outbound entry point
- **Outdial ANI** configured at Control Hub → Contact Center → Outdial ANI

---

## WxCC Global Variables

Defined in **Control Hub > Contact Center > Flows > Global Variables**. Available across all WxCC Flow Designer flows in the org.

### Native Access (Flow Designer)

- Available in Flow Designer flows natively — use the variable picker
- Used for reporting in WxCC Analyzer
- Can be marked as **Sensitive Information** to restrict from logs/reports
- Cannot be added directly to sub-flows — must map from main flow to local variable

### API Access (Connect or External)

Global Variables are fully CRUD-able via the CC Configuration API. This means Webex Connect flows can read and write them using the HTTP Request node, and external systems (web portals, scripts) can update them via standard REST calls.

**Base URL (region-specific):**

| Region | Base URL |
|--------|----------|
| US | `https://api.wxcc-us1.cisco.com` |
| EU | `https://api.wxcc-eu1.cisco.com` |
| CA | `https://api.wxcc-ca1.cisco.com` |
| JP | `https://api.wxcc-jp1.cisco.com` |
| SG | `https://api.wxcc-sg1.cisco.com` |

The five rows above are not the full list: `eu2` (EU) and `anz1` (APJC) also exist — Cisco's Salesforce-integration help page (fetched 2026-10-19) names 7 codes, `us1`, `ca1`, `eu1`, `eu2`, `anz1`, `jp1`, `sg1`, the same 7 `wxcli set-cc-region` offers [owner: `contact-center-core.md` § API Base and Authentication].

**Endpoints:**

| Operation | Method | Path |
|-----------|--------|------|
| Create | POST | `/organization/{orgId}/cad-variable` |
| Get by ID | GET | `/organization/{orgId}/cad-variable/{id}` |
| Update | PUT | `/organization/{orgId}/cad-variable/{id}` |
| Delete | DELETE | `/organization/{orgId}/cad-variable/{id}` |
| List all | GET | `/organization/{orgId}/v2/cad-variable` |
| Bulk save | POST | `/organization/{orgId}/cad-variable/bulk` |
| Bulk export | GET | `/organization/{orgId}/cad-variable/bulk-export` |

**Auth scopes:** `cjp:config_read` (GET), `cjp:config_write` (PUT/POST/DELETE). These are CC-specific OAuth scopes, different from People API or Calling API scopes.

**Key fields on a Global Variable:**

| Field | Required | Notes |
|-------|----------|-------|
| `name` | Yes | Variable name |
| `variableType` | Yes | Title case: `String`, `Integer`, `Boolean`, `Decimal`, `DateTime`. Verified live 2026-10-19: `"String"` created a variable and every stored variable reads `String`; `"STRING"` → 400 (the 400 names `defaultValue`). The other four spellings are from `--help` (which also lists `DATE_TIME`) and were not sent [owner: `contact-center-core.md` § 25 Gotchas, gotcha 21]. Before 2026-10-19 this row listed `STRING`, `INTEGER`, `DATE_TIME`, `BOOLEAN`, `DECIMAL` |
| `defaultValue` | Yes | The stored value — this is what you read/update |
| `active` | Yes | Must be `true` for flows to use it |
| `agentEditable` | Yes | Whether agents can edit in Agent Desktop |
| `agentViewable` | Yes | Whether agents can see in Agent Desktop |
| `reportable` | Yes | Whether it appears in WxCC Analyzer reports |
| `description` | No | Human-readable description |
| `sensitive` | No | Hides value from logs/reports |

**Pattern: Lightweight data store from Connect**

A Global Variable with `variableType: String` (title case; the live API rejects `STRING` with a 400, verified 2026-10-19 — before that date this line said `STRING`) can store any text value (CSV lists, JSON, configuration strings). Connect flows read it via HTTP Request (GET), parse in an Evaluate node, and use the values downstream. External systems (web portals, SMS flows, scripts) update it via HTTP Request (PUT). This eliminates the need for an external database for simple key-value configuration.

### Flow Import Gotcha

Flow Designer allows importing a flow that references a Global Variable that does not exist in the target org. The import succeeds silently, but the flow will fail at runtime when it tries to read the missing variable. After importing any flow that uses Global Variables, verify the variables exist in **Control Hub > Contact Center > Flows > Global Variables** and re-map them if needed.

### Analyzer Reporting Integration

Global Variables with `reportable: true` automatically appear in **WxCC Analyzer** as **Contact Session Record (CSR) custom fields**. This is the primary mechanism for tracking custom business data across flow executions.

#### How It Works

1. Create a Global Variable in Control Hub with `reportable: true`
2. Add it to your flow via the Global Properties pane
3. Set its value during flow execution (via Set Variable activity)
4. After the call ends, the value is written to the Contact Session Record
5. In Analyzer, the variable appears as a custom field available for filtering, grouping, and visualization

#### Common Reportable Variables

| Variable Name | Type | Set When | Reports On |
|---------------|------|----------|------------|
| `CustomAIAgentInteractionOutcome` | STRING | Each exit path (HANDLED, ESCALATED, ERRORED, ABANDONED) | AI agent resolution rate |
| `AB_Test_Path` | STRING | After Percentage Allocation branch | A/B test segment comparison |
| `Self_Service_Duration` | INTEGER | Before Queue Contact or Disconnect | Time spent in self-service |
| `Virtual_Agent_Contained` | BOOLEAN | After Virtual Agent V2 exit | Whether the bot resolved without escalation |
| `Flow_Version_Used` | STRING | Flow start (from `NewContact.FlowVersionLabel`) | Which version label served the call |

#### Custom Visualization in Analyzer

To build custom reports on these variables:

1. Open **WxCC Analyzer** (from Control Hub or direct URL)
2. Navigate to **Visualization > Create Custom Visualization**
3. Select **Contact Session Records** as the data source
4. Your reportable Global Variables appear as available fields
5. Use them as filters, row segments, or measures

Example: Create a bar chart comparing `HANDLED` vs. `ESCALATED` vs. `ERRORED` counts by grouping on `CustomAIAgentInteractionOutcome` — shows AI agent containment rate at a glance.

#### A/B Test Reporting Pattern

Combine Percentage Allocation with reportable Global Variables to measure experiment outcomes:

```
Percentage Allocation
  ├── 50% Path A → Set Variable (AB_Test_Path = "control")
  │                → [existing IVR] → Set Variable (Self_Service_Duration = elapsed)
  └── 50% Path B → Set Variable (AB_Test_Path = "experiment")
                   → [new bot] → Set Variable (Self_Service_Duration = elapsed)
```

In Analyzer, filter by `AB_Test_Path` and compare `Self_Service_Duration`, escalation rate, and CSAT between the two groups.

#### Sensitive Data

Variables marked `sensitive: true` are excluded from Analyzer reports and flow debug logs. Use this for PII (phone numbers, account IDs) that shouldn't appear in reporting dashboards. A variable cannot be both `reportable` and `sensitive` — sensitive overrides reportable.

### Distinction from Connect Variables

WxCC Global Variables and Webex Connect flow variables are **separate systems**. A Global Variable defined in Control Hub is natively accessible in Flow Designer flows. In Webex Connect flows, access it via the CC Configuration API using an HTTP Request node.

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Call drops immediately | Flow not published or not linked to entry point | Publish the flow; assign it to the entry point |
| Virtual agent doesn't respond | CCAI Config not linked to Virtual Agent V2 node, or AI agent not deployed | Verify CCAI Config and deploy status |
| Escalation doesn't ring agents | Team not assigned to queue, or no agents Available | Check team-queue assignment; verify agent status |
| "No agents available" message | No agents logged in, or all agents busy | Have agents log in and set status to Available |
| Caller hears silence then disconnect | Flow Designer validation error | Open flow, click Validate, fix errors, re-publish |
| Digital channel not routing | Connect Service not linked to entry point | Assign Webex Connect Service to the digital entry point |
| AI agent answers but actions don't work | Action not bound to a Webex Connect Service + Flow, action disabled, or the Connect flow isn't live | In AI Agent Studio, open each action and confirm a Webex Connect **Service** and a **Flow** are both selected (you pick each manually from a dropdown — names do not need to match anything); confirm the action's **Enable** toggle is ON; confirm the Connect flow is published/live ([Cisco: Configure fulfilment flows for AI Agent actions](https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions)) |
| HTTP Request after Queue Contact returns empty data | Queue Contact hasn't finished processing when HTTP fires | Add a **Play Message** or **Play Music** activity between Queue Contact and HTTP Request to introduce a short delay |
| HTTP Request returns 429 from WxCC API | Flow Designer API calls are rate limited | Use a Case activity to detect 429 and route to a fallback path; create Read-only connectors for GET-only flows |
| HTTP Connector not appearing in HTTPRequest dropdown | Connector not authorized or wrong admin role | Navigate to Contact Center → Connectors and verify connector status; requires Full Admin, External Admin (Full Access), or CC Service Admin |
| HTTP Request returns "is not a valid HTTP URL" | Leading or trailing space in the Request URL field | Open the HTTP Request node and remove any whitespace before `https://` or after the URL |
| HTTP Request returns 401 on second/third API call but first call works | Headers don't carry over between HTTP Request nodes | Each HTTP Request node needs its own `Authorization` header configured — copy the header config to every node that calls the same API |
| Global_Language not appearing in Set Variable dropdown | Global Variable not added to the flow | Open Global Properties pane (cog icon in zoom toolbar) → Add Global Variable → select `Global_Language` and `Global_VoiceName` |

---

## Day 1 Tenant Hardening

After initial provisioning, a fresh WxCC tenant has default settings that need tuning before production use. These settings are separate from the AI agent configuration.

### Desktop Settings (Tenant Settings > Desktop)

| Setting | Recommended Value | Purpose |
|---------|-------------------|---------|
| **Inactivity Timeout** | Enabled, **480 minutes** | Auto-logout idle agents |
| **End Call** | **ON** | Allows agents to end calls from desktop |
| **RONA Timeout (Telephony)** | **12 seconds** | Ring No Answer — how long before re-routing to next agent |
| **Webex App State Sync** | **ON** | Syncs Webex App calling state to agent idle codes |
| **On a Call mapping** | Map to "On Phone Call" idle code | Auto-sets idle reason during Webex App calls |
| **All other sync mappings** | Do Not Sync | Prevents unintended status changes |

### Idle Codes (Desktop Experience > Idle/Wrap-up Codes)

Create purpose-specific idle codes. Recommended set:

| Idle Code | Notes |
|-----------|-------|
| New Sign In | Rename the default (remove description) |
| On Phone Call | Mapped to Webex App State Sync |
| Lunch | — |
| Meeting | — |
| 15 Minute Break | — |
| Supervisor Escalation Path | For supervisor-initiated state changes |

### Wrap-up Codes

| Wrap-up Code | Notes |
|--------------|-------|
| No Wrap Up Selected | Rename the default (remove description) |
| Additional codes | Per your business requirements |

### Queue Tuning

| Setting | Recommended Value | Purpose |
|---------|-------------------|---------|
| **Maximum Time in Queue** | **86400** (seconds = 24 hours) | Prevents premature contact drops |
| **Permit Monitoring** | **Enabled** | Required for supervisor monitoring |
| **Pause/Resume Enabled** | **Enabled** | Required for recording pause/resume |
| **Default Music in Queue** | `defaultmusic_on_hold_cisco_opus` | Built-in hold music |
| **Service Level Threshold** | **120** (seconds) | SLA target for reporting |

### Business Hours

1. **Control Hub > Contact Center > Business Hours** → Create new schedule
2. Name format: `M-F0800-1800_Eastern` (self-documenting)
3. Define working hours blocks per day
4. Reference in Flow Designer via the **Business Hours** object in the Flow Control Objects menu

Business Hours replaces the legacy Routing Strategies approach for time-of-day routing.

### Tenant Cleanup

- Rename "Site-1" to a meaningful name (customer/org name)
- Deactivate and delete the default system-created team (toggle Active slider OFF, then delete)
- Create a Read/Write API connector as a Day 1 task (name: `API_RW`) — see [HTTP Connector](flow-designer-activities/http-connector.md) section

### Cross-Site Restriction

Users and teams must be tied to **one site only**. Cross-site team or user associations are not permitted. Plan your site structure before creating teams.

## See Also

- [flow-designer-essentials.md](flow-designer-essentials.md) — the Flow Designer activities that use these platform resources
- [flow-designer-patterns.md](flow-designer-patterns.md) — the Flow Designer management API and other patterns
- [ai-agent-studio.md](ai-agent-studio.md) — setting up an AI agent on this platform
- [wxcc-provisioning-api.md](wxcc-provisioning-api.md) — creating the same resources programmatically
