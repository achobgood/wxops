"""Tests for DeviceProfileMapper — CUCM Extension Mobility → hot desking advisory."""

from __future__ import annotations
from datetime import datetime, timezone

from wxcli.migration.models import (
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.device_profile_mapper import DeviceProfileMapper


def _provenance(source_id: str = "test-id", name: str = "test") -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id=source_id,
        source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def _make_profile(
    name: str = "UDP-jdoe",
    lines: list | None = None,
    sd_count: int = 0,
    blf_count: int = 0,
) -> MigrationObject:
    return MigrationObject(
        canonical_id=f"device_profile:{name}",
        provenance=_provenance(source_id=f"uuid-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "profile_name": name,
            "model": "Cisco 8865",
            "protocol": "SIP",
            "device_pool_name": "DP-HQ",
            "lines": lines or [{"dn_pattern": "1001", "partition": "PT-Internal", "index": "1"}],
            "speed_dial_count": sd_count,
            "blf_count": blf_count,
        },
    )


def _make_user(userid: str = "jdoe") -> MigrationObject:
    return MigrationObject(
        canonical_id=f"user:{userid}",
        provenance=_provenance(source_id=f"uuid-user-{userid}", name=userid),
        status=MigrationStatus.NORMALIZED,
    )


class TestDeviceProfileMapperBasic:
    def test_single_line_profile_no_decision(self):
        store = MigrationStore(":memory:")
        store.upsert_object(_make_user())
        store.upsert_object(_make_profile())

        mapper = DeviceProfileMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        assert len(result.decisions) == 0

    def test_profile_creates_canonical(self):
        store = MigrationStore(":memory:")
        store.upsert_object(_make_user())
        store.upsert_object(_make_profile())

        mapper = DeviceProfileMapper()
        mapper.map(store)

        dp = store.get_object("device_profile:UDP-jdoe")
        assert dp is not None
        assert dp["profile_name"] == "UDP-jdoe"
        assert dp["user_canonical_id"] == "user:jdoe"

    def test_user_cross_ref_created(self):
        store = MigrationStore(":memory:")
        store.upsert_object(_make_user())
        store.upsert_object(_make_profile())

        mapper = DeviceProfileMapper()
        mapper.map(store)

        refs = store.find_cross_refs("user:jdoe", "user_has_device_profile")
        assert len(refs) == 1


class TestDeviceProfileMapperFeatureLoss:
    def test_multi_line_produces_feature_approximation(self):
        lines = [
            {"dn_pattern": "1001", "partition": "PT-Internal", "index": "1"},
            {"dn_pattern": "1002", "partition": "PT-Internal", "index": "2"},
        ]
        store = MigrationStore(":memory:")
        store.upsert_object(_make_user())
        store.upsert_object(_make_profile(lines=lines))

        mapper = DeviceProfileMapper()
        result = mapper.map(store)

        assert len(result.decisions) == 1
        assert result.decisions[0].type.value == "FEATURE_APPROXIMATION"

    def test_speed_dials_produce_decision(self):
        store = MigrationStore(":memory:")
        store.upsert_object(_make_user())
        store.upsert_object(_make_profile(sd_count=5))

        mapper = DeviceProfileMapper()
        result = mapper.map(store)

        assert len(result.decisions) == 1
        assert result.decisions[0].type.value == "FEATURE_APPROXIMATION"

    def test_blf_produces_decision(self):
        store = MigrationStore(":memory:")
        store.upsert_object(_make_user())
        store.upsert_object(_make_profile(blf_count=3))

        mapper = DeviceProfileMapper()
        result = mapper.map(store)

        assert len(result.decisions) == 1


class TestDeviceProfileMapperOwnerResolution:
    def test_udp_prefix_resolves_user(self):
        store = MigrationStore(":memory:")
        store.upsert_object(_make_user("jdoe"))
        store.upsert_object(_make_profile("UDP-jdoe"))

        mapper = DeviceProfileMapper()
        mapper.map(store)

        dp = store.get_object("device_profile:UDP-jdoe")
        assert dp["user_canonical_id"] == "user:jdoe"

    def test_no_matching_user(self):
        store = MigrationStore(":memory:")
        store.upsert_object(_make_profile("UDP-unknown"))

        mapper = DeviceProfileMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        dp = store.get_object("device_profile:UDP-unknown")
        assert dp["user_canonical_id"] is None


class TestCanonicalDeviceProfileFields:
    """Verify new hoteling fields exist with correct defaults."""

    def test_hoteling_fields_default(self):
        from wxcli.migration.models import CanonicalDeviceProfile
        dp = CanonicalDeviceProfile(
            canonical_id="device_profile:UDP-jdoe",
            provenance=_provenance(),
        )
        assert dp.hoteling_guest_enabled is False
        assert dp.host_device_canonical_ids == []
        assert dp.auto_logout_minutes == 0
        assert dp.location_canonical_id is None


class TestDeviceProfileMapperHoteling:
    """Verify hoteling execution fields set by the mapper."""

    def test_hoteling_guest_enabled_when_user_found(self):
        """When a user is resolved for the profile, hoteling_guest_enabled = True."""
        store = MigrationStore(":memory:")
        store.upsert_object(_make_user("jdoe"))
        store.upsert_object(_make_profile("UDP-jdoe"))

        mapper = DeviceProfileMapper()
        mapper.map(store)

        dp = store.get_object("device_profile:UDP-jdoe")
        assert dp is not None
        assert dp["hoteling_guest_enabled"] is True

    def test_hoteling_guest_disabled_when_no_user(self):
        """When no user is found for the profile, hoteling_guest_enabled = False."""
        store = MigrationStore(":memory:")
        store.upsert_object(_make_profile("UDP-unknown"))

        mapper = DeviceProfileMapper()
        mapper.map(store)

        dp = store.get_object("device_profile:UDP-unknown")
        assert dp is not None
        assert dp["hoteling_guest_enabled"] is False

    def test_location_resolved_from_device_pool_crossref(self):
        """Location is resolved via device_pool_to_location cross-ref."""
        store = MigrationStore(":memory:")
        store.upsert_object(_make_user("jdoe"))
        store.upsert_object(_make_profile("UDP-jdoe"))
        # Seed the objects so FK constraints pass on cross_refs
        store.upsert_object(MigrationObject(
            canonical_id="device_pool:DP-HQ",
            provenance=_provenance(source_id="dp-hq", name="DP-HQ"),
            status=MigrationStatus.NORMALIZED,
        ))
        store.upsert_object(MigrationObject(
            canonical_id="location:HQ",
            provenance=_provenance(source_id="loc-hq", name="HQ"),
            status=MigrationStatus.NORMALIZED,
        ))
        # Seed the device_pool_to_location cross-ref (written by LocationMapper)
        store.add_cross_ref("device_pool:DP-HQ", "location:HQ", "device_pool_to_location")

        mapper = DeviceProfileMapper()
        mapper.map(store)

        dp = store.get_object("device_profile:UDP-jdoe")
        assert dp is not None
        assert dp["location_canonical_id"] == "location:HQ"

    def test_location_none_when_no_crossref(self):
        """Location stays None when no device_pool_to_location cross-ref exists."""
        store = MigrationStore(":memory:")
        store.upsert_object(_make_user("jdoe"))
        store.upsert_object(_make_profile("UDP-jdoe"))
        # No cross-ref seeded

        mapper = DeviceProfileMapper()
        mapper.map(store)

        dp = store.get_object("device_profile:UDP-jdoe")
        assert dp is not None
        assert dp["location_canonical_id"] is None

    def test_hoteling_location_object_created(self):
        """A hoteling_location MigrationObject is created for the resolved location."""
        store = MigrationStore(":memory:")
        store.upsert_object(_make_user("jdoe"))
        store.upsert_object(_make_profile("UDP-jdoe"))
        store.upsert_object(MigrationObject(
            canonical_id="device_pool:DP-HQ",
            provenance=_provenance(source_id="dp-hq", name="DP-HQ"),
            status=MigrationStatus.NORMALIZED,
        ))
        store.upsert_object(MigrationObject(
            canonical_id="location:HQ",
            provenance=_provenance(source_id="loc-hq", name="HQ"),
            status=MigrationStatus.NORMALIZED,
        ))
        store.add_cross_ref("device_pool:DP-HQ", "location:HQ", "device_pool_to_location")

        mapper = DeviceProfileMapper()
        result = mapper.map(store)

        loc_obj = store.get_object("hoteling_location:location:HQ")
        assert loc_obj is not None
        assert loc_obj["status"] == "analyzed"
        pre = loc_obj["pre_migration_state"]
        assert pre["location_canonical_id"] == "location:HQ"
        assert pre["em_profile_count"] == 1

    def test_hoteling_location_deduped_across_profiles(self):
        """Two profiles in the same location produce one hoteling_location with count=2."""
        store = MigrationStore(":memory:")
        store.upsert_object(_make_user("jdoe"))
        store.upsert_object(_make_user("asmith"))
        store.upsert_object(_make_profile("UDP-jdoe"))
        # Second profile also in DP-HQ (the default)
        store.upsert_object(_make_profile("UDP-asmith"))
        store.upsert_object(MigrationObject(
            canonical_id="device_pool:DP-HQ",
            provenance=_provenance(source_id="dp-hq", name="DP-HQ"),
            status=MigrationStatus.NORMALIZED,
        ))
        store.upsert_object(MigrationObject(
            canonical_id="location:HQ",
            provenance=_provenance(source_id="loc-hq", name="HQ"),
            status=MigrationStatus.NORMALIZED,
        ))
        store.add_cross_ref("device_pool:DP-HQ", "location:HQ", "device_pool_to_location")

        mapper = DeviceProfileMapper()
        result = mapper.map(store)

        loc_obj = store.get_object("hoteling_location:location:HQ")
        assert loc_obj is not None
        pre = loc_obj["pre_migration_state"]
        assert pre["em_profile_count"] == 2

    def test_em_classification_in_decision_context(self):
        """Decision context includes 'classification': 'EXTENSION_MOBILITY'."""
        lines = [
            {"dn_pattern": "1001", "partition": "PT-Internal", "index": "1"},
            {"dn_pattern": "1002", "partition": "PT-Internal", "index": "2"},
        ]
        store = MigrationStore(":memory:")
        store.upsert_object(_make_user("jdoe"))
        store.upsert_object(_make_profile("UDP-jdoe", lines=lines))

        mapper = DeviceProfileMapper()
        result = mapper.map(store)

        assert len(result.decisions) == 1
        ctx = result.decisions[0].context
        assert ctx["classification"] == "EXTENSION_MOBILITY"
