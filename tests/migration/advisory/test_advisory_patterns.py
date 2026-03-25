"""Tests for cross-cutting advisory patterns.

Each pattern takes a MigrationStore and returns list[AdvisoryFinding].
Tests build minimal store fixtures that trigger or don't trigger each pattern.
"""

import os
from datetime import datetime, timezone

from wxcli.migration.models import (
    CanonicalDialPlan,
    CanonicalLocation,
    CanonicalTranslationPattern,
    CanonicalTrunk,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore


def _prov():
    return Provenance(
        source_system="cucm",
        source_id="test",
        source_name="test",
        extracted_at=datetime.now(timezone.utc),
    )


def _store(tmp_path, name="t.db"):
    return MigrationStore(os.path.join(str(tmp_path), name))


def _analyzed(obj):
    obj.status = MigrationStatus.ANALYZED
    return obj


# ===================================================================
# Pattern 1: Restriction CSS Consolidation
# ===================================================================

class TestRestrictionCSSConsolidation:
    """Spec Pattern 1: CSSes with only blocking patterns → eliminate."""

    def test_detects_restriction_only_csses(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_restriction_css_consolidation,
        )

        store = _store(tmp_path)
        # Create 2 CSSes with partitions that have only blocking patterns
        # CSS1 → Partition1 → blocking patterns
        # CSS2 → Partition2 → blocking patterns
        for i in range(1, 3):
            store.conn.execute(
                "INSERT OR REPLACE INTO objects (canonical_id, object_type, status, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (f"css:{i}", "calling_search_space", "analyzed",
                 f'{{"canonical_id": "css:{i}", "name": "CSS{i}", "pre_migration_state": {{"name": "CSS{i}"}}, "provenance": {{"source_system": "cucm", "source_id": "t", "source_name": "t", "extracted_at": "2026-01-01T00:00:00Z"}}}}',
                 "2026-01-01", "2026-01-01"),
            )
            store.conn.execute(
                "INSERT OR REPLACE INTO objects (canonical_id, object_type, status, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (f"partition:{i}", "route_partition", "analyzed",
                 f'{{"canonical_id": "partition:{i}", "name": "PT{i}", "pre_migration_state": {{"name": "PT{i}"}}, "provenance": {{"source_system": "cucm", "source_id": "t", "source_name": "t", "extracted_at": "2026-01-01T00:00:00Z"}}}}',
                 "2026-01-01", "2026-01-01"),
            )
            # Route patterns that are blocking (international/premium blocks)
            for j, pat in enumerate(["011!", "1900!"]):
                store.conn.execute(
                    "INSERT OR REPLACE INTO objects (canonical_id, object_type, status, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (f"route_pattern:{i}_{j}", "route_pattern", "analyzed",
                     f'{{"canonical_id": "route_pattern:{i}_{j}", "pre_migration_state": {{"pattern": "{pat}", "routePartitionName": "PT{i}", "blockEnable": true}}, "provenance": {{"source_system": "cucm", "source_id": "t", "source_name": "t", "extracted_at": "2026-01-01T00:00:00Z"}}}}',
                     "2026-01-01", "2026-01-01"),
                )
                store.add_cross_ref(f"partition:{i}", f"route_pattern:{i}_{j}", "partition_has_pattern", ordinal=j)

            store.add_cross_ref(f"css:{i}", f"partition:{i}", "css_contains_partition", ordinal=0)
        store.conn.commit()

        findings = detect_restriction_css_consolidation(store)
        assert len(findings) >= 1
        assert findings[0].category == "eliminate"
        assert findings[0].severity == "HIGH"

    def test_skips_routing_csses(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_restriction_css_consolidation,
        )

        store = _store(tmp_path)
        # CSS with a routing pattern (not blocking)
        store.conn.execute(
            "INSERT OR REPLACE INTO objects (canonical_id, object_type, status, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("css:1", "calling_search_space", "analyzed",
             '{"canonical_id": "css:1", "name": "CSS1", "pre_migration_state": {"name": "CSS1"}, "provenance": {"source_system": "cucm", "source_id": "t", "source_name": "t", "extracted_at": "2026-01-01T00:00:00Z"}}',
             "2026-01-01", "2026-01-01"),
        )
        store.conn.execute(
            "INSERT OR REPLACE INTO objects (canonical_id, object_type, status, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("partition:1", "route_partition", "analyzed",
             '{"canonical_id": "partition:1", "name": "PT1", "pre_migration_state": {"name": "PT1"}, "provenance": {"source_system": "cucm", "source_id": "t", "source_name": "t", "extracted_at": "2026-01-01T00:00:00Z"}}',
             "2026-01-01", "2026-01-01"),
        )
        # A normal routing pattern (NOT blocking)
        store.conn.execute(
            "INSERT OR REPLACE INTO objects (canonical_id, object_type, status, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("route_pattern:1_0", "route_pattern", "analyzed",
             '{"canonical_id": "route_pattern:1_0", "pre_migration_state": {"pattern": "9.XXXX", "routePartitionName": "PT1", "blockEnable": false}, "provenance": {"source_system": "cucm", "source_id": "t", "source_name": "t", "extracted_at": "2026-01-01T00:00:00Z"}}',
             "2026-01-01", "2026-01-01"),
        )
        store.add_cross_ref("partition:1", "route_pattern:1_0", "partition_has_pattern", ordinal=0)
        store.add_cross_ref("css:1", "partition:1", "css_contains_partition", ordinal=0)
        store.conn.commit()

        findings = detect_restriction_css_consolidation(store)
        assert len(findings) == 0


