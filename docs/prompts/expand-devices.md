# Playbook Expansion: Device Configuration & xAPI

## Context

The wxcli CLI now covers the `webex-device.json` OpenAPI spec: 3 unique command groups, ~6 commands covering device configurations, workspace personalization, and xAPI. These are DISTINCT from the calling-focused device commands already in the playbook (`wxcli devices`, `wxcli device-settings`, `wxcli dect-devices`). The calling device skills manage phone provisioning and activation; these device-spec groups manage device SOFTWARE configuration, workspace personalization, and direct device control via xAPI.

**What exists today:**
- Calling device commands: `wxcli devices`, `wxcli device-settings`, `wxcli dect-devices`, `wxcli hot-desk` (covered by `manage-devices` skill)
- NEW device-spec commands: `wxcli device-configurations`, `wxcli workspace-personalization`, `wxcli xapi` (NOT yet covered)
- The `manage-devices` skill covers calling device provisioning only
- No reference docs or skills for device configuration management or xAPI

**Your job:** Investigate the device-spec CLI surface, understand how it differs from calling device management, map it to Control Hub functionality and real-world use cases, then decide: expand the existing `manage-devices` skill or create new ones.

---

## Phase 1: Discovery

### 1a. Map the 3 device-spec CLI groups

Run `--help` on each:

```bash
wxcli device-configurations --help
wxcli workspace-personalization --help
wxcli xapi --help
```

For each, note: command count, what it actually does, how it differs from the calling device groups.

### 1b. Understand the distinction

This is the critical investigation. There are TWO layers of device management in Webex:

1. **Calling device management** (already covered): phone provisioning, activation codes, line keys, DECT, device call settings. These are telephony operations — "what phone does this user have and how is it configured for calling."

2. **Device platform management** (this expansion): device software configurations, macros, branding, xAPI commands. These are device operations — "what software config does this device run, what UI extensions does it have, can I send commands to it directly."

Map the distinction clearly:

| Question | Calling Device (existing) | Device Platform (new) |
|----------|---------------------------|----------------------|
| "What phone does Alice have?" | `wxcli devices list` | N/A |
| "Configure Alice's line keys" | `wxcli device-settings` | N/A |
| "Deploy a macro to all room devices" | N/A | `wxcli device-configurations` |
| "Set a custom wallpaper on a device" | N/A | `wxcli workspace-personalization` |
| "Send a dial command to a device" | N/A | `wxcli xapi` |
| "Activate a new phone with activation code" | `wxcli devices` | N/A |

Verify this mapping by examining what each group actually does.

### 1c. Control Hub mapping

Map to Control Hub UI:

| Control Hub Area | CLI Group |
|------------------|-----------|
| Devices > Device Configurations (templates) | device-configurations |
| Workspaces > [device] > Personalization | workspace-personalization |
| Devices > [device] > xAPI (developer tools) | xapi |

### 1d. Identify use cases

**Device Configurations:**
- Deploy consistent branding/config across all room devices in an org
- Push macro packages to devices for custom integrations (room booking, hot desking UX, etc.)
- Manage configuration templates at scale
- Version control device configurations

**Workspace Personalization:**
- Set custom backgrounds/wallpapers on shared workspace devices
- Configure workspace-specific branding
- Manage personalization at scale across locations

**xAPI:**
- Programmatic device control (dial, volume, standby, etc.)
- Integration with room booking systems
- Custom automation (turn on lights when someone enters, start recording, etc.)
- Device health monitoring (get device status, network info, etc.)
- This is POWERFUL — xAPI gives direct command-level access to Cisco collaboration devices

### 1e. Scope requirements

Determine required scopes for each group. Common device scopes:
- `spark-admin:devices_read/write`
- `spark:devices_read/write` (user-level for personal devices)
- `spark-admin:workspace_personalization_read/write`
- `spark:xapi_commands` / `spark:xapi_statuses`

---

## Phase 2: Reference Doc

Since this is a small surface area (3 groups, ~6 commands), create ONE reference doc:

| File | Covers |
|------|--------|
| `docs/reference/devices-platform.md` | Device configurations, workspace personalization, xAPI |

Structure:
- Overview: how this differs from calling device management
- Device Configurations: templates, deployment, management
- Workspace Personalization: branding, backgrounds
- xAPI: command execution, status queries, event monitoring
- Scopes and prerequisites
- Gotchas
- Raw HTTP patterns if CLI doesn't cover all operations

**IMPORTANT:** Cross-reference with existing `docs/reference/devices-core.md` to avoid overlap and clearly delineate boundaries.

---

## Phase 3: Skill Decision

You have three options. Choose based on Phase 1 findings:

**Option A: Expand existing `manage-devices` skill**
Add a new section for "Device Platform Management" covering configurations, personalization, and xAPI. Pro: keeps all device knowledge in one place. Con: skill may get too large.

**Option B: Create a new `device-platform` skill**
Separate skill focused on device configs, personalization, and xAPI. Pro: clean separation. Con: users might not know which device skill to use.

**Option C: Fold xAPI into a separate `device-automation` skill**
xAPI is fundamentally different from configuration management — it's real-time device control, more like call-control than device-settings. If xAPI has significant depth, it might warrant its own skill focused on automation use cases.

Make your recommendation based on what you find in Phase 1. Document why.

---

## Phase 4: Agent & CLAUDE.md Updates

1. Update builder agent SKILL DISPATCH table if new skills created
2. Update builder agent INTERVIEW PHASE to recognize device platform objectives (distinct from calling device provisioning)
3. Update CLAUDE.md file map with new reference doc and any new skills
4. Add new reference doc to the agent's REFERENCE DOC LOADING section under an appropriate heading

---

## Constraints

- Do NOT modify any CLI code
- Do NOT modify existing calling reference docs
- Do NOT modify the existing `manage-devices` skill UNLESS you choose Option A
- Clearly distinguish calling device management from device platform management everywhere
- Every CLI command reference should be verified by running `--help`
- Mark unverified information with `<!-- NEEDS VERIFICATION -->`
- xAPI is a deep topic — document what the CLI supports, not the entire xAPI surface
