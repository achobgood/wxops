---
name: manage-devices
description: |
  Manage Webex Calling devices using wxcli CLI commands: phones (MPP, ATA, room devices),
  DECT networks, workspaces, activation codes, device settings, line key templates, and hot desking.
  Guides the user from prerequisites through provisioning, activation, configuration, and verification.
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [device-operation]
---

# Manage Devices Workflow

## Step 1: Load references

1. Read `docs/reference/devices-core.md` for device CRUD, activation codes, MAC provisioning, line key templates, device settings
2. Read `docs/reference/devices-dect.md` for DECT networks, base stations, handsets, hot desking
3. Read `docs/reference/devices-workspaces.md` for workspace creation, workspace device assignment, workspace call settings
4. Read `docs/reference/authentication.md` for auth token conventions

## Step 2: Verify auth token

Before any API calls, confirm the user has a working auth token:

```bash
wxcli whoami
```

If this fails, stop and resolve authentication first (`wxcli configure`). Required scopes vary by operation:

| Operation | Read Scope | Write Scope |
|-----------|-----------|-------------|
| Cloud device CRUD, tags | `spark-admin:devices_read` | `spark-admin:devices_write` |
| Activation codes | `spark-admin:devices_read` | `spark-admin:devices_write` + `identity:one_time_password` |
| Telephony device config (members, settings, line keys, layout) | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |
| Workspaces | `spark-admin:workspaces_read` | `spark-admin:workspaces_write` |
| DECT networks, base stations, handsets | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |

## Step 3: Identify which device operation to perform

Ask the user what they want to do. Present this decision matrix if they are unsure:

| Need | Operation | CLI Group |
|------|-----------|-----------|
| Add a Cisco MPP phone or ATA by MAC address | **Create device by MAC** | `wxcli devices` |
| Generate a code for a phone to self-register | **Activation code** | `wxcli devices` |
| View/manage devices in the org | **List/show/delete devices** | `wxcli devices` |
| Assign lines, shared lines, or members to a phone | **Device members** | `wxcli device-settings` |
| Configure line keys, speed dials, BLF monitoring | **Line key templates / layout** | `wxcli device-settings` |
| Change phone display, ringtone, or device-level settings | **Device settings** | `wxcli device-settings` |
| Set up a wireless DECT phone system | **DECT network** | `wxcli dect-devices` |
| Create a conference room or lobby phone workspace | **Workspace** | `wxcli workspaces` |
| Allow users to temporarily use a shared phone | **Hot desking** | `wxcli hot-desk` / `wxcli hot-desking-portal` |
| Validate MAC addresses before provisioning | **MAC validation** | `wxcli device-settings` |

**Not a hardware operation?** For RoomOS software configuration, workspace personalization, or xAPI commands (dial, volume, standby, room analytics), use the `device-platform` skill instead.

## Step 4: Prerequisites

Before any device operation, verify these exist and gather operation-specific requirements.

### 4a. Location exists

All devices and workspaces are location-scoped. Confirm the target location:

```bash
wxcli locations list --output json
```

Capture the `location_id` for the target location.

### 4b. Check device configuration mode (for settings operations)

**If the user's request involves reading or changing device settings** (not just CRUD, line assignment, or activation), determine which API surface the target device uses:

1. Look up the device:
   ```bash
   wxcli devices list --mac MAC_ADDRESS --output json
   ```

2. Check the `product` field in the response. **Route based on model family:**
   - **9800-series** (product contains "9811", "9821", "9841", "9851", "9861", or "9871"): This device uses RoomOS config keys. **Redirect to the `device-platform` skill** with context: "This is a 9800-series phone that uses `device-configurations` (RoomOS config keys), not `device-settings`."
   - **Room, Board, Desk series**: Same — redirect to `device-platform` skill.
   - **MPP 68xx, 78xx, 88xx, ATA**: Continue with `device-settings` commands in this skill.

