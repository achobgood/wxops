---
name: build-digital-inbound
description: |
  Build a Webex Connect flow for a digital inbound AI agent conversation.
  Handles SMS, WhatsApp, Apple Messages, RCS, Email, Live Chat, and Messenger
  Start triggers, Webex Engage conversation nodes, Process Message, multi-turn
  loops, human escalation via Queue Task, and cross-channel escalation to voice
  (CJDS transcript handoff).
  Use for: setting up a new digital channel to work with an AI agent for inbound
  customer conversations — the multi-turn chat loop with escalation.
  NOT for: single action flows (build-action), outbound notifications (build-notification), voice IVRs (design-flow).
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [channel-name]
---

# Build Digital Inbound Flow Workflow

## Step 1: Load references

YOU MUST use the Read tool on each of these files. Do not proceed to Step 2 until all reads are complete.

1. Read this skill's `reference.md` for the quick-reference cheat sheet
2. Read `docs/reference/digital-inbound.md` for the full architecture reference
3. Read `docs/playbooks/digital-inbound-agent.md` for the step-by-step playbook
4. Read `docs/reference/wxcc-platform.md` for WxCC routing and entry point setup
5. Read `docs/reference/ai-agent-studio.md` for agent configuration

**Checkpoint — do NOT proceed until you can answer these from the docs you just read:**
- What node creates the multi-turn conversation loop, and where does it connect back to? (from `digital-inbound.md`)
- What is the escalation node type and what queue parameter does it require? (from `digital-inbound-agent.md`)

If you cannot answer both, you skipped Step 1. Go back and read the docs.

## Step 2: Gather requirements

Ask the user ONE question at a time. Confirm all answers before proceeding.

### Required information:

1. **Channel**: Which digital channel? (SMS, WhatsApp, Live Chat, Email, FB Messenger, Apple Messages)
2. **AI Agent**: Which AI Agent from AI Agent Studio will handle conversations? (name)
3. **Agent Type**: Scripted or Autonomous?
4. **Escalation queue**: Which queue should human agent escalations go to?
5. **Rich responses**: Will the agent send rich content (cards, buttons, images) or text-only?

## Step 3: Create the Connect Flow — `[Webex Connect]`

1. Navigate to **Services** > select your service > **Flows**
2. Click **Create Flow**, name it (e.g., `whatsapp-inbound-agent`), click **Create**
3. The canvas opens with a green **Start** node

## Step 4: Configure the Start Node — `[Webex Connect -> Start node]`

1. Double-click the Start node
2. Select the channel-specific trigger from reference.md:

| Channel | Channel Section | Start Trigger |
|---------|----------------|--------------|
| SMS | Mobile Originated | Mobile Originated - MO |
| WhatsApp | WhatsApp | Incoming Message |
| Live Chat | Mobile & Web App | Incoming Message |
| Email | Email | Incoming Message |
| FB Messenger | Messenger | Incoming Message |
| Apple Messages | Apple Messages for Business | Incoming Message |

3. Note the message variable and customer ID variable for the selected channel (see reference.md channel triggers table)

## Step 5: Add Webex Engage Conversation Nodes — `[Webex Connect]`

1. Drag **Search Conversation** from the Webex CC Engage palette
2. Wire Start -> Search Conversation
3. Configure Search Conversation with the customer's channel identifier
4. Drag **Create Conversation**, **Append Conversation**, and **Reopen Conversation** nodes
5. Wire Search Conversation to all 5 exit paths:
   - `_noConversationFound` → Create Conversation
   - `_conversationActive` → Append Conversation
   - `_conversationClosed` → Reopen Conversation (or Create Conversation if unavailable)
   - `_conversationInQueue` → handle or log → End
   - `_conversationOnHold` → handle or log → End
6. Wire Create Conversation, Append Conversation, and Reopen Conversation outputs → AI Agent node

**Critical:** Create Conversation outputs `$(conversationId)` -- you will need this for Queue Task escalation later.

## Step 6: Configure the AI Agent Node — `[Webex Connect -> AI Agent node]`

