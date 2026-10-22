## Receive Message Activity

<!-- ref-tag: fd-act-receive-message-v1 -->

> **Provenance:** This activity appeared in the live prod activity registry on 2026-07-11 (52-activity registry, wxcc-flow describe ReceiveMessage (today `wxcli cc-flow show-activity PROJECT_ID ReceiveMessage`)). Cisco has not yet published activity-level help documentation — it belongs to the **Bring Your Own messaging Channel (BYOC)** capability, announced as upcoming in [What's new for agents in Webex Contact Center](https://help.webex.com/en-us/article/n3v7ldh/What's-new-for-agents-in-Webex-Contact-Center): "Webex Contact Center now supports the integration of custom, non-native conversational channels" — developers "inject and update custom channel interactions through APIs, orchestrate messaging flows and routing, relay outbound messages through webhooks." The BYOC developer guide (developer.webex.com/webex-contact-center/docs/bring-your-own-custom-messaging-channel) is restricted to enrolled beta participants. Everything below is from the live activity registry unless marked otherwise. UI click paths and field labels are **not documented**.

Waits to receive a customer message before the flow proceeds (registry description: "Wait to receive a customer message before the flow proceeds."). Supported channel type: `customMessaging` only — this activity is for BYOC custom messaging flows, not voice or the native digital channels.

Registry metadata: `activityName: ReceiveMessage`, category `core`, group `action`, activityType `action`.

### Configuration (from the live activity registry)

| Input | Type | Required | Default | Notes |
|---|---|---|---|---|
| `channelType` | string | Yes | `CUSTOM_MESSAGING` | Only allowed value: `CUSTOM_MESSAGING` |
| `channelName` | string | Yes | — | Has a choices endpoint: `wxcli cc-flow list-activity-choices PROJECT_ID ReceiveMessage channelName` lists the org's configured custom messaging channels |
| `timeout` | int | Yes | `5` | Unit (seconds vs. minutes) is not documented |
| `appendToTranscript` | boolean | No | `true` | UI behavior not documented |
| `outputVariableArray1` | object | No | — | Purpose not documented |
| `flowDecryptAccess` | boolean | No | `false` | Purpose not documented |

How custom messaging channels are provisioned (so that `channelName` has values to choose from) is **not documented** in this project's references — the BYOC setup procedure lives in the beta-gated developer guide. On an org with no provisioned custom messaging channel (2026-07-12), wxcc-flow choices ReceiveMessage channelName (today `wxcli cc-flow list-activity-choices PROJECT_ID ReceiveMessage channelName`) returned **400 "Activity 'ReceiveMessage' not found in registry ... flowType=FLOW"** — the activity is not resolvable for choices in this org's FLOW registry (BYOC beta-gated / not provisioned); whether provisioning a custom messaging channel would then populate `channelName` was not tested. The input names (`channelType`, `channelName`, `timeout`, `appendToTranscript`, `outputVariableArray1`, `flowDecryptAccess`) and output ports (`timeout`, `error`) above were re-confirmed via wxcc-flow describe ReceiveMessage (today `wxcli cc-flow show-activity PROJECT_ID ReceiveMessage`) on 2026-07-12; their semantics remain beta-gated.

### Output Variables (from the live activity registry)

| Variable | Type | Registry description |
|---|---|---|
| `ChannelPayload` | JSON (transient) | "A structured object containing the incoming channel payload content from the customer." |
| `TrackingId` | String | "The unique identifier for the message sending transaction initiated by this node" |
| `ErrorCode` | String | "The error code in case of any error scenario" |
| `ErrorMessage` | String | "The detailed error description that will only be set when there is an error" |
| `status` | String | (no description in the registry) |
| `Description` | String | "Optional summary indicating whether PCI masking was applied to message text and whether any attachments were dropped." |

`ChannelPayload` is marked transient in the registry — transient outputs are not persisted beyond the immediate flow step.

### Output Paths (from the live activity registry)

| Port | isErrorPath | Notes |
|---|---|---|
| `timeout` | Yes | Exact trigger semantics not documented (the activity also has a required `timeout` input) |
| `error` | Yes | Trigger semantics not documented |

The registry lists no success/`default` port. Whether the success edge is implicit (as with `screen-pop` — see flow-designer-flowir.md § Implicit Output Ports) is **not verified** for this activity.

### Not Documented

- UI location, click path, and field labels in Flow Designer
- `timeout` unit and the exact behavior of the `timeout` port
- `appendToTranscript`, `outputVariableArray1`, and `flowDecryptAccess` semantics
- BYOC channel provisioning (beta-gated developer guide)
- FlowIR import behavior — this activity has NOT been round-trip tested via `wxcli cc-flow create-validate PROJECT_ID --json-body file://flow.json` / `wxcli cc-flow create-import PROJECT_ID --json-body file://flow.json`

---
