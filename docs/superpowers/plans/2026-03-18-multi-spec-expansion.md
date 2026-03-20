# Multi-Spec CLI Expansion: Admin, Device, and Messaging APIs

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the wxcli CLI to cover all four Webex OpenAPI specs — adding admin, device, and messaging commands alongside the existing calling commands.

**Architecture:** The generator (`tools/generate_commands.py`) already accepts `--spec` to target any OpenAPI 3.0 JSON file. We run it against each new spec, skipping tags that overlap with already-generated calling commands (identical endpoints confirmed via operationId). The generator's `seen_op_ids` dedup handles multi-tag overlap within a single spec, but cross-spec overlap requires skip patterns or a multi-spec orchestration approach. We choose the simplest path: add overlapping tags to `skip_tags` per-spec, and run the generator once per spec with spec-specific override sections.

**Tech Stack:** Python 3.11, Typer, OpenAPI 3.0 JSON specs. Same generator pipeline as calling: `openapi_parser.py` → `command_renderer.py` → Click command files.

---

## Key Design Decisions

### Cross-spec overlap handling

13 tags appear in multiple specs with **identical operationIds** (verified). Strategy:

| Overlapping Tag | In Specs | Resolution |
|---|---|---|
| People | calling, admin, messaging | **Already generated from calling.** Skip in admin + messaging. |
| Partner Reports/Templates | calling, admin | Already generated. Skip in admin. |
| Recording Report | calling, admin | Already generated. Skip in admin. |
| Reports | calling, admin | Already generated. Skip in admin. |
| Devices | calling, device | Already generated. Skip in device. |
| Device Call Settings | calling, device | Already generated. Skip in device. |
| Device Call Settings With Device Dynamic Settings | calling, device | Already generated. Skip in device. |
| Hot Desk | calling, device | Already generated. Skip in device. |
| Workspaces | calling, device | Already generated. Skip in device. |
| Beta Device Call Settings With Dynamic Device Settings | calling, device | Already skipped (Beta). Skip in device too. |
| Events | admin, messaging | Generate from admin. Skip in messaging. |
| Workspace Locations | admin, device | Generate from admin. Skip in device. |
| Workspace Metrics | admin, device | Generate from admin. Skip in device. |

### Name collision: `licenses`

The admin spec has a `Licenses` tag (3 endpoints). The hand-coded `licenses.py` uses wxc_sdk's `LicensesApi`. Resolution: generate the admin version as `licenses-api` (same pattern used for `locations` → `locations-api`). The hand-coded module stays for its richer wxc_sdk integration.

### `json-patch+json` content type

Two PATCH endpoints use `application/json-patch+json` instead of `application/json`: `PATCH /deviceConfigurations` (Device Configurations tag) and `PATCH /devices/{deviceId}` (Devices tag, shared between calling and device specs). The current `parse_request_body` only checks for `application/json` and `application/json;charset=UTF-8`. We need to add `application/json-patch+json` as a fallback content type.

**Note:** The calling spec's `Devices` tag was already generated but the `PATCH /devices/{deviceId}` endpoint currently has **no body fields** because the parser couldn't find `application/json` content. After the parser fix, regenerating the calling `Devices` tag will pick up the previously-missing `op`, `path`, and `value` fields. The `value` field is `type: array` (skipped for CLI flags), but `op` and `path` will become proper `--op` and `--path` options.

### `Recordings` vs `Converged Recordings`

The admin spec has `Recordings` (12 endpoints on `/recordings/` paths). The calling spec has `Converged Recordings` (9 endpoints on `/convergedRecordings/` paths). These are **different APIs** — no overlap. Both get generated. The admin `Recordings` auto-derives to `recordings` which collides with the calling `Converged Recordings` (already CLI-named `recordings`). Resolution: override admin's `Recordings` to `admin-recordings`.

### Spec-specific override sections

Rather than one monolithic `field_overrides.yaml`, we use spec-targeted sections within the same file. The `skip_tags` and `cli_name_overrides` grow to include new entries. The generator already reads these generically — no code change needed for per-spec overrides as long as we pass the right skip list.

