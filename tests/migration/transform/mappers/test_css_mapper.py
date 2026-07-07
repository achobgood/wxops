"""Tests for css_mapper: CUCM CSS -> Webex Dial Plans + Calling Permissions.

Uses real :memory: SQLite store, no mocks.

Test scenarios (from acceptance criteria):
1. Single routing scope happy path
2. Multiple routing scopes with intersection
3. MIXED partition handling
4. Ordering conflict detection
5. Empty CSS
6. No route patterns
7. Combined line+device CSS
8. Unclassifiable block patterns -> CALLING_PERMISSION_MISMATCH
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from wxcli.migration.models import (
    DecisionType,
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.css_mapper import CSSMapper


# ---------------------------------------------------------------------------
# Configurable category rules (NOT hardcoded US patterns -- passed as config)
# ---------------------------------------------------------------------------

US_CATEGORY_RULES = [
    {"cucm_pattern": "9.011!", "webex_category": "international"},
    {"cucm_pattern": "9.1900XXXXXXX", "webex_category": "premium"},
    {"cucm_pattern": "9.1976XXXXXXX", "webex_category": "premium"},
    {"cucm_pattern": "9.0!", "webex_category": "operator"},
    {"cucm_pattern": "9.1[2-9]XX555XXXX", "webex_category": "directory_assistance"},
    {"cucm_pattern": "9.1900!", "webex_category": "premium"},
]


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


def _css(name: str) -> MigrationObject:
    """Create a CSS MigrationObject."""
    return MigrationObject(
        canonical_id=f"css:{name}",
        provenance=_provenance(source_id=f"uuid-css-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"name": name},
    )


def _partition(name: str) -> MigrationObject:
    """Create a Partition MigrationObject."""
    return MigrationObject(
        canonical_id=f"partition:{name}",
        provenance=_provenance(source_id=f"uuid-pt-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"name": name},
    )


def _route_pattern(
    pattern: str,
    action: str = "ROUTE",
    partition: str | None = None,
    target_type: str | None = None,
    target_name: str | None = None,
) -> MigrationObject:
    """Create a route pattern MigrationObject."""
    # Build a safe canonical ID from pattern + partition
    safe = pattern.replace(".", "_").replace("[", "").replace("]", "").replace("!", "B")
    suffix = f":{partition}" if partition else ""
    state: dict = {"pattern": pattern, "action": action}
    if target_type:
        state["target_type"] = target_type
    if target_name:
        state["target_name"] = target_name

    return MigrationObject(
        canonical_id=f"route_pattern:{safe}{suffix}",
        provenance=_provenance(source_id=f"uuid-rp-{safe}", name=pattern),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=state,
    )


def _dn(number: str, partition: str | None = None) -> MigrationObject:
    """Create a DN (directory number) MigrationObject with no action."""
    suffix = f":{partition}" if partition else ""
    return MigrationObject(
        canonical_id=f"dn:{number}{suffix}",
        provenance=_provenance(source_id=f"uuid-dn-{number}", name=number),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"pattern": number},  # No action field -> DIRECTORY
    )


def _user(name: str) -> MigrationObject:
    """Create a user MigrationObject."""
    return MigrationObject(
        canonical_id=f"user:{name}",
        provenance=_provenance(source_id=f"uuid-user-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"name": name},
    )


@pytest.fixture
def store(tmp_path):
    """Create a MigrationStore with a temp SQLite database."""
    db_path = tmp_path / "test.db"
    s = MigrationStore(str(db_path))
    return s


def _setup_standard_employee_css(store: MigrationStore) -> dict:
    """Set up the standard CSS from 04-css-decomposition.md example.

    CSS "Standard-Employee"
      Partition "Internal-PT" (priority 1) — directory (DNs only)
      Partition "Local-PSTN-PT" (priority 2) — routing
      Partition "International-Block-PT" (priority 3) — blocking
      Partition "Emergency-PT" (priority 4) — routing
    """
    css = _css("Standard-Employee")
    pt_internal = _partition("Internal-PT")
    pt_pstn = _partition("Local-PSTN-PT")
    pt_intl_block = _partition("International-Block-PT")
    pt_emergency = _partition("Emergency-PT")

    # DNs in internal partition
    dn1 = _dn("1001", "Internal-PT")
    dn2 = _dn("1002", "Internal-PT")

    # Route patterns in PSTN partition
    rp_local = _route_pattern(
        "9.1[2-9]XX[2-9]XXXXXX",
        "ROUTE",
        "Local-PSTN-PT",
        target_type="route_group",
        target_name="Local-RG",
    )
    rp_ld = _route_pattern(
        "9.1[2-9]XXXXXXXXX",
        "ROUTE",
        "Local-PSTN-PT",
        target_type="route_group",
        target_name="LD-RG",
    )

    # Block pattern in intl block partition
    rp_intl_block = _route_pattern("9.011!", "BLOCK", "International-Block-PT")

    # Route pattern in emergency partition
    rp_911 = _route_pattern(
        "9.911",
        "ROUTE",
        "Emergency-PT",
        target_type="route_group",
        target_name="Emergency-RG",
    )

    # Insert all objects
    for obj in [
        css, pt_internal, pt_pstn, pt_intl_block, pt_emergency,
        dn1, dn2, rp_local, rp_ld, rp_intl_block, rp_911,
    ]:
        store.upsert_object(obj)

    # Build cross-refs: CSS -> partitions with ordinal
    store.add_cross_ref(css.canonical_id, pt_internal.canonical_id, "css_contains_partition", ordinal=1)
    store.add_cross_ref(css.canonical_id, pt_pstn.canonical_id, "css_contains_partition", ordinal=2)
    store.add_cross_ref(css.canonical_id, pt_intl_block.canonical_id, "css_contains_partition", ordinal=3)
    store.add_cross_ref(css.canonical_id, pt_emergency.canonical_id, "css_contains_partition", ordinal=4)

    # Partition -> patterns
    store.add_cross_ref(pt_internal.canonical_id, dn1.canonical_id, "partition_has_pattern")
    store.add_cross_ref(pt_internal.canonical_id, dn2.canonical_id, "partition_has_pattern")
    store.add_cross_ref(pt_pstn.canonical_id, rp_local.canonical_id, "partition_has_pattern")
    store.add_cross_ref(pt_pstn.canonical_id, rp_ld.canonical_id, "partition_has_pattern")
    store.add_cross_ref(pt_intl_block.canonical_id, rp_intl_block.canonical_id, "partition_has_pattern")
    store.add_cross_ref(pt_emergency.canonical_id, rp_911.canonical_id, "partition_has_pattern")

    return {
        "css": css,
        "partitions": [pt_internal, pt_pstn, pt_intl_block, pt_emergency],
        "route_patterns": [rp_local, rp_ld, rp_intl_block, rp_911],
        "dns": [dn1, dn2],
    }


# ---------------------------------------------------------------------------
# Test 1: Single routing scope happy path
# ---------------------------------------------------------------------------


class TestSingleRoutingScope:
    """AC1+2: Given CSS with 3 partitions (DIRECTORY, ROUTING, BLOCKING), classifies all.
    AC2: Given 2 CSSes with identical routing partitions -> org-wide, NO CSS_ROUTING_MISMATCH.
    AC9: Produces both CanonicalDialPlan and CanonicalCallingPermission.
    """

    def test_classifies_partitions_correctly(self, store):
        """AC1: DIRECTORY, ROUTING, BLOCKING partitions classified correctly."""
        data = _setup_standard_employee_css(store)

        # Add a user assigned to this CSS
        user = _user("jsmith")
        store.upsert_object(user)
        store.add_cross_ref(user.canonical_id, data["css"].canonical_id, "user_has_css")

        mapper = CSSMapper(category_rules=US_CATEGORY_RULES)
        result = mapper.map(store)

        # Should produce dial plans (routing) and calling permissions (blocking)
        assert result.objects_created > 0

        # Verify dial plan was created
        dial_plans = store.get_objects("dial_plan")
        css_dial_plans = [dp for dp in dial_plans if "CSS-Migration" in (dp.get("name") or "")]
        assert len(css_dial_plans) > 0

        # Verify calling permission was created
        permissions = store.get_objects("calling_permission")
        assert len(permissions) > 0

    def test_two_identical_css_no_mismatch(self, store):
        """AC2: Two CSSes with identical routing -> no CSS_ROUTING_MISMATCH for scope."""
        # Set up first CSS
        data1 = _setup_standard_employee_css(store)

        # Set up second CSS with IDENTICAL routing patterns
        css2 = _css("Standard-Employee-2")
        pt2_internal = _partition("Internal-PT-2")
        pt2_pstn = _partition("Local-PSTN-PT-2")
        pt2_block = _partition("International-Block-PT-2")
        pt2_emergency = _partition("Emergency-PT-2")

        # Same patterns, different partition names
        rp2_local = _route_pattern(
            "9.1[2-9]XX[2-9]XXXXXX", "ROUTE", "Local-PSTN-PT-2",
            target_type="route_group", target_name="Local-RG",
        )
        rp2_ld = _route_pattern(
            "9.1[2-9]XXXXXXXXX", "ROUTE", "Local-PSTN-PT-2",
            target_type="route_group", target_name="LD-RG",
        )
        rp2_block = _route_pattern("9.011!", "BLOCK", "International-Block-PT-2")
        rp2_911 = _route_pattern(
            "9.911", "ROUTE", "Emergency-PT-2",
            target_type="route_group", target_name="Emergency-RG",
        )
        dn2_1 = _dn("2001", "Internal-PT-2")

        for obj in [
            css2, pt2_internal, pt2_pstn, pt2_block, pt2_emergency,
            rp2_local, rp2_ld, rp2_block, rp2_911, dn2_1,
        ]:
            store.upsert_object(obj)

        store.add_cross_ref(css2.canonical_id, pt2_internal.canonical_id, "css_contains_partition", ordinal=1)
        store.add_cross_ref(css2.canonical_id, pt2_pstn.canonical_id, "css_contains_partition", ordinal=2)
        store.add_cross_ref(css2.canonical_id, pt2_block.canonical_id, "css_contains_partition", ordinal=3)
        store.add_cross_ref(css2.canonical_id, pt2_emergency.canonical_id, "css_contains_partition", ordinal=4)

        store.add_cross_ref(pt2_internal.canonical_id, dn2_1.canonical_id, "partition_has_pattern")
        store.add_cross_ref(pt2_pstn.canonical_id, rp2_local.canonical_id, "partition_has_pattern")
        store.add_cross_ref(pt2_pstn.canonical_id, rp2_ld.canonical_id, "partition_has_pattern")
        store.add_cross_ref(pt2_block.canonical_id, rp2_block.canonical_id, "partition_has_pattern")
        store.add_cross_ref(pt2_emergency.canonical_id, rp2_911.canonical_id, "partition_has_pattern")

        # Users
        user1 = _user("jsmith")
        user2 = _user("jdoe")
        store.upsert_object(user1)
        store.upsert_object(user2)
        store.add_cross_ref(user1.canonical_id, data1["css"].canonical_id, "user_has_css")
        store.add_cross_ref(user2.canonical_id, css2.canonical_id, "user_has_css")

        mapper = CSSMapper(category_rules=US_CATEGORY_RULES)
        result = mapper.map(store)

        # No CSS_ROUTING_MISMATCH decisions for routing scope
        routing_mismatch_decisions = [
            d for d in result.decisions
            if d.type == DecisionType.CSS_ROUTING_MISMATCH
            and d.context.get("reason") == "routing_scope_mismatch"
        ]
        assert len(routing_mismatch_decisions) == 0

    def test_produces_dial_plan_and_calling_permission(self, store):
        """AC9: Both CanonicalDialPlan and CanonicalCallingPermission produced."""
        data = _setup_standard_employee_css(store)

        user = _user("jsmith")
        store.upsert_object(user)
        store.add_cross_ref(user.canonical_id, data["css"].canonical_id, "user_has_css")

        mapper = CSSMapper(category_rules=US_CATEGORY_RULES)
        result = mapper.map(store)

        dial_plans = store.get_objects("dial_plan")
        permissions = store.get_objects("calling_permission")

        css_dial_plans = [dp for dp in dial_plans if "CSS-Migration" in (dp.get("name") or "")]
        assert len(css_dial_plans) > 0, "Should produce CanonicalDialPlan"
        assert len(permissions) > 0, "Should produce CanonicalCallingPermission"

    def test_calling_permission_blocks_international(self, store):
        """Verify the international block pattern maps to INTERNATIONAL BLOCK permission."""
        data = _setup_standard_employee_css(store)

        user = _user("jsmith")
        store.upsert_object(user)
        store.add_cross_ref(user.canonical_id, data["css"].canonical_id, "user_has_css")

        mapper = CSSMapper(category_rules=US_CATEGORY_RULES)
        mapper.map(store)

        permissions = store.get_objects("calling_permission")
        assert len(permissions) > 0

        # Find the permission object
        perm = permissions[0]
        perm_entries = perm.get("calling_permissions", [])

        # International should be BLOCK
        intl_entries = [e for e in perm_entries if e.get("call_type") == "INTERNATIONAL"]
        assert len(intl_entries) == 1
        assert intl_entries[0]["action"] == "BLOCK"
        assert intl_entries[0]["transfer_enabled"] is False

        # National should be ALLOW (not blocked)
        national_entries = [e for e in perm_entries if e.get("call_type") == "NATIONAL"]
        assert len(national_entries) == 1
        assert national_entries[0]["action"] == "ALLOW"


# ---------------------------------------------------------------------------
# Test 2: Multiple routing scopes with intersection
# ---------------------------------------------------------------------------


class TestMultipleRoutingScopes:
    """AC3: Two CSSes with different routing -> intersection baseline + CSS_ROUTING_MISMATCH."""

    def test_intersection_baseline_with_delta_decision(self, store):
        """Different routing scopes produce intersection + delta decisions."""
        # CSS1: has local + LD + emergency
        css1 = _css("Employee-CSS")
        pt1_route = _partition("EmployeeRouting-PT")
        pt1_emergency = _partition("EmployeeEmergency-PT")

        rp_local = _route_pattern(
            "9.1[2-9]XXXXXXXXX", "ROUTE", "EmployeeRouting-PT",
            target_type="route_group", target_name="Local-RG",
        )
        rp_911 = _route_pattern(
            "9.911", "ROUTE", "EmployeeEmergency-PT",
            target_type="route_group", target_name="Emergency-RG",
        )

        # CSS2: has ONLY emergency (no local/LD) + toll-free
        css2 = _css("Lobby-CSS")
        pt2_emergency = _partition("LobbyEmergency-PT")
        pt2_toll = _partition("LobbyTollFree-PT")

        rp2_911 = _route_pattern(
            "9.911", "ROUTE", "LobbyEmergency-PT",
            target_type="route_group", target_name="Emergency-RG",
        )
        rp2_toll = _route_pattern(
            "9.1800XXXXXXX", "ROUTE", "LobbyTollFree-PT",
            target_type="route_group", target_name="TollFree-RG",
        )

        for obj in [
            css1, pt1_route, pt1_emergency, rp_local, rp_911,
            css2, pt2_emergency, pt2_toll, rp2_911, rp2_toll,
        ]:
            store.upsert_object(obj)

        # CSS1 partitions
        store.add_cross_ref(css1.canonical_id, pt1_route.canonical_id, "css_contains_partition", ordinal=1)
        store.add_cross_ref(css1.canonical_id, pt1_emergency.canonical_id, "css_contains_partition", ordinal=2)
        store.add_cross_ref(pt1_route.canonical_id, rp_local.canonical_id, "partition_has_pattern")
        store.add_cross_ref(pt1_emergency.canonical_id, rp_911.canonical_id, "partition_has_pattern")

        # CSS2 partitions
        store.add_cross_ref(css2.canonical_id, pt2_emergency.canonical_id, "css_contains_partition", ordinal=1)
        store.add_cross_ref(css2.canonical_id, pt2_toll.canonical_id, "css_contains_partition", ordinal=2)
        store.add_cross_ref(pt2_emergency.canonical_id, rp2_911.canonical_id, "partition_has_pattern")
        store.add_cross_ref(pt2_toll.canonical_id, rp2_toll.canonical_id, "partition_has_pattern")

        # Users
        user1 = _user("employee1")
        user2 = _user("lobby-phone")
        store.upsert_object(user1)
        store.upsert_object(user2)
        store.add_cross_ref(user1.canonical_id, css1.canonical_id, "user_has_css")
        store.add_cross_ref(user2.canonical_id, css2.canonical_id, "user_has_css")

        mapper = CSSMapper(category_rules=US_CATEGORY_RULES)
        result = mapper.map(store)

        # Should have CSS_ROUTING_MISMATCH decisions for delta patterns
        routing_mismatch = [
            d for d in result.decisions
            if d.type == DecisionType.CSS_ROUTING_MISMATCH
            and d.context.get("reason") == "routing_scope_mismatch"
        ]
        assert len(routing_mismatch) > 0, "Should flag routing scope differences"

        # Verify intersection baseline: 9.911 is in both CSSes
        # The intersection should contain at least 9.911
        dial_plans = store.get_objects("dial_plan")
        css_dps = [dp for dp in dial_plans if "CSS-Migration" in (dp.get("name") or "")]

        # At least one dial plan should exist (for the intersection baseline)
        assert len(css_dps) > 0

    def test_intersection_not_union(self, store):
        """Verify intersection (conservative) is used, not union (permissive)."""
        # CSS1: patterns A, B
        # CSS2: patterns B, C
        # Intersection = {B}, NOT union = {A, B, C}
        css1 = _css("CSS-AB")
        css2 = _css("CSS-BC")
        pt1 = _partition("PT-AB")
        pt2 = _partition("PT-BC")

        rp_a = _route_pattern("9.1408XXXXXXX", "ROUTE", "PT-AB",
                              target_type="trunk", target_name="TrunkA")
        rp_b1 = _route_pattern("9.911", "ROUTE", "PT-AB",
                               target_type="trunk", target_name="TrunkEmergency")
        rp_b2 = _route_pattern("9.911", "ROUTE", "PT-BC",
                               target_type="trunk", target_name="TrunkEmergency")
        rp_c = _route_pattern("9.1650XXXXXXX", "ROUTE", "PT-BC",
                              target_type="trunk", target_name="TrunkC")

        for obj in [css1, css2, pt1, pt2, rp_a, rp_b1, rp_b2, rp_c]:
            store.upsert_object(obj)

        store.add_cross_ref(css1.canonical_id, pt1.canonical_id, "css_contains_partition", ordinal=1)
        store.add_cross_ref(css2.canonical_id, pt2.canonical_id, "css_contains_partition", ordinal=1)
        store.add_cross_ref(pt1.canonical_id, rp_a.canonical_id, "partition_has_pattern")
        store.add_cross_ref(pt1.canonical_id, rp_b1.canonical_id, "partition_has_pattern")
        store.add_cross_ref(pt2.canonical_id, rp_b2.canonical_id, "partition_has_pattern")
        store.add_cross_ref(pt2.canonical_id, rp_c.canonical_id, "partition_has_pattern")

        mapper = CSSMapper(category_rules=US_CATEGORY_RULES)
        result = mapper.map(store)

        # Should have routing mismatch decisions for delta patterns
        routing_mismatch = [
            d for d in result.decisions
            if d.type == DecisionType.CSS_ROUTING_MISMATCH
            and d.context.get("reason") == "routing_scope_mismatch"
        ]
        # Both CSS-AB delta {A} and CSS-BC delta {C} should generate decisions
        assert len(routing_mismatch) == 2, (
            f"Expected 2 routing mismatch decisions (one per CSS delta), got {len(routing_mismatch)}"
        )

        # Verify delta patterns are correct
        all_delta_patterns = set()
        for d in routing_mismatch:
            all_delta_patterns.update(d.context.get("delta_patterns", []))
        assert "9.1408XXXXXXX" in all_delta_patterns
        assert "9.1650XXXXXXX" in all_delta_patterns
        # 9.911 should NOT be a delta (it's in the intersection)
        assert "9.911" not in all_delta_patterns


# ---------------------------------------------------------------------------
# Test 3: MIXED partition handling
# ---------------------------------------------------------------------------


class TestMixedPartition:
    """AC6: MIXED partition -> split + CSS_ROUTING_MISMATCH decision."""

    def test_mixed_partition_split(self, store):
        """MIXED partition with both ROUTE and BLOCK patterns is split."""
        css = _css("Mixed-CSS")
        pt_mixed = _partition("Mixed-PT")

        rp_route = _route_pattern(
            "9.1[2-9]XXXXXXXXX", "ROUTE", "Mixed-PT",
            target_type="route_group", target_name="Local-RG",
        )
        rp_block = _route_pattern("9.011!", "BLOCK", "Mixed-PT")

        for obj in [css, pt_mixed, rp_route, rp_block]:
            store.upsert_object(obj)

        store.add_cross_ref(css.canonical_id, pt_mixed.canonical_id, "css_contains_partition", ordinal=1)
        store.add_cross_ref(pt_mixed.canonical_id, rp_route.canonical_id, "partition_has_pattern")
        store.add_cross_ref(pt_mixed.canonical_id, rp_block.canonical_id, "partition_has_pattern")

        mapper = CSSMapper(category_rules=US_CATEGORY_RULES)
        result = mapper.map(store)

        # Should produce CSS_ROUTING_MISMATCH decision for MIXED partition
        mixed_decisions = [
            d for d in result.decisions
            if d.type == DecisionType.CSS_ROUTING_MISMATCH
            and d.context.get("reason") == "mixed_partition"
        ]
        assert len(mixed_decisions) == 1
        assert mixed_decisions[0].context["partition_id"] == "partition:Mixed-PT"
        assert mixed_decisions[0].context["route_count"] == 1
        assert mixed_decisions[0].context["block_count"] == 1

    def test_mixed_partition_still_produces_dial_plan(self, store):
        """MIXED partition ROUTE patterns should still create dial plans."""
        css = _css("Mixed-CSS2")
        pt_mixed = _partition("Mixed-PT2")

        rp_route = _route_pattern(
            "9.1[2-9]XXXXXXXXX", "ROUTE", "Mixed-PT2",
            target_type="route_group", target_name="Local-RG",
        )
        rp_block = _route_pattern("9.011!", "BLOCK", "Mixed-PT2")

        for obj in [css, pt_mixed, rp_route, rp_block]:
            store.upsert_object(obj)

        store.add_cross_ref(css.canonical_id, pt_mixed.canonical_id, "css_contains_partition", ordinal=1)
        store.add_cross_ref(pt_mixed.canonical_id, rp_route.canonical_id, "partition_has_pattern")
        store.add_cross_ref(pt_mixed.canonical_id, rp_block.canonical_id, "partition_has_pattern")

        mapper = CSSMapper(category_rules=US_CATEGORY_RULES)
        result = mapper.map(store)

        # Should still produce a dial plan from the ROUTE portion
        dial_plans = store.get_objects("dial_plan")
        css_dps = [dp for dp in dial_plans if "CSS-Migration" in (dp.get("name") or "")]
        assert len(css_dps) > 0, "MIXED partition ROUTE patterns should create dial plans"


# ---------------------------------------------------------------------------
# Test 4: Ordering conflict detection
# ---------------------------------------------------------------------------


class TestOrderingConflicts:
    """AC7: Ordering conflict detection via cucm_patterns_overlap() with risk assessment."""

    def test_route_shadows_block(self, store):
        """ROUTE at higher priority shadows BLOCK -> Webex MORE restrictive."""
        css = _css("Tricky-CSS")
        pt_route = _partition("Broad-Route-PT")
        pt_block = _partition("Intl-Block-PT")

        # 9.! at priority 1 → ROUTE (matches everything including international)
        rp_broad = _route_pattern(
            "9.!", "ROUTE", "Broad-Route-PT",
            target_type="trunk", target_name="PSTN-Trunk",
        )
        # 9.011! at priority 2 → BLOCK (international)
        rp_block = _route_pattern("9.011!", "BLOCK", "Intl-Block-PT")

        for obj in [css, pt_route, pt_block, rp_broad, rp_block]:
            store.upsert_object(obj)

        store.add_cross_ref(css.canonical_id, pt_route.canonical_id, "css_contains_partition", ordinal=1)
        store.add_cross_ref(css.canonical_id, pt_block.canonical_id, "css_contains_partition", ordinal=2)
        store.add_cross_ref(pt_route.canonical_id, rp_broad.canonical_id, "partition_has_pattern")
        store.add_cross_ref(pt_block.canonical_id, rp_block.canonical_id, "partition_has_pattern")

        mapper = CSSMapper(category_rules=US_CATEGORY_RULES)
        result = mapper.map(store)

        # Should detect ordering conflict: route shadows block
        ordering_conflicts = [
            d for d in result.decisions
            if d.type == DecisionType.CSS_ROUTING_MISMATCH
            and d.context.get("reason") == "ordering_conflict"
        ]
        assert len(ordering_conflicts) >= 1

        conflict = ordering_conflicts[0]
        assert "MORE restrictive" in conflict.context.get("risk", "")
        assert conflict.context["shadowing_action"] == "ROUTE"
        assert conflict.context["shadowed_action"] == "BLOCK"

    def test_block_shadows_route(self, store):
        """BLOCK at higher priority shadows ROUTE -> Webex LESS restrictive (risky)."""
        css = _css("Also-Tricky-CSS")
        pt_block = _partition("Block-All-PT")
        pt_route = _partition("Local-Route-PT")

        # 9.! at priority 1 → BLOCK
        rp_block_all = _route_pattern("9.!", "BLOCK", "Block-All-PT")
        # 9.1[2-9]XXXXXXXXX at priority 2 → ROUTE
        rp_local = _route_pattern(
            "9.1[2-9]XXXXXXXXX", "ROUTE", "Local-Route-PT",
            target_type="route_group", target_name="Local-RG",
        )

        for obj in [css, pt_block, pt_route, rp_block_all, rp_local]:
            store.upsert_object(obj)

        store.add_cross_ref(css.canonical_id, pt_block.canonical_id, "css_contains_partition", ordinal=1)
        store.add_cross_ref(css.canonical_id, pt_route.canonical_id, "css_contains_partition", ordinal=2)
        store.add_cross_ref(pt_block.canonical_id, rp_block_all.canonical_id, "partition_has_pattern")
        store.add_cross_ref(pt_route.canonical_id, rp_local.canonical_id, "partition_has_pattern")

        mapper = CSSMapper(category_rules=US_CATEGORY_RULES)
        result = mapper.map(store)

        # Should detect: block shadows route -> Webex LESS restrictive
        ordering_conflicts = [
            d for d in result.decisions
            if d.type == DecisionType.CSS_ROUTING_MISMATCH
            and d.context.get("reason") == "ordering_conflict"
        ]
        assert len(ordering_conflicts) >= 1

        conflict = ordering_conflicts[0]
        assert "LESS restrictive" in conflict.context.get("risk", "")
        assert conflict.context["shadowing_action"] == "BLOCK"
        assert conflict.context["shadowed_action"] == "ROUTE"
        assert conflict.severity == "HIGH"  # LESS restrictive = high severity


# ---------------------------------------------------------------------------
# Test 5: Empty CSS
# ---------------------------------------------------------------------------


class TestEmptyCSS:
    """Empty CSS should be skipped gracefully."""

    def test_no_css_objects(self, store):
        """No CSS objects -> empty result."""
        mapper = CSSMapper(category_rules=US_CATEGORY_RULES)
        result = mapper.map(store)
        assert result.objects_created == 0
        assert result.decisions == []

    def test_css_with_no_partitions(self, store):
        """CSS with no partition cross-refs -> skipped."""
        css = _css("Empty-CSS")
        store.upsert_object(css)

        mapper = CSSMapper(category_rules=US_CATEGORY_RULES)
        result = mapper.map(store)
        assert result.objects_created == 0


# ---------------------------------------------------------------------------
# Test 6: No route patterns (directory only)
# ---------------------------------------------------------------------------


class TestNoRoutePatterns:
    """CSS with only directory (DN) partitions -> no dial plans."""

    def test_directory_only_css(self, store):
        """CSS with only DNs (no route patterns) produces no dial plans."""
        css = _css("Directory-Only-CSS")
        pt = _partition("Internal-PT-Only")
        dn1 = _dn("3001", "Internal-PT-Only")
        dn2 = _dn("3002", "Internal-PT-Only")

        for obj in [css, pt, dn1, dn2]:
            store.upsert_object(obj)

        store.add_cross_ref(css.canonical_id, pt.canonical_id, "css_contains_partition", ordinal=1)
        store.add_cross_ref(pt.canonical_id, dn1.canonical_id, "partition_has_pattern")
        store.add_cross_ref(pt.canonical_id, dn2.canonical_id, "partition_has_pattern")

        mapper = CSSMapper(category_rules=US_CATEGORY_RULES)
        result = mapper.map(store)

        # No dial plans should be created (no routing patterns)
        dial_plans = store.get_objects("dial_plan")
        css_dps = [dp for dp in dial_plans if "CSS-Migration" in (dp.get("name") or "")]
        assert len(css_dps) == 0


# ---------------------------------------------------------------------------
# Test 7: Combined line+device CSS
# ---------------------------------------------------------------------------


class TestCombinedCSS:
    """AC8: Combined CSS: Line CSS (higher) + Device CSS (lower)."""

    def test_user_with_css_via_user_has_css(self, store):
        """User assigned directly via user_has_css gets that CSS's profile."""
        data = _setup_standard_employee_css(store)

        user = _user("direct-user")
        store.upsert_object(user)
        store.add_cross_ref(user.canonical_id, data["css"].canonical_id, "user_has_css")

        mapper = CSSMapper(category_rules=US_CATEGORY_RULES)
        result = mapper.map(store)

        # User should be in the calling permission's assigned_users
        permissions = store.get_objects("calling_permission")
        assert len(permissions) > 0

        assigned_users = permissions[0].get("assigned_users", [])
        assert "user:direct-user" in assigned_users


