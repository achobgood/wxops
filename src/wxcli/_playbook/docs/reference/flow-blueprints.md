# Flow Designer — Flow Blueprints

Common voice flow patterns for WxCC Flow Designer. Each blueprint provides the activities, connections graph, variables, and customization points needed to build the flow.

Use these as starting points when filling out a [Flow Designer Design Document](../templates/flow-designer-design-doc.md). Copy the relevant blueprint's tables into your design doc and customize the values.

> **Source authority:** Activity types, port names, output variables, and configuration fields in these blueprints come from `docs/reference/flow-designer-essentials.md` and `docs/reference/flow-designer-activities/`. If a blueprint detail conflicts with an activity doc, the activity doc wins.

---

## 1. Simple IVR

**When to use:** Caller dials in, hears a menu ("Press 1 for Sales, 2 for Support"), and is routed to the appropriate queue.

### Activities

| ID | Label | Activity Type | Key Configuration |
|----|-------|--------------|-------------------|
| 1 | NewPhoneContact | NewPhoneContact | (start) |
| 2 | MainMenu | Menu | Prompt: "Press 1 for Sales, 2 for Support"; Options: 1=Sales, 2=Support |
| 3 | QueueSales | Queue Contact | Queue: Sales_Queue |
| 4 | QueueSupport | Queue Contact | Queue: Support_Queue |
| 5 | HoldMusic | Play Music | File: Default; Duration: 600 |
| 6 | HoldMusic2 | Play Music | File: Default; Duration: 600 |
| 7 | InvalidMsg | Play Message | TTS: "That wasn't a valid option. Please try again." |
| 8 | Disconnect | Disconnect Contact | (terminal) |
| 9 | Disconnect2 | Disconnect Contact | (terminal) |

### Connections

| Source Activity | Port | Target Activity |
|----------------|------|-----------------|
| NewPhoneContact | Out | MainMenu |
| MainMenu | 1 - Sales | QueueSales |
| MainMenu | 2 - Support | QueueSupport |
| MainMenu | No-Input Timeout | InvalidMsg |
| MainMenu | Unmatched Entry | InvalidMsg |
| InvalidMsg | Default | MainMenu |
| QueueSales | Default | HoldMusic |
| QueueSupport | Default | HoldMusic2 |
| HoldMusic | Default | Disconnect |
| HoldMusic2 | Default | Disconnect2 |

### Variables

None required beyond system variables.

### Customization Points

- Menu prompt text and option labels
- Queue names
- Number of menu options (up to 10)
- Retry logic (add Set Variable counter + Condition before looping back to Menu)

---

## 2. DNIS-Based Routing

**When to use:** A single Entry Point serves multiple dialed numbers. Route to different queues based on which number the caller dialed.

### Activities

| ID | Label | Activity Type | Key Configuration |
|----|-------|--------------|-------------------|
| 1 | NewPhoneContact | NewPhoneContact | (start) |
| 2 | DNISRoute | Case | Variable: `{{NewPhoneContact.DNIS}}`; Branches: per DNIS |
| 3 | QueueSales | Queue Contact | Queue: Sales_Queue |
| 4 | QueueSupport | Queue Contact | Queue: Support_Queue |
| 5 | QueueGeneral | Queue Contact | Queue: General_Queue |
| 6 | HoldMusic | Play Music | File: Default; Duration: 600 |
| 7 | Disconnect | Disconnect Contact | (terminal) |

### Connections

| Source Activity | Port | Target Activity |
|----------------|------|-----------------|
| NewPhoneContact | Out | DNISRoute |
| DNISRoute | +18005551111 | QueueSales |
| DNISRoute | +18005552222 | QueueSupport |
| DNISRoute | Default | QueueGeneral |
| QueueSales | Default | HoldMusic |
| QueueSupport | Default | HoldMusic |
| QueueGeneral | Default | HoldMusic |
| HoldMusic | Default | Disconnect |

### Variables

None required — uses `{{NewPhoneContact.DNIS}}` directly.

### Customization Points

- DNIS values and corresponding queues
- For large DNIS maps (>5 routes), consider Functions Activity with a lookup table instead of Case

---

## 3. Business Hours Routing

**When to use:** Route callers differently based on whether the contact center is open, closed, or on holiday.

### Activities

