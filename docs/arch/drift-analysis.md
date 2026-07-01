# Drift & Gap Analysis — Ranked by Blast Radius × Effort

**Phase 2 of the architectural coherence audit.** Inputs: `docs/arch/coherence-map.md` (+ data
JSON). Every finding cites repo evidence. Ranking: `blast radius` = how much of the system a
defect can mislead or break (breadth × how load-bearing) vs `effort` = cost to fix safely.
Findings ordered by leverage (high blast, low-to-moderate effort first).

## Executive ranking

| # | Finding | Category | Blast radius | Effort | Leverage |
|---|---------|----------|--------------|--------|----------|
| F1 | `rest_patch` doesn't exist in the session; generator emits calls to it | Seam | All PATCH commands crash (5 registered modules, incl. device-platform's core write) | Trivial | ★★★★★ |
| F2 | Spec-refresh ↛ regeneration: no coupling, 57 stale ops, 13 CLI-ahead commands | Process/seam | Trust in the entire generated surface | Small (regen) + process | ★★★★★ |
| F3 | ~45 dead command/group refs across 14 skills + builder agent; no existence check | Taxonomy/process | Skills layer routinely instructs nonexistent commands | Small-medium (mechanical fixes + CI gate) | ★★★★★ |
| F4 | Manual registration seam: 34 orphaned generated modules, 5 with unique coverage (incl. wholesale) | Seam | Dead code shipped; 30 spec ops silently unreachable | Small (decisions + deletions) | ★★★★ |
| F5 | Core messaging `/messages` has no CLI while 2 skills teach it | Coverage | messaging-spaces/bots core workflow is fiction | Small (regen tag + register) | ★★★★ |
| F6 | No shared retry/backoff/429 handling in `WebexSession` | Seam | Every bulk workflow (cleanup, org-health, migration execute, agent swarms) | Medium | ★★★ |
| F7 | `licenses` vs `licenses-api` duplicate groups; ADR-1 calls hand trio "legacy" | Seam/redundancy | License workflows split across 2 surfaces; skills reference both | Medium (consolidation) | ★★★ |
| F8 | 8 `wxcadm-*` docs + `wxc-sdk-patterns.md` have zero skill consumers (1 exception) | Redundancy | Context pollution; Mandatory Grounding Rule points at non-executable paths | Small | ★★★ |
| F9 | Published counts stale everywhere (CLAUDE.md, README, ADR-1) | Doc drift | Trust erosion; agents plan against wrong surface | Trivial | ★★★ |
| F10 | Capability holes behind skill claims: person-level `simultaneousRing`, hot-desk members, CX queue recording | Coverage/taxonomy | 3 skills advertise things the CLI can't do | Medium (regen/register + skill edits) | ★★★ |
| F11 | `WebexError` is a bare string; tips rely on substring matching | Seam | Error UX fragility; wrong tips possible | Small | ★★ |
| F12 | 22 "suspicious" unreferenced groups (emergency-services, announcements, virtual-line-settings, mode-management…) | Taxonomy | Real admin surface invisible to the skills layer | Medium (scope decisions) | ★★ |
| F13 | CC spec churn artifacts: colon-action paths (Functions), flow-store paths embedded in CC spec | Coverage | 17 CC ops ungeneratable/misplaced | Medium (generator support + skip decisions) | ★★ |
| F14 | CLAUDE.md taxonomy rows route to capabilities that don't exist as described | Taxonomy | Disambiguation table misroutes | Small | ★★ |

---

## (a) Seam inconsistencies

