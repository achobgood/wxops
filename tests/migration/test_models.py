"""Tests for migration canonical models.

Acceptance criteria:
- All ~20 canonical types instantiate without error
- MigrationObject base has canonical_id, provenance, status, webex_id, depends_on, batch
- Every type used in 03b mapper tables exists
"""

import pytest
from datetime import datetime, timezone

from wxcli.migration.models import (
    CANONICAL_TYPE_REGISTRY,
    CallingPermissionEntry,
    CanonicalAutoAttendant,
    CanonicalCallPark,
    CanonicalCallQueue,
    CanonicalCallingPermission,
    CanonicalDevice,
    CanonicalDialPlan,
    CanonicalHuntGroup,
    CanonicalLine,
    CanonicalLocation,
    CanonicalOperatingMode,
    CanonicalPagingGroup,
    CanonicalPickupGroup,
    CanonicalRouteGroup,
    CanonicalSharedLine,
    CanonicalTranslationPattern,
    CanonicalTrunk,
    CanonicalUser,
    CanonicalVirtualLine,
    CanonicalVoicemailProfile,
    CanonicalWorkspace,
    DeviceCompatibilityTier,
    LineClassification,
    LocationAddress,
    MigrationInventory,
    MigrationObject,
    MigrationStatus,
    Provenance,
    TrunkGatewayRef,
)


@pytest.fixture
def sample_provenance():
    return Provenance(
        source_system="cucm",
        source_id="pk-abc-123",
        source_name="SEP001122AABBCC",
        cluster="cucm-cluster-1",
        extracted_at=datetime.now(timezone.utc),
        cucm_version="14.0",
    )


@pytest.fixture
def base_kwargs(sample_provenance):
    return {
        "canonical_id": "test:001",
        "provenance": sample_provenance,
    }


class TestMigrationStatus:
    def test_all_values(self):
        expected = {
            "discovered", "normalized", "analyzed", "needs_decision", "planned",
            "preflight_passed", "executing", "completed", "failed", "skipped",
            "rolled_back", "stale",
        }
        actual = {s.value for s in MigrationStatus}
        assert actual == expected

    def test_four_state_progression(self):
        """Object status progression: discovered -> normalized -> analyzed -> planned"""
        progression = [
            MigrationStatus.DISCOVERED,
            MigrationStatus.NORMALIZED,
            MigrationStatus.ANALYZED,
            MigrationStatus.PLANNED,
        ]
        assert all(isinstance(s, MigrationStatus) for s in progression)


class TestProvenance:
    def test_create(self, sample_provenance):
        assert sample_provenance.source_system == "cucm"
        assert sample_provenance.source_id == "pk-abc-123"

    def test_optional_fields(self):
        p = Provenance(
            source_system="webex",
            source_id="uuid-123",
            source_name="Test User",
            extracted_at=datetime.now(timezone.utc),
        )
        assert p.cluster is None
        assert p.cucm_version is None


class TestMigrationObject:
    def test_base_fields(self, base_kwargs):
        obj = MigrationObject(**base_kwargs)
        assert obj.canonical_id == "test:001"
        assert obj.status == MigrationStatus.DISCOVERED
        assert obj.webex_id is None
        assert obj.depends_on == []
        assert obj.batch is None
        assert obj.errors == []
        assert obj.warnings == []

    def test_serialization_roundtrip(self, base_kwargs):
        obj = MigrationObject(**base_kwargs, batch="batch-1", depends_on=["dep:001"])
        data = obj.model_dump_json()
        restored = MigrationObject.model_validate_json(data)
        assert restored.canonical_id == obj.canonical_id
        assert restored.batch == "batch-1"
        assert restored.depends_on == ["dep:001"]


class TestAllCanonicalTypes:
    """Verify every canonical type from the design spec instantiates."""

    def test_registry_has_21_types(self):
        assert len(CANONICAL_TYPE_REGISTRY) == 21

    @pytest.mark.parametrize("type_name", list(CANONICAL_TYPE_REGISTRY.keys()))
    def test_instantiate_type(self, type_name, base_kwargs):
        cls = CANONICAL_TYPE_REGISTRY[type_name]
        obj = cls(**base_kwargs)
        assert obj.canonical_id == "test:001"
        assert isinstance(obj, MigrationObject)


