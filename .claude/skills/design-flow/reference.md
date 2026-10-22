# Design Flow — Quick Reference

## Blueprint Selection Guide

Match user requirements to one or more blueprints from `docs/reference/flow-blueprints.md`.

| Requirement | Blueprint # | Blueprint Name | Key Activities |
|-------------|-------------|---------------|----------------|
| Caller dials in, menu routes to queues | 1 | Simple IVR | Menu, Queue Contact, Play Music, Disconnect |
| Route by dialed number (DNIS) | 2 | DNIS-Based Routing | Case or Functions, Queue Contact |
| Open/closed/holiday routing | 3 | Business Hours Routing | Business Hours, Play Message, Menu |
| Hold music with position announcements | 4 | Queue with Hold Treatment | Queue Contact, Play Music, Get Queue Info, Play Message |
| Offer callback when EWT is high | 5 | Callback Offer | Get Queue Info, Condition, Collect Digits, Callback |
| Check if caller is known via CJDS | 6 | Caller Verification (CJDS) | HTTP Request, Condition, Set Variable |
| Multilingual (language selection at start) | 7 | Language Selection | Menu, Set Variable (Global_Language) |
| Post-call CSAT/NPS survey | 8 | Post-Call Survey | Feedback V2 (in AgentDisconnected event flow) |
| Route by agent skills with relaxation | 9 | Skill-Based Routing | Set Variable, Queue Contact (skill config) |
| Try primary DN, fail over to secondary | 10 | Sequential Transfer (Failover) | Bridged Transfer, Condition |
| Autonomous AI agent handles call | 11 | AI Agent (Autonomous Voice) | Virtual Agent V2, Queue Contact |
| Scripted AI agent with fulfillment | 12 | AI Agent (Scripted Voice) | Virtual Agent V2, Parse, Case, HTTP Request, Set Variable |
| Multilingual with shared menu structure | 13 | Single-Menu Multilingual | Set Variable (Global_Language), Menu, Functions |
| Dynamic business hours from external API | 14 | Dynamic Business Hours (API-Driven) | HTTP Request, Functions, Condition |

## Blueprint Composition Patterns

Common combinations from `flow-blueprints.md § Combining Blueprints`.

| Combination | Merge Point | Notes |
|-------------|-------------|-------|
| Business Hours (3) + Simple IVR (1) | Replace 1's NewPhoneContact→Menu with 3's NewPhoneContact→BusinessHours→WorkingHours→Menu | Add closed/holiday exit paths from BP3 |
| Simple IVR (1) + Callback Offer (5) | After Queue Contact in BP1, add BP5's Get Queue Info→Condition→Callback chain | Callback replaces disconnect on high EWT |
| DNIS Routing (2) + Language Selection (7) | After DNIS-based queue selection, add BP7's language menu per branch | Each DNIS branch gets its own language menu, or share one |
| DNIS Routing (2) + Business Hours (3) | After DNIS lookup identifies the store, check that store's business hours | Use Functions to map DNIS→schedule name, then Business Hours |
| AI Agent (11) + Post-Call Survey (8) | BP8 goes in AgentDisconnected event flow; BP11 is the main flow | Survey fires after agent disconnect regardless of main flow |
| Caller Verification (6) + Skill Routing (9) | After CJDS lookup, use verified status to set skill variable | Verified callers get VIP skill routing |
| Business Hours (3) + AI Agent (11) + Callback (5) | BP3 entry → working hours → BP11 → escalation overflow → BP5 | Callback offered when AI agent escalates and queue is long |
| DNIS (2) + Business Hours (3) + IVR (1) | NewPhoneContact→Case(DNIS)→Functions(get store data)→BusinessHours→Menu | Functions returns store-specific schedule name |
| Language Selection (7) OR Single-Menu Multilingual (13) | If >2 activities differ per language, use BP7 (separate menus). If only the TTS prompts change, use BP13 (shared menu with variable prompts). | BP13 avoids duplicating the entire menu tree; BP7 gives full per-language control |

### Composition Rules