1. Drag an **AI Agent** node onto the canvas
2. Set Method: **Process Message**
3. Set Agent Type: Scripted or Autonomous (from user's answer in Step 2)
4. Select the user's AI Agent from the dropdown
5. Set Message Variable: channel-specific message variable from Step 4
6. Set Channel: the channel name (e.g., "WhatsApp")
7. Set User Identifier: channel-specific customer ID from Step 4
8. (Optional) Configure Custom Parameters for customer profile data (scripted agents only on digital)

### Output variables to note:

| Variable | Description |
|----------|-------------|
| `TextResponse` | Text-only response (first text item) |
| `FullResponse` | Complete response array (rich elements) |
| `SessionId` | Conversation session ID -- MUST store and reuse |
| `MessageMetadata` | Metadata about the inbound message |
| `SessionMetadata` | Session-level metadata from the agent |
| `ResponsePayload` | Full response payload from the agent |

## Step 7: Add the Channel Reply Node — `[Webex Connect]`

1. Drag the channel-specific send node matching the Start trigger:

| Channel | Reply Node |
|---------|-----------|
| SMS | SMS |
| WhatsApp | WhatsApp |
| Live Chat | In-App Messaging |
| Email | Email |
| FB Messenger | Messenger |
| Apple Messages | Apple Messages for Business |

2. Wire AI Agent onSuccess -> Channel Reply
3. Configure:
   - Destination: customer's channel ID from Start node
   - Message: `$(nX.TextResponse)` for text-only, or parse `$(nX.FullResponse)` for rich content
   - Wait For: **Gateway Submit** (always)

## Step 8: Add the Receive Node (Conversation Loop) — `[Webex Connect]`

1. Drag a **Receive** node
2. Wire Channel Reply -> Receive
3. Configure Receive for the same channel as Start
4. Wire Receive output -> back to the AI Agent node
   - **SMS channels**: the Receive node's success exit is labeled `sms.mo` (not generic `onSuccess`) — wire `sms.mo` to the AI Agent node
5. **Critical**: On the second and subsequent AI Agent calls, pass the `SessionId` from the first call to maintain conversation context
6. Update the Message Variable on the AI Agent node to use the Receive node's output: `$(nX.{channel}.message)` for subsequent messages (e.g., `$(nX.whatsapp.message)`, `$(nX.sms.message)`) — there is no `.receive.` segment in the path

## Step 9: Configure Queue Task (Escalation) — `[Webex Connect]`

1. Drag a **Queue Task** node from the Webex CC Engage palette
2. Wire AI Agent onAgentHandover -> Queue Task
3. Configure:

| Field | Value |
|-------|-------|
| Task ID | `$(flid)` |
| Conversation ID | `$(conversationId)` from Create Conversation |
| Media Type | `Social` (SMS, WhatsApp, FB, Apple), `Email`, or `Chat` (Live Chat) |
| Media Channel | Select the originating channel from dropdown |
| Queue | Select the user's escalation queue |

4. Wire Queue Task exits:

| Exit | Route To |
|------|----------|
| `Queued` | End |
| `onError` | Error handling -> End |
| `onInvalidData` | Error handling -> End |
| `onInvalidChoice` | Error handling -> End |
| `onauthorizationfail` | Error handling -> End |
| `taskFailed` | Error handling -> End |
| `onTimeout` | Error handling -> End |

## Step 10: Wire Error and Timeout Paths — `[Webex Connect]`

1. Wire AI Agent onError -> error handling (log + optional "sorry" message via channel reply) -> End
2. Wire AI Agent onTimeOut -> timeout handling (send "please wait" or retry message) -> End
3. Wire AI Agent onInvalidCustomerID -> error handling -> End
4. Wire AI Agent onInvalidMessage -> error handling -> End

## Step 11: Save and Make Live — `[Webex Connect]`

1. Click **Save**
2. Click **Make Live** -- flow must be live to receive inbound messages
3. Verify the channel asset is linked to this service in Connect

## Step 12: Generate the configuration document

Present the full flow configuration to the user with:

1. Flow name and channel
2. Start trigger configuration
3. AI Agent node configuration (agent name, type, message variable, channel, user identifier)
4. Channel reply node configuration (destination, message source, wait mode)
5. Queue Task configuration (task ID, conversation ID, media type, channel, queue)
6. Complete flow diagram (see Step 13)
7. Testing instructions (channel-specific from reference.md)

## Step 13: Present to user

Show the complete flow diagram:

```
Start ({Channel} - Incoming Message)
  -> Search Conversation (customer ID: {variable})
    -> _conversationActive   -> Append Conversation  -+
    -> _noConversationFound  -> Create Conversation  -+
    -> _conversationClosed   -> Reopen Conversation  -+-> AI Agent (Process Message)
    -> _conversationInQueue  -> handle or log -> End  |
    -> _conversationOnHold   -> handle or log -> End  |
                                                      |
  AI Agent (Process Message: agent={name}, message={variable})
    -> onSuccess -----------> {Channel} Reply (TextResponse) -> Receive -> [loop to AI Agent]
    -> onAgentHandover -----> Queue Task (queue={name}) -> End
    -> onError -------------> Error handler -> End
    -> onTimeOut -----------> Timeout handler -> End
    -> onInvalidCustomerID -> Error handler -> End
    -> onInvalidMessage ----> Error handler -> End
```

Remind the user:

- Action flows (Start: AI Agent -> Receive -> HTTP Request -> Flow Outcomes) work for digital WITHOUT changes -- the same action flows used for voice work identically for digital
- SessionId must be stored and passed on each loop iteration to maintain conversation context
- The flow must be Made Live before testing
- Test by sending a message on the configured channel
- Engage nodes must be authorized in Control Hub before they will work

---

## CRITICAL REMINDERS

- **This is NOT an action flow** -- action flows use Start: AI Agent trigger, Receive node, HTTP Request, and Flow Outcomes. This is the parent conversation flow that orchestrates the full customer interaction.
- **Flow Designer is NOT used** for digital inbound -- the entire flow lives in Webex Connect. Flow Designer is voice only.
- **Queue Task, not Queue Contact** -- Queue Contact is for voice (Flow Designer). Queue Task is for digital (Connect).
- **SessionId is essential** for multi-turn conversations -- store it from the first AI Agent call and pass it back on every subsequent call.
- **$(conversationId) must come from Create Conversation** -- Queue Task needs the Conversation ID for escalation to work. Without it, escalation fails silently.
- **Channel-specific reply node** -- the reply node must match the Start trigger channel. WhatsApp Start -> WhatsApp Reply, SMS Start -> SMS Reply, etc.
- **Gateway Submit** for Wait For on all reply nodes -- never use Delivery Report in conversation flows.
- **Webex Engage nodes must be authorized** before use -- navigate to Assets → Integrations → Pre-built Integrations → Actions → Manage → Node Authorizations. The authorizing user must have a Contact Center License and Admin role.
- **Custom Parameters and MessageMetadata** -- only available for scripted agents on digital, not autonomous agents.
- **Customer Journey Data node** -- if the flow needs CJDS caller identification or journey tracking, use the native **Customer Journey Data** node (Flex 3 only). See `docs/playbooks/cjds-integration.md` for method-specific configuration, outcome branches, and output variables. Key gotcha: CJDS reads and writes use one host, `api.wxcc-{region}.cisco.com` (verified 2026-10-19 on `us1`). Until 2026-10-19 this line said reads use `api-jds.prod-{region}.ciscowxdap.com`; that host does not resolve (NXDOMAIN).
- **Cross-channel escalation (chat → voice)** -- if the user wants to escalate from digital chat to a voice call with a human agent, use the **Fetch Conversation Transcript** node (Update Conversation, method: Fetch transcript) to retrieve the full chat history, write it to CJDS as a `chat:transcript` event, then trigger an outbound voice call. The voice agent sees the transcript in the Customer Journey Widget. See `docs/playbooks/cross-channel-escalation.md` for the full pattern and `docs/reference/digital-inbound.md` §4b for the Fetch Transcript node.

## ANTI-HALLUCINATION GUARD

Every field name, header value, variable syntax, node name, and configuration detail in your output MUST appear verbatim in the docs you loaded in Step 1. If you are about to write something you did not read in the docs:

1. STOP and say "I don't have that documented — would you like me to do a web search to find the correct answer?"
2. Wait for the user's response before proceeding.
3. If they approve, use the WebSearch tool to find the answer from official Cisco/Webex documentation.
4. Present what you found and mark it as `[FROM WEB SEARCH — not yet in project docs]` so the user knows it hasn't been verified against the local reference.
5. Do NOT mix web search results into your output without that label.

Do not invent plausible-sounding platform details under any circumstances.
