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


class TestMusicOnHoldExpander:
    """music_on_hold was a planner dead end. Wire it as a visible Phase-A
    op with a no-op handler. Real API calls deferred to Phase B."""

    def test_music_on_hold_expander_registered(self):
        assert "music_on_hold" in _EXPANDERS

    def test_default_source_produces_one_configure_op(self):
        store = MigrationStore(":memory:")
        moh = CanonicalMusicOnHold(
            canonical_id="music_on_hold:SampleAudioSource",
            provenance=_prov(),
            status=MigrationStatus.ANALYZED,
            source_name="SampleAudioSource",
            is_default=True,
            cucm_source_id="1",
        )
        store.upsert_object(moh)

        ops = expand_to_operations(store)

        assert len(ops) == 1
        op = ops[0]
        assert op.resource_type == "music_on_hold"
        assert op.op_type == "configure"
        assert op.canonical_id == "music_on_hold:SampleAudioSource"

    def test_custom_source_also_produces_one_op(self):
        """Custom sources still produce an op so operators see them in the
        plan. The AUDIO_ASSET_MANUAL decision from MOHMapper gates the
        actual behavior — Phase A handler is still a no-op."""
        store = MigrationStore(":memory:")
        moh = CanonicalMusicOnHold(
            canonical_id="music_on_hold:CustomHoldMusic",
            provenance=_prov(),
            status=MigrationStatus.ANALYZED,
            source_name="CustomHoldMusic",
            source_file_name="hold.wav",
            is_default=False,
            cucm_source_id="2",
        )
        store.upsert_object(moh)

        ops = expand_to_operations(store)

        assert len(ops) == 1
        assert ops[0].resource_type == "music_on_hold"


class TestMusicOnHoldHandler:
    def test_handler_registered(self):
        assert ("music_on_hold", "configure") in HANDLER_REGISTRY

    def test_handler_returns_empty_list_phase_a(self):
        """Phase A handler is a no-op — engine marks the op completed
        without making any API call. Real API calls deferred to Phase B."""
        from wxcli.migration.execute.handlers import handle_music_on_hold_configure

        data = {
            "canonical_id": "music_on_hold:SampleAudioSource",
            "source_name": "SampleAudioSource",
            "is_default": True,
        }
        result = handle_music_on_hold_configure(data, deps={}, ctx={"orgId": "org1"})

        assert result == []


class TestMusicOnHoldRegistry:
    def test_tier_assignment_exists(self):
        assert ("music_on_hold", "configure") in TIER_ASSIGNMENTS

    def test_api_call_estimate_is_zero_phase_a(self):
        """Phase A makes no API calls. Value must be 0 so
        TestHandlerRegistry.test_all_operation_types_have_handlers
        skips the handler requirement if that check ever matters."""
        assert API_CALL_ESTIMATES["music_on_hold:configure"] == 0


class TestAnnouncementExpander:
    """announcement was a planner dead end. Wire it as a visible Phase-A
    op with a no-op handler. Real multipart upload deferred to Phase B."""

    def test_announcement_expander_registered(self):
        assert "announcement" in _EXPANDERS

    def test_announcement_produces_one_upload_op(self):
        store = MigrationStore(":memory:")
        ann = CanonicalAnnouncement(
            canonical_id="announcement:Welcome",
            provenance=_prov(),
            status=MigrationStatus.ANALYZED,
            name="Welcome",
            file_name="welcome.wav",
            media_type="WAV",
            source_system="cucm",
        )
        store.upsert_object(ann)

        ops = expand_to_operations(store)

        assert len(ops) == 1
        op = ops[0]
        assert op.resource_type == "announcement"
        assert op.op_type == "upload"
        assert op.canonical_id == "announcement:Welcome"


class TestAnnouncementHandler:
    def test_handler_registered(self):
        assert ("announcement", "upload") in HANDLER_REGISTRY

    def test_handler_returns_empty_list_phase_a(self):
        """Phase A handler is a no-op — multipart audio upload is deferred
        to Phase B alongside engine multipart support. AnnouncementMapper
        creates AUDIO_ASSET_MANUAL decisions to inform operators."""
        from wxcli.migration.execute.handlers import handle_announcement_upload

        data = {
            "canonical_id": "announcement:Welcome",
            "name": "Welcome",
            "file_name": "welcome.wav",
        }
        result = handle_announcement_upload(data, deps={}, ctx={"orgId": "org1"})

        assert result == []


class TestAnnouncementRegistry:
    def test_tier_assignment_exists(self):
        assert ("announcement", "upload") in TIER_ASSIGNMENTS

    def test_tier_is_one(self):
        """Announcements are routing backbone — tier 1."""
        assert TIER_ASSIGNMENTS[("announcement", "upload")] == 1

    def test_api_call_estimate_is_zero_phase_a(self):
        assert API_CALL_ESTIMATES["announcement:upload"] == 0


class TestBridgeCoverage:
    """End-to-end: every canonical object type called out in the bridge
    spec is now either in _EXPANDERS or in _DATA_ONLY_TYPES. No more
    'No expansion pattern' warnings for these types."""

    _BRIDGE_TYPES = [
        "music_on_hold",
        "announcement",
        "e911_config",
        "device_profile",
        # location_schedule uses canonical_id prefix "schedule:" — obj_type
        # resolves to "schedule", which is in _EXPANDERS.
    ]

    def test_all_bridge_types_are_known(self):
        unknown = []
        for t in self._BRIDGE_TYPES:
            if t in _EXPANDERS:
                continue
            if t in _DATA_ONLY_TYPES:
                continue
            unknown.append(t)
        assert unknown == [], f"Bridge types still dead-ending: {unknown}"

    def test_planner_no_warnings_for_bridge_types(self, caplog):
        """Plant one object of each bridge type in the store and confirm
        the planner does not log 'No expansion pattern' for any of them."""
        import logging

        store = MigrationStore(":memory:")
        store.upsert_object(CanonicalMusicOnHold(
            canonical_id="music_on_hold:X", provenance=_prov(),
            status=MigrationStatus.ANALYZED, source_name="X", is_default=True,
        ))
        store.upsert_object(CanonicalAnnouncement(
            canonical_id="announcement:Y", provenance=_prov(),
            status=MigrationStatus.ANALYZED, name="Y", source_system="cucm",
        ))
        store.upsert_object(CanonicalE911Config(
            canonical_id="e911_config:Z", provenance=_prov(),
            status=MigrationStatus.ANALYZED, elin_group_name="Z",
        ))
        store.upsert_object(CanonicalLocationSchedule(
            canonical_id="schedule:abc", provenance=_prov(),
            status=MigrationStatus.ANALYZED, name="abc",
            schedule_type="businessHours", location_id="location:dallas",
        ))

        with caplog.at_level(logging.WARNING, logger="wxcli.migration.execute.planner"):
            expand_to_operations(store)

        for record in caplog.records:
            msg = record.getMessage()
            assert "No expansion pattern" not in msg, (
                f"Planner still warns about a bridge type: {msg}"
            )