**Why this matters:** The 9800-series phones are `productType: phone` but run PhoneOS (RoomOS-derived). Calling `device-settings` on them returns 400 "device type does not support settings through Webex Calling." The agent must check the model BEFORE attempting settings operations.

See `docs/reference/devices-core.md` Section 5a (Device Settings API Router) for the full routing table.

### 4c. User or workspace exists (for device assignment)

Devices must be assigned to a person or workspace:

```bash
# List calling-enabled users
wxcli users list --calling-enabled --output json

# List workspaces
wxcli workspaces list --output json
```

### 4d. Phone numbers/extensions available

```bash
wxcli numbers list --location-id LOCATION_ID --output json
```

### 4e. MPP/ATA phone prerequisites

| Requirement | Details |
|-------------|---------|
| Valid MAC address | 12 hex characters (e.g., `AABBCCDDEEFF`). Validate with `wxcli device-settings validate-a-list --macs AABBCCDDEEFF` |
| Target person/workspace | Must exist before device creation |
| Device model | Must be in supported catalog |
| SIP password | Only for 3rd-party (non-Cisco) devices |

### 4f. Activation code prerequisites

| Requirement | Details |
|-------------|---------|
| Target person/workspace | Must exist |
| Model parameter | Required for phones; optional for RoomOS collaboration devices |

### 4g. DECT prerequisites

| Requirement | Details |
|-------------|---------|
| Location | Must exist |
| Base station MAC addresses | Physical hardware MAC required |
| Dependency chain | Network --> Base Station(s) --> Handset(s). Cannot skip steps |

### 4h. Workspace device prerequisites

| Requirement | Details |
|-------------|---------|
| Workspace | Must be created first with Webex Calling enabled and a location assigned |
| `location_id` and `supported_devices` | Immutable after creation -- set correctly on creation |
| Hot-desk-only workspaces | Cannot have `phoneNumber`, `extension`, `calendar`, or `deviceHostedMeetings` set |

### 4i. Device settings prerequisites

| Requirement | Details |
|-------------|---------|
| Line key template | Device model must match. Template applies org-wide or by location/tag filter |
| Device settings GET/PUT | `deviceModel` parameter is required |

### 4j. Hot desking prerequisites

| Requirement | Details |
|-------------|---------|
| Workspace side | `hotdeskingStatus` must be `on` |
| Person side | Hoteling must be enabled on person's profile via `wxcli device-settings update-hoteling` |

---

## Step 5: Build and present deployment plan -- [SHOW BEFORE EXECUTING]

Before executing any commands, present the full plan to the user:

```
DEPLOYMENT PLAN
===============
Operation: [device operation type]
Location: [name] ([location_id])
Target: [person/workspace name] ([id])

Device Details:
  Type: [MPP phone / ATA / DECT / Room device]
  Model: [model name]
  MAC: [mac_address or "Activation code"]
  Assignment: [person / workspace]

Configuration:
  [Operation-specific settings listed here]

Prerequisites verified:
  [check] Location exists
  [check] Person/workspace exists
  [check] MAC address validated (if applicable)
  [check] [Operation-specific prereqs]

Commands to execute:
  wxcli [group] [command] ...
  wxcli device-settings apply-changes-for DEVICE_ID (if settings changed)

Proceed? (yes/no)
```

**Wait for user confirmation before executing.**

## Step 6: Execute via wxcli

Run the commands in order. For multi-step operations (e.g., workspace + device + settings), execute sequentially.

Handle errors explicitly:
- **401/403**: Token expired or insufficient scopes -- run `wxcli configure` to re-authenticate
- **400 "MAC address unavailable"**: MAC already registered to another device -- check with `wxcli device-settings validate-a-list`
- **400 "Model not supported"**: Use `wxcli device-settings list-supported-devices-dect-networks` or check supported catalog
- **409**: Name or resource conflict -- ask user for alternate

**Always call `apply-changes-for` after updating device settings, members, or layout** to push configuration to the physical device.

