<!-- Created by playbook session 2026-03-19 -->
# Messaging Bots & Adaptive Cards Reference

Developer reference for building Webex bots and integrations. Covers bot fundamentals, adaptive card patterns, the `attachment-actions` and `room-tabs` CLI groups, and cross-domain calling + messaging recipes.

For space/team/membership CRUD, see [`messaging-spaces.md`](messaging-spaces.md).

---

## 1. Bot Fundamentals

A Webex bot is a special Webex user with its own always-on access token — no human login, no session expiry. Bots are created at [developer.webex.com](https://developer.webex.com) → My Apps → Create a Bot.

### What a Bot Can and Cannot Do

| Capability | Bot Token | User Token | Admin Token |
|-----------|-----------|-----------|-------------|
| Send messages | Yes (spaces it's in) | Yes (spaces they're in) | No |
| Create spaces | Yes | Yes | Yes |
| Join spaces | No (must be added by a user) | Yes (if invited or discoverable) | N/A |
| Create teams | No | Yes | Yes |
| Manage memberships | No (except removing self) | Yes (if moderator) | Yes |
| See all messages | Only @mentions + 1:1 | All in their spaces | Compliance API only |
| Admin operations | No | No | Yes |
| Use `spark-admin:` scopes | No | No | Yes |

### Bot Token Scopes

Bot tokens have a fixed scope set — you cannot request additional scopes:

- `spark:messages_read` — read messages in spaces the bot belongs to
- `spark:messages_write` — send messages to spaces
- `spark:rooms_read` — list and read space details
- `spark:memberships_read` — list space members
- `spark:kms` — required for E2E encryption key management

### Configuring a Bot Token

```bash
wxcli configure
# Enter the bot's access token when prompted
wxcli whoami  # Verify — should show the bot's display name
```

### Detecting Token Type from `wxcli whoami`

The `/people/me` endpoint (called by `wxcli whoami`) returns a `type` field:

| Token Type | `type` field | Notes |
|-----------|-------------|-------|
| Bot | `bot` | Display name often ends with "(bot)" or similar; email is bot-specific |
| User | `person` | Normal human name and email |
| Admin | `person` | Same as user — admin privileges come from scopes and org roles, not token type |

The key discriminator: if `type` is `bot`, it is a bot token. If `type` is `person`, check the intended scopes — admin vs. regular user depends on token scopes, not the `/people/me` type field.

<!-- NEEDS VERIFICATION: Confirm that `wxcli whoami` exposes the `type` field from /people/me response. If it only shows a subset of fields, document which fields are visible and how to distinguish bot from user. -->

---

## 2. Sending Messages

Three tiers of message complexity. Plain text and markdown use direct CLI options. Adaptive cards require `--json-body`.

| Tier | Format | CLI Approach |
|------|--------|-------------|
| Plain text | `--text "Hello"` | Direct CLI option |
| Markdown | `--markdown "**Bold**"` | Direct CLI option |
| Adaptive card | `--json-body '{...}'` | JSON body required |

For plain text (`--text`) and markdown (`--markdown`) message patterns, see [`messaging-spaces.md`](messaging-spaces.md).

### Adaptive Card

```bash
wxcli messages create --json-body '{
  "roomId": "ROOM_ID",
  "text": "Fallback text for clients that cannot render cards",
  "attachments": [{
    "contentType": "application/vnd.microsoft.card.adaptive",
    "content": { ... card payload ... }
  }]
}'
```

**Critical:** The `text` field is required even when sending a card. It is the fallback for clients that cannot render adaptive cards (email notifications, older Webex versions, API consumers). Omitting it is not an error but the card may be invisible to some recipients.

For the complete card payload, see the recipe catalog in Section 3.

---

## 3. Adaptive Card Recipe Catalog

Each recipe below is copy-paste ready. Replace `ROOM_ID` with the target space ID.

For interactive recipes (those with `Action.Submit`): the user's card response is captured via webhook (`attachmentActions` resource) and retrieved with `wxcli attachment-actions show ACTION_ID`. See Section 5.

---

### Recipe 1: Notification Card

**Use case:** CI/CD alerts, monitoring notifications, status updates — informational only, no user input.

**What it looks like:** A title in large bold text, a fact table with key-value details (repo, branch, status), and a "View Dashboard" button that opens a URL.

```bash
wxcli messages create --json-body '{
  "roomId": "ROOM_ID",
  "text": "Build notification",
  "attachments": [{
    "contentType": "application/vnd.microsoft.card.adaptive",
    "content": {
      "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
      "type": "AdaptiveCard",
      "version": "1.3",
      "body": [
        {
          "type": "TextBlock",
          "text": "Build Passed",
          "size": "Large",
          "weight": "Bolder",
          "color": "Good"
        },
        {
          "type": "FactSet",
          "facts": [
            {"title": "Repository", "value": "myapp"},
            {"title": "Branch", "value": "main"},
            {"title": "Commit", "value": "a1b2c3d"},
            {"title": "Duration", "value": "2m 14s"}
          ]
        }
      ],
      "actions": [
        {
          "type": "Action.OpenUrl",
          "title": "View Dashboard",
          "url": "https://ci.example.com/builds/123"
        }
      ]
    }
  }]
}'
```

No webhook needed — this card has no user input.

---

### Recipe 2: Approval Flow

**Use case:** Change approvals, expense approvals, access requests.

**What it looks like:** A title, description, a fact table with request details, and two buttons: "Approve" and "Reject". Clicking either fires a webhook.

```bash
wxcli messages create --json-body '{
  "roomId": "ROOM_ID",
  "text": "Approval request pending",
  "attachments": [{
    "contentType": "application/vnd.microsoft.card.adaptive",
    "content": {
      "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
      "type": "AdaptiveCard",
      "version": "1.3",
      "body": [
        {
          "type": "TextBlock",
          "text": "Change Approval Required",
          "size": "Large",
          "weight": "Bolder"
        },
        {
          "type": "TextBlock",
          "text": "A change request requires your approval.",
          "wrap": true
        },
        {
          "type": "FactSet",
          "facts": [
            {"title": "Requester", "value": "Alice Smith"},
            {"title": "Change ID", "value": "CHG-00412"},
            {"title": "Description", "value": "Upgrade firewall firmware"},
            {"title": "Window", "value": "2026-03-20 02:00 UTC"}
          ]
        }
      ],
      "actions": [
        {
          "type": "Action.Submit",
          "title": "Approve",
          "data": {"decision": "approved", "changeId": "CHG-00412"}
        },
        {
          "type": "Action.Submit",
          "title": "Reject",
          "style": "destructive",
          "data": {"decision": "rejected", "changeId": "CHG-00412"}
        }
      ]
    }
  }]
}'
```

**Handling the response:**

1. Set up a webhook for `attachmentActions` resource (see Section 8).
2. When the user clicks Approve or Reject, your webhook receives the action ID.
3. Retrieve the response:

```bash
wxcli attachment-actions show ACTION_ID
```

The `inputs` field will contain the `data` values from the button clicked, e.g. `{"decision": "approved", "changeId": "CHG-00412"}`.

---

### Recipe 3: Form / Survey

**Use case:** Feedback collection, incident reports, onboarding forms.

**What it looks like:** A form with a text input, a dropdown selection, a date picker, and a Submit button.

```bash
wxcli messages create --json-body '{
  "roomId": "ROOM_ID",
  "text": "Feedback form",
  "attachments": [{
    "contentType": "application/vnd.microsoft.card.adaptive",
    "content": {
      "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
      "type": "AdaptiveCard",
      "version": "1.3",
      "body": [
        {
          "type": "TextBlock",
          "text": "Service Feedback",
          "size": "Large",
          "weight": "Bolder"
        },
        {
          "type": "Input.Text",
          "id": "comments",
          "placeholder": "Describe your experience",
          "isMultiline": true,
          "label": "Comments"
        },
        {
          "type": "Input.ChoiceSet",
          "id": "rating",
          "label": "Overall Rating",
          "style": "compact",
          "choices": [
            {"title": "5 - Excellent", "value": "5"},
            {"title": "4 - Good", "value": "4"},
            {"title": "3 - Average", "value": "3"},
            {"title": "2 - Poor", "value": "2"},
            {"title": "1 - Very Poor", "value": "1"}
          ]
        },
        {
          "type": "Input.Date",
          "id": "incidentDate",
          "label": "Date of Incident (if applicable)"
        }
      ],
      "actions": [
        {
          "type": "Action.Submit",
          "title": "Submit Feedback"
        }
      ]
    }
  }]
}'
```

**Retrieving form inputs:**

```bash
wxcli attachment-actions show ACTION_ID
# Response inputs: {"comments": "...", "rating": "4", "incidentDate": "2026-03-19"}
```

---

### Recipe 4: Status Dashboard

**Use case:** System status boards, deployment progress, call queue metrics.

**What it looks like:** A two-column layout. Left column shows service names; right column shows colored status indicators (green = operational, red = degraded).

```bash
wxcli messages create --json-body '{
  "roomId": "ROOM_ID",
  "text": "System status update",
  "attachments": [{
    "contentType": "application/vnd.microsoft.card.adaptive",
    "content": {
      "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
      "type": "AdaptiveCard",
      "version": "1.3",
      "body": [
        {
          "type": "TextBlock",
          "text": "System Status — 2026-03-19 14:30 UTC",
          "size": "Medium",
          "weight": "Bolder"
        },
        {
          "type": "ColumnSet",
          "columns": [
            {
              "type": "Column",
              "width": "stretch",
              "items": [
                {"type": "TextBlock", "text": "API Gateway", "weight": "Bolder"},
                {"type": "TextBlock", "text": "Call Queue"},
                {"type": "TextBlock", "text": "Voicemail"},
                {"type": "TextBlock", "text": "Recording"}
              ]
            },
            {
              "type": "Column",
              "width": "auto",
              "items": [
                {"type": "TextBlock", "text": "Operational", "color": "Good"},
                {"type": "TextBlock", "text": "Degraded", "color": "Attention"},
                {"type": "TextBlock", "text": "Operational", "color": "Good"},
                {"type": "TextBlock", "text": "Operational", "color": "Good"}
              ]
            }
          ]
        },
        {
          "type": "TextBlock",
          "text": "Call Queue: elevated latency detected. Engineering investigating.",
          "wrap": true,
          "color": "Attention",
          "size": "Small"
        }
      ]
    }
  }]
}'
```

No webhook needed — informational only.

---

### Recipe 5: Incident Alert

**Use case:** PagerDuty-style on-call alerts, calling queue overflow notifications.

**What it looks like:** A red-accented header, incident details table, an "Acknowledge" button (Action.Submit) and a "View Runbook" button (Action.OpenUrl).

```bash
wxcli messages create --json-body '{
  "roomId": "ROOM_ID",
  "text": "INCIDENT: High priority alert — action required",
  "attachments": [{
    "contentType": "application/vnd.microsoft.card.adaptive",
    "content": {
      "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
      "type": "AdaptiveCard",
      "version": "1.3",
      "body": [
        {
          "type": "TextBlock",
          "text": "INCIDENT: Call Queue Overflow",
          "size": "Large",
          "weight": "Bolder",
          "color": "Attention"
        },
        {
          "type": "TextBlock",
          "text": "Queue wait time exceeded threshold. Immediate action required.",
          "wrap": true
        },
        {
          "type": "FactSet",
          "facts": [
            {"title": "Queue", "value": "Support — Tier 1"},
            {"title": "Wait Time", "value": "18 minutes"},
            {"title": "Calls Waiting", "value": "24"},
            {"title": "Agents Available", "value": "2"},
            {"title": "Incident ID", "value": "INC-20260319-001"}
          ]
        }
      ],
      "actions": [
        {
          "type": "Action.Submit",
          "title": "Acknowledge",
          "data": {"action": "acknowledge", "incidentId": "INC-20260319-001"}
        },
        {
          "type": "Action.OpenUrl",
          "title": "View Runbook",
          "url": "https://wiki.example.com/runbooks/call-queue-overflow"
        }
      ]
    }
  }]
}'
```

**Handling acknowledgement:** Set up a webhook for `attachmentActions`. When the on-call engineer clicks Acknowledge, retrieve the response with `wxcli attachment-actions show ACTION_ID` and update your incident management system.

---

### Recipe 6: Dropdown Menu

**Use case:** Configuration selection, routing preference, environment targeting. The simplest interactive pattern — good starting point for any bot that needs a single user choice.

```bash
wxcli messages create --json-body '{
  "roomId": "ROOM_ID",
  "text": "Please select a deployment target",
  "attachments": [{
    "contentType": "application/vnd.microsoft.card.adaptive",
    "content": {
      "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
      "type": "AdaptiveCard",
      "version": "1.3",
      "body": [
        {
          "type": "TextBlock",
          "text": "Select Deployment Target",
          "size": "Medium",
          "weight": "Bolder"
        },
        {
          "type": "Input.ChoiceSet",
          "id": "environment",
          "label": "Environment",
          "style": "compact",
          "placeholder": "Choose...",
          "choices": [
            {"title": "Development", "value": "dev"},
            {"title": "Staging", "value": "staging"},
            {"title": "Production", "value": "prod"}
          ]
        }
      ],
      "actions": [
        {
          "type": "Action.Submit",
          "title": "Deploy"
        }
      ]
    }
  }]
}'
```

**Retrieving the selection:**

```bash
wxcli attachment-actions show ACTION_ID
# Response inputs: {"environment": "staging"}
```

---

## 4. Webex Adaptive Cards — Supported Features and Gaps

Webex supports **Adaptive Cards schema version 1.3**.

<!-- NEEDS VERIFICATION: Confirm exact Webex Adaptive Cards support level and gaps against https://developer.webex.com/docs/buttons-and-cards -->

### Supported Elements

| Category | Elements |
|----------|---------|
| Container | `AdaptiveCard`, `Container`, `ColumnSet`, `Column`, `ActionSet` |
| Display | `TextBlock`, `RichTextBlock`, `TextRun`, `Image`, `ImageSet`, `FactSet` |
| Input | `Input.Text`, `Input.Number`, `Input.Date`, `Input.Time`, `Input.Toggle`, `Input.ChoiceSet` |
| Actions | `Action.Submit`, `Action.OpenUrl`, `Action.ShowCard`, `Action.ToggleVisibility` |

### Known Gaps

| Feature | Status | Workaround |
|---------|--------|-----------|
| `Media` element | Not supported | Link to media via `Action.OpenUrl` instead |
| `Action.Execute` (v1.4+) | Not supported | Use `Action.Submit` |
| `fallback` property on elements | Partially supported; behavior inconsistent across clients | Test on all target clients |
| `fallbackText` card property | Not supported | Use `text` field on the message instead |
| `requires` property | Not supported | — |
| `speak` property | Not supported | — |
| `ColumnSet` `height` property | Not supported | — |
| Card actions limit | Max 20 actions per card | Use `ActionSet` inside containers to distribute actions |
| Card payload size | 4KB maximum | Cards larger than 4KB silently fail to render; keep fact sets and text compact |

### Rendering Notes

Card rendering varies between Webex desktop, mobile, and web clients. Test interactive cards (inputs, buttons) on all target client types. The `color` property on TextBlock (`Good`, `Attention`, `Warning`, `Accent`, `Dark`, `Light`) renders differently on light vs. dark themes.

### References

- Full Adaptive Cards schema reference: [adaptivecards.io/explorer/](https://adaptivecards.io/explorer/)
- Webex Cards guide: [developer.webex.com/docs/buttons-and-cards](https://developer.webex.com/docs/buttons-and-cards)
- Webex Buttons and Cards Designer: [developer.webex.com/buttons-and-cards-designer](https://developer.webex.com/buttons-and-cards-designer)

---

## 5. Attachment Actions (`attachment-actions` CLI group — 2 commands)

Attachment actions represent a user's response to an adaptive card `Action.Submit` button. This is how bots receive user input from cards.

### Command Reference

| Command | What It Does |
|---------|-------------|
| `wxcli attachment-actions create-an-attachment` | Submit a card response programmatically (testing/automation) |
| `wxcli attachment-actions show ACTION_ID` | Get a user's card response and input values |

### The Card Interaction Flow

```
1. Bot sends message with adaptive card
   wxcli messages create --json-body '{"roomId":"...","text":"fallback","attachments":[...]}'

2. User clicks Action.Submit in the card
   → Webex fires webhook: resource=attachmentActions, event=created

3. Webhook payload contains the action ID

4. Bot retrieves the user's inputs
   wxcli attachment-actions show ACTION_ID

5. Bot processes inputs and sends follow-up message
```

### Command Details

**Get attachment action details:**

```bash
wxcli attachment-actions show ACTION_ID
```

Response fields:

| Field | Description |
|-------|-------------|
| `id` | The attachment action ID (from the webhook payload) |
| `type` | Always `submit` |
| `messageId` | ID of the message that contained the card |
| `inputs` | Object with key-value pairs from the card's input fields |
| `personId` | ID of the person who submitted the response |
| `roomId` | ID of the space where the card was submitted |
| `created` | Timestamp of submission |

**Create an attachment action (programmatic/testing):**

```bash
wxcli attachment-actions create-an-attachment \
  --type submit \
  --message-id MSG_ID \
  --json-body '{"type":"submit","messageId":"MSG_ID","inputs":{"decision":"approved"}}'
```

For complex input payloads, use `--json-body` to pass the full body directly.

### Retrieving Inputs by Recipe

After `wxcli attachment-actions show ACTION_ID`, the `inputs` field maps to the `id` values defined in your card's input elements:

| Recipe | `inputs` example |
|--------|-----------------|
| Approval Flow (Recipe 2) | `{"decision": "approved", "changeId": "CHG-00412"}` |
| Form/Survey (Recipe 3) | `{"comments": "Great service", "rating": "4", "incidentDate": "2026-03-19"}` |
| Incident Alert (Recipe 5) | `{"action": "acknowledge", "incidentId": "INC-20260319-001"}` |
| Dropdown Menu (Recipe 6) | `{"environment": "staging"}` |

---

## 6. Room Tabs (`room-tabs` CLI group — 5 commands)

> **Room tabs require a user token (moderator), NOT a bot token.** Bot tokens cannot create or manage room tabs. The authenticated user must be a moderator of the space.

Room tabs embed web content — dashboards, wikis, tools, status pages — directly in a Webex space's tab bar. Users in the space can access the embedded content without leaving Webex.

### Command Reference

| Command | What It Does |
|---------|-------------|
| `wxcli room-tabs list --room-id ROOM_ID` | List all tabs in a space |
| `wxcli room-tabs create --room-id ROOM_ID --content-url URL --display-name "Name"` | Add a tab to a space |
| `wxcli room-tabs show TAB_ID` | Get tab details (URL, display name, creator) |
| `wxcli room-tabs update TAB_ID [--content-url URL] [--display-name "Name"]` | Update tab URL or display name |
| `wxcli room-tabs delete TAB_ID` | Remove a tab from a space |

### Command Details

**List tabs in a space:**

```bash
wxcli room-tabs list --room-id ROOM_ID
```

**Create a tab:**

```bash
wxcli room-tabs create \
  --room-id ROOM_ID \
  --content-url "https://dashboard.example.com/calls" \
  --display-name "Call Dashboard"
```

- `--content-url` must use HTTPS
- `--display-name` is the label shown in the tab bar
- All three options are required for `create`

**Update a tab:**

```bash
wxcli room-tabs update TAB_ID --content-url "https://dashboard.example.com/v2/calls"
```

Only include the options you want to change.

**Delete a tab:**

```bash
wxcli room-tabs delete TAB_ID --force
```

Without `--force`, the CLI prompts for confirmation.

---

## 7. Cross-Domain Recipes (Calling + Messaging)

These patterns bridge Webex Calling events with Webex Messaging to build integrated workflows.

### Recipe A: Call Queue Alert → Space Notification

Trigger a card notification to an ops space when a call queue exceeds a wait time threshold.

```
1. Create webhook for telephony_calls events (see webhooks-events.md)
   wxcli webhooks create \
     --name "Queue Monitor" \
     --target-url https://your-bot.com/webhook \
     --resource telephony_calls \
     --event updated

2. In webhook handler, parse event data:
   - Check queue wait time or overflow status
   - If threshold exceeded, trigger notification

3. Send incident alert card to ops space:
   wxcli messages create --json-body '{
     "roomId": "OPS_SPACE_ROOM_ID",
     "text": "Queue overflow alert",
     "attachments": [{ ... Recipe 5 incident alert payload ... }]
   }'

4. Capture acknowledgement via attachmentActions webhook
   wxcli attachment-actions show ACTION_ID
```

### Recipe B: Voicemail → 1:1 Space Notification

Notify a user in their 1:1 bot space when they receive a new voicemail.

```
1. Create webhook for voicemail events
   wxcli webhooks create \
     --name "Voicemail Notifier" \
     --target-url https://your-bot.com/webhook \
     --resource telephony_mwi \
     --event updated

2. In webhook handler, extract:
   - personId (who received the voicemail)
   - caller info, timestamp

3. Create or look up the 1:1 space between bot and user
   wxcli messages create --to-person-id PERSON_ID --text "You have a new voicemail"
   # Creating a message to a person ID creates the 1:1 space automatically

4. Send notification card with caller details and portal link:
   wxcli messages create --json-body '{
     "toPersonId": "PERSON_ID",
     "text": "New voicemail",
     "attachments": [{
       "contentType": "application/vnd.microsoft.card.adaptive",
       "content": {
         "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
         "type": "AdaptiveCard",
         "version": "1.3",
         "body": [
           {"type": "TextBlock", "text": "New Voicemail", "weight": "Bolder", "size": "Medium"},
           {
             "type": "FactSet",
             "facts": [
               {"title": "From", "value": "{{callerName}}"},
               {"title": "Number", "value": "{{callerNumber}}"},
               {"title": "Received", "value": "{{timestamp}}"}
             ]
           }
         ],
         "actions": [
           {"type": "Action.OpenUrl", "title": "Listen to Voicemail", "url": "https://calling.webex.com/voicemail"}
         ]
       }
     }]
   }'
```

### Recipe C: Automated Incident Response

When a calling issue is detected, automatically create an incident space, add responders, and post a diagnostics card.

```
1. Detect the calling issue (CDR anomaly, webhook pattern, monitoring alert)

2. Create a dedicated incident space:
   wxcli rooms create --title "Incident-2026-03-19-CQ-Overflow"

3. Add on-call responders by email:
   wxcli memberships create --room-id ROOM_ID --person-email oncall@example.com
   wxcli memberships create --room-id ROOM_ID --person-email teamlead@example.com

4. Post a status dashboard card with diagnostics:
   wxcli messages create --room-id ROOM_ID --json-body '{
     ... Recipe 4 status dashboard payload with current metrics ...
   }'

5. Post a follow-up incident alert card with Acknowledge + Runbook buttons:
   wxcli messages create --room-id ROOM_ID --json-body '{
     ... Recipe 5 incident alert payload ...
   }'

6. Pin important messages and track acknowledgements via attachmentActions webhooks
```

For space and membership management commands (`rooms create`, `memberships create`), see [`messaging-spaces.md`](messaging-spaces.md).

---

## 8. Webhook Signpost

For full webhook CRUD, event setup, messaging resource event payloads, bot webhook patterns, and HMAC verification, see [`webhooks-events.md`](webhooks-events.md) — especially sections 4b (messaging events) and 6b (bot webhook loop).

**Example — create a bot listener webhook:**

```bash
wxcli webhooks create \
  --name "Bot Listener" \
  --target-url "https://your-bot.com/webhook" \
  --resource messages \
  --event created
```

---

## 9. See Also

- [`messaging-spaces.md`](messaging-spaces.md) — Space and team CRUD, membership management, ECM, HDS
- [`webhooks-events.md`](webhooks-events.md) — Webhook CRUD, event payloads, HMAC verification, telephony and messaging events
- [`authentication.md`](authentication.md) — Token types, scopes, OAuth flows, bot token configuration
- [Adaptive Cards Designer](https://adaptivecards.io/designer/) — Visual card builder (adaptivecards.io)
- [Webex Buttons and Cards Designer](https://developer.webex.com/buttons-and-cards-designer) — Webex-specific card preview
- [Webex Cards Guide](https://developer.webex.com/docs/buttons-and-cards) — Official Webex guide for supported elements and gaps
