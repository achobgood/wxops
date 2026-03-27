---
name: messaging-bots
description: |
  Build Webex bots and automated workflows: send notifications, create interactive
  adaptive card flows, set up webhooks, embed room tabs, and bridge calling + messaging.
  Guides from bot setup through card recipe selection, webhook configuration, and verification.
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [bot-task-type]
---

# Messaging Bots Workflow

**Checkpoint — do NOT proceed until you can answer these:**
1. What token does a bot use to send messages? (Answer: The bot's own access token from developer.webex.com — not an admin token. Each bot has a unique, non-expiring token generated at creation.)
2. How does a bot receive user interactions with adaptive cards? (Answer: Via `attachmentActions` webhook — the bot registers a webhook for `attachmentActions` resource with `created` event, then receives the card submission data.)

If you cannot answer both, you skipped reading this skill. Go back and read it.

## Step 1: Load references

1. Read `docs/reference/messaging-bots.md` for bot patterns, card recipes, attachment actions, room tabs
2. Read `docs/reference/webhooks-events.md` for webhook CRUD, messaging event payloads, bot webhook patterns (sections 4b and 6b)
3. Read `docs/reference/authentication.md` for auth token conventions

## Step 2: Verify auth token

Before any API calls, confirm the user has a working auth token:

```bash
wxcli whoami
```

If this fails, stop and resolve authentication first (`wxcli configure`).

### Token type detection

The `/people/me` response includes a `type` field:

| Token Type | `type` field | Suitable For |
|-----------|-------------|-------------|
| Bot | `bot` | Sending messages, receiving webhooks, card interactions |
| User | `person` | Testing, room tabs (requires moderator), all bot operations |
| Admin (personal) | `person` | CAN post to spaces if admin is a member — same as user token with elevated scopes |
| Service App | `appuser` | NOT suitable for sending messages — service app tokens cannot post to spaces |

<!-- NEEDS VERIFICATION: Confirm wxcli whoami exposes the type field -->

### Bot token scopes (fixed, cannot be expanded)

- `spark:messages_read` / `spark:messages_write` — read and send messages
- `spark:rooms_read` — list and read space details
- `spark:memberships_read` — list space members
- `spark:kms` — E2E encryption key management

**Warning:** If the user has a service app token and wants to send messages, they need to switch to a bot or user token. Service app tokens get 403 on message creation. Personal admin tokens (which are user tokens with elevated scopes) CAN post to spaces if the admin is a member of the space.

### Scope verification

After identifying the token type, verify the token has the scopes required for the user's task:

| Task Type | Required Scopes |
|-----------|----------------|
| Send notification | `spark:messages_write`, `spark:rooms_read` |
| Card interaction | `spark:messages_write`, `spark:rooms_read` + webhook callback URL |
| Webhook setup | `spark:messages_read` or `spark:rooms_read` (depends on resource) |
| Room tab | `spark:rooms_read`, `spark:rooms_write` (user token only) |
| Cross-domain (calling + messaging) | `spark:messages_write` + `spark:calls_read` (may need two tokens) |

**How to check:** Run `wxcli whoami` to confirm identity. `wxcli whoami` does not support `--output json` — it displays a formatted summary. For detailed token inspection, use `wxcli people show-me --output json`. Bot tokens have a fixed scope set (see above). For user/admin tokens, the scopes depend on the OAuth grant.

**If scopes are missing:**
- **Bot token:** Bot scopes are fixed at creation time. If the bot lacks a required scope, the user must create a new bot with the correct scopes at developer.webex.com.
- **User token:** The user must re-authorize with the required scopes in their OAuth flow.
- **Cross-domain:** If the task needs both messaging and calling scopes, the user likely needs two tokens — a bot token for messaging and a user/admin token for calling webhooks.

## Step 3: Identify task type

Ask the user what they want to build. Present this decision matrix if they are unsure:

| User Wants To | Task Type | Prerequisites |
|--------------|-----------|---------------|
| Send alerts/notifications to a space | **Send notification** | Bot/user token + bot is member of target space |
| Build an interactive card flow (approve/reject, forms) | **Card interaction** | Bot token + webhook callback URL + target space |
| Subscribe to messaging events | **Webhook setup** | Bot/user token + publicly accessible HTTPS webhook URL |
| Embed a web app in a space's tab bar | **Room tab** | User token (moderator) — NOT bot token |
| Bridge calling events to messaging | **Cross-domain** | Bot token + calling webhook + target space |

## Step 4: Check prerequisites

Before executing, verify these are in place:

### 4a. Bot token configured

```bash
wxcli whoami
```

If the response shows a bot display name and `type: bot`, the token is configured. If not:

```bash
wxcli configure
# Enter the bot's access token (from developer.webex.com → My Apps → Bot)
```

### 4b. Bot is a member of the target space

```bash
wxcli memberships list --room-id ROOM_ID --output json
```

Look for the bot's person ID in the membership list. If the bot is NOT a member, a **user** must add it:

```bash
wxcli memberships create --room-id ROOM_ID --person-email bot-name@webex.bot
```

**Critical:** Bots cannot add themselves to spaces. A user must invite the bot.

### 4c. Webhook callback URL available (for interactive bots)

The user must have a publicly accessible HTTPS endpoint to receive webhook events. Options:
- **Development:** ngrok (`ngrok http 8080` → use the HTTPS URL)
- **Production:** Cloud function (AWS Lambda, Google Cloud Functions), any HTTPS server

Ask: "Do you have a webhook callback URL? If not, we can set up notifications only (no interactive cards)."

### 4d. Target space exists

```bash
wxcli rooms show ROOM_ID --output json
```

If the space doesn't exist, create one:

```bash
wxcli rooms create --title "Bot Space"
```

Then add the bot to the new space (see 4b).

### 4e. Select card recipe (if applicable)

If the user's task involves sending rich messages or interactive cards, guide them to the right recipe:

| Use Case | Recipe | Interactive? |
|----------|--------|-------------|
| "Alert when X happens" | **Notification** — TextBlock + FactSet + Action.OpenUrl | No |
| "Get approval for X" | **Approval Flow** — FactSet + Action.Submit ×2 (Approve/Reject) | Yes |
| "Collect information from users" | **Form/Survey** — Input.Text + Input.ChoiceSet + Action.Submit | Yes |
| "Show status of X" | **Status Dashboard** — ColumnSet + styled TextBlocks | No |
| "Alert on-call engineer" | **Incident Alert** — Attention style + Action.Submit (Acknowledge) | Yes |
| "Let user pick from options" | **Dropdown Menu** — Input.ChoiceSet + Action.Submit | Yes |

#### After recipe selection

1. Load the complete JSON payload from `docs/reference/messaging-bots.md` Section 3
2. Customize placeholder values: room ID, field names, button labels, URLs
3. Build the `wxcli messages create --json-body '...'` command
4. **If the recipe is interactive** (uses Action.Submit): also set up webhooks (Step 6) and explain the attachment action response flow

#### Sending the card

```bash
wxcli messages create --json-body '{
  "roomId": "ROOM_ID",
  "text": "Fallback text for clients that cannot render cards",
  "attachments": [{
    "contentType": "application/vnd.microsoft.card.adaptive",
    "content": { ... customized card payload ... }
  }]
}'
```

**Critical:** The `text` field is REQUIRED even when sending a card. It's the fallback for email notifications and clients that can't render adaptive cards.

## Step 5: Build and present deployment plan [SHOW BEFORE EXECUTING]

Before executing any commands, compile a deployment plan and present it to the user for approval.

The plan must include:

1. **Task summary** — what we are building (task type from Step 3, card recipe from Step 4e if applicable)
2. **Token type** — bot / user / admin, and any scope gaps identified in Step 2
3. **Target space** — space name and ID
4. **Commands to execute** — the exact `wxcli` commands in execution order:
   - Message/card creation commands
   - Webhook creation commands (if interactive)
   - Room tab commands (if applicable)
   - Cross-domain calling webhook commands (if applicable)
5. **Verification steps** — what we will check after execution
6. **Risks or warnings** — scope gaps, rate limiting concerns, cross-domain token requirements

**Present the plan and wait for user approval before proceeding to Step 6.**

## Step 6: Execute via wxcli

After the user approves the deployment plan, execute the commands:

### 6a. Set up webhooks (if applicable)

For interactive bots that need to receive events:

**Create webhook for messages (so bot can "hear"):**

```bash
wxcli webhooks create \
  --name "Bot Messages" \
  --target-url "https://your-bot.com/webhook" \
  --resource messages \
  --event created
```

**Create webhook for card responses (if using adaptive cards with Action.Submit):**

```bash
wxcli webhooks create \
  --name "Bot Card Responses" \
  --target-url "https://your-bot.com/webhook" \
  --resource attachmentActions \
  --event created
```

**Verify webhooks are active:**

```bash
wxcli webhooks list --output json
```

Check that both webhooks show `"status": "active"`.

### 6b. Send messages and cards

Execute the message/card creation commands from the deployment plan. For cards, use the customized JSON payload built in Step 4e.

### 6c. The bot interaction loop

**Messages:**
1. User sends message mentioning @bot → webhook fires with message metadata (NO text for bot tokens)
2. Bot calls `wxcli messages show MESSAGE_ID` to get the actual message text
3. Bot processes and responds: `wxcli messages create --room-id ROOM_ID --text "Response"`

**Card responses:**
1. User clicks Action.Submit on a card → webhook fires with action metadata
2. Bot calls `wxcli attachment-actions show ACTION_ID` to get the user's input values
3. Bot processes inputs and responds

For full webhook CRUD, HMAC verification, auto-deactivation handling, and advanced filtering, see `docs/reference/webhooks-events.md`.

### 6d. Cross-domain dispatch (if applicable)

When the user's objective involves both Webex Calling and Messaging:

1. **Identify the calling component** — e.g., "monitor call queue overflow", "detect voicemail", "analyze CDR"
2. **Identify the messaging component** — e.g., "post alert to ops space", "send notification card", "create incident space"
3. **Load the appropriate calling skill** for the calling component:
   - Queue/feature monitoring → read `configure-features` skill
   - Call control/webhooks → read `call-control` skill
   - CDR/reporting → read `reporting` skill
4. **Use this skill** for the messaging component (card selection, webhook setup, message sending)

The cross-domain recipes in `docs/reference/messaging-bots.md` Section 7 provide the glue patterns:
- **Queue Alert → Space:** telephony_calls webhook → detect threshold → send incident card to ops space
- **Voicemail → Notification:** telephony_mwi webhook → send notification card to user's 1:1 space
- **Incident Response:** detect issue → create space → add responders → post diagnostics card

**Important:** Calling webhooks require `spark:calls_read` scope, which is separate from bot messaging scopes. The user may need two different tokens (bot token for messaging, user/admin token for calling webhooks) or a user token that has both scope sets.

## Step 7: Verify

### For notification bots (no interaction)

1. Send a test message:
```bash
wxcli messages create --room-id ROOM_ID --text "Test notification from bot"
```
2. Verify the message appears in the Webex App
3. Send a test card (if applicable):
```bash
wxcli messages create --json-body '{ ... card payload ... }'
```
4. Verify the card renders correctly in the Webex App

### For interactive bots

1. Send a card with Action.Submit buttons
2. Click a button in the Webex App
3. Verify the webhook received the attachment action event (user must check their webhook endpoint)
4. Retrieve the action to confirm input capture:
```bash
wxcli attachment-actions show ACTION_ID --output json
```
5. Verify the `inputs` field contains the expected key-value pairs

### For room tabs

```bash
wxcli room-tabs create --room-id ROOM_ID --content-url "https://your-app.com/dashboard" --display-name "Dashboard"
wxcli room-tabs list --room-id ROOM_ID --output json
```

Verify the tab appears in the space's tab bar in the Webex App.

## Step 8: Report results

```
BOT DEPLOYMENT COMPLETE
Task type: [notification / card interaction / webhook setup / room tab / cross-domain]
Token type: [bot / user]

Resources created:
- Webhooks: [count] ([names])
- Cards sent: [count] to [space name]
- Room tabs: [count]

Verification:
- Messages delivered: [✓/✗]
- Cards rendered: [✓/✗]
- Webhooks active: [✓/✗]
- Card responses captured: [✓/✗] (if interactive)

Next steps:
- [Context-specific follow-up, e.g., "Implement webhook handler at your callback URL"]
- [Additional cards or spaces to configure]
```

Wait for user confirmation before proceeding to any additional steps.

## Critical Rules

These are non-negotiable. Violating them causes silent failures or broken bot behavior.

1. **Always verify bot is a member** of the target space before sending messages. Sending to a space the bot isn't in returns 403.

2. **Bot tokens cannot add themselves to spaces.** A user must invite the bot. Don't attempt `wxcli memberships create` with a bot token to add the bot itself.

3. **Adaptive cards REQUIRE the `text` field** as fallback. Never send a card without `text` — email notifications and older clients won't show anything.

4. **Card payloads must be under 4KB.** Cards exceeding this silently fail to render. If a card is too large, split into multiple messages or simplify the layout.

5. **`Action.Execute` (Adaptive Cards 1.4+) is NOT supported** by Webex. Use `Action.Submit` instead. Cards with Action.Execute will render but the button won't work.

6. **Webhook `targetUrl` must be publicly accessible HTTPS.** No HTTP, no localhost (unless tunneled via ngrok or similar). Webhooks to unreachable URLs silently fail.

7. **Bot `messages` webhooks do NOT include message text.** This is a Webex security measure. The bot must call `wxcli messages show MESSAGE_ID` to get the actual content. This is THE standard bot pattern — don't skip it.

8. **Webhooks auto-deactivate after repeated delivery failures.** If the callback URL returns errors, Webex sets the webhook to `inactive`. Reactivate with `wxcli webhooks update WEBHOOK_ID --status active`. Monitor webhook status periodically.

9. **Cross-domain calling webhooks need `spark:calls_read` scope.** This is separate from bot messaging scopes. A bot token doesn't have this scope — the user may need a separate user token for calling webhooks.

10. **Room tabs require a moderator-level user token, NOT a bot token.** Bot tokens get 403 on room tab operations. Always use a user token for tab management.

11. **Rate limiting:** Add `sleep 1` between rapid message sends or webhook creates. Webex messaging APIs enforce rate limits (~5 requests/second for bots). Exceeding the limit returns 429.

## Context Compaction Recovery

If context compacts during a session:

1. Read `docs/plans/` to find the current deployment plan
2. Check what webhooks exist: `wxcli webhooks list --output json`
3. Check what messages were sent (if tracking IDs in the plan)
4. Resume from the next pending step
5. Tell the user:

> "I recovered from a context reset. Based on your deployment plan at [path], we've completed steps 1-N and need to resume at step N+1: [description]. Ready to continue?"
