# Target Architecture — Coherence Audit Phase 3 (revised by Phase 4 critique)

Builds on `coherence-map.md` (Phase 1) and `drift-analysis.md` (Phase 2). Extends — does not
replace — ADR-1/2/7/8 and CLAUDE.md's existing taxonomy tables.

## A. One endpoint-handling pattern

**Invariant: every REST-touching command flows through one session contract, and every generated
artifact is owned end-to-end by the generator.**

### A1. Session contract (`src/wxcli/auth.py`)
- `WebexSession` implements **all five verbs** (`rest_get/post/put/patch/delete`), each accepting
  `params`, `json`, and `content_type` (default `application/json`).
- `WebexError` carries `status_code` and the parsed error body alongside the message text;
  `errors.py` tips key off status + `trackingId`-bearing body fields instead of substring matching.
- Retry policy lives in the session: honor `429 Retry-After` (bounded, logged), single retry on
  connect errors. Orchestrators (cleanup's 409 loop, migration's `rate_limiter.py`) keep their
  domain-specific loops **on top of** the baseline, not instead of it.
- Rationale: F1/F6/F11 are all one seam. Fixing them in the session fixes all 1,838 commands and
  every hand-written module simultaneously, because the seam-conformance table (Phase 2) shows
  everything already routes through `get_api()`.

### A2. Generation lifecycle — "spec sync" is one atomic operation
A spec refresh is not done until the CLI matches it. One command (make target or
`tools/spec_sync.py`) runs: `update-specs.py` → `generate_commands.py` (all specs) →
registration manifest regeneration → drift gate → single commit
`chore(specs): sync specs + regen (date)`.
- Kills F2 structurally: "specs updated, regen forgotten" becomes impossible to commit silently.
- The 13 CLI-ahead-of-spec CC commands get resolved at the first sync: regenerated away if the
  endpoints are gone, or kept via an explicit `keep_endpoints` override in `field_overrides.yaml`
  if they're known-good private endpoints (decision recorded in the YAML comment, same pattern as
  `skip_tags` canonical comments).

### A3. Registration is generator-owned (closes the orphan seam)
The generator emits `src/wxcli/commands/_registry.py` — an explicit list of
`(module, group_name)` pairs for everything it generated from non-skipped tags. `main.py` imports
the manifest for generated groups and keeps **explicit** registrations only for: hand-written
seams, aliases (`users`, `cx-essentials`), and the guarded dev-only `fs_*` block.
- A generated module that exists but isn't in the manifest cannot happen (the generator writes
  both); a manifest entry without a module fails import loudly at build time, not silently at
  runtime. ADR-1's "registration is manual" gotcha is retired.
- Dev-only specs (`webex-flow-store.json`) are excluded from the manifest via a generator flag
  (`--dev-only`): their groups keep the guarded `try/except` block in `main.py`. Otherwise a local
  regen would write untracked fs entries into the tracked manifest and break fresh clones.
- Orphan disposition (the 34): delete the 29 fully-superseded modules; register
  `wholesale-provisioning` + `wholesale-billing-reports` (decision: the specs are tracked and the
  ops are otherwise unreachable — 17 ops); fold `user_call_settings`' unique endpoints
  (simultaneousRing family, services) and `hot_desking_members` into the next regen so they land
  in the *current-generation* modules for those tags (verify tag mapping at regen; do not
  re-register the stale modules themselves); register `ucm-profile` (1 op, trivial) or add its tag
  to `skip_tags` with a comment — either is acceptable; default: register.

