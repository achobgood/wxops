# The Hero Use Case & Why It Wins

## Automated CUCM-to-Webex migration

The platform's flagship capability is migrating a legacy **Cisco Unified Communications Manager (CUCM)** phone system to Webex Calling — one of the hardest, most manual jobs in enterprise collaboration — as an **11-phase, data-driven pipeline**:

```
discover → normalize → map → analyze → decisions → plan → preflight → export → execute
```

It connects to a live CUCM cluster over AXL, extracts the full deployment, normalizes it into canonical models, maps every CUCM object to its Webex Calling equivalent, and surfaces the decisions that genuinely need a human — all backed by a SQLite store with a complete audit journal.

### Two agents, two roles

| Agent | Model | Role |
|---|---|---|
| **wxc-calling-builder** | Sonnet | Runs the pipeline, executes commands, orchestrates the workflow |
| **migration-advisor** | Opus | Reads every decision, applies CCIE-level architectural reasoning, writes the narrative, and flags dissents |

The advisor is grounded in an **8-document migration knowledge base** and works in two layers: per-decision recommendation rules (one per decision type — and honest "this is genuinely ambiguous" when the data doesn't support a call), plus cross-cutting advisory patterns that catch the multi-object issues a CCIE would spot but no single rule can — partition-ordering loss, CPN transformation chains, over-engineered dial plans to eliminate, hunt pilots that should become call queues.

### Dissent analysis — the AI can disagree with the rules

When the static heuristics say one thing but the architectural context suggests another, the advisor raises a **structured dissent** — citing which knowledge-base section informs its reasoning, which heuristic it disagrees with, and why. Dissents are shown to the admin during review so they make **informed** choices, not blind ones. If the advisor is unavailable, the pipeline falls back to the deterministic rules — the backbone is always tested and fast.

### The assessment report — a sales instrument

After analysis, the pipeline generates a professional **HTML/PDF assessment report** in the "Authority Minimal" design system: a **0–100 complexity score** from seven weighted factors, an environment inventory with charts, effort bands (auto / planning / manual), and a full technical appendix explaining every decision in customer-friendly language.

Its strategic purpose is blunt: **stop customers from defaulting to Microsoft Teams** by demystifying the CUCM-to-Webex path with data-backed evidence — turning the opaque "how hard is this migration?" question into a scored, explained, actionable document grounded in the customer's real inventory.

## Org health assessment

A second standalone deliverable: a deterministic, three-phase audit (collect → analyze → report) that runs **18 checks across four categories** and produces a branded, self-contained HTML report.

| Category | Catches |
|---|---|
| **Security posture** | Toll-fraud-prone AA external transfers, queues without recording, unrestricted international dialing, missing outgoing-permission rules |
| **Routing hygiene** | Dial plans with no route choices, orphaned route groups/lists, trunks in error state |
| **Feature utilization** | Disabled AAs, understaffed queues, single-member hunt groups, empty voicemail/paging groups, unused call parks |
| **Device health** | Offline devices, users at the 5-device limit, unassigned devices, workspaces without devices, stale activation codes |

Every check is **deterministic Python code, not LLM analysis** — the report is reproducible and defensible.

## Proof it's real

- **Thousands of automated tests** across the platform — **over 2,700 in the migration engine alone**.
- A **561-operation migration stress test completes in ~90 seconds** via the async concurrent execution engine, which handles 409 auto-recovery (existing resources) and cascade-skip (failed dependencies).
- **Live-verified writes**: create → verify → delete round-trips run against a real org, not mocks.

## Why it wins the hackathon

- **It solves a real, expensive, painful problem** — configuring and migrating Webex at scale — end to end, not as a demo.
- **It's a novel architecture for agent-driven ops**: a three-layer design (docs + skills + tested CLI) that makes an LLM safe to point at production, backed by a **measured** argument that a CLI beats an MCP tool surface by 2.3–4× on tokens while adding full write capability.
- **It's genuinely broad and genuinely deep**: 179 command groups across six API domains *and* a CCIE-grade migration advisor with dissent analysis.
- **It produces customer-facing business value** — assessment reports and health audits that Sales Engineers hand to customers to win deals and prevent churn.
