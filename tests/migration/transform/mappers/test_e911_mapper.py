"""Tests for E911Mapper — CUCM ELIN/GeoLocation → E911 advisory."""

from __future__ import annotations
from datetime import datetime, timezone

from wxcli.migration.models import (
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.e911_mapper import E911Mapper


def _provenance(source_id: str = "test-id", name: str = "test") -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id=source_id,
        source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def _make_elin_group(name: str = "ELIN-HQ", numbers: list[str] | None = None) -> MigrationObject:
    return MigrationObject(
        canonical_id=f"elin_group:{name}",
        provenance=_provenance(source_id=f"uuid-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "name": name,
            "elin_numbers": numbers or ["+14155559911"],
        },
    )


def _make_geo_location(name: str = "GEO-US", country: str = "US") -> MigrationObject:
    return MigrationObject(
        canonical_id=f"geo_location:{name}",
        provenance=_provenance(source_id=f"uuid-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "name": name,
            "country": country,
        },
    )


def _make_route_pattern(pattern: str = "911") -> MigrationObject:
    return MigrationObject(
        canonical_id=f"route_pattern:{pattern}",
        provenance=_provenance(source_id=f"uuid-rp-{pattern}", name=pattern),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"pattern": pattern},
    )


class TestE911MapperWithElinGroups:
    def test_elin_group_creates_config(self):
        store = MigrationStore(":memory:")
        store.upsert_object(_make_elin_group())

        mapper = E911Mapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        config = store.get_object("e911_config:ELIN-HQ")
        assert config is not None
        assert config["elin_group_name"] == "ELIN-HQ"

    def test_produces_architecture_advisory(self):
        store = MigrationStore(":memory:")
        store.upsert_object(_make_elin_group())

        mapper = E911Mapper()
        result = mapper.map(store)

        assert len(result.decisions) == 1
        assert result.decisions[0].type.value == "ARCHITECTURE_ADVISORY"
        assert "E911" in result.decisions[0].summary

    def test_multiple_elin_groups(self):
        store = MigrationStore(":memory:")
        store.upsert_object(_make_elin_group("ELIN-HQ", ["+14155559911"]))
        store.upsert_object(_make_elin_group("ELIN-BRANCH", ["+12125559911"]))

        mapper = E911Mapper()
        result = mapper.map(store)

        assert result.objects_created == 2
        assert len(result.decisions) == 1  # Single advisory for all

    def test_detects_911_route_pattern(self):
        store = MigrationStore(":memory:")
        store.upsert_object(_make_elin_group())
        store.upsert_object(_make_route_pattern("911"))

        mapper = E911Mapper()
        result = mapper.map(store)

        config = store.get_object("e911_config:ELIN-HQ")
        assert config["has_emergency_route_pattern"] is True


class TestE911MapperWithGeoLocationsOnly:
    def test_geo_location_only_creates_config(self):
        store = MigrationStore(":memory:")
        store.upsert_object(_make_geo_location())

        mapper = E911Mapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        assert len(result.decisions) == 1


class TestE911MapperNoData:
    def test_no_e911_data_no_objects(self):
        store = MigrationStore(":memory:")

        mapper = E911Mapper()
        result = mapper.map(store)

        assert result.objects_created == 0
        assert len(result.decisions) == 0
