"""Tests for user communication notice generator."""

from __future__ import annotations

import re

import pytest


class TestNoticeTemplates:
    """Tests for notice_templates.py scenario registry."""

    def test_scenarios_dict_has_all_seven_keys(self):
        from wxcli.migration.report.notice_templates import SCENARIOS

        expected = {
            "phone_upgrade",
            "webex_app_transition",
            "forwarding_simplified",
            "voicemail_rerecord",
            "layout_changes",
            "exec_assistant",
            "device_replacement",
        }
        assert set(SCENARIOS.keys()) == expected

    def test_each_scenario_has_required_fields(self):
        from wxcli.migration.report.notice_templates import SCENARIOS

        required = {"title", "priority", "template", "variables"}
        for key, scenario in SCENARIOS.items():
            missing = required - set(scenario.keys())
            assert not missing, f"Scenario '{key}' missing fields: {missing}"

    def test_scenarios_ordered_by_priority(self):
        from wxcli.migration.report.notice_templates import SCENARIO_ORDER, SCENARIOS

        priorities = [SCENARIOS[s]["priority"] for s in SCENARIO_ORDER]
        assert priorities == sorted(priorities), "SCENARIO_ORDER must be sorted by priority"

    def test_intro_template_has_brand_and_date(self):
        from wxcli.migration.report.notice_templates import INTRO_TEMPLATE

        assert "{brand}" in INTRO_TEMPLATE
        assert "{migration_date}" in INTRO_TEMPLATE

    def test_footer_template_has_helpdesk(self):
        from wxcli.migration.report.notice_templates import FOOTER_TEMPLATE

        assert "{helpdesk}" in FOOTER_TEMPLATE

    def test_timeline_template_has_date_and_helpdesk(self):
        from wxcli.migration.report.notice_templates import TIMELINE_TEMPLATE

        assert "{migration_date}" in TIMELINE_TEMPLATE
        assert "{helpdesk}" in TIMELINE_TEMPLATE