# ===================================================================
# Pattern 2: Translation Pattern Elimination
# ===================================================================

class TestTranslationPatternElimination:
    """Spec Pattern 2: Digit normalization patterns → eliminate."""

    def test_detects_prefix_stripping(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_translation_pattern_elimination,
        )

        store = _store(tmp_path)
        # 2 translation patterns that strip dial prefix
        for i in range(1, 3):
            tp = _analyzed(CanonicalTranslationPattern(
                canonical_id=f"xlate:{i}", provenance=_prov(),
                name=f"TP{i}",
                matching_pattern=f"9.{i}XXX",
                replacement_pattern=f"{i}XXX",
            ))
            tp.pre_migration_state = {
                "pattern": f"9.{i}XXX",
                "calledPartyTransformationMask": f"{i}XXX",
            }
            store.upsert_object(tp)

        findings = detect_translation_pattern_elimination(store)
        assert len(findings) >= 1
        assert findings[0].category == "eliminate"

    def test_skips_non_normalization_patterns(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_translation_pattern_elimination,
        )

        store = _store(tmp_path)
        # Translation pattern that does real transformation (not prefix strip)
        tp = _analyzed(CanonicalTranslationPattern(
            canonical_id="xlate:1", provenance=_prov(),
            name="TP1",
            matching_pattern="5XXX",
            replacement_pattern="+14085551XXX",
        ))
        tp.pre_migration_state = {
            "pattern": "5XXX",
            "calledPartyTransformationMask": "+14085551XXX",
        }
        store.upsert_object(tp)

        findings = detect_translation_pattern_elimination(store)
        # Single pattern shouldn't fire (need count >= 2)
        assert len(findings) == 0


# ===================================================================
# Pattern 4: Device Bulk Upgrade
# ===================================================================

class TestDeviceBulkUpgrade:
    """Spec Pattern 4: 3+ devices of same incompatible model → upgrade plan."""

    def test_groups_by_model(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_device_bulk_upgrade,
        )

        store = _store(tmp_path)
        # 4 DEVICE_INCOMPATIBLE decisions for same model
        for i in range(4):
            store.save_decision({
                "decision_id": f"D{i:04d}",
                "type": "DEVICE_INCOMPATIBLE",
                "severity": "HIGH",
                "summary": f"Device {i} incompatible",
                "context": {"cucm_model": "7941", "_affected_objects": [f"device:{i}"]},
                "options": [{"id": "replace", "label": "Replace", "impact": "new phone"}],
                "affected_objects": [f"device:{i}"],
                "fingerprint": f"fp{i:04d}",
                "run_id": "test-run",
            })

        findings = detect_device_bulk_upgrade(store)
        assert len(findings) >= 1
        assert findings[0].category == "migrate_as_is"

    def test_skips_small_counts(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_device_bulk_upgrade,
        )

        store = _store(tmp_path)
        # Only 2 DEVICE_INCOMPATIBLE decisions (below threshold of 3)
        for i in range(2):
            store.save_decision({
                "decision_id": f"D{i:04d}",
                "type": "DEVICE_INCOMPATIBLE",
                "severity": "HIGH",
                "summary": f"Device {i} incompatible",
                "context": {"cucm_model": "7941", "_affected_objects": [f"device:{i}"]},
                "options": [{"id": "replace", "label": "Replace", "impact": "new phone"}],
                "affected_objects": [f"device:{i}"],
                "fingerprint": f"fp{i:04d}",
                "run_id": "test-run",
            })

        findings = detect_device_bulk_upgrade(store)
        assert len(findings) == 0


# ===================================================================
# Pattern 5: Location Consolidation
# ===================================================================

