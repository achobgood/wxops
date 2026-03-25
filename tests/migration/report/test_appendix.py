"""Tests for technical appendix HTML generation."""
import pytest


class TestAppendix:
    def test_returns_html_string(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert "<section" in html

    def test_contains_object_inventory(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert "Object Inventory" in html
        assert "<table" in html

    def test_contains_decision_detail(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert "Decision Detail" in html
        assert "FEATURE_APPROXIMATION" in html or "Feature Approximation" in html

    def test_contains_device_inventory(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert "Device Inventory" in html
        assert "CP-8845" in html

    def test_uses_details_summary_elements(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert "<details" in html
        assert "<summary>" in html

    def test_skips_empty_sections(self, tmp_path):
        """Appendix for empty store should have minimal content."""
        from wxcli.migration.store import MigrationStore
        from wxcli.migration.report.appendix import generate_appendix
        store = MigrationStore(tmp_path / "empty.db")
        html = generate_appendix(store)
        # Should not have device inventory if no devices
        assert "Device Inventory" not in html or "No devices" in html

    def test_css_partition_analysis(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert "CSS" in html and "Partition" in html

    def test_routing_topology(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert "Routing" in html
        assert "PSTN Trunk" in html or "trunk" in html.lower()
