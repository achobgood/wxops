# New Spec: Webex Contact Center from Postman

## What This Session Does

Generate a new OpenAPI spec from the Cisco Webex Contact Center Postman collection,
then run the wxcli generator to produce CLI command groups. This is a NEW spec — there
is no existing `webex-contact-center.json` in `specs/`.

## Key IDs and Paths

- **Postman collection (Contact Center fork):** `15086833-a864a970-27a6-41ad-89d4-cf794012bbcc`
- **Postman collection UID:** `15086833-a864a970-27a6-41ad-89d4-cf794012bbcc`
- **New spec file:** `specs/webex-contact-center.json`
- **Generator config:** `tools/field_overrides.yaml`
- **Generator script:** `tools/generate_commands.py`
- **CLI entry point:** `src/wxcli/main.py`
- **Output dir:** `src/wxcli/commands/`

## Collection Structure (54 folders, ~450 requests)

### Configuration (26 folders)
| Folder | ID | Reqs |
|--------|----|------|
| Address Book | `15086833-1ced00d2-5566-443d-b71f-c6daa3090977` | 19 |
| Audio Files | `15086833-77faef52-cf92-41a2-bb8b-085acdd106e9` | 7 |
| Auxiliary Code | `15086833-bda4d42c-dc83-4db4-805a-da47543dab9a` | 11 |
| Business Hour | `15086833-9686e65c-ce2a-4e8c-b2e5-4e36d75cf137` | 9 |
| Contact Number | `15086833-09307614-3779-4cb1-b7c5-d6ef000ce94e` | 8 |
| Contact Service Queue | `15086833-2968ab55-9d8d-4174-b5ab-a857492e9ff5` | 23 |
| Desktop Layout | `15086833-11a6c0e8-3f63-4eeb-83a4-52a4cc2bcfa0` | 9 |
| Desktop Profile | `15086833-cf82842e-99e9-476b-a9fc-f37d3a33ad96` | 10 |
| Dial Number | `15086833-425518f5-00ce-42cf-b6ad-7b0d2138f73c` | 12 |
| Dial Plan | `15086833-84642182-7cfe-4b21-a37b-842de4a99eab` | 9 |
| Entry Point | `15086833-ca259212-2cd7-45fb-b94c-48bfb4a9ce4d` | 10 |
| Global Variables | `15086833-bd88aff4-efec-431e-9e62-437a08dba4e1` | 10 |
| Holiday List | `15086833-9a87c53a-a02f-485c-a2bb-30a6c850bf12` | 9 |
| Multimedia Profile | `15086833-bcb90eb2-d020-47e8-88bc-26de981447f2` | 10 |
| Outdial ANI | `15086833-02a03b98-5dda-474a-960f-212dbc5dc3bf` | 16 |
| Overrides | `15086833-cafe179a-fa57-4cc8-81a6-1c241023ebd2` | 9 |
| Site | `15086833-b766b901-af14-42e6-83d1-d4200f51c9a3` | 10 |
| Skill | `15086833-ebd1dfea-e546-4e80-b3ed-92d146b09700` | 10 |
| Skill Profile | `15086833-a1d950d8-f404-4814-876d-34a9fca0298d` | 9 |
| Team | `15086833-dafe7937-94f3-4810-b036-7e5d2634d661` | 10 |
| User Profiles | `15086833-bd338c16-b6d0-495f-a4b3-b2cd471b2c6c` | 17 |
| Users | `15086833-57c5435c-7f2e-48b1-b0ba-e7fe61deec51` | 14 |
| Work Types | `15086833-6ada7bba-e87d-4f7a-beb2-55618556be95` | 9 |
| DNC Management | `15086833-5b970791-c320-4036-9552-9a930da975da` | 3 |
| Resource Collection | `15086833-89b14268-c5b8-4693-98fb-4a39b2949d6e` | 8 |
| Contact List Management | `15086833-fcd742fd-7059-4439-9660-3df2860ad9d3` | 5 |

### Agent & Real-time (10 folders)
| Folder | ID | Reqs |
|--------|----|------|
| Agents | `15086833-8c06a511-9ed7-4c0a-8425-afe1a6fea660` | 11 |
| Agent Personal Greeting Files | `15086833-238c0ebf-3db5-480e-9cbe-2ebb633a3fdd` | 13 |
| Agent Wellbeing | `15086833-4b33d1d3-06f5-40b5-8cf6-5b013dd1e360` | 5 |
| Agent Summaries | `15086833-72f14ab6-50c0-481a-ae40-706d453137c8` | 2 |
| Call Monitoring | `15086833-27f74256-df0e-4a73-8051-96a5b9407899` | 7 |
| Tasks | `15086833-e53722a3-3678-4d3f-a596-cf4074421d00` | 24 |
| Subscriptions | `15086833-b51bf0a9-3575-4425-a2dd-0c3440d9b0d4` | 12 |
| Callbacks | `15086833-94ba8986-1e3f-4b26-8835-5eaea8e23bea` | 5 |
| Estimated Wait Time | `15086833-61117864-7ed5-4b4c-8514-974b815ead55` | 1 |
| Queues | `15086833-eaea57b1-849e-4ec8-973a-332ff9ca28f1` | 1 |