| ID | Label | Activity Type | Key Configuration |
|----|-------|--------------|-------------------|
| 1 | NewPhoneContact | NewPhoneContact | (start) |
| 2 | CheckHours | Business Hours | Schedule: [schedule name] |
| 3 | OpenGreeting | Play Message | TTS: "Thank you for calling [Organization]." |
| 4 | MainMenu | Menu | Prompt: "[menu options]" |
| 5 | ClosedMsg | Play Message | TTS: "We are currently closed. Our hours are Monday through Friday, 8 AM to 6 PM." |
| 6 | HolidayMsg | Play Message | TTS: "We are closed for the holiday. Please call back on the next business day." |
| 7 | QueueMain | Queue Contact | Queue: Main_Queue |
| 8 | HoldMusic | Play Music | File: Default; Duration: 600 |
| 9 | DisconnectOpen | Disconnect Contact | (terminal) |
| 10 | DisconnectClosed | Disconnect Contact | (terminal) |
| 11 | DisconnectHoliday | Disconnect Contact | (terminal) |

### Connections

| Source Activity | Port | Target Activity |
|----------------|------|-----------------|
| NewPhoneContact | Out | CheckHours |
| CheckHours | Working Hours | OpenGreeting |
| CheckHours | Holidays | HolidayMsg |
| CheckHours | Default | ClosedMsg |
| OpenGreeting | Default | MainMenu |
| MainMenu | [options] | QueueMain |
| QueueMain | Default | HoldMusic |
| HoldMusic | Default | DisconnectOpen |
| ClosedMsg | Default | DisconnectClosed |
| HolidayMsg | Default | DisconnectHoliday |

### Variables

None required — Business Hours schedule is configured in Control Hub.

### Customization Points

- Business Hours schedule name (created in Control Hub > Contact Center > Business Hours)
- Open/closed/holiday TTS messages
- What happens during working hours (Menu, VA V2, direct queue, etc.)

---

## 4. Queue with Hold Treatment

**When to use:** Caller is queued and hears periodic position/EWT announcements while waiting, with escalation if wait exceeds a threshold.

### Activities

| ID | Label | Activity Type | Key Configuration |
|----|-------|--------------|-------------------|
| 1 | NewPhoneContact | NewPhoneContact | (start) |
| 2 | WelcomeMsg | Play Message | TTS: "Thank you for calling. Please hold while we connect you." |
| 3 | QueueMain | Queue Contact | Queue: Main_Queue |
| 4 | HoldMusic1 | Play Music | File: Default; Duration: 30 |
| 5 | CheckQueue | Get Queue Info | Queue: Main_Queue; Lookback: 60 min |
| 6 | PositionMsg | Play Message | TTS: "You are currently number {{CheckQueue.PositionInQueue}} in line." |
| 7 | HoldMusic2 | Play Music | File: Default; Duration: 30 |
| 8 | Disconnect | Disconnect Contact | (terminal) |

### Connections

| Source Activity | Port | Target Activity |
|----------------|------|-----------------|
| NewPhoneContact | Out | WelcomeMsg |
| WelcomeMsg | Default | QueueMain |
| QueueMain | Default | HoldMusic1 |
| HoldMusic1 | Default | CheckQueue |
| CheckQueue | Default | PositionMsg |
| CheckQueue | Error | HoldMusic2 |
| PositionMsg | Default | HoldMusic2 |
| HoldMusic2 | Default | HoldMusic1 |

### Variables

None required — uses Get Queue Info output variables directly in TTS.

### Customization Points

- Hold music duration between announcements (30s shown)
- Position/EWT announcement text
- Whether to add an Escalate CDG activity after a threshold
- Whether to offer a callback (see Blueprint 5)

---

## 5. Callback Offer

**When to use:** After queueing, check estimated wait time. If EWT exceeds a threshold, offer the caller a callback instead of waiting.

### Activities

| ID | Label | Activity Type | Key Configuration |
|----|-------|--------------|-------------------|
| 1 | NewPhoneContact | NewPhoneContact | (start) |
| 2 | WelcomeMsg | Play Message | TTS: "Thank you for calling." |
| 3 | QueueMain | Queue Contact | Queue: Main_Queue |
| 4 | CheckEWT | Get Queue Info | Queue: Main_Queue; Lookback: 60 min |
| 5 | EWTHigh | Condition | Expression: `{{CheckEWT.EstimatedWaitTime > 120000}}` |
| 6 | OfferCallback | Play Message | TTS: "Your estimated wait is over 2 minutes. Press 1 for a callback, or stay on the line." |
| 7 | CollectChoice | Collect Digits | Min: 1; Max: 1; Timeout: 7s |
| 8 | DidPress1 | Condition | Expression: `{{CollectChoice.DigitsEntered == 1}}` |
| 9 | RegisterCallback | Callback | Dial Number: `{{NewContact.ANI}}`; Queue: same |
| 10 | ConfirmMsg | Play Message | TTS: "We will call you back shortly. Goodbye." |
| 11 | HoldMusic | Play Music | File: Default; Duration: 60 |
| 12 | Disconnect | Disconnect Contact | (terminal) |
| 13 | Disconnect2 | Disconnect Contact | (terminal) |

