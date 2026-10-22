---
name: configure-ai-agent
description: |
  Configure an AUTONOMOUS AI agent in Webex AI Agent Studio. Sets up the agent
  goal, welcome message, actions with slot entities, action descriptions with
  sample JSON, and agent instructions.
  Use for: configuring the AI Agent in Agent Studio AFTER the backing Connect
  action flows are built. Mid-pipeline skill — run build-action first, then
  this skill, then deploy.
  NOT for: SCRIPTED agents (configure-scripted-agent) or the Connect action flows (build-action).
allowed-tools: Read, Grep, Glob
argument-hint: [action-name]
---

# Configure AI Agent Workflow (Autonomous Only)

> **Scripted agents?** This skill is for autonomous agents. Scripted agents use a different architecture (intents/entities/responses instead of actions with LLM descriptions). Use `configure-scripted-agent` for scripted agent configuration.

## Step 1: Load references

YOU MUST use the Read tool on each of these files. Do not proceed to Step 2 until all reads are complete.

1. Read `docs/reference/ai-agent-studio.md` for Studio conventions
2. Read this skill's `reference.md` for the quick-reference cheat sheet
3. Read the current agent instructions (if they exist) so you can append the new action

**Checkpoint — do NOT proceed until you can answer these from the docs you just read:**
- What syntax is prohibited in action descriptions, and what must you use instead? (from `ai-agent-studio.md`)
- What is the correct CCAI Config dropdown value for an autonomous agent? (from `ai-agent-studio.md`)

If you cannot answer both, you skipped Step 1. Go back and read the docs.

## Step 2: Confirm prerequisites

Before configuring in AI Agent Studio, verify:

- The Webex Connect flow for this action is already built and tested
- You know the action name, input entities, and returned variables from the flow
- The Flow Outcomes key-value pairs are defined

## Step 3: Set Agent Goal — `[AI Agent Studio → Agent Goal field]`

The Agent Goal is a short, concise statement of the agent's overall function or purpose. It focuses on the end result or benefit for the caller.

**Do's:**
- Keep it short and concise
- Focus on the overall function or purpose
- Consider the end result or benefit for the user
- Use clear and concise language
- Ensure the goal aligns with the actions and capabilities of the agent

**Don'ts:**
- Don't include specific details like locations, dates, or user information
- Don't mention particular actions or implementation methods
- Don't use technical jargon or complex terminology
- Don't use overly long or complicated goal statements
- Don't include multiple unrelated goals in a single prompt
- Don't use ambiguous or vague language

**Format:**
```
Help [caller type] [what they get out of calling].
```

**Example:**
```
Help customers schedule appointments and check order status.
```

Set this when first creating the agent. Update it as new capabilities are added.

## Step 4: Set Welcome Message — `[AI Agent Studio → Welcome Message field]`

The Welcome Message is a **separate field** from the Instructions. It is the first thing the caller hears when they connect. Set it under the agent's configuration, not in the Instructions tab.

**Format:**
```
Thanks for calling [Organization]! I can help you with [capability list]. How can I help you today?
```

If the agent's first action is an automatic lookup (like verify_caller with ANI), append a natural transition:
```
Thanks for calling [Organization]! I can help you with [capability list]. One moment while I pull up your account.
```

## Step 5: Create the Action in AI Agent Studio — `[AI Agent Studio]`

1. Navigate to **Control Hub** > **Contact Center** > **AI Agents** > open your agent
2. Go to the **Actions** tab
3. Click **Add Action**
4. In the **Action Name** field, enter the action name in lowercase_underscores format (e.g., `lookup_customer`) — the LLM uses this name to identify when to call this action
5. Under **Connect Flow**, select the flow you just built in Webex Connect from the dropdown — **this is why the Connect flow must be built first; it won't appear here until it exists and is made live**
6. Configure remaining fields per following steps

## Step 6: Generate Action Name — `[AI Agent Studio → Action → Action Name field]`

Use `lowercase_underscores` format (e.g., `verify_caller`, `create_order`). The LLM uses this name to identify the action; the Connect flow is linked via the dropdown selector in Step 5.

## Step 7: Generate Action Description — `[AI Agent Studio → Action → Description field]`

Max 1024 characters. Must include (format and rules from `ai-agent-studio.md`):

```
Call this action when [trigger condition].
Requires: [entity_name] (collected from the caller).
Returns: "returned_var_1", "returned_var_2", "returned_var_3".
[How to use the returned data -- e.g., "Use 'first_name' to greet the caller by name."]
[Timezone note if times are returned: "All times are in UTC. Convert to Eastern Time (subtract 5 hours) before telling the caller."]
```