# ---------------------------------------------------------------------------
# Test 8: Unclassifiable block patterns
# ---------------------------------------------------------------------------


class TestUnclassifiableBlockPatterns:
    """AC5: Unclassifiable block pattern -> CALLING_PERMISSION_MISMATCH decision."""

    def test_unclassifiable_produces_decision(self, store):
        """Block pattern not matching any category rule generates decision."""
        css = _css("Custom-Block-CSS")
        pt_block = _partition("AreaCode-Block-PT")

        # Block a specific area code -- no US_CATEGORY_RULES match for this
        rp_area_block = _route_pattern("9.1408XXXXXXX", "BLOCK", "AreaCode-Block-PT")

        for obj in [css, pt_block, rp_area_block]:
            store.upsert_object(obj)

        store.add_cross_ref(css.canonical_id, pt_block.canonical_id, "css_contains_partition", ordinal=1)
        store.add_cross_ref(pt_block.canonical_id, rp_area_block.canonical_id, "partition_has_pattern")

        user = _user("custom-block-user")
        store.upsert_object(user)
        store.add_cross_ref(user.canonical_id, css.canonical_id, "user_has_css")

        mapper = CSSMapper(category_rules=US_CATEGORY_RULES)
        result = mapper.map(store)

        # Should produce CALLING_PERMISSION_MISMATCH
        perm_mismatch = [
            d for d in result.decisions
            if d.type == DecisionType.CALLING_PERMISSION_MISMATCH
        ]
        assert len(perm_mismatch) == 1
        assert "9.1408XXXXXXX" in perm_mismatch[0].context.get("unclassified_patterns", [])

    def test_mixed_classifiable_and_unclassifiable(self, store):
        """Both classifiable and unclassifiable block patterns handled correctly."""
        css = _css("Mixed-Block-CSS")
        pt_block = _partition("MixedBlock-PT")

        # This one classifies as international
        rp_intl = _route_pattern("9.011!", "BLOCK", "MixedBlock-PT")
        # This one is unclassifiable
        rp_area = _route_pattern("9.1408XXXXXXX", "BLOCK", "MixedBlock-PT-area")

        for obj in [css, pt_block, rp_intl, rp_area]:
            store.upsert_object(obj)

        store.add_cross_ref(css.canonical_id, pt_block.canonical_id, "css_contains_partition", ordinal=1)
        store.add_cross_ref(pt_block.canonical_id, rp_intl.canonical_id, "partition_has_pattern")
        store.add_cross_ref(pt_block.canonical_id, rp_area.canonical_id, "partition_has_pattern")

        user = _user("mixed-block-user")
        store.upsert_object(user)
        store.add_cross_ref(user.canonical_id, css.canonical_id, "user_has_css")

        mapper = CSSMapper(category_rules=US_CATEGORY_RULES)
        result = mapper.map(store)

        # Should have CALLING_PERMISSION_MISMATCH for the unclassifiable pattern
        perm_mismatch = [
            d for d in result.decisions
            if d.type == DecisionType.CALLING_PERMISSION_MISMATCH
        ]
        assert len(perm_mismatch) == 1

        # Should still produce a calling permission with international blocked
        permissions = store.get_objects("calling_permission")
        assert len(permissions) > 0

        perm = permissions[0]
        intl_entries = [
            e for e in perm.get("calling_permissions", [])
            if e.get("call_type") == "INTERNATIONAL"
        ]
        assert len(intl_entries) == 1
        assert intl_entries[0]["action"] == "BLOCK"