### 6a. Device lifecycle -- Create, Activate, Configure, Manage

**List and discover devices:**

```bash
# List all devices in the org
wxcli devices list --output json

# Show details for a specific device
wxcli devices show DEVICE_ID --output json
```

**Create a device by MAC address:**

Collect from user:

| Parameter | Required | Notes |
|-----------|:--------:|-------|
| MAC address | Yes | 12 hex characters (e.g., `AABBCCDDEEFF`) |
| Person ID or Workspace ID | Yes | Who/what the device is assigned to |
| Model | Yes | Must be from the supported devices catalog |
| Password | Only for 3rd-party | SIP password for non-Cisco devices |

```bash
# Validate MAC first
wxcli device-settings validate-a-list --macs AABBCCDDEEFF --output json

# Create the device
wxcli devices create --mac AABBCCDDEEFF --workspace-id WORKSPACE_ID --model "DMS Cisco 8845"
```

**Generate activation code:**

Activation codes allow a phone to self-register when the user enters the code on the phone screen.

```bash
# For a workspace device
wxcli devices create-activation-code --workspace-id WORKSPACE_ID

# For a person's device (model required for phones)
wxcli devices create-activation-code --person-id PERSON_ID --model "DMS Cisco 8845"
```

The code expires after a set period. The user enters it on the phone's activation screen, and the device auto-registers with Webex Calling.

Activation codes provide a zero-touch provisioning workflow:

1. **Admin generates code** via `wxcli devices create-activation-code`
2. **Code is communicated** to the on-site technician or end user
3. **User enters code** on the phone's activation screen
4. **Phone auto-registers** with Webex Calling, downloads config, and becomes operational
5. **Code expires** after the configured period (typically 7 days)

> **NOTE:** Activation codes for phones require a `model` parameter. RoomOS collaboration devices do not require a model.

**Delete a device:**

```bash
wxcli devices delete DEVICE_ID
```

> **WARNING:** Deleting a device deregisters it. The device must be reactivated (new activation code or re-provisioned by MAC) to be reused.

**Update device tags:**

```bash
wxcli devices update DEVICE_ID --output json
```

> **NOTE:** Tag operations use JSON Patch format. The CLI handles this internally. Tags are useful for filtering devices in bulk operations (e.g., apply line key templates by tag).

### 6b. DECT workflow -- Network, Base Station, Handset (strict dependency)

DECT provisioning follows a strict dependency chain. Each step depends on the previous one completing first.

```
DECT Network --> Base Station(s) --> Handset(s)
   (step 1)        (step 2)          (step 3)
```

**You cannot skip steps. A base station requires a network. A handset requires a base station.**

**Create a DECT network:**

Collect from user:

| Parameter | Required | Notes |
|-----------|:--------:|-------|
| Location ID | Yes | Positional argument |
| Name | Yes | Unique per location, 1-40 characters |
| Model | Yes | `DMS Cisco DBS110` (single-cell, 1 base, 30 lines) or `DMS Cisco DBS210` (multi-cell, up to 250 bases, 1000 lines) |
| Default access code enabled | Yes | `true` = shared 4-digit code; `false` = auto-generated per-handset |
| Default access code | If enabled | 4 numeric digits, unique within the location |
| Display name | No | Shown on handsets, max 11 characters |

```bash
# Create DECT network
wxcli dect-devices create LOCATION_ID \
  --name "Building A DECT" \
  --model "DMS Cisco DBS210" \
  --default-access-code-enabled \
  --default-access-code 1234 \
  --display-name "Bldg A"

# List DECT networks
wxcli dect-devices list --output json

# Show network details
wxcli dect-devices show LOCATION_ID DECT_NETWORK_ID --output json
```

**Add base stations:**

Base stations require MAC addresses from the physical DECT base station hardware.