### F1 — PATCH is broken at the session seam ★★★★★
`src/wxcli/auth.py` defines `rest_get/put/post/delete` only. The generator emits
`api.session.rest_patch(...)` in: `cc_tasks.py:120`, `identity_org.py:57`,
`cc_subscriptions.py:153,364`, `device_configurations.py:72` (registered) and
`identity_organization.py:75` (orphan). Every invocation raises `AttributeError`
**before any HTTP call** — the user sees a Python traceback, not `handle_rest_error` output.
`device_configurations.py:72` additionally passes `content_type="application/json-patch+json"`,
a kwarg no session method accepts — so adding `rest_patch` alone isn't enough.
**Blast:** `device-configurations update` is the write path for the `device-platform` skill
(RoomOS config via JSON-Patch). Also breaks identity-org updates and CC task/subscription updates.
**Why it survived:** write commands were never live-tested (operator memory
`feedback_live_test_writes` exists for exactly this class).
**Fix shape:** add `rest_patch(url, json, params, content_type=None)` to `WebexSession`;
thread `content_type` through `_headers()`. ~15 lines.

### F2 — Spec refresh and regeneration are uncoupled ★★★★★
Timeline (git):
- Last full/partial regen of the calling surface: `ed50ac5` (2026-05-04), plus fix `e7fd6f3`.
- Spec refreshes **without** regen: `41ee2fa` (2026-06-15), `dbeef6f` (2026-06-29).

Consequences measured in the coherence map: 57 spec ops missing from *existing registered groups*
(queue DNIS ×13, cc-flows ×10, my-call-settings ×7, agent-greetings ×6, call-recording
announcements ×4, …) and, in the other direction, 13 CLI commands whose endpoints are **no longer
in the current spec** (`cc_queue` bulk-export/internal family, `cc_ai_assistant create`) — these
may 404 at runtime or represent private endpoints Cisco removed from the published spec.
**Blast:** every consumer of the generated surface plans against a stale contract; the builder
agent's `--help` gate reflects the CLI, not the API.
**Fix shape:** regen after every spec update as one atomic commit (`update-specs.py` → generate →
register → test), plus a drift check that fails when spec ops ↔ generated commands diverge.

### F6 — No shared retry/backoff ★★★
`WebexSession.rest_*` = single `httpx` call, raise-on-failure (`auth.py:21-44`). No 429/Retry-After
handling, no backoff, no connect-error retry. Islands that self-medicate: `cleanup.py:14-30,677-743`
(409 location-delete loop), `src/wxcli/migration/rate_limiter.py` (migration execute).
Unprotected: org-health collection, all generated commands under agent-driven bulk use.
**Fix shape:** session-level 429/Retry-After honor + bounded backoff; keep cleanup's 409 logic.

### F11 — Stringly-typed errors ★★
`WebexError(response.text)` (auth.py) discards status code and headers. `errors.py:48-63` matches
substrings (`"wxcc" in err and "403" in err`) and numeric codes parsed back out of text
(`_extract_error_code`). Tips can misfire on unrelated text; per-status handling impossible.
**Fix shape:** carry `status_code` + parsed body on `WebexError`; keep message rendering.

### Seam conformance snapshot (for the target-architecture doc)
| Concern | Generated | cc_*/fs_* generated | cleanup | cucm family | locations/numbers/licenses | converged export |
|---|---|---|---|---|---|---|
| Auth | `get_api()` | `get_api()` + region base URL | `get_api()` | own (AXL + `get_api`) | `get_api()` | `get_api()` |
| Error handling | `handle_rest_error` | `handle_rest_error` | own orchestration | own | mixed (licenses: none) | `handle_rest_error` |
| Pagination | renderer: spec-param or `follow_pagination` | same | `follow_pagination` | n/a | hand-rolled | n/a (streaming) |
| Retry | none | none | own 409 loop | `rate_limiter.py` | none | none |
| Org-id injection | renderer modes (`get_org_id`/`resolve_org_id`/`get_cc_org_id`) | `get_cc_org_id` | own | own | hand-coded | n/a |

The seams are *mostly* conforming — the real inconsistencies are the session-layer gaps (F1, F6,
F11) that every family inherits, plus the two legacy duplications (F7).

## (b) Redundancy

