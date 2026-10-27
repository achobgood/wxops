# Build Flow Programmatic — Reference

Validated patterns and CLI commands for programmatic flow building via FlowIR.

## FlowIR Minimal Structure

```json
{
  "name": "Flow_Name",
  "flowType": "FLOW",
  "description": "...",
  "variables": [],
  "nodes": [],
  "edges": [],
  "eventFlows": {}
}
```

## Node Template

```json
{
  "id": "unique-node-id",
  "name": "Display Name",
  "activityType": "action",
  "group": "action",
  "properties": {
    "activityName": "play-message"
  }
}
```

`activityType` and `group` vary by activity — use `wxcli cc-flow show-node-template PROJECT_ID ACTIVITY` to get the correct values.

## Validated Property Patterns

### TTS Activities (play-message, ivr-menu, ivr-collectdigits, set-whisperannouncement)

All TTS activities require the 5-field connector pattern:

```json
{
  "activityName": "play-message",
  "toggle": true,
  "promptsTts": [{"name": "prompt text", "type": "tts", "value": "prompt text"}],
  "connector": "Cisco Cloud Text-to-Speech",
  "connector_name": "Cisco Cloud Text-to-Speech",
  "connector:name": "Cisco Cloud Text-to-Speech",
  "connector_type": "Cisco Cloud Text-to-Speech",
  "connector:type": "Cisco Cloud Text-to-Speech",
  "speakingRate": 1,
  "volumeGainDb": 0
}
```

Resolve connector values via: `wxcli cc-flow list-activity-choices PROJECT_ID play-message connector`

### Queue Contact (minimal pattern)

```json
{
  "activityName": "queue-contact",
  "queueId": "<queue-uuid>",
  "channelType": "TELEPHONY"
}
```

`channelType` is required: without it `wxcli cc-flow create-validate` fails with `FC1015 Required field 'Channel type' is not configured` (verified live 2026-10-19; this pattern carried `queueId` alone until then) [`flow-designer-flowir.md` § 7 `queue-contact`]. Do NOT include `queueRadioGroup` — it triggers "UI mode" validation. Resolve queue UUIDs via: `wxcli cc-flow list-activity-choices PROJECT_ID queue-contact destination --parent-input-name channelType --parent-value TELEPHONY` (cascading input — the parent flags are required)

### Set Variable (double declaration)

```json
{
  "activityName": "set-variable",
  "activityId": "set-variable",
  "activityType": "logic",
  "setTo": "set-to-literal",
  "srcVariableType": "STRING",
  "srcVariable": "varName",
  "literal": "value or {{expression}}",
  "expr": "value or {{expression}}",
  "setVariablesArray": [
    {
      "setTo": "set-to-literal",
      "srcVariableType": "STRING",
      "srcVariable": "varName",
      "literal": "value or {{expression}}",
      "expr": "value or {{expression}}",
      "literal_invalid_error": false
    }
  ]
}
```

Top-level fields (`setTo`, `srcVariableType`, `srcVariable`, `literal`, `expr`) AND `setVariablesArray` are both required. Omitting either causes FC1015. For INTEGER variables, use `srcVariableType: "INTEGER"` and pass the value as a string (e.g., `"0"`).

### Condition Activity

```json
{
  "activityName": "condition-activity",
  "expression": "{{variable == value}}"
}
```

Output ports: `true`, `false`, `error`.

### Business Hours

```json
{
  "activityName": "business-hours",
  "businessHoursId": "<schedule-uuid>"
}
```

Output ports: `workingHours`, `holidays`, `override`, `default`, `error`. Resolve via: `wxcli cc-flow list-activity-choices PROJECT_ID business-hours businessHoursId`

### HTTP Request v2

```json
{
  "activityName": "http-request-v2",
  "authenticated": true,
  "connectorId": "<connector-uuid>",
  "connectorId:name": "ConnectorName",
  "connectorId_name": "ConnectorName",
  "httpRequestUrl": "https://api.example.com/endpoint",
  "httpRequestMethod": "GET",
  "httpRequestMethod:name": "GET",
  "httpRequestMethod_name": "GET",
  "httpContentType": "None",
  "httpContentType:name": "None",
  "httpContentType_name": "None",
  "contentType": "JSON",
  "contentType_name": "JSON",
  "outputVariableArray": [
    {"outputVariable": "varName", "jsonPathExp": "$.path"}
  ],
  "httpResponseTimeout": 2000,
  "retryAttempts": 1
}
```

