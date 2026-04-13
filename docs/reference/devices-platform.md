# Device Platform Management (RoomOS Configurations, Personalization, xAPI)

## Sources

- wxc_sdk v1.30.0
- OpenAPI spec: specs/webex-device.json
- developer.webex.com Device Platform APIs

This document covers three Webex APIs that manage **device software** on cloud-registered RoomOS devices: configuration key management, workspace personalization, and xAPI command execution / status queries.

These APIs operate on the software layer of a device that is already provisioned and cloud-registered. They do not create, delete, or activate devices — that is a separate concern.

> **For phone provisioning, activation codes, MAC registration, DECT networks, and telephony device settings** see [devices-core.md](devices-core.md).
>
> **For workspace creation and workspace call settings** see [devices-workspaces.md](devices-workspaces.md).
>
> **For DECT base stations and handsets** see [devices-dect.md](devices-dect.md).

---

## Prerequisites

Before using any of the three APIs documented here, you need:

1. **A working auth token.** Verify with `wxcli whoami`. Token type (admin, user, service app) affects which scopes are available — see the Scopes section below.

2. **At least one cloud-registered RoomOS device** (for device-configurations and xAPI). This means a Cisco Room, Board, or Desk series device registered to Webex cloud. MPP phones do not support device-configurations key management or xAPI.

3. **At least one workspace with a device** (for workspace-personalization). The workspace must already exist and have a device assigned to it.

4. **A device ID.** All three APIs require a device ID. To find one:

```bash
wxcli devices list --output json
```

This returns all devices in the org. Filter for the device you need and capture its `id` field. See [devices-core.md](devices-core.md) for details on device listing and filtering.

---

## Scopes

| API | Read Scope | Write Scope |
|-----|-----------|-------------|
| Device Configurations | `spark-admin:devices_read` | `spark-admin:devices_write` |
| Workspace Personalization | `spark-admin:workspaces_read` | `spark-admin:workspaces_write` |
| xAPI Status | `spark:xapi_statuses` | — |
| xAPI Commands | — | `spark:xapi_commands` |

**Key distinction:** Device Configurations and Workspace Personalization use admin-level scopes (`spark-admin:`). xAPI uses user-level scopes (`spark:`). A token may have one set but not the other.

For full xAPI access (both status queries and command execution), ensure your token has both `spark:xapi_statuses` and `spark:xapi_commands`. The official Webex API documentation specifically requires these scopes and does not mention `spark-admin:devices_read/write` as a substitute.

---

## 1. Device Configurations

### What It Does

The Device Configurations API reads and writes RoomOS configuration keys on a specific device. Configuration keys follow a hierarchical dot-notation namespace — `Audio.Ultrasound.MaxVolume`, `Conference.MaxReceiveCallRate`, `Video.Input.Connector[1].Name`, and so on. Each key has a current value, a source (default vs. configured), and editability rules.

Changes are applied via JSON Patch operations (`replace` to set a value, `remove` to revert to the schema default). The API supports filtering by key name, wildcard patterns, and index ranges.

This API targets RoomOS devices only (Room, Board, Desk series). MPP phones do not expose configuration keys through this interface.

### CLI Commands

**List / read configurations:**

```bash
wxcli device-configurations show --device-id DEVICE_ID
```

With key filtering:

```bash
wxcli device-configurations show --device-id DEVICE_ID --key "Audio.Ultrasound.*"
```

| Flag | Required | Description |
|------|----------|-------------|
| `--device-id` | Yes | The device to read configurations from |
| `--key` | No | Filter expression — absolute key, wildcard, or range (see Key Filtering below) |
| `--output` / `-o` | No | Output format: `table` or `json` (default: `json`) |
| `--debug` | No | Print debug info |

**Update configurations:**

```bash
wxcli device-configurations update --device-id DEVICE_ID \
  --json-body '[{"op": "replace", "path": "Audio.Ultrasound.MaxVolume/sources/configured/value", "value": 70}]'
```

