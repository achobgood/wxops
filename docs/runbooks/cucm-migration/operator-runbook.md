<!-- Last verified: 2026-04-07 against branch claude/identify-missing-questions-8Xe2R, Layer 1 commits 1940991 + 3c55241 -->

# CUCM-to-Webex Operator Runbook

> **Audience:** Cisco SE with collab fluency, no prior wxops exposure, running their first CUCM-to-Webex migration.
> **Reading mode:** Read end-to-end before your first migration; section-bookmarked during execution.
> **See also:** [Decision Guide](decision-guide.md) · [Tuning Reference](tuning-reference.md)

## Table of Contents

1. [Quick Index: Where to Start](#quick-index-where-to-start)
2. [Quick Start](#quick-start)
3. [Prerequisites](#prerequisites)
   - [AXL Access](#axl-access)
   - [Webex OAuth Credentials](#webex-oauth-credentials)
   - [Webex Org Readiness](#webex-org-readiness)
   - [Local Environment](#local-environment)
   - [Partner Token Note](#partner-token-note)
   - [User Communication — Voicemail Greetings](#user-communication--voicemail-greetings)
   - [Audio Asset Preparation](#audio-asset-preparation)
   - [Call Intercept Verification](#call-intercept-verification)
4. [Pipeline Walkthrough](#pipeline-walkthrough)
   - [init](#init)
   - [discover](#discover)
   - [normalize](#normalize)
   - [map](#map)
   - [analyze](#analyze)
   - [decisions](#decisions)
   - [plan](#plan)
   - [preflight](#preflight)
   - [export](#export)
   - [execute (via /cucm-migrate)](#execute-via-cucm-migrate)
5. [Assessment Report Orientation](#assessment-report-orientation)
6. [Decision Review](#decision-review)
7. [Execution & Recovery](#execution--recovery)
   - [Calibration Data Capture](#calibration-data-capture)
8. [Failure Patterns](#failure-patterns)
9. [Glossary](#glossary)

---

## Quick Index: Where to Start

Use this index when you don't yet know which section to read first. Match
your customer's environment shape or your current question to the
"Scenario" column and start at the listed entry point.

| Scenario | Start here | Then read |
|---|---|---|
| Brand-new migration, you've never run wxops | This file's [§Quick Start](#quick-start) | This file's [§Pipeline Walkthrough](#pipeline-walkthrough) top to bottom |
| Small SMB customer (10–50 users, single location) | [tuning-reference.md §Recipe 1](tuning-reference.md#recipe-1-small-smb-single-location-1050-users) | This file's [§Quick Start](#quick-start) |
| Hunt-list / call-queue heavy (30+ hunt pilots, mixed algorithms) | [tuning-reference.md §Recipe 2](tuning-reference.md#recipe-2-hunt-list--call-queue-heavy-migration) | [decision-guide.md §feature-approximation](decision-guide.md#feature-approximation) + [§hunt-pilot-reclassification](decision-guide.md#hunt-pilot-reclassification) |
| CSS-heavy with strict partition ordering | [tuning-reference.md §Recipe 3](tuning-reference.md#recipe-3-css-heavy-customer-with-strict-partition-ordering) | [decision-guide.md §css-routing-mismatch](decision-guide.md#css-routing-mismatch) + [kb-css-routing.md](../../knowledge-base/migration/kb-css-routing.md) |
| Cert-based trunks (CCPP) | [tuning-reference.md §Recipe 4](tuning-reference.md#recipe-4-cert-based-trunk-customer) | [decision-guide.md §trunk-type-selection](decision-guide.md#trunk-type-selection) + [kb-trunk-pstn.md](../../knowledge-base/migration/kb-trunk-pstn.md) |
| Heavy analog gateway deployment | [tuning-reference.md §Recipe 5](tuning-reference.md#recipe-5-analog-gateway-heavy-customer) | [decision-guide.md §legacy-gateway-protocols](decision-guide.md#legacy-gateway-protocols) + [kb-device-migration.md](../../knowledge-base/migration/kb-device-migration.md) |
| Mid-execution failure (operation errored, partial state) | This file's [§Failure Patterns](#failure-patterns) | This file's [§Execution & Recovery](#execution--recovery) |
| Decision review confusion (don't know whether to take a recommendation) | This file's [§Decision Review](#decision-review) | [decision-guide.md](decision-guide.md) — look up the specific DecisionType |
| Score lower than expected, you don't know why | [tuning-reference.md §Score Weights](tuning-reference.md#score-weights) | This file's [§Calibration Data Capture](#calibration-data-capture) |
| Not sure if a decision should be auto-ruled | [tuning-reference.md §Non-Auto-Ruled DecisionTypes](tuning-reference.md#non-auto-ruled-decisiontypes) | [decision-guide.md](decision-guide.md) — look up the specific DecisionType |
| Customer environment doesn't match any recipe above | This file's [§Quick Start](#quick-start) | Run discover + analyze, then use [§Decision Review](#decision-review) to identify the dominant decision patterns and pick the closest recipe |

> **If your situation isn't in this index:** start with `wxcli cucm init` and `wxcli cucm discover`, then come back here once you've seen the inventory.

---

## Quick Start

This section is the minimal path for a fresh project. Read it once before you start, then use [§Pipeline Walkthrough](#pipeline-walkthrough) for detail on each stage.

**Assumed environment:** You have AXL credentials for the CUCM publisher, an active Webex Calling org with at least one location, and `wxcli` installed. You have run `wxcli configure` at least once and have a valid OAuth token loaded. See [§Prerequisites](#prerequisites) for all requirements.

> **Note:** AXL credentials are separate from the Webex OAuth token — they are passed inline to `wxcli cucm discover` (or via the `WXCLI_CUCM_*` env vars). `wxcli configure` only handles the Webex OAuth flow.

### Minimal command sequence

```bash
# 1. Authenticate and save credentials
wxcli configure

# 2. Create a new migration project (creates <project>/store.db and config.json)
wxcli cucm init <project>

# 3. Extract CUCM objects via AXL (prompts for host/credentials if not saved)
wxcli cucm discover

# 4. Run pass-1 normalizers + pass-2 cross-reference builder
wxcli cucm normalize

# 5. Run 20 transform mappers → canonical Webex objects + decisions
wxcli cucm map

# 6. Run 13 analyzers + auto-rules + merge decisions
wxcli cucm analyze

# 7. Review open decisions (Rich table; resolve interactively or via batch rules)
wxcli cucm decisions

# 8. Expand objects → operations, build dependency DAG, partition batches
wxcli cucm plan

# 9. Run preflight checks against the live Webex org
wxcli cucm preflight

# 10. Export deployment plan (JSON/CSV/markdown) for review
wxcli cucm export

# 11. Execute via the cucm-migrate skill — this is a Claude Code slash
#     command, invoke it in the session (not in your shell)
/cucm-migrate <project>
```

> **If any stage fails or produces unexpected output**, jump to [§Failure Patterns](#failure-patterns). Do not attempt to manually repair `store.db` — re-run the failed stage after correcting the underlying issue.

For what each stage does, what it reads, and what it writes, see [§Pipeline Walkthrough](#pipeline-walkthrough).

→ Command list verified against `wxcli cucm --help` (2026-04-07)

## Prerequisites

Meet all of these before running `wxcli cucm init`.

### AXL Access

- A CUCM admin account with the **AXL API Access** role assigned. Read-only AXL is sufficient for discovery; write access is not needed by this tool.
- Network reachability from your workstation to the **CUCM publisher** on **TCP 8443** (the AXL SOAP/HTTPS port). Subscriber nodes do not expose AXL by default — always target the publisher.
- AXL must be enabled on the cluster: CUCM Administration → System → Service Parameters → Publisher → Cisco AXL Web Service → Enabled.

→ AXL role and port requirements: `src/wxcli/migration/cucm/connection.py` (connection setup) and `docs/plans/cucm-pipeline/02b-cucm-extraction.md` §AXL setup.

### Webex OAuth Credentials

Run `wxcli configure` to complete the interactive OAuth flow. The CLI prompts for your token and saves it to the config file. Do not enumerate scopes manually — `wxcli configure` handles scope selection. For the full list of required `spark-admin:` scopes and token types, see [`docs/reference/authentication.md` §Calling-Related Scopes](../../reference/authentication.md#calling-related-scopes).

- If you are using a **Personal Access Token** (12-hour lifetime), re-run `wxcli configure` when it expires.
- If you are using a **Service App** token, set up the refresh loop before starting a long migration run. See [`docs/reference/authentication.md` §Service Apps](../../reference/authentication.md#service-apps).

### Webex Org Readiness

- At least **one location** exists in the target Webex Calling org.
- **License inventory** sufficient for the user count being migrated (Webex Calling Professional or equivalent). Run `wxcli manage-licensing list` to verify available seats before executing.
- **Calling is enabled** on the org. If calling is not yet activated, preflight will catch this — but it is faster to verify upfront.

→ License verification: `docs/reference/admin-licensing.md`.

### Local Environment

- **Python 3.11+** — the migration tool uses `match` statements and `tomllib` (3.11 stdlib).
- Install wxcli: `pip install -e .` from the repo root (or the published package if using a release build).
- No additional dependencies beyond those in `pyproject.toml` — no separate AXL library needed; the extractor uses raw SOAP over `requests`.

### Partner Token Note

If `wxcli whoami` shows a **"Target: \<org name\>"** line, the operator is working against the saved customer org (partner/VAR/MSP scenario). This is the correct state for multi-org deployments. If no Target line appears and you are a partner admin, run `wxcli configure` again — it detects multi-org tokens automatically and prompts for org selection. See [`docs/reference/authentication.md` §Partner/Multi-Org Tokens](../../reference/authentication.md#partnermulti-org-tokens) for the full multi-org workflow.

→ Multi-org detection logic: `docs/reference/authentication.md` §How wxcli handles partner tokens.

### User Communication — Voicemail Greetings

**Timing:** At least 1 week before migration cutover.

Custom voicemail greetings stored in Unity Connection do not migrate to Webex Calling. The assessment report (Appendix H) includes the count of affected users and a ready-to-send email template.

**Steps:**
1. Check the assessment report Appendix H for the custom greeting count
2. Copy the email template from Appendix H
3. Fill in the voicemail access number for your site
4. Send to all affected users at least 1 week before migration day

### Audio Asset Preparation

**Timing:** At least 1 week before migration day.

Before migration day, download all custom audio files from CUCM:

1. **Identify custom assets.** Run `wxcli cucm report` and check the Audio Assets appendix section (Appendix I). This lists all custom MoH sources and announcement files.
2. **Download from CUCM.** SFTP to the CUCM publisher at `/usr/local/cm/tftp/`. MoH files are typically `.wav` or `.au` format.
3. **Convert if needed.** Webex requires WAV format, max 8 MB for announcements.
4. **Upload to Webex.** Use Control Hub (Calling > Service Settings > Announcements) or the API (`POST /telephony/config/announcements`).
5. **Assign to features.** After upload, set location MoH to CUSTOM and assign announcements to AA/CQ greetings.

**Why this matters:** Custom MoH and AA greetings are customer-facing. The default Cisco hold music signals "cheap." Enterprise customers pay for professional hold music and will reject a migration that reverts to default.

### Call Intercept Verification

**Timing:** Review surfaces during Step 1c of `/cucm-migrate` (decision review) and again *post-cutover* when you hand intercept configuration back to operations. Nothing on this path blocks `preflight`, `plan`, `export`, or `execute`.

**What the pipeline does for you.** Webex Calling has a native call-intercept feature (for terminated employees, office relocations, leaves of absence, and number changes) with no CUCM equivalent. During `discover`, the `Tier4Extractor` runs two SQL queries against CUCM looking for intercept-*like* configurations: (1) DNs whose **partition name** matches `%intercept%`, `%block%`, `%out_of_service%`, or `%oos%`; and (2) DNs with `Call Forward All → voicemail` where the line has no registered phone behind it. Each match becomes an `intercept_candidate` in the store, cross-referenced to its owning user. `CallSettingsMapper` tags the user's `call_settings.intercept` metadata during Phase 05. Advisory Pattern 30 (`call_intercept_candidates`, severity `MEDIUM`, category `out_of_scope`) emits a single finding that lists all matched candidates grouped by signal type. None of it is auto-configured.

**Where you see it.** The report's Executive Summary Page 2 renders a conditional "Intercept Candidates" stat card (only when count > 0), and Appendix Y ("Call Intercept Candidates") lists each candidate with user, DN, partition, signal type, and forward destination. The advisory shows up in `wxcli cucm decisions --type advisory` and in the Phase A decision-review bundle under `/cucm-migrate`.

1. **Review the advisory during decision review.** When `/cucm-migrate` Step 1c lists advisory findings, find `call_intercept_candidates` under the `out_of_scope` bundle. Accept it — acceptance only acknowledges that you will handle the work manually post-cutover. It does not enable anything in Webex.
2. **Triage Appendix Y before cutover.** Export the report and open the Appendix Y table. For each candidate, classify the CUCM intent with the customer's directory / HR contact:
   - **Genuine intercept** — terminated employee DN, relocated office number, on-leave user. Schedule Webex intercept configuration for post-cutover.
   - **False positive — dial-plan restriction** — a "Block" partition used to enforce outbound calling rules (e.g., `BlockInternational_PT`). Those belong in Webex calling permissions, not intercept.
   - **False positive — ordinary CFA-to-voicemail** — a user whose preference happens to be "send everything to voicemail" on a spare line. No action needed.
3. **Configure Webex intercept post-cutover** for each confirmed case:
   - **Person-level:** `wxcli user-settings update-intercept <personId> --json-body '{…}'` → `PUT /people/{personId}/features/intercept`.
   - **Workspace-level:** `wxcli workspace-settings update-intercept <workspaceId> --json-body '{…}'` → `PUT /workspaces/{workspaceId}/features/intercept`. The `/features/intercept` path works on Basic and Professional workspace licenses.
   - **Location-level (entire site closure):** `PUT /telephony/config/locations/{locationId}/intercept`. Requires Professional-tier admin scopes.
   - **Virtual lines:** `PUT /telephony/config/virtualLines/{virtualLineId}/intercept`.
   - Each endpoint takes the full Webex intercept payload (`enabled`, `incoming.type`, `incoming.announcements.*`, `outgoing.type`, `outgoing.transferEnabled`, optional `destination`). Custom greeting upload is a separate endpoint: `POST /people/{personId}/features/intercept/actions/announcementUpload/invoke` (multipart `audio/wav`). See [`docs/reference/person-call-settings-media.md` § Call Intercept](../../reference/person-call-settings-media.md) for full payload shapes.
4. **Smoke-test interception.** Dial each intercepted DN from a user outside the tenant and confirm the announcement, press-0 transfer, and new-number redirect behave as designed. Re-enable Call Forward All to the voicemail pilot was a *CUCM* pattern — in Webex the correct control is `incoming.voicemailEnabled` inside the intercept payload.

**Why this matters.** The CUCM heuristic is intentionally permissive — the tool errs on the side of surfacing too many candidates rather than silently missing a terminated-user DN. If you skip this triage, terminated employees' numbers will become reachable again the moment they cut over to Webex, and office-relocation number announcements will simply stop playing. The advisory's `MEDIUM` severity reflects the operational risk of that silent failure, not how many users are typically affected (usually < 5%).

## Pipeline Walkthrough

The pipeline has 10 operator-facing stages, run in the order below. Each stage is idempotent unless noted, and each writes its output to the project's SQLite store (`<project>/store.db`) so that subsequent stages can read it. Run `wxcli cucm status` at any point to see what has already landed in the store and which decisions are open.

→ Pipeline command list and ordering: `src/wxcli/migration/CLAUDE.md:41` and `src/wxcli/commands/cucm.py:450`.

### init

**What it does:** Creates a new migration project directory in the current working directory, initializes an empty SQLite store at `<project>/store.db`, and writes a default `config.json`. → `src/wxcli/commands/cucm.py:450`

**Inputs:** A single positional argument `PROJECT_NAME`. No flags. (`wxcli cucm init --help` shows the project name as the only required argument.)

**Outputs:**
- `<project>/store.db` — empty SQLite store with the schema initialized.
- `<project>/config.json` — default config (auto-rules, advisory thresholds, batch sizes).
- Run `wxcli cucm status -p <project>` to confirm the project exists and is at the `init` stage.

**Common issues:**
- **Existing project directory.** `init` refuses to overwrite an existing `<project>/` — it errors out rather than risk clobbering prior work.
- **Wrong cwd.** `init` creates the project relative to the current working directory. Run from the directory where you want the project to live.
- **Permissions.** SQLite cannot create the store on read-only filesystems or NFS mounts that block file locking.

**When to re-run vs. investigate:** Never re-run `init` against an existing project — it will fail. If you need to reset a project, see [§Failure Patterns](#failure-patterns) for the recovery procedure (delete and re-create, or branch the project under a new name).

**See also:** [§Prerequisites](#prerequisites) for what must be in place before `init`.

### discover

**What it does:** Extracts CUCM configuration objects via AXL SOAP (live mode) or loads them from a previously captured collector file. Discovery runs all 19 extractors (users, devices, lines, CSS, partitions, route patterns, hunt pilots, voicemail, etc.) and writes raw object rows into the SQLite store. → `src/wxcli/migration/cucm/extractors/` and `src/wxcli/commands/cucm.py:583`

**Inputs:**
- **Live mode:** `--host <cucm-publisher>`, `--username <axl-admin>`, `--password <password>`. Optional: `--port` (default 8443), `--version` (auto-detected if omitted), `--wsdl <local-wsdl-path>`.
- **File mode:** `--from-file <path>` accepts `.json.gz` or `.json` collector output (e.g., from a standalone field-collector script).
- Common flags on every stage command: `-p/--project <name>` and `-v/--verbose`.
- Verified against `wxcli cucm discover --help` (2026-04-07).

**Outputs:**
- Raw object rows in `store.db` (one row per CUCM object, indexed by extractor and source XML).
- Run `wxcli cucm status -p <project>` to see per-extractor object counts.
- Run `wxcli cucm inventory -p <project>` to browse extracted objects.

**Common issues:**
- **AXL auth failure.** Wrong username/password, or the admin account is missing the **Standard AXL API Access** role. The error message comes back as a SOAP fault from CUCM.
- **AXL throttling on large clusters.** CUCM publishers under load can rate-limit AXL queries; symptoms are intermittent timeouts mid-extraction.
- **Partial extractor failures.** A single extractor (e.g., routing or SNR) failing should not halt discovery. Diagnostic logging added in commit `f1eeaf1` traces the offending object through routing/SNR extractors. → `src/wxcli/migration/cucm/extractors/routing.py`
- **Network reachability.** AXL is on TCP 8443 of the publisher only — subscribers do not expose AXL.

**When to re-run vs. investigate:** `discover` is idempotent — re-running overwrites prior raw rows for the same project, so it is safe to retry after fixing AXL credentials or network issues. If only one extractor fails, re-run with `-v` to capture the trace, then file the discrepancy as an extractor bug rather than editing `store.db` by hand.

**See also:** [§Prerequisites — AXL Access](#axl-access) for credential and port requirements; [§Failure Patterns](#failure-patterns) for AXL throttling recovery.

### normalize

**What it does:** Two passes. **Pass 1** runs 37 normalizer functions that convert raw CUCM objects (device pools, phones, users, CSS, partitions, route patterns, hunt pilots, voicemail profiles, etc.) into canonical `MigrationObject` rows. **Pass 2** runs the `CrossReferenceBuilder` which links objects together (line ↔ device, device ↔ user, route pattern ↔ partition, etc.) and stores the relationships in the `cross_refs` table. → `src/wxcli/migration/transform/normalizers.py` and `src/wxcli/migration/transform/cross_reference.py:113`

**Inputs:**
- `discover` must have run (raw object rows must exist in `store.db`).
- Flags: `-p/--project <name>`, `-v/--verbose`. (`wxcli cucm normalize --help` shows no other flags.)

**Outputs:**
- `objects` table populated with canonical `MigrationObject` rows.
- `cross_refs` table populated with object-to-object relationships.
- Run `wxcli cucm status -p <project>` to see object counts by type, or `wxcli cucm inventory -p <project>` to browse.

**Common issues:**
- **Malformed CUCM data.** A normalizer hits a field that the schema does not document or a value that violates an assumption (empty `<dirn>` block on a phone, missing partition reference, etc.). This is almost always a discover-side bug — the extractor should have caught it before the normalizer ran. Surface as a discover bug, not a normalize bug.
- **Cluster name mismatch.** Normalizers tag every canonical object with a `cluster` value (default `"default"`). Multi-cluster runs need explicit cluster IDs to avoid object collisions.

**When to re-run vs. investigate:** `normalize` is idempotent — re-run freely after fixing upstream extractor issues. If a normalizer raises an exception you cannot explain, capture the offending raw object via `wxcli cucm inventory` and treat it as a discover-stage data-quality bug.

**See also:** Cross-reference relationships and enrichments are documented at `src/wxcli/migration/transform/cross_reference.py:113`. The full normalizer list and field mapping rules live in `src/wxcli/migration/CLAUDE.md:17`.

### map

**What it does:** Runs the 20 transform mappers (announcement, button template, call forwarding, call settings, CSS, device, device layout, device profile, e911, feature, line, location, MoH, monitoring, routing, SNR, softkey, user, voicemail, workspace) that convert canonical CUCM objects into canonical Webex objects and emit `Decision` rows for any choice the pipeline cannot make on its own. Mapping is where most of the project's decisions are produced. → `src/wxcli/migration/transform/mappers/feature_mapper.py` and `src/wxcli/commands/cucm.py:788`

**Inputs:**
- `normalize` must have run.
- Flags: `-p/--project <name>`, `-v/--verbose`.

**Outputs:**
- `objects` table grows with the canonical Webex object rows the mappers produce.
- `decisions` table populates with `Decision` rows (one per choice the mapper deferred).
- Run `wxcli cucm status -p <project>` to see decision counts by severity and type.

**Common issues:**
- **Unmapped CUCM features.** Features the mapper does not know how to translate produce `MISSING_DATA` or `UNSUPPORTED_FEATURE` decisions rather than silently dropping the object.
- **Mapper failures from extractor data shape changes.** If a discover-side change adds or renames a field, a mapper may raise `KeyError` or `AttributeError`. Re-run with `-v` to see which mapper and which object.
- **Decision noise.** Mapping is the heaviest decision-producing stage. Volume is normal — `analyze` and `decisions --status pending` will help triage.

**When to re-run vs. investigate:** `map` is idempotent — re-run freely. If you see exceptions, treat them as either a data-quality issue (fix in `discover`) or a mapper bug (fix in `transform/mappers/`). Do not edit decisions in `store.db` directly.

**See also:** [Decision Guide](decision-guide.md) for the full taxonomy of decision types and how to resolve each one.

### analyze

**What it does:** Runs 13 analyzers (CSS routing, CSS permission, device compatibility, DN ambiguity, duplicate user, extension conflict, feature approximation, layout overflow, location ambiguity, missing data, shared line, voicemail compatibility, workspace license) over the canonical objects, merges new decisions with the existing set, applies auto-resolution rules, then runs the two-phase advisor system: per-decision recommendations via `populate_recommendations()` followed by the cross-cutting `ArchitectureAdvisor`. → `src/wxcli/migration/transform/analyzers/css_routing.py`, `src/wxcli/migration/transform/analysis_pipeline.py:204`, `src/wxcli/migration/advisory/__init__.py:18`, and `src/wxcli/migration/advisory/advisor.py:26`

**Inputs:**
- `map` must have run.
- Flags: `-p/--project <name>`, `-v/--verbose`.

**Outputs:**
- More `Decision` rows in the `decisions` table (analyzer-produced).
- Every decision now has populated `recommendation` and `recommendation_reasoning` fields.
- `ARCHITECTURE_ADVISORY` decisions appear, representing cross-cutting design observations from the advisor.
- Run `wxcli cucm decisions -p <project>` to see the full set or `--status pending` to see what still needs review.

**Common issues:**
- **Cascade re-evaluation.** When a decision is later resolved, `resolve_and_cascade()` re-runs only the analyzers whose decision types intersect the resolved decision's `cascades_to` context. This means resolving one decision can produce new decisions or dismiss existing ones — changes during decision review are expected, not a bug.
- **Auto-rules masking real issues.** The default `DEFAULT_AUTO_RULES` resolve common cases automatically; review `--status resolved` if you suspect over-aggressive auto-resolution.
- **Advisor dependency.** The `ArchitectureAdvisor` runs as part of `analyze`. If you see no advisories, it means none of the cross-cutting patterns matched, not that the advisor failed.

**When to re-run vs. investigate:** `analyze` is idempotent, but cascade behavior may move decisions around between runs. Re-run freely after a `map` re-run, but expect the decision set to shift if new objects entered the pipeline upstream.

**See also:** [Decision Guide](decision-guide.md) for resolution patterns; cascade mechanics in `src/wxcli/migration/transform/analysis_pipeline.py:204`.

### decisions

**What it does:** Read-only command that lists all migration decisions in a Rich table (or JSON). This is **not** a pipeline stage — it does not modify the store and does not re-run analyzers. Use it to triage open decisions before `plan`. → `src/wxcli/commands/cucm.py:1086`

**Inputs:**
- `analyze` must have run for there to be decisions worth listing.
- Flags (verified against `wxcli cucm decisions --help`):
  - `-t/--type <DecisionType>` — filter by decision type (e.g., `MISSING_DATA`, `ARCHITECTURE_ADVISORY`).
  - `-s/--severity <severity>` — filter by severity.
  - `--status pending` or `--status resolved` — filter by status; **use `--status pending` to focus on what still needs action**.
  - `--export-review` — write a markdown decision review file alongside the table.
  - `-o/--output table|json` — switch to JSON output for scripting.
  - `-p/--project <name>`.

**Outputs:**
- Rich table on stdout (default) or JSON (with `-o json`).
- With `--export-review`, a markdown review file under the project directory.
- No changes to `store.db`.

**Common issues:**
- **Noise from auto-resolved decisions.** Default output includes both pending and resolved rows. Filter with `--status pending` for the actionable set.
- **Type mis-spelling.** `--type` matches against `DecisionType` enum values exactly; check `src/wxcli/migration/models.py` for the canonical list if a filter returns nothing.

**When to re-run vs. investigate:** Run anytime — read-only and free of side effects. If a decision is missing that you expected to see, the issue is upstream in `map` or `analyze`, not here.

**See also:** [Decision Guide](decision-guide.md) for what each `DecisionType` means and how to resolve it; [§Decision Review](#decision-review) for the resolution workflow.

### plan

**What it does:** Expands the canonical Webex objects in the store into individual operations (create-user, create-location, create-device, etc.), builds a NetworkX directed acyclic graph encoding the dependency order between them, and partitions the operations into execution batches that can run in parallel within a batch but must complete in order across batches. → `src/wxcli/migration/execute/planner.py` and `src/wxcli/migration/execute/dependency.py`

**Inputs:**
- `analyze` must have run.
- All decisions must be resolved (`wxcli cucm decisions -p <project> --status pending` should return an empty set). The planner refuses to run while pending decisions exist.
- Flags: `-p/--project <name>`. (`wxcli cucm plan --help` shows no other flags.)

**Outputs:**
- `operations` table populated in `store.db`.
- `<project>/exports/plan.json` with the full DAG and batch partitioning.
- Run `wxcli cucm next-batch -p <project>` to see the first batch ready to execute, or `wxcli cucm dry-run -p <project>` to preview the full sequence.

**Common issues:**
- **Pending decisions block planning.** The planner refuses to run if any decision is still in `pending` status. Resolve all decisions in `decisions` before running `plan`.
- **Dependency cycles.** Should not happen in healthy data, but a corrupted cross-reference graph can produce a cycle. The DAG builder will raise an exception identifying the cycle.
- **Empty plan.** If `operations` is empty after a successful run, the canonical object set is empty — re-check `wxcli cucm status` and look for a missing `map` step.

**When to re-run vs. investigate:** Idempotent — re-run after resolving any newly produced decisions. If the planner reports unresolved decisions you thought were resolved, the cascade may have produced new ones; loop back to `decisions`.

**See also:** [§Decision Review](#decision-review) for resolving pending decisions; [§Failure Patterns](#failure-patterns) for cycle and empty-plan recovery.

### preflight

**What it does:** Runs 8 read-only preflight checks against the live Webex Calling org to verify the target environment can absorb the planned migration. The checks are: licenses, workspace-licenses, locations, trunks, feature entitlements, number conflicts, duplicate users, and rate-limit budget. → `src/wxcli/migration/preflight/checks.py:46`

**Inputs:**
- `plan` must have run (preflight reads from the `operations` table).
- A valid OAuth token loaded for the target Webex org (`wxcli configure` completed and `wxcli whoami` shows the right Target).
- Flags (verified against `wxcli cucm preflight --help`):
  - `-c/--check <name>` — run only one check (`licenses`, `workspace-licenses`, `locations`, `trunks`, `features`, `numbers`, `users`, `rate-limit`).
  - `--dry-run` — show what would be checked without querying Webex.
  - `-o/--output table|json` — output format (default `table`).
  - `-p/--project <name>`.

**Outputs:**
- PASS/FAIL report per check on stdout (or JSON with `-o json`).
- No changes to `store.db` and no changes to the live Webex org — preflight is strictly read-only.

**Common issues:**
- **License shortage.** `licenses` or `workspace-licenses` reports fewer available seats than the plan needs. Resolve by reclaiming licenses (`wxcli manage-licensing`) or by adding to the order before execution.
- **Location address gaps.** `locations` reports addresses missing from the target org for locations the plan expects to create. Resolve via `wxcli cucm import-locations` (CSV worksheet) before re-running.
- **Scope mismatches.** A check fails because the loaded token does not have the required scope (e.g., `spark-admin:telephony_config_write`). Re-run `wxcli configure` to refresh scopes.
- **Number conflicts.** `numbers` finds DNs in the plan that already exist in Webex under another resource. Resolve via decision review or by altering the source data.

**When to re-run vs. investigate:** Idempotent and read-only — re-run as often as you need. If a check fails for a transient reason (rate limit, network blip), re-run it with `-c <name>` rather than re-running the full preflight.

**See also:** [§Failure Patterns](#failure-patterns) for license shortage and address gap recovery; the per-check implementation logic in `src/wxcli/migration/preflight/checks.py:46`.

### export

**What it does:** Writes the migration artifacts to disk in human-readable and machine-readable formats. The default format is `deployment-plan` (a markdown summary suitable for stakeholder review); other formats produce JSON, CSV decision exports, and a CSV location worksheet for filling in addresses. → `src/wxcli/migration/export/deployment_plan.py`

> **Note:** The previous `command_builder.py` (which pre-built executable shell commands) was removed in Phase 12b. Execution is now skill-delegated via `/cucm-migrate` rather than pre-built — `export` writes review artifacts only, not runnable scripts. → `src/wxcli/migration/CLAUDE.md:24`

**Inputs:**
- `preflight` should have passed (export does not enforce this, but exporting before passing preflight gives stakeholders a misleading picture).
- Flags (verified against `wxcli cucm export --help`):
  - `-f/--format deployment-plan|json|csv-decisions|location-worksheet` — output format (default `deployment-plan`).
  - `-p/--project <name>`.

**Outputs:**
- `<project>/exports/deployment-plan.md` — human-readable summary (default).
- `<project>/exports/<...>.json` — full machine-readable export with `--format json`.
- `<project>/exports/decisions.csv` — decision register with `--format csv-decisions`.
- `<project>/exports/location-worksheet.csv` — fillable address worksheet with `--format location-worksheet` (consumed by `wxcli cucm import-locations`).

**Common issues:**
- **Nothing structural.** This is a write-out step; failures here almost always mean a permission issue on the `<project>/exports/` directory or a missing earlier stage.
- **Stale exports.** Re-running an upstream stage (`map`, `analyze`, `plan`) does not auto-regenerate exports — you must re-run `export` to refresh the markdown plan.

**When to re-run vs. investigate:** Idempotent and safe — re-run after any upstream change. If a format produces an empty file, the underlying store is empty for that data type; investigate the upstream stage rather than the exporter.

**See also:** [§Assessment Report Orientation](#assessment-report-orientation) for how the exported deployment plan maps to the assessment report; [§Decision Review](#decision-review) for using the CSV decision register during review.

### execute (via /cucm-migrate)

**What it does:** Executes the planned migration against the live Webex org. The skill at `.claude/skills/cucm-migrate/SKILL.md` is invoked by Claude Code when the operator types `/cucm-migrate <project>` — it is the **only** supported execution path. There is no `wxcli cucm execute` direct invocation for the full migration; the underlying `wxcli cucm execute` (and the granular `next-batch` / `mark-complete` / `mark-failed` commands) exist but are designed to be driven by the skill, not run by hand. → `.claude/skills/cucm-migrate/SKILL.md`

**Inputs:**
- `export` must have run; the deployment plan and store are the skill's inputs.
- A **fresh Claude Code session** is preferred — the skill expects to drive the conversation from a clean state.
- A loaded OAuth token with execution-grade scopes for the target Webex org.

**High-level skill flow (6 steps):**
1. **Load** — read project state from `<project>/store.db` and validate it is at the post-export stage.
2. **Preflight** — re-run preflight checks just-in-time before any writes.
3. **Plan summary** — present the operator with batch counts, license consumption, and risk highlights.
4. **Batch execute** — process operations one batch at a time, marking each operation complete or failed in the store as it lands.
5. **Delegate** — hand off complex per-stage work (decision review, advisory presentation) to the migration-advisor agent where appropriate.
6. **Report** — produce a final execution report summarizing what landed, what failed, and what remains.

**Outputs:**
- Updated `operations` table with `completed`/`failed` status for every operation.
- A final execution report (markdown).
- Live changes in the target Webex org.

**Common issues:**
- **Mid-execution failures.** A single operation failing should not halt the run — the skill marks the operation `failed` and continues with the rest of its batch (subject to dependency rules). See [§Failure Patterns](#failure-patterns) for the recovery procedure (`wxcli cucm retry-failed` then re-invoke the skill).
- **Token expiry mid-run.** A 12-hour PAT can expire during a long migration. Use a Service App token for runs over a few hours.
- **Webex rate limits.** The skill respects the rate-limit budget computed during preflight. If you see throttling, the budget calculation needs tuning; do not raise concurrency by hand.

**When to re-run vs. investigate:** Re-running `/cucm-migrate <project>` picks up from the last successful operation — completed operations are not re-attempted. Failed operations are not retried automatically; you must explicitly run `wxcli cucm retry-failed` to reset them to `pending` first. If the same operation fails repeatedly, investigate the underlying API error (see [§Failure Patterns](#failure-patterns)) rather than retrying blindly.

**See also:** [§Execution & Recovery](#execution--recovery) for the full recovery playbook; [§Failure Patterns](#failure-patterns) for symptom-to-cause mapping.

## Assessment Report Orientation

The assessment report is a self-contained HTML/PDF artifact generated by `wxcli cucm report --brand "..." --prepared-by "..."` after the pipeline reaches ANALYZED. It reads directly from the post-analyze SQLite store (no `plan`/`preflight`/`export` required) and is designed to be handed to the customer. Output lands in the project directory as `assessment-report.html` (and `assessment-report.pdf` if `--pdf` is passed). Use it as your customer-facing artifact and your own pre-flight read before committing to a migration date.

### The Report: What's In It

**4 executive pages** (→ `src/wxcli/migration/report/executive.py`):

1. **Migration Complexity Assessment** — tier-colored gauge, factor bars (sorted, highest in teal), key findings, stat grid. → `_page_verdict` at `executive.py:85`
2. **What You Have** — People / Devices (with compatibility donut) / Features / Sites. → `_page_environment` at `executive.py:173`
3. **What Needs Attention** — decision stats and effort bands (auto / planning / manual). → `_page_scope` at `executive.py:334`
4. **Next Steps** — prerequisites, planning, and a CTA box. → `_page_next_steps` at `executive.py:458`

**22 appendix sections A–V** (→ `src/wxcli/migration/report/appendix.py:35`, `generate_appendix`). Each section renders as a collapsed `<details>` element so the customer can expand only what they care about. Appendices A–V cover: object inventory, decision detail, CSS/partitions, devices, DN analysis, user/device map, routing, voicemail, data coverage, gateways, call features, button templates, device layouts, softkeys, cloud-managed resources, feature gaps, manual reconfiguration, planning inputs, recording, SNR, caller-ID transformations, and extension mobility. Empty sections are filtered out before render, so a small customer may see fewer than 22. For detail on a specific section, expand the `<details>` element in the report.

### The 8 Score Factors

The complexity score is computed from 8 weighted factors that sum to 100 (→ `src/wxcli/migration/report/score.py:WEIGHTS` at line 17). Use these to understand *why* a score landed where it did — the factor bars on Page 1 are sorted descending, so the top bar is the dominant driver.

The factors carry two names: the **internal name** (used in code, logs, and operator tooling) and the **customer-facing display name** (rendered in the report). When explaining the report to a customer, use the display name; when grepping source or filing bugs, use the internal name.

| Internal name | Display name (in report) | Weight | What it measures |
|---|---|---:|---|
| CSS Complexity | Calling Restrictions | 20 | Partition/CSS depth, cross-CSS references, CSS-per-phone counts. |
| Feature Parity | Feature Compatibility | 17 | CUCM features with no Webex equivalent (SNR, EM, intercom variants, custom softkeys). |
| Device Compatibility | Device Readiness | 15 | Mix of native-MPP vs. convertible vs. incompatible endpoints; hardware refresh cost proxy. |
| Decision Density | Outstanding Decisions | 15 | Pending `Decision` rows per 100 users — how much judgment is still unresolved post-analyze. |
| Scale | Scale | 10 | Raw object counts (users, devices, lines, sites). |
| Shared Line Complexity | Shared Lines | 10 | Shared DN appearances, cross-device shared lines, bridged-line group depth. |
| Phone Config Complexity | Phone Configuration | 8 | Per-line services, speed dials, BLF pickups, non-default button/softkey templates. |
| Routing Complexity | Routing | 5 | Translation patterns, route list depth, trunk fan-out. |

→ Display names live at `src/wxcli/migration/report/score.py:DISPLAY_NAMES` (line 28). Update both `WEIGHTS` and `DISPLAY_NAMES` if you rename a factor.

**Calibration status:** `SCORE_CALIBRATED = False` (→ `src/wxcli/migration/report/score.py:50`). When this flag is False, the report renders an UNCALIBRATED disclaimer above the key findings on Page 1 (→ `executive.py:127-135`): *"This complexity score uses design-time weights that have not yet been calibrated against completed migrations. Use as a relative indicator, not an absolute measure."* Treat the number as a direction, not a verdict. See [§Calibration Data Capture](#calibration-data-capture) below for what to log during your migration so the flag can flip to True.

Tier thresholds (→ `score.py:LABEL_THRESHOLDS`): **0–30 Straightforward (green)**, **31–55 Moderate (amber)**, **56–100 Complex (red)**.

### "Should I Migrate This Customer?" — Operator Heuristics

These are operator heuristics grounded in the score weights above — not pipeline output. Use them as a pre-flight checklist before quoting a migration.

| # | Signal | What it means |
|---|---|---|
| 1 | **Score ≥ 56** (Complex tier, red) | Have a migration-scope conversation with the customer before quoting. This is not "no-go" — it's "don't pretend it's a copy-paste." |
| 2 | **Any CRITICAL advisory** | Block until resolved. CRITICAL advisories are migration-killers, not paper cuts; no amount of operator judgment routes around them. |
| 3 | **Decision Density factor > 70** | More pending judgment calls than a single review session can absorb. Plan to split decision review into two waves and set customer expectations accordingly. |
| 4 | **Device Compatibility factor > 60** | Hardware refresh cost is material. Surface to customer procurement *early* — lead times on 9800-series / MPP swaps will dominate the critical path. |
| 5 | **Feature Parity factor > 60** | At least one CUCM feature will not survive the migration. Needs explicit customer sign-off on what gets retired vs. manually reconfigured in Webex. |
| 6 | **`SCORE_CALIBRATED = False`** | Treat the score as a direction, not a number. Favor reading appendices B (decisions), P (feature gaps), and Q (manual reconfiguration) over trusting the headline gauge. |

When three or more of these fire at once, stop and escalate to a solution-architect review before committing to a date. The score is there to surface the conversation, not to make the decision for you.

### Per-User Diff (Pre-Execution Verification)

Before executing the migration, generate a per-user diff to verify the planned changes:

```bash
wxcli cucm user-diff                              # HTML with all changed users
wxcli cucm user-diff --format csv                 # CSV for Excel review
wxcli cucm user-diff --user "user:jsmith"         # spot-check one user
wxcli cucm user-diff --location "loc:dallas-hq"   # verify one site
```

The diff shows each user's CUCM state vs. planned Webex state side by side: device model/tier, call forwarding rules, voicemail, BLF keys, speed dials, shared lines, button layout, calling permissions, and any decisions that affect that user. Use this to spot-check a representative sample before pressing go.

## Decision Review

Decision review is Step 1c of the `cucm-migrate` skill. It runs after the pipeline has produced static recommendations for every discovered entity. The operator works alongside Claude (acting as migration-advisor) to accept, reject, skip, or override each recommendation before anything is provisioned. Nothing is committed to Webex until review is complete and you approve the final plan.

### How `cucm-migrate` Invokes the Advisor

At Step 1c, `cucm-migrate` spawns the `migration-advisor` agent (Opus model, `bypassPermissions`) with a review-mode prompt. The agent reads the migration narrative from `<project>/exports/migration-narrative.md`, loads the static recommendations from the pipeline, and presents two review phases in sequence.

→ `.claude/skills/cucm-migrate/SKILL.md:152` — Step 1c definition and agent spawn parameters.

### Phase A: Architecture Advisories

Phase A presents `ARCHITECTURE_ADVISORY` decisions grouped by category before any per-entity review begins. The categories are `ELIMINATE` (CUCM workarounds to remove), `REBUILD` (patterns that need redesign in Webex), `OUT_OF_SCOPE` (items outside the migration boundary), and `MIGRATE_AS_IS` (safe to carry forward unchanged). For each group, the advisor presents a 2–3 sentence narrative connecting the advisory to your specific migration, then lists the individual advisories within it.

The operator can accept a whole group ("accept all ELIMINATE advisories") or drill into individual items. Accepting means the recommended action will be applied in planning. Rejecting flags the advisory for manual follow-up. Architecture advisories shape the framing of Phase B — resolve them before proceeding.

→ `.claude/agents/migration-advisor.md:136` — Review Mode, Phase A presentation protocol.

### Phase B: Per-Decision Review

Phase B works through every non-auto-resolved decision one at a time. For each decision the advisor presents: the entity being decided (device, user, feature, etc.), the static recommendation and its confidence level, any KB entry the static heuristics cited, and — when there is a dissent flag — the advisor's competing view with CCIE-level explanation.

At each prompt the operator chooses one of:

- **accept** — take the static recommendation as-is
- **reject** — reject and override with a manual choice (advisor prompts for the alternative)
- **skip** — defer this entity; it will not appear in the deployment plan
- **override** — accept the advisory's dissent recommendation instead of the static one
- **bulk-accept** — accept all remaining decisions of this `DecisionType` in one step (only offered when the advisor's confidence is HIGH for every remaining instance)

For any specific decision type and what each choice means, look it up in [decision-guide.md §Decision Types A–Z](decision-guide.md#decision-types-az).

### Dissent Flags

A dissent flag appears when the migration-advisor disagrees with the static recommendation. The static system applies `recommendation_rules.py` mechanically; the advisor applies CCIE-level reasoning and may reach a different conclusion. A dissent looks like:

```
⚠ DISSENT [DT-DEVICE-003]: Static recommendation is CONVERT. Advisory: REPLACE.
Reason: This model's SIP firmware path has known CFB issues on Webex Calling 44.x.
Confidence: HIGH
```

The `DT-{DOMAIN}-NNN` code identifies the KB entry the advisor is citing. Do not dismiss dissents without reading the reason — HIGH-confidence dissents from the advisor are more often right than the static rule when edge-case conditions are present.

For what each confidence level means and when to trust the dissent over the static recommendation, see [decision-guide.md §Dissent Handling](decision-guide.md#dissent-handling).

### Auto-Resolved Decisions

Seven decision types are pre-resolved by `DEFAULT_AUTO_RULES` and never appear in the interactive review at all:

| DecisionType | Auto-choice | Rationale |
|---|---|---|
| `DEVICE_INCOMPATIBLE` | skip | No migration path exists |
| `DEVICE_FIRMWARE_CONVERTIBLE` | convert | Firmware flash is always safe |
| `HOTDESK_DN_CONFLICT` | keep_primary | Primary DN wins by definition |
| `FORWARDING_LOSSY` | accept_loss | CUCM-only variant, rarely configured |
| `SNR_LOSSY` | accept_loss | Webex simplification is acceptable |
| `BUTTON_UNMAPPABLE` | accept_loss | No Webex equivalent exists |
| `CALLING_PERMISSION_MISMATCH` (0 users) | skip | Orphaned profile, no impact |

Source: `src/wxcli/commands/cucm_config.py:17` — `DEFAULT_AUTO_RULES`. These rules can be removed or reconfigured per project; see [tuning-reference.md §Auto-Rule Reference](tuning-reference.md#auto-rule-reference).

### When to Break the Review

In almost all cases, issues surfaced during review are fixable inside review — override the recommendation, adjust a choice, or skip and handle manually after migration. **Breaking the review to re-run an upstream stage is rare and disruptive.**

Break the review and re-run only when:

- Discovery data was incorrect (wrong CUCM cluster, missing AXL scope, or incomplete export) — the root data is wrong, not the recommendations
- The normalize or map stage produced systematically incorrect output that cannot be corrected decision-by-decision

Do not break the review for: wrong recommendations on individual entities (use override), missing E911 addresses (fix in the address resolution step, not by re-running), or high decision counts (use bulk-accept).

### See Also

- Per-DecisionType reference: [decision-guide.md §Decision Types A–Z](decision-guide.md#decision-types-az)
- Dissent handling detail: [decision-guide.md §Dissent Handling](decision-guide.md#dissent-handling)
- Auto-rule tuning: [tuning-reference.md §Auto-Rule Reference](tuning-reference.md#auto-rule-reference)
- Failure recovery: [§Failure Patterns](#failure-patterns)

## Execution & Recovery

Execution runs through the `/cucm-migrate` skill — not by issuing `wxcli cucm execute` directly. The skill handles the full lifecycle: dry-run preview, admin confirmation, bulk async execution, failure triage, and post-execution report generation. See `## Execute via /cucm-migrate` above for the stage-level walkthrough. This section covers the status commands, failure handling patterns, and recovery procedures operators need during and after that stage.

### How Execution Runs

When the skill reaches Step 4b, it calls `wxcli cucm execute --concurrency 20`. This triggers a bulk async executor (`→ src/wxcli/migration/execute/batch.py`) that processes all pending operations in dependency order, concurrently at API throughput (~100 req/min). Operations are grouped into batches — each batch runs after all operations in the prior batch have completed or been skipped. Claude is not involved during active execution; it re-enters only when the skill checks `execution-status` and finds failures.

Operations are recorded in the migration SQLite store with status `pending` → `running` → `completed` or `failed`. The `<project>/exports/` directory holds per-run JSON and CSV artifacts generated at report time.

### Execution Status Commands

Use these commands to observe state and intervene manually when the skill prompts you, or when you are diagnosing a migration outside of an active skill session.

| Command | What it does |
|---|---|
| `wxcli cucm execution-status -p <project>` | Show current batch state and per-operation status counts (pending / running / completed / failed) |
| `wxcli cucm execution-status -p <project> -o json` | Full JSON output — use this for failure triage; shows per-operation error messages |
| `wxcli cucm next-batch -p <project>` | Show the next batch of operations whose dependencies are all completed/skipped — ready to run |
| `wxcli cucm mark-complete <node-id> -p <project>` | Manually mark an operation as completed; optionally pass `--webex-id <id>` to record the created resource ID for downstream dependency resolution |
| `wxcli cucm mark-failed <node-id> --error "<message>" -p <project>` | Manually mark an operation as failed (does NOT cascade). Required before retry. Add `--skip` to cascade the failure to all dependent operations (use only when the resource is genuinely not needed) |
| `wxcli cucm retry-failed -p <project>` | Reset all failed operations to `pending` so they can be retried on the next `execute` run |
| `wxcli cucm rollback-ops -p <project>` | List all completed CREATE operations in reverse dependency order — the sequence you'd need to delete to roll back. Use `--batch <name>` to scope to a single batch |

**Flags are positional or named — do not guess.** `mark-complete` and `mark-failed` take `node_id` as a required positional argument, not `--operation-id`. Verify with `wxcli cucm mark-failed --help` if unsure.

### Mid-Execution Failure Handling

When `execution-status` shows failed operations:

1. Run `wxcli cucm execution-status -p <project> -o json` to read the error message for each failed operation.
2. Diagnose the root cause using the skill's domain dispatch table (SKILL.md Step 4c). The error message usually points to: rate limiting (retry immediately), conflict/409 (check for existing resource — partial create), auth failure (token expiry — renew and retry), or a data issue (fix upstream, re-run).
3. For each failed operation, either fix the root cause or decide to skip:
   - Fix + retry: `wxcli cucm mark-failed <node-id> --error "<reason>" -p <project>` (marks as failed, retainable), then `wxcli cucm retry-failed -p <project>` to reset to pending, then `wxcli cucm execute -p <project>` to resume.
   - Skip + cascade: `wxcli cucm mark-failed <node-id> --error "<reason>" --skip -p <project>` — this marks the op skipped and propagates the skip to all dependent operations. Use only when the resource is intentionally not needed.
4. After all failures are resolved, run `wxcli cucm execute` again. Repeat until `execution-status` shows 0 failed, 0 pending.

See `§Failure Patterns` below for specific recipes by failure type.

### Partial-Create Recovery

The most common mid-execution failure is a partial user create: the Webex People API creates the user record but fails on calling setup (license assignment, extension, location binding). The resource exists in Webex — a retry will get a 409 conflict.

Recovery procedure (from SKILL.md Step 4c and roadmap `26419ab`):
1. Check whether the user already exists: `wxcli people list --email <email> -o json`.
2. If the user exists but is not calling-enabled: update with calling data using `wxcli people update <id> --json-body '{"locationId": ..., "extension": ..., "licenses": [...]}'`.
3. Mark the original operation complete with the existing user's ID: `wxcli cucm mark-complete <node-id> --webex-id <user-id> -p <project>`.
4. Continue execution normally.

If the user does NOT exist, it was a genuine failure — present fix+retry or skip options.

This pattern applies to any create operation (locations, call queues, hunt groups) where the API is not atomic. Always check for the existing resource before retrying. See `→ docs/plans/cucm-migration-roadmap.md` Known Issues table (commit `26419ab` upstream data gaps) for the full history.

### Where Logs Live

`<project>/exports/` holds operation records (JSON and CSV) generated at report time. Live operation state is in the migration SQLite store — query it via `wxcli cucm execution-status -p <project>` for the human-readable summary, or `-o json` for full per-operation detail.

### When to Abort Entirely

Aborting entirely — stopping mid-migration, tearing down, and restarting — is rare and should only happen when a structural issue makes fix-forward impractical:

- **Wrong target org.** Resources are being created in the wrong Webex organization. Stop immediately; tearing down is easier now than later.
- **Wrong license tier.** Professional licenses were assumed but only Standard are available. Continuing will misconfigure users — stop, resolve licenses, then replay from plan.
- **Catastrophic data drift.** The CUCM source changed significantly after discovery (a phone remap, a location rename) and the canonical store no longer reflects reality. Restart from `wxcli cucm discover`.

For everything else — rate limits, transient 500s, single-resource conflicts, missing extensions — fix forward using `mark-failed` / `retry-failed`. Tearing down a partial migration and restarting costs more time than diagnosing the failure. When in doubt, check `execution-status -o json`, identify the specific failure, and fix it.

### Calibration Data Capture

> **Why this exists.** `SCORE_CALIBRATED = False` (→ `src/wxcli/migration/report/score.py:50`). The migration complexity score in `wxcli cucm report` is a direction, not a validated number — it was built on structural heuristics before any real environments were tested. Calibration is a separate workstream that requires real-environment data. This section tells you what to log during your migration so that data can exist. The methodology for turning logs into calibrated scores lives elsewhere; your job here is to capture.

**What to log.** Create a file at `<project>/calibration-log.md` and fill in the following fields as you go. This is a manual log — nothing in the pipeline writes to it automatically.

---

#### Score vs Actual Effort

Record immediately after the migration closes:

- **Headline score.** The overall complexity score and band (Low / Medium / High / Very High) from `wxcli cucm report --brand "..." --prepared-by "..."`. Copy the exact numbers.
- **Actual hours.** Elapsed wall-clock time broken into: decision review (Step 3) / execution + triage (Step 4) / cleanup and verification (Steps 5–6). Round to half-hours.
- **Environment characteristics.** Size (user count, device count, location count), device mix (MPP-convertible % / native MPP % / incompatible %), feature complexity (number of auto attendants, hunt groups, call queues, trunks). These are the factors the score uses — recording them lets you later check which ones predicted effort and which didn't.
- **Any score anomalies.** If the score said Medium but the migration took twice as long as a prior High, note why. This is the most valuable signal for calibration.

#### Decision Counts vs Resolution Time

Record at the end of decision review (Step 3):

- **Pending decision counts at review start.** How many decisions were in each status: `PENDING` / `ADVISORY` / `MISSING_DATA` / `CONFLICT`.
- **Review duration.** Wall-clock time from first `wxcli cucm decisions` to issuing `wxcli cucm export`.
- **Bulk accept count vs individual review count.** How many decisions did you accept/reject in bulk (same decision type, same recommendation)? How many required individual inspection?
- **Decision types that required the most time.** Which `decision_type` values caused the most discussion or lookup? (e.g., `DEVICE_FIRMWARE_CONVERTIBLE`, `HUNT_GROUP_MEMBER_LIMIT`, `CSS_PARTITION_DEPTH`).

#### Advisory Firing Rates vs Perceived Value

Record during and after decision review:

- **Which advisory patterns fired.** List the `advisory_pattern` codes shown in the ADVISORY decisions (visible in `wxcli cucm decisions --type ARCHITECTURE_ADVISORY`).
- **Which were useful.** For each advisory: did it surface a real issue you would have missed? Did it change a decision you would have made differently?
- **Which were noise.** Advisories that fired but were irrelevant to this environment — either because the heuristic doesn't apply to this customer's feature profile, or because the threshold was too low.
- **Any false negatives.** Issues you encountered during execution that no advisory flagged.

---

**Where the data goes next.** This is a manual log for now — no automation collects it. Feed the completed `calibration-log.md` to the score-calibration workstream when it opens. The methodology lives elsewhere; your job is to make the data exist.

For context on what the score is measuring and which factors drive each band, see `§Assessment Report Orientation` above.

## Failure Patterns

The `/cucm-migrate` skill handles most failures automatically: it marks the failed operation, continues with independent operations in the same batch, and surfaces a recovery decision to you only when human judgment is required (see [§Execution & Recovery](#execution--recovery) for the general flow). This section maps symptom → cause → recovery for the seven patterns where the skill requires operator action or where the recovery path is non-obvious.

### Pattern 1: Partial Create

**Trigger:** One or more operations in a batch succeeded before a subsequent operation failed. The plan now has a mix of `completed` and `failed` status rows. Most common after a rate-limit burst, a token expiry mid-batch, or a transient Webex API error.

**Symptoms:** `wxcli cucm execution-status -p <project>` shows rows with `status: failed` alongside rows with `status: completed`. The failed row's `error` field contains the raw API error message.

**Recovery:**
1. Identify the root cause from the error field — rate limit, auth, or a data problem.
2. Fix the root cause (e.g., refresh the token, correct the plan JSON for a data problem).
3. Reset failed operations to `pending`: `wxcli cucm retry-failed -p <project>`
4. Re-invoke `/cucm-migrate <project>`. The skill resumes from the reset operations; completed operations are not re-attempted.
5. If the same operation fails again repeatedly, escalate to the 409 Conflict or Mid-Execution Failures patterns below.

See the skill's recovery decision logic at → `.claude/skills/cucm-migrate/SKILL.md:566` (`### 4c. Error handling`).

**Customer communication:** "A subset of objects failed to create during the initial run; we've diagnosed the cause and are re-running the affected operations now."

---

### Pattern 2: 409 Conflict

**Trigger:** A Webex API `POST` returns `409 Conflict` because the target resource already exists. Most common after a partial run was interrupted before the skill could record the created IDs, leaving Webex ahead of the migration store.

**Symptoms:** Execution log shows `409 Conflict` on a create operation. The operation remains `failed` after `retry-failed` because the resource already exists.

**Recovery:**
1. List what was previously created: `wxcli cucm rollback-ops -p <project>` (shows completed CREATE ops in reverse dependency order). Add `--batch <name>` to scope to a single batch.
2. Search for the conflicting resource: `wxcli [resource] list --name "<name>" -o json` to find its Webex ID.
3. Choose one of two paths:
   - **Resource matches the plan:** Record it as complete — `wxcli cucm mark-complete <node_id> -p <project> --webex-id <webex_id>`. The migration advances past the stuck point.
   - **Resource is stale/incorrect:** Delete it — `wxcli cleanup run --scope "Location Name" --dry-run` first, then without `--dry-run`. After deletion, `wxcli cucm retry-failed -p <project>` and re-invoke the skill.

See the 409 recovery branch at → `.claude/skills/cucm-migrate/SKILL.md:566` (`### 4c. Error handling`, first block).

**Customer communication:** "Some objects already existed in the Webex org from a prior run; we've reconciled them and are continuing the migration."

---

### Pattern 3: Preflight Failures

**Trigger:** `wxcli cucm preflight -p <project>` reports one or more `FAIL` rows before execution begins. Execution should not start until all preflight checks pass.

**Symptoms:** Preflight output table contains rows with `result: FAIL`. Each row identifies the check name and a short reason.

**Recovery:** Map the failing check to its fix:

| Check | Fix path |
|-------|----------|
| `licenses` — insufficient Webex Calling licenses | Acquire additional licenses in Control Hub, then re-run preflight. For sizing guidance see [tuning-reference.md §Recipe 1](tuning-reference.md#recipe-1-small-smb-single-location-1050-users). |
| `locations` — address gap or location not calling-enabled | Complete Webex org readiness steps: [§Prerequisites — Webex Org Readiness](#webex-org-readiness). |
| `users` — duplicate users or number conflicts | Resolve duplicates manually; see `wxcli people list --email <email>` to identify conflicts. |
| `numbers` — number already claimed | Release or port the number in Control Hub before re-running. |
| `rate-limit` | Wait for the rate-limit window to expire (typically 60 s), then re-run preflight. |
| OAuth scope mismatch (403 on any check) | Re-authenticate with the correct scopes: [§Prerequisites — Webex OAuth Credentials](#webex-oauth-credentials). |

After fixing, re-run `wxcli cucm preflight -p <project>` to confirm all checks pass before invoking `/cucm-migrate`.

**Customer communication:** "The pre-migration checks found [describe issue] — we need to resolve this in your Webex org before we can proceed."

---

### Pattern 4: Mid-Execution Failures

**Trigger:** A `wxcli cucm` command or Webex API call fails during batch execution for a reason the skill cannot auto-recover (timeout cascade, unexpected 500, dependency cycle, malformed plan JSON).

**Symptoms:** The skill surfaces a recovery decision to you during execution with options: fix-and-retry, skip, rollback batch, or rollback all. The batch halts at the failed operation.

**Recovery:** The `cucm-migrate` skill handles most mid-execution failures automatically — it diagnoses the error and proposes the appropriate recovery path at → `.claude/skills/cucm-migrate/SKILL.md:566` (`### 4c. Error handling`). That section is the source of truth; this pattern is for the cases where the skill surfaces a decision to the operator.

Operator decision tree:
- **Transient error (timeout, rate limit):** Choose fix-and-retry. The skill resets the failed op and continues.
- **Data error (malformed field, invalid reference):** Fix the plan (edit `store.db` or re-run the affected pipeline stage), then retry.
- **Dependency cycle:** Run `wxcli cucm execution-status -o json -p <project>`, identify the cycle, and use `mark-failed <node_id> --error "cycle" --skip -p <project>` to break it.
- **Unrecoverable:** Choose rollback all and file a support case with the full execution log from `~/.wxcli/migrations/<project>/logs/`.

**Customer communication:** "We encountered an unexpected error mid-execution; we're evaluating whether to retry or roll back the affected batch."

---

### Pattern 5: Orphaned Non-Calling User

**Trigger:** The People API created the Webex user record successfully, but the subsequent calling-setup step failed, leaving a Webex user with no calling license or extension. A retry gets `409 Conflict` on the user create because the user already exists. Documented in `docs/plans/cucm-migration-roadmap.md:459`.

**Symptoms:** Execution log shows user create succeeded (HTTP 200 with a `personId`) but the following calling-assign step shows a 400 or 500. `wxcli cucm execution-status -p <project>` shows the user op as `failed`. `wxcli people list --email "<email>" --calling-data true -o json` returns the user but with no `phoneNumbers` or `extension` fields.

**Recovery:**
1. Confirm the user exists without calling: `wxcli people list --email "<email>" --calling-data true -o json`
2. Update the user to add calling: `wxcli people update <person_id> --calling-data true --json-body '{"extension":"<ext>","locationId":"<loc_id>"}'`
3. If the update succeeds: `wxcli cucm mark-complete <node_id> -p <project> --webex-id <person_id>`
4. If the update fails: surface the error to the admin and determine whether the location or license is the underlying issue, then retry.
5. If the user already has calling configured: the skill already recovered it — `wxcli cucm mark-complete <node_id> -p <project> --webex-id <person_id>` to advance past the stuck op.

The full recovery branch for this specific scenario is at → `.claude/skills/cucm-migrate/SKILL.md:566` (`### 4c. Error handling`, "IF 400/500 on user:create" block).

**Customer communication:** "One or more users were created in Webex but their calling settings weren't applied; we're completing the calling setup now."

---

### Pattern 6: Discovery Data Drift Mid-Migration

**Trigger:** A CUCM admin modified the source environment during the migration window — added a phone, renamed a CSS, deleted a route pattern, or changed a DN assignment — after `wxcli cucm discover` ran but before execution completed. The migration plan now references objects that no longer exist or have changed.

**Symptoms:** Execution fails with 404s on objects that should exist, or attempts to create resources that conflict with new CUCM objects not in the original plan. Error messages reference resource names or IDs that don't match the current CUCM state.

**Recovery:**
1. Stop the `/cucm-migrate` skill immediately — do not retry until the data is reconciled.
2. Identify the scope of drift: compare the failed operation's source data against current CUCM state (AXL query or CUCM admin UI).
3. For a small drift (1-2 objects): edit the migration store directly (`wxcli cucm decisions` to inspect, manual `store.db` edits for plan JSON corrections), then `wxcli cucm retry-failed -p <project>`.
4. For large drift (multiple changed objects): re-run the affected pipeline stages on the changed slice — `wxcli cucm discover → normalize → map → analyze` — then manually reconcile the diff against the in-flight plan before resuming execution.
5. For production migrations: negotiate a **change freeze** with the CUCM admin covering the full migration window before starting. Document this in your pre-migration checklist.

**Customer communication:** "Changes were made to the CUCM system during the migration window; we need a change freeze in place before we can safely continue."

---

### Pattern 7: Advisor Agent Unavailable

**Trigger:** The `migration-advisor` agent (Opus) fails to launch during decision review — Claude Code is not running, the agent definition is missing, the agent times out, or the model is unavailable.

**Symptoms:** The `/cucm-migrate` skill logs a fallback message and proceeds to static decision review without producing a `migration-narrative.md` or dissent flags. The per-decision recommendations are still present but lack narrative context and cross-decision analysis.

**Recovery:** The skill handles this automatically. It falls back to the static review flow at → `.claude/skills/cucm-migrate/SKILL.md:183` (`### Step 1c-fallback: Static Decision Review`). No operator action is required to continue the migration.

To obtain the advisory layer retroactively:
1. Ensure Claude Code is running and the `migration-advisor` agent definition exists at `.claude/agents/migration-advisor.md`.
2. Re-invoke `/cucm-migrate <project>` — the skill will detect the project is past the discovery stages and re-enter at decision review, this time with the advisor available.
3. Review any dissent flags that appear on the second pass; the static recommendations remain valid as a baseline.

**Customer communication:** "Decision review proceeded without the AI advisory layer; we'll do a second-pass review of the dissent flags before finalizing the plan."

## Glossary

- **Decision** — a `Decision` row representing a choice the pipeline cannot make alone. → `src/wxcli/migration/models.py:141`
- **Advisory** — an `ARCHITECTURE_ADVISORY` decision produced by `ArchitectureAdvisor`, spans multiple objects. → `src/wxcli/migration/models.py:89`
- **Recommendation** — the `recommendation` field on a Decision; populated by `populate_recommendations()`. → `src/wxcli/migration/advisory/__init__.py:18`
- **Dissent** — a flag from the `migration-advisor` agent disagreeing with the static recommendation, grounded in a `DT-{DOMAIN}-NNN` KB entry. → `.claude/agents/migration-advisor.md`
- **Cascade** — re-evaluation of dependent decisions after one is resolved. → `src/wxcli/migration/transform/analysis_pipeline.py:204`
- **Fingerprint** — content-hash of a Decision used to detect when it has gone stale across re-runs. → `src/wxcli/migration/models.py:155`
- **Stale** — a Decision whose source object has changed since the decision was first produced. → `src/wxcli/migration/models.py:44`
- **Mapper** — a function in `transform/mappers/` that converts CUCM objects to canonical Webex objects + decisions. → `src/wxcli/migration/transform/mappers/feature_mapper.py`
- **Analyzer** — a function in `transform/analyzers/` that produces decisions from canonical objects (linter pattern). → `src/wxcli/migration/transform/analyzers/css_routing.py`
- **Advisor** — the `migration-advisor` Opus agent that adds CCIE-level reasoning around static recommendations. → `src/wxcli/migration/advisory/advisor.py:26`
- **Auto-rule** — a `DEFAULT_AUTO_RULES` (or user-supplied) rule that auto-resolves a Decision matching a `type`/`match` pattern. → `src/wxcli/commands/cucm_config.py:17`
- **Phase A vs Phase B** — the two halves of `cucm-migrate` Step 1c (architecture advisories vs per-decision review). → `.claude/skills/cucm-migrate/SKILL.md`
