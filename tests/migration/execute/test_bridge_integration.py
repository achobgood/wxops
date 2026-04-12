"""End-to-end integration test for the advisory-to-execution bridge.

Builds a synthetic raw_data fixture containing all 5 bridge canonical types
(music_on_hold, announcement, e911_config, device_profile, location_schedule)
and runs the full normalize → map → analyze → expand_to_operations pipeline.
Asserts that each type produces the expected number of ops (or 0 for data-only).

This catches regressions where mapper→canonical→planner wiring breaks against
real raw data shapes, as opposed to the unit tests in
test_advisory_to_execution_bridge.py which construct Canonical* objects directly.
"""
import pytest
from wxcli.migration.execute.planner import expand_to_operations
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.pipeline import normalize_discovery
from wxcli.migration.transform.engine import TransformEngine
from wxcli.migration.transform.analysis_pipeline import AnalysisPipeline


def _ref(name: str, uuid: str = "") -> dict:
    """Build a zeep-style reference field."""
    return {"_value_1": name, "uuid": uuid or f"{{{name}-uuid}}"}


def _empty_ref() -> dict:
    return {"_value_1": None, "uuid": None}


def _auto_resolve_decisions(store: MigrationStore) -> None:
    """Auto-pick the first option for all unresolved decisions."""
    for d in store.get_all_decisions():
        if d.get("chosen_option") is None and d.get("options"):
            opt = d["options"][0]
            store.resolve_decision(
                d["decision_id"],
                opt["id"] if isinstance(opt, dict) else opt,
            )


