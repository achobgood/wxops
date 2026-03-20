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
| `cx-essentials` | CX Essentials (screen pop, wrap-up, supervisors) |

This table shows the 31 most commonly used groups. Run `wxcli --help` to see all ~100 groups, which also cover admin, device, and messaging APIs.

## Claude Code Integration

This repo includes a [Claude Code](https://claude.com/claude-code) playbook that provides guided assistance for Webex Calling configuration:

```bash
# Start the builder agent (walks you through the full workflow)
/wxc-calling-builder

# Debug a failing configuration
/wxc-calling-debug
```

The playbook includes:
- An agent workflow that interviews you, designs a deployment plan, executes via wxcli, and verifies results
- 14 specialized skills covering calling, admin, devices, messaging, and debugging
- 29 reference docs covering every Webex Calling API surface with raw HTTP examples

## Requirements

- Python 3.11+
- A Webex admin account with access tokens
- Required scopes: `spark-admin:telephony_config_read`, `spark-admin:telephony_config_write`, `spark-admin:people_read`, `spark-admin:people_write`

## License

Apache 2.0 — see LICENSE.
