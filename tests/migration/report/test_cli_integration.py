"""CLI integration tests for the ``report`` and ``discover --from-file`` commands.

Tests invoke commands via Typer's CliRunner against a temp project directory,
verifying exit codes, output messages, and side effects (files created, state
updated).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from wxcli.commands.cucm import app


runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def tmp_migrations_dir(tmp_path, monkeypatch):
    """Redirect MIGRATIONS_DIR and CURRENT_PROJECT_FILE to a temp directory."""
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    current_file = tmp_path / "current_project"
    monkeypatch.setattr("wxcli.commands.cucm.MIGRATIONS_DIR", migrations_dir)
    monkeypatch.setattr("wxcli.commands.cucm.CURRENT_PROJECT_FILE", current_file)
    return migrations_dir


def _init_project(name: str = "test-project") -> None:
    """Create a project via the CLI init command."""
    result = runner.invoke(app, ["init", name])
    assert result.exit_code == 0, f"init failed: {result.output}"


def _advance_stages(
    project_dir: Path,
    stages: list[str],
) -> None:
    """Fake-complete pipeline stages in state.json."""
    state_path = project_dir / "state.json"
    state = json.loads(state_path.read_text())
    for stage in stages:
        if stage not in state.get("completed_stages", []):
            state.setdefault("completed_stages", []).append(stage)
    state_path.write_text(json.dumps(state, indent=2))


# ===================================================================
# REPORT COMMAND
# ===================================================================


class TestReport:
    """Tests for ``wxcli cucm report``."""

    def test_report_requires_brand_and_prepared_by(self, tmp_migrations_dir):
        """Calling report without --brand (a required option) should fail."""
        _init_project()
        project_dir = tmp_migrations_dir / "test-project"
        _advance_stages(project_dir, ["discover", "normalize", "map", "analyze"])

        # Missing --brand (required) — Typer should reject before our code runs
        result = runner.invoke(app, ["report", "--prepared-by", "Alice"])
        assert result.exit_code != 0
        assert "brand" in result.output.lower() or "missing" in result.output.lower()

    def test_report_requires_analyze_stage(self, tmp_migrations_dir):
        """Calling report on a project that hasn't been analyzed should fail."""
        _init_project()
        # Project has only "init" completed — no analyze
        result = runner.invoke(
            app,
            ["report", "--brand", "Acme", "--prepared-by", "Alice"],
        )
        assert result.exit_code == 1
        assert "analyze" in result.output.lower()

    def test_report_requires_analyze_stage_with_partial_pipeline(self, tmp_migrations_dir):
        """Report fails even if discover+normalize+map are done, but not analyze."""
        _init_project()
        project_dir = tmp_migrations_dir / "test-project"
        _advance_stages(project_dir, ["discover", "normalize", "map"])

        result = runner.invoke(
            app,
            ["report", "--brand", "Acme", "--prepared-by", "Alice"],
        )
        assert result.exit_code == 1
        assert "analyze" in result.output.lower()

    def test_report_generates_html(self, tmp_migrations_dir, populated_store):
        """Report with all prerequisites met should produce an HTML file."""
        _init_project()
        project_dir = tmp_migrations_dir / "test-project"
        _advance_stages(project_dir, ["discover", "normalize", "map", "analyze"])

        # Copy the populated store's database into the project directory
        import shutil

        src_db = Path(str(populated_store.db_path))
        dst_db = project_dir / "migration.db"
        populated_store.close()
        shutil.copy2(src_db, dst_db)

        result = runner.invoke(
            app,
            [
                "report",
                "--brand", "Acme Corp",
                "--prepared-by", "Alice Engineer",
                "--output", "test-report",
            ],
        )
        assert result.exit_code == 0, f"report failed: {result.output}"
        assert "report generated" in result.output.lower()

        html_path = project_dir / "test-report.html"
        assert html_path.exists()
        html_content = html_path.read_text(encoding="utf-8")
        assert "Acme Corp" in html_content


# ===================================================================
# DISCOVER --from-file
# ===================================================================


class TestDiscoverFromFile:
    """Tests for ``wxcli cucm discover --from-file``."""

    @patch("wxcli.migration.store.MigrationStore.add_journal_entry")
    def test_discover_from_file_creates_raw_data(
        self, _mock_journal, tmp_migrations_dir, sample_collector_file
    ):
        """Loading a valid collector file should create raw_data.json."""
        _init_project()

        result = runner.invoke(
            app,
            ["discover", "--from-file", str(sample_collector_file)],
        )
        assert result.exit_code == 0, f"discover --from-file failed: {result.output}"
        assert "file ingestion complete" in result.output.lower()

        # raw_data.json should exist in the project directory
        project_dir = tmp_migrations_dir / "test-project"
        raw_data_path = project_dir / "raw_data.json"
        assert raw_data_path.exists()

        raw_data = json.loads(raw_data_path.read_text())
        assert isinstance(raw_data, dict)
        # Should have the expected top-level groups from ingest
        assert "devices" in raw_data
        assert "users" in raw_data

    @patch("wxcli.migration.store.MigrationStore.add_journal_entry")
    def test_discover_from_file_marks_stage_complete(
        self, _mock_journal, tmp_migrations_dir, sample_collector_file
    ):
        """After ingestion, discover should be marked complete in state.json."""
        _init_project()

        runner.invoke(
            app,
            ["discover", "--from-file", str(sample_collector_file)],
        )

        project_dir = tmp_migrations_dir / "test-project"
        state = json.loads((project_dir / "state.json").read_text())
        assert "discover" in state["completed_stages"]

    @patch("wxcli.migration.store.MigrationStore.add_journal_entry")
    def test_discover_from_file_saves_metadata_to_config(
        self, _mock_journal, tmp_migrations_dir, sample_collector_file
    ):
        """Collector metadata (cucm_version, cluster_name) should be saved to config."""
        _init_project()

        runner.invoke(
            app,
            ["discover", "--from-file", str(sample_collector_file)],
        )

        project_dir = tmp_migrations_dir / "test-project"
        config = json.loads((project_dir / "config.json").read_text())
        assert config["cucm_version"] == "14.0.1.13900-155"
        assert config["cluster_name"] == "CUCM-LAB"

    def test_discover_from_file_missing_file(self, tmp_migrations_dir):
        """Referencing a nonexistent collector file should fail."""
        _init_project()

        result = runner.invoke(
            app,
            ["discover", "--from-file", "/nonexistent/collector.json.gz"],
        )
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_discover_rejects_no_source(self, tmp_migrations_dir):
        """Calling discover without --host or --from-file should fail."""
        _init_project()

        result = runner.invoke(app, ["discover"])
        assert result.exit_code == 1
        assert "--from-file" in result.output or "--host" in result.output