class TestLocationConsolidation:
    """Spec Pattern 5: Multiple locations same tz+region → consolidate."""

    def test_detects_consolidation_opportunity(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_location_consolidation,
        )

        store = _store(tmp_path)
        # 3 locations with same timezone and region
        for i in range(1, 4):
            loc = _analyzed(CanonicalLocation(
                canonical_id=f"location:{i}", provenance=_prov(),
                name=f"DP_HQ_{i}",
                time_zone="America/Chicago",
            ))
            loc.pre_migration_state = {
                "name": f"DP_HQ_{i}",
                "cucm_region_name": "HQ_Region",
                "cucm_date_time_group": "CMLocal",
            }
            store.upsert_object(loc)

        findings = detect_location_consolidation(store)
        assert len(findings) >= 1
        assert findings[0].category == "rebuild"

    def test_different_timezones_no_finding(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_location_consolidation,
        )

        store = _store(tmp_path)
        # Locations with different timezones
        for i, tz in enumerate(["America/Chicago", "America/New_York", "America/Los_Angeles"]):
            loc = _analyzed(CanonicalLocation(
                canonical_id=f"location:{i}", provenance=_prov(),
                name=f"DP_{i}",
                time_zone=tz,
            ))
            loc.pre_migration_state = {
                "name": f"DP_{i}",
                "cucm_region_name": f"Region_{i}",
            }
            store.upsert_object(loc)

        findings = detect_location_consolidation(store)
        assert len(findings) == 0


# ===================================================================
# Pattern 8: Trunk Destination Consolidation
# ===================================================================

class TestTrunkDestinationConsolidation:
    """Spec Pattern 8: Trunks same destination → finding."""

    def test_detects_same_destination(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_trunk_destination_consolidation,
        )

        store = _store(tmp_path)
        for i in range(1, 3):
            trunk = _analyzed(CanonicalTrunk(
                canonical_id=f"trunk:{i}", provenance=_prov(),
                name=f"Trunk{i}",
                address="sbc.company.com",
            ))
            trunk.pre_migration_state = {
                "name": f"Trunk{i}",
                "destinations": [{"addressIpv4": "sbc.company.com"}],
            }
            store.upsert_object(trunk)

        findings = detect_trunk_destination_consolidation(store)
        assert len(findings) >= 1
        assert findings[0].category == "rebuild"

    def test_different_destinations_no_finding(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_trunk_destination_consolidation,
        )

        store = _store(tmp_path)
        for i, addr in enumerate(["sbc1.company.com", "sbc2.company.com"]):
            trunk = _analyzed(CanonicalTrunk(
                canonical_id=f"trunk:{i}", provenance=_prov(),
                name=f"Trunk{i}",
                address=addr,
            ))
            trunk.pre_migration_state = {
                "name": f"Trunk{i}",
                "destinations": [{"addressIpv4": addr}],
            }
            store.upsert_object(trunk)

        findings = detect_trunk_destination_consolidation(store)
        assert len(findings) == 0


# ===================================================================
# Pattern 9: Voicemail Pilot Simplification
# ===================================================================

class TestVoicemailPilotSimplification:
    """Spec Pattern 9: Multiple VM pilots → finding."""

    def test_detects_multiple_pilots(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_voicemail_pilot_simplification,
        )

        store = _store(tmp_path)
        for i in range(1, 4):
            store.conn.execute(
                "INSERT OR REPLACE INTO objects (canonical_id, object_type, status, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (f"vm_pilot:{i}", "voicemail_pilot", "analyzed",
                 f'{{"canonical_id": "vm_pilot:{i}", "name": "VMP{i}", "pre_migration_state": {{"name": "VMP{i}", "voice_mail_pilot_number": "8000{i}", "css_name": "VM_CSS"}}, "provenance": {{"source_system": "cucm", "source_id": "t", "source_name": "t", "extracted_at": "2026-01-01T00:00:00Z"}}}}',
                 "2026-01-01", "2026-01-01"),
            )
        store.conn.commit()

        findings = detect_voicemail_pilot_simplification(store)
        assert len(findings) >= 1
        assert findings[0].category == "eliminate"

    def test_single_pilot_no_finding(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_voicemail_pilot_simplification,
        )

        store = _store(tmp_path)
        store.conn.execute(
            "INSERT OR REPLACE INTO objects (canonical_id, object_type, status, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("vm_pilot:1", "voicemail_pilot", "analyzed",
             '{"canonical_id": "vm_pilot:1", "name": "VMP1", "pre_migration_state": {"name": "VMP1", "voice_mail_pilot_number": "80001"}, "provenance": {"source_system": "cucm", "source_id": "t", "source_name": "t", "extracted_at": "2026-01-01T00:00:00Z"}}',
             "2026-01-01", "2026-01-01"),
        )
        store.conn.commit()

        findings = detect_voicemail_pilot_simplification(store)
        assert len(findings) == 0


# ===================================================================
# Pattern 10: Over-Engineered Dial Plan
# ===================================================================

