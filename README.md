# Webex Ops

Webex Ops: tell Claude what you want done in Webex, and it does it. Claude looks up the facts in the reference docs, follows a tested checklist, and makes the API calls itself through a built-in command layer. **You never type a command.**

It covers Webex Calling, admin, devices, messaging, meetings, and Contact Center (flows, AI agents, Connect, provisioning, reporting), plus CUCM-to-Webex migration. It runs inside [Claude Code](https://claude.com/claude-code) (Anthropic's AI coding assistant) or OpenAI's Codex.

> **Unofficial community CLI — not affiliated with or endorsed by Cisco.**

> **Use at your own risk.** This software is provided "AS IS", without warranty
> of any kind, and the authors accept no liability for any damage, data loss, or
> service disruption arising from its use (see [LICENSE](LICENSE), Apache 2.0
> §7–8). It performs **write and delete operations against live production
> Webex Calling and CUCM environments**, driven in part by non-deterministic AI.
> You are responsible for reviewing every action before it runs. Read
> [What keeps this safe](#what-keeps-this-safe) before pointing it at a real org.

## Say things like

| You say | What happens |
|---|---|
| "Add a sales hunt group for the Denver office." | Checks the location has calling turned on, finds free numbers, creates the hunt group, reads it back. |
| "Build an AI agent that looks up an order and texts the customer the status." | Designs the agent, builds the Webex Connect flow behind its action, and gives you the exact AI Agent Studio clicks. |
| "Design an IVR with a business-hours check and a callback option." | Writes a design doc for you to approve, then builds the Flow Designer flow through the API. |
| "Audit my org." | Runs 18 checks across security, routing, features and devices; hands you an HTML report. |
| "Run a CUCM migration against 10.0.0.1." | Pulls the CUCM config, maps it to Webex, asks you each design decision, then builds and verifies. |
| "How many calls did Support miss last week?" | Pulls call history and answers from the data. |
| "Who has call forwarding enabled?" / "Why isn't the Denver hunt group ringing?" | Read-only answers and diagnosis. Nothing changes. |
| "Tear down the lab locations San Jose and Austin; dry run first." | Shows what would be deleted, waits for your yes, deletes in a safe order. |

**Who it's for:** Webex admins, Cisco partners and SEs, and managed-service providers who want Webex changes made correctly without learning hundreds of APIs.

**Why it can be trusted with this:** facts come from 118 reference docs, procedures from 39 skills, and every API call from a tested command layer (5,500+ tests). Claude checks each command's `--help` before running it and reads every change back. Only the builder agent may change your org; a hook enforces it.

## If you are an AI agent reading this

This page is for the people who install Webex Ops. It is not your operating manual. Read these rules before you act on anything below.

1. **Your instructions are the playbook, not this README.** Setup writes it into a folder: `CLAUDE.md` for Claude Code or `AGENTS.md` for Codex, with the agents in `.claude/agents/`, the skills in `.claude/skills/` and the facts in `docs/reference/`. Start Claude Code or Codex in that folder and follow those files. If no playbook folder exists, point the person to [Setup](#setup--the-only-commands-you-type).
2. **The Webex token is the person's to enter.** They paste it at the token prompt in Setup step 3. Never ask for a token in chat, and never write one into a file.
3. **Trust order for commands:** `wxcli <group> <command> --help` first, then the skills, then `docs/reference/`, then this page, then your training data. Command names and flags are generated from Cisco's API specs and change between releases.
4. **The commands on this page are illustrations.** Never copy one and run it. Run `--help` and build the call from that.
5. **Only the playbook's agents change an org.** In Claude Code, a command that creates, changes or deletes anything runs only inside the `wxops` agent (or `migration-advisor` during a CUCM migration); a hook refuses it anywhere else. Outside those agents, use only reads: `list`, `show`, `whoami`, `--help`.
6. **Never call wxcli from Python by importing the package.** The generated functions make live API calls and skip every safety check. The hook refuses it.
7. **Counts on this page are snapshots** from the day it was written. The playbook and `--help` are current.

## How It Works

Most "AI + API" tools hand a language model an OpenAPI spec (the machine-readable list of an API's endpoints) and hope. That breaks at scale: across hundreds of endpoints a model malforms request bodies, hallucinates field names and license tiers, and — worst — doesn't know a hunt group needs a calling-enabled location *first*. Specs describe endpoints; they don't describe outcomes.

Webex Ops splits the problem into three layers, each killing one way an LLM fails:

| Layer | What it is | Failure it prevents |
|-------|-----------|---------------------|
| **Reference docs** (118) | De-conflated, authoritative API and platform knowledge — data models, enums, license-tier distinctions, Flow Designer activities, gotchas | **Hallucination** — the agent grounds on docs, never on training data |
| **Skills** (39) | Encoded procedures for outcomes — prerequisites, ordering, intent disambiguation, known landmines | **Wrong sequence / wrong tool** — the agent follows a checklist, not a guess |
| **CLI** (200 groups) | Tested, self-describing commands generated from 10 OpenAPI specs | **Malformed execution** — the model emits a command string, not hand-rolled HTTP |

Alongside the reference docs sit 27 step-by-step playbooks (send an SMS, set up a data lookup, build a scripted agent), each naming the reference doc that owns its values.

The model only does what it's reliably good at — reasoning and orchestration. Facts come from the docs, procedure from the skills, execution from the tested CLI.

**One request, traced** — *"Add a sales hunt group for the Denver office":*

1. The agent routes to the `configure-features` skill — not contact-center, not customer-assist (the routing table handles the overloaded word "queue").
2. The skill loads `docs/reference/call-features-major.md` for ground truth, then checks prerequisites in order: location exists → calling-enabled → users exist → numbers available.
3. Before building the command it runs `wxcli hunt-group create --help` — the CLI is the final source of truth for flags, never the docs or memory.
4. The CLI executes; a verify step reads the result back to confirm.

At every step the agent is forced back to an authoritative source: data model from the doc, flags from `--help`, final state from a read-back. It never operates on memory. That layered grounding *is* the design.

## What keeps this safe

- **Read-only by default.** Outside the builder agent, the shipped hook lets Claude run only `list`, `show`, `whoami` and `--help`. Anything that could change your org is refused unless it runs inside the `wxops` agent (or `migration-advisor` during a CUCM migration). A command the hook doesn't recognize is refused, not guessed at. The same rule covers the optional Flow Designer MCP server.
- **No way around the gate.** A Python script that imports the wxcli package is refused for every caller, so every API call goes through the checked command line.
- **Preview before anything destructive.** Cleanup and migration have dry runs; the agent shows you the plan and waits for your yes.
- **Every change is read back.** A success code means Webex accepted the request, not that it applied. The agent re-reads the resource and reports what is actually there.
- **Your token stays yours.** You paste it at a local prompt during Setup, never into the chat. It is stored in plaintext at `~/.wxcli/config.json`, so treat that file like a password. Personal tokens expire after 12 hours.
- **Still a live org, still an AI.** The same request can produce different actions. Test in a sandbox first, confirm every emergency (E911) address and callback number yourself, and read [Disclaimer & Safe Use](#disclaimer--safe-use).

Under Codex the protection is weaker in three specific ways; see [Codex](#codex).

## Why commands, not MCP

MCP (Model Context Protocol) is the plug-in standard that lets an AI call tools on a server. Cisco publishes some Webex MCP servers, so the natural question is why Webex Ops uses commands instead.

**"So it's a CLI?"** It's the command layer the AI uses. It's technically a command-line program, because that turned out to be the cheapest, most reliable way for an AI to drive hundreds of Webex APIs. But no human is meant to run it.

**The rule.** Commands are the default. A job switches to an official Cisco MCP server only when that server (1) does the whole job, writes included, (2) has been tested live on a real tenant, and (3) costs the same or fewer tokens.

- **The one measured comparison (2026-06-30).** Cisco's Webex Workspaces MCP server (16 tools, all read-only) cost about 11,750 tokens for one read task — list every workspace and the location it belongs to — against about 5,100 through the commands. Connecting the server put all 16 tool schemas (9,894 tokens) into context; the commands loaded only what the task touched. Claude Code has since begun loading MCP tool schemas on demand (observed 2026-10-18), so this result holds for that date and that server only, until it is measured again.
- **Writes.** The Workspaces server had no write tool at all. Cisco's Flow Designer MCP server covered 12 of the Flow Store's 63+ endpoints, and its `list_flows` returned empty lists even when flows existed. The commands do the whole job, writes included.
- **Picking the right tool.** Models pick reliably from a handful of tools, not hundreds of near-duplicates, and Webex is full of overloaded names ("queue" means three different things across Calling, Contact Center and Customer Assist). The skills sort that out before a command is chosen.
- **Commands compose and run anywhere.** Pipe one into the next, loop over a list of IDs, run the same commands in a script or CI with no AI at all.

This isn't anti-MCP. To let another agent platform drive Webex Ops, wrap the CLI behind **one** small MCP tool ("run a wxcli command"), not several hundred.

| Cisco MCP server | What it offered when checked | Path Claude uses | Last checked |
|---|---|---|---|
| Webex Workspaces (`https://mcp.webexapis.com/mcp/workspaces`) | 16 tools, all read-only (search, metrics, diff and lifecycle across devices, workspaces and locations); no write tool | commands | 2026-06-30 |
| Flow Designer (`wxcc-flow-builder`, the Flow Store's `/flow-store/mcp`) | 12 tools over 12 of 63+ Flow Store endpoints; `list_flows` returned empty lists; tokens rotated | commands (`cc-flow` and the Flow Store groups) | July 2026 (the day was not recorded) |

<details>
<summary>Optional MCP servers in the playbook</summary>

The playbook's `.mcp.json` lists two optional servers, with placeholders: Cisco's Flow Designer MCP server (`YOUR_FLOW_STORE_TOKEN`) and Supabase (`YOUR_SUPABASE_PROJECT_REF`, `YOUR_SUPABASE_ACCESS_TOKEN`), for a Supabase database behind an AI agent. Neither is needed: Claude does Flow Designer work through the commands. To use one, paste your own values over its placeholders (they are secrets, so this is yours to do), and delete an entry you don't use. The bundled Flow Store URL is the **US-1 production** address; an org homed in another region uses its region's production Flow Store host. In Claude Code, the Flow Designer server's read tools run anywhere, and its other tools run only inside the `wxops` agent. Under Codex the server reads its token from the `WEBEX_ACCESS_TOKEN` environment variable (`.codex/config.toml`), so no token is written into a project file. The table above is re-checked with the weekly Flow Store drift runbook (`tools/CLAUDE.md`).

</details>

## Setup — the only commands you type

You need [Claude Code](https://claude.com/claude-code) or Codex. Then you type three things: an install, a folder, and your Webex token (again whenever it expires). After that you talk to Claude.

**1. Install.**

```bash
pipx install wxcli      # isolated, always on PATH
```

Works on macOS, Linux, and Windows, with Python 3.11 or newer. `pipx` pulls every dependency automatically.

<details>
<summary>Don't have <code>pipx</code> (<code>command not found: pipx</code>)?</summary>

Install it first, then open a new terminal and run `pipx install wxcli`:

- **macOS** (with [Homebrew](https://brew.sh)): `brew install pipx && pipx ensurepath`
- **Linux** (Debian/Ubuntu): `sudo apt install pipx && pipx ensurepath`
- **Windows:** install [Python 3.11+](https://www.python.org/downloads/) (tick **"Add python.exe to PATH"** during setup), then `python -m pip install --user pipx && python -m pipx ensurepath`

Plain `pip install wxcli` usually fails on macOS and recent Linux: there may be no `pip` command at all, `pip3` with Homebrew's Python refuses with `externally-managed-environment`, and the Python built into macOS is 3.9, too old for wxcli. Use `pipx`.

</details>

**2. Put the playbook in a folder, and start Claude Code or Codex there.**

```bash
wxcli init                   # writes the Claude Code + Codex playbook into ./wxcli-playbook
cd wxcli-playbook && claude  # start Claude Code…
cd wxcli-playbook && codex   # …or start Codex — reads AGENTS.md + .codex/
```

The playbook ships inside the installed package, so there is nothing to clone. It holds:

- **2 agents:** `wxops`, which does every job that changes or audits your org, and `migration-advisor` for CUCM migrations.
- **39 skills and the reference docs.**
- **A `.claude/settings.json`** that pre-approves the skills and installs the safety hook ([What keeps this safe](#what-keeps-this-safe)).

`wxcli init --claude-only` or `wxcli init --codex-only` writes one of the two; `wxcli init --uninstall` removes the files `init` wrote. Personal overrides go in `.claude/settings.local.json`.

**3. Give it your Webex token.** Get a personal access token (a 12-hour admin key) from [developer.webex.com](https://developer.webex.com). Run `wxcli configure` and paste the token at the prompt. Identical in macOS/Linux Terminal, Windows PowerShell, and cmd:

```
wxcli configure
# prompts: "Webex API token:"  → paste token, press Enter
```

The token is your secret, so this step stays yours. When it expires, or Claude reports a 401 or 403, paste a new one: in Claude Code type `! wxcli configure` in the prompt (the `!` runs it in the session); in a terminal run `wxcli configure`. A partner token that reaches several customer orgs: `wxcli configure` asks which org to target.

Prefer a per-session environment variable to a saved token? Set `WEBEX_ACCESS_TOKEN` instead — `export WEBEX_ACCESS_TOKEN="YOUR_TOKEN"` (macOS / Linux), `$env:WEBEX_ACCESS_TOKEN="YOUR_TOKEN"` (PowerShell), `set WEBEX_ACCESS_TOKEN=YOUR_TOKEN` (cmd). Claude checks the token with `wxcli whoami` before it starts.

## What it can do

Each area below is a set of skills Claude picks from by itself. The commands shown are what Claude runs, printed so you can follow along; you don't type them.

### Webex Calling

Locations, users, numbers and licenses; auto attendants, call queues, hunt groups, paging, call park and pickup, voicemail groups, schedules; trunks, route groups, dial plans and translation patterns; per-person settings such as forwarding, do-not-disturb, executive-assistant and recording; phones, DECT, line keys and 9800-series PhoneOS settings; emergency addresses and callback numbers; live call control.

> "Create a San Jose location and turn on calling." "Set up call forwarding for the front desk." "Give the 9861 in reception ringtone 4 on line 2."

### Contact Center and AI agents

The deepest part of the playbook. Claude designs first, gets your approval, then builds.

- **Voice flows (IVRs)** in Flow Designer: business hours, menus, callbacks, skill-based routing, data lookups. Claude writes a design doc, then either builds the flow through the API or gives you a step-by-step build. The reference covers 48 Flow Designer activities, and 4 working example flows ship with the playbook.
- **AI agents** in AI Agent Studio, both kinds: *autonomous* agents, where an AI decides when to call each action, and *scripted* agents, built from intents and entities.
- **Webex Connect flows** behind those agents: the API call for an agent action, inbound conversations on SMS, WhatsApp, Apple Messages, RCS, email and live chat with hand-off to a person, outbound notifications with a voice fallback, and chat-to-voice escalation that carries the transcript.
- **Data lookups** from a flow or agent: the Business Rules Engine (Cisco's built-in lookup tables) or a database such as Supabase.
- **Contact Center setup:** agents, queues, entry points, teams, skills, dial numbers, business hours and campaigns, plus queue and agent statistics.
- **Diagrams and solution decks** from the design doc, for showing a customer.

Webex Connect and AI Agent Studio have no API for these steps, so for those parts Claude gives you the exact click path in each screen instead of doing it for you.

> "Build an AI agent action that looks up an order." "Send an SMS when a ticket closes." "Design an IVR with a business-hours check."

### CUCM-to-Webex migration

Ask "Run a CUCM migration" and give Claude the CUCM host and credentials. Claude pulls the configuration from CUCM through its admin API (AXL), maps every object to its Webex Calling equivalent, and stops at each design decision for you to answer, with a recommendation and its reasons. Then it builds, checks and reports.

Along the way you get a customer-ready **assessment report** (complexity score, environment inventory, analog gateway review, effort estimates), a **per-user before/after comparison**, and an **email-ready notice** for your users.

```bash
wxcli cucm init myproject                 # Create project
wxcli cucm discover --host 10.0.0.1 \    # Extract from CUCM via AXL
  --username admin --password secret -p myproject
wxcli cucm normalize -p myproject         # Normalize to canonical models
wxcli cucm map -p myproject               # Map CUCM objects to Webex operations
wxcli cucm analyze -p myproject           # Run 15 analyzers, generate decisions
wxcli cucm report --brand "Acme Corp" \   # Generate HTML assessment report
  --prepared-by "Jane Admin" -p myproject
wxcli cucm user-diff -p myproject         # Per-user before/after comparison
wxcli cucm user-notice --brand "Acme" \   # Email-ready migration notice
  --migration-date "2026-06-01" \
  --helpdesk "help@acme.com" -p myproject
wxcli cucm plan -p myproject              # Build dependency-ordered execution plan
wxcli cucm preflight -p myproject         # Run 10 preflight checks
wxcli cucm export -p myproject            # Export deployment plan
wxcli cucm execute -p myproject \         # Execute all operations concurrently
  --concurrency 15
```

The build creates things in dependency order, adopts a resource that already exists instead of failing, and skips anything whose prerequisite failed.

<details>
<summary>How the migration engine is built</summary>

- **SQLite-backed store** with objects, cross-references, decisions, and journal
- **42 normalizers** + a cross-reference builder that links related CUCM objects
- **26 mappers** that convert CUCM objects to Webex Calling operations
- **15 analyzers** that surface decisions requiring human review
- **Advisory system** with 25 per-decision rules + 30 cross-cutting patterns
- **Dependency graph** (NetworkX) for ordering and batch planning
- **Async execution engine** with configurable concurrency
- 3133 migration tests

</details>

### Org health assessment

Ask "audit my org". The `wxops` agent collects your org's configuration, runs 18 deterministic checks across 4 categories, and produces a self-contained HTML report.

| Category | Checks |
|----------|--------|
| **Security Posture** | Unrestricted international dialing, no outgoing call restrictions, auto attendant external transfer enabled, call queues without recording |
| **Routing Hygiene** | Empty dial plans, orphan route components (route groups/lists without trunks), trunk errors |
| **Feature Utilization** | Disabled auto attendants, understaffed call queues, single-member hunt groups, empty voicemail groups, empty paging groups, empty call parks |
| **Device Health** | Offline devices, users at device limit, unassigned devices, workspaces without devices, stale activation codes |

### Reporting and questions about your org

Plain-English questions answered from live data, without changing anything: call history (more than 70 ready-made call-history queries plus a guide for composing new ones), call queue and auto attendant statistics, call quality, Contact Center queue and agent statistics, meeting quality and usage.

> "How many calls did Support miss last week?" "Which locations have no users?" "Which queues had the longest waits yesterday?"

### Admin, identity, messaging and meetings

License audits and reclaiming licenses from inactive users; directory sync (SCIM), groups and domain verification; admin audit logs and security events; Webex spaces, bots and adaptive cards; scheduling and managing meetings; Video Mesh.

> "Reclaim licenses from users inactive for 90 days." "Post this incident card to the NOC space."

### Partner / multi-org

For partners, resellers and managed-service providers managing several customer organizations with one token. Ask Claude to switch the target org ("switch to the Acme org", "which org am I in?"); it runs these. Pasting the partner token stays your step (Setup, step 3), and that step asks which org to target first.

```bash
wxcli switch-org                  # Change the active target org
wxcli clear-org                   # Revert to single-org behavior
wxcli whoami                      # Shows "Target:" line when an org is set
```

The commands add the selected organization ID to every endpoint that accepts it — no extra flag required.

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

## Codex

`wxcli init` writes the Codex files too (`AGENTS.md`, `.codex/`). Start Codex in the folder and trust the folder when Codex asks: the shipped `.codex/config.toml` (approval policy, sandbox mode, MCP servers) takes effect only in a folder Codex trusts. Codex has no per-command allowlist, so expect an approval prompt when a command needs to run outside the workspace sandbox.

Three limits apply under Codex that Claude Code does not have:

- **Flow Designer MCP writes are not checked.** The Codex safety hook watches shell commands only, so a write through the Flow Designer MCP server is not held to the `wxops` agent the way it is in Claude Code. `wxcli` commands are checked.
- **Several unattended runs started at once may run without the safety lock.** In a 2026-10-20 test on Codex 0.163.0, 4 of 7 `codex exec` runs started together loaded none of the folder's hooks, and two of them ran a write the lock should have stopped. Runs started one at a time all loaded the hooks. Interactive Codex was not measured. Start runs one at a time.
- **The larger `AGENTS.md` limit needs a trusted folder.** The playbook sets `project_doc_max_bytes = 65536` so Codex reads all of `AGENTS.md`. Codex ignores that setting in a folder it does not trust, and by default cuts the file at 32,768 bytes.

## Updating

Claude can run this for you. At the start of each Claude Code session the playbook checks PyPI (cached for a day) and tells Claude when a newer wxcli exists, so Claude can offer the upgrade:

```bash
wxcli update           # check PyPI and upgrade in place
wxcli update --check   # report the latest version without upgrading
```

`wxcli update` detects how it was installed and upgrades accordingly — `pipx upgrade wxcli` for pipx installs, `pip install --upgrade wxcli` for pip installs — then deep-links the release notes for the new version. Then run `wxcli init` in the playbook folder again: it refreshes only the files it wrote, for the assistants already installed there, and never touches files you added.

Behind a firewall that blocks PyPI? Point `WXCLI_UPDATE_INDEX_URL` at an internal mirror, or install fresh with `pipx install wxcli`.

## For developers: the command layer on its own

Claude reads `--help`, not this section. It is here so you can follow what Claude does, or use the CLI in your own scripts and CI without any AI. Outside Claude, the reference docs in `docs/reference/` are a Webex API knowledge base any developer can read, and the **10 OpenAPI specs** (`specs/webex-*.json`) import into Postman or any API client.

```bash
wxcli --help                               # all 200 command groups
wxcli locations list                       # location IDs
wxcli users list --location-id LOC_ID      # person IDs
wxcli numbers list --location-id LOC_ID    # number inventory
wxcli hunt-group create --help             # every flag a command takes
```

<details>
<summary>More example commands, flags, and the common command groups</summary>

```bash
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
```

**Flags**

- **`--json-body`** — For complex nested settings (call forwarding rules, voicemail config, agent lists), pass the full JSON body: `wxcli call-queue update LOC_ID QUEUE_ID --json-body '{"agents": [...]}'`
- **`--all`** — On every `list` command: fetch **every** page instead of just the first. The default is a single fetch, so a count drawn from it on a large org is wrong. When pages are left behind the CLI says so on **stderr** (`Note: N records returned and the server has more pages...`). Walking is capped at 1000 pages (`WXCLI_MAX_PAGES`); hitting the cap prints an error containing **INCOMPLETE**, which means records are missing.
- **`--fields`** — A JMESPath expression (a JSON query language) applied to the response before rendering, on every command: `wxcli people list --fields '[].{name:displayName,id:id}' -o json`
- **`--debug`** — Add to any command for verbose HTTP request/response output

The full behavior reference, including the eleven known issues, is `docs/reference/wxcli-behavior.md`.

**Common command groups** (run `wxcli --help` to see all 200 groups, which also cover admin, device, messaging, meetings, and contact center APIs)

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

</details>

### Known limitations

- **Call control commands require a user-level OAuth token.** Admin and service app tokens return `400 "Target user not authorized"`. Use a personal access token from the user who will control calls.
- **Complex nested settings need `--json-body`.** Call forwarding rules, agent lists, voicemail config, and similar deeply nested structures can't be expressed as CLI flags — pass the full JSON body instead.
- **Some person call settings have no admin path** and need a user-level token. The list is in `docs/reference/wxcli-behavior.md` § 3. Known Issues, item 4.
- **CDR/analytics endpoints require the `analytics:read_all` scope**, which standard admin tokens may not include.

### Requirements

- Python 3.11+
- A Webex admin account. A personal access token is enough to start; for long-running work use a service app. Token types and OAuth flows: [`docs/reference/authentication.md`](docs/reference/authentication.md).

<details>
<summary>OAuth scopes, by API domain</summary>

Not all scopes are needed — request only those for the API domains you use.

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

</details>

## For maintainers

This section is for people changing this repository. In the repo, too, Claude runs the commands; the rules it follows are in `.claude/rules/repo-development.md` and `tools/CLAUDE.md`.

<details>
<summary>Project layout, design decisions, building and checking</summary>

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
├── tests/                        # 5,500+ tests (pytest)
├── specs/                        # 10 OpenAPI 3.0 specs (calling, admin, device, messaging, meetings, CC, CC Flow Store, UCM, BroadWorks, wholesale)
├── docs/reference/               # 118 reference docs (API + platform knowledge + gotchas)
├── docs/playbooks/               # 27 step-by-step platform guides
├── .claude/agents/               # wxops (the builder) + migration-advisor
└── .claude/skills/               # 39 skills
```

**Key design decisions:**

- **Commands are generated, never hand-edited.** Fix bugs in `field_overrides.yaml` and regenerate with `tools/generate_commands.py`.
- **The CLI uses raw HTTP** via its own `WebexSession` client (`src/wxcli/auth.py`) built on `httpx`, not any third-party SDK. Every operation in the 10 bundled specs has a command, except 194 deliberately skipped; the drift gate enforces it.
- **Reference docs serve both humans and AI.** Developers can read them directly; the playbook loads them as context for guided configuration.

**Building and checking:**

- **Drift gate.** `venv/bin/python -m tools.drift_check --enforce` must end `result: PASS`: every command a doc cites exists, every published count matches, every group is routed. Run it in the venv; on a Python without `pyyaml` it crashes.
- **Tests.** Run the files a change touches, `venv/bin/python -m pytest <files> -q`. The `live` and `mutation` tiers call a real org and are opt-in; CI runs everything else on Python 3.11 and 3.12.
- **The playbook bundle.** `src/wxcli/_playbook/` is generated: never hand-edit it. After changing a shipped source (`CLAUDE.md`, `.claude/agents|skills|rules`, `docs/reference|playbooks|templates|examples`), run `python wxcli-dist/assemble.py` and commit the bundle with the change. It reads tracked files only (`git ls-files`), substitutes the curated `wxcli-dist/settings.bundled.json` and the sanitized `wxcli-dist/mcp.bundled.json`, generates the Codex profile, and fails on a repo-only path left in a shipped file.
- **Releases.** A `v*` tag runs `.github/workflows/release.yml`, which re-runs the assembler, refuses to publish a stale bundle, and publishes to PyPI.

</details>

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
  life-safety risk. Independently confirm every emergency address and emergency
  callback number (ECBN) after any change — do not rely on the tool's read-back alone.
- **`cleanup run --all` is irreversible** and deletes an entire org's calling
  config. There is no undo.
- **Test in a lab or sandbox org first**, especially for CUCM migrations.
- **You are the operator of record.** You are responsible for reviewing and
  authorizing every action, and for compliance with your own change-control,
  regulatory (e.g. the US emergency-calling laws Kari's Law and RAY BAUM's Act),
  and data-handling obligations.

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
