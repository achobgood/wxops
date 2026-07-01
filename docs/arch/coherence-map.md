# Coherence Map — Spec ↔ CLI ↔ Skills ↔ Reference Docs ↔ Builder Agent

**Phase 1 of the architectural coherence audit.** Branch `arch/coherence-audit`, measured 2026-07-01.

**Method.** All figures below were extracted mechanically, not estimated:
- Spec operations: parsed `paths` × HTTP methods from all `specs/*.json`.
- CLI commands: regex-extracted every `@*.command(...)` + `url = f"..."` + `rest_<method>` from
  `src/wxcli/commands/*.py`; group registrations parsed from `app.add_typer(...)` in `src/wxcli/main.py`.
- Matching: URL bases stripped (`https://webexapis.com/v1`, `{cc_base_url}`, `{fs_base_url}`,
  `https://analytics-calling.webexapis.com/v1`), path params normalized to `{}`, matched on
  (method, normalized path), with `/v1`-prefix tolerance for the CC spec.
- Skills/agent/docs: scanned all git-tracked files under `.claude/skills/`, `.claude/agents/`,
  `.claude/rules/`, plus `CLAUDE.md`, for `wxcli <group> <command>` references and
  `docs/reference/*.md` citations; validated against the extracted CLI surface.
- Machine-readable companion: `docs/arch/coherence-map-data.json`.

**Caveats.** (1) Command extraction is static regex, verified against known seams
(`cucm` unnamed `@app.command()` functions, `converged_recordings_export.register()` mounting)
— both handled. (2) Prose false positives in skill scans ("wxcli does…", checklist fragments)
were hand-triaged out; every dead reference listed below was individually verified against the
actual command list of the module in question. (3) `src/wxcli/org_health/collector.py` calls the
API session directly (0 `wxcli` references) — org-health's CLI dependencies live in its SKILL.md only.

---

## 1. Ground truth vs. operator baseline

| Quantity | Baseline (2026-07-01) | Measured | Verdict |
|---|---|---|---|
| OpenAPI specs | 11 | **11 on disk, 10 git-tracked** | `specs/webex-flow-store.json` is local-only (deliberate: dev-only, see §4.4) |
| Spec operations | ~2,106 | **2,106** (2,017 in tracked specs) | Exact match |
| CLI command groups | 185 | **185 registered names = 183 unique modules + 2 aliases; 174 on a fresh clone** (11 `fs-*` groups are dev-only/untracked, §3.3) | Aliases: `cx-essentials`→`customer_assist`, `users`→`people`. Published "173" (README/CLAUDE.md) is 1 behind the fresh-clone count, 11 behind local |
| CLI commands | ~1,867 | **1,838 in registered modules; 2,242 command functions in 216 modules on disk** | Divergence explained by 34 orphaned modules (§4.3) and non-REST `cucm` subcommands |
| Generated share | ~95% | **~97% of registered commands** (hand-written: `cleanup`, `cucm` family, `locations`, `numbers`, `licenses`, `configure`, `converged_recordings_export` = ~55 commands) | Confirmed |
| Skills (git-tracked) | 24 | **24** | Exact match |
| Reference docs | ~40 | **51 tracked `.md` in `docs/reference/`** (49 content docs + `CLAUDE.md` + `TODO.md`) | Baseline undercounted |

**Stale published counts** (doc drift, not measurement error):
- `CLAUDE.md` says "173 command groups" and "9 OpenAPI specs" (multiple places). Fresh-clone
  actual: 174 groups, 10 tracked specs — off by one group and one spec (the tracked-count
  convention itself is right per prior decision; the numbers lag).
- `README.md:3,7,24,39` says "173 command groups", "9 OpenAPI specs". Same staleness.
- `CLAUDE.md` file map lists 6 specs; `specs/` contains 10 tracked (missing: `tts-spec.json`,
  `webex-broadworks.json`, `webex-ucm.json`, and the untracked `webex-flow-store.json`).

---

## 2. Spec → CLI coverage

