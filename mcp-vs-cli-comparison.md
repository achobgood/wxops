# Webex Workspaces MCP vs. wxcli — Token Cost & Capability

**Scope:** A narrow, measured comparison of Cisco's official Webex **Workspaces** MCP server
(`https://mcp.webexapis.com/mcp/workspaces`) against the wxcli CLI on two axes: **tokens to
do one task** and **what each can do**. Run **2026-06-30** against a real org. Everything
here is measured this session unless explicitly marked an estimate.

> **Framing:** This is *not* "CLI instead of skills" — we use 30+ skills. The question is
> how the execution layer *under* the skills is exposed: a curated MCP tool surface vs. an
> open CLI.

**Method.** Token counts use `tiktoken` `cl100k_base` on the verbatim artifacts — for MCP,
each tool's live definition as the Anthropic tools-API block `{name, description,
input_schema}` (compact JSON); for wxcli, the raw stdout of each `--help`/command. Task N1
was run live both ways. The CLI's orchestration skill **is counted** on the wxcli side; the
MCP side is given a free pass (a read needs no skill). Under the BU's "MCP + skills"
standard a skill would load on *both* sides and cancel — that framing is noted where it
changes the multiple.

---

## TL;DR

| | Webex Workspaces MCP | wxcli |
|---|---|---|
| Total tokens, one read task (N1) | **~11,750** | **~5,100** (**~2.3–4× cheaper**) |
| Why | All 16 tool schemas forced into context for any call (**9,894**) | Loads only the skill + the commands touched (**2,151 + 818**) |
| Operations exposed | **16, all read-only** | Full CRUD across **173 command groups** |
| Writes (provision / configure / migrate) | **None** | Yes |
| Schema load model | All 16 schemas **eagerly** | One command's `--help`, **JIT** |

**Headline:** for an ordinary read, the CLI does the identical job for roughly **¼–½ the
tokens**, because connecting the server forces all 16 tool schemas into every request
whether you use them or not. And every **write** has no MCP path at all.

---

## 1. Tokens to do one task (N1) — measured

Task **N1 — "list all workspaces and the location each belongs to,"** run both ways:

| What loads to complete the task | MCP path | wxcli path |
|---|---:|---:|
| Tool documentation to make the calls | **9,894** (all 16 schemas — measured) | **818** (`workspaces list --help` 620 + `locations list --help` 198 — measured) |
| Skill to know what to run | 0 *(schemas self-document; a read needs none)* | **2,151** (`query-live` — measured) |
| Call payloads | ~60 | ~25 |
| Results returned | ~1,800 *(est. — SIMPLE output, comparable to CLI)* | 2,103 *(measured: 733 + 1,370)* |
| Implementation (Python / server) | 0 *(server-side)* | 0 *(subprocess)* |
| **TOTAL** | **~11,750** | **~5,100** |

The multiple is driven by the **measured** documentation term (9,894 vs 818); results are a
wash (~2k either way). **~2.3×** as shown (CLI charged its skill, MCP given a free pass);
**~4×** under "MCP + skills" where skills cancel and only the documentation term remains.
The CLI wins on reads either way.

The gap is **structural**:
- Connecting the MCP server loads **all 16 schemas into every request** — you cannot subset
  to the two you need. The two search tools' filter-DSL descriptions alone are 3,049 tokens.
- The CLI is *also* self-documenting, but loads docs **only for the commands it touches** —
  818 for the two used here, nothing for the other 171 command groups. `--help` is rendered
  at runtime by Typer from the command's decorators; the `.py` implementation never enters
  context.

### Reuse across many commands — fixed vs. incremental

Documentation is **loaded once and reused** for the rest of the session on *both* sides (it
persists in context; with prompt caching it isn't re-billed per turn, though it occupies the
window). So the multi-command picture is fixed vs. incremental:

- **MCP — fixed.** All 16 schemas (9,894) load once, reused at **0 additional cost** — but
  capped at those 16 read-only tools.
- **CLI — incremental.** Each *new distinct* command's `--help` loads once (~500), then is
  reused; repeat calls cost **0**. New commands accrue ~500 apiece, across 173 groups, uncapped.

**Crossover ≈ 16–20 distinct commands.** Focused sessions (1–5 commands — most tasks) → the
CLI is far cheaper. A broad read sweep using most of MCP's 16 tools → the two **converge
toward parity** within that scope (concede this). The eager tax scales with **total surface**
while JIT stays **flat per task**, so the gap only widens as the surface grows.

---

## 2. Capability — what each can do

**MCP: 16 tools, all read-only** — search / metrics / diff / lifecycle across devices,
workspaces, and locations. No create, update, or delete, for anything.

**wxcli: full CRUD across 173 command groups.** The same three domains are
list/create/show/update/delete; the surface also spans calling, admin, messaging, meetings,
and contact center. Live this session, wxcli created a workspace, verified it, deleted it
(`workspaces create` → `delete --force`), and confirmed removal (404) — a write round-trip
the MCP server cannot perform at all.

For the work this playbook exists to do — provisioning, feature config, routing, migration —
there is **no MCP path**.

---

## Bottom line

- **Reads cost ~2.3–4× less via the CLI** for focused sessions, converging toward parity
  only for a broad sweep within MCP's 16 read-only tools. Driver: eager-load all 16 schemas
  (9,894) vs JIT one command's `--help` (818).
- **Writes have no MCP comparison** — the server is read-only; the CLI does the whole surface.
- **Architecture: CLI as the execution layer, MCP as a thin doorway.** Wrap the CLI behind
  one "run a wxcli command" tool and any MCP agent drives the full surface — without
  eager-loading the entire tool set every turn.