```bash
# Create base station(s) by MAC
wxcli dect-devices create-base-stations LOCATION_ID DECT_NETWORK_ID \
  --base-station-macs AABBCCDDEEFF

# List base stations
wxcli dect-devices list-base-stations LOCATION_ID DECT_NETWORK_ID --output json

# Show base station details
wxcli dect-devices show-base-stations LOCATION_ID DECT_NETWORK_ID BASE_STATION_ID --output json
```

**Add handsets:**

Each handset supports up to 2 lines. Line 1 must be a person or workspace (place). Line 2 can also be a virtual line.

```bash
# Search for available members to assign to handsets
wxcli dect-devices list-available-members --output json

# Add a single handset
wxcli dect-devices create-handsets LOCATION_ID DECT_NETWORK_ID \
  --line1-member-id PERSON_ID \
  --custom-display-name "Reception"

# Add handsets in bulk (up to 50)
wxcli dect-devices create-bulk LOCATION_ID DECT_NETWORK_ID --json-body '{
  "items": [
    {"line1MemberId": "PERSON_ID_1", "customDisplayName": "User 1"},
    {"line1MemberId": "PERSON_ID_2", "customDisplayName": "User 2"}
  ]
}'

# List handsets
wxcli dect-devices list-handsets LOCATION_ID DECT_NETWORK_ID --output json

# Update handset line assignment
wxcli dect-devices update-handsets LOCATION_ID DECT_NETWORK_ID HANDSET_ID \
  --line1-member-id NEW_PERSON_ID \
  --custom-display-name "Updated Name"
```

**DECT serviceability password:**

```bash
# Check password status
wxcli dect-devices show-serviceability-password LOCATION_ID DECT_NETWORK_ID --output json

# Generate and enable (WARNING: may reboot entire DECT network)
wxcli dect-devices generate-and-enable LOCATION_ID DECT_NETWORK_ID --output json
```

**DECT association queries:**

```bash
# DECT networks associated with a person
wxcli dect-devices list-dect-networks-people PERSON_ID --output json

# DECT networks associated with a workspace
wxcli dect-devices list-dect-networks-workspaces WORKSPACE_ID --output json
```

### 6c. Workspace devices -- Create workspace, assign device, configure settings

**Create a Webex Calling workspace:**

Collect from user:

| Parameter | Required | Notes |
|-----------|:--------:|-------|
| Display name | Yes | Workspace name |
| Location ID | Yes | Cannot be changed after creation |
| Supported devices | Yes | `phones` (MPP) or `collaborationDevices` (Room/Board/Desk). Cannot be changed after creation |
| Extension or phone number | Yes (one of) | Not applicable for hot-desk-only workspaces |
| Workspace type | No | `desk`, `meetingRoom`, `huddle`, `focus`, `open`, `other` |
| Hotdesking status | No | `on` or `off` |
| Calling license ID | No | Auto-assigned from active subscriptions if omitted |

```bash
# Create a workspace
wxcli workspaces create --json-body '{
  "displayName": "Lobby Phone",
  "locationId": "LOCATION_ID",
  "type": "desk",
  "supportedDevices": "phones",
  "hotdeskingStatus": "off",
  "calling": {
    "type": "webexCalling",
    "webexCalling": {
      "extension": "2001",
      "locationId": "LOCATION_ID"
    }
  }
}'

# List workspaces
wxcli workspaces list --output json

# Show workspace details
wxcli workspaces show WORKSPACE_ID --output json

# Get workspace capabilities
wxcli workspaces show-capabilities WORKSPACE_ID --output json
```

**Assign a device to the workspace:**

After creating the workspace, assign a device using either MAC address or activation code:

```bash
# Option 1: Create device by MAC and assign to workspace
wxcli devices create --mac AABBCCDDEEFF --workspace-id WORKSPACE_ID --model "DMS Cisco 8845"

# Option 2: Generate activation code for the workspace
wxcli devices create-activation-code --workspace-id WORKSPACE_ID
```

**List workspace devices:**

```bash
# List telephony devices assigned to a workspace
wxcli device-settings list-devices-workspaces WORKSPACE_ID --output json
```