### A4. Hand-written exception charter (extends ADR-1)
A module may be hand-written iff it needs **state, orchestration, or I/O a per-endpoint template
cannot express**. Conforming exceptions: `cleanup.py`, `cucm` family, `converged_recordings_export.py`
(streaming), `configure.py`/`update.py` (no REST). Each must still: use `get_api()`, raise/handle
`WebexError`, and use session pagination where applicable — all true today.
**The legacy trio is not chartered**: `licenses.py` retires in favor of generated `licenses-api`
renamed to `licenses` via `cli_name_overrides` (alias `licenses-api` kept one release);
`locations.py`/`numbers.py` migrate the same way **only after** the generated equivalents are
verified to carry the org-id injection and UX they were hand-written for (blocking check, see
refactor plan; if the generator can't express them yet, they stay chartered with a dated comment).

### A5. Deliberate gaps are visible
`skip_tags` already documents canonical-spec ownership in comments. Extend: every skip entry
carries a reason comment (Beta, infra, dev-only, canonical-elsewhere), and the drift gate emits
`docs/arch/deliberate-gaps.md` (generated) listing all skipped ops — so "no CLI" is always
classifiable as *deliberate* vs *drift* without re-running this audit. Flow-store-in-CC-spec paths
(Activities/Templates/Events, 6 ops) and CC `Functions` colon-action paths (11 ops) get explicit
entries: Functions requires generator support for `:action` path segments — generate when
supported; skip-with-comment until then.

### A6. The drift gate (CI / pre-commit)
Three mechanical checks, all derived from the Phase 1 extractor:
1. **Spec ↔ CLI parity**: every non-skipped spec op has ≥1 registered command; every command URL
   maps to a live spec op or a `keep_endpoints` entry.
2. **Reference existence**: every `wxcli <group> [<command>]` token in `.claude/skills/**`,
   `.claude/agents/**`, `.claude/rules/**`, `CLAUDE.md`, `README.md` resolves against the built CLI
   (allowlist for prose false-positives via a fenced-code-only scan).
3. **Published counts**: group/command/spec/skill counts in CLAUDE.md and README match measured.

## B. Skill taxonomy — diff against CLAUDE.md's current tables

The 24-skill structure and the three existing tables survive the audit (Phase 1 §9: overlaps match
the intended lifecycle splits). Changes are row-level:

### B1. Corrections to existing rows
| Table | Row (current) | Change |
|---|---|---|
| Multi-skill workflows | "Hot desking on conference phones → manage-devices (enable hot desking, manage members)" | After A3 lands person-level hot-desking endpoints, note that *person-level* members are `manage-call-settings` territory (person settings), workspace/device-level stays `manage-devices` |
| Disambiguation | "Set up recording (CC queue recording) → customer-assist" | Keep the row; **fix the skill**: replace dead `show-queue-recording`/`update-queue-recording` with the verified live path (call-queue `--has-cx-essentials` per Known Issue #7), or mark the capability API-unavailable after live verification |
| Disambiguation (implicit) | messaging-spaces "messages" scope | Becomes real once F5 lands; skills updated to the actual generated command names in the same commit |

### B2. New rows (claiming the unclaimed surface — drift F12)
Additions to the **Skill Disambiguation** table ("Undocumented capabilities" section):
| If the user wants to... | Use this skill | NOT this one |
|---|---|---|
| Manage announcement repository files/playlists (AA/CQ greetings) | `configure-features` (groups: `announcements`, `announcement-playlists`, `cq-playlists`) | `reporting` (that's recordings, not announcements) |
| Configure E911 emergency services/addresses (`emergency-services` group) | `provision-calling` (location addresses) + `manage-call-settings` (per-person ECBN) — matches existing E911 workflow row | `wxc-calling-debug` |
| Virtual line call settings (`virtual-line-settings`) | `manage-call-settings` (virtual lines are person-like settings; doc exists: `virtual-lines.md`) | `provision-calling` |
| Operating modes / mode management (`mode-management`, user-token only per Known Issue #3) | `manage-call-settings` | `configure-features` (`operating-modes` location/feature side stays there) |
| Org/admin recordings retrieval (`recordings`, `admin-recordings`) | `reporting` | `manage-meetings` |
| Org profile, settings, roles (`identity-org`, `org-settings`, `roles`) | `manage-identity` | `audit-compliance` |

### B3. Explicit out-of-skill-scope declaration (new short list in CLAUDE.md)
Groups intentionally not fronted by any skill — so "unreferenced" is a decision, not drift:
`broadworks-*` (4), `wholesale-*` (2, post-registration), `partner-admins`, `partner-tags`,
`hybrid-clusters`, `hybrid-connectors`, `fs-*` (11, dev-only), `update`, `text-to-speech`,
`archive-users`, `classifications`, `data-sources`, `guest-management`, plus the 15 unclaimed
`cc-*` groups until `contact-center` claims them deliberately (its 30-group scope is already the
largest; expanding it is a product decision, not a hygiene fix).

### B4. What does NOT change
No skill splits/merges. No renames. The Calling-vs-CC terminology table is untouched (it was
verified accurate). `reporting`/`reporting-cc`/`reporting-meetings` split stays (deliberate,
documented, disjoint API domains).

## C. Skill authoring standard (one line)

> **A skill may only teach what the current CLI can execute: every cited `wxcli` invocation must
> resolve against the built CLI (drift-gate-enforced), and every capability claim must trace to a
> cited command or a `docs/reference/*.md` section.**

Corollaries (not new rules, consequences): no `-v2`-era names survive a regen; a capability with
no CLI path is marked "no CLI — raw HTTP fallback" in the skill rather than invented; the runtime
`--help` gate stays as defense-in-depth but stops being the only line.

## D. Five highest-impact changes, before → after

### D1. Session PATCH (F1)
**Before** (`auth.py` — `rest_patch` absent; `device_configurations.py:72` crashes):
```
AttributeError: 'WebexSession' object has no attribute 'rest_patch'
```
**After** (`auth.py` gains, mirroring `rest_put`):
```python
def rest_patch(self, url: str, json=None, params=None, content_type: str | None = None) -> dict:
    headers = self._headers()
    if content_type:
        headers["Content-Type"] = content_type
    response = httpx.patch(url, headers=headers, json=json, params=params)
    if not response.is_success:
        raise WebexError(response.text, status_code=response.status_code)
    return response.json() if response.content else {}
```
`wxcli device-configurations update --device-id … --op replace --path … --value …` executes a real
JSON-Patch request; device-platform's write path works.

### D2. Spec sync (F2)
**Before**: `dbeef6f` updates 7 specs; no regen; 57 ops silently missing; queue-DNIS unreachable.
**After**: `make spec-sync` produces one commit in which `wxcli call-queue --help` shows the 13
DNIS/settings commands, the drift gate passes, and a spec refresh *cannot* land without regen
because CI check A6.1 fails on the diverged parity count.

### D3. Registration manifest (F4)
**Before** (`main.py`, 185 hand-maintained blocks):
```python
from wxcli.commands.cc_users import app as cc_users_app
app.add_typer(cc_users_app, name="cc-users")
# … ×183, and wholesale_provisioning.py sits on disk, imported by nothing
```
**After**:
```python
from wxcli.commands._registry import GENERATED_GROUPS  # emitted by generate_commands.py
for module_name, group_name in GENERATED_GROUPS:
    app.add_typer(import_module(f"wxcli.commands.{module_name}").app, name=group_name)
# explicit: hand-written seams, aliases, guarded fs_* dev block
```
`wxcli wholesale-provisioning list-customers` exists; a future generated-but-unregistered module
is structurally impossible.

### D4. Core messages (F5)
**Before**: `wxcli messages list` → `No such command 'list'.` while
`messaging-spaces/SKILL.md` instructs exactly that.
**After**: messaging-spec `Messages` tag generates the group; the current meeting-messages
surface is renamed `meeting-messages` via `cli_name_overrides`. **No alias for the old name** —
the `messages` name is being reclaimed, so this is a breaking rename; measured consumers of the
old group: zero (no skill, agent, rule, or doc cites `messages delete`).
`wxcli messages create --room-id … --text …` sends a message; both messaging skills cite the
generated names verified by the drift gate.

### D5. Skills reference sweep + gate (F3)
**Before**: `contact-center/SKILL.md` teaches `wxcli cc-entry-point list-entry-point-v2` (dead);
builder agent's worked example uses `wxcli locations enable-calling` (dead).
**After**: one mechanical sweep fixes all ~45 refs to current names
(`list-entry-point`, and the agent example uses the real location-calling enable flow);
drift-gate check A6.2 fails any future PR that reintroduces a dead reference.

---

## Phase 4 — Adversarial critique and revisions applied

Attack rounds run against the draft; structural problems found and the revisions they forced:

**R1. "Renaming `licenses-api`→`licenses` breaks the CUCM migration executor and existing
skills mid-flight."** Verified: `cucm-migrate` + `configure-features` reference `licenses`,
`manage-licensing` references `licenses-api`. A hard cutover breaks one side no matter what.
→ Revision (A4): rename with **alias retained for one release**, same pattern as `users`→`people`;
skills updated in the same commit; migration executor references checked by gate A6.2.
Verified during critique: the migration engine calls the API directly
(`src/wxcli/migration/execute/engine.py` uses the session layer); its `wxcli` mentions are
operator-hint strings for `cucm` subcommands only (`planner.py:1763,1782,…`), which are not being
renamed — so the consolidation cannot break a migration in flight.

**R2. "The registration manifest changes `main.py` import mechanics — lazy vs eager imports and
CLI startup latency; 185 eager imports may already be the cost, but `import_module` in a loop
defeats static analysis."** Partially valid: startup already imports everything eagerly; the loop
only changes *how*. But static-analysis/grep-ability of "which module backs group X" is a real
regression for debugging and for permission-prefix reasoning.
→ Revision (D3): the generator emits the manifest as **explicit literal lines**
(`("cc_users", "cc-users"),` …) in one generated file — greppable, diffable, reviewed like any
regen artifact. No dynamic discovery; `import_module` acceptable since the manifest is static data
in-repo. (Alternative — generator emits the `main.py` block verbatim — rejected: two writers for
one file.)

**R3. "Deleting 29 'fully superseded' orphans assumes normalized-path equivalence proved
supersession. Suffix-collision commands (`-1` variants) or `--json-body` differences could mean
the orphan version is the only *working* variant for some op."** Fair. Path-level supersession
was verified, behavior-level was not.
→ Revision (A3 + refactor plan): deletion is gated on the drift gate passing *after* deletion
(parity check unaffected because orphans aren't registered — trivially true), **plus** a spot
live-test of the 3 highest-traffic superseded families (location settings, workspace settings,
SCIM) per `feedback_live_test_writes`. Deletion stays "safe now" because orphans are unreachable
from the CLI today — removing them cannot change runtime behavior; the live-tests guard the
*claim* that registered equivalents work, which matters for F10-adjacent capabilities, not for
the deletion itself.

**R4. "Bulk location provisioning (real SE workflow): does anything here touch
`provision-calling`'s hot path?"** Checked: provision-calling's dead refs are
`location-call-settings` (orphan name) and `org-domains`; its live groups (`locations`, `numbers`,
`licenses`, `people`) are exactly the ones A4 touches. If `locations.py`/`numbers.py` migration to
generated equivalents changes flag names, bulk CSV workflows break.
→ Revision (A4): locations/numbers migration is **deferred and gated** — stays hand-written
(chartered, dated) unless/until the generated twin passes a flag-compatibility diff. Only
`licenses` (3 commands, trivial surface) consolidates now. This keeps the offboarding and bulk
provisioning workflows on stable commands.

**R5. "WxCC agent setup: fixing `-v2` names in contact-center touches 12 refs, but regen (D2)
may *rename them again* (CC spec churn), invalidating the sweep."** Valid ordering hazard.
→ Revision (refactor plan): the skills reference sweep (D5) runs **after** spec-sync (D2), never
before; the gate pins the order. Same for messaging skills after D4.

**R6. "Phase-per-invocation contract: builder agent reads CLAUDE.md + skills at spawn; changing
tables (B1/B2) mid-flight while a long CUCM migration project is in progress could desync a
running engagement."** Low practical risk (tables are read fresh each invocation — that's the
contract working, not breaking), but the *worked example* fix in the agent (D5) must not change
the documented auth/org-confirmation flow, which cucm runbooks reference by section.
→ Revision: agent edits restricted to dead-command corrections; no structural section moves in
`wxc-calling-builder.md` within this effort.

**R7. "What did you rationalize away? The 15 unclaimed cc-* groups and 22 suspicious groups get
'a decision' but no owner or deadline — that's how drift happened the first time."**
→ Revision (B3): the out-of-scope list is **in CLAUDE.md itself** and the drift gate counts
unreferenced groups against it: a group neither skill-referenced nor on the declared list fails
the gate. Silent unclaimed surface becomes impossible; claiming it remains a product decision.

**R8. "wxcadm docs: call-control legitimately needs XSI; archiving 8 docs may strand other unique
facts (RedSky, Meraki, CP-API in wxcadm-advanced.md)."** Checked — and the first draft of this
critique was itself wrong: RedSky-adjacent E911 *does* have a CLI surface
(`src/wxcli/commands/emergency_services.py`, `redsky` appears in `webex-cloud-calling.json`),
covered by `docs/reference/emergency-services.md`. What wxcadm-advanced.md documents is the
wxcadm *object model* for the RedSky Horizon portal and Meraki dashboards — external products
with no wxcli path. The Webex-side facts already live in the raw-HTTP docs.
→ Revision (B/refactor plan): archive = move to `docs/reference/archive/` + drop from CLAUDE.md
file map + add one redirect line in the map ("historical SDK docs: see archive/"). No deletion.
Any future skill needing RedSky-portal/Meraki facts can resurrect deliberately.

**R9 (second loop, against the revised draft).** Two further structural defects found and fixed
in place: (a) the registration manifest would have included dev-only `fs_*` groups, breaking fresh
clones — A3 now excludes dev-only specs from the manifest; (b) D4 promised an alias for the old
`messages` name while simultaneously reclaiming that name — contradiction removed; the rename is
declared breaking, with measured zero in-repo consumers.

**R10.** No further structural problems; remaining objections are sequencing details the refactor
plan absorbs (e.g., D1 lands before any regen so newly generated `rest_patch` callers never meet
a missing method).
