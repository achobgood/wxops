# Device Platform Expansion — Design Spec

**Date:** 2026-03-19
**Status:** Draft
**Author:** Adam Hobgood + Claude
**Depends on:** Generator query_params fix (shipped), webex-device.json OpenAPI spec, existing manage-devices skill

## Problem

The wxcli CLI covers 3 device-spec command groups (`device-configurations`, `workspace-personalization`, `xapi`) with 6 commands total. These manage RoomOS device SOFTWARE — configuration templates, workspace personalization, and direct device control via xAPI. They are distinct from the calling-focused device commands (`devices`, `device-settings`, `dect-devices`) that manage phone provisioning and telephony configuration.

**No reference doc, skill, or agent routing exists for these 3 groups.** A collaboration admin deploying RoomOS configs, an integrator building xAPI automations, or an IT admin managing workspace personalization has no playbook support. The builder agent doesn't recognize these objectives, can't dispatch to a skill, and can't load relevant reference docs.

## Solution

Three deliverables:

1. **Reference doc** (`docs/reference/devices-platform.md`) — standalone doc covering the 3 API surfaces
2. **Skill** (`.claude/skills/device-platform/SKILL.md`) — guided workflow for device platform operations
3. **Agent + CLAUDE.md updates** — wire the new doc and skill into the builder agent's dispatch, interview, and reference loading

## Goals

- An inexperienced user saying "I want to deploy a config to all my room devices" gets routed to the right skill and guided through the full workflow
- An xAPI integrator saying "I want to send commands to a device" gets the same treatment
- No persona assumed — the playbook serves calling admins, collaboration admins, IT/security teams, integrators, and partner admins equally
- Clean boundary between calling device management (existing) and device platform management (new)
- All 6 CLI commands documented with verified `--help` output

## Non-Goals

- Modifying any CLI code (generator or generated commands)
- Modifying existing calling reference docs (`devices-core.md`, `devices-dect.md`, `devices-workspaces.md`)
- Modifying the existing `manage-devices` skill
- Documenting the entire xAPI command namespace (that's Cisco's RoomOS reference — we document how to USE the CLI to execute xAPI commands, with representative examples)
- Live-testing the 6 commands against the API (no test org available in this session)

---

## Deliverable 1: Reference Doc — `docs/reference/devices-platform.md`

### Purpose

Standalone reference for the three device platform APIs. A collaboration admin or xAPI integrator should be able to read this doc and understand what they can do, which CLI commands to use, and what scopes/prerequisites they need — without reading any calling device docs.

### Boundary Rules

| Topic | Owned by `devices-platform.md` | Owned by `devices-core.md` |
|-------|-------------------------------|---------------------------|
| RoomOS device configuration keys (Audio, Video, Conference, etc.) | Yes | No |
| Workspace personalization (user→workspace binding) | Yes | No |
| xAPI command execution and status queries | Yes | No |
| Device CRUD (list, create, delete, activate) | No | Yes |
| Telephony device settings (members, line keys, layout) | No | Yes (`device-settings`) |
| DECT networks, base stations, handsets | No | Yes (`devices-dect.md`) |
| Workspace creation and workspace call settings | No | Yes (`devices-workspaces.md`) |
| Getting a device ID (needed by all 3 platform APIs) | Cross-reference only — "Use `wxcli devices list` to get device IDs, see `devices-core.md`" | Yes |

### Doc Structure

