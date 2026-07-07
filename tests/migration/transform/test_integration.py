"""Full integration test: messy CUCM fixture -> TransformEngine -> verify outputs.

Seeds the store with normalized CUCM objects (base MigrationObject instances)
and cross-refs simulating a real CUCM environment, then runs TransformEngine.run(),
and verifies all outputs: object counts, decision types, shared line tagging,
hunt pilot classification, and location consolidation.

Fixture set from docs/plans/cucm-build-mappers.md lines 706-773.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from wxcli.migration.models import (
    CanonicalUser,
    MapperResult,
    MigrationObject,
    MigrationStatus,
    Provenance,
    TransformResult,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.decisions import (
    decisions_by_type,
    format_decision_report,
    pending_decisions,
    summarize_decisions,
)
from wxcli.migration.transform.engine import MAPPER_ORDER, TransformEngine
from wxcli.migration.transform.mappers.base import Mapper
from wxcli.migration.transform.rules import apply_auto_rules


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

_EXTRACTED_AT = datetime(2026, 3, 20, 12, 0, 0, tzinfo=timezone.utc)


def _prov(name: str, source_id: str | None = None) -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id=source_id or f"pkid-{name}",
        source_name=name,
        cluster="CUCM-01",
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
# Master fixture: seeds a messy CUCM environment into the store
# ---------------------------------------------------------------------------


@pytest.fixture
def messy_store() -> MigrationStore:
    """Build the full messy CUCM fixture set.

    Objects inserted first, then cross-refs (foreign key constraints require
    both endpoints to exist before the cross-ref is created).

    Objects:
    - 3 Device Pools: HQ-Phones, HQ-Softphones (same CUCM Location), Branch-A-Phones
    - 2 CUCM Locations: Headquarters, Branch-A
    - 2 DateTimeGroups: US-Eastern, US-Pacific
    - 5 End Users: user1 (normal), user2 (shared line), user3 (no email),
                   user4 (Branch-A), user5 (manager ref to user1)
    - 6 Phones: phone1 (6841 native_mpp), phone2 (6841 shared), phone3 (7841 convertible),
                phone4 (7911 incompatible), phone5 (common-area), phone6 (6841 Branch-A)
    - 5 DNs: 1001 (shared), 1002, 1003, 1004, 5551234567
    - 3 Partitions: Internal-PT, PSTN-PT, Block-PT
    - 2 Route Patterns
    - 2 CSSes: Employee-CSS, Restricted-CSS
    - 1 SIP Trunk: CUBE-GW-01
    - 1 Hunt Pilot (+ hunt list + line group): HP-Sales with queue features
    - 1 CTI Route Point + Script: CTI-MainMenu
    - 1 Voicemail Profile: VM-Standard
    - 1 Time Schedule + Time Period: Business-Hours
    """
    store = MigrationStore(":memory:")

    # ==================================================================
    # PHASE 1: Insert ALL objects first (FK constraints)
    # ==================================================================

    # CUCM Locations
    store.upsert_object(_obj(
        "cucm_location:Headquarters", "Headquarters",
        {"address1": "100 Main St", "city": "New York", "state": "NY",
         "postal_code": "10001", "country": "US"},
    ))
    store.upsert_object(_obj(
        "cucm_location:Branch-A", "Branch-A",
        {"address1": "200 Oak Ave", "city": "Los Angeles", "state": "CA",
         "postal_code": "90001", "country": "US"},
    ))

    # DateTimeGroups
    store.upsert_object(_obj(
        "dtg:US-Eastern", "US-Eastern",
        {"datetime_group_name": "US-Eastern", "timezone": "America/New_York"},
    ))
    store.upsert_object(_obj(
        "dtg:US-Pacific", "US-Pacific",
        {"datetime_group_name": "US-Pacific", "timezone": "America/Los_Angeles"},
    ))

    # Device Pools
    store.upsert_object(_obj(
        "device_pool:HQ-Phones", "HQ-Phones",
        {"device_pool_name": "HQ-Phones"},
    ))
    store.upsert_object(_obj(
        "device_pool:HQ-Softphones", "HQ-Softphones",
        {"device_pool_name": "HQ-Softphones"},
    ))
    store.upsert_object(_obj(
        "device_pool:Branch-A-Phones", "Branch-A-Phones",
        {"device_pool_name": "Branch-A-Phones"},
    ))

    # DNs (must exist before phone->DN cross-refs)
    store.upsert_object(_obj(
        "dn:5551234567:Internal-PT", "5551234567",
        {"pattern": "5551234567", "partition": "Internal-PT"},
    ))
    store.upsert_object(_obj(
        "dn:1001:Internal-PT", "1001",
        {"pattern": "1001", "partition": "Internal-PT"},
    ))
    store.upsert_object(_obj(
        "dn:1002:Internal-PT", "1002",
        {"pattern": "1002", "partition": "Internal-PT"},
    ))
    store.upsert_object(_obj(
        "dn:1003:Internal-PT", "1003",
        {"pattern": "1003", "partition": "Internal-PT"},
    ))
    store.upsert_object(_obj(
        "dn:1004:Internal-PT", "1004",
        {"pattern": "1004", "partition": "Internal-PT"},
    ))

    # Phones
    store.upsert_object(_obj(
        "phone:SEP001122334401", "SEP001122334401",
        {"name": "SEP001122334401", "model": "Cisco 6841", "protocol": "SIP",
         "is_common_area": False, "description": "User1 Desk Phone",
         "line_appearances": [
             {"dn_canonical_id": "dn:5551234567:Internal-PT", "position": 1},
         ]},
    ))
    store.upsert_object(_obj(
        "phone:SEP001122334402", "SEP001122334402",
        {"name": "SEP001122334402", "model": "Cisco 6841", "protocol": "SIP",
         "is_common_area": False, "description": "User2 Desk Phone",
         "line_appearances": [
             {"dn_canonical_id": "dn:1001:Internal-PT", "position": 1},
         ]},
    ))
    store.upsert_object(_obj(
        "phone:SEP001122334403", "SEP001122334403",
        {"name": "SEP001122334403", "model": "Cisco 7841", "protocol": "SIP",
         "is_common_area": False, "description": "User2 Secondary Phone",
         "line_appearances": [
             {"dn_canonical_id": "dn:1001:Internal-PT", "position": 1},
         ]},
    ))
    store.upsert_object(_obj(
        "phone:SEP001122334404", "SEP001122334404",
        {"name": "SEP001122334404", "model": "Cisco 7911", "protocol": "SCCP",
         "is_common_area": False, "description": "User3 Old Phone",
         "line_appearances": [
             {"dn_canonical_id": "dn:1003:Internal-PT", "position": 1},
         ]},
    ))
    store.upsert_object(_obj(
        "phone:SEP001122334405", "SEP001122334405",
        {"name": "SEP001122334405", "model": "Cisco 6841", "protocol": "SIP",
         "is_common_area": True, "description": "Lobby Phone",
         "cucm_device_pool": "HQ-Phones",
         "line_appearances": [
             {"dn_canonical_id": "dn:1004:Internal-PT", "position": 1},
         ]},
    ))
    store.upsert_object(_obj(
        "phone:SEP001122334406", "SEP001122334406",
        {"name": "SEP001122334406", "model": "Cisco 6841", "protocol": "SIP",
         "is_common_area": False, "description": "User4 Branch Phone",
         "line_appearances": [
             {"dn_canonical_id": "dn:1002:Internal-PT", "position": 1},
         ]},
    ))

    # End Users — stored as CanonicalUser so cucm_mailid / cucm_userid are
    # at the JSON top level (matching what the normalizer produces, and what
    # UserMapper reads via user_data.get("cucm_mailid")).
    store.upsert_object(CanonicalUser(
        canonical_id="user:jsmith",
        provenance=_prov("jsmith"),
        status=MigrationStatus.NORMALIZED,
        cucm_userid="jsmith",
        cucm_mailid="jsmith@example.com",
        first_name="John",
        last_name="Smith",
        department="Engineering",
        title="Engineer",
        pre_migration_state={"userid": "jsmith", "mailid": "jsmith@example.com"},
    ))
    store.upsert_object(CanonicalUser(
        canonical_id="user:jdoe",
        provenance=_prov("jdoe"),
        status=MigrationStatus.NORMALIZED,
        cucm_userid="jdoe",
        cucm_mailid="jdoe@example.com",
        first_name="Jane",
        last_name="Doe",
        department="Sales",
        title="Rep",
        pre_migration_state={"userid": "jdoe", "mailid": "jdoe@example.com"},
    ))
    store.upsert_object(CanonicalUser(
        canonical_id="user:noemail",
        provenance=_prov("noemail"),
        status=MigrationStatus.NORMALIZED,
        cucm_userid="noemail",
        cucm_mailid="",
        first_name="No",
        last_name="Email",
        pre_migration_state={"userid": "noemail", "mailid": ""},
    ))
    store.upsert_object(CanonicalUser(
        canonical_id="user:bwilson",
        provenance=_prov("bwilson"),
        status=MigrationStatus.NORMALIZED,
        cucm_userid="bwilson",
        cucm_mailid="bwilson@example.com",
        first_name="Bob",
        last_name="Wilson",
        department="Support",
        pre_migration_state={"userid": "bwilson", "mailid": "bwilson@example.com"},
    ))
    store.upsert_object(CanonicalUser(
        canonical_id="user:mmanager",
        provenance=_prov("mmanager"),
        status=MigrationStatus.NORMALIZED,
        cucm_userid="mmanager",
        cucm_mailid="mmanager@example.com",
        first_name="Mary",
        last_name="Manager",
        department="Engineering",
        title="Director",
        cucm_manager_user_id="jsmith",
        pre_migration_state={"userid": "mmanager", "mailid": "mmanager@example.com", "manager": "jsmith"},
    ))

    # Partitions
    store.upsert_object(_obj(
        "partition:Internal-PT", "Internal-PT",
        {"name": "Internal-PT", "description": "Internal directory"},
    ))
    store.upsert_object(_obj(
        "partition:PSTN-PT", "PSTN-PT",
        {"name": "PSTN-PT", "description": "PSTN routing"},
    ))
    store.upsert_object(_obj(
        "partition:Block-PT", "Block-PT",
        {"name": "Block-PT", "description": "Call blocking"},
    ))

    # Route Patterns
    store.upsert_object(_obj(
        "route_pattern:9.1[2-9]XXXXXXXXX:PSTN-PT", "9.1[2-9]XXXXXXXXX",
        {"pattern": "9.1[2-9]XXXXXXXXX", "action": "ROUTE",
         "target_type": "gateway", "target_name": "CUBE-GW-01"},
    ))
    store.upsert_object(_obj(
        "route_pattern:9.1900XXXXXXX:Block-PT", "9.1900XXXXXXX",
        {"pattern": "9.1900XXXXXXX", "action": "BLOCK"},
    ))

    # CSSes
    store.upsert_object(_obj(
        "css:Employee-CSS", "Employee-CSS",
        {"name": "Employee-CSS"},
    ))
    store.upsert_object(_obj(
        "css:Restricted-CSS", "Restricted-CSS",
        {"name": "Restricted-CSS"},
    ))

    # SIP Trunk
    store.upsert_object(_obj(
        "sip_trunk:CUBE-GW-01", "CUBE-GW-01",
        {"name": "CUBE-GW-01",
         "destinations": [{"address": "cube01.example.com", "port": 5060, "sort_order": 1}],
         "max_calls": 100},
    ))

    # Hunt Pilot + Hunt List + Line Group
    store.upsert_object(_obj(
        "hunt_pilot:HP-Sales", "HP-Sales",
        {"name": "Sales Queue", "pattern": "2000",
         "extension": "2000",
         "queueCalls": {"enabled": True, "maxCallersInQueue": 10},
         "enabled": True},
    ))
    store.upsert_object(_obj(
        "hunt_list:HL-Sales", "HL-Sales",
        {"name": "Sales Hunt List",
         "voiceMailUsage": "NONE"},
    ))
    store.upsert_object(_obj(
        "line_group:LG-Sales", "LG-Sales",
        {"name": "Sales Line Group", "distributionAlgorithm": "Circular",
         "rnaReversionTimeOut": 18},
    ))

    # CTI Route Point + Script
    store.upsert_object(_obj(
        "cti_rp:CTI-MainMenu", "CTI-MainMenu",
        {"name": "Main Menu IVR", "pattern": "3000", "extension": "3000",
         "description": "Main Menu Auto Attendant"},
    ))
    store.upsert_object(_obj(
        "script:MainMenuScript", "MainMenuScript",
        {"name": "MainMenuScript", "script_type": "Cisco"},
    ))

    # Voicemail Profile
    store.upsert_object(_obj(
        "voicemail_profile:VM-Standard", "VM-Standard",
        {"voicemail_profile_name": "VM-Standard",
         "cfnaTimeout": 18,
         "callerInputRules": [{"digit": "0", "action": "transfer"}],
         "callForwardNoAnswer": True},
    ))

    # Time Schedule + Time Period
    store.upsert_object(_obj(
        "time_schedule:Business-Hours", "Business-Hours",
        {"name": "Business Hours", "schedule_type": "SAME_HOURS_DAILY"},
    ))
    store.upsert_object(_obj(
        "time_period:BH-Weekdays", "BH-Weekdays",
        {"name": "BH-Weekdays", "start_time": "08:00", "end_time": "17:00",
         "day_of_week": "Monday-Friday"},
    ))

    # ==================================================================
    # PHASE 2: Insert ALL cross-refs (all objects exist now)
    # ==================================================================

    # Device Pool -> CUCM Location
    store.add_cross_ref("device_pool:HQ-Phones", "cucm_location:Headquarters", "device_pool_at_cucm_location")
    store.add_cross_ref("device_pool:HQ-Softphones", "cucm_location:Headquarters", "device_pool_at_cucm_location")
    store.add_cross_ref("device_pool:Branch-A-Phones", "cucm_location:Branch-A", "device_pool_at_cucm_location")

    # Device Pool -> DateTimeGroup
    store.add_cross_ref("device_pool:HQ-Phones", "dtg:US-Eastern", "device_pool_has_datetime_group")
    store.add_cross_ref("device_pool:HQ-Softphones", "dtg:US-Eastern", "device_pool_has_datetime_group")
    store.add_cross_ref("device_pool:Branch-A-Phones", "dtg:US-Pacific", "device_pool_has_datetime_group")

    # Phone -> Device Pool
    store.add_cross_ref("phone:SEP001122334401", "device_pool:HQ-Phones", "device_in_pool")
    store.add_cross_ref("phone:SEP001122334402", "device_pool:HQ-Phones", "device_in_pool")
    store.add_cross_ref("phone:SEP001122334403", "device_pool:HQ-Softphones", "device_in_pool")
    store.add_cross_ref("phone:SEP001122334404", "device_pool:HQ-Phones", "device_in_pool")
    store.add_cross_ref("phone:SEP001122334405", "device_pool:HQ-Phones", "common_area_device_in_pool")
    store.add_cross_ref("phone:SEP001122334406", "device_pool:Branch-A-Phones", "device_in_pool")

    # Phone -> DN (device_has_dn)
    store.add_cross_ref("phone:SEP001122334401", "dn:5551234567:Internal-PT", "device_has_dn")
    store.add_cross_ref("phone:SEP001122334402", "dn:1001:Internal-PT", "device_has_dn")
    store.add_cross_ref("phone:SEP001122334403", "dn:1001:Internal-PT", "device_has_dn")  # Shared line!
    store.add_cross_ref("phone:SEP001122334404", "dn:1003:Internal-PT", "device_has_dn")
    store.add_cross_ref("phone:SEP001122334405", "dn:1004:Internal-PT", "device_has_dn")
    store.add_cross_ref("phone:SEP001122334406", "dn:1002:Internal-PT", "device_has_dn")

    # Phone -> User (device_owned_by_user)
    store.add_cross_ref("phone:SEP001122334401", "user:jsmith", "device_owned_by_user")
    store.add_cross_ref("phone:SEP001122334402", "user:jdoe", "device_owned_by_user")
    store.add_cross_ref("phone:SEP001122334403", "user:jdoe", "device_owned_by_user")
    store.add_cross_ref("phone:SEP001122334404", "user:noemail", "device_owned_by_user")
    store.add_cross_ref("phone:SEP001122334406", "user:bwilson", "device_owned_by_user")

    # User -> Device (user_has_device)
    store.add_cross_ref("user:jsmith", "phone:SEP001122334401", "user_has_device")
    store.add_cross_ref("user:jdoe", "phone:SEP001122334402", "user_has_device")
    store.add_cross_ref("user:jdoe", "phone:SEP001122334403", "user_has_device")
    store.add_cross_ref("user:noemail", "phone:SEP001122334404", "user_has_device")
    store.add_cross_ref("user:bwilson", "phone:SEP001122334406", "user_has_device")
    store.add_cross_ref("user:mmanager", "phone:SEP001122334401", "user_has_device")

    # User -> Primary DN
    store.add_cross_ref("user:jsmith", "dn:5551234567:Internal-PT", "user_has_primary_dn")
    store.add_cross_ref("user:jdoe", "dn:1001:Internal-PT", "user_has_primary_dn")
    store.add_cross_ref("user:noemail", "dn:1003:Internal-PT", "user_has_primary_dn")
    store.add_cross_ref("user:bwilson", "dn:1002:Internal-PT", "user_has_primary_dn")
    store.add_cross_ref("user:mmanager", "dn:5551234567:Internal-PT", "user_has_primary_dn")

    # Partition -> Route Pattern
    store.add_cross_ref("partition:PSTN-PT", "route_pattern:9.1[2-9]XXXXXXXXX:PSTN-PT", "partition_has_pattern")
    store.add_cross_ref("partition:Block-PT", "route_pattern:9.1900XXXXXXX:Block-PT", "partition_has_pattern")

    # Route Pattern -> Gateway
    store.add_cross_ref("route_pattern:9.1[2-9]XXXXXXXXX:PSTN-PT", "sip_trunk:CUBE-GW-01", "route_pattern_uses_gateway")

    # CSS -> Partitions (ordered)
    store.add_cross_ref("css:Employee-CSS", "partition:Internal-PT", "css_contains_partition", ordinal=1)
    store.add_cross_ref("css:Employee-CSS", "partition:PSTN-PT", "css_contains_partition", ordinal=2)
    store.add_cross_ref("css:Restricted-CSS", "partition:Internal-PT", "css_contains_partition", ordinal=1)
    store.add_cross_ref("css:Restricted-CSS", "partition:PSTN-PT", "css_contains_partition", ordinal=2)
    store.add_cross_ref("css:Restricted-CSS", "partition:Block-PT", "css_contains_partition", ordinal=3)

    # User -> CSS
    store.add_cross_ref("user:jsmith", "css:Employee-CSS", "user_has_css")
    store.add_cross_ref("user:jdoe", "css:Employee-CSS", "user_has_css")
    store.add_cross_ref("user:bwilson", "css:Restricted-CSS", "user_has_css")

    # Trunk -> Device Pool (for location resolution)
    store.add_cross_ref("sip_trunk:CUBE-GW-01", "device_pool:HQ-Phones", "trunk_at_location")

    # Hunt Pilot -> Hunt List -> Line Group -> Members
    store.add_cross_ref("hunt_pilot:HP-Sales", "hunt_list:HL-Sales", "hunt_pilot_has_hunt_list")
    store.add_cross_ref("hunt_list:HL-Sales", "line_group:LG-Sales", "hunt_list_has_line_group")
    store.add_cross_ref("line_group:LG-Sales", "user:jsmith", "line_group_has_members")
    store.add_cross_ref("line_group:LG-Sales", "user:jdoe", "line_group_has_members")

    # CTI Route Point -> Script
    store.add_cross_ref("cti_rp:CTI-MainMenu", "script:MainMenuScript", "cti_rp_has_script")

    # User -> Voicemail Profile
    store.add_cross_ref("user:jsmith", "voicemail_profile:VM-Standard", "user_has_voicemail_profile")

    # Time Schedule -> Time Period
    store.add_cross_ref("time_schedule:Business-Hours", "time_period:BH-Weekdays", "schedule_has_time_period")

    return store


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------


class TestFullIntegration:
    """Run TransformEngine on the messy fixture and verify all outputs."""

    def test_engine_runs_without_errors(self, messy_store: MigrationStore) -> None:
        """All 9 mappers should complete without exceptions."""
        engine = TransformEngine()
        result = engine.run(messy_store)

        assert isinstance(result, TransformResult)
        for err in result.errors:
            pytest.fail(f"Mapper {err.mapper_name} failed: {err.error_message}")

    def test_location_consolidation(self, messy_store: MigrationStore) -> None:
        """HQ-Phones + HQ-Softphones -> 1 location, Branch-A-Phones -> 1 location.
        Total: 2 CanonicalLocations."""
        engine = TransformEngine()
        engine.run(messy_store)

        locations = messy_store.get_objects("location")
        assert len(locations) == 2

        hq_location = None
        branch_location = None
        for loc in locations:
            pool_names = loc.get("cucm_device_pool_names", [])
            if "HQ-Phones" in pool_names:
                hq_location = loc
            elif "Branch-A-Phones" in pool_names:
                branch_location = loc

        assert hq_location is not None, "HQ consolidated location not found"
        assert branch_location is not None, "Branch-A location not found"

        # HQ location should have both pool names
        assert "HQ-Phones" in hq_location["cucm_device_pool_names"]
        assert "HQ-Softphones" in hq_location["cucm_device_pool_names"]

        # Verify timezone from DateTimeGroup
        assert hq_location.get("time_zone") == "America/New_York"
        assert branch_location.get("time_zone") == "America/Los_Angeles"

        # Verify address from CUCM Location
        assert hq_location["address"]["city"] == "New York"
        assert branch_location["address"]["city"] == "Los Angeles"

    def test_user_mapping_missing_email(self, messy_store: MigrationStore) -> None:
        """User3 (no email) produces MISSING_DATA decision."""
        engine = TransformEngine()
        result = engine.run(messy_store)

        missing_data_decisions = [
            d for d in result.decisions
            if d.type.value == "MISSING_DATA"
            and "noemail" in d.summary
        ]
        assert len(missing_data_decisions) >= 1, "Expected MISSING_DATA for user with no email"

    def test_device_compatibility_tiers(self, messy_store: MigrationStore) -> None:
        """Phone1 (6841): native_mpp, Phone3 (7841): convertible,
        Phone4 (7911 SCCP): incompatible.
        Phone5 (common-area) should NOT appear in devices."""
        engine = TransformEngine()
        result = engine.run(messy_store)

        devices = messy_store.get_objects("device")
        device_by_name = {d.get("cucm_device_name", ""): d for d in devices}

        # Phone1: native_mpp (6841)
        p1 = device_by_name.get("SEP001122334401")
        assert p1 is not None
        assert p1.get("compatibility_tier") == "native_mpp"

        # Phone3: convertible (7841)
        p3 = device_by_name.get("SEP001122334403")
        assert p3 is not None
        assert p3.get("compatibility_tier") == "convertible"

        # Phone4: incompatible (7911 + SCCP)
        p4 = device_by_name.get("SEP001122334404")
        assert p4 is not None
        assert p4.get("compatibility_tier") == "incompatible"

        # Phone5 (common-area) should NOT be in devices
        assert "SEP001122334405" not in device_by_name

        # Verify decisions — convertible is classification-only (no decision)
        decision_types = [d.type.value for d in result.decisions]
        assert "DEVICE_INCOMPATIBLE" in decision_types
        assert "DEVICE_FIRMWARE_CONVERTIBLE" not in decision_types

    def test_workspace_from_common_area(self, messy_store: MigrationStore) -> None:
        """Phone5 (common-area) should produce a CanonicalWorkspace."""
        engine = TransformEngine()
        engine.run(messy_store)

        workspaces = messy_store.get_objects("workspace")
        assert len(workspaces) >= 1

        ws = workspaces[0]
        assert ws.get("is_common_area") is True
        assert ws.get("display_name") == "Lobby Phone"

    def test_shared_line_tagging(self, messy_store: MigrationStore) -> None:
        """DN 1001 is on phone2 and phone3 -> should be tagged shared=True."""
        engine = TransformEngine()
        engine.run(messy_store)

        lines = messy_store.get_objects("line")
        line_by_pattern = {}
        for line in lines:
            pattern = line.get("cucm_pattern", "")
            line_by_pattern[pattern] = line

        # DN 1001 should be shared
        dn_1001 = line_by_pattern.get("1001")
        assert dn_1001 is not None, "Line for DN 1001 not found"
        assert dn_1001.get("shared") is True, "DN 1001 should be shared (2 devices)"

        # DN 1002 should NOT be shared (only 1 device)
        dn_1002 = line_by_pattern.get("1002")
        if dn_1002:
            assert dn_1002.get("shared") is False

    def test_routing_objects(self, messy_store: MigrationStore) -> None:
        """Should produce 1 trunk and at least 1 dial plan from route patterns."""
        engine = TransformEngine()
        engine.run(messy_store)

        trunks = messy_store.get_objects("trunk")
        assert len(trunks) >= 1
        trunk = trunks[0]
        assert trunk.get("name") == "CUBE-GW-01"
        assert trunk.get("address") == "cube01.example.com"

        dial_plans = messy_store.get_objects("dial_plan")
        assert len(dial_plans) >= 1

    def test_hunt_pilot_classified_as_call_queue(self, messy_store: MigrationStore) -> None:
        """Hunt pilot with queueCalls.enabled=True -> CallQueue, not HuntGroup."""
        engine = TransformEngine()
        engine.run(messy_store)

        call_queues = messy_store.get_objects("call_queue")
        assert len(call_queues) >= 1, "Expected at least 1 call queue from queue-style hunt pilot"

        cq = call_queues[0]
        assert cq.get("name") == "Sales Queue"
        assert cq.get("extension") == "2000"
        assert cq.get("policy") == "CIRCULAR"

        # Should NOT produce a hunt group for this pilot
        hunt_groups = messy_store.get_objects("hunt_group")
        hg_names = [hg.get("name") for hg in hunt_groups]
        assert "Sales Queue" not in hg_names

    def test_cti_rp_produces_auto_attendant(self, messy_store: MigrationStore) -> None:
        """CTI Route Point -> CanonicalAutoAttendant + FEATURE_APPROXIMATION decision."""
        engine = TransformEngine()
        result = engine.run(messy_store)

        auto_attendants = messy_store.get_objects("auto_attendant")
        assert len(auto_attendants) >= 1

        aa = auto_attendants[0]
        assert aa.get("name") == "Main Menu IVR"
        assert aa.get("extension") == "3000"

        fa_decisions = [
            d for d in result.decisions
            if d.type.value == "FEATURE_APPROXIMATION"
            and "CTI Route Point" in d.summary
        ]
        assert len(fa_decisions) >= 1

    def test_voicemail_profile_mapped(self, messy_store: MigrationStore) -> None:
        """User jsmith has VM profile with CFNA 18s -> 3 rings, callerInputRules -> gap."""
        engine = TransformEngine()
        result = engine.run(messy_store)

        vm_profiles = messy_store.get_objects("voicemail_profile")
        assert len(vm_profiles) >= 1

        vm = vm_profiles[0]
        assert vm.get("enabled") is True
        assert vm.get("user_canonical_id") == "user:jsmith"

        # CFNA 18 seconds / 6 = 3 rings
        unanswered = vm.get("send_unanswered_calls", {})
        assert unanswered.get("numberOfRings") == 3

        # Should have VOICEMAIL_INCOMPATIBLE for callerInputRules
        vm_decisions = [
            d for d in result.decisions
            if d.type.value == "VOICEMAIL_INCOMPATIBLE"
        ]
        assert len(vm_decisions) >= 1

    def test_operating_mode_from_schedule(self, messy_store: MigrationStore) -> None:
        """Time Schedule -> CanonicalOperatingMode."""
        engine = TransformEngine()
        engine.run(messy_store)

        operating_modes = messy_store.get_objects("operating_mode")
        assert len(operating_modes) >= 1

        om = operating_modes[0]
        assert om.get("name") == "Business Hours"
        assert om.get("schedule_type") == "SAME_HOURS_DAILY"

    def test_css_produces_calling_permissions(self, messy_store: MigrationStore) -> None:
        """CSS decomposition should produce CallingPermissions."""
        engine = TransformEngine()
        engine.run(messy_store)

        permissions = messy_store.get_objects("calling_permission")
        assert len(permissions) >= 1

    def test_expected_decision_types(self, messy_store: MigrationStore) -> None:
        """Verify the full set of expected decision types from the messy fixture."""
        engine = TransformEngine()
        result = engine.run(messy_store)

        decision_types = {d.type.value for d in result.decisions}

        assert "MISSING_DATA" in decision_types, "Expected MISSING_DATA (user3 no email, trunk password)"
        assert "DEVICE_INCOMPATIBLE" in decision_types, "Expected DEVICE_INCOMPATIBLE (7911)"
        # DEVICE_FIRMWARE_CONVERTIBLE no longer emitted — convertibility is
        # a model classification, not a decision.
        assert "DEVICE_FIRMWARE_CONVERTIBLE" not in decision_types
        assert "FEATURE_APPROXIMATION" in decision_types, "Expected FEATURE_APPROXIMATION (CTI RP)"
        assert "VOICEMAIL_INCOMPATIBLE" in decision_types, "Expected VOICEMAIL_INCOMPATIBLE (callerInputRules)"

    def test_national_dn_classified_with_e164(self, messy_store: MigrationStore) -> None:
        """DN '5551234567' at a US location should be classified NATIONAL with E.164.
        (from build plan line 742)
        """
        engine = TransformEngine()
        engine.run(messy_store)

        lines = messy_store.get_objects("line")
        national_dn = None
        for line in lines:
            if line.get("cucm_pattern") == "5551234567":
                national_dn = line
                break
        if national_dn:
            assert national_dn.get("classification") in ("NATIONAL", "E164"), (
                f"DN 5551234567 should be NATIONAL or E164, got {national_dn.get('classification')}"
            )
            # E.164 may vary by phonenumbers library version, but should start with +
            if national_dn.get("e164"):
                assert national_dn["e164"].startswith("+"), "E.164 should start with +"

    def test_decisions_saved_to_store(self, messy_store: MigrationStore) -> None:
        """All decisions from engine should be saved in the store."""
        engine = TransformEngine()
        result = engine.run(messy_store)

        store_decisions = messy_store.get_all_decisions()
        assert len(store_decisions) >= len(result.decisions)

    def test_auto_rules_resolve_decisions(self, messy_store: MigrationStore) -> None:
        """After engine.run(), apply auto-rules and verify resolution."""
        engine = TransformEngine()
        engine.run(messy_store)

        config = {
            "auto_rules": [
                {"type": "DEVICE_INCOMPATIBLE", "choice": "skip"},
            ]
        }
        count = apply_auto_rules(messy_store, config)
        assert count >= 1  # At least 7911 incompatible

        all_decs = messy_store.get_all_decisions()
        device_incompat = [d for d in all_decs if d["type"] == "DEVICE_INCOMPATIBLE"]
        for d in device_incompat:
            assert d["chosen_option"] == "skip"
            assert d["resolved_by"] == "auto_rule"

    def test_decision_helpers(self, messy_store: MigrationStore) -> None:
        """Test decision helper functions after engine.run()."""
        engine = TransformEngine()
        engine.run(messy_store)

        all_decisions = messy_store.get_all_decisions()

        # summarize_decisions
        summary = summarize_decisions(all_decisions)
        assert isinstance(summary, dict)
        assert len(summary) > 0

        # format_decision_report
        report = format_decision_report(all_decisions)
        assert "Decision Report:" in report
        assert "total" in report

        # decisions_by_type
        missing = decisions_by_type(messy_store, "MISSING_DATA")
        assert len(missing) >= 1

        # pending_decisions
        pend = pending_decisions(messy_store)
        assert len(pend) == len(all_decisions)

    def test_mappers_dont_interfere(self, messy_store: MigrationStore) -> None:
        """Running the engine twice produces the same object counts (idempotent upserts)."""
        engine = TransformEngine()

        engine.run(messy_store)
        locations_1 = len(messy_store.get_objects("location"))
        users_1 = len(messy_store.get_objects("user"))
        devices_1 = len(messy_store.get_objects("device"))

        engine.run(messy_store)
        locations_2 = len(messy_store.get_objects("location"))
        users_2 = len(messy_store.get_objects("user"))
        devices_2 = len(messy_store.get_objects("device"))

        assert locations_1 == locations_2
        assert users_1 == users_2
        assert devices_1 == devices_2


class TestEngineFailureHandling:
    """Test that one mapper explosion does not crash the pipeline."""

    def test_single_mapper_failure_continues(self) -> None:
        """Inject a failing mapper into the order and verify others still run."""
        store = MigrationStore(":memory:")

        # Seed minimal data for LocationMapper
        store.upsert_object(_obj(
            "device_pool:TestPool", "TestPool",
            {"device_pool_name": "TestPool"},
        ))
        store.upsert_object(_obj(
            "cucm_location:TestLoc", "TestLoc",
            {"city": "Test City", "country": "US"},
        ))
        store.add_cross_ref("device_pool:TestPool", "cucm_location:TestLoc", "device_pool_at_cucm_location")

        original_order = list(MAPPER_ORDER)

        class FailingMapper(Mapper):
            name = "failing_mapper"
            depends_on: list[str] = []

            def map(self, store_arg: MigrationStore) -> MapperResult:
                raise ValueError("I always fail")

        try:
            # Put FailingMapper between LocationMapper and RoutingMapper
            MAPPER_ORDER.clear()
            MAPPER_ORDER.append(original_order[0])  # LocationMapper
            MAPPER_ORDER.append(FailingMapper)
            MAPPER_ORDER.extend(original_order[1:])

            engine = TransformEngine()
            result = engine.run(store)

            # Should have exactly 1 error (from FailingMapper)
            assert len(result.errors) == 1
            assert result.errors[0].mapper_name == "failing_mapper"

            # LocationMapper should have still produced a location
            locations = store.get_objects("location")
            assert len(locations) >= 1

        finally:
            MAPPER_ORDER.clear()
            MAPPER_ORDER.extend(original_order)
