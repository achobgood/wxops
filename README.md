# wxcli — Webex Calling CLI

A command-line tool and AI-assisted playbook for provisioning, managing, migrating, and auditing Webex Calling environments. 178 command groups covering the full Webex Calling, admin, device, messaging, meetings, and contact center API surface.

> **Unofficial community CLI — not affiliated with or endorsed by Cisco.**

## What It Does

- **178 CLI command groups** — provision locations, users, call features, devices, routing, PSTN, messaging, meetings, and contact center resources from the terminal
- **AI-guided playbook** — a Claude Code agent that interviews you about what to build, generates a deployment plan, executes commands, and verifies results
- **CUCM-to-Webex migration** — 11-phase pipeline: discover a CUCM cluster via AXL, normalize, map, analyze, generate decisions, plan, and execute the migration with an async concurrent engine
- **Org health assessment** — 18 automated checks across security posture, routing hygiene, feature utilization, and device health with a self-contained HTML report
- **Partner / multi-org support** — manage multiple customer orgs with a single partner token; 1150 commands auto-inject the target `orgId`
- **Batch cleanup** — dependency-safe teardown of an entire Webex Calling environment (or scoped to specific locations) with `--dry-run` support

## How It Works

Most "AI + API" tools hand a language model an OpenAPI spec and hope. That breaks at scale: across hundreds of endpoints a model malforms request bodies, hallucinates field names and license tiers, and — worst — doesn't know a hunt group needs a calling-enabled location *first*. Specs describe endpoints; they don't describe outcomes.

wxops splits the problem into three layers, each killing one way an LLM fails:

| Layer | What it is | Failure it prevents |
|-------|-----------|---------------------|
| **Reference docs** (43 active) | De-conflated, authoritative API knowledge — data models, enums, license-tier distinctions, gotchas | **Hallucination** — the agent grounds on docs, never on training data |
| **Skills** (24) | Encoded procedures for outcomes — prerequisites, ordering, intent disambiguation, known landmines | **Wrong sequence / wrong tool** — the agent follows a checklist, not a guess |
| **CLI** (178 groups) | Tested, self-describing commands generated from 9 OpenAPI specs | **Malformed execution** — the model emits a command string, not hand-rolled HTTP |

The model only does what it's reliably good at — reasoning and orchestration. Facts come from the docs, procedure from the skills, execution from the tested CLI.

**One request, traced** — *"Add a sales hunt group for the Denver office":*

1. The agent routes to the `configure-features` skill — not contact-center, not customer-assist (the disambiguation map handles the overloaded word "queue").
2. The skill loads `docs/reference/call-features-major.md` for ground truth, then checks prerequisites in order: location exists → calling-enabled → users exist → numbers available.
3. Before building the command it runs `wxcli hunt-group create --help` — the CLI is the final source of truth for flags, never the docs or memory.
4. The CLI executes; a verify step reads the result back to confirm.

At every step the agent is forced back to an authoritative source: data model from the doc, flags from `--help`, final state from a read-back. It never operates on memory. That layered grounding *is* the design.

### Why a CLI, not an MCP server?

The natural question for an agent-driven tool: why not expose the API as MCP tools? Because at this surface area — 178 command groups and several hundred individual operations — one tool per endpoint breaks down:

- **MCP tool schemas load eagerly, every turn.** Hundreds of operations means hundreds of JSON tool definitions sitting in the model's context *before it reads your request* — tens of thousands of tokens of overhead on every call. A CLI loads nothing up front; the model pulls a single command's schema on demand with `wxcli <group> <command> --help`. Just-in-time, not all-at-once.
- **Tool-selection accuracy collapses well before hundreds.** Models reliably pick from a handful of tools, not a sea of near-duplicates — and this surface is full of overloaded names ("queue" means three different things across Calling, Contact Center, and Customer Assist). The skill layer disambiguates intent; a flat tool list just hands the model the ambiguity.
- **CLI commands compose; MCP tool calls don't.** Pipe to `jq`, filter with `grep`, chain a list of IDs into the next command. Ops work is full of "get these, feed them to that" — the shell makes it trivial.
- **The CLI runs without an LLM at all.** The same commands work in scripts, in CI, and by hand, backed by thousands of tests. An MCP tool only exists inside an MCP client.

