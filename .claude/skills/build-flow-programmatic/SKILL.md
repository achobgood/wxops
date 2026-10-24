---
name: build-flow-programmatic
description: |
  Build a WxCC Flow Designer voice flow programmatically from an existing design
  document in docs/plans/. Generates FlowIR JSON, validates via wxcli (the cc-flow* and cc-functions groups),
  creates the flow in the sandbox, and optionally publishes it.
  Use for: programmatic flow creation AFTER a design document exists — the
  programmatic alternative to build-flow-designer (design-flow → build-flow-programmatic).
  NOT for: creating the design (design-flow) or manual UI builds (build-flow-designer).
allowed-tools: Read, Grep, Glob, Bash, Edit, Write
argument-hint: [path-to-design-doc]
---

# Build Flow Programmatic Workflow

## Step 1: Load references

YOU MUST use the Read tool on each of these files sequentially. Do not proceed until all reads are complete.

1. Read `docs/reference/flow-designer-flowir.md` — §2 (FlowIR Structure), §3 (Variables), §4 (Nodes), §5 (Edges), §6 (Event Flows), §7/§7b (Activity Properties), §11 (Gotchas)
2. Read `docs/reference/flow-designer-essentials.md` — essential activity configs
3. Read this skill's `reference.md` — validated property patterns and CLI commands

**Checkpoint:** Before proceeding, confirm you can answer:
- What are the required fields in a FlowIR node? (from §4)
- What is the 5-field connector pattern for TTS activities? (from §7)
- What is the Set Variable double declaration rule? (from §11)

## Step 1.5: Check for design doc

1. If an argument was passed: read the design doc at that path
2. If no argument: use Glob to check `docs/plans/*.md` for recent flow design docs
3. If a design doc exists with Activities table (§4), Connections table (§5), Variables (§3), Event Handlers (§6): use it
4. If NO design doc exists: tell the user to run `design-flow` first. Do NOT proceed without one.

## Step 2: Parse the design doc

Extract these sections from the design doc:

| Design Doc Section | FlowIR Target |
|---|---|
| §2 Flow Metadata (name, type) | Top-level `name`, `flowType`, `description` |
| §3 Variables | `variables` array |
| §4 Activities table | `nodes` array |
| §5 Connections table | `edges` array |
| §6 Event Handlers | `eventFlows` object |
| §7 TTS Content | Activity `properties` (prompts, promptsTts) |
| §8 External Integrations | HTTP Request node properties |

## Step 2.5: Provision missing WxCC resources

Before resolving entity IDs, check whether the resources referenced in the design doc exist. The Flow Store API can only LOOK UP existing resources — it cannot CREATE teams, queues, business hours, or entry points.

1. Check existing resources: `wxcli cc-queue list`, `wxcli cc-team list`, `wxcli cc-business-hour list`, `wxcli cc-entry-point list`
2. For any resource that doesn't exist, create it via the WxCC Provisioning API. See `docs/reference/wxcc-provisioning-api.md` for the exact API patterns (required fields, gotchas).
3. Provisioning order: Site (usually exists) → Team → Queues (need team ID + CDG) → Business Hours → Entry Point (can include flowId)

**Create with `--json-body`.** `wxcli cc-team create --json-body '{"name":"…","siteId":"…","active":true,"teamType":"AGENT","teamStatus":"IN_SERVICE"}'` sends the JSON as the request body: verified live 2026-10-19 on the CC Bootcamp Sandbox (team created, name and site read back with `wxcli cc-team show`). `wxcli cc-queue create-contact-service-queue --json-body file://queue.json` created a queue the same day; see `docs/reference/wxcc-provisioning-api.md` for the fields a queue needs. (History: until the generator fix of 2026-10-13, ADR-16, `cc-team create` sent the body as a query parameter, and this gotcha said to use direct `curl` calls for resource creation; curl remains the raw-HTTP fallback.)

## Step 3: Resolve entity IDs

After provisioning, resolve all entity references to UUIDs (`PROJECT_ID` below is the `projectId` that `wxcli cc-flow-projects show-user-preferences` returns):

- **Queues:** `wxcli cc-flow list-activity-choices PROJECT_ID queue-contact destination --parent-input-name channelType --parent-value TELEPHONY` → get queue UUID (cascading input — the parent flags are required)
- **TTS Connectors:** `wxcli cc-flow list-activity-choices PROJECT_ID play-message connector` → get connector UUID/name
- **HTTP Connectors:** `wxcli cc-flow list-activity-choices PROJECT_ID http-request connectorId` → get connector UUID
- **Business Hours:** `wxcli cc-flow list-activity-choices PROJECT_ID business-hours businessHoursId` → get schedule UUID
- **Entry Points (for GoTo):** `wxcli cc-flow list-activity-choices PROJECT_ID hand-off handOffFlow` → get EP UUID
- **Global Variables:** `wxcli cc-flow-store list-global-variables PROJECT_ID --fields variables` → get the full metadata object (including `id`, `source`, `isReportable`, `isCAD`, `desktopLabel`) for any global variable referenced in the design doc (e.g., `Global_Language`, `Global_VoiceName`). Copy the entire object into the FlowIR `variables` array and make sure `source` is `"GLOBAL"` — the value stored flows hold (verified live 2026-10-19; `"GLOBAL_TM"`, which this step named until then, also passes validate but no stored flow read holds it) [`flow-designer-flowir.md` § 3]. Without `source` and `id`, Set Variable creates a local shadow that doesn't affect the TTS engine or Analyzer.

