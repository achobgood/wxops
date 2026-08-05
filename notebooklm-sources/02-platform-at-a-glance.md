# Platform at a Glance

## The numbers

| Dimension | Scale |
|---|---|
| CLI command groups | **179** |
| Domain skills (loaded on demand) | **24** |
| OpenAPI 3.0 specs | **10** |
| API reference docs | **~50** |
| AI agents | **2** (a Sonnet builder + an Opus migration advisor) |
| Automated tests | **thousands** — over **2,700 in the migration engine alone** |

One command-line tool, driven by natural language, covering provisioning, feature config, call settings, routing, devices, messaging, meetings, contact center, migration, and auditing — with full create/read/update/delete across the surface.

## The core idea: a three-layer architecture

Most "AI + API" tools hand a model an OpenAPI spec and hope. wxops instead splits the problem into three layers, **each one killing a specific way an LLM fails**:

| Layer | What it is | The failure it prevents |
|---|---|---|
| **Reference docs** (~50) | De-conflated, authoritative API knowledge — data models, enums, license-tier distinctions, hard-won gotchas | **Hallucination** — the agent grounds on docs, never on training data |
| **Skills** (24) | Encoded procedures for outcomes — prerequisites, ordering, intent disambiguation, known landmines | **Wrong sequence / wrong tool** — the agent follows a checklist, not a guess |
| **CLI** (179 groups) | Tested, self-describing commands generated from 10 OpenAPI specs | **Malformed execution** — the model emits a command string, not hand-rolled HTTP |

The model only does what it is reliably good at — **reasoning and orchestration**. Facts come from the docs, procedure from the skills, execution from the tested CLI. That layered grounding *is* the design.

## API domains covered

| Domain | What it covers |
|---|---|
| **Calling** | Provisioning, call features, person/workspace settings, routing, call control, reporting |
| **Admin** | Org management, identity/SCIM, licensing, audit, hybrid, partner ops |
| **Devices** | Phone/DECT provisioning, PhoneOS/RoomOS configs, xAPI, workspaces |
| **Messaging** | Spaces, teams, memberships, bots, adaptive cards, ECM |
| **Meetings** | Meeting CRUD, transcripts, recordings, Video Mesh, polls, Q&A |
| **Contact Center** | Agents, queues, entry points, flows, campaigns, analytics |

Four more specs round out the ten: **Wholesale**, **BroadWorks**, **UCM Cloud**, and **Text-to-Speech**.

## The wxcli CLI — why a CLI, not an MCP server

`wxcli` is a regular Python command-line tool. Its commands are **generated from the OpenAPI specs**, never hand-edited — fix a bug in the generator config and regenerate. That matters for the AI in four ways:

- **Self-documenting, just-in-time.** The model pulls one command's schema on demand with `wxcli <group> <command> --help`. Nothing loads up front. (Contrast: MCP tool schemas load *eagerly, every turn* — see doc 04.)
- **Composable.** Pipe to `jq`, filter with `grep`, chain a list of IDs into the next command. Real ops work is "get these, feed them to that."
- **Tested and LLM-free.** The same commands run in scripts, in CI, and by hand — backed by thousands of tests. An MCP tool only exists inside an MCP client.
- **Disambiguated by the skill layer**, so the model never has to pick from a sea of near-duplicate, overloaded tool names.

## Partner / multi-org support

For partners, VARs, and MSPs managing many customer orgs with a single token, wxops auto-detects multi-org tokens, prompts for the target org, and then **~1,150 commands transparently inject the correct `orgId`** into every API call — no flag required. The builder agent also hard-stops and confirms the target org before any write, so you never provision into the wrong customer.