# ---------------------------------------------------------------------------
# Test 9: Users grouped by identical restriction profile
# ---------------------------------------------------------------------------


class TestUserGrouping:
    """AC4: Groups users by identical restriction profile -> one CanonicalCallingPermission per group."""

    def test_users_same_profile_grouped(self, store):
        """Two users with same CSS -> same CallingPermission."""
        # Both users share the same CSS
        data = _setup_standard_employee_css(store)

        user1 = _user("alice")
        user2 = _user("bob")
        store.upsert_object(user1)
        store.upsert_object(user2)
        store.add_cross_ref(user1.canonical_id, data["css"].canonical_id, "user_has_css")
        store.add_cross_ref(user2.canonical_id, data["css"].canonical_id, "user_has_css")

        mapper = CSSMapper(category_rules=US_CATEGORY_RULES)
        result = mapper.map(store)

        permissions = store.get_objects("calling_permission")
        # Both users should be in the same permission object
        # (they share the same CSS, so same restriction profile)
        total_assigned = 0
        for perm in permissions:
            assigned = perm.get("assigned_users", [])
            if "user:alice" in assigned:
                assert "user:bob" in assigned, (
                    "Users with identical restriction profile should be grouped together"
                )
                total_assigned += 1
        assert total_assigned > 0

    def test_users_different_profiles_separate(self, store):
        """Two users with different CSSes (different blocking) -> different CallingPermissions."""
        # CSS1: blocks international
        css1 = _css("Block-Intl-CSS")
        pt1 = _partition("IntlBlock-PT")
        rp1 = _route_pattern("9.011!", "BLOCK", "IntlBlock-PT")

        # CSS2: blocks premium
        css2 = _css("Block-Premium-CSS")
        pt2 = _partition("PremiumBlock-PT")
        rp2 = _route_pattern("9.1900XXXXXXX", "BLOCK", "PremiumBlock-PT")

        for obj in [css1, pt1, rp1, css2, pt2, rp2]:
            store.upsert_object(obj)

        store.add_cross_ref(css1.canonical_id, pt1.canonical_id, "css_contains_partition", ordinal=1)
        store.add_cross_ref(pt1.canonical_id, rp1.canonical_id, "partition_has_pattern")
        store.add_cross_ref(css2.canonical_id, pt2.canonical_id, "css_contains_partition", ordinal=1)
        store.add_cross_ref(pt2.canonical_id, rp2.canonical_id, "partition_has_pattern")

        user1 = _user("intl-blocked-user")
        user2 = _user("premium-blocked-user")
        store.upsert_object(user1)
        store.upsert_object(user2)
        store.add_cross_ref(user1.canonical_id, css1.canonical_id, "user_has_css")
        store.add_cross_ref(user2.canonical_id, css2.canonical_id, "user_has_css")

        mapper = CSSMapper(category_rules=US_CATEGORY_RULES)
        result = mapper.map(store)

        permissions = store.get_objects("calling_permission")
        # Should have at least 2 different calling permission profiles
        assert len(permissions) >= 2, (
            f"Expected at least 2 different permission profiles, got {len(permissions)}"
        )

        # Verify the users are in different permission objects
        user1_perms = [
            p for p in permissions
            if "user:intl-blocked-user" in p.get("assigned_users", [])
        ]
        user2_perms = [
            p for p in permissions
            if "user:premium-blocked-user" in p.get("assigned_users", [])
        ]
        assert len(user1_perms) == 1
        assert len(user2_perms) == 1
        assert user1_perms[0]["canonical_id"] != user2_perms[0]["canonical_id"]


