# Flow Designer — Quick Reference

## Flow Structure Patterns

### Standard IVR

```
NewPhoneContact → Business Hours
  ├── Working Hours → Menu ("Press 1 for Sales, 2 for Support")
  │     ├── 1 → Queue Contact (Sales) → Play Music → Disconnect
  │     ├── 2 → Queue Contact (Support) → Play Music → Disconnect
  │     └── No-Input / Unmatched → Play Message ("Invalid") → loop to Menu
  ├── Holidays → Play Message ("Closed for holiday") → Disconnect
  └── Default → Play Message ("Hours are...") → Disconnect
OnGlobalError → Play Message → Queue Contact (fallback) → Play Music → Disconnect
```

### IVR with Callback Option

```
NewPhoneContact → Business Hours → Menu
  → Queue Contact → Get Queue Info
  → Condition: EWT > 120000 (ms)?
    ├── TRUE → Play Message ("Press 1 for callback") → Collect Digits
    │     ├── 1 → Callback ({{NewContact.ANI}}) → Disconnect
    │     └── other → Play Music (continue holding)
    └── FALSE → Play Music (hold)
CallbackFailed (Event Flow) → Wait (60s) → Callback → End Flow
```

### DNIS-Based Routing

```
NewPhoneContact → Case ({{NewContact.DNIS}})
  ├── +18005551111 → Queue Contact (Sales)
  ├── +18005552222 → Queue Contact (Support)
  ├── +18005553333 → Queue Contact (Billing)
  └── Default → Queue Contact (General)
  → Play Music → Disconnect
```

Or use Functions Activity for large DNIS maps (>5 routes).

### Queue Treatment Loop

```
Queue Contact → Play Music (30s)
  → Get Queue Info → Play Message ("Position {{PIQ}}, wait {{EWT}}")
  → Condition: EWT > threshold?
    ├── TRUE → Escalate Call Distribution Group → loop to Play Music
    └── FALSE → Play Music (30s) → loop to Get Queue Info
```

### Post-Call Survey

```
AgentDisconnected (Event Flow)
  → Play Message ("Please rate your experience 1-5")
  → Feedback V2
  → Disconnect Contact
```

### Data Dip + Route

```
NewPhoneContact → Set Variable (trim ANI)
  → HTTP Request (customer lookup)
  → Parse (extract tier)
  → Case ({{customerTier}})
    ├── "platinum" → Queue Contact (VIP, priority P1)
    ├── "gold" → Queue Contact (Priority)
    └── Default → Queue Contact (General)
  → Play Music → Disconnect
```

## Variable Syntax (Pebble Templates)

| Operation | Syntax |
|-----------|--------|
| Reference variable | `{{variableName}}` |
| Activity output | `{{ActivityLabel.OutputVar}}` |
| NewContact ANI | `{{NewContact.ANI}}` |
| NewContact DNIS | `{{NewContact.DNIS}}` |
| Comparison (inside Condition) | `{{variable > 0}}` |
| String equality | `{{variable == "value"}}` |
| Strip first char | `{{ variable \| slice(1) }}` |
| Replace | `{{ variable \| replace({"+":""}) }}` |
| Current epoch (ms) | `{{ now() \| epoch(inMillis=true) }}` |
| Split + join | `{{ variable \| split("") \| join(", ") }}` |

## Activity Wiring Rules

| Rule | Why |
|------|-----|
| Queue Contact THEN Play Music | Queue places the contact; Play Music fills the wait |
| Play Message THEN HTTP Request | Fills silence during API call ("Please wait...") |
| Business Hours FIRST | Route closed/holiday callers before any IVR logic |
| OnGlobalError always wired | Without it, errors silently drop calls |
| Disconnect Contact at every exit | End Flow doesn't hang up — only Disconnect does |
| End Flow in event flows only | AgentDisconnected, PhoneContactEnded, CallbackFailed |
| No VAV2 after Queue Contact | Unsupported configuration |
| No VAV2 in Event Flow canvas | Unsupported configuration |

## TTS Configuration (Cisco Cloud TTS)