1. **One NewPhoneContact per flow.** Only one start node exists — the first blueprint provides the entry; subsequent blueprints connect downstream.
2. **Event handlers are additive.** Each blueprint contributes its relevant event handlers (e.g., BP5 adds CallbackFailed, BP8 adds AgentDisconnected survey).
3. **Variables merge by name.** When combining, deduplicate variables. If two blueprints use the same variable name for different purposes, rename one.
4. **Shared activities merge into one.** If both blueprints have a Queue Contact to the same queue, use one instance. Don't duplicate terminal activities (Disconnect Contact) unnecessarily — but each unique exit path needs its own.
5. **OnGlobalError is always present.** Every combined flow must have OnGlobalError wired. If multiple blueprints define error handling, merge into one error handler chain.

## Activity Quick Reference

One row per activity. Exit ports and required config extracted from `docs/reference/flow-designer-essentials.md` and `docs/reference/flow-designer-activities/`.

**Port name convention:** "Default" is the success path for most activities. "Error" is the system-error path. Activity-specific ports are listed explicitly. See the Port Name Canonical Map below for exact names per activity.

### Essential Activities (flow-designer-essentials.md)

| Activity | Category | Exit Ports | Required Config | Doc |
|----------|----------|------------|-----------------|-----|
| NewPhoneContact | Start | Out | (pre-placed, no config) | essentials |
| Play Message | Action | Default, Error | Prompt (TTS text or audio file), Connector | essentials |
| Play Music | Action | Default, Error | Music File, Music Duration | essentials |
| Set Variable | Utility | Out, Error | Variable, Variable Value (up to 10 per activity) | essentials |
| Queue Contact | Contact Handling | Default, Error | Queue (Static or Variable), optional: Priority, Skills, Skill Relaxation | essentials |
| Disconnect Contact | Terminal | (none — terminal) | (no config) | essentials |

### Situational Activities (flow-designer-activities/)

| Activity | Category | Exit Ports | Required Config | Doc File |
|----------|----------|------------|-----------------|----------|
| Menu | Gateway | [digit branches], No-Input Timeout, Unmatched Entry, Error | Prompt, Custom Menu Links (digit→label), No-Input Timeout | menu.md |
| Collect Digits | Gateway | Default, Entry Timeout, Unmatched Entry, Error | Prompt, Min Digits, Max Digits | collect-digits.md |
| Condition | Gateway | True, False, Error | Expression | condition.md |
| Case | Gateway | [case value branches], Default, Error | Variable or Expression, Case values (max 20) | case.md |
| Business Hours | Gateway | Overrides, Holidays, Working Hours, Default, Error | Schedule (Static or Variable) | business-hours.md |
| Percentage Allocation | Gateway | [Path 1..N], Error | Output paths (2-10), Percentage weights (sum to 100) | percentage-allocation.md |
| HTTP Request | Action | Default, Error | URL, Method, Headers, optional: Body, Parse settings | http-request.md |
| Parse | Action | Default, Error | Input Variable, Content Type, Output Variable, Path Expression | parse.md |
| Functions | Action | Default, Error | Function selection, Input Mappings, Output JSONPath | functions-activity.md |
| BRE Request | Action | Default, Error | Context, Key | bre-request.md |
| HTTP Connector | Action | Default, Error | Connector, Request Path, Method | http-connector.md |
| Custom Connectors | Action | Default, Error | Connector, Request Path, Method | custom-connectors.md |
| Callback | Contact Handling | Default, Error | Callback Dial Number, optional: Queue, ANI | callback.md |
| Schedule Callback | Contact Handling | Default, Error | Callback Dial Number, Queue, Schedule Date/Time/Timezone | schedule-callback.md |
| Get Queue Info | Contact Handling | Default, Insufficient Information, Failure | Queue, Lookback Time | get-queue-info.md |
| Advanced Queue Information | Contact Handling | Default, Error | Queue | advanced-queue-information.md |
| Escalate CDG | Contact Handling | Default, Error | (no config — operates on current queue) | escalate-cdg.md |
| Set Contact Priority | Contact Handling | Default, Error | Priority (P1-P9) | set-contact-priority.md |
| Queue To Agent | Contact Handling | Default, Error | Agent Variable, Agent Lookup Type, Reporting Queue | queue-to-agent.md |
| Virtual Agent V2 | AI | Handled, Escalated, Error | CCAI Config, optional: State Event Settings | virtual-agent-v2.md |
| Virtual Agent (Legacy) | AI | Handled, Escalated, Error | (deprecated — use VAV2) | virtual-agent-legacy.md |
| Blind Transfer | Terminal | Failure | Transfer Dial Number | blind-transfer.md |
| Bridged Transfer | Action | Failure (only wireable port — branch on `FailureCode`) | Transfer Dial Number, Timeout | bridged-transfer.md |
| GoTo | Terminal | (terminal) | Destination Flow or Entry Point | goto.md |
| End Flow | Terminal | (none — terminal) | (no config) — event flows only | end-flow.md |
| Wait | Utility | Default, Error | Duration (10s–72h) | wait.md |
| Record | Action | Default, No Input Timeout, Error | Silence Timeout, Max Duration, Terminator | record.md |
| Feedback V2 | Action | Default, Error | Survey (from Survey Builder) | feedback-v2.md |
| Screen Pop | Event | (single exit) | Screen Pop URL, Display mode | screen-pop.md |
| Recording Control | Utility | Default | Enable Recording (variable) | recording-control.md |
| Set Whisper | Utility | Default | Whisper prompt | set-whisper.md |
| Set Announcement | Utility | Default | Announcement prompt | set-announcement.md |
| Send Digits | Utility | Default | DTMF digits | send-digits.md |
| Set Caller ID | Event (terminal) | (none — PreDial terminal) | Caller ID DN | set-caller-id.md |
| Call Progress Analysis | Action | CPA Successful, Error | (outbound campaign activity) | call-progress-analysis.md |
| Upload Audio | Action | Default, Error | Audio data variable | upload-audio.md |
| Start Media Stream | Action | Default, Error | Media Destination | start-media-stream.md |
| Outdial Entry Point | Start | (outbound campaign start) | (restricted activity set) | outdial-entry-point.md |
| Receive Message | Action (BYOC custom messaging) | Timeout, Error | Channel Type, Channel Name, Timeout (UI not documented — beta) | receive-message.md |
| Send Custom Message | Action (BYOC custom messaging) | Error | Channel Name, Message Type, Message Text (UI not documented — beta) | send-custom-message.md |
| Cryptographic Hash | Utility | Default (implicit), Error | Plain Text input; Salt (FlowIR validator requires non-empty even when Apply Salt is off) | cryptographic-hash.md |
| Generate OTP | Utility | Default (implicit), Error | OTP Format, OTP Length, OTP Validity, On-resend action, Transaction Reference | generate-otp.md |
| Verify OTP | Utility | Failure, Resend, Error | OTP variable, Transaction Reference | verify-otp.md |

