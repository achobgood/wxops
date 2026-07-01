# Refactor Plan — Coherence Audit Phase 5

Dependency-ordered execution plan for the target architecture
(`docs/arch/target-architecture.md`). Each step: files touched, risk, rollback,
**M**echanical vs **J**udgment. Steps that touch the generator or `field_overrides.yaml` are
marked **⚠ GENERATOR RIPPLE** — their output ripples across all 185 generated groups and must be
reviewed as a regen diff, not per-file.

Dependency spine:
```
S0.1 session layer ──► S2.1 spec sync ──► S4.1 skills sweep ──► S4.5 gate enforcing
S0.2 drift gate (report-only) ──┘              │
S1.1 registration manifest ──► S2.1            └─► S4.2 CLAUDE.md/README updates
S1.2 field_overrides changes ──► S2.1
S0.3 orphan deletion (independent)             S3.x consolidations (after S2.1)
```

---

## Group 1 — SAFE NOW (no behavior change for any existing consumer)

### S0.1 Complete the session contract
- **What:** Add `rest_patch` (with `content_type` support) to `WebexSession`; add optional
  `status_code` + parsed body to `WebexError` (message-first constructor unchanged — existing
  `WebexError(response.text)` call sites stay valid); add bounded 429/Retry-After retry + single
  connect-error retry in the session.
- **Files:** `src/wxcli/auth.py`, `src/wxcli/errors.py`, tests.
- **Risk:** Low. Fixes a hard crash (F1); retry default is the only judgment call (bounded, logged,
  env-var opt-out for scripted contexts).
- **Rollback:** revert commit; no callers change signature.
- **Tag:** M (patch/error fields) + J (retry policy). **Must land before S2.1** so regenerated
  PATCH commands are born working. Live-verify one PATCH command after
  (`device-configurations update` per `feedback_live_test_writes`).

### S0.2 Drift gate, report-only
- **What:** Port the Phase 1 extractor into `tools/drift_check.py`: (1) spec↔CLI parity,
  (2) `wxcli` reference existence across `.claude/**`, `CLAUDE.md`, `README.md` (fenced-code scan),
  (3) published-count check, (4) unreferenced-group-vs-declared-list check. Wire as advisory
  pre-commit/CI output.
- **Files:** `tools/drift_check.py` (new), CI config.
- **Risk:** None (report-only). **Rollback:** delete file. **Tag:** M.

### S0.3 Delete the 29 fully-superseded orphan modules
- **What:** `git rm` the 29 modules listed in `coherence-map.md` §3.2 (unreachable from the CLI;
  path-level supersession verified). Spot live-test 3 registered replacement families
  (location-settings, workspace-settings, scim-users) to validate the supersession claim
  behaviorally (guards F10-adjacent capabilities; not a precondition for deletion — orphans are
  dead code either way).
- **Files:** 29 files under `src/wxcli/commands/`.
- **Risk:** Low (nothing imports them — verified). **Rollback:** git revert restores files.
- **Tag:** M (deletion) + J (live-test review).
- **Note:** do NOT delete `wholesale_*`, `user_call_settings`, `hot_desking_members`,
  `ucm_profile` here — they carry unique coverage handled in S2.1.

### S0.4 Archive the wxcadm doc family
- **What:** Move 8 docs (`wxcadm-core/person/locations/features/devices-workspaces/routing/advanced`,
  `wxc-sdk-patterns`) to `docs/reference/archive/`; keep `wxcadm-xsi-realtime.md` in place
  (call-control depends on it); replace their CLAUDE.md file-map rows with one archive pointer.
- **Files:** 8 doc moves, `CLAUDE.md`.
- **Risk:** Low; no skill cites the moved docs (verified §5.3/F8). **Rollback:** move back.
- **Tag:** M.

---

## Group 2 — NEEDS REVIEW (structural; correct by design but review the diffs)

### S1.1 Generator-owned registration manifest ⚠ GENERATOR RIPPLE
- **What:** `generate_commands.py` emits `src/wxcli/commands/_registry.py` (literal
  `(module, group)` lines); `main.py` replaces ~170 generated-group registration blocks with the
  manifest loop; keeps explicit blocks for hand-written seams, aliases (`users`, `cx-essentials`),
  and the guarded `fs_*` dev block. Dev-only specs excluded from the manifest (`--dev-only` flag).