class TestCanonicalLocation:
    def test_fields(self, base_kwargs):
        loc = CanonicalLocation(
            **base_kwargs,
            name="HQ-Phones",
            time_zone="America/Los_Angeles",
            calling_enabled=True,
            address=LocationAddress(
                address1="123 Main St",
                city="San Jose",
                state="CA",
                postal_code="95134",
                country="US",
            ),
            routing_prefix="800",
            outside_dial_digit="9",
        )
        assert loc.name == "HQ-Phones"
        assert loc.address.city == "San Jose"
        assert loc.calling_enabled is True


class TestCanonicalUser:
    def test_fields(self, base_kwargs):
        user = CanonicalUser(
            **base_kwargs,
            emails=["jsmith@example.com"],
            first_name="John",
            last_name="Smith",
            display_name="John Smith",
            extension="1001",
            create_method="scim",
            calling_data=True,
            cucm_manager_user_id="mgr-pk-456",
        )
        assert user.emails == ["jsmith@example.com"]
        assert user.create_method == "scim"
        assert user.calling_data is True


class TestCanonicalLine:
    def test_fields(self, base_kwargs):
        line = CanonicalLine(
            **base_kwargs,
            extension="1001",
            e164="+15551001001",
            classification=LineClassification.NATIONAL,
            shared=False,
            cucm_pattern="1001",
        )
        assert line.classification == LineClassification.NATIONAL
        assert line.e164 == "+15551001001"


class TestCanonicalDevice:
    def test_compatibility_tiers(self, base_kwargs):
        for tier in DeviceCompatibilityTier:
            dev = CanonicalDevice(**base_kwargs, compatibility_tier=tier)
            assert dev.compatibility_tier == tier

    def test_fields(self, base_kwargs):
        dev = CanonicalDevice(
            **base_kwargs,
            mac="001122AABBCC",
            model="Cisco 8845",
            compatibility_tier=DeviceCompatibilityTier.CONVERTIBLE,
            cucm_protocol="SIP",
        )
        assert dev.mac == "001122AABBCC"
        assert dev.cucm_protocol == "SIP"


class TestCanonicalRouteGroup:
    def test_local_gateways(self, base_kwargs):
        rg = CanonicalRouteGroup(
            **base_kwargs,
            name="RG-PSTN",
            local_gateways=[
                TrunkGatewayRef(trunk_canonical_id="trunk:001", priority=1),
                TrunkGatewayRef(trunk_canonical_id="trunk:002", priority=2),
            ],
        )
        assert len(rg.local_gateways) == 2
        assert rg.local_gateways[0].priority == 1


class TestCanonicalCallingPermission:
    def test_fields(self, base_kwargs):
        cp = CanonicalCallingPermission(
            **base_kwargs,
            calling_permissions=[
                CallingPermissionEntry(call_type="INTERNATIONAL", action="BLOCK", transfer_enabled=False),
                CallingPermissionEntry(call_type="NATIONAL", action="ALLOW", transfer_enabled=True),
            ],
            assigned_users=["user:001", "user:002"],
        )
        assert len(cp.calling_permissions) == 2
        assert cp.assigned_users == ["user:001", "user:002"]
        assert cp.use_custom_enabled is True


class TestMigrationInventory:
    def test_create_empty(self):
        inv = MigrationInventory(project_id="proj-1", cucm_cluster="cucm-hq")
        assert inv.project_id == "proj-1"
        assert inv.locations == []
        assert inv.users == []

    def test_with_objects(self, base_kwargs):
        loc = CanonicalLocation(**{**base_kwargs, "canonical_id": "loc:001"}, name="HQ")
        user = CanonicalUser(**{**base_kwargs, "canonical_id": "user:001"}, first_name="John")
        inv = MigrationInventory(
            project_id="proj-1",
            cucm_cluster="cucm-hq",
            locations=[loc],
            users=[user],
        )
        assert len(inv.locations) == 1
        assert len(inv.users) == 1


def test_new_decision_types_exist():
    """Tier 2 DecisionTypes are defined."""
    from wxcli.migration.models import DecisionType
    assert hasattr(DecisionType, "FORWARDING_LOSSY")
    assert hasattr(DecisionType, "SNR_LOSSY")
    assert hasattr(DecisionType, "AUDIO_ASSET_MANUAL")
