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

    def test_contains_dn_analysis(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert "DN Analysis" in html
        # Verify classification breakdown rows are present
        assert "EXTENSION" in html
        assert "E164" in html

    def test_contains_voicemail_section(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert "Voicemail Analysis" in html
        # Voicemail profile table should be present
        assert "Voicemail Profiles" in html
        # VOICEMAIL_INCOMPATIBLE decision should appear
        assert "Voicemail Incompatibilities" in html

    def test_contains_user_device_line_map(self, populated_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert "User" in html and "Device" in html and "Line" in html
        # Verify the cross-ref chain renders user names and DN patterns
        assert "User 001" in html
        assert "CP-8845" in html
        # Verify partition names appear via dn_in_partition cross-refs
        assert "PT-Internal" in html

    def test_call_forwarding_section(self, populated_store):
        """Call forwarding section appears when call_forwarding objects exist."""
        from wxcli.migration.report.appendix import generate_appendix
        from wxcli.migration.models import CanonicalCallForwarding, Provenance
        from datetime import datetime, timezone
        cf = CanonicalCallForwarding(
            canonical_id="call_forwarding:user1",
            provenance=Provenance(
                source_system="cucm", source_id="pk-1", source_name="test",
                extracted_at=datetime.now(timezone.utc),
            ),
            user_canonical_id="user:user1",
            always_enabled=True,
            always_destination="+15551234567",
        )
        populated_store.upsert_object(cf)
        html = generate_appendix(populated_store)
        assert "Call Forwarding" in html
        assert "CFA" in html

    def test_monitoring_section(self, populated_store):
        """Monitoring section appears when monitoring_list objects exist."""
        from wxcli.migration.report.appendix import generate_appendix
        from wxcli.migration.models import CanonicalMonitoringList, Provenance
        from datetime import datetime, timezone
        ml = CanonicalMonitoringList(
            canonical_id="monitoring_list:user1",
            provenance=Provenance(
                source_system="cucm", source_id="pk-2", source_name="test",
                extracted_at=datetime.now(timezone.utc),
            ),
            user_canonical_id="user:user1",
            monitored_members=[{"target_canonical_id": "user:user2", "display_label": "Bob"}],
        )
        populated_store.upsert_object(ml)
        html = generate_appendix(populated_store)
        assert "Monitoring" in html
        assert "monitored members" in html.lower() or "Monitored" in html

    def test_routing_trunk_table_has_security_columns(self, populated_store):
        """Routing topology trunk table includes Security and Early Offer columns."""
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(populated_store)
        assert "Security" in html
        assert "Early Offer" in html