## Variable Naming Conventions

Standard variable names used across blueprints. Use these for consistency.

| Variable | Type | Used In | Purpose |
|----------|------|---------|---------|
| CallerANI | STRING | Most flows | Stores caller's phone number from `{{NewPhoneContact.ANI}}` |
| DNIS | STRING | DNIS routing | Stores dialed number from `{{NewPhoneContact.DNIS}}` |
| Global_Language | STRING (Global) | Multilingual | TTS language code (e.g., `en-US`, `es-US`) |
| Global_VoiceName | STRING (Global) | Multilingual | TTS voice name override |
| Global_FeedbackSurveyOptin | BOOLEAN (Global) | Post-call survey | Must be `true` before Feedback V2 executes |
| noInputCount | INTEGER | Menu retry | Counter for no-input retries |
| storeId | STRING | DNIS/data dip | Identifier from lookup |
| customerTier | STRING | Data dip + route | Customer tier from API response |
| VerifiedCount | INTEGER | CJDS verification | Result count from CJDS event query |
| RequiredSkill | STRING | Skill routing | Skill value for Queue Contact skill matching |
| event_name | STRING | Scripted AI fulfillment | State Event name to send back to agent |
| event_data | JSON | Scripted AI fulfillment | Parsed API response (counts toward 5 JSON limit) |
| event_data_string | STRING | Scripted AI fulfillment | Stringified event_data (VAV2 requires STRING) |
| PrimaryDN | STRING | Sequential transfer | Primary transfer destination |
| SecondaryDN | STRING | Sequential transfer | Secondary transfer destination |

### Variable Type Rules

