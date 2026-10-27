<!-- ref-tag: fd-flowir-v9 -->

# Flow Designer FlowIR Reference

FlowIR is Cisco's intermediate representation format for Flow Designer flows. It is the documented, API-supported format for programmatic flow building via the v2 REST API and MCP server. FlowIR is NOT the proprietary export JSON — the server resolves FlowIR into the full internal format (activity UUIDs, connector IDs, event spec IDs, diagram coordinates) automatically.

## 1. REST API Endpoints

Base URL: `https://flow-store.produs1.ciscoccservice.com/flow-store`
Auth: `Authorization: Bearer <token>` header

> ⚠️ **Path structure (verified live on produs1, 2026-07-11):** the `v2` segment comes **after**
> `project/{projectId}`, NOT before `{orgId}`. The `/v2/{orgId}/project/{projectId}/...` form 500s on
> prod (unrouted path). If these ever 500/404, re-pull the live contract `GET {base}/v3/api-docs` and diff.
> "FlowIR" is our coined term; Cisco's schema is **FlowV2** (FDL 2.0).

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/{orgId}/project/{projectId}/v2/flows:import?overwrite=` | Create flow from FlowV2 → `201`, returns `{"flow":{...}}` |
| POST | `/{orgId}/project/{projectId}/v2/flows:validate` | Dry-run validate FlowV2 (no save) → `{valid, errors, warnings}` |
| GET | `/{orgId}/project/{projectId}/v2/flows/{flowId}` | Read flow as FlowV2 (use this for export/draft) |
| POST | `/{orgId}/project/{projectId}/v2/flows/{flowId}?expectedVersion=N` | Save draft from FlowV2 (optimistic lock — a wrong N is rejected with `409`, but the draft version stays `0`, see § 9 Step 6; **no `/draft` suffix**) |
| GET | `/{orgId}/project/{projectId}/v2/flows/{flowId}:validate` | Validate a persisted flow → `{valid, results}` |
| GET | `/{orgId}/project/{projectId}/v2/activities` | List activity definitions (flat list, keyed by `activityName`) |
| GET | `/{orgId}/project/{projectId}/v2/activities/{name}` | Describe one activity |
| GET | `/{orgId}/project/{projectId}/v2/activities/{name}/inputs/{input}/choices` | Dropdown values |
| GET | `/{orgId}/project/{projectId}/v2/event-specifications` | Event source/classification/specification triplets → `{specifications, quick_start}` (added to prod 2026-07) |
| GET | `/{orgId}/project/{projectId}/v2/flow-template` | Server-side starter skeleton → `{flow, notes, canonical_minimal_flow, checklist}` (added to prod 2026-07) |

The `orgId` and `projectId` are required in all paths. Resolve `projectId` via `GET /{orgId}/project`.

⚠️ The path is **kebab-case**: `/v2/event-specifications`. The camelCase spelling
`/v2/eventSpecifications` returns `500 "Oops... Something broke..."` (verified live 2026-07-24).

### 1a. Public Gateway vs. Flow Store Host

Cisco publishes these operations under the **regional Webex CC gateway** (see the
[Flow Orchestration guide](https://developer.webex.com/webex-contact-center/docs/api/guides/flow-orchestration),
labelled Beta). The gateway serves only the publicly documented subset — the full
93-operation surface the `cc-flow*` command groups use requires the Flow Store host. Verified live 2026-07-25:

| Request | Flow Store host | `api.wxcc-us1.cisco.com` |
|---|---|---|
| `/{orgId}/project/{projectId}/flows`, `/v2/activities`, `/v2/event-specifications`, `/templates` | 200 | 200 |
| `/v2/flow-template`, `/flows/global-variables`, `/flows/versions`, `/{orgId}/userPreferences`, `/build_info` | 200 | **404** |
| `/v1/{orgId}/functions` (Custom Functions) | **404 / 500** | 200 |

The gateway also accepts the documented flow paths with a `/flow-store` prefix
(`/flow-store/{orgId}/project/{projectId}/flows`) — byte-identical response.

| Region | Base URL |
|---|---|
| US | `https://api.wxcc-us1.cisco.com` |
| ANZ | `https://api.wxcc-anz1.cisco.com` |
| UK | `https://api.wxcc-eu1.cisco.com` |
| EU (Frankfurt) | `https://api.wxcc-eu2.cisco.com` |
| Japan | `https://api.wxcc-jp1.cisco.com` |
| Canada | `https://api.wxcc-ca1.cisco.com` |
| Singapore | `https://api.wxcc-sg1.cisco.com` |
| India | `https://api.wxcc-in1.cisco.com` |

Two gotchas from the guide:

- **`orgId` must be the organization UUID** (e.g. `8eb7da9a-c81c-4d13-b08b-38fdeb7330d8`). The Spark-encoded org ID some generic Webex APIs return is rejected by this gateway.
- **`projectId` is always `5e5c9ad6d61f870d6d778c1b`** — a system-generated value identical across orgs and environments.

Scopes: `cjp:config_read` for the discovery calls (activities, choices,
event-specifications), `cjp:config_write` for validate and import.
`GET .../v2/flows/{flowId}:export` works: verified live 2026-10-19 on the CC Bootcamp Sandbox, it
returned 200 on a published flow (`CCBootCampTest`) on the Flow Store host above and on the regional
gateway (`https://api.wxcc-us1.cisco.com`, with and without the `/flow-store` prefix); so did the v1
`GET .../flows/{flowId}:export`. `wxcli cc-flow export PROJECT_ID FLOW_ID --version latest` calls it on the
gateway [`contact-center-routing.md` § 11]. The v1 trailing-slash form `.../flows/{flowId}:export/` answered
200 on the Flow Store host only. The read endpoint (`GET .../v2/flows/{flowId}`) still returns the
FlowV2 draft. (History, July 2026: `:export` returned `400 "Invalid flowId"` even on published flows, so
this section called it a dead route; that did not reproduce on 2026-10-19.) There is no
`.../activities/{name}/schema` endpoint on prod.

## 2. FlowIR Structure

```json
{
  "name": "Flow_Name",
  "flowType": "FLOW",
  "contactType": "telephony",
  "description": "...",
  "variables": [],
  "nodes": [],
  "edges": [],
  "eventFlows": {},
  "preferences": [
    { "name": "hideSecureCADWarning", "type": "Boolean", "value": "true" }
  ]
}
```

### Top-level fields

| Property | Type | Notes |
|---|---|---|
| `name` | string | Must be unique in the project unless you import with `overwrite=true` (otherwise `409 Conflict`). |
| `flowType` | enum | `FLOW` or `SUBFLOW`. |
| `contactType` | string | Channel type — `telephony`, `customMessaging`, `workItem`, `genericAction`. |
| `description` | string | Human-readable description. |
| `version` | integer | Monotonically increasing. **Server-assigned — do not set it on import.** |
| `status` | enum | `Draft` or `Published`. Server-managed. |
| `nodes` | array | Main-process activity nodes. Must contain exactly one `start` node. |
| `edges` | array | Main-process edges. |
| `variables` | array | Flow variables. |
| `eventFlows` | object | Event-handler process — see § 6. |
| `preferences` | array | Flow-level settings, each `{name, type, value}` (e.g. `hideSecureCADWarning` / `Boolean` / `"true"`). |

### flowType Values

| Value | Usage |
|-------|-------|
| `FLOW` | Main flow (inbound voice, etc.) |
| `SUBFLOW` | Reusable subflow |

### Edge condition aliases

The server normalizes two aliases before matching an edge's `condition` against
the source activity's `outputPorts[].condition`:

| You write | Server reads |
|---|---|
| `done` | `out` |
| `defaultBranch` | `default` |

### Activities with no success port

Some activities expose **only** error ports — every entry in `outputPorts[]` has
`isErrorPath: true`. `ivr-collectdigits` is the clearest case: its ports are
`timeout`, `invalid`, and `error`, with no success port at all.

For `ivr-collectdigits`, write the success edge as `condition: "default"` — the form a
Designer-built flow stores. Verified live 2026-10-19 on the CC Bootcamp Sandbox:

| Success edge | `create-validate` (dry run) | `create-import` | Stored in a Designer-built flow |
|---|---|---|---|
| `condition: "default"` | **rejected** — `Condition 'default' is not valid for activity 'ivr-collectdigits'.` (`Use one of: error, invalid, timeout`) | accepted, **0** preflight warnings; read back as `default` | yes — `CCBootCampTest` (`CollectAcct` → `default`; recorded as Designer-built in `contact-center-routing.md` § 11, provenance not re-checked) |
| no `condition` field | `valid: true` | not tried | no flow read stores it |

So validate rejects `default` although import accepts it and a stored flow uses it, and an edge with no
`condition` is what validate passes. Which form fires at runtime is not verified (no call placed). (History, verified live
2026-07-25: `"default"`, `"out"` and `"done"` all failed validation and omitting `condition` validated
clean, so this section said to omit it; the 2026-10-19 validate results are the same, only the
recommendation changed to the stored form.) Check
`wxcli cc-flow show-activity PROJECT_ID ACTIVITY` before wiring an activity's success path.

## 3. Variables

```json
{
  "name": "varName",
  "type": "STRING",
  "value": "",
  "isReportable": false,
  "isCAD": false,
  "isAgentEditable": false,
  "isSecure": false,
  "isExternalized": false,
  "desktopLabel": "",
  "description": ""
}
```

| Field | Required | Values |
|-------|----------|--------|
| `name` | Yes | Variable name |
| `type` | Yes | `STRING`, `INTEGER`, `BOOLEAN` |
| `value` | Yes | Default value (string, even for INTEGER — use `"0"`) |
| `isReportable` | No | Whether variable appears in Analyzer |
| `isCAD` | No | Call-associated data |
| `isAgentEditable` | No | Agent can modify on desktop |
| `isSecure` | No | Encrypted storage |
| `isExternalized` | No | Externalized to global scope |
| `desktopLabel` | No | Label shown to agent on desktop |
| `source` | Conditional | `"GLOBAL"` for org-wide global variables — the value every stored flow read on 2026-10-19 holds (see below). Omit for flow-local variables. |
| `id` | Conditional | UUID of the global variable (from `wxcli cc-flow-store list-global-variables PROJECT_ID -o json --fields variables`, or `wxcli cc-global-vars list-cad-variable -o json`). Required when `source` is `"GLOBAL"`. Omit for flow-local variables. |
| `overwrite` | No | Whether flow can overwrite the global variable's default value |

### Global Variables in FlowIR

Global variables (e.g., `Global_Language`, `Global_VoiceName`, `Global_FeedbackSurveyOptIn`) are org-wide variables managed in Control Hub. To use one in a FlowIR flow, you MUST declare it in the `variables` array with its global metadata — otherwise Set Variable activities that reference it will silently fail to set the global value.

```json
{
  "name": "Global_Language",
  "description": "System-defined variable to store the language",
  "type": "STRING",
  "value": "en-US",
  "isCAD": true,
  "desktopLabel": "Customer Language",
  "isAgentEditable": false,
  "source": "GLOBAL",
  "isReportable": true,
  "overwrite": false,
  "isSecure": false,
  "id": "1db241b4-21a0-4819-a258-4ebc649a8bfe",
  "isExternalized": false,
  "resourceType": ""
}
```

**`source` is `"GLOBAL"`.** Verified live 2026-10-19 on the CC Bootcamp Sandbox: every global variable declared in the stored flows read (`Record_Agent_Greeting`, a Cisco-authored flow, and `Retail_IVR_Test` — five variables, including `Global_Language`, `Global_VoiceName` and `AuthKey`) carries `source: "GLOBAL"`; none carries `"GLOBAL_TM"`. `create-validate` passes the `Global_Language` object above with either value, so validate does not tell them apart. `"GLOBAL_TM"` is therefore "also accepted by validate, not what the stored flows hold"; how a `GLOBAL_TM` declaration behaves on a live call is untested. (History: until 2026-10-19 this section, its example and § 11 said `"GLOBAL_TM"`.)

**How to get the global variable metadata:** Run `wxcli cc-flow-store list-global-variables PROJECT_ID -o json --fields variables` — this returns the full object for each global variable including `id`, `source`, `isCAD`, `desktopLabel`, and `isReportable`. Copy the entire object into your FlowIR `variables` array, then make sure `source` is `"GLOBAL"`.

> **Unverified:** the `source` value inside the `list-global-variables` objects was not recorded on 2026-10-19; a read of that command's output settles whether the copied object already says `"GLOBAL"`.

**Gotcha:** A flow-local variable named `Global_Language` (without `source: "GLOBAL"` and `id`) will NOT control the TTS language. The `source` and `id` fields are what link the flow variable to the org-wide global. Without them, Set Variable sets a local variable that shadows the global but doesn't affect the TTS engine.

Variable expressions use `{{double braces}}`:
- `{{NewPhoneContact.ANI}}` — start node output
- `{{varName}}` — flow variable
- `{{varName + 1}}` — arithmetic expression
- `{{ActivityName.OutputVar}}` — activity output variable

## 4. Nodes