Per-spec operation coverage by **registered** command groups:

| Spec | Ops | Covered (registered) | Covered only by unregistered module | No CLI at all |
|---|---|---|---|---|
| webex-cloud-calling.json | 1,044 | 981 | 12 | 51 |
| webex-contact-center.json | 444 | 399 | 0 | 45 |
| webex-meetings.json | 168 | 168 | 0 | 0 |
| webex-admin.json | 148 | 146 | 0 | 2 |
| webex-device.json | 101 | 99 | 0 | 2 |
| webex-flow-store.json (untracked) | 89 | 72 | 0 | 17 |
| webex-messaging.json | 63 | 57 | 0 | 6 |
| webex-broadworks.json | 19 | 19 | 0 | 0 |
| webex-wholesale.json | 18 | 1* | 17 | 0 |
| tts-spec.json | 11 | 11 | 0 | 0 |
| webex-ucm.json | 1 | 0 | 1 | 0 |
| **Total** | **2,106** | **1,953** | **30** | **123** |

\* The 1 "covered" wholesale op (`POST /subscribers/{subscriberId}/emails/consentMove`) is covered
coincidentally by `broadworks_subscribers:create-consent-move` — the same path exists in both specs (§6).

### 2.1 Uncovered ops classified: deliberate vs. gap

`tools/field_overrides.yaml:558` (`skip_tags`) deliberately skips `Beta *` globally plus per-spec
non-canonical/infra tags. Classifying the 123 uncovered + 2 CDR ops that matched after base-URL
normalization (net 121):

- **38 deliberately skipped** (working as designed, but undocumented outside the YAML):
  - `Beta *` tags: 20 ops (16 "Beta Call Settings For Me With Userhub Phase1", 2 barge-in, 2 device).
  - Flow-store infra controllers: 17 ops (`admin-flow-controller` 12, `auth`, `health`,
    `prometheus`, `buid-info`).
  - `Device Call Settings` in webex-device.json: 1 op (canonical copy lives in cloud-calling spec).
- **83 real gaps**, split by cause:

**STALE-GROUP (57 ops)** — a registered group exists for the tag, but ops added to the spec after
the group's last regeneration are missing. Root cause: two spec refreshes
(`41ee2fa` 2026-06-15, `dbeef6f` 2026-06-29) landed with **no regeneration**; last regen of the
calling surface was 2026-05-04 (`ed50ac5`).

| Spec | Tag → stale registered group | Missing ops | What's missing |
|---|---|---|---|
| cloud-calling | Features: Call Queue → `call-queue` | 13 | Entire queue-DNIS family (`/telephony/config/locations/{loc}/queues/{q}/dnis*`) + org-level `/telephony/config/queues/settings` (added 2026-06-15) |
| contact-center | Flows / Legacy Flows → `cc-flow` | 10 | Flow lifecycle ops |
| cloud-calling | Call Settings For Me (+Phase 4) → `my-call-settings` | 7 | Newer self-service endpoints |
| contact-center | Agent Personal Greeting Files → `cc-agent-greetings` | 6 | File upload/download ops |
| contact-center | Agents → `cc-agents` | 4 | |
| cloud-calling | Features: Call Recording → `call-recording` | 4 | |
| contact-center | Audio Files → `cc-audio-files` | 3 | |
| admin | Identity Organization → `identity-org` | 2 | `PATCH .../authenticationConfig`, `PATCH .../passwordPolicy` |
| contact-center | Tasks → `cc-tasks`; Users → `cc-users`; Campaign Manager → `cc-campaign` | 2+2+1 | |
| cloud-calling | Workspace Call Settings → `workspace-settings`; Device Call Settings → `device-settings` | 2+1 | |

**NO-GROUP (26 ops)** — no registered group covers the tag at all:

| Spec | Tag | Ops | Notes |
|---|---|---|---|
| contact-center | Functions | 11 | `/v1/{orgId}/functions` CRUD + colon-action paths (`:import`, `:lock`, `:test`, `:publish`) — colon-suffix paths may need generator support |
| messaging | **Messages** | 6 | **The core messaging API**: `GET/POST /messages`, `GET /messages/direct`, `GET/PUT/DELETE /messages/{messageId}` — confirmed known gap; the registered `messages` group is meeting-messages only (its sole command is `delete` → `/v1/meeting/messages/{id}`, `src/wxcli/commands/messages.py`) |
| contact-center | Activities | 3 | Paths are `/flow-store/{orgId}/project/...` — flow-store surface embedded in the CC spec (§6) |
| contact-center | Templates / Events | 2+1 | Also flow-store-in-CC-spec paths |
| cloud-calling | User Call Settings | 2 | `GET .../monitoring/availableMembers`, `GET .../monitoring/speedDials/availableMembers` |
| cloud-calling | (untagged) | 1 | `GET /telephony/config/people/me/settings/contactCenterExtensions` |

### 2.2 Known-gap confirmations (from mission brief)

1. **Wholesale**: CONFIRMED with nuance. It is *not* that no CLI exists — `wholesale_provisioning.py`
   (14 commands) and `wholesale_billing_reports.py` (4 commands) were generated in commit `37d299c`
   and are git-tracked, but were **never registered in `main.py`**. 17 of 18 wholesale ops are
   reachable only through these dead modules.
2. **Core messaging `/messages`**: CONFIRMED exactly as stated (see NO-GROUP table). Worse: two
   skills actively cite the nonexistent commands (§5.2).

---

## 3. CLI → spec (reverse direction)

Of 2,214 (command, method, URL) tuples extracted, only **13 have no spec operation**:

| Where | Commands | Verdict |
|---|---|---|
| `cc_queue` (registered) | `create` (`POST .../contact-service-queue`), `list-bulk-export`, 4× `list-internal-by-*`, `update-contact-service-queue-organization` | CLI **ahead of** spec — endpoints exist in the CLI that the current CC spec no longer (or never) documents. Likely generated from an earlier CC spec revision and kept through refresh |
| `cc_business_hour`, `cc_desktop_layout`, `cc_desktop_profile`, `cc_dial_plan`, `cc_outdial_ani` (registered) | one `*bulk-export` command each | Same pattern — `bulk-export` family absent from current spec |
| `cc_ai_assistant` (registered) | `create` (`POST {cc_base_url}/event`) | Same |

Everything else — including the hand-written seams — maps to a spec operation. The two
`converged_recordings_export` commands reuse spec paths (`/admin/convergedRecordings`,
`/convergedRecordings/{id}`) already covered by the generated group.

### 3.1 Hand-written seam inventory (the ~3% that is not generated)

| Seam | File(s) | Registration | Nature |
|---|---|---|---|
| `cleanup` | `src/wxcli/commands/cleanup.py` | `main.py:159` | Batch orchestrator (13-layer deletion, threading, retries); calls APIs via `get_api()` session, no per-endpoint commands |
| `cucm` (27 subcommands) | `src/wxcli/commands/cucm.py`, `cucm_config.py`, backed by `src/wxcli/migration/` | `main.py:156` | Local pipeline commands (no REST URLs) + AXL/SOAP against CUCM |
| `locations` | `src/wxcli/commands/locations.py` | `main.py:153` | Hand-coded org-id injection; 10 commands |
| `numbers` | `src/wxcli/commands/numbers.py` | `main.py:154` | Hand-coded org-id injection |
| `licenses` | `src/wxcli/commands/licenses.py` | `main.py:155` | Hand-coded; **coexists with generated `licenses-api` group** (`licenses_api.py`) — two registered groups for the same API family (§5.4) |
| `converged-recordings` download/export | `converged_recordings_export.py` | Mounted into the *generated* group via `converged_recordings_export.register(converged_recordings_app)` (`main.py:164-165`) | The documented model for extending a generated group |
| `configure` / `update` / top-level (`whoami`, `switch-org`, `clear-org`, `set-cc-region`, …) | `main.py`, `configure.py`, `update.py` | top-level | Config/auth/self-update; no REST endpoints |