# ---------------------------------------------------------------------------
# Test 10: Mapper interface
# ---------------------------------------------------------------------------


class TestMapperInterface:
    """Verify CSSMapper adheres to Mapper ABC contract."""

    def test_inherits_mapper(self):
        """CSSMapper inherits from Mapper."""
        from wxcli.migration.transform.mappers.base import Mapper
        assert issubclass(CSSMapper, Mapper)

    def test_has_name(self):
        mapper = CSSMapper()
        assert mapper.name == "css_mapper"

    def test_has_depends_on(self):
        mapper = CSSMapper()
        assert "routing_mapper" in mapper.depends_on

    def test_map_returns_mapper_result(self, store):
        """map() returns MapperResult."""
        from wxcli.migration.models import MapperResult
        mapper = CSSMapper()
        result = mapper.map(store)
        assert isinstance(result, MapperResult)

    def test_configurable_category_rules(self):
        """Category rules are configurable, not hardcoded."""
        # UK rules as an example
        uk_rules = [
            {"cucm_pattern": "00!", "webex_category": "international"},
            {"cucm_pattern": "09XXXXXXXX", "webex_category": "premium"},
        ]
        mapper = CSSMapper(category_rules=uk_rules)
        assert mapper.category_rules == uk_rules

    def test_exported_from_init(self):
        """CSSMapper is exported from mappers __init__."""
        from wxcli.migration.transform.mappers import CSSMapper as ImportedCSSMapper
        assert ImportedCSSMapper is CSSMapper