| Flag | Required | Description |
|------|----------|-------------|
| `--device-id` | Yes | The device to update configurations on |
| `--json-body` | Yes (effectively) | Full JSON Patch array — see note below |
| `--op` | No | **Non-functional** — see warning below |
| `--path` | No | **Non-functional** — see warning below |
| `--debug` | No | Print debug info |

> **WARNING:** The `--op` and `--path` flags exist on the `update` command but do NOT produce a valid JSON Patch array. They build a flat object `{"op": "...", "path": "..."}` instead of the required array `[{"op": "...", "path": "..."}]`, and provide no way to set a `value` field. **Always use `--json-body` for update operations.**

### Key Filtering

The `--key` flag on the `show` command accepts several filter formats:

| Format | Example | Behavior |
|--------|---------|----------|
| Absolute key | `"Conference.MaxReceiveCallRate"` | Returns one specific configuration |
| Wildcard | `"Audio.Ultrasound.*"` | Returns all keys matching the pattern |
| Range | `"FacilityService.Service[1..3].Name"` | Returns keys for indices 1 through 3 |

Square brackets in filter expressions must be URL-encoded (`%5B` / `%5D`) when using raw HTTP. The CLI handles this encoding automatically.

### Configuration Update Pattern

Updates use JSON Patch operations. The body is a JSON array of patch operations:

**Set a value (replace):**

```bash
wxcli device-configurations update --device-id DEVICE_ID \
  --json-body '[{"op": "replace", "path": "Audio.Ultrasound.MaxVolume/sources/configured/value", "value": 70}]'
```

**Revert to default (remove):**

```bash
wxcli device-configurations update --device-id DEVICE_ID \
  --json-body '[{"op": "remove", "path": "Audio.Ultrasound.MaxVolume/sources/configured/value"}]'
```

**Multiple operations in one request:**

```bash
wxcli device-configurations update --device-id DEVICE_ID \
  --json-body '[
    {"op": "replace", "path": "Audio.Ultrasound.MaxVolume/sources/configured/value", "value": 70},
    {"op": "replace", "path": "Conference.MaxReceiveCallRate/sources/configured/value", "value": 6000}
  ]'
```

The `op` field accepts two values:
- `replace` — set the key to a specific value
- `remove` — clear the configured value and revert to the schema default

The `path` field must end in `/sources/configured/value`. The portion before that suffix is the configuration key name using dot-notation (e.g., `Audio.Ultrasound.MaxVolume`).

### Raw HTTP

**Read configurations:**

```
GET https://webexapis.com/v1/deviceConfigurations?deviceId={deviceId}
GET https://webexapis.com/v1/deviceConfigurations?deviceId={deviceId}&key=Audio.*
```

**Update configurations:**

```
PATCH https://webexapis.com/v1/deviceConfigurations?deviceId={deviceId}
Content-Type: application/json-patch+json

[
  {
    "op": "replace",
    "path": "Audio.Ultrasound.MaxVolume/sources/configured/value",
    "value": 70
  }
]
```

Note the content type: `application/json-patch+json`, not `application/json`. The CLI handles this automatically. Raw HTTP callers must set the header correctly or the request will fail.

---

## 2. Workspace Personalization

### What It Does

Workspace Personalization temporarily personalizes a shared workspace device for a specific user. When personalized, the user's speed dials, favorites, and call history appear on the workspace device. This is useful for hot-desk-like scenarios on RoomOS collaboration devices (Room, Board, Desk series).

Personalization is an **asynchronous operation**. The `create` command initiates personalization and returns immediately. You must poll the task endpoint with `show` to determine when personalization is complete.

### CLI Commands

**Personalize a workspace for a user:**

```bash
wxcli workspace-personalization create WORKSPACE_ID --email user@example.com
```

| Flag / Argument | Required | Description |
|-----------------|----------|-------------|
| `WORKSPACE_ID` (positional) | Yes | The workspace to personalize |
| `--email` | Yes | Email address of the user whose preferences to apply |
| `--json-body` | No | Full JSON body (overrides `--email`) |
| `--debug` | No | Print debug info |

**Check personalization task status:**

```bash
wxcli workspace-personalization show WORKSPACE_ID
```