```json
{
  "id": "node-unique-id",
  "name": "DisplayName",
  "activityType": "start|action|end|event",
  "group": "group-name",
  "properties": {
    "activityName": "activity-type-from-registry",
    ...activity-specific properties...
  }
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `id` | Yes | Unique within the flow. Any format works; server may normalize. |
| `name` | Yes | Display name on canvas. Also used as edge `from`/`to` reference after save. |
| `activityType` | Yes | `start` (one per flow), `action` (most activities), `end` (disconnect, end-subflow), `event` (event handlers) |
| `group` | Conditional | Required for certain activity types — see Activity Reference below |
| `properties.activityName` | Yes | Must match the registry name exactly |

### activityType Mapping

| activityType | Used By |
|-------------|---------|
| `start` | `NewContact` (start node) |
| `action` | All core and logic activities |
| `end` | `disconnect-contact`, `end-subflow`, `end` |
| `event` | Event handler triggers in `eventFlows` |

## 5. Edges

```json
{
  "id": "edge-unique-id",
  "from": "node-id-or-name",
  "to": "node-id-or-name",
  "condition": "port-condition",
  "properties": {}
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `id` | No | Optional. Verified live 2026-10-19: `create-validate` returned `valid: true` with an `id` on every edge and with every `id` removed, and edges read back with no `id` either way (the server does not persist edge ids — § 9 Step 6). (History: this row said "Yes — unique within the flow" until 2026-10-19.) |
| `from` | Yes | Source node ID or name |
| `to` | Yes | Target node ID or name |
| `condition` | Yes | Must match an output port from the source activity — see § 7 |
| `properties` | Yes | Usually empty `{}` — server may add `{"value": "condition"}` on save |

### Default Edge Conditions

| Activity Pattern | Success Port | Error/Failure Port |
|-----------------|-------------|-------------------|
| Start node | `out` | — |
| Set Variable | `out` | `error` |
| Play Message, Play Music | `default` | `error` |
| Menu (ivr-menu) | `1`, `2`, ..., `9`, `0`, `#`, `*` | `timeout`, `invalid`, `error` |
| Condition | `true`, `false` | `error` |
| Business Hours | `workingHours`, `holidays`, `override`, `default` | `error` |
| Bridged Transfer | — (no success port — see § 7 `bridged-transfer`) | `failure` |
| Blind Transfer | — (success = call transfers) | `failure` |
| Queue Contact | `default` (queued — the hold treatment path; success = agent answers) | `failure` (validate accepts it; import warns — see § 7 `queue-contact`) |
| Get Queue Info (queue-lookup) | `out` | `insufficientdata`, `failure` |
| Advanced Queue Info | `out` | `failure` |
| Set Contact Priority | `out` | `failure` |
| Escalate CDG | `out` | `error` |
| HTTP Request | `default` | — (no explicit error port) |
| Disconnect | — (terminal, no output ports) | — |

## 6. Event Flows

```json
{
  "eventFlows": {
    "GLOBAL_EVENTS": {
      "name": "Global Error Handling",
      "description": "...",
      "id": "GLOBAL_EVENTS",
      "onEvents": {
        "GlobalErrorHandling": "event-node-id"
      },
      "nodes": [...],
      "edges": [...]
    }
  }
}
```

Every flow should include a `GLOBAL_EVENTS` handler at minimum. The `onEvents` map links event specification names to the event node IDs that handle them. Nodes and edges inside `eventFlows` follow the same format as the main flow.

### ⚠️ The `eventFlows` key name is load-bearing

Two shapes deserialize; anything else returns `400 "The provided request body is
not readable"` **before validation even runs**, so you get no diagnostic pointing
at `eventFlows`. Verified live 2026-07-25 with the handler body held constant:

| `eventFlows` shape | Result |
|---|---|
| `{"GLOBAL_EVENTS": {…}}` — the keyed form above | **parses** |
| `{"nodes": [...], "edges": [...]}` — the flat form in Cisco's Flow Orchestration guide and the server's own `/v2/flow-template` | **parses** |
| `{"OnGlobalError": {…}}` — any other map key | **400 unparseable** |
| `{"eventSpecificationName": "...", "nodes": [...], "edges": [...]}` — flat plus a stray sibling key | **400 unparseable** |

Only the key changed between rows 1 and 3 — same `nodes`, same `edges`. Adding
`name`/`description`/`id`/`onEvents` to the handler does not rescue a non-standard
key. Use `GLOBAL_EVENTS` (keyed) or the bare `{nodes, edges}` (flat).

In the flat form there is no wrapper at all — the event node's
`properties.eventSpecificationName` carries the binding, and there is no
top-level `event` field.

**Gotcha — node containment:** All nodes referenced by event flow edges must be declared inside the event flow's own `nodes` array. Event flow edges CANNOT reference nodes from the main flow's `nodes` array — doing so causes FC1012 ("A broken link was found at activity X in the Event Flow"). If your error handler chains to Play Message → Disconnect, both the Play Message and Disconnect nodes must be in `eventFlows.GLOBAL_EVENTS.nodes`, not in the top-level `nodes`.

Event node properties:
```json
{
  "activityName": "Event",
  "eventSourceName": "WebexContactCenter",
  "eventClassificationName": "VoiceInteractions",
  "eventSpecificationName": "GlobalErrorHandling"
}
```

⚠️ `activityName` is **`Event`, capital E** — that is the name in the live registry
(`wxcli cc-flow show-activity PROJECT_ID Event` → `activityType: action`, `group: action`; there is no
lowercase `event` activity). Cisco's Flow Orchestration guide shows lowercase
`event` with `activityType: "event"`; on this deployment use the registry value.

The server auto-resolves `eventSourceId`, `eventClassificationId`, `eventSpecificationId` from the names.

### Available Event Specifications

Get the authoritative list with `wxcli cc-flow list-event-specifications PROJECT_ID --fields specifications` (`GET /v2/event-specifications`).
Live prod returned **20** specs on 2026-07-24, all with
`eventSourceName: "WebexContactCenter"` and `eventClassificationName: "VoiceInteractions"`.

| eventSpecificationName | Purpose |
|----------------------|---------|
| `ContactStartWorkflow` | Start node trigger (required, exactly one per flow) |
| `GlobalErrorHandling` | Unhandled error catch-all (recommended in every flow) |
| `AgentOfferContact` | Agent is offered the contact |
| `AgentContactAssigned` | Agent accepts/is assigned the contact |
| `ContactPredial` | Before outbound dial completes |
| `ContactEnded` | Contact interaction ends |
| `ContactCallbackFailed` | Scheduled callback failed |
| `ContactAniUpdated` | Caller ANI updated mid-call |
| `ContactOutboundCampaignResult` | Outbound campaign dialer result |
| `ContactReservationStarted` | Queue reservation begins |
| `FCAsk(ContactLastAgentRemoved)` | Last agent removed from contact |
| `ContactCleanup` | Contact resources released |
| `ContactDelete` | Contact deleted |
| `ContactInviteParticipant` | A participant is invited to the contact |
| `ContactPark` | Contact parked |
| `ContactStopWorkflow` | Workflow stopped for the contact |
| `ContactUpdated` | Contact record updated mid-interaction |
| `GenericActionStartWorkflow` | Start trigger for a `genericAction` contact type |
| `FlowTestEvent` | Platform test event |
| `TestEventPleaseDelete` | Platform test event |

## 7. Activity Reference — Tested Property Patterns

These patterns were validated by building real flows and confirming them with the `validate_flow` and `create_flow` APIs. Activities marked ✅ TESTED were used in flows that passed validation and were successfully created in a production sandbox.

### start (NewContact) — ✅ TESTED

```json
{
  "id": "node-start",
  "name": "NewPhoneContact",
  "activityType": "start",
  "properties": {
    "activityName": "start",
    "flowType": {
      "eventSourceName": "WebexContactCenter",
      "eventClassificationName": "VoiceInteractions",
      "eventSpecificationName": "ContactStartWorkflow"
    }
  }
}
```

Exactly one start node per flow. The server resolves event spec IDs from names. Output port: `out`.

**Both start-node names validate.** Verified live 2026-10-19 on the CC Bootcamp Sandbox, `create-validate` returned `valid: true` for this node exactly, for the `NewContact` node in `contact-center-routing.md` § 11 (`name`, `activityName` and `event` all `NewContact`, `activityId: "start"`, the three event-spec ids and names), and for that `NewContact` node renamed `NewPhoneContact` throughout. The `FC1024 Activity is not allowed for the current flow type` that `contact-center-routing.md` § 11 reports for `NewPhoneContact` (2026-10-13, inside a 43-node flow) did **not** reproduce on the starter flow. Stored flows use both: `CCBootCampTest` and `Record_Agent_Greeting` start at `NewPhoneContact`, `Retail_IVR_Test` at `NewContact`. No deliberately wrong start node was sent, so this shows only that validate did not object to either name; runtime was not tested.

> **Unverified:** `NewPhoneContact` may still return `FC1024` in a larger flow. The 2026-10-13 report came from a 43-node flow and the 2026-10-19 check used the starter flow, so nothing explains why the two differ. Validating `NewPhoneContact` inside a 43-node flow would settle it.

### play-message — ✅ TESTED

```json
{
  "activityName": "play-message",
  "toggle": true,
  "promptsTts": [{"name": "The TTS text", "type": "tts", "value": "The TTS text"}],
  "prompts": null,
  "connector": "Cisco Cloud Text-to-Speech",
  "connector_name": "Cisco Cloud Text-to-Speech",
  "connector:name": "Cisco Cloud Text-to-Speech",
  "connector_type": "Cisco Cloud Text-to-Speech",
  "connector:type": "Cisco Cloud Text-to-Speech",
  "speakingRate": 1,
  "volumeGainDb": 0
}
```

**Gotcha:** All 5 connector fields are required — `connector`, `connector_name`, `connector:name`, `connector_type`, `connector:type`. The server needs them in multiple formats.

`toggle: true` selects TTS mode (vs. audio file). `prompts: null` disables the audio file prompt. TTS text supports `{{variable}}` references.

#### The shared 5-field prompt pattern (`showOnCondition`)

Four activities — `play-message`, `ivr-menu`, `ivr-collectdigits`, `set-whisperannouncement` — expose an **identical** set of five conditional prompt fields. Documented once here; the other three cross-reference this table. Conditions verified live 2026-07-25.

| Property | Condition (`showOnCondition`) | Meaning |
|----------|-------------------------------|---------|
| `prompts` | **REQUIRED IF** `toggle == false` | Audio-file mode |
| `connector` | **REQUIRED IF** `toggle == true` | TTS mode |
| `promptsTts` | **REQUIRED IF** `toggle == true` | TTS mode |
| `toggleLanguage` | IF `connector != null && connector != Cisco Cloud Text-to-Speech` | Language/voice override |
| `voiceLanguage` | **REQUIRED IF** `toggleLanguage == true && toggle == true` | Output voice selection |

**Critical:** `toggleLanguage` and `voiceLanguage` are **UNREACHABLE** in an org whose only TTS connector is Cisco Cloud Text-to-Speech — the condition excludes that connector **by name**. Reaching either field requires provisioning a second TTS connector.

Output ports: `default`, `error`.

### ivr-menu (Menu) — ✅ TESTED

```json
{
  "activityName": "ivr-menu",
  "toggle": true,
  "promptsTts": [{"name": "Press 1 for Sales.", "type": "tts", "value": "Press 1 for Sales."}],
  "prompts": null,
  "connector": "Cisco Cloud Text-to-Speech",
  "connector_name": "Cisco Cloud Text-to-Speech",
  "connector:name": "Cisco Cloud Text-to-Speech",
  "connector_type": "Cisco Cloud Text-to-Speech",
  "connector:type": "Cisco Cloud Text-to-Speech",
  "menuOptions": [
    {"digit": "1", "label": "Sales"},
    {"digit": "2", "label": "Support"}
  ],
  "entryTimeout": "5",
  "speakingRate": 1,
  "volumeGainDb": 0
}
```

**Gotcha:** Use `menuOptions` for authoring, NOT `menuLinks`. The backend converts automatically. `menuLinks` is the stored format but `menuOptions` is the input format.

**Conditional fields:** `ivr-menu` uses the same five `showOnCondition`-gated prompt fields (`prompts`, `connector`, `promptsTts`, `toggleLanguage`, `voiceLanguage`) as `play-message` — see § "The shared 5-field prompt pattern (`showOnCondition`)" under `play-message`.

Group: `enum-gateway`. Output ports: `0`–`9`, `#`, `*`, `timeout`, `invalid`, `error`.

### set-variable — ✅ TESTED

```json
{
  "activityName": "set-variable",
  "activityId": "set-variable",
  "activityType": "logic",
  "setTo": "set-to-literal",
  "srcVariableType": "STRING",
  "srcVariable": "firstVarName",
  "literal": "value",
  "expr": "value",
  "setVariablesArray": [
    {
      "setTo": "set-to-literal",
      "srcVariableType": "STRING",
      "srcVariable": "firstVarName",
      "literal": "value",
      "expr": "value",
      "literal_invalid_error": false
    },
    {
      "setTo": "set-to-literal",
      "srcVariableType": "INTEGER",
      "srcVariable": "secondVarName",
      "literal": "0",
      "expr": "0",
      "literal_invalid_error": false
    }
  ]
}
```

**Gotcha:** MUST include BOTH the top-level fields (`setTo`, `srcVariableType`, `srcVariable`, `literal`, `expr`) AND the `setVariablesArray`. The top-level fields represent the first/primary variable assignment. Validation fails with FC1015 ("Required field 'Variable' is not configured") if top-level fields are missing.

Group: `set-variable`. Output ports: `out`, `error`.

For expressions: `"literal": "{{noInputCount + 1}}"`, `"expr": "{{noInputCount + 1}}"`.

### condition-activity — ✅ TESTED

```json
{
  "activityName": "condition-activity",
  "activityId": "condition-activity",
  "activityType": "logic",
  "expression": "{{noInputCount >= 3}}"
}
```

Group: `enum-gateway`. Output ports: `true`, `false`, `error`.

Expression syntax: `{{variable operator value}}`. Operators: `==`, `!=`, `>`, `<`, `>=`, `<=`. Boolean expressions evaluate to the `true` or `false` edge.

**Gotcha:** Do not reference activity output variables (like `{{TransferPharmacy.FailureCode}}`) unless you have declared a flow variable to capture that output. Validation returns FC1038 ("Variable 'X' is referenced but not declared").

### bridged-transfer — ✅ TESTED

```json
{
  "activityName": "bridged-transfer",
  "transfertodn": "1001",
  "transfertodn:radioName": "setToValue",
  "transfertodn_radioName": "setToValue",
  "timeout": 30
}
```

| Property | Required | Notes |
|----------|----------|-------|
| `transfertodn` | Yes | Dial number or `{{variable}}` reference |
| `transfertodn:radioName` | Yes | `setToValue` (literal) or `setToVariable` (variable ref) |
| `transfertodn_radioName` | Yes | Same value, alternate format |
| `timeout` | Yes | Seconds to wait for answer |
| `transferoutdigits` | No | DTMF digits to send after connect |

Cisco documents that the transfer is temporary and that the flow retains control: "The Bridged Transfer activity allows a call to be temporarily transferred with a flow to an external destination while retaining control of the call. ... When the third-party ends the call, the call flow continues and reengages as required, such as queuing the call to an agent." [source: https://help.webex.com/en-us/article/nhovcy4/Build-and-manage-flows-with-Flow-Designer]

Output ports: `failure` only — there is no success port to wire. **This tension is UNRESOLVED:** Cisco documents a continuation on success, yet the registry exposes no success port. Both can be true if the continuation is implicit rather than a wired edge; only a live call settles it. Author the `failure` edge (no answer, busy, error) and do not depend on a wireable success edge.

### blind-transfer — ✅ TESTED

```json
{
  "activityName": "blind-transfer",
  "transfertodn": "{{TransferTarget}}",
  "transfertodn:radioName": "setToVariable",
  "transfertodn_radioName": "setToVariable"
}
```

Same pattern as bridged-transfer but no `timeout` (the call is fully transferred, Flow Designer loses control). Output ports: `failure` only.

### business-hours — ✅ TESTED

```json
{
  "activityName": "business-hours",
  "businessHoursId": "<schedule-uuid-from-control-hub>"
}
```

| Property | Required | Notes |
|----------|----------|-------|
| `businessHoursId` | Yes | UUID of the schedule from Control Hub |
| `businessHoursVariable` | Yes | Variable containing schedule ID (alternative to static ID) |
| `businessHoursRadioGroup` | No | Selection mode |

Group: `enum-gateway`. Output ports: `workingHours`, `holidays`, `override`, `default`, `error`.

Use `wxcli cc-flow list-activity-choices PROJECT_ID business-hours businessHoursId` to list available schedules.

### disconnect-contact — ✅ TESTED

```json
{
  "id": "node-disconnect",
  "name": "DisconnectContact",
  "activityType": "end",
  "properties": {
    "activityName": "disconnect-contact"
  }
}
```

Terminal node — no output ports. Multiple disconnect nodes per flow are valid (one per terminal path).

### queue-contact — ✅ TESTED

**Minimal (recommended for FlowIR authoring):**

```json
{
  "activityName": "queue-contact",
  "queueId": "247ec630-c684-4a6b-8b05-7c9cfcdb8f36",
  "channelType": "TELEPHONY"
}
```

**`channelType` is required too.** Verified live 2026-10-19 on the CC Bootcamp Sandbox: a `queue-contact` node with only `queueId` failed `create-validate` with `FC1015 Required field 'Channel type' is not configured in activity 'QueueNode'`; adding `"channelType": "TELEPHONY"` passed. The live definition (`wxcli cc-flow show-activity PROJECT_ID queue-contact -o json`) marks `channelType` `required: true` with `allowedValues` `TELEPHONY`, `WORK_ITEM`, `CUSTOM_MESSAGING`, `CHAT`. (History: until 2026-10-19 this section said `queueId` was the only required field, and the minimal example had no `channelType`.)

The `queueId` property is the field the validator checks for the queue. It accepts a queue UUID, a queue name, or a `{{variable}}` expression. The server auto-resolves the queue type, routing algorithm, and all internal fields. Resolve available queue values via `wxcli cc-flow list-activity-choices PROJECT_ID queue-contact destination --parent-input-name channelType --parent-value TELEPHONY` (the API input name is `destination` and cascades on `channelType`, but the node property the validator checks is `queueId`).

**With optional fields:**

```json
{
  "activityName": "queue-contact",
  "queueId": "247ec630-c684-4a6b-8b05-7c9cfcdb8f36",
  "channelType": "TELEPHONY",
  "fallbackQueue": "<fallback-queue-uuid>",
  "toggle": false,
  "toggleAgentAvailability": false,
  "skills": null
}
```

| Property | Required | Notes |
|----------|----------|-------|
| `queueId` | **Yes** | Queue UUID, queue name, or `{{variable}}`. This is the field the validator checks — `destination` alone will NOT pass. |
| `channelType` | **Yes** | `TELEPHONY`, `WORK_ITEM`, `CUSTOM_MESSAGING` or `CHAT`. Omitted → `FC1015 Required field 'Channel type'` (verified live 2026-10-19) |
| `fallbackQueue` | No | Fallback queue UUID (recommended when using `{{variable}}` for `queueId`) |
| `toggle` | No | `true` to enable contact priority settings (default `false`) |
| `priority` | Conditional | Static priority value (int) — required when `toggle` is `true` |
| `toggleAgentAvailability` | No | `true` to check agent availability before queuing (default `false`) |
| `skills` | No | `null` for no skill routing; object for skill-based routing |

**Critical gotcha — DO NOT include `queueRadioGroup`:** The `queueRadioGroup` property (values `staticQueue` / `variableQueue`) switches the validator into "UI mode" where it expects the full `destination` + dual-format field set AND still requires `queueId`. Including it triggers cascading validation failures:
- `queueRadioGroup: "staticQueue"` requires `destination` + `destination:name` + `destination_name` + `destination:type` + `destination_type` AND `queueId` — omitting any one fails with FC1015.
- `queueRadioGroup: "variableQueue"` requires `destinationVariable` AND `skills` (even if null) AND `queueId` — omitting `skills` fails with FC1015 "Required field 'skills' is not configured".
- Omitting `queueRadioGroup` entirely lets `queueId` work as a complete shorthand with zero additional fields.

**Why `destination` alone fails:** The v2 import/validate API checks for `queueId` as the queue selection field. The `destination` property is the UI/export format — it appears in exported flows but is NOT what the validator checks on import. The activity definition API lists `destination` as the input name (and the choices API takes input `destination`), but the actual node property the validator requires is `queueId`. This is a naming mismatch between the activity definition layer and the validation layer.

**What exported flows look like:** When a flow is created via the `queueId` shorthand (no `queueRadioGroup`), the export preserves the shorthand format — `queueId` is present and no `destination`/`queueRadioGroup` expansion occurs. This means re-importing an exported flow that was created via FlowIR works without modification. However, flows created via the Flow Designer UI export with the full property set (`destination`, `destination:name`, `destination_name`, `destination:type`, `destination_type`, `queueRadioGroup`, etc.) — re-importing those DOES require adding `queueId`.

**Full conditional-field map (`showOnCondition`):** `queue-contact` has 12 conditional fields — the most of any activity. Verbatim from the live definition (verified 2026-07-25):

| Property | Condition (`showOnCondition`) |
|----------|-------------------------------|
| `destination` | **REQUIRED IF** `queueRadioGroup == staticQueue` |
| `destinationVariable` | **REQUIRED IF** `queueRadioGroup == variableQueue` |
| `fallbackQueue` | **REQUIRED IF** `queueRadioGroup == variableQueue` |
| `priorityRadioGroup` | IF `toggle == true` |
| `priority` | **REQUIRED IF** `priorityRadioGroup == staticPriority` |
| `priorityVariable` | **REQUIRED IF** `priorityRadioGroup == variablePriority` |
| `toggleAgentAvailability` | IF `queueRadioGroup == staticQueue && destination:queueRoutingType == TEAM_BASED` |
| `toggleAgentAvailability` | IF `queueRadioGroup == variableQueue` |
| `agentAvailabilityRadioGroup` | IF `toggleAgentAvailability == true` |
| `agentAvailabilityVariable` | **REQUIRED IF** `agentAvailabilityRadioGroup == variableAgentAvailability` |
| `skills` | **REQUIRED IF** `queueRadioGroup == staticQueue && destination:queueRoutingType == TEAM_BASED && destination:routingType == SKILLS_BASED` |
| `skills` | **REQUIRED IF** `queueRadioGroup == variableQueue` |

**⚠️ `skills` and `toggleAgentAvailability` EACH APPEAR TWICE**, with different conditions. Both are listed twice in the live definition — one entry for the static-queue path and one for the variable-queue path. Either entry firing makes the field apply, so you cannot read a single row and conclude the field is out of scope.

**⚠️ The `destination:queueRoutingType` / `destination:routingType` syntax reaches INTO the selected queue's own attributes.** These are not sibling inputs in your FlowIR — they are properties of the queue entity you selected. Whether the field applies therefore depends on **how the target queue was provisioned in Control Hub**, not on anything present in your FlowIR document. You cannot determine from the FlowIR alone whether `skills` or `toggleAgentAvailability` is in play on the static-queue path.

**Consequence:** on the static-queue path, `skills` is **unreachable** unless the org contains a queue with BOTH `queueRoutingType: TEAM_BASED` AND `routingType: SKILLS_BASED`. If no such queue exists, no static-queue configuration can ever satisfy that condition.

Output ports: `default` (queued — the hold treatment path) and `failure`. Output variables: `QueueId`, `FailureCode`, `FailureDescription`.

**What each check says about the two edges** (verified live 2026-10-19 on the CC Bootcamp Sandbox, node with `queueId` and `channelType: "TELEPHONY"`):

| Check | `default` edge | `failure` edge |
|---|---|---|
| Activity definition (`show-activity queue-contact`, `outputPorts`) | listed (`isErrorPath: false`) | listed (`isErrorPath: true`) |
| `create-validate` (dry run) | `valid: true` | `valid: true` |
| `create-import` | accepted, 0 preflight warnings | accepted, **1** preflight warning: `Condition 'failure' is not valid for activity 'queue-contact'.` (`Use one of: default`) |
| Stored flows (`CCBootCampTest`, `Retail_IVR_Test`) | `default` | — |

Both edges were stored as sent. Wire `default` for the hold treatment; a `failure` edge imports with that warning. Runtime behaviour of either edge was not tested. (History: until 2026-10-19 this section listed `failure` as the only output port, and § 11 said the validator rejects `default` and suggests `failure` — the reverse of what import says.)

### http-request-v2 — ✅ TESTED

**Mode 1: No connector (inline auth headers)**

```json
{
  "activityName": "http-request-v2",
  "authenticated": false,
  "httpRequestUrl": "https://api.example.com/endpoint",
  "httpRequestMethod": "GET",
  "httpRequestMethod:name": "GET",
  "httpRequestMethod_name": "GET",
  "httpContentType": "None",
  "httpContentType:name": "None",
  "httpContentType_name": "None",
  "contentType": "JSON",
  "contentType_name": "JSON",
  "httpRequestHeaders": {
    "Authorization": "Bearer {{AuthKey}}"
  },
  "outputVariableArray": [
    {
      "outputVariable": "targetVar",
      "jsonPathExp": "$.data.value"
    }
  ]
}
```

**Mode 2: With connector (managed auth)**

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
    {
      "outputVariable": "targetVar",
      "jsonPathExp": "$.data.value"
    }
  ]
}
```

| Property | Required | Notes |
|----------|----------|-------|
| `authenticated` | Yes | `false` = inline headers (no connector), `true` = managed connector. **Default is `true`** — omitting this requires a connector |
| `httpRequestUrl` | Yes | Full URL or `{{variable}}` |
| `httpRequestMethod` | Yes | `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `HEAD`, `OPTIONS`. Uses Select pattern (`:name`/`_name` suffix) |
| `httpContentType` | Yes | Request body content type. `None` for GET, `Application/JSON` for POST/PUT. Uses Select pattern |
| `contentType` | No | Response parse type (e.g. `JSON`). Uses Select pattern (`_name` suffix) |
| `httpRequestHeaders` | No | Key-value object for headers |
| `httpRequestBody` | No | Request body (for POST/PUT/PATCH) |
| `outputVariableArray` | No | Array of `{outputVariable, jsonPathExp}` mapping JSON paths to flow variables |
| `httpResponseTimeout` | No | Timeout in ms (default `2000`) |
| `retryAttempts` | No | Number of retries (default `1`) |
| `connectorId` | Conditional | Required when `authenticated` is `true`. Uses Select pattern. **Omit entirely when `authenticated` is `false`** — do not set to `null` |