**However**, the current skip_tags are global across all generator runs. When running against `webex-admin.json`, we need to skip different tags than when running against `webex-device.json`. Two options:

1. **Add all overlapping tags to global skip_tags** — safe because the calling spec already generated them.
2. **Spec-specific override files** — overkill for this.

We choose option 1. Add all overlap tags to `skip_tags` in `field_overrides.yaml`. Since these tags are identical across specs, skipping them from non-calling specs loses nothing.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `tools/field_overrides.yaml` | **Modify** | Add skip_tags for overlap, cli_name_overrides for new tags, table_columns for new list commands |
| `tools/openapi_parser.py` | **Modify** | Add `application/json-patch+json` content type support |
| `src/wxcli/main.py` | **Modify** | Add registration blocks for new command groups |
| `src/wxcli/commands/*.py` | **Generate** | New command files from admin/device/messaging specs |
| `CLAUDE.md` | **Modify** | Update CLI status, file map, command count |

---

## Task 1: Parser Fix — Support `json-patch+json` Content Type

**Files:**
- Modify: `tools/openapi_parser.py:143-158` (`parse_request_body` function)

### Step 1.1: Update `parse_request_body` to handle json-patch+json

- [ ] **Modify `parse_request_body` in `tools/openapi_parser.py`** — add `application/json-patch+json` as a third content type fallback:

Change line 153-156 from:
```python
    json_content = (
        content.get("application/json")
        or content.get("application/json;charset=UTF-8", {})
    )
```

To:
```python
    json_content = (
        content.get("application/json")
        or content.get("application/json;charset=UTF-8")
        or content.get("application/json-patch+json", {})
    )
```

- [ ] **Verify the fix works** — dry-run against device spec:

```bash
PYTHONPATH=. python3.11 tools/generate_commands.py --spec webex-device.json --tag "Device Configurations" --dry-run
```

Expected: Shows 2 endpoints (GET + PATCH) with correct fields parsed from the json-patch schema.

- [ ] **Regenerate the calling `Devices` tag** to pick up the previously-missing body fields:

```bash
PYTHONPATH=. python3.11 tools/generate_commands.py --spec webex-cloud-calling.json --tag "Devices"
pip3.11 install -e . -q
wxcli devices update --help
```

Expected: The `update` command now shows `--op` and `--path` options.

- [ ] **Commit**

```bash
git add tools/openapi_parser.py src/wxcli/commands/devices.py
git commit -m "fix: support application/json-patch+json content type in OpenAPI parser"
```

---

## Task 2: Update `field_overrides.yaml` — Skip Overlap Tags + New CLI Names

**Files:**
- Modify: `tools/field_overrides.yaml`

### Step 2.1: Add overlap tags to skip_tags

- [ ] **Add overlapping tags to `skip_tags`** so they're not re-generated when running against admin/device/messaging specs:

```yaml
skip_tags:
  - "Beta *"
  - "Call Settings For Me*"
  - "* Phase*"
  # Cross-spec overlaps (identical endpoints already generated from calling spec)
  - "Partner Reports/Templates"
  - "Recording Report"
  - "Reports"
  - "People"
  - "Devices"
  - "Device Call Settings"
  - "Device Call Settings With Device Dynamic Settings"
  - "Hot Desk"
  - "Workspaces"
```

**Note on tags NOT in skip_tags:**
- `Events` (admin + messaging) — NOT in calling spec. Generate from admin; when messaging spec runs, it overwrites with identical content. Only register once in main.py.
- `Workspace Locations` (admin + device) — NOT in calling spec. Generate from admin; device spec overwrites with identical content. Only register once.
- `Workspace Metrics` (admin + device) — NOT in calling spec. Same handling as Workspace Locations.
- `Licenses` — needs to be generated as `licenses-api` from admin (collision with hand-coded `licenses.py`).
- `Recordings` (admin) — different API from `Converged Recordings` (calling). Not an overlap.