- **Files:** `tools/generate_commands.py`, `src/wxcli/main.py`, `src/wxcli/commands/_registry.py` (new).
- **Risk:** Medium — touches startup path of every group. Verify: `wxcli --help` group list
  identical before/after (mechanical diff of group names), fresh-clone smoke test without fs files.
- **Rollback:** revert; old main.py blocks live in git.
- **Tag:** J (design) + M (verification).

### S1.2 `field_overrides.yaml` additions ⚠ GENERATOR RIPPLE
- **What:** (a) `cli_name_overrides`: meeting-messages tag → `meeting-messages` (frees the
  `messages` name — see S3.2 breaking note); (b) new `keep_endpoints` override for CLI-ahead-of-spec
  endpoints worth keeping (decide per-endpoint for the 13 CC entries at S2.1 review);
  (c) reason comments on every `skip_tags` entry; explicit skips + comments for CC `Functions`
  (until colon-path support) and the flow-store-embedded CC tags (Activities/Templates/Events);
  (d) generated `docs/arch/deliberate-gaps.md` emission.
- **Files:** `tools/field_overrides.yaml`, `tools/generate_commands.py`.
- **Risk:** Medium — YAML mistakes ripple into every regen. Review as regen diff at S2.1.
- **Rollback:** revert YAML; regen restores prior output.
- **Tag:** J.

### S2.1 First atomic spec sync (the big one) ⚠ GENERATOR RIPPLE
- **What:** `make spec-sync`: `tools/update-specs.py` → full regen (all tracked specs) →
  manifest → drift gate report → single commit. Expected resolution: 57 stale ops appear
  (queue-DNIS ×13, cc-flows ×10, my-call-settings ×7, agent-greetings ×6, recording announcements
  ×4, cc-agents ×4, identity-org ×2 incl. the PATCH ops, …); messaging `Messages` group generated;
  `user_call_settings`-unique + `hot_desking_members` endpoints land in current-generation modules
  (verify tag mapping in regen diff, then delete those 2 orphan files); `wholesale-provisioning`,
  `wholesale-billing-reports`, `ucm-profile` registered via manifest; 13 CLI-ahead CC commands
  either drop or persist via `keep_endpoints` (per-endpoint decision at review).
- **Files:** `specs/*.json`, mass diff under `src/wxcli/commands/`, `_registry.py`.
- **Depends on:** S0.1 (PATCH), S1.1, S1.2.
- **Risk:** Medium-high by size, low by kind (regen is the designed operation; ADR-1). Review =
  group-list diff + spot `--help` diffs + live smoke of one new command family (queue DNIS).
- **Rollback:** revert the single sync commit.
- **Tag:** M (output) + J (review, keep_endpoints decisions).

### S4.1 Skills & agent reference sweep (after S2.1 — names must be final)
- **What:** Fix all ~45 dead references (coherence-map §5) across 14 skills to
  post-regen names; fix builder-agent worked example (`wxc-calling-builder.md:391`) to the real
  location-calling enable flow — dead-command corrections only, no structural edits (critique R6).
  Two judgment items: `customer-assist` queue recording (live-verify the CX path — call-queue
  `--has-cx-essentials` — before rewriting; if no API path exists, mark capability unavailable),
  `manage-call-settings` simultaneous ring (cite the newly generated commands).
- **Files:** 14 `SKILL.md`s (+ `query-live/domains/routing.md`), `wxc-calling-builder.md`.
- **Risk:** Low-medium (skill text; per-skill review). **Rollback:** per-file revert.
- **Tag:** M (rename fixes, gate-verified) + J (2 capability items).

### S4.2 CLAUDE.md / README truth sweep
- **What:** Counts (groups/commands/specs) regenerated mechanically; spec file-map completed
  (10 tracked specs); taxonomy diff applied (target-architecture §B1/B2 rows, §B3 out-of-scope
  list); hot-desking row nuance; ADR-1 count refresh + "registration is manual" gotcha retired;
  ADR amendment or new ADR-9 documenting spec-sync + drift gate + registration manifest;
  `docs/architecture/01-structural-map.md` + `04-operations-and-evolution.md` updated for
  `_registry.py` and the sync workflow (per the Architecture Docs Rule, same session as S1/S2).
