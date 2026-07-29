---
name: device-platform
description: |
  Manage PhoneOS/RoomOS device configurations, workspace personalization, and xAPI device control
  using wxcli CLI commands. Covers device software configuration templates, user-to-workspace
  personalization, and programmatic device command execution and status queries.
  Also covers 9800-series phones (9811, 9821, 9841, 9851, 9861, 9871) which use PhoneOS config keys.
  Guides the user from prerequisites through execution and verification.
  NOT for: device provisioning, activation codes, DECT, or line key templates (use manage-devices skill).
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [device-platform-operation]
---

# Device Platform Workflow

**Checkpoint — do NOT proceed until you can answer these:**
1. Do 9800-series phones (9811/9821/9841/9851/9861/9871) use telephony device settings or PhoneOS config keys? (Answer: PhoneOS config keys via the Device Configurations API (`wxcli device-configurations`) — they are NOT configured via `wxcli device-settings` or telephony settings APIs.)
2. What CLI group handles xAPI commands for device control? (Answer: `wxcli xapi` — covers schema discovery (`list`), status queries (`show`), and command execution (`create`).)
3. You need a key name (command, status, or config) and don't know it. What do you do FIRST? (Answer: dump the device's full namespace to disk with `"*"` and grep it — see 6c. Do NOT guess a namespace, do NOT use training data, do NOT send the user to a website.)
4. You grep all three dumps and the key isn't there. What do you report? (Answer: "this device does not expose it" — NOT "the feature doesn't exist." Coverage varies by model and firmware.)

If you cannot answer all four, you skipped reading this skill. Go back and read it.

## Step 1: Load references

1. Read `docs/reference/devices-platform.md` for device configurations, workspace personalization, xAPI commands and status queries

