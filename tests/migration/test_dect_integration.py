"""DECT Phase 2 integration test scenarios.

Verifies the full DECT pipeline from discovery data through execution planning:
  normalize_discovery → TransformEngine (DECTMapper) → AnalysisPipeline → expand_to_operations

Five scenarios (from docs/superpowers/specs/2026-04-10-dect-migration.md §10c):
  1. Pure desk phone environment — regression: no DECT output produced
  2. Mixed DECT + desk phone — DECT and desk phones coexist
  3. Large DECT deployment (zone ambiguity) — DECT_NETWORK_DESIGN decisions generated
  4. Unowned DECT handsets — DECT_HANDSET_ASSIGNMENT decisions generated
  5. DECT with supplemental base station inventory — full provisioning path (3 ops/network)
"""

import pytest
import networkx as nx

from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.pipeline import normalize_discovery
from wxcli.migration.transform.engine import TransformEngine
from wxcli.migration.transform.analysis_pipeline import AnalysisPipeline
from wxcli.migration.execute.planner import expand_to_operations
from wxcli.migration.execute.dependency import build_dependency_graph
from wxcli.migration.execute.batch import partition_into_batches


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _ref(name: str, uuid: str) -> dict:
    return {"_value_1": name, "uuid": uuid}


def _empty_ref() -> dict:
    return {"_value_1": None, "uuid": None}


def _auto_resolve_decisions(store: MigrationStore) -> None:
    """Pick the first option for every unresolved decision."""
    for d in store.get_all_decisions():
        if d.get("chosen_option") is None and d.get("options"):
            opt = d["options"][0]
            store.resolve_decision(
                d["decision_id"],
                opt["id"] if isinstance(opt, dict) else opt,
            )


def _run_through_analysis(store: MigrationStore, raw_data: dict, **norm_kwargs) -> None:
    """normalize → map → analyze → auto-resolve."""
    normalize_discovery(raw_data, store, **norm_kwargs)
    TransformEngine().run(store)
    AnalysisPipeline().run(store)
    _auto_resolve_decisions(store)


# ---------------------------------------------------------------------------
# Base CUCM data builders
# ---------------------------------------------------------------------------

def _base_raw_data(**device_overrides) -> dict:
    """Minimal CUCM raw_data with 1 device pool and optional device list override."""
    return {
        "locations": {
            "device_pools": [
                {
                    "pkid": "{DP-HQ-0001}",
                    "name": "DP-HQ",
                    "dateTimeSettingName": _ref("DT-Eastern", "{DT-EAST-0001}"),
                    "locationName": _ref("LOC-HQ", "{LOC-HQ-0001}"),
                    "callManagerGroupName": _ref("Default", "{CMG-0001}"),
                    "srstName": None,
                    "regionName": _ref("Default", "{RGN-0001}"),
                    "mediaResourceListName": None,
                },
            ],
            "datetime_groups": [
                {
                    "pkid": "{DT-EAST-0001}",
                    "name": "DT-Eastern",
                    "timeZone": "America/New_York",
                },
            ],
            "cucm_locations": [
                {
                    "pkid": "{LOC-HQ-0001}",
                    "name": "LOC-HQ",
                },
            ],
        },
        "users": {
            "users": device_overrides.get("users", []),
        },
        "devices": {
            "phones": device_overrides.get("phones", []),
        },
        "routing": {
            "partitions": [
                {
                    "pkid": "{PT-INT-0001}",
                    "name": "PT-Internal",
                    "description": "Internal",
                },
            ],
            "css_list": [],
            "route_patterns": [],
            "gateways": [],
            "sip_trunks": [],
            "route_groups": [],
            "route_lists": [],
            "translation_patterns": [],
        },
        "features": {
            "hunt_pilots": [],
            "hunt_lists": [],
            "line_groups": [],
            "cti_route_points": [],
            "call_parks": [],
            "pickup_groups": [],
            "time_schedules": [],
            "time_periods": [],
        },
        "voicemail": {
            "voicemail_profiles": [],
            "voicemail_pilots": [],
        },
        "templates": {
            "button_templates": [],
            "softkey_templates": [],
        },
        "remote_destinations": {
            "remote_destinations": [],
        },
        "e911": {
            "elin_groups": [],
            "geo_locations": [],
        },
        "device_profiles": {
            "device_profiles": [],
        },
        "moh": {
            "moh_sources": [],
        },
        "announcements": {
            "announcements": [],
        },
        "informational": {
            "region": [],
            "srst": [],
            "media_resource_group": [],
            "media_resource_list": [],
            "aar_group": [],
            "device_mobility_group": [],
            "conference_bridge": [],
            "softkey_template": [],
            "ip_phone_service": [],
            "intercom": [],
            "common_phone_config": [],
            "phone_button_template": [],
            "feature_control_policy": [],
            "credential_policy": [],
            "recording_profile": [],
            "ldap_directory": [],
            "app_user": [],
            "h323_gateway": [],
            "enterprise_params": [],
            "service_params": [],
        },
        "tier4": {
            "recording_profiles": [],
            "calling_party_transformations": [],
            "called_party_transformations": [],
            "device_profiles": [],
            "remote_destination_profiles": [],
        },
    }


