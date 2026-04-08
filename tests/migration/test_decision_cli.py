"""CLI integration tests for --export-review and --apply-auto."""

import hashlib
import json
import pytest
from typer.testing import CliRunner

from wxcli.commands.cucm import app, MIGRATIONS_DIR
from wxcli.migration.store import MigrationStore


runner = CliRunner()


@pytest.fixture(autouse=True)
def tmp_migrations_dir(tmp_path, monkeypatch):
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    current_file = tmp_path / "current_project"
    monkeypatch.setattr("wxcli.commands.cucm.MIGRATIONS_DIR", migrations_dir)
    monkeypatch.setattr("wxcli.commands.cucm.CURRENT_PROJECT_FILE", current_file)
    return migrations_dir


def _init_project(name="test-project"):
    runner.invoke(app, ["init", name])


def _seed_decisions(tmp_migrations_dir, project="test-project"):
    """Seed the project store with a mix of decision types."""
    db_path = tmp_migrations_dir / project / "migration.db"
    store = MigrationStore(str(db_path))

    def _save(did, dtype, sev, summary, ctx, opts, affected=None):
        fp = hashlib.sha256(f"{dtype}:{did}".encode()).hexdigest()[:16]
        c = dict(ctx)
        if affected:
            c["_affected_objects"] = affected
        store.save_decision({
            "decision_id": did, "type": dtype, "severity": sev,
            "summary": summary, "context": c, "options": opts,
            "chosen_option": None, "fingerprint": fp, "run_id": "test",
        })

    # Auto-apply: incompatible device
    _save("D001", "DEVICE_INCOMPATIBLE", "HIGH", "CSF is incompatible",
          {"device_id": "device:CSF001", "device_name": "CSF001",
           "compatibility_tier": "incompatible"},
          [{"id": "skip", "label": "Skip"}, {"id": "manual", "label": "Replace"}],
          ["device:CSF001"])

    # Auto-apply: missing data on same incompatible device
    _save("D002", "MISSING_DATA", "HIGH", "device:CSF001 missing mac",
          {"object_type": "device", "canonical_id": "device:CSF001",
           "missing_fields": ["mac"]},
          [{"id": "provide_data", "label": "Provide"}, {"id": "skip", "label": "Skip"}],
          ["device:CSF001"])

    # Needs-input: workspace license
    _save("D003", "WORKSPACE_LICENSE_TIER", "MEDIUM", "Lobby phone license",
          {"workspace_name": "Lobby"},
          [{"id": "workspace", "label": "Basic"}, {"id": "professional", "label": "Pro"},
           {"id": "skip", "label": "Skip"}])

    # Auto-apply: firmware convertible (matches new DEVICE_FIRMWARE_CONVERTIBLE default rule)
    _save("D004", "DEVICE_FIRMWARE_CONVERTIBLE", "MEDIUM", "7841 can convert",
          {"device_name": "SEP112233", "model": "7841"},
          [{"id": "convert", "label": "Convert"}, {"id": "skip", "label": "Skip"}])

    store.close()


