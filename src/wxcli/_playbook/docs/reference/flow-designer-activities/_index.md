# Flow Designer — Situational Activities Index

<!-- ref-tag: fd-act-index-v1 -->

> Essential activities (Play Message, Play Music, Set Variable, Queue Contact, Disconnect Contact, Variable Types, Output Variables, Global Events) are in [flow-designer-essentials.md](../flow-designer-essentials.md).
>
> Patterns and advanced topics are in [flow-designer-patterns.md](../flow-designer-patterns.md).

**Adding a new activity:** Create a new `.md` file in this directory (kebab-case name, e.g., `new-activity.md`). Start it with `## Activity Name` as an H2 heading. Then add a row to the table below. Do NOT append to an existing file.

| File | Activity | Purpose |
|------|----------|---------|
| [advanced-queue-information.md](advanced-queue-information.md) | Advanced Queue Information | Returns real-time agent counts and queue position |
| [blind-transfer.md](blind-transfer.md) | Blind Transfer | Transfers a call to an external DN (terminal node) |
| [bre-request.md](bre-request.md) | BRE Request | Invokes Business Rules Engine for key-value lookups |
| [bridged-transfer.md](bridged-transfer.md) | Bridged Transfer | Temporarily transfers to external DN, retains flow control |
| [business-hours.md](business-hours.md) | Business Hours | Routes based on configured business hours schedule |
| [call-progress-analysis.md](call-progress-analysis.md) | Call Progress Analysis | Detects live person vs answering machine on outbound calls |
| [callback.md](callback.md) | Callback | Registers immediate courtesy callback, keeps queue position |
| [case.md](case.md) | Case | Branches on a variable's value (switch/case) |
| [collect-digits.md](collect-digits.md) | Collect Digits | Collects DTMF input for auth, data entry, or navigation |
| [condition.md](condition.md) | Condition | Evaluates expression, routes to TRUE or FALSE branch |
| [cryptographic-hash.md](cryptographic-hash.md) | Cryptographic Hash | Generates one-way SHA256/SHA512 hash with optional salt (payload integrity) |
| [custom-connectors.md](custom-connectors.md) | Custom Connectors | Managed auth for calling third-party APIs from flows |
| [end-flow.md](end-flow.md) | End Flow | Terminates flow without disconnecting the call |
| [escalate-cdg.md](escalate-cdg.md) | Escalate Call Distribution Group | Widens agent pool by escalating to next CDG in queue |
| [feedback-v2.md](feedback-v2.md) | Feedback V2 | Post-call IVR survey (CSAT/NPS) via DTMF |
| [feedback.md](feedback.md) | Feedback (Legacy) | Legacy survey activity; prefer Feedback V2 |
| [functions-activity.md](functions-activity.md) | Functions | Executes custom JS or Python code within a flow |
| [generate-otp.md](generate-otp.md) | Generate OTP | Generates a one-time password for 2FA/MFA; pairs with Verify OTP |
| [get-queue-info.md](get-queue-info.md) | Get Queue Info | Retrieves EWT and position in queue metrics |
| [global-event-output-variables.md](global-event-output-variables.md) | Global Event Output Variables | Variables associated with event handlers |
| [goto.md](goto.md) | GoTo | Transfers call to a different flow or entry point (terminal) |
| [http-connector.md](http-connector.md) | HTTP Connector | Managed auth for calling WxCC APIs from flows |
| [last-agent-removed.md](last-agent-removed.md) | Last Agent Removed (Event) | Fires when the last agent is removed from the interaction (**stub — pending verification**) |
| [http-request.md](http-request.md) | HTTP Request | Makes outbound HTTP calls to external APIs |
| [menu.md](menu.md) | Menu | Plays prompt and routes based on DTMF digit pressed |
| [outdial-entry-point.md](outdial-entry-point.md) | Outdial Entry Point | Restricted activity set for outbound campaign flows |
| [parse.md](parse.md) | Parse | Extracts values from JSON/XML/TOML/YAML responses |
| [percentage-allocation.md](percentage-allocation.md) | Percentage Allocation | Splits traffic by percentage (A/B testing, migrations) |
| [queue-to-agent.md](queue-to-agent.md) | Queue To Agent | Routes contact directly to a specific agent by ID/email |
| [receive-message.md](receive-message.md) | Receive Message | Waits for a customer message on a BYOC custom messaging channel (**from live registry — Cisco docs beta-gated**) |
| [record.md](record.md) | Record | Records caller audio (voicemail, confirmations) |
| [recording-control.md](recording-control.md) | Recording Control | Toggles call recording on/off based on consent |
| [reservation-start.md](reservation-start.md) | Reservation Start (Event) | Fires when the routing engine reserves an agent for a contact (**stub — pending verification**) |
| [schedule-callback.md](schedule-callback.md) | Schedule Callback | Registers a future callback request |
| [screen-pop.md](screen-pop.md) | Screen Pop | Pops a URL to the agent desktop on contact offer |
| [self-loop-limits.md](self-loop-limits.md) | Self-Loop Limits | System limits on activity self-loops to prevent infinites |
| [send-custom-message.md](send-custom-message.md) | Send Custom Message | Sends a message on a BYOC custom messaging channel (**from live registry — Cisco docs beta-gated**) |
| [send-digits.md](send-digits.md) | Send Digits | Sends DTMF tones during an active call |
| [set-announcement.md](set-announcement.md) | Set Announcement | Configures compliance, greeting, and whisper announcements |
| [set-caller-id.md](set-caller-id.md) | Set Caller ID | Customizes outbound caller ID for transfers |
| [set-contact-priority.md](set-contact-priority.md) | Set Contact Priority | Assigns priority level to control queue position |
| [set-whisper.md](set-whisper.md) | Set Whisper Announcement | Plays agent-only announcement before connecting caller |
| [start-media-stream.md](start-media-stream.md) | Start Media Stream | Streams live call audio to a configured media destination |
| [upload-audio.md](upload-audio.md) | Upload Audio | Uploads audio file (e.g., agent personal greeting) |
| [verify-otp.md](verify-otp.md) | Verify OTP | Validates a user-provided OTP against the Generate OTP transaction reference |
| [virtual-agent-legacy.md](virtual-agent-legacy.md) | Virtual Agent (Legacy) | Dialogflow ES integration; prefer Virtual Agent V2 |
| [virtual-agent-v2.md](virtual-agent-v2.md) | Virtual Agent V2 | Real-time conversational AI within the IVR flow |
| [wait.md](wait.md) | Wait | Pauses flow execution for a specified duration |
