import pytest
from wxcli.org_health.checks import ALL_CHECKS, run_all_checks
from wxcli.org_health.models import Finding


class TestCheckRegistry:
    def test_all_checks_populated(self):
        assert len(ALL_CHECKS) == 18

    def test_run_all_checks_returns_findings(self, sample_collected_data):
        findings = run_all_checks(sample_collected_data)
        assert isinstance(findings, list)
        for f in findings:
            assert isinstance(f, Finding)


# ---- Feature Utilization checks ----

class TestDisabledAutoAttendants:
    def test_finds_disabled_aas(self, sample_collected_data):
        sample_collected_data["auto_attendants"] = [
            {"id": "aa-1", "name": "Main", "locationName": "HQ", "enabled": True},
            {"id": "aa-2", "name": "After Hours", "locationName": "HQ", "enabled": False},
            {"id": "aa-3", "name": "Old AA", "locationName": "Branch", "enabled": False},
        ]
        findings = run_all_checks(sample_collected_data)
        disabled = [f for f in findings if f.check_name == "disabled_auto_attendants"]
        assert len(disabled) == 1
        assert disabled[0].severity == "MEDIUM"
        assert len(disabled[0].affected_items) == 2

    def test_no_disabled_aas(self, sample_collected_data):
        sample_collected_data["auto_attendants"] = [
            {"id": "aa-1", "name": "Main", "locationName": "HQ", "enabled": True},
        ]
        findings = run_all_checks(sample_collected_data)
        disabled = [f for f in findings if f.check_name == "disabled_auto_attendants"]
        assert len(disabled) == 0

    def test_empty_aa_list(self, sample_collected_data):
        findings = run_all_checks(sample_collected_data)
        disabled = [f for f in findings if f.check_name == "disabled_auto_attendants"]
        assert len(disabled) == 0


class TestUnderstaffedCallQueues:
    def test_zero_agents_is_high(self, sample_collected_data):
        sample_collected_data["call_queues"] = [
            {"id": "cq-1", "name": "Sales", "locationName": "HQ", "enabled": True,
             "agents": []},
        ]
        findings = run_all_checks(sample_collected_data)
        cq = [f for f in findings if f.check_name == "understaffed_call_queues"]
        assert len(cq) == 1
        assert cq[0].severity == "HIGH"

    def test_one_agent_is_medium(self, sample_collected_data):
        sample_collected_data["call_queues"] = [
            {"id": "cq-1", "name": "Sales", "locationName": "HQ", "enabled": True,
             "agents": [{"id": "agent-1"}]},
        ]
        findings = run_all_checks(sample_collected_data)
        cq = [f for f in findings if f.check_name == "understaffed_call_queues"]
        assert len(cq) == 1
        assert cq[0].severity == "MEDIUM"

    def test_two_agents_ok(self, sample_collected_data):
        sample_collected_data["call_queues"] = [
            {"id": "cq-1", "name": "Sales", "locationName": "HQ", "enabled": True,
             "agents": [{"id": "a1"}, {"id": "a2"}]},
        ]
        findings = run_all_checks(sample_collected_data)
        cq = [f for f in findings if f.check_name == "understaffed_call_queues"]
        assert len(cq) == 0


class TestSingleMemberHuntGroups:
    def test_single_member_flagged(self, sample_collected_data):
        sample_collected_data["hunt_groups"] = [
            {"id": "hg-1", "name": "Support", "locationName": "HQ", "enabled": True,
             "agents": [{"id": "a1"}]},
        ]
        findings = run_all_checks(sample_collected_data)
        hg = [f for f in findings if f.check_name == "single_member_hunt_groups"]
        assert len(hg) == 1
        assert hg[0].severity == "MEDIUM"

    def test_multiple_members_ok(self, sample_collected_data):
        sample_collected_data["hunt_groups"] = [
            {"id": "hg-1", "name": "Support", "locationName": "HQ", "enabled": True,
             "agents": [{"id": "a1"}, {"id": "a2"}]},
        ]
        findings = run_all_checks(sample_collected_data)
        hg = [f for f in findings if f.check_name == "single_member_hunt_groups"]
        assert len(hg) == 0


