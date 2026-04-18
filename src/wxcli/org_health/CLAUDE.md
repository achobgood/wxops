# org_health/ — Webex Calling Org Health Assessment

Deterministic health audit for live Webex Calling orgs. **76 tests passing.** Not wired into the wxcli CLI — invoked directly via `python3.14 -m` by the builder agent through the `org-health` skill.

## How It Works

```
wxcli commands (via skill) → collected JSON → analyze.py → checks.py → results.json → report.py → HTML
```

The skill orchestrates collection (Phase 1) by running wxcli commands and saving JSON output. The Python module handles analysis (Phase 2) and report generation (Phase 3). All checks are deterministic — same data produces same findings regardless of which LLM session runs it.

## Files

| File | Purpose |
|------|---------|
| `models.py` | `Finding`, `CategoryScore`, `HealthResult`, `OrgStats` dataclasses with `to_dict()` serialization |
| `collector.py` | `load_manifest()`, `validate_collection()`, `load_collected_data()` — reads JSON from collected directory |
| `checks.py` | 18 check functions registered via `@check(category)` decorator into `ALL_CHECKS`. `run_all_checks(data)` runs all and returns `list[Finding]` |
| `analyze.py` | `run_analysis(collected_dir) → HealthResult`. Also `__main__` for CLI: `python3.14 -m wxcli.org_health.analyze <dir> --output <dir>` |
| `report.py` | `generate_report(result, brand=, prepared_by=) → str`. Also `__main__` for CLI: `python3.14 -m wxcli.org_health.report <dir> --brand "..." --prepared-by "..."` |

## Check Categories (18 checks)

| Category | Key | Checks | Severities |
|----------|-----|--------|------------|
| Security Posture | `security` | AA external transfer, queues without recording, unrestricted international, no outgoing restrictions | MEDIUM, MEDIUM, HIGH, MEDIUM |
| Routing Hygiene | `routing` | Empty dial plans, orphan route components, trunk errors | HIGH, MEDIUM, HIGH |
| Feature Utilization | `feature_utilization` | Disabled AAs, understaffed queues (0=HIGH, 1=MEDIUM), single-member HGs, empty VM/paging/park groups | MEDIUM, HIGH/MEDIUM, MEDIUM, LOW |
| Device Health | `device_health` | Offline devices, 5-device limit, unassigned, deviceless workspaces, stale activation codes | HIGH, MEDIUM, MEDIUM, LOW, LOW |

## Reused from Migration Report

```python
from wxcli.migration.report.styles import REPORT_CSS, GOOGLE_FONTS_LINKS
from wxcli.migration.report.charts import horizontal_bar_chart
```

CSS design system (Lora/Source Sans 3/IBM Plex Mono, teal primary, warm neutrals) and SVG bar charts are imported directly. No store dependency — the migration report module's chart functions are pure.

## Data Flow

1. Skill tells agent to run wxcli commands → JSON files in `org-health-output/<timestamp>/collected/`
2. `analyze.py` loads collected JSON via `collector.py`, runs `checks.py`, writes `results/results.json`
3. `report.py` reads `results.json`, generates `report/org-health-report.html`

## Sampling

- Call queue details: all queues fetched individually (orgs rarely have >50)
- Outgoing permissions: first 50 users sampled. Report discloses sample size.

## Design Spec

`docs/superpowers/specs/2026-04-17-org-health-assessment-design.md`

## Tests

- `tests/org_health/conftest.py` — `collected_dir`, `sample_manifest`, `sample_collected_data` fixtures
- `tests/org_health/test_models.py` — dataclass construction, serialization
- `tests/org_health/test_collector.py` — manifest loading, validation, detail subdirectories
- `tests/org_health/test_checks.py` — 2-3 tests per check (positive, negative, edge case)
- `tests/org_health/test_analyze.py` — integration (collected dir → results), CLI, edge cases
- `tests/org_health/test_report.py` — HTML structure, severity badges, stat cards, zero-findings