class TestOverEngineeredDialPlan:
    """Spec Pattern 10: Patterns matching extension range → finding."""

    def test_detects_extension_range_patterns(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_overengineered_dial_plan,
        )

        store = _store(tmp_path)
        # 2+ dial plans with extension-range patterns
        for i in range(1, 3):
            dp = _analyzed(CanonicalDialPlan(
                canonical_id=f"dial_plan:{i}", provenance=_prov(),
                name=f"DP{i}",
                dial_patterns=[f"[1-9]XXX"],
            ))
            dp.pre_migration_state = {"name": f"DP{i}"}
            store.upsert_object(dp)

        findings = detect_overengineered_dial_plan(store)
        assert len(findings) >= 1
        assert findings[0].category == "eliminate"

    def test_skips_non_extension_patterns(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_overengineered_dial_plan,
        )

        store = _store(tmp_path)
        dp = _analyzed(CanonicalDialPlan(
            canonical_id="dial_plan:1", provenance=_prov(),
            name="DP1",
            dial_patterns=["+1408555XXXX"],
        ))
        dp.pre_migration_state = {"name": "DP1"}
        store.upsert_object(dp)

        findings = detect_overengineered_dial_plan(store)
        assert len(findings) == 0


# ===================================================================
# Pattern 15: Media Resource Scope Removal
# ===================================================================

class TestMediaResourceScopeRemoval:
    """Spec Pattern 15: Device pools with MRGL → finding."""

    def test_detects_mrgl_references(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_media_resource_scope_removal,
        )

        store = _store(tmp_path)
        for i in range(1, 3):
            store.conn.execute(
                "INSERT OR REPLACE INTO objects (canonical_id, object_type, status, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (f"device_pool:{i}", "device_pool", "analyzed",
                 f'{{"canonical_id": "device_pool:{i}", "name": "DP{i}", "pre_migration_state": {{"name": "DP{i}", "cucm_media_resource_list": "MRGL_HQ"}}, "provenance": {{"source_system": "cucm", "source_id": "t", "source_name": "t", "extracted_at": "2026-01-01T00:00:00Z"}}}}',
                 "2026-01-01", "2026-01-01"),
            )
        store.conn.commit()

        findings = detect_media_resource_scope_removal(store)
        assert len(findings) >= 1
        assert findings[0].category == "out_of_scope"
        assert findings[0].severity == "INFO"

    def test_no_mrgl_no_finding(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_media_resource_scope_removal,
        )

        store = _store(tmp_path)
        store.conn.execute(
            "INSERT OR REPLACE INTO objects (canonical_id, object_type, status, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("device_pool:1", "device_pool", "analyzed",
             '{"canonical_id": "device_pool:1", "name": "DP1", "pre_migration_state": {"name": "DP1"}, "provenance": {"source_system": "cucm", "source_id": "t", "source_name": "t", "extracted_at": "2026-01-01T00:00:00Z"}}',
             "2026-01-01", "2026-01-01"),
        )
        store.conn.commit()

        findings = detect_media_resource_scope_removal(store)
        assert len(findings) == 0


# ===================================================================
# Pattern 3: Hunt Pilot Reclassification
# ===================================================================

class TestHuntPilotReclassification:
    """Spec Pattern 3: HG with queue-like behavior → finding."""

    def test_detects_queue_signals(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_hunt_pilot_reclassification,
        )

        store = _store(tmp_path)
        from wxcli.migration.models import CanonicalHuntGroup
        hg = _analyzed(CanonicalHuntGroup(
            canonical_id="hunt_group:1", provenance=_prov(),
            name="HG1",
            agents=[f"user:{i}" for i in range(8)],  # > 6 agents
            policy="CIRCULAR",
        ))
        hg.pre_migration_state = {
            "name": "HG1",
            "distributionAlgorithm": "Circular",
            "voiceMailUsage": "PERSONAL_GREETING",
        }
        store.upsert_object(hg)

        findings = detect_hunt_pilot_reclassification(store)
        assert len(findings) >= 1
        assert findings[0].category == "rebuild"
        assert findings[0].severity == "HIGH"

    def test_skips_simple_hunt_group(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_hunt_pilot_reclassification,
        )

        store = _store(tmp_path)
        from wxcli.migration.models import CanonicalHuntGroup
        hg = _analyzed(CanonicalHuntGroup(
            canonical_id="hunt_group:1", provenance=_prov(),
            name="HG1",
            agents=["user:1", "user:2"],  # ≤ 6 agents
            policy="SIMULTANEOUS",
        ))
        hg.pre_migration_state = {
            "name": "HG1",
            "distributionAlgorithm": "Top Down",
            "voiceMailUsage": "NONE",
        }
        store.upsert_object(hg)

        findings = detect_hunt_pilot_reclassification(store)
        assert len(findings) == 0


# ===================================================================
# Pattern 6: Shared Line Simplification
# ===================================================================