| Type | Limits | Use For |
|------|--------|---------|
| STRING | No documented limit | Phone numbers, names, IDs, text |
| INTEGER | Standard integer range | Counters, priorities, status codes |
| BOOLEAN | true/false | Flags, toggles |
| DECIMAL | Standard decimal | Percentages, scores |
| DATE TIME | ISO-8601 formats | Timestamps, schedules |
| JSON | **Max 5 per flow, 16KB each** | Parsed API responses, complex data |
| Global STRING | Init: 256 chars, Runtime: 1024 chars | Reportable variables, shared config |

## TTS Connector Reference

| Connector | Setup | Language Support | Character Limit | Notes |
|-----------|-------|-----------------|-----------------|-------|
| Cisco Cloud TTS | Default — no setup needed | Multiple (set via `Global_Language`) | None | Available on Next Gen voice platform |
| Google TTS | Requires ChirpTTS connector in Control Hub | Multiple | Not documented | Classic platform: Google TTS only |

**TTS in activities:** Play Message, Menu, and Collect Digits all support TTS prompts. Each supports:
- Speaking Rate: 0.25–4.0 wpm (default 1.0)
- Volume Gain: -96.0–16.0 dB (default 0.0)
- Override Default Language & Voice Settings toggle
- `{{variable}}` interpolation in TTS text
- SSML tags inside `<speak>` wrappers (Cisco TTS)

**Use single quotes** inside Pebble expressions in TTS text. Double quotes conflict with the expression parser.

## Common Design Gotchas

Issues to catch during design (before build).

| Gotcha | Wrong | Right | Why |
|--------|-------|-------|-----|
| Menu after Queue | Queue Contact → Menu | Menu → Queue Contact | Can't play menu while caller is in queue |
| Self-loop on Menu without counter | Menu Timeout → same Menu | Menu Timeout → SetVariable(count+1) → Condition(count<3) → Menu | Infinite loop with no exit |
| End Flow in main flow | Main path ends with End Flow | Main path ends with Disconnect Contact | End Flow doesn't hang up — caller hears dead air |
| Play Message only loop after Queue | Queue → Play Message → Play Message → ... | Queue → Play Music → Play Message → Play Music → ... | Must include Play Music in loop after Queue |
| HTTP Request right after Queue | Queue → HTTP Request | Queue → Play Message → HTTP Request | HTTP may fail due to timing |
| Missing OnGlobalError | No event handler wired | Play Message → Queue → Play Music → Disconnect | Errors silently drop calls |
| VAV2 after Queue Contact | Queue → VAV2 | VAV2 → Queue (on Escalated) | Unsupported configuration |
| VAV2 in Event Flow | AgentDisconnected → VAV2 | VAV2 in main flow only | Unsupported configuration |
| Variable Queue with skills | Variable Queue + Skill Requirements | Static Queue + Skill Requirements | Variable Queue ignores skills, uses LAA |
| JSON variable overuse | 6+ JSON variables | Max 5 JSON, use STRING + Parse for additional | Platform limit is 5 per flow, 16KB each |
| INTEGER for phone numbers | Phone: INTEGER type | Phone: STRING type | Leading zeros stripped, formatting lost |
| Missing Disconnect after Callback | Callback → (nothing) | Callback → Disconnect Contact | Call never ends without Disconnect |
| No CallbackFailed handler | Callback with no event handler | Wire CallbackFailed → Wait → Callback retry | Failed callbacks never retried |
| Priority outside 1-9 | Priority: 0 or 10+ | Priority: P1–P9 | Values outside 1–9 default to P10 (lowest) |
| Global Variable string too long | >1024 chars at runtime | Keep under 1024 chars | Exceeding causes call failures |
| Blind Transfer silence | Blind Transfer → (no comfort message) | Play Message → Blind Transfer | Caller hears dead air during transfer |
| Empty string comparison | `{{var == ""}}` in Condition | Use numeric check: `{{count > 0}}` | Empty string comparison unsupported |
| EWT returns -1 | Treat -1 as "short wait" | Handle as "unknown wait time" | -1 means insufficient data, not zero wait |

## Port Name Canonical Map

Port names for the design doc Connections table. These match the convention from `flow-designer-design-doc.md` and `build-spec-diagram/reference.md` PORT_DEFINITIONS — the standard error port is **"Error"** (not "Undefined Error"), and activity-specific ports use the simplified names below.

