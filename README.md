# Webex Ops

Webex Ops: tell Claude what you want done in Webex, and it does it. Claude looks up the facts in the reference docs, follows a tested checklist, and makes the API calls itself through a built-in command layer. **You never type a command.**

It covers Webex Calling, admin, devices, messaging, meetings, and Contact Center (flows, AI agents, Connect, provisioning, reporting). It works in Claude Code and in Codex.

> **Unofficial community CLI — not affiliated with or endorsed by Cisco.**

> **Use at your own risk.** This software is provided "AS IS", without warranty
> of any kind, and the authors accept no liability for any damage, data loss, or
> service disruption arising from its use (see [LICENSE](LICENSE), Apache 2.0
> §7–8). It performs **write and delete operations against live production
> Webex Calling and CUCM environments**, driven in part by non-deterministic AI.
> You are responsible for reviewing every action before it runs.

## Why commands, not MCP

**"So it's a CLI?"** It's the command layer the AI uses. It's technically a command-line program, because that turned out to be the cheapest, most reliable way for an AI to drive hundreds of Webex APIs. But no human is meant to run it.

**The rule:** commands are the default. A job moves to an official Cisco MCP server only when that server does the whole job, writes included, has been tested live on a real tenant, and costs the same or fewer tokens. The reasoning, the measured numbers and the dated "which path" table are in [Commands, not MCP](#commands-not-mcp).

## Setup — the only commands you type

You need [Claude Code](https://claude.com/claude-code) or Codex. Then you type three things: an install, a folder, and your Webex token (again whenever it expires). After that you talk to Claude.

**1. Install.**

```bash
pipx install wxcli      # isolated, always on PATH
```

Works on macOS, Linux, and Windows, with Python 3.11 or newer. `pipx` pulls every dependency automatically. Don't have `pipx` (`command not found: pipx`)? Install it first, then open a new terminal and run `pipx install wxcli`:

- **macOS** (with [Homebrew](https://brew.sh)): `brew install pipx && pipx ensurepath`
- **Linux** (Debian/Ubuntu): `sudo apt install pipx && pipx ensurepath`
- **Windows:** install [Python 3.11+](https://www.python.org/downloads/) (tick **"Add python.exe to PATH"** during setup), then `python -m pip install --user pipx && python -m pipx ensurepath`

Plain `pip install wxcli` usually fails on macOS and recent Linux: there may be no `pip` command at all, `pip3` with Homebrew's Python refuses with `externally-managed-environment`, and the Python built into macOS is 3.9, too old for wxcli. Use `pipx`.

**2. Put the playbook in a folder, and start Claude Code or Codex there.**

```bash
wxcli init                   # writes the Claude Code + Codex playbook into ./wxcli-playbook
cd wxcli-playbook && claude  # start Claude Code…
cd wxcli-playbook && codex   # …or start Codex — reads AGENTS.md + .codex/
```

The playbook ships **inside the wheel**, so no clone is needed. It holds 2 agents (`wxops`, which does every job that changes or audits your org, and `migration-advisor` for CUCM migrations), 39 skills and the reference docs, plus a `.claude/settings.json` that pre-approves the skills and installs the safety hook: only the `wxops` agent may run a command that changes your org. `wxcli init --claude-only` or `wxcli init --codex-only` writes one of the two; `wxcli init --uninstall` removes the files `init` wrote. Personal overrides go in `.claude/settings.local.json`.

**3. Give it your Webex token.** Get a personal access token from [developer.webex.com](https://developer.webex.com) (valid for 12 hours). Run `wxcli configure` and paste the token at the prompt. Identical in macOS/Linux Terminal, Windows PowerShell, and cmd:

```
wxcli configure
# prompts: "Webex API token:"  → paste token, press Enter
```

The token is your secret, so this step stays yours. When it expires, or Claude reports a 401 or 403, paste a new one: in Claude Code type `! wxcli configure` in the prompt (the `!` runs it in the session); in a terminal run `wxcli configure`. A partner token that reaches several customer orgs: `wxcli configure` asks which org to target.

Prefer a per-session environment variable to a saved token? Set `WEBEX_ACCESS_TOKEN` instead — `export WEBEX_ACCESS_TOKEN="YOUR_TOKEN"` (macOS / Linux), `$env:WEBEX_ACCESS_TOKEN="YOUR_TOKEN"` (PowerShell), `set WEBEX_ACCESS_TOKEN=YOUR_TOKEN` (cmd). Claude checks the token with `wxcli whoami` before it starts.

## Updating

Claude can run this for you. At the start of each Claude Code session the playbook checks PyPI (cached for a day) and tells Claude when a newer wxcli exists, so Claude can offer the upgrade:

```bash
wxcli update           # check PyPI and upgrade in place
wxcli update --check   # report the latest version without upgrading
```

`wxcli update` detects how it was installed and upgrades accordingly — `pipx upgrade wxcli` for pipx installs, `pip install --upgrade wxcli` for pip installs — then deep-links the release notes for the new version. Then run `wxcli init` in the playbook folder again: it refreshes only the files it wrote, for the assistants already installed there, and never touches files you added.

Behind a firewall that blocks PyPI? Point `WXCLI_UPDATE_INDEX_URL` at an internal mirror, or install fresh with `pipx install wxcli`.

## What you can ask for

Say what you want in plain words. Claude interviews you about the details, writes a plan, makes the changes through the `wxops` agent and reads the result back. A step that only exists as a click in a Cisco screen comes to you as an exact click path.

- **Build Webex Calling.** "Add a sales hunt group for the Denver office." "Create a San Jose location and turn on calling." "Set up call forwarding for the front desk."
- **Contact Center flows and AI agents.** "Build an AI agent action that looks up an order." "Design an IVR with a business-hours check." "Send an SMS when a ticket closes." "Create a Contact Center queue." Claude designs first, then builds in Flow Designer, Webex Connect and AI Agent Studio.
- **Migrate from CUCM.** "Run a CUCM migration," with the CUCM host and credentials. You answer each design decision; Claude runs the pipeline ([what it runs](#cucm-to-webex-migration)).
- **Audit your org.** "Audit my org." You get a self-contained HTML report ([the checks](#org-health-assessment)).
- **Clean up.** "Tear down the lab locations San Jose and Austin, and show me a dry run first." ([what it deletes, in order](#cleanup))
- **Work across customer orgs (partners).** "Switch the target org to Acme." "Which org am I working in?" ([details](#partner--multi-org))
- **Find out what is there.** "Who has call forwarding enabled?" "Which locations have no users?"
- **Fix what is broken.** "Why isn't the Denver hunt group ringing?" "Why did my Connect flow fail?"

## How It Works

Most "AI + API" tools hand a language model an OpenAPI spec and hope. That breaks at scale: across hundreds of endpoints a model malforms request bodies, hallucinates field names and license tiers, and — worst — doesn't know a hunt group needs a calling-enabled location *first*. Specs describe endpoints; they don't describe outcomes.

wxops splits the problem into three layers, each killing one way an LLM fails:

| Layer | What it is | Failure it prevents |
|-------|-----------|---------------------|
| **Reference docs** (118) | De-conflated, authoritative API and platform knowledge — data models, enums, license-tier distinctions, Flow Designer activities, gotchas | **Hallucination** — the agent grounds on docs, never on training data |
| **Skills** (39) | Encoded procedures for outcomes — prerequisites, ordering, intent disambiguation, known landmines | **Wrong sequence / wrong tool** — the agent follows a checklist, not a guess |
| **CLI** (200 groups) | Tested, self-describing commands generated from 10 OpenAPI specs | **Malformed execution** — the model emits a command string, not hand-rolled HTTP |

(Counts from `git ls-files` on 2026-10-20: reference docs exclude the folder indexes.)

The model only does what it's reliably good at — reasoning and orchestration. Facts come from the docs, procedure from the skills, execution from the tested CLI.

**One request, traced** — *"Add a sales hunt group for the Denver office":*

1. The agent routes to the `configure-features` skill — not contact-center, not customer-assist (the disambiguation map handles the overloaded word "queue").
2. The skill loads `docs/reference/call-features-major.md` for ground truth, then checks prerequisites in order: location exists → calling-enabled → users exist → numbers available.
3. Before building the command it runs `wxcli hunt-group create --help` — the CLI is the final source of truth for flags, never the docs or memory.
4. The CLI executes; a verify step reads the result back to confirm.

At every step the agent is forced back to an authoritative source: data model from the doc, flags from `--help`, final state from a read-back. It never operates on memory. That layered grounding *is* the design.

## Commands, not MCP

The natural question for an agent-driven tool: why not expose the API as MCP tools? Commands are the default here, for these reasons:

- **The one measured comparison (2026-06-30).** On 2026-06-30, Cisco's Webex Workspaces MCP server (16 tools, all read-only) cost about 11,750 tokens for one read task — list every workspace and the location it belongs to — against about 5,100 through the commands. Connecting the server put all 16 tool schemas (9,894 tokens) into context for any call; the commands loaded only the skill and the commands the task touched, each one's schema read on demand with `wxcli <group> <command> --help`. Claude Code has since begun loading MCP tool schemas on demand (observed 2026-10-18), so this result holds for that date and that server only, until it is measured again.
- **Writes.** The Workspaces server had no write tool at all. Cisco's Flow Designer MCP server covered 12 of the Flow Store's 63+ endpoints, and its `list_flows` returned empty lists even when flows existed. The commands do the whole job, writes included.
- **Tool-selection accuracy collapses well before hundreds.** Models reliably pick from a handful of tools, not a sea of near-duplicates — and this surface is full of overloaded names ("queue" means three different things across Calling, Contact Center, and Customer Assist). The skill layer disambiguates intent; a flat tool list just hands the model the ambiguity.
- **CLI commands compose; MCP tool calls don't.** Pipe to `jq`, filter with `grep`, chain a list of IDs into the next command. Ops work is full of "get these, feed them to that" — the shell makes it trivial.
- **The CLI runs without an LLM at all.** The same commands work in scripts and in CI, backed by thousands of tests. An MCP tool only exists inside an MCP client.

**The rule.** Commands are the default. A job switches to an official Cisco MCP server only when that server (1) does the whole job, writes included, (2) has been tested live on a real tenant, and (3) costs the same or fewer tokens.

This isn't anti-MCP. MCP is the right *thin boundary* for host integration: to let an agent platform drive wxops, you wrap the CLI behind **one** small MCP surface — a single "run a wxcli command" tool — not several hundred. The CLI stays the execution layer; MCP is just the seam. You get the integration without paying the tool-explosion tax.

### Which path, last checked on

| Cisco MCP server | What it offered when checked | Path Claude uses | Last checked |
|---|---|---|---|
| Webex Workspaces (`https://mcp.webexapis.com/mcp/workspaces`) | 16 tools, all read-only (search, metrics, diff and lifecycle across devices, workspaces and locations); no write tool | commands | 2026-06-30 |
| Flow Designer (`wxcc-flow-builder`, the Flow Store's `/flow-store/mcp`) | 12 tools over 12 of 63+ Flow Store endpoints; `list_flows` returned empty lists; tokens rotated | commands (`cc-flow` and the Flow Store groups) | July 2026 (the day was not recorded) |

Re-checked with the weekly Flow Store drift runbook (`tools/CLAUDE.md`).

### Optional MCP servers in the playbook

The playbook's `.mcp.json` lists two optional servers, with placeholders: Cisco's Flow Designer MCP server (`YOUR_FLOW_STORE_TOKEN`) and Supabase (`YOUR_SUPABASE_PROJECT_REF`, `YOUR_SUPABASE_ACCESS_TOKEN`), for a Supabase database behind an AI agent. Neither is needed: Claude does Flow Designer work through the commands. To use one, paste your own values over its placeholders (they are secrets, so this is yours to do), and delete an entry you don't use. The bundled Flow Store URL is the **US-1 production** endpoint; an org homed in another region uses its region's production Flow Store host. In Claude Code, the Flow Designer server's read tools run anywhere, and its other tools run only inside the `wxops` agent. Under Codex the server reads its token from the `WEBEX_ACCESS_TOKEN` environment variable (`.codex/config.toml`), so no token is written into a project file.

## Codex

`wxcli init` writes the Codex files too (`AGENTS.md`, `.codex/`). Start Codex in the folder and trust the folder when Codex asks: the shipped `.codex/config.toml` (approval policy, sandbox mode, MCP servers) takes effect only in a folder Codex trusts. Codex has no per-command allowlist, so expect an approval prompt when a command needs to run outside the workspace sandbox.

Three limits apply under Codex that Claude Code does not have:

- **Flow Designer MCP writes are not checked.** The Codex safety hook watches shell commands only, so a write through the Flow Designer MCP server is not held to the `wxops` agent the way it is in Claude Code. `wxcli` commands are checked.
- **Several headless runs started at once may run without the safety lock.** In a 2026-10-20 test on Codex 0.163.0, 4 of 7 `codex exec` runs started together loaded none of the folder's hooks, and two of them ran a write the lock should have stopped. Runs started one at a time all loaded the hooks. Interactive Codex was not measured. Start runs one at a time.
- **The larger `AGENTS.md` limit needs a trusted folder.** The playbook sets `project_doc_max_bytes = 65536` so Codex reads all of `AGENTS.md`. Codex ignores that setting in a folder it does not trust, and by default cuts the file at 32,768 bytes.

## Reference material Claude uses

This part is what Claude reads and runs, not instructions for you. It is here so you can follow what Claude does and check it. Outside Claude, the reference docs in `docs/reference/` are a Webex API knowledge base any developer can read, and the **10 OpenAPI specs** (`specs/webex-*.json`) import into Postman or any API client.

### Common commands

```bash
# See all 200 command groups
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
wxcli locations list                       # Get location IDs
wxcli users list --location-id LOC_ID      # Get person IDs
wxcli numbers list --location-id LOC_ID  # Get number inventory
```

### Flags

- **`--json-body`** — For complex nested settings (call forwarding rules, voicemail config, agent lists), pass the full JSON body: `wxcli call-queue update LOC_ID QUEUE_ID --json-body '{"agents": [...]}'`
- **`--all`** — On every `list` command: fetch **every** page instead of just the first, overriding `--limit`. The default is a single fetch, so on a large org `wxcli people list` answers from page one and a count drawn from it is wrong. When a single fetch leaves pages behind the CLI says so on **stderr** (`Note: N records returned and the server has more pages...`) — easy to miss if you are piping stdout. Walking is capped at 1000 pages (`WXCLI_MAX_PAGES`); hitting the cap prints an error containing **INCOMPLETE**, which means records are missing. On endpoints that do not paginate the flag is accepted and does nothing, deliberately, so the rule is the same on every list command.
- **`--fields`** — A JMESPath expression applied to the response before rendering, on every command: `wxcli people list --fields '[].{name:displayName,id:id}' -o json`
- **`--debug`** — Add to any command for verbose HTTP request/response output, useful for troubleshooting

### Command groups

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

This table shows the most commonly used groups. Run `wxcli --help` to see all 200 groups, which also cover admin, device, messaging, meetings, and contact center APIs.

### CUCM-to-Webex migration

A full migration pipeline at `src/wxcli/migration/` that analyzes a CUCM environment, maps objects to Webex Calling equivalents, and executes the migration. 3133 tests. You start it by asking Claude ("Run a CUCM migration") and answer each review decision; Claude runs the phases below, one at a time.

#### Pipeline

```bash
wxcli cucm init myproject                 # Create project
wxcli cucm discover --host 10.0.0.1 \    # Extract from CUCM via AXL
  --username admin --password secret -p myproject
wxcli cucm normalize -p myproject         # Normalize to canonical models
wxcli cucm map -p myproject               # Map CUCM objects to Webex operations
wxcli cucm analyze -p myproject           # Run 14 analyzers, generate decisions
wxcli cucm report --brand "Acme Corp" \   # Generate HTML assessment report
  --prepared-by "Jane Admin" -p myproject
```

The assessment report provides a complexity score, environment inventory, analog gateway review, and effort estimates — suitable for customer-facing delivery.

#### Additional pipeline outputs

```bash
wxcli cucm user-diff -p myproject         # Per-user before/after comparison
wxcli cucm user-notice --brand "Acme" \   # Email-ready migration notice
  --migration-date "2026-06-01" \
  --helpdesk "help@acme.com" -p myproject
```

#### Execution

After analysis and decision review:

```bash
wxcli cucm plan -p myproject              # Build dependency-ordered execution plan
wxcli cucm preflight -p myproject         # Run 8 preflight checks
wxcli cucm export -p myproject            # Export deployment plan
wxcli cucm execute -p myproject \         # Execute all operations concurrently
  --concurrency 15
```

The execution engine handles 409 auto-recovery (existing resources), cascade-skip (failed dependencies), and concurrent batch execution. A 561-operation stress test completes in ~90 seconds.

#### Migration architecture

- **SQLite-backed store** with objects, cross-references, decisions, and journal
- **42 normalizers** (Pass 1) + CrossReferenceBuilder (34 relationships)
- **26 mappers** that convert CUCM objects to Webex Calling operations
- **14 analyzers** that surface decisions requiring human review
- **Advisory system** with 19 per-decision rules + 30 cross-cutting patterns
- **NetworkX DAG** for dependency ordering and batch planning
- **Async execution engine** with configurable concurrency

### Org health assessment

An automated audit of a live Webex Calling org. Runs 18 deterministic checks across 4 categories and produces a self-contained HTML report.

#### Categories and checks

| Category | Checks |
|----------|--------|
| **Security Posture** | Unrestricted international dialing, no outgoing call restrictions, auto attendant external transfer enabled, call queues without recording |
| **Routing Hygiene** | Empty dial plans, orphan route components (route groups/lists without trunks), trunk errors |
| **Feature Utilization** | Disabled auto attendants, understaffed call queues, single-member hunt groups, empty voicemail groups, empty paging groups, empty call parks |
| **Device Health** | Offline devices, users at device limit, unassigned devices, workspaces without devices, stale activation codes |

#### How it runs

Ask Claude: "audit my org". The `wxops` agent orchestrates three phases: collect data via `wxcli`, analyze with the check engine, and generate the HTML report.

### Partner / multi-org

For partners, VARs, and MSPs managing multiple customer organizations with a single token. Ask Claude to switch the target org ("switch to the Acme org", "which org am I in?"); it runs these. Pasting the partner token stays your step (Setup, step 3), and that step asks which org to target first.

```bash
wxcli switch-org                  # Change the active target org
wxcli clear-org                   # Revert to single-org behavior
wxcli whoami                      # Shows "Target:" line when an org is set
```

The generated commands add the selected `orgId` to every endpoint that accepts it — no extra flag required.

### Cleanup

Ask Claude to tear down what you name ("delete the lab locations San Jose and Austin; dry run first"). It batch-deletes Webex Calling resources in dependency-safe order (13 layers, reverse of creation order):

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

### Known limitations

- **Call control commands require a user-level OAuth token.** Admin and service app tokens return `400 "Target user not authorized"`. Use a personal access token from the user who will control calls.
- **Complex nested settings need `--json-body`.** Call forwarding rules, agent lists, voicemail config, and similar deeply nested structures can't be expressed as CLI flags — pass the full JSON body instead.
- **6 person call settings are user-only.** `simultaneousRing`, `sequentialRing`, `priorityAlert`, `callNotify`, `anonymousCallReject`, and `callPolicies` only work with user-level tokens, not admin tokens.
- **CDR/analytics endpoints require the `analytics:read_all` scope**, which standard admin tokens may not include.

### Requirements

- Python 3.11+ (includes `pip`)
- A Webex admin account with access tokens

#### OAuth scopes

The CLI covers 200 command groups across calling, admin, device, messaging, meetings, and contact center APIs. Not all scopes are needed — request only those for the API domains you use.

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
| `spark:xsi` | XSI scope for Webex Calling resources |

See [`docs/reference/authentication.md`](docs/reference/authentication.md) for full details on token types, OAuth flows, and scope requirements per endpoint.

## For maintainers

This section is for people changing this repository. In the repo, too, Claude runs the commands; the rules it follows are in `.claude/rules/repo-development.md` and `tools/CLAUDE.md`.

### Project layout

```
wxops/
├── src/wxcli/                    # CLI source (Typer + httpx REST client)
│   ├── main.py                   # Entry point — registers 200 command groups
│   ├── auth.py                   # Token storage and API client init
│   ├── output.py                 # Table/JSON output formatting
│   ├── commands/                 # generated command modules (one per API tag) + _registry.py manifest
│   ├── org_health/               # Org health assessment engine (18 checks → HTML report)
│   ├── _playbook/                # GENERATED playbook bundle that `wxcli init` writes (Claude Code + Codex)
│   └── migration/                # CUCM-to-Webex migration engine
│       ├── cucm/                 # AXL extractors and discovery
│       ├── transform/            # Normalizers, mappers, analyzers
│       ├── execute/              # Async execution engine + handlers
│       ├── advisory/             # Decision recommendations
│       ├── report/               # HTML/PDF assessment report generator
│       └── models.py             # 38 canonical data models
├── tools/                        # Code generator pipeline and the drift gate
│   ├── generate_commands.py      # Orchestrator: OpenAPI → Click commands
│   ├── openapi_parser.py         # Parses OpenAPI 3.0 specs into Endpoint objects
│   ├── command_renderer.py       # Renders Endpoints into Python command files
│   ├── drift_check.py            # The drift gate (docs, skills and CLI agree)
│   └── field_overrides.yaml      # Table columns, display config, bug fixes
├── wxcli-dist/                   # assemble.py + the curated settings, MCP and hook files it ships
├── tests/                        # 5560 tests (pytest)
├── specs/                        # 10 OpenAPI 3.0 specs (calling, admin, device, messaging, meetings, CC, CC Flow Store, UCM, BroadWorks, wholesale)
├── docs/reference/               # 118 reference docs (API + platform knowledge + gotchas)
├── docs/playbooks/               # step-by-step platform guides
├── .claude/agents/               # wxops (the builder) + migration-advisor
└── .claude/skills/               # 39 skills
```

**Key design decisions:**

- **Commands are generated, never hand-edited.** Fix bugs in `field_overrides.yaml` and regenerate with `tools/generate_commands.py`.
- **The CLI uses raw HTTP** via its own `WebexSession` client (`src/wxcli/auth.py`) built on `httpx`, not any third-party SDK. This gives 100% API coverage without external dependencies.
- **Reference docs serve both humans and AI.** Developers can read them directly; the playbook loads them as context for guided configuration.

### Building and checking

- **Drift gate.** `python -m tools.drift_check --enforce` must end `result: PASS`: every command a doc cites exists, every published count matches, every group is routed.
- **Tests.** Run the files a change touches, `venv/bin/python -m pytest <files> -q`. The `live` and `mutation` tiers call a real org and are opt-in; CI runs everything else on Python 3.11 and 3.12.
- **The playbook bundle.** `src/wxcli/_playbook/` is generated: never hand-edit it. After changing a shipped source (`CLAUDE.md`, `.claude/agents|skills|rules`, `docs/reference|playbooks|templates|examples`), run `python wxcli-dist/assemble.py` and commit the bundle with the change. It reads tracked files only (`git ls-files`), substitutes the curated `wxcli-dist/settings.bundled.json` and the sanitized `wxcli-dist/mcp.bundled.json`, generates the Codex profile, and fails on a repo-only path left in a shipped file.
- **Releases.** A `v*` tag runs `.github/workflows/release.yml`, which re-runs the assembler, refuses to publish a stale bundle, and publishes to PyPI.

## Disclaimer & Safe Use

wxcli is an unofficial, community-maintained tool. It is **not affiliated with,
endorsed by, or supported by Cisco.** "Webex", "Webex Calling", and "CUCM" are
Cisco trademarks, used here only to describe interoperability.

**This tool changes and deletes real telephony configuration.** The AI playbook
reasons and orchestrates using a large language model, which is non-deterministic:
the same prompt can produce different actions, and the agent can select the wrong
resource. The layered design (docs → skills → tested CLI, with read-back
verification) is built to reduce this, but **cannot eliminate it.**

Before running anything against a production org:

- **Preview first.** Use `--dry-run` (cleanup, migration) and review the plan.
- **Verify emergency services.** E911 / emergency-callback misconfiguration is a
  life-safety risk. Independently confirm every emergency address and ECBN after
  any change — do not rely on the tool's read-back alone.
- **`cleanup run --all` is irreversible** and deletes an entire org's calling
  config. There is no undo.
- **Test in a lab or sandbox org first**, especially for CUCM migrations.
- **You are the operator of record.** You are responsible for reviewing and
  authorizing every action, and for compliance with your own change-control,
  regulatory (e.g. Kari's Law / RAY BAUM's Act), and data-handling obligations.

By using this tool you accept these risks and the terms of the Apache 2.0 License.

### Credentials, secrets, and API usage

- **Tokens are stored locally in plaintext** in your wxcli config file. Treat that
  file like a password — it grants full admin access to your Webex org. Personal
  access tokens expire after 12 hours; OAuth/service-app tokens live longer, so
  guard them accordingly.
- **CUCM AXL credentials** passed inline to `wxcli cucm discover --username/--password`
  land in your shell history. Prefer a prompt-based flow or a throwaway shell, and
  clear the history afterward.
- **The AI playbook can generate many API calls in a loop.** Long agent runs and
  large migrations may hit Webex API rate limits; the tool retries, but you own the
  API-usage footprint against your org.

## License

Apache 2.0 — see LICENSE.
