"""Tests for Tier 3 informational appendix sections O-R."""
from datetime import datetime, timezone

import pytest

from wxcli.migration.models import MigrationObject, MigrationStatus, Provenance
from wxcli.migration.store import MigrationStore


def _prov(name: str) -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id=name,
        source_name=name,
        extracted_at=datetime(2026, 3, 27, 12, 0, 0, tzinfo=timezone.utc),
    )


def _info_obj(suffix: str, name: str, category: str, **extra) -> MigrationObject:
    """Create an informational MigrationObject."""
    state = {"name": name, "_category": category, "_info_type": suffix, **extra}
    return MigrationObject(
        canonical_id=f"info_{suffix}:{name}",
        provenance=_prov(name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=state,
    )


@pytest.fixture()
def tier3_store(tmp_path):
    """Store populated with informational objects across all 4 categories."""
    store = MigrationStore(tmp_path / "migration.db")

    # Cloud-managed (category O)
    store.upsert_object(_info_obj("region", "Default", "cloud_managed", defaultCodec="G.711"))
    store.upsert_object(_info_obj("region", "LowBW", "cloud_managed", defaultCodec="G.729"))
    store.upsert_object(_info_obj("srst", "SRST-HQ", "cloud_managed", ipAddress="10.1.1.1"))
    store.upsert_object(_info_obj("media_resource_group", "MRG-1", "cloud_managed"))
    store.upsert_object(_info_obj("conference_bridge", "CFB-1", "cloud_managed", product="Cisco IOS"))

    # Not migratable (category P)
    store.upsert_object(_info_obj("ip_phone_service", "Corp Directory", "not_migratable", url="http://dir.local"))
    store.upsert_object(_info_obj("ip_phone_service", "Weather Service", "not_migratable", url="http://weather.local"))
    store.upsert_object(_info_obj("softkey_template", "Standard", "not_migratable"))
    intercom = MigrationObject(
        canonical_id="info_intercom:9001",
        provenance=_prov("9001"),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"dnorpattern": "9001", "_category": "not_migratable", "_info_type": "intercom"},
    )
    store.upsert_object(intercom)

    # Different architecture (category Q)
    store.upsert_object(_info_obj("common_phone_config", "Standard CPP", "different_arch"))
    store.upsert_object(_info_obj("recording_profile", "Default Recording", "different_arch", recorderDestination="recorder.local"))
    store.upsert_object(_info_obj("ldap_directory", "Corp AD", "different_arch", ldapDn="dc=corp,dc=local"))

    # Planning input (category R)
    app_user = MigrationObject(
        canonical_id="info_app_user:JTAPI_USER",
        provenance=_prov("JTAPI_USER"),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "userid": "JTAPI_USER", "description": "JTAPI for Finesse",
            "associatedDevices": "CTI-1", "_category": "planning", "_info_type": "app_user",
        },
    )
    store.upsert_object(app_user)
    store.upsert_object(_info_obj("h323_gateway", "GW-Analog", "planning", product="Cisco VG310"))

    return store


class TestSectionO_CloudManaged:
    def test_renders_cloud_managed_section(self, tier3_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(tier3_store)
        assert 'id="cloud-managed"' in html
        assert "O. Cloud-Managed" in html
        assert "Regions" in html
        assert "SRST" in html

    def test_shows_count_per_type(self, tier3_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(tier3_store)
        assert ">2<" in html

    def test_shows_cloud_managed_message(self, tier3_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(tier3_store)
        assert "Webex manages this automatically" in html


class TestSectionP_FeatureGaps:
    def test_renders_feature_gaps_section(self, tier3_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(tier3_store)
        assert 'id="feature-gaps"' in html
        assert "P. Feature Gaps" in html
        assert "IP Phone Services" in html

    def test_shows_workaround_for_intercom(self, tier3_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(tier3_store)
        assert "auto-answer" in html.lower() or "speed dial" in html.lower()


class TestSectionQ_ManualReconfig:
    def test_renders_manual_reconfig_section(self, tier3_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(tier3_store)
        assert 'id="manual-reconfig"' in html
        assert "Q. Manual Reconfiguration" in html
        assert "Common Phone Profiles" in html

    def test_shows_webex_equivalent(self, tier3_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(tier3_store)
        assert "Device configuration templates" in html


class TestSectionR_PlanningInputs:
    def test_renders_planning_section(self, tier3_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(tier3_store)
        assert 'id="planning-inputs"' in html
        assert "R. Planning Inputs" in html
        assert "JTAPI_USER" in html

    def test_flags_jtapi_app_user(self, tier3_store):
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(tier3_store)
        assert "JTAPI" in html


class TestSectionsEmpty:
    def test_empty_store_produces_no_tier3_sections(self, tmp_path):
        store = MigrationStore(tmp_path / "empty.db")
        from wxcli.migration.report.appendix import generate_appendix
        html = generate_appendix(store)
        assert "Cloud-Managed" not in html
        assert "Feature Gaps" not in html
        assert "Manual Reconfiguration" not in html
        assert "Planning Inputs" not in html