**Rules:**
- Reference returned variables in **quotes**: `"first_name"`, `"confirmation_number"` -- this works
- **NEVER** use `{{variable_name}}` syntax **to reference Flow Outcomes return data** -- it returns the literal string, not the value. Exception: `{{variable_name}}` DOES work for custom data variables passed from Flow Designer at session start (see `docs/reference/ai-agent-studio.md` "Custom Data at Session Start").
- Keep under 1024 chars

## Step 8: Generate Input Entities — `[AI Agent Studio → Action → Slot Entities section]`

Click **Add Entity** for each input. Fill in **Entity Name**, **Entity Type**, **Entity Description**, **Entity Example**, and toggle **Required** ON for mandatory fields.

| Entity Name | Entity Type | Entity Description | Entity Example | Required |
|-------------|-------------|-------------------|----------------|----------|
| phone_number | String | The caller's 10-digit phone number | 5551234567 | Yes |

**Rules:**
- Phone numbers = **String** type (NOT Number)
- Always set **Required** toggle ON for mandatory fields
- Entity Description is read by the LLM -- write it as a plain-language instruction
- Entity Name must match the key in the Configure AI Agent Event sample JSON

## Step 9: Register sample JSON in Start node — `[Webex Connect → Start node → Provide sample JSON]`

This is configured in **Webex Connect**, not AI Agent Studio. In the Connect flow, click the **Start** node, set the **Trigger category** to **AI Agent** (the event auto-populates as "Trigger from AI Agent to initiate flow"), then paste a sample payload into the **Provide sample JSON** field and click **Parse** to register the variables.

One key per input entity with realistic example values:

```json
{
  "phone_number": "5551234567",
  "preferred_date": "2026-03-15"
}
```

Keys must match entity names exactly.

## Step 10: REMIND USER — Enable the action — `[AI Agent Studio → Action → Enable toggle]`

**This is the single most common reason actions fail to fire.**

After saving, locate the **Enable toggle** on the action row and switch it **ON**. If the toggle is OFF, the action silently does not execute -- no error, no log, nothing.

Say this explicitly every time:

> "After saving, make sure the action's Enable toggle is switched ON. This is the most commonly missed step."

## Step 11: Generate updated agent instructions — `[AI Agent Studio → Instructions tab]`

Navigate back to the agent's main **Instructions** tab (separate from the Actions tab). Replace the existing instructions with the updated version.

Use markdown headings and lists in the instructions. Follow this template structure:

### 1. Identity

- **Role Definition**: Define the persona and expertise. "You are [Name/Role], a [description] for [Organization]."
- **Tone and Demeanor**: Specify friendly, formal, or casual. Match the organization's brand voice.

### 2. Context

- **Background Information**: Relevant details the agent should consider (e.g., "This is a customer support line for scheduling and account inquiries").
- **Environment Details**: System constraints (e.g., "The caller is on voice and may have background noise which impacts transcription quality").

### 3. Task

Break down the overall task into specific, sequential steps. Reference the actions at each step.

- **Step 1**: What happens first (e.g., identity verification)
- **Step 2**: What the agent can do next (e.g., look up records, create entries)
- **Step N**: Additional capabilities

For each step, specify:
- When to call the action
- What it returns (use quoted variable names where applicable like `"first_name"`, `"last_name"`)
- How to use the returned data conversationally
- Use forceful language for required actions: "You MUST call [action_name] before anything else. No exceptions."
- Weak phrasing ("you should", "try to") gets ignored intermittently by the LLM.

**Timezone note**: If any action returns timestamps in UTC, add explicit conversion instructions: "All times from the database are in UTC. You MUST convert to [Local Timezone] (subtract/add N hours) before saying any time to the caller. Never mention UTC."

### 4. Response Guidelines

- **Formatting Rules**: For voice: keep responses to one or two sentences at a time. Do not stack multiple questions. For digital: bullet lists for options, clear numbering for steps.
- **Language Style**: Natural filler ("Let me check on that", "One moment"). Confirm before committing -- read back details and wait for "yes". Wrap up: "Anything else I can help with?" Sign off warm: "Thanks for calling, [Name]. Have a great day!"

### 5. Error Handling and Fallbacks

- **Clarification Prompts**: "I didn't catch that, could you please repeat?" or "Could you double-check [input] and try again?"
- **Default Responses**: "I'm sorry, I didn't understand. Can you try rephrasing?"
- **Action Failures**: "I'm having trouble looking that up. Let me transfer you to someone who can help." Then escalate.

### 6. Guardrails

Instruct the agent to respond only in the context of the goal. Include domain-specific restrictions:
- What the agent must NOT do (give unauthorized advice, make commitments, share internal IDs, etc.)
- Topics that should trigger escalation rather than a response

### 7. Examples (Optional)

