"""Tests for DECTMapper: CanonicalDECTNetwork enrichment + decision generation.

Uses real :memory: SQLite store, no mocks.

Test cases from docs/superpowers/specs/2026-04-10-dect-migration.md §10b cases 4-6.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from wxcli.migration.models import (
    CanonicalDECTNetwork,
    CanonicalLocation,
    LocationAddress,
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.dect_mapper import DECTMapper


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _provenance(source_id: str = "test-id", name: str = "test") -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id=source_id,
        source_name=name,
        extracted_at=_now(),
    )


def _make_store() -> MigrationStore:
    return MigrationStore(":memory:")


def _dect_network(
    pool_name: str = "HQ-DECT",
    handset_names: list[str] | None = None,
    base_stations: list[dict] | None = None,
) -> CanonicalDECTNetwork:
    """Build a minimal CanonicalDECTNetwork as normalize_dect_group() would produce it."""
    if handset_names is None:
        handset_names = ["DECT001", "DECT002"]

    assignments = [
        {"device_canonical_id": f"device:{n}", "cucm_device_name": n}
        for n in handset_names
    ]

    pre = {"cucm_device_pool": pool_name, "handset_count": len(handset_names)}
    if base_stations:
        pre["base_stations"] = base_stations

    return CanonicalDECTNetwork(
        canonical_id=f"dect_network:{pool_name}",
        provenance=_provenance(source_id=f"uuid-{pool_name}", name=f"DECT-{pool_name}"),
        status=MigrationStatus.NORMALIZED,
        network_name=f"DECT-{pool_name}",
        display_name=f"DECT-{pool_name}",
        model="PENDING",
        access_code="",
        base_stations=base_stations or [],
        handset_assignments=assignments,
        pre_migration_state=pre,
    )


def _seed_location(store: MigrationStore, loc_name: str = "HQ") -> str:
    """Add a CanonicalLocation to the store and return its canonical_id."""
    loc = CanonicalLocation(
        canonical_id=f"location:{loc_name}",
        provenance=_provenance(source_id=f"uuid-loc-{loc_name}", name=loc_name),
        status=MigrationStatus.ANALYZED,
        name=loc_name,
        address=LocationAddress(country="US"),
    )
    store.upsert_object(loc)
    return loc.canonical_id


def _seed_device_pool(store: MigrationStore, pool_name: str) -> str:
    """Add a device_pool MigrationObject and return its canonical_id."""
    dp = MigrationObject(
        canonical_id=f"device_pool:{pool_name}",
        provenance=_provenance(source_id=f"uuid-dp-{pool_name}", name=pool_name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"device_pool_name": pool_name},
    )
    store.upsert_object(dp)
    return dp.canonical_id


def _seed_user(store: MigrationStore, user_name: str = "jdoe") -> str:
    """Add a minimal user device object and return its canonical_id."""
    user_cid = f"user:{user_name}"
    user = MigrationObject(
        canonical_id=user_cid,
        provenance=_provenance(source_id=f"uuid-{user_name}", name=user_name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"userName": user_name},
    )
    store.upsert_object(user)
    return user_cid


# ---------------------------------------------------------------------------
# Test 1: DECTMapper resolves location via device_pool_to_location cross-ref
# ---------------------------------------------------------------------------


class TestDECTMapperResolvesLocation:
    def test_dect_mapper_resolves_location(self):
        """Network with device_pool_to_location cross-ref gets location resolved."""
        store = _make_store()

        pool_name = "HQ-DECT"
        loc_cid = _seed_location(store, "HQ")
        pool_cid = _seed_device_pool(store, pool_name)
        store.add_cross_ref(pool_cid, loc_cid, "device_pool_to_location")

        network = _dect_network(pool_name=pool_name, handset_names=["DECT001"])
        store.upsert_object(network)

        mapper = DECTMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        enriched = store.get_objects("dect_network")
        assert len(enriched) == 1
        assert enriched[0]["location_canonical_id"] == loc_cid


# ---------------------------------------------------------------------------
# Test 2: DECT_NETWORK_DESIGN decision when no base station inventory
# ---------------------------------------------------------------------------


class TestDECTMapperDesignDecisionNoInventory:
    def test_dect_mapper_design_decision_no_inventory(self):
        """DECT network without base station inventory generates DECT_NETWORK_DESIGN decision."""
        store = _make_store()

        pool_name = "HQ-DECT"
        loc_cid = _seed_location(store, "HQ")
        pool_cid = _seed_device_pool(store, pool_name)
        store.add_cross_ref(pool_cid, loc_cid, "device_pool_to_location")

        # No base_stations in pre_migration_state
        network = _dect_network(pool_name=pool_name, handset_names=["DECT001", "DECT002"])
        store.upsert_object(network)

        mapper = DECTMapper()
        result = mapper.map(store)

        design_decisions = [
            d for d in result.decisions
            if d.type.value == "DECT_NETWORK_DESIGN"
        ]
        assert len(design_decisions) >= 1

        # The no-inventory decision should be MEDIUM severity
        no_inv = next(
            (d for d in design_decisions if d.severity == "MEDIUM"
             and not d.context.get("base_stations_provided", True)),
            None,
        )
        assert no_inv is not None, "Expected MEDIUM DECT_NETWORK_DESIGN for missing inventory"
        assert no_inv.context["cucm_device_pool"] == pool_name


# ---------------------------------------------------------------------------
# Test 3: DECT_NETWORK_DESIGN decision when multiple zones share same location
# ---------------------------------------------------------------------------


class TestDECTMapperDesignDecisionMultiZone:
    def test_dect_mapper_design_decision_multi_zone(self):
        """Two DECT networks pointing to the same location generate a zone-boundary decision."""
        store = _make_store()

        loc_cid = _seed_location(store, "HQ")

        for pool_name in ["DECT-ZONE-A", "DECT-ZONE-B"]:
            pool_cid = _seed_device_pool(store, pool_name)
            store.add_cross_ref(pool_cid, loc_cid, "device_pool_to_location")
            network = _dect_network(
                pool_name=pool_name,
                handset_names=[f"{pool_name}-D001"],
            )
            store.upsert_object(network)

        mapper = DECTMapper()
        result = mapper.map(store)

        # One multi-zone DECT_NETWORK_DESIGN decision should be generated
        multi_zone = [
            d for d in result.decisions
            if d.type.value == "DECT_NETWORK_DESIGN"
            and d.context.get("zone_count", 0) > 1
        ]
        assert len(multi_zone) == 1, (
            f"Expected exactly 1 multi-zone decision, got {len(multi_zone)}: "
            f"{[d.context for d in multi_zone]}"
        )
        assert multi_zone[0].context["zone_count"] == 2
        assert multi_zone[0].context["location_name"] == loc_cid


# ---------------------------------------------------------------------------
# Test 4: DECT_HANDSET_ASSIGNMENT decision for unowned handsets
# ---------------------------------------------------------------------------


class TestDECTMapperUnownedHandsetDecision:
    def test_dect_mapper_unowned_handset_decision(self):
        """Handset with no device_owned_by_user cross-ref generates DECT_HANDSET_ASSIGNMENT."""
        store = _make_store()

        pool_name = "HQ-DECT"
        loc_cid = _seed_location(store, "HQ")
        pool_cid = _seed_device_pool(store, pool_name)
        store.add_cross_ref(pool_cid, loc_cid, "device_pool_to_location")

        # Two handsets; only one has an owner cross-ref
        network = _dect_network(
            pool_name=pool_name,
            handset_names=["DECT001", "DECT002"],
        )
        store.upsert_object(network)

        # Seed device objects so the FK constraint is satisfied
        for device_name in ["DECT001", "DECT002"]:
            dev = MigrationObject(
                canonical_id=f"device:{device_name}",
                provenance=_provenance(source_id=f"uuid-{device_name}", name=device_name),
                status=MigrationStatus.NORMALIZED,
                pre_migration_state={"name": device_name},
            )
            store.upsert_object(dev)

        # Give DECT001 an owner but leave DECT002 unowned
        user_cid = _seed_user(store, "jdoe")
        store.add_cross_ref("device:DECT001", user_cid, "device_owned_by_user")

        mapper = DECTMapper()
        result = mapper.map(store)

        handset_decisions = [
            d for d in result.decisions
            if d.type.value == "DECT_HANDSET_ASSIGNMENT"
        ]
        assert len(handset_decisions) == 1
        assert handset_decisions[0].context["cucm_device_name"] == "DECT002"
        assert handset_decisions[0].context["owner_status"] == "unowned"

        # Verify the enriched handset_assignments reflect owner resolution
        enriched = store.get_objects("dect_network")[0]
        assignments = enriched["handset_assignments"]
        owned = next(a for a in assignments if a["cucm_device_name"] == "DECT001")
        unowned = next(a for a in assignments if a["cucm_device_name"] == "DECT002")
        assert owned["user_canonical_id"] == user_cid
        assert unowned["user_canonical_id"] is None


# ---------------------------------------------------------------------------
# Test 5: Auto-select DBS-110 for <= 30 handsets
# ---------------------------------------------------------------------------


class TestDECTMapperAutoDBS110:
    def test_dect_mapper_auto_dbs110(self):
        """Network with <= 30 handsets auto-selects DBS-110 model."""
        store = _make_store()

        pool_name = "SMALL-DECT"
        loc_cid = _seed_location(store, "Branch")
        pool_cid = _seed_device_pool(store, pool_name)
        store.add_cross_ref(pool_cid, loc_cid, "device_pool_to_location")

        # Exactly 30 handsets — at the DBS-110 threshold
        handsets = [f"DECT{i:03d}" for i in range(30)]
        network = _dect_network(pool_name=pool_name, handset_names=handsets)
        store.upsert_object(network)

        mapper = DECTMapper()
        result = mapper.map(store)

        enriched = store.get_objects("dect_network")
        assert enriched[0]["model"] == "DBS-110"


# ---------------------------------------------------------------------------
# Test 6: Auto-select DBS-210 for > 30 handsets
# ---------------------------------------------------------------------------


class TestDECTMapperAutoDBS210:
    def test_dect_mapper_auto_dbs210(self):
        """Network with > 30 handsets auto-selects DBS-210 model."""
        store = _make_store()

        pool_name = "LARGE-DECT"
        loc_cid = _seed_location(store, "Campus")
        pool_cid = _seed_device_pool(store, pool_name)
        store.add_cross_ref(pool_cid, loc_cid, "device_pool_to_location")

        # 31 handsets — just over the DBS-110 threshold
        handsets = [f"DECT{i:03d}" for i in range(31)]
        network = _dect_network(pool_name=pool_name, handset_names=handsets)
        store.upsert_object(network)

        mapper = DECTMapper()
        result = mapper.map(store)

        enriched = store.get_objects("dect_network")
        assert enriched[0]["model"] == "DBS-210"
