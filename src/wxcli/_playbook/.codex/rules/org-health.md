---
paths:
  - "src/wxcli/org_health/**"
---

# Org Health Assessment

Live Webex Calling org audit. Deterministic Python checks against collected JSON — no LLM analysis. Reuses the migration report's CSS design system and chart functions.

Implementation lives inside the installed wxcli package; run it via `wxcli org-health`.

**To run:** Builder agent → "audit my org" → `org-health` skill orchestrates 3 phases (collect via wxcli → analyze via `wxcli org-health analyze` → report via `wxcli org-health report`).

**Check categories:** Security Posture (4), Routing Hygiene (3), Feature Utilization (6), Device Health (5).