**Configure workspace call settings:**

Workspace call settings mirror person call settings. Use `wxcli workspace-settings`:

```bash
# Call forwarding
wxcli workspace-settings show WORKSPACE_ID --output json
wxcli workspace-settings update WORKSPACE_ID --json-body '{"callForwarding": {"always": {"enabled": true, "destination": "+15551234567"}}}'

# Call waiting
wxcli workspace-settings show-call-waiting WORKSPACE_ID --output json
wxcli workspace-settings update-call-waiting WORKSPACE_ID --enabled

# Caller ID
wxcli workspace-settings list WORKSPACE_ID --output json

# Monitoring (BLF)
wxcli workspace-settings show-monitoring WORKSPACE_ID --output json

# DND
wxcli workspace-settings show-do-not-disturb WORKSPACE_ID --output json
wxcli workspace-settings update-do-not-disturb WORKSPACE_ID --enabled

# Voicemail
wxcli workspace-settings show-voicemail WORKSPACE_ID --output json
```

**Delete a workspace:**

```bash
wxcli workspaces delete WORKSPACE_ID
```

> **WARNING:** Deleting a workspace also deletes all associated devices. Those devices must be reactivated to be reused.

### 6d. Device settings configuration

**Device members (line assignment):**

Manage which users/lines appear on a phone:

```bash
# Get current members on a device
wxcli device-settings list DEVICE_ID --output json

# Search for available members to add as shared lines
wxcli device-settings list-available-members DEVICE_ID --output json

# Update members (add shared line appearance)
wxcli device-settings update DEVICE_ID --json-body '{
  "members": [
    {"id": "PRIMARY_PERSON_ID", "port": 1, "lineType": "PRIMARY", "primaryOwner": true},
    {"id": "SHARED_PERSON_ID", "port": 2, "lineType": "SHARED_LINE", "primaryOwner": false}
  ]
}'

# Apply changes to push config to the physical device
wxcli device-settings apply-changes-for DEVICE_ID
```

**Device-level settings (MPP/ATA):**

```bash
# Get device settings (model required)
wxcli device-settings show-settings-devices DEVICE_ID --device-model "DMS Cisco 8845" --output json

# Update device settings
wxcli device-settings update-settings-devices DEVICE_ID --json-body '{
  "customEnabled": true,
  "customizations": {"mpp": {"displayNameFormat": "PERSON_LAST_THEN_FIRST_NAME"}}
}'

# Get person-level device settings (compression)
wxcli device-settings show-settings-devices-3 PERSON_ID --output json

# Get workspace-level device settings (compression)
wxcli device-settings show-settings-devices-4 WORKSPACE_ID --output json

# Get location-level device settings
wxcli device-settings show-settings-devices-1 LOCATION_ID --output json

# Get org-level device settings
wxcli device-settings show-settings-devices-2 --output json
```

**Line key templates:**

Line key templates define the button layout for phone models org-wide:

```bash
# List existing templates
wxcli device-settings list-line-key-templates --output json

# Create a template
wxcli device-settings create --json-body '{
  "templateName": "Standard Layout",
  "deviceModel": "DMS Cisco 8845",
  "lineKeys": [
    {"lineKeyIndex": 1, "lineKeyType": "PRIMARY_LINE"},
    {"lineKeyIndex": 2, "lineKeyType": "MONITOR"},
    {"lineKeyIndex": 3, "lineKeyType": "SPEED_DIAL", "lineKeyLabel": "Front Desk", "lineKeyValue": "1000"},
    {"lineKeyIndex": 4, "lineKeyType": "OPEN"}
  ]
}'

# Preview how many devices would be affected
wxcli device-settings preview-apply-line TEMPLATE_ID --output json

# Apply template to devices
wxcli device-settings create-apply-line-key-template --json-body '{
  "action": "APPLY_TEMPLATE",
  "templateId": "TEMPLATE_ID"
}'

# Check apply job status
wxcli device-settings list-apply-line-key-template --output json
wxcli device-settings show-apply-line-key-template JOB_ID --output json
```

