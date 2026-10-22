## Set Caller ID Activity

<!-- ref-tag: fd-act-set-caller-id-v1 -->

Customizes the outbound caller ID (CLID) displayed when the call is transferred or when an agent makes an outbound call.

### Configuration

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | Optional description |
| Caller ID DN | **Static Caller ID** — choose a dial number mapped to an Entry Point. **Variable Caller ID** — choose a flow variable containing a valid E.164 number with valid EP-DN mapping. |

### Placement

Set Caller ID is used in **Event Flows only**, typically in the **PreDial** event flow. It marks the end (terminal activity) of the PreDial event flow.

If no selection is made, or the number is not in E.164 format, the system uses the default caller ID depending on the call scenario.

### ANI Scenarios

The Set Caller ID activity helps configure the ANI for the following scenarios:

| Scenario | PreDial.OperationType | PreDial.ParticipantType |
|---|---|---|
| Inbound calls | INBOUND | Agent |
| Outdial calls | OUTDIAL | Agent, Customer |
| Courtesy callback | COURTESY_CALLBACK | Agent, Customer |
| Preview campaign | PREVIEW_CAMPAIGN | Agent, Customer |
| Web callback | WEB_CALLBACK | Agent, Customer |
| Transfer to dial number | TRANSFER_TO_DN | DN |
| Transfer to agent | TRANSFER_TO_AGENT | Agent |
| Consult to dial number | CONSULT_TO_DN | DN |
| Consult to agent | CONSULT_TO_AGENT | Agent |
| Consult to queue | CONSULT_TO_QUEUE | Agent |
| Consult to EP-DN | CONSULT_TO_EP_DN | EP-DN |

### ANI Behavior by Call Scenario (Next Generation environment)

| Scenario | Configuration | Result ANI |
|---|---|---|
| Customer calls in | PreDial event handler is not configured | ANI of the contact is presented on the agent's device. EP-DN is presented on the contact's device. |
| Customer calls in | PreDial event handler is configured | ANI is presented on the agent's device as defined in the Set Caller ID activity. |
| Agent Outdial | PreDial event handler is not configured | The contact's device and the agent's device are both presented with Agent selected Outdial ANI if the agent selects an Outdial ANI on the Desktop. Otherwise both are presented with the tenant's default ANI. |
| Agent Outdial | PreDial event handler is configured | For each participant's device, either the Agent selected Outdial ANI can be retained, if selected, or can be customized, as defined in the Set Caller ID activity. |
| Courtesy callback | Customer ANI defined in Callback activity, PreDial not configured | ANI defined at the Callback activity is presented to the contact's device. |
| Courtesy callback | Customer ANI defined in Callback activity, PreDial configured for customer leg | Set Caller ID activity configured will take precedence. |
| Courtesy callback | Customer ANI not defined, PreDial not configured | Tenant default ANI is presented on the contact's device. |
| Agent transfer, consult | PreDial event handler is configured | Configured Set Caller ID is displayed on transferred/consulted Agent-2 device. |

### Agent DN as Customized ANI

You can configure the agent's DN as a customized ANI, so that the callee agent can see the caller agent DN/extension number when they are contacted. This reduces the chances of internal calls getting dropped. For example, when a front office user (the contact center agent) calls a back-office user (an internal employee), the back-office user can see the internal caller ID (contact number/extension) of the agent, minimizing call rejections.

To allow internal extensions as customized ANI for the callers, when you configure the predial flow for customer/consulted agent or DN/transferred agent or DN, choose the `Predial.otherPartyDn` variable from the dropdown as Variable Caller ID. Since this variable contains the primary agent's DN, it will be a valid custom ANI shown on the receiver's device.

You must add the contact number to the list of internal numbers for an organization in **Control Hub > Contact Center > Tenant Settings > Voice > Contact Number**.

### Output Variables

This activity has no output variables. Set Caller ID is a terminal activity in the PreDial event flow.

### Output Paths

N/A — terminal activity in the PreDial event flow. Set Caller ID marks the end of the event flow path.

### Failure Codes

No failure codes are documented for this activity. If no selection is made, or the number is not in E.164 format, the system silently falls back to the default caller ID for the call scenario.

### Use Cases

- **Mask internal extensions:** When transferring a call externally, display the main company number instead of an internal extension.
- **Per-queue caller ID:** Set different outbound caller IDs based on which queue or department is handling the call.
- **Campaign caller ID:** For outbound campaigns, set a local-presence number matching the customer's area code.

### Regulatory Note

ANI customization has a dependency on regulatory requirements. Consider the regional dependencies before deployment of the environment. Flow support is required for any inbound or outbound scenario to customize the ANI. For use cases having dependencies on service providers such as country-code based decisions or regional restrictions, consider testing the flows with the service providers first.

---

