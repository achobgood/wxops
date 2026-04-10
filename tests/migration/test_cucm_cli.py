"""CLI integration tests for wxcli cucm subcommands.

Tests invoke commands via Typer's CliRunner and verify output + side effects
(project directory creation, state.json updates, store contents).
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from wxcli.commands.cucm import app, MIGRATIONS_DIR


runner = CliRunner()


@pytest.fixture(autouse=True)
def tmp_migrations_dir(tmp_path, monkeypatch):
    """Redirect MIGRATIONS_DIR and CURRENT_PROJECT_FILE to a temp directory."""
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    current_file = tmp_path / "current_project"
    monkeypatch.setattr("wxcli.commands.cucm.MIGRATIONS_DIR", migrations_dir)
    monkeypatch.setattr("wxcli.commands.cucm.CURRENT_PROJECT_FILE", current_file)
    return migrations_dir


# ===================================================================
# PROJECT MANAGEMENT
# ===================================================================


class TestInit:
    def test_init_creates_project_directory(self, tmp_migrations_dir):
        result = runner.invoke(app, ["init", "test-project"])
        assert result.exit_code == 0
        assert "Created migration project" in result.output

        project_dir = tmp_migrations_dir / "test-project"
        assert project_dir.exists()
        assert (project_dir / "migration.db").exists()
        assert (project_dir / "state.json").exists()
        assert (project_dir / "config.json").exists()

    def test_init_creates_valid_state(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])
        state = json.loads((tmp_migrations_dir / "test-project" / "state.json").read_text())
        assert state["project_id"] == "test-project"
        assert state["state"] == "initialized"
        assert "init" in state["completed_stages"]

    def test_init_creates_default_config(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])
        config = json.loads((tmp_migrations_dir / "test-project" / "config.json").read_text())
        assert config["country_code"] == "+1"
        assert config["default_language"] == "en_us"

    def test_init_sets_current_project(self, tmp_migrations_dir, tmp_path):
        runner.invoke(app, ["init", "test-project"])
        current = (tmp_path / "current_project").read_text()
        assert current == "test-project"

    def test_init_duplicate_fails(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])
        result = runner.invoke(app, ["init", "test-project"])
        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_init_creates_valid_sqlite(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])
        db_path = tmp_migrations_dir / "test-project" / "migration.db"
        conn = sqlite3.connect(str(db_path))
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        conn.close()
        assert "objects" in tables
        assert "decisions" in tables
        assert "cross_refs" in tables
        assert "plan_operations" in tables


class TestStatus:
    def test_status_shows_project_info(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "test-project" in result.output
        assert "initialized" in result.output

    def test_status_no_project_fails(self, tmp_migrations_dir):
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 1
        assert "No project" in result.output


# ===================================================================
# CONFIG COMMANDS
# ===================================================================


class TestConfig:
    def test_config_show(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        assert "country_code" in result.output

    def test_config_set(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])
        result = runner.invoke(app, ["config", "set", "country_code", "+44"])
        assert result.exit_code == 0
        assert "+44" in result.output

        # Verify persisted
        config = json.loads(
            (tmp_migrations_dir / "test-project" / "config.json").read_text()
        )
        assert config["country_code"] == "+44"

    def test_config_set_boolean(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])
        runner.invoke(app, ["config", "set", "include_phoneless_users", "true"])
        config = json.loads(
            (tmp_migrations_dir / "test-project" / "config.json").read_text()
        )
        assert config["include_phoneless_users"] is True


# ===================================================================
# CONFIG RESET
# ===================================================================


class TestConfigReset:
    """Tests for `wxcli cucm config reset <key>` (Bug G fix)."""

    def test_config_reset_auto_rules_restores_defaults(self, tmp_migrations_dir):
        """Removing a default rule then running `config reset auto_rules`
        restores the full default list."""
        from wxcli.commands.cucm_config import DEFAULT_AUTO_RULES

        runner.invoke(app, ["init", "test-project"])

        project_dir = tmp_migrations_dir / "test-project"
        config_path = project_dir / "config.json"

        # Hand-edit to remove one default rule.
        config = json.loads(config_path.read_text())
        original_count = len(config["auto_rules"])
        config["auto_rules"] = config["auto_rules"][:-1]
        config_path.write_text(json.dumps(config, indent=2))
        assert len(json.loads(config_path.read_text())["auto_rules"]) == original_count - 1

        # Reset auto_rules to defaults.
        result = runner.invoke(
            app, ["config", "reset", "auto_rules", "-y", "-p", "test-project"]
        )
        assert result.exit_code == 0

        restored = json.loads(config_path.read_text())["auto_rules"]
        assert len(restored) == len(DEFAULT_AUTO_RULES)

    def test_config_reset_preserves_other_keys(self, tmp_migrations_dir):
        """Resetting one key must NOT touch other keys."""
        runner.invoke(app, ["init", "test-project"])
        runner.invoke(app, ["config", "set", "country_code", "+44"])

        project_dir = tmp_migrations_dir / "test-project"
        config_path = project_dir / "config.json"
        assert json.loads(config_path.read_text())["country_code"] == "+44"

        result = runner.invoke(
            app, ["config", "reset", "auto_rules", "-y", "-p", "test-project"]
        )
        assert result.exit_code == 0

        # Custom country_code must still be "+44" after reset.
        config = json.loads(config_path.read_text())
        assert config["country_code"] == "+44"

    def test_config_reset_refuses_unknown_key(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])
        result = runner.invoke(
            app, ["config", "reset", "bogus_key", "-y", "-p", "test-project"]
        )
        assert result.exit_code == 1
        # Error message should list valid keys.
        assert "auto_rules" in result.output
        assert "country_code" in result.output

    def test_config_reset_refuses_without_key(self, tmp_migrations_dir):
        """No key argument → Typer shows usage / exits non-zero."""
        runner.invoke(app, ["init", "test-project"])
        result = runner.invoke(app, ["config", "reset", "-p", "test-project"])
        assert result.exit_code != 0

    def test_config_reset_confirmation_prompt(self, tmp_migrations_dir):
        """Without -y, the command prompts and aborts on 'n'."""
        from wxcli.commands.cucm_config import DEFAULT_AUTO_RULES

        runner.invoke(app, ["init", "test-project"])

        project_dir = tmp_migrations_dir / "test-project"
        config_path = project_dir / "config.json"
        config = json.loads(config_path.read_text())
        config["auto_rules"] = []
        config_path.write_text(json.dumps(config, indent=2))

        # Reply "n" to the confirmation prompt.
        result = runner.invoke(
            app,
            ["config", "reset", "auto_rules", "-p", "test-project"],
            input="n\n",
        )
        assert result.exit_code == 0  # Graceful abort, not an error.

        # auto_rules must still be empty (reset was cancelled).
        restored = json.loads(config_path.read_text())["auto_rules"]
        assert restored == []


# ===================================================================
# PIPELINE STAGE ORDERING
# ===================================================================


class TestPipelineOrdering:
    """Pipeline commands refuse to run out of order."""

    def test_normalize_before_discover_fails(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])
        result = runner.invoke(app, ["normalize"])
        assert result.exit_code == 1
        assert "prerequisite" in result.output.lower() or "discover" in result.output.lower()

    def test_map_before_normalize_fails(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])
        result = runner.invoke(app, ["map"])
        assert result.exit_code == 1

    def test_analyze_before_map_fails(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])
        result = runner.invoke(app, ["analyze"])
        assert result.exit_code == 1

    def test_plan_before_analyze_fails(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])
        result = runner.invoke(app, ["plan"])
        assert result.exit_code == 1


# ===================================================================
# PIPELINE STAGES (with mocked pipeline functions)
# ===================================================================


class TestDiscover:
    @patch("wxcli.commands.cucm.socket.socket")
    @patch("wxcli.migration.cucm.discovery.run_discovery")
    @patch("wxcli.migration.cucm.connection.AXLConnection")
    def test_discover_success(self, mock_conn_cls, mock_discover, mock_socket_cls, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])

        # Mock socket TCP probe to succeed
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0
        mock_socket_cls.return_value = mock_sock

        # Setup mocks
        mock_conn = MagicMock()
        mock_conn_cls.return_value = mock_conn

        mock_result = MagicMock()
        mock_result.raw_data = {"locations": {"device_pools": []}, "users": {"users": []}}
        mock_result.cucm_version = "15.0"
        mock_result.total_objects = 42
        mock_result.total_failed = 0
        mock_result.extractor_results = {}
        mock_discover.return_value = mock_result

        result = runner.invoke(
            app,
            ["discover", "--host", "10.0.0.1", "--username", "admin", "--password", "secret"],
        )
        assert result.exit_code == 0
        assert "Discovery complete" in result.output
        assert "42" in result.output

        # Verify raw_data.json persisted
        raw_path = tmp_migrations_dir / "test-project" / "raw_data.json"
        assert raw_path.exists()

        # Verify stage marked
        state = json.loads(
            (tmp_migrations_dir / "test-project" / "state.json").read_text()
        )
        assert "discover" in state["completed_stages"]

    @patch("wxcli.commands.cucm.socket.socket")
    @patch("wxcli.migration.cucm.connection.AXLConnection")
    def test_discover_connection_failure(self, mock_conn_cls, mock_socket_cls, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])

        # Mock socket TCP probe to succeed (so we reach the AXLConnection error)
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0
        mock_socket_cls.return_value = mock_sock

        mock_conn_cls.side_effect = Exception("Connection refused")

        result = runner.invoke(
            app,
            ["discover", "--host", "10.0.0.1", "--username", "admin", "--password", "secret"],
        )
        assert result.exit_code == 1
        assert "Connection failed" in result.output


class TestNormalize:
    def test_normalize_success(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])
        project_dir = tmp_migrations_dir / "test-project"

        # Fake discover stage
        state = json.loads((project_dir / "state.json").read_text())
        state["completed_stages"].append("discover")
        (project_dir / "state.json").write_text(json.dumps(state))

        # Write raw_data.json (empty but valid)
        (project_dir / "raw_data.json").write_text(json.dumps({
            "locations": {"device_pools": [], "datetime_groups": [], "cucm_locations": []},
            "users": {"users": []},
            "devices": {"phones": []},
            "routing": {"partitions": [], "css_list": [], "route_patterns": []},
            "features": {"hunt_pilots": [], "hunt_lists": [], "line_groups": []},
            "voicemail": {"voicemail_profiles": [], "voicemail_pilots": []},
        }))

        result = runner.invoke(app, ["normalize"])
        assert result.exit_code == 0
        assert "Normalization complete" in result.output

        # Verify stage marked
        state = json.loads((project_dir / "state.json").read_text())
        assert "normalize" in state["completed_stages"]


class TestMap:
    def test_map_success(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])
        project_dir = tmp_migrations_dir / "test-project"

        # Fake prior stages
        state = json.loads((project_dir / "state.json").read_text())
        state["completed_stages"].extend(["discover", "normalize"])
        (project_dir / "state.json").write_text(json.dumps(state))

        result = runner.invoke(app, ["map"])
        assert result.exit_code == 0
        assert "Mapping complete" in result.output

        state = json.loads((project_dir / "state.json").read_text())
        assert "map" in state["completed_stages"]


class TestAnalyze:
    def test_analyze_success(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])
        project_dir = tmp_migrations_dir / "test-project"

        # Fake prior stages
        state = json.loads((project_dir / "state.json").read_text())
        state["completed_stages"].extend(["discover", "normalize", "map"])
        (project_dir / "state.json").write_text(json.dumps(state))

        result = runner.invoke(app, ["analyze"])
        assert result.exit_code == 0
        assert "Analysis complete" in result.output

        state = json.loads((project_dir / "state.json").read_text())
        assert "analyze" in state["completed_stages"]


class TestPlan:
    def test_plan_success(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])
        project_dir = tmp_migrations_dir / "test-project"

        # Fake prior stages
        state = json.loads((project_dir / "state.json").read_text())
        state["completed_stages"].extend(["discover", "normalize", "map", "analyze"])
        (project_dir / "state.json").write_text(json.dumps(state))

        result = runner.invoke(app, ["plan"])
        assert result.exit_code == 0
        assert "Planning complete" in result.output

        state = json.loads((project_dir / "state.json").read_text())
        assert "plan" in state["completed_stages"]


# ===================================================================
# DECISION MANAGEMENT
# ===================================================================


def _seed_plan(project_dir: Path) -> None:
    """Insert a minimal execution plan into the store for export tests."""
    from datetime import datetime, timezone
    from wxcli.migration.models import CanonicalLocation, MigrationStatus, Provenance
    from wxcli.migration.store import MigrationStore

    store = MigrationStore(project_dir / "migration.db")
    # Insert the object first (FK on plan_operations → objects)
    loc = CanonicalLocation(
        canonical_id="location:hq",
        provenance=Provenance(
            source_system="cucm", source_id="pk-test",
            source_name="test", extracted_at=datetime.now(timezone.utc),
        ),
        status=MigrationStatus.ANALYZED,
        name="HQ", time_zone="America/New_York",
        preferred_language="en_US", announcement_language="en_us",
    )
    store.upsert_object(loc)
    store.conn.execute(
        """INSERT INTO plan_operations
           (node_id, canonical_id, op_type, resource_type, tier, batch,
            api_calls, description, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("location:hq:create", "location:hq", "create", "location", 0,
         "org-wide", 1, "Create location HQ", "pending"),
    )
    store.conn.commit()
    store.close()