**Line key types:**

| Type | Description |
|------|-------------|
| `PRIMARY_LINE` | User's primary line |
| `SHARED_LINE` | Shared line appearance |
| `MONITOR` | BLF (busy lamp field) monitoring |
| `CALL_PARK_EXTENSION` | Dedicated call park button |
| `SPEED_DIAL` | Speed dial (requires label + value) |
| `OPEN` | Available for user self-configuration |
| `CLOSED` | Locked/unavailable |
| `MODE_MANAGEMENT` | Operating mode control |

**Device layout (per-device customization):**

```bash
# Get current device layout
wxcli device-settings list-layout DEVICE_ID --output json

# Update layout
wxcli device-settings update-layout DEVICE_ID --json-body '{
  "layoutMode": "CUSTOM",
  "lineKeys": [
    {"lineKeyIndex": 1, "lineKeyType": "PRIMARY_LINE"},
    {"lineKeyIndex": 2, "lineKeyType": "SPEED_DIAL", "lineKeyLabel": "Lobby", "lineKeyValue": "2000"}
  ]
}'
```

**Background images:**

```bash
# List org background images
wxcli device-settings list-background-images --output json

# Upload a background image to a device
wxcli device-settings upload-a-device DEVICE_ID --file /path/to/image.png

# Delete background images
wxcli device-settings delete-background-images --json-body '{
  "backgroundImages": [{"fileName": "logo.png", "forceDelete": true}]
}'
```

**MAC address validation:**

```bash
wxcli device-settings validate-a-list --macs AABBCCDDEEFF,112233445566 --output json
```

States: `AVAILABLE`, `UNAVAILABLE`, `DUPLICATE_IN_LIST`, `INVALID`

### 6e. Hot desking configuration

Hot desking allows users to temporarily sign into a shared workspace phone and use it as their own.

**Workspace side: enable hot desking:**

When creating a workspace, set `hotdeskingStatus` to `on`. For hot-desk-only workspaces, do not set `phoneNumber`, `extension`, `calendar`, or `deviceHostedMeetings`.

**Person side: enable hoteling:**

Use `wxcli device-settings update-hoteling` to enable hoteling on a person's profile so they can sign into hot desk workspaces.

**Manage hot desk sessions:**

```bash
# List active hot desk sessions
wxcli hot-desk list --output json

# List sessions for a specific person
wxcli hot-desk list --person-id PERSON_ID --output json

# List sessions for a specific workspace
wxcli hot-desk list --workspace-id WORKSPACE_ID --output json

# End a hot desk session
wxcli hot-desk delete SESSION_ID
```

**Voice portal hot desking sign-in:**

```bash
# View location-level voice portal hot desking settings
wxcli hot-desking-portal show LOCATION_ID --output json

# Update location-level settings
wxcli hot-desking-portal update LOCATION_ID --json-body '{...}'

# View user-level guest hot desking settings
wxcli hot-desking-portal show-guest PERSON_ID --output json
```

---

## Step 7: Verify

After execution, fetch details back and confirm:

```bash
# Verify device creation
wxcli devices show DEVICE_ID --output json

# Verify DECT network
wxcli dect-devices show LOCATION_ID DECT_NETWORK_ID --output json

# Verify workspace
wxcli workspaces show WORKSPACE_ID --output json

# Verify device members/lines
wxcli device-settings list DEVICE_ID --output json

# Verify device layout
wxcli device-settings list-layout DEVICE_ID --output json

# Verify workspace devices
wxcli device-settings list-devices-workspaces WORKSPACE_ID --output json
```

## Step 8: Report results

Present the results:

```
DEVICE OPERATION COMPLETE
=========================
Operation: [type]
Device: [display_name]
ID: [device_id]
MAC: [mac_address]
Model: [model]
Assigned to: [person/workspace name] ([id])
Location: [location_name]
Status: [activation_state]

Next steps:
  - [Operation-specific next steps]
  - [e.g., "Enter activation code XXXX-XXXX on the phone"]
  - [e.g., "Configure line key template for standardized button layout"]
  - [e.g., "Add shared line appearances via device-settings update"]
```

---

## Critical Rules

1. **Always verify location exists** before any device operation. Devices and workspaces are location-scoped.
2. **Always show the deployment plan** (Step 5) and wait for user confirmation before executing.
3. **Always call `apply-changes-for` after settings changes.** After updating device members, settings, or layout, call `wxcli device-settings apply-changes-for DEVICE_ID` to push config to the physical device. Without this, changes exist only in the cloud.
4. **DECT dependency chain is strict.** Network must exist before base stations. Base stations must exist before handsets. You cannot skip steps.
5. **DECT serviceability password operations can reboot the entire network.** Generating or toggling the password triggers a network-wide reboot. Schedule during maintenance windows.
6. **90-second cooldown on DECT handset changes.** Adding or removing handsets within 90 seconds may leave base stations out of sync until rebooted.
7. **Adding a DECT handset to a Standard license user disables Webex Calling** on their mobile, tablet, desktop, and browser apps. Deleting the handset re-enables it. Use Professional licenses for users who need both.
8. **Workspace `location_id` and `supported_devices` are immutable.** Set correctly on creation; they cannot be changed afterward.
9. **Deleting a workspace deletes all associated devices.** Those devices must be reactivated (new activation code or MAC re-provision) to be reused.
10. **Hot-desk-only workspaces** cannot have `phoneNumber`, `extension`, `calendar`, or `deviceHostedMeetings` set. These cause errors if provided.
11. **`deviceModel` is required for device settings GET/PUT.** Omitting it from `wxcli device-settings show-settings-devices` returns an error.
12. **Device IDs differ between API surfaces.** The `id` from `GET /devices` (cloud CRUD) may differ from the telephony `callingDeviceId`. Use the correct ID for each CLI group.
13. **No API for auto-generated DECT access codes.** When `defaultAccessCodeEnabled` is `false`, per-handset codes are auto-generated but cannot be retrieved via API. Use Control Hub instead.
14. **DECT handset Line 1 vs Line 2 member types.** Line 1 supports only PEOPLE and PLACE. Line 2 also supports VIRTUAL_LINE. Virtual lines cannot be the primary (line 1) member.
15. **Activation codes for phones require a model parameter.** RoomOS collaboration devices do not require a model.
16. **Background image limits.** Max 100 images per org. Upload max 625 KB, `.jpeg` or `.png` only. Max 10 images per delete request.
17. **DECT network create response uses `dectNetworkId`, not `id`.** The CLI handles this, but if using raw HTTP, parse the correct key.
18. **DECT is not supported for Webex for Government (FedRAMP).**
19. **Workspace call settings mirror person call settings.** Use `wxcli workspace-settings` with the workspace ID. The sub-API is the same as person settings but workspace-scoped.

---

## Scope Quick Reference

| CLI Group | Read Scope | Write Scope |
|-----------|-----------|-------------|
| `wxcli devices` | `spark-admin:devices_read` | `spark-admin:devices_write` |
| `wxcli device-settings` | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |
| `wxcli dect-devices` | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |
| `wxcli workspaces` | `spark-admin:workspaces_read` | `spark-admin:workspaces_write` |
| `wxcli workspace-settings` | `spark-admin:workspaces_read` | `spark-admin:workspaces_write` |
| `wxcli hot-desk` | (undocumented) | (undocumented) |
| `wxcli hot-desking-portal` | `spark-admin:telephony_config_read` | `spark-admin:telephony_config_write` |

---

## Context Compaction Recovery

If context compacts mid-execution, recover by:
1. Read the deployment plan from `docs/plans/` to recover what was planned
2. Check what's already been created: run the relevant `list` / `show` commands
3. Resume from the first incomplete step
