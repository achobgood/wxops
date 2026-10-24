---
paths:
  - "docs/reference/flow-designer-flowir.md"
  - "docs/examples/flowir/**"
  - ".claude/skills/build-flow-programmatic/**"
---

# FlowIR Properties — Live Verification Required (CLI-first)

When working with FlowIR activity properties — writing snippets, validating flows, or documenting property tables — you MUST get the activity definition from the live API before guessing. `wxcli` (the `cc-flow*` and `cc-functions` groups) is the primary tool; the `wxcc-flow-builder` MCP server is an optional alternative if the user prefers it and it is connected.

## Mandatory Steps (CLI)

`PROJECT_ID` in the commands below is the `projectId` that `wxcli cc-flow-projects show-user-preferences` returns.

1. **Get the activity definition** via `wxcli cc-flow show-activity PROJECT_ID ACTIVITY` (add `-o json` for the raw definition) — returns the flat prod shape: `inputs` (with `children`, `required`, `defaultValue`, string `showOnCondition`, `allowedValues`, `choicesEndpoint`), `outputs`, `outputPorts`, and `activityType`
2. **Resolve field values** via `wxcli cc-flow list-activity-choices PROJECT_ID ACTIVITY INPUT` — supports `--search TERM` and cascading parents via `--parent-input-name PARENT --parent-value VALUE`. A 400 names the component when a field doesn't support choices (e.g. "is a 'Toggle'"). See "Reading a `choices` Failure Correctly" below — some 400s/502s do NOT mean the activity or field is missing
3. **Get a node template** via `wxcli cc-flow show-node-template PROJECT_ID ACTIVITY` — required properties, conditional properties, import field overrides (e.g. queue-contact `destination` → `queueId`), and output ports
4. **Only then** write the FlowIR JSON and validate via `wxcli cc-flow create-validate PROJECT_ID --json-body file://FLOW_FILE`

If the user prefers the MCP server (`mcp__wxcc-flow-builder__*`: `get_activity_definitions`, `get_choices`, `get_activity_node_schema`), the same never-guess rules apply — but note the MCP layer returns the older `inputGroups` shape and its `list_flows` is broken; the CLI is authoritative when they disagree.

## Hard Rules

- NEVER guess property names from exported flows — export format may differ from import format (e.g., queue-contact uses `destination` in exports but requires `queueId` for import)
- NEVER assume a field is required/optional without checking the activity definition's `required` flag and `showOnCondition`
- NEVER declare a finding based on trial-and-error without first reading the live definition (`wxcli cc-flow show-activity`)
- NEVER assume a validation error means a field is "always required" — check whether you have other fields misconfigured first
- On any 500/404 from the CLI: the path moved — re-pull the live contract (`GET {base}/v3/api-docs`) and compare it with what the command sent (`--debug`); do not theorize

## Reading a `choices` Failure Correctly

Step 2 (`wxcli cc-flow list-activity-choices PROJECT_ID ACTIVITY INPUT`) has two known failure modes that do NOT mean what they appear to mean. A `choices` 400 or 502 is NEVER evidence that the activity or field does not exist — `wxcli cc-flow show-activity` is authoritative for whether an activity exists and what its inputs are.

**400 `"Activity 'X' not found in registry for org=… flowType=FLOW"`** — `choices` resolves against a DIFFERENT server-side registry than `activities`/`describe`, and the two disagree about which activities exist. Verified live 2026-07-25: `choices ReceiveMessage channelType` (and `channelName`, and `SendCustomMessage messageType`) each returned this 400, while in the same session/org/flowType `activities -o json` listed all 50 activities INCLUDING `ReceiveMessage` and `SendCustomMessage`, and `describe ReceiveMessage -o json` returned a full definition (`category: core`, `group: action`, `activityType: action`, inputs channelType/channelName/timeout/appendToTranscript/outputVariableArray1/flowDecryptAccess). Not a blanket outage — the control `choices queue-contact channelType` returned HTTP 200 with 3 static choices in the same session. Take the field value from `describe`'s `allowedValues`/`defaultValue` or from the Flow Designer UI.

⚠ **RESOLVED 2026-07-25 — open item O3. The answer is the pessimistic one: these two activities CANNOT be built via the API.** `validate` runs in two stages against two different registries:

1. **Port/condition checks** resolve against the `describe` registry. A wrong port returns a precise, activity-aware error: `Condition 'out' is not valid for activity 'ReceiveMessage'. Use one of: error, timeout` — proof the activity resolved.
2. **Once the port checks pass**, the server import pipeline returns HTTP 500 `ACTIVITY_NOT_FOUND` — `"Activity Mapping for ReceiveMessage could not be found"`.

Reproduced live for BOTH `ReceiveMessage` and `SendCustomMessage`; a baseline flow without them returned `valid: true` in the same session, so this is not a pipeline outage. **Consequence: a `choices` 400 "not found in registry" IS a true signal that the activity is unbuildable via the API** — it does not mean the activity is fictional (`describe` still documents it correctly, and it may exist in the UI), but it does mean you cannot import a flow containing it. Author such flows in the Flow Designer UI, or choose a different activity. The stage-1 port error is a trap: it looks like the only problem, and fixing it merely surfaces the real one.

**HTTP connectors are listable as of 2026-10-19.** Verified live on the CC Bootcamp Sandbox: `wxcli cc-flow list-activity-choices PROJECT_ID http-request-v2 connectorId` returned 200 with 4 connectors (`Webex_API_ReadWrite`, `IMI OAuth Client Credential`, `Convox-HTTPConnector`, `Webex_API_Ready_Only`), and `wxcli cc-flow list-connectors PROJECT_ID` returned 7 (those 4 HTTP connectors plus the TTS connectors `ChirpTTS`, `Google Bootcamp Connector`, `Cisco Cloud Text-to-Speech`) with no failing source on stderr. A `create-validate` of an `http-request-v2` node in authenticated mode with a connector from that list passed. So take `connectorId` from discovery; if a source fails again, `list-connectors` names it on stderr.

History — **502 wrapping an upstream `401 Unauthorized`**, verified live 2026-07-25 on `choices http-request-v2 connectorId`, where the 401 came from `GET /v1/config/organization/{orgId}/credentials`. Consistent with wxcc-flow connectors (today `wxcli cc-flow list-connectors PROJECT_ID`) returning ONLY the single TTS connector (`Cisco Cloud Text-to-Speech`) and no HTTP/Custom connectors. It was read then as a token-scope limit, not a missing field: `http-request-v2` in authenticated mode requires `connectorId`, so that mode could not be configured from discovery alone and the ID had to come from elsewhere (Control Hub UI). It did not reproduce on 2026-10-19 (above); why it was fixed is not known. ⚠ Still UNTESTED: whether a known connector ID that discovery does **not** list is ACCEPTED on import — do not assert either way.

Neither case licenses guessing. When `choices` fails, fall back to `describe`/`schema` or an authoritative UI value — never to training data or an invented value.

## Known API Layer Mismatches

Property names in the activity definition API may differ from what the import validator accepts. When in doubt, test with BOTH the definition field name and the schema/template field name. Document any mismatches in `flow-designer-flowir.md` § 11 "Property Name Mismatches Between API Layers."

## If the CLI Is Unavailable

If `wxcli` errors on auth (401), tell the user to regenerate the token at developer.webex.com — do not fall back to guessing. The MCP server (if connected) can serve as a backup for activity definitions and choices, subject to the same never-guess rules.