class TestScenarioDetection:
    """Tests for _build_scenario_matrix using the populated_store fixture."""

    def test_matrix_has_entry_per_user(self, populated_store):
        from wxcli.migration.report.user_notice import _build_scenario_matrix

        matrix = _build_scenario_matrix(populated_store)
        assert len(matrix) == 50

    def test_convertible_devices_get_phone_upgrade(self, populated_store):
        from wxcli.migration.report.user_notice import _build_scenario_matrix

        matrix = _build_scenario_matrix(populated_store)
        upgrade_users = [u for u in matrix if "phone_upgrade" in u.scenarios]
        assert len(upgrade_users) == 3
        for u in upgrade_users:
            assert u.device_model == "CP-7841"
            assert u.device_tier == "convertible"

    def test_incompatible_devices_get_device_replacement(self, populated_store):
        from wxcli.migration.report.user_notice import _build_scenario_matrix

        matrix = _build_scenario_matrix(populated_store)
        replacement_users = [u for u in matrix if "device_replacement" in u.scenarios]
        assert len(replacement_users) == 2
        for u in replacement_users:
            assert u.device_model == "CP-7962G"

    def test_voicemail_users_get_voicemail_rerecord(self, populated_store):
        from wxcli.migration.report.user_notice import _build_scenario_matrix

        populated_store.add_cross_ref(
            "user:user-001", "voicemail_profile:vm-default", "user_has_voicemail_profile"
        )
        matrix = _build_scenario_matrix(populated_store)
        vm_users = [u for u in matrix if "voicemail_rerecord" in u.scenarios]
        assert len(vm_users) >= 1
        assert any(u.user_canonical_id == "user:user-001" for u in vm_users)

    def test_native_mpp_users_have_no_device_scenario(self, populated_store):
        from wxcli.migration.report.user_notice import _build_scenario_matrix

        matrix = _build_scenario_matrix(populated_store)
        device_scenarios = {"phone_upgrade", "webex_app_transition", "device_replacement"}
        for u in matrix:
            if u.device_tier == "native_mpp":
                assert not (set(u.scenarios) & device_scenarios), (
                    f"native_mpp user {u.user_canonical_id} should have no device scenario"
                )

    def test_forwarding_lossy_detected(self, populated_store):
        from wxcli.migration.report.user_notice import _build_scenario_matrix

        populated_store.save_decision({
            "decision_id": populated_store.next_decision_id(),
            "type": "FORWARDING_LOSSY",
            "severity": "MEDIUM",
            "summary": "Call forwarding chain simplified",
            "context": {"user_canonical_id": "user:user-005"},
            "options": [{"id": "accept", "label": "Accept"}],
            "fingerprint": "fwd-lossy-005",
            "run_id": "test",
        })
        matrix = _build_scenario_matrix(populated_store)
        fwd_users = [u for u in matrix if "forwarding_simplified" in u.scenarios]
        assert any(u.user_canonical_id == "user:user-005" for u in fwd_users)

    def test_button_unmappable_detected(self, populated_store):
        from wxcli.migration.report.user_notice import _build_scenario_matrix

        populated_store.save_decision({
            "decision_id": populated_store.next_decision_id(),
            "type": "BUTTON_UNMAPPABLE",
            "severity": "LOW",
            "summary": "BLF button cannot be mapped",
            "context": {"user_canonical_id": "user:user-010"},
            "options": [{"id": "accept", "label": "Accept"}],
            "fingerprint": "btn-unmap-010",
            "run_id": "test",
        })
        matrix = _build_scenario_matrix(populated_store)
        layout_users = [u for u in matrix if "layout_changes" in u.scenarios]
        assert any(u.user_canonical_id == "user:user-010" for u in layout_users)

    def test_exec_assistant_detected(self, populated_store):
        from wxcli.migration.report.user_notice import _build_scenario_matrix

        populated_store.save_decision({
            "decision_id": populated_store.next_decision_id(),
            "type": "FEATURE_APPROXIMATION",
            "severity": "MEDIUM",
            "summary": "Executive assistant filtering approximated",
            "context": {"user_canonical_id": "user:user-020"},
            "options": [{"id": "accept", "label": "Accept"}],
            "fingerprint": "exec-assist-020",
            "run_id": "test",
        })
        matrix = _build_scenario_matrix(populated_store)
        exec_users = [u for u in matrix if "exec_assistant" in u.scenarios]
        assert any(u.user_canonical_id == "user:user-020" for u in exec_users)

    def test_empty_store_returns_empty_matrix(self, tmp_path):
        from wxcli.migration.store import MigrationStore
        from wxcli.migration.report.user_notice import _build_scenario_matrix

        store = MigrationStore(tmp_path / "empty.db")
        matrix = _build_scenario_matrix(store)
        assert matrix == []
        store.close()

    def test_user_can_match_multiple_scenarios(self, populated_store):
        from wxcli.migration.report.user_notice import _build_scenario_matrix

        populated_store.save_decision({
            "decision_id": populated_store.next_decision_id(),
            "type": "FORWARDING_LOSSY",
            "severity": "MEDIUM",
            "summary": "Forwarding simplified",
            "context": {"user_canonical_id": "user:user-041"},
            "options": [{"id": "accept", "label": "Accept"}],
            "fingerprint": "fwd-lossy-041",
            "run_id": "test",
        })
        matrix = _build_scenario_matrix(populated_store)
        user_041 = next(u for u in matrix if u.user_canonical_id == "user:user-041")
        assert "phone_upgrade" in user_041.scenarios
        assert "forwarding_simplified" in user_041.scenarios