def _desk_phone(name: str, model: str, owner: str, pool: str, pool_uuid: str,
                ext: str, pt: str, pt_uuid: str, pkid: str) -> dict:
    """Build a minimal desk phone AXL dict."""
    return {
        "pkid": pkid,
        "name": name,
        "model": model,
        "product": model,
        "class": "Phone",
        "description": f"{owner} - Desk Phone",
        "protocol": "SIP",
        "ownerUserName": owner,
        "devicePoolName": _ref(pool, pool_uuid),
        "callingSearchSpaceName": _empty_ref(),
        "phoneTemplateName": _empty_ref(),
        "softkeyTemplateName": None,
        "deviceMobilityMode": "Default",
        "lines": {
            "line": [
                {
                    "index": "1",
                    "label": f"{owner} - {ext}",
                    "display": owner,
                    "e164Mask": None,
                    "associatedEndusers": {"enduser": [{"userId": owner}]},
                    "dirn": {
                        "pattern": ext,
                        "routePartitionName": _ref(pt, pt_uuid),
                        "alertingName": owner,
                        "description": f"{owner} Ext {ext}",
                        "shareLineAppearanceCssName": _empty_ref(),
                        "callingSearchSpaceName": _empty_ref(),
                    },
                },
            ],
        },
        "speeddials": [],
        "busyLampFields": [],
    }


def _dect_handset(name: str, owner: str | None, pool: str, pool_uuid: str,
                  ext: str, pt: str, pt_uuid: str, pkid: str) -> dict:
    """Build a DECT handset (Cisco 6825) AXL dict."""
    return {
        "pkid": pkid,
        "name": name,
        "model": "Cisco 6825",
        "product": "Cisco 6825",
        "class": "Phone",
        "description": f"{owner or 'Unowned'} - DECT Handset",
        "protocol": "SIP",
        "ownerUserName": owner,
        "devicePoolName": _ref(pool, pool_uuid),
        "callingSearchSpaceName": _empty_ref(),
        "phoneTemplateName": _empty_ref(),
        "softkeyTemplateName": None,
        "deviceMobilityMode": "Default",
        "lines": {
            "line": [
                {
                    "index": "1",
                    "label": f"{owner or 'Unowned'} - {ext}",
                    "display": owner or "Unowned",
                    "e164Mask": None,
                    "associatedEndusers": (
                        {"enduser": [{"userId": owner}]} if owner else None
                    ),
                    "dirn": {
                        "pattern": ext,
                        "routePartitionName": _ref(pt, pt_uuid),
                        "alertingName": owner or "Unowned",
                        "description": f"Ext {ext}",
                        "shareLineAppearanceCssName": _empty_ref(),
                        "callingSearchSpaceName": _empty_ref(),
                    },
                },
            ],
        },
        "speeddials": [],
        "busyLampFields": [],
    }


