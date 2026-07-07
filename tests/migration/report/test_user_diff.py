"""Tests for per-user CUCM-vs-Webex migration diff."""
from __future__ import annotations

from wxcli.migration.report.user_diff import (
    ForwardingDiff,
    ForwardingRuleDiff,
    UserDecisionSummary,
    UserDiffRecord,
    build_user_diffs,
    render_csv,
    render_html,
)


def test_user_diff_record_defaults():
    """UserDiffRecord can be constructed with minimal fields."""
    record = UserDiffRecord(
        canonical_id="user:jsmith",
        display_name="Jane Smith",
    )
    assert record.canonical_id == "user:jsmith"
    assert record.display_name == "Jane Smith"
    assert record.email is None
    assert record.extension is None
    assert record.decisions == []
    assert record.has_changes is False
    assert record.change_categories == []


def test_forwarding_rule_diff():
    """ForwardingRuleDiff captures a single rule comparison."""
    rule = ForwardingRuleDiff(
        rule_type="busy",
        cucm_enabled=True,
        cucm_destination="1099",
        webex_enabled=True,
        webex_destination="Voicemail",
        status="mapped",
    )
    assert rule.status == "mapped"


def test_user_decision_summary():
    """UserDecisionSummary captures compact decision info."""
    dec = UserDecisionSummary(
        decision_id="D0012",
        type="FORWARDING_LOSSY",
        severity="MEDIUM",
        summary="Busy internal forwarding not mapped",
        resolution="auto-resolved: accept_lossy",
    )
    assert dec.decision_id == "D0012"
    assert dec.resolution == "auto-resolved: accept_lossy"


class TestBuildUserDiffs:
    """Tests for the core data join logic."""

    def test_basic_join_returns_all_users(self, populated_store):
        records = build_user_diffs(populated_store)
        assert len(records) == 50

    def test_user_identity_fields(self, populated_store):
        records = build_user_diffs(populated_store)
        by_id = {r.canonical_id: r for r in records}
        r = by_id["user:user-001"]
        assert r.display_name == "User 001"
        assert r.email == "user1@example.com"
        assert r.extension == "1001"

    def test_device_join(self, populated_store):
        records = build_user_diffs(populated_store)
        by_id = {r.canonical_id: r for r in records}
        r = by_id["user:user-001"]
        assert r.cucm_device_model == "CP-8845"
        assert r.device_tier == "native_mpp"

    def test_user_without_device(self, populated_store):
        records = build_user_diffs(populated_store)
        by_id = {r.canonical_id: r for r in records}
        r = by_id["user:user-050"]
        assert r.cucm_device_model is None
        assert r.device_tier is None

    def test_forwarding_join(self, populated_store):
        records = build_user_diffs(populated_store)
        by_id = {r.canonical_id: r for r in records}
        r = by_id["user:user-001"]
        assert r.forwarding is not None
        assert len(r.forwarding.rules) > 0
        rule_types = {rule.rule_type: rule for rule in r.forwarding.rules}
        assert "busy_internal" in rule_types
        assert rule_types["busy_internal"].status == "not_mapped"

    def test_forwarding_mapped_rules(self, populated_store):
        records = build_user_diffs(populated_store)
        by_id = {r.canonical_id: r for r in records}
        r = by_id["user:user-001"]
        rule_types = {rule.rule_type: rule for rule in r.forwarding.rules}
        assert rule_types["busy"].status == "mapped"
        assert rule_types["no_answer"].status == "mapped"

    def test_voicemail_join(self, populated_store):
        records = build_user_diffs(populated_store)
        by_id = {r.canonical_id: r for r in records}
        r = by_id["user:user-001"]
        assert r.cucm_voicemail is not None
        assert "Enabled" in r.cucm_voicemail
        assert r.webex_voicemail is not None

    def test_monitoring_join(self, populated_store):
        records = build_user_diffs(populated_store)
        by_id = {r.canonical_id: r for r in records}
        r = by_id["user:user-001"]
        assert r.blf_count_cucm == 3
        assert r.blf_mapped == 2
        assert r.blf_unmapped == 1

    def test_shared_line_join(self, populated_store):
        records = build_user_diffs(populated_store)
        by_id = {r.canonical_id: r for r in records}
        r = by_id["user:user-001"]
        assert len(r.shared_line_dns) > 0

    def test_device_layout_join(self, populated_store):
        records = build_user_diffs(populated_store)
        by_id = {r.canonical_id: r for r in records}
        r = by_id["user:user-001"]
        assert r.total_buttons_cucm > 0
        assert r.speed_dial_count_cucm == 2
        assert len(r.unmapped_buttons) == 1

    def test_calling_permission_join(self, populated_store):
        records = build_user_diffs(populated_store)
        by_id = {r.canonical_id: r for r in records}
        r = by_id["user:user-001"]
        assert r.cucm_css is not None
        assert r.webex_permissions is not None

    def test_decision_association(self, populated_store):
        records = build_user_diffs(populated_store)
        by_id = {r.canonical_id: r for r in records}
        r = by_id["user:user-001"]
        assert len(r.decisions) >= 1
        dec_types = [d.type for d in r.decisions]
        assert "FORWARDING_LOSSY" in dec_types

    def test_single_user_filter(self, populated_store):
        records = build_user_diffs(populated_store, user_filter="user:user-001")
        assert len(records) == 1
        assert records[0].canonical_id == "user:user-001"

    def test_location_filter(self, populated_store):
        records = build_user_diffs(
            populated_store, location_filter="loc:dallas-hq",
        )
        assert len(records) == 25
        assert all(r.webex_location == "Dallas HQ" for r in records)

    def test_has_changes_flag(self, populated_store):
        records = build_user_diffs(populated_store)
        by_id = {r.canonical_id: r for r in records}
        r = by_id["user:user-001"]
        assert r.has_changes is True
        assert len(r.change_categories) > 0

    def test_no_change_filtering(self, populated_store):
        all_records = build_user_diffs(populated_store)
        changed = [r for r in all_records if r.has_changes or r.decisions]
        unchanged = [r for r in all_records if not r.has_changes and not r.decisions]
        assert len(changed) > 0
        assert len(unchanged) > 0
        assert len(changed) + len(unchanged) == 50

    def test_sorted_by_display_name(self, populated_store):
        records = build_user_diffs(populated_store)
        names = [r.display_name for r in records]
        assert names == sorted(names, key=str.lower)

    def test_empty_store(self, tmp_path):
        from wxcli.migration.store import MigrationStore
        store = MigrationStore(tmp_path / "empty.db")
        records = build_user_diffs(store)
        assert records == []
        store.close()


