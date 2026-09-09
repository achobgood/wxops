"""Export layer — converts migration plan into deployment artifacts.

Produces deployment plans (markdown), JSON exports, and CSV decision reports
from the SQLite migration store. The deployment plan is a migration-specific
summary format (see deployment_plan.py section functions) — it does not follow
docs/templates/deployment-plan.md, which is the template for non-migration
provisioning plans produced directly by the wxc-calling-builder agent.

(Phase 09 — bridge to wxc-calling-builder)
"""