class TestEmptyVoicemailGroups:
    def test_empty_group_flagged(self, sample_collected_data):
        sample_collected_data["voicemail_groups"] = [
            {"id": "vg-1", "name": "Sales VM", "locationName": "HQ", "members": []},
        ]
        findings = run_all_checks(sample_collected_data)
        vg = [f for f in findings if f.check_name == "empty_voicemail_groups"]
        assert len(vg) == 1
        assert vg[0].severity == "LOW"

    def test_non_empty_group_ok(self, sample_collected_data):
        sample_collected_data["voicemail_groups"] = [
            {"id": "vg-1", "name": "Sales VM", "locationName": "HQ",
             "members": [{"id": "u1"}]},
        ]
        findings = run_all_checks(sample_collected_data)
        vg = [f for f in findings if f.check_name == "empty_voicemail_groups"]
        assert len(vg) == 0


class TestEmptyPagingGroups:
    def test_no_targets_flagged(self, sample_collected_data):
        sample_collected_data["paging_groups"] = [
            {"id": "pg-1", "name": "Warehouse", "locationName": "HQ", "targets": []},
        ]
        findings = run_all_checks(sample_collected_data)
        pg = [f for f in findings if f.check_name == "empty_paging_groups"]
        assert len(pg) == 1
        assert pg[0].severity == "LOW"

    def test_has_targets_ok(self, sample_collected_data):
        sample_collected_data["paging_groups"] = [
            {"id": "pg-1", "name": "Warehouse", "locationName": "HQ",
             "targets": [{"id": "t1"}]},
        ]
        findings = run_all_checks(sample_collected_data)
        pg = [f for f in findings if f.check_name == "empty_paging_groups"]
        assert len(pg) == 0


class TestEmptyCallParks:
    def test_no_extensions_flagged(self, sample_collected_data):
        sample_collected_data["call_parks"] = [
            {"id": "cp-1", "name": "Lobby Park", "locationName": "HQ",
             "callParkExtensions": []},
        ]
        findings = run_all_checks(sample_collected_data)
        cp = [f for f in findings if f.check_name == "empty_call_parks"]
        assert len(cp) == 1
        assert cp[0].severity == "LOW"

    def test_has_extensions_ok(self, sample_collected_data):
        sample_collected_data["call_parks"] = [
            {"id": "cp-1", "name": "Lobby Park", "locationName": "HQ",
             "callParkExtensions": [{"id": "ext-1"}]},
        ]
        findings = run_all_checks(sample_collected_data)
        cp = [f for f in findings if f.check_name == "empty_call_parks"]
        assert len(cp) == 0


# ---- Device Health checks ----

class TestOfflineDevices:
    def test_offline_flagged(self, sample_collected_data):
        sample_collected_data["devices"] = [
            {"id": "d-1", "displayName": "Lobby Phone", "connectionStatus": "connected",
             "product": "Cisco 8845", "personId": "u-1"},
            {"id": "d-2", "displayName": "Conf Room", "connectionStatus": "disconnected",
             "product": "Cisco 8845", "personId": "u-2"},
            {"id": "d-3", "displayName": "Old Phone", "connectionStatus": "offline",
             "product": "Cisco 7841", "personId": "u-3"},
        ]
        findings = run_all_checks(sample_collected_data)
        offline = [f for f in findings if f.check_name == "offline_devices"]
        assert len(offline) == 1
        assert offline[0].severity == "HIGH"
        assert len(offline[0].affected_items) == 2

    def test_all_online(self, sample_collected_data):
        sample_collected_data["devices"] = [
            {"id": "d-1", "displayName": "Phone", "connectionStatus": "connected",
             "product": "Cisco 8845", "personId": "u-1"},
        ]
        findings = run_all_checks(sample_collected_data)
        offline = [f for f in findings if f.check_name == "offline_devices"]
        assert len(offline) == 0