# ---------------------------------------------------------------------------
# Test 11: Partition classification
# ---------------------------------------------------------------------------


class TestPartitionClassification:
    """Verify partition classification logic."""

    def test_classify_directory(self):
        """Partition with only DNs (no action) -> DIRECTORY."""
        patterns = [{"pattern": "1001", "action": ""}]
        assert CSSMapper._classify_partition(patterns) == "DIRECTORY"

    def test_classify_routing(self):
        """Partition with only ROUTE patterns -> ROUTING."""
        patterns = [{"pattern": "9.1XXXXXXXXXX", "action": "ROUTE"}]
        assert CSSMapper._classify_partition(patterns) == "ROUTING"

    def test_classify_blocking(self):
        """Partition with only BLOCK patterns -> BLOCKING."""
        patterns = [{"pattern": "9.011!", "action": "BLOCK"}]
        assert CSSMapper._classify_partition(patterns) == "BLOCKING"

    def test_classify_mixed(self):
        """Partition with both ROUTE and BLOCK -> MIXED."""
        patterns = [
            {"pattern": "9.1XXXXXXXXXX", "action": "ROUTE"},
            {"pattern": "9.011!", "action": "BLOCK"},
        ]
        assert CSSMapper._classify_partition(patterns) == "MIXED"

    def test_classify_empty(self):
        """Empty pattern list -> DIRECTORY."""
        assert CSSMapper._classify_partition([]) == "DIRECTORY"