Report the resolved IDs to the user for confirmation before proceeding.

## Step 4: Compose FlowIR JSON

**Before writing any FlowIR:** read `.claude/rules/flowir-mcp-verification.md` and do its Mandatory Steps (`wxcli cc-flow show-activity PROJECT_ID ACTIVITY`, `wxcli cc-flow list-activity-choices PROJECT_ID ACTIVITY INPUT`, `wxcli cc-flow show-node-template PROJECT_ID ACTIVITY`, then `wxcli cc-flow create-validate PROJECT_ID --json-body file://FLOW_FILE`). Never guess a property name.

Generate the complete FlowIR JSON. Follow these rules strictly:

### Node structure
Every node must have: `id`, `name`, `activityType`, `group`, `properties` (with `activityName`).

### Activity property patterns
- **TTS activities** (play-message, ivr-menu, ivr-collectdigits, set-whisperannouncement): use the 5-field connector pattern from reference.md
- **queue-contact**: use minimal `queueId` + `channelType` pattern — do NOT include `queueRadioGroup`
- **set-variable**: include BOTH `variable_N`/`value_N` fields AND `setVariablesArray`
- **condition-activity**: use `expression` field with `{{variable operator value}}` syntax
- **RadioGroupWithValue fields**: include `:radioName` and `_radioName` suffix fields

### Edge structure
Every edge: `from` (node id), `to` (node id), optional `condition` (port name), and optionally `id` — validate passes with or without edge `id`s, and the server does not store them (verified live 2026-10-19) [`flow-designer-flowir.md` § 5].

### Event flows
Minimum: `OnGlobalError` with Play Message → Queue Contact → Play Music → Disconnect chain.

### Write the file
Write the FlowIR JSON to `docs/plans/flowir/{flow-name}.json`. Create the directory if needed.

## Step 5: Validate

```bash
wxcli cc-flow create-validate PROJECT_ID --json-body file://docs/plans/flowir/{flow-name}.json
```

- **Errors (FC1015, FC1002, etc.):** Fix the FlowIR JSON and re-validate. See reference.md for common fixes.
- **Warnings only (FC1004, FC1007):** Report to user, continue — these are recommendations, not blockers.
- **Validation pipeline errors (FC0000):** Usually ignorable — some activity validators have internal issues.

Iterate until `valid: true`.

## Step 6: Create

```bash
wxcli cc-flow create-import PROJECT_ID --json-body file://docs/plans/flowir/{flow-name}.json
```

Capture the flow ID from the output. If creation fails with ACTIVITY_NOT_FOUND, the activity may be feature-gated — check reference.md.

## Step 7: Verify round-trip

```bash
wxcli cc-flow export PROJECT_ID {flow-id} --version draft -o json
```

Spot-check that key properties survived the import: queue IDs, TTS connector names, variable assignments, edge conditions. Report any discrepancies.

**UI-loadability:** Flows built here via `wxcli cc-flow create-import` open normally in the Flow Designer UI — `create-import` assigns correct diagram widget types (verified 2026-07-23, run then as wxcc-flow create). This does NOT hold for `cc-flow create-flows` (wxcc-flow's save-draft): adding activities to an *existing* flow with `wxcli cc-flow create-flows` corrupts the diagram widget types and the flow then fails to open with "Cannot find factory with type [...]". To add activities to an existing flow programmatically and keep it UI-openable, use the `wxcli cc-flow create-flows` → `wxcli cc-legacy-flows export-ui` → remap widget types → `wxcli cc-legacy-flows import-ui` workaround in `docs/reference/flow-designer-flowir.md` § "Working CLI Workaround".

## Step 8: Publish (optional)

Ask the user if they want to publish:

```bash
wxcli cc-flow publish {flow-id} PROJECT_ID
```

`wxcli cc-flow publish` validates the flow first (wxcc-flow publish did not, unless asked); add `--skip-validation true` to publish without that check.

Remind them to assign the flow to an Entry Point in Control Hub (see `docs/playbooks/wxcc-setup.md`).

## Step 9: Present summary

Show:
- Flow ID and name
- Status (Draft / Published)
- Activity count and edge count
- Any validation warnings
- Next steps (assign to Entry Point, configure queues/teams if not done)

---

## CRITICAL REMINDERS

- NEVER guess FlowIR property names — always check `flow-designer-flowir.md` §7/§7b
- NEVER generate proprietary export JSON — only FlowIR
- Read the specific activity doc before composing properties for ANY activity
- The 5-field connector pattern is REQUIRED for all TTS activities
- Use `queueId` for queue-contact, NOT `destination` (see §11 Property Name Mismatches)
- Set Variable requires BOTH numbered fields AND `setVariablesArray`
- `subflow-handoff` and `fn-activity` require manually-created entity IDs — they cannot be created via the CLI
- `end-subflow` is NOT importable — use `end` as a substitute
- Always validate before creating — `wxcli cc-flow create-validate PROJECT_ID --json-body file://FLOW_FILE` catches most errors before they hit the server