This isn't anti-MCP. MCP is the right *thin boundary* for host integration: to let an agent platform drive wxops, you wrap the CLI behind **one** small MCP surface — a single "run a wxcli command" tool — not several hundred. The CLI stays the execution layer; MCP is just the seam. You get the integration without paying the tool-explosion tax.

## Install

```bash
pipx install wxcli      # recommended — isolated, always on PATH
# or:
pip install wxcli
```

Works on macOS, Linux, and Windows. On Windows, first install [Python 3.11+](https://www.python.org/downloads/) (tick **"Add python.exe to PATH"** during setup); then `python -m pip install --user pipx && python -m pipx ensurepath` gives you `pipx`. `pipx`/`pip` pull every dependency automatically.

### From source (for development or the Claude Code playbook)

The Claude Code playbook (agents, skills, reference docs) lives in the repo, not the wheel. Clone if you want the playbook or plan to develop wxcli:

```bash
git clone https://github.com/achobgood/wxops.git
cd wxops
pip install -e .
```

On Windows this also needs [Git](https://git-scm.com/download/win). The version is derived from git tags at install time, so a full clone (not a shallow/zip download) is required.

## Authenticate

Get a personal access token from [developer.webex.com](https://developer.webex.com) (valid for 12 hours).

**Option 1 — persistent (recommended).** Run `wxcli configure` and paste the token at the prompt. Identical in macOS/Linux Terminal, Windows PowerShell, and cmd:

```
wxcli configure
# prompts: "Webex API token:"  → paste token, press Enter
```

**Option 2 — environment variable (per session).** Use the form for your shell:

```bash
# macOS / Linux
export WEBEX_ACCESS_TOKEN="YOUR_TOKEN"
```

```powershell
# Windows PowerShell
$env:WEBEX_ACCESS_TOKEN="YOUR_TOKEN"
```

```bat
:: Windows cmd
set WEBEX_ACCESS_TOKEN=YOUR_TOKEN
```

Verify auth (any shell):

```
wxcli whoami
```

## Updating

```bash
wxcli update           # check PyPI and upgrade in place
wxcli update --check   # report the latest version without upgrading
```

`wxcli update` detects how it was installed and upgrades accordingly — `pipx upgrade wxcli` for pipx installs, `pip install --upgrade wxcli` for pip installs — then deep-links the release notes for the new version. No git required.

**If you originally cloned the repo** (a source/dev install), `wxcli update` prints guidance instead of upgrading. To move to a managed install, run:

```bash
wxcli update --migrate   # installs via pipx, removes the old editable install
```

Developers who want to keep hacking on the source stay on `git pull`. Behind a firewall that blocks PyPI? Point `WXCLI_UPDATE_INDEX_URL` at an internal mirror, or install fresh with `pipx install wxcli` and abandon the clone.

## Claude Code Playbook

This repo includes an AI playbook for [Claude Code](https://claude.com/claude-code) that turns your terminal into a guided Webex Calling configuration assistant.

### What is the Playbook?

A guided AI assistant that walks you through Webex Calling configuration end-to-end. It interviews you about what you want to build, generates a deployment plan, executes `wxcli` commands on your behalf, and verifies the results. Think of it as a Webex Calling expert sitting next to you in the terminal.

### What's Included

- **1 builder agent** (`/agents` → wxc-calling-builder) — the main entry point that drives the full workflow
- **24 domain skills** covering: provisioning & teardown, call features, Customer Assist, routing, devices, device platform, call settings, call control, reporting (calling, meetings, contact center), identity/SCIM, licensing, audit/compliance, messaging spaces, messaging bots, meetings, video mesh, contact center, CUCM migration, org health, live query, and debugging
- **43 reference docs** in `docs/reference/` (+8 archived historical SDK docs) documenting every Webex Calling API surface with SDK method signatures, raw HTTP examples, and gotchas
- **Shared permissions** (`.claude/settings.json`) that pre-approve `wxcli` commands so Claude Code doesn't prompt you for every CLI execution

### How to Use It

1. Install [Claude Code](https://claude.com/claude-code)
2. Clone this repo and `cd` into it — the clone delivers the **playbook** (agents/skills/docs)
3. Install the CLI: `pip install -e .` (or use a PyPI-installed `wxcli` — the playbook drives whichever `wxcli` is on your PATH)
4. Run `claude` to start Claude Code
5. Use `/agents` and select **wxc-calling-builder** to begin
6. Or use `/wxc-calling-debug` to troubleshoot a specific issue

The repo includes a `.claude/settings.json` that pre-approves common commands (`wxcli`, `pip install`, `which`). This means the playbook agent can run `wxcli` commands without prompting you for permission each time. You can review or customize these permissions in `.claude/settings.json`. Any personal overrides go in `.claude/settings.local.json` (gitignored).

### Without Claude Code

The AI playbook is optional — everything else works standalone:

- **wxcli** is a regular Python CLI tool. Install it and use it directly.
- The **43 reference docs** in `docs/reference/` are a comprehensive API knowledge base, useful for any developer working with Webex APIs.
- The **9 OpenAPI specs** (`specs/webex-*.json`) can be imported into Postman or any API client.

## CLI Reference

```bash
# See all 178 command groups
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
wxcli users list --location-id LOC_ID      # Get person IDs
wxcli numbers list --location-id LOC_ID  # Get number inventory
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
| `cleanup` | Batch-delete resources in dependency-safe order |

This table shows the most commonly used groups. Run `wxcli --help` to see all 178 groups, which also cover admin, device, messaging, meetings, and contact center APIs.

---

## CUCM-to-Webex Migration Tool

A full migration pipeline at `src/wxcli/migration/` that analyzes a CUCM environment, maps objects to Webex Calling equivalents, and executes the migration. 2535 tests passing.

### Pipeline

```bash
wxcli cucm init -p myproject              # Create project
wxcli cucm discover --host 10.0.0.1 \    # Extract from CUCM via AXL
  --username admin --password secret -p myproject
wxcli cucm normalize -p myproject         # Normalize to canonical models
wxcli cucm map -p myproject               # Map CUCM objects to Webex operations
wxcli cucm analyze -p myproject           # Run 14 analyzers, generate decisions
wxcli cucm report --brand "Acme Corp" \   # Generate HTML assessment report
  --prepared-by "Jane Admin" -p myproject
```

The assessment report provides a complexity score, environment inventory, analog gateway review, and effort estimates — suitable for customer-facing delivery.

### Additional Pipeline Outputs

```bash
wxcli cucm user-diff -p myproject         # Per-user before/after comparison
wxcli cucm user-notice --brand "Acme" \   # Email-ready migration notice
  --migration-date "2026-06-01" \
  --helpdesk "help@acme.com" -p myproject
```

### Execution

After analysis and decision review:

```bash
wxcli cucm plan -p myproject              # Build dependency-ordered execution plan
wxcli cucm preflight -p myproject         # Run 8 preflight checks
wxcli cucm export -p myproject            # Export deployment plan
wxcli cucm execute -p myproject \         # Execute all operations concurrently
  --concurrency 15
```

The execution engine handles 409 auto-recovery (existing resources), cascade-skip (failed dependencies), and concurrent batch execution. A 561-operation stress test completes in ~90 seconds.

### Migration Architecture

- **SQLite-backed store** with objects, cross-references, decisions, and journal
- **42 normalizers** (Pass 1) + CrossReferenceBuilder (34 relationships)
- **26 mappers** that convert CUCM objects to Webex Calling operations
- **14 analyzers** that surface decisions requiring human review
- **Advisory system** with 19 per-decision rules + 30 cross-cutting patterns
- **NetworkX DAG** for dependency ordering and batch planning
- **Async execution engine** with configurable concurrency

---

## Org Health Assessment

An automated audit of a live Webex Calling org. Runs 18 deterministic checks across 4 categories and produces a self-contained HTML report.

### Categories and Checks

| Category | Checks |
|----------|--------|
| **Security Posture** | Unrestricted international dialing, no outgoing call restrictions, auto attendant external transfer enabled, call queues without recording |
| **Routing Hygiene** | Empty dial plans, orphan route components (route groups/lists without trunks), trunk errors |
| **Feature Utilization** | Disabled auto attendants, understaffed call queues, single-member hunt groups, empty voicemail groups, empty paging groups, empty call parks |
| **Device Health** | Offline devices, users at device limit, unassigned devices, workspaces without devices, stale activation codes |

### How to Run

Via the Claude Code playbook:

```
/agents → wxc-calling-builder → "audit my org"
```

The builder agent orchestrates three phases: collect data via `wxcli`, analyze with the check engine, and generate the HTML report.

---

## Partner / Multi-Org Support

For partners, VARs, and MSPs managing multiple customer organizations with a single token.

```bash
wxcli configure                   # Auto-detects multi-org token, prompts for org selection
wxcli switch-org                  # Change the active target org
wxcli clear-org                   # Revert to single-org behavior
wxcli whoami                      # Shows "Target:" line when an org is set
```

1149 of the generated commands auto-inject the selected `orgId` on endpoints that accept it — no extra flag required.

---

## Cleanup

Batch-delete Webex Calling resources in dependency-safe order (13 layers, reverse of creation order).

```bash
wxcli cleanup run --scope "San Jose,Austin"  # Specific locations only
wxcli cleanup run --all                       # Entire org
wxcli cleanup run --all --dry-run             # Preview without deleting
```

**Flags:**
- `--include-users` — also delete users (off by default)
- `--include-locations` — also delete locations (off by default)
- `--exclude-user-domains "wbx.ai,corp.com"` — protect users matching these email domains
- `--max-concurrent N` — parallel deletions per layer (default 5)
- `--force` — skip confirmation prompt

**Deletion order:** dial plans → route lists → route groups → translation patterns → trunks → call features → schedules/operating modes → virtual lines → devices → workspaces → users → numbers → locations.

---

## Project Architecture

```
wxops/
├── src/wxcli/                    # CLI source (Typer + httpx REST client)
│   ├── main.py                   # Entry point — registers 178 command groups
│   ├── auth.py                   # Token storage and API client init
│   ├── output.py                 # Table/JSON output formatting
│   ├── commands/                 # generated command modules (one per API tag) + _registry.py manifest
│   ├── org_health/               # Org health assessment engine (18 checks → HTML report)
│   └── migration/                # CUCM-to-Webex migration engine
│       ├── cucm/                 # AXL extractors and discovery
│       ├── transform/            # Normalizers, mappers, analyzers
│       ├── execute/              # Async execution engine + handlers
│       ├── advisory/             # Decision recommendations
│       ├── report/               # HTML/PDF assessment report generator
│       └── models.py             # 38 canonical data models
├── tools/                        # Code generator pipeline
│   ├── generate_commands.py      # Orchestrator: OpenAPI → Click commands
│   ├── openapi_parser.py         # Parses OpenAPI 3.0 specs into Endpoint objects
│   ├── command_renderer.py       # Renders Endpoints into Python command files
│   └── field_overrides.yaml      # Table columns, display config, bug fixes
├── tests/                        # 2535 tests (pytest)
├── specs/                        # 9 OpenAPI 3.0 specs (calling, admin, device, messaging, meetings, CC, UCM, BroadWorks, wholesale)
├── docs/reference/               # 43 API reference docs (SDK + raw HTTP + gotchas)
├── .claude/settings.json         # Shared permissions (pre-approves wxcli commands)
├── .claude/agents/               # Claude Code builder + migration advisor agents
└── .claude/skills/               # 25 Claude Code skills
```

**Key design decisions:**

- **Commands are generated, never hand-edited.** Fix bugs in `field_overrides.yaml` and regenerate with `tools/generate_commands.py`.
- **The CLI uses raw HTTP** via its own `WebexSession` client (`src/wxcli/auth.py`) built on `httpx`, not any third-party SDK. This gives 100% API coverage without external dependencies.
- **Reference docs serve both humans and AI.** Developers can read them directly; the playbook loads them as context for guided configuration.

## Known Limitations

- **Call control commands require a user-level OAuth token.** Admin and service app tokens return `400 "Target user not authorized"`. Use a personal access token from the user who will control calls.
- **Complex nested settings need `--json-body`.** Call forwarding rules, agent lists, voicemail config, and similar deeply nested structures can't be expressed as CLI flags — pass the full JSON body instead.
- **6 person call settings are user-only.** `simultaneousRing`, `sequentialRing`, `priorityAlert`, `callNotify`, `anonymousCallReject`, and `callPolicies` only work with user-level tokens, not admin tokens.
- **CDR/analytics endpoints require the `analytics:read_all` scope**, which standard admin tokens may not include.

## Requirements

- Python 3.11+ (includes `pip`)
- Git — required to clone the repo *and* to build it (the version is derived from git tags at install time)
- A Webex admin account with access tokens

### OAuth Scopes

The CLI covers 178 command groups across calling, admin, device, messaging, meetings, and contact center APIs. Not all scopes are needed — request only those for the API domains you use.

**Minimum scopes for Webex Calling admin operations:**

| Scope | Purpose |
|-------|---------|
| `spark-admin:telephony_config_read` | Read telephony config (locations, numbers, call routing, features) |
| `spark-admin:telephony_config_write` | Create/edit/delete telephony config |
| `spark-admin:people_read` | Read people across the organization |
| `spark-admin:people_write` | Create/update/delete people |
| `spark-admin:locations_read` | List and view locations |
| `spark-admin:locations_write` | Create/update/delete locations |
| `spark-admin:licenses_read` | List and inspect licenses |
| `spark-admin:devices_read` | View devices |
| `spark-admin:devices_write` | Add/update/delete devices |
| `spark-admin:workspaces_read` | View workspaces and workspace settings |
| `spark-admin:workspaces_write` | Create/update/delete workspaces |

**Additional scopes by API domain:**

| Domain | Scopes |
|--------|--------|
| PSTN / routing | `spark-admin:telephony_pstn_read`, `spark-admin:telephony_pstn_write` |
| Workspace locations | `spark-admin:workspace_locations_read`, `spark-admin:workspace_locations_write` |
| Org-wide call control | `spark-admin:calls_read`, `spark-admin:calls_write` |
| CDR / call history | `spark-admin:calling_cdr_read` (+ admin role "Webex Calling Detailed Call History API access") |
| Reports / analytics | `analytics:read_all` (requires Pro Pack) |
| Org & roles | `spark-admin:organizations_read` |
| Audit events | `spark-admin:audit_events_read` |
| SCIM identity sync | `identity:people_rw`, `identity:people_read` |
| Hybrid services | `spark-admin:hybrid_clusters_read`, `spark-admin:hybrid_connectors_read` |
| Recordings | `spark-admin:recordings_read`, `spark-admin:recordings_write` |
| Data sources | `spark-admin:datasource_read`, `spark-admin:datasource_write` |
| Resource groups | `spark-admin:resource_groups_read`, `spark-admin:resource_group_memberships_write` |
| Partner reports | `spark-admin:reports_read`, `spark-admin:reports_write` |
| Messaging (rooms) | `spark:rooms_read`, `spark:rooms_write` |
| Messaging (memberships) | `spark:memberships_read`, `spark:memberships_write` |
| RoomOS xAPI | `spark:xapi_commands`, `spark:xapi_statuses` |
| Device activation | `identity:placeonetimepassword_create` or `Identity:one_time_password` |
| Contact center | `cjp:config_read`, `cjp:config_write` (also requires `wxcli set-cc-region`) |

**User-level scopes** (for call control and self-service settings — requires a user token, not admin):

| Scope | Purpose |
|-------|---------|
| `spark:calls_read` | List active calls and call history |
| `spark:calls_write` | Call control (answer, hold, transfer, park) |
| `spark:people_read` | Read own user info |
| `spark:people_write` | Modify own call settings |
| `spark:xsi` | XSI events and call monitoring |

See [`docs/reference/authentication.md`](docs/reference/authentication.md) for full details on token types, OAuth flows, and scope requirements per endpoint.

## License

Apache 2.0 — see LICENSE.