**Gotcha:** `authenticated: false` (no connector, inline headers) does NOT work via FlowIR validation — returns FC1015. Always use `authenticated: true` with a Custom Connector. Resolve connector UUIDs via `wxcli cc-flow list-activity-choices PROJECT_ID http-request-v2 connectorId`.

### Collect Digits

```json
{
  "activityName": "ivr-collectdigits",
  "toggle": true,
  "promptsTts": [{"name": "text", "type": "tts", "value": "text"}],
  "connector": "Cisco Cloud Text-to-Speech",
  "connector_name": "Cisco Cloud Text-to-Speech",
  "connector:name": "Cisco Cloud Text-to-Speech",
  "connector_type": "Cisco Cloud Text-to-Speech",
  "connector:type": "Cisco Cloud Text-to-Speech",
  "entryTimeout": "5",
  "interDigitTimeout": "3",
  "minDigits": 1,
  "maxDigits": 10,
  "terminatorSymbol": "#",
  "speakingRate": 1,
  "volumeGainDb": 0
}
```

Output ports: `default`, `timeout`, `invalid`, `error`. The definition lists only the last three; `default` is the success edge stored flows hold. `wxcli cc-flow create-validate` rejects `default` here (`Use one of: error, invalid, timeout`) and `wxcli cc-flow create-import` accepts it with no warning (verified live 2026-10-19) [`flow-designer-flowir.md` § 2].

### Transfers

```json
{"activityName": "bridged-transfer", "transfertodn": "{{dialNumber}}", "transfertodn:radioName": "setToVariable", "transfertodn_radioName": "setToVariable", "timeout": 10}
{"activityName": "blind-transfer", "transfertodn": "{{dialNumber}}", "transfertodn:radioName": "setToVariable", "transfertodn_radioName": "setToVariable"}
```

Both use RadioGroupWithValue for `transfertodn` — use `setToValue` for literal numbers, `setToVariable` for variable references. Bridged has `failure` port only (success = call bridges, flow loses control). Default timeout: 10 seconds. Blind has no timeout (call is fully transferred).

### Virtual Agent V2 (ivr-virtualassistantvoice)

```json
{
  "activityName": "ivr-virtualassistantvoice",
  "connector": "NATIVE_ADVANCED_VIRTUAL_AGENT",
  "connector:name": "Webex AI Agent (Autonomous)",
  "connector_name": "Webex AI Agent (Autonomous)",
  "virtualAgentId": "<agent-id>",
  "terminationDelay": 30,
  "speakingRate": 1,
  "volumeGain": 0,
  "pitch": 0,
  "transcript": true
}
```

Connector values are named constants, NOT UUIDs: `NATIVE_ADVANCED_VIRTUAL_AGENT` (Autonomous) or `NATIVE_BASIC_VIRTUAL_AGENT` (Scripted). Resolve agent IDs via cascading choices: `wxcli cc-flow list-activity-choices PROJECT_ID ivr-virtualassistantvoice virtualAgentId --parent-input-name connector --parent-value NATIVE_ADVANCED_VIRTUAL_AGENT`. Output ports: `ENDED`, `ESCALATE`, `error`.

### Case Statement (case-statement)

```json
{
  "activityName": "case-statement",
  "expression": "{{varName}}"
}
```

Group: `enum-gateway`. Output ports are DYNAMIC — one per case value. Edge conditions must match case values exactly. Include `error` port.

### Percent Allocation (percent-allocation)

```json
{
  "activityName": "percent-allocation",
  "allocations": [
    {"percent": 70, "desc": "PathA"},
    {"percent": 30, "desc": "PathB"}
  ]
}
```

Group: `logic`. Allocations must be objects (NOT stringified JSON). Percentages must sum to 100. Edge conditions use the `desc` values. Include `error` port.

### Record (record)

```json
{
  "activityName": "record",
  "playStartTone": true,
  "silenceTimeout": 4,
  "maxRecordingTime": 30,
  "terminationSymbol": "#",
  "terminationSymbol:name": "#",
  "terminationSymbol_name": "#"
}
```

**Warning:** `record` uses `terminationSymbol` (Select pattern with `:name`/`_name`). `ivr-collectdigits` uses `terminatorSymbol` (plain string). Different names — using the wrong one causes FC1015.