```
# Device Platform Management (RoomOS Configurations, Personalization, xAPI)

## Overview
  - What this covers (3 APIs, device SOFTWARE management)
  - Signpost: "For phone provisioning, activation codes, DECT, line keys → devices-core.md"
  - Signpost: "For workspace creation and workspace call settings → devices-workspaces.md"

## Prerequisites
  - Working auth token (wxcli whoami)
  - At least one cloud-registered RoomOS device (for device-configurations and xAPI)
  - At least one workspace with a device (for workspace-personalization)
  - How to get a device ID: wxcli devices list --output json

## Scopes
  | API | Read Scope | Write Scope |
  | Device Configurations | spark-admin:devices_read | spark-admin:devices_write |
  | Workspace Personalization | spark-admin:workspaces_read | spark-admin:workspaces_write |
  | xAPI Status | spark:xapi_statuses | — |
  | xAPI Commands | — | spark:xapi_commands |
  Note: xAPI scopes are user-level (spark:), not admin-level (spark-admin:).
  Admin tokens with spark-admin:devices_read/write also work for xAPI.
  For full xAPI access (both status and commands), ensure your token has both read and
  write scopes for whichever scope type you use (user-level or admin-level).
  <!-- NEEDS VERIFICATION — xAPI scope behavior with admin vs user tokens -->

## 1. Device Configurations
  ### What It Does
    - Read/write RoomOS configuration keys (Audio.*, Video.*, Conference.*, etc.)
    - Configuration keys follow a hierarchical dot-notation namespace
    - Each key has a source (default vs configured) and editability rules
    - Changes are applied via JSON Patch (replace/remove operations)

  ### CLI Commands
    wxcli device-configurations show --device-id DEVICE_ID [--key "Audio.*"]
    wxcli device-configurations update --device-id DEVICE_ID --json-body '[{"op": "replace", "path": "Audio.Ultrasound.MaxVolume/sources/configured/value", "value": 70}]'

    NOTE: The update command's --op and --path flags exist but cannot set a value and do not
    produce a valid JSON Patch array. Always use --json-body for this command.

  ### Key Filtering
    - Absolute: "Conference.MaxReceiveCallRate" → one config
    - Wildcard: "Audio.Ultrasound.*" → all Audio Ultrasound configs
    - Range: "FacilityService.Service[1..3].Name" → first three
    - Note: square brackets must be URL-encoded (%5B / %5D) in raw HTTP; CLI handles this

  ### Configuration Update Pattern
    - op: "replace" (set value) or "remove" (revert to schema default)
    - path: must end in /sources/configured/value
    - Example — set max ultrasound volume to 70:
      wxcli device-configurations update --device-id DEVICE_ID --json-body '[{"op": "replace", "path": "Audio.Ultrasound.MaxVolume/sources/configured/value", "value": 70}]'
    - Example — remove a custom config (revert to default):
      wxcli device-configurations update --device-id DEVICE_ID --json-body '[{"op": "remove", "path": "Audio.Ultrasound.MaxVolume/sources/configured/value"}]'

  ### Raw HTTP (for operations beyond CLI)
    GET /v1/deviceConfigurations?deviceId=DEVICE_ID&key=Audio.*
    PATCH /v1/deviceConfigurations?deviceId=DEVICE_ID
      Content-Type: application/json-patch+json
      [{"op": "replace", "path": "Audio.Ultrasound.MaxVolume/sources/configured/value", "value": 70}]

## 2. Workspace Personalization
  ### What It Does
    - Temporarily personalizes a shared workspace device for a specific user
    - User's speed dials, favorites, call history appear on the workspace device
    - Async operation — returns a task, poll for completion (~30 seconds)
    - Use case: hot-desk-like personalization for room devices

  ### CLI Commands
    wxcli workspace-personalization create WORKSPACE_ID --email user@example.com
    wxcli workspace-personalization show WORKSPACE_ID

  ### Workflow
    1. Get workspace ID: wxcli workspaces list
    2. Personalize: wxcli workspace-personalization create WORKSPACE_ID --email user@example.com
    3. Poll for completion: wxcli workspace-personalization show WORKSPACE_ID
       - Returns { "success": true } or { "success": false, "errorDescription": "..." }
    4. Common error: "Device is offline" — device must be online and registered

  ### Relationship to Hot Desking
    - Hot desking (manage-devices skill) = telephony hot desking on MPP phones via voice portal
    - Workspace personalization = user preferences pushed to RoomOS collaboration devices
    - Different mechanisms, similar concept, different device types

  ### Raw HTTP
    POST /v1/workspaces/{workspaceId}/personalize  {"email": "user@example.com"}
    GET  /v1/workspaces/{workspaceId}/personalizationTask

## 3. xAPI (Device Command Execution & Status Queries)
  ### What It Does
    - Execute commands on RoomOS devices: dial, volume, standby, bookings, etc.
    - Query device status: network info, call state, room analytics, peripheral health
    - Direct programmatic control — the same as using the xAPI console on the device
    - Powerful integration surface for room booking, digital signage, custom automations

  ### CLI Commands
    wxcli xapi show --device-id DEVICE_ID --name "Audio.Volume"
    wxcli xapi create Standby.Activate --device-id DEVICE_ID
    wxcli xapi create Audio.Volume.Set --device-id DEVICE_ID --json-body '{"deviceId": "DEVICE_ID", "arguments": {"Level": 50}}'

    NOTE: When using --json-body, the CLI does NOT auto-inject --device-id into the body.
    You must include "deviceId" in the JSON body yourself. Without --json-body, the CLI
    auto-populates deviceId from --device-id (works for no-argument commands like Standby.Activate).

  ### Status Queries
    - --name accepts status expressions (dot-notation paths)
    - Multiple expressions: --name "Audio.Volume,SystemUnit.State.NumberOfActiveCalls"
    - Up to 10 expressions per request
    - Returns current values from the device in real-time

  ### Command Execution
    - commandName is the positional argument (dot-notation, e.g., Audio.Volume.Set)
    - --device-id identifies the target device
    - --json-body passes arguments: {"deviceId": "...", "arguments": {"Level": 50}}
    - Response contains command result or error

  ### Common xAPI Commands (representative, not exhaustive)
    | Command | Arguments | Use Case |
    | Audio.Volume.Set | Level (0-100) | Set volume |
    | Audio.Volume.Mute | — | Mute microphone |
    | Call.Dial | Number | Initiate a call |
    | Call.Disconnect | CallId | End a call |
    | Standby.Activate | — | Put device in standby |
    | Standby.Deactivate | — | Wake device |
    | Bookings.List | Days, Offset | Get calendar bookings |
    | Message.Send | Text | Display on-screen message |
    | UserInterface.Message.Alert.Display | Title, Text, Duration | Show alert popup |

  ### Common xAPI Status Queries (representative, not exhaustive)
    | Status Path | Returns |
    | Audio.Volume | Current volume level |
    | SystemUnit.State.NumberOfActiveCalls | Active call count |
    | Network[1].IPv4.Address | Device IP address |
    | RoomAnalytics.PeopleCount.Current | People in the room |
    | Peripherals.ConnectedDevice[*].Name | Connected peripherals |
    | Standby.State | Standby/active state |

  ### xAPI Command Reference
    Full xAPI namespace: https://roomos.cisco.com/xapi
    Device Developers Guide: developer.webex.com (xAPI section)
    The CLI exposes the cloud xAPI interface — same commands as local xAPI but via Webex cloud.

  ### Raw HTTP
    GET  /v1/xapi/status?deviceId=DEVICE_ID&name=Audio.Volume
    POST /v1/xapi/command/Audio.Volume.Set  {"deviceId": "DEVICE_ID", "arguments": {"Level": 50}}

## Gotchas
  1. xAPI only works with RoomOS devices (Room, Board, Desk series). MPP phones do not support xAPI.
  2. Device must be online and cloud-registered for xAPI commands to reach it.
  3. Device Configurations PATCH uses application/json-patch+json content type, not application/json.
     The CLI handles this; raw HTTP callers must set the header correctly.
  4. xAPI --name query param accepts comma-separated expressions but max 10 per request.
  5. Workspace personalization is async. Always poll the task endpoint; don't assume instant completion.
  6. xAPI scopes (spark:xapi_commands, spark:xapi_statuses) are user-level scopes.
     Admin tokens with spark-admin:devices_read/write should also work.
     <!-- NEEDS VERIFICATION — exact scope behavior -->
  7. Configuration key paths use / as separator in the update path field, but . as separator
     in the key filter. Don't mix them up.
     Key filter: "Audio.Ultrasound.MaxVolume"
     Update path: "Audio.Ultrasound.MaxVolume/sources/configured/value"

## See Also
  - devices-core.md — Device CRUD, activation codes, MAC provisioning
  - devices-dect.md — DECT networks, base stations, handsets
  - devices-workspaces.md — Workspace creation, workspace call settings, workspace locations
  - authentication.md — Token types, scopes, OAuth flows
```

