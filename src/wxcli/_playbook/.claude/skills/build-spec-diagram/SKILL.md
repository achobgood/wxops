---
name: build-spec-diagram
description: |
  Generate a .drawio flow diagram from a Flow Designer design document in
  docs/plans/: a 3-tab diagram (Summary, Main Flow, Event Flow) with activity
  cards in the Cloverhound/WxCC Flow Builder format.
  Triggers on: "build spec diagram", "generate flow diagram", "visualize this spec", "spec to drawio".
  Use for: visual .drawio representation of a Flow Designer design — activities, ports, connections.
  NOT for: architecture docs with Mermaid and PPTX (build-solution-docs), building the flow
  (build-flow-designer), designing it (design-flow).
allowed-tools: Read, Bash, Write, Grep, Glob
argument-hint: [path-to-plan-document]
---

# Build Spec Diagram Workflow

## Step 1: Load references

1. Read this skill's `reference.md` for XML templates, icon registry, color constants, and layout rules
2. Read the user's plan document (the argument passed to this skill, or ask which plan to use from `docs/plans/`)
3. For each activity type in the plan, read its doc from `docs/reference/flow-designer-activities/` or `docs/reference/flow-designer-essentials.md` to get: category, connection ports, output variables, required settings

**Checkpoint — do NOT proceed until you can answer these:**
- What activities are in the plan? (names, types, configurations)
- What connections exist between them? (source port → target activity)
- What flow variables are defined? (name, type, default, description)
- What event handlers does the plan specify?

## Step 2: Parse the design doc into a structured model

Extract from the plan document:

| Field | Source |
|---|---|
| **Flow name** | Plan title / H1 heading |
| **Description** | Purpose section |
| **Author** | Created-by or infer from git |
| **Activities** | `## Activities` table (Section 4 in `flow-designer-design-doc.md` template) or `## Node-by-Node Configuration` in older plans — for each: ID/label, activity type, key configuration |
| **Connections** | `## Connections` table (Section 5 in template) — Source Activity, Port, Target Activity |
| **Variables** | `## Variables` section (Section 3 in template) — flow variables table + global variables table |
| **Event handlers** | `## Event Handlers` section (Section 6 in template) — OnGlobalError chain + additional handlers |

Build an in-memory list of activity objects:

```
activity = {
  id: "PlayMessage_001",        # type + counter
  name: "Welcome Message",      # display name from plan
  type: "Play Message",         # canonical activity type
  category: "Action",           # from reference.md category map
  config: { key: value, ... },  # configuration details
  ports: ["Default", "Error"],  # from reference.md port definitions
}
```

If the design doc format doesn't map cleanly to activities, ask the user to confirm the activity list before generating.

## Step 3: Look up activity metadata

For each activity in the model:

1. Determine its **category** from the `CATEGORY_MAP` in `reference.md`
2. Look up its **exit ports** from the `PORT_DEFINITIONS` in `reference.md`
3. Get its **SVG icon** from the `ICON_REGISTRY` in `reference.md`
4. Get its **badge color**, **card fill color**, and **badge shape** from the `CATEGORY_COLORS` in `reference.md`

If the activity type isn't in the reference, fall back to the category default icon. If the category is unknown, use Action as the default.

## Step 4: Build the JSON model

Build a JSON object following the schema below. Write it to a temp file (e.g., `/tmp/flow-model.json`).

### JSON Schema

```json
{
  "flow_name": "string — H1 title from the plan",
  "description": "string — first sentence of Use Case section",
  "author": "string — from git or plan metadata",
  "date": "string — YYYY-MM-DD",

  "variables": [
    {
      "name": "CallerANI",
      "type": "String",
      "default": "",
      "desc": "Raw ANI from NewPhoneContact"
    }
  ],

  "activities": [
    {
      "id": "HTTPRequest_001",
      "name": "CJDSEventCheck",
      "type": "HTTP Request",
      "details": "Use Authenticated Endpoint: Off\nRequest URL: https://api-jds...\nMethod: GET\n..."
    }
  ],

  "edges": [
    {
      "source": "NewPhoneContact_001",
      "port": "Out",
      "target": "SetVariable_001"
    }
  ],

  "events": []
}
```

