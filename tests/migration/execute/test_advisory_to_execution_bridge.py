"""Tests for the advisory-to-execution bridge.

Wires canonical object types that previously had mappers but no planner
expander or handler. See docs/superpowers/plans/2026-04-11-advisory-to-execution-bridge.md.
"""
from datetime import datetime, timezone

from wxcli.migration.execute import TIER_ASSIGNMENTS, API_CALL_ESTIMATES
from wxcli.migration.execute.planner import (
    _DATA_ONLY_TYPES,
    _EXPANDERS,
    expand_to_operations,
)
from wxcli.migration.execute.handlers import HANDLER_REGISTRY
from wxcli.migration.models import (
    CanonicalAnnouncement,
    CanonicalE911Config,
    CanonicalLocationSchedule,
    CanonicalMusicOnHold,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore


def _prov() -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id="t",
        source_name="t",
        extracted_at=datetime.now(timezone.utc),
    )


class TestLocationScheduleFlowsThroughScheduleExpander:
    """CanonicalLocationSchedule uses canonical_id prefix 'schedule:' so it
    already runs through the existing _expand_schedule path. Verify nothing
    new is needed for this type."""

    def test_location_schedule_produces_schedule_create_op(self):
        store = MigrationStore(":memory:")
        sched = CanonicalLocationSchedule(
            canonical_id="schedule:abc123",
            provenance=_prov(),
            status=MigrationStatus.ANALYZED,
            name="Business Hours",
            schedule_type="businessHours",
            location_id="location:dallas",
            events=[{"name": "weekday", "startDate": "2026-01-01"}],
        )
        store.upsert_object(sched)

        ops = expand_to_operations(store)

        assert len(ops) == 1
        op = ops[0]
        assert op.resource_type == "schedule"
        assert op.op_type == "create"
        assert op.canonical_id == "schedule:abc123"
        assert op.batch == "location:dallas"

    def test_schedule_expander_entry_exists(self):
        assert "schedule" in _EXPANDERS


class TestDeviceProfileAlreadyWired:
    """device_profile and hoteling_location were wired by the hoteling-migration
    merge. Snapshot their registry entries so regressions get flagged."""

    def test_device_profile_expander_registered(self):
        assert "device_profile" in _EXPANDERS
        assert "hoteling_location" in _EXPANDERS

    def test_device_profile_handlers_registered(self):
        assert ("device_profile", "enable_hoteling_guest") in HANDLER_REGISTRY
        assert ("device_profile", "enable_hoteling_host") in HANDLER_REGISTRY
        assert ("hoteling_location", "enable_hotdesking") in HANDLER_REGISTRY

    def test_device_profile_tier_assignments(self):
        assert TIER_ASSIGNMENTS[("device_profile", "enable_hoteling_guest")] == 5
        assert TIER_ASSIGNMENTS[("device_profile", "enable_hoteling_host")] == 5
        assert TIER_ASSIGNMENTS[("hoteling_location", "enable_hotdesking")] == 0

    def test_device_profile_api_estimates(self):
        assert API_CALL_ESTIMATES["device_profile:enable_hoteling_guest"] == 1
        assert API_CALL_ESTIMATES["device_profile:enable_hoteling_host"] == 1
        assert API_CALL_ESTIMATES["hoteling_location:enable_hotdesking"] == 1


class TestE911ConfigIsDataOnly:
    """CUCM E911 (ELIN) and Webex E911 (civic address + RedSky) are
    architecturally different. e911_config objects exist for the report
    and for ARCHITECTURE_ADVISORY decisions — they never produce
    execution ops. ECBN per-user config belongs in user:configure_settings."""

    def test_e911_config_in_data_only_types(self):
        assert "e911_config" in _DATA_ONLY_TYPES

    def test_e911_config_object_produces_zero_ops(self):
        store = MigrationStore(":memory:")
        cfg = CanonicalE911Config(
            canonical_id="e911_config:Main-ELIN",
            provenance=_prov(),
            status=MigrationStatus.ANALYZED,
            elin_group_name="Main-ELIN",
            elin_numbers=["+1-555-0100"],
        )
        store.upsert_object(cfg)

        ops = expand_to_operations(store)

        assert ops == []