**Gotcha:** The `authenticated` field defaults to `true`. If you omit it, the validator requires `connectorId`. There are TWO content-type fields: `httpContentType` (request body type) and `contentType` (response parse type). See the gotcha below about `authenticated: false` limitations.

**Gotcha — `authenticated: false` fails FlowIR validation:** Despite the activity definition showing `connectorId` as conditional on `authenticated == true`, the FlowIR validator returns FC1015 "Required field 'Connector' is not configured" when `authenticated` is `false` and no `connectorId` is provided. The "Mode 1" pattern above may work in the Flow Designer UI but does NOT work via the v2 import/validate API. **Workaround:** Always use `authenticated: true` with a connector for FlowIR-based flows. Use a Custom Connector configured in Control Hub, and include `connectorId` + `:name`/`_name` suffix fields.

Output ports: `default` (no explicit error port — use condition check after).

### fn-activity (Function) — FROM REAL FLOW

```json
{
  "activityName": "fn-activity",
  "fnVersionConfig": {
    "id": "<function-entity-id>",
    "tag": "Latest",
    "version": "2"
  },
  "fnInputVariables": [
    {"src": "ActivityName.outputVar", "target": "functionParamName", "type": "STRING"}
  ],
  "fnOutputVariables": [
    {"outputVariable": "flowVarName", "jsonPathExp": "$.returnField"}
  ]
}
```

Group: `fn-activity`. Output ports: `default`, `error`.

### ivr-collectdigits (Collect Digits) — ✅ TESTED

```json
{
  "activityName": "ivr-collectdigits",
  "toggle": true,
  "promptsTts": [{"name": "Enter your account number.", "type": "tts", "value": "Enter your account number."}],
  "prompts": null,
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

Same connector pattern as play-message and ivr-menu.

**Conditional fields:** `ivr-collectdigits` uses the same five `showOnCondition`-gated prompt fields (`prompts`, `connector`, `promptsTts`, `toggleLanguage`, `voiceLanguage`) as `play-message` — see § "The shared 5-field prompt pattern (`showOnCondition`)" under `play-message`.

Output ports: `timeout`, `invalid`, `error` — all three are `isErrorPath: true`, and there is
**no success port** (verified live 2026-07-25, run then as wxcc-flow describe ivr-collectdigits; today the command is `wxcli cc-flow show-activity PROJECT_ID ivr-collectdigits`). Wire the
digits-collected path with `condition: "default"`, the form stored flows hold; `create-validate`
rejects it but `create-import` accepts it with no warning (verified live 2026-10-19 — the table and
history are in § 2 "Activities with no success port"). An edge with **no `condition` field** is what
validate passes; `default`, `out`, and `done` all fail validation with
`Condition 'X' is not valid for activity 'ivr-collectdigits'` (2026-07-25, `default` again 2026-10-19).

Output variables: `DigitsEntered`, `remoteEntity`, `status`.

### ivr-virtualassistantvoice (Virtual Agent V2) — ✅ TESTED

```json
{
  "activityName": "ivr-virtualassistantvoice",
  "connector": "NATIVE_ADVANCED_VIRTUAL_AGENT",
  "connector:name": "Webex AI Agent (Autonomous)",
  "connector_name": "Webex AI Agent (Autonomous)",
  "virtualAgentId": "<agent-id-from-choices>",
  "terminationDelay": 30,
  "speakingRate": 1,
  "volumeGain": 0,
  "pitch": 0,
  "transcript": true
}
```

**Gotcha:** `terminationDelay` is in seconds (0-30), NOT milliseconds. Default is `30`. The `connector` field uses the Select pattern (`:name`/`_name` suffix) but the VALUE is a named constant (`NATIVE_ADVANCED_VIRTUAL_AGENT` or `NATIVE_BASIC_VIRTUAL_AGENT`), NOT a UUID. Available connector values: `NATIVE_ADVANCED_VIRTUAL_AGENT` (Webex AI Agent Autonomous) and `NATIVE_BASIC_VIRTUAL_AGENT` (Webex AI Agent Scripted). The `virtualAgentId` field requires a cascading choice — you must provide the connector value as a parent parameter to get the list of available agents: `wxcli cc-flow list-activity-choices PROJECT_ID ivr-virtualassistantvoice virtualAgentId --parent-input-name connector --parent-value NATIVE_ADVANCED_VIRTUAL_AGENT` (REST equivalent: `GET /{org}/project/{proj}/v2/activities/ivr-virtualassistantvoice/inputs/virtualAgentId/choices?parentInputName=connector&parentValue=NATIVE_ADVANCED_VIRTUAL_AGENT`).

**Conditional fields (`showOnCondition`)** — verbatim from the live definition (verified 2026-07-25):

| Property | Condition (`showOnCondition`) |
|----------|-------------------------------|
| `connector` | **REQUIRED IF** `configIdRadioGroup == staticConfigId` |
| `virtualAgentId` | **REQUIRED IF** `configIdRadioGroup == staticConfigId` |
| `variableSelection` | **REQUIRED IF** `configIdRadioGroup == variableConfigId` |
| `recordAutonomous` | IF `connector != null && connector:name == Webex AI Agent (Autonomous)` |
| `recordScripted` | IF `connector != null && connector:name == Webex AI Agent (Scripted)` |

**⚠️ `recordAutonomous` and `recordScripted` match the connector's DISPLAY NAME, not its value.** The condition tests `connector:name` against the human-readable labels `Webex AI Agent (Autonomous)` and `Webex AI Agent (Scripted)` — while the `connector` VALUE is `NATIVE_ADVANCED_VIRTUAL_AGENT` / `NATIVE_BASIC_VIRTUAL_AGENT`. This is a string-match dependency on a human-readable label, so the `:name` suffix fields must carry the exact label text for these two fields to apply.

**Untested path:** selecting the virtual agent by variable (`configIdRadioGroup: "variableConfigId"` + `variableSelection`) has not been round-trip tested. The tested pattern above is the static path (`staticConfigId`).

Output ports: `ENDED`, `ESCALATE`, `error`.

### play-music — ✅ TESTED

```json
{
  "activityName": "play-music",
  "prompt": "<audio-file-id>",
  "audioRadioGroup": "audioFile"
}
```

No connector fields needed (unlike play-message). Output ports: `default`, `error`.

### callback — ✅ TESTED

```json
{
  "activityName": "callback",
  "callbackDn": "{{NewPhoneContact.ANI}}",
  "callbackQueue": "<queue-uuid>"
}
```

Output ports: `failure`.

### case-statement (Case) — ✅ TESTED

```json
{
  "activityName": "case-statement",
  "expression": "{{varName}}"
}
```

Group: `enum-gateway`. Output ports are dynamic — one per case value configured. Include an `error` port.

### parse-activity (Parse) — ✅ TESTED

```json
{
  "activityName": "parse-activity",
  "inputVariable": "{{HTTPRequest.responseBody}}",
  "contentType": "JSON",
  "outputVariableArray": [
    {"outputVariable": "targetVar", "jsonPathExp": "$.path.to.value"}
  ]
}
```

Group: `parse-activity`. Output ports: `default`.

**Note:** On export, `activityId` is the literal string `"parse-activity"` (not a server-generated UUID), matching the behavior of `http-request-v2`, `percent-allocation`, `wait-activity`, and `hand-off`.

### bre-request (BRE Request) — ✅ TESTED

```json
{
  "activityName": "bre-request",
  "httpQueryParameters": {"key": "{{lookupValue}}"},
  "outputVariableArray": [
    {"outputVariable": "result", "jsonPathExp": "$.attributeValue"}
  ]
}
```

Output ports: `default`.

### subflow-handoff (Subflow) — FROM REGISTRY

```json
{
  "activityName": "subflow-handoff",
  "subflowVersion": {"id": "<subflow-id>", "tag": "Latest"},
  "automaticUpdates": true,
  "subflowInputVariables": [
    {"src": "flowVar", "target": "subflowInputVar", "type": "STRING"}
  ],
  "subflowOutputVariables": [
    {"outputVariable": "flowVar", "target": "subflowOutputVar", "type": "STRING"}
  ]
}
```

Output ports: `default`, `error`.

## 7b. Additional Activity Properties

Required-property tables for activities not covered by the full snippets in § 7. Parsed from the activity definition API (`wxcli cc-flow show-activity PROJECT_ID ACTIVITY`). The `flowDecryptAccess` toggle (boolean, optional, default `false`) appears on **45 of the 52** registry activities (counted live 2026-07-12) — it is omitted from the tables below for brevity. Its runtime purpose is documented nowhere (not in the Cisco articles, the registry payload, or this reference); it stays "not documented."

### screen-pop (Screen Pop) — ✅ TESTED

| Property | Type | Required | Notes |
|----------|------|----------|-------|
| `screenPopUrl` | string | Yes | URL to display on agent desktop |
| `queryParameters` | object | No | Key-value pairs appended as query string — values can use `{{variable}}` |
| `screenPopDesktopLabel` | string | Yes | Label shown on agent desktop |
| `target` | string | Yes | `insideDesktop` or `outsideDesktop` — uses RadioGroup (direct value, no suffix fields) |

**Gotcha:** Screen-pop has an implicit `out` success port for flow continuation, despite the registry listing no output ports. The `target` field uses RadioGroup — set the value directly.

### record (Record) — ✅ TESTED

| Property | Type | Required | Notes |
|----------|------|----------|-------|
| `playStartTone` | boolean | Yes | Play tone before recording (default `true`) |
| `silenceTimeout` | integer | Yes | Seconds of silence before stop (default `4`) |
| `maxRecordingTime` | integer | Yes | Max recording duration in seconds (default `30`) |
| `terminationSymbol` | string | Yes | Select: `#` (default) or `*` — DTMF key to stop recording |

**Gotcha — field name confusion:** The `record` activity uses `terminationSymbol` (with Select pattern: `:name`/`_name` suffixes required). The `ivr-collectdigits` activity uses `terminatorSymbol` (plain string, no suffix fields). These are different field names on different activities — using the wrong one causes FC1015.

### RecordingControl (Recording Control) — ✅ TESTED

| Property | Type | Required | Notes |
|----------|------|----------|-------|
| `enableRecording` | boolean | Yes | VariableSelect — must reference a boolean flow variable (e.g. `{{enableRec}}`). Declare the variable as `BOOLEAN` type. `filterType: "boolean"`, `valueAsPebbleTemplate: true` |

### scheduled-callback (Schedule Callback) — ✅ TESTED

| Property | Type | Required | Notes |
|----------|------|----------|-------|
| `callbackDn` | string | No | Callback number (default `{{NewPhoneContact.ANI}}`) |
| `callbackQueue` | string | Yes | Queue UUID or variable — uses RadioGroupWithValue |
| `callbackQueue:radioName` | string | Yes | `setToValue` (static) or `setToVariable` (variable ref) |
| `callbackQueue_radioName` | string | Yes | Same value, alternate format |
| `callbackQueue:name` | string | Conditional | Queue display name (when static) |
| `callbackQueue_name` | string | Conditional | Same value, alternate format |
| `customerName` | string | No | Variable holding customer name |
| `scheduleDate` | string | Yes | Variable holding date for callback (e.g. `{{cbDate}}`) |
| `scheduleStartTime` | string | Yes | Variable holding schedule window start (e.g. `{{cbStartTime}}`) |
| `scheduleEndTime` | string | Yes | Variable holding schedule window end (e.g. `{{cbEndTime}}`) |
| `scheduleTimezone` | string | Yes | Timezone value (e.g. `America/New_York`) — uses RadioGroupWithValue |
| `scheduleTimezone:radioName` | string | Yes | `setToValue` (static) or `setToVariable` (variable ref) |
| `scheduleTimezone_radioName` | string | Yes | Same value, alternate format |

**Gotcha:** RadioGroupWithValue fields require the `:radioName` / `_radioName` suffix fields alongside the value. The `callbackQueue` and `scheduleTimezone` fields both follow this pattern.

### queue-to-agent (Queue To Agent) — ✅ TESTED

| Property | Type | Required | Notes |
|----------|------|----------|-------|
| `destinationVariable` | string | Yes | Variable containing agent ID or email (e.g. `{{agentEmail}}`) |
| `destinationLookupType` | string | Yes | `agentEmail` or `agentId` (from choices API) |
| `channelType` | string | Yes | `TELEPHONY`, `CHAT`, etc. (default `TELEPHONY`) |
| `queueRadioGroup` | string | No | `staticQueue` (default) |
| `reportingQueue` | string | Yes | Queue UUID for reporting — resolve via `wxcli cc-flow list-activity-choices PROJECT_ID ACTIVITY INPUT` |
| `reportingQueue:name` | string | Yes | Queue display name |
| `reportingQueue_name` | string | Yes | Same value, alternate format |
| `destinationReportingQueueVariable` | string | Conditional | Variable alternative — required only when using variable mode |
| `priorityToggle` | boolean | No | Enable priority settings (default `false`) |
| `priorityRadioGroup` | string | Conditional | `staticPriority` or `variablePriority` — required when `priorityToggle` is `true` |
| `priority` | int | Conditional | Static priority value — required when `priorityRadioGroup` is `staticPriority` |
| `priorityVariable` | int | Conditional | Variable for priority — required when `priorityRadioGroup` is `variablePriority` |
| `parkContactToggle` | boolean | No | Park if agent unavailable (default `false`) |
| `queueRecoveryRadioGroup` | string | No | `staticRecoveryQueue` (default) |
| `recoveryQueue` | string | Yes | Recovery queue UUID — **required even when `parkContactToggle` is `false`** |
| `recoveryQueue:name` | string | Yes | Queue display name |
| `recoveryQueue_name` | string | Yes | Same value, alternate format |
| `destinationRecoveryQueueVariable` | string | Conditional | Variable alternative — required only when using variable mode |

**Gotcha:** `recoveryQueue` is always required — validation fails with FC1015 if omitted, even when `parkContactToggle` is `false`. The `priority` and `priorityVariable` fields are only required when their respective radio group mode is active.

### queue-lookup (Get Queue Info) — ✅ TESTED

```json
{
  "activityName": "queue-lookup",
  "channelType": "TELEPHONY",
  "destination": "247ec630-c684-4a6b-8b05-7c9cfcdb8f36",
  "destination:radioName": "setToValue",
  "destination_radioName": "setToValue",
  "ewtLookbackMinutes": 5
}
```

