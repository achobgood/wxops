# docs/

Documentation hub for the Webex Calling Playbook project. Subdirectories each have their own CLAUDE.md with local context.

## Subdirectories

| Path | Contents |
|------|----------|
| `reference/` | Webex API reference docs — grounded in wxc_sdk, wxcadm source, and OpenAPI specs |
| `plans/` | Migration design specs and build planning for the CUCM-to-Webex migration tool |
| `prompts/` | Design and build execution prompts that drive Claude Code sessions |
| `templates/` | Report templates (deployment plan, execution report) used by the builder agent |
| `superpowers/` | Superpowers plans and specs (separate from CUCM migration work) |
| `later/` | Parked items not currently active |

## How They Work Together

```
reference/  ──informs──>  plans/  ──informs──>  prompts/
   (API surface)        (design specs)      (build instructions)
```

- **Reference docs** document every API surface (methods, scopes, gotchas, raw HTTP).
- **Plans** use reference docs to design migration architecture and build strategies.
- **Prompts** encode the plans into structured instructions that drive build sessions.
- **Templates** standardize the output of builder agent runs.

## Key Entry Points

- **Master project status:** `plans/cucm-migration-roadmap.md` — what's done, what's ready, what's next
- **Pipeline architecture:** `plans/cucm-pipeline-architecture.md` — authoritative design (§3 and §7 marked BUILT)
- **Detailed pipeline docs:** `plans/cucm-pipeline/01-07 + 03b` — 8 architecture deep-dives (all implemented in Phases 01-11)
- **Migration execution:** Use `/cucm-migrate` skill after running `wxcli cucm discover` through `wxcli cucm export`. All 11 build phases complete, 1507 tests passing.
- **Build prompts (all executed):** `prompts/phase-01-foundation.md` through `prompts/phase-11-cucm-migrate-skill.md`

## Root Files

- `wxc-pipeline-visual.html` — Interactive pipeline visualization