> The activity doc files in `docs/reference/flow-designer-activities/` use "Undefined Error" for the error path. The design doc template normalizes this to "Error" for consistency with the spec diagram generator. Use the names below in the design doc, not the activity doc names.

| Activity Type | Port Name | Fires When | Include in Connections? |
|---------------|-----------|------------|------------------------|
| NewPhoneContact | Out | Always (flow entry) | Yes |
| Play Message | Default | Playback complete | Yes |
| Play Message | Error | System error | No (auto-handled) |
| Play Music | Default | Music duration elapsed or agent answers | Yes |
| Play Music | Error | System error | No (auto-handled) |
| Set Variable | Out | Variables set | Yes |
| Set Variable | Error | System error | No (auto-handled) |
| Queue Contact | Default | Contact placed in queue | Yes |
| Queue Contact | Error | System error | No (auto-handled) |
| Disconnect Contact | (terminal) | Call terminated | Yes |
| Menu | [digit] - [label] | Caller pressed that digit (e.g., "1 - Sales") | Yes |
| Menu | No-Input Timeout | No digit within timeout | Yes |
| Menu | Unmatched Entry | Digit not in menu options | Yes |
| Menu | Error | System error during Menu execution (trigger semantics not documented) | No (auto-handled) |
| Collect Digits | Default | Valid digits collected within the timeouts and digit-count constraints (registry lists no success port — the success edge carries no condition) | Yes |
| Collect Digits | Entry Timeout | No-input timeout elapsed without receiving any digits | Yes |
| Collect Digits | Unmatched Entry | Input received but did not match expected criteria (e.g. fewer than Minimum Digits before terminator or inter-digit timeout) | Yes |
| Collect Digits | Error | System error during digit collection | No (auto-handled) |
| Condition | True | Expression is true | Yes |
| Condition | False | Expression is false | Yes |
| Condition | Error | System error | No (auto-handled) |
| Case | [value] | Variable matches case value | Yes |
| Case | Default | No case matched | Yes |
| Case | Error | System error | No (auto-handled) |
| Business Hours | Overrides | Current time is defined as an override — taken regardless of the shift timings | Yes |
| Business Hours | Holidays | Current day is in the Holidays List — taken regardless of the shift timings | Yes |
| Business Hours | Working Hours | Within the shift timing of the selected business hour (primary path) | Yes |
| Business Hours | Default | None of the above evaluates | Yes |
| Business Hours | Error | System error | No (auto-handled) |
| HTTP Request | Default | Request completed (any status code) | Yes |
| HTTP Request | Error | Connection failure, DNS error | No (auto-handled) |
| Parse | Default | Parse succeeded | Yes |
| Parse | Error | Malformed input or bad path | No (auto-handled) |
| Functions | Default | Function executed successfully | Yes |
| Functions | Error | Exception, timeout, or memory | No (auto-handled) |
| Callback | Default | Callback registered | Yes |
| Callback | Error | System error | No (auto-handled) |
| Bridged Transfer | Failure | The only output port in the live registry — branch on `FailureCode` here | Yes |
| Blind Transfer | Failure | Transfer initiated (terminal — call leaves WxCC) | Yes |
| GoTo | (terminal) | Call transfers to destination flow | Yes |
| End Flow | (terminal) | Flow ends (call continues) | Yes |
| Virtual Agent V2 | Handled | AI resolved the interaction | Yes |
| Virtual Agent V2 | Escalated | Caller needs human agent | Yes |
| Virtual Agent V2 | Error | Error during conversation | No (auto-handled) |
| Get Queue Info | Default | Valid PIQ and a positive EWT returned | Yes |
| Get Queue Info | Insufficient Information | Valid PIQ but EWT = -1 (not enough data to estimate) — branch here rather than testing the EWT variable | Yes |
| Get Queue Info | Failure | API failure or invalid queue | Yes |
| Advanced Queue Information | Default | Info retrieved | Yes |
| Advanced Queue Information | Error | System error | No (auto-handled) |
| Escalate CDG | Default | CDG escalated | Yes |
| Escalate CDG | Error | System error | No (auto-handled) |
| Feedback V2 | Default | Survey complete (full or partial) | Yes |
| Feedback V2 | Error | System error | No (auto-handled) |
| Queue To Agent | Default | Agent reserved or parked/recovery | Yes |
| Queue To Agent | Error | System error | No (auto-handled) |
| Schedule Callback | Default | Callback scheduled | Yes |
| Schedule Callback | Error | System error | No (auto-handled) |
| Wait | Default | Duration elapsed | Yes |
| Wait | Error | System error | No (auto-handled) |
| Record | Default | Recording captured — `Record_audioFileData` populated | Yes |
| Record | No Input Timeout | A distinct output port, separate from Error (trigger semantics not documented) | Yes |
| Record | Error | Recording failed | No (auto-handled) |
| Percentage Allocation | [Path 1..N] | WRR selected this path | Yes |
| Percentage Allocation | Error | System error | No (auto-handled) |
| Start Media Stream | Default | Stream started | Yes |
| Start Media Stream | Error | Stream failed | No (auto-handled) |
| Screen Pop | Default | URL pushed to desktop | Yes |
| Screen Pop | Error | System error | No (auto-handled) |
| Recording Control | Default | Recording toggled | Yes |
| Recording Control | Error | System error | No (auto-handled) |
| Set Whisper | Default | Whisper configured | Yes |
| Set Whisper | Error | System error | No (auto-handled) |
| Set Announcement | Default | Announcement configured | Yes |
| Set Announcement | Error | System error | No (auto-handled) |
| Send Digits | Default | DTMF sent | Yes |
| Send Digits | Error | System error | No (auto-handled) |
| Set Caller ID | Default | Caller ID set (PreDial terminal) | Yes |
| Set Caller ID | Error | System error | No (auto-handled) |
| Set Contact Priority | Default | Priority set | Yes |
| Set Contact Priority | Error | System error | No (auto-handled) |
| Call Progress Analysis | CPA Successful | CPA completed | Yes |
| Call Progress Analysis | Error | System error | No (auto-handled) |
| Upload Audio | Default | Audio uploaded | Yes |
| Upload Audio | Error | System error | No (auto-handled) |
| HTTP Connector | Default | Request completed | Yes |
| HTTP Connector | Error | System error | No (auto-handled) |
| Custom Connectors | Default | Request completed | Yes |
| Custom Connectors | Error | System error | No (auto-handled) |
| Outdial Entry Point | (outbound campaign start) | Restricted context | Yes |
| Cryptographic Hash | Default | Hash generated (implicit `out` port — registry lists only error) | Yes |
| Cryptographic Hash | Error | Hash generation failed because of invalid input | No (auto-handled) |
| Generate OTP | Default | OTP generated (implicit `out` port — registry lists only error) | Yes |
| Generate OTP | Error | System error (trigger semantics not documented) | No (auto-handled) |
| Verify OTP | Failure | Verification failed (exact semantics not documented) | Yes |
| Verify OTP | Resend | Resend requested — loop back to Generate OTP | Yes |
| Verify OTP | Error | System error (trigger semantics not documented) | No (auto-handled) |
| Receive Message | Timeout | (from live registry — semantics not documented; BYOC beta) | Yes |
| Receive Message | Error | (from live registry — semantics not documented; BYOC beta) | Yes |
| Send Custom Message | Error | (from live registry — semantics not documented; BYOC beta) | Yes |
| Event handlers (all) | Out | Event handler entry | Yes |

> **Bridged Transfer — unresolved.** Cisco states the flow retains control of the call and "when the third-party ends the call, the call flow continues and reengages as required," yet the live registry exposes no success port (only `failure`, and bridged-transfer is absent from flowir.md's implicit-`out` list). Both can be true if the continuation is implicit. Until this is confirmed by a live call, wire only the `failure` port and do not design a success-continuation edge.

## Transfer Type Decision

| Choose | When | Why |
|--------|------|-----|
| **Blind Transfer** | The destination always answers (e.g., another queue, a known extension), OR you don't need to handle transfer failure in the flow | Call leaves WxCC — simpler, no return path needed |
| **Bridged Transfer** | You need to handle no-answer/busy in the flow (e.g., try extension, on failure route to queue) | Call stays in WxCC — flow continues on failure |

Default to **Blind Transfer** unless the requirements explicitly mention fallback behavior on transfer failure.
