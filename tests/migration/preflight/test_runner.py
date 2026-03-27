"""Tests for preflight runner orchestrator.

Mocks _run_wxcli to return canned JSON — no live Webex calls.
(from phase-10-preflight.md, testing approach)
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from wxcli.migration.models import (
    CanonicalLocation,
    CanonicalUser,
    CanonicalWorkspace,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.preflight import CheckStatus
from wxcli.migration.preflight.runner import PreflightRunner, _worst_status
from wxcli.migration.preflight import CheckResult
from wxcli.migration.store import MigrationStore


@pytest.fixture
def store(tmp_path):
    s = MigrationStore(tmp_path / "test.db")
    yield s
    s.close()


def _prov():
    return Provenance(
        source_system="cucm",
        source_id="pk-test",
        source_name="test",
        extracted_at=datetime.now(timezone.utc),
    )


def _analyzed(obj):
    obj.status = MigrationStatus.ANALYZED
    return obj


def _seed_basic_store(store):
    """Seed store with 1 user, 1 location, 1 workspace for typical test."""
    store.upsert_object(_analyzed(CanonicalUser(
        canonical_id="user:001", provenance=_prov(),
        emails=["alice@test.com"], location_id="loc-123",
    )))
    store.upsert_object(_analyzed(CanonicalLocation(
        canonical_id="location:hq", provenance=_prov(), name="HQ Office",
    )))
    store.upsert_object(_analyzed(CanonicalWorkspace(
        canonical_id="workspace:001", provenance=_prov(), display_name="Lobby",
    )))


# ===================================================================
# _worst_status helper
# ===================================================================


class TestWorstStatus:
    def test_all_pass(self):
        results = [
            CheckResult("a", CheckStatus.PASS, "ok"),
            CheckResult("b", CheckStatus.PASS, "ok"),
        ]
        assert _worst_status(results) == CheckStatus.PASS

    def test_warn_beats_pass(self):
        results = [
            CheckResult("a", CheckStatus.PASS, "ok"),
            CheckResult("b", CheckStatus.WARN, "warning"),
        ]
        assert _worst_status(results) == CheckStatus.WARN

    def test_fail_beats_warn(self):
        results = [
            CheckResult("a", CheckStatus.WARN, "warning"),
            CheckResult("b", CheckStatus.FAIL, "fail"),
        ]
        assert _worst_status(results) == CheckStatus.FAIL

    def test_skip_is_lowest(self):
        results = [
            CheckResult("a", CheckStatus.SKIP, "skip"),
            CheckResult("b", CheckStatus.PASS, "ok"),
        ]
        assert _worst_status(results) == CheckStatus.PASS

    def test_all_skip(self):
        results = [
            CheckResult("a", CheckStatus.SKIP, "skip"),
        ]
        assert _worst_status(results) == CheckStatus.SKIP


# ===================================================================
# PreflightRunner integration tests (mocked wxcli)
# ===================================================================


class TestPreflightRunner:
    @patch("wxcli.migration.preflight.runner._run_wxcli")
    def test_all_pass_scenario(self, mock_wxcli, store):
        _seed_basic_store(store)

        # Mock wxcli responses
        def side_effect(args):
            cmd = " ".join(args)
            if "licenses" in cmd:
                return [
                    {"name": "Webex Calling - Professional", "totalUnits": 100, "consumedUnits": 0},
                    {"name": "Webex Calling - Workspaces", "totalUnits": 50, "consumedUnits": 0},
                ]
            if "locations" in cmd:
                return [{"name": "HQ Office", "id": "loc-123"}]
            if "pstn" in cmd and "list-connection" in cmd:
                return [{"routingChoice": "TRUNK", "trunkId": "trunk-1"}]
            if "numbers" in cmd:
                return []
            if "users" in cmd:
                return []
            if "list-trunks" in cmd:
                return []
            if "auto-attendant" in cmd or "call-queue" in cmd or "hunt-group" in cmd or "paging-group" in cmd:
                return []
            return []

        mock_wxcli.side_effect = side_effect
        runner = PreflightRunner(config={"rate_limit_per_minute": 100, "max_migration_hours": 8})
        result = runner.run(store)

        assert result.overall in (CheckStatus.PASS, CheckStatus.SKIP)
        assert len(result.checks) == 8

    @patch("wxcli.migration.preflight.runner._run_wxcli")
    def test_single_check_filter(self, mock_wxcli, store):
        _seed_basic_store(store)

        mock_wxcli.return_value = [
            {"name": "Webex Calling - Professional", "totalUnits": 100, "consumedUnits": 0},
        ]

        runner = PreflightRunner()
        result = runner.run(store, check_filter="licenses")
        assert len(result.checks) == 1
        assert result.checks[0].name == "User licenses"

    def test_dry_run(self, store):
        _seed_basic_store(store)

        runner = PreflightRunner()
        result = runner.run(store, dry_run=True)
        assert result.overall == CheckStatus.SKIP
        assert all("[dry-run]" in c.detail for c in result.checks)

    def test_dry_run_with_filter(self, store):
        _seed_basic_store(store)
        runner = PreflightRunner()
        result = runner.run(store, check_filter="licenses", dry_run=True)
        assert len(result.checks) == 1

    @patch("wxcli.migration.preflight.runner._run_wxcli")
    def test_number_conflict_produces_decisions(self, mock_wxcli, store):
        store.upsert_object(_analyzed(CanonicalUser(
            canonical_id="user:001", provenance=_prov(),
            emails=["alice@test.com"],
            phone_numbers=[{"type": "work", "value": "+14155551234"}],
        )))

        def side_effect(args):
            cmd = " ".join(args)
            if "licenses" in cmd:
                return [{"name": "Webex Calling - Professional", "totalUnits": 100, "consumedUnits": 0}]
            if "numbers" in cmd:
                return [{
                    "phoneNumber": "+14155551234",
                    "owner": {"id": "p-existing", "type": "PEOPLE", "lastName": "Bob"},
                }]
            return []

        mock_wxcli.side_effect = side_effect
        runner = PreflightRunner(config={"rate_limit_per_minute": 100, "max_migration_hours": 8})
        result = runner.run(store)

        assert len(result.new_decision_ids) >= 1
        # Verify decision was merged into store
        all_decisions = store.get_all_decisions()
        number_decs = [d for d in all_decisions if d.get("type") == "NUMBER_CONFLICT"]
        assert len(number_decs) >= 1

    @patch("wxcli.migration.preflight.runner._run_wxcli")
    def test_duplicate_user_produces_decisions(self, mock_wxcli, store):
        store.upsert_object(_analyzed(CanonicalUser(
            canonical_id="user:001", provenance=_prov(), emails=["alice@test.com"],
        )))

        def side_effect(args):
            cmd = " ".join(args)
            if "licenses" in cmd:
                return [{"name": "Webex Calling - Professional", "totalUnits": 100, "consumedUnits": 0}]
            if "users" in cmd:
                return [{"emails": ["alice@test.com"], "id": "p-existing", "displayName": "Alice"}]
            return []

        mock_wxcli.side_effect = side_effect
        runner = PreflightRunner(config={"rate_limit_per_minute": 100, "max_migration_hours": 8})
        result = runner.run(store)

        assert len(result.new_decision_ids) >= 1
        all_decisions = store.get_all_decisions()
        dup_decs = [d for d in all_decisions if d.get("type") == "DUPLICATE_USER"]
        assert len(dup_decs) >= 1

    def test_invalid_check_filter_raises(self, store):
        runner = PreflightRunner()
        with pytest.raises(Exception, match="Unknown check"):
            runner.run(store, check_filter="nonexistent")

    @patch("wxcli.migration.preflight.runner._run_wxcli")
    def test_rerun_merges_decisions(self, mock_wxcli, store):
        """Re-running preflight should merge decisions (keep resolved ones)."""
        store.upsert_object(_analyzed(CanonicalUser(
            canonical_id="user:001", provenance=_prov(),
            emails=["alice@test.com"],
            phone_numbers=[{"type": "work", "value": "+14155551234"}],
        )))

        def side_effect(args):
            cmd = " ".join(args)
            if "licenses" in cmd:
                return [{"name": "Webex Calling - Professional", "totalUnits": 100, "consumedUnits": 0}]
            if "numbers" in cmd:
                return [{
                    "phoneNumber": "+14155551234",
                    "owner": {"id": "p-existing", "type": "PEOPLE", "lastName": "Bob"},
                }]
            return []

        mock_wxcli.side_effect = side_effect
        runner = PreflightRunner(config={"rate_limit_per_minute": 100, "max_migration_hours": 8})

        # First run
        result1 = runner.run(store)
        assert len(result1.new_decision_ids) >= 1

        # Resolve the decision
        all_decs = store.get_all_decisions()
        number_dec = [d for d in all_decs if d.get("type") == "NUMBER_CONFLICT"][0]
        store.resolve_decision(number_dec["decision_id"], "skip_number", "user")

        # Re-run — resolved decision should be kept (not duplicated)
        result2 = runner.run(store)
        all_decs2 = store.get_all_decisions()
        number_decs2 = [d for d in all_decs2
                        if d.get("type") == "NUMBER_CONFLICT"
                        and d.get("chosen_option") != "__stale__"]
        assert len(number_decs2) == 1  # Exactly 1, not duplicated
        assert number_decs2[0].get("chosen_option") == "skip_number"

    @patch("wxcli.migration.preflight.runner._run_wxcli")
    def test_wxcli_failure_degrades_gracefully(self, mock_wxcli, store):
        """If wxcli commands fail, runner should degrade — not crash."""
        from wxcli.migration.preflight import PreflightError
        _seed_basic_store(store)
        mock_wxcli.side_effect = PreflightError("wxcli not found")
        runner = PreflightRunner(config={"rate_limit_per_minute": 100, "max_migration_hours": 8})
        result = runner.run(store)
        # Should not raise — checks receive empty data
        assert len(result.checks) == 8
