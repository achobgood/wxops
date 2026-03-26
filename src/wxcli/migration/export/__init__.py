"""Export layer — converts migration plan into deployment artifacts.

Produces deployment plans (markdown), JSON exports, and CSV decision reports
from the SQLite migration store. The deployment plan format matches
docs/templates/deployment-plan.md and is consumable by the wxc-calling-builder agent.

(Phase 09 — bridge to wxc-calling-builder)
"""