### What Is NOT In This Doc

- No SDK method signatures (wxc_sdk DeviceConfigurationsApi) — the existing `devices-core.md` already covers that SDK surface. This doc is CLI + raw HTTP only.
- No calling device content — strict boundary per the table above.
- No exhaustive xAPI command list — we provide representative examples and link to Cisco's reference.

---

## Deliverable 2: Skill — `.claude/skills/device-platform/SKILL.md`

### Purpose

Guide any user through device platform operations via the wxcli CLI. The skill assumes no prior calling knowledge. A collaboration admin deploying RoomOS configs should get the same quality guidance as a calling admin deploying phones.

### Skill Metadata

```yaml
---
name: device-platform
description: |
  Manage RoomOS device configurations, workspace personalization, and xAPI device control
  using wxcli CLI commands. Covers device software configuration templates, user-to-workspace
  personalization, and programmatic device command execution and status queries.
  Guides the user from prerequisites through execution and verification.
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [device-platform-operation]
---
```

### Workflow Structure

The skill follows the same step pattern as all other playbook skills:

```
Step 1: Load references
  → Read docs/reference/devices-platform.md
  → Read docs/reference/authentication.md (for auth conventions)

Step 2: Verify auth token
  → wxcli whoami
  → Check scopes match the operation (device configs need spark-admin:devices_*, xAPI needs spark:xapi_*)

Step 3: Identify which device platform operation to perform
  Decision matrix:
  | Need | Operation | CLI Group |
  | Read/set RoomOS configuration keys on a device | Device configurations | wxcli device-configurations |
  | Deploy configuration templates across devices | Device configurations (bulk) | wxcli device-configurations + loop |
  | Personalize a workspace device for a user | Workspace personalization | wxcli workspace-personalization |
  | Send a command to a RoomOS device (dial, volume, standby, etc.) | xAPI command execution | wxcli xapi create |
  | Query device status (volume, call state, network, room analytics) | xAPI status query | wxcli xapi show |
  | Build a device automation/integration | xAPI (combination) | wxcli xapi show + create |

Step 4: Check prerequisites
  4a. Device exists and is cloud-registered RoomOS:
      wxcli devices list --output json
      → Confirm device is RoomOS (Room, Board, Desk series), not MPP phone
      → Capture device_id

  4b. For workspace personalization: workspace exists with a device:
      wxcli workspaces list --output json
      → Capture workspace_id

  4c. For xAPI: device is online
      wxcli xapi show --device-id DEVICE_ID --name "SystemUnit.State.System"
      → If error, device may be offline or not xAPI-capable

Step 5: Build and present deployment plan [SHOW BEFORE EXECUTING]
  (same pattern as all other skills — show plan, wait for user confirmation before executing)

Step 6: Execute via wxcli
  [Operation-specific command sequences — see reference doc for each]
  - Device configurations: show → filter → update → verify
  - Workspace personalization: create → poll → verify
  - xAPI: show status or create command → check result

Step 7: Verify
  Read back results and confirm operation succeeded.
  - Device configurations: re-read the config key to confirm new value
  - Workspace personalization: check task status shows success: true
  - xAPI: check command response for success/error

Step 8: Report results
  (same pattern as all other skills)
```