class TestDeviceLimitUsers:
    def test_user_at_limit_flagged(self, sample_collected_data):
        sample_collected_data["devices"] = [
            {"id": f"d-{i}", "displayName": f"Phone {i}", "connectionStatus": "connected",
             "product": "Cisco 8845", "personId": "u-1"}
            for i in range(5)
        ]
        sample_collected_data["users"] = [{"id": "u-1", "displayName": "John Doe", "emails": ["john@acme.com"]}]
        findings = run_all_checks(sample_collected_data)
        dl = [f for f in findings if f.check_name == "device_limit_users"]
        assert len(dl) == 1
        assert dl[0].severity == "MEDIUM"

    def test_user_under_limit_ok(self, sample_collected_data):
        sample_collected_data["devices"] = [
            {"id": f"d-{i}", "displayName": f"Phone {i}", "connectionStatus": "connected",
             "product": "Cisco 8845", "personId": "u-1"}
            for i in range(4)
        ]
        sample_collected_data["users"] = [{"id": "u-1", "displayName": "John Doe", "emails": ["john@acme.com"]}]
        findings = run_all_checks(sample_collected_data)
        dl = [f for f in findings if f.check_name == "device_limit_users"]
        assert len(dl) == 0


class TestUnassignedDevices:
    def test_no_owner_flagged(self, sample_collected_data):
        sample_collected_data["devices"] = [
            {"id": "d-1", "displayName": "Unowned", "connectionStatus": "connected",
             "product": "Cisco 8845"},
        ]
        findings = run_all_checks(sample_collected_data)
        ua = [f for f in findings if f.check_name == "unassigned_devices"]
        assert len(ua) == 1
        assert ua[0].severity == "MEDIUM"

    def test_has_person_ok(self, sample_collected_data):
        sample_collected_data["devices"] = [
            {"id": "d-1", "displayName": "Owned", "connectionStatus": "connected",
             "product": "Cisco 8845", "personId": "u-1"},
        ]
        findings = run_all_checks(sample_collected_data)
        ua = [f for f in findings if f.check_name == "unassigned_devices"]
        assert len(ua) == 0

    def test_has_workspace_ok(self, sample_collected_data):
        sample_collected_data["devices"] = [
            {"id": "d-1", "displayName": "Room", "connectionStatus": "connected",
             "product": "Cisco Room Kit", "workspaceId": "ws-1"},
        ]
        findings = run_all_checks(sample_collected_data)
        ua = [f for f in findings if f.check_name == "unassigned_devices"]
        assert len(ua) == 0


class TestDevicelessWorkspaces:
    def test_no_device_flagged(self, sample_collected_data):
        sample_collected_data["workspaces"] = [
            {"id": "ws-1", "displayName": "Conf Room A", "calling": {"type": "webexCalling"}},
        ]
        sample_collected_data["devices"] = []
        findings = run_all_checks(sample_collected_data)
        dw = [f for f in findings if f.check_name == "deviceless_workspaces"]
        assert len(dw) == 1
        assert dw[0].severity == "LOW"

    def test_has_device_ok(self, sample_collected_data):
        sample_collected_data["workspaces"] = [
            {"id": "ws-1", "displayName": "Conf Room A", "calling": {"type": "webexCalling"}},
        ]
        sample_collected_data["devices"] = [
            {"id": "d-1", "displayName": "Room Kit", "workspaceId": "ws-1",
             "connectionStatus": "connected", "product": "Room Kit"},
        ]
        findings = run_all_checks(sample_collected_data)
        dw = [f for f in findings if f.check_name == "deviceless_workspaces"]
        assert len(dw) == 0


class TestStaleActivationCodes:
    def test_activating_device_flagged(self, sample_collected_data):
        sample_collected_data["devices"] = [
            {"id": "d-1", "displayName": "New Phone", "connectionStatus": "disconnected",
             "product": "Cisco 8845", "activationState": "activating"},
        ]
        findings = run_all_checks(sample_collected_data)
        sa = [f for f in findings if f.check_name == "stale_activation_codes"]
        assert len(sa) == 1
        assert sa[0].severity == "LOW"

    def test_activated_device_ok(self, sample_collected_data):
        sample_collected_data["devices"] = [
            {"id": "d-1", "displayName": "Phone", "connectionStatus": "connected",
             "product": "Cisco 8845", "activationState": "activated"},
        ]
        findings = run_all_checks(sample_collected_data)
        sa = [f for f in findings if f.check_name == "stale_activation_codes"]
        assert len(sa) == 0


# ---- Security Posture checks ----

