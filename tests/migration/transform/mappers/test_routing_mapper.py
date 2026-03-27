"""Tests for routing_mapper: CUCM routing -> Webex Calling routing infrastructure.

Uses real :memory: SQLite store, no mocks.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from wxcli.migration.models import (
    CanonicalLocation,
    LocationAddress,
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.routing_mapper import RoutingMapper


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


def _sip_trunk(
    name: str = "SIP-Trunk-1",
    destinations: list | None = None,
    cucm_device_pool: str | None = None,
    security_profile: str | None = None,
    max_calls: int | None = None,
) -> MigrationObject:
    state: dict = {
        "name": name,
        "destinations": destinations or [{"address": "sbc.example.com", "port": 5060, "sort_order": 1}],
    }
    if cucm_device_pool:
        state["cucm_device_pool"] = cucm_device_pool
    if security_profile:
        state["securityProfileName"] = security_profile
    if max_calls:
        state["max_calls"] = max_calls

    return MigrationObject(
        canonical_id=f"sip_trunk:{name}",
        provenance=_provenance(source_id=f"uuid-trunk-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=state,
    )


def _route_group(
    name: str = "RG-Primary",
    trunks: list[dict] | None = None,
) -> MigrationObject:
    state: dict = {
        "name": name,
        "trunks": trunks or [{"trunk_name": "SIP-Trunk-1", "priority": 1}],
    }
    return MigrationObject(
        canonical_id=f"route_group:{name}",
        provenance=_provenance(source_id=f"uuid-rg-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=state,
    )


def _route_pattern(
    pattern: str = "9.1[2-9]XXXXXXXXX",
    target_type: str | None = None,
    target_name: str | None = None,
    partition: str | None = None,
) -> MigrationObject:
    state: dict = {"pattern": pattern}
    if target_type:
        state["target_type"] = target_type
    if target_name:
        state["target_name"] = target_name
    if partition:
        state["partition"] = partition

    # Canonical ID from pattern (replace special chars for ID safety)
    safe_pattern = pattern.replace(".", "_").replace("[", "").replace("]", "").replace("!", "BANG")
    return MigrationObject(
        canonical_id=f"route_pattern:{safe_pattern}",
        provenance=_provenance(source_id=f"uuid-rp-{safe_pattern}", name=pattern),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=state,
    )


def _translation_pattern(
    pattern: str = "9.1XXX",
    replacement: str = "+1XXX",
    description: str | None = None,
    partition: str | None = None,
) -> MigrationObject:
    state: dict = {
        "pattern": pattern,
        "calledPartyTransformationMask": replacement,
    }
    if description:
        state["description"] = description
    if partition:
        state["partition"] = partition

    safe_pattern = pattern.replace(".", "_")
    return MigrationObject(
        canonical_id=f"translation_pattern:{safe_pattern}",
        provenance=_provenance(source_id=f"uuid-tp-{safe_pattern}", name=pattern),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=state,
    )


def _make_store() -> MigrationStore:
    return MigrationStore(":memory:")


def _seed_location_chain(store: MigrationStore, dp_name: str = "HQ-Trunks") -> str:
    """Seed device pool + location for trunk location resolution."""
    dp = MigrationObject(
        canonical_id=f"device_pool:{dp_name}",
        provenance=_provenance(source_id=f"uuid-dp-{dp_name}", name=dp_name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"device_pool_name": dp_name},
    )
    store.upsert_object(dp)

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
# Tests — trunk mapping
# ---------------------------------------------------------------------------


class TestRoutingMapperTrunks:
    """CUCM SIP Trunk -> CanonicalTrunk."""

    def test_trunk_created_with_password_and_decision(self):
        """Trunk created with generated password; MISSING_DATA decision for password."""
        store = _make_store()
        trunk = _sip_trunk("SIP-Trunk-1")
        store.upsert_object(trunk)

        mapper = RoutingMapper()
        result = mapper.map(store)

        assert result.objects_created >= 1  # at least the trunk

        trunks = store.get_objects("trunk")
        assert len(trunks) == 1
        assert trunks[0]["name"] == "SIP-Trunk-1"
        assert trunks[0]["password"] is not None
        assert len(trunks[0]["password"]) == 16  # _TRUNK_PASSWORD_LENGTH

        # MISSING_DATA decision for password
        password_decisions = [
            d for d in result.decisions
            if d.type.value == "MISSING_DATA"
            and d.context.get("reason") == "password_not_extractable"
        ]
        assert len(password_decisions) == 1

    def test_trunk_handles_destinations_as_list(self):
        """pre_migration_state.destinations is a list of [{address, port, sort_order}]."""
        store = _make_store()
        trunk = _sip_trunk(
            "SIP-Trunk-1",
            destinations=[
                {"address": "backup.example.com", "port": 5061, "sort_order": 2},
                {"address": "primary.example.com", "port": 5060, "sort_order": 1},
            ],
        )
        store.upsert_object(trunk)

        mapper = RoutingMapper()
        mapper.map(store)

        trunks = store.get_objects("trunk")
        assert trunks[0]["address"] == "primary.example.com"
        assert trunks[0]["port"] == 5060

    def test_trunk_type_registering_default(self):
        store = _make_store()
        trunk = _sip_trunk("SIP-Trunk-1")
        store.upsert_object(trunk)

        mapper = RoutingMapper()
        mapper.map(store)

        trunks = store.get_objects("trunk")
        assert trunks[0]["trunk_type"] == "REGISTERING"

    def test_trunk_type_certificate_based(self):
        store = _make_store()
        trunk = _sip_trunk("SIP-Trunk-TLS", security_profile="SIP-Trunk-TLS-Profile")
        store.upsert_object(trunk)

        mapper = RoutingMapper()
        mapper.map(store)

        trunks = store.get_objects("trunk")
        assert trunks[0]["trunk_type"] == "CERTIFICATE_BASED"

    def test_trunk_location_resolved(self):
        store = _make_store()
        loc_id = _seed_location_chain(store, "HQ-Trunks")
        trunk = _sip_trunk("SIP-Trunk-1", cucm_device_pool="HQ-Trunks")
        store.upsert_object(trunk)
        store.add_cross_ref(trunk.canonical_id, "device_pool:HQ-Trunks", "trunk_at_location")

        mapper = RoutingMapper()
        mapper.map(store)

        trunks = store.get_objects("trunk")
        assert trunks[0]["location_id"] == loc_id

    def test_trunk_no_location_multiple_locations_with_none_pre_migration_state(self):
        """Trunk with no device pool + locations whose pre_migration_state is None.

        Regression: loc.get('pre_migration_state', {}) returns None (not {})
        when the key exists with value None, causing AttributeError on .get('name').
        """
        store = _make_store()
        # CanonicalLocation objects from LocationMapper have pre_migration_state=None
        loc1 = CanonicalLocation(
            canonical_id="location:Site-A",
            provenance=_provenance(source_id="uuid-loc-a", name="Site-A"),
            status=MigrationStatus.ANALYZED,
            name="Site-A",
            address=LocationAddress(country="US"),
        )
        loc2 = CanonicalLocation(
            canonical_id="location:Site-B",
            provenance=_provenance(source_id="uuid-loc-b", name="Site-B"),
            status=MigrationStatus.ANALYZED,
            name="Site-B",
            address=LocationAddress(country="US"),
        )
        store.upsert_object(loc1)
        store.upsert_object(loc2)

        # Trunk with no device pool cross-ref -> triggers multi-location branch
        trunk = _sip_trunk("Org-Trunk-1")
        store.upsert_object(trunk)

        mapper = RoutingMapper()
        result = mapper.map(store)  # should NOT raise AttributeError

        # Should produce LOCATION_AMBIGUOUS decision
        loc_decisions = [
            d for d in result.decisions
            if d.type.value == "LOCATION_AMBIGUOUS"
        ]
        assert len(loc_decisions) == 1
        assert "Org-Trunk-1" in loc_decisions[0].summary

    def test_trunk_handles_none_destination_entries(self):
        """Destinations list with None entries should not crash."""
        store = _make_store()
        trunk = _sip_trunk(
            "SIP-Trunk-1",
            destinations=[None, {"address": "sbc.example.com", "port": 5060, "sort_order": 1}],
        )
        store.upsert_object(trunk)

        mapper = RoutingMapper()
        mapper.map(store)

        trunks = store.get_objects("trunk")
        assert trunks[0]["address"] == "sbc.example.com"


# ---------------------------------------------------------------------------
# Tests — route group mapping
# ---------------------------------------------------------------------------


class TestRoutingMapperRouteGroups:
    """CUCM Route Group -> CanonicalRouteGroup."""

    def test_route_group_created_with_trunk_refs(self):
        store = _make_store()
        trunk = _sip_trunk("SIP-Trunk-1")
        store.upsert_object(trunk)

        rg = _route_group("RG-Primary", trunks=[{"trunk_name": "SIP-Trunk-1", "priority": 1}])
        store.upsert_object(rg)
        store.add_cross_ref(rg.canonical_id, trunk.canonical_id, "route_group_has_trunk")

        mapper = RoutingMapper()
        result = mapper.map(store)

        rgs = store.get_objects("route_group")
        assert len(rgs) == 1
        assert rgs[0]["name"] == "RG-Primary"
        assert len(rgs[0]["local_gateways"]) == 1
        assert rgs[0]["local_gateways"][0]["trunk_canonical_id"] == "trunk:SIP-Trunk-1"

    def test_route_group_split_over_10_trunks(self):
        """Route group with 12 trunks -> split into 2 groups (10 + 2)."""
        store = _make_store()

        trunk_names = [f"SIP-Trunk-{i}" for i in range(1, 13)]
        trunk_state_list = []
        for tn in trunk_names:
            t = _sip_trunk(tn)
            store.upsert_object(t)
            trunk_state_list.append({"trunk_name": tn, "priority": trunk_names.index(tn) + 1})

        rg = _route_group("RG-Large", trunks=trunk_state_list)
        store.upsert_object(rg)
        for tn in trunk_names:
            store.add_cross_ref(rg.canonical_id, f"sip_trunk:{tn}", "route_group_has_trunk")

        mapper = RoutingMapper()
        result = mapper.map(store)

        # Filter mapper-produced route groups (status=analyzed) from input objects (status=normalized)
        all_rgs = store.get_objects("route_group")
        mapped_rgs = [rg_obj for rg_obj in all_rgs if rg_obj["status"] == "analyzed"]
        # Should be 2 route groups: RG-Large-1 (10 trunks) and RG-Large-2 (2 trunks)
        assert len(mapped_rgs) == 2

        rg_names = {rg_obj["name"] for rg_obj in mapped_rgs}
        assert "RG-Large-1" in rg_names
        assert "RG-Large-2" in rg_names

        # Check trunk counts
        for rg_obj in mapped_rgs:
            if rg_obj["name"] == "RG-Large-1":
                assert len(rg_obj["local_gateways"]) == 10
            elif rg_obj["name"] == "RG-Large-2":
                assert len(rg_obj["local_gateways"]) == 2


# ---------------------------------------------------------------------------
# Tests — dial plan mapping (route patterns)
# ---------------------------------------------------------------------------


class TestRoutingMapperDialPlans:
    """CUCM Route Patterns -> CanonicalDialPlan."""

    def test_route_patterns_grouped_into_dial_plan(self):
        """Two route patterns targeting the same trunk -> one dial plan with both patterns."""
        store = _make_store()
        trunk = _sip_trunk("SIP-Trunk-1")
        store.upsert_object(trunk)

        rp1 = _route_pattern("9.1[2-9]XXXXXXXXX", target_type="trunk", target_name="SIP-Trunk-1")
        rp2 = _route_pattern("9.1900XXXXXXX", target_type="trunk", target_name="SIP-Trunk-1")
        store.upsert_object(rp1)
        store.upsert_object(rp2)

        mapper = RoutingMapper()
        result = mapper.map(store)

        dps = store.get_objects("dial_plan")
        assert len(dps) == 1
        assert "SIP-Trunk-1" in dps[0]["name"]
        assert dps[0]["route_type"] == "TRUNK"
        assert dps[0]["route_id"] == "trunk:SIP-Trunk-1"
        # Both patterns should be in the dial plan
        assert len(dps[0]["dial_patterns"]) == 2

    def test_at_macro_produces_feature_approximation(self):
        """Route pattern with @ macro -> FEATURE_APPROXIMATION decision, pattern skipped."""
        store = _make_store()
        rp = _route_pattern("9.@", target_type="trunk", target_name="SIP-Trunk-1")
        store.upsert_object(rp)

        mapper = RoutingMapper()
        result = mapper.map(store)

        at_decisions = [
            d for d in result.decisions if d.type.value == "FEATURE_APPROXIMATION"
        ]
        assert len(at_decisions) == 1
        assert "@ macro" in at_decisions[0].summary

    def test_empty_cross_refs_fallback_to_pre_migration_state(self):
        """When cross-refs are empty, routing target extracted from pre_migration_state."""
        store = _make_store()
        trunk = _sip_trunk("SIP-Trunk-1")
        store.upsert_object(trunk)

        # Route pattern with target info in pre_migration_state but NO cross-refs
        rp = _route_pattern(
            "9.1[2-9]XXXXXXXXX",
            target_type="trunk",
            target_name="SIP-Trunk-1",
        )
        store.upsert_object(rp)
        # Deliberately NOT adding route_pattern_uses_gateway cross-ref

        mapper = RoutingMapper()
        result = mapper.map(store)

        dps = store.get_objects("dial_plan")
        assert len(dps) == 1
        assert dps[0]["route_id"] == "trunk:SIP-Trunk-1"

    def test_no_target_produces_missing_data(self):
        """Route pattern with no target at all -> MISSING_DATA decision."""
        store = _make_store()
        rp = _route_pattern("9.1XXXXXXXXXX")
        # No cross-refs, no target in pre_migration_state
        store.upsert_object(rp)

        mapper = RoutingMapper()
        result = mapper.map(store)

        missing = [
            d for d in result.decisions
            if d.type.value == "MISSING_DATA"
            and d.context.get("reason") == "no_routing_target"
        ]
        assert len(missing) == 1

    def test_pattern_conversion_applied(self):
        """CUCM pattern '9.1[2-9]XXXXXXXXX' -> Webex '+1[2-9]XXXXXXXXX'."""
        store = _make_store()
        trunk = _sip_trunk("SIP-Trunk-1")
        store.upsert_object(trunk)

        rp = _route_pattern("9.1[2-9]XXXXXXXXX", target_type="trunk", target_name="SIP-Trunk-1")
        store.upsert_object(rp)

        mapper = RoutingMapper()
        mapper.map(store)

        dps = store.get_objects("dial_plan")
        assert "+1[2-9]XXXXXXXXX" in dps[0]["dial_patterns"]

    def test_route_pattern_via_cross_ref_gateway(self):
        """Route pattern resolved via route_pattern_uses_gateway cross-ref."""
        store = _make_store()
        trunk = _sip_trunk("SIP-Trunk-1")
        store.upsert_object(trunk)

        rp = _route_pattern("9.1[2-9]XXXXXXXXX")
        store.upsert_object(rp)
        # Add cross-ref instead of pre_migration_state target
        store.add_cross_ref(
            rp.canonical_id, "sip_trunk:SIP-Trunk-1", "route_pattern_uses_gateway"
        )

        mapper = RoutingMapper()
        mapper.map(store)

        dps = store.get_objects("dial_plan")
        assert len(dps) == 1
        assert dps[0]["route_id"] == "trunk:SIP-Trunk-1"
        assert dps[0]["route_type"] == "TRUNK"


# ---------------------------------------------------------------------------
# Tests — translation patterns
# ---------------------------------------------------------------------------


class TestRoutingMapperTranslationPatterns:
    """CUCM Translation Pattern -> CanonicalTranslationPattern."""

    def test_translation_pattern_created(self):
        store = _make_store()
        tp = _translation_pattern("9.1XXX", "1XXX", description="Strip 9 prefix")
        store.upsert_object(tp)

        mapper = RoutingMapper()
        result = mapper.map(store)

        # Filter mapper-produced objects (status=analyzed) from input objects (status=normalized)
        all_tps = store.get_objects("translation_pattern")
        mapped_tps = [t for t in all_tps if t["status"] == "analyzed"]
        assert len(mapped_tps) == 1
        assert mapped_tps[0]["name"] == "Strip 9 prefix"
        assert mapped_tps[0]["replacement_pattern"] == "1XXX"
        assert mapped_tps[0]["status"] == "analyzed"

    def test_e164_replacement_with_wildcards_flagged(self):
        """E.164 replacement pattern with X wildcards -> MISSING_DATA decision."""
        store = _make_store()
        tp = _translation_pattern("9.1XXXXXXXXXX", "+1919666XXXX")
        store.upsert_object(tp)

        mapper = RoutingMapper()
        result = mapper.map(store)

        wildcard_decisions = [
            d for d in result.decisions
            if d.type.value == "MISSING_DATA"
            and d.context.get("reason") == "e164_replacement_has_wildcards"
        ]
        assert len(wildcard_decisions) == 1

    def test_non_e164_replacement_with_wildcards_allowed(self):
        """Non-E.164 replacement pattern with X wildcards -> no decision about wildcards."""
        store = _make_store()
        tp = _translation_pattern("9.1XXX", "1XXX")
        store.upsert_object(tp)

        mapper = RoutingMapper()
        result = mapper.map(store)

        wildcard_decisions = [
            d for d in result.decisions
            if d.type.value == "MISSING_DATA"
            and d.context.get("reason") == "e164_replacement_has_wildcards"
        ]
        assert len(wildcard_decisions) == 0


# ---------------------------------------------------------------------------
# Tests — full routing pipeline
# ---------------------------------------------------------------------------


class TestRoutingMapperFullPipeline:
    """End-to-end: trunk + route group + route patterns -> all objects created."""

    def test_full_pipeline(self):
        store = _make_store()

        # Create trunk
        trunk = _sip_trunk("SIP-Trunk-1")
        store.upsert_object(trunk)

        # Create route group with that trunk
        rg = _route_group("RG-Primary", trunks=[{"trunk_name": "SIP-Trunk-1", "priority": 1}])
        store.upsert_object(rg)
        store.add_cross_ref(rg.canonical_id, trunk.canonical_id, "route_group_has_trunk")

        # Create route pattern targeting the route group via pre_migration_state
        rp = _route_pattern(
            "9.1[2-9]XXXXXXXXX",
            target_type="route_group",
            target_name="RG-Primary",
        )
        store.upsert_object(rp)

        # Create translation pattern
        tp = _translation_pattern("9.1XXX", "1XXX", description="Strip-9")
        store.upsert_object(tp)

        mapper = RoutingMapper()
        result = mapper.map(store)

        trunks = store.get_objects("trunk")
        # Filter mapper-produced route groups from input route groups
        all_rgs = store.get_objects("route_group")
        mapped_rgs = [rg for rg in all_rgs if rg["status"] == "analyzed"]
        dps = store.get_objects("dial_plan")
        all_tps = store.get_objects("translation_pattern")
        mapped_tps = [t for t in all_tps if t["status"] == "analyzed"]

        assert len(trunks) == 1
        assert len(mapped_rgs) == 1
        assert len(dps) == 1
        assert len(mapped_tps) == 1

        # Dial plan should reference the route group
        assert dps[0]["route_type"] == "ROUTE_GROUP"
        assert dps[0]["route_id"] == "route_group:RG-Primary"


class TestInferTrunkType:
    """Test _infer_trunk_type with Tier 2 security_mode field."""

    def test_tls_security_mode(self):
        from wxcli.migration.transform.mappers.routing_mapper import _infer_trunk_type
        assert _infer_trunk_type({"security_mode": "TLS"}) == "CERTIFICATE_BASED"

    def test_ipsec_security_mode(self):
        from wxcli.migration.transform.mappers.routing_mapper import _infer_trunk_type
        assert _infer_trunk_type({"security_mode": "IPSEC"}) == "CERTIFICATE_BASED"

    def test_non_secure_security_mode(self):
        from wxcli.migration.transform.mappers.routing_mapper import _infer_trunk_type
        assert _infer_trunk_type({"security_mode": "NON_SECURE"}) == "REGISTERING"

    def test_fallback_security_profile_name(self):
        from wxcli.migration.transform.mappers.routing_mapper import _infer_trunk_type
        assert _infer_trunk_type({"security_profile": "TLS-SIP-Profile"}) == "CERTIFICATE_BASED"

    def test_fallback_legacy_field(self):
        from wxcli.migration.transform.mappers.routing_mapper import _infer_trunk_type
        assert _infer_trunk_type({"securityProfileName": "Non Secure SIP Trunk Profile"}) == "REGISTERING"

    def test_default_registering(self):
        from wxcli.migration.transform.mappers.routing_mapper import _infer_trunk_type
        assert _infer_trunk_type({}) == "REGISTERING"
