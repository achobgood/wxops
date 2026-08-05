# What Makes It Different — Grounded, and Far Cheaper

Two properties separate wxops from a generic "AI + API" wrapper: it is **engineered so the AI cannot hallucinate**, and it is **structurally cheaper to run** than the obvious alternative.

## Differentiator 1 — Mandatory grounding (it can't make things up)

The playbook's first rule is absolute: **never answer any question about Webex from training data alone.** For every question — capability, configuration, behavior, limit — the agent must either invoke the relevant skill or read the relevant reference doc. The docs and skills are the authoritative source.

Why this rule exists: training data about Cisco/Webex is unreliable. Product tiers get conflated, feature names change, and capabilities vary by license. So the agent is forced to a source of truth at every step, and it grounds in a strict priority order:

1. **Curated knowledge-base / reference docs** (highest authority)
2. **Deterministic tool output** (static rules, `--help`, live API reads)
3. **The model's own training** (last resort)

If it can't answer from any of those, **it says so explicitly rather than filling the gap.** Honest "I don't know" is a designed behavior, not a failure. This is what makes the platform safe to point at a production org.

## Differentiator 2 — A CLI beats an MCP server, measured

The natural question for an agent tool is "why not expose the API as MCP tools?" wxops deliberately does not — and the reason is measurable.

**A single, ordinary read task, run both ways** (list all workspaces and each one's location):

| | Cisco's official Webex MCP server | wxops CLI |
|---|---|---|
| Total tokens for the task | **~11,750** | **~5,100** (**≈2.3–4× cheaper**) |
| Documentation loaded | **9,894** — all 16 tool schemas, forced into context | **818** — only the two commands actually used |
| Operations exposed | **16, all read-only** | Full CRUD across **179 command groups** |
| Can it write (provision / configure / migrate)? | **No** | **Yes** |
| Schema load model | All schemas **eagerly, every turn** | One command's `--help`, **just-in-time** |

The gap is **structural, not incidental**:

- **Connecting the MCP server loads all 16 tool schemas into every request** — you can't subset to the two you need. The two search tools' filter descriptions alone are ~3,000 tokens.
- **The CLI is also self-documenting, but loads docs only for the commands it touches** — 818 tokens for the two used here, nothing for the other 177 groups. The eager tax scales with *total surface*; just-in-time stays *flat per task*. So the gap only widens as the surface grows.
- **Tool-selection accuracy collapses well before hundreds of tools.** Models reliably pick from a handful, not a sea of overloaded near-duplicates. The skill layer disambiguates intent; a flat tool list just hands the model the ambiguity.

And every **write** — provisioning, feature config, routing, migration — has **no MCP path at all**. In the same measured session, wxcli created a workspace, verified it, and deleted it: a round-trip the read-only MCP server cannot perform.

## The architectural stance — not anti-MCP

This isn't a rejection of MCP; it's putting it in the right place. **The CLI is the execution layer; MCP is a thin doorway.** To let any agent platform drive wxops, you wrap the CLI behind **one** small "run a wxcli command" tool — not several hundred eager-loaded tool definitions. You get the host integration without paying the tool-explosion tax, and the full surface stays reachable.