class TestExportReview:
    def test_creates_markdown_file(self, tmp_migrations_dir):
        _init_project()
        _seed_decisions(tmp_migrations_dir)
        result = runner.invoke(app, ["decisions", "--export-review", "-p", "test-project"])
        assert result.exit_code == 0
        review_path = tmp_migrations_dir / "test-project" / "exports" / "decision-review.md"
        assert review_path.exists()
        content = review_path.read_text()
        assert "## Auto-Apply" in content
        assert "## Needs Your Input" in content

    def test_prints_summary_counts(self, tmp_migrations_dir):
        _init_project()
        _seed_decisions(tmp_migrations_dir)
        result = runner.invoke(app, ["decisions", "--export-review", "-p", "test-project"])
        assert "Auto-apply: 2 decisions" in result.output
        assert "Needs input: 2 decisions" in result.output

    def test_json_output_has_structured_data(self, tmp_migrations_dir):
        _init_project()
        _seed_decisions(tmp_migrations_dir)
        result = runner.invoke(app, ["decisions", "--export-review", "-o", "json", "-p", "test-project"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "review_file" in data
        assert len(data["auto_apply"]) == 2
        assert len(data["needs_input"]) == 2

    def test_json_includes_review_file_path(self, tmp_migrations_dir):
        _init_project()
        _seed_decisions(tmp_migrations_dir)
        result = runner.invoke(app, ["decisions", "--export-review", "-o", "json", "-p", "test-project"])
        data = json.loads(result.output)
        assert "decision-review.md" in data["review_file"]

    def test_json_auto_apply_has_choice_and_reason(self, tmp_migrations_dir):
        _init_project()
        _seed_decisions(tmp_migrations_dir)
        result = runner.invoke(app, ["decisions", "--export-review", "-o", "json", "-p", "test-project"])
        data = json.loads(result.output)
        for d in data["auto_apply"]:
            assert d["auto_choice"] is not None
            assert d["auto_reason"] is not None

    def test_no_pending_decisions(self, tmp_migrations_dir):
        _init_project()
        # No decisions seeded
        result = runner.invoke(app, ["decisions", "--export-review", "-p", "test-project"])
        assert result.exit_code == 0
        assert "Auto-apply: 0 decisions" in result.output


class TestApplyAuto:
    def test_resolves_only_auto_decisions(self, tmp_migrations_dir):
        _init_project()
        _seed_decisions(tmp_migrations_dir)
        result = runner.invoke(app, ["decide", "--apply-auto", "-y", "-p", "test-project"])
        assert result.exit_code == 0
        assert "Auto-applied 2 decisions" in result.output

        # Verify: D001 and D002 resolved, D003 and D004 still pending
        db_path = tmp_migrations_dir / "test-project" / "migration.db"
        store = MigrationStore(str(db_path))
        d1 = store.get_decision("D001")
        d2 = store.get_decision("D002")
        d3 = store.get_decision("D003")
        d4 = store.get_decision("D004")
        assert d1["chosen_option"] == "skip"
        assert d2["chosen_option"] == "skip"
        assert d3["chosen_option"] is None  # needs-input, untouched
        assert d4["chosen_option"] is None  # needs-input, untouched
        store.close()

    def test_resolved_by_auto_apply(self, tmp_migrations_dir):
        _init_project()
        _seed_decisions(tmp_migrations_dir)
        runner.invoke(app, ["decide", "--apply-auto", "-y", "-p", "test-project"])
        db_path = tmp_migrations_dir / "test-project" / "migration.db"
        store = MigrationStore(str(db_path))
        d1 = store.get_decision("D001")
        assert d1["resolved_by"] == "auto_apply"
        store.close()

    def test_no_auto_decisions_found(self, tmp_migrations_dir):
        _init_project()
        # No decisions seeded
        result = runner.invoke(app, ["decide", "--apply-auto", "-y", "-p", "test-project"])
        assert result.exit_code == 0
        assert "No auto-resolvable decisions" in result.output

    def test_prompts_without_yes_flag(self, tmp_migrations_dir):
        _init_project()
        _seed_decisions(tmp_migrations_dir)
        # Without -y, should prompt. CliRunner sends no input → cancelled
        result = runner.invoke(app, ["decide", "--apply-auto", "-p", "test-project"])
        # Should show the summary but not apply (no confirmation input)
        assert "DEVICE_INCOMPATIBLE" in result.output


class TestExportReviewConfigThreading:
    """--export-review must load config.json and thread it through to
    classify_decisions and generate_decision_review, so custom auto_rules
    show up in the markdown review file's Auto-Apply section."""

    def test_export_review_honors_custom_auto_rule(self, tmp_migrations_dir):
        _init_project()

        # Edit config.json to add a custom rule matching DN_AMBIGUOUS
        # decisions with 3-digit DNs.
        project_dir = tmp_migrations_dir / "test-project"
        config_path = project_dir / "config.json"
        config = json.loads(config_path.read_text())
        config["auto_rules"].append({
            "type": "DN_AMBIGUOUS",
            "match": {"dn_length_lte": 3},
            "choice": "extension_only",
            "reason": "3-digit extensions are internal",
        })
        config_path.write_text(json.dumps(config, indent=2))

        # Seed one DN_AMBIGUOUS decision with dn_length=3.
        db_path = project_dir / "migration.db"
        store = MigrationStore(str(db_path))
        fp = hashlib.sha256(b"DN_AMBIGUOUS:D_DN_01").hexdigest()[:16]
        store.save_decision({
            "decision_id": "D_DN_01",
            "type": "DN_AMBIGUOUS",
            "severity": "LOW",
            "summary": "3-digit DN ambiguous",
            "context": {"dn_length": 3, "dn": "101"},
            "options": [
                {"id": "extension_only", "label": "Extension", "impact": "Internal"},
                {"id": "skip", "label": "Skip", "impact": "Excluded"},
            ],
            "chosen_option": None,
            "fingerprint": fp,
            "run_id": "test",
        })
        store.close()

        result = runner.invoke(
            app,
            ["decisions", "--export-review", "-o", "json", "-p", "test-project"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)

        auto_ids = {d["decision_id"] for d in data["auto_apply"]}
        assert "D_DN_01" in auto_ids, (
            f"Custom auto_rules rule was not applied by --export-review. "
            f"auto_apply: {data['auto_apply']}"
        )

    def test_export_review_custom_reason_in_markdown(self, tmp_migrations_dir):
        """The custom rule's `reason` must appear in the rendered markdown."""
        _init_project()

        project_dir = tmp_migrations_dir / "test-project"
        config_path = project_dir / "config.json"
        config = json.loads(config_path.read_text())
        config["auto_rules"].append({
            "type": "DN_AMBIGUOUS",
            "match": {"dn_length_lte": 3},
            "choice": "extension_only",
            "reason": "3-digit extensions are internal per the dial plan",
        })
        config_path.write_text(json.dumps(config, indent=2))

        db_path = project_dir / "migration.db"
        store = MigrationStore(str(db_path))
        fp = hashlib.sha256(b"DN_AMBIGUOUS:D_DN_02").hexdigest()[:16]
        store.save_decision({
            "decision_id": "D_DN_02",
            "type": "DN_AMBIGUOUS",
            "severity": "LOW",
            "summary": "3-digit DN ambiguous",
            "context": {"dn_length": 3, "dn": "101"},
            "options": [
                {"id": "extension_only", "label": "Extension", "impact": "Internal"},
                {"id": "skip", "label": "Skip", "impact": "Excluded"},
            ],
            "chosen_option": None,
            "fingerprint": fp,
            "run_id": "test",
        })
        store.close()

        runner.invoke(app, ["decisions", "--export-review", "-p", "test-project"])

        review_path = project_dir / "exports" / "decision-review.md"
        md = review_path.read_text()
        assert "3-digit extensions are internal per the dial plan" in md