def _user(userid: str, first: str, last: str, ext: str, pt: str, pt_uuid: str,
          device_name: str, pkid: str) -> dict:
    """Build a minimal CUCM user AXL dict."""
    return {
        "pkid": pkid,
        "userid": userid,
        "firstName": first,
        "lastName": last,
        "mailid": f"{userid}@acme.com",
        "telephoneNumber": None,
        "department": "Staff",
        "title": "Staff",
        "manager": _empty_ref(),
        "directoryUri": f"{userid}@acme.com",
        "userLocale": "English United States",
        "selfService": None,
        "enableCti": "false",
        "associatedDevices": {"device": [device_name]} if device_name else None,
        "primaryExtension": {
            "pattern": ext,
            "routePartitionName": _ref(pt, pt_uuid),
        },
        "callingSearchSpaceName": _empty_ref(),
        "voiceMailProfile": _empty_ref(),
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def store(tmp_path):
    s = MigrationStore(tmp_path / "dect_integration.db")
    yield s
    s.close()


# ===========================================================================
# Scenario 1 — Pure desk phone environment (regression)
# ===========================================================================

class TestScenario1PureDeskPhones:
    """No DECT devices present — pipeline must not generate any DECT output."""

    @pytest.fixture
    def raw_data(self):
        users = [
            _user("alice", "Alice", "Smith", "1001", "PT-Internal", "{PT-INT-0001}",
                  "SEP001122334455", "{USR-ALICE-0001}"),
            _user("bob", "Bob", "Jones", "1002", "PT-Internal", "{PT-INT-0001}",
                  "SEP001122334466", "{USR-BOB-0001}"),
        ]
        phones = [
            _desk_phone("SEP001122334455", "Cisco 6861", "alice", "DP-HQ", "{DP-HQ-0001}",
                        "1001", "PT-Internal", "{PT-INT-0001}", "{PH-ALICE-0001}"),
            _desk_phone("SEP001122334466", "Cisco 6861", "bob", "DP-HQ", "{DP-HQ-0001}",
                        "1002", "PT-Internal", "{PT-INT-0001}", "{PH-BOB-0001}"),
        ]
        return _base_raw_data(users=users, phones=phones)

    def test_no_dect_networks_created(self, store, raw_data):
        """Normalization produces zero dect_network objects."""
        normalize_discovery(raw_data, store)
        assert store.count_by_type("dect_network") == 0

    def test_no_dect_decisions_generated(self, store, raw_data):
        """Mapping and analysis produce no DECT-related decisions."""
        normalize_discovery(raw_data, store)
        TransformEngine().run(store)
        AnalysisPipeline().run(store)

        decisions = store.get_all_decisions()
        dect_types = {d["type"] for d in decisions if d["type"].startswith("DECT_")}
        assert len(dect_types) == 0, f"Unexpected DECT decisions: {dect_types}"

    def test_desk_phones_processed_normally(self, store, raw_data):
        """Desk phones produce canonical device objects at the correct tier."""
        normalize_discovery(raw_data, store)
        TransformEngine().run(store)

        devices = store.get_objects("device")
        assert len(devices) >= 2
        # 8845 is NATIVE_MPP
        tiers = {d.get("compatibility_tier") for d in devices}
        assert "native_mpp" in tiers

    def test_no_dect_ops_in_plan(self, store, raw_data):
        """Execution plan contains no dect_network operations."""
        _run_through_analysis(store, raw_data)
        ops = expand_to_operations(store)

        dect_ops = [op for op in ops if op.resource_type == "dect_network"]
        assert len(dect_ops) == 0, f"Unexpected DECT ops: {dect_ops}"

    def test_pipeline_is_acyclic(self, store, raw_data):
        """Dependency graph is a valid DAG (regression check)."""
        _run_through_analysis(store, raw_data)
        ops = expand_to_operations(store)
        G = build_dependency_graph(ops, store)
        assert nx.is_directed_acyclic_graph(G)


# ===========================================================================
# Scenario 2 — Mixed DECT + desk phone environment
# ===========================================================================

class TestScenario2MixedDectAndDeskPhones:
    """80% desk phones, 20% DECT handsets in the same device pool.

    Expected:
    - DECT handsets grouped into 1 dect_network object
    - Desk phones processed normally (native_mpp tier)
    - 3 DECT ops in plan + desk phone ops both present
    - Dependency graph is acyclic
    """

    @pytest.fixture
    def raw_data(self):
        users = [
            _user("alice", "Alice", "Smith", "1001", "PT-Internal", "{PT-INT-0001}",
                  "SEP001122334455", "{USR-ALICE-0001}"),
            _user("bob", "Bob", "Jones", "1002", "PT-Internal", "{PT-INT-0001}",
                  "SEP001122334466", "{USR-BOB-0001}"),
            _user("carol", "Carol", "White", "1003", "PT-Internal", "{PT-INT-0001}",
                  "SEP001122334477", "{USR-CAROL-0001}"),
            _user("dave", "Dave", "Black", "1004", "PT-Internal", "{PT-INT-0001}",
                  "SEP001122334488", "{USR-DAVE-0001}"),
            _user("eve", "Eve", "Green", "2001", "PT-Internal", "{PT-INT-0001}",
                  "DECT001122334401", "{USR-EVE-0001}"),
        ]
        phones = [
            # 4 desk phones (Cisco 6861 — NATIVE_MPP)
            _desk_phone("SEP001122334455", "Cisco 6861", "alice", "DP-HQ", "{DP-HQ-0001}",
                        "1001", "PT-Internal", "{PT-INT-0001}", "{PH-ALICE-0001}"),
            _desk_phone("SEP001122334466", "Cisco 6861", "bob", "DP-HQ", "{DP-HQ-0001}",
                        "1002", "PT-Internal", "{PT-INT-0001}", "{PH-BOB-0001}"),
            _desk_phone("SEP001122334477", "Cisco 6861", "carol", "DP-HQ", "{DP-HQ-0001}",
                        "1003", "PT-Internal", "{PT-INT-0001}", "{PH-CAROL-0001}"),
            _desk_phone("SEP001122334488", "Cisco 6861", "dave", "DP-HQ", "{DP-HQ-0001}",
                        "1004", "PT-Internal", "{PT-INT-0001}", "{PH-DAVE-0001}"),
            # 1 DECT handset (20% of 5)
            _dect_handset("DECT001122334401", "eve", "DP-HQ", "{DP-HQ-0001}",
                          "2001", "PT-Internal", "{PT-INT-0001}", "{PH-EVE-DECT-0001}"),
        ]
        return _base_raw_data(users=users, phones=phones)

    def test_dect_network_created(self, store, raw_data):
        """One DECT network is created (all DECT handsets in same pool)."""
        normalize_discovery(raw_data, store)
        assert store.count_by_type("dect_network") == 1

    def test_desk_phones_also_created(self, store, raw_data):
        """Desk phones produce canonical device objects alongside the DECT network."""
        normalize_discovery(raw_data, store)
        # 5 total devices (4 desk + 1 DECT handset)
        assert store.count_by_type("device") == 5

    def test_dect_and_desk_phones_separate_tiers(self, store, raw_data):
        """DECT handset is classified as 'dect' tier; desk phones as 'native_mpp'."""
        normalize_discovery(raw_data, store)
        TransformEngine().run(store)

        devices = store.get_objects("device")
        tiers = [d.get("compatibility_tier") for d in devices]
        assert "dect" in tiers
        assert "native_mpp" in tiers

    def test_plan_has_dect_and_desk_phone_ops(self, store, raw_data):
        """Execution plan includes both DECT ops and desk phone ops."""
        _run_through_analysis(store, raw_data)
        ops = expand_to_operations(store)

        op_types = {(op.resource_type, op.op_type) for op in ops}
        # DECT network produces 3 ops
        assert ("dect_network", "create") in op_types
        assert ("dect_network", "create_base_stations") in op_types
        assert ("dect_network", "assign_handsets") in op_types
        # Desk phones produce device:create ops (native_mpp tier)
        resource_types = {op.resource_type for op in ops}
        assert "location" in resource_types
        assert "user" in resource_types

    def test_exactly_3_dect_ops(self, store, raw_data):
        """Each DECT network expands to exactly 3 ops."""
        _run_through_analysis(store, raw_data)
        ops = expand_to_operations(store)

        dect_ops = [op for op in ops if op.resource_type == "dect_network"]
        # 1 network × 3 ops = 3
        assert len(dect_ops) == 3

    def test_dependency_graph_is_acyclic(self, store, raw_data):
        """Dependency graph is a valid DAG with mixed DECT and desk phone ops."""
        _run_through_analysis(store, raw_data)
        ops = expand_to_operations(store)
        G = build_dependency_graph(ops, store)
        assert nx.is_directed_acyclic_graph(G)

    def test_batches_produced(self, store, raw_data):
        """Batch partitioning produces at least one batch including DECT ops."""
        _run_through_analysis(store, raw_data)
        ops = expand_to_operations(store)
        G = build_dependency_graph(ops, store)
        batches = partition_into_batches(G)
        assert len(batches) > 0


# ===========================================================================
# Scenario 3 — Large DECT deployment (zone ambiguity)
# ===========================================================================

class TestScenario3LargeDectMultiZone:
    """DECT handsets spread across two device pools that map to the SAME location.

    Expected:
    - 2 dect_network objects (one per pool)
    - DECT_NETWORK_DESIGN decisions generated (no-inventory + multi-zone)
    - Auto model selection: DBS-110 for ≤30 handsets, DBS-210 for >30
    - Dependency graph remains acyclic
    """

    @pytest.fixture
    def raw_data_two_pools(self, tmp_path):
        """Two device pools both mapping to LOC-HQ, each with DECT handsets."""
        return {
            "locations": {
                "device_pools": [
                    {
                        "pkid": "{DP-HQ-ZONE1-0001}",
                        "name": "DP-HQ-Zone1",
                        "dateTimeSettingName": _ref("DT-Eastern", "{DT-EAST-0001}"),
                        "locationName": _ref("LOC-HQ", "{LOC-HQ-0001}"),
                        "callManagerGroupName": _ref("Default", "{CMG-0001}"),
                        "srstName": None,
                        "regionName": _ref("Default", "{RGN-0001}"),
                        "mediaResourceListName": None,
                    },
                    {
                        "pkid": "{DP-HQ-ZONE2-0002}",
                        "name": "DP-HQ-Zone2",
                        "dateTimeSettingName": _ref("DT-Eastern", "{DT-EAST-0001}"),
                        "locationName": _ref("LOC-HQ", "{LOC-HQ-0001}"),
                        "callManagerGroupName": _ref("Default", "{CMG-0001}"),
                        "srstName": None,
                        "regionName": _ref("Default", "{RGN-0001}"),
                        "mediaResourceListName": None,
                    },
                ],
                "datetime_groups": [
                    {
                        "pkid": "{DT-EAST-0001}",
                        "name": "DT-Eastern",
                        "timeZone": "America/New_York",
                    },
                ],
                "cucm_locations": [
                    {
                        "pkid": "{LOC-HQ-0001}",
                        "name": "LOC-HQ",
                    },
                ],
            },
            "users": {
                "users": [
                    _user("user1", "User", "One", "3001", "PT-Internal", "{PT-INT-0001}",
                          "DECT000000000001", "{USR-U1-0001}"),
                ],
            },
            "devices": {
                "phones": [
                    # Zone 1: 5 handsets (should auto-select DBS-110)
                    _dect_handset("DECT000000000001", "user1", "DP-HQ-Zone1",
                                  "{DP-HQ-ZONE1-0001}", "3001", "PT-Internal",
                                  "{PT-INT-0001}", "{PH-D01}"),
                    _dect_handset("DECT000000000002", None, "DP-HQ-Zone1",
                                  "{DP-HQ-ZONE1-0001}", "3002", "PT-Internal",
                                  "{PT-INT-0001}", "{PH-D02}"),
                    _dect_handset("DECT000000000003", None, "DP-HQ-Zone1",
                                  "{DP-HQ-ZONE1-0001}", "3003", "PT-Internal",
                                  "{PT-INT-0001}", "{PH-D03}"),
                    _dect_handset("DECT000000000004", None, "DP-HQ-Zone1",
                                  "{DP-HQ-ZONE1-0001}", "3004", "PT-Internal",
                                  "{PT-INT-0001}", "{PH-D04}"),
                    _dect_handset("DECT000000000005", None, "DP-HQ-Zone1",
                                  "{DP-HQ-ZONE1-0001}", "3005", "PT-Internal",
                                  "{PT-INT-0001}", "{PH-D05}"),
                    # Zone 2: 3 handsets (DBS-110 as well)
                    _dect_handset("DECT000000000011", None, "DP-HQ-Zone2",
                                  "{DP-HQ-ZONE2-0002}", "3011", "PT-Internal",
                                  "{PT-INT-0001}", "{PH-D11}"),
                    _dect_handset("DECT000000000012", None, "DP-HQ-Zone2",
                                  "{DP-HQ-ZONE2-0002}", "3012", "PT-Internal",
                                  "{PT-INT-0001}", "{PH-D12}"),
                    _dect_handset("DECT000000000013", None, "DP-HQ-Zone2",
                                  "{DP-HQ-ZONE2-0002}", "3013", "PT-Internal",
                                  "{PT-INT-0001}", "{PH-D13}"),
                ],
            },
            "routing": {
                "partitions": [
                    {"pkid": "{PT-INT-0001}", "name": "PT-Internal",
                     "description": "Internal"},
                ],
                "css_list": [], "route_patterns": [], "gateways": [],
                "sip_trunks": [], "route_groups": [], "route_lists": [],
                "translation_patterns": [],
            },
            "features": {
                "hunt_pilots": [], "hunt_lists": [], "line_groups": [],
                "cti_route_points": [], "call_parks": [], "pickup_groups": [],
                "time_schedules": [], "time_periods": [],
            },
            "voicemail": {"voicemail_profiles": [], "voicemail_pilots": []},
            "templates": {"button_templates": [], "softkey_templates": []},
            "remote_destinations": {"remote_destinations": []},
            "e911": {"elin_groups": [], "geo_locations": []},
            "device_profiles": {"device_profiles": []},
            "moh": {"moh_sources": []},
            "announcements": {"announcements": []},
            "informational": {
                "region": [], "srst": [], "media_resource_group": [],
                "media_resource_list": [], "aar_group": [], "device_mobility_group": [],
                "conference_bridge": [], "softkey_template": [], "ip_phone_service": [],
                "intercom": [], "common_phone_config": [], "phone_button_template": [],
                "feature_control_policy": [], "credential_policy": [],
                "recording_profile": [], "ldap_directory": [], "app_user": [],
                "h323_gateway": [], "enterprise_params": [], "service_params": [],
            },
            "tier4": {
                "recording_profiles": [], "calling_party_transformations": [],
                "called_party_transformations": [], "device_profiles": [],
                "remote_destination_profiles": [],
            },
        }

    @pytest.fixture
    def store_two_pools(self, tmp_path):
        s = MigrationStore(tmp_path / "dect_two_pools.db")
        yield s
        s.close()

    def test_two_dect_networks_created(self, store_two_pools, raw_data_two_pools):
        """Two device pools produce two separate dect_network objects."""
        normalize_discovery(raw_data_two_pools, store_two_pools)
        assert store_two_pools.count_by_type("dect_network") == 2

    def test_dect_network_design_decisions_generated(self, store_two_pools, raw_data_two_pools):
        """DECT_NETWORK_DESIGN decisions are generated (no inventory + multi-zone)."""
        normalize_discovery(raw_data_two_pools, store_two_pools)
        TransformEngine().run(store_two_pools)
        AnalysisPipeline().run(store_two_pools)

        decisions = store_two_pools.get_all_decisions()
        design_decisions = [d for d in decisions if d["type"] == "DECT_NETWORK_DESIGN"]
        assert len(design_decisions) >= 1, (
            f"Expected DECT_NETWORK_DESIGN decisions, got: {[d['type'] for d in decisions]}"
        )

    def test_no_inventory_decision_generated(self, store_two_pools, raw_data_two_pools):
        """DECT_NETWORK_DESIGN with 'no base station inventory' context is generated."""
        normalize_discovery(raw_data_two_pools, store_two_pools)
        TransformEngine().run(store_two_pools)
        AnalysisPipeline().run(store_two_pools)

        decisions = store_two_pools.get_all_decisions()
        design_decisions = [d for d in decisions if d["type"] == "DECT_NETWORK_DESIGN"]
        inventory_decisions = [
            d for d in design_decisions
            if not (d.get("context") or {}).get("base_stations_provided")
        ]
        assert len(inventory_decisions) >= 1, (
            "Expected at least one DECT_NETWORK_DESIGN flagging missing inventory"
        )

    def test_multi_zone_ambiguity_decision_generated(self, store_two_pools, raw_data_two_pools):
        """DECT_NETWORK_DESIGN with zone_count > 1 is generated for multi-zone ambiguity."""
        normalize_discovery(raw_data_two_pools, store_two_pools)
        TransformEngine().run(store_two_pools)

        decisions = store_two_pools.get_all_decisions()
        multi_zone = [
            d for d in decisions
            if d["type"] == "DECT_NETWORK_DESIGN"
            and (d.get("context") or {}).get("zone_count", 1) > 1
        ]
        assert len(multi_zone) >= 1, (
            "Expected DECT_NETWORK_DESIGN with zone_count > 1 for multi-zone ambiguity"
        )

    def test_auto_model_selection_dbs110_small_zone(self, store_two_pools, raw_data_two_pools):
        """Small zones (≤30 handsets) auto-select DBS-110."""
        normalize_discovery(raw_data_two_pools, store_two_pools)
        TransformEngine().run(store_two_pools)

        networks = store_two_pools.get_objects("dect_network")
        # Both zones have < 30 handsets → both should be DBS-110
        models = {n.get("model") for n in networks if n.get("model") and n["model"] != "PENDING"}
        assert "DBS-110" in models, f"Expected DBS-110 for small zones, got: {models}"

    def test_dependency_graph_is_acyclic(self, store_two_pools, raw_data_two_pools):
        """Multi-zone DECT dependency graph is a valid DAG."""
        normalize_discovery(raw_data_two_pools, store_two_pools)
        TransformEngine().run(store_two_pools)
        AnalysisPipeline().run(store_two_pools)
        _auto_resolve_decisions(store_two_pools)

        ops = expand_to_operations(store_two_pools)
        G = build_dependency_graph(ops, store_two_pools)
        assert nx.is_directed_acyclic_graph(G)

    def test_plan_has_6_dect_ops(self, store_two_pools, raw_data_two_pools):
        """Two DECT networks each expand to 3 ops = 6 total DECT ops."""
        normalize_discovery(raw_data_two_pools, store_two_pools)
        TransformEngine().run(store_two_pools)
        AnalysisPipeline().run(store_two_pools)
        _auto_resolve_decisions(store_two_pools)

        ops = expand_to_operations(store_two_pools)
        dect_ops = [op for op in ops if op.resource_type == "dect_network"]
        assert len(dect_ops) == 6, f"Expected 6 DECT ops (2 nets × 3), got {len(dect_ops)}"


# ===========================================================================
# Scenario 4 — Unowned DECT handsets
# ===========================================================================

class TestScenario4UnownedDectHandsets:
    """DECT handsets with no CUCM user association.

    Expected:
    - DECT_HANDSET_ASSIGNMENT decisions generated for each unowned handset
    - Handsets can be auto-assigned to workspaces (first option is ACCEPT)
    - Owned handsets do NOT get DECT_HANDSET_ASSIGNMENT decisions
    """

    @pytest.fixture
    def raw_data(self):
        users = [
            _user("alice", "Alice", "Smith", "1001", "PT-Internal", "{PT-INT-0001}",
                  "DECT001122334401", "{USR-ALICE-0001}"),
        ]
        phones = [
            # 1 owned handset (alice)
            _dect_handset("DECT001122334401", "alice", "DP-HQ", "{DP-HQ-0001}",
                          "1001", "PT-Internal", "{PT-INT-0001}", "{PH-ALICE-DECT}"),
            # 3 unowned handsets (no ownerUserName)
            _dect_handset("DECT001122334402", None, "DP-HQ", "{DP-HQ-0001}",
                          "1002", "PT-Internal", "{PT-INT-0001}", "{PH-UNO-1}"),
            _dect_handset("DECT001122334403", None, "DP-HQ", "{DP-HQ-0001}",
                          "1003", "PT-Internal", "{PT-INT-0001}", "{PH-UNO-2}"),
            _dect_handset("DECT001122334404", None, "DP-HQ", "{DP-HQ-0001}",
                          "1004", "PT-Internal", "{PT-INT-0001}", "{PH-UNO-3}"),
        ]
        return _base_raw_data(users=users, phones=phones)

    def test_handset_assignment_decisions_generated(self, store, raw_data):
        """3 unowned handsets generate 3 DECT_HANDSET_ASSIGNMENT decisions."""
        normalize_discovery(raw_data, store)
        TransformEngine().run(store)

        decisions = store.get_all_decisions()
        assign_decisions = [d for d in decisions if d["type"] == "DECT_HANDSET_ASSIGNMENT"]
        assert len(assign_decisions) == 3, (
            f"Expected 3 DECT_HANDSET_ASSIGNMENT decisions (one per unowned handset), "
            f"got {len(assign_decisions)}"
        )

    def test_owned_handset_no_assignment_decision(self, store, raw_data):
        """Owned handset (alice) does not get a DECT_HANDSET_ASSIGNMENT decision."""
        normalize_discovery(raw_data, store)
        TransformEngine().run(store)

        decisions = store.get_all_decisions()
        assign_decisions = [d for d in decisions if d["type"] == "DECT_HANDSET_ASSIGNMENT"]

        # None of the assignment decisions should reference alice's device
        for d in assign_decisions:
            ctx = d.get("context") or {}
            assert "DECT001122334401" not in str(ctx), (
                f"alice's owned handset should NOT have DECT_HANDSET_ASSIGNMENT: {ctx}"
            )

    def test_assignment_decisions_have_workspace_option(self, store, raw_data):
        """DECT_HANDSET_ASSIGNMENT decisions include an ACCEPT option for workspace creation."""
        normalize_discovery(raw_data, store)
        TransformEngine().run(store)

        decisions = store.get_all_decisions()
        assign_decisions = [d for d in decisions if d["type"] == "DECT_HANDSET_ASSIGNMENT"]

        for d in assign_decisions:
            options = d.get("options") or []
            # DecisionOption uses 'id' field (not 'type'): "accept", "manual", "skip"
            option_ids = [opt.get("id") if isinstance(opt, dict) else opt for opt in options]
            assert "accept" in option_ids, (
                f"DECT_HANDSET_ASSIGNMENT should have an ACCEPT option for workspace creation, "
                f"got: {option_ids}"
            )

    def test_unowned_handset_context_has_expected_fields(self, store, raw_data):
        """DECT_HANDSET_ASSIGNMENT decisions carry expected context fields."""
        normalize_discovery(raw_data, store)
        TransformEngine().run(store)

        decisions = store.get_all_decisions()
        assign_decisions = [d for d in decisions if d["type"] == "DECT_HANDSET_ASSIGNMENT"]

        for d in assign_decisions:
            ctx = d.get("context") or {}
            assert "device_canonical_id" in ctx
            assert "cucm_device_name" in ctx
            assert ctx.get("owner_status") == "unowned"

    def test_pipeline_produces_plan_despite_unresolved_decisions(self, store, raw_data):
        """Pipeline completes planning after auto-resolving assignment decisions."""
        normalize_discovery(raw_data, store)
        TransformEngine().run(store)
        AnalysisPipeline().run(store)
        _auto_resolve_decisions(store)

        ops = expand_to_operations(store)
        dect_ops = [op for op in ops if op.resource_type == "dect_network"]
        # 1 network → 3 ops
        assert len(dect_ops) == 3


# ===========================================================================
# Scenario 5 — DECT with supplemental base station inventory (CSV)
# ===========================================================================

class TestScenario5DectWithInventory:
    """DECT handsets + CSV base station inventory.

    Expected:
    - Base stations attached to the network (base_stations non-empty)
    - Model resolved from CSV (DBS-110 or DBS-210 from inventory)
    - Full provisioning operations created: 3 ops per network
    - create_dect_network → create_base_stations → assign_handsets dependency chain
    - No MISSING_INVENTORY DECT_NETWORK_DESIGN decision (inventory is provided)
    """

    @pytest.fixture
    def dect_inventory(self):
        """Simulated --dect-inventory CSV: 2 base stations for DP-HQ zone."""
        return [
            {
                "coverage_zone": "DP-HQ",
                "base_station_mac": "AA:BB:CC:DD:EE:01",
                "base_station_model": "DBS-110",
            },
            {
                "coverage_zone": "DP-HQ",
                "base_station_mac": "AA:BB:CC:DD:EE:02",
                "base_station_model": "DBS-110",
            },
        ]

    @pytest.fixture
    def raw_data(self):
        users = [
            _user("alice", "Alice", "Smith", "2001", "PT-Internal", "{PT-INT-0001}",
                  "DECT001122334401", "{USR-ALICE-0001}"),
            _user("bob", "Bob", "Jones", "2002", "PT-Internal", "{PT-INT-0001}",
                  "DECT001122334402", "{USR-BOB-0001}"),
        ]
        phones = [
            _dect_handset("DECT001122334401", "alice", "DP-HQ", "{DP-HQ-0001}",
                          "2001", "PT-Internal", "{PT-INT-0001}", "{PH-ALICE-DECT}"),
            _dect_handset("DECT001122334402", "bob", "DP-HQ", "{DP-HQ-0001}",
                          "2002", "PT-Internal", "{PT-INT-0001}", "{PH-BOB-DECT}"),
        ]
        return _base_raw_data(users=users, phones=phones)

    def test_base_stations_attached_to_network(self, store, raw_data, dect_inventory):
        """normalize_discovery merges inventory: base_stations list is non-empty."""
        normalize_discovery(raw_data, store, dect_inventory=dect_inventory)

        networks = store.get_objects("dect_network")
        assert len(networks) == 1
        base_stations = networks[0].get("base_stations") or []
        assert len(base_stations) == 2, (
            f"Expected 2 base stations from inventory, got {len(base_stations)}"
        )

    def test_base_station_mac_in_network(self, store, raw_data, dect_inventory):
        """Base station MAC addresses from inventory appear on the network."""
        normalize_discovery(raw_data, store, dect_inventory=dect_inventory)

        networks = store.get_objects("dect_network")
        base_stations = networks[0].get("base_stations") or []
        macs = {bs.get("mac") for bs in base_stations}
        assert "AA:BB:CC:DD:EE:01" in macs
        assert "AA:BB:CC:DD:EE:02" in macs

    def test_model_resolved_from_inventory(self, store, raw_data, dect_inventory):
        """Network model is resolved from inventory (DBS-110), not PENDING."""
        normalize_discovery(raw_data, store, dect_inventory=dect_inventory)
        TransformEngine().run(store)

        networks = store.get_objects("dect_network")
        assert len(networks) == 1
        model = networks[0].get("model")
        # DECTMapper auto-selects based on handset count (2 ≤ 30 → DBS-110)
        assert model == "DBS-110", f"Expected DBS-110 model selection, got: {model}"

    def test_no_missing_inventory_design_decision(self, store, raw_data, dect_inventory):
        """With inventory provided, no DECT_NETWORK_DESIGN for missing base stations."""
        normalize_discovery(raw_data, store, dect_inventory=dect_inventory)
        TransformEngine().run(store)

        decisions = store.get_all_decisions()
        design_decisions = [d for d in decisions if d["type"] == "DECT_NETWORK_DESIGN"]
        missing_inventory = [
            d for d in design_decisions
            if not (d.get("context") or {}).get("base_stations_provided")
        ]
        assert len(missing_inventory) == 0, (
            f"Expected no missing-inventory DECT_NETWORK_DESIGN when inventory provided, "
            f"got {len(missing_inventory)}: {[d.get('summary') for d in missing_inventory]}"
        )

    def test_three_ops_per_network(self, store, raw_data, dect_inventory):
        """Each network with inventory expands to exactly 3 ops."""
        normalize_discovery(raw_data, store, dect_inventory=dect_inventory)
        TransformEngine().run(store)
        AnalysisPipeline().run(store)
        _auto_resolve_decisions(store)

        ops = expand_to_operations(store)
        dect_ops = [op for op in ops if op.resource_type == "dect_network"]
        assert len(dect_ops) == 3, (
            f"Expected 3 DECT ops (create + create_base_stations + assign_handsets), "
            f"got {len(dect_ops)}: {[(op.op_type) for op in dect_ops]}"
        )

    def test_op_types_correct(self, store, raw_data, dect_inventory):
        """The 3 ops are: create, create_base_stations, assign_handsets."""
        normalize_discovery(raw_data, store, dect_inventory=dect_inventory)
        TransformEngine().run(store)
        AnalysisPipeline().run(store)
        _auto_resolve_decisions(store)

        ops = expand_to_operations(store)
        dect_ops = [op for op in ops if op.resource_type == "dect_network"]
        op_type_set = {op.op_type for op in dect_ops}
        assert op_type_set == {"create", "create_base_stations", "assign_handsets"}, (
            f"Unexpected DECT op types: {op_type_set}"
        )

    def test_dependency_chain_create_to_base_stations(self, store, raw_data, dect_inventory):
        """create_base_stations depends on create_dect_network."""
        normalize_discovery(raw_data, store, dect_inventory=dect_inventory)
        TransformEngine().run(store)
        AnalysisPipeline().run(store)
        _auto_resolve_decisions(store)

        ops = expand_to_operations(store)
        G = build_dependency_graph(ops, store)
        assert nx.is_directed_acyclic_graph(G)

        # Node IDs are computed as "{canonical_id}:{op_type}"
        dect_ops = [op for op in ops if op.resource_type == "dect_network"]
        create_op = next(op for op in dect_ops if op.op_type == "create")
        base_op = next(op for op in dect_ops if op.op_type == "create_base_stations")
        create_node = f"{create_op.canonical_id}:{create_op.op_type}"
        base_node = f"{base_op.canonical_id}:{base_op.op_type}"

        # create_base_stations must depend (directly or transitively) on create
        assert nx.has_path(G, create_node, base_node), (
            "create_base_stations should depend on create_dect_network"
        )

    def test_dependency_chain_base_stations_to_assign_handsets(self, store, raw_data, dect_inventory):
        """assign_handsets depends on create_base_stations."""
        normalize_discovery(raw_data, store, dect_inventory=dect_inventory)
        TransformEngine().run(store)
        AnalysisPipeline().run(store)
        _auto_resolve_decisions(store)

        ops = expand_to_operations(store)
        G = build_dependency_graph(ops, store)

        dect_ops = [op for op in ops if op.resource_type == "dect_network"]
        base_op = next(op for op in dect_ops if op.op_type == "create_base_stations")
        assign_op = next(op for op in dect_ops if op.op_type == "assign_handsets")
        base_node = f"{base_op.canonical_id}:{base_op.op_type}"
        assign_node = f"{assign_op.canonical_id}:{assign_op.op_type}"

        assert nx.has_path(G, base_node, assign_node), (
            "assign_handsets should depend on create_base_stations"
        )

    def test_has_inventory_flag_in_pre_migration_state(self, store, raw_data, dect_inventory):
        """Post-mapping network carries has_base_station_inventory=True."""
        normalize_discovery(raw_data, store, dect_inventory=dect_inventory)
        TransformEngine().run(store)

        networks = store.get_objects("dect_network")
        for net in networks:
            pms = net.get("pre_migration_state") or {}
            assert pms.get("has_base_station_inventory") is True, (
                f"Expected has_base_station_inventory=True in pre_migration_state, got: {pms}"
            )

    def test_large_zone_selects_dbs210(self, store, tmp_path, dect_inventory):
        """A zone with >30 handsets triggers DBS-210 auto-selection."""
        # Build a store with 31 handsets
        s = MigrationStore(tmp_path / "dect_large.db")
        users_large = [
            _user(f"u{i}", f"User{i}", "Test", f"30{i:02d}", "PT-Internal",
                  "{PT-INT-0001}", f"DECT0000000{i:05d}", f"{{USR-{i:04d}}}")
            for i in range(1, 4)  # 3 users (rest are unowned)
        ]
        phones_large = [
            _dect_handset(f"DECT0000000{i:05d}",
                          f"u{i}" if i <= 3 else None,
                          "DP-HQ", "{DP-HQ-0001}",
                          f"30{i:02d}", "PT-Internal", "{PT-INT-0001}",
                          f"{{PH-LARGE-{i:04d}}}")
            for i in range(1, 32)  # 31 handsets
        ]
        raw_large = _base_raw_data(users=users_large, phones=phones_large)
        # Inventory for the large zone
        large_inventory = [{
            "coverage_zone": "DP-HQ",
            "base_station_mac": f"BB:BB:BB:BB:{j:02X}:00",
            "base_station_model": "DBS-210",
        } for j in range(1, 5)]

        normalize_discovery(raw_large, s, dect_inventory=large_inventory)
        TransformEngine().run(s)
        s.close()

        # Re-open to verify
        s2 = MigrationStore(tmp_path / "dect_large.db")
        networks = s2.get_objects("dect_network")
        assert len(networks) == 1
        model = networks[0].get("model")
        # DECTMapper: 31 handsets > 30 → DBS-210
        assert model == "DBS-210", (
            f"Expected DBS-210 for 31 handsets, got: {model}"
        )
        s2.close()
