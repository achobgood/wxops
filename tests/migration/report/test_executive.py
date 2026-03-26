"""Tests for executive summary HTML generation (v4: 4-page narrative)."""
import pytest


class TestExecutiveSummary:
    def test_returns_html_string(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "<section" in html
        assert "</section>" in html

    def test_contains_all_four_section_ids(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        for section_id in ["score", "inventory", "decisions", "next-steps"]:
            assert f'id="{section_id}"' in html, f"Missing section #{section_id}"

    def test_page1_verdict(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "Migration Complexity Assessment" in html
        assert "<svg" in html  # gauge chart
        assert "Straightforward" in html or "Moderate" in html

    def test_page1_score_breakdown_with_scale(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "score-breakdown" in html
        assert "Complexity Impact" in html
        assert "Low" in html
        assert "High" in html

    def test_page1_key_findings(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "key-findings" in html

    def test_page2_environment_groups(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "People" in html
        assert "Devices" in html
        assert "Call Features" in html
        assert "Sites" in html

    def test_page2_contains_counts(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "50" in html  # user count
        assert "45" in html  # device count

    def test_page2_phone_compatibility(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "Native MPP" in html
        assert "Convertible" in html
        assert "Incompatible" in html

    def test_page3_effort_bands(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "Migrates Automatically" in html
        assert "Needs Planning" in html or "Planning" in html

    def test_page3_feature_table(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "Hunt Group" in html
        assert "Auto Attendant" in html
        assert "Direct" in html or "badge-direct" in html

    def test_page4_next_steps(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "Before Migration" in html or "next-steps" in html

    def test_no_canonical_id_prefixes(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "CSS_ROUTING_MISMATCH" not in html

    def test_contains_prepared_by(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "Test SE" in html  # in the CTA box

    def test_site_breakdown_present(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "Dallas" in html

    def test_analog_gateway_callout(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "analog gateway" in html.lower()
        assert "Technical Appendix" in html

    def test_page1_has_direct_heading(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "Migration Complexity Assessment" in html
        assert "section-kicker" not in html
