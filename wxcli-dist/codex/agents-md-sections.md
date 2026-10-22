<!-- @section: ## Quick Start -->
## Quick Start

Ask Codex to use the **wxops** agent for every job that changes or
audits the org: it authenticates, interviews you, plans, runs `wxcli` and
verifies the result.

- Contact Center flows, Webex Connect flows, AI agents: the agent starts with the
  `design-ai-agent` skill, then runs the WxCC skills in the order § Routing Table gives.
- CUCM migration: ask it to "run a CUCM migration" (`.claude/rules/cucm-migration.md`).
- Debugging: the `wxc-calling-debug` skill (Calling) or the `wxcc-debug` skill (AI agent actions).
- Read-only questions about the live org: the `query-live` skill. Org health: "audit my org".

If this file ends mid-sentence, this folder is not trusted in Codex: run `codex` here
and accept the trust prompt, then start again. The safety lock runs only after you
trust this folder's hooks on Codex's start screen.

<!-- @section: ### Agent Invocation Pattern -->
### Agent Invocation Pattern

Codex orchestrates subagents itself — it spawns them, routes follow-up
instructions, waits for results, and closes agent threads. There is no manual
message-passing.

- One agent per job: ask Codex to use the **wxops** agent
  (`.codex/agents/wxops.toml`) and describe the job. Refine it with
  follow-up instructions in the same session ("also add voicemail to that user").
  Give unrelated jobs separate agents; keep dependent steps in one agent.
- CUCM migration is the one exception: a fresh agent per phase, one phase at a
  time, because a whole migration outgrows one agent's context.
- For CUCM migration advisory and decision review, ask Codex to use the
  **migration-advisor** agent (`.codex/agents/migration-advisor.toml`).

<!-- @section: ### Agent Model Selection -->
### Agent Model Selection

Codex agents inherit the session model; task complexity maps to reasoning
effort, set per agent via `model_reasoning_effort` in its TOML: cleanup /
read-only checks → `low`; standard provisioning and feature config → `medium`;
WxCC builds, multi-phase CUCM migration and architectural decisions → `high`.
The migration-advisor runs at `high`; the builder at `medium`.

<!-- @section: ### Inline IDs in Commands -->
### Inline IDs in Commands

Inline resource IDs directly as `wxcli` arguments; never put multi-line shell
variable assignments before a `wxcli` command.

<!-- @section: ### Agent Orchestration — Long-Running Work & Silence Detection -->
### Agent Orchestration — Long-Running Work

Codex manages subagent lifecycle and result collection, so no manual
silence-detection or transcript-inspection protocol is needed. For
long-running commands (e.g. `wxcli cucm execute`), run them and let Codex await
completion; when a command must run outside the sandbox, Codex escalates for
your approval. Always verify final state with `wxcli` read commands rather than
trusting a single command's self-reported result.
