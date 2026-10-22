## Screen Pop Activity

<!-- ref-tag: fd-act-screen-pop-v1 -->

Pops a URL to the agent's Contact Center Desktop when a contact is offered or connected. Use it to auto-open a CRM record, knowledge base article, or custom application based on caller data.

### Configuration

| Field | Description |
|---|---|
| Activity Label | Name for the activity |
| Activity Description | (Optional) Description for the activity |
| Screen Pop URL | Target URL — supports `{{variable}}` interpolation |
| Query Parameters | Key-value pairs appended to the URL. Supports `{{variable}}` syntax in values. |
| Screen Pop Desktop Label | Custom display text that replaces the raw URL on the Agent Desktop |
| Screen Pop Display | **New browser tab**, **Existing Screen Pop tab**, or **Inside Desktop** (displays in the Auxiliary Information pane) |

### Output Variables

No output variables. Screen Pop triggers a desktop action and does not return data to the flow.

### Output Paths

N/A — event flow activity with a single exit.

### Placement

Configure Screen Pop in the **Event Flows** tab, typically on the **AgentAccepted** event or the **PhoneContactEnded** event. This ensures the pop fires when the agent answers the call or after the call ends.

You can define one Screen Pop for each flow.

> **Warning:** If the Screen Pop display option is **Inside Desktop** or **Existing browser tab**, data being entered in the Screen Pop for a call is lost if the agent accepts a new call. To prevent data loss, configure the display option as **New browser tab**.

> **Note:** Screen Pop for new digital channels must be configured in the Connect Flow Builder.

### Common Patterns

- CRM lookup by ANI: `https://crm.example.com/contact?phone={{NewContact.ANI}}`
- Interaction context: `https://portal.example.com/case?id={{NewContact.InteractionId}}`
- Data from prior HTTP Request: `https://crm.example.com/account/{{accountId}}`

---