def _seed_decisions(project_dir: Path) -> None:
    """Insert test decisions into the store for decision management tests."""
    from wxcli.migration.store import MigrationStore

    store = MigrationStore(project_dir / "migration.db")
    for i in range(3):
        sev = ["HIGH", "MEDIUM", "LOW"][i]
        store.save_decision({
            "decision_id": f"D{i + 1:04d}",
            "type": "DEVICE_INCOMPATIBLE" if i < 2 else "MISSING_DATA",
            "severity": sev,
            "summary": f"Test decision {i + 1}",
            "context": {"_affected_objects": [f"device:{i}"]},
            "options": [
                {"id": "skip", "label": "Skip", "impact": "Device not migrated"},
                {"id": "convert", "label": "Convert", "impact": "Attempt firmware conversion"},
            ],
            "chosen_option": None,
            "fingerprint": f"fp-test-{i}",
            "run_id": "test-run",
        })
    store.close()


class TestDecisions:
    def test_decisions_list(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])
        _seed_decisions(tmp_migrations_dir / "test-project")

        result = runner.invoke(app, ["decisions"])
        assert result.exit_code == 0
        # Rich table may truncate columns in narrow terminal; check content that's visible
        assert "DEVICE_INCOMPATIBLE" in result.output
        assert "3 pending" in result.output

    def test_decisions_filter_by_type(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])
        _seed_decisions(tmp_migrations_dir / "test-project")

        result = runner.invoke(app, ["decisions", "--type", "MISSING_DATA"])
        assert result.exit_code == 0
        assert "MISSING_DATA" in result.output
        assert "1 pending" in result.output

    def test_decisions_filter_pending(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])
        _seed_decisions(tmp_migrations_dir / "test-project")

        result = runner.invoke(app, ["decisions", "--status", "pending"])
        assert result.exit_code == 0
        assert "3 pending" in result.output

    def test_decisions_empty(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])
        result = runner.invoke(app, ["decisions"])
        assert result.exit_code == 0
        assert "No decisions" in result.output