### Connections

| Source Activity | Port | Target Activity |
|----------------|------|-----------------|
| NewPhoneContact | Out | WelcomeMsg |
| WelcomeMsg | Default | QueueMain |
| QueueMain | Default | CheckEWT |
| CheckEWT | Default | EWTHigh |
| CheckEWT | Error | HoldMusic |
| EWTHigh | True | OfferCallback |
| EWTHigh | False | HoldMusic |
| OfferCallback | Default | CollectChoice |
| CollectChoice | Default | DidPress1 |
| CollectChoice | Error | HoldMusic |
| DidPress1 | True | RegisterCallback |
| DidPress1 | False | HoldMusic |
| RegisterCallback | Default | ConfirmMsg |
| ConfirmMsg | Default | Disconnect |
| HoldMusic | Default | CheckEWT |
| Disconnect | — | — |

### Variables

None required — uses activity output variables directly.

### Event Handler: CallbackFailed

```
CallbackFailed → Wait (60s) → Callback (retry) → End Flow
```

### Customization Points

- EWT threshold (120000ms = 2 minutes shown)
- Callback confirmation message
- Retry count and interval in CallbackFailed handler

---

## 6. Caller Verification (CJDS)

**When to use:** Check CJDS for a custom event to determine if the caller is known/verified. Route verified callers differently (skip IVR, VIP queue, etc.).

### Activities

| ID | Label | Activity Type | Key Configuration |
|----|-------|--------------|-------------------|
| 1 | NewPhoneContact | NewPhoneContact | (start) |
| 2 | CaptureANI | Set Variable | `CallerANI` = `{{NewPhoneContact.ANI}}` |
| 3 | CJDSLookup | HTTP Request | URL: CJDS events endpoint; Method: GET; Query: identity={{CallerANI}}, filter=type=='custom:verified'; Parse: VerifiedCount = $.meta.resultCount |
| 4 | IsVerified | Condition | Expression: `{{VerifiedCount > 0}}` |
| 5 | VerifiedPath | Play Message | TTS: "Welcome back." |
| 6 | UnverifiedPath | Play Message | TTS: "Thank you for calling." |
| 7 | QueueVIP | Queue Contact | Queue: VIP_Queue; Priority: P1 |
| 8 | QueueGeneral | Queue Contact | Queue: General_Queue |
| 9 | HoldMusic | Play Music | File: Default; Duration: 600 |
| 10 | HoldMusic2 | Play Music | File: Default; Duration: 600 |
| 11 | Disconnect | Disconnect Contact | (terminal) |
| 12 | Disconnect2 | Disconnect Contact | (terminal) |

### Connections

| Source Activity | Port | Target Activity |
|----------------|------|-----------------|
| NewPhoneContact | Out | CaptureANI |
| CaptureANI | Out | CJDSLookup |
| CJDSLookup | Default | IsVerified |
| CJDSLookup | Error | UnverifiedPath |
| IsVerified | True | VerifiedPath |
| IsVerified | False | UnverifiedPath |
| VerifiedPath | Default | QueueVIP |
| UnverifiedPath | Default | QueueGeneral |
| QueueVIP | Default | HoldMusic |
| QueueGeneral | Default | HoldMusic2 |
| HoldMusic | Default | Disconnect |
| HoldMusic2 | Default | Disconnect2 |

### Variables

| Name | Type | Default | Purpose |
|------|------|---------|---------|
| CallerANI | STRING | (empty) | Raw ANI from NewPhoneContact |
| VerifiedCount | INTEGER | 0 | Result count from CJDS event query |

### Global Variables

| Name | Type | Sensitive | Purpose |
|------|------|-----------|---------|
| CJDS_Auth_Token | String | Yes | Bearer token for CJDS API |
| CJDS_Workspace_ID | String | No | CJDS workspace identifier |
| CJDS_Region | String | No | Region slug (e.g., useast1) |