### Step 2.2: Add cli_name_overrides for new tags

- [ ] **Add `cli_name_overrides` for tags with ugly or colliding auto-derived names:**

```yaml
  # Admin spec overrides
  "API - Domain Management": "domains"
  "Admin Audit Events": "audit-events"
  "Bulk Manage SCIM 2 Users and Groups": "scim-bulk"
  "Historical Analytics APIs": "analytics"
  "Identity Organization": "identity-org"
  "Licenses": "licenses-api"
  "Organization Contacts": "org-contacts"
  "Partner Administrators": "partner-admins"
  "Recordings": "admin-recordings"
  "SCIM 2 Groups": "scim-groups"
  "SCIM 2 Schemas": "scim-schemas"
  "SCIM 2 Users": "scim-users"
  "Security Audit Events": "security-audit"
  "Send Activation Email": "activation-email"
  "Settings": "org-settings"
  # Messaging spec overrides
  "Attachment Actions": "attachment-actions"
  "ECM folder linking": "ecm"
  "Team Memberships": "team-memberships"
```

Tags with clean auto-derived names (e.g., `Events` → `events`, `Groups` → `groups`, `Roles` → `roles`, `Messages` → `messages`, `Rooms` → `rooms`, `Teams` → `teams`, `Webhooks` → `webhooks`) do NOT need overrides.

### Step 2.3: Add table_columns for new list commands

- [ ] **Add `table_columns` for key new groups** (start minimal — can refine after live testing):

```yaml
"Licenses":
  list:
    table_columns:
      - ["ID", "id"]
      - ["Name", "name"]
      - ["Total Units", "totalUnits"]
      - ["Consumed", "consumedUnits"]

"Organizations":
  list:
    table_columns:
      - ["ID", "id"]
      - ["Display Name", "displayName"]

"Roles":
  list:
    table_columns:
      - ["ID", "id"]
      - ["Name", "name"]

"Groups":
  list:
    table_columns:
      - ["ID", "id"]
      - ["Display Name", "displayName"]
      - ["Member Count", "memberSize"]

"Workspace Locations":
  list:
    table_columns:
      - ["ID", "id"]
      - ["Display Name", "displayName"]
      - ["City", "address.city"]

"Rooms":
  list:
    table_columns:
      - ["ID", "id"]
      - ["Title", "title"]
      - ["Type", "type"]

"Teams":
  list:
    table_columns:
      - ["ID", "id"]
      - ["Name", "name"]

"Messages":
  list:
    table_columns:
      - ["ID", "id"]
      - ["Person Email", "personEmail"]
      - ["Text", "text"]

"Webhooks":
  list:
    table_columns:
      - ["ID", "id"]
      - ["Name", "name"]
      - ["Target URL", "targetUrl"]
      - ["Resource", "resource"]

"Recordings":
  list:
    table_columns:
      - ["ID", "id"]
      - ["Topic", "topic"]
      - ["Format", "format"]
      - ["Created", "timeRecorded"]
```

- [ ] **Commit**

```bash
git add tools/field_overrides.yaml
git commit -m "feat: add skip_tags, cli_name_overrides, and table_columns for admin/device/messaging specs"
```

---

## Task 3: Generate Admin Spec Commands

**Files:**
- Generate: `src/wxcli/commands/*.py` (new files for ~35 admin tags)
- Modify: `src/wxcli/main.py`

### Step 3.1: Dry-run the admin spec

- [ ] **Run the generator in dry-run mode** to verify tag processing, skip patterns, and CLI names:

```bash
PYTHONPATH=. python3.11 tools/generate_commands.py --spec webex-admin.json --all --dry-run
```

Expected:
- Tags overlapping with calling (`People`, `Partner Reports/Templates`, `Recording Report`, `Reports`) are SKIPPED
- ~35 unique admin tags generate commands (39 total minus 4 calling overlaps)
- `Licenses` generates as `licenses-api` (not `licenses`)
- `Recordings` generates as `admin-recordings` (not `recordings`)
- `Settings` generates as `org-settings` (not `settings`)
- `Events`, `Workspace Locations`, `Workspace Metrics` all generate (not in skip_tags)
- No errors

