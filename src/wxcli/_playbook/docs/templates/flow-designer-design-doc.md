# [Flow Name] -- Design Document

Created: [YYYY-MM-DD]

## 1. Purpose

[What this flow does, what problem it solves, who calls in]

## 1b. Applicable Blueprints

> Reference: `docs/reference/flow-blueprints.md`

| Blueprint # | Blueprint Name | How It Applies |
|-------------|---------------|----------------|
| | | |

> If combining multiple blueprints, note how they compose: which blueprint provides the entry path, where they merge, and what customizations are needed. See "Combining Blueprints" in flow-blueprints.md.

## 2. Flow Metadata

| Field | Value |
|-------|-------|
| Flow Name | [descriptive name] |
| Flow Type | Inbound Voice / Subflow / Event Flow |
| Entry Point | [EP name in Control Hub] |
| PSTN Number | [number assigned to EP] |
| Business Hours Schedule | [schedule name, or "N/A"] |
| TTS Connector | Cisco Cloud TTS / Google TTS |
| Version Label | Dev / Live |

## 3. Variables

### Flow Variables

| Name | Type | Default | Agent Viewable | Desktop Label | Purpose |
|------|------|---------|---------------|---------------|---------|
| | STRING / INTEGER / BOOLEAN / JSON | | Yes / No | | |

### Global Variables Referenced

| Name | Type | Sensitive | Source |
|------|------|-----------|--------|
| | | Yes / No | [where the value comes from] |

### NewPhoneContact Outputs Used

| Variable | Purpose |
|----------|---------|
| `{{NewPhoneContact.ANI}}` | [e.g., caller identification] |
| `{{NewPhoneContact.DNIS}}` | [e.g., DNIS-based routing] |

## 4. Activities

List every activity in the flow in wiring order. Each row captures the key configuration fields — downstream skills and diagram generators parse this table.

| ID | Label | Activity Type | Key Configuration |
|----|-------|--------------|-------------------|
| 1 | NewPhoneContact | NewPhoneContact | (start — pre-placed, no config) |
| 2 | | Set Variable | Variable: `[name]` = `[value]` |
| 3 | | Business Hours | Schedule: `[name]` |
| 4 | | Menu | Prompt: "[TTS text]"; Options: 1=[label], 2=[label] |
| 5 | | Queue Contact | Queue: `[name]`; Priority: P[1-9]; Skills: [if any] |
| 6 | | Play Music | File: [name or "Default"]; Duration: [seconds] |
| 7 | | Disconnect Contact | (no config) |
| 8 | | Play Message | Audio: TTS; Text: "[message]"; Language: [lang] |
| 9 | | HTTP Request | URL: `[url]`; Method: [GET/POST]; Parse: [output_var] = [json_path] |
| 10 | | Condition | Expression: `{{[var]}} [op] [value]` |
| 11 | | Case | Variable: `{{[var]}}`; Branches: [value1]=[label], [value2]=[label] |
| 12 | | Callback | Dial Number: `{{NewContact.ANI}}`; Queue: [same/different] |
| 13 | | Bridged Transfer | Dial Number: `{{[var]}}`; Timeout: [seconds] |
| 14 | | Collect Digits | Min: [n]; Max: [n]; Timeout: [seconds] |
| 15 | | Parse | Input: `{{[source_var]}}`; Content Type: JSON; Output: [var] = [json_path] |
| 16 | | Functions | Function: [name]; Input: [var]=[flow_var]; Output: [var] = [$.jsonpath] |

> **Key Configuration** uses a condensed key-value format. For activities with many fields, list only the non-default values — the build skill reads the full field table from `docs/reference/`.

## 5. Connections

The directed graph of the flow. Every **non-error** activity exit path must appear as a row. This is the critical structure — it defines the complete wiring.

> **Port names must match the canonical names from `build-spec-diagram/reference.md` PORT_DEFINITIONS.** Common mappings: most activities use "Default" (not "Out") for their success path. Menu uses dynamic digit ports + "No-Input Timeout" + "Unmatched Entry". Condition uses "True" / "False".

> **Error ports are auto-handled.** Activities' Undefined Error / Error ports route to OnGlobalError automatically. Do NOT include Error port rows in this table — only include ports that carry intentional flow logic (Default, True/False, digit branches, etc.). The only exception is if the flow intentionally routes an Error port to a specific activity instead of OnGlobalError.

| Source Activity | Port | Target Activity |
|----------------|------|-----------------|
| NewPhoneContact | Out | [next activity label] |
| BusinessHours | Working Hours | [activity label] |
| BusinessHours | Holidays | [activity label] |
| BusinessHours | Default | [activity label] |
| Menu | 1 - [option label] | [activity label] |
| Menu | 2 - [option label] | [activity label] |
| Menu | No-Input Timeout | [activity label] |
| Menu | Unmatched Entry | [activity label] |
| QueueContact | Default | [activity label — typically Play Music for hold treatment] |
| Condition | True | [activity label] |
| Condition | False | [activity label] |
| Case | [value1] | [activity label] |
| Case | [value2] | [activity label] |
| Case | Default | [activity label] |
| HTTPRequest | Default | [activity label — branch on httpStatusCode downstream] |
| BridgedTransfer | Default | [activity label — branch on FailureCode downstream] |
| Callback | Default | [activity label — must wire to Disconnect Contact] |
| PlayMessage | Default | [activity label] |
| PlayMusic | Default | [activity label] |
| CollectDigits | Default | [activity label] |
| Functions | Default | [activity label] |

