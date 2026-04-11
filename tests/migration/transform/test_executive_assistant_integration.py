"""Integration tests: executive/assistant through the full transform pipeline.

Seeds a minimal store with users, phones, device pools, location data, and
executive/assistant objects (exec_asst_pair + exec_setting), then runs the full
TransformEngine and verifies that:
  1. The executive_assistant_mapper produces CanonicalExecutiveAssistant objects
  2. The assessment report appendix includes the Executive/Assistant section
"""

from datetime import datetime, timezone

import pytest

from wxcli.migration.models import (
    CanonicalUser,
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.cross_reference import CrossReferenceBuilder
from wxcli.migration.transform.engine import TransformEngine
from wxcli.migration.report.appendix import generate_appendix


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_EXTRACTED_AT = datetime(2026, 4, 10, 12, 0, 0, tzinfo=timezone.utc)


def _prov(name: str) -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id=f"pkid-{name}",
        source_name=name,
        cluster="CUCM-TEST",
        extracted_at=_EXTRACTED_AT,
        cucm_version="14.0",
    )


def _obj(canonical_id: str, name: str, pre_migration_state: dict | None = None) -> MigrationObject:
    return MigrationObject(
        canonical_id=canonical_id,
        provenance=_prov(name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=pre_migration_state or {},
    )


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def exec_store() -> MigrationStore:
    """Build a minimal store with executive/assistant data and location chain.

    Contains:
    - 1 CUCM location + 1 device pool + 1 datetime group
    - 2 users (jsmith = executive, jdoe = assistant)
    - 2 phones (one per user) for location resolution
    - 1 exec_asst_pair object (jsmith -> jdoe)
    - 2 exec_setting objects (jsmith=EXECUTIVE, jdoe=EXECUTIVE_ASSISTANT)

    All objects are inserted first, then cross-refs (FK constraints require
    both endpoints to exist).
    """
    store = MigrationStore(":memory:")

    # ==================================================================
    # PHASE 1: Insert ALL objects (FK constraints require both ends)
    # ==================================================================

    # Location infrastructure
    # (CrossReferenceBuilder reads cucm_location_name and cucm_datetime_group
    # from device_pool pre_migration_state to build refs)
    store.upsert_object(_obj(
        "cucm_location:HQ", "HQ",
        {"address1": "100 Main St", "city": "Dallas", "state": "TX",
         "postal_code": "75001", "country": "US"},
    ))
    store.upsert_object(_obj(
        "datetime_group:US-Central", "US-Central",
        {"datetime_group_name": "US-Central", "timezone": "America/Chicago"},
    ))
    store.upsert_object(_obj(
        "device_pool:DP-HQ", "DP-HQ",
        {"device_pool_name": "DP-HQ",
         "cucm_location_name": "HQ",
         "cucm_datetime_group": "US-Central"},
    ))

    # DNs
    store.upsert_object(_obj(
        "dn:1001:Internal-PT", "1001",
        {"pattern": "1001", "partition": "Internal-PT"},
    ))
    store.upsert_object(_obj(
        "dn:1002:Internal-PT", "1002",
        {"pattern": "1002", "partition": "Internal-PT"},
    ))

    # Phones (raw phone objects for location resolution and call settings)
    store.upsert_object(_obj(
        "phone:SEP111111111111", "SEP111111111111",
        {"name": "SEP111111111111", "model": "Cisco 6841", "protocol": "SIP",
         "is_common_area": False, "description": "Jsmith Desk Phone",
         "line_appearances": [
             {"dn_canonical_id": "dn:1001:Internal-PT", "position": 1},
         ]},
    ))
    store.upsert_object(_obj(
        "phone:SEP222222222222", "SEP222222222222",
        {"name": "SEP222222222222", "model": "Cisco 6841", "protocol": "SIP",
         "is_common_area": False, "description": "Jdoe Desk Phone",
         "line_appearances": [
             {"dn_canonical_id": "dn:1002:Internal-PT", "position": 1},
         ]},
    ))

    # Device objects (CrossReferenceBuilder reads cucm_device_pool + cucm_owner_user
    # from pre_migration_state to build device_in_pool + device_owned_by_user refs)
    store.upsert_object(_obj(
        "device:SEP111111111111", "SEP111111111111",
        {"name": "SEP111111111111", "model": "Cisco 6841",
         "cucm_device_pool": "DP-HQ", "cucm_owner_user": "jsmith"},
    ))
    store.upsert_object(_obj(
        "device:SEP222222222222", "SEP222222222222",
        {"name": "SEP222222222222", "model": "Cisco 6841",
         "cucm_device_pool": "DP-HQ", "cucm_owner_user": "jdoe"},
    ))

    # Users (CanonicalUser with email/cucm_userid + associated_devices for cross-ref builder)
    store.upsert_object(CanonicalUser(
        canonical_id="user:jsmith",
        provenance=_prov("jsmith"),
        status=MigrationStatus.NORMALIZED,
        cucm_userid="jsmith",
        cucm_mailid="jsmith@example.com",
        emails=["jsmith@example.com"],
        first_name="John",
        last_name="Smith",
        pre_migration_state={
            "userid": "jsmith", "mailid": "jsmith@example.com",
            "associated_devices": ["SEP111111111111"],
        },
    ))
    store.upsert_object(CanonicalUser(
        canonical_id="user:jdoe",
        provenance=_prov("jdoe"),
        status=MigrationStatus.NORMALIZED,
        cucm_userid="jdoe",
        cucm_mailid="jdoe@example.com",
        emails=["jdoe@example.com"],
        first_name="Jane",
        last_name="Doe",
        pre_migration_state={
            "userid": "jdoe", "mailid": "jdoe@example.com",
            "associated_devices": ["SEP222222222222"],
        },
    ))

    # Executive/Assistant objects

    # exec_asst_pair: jsmith (executive) -> jdoe (assistant)
    store.upsert_object(MigrationObject(
        canonical_id="exec_asst_pair:jsmith:jdoe",
        provenance=_prov("exec_pair_jsmith_jdoe"),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "executive_userid": "jsmith",
            "assistant_userid": "jdoe",
            "executive_pkid": "{EXEC-PKID-1}",
            "assistant_pkid": "{ASST-PKID-1}",
        },
    ))

    # exec_setting: jsmith is EXECUTIVE
    store.upsert_object(MigrationObject(
        canonical_id="exec_setting:jsmith",
        provenance=_prov("exec_setting_jsmith"),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "userid": "jsmith",
            "role": "EXECUTIVE",
            "service_name": "Executive",
            "servicetype": "Feature",
        },
    ))

    # exec_setting: jdoe is EXECUTIVE_ASSISTANT
    store.upsert_object(MigrationObject(
        canonical_id="exec_setting:jdoe",
        provenance=_prov("exec_setting_jdoe"),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "userid": "jdoe",
            "role": "EXECUTIVE_ASSISTANT",
            "service_name": "Executive-Assistant",
            "servicetype": "Feature",
        },
    ))

    # ==================================================================
    # PHASE 2: Build cross-refs + run transform engine
    # ==================================================================
    # CrossReferenceBuilder.build() clears any existing cross-refs and rebuilds
    # from object pre_migration_state. No manual cross-refs needed — the builder
    # derives everything from:
    #   - device_pool.cucm_location_name → device_pool_at_cucm_location
    #   - device_pool.cucm_datetime_group → device_pool_has_datetime_group
    #   - device.cucm_device_pool → device_in_pool
    #   - device.cucm_owner_user → device_owned_by_user
    #   - user.associated_devices → user_has_device
    CrossReferenceBuilder(store).build()
    TransformEngine().run(store)

    yield store
    store.close()