### Step 3.2: Generate admin commands

- [ ] **Run the generator for real:**

```bash
PYTHONPATH=. python3.11 tools/generate_commands.py --spec webex-admin.json --all
```

- [ ] **Copy the registration block** from the generator output.

### Step 3.3: Add admin registrations to main.py

- [ ] **Append the registration block** to `src/wxcli/main.py` after the existing auto-generated calling registrations. Add a comment separator:

```python
# Auto-generated from admin spec (webex-admin.json)
```

### Step 3.4: Verify the CLI loads

- [ ] **Reinstall and smoke test:**

```bash
pip3.11 install -e . -q
wxcli --help
wxcli audit-events --help
wxcli scim-users --help
wxcli organizations --help
wxcli admin-recordings --help
wxcli licenses-api --help
```

Expected: All new groups appear in `--help`, no import errors.

- [ ] **Commit**

```bash
git add src/wxcli/commands/ src/wxcli/main.py
git commit -m "feat: generate admin API commands from webex-admin.json OpenAPI spec"
```

---

## Task 4: Generate Device Spec Commands

**Files:**
- Generate: `src/wxcli/commands/*.py` (new files for ~3 device-unique tags)
- Modify: `src/wxcli/main.py`

### Step 4.1: Dry-run the device spec

- [ ] **Run the generator in dry-run mode:**

```bash
PYTHONPATH=. python3.11 tools/generate_commands.py --spec webex-device.json --all --dry-run
```

Expected:
- Calling overlaps (`Devices`, `Device Call Settings`, `Device Call Settings With Device Dynamic Settings`, `Hot Desk`, `Workspaces`) are SKIPPED via skip_tags
- `Workspace Locations` and `Workspace Metrics` regenerate (overwriting identical admin-generated files — harmless)
- ~3 device-unique tags generate: `Device Configurations`, `Workspace Personalization`, `xAPI`
- `Device Configurations` PATCH endpoint has body fields parsed from `json-patch+json` schema
- The generator will also output registration blocks for `workspace-locations` and `workspace-metrics` — **ignore these** since they're already registered from admin in Task 3

### Step 4.2: Generate device commands

- [ ] **Run the generator:**

```bash
PYTHONPATH=. python3.11 tools/generate_commands.py --spec webex-device.json --all
```

### Step 4.3: Add device registrations to main.py

- [ ] **Append ONLY the new device-unique registrations** to `src/wxcli/main.py`. The generator output will include registration blocks for ALL non-skipped tags — only add the ones not already registered from calling or admin:

```python
# Auto-generated from device spec (webex-device.json)
```

Expected new groups to register: `device-configurations`, `workspace-personalization`, `xapi`

**Skip these** (already registered from admin): `workspace-locations`, `workspace-metrics`

### Step 4.4: Verify the CLI loads

- [ ] **Reinstall and smoke test:**

```bash
pip3.11 install -e . -q
wxcli --help
wxcli device-configurations --help
wxcli xapi --help
wxcli workspace-personalization --help
```

- [ ] **Commit**

```bash
git add src/wxcli/commands/ src/wxcli/main.py
git commit -m "feat: generate device API commands from webex-device.json OpenAPI spec"
```

---

## Task 5: Generate Messaging Spec Commands

**Files:**
- Generate: `src/wxcli/commands/*.py` (new files for ~10 messaging tags)
- Modify: `src/wxcli/main.py`

### Step 5.1: Dry-run the messaging spec

- [ ] **Run the generator in dry-run mode:**

```bash
PYTHONPATH=. python3.11 tools/generate_commands.py --spec webex-messaging.json --all --dry-run
```

Expected:
- `People` is SKIPPED (already in calling skip_tags)
- `Events` overwrites the admin-generated version (identical endpoints — harmless)
- ~11 tags process total, but only 10 produce new unique command files

