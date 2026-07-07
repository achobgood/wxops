"""Tests for device_mapper: CUCM Phones -> Webex Calling Devices.

Uses real :memory: SQLite store, no mocks.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from wxcli.migration.models import (
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.device_mapper import DeviceMapper


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _provenance(source_id: str = "test-id", name: str = "test") -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id=source_id,
        source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def _phone(
    name: str = "SEP001122AABBCC",
    model: str = "Cisco 6841",
    protocol: str = "SIP",
    is_common_area: bool = False,
    description: str | None = None,
    line_appearances: list | None = None,
    cucm_device_pool: str | None = None,
    cucm_owner_user: str | None = None,
) -> MigrationObject:
    state: dict = {
        "name": name,
        "model": model,
        "protocol": protocol,
        "is_common_area": is_common_area,
    }
    if description:
        state["description"] = description
    if line_appearances:
        state["line_appearances"] = line_appearances
    if cucm_device_pool:
        state["cucm_device_pool"] = cucm_device_pool
    if cucm_owner_user:
        state["cucm_owner_user"] = cucm_owner_user

    return MigrationObject(
        canonical_id=f"phone:{name}",
        provenance=_provenance(source_id=f"uuid-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=state,
    )


def _device_pool(name: str = "HQ-Phones") -> MigrationObject:
    return MigrationObject(
        canonical_id=f"device_pool:{name}",
        provenance=_provenance(source_id=f"uuid-dp-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"device_pool_name": name},
    )


def _make_store() -> MigrationStore:
    return MigrationStore(":memory:")


def _seed_location_chain(store: MigrationStore, dp_name: str = "HQ-Phones") -> str:
    """Seed a device pool and location, return the location canonical_id."""
    dp = _device_pool(dp_name)
    store.upsert_object(dp)

    # Create a minimal location object so device_pool_to_location cross-ref can work
    from wxcli.migration.models import CanonicalLocation, LocationAddress

    loc = CanonicalLocation(
        canonical_id=f"location:{dp_name}",
        provenance=_provenance(source_id=f"uuid-loc-{dp_name}", name=dp_name),
        status=MigrationStatus.ANALYZED,
        name=dp_name,
        address=LocationAddress(country="US"),
    )
    store.upsert_object(loc)
    store.add_cross_ref(dp.canonical_id, loc.canonical_id, "device_pool_to_location")
    return loc.canonical_id


# ---------------------------------------------------------------------------
# Tests — happy path: three-tier classification
# ---------------------------------------------------------------------------


class TestDeviceMapperCompatibility:
    """Three-tier model compatibility classification."""

    def test_native_mpp_no_decision(self):
        """Cisco 6841 is native MPP -> no decision generated."""
        store = _make_store()
        loc_id = _seed_location_chain(store)
        phone = _phone("SEP001122AABBCC", model="Cisco 6841")
        store.upsert_object(phone)
        store.add_cross_ref(phone.canonical_id, "device_pool:HQ-Phones", "device_in_pool")

        mapper = DeviceMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        assert result.decisions == []

        devices = store.get_objects("device")
        assert len(devices) == 1
        assert devices[0]["compatibility_tier"] == "native_mpp"
        assert devices[0]["mac"] == "001122AABBCC"

    def test_convertible_produces_no_decision(self):
        """Cisco 7841 is firmware convertible -> no decision; classification only."""
        store = _make_store()
        _seed_location_chain(store)
        phone = _phone("SEP112233445566", model="Cisco 7841")
        store.upsert_object(phone)
        store.add_cross_ref(phone.canonical_id, "device_pool:HQ-Phones", "device_in_pool")

        mapper = DeviceMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        assert result.decisions == []

        devices = store.get_objects("device")
        assert devices[0]["compatibility_tier"] == "convertible"

    def test_incompatible_produces_device_incompatible_decision(self):
        """Cisco 7911 is incompatible -> DEVICE_INCOMPATIBLE decision."""
        store = _make_store()
        _seed_location_chain(store)
        phone = _phone("SEP778899AABBCC", model="Cisco 7911")
        store.upsert_object(phone)
        store.add_cross_ref(phone.canonical_id, "device_pool:HQ-Phones", "device_in_pool")

        mapper = DeviceMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        assert len(result.decisions) == 1
        assert result.decisions[0].type.value == "DEVICE_INCOMPATIBLE"
        assert result.decisions[0].severity == "HIGH"

        devices = store.get_objects("device")
        assert devices[0]["compatibility_tier"] == "incompatible"

    def test_dect_handset_no_decision(self):
        """Cisco 6825 is DECT -> no decision generated, tier is 'dect'."""
        store = _make_store()
        _seed_location_chain(store)
        phone = _phone("SEP998877665544", model="Cisco 6825")
        store.upsert_object(phone)
        store.add_cross_ref(phone.canonical_id, "device_pool:HQ-Phones", "device_in_pool")

        mapper = DeviceMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        assert result.decisions == []
        devices = store.get_objects("device")
        dect_dev = [d for d in devices if d.get("compatibility_tier") == "dect"]
        assert len(dect_dev) == 1

    def test_dect_6823_no_decision(self):
        """Cisco 6823 is DECT -> no decision generated."""
        store = _make_store()
        _seed_location_chain(store)
        phone = _phone("SEP112233445566", model="Cisco 6823")
        store.upsert_object(phone)
        store.add_cross_ref(phone.canonical_id, "device_pool:HQ-Phones", "device_in_pool")

        mapper = DeviceMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        assert result.decisions == []
        devices = store.get_objects("device")
        dect_dev = [d for d in devices if d.get("compatibility_tier") == "dect"]
        assert len(dect_dev) == 1


# ---------------------------------------------------------------------------
# Tests — MAC extraction
# ---------------------------------------------------------------------------


class TestDeviceMapperMacExtraction:
    """MAC address extracted by stripping SEP prefix."""

    def test_sep_prefix_stripped(self):
        store = _make_store()
        _seed_location_chain(store)
        phone = _phone("SEP001122AABBCC", model="Cisco 6841")
        store.upsert_object(phone)
        store.add_cross_ref(phone.canonical_id, "device_pool:HQ-Phones", "device_in_pool")

        mapper = DeviceMapper()
        mapper.map(store)

        devices = store.get_objects("device")
        assert devices[0]["mac"] == "001122AABBCC"

    def test_lowercase_sep_still_works(self):
        store = _make_store()
        _seed_location_chain(store)
        # The name stored in pre_migration_state matters, not the canonical_id prefix
        phone = _phone("SEPaabbccddeeff", model="Cisco 6841")
        store.upsert_object(phone)
        store.add_cross_ref(phone.canonical_id, "device_pool:HQ-Phones", "device_in_pool")

        mapper = DeviceMapper()
        mapper.map(store)

        devices = store.get_objects("device")
        assert devices[0]["mac"] == "AABBCCDDEEFF"


# ---------------------------------------------------------------------------
# Tests — cross-ref resolution
# ---------------------------------------------------------------------------


class TestDeviceMapperCrossRefs:
    """Location and owner resolution via cross-refs."""

    def test_location_resolved_via_cross_ref_chain(self):
        store = _make_store()
        loc_id = _seed_location_chain(store)
        phone = _phone("SEP001122AABBCC", model="Cisco 6841")
        store.upsert_object(phone)
        # Cross-refs use device:{name} — mapper derives device_id from phone name
        device_id = "device:SEP001122AABBCC"
        store.upsert_object(MigrationObject(
            canonical_id=device_id, provenance=_provenance("d", "d"),
            status=MigrationStatus.NORMALIZED,
        ))
        store.add_cross_ref(device_id, "device_pool:HQ-Phones", "device_in_pool")

        mapper = DeviceMapper()
        mapper.map(store)

        devices = store.get_objects("device")
        matched = [d for d in devices if d.get("canonical_id") == device_id]
        assert matched[0]["location_canonical_id"] == loc_id

    def test_owner_resolved_via_cross_ref(self):
        store = _make_store()
        _seed_location_chain(store)
        phone = _phone("SEP001122AABBCC", model="Cisco 6841")
        store.upsert_object(phone)
        device_id = "device:SEP001122AABBCC"
        store.upsert_object(MigrationObject(
            canonical_id=device_id, provenance=_provenance("d", "d"),
            status=MigrationStatus.NORMALIZED,
        ))
        store.add_cross_ref(device_id, "device_pool:HQ-Phones", "device_in_pool")

        user = MigrationObject(
            canonical_id="user:jdoe",
            provenance=_provenance("uuid-user-jdoe", "jdoe"),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={"userid": "jdoe"},
        )
        store.upsert_object(user)
        store.add_cross_ref(device_id, user.canonical_id, "device_owned_by_user")

        mapper = DeviceMapper()
        mapper.map(store)

        devices = store.get_objects("device")
        assert devices[0]["owner_canonical_id"] == "user:jdoe"


# ---------------------------------------------------------------------------
# Tests — edge cases
# ---------------------------------------------------------------------------


class TestDeviceMapperEdgeCases:
    """Edge cases: common-area skip, SCCP protocol, no model."""

    def test_common_area_phones_skipped(self):
        """Common-area phones are NOT processed by device_mapper."""
        store = _make_store()
        _seed_location_chain(store)
        phone = _phone("SEP001122AABBCC", model="Cisco 6841", is_common_area=True)
        store.upsert_object(phone)
        store.add_cross_ref(phone.canonical_id, "device_pool:HQ-Phones", "device_in_pool")

        mapper = DeviceMapper()
        result = mapper.map(store)

        assert result.objects_created == 0
        assert result.decisions == []
        assert store.get_objects("device") == []

    def test_sccp_protocol_classified_as_incompatible(self):
        """SCCP-only phones are classified as Incompatible regardless of model."""
        store = _make_store()
        _seed_location_chain(store)
        # Cisco 6841 is normally native MPP, but SCCP makes it incompatible
        phone = _phone("SEP001122AABBCC", model="Cisco 6841", protocol="SCCP")
        store.upsert_object(phone)
        store.add_cross_ref(phone.canonical_id, "device_pool:HQ-Phones", "device_in_pool")

        mapper = DeviceMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        assert len(result.decisions) == 1
        assert result.decisions[0].type.value == "DEVICE_INCOMPATIBLE"

        devices = store.get_objects("device")
        assert devices[0]["compatibility_tier"] == "incompatible"
        assert devices[0]["cucm_protocol"] == "SCCP"

    def test_cucm_protocol_stored(self):
        """cucm_protocol field is stored on the canonical device."""
        store = _make_store()
        _seed_location_chain(store)
        phone = _phone("SEP001122AABBCC", model="Cisco 6841", protocol="SIP")
        store.upsert_object(phone)
        store.add_cross_ref(phone.canonical_id, "device_pool:HQ-Phones", "device_in_pool")

        mapper = DeviceMapper()
        mapper.map(store)

        devices = store.get_objects("device")
        assert devices[0]["cucm_protocol"] == "SIP"

    def test_status_set_to_analyzed(self):
        store = _make_store()
        _seed_location_chain(store)
        phone = _phone("SEP001122AABBCC", model="Cisco 6841")
        store.upsert_object(phone)
        store.add_cross_ref(phone.canonical_id, "device_pool:HQ-Phones", "device_in_pool")

        mapper = DeviceMapper()
        mapper.map(store)

        devices = store.get_objects("device")
        assert devices[0]["status"] == "analyzed"

    def test_multiple_phones_mixed_tiers(self):
        """Process three phones with different compatibility tiers in one run."""
        store = _make_store()
        _seed_location_chain(store)

        phones = [
            _phone("SEP111111111111", model="Cisco 6841"),   # native
            _phone("SEP222222222222", model="Cisco 7841"),   # convertible
            _phone("SEP333333333333", model="Cisco 7911"),   # incompatible
        ]
        for p in phones:
            store.upsert_object(p)
            store.add_cross_ref(p.canonical_id, "device_pool:HQ-Phones", "device_in_pool")

        mapper = DeviceMapper()
        result = mapper.map(store)

        assert result.objects_created == 3
        # Only incompatible produces a decision; convertible is classification-only
        assert len(result.decisions) == 1

        decision_types = {d.type.value for d in result.decisions}
        assert "DEVICE_INCOMPATIBLE" in decision_types
