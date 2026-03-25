"""Tests for full report assembly (v2)."""
import pytest


class TestAssembler:
    def test_assemble_returns_complete_html(self, populated_store):
        from wxcli.migration.report.assembler import assemble_report
        html = assemble_report(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html
        assert "<style>" in html  # embedded CSS
        assert "Acme Corp" in html

    def test_html_is_self_contained(self, populated_store):
        from wxcli.migration.report.assembler import assemble_report
        html = assemble_report(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert '<script src="' not in html  # no external JS
        assert '<link rel="stylesheet" href="http' not in html

    def test_contains_executive_and_appendix(self, populated_store):
        from wxcli.migration.report.assembler import assemble_report
        html = assemble_report(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert 'id="score"' in html  # executive section present
        assert 'id="people"' in html or 'id="devices"' in html  # appendix

    def test_executive_only_flag(self, populated_store):
        from wxcli.migration.report.assembler import assemble_report
        html = assemble_report(populated_store,
            brand="Acme Corp", prepared_by="Test SE",
            executive_only=True)
        assert "TECHNICAL REFERENCE" not in html  # no interstitial
        assert "Acme Corp" in html

    def test_print_styles_present(self, populated_store):
        from wxcli.migration.report.assembler import assemble_report
        html = assemble_report(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "@media print" in html
        assert "@page" in html

    def test_write_report_to_file(self, populated_store, tmp_path):
        from wxcli.migration.report.assembler import assemble_report
        html = assemble_report(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        out_path = tmp_path / "report.html"
        out_path.write_text(html)
        assert out_path.exists()
        assert out_path.stat().st_size > 1000

    def test_dark_interstitial_present(self, populated_store):
        from wxcli.migration.report.assembler import assemble_report
        html = assemble_report(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "TECHNICAL REFERENCE" in html
        assert "tech-interstitial" in html

    def test_sidebar_nav_exec_items(self, populated_store):
        from wxcli.migration.report.assembler import assemble_report
        html = assemble_report(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "The Verdict" in html
        assert "Your Environment" in html
        assert "Migration Scope" in html
        assert "Next Steps" in html

    def test_sidebar_nav_tech_items(self, populated_store):
        from wxcli.migration.report.assembler import assemble_report
        html = assemble_report(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert 'href="#people"' in html
        assert 'href="#devices"' in html
        assert 'href="#routing"' in html

    def test_summary_bar_present(self, populated_store):
        from wxcli.migration.report.assembler import assemble_report
        html = assemble_report(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "summary-bar" in html
        assert "Score" in html
        assert "Users" in html
        assert "Devices" in html
        assert "Sites" in html

    def test_max_width_wrapper(self, populated_store):
        from wxcli.migration.report.assembler import assemble_report
        html = assemble_report(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "detail-panel-content" in html