### Customization Points

- CJDS event type to check (custom:verified, custom:vip, etc.)
- Verified vs. unverified routing (VIP queue, skip IVR, different greeting)
- Whether to write a new CJDS event after verification (add HTTP Request POST)

---

## 7. Language Selection

**When to use:** Caller chooses a language at the start. The selection persists via `Global_Language` for all downstream TTS.

### Activities

| ID | Label | Activity Type | Key Configuration |
|----|-------|--------------|-------------------|
| 1 | NewPhoneContact | NewPhoneContact | (start) |
| 2 | LangMenu | Menu | Prompt: "For English, press 1. Para Espanol, oprima 2."; Options: 1=English, 2=Spanish |
| 3 | SetEnglish | Set Variable | `Global_Language` = `en-US` |
| 4 | SetSpanish | Set Variable | `Global_Language` = `es-US` |
| 5 | EnglishMenu | Menu | Prompt (English): "[main menu options]" |
| 6 | SpanishMenu | Menu | Prompt (Spanish): "[opciones del menu]" |
| 7 | QueueEN | Queue Contact | Queue: English_Queue |
| 8 | QueueES | Queue Contact | Queue: Spanish_Queue |
| 9 | HoldMusic | Play Music | File: Default; Duration: 600 |
| 10 | HoldMusic2 | Play Music | File: Default; Duration: 600 |
| 11 | Disconnect | Disconnect Contact | (terminal) |
| 12 | Disconnect2 | Disconnect Contact | (terminal) |

### Connections

| Source Activity | Port | Target Activity |
|----------------|------|-----------------|
| NewPhoneContact | Out | LangMenu |
| LangMenu | 1 - English | SetEnglish |
| LangMenu | 2 - Spanish | SetSpanish |
| LangMenu | No-Input Timeout | SetEnglish |
| LangMenu | Unmatched Entry | SetEnglish |
| SetEnglish | Out | EnglishMenu |
| SetSpanish | Out | SpanishMenu |
| EnglishMenu | [options] | QueueEN |
| SpanishMenu | [options] | QueueES |
| QueueEN | Default | HoldMusic |
| QueueES | Default | HoldMusic2 |
| HoldMusic | Default | Disconnect |
| HoldMusic2 | Default | Disconnect2 |

### Variables

Uses the predefined `Global_Language` global variable (set via Set Variable activity).

### Customization Points

- Language codes (en-US, es-US, fr-CA, etc.)
- Default language for no-input/unmatched (English shown)
- Whether language-specific queues or a single queue with skill-based routing

---

## 8. Post-Call Survey

**When to use:** After the agent disconnects, play a CSAT/NPS survey to the caller before hanging up.

### Activities (in AgentDisconnected Event Flow)

| ID | Label | Activity Type | Key Configuration |
|----|-------|--------------|-------------------|
| 1 | SetSurveyOpt | Set Variable | `Global_FeedbackSurveyOptin` = `true` |
| 2 | Survey | Feedback V2 | Survey: [select from Survey Builder dropdown] |
| 3 | Disconnect | Disconnect Contact | (terminal) |

### Connections (AgentDisconnected Event Flow)

| Source Activity | Port | Target Activity |
|----------------|------|-----------------|
| AgentDisconnected | Out | SetSurveyOpt |
| SetSurveyOpt | Out | Survey |
| Survey | Default | Disconnect |

### Main Flow Activities

The main flow is unchanged — standard IVR or queue pattern. The survey is entirely in the event flow.

### Prerequisites

- `Global_FeedbackSurveyOptin` must be set to `true` before Feedback V2 executes
- Survey questionnaire must be created in Control Hub > Contact Center > Customer Experience > Surveys
- Feedback V2 must be in the **AgentDisconnected** event flow, not the main canvas

### Customization Points

- Survey type (NPS 0-9, CSAT 1-5, CES 1-5 or 1-7, Custom)
- Thank you / invalid input / timeout audio prompts (configured in Survey Builder)
- Whether survey is opt-in (conditional on caller response) or automatic

---

## 9. Skill-Based Routing

**When to use:** Route to agents with specific skills. Relax skill requirements progressively if no matching agent is available within a timeout.

### Activities

