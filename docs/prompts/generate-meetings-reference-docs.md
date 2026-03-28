# Generate Reference Docs: Webex Meetings

## What This Session Does

Write 4 reference docs for the Webex Meetings API surface (17 CLI groups, 139 commands).
The OpenAPI spec and CLI commands already exist — this session writes the docs that ground
them in API details, data models, raw HTTP examples, and gotchas.

## Context (Zero-Context Briefing)

This project is a Webex Calling CLI (`wxcli`) with guided agent assistance. The CLI has
165 command groups generated from 7 OpenAPI specs. Every API surface has **reference docs**
(`docs/reference/*.md`) — deep technical references documenting CLI commands, raw HTTP
endpoints, data models, and gotchas. Meetings was just added but has NO reference docs yet.

**IMPORTANT:** The Meetings API is NOT in wxc_sdk or wxcadm. Do NOT include SDK method
signatures. Reference docs should document **wxcli CLI commands** (primary) and **Raw HTTP
endpoints** (from the OpenAPI spec) only.

## Key Files

### Patterns (READ THESE FIRST)

| What | Path | Why |
|------|------|-----|
| Reference doc pattern (features) | `docs/reference/call-features-major.md` | Best example (~1300 lines): Sources, TOC, API sections, data models, CLI examples, Raw HTTP, Gotchas, See Also |
| Reference doc pattern (simpler) | `docs/reference/messaging-spaces.md` | Simpler example (~700 lines) |
| Project instructions | `CLAUDE.md` | Full file map, CLI status, known issues |

### Source Material

| What | Path | Contents |
|------|------|----------|
| Meetings spec | `specs/webex-meetings.json` | 112 paths, 19 tags (17 generated, 2 skipped) |
| CLI commands | `src/wxcli/commands/meetings.py` + `meeting_*.py` + `video_mesh.py` | 17 generated command files |
| Sync report | `docs/reports/postman-meetings-sync-2026-03-28.md` | Tag mapping and counts |

### CLI Groups

| CLI Group | Tag | Ops | Domain |
|-----------|-----|-----|--------|
| `meetings` | Meetings | 46 | Core CRUD, templates, controls, registrants, interpreters, breakouts, surveys |
| `meeting-participants` | Participants | 7 | Participant list, details, admit, SIP callout |
| `meeting-invitees` | Invitees | 6 | Invitee CRUD, batch operations |
| `meeting-transcripts` | Transcripts | 7 | Transcript list, download, snippets, CRUD |
| `meeting-preferences` | Preferences | 14 | Personal room, audio/video/scheduling, delegates, sites |
| `meeting-tracking-codes` | Tracking Codes | 7 | Tracking code CRUD, user codes |
| `video-mesh` | Video Mesh | 30 | Clusters, nodes, availability, utilization, reachability, health monitoring |
| `meeting-captions` | Closed Captions | 3 | Caption list, snippets, download |
| `meeting-polls` | Meeting Polls | 3 | Poll list, results, respondents |
| `meeting-summaries` | Summaries | 3 | AI summary get/delete, compliance |
| `meeting-session-types` | Session Types | 3 | Site/user session types |
| `meeting-chats` | Chats | 2 | In-meeting chat list, delete |
| `meeting-qa` | Meeting Q and A | 2 | Q&A list, answer list |
| `meeting-reports` | Meetings Summary Report | 2 | Usage reports, attendee reports |
| `meeting-site` | Site | 2 | Site-wide meeting settings |
| `meeting-slido` | Slido Secure Premium | 1 | Compliance events |
| `meeting-messages` | Meeting Messages | 1 | Delete meeting message |

## Guardrails

- **Read the pattern files first.** Do not write any docs until you've read at least one
  reference doc to understand the structure.
- **Extract endpoint details from the spec and CLI.** Use `wxcli <group> --help` and
  `wxcli <group> <command> --help` to verify command signatures. Use a python one-liner
  to extract paths/methods/summaries from the spec per tag.
- **Break large writes into sections.** Reference docs are 500-1000 lines. Write in
  sections to avoid 502 errors.
- **Never hand-edit generated command files.** The reference docs describe the APIs.
- **Stage specific files only.** Never `git add -A` or `git add .`.
- **Self-review after each doc.** Read what you wrote and verify it matches the pattern
  and the actual CLI commands.
- **Build an explicit checklist before writing each doc.** List every section you intend
  to include, then verify after writing.

## Step-by-Step Procedure

### Step 1: Read Patterns

1. Read `CLAUDE.md` — understand the project structure, file map, known issues.
2. Read `docs/reference/call-features-major.md` — the reference doc pattern. Note the
   structure: Sources, TOC, API sections (with wxcli CLI examples and Raw HTTP), Gotchas,
   See Also.
3. Skim `docs/reports/postman-meetings-sync-2026-03-28.md` — understand the tag mapping.

### Step 2: Extract Endpoint Details

For each of the 4 docs, extract the relevant endpoints from the spec:

```bash
# Example: extract all Meetings-tagged endpoints
python3.11 -c "
import json
with open('specs/webex-meetings.json') as f:
    spec = json.load(f)
for path, methods in sorted(spec['paths'].items()):
    for method, op in methods.items():
        if isinstance(op, dict) and 'TAG_NAME' in op.get('tags', []):
            params = [p.get('name') for p in op.get('parameters', [])]
            print(f'{method.upper():7s} {path:60s} {op.get(\"summary\", \"\")[:50]:50s} params={params}')
"
```

Also run `wxcli <group> --help` for each group to verify subcommand names.

### Step 3: Write the 4 Reference Docs

**Present the section outlines for all 4 docs to the user before writing. Wait for approval.**

#### 3a. `docs/reference/meetings-core.md` (~800-1000 lines)

Covers the `meetings` CLI group (46 commands). Sections:

1. Sources (spec file, developer.webex.com Meetings APIs)
2. Meeting CRUD (list, create, get, update, patch, delete, join, end, reassign host)
3. Meeting Templates (list, get)
4. Meeting Controls (get status, update status)
5. Session Types (list site types, list user types, get type)
6. Registration (get form, update form, delete form)
7. Registrants (list, create, batch create, get, delete, query, batch update/approve/reject/cancel/delete)
8. Interpreters (list, create, get, update, delete, update simultaneous interpretation)
9. Breakout Sessions (list, update, delete)
10. Surveys (get survey, list results, get links)
11. Invitation Sources (list, create)
12. Tracking Codes (list meeting tracking codes)
13. Raw HTTP Endpoints (table of all 46 endpoints)
14. Gotchas
15. See Also

#### 3b. `docs/reference/meetings-content.md` (~600-800 lines)

Covers content and media groups. Sections:

1. Sources
2. Transcripts (`meeting-transcripts`, 7 commands)
3. Recordings — cross-reference only (already in admin spec as `admin-recordings`)
4. Closed Captions (`meeting-captions`, 3 commands)
5. Chats (`meeting-chats`, 2 commands)
6. Meeting Messages (`meeting-messages`, 1 command)
7. Summaries (`meeting-summaries`, 3 commands)
8. Raw HTTP Endpoints
9. Gotchas
10. See Also

#### 3c. `docs/reference/meetings-settings.md` (~500-700 lines)

Covers settings, preferences, analytics. Sections:

1. Sources
2. Preferences (`meeting-preferences`, 14 commands)
3. Session Types (`meeting-session-types`, 3 commands)
4. Tracking Codes (`meeting-tracking-codes`, 7 commands)
5. Site Settings (`meeting-site`, 2 commands)
6. Meeting Polls (`meeting-polls`, 3 commands)
7. Meeting Q&A (`meeting-qa`, 2 commands)
8. Meeting Reports (`meeting-reports`, 2 commands)
9. Slido (`meeting-slido`, 1 command)
10. Raw HTTP Endpoints
11. Gotchas
12. See Also

#### 3d. `docs/reference/meetings-infrastructure.md` (~600-800 lines)

Covers Video Mesh and Participants. Sections:

1. Sources
2. Video Mesh (`video-mesh`, 30 commands) — subsections for clusters, availability,
   health, utilization, reachability, network tests, client distribution, on-demand tests,
   thresholds, overflow, redirects
3. Participants (`meeting-participants`, 7 commands)
4. Invitees (`meeting-invitees`, 6 commands)
5. Raw HTTP Endpoints
6. Gotchas
7. See Also

### Step 4: Update CLAUDE.md

Add the 4 new reference docs to the file map table in `CLAUDE.md` under the existing
Reference Docs section:

```
| `docs/reference/meetings-core.md` | Meeting CRUD, templates, controls, registrants, interpreters, breakouts, surveys |
| `docs/reference/meetings-content.md` | Transcripts, captions, chats, summaries, meeting messages |
| `docs/reference/meetings-settings.md` | Preferences, session types, tracking codes, site settings, polls, Q&A, reports |
| `docs/reference/meetings-infrastructure.md` | Video Mesh (clusters, nodes, health, utilization), participants, invitees |
```

### Step 5: Commit

Stage specific files:
```
docs/reference/meetings-core.md
docs/reference/meetings-content.md
docs/reference/meetings-settings.md
docs/reference/meetings-infrastructure.md
CLAUDE.md
```

Commit message: `docs(meetings): reference docs for Meetings API (4 docs, 17 CLI groups)`

## Success Criteria

- [ ] 4 reference docs exist and follow the pattern (Sources, API sections, CLI examples, Raw HTTP, Gotchas, See Also)
- [ ] All 17 meetings CLI groups are documented in at least one reference doc
- [ ] No wxc_sdk or wxcadm method signatures (these APIs aren't in those SDKs)
- [ ] All wxcli command examples use actual CLI group and command names (verified via --help)
- [ ] Raw HTTP endpoint tables include method, path, and description for every endpoint
- [ ] CLAUDE.md file map updated
- [ ] Committed with specific file staging