class TestSharedLineSimplification:
    """Spec Pattern 6: Monitoring-only secondary appearances → finding."""

    def test_detects_monitoring_only(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_shared_line_simplification,
        )

        store = _store(tmp_path)
        store.save_decision({
            "decision_id": "D0001",
            "type": "SHARED_LINE_COMPLEX",
            "severity": "MEDIUM",
            "summary": "Shared line complex",
            "context": {
                "appearances": [
                    {"lineText": "Main Line", "owner": "user:1"},
                    {"lineText": "BLF Monitor", "owner": "user:2"},
                    {"lineText": "Busy Lamp Field", "owner": "user:3"},
                ],
                "_affected_objects": ["line:1"],
            },
            "options": [{"id": "shared_line", "label": "Shared Line", "impact": "keep"}],
            "affected_objects": ["line:1"],
            "fingerprint": "fp0001",
            "run_id": "test-run",
        })

        findings = detect_shared_line_simplification(store)
        assert len(findings) >= 1
        assert findings[0].category == "rebuild"

    def test_skips_non_monitoring(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_shared_line_simplification,
        )

        store = _store(tmp_path)
        store.save_decision({
            "decision_id": "D0001",
            "type": "SHARED_LINE_COMPLEX",
            "severity": "MEDIUM",
            "summary": "Shared line complex",
            "context": {
                "appearances": [
                    {"lineText": "Main Line", "owner": "user:1"},
                    {"lineText": "Reception Desk", "owner": "user:2"},
                ],
                "_affected_objects": ["line:1"],
            },
            "options": [{"id": "shared_line", "label": "Shared Line", "impact": "keep"}],
            "affected_objects": ["line:1"],
            "fingerprint": "fp0001",
            "run_id": "test-run",
        })

        findings = detect_shared_line_simplification(store)
        assert len(findings) == 0


# ===================================================================
# Pattern 7: Partition-Based Time Routing
# ===================================================================

class TestPartitionTimeRouting:
    """Spec Pattern 7: Partitions with time schedules → finding."""

    def test_detects_time_schedules(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_partition_time_routing,
        )

        store = _store(tmp_path)
        store.conn.execute(
            "INSERT OR REPLACE INTO objects (canonical_id, object_type, status, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("partition:1", "route_partition", "analyzed",
             '{"canonical_id": "partition:1", "name": "PT_BizHours", "pre_migration_state": {"name": "PT_BizHours", "timeScheduleIdName": "BizHoursSchedule"}, "provenance": {"source_system": "cucm", "source_id": "t", "source_name": "t", "extracted_at": "2026-01-01T00:00:00Z"}}',
             "2026-01-01", "2026-01-01"),
        )
        store.conn.commit()

        findings = detect_partition_time_routing(store)
        assert len(findings) >= 1
        assert findings[0].category == "eliminate"
        assert findings[0].severity == "MEDIUM"

    def test_no_schedule_no_finding(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_partition_time_routing,
        )

        store = _store(tmp_path)
        store.conn.execute(
            "INSERT OR REPLACE INTO objects (canonical_id, object_type, status, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("partition:1", "route_partition", "analyzed",
             '{"canonical_id": "partition:1", "name": "PT_Internal", "pre_migration_state": {"name": "PT_Internal"}, "provenance": {"source_system": "cucm", "source_id": "t", "source_name": "t", "extracted_at": "2026-01-01T00:00:00Z"}}',
             "2026-01-01", "2026-01-01"),
        )
        store.conn.commit()

        findings = detect_partition_time_routing(store)
        assert len(findings) == 0


# ===================================================================
# Pattern 11: Partition Ordering Loss (CRITICAL)
# ===================================================================