### AI & Analytics (5 folders)
| Folder | ID | Reqs |
|--------|----|------|
| AI Feature | `15086833-5e5153b5-c6c8-4743-9eb9-22ca20e50b56` | 3 |
| AI Assistant | `15086833-88c41484-53ba-471c-a73a-c1bcd384b1e1` | 1 |
| Auto CSAT | `15086833-28a85f4c-e2cc-40a0-ad87-ad7a43a6e0e7` | 8 |
| Generated Summaries | `15086833-67d49a63-aaed-499b-88f6-8a600785a7b2` | 3 |
| Realtime | `15086833-c62c3048-d4af-4dda-9357-3aed9229a5be` | 1 |

### Journey (7 folders)
| Folder | ID | Reqs |
|--------|----|------|
| Journey | `15086833-eecf9504-4182-44f1-9ce5-b7f6f52b977a` | 39 |
| Journey - Customer Identification API | `15086833-cfe58485-182b-4939-b8ce-f71750b6c7c9` | 9 |
| Journey - Data Ingestion API | `15086833-ea41c637-0ab8-45a2-9f39-f3a645a4c056` | 1 |
| Journey - Profile Creation & Insights API | `15086833-13acd73f-9ea3-4f6c-9f03-70ec32644344` | 14 |
| Journey - Subscription API | `15086833-8469d9b4-e0e6-48d0-8d0b-a482999a6e39` | 3 |
| Journey - Trigger Actions API | `15086833-7ba7d454-2735-470a-968b-3f24a8a6a4b1` | 7 |
| Journey - Workspace management API | `15086833-0e671a96-3657-4d95-a140-871ee54ec455` | 5 |

### Other (6 folders)
| Folder | ID | Reqs |
|--------|----|------|
| Campaign Manager | `15086833-28cfbf9f-2154-434c-a73f-715b0cb7261c` | 3 |
| Captures | `15086833-8c2906c5-8d61-42d5-b349-87082818b183` | 1 |
| Data Sources | `15086833-4b0c3dbc-2445-4831-b483-8b51654f5b8a` | 7 |
| Flow | `15086833-ff14f3ce-9631-4530-9f5d-9ca000057916` | 4 |
| Notification | `15086833-35d41d1d-35ac-48e8-b64d-812771dc092e` | 1 |
| Search | `15086833-97e24f41-1865-4ede-860d-2e825e8a4da2` | 1 |

## Guardrails

- **Never hand-edit generated command files.** Fix via `field_overrides.yaml` + regenerate.
- **Never `git add -A` or `git add .`.** Stage specific files only.
- **Do NOT download the full collection** — it's large. Use `getCollectionFolder` with
  `populate: true` and the folder IDs above to pull one folder at a time.
- **Review gate before every major step.** Present findings, wait for approval.
- **Cross-spec overlap:** The Contact Center collection has a "Data Sources" folder that
  overlaps with the Admin spec. Add it to `skip_tags` if the endpoints are identical.

## Step-by-Step Procedure

### Step 1: Verify Prerequisites

1. Call `getAuthenticatedUser` via Postman MCP to confirm connection.
2. Verify `specs/` directory exists and confirm there is NO existing `webex-contact-center.json`.
3. Read `tools/field_overrides.yaml` to understand existing patterns.
4. Read `src/wxcli/main.py` to understand how specs are registered.

### Step 2: Generate OpenAPI Spec from Postman Collection

Use the Postman MCP `generateSpecFromCollection` tool:
- `collectionUid`: `"15086833-a864a970-27a6-41ad-89d4-cf794012bbcc"`
- `elementType`: `"spec"`
- `name`: `"Webex Contact Center"`
- `type`: `"OPENAPI:3.0"`
- `format`: `"JSON"`

This is an async operation — it returns a task ID. Poll `getAsyncSpecTaskStatus` until complete,
then use `getSpecDefinition` to download the generated spec.

### Step 3: Review the Generated Spec

1. Download the generated spec JSON.
2. Analyze its structure:
   - How many paths/operations?
   - What tags does it use? Do they match the Postman folder names?
   - Are there any empty or malformed operations?
3. Present a summary to the user:
   | Tag | Operations | Methods |
4. Identify any cross-spec overlaps with existing specs (Data Sources, People, etc.)

**Wait for user approval before proceeding.**

### Step 4: Save and Validate the Spec

1. Save the spec to `specs/webex-contact-center.json`.
2. Validate it parses correctly:
   ```bash
   python3.11 -c "import json; d=json.load(open('specs/webex-contact-center.json')); print(f'Paths: {len(d.get(\"paths\",{}))}, Tags: {len(set(t for p in d[\"paths\"].values() for m in p.values() if isinstance(m,dict) for t in m.get(\"tags\",[])))}')"
   ```