def _bridge_raw_data() -> dict:
    """Synthetic CUCM environment with all 5 bridge object categories.

    Includes:
    - 2 MOH sources (1 default, 1 custom) → 2 music_on_hold:configure ops
    - 1 announcement → 1 announcement:upload op
    - 1 ELIN group → 0 ops (e911_config is data-only)
    - 1 device profile (UDP-jsmith) + matching user → device_profile ops
    - 1 time schedule + 1 time period → operating_mode:create ops

    Supporting objects: 1 location (device pool + datetime group + cucm location),
    1 user (jsmith), 1 phone (SEP001122334455), 1 partition, 1 CSS.

    NOTE: raw_data keys must match the RAW_DATA_MAPPING in normalizers.py:
      - phones go under "devices" → "phones" (not "phones" → "phones")
      - CSS/partitions go under "routing" → "css_list" / "partitions"
      - directory_numbers are NOT a normalizer key; they are derived from phones
    """
    return {
        # --- Locations (required by all mappers) ---
        "locations": {
            "device_pools": [
                {
                    "pkid": "{DP-HQ-0001}",
                    "name": "DP-HQ",
                    "dateTimeSettingName": _ref("DT-Eastern"),
                    "locationName": _ref("LOC-HQ"),
                    "callManagerGroupName": _ref("Default"),
                    "srstName": None,
                    "regionName": _ref("Default"),
                    "mediaResourceListName": None,
                },
            ],
            "datetime_groups": [
                {"pkid": "{DT-EAST-0001}", "name": "DT-Eastern", "timeZone": "America/New_York"},
            ],
            "cucm_locations": [
                {"pkid": "{LOC-HQ-0001}", "name": "LOC-HQ"},
            ],
        },

        # --- Users (required by device_profile mapper) ---
        "users": {
            "users": [
                {
                    "pkid": "{USR-JSMT-0001}",
                    "userid": "jsmith",
                    "firstName": "John",
                    "lastName": "Smith",
                    "mailid": "jsmith@acme.com",
                    "telephoneNumber": "+12125551001",
                    "department": "Engineering",
                    "title": "Engineer",
                    "manager": _empty_ref(),
                    "directoryUri": "jsmith@acme.com",
                    "userLocale": "English United States",
                    "selfService": None,
                    "enableCti": "true",
                    "associatedDevices": {"device": ["SEP001122334455"]},
                    "primaryExtension": {
                        "pattern": "1001",
                        "routePartitionName": _ref("PT-Internal"),
                    },
                    "callingSearchSpaceName": _ref("CSS-Internal"),
                    "voiceMailProfile": _empty_ref(),
                },
            ],
        },

        # --- Devices (phones) — RAW_DATA_MAPPING key is ("devices", "phones", "phone") ---
        "devices": {
            "phones": [
                {
                    "pkid": "{PHN-0001}",
                    "name": "SEP001122334455",
                    "product": "Cisco 8845",
                    "model": "Cisco 8845",
                    "protocol": "SIP",
                    "class": "Phone",
                    "devicePoolName": _ref("DP-HQ"),
                    "ownerUserName": "jsmith",
                    "callingSearchSpaceName": _ref("CSS-Internal"),
                    "lines": {
                        "line": [
                            {
                                "index": "1",
                                "display": "John Smith",
                                "e164Mask": "+12125551001",
                                "associatedEndusers": {"enduser": [{"userId": "jsmith"}]},
                                "dirn": {
                                    "pattern": "1001",
                                    "routePartitionName": _ref("PT-Internal"),
                                    "alertingName": "John Smith",
                                    "description": "John Smith Ext 1001",
                                    "shareLineAppearanceCssName": _empty_ref(),
                                    "callingSearchSpaceName": _ref("CSS-Internal"),
                                },
                            },
                        ],
                    },
                    "speeddials": [],
                    "busyLampFields": [],
                    "phoneTemplateName": _ref("Standard 8845 SIP"),
                    "softkeyTemplateName": None,
                    "deviceMobilityMode": "Default",
                },
            ],
        },

        # --- Routing — RAW_DATA_MAPPING uses ("routing", "partitions") and ("routing", "css_list") ---
        "routing": {
            "partitions": [
                {
                    "pkid": "{PT-INT-0001}",
                    "name": "PT-Internal",
                    "description": "Internal partition",
                },
            ],
            "css_list": [
                {
                    "pkid": "{CSS-INT-0001}",
                    "name": "CSS-Internal",
                    "description": "Internal calls",
                    "members": {
                        "member": [
                            {
                                "routePartitionName": _ref("PT-Internal"),
                                "index": "1",
                            },
                        ],
                    },
                },
            ],
            "route_patterns": [],
            "gateways": [],
            "sip_trunks": [],
            "route_groups": [],
            "route_lists": [],
            "translation_patterns": [],
        },

        # ===== BRIDGE TYPE 1: MOH Audio Sources =====
        "moh": {
            "moh_sources": [
                {
                    "name": "SampleAudioSource",
                    "sourceFileName": "",
                    "isDefault": "true",
                    "sourceId": "1",
                },
                {
                    "name": "CustomHoldMusic",
                    "sourceFileName": "custom_hold.wav",
                    "isDefault": "false",
                    "sourceId": "2",
                },
            ],
        },

        # ===== BRIDGE TYPE 2: Announcements =====
        "announcements": {
            "announcements": [
                {
                    "name": "Welcome Greeting",
                    "description": "Main AA welcome prompt",
                    "announcementFile": "welcome_greeting.wav",
                },
            ],
        },

        # ===== BRIDGE TYPE 3: E911 (ELIN Groups) =====
        "e911": {
            "elin_groups": [
                {
                    "name": "ELIN-HQ",
                    "description": "HQ Emergency Line",
                    "elinNumbers": ["+14085551911"],
                },
            ],
            "geo_locations": [],
        },

        # ===== BRIDGE TYPE 4: Device Profiles (Extension Mobility) =====
        "device_profiles": {
            "device_profiles": [
                {
                    "name": "UDP-jsmith",
                    "product": "Cisco 8845",
                    "protocol": "SIP",
                    "devicePoolName": _ref("DP-HQ"),
                    "lines": {
                        "line": [
                            {
                                "index": "1",
                                "dirn": {
                                    "pattern": "1001",
                                    "routePartitionName": _ref("PT-Internal"),
                                },
                            },
                        ],
                    },
                    "speeddials": [],
                    "busyLampFields": [],
                },
            ],
        },

        # ===== BRIDGE TYPE 5: Time Schedules + Periods =====
        # NOTE: These produce CanonicalOperatingMode (object_type=operating_mode)
        # via FeatureMapper._map_schedules. CanonicalLocationSchedule requires
        # an AA with business_schedule + location_id, which can't be exercised
        # through the raw pipeline alone (see code gaps in bridge plan §Task 1).
        # The schedule: prefix path is already verified by the unit test in
        # test_advisory_to_execution_bridge.py::TestLocationScheduleFlowsThroughScheduleExpander.
        "features": {
            "time_schedules": [
                {
                    "name": "BusinessHours",
                    "members": {
                        "member": [
                            {"timePeriodName": _ref("Weekday-9to5")},
                        ],
                    },
                },
            ],
            "time_periods": [
                {
                    "name": "Weekday-9to5",
                    "startTime": "09:00",
                    "endTime": "17:00",
                    "startDate": None,
                    "endDate": None,
                    "monthOfYear": None,
                    "dayOfMonth": None,
                    "dayOfWeek": "Monday",
                },
            ],
            "hunt_pilots": [],
            "hunt_lists": [],
            "line_groups": [],
            "cti_route_points": [],
            "call_parks": [],
            "pickup_groups": [],
            "executive_assistant_pairs": [],
            "executive_settings": [],
        },
    }


