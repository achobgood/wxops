"""Project-level state machine for CUCM-to-Webex migration.

Tracks the current phase of a migration project. Persisted to state.json
(not SQLite — it's ~10 lines and read on every CLI invocation).

State diagram from: cucm-wxc-migration.md lines 228-261
Persistence pattern from: 01-data-representation.md lines 147-154
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class ProjectState(str, Enum):
    """Project-level migration states.
    (from cucm-wxc-migration.md lines 230-254)
    """
    INITIALIZED = "initialized"
    CONNECTED = "connected"
    DISCOVERED = "discovered"
    ANALYZED = "analyzed"
    READY = "ready"
    BLOCKED = "blocked"
    PLANNED = "planned"
    PREFLIGHT = "preflight"
    PREFLIGHT_FAILED = "preflight_failed"
    SNAPSHOTTED = "snapshotted"
    EXECUTING = "executing"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    VALIDATING = "validating"
    COMPLETED = "completed"


# Valid transitions from each state.
# (from cucm-wxc-migration.md state diagram lines 228-261)
VALID_TRANSITIONS: dict[ProjectState, set[ProjectState]] = {
    ProjectState.INITIALIZED: {ProjectState.CONNECTED},
    ProjectState.CONNECTED: {ProjectState.DISCOVERED},
    ProjectState.DISCOVERED: {ProjectState.ANALYZED},
    ProjectState.ANALYZED: {ProjectState.READY, ProjectState.BLOCKED},
    ProjectState.READY: {ProjectState.PLANNED},
    ProjectState.BLOCKED: {ProjectState.PLANNED},
    ProjectState.PLANNED: {ProjectState.PREFLIGHT},
    ProjectState.PREFLIGHT: {ProjectState.PREFLIGHT_FAILED, ProjectState.SNAPSHOTTED, ProjectState.PREFLIGHT},
    ProjectState.PREFLIGHT_FAILED: {ProjectState.SNAPSHOTTED, ProjectState.PREFLIGHT},
    ProjectState.SNAPSHOTTED: {ProjectState.EXECUTING},
    ProjectState.EXECUTING: {ProjectState.FAILED, ProjectState.VALIDATING},
    ProjectState.FAILED: {ProjectState.ROLLED_BACK},
    ProjectState.VALIDATING: {ProjectState.COMPLETED},
    ProjectState.ROLLED_BACK: set(),
    ProjectState.COMPLETED: set(),
}


class InvalidTransitionError(Exception):
    """Raised when a state transition is not allowed."""


class MigrationState:
    """State machine for a migration project with JSON persistence.

    (from cucm-wxc-migration.md lines 228-261,
     01-data-representation.md lines 147-154)
    """

    def __init__(self, state_path: Path | str, project_id: str | None = None) -> None:
        self.state_path = Path(state_path)
        self._data: dict[str, Any] = self._load()
        if project_id is not None and not self._data["project_id"]:
            self._data["project_id"] = project_id
            self._save()

    @property
    def state(self) -> ProjectState:
        return ProjectState(self._data["state"])

    @property
    def project_id(self) -> str:
        return self._data["project_id"]

    @property
    def history(self) -> list[dict[str, str]]:
        return self._data.get("history", [])

    def transition(self, target: ProjectState) -> None:
        """Transition to a new state. Raises InvalidTransitionError if not allowed."""
        current = self.state
        if target not in VALID_TRANSITIONS.get(current, set()):
            raise InvalidTransitionError(
                f"Cannot transition from {current.value} to {target.value}. "
                f"Valid targets: {sorted(s.value for s in VALID_TRANSITIONS.get(current, set()))}"
            )
        now = datetime.now(timezone.utc).isoformat()
        self._data["history"].append({
            "from": current.value,
            "to": target.value,
            "timestamp": now,
        })
        self._data["state"] = target.value
        self._data["updated_at"] = now
        self._save()

    def _load(self) -> dict[str, Any]:
        if self.state_path.exists():
            with open(self.state_path, encoding="utf-8") as f:
                return json.load(f)
        return self._default_data()

    def _save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)

    @staticmethod
    def _default_data() -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        return {
            "project_id": "",
            "state": ProjectState.INITIALIZED.value,
            "created_at": now,
            "updated_at": now,
            "history": [],
        }

    @classmethod
    def create(cls, state_path: Path | str, project_id: str) -> MigrationState:
        """Create a new migration state file."""
        instance = cls.__new__(cls)
        instance.state_path = Path(state_path)
        instance._data = cls._default_data()
        instance._data["project_id"] = project_id
        instance._save()
        return instance
