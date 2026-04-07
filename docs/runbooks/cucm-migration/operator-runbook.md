<!-- Last verified: 2026-04-07 against branch claude/identify-missing-questions-8Xe2R, Layer 1 commits 1940991 + 3c55241 -->

# CUCM-to-Webex Operator Runbook

> **Audience:** Cisco SE with collab fluency, no prior wxops exposure, running their first CUCM-to-Webex migration.
> **Reading mode:** Read end-to-end before your first migration; section-bookmarked during execution.
> **See also:** [Decision Guide](decision-guide.md) · [Tuning Reference](tuning-reference.md)

## Table of Contents

1. [Quick Start](#quick-start)
2. [Prerequisites](#prerequisites)
3. [Pipeline Walkthrough](#pipeline-walkthrough)
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
4. [Assessment Report Orientation](#assessment-report-orientation)
5. [Decision Review](#decision-review)
6. [Execution & Recovery](#execution--recovery)
   - [Calibration Data Capture](#calibration-data-capture)
7. [Failure Patterns](#failure-patterns)
8. [Glossary](#glossary)

---

<!-- Wave 2 (Phase B) will fill each section below. Section headings here are the canonical anchors that other artifacts link to. Do not rename without updating the cross-reference map. -->

## Quick Start

This section is the minimal path for a fresh project. Read it once before you start, then use [§Pipeline Walkthrough](#pipeline-walkthrough) for detail on each stage.

**Assumed environment:** You have AXL credentials for the CUCM publisher, an active Webex Calling org with at least one location, and `wxcli` installed. You have run `wxcli configure` at least once and have a valid OAuth token loaded. See [§Prerequisites](#prerequisites) for all requirements.

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

# 5. Run 9 transform mappers → canonical Webex objects + decisions
wxcli cucm map

# 6. Run 12 analyzers + auto-rules + merge decisions
wxcli cucm analyze

# 7. Review open decisions (Rich table; resolve interactively or via batch rules)
wxcli cucm decisions

# 8. Expand objects → operations, build dependency DAG, partition batches
wxcli cucm plan

# 9. Run preflight checks against the live Webex org
wxcli cucm preflight

# 10. Export deployment plan (JSON/CSV/markdown) for review
wxcli cucm export

# 11. Execute via the cucm-migrate skill (delegates to wxc-calling-builder agent)
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

**What it does:** Two passes. **Pass 1** runs 27 normalizer functions that convert raw CUCM objects (device pools, phones, users, CSS, partitions, route patterns, hunt pilots, voicemail profiles, etc.) into canonical `MigrationObject` rows. **Pass 2** runs the `CrossReferenceBuilder` which links objects together (line ↔ device, device ↔ user, route pattern ↔ partition, etc.) and stores the relationships in the `cross_refs` table. → `src/wxcli/migration/transform/normalizers.py:145` and `src/wxcli/migration/transform/cross_reference.py:113`

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

**What it does:** Runs the transform mappers — currently 14 mapper modules (announcement, button template, call forwarding, call settings, CSS, device, device layout, device profile, e911, feature, line, location, MoH, monitoring, routing, SNR, softkey, user, voicemail, workspace) — that convert canonical CUCM objects into canonical Webex objects and emit `Decision` rows for any choice the pipeline cannot make on its own. Mapping is where most of the project's decisions are produced. → `src/wxcli/migration/transform/mappers/feature_mapper.py` and `src/wxcli/commands/cucm.py:788`

> **Note:** The CLI help text says "9 transform mappers" — this counts the original Phase 05 mapper set. The current implementation has 14 mapper modules (Phase 12+); the CLI help string is stale but the command runs all of them. → `src/wxcli/migration/CLAUDE.md:20`

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

**What it does:** Runs 12 analyzers (CSS routing, CSS permission, device compatibility, DN ambiguity, duplicate user, extension conflict, feature approximation, layout overflow, location ambiguity, missing data, shared line, voicemail compatibility, workspace license) over the canonical objects, merges new decisions with the existing set, applies auto-resolution rules, then runs the two-phase advisor system: per-decision recommendations via `populate_recommendations()` followed by the cross-cutting `ArchitectureAdvisor`. → `src/wxcli/migration/transform/analyzers/css_routing.py`, `src/wxcli/migration/transform/analysis_pipeline.py:204`, `src/wxcli/migration/advisory/__init__.py:18`, and `src/wxcli/migration/advisory/advisor.py:26`

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

| Factor | Weight | What it measures |
|---|---:|---|
| CSS Complexity | 20 | Partition/CSS depth, cross-CSS references, CSS-per-phone counts. |
| Feature Parity | 17 | CUCM features with no Webex equivalent (SNR, EM, intercom variants, custom softkeys). |
| Device Compatibility | 15 | Mix of native-MPP vs. convertible vs. incompatible endpoints; hardware refresh cost proxy. |
| Decision Density | 15 | Pending `Decision` rows per 100 users — how much judgment is still unresolved post-analyze. |
| Scale | 10 | Raw object counts (users, devices, lines, sites). |
| Shared Line Complexity | 10 | Shared DN appearances, cross-device shared lines, bridged-line group depth. |
| Phone Config Complexity | 8 | Per-line services, speed dials, BLF pickups, non-default button/softkey templates. |
| Routing Complexity | 5 | Translation patterns, route list depth, trunk fan-out. |

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

## Decision Review

Decision review is Step 1c of the `cucm-migrate` skill. It runs after the pipeline has produced static recommendations for every discovered entity. The operator works alongside Claude (acting as migration-advisor) to accept, reject, skip, or override each recommendation before anything is provisioned. Nothing is committed to Webex until review is complete and you approve the final plan.

### How `cucm-migrate` Invokes the Advisor

At Step 1c, `cucm-migrate` spawns the `migration-advisor` agent (Opus model, `bypassPermissions`) with a review-mode prompt. The agent reads the migration narrative from `<project>/exports/migration-narrative.md`, loads the static recommendations from the pipeline, and presents two review phases in sequence.

→ `.claude/skills/cucm-migrate/SKILL.md:142` — Step 1c definition and agent spawn parameters.

### Phase A: Architecture Advisories

Phase A presents `ARCHITECTURE_ADVISORY` decisions grouped by category before any per-entity review begins. The categories are `ELIMINATE` (CUCM workarounds to remove), `REBUILD` (patterns that need redesign in Webex), `OUT_OF_SCOPE` (items outside the migration boundary), and `MIGRATE_AS_IS` (safe to carry forward unchanged). For each group, the advisor presents a 2–3 sentence narrative connecting the advisory to your specific migration, then lists the individual advisories within it.

The operator can accept a whole group ("accept all ELIMINATE advisories") or drill into individual items. Accepting means the recommended action will be applied in planning. Rejecting flags the advisory for manual follow-up. Architecture advisories shape the framing of Phase B — resolve them before proceeding.

→ `.claude/agents/migration-advisor.md:123` — Review Mode, Phase A presentation protocol.

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

Source: `src/wxcli/commands/cucm_config.py:17` — `DEFAULT_AUTO_RULES`. These rules can be removed or reconfigured per project; see [tuning-reference.md §Auto-Rules](tuning-reference.md#auto-rules).

### When to Break the Review

In almost all cases, issues surfaced during review are fixable inside review — override the recommendation, adjust a choice, or skip and handle manually after migration. **Breaking the review to re-run an upstream stage is rare and disruptive.**

Break the review and re-run only when:

- Discovery data was incorrect (wrong CUCM cluster, missing AXL scope, or incomplete export) — the root data is wrong, not the recommendations
- The normalize or map stage produced systematically incorrect output that cannot be corrected decision-by-decision

Do not break the review for: wrong recommendations on individual entities (use override), missing E911 addresses (fix in the address resolution step, not by re-running), or high decision counts (use bulk-accept).

### See Also

- Per-DecisionType reference: [decision-guide.md §Decision Types A–Z](decision-guide.md#decision-types-az)
- Dissent handling detail: [decision-guide.md §Dissent Handling](decision-guide.md#dissent-handling)
- Auto-rule tuning: [tuning-reference.md §Auto-Rules](tuning-reference.md#auto-rules)
- Failure recovery: [§Failure Patterns](#failure-patterns)

## Execution & Recovery

_TBD — Wave 2 Phase B Task B5_

### Calibration Data Capture

_TBD — Wave 2 Phase B Task B5 (per spec D9)_

## Failure Patterns

_TBD — Wave 2 Phase B Task B6_

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