| Property | Type | Required | Notes |
|----------|------|----------|-------|
| `channelType` | string | Yes | `TELEPHONY`, `CHAT`, etc. (default `TELEPHONY`). Not exposed via the choices API — set directly |
| `destination` | string | Yes | RadioGroupWithValue — queue UUID or `{{variable}}`. The choices API returns "RadioGroupWithValue not supported" — resolve queue UUIDs via `wxcli cc-flow list-activity-choices PROJECT_ID queue-contact destination --parent-input-name channelType --parent-value TELEPHONY` instead |
| `destination:radioName` | string | Yes | `setToValue` (literal UUID) or `setToVariable` (variable ref) |
| `destination_radioName` | string | Yes | Same value, alternate format |
| `ewtLookbackMinutes` | int | Yes | Lookback window in minutes for EWT calculation (range: 5–240) |

**Gotcha — no `queueId` mismatch:** Unlike `queue-contact` (where the validator requires `queueId` instead of `destination`), `queue-lookup` accepts `destination` directly with RadioGroupWithValue suffix fields. No naming mismatch.

**Gotcha — success port:** The `describe` command only lists error ports (`insufficientdata`, `failure`), but the activity has an implicit `out` success port validated via round-trip. Connect the success path using `condition: "out"`.

Output ports: `out` (success), `insufficientdata` (valid PIQ but EWT = -1), `failure` (API error or invalid queue).

Output variables: `PIQ`, `EWT`, `status`, `CallsQueuedNow`, `OldestCallTime`, `LoggedOnAgentsCurrent`, `LoggedOnAgentsAll`, `AvailableAgentsCurrent`, `AvailableAgentsAll`, `FailureCode`, `FailureDescription`.

### advanced-queue-info (Advanced Queue Info) — ✅ TESTED

```json
{
  "activityName": "advanced-queue-info",
  "channelType": "TELEPHONY",
  "queueRadioGroup": "staticQueue",
  "destination": "247ec630-c684-4a6b-8b05-7c9cfcdb8f36",
  "destination:name": "Queue-1",
  "destination_name": "Queue-1",
  "skills": {
    "skillRequirements": [],
    "relaxation": null
  }
}
```

| Property | Type | Required | Notes |
|----------|------|----------|-------|
| `channelType` | string | Yes | `TELEPHONY`, `CHAT`, etc. (default `TELEPHONY`). Not exposed via the choices API — set directly |
| `queueRadioGroup` | string | No | RadioGroup: `staticQueue` or `variableQueue`. Can be omitted — `destination` works without it |
| `destination` | string | Conditional | Select — queue UUID (when `staticQueue`). Resolve via `wxcli cc-flow list-activity-choices PROJECT_ID ACTIVITY INPUT` on input `destination`. Uses Select pattern (`:name`/`_name` suffix) |
| `destination:name` | string | Conditional | Queue display name |
| `destination_name` | string | Conditional | Same value, alternate format |
| `destinationVariable` | string | Conditional | VariableSelect — variable containing queue UUID (when `variableQueue`) |
| `skills` | object | **Yes** | SkillRequirementsAndRelaxation — use `{"skillRequirements": [], "relaxation": null}` for no skills. **Both `null` and `{}` fail validation with FC1015** |

**Gotcha — skills format:** The `skills` field is required and neither `null` nor `{}` passes validation. The minimum valid value is `{"skillRequirements": [], "relaxation": null}`.

**Gotcha — no `queueId` mismatch:** Unlike `queue-contact`, `advanced-queue-info` uses `destination` directly as a Select field. No naming mismatch between definition and validator.

**Gotcha — success port:** The `describe` command only lists `failure`, but the activity has an implicit `out` success port validated via round-trip.

Output ports: `out` (success), `failure`.

Output variables: `PIQ`, `LoggedOnAgentsCurrent`, `LoggedOnAgentsAll`, `AvailableAgentsCurrent`, `AvailableAgentsAll`, `CurrentGroup`, `TotalGroups`, `status`, `FailureCode`, `FailureDescription`.

### escalate-cdg (Escalate Call Distribution Group) — ✅ TESTED

```json
{
  "activityName": "escalate-cdg",
  "callDistributionGroup": "nextGroup",
  "callDistributionGroup:name": "Next Group",
  "callDistributionGroup_name": "Next Group"
}
```

| Property | Type | Required | Notes |
|----------|------|----------|-------|
| `callDistributionGroup` | string | Yes | Select: `nextGroup` (Next Group) or `lastGroup` (Last Group) — NOT a UUID. Uses Select pattern (`:name`/`_name` suffix) |
| `callDistributionGroup:name` | string | Yes | Display name: `"Next Group"` or `"Last Group"` |
| `callDistributionGroup_name` | string | Yes | Same value, alternate format |

**Gotcha — error port name:** The error port is `error` (not `failure` like most queue activities). Confirmed via `describe` and round-trip.

**Gotcha — success port:** The `describe` command only lists `error`, but the activity has an implicit `out` success port validated via round-trip.

Output ports: `out` (success), `error`.

Output variables: `CurrentGroup`, `TotalGroups`, `status`, `FailureCode`, `FailureDescription`.

### set-announcement (Set Announcement) — ✅ TESTED

| Property | Type | Required | Notes |
|----------|------|----------|-------|
| `toggleAgentGreeting` | boolean | No | Enable agent greeting (default `false`) |
| `attributeTag` | string | Conditional | Two feature-flag variants exist (flag `wxcc_record_agent_personal_greeting`): (1) When flag is `off`/`control` — "Attribute tag", not required. (2) When flag is `on` — "Greeting Purpose", required with defaultValue `"Default"`. Required when `toggleAgentGreeting` is `true`. Setting just `"Default"` may fail with "tag is set but version is missing" depending on greeting assets available. |
| `toggleComplianceAnnouncement` | boolean | No | Enable compliance message (default `false`) |
| `audioFile` | audioFile | Conditional | Audio file name — required when `toggleComplianceAnnouncement` is `true`. Uses Select. Use `wxcli cc-flow list-activity-choices PROJECT_ID set-announcement audioFile` to get available files (e.g., `"defaultmusic_on_hold.wav"`) |

**Gotcha:** With both toggles off, ZERO properties beyond `activityName` are needed — the activity accepts a completely bare node. When `toggleAgentGreeting` is `true`, validation requires the `attributeTag` field — which has two feature-flag variants (see table above). The `wxcli cc-flow show-activity PROJECT_ID ACTIVITY` command now shows both variants with `[Attribute tag]` and `[Greeting Purpose]` labels. Use `toggleComplianceAnnouncement` + `audioFile` for the simpler compliance announcement path.

### send-digits (Send Digits) — ✅ TESTED

| Property | Type | Required | Notes |
|----------|------|----------|-------|
| `transferoutdigits` | string | Yes | DTMF digits to send — uses RadioGroupWithValue. Static value regex: `^(?=.*[A-D0-9*#])[A-D0-9*#,]{1,32}$`. For variable reference, use `"{{varName}}"` with `setToVariable`. |
| `transferoutdigits:radioName` | string | Yes | `setToValue` (static DTMF string) or `setToVariable` (variable reference) |
| `transferoutdigits_radioName` | string | Yes | Same value as above (alternate format required by API) |

### set-contact-priority (Set Contact Priority) — ✅ TESTED

```json
{
  "activityName": "set-contact-priority",
  "priorityRadioGroup": "staticPriority",
  "priority": 1,
  "priority:name": "P1 (Priority 1)",
  "priority_name": "P1 (Priority 1)"
}
```

| Property | Type | Required | Notes |
|----------|------|----------|-------|
| `priorityRadioGroup` | string | Yes | RadioGroup: `staticPriority` or `variablePriority` — set value directly, no suffix fields |
| `priority` | int | Conditional | Select: P1=1 through P9=9 — required when `priorityRadioGroup` is `staticPriority`. Uses Select pattern (`:name`/`_name` suffix) |
| `priority:name` | string | Conditional | Display name (e.g., `"P1 (Priority 1)"`) |
| `priority_name` | string | Conditional | Same value, alternate format |
| `priorityVariable` | int | Conditional | VariableSelect — required when `priorityRadioGroup` is `variablePriority` |

**Gotcha — success port:** The `describe` command only lists `failure`, but the activity has an implicit `out` success port validated via round-trip.

Output ports: `out` (success), `failure`.

Output variables: `status`, `FailureCode`, `FailureDescription`.

### percent-allocation (Percent Allocation) — ✅ TESTED

| Property | Type | Required | Notes |
|----------|------|----------|-------|
| `allocations` | object[] | No | Array of allocation objects (NOT stringified JSON). Each object: `{"percent": <int>, "desc": "<label>"}`. Percentages must sum to 100. Default: `[{"percent": 100, "desc": "Allocation Default"}]` |

Output ports are dynamic — one per allocation entry (using the `desc` value as the edge condition), plus `error`. Example with 60/40 split: edges use `"condition": "PathA"` and `"condition": "PathB"` matching the `desc` values.

**Gotcha:** The `describe` output reports `allocations` as type `string[]` (array of JSON strings), but the API rejects stringified JSON — validation fails with "Percent allocation values must sum to 100 (current sum: 0.0)". Use actual objects instead. The `activityId` in exports is `"percent-allocation"` (same as activityName, not a server-generated UUID). The `group` in the FlowIR input should be `"logic"` per the `describe` output.

### wait-activity (Wait) — ✅ TESTED

| Property | Type | Required | Notes |
|----------|------|----------|-------|
| `duration` | string | Yes | Format `HH:MM:SS` — UI enforces min `00:00:05` / max `72:00:00`, but API accepts values outside this range. Use Duration component format |

**Gotcha:** The `activityId` field in the export comes back as `"wait-activity"` (same as activityName) instead of a UUID — `hand-off` and `percent-allocation` also exhibit this behavior.

### hand-off (GoTo) — ✅ TESTED

| Property | Type | Required | Notes |
|----------|------|----------|-------|
| `handOffFlow` | string | Yes | Entry point UUID — uses HandOffFlow component (fetches telephony entry points from config service). Use `wxcli cc-flow list-activity-choices PROJECT_ID hand-off handOffFlow` to get valid entry point UUIDs. |

**Gotcha:** Validation always returns "GoTo destination is missing" (FC1015) even with valid entry point UUIDs — this is a validator limitation with the HandOffFlow component. Create succeeds regardless. The `group` in FlowIR input is `"logic"` (not `"action"` like most activities). On export, `activityId` is the literal string `"hand-off"` (not a server-generated UUID like other activities).

### generate-otp (Generate OTP) — ✅ TESTED

| Property | Type | Required | Notes |
|----------|------|----------|-------|
| `pinFormat` | string | Yes | `ALPHANUMERIC` (default), `NUMERIC`, or `ALPHA` — uses RadioGroup (direct value, no suffix fields) |
| `pinLength` | string | Yes | OTP length as string, valid range 4-64 (regex: `^(0*(?:[4-9]|[1-5][0-9]|6[0-4]))$`). Default `"6"` |
| `pinValidity` | string | Yes | Validity duration in seconds as string (e.g. `"300"`) |
| `pinResend` | string | Yes | RadioGroup: `GENERATE_NEW` (default) or `REUSE_SAME` |
| `transactionReference` | string | Yes | Unique transaction identifier — can use `{{variable}}` (e.g. `{{NewPhoneContact.ANI}}`) |
| `extraParameters` | object | No | Additional key-value pairs |

**Gotcha:** `pinFormat` uses RadioGroup (not RadioGroupWithValue) — set the value directly without `:radioName` suffix fields. `pinLength` and `pinValidity` are strings, not integers. The activity has an `out` success port (not documented in the `describe` output, but validated and round-tripped).

### verify-otp (Verify OTP) — ✅ TESTED

| Property | Type | Required | Notes |
|----------|------|----------|-------|
| `pin` | string | Yes | Variable containing the OTP to verify (e.g. `{{otpCode}}`) |
| `transactionReference` | string | Yes | Must match the generate-otp transaction reference |
| `pinFormatPrefix` | string | No | Prefix for OTP display |
| `pinFormatSuffix` | string | No | Suffix for OTP display |
| `notifyURL` | string | No | URL for notification callback |
| `resendCommand` | string | No | Command for resend behavior |
| `extraParameters` | object | No | Additional key-value pairs |

**Gotcha:** Minimal required set is just `pin` and `transactionReference`. Output ports: `error`, `failure`, `resend` — use the `resend` port to loop back to `generate-otp`.

### cryptographic-hash (Cryptographic Hash) — ✅ TESTED

| Property | Type | Required | Notes |
|----------|------|----------|-------|
| `algorithm` | string | No | Select: `SHA256` (default) or `SHA512` — only two options |
| `input` | string | Yes | Value to hash — can use `{{variable}}` |
| `applySalt` | boolean | No | Enable salt (default `false`) |
| `saltEncoding` | string | No | Select: `AUTO`, `TEXT` (default), `BASE64`, `HEX` |
| `salt` | string | Yes | Salt value — **always required and must be non-empty**, regardless of `applySalt` or `saltEncoding` values. The describe API reports this as conditional but validation rejects empty/missing salt in all cases |

**Gotcha:** The describe API condition (`applySalt == true && saltEncoding != AUTO`) does not match server-side validation. The `salt` field must always be present and non-empty — even when `applySalt` is `false` or `saltEncoding` is `AUTO`. Omitting it or sending `""` causes FC1015 error.

### upload-audio (Upload Audio) — ✅ TESTED

| Property | Type | Required | Notes |
|----------|------|----------|-------|
| `audioFileType` | string | Yes | Select: `agent_greeting` (only option — Agent Personal Greeting) |
| `greetingPurpose` | string | Yes | Up to 80 alphanumeric characters with hyphens and underscores — NO spaces allowed (FC1015 error). Use snake_case or kebab-case. |
| `audioFileData` | json | Yes | VariableSelect — must reference a JSON flow variable containing recorded audio data (use `{{varName}}` syntax) |
| `agentId` | string | Yes | VariableSelect — must reference a String flow variable containing the agent user ID (use `{{varName}}` syntax) |

**Gotcha:** `greetingPurpose` rejects spaces — use underscores or hyphens (e.g. `"Welcome_greeting"`, not `"Welcome greeting"`). Error port is `error` (not `failure`).

### start-media-stream (Start Media Stream) — ✅ TESTED

| Property | Type | Required | Notes |
|----------|------|----------|-------|
| `mediaDestinationId` | string | Conditional | Media destination — `"Cisco AI Assistant"` (currently the only option). Value is a display name string, not a UUID. Use `wxcli cc-flow list-activity-choices PROJECT_ID start-media-stream mediaDestinationId` to check available destinations. Gated: **REQUIRED IF** `dummy == true` (see below). |

**⚠️ `mediaDestinationId` is gated on `dummy == true`.** That is the `showOnCondition` verbatim from the live definition (verified 2026-07-25). `dummy` is not a documented input of this activity and has no meaning in the FlowIR contract — this appears to be an internal placeholder condition leaking into the public contract. Treat `mediaDestinationId` as required in practice, but be aware the condition gating it is not something you can meaningfully satisfy or reason about from the FlowIR side.

### call-progress-analysis (Call Progress Analysis) — ✅ TESTED

| Property | Type | Required | Notes |
|----------|------|----------|-------|
| `minSilencePeriod` | int | Yes | Min silence in ms (default `608`) |
| `analysisPeriod` | int | Yes | Analysis window in ms (default `2500`) |
| `minValidSpeech` | int | Yes | Min speech duration in ms (default `112`) |
| `maxTimeAnalysis` | int | Yes | Max analysis time in ms (default `3000`) |

**Note:** All properties are plain integers. Described as "currently supported only for callback." Output variables include `status`, `FailureCode`, and `FailureDescription`.

### LiveCallerSentiment (Live Caller Sentiment) — ⚠️ FEATURE-GATED

No configurable properties. Enable by placing the activity in the flow.

**Gotcha (historical):** When this activity was still listed, its definition existed in the schema catalog but creation failed with `ACTIVITY_NOT_FOUND` on orgs without the Live Caller Sentiment feature provisioned (validation reported `valid: true` with a 500-level warning about the missing activity mapping). As of 2026-07-11 it is absent from the live prod registry entirely — `wxcli cc-flow show-activity PROJECT_ID NAME` and `wxcli cc-flow show-node-template PROJECT_ID NAME` (run then as wxcc-flow describe and schema) now return "not found in the registry".

**Re-checked 2026-10-19 (live, CC Bootcamp Sandbox): hidden by default, not gone.** It is absent from `wxcli cc-flow list-activities PROJECT_ID` (54) and from `--flow-type SUBFLOW` (29), and listed with `--check-ui-enabled true` (57). Whether `show-activity`, choices and import still fail for it was not re-tested.

### queue-reservation (Queue Reservation) — ⚠️ FEATURE-GATED

| Property | Type | Required | Notes |
|----------|------|----------|-------|
| `toggle` | boolean | No | Enable contact priority (default `true`) |
| `priorityRadioGroup` | string | No | RadioGroup: `staticPriority` or `variablePriority` |
| `priority` | int | Conditional | Select: P1=1 through P9=9 — required when `priorityRadioGroup` is `staticPriority` |
| `priorityVariable` | int | Conditional | VariableSelect — required when `priorityRadioGroup` is `variablePriority` |

**Warning (historical):** When this activity was still listed, it returned `ACTIVITY_NOT_FOUND` on choices lookups (HTTP 400) and `create` (HTTP 500); validation passed with a 500-level warning. Same behavior as `flow-test-activity` and `LiveCallerSentiment`. As of 2026-07-11 it is absent from the live prod registry entirely — `wxcli cc-flow show-activity PROJECT_ID NAME` and `wxcli cc-flow show-node-template PROJECT_ID NAME` (run then as wxcc-flow describe and schema) now return "not found in the registry". Properties above are from the historical registry definition and have NOT been validated via round-trip.

Output variables (from definition): `QueueId`, `status`, `FailureCode`, `FailureDescription`.

**Re-checked 2026-10-19 (live, CC Bootcamp Sandbox): hidden by default, not gone.** It is absent from `wxcli cc-flow list-activities PROJECT_ID` (54) and from `--flow-type SUBFLOW` (29), and listed with `--check-ui-enabled true` (57). Whether `show-activity`, choices and import still fail for it was not re-tested.

### flow-test-activity (Test Activity Flow) — ⚠️ FEATURE-GATED

