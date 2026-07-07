"""Tests for location_mapper: CUCM Device Pools -> Webex Calling Locations.

Uses real :memory: SQLite store, no mocks.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from wxcli.migration.models import (
    CanonicalLocation,
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.location_mapper import LocationMapper


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


def _device_pool(name: str = "HQ-Phones") -> MigrationObject:
    return MigrationObject(
        canonical_id=f"device_pool:{name}",
        provenance=_provenance(source_id=f"uuid-dp-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"device_pool_name": name},
    )


def _datetime_group(
    name: str = "US-Eastern", tz: str = "America/New_York"
) -> MigrationObject:
    return MigrationObject(
        canonical_id=f"dtg:{name}",
        provenance=_provenance(source_id=f"uuid-dtg-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"datetime_group_name": name, "timezone": tz},
    )


def _cucm_location(
    name: str = "HQ",
    address1: str = "123 Main St",
    city: str = "New York",
    state: str = "NY",
    postal_code: str = "10001",
    country: str = "US",
) -> MigrationObject:
    return MigrationObject(
        canonical_id=f"cucm_location:{name}",
        provenance=_provenance(source_id=f"uuid-loc-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "address1": address1,
            "city": city,
            "state": state,
            "postal_code": postal_code,
            "country": country,
        },
    )


def _make_store() -> MigrationStore:
    return MigrationStore(":memory:")


# ---------------------------------------------------------------------------
# Tests — happy path
# ---------------------------------------------------------------------------


class TestLocationMapperHappyPath:
    """Device pool with datetime group and CUCM location -> CanonicalLocation."""

    def test_single_device_pool_produces_one_location(self):
        store = _make_store()
        dp = _device_pool("HQ-Phones")
        dtg = _datetime_group("US-Eastern", "America/New_York")
        loc = _cucm_location("HQ", city="New York")

        store.upsert_object(dp)
        store.upsert_object(dtg)
        store.upsert_object(loc)
        store.add_cross_ref(dp.canonical_id, dtg.canonical_id, "device_pool_has_datetime_group")
        store.add_cross_ref(dp.canonical_id, loc.canonical_id, "device_pool_at_cucm_location")

        mapper = LocationMapper(
            default_language="en_us",
            default_country="US",
            outside_dial_digit="9",
        )
        result = mapper.map(store)

        assert result.objects_created == 1
        assert result.decisions == []

        # Verify the created location object
        locations = store.get_objects("location")
        assert len(locations) == 1
        location_data = locations[0]
        assert location_data["name"] == "HQ-Phones"
        assert location_data["time_zone"] == "America/New_York"
        assert location_data["announcement_language"] == "en_us"
        assert location_data["calling_enabled"] is True
        assert location_data["address"]["city"] == "New York"
        assert location_data["address"]["country"] == "US"

    def test_device_pool_to_location_cross_ref_created(self):
        store = _make_store()
        dp = _device_pool("HQ-Phones")
        dtg = _datetime_group("US-Eastern", "America/New_York")
        loc = _cucm_location("HQ")

        store.upsert_object(dp)
        store.upsert_object(dtg)
        store.upsert_object(loc)
        store.add_cross_ref(dp.canonical_id, dtg.canonical_id, "device_pool_has_datetime_group")
        store.add_cross_ref(dp.canonical_id, loc.canonical_id, "device_pool_at_cucm_location")

        mapper = LocationMapper()
        mapper.map(store)

        # Verify device_pool_to_location cross-ref was created
        targets = store.find_cross_refs(dp.canonical_id, "device_pool_to_location")
        assert len(targets) == 1
        assert targets[0].startswith("location:")

    def test_announcement_language_lowercase(self):
        store = _make_store()
        dp = _device_pool("HQ-Phones")
        dtg = _datetime_group("US-Eastern", "America/New_York")
        loc = _cucm_location("HQ")

        store.upsert_object(dp)
        store.upsert_object(dtg)
        store.upsert_object(loc)
        store.add_cross_ref(dp.canonical_id, dtg.canonical_id, "device_pool_has_datetime_group")
        store.add_cross_ref(dp.canonical_id, loc.canonical_id, "device_pool_at_cucm_location")

        mapper = LocationMapper(default_language="en_US")
        mapper.map(store)

        locations = store.get_objects("location")
        assert locations[0]["announcement_language"] == "en_us"


# ---------------------------------------------------------------------------
# Tests — consolidation
# ---------------------------------------------------------------------------


class TestLocationMapperConsolidation:
    """Multiple device pools sharing the same CUCM Location -> one Webex location."""

    def test_two_pools_same_cucm_location_produce_one_location(self):
        store = _make_store()
        dp1 = _device_pool("HQ-Phones")
        dp2 = _device_pool("HQ-Softphones")
        dtg = _datetime_group("US-Eastern", "America/New_York")
        loc = _cucm_location("HQ", city="New York")

        store.upsert_object(dp1)
        store.upsert_object(dp2)
        store.upsert_object(dtg)
        store.upsert_object(loc)

        # Both pools point to the same CUCM Location
        store.add_cross_ref(dp1.canonical_id, dtg.canonical_id, "device_pool_has_datetime_group")
        store.add_cross_ref(dp2.canonical_id, dtg.canonical_id, "device_pool_has_datetime_group")
        store.add_cross_ref(dp1.canonical_id, loc.canonical_id, "device_pool_at_cucm_location")
        store.add_cross_ref(dp2.canonical_id, loc.canonical_id, "device_pool_at_cucm_location")

        mapper = LocationMapper()
        result = mapper.map(store)

        # Exactly one location, not two
        assert result.objects_created == 1
        locations = store.get_objects("location")
        assert len(locations) == 1

        # Both pool names recorded
        assert "HQ-Phones" in locations[0]["cucm_device_pool_names"]
        assert "HQ-Softphones" in locations[0]["cucm_device_pool_names"]

    def test_both_pools_get_cross_refs(self):
        store = _make_store()
        dp1 = _device_pool("HQ-Phones")
        dp2 = _device_pool("HQ-Softphones")
        dtg = _datetime_group("US-Eastern", "America/New_York")
        loc = _cucm_location("HQ")

        store.upsert_object(dp1)
        store.upsert_object(dp2)
        store.upsert_object(dtg)
        store.upsert_object(loc)

        store.add_cross_ref(dp1.canonical_id, dtg.canonical_id, "device_pool_has_datetime_group")
        store.add_cross_ref(dp2.canonical_id, dtg.canonical_id, "device_pool_has_datetime_group")
        store.add_cross_ref(dp1.canonical_id, loc.canonical_id, "device_pool_at_cucm_location")
        store.add_cross_ref(dp2.canonical_id, loc.canonical_id, "device_pool_at_cucm_location")

        mapper = LocationMapper()
        mapper.map(store)

        # Both pools have device_pool_to_location cross-refs
        refs1 = store.find_cross_refs(dp1.canonical_id, "device_pool_to_location")
        refs2 = store.find_cross_refs(dp2.canonical_id, "device_pool_to_location")
        assert len(refs1) == 1
        assert len(refs2) == 1
        # Both point to the same location
        assert refs1[0] == refs2[0]


# ---------------------------------------------------------------------------
# Tests — edge cases and decisions
# ---------------------------------------------------------------------------


class TestLocationMapperEdgeCases:
    """Edge cases: missing CUCM location, name truncation."""

    def test_orphan_pool_produces_location_ambiguous_decision(self):
        store = _make_store()
        dp = _device_pool("Orphan-DP")
        store.upsert_object(dp)
        # No device_pool_at_cucm_location cross-ref

        mapper = LocationMapper()
        result = mapper.map(store)

        assert result.objects_created == 0
        assert len(result.decisions) == 1
        decision = result.decisions[0]
        assert decision.type.value == "LOCATION_AMBIGUOUS"
        assert decision.severity == "HIGH"
        assert "Orphan-DP" in decision.summary

        # Decision was saved to store
        stored_decisions = store.get_all_decisions()
        assert len(stored_decisions) == 1
        assert stored_decisions[0]["type"] == "LOCATION_AMBIGUOUS"

    def test_location_name_truncated_at_80_chars(self):
        store = _make_store()
        long_name = "A" * 100
        dp = _device_pool(long_name)
        dtg = _datetime_group("US-Eastern", "America/New_York")
        loc = _cucm_location("HQ")

        store.upsert_object(dp)
        store.upsert_object(dtg)
        store.upsert_object(loc)
        store.add_cross_ref(dp.canonical_id, dtg.canonical_id, "device_pool_has_datetime_group")
        store.add_cross_ref(dp.canonical_id, loc.canonical_id, "device_pool_at_cucm_location")

        mapper = LocationMapper()
        result = mapper.map(store)

        locations = store.get_objects("location")
        assert len(locations[0]["name"]) == 80

        # Warning should be recorded
        assert any("truncated" in w.lower() for w in locations[0]["warnings"])

    def test_address_populated_from_cucm_location(self):
        store = _make_store()
        dp = _device_pool("Branch-Phones")
        dtg = _datetime_group("US-Central", "America/Chicago")
        loc = _cucm_location(
            "Branch",
            address1="456 Oak Ave",
            city="Chicago",
            state="IL",
            postal_code="60601",
            country="US",
        )

        store.upsert_object(dp)
        store.upsert_object(dtg)
        store.upsert_object(loc)
        store.add_cross_ref(dp.canonical_id, dtg.canonical_id, "device_pool_has_datetime_group")
        store.add_cross_ref(dp.canonical_id, loc.canonical_id, "device_pool_at_cucm_location")

        mapper = LocationMapper()
        mapper.map(store)

        locations = store.get_objects("location")
        addr = locations[0]["address"]
        assert addr["address1"] == "456 Oak Ave"
        assert addr["city"] == "Chicago"
        assert addr["state"] == "IL"
        assert addr["postal_code"] == "60601"
        assert addr["country"] == "US"

    def test_status_set_to_analyzed(self):
        store = _make_store()
        dp = _device_pool("HQ-Phones")
        dtg = _datetime_group("US-Eastern", "America/New_York")
        loc = _cucm_location("HQ")

        store.upsert_object(dp)
        store.upsert_object(dtg)
        store.upsert_object(loc)
        store.add_cross_ref(dp.canonical_id, dtg.canonical_id, "device_pool_has_datetime_group")
        store.add_cross_ref(dp.canonical_id, loc.canonical_id, "device_pool_at_cucm_location")

        mapper = LocationMapper()
        mapper.map(store)

        locations = store.get_objects("location")
        assert locations[0]["status"] == "analyzed"

    def test_outside_dial_digit_int_coerced_to_str(self):
        """Config may supply outside_dial_digit as int (JSON round-trip loses str type).

        Regression test: LocationMapper must coerce to str before passing to
        CanonicalLocation, which expects str | None.
        """
        store = _make_store()
        dp = _device_pool("HQ-Phones")
        dtg = _datetime_group("US-Eastern", "America/New_York")
        loc = _cucm_location("HQ")

        store.upsert_object(dp)
        store.upsert_object(dtg)
        store.upsert_object(loc)
        store.add_cross_ref(dp.canonical_id, dtg.canonical_id, "device_pool_has_datetime_group")
        store.add_cross_ref(dp.canonical_id, loc.canonical_id, "device_pool_at_cucm_location")

        # Pass outside_dial_digit as int (simulates config from JSON)
        mapper = LocationMapper(outside_dial_digit=9)
        result = mapper.map(store)

        assert result.objects_created == 1
        locations = store.get_objects("location")
        assert locations[0]["outside_dial_digit"] == "9"

    def test_idempotent_rerun(self):
        """Running the mapper twice produces the same output (idempotent)."""
        store = _make_store()
        dp = _device_pool("HQ-Phones")
        dtg = _datetime_group("US-Eastern", "America/New_York")
        loc = _cucm_location("HQ")

        store.upsert_object(dp)
        store.upsert_object(dtg)
        store.upsert_object(loc)
        store.add_cross_ref(dp.canonical_id, dtg.canonical_id, "device_pool_has_datetime_group")
        store.add_cross_ref(dp.canonical_id, loc.canonical_id, "device_pool_at_cucm_location")

        mapper = LocationMapper()
        result1 = mapper.map(store)
        result2 = mapper.map(store)

        # Same count (upsert means no duplication)
        locations = store.get_objects("location")
        assert len(locations) == 1
