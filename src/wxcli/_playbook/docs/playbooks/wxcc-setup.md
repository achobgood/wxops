# Webex Contact Center (WxCC) Setup Playbook

<!-- ref-tag: wxcc-setup-v3 -->

## Overview

This playbook covers the one-time setup required in WxCC Control Hub and Flow Designer before an AI agent can handle calls or chats.

---

## 1. Control Hub Prerequisites

Log into **Control Hub** (admin.webex.com) with an admin account that has WxCC entitlements.

### 1.1 Site Setup
- Navigate to **Contact Center > Settings > General**
- Confirm a Site is provisioned (e.g., "Default Site")
- If no site exists, contact your Cisco partner to provision

### 1.2 Create a Team
1. **Contact Center > Teams > Add Team**
2. Fill in: Team Name (e.g., "Lab Agents"), Site, Type: Agent-Based
3. Save

### 1.3 Create a Queue
1. **Contact Center > Queues > Add Queue**
2. Fill in:
   - Name: e.g., `Lab_Scheduling_Queue`
   - Channel Type: Telephony (or Chat)
   - Routing Type: Longest Available Agent
3. Under Team Assignment, add the team created above
4. Save

### 1.4 Create an Entry Point
1. **Contact Center > Entry Points > Add Entry Point**
2. Fill in:
   - Name: e.g., `Lab_Scheduling_EP`
   - Channel Type: Telephony
   - Service Level Threshold: 60
3. Save — note the Entry Point ID (shown in URL)

### 1.5 Assign a PSTN Number
1. **Contact Center > Phone Numbers**
2. Click an unassigned number → Assign to Entry Point created above
3. Save

### 1.6 Additional Setup for API-Driven Flows

- If your flow uses **Custom Connectors** for authenticated API calls to external services (ServiceNow, Salesforce, custom backends), see [Custom Connectors Setup](custom-connectors-setup.md) for the full walkthrough: creating the connector in Control Hub, configuring OAuth or Basic Auth, and linking it to an HTTP Request activity in Flow Designer.
- If your flow uses **Functions** for data transformation (DNIS maps, date formatting, JSON restructuring), see [Functions Setup](functions-setup.md) for creating, testing, publishing, and wiring a Function into a flow.

---

## 2. WxCC Flow Designer — Voice Flow

### 2.1 Create a New Flow
1. **Contact Center > Flows > New Flow**
2. Name: e.g., `Lab_Scheduling_Voice_Flow`
3. Click the canvas — Flow Designer opens

### 2.2 Add Virtual Agent V2 Node
1. Drag **Virtual Agent V2** from the activity panel
2. Configure:
   - Contact Center AI Config: select **Webex AI Agent Autonomous** (or **Webex AI Agent Scripted**), then select your published agent. There is no Control Hub step to create this — it is a selection, not a creation [`ai-agent-studio.md` § CCAI Config (Linking Agent to WxCC)]. If those entries are missing from the drop-down, a one-time tenant enablement is outstanding [`wxcc-platform.md` § Webex AI Agent Tenant Prerequisite]. Do **not** use section 4 below — that is the Google CCAI integration.
   - Prompt: leave blank (AI agent handles greeting)
3. Connect **NewPhoneContact** → **Virtual Agent V2**

### 2.3 Handle Escalation and End
1. From **Virtual Agent V2**, connect:
   - `Escalated` output → **Queue Contact** node
   - `Handled` output → **Disconnect Contact** node
   - `Errored` output → **Disconnect Contact** node (or a Play Message + Disconnect)
2. **Queue Contact** node: select `Lab_Scheduling_Queue`
3. Connect **Queue Contact** → **Disconnect Contact**

### 2.4 Publish the Flow
1. Validate (toolbar button) — fix any errors
2. Publish — select a **version label**:
   - **Dev** for initial testing (assign to a test Entry Point)
   - **Live** for production traffic
   - See `docs/reference/flow-designer-patterns.md` § Flow Versioning for the full Dev → Test → Live promotion workflow

### 2.5 Link Flow to Entry Point
1. Back in **Control Hub > Entry Points**
2. Click entry point → Edit
3. Under **Flow**, select the published flow
4. Under **Version Label**, select which version to serve (Dev, Test, or Live)
5. Save

---

## 3. Digital (Chat/SMS) Channel Setup