class TestHtmlGeneration:
    """Tests for generate_user_notice HTML output."""

    def test_returns_valid_html_document(self, populated_store):
        from wxcli.migration.report.user_notice import generate_user_notice

        html = generate_user_notice(
            populated_store,
            brand="Contoso",
            migration_date="January 15, 2027",
            helpdesk="IT Help Desk at ext. 5000",
            prepared_by="Jane Smith",
        )
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html

    def test_brand_substituted_in_intro(self, populated_store):
        from wxcli.migration.report.user_notice import generate_user_notice

        html = generate_user_notice(
            populated_store,
            brand="Contoso",
            migration_date="January 15, 2027",
            helpdesk="helpdesk@contoso.com",
        )
        assert "Contoso" in html

    def test_migration_date_in_timeline(self, populated_store):
        from wxcli.migration.report.user_notice import generate_user_notice

        html = generate_user_notice(
            populated_store,
            brand="Acme",
            migration_date="March 1, 2027",
            helpdesk="x5000",
        )
        assert "March 1, 2027" in html

    def test_helpdesk_in_footer(self, populated_store):
        from wxcli.migration.report.user_notice import generate_user_notice

        html = generate_user_notice(
            populated_store,
            brand="Acme",
            migration_date="Q1 2027",
            helpdesk="help@acme.com",
        )
        assert "help@acme.com" in html

    def test_no_unsubstituted_variables(self, populated_store):
        from wxcli.migration.report.user_notice import generate_user_notice

        html = generate_user_notice(
            populated_store,
            brand="Acme",
            migration_date="Q1 2027",
            helpdesk="x5000",
            prepared_by="Test SE",
        )
        unsubstituted = re.findall(r"\{[a-z_]+\}", html)
        assert unsubstituted == [], f"Unsubstituted variables found: {unsubstituted}"

    def test_scenario_sections_only_for_active_scenarios(self, populated_store):
        from wxcli.migration.report.user_notice import generate_user_notice

        html = generate_user_notice(
            populated_store,
            brand="Acme",
            migration_date="Q1 2027",
            helpdesk="x5000",
        )
        assert "Your Phone Is Being Upgraded" in html
        assert "Your Phone Is Being Replaced" in html
        assert "Instead of Jabber" not in html

    def test_affected_count_shown(self, populated_store):
        from wxcli.migration.report.user_notice import generate_user_notice

        html = generate_user_notice(
            populated_store,
            brand="Acme",
            migration_date="Q1 2027",
            helpdesk="x5000",
        )
        assert "Applies to 3 users" in html

    def test_prepared_by_in_footer(self, populated_store):
        from wxcli.migration.report.user_notice import generate_user_notice

        html = generate_user_notice(
            populated_store,
            brand="Acme",
            migration_date="Q1 2027",
            helpdesk="x5000",
            prepared_by="Jane Smith, Cisco SE",
        )
        assert "Jane Smith, Cisco SE" in html

    def test_email_safe_layout(self, populated_store):
        from wxcli.migration.report.user_notice import generate_user_notice

        html = generate_user_notice(
            populated_store,
            brand="Acme",
            migration_date="Q1 2027",
            helpdesk="x5000",
        )
        assert "max-width" in html
        assert "640px" in html


class TestPlainTextOutput:
    """Tests for generate_user_notice with text_only=True."""

    def test_plain_text_has_no_html_tags(self, populated_store):
        from wxcli.migration.report.user_notice import generate_user_notice

        text = generate_user_notice(
            populated_store,
            brand="Acme",
            migration_date="Q1 2027",
            helpdesk="x5000",
            text_only=True,
        )
        assert "<div" not in text
        assert "<style" not in text
        assert "<!DOCTYPE" not in text

    def test_plain_text_preserves_content(self, populated_store):
        from wxcli.migration.report.user_notice import generate_user_notice

        text = generate_user_notice(
            populated_store,
            brand="Acme",
            migration_date="Q1 2027",
            helpdesk="x5000",
            text_only=True,
        )
        assert "Acme" in text
        assert "Q1 2027" in text
        assert "x5000" in text

    def test_plain_text_headings_underlined(self, populated_store):
        from wxcli.migration.report.user_notice import generate_user_notice

        text = generate_user_notice(
            populated_store,
            brand="Acme",
            migration_date="Q1 2027",
            helpdesk="x5000",
            text_only=True,
        )
        assert "---" in text or "===" in text

    def test_no_unsubstituted_variables_text(self, populated_store):
        from wxcli.migration.report.user_notice import generate_user_notice

        text = generate_user_notice(
            populated_store,
            brand="Acme",
            migration_date="Q1 2027",
            helpdesk="x5000",
            prepared_by="SE",
            text_only=True,
        )
        unsubstituted = re.findall(r"\{[a-z_]+\}", text)
        assert unsubstituted == [], f"Unsubstituted: {unsubstituted}"