- **Files:** `CLAUDE.md`, `README.md`, `docs/architecture/{01,02,04}-*.md`.
- **Risk:** Low. **Rollback:** revert. **Tag:** M (counts) + J (taxonomy rows, ADR).

### S4.5 Flip the drift gate to enforcing
- **What:** Once S2.1 + S4.1 + S4.2 leave the gate clean, make checks 1-4 blocking in CI.
- **Risk:** None functional; process change. **Tag:** M. **Depends on:** everything above.

### S1.3 (optional, defer-able) Colon-action path support ⚠ GENERATOR RIPPLE
- **What:** Teach `openapi_parser.py`/`command_renderer.py` to render `/functions/{id}:publish`
  style paths → unlocks CC `Functions` (11 ops). Until then the explicit skip (S1.2c) keeps the
  gap deliberate.
- **Risk:** Medium (parser change affects all specs — regression-test regen diff must be
  functions-only). **Tag:** J.

---

## Group 3 — BREAKING — FLAG BEFORE TOUCHING

### S3.1 `licenses` consolidation (breaking rename with alias)
- **What:** Retire hand-written `licenses.py` (ADR-1 "legacy"); rename generated `licenses-api` →
  `licenses` via `cli_name_overrides`; register alias `licenses-api` → same module for one release
  (the `users`→`people` pattern).
- **Preconditions (blocking):** flag-compatibility diff between hand `licenses` commands
  (`list/show/update`) and generated equivalents; **live-verify** the generated update path —
  operator memory records a broken PATCH-style update here; current `licenses_api.py` does not
  call `rest_patch` (verified), but the fix must be proven against a live org before the hand
  module is deleted.
- **Files:** `src/wxcli/commands/licenses.py` (delete), `field_overrides.yaml`, `main.py` (alias),
  `manage-licensing`/`provision-calling` SKILL.mds.
- **Risk:** Medium-high — license assignment is an offboarding/provisioning hot path.
- **Rollback:** revert; hand module restored.
- **Tag:** J. Migration engine verified unaffected (API-direct, critique R1).

### S3.2 `messages` name reclaim (breaking, no alias possible)
- **What:** Lands mechanically inside S1.2+S2.1 but is a **behavioral break**: `wxcli messages`
  stops meaning meeting-messages (1 command, `delete`) and becomes the core messaging group.
  Measured in-repo consumers of the old name: zero. Flagging because external muscle
  memory/scripts can't be measured from the repo.
- **Tag:** J (approve the break) → then M.

### S3.3 `locations` / `numbers` migration — explicitly DEFERRED
- **What:** Stay hand-written under the ADR-1 charter with a dated comment. Revisit only with a
  flag-compatibility diff + live bulk-provisioning test (critique R4: these are the bulk
  provisioning and number-management hot paths; breaking them costs more than the duplication
  risk, and no generated twin is currently registered).
- **Tag:** J (the deferral is the decision).

### S3.4 Wholesale exposure (mild, included in S2.1 — flag only)
- Registering wholesale groups exposes commands that 403 for non-wholesale-partner tokens — same
  posture as the already-registered `broadworks-*` groups. Declared out-of-skill-scope (§B3).
  Approve as part of S2.1 review.

---

## Sequencing summary

| Order | Step | Group | Generator/YAML ripple |
|---|---|---|---|
| 1 | S0.1 session contract | safe | no |
| 2 | S0.2 drift gate (report) | safe | no |
| 3 | S0.3 orphan deletion | safe | no |
| 4 | S0.4 wxcadm archive | safe | no |
| 5 | S1.1 registration manifest | review | **yes** |
| 6 | S1.2 field_overrides additions | review | **yes** |
| 7 | S2.1 atomic spec sync (carries S3.2, S3.4 — flagged) | review + flagged breaks | **yes** |
| 8 | S4.1 skills/agent sweep | review | no |
| 9 | S4.2 CLAUDE.md/README/arch-docs sweep | review | no |
| 10 | S3.1 licenses consolidation | breaking | yes (name override) |
| 11 | S4.5 gate → enforcing | review | no |
| — | S1.3 colon-paths | optional | **yes** |
| — | S3.3 locations/numbers | deferred | — |

Steps 1-4 are independent of each other and can land in any order; everything else follows the
spine. Each step is one commit (S2.1 exactly one), each with a stated rollback.