### Critical Rules (skill-specific)

1. **xAPI only works on RoomOS devices.** If the user asks to send an xAPI command to an MPP phone, stop and explain. MPP phones use device-settings, not xAPI.
2. **Always get a device ID first.** All 3 APIs require a device ID. The user may not have one — guide them through `wxcli devices list` to find it.
3. **Workspace personalization is async.** After creating, always poll with `show` until the task completes. Don't tell the user it's done until `success: true`.
4. **Device must be online for xAPI.** Commands fail silently or with unhelpful errors on offline devices. Check reachability first.
5. **Configuration PATCH content type.** If user falls back to raw HTTP, they must use `application/json-patch+json`, not `application/json`.
6. **Don't enumerate xAPI commands.** The namespace is huge. Ask the user what they want to DO, then look up the command name. Point them to roomos.cisco.com/xapi for the full reference.
7. **Scope mismatch between device-configurations and xAPI.** Device configs use admin scopes (`spark-admin:devices_*`). xAPI uses user-level scopes (`spark:xapi_*`). A token may have one but not the other. Diagnose scope issues early.

### What The Skill Does NOT Cover

- Phone provisioning, activation codes, DECT, line keys, hot desking → `manage-devices` skill
- Workspace creation → `manage-devices` skill
- Device CRUD (list/create/delete devices) → `manage-devices` skill (though the skill USES `wxcli devices list` to find device IDs)