class TestRenderCsv:
    """Tests for CSV output rendering."""

    def test_csv_header_row(self, populated_store):
        records = build_user_diffs(populated_store, user_filter="user:user-001")
        output = render_csv(records)
        lines = output.strip().split("\n")
        header = lines[0]
        assert "User" in header
        assert "Email" in header
        assert "Extension" in header
        assert "Category" in header
        assert "CUCM_Value" in header
        assert "Webex_Value" in header
        assert "Status" in header

    def test_csv_has_data_rows(self, populated_store):
        records = build_user_diffs(populated_store, user_filter="user:user-001")
        output = render_csv(records)
        lines = output.strip().split("\n")
        assert len(lines) >= 4

    def test_csv_utf8_bom(self, populated_store):
        records = build_user_diffs(populated_store, user_filter="user:user-001")
        output = render_csv(records)
        assert output.startswith("\ufeff")

    def test_csv_empty_records(self):
        output = render_csv([])
        lines = output.strip().split("\n")
        assert len(lines) == 1

    def test_csv_forwarding_rules_expanded(self, populated_store):
        records = build_user_diffs(populated_store, user_filter="user:user-001")
        output = render_csv(records)
        assert "Fwd Busy" in output
        assert "Fwd No Answer" in output
        assert "NOT MAPPED" in output


