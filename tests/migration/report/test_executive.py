"""Tests for executive summary HTML generation (v4: 4-page narrative)."""
import pytest
from datetime import datetime, timezone


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

    def test_dect_in_device_summary(self, populated_store):
        """DECT appears as a distinct segment in executive summary."""
        from wxcli.migration.report.executive import generate_executive_summary

        html = generate_executive_summary(populated_store, brand="Acme Corp", prepared_by="Test SE")
        assert "DECT" in html


class TestVoicemailGreetingCallout:
    """Executive Page 4 should show greeting re-recording callout."""

    def test_greeting_callout_present(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary

        run_id = "exec-greeting-test"
        for i in range(12):
            populated_store.save_decision({
                "decision_id": populated_store.next_decision_id(),
                "type": "MISSING_DATA",
                "severity": "MEDIUM",
                "summary": f"Custom greeting for user-{i}",
                "context": {"user_id": f"user:user-{i:03d}", "reason": "custom_greeting_not_extractable"},
                "options": [{"id": "accept", "label": "Use defaults"}],
                "fingerprint": f"exec-greet-{i}",
                "run_id": run_id,
            })

        result = generate_executive_summary(populated_store, "TestCo", "SE Name")
        assert "re-record" in result.lower()
        assert "12" in result
        assert "voicemail" in result.lower()

    def test_no_greeting_callout_when_none(self, populated_store):
        from wxcli.migration.report.executive import generate_executive_summary

        result = generate_executive_summary(populated_store, "TestCo", "SE Name")
        assert "re-record" not in result.lower()


class TestMOHExecutiveSummary:
    """Executive Page 2 should show Custom MoH stat cards when data present."""

    def _make_prov(self):
        from wxcli.migration.models import Provenance
        return Provenance(
            source_system="cucm",
            source_id="test",
            source_name="test",
            extracted_at=datetime(2026, 3, 24, 12, 0, 0, tzinfo=timezone.utc),
        )

    def test_moh_stat_card_renders(self, populated_store):
        """Custom MoH Sources stat card appears when custom MOH sources are present."""
        from wxcli.migration.models import CanonicalMusicOnHold, MigrationStatus
        from wxcli.migration.report.executive import generate_executive_summary

        prov = self._make_prov()
        for i in range(3):
            populated_store.upsert_object(CanonicalMusicOnHold(
                canonical_id=f"music_on_hold:CustomMOH{i}",
                provenance=prov,
                status=MigrationStatus.ANALYZED,
                source_name=f"CustomMOH{i}",
                source_file_name=f"music{i}.wav",
                is_default=False,
                cucm_source_id=str(10 + i),
            ))

        result = generate_executive_summary(populated_store, "Acme Corp", "Test SE")
        assert "Custom MoH" in result or "Custom MoH Sources" in result
        assert "3" in result

    def test_moh_stat_card_absent_when_no_custom_moh(self, populated_store):
        """Custom MoH Sources stat card is absent when no custom MOH sources exist."""
        from wxcli.migration.report.executive import generate_executive_summary

        result = generate_executive_summary(populated_store, "Acme Corp", "Test SE")
        assert "Custom MoH Sources" not in result

    def test_moh_callout_points_to_appendix(self, populated_store):
        """Audio assets callout links to appendix when custom MOH or announcements present."""
        from wxcli.migration.models import CanonicalMusicOnHold, MigrationStatus
        from wxcli.migration.report.executive import generate_executive_summary

        prov = self._make_prov()
        populated_store.upsert_object(CanonicalMusicOnHold(
            canonical_id="music_on_hold:AnnualMOH",
            provenance=prov,
            status=MigrationStatus.ANALYZED,
            source_name="AnnualMOH",
            source_file_name="annual.wav",
            is_default=False,
            cucm_source_id="99",
        ))

        result = generate_executive_summary(populated_store, "Acme Corp", "Test SE")
        # Callout should point to the appendix audio assets section
        assert "Audio Assets" in result or "audio" in result.lower()
        assert "callout" in result or "warning" in result

    def test_announcement_stat_card_renders(self, populated_store):
        """Announcement Files stat card appears when announcements present."""
        from wxcli.migration.models import CanonicalAnnouncement, MigrationStatus
        from wxcli.migration.report.executive import generate_executive_summary

        prov = self._make_prov()
        for i in range(2):
            populated_store.upsert_object(CanonicalAnnouncement(
                canonical_id=f"announcement:Greeting{i}",
                provenance=prov,
                status=MigrationStatus.ANALYZED,
                name=f"Greeting{i}",
                file_name=f"greeting{i}.wav",
                media_type="audio/wav",
            ))

        result = generate_executive_summary(populated_store, "Acme Corp", "Test SE")
        assert "Announcement" in result
        assert "2" in result
