# wxcli — Webex Calling CLI

A command-line tool for provisioning and managing Webex Calling environments. 100 command groups covering the full Webex Calling, admin, device, and messaging API surface.

## Install

```bash
cd webexCalling
pip install -e .
```

## Authenticate

Get a personal access token from [developer.webex.com](https://developer.webex.com) (valid for 12 hours):

```bash
# Option 1: Persistent (recommended)
echo "YOUR_TOKEN" | wxcli configure

# Option 2: Environment variable (per-session only)
export WEBEX_ACCESS_TOKEN="YOUR_TOKEN"

# Verify auth
wxcli whoami
```

## Usage

```bash
# See all 100 command groups
wxcli --help

# List calling-enabled locations
wxcli location-settings list-1

# Create a location (address requires --json-body)
wxcli locations create --name "San Jose Office" \
  --time-zone "America/Los_Angeles" \
  --preferred-language en_us \
  --announcement-language en_us \
  --json-body '{"address": {"address1": "123 Main St", "city": "San Jose", "state": "CA", "postalCode": "95113", "country": "US"}}'

# Enable Webex Calling on a location (fetch details first with wxcli locations show LOCATION_ID)
wxcli location-settings create --id LOCATION_ID --name "..." --time-zone "..." --preferred-language en_US --announcement-language en_us

# Create an auto attendant (LOCATION_ID is positional)
wxcli auto-attendant create LOCATION_ID \
  --name "Main Menu" --extension 1000 --business-schedule "Business Hours"

# Create a call queue
wxcli call-queue create LOCATION_ID \
  --name "Support Queue" --extension 2000

# Create a hunt group
wxcli hunt-group create LOCATION_ID \
  --name "Sales Team" --extension 3000 --enabled

# View user call settings
wxcli user-settings show-call-forwarding PERSON_ID --output json

# Get help for any command
wxcli locations create --help
```

### Finding IDs

```bash
wxcli locations list --calling-only        # Get location IDs
wxcli users list --location LOC_ID         # Get person IDs
wxcli numbers-api list --location-id LOC_ID  # Get number inventory
```

### Tips

- **`--json-body`** — For complex nested settings (call forwarding rules, voicemail config, agent lists), pass the full JSON body: `wxcli call-queue update LOC_ID QUEUE_ID --json-body '{"agents": [...]}'`
- **`--debug`** — Add to any command for verbose HTTP request/response output, useful for troubleshooting

## Command Groups

| Group | Description |
|-------|-------------|
| `whoami` | Show current authenticated user and org |
| `locations` | Create, list, enable calling on locations |
| `users` | Create, list, manage users |
| `licenses` | List and inspect licenses |
| `numbers` | Manage phone numbers |
| `numbers-api` | Add, remove, validate numbers |
| `location-schedules` | Business hours and holiday schedules |
| `auto-attendant` | IVR menus with key-press routing |
| `call-queue` | Hold callers until an agent is free |
| `hunt-group` | Ring a group of agents directly |
| `call-park` | Park calls on extensions |
| `call-pickup` | Answer each other's ringing phones |
| `paging-group` | One-way broadcast announcements |
| `location-voicemail` | Shared voicemail boxes |
| `operating-modes` | Business hours operating modes |
| `call-routing` | Dial plans, trunks, route groups |
| `call-controls` | Real-time call control (dial, hold, transfer) |
| `user-settings` | Person-level call settings (forwarding, DND, voicemail, etc.) |
| `location-settings` | Location-level call settings |
| `dect-devices` | DECT networks, base stations, handsets |
| `device-settings` | Device configurations |
| `workspaces` | Workspace management |
| `emergency-services` | E911 and emergency services |
| `announcements` | Announcement repository |
| `announcement-playlists` | Playlist management |
| `virtual-extensions` | Virtual extension management |
| `single-number-reach` | Single number reach settings |
| `call-recording` | Call recording settings |
| `pstn` | PSTN connection management |
| `cx-essentials` | Customer Assist (screen pop, wrap-up, supervisors) |

This table shows the 31 most commonly used groups. Run `wxcli --help` to see all ~100 groups, which also cover admin, device, and messaging APIs.

## Claude Code Integration

This repo includes an AI playbook for [Claude Code](https://claude.com/claude-code) that turns your terminal into a guided Webex Calling configuration assistant.

### What is the Playbook?

A guided AI assistant that walks you through Webex Calling configuration end-to-end. It interviews you about what you want to build, generates a deployment plan, executes `wxcli` commands on your behalf, and verifies the results. Think of it as a Webex Calling expert sitting next to you in the terminal.

### What's Included

- **1 builder agent** (`/agents` → wxc-calling-builder) — the main entry point that drives the full workflow
- **16 specialized skills** covering: provisioning, call features, Customer Assist, routing, devices, device platform, call settings, call control, reporting, identity/SCIM, licensing, audit/compliance, messaging spaces, messaging bots, debugging, and a seven-advisors decision framework
- **29 reference docs** in `docs/reference/` documenting every Webex Calling API surface with SDK method signatures and raw HTTP examples
- **Shared permissions** (`.claude/settings.json`) that pre-approve `wxcli` commands so Claude Code doesn't prompt you for every CLI execution

### How to Use It

1. Install [Claude Code](https://claude.com/claude-code)
2. Clone this repo and `cd` into it
3. Install the CLI: `pip install -e .`
4. Run `claude` to start Claude Code
5. Use `/agents` and select **wxc-calling-builder** to begin
6. Or use `/wxc-calling-debug` to troubleshoot a specific issue

The repo includes a `.claude/settings.json` that pre-approves common commands (`wxcli`, `pip install`, `which`). This means the playbook agent can run `wxcli` commands without prompting you for permission each time. You can review or customize these permissions in `.claude/settings.json`. Any personal overrides go in `.claude/settings.local.json` (gitignored).

### Without Claude Code

The AI playbook is optional — everything else works standalone:

- **wxcli** is a regular Python CLI tool. Install it and use it directly.
- The **29 reference docs** in `docs/reference/` are a comprehensive API knowledge base, useful for any developer working with Webex APIs.
- The **OpenAPI specs** (`webex-*.json`) can be imported into Postman or any API client.

## Project Architecture

```
webexCalling/
├── src/wxcli/                    # CLI source (Click + wxc-sdk REST client)
│   ├── main.py                   # Entry point — registers 100 command groups
│   ├── auth.py                   # Token storage and API client init
│   ├── output.py                 # Table/JSON output formatting
│   └── commands/                 # 100 generated command files (one per API group)
├── tools/                        # Code generator pipeline
│   ├── generate_commands.py      # Orchestrator: OpenAPI → Click commands
│   ├── openapi_parser.py         # Parses OpenAPI 3.0 specs into Endpoint objects
│   ├── command_renderer.py       # Renders Endpoints into Python command files
│   └── field_overrides.yaml      # Table columns, display config, bug fixes
├── webex-*.json                  # 4 OpenAPI 3.0 specs (calling, admin, device, messaging)
├── docs/reference/               # 29 API reference docs (SDK + raw HTTP)
├── .claude/settings.json          # Shared permissions (pre-approves wxcli commands)
├── .claude/agents/               # Claude Code builder agent
└── .claude/skills/               # 16 Claude Code skills
```

**Key design decisions:**

- **Commands are generated, never hand-edited.** Fix bugs in `field_overrides.yaml` and regenerate with `tools/generate_commands.py`.
- **The CLI uses raw HTTP** via wxc-sdk's REST client, not the SDK's typed methods. This gives 100% API coverage without waiting for SDK updates.
- **Reference docs serve both humans and AI.** Developers can read them directly; the playbook loads them as context for guided configuration.

## Known Limitations

- **Call control commands require a user-level OAuth token.** Admin and service app tokens return `400 "Target user not authorized"`. Use a personal access token from the user who will control calls.
- **Complex nested settings need `--json-body`.** Call forwarding rules, agent lists, voicemail config, and similar deeply nested structures can't be expressed as CLI flags — pass the full JSON body instead.
- **6 person call settings are user-only.** `simultaneousRing`, `sequentialRing`, `priorityAlert`, `callNotify`, `anonymousCallReject`, and `callPolicies` only work with user-level tokens, not admin tokens.
- **CDR/analytics endpoints require the `analytics:read_all` scope**, which standard admin tokens may not include.

## Requirements

- Python 3.11+
- A Webex admin account with access tokens
- Required scopes: `spark-admin:telephony_config_read`, `spark-admin:telephony_config_write`, `spark-admin:people_read`, `spark-admin:people_write`

## License

Apache 2.0 — see LICENSE.
