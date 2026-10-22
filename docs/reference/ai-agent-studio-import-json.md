<!-- ref-tag: ai-agent-import-json-v1 -->

# AI Agent Studio Import JSON — Autonomous Agent Format

Authoritative schema for the import/export JSON that Webex AI Agent Studio uses to
create an **autonomous** agent (`bot_type: virtualagent`) in one step, instead of
configuring the goal, welcome message, voice settings, and each action by hand in the
Studio UI.

**Scope:** autonomous agents only. Scripted agents export as a completely different
format (`bot_type: mlbot`, top-level `intents` / `entities` / `responses` — no
`configuration` or `tools` keys). That format is NOT documented here and must not be
generated from this reference. See "Scripted agents" at the bottom.

## Provenance

Two classes of claim in this doc have two different sources. Keep them separate.

**Structural claims (field names, nesting, types, constants)** were verified field-by-field
against real AI Agent Studio agent exports published in the official Cisco
`ciscoAISCG/webex-cx-ai` repository:

- `Playbooks/concierge-ai-agent/templates/concierge-ai-agent-studio-import.json` (import template; contains a `custom_transfer` tool)
- `Playbooks/Order_Tracking/exports/Order_Tracking_Agent.json` (built agent, voice)
- `Playbooks/Data_Driven_Ordering/exports/Data_Driven_Ordering_Agent.json` (built agent, voice)

**Behavioral / validation claims** (character limits, action-count limits, which fields the
importer validates, why `kb_ids` must be empty) are NOT derivable from static export files.
They come from Cisco's published `webex-ai-agent-creator` skill and its
`references/ai-agent-studio-json-import.md` in the same repo (Skills Shed). These are
official but secondhand guidance, not something this project has independently tested. Each
such claim below is tagged `[Cisco guidance]`. Anything neither in an export nor in Cisco's
published guidance is tagged `[INFERRED — unverified]`.

Do not add a structural field that does not appear in one of the verified exports. If a
field or rule is needed but unverified, mark it explicitly and confirm against a fresh
export or a real import attempt in the user's tenant.

## When to Use

Generate this file as an **accelerator** after the agent design is complete (goal,
welcome message, actions with parameters, instructions). It produces a draft agent
skeleton the user imports and then finishes in the UI. It does NOT replace building the
backing Webex Connect action flows — those are created separately, and their real
`flow_id`, `service_id`, and `webhook_url` values replace the placeholders after import.

## Top-Level Structure

The file is a single JSON object with exactly three top-level keys:

| Key | Type | Value |
|-----|------|-------|
| `bot_type` | string | `"virtualagent"` for autonomous agents (verified constant) |
| `configuration` | object | Agent metadata, model settings, instructions, greeting, voice settings (9 keys — see below) |
| `tools` | array | System tools + one entry per action (see Tools Array) |

The file must be valid JSON with no comments and no Markdown fences.

## `configuration` Object — All 9 Fields

Every export contains exactly these 9 keys:

| Field | Type | Verified value / rule |
|-------|------|-----------------------|
| `ai_engine` | string | `"PRO_US"` (only value seen in verified exports; other engine codes are not in verified sources) |
| `default_language` | string | BCP-47 locale, e.g. `"en-US"` |
| `kb_ids` | array | **Always `[]`.** Per Cisco guidance, invalid or guessed knowledge-base IDs can cause import or UI errors — never populate this. `[Cisco guidance]` |
| `llm_agent_description` | string | Agent goal + instructions, formatted per the rule below |
| `llm_model` | string | `"1.0.0"` (verified constant) |
| `logo` | string | Default: `"https://aiagent.webexbotbuilder.com/static/assets/img/bot-logo/default-virtualagent.svg"` |
| `timezone` | string | **Valid IANA timezone** (e.g. `"Europe/London"`, `"America/Los_Angeles"`). Per Cisco guidance the importer validates this field, so never use a placeholder here. `[Cisco guidance]` |
| `voice_settings` | object | `advance_settings` + `voices` (see Voice Settings). Present for both voice and digital agents. |
| `welcome_message` | string | The greeting the agent opens with; keep aligned with the design's suggested greeting |