class TestAAExternalTransfer:
    def test_external_transfer_flagged(self, sample_collected_data):
        sample_collected_data["auto_attendants"] = [
            {"id": "aa-1", "name": "Main", "locationName": "HQ", "enabled": True,
             "extensionDialing": "ENTERPRISE", "transferEnabled": True},
        ]
        findings = run_all_checks(sample_collected_data)
        et = [f for f in findings if f.check_name == "aa_external_transfer"]
        assert len(et) == 1
        assert et[0].severity == "MEDIUM"

    def test_no_transfer_ok(self, sample_collected_data):
        sample_collected_data["auto_attendants"] = [
            {"id": "aa-1", "name": "Main", "locationName": "HQ", "enabled": True,
             "transferEnabled": False},
        ]
        findings = run_all_checks(sample_collected_data)
        et = [f for f in findings if f.check_name == "aa_external_transfer"]
        assert len(et) == 0


class TestQueuesWithoutRecording:
    def test_no_recording_flagged(self, sample_collected_data):
        sample_collected_data["call_queues"] = [
            {"id": "cq-1", "name": "Sales", "locationName": "HQ", "enabled": True,
             "agents": [{"id": "a1"}, {"id": "a2"}]},
        ]
        sample_collected_data["call_queue_details"] = {
            "cq-1": {"id": "cq-1", "name": "Sales", "callRecording": {"enabled": False}},
        }
        findings = run_all_checks(sample_collected_data)
        qr = [f for f in findings if f.check_name == "queues_without_recording"]
        assert len(qr) == 1
        assert qr[0].severity == "MEDIUM"

    def test_recording_enabled_ok(self, sample_collected_data):
        sample_collected_data["call_queues"] = [
            {"id": "cq-1", "name": "Sales", "locationName": "HQ", "enabled": True,
             "agents": [{"id": "a1"}, {"id": "a2"}]},
        ]
        sample_collected_data["call_queue_details"] = {
            "cq-1": {"id": "cq-1", "name": "Sales", "callRecording": {"enabled": True}},
        }
        findings = run_all_checks(sample_collected_data)
        qr = [f for f in findings if f.check_name == "queues_without_recording"]
        assert len(qr) == 0

    def test_no_detail_data_flagged(self, sample_collected_data):
        sample_collected_data["call_queues"] = [
            {"id": "cq-1", "name": "Sales", "locationName": "HQ", "enabled": True,
             "agents": [{"id": "a1"}, {"id": "a2"}]},
        ]
        sample_collected_data["call_queue_details"] = {}
        findings = run_all_checks(sample_collected_data)
        qr = [f for f in findings if f.check_name == "queues_without_recording"]
        assert len(qr) == 1


class TestUnrestrictedInternational:
    def test_unrestricted_flagged(self, sample_collected_data):
        sample_collected_data["outgoing_permissions"] = {
            "u-1": {
                "callingPermissions": [
                    {"callType": "INTERNATIONAL", "action": "ALLOW"},
                    {"callType": "TOLL_FREE", "action": "ALLOW"},
                ]
            },
        }
        sample_collected_data["manifest"]["sampled_users_for_permissions"] = 1
        findings = run_all_checks(sample_collected_data)
        ui = [f for f in findings if f.check_name == "unrestricted_international"]
        assert len(ui) == 1
        assert ui[0].severity == "HIGH"

    def test_blocked_international_ok(self, sample_collected_data):
        sample_collected_data["outgoing_permissions"] = {
            "u-1": {
                "callingPermissions": [
                    {"callType": "INTERNATIONAL", "action": "BLOCK"},
                ]
            },
        }
        findings = run_all_checks(sample_collected_data)
        ui = [f for f in findings if f.check_name == "unrestricted_international"]
        assert len(ui) == 0


class TestNoOutgoingRestrictions:
    def test_no_rules_flagged(self, sample_collected_data):
        sample_collected_data["outgoing_permissions"] = {
            "u-1": {"callingPermissions": []},
            "u-2": {"callingPermissions": []},
        }
        sample_collected_data["manifest"]["sampled_users_for_permissions"] = 2
        findings = run_all_checks(sample_collected_data)
        nr = [f for f in findings if f.check_name == "no_outgoing_restrictions"]
        assert len(nr) == 1
        assert nr[0].severity == "MEDIUM"

    def test_has_rules_ok(self, sample_collected_data):
        sample_collected_data["outgoing_permissions"] = {
            "u-1": {
                "callingPermissions": [
                    {"callType": "INTERNATIONAL", "action": "BLOCK"},
                ]
            },
        }
        findings = run_all_checks(sample_collected_data)
        nr = [f for f in findings if f.check_name == "no_outgoing_restrictions"]
        assert len(nr) == 0


