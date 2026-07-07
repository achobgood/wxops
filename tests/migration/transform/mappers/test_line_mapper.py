"""Tests for line_mapper: CUCM Directory Numbers -> Webex Phone Numbers + Extensions.

Uses real :memory: SQLite store, no mocks.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from wxcli.migration.models import (
    CanonicalLine,
    CanonicalLocation,
    LineClassification,
    LocationAddress,
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.line_mapper import LineMapper


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


def _dn(pattern: str = "1001", partition: str = "Internal-PT") -> MigrationObject:
    return MigrationObject(
        canonical_id=f"dn:{pattern}:{partition}",
        provenance=_provenance(source_id=f"uuid-dn-{pattern}", name=pattern),
        status=MigrationStatus.NORMALIZED,
    )


def _device(
    name: str = "SEP001122AABBCC",
    line_appearances: list | None = None,
) -> MigrationObject:
    state = {}
    if line_appearances is not None:
        state["line_appearances"] = line_appearances
    return MigrationObject(
        canonical_id=f"device:{name}",
        provenance=_provenance(source_id=f"uuid-dev-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=state if state else None,
    )


def _device_pool(name: str = "HQ-Phones") -> MigrationObject:
    return MigrationObject(
        canonical_id=f"device_pool:{name}",
        provenance=_provenance(source_id=f"uuid-dp-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
    )


def _location(name: str = "HQ", country: str = "US") -> CanonicalLocation:
    return CanonicalLocation(
        canonical_id=f"location:{name}",
        provenance=_provenance(source_id=f"uuid-loc-{name}", name=name),
        status=MigrationStatus.ANALYZED,
        name=name,
        address=LocationAddress(country=country),
    )


def _make_store() -> MigrationStore:
    return MigrationStore(":memory:")


def _seed_dn_with_device_chain(
    store: MigrationStore,
    dn_pattern: str = "1001",
    dn_partition: str = "Internal-PT",
    device_name: str = "SEP001122AABBCC",
    dp_name: str = "HQ-Phones",
    loc_name: str = "HQ",
    country: str = "US",
    line_appearances: list | None = None,
) -> str:
    """Seed the store with a DN -> device -> pool -> location chain.

    Returns the DN canonical_id.
    """
    dn = _dn(dn_pattern, dn_partition)
    dev = _device(device_name, line_appearances=line_appearances)
    dp = _device_pool(dp_name)
    loc = _location(loc_name, country=country)

    store.upsert_object(dn)
    store.upsert_object(dev)
    store.upsert_object(dp)
    store.upsert_object(loc)

    store.add_cross_ref(dev.canonical_id, dn.canonical_id, "device_has_dn")
    store.add_cross_ref(dev.canonical_id, dp.canonical_id, "device_in_pool")
    store.add_cross_ref(dp.canonical_id, loc.canonical_id, "device_pool_to_location")

    return dn.canonical_id


# ---------------------------------------------------------------------------
# Tests — happy path
# ---------------------------------------------------------------------------


class TestLineMapperHappyPath:
    """Extension-only DNs and national-number DNs."""

    def test_extension_dn_produces_canonical_line(self):
        """Short DN '1001' at US location -> extension-only CanonicalLine."""
        store = _make_store()
        _seed_dn_with_device_chain(store, dn_pattern="1001")

        mapper = LineMapper(default_country_code="US")
        result = mapper.map(store)

        assert result.objects_created == 1
        assert result.decisions == []

        lines = store.get_objects("line")
        assert len(lines) == 1
        line = lines[0]
        assert line["extension"] == "1001"
        assert line["classification"] == "EXTENSION"
        assert line["e164"] is None
        assert line["shared"] is False
        assert line["cucm_pattern"] == "1001"
        assert line["status"] == "analyzed"

    def test_national_number_dn_produces_e164(self):
        """10-digit national number '2125551234' at US location -> E.164 '+12125551234'."""
        store = _make_store()
        _seed_dn_with_device_chain(store, dn_pattern="2125551234")

        mapper = LineMapper(default_country_code="US")
        result = mapper.map(store)

        assert result.objects_created == 1
        lines = store.get_objects("line")
        line = lines[0]
        assert line["e164"] == "+12125551234"
        assert line["classification"] == "NATIONAL"

    def test_country_code_resolved_from_location_chain(self):
        """Country code comes from the location's address, not the default."""
        store = _make_store()
        # Use a UK location and a UK-format national number
        _seed_dn_with_device_chain(
            store,
            dn_pattern="2071234567",  # London number
            country="GB",
        )

        mapper = LineMapper(default_country_code="US")  # default is US but location is GB
        result = mapper.map(store)

        lines = store.get_objects("line")
        assert lines[0]["e164"] == "+442071234567"
        assert lines[0]["classification"] == "NATIONAL"


# ---------------------------------------------------------------------------
# Tests — shared lines
# ---------------------------------------------------------------------------