class TestDecide:
    def test_decide_single(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])
        _seed_decisions(tmp_migrations_dir / "test-project")

        result = runner.invoke(app, ["decide", "D0001", "skip"])
        assert result.exit_code == 0
        assert "Resolved D0001" in result.output

        # Verify in store
        from wxcli.migration.store import MigrationStore

        store = MigrationStore(tmp_migrations_dir / "test-project" / "migration.db")
        d = store.get_decision("D0001")
        assert d["chosen_option"] == "skip"
        store.close()

    def test_decide_batch(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])
        _seed_decisions(tmp_migrations_dir / "test-project")

        result = runner.invoke(
            app,
            ["decide", "--type", "DEVICE_INCOMPATIBLE", "--all", "--choice", "skip"],
            input="y\n",
        )
        assert result.exit_code == 0
        assert "Resolved 2 decisions" in result.output

    def test_decide_not_found(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])
        result = runner.invoke(app, ["decide", "D9999", "skip"])
        assert result.exit_code == 1
        assert "not found" in result.output


# ===================================================================
# EXPORT
# ===================================================================


class TestExport:
    def test_export_json(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])
        result = runner.invoke(app, ["export", "--format", "json"])
        assert result.exit_code == 0
        assert "export.json" in result.output

        export_path = tmp_migrations_dir / "test-project" / "exports" / "export.json"
        assert export_path.exists()
        data = json.loads(export_path.read_text())
        assert "objects" in data
        assert "decisions" in data

    def test_export_csv_decisions(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])
        _seed_decisions(tmp_migrations_dir / "test-project")

        result = runner.invoke(app, ["export", "--format", "csv-decisions"])
        assert result.exit_code == 0
        assert "decisions.csv" in result.output

        csv_path = tmp_migrations_dir / "test-project" / "exports" / "decisions.csv"
        assert csv_path.exists()
        content = csv_path.read_text()
        assert "decision_id" in content
        assert "D0001" in content

    def test_export_deployment_plan(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])
        # Seed a plan in the store so the export has something to render
        _seed_plan(tmp_migrations_dir / "test-project")
        result = runner.invoke(app, ["export", "--format", "deployment-plan"])
        assert result.exit_code == 0
        assert "Deployment plan exported" in result.output

        plan_path = tmp_migrations_dir / "test-project" / "exports" / "deployment-plan.md"
        assert plan_path.exists()
        assert "Deployment Plan" in plan_path.read_text()

    def test_export_unknown_format(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])
        result = runner.invoke(app, ["export", "--format", "xml"])
        assert result.exit_code == 1
        assert "Unknown format" in result.output