---

## Deliverable 3: Agent + CLAUDE.md Updates

### 3a. Builder Agent — Interview Phase

**File:** `.claude/agents/wxc-calling-builder.md`
**Section:** INTERVIEW PHASE → Question 1: Objective (lines ~96-104)

**Current objective list:**
```
- Provisioning: creating users, assigning licenses, setting up locations
- Call features: auto attendants, call queues, hunt groups, ...
- Person settings: call forwarding, DND, caller ID, ...
- Location settings: internal dialing, voicemail policies, ...
- Routing: dial plans, trunks, route groups, ...
- Devices: phone provisioning, activation codes, DECT networks, workspace devices
- Call control: real-time call operations (dial, hold, transfer, ...)
- Monitoring: XSI real-time event streams, call webhooks, CDR analysis
- Bulk operations: CSV-driven mass provisioning, ...
```

**Add after the "Devices" line:**
```
- Device platform: RoomOS device configuration management, workspace personalization, xAPI device commands and status queries
```

**Rationale:** This is the routing signal. When a user says "deploy configs to my room devices" or "send an xAPI command", the agent needs to recognize it as device-platform, not calling-device. Placing it right after the Devices line creates a natural visual grouping while maintaining separation.

### 3b. Builder Agent — Skill Dispatch Table

**File:** `.claude/agents/wxc-calling-builder.md`
**Section:** SKILL DISPATCH → Dispatch Table (lines ~332-341)

**Add row after the "Phones, DECT, workspaces, activation codes" row:**

```markdown
| RoomOS device configs, workspace personalization, xAPI | `.claude/skills/device-platform/SKILL.md` | Device config management, xAPI commands, personalization workflow |
```

### 3c. Builder Agent — Skill Dispatch "How Dispatch Works" / "Multiple Skills Per Plan"

**File:** `.claude/agents/wxc-calling-builder.md`
**Section:** SKILL DISPATCH → Multiple Skills Per Plan (lines ~352-359)

**Add line after "Steps provisioning devices → read manage-devices":**
```
- Steps managing RoomOS configs, personalization, or xAPI → read device-platform
```

### 3d. Builder Agent — Reference Doc Loading

**File:** `.claude/agents/wxc-calling-builder.md`
**Section:** REFERENCE DOC LOADING (lines ~457-553)

**Add new section after "Devices (phones, DECT, workspaces)" (after line 500):**

```markdown
### Device Platform (RoomOS configurations, personalization, xAPI)
```
docs/reference/devices-platform.md    — device configs, workspace personalization, xAPI
```
```