### 3.2 Orphaned command modules (git-tracked, never imported)

**34 modules containing ~388 command functions exist in `src/wxcli/commands/`, are git-tracked,
and are imported by nothing.** `main.py` does not register them; no other module imports them.
29 are **fully superseded** — every endpoint they touch is also covered by a currently
registered module (they are earlier-generation outputs kept on disk after tags were merged/renamed,
last touched in the `e4dfb22` wxc_sdk-removal refactor or earlier):

`admin_audit_events`, `api_domain_management`, `bulk_manage_scim_2_users_and_groups`,
`call_queue_settings_with_playlist_settings`, `caller_reputation_provider`,
`calling_service_settings`, `client_call_settings`, `conference_controls`, `cx_essentials`,
`dect_devices_settings`, `ecm_folder_linking`, `historical_analytics_apis`,
`identity_organization`, `location_call_settings`, `location_call_settings_call_handling`,
`location_call_settings_schedules`, `location_call_settings_voicemail`, `meeting_slido`,
`organization_contacts`, `partner_administrators`, `reports_detailed_call_history`,
`scim_2_groups`, `scim_2_schemas`, `scim_2_users`, `security_audit_events`,
`send_activation_email`, `settings`, `virtual_line_call_settings`, `workspace_call_settings`

5 orphans carry **unique endpoint coverage** no registered module provides:

| Orphan module | Unique endpoints | Assessment |
|---|---|---|
| `wholesale_provisioning` | 13 | The wholesale gap (§2.2) |
| `wholesale_billing_reports` | 4 | The wholesale gap (§2.2) |
| `user_call_settings` | 9 | Admin-path `anonymousCallReject` (2), `simultaneousRing` + criteria (5), `services` (1)… `anonymousCallReject` admin path 404s per Known Issue #4, but **per-person `simultaneousRing` admin endpoints exist nowhere in the registered CLI** even though the `manage-call-settings` skill advertises simultaneous ring |
| `hot_desking_members` | 3 | `/telephony/config/people/{id}/features/hotDesking/{availableMembers,members}` — CLAUDE.md's multi-skill table routes "hot desking members" to `manage-devices`, but the registered surface has no group for these person-level endpoints |
| `ucm_profile` | 1 | `GET /telephony/config/callingProfiles` (webex-ucm.json's only op) |

### 3.3 The `fs_*` dev-only seam (deliberate, documented in-line)

All 11 `fs_*.py` modules and `specs/webex-flow-store.json` are **untracked**; `main.py:512-537`
registers them inside a `try/except ImportError` explicitly commented
"Dev-only: Flow Store CLI (gitignored…)". A fresh clone gets a working CLI without the 11 fs groups.
This is a deliberate exception, but note: it is invisible to CLAUDE.md and README (group counts
in docs include/exclude it inconsistently — 185 registrations include the 11 fs groups only when
the local files exist).

---

## 4. Skills → CLI groups & reference docs (dependency matrix)

Counts of distinct registered CLI groups referenced and `docs/reference/*.md` docs cited, per
git-tracked skill (from `SKILL.md` + all tracked files in the skill directory):

| Skill | CLI groups | Ref docs | Skill | CLI groups | Ref docs |
|---|---|---|---|---|---|
| contact-center | 30 | 4 | manage-identity | 11 | 2 |
| cucm-migrate | 19 | 1 | provision-calling | 11 | 1 |
| manage-meetings | 18 | 3 | messaging-spaces | 10 | 1 |
| teardown | 17 | 2 | wxc-calling-debug | 10 | 12 |
| configure-features | 15 | 2 | messaging-bots | 9 | 2 |
| query-live | 15 | 0 | audit-compliance | 8 | 1 |
| manage-devices | 14 | 3 | device-platform | 8 | 4 |
| manage-call-settings | 13 | 5 | reporting | 8 | 1 |
| org-health | 13 | 0 | reporting-cc | 8 | 1 |
| — | — | — | manage-licensing | 7 | 2 |
| — | — | — | reporting-meetings | 7 | 3 |
| — | — | — | customer-assist | 6 | 2 |
| — | — | — | call-control | 5 | 3 |
| — | — | — | configure-routing | 5 | 1 |
| — | — | — | video-mesh | 3 | 1 |

Full per-skill group and doc lists: `docs/arch/coherence-map-data.json`.

## 5. Skills → CLI: verified dead references

Every entry below was verified against the actual command list of the named module
(prose false positives excluded; runtime-mounted commands like `converged-recordings download/export`
and all `cucm` subcommands verified as VALID and excluded).

### 5.1 References to unregistered/nonexistent **groups**

| Skill / file | Dead reference | Reality |
|---|---|---|
| `cucm-migrate/SKILL.md` | `wxcli location-call-settings-schedules` | Orphan module, never registered; live group is `location-schedules` |
| `manage-call-settings/SKILL.md` | `wxcli location-call-settings` | Orphan module; live group is `location-settings` |
| `provision-calling/SKILL.md` | `wxcli location-call-settings` | Same |
| `provision-calling/SKILL.md` | `wxcli org-domains` | No such group (domains live under identity/org groups) |
| `manage-devices/SKILL.md` | `wxcli user-call-settings` | Orphan module; live group is `user-settings` |
| `query-live/domains/routing.md` | `wxcli route-group`, `wxcli trunk` | Groups are plural-free under `call-routing` (`create-route-groups`, `create-trunks`, …); neither `route-group` nor `trunk` is a group |
| `reporting-cc/SKILL.md` | `wxcli get-cc-region` | Only `set-cc-region` exists (top-level); no getter |

### 5.2 References to nonexistent **commands** in valid groups

| Skill | Cited (dead) | Actual command |
|---|---|---|
| messaging-spaces | `messages create` / `list` / `list-direct` / `show` / `update` | **None exist.** `messages` has exactly one command: `delete` (meeting messages). The core /messages API has no CLI (§2.1) |
| messaging-bots | `messages create`, `messages show` | Same |
| messaging-spaces | `hds list-multi-tenant` | `hds list-tenants` |
| contact-center | 12 refs: `cc-aux-code list-auxiliary-code-v2`, `cc-dial-plan list-dial-plan-v2`, `cc-entry-point list-entry-point-v2`, `cc-multimedia-profile list-multimedia-profile-v2`, `cc-queue create-contact-service-queue-v2`, `cc-skill-profile list-skill-profile-v2`, `cc-call-monitoring create-monitor`, `cc-desktop-profile create-agent-profile`, `cc-dial-plan create-dial-plan`, `cc-entry-point create-entry-point`, `cc-multimedia-profile create-multimedia-profile`, `cc-skill-profile create-skill-profile` | `-v2` suffixes no longer exist (now bare `list-dial-plan`, etc.); resource-suffixed creates are now bare `create` |
| manage-meetings | `meetings create-meetings` / `delete-meetings` / `list-meetings-admin` / `update-meetings-1` | `create` / `delete` / (no admin variant) / `update-meetings` |
| manage-meetings | `meeting-captions list-meeting-closed-captions`; `meeting-polls list-polls`; `meeting-preferences list-meeting-preferences`, `create-insert`, `update-personal-meeting-room` | `list`; `list`; `list`, (n/a), (only `list-personal-meeting-room` exists) |
| call-control | `call-controls create-dial`, `list-calls`, `show-calls` (used in 4 canonical examples, `SKILL.md:90,326,335,338`) | Split into `-me`/`-members` variants: `create-dial-me`, `create-dial-members`, `list-calls-me`, `list-calls-members`, `show-calls-me`, `show-calls-members` |
| video-mesh | `video-mesh create-clusters`, `list-availability-clusters`, `show-availability-clusters`, `show-availability-nodes` | `create` (+`create-nodes`), `list-availability`, `show-availability` |
| reporting | `cdr list-cdr`, `cdr pull` | `cdr list`, `cdr list-cdr_stream` (note the underscore — generation artifact) |
| teardown | `call-routing delete-dial-plans`, `delete-translation-patterns` | `delete` (bare = dial plans: `.../premisePstn/dialPlans/{id}`), `delete-translation-patterns-call-routing` |
| teardown | `location-voicemail list-voicemail-groups` | `location-voicemail list` |
| customer-assist | `customer-assist show-queue-recording`, `update-queue-recording`; `call-recording show-settings` | No queue-recording commands in `customer_assist`; `call_recording` has `show`, `show-call-recording`, no `show-settings` |
| org-health | `user-settings show-outgoing-permissions` | `user-settings list-outgoing-permission` (singular, list-) |
| manage-devices | `device-settings upload-a-device` | No such command |

**Total: ~45 verified dead command/group references across 14 of 24 skills.** The `-v2`/renamed
patterns indicate these were valid against an earlier generation and broke silently when the
generator's naming changed — there is no CI check that skill-cited commands exist.

### 5.3 Skills → reference docs

- **0 broken citations**: every `docs/reference/*.md` cited by any skill/agent/rule exists.
- **49 of 49 content docs are cited** by at least one skill, agent, rule, or CLAUDE.md.
  (The only uncited files are `docs/reference/CLAUDE.md` and `docs/reference/TODO.md` — meta files.)

### 5.4 Duplicate/alias surfaces skills must navigate

- `licenses` (hand-coded: `list`, `show`, `update`) **and** `licenses-api` (generated) are both
  registered. `manage-licensing/SKILL.md:84-92` builds its workflow on `licenses-api`;
  `provision-calling` references both `licenses` and `licenses-api`. `manage-licensing/SKILL.md:86`
  recommends `licenses-api update` (PATCH) with no caveat — operator experience (memory:
  `reference_licenses_api_patch_bug`) says this PATCH is broken and a raw `PUT /v1/people/{id}`
  is required; nothing in the repo documents this. Needs live verification before Phase 5 acts on it.
- `users` ↔ `people`, `cx-essentials` ↔ `customer-assist`: registered aliases (deliberate).

---

## 6. Cross-spec duplication

The generator already manages canonical ownership via per-spec `skip_tags`
(`tools/field_overrides.yaml:558-580`: e.g. Devices/Workspaces canonical in webex-device.json;
People canonical in webex-cloud-calling.json). Two duplications escape that mechanism:

1. **Wholesale ↔ BroadWorks**: `POST /subscribers/{subscriberId}/emails/consentMove` exists in
   both `webex-wholesale.json` and `webex-broadworks.json`; both generated a command
   (`broadworks_subscribers:create-consent-move` registered, `wholesale_provisioning:create-consent-move` orphaned).
2. **Flow-store surface embedded in the CC spec**: `webex-contact-center.json` contains
   `/flow-store/{orgId}/project/...` paths (tags Activities, Templates, Events — 6 ops) that
   overlap the dedicated (untracked) `webex-flow-store.json`. Because flow-store is dev-only,
   these 6 ops count as production gaps despite being "covered" by dev-only `fs-*` groups locally.

## 7. CLI groups referenced by no skill, agent, rule, or CLAUDE.md

**62 of 185 registered group names have zero references** in the skills/agent layer.
Full list in `coherence-map-data.json`. Buckets:

- **Expected/benign (25)**: 11 `fs-*` (dev-only), 4 `broadworks-*` + `cx-essentials` alias
  (partner/alias surfaces), `update` (self-update), `text-to-speech`, `archive-users`,
  `classifications`, `data-sources`, `guest-management`, `partner-admins`, `partner-tags`,
  `hybrid-clusters`, `hybrid-connectors` — no skill claims these domains today.
- **Suspicious — skill domain exists but never touches the group (22)**, e.g.:
  - `emergency-services` — CLAUDE.md's multi-skill table has an "E911 compliance" workflow and
    `docs/reference/emergency-services.md` exists, but no skill references the group.
  - `announcements`, `announcement-playlists`, `cq-playlists` — `configure-features` builds
    AA/CQ greetings but never references the announcement repository groups.
  - `virtual-line-settings` — `docs/reference/virtual-lines.md` exists, cucm-migrate provisions
    virtual lines, yet the settings group is unreferenced.
  - `mode-management` — named in CLAUDE.md Known Issue #3 but no skill uses it.
  - `recordings`, `admin-recordings` — `reporting` skill covers converged recordings but not these.
  - `caller-reputation`, `calling-service`, `client-settings`, `device-dynamic-settings`,
    `external-voicemail`, `location-call-handling`, `identity-org`, `org-settings`, `roles`,
    `resource-groups`, `resource-group-memberships`, `workspace-locations`, `mode-management`,
    `activation-email`, `admin-recordings`.
- **CC long tail (15)**: `cc-address-book`, `cc-agent-greetings`, `cc-agent-wellbeing`,
  `cc-ai-assistant`, `cc-ai-feature`, `cc-callbacks`, `cc-captures`, `cc-contact-number`,
  `cc-data-sources`, `cc-dnc`, `cc-notification`, `cc-overrides`, `cc-resource-collection`,
  `cc-summaries`, `cc-user-profiles` — the contact-center skill references 30 groups but not these.

Unreferenced ≠ wrong (the CLI legitimately exposes more than the skills teach), but each
"suspicious" entry is either a skill-coverage gap or a group that needs no skill — Phase 2 ranks them.

## 8. Builder agent & rules layer

- `.claude/agents/wxc-calling-builder.md:391` shows `wxcli locations enable-calling Y2lz...abc`
  as a worked example — **no such command exists** (`locations` has create/delete/list/show/update
  + floors). Enabling calling on a location is exactly the workflow the agent owns.
- `.claude/agents/wxc-calling-builder.md:772` correctly warns `users assign-license` doesn't exist
  and routes to `licenses-api update` — which carries the undocumented-broken-PATCH concern (§5.4).
- `.claude/agents/wxc-calling-builder.md:591` illustrates doc-vs-CLI conflict with a hypothetical
  `wxcli locations-api list` — harmless as written (it teaches `--help` verification).
- All `wxcli cucm <cmd>` references in `wxc-calling-builder.md`, `migration-advisor.md`, and
  `.claude/rules/cucm-migration.md` are **valid** (verified against the 27 actual cucm subcommands).
- `.claude/rules/` docs (`cleanup.md`, `cucm-migration.md`, `org-health.md`) have no dead CLI refs.

## 9. Skill ↔ skill group sharing (taxonomy signal)

Shared-group analysis shows a **mostly healthy** create/configure/query/delete split: feature groups
(`call-queue`, `auto-attendant`, `hunt-group`, `paging-group`, `call-park`, …) are shared by the
expected lifecycle set {configure-features, teardown, query-live, org-health, cucm-migrate}, and
infra groups (`locations`, `people`, `numbers`, `licenses`) by their natural provisioning set.
Overlaps worth Phase 2 attention:

- `call-recording` shared by customer-assist + manage-call-settings (CLAUDE.md's terminology table
  already disambiguates this — but customer-assist's queue-recording commands are dead, §5.2).
- `licenses` + `licenses-api` both referenced across manage-licensing/provision-calling (§5.4).
- `device-settings` referenced by 3 skills (device-platform, manage-call-settings, manage-devices)
  — the boundary CLAUDE.md draws between manage-devices and device-platform blurs at this group.

---

## Appendix: artifacts

- `docs/arch/coherence-map-data.json` — machine-readable: per-spec coverage, classified gaps,
  orphan modules with supersession status, verified dead references, unreferenced groups,
  per-skill dependency lists.
- Extraction/validation scripts were run from the session scratchpad; they are deterministic
  re-derivations from repo state (specs, `src/wxcli/commands/`, `main.py`, git-tracked skill files)
  and can be recreated from the method notes at the top of this document.