### `llm_agent_description` Format

This single field holds both the goal and the full instructions, joined by a literal
separator:

```text
<Agent goal text>

### INSTRUCTIONS:
<Detailed AI agent instructions>
```

- One blank line between the goal and the `### INSTRUCTIONS:` separator.
- The instructions portion must stay **under 5000 characters**. `[Cisco guidance]`

## Voice Settings — Full Enumeration

`voice_settings` has two keys: `advance_settings` and `voices`.

```json
{
  "advance_settings": {
    "global": {
      "delays_and_interruptions": {
        "caller_turn_timeout": 1500,
        "custom_no_input": 10,
        "customer_interruption": true,
        "eos_sensitivity": 500,
        "fulfilment_timeout": 30,
        "optimized_barge_in": true,
        "slots_additional_delay": 800
      },
      "dtmf_settings": {
        "max_length": 16,
        "term_char": "#",
        "timeout_between_digits": 5,
        "turn_on_dtmf": true
      },
      "is_customized": false,
      "response_settings": {
        "custom_vocabulary": [],
        "include_disfluencies": true,
        "response_style": "ACTIVE"
      }
    }
  },
  "voices": []
}
```

Field enumeration:

- `advance_settings.global.delays_and_interruptions` — 7 fields: `caller_turn_timeout`, `custom_no_input`, `customer_interruption` (bool), `eos_sensitivity`, `fulfilment_timeout`, `optimized_barge_in` (bool), `slots_additional_delay`. Numeric fields are bare numbers in the exports; the defaults shown above are the verified values — carry them through verbatim rather than reasoning about their units. `[units INFERRED — unverified]`
- `advance_settings.global.dtmf_settings` — 4 fields: `max_length`, `term_char`, `timeout_between_digits`, `turn_on_dtmf` (bool).
- `advance_settings.global.is_customized` — bool. `false` when using the defaults above; `true` when the tenant tuned them.
- `advance_settings.global.response_settings` — 3 fields: `custom_vocabulary` (array), `include_disfluencies` (bool), `response_style` (`"ACTIVE"` or `"DIRECT"` — both verified).
- `voices` — array. Empty `[]` for digital-only agents. For voice agents, one entry with `displayName`, `language`, `locale`, and optional `speaking_rate`, e.g. `{"displayName": "en-US-Jess", "language": "English", "locale": "en-US", "speaking_rate": 1}`. **Always leave the specific voice as a placeholder** — the user must confirm an available voice in their tenant.

## Tools Array

The `tools` array holds one entry per system tool plus one entry per business action.

### System Tool — Agent Handover (include by default)

Always include the human-escalation tool unless the user explicitly excludes escalation.
All 9 fields:

```json
{
  "capability": "slot_filling",
  "description": "Escalate the conversation to a human agent if the user asks for it.",
  "enabled": true,
  "fulfillment": {},
  "id": "<unique_32_char_hex_id>",
  "name": "Agent handover",
  "slots": [],
  "slots_view": "table",
  "system_tool": true
}
```

- `capability` — `"slot_filling"` for the handover tool (no fulfillment call).
- `fulfillment` — empty object `{}`.
- `id` — a unique 32-character lowercase hex string, generated per tool.
- `system_tool` — `true`.

### Business Action Tool — `slot_filling_with_fulfillment`

One entry per flow-backed action — the common case. (Agent-to-agent handoffs use the
`custom_transfer` shape documented after this one.) All fields, verified from real exports:

