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

_TBD — Wave 2 Phase B Task B1_

## Prerequisites

_TBD — Wave 2 Phase B Task B1_

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
