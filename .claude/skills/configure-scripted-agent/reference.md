# Scripted AI Agent Studio — Quick Reference

## AI Engines

Scripted agents support **two** engines. Names below are verbatim from [Understand AI engines for AI agents](https://help.webex.com/en-us/article/ne6s80cb/Understand-AI-engines-for-AI-agents) (Cisco page last updated July 16, 2026; verified 2026-07-27).

| Engine | Best For | Notes |
|--------|----------|-------|
| **Webex AI Pro 2.0 (with Swiftmatch)** | Intents with 10 or more utterances | Cisco: "Each intent must include at least 10 representative utterances." Requires intent descriptions |
| **Webex AI Pro 1.0 (with Swiftmatch)** | "fewer than 10 utterances per intent"; multilingual agents | Same page, Cisco's stated selection criteria |

Autonomous agents use a different set — "Webex AI Pro 1.0", "Webex AI Pro-US 1.0", "Webex AI Pro-Europe 1.0" — which are **not** selectable for scripted agents.

**"MindMeld" and "Rasa" are not AI Agent Studio engine names.** Those are Webex Connect Bot Builder terminology (`help.webexconnect.io/docs/nlu-engine`) — a different product. Neither name appears on Cisco's AI engines page.

## Entity Types

Cisco documents **six** custom entity types. Type names below are verbatim from [Understand intents, entities, and responses](https://help.webex.com/en-us/article/sz02k8/Understand-intents,-entities,-and-responses-in-AI-Agent-Studio) (Cisco page last updated July 16, 2026; verified 2026-07-27).

| Type | Use For | Notes |
|------|---------|-------|
| Custom list | Finite set of values not covered by prebuilt entities | Add all values with synonyms |
| Regex | Pattern-based input | e.g., `[A-Z]{3}\d{6}` for confirmation codes |
| Digits | Fixed-length numeric input, especially in voice interactions | Set expected length |
| Alphanumeric | Combinations of letters and numbers | Works for both voice and nonvoice inputs |
| Free form | Flexible data points that are difficult to define or validate | No validation applied |
| Map location (WhatsApp) | Location data shared on the WhatsApp channel | WhatsApp channel only |

Eleven prebuilt (system) entities also exist — see `docs/reference/ai-agent-studio-scripted.md` § System Entities (Prebuilt) for the full list.

**Entity type cannot be changed after creation.** Delete and recreate if wrong.

## Response Variable Syntax

| Syntax | Source | Example |
|--------|--------|---------|
| `${entity.name}` | Collected slot values | `${entity.appointment_date}` |
| `${extra_params.name}` | Flow message parameters | `${extra_params.customer_name}` |
| `${eventStore.name}` | Custom Event data (voice) | `${eventStore.confirmation_number}` |

## Intent Configuration Checklist

| Field | Required? | Notes |
|-------|-----------|-------|
| Intent Name | Yes | e.g., `book_appointment` |
| Description | Yes (Pro 2.0) | Helps NLU distinguish similar intents |
| Utterances | Yes (3 min, 10+ recommended) | Use Generate variants for more |
| Slots | If entities needed | Link entity, set Required, Retries, Response |
| Entry Contexts | If chained | Context values required for intent to match |
| Exit Contexts | If chained | Context values activated when intent matches; set Duration (turns) |
| Reset slots | Optional | Toggle ON to clear slot values after completion |
| End conversation | Optional | Toggle ON for terminal intents |

## Context Flow

- **Entry context**: Intent only matches when this context is active
- **Exit context**: Intent activates this context when matched
- **Duration**: Number of conversational turns the context stays active
- Chain intents by setting one intent's exit context as another's entry context

## System Responses

| Response | Default | Customize? |
|----------|---------|-----------|
| Welcome message | Generic greeting | Yes — set from design doc |
| Fallback message | "I didn't understand" | Yes |
| Partial message | "Did you mean..." | Yes |
| Agent handover | "Connecting you..." | Yes |

## AI Engine Tuning

| Setting | Default | When to Change |
|---------|---------|---------------|
| Fallback threshold | Platform default | Lower if fallback fires too often |
| Partial match threshold | Platform default | Adjust based on testing |
| Spellcheck in inference | OFF | Turn ON for text channels |
| Expand contractions | OFF | Turn ON (handles "don't" → "do not") |
| Prioritize slot filling | OFF | Turn ON if entity extraction > intent switching |

## CCAI Config (Linking Agent to WxCC)

**There is no Control Hub creation step for a Webex AI Agent.** CCAI (Contact Center AI) is Google's product; Webex AI Agent is Cisco's own. The Control Hub flow *Services > Contact Center > Tenant settings > Integrations > Features > New > Contact Center AI Config* exists for **Google CCAI / BYOVA / Agent Answers** — its stated prerequisite is "Ensure that the service-specific integration connector is created. For example, **Google** Contact Center AI connector", and its Contact Center AI Connector field offers only "Webex CCAI", "Integration Connector", and "Service App" ([Cisco npbt02j](https://help.webex.com/en-us/article/npbt02j/Create-a-Contact-Center-AI-configuration)). For a Webex AI Agent, Cisco says only: "Select **Webex AI Agent Scripted** from the **Contact Center AI Config** drop-down list" ([Cisco s0qro1](https://help.webex.com/en-us/article/s0qro1/)). Settled with the platform owner 2026-07-27.

**Voice deploy sequence:**

1. AI Agent Studio > **Publish** the agent
2. WxCC Flow Designer > open the **Virtual Agent V2** activity
3. In its **Contact Center AI Config** dropdown, select **"Webex AI Agent Scripted"**
4. Select your published agent

**Digital channels:** unchanged — no CCAI Config involved; the agent is selected directly in the Webex Connect flow's AI Agent node.

A one-time tenant enablement is required before those dropdown entries appear (platform owner, 2026-07-27) — see [`wxcc-platform.md` § Webex AI Agent Tenant Prerequisite].

## Channel Wiring

| Channel | Platform | Node | Agent Type Setting |
|---------|----------|------|-------------------|
| Voice | Flow Designer | Virtual Agent V2 | "Webex AI Agent Scripted" |
| Digital | Webex Connect | AI Agent | Agent Type: Scripted, Method: Process Message |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Intent not matching | Too few utterances | Add 10+ utterances; use Generate variants |
| Similar intents confused | Missing intent descriptions (Pro 2.0) | Add clear, unique descriptions |
| Entity type wrong | Type locked after creation | Delete and recreate entity |
| Slot not collected | Entity not linked as Required slot | Click +Link, toggle Required ON |
| Context chain breaks | Exit context duration too short | Increase duration (number of turns) |
| Custom Event not firing (voice) | Response type not Custom Event on Voice | Add Custom Event response for Voice channel |
| template_key not found (digital) | Response missing template key | Set template key in Response Designer |
| Agent not in CCAI dropdown | Not published | Click Publish first |