### Scheduled Callback (scheduled-callback)

```json
{
  "activityName": "scheduled-callback",
  "callbackDn": "{{NewPhoneContact.ANI}}",
  "callbackQueue": "<queue-uuid>",
  "callbackQueue:radioName": "setToValue",
  "callbackQueue_radioName": "setToValue",
  "callbackQueue:name": "Queue-1",
  "callbackQueue_name": "Queue-1",
  "scheduleDate": "{{cbDate}}",
  "scheduleStartTime": "{{cbStartTime}}",
  "scheduleEndTime": "{{cbEndTime}}",
  "scheduleTimezone": "America/New_York",
  "scheduleTimezone:radioName": "setToValue",
  "scheduleTimezone_radioName": "setToValue"
}
```

Most complex RadioGroupWithValue activity — both `callbackQueue` and `scheduleTimezone` need `:radioName`/`_radioName` suffix fields.

### Queue To Agent (queue-to-agent)

```json
{
  "activityName": "queue-to-agent",
  "destinationVariable": "{{agentEmail}}",
  "destinationLookupType": "agentEmail",
  "channelType": "TELEPHONY",
  "reportingQueue": "<queue-uuid>",
  "reportingQueue:name": "Queue-1",
  "reportingQueue_name": "Queue-1",
  "recoveryQueue": "<queue-uuid>",
  "recoveryQueue:name": "Queue-1",
  "recoveryQueue_name": "Queue-1"
}
```

**Gotcha:** `recoveryQueue` is ALWAYS required — validation fails with FC1015 even when `parkContactToggle` is `false`.

### Advanced Queue Info (advanced-queue-info)

```json
{
  "activityName": "advanced-queue-info",
  "channelType": "TELEPHONY",
  "destination": "<queue-uuid>",
  "destination:name": "Queue-1",
  "destination_name": "Queue-1",
  "skills": {"skillRequirements": [], "relaxation": null}
}
```

**Gotcha:** `skills` is required — neither `null` nor `{}` passes. Minimum: `{"skillRequirements": [], "relaxation": null}`.

### Wait Activity (wait-activity)

```json
{
  "activityName": "wait-activity",
  "duration": "00:00:05"
}
```

Duration format: `HH:MM:SS`. Min `00:00:05`, max `72:00:00`.

### GoTo / Hand-Off (hand-off)

```json
{
  "activityName": "hand-off",
  "handOffFlow": "<entry-point-uuid>"
}
```

Group: `logic`. Resolve entry point UUIDs via `wxcli cc-flow list-activity-choices PROJECT_ID hand-off handOffFlow`. **Note:** Validation always warns FC1015 "GoTo destination is missing" — create succeeds anyway.

## Event Flows

Minimum required: OnGlobalError. All downstream nodes (Play Message, Disconnect, etc.) must be inside the event flow's `nodes` array — they CANNOT be in the main flow's `nodes` array.

**Gotcha:** Event flow edges cannot reference main flow nodes. If your error handler wires to a Play Message and then a Disconnect, both must be declared in `eventFlows.GLOBAL_EVENTS.nodes`, not in the top-level `nodes`. Putting them in the main flow causes FC1012 ("broken link in Event Flow").

Template:

```json
"eventFlows": {
  "GLOBAL_EVENTS": {
    "name": "Global Error Handling",
    "description": "Handles unrecoverable errors",
    "id": "GLOBAL_EVENTS",
    "onEvents": {
      "GlobalErrorHandling": "node-event-error"
    },
    "nodes": [
      {"id": "node-event-error", "name": "OnGlobalError", "activityType": "event", "group": "action",
       "properties": {"activityName": "event", "eventSourceName": "WebexContactCenter",
                      "eventClassificationName": "VoiceInteractions",
                      "eventSpecificationName": "GlobalErrorHandling"}},
      {"id": "node-error-msg", "name": "ErrorMsg", "activityType": "action", "group": "action",
       "properties": {"activityName": "play-message", "toggle": true,
                      "promptsTts": [{"name": "Error message.", "type": "tts", "value": "Error message."}],
                      "prompts": null,
                      "connector": "Cisco Cloud Text-to-Speech",
                      "connector_name": "Cisco Cloud Text-to-Speech",
                      "connector:name": "Cisco Cloud Text-to-Speech",
                      "connector_type": "Cisco Cloud Text-to-Speech",
                      "connector:type": "Cisco Cloud Text-to-Speech",
                      "speakingRate": 1, "volumeGainDb": 0}},
      {"id": "node-disconnect-error", "name": "DisconnectError", "activityType": "end",
       "group": "terminating-action", "properties": {"activityName": "disconnect-contact"}}
    ],
    "edges": [
      {"id": "ev1", "from": "node-event-error", "to": "node-error-msg", "condition": "out", "properties": {}},
      {"id": "ev2", "from": "node-error-msg", "to": "node-disconnect-error", "condition": "default", "properties": {}}
    ]
  }
}
```