**Mandatory --help verification:** Before constructing any wxcli command, run `wxcli <group> --help` to verify the subcommand exists, then `wxcli <group> <subcommand> --help` to verify the exact flags (e.g. `wxcli device-configurations update --help` and `wxcli xapi --help` — config-key names are firmware-dependent and the schema differs by device/PhoneOS version, known issue #10). Do NOT rely on examples in this skill or reference docs — the CLI is auto-generated and flag names may differ from what documentation suggests.

## Step 2: Verify auth token

Before any API calls, confirm the user has a working auth token:

```bash
wxcli whoami
```

If this fails, stop and resolve authentication first (`wxcli configure`). Required scopes vary by operation:

| Operation | Read Scope | Write Scope |
|-----------|-----------|-------------|
| Device configurations | `spark-admin:devices_read` | `spark-admin:devices_write` |
| Workspace personalization | `spark-admin:workspaces_read` | `spark-admin:workspaces_write` |
| xAPI status queries | `spark:xapi_statuses` | -- |
| xAPI command execution | -- | `spark:xapi_commands` |

> **NOTE:** xAPI scopes are user-level (`spark:`), not admin-level (`spark-admin:`). Admin tokens with `spark-admin:devices_read`/`spark-admin:devices_write` are **NOT** a substitute for xAPI scopes. A token may have device-config scopes but not xAPI scopes, or vice versa. Diagnose scope issues early.
>

## Step 3: Identify which device platform operation to perform

Ask the user what they want to do. Present this decision matrix if they are unsure:

| Need | Operation | CLI Group |
|------|-----------|-----------|
| Read/set RoomOS configuration keys on a device | Device configurations | `wxcli device-configurations` |
| Deploy configuration templates across multiple devices | Device configurations (bulk) | `wxcli device-configurations` + loop |
| Personalize a workspace device for a specific user | Workspace personalization | `wxcli workspace-personalization` |
| Send a command to a RoomOS device (dial, volume, standby, etc.) | xAPI command execution | `wxcli xapi create` |
| Query device status (volume, call state, network, room analytics) | xAPI status query | `wxcli xapi show` |
| Build a device automation/integration | xAPI (combination) | `wxcli xapi show` + `wxcli xapi create` |

**If the user asks about MPP phone (68xx/78xx/88xx) provisioning, activation codes, DECT, line keys, or hot desking**, redirect them to the `manage-devices` skill. Note: 9800-series phones (9811, 9821, 9841, 9851, 9861, 9871) are handled HERE — they use RoomOS config keys despite being `productType: phone`. This skill covers device SOFTWARE (RoomOS configs, personalization, xAPI), not device HARDWARE provisioning.

## Step 4: Check prerequisites

### 4a. Device exists and uses RoomOS configuration model

All 3 APIs require a device ID. Get it from `wxcli devices list`:

```bash
wxcli devices list --output json
```

- Confirm the target device uses the RoomOS configuration model. Valid devices:
  - **RoomOS devices:** Room, Board, or Desk series (`productType: roomdesk`)
  - **9800-series phones:** Cisco 9811, 9821, 9841, 9851, 9861, 9871 (`productType: phone` but runs PhoneOS/RoomOS)
- **MPP phones (68xx, 78xx, 88xx) and ATAs do NOT use this API.** Redirect to `manage-devices` skill for those.
- Capture `device_id` for use in subsequent commands
- If the user does not have any devices, direct them to the `manage-devices` skill to create or activate one first

### 4b. For workspace personalization: workspace exists with a device

```bash
wxcli workspaces list --output json
```

- Capture `workspace_id` for the target workspace
- If the workspace does not exist, direct the user to the `manage-devices` skill to create it first

### 4c. For xAPI: device is online and reachable

Test reachability with a status query:

```bash
wxcli xapi show --device-id DEVICE_ID --name "SystemUnit.State.System"
```

- If this returns data, the device is online and xAPI-capable
- If this errors, the device may be offline, not cloud-registered, or not a RoomOS device

### 4d. Operation-specific prerequisites

| Operation | Prerequisites |
|-----------|--------------|
| **Device configurations (read)** | Device ID, device must be cloud-registered RoomOS |
| **Device configurations (write)** | Device ID, configuration key path must be valid and editable |
| **Workspace personalization** | Workspace ID, workspace must have a device assigned, device must be online |
| **xAPI status query** | Device ID, device must be online and RoomOS |
| **xAPI command execution** | Device ID, device must be online and RoomOS, command name must be valid |

---

## Step 5: Build and present deployment plan -- [SHOW BEFORE EXECUTING]

Before executing any commands, present the full plan to the user:

```
DEPLOYMENT PLAN
===============
Operation: [device platform operation type]
Device: [device display name] ([device_id])
Device Type: [Room Kit / Board / Desk Pro / etc.]

Operation Details:
  [Operation-specific details listed here]
  - For device configs: key(s) to read or update, new value(s)
  - For personalization: workspace name, user email
  - For xAPI: command name or status expression(s)

Prerequisites verified:
  [check] Device exists and is RoomOS
  [check] Device is cloud-registered
  [check] Auth token has required scopes
  [check] [Operation-specific prereqs]

Commands to execute:
  wxcli [group] [command] ...
  [Verification command]

Proceed? (yes/no)
```

**Wait for user confirmation before executing.**

---

## Step 6: Execute via wxcli

### 6a. Device Configurations

**Read configuration keys:**

```bash
# Read all configurations for a device
wxcli device-configurations show --device-id DEVICE_ID

# Filter by key pattern (wildcard)
wxcli device-configurations show --device-id DEVICE_ID --key "Audio.Ultrasound.*"

# Filter by exact key
wxcli device-configurations show --device-id DEVICE_ID --key "Conference.MaxReceiveCallRate"
```

**Update configuration keys:**

> **WARNING:** The `--op` and `--path` flags on the update command are broken -- they cannot set a value and do not produce a valid JSON Patch array. **Always use `--json-body` for this command.**

```bash
# Set a configuration value (replace operation)
wxcli device-configurations update --device-id DEVICE_ID --json-body '[{"op": "replace", "path": "Audio.Ultrasound.MaxVolume/sources/configured/value", "value": 70}]'

# Revert a configuration to its schema default (remove operation)
wxcli device-configurations update --device-id DEVICE_ID --json-body '[{"op": "remove", "path": "Audio.Ultrasound.MaxVolume/sources/configured/value"}]'

# Multiple changes in one request
wxcli device-configurations update --device-id DEVICE_ID --json-body '[
  {"op": "replace", "path": "Audio.Ultrasound.MaxVolume/sources/configured/value", "value": 70},
  {"op": "replace", "path": "Conference.MaxReceiveCallRate/sources/configured/value", "value": 6000}
]'
```

**Key path rules:**
- Key filter uses `.` as separator: `Audio.Ultrasound.MaxVolume`
- Update path uses `/` after the key name: `Audio.Ultrasound.MaxVolume/sources/configured/value`
- All update paths must end in `/sources/configured/value`
- `op` is either `replace` (set value) or `remove` (revert to default)

### 6b. Workspace Personalization

Workspace personalization is an **async** operation. It temporarily pushes a user's speed dials, favorites, and call history to a shared workspace device.

```bash
# Personalize a workspace for a user
wxcli workspace-personalization create WORKSPACE_ID --email user@example.com

# Poll for task completion
wxcli workspace-personalization show WORKSPACE_ID
```

- `create` takes `WORKSPACE_ID` as a positional argument and `--email` as a required option
- `show` takes `WORKSPACE_ID` as a positional argument
- The `show` response contains `success: true` or `success: false` with an `errorDescription`
- Common error: "Device is offline" -- the workspace device must be online and registered
- **Do not tell the user it is done until `show` returns `success: true`**

### 6c. Discover the Namespace -- Dump, Then Grep

**Do this FIRST whenever you do not already know the exact key name. Do NOT guess a namespace, and do NOT rely on your training data for xAPI key names.**

The device reports its own complete namespace. Dump all three surfaces to disk, then grep locally:

**One device per dump. Always namespace the filenames by device.** Namespaces differ by model and firmware — a key on one device may be absent on the next.

```bash
# Pick a short unique tag per device (e.g. its displayName, slugified). ONE device per file.
TAG=roombarpro   # <- change per device; never reuse across devices

wxcli xapi list --device-id DEVICE_ID --status  "*" -o json > /tmp/${TAG}_status.json
wxcli xapi list --device-id DEVICE_ID --command "*" -o json > /tmp/${TAG}_commands.json

# Configurations -- DIFFERENT API, see the surface table below
wxcli device-configurations show --device-id DEVICE_ID -o json > /tmp/${TAG}_configs.json

# Search ONE device's dumps at a time -- never glob across devices
grep -io '"[A-Za-z][A-Za-z0-9._[]]*Background[A-Za-z0-9._[]]*"' /tmp/${TAG}_*.json | sort -u
```

**NEVER `Read` these dumps.** Verified live on a Room Bar Pro: 535 statuses + 453 commands + 1,218 configs, ~1.4 MB combined (~350k tokens). Grep them; never open them.

**Multi-device rules — violating these is how you execute against the wrong box:**

- **Never grep across devices** (no `/tmp/*_status.json` globs). A hit tells you a key exists *somewhere*, not on the device you're about to call. Re-grep that device's own dump before executing.
- `--device-id` accepts up to **5 device IDs** per request, and the response is an array where each item carries its own `deviceId`. If you ever query more than one at a time, you **must** parse per `deviceId` — a flat grep destroys the attribution the API gave you.
- **Fleet-wide work:** dump each device separately, grep each separately, and treat "device A has it" as zero evidence about device B. Report per-device results, not a single fleet-wide answer.
- **Mixed fleets: xAPI is RoomOS-only.** Room/Board/Desk series support xAPI; PhoneOS 9800-series and MPP phones do not. On a 9800-series phone, skip the `xapi` dumps entirely and use `device-configurations` (6a) — that API serves both RoomOS and PhoneOS. A failed xAPI call on a phone is expected, not a bug; do not report it as the device being broken, and do not retry it.

**Why dump instead of filter:** filtering requires guessing the first word, and that guess is a coin flip. `Camera.*` and `Cameras.*` are BOTH real, distinct namespaces on the same device — a filtered query on the wrong one returns a confident, complete-looking, wrong answer. Dumping has no such failure mode. Once you know the namespace, filtering (`--command "Camera.*"`) is a fine optimization.

**Three surfaces, two APIs — a key lives in exactly one:**

| Surface | API | Command | Example |
|---------|-----|---------|---------|
| Command (do a thing) | xAPI | `wxcli xapi list --command`, `xapi create` | `Camera.PositionReset` |
| Status (read a live value) | xAPI | `wxcli xapi list --status`, `xapi show` | `SystemUnit.ProductPlatform` |
| Configuration (persistent setting) | Device Configurations | `wxcli device-configurations show` / `wxcli device-configurations update` (6a) | `Video.Input.CameraConfigMode` |

`xapi list` **cannot see configurations** — `/xapi/schema` accepts only `--status` and `--command`. If you search only xAPI for a setting, you will wrongly conclude it does not exist. Search all three dumps.

**Verified behaviors — do not re-derive these:**

- **`-o json` is mandatory.** The default table output renders a single `Device Id` column and silently drops every command, argument, and schema. It does not error — it just looks like the device has nothing.
- **The dumps contain NO descriptions.** Checked across all 2,206 keys on a live device: zero `description`/`help`/`summary`/`doc` fields. A command returns only `arguments` (each with `required` + a JSON Schema) and a `resultSchema`; a config returns only `value`, `source`, `sources`, `valueSpace`, `appliedConfigurationValue`. **The device tells you a key's shape, never its meaning.** Do not tell the user what a key does based on a dump alone — say you have the name and shape but not the semantics.
- `--device-id` is required (max 5 per request). Discovery needs a live, online, cloud-registered device.
- Scopes differ: `spark:xapi_commands` for `--command`, `spark:xapi_statuses` for `--status`. Configurations use `spark-admin:devices_read/write`.

**Absence in a dump means "not on THIS device" — never "does not exist."**
Coverage varies sharply by model and firmware. A real example: the virtual-background keys (`Cameras.Background.*`) exist on Cisco hardware but are absent from a Room Bar Pro's dump entirely. If you grep and find nothing, report *"this device does not expose it"* and name the device — do NOT tell the user the feature does not exist. A confident false negative is worse than no answer.

**Worked example -- "reset the camera position on device XYZ":**

1. Dump + grep: `grep -io '"Camera[^"]*"' /tmp/dev_commands.json | sort -u` -> finds `Camera.PositionReset`
2. Read that key's object: `CameraId` (required, integer 1-15) and `Axis` (optional enum `All`/`Focus`/`PanTilt`/`Zoom`, default `All`). *(Verified live.)*
3. Execute: `wxcli xapi create Camera.PositionReset --device-id XYZ --json-body '{"deviceId": "XYZ", "arguments": {"CameraId": 1}}'`

Argument names and value ranges vary by model and firmware. Trust the dump for the device in front of you over any example in this skill.

### 6d. xAPI -- Status Queries

```bash
# Query a single status value
wxcli xapi show --device-id DEVICE_ID --name "Audio.Volume"

# Query multiple status values (comma-separated, max 10)
wxcli xapi show --device-id DEVICE_ID --name "Audio.Volume,SystemUnit.State.NumberOfActiveCalls"
```

- `--device-id` and `--name` are both required
- `--name` accepts dot-notation status paths
- Returns current real-time values from the device

**Common status queries:**

| Status Path | Returns |
|-------------|---------|
| `Audio.Volume` | Current volume level |
| `SystemUnit.State.NumberOfActiveCalls` | Active call count |
| `Network[1].IPv4.Address` | Device IP address |
| `RoomAnalytics.PeopleCount.Current` | People in the room |
| `Peripherals.ConnectedDevice[*].Name` | Connected peripherals |
| `Standby.State` | Standby/active state |

### 6e. xAPI -- Command Execution

```bash
# Simple command with no arguments (deviceId auto-populated from --device-id)
wxcli xapi create Standby.Activate --device-id DEVICE_ID

# Command with arguments (must include deviceId in JSON body)
wxcli xapi create Audio.Volume.Set --device-id DEVICE_ID --json-body '{"deviceId": "DEVICE_ID", "arguments": {"Level": 50}}'

# Another example: display an on-screen message
wxcli xapi create UserInterface.Message.Alert.Display --device-id DEVICE_ID --json-body '{"deviceId": "DEVICE_ID", "arguments": {"Title": "IT Notice", "Text": "Maintenance at 5pm", "Duration": 30}}'
```

> **IMPORTANT:** When using `--json-body`, the CLI does NOT auto-inject `--device-id` into the body. You must include `"deviceId"` in the JSON body yourself. Without `--json-body`, the CLI auto-populates `deviceId` from `--device-id` (works for no-argument commands like `Standby.Activate`).

- `command_name` is a positional argument (dot-notation, e.g., `Audio.Volume.Set`)
- `--device-id` identifies the target device (always required as a CLI flag)
- `--json-body` passes the request body including `deviceId` and `arguments`

**Common xAPI commands (representative, not exhaustive):**

| Command | Arguments | Use Case |
|---------|-----------|----------|
| `Audio.Volume.Set` | `Level` (0-100) | Set volume |
| `Audio.Volume.Mute` | -- | Mute microphone |
| `Call.Dial` | `Number` | Initiate a call |
| `Call.Disconnect` | `CallId` | End a call |
| `Standby.Activate` | -- | Put device in standby |
| `Standby.Deactivate` | -- | Wake device |
| `Bookings.List` | `Days`, `Offset` | Get calendar bookings |
| `Message.Send` | `Text` | Display on-screen message |
| `UserInterface.Message.Alert.Display` | `Title`, `Text`, `Duration` | Show alert popup |

**Do not paste the namespace into context — but do dump it.** An unfiltered `xapi list` returns hundreds of keys (~350k tokens across all three surfaces). Redirect it to a file and grep (6c); never `Read` it. https://roomos.cisco.com/xapi documents the namespace for humans and is the only source of *prose* for what a key means, but it is not a substitute for 6c — only the device knows what it actually exposes.

### Error handling

| Error | Cause | Fix |
|-------|-------|-----|
| 401/403 | Token expired or insufficient scopes | Run `wxcli configure` to re-authenticate |
| 400 "device not found" | Invalid device ID or device not cloud-registered | Verify with `wxcli devices list` |
| 400 on xAPI command | Device offline, wrong command name, or missing arguments | Check device is online, then confirm the command name and its required arguments against the device with a filtered `wxcli xapi list` (6c) |
| 400 on device-configurations update | Invalid path, bad JSON Patch format, or non-editable key | Verify path ends in `/sources/configured/value`, check key is editable |
| Personalization "Device is offline" | Workspace device not online | Device must be powered on and cloud-registered |

---

## Step 7: Verify

After execution, read back results and confirm the operation succeeded.

### Device configurations

```bash
# Re-read the config key to confirm the new value took effect
wxcli device-configurations show --device-id DEVICE_ID --key "Audio.Ultrasound.MaxVolume"
```

Verify the `source` shows `configured` (not `default`) and the value matches what was set.

### Workspace personalization

```bash
# Check task status
wxcli workspace-personalization show WORKSPACE_ID
```

Verify `success: true` in the response. If `success: false`, check the `errorDescription` and troubleshoot.

### xAPI

```bash
# For status queries: result is immediate in the response
# For commands: check the response for success or error

# Example: verify volume was set
wxcli xapi show --device-id DEVICE_ID --name "Audio.Volume"
```

---

## Step 8: Report results

Present the results:

```
DEVICE PLATFORM OPERATION COMPLETE
====================================
Operation: [type -- config read/write, personalization, xAPI command/status]
Device: [device display name] ([device_id])
Device Type: [Room Kit / Board / Desk Pro / etc.]

Results:
  [Operation-specific results]
  - For config read: key values and their sources
  - For config write: confirmed new values
  - For personalization: task status (success/failure)
  - For xAPI status: returned status values
  - For xAPI command: command result

Next steps:
  - [Operation-specific next steps]
  - [e.g., "Deploy same config to other devices in the org"]
  - [e.g., "Set up a scheduled automation for this xAPI command"]
  - [e.g., "Check personalization task again if still in progress"]
```

---

## Critical Rules

1. **xAPI only works on RoomOS devices.** If the user asks to send an xAPI command to an MPP phone, stop and explain. MPP phones use `device-settings` (see `manage-devices` skill), not xAPI. RoomOS devices include Room, Board, and Desk series.

2. **9800-series phones straddle both skills.** 9800-series phones (9811/9821/9841/9851/9861/9871) use this skill (device-platform) for **PhoneOS** config keys, BUT they also support some telephony device-settings commands via the `manage-devices` skill. **IMPORTANT: 9800-series runs PhoneOS, not RoomOS. PhoneOS is RoomOS-derived but is a distinct OS — Room/Board/Desk series run RoomOS; 9800-series runs PhoneOS. The Device Configurations API surface is shared, but the schemas differ. Do not call 9800-series "RoomOS devices".**
   - **Line Key Templates** -- model string is `"Cisco 98xx"` (no `"DMS"` prefix; older MPP phones use `"DMS Cisco 88xx"` format)
   - **Device member management** -- add/remove lines on ports
   - **Person-level device settings** -- limited fields like compression
   
   Rule of thumb: PhoneOS config keys on 9800-series or RoomOS config keys on Room/Board/Desk (software settings, UI, audio, video, line labels, wallpaper) -> this skill. Line key templates, device members, telephony device settings -> `manage-devices` skill.

3. **Always get a device ID first.** All 3 APIs require a device ID. The user may not have one -- guide them through `wxcli devices list` to find it. For workspace personalization, also get the workspace ID via `wxcli workspaces list`.

4. **Workspace personalization is async.** After creating a personalization request, always poll with `wxcli workspace-personalization show WORKSPACE_ID` until the task completes. Do not tell the user it is done until `success: true` is returned. Typical completion time is ~30 seconds.

5. **Device must be online for xAPI.** xAPI commands fail silently or with unhelpful errors on offline devices. Always check reachability first with a status query (`wxcli xapi show --device-id DEVICE_ID --name "SystemUnit.State.System"`).

6. **Configuration update PATCH content type.** The API uses `application/json-patch+json`, not `application/json`. The CLI handles this automatically. If the user falls back to raw HTTP (curl), they must set the `Content-Type` header correctly.

7. **Never guess a key name — dump the device's namespace and grep it (6c).** Filtering on a guessed namespace is a coin flip: `Camera.*` and `Cameras.*` are both real and distinct, so a wrong guess returns a confident, complete-looking, wrong answer. Dump all three surfaces with `"*"` to disk and grep. Never `Read` the dumps (~350k tokens). Do not substitute training data or a link to roomos.cisco.com for the lookup. The device is authoritative for its own model and firmware — but only about itself: absence means "not on this device," not "does not exist."

8. **Scope mismatch between device-configurations and xAPI.** Device configurations use admin scopes (`spark-admin:devices_read`/`spark-admin:devices_write`). xAPI uses user-level scopes (`spark:xapi_statuses`/`spark:xapi_commands`). A token may have one set but not the other. Diagnose scope issues early in Step 2.

---

## CLI Bug Notes

1. **`device-configurations update` -- `--op` and `--path` flags are broken.** These flags exist but cannot set a value and do not produce a valid JSON Patch array. **Always use `--json-body`** for configuration updates.

2. **`xapi create` -- `--json-body` does not auto-inject `deviceId`.** When you use `--json-body`, the CLI does NOT copy `--device-id` into the body. You must include `"deviceId"` in the JSON body manually. Without `--json-body` (for no-argument commands), the CLI auto-populates `deviceId` from `--device-id`.

---

## Scope Quick Reference

| CLI Group | Read Scope | Write Scope |
|-----------|-----------|-------------|
| `wxcli device-configurations` | `spark-admin:devices_read` | `spark-admin:devices_write` |
| `wxcli workspace-personalization` | `spark-admin:workspaces_read` | `spark-admin:workspaces_write` |
| `wxcli xapi` (status) | `spark:xapi_statuses` | -- |
| `wxcli xapi` (commands) | -- | `spark:xapi_commands` |

> Admin tokens with `spark-admin:devices_read`/`spark-admin:devices_write` do NOT work for xAPI operations. xAPI requires user-level scopes: `spark:xapi_statuses` (for status queries) and `spark:xapi_commands` (for command execution). See devices-platform.md scope table.
>

---

## Cross-References

- **Device CRUD, activation codes, MAC provisioning** -- use the `manage-devices` skill (`.codex/skills/manage-devices/SKILL.md`)
- **Workspace creation** -- use the `manage-devices` skill (Step 7: Workspace devices)
- **DECT networks, base stations, handsets** -- use the `manage-devices` skill (Step 6: DECT workflow)
- **Phone settings, line keys, device members** -- use the `manage-devices` skill (Step 9: Device settings)
- **Hot desking on MPP phones** -- use the `manage-devices` skill (Step 10: Hot desking)
- **Hot desking vs. workspace personalization** -- hot desking is a telephony feature on MPP phones (voice portal sign-in); workspace personalization pushes user preferences to RoomOS collaboration devices. Different mechanisms, similar concept, different device types.
- **Reference docs**: `docs/reference/devices-platform.md` (this skill's reference), `docs/reference/devices-core.md`, `docs/reference/devices-dect.md`, `docs/reference/devices-workspaces.md`
- **Full xAPI reference**: https://roomos.cisco.com/xapi

---

## Context Compaction Recovery

If context compacts mid-execution, recover by:
1. Read the deployment plan from `docs/plans/` to recover what was planned
2. Check what has already been done:
   - For device configs: `wxcli device-configurations show --device-id DEVICE_ID` to see current state
   - For personalization: `wxcli workspace-personalization show WORKSPACE_ID` to check task status
   - For xAPI: re-run the status query to confirm current device state
3. Resume from the first incomplete step