class TestRenderHtml:
    """Tests for HTML output rendering."""

    def test_html_is_complete_document(self, populated_store):
        records = build_user_diffs(populated_store)
        output = render_html(records, brand="Test Corp")
        assert output.startswith("<!DOCTYPE html>")
        assert "</html>" in output
        assert "<style>" in output
        assert "Test Corp" in output

    def test_html_has_details_per_user(self, populated_store):
        records = build_user_diffs(populated_store)
        output = render_html(records, brand="Test Corp")
        assert output.count("<details") == 50

    def test_html_has_diff_table(self, populated_store):
        records = build_user_diffs(
            populated_store, user_filter="user:user-001",
        )
        output = render_html(records, brand="Test Corp")
        assert "CUCM (Current)" in output
        assert "Webex (Planned)" in output
        assert "<table" in output

    def test_html_summary_bar(self, populated_store):
        records = build_user_diffs(populated_store)
        output = render_html(records, brand="Test Corp")
        assert "summary-bar" in output
        assert "50" in output

    def test_html_search_input(self, populated_store):
        records = build_user_diffs(populated_store)
        output = render_html(records, brand="Test Corp")
        assert 'id="search"' in output
        assert "filter-category" in output

    def test_html_not_mapped_highlighted(self, populated_store):
        records = build_user_diffs(
            populated_store, user_filter="user:user-001",
        )
        output = render_html(records, brand="Test Corp")
        assert "not-mapped" in output

    def test_html_decisions_section(self, populated_store):
        records = build_user_diffs(populated_store)
        output = render_html(records, brand="Test Corp")
        assert "decisions-section" in output or "decision" in output.lower()

    def test_html_expand_collapse_button(self, populated_store):
        records = build_user_diffs(populated_store)
        output = render_html(records, brand="Test Corp")
        assert "expand-all" in output or "Expand All" in output

    def test_html_no_script_dependency(self, populated_store):
        records = build_user_diffs(
            populated_store, user_filter="user:user-001",
        )
        output = render_html(records, brand="Test Corp")
        assert "<details" in output
        assert "<summary" in output

    def test_html_empty_records(self):
        output = render_html([], brand="Test Corp")
        assert "<!DOCTYPE html>" in output
        assert "No users" in output or "0 users" in output


# ---------------------------------------------------------------------------
# CLI Integration Tests
# ---------------------------------------------------------------------------

from unittest.mock import patch

from typer.testing import CliRunner

from wxcli.commands.cucm import app as cucm_app


class TestCliIntegration:
    """Tests for the wxcli cucm user-diff CLI command."""

    def test_user_diff_html_default(self, populated_store, tmp_path):
        """user-diff generates HTML by default."""
        runner = CliRunner()
        with patch("wxcli.commands.cucm._resolve_project_dir", return_value=tmp_path), \
             patch("wxcli.commands.cucm._completed_stages", return_value={"init", "discover", "normalize", "map", "analyze"}), \
             patch("wxcli.commands.cucm._open_store", return_value=populated_store), \
             patch("wxcli.commands.cucm.load_config", return_value={"cluster_name": "Test"}):
            result = runner.invoke(cucm_app, ["user-diff"])

        assert result.exit_code == 0, result.output
        html_path = tmp_path / "user-diff.html"
        assert html_path.exists()
        content = html_path.read_text()
        assert "<!DOCTYPE html>" in content

    def test_user_diff_csv(self, populated_store, tmp_path):
        """user-diff --format csv generates CSV."""
        runner = CliRunner()
        with patch("wxcli.commands.cucm._resolve_project_dir", return_value=tmp_path), \
             patch("wxcli.commands.cucm._completed_stages", return_value={"init", "discover", "normalize", "map", "analyze"}), \
             patch("wxcli.commands.cucm._open_store", return_value=populated_store):
            result = runner.invoke(cucm_app, ["user-diff", "--format", "csv"])

        assert result.exit_code == 0, result.output
        csv_path = tmp_path / "user-diff.csv"
        assert csv_path.exists()

    def test_user_diff_single_user(self, populated_store, tmp_path):
        """user-diff --user filters to one user."""
        runner = CliRunner()
        with patch("wxcli.commands.cucm._resolve_project_dir", return_value=tmp_path), \
             patch("wxcli.commands.cucm._completed_stages", return_value={"init", "discover", "normalize", "map", "analyze"}), \
             patch("wxcli.commands.cucm._open_store", return_value=populated_store), \
             patch("wxcli.commands.cucm.load_config", return_value={"cluster_name": "Test"}):
            result = runner.invoke(
                cucm_app, ["user-diff", "--user", "user:user-001"],
            )

        assert result.exit_code == 0, result.output
        html_path = tmp_path / "user-diff.html"
        content = html_path.read_text()
        assert content.count("<details") == 1

    def test_user_diff_requires_analyze(self, tmp_path):
        """user-diff fails if analyze stage not complete."""
        runner = CliRunner()
        with patch("wxcli.commands.cucm._resolve_project_dir", return_value=tmp_path), \
             patch("wxcli.commands.cucm._completed_stages", return_value={"init", "discover"}):
            result = runner.invoke(cucm_app, ["user-diff"])

        assert result.exit_code == 1
        assert "analyze" in result.output.lower()
