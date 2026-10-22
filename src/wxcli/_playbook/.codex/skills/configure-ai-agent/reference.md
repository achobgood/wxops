# AI Agent Studio -- Quick Reference

## Agent Goal

Short, concise statement of the agent's overall purpose. Focuses on the end result for the caller.

**Do:** Keep it short, clear, aligned with capabilities. Focus on benefit to the caller.
**Don't:** Include specific details, action names, technical jargon, or multiple unrelated goals.

## Slot Entity Fields

| Field | Notes |
|-------|-------|
| Entity Type | `String` for most values (including phone numbers); `Date` for dates; `Number` for quantities |
| Entity Name | Lowercase underscores: `phone_number`, `preferred_date` |
| Entity Description | Plain language -- tells the LLM what to ask the caller |
| Entity Example | Format hint for the LLM (e.g., `5551234567`, `2026-03-15`) |
| Required | Toggle ON for mandatory fields |

**Phone number = String** (not Number). Using Number breaks leading zeros and formatting.

## Action Description Rules

- Max **1024 characters**
- Reference returned variables in **quotes**: `"first_name"`, `"confirmation_number"` -- WORKS
- **NEVER** use `{{variable_name}}` for Flow Outcomes return data -- returns the literal string. Exception: `{{variable_name}}` works for custom data variables from Flow Designer State Event (see `docs/reference/ai-agent-studio.md` "Custom Data at Session Start").
- Include: when to call, what it needs, what it returns, how to use the data

## Action Name

Use `lowercase_underscores` format. The LLM uses this name to identify the action; the Connect flow is linked via the flow selector dropdown in AI Agent Studio.

## Enable Toggle

Actions must be **ENABLED** (toggle ON) to fire. If OFF, the action silently does not execute. **Most common oversight.**

## Output Variables

AI Agent Studio has **no output variables section**. Outputs come from Flow Outcomes in the Connect flow. Reference those keys in the action description with quotes.

## Welcome Message

Separate field from Instructions. First thing the caller hears. Set under agent configuration, not the Instructions tab.

## Agent Instructions Template

Use markdown headings and lists. Follow this structure:

1. **Identity** — Role definition, tone and demeanor
2. **Context** — Background info, environment details (voice = background noise caveat)
3. **Task** — Sequential steps referencing actions. Forceful language for required actions ("You MUST call...")
4. **Response Guidelines** — Voice: 1-2 sentences, no stacked questions. Digital: bullet lists, numbered steps
5. **Error Handling and Fallbacks** — Clarification prompts, default responses, action failure handling
6. **Guardrails** — Stay in scope, domain-specific restrictions
7. **Examples** (optional) — Sample conversation for complex flows

| Pattern | Example |
|---------|---------|
| Forceful required action | "You MUST call verify_caller before anything else. No exceptions." |
| Timezone conversion | "All times are UTC. Convert to Eastern (subtract 5 hours). Never mention UTC." |
| Clarification prompt | "I didn't catch that, could you please repeat?" |
| Action failure | "I'm having trouble looking that up. Let me transfer you to someone who can help." |
| Conversation pacing | One to two sentences at a time. Don't stack questions. |

## Testing

| Mode | Reliability | Notes |
|------|-------------|-------|
| Chat Preview | Non-deterministic | LLM may skip actions; add forceful language before assuming config issue |
| Voice Preview | More reliable | Test via WxCC Flow Designer — Virtual Agent V2 activity with its **Contact Center AI Config** dropdown set to "Webex AI Agent Autonomous" |

## CCAI Config (Linking Agent to WxCC)

**There is no Control Hub creation step for a Webex AI Agent.** CCAI (Contact Center AI) is Google's product; Webex AI Agent is Cisco's own. The Control Hub flow *Services > Contact Center > Tenant settings > Integrations > Features > New > Contact Center AI Config* exists for **Google CCAI / BYOVA / Agent Answers** — its stated prerequisite is "Ensure that the service-specific integration connector is created. For example, **Google** Contact Center AI connector", and its Contact Center AI Connector field offers only "Webex CCAI", "Integration Connector", and "Service App" ([Cisco npbt02j](https://help.webex.com/en-us/article/npbt02j/Create-a-Contact-Center-AI-configuration)). For a Webex AI Agent, Cisco says only: "Select **Webex AI Agent Autonomous** from the **Contact Center AI Config** drop-down list" ([Cisco s0qro1](https://help.webex.com/en-us/article/s0qro1/)). Settled with the platform owner 2026-07-27.

**Voice deploy sequence:**

1. AI Agent Studio > **Publish** the agent
2. WxCC Flow Designer > open the **Virtual Agent V2** activity
3. In its **Contact Center AI Config** dropdown, select **"Webex AI Agent Autonomous"**
4. Select your published agent

**Digital channels:** unchanged — no CCAI Config involved; the agent is selected directly in the Webex Connect flow's AI Agent node.

A one-time tenant enablement is required before those dropdown entries appear (platform owner, 2026-07-27) — see [`wxcc-platform.md` § Webex AI Agent Tenant Prerequisite].

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Action never fires | Enable toggle OFF | Turn it ON |
| Action never fires (toggle ON) | Action not bound to a Webex Connect Service + Flow, or the flow isn't live | Select a Webex Connect **Service**, then select the **Flow** from the dropdown (both manual; names need not match); publish the Connect flow ([Cisco](https://help.webexconnect.io/docs/configure-fulfilment-flows-for-ai-agent-actions)) |
| Agent skips required action | LLM non-determinism | "You MUST call..." language |
| Variables as literal strings | Using `{{var}}` syntax | Use quoted names: `"var"` |
| Agent gives wrong time | No timezone note | Add UTC conversion instruction |
| Chat preview unreliable | Expected LLM behavior | Use voice preview instead |
| No greeting | Welcome Message empty | Set Welcome Message field |
| Agent not in CCAI dropdown | Not deployed | Click Deploy first |
| Flow data doesn't reach agent | Notify AI Agent not selected as the notification target | Open Flow Settings → Flow Outcomes → the **Last Execution Status** row, enable **Notify**, and confirm **Notify AI Agent** is selected. **UNVERIFIED** whether it is pre-selected by default or an explicit click under a **Notification Settings** heading — Cisco documents it as enabled by default for the AI Agent start node, the platform owner describes selecting it explicitly, and the two have not been reconciled. Check the tenant UI and confirm it is selected either way (open item **O2** in `docs/plans/2026-07-25-documentation-remediation-backlog.md` §6) |