> Only include rows for activities actually in this flow. Delete example rows that don't apply.

## 6. Event Handlers

### OnGlobalError (mandatory)

| Activity | Configuration |
|----------|--------------|
| Play Message | TTS: "[error message text]" |
| Queue Contact | Queue: [fallback queue name] |
| Play Music | File: Default; Duration: 600 |
| Disconnect Contact | (terminal) |

**Wiring:** Play Message → Queue Contact → Play Music → Disconnect Contact

### Additional Event Handlers (if applicable)

| Event | Handler Chain | Purpose |
|-------|--------------|---------|
| AgentDisconnected | [activity chain] | [e.g., post-call survey] |
| PhoneContactEnded | [activity chain] | [e.g., cleanup] |
| CallbackFailed | [activity chain] | [e.g., retry callback] |

## 7. TTS Content

All text-to-speech prompts used in the flow, listed by activity label for easy review and localization.

| Activity Label | TTS Text | Language |
|----------------|----------|----------|
| | | English (United States) |

## 8. External Integrations (if applicable)

> Skip if the flow has no HTTP Request, HTTP Connector, or Custom Connector activities.

| Activity Label | API Endpoint | Method | Auth | Expected Response Shape |
|----------------|-------------|--------|------|------------------------|
| | | GET / POST | [Bearer token / Connector name / API key] | [brief description or sample JSON] |

### HTTP Headers (per integration)

| Activity Label | Header | Value |
|----------------|--------|-------|
| | | |

## 9. Business Hours (if applicable)

> Skip if the flow doesn't use Business Hours activity.

| Field | Value |
|-------|-------|
| Schedule Name | [name in Control Hub] |
| Working Hours | [e.g., Mon-Fri 8:00 AM - 6:00 PM ET] |
| Holidays | [list or "per Control Hub schedule"] |
| Overrides | [if any] |

### Routing by Time

| Path | Routes To |
|------|-----------|
| Working Hours | [activity label] |
| Holidays | [activity label] |
| Default (after hours) | [activity label] |
| Overrides | [activity label] |

## 10. Queue Configuration

| Queue Name | Team | Priority | Skill Requirements | Skill Relaxation |
|-----------|------|----------|-------------------|-----------------|
| | | P[1-9] | [skill conditions, or "N/A"] | [relaxation rules, or "N/A"] |

## 11. Error Handling Summary

| Error Source | Failure Mode | Routes To | Rationale |
|-------------|-------------|-----------|-----------|
| OnGlobalError | Unhandled exception | Play Message → Queue → Disconnect | Safe default |
| HTTPRequest | Non-200 or timeout | [activity label] | [why this path] |
| BridgedTransfer | No answer / busy | [activity label] | [why this path] |
| | | | |

## 12. Flow Diagram

ASCII art showing the complete flow with all paths. Use the same activity labels from the Activities table.

```
[NewPhoneContact]
    │
    ▼
[Activity Label] ── config summary
    │
    ├── Path 1 ──► [Activity Label]
    │                   │
    │                   ▼
    │              [Activity Label] → [Disconnect]
    │
    └── Path 2 ──► [Activity Label] → [Disconnect]

── OnGlobalError ──
PlayMessage → QueueContact → PlayMusic → Disconnect
```

## 13. Test Plan

| # | Scenario | Expected Result |
|---|----------|----------------|
| 1 | [happy path] | [what should happen] |
| 2 | [error path] | [what should happen] |
| 3 | [edge case] | [what should happen] |

## 14. Build Checklist

| # | Step | Status |
|---|------|--------|
| 1 | Create flow in Flow Designer | pending |
| 2 | Create flow variables | pending |
| 3 | Configure activities (per Section 4) | pending |
| 4 | Wire connections (per Section 5) | pending |
| 5 | Wire OnGlobalError (per Section 6) | pending |
| 6 | Wire additional event handlers | pending |
| 7 | Validate flow (toolbar) | pending |
| 8 | Publish (Dev label) | pending |
| 9 | Assign to Entry Point | pending |
| 10 | Test all scenarios (per Section 13) | pending |
| 11 | Publish (Live label) | pending |

### One-Time Setup (if not already done)

| # | Step | Status |
|---|------|--------|
| S1 | Site provisioned in Control Hub | pending |
| S2 | Team created | pending |
| S3 | Queue created with team assigned | pending |
| S4 | Entry Point created (Telephony) | pending |
| S5 | PSTN number assigned to Entry Point | pending |
| S6 | Global Variables created (if needed) | pending |
| S7 | Business Hours schedule created (if needed) | pending |