class TestBridgeTypesEndToEnd:
    """Full pipeline integration for all 5 bridge canonical types.

    Runs normalize → map → analyze → auto-resolve → expand_to_operations
    on a synthetic raw_data fixture that contains every bridge type.
    Asserts each type produces the expected ops (or 0 for data-only).
    """

    @pytest.fixture(autouse=True)
    def setup_pipeline(self):
        """Run the full pipeline once, share ops across all tests."""
        self.store = MigrationStore(":memory:")
        raw = _bridge_raw_data()
        normalize_discovery(raw, self.store)
        TransformEngine().run(self.store)
        AnalysisPipeline().run(self.store)
        _auto_resolve_decisions(self.store)
        self.ops = expand_to_operations(self.store)
        self.op_pairs = {(op.resource_type, op.op_type) for op in self.ops}
        self.type_counts = {}
        for op in self.ops:
            key = (op.resource_type, op.op_type)
            self.type_counts[key] = self.type_counts.get(key, 0) + 1

    # --- MOH ---

    def test_music_on_hold_produces_configure_ops(self):
        """2 MOH sources (default + custom) → 2 music_on_hold:configure ops."""
        count = self.type_counts.get(("music_on_hold", "configure"), 0)
        assert count == 2, f"Expected 2 music_on_hold:configure ops, got {count}"

    def test_music_on_hold_canonical_objects_in_store(self):
        objs = self.store.get_objects("music_on_hold")
        assert len(objs) == 2

    # --- Announcements ---

    def test_announcement_produces_upload_ops(self):
        """1 announcement → 1 announcement:upload op."""
        count = self.type_counts.get(("announcement", "upload"), 0)
        assert count == 1, f"Expected 1 announcement:upload op, got {count}"

    def test_announcement_has_audio_asset_decision(self):
        """AnnouncementMapper always creates AUDIO_ASSET_MANUAL decisions."""
        decisions = self.store.get_all_decisions()
        # Store returns "type" not "decision_type" (matches decisions table column name)
        audio_decisions = [
            d for d in decisions
            if d.get("type") == "AUDIO_ASSET_MANUAL"
            and "Welcome Greeting" in str(d.get("context", {}).get("announcement_name", ""))
        ]
        assert len(audio_decisions) >= 1

    # --- E911 ---

    def test_e911_config_produces_zero_ops(self):
        """e911_config is data-only — never produces execution ops."""
        resource_types = {op.resource_type for op in self.ops}
        assert "e911_config" not in resource_types

    def test_e911_config_canonical_objects_in_store(self):
        """But the CanonicalE911Config objects exist for the report."""
        objs = self.store.get_objects("e911_config")
        assert len(objs) >= 1

    def test_e911_architecture_advisory_decision(self):
        """E911Mapper creates an ARCHITECTURE_ADVISORY decision."""
        decisions = self.store.get_all_decisions()
        # Store returns "type" not "decision_type" (matches decisions table column name)
        e911_advisories = [
            d for d in decisions
            if d.get("type") == "ARCHITECTURE_ADVISORY"
            and "e911" in str(d.get("context", {}).get("advisory_type", "")).lower()
        ]
        assert len(e911_advisories) >= 1

    # --- Device Profile ---

    def test_device_profile_produces_hoteling_ops(self):
        """UDP-jsmith resolves to user:jsmith → hoteling guest op."""
        dp_ops = [op for op in self.ops if op.resource_type == "device_profile"]
        assert len(dp_ops) >= 1, "Expected at least 1 device_profile op"
        dp_op_types = {op.op_type for op in dp_ops}
        assert dp_op_types.issubset({"enable_hoteling_guest", "enable_hoteling_host"})

    # --- Time Schedule → Operating Mode ---

    def test_operating_mode_produced_from_time_schedule(self):
        """Time schedule + period → operating_mode:create op."""
        count = self.type_counts.get(("operating_mode", "create"), 0)
        assert count >= 1, f"Expected at least 1 operating_mode:create op, got {count}"

    # --- Pipeline stability ---

    def test_pipeline_produces_nonzero_ops(self):
        """Sanity: pipeline produces at least some ops."""
        assert len(self.ops) > 0

    def test_no_bridge_type_planner_warnings(self, caplog):
        """Re-run expand_to_operations and confirm no 'No expansion pattern'
        warnings for any of the 5 bridge types."""
        import logging
        with caplog.at_level(logging.WARNING, logger="wxcli.migration.execute.planner"):
            expand_to_operations(self.store)
        bridge_warnings = [
            r.getMessage() for r in caplog.records
            if "No expansion pattern" in r.getMessage()
            and any(t in r.getMessage() for t in [
                "music_on_hold", "announcement", "e911_config",
                "device_profile", "schedule",
            ])
        ]
        assert bridge_warnings == [], f"Planner warnings for bridge types: {bridge_warnings}"