class TestPartitionOrderingLoss:
    """Spec Pattern 11: CSS with overlapping patterns at different positions."""

    def test_detects_ordering_conflict(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_partition_ordering_loss,
        )

        store = _store(tmp_path)
        # CSS with 2 partitions, each with overlapping patterns going to different destinations
        store.conn.execute(
            "INSERT OR REPLACE INTO objects (canonical_id, object_type, status, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("css:1", "calling_search_space", "analyzed",
             '{"canonical_id": "css:1", "name": "CSS_Main", "pre_migration_state": {"name": "CSS_Main"}, "provenance": {"source_system": "cucm", "source_id": "t", "source_name": "t", "extracted_at": "2026-01-01T00:00:00Z"}}',
             "2026-01-01", "2026-01-01"),
        )
        for i, (part_name, pat, dest) in enumerate([
            ("PT_Internal", "9XXX", "gw:internal"),
            ("PT_External", "9XXX", "gw:external"),
        ]):
            store.conn.execute(
                "INSERT OR REPLACE INTO objects (canonical_id, object_type, status, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (f"partition:{i}", "route_partition", "analyzed",
                 f'{{"canonical_id": "partition:{i}", "name": "{part_name}", "pre_migration_state": {{"name": "{part_name}"}}, "provenance": {{"source_system": "cucm", "source_id": "t", "source_name": "t", "extracted_at": "2026-01-01T00:00:00Z"}}}}',
                 "2026-01-01", "2026-01-01"),
            )
            store.conn.execute(
                "INSERT OR REPLACE INTO objects (canonical_id, object_type, status, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (f"route_pattern:p{i}", "route_pattern", "analyzed",
                 f'{{"canonical_id": "route_pattern:p{i}", "pre_migration_state": {{"pattern": "{pat}", "destination": "{dest}"}}, "provenance": {{"source_system": "cucm", "source_id": "t", "source_name": "t", "extracted_at": "2026-01-01T00:00:00Z"}}}}',
                 "2026-01-01", "2026-01-01"),
            )
            store.add_cross_ref(f"partition:{i}", f"route_pattern:p{i}", "partition_has_pattern", ordinal=0)
            store.add_cross_ref("css:1", f"partition:{i}", "css_contains_partition", ordinal=i)
        store.conn.commit()

        findings = detect_partition_ordering_loss(store)
        assert len(findings) >= 1
        assert findings[0].severity == "CRITICAL"
        assert findings[0].category == "rebuild"
        # Affected objects should include CSS + partitions + route patterns
        affected = findings[0].affected_objects
        assert "css:1" in affected
        assert "partition:0" in affected or "partition:1" in affected
        assert "route_pattern:p0" in affected or "route_pattern:p1" in affected

    def test_non_overlapping_no_finding(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_partition_ordering_loss,
        )

        store = _store(tmp_path)
        store.conn.execute(
            "INSERT OR REPLACE INTO objects (canonical_id, object_type, status, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("css:1", "calling_search_space", "analyzed",
             '{"canonical_id": "css:1", "name": "CSS_Main", "pre_migration_state": {"name": "CSS_Main"}, "provenance": {"source_system": "cucm", "source_id": "t", "source_name": "t", "extracted_at": "2026-01-01T00:00:00Z"}}',
             "2026-01-01", "2026-01-01"),
        )
        # Non-overlapping patterns: 2XXX and 5XXX
        for i, (part_name, pat, dest) in enumerate([
            ("PT_A", "2XXX", "gw:a"),
            ("PT_B", "5XXX", "gw:b"),
        ]):
            store.conn.execute(
                "INSERT OR REPLACE INTO objects (canonical_id, object_type, status, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (f"partition:{i}", "route_partition", "analyzed",
                 f'{{"canonical_id": "partition:{i}", "name": "{part_name}", "pre_migration_state": {{"name": "{part_name}"}}, "provenance": {{"source_system": "cucm", "source_id": "t", "source_name": "t", "extracted_at": "2026-01-01T00:00:00Z"}}}}',
                 "2026-01-01", "2026-01-01"),
            )
            store.conn.execute(
                "INSERT OR REPLACE INTO objects (canonical_id, object_type, status, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (f"route_pattern:p{i}", "route_pattern", "analyzed",
                 f'{{"canonical_id": "route_pattern:p{i}", "pre_migration_state": {{"pattern": "{pat}", "destination": "{dest}"}}, "provenance": {{"source_system": "cucm", "source_id": "t", "source_name": "t", "extracted_at": "2026-01-01T00:00:00Z"}}}}',
                 "2026-01-01", "2026-01-01"),
            )
            store.add_cross_ref(f"partition:{i}", f"route_pattern:p{i}", "partition_has_pattern", ordinal=0)
            store.add_cross_ref("css:1", f"partition:{i}", "css_contains_partition", ordinal=i)
        store.conn.commit()

        findings = detect_partition_ordering_loss(store)
        assert len(findings) == 0

    def test_same_destination_no_finding(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_partition_ordering_loss,
        )

        store = _store(tmp_path)
        store.conn.execute(
            "INSERT OR REPLACE INTO objects (canonical_id, object_type, status, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("css:1", "calling_search_space", "analyzed",
             '{"canonical_id": "css:1", "name": "CSS_Main", "pre_migration_state": {"name": "CSS_Main"}, "provenance": {"source_system": "cucm", "source_id": "t", "source_name": "t", "extracted_at": "2026-01-01T00:00:00Z"}}',
             "2026-01-01", "2026-01-01"),
        )
        # Same pattern, same destination (no ambiguity)
        for i, part_name in enumerate(["PT_A", "PT_B"]):
            store.conn.execute(
                "INSERT OR REPLACE INTO objects (canonical_id, object_type, status, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (f"partition:{i}", "route_partition", "analyzed",
                 f'{{"canonical_id": "partition:{i}", "name": "{part_name}", "pre_migration_state": {{"name": "{part_name}"}}, "provenance": {{"source_system": "cucm", "source_id": "t", "source_name": "t", "extracted_at": "2026-01-01T00:00:00Z"}}}}',
                 "2026-01-01", "2026-01-01"),
            )
            store.conn.execute(
                "INSERT OR REPLACE INTO objects (canonical_id, object_type, status, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (f"route_pattern:p{i}", "route_pattern", "analyzed",
                 f'{{"canonical_id": "route_pattern:p{i}", "pre_migration_state": {{"pattern": "9XXX", "destination": "gw:same"}}, "provenance": {{"source_system": "cucm", "source_id": "t", "source_name": "t", "extracted_at": "2026-01-01T00:00:00Z"}}}}',
                 "2026-01-01", "2026-01-01"),
            )
            store.add_cross_ref(f"partition:{i}", f"route_pattern:p{i}", "partition_has_pattern", ordinal=0)
            store.add_cross_ref("css:1", f"partition:{i}", "css_contains_partition", ordinal=i)
        store.conn.commit()

        findings = detect_partition_ordering_loss(store)
        assert len(findings) == 0