### F7 — `licenses` + `licenses-api`; ADR-1's "legacy" trio ★★★
`docs/architecture/02-decisions.md` ADR-1: `locations.py`, `numbers.py`, `licenses.py`
"predate the generator (legacy)". `licenses` (3 commands) and generated `licenses-api` are **both
registered** (`main.py:155` + generated registration). `manage-licensing` builds on `licenses-api`
(SKILL.md:84-92); `provision-calling` references both; `configure-features`/`cucm-migrate` use
`licenses`. `manage-licensing/SKILL.md:86` recommends `licenses-api update` (PATCH semantics via
`--json-body`) with no caveat, while operator memory records that PATCH as broken (needs live
verification — the current `licenses_api.py` uses `rest_put`; re-test before acting).
`locations`/`numbers` have no generated twin registered, so they are duplication-*risk*, not
duplication-fact.
**Fix shape:** single canonical group per API family; alias the loser during a deprecation window.

### F8 — The wxcadm doc family is context debt ★★★
8 docs (`wxcadm-core/person/locations/features/devices-workspaces/routing/advanced` + realtime)
+ `wxc-sdk-patterns.md` ("Historical" per CLAUDE.md) are cited by **no skill** except
`call-control` → `wxcadm-xsi-realtime.md` (legitimate: XSI streaming has no wxcli path).
No code imports wxcadm (`grep` clean). CLAUDE.md's Mandatory Grounding Rule directs agents to
these docs as authoritative, but they document a Python object model this repo cannot execute.
**Fix shape:** archive 8 docs out of the grounding path (keep `wxcadm-xsi-realtime.md`),
or fold their unique API facts into the raw-HTTP docs.

### F9 — Stale published counts ★★★
"173 command groups / 9 specs": `CLAUDE.md` (≥3 places), `README.md:3,7,24,39`. Actual fresh-clone:
174 groups, 10 tracked specs, 1,838 commands. ADR-1 says "208 generated files, 8 hand-written";
disk has 216 modules (incl. 34 orphans). CLAUDE.md's spec file-map lists 6 of 10 tracked specs.
**Fix shape:** regenerate counts mechanically; add counts to the drift check (F2).

## (c) Coverage gaps (both directions)

### F5 — Core messaging /messages ★★★★
6 ops (`GET/POST /messages`, `GET /messages/direct`, `GET/PUT/DELETE /messages/{messageId}`),
tag `Messages` in `webex-messaging.json` — **no CLI**. The registered `messages` group is
meeting-messages (single command `delete` → `/v1/meeting/messages/{id}`). Meanwhile
`messaging-spaces/SKILL.md` cites `wxcli messages list/create/show/update/list-direct` and
`messaging-bots/SKILL.md` cites `messages create/show` — a workflow that cannot execute.
Root cause is a **tag-name collision** between the messaging spec's `Messages` and the meetings
spec's meeting-messages surface: the generator maps tag → module name, and meeting messages
claimed `messages.py` (verify collision mechanics during fix).
**Fix shape:** generate the messaging `Messages` tag under the natural name; rename or merge the
meeting-messages group (`cli_name_overrides` in field_overrides.yaml); regen + register + fix skills.

### F4 — The manual-registration seam ★★★★
ADR-1 gotcha, verbatim: "Registration is manual: each generated file must be added to `main.py`".
Measured cost: 34 tracked orphan modules (~388 commands), of which 29 fully superseded (stale
generations never deleted) and 5 with unique coverage — `wholesale_provisioning` (13 ops),
`wholesale_billing_reports` (4), `user_call_settings` (9), `hot_desking_members` (3),
`ucm_profile` (1). The wholesale gap from the mission brief is precisely this seam failing.
**Fix shape:** make registration generator-owned (emit a registration manifest imported by
`main.py`), decide the 5 unique-coverage cases, delete the 29 superseded files.

### F10 — Capability holes behind skill claims ★★★
1. Person-level `simultaneousRing` admin endpoints exist only in orphan `user_call_settings.py`
   — `manage-call-settings` advertises simultaneous ring; admin path unreachable via registered CLI.