| Field | Default | Notes |
|-------|---------|-------|
| Connector | Cisco Cloud TTS | Or Google TTS if configured |
| Speaking Rate | 1.0 wpm | Range: 0.25–4.0 |
| Volume Gain | 0.0 dB | Range: -96.0–16.0 |
| Character limit | None (Cisco) | No char limit for Cisco TTS |

Use `{{variable}}` in TTS text for dynamic values. Use single quotes inside Pebble expressions.

## Queue Contact — Key Config

| Field | Notes |
|-------|-------|
| Static Queue | Dropdown — pick one |
| Variable Queue | STRING var resolving to queue ID. Requires Fallback Queue. Does NOT support skill-based routing. |
| Contact Priority | P1 (highest) to P9. Values outside 1–9 default to P10. |
| Skill Requirements | Only with skill-based routing queues. Condition: IS, IS NOT, >=, <= |
| Skill Relaxation | Progressive loosening after wait threshold (seconds) |
| Check Agent Availability | Toggle — checks before queueing |

## Business Hours Outputs

| Path | Precedence | Fires When |
|------|-----------|------------|
| Overrides | Highest | Matches a schedule override |
| Holidays | High | Current date is a holiday |
| Working Hours | Normal | Within configured shift |
| Default | Lowest | None of the above |

## Callback Activity — Key Config

| Field | Value |
|-------|-------|
| Callback Dial Number | `{{NewContact.ANI}}` (default) |
| Callback Queue | Same queue or different (toggle) |
| Max retries | 10 (system limit) |
| Min Wait between retries | 10 seconds |
| Max Wait between retries | 72 hours |
| Max interaction lifetime | 14 days |

**Must use Disconnect Contact after Callback.** Otherwise the call doesn't end.

## Self-Loop Limits (Key Activities)

| Activity | Limit |
|----------|-------|
| Queue Contact | 100 |
| Menu | 100 |
| Collect Digits | 100 |
| Callback | 10 |
| Blind Transfer | 10 |
| Bridged Transfer | 75 |
| Virtual Agent V2 | 20 |
| Escalate CDG | 750 |

## Gotchas

| Issue | Cause | Fix |
|-------|-------|-----|
| Call silently drops on error | OnGlobalError not wired | Wire it to Play Message + Queue + Disconnect |
| HTTP Request fails after Queue | Timing issue | Add Play Message or Play Music buffer between them |
| Play Music loops forever | No downstream activity | Always wire an exit after Play Music |
| Condition `== ""` won't validate | Empty string comparison unsupported | Use numeric check (e.g., `{{count > 0}}`) instead |
| `replace("+","")` fails | Wrong syntax — 2 args not supported | Use map form: `{{ var \| replace({"+":""}) }}` |
| Global Variable changes not reflected | 8-hour cache on metadata changes | Wait for cache expiry or republish flow |
| Variable Queue ignores skills | By design — reverts to Longest Available Agent | Use Static Queue for skill-based routing |
| JSON variable limit hit | Max 5 JSON vars per flow, 16KB each | Use String + Parse for additional JSON |
| Priority value ignored | Value outside 1–9 defaults to P10 | Ensure INTEGER 1–9 |
| Caller hears dead air after transfer | No comfort message before transfer | Add Play Message before Blind/Bridged Transfer |
| EWT returns -1 | Insufficient data or skill-based queue | Handle as "unknown wait time" in TTS |
| Callback not retried | No CallbackFailed event handler | Wire CallbackFailed with Wait + re-queue |
| End Flow used in main flow | Causes dead air — call doesn't disconnect | Use Disconnect Contact instead |

## Activity Finder

When a user's need doesn't map to a standard pattern above, use this table to identify the right activity.

**Lookup method:** Read the activity file directly from `docs/reference/flow-designer-activities/<filename>`.