### Step 5.2: Generate messaging commands

- [ ] **Run the generator:**

```bash
PYTHONPATH=. python3.11 tools/generate_commands.py --spec webex-messaging.json --all
```

### Step 5.3: Add messaging registrations to main.py

- [ ] **Append ONLY new messaging-unique registrations** — skip `Events` (already registered from admin in Task 3):

```python
# Auto-generated from messaging spec (webex-messaging.json)
```

Expected new groups: `attachment-actions`, `ecm`, `hds`, `memberships`, `messages`, `room-tabs`, `rooms`, `team-memberships`, `teams`, `webhooks`

### Step 5.4: Verify the CLI loads

- [ ] **Reinstall and smoke test:**

```bash
pip3.11 install -e . -q
wxcli --help
wxcli rooms --help
wxcli messages --help
wxcli teams --help
wxcli webhooks --help
wxcli memberships --help
```

- [ ] **Commit**

```bash
git add src/wxcli/commands/ src/wxcli/main.py
git commit -m "feat: generate messaging API commands from webex-messaging.json OpenAPI spec"
```

---

## Task 6: Update CLAUDE.md and Final Verification

**Files:**
- Modify: `CLAUDE.md`

### Step 6.1: Full CLI smoke test

- [ ] **Run `wxcli --help`** and verify all groups appear. Count total groups.

- [ ] **Spot-check one command from each spec:**

```bash
wxcli auto-attendant list --help       # calling (existing)
wxcli organizations list --help        # admin (new)
wxcli device-configurations --help     # device (new)
wxcli rooms list --help                # messaging (new)
```

### Step 6.2: Update CLAUDE.md

- [ ] **Update the CLI status section** in `CLAUDE.md`:
  - Update command group count (was 62 for calling, now ~107 total)
  - Update the Quick Start to mention admin/device/messaging coverage
  - Add the three new spec files to the File Map
  - Update generator commands to show multi-spec usage:
    ```
    Regenerate calling:   PYTHONPATH=. python3.11 tools/generate_commands.py --spec webex-cloud-calling.json --all
    Regenerate admin:     PYTHONPATH=. python3.11 tools/generate_commands.py --spec webex-admin.json --all
    Regenerate device:    PYTHONPATH=. python3.11 tools/generate_commands.py --spec webex-device.json --all
    Regenerate messaging: PYTHONPATH=. python3.11 tools/generate_commands.py --spec webex-messaging.json --all
    ```

- [ ] **Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for multi-spec CLI coverage (admin, device, messaging)"
```

---

## Parallelization Guide

| Wave | Tasks | Notes |
|------|-------|-------|
| Wave 1 | Task 1 (parser fix) + Task 2 (overrides update) | Independent — parser fix is code, overrides is config |
| Wave 2 | Task 3 (admin) | Depends on Tasks 1+2. Must run before Tasks 4+5 (generates shared Workspace Locations/Events/Workspace Metrics) |
| Wave 3 | Task 4 (device) then Task 5 (messaging) | **Sequential, not parallel.** Both modify `main.py` — running in parallel causes merge conflicts. Command file generation is safe in parallel (different files), but the main.py registration step must be sequential. |
| Wave 4 | Task 6 (verify + docs) | Depends on Tasks 3-5 |

---

## Success Criteria

1. `wxcli --help` shows ~99 command groups (46 calling-generated + 5 hand-coded + ~35 admin + ~3 device-unique + ~10 messaging-unique — minus cross-spec overlaps registered once)
2. No duplicate command groups — each tag generates exactly one module, registered once
3. `wxcli <new-group> --help` works for every new group (no import errors)
4. `json-patch+json` endpoints in device spec parse correctly
5. `Licenses` (admin) generates as `licenses-api`, not colliding with hand-coded `licenses`
6. `Recordings` (admin) generates as `admin-recordings`, not colliding with `recordings` (calling)
7. All existing calling commands still work unchanged