# ===================================================================
# Pattern 12: CPN Transformation Chain
# ===================================================================

class TestCPNTransformationChain:
    """Spec Pattern 12: Route patterns with CPN transformations."""

    def test_detects_calling_transform(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_cpn_transformation_chain,
        )

        store = _store(tmp_path)
        store.conn.execute(
            "INSERT OR REPLACE INTO objects (canonical_id, object_type, status, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("route_pattern:1", "route_pattern", "analyzed",
             '{"canonical_id": "route_pattern:1", "pre_migration_state": {"pattern": "9.!", "callingPartyTransformationMask": "+14085551000"}, "provenance": {"source_system": "cucm", "source_id": "t", "source_name": "t", "extracted_at": "2026-01-01T00:00:00Z"}}',
             "2026-01-01", "2026-01-01"),
        )
        store.conn.commit()

        findings = detect_cpn_transformation_chain(store)
        assert len(findings) >= 1
        assert findings[0].category == "rebuild"

    def test_no_transforms_no_finding(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_cpn_transformation_chain,
        )

        store = _store(tmp_path)
        store.conn.execute(
            "INSERT OR REPLACE INTO objects (canonical_id, object_type, status, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("route_pattern:1", "route_pattern", "analyzed",
             '{"canonical_id": "route_pattern:1", "pre_migration_state": {"pattern": "9.!"}, "provenance": {"source_system": "cucm", "source_id": "t", "source_name": "t", "extracted_at": "2026-01-01T00:00:00Z"}}',
             "2026-01-01", "2026-01-01"),
        )
        store.conn.commit()

        findings = detect_cpn_transformation_chain(store)
        assert len(findings) == 0

    def test_multi_level_chain(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_cpn_transformation_chain,
        )

        store = _store(tmp_path)
        # Route pattern with transform
        store.conn.execute(
            "INSERT OR REPLACE INTO objects (canonical_id, object_type, status, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("route_pattern:1", "route_pattern", "analyzed",
             '{"canonical_id": "route_pattern:1", "pre_migration_state": {"pattern": "9.!", "callingPartyTransformationMask": "+14085551000"}, "provenance": {"source_system": "cucm", "source_id": "t", "source_name": "t", "extracted_at": "2026-01-01T00:00:00Z"}}',
             "2026-01-01", "2026-01-01"),
        )
        # Trunk with transform
        trunk = _analyzed(CanonicalTrunk(
            canonical_id="trunk:1", provenance=_prov(),
            name="Trunk1", address="sbc.com",
        ))
        trunk.pre_migration_state = {
            "name": "Trunk1",
            "callingPartyTransformationMask": "+14085550000",
        }
        store.upsert_object(trunk)
        store.conn.commit()

        findings = detect_cpn_transformation_chain(store)
        assert len(findings) >= 1
        assert "Multi-level" in findings[0].detail


# ===================================================================
# Pattern 13: PSTN Connection Type
# ===================================================================

