## Outdial Entry Point Flows

<!-- ref-tag: fd-act-outdial-entry-point-v1 -->

Outdial Entry Point flows control the call experience for outbound (outdial) contacts — agent-initiated outdial calls and outbound campaign calls (progressive, predictive, preview, and IVR campaigns). They determine what happens when the system dials a customer: ANI customization, screen pops to the agent, call progress analysis handling, and IVR interactions for agent-less campaigns. [source: [Build and manage flows with Flow Designer](https://help.webex.com/en-us/article/nhovcy4/Build-and-manage-flows-with-Flow-Designer) § Support for workflows in Outdial Entry Point; [Configure Voice Outbound Campaign Modes](https://help.webex.com/en-us/article/nqu2kub/Configure-Voice-Outbound-Campaign-Modes-in-Webex-Contact-Center)]

Because the call is outbound (the system or agent initiates it), inbound IVR activities like menus, queuing, and caller self-service are not applicable. The activity set is restricted accordingly.

### Setup — Create an Outdial Entry Point

Create the outdial entry point in Control Hub before building the flow. [source: [Set up a channel](https://help.webex.com/en-us/article/ewuay1/Set-up-a-channel)]

1. **Control Hub > Services > Contact Center > Customer Experience > Channels > Create**
2. Fill in:

| Field | Value |
|---|---|
| Name | Descriptive name (max 80 characters, alphanumeric/underscore/hyphen) |
| Description | Optional |
| Channel Type | **Outbound Telephony** |
| Timezone | Time zone for business hours |
| Routing Flow | Select the published flow you built for this campaign |
| Version Label | Select preferred flow version (Dev, Test, Live, Latest) |
| Music on Hold | Audio file for outdial hold music |
| Outdial Queue | Select the outdial queue from the list |

3. Save.

> **Note:** The system automatically creates an entry point called **Outdial Transfer to Queue**. If you need to transfer outbound calls to a queue (e.g., IVR campaign escalation to a live agent), link the support or dial number to this system entry point. [source: [Set up a channel](https://help.webex.com/en-us/article/ewuay1/Set-up-a-channel)]

### Supported Activities

The following activities and events are supported in Outdial Entry Point flows. [source: [Build and manage flows with Flow Designer](https://help.webex.com/en-us/article/nhovcy4/Build-and-manage-flows-with-Flow-Designer) § Support for workflows in Outdial Entry Point]

| Activity | Outdial Use Case |
|---|---|
| HTTP Request | Look up customer record, CRM data dip before agent connection |
| Condition | Branch on campaign type, customer segment, CPA result |
| Parse | Extract fields from HTTP response JSON |
| Set Variable | Store campaign data, set caller ID variables, increment counters |
| Business Hours | Check if the current time is within campaign operating hours |
| End Flow | Terminate flow without disconnecting (call stays active) |
| Screen Pop | Pop CRM record or customer info to the agent desktop on answer |
| Event handlers | PreDial, AgentOffered, OutboundCampaignCallResult, PhoneContactEnded, OnGlobalError, AgentAccepted, AgentDisconnected (populated based on main flow activities) |

Global variables and local variables are both supported.

### Unsupported Activities

The following activities are **not available** in Outdial Entry Point flows. [source: [Build and manage flows with Flow Designer](https://help.webex.com/en-us/article/nhovcy4/Build-and-manage-flows-with-Flow-Designer) § Support for workflows in Outdial Entry Point]

| Activity | Why Unsupported |
|---|---|
| Queue Contact | Outbound calls are already associated with an outdial queue |
| Queue To Agent | Not applicable — the agent is already assigned or the system manages routing |
| Callback | Callback registration is an inbound concept |
| Get Queue Info (Queue Lookup) | No inbound queue to query |
| Advanced Queue Information | No inbound queue to query |
| Blind Transfer | Not supported for outbound call flows |
| Bridged Transfer | Not supported for outbound call flows [source: bridged-transfer.md § Restrictions] |
| Escalate Call Distribution Group | No CDG escalation in outbound context |
| Play Message (IVR message) | Not available as a standalone IVR prompt activity in outdial flows |
| Menu | DTMF menu is an inbound IVR concept |
| Feedback / Survey | Post-call survey is not supported in outdial flows |
| Set Contact Priority | Not supported for outdial and campaign contacts (failure code 48) [source: set-contact-priority.md § Failure Codes] |

> **Warning:** Do not include a **Disconnect Contact** activity at the end of an outdial flow. Using Disconnect Contact causes the flow to end the call and prompt a wrap-up while the outdial call is actually active and connected. [source: [Build and manage flows with Flow Designer](https://help.webex.com/en-us/article/nhovcy4/Build-and-manage-flows-with-Flow-Designer) § Support for workflows in Outdial Entry Point]

### Event Handlers in Outdial Context

Event handlers are populated based on the activities you add in the main flow. The key events for outdial flows are: [source: [Configure Voice Outbound Campaign Modes](https://help.webex.com/en-us/article/nqu2kub/Configure-Voice-Outbound-Campaign-Modes-in-Webex-Contact-Center); global-event-output-variables.md]

| Event | Outdial Behavior |
|---|---|
| **PreDial** | Fires before the outbound call is placed. Use to customize ANI via Set Caller ID. In outdial context, `PreDial.operationType` is `OUTDIAL` or `PREVIEW_CAMPAIGN`, and `PreDial.participantType` is `Agent` or `Customer`. Configure Set Caller ID as the terminal activity in the PreDial handler. |
| **OutboundCampaignCallResult** | Fires when a campaign call completes. Exposes `CPAResult` (`AMD`, `ABANDONED`, `LIVE_VOICE`) and `CPAResultCode`. Use to branch on CPA outcome — e.g., disconnect on AMD, play IVR on LIVE_VOICE (for IVR campaigns), or log abandoned calls. |
| **AgentOffered** | Fires when a call is offered to an agent. **Not supported for progressive, predictive, and preview campaigns.** Only fires for agent-initiated outdial calls. |
| **AgentAccepted** | Fires when the agent accepts the outdial call. Use for screen pop or logging. |
| **PhoneContactEnded** | Fires after the call terminates. Use for post-call logging or CJDS updates. |
| **OnGlobalError** | Fires on unhandled errors. Wire to a fallback path. |

### Available Variables

Outdial flows support global and local variables. For outbound campaigns, customer data is passed to the flow via global variables. [source: [Configure Voice Outbound Campaign Modes](https://help.webex.com/en-us/article/nqu2kub/Configure-Voice-Outbound-Campaign-Modes-in-Webex-Contact-Center)]

| Variable Category | Details |
|---|---|
| **Global variables** | Up to **28** global variables of type String can carry customer data imported from Campaign Manager. Mark as **Agent Viewable = True** to display on the agent desktop. |
| **`campaignId`** (mandatory) | Create a global variable named exactly `campaignId` (case-sensitive) with Desktop Label `Campaign Name`. Required for all campaign flows. |
| **Local variables** | Standard flow-scoped variables for intermediate calculations. |
| **PreDial output variables** | `PreDial.direction`, `PreDial.participantType`, `PreDial.dialNumber`, `PreDial.otherPartyDn`, `PreDial.epDn`, `PreDial.agentSelectedAni`, `PreDial.operationType` |
| **OutboundCampaignCallResult output variables** | `OutboundCampaignCallResult.CPAResult`, `OutboundCampaignCallResult.CPAResultCode` |
| **Desktop viewability** | Configure variables for the Incoming Popover (max 6) and Interaction Panel (max 30). Include `campaignId` in the incoming popover so the campaign name displays when the call rings. |

> **Note:** Agent-Editable variables are accessible within the flow for direct preview calls. Agent non-Editable variables are not accessible within the flow. [source: [Configure Voice Outbound Campaign Modes](https://help.webex.com/en-us/article/nqu2kub/Configure-Voice-Outbound-Campaign-Modes-in-Webex-Contact-Center)]

### Typical Outdial Flow Pattern

**Agent-based campaign flow** (progressive/predictive/preview):

```
[Flow Start]
  │
  ├── PreDial Event Handler:
  │     Set Caller ID (local-presence ANI) → [terminal]
  │
  ├── OutboundCampaignCallResult Event Handler:
  │     Condition: CPAResult == "AMD"
  │       ├── TRUE → End Flow (answering machine — skip)
  │       └── FALSE → Condition: CPAResult == "ABANDONED"
  │             ├── TRUE → End Flow (no agent available)
  │             └── FALSE (LIVE_VOICE) → End Flow (agent handles)
  │
  ├── AgentAccepted Event Handler:
  │     Screen Pop (CRM URL with campaign variables)
  │
  └── Main Flow:
        HTTP Request (CRM data dip for customer record)
          → Parse (extract customer details)
            → Set Variable (store in flow variables for desktop display)
              → End Flow
```

**IVR campaign flow** (no live agent — plays messages or routes to AI agent):

For IVR campaigns (IVR Progressive / IVR Predictive), the system uses IVR ports instead of live agents. When a LIVE_VOICE result is detected, the flow can play messages to the customer or route to an AI agent. To escalate an IVR campaign call to a live agent, use a **GoTo** activity to transfer to a separate inbound entry point and flow. [source: [Configure Voice Outbound Campaign Modes](https://help.webex.com/en-us/article/nqu2kub/Configure-Voice-Outbound-Campaign-Modes-in-Webex-Contact-Center)]

---