class TestLineMapperSharedLines:
    """DN referenced by multiple devices -> shared=True."""

    def test_shared_dn_tagged_true(self):
        store = _make_store()
        dn = _dn("3001", "Internal-PT")
        dev1 = _device("SEP111111111111")
        dev2 = _device("SEP222222222222")
        dp = _device_pool("HQ-Phones")
        loc = _location("HQ")

        store.upsert_object(dn)
        store.upsert_object(dev1)
        store.upsert_object(dev2)
        store.upsert_object(dp)
        store.upsert_object(loc)

        # Both devices reference the same DN
        store.add_cross_ref(dev1.canonical_id, dn.canonical_id, "device_has_dn")
        store.add_cross_ref(dev2.canonical_id, dn.canonical_id, "device_has_dn")
        store.add_cross_ref(dev1.canonical_id, dp.canonical_id, "device_in_pool")
        store.add_cross_ref(dev2.canonical_id, dp.canonical_id, "device_in_pool")
        store.add_cross_ref(dp.canonical_id, loc.canonical_id, "device_pool_to_location")

        mapper = LineMapper()
        result = mapper.map(store)

        lines = store.get_objects("line")
        assert len(lines) == 1
        assert lines[0]["shared"] is True

    def test_single_device_dn_not_shared(self):
        store = _make_store()
        _seed_dn_with_device_chain(store, dn_pattern="4001")

        mapper = LineMapper()
        mapper.map(store)

        lines = store.get_objects("line")
        assert lines[0]["shared"] is False


# ---------------------------------------------------------------------------
# Tests — edge cases and decisions
# ---------------------------------------------------------------------------


