"""Tests for Phase 12a fixes 4, 5, 6, 10, and 11.

Fix 4:  MissingDataAnalyzer — location address checks (dot-notation nested fields)
Fix 5:  MissingDataAnalyzer — user location_id required for Webex Calling
Fix 6:  RoutingMapper skips empty-pattern translation patterns;
        MissingDataAnalyzer flags translation patterns with empty matching_pattern
Fix 10: RoutingMapper creates MISSING_DATA when trunk has no resolvable location
Fix 11: RoutingMapper creates MISSING_DATA when route group has no resolvable members;
        MissingDataAnalyzer flags route groups with empty local_gateways

Uses real :memory: SQLite store, no mocks.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from wxcli.migration.models import (
    CanonicalLocation,
    CanonicalRouteGroup,
    CanonicalTranslationPattern,
    CanonicalTrunk,
    CanonicalUser,
    DecisionType,
    LocationAddress,
    MigrationObject,
    MigrationStatus,
    Provenance,
    TrunkGatewayRef,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.analyzers.missing_data import (
    MissingDataAnalyzer,
    _get_nested,
)
from wxcli.migration.transform.mappers.routing_mapper import RoutingMapper


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_store() -> MigrationStore:
    return MigrationStore(":memory:")


def _prov(name: str = "test") -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id=name,
        source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


# ===================================================================
# Fix 4: MissingDataAnalyzer — location address checks
# ===================================================================


class TestFix4LocationAddressChecks:
    """MissingDataAnalyzer should flag locations with missing address fields
    using dot-notation field access (address.country, address.city, etc.)."""

    def setup_method(self) -> None:
        self.store = _make_store()
        self.analyzer = MissingDataAnalyzer()

    def teardown_method(self) -> None:
        self.store.close()

    def test_location_complete_address_no_decision(self) -> None:
        """Location with all address fields populated produces no decision."""
        loc = CanonicalLocation(
            canonical_id="location:hq",
            provenance=_prov("hq"),
            name="Headquarters",
            address=LocationAddress(
                address1="100 Main St",
                city="San Jose",
                state="CA",
                postal_code="95134",
                country="US",
            ),
        )
        self.store.upsert_object(loc)

        decisions = self.analyzer.analyze(self.store)
        loc_decisions = [
            d for d in decisions if d.context.get("object_type") == "location"
        ]
        assert len(loc_decisions) == 0

    def test_location_missing_address1_city_state_high(self) -> None:
        """Location missing address1, city, and state produces HIGH decision."""
        loc = CanonicalLocation(
            canonical_id="location:noaddr",
            provenance=_prov("noaddr"),
            name="Branch Office",
            address=LocationAddress(
                address1=None,
                city=None,
                state=None,
                postal_code="95134",
                country="US",
            ),
        )
        self.store.upsert_object(loc)

        decisions = self.analyzer.analyze(self.store)
        loc_decisions = [
            d for d in decisions if d.context.get("object_type") == "location"
        ]
        assert len(loc_decisions) == 1
        assert loc_decisions[0].severity == "HIGH"
        missing_fields = loc_decisions[0].context["missing_fields"]
        assert "address.address1" in missing_fields
        assert "address.city" in missing_fields
        assert "address.state" in missing_fields

    def test_location_missing_country_high(self) -> None:
        """Location missing country produces HIGH decision (E911 compliance)."""
        loc = CanonicalLocation(
            canonical_id="location:nocountry",
            provenance=_prov("nocountry"),
            name="Remote Site",
            address=LocationAddress(
                address1="200 Oak Ave",
                city="Austin",
                state="TX",
                postal_code="73301",
                country=None,
            ),
        )
        self.store.upsert_object(loc)

        decisions = self.analyzer.analyze(self.store)
        loc_decisions = [
            d for d in decisions if d.context.get("object_type") == "location"
        ]
        assert len(loc_decisions) == 1
        assert loc_decisions[0].severity == "HIGH"
        assert "address.country" in loc_decisions[0].context["missing_fields"]

    def test_location_missing_postal_code_only_medium(self) -> None:
        """Location missing only postal_code produces MEDIUM (not HIGH)."""
        loc = CanonicalLocation(
            canonical_id="location:nozip",
            provenance=_prov("nozip"),
            name="Satellite",
            address=LocationAddress(
                address1="300 Pine Blvd",
                city="Denver",
                state="CO",
                postal_code=None,
                country="US",
            ),
        )
        self.store.upsert_object(loc)

        decisions = self.analyzer.analyze(self.store)
        loc_decisions = [
            d for d in decisions if d.context.get("object_type") == "location"
        ]
        assert len(loc_decisions) == 1
        assert loc_decisions[0].severity == "MEDIUM"
        assert loc_decisions[0].context["missing_fields"] == ["address.postal_code"]

    def test_location_missing_multiple_fields_highest_severity_wins(self) -> None:
        """Location missing postal_code (MEDIUM) and country (HIGH) -> HIGH overall."""
        loc = CanonicalLocation(
            canonical_id="location:multimissing",
            provenance=_prov("multimissing"),
            name="New Branch",
            address=LocationAddress(
                address1="400 Elm St",
                city="Portland",
                state="OR",
                postal_code=None,
                country=None,
            ),
        )
        self.store.upsert_object(loc)

        decisions = self.analyzer.analyze(self.store)
        loc_decisions = [
            d for d in decisions if d.context.get("object_type") == "location"
        ]
        assert len(loc_decisions) == 1
        assert loc_decisions[0].severity == "HIGH"
        missing_fields = loc_decisions[0].context["missing_fields"]
        assert "address.country" in missing_fields
        assert "address.postal_code" in missing_fields


class TestGetNestedHelper:
    """Test the _get_nested dot-notation helper independently."""

    def test_simple_key(self) -> None:
        assert _get_nested({"name": "HQ"}, "name") == "HQ"

    def test_nested_key(self) -> None:
        assert _get_nested({"address": {"country": "US"}}, "address.country") == "US"

    def test_deeply_nested(self) -> None:
        data = {"a": {"b": {"c": 42}}}
        assert _get_nested(data, "a.b.c") == 42

    def test_missing_intermediate_returns_none(self) -> None:
        assert _get_nested({"address": None}, "address.country") is None

    def test_missing_top_level_returns_none(self) -> None:
        assert _get_nested({}, "address.country") is None

    def test_non_dict_intermediate_returns_none(self) -> None:
        assert _get_nested({"address": "string"}, "address.country") is None

    def test_empty_dict_returns_none(self) -> None:
        assert _get_nested({}, "any_key") is None


# ===================================================================
# Fix 5: MissingDataAnalyzer — user location_id check
# ===================================================================


class TestFix5UserLocationIdCheck:
    """MissingDataAnalyzer should flag users missing location_id."""

    def setup_method(self) -> None:
        self.store = _make_store()
        self.analyzer = MissingDataAnalyzer()

    def teardown_method(self) -> None:
        self.store.close()

    def test_user_no_location_id_high(self) -> None:
        """User with email and name but no location_id -> HIGH MISSING_DATA."""
        user = CanonicalUser(
            canonical_id="user:noloc",
            provenance=_prov("noloc"),
            emails=["alice@example.com"],
            first_name="Alice",
            last_name="Smith",
            location_id=None,
        )
        self.store.upsert_object(user)

        decisions = self.analyzer.analyze(self.store)
        loc_decisions = [
            d for d in decisions
            if "location_id" in d.context.get("missing_fields", [])
        ]
        assert len(loc_decisions) == 1
        assert loc_decisions[0].severity == "HIGH"

    def test_user_with_email_and_location_id_no_decision(self) -> None:
        """User with email, first/last name, and location_id -> no decision."""
        user = CanonicalUser(
            canonical_id="user:complete",
            provenance=_prov("complete"),
            emails=["bob@example.com"],
            first_name="Bob",
            last_name="Jones",
            location_id="location:hq",
        )
        self.store.upsert_object(user)

        decisions = self.analyzer.analyze(self.store)
        user_decisions = [
            d for d in decisions if d.context.get("object_type") == "user"
        ]
        assert len(user_decisions) == 0

    def test_user_empty_string_location_id_high(self) -> None:
        """User with blank location_id -> flagged as missing."""
        user = CanonicalUser(
            canonical_id="user:blankloc",
            provenance=_prov("blankloc"),
            emails=["carol@example.com"],
            first_name="Carol",
            last_name="White",
            location_id="   ",
        )
        self.store.upsert_object(user)

        decisions = self.analyzer.analyze(self.store)
        loc_decisions = [
            d for d in decisions
            if "location_id" in d.context.get("missing_fields", [])
        ]
        assert len(loc_decisions) == 1


# ===================================================================
# Fix 6: Translation pattern empty-pattern handling
# ===================================================================


class TestFix6TranslationPatternEmptyPattern:
    """RoutingMapper should skip translation patterns with empty/None pattern.
    MissingDataAnalyzer should flag translation patterns with empty matching_pattern."""

    def setup_method(self) -> None:
        self.store = _make_store()

    def teardown_method(self) -> None:
        self.store.close()

    def test_routing_mapper_skips_empty_pattern(self) -> None:
        """Seed a translation_pattern with empty pattern, run RoutingMapper.map(),
        verify no mapped translation_pattern objects created."""
        tp = MigrationObject(
            canonical_id="translation_pattern:empty",
            provenance=_prov("empty-tp"),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={
                "pattern": "",
                "calledPartyTransformationMask": "+1XXX",
            },
        )
        self.store.upsert_object(tp)

        mapper = RoutingMapper()
        result = mapper.map(self.store)

        # The input object still exists but no mapped (analyzed) translation_pattern should be created
        all_tps = self.store.get_objects("translation_pattern")
        mapped_tps = [t for t in all_tps if t["status"] == "analyzed"]
        assert len(mapped_tps) == 0

    def test_routing_mapper_skips_none_pattern(self) -> None:
        """Translation pattern with None pattern field also skipped."""
        tp = MigrationObject(
            canonical_id="translation_pattern:none",
            provenance=_prov("none-tp"),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={
                "calledPartyTransformationMask": "+1XXX",
            },
        )
        self.store.upsert_object(tp)

        mapper = RoutingMapper()
        result = mapper.map(self.store)

        all_tps = self.store.get_objects("translation_pattern")
        mapped_tps = [t for t in all_tps if t["status"] == "analyzed"]
        assert len(mapped_tps) == 0

    def test_routing_mapper_processes_valid_pattern(self) -> None:
        """Translation pattern with a real pattern is still processed normally."""
        tp = MigrationObject(
            canonical_id="translation_pattern:9_1XXX",
            provenance=_prov("valid-tp"),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={
                "pattern": "9.1XXX",
                "calledPartyTransformationMask": "1XXX",
            },
        )
        self.store.upsert_object(tp)

        mapper = RoutingMapper()
        result = mapper.map(self.store)

        all_tps = self.store.get_objects("translation_pattern")
        mapped_tps = [t for t in all_tps if t["status"] == "analyzed"]
        assert len(mapped_tps) == 1

    def test_analyzer_flags_empty_matching_pattern(self) -> None:
        """MissingDataAnalyzer flags a CanonicalTranslationPattern with empty matching_pattern."""
        tp = CanonicalTranslationPattern(
            canonical_id="translation_pattern:empty_match",
            provenance=_prov("empty-match"),
            name="BadPattern",
            matching_pattern="",
            replacement_pattern="+1XXX",
        )
        self.store.upsert_object(tp)

        analyzer = MissingDataAnalyzer()
        decisions = analyzer.analyze(self.store)

        tp_decisions = [
            d for d in decisions
            if d.context.get("object_type") == "translation_pattern"
            and "matching_pattern" in d.context.get("missing_fields", [])
        ]
        assert len(tp_decisions) == 1
        assert tp_decisions[0].severity == "HIGH"

    def test_analyzer_flags_none_matching_pattern(self) -> None:
        """MissingDataAnalyzer flags matching_pattern=None."""
        tp = CanonicalTranslationPattern(
            canonical_id="translation_pattern:none_match",
            provenance=_prov("none-match"),
            name="NullPattern",
            matching_pattern=None,
            replacement_pattern="+1XXX",
        )
        self.store.upsert_object(tp)

        analyzer = MissingDataAnalyzer()
        decisions = analyzer.analyze(self.store)

        tp_decisions = [
            d for d in decisions
            if d.context.get("object_type") == "translation_pattern"
            and "matching_pattern" in d.context.get("missing_fields", [])
        ]
        assert len(tp_decisions) == 1


# ===================================================================
# Fix 10: Trunk location_id MISSING_DATA from RoutingMapper
# ===================================================================


class TestFix10TrunkMissingLocationId:
    """RoutingMapper should create MISSING_DATA decision when trunk has no
    resolvable location through the device pool chain."""

    def setup_method(self) -> None:
        self.store = _make_store()

    def teardown_method(self) -> None:
        self.store.close()

    def test_trunk_no_location_produces_missing_data(self) -> None:
        """Seed a sip_trunk with no device pool cross-refs, verify MISSING_DATA."""
        trunk = MigrationObject(
            canonical_id="sip_trunk:SBC-Orphan",
            provenance=_prov("orphan-trunk"),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={
                "name": "SBC-Orphan",
                "destinations": [
                    {"address": "sbc.example.com", "port": 5060, "sort_order": 1}
                ],
            },
        )
        self.store.upsert_object(trunk)

        mapper = RoutingMapper()
        result = mapper.map(self.store)

        no_location_decisions = [
            d for d in result.decisions
            if d.type == DecisionType.MISSING_DATA
            and d.context.get("reason") == "no_location"
        ]
        assert len(no_location_decisions) == 1
        assert no_location_decisions[0].severity == "HIGH"
        assert "SBC-Orphan" in no_location_decisions[0].summary

    def test_trunk_with_location_no_missing_location_decision(self) -> None:
        """Trunk with resolved location should NOT produce a no_location decision."""
        # Seed device pool and location for resolution chain
        dp = MigrationObject(
            canonical_id="device_pool:DP-HQ",
            provenance=_prov("dp-hq"),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={"device_pool_name": "DP-HQ"},
        )
        self.store.upsert_object(dp)

        loc = CanonicalLocation(
            canonical_id="location:HQ",
            provenance=_prov("loc-hq"),
            status=MigrationStatus.ANALYZED,
            name="HQ",
            address=LocationAddress(country="US"),
        )
        self.store.upsert_object(loc)
        self.store.add_cross_ref("device_pool:DP-HQ", "location:HQ", "device_pool_to_location")

        trunk = MigrationObject(
            canonical_id="sip_trunk:SBC-HQ",
            provenance=_prov("sbc-hq"),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={
                "name": "SBC-HQ",
                "destinations": [
                    {"address": "sbc-hq.example.com", "port": 5060, "sort_order": 1}
                ],
            },
        )
        self.store.upsert_object(trunk)
        self.store.add_cross_ref("sip_trunk:SBC-HQ", "device_pool:DP-HQ", "trunk_at_location")

        mapper = RoutingMapper()
        result = mapper.map(self.store)

        no_location_decisions = [
            d for d in result.decisions
            if d.type == DecisionType.MISSING_DATA
            and d.context.get("reason") == "no_location"
        ]
        assert len(no_location_decisions) == 0

    def test_trunk_missing_location_decision_saved_to_store(self) -> None:
        """The MISSING_DATA decision for no location is also persisted in the store."""
        trunk = MigrationObject(
            canonical_id="sip_trunk:SBC-Lost",
            provenance=_prov("lost-trunk"),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={
                "name": "SBC-Lost",
                "destinations": [
                    {"address": "lost.example.com", "port": 5060, "sort_order": 1}
                ],
            },
        )
        self.store.upsert_object(trunk)

        mapper = RoutingMapper()
        mapper.map(self.store)

        all_decisions = self.store.get_all_decisions()
        no_loc = [
            d for d in all_decisions
            if d.get("type") == "MISSING_DATA"
            and d.get("context", {}).get("reason") == "no_location"
        ]
        assert len(no_loc) == 1


# ===================================================================
# Fix 11: Route group empty gateways
# ===================================================================


class TestFix11RouteGroupEmptyGateways:
    """RoutingMapper should create MISSING_DATA when route group has no
    resolvable members. MissingDataAnalyzer should also flag empty-gateway
    route groups."""

    def setup_method(self) -> None:
        self.store = _make_store()

    def teardown_method(self) -> None:
        self.store.close()

    def test_route_group_no_members_produces_missing_data(self) -> None:
        """Route group with no cross-refs and no state trunks -> MISSING_DATA."""
        rg = MigrationObject(
            canonical_id="route_group:RG-Empty",
            provenance=_prov("rg-empty"),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={
                "name": "RG-Empty",
                "trunks": [],
            },
        )
        self.store.upsert_object(rg)

        mapper = RoutingMapper()
        result = mapper.map(self.store)

        no_gw_decisions = [
            d for d in result.decisions
            if d.type == DecisionType.MISSING_DATA
            and d.context.get("reason") == "no_gateways"
        ]
        assert len(no_gw_decisions) == 1
        assert no_gw_decisions[0].severity == "HIGH"
        assert "RG-Empty" in no_gw_decisions[0].summary

    def test_route_group_with_members_no_gateway_decision(self) -> None:
        """Route group with resolved trunk members should NOT produce no_gateways decision."""
        trunk = MigrationObject(
            canonical_id="sip_trunk:SIP-T1",
            provenance=_prov("sip-t1"),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={
                "name": "SIP-T1",
                "destinations": [
                    {"address": "gw.example.com", "port": 5060, "sort_order": 1}
                ],
            },
        )
        self.store.upsert_object(trunk)

        rg = MigrationObject(
            canonical_id="route_group:RG-Active",
            provenance=_prov("rg-active"),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={
                "name": "RG-Active",
                "trunks": [{"trunk_name": "SIP-T1", "priority": 1}],
            },
        )
        self.store.upsert_object(rg)
        self.store.add_cross_ref(
            "route_group:RG-Active", "sip_trunk:SIP-T1", "route_group_has_trunk"
        )

        mapper = RoutingMapper()
        result = mapper.map(self.store)

        no_gw_decisions = [
            d for d in result.decisions
            if d.type == DecisionType.MISSING_DATA
            and d.context.get("reason") == "no_gateways"
        ]
        assert len(no_gw_decisions) == 0

    def test_analyzer_flags_empty_local_gateways(self) -> None:
        """MissingDataAnalyzer flags a CanonicalRouteGroup with empty local_gateways."""
        rg = CanonicalRouteGroup(
            canonical_id="route_group:RG-NoGW",
            provenance=_prov("rg-nogw"),
            name="RG-NoGW",
            local_gateways=[],
        )
        self.store.upsert_object(rg)

        analyzer = MissingDataAnalyzer()
        decisions = analyzer.analyze(self.store)

        rg_decisions = [
            d for d in decisions
            if d.context.get("object_type") == "route_group"
            and "local_gateways" in d.context.get("missing_fields", [])
        ]
        assert len(rg_decisions) == 1
        assert rg_decisions[0].severity == "HIGH"

    def test_analyzer_no_decision_for_populated_gateways(self) -> None:
        """CanonicalRouteGroup with gateways should NOT be flagged."""
        rg = CanonicalRouteGroup(
            canonical_id="route_group:RG-OK",
            provenance=_prov("rg-ok"),
            name="RG-OK",
            local_gateways=[
                TrunkGatewayRef(trunk_canonical_id="trunk:SBC-1", priority=1),
            ],
        )
        self.store.upsert_object(rg)

        analyzer = MissingDataAnalyzer()
        decisions = analyzer.analyze(self.store)

        rg_decisions = [
            d for d in decisions
            if d.context.get("object_type") == "route_group"
        ]
        assert len(rg_decisions) == 0

    def test_empty_gateways_decision_saved_to_store(self) -> None:
        """The MISSING_DATA decision for no gateways is persisted in the store."""
        rg = MigrationObject(
            canonical_id="route_group:RG-Persist",
            provenance=_prov("rg-persist"),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={
                "name": "RG-Persist",
                "trunks": [],
            },
        )
        self.store.upsert_object(rg)

        mapper = RoutingMapper()
        mapper.map(self.store)

        all_decisions = self.store.get_all_decisions()
        no_gw = [
            d for d in all_decisions
            if d.get("type") == "MISSING_DATA"
            and d.get("context", {}).get("reason") == "no_gateways"
        ]
        assert len(no_gw) == 1
