"""Tests for executive summary HTML generation."""
import pytest


class TestExecutiveSummary:
    def test_returns_html_string(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "<section" in html
        assert "</section>" in html

    def test_contains_complexity_score(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "<svg" in html  # gauge chart
        assert "Straightforward" in html or "Moderate" in html

    def test_contains_brand_name(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "Acme Corp" in html

    def test_contains_environment_snapshot(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "50" in html  # user count
        assert "45" in html  # device count

    def test_contains_phone_compatibility_chart(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "Native MPP" in html
        assert "Convertible" in html
        assert "Incompatible" in html

    def test_contains_site_breakdown(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "Dallas" in html or "loc_dallas" in html

    def test_contains_decision_summary(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "Auto-resolved" in html or "auto-resolved" in html
        assert "Decision" in html or "decision" in html

    def test_contains_feature_mapping_table(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        assert "Hunt Group" in html
        assert "Auto Attendant" in html

    def test_contains_plain_english_decisions(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary
        html = generate_executive_summary(populated_store,
            brand="Acme Corp", prepared_by="Test SE")
        # Should use explainer, not raw decision type names
        assert "CSS_ROUTING_MISMATCH" not in html
