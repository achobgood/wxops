---
paths:
  - "src/wxcli/org_health/**"
---

# Org Health Assessment

Live Webex Calling org audit at `src/wxcli/org_health/`. Deterministic Python checks against collected JSON — no LLM analysis. Reuses the migration report's CSS design system and chart functions. **76 tests passing.**

| Path | Purpose |
|------|---------|
| `src/wxcli/org_health/models.py` | Finding, CategoryScore, HealthResult, OrgStats dataclasses |
| `src/wxcli/org_health/collector.py` | Load manifest, validate collection, load collected JSON |
| `src/wxcli/org_health/checks.py` | 18 check functions + `@check()` decorator registry across 4 categories |
| `src/wxcli/org_health/analyze.py` | `__main__` entry: load → check → write `results.json` |
| `src/wxcli/org_health/report.py` | `__main__` entry: read results → generate self-contained HTML report |

**To run:** Builder agent → "audit my org" → `org-health` skill orchestrates 3 phases (collect via wxcli → analyze via `python3.14 -m wxcli.org_health.analyze` → report via `python3.14 -m wxcli.org_health.report`).

**Check categories:** Security Posture (4), Routing Hygiene (3), Feature Utilization (6), Device Health (5).
