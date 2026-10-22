# Scripted Fulfillment -- Quick Reference

## Digital Fulfillment Flow Structure

```
AI Agent (onSuccess) → Data Parser (SessionMetadata) → Branch (template_key)
  → Fulfillment: HTTP Request → Evaluate → Channel Reply → Append Conversation → Receive → [loop to AI Agent]
  → Default: Channel Reply (TextResponse) → Receive → [loop to AI Agent]
```

## Voice Fulfillment Flow Structure (Flow Designer)

**Single intent:**
```
VirtualAgentV2 (ENDED / Custom Event)
  → Parse (VirtualAgentV2.MetaData → http_input at $)
  → HTTP Request (POST with http_input body)
  → Condition (httpStatusCode == 200)
    → TRUE: SetVariable event_name = "<intent>_confirm_entry"
            → SetVariable event_data_string = "{{ event_data }}"
            → VirtualAgentV2 (resume via State Event)
    → FALSE: PlayMessage (TTS error) → QueueContact (escalate)
```

**Multiple intents (multi-event routing):**
```
VirtualAgentV2 (ENDED / Custom Event)
  → Parse (VirtualAgentV2.MetaData → http_input at $)
  → Case ({{VirtualAgentV2.StateEventName}})
    ├── "check_availability_exit"  → HTTPRequest (POST /check_availability)
    ├── "create_appointment_exit"  → HTTPRequest (POST /create_appointment)
    ├── "cancel_appointment_exit"  → HTTPRequest (POST /cancel_appointment)
    └── default                    → DisconnectContact
  → [each HTTP path]: Condition (status 200?)
    → TRUE: SetVariable event_name → SetVariable event_data_string → VirtualAgentV2 (resume)
    → FALSE: PlayMessage → QueueContact
```

**Key variables (declare as flow variables in Flow Designer):**

| Variable | Type | Purpose |
|---|---|---|
| `event_name` | STRING | State Event name to send back (e.g., `check_availability_confirm_entry`) |
| `event_data` | JSON | Parsed API response body |
| `event_data_string` | STRING | Stringified `event_data` — VAV2 `eventData` field requires STRING |
| `http_input` | STRING | Parsed from MetaData — the payload sent by the Custom Event |

**Event naming convention:** `<intent>_exit` (agent → flow) and `<intent>_confirm_entry` (flow → agent). Must match exactly between AI Agent Studio Custom Event config and Flow Designer Case/SetVariable activities.

> Full reference: `docs/reference/flow-designer-patterns.md` § Scripted Agent Fulfillment Pattern

## Key Variable Paths (Digital)

| Data | JSON Path (in SessionMetadata) |
|------|-------------------------------|
| Template key | `$.model_state.template_key` |
| Entity value | `$.model_state.entities.<entity_name>.value` |
| Intent name | `$.model_state.intent.name` |
| Previous intent | `$.previous_intent_model_state.intent.name` |

## Key Variable Syntax (Voice / Responses)

| Syntax | Source |
|--------|--------|
| `${entity.<name>}` | Collected slot value (in response templates) |
| `${eventStore.<name>}` | Data from state_update event |
| `${extra_params.<key>}` | Message parameters from flow |
| `${consumerData.extra_params.<key>}` | Custom Parameters (digital only) |

## Custom Event Payload (Voice)

```json
{
  "entity_name": "${entity.<entity_name>}",
  "another_entity": "${entity.<another_entity>}"
}
```

## state_update Payload (Voice)

**Return data to agent:**
```json
{
  "intent": "<intent_name>",
  "slots": {
    "result_field": "value_from_api"
  }
}
```

**Clear slot for re-prompting:**
```json
{
  "intent": "<intent_name>",
  "slots": {
    "slot_to_clear": ""
  }
}
```

<!-- SYNC: also update .claude/skills/build-action/reference.md (Standard Headers table) when changing this section -->
## Standard Headers (Supabase/PostgREST)

| Header | Value | When |
|--------|-------|------|
| `apikey` | `{anon_key}` | Always |
| `Authorization` | `Bearer {anon_key}` | Always (space before key required) |
| `Content-Type` | `application/json` | Always |
| `Accept` | `application/vnd.pgrst.object+json` | Single-object responses only |
| `Prefer` | `return=representation` | POST/PATCH only |

## Scripted vs Autonomous Fulfillment Comparison

| Aspect | Autonomous (`build-action`) | Scripted (`build-scripted-fulfillment`) |
|--------|---------------------------|----------------------------------------|
| Trigger | LLM calls action | Branch on template_key (digital) / Custom Event (voice) |
| Flow type | Standalone Connect flow | Inline in conversation flow (digital) / Flow Designer (voice) |
| Entry node | Start node (AI Agent trigger) | Data Parser → Branch (digital) / Custom Event path (voice) |
| Results return | Flow Outcomes → agent | Channel Reply directly to user (digital) / state_update → agent (voice) |
| Agent awareness | Agent sees results | Digital: agent is "blind". Voice: agent gets state_update |

## Gotchas

| Issue | Cause | Fix |
|-------|-------|-----|
| SessionMetadata is empty | Using an autonomous agent, or digital agent not configured as scripted | SessionMetadata is only available for scripted agents on digital channels |
| template_key not found | Response on the intent doesn't have a template key set | Set a template key on the intent's completion response in AI Agent Studio |
| Entity value is null/empty | Wrong JSON path in Data Parser | Verify path: `$.model_state.entities.<exact_entity_name>.value` |
| Fulfillment response not showing | Missing Append Conversation after Channel Reply | Add Append Conversation node between Channel Reply and Receive |
| Custom Event not triggering (voice) | Response type on Voice channel not set to Custom Event | In Response Designer, select Voice channel and add Custom Event type |
| state_update has no effect | Payload JSON format incorrect or variable names don't match | Verify intent name and slot names match exactly (case-sensitive) |
| HTTP request times out | API endpoint slow or unreachable from Connect | Test with curl first; check firewall rules for Connect's IP range |
| Flow loops without sending response | Channel Reply node not wired correctly after Evaluate | Verify wiring: HTTP → Evaluate → Channel Reply → Append → Receive |
