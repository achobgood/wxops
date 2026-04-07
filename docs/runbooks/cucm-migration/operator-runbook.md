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

_TBD — Wave 2 Phase B Task B2 (one subsection per command)_

### init
### discover
### normalize
### map
### analyze
### decisions
### plan
### preflight
### export
### execute (via /cucm-migrate)

## Assessment Report Orientation

_TBD — Wave 2 Phase B Task B3_

## Decision Review

_TBD — Wave 2 Phase B Task B4_

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