# ===================================================================
# INVENTORY
# ===================================================================


class TestInventory:
    def test_inventory_empty(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])
        result = runner.invoke(app, ["inventory"])
        assert result.exit_code == 0
        assert "No objects" in result.output

    def test_inventory_with_objects(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])
        project_dir = tmp_migrations_dir / "test-project"

        # Seed some objects
        from wxcli.migration.models import MigrationObject, MigrationStatus, Provenance
        from wxcli.migration.store import MigrationStore
        from datetime import datetime, timezone

        store = MigrationStore(project_dir / "migration.db")
        for i in range(3):
            obj = MigrationObject(
                canonical_id=f"user:{i:04d}",
                provenance=Provenance(
                    source_system="cucm",
                    source_id=f"pkid-{i}",
                    source_name=f"user{i}",
                    extracted_at=datetime.now(timezone.utc),
                ),
                status=MigrationStatus.DISCOVERED,
            )
            store.upsert_object(obj)
        store.close()

        result = runner.invoke(app, ["inventory"])
        assert result.exit_code == 0
        # Should show count for user type (MigrationObject base class uses canonical_id prefix)

    def test_inventory_filter(self, tmp_migrations_dir):
        runner.invoke(app, ["init", "test-project"])
        result = runner.invoke(app, ["inventory", "--type", "nonexistent"])
        assert result.exit_code == 0
        assert "No" in result.output


# ===================================================================
# HELP TEXT
# ===================================================================


class TestHelp:
    def test_cucm_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "cucm" in result.output.lower() or "CUCM" in result.output

    def test_discover_help(self):
        result = runner.invoke(app, ["discover", "--help"])
        assert result.exit_code == 0
        assert "--host" in result.output
        assert "--username" in result.output

    def test_decisions_help(self):
        result = runner.invoke(app, ["decisions", "--help"])
        assert result.exit_code == 0
        assert "--type" in result.output

    def test_export_help(self):
        result = runner.invoke(app, ["export", "--help"])
        assert result.exit_code == 0
        assert "deployment-plan" in result.output
