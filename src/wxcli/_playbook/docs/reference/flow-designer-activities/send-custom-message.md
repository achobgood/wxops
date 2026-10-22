## Send Custom Message Activity

<!-- ref-tag: fd-act-send-custom-message-v1 -->

> **Provenance:** This activity appeared in the live prod activity registry on 2026-07-11 (52-activity registry, wxcc-flow describe SendCustomMessage (today `wxcli cc-flow show-activity PROJECT_ID SendCustomMessage`)). Cisco has not yet published activity-level help documentation — it belongs to the **Bring Your Own messaging Channel (BYOC)** capability, announced as upcoming in [What's new for agents in Webex Contact Center](https://help.webex.com/en-us/article/n3v7ldh/What's-new-for-agents-in-Webex-Contact-Center): "Webex Contact Center now supports the integration of custom, non-native conversational channels" — developers "inject and update custom channel interactions through APIs, orchestrate messaging flows and routing, relay outbound messages through webhooks." The BYOC developer guide (developer.webex.com/webex-contact-center/docs/bring-your-own-custom-messaging-channel) is restricted to enrolled beta participants. Everything below is from the live activity registry unless marked otherwise. UI click paths and field labels are **not documented**.

Sends a message on a custom messaging channel (registry description: "Send a message on a custom messaging channel configured for your organization."). Supported channel type: `customMessaging` only — this activity is for BYOC custom messaging flows, not voice or the native digital channels.

Registry metadata: `activityName: SendCustomMessage`, category `core`, group `action`, activityType `action`.

### Configuration (from the live activity registry)

| Input | Type | Required | Default | Notes |
|---|---|---|---|---|
| `channelName` | string | Yes | — | Has a choices endpoint: `wxcli cc-flow list-activity-choices PROJECT_ID SendCustomMessage channelName` lists the org's configured custom messaging channels |
| `messageType` | string | Yes | `text` | Allowed values: `text`, `text-with-attachments` |
| `messageText` | string | Yes | — | Marked `isSecure: true` in the registry |
| `attachments` | object[] | No | — | Shown when `messageType != text` (`showOnCondition` from the registry); attachment object shape not documented |
| `appendToTranscript` | boolean | No | `true` | UI behavior not documented |
| `outputVariableArray1` | object | No | — | Purpose not documented |
| `flowDecryptAccess` | boolean | No | `false` | Purpose not documented |

How custom messaging channels are provisioned (so that `channelName` has values to choose from) is **not documented** in this project's references — the BYOC setup procedure lives in the beta-gated developer guide. On an org with no provisioned custom messaging channel (2026-07-12), wxcc-flow choices SendCustomMessage channelName (today `wxcli cc-flow list-activity-choices PROJECT_ID SendCustomMessage channelName`) returned **400 "Activity 'SendCustomMessage' not found in registry ... flowType=FLOW"** — the activity is not resolvable for choices in this org's FLOW registry (BYOC beta-gated / not provisioned); whether provisioning a custom messaging channel would then populate `channelName` was not tested. The input names (`channelName`, `messageType`, `messageText`, `attachments`, `appendToTranscript`, `outputVariableArray1`, `flowDecryptAccess`) and output port (`error`) above were re-confirmed via wxcc-flow describe SendCustomMessage (today `wxcli cc-flow show-activity PROJECT_ID SendCustomMessage`) on 2026-07-12; their semantics remain beta-gated.

### Output Variables (from the live activity registry)

| Variable | Type | Registry description |
|---|---|---|
| `ChannelPayload` | JSON (transient) | "A structured object containing the outgoing channel payload content." |
| `TrackingId` | String | "This variable stores the unique identifier for the message sending transaction initiated by this node." |
| `ErrorCode` | String | "This variable captures the error code whenever an error occurs." |
| `ErrorMessage` | String | "This variable captures the error code whenever an error occurs." (registry text — appears to duplicate the ErrorCode description) |
| `status` | String | (no description in the registry) |
| `Description` | String | "Optional summary indicating whether PCI masking was applied to message text and whether any attachments were dropped." |

`ChannelPayload` is marked transient in the registry — transient outputs are not persisted beyond the immediate flow step.

### Output Paths (from the live activity registry)

| Port | isErrorPath | Notes |
|---|---|---|
| `error` | Yes | Trigger semantics not documented |

The registry lists no success/`default` port. Whether the success edge is implicit (as with `screen-pop` — see flow-designer-flowir.md § Implicit Output Ports) is **not verified** for this activity.

### Not Documented

- UI location, click path, and field labels in Flow Designer
- Attachment object shape for `messageType: text-with-attachments`
- `appendToTranscript`, `outputVariableArray1`, and `flowDecryptAccess` semantics
- BYOC channel provisioning and outbound webhook relay (beta-gated developer guide)
- FlowIR import behavior — this activity has NOT been round-trip tested via `wxcli cc-flow create-validate PROJECT_ID --json-body file://flow.json` / `wxcli cc-flow create-import PROJECT_ID --json-body file://flow.json`

---