| ID | Label | Activity Type | Key Configuration |
|----|-------|--------------|-------------------|
| 1 | NewPhoneContact | NewPhoneContact | (start) |
| 2 | SetSkill | Set Variable | `RequiredSkill` = `[value based on caller intent or data dip]` |
| 3 | QueueSkilled | Queue Contact | Queue: Skilled_Queue (skill-based); Skill: Language IS {{RequiredSkill}}; Relaxation: after 60s remove skill |
| 4 | HoldMusic | Play Music | File: Default; Duration: 600 |
| 5 | Disconnect | Disconnect Contact | (terminal) |

### Connections

| Source Activity | Port | Target Activity |
|----------------|------|-----------------|
| NewPhoneContact | Out | SetSkill |
| SetSkill | Out | QueueSkilled |
| QueueSkilled | Default | HoldMusic |
| HoldMusic | Default | Disconnect |

### Variables

| Name | Type | Default | Purpose |
|------|------|---------|---------|
| RequiredSkill | STRING | (empty) | Skill value to match against (e.g., language code, product line) |

### Customization Points

- Skill name and values (configured in Control Hub > Contact Center > Skills)
- Skill condition (IS, IS NOT, >=, <=)
- Relaxation timing and steps (e.g., after 60s loosen, after 120s remove)
- Variable Queue is NOT supported with skill-based routing — use Static Queue

---

## 10. Sequential Transfer (Failover)

**When to use:** Try transferring to a primary destination. If no answer or busy, try a secondary destination. If both fail, fall back to a queue.

### Activities

| ID | Label | Activity Type | Key Configuration |
|----|-------|--------------|-------------------|
| 1 | NewPhoneContact | NewPhoneContact | (start) |
| 2 | AnnounceTransfer | Play Message | TTS: "Connecting you now." |
| 3 | TransferPrimary | Bridged Transfer | Dial: {{PrimaryDN}}; Timeout: 30s |
| 4 | CheckPrimary | Condition | Expression: `{{TransferPrimary.FailureCode == 0}}` |
| 5 | TransferSecondary | Bridged Transfer | Dial: {{SecondaryDN}}; Timeout: 30s |
| 6 | CheckSecondary | Condition | Expression: `{{TransferSecondary.FailureCode == 0}}` |
| 7 | FailMsg | Play Message | TTS: "We were unable to connect your call. Please hold for the next available agent." |
| 8 | QueueFallback | Queue Contact | Queue: Fallback_Queue |
| 9 | HoldMusic | Play Music | File: Default; Duration: 600 |
| 10 | Disconnect | Disconnect Contact | (terminal) |
| 11 | Disconnect2 | Disconnect Contact | (terminal) |
| 12 | Disconnect3 | Disconnect Contact | (terminal) |

### Connections

| Source Activity | Port | Target Activity |
|----------------|------|-----------------|
| NewPhoneContact | Out | AnnounceTransfer |
| AnnounceTransfer | Default | TransferPrimary |
| TransferPrimary | Default | CheckPrimary |
| CheckPrimary | True | Disconnect |
| CheckPrimary | False | TransferSecondary |
| TransferSecondary | Default | CheckSecondary |
| CheckSecondary | True | Disconnect2 |
| CheckSecondary | False | FailMsg |
| FailMsg | Default | QueueFallback |
| QueueFallback | Default | HoldMusic |
| HoldMusic | Default | Disconnect3 |

### Variables

| Name | Type | Default | Purpose |
|------|------|---------|---------|
| PrimaryDN | STRING | (empty) | Primary transfer destination (extension or E.164) |
| SecondaryDN | STRING | (empty) | Secondary transfer destination |

### Customization Points

- Number of transfer attempts (add more Bridged Transfer + Condition pairs)
- Transfer timeout per attempt
- Whether to announce each transfer attempt ("Trying another number...")
- Fallback queue for when all transfers fail
- FailureCode 0 = success; all other codes = failure (see bridged-transfer.md for full code list)

---

## 11. AI Agent (Autonomous Voice)

**When to use:** Inbound call routes to an autonomous AI agent (Webex AI Agent Studio) via Virtual Agent V2. Agent handles the conversation; escalation goes to a queue.

### Activities

| ID | Label | Activity Type | Key Configuration |
|----|-------|--------------|-------------------|
| 1 | NewPhoneContact | NewPhoneContact | (start) |
| 2 | AIAgent | Virtual Agent V2 | Agent: [select Cisco AI Agent from dropdown] |
| 3 | QueueEscalation | Queue Contact | Queue: Escalation_Queue |
| 4 | HoldMusic | Play Music | File: Default; Duration: 600 |
| 5 | ErrorMsg | Play Message | TTS: "We're experiencing technical difficulties. Goodbye." |
| 6 | Disconnect | Disconnect Contact | (terminal) |
| 7 | DisconnectHandled | Disconnect Contact | (terminal) |
| 8 | DisconnectError | Disconnect Contact | (terminal) |