| Property | Type | Required | Notes |
|----------|------|----------|-------|
| `queueRadioGroup` | string | No | `staticQueue` or `variableQueue` |
| `destination` | string | Yes | Queue UUID (static mode) |
| `destinationVariable` | string | Yes | Variable for queue (variable mode) |
| `fallbackQueue` | string | Yes | Fallback queue UUID |
| `toggle` | boolean | No | Enable priority (default `false`) |
| `priorityRadioGroup` | string | No | `staticPriority` or `variablePriority` |
| `priority` | int | Yes | Static priority value |
| `priorityVariable` | int | Yes | Variable for priority |
| `toggleAgentAvailability` | boolean | No | Check agent availability (default `false`) |
| `agentAvailabilityRadioGroup` | string | No | Availability check mode |
| `agentAvailabilityVariable` | boolean | Yes | Variable for availability check |
| `skills` | object | Yes | Skill requirements and relaxation config |

**Warning (historical):** When this activity was still listed, it returned `ACTIVITY_NOT_FOUND` on both choices lookups and `create` (HTTP 500); validation passed with a warning. As of 2026-07-11 it is absent from the live prod registry entirely — `wxcli cc-flow show-activity PROJECT_ID NAME` and `wxcli cc-flow show-node-template PROJECT_ID NAME` (run then as wxcc-flow describe and schema) now return "not found in the registry". Properties above are from the historical registry definition and have NOT been validated via round-trip.

**Re-checked 2026-10-19 (live, CC Bootcamp Sandbox): hidden by default, not gone.** It is absent from `wxcli cc-flow list-activities PROJECT_ID` (54) and from `--flow-type SUBFLOW` (29), and listed with `--check-ui-enabled true` (57). Whether `show-activity`, choices and import still fail for it was not re-tested.

### Feedback (Feedback) — ✅ TESTED

| Property | Type | Required | Notes |
|----------|------|----------|-------|
| `dispatch` | string | No | Survey dispatch method — `choices` endpoint returns 404 for this field |
| `language` | string | No | Survey language — uses RadioGroupWithValue |
| `customerId` | string | No | Variable with customer ID |
| `email` | string | No | Variable with customer email |
| `phoneNumber` | string | No | Variable with customer phone |

**Gotcha:** All properties are optional — a completely bare node (only `activityName`) validates and creates successfully. This is a legacy v1 activity with NO output ports at all (no error port either). Wire the exit using the `default` edge condition. The `dispatch` field's choices endpoint returns HTTP 404 — the Select values cannot be discovered programmatically.

### Feedback-V2 (Feedback V2) — ✅ TESTED

| Property | Type | Required | Notes |
|----------|------|----------|-------|
| `surveyMethod` | string | Yes | Survey delivery method — uses RadioGroupWithValue. Value: `inlineSurvey` for voice |
| `surveyMethod:radioName` | string | Yes | `setToValue` (static) or `setToVariable` (variable ref) |
| `surveyMethod_radioName` | string | Yes | Same value, alternate format |
| `overrideLanguageToggle` | boolean | No | Override language settings (default `false`) |
| `language` | string | Conditional | Language code — required when `overrideLanguageToggle` is `true` |
| `customerId` | string | No | Variable with customer ID (not for voice-based survey) |
| `email` | string | No | Variable with customer email (not for voice-based survey) |
| `phoneNumber` | string | No | Variable with customer phone (not for voice-based survey) |
| `customPreFills` | object | No | Key-value pre-fill data (not for voice-based survey) |
| `timeout` | int | Yes | Timeout in seconds (default `3`, not for email/SMS survey) |

**Gotcha:** `surveyMethod` uses RadioGroupWithValue — requires `:radioName` / `_radioName` suffix fields. The value `inlineSurvey` selects voice-based inline survey. `language` is only required when `overrideLanguageToggle` is `true`.

### SetCallerID (Set Caller ID) — ✅ TESTED

| Property | Type | Required | Notes |
|----------|------|----------|-------|
| `callerId` | string | No | Caller ID value — uses RadioGroupWithValue for static/variable. E.164 format (e.g., `"+15551234567"`) |
| `callerId:radioName` | string | No | `setToValue` (static number) or `setToVariable` (variable reference) |
| `callerId_radioName` | string | No | Same value as above (alternate format required by API) |

**Gotcha:** All properties are optional — a bare node (only `activityName`) validates and creates successfully. When `callerId` is provided, the `:radioName` / `_radioName` suffix fields are required for the value to take effect. No output ports (no error port) — wire exit using `default` edge condition.

### set-whisperannouncement (Set Whisper Announcement) — ✅ TESTED

| Property | Type | Required | Notes |
|----------|------|----------|-------|
| `toggle` | boolean | No | Enable TTS mode (default `false`). Set `true` for TTS |
| `prompts` | object[] | Conditional | Audio file prompts — set to `null` when using TTS mode |
| `connector` | string | Conditional | TTS connector name (same 5-field pattern as play-message) — required when `toggle` is `true` |
| `connector_name` | string | Conditional | Same value, alternate format |
| `connector:name` | string | Conditional | Same value, alternate format |
| `connector_type` | string | Conditional | Same value, alternate format |
| `connector:type` | string | Conditional | Same value, alternate format |
| `toggleLanguage` | boolean | No | Override language and voice (default `true`) |
| `voiceLanguage` | string | Conditional | Output voice selection — required when `toggleLanguage` is `true` and non-default voice desired |
| `promptsTts` | object[] | Conditional | TTS prompt objects (same format as play-message) — required when `toggle` is `true` |
| `speakingRate` | double | No | Speech rate (default `1.0`, non-Cisco connectors only) |
| `volumeGainDb` | double | No | Volume gain in dB (default `0.0`, non-Cisco connectors only) |

**Gotcha:** Uses the same 5-field connector pattern as `play-message`. When using TTS (`toggle: true`), set `prompts: null` and provide `promptsTts`. The `voiceLanguage` field is not strictly required — the server accepts the node without it and uses defaults.

**Conditional fields:** `set-whisperannouncement` uses the same five `showOnCondition`-gated prompt fields (`prompts`, `connector`, `promptsTts`, `toggleLanguage`, `voiceLanguage`) as `play-message` — see § "The shared 5-field prompt pattern (`showOnCondition`)" under `play-message`. Note that `toggleLanguage`/`voiceLanguage` are unreachable when Cisco Cloud Text-to-Speech is the org's only TTS connector.

### ivr-virtualassistant (Virtual Agent v1) — ✅ TESTED

| Property | Type | Required | Notes |
|----------|------|----------|-------|
| `connector` | string | Yes | CCAI connector UUID — resolve via `wxcli cc-flow list-activity-choices PROJECT_ID ACTIVITY INPUT`. Uses Select pattern |
| `connector:name` | string | Yes | Connector display name |
| `connector_name` | string | Yes | Same value, alternate format |
| `interruptible` | boolean | Yes | Allow caller to interrupt prompts (default `false`) |
| `overrideLanguageToggle` | boolean | No | Override language and voice (default `true`) |
| `inputLanguage` | string | Conditional | Input language for speech recognition (e.g. `en-US`) — uses Select, 56 languages available. Required when `overrideLanguageToggle` is `true` |
| `inputLanguage:name` | string | Conditional | Same value as `inputLanguage` |
| `inputLanguage_name` | string | Conditional | Same value, alternate format |
| `outputVoice` | string | Conditional | Output voice (default `Automatic`) — uses Select, 236 voices available. Required when `overrideLanguageToggle` is `true` |
| `outputVoice:name` | string | Conditional | Same value as `outputVoice` |
| `outputVoice_name` | string | Conditional | Same value, alternate format |
| `botParameters` | object | No | Key-value pairs passed to virtual agent |
| `noInputTimeout` | int | Yes | Seconds before no-input timeout (default `5`) |
| `maxNoInputCount` | int | Yes | Max no-input retries (default `3`) |
| `dtmfTimeout` | int | Yes | DTMF inter-digit timeout (default `5`) |
| `dtmfTerminatorSymbol` | string | Yes | DTMF terminator (default `#`) |
| `terminationDelay` | int | Yes | Delay before termination in ms (default `5`) |
| `speakingRate` | double | Yes | Speech rate (default `1.0`) |
| `volumeGain` | double | Yes | Volume gain in dB (default `0.0`) |
| `transcript` | boolean | Yes | Enable conversation transcript (default `true`) |

**Gotcha:** The `connector` field uses Select pattern (UUID + `:name`/`_name` suffix), NOT the 5-field TTS connector pattern. `inputLanguage` and `outputVoice` also use Select pattern with `:name`/`_name` suffix fields. Both are only required when `overrideLanguageToggle` is `true`.

### http-request (HTTP Request v1) — ✅ TESTED

| Property | Type | Required | Notes |
|----------|------|----------|-------|
| `connectorId` | string | Yes | Custom Connector UUID — resolve via `wxcli cc-flow list-activity-choices PROJECT_ID ACTIVITY INPUT`. Uses Select pattern |
| `connectorId:name` | string | Yes | Connector display name |
| `connectorId_name` | string | Yes | Same value, alternate format |
| `httpRequestPath` | string | No | Path appended to connector base URL (e.g. `/api/test`) |
| `httpRequestMethod` | string | Yes | `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `HEAD`, `OPTIONS`. Uses Select pattern |
| `httpRequestMethod:name` | string | Yes | Same value as `httpRequestMethod` |
| `httpRequestMethod_name` | string | Yes | Same value, alternate format |
| `httpQueryParameters` | object | No | Key-value query parameters |
| `httpRequestHeaders` | object | No | Key-value headers |
| `httpContentType` | string | Yes | `Application/JSON`, `TOML`, `XML`, `YAML`, `OTHER`. Uses Select pattern |
| `httpContentType:name` | string | Yes | Same value as `httpContentType` |
| `httpContentType_name` | string | Yes | Same value, alternate format |
| `httpRequestBody` | string | No | Request body (for POST/PUT/PATCH) |
| `httpResponseTimeout` | int | No | Timeout in ms (default `2000`) |
| `retryAttempts` | int | No | Number of retries (default `1`) |
| `contentType` | string | No | Response content type for parsing (e.g. `JSON`) |
| `outputVariableArray` | object[] | No | Array of `{outputVariable, jsonPathExp}` objects mapping JSON paths to flow variables |

**Key difference from http-request-v2:** v1 requires a Custom Connector (`connectorId`) and uses `httpRequestPath` relative to the connector base URL. v2 uses a full `httpRequestUrl` and does not require a connector.

**Gotcha:** `httpRequestPath` is a string (not int as originally documented). All three Select-type fields (`connectorId`, `httpRequestMethod`, `httpContentType`) require the `:name` / `_name` dual-format suffix fields. There are 7 HTTP methods available (including PATCH, HEAD, OPTIONS), not just 4.

### NewSubFlowStart (Start Subflow)

No configurable properties. Automatically placed as the entry point of a subflow. For subflow start nodes in FlowIR import, use `activityName: "start"` with `activityType: "start-subflow"` — the server resolves `start` to `NewSubFlowStart` automatically (the stored draft then reads back `activityType: "start"`; round-trip verified live 2026-07-11).

### end-subflow (End Subflow)

No configurable properties. Terminal node that returns control to the calling flow. Importable ONLY when the import call carries the `?flowType=SUBFLOW` query param (`wxcli cc-flow create-import PROJECT_ID --json-body file://file.json --flow-type SUBFLOW`) — without it, the server resolves activities against the FLOW registry and returns `ACTIVITY_NOT_FOUND` (verified live 2026-07-11; use `activityType: "end"` on the node). Dry-run validate (`POST /v2/flows:validate`) has no flowType query param, so it also resolves `end-subflow` against the FLOW registry and fails with ACTIVITY_NOT_FOUND even for a valid subflow — validate subflows post-create with `wxcli cc-flow list-validate PROJECT_ID FLOW_ID --version-id draft --flow-type SUBFLOW` instead.

### end (End Flow)

No configurable properties. Terminal node for flows that need an explicit end without disconnect.

### Event (Event Handler)

No configurable input properties. Event handlers are configured via the `eventFlows` section — see § 6. The event node properties (`eventSourceName`, `eventClassificationName`, `eventSpecificationName`) are set in the node's `properties` block — they do not appear as inputs in the activity definition.

## 8. Complete Activity Registry

All activities in the Flow Designer activity registry, with their category, required `group` field, and output port conditions. Verified live 2026-10-19: `wxcli cc-flow list-activities PROJECT_ID` (`GET .../v2/activities`) returns **54** activities for a FLOW and **29** with `--flow-type SUBFLOW`. The three ⚠️ FEATURE-GATED entries below (`queue-reservation`, `LiveCallerSentiment`, `flow-test-activity`) are hidden by default and appear only with `--check-ui-enabled true` (57). Output Ports hold every live `outputPorts` condition. Ten rows also list a port the live definition does not carry — an implicit success port (`out` on `advanced-queue-info`, `escalate-cdg`, `Event`, `generate-otp`, `NewContact`, `queue-lookup`, `screen-pop`, `set-contact-priority`; `default` on `bre-request`) or `resend` on `verify-otp`; those come from the earlier tested flows (§ 7), not from the 2026-10-19 registry. (History, 2026-07-11: the registry returned 52 activities, and `ReceiveMessage` / `SendCustomMessage` (custom-messaging channel) appeared in it; both are still in the 2026-10-19 list.) A **subflow** has a smaller registry: wxcc counted 31 activities for `SUBFLOW` against 52 for `FLOW` (2026-07; not re-counted since).

### Core Activities

| activityName | Display Name | Group | Output Ports |
|-------------|-------------|-------|-------------|
| `disconnect-contact` | Disconnect Contact | `terminating-action` | (none — terminal) |
| `play-message` | Play Message | `action` | `default`, `error` |
| `play-music` | Play Music | `action` | `default`, `error` |
| `ivr-menu` | Menu | `enum-gateway` | `0`–`9`, `#`, `*`, `timeout`, `invalid`, `error` |
| `ivr-collectdigits` | Collect Digits | `action` | `timeout`, `invalid`, `error` — **no success port** in the definition; write the success edge as `default` (what stored flows hold; validate rejects it, import accepts it — see § 2) |
| `queue-contact` | Queue Contact | `action` | `default`, `failure` |
| `queue-to-agent` | Queue To Agent | `action` | `error` |
| `queue-lookup` | Get Queue Info | `action` | `out`, `insufficientdata`, `failure` |
| `advanced-queue-info` | Advanced Queue Info | `action` | `out`, `failure` |
| `queue-reservation` | Queue Reservation (⚠️ FEATURE-GATED — listed only with `--check-ui-enabled true`) | `action` | `failure` |
| `callback` | Callback | `action` | `default`, `failure` |
| `scheduled-callback` | Schedule Callback | `action` | `failure` |
| `blind-transfer` | Blind Transfer | `action` | `failure` |
| `bridged-transfer` | Bridged Transfer | `action` | `failure` |
| `ivr-virtualassistant` | Virtual Agent | `action` | `ENDED`, `ESCALATE`, `error` |
| `ivr-virtualassistantvoice` | Virtual Agent V2 | `action` | `ENDED`, `ESCALATE`, `error` |
| `screen-pop` | Screen Pop | `action` | `out` (implicit — flow continues after pop) |
| `SetCallerID` | Set Caller ID | `action` | (none) |
| `set-announcement` | Set Announcement | `action` | `error` |
| `set-whisperannouncement` | Set Whisper Announcement | `action` | `error` |
| `set-contact-priority` | Set Contact Priority | `action` | `out`, `failure` |
| `escalate-cdg` | Escalate Call Distribution Group | `action` | `out`, `error` |
| `record` | Record | `action` | `noInputTimeout`, `undefinedErrors` |
| `RecordingControl` | Recording Control | `action` | `failure` |
| `Feedback` | Feedback | `action` | (none) |
| `Feedback-V2` | Feedback V2 | `action` | `error` |
| `start-media-stream` | Start Media Stream | `action` | `failure` |
| `send-digits` | Send Digits | `action` | `failure` |
| `call-progress-analysis` | Call Progress Analysis | `action` | `failure` |
| `LiveCallerSentiment` | Live Caller Sentiment (⚠️ FEATURE-GATED — listed only with `--check-ui-enabled true`) | `action` | `failure` |
| `upload-audio` | Upload Audio | `action` | `error` |
| `cryptographic-hash` | Cryptographic Hash | `action` | `error` |
| `generate-otp` | Generate OTP | `action` | `out`, `error` |
| `verify-otp` | Verify OTP | `action` | `error`, `failure`, `resend` |
| `ReceiveMessage` | Receive Message | `action` | `timeout`, `error` |
| `SendCustomMessage` | Send Custom Message | `action` | `error` |
| `flow-test-activity` | Test Activity Flow (⚠️ FEATURE-GATED — listed only with `--check-ui-enabled true`) | `action` | `failure` |
| `SendChat` | Send Chat | `action` | `timeout`, `error` |
| `SendEmail` | Send Email | `action` | `timeout`, `error` |
| `SendSMS` | Send SMS | `action` | `timeout`, `error` |
| `SetCustomerIdentity` | Set Customer Identity | `action` | `error` |

### Logic Activities

| activityName | Display Name | Group | Output Ports |
|-------------|-------------|-------|-------------|
| `set-variable` | Set Variable | `set-variable` | `out`, `error` |
| `condition-activity` | Condition | `enum-gateway` | `true`, `false`, `error` |
| `business-hours` | Business Hours | `enum-gateway` | `workingHours`, `holidays`, `override`, `default`, `error` |
| `case-statement` | Case | `enum-gateway` | (dynamic per case), `error` |
| `percent-allocation` | Percent Allocation | `action` | (dynamic per allocation `desc`), `error` |
| `http-request` | HTTP Request (v1) — not in the 2026-10-19 FLOW, SUBFLOW or UI-enabled lists | `http-request` | `default` |
| `http-request-v2` | HTTP Request (v2) | `http-request` | `default`, `out`, `success`, `error`, `failure`, `timeout` |
| `bre-request` | BRE Request | `action` | `default` |
| `fn-activity` | Function — not in the 2026-10-19 FLOW, SUBFLOW or UI-enabled lists | `fn-activity` | `default`, `error` |
| `parse-activity` | Parse | `parse-activity` | `default`, `out`, `error` |
| `hand-off` | GoTo | `action` | `error` |
| `subflow-handoff` | Subflow | `action` | `default`, `out`, `error` |
| `wait-activity` | Wait | `action` | `error` |
| `NewContact` | Start Flow | `action` | `out` |
| `NewSubFlowStart` | Start Subflow | `action` | (none) |
| `end-subflow` | End Subflow | `terminating-action` | (none — terminal) |
| `end` | End Flow | `action` | (none) |
| `Event` | Event Handler | `action` | `out` |

