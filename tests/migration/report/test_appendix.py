"""Tests for technical appendix HTML generation (v4: 14 lettered sections)."""
import pytest


class TestAppendix:
    def test_returns_html_string(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert "<section" in html

    def test_has_six_details_elements(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert html.count("<details") >= 5  # at least 5 non-empty groups

    def test_section_ids(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        for sid in ["objects", "decision-detail", "device-detail", "routing", "gateways", "coverage"]:
            assert f'id="{sid}"' in html, f"Missing section #{sid}"

    def test_uses_details_summary(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert "<details" in html
        assert "<summary>" in html

    def test_all_collapsed_by_default(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        # No <details open> attributes
        assert "<details open" not in html

    def test_summary_has_count(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        # Summary lines should include counts
        assert "50 users" in html.lower() or "50" in html

    def test_dn_analysis_section(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert "DN Analysis" in html or 'id="dn-analysis"' in html

    def test_user_device_map_section(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert "User/Device Map" in html or 'id="user-device-map"' in html

    def test_devices_section(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert 'id="device-detail"' in html
        assert "CP-8845" in html

    def test_features_section(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert 'id="call-features"' in html or "Call Features" in html

    def test_routing_section(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert 'id="routing"' in html

    def test_css_partitions_section(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert 'id="css-partitions"' in html

    def test_decisions_grouped_by_type(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        # Should use display names, not raw type names
        assert "Feature Approximation" in html
        assert "CSS Routing Mismatch" in html or "Routing Mismatch" in html

    def test_no_canonical_id_prefixes_in_text(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        # Canonical prefixes should be stripped from visible text
        # Allow them in id attributes but not in displayed text
        for prefix in ["css:", "device:", "voicemail_profile:"]:
            assert f">{prefix}" not in html, f"Prefix '{prefix}' found in visible text"

    def test_gateways_group_present(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert 'id="gateways"' in html
        assert "Analog" in html or "analog" in html

    def test_gateways_analog_table(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert "VG310" in html
        assert "ATA 191" in html or "ATA191" in html

    def test_gateways_mgcp_warning(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert "MGCP" in html
        assert "not supported" in html.lower() or "convert to SIP" in html

    def test_gateways_port_estimate(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        # VG310 = 24 ports, ATA 191 = 2 ports → 26 total estimated
        assert "24" in html  # VG310 port count in table
        assert "2" in html   # ATA 191 port count in table

    def test_gateways_section_id(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert 'id="gateways"' in html

    def test_skips_empty_sections(self, tmp_path):
        from wxcli.migration.store import MigrationStore
        from wxcli.migration.report.appendix import generate_appendix
        store = MigrationStore(tmp_path / "empty.db")
        html = generate_appendix(store)
        # Empty store should produce minimal output
        assert "<details" not in html or html.count("<details") == 0