### Step 5: Supplement with Postman Folder Data

The auto-generated spec may be incomplete (missing response schemas, descriptions, etc.).
For the most important folders, pull the Postman folder to verify/supplement:

Use `getCollectionFolder` with `populate: true` for a few key folders:
- Contact Service Queue (23 requests — biggest folder)
- Address Book (19 requests)
- Agents (11 requests)

Compare these against the generated spec — add any missing parameters, response schemas,
or descriptions.

### Step 6: Configure field_overrides.yaml

1. Add `skip_tags` entries for cross-spec overlaps (e.g., "Data Sources" if identical to Admin).
2. Add `cli_name_overrides` for human-friendly group names. Proposed:
   ```yaml
   cli_name_overrides:
     "Contact Service Queue": "cc-queue"
     "Auxiliary Code": "cc-aux-code"
     "Desktop Layout": "cc-desktop-layout"
     "Desktop Profile": "cc-desktop-profile"
     "Multimedia Profile": "cc-multimedia-profile"
     "Skill Profile": "cc-skill-profile"
     "User Profiles": "cc-user-profiles"
     "Outdial ANI": "cc-outdial-ani"
     # ... prefix with cc- to distinguish from Calling groups
   ```
3. Add `table_columns` for the most common list commands. Derive field names from Postman
   response examples (use `getCollectionFolder` with `populate: true` to get examples).
4. Consider `tag_merge` for the Journey folders — merge all 7 into a single `cc-journey` group.

### Step 7: Register the Spec in the Generator

The generator needs to know about the new spec. Check how existing specs are registered:
- `src/wxcli/main.py` — how groups are loaded
- `tools/generate_commands.py` — how `--spec` flag works

The generator already accepts `--spec` as a flag, so no code changes needed for generation.
But `main.py` may need to import the new command groups. Check how existing groups are
auto-discovered (likely via `commands/` directory scanning).

### Step 8: Generate CLI Commands

```bash
PYTHONPATH=. python3.11 tools/generate_commands.py --spec specs/webex-contact-center.json --all
pip3.11 install -e . -q
```

### Step 9: Verify

1. Run `wxcli --help` — confirm new groups appear (cc-queue, cc-agents, etc.).
2. For each new group, run `wxcli <group> --help` — confirm subcommands.
3. Count total new groups — should roughly match the number of non-skipped tags.
4. Spot-check 3-4 commands with `wxcli <group> <cmd> --help` — confirm parameters.

### Step 10: Update Documentation

1. Add the new spec to the file map table in `CLAUDE.md`:
   ```
   | `specs/webex-contact-center.json` | OpenAPI 3.0 spec — contact center APIs |
   ```
2. Update the command group count in `CLAUDE.md`.
3. Add the Contact Center collection to the Postman fork IDs section (already there).

### Step 11: Commit

Stage and commit specific files only:
- `specs/webex-contact-center.json`
- `tools/field_overrides.yaml`
- `src/wxcli/commands/cc_*.py` (all generated Contact Center command files)
- `CLAUDE.md` (updated file map and group count)

Commit message: `feat(contact-center): generate CLI from Postman Contact Center collection (~450 endpoints)`

## Success Criteria

- `specs/webex-contact-center.json` exists and parses correctly
- CLI groups for Contact Center appear in `wxcli --help`
- Each group's `--help` shows correct subcommands
- No cross-spec overlap (duplicate command groups)
- CLAUDE.md updated with new spec and group count

## Post-Generation Fixups (Lessons from 2026-03-28)

Postman's `generateSpecFromCollection` has known limitations. After generating any new
spec from a Postman collection, check for these issues:

1. **Base URL missing.** Postman environment variables (like `{{baseUrl}}`) are NOT preserved
   in the generated spec. The `servers` field will be `[{url: "/"}]`. Fix by setting the
   correct server URLs in the spec JSON. For CC: `api.wxcc-{region}.cisco.com`.

2. **Path parameters not declared.** Variables like `{orgid}` may appear in URL paths but
   lack formal parameter definitions. The generator sees them in the f-string but creates no
   CLI option → `NameError` at runtime. Fix by adding path parameter objects to each
   operation in the spec, then use `auto_inject_from_config` in `field_overrides.yaml` if
   the param should be auto-injected (like `orgid`).

3. **Literal path segments misinterpreted as variables.** Paths like `/flows/import` may
   become `/flows{import}` in the spec. This causes Python keyword conflicts in f-strings.
   Fix by replacing `{import}` → `/import` (etc.) in the spec paths.

4. **Tag name collisions.** If the new spec has tags that match existing specs (e.g., "Site",
   "Data Sources"), rename them in the spec before generating to avoid file/CLI name collisions.
   Use a prefix like "CC Site", then map via `cli_name_overrides`.