## 9. Validate → Create Workflow

The whole workflow in `wxcli` commands (each step below gives the REST call and its details; `PROJECT_ID` is the `projectId` that `wxcli cc-flow-projects show-user-preferences` returns):

```
wxcli cc-flow show-starter-flow simple-inbound -o json > flow.json   # starter FlowIR (built locally, no API call)
# ... edit flow.json: nodes, edges, variables, eventFlows ...
wxcli cc-flow create-validate PROJECT_ID --json-body file://flow.json  # dry-run validate (Step 2)
wxcli cc-flow create-import PROJECT_ID --json-body file://flow.json    # create the flow (Step 3); prints its ID
wxcli cc-flow publish FLOW_ID PROJECT_ID                               # publish the draft (Step 5); validates first
```

### Step 1: Build FlowIR

Construct the FlowIR JSON object with all nodes, edges, variables, and event flows. Save to a file.

### Step 2: Dry-Run Validate

```
POST /{orgId}/project/{projectId}/v2/flows:validate
Content-Type: application/json
Body: { FlowV2 object }
```

Response:
```json
{
  "valid": true,
  "errors": [],
  "warnings": [{"code": "FC1007", "message": "Add descriptions", "severity": "RECOMMENDATION"}],
  "summary": "FlowV2 looks valid for import/save."
}
```

Fix all ERRORs. RECOMMENDATIONs (FC1004 isolated activities, FC1007 missing descriptions) are safe to ignore.

⚠️ **`:validate` and `:import` do not enforce the same rules, and the gap runs both ways.**
Cisco's Flow Orchestration guide is explicit: an edge whose `condition` is not a real
output port fails `:validate` with `valid: false` yet still imports with `201`; other
checks are only meaningful at import time. Treat a clean validate as **necessary, not
sufficient** — always handle an error on `:import` too.

A third failure mode sits in front of both: a body the server cannot deserialize
returns `400 "The provided request body is not readable"` with no field-level
diagnostic. A malformed `eventFlows` key is the usual cause — see § 6.

### Step 3: Create/Import

```
POST /{orgId}/project/{projectId}/v2/flows:import?overwrite=false&flowType=FLOW
Content-Type: application/json
Body: { FlowV2 object }
```

Returns `201` with `{"flow": {...}, "preflightWarnings": [], "preflightWarningsCount": 0}` —
flow metadata including `id`, `status: "Draft"`, `createdBy`, `createdDate`. The server
assigns `flow.id` and the authoritative `flow.version`; any `version` you send is ignored.

**Import error responses** use a different envelope from `:validate` — `{"status", "errors", "trackingId"}`,
where each `errors` entry is either a plain message string or a `{"description", "type"}`
object. There is no `valid` field and no JSON-pointer `path`.

| Status | Meaning |
|---|---|
| `409 Conflict` | A flow with that `name` exists and `overwrite=false`. Re-import with `overwrite=true` or rename. |
| `400 Bad Request` | Structural failure — missing or duplicate start node, an edge referencing a nonexistent node, or an unreadable body. |
| `500` + `type: ACTIVITY_NOT_FOUND` | An unknown `activityName` (or a `fn-activity` node missing `fnName` — see § 11). |

### Step 4: Verify

```
GET /{orgId}/project/{projectId}/v2/flows/{flowId}
```

Confirm the flow was created with all nodes, edges, and resolved properties.

### Step 5: Publish (Optional)

```
POST /{orgId}/project/{projectId}/flows/{flowId}:publish
```

Publishes the draft. Only available via REST API, not MCP. `wxcli cc-flow publish FLOW_ID PROJECT_ID` validates at publish time, and that is now the only publish behaviour the CLI offers: upstream dropped the `skipValidation` query parameter from this operation in the spec sync of 2026-10-26, so the generated command no longer renders the skip flag it carried until then. Until that removal, `skipValidation` (default `false` on the server) controlled whether the server re-validated at publish time, and wxcc-flow publish skipped it by default because that CLI workflow validated explicitly beforehand and publish-time validation can false-positive (e.g. FC1015 on hand-off flows); the skip path, run after an explicit `wxcli cc-flow create-validate PROJECT_ID --json-body file://flow.json`, was verified live 2026-07-11 (run then as wxcc-flow publish and wxcc-flow publish --validate).

> **Unverified:** whether the server still honours a hand-sent `?skipValidation=true` now that the parameter has left the spec was not retested. Only the CLI flag's removal is established.

### Step 6: Iterate with PATCH (partial draft updates)

```
PATCH /{orgId}/project/{projectId}/v2/flows/{flowId}?expectedVersion=N
Content-Type: application/json
Body: {"upsert_nodes": [...], "upsert_edges": [...],
       "remove_node_names": [...], "remove_edge_keys": [...]}
```

⚠️ **`remove_edge_keys` does not work — use `remove_node_names` instead (verified live 2026-07-25).** The server does not persist edge `id`s: every edge in a stored draft comes back with `"id": null`, so there is nothing for an id-keyed removal to match. Tested against a FlowIR-authored draft:

| `remove_edge_keys` value | Result |
|---|---|
| `["edge-2"]` (edge id — the shape Cisco's Flow Orchestration guide documents) | HTTP 200, **silently removes nothing** |
| `["HoldMusic->Disconnect(default)"]`, `["HoldMusic\|Disconnect\|default"]`, `["HoldMusic->Disconnect"]` | HTTP 200, **silently removes nothing** |
| `[{"from": "...", "to": "...", "condition": "..."}]` | **HTTP 500** "Oops... Something broke..." |
| `[{"from": "...", "to": "..."}]` | **HTTP 500** |

`remove_node_names` DOES work, and it **cascades**: removing a node also drops every edge that referenced it, with no dangling edges left behind. This contradicts the warning in Cisco's guide ("if you remove a node, remove the edges that reference it in the same patch or the merged document fails validation") — no accompanying edge removal is needed. To delete an edge while keeping both of its nodes, `save-draft` the full document with that edge omitted.

CLI: `wxcli cc-flow update PROJECT_ID FLOW_ID --json-body file://patch.json` (wxcc-flow patch resolved `expectedVersion` from the current draft itself; `wxcli cc-flow update` does not — omitting `--expected-version` skips the check, or read N with `wxcli cc-flow show PROJECT_ID FLOW_ID -o json --fields version` and pass `--expected-version N`). Top-level FlowV2 fields (`name`, `description`, `variables`, …) can also be patched directly — this is how renames work (`wxcli cc-flow update PROJECT_ID FLOW_ID --json-body '{"name":"NEW"}'`); the new name propagates to the flow level (list/get) on the next publish. All four patch keys plus top-level fields verified live 2026-07-11 with content round-trips.

**Rename timing depends on whether the flow was ever published.** Verified live 2026-10-19 on the CC Bootcamp Sandbox, on a flow published once: after `wxcli cc-flow update PROJECT_ID FLOW_ID --json-body '{"name":"NEW"}'`, the draft (`wxcli cc-flow show PROJECT_ID FLOW_ID`) carried the new name, but the flow level (`wxcli cc-flow-store show-metadata PROJECT_ID FLOW_ID` and `wxcli cc-flow list PROJECT_ID`) kept the old one until `wxcli cc-flow publish FLOW_ID PROJECT_ID` (run with publish-time validation on), after which it showed the new name. On a **never-published** flow (one observation, 2026-10-19), the flow-level name changed at once, before any publish. The never-published case was not repeated.

**`--expected-version` is enforced, but the draft version never moves.** Verified live 2026-10-19: `wxcli cc-flow update PROJECT_ID FLOW_ID --json-body file://patch.json --expected-version 99` on a draft at version `0` returned `409 Version conflict for flow …: expected version 99 but found 0`, and nothing was written; the same patch with `--expected-version 0` was accepted. The draft `version` stayed `0` after that patch, after two publishes and after a rename (and through every save-draft and patch measured earlier the same day). So the check rejects a wrong number, but two writers who both read `0` both pass it: it does not separate concurrent edits of one draft.

⚠️ Two PATCH gotchas (both verified live 2026-07-11): (1) PATCHing a draft that was created by `flows:consume-template` returns a bare 500 ("Oops... Something broke...") — patch works only on FlowIR-authored drafts; (2) the v1 `PATCH /flows/{flowId}` merge-patch endpoint returns 200 but SILENTLY IGNORES `name`/`description` changes (only `lastModifiedDate` bumps) — never use it for metadata updates.

### Step 7: Observe (after real calls)

Once an entry point routes real calls to the flow: `wxcli cc-flow-tracing list-interactions PROJECT_ID FLOW_ID` lists calls (`{"interactions": [], "pageInfo": {...}}` shape), `wxcli cc-flow-tracing list-traces PROJECT_ID FLOW_ID VERSION_ID INTERACTION_ID` returns step-by-step execution (for decrypted payloads use the separate `wxcli cc-flow-tracing list-traces-decrypted PROJECT_ID FLOW_ID VERSION_ID INTERACTION_ID --process-id PID` — `--process-id` is required), and `wxcli cc-flow-tracing show-analytics PROJECT_ID FLOW_ID VERSION_ID` returns aggregates (fields are `-1` when no data). The Flow Store API cannot place calls — generating an interaction always requires the contact-center side (route an entry point to the flow, dial it).

### Subflows

All of the above works for subflows by adding `flowType=SUBFLOW` as a QUERY param: `--flow-type SUBFLOW` on `wxcli cc-flow` `create-import`, `show`, `create-flows`, `update`, `export`, `list-validate`, `publish`, `create-lock`/`create-unlock`, `list`, `delete`, `list-activities`, `show-activity`, `list-activity-choices` and `show-node-template`, and on `wxcli cc-flow-store` `revert`, `show-metadata`, `consume`, `consume-template`, `check-name` and `list-usages` (wxcc-flow's `--type SUBFLOW`, renamed). Omitting it on `list-activities` gives the FLOW registry, so a subflow author must pass it. `cc-flow create-validate` also offers `--flow-type`, but it sets the body's `flowType` field, not a query parameter (read from the command source), and § 11 records that validate always validates as FLOW. See § 11 "Subflow Creation via FlowIR Import" for the start/end node shapes and validator quirks.

## 10. Common Validation Errors

| Code | Message | Fix |
|------|---------|-----|
| FC1015 | "Required field 'Variable' is not configured in Set Variable" | Add top-level `srcVariable`, `setTo`, `srcVariableType`, `literal`, `expr` to set-variable nodes |
| FC1038 | "Variable 'X' is referenced but not declared" | Declare the variable in the `variables` array, or fix the expression to reference a declared variable |
| FC1015 | "Required field 'Recovery Queue' is not configured" | Add `recoveryQueue` (UUID), `recoveryQueue:name`, `recoveryQueue_name` to `queue-to-agent` — required even when `parkContactToggle` is `false` |
| FC1015 | "One or more fields in the activity are not configured correctly" | Generic catch-all — check all required fields in the activity's §7b table. Often accompanies a more specific FC1015 |
| FC1004 | "Flow has isolated activities" | RECOMMENDATION only — nodes not reachable from start. Safe for placeholder nodes wired to Business Hours later. |
| FC1007 | "Add descriptions for activities" | RECOMMENDATION only — cosmetic |

## 11. Gotchas and Lessons Learned

### FlowIR vs Proprietary Export JSON

FlowIR is the **official API format** for programmatic flow building. It is NOT the same as the proprietary JSON from Flow Designer's UI export. Key differences:

| | FlowIR (v2 API) | Export JSON (UI) |
|-|-----------------|-----------------|
| Activity references | Names (`"activityName": "play-message"`) | UUIDs (`"activityId": "5f114466..."`) |
| Connector references | Names (`"connector": "Cisco Cloud Text-to-Speech"`) | Resolved IDs |
| Event specs | Names (`"eventSpecificationName": "GlobalErrorHandling"`) | UUIDs |
| Diagram layout | Not included (server generates) | Pixel coordinates |
| Safe to generate | **Yes** | **No** |

### Connector Field Redundancy

Play Message, Menu, Collect Digits, and Set Whisper Announcement all require 5 connector fields: `connector`, `connector_name`, `connector:name`, `connector_type`, `connector:type`. Omitting any may cause the activity to render without TTS.

### Global Variables Require Full Metadata

Global variables (like `Global_Language`) must be declared in the FlowIR `variables` array with `source: "GLOBAL"` (what stored flows hold, verified live 2026-10-19; `"GLOBAL_TM"`, which this gotcha named until then, also passes validate) and their org-wide `id` UUID. Without these fields, a Set Variable activity that references `Global_Language` creates a local variable that shadows the global — the TTS engine and Analyzer reports won't see the change. Get the metadata via `wxcli cc-flow-store list-global-variables PROJECT_ID -o json --fields variables` and copy the full object into `variables`. See § 3 for the complete pattern.

### Queue Creation Is Not Available via Flow APIs

The Flow Store REST API, `wxcli` (the `cc-flow*` and `cc-functions` groups), and MCP server can look up existing queues (`wxcli cc-flow list-activity-choices PROJECT_ID queue-contact destination --parent-input-name channelType --parent-value TELEPHONY`) but cannot create new ones. Queue creation requires the WxCC Provisioning API or the Control Hub UI (`Control Hub → Contact Center → Queues → Create Queue`). Plan queue creation as a manual prerequisite before programmatic flow building.

### Set Variable Double Declaration

The `set-variable` activity requires both top-level property fields AND a `setVariablesArray`. This is the most common validation error (FC1015).

### Activity Output Variable References (FC1038)

Expressions referencing activity output variables — `{{ActivityName.OutputVar}}` (e.g., `{{CheckQueue.EWT}}`, `{{LookupAccount.httpResponseBody}}`) — trigger FC1038 "Variable 'X' is referenced but not declared" at FlowIR validation time. This applies everywhere: condition expressions, set-variable literals, parse `inputVariable`, etc.

**At runtime these references work fine** — this is purely a validation-time limitation. The validator cannot resolve activity output scopes.

**Workaround strategies by activity type:**

| Activity | Output Variable | Workaround |
|----------|----------------|------------|
| HTTP Request | `httpStatusCode`, `responseBody` | Use `outputVariableArray` to map JSON paths to declared flow variables |
| Parse | Output variables | Use `outputVariableArray` similarly |
| Queue Lookup (Get Queue Info) | `PIQ`, `EWT` | Cannot capture via `outputVariableArray` — outputs are implicit. Use static TTS text instead of `{{GetQueueInfo.PositionInQueue}}` in Play Message prompts |
| Collect Digits | `DigitsEntered` | **Avoid Collect Digits + Condition pattern entirely.** Use `ivr-menu` (Menu) instead — Menu routes directly by digit via edge conditions (`"1"`, `"2"`, etc.) without needing to reference an output variable. This is the recommended FlowIR pattern for single-digit choices. |
| Condition after any activity | `{{Activity.OutputVar}}` | Declare a flow variable, add a Set Variable node to capture the output, then reference the flow variable in the Condition. Note: the Set Variable `literal` field also triggers FC1038 if it contains `{{Activity.OutputVar}}` — this means the capture itself fails validation. The only clean workaround is to redesign the flow to avoid referencing activity outputs in expressions. |

**Design principle for FlowIR:** Prefer `ivr-menu` over `ivr-collectdigits` + `condition-activity` whenever the caller is choosing from a small set of options. Menu routes directly by digit without needing variable capture. Reserve Collect Digits for multi-digit input (account numbers, PINs) where the digits feed into a downstream HTTP Request `outputVariableArray`.

### Queue Contact `default` Edge Condition Warning

**Corrected 2026-10-19 (verified live on the CC Bootcamp Sandbox, § 7 `queue-contact`):** the warning runs the other way. With `channelType` set, `create-validate` accepts both `default` and `failure`; `create-import` accepts both but attaches a preflight WARNING to `failure` — `Condition 'failure' is not valid for activity 'queue-contact'. Use one of: default` — and none to `default`. The activity definition lists both ports, and stored flows use `default`. Wire `default`. The rest of this subsection is the earlier (pre-2026-10-19) reading, kept as history: the FlowIR validator warns that `default` is not a valid condition for `queue-contact`, suggesting `failure` instead. However, `default` works correctly at runtime — the hold music/treatment path after Queue Contact executes while the caller waits for an agent. The warning is safe to ignore. Using `failure` instead would only wire the error path, not the hold treatment path. This is a validator limitation — the `queue-contact` activity's success continuation is implicit (agent answers), but the hold treatment path needs an edge condition to wire the downstream activities.

### Bridged Transfer Has No Success Port

`bridged-transfer` only has a `failure` output port, so `failure` is the only edge you can wire — design flows to handle failure (no answer → return to menu). Cisco, however, documents that control is retained: "When the third-party ends the call, the call flow continues and reengages as required, such as queuing the call to an agent." [source: https://help.webex.com/en-us/article/nhovcy4/Build-and-manage-flows-with-Flow-Designer] **UNRESOLVED** — the documented continuation may be implicit rather than a wired edge; only a live call settles it. See § 7 `bridged-transfer`.

### Node Names vs IDs in Edges

**Always wire edges by node `name`.** `:validate` accepts node ids in `from`/`to`, but
`create` (import) has rejected them with `400 "Edge from='<id>' does not match any node name."`
(verified live 2026-07-12) — this is one of the validate-vs-import gaps described in § 9,
so a clean validate does not prove an id-wired flow will import.

Node `id` is incidental to import: a stored draft returns `"id": null` for every **edge**,
and a live `flows/{id}:export` returns `null` for a node's `id`. After saving, the server
normalizes edge endpoints to node names.

### MCP list_flows Bug

The MCP server's `list_flows` tool returns empty arrays even when flows exist. Use `wxcli cc-flow list PROJECT_ID --all` (which paginates the REST API `GET /{orgId}/project/{projectId}/flows` — the server defaults to `size=10` and silently truncates) instead.

### RadioGroupWithValue Pattern

Properties using `RadioGroupWithValue` (identified by the choices API returning a 400 error for that input) require suffix fields alongside the value:

```json
{
  "fieldName": "actual-value",
  "fieldName:radioName": "setToValue",
  "fieldName_radioName": "setToValue"
}
```

Use `setToValue` for static values, `setToVariable` for variable references. Activities confirmed to use this pattern: `scheduled-callback` (`callbackQueue`, `scheduleTimezone`), `Feedback-V2` (`surveyMethod`), `SetCallerID` (`callerId`), `send-digits` (`transferoutdigits`).

### RadioGroup Pattern (Direct Value, No Suffix)

Properties using `RadioGroup` (NOT `RadioGroupWithValue`) accept the value directly — no `:radioName` / `_radioName` suffix fields needed:

```json
{
  "fieldName": "NUMERIC"
}
```

Identified by the choices API returning a 400 with "is a 'RadioGroup' which does not support choices." Activities confirmed to use this pattern: `generate-otp` (`pinFormat`), `screen-pop` (`target`).

### Select Pattern (Dual-Format Name Fields)

Properties using `Select` type (identified by the choices API returning valid choices) require name suffix fields:

```json
{
  "fieldName": "uuid-or-value",
  "fieldName:name": "Display Name",
  "fieldName_name": "Display Name"
}
```

For entity references (queues, connectors), the value is a UUID and the name is the display name. For enum-like selects (HTTP methods, content types), the value and name are typically the same. Activities confirmed to use this pattern: `http-request` (`connectorId`, `httpRequestMethod`, `httpContentType`), `queue-contact` (`destination` for choices API, but `queueId` for the actual node property — see § queue-contact), `queue-to-agent` (`reportingQueue`, `recoveryQueue`), `ivr-virtualassistant` (`connector`, `inputLanguage`, `outputVoice`).

### Implicit Output Ports

Some activities accept edge conditions that aren't reported by the `describe` command or the activity definition API. Known cases:
- `generate-otp`: has an `out` success port (registry only lists `error`)
- `screen-pop`: has an `out` success port (registry lists no ports)

When building flows, if an activity logically continues to the next step, try the `out` condition even if the registry doesn't list it.

### Feature-Gated Activities

Historically, some activities appeared in the registry metadata but were not available for all orgs — `flow-test-activity`, `LiveCallerSentiment`, and `queue-reservation` returned `ACTIVITY_NOT_FOUND` on choices lookups and `create` while validation passed with a warning ("Validation pipeline error"). As of 2026-07-11 all three were gone from the live prod registry. Re-checked 2026-10-19 (live): they are **hidden by default, not gone** — absent from `wxcli cc-flow list-activities PROJECT_ID` (54) and listed with `--check-ui-enabled true` (57); see § 12 Feature-Gated Activities.

If a listed activity behaves this way in the future, the signal is a 400 "Activity not found" from `wxcli cc-flow list-activity-choices PROJECT_ID ACTIVITY INPUT` on any required Select-type field — check before investing in a full flow.

### Subflow Creation via FlowIR Import — REQUIRES the flowType Query Param

Subflow creation via FlowIR import WORKS, but only through the `?flowType=SUBFLOW` **query parameter** (verified live 2026-07-11, run then as wxcc-flow create file.json --type SUBFLOW; today `wxcli cc-flow create-import PROJECT_ID --json-body file://file.json --flow-type SUBFLOW` — created, listed under `wxcli cc-flow list PROJECT_ID --all --flow-type SUBFLOW`, exported with `flowType: "SUBFLOW"`, and published). The `flowType: "SUBFLOW"` **body field alone** is ignored — without the query param the import resolves activities against the FLOW registry (so `end-subflow` returns `ACTIVITY_NOT_FOUND`) and creates a `FLOW`. Minimal working subflow: start node `activityName: "start"` / `activityType: "start-subflow"`, end node `activityName: "end-subflow"` / `activityType: "end"`.

Two validator quirks (both verified live): dry-run validate (`POST /v2/flows:validate`) has no flowType query param and always validates as FLOW — a valid subflow fails it with ACTIVITY_NOT_FOUND for `end-subflow`; and post-create `wxcli cc-flow list-validate PROJECT_ID FLOW_ID --version-id draft --flow-type SUBFLOW` reports a cosmetic FC1024 on the start node while publish (`skipValidation=true`, wxcc-flow's old default; the CLI has had no skip flag since the 2026-10-26 spec sync dropped the parameter) succeeds.

**Consequence (updated 2026-07-11):** subflows CAN now be created programmatically, so `subflow-handoff` is round-trip testable end-to-end (create subflow → publish → reference its ID in `subflowVersion`). `fn-activity` still requires a function ID. The Flow Store has no Functions API (the string FUNCTION appears 0 times in its live /v3/api-docs contract), but the Custom Functions API on the regional CC gateway does: create the function with `wxcli cc-functions create --json-body file://fn.json` and publish it with `wxcli cc-functions publish ID --json-body '{"tags":["Live"],"comment":"…"}'` [`custom-functions.md` § Lifecycle]. (History: until 2026-10-19 this line said the function "can only be created in the UI".)

The `subflowVersion` field of `subflow-handoff` (component type `SubflowVersionSelect`, per the choices 400 error — the flat prod definition does not name component types) does not support the choices API — it returns a 400 error.

### Required Fields May Not Be Truly Conditional

Some fields marked as conditional in the activity definition are actually always required by the validator. Known cases:
- `queue-to-agent`: `recoveryQueue` is always required, even when `parkContactToggle` is `false`
- `cryptographic-hash`: `salt` is always required and must be non-empty, even when `applySalt` is `false` or `saltEncoding` is `AUTO`. The activity definition marks `salt` as `required: true` with `showOnCondition: "applySalt == true && saltEncoding != AUTO"` — the `required` flag is enforced but the `showOnCondition` is ignored by the validator
- When in doubt, provide default values for all "Required: Yes" fields in the table even if the toggle appears to gate them

### Property Name Mismatches Between API Layers

Some activities have different property names in the activity definition API vs. the validation/import API. Known cases:
- `queue-contact`: The activity definition and choices API use `destination` as the input name, but the validator requires `queueId` as the node property. Using `destination` without `queueId` always fails with FC1015 "Required field 'Queue' is not configured". Use `queueId` for authoring; use `wxcli cc-flow list-activity-choices PROJECT_ID queue-contact destination --parent-input-name channelType --parent-value TELEPHONY` to resolve available queues.
- `queue-contact`: Including `queueRadioGroup` activates "UI mode" validation that requires `destination` + all dual-format fields IN ADDITION TO `queueId`. Omit `queueRadioGroup` entirely to let `queueId` work as a complete shorthand.
- `percent-allocation`: The activity definition API reports `allocations` as type `string[]` (the PercentAllocation component — the flat prod definition does not name it) with a default of `["{\"percent\":100,\"desc\":\"Allocation Default\"}"]` (an array of stringified JSON objects). The import validator rejects this format — it fails with "Percent allocation values must sum to 100 (current sum: 0.0)". The validator only accepts actual object arrays: `[{"percent":60,"desc":"PathA"},{"percent":40,"desc":"PathB"}]`. Use `object[]` semantics despite the API declaring `string[]`.
- `play-music`: The activity definition (`wxcli cc-flow show-activity PROJECT_ID play-music`) reports `audioRadioGroup` with `showOnCondition` values `staticAudio` / `dynamicAudio`, but the value that actually saves and round-trips for a static hold-music file is `audioRadioGroup: "audioFile"` (with `prompt: "<audio-file-name>"`). Verified 2026-07-23 via `save-draft` (today `wxcli cc-flow create-flows PROJECT_ID FLOW_ID --json-body file://flow.json`) + re-export of a Play Music node (`prompt: "defaultmusic_on_hold.wav"`, `audioRadioGroup: "audioFile"`, `duration: 60`) — it validated clean and round-tripped unchanged. Use `wxcli cc-flow list-activity-choices PROJECT_ID play-music prompt` to list available audio file names.
- `set-announcement`: Older definition layers returned TWO inputs named `attributeTag` — feature-flag variants distinguished by `flagName=wxcc_record_agent_personal_greeting` ("Attribute tag", not required, when `flagValue=off,control`; "Greeting Purpose", required, defaultValue="Default", when `flagValue=on`). The live prod registry (2026-07-11) resolves the flag server-side and returns ONE `attributeTag` (required, defaultValue="Default", shown when `toggleAgentGreeting == true`). When `toggleAgentGreeting` is `true`, omitting `attributeTag` fails validation.

### `fnName` Dropped on Export/Copy Breaks Round-Trips (Function Activities)

`wxcli cc-flow show PROJECT_ID FLOW_ID -o json` (the FlowV2 draft; run then as wxcc-flow draft) and `wxcli cc-flow-store copy PROJECT_ID --source-flow-id FLOW_ID` **may** omit the `fnName` property on Function (`fn-activity`) nodes — the node keeps its `fnVersionConfig.id` (the real function link) but loses the `fnName` label. **The drop is inconsistent, not universal — it is per-node, and some Function nodes in the same export keep `fnName` while others lose it.** In a FlowV2 draft export, a Function node appears as `activityType: "action"` with `properties.activityName: "fn-activity"`, `properties.activityType: "function"`, and `properties.fnName`; it is `properties.fnName` that goes missing on the affected nodes. Consequences (verified live 2026-07-23):

**Re-verified 2026-07-23 (2nd pass) — the drop does NOT reproduce on every flow.** On flow `NAPA_IVR` (a UI-authored flow with three `fn-activity` nodes) a `draft` export (wxcc-flow draft, today `wxcli cc-flow show PROJECT_ID FLOW_ID -o json`) dropped `fnName` on exactly **one** of the three (`parseStoreUserName_r5z`, whose `fnVersionConfig.version` was `"1"`), while the other two (`FormatStoreHours2_o4j`, `FormatStoreAddress_6w3`, both `fnVersionConfig.version "2"`) retained `fnName`. Validating that draft failed with `Import Failure: fnName not found for activity with id 51cd9583-...` (`ACTIVITY_NOT_FOUND`) — confirming even one null `fnName` breaks the round-trip. But on `NAPA_fixed_import_test` (a flow whose `fnName`s had already been restored and re-imported), both `draft` **and** `copy` retained `fnName` on **all three** nodes and `wxcli cc-flow create-validate PROJECT_ID --json-body file://flow.json` (run then as wxcc-flow validate) passed with **no** `fnName` error. **Takeaway:** once every `fn-activity` node's `fnName` is restored and the flow is re-imported, it round-trips cleanly and the drop does not recur. The `version "1"` vs `"2"` correlation above is an observation, not a confirmed deterministic trigger — always check every `fn-activity` node after export rather than relying on a rule for which ones drop.

- `wxcli cc-flow create-validate PROJECT_ID --json-body file://flow.json` / `wxcli cc-flow create-flows PROJECT_ID FLOW_ID --json-body file://flow.json` on the exported FlowV2 fail with `Import Failure: fnName not found for activity with id <uuid>` (`ACTIVITY_NOT_FOUND`).
- `wxcli cc-flow list-validate PROJECT_ID FLOW_ID --version-id draft` on the **same live draft** does **not** flag it — the persisted-draft validator resolves the function via `fnVersionConfig.id`, so the flow runs fine live. The mismatch is purely in the export/import round-trip path.
- `wxcli cc-flow update PROJECT_ID FLOW_ID --json-body file://patch.json` (a patch) re-imports the **entire** resulting draft server-side, so if **any** `fn-activity` node has a null `fnName` in the import representation it fails with the same `fnName not found` error **even when the patch delta only touches unrelated nodes**. This makes `patch` unusable on a flow that still has any un-restored `fnName` (a flow whose `fnName`s all round-trip — e.g. after a restore-and-reimport — patches fine).

**Workarounds:**
- Before `save-draft`/`validate`, re-add `fnName` to every `fn-activity` node. The value equals the node label minus its `_xxx` suffix (e.g. node `parseStoreUserName_r5z` → `fnName: "parseStoreUserName"`). A clean `wxcli cc-flow create-validate PROJECT_ID --json-body file://flow.json` confirms the value resolves (a wrong name re-triggers `fnName not found`).
- `save-draft` (full-flow replace) passes `validate` once `fnName` is restored, and the `fn-activity` nodes' `fnName`/`fnVersionConfig` round-trip intact — **BUT save-draft alone leaves the flow un-openable in the Flow Designer UI** (widget-type corruption, see next subsection). To keep it UI-openable, follow `save-draft` with the remap + `import-ui` workaround documented below.
- A plain `wxcli cc-flow-store copy PROJECT_ID --source-flow-id FLOW_ID` (no `save-draft`) stays UI-loadable if you just need a backup.

### `save-draft` of a FlowV2 Body Corrupts the UI Diagram ("Cannot find factory")

`wxcli cc-flow create-flows PROJECT_ID FLOW_ID --json-body file://flow.json` (run then as wxcc-flow save-draft; and any FlowV2 import that lacks a `diagram` block) makes the server **auto-regenerate the diagram**. The regenerator re-types **specific** activity widgets to their raw `activityName` instead of the generic UI widget type — but it is **selective, not blanket**: most `action`-category activities keep the correct `action` type. Re-verified live 2026-07-23 (2nd pass) on a clean `copy` (fn/HTTP widgets = `action` before save-draft), the diagram-less `save-draft` re-typed exactly three activity kinds and left the rest correct:

| activityName | Correct widget `type` | `type` after `save-draft` | Corrupted? |
|---|---|---|---|
| `fn-activity` | `action` | `fn-activity` | ❌ Yes |
| `http-request-v2` | `action` | `http-request` | ❌ Yes |
| `end` | `end` | `action` | ❌ Yes |
| `play-message`, `play-music`, `queue-contact`, `bridged-transfer` | `action` | `action` | ✅ No |
| `set-variable` | `set-variable` | `set-variable` | ✅ No |
| `condition-activity`, `ivr-menu` | `enum-gateway` | `enum-gateway` | ✅ No |
| `blind-transfer`, `disconnect-contact` | `terminating-action` | `terminating-action` | ✅ No |

The Flow Designer UI registers factories by widget `type` and only knows the generic types, so a corrupted `fn-activity`/`http-request` widget fails to open the flow with:

```
Failed to load flow
Cannot find factory with type [fn-activity]
```

Verified live 2026-07-23 by diffing `export-ui` of the same flow through three states:

| Flow state | Function-node widget `type` | Opens in Flow Designer UI? |
|---|---|---|
| Original (UI-authored) | `action` | ✅ Yes |
| After `wxcli cc-flow-store copy PROJECT_ID --source-flow-id FLOW_ID` only | `action` | ✅ Yes |
| After `wxcli cc-flow create-import PROJECT_ID --json-body file://flow.json` (new flow from FlowIR) | `action` | ✅ Yes — **`create` does NOT corrupt** (verified: `play-message` → `action`, `disconnect-contact` → `terminating-action`) |
| After `wxcli cc-flow create-flows PROJECT_ID FLOW_ID --json-body file://flow.json` (save-draft) of a FlowV2 body | `fn-activity` (and HTTP nodes → `http-request`) | ❌ No — "Cannot find factory" |

**Key distinction:** the bug is specific to `save-draft` (regenerating the diagram of an *existing* flow). Building a *new* flow with `create` runs a different diagram-generation path that assigns correct widget types — so the `build-flow-programmatic` skill (which uses `create`) produces UI-loadable flows. The corruption only bites when you `save-draft` a FlowV2 body over an existing flow.

The logical graph (`nodes`/`edges`/variables) and `validate` results are unaffected — only the widget `type` field is corrupted. Verified 2026-07-23 by diffing a corrupted widget against the original: **every field is identical except `type`** (`widgetType` stays `activity`, ports/coordinates/properties all intact). This makes the corruption fully reversible — see the workaround below.

> **Scope of this finding:** `save-draft` over an existing flow corrupts the diagram (verified 2026-07-23). `create` (new flow from FlowIR) does **not** — verified same day by creating a flow with `play-message`/`disconnect-contact` nodes and confirming `export-ui` shows widget types `action`/`terminating-action` (correct). So the corruption is a `save-draft`-only behavior, not a general FlowV2-import behavior.

> **⚠️ Measurement caution — always baseline against a widget `type` of `action`, not against a prior `export-ui`.** The corruption is easy to "fail to reproduce" if your BEFORE snapshot was itself taken after a `save-draft`. In one build the `export-ui` used as "before" already showed `fn-activity`/`http-request` widget types (it had been save-drafted earlier in the session), so comparing it to the post-`save-draft` "after" showed **no change** and led to a false "no corruption" conclusion. A truly clean baseline is a fresh `wxcli cc-flow-store copy PROJECT_ID --source-flow-id FLOW_ID` of a UI-authored / `import-ui`'d flow: its fn/HTTP widgets read `type: "action"` (verified 2026-07-23). Re-run the check against that, not against a possibly-already-corrupted export.

### Working CLI Workaround: `save-draft` → remap widget `type` → `import-ui`

You CAN add activities programmatically and keep the flow UI-openable. The trick: let `save-draft` do the hard part (generating complete, correctly-wired widgets/ports/arrows for the new nodes), then fix only the corrupted `type` field before re-importing via `import-ui` (which — unlike `save-draft` — transports the diagram **verbatim** and does NOT regenerate it). Verified end-to-end live 2026-07-23: the resulting flow had correct types, all `fnName`s intact, and the new nodes/edges wired.

**The `activityName` → correct-widget-`type` map** (harvest from any uncorrupted `export-ui` of the flow; these are the values seen in a real UI-authored flow):

| Widget `type` | activityNames that use it |
|---|---|
| `start` | the start node (`NewContact` etc.) |
| `action` | `http-request-v2`, `fn-activity`, `queue-contact`, `play-message`, `play-music`, `bridged-transfer`, and most other activities |
| `set-variable` | `set-variable` |
| `enum-gateway` | `condition-activity`, `ivr-menu` (and other branching/gateway activities) |
| `terminating-action` | `disconnect-contact`, `blind-transfer` |
| `end` | `end` (End Flow) |
| `arrow` | links (`widgetType: "link"`) — never remap these |

**Procedure** (always rehearse on a `copy` first — a plain `copy` is UI-loadable, so it's a safe sandbox):

```
1. wxcli cc-legacy-flows export-ui FLOW_ID PROJECT_ID -o json > ui_before.json   # BEFORE any save-draft — source of the correct type map
2. wxcli cc-flow show PROJECT_ID FLOW_ID -o json > flow.json                      # FlowV2 logical graph
   # edit flow.json: add nodes/edges (restore fnName on every fn-activity node first — see prior subsection)
3. wxcli cc-flow create-flows PROJECT_ID COPY_ID --json-body file://flow.json     # (save-draft) generates the full diagram, but with corrupted widget types
4. wxcli cc-legacy-flows export-ui COPY_ID PROJECT_ID -o json > ui_after.json    # complete graph + ports + arrows, wrong types
   # remap: for each activity widget in ui_after, set type = map[properties.activityName]
   #        (new activity nodes not in the map → "action"); leave widgetType:"link" arrows alone
   # clear top-level "id"/"flowId", set a unique "name"
5. wxcli cc-legacy-flows import-ui PROJECT_ID --file ui_after_fixed.json          # transports diagram verbatim → types preserved → UI-loadable
6. wxcli cc-legacy-flows export-ui NEW_ID PROJECT_ID -o json > verify.json       # confirm no widget has type in {activityName-style values}; confirm fnName intact
```

**Why it works:** `import-ui` is verbatim transport (v1 shape), so whatever widget `type` you set survives. Doing the graph-building with `save-draft` (on a throwaway copy) and the final write with `import-ui` gets you correct wiring *and* correct types.

⚠ **`save-draft` is NOT the only diagram-regenerating step — `wxcli cc-flow update` (rename/re-describe) also regenerates and selectively corrupts the diagram.** Because `update` writes via the v2 draft patch, it triggers the exact same widget-`type` corruption as `save-draft`. Verified live 2026-07-23: a fresh `copy` of a UI-loadable flow `export-ui`'d clean widget types `{'http-request-v2': 'action', 'fn-activity': 'action', 'end': 'end'}`; a single rename (run then as wxcc-flow update ID --name; today `wxcli cc-flow update PROJECT_ID FLOW_ID --json-body '{"name":"..."}'`; rename only, no other change) then `export-ui`'d `{'http-request-v2': 'http-request', 'fn-activity': 'fn-activity', 'end': 'action'}` — the same selective corruption (`fn-activity` → `fn-activity`, `http-request-v2` → `http-request`, `end` → `action`; other widgets untouched). **Implication:** if you rename a flow via the CLI after it was UI-loadable, re-run the `export-ui` → remap → `import-ui` fix above before opening it in the Flow Designer UI.

To land the workaround on the real flow, `import-ui` with `--overwrite yes` and the production flow's `name`. **Flow ID preservation is VERIFIED (2026-07-23):** `import-ui --overwrite yes` updates the SAME flow ID in place (an overwrite of `6a629dc0d66dac31e10dabb2` / `NAPA_huntgroup_routing` left exactly one flow with that ID and the corrected diagram). The CC entry-point assignment binds to the flow ID, so it should carry over — but the CC side was NOT directly re-verified here (cc-* APIs need cjp scope).

### v1 flows:import Is Multipart (Contract Mislabels It)

`POST /{orgId}/project/{projectId}/flows:import` (v1 import of UI-exported flow JSON) is a multipart file-upload endpoint: the live contract's requestBody schema is `{"file": {"type": "string", "format": "binary"}}` even though the content type reads `application/json` (springdoc mislabeling of a MultipartFile param). Sending the JSON as a raw request body returns a bare 500 ("Oops... Something broke..."). Send it as a multipart `file` part instead — `curl -F "file=@export.json;type=application/json"` or `wxcli cc-legacy-flows import-ui PROJECT_ID --file export.json`. Success is HTTP 201; a duplicate name with `overwrite=no` is a 409 FLOW_ALREADY_EXISTS. The payload is the verbatim `flows/{id}:export` output (name-only changes allowed; no field stripping needed). Query params `overwrite` (string yes/no) and `Flow Type` (with a space) are optional. Verified live 2026-07-11.

### v1 Merge-Patch Ignores Flow Metadata

`PATCH /{orgId}/project/{projectId}/flows/{flowId}` (application/merge-patch+json) returns 200 but silently ignores `name` and `description` — only `lastModifiedDate` changes (verified live 2026-07-11 with full before/after entity diffs). To rename or re-describe a flow, patch the v2 draft instead (`wxcli cc-flow update PROJECT_ID FLOW_ID --json-body '{"name":"NEW"}'`) and publish; the flow-level name updates on publish (verified live 2026-10-19 on a published flow; a never-published flow showed the new name before publish — § 9 Step 6).

### test-expr Bindings Are a Map, Not an Array

`wxcli cc-flow-store test-expression` passes variable bindings via `--json-body`, and the `variables` binding must be a **map** (name→value), NOT an array — e.g. `--json-body '{"expr":"{{ foo }}","variables":{"foo":"bar"}}'` → `generatedValue: "bar"`. The `[{"name","value","type"}]` array shape returns HTTP 400 "request body is not readable" (verified live 2026-07-23). The expression goes in `expr`: any other field name returned `isValid: false` with "compiledTemplate is null" and no error (wxcc, observed live 2026-07).

### Cascading Choices

Some activity fields have cascading dependencies — the available choices depend on a parent field's value. Pass the parent via the CLI (verified live 2026-07-11):

```
wxcli cc-flow list-activity-choices PROJECT_ID {activity} {input} --parent-input-name {parent} --parent-value {value}
```

The retired wxcc-flow `choices` took `--parent-input X`; the flag is `--parent-input-name X` here.

REST equivalent:

```
GET /{org}/project/{proj}/v2/activities/{name}/inputs/{input}/choices?parentInputName={parent}&parentValue={value}
```

Known cascading fields:
- `ivr-virtualassistantvoice` → `virtualAgentId` depends on `connector` value
- `queue-contact` → `destination` depends on `channelType` value (e.g. `--parent-input-name channelType --parent-value TELEPHONY`). Without the parent the call returns 400 — the old fallback to static values is gone — so always pass the parent context.

### `choices` Uses a Different Registry — `ReceiveMessage` and `SendCustomMessage` Cannot Be Imported

`wxcli cc-flow list-activity-choices` resolves against a **different** server-side registry from `list-activities` / `show-activity`, and the two disagree about which activities exist. Verified live 2026-07-25 (run then through wxcc-flow's `choices`, `activities` and `describe`, today's `list-activity-choices`, `list-activities` and `show-activity`): the choices call for `ReceiveMessage` `channelType` (and `channelName`, and `SendCustomMessage` `messageType`) returned 400 `"Activity 'ReceiveMessage' not found in registry for org=… flowType=FLOW"`, while in the same session the activity list held all 50 activities then in the registry, `ReceiveMessage` and `SendCustomMessage` among them, and the describe call for `ReceiveMessage` returned a full definition (`category: core`, `activityType: action`; inputs `channelType`, `channelName`, `timeout`, `appendToTranscript`, `outputVariableArray1`, `flowDecryptAccess`). The control, choices for `queue-contact` `channelType`, returned 200 in the same session. (Counts today: the registry lists 54 FLOW activities and 29 SUBFLOW, 2026-10-19, § 8; the "50" is the 2026-07-25 count. Both activities are still in the 2026-10-19 list.)

**The 400 is a true signal: flows using either activity cannot be imported** (open item O3, resolved 2026-07-25). `create-validate` runs in two stages. The port checks resolve against the `show-activity` registry, so a wrong port gives a precise error (`Condition 'out' is not valid for activity 'ReceiveMessage'. Use one of: error, timeout`); once the ports pass, the import pipeline returns 500 `ACTIVITY_NOT_FOUND` — `"Activity Mapping for ReceiveMessage could not be found"`. Reproduced live for both activities; a baseline flow without them validated clean in the same session. Use `show-activity` for what an activity's inputs and ports are, never as proof it can be built; author flows that need these two in the Flow Designer UI. The rule `flowir-mcp-verification.md` § "Reading a `choices` Failure Correctly" carries the same finding for authors.

### HTTP Connector Choices (`http-request-v2` `connectorId`)

Listable as of 2026-10-19 (verified live on the CC Bootcamp Sandbox): `wxcli cc-flow list-activity-choices PROJECT_ID http-request-v2 connectorId` returned 200 with 4 HTTP connectors, and `wxcli cc-flow list-connectors PROJECT_ID` returned 7 (the 4 HTTP connectors and 3 TTS connectors) with no failing source on stderr. Take `connectorId` from discovery; if a source fails again, `list-connectors` names it on stderr.

History: on 2026-07-25 the same choices call returned 502 wrapping an upstream `401 Unauthorized` from `GET /v1/config/organization/{orgId}/credentials`, and the connectors listing returned only the `Cisco Cloud Text-to-Speech` connector, so authenticated `http-request-v2` could not be configured from discovery and the ID came from Control Hub. Why it changed is not known. ⚠ Still UNTESTED: whether a connector ID that discovery does **not** list is accepted on import.

### `list-all-latest` Returns 500 Org-Wide

`wxcli cc-flow-versions list-all-latest PROJECT_ID` (the latest version of every flow) returns 500 for the whole org when any flow in the project has never been published (wxcc, 2026-07; the Flow Store answered JSON 500 on the CC Bootcamp Sandbox project again on 2026-10-19). wxcc-flow printed a warning before every call; `wxcli` does not. Fall back to the paged list of every version: `wxcli cc-flow-versions list-all PROJECT_ID --all`.

### SUBFLOW Templates Return 404

`wxcli cc-flow-store consume-template PROJECT_ID --template-name NAME --flow-name NEW --flow-type SUBFLOW` returns 404 `FLOW_TEMPLATE_NOT_FOUND` (wxcc, verified live 2026-07-12): SUBFLOW templates are behind the feature flag `flow-control-draft-templates`. `wxcli` prints `Warning: SUBFLOW templates 404 (feature-flag 'flow-control-draft-templates' gated)` (measured live 2026-10-19). Create subflows from FlowIR instead: `wxcli cc-flow create-import PROJECT_ID --json-body file://subflow.json --flow-type SUBFLOW` (§ 11 "Subflow Creation via FlowIR Import").

### Edges Reference Node `name`, Not `id`

FlowIR import matches each edge's `from`/`to` against node **`name`** values, not node `id`s. An edge that names a node id fails at `create` with `400 "Edge from='<id>' does not match any node name."` (verified live 2026-07-12: a fixture whose edges referenced node ids failed import until the edges were rewritten to node names). Node `id` is incidental to import — a live `flows/{id}:export` returns `null` for a node's `id`. When authoring or hand-editing FlowIR, always wire edges by node `name`. The same 2026-07-12 fix also rewrote the `eventFlows[*].onEvents` targets from ids to node names as a precaution and the flow then imported cleanly — but the 400 named only an edge, so whether `onEvents` strictly requires the name was not isolated; use node names there too to be safe.

### `copy` Returns 500 on Structurally-Incomplete Flows

`wxcli cc-flow-store copy PROJECT_ID --source-flow-id FLOW_ID` (`POST /flows/{id}:copy`) returns a generic `HTTP 500 "Oops... Something broke..."` when the source flow has unresolved structural errors (e.g. a GoTo/hand-off with no destination — the class of problem `validate` reports as FC1015; the 500 itself carries no specific code). The server **still creates the copy** (observed name prefix `Copy_`) despite the 500, so a scripted caller must reconcile by name after a 500 rather than trust the error to mean "nothing was created" (verified live 2026-07-12). `copy` succeeds cleanly on a valid flow.

## 12. Property Input Type Summary

The activity definition API uses different component types for input fields. Each type has a distinct FlowIR authoring pattern. The live prod registry does not name components directly — identify them from `wxcli cc-flow show-activity PROJECT_ID <activity>` (field type, allowed values, choices endpoint) and from the `/choices` 400 message, which names the component when a field doesn't support choices (e.g., "is a 'Toggle'").

### Component Type → FlowIR Pattern

| Component | FlowIR Pattern | How to discover values |
|-----------|---------------|----------------------|
| **Select** | Value + `:name`/`_name` suffix fields. For entity refs (queues, connectors): value=UUID, name=display name. For enums (methods, content types): value and name are the same. | `wxcli cc-flow list-activity-choices PROJECT_ID <activity> <field>` |
| **RadioGroup** | Direct value, no suffix fields. E.g., `"priorityRadioGroup": "staticPriority"` | Options visible in `wxcli cc-flow show-activity PROJECT_ID ACTIVITY` output or try common values |
| **RadioGroupWithValue** | Value + `:radioName`/`_radioName` suffix fields. `setToValue` for static, `setToVariable` for variable ref. | `choices` returns 400 naming the component type (the flat prod definition does not) |
| **VariableSelect** | Flow variable reference using `{{varName}}` syntax. Declare the variable in the flow's `variables` array with the correct type. | The flat prod definition gives only `type` — match the variable's type to what the field expects (see the activity's property table) |
| **Toggle** | Boolean `true`/`false`. Often controls visibility of other fields via `showOnCondition`. | Check `defaultValue` in describe output |
| **Input** | Direct value (string or number). May have `validationRegex` constraints. | Check describe output for defaults and constraints |
| **CheckBox** | Boolean `true`/`false`. | Same as Toggle |
| **KeyValuePairs** | JSON object `{"key": "value"}`. Values can use `{{variable}}` syntax. | N/A |
| **OrderedList** | Array of prompt objects: `[{"name": "text", "type": "tts", "value": "text"}]` | N/A |
| **SkillRequirementsAndRelaxation** | Object: `{"skillRequirements": [...], "relaxation": null}`. Cannot be `null` or `{}`. | N/A |
| **PercentAllocation** | Array of objects: `[{"percent": 60, "desc": "PathA"}]`. API says `string[]` but validator needs `object[]`. | N/A |
| **HandOffFlow** | Entry point UUID. Validation may false-positive (FC1015) but create succeeds. | `wxcli cc-flow list-activity-choices PROJECT_ID <activity> <field>` |
| **Duration** | String `HH:MM:SS`. Range: `00:00:05` to `72:00:00`. | N/A |
| **SubflowVersionSelect** | Object: `{"id": "<subflow-uuid>", "tag": "Latest"}`. Cannot query available subflows via choices API. | Manual: create subflow in UI, copy ID |

### Conditional Fields (`showOnCondition`)

**19 of 50 live activities expose fields gated by `showOnCondition` — 69 conditional fields in total. The other 31 activities are flat** (every input always applies). Verified against the live registry 2026-07-25, when it held 50 activities; the registry held 54 (FLOW) on 2026-10-19 (§ 8), and these counts were not re-measured against it.

`showOnCondition` is a **string expression evaluated against sibling input values** on the same node — not a static flag. Three consequences for FlowIR authoring:

- **A hidden field is not merely optional.** When its condition is not met, supplying the field may be rejected or silently ignored. Omitting the gating input does not make the gated field safe to include.
- **A required field only becomes required once its condition is met.** A field marked `required` in `describe` output is not unconditionally required — read its `showOnCondition` first.
- **The same field can appear more than once** with different conditions (see `queue-contact`, where `skills` and `toggleAgentAvailability` each appear twice).

| Activity | Conditional fields |
|----------|-------------------|
| `queue-contact` | 12 |
| `http-request-v2` | 7 |
| `queue-to-agent` | 7 |
| `ivr-collectdigits` | 5 |
| `ivr-menu` | 5 |
| `ivr-virtualassistantvoice` | 5 |
| `play-message` | 5 |
| `set-whisperannouncement` | 5 |
| `advanced-queue-info` | 2 |
| `business-hours` | 2 |
| `cryptographic-hash` | 2 |
| `ivr-virtualassistant` | 2 |
| `play-music` | 2 |
| `set-announcement` | 2 |
| `set-contact-priority` | 2 |
| `Feedback-V2` | 1 |
| `SendCustomMessage` | 1 |
| `callback` | 1 |
| `start-media-stream` | 1 |

Fully mapped in §7/§7b: `queue-contact`, `ivr-virtualassistantvoice`, `start-media-stream`, and the shared 5-field prompt pattern covering `play-message`, `ivr-menu`, `ivr-collectdigits`, and `set-whisperannouncement`. For any other activity in this table, read the conditions from `wxcli cc-flow show-activity PROJECT_ID <activity>` before authoring.

### Feature-Gated Activities

These activities returned `ACTIVITY_NOT_FOUND` on create when they were still listed. As of 2026-07-11 they no longer appeared in the live prod registry at all. Re-checked 2026-10-19 (live, CC Bootcamp Sandbox): they are **hidden by default, not gone** — absent from `wxcli cc-flow list-activities PROJECT_ID` (54) and `--flow-type SUBFLOW` (29), listed with `--check-ui-enabled true` (57). The `ACTIVITY_NOT_FOUND` status below is from when they were listed; it was not re-tested.

| Activity | Status |
|----------|--------|
| `flow-test-activity` | ACTIVITY_NOT_FOUND |
| `LiveCallerSentiment` | ACTIVITY_NOT_FOUND |
| `queue-reservation` | ACTIVITY_NOT_FOUND |

### Activities with Implicit `out` Success Port

Many action-type activities have an implicit `out` success port not reported by `describe` or the activity definition API. The port works for FlowIR edge conditions. Confirmed on: `generate-otp`, `screen-pop`, `queue-lookup`, `advanced-queue-info`, `escalate-cdg`, `set-contact-priority`, `record`, `RecordingControl`, `wait-activity`, `cryptographic-hash`, `upload-audio`, `start-media-stream`, `call-progress-analysis`, `set-announcement`, `send-digits`, `SetCallerID`, `Feedback`, `percent-allocation`, `hand-off`.

## See Also

- [flow-designer-essentials.md](flow-designer-essentials.md) — the activities FlowIR describes, in Flow Designer terms
- [_index.md](flow-designer-activities/_index.md) — one file per activity, with exit paths and limits
- [flow-blueprints.md](flow-blueprints.md) — complete working flows written in FlowIR
- [flow-designer-patterns.md](flow-designer-patterns.md) — versioning, subflows and the management API