# ---------------------------------------------------------------------------
# Test 1: TransformEngine produces executive_assistant objects
# ---------------------------------------------------------------------------

class TestEngineProducesExecAssistantObjects:

    def test_engine_produces_exec_assistant_objects(self, exec_store: MigrationStore):
        """Full pipeline: normalize + cross-ref + map produces executive_assistant objects."""
        store = exec_store

        # No mapper errors for executive_assistant_mapper
        # (TransformEngine logs errors in result.errors; we verify by checking
        # that objects were produced successfully)
        ea_objects = store.get_objects("executive_assistant")
        assert len(ea_objects) == 1, (
            f"Expected 1 executive_assistant object, got {len(ea_objects)}"
        )

        ea = ea_objects[0]

        # The executive canonical ID should reference jsmith
        exec_id = (
            ea.get("executive_canonical_id")
            or (ea.get("pre_migration_state") or {}).get("executive_canonical_id")
        )
        assert exec_id == "user:jsmith", (
            f"Expected executive_canonical_id='user:jsmith', got '{exec_id}'"
        )

        # jdoe should be in the assistant list
        asst_ids = (
            ea.get("assistant_canonical_ids")
            or (ea.get("pre_migration_state") or {}).get("assistant_canonical_ids")
            or []
        )
        assert "user:jdoe" in asst_ids, (
            f"Expected 'user:jdoe' in assistant_canonical_ids, got {asst_ids}"
        )


# ---------------------------------------------------------------------------
# Test 2: Assessment report appendix includes Executive/Assistant section
# ---------------------------------------------------------------------------

class TestReportIncludesExecAssistant:

    def test_report_includes_exec_assistant(self, exec_store: MigrationStore):
        """Assessment report appendix includes Executive/Assistant section."""
        store = exec_store

        appendix_html = generate_appendix(store)

        assert "Executive/Assistant" in appendix_html, (
            "Expected 'Executive/Assistant' in appendix HTML"
        )
        # At least one of jsmith/Jsmith should appear (case may vary by formatter)
        assert "jsmith" in appendix_html or "Jsmith" in appendix_html, (
            "Expected 'jsmith' or 'Jsmith' in appendix HTML"
        )
