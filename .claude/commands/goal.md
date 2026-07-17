---
description: Turn a rough request into a structured, well-specified goal brief before work starts
argument-hint: <one-line description of what you want done>
---

# /goal — structured goal brief

You have been handed a rough request to work on **this repository** (the Webex
Calling Playbook — skills, agents, `wxcli` CLI, reference docs, migration tooling).
Before touching anything, restate it as the five-field brief below, then confirm.

The raw request:

> $ARGUMENTS

## Step 1 — Draft the brief

Fill in every field. Infer sensible values from the request and the codebase;
where the request is genuinely ambiguous, write `⚠ NEEDS INPUT:` and a specific
question rather than guessing. Keep each field to 1–3 lines.

- **TASK** — What to do, concretely. Name the actual files, skills, agents, or
  CLI groups involved (e.g. "add a `NOT for:` line to `configure-features/SKILL.md`").
- **WHY** — Why it matters / who it's for. If this fixes a correction the user
  made, say so — it should become a feedback memory (see CONSTRAINTS).
- **OUTCOME** — The exact finished state. What will exist, change, or be
  verifiable when done. Prefer observable results ("`wxcli x --help` lists the
  new command") over intentions ("the command is added").
- **CONSTRAINTS** — What must / must not happen. Start from the project's
  standing rules below and add task-specific ones:
  - Never answer Webex questions from training data — ground in skills or
    `docs/reference/`. **`wxcli <cmd> --help` outranks skills, which outrank
    reference docs, which outrank training.** If a recipe and `--help` disagree,
    fix the recipe.
  - Discovery-first: one broad query, evaluate, stop within 3 commands; accept a
    negative result instead of hunting for a positive. But confirm the query
    *could* have returned a positive (e.g. `--calling-data true`) before reporting
    "none found".
  - User-facing text follows the Plain-English rule: lead with the plain decision,
    replace jargon with concrete before/after, end with a recommendation.
  - If a new/renamed CLI group is involved, keep the drift-gate happy — route it
    in a skill or justify it in the Out-of-Scope table (never backtick a group
    name in a *reason*).
  - Don't push to any branch other than the designated one; don't open a PR
    unless explicitly asked.
  - After any user correction, save a feedback memory capturing the pattern.
- **VERIFICATION** — How you'll prove the OUTCOME is real, not inferred. Be
  specific: the exact command to run and expected output, the file+line to read
  back, the gate/test to pass. "Verify before claiming done — would a staff
  engineer approve this?"

## Step 2 — Resolve and route

- If any field has `⚠ NEEDS INPUT`, ask those questions now (use `AskUserQuestion`
  for choices) before doing work.
- Identify the right execution path: a specific **skill**, the
  **wxc-calling-builder agent** (fresh invocation per phase), or direct edits for
  repo/docs changes. State which and why in one line.

## Step 3 — Confirm, then execute

Show the completed brief, state the execution path, and proceed once it's
unambiguous. Then do the work and close by walking through the VERIFICATION
field with real output — not a claim that it's done.