```json
{
  "bot_id": 0,
  "capability": "slot_filling_with_fulfillment",
  "description": "<action purpose and parameter-sourcing guidance>",
  "enabled": true,
  "fulfillment": {
    "authentication": {
      "service_key": "",
      "type": "ci_bearer_token"
    },
    "flow_builder": "connect",
    "flow_id": "",
    "flow_name": "",
    "output_entities": {
      "parameters": {
        "properties": {},
        "required": [],
        "secure": [],
        "type": "object"
      }
    },
    "output_entities_format": "table",
    "output_entities_text": "",
    "output_entities_view": "table",
    "service_id": "",
    "service_name": "",
    "type": "flow",
    "webhook_url": ""
  },
  "id": "<unique_32_char_hex_id>",
  "input_entities": {
    "parameters": {
      "properties": {
        "<parameter_name>": {
          "description": "<plain-language description; use {{parameter_name}} when the value is always injected>",
          "examples": [],
          "type": "string"
        }
      },
      "required": ["<required_parameter_name>"],
      "secure": [],
      "type": "object"
    }
  },
  "name": "<action_name>",
  "slots_view": "table",
  "system_tool": false
}
```

**Unbuilt-flow convention:** the concierge *import template* leaves every Connect-specific
value as an **empty string** — `flow_id: ""` (a string, not `0`), `flow_name: ""`,
`service_name: ""`, `service_id: ""`, `webhook_url: ""` — because the backing flows are not
wired yet. This doc uses that verified empty-string convention. (Cisco's published import
guidance alternatively prescribes `flow_id: 0`; both are unverified for a
`slot_filling_with_fulfillment` action specifically, since the only real *import* file
observed uses a `custom_transfer` tool. When in doubt, follow the empty-string convention
and confirm against a real import.)

Field notes:

- `bot_id` — integer. Tenant-specific in real exports (e.g. `22471`); set to `0` for a fresh import.
- `capability` — `"slot_filling_with_fulfillment"` for actions that call a flow.
- `fulfillment.authentication` — 2 fields: `service_key` (empty string) and `type` (`"ci_bearer_token"`).
- `fulfillment.flow_builder` — `"connect"` (Webex Connect fulfillment). Present in all real exports; not listed in Cisco's Skills-Shed `ai-agent-studio-json-import.md` sample.
- `fulfillment.flow_id` — empty string `""` at import; replaced with the real flow ID after the Connect flow is built (built-agent exports show an integer, e.g. `92066`).
- `fulfillment.flow_name` — empty string `""` at import; the backing flow's name after wiring.
- `fulfillment.output_entities.parameters` — 4 keys: `properties` (object), `required` (array), `secure` (array), `type` (`"object"`). Leave `properties`/`required`/`secure` empty on generation; the fields the flow returns are mapped in the UI.
- `fulfillment.output_entities_format` / `output_entities_view` — `"table"`. `output_entities_text` — empty string.
- `fulfillment.service_id` — empty string `""` at import (real value is the tenant's Connect service ID).
- `fulfillment.service_name` — empty string `""` at import (the Connect service name after wiring).
- `fulfillment.type` — `"flow"`.
- `fulfillment.webhook_url` — empty string `""` at import. Built-agent exports follow the pattern `https://hooks.<dc>.webexconnect.io/flows/<flow_id>/trigger/aiagent` (e.g. `https://hooks.us.webexconnect.io/flows/92066/trigger/aiagent`; only the `us` data center appears in the observed samples). The real URL comes from the built flow.
- `id` — unique 32-character lowercase hex, generated per tool.
- `input_entities.parameters` — 4 keys: `properties` (each parameter as a JSON-Schema property), `required` (array of required parameter names), `secure` (array — empty unless a parameter is sensitive), `type` (`"object"`). Each property has `description`, `examples` (array; populate from the entity's example value), and `type`. `type` is usually `"string"`; a fixed-choice parameter instead uses `"type": "custom_list"` with an `"enum": [...]` array of allowed values (verified in the concierge `target_agent` parameter). Put optional parameters in `properties` but NOT in `required`.
- `name` — the action name. **Must match the action name used in the instructions verbatim.**
- `system_tool` — `false`.

### Agent-to-Agent Transfer Tool — `custom_transfer`

The concierge import file contains a third tool shape: a `custom_transfer` tool that hands
the conversation to another AI agent rather than calling a flow. All fields, verified from
`concierge-ai-agent-studio-import.json`:

```json
{
  "action_type": "transfer",
  "bot_id": 0,
  "capability": "custom_transfer",
  "description": "<when to transfer and what summary to include>",
  "enabled": true,
  "exit_details": { "announce_transfer": true, "type": "custom_transfer" },
  "fulfillment": {
    "authentication": { "service_key": "", "type": "ci_bearer_token" },
    "exit_details": { "announce_transfer": true, "type": "custom_transfer" },
    "flow_builder": "connect",
    "flow_id": "",
    "flow_name": "",
    "output_entities": { "parameters": { "properties": {}, "required": [], "secure": [], "type": "object" } },
    "output_entities_format": "table",
    "output_entities_text": "",
    "output_entities_view": "table",
    "service_id": "",
    "service_name": "",
    "type": "flow",
    "webhook_url": ""
  },
  "id": "<unique_32_char_hex_id>",
  "input_entities": { "parameters": { "properties": { "<param>": { "description": "…", "examples": [], "type": "string" } }, "required": [], "secure": [], "type": "object" } },
  "name": "<transfer_action_name>",
  "skip_greetings_match_voice": true,
  "slots_view": "table",
  "system_tool": false
}
```

Differences from the `slot_filling_with_fulfillment` shape: adds tool-level `action_type`
(`"transfer"`), tool-level `exit_details` and a duplicate `fulfillment.exit_details`
(`{"announce_transfer": true, "type": "custom_transfer"}`), and `skip_greetings_match_voice`
(bool). Only generate this shape when the design explicitly calls for an agent-to-agent
handoff; otherwise use the flow-backed action shape above.

## Import-Validation Gotchas

Items 1–4 are Cisco's published import guidance `[Cisco guidance]`; items 5–6 are
structural requirements of the JSON itself.

1. **`configuration.kb_ids` must be `[]`.** Guessed KB IDs can cause import or UI errors. `[Cisco guidance]`
2. **`configuration.timezone` must be a real IANA value** — the importer validates it, so no placeholder. `[Cisco guidance]`
3. **Instructions under 5000 characters** (inside `llm_agent_description`). `[Cisco guidance]`
4. **Maximum 10 action tools.** If the design needs more than 10 actions, split into multiple agents. `[Cisco guidance]`
5. **Action names must match** between the instructions text and `tools[].name`.
6. **Every tool `id` must be unique** and 32 lowercase hex characters. Cisco's guidance calls for unique generated IDs to keep the JSON valid; a collision or malformed ID risks import rejection.

## Placeholder Rules — What to Generate vs. What the User Replaces

Leave these empty (do NOT invent real values) — they are filled after the Connect flows
exist:

- `service_name` and `service_id` — empty string `""`
- `flow_id` and `flow_name` — empty string `""` for each action
- `webhook_url` — empty string `""` for each flow
- The specific voice in `voice_settings.voices` — leave the voice entry as a placeholder, or use `voices: []` for a digital-only agent

Never invent real Epic, Webex Connect, service, flow, webhook, or knowledge-base IDs.
State clearly in the handoff that the user must build the Webex Connect flows and replace
these placeholders before the imported agent is functional beyond a draft/demo.

## Scripted Agents (Out of Scope Here)

Scripted agents export with `bot_type: "mlbot"` and a fundamentally different top-level
shape — **no `configuration` or `tools` keys.** The full top-level key set observed in a
real `mlbot` export (`Payment_AI_Agent_Scripted.json`) is: `agent_handover_setting`,
`algorithm`, `allow_agent_handover`, `allow_curation`, `allow_feedback`, `bot_metadata`,
`bot_type`, `curation_settings`, `default_language`, `description`, `entities`,
`error_message`, `first_message`, `intents`, `language`, `languages`, `logo`, `responses`,
`test_cases`, `test_cases_callbacks`, `test_cases_partial_match_success`, `voice_settings`.
That format is not documented or generated from this reference. If a user needs a
scripted-agent import file, capture a real `mlbot` export from their tenant first and
document it separately before generating one.

## See Also

- [ai-agent-studio.md](ai-agent-studio.md) — the agent setup, instructions, actions and Flow Outcomes that an imported JSON file configures
- [ai-agent-studio-scripted.md](ai-agent-studio-scripted.md) — the scripted-agent side, which this file leaves out of scope