### Field rules

| Field | Who owns it | Notes |
|-------|-------------|-------|
| `id` | You assign | Format: `{TypeNoSpaces}_{NNN}`. Must be unique. Edges reference these. |
| `type` | You assign | Must be a canonical activity type name from reference.md (e.g., `"HTTP Request"`, not `"HTTPRequest"`). Script derives category, ports, icon, and colors from this. |
| `details` | You build | Pre-formatted plain text, one `key: value` per line. Script renders verbatim — does not parse or interpret. For HTTP Request nodes, include all fields, query params, headers, parse settings, and request body. |
| `events` | You populate or leave empty | If `[]`, script generates the 10 default event handlers. If populated, uses those instead. Each event entry has `name`, `event_type`, `event_name`. |
| `edges` | You enumerate | Every connection in the flow. `port` must be a canonical port name from reference.md PORT_DEFINITIONS. The script warns on unrecognized ports. **Do NOT generate edge entries for Error / Undefined Error ports.** These are auto-handled by OnGlobalError and should not appear as edges in the diagram. Only include an Error port edge if the design doc explicitly routes that Error port to a specific activity (not OnGlobalError). |

### Details text format

```
Field1: value1
Field2: value2
--- Query Parameters ---
key1: value1
key2: value2
--- HTTP Headers ---
Authorization: Bearer {{token}}
--- Parse Settings ---
OutputVar: $.json.path
--- Request Body ---
{
  "full": "json body here"
}
```

Section dividers (`--- Label ---`) are optional — only include when the node has that section. The script renders this as-is in fontSize=8 plain text.

### Building the model

For each activity in the plan:
1. Assign an `id` in `{TypeNoSpaces}_{NNN}` format (e.g., `PlayMessage_001`, `Condition_002`)
2. Set `type` to the canonical activity type name from reference.md
3. Build `details` as plain text with every config field from the plan — never truncate URLs, JSON bodies, or filter expressions

For each connection in the plan, add an `edges` entry with `source` (activity id), `port` (canonical port name from PORT_DEFINITIONS), and `target` (activity id).

Write the JSON to a temp file using the Write tool.

## Step 5: Generate the .drawio

```bash
python3 .claude/skills/build-spec-diagram/generate.py /tmp/flow-model.json {output-path}
```

Where `{output-path}` is in the same directory as the plan, named `{plan-name}-flow.drawio` (strip date prefix if present).

The script:
- Enriches each activity with category, ports, and icon based on `type`
- Validates that all edge source/target IDs exist
- Computes card heights from details line count and port count
- Runs BFS layout to position cards left-to-right
- Generates XML for all 3 tabs (Summary, Main Flow, Event Flow)

## Step 6: Open the file

```bash
open {output-path}
```

Tell the user:
1. The file path
2. It opens in DrawIO (desktop app, VS Code extension, or draw.io web)
3. They can rearrange cards, collapse sections, and edit details directly in DrawIO

---

## CRITICAL REMINDERS

- **Activity configs come from docs, not training data.** Every field name and port name must trace to `docs/reference/flow-designer-activities/` or `flow-designer-essentials.md`.
- **Unique IDs.** Use `{ActivityType}_{counter}` format (e.g., `PlayMessage_001`) — human-readable and debuggable.
- **Don't fabricate config.** Only use information from the plan document. If the plan doesn't specify a field, omit it from the Details section.
- **Don't truncate.** Never shorten URLs, JSON bodies, filter expressions, or header values. The details text is rendered verbatim.
- **Port names are canonical.** Use the exact port names from PORT_DEFINITIONS in reference.md (e.g., `"Default"`, not `"Success"`; `"True"`, not `"TRUE"`).
- **Test the output.** After generating, verify the file opens correctly by running `open`.
