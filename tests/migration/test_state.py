"""Tests for migration project state machine.

Acceptance criteria:
- Valid transitions succeed
- Invalid transitions raise InvalidTransitionError
- State persists to JSON and round-trips
"""

import json
import pytest
from pathlib import Path

from wxcli.migration.state import (
    InvalidTransitionError,
    MigrationState,
    ProjectState,
    VALID_TRANSITIONS,
)


@pytest.fixture
def state_path(tmp_path):
    return tmp_path / "state.json"


@pytest.fixture
def state(state_path):
    return MigrationState.create(state_path, "test-project")


class TestStateCreation:
    def test_initial_state(self, state):
        assert state.state == ProjectState.INITIALIZED
        assert state.project_id == "test-project"

    def test_state_file_exists(self, state, state_path):
        assert state_path.exists()
        data = json.loads(state_path.read_text())
        assert data["state"] == "initialized"
        assert data["project_id"] == "test-project"

    def test_init_with_project_id_sets_on_new_file(self, tmp_path):
        p = tmp_path / "new_state.json"
        s = MigrationState(p, project_id="auto-project")
        assert s.project_id == "auto-project"
        assert s.state == ProjectState.INITIALIZED

    def test_init_with_project_id_does_not_overwrite_existing(self, state_path, state):
        """If the file already has a project_id, __init__ should not overwrite it."""
        s2 = MigrationState(state_path, project_id="other-project")
        assert s2.project_id == "test-project"  # original preserved


class TestValidTransitions:
    def test_full_happy_path(self, state):
        """Walk the entire happy path through the state machine."""
        path = [
            ProjectState.CONNECTED,
            ProjectState.DISCOVERED,
            ProjectState.ANALYZED,
            ProjectState.READY,
            ProjectState.PLANNED,
            ProjectState.PREFLIGHT,
            ProjectState.SNAPSHOTTED,
            ProjectState.EXECUTING,
            ProjectState.VALIDATING,
            ProjectState.COMPLETED,
        ]
        for target in path:
            state.transition(target)
            assert state.state == target

    def test_blocked_path(self, state):
        """Walk the blocked -> planned path."""
        state.transition(ProjectState.CONNECTED)
        state.transition(ProjectState.DISCOVERED)
        state.transition(ProjectState.ANALYZED)
        state.transition(ProjectState.BLOCKED)
        state.transition(ProjectState.PLANNED)
        assert state.state == ProjectState.PLANNED

    def test_preflight_failure_retry(self, state):
        state.transition(ProjectState.CONNECTED)
        state.transition(ProjectState.DISCOVERED)
        state.transition(ProjectState.ANALYZED)
        state.transition(ProjectState.READY)
        state.transition(ProjectState.PLANNED)
        state.transition(ProjectState.PREFLIGHT)
        state.transition(ProjectState.PREFLIGHT_FAILED)
        state.transition(ProjectState.SNAPSHOTTED)
        assert state.state == ProjectState.SNAPSHOTTED

    def test_failure_and_rollback(self, state):
        state.transition(ProjectState.CONNECTED)
        state.transition(ProjectState.DISCOVERED)
        state.transition(ProjectState.ANALYZED)
        state.transition(ProjectState.READY)
        state.transition(ProjectState.PLANNED)
        state.transition(ProjectState.PREFLIGHT)
        state.transition(ProjectState.SNAPSHOTTED)
        state.transition(ProjectState.EXECUTING)
        state.transition(ProjectState.FAILED)
        state.transition(ProjectState.ROLLED_BACK)
        assert state.state == ProjectState.ROLLED_BACK


class TestInvalidTransitions:
    def test_skip_states(self, state):
        """Can't jump from INITIALIZED to EXECUTING."""
        with pytest.raises(InvalidTransitionError):
            state.transition(ProjectState.EXECUTING)

    def test_backward(self, state):
        """Can't go backward."""
        state.transition(ProjectState.CONNECTED)
        with pytest.raises(InvalidTransitionError):
            state.transition(ProjectState.INITIALIZED)

    def test_completed_is_terminal(self, state):
        """No transitions from COMPLETED."""
        state.transition(ProjectState.CONNECTED)
        state.transition(ProjectState.DISCOVERED)
        state.transition(ProjectState.ANALYZED)
        state.transition(ProjectState.READY)
        state.transition(ProjectState.PLANNED)
        state.transition(ProjectState.PREFLIGHT)
        state.transition(ProjectState.SNAPSHOTTED)
        state.transition(ProjectState.EXECUTING)
        state.transition(ProjectState.VALIDATING)
        state.transition(ProjectState.COMPLETED)
        with pytest.raises(InvalidTransitionError):
            state.transition(ProjectState.INITIALIZED)

    def test_rolled_back_is_terminal(self, state):
        state.transition(ProjectState.CONNECTED)
        state.transition(ProjectState.DISCOVERED)
        state.transition(ProjectState.ANALYZED)
        state.transition(ProjectState.READY)
        state.transition(ProjectState.PLANNED)
        state.transition(ProjectState.PREFLIGHT)
        state.transition(ProjectState.SNAPSHOTTED)
        state.transition(ProjectState.EXECUTING)
        state.transition(ProjectState.FAILED)
        state.transition(ProjectState.ROLLED_BACK)
        with pytest.raises(InvalidTransitionError):
            state.transition(ProjectState.INITIALIZED)

    def test_error_message_content(self, state):
        with pytest.raises(InvalidTransitionError, match="Cannot transition from initialized to executing"):
            state.transition(ProjectState.EXECUTING)


class TestPersistence:
    def test_round_trip(self, state, state_path):
        state.transition(ProjectState.CONNECTED)
        state.transition(ProjectState.DISCOVERED)
        # Reload from disk
        state2 = MigrationState(state_path)
        assert state2.state == ProjectState.DISCOVERED
        assert state2.project_id == "test-project"

    def test_history_preserved(self, state, state_path):
        state.transition(ProjectState.CONNECTED)
        state.transition(ProjectState.DISCOVERED)
        state2 = MigrationState(state_path)
        assert len(state2.history) == 2
        assert state2.history[0]["from"] == "initialized"
        assert state2.history[0]["to"] == "connected"
        assert state2.history[1]["to"] == "discovered"


class TestTransitionCoverage:
    def test_all_states_have_entries(self):
        """Every ProjectState should appear in VALID_TRANSITIONS."""
        for s in ProjectState:
            assert s in VALID_TRANSITIONS, f"{s} missing from VALID_TRANSITIONS"