class TestAudienceFiltering:
    """Tests for --audience flag behavior."""

    def test_audience_all_includes_all_scenarios(self, populated_store):
        from wxcli.migration.report.user_notice import generate_user_notice

        html = generate_user_notice(
            populated_store,
            brand="Acme",
            migration_date="Q1 2027",
            helpdesk="x5000",
            audience="all",
        )
        assert "Your Phone Is Being Upgraded" in html
        assert "Your Phone Is Being Replaced" in html

    def test_audience_phone_upgrade_filters(self, populated_store):
        from wxcli.migration.report.user_notice import generate_user_notice

        html = generate_user_notice(
            populated_store,
            brand="Acme",
            migration_date="Q1 2027",
            helpdesk="x5000",
            audience="phone-upgrade",
        )
        assert "Your Phone Is Being Upgraded" in html or "Your Phone Is Being Replaced" in html

    def test_audience_general_excludes_device_scenarios(self, populated_store):
        from wxcli.migration.report.user_notice import generate_user_notice

        html = generate_user_notice(
            populated_store,
            brand="Acme",
            migration_date="Q1 2027",
            helpdesk="x5000",
            audience="general",
        )
        assert "Your Phone Is Being Upgraded" not in html
        assert "Your Phone Is Being Replaced" not in html


class TestCliIntegration:
    """Tests for wxcli cucm user-notice CLI command."""

    def test_cli_user_notice_exits_zero(self, populated_store, tmp_path):
        from unittest.mock import patch
        from typer.testing import CliRunner
        from wxcli.commands.cucm import app

        runner = CliRunner()
        with (
            patch("wxcli.commands.cucm._resolve_project_dir", return_value=tmp_path),
            patch("wxcli.commands.cucm._completed_stages", return_value={"discover", "normalize", "map", "analyze"}),
            patch("wxcli.commands.cucm._open_store", return_value=populated_store),
        ):
            result = runner.invoke(app, [
                "user-notice",
                "--brand", "TestCo",
                "--migration-date", "Jan 2027",
                "--helpdesk", "x5000",
            ])
        assert result.exit_code == 0, f"CLI failed: {result.output}"
        output_file = tmp_path / "user-notice.html"
        assert output_file.exists()
        content = output_file.read_text()
        assert "TestCo" in content
        assert "<!DOCTYPE html>" in content

    def test_cli_text_only_flag(self, populated_store, tmp_path):
        from unittest.mock import patch
        from typer.testing import CliRunner
        from wxcli.commands.cucm import app

        runner = CliRunner()
        with (
            patch("wxcli.commands.cucm._resolve_project_dir", return_value=tmp_path),
            patch("wxcli.commands.cucm._completed_stages", return_value={"discover", "normalize", "map", "analyze"}),
            patch("wxcli.commands.cucm._open_store", return_value=populated_store),
        ):
            result = runner.invoke(app, [
                "user-notice",
                "--brand", "TestCo",
                "--migration-date", "Jan 2027",
                "--helpdesk", "x5000",
                "--text-only",
            ])
        assert result.exit_code == 0, f"CLI failed: {result.output}"
        output_file = tmp_path / "user-notice.txt"
        assert output_file.exists()
        content = output_file.read_text()
        assert "<!DOCTYPE" not in content
        assert "TestCo" in content

    def test_cli_rejects_without_analyze(self, tmp_path):
        from unittest.mock import patch
        from typer.testing import CliRunner
        from wxcli.commands.cucm import app

        runner = CliRunner()
        with (
            patch("wxcli.commands.cucm._resolve_project_dir", return_value=tmp_path),
            patch("wxcli.commands.cucm._completed_stages", return_value={"discover", "normalize"}),
        ):
            result = runner.invoke(app, [
                "user-notice",
                "--brand", "TestCo",
                "--migration-date", "Jan 2027",
                "--helpdesk", "x5000",
            ])
        assert result.exit_code != 0