Add a sample conversation between the caller and the agent to improve prompt adherence. Most useful for complex or nuanced flows.

## Step 12: Present all config to user

Format everything for direct copy-paste into AI Agent Studio:

1. Agent Goal (full text, ready to paste)
2. Welcome Message (full text, ready to paste)
3. Action Name
4. Action Description (full text, ready to paste)
5. Input Entities table
6. Configure AI Agent Event sample JSON
7. Enable toggle reminder
8. Updated agent instructions (full text, ready to paste into Instructions tab)

## Step 13: (Optional) Generate import-ready agent JSON — accelerator

If the user wants to bootstrap the whole agent in one import instead of building it field-by-field in the Studio UI, generate an import JSON. This is **autonomous agents only** (`bot_type: virtualagent`) — never generate a scripted-agent (`mlbot`) import file from this skill.

**Before generating, YOU MUST read `docs/reference/ai-agent-studio-import-json.md`** — it is the authoritative, verified schema. Do not author the JSON from memory.

Procedure:

1. Read `docs/reference/ai-agent-studio-import-json.md` (schema + gotchas) and `docs/templates/ai-agent-studio-import-template.json` (skeleton).
2. Copy the template and fill it from the design:
   - `configuration.llm_agent_description` = agent goal, then a blank line, then the literal `### INSTRUCTIONS:` separator, then the instructions from Step 11.
   - `configuration.welcome_message` = the Welcome Message from Step 4.
   - `configuration.timezone` = a **real IANA timezone** (never a placeholder — validated on import).
   - `configuration.kb_ids` = `[]` (never populate).
   - For voice agents, leave the specific voice in `voice_settings.voices` as a placeholder; for digital-only, use `[]`.
   - One `tools[]` entry per action (`slot_filling_with_fulfillment`), plus the `Agent handover` system tool by default.
   - Each action's `input_entities.parameters.properties` = the Input Entities from Step 8; list required ones in `required`, and map each entity's **Entity Example** value into that property's `examples` array. For a fixed-choice parameter, use `"type": "custom_list"` with an `"enum": [...]` of allowed values instead of `"type": "string"`.
   - Leave every Connect-backend field as an **empty string**: `flow_id: ""`, `flow_name: ""`, `service_id: ""`, `service_name: ""`, `webhook_url: ""` (the verified unbuilt-flow convention — see the reference).
   - Give every tool a unique 32-character lowercase hex `id`.
3. Enforce the import-validation gotchas from the reference: instructions under 5000 characters, maximum 10 action tools (split into multiple agents if exceeded), and `tools[].name` matching the action names in the instructions verbatim.
4. Present the completed JSON to the user in a fenced ` ```json ` code block, ready to save. The saved file itself must be valid JSON with **no comments and no code fences**. Recommend the filename `docs/plans/<agent-name>-ai-agent-studio-import.json`. This skill's own toolset is read-only (it produces copy-paste output like every other step); if the orchestrating agent has Write access it may also save the file to that path, but you must show the JSON to the user either way.
5. State plainly that this is a **draft skeleton**: the user must build the Webex Connect flows and fill the empty `flow_id` / `flow_name` / `service_id` / `service_name` / `webhook_url` fields (and choose a voice) before the imported agent is functional beyond a demo import.

Never invent real Webex Connect service IDs, flow IDs, webhook URLs, or knowledge-base IDs — leave them as empty strings per the reference.

---

## CRITICAL REMINDERS

- **NEVER invent action description syntax.** The `{{variable_name}}` vs quoted `"variable_name"` distinction is documented in `ai-agent-studio.md` — follow it exactly.
- **NEVER skip the Enable toggle reminder** — it is the #1 cause of actions failing to fire.
- **Entity Name must match the sample JSON key** — a mismatch means the entity value never reaches the Connect flow.
- **Action description max 1024 characters** — exceeding this silently truncates.
- **Instructions are markdown** — use headings, lists, and bold for structure. Plain prose gets ignored by the LLM.

## ANTI-HALLUCINATION GUARD

Every field name, UI location, configuration detail, and syntax rule in your output MUST appear verbatim in the docs you loaded in Step 1 — and, for import-JSON output, in `docs/reference/ai-agent-studio-import-json.md` loaded in Step 13. If you are about to write something you did not read in the docs:

1. STOP and say "I don't have that documented — would you like me to do a web search to find the correct answer?"
2. Wait for the user's response before proceeding.
3. If they approve, use the WebSearch tool to find the answer from official Cisco/Webex documentation.
4. Present what you found and mark it as `[FROM WEB SEARCH — not yet in project docs]` so the user knows it hasn't been verified against the local reference.
5. Do NOT mix web search results into your output without that label.

Do not invent plausible-sounding platform details under any circumstances.
