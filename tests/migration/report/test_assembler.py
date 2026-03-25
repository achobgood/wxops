"""Tests for full report assembly."""
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
        # No external references
        assert 'href="http' not in html or 'fonts.googleapis' in html  # font CDN is OK
        assert '<script src="' not in html  # no external JS
        assert '<link rel="stylesheet" href="http' not in html

    def test_contains_executive_and_appendix(self, populated_store):
        from wxcli.migration.report.assembler import assemble_report
        html = assemble_report(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "Migration Complexity Score" in html or "Complexity" in html  # executive
        assert "Object Inventory" in html  # appendix

    def test_executive_only_flag(self, populated_store):
        from wxcli.migration.report.assembler import assemble_report
        html = assemble_report(populated_store,
            brand="Acme Corp", prepared_by="Test SE",
            executive_only=True)
        assert "Object Inventory" not in html  # no appendix
        assert "Acme Corp" in html  # executive still there

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
        assert out_path.stat().st_size > 1000  # not trivially small
