## Global Event Output Variables

<!-- ref-tag: fd-act-global-event-output-variables-v1 -->

Event Output Variables are specifically associated with events and use the nomenclature `<EventName>.<VariableName>`. They appear automatically in the **Global Properties** pane after an event is introduced to the flow, and in the **Properties** pane for the associated Event Handler activity.

> For event behavior descriptions (when each event fires, wiring patterns), see [flow-designer-essentials.md](../flow-designer-essentials.md#global-event-flows).

### NewContact

> **Renamed from `NewPhoneContact` to `NewContact` in April 2025.** Existing flows keep the legacy name. New flows use `NewContact`. Both work identically.

| Variable | Description |
|---|---|
| `NewContact.ANI` | Caller's phone number. Returns `anonymous` (not empty) for blocked caller ID. |
| `NewContact.DNIS` | Dialed number (the number the caller called). |
| `NewContact.InteractionId` | Unique interaction identifier. Can be displayed on Agent Desktop. |
| `NewContact.EntryPointId` | Entry Point ID that triggered the flow. |
| `NewContact.PSTNRegion` | PSTN region from EP-DN mapping. RTMS (Next Gen voice platform) only. |
| `NewContact.FlowId` | Flow identifier. |
| `NewContact.FlowVersionLabel` | Flow version label (Dev, Test, Live, Latest). |
| `NewContact.OrgId` | Organization identifier. |
| `NewContact.Headers` | SIP headers from the incoming INVITE in JSON format. Max 20 headers (alphabetically sorted), 1000 bytes total. RTMS only. |
| `NewContact.CallbackType` | `scheduled` or `scheduled_personal` for callbacks. Empty for normal calls. |
| `NewContact.ScheduleSourceInteractionId` | Original interaction ID for callbacks. Empty for normal calls. |
| `NewContact.CallbackReason` | Callback reason text. Empty for normal calls. |
| `NewContact.Payload` | Additional data passed to the flow. May not be available in all tenants — verify in your environment. |

### AgentAccepted

| Variable | Description |
|---|---|
| `AgentAccepted.AgentID` | Agent identifier. |
| `AgentAccepted.AgentName` | Agent display name. |
| `AgentAccepted.AgentEmailId` | Agent email address. May be null in some scenarios — validate before use. |
| `AgentAccepted.AgentSessionID` | Agent session identifier. |
| `AgentAccepted.QueueID` | Queue identifier the call was routed from. |
| `AgentAccepted.QueueName` | Queue display name. |
| `AgentAccepted.TeamID` | Agent's team identifier. |
| `AgentAccepted.TeamName` | Agent's team display name. |
| `AgentAccepted.TenantID` | Tenant (organization) identifier. |
| `AgentAccepted.CAD` | Call-associated data attached to the interaction. |

### PhoneContactEnded

| Variable | Description |
|---|---|
| `PhoneContactEnded.AgentID` | Agent identifier (last agent on the call). |
| `PhoneContactEnded.AgentEmailID` | Agent email address. May be null — validate before use. |
| `PhoneContactEnded.TeamID` | Agent's team identifier. |
| `PhoneContactEnded.QueueID` | Queue identifier the call was routed through. |
| `PhoneContactEnded.InboundChannel` | Inbound channel identifier. |
| `PhoneContactEnded.RoutingStrategyID` | Routing strategy identifier used for the interaction. |

### AgentOffered

> **Note:** The `AgentOffered` event is not supported for progressive, predictive, and preview campaigns.

| Variable | Description |
|---|---|
| `AgentOffered.agentId` | Agent identifier (camelCase variant). |
| `AgentOffered.agentName` | Agent display name (camelCase variant). |
| `AgentOffered.agentEmailId` | Agent email address (camelCase variant). |
| `AgentOffered.agentSessionId` | Agent session identifier (camelCase variant). |
| `AgentOffered.queueId` | Queue identifier (camelCase variant). |
| `AgentOffered.queueName` | Queue display name (camelCase variant). |
| `AgentOffered.teamId` | Agent's team identifier (camelCase variant). |
| `AgentOffered.teamName` | Agent's team display name (camelCase variant). |
| `AgentOffered.tenantId` | Tenant (organization) identifier (camelCase variant). |
| `AgentOffered.callAssociatedData` | Call-associated data (camelCase variant). |
| `AgentOffered.AgentID` | Agent identifier (PascalCase variant). |
| `AgentOffered.AgentName` | Agent display name (PascalCase variant). |
| `AgentOffered.AgentSessionID` | Agent session identifier (PascalCase variant). |
| `AgentOffered.QueueID` | Queue identifier (PascalCase variant). |
| `AgentOffered.QueueName` | Queue display name (PascalCase variant). |
| `AgentOffered.TeamID` | Agent's team identifier (PascalCase variant). |
| `AgentOffered.TeamName` | Agent's team display name (PascalCase variant). |
| `AgentOffered.TenantID` | Tenant (organization) identifier (PascalCase variant). |
| `AgentOffered.CAD` | Call-associated data (PascalCase variant). |

### AgentDisconnected

| Variable | Description |
|---|---|
| `AgentDisconnected.AgentId` | Agent identifier. |
| `AgentDisconnected.AgentEmailId` | Agent email address. May be null — validate before use. |
| `AgentDisconnected.QueueId` | Queue identifier the call was routed through. |
| `AgentDisconnected.TeamId` | Agent's team identifier. |
| `AgentDisconnected.InboundChannel` | Inbound channel identifier. |
| `AgentDisconnected.RoutingStrategyId` | Routing strategy identifier used for the interaction. |

### PreDial

| Variable | Description |
|---|---|
| `PreDial.direction` | Call direction (inbound or outbound). |
| `PreDial.participantType` | Participant type (Agent, Customer, DN, EP-DN). See operationType mapping below. |
| `PreDial.dialNumber` | Number being dialed. |
| `PreDial.otherPartyDn` | Directory number of the other party on the call. |
| `PreDial.epDn` | Entry Point dial number. |
| `PreDial.agentSelectedAni` | ANI selected by the agent for the outbound call. |
| `PreDial.operationType` | Operation type that triggered the PreDial event. See operationType mapping below. |

### PreDial operationType Mapping

| `PreDial.OperationType` | `PreDial.ParticipantType` |
|---|---|
| `INBOUND` | Agent |
| `OUTDIAL` | Agent, Customer |
| `COURTESY_CALLBACK` | Agent, Customer |
| `PREVIEW_CAMPAIGN` | Agent, Customer |
| `WEB_CALLBACK` | Agent, Customer |
| `TRANSFER_TO_DN` | DN |
| `TRANSFER_TO_AGENT` | Agent |
| `CONSULT_TO_DN` | DN |
| `CONSULT_TO_AGENT` | Agent |
| `CONSULT_TO_QUEUE` | Agent |
| `CONSULT_TO_EP_DN` | EP-DN |

> **Note:** Customize ANI is not applicable for Supervisor when call monitoring is configured. Configure every PreDial event handler path with Set Caller ID as a terminal activity, otherwise the contact can be abandoned. Do not use flow activities that queue a contact with the PreDial event handler.

### OutboundCampaignCallResult

| Variable | Description |
|---|---|
| `OutboundCampaignCallResult.CPAResult` | Call Progress Analysis result. Values: `AMD` (answering machine detected), `ABANDONED` (call abandoned due to agent unavailability), `LIVE_VOICE` (live voice detected in IVR campaign). |
| `OutboundCampaignCallResult.CPAResultCode` | Call Progress Analysis result code. |

CPA result values:
- `AMD` -- indicates an answering machine is detected
- `ABANDONED` -- indicates the call has been abandoned due to unavailability of an agent
- `LIVE_VOICE` -- indicates a live voice of a customer is detected in an IVR campaign

### CallbackFailed

Fires when a courtesy callback, scheduled callback, or personal scheduled callback fails (contact busy/unavailable, no answer, agent unreachable, scheduled end time reached, or assigned agent not logged in).

| Variable | Description |
|---|---|
| `CallbackFailed.reason` | Reason the callback failed. Value `AMD` indicates answering machine / voicemail was detected for the customer. Use this variable to decide whether to retry the callback. |

> **Scope:** `CallbackFailed.reason` is available in the event flow on the CallbackFailed event handler, and in the main flow for scheduled callback or personal scheduled callback interactions.

### ContactAniUpdated

Fires when the caller's ANI changes during the interaction (e.g., a customer call goes through an operator desk before reaching the agent, updating the ANI to the original caller's number).

> Output variables for this event are not documented in the Cisco help docs. Verify in a live tenant.

### OnGlobalError

Fires when an unhandled error occurs in any activity that does not have an error-handling path configured. All activities in Call Handling and Flow Control expose this event. Without it, an unhandled activity error silently drops the call.

> Output variables for this event are not documented in the Cisco help docs. Verify in a live tenant.

> **Note:** In certain cases, the `AgentEmailId` variable may be null. Flow developers should validate this variable before using it, especially in scenarios involving cache lookup issues.