class TestLineMapperEdgeCases:
    """Extension length validation, ambiguous DNs, precomputed e164_result."""

    def test_extension_too_short_produces_missing_data(self):
        """1-digit extension is outside Webex's 2-10 char limit."""
        store = _make_store()
        _seed_dn_with_device_chain(store, dn_pattern="5")

        mapper = LineMapper()
        result = mapper.map(store)

        # Should produce MISSING_DATA decision
        assert len(result.decisions) == 1
        d = result.decisions[0]
        assert d.type.value == "MISSING_DATA"
        assert "2-10 char" in d.summary.lower()

        # Line object should still be created
        assert result.objects_created == 1

    def test_ambiguous_dn_produces_dn_ambiguous_decision(self):
        """DN that can't be classified produces DN_AMBIGUOUS."""
        store = _make_store()
        # A pattern starting with * is not a normal DN
        _seed_dn_with_device_chain(store, dn_pattern="*97")

        mapper = LineMapper()
        result = mapper.map(store)

        assert len(result.decisions) == 1
        d = result.decisions[0]
        assert d.type.value == "DN_AMBIGUOUS"
        assert result.objects_created == 0  # AMBIGUOUS DNs are skipped

    def test_does_not_produce_extension_conflict(self):
        """line_mapper does NOT produce EXTENSION_CONFLICT (analyzer-owned)."""
        store = _make_store()
        # Two DNs with same pattern in different partitions
        _seed_dn_with_device_chain(
            store,
            dn_pattern="1001",
            dn_partition="PT-A",
            device_name="SEP111111111111",
        )
        # Second DN with same pattern, different partition
        dn2 = _dn("1001", "PT-B")
        dev2 = _device("SEP222222222222")
        store.upsert_object(dn2)
        store.upsert_object(dev2)
        store.add_cross_ref(dev2.canonical_id, dn2.canonical_id, "device_has_dn")
        store.add_cross_ref(dev2.canonical_id, "device_pool:HQ-Phones", "device_in_pool")

        mapper = LineMapper()
        result = mapper.map(store)

        for d in result.decisions:
            assert d.type.value != "EXTENSION_CONFLICT"

    def test_precomputed_e164_result_used_when_available(self):
        """When device line appearances have e164_result, use it instead of normalize_dn()."""
        store = _make_store()

        dn = _dn("5551234567", "Internal-PT")
        # Device with pre-computed e164_result in line appearances
        dev = _device(
            "SEP001122AABBCC",
            line_appearances=[
                {
                    "dn_canonical_id": "dn:5551234567:Internal-PT",
                    "e164_result": {
                        "e164": "+15551234567",
                        "extension": "5551234567",
                        "classification": "NATIONAL",
                    },
                }
            ],
        )
        dp = _device_pool("HQ-Phones")
        loc = _location("HQ")

        store.upsert_object(dn)
        store.upsert_object(dev)
        store.upsert_object(dp)
        store.upsert_object(loc)

        store.add_cross_ref(dev.canonical_id, dn.canonical_id, "device_has_dn")
        store.add_cross_ref(dev.canonical_id, dp.canonical_id, "device_in_pool")
        store.add_cross_ref(dp.canonical_id, loc.canonical_id, "device_pool_to_location")

        mapper = LineMapper(default_country_code="US")
        result = mapper.map(store)

        lines = store.get_objects("line")
        assert len(lines) == 1
        # Should use the precomputed result
        assert lines[0]["e164"] == "+15551234567"
        assert lines[0]["classification"] == "NATIONAL"

    def test_precomputed_e164_extension_result(self):
        """Pre-computed e164_result with EXTENSION classification."""
        store = _make_store()

        dn = _dn("2001", "Internal-PT")
        dev = _device(
            "SEP001122AABBCC",
            line_appearances=[
                {
                    "dn_canonical_id": "dn:2001:Internal-PT",
                    "e164_result": {
                        "e164": None,
                        "extension": "2001",
                        "classification": "EXTENSION",
                    },
                }
            ],
        )
        dp = _device_pool("HQ-Phones")
        loc = _location("HQ")

        store.upsert_object(dn)
        store.upsert_object(dev)
        store.upsert_object(dp)
        store.upsert_object(loc)

        store.add_cross_ref(dev.canonical_id, dn.canonical_id, "device_has_dn")
        store.add_cross_ref(dev.canonical_id, dp.canonical_id, "device_in_pool")
        store.add_cross_ref(dp.canonical_id, loc.canonical_id, "device_pool_to_location")

        mapper = LineMapper(default_country_code="US")
        result = mapper.map(store)

        lines = store.get_objects("line")
        assert lines[0]["extension"] == "2001"
        assert lines[0]["classification"] == "EXTENSION"
        assert lines[0]["e164"] is None

    def test_fallback_to_normalize_dn_when_no_precomputed(self):
        """When no precomputed e164_result, falls back to normalize_dn()."""
        store = _make_store()

        dn = _dn("3001", "Internal-PT")
        # Device without line_appearances in pre_migration_state
        dev = _device("SEP001122AABBCC")
        dp = _device_pool("HQ-Phones")
        loc = _location("HQ")

        store.upsert_object(dn)
        store.upsert_object(dev)
        store.upsert_object(dp)
        store.upsert_object(loc)

        store.add_cross_ref(dev.canonical_id, dn.canonical_id, "device_has_dn")
        store.add_cross_ref(dev.canonical_id, dp.canonical_id, "device_in_pool")
        store.add_cross_ref(dp.canonical_id, loc.canonical_id, "device_pool_to_location")

        mapper = LineMapper(default_country_code="US")
        result = mapper.map(store)

        lines = store.get_objects("line")
        assert len(lines) == 1
        # 3001 is a 4-digit number -> extension
        assert lines[0]["extension"] == "3001"
        assert lines[0]["classification"] == "EXTENSION"

    def test_partition_preserved_in_line(self):
        store = _make_store()
        _seed_dn_with_device_chain(store, dn_pattern="1001", dn_partition="Main-PT")

        mapper = LineMapper()
        mapper.map(store)

        lines = store.get_objects("line")
        assert lines[0]["route_partition_name"] == "Main-PT"

    def test_multiple_dns_produce_multiple_lines(self):
        store = _make_store()
        dn1 = _dn("1001", "PT-A")
        dn2 = _dn("2002", "PT-A")
        dev = _device("SEP001122AABBCC")
        dp = _device_pool("HQ-Phones")
        loc = _location("HQ")

        store.upsert_object(dn1)
        store.upsert_object(dn2)
        store.upsert_object(dev)
        store.upsert_object(dp)
        store.upsert_object(loc)

        store.add_cross_ref(dev.canonical_id, dn1.canonical_id, "device_has_dn")
        store.add_cross_ref(dev.canonical_id, dn2.canonical_id, "device_has_dn")
        store.add_cross_ref(dev.canonical_id, dp.canonical_id, "device_in_pool")
        store.add_cross_ref(dp.canonical_id, loc.canonical_id, "device_pool_to_location")

        mapper = LineMapper()
        result = mapper.map(store)

        assert result.objects_created == 2
        lines = store.get_objects("line")
        assert len(lines) == 2

    def test_device_get_object_returns_none_gracefully(self):
        """Line mapper handles devices where get_object returns incomplete data."""
        store = _make_store()
        dn = _dn("1001", "Internal-PT")
        # Device with no pre_migration_state at all
        dev = MigrationObject(
            canonical_id="device:SEPMISSING",
            provenance=_provenance(source_id="uuid-dev-missing", name="SEPMISSING"),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state=None,
        )
        dp = _device_pool("HQ-Phones")
        loc = _location("HQ")

        store.upsert_object(dn)
        store.upsert_object(dev)
        store.upsert_object(dp)
        store.upsert_object(loc)

        store.add_cross_ref(dev.canonical_id, dn.canonical_id, "device_has_dn")
        store.add_cross_ref(dev.canonical_id, dp.canonical_id, "device_in_pool")
        store.add_cross_ref(dp.canonical_id, loc.canonical_id, "device_pool_to_location")

        # Should not raise; falls back to normalize_dn()
        mapper = LineMapper()
        result = mapper.map(store)
        assert result.objects_created == 1
