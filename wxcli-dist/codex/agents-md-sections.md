<!-- @section: ### Agent Invocation Pattern -->
### Agent Invocation Pattern

Codex orchestrates subagents itself — it spawns them, routes follow-up
instructions, waits for results, and closes agent threads. There is no
phase-per-invocation requirement and no manual message-passing.

- To build/configure/tear down: ask Codex to use the **wxc-calling-builder**
  agent (defined in `.codex/agents/wxc-calling-builder.toml`), describing what
  you want. Codex sequences multi-step work (auth → provisioning → feature
  config) within the turn and keeps context; refine conversationally ("also add
  voicemail to that user").
- For CUCM migration advisory and decision review, ask Codex to use the
  **migration-advisor** agent (`.codex/agents/migration-advisor.toml`).

<!-- @section: ### Agent Model Selection -->
### Agent Model Selection

Codex agents inherit the session model; task complexity maps to reasoning
effort, set per agent via `model_reasoning_effort` in its TOML: cleanup /
read-only checks → `low`; standard provisioning and feature config → `medium`;
multi-phase CUCM migration and architectural decisions → `high`. The
migration-advisor runs at `high`; the builder at `medium`.

<!-- @section: ### Agent Orchestration — Long-Running Work & Silence Detection -->
### Agent Orchestration — Long-Running Work

Codex manages subagent lifecycle and result collection, so no manual
silence-detection or transcript-inspection protocol is needed. For
long-running commands (e.g. `wxcli cucm execute`), run them and let Codex await
completion; when a command must run outside the sandbox, Codex escalates for
your approval. Always verify final state with `wxcli` read commands rather than
trusting a single command's self-reported result.