| Activity | Use When | File |
|----------|----------|------|
| Recording Control | Pause recording for PCI compliance (credit card input) | recording-control.md |
| Start Media Stream | Stream real-time audio to configured media destination (live transcription, AI Assistant) | start-media-stream.md |
| Set Whisper | Play announcement to AGENT only before connect (queue/intent context) | set-whisper.md |
| Set Announcement | Play announcement to CALLER when agent answers ("call is recorded") | set-announcement.md |
| Send Digits | DTMF outpulse after bridged transfer (navigate external IVR) | send-digits.md |
| Call Progress Analysis | Detect voicemail/answering machine on outbound campaigns | call-progress-analysis.md |
| Upload Audio | Upload audio file dynamically during flow execution | upload-audio.md |
| Screen Pop | Push URL to agent desktop (CRM deep link with variables) | screen-pop.md |
| Blind Transfer | Transfer OUT permanently — call leaves WxCC | blind-transfer.md |
| Bridged Transfer | Transfer to external DN but keep control — returns on failure | bridged-transfer.md |
| Queue To Agent | Route to specific agent by ID (VIP or callback-to-same-agent) | queue-to-agent.md |
| Get Queue Info | Check PIQ/EWT before deciding to queue or offer callback | get-queue-info.md |
| Advanced Queue Information | Like Get Queue Info but works mid-queue, CDG-aware | advanced-queue-information.md |
| Escalate CDG | Move to next Call Distribution Group when current has no agents | escalate-cdg.md |
| Set Contact Priority | Change priority P1-P9 for already-queued contacts | set-contact-priority.md |
| Schedule Callback | Future callback at scheduled time (not immediate Callback) | schedule-callback.md |
| Virtual Agent V2 | Invoke Webex AI Agent for NLU/conversation handling | virtual-agent-v2.md |
| Virtual Agent | LEGACY Dialogflow ES only — deprecated, use VAV2 instead | virtual-agent-legacy.md |
| HTTP Connector | Call WxCC's own APIs with managed auth (no token handling) | http-connector.md |
| Custom Connectors | Call external APIs with managed OAuth (configured in Control Hub) | custom-connectors.md; playbook: custom-connectors-setup.md |
| Functions Activity | Run JavaScript/Python in-flow (5s limit, data transformation only) | functions-activity.md; playbook: functions-setup.md |
| HTTP Request | Call external APIs with manual headers (GET/POST/PUT/DELETE) | http-request.md |
| Parse | Extract fields from JSON via JSONPath (after HTTP Request) | parse.md |
| BRE Request | Lookup Business Rules Engine (built-in key-value, no external API) | bre-request.md |
| Menu | Single-digit choice 0-9 ("Press 1 for Sales") | menu.md |
| Collect Digits | Multi-digit input (account number, ZIP, PIN) | collect-digits.md |
| Record | Record caller's voice (voicemail, dictation) | record.md |
| Feedback V2 | Post-call CSAT survey with inline questions | feedback-v2.md |
| Case | Multi-way branch on variable value (switch, up to 20 branches) | case.md |
| GoTo | Jump to another flow or re-enter current (flow chaining) | goto.md |
| Wait | Pause between retries (10s–72h range) | wait.md |
| Condition | Simple if/else on boolean expression | condition.md |
| End Flow | End without disconnecting — event flows only, NOT main flow | end-flow.md |
| Percentage Allocation | A/B test routing — split traffic by percentage | percentage-allocation.md |
| Outdial Entry Point | Outbound campaign flows — entry for dialer-initiated calls | outdial-entry-point.md |
| Play Message | Play TTS or audio prompt to caller | essentials |
| Play Music | Hold music / comfort noise while waiting | essentials |
| Queue Contact | Route contact to queue (skill-based or longest-available) | essentials |
| Set Variable | Assign or transform a variable value | essentials |
| Disconnect Contact | Hang up the call — required at every exit path | essentials |
| Business Hours | Route by schedule (working hours, holidays, overrides) | business-hours.md |
| Callback | Immediate callback — caller hangs up, system calls back | callback.md |
| Receive Message | Wait for a customer message on a BYOC custom messaging channel (beta; Cisco docs gated) | receive-message.md |
| Send Custom Message | Send a message on a BYOC custom messaging channel (beta; Cisco docs gated) | send-custom-message.md |
| Cryptographic Hash | Hash a string (SHA256/SHA512, optional salt) for payload integrity in API calls | cryptographic-hash.md |
| Generate OTP | Generate a one-time password for 2FA/MFA caller authentication | generate-otp.md |
| Verify OTP | Validate the caller-entered OTP against Generate OTP's transaction reference | verify-otp.md |
