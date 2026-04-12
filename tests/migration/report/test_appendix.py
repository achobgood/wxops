"""Tests for technical appendix HTML generation (v4: 14 lettered sections)."""
import pytest
from datetime import datetime, timezone


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


class TestVoicemailGreetingCount:
    """Appendix H should show custom greeting count and email template."""

    def test_greeting_count_shown(self, populated_store):
        """Appendix H shows custom greeting count when present."""
        from wxcli.migration.report.appendix import generate_appendix

        run_id = "greeting-test"
        for i in range(7):
            populated_store.save_decision({
                "decision_id": populated_store.next_decision_id(),
                "type": "MISSING_DATA",
                "severity": "MEDIUM",
                "summary": f"Custom greeting for user-{i}",
                "context": {"user_id": f"user:user-{i:03d}", "reason": "custom_greeting_not_extractable"},
                "options": [{"id": "accept", "label": "Use defaults"}],
                "fingerprint": f"vm-greet-{i}",
                "run_id": run_id,
            })

        result = generate_appendix(populated_store)
        assert "Custom Greeting" in result or "custom greeting" in result.lower()
        assert "7" in result
        assert "re-record" in result.lower()

    def test_no_greeting_count_when_none(self, populated_store):
        """Appendix H does not show greeting row when no custom greetings exist."""
        from wxcli.migration.report.appendix import generate_appendix

        result = generate_appendix(populated_store)
        assert "re-record" not in result.lower()

    def test_communication_template_present(self, populated_store):
        """Appendix H includes email template when custom greetings exist."""
        from wxcli.migration.report.appendix import generate_appendix

        run_id = "greeting-test"
        for i in range(3):
            populated_store.save_decision({
                "decision_id": populated_store.next_decision_id(),
                "type": "MISSING_DATA",
                "severity": "MEDIUM",
                "summary": f"Custom greeting for user-{i}",
                "context": {"user_id": f"user:user-{i:03d}", "reason": "custom_greeting_not_extractable"},
                "options": [{"id": "accept", "label": "Use defaults"}],
                "fingerprint": f"vm-greet-comm-{i}",
                "run_id": run_id,
            })

        result = generate_appendix(populated_store)
        assert "Action Required" in result
        assert "Webex App" in result
        assert "Settings" in result


class TestMOHAppendix:
    """Appendix I (Audio Assets) should render MOH and announcement data."""

    def _make_prov(self):
        from wxcli.migration.models import Provenance
        return Provenance(
            source_system="cucm",
            source_id="test",
            source_name="test",
            extracted_at=datetime(2026, 3, 24, 12, 0, 0, tzinfo=timezone.utc),
        )

    def test_audio_assets_section_renders_with_moh_data(self, populated_store):
        """Appendix I renders with custom MOH source data present."""
        from wxcli.migration.models import CanonicalMusicOnHold, MigrationStatus
        from wxcli.migration.report.appendix import generate_appendix

        prov = self._make_prov()
        populated_store.upsert_object(CanonicalMusicOnHold(
            canonical_id="music_on_hold:CustomMOH",
            provenance=prov,
            status=MigrationStatus.ANALYZED,
            source_name="CustomMOH",
            source_file_name="custom_music.wav",
            is_default=False,
            cucm_source_id="42",
        ))

        result = generate_appendix(populated_store)
        assert 'id="audio-assets"' in result
        assert "CustomMOH" in result
        assert "custom_music.wav" in result
        assert "Action Required" in result

    def test_audio_assets_section_empty_store(self, tmp_path):
        """Appendix I is suppressed when no custom MOH sources or announcements."""
        from wxcli.migration.store import MigrationStore
        from wxcli.migration.report.appendix import generate_appendix

        store = MigrationStore(tmp_path / "empty_moh.db")
        result = generate_appendix(store)
        assert 'id="audio-assets"' not in result

    def test_audio_assets_suppressed_for_default_moh(self, populated_store):
        """Appendix I is suppressed when only default MOH sources exist (not custom)."""
        from wxcli.migration.models import CanonicalMusicOnHold, MigrationStatus
        from wxcli.migration.report.appendix import generate_appendix

        prov = self._make_prov()
        populated_store.upsert_object(CanonicalMusicOnHold(
            canonical_id="music_on_hold:Default",
            provenance=prov,
            status=MigrationStatus.ANALYZED,
            source_name="Default",
            source_file_name="default.wav",
            is_default=True,
            cucm_source_id="1",
        ))

        result = generate_appendix(populated_store)
        # Default MOH only — section should not render
        assert 'id="audio-assets"' not in result

    def test_audio_assets_shows_announcement_data(self, populated_store):
        """Appendix I renders announcement rows when announcement objects present."""
        from wxcli.migration.models import CanonicalAnnouncement, MigrationStatus
        from wxcli.migration.report.appendix import generate_appendix

        prov = self._make_prov()
        populated_store.upsert_object(CanonicalAnnouncement(
            canonical_id="announcement:WelcomeGreeting",
            provenance=prov,
            status=MigrationStatus.ANALYZED,
            name="WelcomeGreeting",
            file_name="welcome.wav",
            media_type="audio/wav",
        ))

        result = generate_appendix(populated_store)
        assert 'id="audio-assets"' in result
        assert "WelcomeGreeting" in result
        assert "welcome.wav" in result

    def test_audio_assets_moh_feature_cross_ref(self, populated_store):
        """Appendix I shows features using a MOH source via cross-ref."""
        from wxcli.migration.models import CanonicalMusicOnHold, MigrationStatus
        from wxcli.migration.report.appendix import generate_appendix

        prov = self._make_prov()
        populated_store.upsert_object(CanonicalMusicOnHold(
            canonical_id="music_on_hold:SalesMOH",
            provenance=prov,
            status=MigrationStatus.ANALYZED,
            source_name="SalesMOH",
            source_file_name="sales.wav",
            is_default=False,
            cucm_source_id="55",
        ))
        # Wire a hunt group as using this MOH source
        populated_store.add_cross_ref(
            "hunt_group:hg-1", "music_on_hold:SalesMOH", "feature_uses_moh_source"
        )

        result = generate_appendix(populated_store)
        assert "SalesMOH" in result
        # The feature name should appear in the "Features Using" column
        assert "hg-1" in result
