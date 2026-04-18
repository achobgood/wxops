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
