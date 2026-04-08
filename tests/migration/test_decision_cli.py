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
        # --export-review now runs enrich_cross_decision_context before
        # classification, matching --apply-auto. D002 (MISSING_DATA on the
        # same incompatible device as D001) is auto-classified via the
        # is_on_incompatible_device field → 3 auto, 1 needs-input.
        assert "Auto-apply: 3 decisions" in result.output
        assert "Needs input: 1 decisions" in result.output

    def test_json_output_has_structured_data(self, tmp_migrations_dir):
        _init_project()
        _seed_decisions(tmp_migrations_dir)
        result = runner.invoke(app, ["decisions", "--export-review", "-o", "json", "-p", "test-project"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "review_file" in data
        # D002 now auto-classifies via enriched is_on_incompatible_device
        # field → 3 auto, 1 needs-input (unified with --apply-auto).
        assert len(data["auto_apply"]) == 3
        assert len(data["needs_input"]) == 1

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

    def test_export_review_runs_enrichment(self, tmp_migrations_dir):
        """--export-review must run enrich_cross_decision_context before
        classification so MISSING_DATA-on-incompatible decisions get the
        is_on_incompatible_device field, matching --apply-auto's behavior.
        Without enrichment, the preview counts would undercount relative
        to what --apply-auto actually resolves (the Phase C asymmetry fix).
        """
        _init_project()

        project_dir = tmp_migrations_dir / "test-project"
        db_path = project_dir / "migration.db"
        store = MigrationStore(str(db_path))

        # Seed a DEVICE_INCOMPATIBLE + MISSING_DATA pair on the same device.
        # The MISSING_DATA context deliberately omits is_on_incompatible_device
        # to simulate a project whose analyze ran without enrichment.
        fp_di = hashlib.sha256(b"DEVICE_INCOMPATIBLE:EXR_DI_01").hexdigest()[:16]
        store.save_decision({
            "decision_id": "EXR_DI_01",
            "type": "DEVICE_INCOMPATIBLE",
            "severity": "HIGH",
            "summary": "Legacy device",
            "context": {"device_id": "phone:old", "_affected_objects": ["phone:old"]},
            "options": [
                {"id": "skip", "label": "Skip", "impact": "Not migrated"},
                {"id": "manual", "label": "Manual", "impact": "Replace"},
            ],
            "chosen_option": None,
            "fingerprint": fp_di,
            "run_id": "test",
        })
        fp_md = hashlib.sha256(b"MISSING_DATA:EXR_MD_01").hexdigest()[:16]
        store.save_decision({
            "decision_id": "EXR_MD_01",
            "type": "MISSING_DATA",
            "severity": "MEDIUM",
            "summary": "phone:old missing mac",
            "context": {
                "object_type": "device",
                "canonical_id": "phone:old",
                "missing_fields": ["mac"],
                # Deliberately no is_on_incompatible_device field.
            },
            "options": [
                {"id": "skip", "label": "Skip", "impact": "Excluded"},
                {"id": "provide_data", "label": "Provide", "impact": "Supply"},
            ],
            "chosen_option": None,
            "fingerprint": fp_md,
            "run_id": "test",
        })
        store.close()

        result = runner.invoke(
            app,
            ["decisions", "--export-review", "-o", "json", "-p", "test-project"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)

        # Both decisions must appear in auto_apply. If enrichment did not
        # run, EXR_MD_01 would land in needs_input because the MISSING_DATA
        # default rule requires is_on_incompatible_device == true.
        auto_ids = {d["decision_id"] for d in data["auto_apply"]}
        assert "EXR_DI_01" in auto_ids
        assert "EXR_MD_01" in auto_ids, (
            "MISSING_DATA on incompatible device was not auto-classified — "
            "enrich_cross_decision_context may not be running in the "
            f"--export-review path. auto_apply: {data['auto_apply']}"
        )


class TestApplyAuto:
    def test_resolves_only_auto_decisions(self, tmp_migrations_dir):
        _init_project()
        _seed_decisions(tmp_migrations_dir)
        result = runner.invoke(app, ["decide", "--apply-auto", "-y", "-p", "test-project"])
        assert result.exit_code == 0
        # D001 (DEVICE_INCOMPATIBLE), D002 (MISSING_DATA on incompatible device
        # via enrichment), and D004 (DEVICE_FIRMWARE_CONVERTIBLE) all match
        # default auto-rules.
        assert "Auto-applied 3 decisions" in result.output

        # Verify: D001, D002, D004 resolved; D003 still pending.
        db_path = tmp_migrations_dir / "test-project" / "migration.db"
        store = MigrationStore(str(db_path))
        d1 = store.get_decision("D001")
        d2 = store.get_decision("D002")
        d3 = store.get_decision("D003")
        d4 = store.get_decision("D004")
        assert d1["chosen_option"] == "skip"
        assert d2["chosen_option"] == "skip"  # via is_on_incompatible_device
        assert d3["chosen_option"] is None     # needs-input, untouched
        assert d4["chosen_option"] == "convert"
        store.close()

    def test_resolved_by_auto_rule(self, tmp_migrations_dir):
        _init_project()
        _seed_decisions(tmp_migrations_dir)
        runner.invoke(app, ["decide", "--apply-auto", "-y", "-p", "test-project"])
        db_path = tmp_migrations_dir / "test-project" / "migration.db"
        store = MigrationStore(str(db_path))
        d1 = store.get_decision("D001")
        # Unified matcher writes the "auto_rule" marker, not the legacy "auto_apply".
        assert d1["resolved_by"] == "auto_rule"
        store.close()

    def test_no_auto_decisions_found(self, tmp_migrations_dir):
        _init_project()
        # No decisions seeded
        result = runner.invoke(app, ["decide", "--apply-auto", "-y", "-p", "test-project"])
        assert result.exit_code == 0
        assert "No pending decisions match current auto-rules" in result.output

    def test_prompts_without_yes_flag(self, tmp_migrations_dir):
        _init_project()
        _seed_decisions(tmp_migrations_dir)
        # Without -y, should prompt. CliRunner sends no input → cancelled
        result = runner.invoke(app, ["decide", "--apply-auto", "-p", "test-project"])
        # Should show the summary but not apply (no confirmation input)
        assert "DEVICE_INCOMPATIBLE" in result.output

    def test_decide_apply_auto_runs_config_rules(self, tmp_migrations_dir):
        """--apply-auto runs the project's config auto_rules, not a
        hardcoded list."""
        _init_project()

        # Seed one decision that matches a custom rule.
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

        db_path = project_dir / "migration.db"
        store = MigrationStore(str(db_path))
        fp = hashlib.sha256(b"DN_AMBIGUOUS:D_APPLY_01").hexdigest()[:16]
        store.save_decision({
            "decision_id": "D_APPLY_01",
            "type": "DN_AMBIGUOUS",
            "severity": "LOW",
            "summary": "3-digit DN",
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
            app, ["decide", "--apply-auto", "-y", "-p", "test-project"]
        )
        assert result.exit_code == 0

        store = MigrationStore(str(db_path))
        d = store.get_decision("D_APPLY_01")
        assert d["chosen_option"] == "extension_only"
        assert d["resolved_by"] == "auto_rule"
        store.close()

    def test_decide_apply_auto_picks_up_config_edits(self, tmp_migrations_dir):
        """Editing config.json between runs must change what --apply-auto
        resolves — no need to re-run analyze."""
        _init_project()

        project_dir = tmp_migrations_dir / "test-project"
        db_path = project_dir / "migration.db"

        store = MigrationStore(str(db_path))
        fp = hashlib.sha256(b"DN_AMBIGUOUS:D_EDIT_01").hexdigest()[:16]
        store.save_decision({
            "decision_id": "D_EDIT_01",
            "type": "DN_AMBIGUOUS",
            "severity": "LOW",
            "summary": "5-digit DN",
            "context": {"dn_length": 5, "dn": "10101"},
            "options": [
                {"id": "extension_only", "label": "Extension", "impact": "Internal"},
                {"id": "skip", "label": "Skip", "impact": "Excluded"},
            ],
            "chosen_option": None,
            "fingerprint": fp,
            "run_id": "test",
        })
        store.close()

        # First run: no matching rule → no resolution.
        result1 = runner.invoke(
            app, ["decide", "--apply-auto", "-y", "-p", "test-project"]
        )
        assert result1.exit_code == 0

        store = MigrationStore(str(db_path))
        assert store.get_decision("D_EDIT_01")["chosen_option"] is None
        store.close()

        # Edit config.json to add a rule that matches.
        config_path = project_dir / "config.json"
        config = json.loads(config_path.read_text())
        config["auto_rules"].append({
            "type": "DN_AMBIGUOUS",
            "match": {"dn_length_lte": 5},
            "choice": "extension_only",
            "reason": "5-digit internal plan",
        })
        config_path.write_text(json.dumps(config, indent=2))

        # Second run: edit is picked up, D_EDIT_01 resolves.
        result2 = runner.invoke(
            app, ["decide", "--apply-auto", "-y", "-p", "test-project"]
        )
        assert result2.exit_code == 0

        store = MigrationStore(str(db_path))
        assert store.get_decision("D_EDIT_01")["chosen_option"] == "extension_only"
        store.close()

    def test_decide_apply_auto_runs_enrichment(self, tmp_migrations_dir):
        """--apply-auto must run enrich_cross_decision_context so
        MISSING_DATA-on-incompatible decisions get the is_on_incompatible_device
        field before rules fire, even if analyze ran before enrichment
        was added."""
        _init_project()

        project_dir = tmp_migrations_dir / "test-project"
        db_path = project_dir / "migration.db"
        store = MigrationStore(str(db_path))

        # Seed a DEVICE_INCOMPATIBLE + MISSING_DATA pair on the same device,
        # simulating a project whose analyze ran without enrichment.
        fp_di = hashlib.sha256(b"DEVICE_INCOMPATIBLE:D_DI_01").hexdigest()[:16]
        store.save_decision({
            "decision_id": "D_DI_01",
            "type": "DEVICE_INCOMPATIBLE",
            "severity": "HIGH",
            "summary": "Legacy device",
            "context": {"device_id": "phone:old", "_affected_objects": ["phone:old"]},
            "options": [
                {"id": "skip", "label": "Skip", "impact": "Not migrated"},
                {"id": "manual", "label": "Manual", "impact": "Replace"},
            ],
            "chosen_option": None,
            "fingerprint": fp_di,
            "run_id": "test",
        })
        fp_md = hashlib.sha256(b"MISSING_DATA:D_MD_01").hexdigest()[:16]
        store.save_decision({
            "decision_id": "D_MD_01",
            "type": "MISSING_DATA",
            "severity": "MEDIUM",
            "summary": "phone:old missing mac",
            "context": {
                "object_type": "device",
                "canonical_id": "phone:old",
                "missing_fields": ["mac"],
                # Deliberately no is_on_incompatible_device field.
            },
            "options": [
                {"id": "skip", "label": "Skip", "impact": "Excluded"},
                {"id": "provide_data", "label": "Provide", "impact": "Supply"},
            ],
            "chosen_option": None,
            "fingerprint": fp_md,
            "run_id": "test",
        })
        store.close()

        result = runner.invoke(
            app, ["decide", "--apply-auto", "-y", "-p", "test-project"]
        )
        assert result.exit_code == 0

        store = MigrationStore(str(db_path))
        # Both the DI and MD decisions are auto-resolved via default rules
        # (MD requires the enrichment step to have run first).
        assert store.get_decision("D_DI_01")["chosen_option"] == "skip"
        assert store.get_decision("D_MD_01")["chosen_option"] == "skip"
        store.close()

    def test_existing_project_without_new_default_rule_still_runs(
        self, tmp_migrations_dir
    ):
        """Backwards compat: a project whose config.json was seeded before
        the new MISSING_DATA default rule existed must still run without
        crashing. MISSING_DATA-on-incompatible decisions stay pending
        (not auto-resolved) because the rule isn't in the saved config."""
        _init_project()

        project_dir = tmp_migrations_dir / "test-project"
        config_path = project_dir / "config.json"

        # Overwrite config.json with ONLY the old 7 defaults (no new rule).
        legacy_rules = [
            {"type": "DEVICE_INCOMPATIBLE", "choice": "skip"},
            {"type": "DEVICE_FIRMWARE_CONVERTIBLE", "choice": "convert"},
            {"type": "HOTDESK_DN_CONFLICT", "choice": "keep_primary"},
            {"type": "FORWARDING_LOSSY", "choice": "accept_loss"},
            {"type": "SNR_LOSSY", "choice": "accept_loss"},
            {"type": "BUTTON_UNMAPPABLE", "choice": "accept_loss"},
            {"type": "CALLING_PERMISSION_MISMATCH",
             "match": {"assigned_users_count": 0}, "choice": "skip"},
        ]
        config = json.loads(config_path.read_text())
        config["auto_rules"] = legacy_rules
        config_path.write_text(json.dumps(config, indent=2))

        db_path = project_dir / "migration.db"
        store = MigrationStore(str(db_path))
        fp_di = hashlib.sha256(b"DEVICE_INCOMPATIBLE:D_DI_L").hexdigest()[:16]
        store.save_decision({
            "decision_id": "D_DI_L",
            "type": "DEVICE_INCOMPATIBLE",
            "severity": "HIGH",
            "summary": "Legacy device",
            "context": {"device_id": "phone:old", "_affected_objects": ["phone:old"]},
            "options": [
                {"id": "skip", "label": "Skip", "impact": "Not migrated"},
                {"id": "manual", "label": "Manual", "impact": "Replace"},
            ],
            "chosen_option": None,
            "fingerprint": fp_di,
            "run_id": "test",
        })
        fp_md = hashlib.sha256(b"MISSING_DATA:D_MD_L").hexdigest()[:16]
        store.save_decision({
            "decision_id": "D_MD_L",
            "type": "MISSING_DATA",
            "severity": "MEDIUM",
            "summary": "phone:old missing mac",
            "context": {
                "object_type": "device",
                "canonical_id": "phone:old",
                "missing_fields": ["mac"],
            },
            "options": [
                {"id": "skip", "label": "Skip", "impact": "Excluded"},
                {"id": "provide_data", "label": "Provide", "impact": "Supply"},
            ],
            "chosen_option": None,
            "fingerprint": fp_md,
            "run_id": "test",
        })
        store.close()

        result = runner.invoke(
            app, ["decide", "--apply-auto", "-y", "-p", "test-project"]
        )
        assert result.exit_code == 0

        store = MigrationStore(str(db_path))
        # D_DI_L resolved via legacy DEVICE_INCOMPATIBLE rule.
        assert store.get_decision("D_DI_L")["chosen_option"] == "skip"
        # D_MD_L stays pending — legacy config has no rule for it.
        assert store.get_decision("D_MD_L")["chosen_option"] is None
        store.close()

    def test_decide_apply_auto_empty_store(self, tmp_migrations_dir):
        """Empty store: --apply-auto prints 'no pending' and exits 0."""
        _init_project()
        result = runner.invoke(
            app, ["decide", "--apply-auto", "-y", "-p", "test-project"]
        )
        assert result.exit_code == 0
        assert "No pending decisions" in result.output or "No auto-resolvable" in result.output


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