# ---- Routing Hygiene checks ----

class TestEmptyDialPlans:
    def test_no_patterns_flagged(self, sample_collected_data):
        sample_collected_data["dial_plans"] = [
            {"id": "dp-1", "name": "US Domestic", "routeChoices": []},
        ]
        findings = run_all_checks(sample_collected_data)
        ed = [f for f in findings if f.check_name == "empty_dial_plans"]
        assert len(ed) == 1
        assert ed[0].severity == "HIGH"

    def test_has_patterns_ok(self, sample_collected_data):
        sample_collected_data["dial_plans"] = [
            {"id": "dp-1", "name": "US Domestic",
             "routeChoices": [{"routeGroupId": "rg-1"}]},
        ]
        findings = run_all_checks(sample_collected_data)
        ed = [f for f in findings if f.check_name == "empty_dial_plans"]
        assert len(ed) == 0


class TestOrphanRouteComponents:
    def test_route_group_no_trunks(self, sample_collected_data):
        sample_collected_data["route_groups"] = [
            {"id": "rg-1", "name": "RG-Dallas", "localGateways": []},
        ]
        findings = run_all_checks(sample_collected_data)
        orc = [f for f in findings if f.check_name == "orphan_route_components"]
        assert len(orc) >= 1
        rg_finding = [f for f in orc if "Route Group" in f.title]
        assert len(rg_finding) == 1
        assert rg_finding[0].severity == "MEDIUM"

    def test_route_list_no_groups(self, sample_collected_data):
        sample_collected_data["route_lists"] = [
            {"id": "rl-1", "name": "RL-Main", "routeGroups": []},
        ]
        findings = run_all_checks(sample_collected_data)
        orc = [f for f in findings if f.check_name == "orphan_route_components"]
        assert len(orc) >= 1
        rl_finding = [f for f in orc if "Route List" in f.title]
        assert len(rl_finding) == 1

    def test_populated_components_ok(self, sample_collected_data):
        sample_collected_data["route_groups"] = [
            {"id": "rg-1", "name": "RG-Dallas",
             "localGateways": [{"id": "trunk-1"}]},
        ]
        sample_collected_data["route_lists"] = [
            {"id": "rl-1", "name": "RL-Main",
             "routeGroups": [{"id": "rg-1"}]},
        ]
        findings = run_all_checks(sample_collected_data)
        orc = [f for f in findings if f.check_name == "orphan_route_components"]
        assert len(orc) == 0


class TestTrunkErrors:
    def test_error_trunk_flagged(self, sample_collected_data):
        sample_collected_data["trunks"] = [
            {"id": "t-1", "name": "Dallas LGW", "trunkType": "REGISTERING",
             "inUse": True, "registrationStatus": "error"},
            {"id": "t-2", "name": "Austin LGW", "trunkType": "REGISTERING",
             "inUse": True, "registrationStatus": "registered"},
        ]
        findings = run_all_checks(sample_collected_data)
        te = [f for f in findings if f.check_name == "trunk_errors"]
        assert len(te) == 1
        assert te[0].severity == "HIGH"
        assert len(te[0].affected_items) == 1

    def test_all_registered_ok(self, sample_collected_data):
        sample_collected_data["trunks"] = [
            {"id": "t-1", "name": "Dallas LGW", "trunkType": "REGISTERING",
             "inUse": True, "registrationStatus": "registered"},
        ]
        findings = run_all_checks(sample_collected_data)
        te = [f for f in findings if f.check_name == "trunk_errors"]
        assert len(te) == 0

    def test_empty_trunks_ok(self, sample_collected_data):
        findings = run_all_checks(sample_collected_data)
        te = [f for f in findings if f.check_name == "trunk_errors"]
        assert len(te) == 0