## Common Validation Errors

| Code | Message | Fix |
|------|---------|-----|
| FC1015 | Required field not configured | Check `wxcli cc-flow show-activity PROJECT_ID ACTIVITY` for required fields. Common: missing Set Variable double declaration, missing connector fields |
| FC1002 | Start activity not found | Ensure one node has `activityName: "start"` with `activityType: "start"` |
| FC1004 | Isolated activities | Wire all nodes — every node must be reachable from start. This is a warning, not an error |
| FC1007 | Add descriptions for activities | Cosmetic warning — safe to ignore |
| FC0000 | Validation pipeline error | Internal validator issue — safe to ignore if no other errors |

## Key Gotchas

1. **queueId vs destination**: The choices API uses `destination` but the validator requires `queueId`. Use `wxcli cc-flow list-activity-choices PROJECT_ID queue-contact destination --parent-input-name channelType --parent-value TELEPHONY` to find values, put them in `queueId`.
2. **RadioGroupWithValue suffix fields**: Fields like `callbackQueue`, `scheduleTimezone`, `surveyMethod` need `:radioName` and `_radioName` suffix fields alongside the value.
3. **Feature-gated activities**: `flow-test-activity`, `LiveCallerSentiment`, `queue-reservation` historically returned ACTIVITY_NOT_FOUND on create despite passing validation; as of 2026-07-11 they were gone from the live prod registry entirely (52 activities then). Re-checked live 2026-10-19: they are hidden by default, not gone — absent from `wxcli cc-flow list-activities PROJECT_ID` (54 activities) and listed with `--check-ui-enabled true` (57) [`flow-designer-flowir.md` § 8]. Do not use them in FlowIR.
4. **Subflows import ONLY with the query param**: `wxcli cc-flow create-import PROJECT_ID --json-body file://file.json --flow-type SUBFLOW` works (verified live 2026-07-11, run then as wxcc-flow create file.json --type SUBFLOW) — the `flowType: "SUBFLOW"` body field alone is ignored and `end-subflow` then returns ACTIVITY_NOT_FOUND. Node shapes: start = `activityName: "start"` / `activityType: "start-subflow"`; end = `activityName: "end-subflow"` / `activityType: "end"`. Dry-run validate always runs in FLOW context (no flowType param), so validate subflows post-create with `wxcli cc-flow list-validate PROJECT_ID ID --version-id draft --flow-type SUBFLOW` (expect a cosmetic FC1024 on the start node; publish still works).
5. **fn-activity**: Requires a function ID. Create the function with `wxcli cc-functions create --json-body file://fn.json` and publish it with `wxcli cc-functions publish ID --json-body '{"tags":["Live"],"comment":"…"}'` — the Custom Functions API on the regional CC gateway [`custom-functions.md` § Lifecycle]. Using a function made this way from `fn-activity` follows from `custom-functions.md` (a published function can be referenced from a flow) and was not run live. (History: this gotcha said the function "must be created manually in the UI first (flow-store has no Functions API)"; the Flow Store indeed has none, but the gateway does.) `subflow-handoff` no longer has this limitation — create the subflow programmatically (gotcha 4), publish it, and reference its ID in `subflowVersion`.
6. **Activity output variable references (FC1038)**: `{{ActivityName.OutputVar}}` expressions fail FlowIR validation. Key design patterns to avoid FC1038:
   - **Single-digit choices:** Use `ivr-menu` (Menu) instead of `ivr-collectdigits` + `condition-activity`. Menu routes by digit via edge conditions (`"1"`, `"2"`) without referencing output variables.
   - **HTTP responses:** Use `outputVariableArray` to capture JSON paths into declared flow variables.
   - **Queue position/EWT:** Use static TTS text instead of `{{GetQueueInfo.PositionInQueue}}` — the output variable can't be captured into a flow variable via any mechanism.
   - **General rule:** Any `{{ActivityName.OutputVar}}` in a Condition expression, Set Variable literal, or TTS prompt triggers FC1038. Redesign to avoid the reference.