| Flag / Argument | Required | Description |
|-----------------|----------|-------------|
| `WORKSPACE_ID` (positional) | Yes | The workspace to check |
| `--output` / `-o` | No | Output format: `table` or `json` (default: `json`) |
| `--debug` | No | Print debug info |

### Workflow

1. **Get a workspace ID** (if you don't have one):
   ```bash
   wxcli workspaces list --output json
   ```
   If the workspace doesn't exist yet, create it first — see [devices-workspaces.md](devices-workspaces.md).

2. **Personalize the workspace:**
   ```bash
   wxcli workspace-personalization create WORKSPACE_ID --email user@example.com
   ```

3. **Poll for completion** (personalization takes approximately 30 seconds):
   ```bash
   wxcli workspace-personalization show WORKSPACE_ID
   ```
   - Success: `{ "success": true }`
   - Failure: `{ "success": false, "errorDescription": "..." }`

4. **Common failure:** `"Device is offline"` — the workspace device must be powered on, online, and registered to Webex cloud.

### Relationship to Hot Desking

Hot desking and workspace personalization both let a user temporarily use a shared device. They are **not the same mechanism**:

| Feature | Hot Desking | Workspace Personalization |
|---------|------------|--------------------------|
| Device type | MPP phones | RoomOS devices (Room, Board, Desk) |
| Mechanism | Voice portal login or app-based | API-driven user binding |
| Managed by | `manage-devices` skill / telephony settings | `device-platform` skill / personalization API |
| Scope | Calling features only | User preferences (speed dials, favorites, call history) |

### Raw HTTP

**Personalize a workspace:**

```
POST https://webexapis.com/v1/workspaces/{workspaceId}/personalize
Content-Type: application/json

{
  "email": "user@example.com"
}
```

**Check personalization task status:**

```
GET https://webexapis.com/v1/workspaces/{workspaceId}/personalizationTask
```

---

## 3. xAPI (Device Command Execution & Status Queries)

### What It Does

The xAPI interface lets you execute commands on RoomOS devices and query their real-time status. This is the same xAPI available on the device's local interface, but accessed through the Webex cloud — enabling remote programmatic control of devices anywhere in the org.

Use cases include:
- Room booking and digital signage integrations
- Remote volume, standby, and display control
- Real-time room analytics (people count, call state)
- Custom automations triggered by events or schedules

xAPI works **only with RoomOS devices** (Room, Board, Desk series). MPP phones do not support xAPI. The device must be online and cloud-registered for commands to reach it.

### CLI Commands

**Query device status:**

```bash
wxcli xapi show --device-id DEVICE_ID --name "Audio.Volume"
```

| Flag | Required | Description |
|------|----------|-------------|
| `--device-id` | Yes | The RoomOS device to query |
| `--name` | Yes | Status expression(s) — comma-separated, max 10 per request |
| `--output` / `-o` | No | Output format: `table` or `json` (default: `json`) |
| `--debug` | No | Print debug info |

**Execute a command (no arguments):**

```bash
wxcli xapi create Standby.Activate --device-id DEVICE_ID
```

When no `--json-body` is provided, the CLI automatically populates `deviceId` in the request body from the `--device-id` flag. This works for commands that take no arguments.

**Execute a command (with arguments):**

```bash
wxcli xapi create Audio.Volume.Set --device-id DEVICE_ID \
  --json-body '{"deviceId": "DEVICE_ID", "arguments": {"Level": 50}}'
```

| Flag / Argument | Required | Description |
|-----------------|----------|-------------|
| `COMMAND_NAME` (positional) | Yes | xAPI command name in dot-notation (e.g., `Audio.Volume.Set`) |
| `--device-id` | Yes | The RoomOS device to send the command to |
| `--json-body` | No | Full JSON body with arguments — see note below |
| `--debug` | No | Print debug info |

> **IMPORTANT:** When using `--json-body`, the CLI does NOT auto-inject `--device-id` into the body. You must include `"deviceId"` in the JSON body yourself. Without `--json-body`, the CLI auto-populates `deviceId` from `--device-id` (works for no-argument commands like `Standby.Activate`).

### Status Queries

The `show` command queries real-time status values from a device. The `--name` flag accepts dot-notation status path expressions.

**Single status query:**

```bash
wxcli xapi show --device-id DEVICE_ID --name "Audio.Volume"
```

**Multiple status queries (comma-separated, max 10):**

```bash
wxcli xapi show --device-id DEVICE_ID --name "Audio.Volume,SystemUnit.State.NumberOfActiveCalls"
```

#### Common Status Queries

| Status Path | Returns |
|-------------|---------|
| `Audio.Volume` | Current volume level |
| `SystemUnit.State.NumberOfActiveCalls` | Active call count |
| `Network[1].IPv4.Address` | Device IP address |
| `RoomAnalytics.PeopleCount.Current` | Number of people detected in the room |
| `Peripherals.ConnectedDevice[*].Name` | Connected peripheral device names |
| `Standby.State` | Whether device is in standby or active |
| `SystemUnit.Software.DisplayName` | Current firmware version |
| `SystemUnit.ProductId` | Device model identifier |

### Command Execution

Commands are sent via the `create` subcommand. The positional argument is the xAPI command name in dot-notation. Arguments to the command are passed via `--json-body`.

**No-argument command (deviceId auto-populated):**

```bash
wxcli xapi create Standby.Activate --device-id DEVICE_ID
```

**Command with arguments (deviceId must be in body):**

```bash
wxcli xapi create Audio.Volume.Set --device-id DEVICE_ID \
  --json-body '{"deviceId": "DEVICE_ID", "arguments": {"Level": 50}}'
```

```bash
wxcli xapi create Call.Dial --device-id DEVICE_ID \
  --json-body '{"deviceId": "DEVICE_ID", "arguments": {"Number": "user@example.com"}}'
```

```bash
wxcli xapi create UserInterface.Message.Alert.Display --device-id DEVICE_ID \
  --json-body '{"deviceId": "DEVICE_ID", "arguments": {"Title": "Notice", "Text": "Meeting starts in 5 minutes", "Duration": 30}}'
```

#### Common xAPI Commands

| Command | Arguments | Use Case |
|---------|-----------|----------|
| `Audio.Volume.Set` | `Level` (0-100) | Set volume |
| `Audio.Volume.Mute` | — | Mute microphone |
| `Audio.Volume.Unmute` | — | Unmute microphone |
| `Call.Dial` | `Number` | Initiate a call |
| `Call.Disconnect` | `CallId` | End a call |
| `Standby.Activate` | — | Put device in standby |
| `Standby.Deactivate` | — | Wake device from standby |
| `Bookings.List` | `Days`, `Offset` | Get calendar bookings |
| `Message.Send` | `Text` | Display on-screen message |
| `UserInterface.Message.Alert.Display` | `Title`, `Text`, `Duration` | Show alert popup on screen |

This table is representative, not exhaustive. The full xAPI command namespace is documented by Cisco at [roomos.cisco.com/xapi](https://roomos.cisco.com/xapi).

### xAPI Command Reference

The cloud xAPI interface exposed by the Webex API mirrors the local xAPI available on RoomOS devices. Any command or status path documented in Cisco's RoomOS xAPI reference can be used through the CLI.

- **Full xAPI namespace:** [roomos.cisco.com/xapi](https://roomos.cisco.com/xapi)
- **Device Developers Guide:** [developer.webex.com](https://developer.webex.com) (xAPI section)

### Raw HTTP

**Query status:**

```
GET https://webexapis.com/v1/xapi/status?deviceId={deviceId}&name=Audio.Volume
```

**Execute a command:**

```
POST https://webexapis.com/v1/xapi/command/Audio.Volume.Set
Content-Type: application/json

{
  "deviceId": "DEVICE_ID",
  "arguments": {
    "Level": 50
  }
}
```

**Execute a no-argument command:**

```
POST https://webexapis.com/v1/xapi/command/Standby.Activate
Content-Type: application/json

{
  "deviceId": "DEVICE_ID"
}
```

---

## Gotchas

1. **xAPI only works with RoomOS devices.** Room, Board, and Desk series devices support xAPI. MPP phones do not. If you need to manage MPP phone settings, use the telephony device settings API — see [devices-core.md](devices-core.md).

2. **Device must be online and cloud-registered.** xAPI commands and device configuration reads/writes require the device to be reachable through Webex cloud. Offline devices will return errors or fail silently.

3. **Device Configurations PATCH requires `application/json-patch+json`.** The content type for configuration updates is `application/json-patch+json`, not `application/json`. The CLI sets this automatically. Raw HTTP callers must set the `Content-Type` header correctly or the request will be rejected.

4. **xAPI `--name` accepts comma-separated expressions, max 10 per request.** If you need more than 10 status values, make multiple requests.

5. **Workspace personalization is asynchronous.** The `create` command returns immediately. Always poll with `show` until the task reports `success: true` or `success: false`. Do not assume instant completion — typical completion time is approximately 30 seconds.

6. **xAPI scopes are user-level, not admin-level.** xAPI status queries need `spark:xapi_statuses` and command execution needs `spark:xapi_commands`. These are `spark:` scopes (user-level), not `spark-admin:` scopes. The official Webex API documentation does not indicate that `spark-admin:devices_read/write` can substitute for these scopes. Ensure your token explicitly includes the `spark:xapi_*` scopes for xAPI operations.

7. **Configuration key paths use different separators in different contexts.** The key filter (for reading) uses dot-notation: `Audio.Ultrasound.MaxVolume`. The update path field uses dots for the key portion but forward slashes for the path suffix: `Audio.Ultrasound.MaxVolume/sources/configured/value`. Do not mix them up.

8. **The `device-configurations update` command's `--op` and `--path` flags are non-functional.** They produce a flat JSON object instead of the required JSON Patch array, and provide no way to set a value. Always use `--json-body` for configuration updates.

9. **xAPI `create` with `--json-body` does not auto-inject deviceId.** When you pass `--json-body`, the CLI uses the JSON body as-is without injecting the `--device-id` value. You must include `"deviceId"` in your JSON body manually. Without `--json-body`, the CLI correctly populates `deviceId` from `--device-id`.

10. **Device configuration schema is device-reported and firmware-dependent.** The set of available config keys is not static — each device reports its own schema when it registers with Webex cloud. Newer PhoneOS/RoomOS firmware versions may expose keys that older versions do not. Offline or `offline_expired` devices retain a stale schema. A key visible in Control Hub's UI may not appear in the Device Configurations API if the device's firmware hasn't been updated to a version that includes it in the reported schema.

11. **Per-line ringtone (`Lines.Line[N].CallFeatureSettings.Ringtone`) is available on PhoneOS 4.1+.** On PhoneOS 3.5.1 and 3.6.1 the key does not appear in the Device Configurations API schema — only `Lines.Line[N].CallFeatureSettings.MissedCallNotification` is present on those versions. On PhoneOS 4.1.1 (build 20260318), the `Ringtone` key is present and writable for all 16 line positions. Value space is `"No Ring"` or `"1"` through `"13"`. Set per-line ringtones with a single multi-operation PATCH: `[{"op": "replace", "path": "Lines.Line[1].CallFeatureSettings.Ringtone/sources/configured/value", "value": "2"}, ...]`. Revert a line to default with `"op": "remove"`.
12. **Static device settings API and dynamic settings API are separate surfaces.** Static (`/telephony/config/devices/{id}/settings`) uses JSON objects under `customizations.mpp`. Dynamic (`/telephony/config/devices/{id}/dynamicSettings`) uses tag-based addressing (`%ENABLE_BLUETOOTH%`). Do not mix them — use static API for standard MPP/PhoneOS settings.

---

## See Also

- [devices-core.md](devices-core.md) — Device CRUD, activation codes, MAC provisioning, telephony device settings
- [devices-dect.md](devices-dect.md) — DECT networks, base stations, handsets
- [devices-workspaces.md](devices-workspaces.md) — Workspace creation, workspace call settings, workspace locations
- [authentication.md](authentication.md) — Token types, scopes, OAuth flows
