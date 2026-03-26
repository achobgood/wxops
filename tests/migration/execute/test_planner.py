"""Tests for execution planner — expand_to_operations().

Acceptance criteria (from phase-07-planning.md):
- Given 10 analyzed canonical objects (2 users, 2 devices, 1 HG, 1 location,
  2 lines, 1 trunk, 1 dial plan), expand_to_operations() produces the correct
  number of operations with correct tiers and depends_on.
"""

import pytest
from datetime import datetime, timezone

from wxcli.migration.models import (
    CanonicalAutoAttendant,
    CanonicalCallForwarding,
    CanonicalCallPark,
    CanonicalCallQueue,
    CanonicalCallingPermission,
    CanonicalDevice,
    CanonicalDeviceLayout,
    CanonicalDialPlan,
    CanonicalHuntGroup,
    CanonicalLine,
    CanonicalLineKeyTemplate,
    CanonicalLocation,
    CanonicalLocationSchedule,
    CanonicalMonitoringList,
    CanonicalOperatingMode,
    CanonicalPagingGroup,
    CanonicalPickupGroup,
    CanonicalRouteGroup,
    CanonicalSharedLine,
    CanonicalSoftkeyConfig,
    CanonicalTranslationPattern,
    CanonicalTrunk,
    CanonicalUser,
    CanonicalVirtualLine,
    CanonicalVoicemailProfile,
    CanonicalWorkspace,
    DeviceCompatibilityTier,
    MigrationStatus,
    Provenance,
    TrunkGatewayRef,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.execute.planner import expand_to_operations


@pytest.fixture
def store(tmp_path):
    s = MigrationStore(tmp_path / "test.db")
    yield s
    s.close()


def _prov():
    return Provenance(
        source_system="cucm",
        source_id="pk-test",
        source_name="test",
        extracted_at=datetime.now(timezone.utc),
    )


def _set_analyzed(obj):
    """Set object status to analyzed."""
    obj.status = MigrationStatus.ANALYZED
    return obj


def _node_id_in_deps(cid: str, op_type: str, depends_on: list[str]) -> bool:
    return f"{cid}:{op_type}" in depends_on


class TestAcceptanceCriteria:
    """Given 10 analyzed objects, verify correct operation count and tiers."""

    def test_10_objects_produce_correct_ops(self, store):
        """2 users + 2 devices + 1 HG + 1 location + 2 lines + 1 trunk + 1 dial plan.

        Expected operations:
        - 1 location → 2 ops (create + enable_calling)
        - 1 trunk → 1 op (create)
        - 1 dial plan → 1 op (create)
        - 2 users (no settings data) → 1 op each = 2 ops
        - 2 devices → 2 ops each = 4 ops
        - 1 hunt group → 1 op (create)
        - 2 lines → 0 ops (data-only)
        Total: 11 ops
        """
        objects = [
            _set_analyzed(CanonicalLocation(
                canonical_id="location:hq",
                provenance=_prov(),
                name="HQ",
            )),
            _set_analyzed(CanonicalTrunk(
                canonical_id="trunk:main",
                provenance=_prov(),
                name="Main Trunk",
            )),
            _set_analyzed(CanonicalDialPlan(
                canonical_id="dial_plan:national",
                provenance=_prov(),
                name="National",
                route_id="trunk:main",
                route_type="TRUNK",
            )),
            _set_analyzed(CanonicalUser(
                canonical_id="user:jsmith",
                provenance=_prov(),
                emails=["jsmith@acme.com"],
                location_id="location:hq",
                extension="1001",
            )),
            _set_analyzed(CanonicalUser(
                canonical_id="user:jdoe",
                provenance=_prov(),
                emails=["jdoe@acme.com"],
                location_id="location:hq",
                extension="1002",
            )),
            _set_analyzed(CanonicalDevice(
                canonical_id="device:phone1",
                provenance=_prov(),
                mac="AABBCCDDEEFF",
                compatibility_tier=DeviceCompatibilityTier.NATIVE_MPP,
                owner_canonical_id="user:jsmith",
                location_canonical_id="location:hq",
            )),
            _set_analyzed(CanonicalDevice(
                canonical_id="device:phone2",
                provenance=_prov(),
                mac="112233445566",
                compatibility_tier=DeviceCompatibilityTier.NATIVE_MPP,
                owner_canonical_id="user:jdoe",
                location_canonical_id="location:hq",
            )),
            _set_analyzed(CanonicalHuntGroup(
                canonical_id="hunt_group:sales",
                provenance=_prov(),
                name="Sales HG",
                agents=["user:jsmith", "user:jdoe"],
            )),
            _set_analyzed(CanonicalLine(
                canonical_id="line:1001",
                provenance=_prov(),
                extension="1001",
            )),
            _set_analyzed(CanonicalLine(
                canonical_id="line:1002",
                provenance=_prov(),
                extension="1002",
            )),
        ]

        for obj in objects:
            store.upsert_object(obj)

        ops = expand_to_operations(store)

        # 2 loc + 1 trunk + 1 dp + 2 user (no settings) + 4 device + 1 hg = 11
        assert len(ops) == 11

        # Verify tier assignments
        by_type = {}
        for op in ops:
            key = f"{op.resource_type}:{op.op_type}"
            by_type.setdefault(key, []).append(op)

        assert by_type["location:create"][0].tier == 0
        assert by_type["location:enable_calling"][0].tier == 0
        assert by_type["trunk:create"][0].tier == 1
        assert by_type["dial_plan:create"][0].tier == 2
        assert all(op.tier == 2 for op in by_type["user:create"])
        # Users without settings data don't produce configure_settings/voicemail ops
        assert "user:configure_settings" not in by_type
        assert "user:configure_voicemail" not in by_type
        assert all(op.tier == 3 for op in by_type["device:create"])
        assert all(op.tier == 5 for op in by_type["device:configure_settings"])
        assert by_type["hunt_group:create"][0].tier == 4

    def test_user_depends_on_chain(self, store):
        """User without settings data → only create op."""
        user = _set_analyzed(CanonicalUser(
            canonical_id="user:test",
            provenance=_prov(),
            emails=["test@acme.com"],
        ))
        store.upsert_object(user)
        ops = expand_to_operations(store)

        by_op = {op.op_type: op for op in ops}

        assert by_op["create"].depends_on == []
        assert len(by_op) == 1  # only create (no settings/voicemail data)

    def test_dial_plan_depends_on_trunk(self, store):
        """Dial plan depends on its route target (trunk)."""
        trunk = _set_analyzed(CanonicalTrunk(
            canonical_id="trunk:t1", provenance=_prov(), name="T1",
        ))
        dp = _set_analyzed(CanonicalDialPlan(
            canonical_id="dial_plan:dp1", provenance=_prov(),
            name="DP1", route_id="trunk:t1", route_type="TRUNK",
        ))
        store.upsert_object(trunk)
        store.upsert_object(dp)

        ops = expand_to_operations(store)
        dp_op = [op for op in ops if op.resource_type == "dial_plan"][0]
        assert "trunk:t1:create" in dp_op.depends_on


class TestDecisionAwareExpansion:
    """Verify that resolved decisions affect expansion."""

    def test_device_incompatible_skip(self, store):
        """DEVICE_INCOMPATIBLE resolved as 'skip' → no device ops."""
        device = _set_analyzed(CanonicalDevice(
            canonical_id="device:bad",
            provenance=_prov(),
            mac="FFFFFFFFFFFF",
            compatibility_tier=DeviceCompatibilityTier.INCOMPATIBLE,
        ))
        store.upsert_object(device)

        # Add a resolved DEVICE_INCOMPATIBLE decision
        store.save_decision({
            "decision_id": "D0001",
            "type": "DEVICE_INCOMPATIBLE",
            "severity": "HIGH",
            "summary": "Device incompatible",
            "context": {"_affected_objects": ["device:bad"]},
            "options": [{"id": "skip", "label": "Skip", "impact": "none"}],
            "chosen_option": "skip",
            "resolved_at": "2026-01-01T00:00:00Z",
            "resolved_by": "user",
            "fingerprint": "fp-device-bad",
            "run_id": "test-run",
        })

        ops = expand_to_operations(store)
        device_ops = [op for op in ops if op.resource_type == "device"]
        assert len(device_ops) == 0

    def test_shared_line_skip(self, store):
        """SHARED_LINE_COMPLEX resolved as 'skip' → no shared_line ops."""
        sl = _set_analyzed(CanonicalSharedLine(
            canonical_id="shared_line:sl1",
            provenance=_prov(),
            dn_canonical_id="line:1001",
            owner_canonical_ids=["user:a", "user:b"],
        ))
        store.upsert_object(sl)

        store.save_decision({
            "decision_id": "D0002",
            "type": "SHARED_LINE_COMPLEX",
            "severity": "MEDIUM",
            "summary": "Complex shared line",
            "context": {"_affected_objects": ["shared_line:sl1"]},
            "options": [{"id": "skip", "label": "Skip", "impact": "none"}],
            "chosen_option": "skip",
            "resolved_at": "2026-01-01T00:00:00Z",
            "resolved_by": "user",
            "fingerprint": "fp-sl1",
            "run_id": "test-run",
        })

        ops = expand_to_operations(store)
        sl_ops = [op for op in ops if op.resource_type == "shared_line"]
        assert len(sl_ops) == 0

    def test_shared_line_virtual_line_redirect(self, store):
        """SHARED_LINE_COMPLEX resolved as 'virtual_line' → no shared_line ops."""
        sl = _set_analyzed(CanonicalSharedLine(
            canonical_id="shared_line:sl2",
            provenance=_prov(),
            dn_canonical_id="line:1001",
        ))
        store.upsert_object(sl)

        store.save_decision({
            "decision_id": "D0003",
            "type": "SHARED_LINE_COMPLEX",
            "severity": "MEDIUM",
            "summary": "Complex shared line",
            "context": {"_affected_objects": ["shared_line:sl2"]},
            "options": [{"id": "virtual_line", "label": "Virtual Line", "impact": "1 VL"}],
            "chosen_option": "virtual_line",
            "resolved_at": "2026-01-01T00:00:00Z",
            "resolved_by": "user",
            "fingerprint": "fp-sl2",
            "run_id": "test-run",
        })

        ops = expand_to_operations(store)
        sl_ops = [op for op in ops if op.resource_type == "shared_line"]
        assert len(sl_ops) == 0


class TestDataOnlyTypes:
    """Line and voicemail_profile don't produce operations."""

    def test_lines_produce_no_ops(self, store):
        line = _set_analyzed(CanonicalLine(
            canonical_id="line:ext1", provenance=_prov(), extension="1001",
        ))
        store.upsert_object(line)
        ops = expand_to_operations(store)
        assert len(ops) == 0

    def test_voicemail_profiles_produce_no_ops(self, store):
        vm = _set_analyzed(CanonicalVoicemailProfile(
            canonical_id="voicemail_profile:vm1", provenance=_prov(),
        ))
        store.upsert_object(vm)
        ops = expand_to_operations(store)
        assert len(ops) == 0


class TestNeedsDecisionSkipped:
    """Objects at status needs_decision are not expanded."""

    def test_needs_decision_skipped(self, store):
        user = CanonicalUser(
            canonical_id="user:pending",
            provenance=_prov(),
            emails=["pending@acme.com"],
            status=MigrationStatus.NEEDS_DECISION,
        )
        store.upsert_object(user)
        ops = expand_to_operations(store)
        assert len(ops) == 0


class TestBatchAssignment:
    """Org-wide types get batch='org-wide', site types get location_id."""

    def test_org_wide_batch(self, store):
        trunk = _set_analyzed(CanonicalTrunk(
            canonical_id="trunk:t1", provenance=_prov(), name="T1",
        ))
        store.upsert_object(trunk)
        ops = expand_to_operations(store)
        assert ops[0].batch == "org-wide"

    def test_site_batch(self, store):
        user = _set_analyzed(CanonicalUser(
            canonical_id="user:u1", provenance=_prov(),
            emails=["u1@acme.com"], location_id="location:hq",
        ))
        store.upsert_object(user)
        ops = expand_to_operations(store)
        for op in ops:
            assert op.batch == "location:hq"


class TestAllObjectTypes:
    """Every canonical type has an expansion pattern."""

    def test_all_types_covered(self, store):
        """Insert one of each type at analyzed status and verify no warnings."""
        all_objects = [
            _set_analyzed(CanonicalLocation(canonical_id="location:l1", provenance=_prov(), name="L1")),
            _set_analyzed(CanonicalTrunk(canonical_id="trunk:t1", provenance=_prov(), name="T1")),
            _set_analyzed(CanonicalRouteGroup(canonical_id="route_group:rg1", provenance=_prov(), name="RG1")),
            _set_analyzed(CanonicalOperatingMode(canonical_id="operating_mode:om1", provenance=_prov(), name="OM1")),
            _set_analyzed(CanonicalUser(canonical_id="user:u1", provenance=_prov(), emails=["u1@x.com"])),
            _set_analyzed(CanonicalWorkspace(canonical_id="workspace:w1", provenance=_prov(), display_name="W1")),
            _set_analyzed(CanonicalDevice(canonical_id="device:d1", provenance=_prov(), mac="AABB")),
            _set_analyzed(CanonicalDialPlan(canonical_id="dial_plan:dp1", provenance=_prov(), name="DP1")),
            _set_analyzed(CanonicalTranslationPattern(canonical_id="translation_pattern:tp1", provenance=_prov(), name="TP1")),
            _set_analyzed(CanonicalCallingPermission(canonical_id="calling_permission:cp1", provenance=_prov())),
            _set_analyzed(CanonicalHuntGroup(canonical_id="hunt_group:hg1", provenance=_prov(), name="HG1")),
            _set_analyzed(CanonicalCallQueue(canonical_id="call_queue:cq1", provenance=_prov(), name="CQ1")),
            _set_analyzed(CanonicalAutoAttendant(canonical_id="auto_attendant:aa1", provenance=_prov(), name="AA1")),
            _set_analyzed(CanonicalCallPark(canonical_id="call_park:cp1", provenance=_prov(), name="CP1")),
            _set_analyzed(CanonicalPickupGroup(canonical_id="pickup_group:pg1", provenance=_prov(), name="PG1")),
            _set_analyzed(CanonicalPagingGroup(canonical_id="paging_group:pag1", provenance=_prov(), name="PAG1")),
            _set_analyzed(CanonicalSharedLine(canonical_id="shared_line:sl1", provenance=_prov())),
            _set_analyzed(CanonicalVirtualLine(canonical_id="virtual_line:vl1", provenance=_prov())),
            _set_analyzed(CanonicalLocationSchedule(canonical_id="schedule:s1", provenance=_prov(), name="S1")),
            # Data-only types (no ops expected)
            _set_analyzed(CanonicalLine(canonical_id="line:ln1", provenance=_prov())),
            _set_analyzed(CanonicalVoicemailProfile(canonical_id="voicemail_profile:vm1", provenance=_prov())),
        ]
        for obj in all_objects:
            store.upsert_object(obj)

        ops = expand_to_operations(store)

        # Verify all expandable types produced ops
        resource_types = {op.resource_type for op in ops}
        # calling_permission with no assigned_users produces 0 ops (no create op)
        expected_types = {
            "location", "trunk", "route_group", "operating_mode",
            "user", "workspace", "device", "dial_plan", "translation_pattern",
            "hunt_group", "call_queue", "auto_attendant",
            "call_park", "pickup_group", "paging_group", "shared_line",
            "virtual_line", "schedule",
        }
        assert expected_types == resource_types

    def test_workspace_expansion(self, store):
        """Workspace → 3 ops: create, assign_number, configure_settings."""
        ws = _set_analyzed(CanonicalWorkspace(
            canonical_id="workspace:lobby", provenance=_prov(),
            display_name="Lobby Phone", location_id="location:hq",
        ))
        store.upsert_object(ws)
        ops = expand_to_operations(store)
        assert len(ops) == 3
        op_types = [op.op_type for op in ops]
        assert "create" in op_types
        assert "assign_number" in op_types
        assert "configure_settings" in op_types

    def test_virtual_line_expansion(self, store):
        """Virtual line → 2 ops: create, configure."""
        vl = _set_analyzed(CanonicalVirtualLine(
            canonical_id="virtual_line:vl1", provenance=_prov(),
            extension="9001", display_name="VL1",
        ))
        store.upsert_object(vl)
        ops = expand_to_operations(store)
        assert len(ops) == 2
        assert ops[0].op_type == "create"
        assert ops[1].op_type == "configure"

    def test_route_group_depends_on_trunks(self, store):
        """Route group with local_gateways depends on those trunks."""
        trunk = _set_analyzed(CanonicalTrunk(
            canonical_id="trunk:t1", provenance=_prov(), name="T1",
        ))
        rg = _set_analyzed(CanonicalRouteGroup(
            canonical_id="route_group:rg1", provenance=_prov(),
            name="RG1",
            local_gateways=[TrunkGatewayRef(trunk_canonical_id="trunk:t1")],
        ))
        store.upsert_object(trunk)
        store.upsert_object(rg)
        ops = expand_to_operations(store)
        rg_op = [op for op in ops if op.resource_type == "route_group"][0]
        assert "trunk:t1:create" in rg_op.depends_on

    def test_calling_permission_with_users(self, store):
        """Calling permission with assigned_users produces only assign op (no create)."""
        cp = _set_analyzed(CanonicalCallingPermission(
            canonical_id="calling_permission:intl_block", provenance=_prov(),
            assigned_users=["user:a", "user:b"],
        ))
        store.upsert_object(cp)
        ops = expand_to_operations(store)
        assert len(ops) == 1  # assign only (no create)
        assign_op = ops[0]
        assert assign_op.op_type == "assign"
        assert assign_op.api_calls == 2  # one per user
        assert "user:a:create" in assign_op.depends_on
        assert "user:b:create" in assign_op.depends_on


class TestLocationScheduleExpansion:
    """Location schedule expansion and tier assignment."""

    def test_schedule_expansion(self, store):
        """Location schedule -> 1 op: create at tier 1."""
        sched = _set_analyzed(CanonicalLocationSchedule(
            canonical_id="schedule:s1", provenance=_prov(),
            name="BusinessHours", schedule_type="businessHours",
            location_id="location:hq",
        ))
        store.upsert_object(sched)
        ops = expand_to_operations(store)
        assert len(ops) == 1
        assert ops[0].op_type == "create"
        assert ops[0].resource_type == "schedule"
        assert ops[0].tier == 1
        assert ops[0].batch == "location:hq"

    def test_schedule_before_aa_in_tier_order(self, store):
        """Schedule (tier 1) is before AA (tier 4)."""
        sched = _set_analyzed(CanonicalLocationSchedule(
            canonical_id="schedule:s1", provenance=_prov(),
            name="BusinessHours",
        ))
        aa = _set_analyzed(CanonicalAutoAttendant(
            canonical_id="auto_attendant:aa1", provenance=_prov(),
            name="MainAA",
        ))
        store.upsert_object(sched)
        store.upsert_object(aa)
        ops = expand_to_operations(store)
        sched_op = [o for o in ops if o.resource_type == "schedule"][0]
        aa_op = [o for o in ops if o.resource_type == "auto_attendant"][0]
        assert sched_op.tier < aa_op.tier


class TestStaleDecisionsIgnored:
    """Stale decisions (chosen_option='__stale__') are ignored by the planner."""

    def test_stale_device_decision_ignored(self, store):
        """A stale DEVICE_INCOMPATIBLE decision should NOT suppress device ops."""
        device = _set_analyzed(CanonicalDevice(
            canonical_id="device:stale_test",
            provenance=_prov(),
            mac="AABBCCDDEEFF",
            compatibility_tier=DeviceCompatibilityTier.NATIVE_MPP,
        ))
        store.upsert_object(device)

        # Stale decision — should be ignored
        store.save_decision({
            "decision_id": "D0010",
            "type": "DEVICE_INCOMPATIBLE",
            "severity": "HIGH",
            "summary": "Device incompatible (stale)",
            "context": {"_affected_objects": ["device:stale_test"]},
            "options": [{"id": "skip", "label": "Skip", "impact": "none"}],
            "chosen_option": "__stale__",
            "resolved_at": "2026-01-01T00:00:00Z",
            "resolved_by": "stale",
            "fingerprint": "fp-stale-device",
            "run_id": "test-run",
        })

        ops = expand_to_operations(store)
        device_ops = [op for op in ops if op.resource_type == "device"]
        assert len(device_ops) == 2  # create + configure_settings


class TestAdditionalDecisionSkips:
    """EXTENSION_CONFLICT, LOCATION_AMBIGUOUS, FIRMWARE_CONVERTIBLE skip paths."""

    def test_extension_conflict_skip(self, store):
        """EXTENSION_CONFLICT resolved as 'skip' → no user ops."""
        user = _set_analyzed(CanonicalUser(
            canonical_id="user:conflicted",
            provenance=_prov(),
            emails=["conflict@acme.com"],
        ))
        store.upsert_object(user)

        store.save_decision({
            "decision_id": "D0011",
            "type": "EXTENSION_CONFLICT",
            "severity": "HIGH",
            "summary": "Extension conflict",
            "context": {"_affected_objects": ["user:conflicted"]},
            "options": [{"id": "skip", "label": "Skip", "impact": "user not migrated"}],
            "chosen_option": "skip",
            "resolved_at": "2026-01-01T00:00:00Z",
            "resolved_by": "user",
            "fingerprint": "fp-ext-conflict",
            "run_id": "test-run",
        })

        ops = expand_to_operations(store)
        user_ops = [op for op in ops if op.canonical_id == "user:conflicted"]
        assert len(user_ops) == 0

    def test_location_ambiguous_skip(self, store):
        """LOCATION_AMBIGUOUS resolved as 'skip' → no location ops."""
        loc = _set_analyzed(CanonicalLocation(
            canonical_id="location:ambig",
            provenance=_prov(),
            name="Ambiguous Site",
        ))
        store.upsert_object(loc)

        store.save_decision({
            "decision_id": "D0012",
            "type": "LOCATION_AMBIGUOUS",
            "severity": "MEDIUM",
            "summary": "Location ambiguous",
            "context": {"_affected_objects": ["location:ambig"]},
            "options": [{"id": "skip", "label": "Skip", "impact": "location not created"}],
            "chosen_option": "skip",
            "resolved_at": "2026-01-01T00:00:00Z",
            "resolved_by": "user",
            "fingerprint": "fp-loc-ambig",
            "run_id": "test-run",
        })

        ops = expand_to_operations(store)
        loc_ops = [op for op in ops if op.canonical_id == "location:ambig"]
        assert len(loc_ops) == 0

    def test_firmware_convertible_skip(self, store):
        """DEVICE_FIRMWARE_CONVERTIBLE resolved as 'skip' → no device ops."""
        device = _set_analyzed(CanonicalDevice(
            canonical_id="device:old_firmware",
            provenance=_prov(),
            mac="FFFFFFFFFFFF",
            compatibility_tier=DeviceCompatibilityTier.CONVERTIBLE,
        ))
        store.upsert_object(device)

        store.save_decision({
            "decision_id": "D0013",
            "type": "DEVICE_FIRMWARE_CONVERTIBLE",
            "severity": "MEDIUM",
            "summary": "Device firmware convertible",
            "context": {"_affected_objects": ["device:old_firmware"]},
            "options": [{"id": "skip", "label": "Skip", "impact": "device not migrated"}],
            "chosen_option": "skip",
            "resolved_at": "2026-01-01T00:00:00Z",
            "resolved_by": "user",
            "fingerprint": "fp-fw-skip",
            "run_id": "test-run",
        })

        ops = expand_to_operations(store)
        device_ops = [op for op in ops if op.canonical_id == "device:old_firmware"]
        assert len(device_ops) == 0

    def test_firmware_convertible_convert_still_expands(self, store):
        """DEVICE_FIRMWARE_CONVERTIBLE resolved as 'convert' → normal device ops."""
        device = _set_analyzed(CanonicalDevice(
            canonical_id="device:convert_me",
            provenance=_prov(),
            mac="AABBCCDDEEFF",
            compatibility_tier=DeviceCompatibilityTier.CONVERTIBLE,
        ))
        store.upsert_object(device)

        store.save_decision({
            "decision_id": "D0014",
            "type": "DEVICE_FIRMWARE_CONVERTIBLE",
            "severity": "MEDIUM",
            "summary": "Device firmware convertible",
            "context": {"_affected_objects": ["device:convert_me"]},
            "options": [{"id": "convert", "label": "Convert", "impact": "firmware update"}],
            "chosen_option": "convert",
            "resolved_at": "2026-01-01T00:00:00Z",
            "resolved_by": "user",
            "fingerprint": "fp-fw-convert",
            "run_id": "test-run",
        })

        ops = expand_to_operations(store)
        device_ops = [op for op in ops if op.canonical_id == "device:convert_me"]
        assert len(device_ops) == 2  # create + configure_settings


class TestEdgeCases:
    """Q3 edge cases from phase-07-expansion-fixes.md."""

    def test_location_with_users_no_devices(self, store):
        """Location with users but no devices — device ops just absent."""
        loc = _set_analyzed(CanonicalLocation(
            canonical_id="location:site1", provenance=_prov(), name="Site 1",
        ))
        user = _set_analyzed(CanonicalUser(
            canonical_id="user:u1", provenance=_prov(),
            emails=["u1@acme.com"], location_id="location:site1",
        ))
        store.upsert_object(loc)
        store.upsert_object(user)

        ops = expand_to_operations(store)
        resource_types = {op.resource_type for op in ops}
        assert "location" in resource_types
        assert "user" in resource_types
        assert "device" not in resource_types
        # 2 location ops + 1 user op (no settings data) = 3
        assert len(ops) == 3

    def test_user_with_no_location_id(self, store):
        """User with no location_id — batch is None (not org-wide, not site-specific)."""
        user = _set_analyzed(CanonicalUser(
            canonical_id="user:orphan", provenance=_prov(),
            emails=["orphan@acme.com"],
        ))
        store.upsert_object(user)

        ops = expand_to_operations(store)
        assert len(ops) == 1  # only create (no settings/voicemail data)
        for op in ops:
            assert op.batch is None  # no location → no batch assignment

    def test_hunt_group_with_no_agents(self, store):
        """Hunt group with empty agents list — 1 create op, no depends_on."""
        hg = _set_analyzed(CanonicalHuntGroup(
            canonical_id="hunt_group:empty", provenance=_prov(),
            name="Empty HG", agents=[],
        ))
        store.upsert_object(hg)

        ops = expand_to_operations(store)
        assert len(ops) == 1
        assert ops[0].op_type == "create"
        assert ops[0].depends_on == []

    def test_call_queue_with_no_agents(self, store):
        """Call queue with empty agents list — 1 create op, no depends_on."""
        cq = _set_analyzed(CanonicalCallQueue(
            canonical_id="call_queue:empty", provenance=_prov(),
            name="Empty CQ", agents=[],
        ))
        store.upsert_object(cq)

        ops = expand_to_operations(store)
        assert len(ops) == 1
        assert ops[0].op_type == "create"
        assert ops[0].depends_on == []

    def test_auto_attendant_with_no_agents(self, store):
        """Auto attendant — 1 create op, no agent deps (AAs don't have agents)."""
        aa = _set_analyzed(CanonicalAutoAttendant(
            canonical_id="auto_attendant:empty", provenance=_prov(),
            name="Empty AA",
        ))
        store.upsert_object(aa)

        ops = expand_to_operations(store)
        assert len(ops) == 1
        assert ops[0].op_type == "create"
        assert ops[0].depends_on == []

    def test_all_objects_needs_decision(self, store):
        """All objects at needs_decision — zero ops produced."""
        user = CanonicalUser(
            canonical_id="user:pending1", provenance=_prov(),
            emails=["p1@acme.com"], status=MigrationStatus.NEEDS_DECISION,
        )
        device = CanonicalDevice(
            canonical_id="device:pending1", provenance=_prov(),
            mac="AABBCCDDEEFF", status=MigrationStatus.NEEDS_DECISION,
        )
        loc = CanonicalLocation(
            canonical_id="location:pending1", provenance=_prov(),
            name="Pending", status=MigrationStatus.NEEDS_DECISION,
        )
        store.upsert_object(user)
        store.upsert_object(device)
        store.upsert_object(loc)

        ops = expand_to_operations(store)
        assert len(ops) == 0

    def test_calling_permission_with_zero_users(self, store):
        """Calling permission with 0 assigned_users — no ops at all."""
        cp = _set_analyzed(CanonicalCallingPermission(
            canonical_id="calling_permission:empty", provenance=_prov(),
            assigned_users=[],
        ))
        store.upsert_object(cp)

        ops = expand_to_operations(store)
        assert len(ops) == 0  # no users to assign → no ops

    def test_api_call_estimate_auto_attendant(self, store):
        """Auto attendant create should be 1 API call (menu is part of POST body)."""
        aa = _set_analyzed(CanonicalAutoAttendant(
            canonical_id="auto_attendant:test", provenance=_prov(),
            name="Test AA",
        ))
        store.upsert_object(aa)

        ops = expand_to_operations(store)
        assert len(ops) == 1
        assert ops[0].api_calls == 1  # single POST, menu included in body

    def test_api_call_estimate_device(self, store):
        """Device create should be 1 API call (POST by MAC or activation code)."""
        device = _set_analyzed(CanonicalDevice(
            canonical_id="device:test", provenance=_prov(),
            mac="AABBCCDDEEFF",
            compatibility_tier=DeviceCompatibilityTier.NATIVE_MPP,
        ))
        store.upsert_object(device)

        ops = expand_to_operations(store)
        create_op = [op for op in ops if op.op_type == "create"][0]
        assert create_op.api_calls == 1  # single POST, no separate activation


class TestExpandLineKeyTemplate:
    def test_basic(self, store):
        tmpl = _set_analyzed(CanonicalLineKeyTemplate(
            canonical_id="line_key_template:Standard 8845",
            provenance=_prov(),
            name="Standard 8845",
            device_model="DMS Cisco 8845",
            line_keys=[{"index": 1, "key_type": "PRIMARY_LINE"}],
            phones_using=3,
        ))
        store.upsert_object(tmpl)
        ops = expand_to_operations(store)
        assert len(ops) == 1
        op = ops[0]
        assert op.resource_type == "line_key_template"
        assert op.op_type == "create"
        assert op.tier == 1
        assert op.batch == "org-wide"

    def test_dead_template_skipped(self, store):
        tmpl = _set_analyzed(CanonicalLineKeyTemplate(
            canonical_id="line_key_template:Unused",
            provenance=_prov(),
            name="Unused",
            device_model="DMS Cisco 8845",
            line_keys=[],
            phones_using=0,
        ))
        store.upsert_object(tmpl)
        ops = expand_to_operations(store)
        assert ops == []


class TestExpandCallForwarding:
    def test_basic(self, store):
        cf = _set_analyzed(CanonicalCallForwarding(
            canonical_id="call_forwarding:user:jsmith",
            provenance=_prov(),
            user_canonical_id="user:jsmith",
            always_enabled=True,
            always_destination="+12223334444",
        ))
        store.upsert_object(cf)
        ops = expand_to_operations(store)
        assert len(ops) == 1
        op = ops[0]
        assert op.resource_type == "call_forwarding"
        assert op.op_type == "configure"
        assert op.tier == 5
        assert _node_id_in_deps("user:jsmith", "create", op.depends_on)

    def test_all_disabled_skipped(self, store):
        cf = _set_analyzed(CanonicalCallForwarding(
            canonical_id="call_forwarding:user:jsmith",
            provenance=_prov(),
            user_canonical_id="user:jsmith",
            always_enabled=False,
            busy_enabled=False,
            no_answer_enabled=False,
        ))
        store.upsert_object(cf)
        ops = expand_to_operations(store)
        assert ops == []


class TestExpandMonitoringList:
    def test_basic(self, store):
        ml = _set_analyzed(CanonicalMonitoringList(
            canonical_id="monitoring_list:user:jsmith",
            provenance=_prov(),
            user_canonical_id="user:jsmith",
            monitored_members=[
                {"target_canonical_id": "user:alice"},
                {"target_canonical_id": "user:bob"},
            ],
        ))
        store.upsert_object(ml)
        ops = expand_to_operations(store)
        assert len(ops) == 1
        op = ops[0]
        assert op.resource_type == "monitoring_list"
        assert op.op_type == "configure"
        assert op.tier == 6
        assert _node_id_in_deps("user:jsmith", "create", op.depends_on)
        assert _node_id_in_deps("user:alice", "create", op.depends_on)
        assert _node_id_in_deps("user:bob", "create", op.depends_on)

    def test_empty_members_skipped(self, store):
        ml = _set_analyzed(CanonicalMonitoringList(
            canonical_id="monitoring_list:user:jsmith",
            provenance=_prov(),
            user_canonical_id="user:jsmith",
            monitored_members=[],
        ))
        store.upsert_object(ml)
        ops = expand_to_operations(store)
        assert ops == []


class TestExpandDeviceLayout:
    def test_basic(self, store):
        layout = _set_analyzed(CanonicalDeviceLayout(
            canonical_id="device_layout:SEPAA112233",
            provenance=_prov(),
            device_canonical_id="device:SEPAA112233",
            template_canonical_id="line_key_template:Standard 8845",
            owner_canonical_id="user:jsmith",
            line_members=[
                {"port": 1, "member_canonical_id": "user:jsmith"},
            ],
            resolved_line_keys=[{"index": 1, "key_type": "PRIMARY_LINE"}],
        ))
        store.upsert_object(layout)
        ops = expand_to_operations(store)
        assert len(ops) == 1
        op = ops[0]
        assert op.resource_type == "device_layout"
        assert op.op_type == "configure"
        assert op.tier == 7
        assert _node_id_in_deps("device:SEPAA112233", "create", op.depends_on)
        assert _node_id_in_deps("line_key_template:Standard 8845", "create", op.depends_on)
        assert _node_id_in_deps("user:jsmith", "create", op.depends_on)

    def test_no_keys_no_template_skipped(self, store):
        layout = _set_analyzed(CanonicalDeviceLayout(
            canonical_id="device_layout:SEPAA112233",
            provenance=_prov(),
            device_canonical_id="device:SEPAA112233",
            resolved_line_keys=[],
            template_canonical_id=None,
        ))
        store.upsert_object(layout)
        ops = expand_to_operations(store)
        assert ops == []


class TestExpandSoftkeyConfig:
    def test_psk_target_produces_op(self, store):
        sc = _set_analyzed(CanonicalSoftkeyConfig(
            canonical_id="softkey_config:device:SEP001122334455",
            provenance=_prov(),
            device_canonical_id="device:SEP001122334455",
            is_psk_target=True,
            psk_mappings=[{"psk_slot": "PSK1", "keyword": "park"}],
            state_key_lists={"idle": ["park"]},
        ))
        store.upsert_object(sc)
        ops = expand_to_operations(store)
        assert len(ops) == 1
        op = ops[0]
        assert op.resource_type == "softkey_config"
        assert op.op_type == "configure"
        assert op.tier == 7
        assert _node_id_in_deps("device:SEP001122334455", "create", op.depends_on)

    def test_not_psk_target_skipped(self, store):
        sc = _set_analyzed(CanonicalSoftkeyConfig(
            canonical_id="softkey_config:Standard User",
            provenance=_prov(),
            is_psk_target=False,
            phones_using=5,
        ))
        store.upsert_object(sc)
        ops = expand_to_operations(store)
        assert ops == []