### Connections

| Source Activity | Port | Target Activity |
|----------------|------|-----------------|
| NewPhoneContact | Out | AIAgent |
| AIAgent | Escalated | QueueEscalation |
| AIAgent | Handled | DisconnectHandled |
| AIAgent | Error | ErrorMsg |
| QueueEscalation | Default | HoldMusic |
| HoldMusic | Default | Disconnect |
| ErrorMsg | Default | DisconnectError |

### Variables

None required — the AI agent manages its own conversation state.

### Prerequisites

- AI agent created and deployed in AI Agent Studio
- Action flows built and live in Webex Connect

### Customization Points

- AI Agent selection in VAV2 activity
- Escalation queue
- Error handling (queue to fallback vs. disconnect)
- State Event Settings for custom data at session start (pass ANI, DNIS, CRM data to agent)

---

## 12. AI Agent (Scripted Voice)

**When to use:** Inbound call routes to a scripted AI agent. When the agent raises a Custom Event (for fulfillment), the flow handles the API call and returns the result via State Event.

### Activities

| ID | Label | Activity Type | Key Configuration |
|----|-------|--------------|-------------------|
| 1 | NewPhoneContact | NewPhoneContact | (start) |
| 2 | AIAgent | Virtual Agent V2 | Agent: [select Cisco AI Agent (Scripted) from dropdown]; State Event: eventName={{event_name}}, eventData={{event_data_string}} |
| 3 | ParseMeta | Parse | Input: `{{VirtualAgentV2.MetaData}}`; Content Type: JSON; Output: http_input = $ |
| 4 | RouteEvent | Case | Variable: `{{VirtualAgentV2.StateEventName}}`; Branches: per intent exit event |
| 5 | HTTPFulfill | HTTP Request | URL: [API endpoint]; Method: POST; Body: {{http_input}}; Parse: event_data = $ |
| 6 | CheckResult | Condition | Expression: `{{HTTPFulfill.httpStatusCode == 200}}` |
| 7 | SetEventName | Set Variable | `event_name` = `[intent]_confirm_entry` |
| 8 | SetEventData | Set Variable | `event_data_string` = `{{ event_data }}` |
| 9 | ErrorMsg | Play Message | TTS: "I'm having trouble looking that up. Let me connect you to an agent." |
| 10 | QueueEscalation | Queue Contact | Queue: Escalation_Queue |
| 11 | HoldMusic | Play Music | File: Default; Duration: 600 |
| 12 | DisconnectHandled | Disconnect Contact | (terminal) |
| 13 | Disconnect | Disconnect Contact | (terminal) |

### Connections

| Source Activity | Port | Target Activity |
|----------------|------|-----------------|
| NewPhoneContact | Out | AIAgent |
| AIAgent | Handled | DisconnectHandled |
| AIAgent | Escalated | QueueEscalation |
| AIAgent | Error | ErrorMsg |
| AIAgent | ENDED | ParseMeta |
| ParseMeta | Default | RouteEvent |
| RouteEvent | [intent_exit_event] | HTTPFulfill |
| RouteEvent | Default | DisconnectHandled |
| HTTPFulfill | Default | CheckResult |
| HTTPFulfill | Error | ErrorMsg |
| CheckResult | True | SetEventName |
| CheckResult | False | ErrorMsg |
| SetEventName | Out | SetEventData |
| SetEventData | Out | AIAgent |
| ErrorMsg | Default | QueueEscalation |
| QueueEscalation | Default | HoldMusic |
| HoldMusic | Default | Disconnect |

### Variables

| Name | Type | Default | Purpose |
|------|------|---------|---------|
| event_name | STRING | (empty) | State Event name to send back to agent |
| event_data | JSON | {} | Parsed API response |
| event_data_string | STRING | (empty) | Stringified event_data (VAV2 eventData requires STRING) |
| http_input | STRING | (empty) | Parsed from MetaData — Custom Event payload |

### Customization Points