2. Person-level hot-desking members (`.../features/hotDesking/{members,availableMembers}`) only in
   orphan `hot_desking_members.py`; CLAUDE.md's multi-skill table routes "manage members" to
   `manage-devices`, which only has workspace-level `hot-desk`/`hot-desking-portal` groups.
3. `customer-assist` cites `show-queue-recording`/`update-queue-recording` — no such commands
   exist anywhere in the CLI, and no spec op obviously matches; the 4 uncovered Call Recording ops
   are org/location *announcement* settings, not queue recording. Needs upstream verification:
   the capability may live behind `call-queue` + `--has-cx-essentials` or may not exist via API.

### F13 — CC spec churn artifacts ★★
`Functions` (11 ops) use colon-action paths (`/functions/{id}:publish`) the generator has never
produced commands for (verify generator handles `:` in path segments); `Activities`/`Templates`/
`Events` (6 ops) are flow-store paths embedded in the CC spec — covered only by dev-only fs groups.
Decide: generate, or add to `skip_tags` with a comment (making the skip *deliberate* instead of
accidental).

## (d) Taxonomy problems

### F3 — Skills cite the CLI from memory, and nothing checks ★★★★★
Coherence map §5: ~45 verified dead references across 14 of 24 skills + 1 in the builder agent
(`wxc-calling-builder.md:391`). Patterns: pre-rename `-v2` names (contact-center ×12), pre-split
names (`call-controls create-dial` → `-me`/`-members`), orphan-module group names
(`location-call-settings`, `user-call-settings`), plain typos (`hds list-multi-tenant`).
The repo already has the antidote as policy — the `--help` verification gate
(`feedback_help_gate_for_skills`, CLAUDE.md Known Issue #5) — but it operates at *runtime* per
session, costing tokens and only catching what a session happens to touch.
**Fix shape:** mechanical reference-checker (the Phase 1 extractor is 80% of it) run in CI/pre-commit;
fix all 45 refs in one sweep.

### F12 — Unclaimed admin surface ★★
22 "suspicious" unreferenced groups (coherence map §7): `emergency-services` (CLAUDE.md has an E911
workflow row and a dedicated reference doc, yet no skill runs the group), `announcements`/
`announcement-playlists`/`cq-playlists` (configure-features builds AA/CQ but never manages the
announcement repository), `virtual-line-settings`, `mode-management` (named in Known Issue #3),
`recordings`/`admin-recordings`, `identity-org`, `org-settings`, `roles`, etc. Plus 15 unclaimed
`cc-*` groups. Each needs a routing decision: extend an existing skill's table entry, or explicitly
declare out-of-skill-scope.

### F14 — CLAUDE.md tables route to capabilities that don't exist as described ★★
- "Hot desking on conference phones → manage-devices (enable hot desking, **manage members**)":
  person-level members API unregistered (F10.2).
- Skill-disambiguation rows for recording ("Set up recording (CC queue recording) → customer-assist")
  route to dead commands (F10.3).
- The `messages` rows in messaging skills' scopes (F5).
The tables' *structure* is sound (Phase 1 §9 shows healthy lifecycle splits); the defects are
these specific rows plus missing rows for the F12 surface.

---

## What is *not* drifted (verified healthy)

- Reference docs ↔ skills: 0 broken citations; 49/49 content docs cited (§5.3).
- Generated-command internals: uniform auth (`get_api`), error funnel (`handle_rest_error`),
  spec-driven pagination, renderer-owned org-id injection — generation is doing its job (§seam table).
- Skill↔skill group overlap: matches the intended lifecycle taxonomy (map §9).
- `fs_*` dev-only seam: guarded, commented, deliberate (`main.py:512-537`).
- `cucm`/`cleanup`/`converged-export` hand seams: justified per ADR-1, conforming where applicable.