7. **Global variables need full metadata**: Global variables like `Global_Language` must be declared in the `variables` array with `source: "GLOBAL"` (what stored flows hold, verified live 2026-10-19; `"GLOBAL_TM"`, named here until then, also passes validate) [`flow-designer-flowir.md` § 3] and their org-wide UUID `id`. Without these, Set Variable creates a local shadow that doesn't affect TTS or Analyzer. Get the metadata via `wxcli cc-flow-store list-global-variables PROJECT_ID --fields variables`.
8. **Queue creation is outside Flow APIs**: `wxcli` (the `cc-flow*` and `cc-functions` groups) and the MCP server can look up queues but cannot create them. Use the WxCC Provisioning API — `wxcli cc-queue create-contact-service-queue --json-body file://queue.json` created a queue live on 2026-10-19 (direct curl is the raw-HTTP fallback) — see `docs/reference/wxcc-provisioning-api.md` for the fields it needs.
9. **Queue Contact edges**: wire `default` for the hold treatment path. Verified live 2026-10-19 (node with `queueId` and `channelType`): the activity definition lists `default` and `failure`, `wxcli cc-flow create-validate` accepts both, and `wxcli cc-flow create-import` warns only on `failure` (`Condition 'failure' is not valid for activity 'queue-contact'. Use one of: default`) [`flow-designer-flowir.md` § 7 `queue-contact`]. (History: this gotcha said the validator warns on `default` and suggests `failure` — the reverse of what import says on 2026-10-19.) Using `failure` alone would only wire the error path.
10. **Create CC resources with `--json-body`**: `wxcli cc-team create --json-body '{"name":"…","siteId":"…","active":true,"teamType":"AGENT","teamStatus":"IN_SERVICE"}'` sends the JSON as the request body (verified live 2026-10-19: created, read back with `wxcli cc-team show`). (History: until the generator fix of 2026-10-13, ADR-16, `wxcli cc-team create --team-dto` sent the JSON as a query parameter, and this gotcha said to use direct `curl` calls; curl stays as the raw-HTTP fallback.)

## CLI Command Reference

| Command | Purpose |
|---------|---------|
| `wxcli cc-flow show-starter-flow [NAME]` | Get a starter FlowIR template |
| `wxcli cc-flow show-node-template PROJECT_ID ACTIVITY` | Get a FlowIR node template with property hints |
| `wxcli cc-flow show-activity PROJECT_ID ACTIVITY` | Show all input fields, types, required flags |
| `wxcli cc-flow list-activity-choices PROJECT_ID ACTIVITY INPUT_NAME` | Resolve entity IDs (queues, connectors, schedules) |
| `wxcli cc-flow create-validate PROJECT_ID --json-body file://FLOW_FILE` | Dry-run validate FlowIR (no save) |
| `wxcli cc-flow create-import PROJECT_ID --json-body file://FLOW_FILE` | Import flow from FlowIR JSON |
| `wxcli cc-flow export PROJECT_ID FLOW_ID --version draft` | Export flow as FlowIR for verification |
| `wxcli cc-flow publish FLOW_ID PROJECT_ID` | Publish a draft flow (always validates first; the skip-validation flag was dropped in the 2026-10-26 spec sync when upstream removed the `skipValidation` query parameter) |
| `wxcli cc-flow list-connectors PROJECT_ID` | List all available connectors (TTS + HTTP) |
| `wxcli cc-flow-store list-global-variables PROJECT_ID --fields variables` | List org global variables |

## Validated Examples

Working FlowIR examples in `docs/examples/flowir/`:

| File | Pattern |
|------|---------|
| `simple-inbound.json` | Greeting → Queue → Hold Music → Disconnect |
| `menu-routing.json` | Menu → digit branches → multiple queues |
| `data-dip-routing.json` | Collect Digits → HTTP lookup → Condition branch → route |
| `business-hours-routing.json` | Business Hours → working/closed paths |