### 3e. Builder Agent — skills frontmatter

**File:** `.claude/agents/wxc-calling-builder.md`
**Line 10:** `skills: provision-calling, configure-features, manage-call-settings, configure-routing, manage-devices, call-control, reporting, wxc-calling-debug`

**Change to:**
```
skills: provision-calling, configure-features, manage-call-settings, configure-routing, manage-devices, device-platform, call-control, reporting, wxc-calling-debug
```

### 3f. CLAUDE.md — File Map Updates

**File:** `CLAUDE.md`

**Agent & Skills table — add row after manage-devices:**
```markdown
| `.claude/skills/device-platform/` | Skill: manage RoomOS device configs, workspace personalization, xAPI |
```

**Reference Docs table — add row after devices-workspaces.md:**
```markdown
| `docs/reference/devices-platform.md` | RoomOS device configurations, workspace personalization, xAPI |
```

**Reference Doc Sync Protocol — update device file count (line 167):**
Change:
```
- Devices: `docs/reference/devices-*.md` (3 files: core, dect, workspaces)
```
To:
```
- Devices: `docs/reference/devices-*.md` (4 files: core, dect, workspaces, platform)
```

---

## Scope Overlap Analysis

This section explicitly documents where boundaries are drawn to prevent future confusion.

### Device ID: shared prerequisite, different owners

All 3 platform APIs and all calling device APIs require a device ID. The device ID comes from `wxcli devices list` (owned by `devices-core.md` / `manage-devices` skill). The `device-platform` skill and doc cross-reference this but don't duplicate the device listing workflow. The skill says: "Get your device ID first — use `wxcli devices list`."

### Workspace ID: shared prerequisite, different owners

Workspace personalization needs a workspace ID. Workspace creation is owned by `devices-workspaces.md` / `manage-devices` skill. The `device-platform` skill says: "Get your workspace ID — use `wxcli workspaces list`." If the workspace doesn't exist yet, the skill directs the user to the `manage-devices` skill to create it first.

### Hot desking vs. workspace personalization

Both let a user "temporarily use" a shared device. They are NOT the same:
- Hot desking = telephony feature on MPP phones, managed by manage-devices skill
- Workspace personalization = user preferences on RoomOS collaboration devices, managed by device-platform skill

The device-platform reference doc explains this distinction. The manage-devices skill does NOT mention workspace personalization (it doesn't need to).

### Background images

`devices-core.md` covers background images via `wxcli device-settings` (telephony device background images — MPP phone wallpapers). `devices-platform.md` does NOT cover background images (the device-configurations API manages RoomOS config keys, not image uploads). No overlap.

### Device configurations (API name collision)

`devices-core.md` documents the `DeviceConfigurationsApi` from wxc_sdk (the SDK wrapper). `devices-platform.md` documents the same underlying API (`/deviceConfigurations`) but via CLI commands and raw HTTP fallback patterns. This is intentional — the reference doc covers SDK method signatures, the platform doc covers CLI commands and raw HTTP. The skill always routes through CLI.

---

## Verification Criteria

Before marking implementation complete:

1. **Reference doc** exists at `docs/reference/devices-platform.md` and contains all sections from the structure above
2. **Skill** exists at `.claude/skills/device-platform/SKILL.md` and follows the workflow structure above
3. **All 6 CLI commands** appear in the reference doc with correct flags verified against `--help` output
4. **Builder agent** has all 5 updates (3a through 3e) applied
5. **CLAUDE.md** has both new rows in the file map and the updated device file count in the Sync Protocol
6. **Signposts** in `devices-platform.md` correctly point to `devices-core.md`, `devices-dect.md`, `devices-workspaces.md`
7. **No calling device content** leaked into the new doc or skill
8. **No existing files modified** except the builder agent and CLAUDE.md
9. **`<!-- NEEDS VERIFICATION -->` tags** on any scope or behavioral claims not verified against a live API