- Case branches (one per intent Custom Event exit name)
- HTTP endpoint per intent
- Event naming convention: `<intent>_exit` (agent → flow) and `<intent>_confirm_entry` (flow → agent)
- For multiple intents: duplicate HTTPFulfill/CheckResult/SetEventName chain per Case branch
- For re-prompting on failure: set event_data_string to a state_update payload that clears a slot (`{"intent":"...","slots":{"slot_name":""}}`)

### Prerequisites

- Scripted agent created in AI Agent Studio with Custom Event responses configured per intent
- Scripted AI Agent deployed and selectable in VAV2 activity

---

## 13. Single-Menu Multilingual

**When to use:** Caller selects a language via a menu option (e.g., Press 0 for Spanish). The same Menu activity serves all languages by switching the TTS prompt variable based on `Global_Language`. Avoids duplicating the entire menu tree per language.

### How It Works

1. A Functions activity (or Set Variable chain) pre-computes TTS prompt strings for each language and stores them in flow variables (e.g., `ttsMenuPrompt`, `ttsMenuPromptEs`)
2. The Menu activity's TTS prompt uses a conditional variable: the flow sets a single `menuPrompt` variable to the language-appropriate string when Global_Language changes
3. When the caller presses the language-switch digit, a Set Variable changes `Global_Language` AND `menuPrompt`, then loops back to the same Menu

### Pattern

Activities:
| ID | Label | Activity Type | Key Configuration |
|----|-------|--------------|-------------------|
| 1 | SetMenuPrompts | Set Variable | `menuPrompt` = `{{ttsMenuPromptEN}}`; `hoursPrompt` = `{{ttsHoursEN}}` |
| 2 | MainMenu | Menu | Prompt: "{{menuPrompt}}"; Options: 1=Transfer, 2=Hours, 3=Address, 0=Language |
| 3 | SwitchLang | Set Variable | Toggle `Global_Language` and `menuPrompt`/`hoursPrompt` to the other language |

Connections:
| Source Activity | Port | Target Activity |
|----------------|------|-----------------|
| MainMenu | 0 - Language | SwitchLang |
| SwitchLang | Out | MainMenu |

### Customization Points
- Number of languages (2 shown; extend by adding more SetVariable toggles)
- Which menu digit triggers the switch
- Whether to use Functions (complex prompt formatting) or Set Variable (simple text swap)

---

## 14. Dynamic Business Hours (API-Driven)

**When to use:** Business hours are managed in an external system (Webex Calling Schedules API, ServiceNow, custom REST endpoint) instead of a static Control Hub schedule. The flow makes an HTTP Request to get hours, then a Functions activity formats them for TTS.

### Activities
| ID | Label | Activity Type | Key Configuration |
|----|-------|--------------|-------------------|
| 1 | NewPhoneContact | NewPhoneContact | (start) |
| 2 | FetchHours | HTTP Request | URL: [schedule API endpoint]; Method: GET |
| 3 | CheckFetchStatus | Condition | Expression: `{{FetchHours.httpStatusCode == 200}}` |
| 4 | FormatHours | Functions | Function: FormatBusinessHours; Input: hoursJson; Output: ttsHours, isOpen |
| 5 | IsOpen | Condition | Expression: `{{isOpen == true}}` |
| 6 | OpenGreeting | Play Message | TTS: "Thank you for calling. [dynamic greeting]" |
| 7 | ClosedMsg | Play Message | TTS: "We are currently closed. {{ttsHours}}" |
| 8 | Disconnect | Disconnect Contact | (terminal) |

### Connections
| Source Activity | Port | Target Activity |
|----------------|------|-----------------|
| NewPhoneContact | Out | FetchHours |
| FetchHours | Default | CheckFetchStatus |
| CheckFetchStatus | True | FormatHours |
| CheckFetchStatus | False | ClosedMsg |
| FormatHours | Default | IsOpen |
| IsOpen | True | OpenGreeting |
| IsOpen | False | ClosedMsg |
| ClosedMsg | Default | Disconnect |

### Customization Points
- API endpoint and auth (Custom Connector vs manual headers)
- Functions logic to determine isOpen based on current time vs schedule
- What to do during open hours (IVR menu, direct queue, AI agent, etc.)

---

## Combining Blueprints

Many production flows combine multiple blueprints. Common combinations:

| Combination | Pattern |
|-------------|---------|
| Business Hours + IVR | Blueprint 3 → during working hours, use Blueprint 1 |
| IVR + Callback | Blueprint 1 → after queueing, add Blueprint 5's callback offer |
| DNIS Routing + Language Selection | Blueprint 2 → per-DNIS, add Blueprint 7's language menu |
| AI Agent + Post-Call Survey | Blueprint 11 → add Blueprint 8 in AgentDisconnected event flow |
| Data Dip + Skill Routing | Blueprint 6 (CJDS or HTTP lookup) → set skill variable → Blueprint 9 |
| Business Hours + AI Agent + Callback | Blueprint 3 → working hours → Blueprint 11 → Blueprint 5 for escalation overflow |

When combining, merge the Activities and Connections tables from each blueprint. Use the Flow Designer Design Doc template to capture the unified flow.

### Worked Example: Business Hours + Simple IVR (Blueprints 3 + 1)

Merge Blueprint 3 (Business Hours Routing) into Blueprint 1 (Simple IVR). Business Hours becomes the entry point; the IVR Menu is the working-hours destination.

**Merged Activities:**

| ID | Label | Activity Type | Key Configuration |
|----|-------|--------------|-------------------|
| 1 | NewPhoneContact | NewPhoneContact | (start) |
| 2 | CheckHours | Business Hours | Schedule: Store_Hours |
| 3 | MainMenu | Menu | Prompt: "Press 1 for Sales, 2 for Support"; Options: 1=Sales, 2=Support |
| 4 | ClosedMsg | Play Message | TTS: "We are currently closed." |
| 5 | HolidayMsg | Play Message | TTS: "We are closed for the holiday." |
| 6 | QueueSales | Queue Contact | Queue: Sales_Queue |
| 7 | QueueSupport | Queue Contact | Queue: Support_Queue |
| 8 | HoldMusic | Play Music | File: Default; Duration: 600 |
| 9 | HoldMusic2 | Play Music | File: Default; Duration: 600 |
| 10 | InvalidMsg | Play Message | TTS: "That wasn't a valid option." |
| 11 | DisconnectOpen | Disconnect Contact | (terminal) |
| 12 | DisconnectClosed | Disconnect Contact | (terminal) |
| 13 | DisconnectHoliday | Disconnect Contact | (terminal) |

**Merged Connections:**

| Source Activity | Port | Target Activity |
|----------------|------|-----------------|
| NewPhoneContact | Out | CheckHours |
| CheckHours | Working Hours | MainMenu |
| CheckHours | Holidays | HolidayMsg |
| CheckHours | Default | ClosedMsg |
| MainMenu | 1 - Sales | QueueSales |
| MainMenu | 2 - Support | QueueSupport |
| MainMenu | No-Input Timeout | InvalidMsg |
| MainMenu | Unmatched Entry | InvalidMsg |
| InvalidMsg | Default | MainMenu |
| QueueSales | Default | HoldMusic |
| QueueSupport | Default | HoldMusic2 |
| HoldMusic | Default | DisconnectOpen |
| HoldMusic2 | Default | DisconnectOpen |
| ClosedMsg | Default | DisconnectClosed |
| HolidayMsg | Default | DisconnectHoliday |

**Merge pattern:** Replace Blueprint 1's `NewPhoneContact → MainMenu` connection with Blueprint 3's `NewPhoneContact → CheckHours → Working Hours → MainMenu`. Add Blueprint 3's closed/holiday paths as new exit branches.

---

## OnGlobalError (Required for All Blueprints)

Every flow MUST have OnGlobalError wired. Without it, unhandled errors silently drop calls.

### Event Flow Activities

| ID | Label | Activity Type | Key Configuration |
|----|-------|--------------|-------------------|
| E1 | ErrorAnnounce | Play Message | TTS: "We're experiencing technical difficulties. Please hold while we connect you to an agent." |
| E2 | FallbackQueue | Queue Contact | Queue: [fallback queue] |
| E3 | FallbackMusic | Play Music | File: Default; Duration: 600 |
| E4 | FallbackDisconnect | Disconnect Contact | (terminal) |

### Event Flow Connections

| Source Activity | Port | Target Activity |
|----------------|------|-----------------|
| OnGlobalError | Out | ErrorAnnounce |
| ErrorAnnounce | Default | FallbackQueue |
| FallbackQueue | Default | FallbackMusic |
| FallbackMusic | Default | FallbackDisconnect |

## See Also

- [flow-designer-essentials.md](flow-designer-essentials.md) — the activities these blueprints are assembled from
- [flow-designer-flowir.md](flow-designer-flowir.md) — the FlowIR format the blueprints are written in
- [flow-designer-patterns.md](flow-designer-patterns.md) — patterns that extend the blueprints
