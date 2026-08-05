# How It Works — From Plain English to Verified Config

The builder agent runs a five-phase pipeline. Everything before the approval gate is just conversation and read-only discovery; nothing touches your org until you say go.

```
Setup  →  Interview  →  Design  →  [APPROVAL GATE]  →  Execute  →  Verify  →  Report
```

## Phase 1 — Setup

The agent confirms `wxcli` is installed and validates your token with `wxcli whoami`. A stale or missing token is the #1 reason builds fail, so it is checked first and fixed interactively. For partner tokens, the agent detects the target org and **hard-stops for confirmation** before anything runs.

## Phase 2 — Interview

The agent asks questions **one at a time** — "What do you want to build?" then "At what scope?" — and listens for domain signals to decide which of the 24 skills to load. It then runs **live prerequisite checks** against your org (do the locations exist and have calling enabled? are there enough licenses? are any extensions already in use?) and gathers constraints: naming conventions, extension ranges, schedules, compliance rules.

## Phase 3 — Design

The agent loads the relevant reference docs and writes a complete, executable **deployment plan** with seven sections: objective, prerequisites, **real resource IDs from the live org (never placeholders)**, dependency-ordered execution steps, a rollback plan, verification steps, and an execution estimate. The plan is saved to disk — so if the agent's context compacts mid-build, it re-reads the plan and resumes.

Dependency ordering is explicit and enforced. For example:

- Location (calling-enabled) → any location-scoped resource
- Schedules → auto attendants and call queues
- Users (with a calling license) → hunt-group/queue agents
- Trunks → route groups → route lists → dial plans

## The Approval Gate — the one hard stop

The agent presents the full plan and **waits**. It will not execute a single write until you explicitly approve. Even "just do it" gets a plan shown first — this is non-negotiable. Everything before the gate is reversible; everything after modifies your Webex org.

## Phase 4 — Execute

Before running a domain's commands, the agent **reads that domain's skill file** for the exact command mappings, prerequisites, and gotchas that prevent trial-and-error failures. Commands then run **sequentially in dependency order**, with output captured and progress reported in real time. On any error the agent **stops immediately**, shows the full error, diagnoses it against known patterns (401 = token, 403 = scope, 409 = conflict, 400 = bad params), and offers three choices: fix and retry, skip, or roll back.

## Phase 5 — Verify

Every resource the agent created is **read back from the API** with a `show` command and compared to the plan — names, extensions, agent lists, schedule associations, phone numbers, settings values. Discrepancies are flagged. Then the agent writes an **execution report** saved alongside the plan, giving every build a complete audit trail.

## One request, traced

*"Add a sales hunt group for the Denver office"*

1. The agent routes to the **`configure-features`** skill — not contact-center, not customer-assist (the disambiguation map handles the overloaded word "queue").
2. The skill loads `call-features-major.md` for ground truth, then checks prerequisites in order: location exists → calling-enabled → users exist → numbers available.
3. Before building the command it runs `wxcli hunt-group create --help` — the CLI is the final source of truth for flags, never the docs or memory.
4. The CLI executes; a verify step reads the result back to confirm.

At every step the agent is forced back to an authoritative source: data model from the doc, flags from `--help`, final state from a read-back. **It never operates on memory.**

## Standalone workflows

Beyond guided builds, the same platform runs three read-only or specialized modes on demand:

- **Query live state** — ask plain-English questions ("Which users at Austin don't have voicemail?", "What happens when someone calls +1-512-555-1000?"). Read-only is enforced: only `list`, `show`, and `test` verbs are allowed; create/update/delete are blocklisted.
- **Org health assessment** — a three-phase audit (collect → analyze → report) running 18 deterministic checks; see doc 05.
- **CUCM migration** — the full legacy-to-Webex pipeline; see doc 05.

## Built-in resilience

The playbook anticipates how builds fail and recovers: token expiry mid-build (re-auth and resume from the last step), scope gaps, duplicate resources (409 — never silently duplicated), missing prerequisites, rate limiting, partial bulk failures, and context compaction (the on-disk plan is the recovery anchor). When a build discovers a new API gotcha, it writes it back into the reference docs — so the playbook gets smarter every session.
