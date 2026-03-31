"""Tests for TransformEngine — mapper orchestration and failure handling.

Uses real :memory: SQLite store, no mocks.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from wxcli.migration.models import (
    MapperResult,
    MigrationObject,
    MigrationStatus,
    Provenance,
    TransformResult,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.engine import MAPPER_ORDER, TransformEngine
from wxcli.migration.transform.mappers.base import Mapper


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _provenance(name: str = "test") -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id=f"uuid-{name}",
        source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def _make_store() -> MigrationStore:
    return MigrationStore(":memory:")


# ---------------------------------------------------------------------------
# Tests: MAPPER_ORDER
# ---------------------------------------------------------------------------


class TestMapperOrder:
    """Verify MAPPER_ORDER contains all 20 mappers in correct dependency order."""

    def test_has_twenty_mappers(self) -> None:
        assert len(MAPPER_ORDER) == 20

    def test_order_names(self) -> None:
        names = [cls.__name__ for cls in MAPPER_ORDER]
        assert names == [
            "LocationMapper",
            "RoutingMapper",
            "UserMapper",
            "LineMapper",
            "WorkspaceMapper",
            "DeviceMapper",
            "FeatureMapper",
            "CSSMapper",
            "VoicemailMapper",
            "CallForwardingMapper",
            "MonitoringMapper",
            "SNRMapper",
            "DeviceProfileMapper",
            "E911Mapper",
            "MOHMapper",
            "AnnouncementMapper",
            "SoftkeyMapper",
            "ButtonTemplateMapper",
            "CallSettingsMapper",
            "DeviceLayoutMapper",
        ]

    def test_location_is_first(self) -> None:
        """LocationMapper must run before anything that depends on locations."""
        from wxcli.migration.transform.mappers.location_mapper import LocationMapper

        assert MAPPER_ORDER[0] is LocationMapper


# ---------------------------------------------------------------------------
# Tests: TransformEngine.run()
# ---------------------------------------------------------------------------


class TestTransformEngineRun:
    """Test the engine's run() method."""

    def test_empty_store_produces_empty_result(self) -> None:
        """Running all mappers on an empty store produces no errors."""
        store = _make_store()
        engine = TransformEngine()
        result = engine.run(store)

        assert isinstance(result, TransformResult)
        assert result.errors == []
        # May have 0 decisions (nothing to map)
        assert isinstance(result.decisions, list)

    def test_returns_transform_result(self) -> None:
        store = _make_store()
        engine = TransformEngine()
        result = engine.run(store)

        assert isinstance(result, TransformResult)
        assert hasattr(result, "decisions")
        assert hasattr(result, "errors")

    def test_config_passed_to_location_mapper(self) -> None:
        """Verify config keys are forwarded to LocationMapper."""
        store = _make_store()
        # Seed a device pool so LocationMapper has something to do
        dp = MigrationObject(
            canonical_id="device_pool:HQ-Test",
            provenance=_provenance("HQ-Test"),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={"device_pool_name": "HQ-Test"},
        )
        store.upsert_object(dp)
        # Add a cucm_location reference
        loc = MigrationObject(
            canonical_id="cucm_location:HQ",
            provenance=_provenance("HQ"),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={
                "city": "Denver",
                "state": "CO",
                "country": "US",
            },
        )
        store.upsert_object(loc)
        store.add_cross_ref(
            "device_pool:HQ-Test", "cucm_location:HQ", "device_pool_at_cucm_location"
        )

        engine = TransformEngine(config={"default_language": "fr_fr"})
        result = engine.run(store)

        # The location created should have the custom language
        locations = store.get_objects("location")
        assert len(locations) >= 1
        loc_data = locations[0]
        assert loc_data.get("preferred_language") == "fr_fr"

    def test_continues_on_mapper_failure(self) -> None:
        """If a mapper raises an exception, engine records error and continues."""
        store = _make_store()

        # Patch LocationMapper.map to raise
        with patch(
            "wxcli.migration.transform.engine.LocationMapper"
        ) as MockLocMapper:
            mock_instance = MockLocMapper.return_value
            mock_instance.name = "location_mapper"
            mock_instance.map.side_effect = RuntimeError("Simulated failure")

            # We need to keep the real MAPPER_ORDER but with our mock
            # Instead, let's patch just the one mapper's map method
            pass

        # Better approach: use a custom engine subclass approach
        # Actually, let's just test with the real thing by making a mapper fail
        # via bad data. Let's use a more direct test.

        # Simpler: patch one mapper in the order to blow up
        original_order = list(MAPPER_ORDER)

        class BoomMapper(Mapper):
            name = "boom_mapper"
            depends_on: list[str] = []

            def map(self, store: MigrationStore) -> MapperResult:
                raise RuntimeError("Simulated mapper explosion")

        try:
            # Insert BoomMapper at position 0 and remove LocationMapper
            MAPPER_ORDER.clear()
            MAPPER_ORDER.append(BoomMapper)
            MAPPER_ORDER.extend(original_order)

            engine = TransformEngine()
            result = engine.run(store)

            # Should have 1 error from BoomMapper
            assert len(result.errors) >= 1
            boom_error = result.errors[0]
            assert boom_error.mapper_name == "boom_mapper"
            assert "Simulated mapper explosion" in boom_error.error_message
            assert boom_error.traceback is not None
        finally:
            # Restore original order
            MAPPER_ORDER.clear()
            MAPPER_ORDER.extend(original_order)

    def test_aggregates_decisions_from_multiple_mappers(self) -> None:
        """Decisions from multiple mappers are aggregated into a single result."""
        store = _make_store()

        # Seed a device pool with no CUCM location (orphan -> LOCATION_AMBIGUOUS decision)
        dp = MigrationObject(
            canonical_id="device_pool:OrphanPool",
            provenance=_provenance("OrphanPool"),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={"device_pool_name": "OrphanPool"},
        )
        store.upsert_object(dp)

        # Seed a user with no email (-> MISSING_DATA decision from UserMapper)
        user = MigrationObject(
            canonical_id="user:noemail",
            provenance=_provenance("noemail"),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={
                "userid": "noemail",
                "firstName": "Test",
                "lastName": "User",
            },
        )
        store.upsert_object(user)

        engine = TransformEngine()
        result = engine.run(store)

        # Should have decisions from both LocationMapper and UserMapper
        decision_types = {d.type.value for d in result.decisions}
        assert "LOCATION_AMBIGUOUS" in decision_types
        assert "MISSING_DATA" in decision_types

    def test_decisions_saved_to_store(self) -> None:
        """Decisions produced by mappers are saved to the store."""
        store = _make_store()

        # Seed orphan pool
        dp = MigrationObject(
            canonical_id="device_pool:Orphan2",
            provenance=_provenance("Orphan2"),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={"device_pool_name": "Orphan2"},
        )
        store.upsert_object(dp)

        engine = TransformEngine()
        result = engine.run(store)

        # Decisions should be in the store
        store_decisions = store.get_all_decisions()
        assert len(store_decisions) >= 1
        # Store decisions should match result decisions count
        # (Note: some mappers may save decisions directly too, so use >= )
        assert len(store_decisions) >= len(result.decisions)