class TestPSTNConnectionType:
    """Spec Pattern 13: Trunk topology → PSTN recommendation."""

    def test_sbc_trunk_local_gateway(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_pstn_connection_type,
        )

        store = _store(tmp_path)
        trunk = _analyzed(CanonicalTrunk(
            canonical_id="trunk:1", provenance=_prov(),
            name="CUBE_HQ", address="cube.company.com",
        ))
        trunk.pre_migration_state = {"name": "CUBE_HQ"}
        store.upsert_object(trunk)
        # Device pool with SRST
        store.conn.execute(
            "INSERT OR REPLACE INTO objects (canonical_id, object_type, status, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("device_pool:1", "device_pool", "analyzed",
             '{"canonical_id": "device_pool:1", "pre_migration_state": {"cucm_srst": "SRST_HQ"}, "provenance": {"source_system": "cucm", "source_id": "t", "source_name": "t", "extracted_at": "2026-01-01T00:00:00Z"}}',
             "2026-01-01", "2026-01-01"),
        )
        store.conn.commit()

        findings = detect_pstn_connection_type(store)
        assert len(findings) >= 1
        assert "Local Gateway" in findings[0].summary

    def test_no_trunks_cloud_pstn(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_pstn_connection_type,
        )

        store = _store(tmp_path)
        # Empty store with just a device pool (no trunks)
        store.conn.execute(
            "INSERT OR REPLACE INTO objects (canonical_id, object_type, status, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("device_pool:1", "device_pool", "analyzed",
             '{"canonical_id": "device_pool:1", "pre_migration_state": {}, "provenance": {"source_system": "cucm", "source_id": "t", "source_name": "t", "extracted_at": "2026-01-01T00:00:00Z"}}',
             "2026-01-01", "2026-01-01"),
        )
        store.conn.commit()

        findings = detect_pstn_connection_type(store)
        assert len(findings) >= 1
        assert "Cloud Connected PSTN" in findings[0].summary

    def test_carrier_sip_no_srst(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_pstn_connection_type,
        )

        store = _store(tmp_path)
        trunk = _analyzed(CanonicalTrunk(
            canonical_id="trunk:1", provenance=_prov(),
            name="Carrier_SIP", address="sip.carrier.com",
        ))
        trunk.pre_migration_state = {"name": "Carrier_SIP"}
        store.upsert_object(trunk)

        findings = detect_pstn_connection_type(store)
        assert len(findings) >= 1
        assert "Cloud Connected PSTN" in findings[0].summary or "PSTN" in findings[0].summary


# ===================================================================
# Pattern 14: Globalized vs. Localized
# ===================================================================

class TestGlobalizedVsLocalized:
    """Spec Pattern 14: Dial plan style detection."""

    def test_detects_globalized(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_globalized_vs_localized,
        )

        store = _store(tmp_path)
        # 3 E.164 patterns, 1 local → >50% E.164
        for i, pat in enumerate(["+14085551234", "+14085555678", "+442012345678", "9XXX"]):
            store.conn.execute(
                "INSERT OR REPLACE INTO objects (canonical_id, object_type, status, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (f"route_pattern:{i}", "route_pattern", "analyzed",
                 f'{{"canonical_id": "route_pattern:{i}", "pre_migration_state": {{"pattern": "{pat}"}}, "provenance": {{"source_system": "cucm", "source_id": "t", "source_name": "t", "extracted_at": "2026-01-01T00:00:00Z"}}}}',
                 "2026-01-01", "2026-01-01"),
            )
        store.conn.commit()

        findings = detect_globalized_vs_localized(store)
        assert len(findings) >= 1
        assert "globalized" in findings[0].summary

    def test_detects_localized(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_globalized_vs_localized,
        )

        store = _store(tmp_path)
        # 5 local patterns, 0 E.164 → <20%
        for i, pat in enumerate(["9.XXXX", "8.XXXX", "7XXX", "6XXX", "5XXX"]):
            store.conn.execute(
                "INSERT OR REPLACE INTO objects (canonical_id, object_type, status, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (f"route_pattern:{i}", "route_pattern", "analyzed",
                 f'{{"canonical_id": "route_pattern:{i}", "pre_migration_state": {{"pattern": "{pat}"}}, "provenance": {{"source_system": "cucm", "source_id": "t", "source_name": "t", "extracted_at": "2026-01-01T00:00:00Z"}}}}',
                 "2026-01-01", "2026-01-01"),
            )
        store.conn.commit()

        findings = detect_globalized_vs_localized(store)
        assert len(findings) >= 1
        assert "localized" in findings[0].summary


# ===================================================================
# Pattern 16: E911 Migration Flag
# ===================================================================

class TestE911MigrationFlag:
    """Spec Pattern 16: E911/ELIN patterns → out_of_scope."""

    def test_detects_e911_partition(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_e911_migration_flag,
        )

        store = _store(tmp_path)
        store.conn.execute(
            "INSERT OR REPLACE INTO objects (canonical_id, object_type, status, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("partition:e911", "route_partition", "analyzed",
             '{"canonical_id": "partition:e911", "name": "E911_PT", "pre_migration_state": {"name": "E911_PT"}, "provenance": {"source_system": "cucm", "source_id": "t", "source_name": "t", "extracted_at": "2026-01-01T00:00:00Z"}}',
             "2026-01-01", "2026-01-01"),
        )
        store.conn.commit()

        findings = detect_e911_migration_flag(store)
        assert len(findings) >= 1
        assert findings[0].category == "out_of_scope"
        assert findings[0].severity == "HIGH"

    def test_no_e911_still_warns(self, tmp_path):
        from wxcli.migration.advisory.advisory_patterns import (
            detect_e911_migration_flag,
        )

        store = _store(tmp_path)
        # No E911 signals — should still produce a warning about CER
        findings = detect_e911_migration_flag(store)
        assert len(findings) >= 1
        assert "CER" in findings[0].detail