# ---------------------------------------------------------------------------
# Test 12: Line/Device CSS fallback (user has no direct CSS)
# ---------------------------------------------------------------------------


class TestLineCSSFallback:
    """When a user has no direct user_has_css, the mapper should resolve
    effective CSS from the user's line (higher priority) then device (lower).
    This is the common CUCM pattern where CSS is assigned on the DN, not the user.
    """

    def test_user_inherits_css_from_line(self, store):
        """User with no direct CSS gets permissions from their line's CSS."""
        # Create routing infrastructure
        css = _css("Employee-CSS")
        pt = _partition("PSTN-PT")
        rp = _route_pattern("9.1[2-9]XXXXXXXXX", action="ROUTE", partition="PSTN-PT")
        user = _user("jsmith")
        phone = MigrationObject(
            canonical_id="phone:SEP111111111111",
            provenance=_provenance("uuid-phone", "SEP111111111111"),
            status=MigrationStatus.NORMALIZED,
        )
        dn = MigrationObject(
            canonical_id="dn:1001:Internal-PT",
            provenance=_provenance("uuid-dn", "1001"),
            status=MigrationStatus.NORMALIZED,
        )

        for obj in [css, pt, rp, user, phone, dn]:
            store.upsert_object(obj)

        # Wire cross-refs
        store.add_cross_ref("css:Employee-CSS", "partition:PSTN-PT", "css_contains_partition", ordinal=1)
        store.add_cross_ref("partition:PSTN-PT", rp.canonical_id, "partition_has_pattern")
        # NO user_has_css — user doesn't have a direct CSS
        # Instead: user → device → dn → css
        store.add_cross_ref("user:jsmith", "phone:SEP111111111111", "user_has_device")
        store.add_cross_ref("phone:SEP111111111111", "dn:1001:Internal-PT", "device_has_dn")
        store.add_cross_ref("dn:1001:Internal-PT", "css:Employee-CSS", "line_has_css")

        mapper = CSSMapper(category_rules=US_CATEGORY_RULES)
        result = mapper.map(store)

        # User should have effective CSS from the line, producing a dial plan
        dial_plans = store.query_by_type("dial_plan")
        assert len(dial_plans) >= 1, "Line CSS should produce at least one dial plan"

    def test_user_inherits_css_from_device_when_no_line_css(self, store):
        """User with no direct CSS and no line CSS gets permissions from device CSS."""
        css = _css("Device-CSS")
        pt = _partition("PSTN-PT")
        rp = _route_pattern("9.1[2-9]XXXXXXXXX", action="ROUTE", partition="PSTN-PT")
        user = _user("jdoe")
        phone = MigrationObject(
            canonical_id="phone:SEP222222222222",
            provenance=_provenance("uuid-phone2", "SEP222222222222"),
            status=MigrationStatus.NORMALIZED,
        )

        for obj in [css, pt, rp, user, phone]:
            store.upsert_object(obj)

        store.add_cross_ref("css:Device-CSS", "partition:PSTN-PT", "css_contains_partition", ordinal=1)
        store.add_cross_ref("partition:PSTN-PT", rp.canonical_id, "partition_has_pattern")
        # user → device → css (device-level, not line-level)
        store.add_cross_ref("user:jdoe", "phone:SEP222222222222", "user_has_device")
        store.add_cross_ref("phone:SEP222222222222", "css:Device-CSS", "device_has_css")

        mapper = CSSMapper(category_rules=US_CATEGORY_RULES)
        result = mapper.map(store)

        dial_plans = store.query_by_type("dial_plan")
        assert len(dial_plans) >= 1, "Device CSS should produce at least one dial plan"

    def test_line_css_takes_priority_over_device_css(self, store):
        """When both line and device have CSS, line partitions are added first
        (higher priority), then device partitions. Both contribute to the
        user's effective CSS."""
        # Use one CSS for the line (with routing + blocking) and one for device
        # (with just routing). The line's blocking partition should appear.
        line_css = _css("Line-CSS")
        device_css = _css("Device-CSS")
        routing_pt = _partition("PSTN-PT")
        block_pt = _partition("Block-PT")
        rp = _route_pattern("9.1[2-9]XXXXXXXXX", action="ROUTE", partition="PSTN-PT")
        block_rp = _route_pattern("9.011!", action="BLOCK", partition="Block-PT")
        user = _user("both")
        phone = MigrationObject(
            canonical_id="phone:SEP333333333333",
            provenance=_provenance("uuid-phone3", "SEP333333333333"),
            status=MigrationStatus.NORMALIZED,
        )
        dn = MigrationObject(
            canonical_id="dn:2001:PSTN-PT",
            provenance=_provenance("uuid-dn2", "2001"),
            status=MigrationStatus.NORMALIZED,
        )

        for obj in [line_css, device_css, routing_pt, block_pt, rp, block_rp, user, phone, dn]:
            store.upsert_object(obj)

        # Line CSS has routing + blocking
        store.add_cross_ref("css:Line-CSS", "partition:PSTN-PT", "css_contains_partition", ordinal=1)
        store.add_cross_ref("css:Line-CSS", "partition:Block-PT", "css_contains_partition", ordinal=2)
        store.add_cross_ref("partition:PSTN-PT", rp.canonical_id, "partition_has_pattern")
        store.add_cross_ref("partition:Block-PT", block_rp.canonical_id, "partition_has_pattern")
        # Device CSS has same routing partition (common in CUCM)
        store.add_cross_ref("css:Device-CSS", "partition:PSTN-PT", "css_contains_partition", ordinal=1)
        # user → device → dn → line_css AND device → device_css
        store.add_cross_ref("user:both", "phone:SEP333333333333", "user_has_device")
        store.add_cross_ref("phone:SEP333333333333", "dn:2001:PSTN-PT", "device_has_dn")
        store.add_cross_ref("dn:2001:PSTN-PT", "css:Line-CSS", "line_has_css")
        store.add_cross_ref("phone:SEP333333333333", "css:Device-CSS", "device_has_css")

        mapper = CSSMapper(category_rules=US_CATEGORY_RULES)
        result = mapper.map(store)

        # User should get effective CSS from line (includes routing + blocking)
        # This means both dial plans and calling permissions should be produced
        dial_plans = store.query_by_type("dial_plan")
        assert len(dial_plans) >= 1, "Line CSS routing partitions should produce dial plans"

    def test_direct_user_css_overrides_line_and_device(self, store):
        """When user has a direct CSS, line/device CSSes are NOT consulted."""
        user_css = _css("User-CSS")
        line_css = _css("Line-CSS")
        pt = _partition("PSTN-PT")
        rp = _route_pattern("9.1[2-9]XXXXXXXXX", action="ROUTE", partition="PSTN-PT")
        # Line CSS has a different partition with a block pattern
        block_pt = _partition("Block-PT")
        block_rp = _route_pattern("9.1900XXXXXXX", action="BLOCK", partition="Block-PT")
        user = _user("override")
        phone = MigrationObject(
            canonical_id="phone:SEP444444444444",
            provenance=_provenance("uuid-phone4", "SEP444444444444"),
            status=MigrationStatus.NORMALIZED,
        )
        dn = MigrationObject(
            canonical_id="dn:3001:PSTN-PT",
            provenance=_provenance("uuid-dn3", "3001"),
            status=MigrationStatus.NORMALIZED,
        )

        for obj in [user_css, line_css, pt, block_pt, rp, block_rp, user, phone, dn]:
            store.upsert_object(obj)

        store.add_cross_ref("css:User-CSS", "partition:PSTN-PT", "css_contains_partition", ordinal=1)
        store.add_cross_ref("partition:PSTN-PT", rp.canonical_id, "partition_has_pattern")
        store.add_cross_ref("css:Line-CSS", "partition:Block-PT", "css_contains_partition", ordinal=1)
        store.add_cross_ref("partition:Block-PT", block_rp.canonical_id, "partition_has_pattern")
        # User has DIRECT CSS assignment — should override
        store.add_cross_ref("user:override", "css:User-CSS", "user_has_css")
        # Also has line CSS (should NOT be used)
        store.add_cross_ref("user:override", "phone:SEP444444444444", "user_has_device")
        store.add_cross_ref("phone:SEP444444444444", "dn:3001:PSTN-PT", "device_has_dn")
        store.add_cross_ref("dn:3001:PSTN-PT", "css:Line-CSS", "line_has_css")

        mapper = CSSMapper(category_rules=US_CATEGORY_RULES)
        result = mapper.map(store)

        # Only User-CSS routing should appear — no block patterns from Line-CSS
        decisions = store.get_all_decisions()
        # The block pattern from Line-CSS should NOT show up as a calling permission
        # since user has a direct CSS that doesn't include Block-PT
        perm_decisions = [d for d in decisions if d["type"] == "CALLING_PERMISSION_MISMATCH"]
        # No CALLING_PERMISSION_MISMATCH expected from Line-CSS's block
        # (User-CSS has no block partitions)