### 3.1 Create a Digital Channel Entry Point
1. **Contact Center > Entry Points > Add Entry Point**
2. Channel Type: Chat (or SMS)
3. Assign a Webex Connect Service (links WxCC to your Connect org)

### 3.2 WxCC Flow Designer — Digital Flow
1. Create a new flow with an **AI Agent** node (not Virtual Agent V2)
2. Connect to **Queue Task** on escalation
3. Publish and link to digital entry point

### 3.3 Webex Connect
- The actual inbound handler lives in Webex Connect, not WxCC Flow Designer
- Connect flow routes to the AI Agent, then optionally escalates via Queue Task API call
- See connect-flows.md for Connect flow conventions

---

## 4. CCAI Config (Google CCAI / BYOVA / Agent Answers)

> ⚠ **Skip this entire section if you are building a Webex AI Agent.** CCAI is Google's product and Webex AI Agent is Cisco's own; a Webex AI Agent has **no Control Hub creation step**. You publish the agent in AI Agent Studio and then select it in the Virtual Agent V2 activity — step 2.2 above. Why: [`wxcc-platform.md` § CCAI Config (Google CCAI / BYOVA / Agent Answers)]. The Webex AI Agent path: [`ai-agent-studio.md` § CCAI Config (Linking Agent to WxCC)].

Do this section **only** when integrating **Google CCAI**, **BYOVA (Bring Your Own Virtual Agent)**, or **Agent Answers**.

**Before you start:** the service-specific integration connector must already exist — for example, a Google Contact Center AI connector [`wxcc-platform.md` § CCAI Config (Google CCAI / BYOVA / Agent Answers)].

1. **Control Hub > Services > Contact Center > Tenant settings > Integrations**
2. Go to the **Features** tab, then click **New > Contact Center AI Config** [`wxcc-platform.md` § CCAI Config (Google CCAI / BYOVA / Agent Answers)]
3. Set **Contact Center AI Connector**, then set **Feature** — the valid values for both fields are listed in [`wxcc-platform.md` § CCAI Config (Google CCAI / BYOVA / Agent Answers)]
4. Name it (e.g., `Lab_Google_CCAI`)
5. Save
6. Use this CCAI Config name in your Virtual Agent V2 node

---

## 5. Agent Desktop

Agents who receive escalated calls need the Webex Contact Center agent desktop.

1. Agents log in at: `desktop.wxcc.cisco.com`
2. Agent must be assigned to the team linked to the queue
3. Agent sets status to **Available** to receive calls

---

## 6. Testing Voice End-to-End

1. Dial the PSTN number assigned to your Entry Point
2. Flow routes to Virtual Agent V2 → your AI agent answers
3. If you say "talk to an agent," call escalates to the queue
4. Agent desktop rings for available agents

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Call drops immediately | Flow not published or not linked to entry point |
| Virtual agent doesn't respond | CCAI Config not linked, or AI agent not deployed |
| Escalation doesn't ring agents | Team not assigned to queue, or agent not Available |
| "No agents available" message | No agents logged in or all busy |

---

## Developer Resources

### Developer Sandbox

Request a dedicated WxCC sandbox for development and testing at the Webex Developer Portal:

1. Go to **developer.webex.com → Documentation → Webex Contact Center → Contact Center Sandbox**
2. Click **Request Sandbox** — a pre-filled support ticket opens
3. Include your **Org ID** in the request (find it in Control Hub → Account → Org ID)
4. US-based customers only. Provides administrator access to a licensed WxCC instance with a dialable phone number.

### Developer Portal

**developer.webex.com** — primary resource for WxCC development:

| Resource | Description |
|---|---|
| Documentation | API reference for WxCC, Webex Connect, and platform APIs |
| Sandbox | Request a dedicated development environment |
| Sample code/SDKs | Reference implementations and client libraries |
| Blog | Technical articles and release announcements |

### Developer Support

| Channel | Details |
|---|---|
| Email | wxccdevsupport@webex.com |
| Ticket Portal | devsupport.webex.com — ticketed process for tracking |
| Developer Community | cs.co/WebexDeveloperCommunity — use label "Webex Contact Center APIs" |

### Webex App Hub

**apphub.webex.com** — marketplace for third-party integrations and apps that extend Webex Contact Center.
